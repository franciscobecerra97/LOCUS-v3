from __future__ import annotations

import io
import json
import time
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from typing import Any
from unittest.mock import patch

import tasks
from locus.docker_engine import DockerEngineError
from locus.integrated_controller import (
    CLIENT_ID_LABEL,
    CLIENT_LABEL,
    CLIENT_NETWORKS,
    CONTROLLER_LABEL,
    CONTROLLER_PROFILE,
    EXPECTED_COMPOSE_SERVICES,
    IMAGE_METADATA_LABELS,
    PROJECT_LABEL,
    S3_IMAGE,
    TOKEN_DIGEST_LABEL,
    ControllerError,
    ManagedContainerController,
)
from locus.integrated_manager import (
    ManagerApplication,
    ManagerUiError,
    _loopback_origin,
)

IMAGE = "sha256:" + "a1" * 32
PROJECT = "locus-managed-test"
VOLUME = f"{PROJECT}_managed-client-data"


class _FakeEngine:
    def __init__(self) -> None:
        self.clients: dict[str, dict[str, Any]] = {}
        self.compose: list[dict[str, Any]] = []
        self.inspections: dict[str, dict[str, Any]] = {}
        self.calls: list[tuple[str, str]] = []
        self.create_calls = 0
        self.fail_create_response = False
        self.remove_failures = 0
        self.stop_failures: set[str] = set()
        self.removed_networks: set[str] = set()

    def containers(self, *, labels: tuple[str, ...]) -> list[dict[str, Any]]:
        if f"{CLIENT_LABEL}=true" in labels:
            return list(self.clients.values())
        return self.compose

    def networks(self, *, labels: tuple[str, ...]) -> list[dict[str, Any]]:
        logical = labels[1].split("=", 1)[1]
        if logical in self.removed_networks:
            return []
        return [
            {
                "IPAM": {
                    "Config": [
                        {
                            "Gateway": "172.31.0.1",
                            "Subnet": "172.31.0.0/24",
                        }
                    ]
                },
                "Id": f"network-{logical}",
                "Name": f"{PROJECT}_{logical}",
            }
        ]

    def create_container(self, *, name: str, specification: dict[str, Any]) -> str:
        self.create_calls += 1
        identifier = "b2" * 32
        labels = {**IMAGE_METADATA_LABELS, **specification["Labels"]}
        first_network = specification["HostConfig"]["NetworkMode"]
        summary = {
            "Id": identifier,
            "ImageID": IMAGE,
            "Labels": labels,
            "Names": [f"/{name}"],
            "Ports": [],
            "State": "created",
            "Status": "Created",
        }
        self.clients[identifier] = summary
        self.inspections[identifier] = {
            "Config": {
                "Cmd": specification["Cmd"],
                "Env": specification["Env"],
                "ExposedPorts": specification["ExposedPorts"],
                "Healthcheck": specification["Healthcheck"],
                "Image": IMAGE,
                "Labels": labels,
                "User": specification["User"],
            },
            "HostConfig": specification["HostConfig"],
            "Id": identifier,
            "Image": IMAGE,
            "Mounts": [
                {
                    "Destination": "/role",
                    "Name": VOLUME,
                    "RW": False,
                    "Type": "volume",
                }
            ],
            "NetworkSettings": {"Networks": {first_network: {}}},
            "State": {"Health": {"Status": "starting"}, "Status": "created"},
        }
        if self.fail_create_response:
            raise DockerEngineError("injected ambiguous create response")
        return identifier

    def connect_network(self, network_id: str, container_id: str) -> None:
        logical = network_id.removeprefix("network-")
        self.inspections[container_id]["NetworkSettings"]["Networks"][
            f"{PROJECT}_{logical}"
        ] = {}

    def inspect_container(self, container_id: str) -> dict[str, Any]:
        return self.inspections[container_id]

    def start_container(self, container_id: str) -> None:
        self.calls.append(("start", container_id))
        self.clients[container_id]["State"] = "running"
        self.clients[container_id]["Status"] = "Up (healthy)"
        self.clients[container_id]["Ports"] = [
            {"IP": "127.0.0.1", "PrivatePort": 8080, "PublicPort": 49152}
        ]
        self.inspections[container_id]["State"] = {
            "Health": {"Status": "healthy"},
            "Status": "running",
        }

    def stop_container(self, container_id: str, *, timeout: int = 3) -> None:
        del timeout
        self.calls.append(("stop", container_id))
        if container_id in self.stop_failures:
            raise DockerEngineError("injected stop failure")
        if container_id in self.clients:
            self.clients[container_id]["State"] = "exited"
            self.clients[container_id]["Status"] = "Exited"
        else:
            for item in self.compose:
                if item["Id"] == container_id:
                    item["State"] = "exited"
                    item["Status"] = "Exited"
                    break
        if container_id in self.inspections:
            self.inspections[container_id]["State"] = {"Status": "exited"}

    def restart_container(self, container_id: str, *, timeout: int = 3) -> None:
        del timeout
        self.calls.append(("restart", container_id))

    def kill_container(self, container_id: str) -> None:
        self.calls.append(("kill", container_id))

    def remove_container(self, container_id: str, *, force: bool = False) -> None:
        del force
        self.calls.append(("remove", container_id))
        if self.remove_failures:
            self.remove_failures -= 1
            raise DockerEngineError("injected remove failure")
        self.clients.pop(container_id, None)
        self.inspections.pop(container_id, None)

    def remove_network(self, network_id: str) -> None:
        self.calls.append(("remove-network", network_id))
        self.removed_networks.add(network_id.removeprefix("network-"))


def _install_compose(engine: _FakeEngine) -> None:
    for index, service in enumerate(sorted(EXPECTED_COMPOSE_SERVICES), start=1):
        identifier = f"{index:064x}"
        item = {
            "Id": identifier,
            "Image": S3_IMAGE if service == "s3" else IMAGE,
            "ImageID": IMAGE,
            "Labels": {
                "com.docker.compose.project": PROJECT,
                "com.docker.compose.service": service,
            },
            "Names": [f"/{PROJECT}-{service}-1"],
            "Ports": [],
            "State": "running" if service != "bootstrap" else "exited",
            "Status": "Up" if service != "bootstrap" else "Exited",
        }
        engine.compose.append(item)
        engine.inspections[identifier] = {
            "Config": {"Labels": item["Labels"]},
            "Id": identifier,
            "State": {"Status": item["State"]},
        }


def _wait_until(predicate: Any, *, timeout: float = 2.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.01)
    raise AssertionError("timed out waiting for background lifecycle operation")


class ManagedControllerTests(unittest.TestCase):
    def controller(self, engine: _FakeEngine) -> ManagedContainerController:
        return ManagedContainerController(
            engine=engine,  # type: ignore[arg-type]
            project=PROJECT,
            image=IMAGE,
            client_volume=VOLUME,
            lifecycle_secret=b"l" * 32,
        )

    def test_create_is_fixed_scoped_and_idempotent(self) -> None:
        engine = _FakeEngine()
        controller = self.controller(engine)
        first = controller.create_client()
        second = controller.create_client()
        self.assertEqual(first, second)
        self.assertEqual(first["role"], "client")
        self.assertEqual(first["url"], "http://127.0.0.1:49152/")
        self.assertEqual(len(engine.clients), 1)
        item = next(iter(engine.clients.values()))
        labels = item["Labels"]
        self.assertEqual(labels[PROJECT_LABEL], PROJECT)
        self.assertEqual(labels[CLIENT_LABEL], "true")
        self.assertEqual(labels[CONTROLLER_LABEL], CONTROLLER_PROFILE)
        self.assertRegex(labels[CLIENT_ID_LABEL], r"^client-[0-9a-f]{16}$")
        self.assertRegex(labels[TOKEN_DIGEST_LABEL], r"^[0-9a-f]{64}$")
        inspection = next(iter(engine.inspections.values()))
        self.assertEqual(
            set(inspection["NetworkSettings"]["Networks"]),
            {f"{PROJECT}_{name}" for name in CLIENT_NETWORKS},
        )
        self.assertNotIn("management", CLIENT_NETWORKS)

    def test_performance_client_environment_is_exact_and_revalidated(self) -> None:
        engine = _FakeEngine()
        environment = {
            "LOCUS_PERFORMANCE_EVIDENCE": "1",
            "LOCUS_PERFORMANCE_FIXTURE_ID": "topology:block-01",
        }
        with patch.dict("os.environ", environment, clear=False):
            controller = self.controller(engine)
            controller.create_client()
            inspection = next(iter(engine.inspections.values()))
            observed = {
                item
                for item in inspection["Config"]["Env"]
                if item.startswith("LOCUS_PERFORMANCE_")
            }
            self.assertEqual(
                observed,
                {
                    "LOCUS_PERFORMANCE_EVIDENCE=1",
                    "LOCUS_PERFORMANCE_FIXTURE_ID=topology:block-01",
                },
            )
            controller._validate_client_inspection(inspection)

    def test_controller_mutations_replay_once_and_reject_changed_reuse(self) -> None:
        engine = _FakeEngine()
        controller = self.controller(engine)
        create_request = {"operation_id": "create-0001"}
        first_status, first = controller.handle(
            "/v1/client/create", create_request, "manager-ui"
        )
        second_status, second = controller.handle(
            "/v1/client/create", create_request, "manager-ui"
        )
        self.assertEqual((first_status, first), (second_status, second))
        self.assertEqual(engine.create_calls, 1)
        client = first["client"]
        assert isinstance(client, dict)
        action_request = {
            "action": "restart",
            "container_id": client["id"],
            "operation_id": "restart-0001",
        }
        action_first = controller.handle(
            "/v1/container/action", action_request, "manager-ui"
        )
        action_second = controller.handle(
            "/v1/container/action", action_request, "manager-ui"
        )
        self.assertEqual(action_first, action_second)
        self.assertEqual(
            [call for call in engine.calls if call[0] == "restart"],
            [("restart", client["id"])],
        )
        with self.assertRaisesRegex(ControllerError, "changed request"):
            controller.handle(
                "/v1/container/action",
                {**action_request, "action": "stop"},
                "manager-ui",
            )
        with self.assertRaisesRegex(ControllerError, "changed request"):
            controller.handle(
                "/v1/client/destroy",
                {
                    "container_id": client["id"],
                    "operation_id": "restart-0001",
                },
                "manager-ui",
            )

    def test_operation_identifier_is_required_and_bounded(self) -> None:
        controller = self.controller(_FakeEngine())
        for invalid in ("", " contains-space", "x" * 129, "slash/value", None):
            with self.subTest(invalid=invalid), self.assertRaises(ControllerError):
                controller.handle(
                    "/v1/client/create",
                    {"operation_id": invalid},
                    "manager-ui",
                )

    def test_existing_client_is_fully_inspected_before_idempotent_return(self) -> None:
        engine = _FakeEngine()
        controller = self.controller(engine)
        controller.create_client()
        inspection = next(iter(engine.inspections.values()))
        inspection["Mounts"].append(
            {
                "Destination": "/unexpected",
                "Name": "forged-volume",
                "RW": False,
                "Type": "volume",
            }
        )
        with self.assertRaisesRegex(ControllerError, "role mount changed"):
            controller.create_client()

    def test_ambiguous_create_response_is_cleaned_before_retry(self) -> None:
        engine = _FakeEngine()
        controller = self.controller(engine)
        engine.fail_create_response = True
        with self.assertRaises(DockerEngineError):
            controller.create_client()
        self.assertFalse(engine.clients)
        self.assertEqual(len([call for call in engine.calls if call[0] == "remove"]), 1)
        engine.fail_create_response = False
        self.assertEqual(controller.create_client()["state"], "running")
        self.assertEqual(engine.create_calls, 2)

    def test_full_container_id_and_exact_transition_matrix_are_enforced(self) -> None:
        engine = _FakeEngine()
        controller = self.controller(engine)
        client = controller.create_client()
        identifier = str(client["id"])
        with self.assertRaisesRegex(ControllerError, "container identifier"):
            controller.action(identifier[:12], "restart")
        baseline = list(engine.calls)
        with self.assertRaisesRegex(ControllerError, "current state"):
            controller.action(identifier, "start")
        self.assertEqual(engine.calls, baseline)
        controller.action(identifier, "stop")
        with self.assertRaisesRegex(ControllerError, "current state"):
            controller.action(identifier, "restart")
        controller.action(identifier, "start")
        self.assertEqual(engine.inspections[identifier]["State"]["Status"], "running")

    def test_self_destroy_retries_checks_postcondition_and_exposes_failure(
        self,
    ) -> None:
        engine = _FakeEngine()
        controller = self.controller(engine)
        client = controller.create_client()
        client_id = str(client["client_id"])
        token = controller._token(client_id)
        request = {
            "client_id": client_id,
            "operation_id": "self-destroy-fails",
            "token": token,
        }
        engine.remove_failures = 3
        with (
            patch("locus.integrated_controller.SELF_DESTROY_INITIAL_DELAY_SECONDS", 0),
            patch("locus.integrated_controller.SELF_DESTROY_RETRY_DELAY_SECONDS", 0),
        ):
            first = controller.handle(
                "/v1/client/self-destroy", request, "managed-client"
            )
            _wait_until(
                lambda: controller._self_destroy_status.get(client_id) == "failed"
            )
            self.assertEqual(
                controller._public_item(next(iter(engine.clients.values())))[
                    "self_destroy_status"
                ],
                "failed",
            )
            removal_calls = len([call for call in engine.calls if call[0] == "remove"])
            self.assertEqual(removal_calls, 3)
            self.assertEqual(
                controller.handle("/v1/client/self-destroy", request, "managed-client"),
                first,
            )
            self.assertEqual(
                len([call for call in engine.calls if call[0] == "remove"]),
                removal_calls,
            )
            with self.assertRaisesRegex(ControllerError, "changed request"):
                controller.handle(
                    "/v1/client/self-destroy",
                    {**request, "token": "0" * 64},
                    "managed-client",
                )
            controller.handle(
                "/v1/client/self-destroy",
                {**request, "operation_id": "self-destroy-retry"},
                "managed-client",
            )
            _wait_until(
                lambda: controller._self_destroy_status.get(client_id) == "destroyed"
            )
            self.assertFalse(engine.clients)
        self.assertEqual(controller._self_destroy_status[client_id], "destroyed")

    def test_partial_system_stop_is_reported_failed_and_exact_replay_is_stable(
        self,
    ) -> None:
        engine = _FakeEngine()
        _install_compose(engine)
        controller = self.controller(engine)
        party = next(
            item
            for item in engine.compose
            if item["Labels"]["com.docker.compose.service"] == "party1"
        )
        engine.stop_failures.add(str(party["Id"]))
        request = {"operation_id": "system-stop-fails"}
        with patch("locus.integrated_controller.SYSTEM_STOP_DELAY_SECONDS", 0):
            first = controller.handle("/v1/system/stop", request, "manager-ui")
            self.assertEqual(first[1]["shutdown_status"], "stopping")
            _wait_until(lambda: controller.shutdown_status == "failed")
            status = controller.status()
            self.assertEqual(status["shutdown_status"], "failed")
            stop_calls = list(engine.calls)
            self.assertEqual(
                controller.handle("/v1/system/stop", request, "manager-ui"), first
            )
            time.sleep(0.02)
            self.assertEqual(engine.calls, stop_calls)

    def test_caller_cannot_supply_a_target_or_docker_specification(self) -> None:
        controller = self.controller(_FakeEngine())
        with self.assertRaises(ControllerError):
            controller.handle("/v1/client/create", {"image": "attacker"}, "manager-ui")
        with self.assertRaises(ControllerError):
            controller.handle("/v1/status", {}, "managed-client")
        with self.assertRaises(ControllerError):
            controller.handle(
                "/v1/client/self-destroy",
                {
                    "client_id": "client-0000000000000000",
                    "operation_id": "forged-destroy",
                    "token": "bad",
                },
                "managed-client",
            )

    def test_forged_client_inventory_fails_closed(self) -> None:
        engine = _FakeEngine()
        controller = self.controller(engine)
        controller.create_client()
        item = next(iter(engine.clients.values()))
        item["ImageID"] = "sha256:" + "ff" * 32
        with self.assertRaises(ControllerError):
            controller._clients()

    def test_unknown_compose_service_fails_closed(self) -> None:
        engine = _FakeEngine()
        engine.compose.append(
            {
                "Id": "c3" * 32,
                "ImageID": IMAGE,
                "Labels": {
                    "com.docker.compose.project": PROJECT,
                    "com.docker.compose.service": "forged-service",
                },
                "Names": [f"/{PROJECT}-forged-service-1"],
            }
        )
        with self.assertRaises(ControllerError):
            self.controller(engine).status()

    def test_constructor_requires_an_immutable_image_id(self) -> None:
        with self.assertRaises(ControllerError):
            ManagedContainerController(
                engine=_FakeEngine(),  # type: ignore[arg-type]
                project=PROJECT,
                image="locus:latest",
                client_volume=VOLUME,
                lifecycle_secret=b"l" * 32,
            )

    def test_client_process_actions_use_only_the_exact_managed_instance(self) -> None:
        engine = _FakeEngine()
        controller = self.controller(engine)
        client = controller.create_client()
        controller.action(client["id"], "restart")
        self.assertIn(("restart", client["id"]), engine.calls)


class ManagerApplicationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.application = ManagerApplication(role_root=Path("unused"))
        self.calls: list[tuple[str, dict[str, Any]]] = []

        def controller(path: str, value: dict[str, Any]) -> dict[str, Any]:
            self.calls.append((path, value))
            return {
                "containers": [],
                "shutdown_status": "ready",
                "status": "ready",
            }

        self.application._controller = controller  # type: ignore[method-assign]

    def test_session_and_mutations_are_separate_and_csrf_protected(self) -> None:
        session = self.application.dispatch(
            "GET",
            "/api/manager/v1/session",
            b"",
            content_type=None,
            csrf_token=None,
            origin=None,
            expected_origin="http://127.0.0.1:8765",
        )
        value = json.loads(session.body)
        self.assertEqual(value["status"], "ready")
        with self.assertRaises(ManagerUiError):
            self.application.dispatch(
                "POST",
                "/api/manager/v1/clients",
                b"{}",
                content_type="application/json",
                csrf_token=None,
                origin="http://127.0.0.1:8765",
                expected_origin="http://127.0.0.1:8765",
            )
        created = self.application.dispatch(
            "POST",
            "/api/manager/v1/clients",
            json.dumps({"operation_id": "create-ui-0001"}).encode(),
            content_type="application/json",
            csrf_token=value["csrf_token"],
            origin="http://127.0.0.1:8765",
            expected_origin="http://127.0.0.1:8765",
        )
        self.assertEqual(created.status, 201)
        self.assertEqual(
            self.calls,
            [("/v1/client/create", {"operation_id": "create-ui-0001"})],
        )

    def test_all_manager_mutations_require_and_forward_operation_id(self) -> None:
        session = json.loads(
            self.application.dispatch(
                "GET",
                "/api/manager/v1/session",
                b"",
                content_type=None,
                csrf_token=None,
                origin=None,
                expected_origin="http://127.0.0.1:8765",
            ).body
        )
        common: dict[str, Any] = {
            "content_type": "application/json",
            "csrf_token": session["csrf_token"],
            "origin": "http://127.0.0.1:8765",
            "expected_origin": "http://127.0.0.1:8765",
        }
        requests = (
            (
                "/api/manager/v1/container-action",
                {
                    "action": "restart",
                    "container_id": "a" * 64,
                    "operation_id": "restart-ui-0001",
                },
                "/v1/container/action",
            ),
            (
                "/api/manager/v1/client-destroy",
                {"container_id": "b" * 64, "operation_id": "destroy-ui-0001"},
                "/v1/client/destroy",
            ),
            (
                "/api/manager/v1/system-stop",
                {"operation_id": "stop-ui-0001"},
                "/v1/system/stop",
            ),
        )
        for route, body, controller_route in requests:
            with self.subTest(route=route):
                self.application.dispatch(
                    "POST", route, json.dumps(body).encode(), **common
                )
                self.assertEqual(self.calls[-1], (controller_route, body))
                with self.assertRaises(ManagerUiError):
                    self.application.dispatch(
                        "POST",
                        route,
                        json.dumps(
                            {
                                key: value
                                for key, value in body.items()
                                if key != "operation_id"
                            }
                        ).encode(),
                        **common,
                    )

    def test_manager_json_decoder_rejects_duplicates_constants_and_nonobjects(
        self,
    ) -> None:
        session = json.loads(
            self.application.dispatch(
                "GET",
                "/api/manager/v1/session",
                b"",
                content_type=None,
                csrf_token=None,
                origin=None,
                expected_origin="http://127.0.0.1:8765",
            ).body
        )
        common: dict[str, Any] = {
            "content_type": "application/json",
            "csrf_token": session["csrf_token"],
            "origin": "http://127.0.0.1:8765",
            "expected_origin": "http://127.0.0.1:8765",
        }
        for body in (
            b'{"operation_id":"one","operation_id":"two"}',
            b'{"operation_id":NaN}',
            b"[]",
            b"\xff",
        ):
            with self.subTest(body=body):
                with self.assertRaises(ManagerUiError):
                    self.application.dispatch(
                        "POST", "/api/manager/v1/clients", body, **common
                    )

    def test_manager_asset_surfaces_shutdown_and_self_destroy_failures(self) -> None:
        source = Path("locus/manager_assets/manager.js").read_text(encoding="utf-8")
        self.assertIn("value.shutdown_status", source)
        self.assertIn('failed: "Shutdown failed"', source)
        self.assertIn('container.self_destroy_status === "failed"', source)
        self.assertNotIn('byId("system-state").textContent = "Ready"', source)

    def test_manager_asset_locks_mutations_during_shutdown(self) -> None:
        root = Path("locus/manager_assets")
        html = (root / "index.html").read_text(encoding="utf-8")
        script = (root / "manager.js").read_text(encoding="utf-8")
        stylesheet = (root / "manager.css").read_text(encoding="utf-8")

        header = html.split("</header>", 1)[0]
        self.assertIn('id="stop-system"', header)
        self.assertNotIn("danger-zone", html)
        self.assertIn("let systemStopping = false", script)
        self.assertIn("if (busy || systemStopping) return false", script)
        self.assertIn('systemStopping = shutdownStatus === "stopping"', script)
        self.assertIn("hasClient || systemStopping", script)
        self.assertIn(".header-stop", stylesheet)

    def test_loopback_host_is_required(self) -> None:
        self.assertEqual(_loopback_origin("127.0.0.1:8765"), "http://127.0.0.1:8765")
        self.assertEqual(_loopback_origin("localhost:8765"), "http://localhost:8765")
        with self.assertRaises(ManagerUiError):
            _loopback_origin("example.test:8765")


class ManagedCommandSurfaceTests(unittest.TestCase):
    def test_smoke_concurrent_create_replays_one_exact_client(self) -> None:
        client = {
            "client_id": "client-0123456789abcdef",
            "id": "a" * 64,
            "port": 49152,
        }
        requests: list[dict[str, object]] = []

        def post(
            _port: int,
            _csrf: str,
            _path: str,
            request: dict[str, object],
            *,
            expected: tuple[int, ...],
        ) -> dict[str, object]:
            self.assertEqual(expected, (201,))
            requests.append(request)
            return {"client": client, "status": "created"}

        with (
            patch("tasks._manager_post", side_effect=post),
            patch(
                "tasks._manager_status",
                return_value={"containers": [client]},
            ),
        ):
            self.assertEqual(tasks._create_client_concurrently(8765, "csrf"), client)
        self.assertEqual(len(requests), 2)
        self.assertEqual(requests[0], requests[1])

    def test_missing_browser_network_empty_list_is_absent(self) -> None:
        with patch("tasks.run_capture", return_value="[]\n"):
            self.assertIsNone(tasks._browser_edge_inspection(PROJECT, {}))

    def test_start_has_no_workflow_mode_and_stop_has_no_destroy_switch(self) -> None:
        parser = tasks.build_integrated_parser()
        parsed = parser.parse_args(["integrated-start"])
        self.assertEqual(parsed.project, tasks.DEFAULT_PROJECT)
        self.assertEqual(parsed.port, tasks.DEFAULT_MANAGER_PORT)
        self.assertFalse(hasattr(parsed, "mode"))
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            parser.parse_args(["integrated-start", "--mode", "enrollment"])
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            parser.parse_args(["integrated-stop", "--destroy"])


if __name__ == "__main__":
    unittest.main()
