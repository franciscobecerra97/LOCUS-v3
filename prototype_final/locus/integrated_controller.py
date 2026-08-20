"""Project-scoped Docker lifecycle controller for the managed deployment."""

from __future__ import annotations

import argparse
import contextvars
import copy
import hashlib
import hmac
import ipaddress
import os
import re
import secrets
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .codec import encode
from .docker_engine import DockerEngine, DockerEngineError
from .flow_audit import configure_role
from .integrated_rpc import serve_rpc

CONTROLLER_PROFILE = "LOCUS-local-container-controller-v1"
CONTROLLER_API_VERSION = "LOCUS-container-controller-api-v1"
PROJECT_LABEL = "com.locus.project"
CLIENT_LABEL = "com.locus.managed-client"
CLIENT_ID_LABEL = "com.locus.client-id"
CONTROLLER_LABEL = "com.locus.controller-profile"
TOKEN_DIGEST_LABEL = "com.locus.lifecycle-token-sha256"
COMPOSE_PROJECT_LABEL = "com.docker.compose.project"
COMPOSE_SERVICE_LABEL = "com.docker.compose.service"
CLIENT_NETWORKS = (
    "admission",
    "browser-edge",
    "client-lifecycle",
    "control",
    "recovery",
    "resolver",
    "storage",
)
BLOCKED_BASE_ACTIONS = {"bootstrap", "manager-controller", "manager-ui"}
ALLOWED_ACTIONS = {"kill", "restart", "start", "stop"}
MAX_CONTROLLER_OPERATIONS = 4096
SELF_DESTROY_ATTEMPTS = 3
SELF_DESTROY_INITIAL_DELAY_SECONDS = 0.35
SELF_DESTROY_RETRY_DELAY_SECONDS = 0.25
SYSTEM_STOP_DELAY_SECONDS = 0.5
_OPERATION_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z")
EXPECTED_COMPOSE_SERVICES = frozenset(
    {
        "admission",
        "bootstrap",
        "manager-controller",
        "manager-ui",
        "operator",
        "party1",
        "party2",
        "party3",
        "party4",
        "party5",
        "resolver",
        "s3",
        "storage-gateway",
    }
)
S3_IMAGE = (
    "chrislusf/seaweedfs:4.29@"
    "sha256:d47c7ee99fcb951351d7194915f4e3a5ea604a8e8871183d713907dec4fb9bf5"
)
IMAGE_METADATA_LABELS = {
    "org.opencontainers.image.source": "anonymous-artifact-pending",
    "org.opencontainers.image.title": "LOCUS reference deployment",
    "org.opencontainers.image.version": "0.1.0",
}


class ControllerError(ValueError):
    """A lifecycle request exceeded the fixed managed-project authority."""


def _exact(value: object, fields: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        raise ControllerError(f"invalid {label}")
    return value


def _operation_id(value: object) -> str:
    if not isinstance(value, str) or _OPERATION_ID.fullmatch(value) is None:
        raise ControllerError("invalid operation identifier")
    return value


@dataclass
class _MutationRecord:
    signature: bytes
    result: tuple[int, dict[str, Any]] | None = None
    failed: bool = False


class ManagedContainerController:
    """Narrow controller; no decoded request can supply a Docker specification."""

    def __init__(
        self,
        *,
        engine: DockerEngine,
        project: str,
        image: str,
        client_volume: str,
        lifecycle_secret: bytes,
    ) -> None:
        if (
            not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,47}", project)
            or not re.fullmatch(r"sha256:[0-9a-f]{64}", image)
            or not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]{0,127}", client_volume)
        ):
            raise ControllerError("invalid managed project")
        if len(lifecycle_secret) < 32:
            raise ControllerError("invalid lifecycle secret")
        self.engine = engine
        self.project = project
        self.image = image
        self.client_volume = client_volume
        self.lifecycle_secret = lifecycle_secret
        self.lock = threading.RLock()
        self.shutdown_status = "ready"
        self._mutations: dict[str, _MutationRecord] = {}
        self._self_destroy_status: dict[str, str] = {}

    def _mutation(
        self,
        *,
        peer: str,
        path: str,
        request: dict[str, Any],
        execute: Callable[[], tuple[int, dict[str, Any]]],
    ) -> tuple[int, dict[str, Any]]:
        """Execute one bounded mutation or replay its exact stored outcome."""

        operation = _operation_id(request.get("operation_id"))
        signature = hashlib.sha256(
            encode({"path": path, "peer": peer, "request": request})
        ).digest()
        with self.lock:
            prior = self._mutations.get(operation)
            if prior is not None:
                if not hmac.compare_digest(prior.signature, signature):
                    raise ControllerError("operation identifier reuse changed request")
                if prior.failed:
                    raise ControllerError("stored lifecycle operation failed")
                if prior.result is None:
                    raise ControllerError("lifecycle operation is still running")
                return copy.deepcopy(prior.result)
            if len(self._mutations) >= MAX_CONTROLLER_OPERATIONS:
                raise ControllerError("lifecycle operation limit reached")
            record = _MutationRecord(signature=signature)
            self._mutations[operation] = record
            try:
                status, value = execute()
                if (
                    isinstance(status, bool)
                    or not isinstance(status, int)
                    or not 100 <= status <= 599
                    or not isinstance(value, dict)
                ):
                    raise ControllerError("invalid lifecycle operation result")
                record.result = (status, copy.deepcopy(value))
                return status, value
            except Exception:
                record.failed = True
                raise

    def _compose(self) -> list[dict[str, Any]]:
        items = self.engine.containers(
            labels=(f"{COMPOSE_PROJECT_LABEL}={self.project}",)
        )
        observed: dict[str, dict[str, Any]] = {}
        for item in items:
            labels = item.get("Labels")
            service = (
                labels.get(COMPOSE_SERVICE_LABEL) if isinstance(labels, dict) else None
            )
            if (
                not isinstance(labels, dict)
                or labels.get(COMPOSE_PROJECT_LABEL) != self.project
                or not isinstance(service, str)
                or service not in EXPECTED_COMPOSE_SERVICES
                or service in observed
                or self._name(item) != f"{self.project}-{service}-1"
                or (service != "s3" and item.get("ImageID") != self.image)
                or (service == "s3" and item.get("Image") != S3_IMAGE)
            ):
                raise ControllerError("invalid managed Compose inventory")
            observed[service] = item
        if set(observed) != EXPECTED_COMPOSE_SERVICES:
            raise ControllerError("incomplete managed Compose inventory")
        return items

    def _clients(self) -> list[dict[str, Any]]:
        items = self.engine.containers(
            labels=(f"{PROJECT_LABEL}={self.project}", f"{CLIENT_LABEL}=true")
        )
        for item in items:
            labels = item.get("Labels")
            client_id = (
                labels.get(CLIENT_ID_LABEL) if isinstance(labels, dict) else None
            )
            if (
                not isinstance(labels, dict)
                or labels.get(PROJECT_LABEL) != self.project
                or labels.get(CLIENT_LABEL) != "true"
                or labels.get(CONTROLLER_LABEL) != CONTROLLER_PROFILE
                or not isinstance(client_id, str)
                or re.fullmatch(r"client-[0-9a-f]{16}", client_id) is None
                or not isinstance(labels.get(TOKEN_DIGEST_LABEL), str)
                or re.fullmatch(r"[0-9a-f]{64}", labels[TOKEN_DIGEST_LABEL]) is None
                or item.get("ImageID") != self.image
                or self._name(item) != f"{self.project}-{client_id}"
            ):
                raise ControllerError("invalid managed client inventory")
        return items

    @staticmethod
    def _name(item: dict[str, Any]) -> str:
        names = item.get("Names")
        if (
            not isinstance(names, list)
            or len(names) != 1
            or not isinstance(names[0], str)
        ):
            raise ControllerError("invalid Docker container name")
        return names[0].removeprefix("/")

    def _public_item(self, item: dict[str, Any]) -> dict[str, object]:
        labels = item.get("Labels")
        if not isinstance(labels, dict):
            raise ControllerError("invalid Docker labels")
        client_id = labels.get(CLIENT_ID_LABEL)
        service = labels.get(COMPOSE_SERVICE_LABEL)
        role = "client" if client_id is not None else str(service)
        ports = item.get("Ports", [])
        public_port: int | None = None
        if isinstance(ports, list):
            for port in ports:
                if (
                    isinstance(port, dict)
                    and port.get("PrivatePort") == 8080
                    and port.get("IP") == "127.0.0.1"
                    and isinstance(port.get("PublicPort"), int)
                ):
                    public_port = int(port["PublicPort"])
        return {
            "client_id": client_id,
            "health": str(item.get("Status", "unknown")),
            "id": str(item.get("Id", "")),
            "name": self._name(item),
            "port": public_port,
            "role": role,
            "self_destroy_status": (
                self._self_destroy_status.get(str(client_id), "ready")
                if client_id is not None
                else None
            ),
            "state": str(item.get("State", "unknown")),
            "url": None if public_port is None else f"http://127.0.0.1:{public_port}/",
        }

    def status(self) -> dict[str, object]:
        items = [*self._compose(), *self._clients()]
        public = sorted(
            (self._public_item(item) for item in items),
            key=lambda item: str(item["name"]),
        )
        return {
            "api_version": CONTROLLER_API_VERSION,
            "containers": public,
            "project": self.project,
            "shutdown_status": self.shutdown_status,
            "status": "ready",
        }

    def _network(self, logical_name: str) -> dict[str, Any]:
        matches = self.engine.networks(
            labels=(
                f"{COMPOSE_PROJECT_LABEL}={self.project}",
                f"com.docker.compose.network={logical_name}",
            )
        )
        if len(matches) != 1 or not isinstance(matches[0].get("Id"), str):
            raise ControllerError("managed network is unavailable")
        return matches[0]

    def _token(self, client_id: str) -> str:
        return hmac.new(
            self.lifecycle_secret,
            f"{self.project}:{client_id}".encode("ascii"),
            hashlib.sha256,
        ).hexdigest()

    @staticmethod
    def _network_gateway(network: dict[str, Any]) -> str:
        ipam = network.get("IPAM")
        configurations = ipam.get("Config") if isinstance(ipam, dict) else None
        if not isinstance(configurations, list) or len(configurations) != 1:
            raise ControllerError("managed browser network has invalid IPAM")
        configuration = configurations[0]
        gateway = (
            configuration.get("Gateway") if isinstance(configuration, dict) else None
        )
        if not isinstance(gateway, str):
            raise ControllerError("managed browser network has invalid gateway")
        try:
            address = ipaddress.ip_address(gateway)
        except ValueError as exc:
            raise ControllerError(
                "managed browser network has invalid gateway"
            ) from exc
        if (
            not isinstance(address, ipaddress.IPv4Address)
            or address.is_loopback
            or address.is_unspecified
            or address.is_multicast
        ):
            raise ControllerError("managed browser network has invalid gateway")
        return str(address)

    def _client_specification(
        self,
        *,
        browser_gateway: str,
        client_id: str,
        token: str,
        first_network: str,
    ) -> dict[str, Any]:
        environment = [
            f"LOCUS_BROWSER_EDGE_GATEWAY={browser_gateway}",
            f"LOCUS_CLIENT_INSTANCE_ID={client_id}",
            f"LOCUS_CLIENT_SELF_DESTRUCT_TOKEN={token}",
            "LOCUS_MANAGER_CONTROL_ENDPOINT=https://manager-controller:8443",
            "LOCUS_OPERATOR_DIAGNOSTICS=1",
        ]
        if os.environ.get("LOCUS_FLOW_AUDIT") == "1":
            environment.append("LOCUS_FLOW_AUDIT=1")
        if os.environ.get("LOCUS_PERFORMANCE_EVIDENCE") == "1":
            environment.append("LOCUS_PERFORMANCE_EVIDENCE=1")
            fixture_id = os.environ.get("LOCUS_PERFORMANCE_FIXTURE_ID")
            if fixture_id:
                environment.append(f"LOCUS_PERFORMANCE_FIXTURE_ID={fixture_id}")
        return {
            "AttachStderr": True,
            "AttachStdout": True,
            "Cmd": [
                "python",
                "-m",
                "locus.managed_client_ui",
                "--root",
                "/role",
                "--port",
                "8080",
            ],
            "Env": environment,
            "ExposedPorts": {"8080/tcp": {}},
            "Healthcheck": {
                "Interval": 2_000_000_000,
                "Retries": 30,
                "StartPeriod": 3_000_000_000,
                "Test": ["CMD", "python", "-m", "locus.managed_client_health"],
                "Timeout": 3_000_000_000,
            },
            "HostConfig": {
                "AutoRemove": False,
                "Binds": [f"{self.client_volume}:/role:ro"],
                "CapDrop": ["ALL"],
                "NetworkMode": first_network,
                "PortBindings": {"8080/tcp": [{"HostIp": "127.0.0.1", "HostPort": ""}]},
                "ReadonlyRootfs": True,
                "SecurityOpt": ["no-new-privileges:true"],
                "Tmpfs": {"/tmp": "rw,noexec,nosuid,nodev,size=16m"},
            },
            "Image": self.image,
            "Labels": {
                CLIENT_ID_LABEL: client_id,
                CLIENT_LABEL: "true",
                CONTROLLER_LABEL: CONTROLLER_PROFILE,
                PROJECT_LABEL: self.project,
                TOKEN_DIGEST_LABEL: hashlib.sha256(token.encode("ascii")).hexdigest(),
            },
            "OpenStdin": False,
            "StopTimeout": 3,
            "Tty": False,
            "User": "65532:65532",
        }

    def create_client(self) -> dict[str, object]:
        with self.lock:
            clients = self._clients()
            running = [
                item
                for item in clients
                if str(item.get("State")) in {"created", "restarting", "running"}
            ]
            if running:
                if len(running) != 1:
                    raise ControllerError("managed client inventory is ambiguous")
                inspected = self.engine.inspect_container(str(running[0].get("Id", "")))
                if inspected.get("Id") != running[0].get("Id"):
                    raise ControllerError("managed client inventory changed")
                self._validate_client_inspection(inspected)
                return self._public_item(running[0])
            if clients:
                raise ControllerError("destroy or restart the existing managed client")
            self._self_destroy_status.clear()
            client_id = f"client-{secrets.token_hex(8)}"
            token = self._token(client_id)
            networks = {name: self._network(name) for name in CLIENT_NETWORKS}
            first = networks["browser-edge"]
            first_name = first.get("Name")
            if not isinstance(first_name, str):
                raise ControllerError("invalid managed network")
            browser_gateway = self._network_gateway(first)
            container_id: str | None = None
            try:
                container_id = self.engine.create_container(
                    name=f"{self.project}-{client_id}",
                    specification=self._client_specification(
                        browser_gateway=browser_gateway,
                        client_id=client_id,
                        token=token,
                        first_network=first_name,
                    ),
                )
                for name in CLIENT_NETWORKS:
                    if name == "browser-edge":
                        continue
                    network_id = networks[name].get("Id")
                    if not isinstance(network_id, str):
                        raise ControllerError("invalid managed network")
                    self.engine.connect_network(network_id, container_id)
                self.engine.start_container(container_id)
                deadline = time.monotonic() + 75
                while time.monotonic() < deadline:
                    inspected = self.engine.inspect_container(container_id)
                    state = inspected.get("State")
                    if isinstance(state, dict):
                        health = state.get("Health")
                        if (
                            isinstance(health, dict)
                            and health.get("Status") == "healthy"
                        ):
                            break
                        if state.get("Status") in {"dead", "exited"}:
                            raise ControllerError("managed client failed to start")
                    time.sleep(0.25)
                else:
                    raise ControllerError("managed client health timed out")
                matches = [
                    item
                    for item in self._clients()
                    if isinstance(item.get("Labels"), dict)
                    and item["Labels"].get(CLIENT_ID_LABEL) == client_id
                ]
                if len(matches) != 1:
                    raise ControllerError("managed client inventory changed")
                inspected = self.engine.inspect_container(str(matches[0].get("Id", "")))
                if inspected.get("Id") != matches[0].get("Id"):
                    raise ControllerError("managed client inventory changed")
                self._validate_client_inspection(inspected)
                return self._public_item(matches[0])
            except BaseException:
                candidates: list[str] = []
                if container_id is not None:
                    candidates.append(container_id)
                else:
                    try:
                        candidates.extend(
                            str(item["Id"])
                            for item in self._clients()
                            if isinstance(item.get("Labels"), dict)
                            and item["Labels"].get(CLIENT_ID_LABEL) == client_id
                        )
                    except (ControllerError, DockerEngineError) as reconcile_error:
                        raise ControllerError(
                            "managed client creation could not be reconciled"
                        ) from reconcile_error
                try:
                    for identifier in set(candidates):
                        self.engine.remove_container(identifier, force=True)
                    if any(
                        isinstance(item.get("Labels"), dict)
                        and item["Labels"].get(CLIENT_ID_LABEL) == client_id
                        for item in self._clients()
                    ):
                        raise ControllerError("managed client creation cleanup failed")
                except (ControllerError, DockerEngineError) as cleanup_error:
                    raise ControllerError(
                        "managed client creation cleanup failed"
                    ) from cleanup_error
                raise

    def _validate_client_inspection(self, inspected: dict[str, Any]) -> None:
        config = inspected.get("Config")
        host = inspected.get("HostConfig")
        mounts = inspected.get("Mounts")
        networks = inspected.get("NetworkSettings")
        labels = config.get("Labels") if isinstance(config, dict) else None
        client_id = labels.get(CLIENT_ID_LABEL) if isinstance(labels, dict) else None
        browser_network = str(self._network("browser-edge")["Name"])
        expected_labels = (
            {
                **IMAGE_METADATA_LABELS,
                CLIENT_ID_LABEL: client_id,
                CLIENT_LABEL: "true",
                CONTROLLER_LABEL: CONTROLLER_PROFILE,
                PROJECT_LABEL: self.project,
                TOKEN_DIGEST_LABEL: hashlib.sha256(
                    self._token(client_id).encode("ascii")
                ).hexdigest(),
            }
            if isinstance(client_id, str)
            else None
        )
        if (
            inspected.get("Image") != self.image
            or not isinstance(config, dict)
            or config.get("Image") != self.image
            or config.get("User") != "65532:65532"
            or config.get("Cmd")
            != [
                "python",
                "-m",
                "locus.managed_client_ui",
                "--root",
                "/role",
                "--port",
                "8080",
            ]
            or config.get("ExposedPorts") != {"8080/tcp": {}}
            or labels != expected_labels
            or not isinstance(host, dict)
            or host.get("AutoRemove") is not False
            or host.get("Binds") != [f"{self.client_volume}:/role:ro"]
            or host.get("ReadonlyRootfs") is not True
            or host.get("CapDrop") != ["ALL"]
            or host.get("NetworkMode") != browser_network
            or host.get("SecurityOpt") != ["no-new-privileges:true"]
            or host.get("Tmpfs") != {"/tmp": "rw,noexec,nosuid,nodev,size=16m"}
            or not isinstance(mounts, list)
        ):
            raise ControllerError("managed client specification changed")
        healthcheck = config.get("Healthcheck")
        if not isinstance(healthcheck, dict) or any(
            healthcheck.get(field) != expected
            for field, expected in {
                "Interval": 2_000_000_000,
                "Retries": 30,
                "StartPeriod": 3_000_000_000,
                "Test": ["CMD", "python", "-m", "locus.managed_client_health"],
                "Timeout": 3_000_000_000,
            }.items()
        ):
            raise ControllerError("managed client healthcheck changed")
        port_bindings = host.get("PortBindings")
        if (
            not isinstance(port_bindings, dict)
            or set(port_bindings) != {"8080/tcp"}
            or not isinstance(port_bindings["8080/tcp"], list)
            or len(port_bindings["8080/tcp"]) != 1
            or not isinstance(port_bindings["8080/tcp"][0], dict)
            or port_bindings["8080/tcp"][0].get("HostIp") != "127.0.0.1"
            or not isinstance(port_bindings["8080/tcp"][0].get("HostPort"), str)
            or (
                port_bindings["8080/tcp"][0]["HostPort"]
                and not port_bindings["8080/tcp"][0]["HostPort"].isdigit()
            )
        ):
            raise ControllerError("managed client port binding changed")
        environment = config.get("Env")
        if not isinstance(environment, list) or not isinstance(client_id, str):
            raise ControllerError("managed client environment changed")
        locus_environment = {
            item.split("=", 1)[0]: item
            for item in environment
            if isinstance(item, str) and item.startswith("LOCUS_") and "=" in item
        }
        expected_environment = {
            "LOCUS_BROWSER_EDGE_GATEWAY": (
                "LOCUS_BROWSER_EDGE_GATEWAY="
                + self._network_gateway(self._network("browser-edge"))
            ),
            "LOCUS_CLIENT_INSTANCE_ID": f"LOCUS_CLIENT_INSTANCE_ID={client_id}",
            "LOCUS_CLIENT_SELF_DESTRUCT_TOKEN": (
                f"LOCUS_CLIENT_SELF_DESTRUCT_TOKEN={self._token(client_id)}"
            ),
            "LOCUS_MANAGER_CONTROL_ENDPOINT": (
                "LOCUS_MANAGER_CONTROL_ENDPOINT=https://manager-controller:8443"
            ),
            "LOCUS_OPERATOR_DIAGNOSTICS": "LOCUS_OPERATOR_DIAGNOSTICS=1",
        }
        if os.environ.get("LOCUS_FLOW_AUDIT") == "1":
            expected_environment["LOCUS_FLOW_AUDIT"] = "LOCUS_FLOW_AUDIT=1"
        if locus_environment != expected_environment:
            raise ControllerError("managed client environment changed")
        role_mounts = [
            item
            for item in mounts
            if isinstance(item, dict) and item.get("Destination") == "/role"
        ]
        if (
            len(mounts) != 1
            or len(role_mounts) != 1
            or role_mounts[0].get("Type") != "volume"
            or role_mounts[0].get("Name") != self.client_volume
            or role_mounts[0].get("RW") is not False
        ):
            raise ControllerError("managed client role mount changed")
        attached = networks.get("Networks") if isinstance(networks, dict) else None
        expected = {str(self._network(name)["Name"]) for name in CLIENT_NETWORKS}
        if not isinstance(attached, dict) or set(attached) != expected:
            raise ControllerError("managed client network membership changed")

    def _locate(self, container_id: object) -> tuple[dict[str, Any], bool]:
        if (
            not isinstance(container_id, str)
            or re.fullmatch(r"[0-9a-f]{64}", container_id) is None
        ):
            raise ControllerError("invalid container identifier")
        inspected = self.engine.inspect_container(container_id)
        config = inspected.get("Config")
        if not isinstance(config, dict) or not isinstance(config.get("Labels"), dict):
            raise ControllerError("invalid managed container")
        labels = config["Labels"]
        if (
            labels.get(PROJECT_LABEL) == self.project
            and labels.get(CLIENT_LABEL) == "true"
        ):
            if labels.get(CONTROLLER_LABEL) != CONTROLLER_PROFILE:
                raise ControllerError("invalid managed client profile")
            client_id = labels.get(CLIENT_ID_LABEL)
            token_digest = labels.get(TOKEN_DIGEST_LABEL)
            if (
                not isinstance(client_id, str)
                or re.fullmatch(r"client-[0-9a-f]{16}", client_id) is None
                or token_digest
                != hashlib.sha256(self._token(client_id).encode("ascii")).hexdigest()
            ):
                raise ControllerError("invalid managed client identity")
            self._validate_client_inspection(inspected)
            return inspected, True
        if labels.get(COMPOSE_PROJECT_LABEL) == self.project:
            matches = [
                item
                for item in self._compose()
                if item.get("Id") == inspected.get("Id")
            ]
            service = labels.get(COMPOSE_SERVICE_LABEL)
            if (
                len(matches) != 1
                or not isinstance(service, str)
                or service in BLOCKED_BASE_ACTIONS
            ):
                raise ControllerError("container action is not permitted")
            return inspected, False
        raise ControllerError("container is outside the managed project")

    def action(self, container_id: object, action: object) -> None:
        if action not in ALLOWED_ACTIONS:
            raise ControllerError("unsupported container action")
        inspected, client = self._locate(container_id)
        exact_id = str(inspected["Id"])
        state_value = inspected.get("State")
        state = state_value.get("Status") if isinstance(state_value, dict) else None
        if (
            state == "running"
            and action not in {"kill", "restart", "stop"}
            or state in {"created", "dead", "exited"}
            and action != "start"
            or state not in {"created", "dead", "exited", "running"}
        ):
            raise ControllerError("container action is invalid for current state")
        if client and action in {"start", "restart"}:
            active_others = [
                item
                for item in self._clients()
                if item.get("Id") != exact_id
                and item.get("State") in {"created", "restarting", "running"}
            ]
            if active_others:
                raise ControllerError("another managed client is active")
        if action == "start":
            self.engine.start_container(exact_id)
        elif action == "stop":
            self.engine.stop_container(exact_id)
        elif action == "restart":
            self.engine.restart_container(exact_id)
        else:
            self.engine.kill_container(exact_id)
        if client:
            config = inspected.get("Config")
            labels = config.get("Labels") if isinstance(config, dict) else None
            client_id = (
                labels.get(CLIENT_ID_LABEL) if isinstance(labels, dict) else None
            )
            if isinstance(client_id, str):
                self._self_destroy_status[client_id] = "ready"

    def destroy_client(self, container_id: object) -> None:
        inspected, client = self._locate(container_id)
        if not client:
            raise ControllerError("only managed clients may be destroyed")
        exact_id = str(inspected["Id"])
        config = inspected.get("Config")
        labels = config.get("Labels") if isinstance(config, dict) else None
        client_id = labels.get(CLIENT_ID_LABEL) if isinstance(labels, dict) else None
        if not isinstance(client_id, str):
            raise ControllerError("invalid managed client identity")
        self.engine.remove_container(exact_id, force=True)
        if any(item.get("Id") == exact_id for item in self._clients()):
            raise ControllerError("managed client remained after destruction")
        self._self_destroy_status[client_id] = "destroyed"

    def _client_by_id(self, client_id: str) -> dict[str, Any]:
        matches = [
            item
            for item in self._clients()
            if isinstance(item.get("Labels"), dict)
            and item["Labels"].get(CLIENT_ID_LABEL) == client_id
        ]
        if len(matches) != 1:
            raise ControllerError("managed client is unavailable")
        return matches[0]

    def schedule_self_destroy(
        self, *, client_id: object, token: object
    ) -> dict[str, object]:
        if (
            not isinstance(client_id, str)
            or not isinstance(token, str)
            or not hmac.compare_digest(token, self._token(client_id))
        ):
            raise ControllerError("invalid self-destruction capability")
        item = self._client_by_id(client_id)
        labels = item.get("Labels")
        if (
            not isinstance(labels, dict)
            or labels.get(TOKEN_DIGEST_LABEL)
            != hashlib.sha256(token.encode("ascii")).hexdigest()
        ):
            raise ControllerError("invalid self-destruction capability")
        container_id = str(item["Id"])

        with self.lock:
            if self._self_destroy_status.get(client_id) == "destroying":
                return {
                    "client_id": client_id,
                    "self_destroy_status": "destroying",
                    "status": "destroying",
                }
            self._self_destroy_status[client_id] = "destroying"

        def destroy() -> None:
            observation_drain = (
                3.0
                if os.environ.get("LOCUS_FLOW_AUDIT") == "1"
                else SELF_DESTROY_INITIAL_DELAY_SECONDS
            )
            time.sleep(observation_drain)
            for attempt in range(SELF_DESTROY_ATTEMPTS):
                try:
                    self.engine.remove_container(container_id, force=True)
                    if any(
                        candidate.get("Id") == container_id
                        for candidate in self._clients()
                    ):
                        raise ControllerError(
                            "managed client remained after self-destruction"
                        )
                except (ControllerError, DockerEngineError):
                    if attempt + 1 < SELF_DESTROY_ATTEMPTS:
                        time.sleep(SELF_DESTROY_RETRY_DELAY_SECONDS)
                        continue
                    with self.lock:
                        if self._self_destroy_status.get(client_id) == "destroying":
                            self._self_destroy_status[client_id] = "failed"
                    return
                with self.lock:
                    self._self_destroy_status[client_id] = "destroyed"
                return

        context = contextvars.copy_context()
        threading.Thread(target=context.run, args=(destroy,), daemon=True).start()
        return {
            "client_id": client_id,
            "self_destroy_status": "destroying",
            "status": "destroying",
        }

    def schedule_system_stop(self) -> dict[str, object]:
        with self.lock:
            if self.shutdown_status == "stopping":
                return {"shutdown_status": "stopping", "status": "stopping"}
            self.shutdown_status = "stopping"

        def stop() -> None:
            time.sleep(SYSTEM_STOP_DELAY_SECONDS)
            try:
                clients = self._clients()
                containers = self._compose()
                try:
                    browser_edge = self._network("browser-edge")
                except ControllerError:
                    browser_edge = None
                manager: list[str] = []
                controller: list[str] = []
                ordinary: list[str] = []
                for item in containers:
                    labels = item.get("Labels", {})
                    identifier = str(item.get("Id", ""))
                    service = (
                        labels.get(COMPOSE_SERVICE_LABEL)
                        if isinstance(labels, dict)
                        else None
                    )
                    if service == "manager-ui":
                        manager.append(identifier)
                    elif service == "manager-controller":
                        controller.append(identifier)
                    else:
                        ordinary.append(identifier)
                for item in clients:
                    self.engine.remove_container(str(item["Id"]), force=True)
                if self._clients():
                    raise ControllerError("managed clients remain during shutdown")
                if browser_edge is not None:
                    self.engine.remove_network(str(browser_edge["Id"]))
                    remaining_browser_edges = self.engine.networks(
                        labels=(
                            f"{COMPOSE_PROJECT_LABEL}={self.project}",
                            "com.docker.compose.network=browser-edge",
                        )
                    )
                    if remaining_browser_edges:
                        raise ControllerError(
                            "managed browser network remained during shutdown"
                        )
                for identifier in ordinary:
                    self.engine.stop_container(identifier)
                    state = self.engine.inspect_container(identifier).get("State")
                    if not isinstance(state, dict) or state.get("Status") not in {
                        "dead",
                        "exited",
                    }:
                        raise ControllerError("managed service did not stop")
                for identifier in [*manager, *controller]:
                    self.engine.stop_container(identifier)
            except Exception:
                with self.lock:
                    self.shutdown_status = "failed"

        context = contextvars.copy_context()
        threading.Thread(target=context.run, args=(stop,), daemon=True).start()
        return {"shutdown_status": "stopping", "status": "stopping"}

    def handle(
        self, path: str, request: dict[str, Any], peer: str
    ) -> tuple[int, dict[str, Any]]:
        if path == "/health":
            return 200, {"role": "manager-controller", "status": "ready"}
        if peer == "manager-ui":
            if path == "/v1/status" and not request:
                return 200, self.status()
            if path == "/v1/client/create":
                parsed = _exact(request, {"operation_id"}, "client-create request")
                operation = _operation_id(parsed["operation_id"])
                return self._mutation(
                    peer=peer,
                    path=path,
                    request=parsed,
                    execute=lambda: (
                        200,
                        {
                            "client": self.create_client(),
                            "operation_id": operation,
                            "status": "created",
                        },
                    ),
                )
            if path == "/v1/container/action":
                parsed = _exact(
                    request,
                    {"action", "container_id", "operation_id"},
                    "action request",
                )
                operation = _operation_id(parsed["operation_id"])

                def action() -> tuple[int, dict[str, Any]]:
                    self.action(parsed["container_id"], parsed["action"])
                    return 200, {
                        "operation_id": operation,
                        "status": "completed",
                    }

                return self._mutation(
                    peer=peer, path=path, request=parsed, execute=action
                )
            if path == "/v1/client/destroy":
                parsed = _exact(
                    request,
                    {"container_id", "operation_id"},
                    "destroy request",
                )
                operation = _operation_id(parsed["operation_id"])

                def destroy_client() -> tuple[int, dict[str, Any]]:
                    self.destroy_client(parsed["container_id"])
                    return 200, {
                        "operation_id": operation,
                        "status": "destroyed",
                    }

                return self._mutation(
                    peer=peer, path=path, request=parsed, execute=destroy_client
                )
            if path == "/v1/system/stop":
                parsed = _exact(request, {"operation_id"}, "system-stop request")
                operation = _operation_id(parsed["operation_id"])

                def stop_system() -> tuple[int, dict[str, Any]]:
                    value = self.schedule_system_stop()
                    value["operation_id"] = operation
                    return 200, value

                return self._mutation(
                    peer=peer, path=path, request=parsed, execute=stop_system
                )
        if peer == "managed-client" and path == "/v1/client/self-destroy":
            parsed = _exact(
                request,
                {"client_id", "operation_id", "token"},
                "self-destroy request",
            )
            operation = _operation_id(parsed["operation_id"])

            def self_destroy() -> tuple[int, dict[str, Any]]:
                value = self.schedule_self_destroy(
                    client_id=parsed["client_id"], token=parsed["token"]
                )
                value["operation_id"] = operation
                return 200, value

            return self._mutation(
                peer=peer, path=path, request=parsed, execute=self_destroy
            )
        raise ControllerError("unsupported controller request")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8443)
    args = parser.parse_args()
    configure_role("manager-controller")
    project = os.environ["LOCUS_DOCKER_PROJECT"]
    controller = ManagedContainerController(
        engine=DockerEngine(),
        project=project,
        image=os.environ["LOCUS_INTEGRATED_IMAGE"],
        client_volume=os.environ["LOCUS_MANAGED_CLIENT_VOLUME"],
        lifecycle_secret=(args.root / "lifecycle-secret.bin").read_bytes(),
    )
    serve_rpc(
        host=args.host, port=args.port, role_root=args.root, handler=controller.handle
    )


if __name__ == "__main__":
    main()
