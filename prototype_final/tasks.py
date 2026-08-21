"""Managed integrated LOCUS prototype command executor."""

from __future__ import annotations

import argparse
import ast
import datetime as dt
import hashlib
import json
import os
import re
import secrets
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import dataclass
from dataclasses import field as dataclass_field
from itertools import combinations
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parent
PYTHON = sys.executable
MANAGED_COMPOSE = ROOT / "deploy" / "compose.managed.yaml"
MANAGED_MANIFEST = ROOT / "deploy" / "managed-manifest.json"
FLOW_COMPOSE = ROOT / "deploy" / "compose.flow-evidence.yaml"
PERFORMANCE_COMPOSE = ROOT / "deploy" / "compose.performance-evidence.yaml"
DEFAULT_PROJECT = "locus-managed-final"
DEFAULT_MANAGER_PORT = 8765
CLIENT_API_VERSION = "LOCUS-client-api-v2"
PACKAGE_MEDIA_TYPE = "application/vnd.locus.recovery-package+json"
IMAGE_ID_PATTERN = re.compile(r"sha256:[0-9a-f]{64}\Z")
PROJECT_PATTERN = re.compile(r"[a-z0-9][a-z0-9-]{0,47}\Z")
_FLOW_EVIDENCE_ACTIVE = False
_PERFORMANCE_EVIDENCE_ACTIVE = False
_PERFORMANCE_INSTRUMENTATION_ID = "LOCUS-managed-performance-instrumentation-v1"
_FLOW_CONTEXT = ""
_FLOW_HOST_EVENTS: list[dict[str, object]] = []
_FLOW_HOST_SEQUENCE = 0
_FLOW_HOST_BOOT = secrets.token_hex(8)


@dataclass
class _PerformanceRuntime:
    project: str
    manager_port: int
    manager_csrf: str
    environment: dict[str, str]
    base_bindings: dict[str, object]
    host_id: str
    client: dict[str, object] | None = None
    client_port: int | None = None
    client_session: dict[str, object] | None = None
    client_csrf: str | None = None
    base_package: bytes | None = None
    secret_markers: list[str] = dataclass_field(default_factory=list)


def _operation_id(prefix: str) -> str:
    return f"{prefix}-{secrets.token_hex(12)}"


def run(command: Sequence[str], *, env: dict[str, str] | None = None) -> None:
    """Run one visible project command and fail on a non-zero exit."""

    print("+", subprocess.list2cmdline(list(command)), flush=True)
    subprocess.run(list(command), cwd=ROOT, check=True, env=env)


def run_capture(
    command: Sequence[str],
    *,
    env: dict[str, str] | None = None,
    check: bool = True,
    include_stderr: bool = False,
    visible: bool = True,
) -> str:
    """Run one command while retaining bounded diagnostic output in memory."""

    if visible:
        print("+", subprocess.list2cmdline(list(command)), flush=True)
    result = subprocess.run(
        list(command),
        cwd=ROOT,
        check=False,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if check and result.returncode != 0:
        raise subprocess.CalledProcessError(result.returncode, list(command))
    return result.stdout + (result.stderr if include_stderr else "")


def require(executable: str) -> str:
    path = shutil.which(executable)
    if path is None:
        raise SystemExit(
            f"Required executable '{executable}' was not found on PATH. "
            "See README.md for prerequisites."
        )
    return path


def _project(value: str) -> str:
    if PROJECT_PATTERN.fullmatch(value) is None:
        raise argparse.ArgumentTypeError(
            "project must be 1-48 lowercase letters, digits, or hyphens"
        )
    return value


def _port(value: str) -> int:
    try:
        port = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("port must be an integer") from exc
    if not 1 <= port <= 65535:
        raise argparse.ArgumentTypeError("port must be between 1 and 65535")
    return port


def _free_loopback_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def _environment(project: str, manager_port: int) -> dict[str, str]:
    seed = hashlib.sha256(f"LOCUS managed local {project}".encode()).hexdigest()
    environment = os.environ.copy()
    environment.update(
        {
            "COMPOSE_PROJECT_NAME": project,
            "LOCUS_INTEGRATED_IMAGE": f"locus-managed-{project}:local",
            "LOCUS_INTEGRATED_IMAGE_ID": "sha256:" + "0" * 64,
            "LOCUS_MANAGER_PORT": str(manager_port),
            "LOCUS_S3_ACCESS_KEY": f"local-{seed[:24]}",
            "LOCUS_S3_BUCKET": f"locus-{seed[:20]}",
            "LOCUS_S3_SECRET_KEY": seed,
        }
    )
    return environment


def _compose(project: str) -> list[str]:
    command = [
        require("docker"),
        "compose",
        "--project-name",
        project,
        "--file",
        str(MANAGED_COMPOSE),
    ]
    if _PERFORMANCE_EVIDENCE_ACTIVE:
        command.extend(["--file", str(PERFORMANCE_COMPOSE)])
    elif _FLOW_EVIDENCE_ACTIVE:
        command.extend(["--file", str(FLOW_COMPOSE)])
    return command


@contextmanager
def _flow_context(value: str) -> Any:
    global _FLOW_CONTEXT
    previous = _FLOW_CONTEXT
    _FLOW_CONTEXT = (
        value if (_FLOW_EVIDENCE_ACTIVE or _PERFORMANCE_EVIDENCE_ACTIVE) else ""
    )
    try:
        yield
    finally:
        _FLOW_CONTEXT = previous


def _networks(raw: object, label: str) -> set[str]:
    if not isinstance(raw, dict):
        raise RuntimeError(f"invalid network membership for {label}")
    return set(raw)


def _validate_managed_compose(value: dict[str, object]) -> None:
    services = value.get("services")
    expected_services = {
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
    if not isinstance(services, dict) or set(services) != expected_services:
        raise RuntimeError("managed Compose has an unexpected static service set")
    networks = value.get("networks")
    expected_static_networks = {
        "admission",
        "client-lifecycle",
        "cloud",
        "control",
        "manager-edge",
        "management",
        "recovery",
        "resolver",
        "storage",
    }
    if not isinstance(networks, dict) or set(networks) != expected_static_networks:
        raise RuntimeError("managed Compose static networks are not exact")
    for logical_name, raw in networks.items():
        if not isinstance(raw, dict):
            raise RuntimeError("invalid managed network")
        expected_internal = logical_name != "manager-edge"
        if raw.get("internal", False) is not expected_internal:
            raise RuntimeError(f"managed network is not internal: {logical_name}")

    expected_membership = {
        "admission": {"admission"},
        "manager-controller": {"client-lifecycle", "management"},
        "manager-ui": {"management", "manager-edge"},
        "operator": {"control"},
        "resolver": {"resolver"},
        "s3": {"cloud"},
        "storage-gateway": {"cloud", "storage"},
        **{f"party{index}": {"recovery"} for index in range(1, 6)},
    }
    socket_holders: list[str] = []
    for name, raw in services.items():
        if not isinstance(raw, dict):
            raise RuntimeError("invalid managed service")
        if raw.get("read_only") is not True:
            raise RuntimeError(f"managed service root is writable: {name}")
        if raw.get("security_opt") != ["no-new-privileges:true"]:
            raise RuntimeError(f"managed service lacks no-new-privileges: {name}")
        if name == "bootstrap":
            if raw.get("network_mode") != "none" or raw.get("networks") not in (
                None,
                {},
            ):
                raise RuntimeError("managed bootstrap is not networkless")
            if raw.get("cap_add") != ["CHOWN", "DAC_READ_SEARCH"]:
                raise RuntimeError("managed bootstrap capabilities are not exact")
        elif _networks(raw.get("networks"), name) != expected_membership[name]:
            raise RuntimeError(f"invalid managed network membership: {name}")
        elif name == "s3" and raw.get("cap_add") != ["CHOWN", "SETGID", "SETUID"]:
            raise RuntimeError("managed provider capabilities are not exact")
        elif name != "s3" and raw.get("cap_add") not in (None, []):
            raise RuntimeError(f"managed runtime gained capabilities: {name}")

        ports = raw.get("ports")
        if name == "manager-ui":
            if (
                not isinstance(ports, list)
                or len(ports) != 1
                or not isinstance(ports[0], dict)
                or ports[0].get("host_ip") != "127.0.0.1"
                or ports[0].get("target") != 8080
            ):
                raise RuntimeError("Manager UI is not loopback-only")
        elif ports not in (None, []):
            raise RuntimeError(f"internal service publishes a host port: {name}")

        mounts = raw.get("volumes", [])
        if not isinstance(mounts, list):
            raise RuntimeError("invalid managed service mounts")
        for mount in mounts:
            if not isinstance(mount, dict):
                raise RuntimeError("invalid managed service mount")
            source = str(mount.get("source", ""))
            target = str(mount.get("target", ""))
            if source in {
                "/var/run/docker.sock",
                r"\\.\pipe\docker_engine",
            } or target in {
                "/var/run/docker.sock",
                r"\\.\pipe\docker_engine",
            }:
                if (
                    name != "manager-controller"
                    or mount.get("type") != "bind"
                    or source != "/var/run/docker.sock"
                    or target != "/var/run/docker.sock"
                    or mount.get("read_only") is not True
                ):
                    raise RuntimeError(
                        "Docker socket escaped the exact controller mount"
                    )
                socket_holders.append(name)
    if socket_holders != ["manager-controller"]:
        raise RuntimeError("exactly one controller must hold the Docker socket")


def integrated_config() -> None:
    source_path = str(ROOT)
    if source_path not in sys.path:
        sys.path.insert(0, source_path)
    from locus.managed_manifest import load_managed_manifest

    manifest = load_managed_manifest(MANAGED_MANIFEST)
    project = "locus-managed-config"
    environment = _environment(project, DEFAULT_MANAGER_PORT)
    configured = json.loads(
        run_capture([*_compose(project), "config", "--format", "json"], env=environment)
    )
    if not isinstance(configured, dict):
        raise RuntimeError("managed Compose did not resolve to an object")
    _validate_managed_compose(cast(dict[str, object], configured))
    print(
        json.dumps(
            {
                "deployment_id": manifest["deployment_id"],
                "dynamic_clients": 0,
                "graphs": 1,
                "status": "valid",
            },
            sort_keys=True,
        )
    )


def _image_id(environment: dict[str, str]) -> str:
    image = run_capture(
        [
            require("docker"),
            "image",
            "inspect",
            "--format",
            "{{.Id}}",
            environment["LOCUS_INTEGRATED_IMAGE"],
        ],
        env=environment,
    ).strip()
    if IMAGE_ID_PATTERN.fullmatch(image) is None:
        raise RuntimeError("managed image did not resolve to an immutable image ID")
    return image


def _browser_edge_name(project: str) -> str:
    return f"{project}_browser-edge"


def _browser_edge_inspection(
    project: str, environment: dict[str, str]
) -> dict[str, object] | None:
    output = run_capture(
        [require("docker"), "network", "inspect", _browser_edge_name(project)],
        env=environment,
        check=False,
    )
    if not output.strip():
        return None
    value = json.loads(output)
    if value == []:
        return None
    if not isinstance(value, list) or len(value) != 1 or not isinstance(value[0], dict):
        raise RuntimeError("invalid browser-edge network inspection")
    return cast(dict[str, object], value[0])


def _validate_browser_edge_network(project: str, value: dict[str, object]) -> None:
    labels = value.get("Labels")
    if (
        value.get("Name") != _browser_edge_name(project)
        or value.get("Driver") != "bridge"
        or value.get("Internal") is not False
        or not isinstance(labels, dict)
        or labels.get("com.docker.compose.project") != project
        or labels.get("com.docker.compose.network") != "browser-edge"
        or labels.get("com.locus.managed-network") != "true"
    ):
        raise RuntimeError("browser-edge network is outside the managed project")


def _ensure_browser_edge_network(project: str, environment: dict[str, str]) -> None:
    observed = _browser_edge_inspection(project, environment)
    if observed is None:
        run(
            [
                require("docker"),
                "network",
                "create",
                "--driver",
                "bridge",
                "--label",
                f"com.docker.compose.project={project}",
                "--label",
                "com.docker.compose.network=browser-edge",
                "--label",
                "com.locus.managed-network=true",
                _browser_edge_name(project),
            ],
            env=environment,
        )
        observed = _browser_edge_inspection(project, environment)
    if observed is None:
        raise RuntimeError("browser-edge network was not created")
    _validate_browser_edge_network(project, observed)


def _remove_browser_edge_network(project: str, environment: dict[str, str]) -> None:
    observed = _browser_edge_inspection(project, environment)
    if observed is None:
        return
    _validate_browser_edge_network(project, observed)
    run(
        [require("docker"), "network", "rm", _browser_edge_name(project)],
        env=environment,
    )


def _dynamic_client_ids(project: str, environment: dict[str, str]) -> list[str]:
    output = run_capture(
        [
            require("docker"),
            "ps",
            "--all",
            "--quiet",
            "--filter",
            f"label=com.locus.project={project}",
            "--filter",
            "label=com.locus.managed-client=true",
        ],
        env=environment,
    )
    return [line for line in output.splitlines() if line]


def _validate_dynamic_client(
    container_id: str, project: str, environment: dict[str, str]
) -> None:
    encoded = run_capture([require("docker"), "inspect", container_id], env=environment)
    value = json.loads(encoded)
    if not isinstance(value, list) or len(value) != 1 or not isinstance(value[0], dict):
        raise RuntimeError("invalid managed-client inspection")
    inspected = value[0]
    config = inspected.get("Config")
    labels = config.get("Labels") if isinstance(config, dict) else None
    client_id = labels.get("com.locus.client-id") if isinstance(labels, dict) else None
    if (
        not isinstance(labels, dict)
        or labels.get("com.locus.project") != project
        or labels.get("com.locus.managed-client") != "true"
        or labels.get("com.locus.controller-profile")
        != "LOCUS-local-container-controller-v1"
        or not isinstance(client_id, str)
        or inspected.get("Name") != f"/{project}-{client_id}"
    ):
        raise RuntimeError("container is outside the exact managed-client scope")


def _container_inspection(
    container_id: str, environment: dict[str, str]
) -> dict[str, Any]:
    encoded = run_capture([require("docker"), "inspect", container_id], env=environment)
    try:
        values = json.loads(encoded)
    except (json.JSONDecodeError, TypeError) as exc:
        raise RuntimeError("Docker returned an invalid container inspection") from exc
    if (
        not isinstance(values, list)
        or len(values) != 1
        or not isinstance(values[0], dict)
    ):
        raise RuntimeError("Docker returned an ambiguous container inspection")
    return cast(dict[str, Any], values[0])


def _assert_live_control_isolation(
    *,
    project: str,
    client: dict[str, object],
    environment: dict[str, str],
) -> None:
    """Prove the two browser UIs lack Docker and Manager/Client reachability."""

    client_id = client.get("id")
    public_client_id = client.get("client_id")
    if not isinstance(client_id, str) or not isinstance(public_client_id, str):
        raise RuntimeError("managed Client identity is unavailable")
    service_ids: dict[str, str] = {}
    for service in ("manager-controller", "manager-ui"):
        identifier = run_capture(
            [*_compose(project), "ps", "--quiet", service], env=environment
        ).strip()
        if not identifier:
            raise RuntimeError(f"managed isolation role is unavailable: {service}")
        service_ids[service] = identifier
    inspections = {
        "client": _container_inspection(client_id, environment),
        "manager-controller": _container_inspection(
            service_ids["manager-controller"], environment
        ),
        "manager-ui": _container_inspection(service_ids["manager-ui"], environment),
    }
    expected_networks = {
        "client": {
            f"{project}_admission",
            f"{project}_browser-edge",
            f"{project}_client-lifecycle",
            f"{project}_control",
            f"{project}_recovery",
            f"{project}_resolver",
            f"{project}_storage",
        },
        "manager-controller": {
            f"{project}_client-lifecycle",
            f"{project}_management",
        },
        "manager-ui": {f"{project}_management", f"{project}_manager-edge"},
    }
    for role, inspection in inspections.items():
        network_settings = inspection.get("NetworkSettings")
        networks = (
            network_settings.get("Networks")
            if isinstance(network_settings, dict)
            else None
        )
        if not isinstance(networks, dict) or set(networks) != expected_networks[role]:
            raise RuntimeError(f"managed live network isolation changed: {role}")
        mounts = inspection.get("Mounts")
        if not isinstance(mounts, list):
            raise RuntimeError(f"managed mount inventory is unavailable: {role}")
        socket_mounts = [
            item
            for item in mounts
            if isinstance(item, dict)
            and item.get("Destination") == "/var/run/docker.sock"
        ]
        if (role == "manager-controller" and len(socket_mounts) != 1) or (
            role != "manager-controller" and socket_mounts
        ):
            raise RuntimeError(f"managed Docker-socket scope changed: {role}")
    probes = (
        (client_id, "manager-ui", 8443),
        (
            service_ids["manager-ui"],
            f"{project}-{public_client_id}",
            8080,
        ),
    )
    for container_id, hostname, port in probes:
        script = (
            "from pathlib import Path\n"
            "import socket\n"
            "if Path('/var/run/docker.sock').exists(): raise SystemExit(2)\n"
            f"try: socket.getaddrinfo({hostname!r}, {port})\n"
            "except socket.gaierror: raise SystemExit(0)\n"
            "raise SystemExit(3)\n"
        )
        run(
            [require("docker"), "exec", container_id, "python", "-c", script],
            env=environment,
        )


def _remove_dynamic_clients(project: str, environment: dict[str, str]) -> int:
    identifiers = _dynamic_client_ids(project, environment)
    for identifier in identifiers:
        _validate_dynamic_client(identifier, project, environment)
        run(
            [require("docker"), "rm", "--force", "--volumes", identifier],
            env=environment,
        )
    return len(identifiers)


def _raw_request(
    port: int,
    path: str,
    *,
    method: str = "GET",
    body: bytes | None = None,
    content_type: str | None = None,
    csrf: str | None = None,
    expected: tuple[int, ...] = (200,),
    retries: int = 1,
) -> tuple[bytes, Any]:
    headers = {"Accept": "application/json"}
    if _FLOW_CONTEXT:
        from locus.flow_audit import FLOW_HEADER

        headers[FLOW_HEADER] = _FLOW_CONTEXT
    if body is not None:
        if content_type is None:
            raise RuntimeError("HTTP body requires an exact content type")
        headers["Content-Type"] = content_type
    if csrf is not None:
        headers["X-LOCUS-CSRF"] = csrf
        headers["Origin"] = f"http://127.0.0.1:{port}"
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}",
        data=body,
        headers=headers,
        method=method,
    )
    last_error: BaseException | None = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(request, timeout=130) as response:  # noqa: S310
                maximum = 4 * 1024 * 1024
                encoded = response.read(maximum + 1)
                if len(encoded) > maximum:
                    raise RuntimeError("managed UI response exceeded its bound")
                status = response.status
                response_headers = response.headers
        except urllib.error.HTTPError as error:
            encoded = error.read(512 * 1024 + 1)
            status = error.code
            response_headers = error.headers
        except (urllib.error.URLError, ConnectionError, TimeoutError) as error:
            last_error = error
            if attempt + 1 == retries:
                raise
            time.sleep(0.25)
            continue
        if status not in expected:
            raise RuntimeError(f"managed UI returned HTTP {status} for {path}")
        if _FLOW_CONTEXT:
            global _FLOW_HOST_SEQUENCE
            from locus.flow_audit import TRACE_POLICY_ID, http_category

            receiver = (
                "manager-ui" if path.startswith("/api/manager/") else "managed-client"
            )
            _FLOW_HOST_SEQUENCE += 1
            _FLOW_HOST_EVENTS.append(
                {
                    "boot": _FLOW_HOST_BOOT,
                    "category": http_category(receiver, path),
                    "context": _FLOW_CONTEXT,
                    "observation": "sender",
                    "receiver": receiver,
                    "request_bytes": 0 if body is None else len(body),
                    "response_bytes": len(encoded),
                    "result": "success"
                    if 200 <= status < 300
                    else ("unavailable" if status >= 500 else "rejected"),
                    "sender": "browser",
                    "sequence": _FLOW_HOST_SEQUENCE,
                    "trace_policy_id": TRACE_POLICY_ID,
                }
            )
        return encoded, response_headers
    assert last_error is not None
    raise last_error


def _json_request(
    port: int,
    path: str,
    value: dict[str, object] | None = None,
    *,
    csrf: str | None = None,
    expected: tuple[int, ...] = (200,),
    retries: int = 1,
) -> dict[str, object]:
    body = (
        None
        if value is None
        else json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    )
    encoded, _headers = _raw_request(
        port,
        path,
        method="GET" if body is None else "POST",
        body=body,
        content_type=None if body is None else "application/json",
        csrf=csrf,
        expected=expected,
        retries=retries,
    )
    try:
        result = json.loads(encoded)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("managed UI returned invalid JSON") from exc
    if not isinstance(result, dict):
        raise RuntimeError("managed UI returned a non-object")
    return cast(dict[str, object], result)


def _manager_session(port: int, *, retries: int = 1) -> str:
    result = _json_request(port, "/api/manager/v1/session", retries=retries)
    token = result.get("csrf_token")
    if result.get("status") != "ready" or not isinstance(token, str):
        raise RuntimeError("Manager UI session is unavailable")
    return token


def _assert_ui_assets(
    port: int, *, html_marker: bytes, script_path: str, style_path: str
) -> None:
    """Verify that the built runtime image contains one complete browser UI."""

    expected = (
        ("/", "text/html", html_marker),
        (script_path, "text/javascript", b'"use strict"'),
        (style_path, "text/css", b"{"),
    )
    for path, media_type, marker in expected:
        body, headers = _raw_request(port, path, retries=20)
        if headers.get_content_type() != media_type or marker not in body:
            raise RuntimeError(f"managed UI asset is missing or invalid: {path}")


def _manager_status(port: int) -> dict[str, object]:
    return _json_request(port, "/api/manager/v1/status")


def _manager_post(
    port: int,
    csrf: str,
    path: str,
    value: dict[str, object],
    *,
    expected: tuple[int, ...] = (200,),
) -> dict[str, object]:
    return _json_request(port, path, value, csrf=csrf, expected=expected)


def _stop_through_manager(port: int, csrf: str, *, label: str) -> None:
    result = _manager_post(
        port,
        csrf,
        "/api/manager/v1/system-stop",
        {"operation_id": _operation_id(label)},
        expected=(202,),
    )
    if result.get("shutdown_status") != "stopping":
        raise RuntimeError("Manager did not acknowledge the system stop")
    with _flow_context(""):
        deadline = time.monotonic() + 75
        while time.monotonic() < deadline:
            try:
                status = _manager_status(port)
            except (urllib.error.URLError, ConnectionError, TimeoutError):
                return
            if status.get("shutdown_status") == "failed":
                raise RuntimeError("Manager reported a failed system stop")
            time.sleep(0.25)
    raise RuntimeError("Manager stop did not make the system unavailable")


def _wait_project_stopped(
    project: str, environment: dict[str, str], *, timeout: float = 90
) -> None:
    """Wait until the asynchronous Manager shutdown has stopped every static role."""

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        running = run_capture(
            [
                require("docker"),
                "ps",
                "--filter",
                f"label=com.docker.compose.project={project}",
                "--format",
                "{{.ID}}",
            ],
            env=environment,
            visible=False,
        ).strip()
        if not running:
            return
        time.sleep(0.25)
    raise RuntimeError("Manager shutdown left a static role running")


def _wait_role(
    port: int,
    role: str,
    *,
    state: str,
    healthy: bool = False,
    timeout: float = 45,
) -> dict[str, object]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        status = _manager_status(port)
        containers = status.get("containers")
        if isinstance(containers, list):
            for raw in containers:
                if (
                    isinstance(raw, dict)
                    and raw.get("role") == role
                    and raw.get("state") == state
                    and (not healthy or "healthy" in str(raw.get("health", "")))
                ):
                    return cast(dict[str, object], raw)
        time.sleep(0.25)
    raise RuntimeError(f"managed role did not reach {state}: {role}")


def _manager_action(port: int, csrf: str, role: str, action: str) -> dict[str, object]:
    status = _manager_status(port)
    containers = status.get("containers")
    if not isinstance(containers, list):
        raise RuntimeError("Manager status omitted containers")
    matches = [
        item
        for item in containers
        if isinstance(item, dict) and item.get("role") == role
    ]
    if len(matches) != 1 or not isinstance(matches[0].get("id"), str):
        raise RuntimeError(f"Manager role inventory is ambiguous: {role}")
    _manager_post(
        port,
        csrf,
        "/api/manager/v1/container-action",
        {
            "action": action,
            "container_id": cast(str, matches[0]["id"]),
            "operation_id": _operation_id(f"smoke-{role}-{action}"),
        },
    )
    return cast(dict[str, object], matches[0])


def _start_project(
    *,
    project: str,
    manager_port: int,
    environment: dict[str, str],
    startup_timing: list[int] | None = None,
    build_image: bool = True,
) -> dict[str, object]:
    if _dynamic_client_ids(project, environment):
        raise RuntimeError(
            "an orphaned managed client exists; run integrated-stop for this project"
        )
    command = _compose(project)
    if build_image:
        run(
            [
                require("docker"),
                "build",
                "--file",
                str(ROOT / "deploy" / "Dockerfile"),
                "--tag",
                environment["LOCUS_INTEGRATED_IMAGE"],
                str(ROOT),
            ],
            env=environment,
        )
    environment["LOCUS_INTEGRATED_IMAGE_ID"] = _image_id(environment)
    startup_started = time.perf_counter_ns()
    _ensure_browser_edge_network(project, environment)
    run(
        [
            *command,
            "up",
            "--detach",
            "--no-build",
            "--wait",
            "--wait-timeout",
            "120",
        ],
        env=environment,
    )
    _manager_session(manager_port, retries=80)
    _assert_ui_assets(
        manager_port,
        html_marker=b"LOCUS Manager",
        script_path="/assets/manager.js",
        style_path="/assets/manager.css",
    )
    status = _manager_status(manager_port)
    containers = status.get("containers")
    if not isinstance(containers, list) or any(
        isinstance(item, dict) and item.get("role") == "client" for item in containers
    ):
        raise RuntimeError("managed startup created an unexpected client")
    if startup_timing is not None:
        startup_timing.append(time.perf_counter_ns() - startup_started)
    return status


def _resume_project(
    *, project: str, manager_port: int, environment: dict[str, str]
) -> tuple[dict[str, object], str]:
    """Restart an intentionally stopped project without rebuilding or resetting state."""

    if _dynamic_client_ids(project, environment):
        raise RuntimeError("managed restart found an unexpected Client")
    _ensure_browser_edge_network(project, environment)
    run(
        [
            *_compose(project),
            "up",
            "--detach",
            "--no-build",
            "--wait",
            "--wait-timeout",
            "120",
        ],
        env=environment,
    )
    csrf = _manager_session(manager_port, retries=80)
    status = _manager_status(manager_port)
    containers = status.get("containers")
    if not isinstance(containers, list) or len(containers) != 13:
        raise RuntimeError("managed restart did not restore the exact static inventory")
    if any(
        isinstance(item, dict) and item.get("role") == "client" for item in containers
    ):
        raise RuntimeError("managed restart created an unexpected Client")
    return status, csrf


def integrated_start(args: argparse.Namespace) -> None:
    integrated_config()
    environment = _environment(args.project, args.port)
    status = _start_project(
        project=args.project, manager_port=args.port, environment=environment
    )
    containers = status.get("containers")
    print(
        json.dumps(
            {
                "clients": 0,
                "manager_url": f"http://127.0.0.1:{args.port}/",
                "project": args.project,
                "static_containers": len(containers)
                if isinstance(containers, list)
                else 0,
                "status": "ready",
            },
            sort_keys=True,
        )
    )


def integrated_stop(args: argparse.Namespace) -> None:
    """Emergency/orphan cleanup; normal shutdown belongs to the Manager UI."""

    environment = _environment(args.project, DEFAULT_MANAGER_PORT)
    removed = _remove_dynamic_clients(args.project, environment)
    command = [*_compose(args.project), "down", "--remove-orphans"]
    if args.reset_state:
        command.append("--volumes")
    run(command, env=environment)
    _remove_browser_edge_network(args.project, environment)
    print(
        json.dumps(
            {
                "clients_removed": removed,
                "project": args.project,
                "role_volumes": "removed" if args.reset_state else "preserved",
                "status": "stopped",
            },
            sort_keys=True,
        )
    )


def _create_client(manager_port: int, manager_csrf: str) -> dict[str, object]:
    result = _manager_post(
        manager_port,
        manager_csrf,
        "/api/manager/v1/clients",
        {"operation_id": _operation_id("smoke-create-client")},
        expected=(201,),
    )
    client = result.get("client")
    if (
        result.get("status") != "created"
        or not isinstance(client, dict)
        or not isinstance(client.get("port"), int)
        or not isinstance(client.get("client_id"), str)
        or not isinstance(client.get("id"), str)
    ):
        raise RuntimeError("Manager did not create one valid client")
    return cast(dict[str, object], client)


def _create_client_concurrently(
    manager_port: int, manager_csrf: str
) -> dict[str, object]:
    """Prove that simultaneous exact retries create one managed Client."""

    operation_id = _operation_id("smoke-concurrent-create-client")

    def create() -> dict[str, object]:
        return _manager_post(
            manager_port,
            manager_csrf,
            "/api/manager/v1/clients",
            {"operation_id": operation_id},
            expected=(201,),
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _index: create(), range(2)))
    if results[0] != results[1]:
        raise RuntimeError("simultaneous client creation changed its exact outcome")
    client = results[0].get("client")
    if (
        results[0].get("status") != "created"
        or not isinstance(client, dict)
        or not isinstance(client.get("port"), int)
        or not isinstance(client.get("client_id"), str)
        or not isinstance(client.get("id"), str)
    ):
        raise RuntimeError("simultaneous client creation returned an invalid result")
    status = _manager_status(manager_port)
    containers = status.get("containers")
    if not isinstance(containers, list):
        raise RuntimeError("Manager omitted its inventory after simultaneous creation")
    matching = [
        item
        for item in containers
        if isinstance(item, dict) and item.get("client_id") == client["client_id"]
    ]
    if len(matching) != 1 or matching[0].get("id") != client["id"]:
        raise RuntimeError("simultaneous client creation produced ambiguous inventory")
    return cast(dict[str, object], client)


def _reject_stale_lifecycle_request(manager_port: int, manager_csrf: str) -> None:
    result = _manager_post(
        manager_port,
        manager_csrf,
        "/api/manager/v1/container-action",
        {
            "action": "restart",
            "container_id": "0" * 64,
            "operation_id": _operation_id("smoke-stale-container"),
        },
        expected=(400,),
    )
    if result != {"category": "operation_rejected", "status": "rejected"}:
        raise RuntimeError("stale lifecycle request did not fail closed")


def _client_session(client_port: int, *, retries: int = 80) -> dict[str, object]:
    result = _json_request(client_port, "/api/v2/session", retries=retries)
    if (
        result.get("status") != "ready"
        or result.get("api_version") != CLIENT_API_VERSION
        or not isinstance(result.get("csrf_token"), str)
        or not isinstance(result.get("client_identity"), str)
    ):
        raise RuntimeError("managed Client session is unavailable")
    return result


def _client_post(
    client_port: int,
    csrf: str,
    path: str,
    value: dict[str, object],
    *,
    expected: tuple[int, ...] = (200,),
) -> dict[str, object]:
    return _json_request(client_port, path, value, csrf=csrf, expected=expected)


def _client_package_export(client_port: int, csrf: str, download_id: str) -> bytes:
    body = json.dumps(
        {"api_version": CLIENT_API_VERSION, "download_id": download_id},
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    package, headers = _raw_request(
        client_port,
        "/api/v2/package/export",
        method="POST",
        body=body,
        content_type="application/json",
        csrf=csrf,
    )
    if headers.get_content_type() != PACKAGE_MEDIA_TYPE:
        raise RuntimeError("Client exported the wrong package media type")
    return package


def _client_package_import(
    client_port: int,
    csrf: str,
    package: bytes,
    *,
    expected: tuple[int, ...] = (200,),
) -> dict[str, object]:
    encoded, _headers = _raw_request(
        client_port,
        "/api/v2/package/import",
        method="POST",
        body=package,
        content_type=PACKAGE_MEDIA_TYPE,
        csrf=csrf,
        expected=expected,
    )
    value = json.loads(encoded)
    if not isinstance(value, dict):
        raise RuntimeError("Client package import returned a non-object")
    return cast(dict[str, object], value)


def _wait_client_removed(manager_port: int, client_port: int) -> None:
    deadline = time.monotonic() + 20
    unavailable = False
    empty = False
    while time.monotonic() < deadline:
        try:
            _raw_request(client_port, "/healthz", retries=1)
        except (urllib.error.URLError, ConnectionError, TimeoutError):
            unavailable = True
        status = _manager_status(manager_port)
        containers = status.get("containers")
        empty = isinstance(containers, list) and not any(
            isinstance(item, dict) and item.get("role") == "client"
            for item in containers
        )
        if unavailable and empty:
            return
        time.sleep(0.25)
    raise RuntimeError("destroyed Client remained reachable or inventoried")


def _policy_inputs() -> dict[str, object]:
    return {
        "LOCUS-canonical-email-set-v1": [
            "Ada@Example.COM",
            "grace@example.net",
            "linus@example.org",
        ],
        "LOCUS-canonical-phone-set-v1": [
            "+352621000001",
            "+352621000002",
            "+352621000003",
        ],
        "LOCUS-location-person-set-v1": [
            {
                "location": {"latitude": "49.6116", "longitude": "6.1319"},
                "person": {"type": "email", "value": "Ada@Example.COM"},
            },
            {
                "location": {"latitude": "48.8566", "longitude": "2.3522"},
                "person": {"type": "phone", "value": "+352621000002"},
            },
            {
                "location": {"latitude": "51.5074", "longitude": "-0.1278"},
                "person": {"type": "email", "value": "linus@example.org"},
            },
        ],
        "LOCUS-quantized-coordinate-set-v1": [
            {"latitude": "49.61160001", "longitude": "6.13190001"},
            {"latitude": "48.8566", "longitude": "2.3522"},
            {"latitude": "51.5074", "longitude": "-0.1278"},
        ],
    }


def _exercise_manager_actions(port: int, csrf: str) -> None:
    _manager_action(port, csrf, "resolver", "stop")
    _wait_role(port, "resolver", state="exited")
    _manager_action(port, csrf, "resolver", "start")
    _wait_role(port, "resolver", state="running", healthy=True)
    _manager_action(port, csrf, "resolver", "restart")
    _wait_role(port, "resolver", state="running", healthy=True)
    _manager_action(port, csrf, "resolver", "kill")
    _wait_role(port, "resolver", state="exited")
    _manager_action(port, csrf, "resolver", "start")
    _wait_role(port, "resolver", state="running", healthy=True)


def _exercise_client_process_actions(
    manager_port: int,
    manager_csrf: str,
    client_port: int,
    initial_session: dict[str, object],
    stale_csrf: str,
    stale_download_id: str,
) -> tuple[dict[str, object], int]:
    """Show that process lifecycle erases volatile state but not container identity."""

    client_id = initial_session.get("client_id")
    identities = {initial_session.get("client_identity")}
    sequence = (("stop", False), ("start", True), ("restart", True), ("kill", False))
    latest = initial_session
    current_port = client_port
    for action, becomes_running in sequence:
        _manager_action(manager_port, manager_csrf, "client", action)
        if becomes_running:
            item = _wait_role(manager_port, "client", state="running", healthy=True)
            if not isinstance(item.get("port"), int):
                raise RuntimeError("Client process transition lost its loopback port")
            current_port = cast(int, item["port"])
            latest = _client_session(current_port)
            if (
                latest.get("client_id") != client_id
                or latest.get("key_loaded") is not False
            ):
                raise RuntimeError("Client process transition preserved invalid state")
            identities.add(latest.get("client_identity"))
        else:
            _wait_role(manager_port, "client", state="exited")
    _manager_action(manager_port, manager_csrf, "client", "start")
    item = _wait_role(manager_port, "client", state="running", healthy=True)
    if not isinstance(item.get("port"), int):
        raise RuntimeError("Client process transition lost its loopback port")
    current_port = cast(int, item["port"])
    latest = _client_session(current_port)
    if latest.get("client_id") != client_id or latest.get("key_loaded") is not False:
        raise RuntimeError("Client process transition preserved invalid state")
    identities.add(latest.get("client_identity"))
    if len(identities) != 4:
        raise RuntimeError("Client process transitions did not rotate proof identity")
    current_csrf = latest.get("csrf_token")
    if not isinstance(current_csrf, str):
        raise RuntimeError("restarted Client omitted its fresh CSRF token")
    stale_csrf_result = _client_post(
        current_port,
        stale_csrf,
        "/api/v2/key/reveal",
        {"api_version": CLIENT_API_VERSION},
        expected=(400,),
    )
    if stale_csrf_result.get("category") != "request_authentication_rejected":
        raise RuntimeError("Client process reset accepted its old CSRF token")
    stale_download = _client_post(
        current_port,
        current_csrf,
        "/api/v2/package/export",
        {"api_version": CLIENT_API_VERSION, "download_id": stale_download_id},
        expected=(400,),
    )
    if stale_download.get("category") != "package_export_rejected":
        raise RuntimeError("Client process reset retained an old package download")
    stale_import = _client_post(
        current_port,
        current_csrf,
        "/api/v2/recover",
        {
            "api_version": CLIENT_API_VERSION,
            "operation_id": "smoke-reset-package-state",
            "recovery_input": [],
            "selected_holder_ids": [],
        },
        expected=(400,),
    )
    if stale_import.get("category") != "package_required":
        raise RuntimeError("Client process reset retained an imported package")
    return latest, current_port


def _observe_role_volumes(
    project: str, environment: dict[str, str]
) -> list[dict[str, object]]:
    roles = (
        ("admission-data", "admission"),
        ("bootstrap-data", "bootstrap"),
        ("managed-client-data", "managed-client-template"),
        ("manager-controller-data", "manager-controller"),
        ("manager-ui-data", "manager-ui"),
        ("operator-data", "operator"),
        ("party1-data", "party"),
        ("party2-data", "party"),
        ("party3-data", "party"),
        ("party4-data", "party"),
        ("party5-data", "party"),
        ("resolver-data", "resolver"),
        ("s3-data", "provider"),
        ("s3-role-data", "s3-role"),
        ("storage-gateway-data", "storage-gateway"),
    )
    observations: list[dict[str, object]] = []
    for volume_name, role in roles:
        output = run_capture(
            [
                require("docker"),
                "run",
                "--rm",
                "--network",
                "none",
                "--read-only",
                "--volume",
                f"{project}_{volume_name}:/audit:ro",
                environment["LOCUS_INTEGRATED_IMAGE"],
                "python",
                "-m",
                "locus.integrated_state_audit",
                "--root",
                "/audit",
                "--role",
                role,
            ],
            env=environment,
        )
        lines = [line for line in output.splitlines() if line.startswith("{")]
        if not lines:
            raise RuntimeError(f"managed role-state audit failed: {role}")
        observed = json.loads(lines[-1])
        if (
            not isinstance(observed, dict)
            or observed.get("status") != "clean"
            or not isinstance(observed.get("files"), int)
            or not isinstance(observed.get("total_bytes"), int)
        ):
            raise RuntimeError(f"managed role-state audit failed: {role}")
        observations.append(
            {
                "files": observed["files"],
                "role": role,
                "total_bytes": observed["total_bytes"],
                "volume_role": volume_name,
            }
        )
    return observations


def _audit_role_volumes(project: str, environment: dict[str, str]) -> int:
    return len(_observe_role_volumes(project, environment))


def _volume_file_digest(
    project: str,
    environment: dict[str, str],
    *,
    volume_name: str,
    relative_path: str,
) -> str:
    """Return only a public file digest from one exact managed role volume."""

    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", volume_name):
        raise RuntimeError("invalid managed volume name")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,127}", relative_path):
        raise RuntimeError("invalid managed volume file")
    script = (
        "from pathlib import Path\n"
        "import hashlib\n"
        f"data = (Path('/audit') / {relative_path!r}).read_bytes()\n"
        "print(hashlib.sha256(data).hexdigest())\n"
    )
    output = run_capture(
        [
            require("docker"),
            "run",
            "--rm",
            "--network",
            "none",
            "--read-only",
            "--volume",
            f"{project}_{volume_name}:/audit:ro",
            environment["LOCUS_INTEGRATED_IMAGE"],
            "python",
            "-c",
            script,
        ],
        env=environment,
    ).strip()
    if re.fullmatch(r"[0-9a-f]{64}", output) is None:
        raise RuntimeError("managed public-state digest is invalid")
    return output


def _cleanup_smoke_project(
    project: str, environment: dict[str, str], *, remove_image: bool = True
) -> None:
    failures: list[str] = []
    try:
        _remove_dynamic_clients(project, environment)
    except BaseException as error:
        failures.append(f"clients:{type(error).__name__}")
    try:
        down_command = [
            *_compose(project),
            "down",
            "--volumes",
            "--remove-orphans",
        ]
        if remove_image:
            down_command.extend(["--rmi", "local"])
        run_capture(
            down_command,
            env=environment,
            check=False,
        )
    except BaseException as error:
        failures.append(f"compose:{type(error).__name__}")
    if remove_image:
        try:
            run_capture(
                [
                    require("docker"),
                    "image",
                    "rm",
                    environment["LOCUS_INTEGRATED_IMAGE"],
                ],
                env=environment,
                check=False,
            )
        except BaseException as error:
            failures.append(f"image:{type(error).__name__}")
    try:
        _remove_browser_edge_network(project, environment)
    except BaseException as error:
        failures.append(f"browser-edge:{type(error).__name__}")
    leftovers: dict[str, str] = {}
    queries = {
        "compose_containers": [
            require("docker"),
            "ps",
            "--all",
            "--filter",
            f"label=com.docker.compose.project={project}",
            "--format",
            "{{.ID}}",
        ],
        "networks": [
            require("docker"),
            "network",
            "ls",
            "--filter",
            f"label=com.docker.compose.project={project}",
            "--format",
            "{{.ID}}",
        ],
        "volumes": [
            require("docker"),
            "volume",
            "ls",
            "--filter",
            f"label=com.docker.compose.project={project}",
            "--format",
            "{{.Name}}",
        ],
    }
    if remove_image:
        queries["images"] = [
            require("docker"),
            "images",
            "--filter",
            f"reference={environment['LOCUS_INTEGRATED_IMAGE']}",
            "--format",
            "{{.ID}}",
        ]
    for label, command in queries.items():
        try:
            leftovers[label] = run_capture(command, env=environment).strip()
        except BaseException as error:
            failures.append(f"inspect-{label}:{type(error).__name__}")
    try:
        leftovers["managed_clients"] = "\n".join(
            _dynamic_client_ids(project, environment)
        )
    except BaseException as error:
        failures.append(f"inspect-clients:{type(error).__name__}")
    remaining = sorted(label for label, value in leftovers.items() if value)
    if failures or remaining:
        detail = ",".join([*failures, *[f"leftover-{item}" for item in remaining]])
        raise RuntimeError(f"managed smoke cleanup failed: {detail}")


def _managed_flow_positive_controls(
    contacts: dict[str, list[dict[str, object]]],
) -> dict[str, bool]:
    from locus.flow_audit import (
        FLOW_PREFIX,
        TRACE_POLICY_ID,
        FlowAuditError,
        aggregate_events,
        parse_events,
        validate_event,
    )
    from locus.redaction import exposed_categories

    base: dict[str, object] = {
        "boot": "11" * 8,
        "category": "admission-issue",
        "context": "NF01:yi-2of3",
        "observation": "sender",
        "receiver": "admission",
        "request_bytes": 1,
        "response_bytes": 1,
        "result": "success",
        "sender": "managed-client",
        "sequence": 1,
        "trace_policy_id": TRACE_POLICY_ID,
    }

    def rejected(**changes: object) -> bool:
        candidate = dict(base)
        candidate.update(changes)
        try:
            validate_event(candidate)
        except FlowAuditError:
            return True
        return False

    mismatch_sender = cast(dict[str, Any], dict(base))
    mismatch_receiver = cast(dict[str, Any], dict(base))
    mismatch_receiver.update(
        {"boot": "22" * 8, "observation": "receiver", "response_bytes": 2}
    )
    try:
        aggregate_events([mismatch_sender, mismatch_receiver])
        mismatch_detected = False
    except FlowAuditError:
        mismatch_detected = True
    gap = dict(base)
    gap["sequence"] = 2
    try:
        parse_events([FLOW_PREFIX + json.dumps(gap)])
        sequence_gap_detected = False
    except FlowAuditError:
        sequence_gap_detected = True
    flattened = [contact for values in contacts.values() for contact in values]
    return {
        "allowed_edge_observed": bool(flattened),
        "blocked_isolation_probes": True,
        "byte_bound_detected": rejected(request_bytes=4 * 1024 * 1024 + 1),
        "client_controller_success": any(
            item["sender_role"] == "managed-client"
            and item["receiver_role"] == "manager-controller"
            and cast(int, item["success_count"]) > 0
            for item in flattened
        ),
        "fabricated_noresolver_detected": rejected(
            receiver="resolver", category="resolver-resolve"
        ),
        "fictional_marker_detected": exposed_categories(
            "fictional-flow-marker",
            {"fictional-marker": "fictional-flow-marker"},
        )
        == ["fictional-marker"],
        "manager_controller_success": any(
            item["sender_role"] == "manager-ui"
            and item["receiver_role"] == "manager-controller"
            and cast(int, item["success_count"]) > 0
            for item in flattened
        ),
        "mismatch_detected": mismatch_detected,
        "raw_events_discarded": True,
        "sequence_gap_detected": sequence_gap_detected,
        "service_logs_discarded": True,
        "unknown_category_detected": rejected(category="unknown"),
        "unknown_role_detected": rejected(receiver="unknown"),
    }


def integrated_smoke(
    *, state_evidence: bool = False, flow_evidence: bool = False
) -> dict[str, object]:
    global _FLOW_EVIDENCE_ACTIVE, _FLOW_HOST_BOOT, _FLOW_HOST_EVENTS
    global _FLOW_HOST_SEQUENCE
    if state_evidence and flow_evidence:
        raise RuntimeError("state and flow evidence modes are disjoint")
    integrated_config()
    _FLOW_EVIDENCE_ACTIVE = flow_evidence
    _FLOW_HOST_EVENTS = []
    _FLOW_HOST_SEQUENCE = 0
    _FLOW_HOST_BOOT = secrets.token_hex(8)
    project = f"locus-managed-smoke-{secrets.token_hex(4)}"
    manager_port = _free_loopback_port()
    environment = _environment(project, manager_port)
    manager_csrf = ""
    original_key = ""
    client_a_logs = ""
    original_cues = _policy_inputs()
    packages: list[dict[str, object]] = []
    subset_recoveries = 0
    summary: dict[str, object] | None = None
    state_snapshots: dict[str, list[dict[str, object]]] = {}
    flow_logs: list[str] = []
    resolved_graph = json.loads(
        run_capture([*_compose(project), "config", "--format", "json"], env=environment)
    )
    resolved_graph_sha256 = hashlib.sha256(
        json.dumps(resolved_graph, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    live_graph_sha256 = ""
    try:
        status = _start_project(
            project=project, manager_port=manager_port, environment=environment
        )
        containers = status.get("containers")
        if not isinstance(containers, list) or len(containers) != 13:
            raise RuntimeError("managed static inventory is incomplete")
        live_graph_sha256 = hashlib.sha256(
            json.dumps(containers, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        with _flow_context("NF12:managed-common"):
            manager_csrf = _manager_session(manager_port)
            _exercise_manager_actions(manager_port, manager_csrf)

        with _flow_context("NF07:managed-common"):
            client_a = _create_client_concurrently(manager_port, manager_csrf)
        _reject_stale_lifecycle_request(manager_port, manager_csrf)
        client_a_port = cast(int, client_a["port"])
        session_a = _client_session(client_a_port)
        _assert_ui_assets(
            client_a_port,
            html_marker=b"LOCUS Client",
            script_path="/assets/client.js",
            style_path="/assets/client.css",
        )
        with _flow_context("NF12:managed-common"):
            _client_session(client_a_port)
            _assert_live_control_isolation(
                project=project, client=client_a, environment=environment
            )
        client_a_csrf = cast(str, session_a["csrf_token"])
        generated = _client_post(
            client_a_port,
            client_a_csrf,
            "/api/v2/key/generate",
            {"api_version": CLIENT_API_VERSION, "operation_id": "smoke-generate-a"},
        )
        generated_key = generated.get("private_key")
        if not isinstance(generated_key, str) or len(generated_key) != 64:
            raise RuntimeError("Client A did not reveal a synthetic Ed25519 seed")
        original_key = generated_key

        arms = (
            (
                "LOCUS-APPSS-2HASHDH-RISTRETTO255-SHA512-GF128-v1",
                "LOCUS-paired-suite-deployment-2of3-v1",
                "LOCUS-canonical-email-set-v1",
            ),
            (
                "LOCUS-TPASS-YI-ZK-RISTRETTO255-v1",
                "LOCUS-paired-suite-deployment-2of3-v1",
                "LOCUS-canonical-email-set-v1"
                if state_evidence or flow_evidence
                else "LOCUS-canonical-phone-set-v1",
            ),
            (
                "LOCUS-APPSS-2HASHDH-RISTRETTO255-SHA512-GF128-v1",
                "LOCUS-paired-suite-deployment-3of5-v1",
                "LOCUS-location-person-set-v1",
            ),
            (
                "LOCUS-TPASS-YI-ZK-RISTRETTO255-v1",
                "LOCUS-paired-suite-deployment-3of5-v1",
                "LOCUS-location-person-set-v1"
                if state_evidence or flow_evidence
                else "LOCUS-quantized-coordinate-set-v1",
            ),
        )
        expected_thresholds = {
            "LOCUS-paired-suite-deployment-2of3-v1": {"k": 2, "n": 3},
            "LOCUS-paired-suite-deployment-3of5-v1": {"k": 3, "n": 5},
        }
        expected_suite_profiles = {
            (
                "LOCUS-APPSS-2HASHDH-RISTRETTO255-SHA512-GF128-v1",
                "LOCUS-paired-suite-deployment-2of3-v1",
            ): "LOCUS-APPSS-2of3-v1",
            (
                "LOCUS-APPSS-2HASHDH-RISTRETTO255-SHA512-GF128-v1",
                "LOCUS-paired-suite-deployment-3of5-v1",
            ): "LOCUS-APPSS-3of5-v1",
            (
                "LOCUS-TPASS-YI-ZK-RISTRETTO255-v1",
                "LOCUS-paired-suite-deployment-2of3-v1",
            ): "LOCUS-TPASS-YI-2of3-v1",
            (
                "LOCUS-TPASS-YI-ZK-RISTRETTO255-v1",
                "LOCUS-paired-suite-deployment-3of5-v1",
            ): "LOCUS-TPASS-YI-3of5-v1",
        }
        for index, (suite_id, profile_id, policy_id) in enumerate(arms, start=1):
            family = "yi" if suite_id.startswith("LOCUS-TPASS-YI") else "appss"
            topology = "2of3" if profile_id.endswith("2of3-v1") else "3of5"
            arm_id = f"{family}-{topology}"
            with _flow_context(f"NF05:{arm_id}"):
                preview = _client_post(
                    client_a_port,
                    client_a_csrf,
                    "/api/v2/preview-policy",
                    {
                        "api_version": CLIENT_API_VERSION,
                        "policy_id": policy_id,
                        "recovery_input": original_cues[policy_id],
                    },
                )
                if preview.get("status") != "input_validated":
                    raise RuntimeError("managed policy preview failed")
            with _flow_context(f"NF01:{arm_id}"):
                result = _client_post(
                    client_a_port,
                    client_a_csrf,
                    "/api/v2/enroll",
                    {
                        "api_version": CLIENT_API_VERSION,
                        "deployment_profile_id": profile_id,
                        "operation_id": f"smoke-enroll-{index}",
                        "policy_id": policy_id,
                        "recovery_input": original_cues[policy_id],
                        "suite_id": suite_id,
                    },
                )
            download_id = result.get("download_id")
            if result.get("status") != "enrolled" or not isinstance(download_id, str):
                raise RuntimeError("managed enrollment did not complete")
            suite_profile_id = result.get("suite_profile_id")
            if (
                result.get("deployment_profile_id") != profile_id
                or suite_profile_id != expected_suite_profiles[(suite_id, profile_id)]
                or suite_profile_id == profile_id
            ):
                raise RuntimeError(
                    "managed enrollment confused deployment and suite profiles"
                )
            with _flow_context(f"NF03:{arm_id}"):
                package = _client_package_export(
                    client_a_port, client_a_csrf, download_id
                )
            prohibited_package_values = (
                original_key,
                "Ada@Example.COM",
                "+352621000001",
                "49.61160001",
            )
            if any(value.encode() in package for value in prohibited_package_values):
                raise RuntimeError("encrypted package exposed client-only input")
            packages.append(
                {
                    "bytes": package,
                    "arm_id": arm_id,
                    "deployment_profile_id": profile_id,
                    "policy_id": policy_id,
                    "suite_profile_id": suite_profile_id,
                    "suite_id": suite_id,
                    "threshold": expected_thresholds[profile_id],
                }
            )

        if state_evidence:
            state_snapshots["post_enrollment"] = _observe_role_volumes(
                project, environment
            )

        with _flow_context("NF08:managed-common"):
            resumed_a, client_a_port = _exercise_client_process_actions(
                manager_port,
                manager_csrf,
                client_a_port,
                session_a,
                client_a_csrf,
                cast(str, download_id),
            )
        client_a_csrf = cast(str, resumed_a["csrf_token"])

        client_a_logs = run_capture(
            [require("docker"), "logs", cast(str, client_a["id"])],
            env=environment,
            include_stderr=True,
        )
        flow_logs.append(client_a_logs)
        with _flow_context("NF09:managed-common"):
            _client_post(
                client_a_port,
                client_a_csrf,
                "/api/v2/self-destroy",
                {"api_version": CLIENT_API_VERSION, "operation_id": "smoke-destroy-a"},
                expected=(202,),
            )
        flow_logs.append(
            run_capture(
                [require("docker"), "logs", cast(str, client_a["id"])],
                env=environment,
                check=False,
                include_stderr=True,
            )
        )
        _wait_client_removed(manager_port, client_a_port)

        with _flow_context("NF07:managed-common"):
            client_b = _create_client(manager_port, manager_csrf)
        client_b_port = cast(int, client_b["port"])
        session_b = _client_session(client_b_port)
        _assert_ui_assets(
            client_b_port,
            html_marker=b"LOCUS Client",
            script_path="/assets/client.js",
            style_path="/assets/client.css",
        )
        client_b_csrf = cast(str, session_b["csrf_token"])
        if (
            session_a["client_id"] == session_b["client_id"]
            or session_a["client_identity"] == session_b["client_identity"]
            or session_a["proof_key_thumbprint"] == session_b["proof_key_thumbprint"]
        ):
            raise RuntimeError("clean Client B did not receive a fresh public identity")
        temporary = _client_post(
            client_b_port,
            client_b_csrf,
            "/api/v2/key/generate",
            {"api_version": CLIENT_API_VERSION, "operation_id": "smoke-generate-b"},
        )
        temporary_value = temporary.get("private_key")
        if not isinstance(temporary_value, str):
            raise RuntimeError("Client B did not create its temporary key")
        temporary_key = temporary_value
        if temporary_key == original_key:
            raise RuntimeError("Client B temporary key was not fresh")

        corrupted = b"[" + cast(bytes, packages[0]["bytes"])[1:]
        with _flow_context("NF04:appss-2of3"):
            rejected_package = _client_package_import(
                client_b_port,
                client_b_csrf,
                corrupted,
                expected=(400,),
            )
        if rejected_package.get("category") != "package_import_rejected":
            raise RuntimeError("corrupt package was not rejected")

        first_success_operation = ""
        for package_index, record in enumerate(packages, start=1):
            arm_id = cast(str, record["arm_id"])
            with _flow_context(f"NF03:{arm_id}"):
                imported = _client_package_import(
                    client_b_port, client_b_csrf, cast(bytes, record["bytes"])
                )
            if (
                imported.get("status") != "package_authenticated"
                or imported.get("suite_id") != record["suite_id"]
                or imported.get("policy_id") != record["policy_id"]
                or imported.get("deployment_profile_id")
                != record["deployment_profile_id"]
                or imported.get("suite_profile_id") != record["suite_profile_id"]
                or imported.get("threshold") != record["threshold"]
            ):
                raise RuntimeError("package metadata was not authenticated exactly")
            threshold = imported.get("threshold")
            holders = imported.get("holder_ids")
            if not isinstance(threshold, dict) or not isinstance(holders, list):
                raise RuntimeError("authenticated package omitted holder configuration")
            k = threshold.get("k")
            if not isinstance(k, int) or any(
                not isinstance(item, int) for item in holders
            ):
                raise RuntimeError(
                    "authenticated package has invalid holder configuration"
                )
            n = threshold.get("n")
            if (
                not isinstance(n, int)
                or holders != list(range(1, n + 1))
                or imported.get("authorization_quorum") != 4
            ):
                raise RuntimeError("authenticated package changed fixed party topology")

            if package_index == 1:
                with _flow_context(f"NF04:{arm_id}"):
                    wrong = _client_post(
                        client_b_port,
                        client_b_csrf,
                        "/api/v2/recover",
                        {
                            "api_version": CLIENT_API_VERSION,
                            "operation_id": "smoke-wrong-input",
                            "recovery_input": [
                                "wrong1@example.test",
                                "wrong2@example.test",
                                "wrong3@example.test",
                            ],
                            "selected_holder_ids": holders[:k],
                        },
                        expected=(400,),
                    )
                if wrong.get("category") != "recovery_rejected":
                    raise RuntimeError("wrong recovery input was not normalized")
                still_temporary = _client_post(
                    client_b_port,
                    client_b_csrf,
                    "/api/v2/key/reveal",
                    {"api_version": CLIENT_API_VERSION},
                )
                if still_temporary.get("private_key") != temporary_key:
                    raise RuntimeError("failed recovery replaced the current key")
                with _flow_context(f"NF04:{arm_id}"):
                    override = _client_post(
                        client_b_port,
                        client_b_csrf,
                        "/api/v2/recover",
                        {
                            "api_version": CLIENT_API_VERSION,
                            "operation_id": "smoke-suite-override",
                            "recovery_input": original_cues[
                                cast(str, record["policy_id"])
                            ],
                            "selected_holder_ids": holders[:k],
                            "suite_id": "LOCUS-TPASS-YI-ZK-RISTRETTO255-v1",
                        },
                        expected=(400,),
                    )
                if override.get("category") != "recovery_rejected":
                    raise RuntimeError("recovery-time suite override was not rejected")
                with _flow_context(f"NF04:{arm_id}"):
                    invalid_subset = _client_post(
                        client_b_port,
                        client_b_csrf,
                        "/api/v2/recover",
                        {
                            "api_version": CLIENT_API_VERSION,
                            "operation_id": "smoke-invalid-subset",
                            "recovery_input": original_cues[
                                cast(str, record["policy_id"])
                            ],
                            "selected_holder_ids": holders[: max(0, k - 1)],
                        },
                        expected=(400,),
                    )
                if invalid_subset.get("category") != "recovery_rejected":
                    raise RuntimeError("invalid holder subset was not rejected")
            else:
                with _flow_context(f"NF04:{arm_id}"):
                    invalid_subset = _client_post(
                        client_b_port,
                        client_b_csrf,
                        "/api/v2/recover",
                        {
                            "api_version": CLIENT_API_VERSION,
                            "operation_id": f"smoke-invalid-subset-{package_index}",
                            "recovery_input": original_cues[
                                cast(str, record["policy_id"])
                            ],
                            "selected_holder_ids": holders[: max(0, k - 1)],
                        },
                        expected=(400,),
                    )
                if invalid_subset.get("category") != "recovery_rejected":
                    raise RuntimeError("invalid holder subset was not rejected")

            for subset_index, subset in enumerate(combinations(holders, k), start=1):
                operation_id = f"smoke-recover-{package_index}-{subset_index}"
                with _flow_context(f"NF02:{arm_id}"):
                    result = _client_post(
                        client_b_port,
                        client_b_csrf,
                        "/api/v2/recover",
                        {
                            "api_version": CLIENT_API_VERSION,
                            "operation_id": operation_id,
                            "recovery_input": original_cues[
                                cast(str, record["policy_id"])
                            ],
                            "selected_holder_ids": list(subset),
                        },
                    )
                if (
                    result.get("status") != "recovered"
                    or result.get("key_identity_verified") is not True
                    or result.get("key_replaced") is not True
                ):
                    raise RuntimeError("exact-threshold managed recovery failed")
                subset_recoveries += 1
                if not first_success_operation:
                    first_success_operation = operation_id
            revealed = _client_post(
                client_b_port,
                client_b_csrf,
                "/api/v2/key/reveal",
                {"api_version": CLIENT_API_VERSION},
            )
            if revealed.get("private_key") != original_key:
                raise RuntimeError("recovered key did not match Client A's key")

        if state_evidence:
            state_snapshots["post_recovery"] = _observe_role_volumes(
                project, environment
            )

        with _flow_context(f"NF04:{packages[-1]['arm_id']}"):
            replay = _client_post(
                client_b_port,
                client_b_csrf,
                "/api/v2/recover",
                {
                    "api_version": CLIENT_API_VERSION,
                    "operation_id": first_success_operation,
                    "recovery_input": original_cues[
                        cast(str, packages[-1]["policy_id"])
                    ],
                    "selected_holder_ids": [1, 2, 3],
                },
                expected=(409,),
            )
        if replay.get("category") != "operation_conflict":
            raise RuntimeError("completed recovery replay was not rejected")

        with _flow_context("NF06:appss-2of3"):
            _manager_action(manager_port, manager_csrf, "party5", "stop")
        _wait_role(manager_port, "party5", state="exited")
        with _flow_context("NF06:appss-2of3"):
            _client_package_import(
                client_b_port, client_b_csrf, cast(bytes, packages[0]["bytes"])
            )
            with_one_down = _client_post(
                client_b_port,
                client_b_csrf,
                "/api/v2/recover",
                {
                    "api_version": CLIENT_API_VERSION,
                    "operation_id": "smoke-one-authorizer-down",
                    "recovery_input": original_cues[
                        cast(str, packages[0]["policy_id"])
                    ],
                    "selected_holder_ids": [1, 2],
                },
            )
        if with_one_down.get("status") != "recovered":
            raise RuntimeError("4-of-5 authorization did not tolerate one outage")
        with _flow_context("NF06:appss-2of3"):
            _manager_action(manager_port, manager_csrf, "party4", "stop")
        _wait_role(manager_port, "party4", state="exited")
        with _flow_context("NF06:appss-2of3"):
            quorum_loss = _client_post(
                client_b_port,
                client_b_csrf,
                "/api/v2/recover",
                {
                    "api_version": CLIENT_API_VERSION,
                    "operation_id": "smoke-auth-quorum-loss",
                    "recovery_input": original_cues[
                        cast(str, packages[0]["policy_id"])
                    ],
                    "selected_holder_ids": [1, 2],
                },
                expected=(400,),
            )
        if quorum_loss.get("category") != "recovery_rejected":
            raise RuntimeError("authorization-quorum loss was not rejected")
        for role in ("party4", "party5"):
            _manager_action(manager_port, manager_csrf, role, "start")
            _wait_role(manager_port, role, state="running", healthy=True)

        with _flow_context("NF06:appss-2of3"):
            _manager_action(manager_port, manager_csrf, "s3", "stop")
        _wait_role(manager_port, "s3", state="exited")
        for record in packages:
            with _flow_context(f"NF06:{record['arm_id']}"):
                provider_loss = _client_package_import(
                    client_b_port,
                    client_b_csrf,
                    cast(bytes, record["bytes"]),
                    expected=(400,),
                )
            if provider_loss.get("category") != "package_import_rejected":
                raise RuntimeError("provider outage was not rejected")
        _manager_action(manager_port, manager_csrf, "s3", "start")
        _wait_role(manager_port, "s3", state="running", healthy=True, timeout=75)
        _client_package_import(
            client_b_port, client_b_csrf, cast(bytes, packages[0]["bytes"])
        )

        _manager_action(manager_port, manager_csrf, "party1", "restart")
        _wait_role(manager_port, "party1", state="running", healthy=True)
        restarted = _client_post(
            client_b_port,
            client_b_csrf,
            "/api/v2/recover",
            {
                "api_version": CLIENT_API_VERSION,
                "operation_id": "smoke-party-restart",
                "recovery_input": original_cues[cast(str, packages[0]["policy_id"])],
                "selected_holder_ids": [1, 2],
            },
        )
        if restarted.get("status") != "recovered":
            raise RuntimeError("party restart recovery failed")

        client_b_id = cast(str, client_b["id"])
        client_logs = run_capture(
            [require("docker"), "logs", client_b_id],
            env=environment,
            include_stderr=True,
        )
        compose_logs = run_capture(
            [*_compose(project), "logs", "--no-color"],
            env=environment,
            include_stderr=True,
        )
        flow_logs.extend([client_logs, compose_logs])
        from locus.redaction import exposed_categories

        exposures = exposed_categories(
            client_a_logs + client_logs + compose_logs,
            {
                "original-private-key": original_key,
                "storage-access-key": environment["LOCUS_S3_ACCESS_KEY"],
                "storage-secret-key": environment["LOCUS_S3_SECRET_KEY"],
                "synthetic-email": "Ada@Example.COM",
                "synthetic-phone": "+352621000001",
            },
        )
        if exposures:
            raise RuntimeError(
                "managed output scan found prohibited categories: "
                + ",".join(exposures)
            )

        with _flow_context("NF09:managed-common"):
            _client_post(
                client_b_port,
                client_b_csrf,
                "/api/v2/self-destroy",
                {"api_version": CLIENT_API_VERSION, "operation_id": "smoke-destroy-b"},
                expected=(202,),
            )
        flow_logs.append(
            run_capture(
                [require("docker"), "logs", client_b_id],
                env=environment,
                check=False,
                include_stderr=True,
            )
        )
        _wait_client_removed(manager_port, client_b_port)
        trust_before_stop = _volume_file_digest(
            project,
            environment,
            volume_name="manager-ui-data",
            relative_path="ca.pem",
        )
        with _flow_context("NF10:managed-common"):
            _stop_through_manager(
                manager_port, manager_csrf, label="smoke-preserving-system-stop"
            )
        flow_logs.append(
            run_capture(
                [*_compose(project), "logs", "--no-color"],
                env=environment,
                include_stderr=True,
            )
        )
        preserved_observations = _observe_role_volumes(project, environment)
        preserved_role_audits = len(preserved_observations)
        if state_evidence:
            state_snapshots["preserved_restart"] = preserved_observations

        _resumed_status, manager_csrf = _resume_project(
            project=project, manager_port=manager_port, environment=environment
        )
        trust_after_restart = _volume_file_digest(
            project,
            environment,
            volume_name="manager-ui-data",
            relative_path="ca.pem",
        )
        if trust_after_restart != trust_before_stop:
            raise RuntimeError("normal Manager stop changed the project trust root")

        with _flow_context("NF10:managed-common"):
            client_c = _create_client(manager_port, manager_csrf)
        client_c_port = cast(int, client_c["port"])
        session_c = _client_session(client_c_port)
        client_c_csrf = cast(str, session_c["csrf_token"])
        with _flow_context("NF10:managed-common"):
            preserved_import = _client_package_import(
                client_c_port,
                client_c_csrf,
                cast(bytes, packages[0]["bytes"]),
            )
        preserved_threshold = preserved_import.get("threshold")
        preserved_holders = preserved_import.get("holder_ids")
        if not isinstance(preserved_threshold, dict) or not isinstance(
            preserved_holders, list
        ):
            raise RuntimeError("preserved package omitted authenticated topology")
        preserved_k = preserved_threshold.get("k")
        if not isinstance(preserved_k, int):
            raise RuntimeError("preserved package omitted its threshold")
        with _flow_context("NF10:managed-common"):
            preserved_recovery = _client_post(
                client_c_port,
                client_c_csrf,
                "/api/v2/recover",
                {
                    "api_version": CLIENT_API_VERSION,
                    "operation_id": _operation_id("smoke-preserved-recovery"),
                    "recovery_input": original_cues[
                        cast(str, packages[0]["policy_id"])
                    ],
                    "selected_holder_ids": preserved_holders[:preserved_k],
                },
            )
        if preserved_recovery.get("status") != "recovered":
            raise RuntimeError("normal stop/start did not preserve recovery state")
        preserved_reveal = _client_post(
            client_c_port,
            client_c_csrf,
            "/api/v2/key/reveal",
            {"api_version": CLIENT_API_VERSION},
        )
        if preserved_reveal.get("private_key") != original_key:
            raise RuntimeError("normal stop/start recovered the wrong key")
        flow_logs.append(
            run_capture(
                [require("docker"), "logs", cast(str, client_c["id"])],
                env=environment,
                check=False,
                include_stderr=True,
            )
        )
        with _flow_context("NF09:managed-common"):
            _client_post(
                client_c_port,
                client_c_csrf,
                "/api/v2/self-destroy",
                {
                    "api_version": CLIENT_API_VERSION,
                    "operation_id": _operation_id("smoke-destroy-c"),
                },
                expected=(202,),
            )
        flow_logs.append(
            run_capture(
                [require("docker"), "logs", cast(str, client_c["id"])],
                env=environment,
                check=False,
                include_stderr=True,
            )
        )
        _wait_client_removed(manager_port, client_c_port)
        with _flow_context("NF11:managed-common"):
            _stop_through_manager(
                manager_port, manager_csrf, label="smoke-before-state-reset"
            )
        flow_logs.append(
            run_capture(
                [*_compose(project), "logs", "--no-color"],
                env=environment,
                include_stderr=True,
            )
        )

        integrated_stop(argparse.Namespace(project=project, reset_state=True))
        fresh_status = _start_project(
            project=project, manager_port=manager_port, environment=environment
        )
        fresh_containers = fresh_status.get("containers")
        if not isinstance(fresh_containers, list) or len(fresh_containers) != 13:
            raise RuntimeError("state reset did not create a fresh static system")
        with _flow_context("NF11:managed-common"):
            manager_csrf = _manager_session(manager_port)
        trust_after_reset = _volume_file_digest(
            project,
            environment,
            volume_name="manager-ui-data",
            relative_path="ca.pem",
        )
        if trust_after_reset == trust_before_stop:
            raise RuntimeError("destructive state reset reused the old trust root")

        with _flow_context("NF11:managed-common"):
            client_d = _create_client(manager_port, manager_csrf)
        client_d_port = cast(int, client_d["port"])
        session_d = _client_session(client_d_port)
        client_d_csrf = cast(str, session_d["csrf_token"])
        if session_c.get("client_id") == session_d.get("client_id") or session_c.get(
            "client_identity"
        ) == session_d.get("client_identity"):
            raise RuntimeError("fresh system reused the prior Client identity")
        with _flow_context("NF11:managed-common"):
            reset_import = _client_package_import(
                client_d_port,
                client_d_csrf,
                cast(bytes, packages[0]["bytes"]),
                expected=(400,),
            )
        if reset_import.get("category") != "package_import_rejected":
            raise RuntimeError("fresh system accepted a pre-reset recovery package")
        flow_logs.append(
            run_capture(
                [require("docker"), "logs", cast(str, client_d["id"])],
                env=environment,
                check=False,
                include_stderr=True,
            )
        )
        with _flow_context("NF09:managed-common"):
            _client_post(
                client_d_port,
                client_d_csrf,
                "/api/v2/self-destroy",
                {
                    "api_version": CLIENT_API_VERSION,
                    "operation_id": _operation_id("smoke-destroy-d"),
                },
                expected=(202,),
            )
        flow_logs.append(
            run_capture(
                [require("docker"), "logs", cast(str, client_d["id"])],
                env=environment,
                check=False,
                include_stderr=True,
            )
        )
        _wait_client_removed(manager_port, client_d_port)
        with _flow_context("NF11:managed-common"):
            _stop_through_manager(manager_port, manager_csrf, label="smoke-final-stop")
        flow_logs.append(
            run_capture(
                [*_compose(project), "logs", "--no-color"],
                env=environment,
                include_stderr=True,
            )
        )

        role_observations = _observe_role_volumes(project, environment)
        role_audits = len(role_observations)
        if state_evidence:
            state_snapshots["fresh_reset"] = role_observations
        flow_contacts: dict[str, list[dict[str, object]]] = {}
        flow_controls: dict[str, bool] = {}
        if flow_evidence:
            from locus.flow_audit import aggregate_events, parse_events
            from locus.managed_flow_evidence import scenario_manifest

            all_flow_output = "".join(flow_logs)
            later_exposures = exposed_categories(
                all_flow_output,
                {
                    "original-private-key": original_key,
                    "storage-access-key": environment["LOCUS_S3_ACCESS_KEY"],
                    "storage-secret-key": environment["LOCUS_S3_SECRET_KEY"],
                    "synthetic-email": "Ada@Example.COM",
                    "synthetic-phone": "+352621000001",
                },
            )
            if later_exposures:
                raise RuntimeError(
                    "managed flow output scan found prohibited categories: "
                    + ",".join(later_exposures)
                )
            flow_contacts = cast(
                dict[str, list[dict[str, object]]],
                aggregate_events(
                    parse_events(flow_logs, extra_events=cast(Any, _FLOW_HOST_EVENTS))
                ),
            )
            expected_contexts = {
                f"{item['scenario_id']}:{item['arm_id']}"
                for item in cast(list[dict[str, str]], scenario_manifest()["reports"])
            }
            if set(flow_contacts) != expected_contexts:
                missing = sorted(expected_contexts - set(flow_contacts))
                extra = sorted(set(flow_contacts) - expected_contexts)
                raise RuntimeError(
                    f"managed flow contexts changed (missing={missing}, extra={extra})"
                )
            flow_controls = _managed_flow_positive_controls(flow_contacts)
        summary = {
            "arms": 4,
            "clean_clients": 4,
            "client_process_identity_rotations": 3,
            "client_identity_changed": True,
            "concurrent_client_create": "passed",
            "live_control_isolation": "passed",
            "manager_actions": ["start", "stop", "restart", "kill"],
            "normal_stop_restart_recovery": "passed",
            "output_scan": "passed",
            "packages": 4,
            "policies": 2 if state_evidence or flow_evidence else 4,
            "preserved_role_state_audits": preserved_role_audits,
            "reset_state_fresh_trust": "passed",
            "resolved_graph_sha256": resolved_graph_sha256,
            "role_state_audits": role_audits,
            "status": "passed",
            "stale_lifecycle_rejection": "passed",
            "subset_recoveries": subset_recoveries,
            "live_graph_sha256": live_graph_sha256,
            "image_id": environment["LOCUS_INTEGRATED_IMAGE_ID"],
        }
        if state_evidence:
            summary["state_snapshots"] = state_snapshots
            summary["paired_policy_conditions"] = True
        if flow_evidence:
            summary["flow_contacts"] = flow_contacts
            summary["positive_controls"] = flow_controls
            summary["paired_policy_conditions"] = True
            client_set = "\n".join(
                sorted(
                    cast(str, session["client_id"])
                    for session in (session_a, session_b, session_c, session_d)
                )
            )
            package_set = "\n".join(
                sorted(
                    hashlib.sha256(cast(bytes, item["bytes"])).hexdigest()
                    for item in packages
                )
            )
            summary["pseudonymous_project_id"] = (
                "project-" + hashlib.sha256(project.encode()).hexdigest()[:16]
            )
            summary["pseudonymous_client_set_id"] = (
                "clients-" + hashlib.sha256(client_set.encode()).hexdigest()[:16]
            )
            summary["pseudonymous_package_set_id"] = (
                "packages-" + hashlib.sha256(package_set.encode()).hexdigest()[:16]
            )
        printable_summary = dict(summary)
        if flow_evidence:
            printable_summary.pop("flow_contacts", None)
            printable_summary["flow_contexts"] = len(flow_contacts)
            printable_summary["flow_contact_categories"] = sum(
                len(contacts) for contacts in flow_contacts.values()
            )
        print(json.dumps(printable_summary, sort_keys=True))
    except BaseException:
        active_error = sys.exc_info()[1]
        print(
            json.dumps(
                {
                    "category": "managed_smoke_failed",
                    "error": type(active_error).__name__,
                    "message": str(active_error),
                },
                sort_keys=True,
            ),
            file=sys.stderr,
            flush=True,
        )
        raise
    finally:
        primary_error = sys.exc_info()[1]
        try:
            _cleanup_smoke_project(project, environment)
        except BaseException as cleanup_error:
            if primary_error is None:
                raise
            primary_error.add_note(
                "managed cleanup also failed: "
                f"{type(cleanup_error).__name__}: {cleanup_error}"
            )
            print(
                json.dumps(
                    {
                        "category": "managed_cleanup_failed",
                        "error": type(cleanup_error).__name__,
                    },
                    sort_keys=True,
                ),
                file=sys.stderr,
                flush=True,
            )
        _FLOW_EVIDENCE_ACTIVE = False
    if summary is None:
        raise RuntimeError("managed smoke produced no summary")
    return summary


def native_build() -> None:
    require("uv")
    environment = os.environ.copy()
    environment["VIRTUAL_ENV"] = sys.prefix
    run([PYTHON, "-m", "maturin", "develop", "--uv", "--locked"], env=environment)


def integrated_check() -> None:
    """Run the focused quality/native gate for this isolated implementation."""

    sources = [ROOT / "tasks.py", *sorted((ROOT / "locus").rglob("*.py"))]
    sources.extend(sorted((ROOT / "tests").rglob("*.py")))
    for source in sources:
        ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
    print(f"Parsed {len(sources)} Python files successfully.")
    run([PYTHON, "-m", "ruff", "format", "--check", "tasks.py", "locus", "tests"])
    run([PYTHON, "-m", "ruff", "check", "tasks.py", "locus", "tests"])
    run([PYTHON, "-m", "mypy", "tasks.py", "locus", "tests"])
    cargo = require("cargo")
    manifests = (
        "appss-core/Cargo.toml",
        "tpass-core/Cargo.toml",
        "tpass-python/Cargo.toml",
    )
    for manifest in manifests:
        run([cargo, "fmt", "--manifest-path", manifest, "--", "--check"])
        run(
            [
                cargo,
                "clippy",
                "--locked",
                "--manifest-path",
                manifest,
                "--all-targets",
                "--",
                "-D",
                "warnings",
            ]
        )
    native_build()
    run([PYTHON, "-B", "-m", "unittest", "discover", "-s", "tests", "-t", "."])
    for manifest in manifests:
        run([cargo, "test", "--locked", "--manifest-path", manifest])


def _tracked_source_provenance(*, require_clean: bool) -> dict[str, object]:
    git = require("git")
    repository = ROOT.parent
    status = run_capture(
        [
            git,
            "-C",
            str(repository),
            "status",
            "--porcelain=v1",
            "--untracked-files=all",
        ],
    )
    if require_clean and status:
        raise RuntimeError("retained evidence requires a clean source commit")
    commit = run_capture([git, "-C", str(repository), "rev-parse", "HEAD"]).strip()
    if re.fullmatch(r"[0-9a-f]{40}", commit) is None:
        raise RuntimeError("source commit is unavailable")
    tracked = [
        line
        for line in run_capture(
            [git, "-C", str(repository), "ls-files", "--", "prototype_final"],
        ).splitlines()
        if line
    ]
    source_hash = hashlib.sha256()
    for relative in sorted(tracked):
        path = repository / relative
        if not path.is_file():
            raise RuntimeError("tracked source file is unavailable")
        encoded_path = relative.replace("\\", "/").encode("utf-8")
        source_hash.update(len(encoded_path).to_bytes(4, "big"))
        source_hash.update(encoded_path)
        source_hash.update(hashlib.sha256(path.read_bytes()).digest())
    host_digest = hashlib.sha256(
        ("LOCUS-pseudonymous-host-v1:" + socket.gethostname()).encode("utf-8")
    ).hexdigest()
    return {
        "collected_at_utc": dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat(),
        "compose_sha256": hashlib.sha256(MANAGED_COMPOSE.read_bytes()).hexdigest(),
        "host_tier": "same-host-single-operator",
        "lockfile_sha256": hashlib.sha256((ROOT / "uv.lock").read_bytes()).hexdigest(),
        "managed_manifest_sha256": hashlib.sha256(
            MANAGED_MANIFEST.read_bytes()
        ).hexdigest(),
        "pseudonymous_host_id": f"host-{host_digest[:16]}",
        "source_commit": commit,
        "source_tree_sha256": source_hash.hexdigest(),
    }


def _performance_client_observation(port: int, csrf: str) -> dict[str, object]:
    result = _client_post(
        port,
        csrf,
        "/api/v2/performance-observation",
        {
            "api_version": CLIENT_API_VERSION,
            "instrumentation_id": _PERFORMANCE_INSTRUMENTATION_ID,
        },
    )
    observation = result.get("observation")
    if result.get("status") != "observed" or not isinstance(observation, dict):
        raise RuntimeError("managed Client omitted its performance observation")
    return cast(dict[str, object], observation)


def _performance_client_json(
    port: int,
    csrf: str,
    path: str,
    value: dict[str, object],
    *,
    expected: tuple[int, ...] = (200,),
) -> tuple[dict[str, object], int, dict[str, int], dict[str, int]]:
    body = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    started = time.perf_counter_ns()
    encoded, _headers = _raw_request(
        port,
        path,
        method="POST",
        body=body,
        content_type="application/json",
        csrf=csrf,
        expected=expected,
    )
    elapsed = time.perf_counter_ns() - started
    result = json.loads(encoded)
    if not isinstance(result, dict):
        raise RuntimeError("managed Client returned a non-object")
    measured = _performance_client_observation(port, csrf)
    phases = measured.get("phase_latency_ns")
    internal_body = measured.get("application_body_bytes_by_role")
    if not isinstance(phases, dict) or not isinstance(internal_body, dict):
        raise RuntimeError("managed Client returned invalid performance metrics")
    bodies = {
        str(role): count
        for role, count in internal_body.items()
        if isinstance(count, int) and count >= 0
    }
    browser_count = len(body) + len(encoded)
    bodies["browser"] = bodies.get("browser", 0) + browser_count
    bodies["managed-client"] = bodies.get("managed-client", 0) + browser_count
    return (
        cast(dict[str, object], result),
        elapsed,
        {
            str(phase): count
            for phase, count in phases.items()
            if isinstance(count, int) and count >= 0
        },
        bodies,
    )


def _performance_client_export(
    port: int, csrf: str, download_id: str
) -> tuple[bytes, int, dict[str, int]]:
    body = json.dumps(
        {"api_version": CLIENT_API_VERSION, "download_id": download_id},
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    started = time.perf_counter_ns()
    package, headers = _raw_request(
        port,
        "/api/v2/package/export",
        method="POST",
        body=body,
        content_type="application/json",
        csrf=csrf,
    )
    elapsed = time.perf_counter_ns() - started
    if headers.get_content_type() != PACKAGE_MEDIA_TYPE:
        raise RuntimeError("Client exported the wrong package media type")
    measured = _performance_client_observation(port, csrf)
    internal = measured.get("application_body_bytes_by_role")
    if not isinstance(internal, dict):
        raise RuntimeError("package export omitted its byte observation")
    bodies = {
        str(role): count
        for role, count in internal.items()
        if isinstance(count, int) and count >= 0
    }
    browser_count = len(body) + len(package)
    bodies["browser"] = bodies.get("browser", 0) + browser_count
    bodies["managed-client"] = bodies.get("managed-client", 0) + browser_count
    return package, elapsed, bodies


def _performance_client_import(
    port: int, csrf: str, package: bytes
) -> tuple[dict[str, object], int, dict[str, int], dict[str, int]]:
    started = time.perf_counter_ns()
    encoded, _headers = _raw_request(
        port,
        "/api/v2/package/import",
        method="POST",
        body=package,
        content_type=PACKAGE_MEDIA_TYPE,
        csrf=csrf,
    )
    elapsed = time.perf_counter_ns() - started
    result = json.loads(encoded)
    if not isinstance(result, dict):
        raise RuntimeError("package import returned a non-object")
    measured = _performance_client_observation(port, csrf)
    phases = measured.get("phase_latency_ns")
    internal = measured.get("application_body_bytes_by_role")
    if not isinstance(phases, dict) or not isinstance(internal, dict):
        raise RuntimeError("package import omitted its performance metrics")
    bodies = {
        str(role): count
        for role, count in internal.items()
        if isinstance(count, int) and count >= 0
    }
    browser_count = len(package) + len(encoded)
    bodies["browser"] = bodies.get("browser", 0) + browser_count
    bodies["managed-client"] = bodies.get("managed-client", 0) + browser_count
    return (
        cast(dict[str, object], result),
        elapsed,
        {
            str(phase): count
            for phase, count in phases.items()
            if isinstance(count, int) and count >= 0
        },
        bodies,
    )


def _sum_role_bytes(*values: dict[str, int]) -> dict[str, int]:
    result: dict[str, int] = {}
    for value in values:
        for role, count in value.items():
            result[role] = result.get(role, 0) + count
    return result


def _performance_persisted_bytes(
    project: str,
    environment: dict[str, str],
    client: dict[str, object] | None,
) -> dict[str, int]:
    mounts = {
        "admission": "admission-data",
        "bootstrap": "bootstrap-data",
        "managed-client-template": "managed-client-data",
        "manager-controller": "manager-controller-data",
        "manager-ui": "manager-ui-data",
        "operator": "operator-data",
        "party-1": "party1-data",
        "party-2": "party2-data",
        "party-3": "party3-data",
        "party-4": "party4-data",
        "party-5": "party5-data",
        "resolver": "resolver-data",
        "provider": "s3-data",
        "s3-role": "s3-role-data",
        "storage-gateway": "storage-gateway-data",
    }
    command = [require("docker"), "run", "--rm", "--network", "none", "--read-only"]
    for role, volume in mounts.items():
        command.extend(["--volume", f"{project}_{volume}:/audit/{role}:ro"])
    script = (
        "from pathlib import Path\n"
        "import json\n"
        f"roles={list(mounts)!r}\n"
        "def size(root):\n"
        " total=0\n"
        " for path in root.rglob('*'):\n"
        "  if path.is_file() and not path.is_symlink(): total += path.stat().st_size\n"
        " return total\n"
        "print(json.dumps({role:size(Path('/audit')/role) for role in roles},sort_keys=True))\n"
    )
    command.extend([environment["LOCUS_INTEGRATED_IMAGE"], "python", "-c", script])
    output = run_capture(command, env=environment, visible=False)
    lines = [line for line in output.splitlines() if line.startswith("{")]
    if not lines:
        raise RuntimeError("persisted-byte observation failed")
    parsed = json.loads(lines[-1])
    if not isinstance(parsed, dict) or set(parsed) != set(mounts):
        raise RuntimeError("persisted-byte role set changed")
    result = {role: int(parsed[role]) for role in mounts}
    result["managed-client-instance"] = 0
    if client is not None and isinstance(client.get("id"), str):
        inspected = json.loads(
            run_capture(
                [require("docker"), "inspect", "--size", cast(str, client["id"])],
                env=environment,
                visible=False,
            )
        )
        if not isinstance(inspected, list) or len(inspected) != 1:
            raise RuntimeError("managed Client persisted-byte observation failed")
        size = inspected[0].get("SizeRw")
        if not isinstance(size, int) or size < 0:
            raise RuntimeError("managed Client writable-layer size is unavailable")
        result["managed-client-instance"] = size
    return result


def _performance_redact_graph_value(
    value: object, *, project: str, environment: dict[str, str]
) -> object:
    if isinstance(value, dict):
        return {
            key: _performance_redact_graph_value(
                child, project=project, environment=environment
            )
            for key, child in sorted(value.items())
        }
    if isinstance(value, list):
        return [
            _performance_redact_graph_value(
                child, project=project, environment=environment
            )
            for child in value
        ]
    if isinstance(value, str):
        result = value.replace(project, "<project>")
        replacements = {
            environment["LOCUS_INTEGRATED_IMAGE"]: "<managed-image>",
            environment["LOCUS_S3_ACCESS_KEY"]: "<synthetic-access-key>",
            environment["LOCUS_S3_BUCKET"]: "<synthetic-bucket>",
            environment["LOCUS_S3_SECRET_KEY"]: "<synthetic-secret-key>",
            environment["LOCUS_MANAGER_PORT"]: "<manager-port>",
            environment.get("LOCUS_PERFORMANCE_FIXTURE_ID", ""): "<fixture-id>",
        }
        for original, replacement in replacements.items():
            if original:
                result = result.replace(original, replacement)
        return result
    return value


def _performance_base_bindings(
    *,
    project: str,
    environment: dict[str, str],
    status: dict[str, object],
    provenance: dict[str, object],
) -> dict[str, object]:
    from locus.performance_evidence import digest

    configured = json.loads(
        run_capture(
            [*_compose(project), "config", "--format", "json"],
            env=environment,
            visible=False,
        )
    )
    if not isinstance(configured, dict):
        raise RuntimeError("performance Compose graph is invalid")
    _validate_managed_compose(cast(dict[str, object], configured))
    normalized = _performance_redact_graph_value(
        configured, project=project, environment=environment
    )
    manifest = json.loads(MANAGED_MANIFEST.read_bytes())
    services = manifest.get("services") if isinstance(manifest, dict) else None
    networks = manifest.get("networks") if isinstance(manifest, dict) else None
    containers = status.get("containers")
    if not isinstance(services, list) or not isinstance(networks, list):
        raise RuntimeError("managed manifest graph is unavailable")
    if not isinstance(containers, list) or len(containers) != 13:
        raise RuntimeError("live performance graph is incomplete")
    live_roles = sorted(
        {
            str(item.get("role"))
            for item in containers
            if isinstance(item, dict) and isinstance(item.get("role"), str)
        }
    )
    expected_roles = sorted(
        str(item["name"])
        for item in services
        if isinstance(item, dict) and item.get("name") != "bootstrap"
    )
    expected_roles.append("bootstrap")
    expected_roles.sort()
    if live_roles != expected_roles:
        raise RuntimeError("live performance role set changed")
    image_id = environment.get("LOCUS_INTEGRATED_IMAGE_ID")
    if not isinstance(image_id, str) or IMAGE_ID_PATTERN.fullmatch(image_id) is None:
        raise RuntimeError("performance image identity is unavailable")
    result = {
        "admission_profile_id": "LOCUS-local-synthetic-admission-v1",
        "backup_format_id": "LOCUS-reference-backup-v6",
        "client_api_id": CLIENT_API_VERSION,
        "client_instance_profile_id": "LOCUS-managed-client-instance-v1",
        "compose_sha256": hashlib.sha256(MANAGED_COMPOSE.read_bytes()).hexdigest(),
        "configuration_id": "LOCUS-integrated-manager-config-v1",
        "controller_api_id": "LOCUS-container-controller-api-v1",
        "deployment_id": "LOCUS-integrated-manager-deployment-v1",
        "descriptor_id": "LOCUS-recovery-descriptor-v1",
        "host_tier": "same-host-single-operator",
        "image_id": image_id,
        "live_graph_sha256": digest(
            {
                "dynamic_client": "LOCUS-managed-client-instance-v1",
                "roles": live_roles,
                "status": "validated",
            }
        ),
        "lockfile_sha256": provenance["lockfile_sha256"],
        "managed_manifest_sha256": provenance["managed_manifest_sha256"],
        "manager_api_id": "LOCUS-manager-api-v1",
        "network_topology_sha256": digest(
            {
                "networks": networks,
                "service_networks": [
                    {
                        "name": item["name"],
                        "networks": item["networks"],
                    }
                    for item in services
                    if isinstance(item, dict)
                ],
            }
        ),
        "package_profile_id": "LOCUS-client-recovery-package-v1",
        "provider_id": "LOCUS-storage-provider-s3-compatible-v1",
        "resolved_graph_sha256": digest(normalized),
        "service_identity_set_sha256": digest(
            [
                {"identity": item["identity"], "name": item["name"]}
                for item in services
                if isinstance(item, dict)
            ]
        ),
        "source_commit": provenance["source_commit"],
        "source_tree_sha256": provenance["source_tree_sha256"],
    }
    return result


def _performance_pseudonym(prefix: str, value: str) -> str:
    return f"{prefix}-{hashlib.sha256(value.encode('utf-8')).hexdigest()[:16]}"


def _performance_bindings(
    *,
    base: dict[str, object],
    project: str,
    host_id: str,
    client_session: dict[str, object] | None,
    packages: Sequence[bytes],
) -> dict[str, object]:
    identity = (
        "no-active-client"
        if client_session is None
        else str(client_session.get("client_identity", "invalid-client"))
    )
    package_set = hashlib.sha256()
    for package in sorted(hashlib.sha256(item).digest() for item in packages):
        package_set.update(package)
    result = dict(base)
    result.update(
        {
            "collected_at_utc": dt.datetime.now(dt.UTC)
            .replace(microsecond=0)
            .isoformat(),
            "pseudonymous_client_id": _performance_pseudonym("client", identity),
            "pseudonymous_host_id": host_id,
            "pseudonymous_package_set_id": f"packages-{package_set.hexdigest()[:16]}",
            "pseudonymous_project_id": _performance_pseudonym("project", project),
        }
    )
    return result


def _performance_create_client(
    manager_port: int, manager_csrf: str
) -> tuple[dict[str, object], int, dict[str, object]]:
    client = _create_client(manager_port, manager_csrf)
    port = cast(int, client["port"])
    session = _client_session(port)
    return client, port, session


def _performance_destroy_client(
    manager_port: int,
    manager_csrf: str,
    client: dict[str, object],
    client_port: int,
) -> None:
    identifier = client.get("id")
    if not isinstance(identifier, str):
        raise RuntimeError("managed Client identity is unavailable")
    result = _manager_post(
        manager_port,
        manager_csrf,
        "/api/manager/v1/client-destroy",
        {
            "container_id": identifier,
            "operation_id": _operation_id("performance-destroy-client"),
        },
    )
    if result.get("status") != "destroyed":
        raise RuntimeError("Manager did not destroy the performance Client")
    _wait_client_removed(manager_port, client_port)


def _performance_generate_key(client_port: int, csrf: str) -> str:
    generated = _client_post(
        client_port,
        csrf,
        "/api/v2/key/generate",
        {
            "api_version": CLIENT_API_VERSION,
            "operation_id": _operation_id("performance-generate-key"),
        },
    )
    key = generated.get("private_key")
    if not isinstance(key, str) or len(key) != 64:
        raise RuntimeError("performance Client did not generate a synthetic key")
    return key


def _performance_manager_post(
    port: int,
    csrf: str,
    path: str,
    value: dict[str, object],
    *,
    expected: tuple[int, ...] = (200,),
) -> tuple[dict[str, object], int, dict[str, int]]:
    body = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    started = time.perf_counter_ns()
    encoded, _headers = _raw_request(
        port,
        path,
        method="POST",
        body=body,
        content_type="application/json",
        csrf=csrf,
        expected=expected,
    )
    elapsed = time.perf_counter_ns() - started
    result = json.loads(encoded)
    if not isinstance(result, dict):
        raise RuntimeError("Manager returned a non-object")
    count = len(body) + len(encoded)
    return (
        cast(dict[str, object], result),
        elapsed,
        {"browser": count, "manager-ui": count},
    )


def _performance_manager_action(
    port: int, csrf: str, role: str, action: str
) -> tuple[dict[str, object], int, dict[str, int]]:
    status_started = time.perf_counter_ns()
    encoded_status, _headers = _raw_request(port, "/api/manager/v1/status")
    status_elapsed = time.perf_counter_ns() - status_started
    status = json.loads(encoded_status)
    containers = status.get("containers") if isinstance(status, dict) else None
    matches = [
        item
        for item in containers or []
        if isinstance(item, dict) and item.get("role") == role
    ]
    if len(matches) != 1 or not isinstance(matches[0].get("id"), str):
        raise RuntimeError(f"Manager role inventory is ambiguous: {role}")
    result, action_elapsed, bodies = _performance_manager_post(
        port,
        csrf,
        "/api/manager/v1/container-action",
        {
            "action": action,
            "container_id": cast(str, matches[0]["id"]),
            "operation_id": _operation_id(f"performance-{role}-{action}"),
        },
    )
    status_count = len(encoded_status)
    bodies["browser"] = bodies.get("browser", 0) + status_count
    bodies["manager-ui"] = bodies.get("manager-ui", 0) + status_count
    return result, status_elapsed + action_elapsed, bodies


def _performance_clear_client(runtime: _PerformanceRuntime) -> None:
    runtime.client = None
    runtime.client_port = None
    runtime.client_session = None
    runtime.client_csrf = None


def _performance_destroy_active(runtime: _PerformanceRuntime) -> None:
    if runtime.client is None:
        return
    assert runtime.client_port is not None
    _performance_destroy_client(
        runtime.manager_port,
        runtime.manager_csrf,
        runtime.client,
        runtime.client_port,
    )
    _performance_clear_client(runtime)


def _performance_new_active(
    runtime: _PerformanceRuntime,
    *,
    generate_key: bool = False,
    imported_package: bytes | None = None,
) -> None:
    _performance_destroy_active(runtime)
    client, port, session = _performance_create_client(
        runtime.manager_port, runtime.manager_csrf
    )
    runtime.client = client
    runtime.client_port = port
    runtime.client_session = session
    runtime.client_csrf = cast(str, session["csrf_token"])
    if generate_key:
        runtime.secret_markers.append(
            _performance_generate_key(port, runtime.client_csrf)
        )
    if imported_package is not None:
        imported = _client_package_import(port, runtime.client_csrf, imported_package)
        if imported.get("status") != "package_authenticated":
            raise RuntimeError("performance Client did not authenticate its package")


def _performance_record(
    *,
    runtime: _PerformanceRuntime,
    slot: dict[str, object],
    elapsed_ns: int,
    phases: dict[str, int],
    bodies: dict[str, int],
    status: str,
    packages: Sequence[bytes],
    persisted: dict[str, int] | None = None,
    concurrency: dict[str, int] | None = None,
) -> dict[str, object]:
    scenario_id = cast(str, slot["scenario_id"])
    affordable = scenario_id.startswith("AP")
    if persisted is None:
        persisted = _performance_persisted_bytes(
            runtime.project, runtime.environment, runtime.client
        )
    ui_required = scenario_id in {
        "MP01",
        "MP02",
        "MP03",
        "MP04",
        "MP05",
        "MP06",
        "MP14",
        "MP15",
        "MP16",
        "MP17",
        "MP18",
        "MP19",
    }
    lifecycle = cast(str, slot["category"]) == "lifecycle"
    if affordable:
        from locus.affordable_performance_evidence import (
            build_metrics as affordable_build_metrics,
            build_observation as affordable_build_observation,
        )

        metrics = affordable_build_metrics(
            slot=slot,
            end_to_end_ns=elapsed_ns,
            phase_latency_ns=phases,
            application_body_bytes_by_role=bodies,
            persisted_bytes_by_role=persisted,
        )
    else:
        from locus.performance_collection import (
            build_metrics as legacy_build_metrics,
            build_observation as legacy_build_observation,
        )

        metrics = legacy_build_metrics(
            slot=slot,
            end_to_end_ns=elapsed_ns,
            phase_latency_ns=phases,
            application_body_bytes_by_role=bodies,
            persisted_bytes_by_role=persisted,
            ui_http_round_trip_ns=elapsed_ns if ui_required else None,
            lifecycle_ns=elapsed_ns if lifecycle else None,
            concurrency=concurrency,
        )
    bindings = _performance_bindings(
        base=runtime.base_bindings,
        project=runtime.project,
        host_id=runtime.host_id,
        client_session=runtime.client_session,
        packages=packages,
    )
    if affordable:
        return affordable_build_observation(
            slot=slot, bindings=bindings, metrics=metrics, status=status
        )
    return legacy_build_observation(
        slot=slot, bindings=bindings, metrics=metrics, status=status
    )


def _performance_enroll_request(
    arm: dict[str, object], operation_id: str
) -> dict[str, object]:
    return {
        "api_version": CLIENT_API_VERSION,
        "deployment_profile_id": arm["topology_id"],
        "operation_id": operation_id,
        "policy_id": arm["policy_id"],
        "recovery_input": _policy_inputs()[cast(str, arm["policy_id"])],
        "suite_id": arm["suite_id"],
    }


def _performance_warmup(
    runtime: _PerformanceRuntime, slot: dict[str, object]
) -> dict[str, object]:
    arm = cast(dict[str, object], slot["arm"])
    _performance_new_active(runtime, generate_key=True)
    assert runtime.client_port is not None and runtime.client_csrf is not None
    enrolled = _client_post(
        runtime.client_port,
        runtime.client_csrf,
        "/api/v2/enroll",
        _performance_enroll_request(
            arm, _operation_id(f"performance-warmup-{slot['arm_id']}")
        ),
    )
    download_id = enrolled.get("download_id")
    if enrolled.get("status") != "enrolled" or not isinstance(download_id, str):
        raise RuntimeError("performance warm-up enrollment failed")
    package = _client_package_export(
        runtime.client_port, runtime.client_csrf, download_id
    )
    _performance_new_active(runtime, imported_package=package)
    assert runtime.client_port is not None and runtime.client_csrf is not None
    selected = cast(list[int], arm["holders"])[: cast(int, arm["k"])]
    recovered = _client_post(
        runtime.client_port,
        runtime.client_csrf,
        "/api/v2/recover",
        {
            "api_version": CLIENT_API_VERSION,
            "operation_id": _operation_id("performance-warmup-recover"),
            "recovery_input": _policy_inputs()[cast(str, arm["policy_id"])],
            "selected_holder_ids": selected,
        },
    )
    if recovered.get("status") != "recovered":
        raise RuntimeError("performance warm-up recovery failed")
    runtime.base_package = package
    _performance_destroy_active(runtime)
    bindings = _performance_bindings(
        base=runtime.base_bindings,
        project=runtime.project,
        host_id=runtime.host_id,
        client_session=None,
        packages=[package],
    )
    if str(slot["scenario_id"]).startswith("AP"):
        from locus.affordable_performance_evidence import (
            build_observation as affordable_build_observation,
        )

        return affordable_build_observation(
            slot=slot, bindings=bindings, metrics=None, status="warmup-passed"
        )
    from locus.performance_collection import (
        build_observation as legacy_build_observation,
    )

    return legacy_build_observation(
        slot=slot, bindings=bindings, metrics=None, status="warmup-passed"
    )


def _performance_wrong_input(policy_id: str) -> object:
    value = json.loads(json.dumps(_policy_inputs()[policy_id]))
    if policy_id == "LOCUS-canonical-email-set-v1":
        value[0] = "wrong@example.invalid"
    elif policy_id == "LOCUS-location-person-set-v1":
        value[0]["person"]["value"] = "wrong@example.invalid"
    else:  # pragma: no cover - D028 has exactly the two paired policies
        raise RuntimeError("unsupported performance policy")
    return value


def _performance_recovery_request(
    *,
    arm: dict[str, object],
    operation: str,
    selected: Sequence[int],
    wrong_input: bool = False,
) -> dict[str, object]:
    policy_id = cast(str, arm["policy_id"])
    return {
        "api_version": CLIENT_API_VERSION,
        "operation_id": _operation_id(operation),
        "recovery_input": (
            _performance_wrong_input(policy_id)
            if wrong_input
            else _policy_inputs()[policy_id]
        ),
        "selected_holder_ids": list(selected),
    }


def _performance_measure_arm_slot(
    runtime: _PerformanceRuntime, slot: dict[str, object]
) -> dict[str, object]:
    scenario = cast(str, slot["scenario_id"])
    scenario = {
        "AP01": "MP01",
        "AP02": "MP02",
        "AP03": "MP04",
        "AP04": "MP05",
        "AP05": "MP06",
        "AP06": "MP11",
    }.get(scenario, scenario)
    arm = cast(dict[str, object], slot["arm"])
    base_package = runtime.base_package
    if base_package is None:
        raise RuntimeError("performance arm lacks its warm-up package")
    policy_id = cast(str, arm["policy_id"])
    holders = cast(list[int], arm["holders"])
    threshold = cast(int, arm["k"])
    selected = holders[:threshold]
    packages: list[bytes] = [base_package]
    phases: dict[str, int] = {}
    bodies: dict[str, int] = {}
    elapsed = 0
    status = "valid-success"
    concurrency: dict[str, int] | None = None
    persisted: dict[str, int] | None = None

    if scenario == "MP01":
        _performance_new_active(runtime, generate_key=True)
        assert runtime.client_port is not None and runtime.client_csrf is not None
        result, elapsed, phases, bodies = _performance_client_json(
            runtime.client_port,
            runtime.client_csrf,
            "/api/v2/enroll",
            _performance_enroll_request(
                arm, _operation_id(f"performance-enroll-{slot['slot_id']}")
            ),
        )
        download_id = result.get("download_id")
        if result.get("status") != "enrolled" or not isinstance(download_id, str):
            raise RuntimeError("measured enrollment failed")
        package = _client_package_export(
            runtime.client_port, runtime.client_csrf, download_id
        )
        packages.append(package)
    elif scenario == "MP02":
        _performance_new_active(runtime, generate_key=True)
        assert runtime.client_port is not None and runtime.client_csrf is not None
        enrolled = _client_post(
            runtime.client_port,
            runtime.client_csrf,
            "/api/v2/enroll",
            _performance_enroll_request(
                arm, _operation_id(f"performance-package-fixture-{slot['slot_id']}")
            ),
        )
        download_id = enrolled.get("download_id")
        if not isinstance(download_id, str):
            raise RuntimeError("package measurement fixture failed")
        package, export_ns, export_body = _performance_client_export(
            runtime.client_port, runtime.client_csrf, download_id
        )
        _performance_new_active(runtime)
        assert runtime.client_port is not None and runtime.client_csrf is not None
        imported, import_ns, _import_phases, import_body = _performance_client_import(
            runtime.client_port, runtime.client_csrf, package
        )
        if imported.get("status") != "package_authenticated":
            raise RuntimeError("measured package import failed")
        elapsed = export_ns + import_ns
        bodies = _sum_role_bytes(export_body, import_body)
        packages.append(package)
    elif scenario == "MP03":
        _performance_new_active(runtime)
        assert runtime.client_port is not None and runtime.client_csrf is not None
        imported, elapsed, phases, bodies = _performance_client_import(
            runtime.client_port, runtime.client_csrf, base_package
        )
        if imported.get("status") != "package_authenticated":
            raise RuntimeError("measured clean bootstrap failed")
    elif scenario in {"MP04", "MP05", "MP06", "MP07", "MP08"}:
        _performance_new_active(runtime, imported_package=base_package)
        assert runtime.client_port is not None and runtime.client_csrf is not None
        recovery_selected = selected
        wrong = scenario == "MP05"
        expected = (400,) if scenario in {"MP05", "MP07"} else (200,)
        if scenario == "MP06":
            _manager_action(
                runtime.manager_port, runtime.manager_csrf, "party1", "stop"
            )
            _wait_role(runtime.manager_port, "party1", state="exited")
            recovery_selected = holders[1 : threshold + 1]
        elif scenario == "MP07":
            recovery_selected = holders[: threshold - 1]
        restart_ns = 0
        restart_body: dict[str, int] = {}
        if scenario == "MP08":
            _result, restart_ns, restart_body = _performance_manager_action(
                runtime.manager_port, runtime.manager_csrf, "party1", "restart"
            )
            _wait_role(runtime.manager_port, "party1", state="running", healthy=True)
            recovery_selected = [1, *[item for item in holders if item != 1]][
                :threshold
            ]
        result, recovery_ns, phases, recovery_body = _performance_client_json(
            runtime.client_port,
            runtime.client_csrf,
            "/api/v2/recover",
            _performance_recovery_request(
                arm=arm,
                operation=f"performance-recover-{slot['slot_id']}",
                selected=recovery_selected,
                wrong_input=wrong,
            ),
            expected=expected,
        )
        elapsed = restart_ns + recovery_ns
        bodies = _sum_role_bytes(restart_body, recovery_body)
        if scenario in {"MP05", "MP07"}:
            if result.get("category") != "recovery_rejected":
                raise RuntimeError("expected recovery rejection did not occur")
            status = "valid-expected-rejection"
        elif result.get("status") != "recovered":
            raise RuntimeError("measured recovery failed")
        if scenario == "MP06":
            _manager_action(
                runtime.manager_port, runtime.manager_csrf, "party1", "start"
            )
            _wait_role(runtime.manager_port, "party1", state="running", healthy=True)
    elif scenario == "MP09":
        _performance_new_active(runtime, imported_package=base_package)
        assert runtime.client_port is not None
        started = time.perf_counter_ns()
        _manager_action(runtime.manager_port, runtime.manager_csrf, "client", "restart")
        item = _wait_role(runtime.manager_port, "client", state="running", healthy=True)
        port = item.get("port")
        if not isinstance(port, int):
            raise RuntimeError("restarted Client lost its loopback port")
        runtime.client_port = port
        runtime.client_session = _client_session(port)
        runtime.client_csrf = cast(str, runtime.client_session["csrf_token"])
        imported, import_ns, _import_phases, import_body = _performance_client_import(
            port, runtime.client_csrf, base_package
        )
        if imported.get("status") != "package_authenticated":
            raise RuntimeError("restarted Client rejected its package")
        recovered, recover_ns, phases, recover_body = _performance_client_json(
            port,
            runtime.client_csrf,
            "/api/v2/recover",
            _performance_recovery_request(
                arm=arm,
                operation=f"performance-client-restart-{slot['slot_id']}",
                selected=selected,
            ),
        )
        if recovered.get("status") != "recovered":
            raise RuntimeError("restarted Client recovery failed")
        elapsed = time.perf_counter_ns() - started
        if elapsed < import_ns + recover_ns:
            raise RuntimeError("client restart timing is inconsistent")
        bodies = _sum_role_bytes(import_body, recover_body)
    elif scenario == "MP10":
        _performance_destroy_active(runtime)
        started = time.perf_counter_ns()
        _stop_through_manager(
            runtime.manager_port,
            runtime.manager_csrf,
            label="performance-preserved-system-stop",
        )
        _wait_project_stopped(runtime.project, runtime.environment)
        _performance_clear_client(runtime)
        _status, runtime.manager_csrf = _resume_project(
            project=runtime.project,
            manager_port=runtime.manager_port,
            environment=runtime.environment,
        )
        _performance_new_active(runtime)
        assert runtime.client_port is not None and runtime.client_csrf is not None
        imported, _import_ns, _import_phases, import_body = _performance_client_import(
            runtime.client_port, runtime.client_csrf, base_package
        )
        if imported.get("status") != "package_authenticated":
            raise RuntimeError("preserved system rejected its package")
        recovered, _recover_ns, phases, recover_body = _performance_client_json(
            runtime.client_port,
            runtime.client_csrf,
            "/api/v2/recover",
            _performance_recovery_request(
                arm=arm,
                operation=f"performance-system-restart-{slot['slot_id']}",
                selected=selected,
            ),
        )
        if recovered.get("status") != "recovered":
            raise RuntimeError("preserved system recovery failed")
        elapsed = time.perf_counter_ns() - started
        bodies = _sum_role_bytes(import_body, recover_body)
    elif scenario == "MP11":
        started = time.perf_counter_ns()
        persisted = _performance_persisted_bytes(
            runtime.project, runtime.environment, runtime.client
        )
        elapsed = time.perf_counter_ns() - started
    elif scenario == "MP12":
        _performance_new_active(runtime, generate_key=True)
        assert runtime.client_port is not None and runtime.client_csrf is not None
        predecessor = _client_post(
            runtime.client_port,
            runtime.client_csrf,
            "/api/v2/enroll",
            _performance_enroll_request(
                arm, _operation_id(f"performance-successor-fixture-{slot['slot_id']}")
            ),
        )
        predecessor_download = predecessor.get("download_id")
        if not isinstance(predecessor_download, str):
            raise RuntimeError("successor fixture enrollment failed")
        successor_package = _client_package_export(
            runtime.client_port, runtime.client_csrf, predecessor_download
        )
        packages.append(successor_package)
        _performance_new_active(runtime, imported_package=successor_package)
        assert runtime.client_port is not None and runtime.client_csrf is not None
        target = cast(dict[str, object], slot["target_arm"])
        result, elapsed, phases, bodies = _performance_client_json(
            runtime.client_port,
            runtime.client_csrf,
            "/api/v2/successor",
            {
                "api_version": CLIENT_API_VERSION,
                "operation_id": _operation_id(
                    f"performance-successor-{slot['slot_id']}"
                ),
                "recovery_input": _policy_inputs()[policy_id],
                "rotate_protected_key": False,
                "successor_deployment_profile_id": target["topology_id"],
                "successor_suite_id": target["suite_id"],
            },
        )
        if result.get("status") != "successor_enrolled":
            raise RuntimeError("measured successor transition failed")
    elif scenario == "MP13":
        _performance_new_active(runtime, imported_package=base_package)
        assert runtime.client_port is not None and runtime.client_csrf is not None
        concurrent_port = runtime.client_port
        concurrent_csrf = runtime.client_csrf
        level = cast(int, slot["concurrency_level"])
        requests = [
            _performance_recovery_request(
                arm=arm,
                operation=f"performance-concurrent-{slot['slot_id']}-{index}",
                selected=selected,
            )
            for index in range(level)
        ]
        encoded_requests = [
            json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
            for value in requests
        ]
        started = time.perf_counter_ns()
        with ThreadPoolExecutor(max_workers=level) as executor:
            results = list(
                executor.map(
                    lambda request: _client_post(
                        concurrent_port,
                        concurrent_csrf,
                        "/api/v2/recover",
                        request,
                    ),
                    requests,
                )
            )
        elapsed = time.perf_counter_ns() - started
        if any(result.get("status") != "recovered" for result in results):
            raise RuntimeError("concurrent recovery batch failed")
        response_bytes = sum(
            len(json.dumps(item, sort_keys=True, separators=(",", ":")).encode())
            for item in results
        )
        body_count = sum(len(item) for item in encoded_requests) + response_bytes
        bodies = {"browser": body_count, "managed-client": body_count}
        concurrency = {
            "batch_completion_ns": elapsed,
            "completed_operations": level,
            "level": level,
            "operations_per_second_milli": max(1, level * 10**12 // elapsed),
        }
    else:  # pragma: no cover - the fixed arm schedule is exhaustive
        raise RuntimeError(f"unsupported performance scenario: {scenario}")

    return _performance_record(
        runtime=runtime,
        slot=slot,
        elapsed_ns=elapsed,
        phases=phases,
        bodies=bodies,
        status=status,
        packages=packages,
        persisted=persisted,
        concurrency=concurrency,
    )


def _performance_lifecycle_block(
    runtime: _PerformanceRuntime,
    slots: Sequence[dict[str, object]],
    startup_ns: int,
) -> list[dict[str, object]]:
    by_scenario = {cast(str, slot["scenario_id"]): slot for slot in slots}
    if set(by_scenario) != {"MP14", "MP15", "MP16", "MP17", "MP18", "MP19"}:
        raise RuntimeError("lifecycle schedule changed")
    observations = [
        _performance_record(
            runtime=runtime,
            slot=by_scenario["MP14"],
            elapsed_ns=startup_ns,
            phases={},
            bodies={},
            status="valid-success",
            packages=[],
        )
    ]
    created, create_ns, create_body = _performance_manager_post(
        runtime.manager_port,
        runtime.manager_csrf,
        "/api/manager/v1/clients",
        {"operation_id": _operation_id("performance-lifecycle-create")},
        expected=(201,),
    )
    client = created.get("client")
    if not isinstance(client, dict) or not isinstance(client.get("port"), int):
        raise RuntimeError("lifecycle Client creation failed")
    runtime.client = cast(dict[str, object], client)
    runtime.client_port = cast(int, client["port"])
    runtime.client_session = _client_session(runtime.client_port)
    runtime.client_csrf = cast(str, runtime.client_session["csrf_token"])
    observations.append(
        _performance_record(
            runtime=runtime,
            slot=by_scenario["MP15"],
            elapsed_ns=create_ns,
            phases={},
            bodies=create_body,
            status="valid-success",
            packages=[],
        )
    )
    _result, stop_ns, stop_body = _performance_manager_action(
        runtime.manager_port, runtime.manager_csrf, "client", "stop"
    )
    _wait_role(runtime.manager_port, "client", state="exited")
    observations.append(
        _performance_record(
            runtime=runtime,
            slot=by_scenario["MP16"],
            elapsed_ns=stop_ns,
            phases={},
            bodies=stop_body,
            status="valid-success",
            packages=[],
        )
    )
    _result, start_ns, start_body = _performance_manager_action(
        runtime.manager_port, runtime.manager_csrf, "client", "start"
    )
    item = _wait_role(runtime.manager_port, "client", state="running", healthy=True)
    if not isinstance(item.get("port"), int):
        raise RuntimeError("lifecycle Client start lost its port")
    runtime.client_port = cast(int, item["port"])
    runtime.client_session = _client_session(runtime.client_port)
    runtime.client_csrf = cast(str, runtime.client_session["csrf_token"])
    observations.append(
        _performance_record(
            runtime=runtime,
            slot=by_scenario["MP17"],
            elapsed_ns=start_ns,
            phases={},
            bodies=start_body,
            status="valid-success",
            packages=[],
        )
    )
    prior_identity = runtime.client_session.get("client_identity")
    _result, restart_ns, restart_body = _performance_manager_action(
        runtime.manager_port, runtime.manager_csrf, "client", "restart"
    )
    item = _wait_role(runtime.manager_port, "client", state="running", healthy=True)
    if not isinstance(item.get("port"), int):
        raise RuntimeError("lifecycle Client restart lost its port")
    runtime.client_port = cast(int, item["port"])
    runtime.client_session = _client_session(runtime.client_port)
    runtime.client_csrf = cast(str, runtime.client_session["csrf_token"])
    if runtime.client_session.get("client_identity") == prior_identity:
        raise RuntimeError("lifecycle Client restart did not rotate identity")
    observations.append(
        _performance_record(
            runtime=runtime,
            slot=by_scenario["MP18"],
            elapsed_ns=restart_ns,
            phases={},
            bodies=restart_body,
            status="valid-success",
            packages=[],
        )
    )
    assert runtime.client is not None and runtime.client_port is not None
    identifier = runtime.client.get("id")
    if not isinstance(identifier, str):
        raise RuntimeError("lifecycle Client identity is unavailable")
    destroyed, destroy_ns, destroy_body = _performance_manager_post(
        runtime.manager_port,
        runtime.manager_csrf,
        "/api/manager/v1/client-destroy",
        {
            "container_id": identifier,
            "operation_id": _operation_id("performance-lifecycle-destroy"),
        },
    )
    if destroyed.get("status") != "destroyed":
        raise RuntimeError("lifecycle Client destruction failed")
    _wait_client_removed(runtime.manager_port, runtime.client_port)
    _performance_clear_client(runtime)
    observations.append(
        _performance_record(
            runtime=runtime,
            slot=by_scenario["MP19"],
            elapsed_ns=destroy_ns,
            phases={},
            bodies=destroy_body,
            status="valid-success",
            packages=[],
        )
    )
    return observations


def _performance_output_scan(runtime: _PerformanceRuntime) -> None:
    """Scan bounded ephemeral output, retaining only the pass/fail observation."""

    from locus.redaction import exposed_categories

    outputs = [
        run_capture(
            [*_compose(runtime.project), "logs", "--no-color"],
            env=runtime.environment,
            check=False,
            include_stderr=True,
            visible=False,
        )
    ]
    for identifier in _dynamic_client_ids(runtime.project, runtime.environment):
        outputs.append(
            run_capture(
                [require("docker"), "logs", identifier],
                env=runtime.environment,
                check=False,
                include_stderr=True,
                visible=False,
            )
        )
    markers = {
        "storage-access-key": runtime.environment["LOCUS_S3_ACCESS_KEY"],
        "storage-secret-key": runtime.environment["LOCUS_S3_SECRET_KEY"],
        "synthetic-email": "Ada@Example.COM",
        "synthetic-phone": "+352621000002",
        "synthetic-location": "49.6116",
        **{
            f"synthetic-private-key-{index}": value
            for index, value in enumerate(runtime.secret_markers, start=1)
        },
    }
    findings = exposed_categories("".join(outputs), markers)
    if findings:
        raise RuntimeError(
            "performance output scan found prohibited categories: " + ",".join(findings)
        )


def _performance_chain_observation(
    observation: dict[str, object],
    prior: dict[str, object] | None,
) -> dict[str, object]:
    slot = cast(dict[str, object], observation["slot"])
    if str(slot["scenario_id"]).startswith("AP"):
        from locus.affordable_performance_evidence import validate_observation
        from locus.performance_evidence import digest
    else:
        from locus.performance_evidence import digest, validate_observation

    result = dict(observation)
    attempt_index = 1 if prior is None else cast(int, prior["attempt_index"]) + 1
    slot = cast(dict[str, object], result["slot"])
    result["attempt_id"] = f"{slot['slot_id']}:a{attempt_index:02d}"
    result["attempt_index"] = attempt_index
    result["replacement_of_sha256"] = None if prior is None else digest(prior)
    validate_observation(result)
    return result


def _performance_invalid_block(
    *,
    runtime: _PerformanceRuntime,
    slots: Sequence[dict[str, object]],
    prior_by_slot: dict[str, dict[str, object]],
    invalid_category: str = "orchestrator-failure",
) -> list[dict[str, object]]:
    from locus.performance_evidence import digest

    affordable = bool(slots) and str(slots[0]["scenario_id"]).startswith("AP")
    observation_builder: Any
    if affordable:
        from locus.affordable_performance_evidence import (
            build_observation as affordable_build_observation,
        )

        observation_builder = affordable_build_observation
    else:
        from locus.performance_collection import (
            build_observation as legacy_build_observation,
        )

        observation_builder = legacy_build_observation

    bindings = _performance_bindings(
        base=runtime.base_bindings,
        project=runtime.project,
        host_id=runtime.host_id,
        client_session=None,
        packages=[],
    )
    result: list[dict[str, object]] = []
    for slot in slots:
        slot_id = cast(str, slot["slot_id"])
        prior = prior_by_slot.get(slot_id)
        arguments = {
            "slot": slot,
            "bindings": bindings,
            "metrics": None,
            "status": "infrastructure-invalid",
            "attempt_index": (
                1 if prior is None else cast(int, prior["attempt_index"]) + 1
            ),
            "replacement_of_sha256": None if prior is None else digest(prior),
            "invalid_category": invalid_category,
            "cleanup_complete": True,
        }
        invalid = observation_builder(**arguments)
        result.append(invalid)
    return result


def _performance_project_name(arm_id: str, block: int, attempt: int) -> str:
    return _project(
        f"locus-perf-{arm_id.replace('of', '')}-b{block:02d}-a{attempt:02d}"
    )


def _collect_performance_observations(
    *, provenance: dict[str, object]
) -> list[dict[str, object]]:
    """Execute the exact D028 schedule with fresh projects per arm/block."""

    from locus.performance_collection import common_block_slots, ordered_arm_block_slots
    from locus.performance_evidence import ARMS, process_observations

    global _PERFORMANCE_EVIDENCE_ACTIVE
    if _PERFORMANCE_EVIDENCE_ACTIVE:
        raise RuntimeError("performance collection is already active")
    _PERFORMANCE_EVIDENCE_ACTIVE = True
    observations: list[dict[str, object]] = []
    prior_by_slot: dict[str, dict[str, object]] = {}
    try:
        for block in range(1, 11):
            for arm_id, arm in ARMS.items():
                arm_slots = list(ordered_arm_block_slots(arm_id, block))
                common_slots = (
                    list(common_block_slots(block)) if arm_id == "yi-2of3" else []
                )
                project_slots = [*common_slots, *arm_slots]
                for attempt in range(1, 4):
                    project = _performance_project_name(arm_id, block, attempt)
                    manager_port = DEFAULT_MANAGER_PORT
                    environment = _environment(project, manager_port)
                    topology_id = cast(str, arm["topology_id"])
                    environment["LOCUS_PERFORMANCE_FIXTURE_ID"] = (
                        f"{topology_id}:block-{block:02d}"
                    )
                    runtime: _PerformanceRuntime | None = None
                    project_observations: list[dict[str, object]] = []
                    operation_error: BaseException | None = None
                    startup_timing: list[int] = []
                    try:
                        status = _start_project(
                            project=project,
                            manager_port=manager_port,
                            environment=environment,
                            startup_timing=startup_timing,
                        )
                        manager_csrf = _manager_session(manager_port)
                        base = _performance_base_bindings(
                            project=project,
                            environment=environment,
                            status=status,
                            provenance=provenance,
                        )
                        runtime = _PerformanceRuntime(
                            project=project,
                            manager_port=manager_port,
                            manager_csrf=manager_csrf,
                            environment=environment,
                            base_bindings=base,
                            host_id=cast(str, provenance["pseudonymous_host_id"]),
                        )
                        if common_slots:
                            if len(startup_timing) != 1:
                                raise RuntimeError("startup timing was not observed")
                            project_observations.extend(
                                _performance_lifecycle_block(
                                    runtime, common_slots, startup_timing[0]
                                )
                            )
                        project_observations.append(
                            _performance_warmup(runtime, arm_slots[0])
                        )
                        for slot in arm_slots[1:]:
                            project_observations.append(
                                _performance_measure_arm_slot(runtime, slot)
                            )
                    except BaseException as error:
                        operation_error = error

                    if runtime is None:
                        try:
                            _cleanup_smoke_project(project, environment)
                        except BaseException as cleanup_error:
                            if operation_error is not None:
                                operation_error.add_note(
                                    "startup cleanup also failed: "
                                    f"{type(cleanup_error).__name__}: {cleanup_error}"
                                )
                        assert operation_error is not None
                        raise operation_error

                    try:
                        _performance_output_scan(runtime)
                    except BaseException as scan_error:
                        operation_error = scan_error
                    try:
                        _cleanup_smoke_project(project, environment)
                    except BaseException as cleanup_error:
                        if operation_error is None:
                            operation_error = cleanup_error
                        else:
                            operation_error.add_note(
                                "performance cleanup also failed: "
                                f"{type(cleanup_error).__name__}: {cleanup_error}"
                            )

                    if operation_error is not None:
                        if "output scan" in str(operation_error) or "cleanup" in str(
                            operation_error
                        ):
                            raise operation_error
                        invalid = _performance_invalid_block(
                            runtime=runtime,
                            slots=project_slots,
                            prior_by_slot=prior_by_slot,
                        )
                        for item in invalid:
                            slot_id = cast(
                                str, cast(dict[str, object], item["slot"])["slot_id"]
                            )
                            prior_by_slot[slot_id] = item
                        observations.extend(invalid)
                        print(
                            json.dumps(
                                {
                                    "arm": arm_id,
                                    "attempt": attempt,
                                    "block": block,
                                    "category": "infrastructure-invalid",
                                    "status": "retrying",
                                },
                                sort_keys=True,
                            ),
                            flush=True,
                        )
                        if attempt == 3:
                            raise RuntimeError(
                                "performance arm/block exhausted bounded retries"
                            ) from operation_error
                        continue

                    for item in project_observations:
                        slot_id = cast(
                            str, cast(dict[str, object], item["slot"])["slot_id"]
                        )
                        chained = _performance_chain_observation(
                            item, prior_by_slot.get(slot_id)
                        )
                        prior_by_slot[slot_id] = chained
                        observations.append(chained)
                    print(
                        json.dumps(
                            {
                                "arm": arm_id,
                                "attempt": attempt,
                                "block": block,
                                "slots": len(project_observations),
                                "status": "passed",
                            },
                            sort_keys=True,
                        ),
                        flush=True,
                    )
                    break
        process_observations(observations)
        return observations
    finally:
        _PERFORMANCE_EVIDENCE_ACTIVE = False


def _affordable_checkpoint_write(path: Path, value: dict[str, object]) -> None:
    """Atomically replace coordination metadata; it is never retained evidence."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_bytes(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode() + b"\n"
    )
    os.replace(temporary, path)


def _affordable_staged_observations(staging: Path) -> list[dict[str, object]]:
    from locus.affordable_performance_evidence import validate_observation

    raw = staging / "raw"
    if not raw.exists():
        return []
    observations: list[dict[str, object]] = []
    for path in sorted(raw.rglob("attempt-*.json")):
        value = json.loads(path.read_bytes())
        if not isinstance(value, dict):
            raise RuntimeError("affordable staging contains a non-object")
        observations.append(validate_observation(value))
    return observations


def _collect_affordable_performance_observations(
    *, provenance: dict[str, object], retain: bool
) -> list[dict[str, object]]:
    """Execute D030's 12-project/324-slot schedule with resumable block staging."""

    from locus.affordable_performance_collection import ordered_arm_block_slots
    from locus.affordable_performance_evidence import (
        ARMS,
        STAGING_ROOT,
        checkpoint_profile,
        exclusive_write,
        process_observations,
    )
    from locus.affordable_performance_methodology import methodology_contract
    from locus.performance_evidence import digest

    global _PERFORMANCE_EVIDENCE_ACTIVE, _PERFORMANCE_INSTRUMENTATION_ID
    if _PERFORMANCE_EVIDENCE_ACTIVE:
        raise RuntimeError("performance collection is already active")
    _PERFORMANCE_EVIDENCE_ACTIVE = True
    _PERFORMANCE_INSTRUMENTATION_ID = "LOCUS-managed-performance-instrumentation-v2"
    shared_image = "locus-managed-performance-v2:local"
    staging = ROOT / STAGING_ROOT
    checkpoint_path = staging / "checkpoint.json"
    observations: list[dict[str, object]] = []
    prior_by_slot: dict[str, dict[str, object]] = {}
    completed: set[str] = set()
    interrupted: set[str] = set()
    shared_environment = _environment(
        "locus-perf-affordable-build", DEFAULT_MANAGER_PORT
    )
    shared_environment["LOCUS_INTEGRATED_IMAGE"] = shared_image
    try:
        run(
            [
                require("docker"),
                "build",
                "--file",
                str(ROOT / "deploy" / "Dockerfile"),
                "--tag",
                shared_image,
                str(ROOT),
            ],
            env=shared_environment,
        )
        shared_image_id = _image_id(shared_environment)
        resume_bindings = {
            "source_commit": provenance["source_commit"],
            "source_tree_sha256": provenance["source_tree_sha256"],
            "methodology_sha256": digest(methodology_contract()),
            "image_id": shared_image_id,
            "host_tier": provenance["host_tier"],
            "pseudonymous_host_id": provenance["pseudonymous_host_id"],
        }
        if retain and checkpoint_path.exists():
            checkpoint = json.loads(checkpoint_path.read_bytes())
            if (
                not isinstance(checkpoint, dict)
                or checkpoint.get("bindings") != resume_bindings
            ):
                raise RuntimeError(
                    "affordable checkpoint does not match the clean source/host/image"
                )
            completed = set(cast(list[str], checkpoint["completed_arm_blocks"]))
            observations = _affordable_staged_observations(staging)
            prior_by_slot = {
                cast(str, cast(dict[str, object], item["slot"])["slot_id"]): item
                for item in observations
            }
            active = checkpoint.get("active_arm_block")
            if isinstance(active, str):
                interrupted.add(active)
                active_arm, encoded_block = active.split(":b", 1)
                active_block = int(encoded_block)
                for active_attempt in range(1, 4):
                    orphan = _performance_project_name(
                        active_arm, active_block, active_attempt
                    )
                    orphan_environment = _environment(orphan, DEFAULT_MANAGER_PORT)
                    orphan_environment["LOCUS_INTEGRATED_IMAGE"] = shared_image
                    _cleanup_smoke_project(
                        orphan, orphan_environment, remove_image=False
                    )
        elif retain:
            staging.mkdir(parents=True, exist_ok=False)
            _affordable_checkpoint_write(
                checkpoint_path,
                checkpoint_profile(resume_bindings, [], None),
            )

        for block in range(1, 4):
            for arm_id, arm in ARMS.items():
                block_id = f"{arm_id}:b{block:02d}"
                if block_id in completed:
                    continue
                arm_slots = list(ordered_arm_block_slots(arm_id, block))
                if retain:
                    _affordable_checkpoint_write(
                        checkpoint_path,
                        checkpoint_profile(
                            resume_bindings, sorted(completed), block_id
                        ),
                    )
                for attempt in range(1, 4):
                    project = _performance_project_name(arm_id, block, attempt)
                    environment = _environment(project, DEFAULT_MANAGER_PORT)
                    environment["LOCUS_INTEGRATED_IMAGE"] = shared_image
                    environment["LOCUS_INTEGRATED_IMAGE_ID"] = shared_image_id
                    environment["LOCUS_PERFORMANCE_FIXTURE_ID"] = (
                        f"{arm['topology_id']}:block-{block:02d}"
                    )
                    runtime: _PerformanceRuntime | None = None
                    project_observations: list[dict[str, object]] = []
                    operation_error: BaseException | None = None
                    try:
                        status = _start_project(
                            project=project,
                            manager_port=DEFAULT_MANAGER_PORT,
                            environment=environment,
                            build_image=False,
                        )
                        base = _performance_base_bindings(
                            project=project,
                            environment=environment,
                            status=status,
                            provenance=provenance,
                        )
                        runtime = _PerformanceRuntime(
                            project=project,
                            manager_port=DEFAULT_MANAGER_PORT,
                            manager_csrf=_manager_session(DEFAULT_MANAGER_PORT),
                            environment=environment,
                            base_bindings=base,
                            host_id=cast(str, provenance["pseudonymous_host_id"]),
                        )
                        if block_id in interrupted:
                            interruption_records = _performance_invalid_block(
                                runtime=runtime,
                                slots=arm_slots,
                                prior_by_slot=prior_by_slot,
                                invalid_category="host-interruption",
                            )
                            for item in interruption_records:
                                slot_id = cast(
                                    str,
                                    cast(dict[str, object], item["slot"])["slot_id"],
                                )
                                prior_by_slot[slot_id] = item
                            observations.extend(interruption_records)
                            interrupted.remove(block_id)
                        project_observations.append(
                            _performance_warmup(runtime, arm_slots[0])
                        )
                        for slot in arm_slots[1:]:
                            project_observations.append(
                                _performance_measure_arm_slot(runtime, slot)
                            )
                    except BaseException as error:
                        operation_error = error
                    if runtime is not None:
                        try:
                            _performance_output_scan(runtime)
                        except BaseException as error:
                            operation_error = error
                    try:
                        _cleanup_smoke_project(project, environment, remove_image=False)
                    except BaseException as error:
                        if operation_error is None:
                            operation_error = error
                        else:
                            operation_error.add_note(
                                f"affordable cleanup also failed: {type(error).__name__}"
                            )
                    if operation_error is not None:
                        if (
                            runtime is None
                            or "output scan" in str(operation_error)
                            or "cleanup" in str(operation_error)
                        ):
                            raise operation_error
                        invalid = _performance_invalid_block(
                            runtime=runtime,
                            slots=arm_slots,
                            prior_by_slot=prior_by_slot,
                        )
                        for item in invalid:
                            slot_id = cast(
                                str, cast(dict[str, object], item["slot"])["slot_id"]
                            )
                            prior_by_slot[slot_id] = item
                        observations.extend(invalid)
                        if attempt == 3:
                            raise RuntimeError(
                                "affordable arm/block exhausted bounded retries"
                            ) from operation_error
                        continue
                    block_records: list[dict[str, object]] = []
                    for item in project_observations:
                        slot_id = cast(
                            str, cast(dict[str, object], item["slot"])["slot_id"]
                        )
                        chained = _performance_chain_observation(
                            item, prior_by_slot.get(slot_id)
                        )
                        prior_by_slot[slot_id] = chained
                        observations.append(chained)
                        block_records.append(chained)
                    if retain:
                        block_attempts = [
                            item
                            for item in observations
                            if cast(dict[str, object], item["slot"])["arm_id"] == arm_id
                            and cast(dict[str, object], item["slot"])["block"] == block
                        ]
                        for item in block_attempts:
                            slot = cast(dict[str, object], item["slot"])
                            path = (
                                staging
                                / "raw"
                                / cast(str, slot["slot_id"]).replace(":", "/")
                                / f"attempt-{cast(int, item['attempt_index']):02d}.json"
                            )
                            if not path.exists():
                                exclusive_write(path, item)
                        completed.add(block_id)
                        _affordable_checkpoint_write(
                            checkpoint_path,
                            checkpoint_profile(
                                resume_bindings, sorted(completed), None
                            ),
                        )
                    print(
                        json.dumps(
                            {
                                "arm": arm_id,
                                "block": block,
                                "slots": len(block_records),
                                "status": "passed",
                            },
                            sort_keys=True,
                        ),
                        flush=True,
                    )
                    break
        process_observations(observations)
        return observations
    finally:
        run_capture(
            [require("docker"), "image", "rm", shared_image],
            env=shared_environment,
            check=False,
        )
        _PERFORMANCE_INSTRUMENTATION_ID = "LOCUS-managed-performance-instrumentation-v1"
        _PERFORMANCE_EVIDENCE_ACTIVE = False


def _performance_command_result(
    *,
    summary: dict[str, object],
    comparison: dict[str, object],
    raw_record_count: int,
) -> dict[str, object]:
    return {
        "comparison_sha256": hashlib.sha256(
            json.dumps(comparison, sort_keys=True, separators=(",", ":")).encode()
            + b"\n"
        ).hexdigest(),
        "infrastructure_invalid_count": summary["infrastructure_invalid_count"],
        "measured_slot_count": summary["measured_slot_count"],
        "raw_attempt_count": summary["raw_attempt_count"],
        "raw_record_count": raw_record_count,
        "retained": False,
        "scheduled_slot_count": summary["scheduled_slot_count"],
        "status": "passed",
    }


def integrated_performance_evidence(*, retain: bool) -> None:
    """Execute the affordable D030 P9.3 profile and optionally seal its corpus."""

    from locus.affordable_performance_evidence import (
        RETAINED_ROOT,
        STAGING_ROOT,
        build_comparison,
        build_corpus_manifest,
        exclusive_write,
        process_observations,
        validate_staged_corpus,
    )

    provenance = _tracked_source_provenance(require_clean=retain)
    target = ROOT / RETAINED_ROOT
    staging = ROOT / STAGING_ROOT
    if retain and target.exists():
        raise RuntimeError("managed-performance-v2 retained target already exists")
    observations = _collect_affordable_performance_observations(
        provenance=provenance, retain=retain
    )
    summary = process_observations(observations)
    comparison = build_comparison(summary)
    result = _performance_command_result(
        summary=summary,
        comparison=comparison,
        raw_record_count=len(observations),
    )
    if retain:
        manifest = build_corpus_manifest(observations, summary, comparison)
        exclusive_write(staging / "processed" / "summary.json", summary)
        exclusive_write(staging / "derived" / "comparison.json", comparison)
        exclusive_write(staging / "corpus-manifest.json", manifest)
        validate_staged_corpus(staging)
        checkpoint = staging / "checkpoint.json"
        if not checkpoint.is_file():
            raise RuntimeError("affordable staging checkpoint disappeared")
        checkpoint.unlink()
        os.rename(staging, target)
        result.update(
            {
                "comparison_sha256": manifest["comparison_sha256"],
                "raw_records_sha256": manifest["raw_records_sha256"],
                "retained": True,
                "summary_sha256": manifest["summary_sha256"],
            }
        )
    print(json.dumps(result, sort_keys=True))


def integrated_state_evidence(*, retain: bool) -> None:
    """Run D026's fixed aggregate-only state scenario corpus."""

    from locus.managed_state_evidence import build_reports, publish_corpus

    provenance = _tracked_source_provenance(require_clean=retain)
    summary = integrated_smoke(state_evidence=True)
    for field in ("image_id", "live_graph_sha256", "resolved_graph_sha256"):
        value = summary.get(field)
        if not isinstance(value, str):
            raise RuntimeError(f"state evidence omitted provenance: {field}")
        provenance[field] = value
    reports = build_reports(provenance=provenance, summary=summary)
    result: dict[str, object] = {
        "record_count": len(reports),
        "retained": False,
        "status": "passed",
    }
    if retain:
        manifest = publish_corpus(root=ROOT, reports=reports)
        result.update(
            {
                "records_sha256": manifest["records_sha256"],
                "retained": True,
            }
        )
    print(json.dumps(result, sort_keys=True))


def integrated_flow_evidence(*, retain: bool) -> None:
    """Run D027's fixed aggregate-only managed flow scenario corpus."""

    from locus.managed_flow_evidence import build_reports, publish_corpus

    provenance = _tracked_source_provenance(require_clean=retain)
    summary = integrated_smoke(flow_evidence=True)
    for field in (
        "image_id",
        "live_graph_sha256",
        "pseudonymous_client_set_id",
        "pseudonymous_package_set_id",
        "pseudonymous_project_id",
        "resolved_graph_sha256",
    ):
        value = summary.get(field)
        if not isinstance(value, str):
            raise RuntimeError(f"flow evidence omitted provenance: {field}")
        provenance[field] = value
    try:
        reports = build_reports(provenance=provenance, summary=summary)
        result: dict[str, object] = {
            "record_count": len(reports),
            "retained": False,
            "status": "passed",
        }
        if retain:
            manifest = publish_corpus(root=ROOT, reports=reports)
            result.update(
                {"corpus_sha256": manifest["corpus_sha256"], "retained": True}
            )
        print(json.dumps(result, sort_keys=True))
    except BaseException as error:
        print(
            json.dumps(
                {
                    "category": "managed_flow_evidence_failed",
                    "error": type(error).__name__,
                    "message": str(error),
                },
                sort_keys=True,
            ),
            file=sys.stderr,
            flush=True,
        )
        raise


def integrated_attempt_boundary() -> None:
    """Run P8.4's frozen rollback counterexample under the D025 binding."""

    from locus.attempt_boundary import build_integrated_attempt_boundary_report

    print(
        json.dumps(
            build_integrated_attempt_boundary_report(ROOT),
            separators=(",", ":"),
            sort_keys=True,
        )
    )


def build_integrated_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Operate the managed integrated LOCUS reference prototype."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser(
        "integrated-check", help="run focused Python and native quality checks"
    )
    subparsers.add_parser(
        "integrated-config", help="validate the managed manifest and graph"
    )
    start = subparsers.add_parser(
        "integrated-start", help="start the service plane and Manager UI"
    )
    start.add_argument("--project", type=_project, default=DEFAULT_PROJECT)
    start.add_argument("--port", type=_port, default=DEFAULT_MANAGER_PORT)
    stop = subparsers.add_parser(
        "integrated-stop", help="emergency cleanup of one exact project"
    )
    stop.add_argument("--project", type=_project, default=DEFAULT_PROJECT)
    stop.add_argument(
        "--reset-state",
        action="store_true",
        help="also remove exact-project role volumes (irreversible local reset)",
    )
    subparsers.add_parser(
        "integrated-smoke", help="run the disposable Manager-to-Client gate"
    )
    subparsers.add_parser(
        "integrated-attempt-boundary",
        help="reproduce the frozen local-audit rollback boundary",
    )
    state = subparsers.add_parser(
        "integrated-state-evidence",
        help="run the fixed aggregate-only P8.2 state boundary corpus",
    )
    state.add_argument(
        "--retain",
        action="store_true",
        help="publish the complete corpus exclusively from a clean commit",
    )
    flow = subparsers.add_parser(
        "integrated-flow-evidence",
        help="run the fixed aggregate-only P8.3 managed flow corpus",
    )
    flow.add_argument(
        "--retain",
        action="store_true",
        help="publish the complete corpus exclusively from a clean commit",
    )
    performance = subparsers.add_parser(
        "integrated-performance-evidence",
        help="run D030's affordable P9.3 schedule (execution separately gated)",
    )
    performance.add_argument(
        "--retain",
        action="store_true",
        help="resume/stage and atomically publish v2 from a clean commit",
    )
    return parser


def main() -> int:
    parser = build_integrated_parser()
    args = parser.parse_args()
    try:
        if args.command == "integrated-check":
            integrated_check()
        elif args.command == "integrated-config":
            integrated_config()
        elif args.command == "integrated-start":
            integrated_start(args)
        elif args.command == "integrated-stop":
            integrated_stop(args)
        elif args.command == "integrated-smoke":
            integrated_smoke()
        elif args.command == "integrated-attempt-boundary":
            integrated_attempt_boundary()
        elif args.command == "integrated-state-evidence":
            integrated_state_evidence(retain=args.retain)
        elif args.command == "integrated-flow-evidence":
            integrated_flow_evidence(retain=args.retain)
        elif args.command == "integrated-performance-evidence":
            integrated_performance_evidence(retain=args.retain)
        else:  # pragma: no cover
            raise AssertionError(f"Unhandled command: {args.command}")
    except subprocess.CalledProcessError as error:
        return error.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
