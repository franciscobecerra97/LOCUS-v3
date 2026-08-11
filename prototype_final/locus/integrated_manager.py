"""Loopback Manager UI over the narrow internal lifecycle controller."""

from __future__ import annotations

import argparse
import ipaddress
import json
import re
import secrets
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from .integrated_rpc import rpc_request

MANAGER_UI_PROFILE = "LOCUS-local-manager-ui-v1"
MANAGER_API_VERSION = "LOCUS-manager-api-v1"
MAX_MANAGER_REQUEST_BYTES = 32 * 1024
ASSET_ROOT = Path(__file__).resolve().parent / "manager_assets"
_OPERATION_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z")


class ManagerUiError(ValueError):
    """A Manager request failed its local control-plane boundary."""


@dataclass(frozen=True)
class ManagerResponse:
    status: int
    content_type: str
    body: bytes


def _unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ManagerUiError("duplicate JSON member")
        result[key] = value
    return result


def _json(value: object, *, status: int = 200) -> ManagerResponse:
    return ManagerResponse(
        status,
        "application/json; charset=utf-8",
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode(),
    )


def _asset(name: str, content_type: str) -> ManagerResponse:
    path = ASSET_ROOT / name
    if path.is_symlink() or not path.is_file():
        raise ManagerUiError("Manager asset unavailable")
    body = path.read_bytes()
    if not body or len(body) > 512 * 1024:
        raise ManagerUiError("invalid Manager asset")
    return ManagerResponse(200, content_type, body)


def _operation_id(value: object) -> str:
    if not isinstance(value, str) or _OPERATION_ID.fullmatch(value) is None:
        raise ManagerUiError("invalid Manager operation identifier")
    return value


class ManagerApplication:
    def __init__(self, *, role_root: Path) -> None:
        self.root = role_root
        self.csrf_token = secrets.token_urlsafe(32)

    def _controller(self, path: str, value: dict[str, Any]) -> dict[str, Any]:
        return rpc_request(
            endpoint="https://manager-controller:8443",
            path=path,
            role_root=self.root,
            value=value,
            timeout=80 if path == "/v1/client/create" else 10,
        )

    def dispatch(
        self,
        method: str,
        target: str,
        body: bytes,
        *,
        content_type: str | None,
        csrf_token: str | None,
        origin: str | None,
        expected_origin: str,
    ) -> ManagerResponse:
        parsed = urlsplit(target)
        if parsed.query or parsed.fragment:
            return _json(
                {"category": "route_rejected", "status": "rejected"}, status=404
            )
        path = parsed.path
        if method == "GET":
            if path == "/":
                return _asset("index.html", "text/html; charset=utf-8")
            if path == "/assets/manager.css":
                return _asset("manager.css", "text/css; charset=utf-8")
            if path == "/assets/manager.js":
                return _asset("manager.js", "text/javascript; charset=utf-8")
            if path == "/api/manager/v1/session":
                return _json(
                    {
                        "api_version": MANAGER_API_VERSION,
                        "csrf_token": self.csrf_token,
                        "status": "ready",
                        "ui_profile": MANAGER_UI_PROFILE,
                    }
                )
            if path == "/api/manager/v1/status":
                return _json(self._controller("/v1/status", {}))
            return _json(
                {"category": "route_rejected", "status": "rejected"}, status=404
            )
        if (
            method != "POST"
            or content_type != "application/json"
            or origin != expected_origin
            or not isinstance(csrf_token, str)
            or not secrets.compare_digest(csrf_token, self.csrf_token)
        ):
            raise ManagerUiError("manager request authentication failed")
        try:
            request = json.loads(
                body.decode("utf-8"),
                object_pairs_hook=_unique,
                parse_constant=lambda _item: (_ for _ in ()).throw(ValueError()),
            )
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            raise ManagerUiError("invalid Manager request") from exc
        if not isinstance(request, dict):
            raise ManagerUiError("invalid Manager request")
        if path == "/api/manager/v1/clients":
            if set(request) != {"operation_id"}:
                raise ManagerUiError("invalid client creation")
            _operation_id(request["operation_id"])
            return _json(self._controller("/v1/client/create", request), status=201)
        if path == "/api/manager/v1/container-action":
            if set(request) != {"action", "container_id", "operation_id"}:
                raise ManagerUiError("invalid container action")
            _operation_id(request["operation_id"])
            return _json(self._controller("/v1/container/action", request))
        if path == "/api/manager/v1/client-destroy":
            if set(request) != {"container_id", "operation_id"}:
                raise ManagerUiError("invalid client destruction")
            _operation_id(request["operation_id"])
            return _json(self._controller("/v1/client/destroy", request))
        if path == "/api/manager/v1/system-stop":
            if set(request) != {"operation_id"}:
                raise ManagerUiError("invalid system stop")
            _operation_id(request["operation_id"])
            return _json(self._controller("/v1/system/stop", request), status=202)
        return _json({"category": "route_rejected", "status": "rejected"}, status=404)


def _loopback_origin(host_header: str) -> str:
    """Return the one local origin represented by a safe Host header."""

    try:
        parsed = urlsplit(f"http://{host_header}")
        if (
            parsed.scheme != "http"
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path
            or parsed.query
            or parsed.fragment
            or parsed.hostname is None
        ):
            raise ValueError
        if (
            parsed.hostname != "localhost"
            and not ipaddress.ip_address(parsed.hostname).is_loopback
        ):
            raise ValueError
        if parsed.port is None:
            raise ValueError
    except ValueError as exc:
        raise ManagerUiError("invalid Manager host") from exc
    return f"http://{host_header}"


SECURITY_HEADERS = {
    "Cache-Control": "no-store, max-age=0",
    "Content-Security-Policy": (
        "default-src 'none'; base-uri 'none'; connect-src 'self'; "
        "form-action 'self'; frame-ancestors 'none'; img-src 'self' data:; "
        "object-src 'none'; script-src 'self'; style-src 'self'"
    ),
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
    "Permissions-Policy": "camera=(), geolocation=(), microphone=(), payment=(), usb=()",
    "Pragma": "no-cache",
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
}


class _ManagerServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(
        self, address: tuple[str, int], application: ManagerApplication
    ) -> None:
        self.application = application
        super().__init__(address, _ManagerHandler)

    def handle_error(self, request: object, client_address: object) -> None:
        del request, client_address


class _ManagerHandler(BaseHTTPRequestHandler):
    server: _ManagerServer
    server_version = "LOCUSManagerUI/1"
    sys_version = ""

    def log_message(self, _format: str, *_args: object) -> None:
        return

    def do_GET(self) -> None:  # noqa: N802
        self._handle("GET")

    def do_POST(self) -> None:  # noqa: N802
        self._handle("POST")

    def _handle(self, method: str) -> None:
        body = b""
        content_type = None
        if method == "POST":
            try:
                length = int(self.headers.get("Content-Length", "-1"))
            except ValueError:
                length = -1
            if length < 2 or length > MAX_MANAGER_REQUEST_BYTES:
                self._send(
                    _json(
                        {"category": "input_rejected", "status": "rejected"}, status=400
                    )
                )
                return
            body = self.rfile.read(length)
            content_type = self.headers.get("Content-Type")
        try:
            expected_origin = _loopback_origin(self.headers.get("Host", ""))
            response = self.server.application.dispatch(
                method,
                self.path,
                body,
                content_type=content_type,
                csrf_token=self.headers.get("X-LOCUS-CSRF"),
                origin=self.headers.get("Origin"),
                expected_origin=expected_origin,
            )
        except Exception:
            response = _json(
                {"category": "operation_rejected", "status": "rejected"}, status=400
            )
        self._send(response)

    def _send(self, response: ManagerResponse) -> None:
        self.send_response(response.status)
        self.send_header("Content-Type", response.content_type)
        self.send_header("Content-Length", str(len(response.body)))
        for name, value in SECURITY_HEADERS.items():
            self.send_header(name, value)
        if response.content_type.startswith("text/html"):
            self.send_header("Clear-Site-Data", '"cache", "cookies", "storage"')
        self.end_headers()
        self.wfile.write(response.body)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    application = ManagerApplication(role_root=args.root)
    with _ManagerServer((args.host, args.port), application) as server:
        print(
            json.dumps(
                {"status": "ready", "ui_profile": MANAGER_UI_PROFILE},
                sort_keys=True,
                separators=(",", ":"),
            ),
            flush=True,
        )
        server.serve_forever(poll_interval=0.2)


if __name__ == "__main__":
    main()
