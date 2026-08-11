"""Small bounded Docker Engine client for the local managed deployment.

The module deliberately exposes only the operations required by the internal
container controller.  It is not a general Docker proxy.
"""

from __future__ import annotations

import http.client
import json
import re
import socket
from pathlib import Path
from typing import Any, cast
from urllib.parse import quote, urlencode

MAX_DOCKER_RESPONSE_BYTES = 4 * 1024 * 1024
MINIMUM_API_VERSION = (1, 41)
MAXIMUM_API_VERSION = (1, 47)


class DockerEngineError(RuntimeError):
    """The local Docker engine rejected a bounded lifecycle operation."""


class _UnixConnection(http.client.HTTPConnection):
    def __init__(self, socket_path: Path, *, timeout: float) -> None:
        super().__init__("localhost", timeout=timeout)
        self.socket_path = socket_path

    def connect(self) -> None:
        family = cast(int, getattr(socket, "AF_UNIX", -1))
        if family < 0:
            raise DockerEngineError("Unix sockets are unavailable")
        connection = socket.socket(family, socket.SOCK_STREAM)
        connection.settimeout(self.timeout)
        connection.connect(str(self.socket_path))
        self.sock = connection


class DockerEngine:
    """Minimal Docker Engine HTTP client over one local Unix socket."""

    def __init__(
        self, socket_path: str | Path = "/var/run/docker.sock", *, timeout: float = 10
    ) -> None:
        self.socket_path = Path(socket_path)
        self.timeout = timeout
        self._api_prefix: str | None = None

    def _negotiate(self) -> str:
        """Select a bounded Engine API version from the local daemon."""

        if self._api_prefix is not None:
            return self._api_prefix
        value = self._request_raw("GET", "/version", expected=frozenset({200}))
        if not isinstance(value, dict) or not isinstance(value.get("ApiVersion"), str):
            raise DockerEngineError("invalid Docker Engine version response")
        match = re.fullmatch(r"(\d+)\.(\d+)", value["ApiVersion"])
        if match is None:
            raise DockerEngineError("invalid Docker Engine API version")
        observed = (int(match.group(1)), int(match.group(2)))
        if observed < MINIMUM_API_VERSION:
            raise DockerEngineError("Docker Engine API is too old")
        selected = min(observed, MAXIMUM_API_VERSION)
        self._api_prefix = f"/v{selected[0]}.{selected[1]}"
        return self._api_prefix

    def _request_raw(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        expected: frozenset[int] = frozenset({200, 201, 204}),
    ) -> Any:
        if not path.startswith("/") or "\r" in path or "\n" in path:
            raise DockerEngineError("invalid Docker Engine path")
        body = None
        headers: dict[str, str] = {}
        if payload is not None:
            body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
            headers = {"Content-Type": "application/json"}
        connection = _UnixConnection(self.socket_path, timeout=self.timeout)
        try:
            connection.request(method, path, body=body, headers=headers)
            response = connection.getresponse()
            encoded = response.read(MAX_DOCKER_RESPONSE_BYTES + 1)
        except (OSError, http.client.HTTPException) as exc:
            raise DockerEngineError("Docker Engine is unavailable") from exc
        finally:
            connection.close()
        if len(encoded) > MAX_DOCKER_RESPONSE_BYTES:
            raise DockerEngineError("Docker Engine response is too large")
        if response.status not in expected:
            raise DockerEngineError(
                f"Docker Engine rejected operation ({response.status})"
            )
        if not encoded:
            return None
        try:
            return json.loads(encoded)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise DockerEngineError("invalid Docker Engine response") from exc

    def _request(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        expected: frozenset[int] = frozenset({200, 201, 204}),
    ) -> Any:
        if not path.startswith("/"):
            raise DockerEngineError("invalid Docker Engine path")
        return self._request_raw(
            method,
            f"{self._negotiate()}{path}",
            payload=payload,
            expected=expected,
        )

    @staticmethod
    def _filters(value: dict[str, list[str]]) -> str:
        return quote(json.dumps(value, sort_keys=True, separators=(",", ":")))

    def containers(self, *, labels: tuple[str, ...]) -> list[dict[str, Any]]:
        value = self._request(
            "GET",
            f"/containers/json?all=1&filters={self._filters({'label': list(labels)})}",
        )
        if not isinstance(value, list) or any(
            not isinstance(item, dict) for item in value
        ):
            raise DockerEngineError("invalid container inventory")
        return cast(list[dict[str, Any]], value)

    def inspect_container(self, container_id: str) -> dict[str, Any]:
        value = self._request("GET", f"/containers/{quote(container_id, safe='')}/json")
        if not isinstance(value, dict):
            raise DockerEngineError("invalid container inspection")
        return cast(dict[str, Any], value)

    def inspect_image(self, image: str) -> dict[str, Any]:
        value = self._request("GET", f"/images/{quote(image, safe='')}/json")
        if not isinstance(value, dict) or not isinstance(value.get("Id"), str):
            raise DockerEngineError("invalid image inspection")
        return cast(dict[str, Any], value)

    def create_container(self, *, name: str, specification: dict[str, Any]) -> str:
        value = self._request(
            "POST",
            f"/containers/create?{urlencode({'name': name})}",
            payload=specification,
        )
        if not isinstance(value, dict) or not isinstance(value.get("Id"), str):
            raise DockerEngineError("invalid container creation response")
        return str(value["Id"])

    def start_container(self, container_id: str) -> None:
        self._request(
            "POST",
            f"/containers/{quote(container_id, safe='')}/start",
            expected=frozenset({204, 304}),
        )

    def stop_container(self, container_id: str, *, timeout: int = 3) -> None:
        self._request(
            "POST",
            f"/containers/{quote(container_id, safe='')}/stop?t={timeout}",
            expected=frozenset({204, 304}),
        )

    def restart_container(self, container_id: str, *, timeout: int = 3) -> None:
        self._request(
            "POST",
            f"/containers/{quote(container_id, safe='')}/restart?t={timeout}",
            expected=frozenset({204}),
        )

    def kill_container(self, container_id: str) -> None:
        self._request(
            "POST",
            f"/containers/{quote(container_id, safe='')}/kill?signal=SIGKILL",
            expected=frozenset({204}),
        )

    def remove_container(self, container_id: str, *, force: bool = False) -> None:
        query = urlencode({"force": "1" if force else "0", "v": "1"})
        self._request(
            "DELETE",
            f"/containers/{quote(container_id, safe='')}?{query}",
            expected=frozenset({204, 404}),
        )

    def networks(self, *, labels: tuple[str, ...]) -> list[dict[str, Any]]:
        value = self._request(
            "GET", f"/networks?filters={self._filters({'label': list(labels)})}"
        )
        if not isinstance(value, list) or any(
            not isinstance(item, dict) for item in value
        ):
            raise DockerEngineError("invalid network inventory")
        return cast(list[dict[str, Any]], value)

    def connect_network(self, network_id: str, container_id: str) -> None:
        self._request(
            "POST",
            f"/networks/{quote(network_id, safe='')}/connect",
            payload={"Container": container_id},
            expected=frozenset({200}),
        )

    def remove_network(self, network_id: str) -> None:
        self._request(
            "DELETE",
            f"/networks/{quote(network_id, safe='')}",
            expected=frozenset({204, 404}),
        )


__all__ = ["DockerEngine", "DockerEngineError"]
