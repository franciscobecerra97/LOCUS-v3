"""P7 local no-persistence web UI over the frozen research-client API."""

from __future__ import annotations

import argparse
import ipaddress
import json
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from .client_api import LocalResearchClientApi, public_failure
from .redaction import validate_public_output

LOCAL_RESEARCH_UI_PROFILE = "LOCUS-local-research-ui-v1"
MAX_UI_REQUEST_BYTES = 128 * 1024
MAX_ASSET_BYTES = 512 * 1024
ASSET_ROOT = Path(__file__).resolve().parent / "ui_assets"


class ResearchUiError(ValueError):
    """The local UI transport or asset boundary failed closed."""


@dataclass(frozen=True)
class UiResponse:
    status: int
    content_type: str
    body: bytes
    transient_secret_path: bool = False


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ResearchUiError("duplicate JSON field")
        result[key] = value
    return result


def _decode_request(body: bytes) -> object:
    if not body or len(body) > MAX_UI_REQUEST_BYTES:
        raise ResearchUiError("invalid UI request size")
    try:
        return json.loads(
            body.decode("utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=lambda _value: (_ for _ in ()).throw(
                ResearchUiError("non-finite JSON number")
            ),
        )
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ResearchUiError("invalid UI request") from exc


def _json_response(
    value: object, *, status: int = HTTPStatus.OK, transient: bool = False
) -> UiResponse:
    if not transient:
        validate_public_output(value)
    return UiResponse(
        status=int(status),
        content_type="application/json; charset=utf-8",
        body=json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8"),
        transient_secret_path=transient,
    )


def _asset(name: str, content_type: str) -> UiResponse:
    path = ASSET_ROOT / name
    try:
        if path.is_symlink() or not path.is_file():
            raise ResearchUiError("UI asset is unavailable")
        body = path.read_bytes()
    except OSError as exc:
        raise ResearchUiError("UI asset is unavailable") from exc
    if not body or len(body) > MAX_ASSET_BYTES:
        raise ResearchUiError("UI asset size is invalid")
    return UiResponse(status=HTTPStatus.OK, content_type=content_type, body=body)


class ResearchUiApplication:
    """Strict route adapter; request bodies and exception text are never logged."""

    def __init__(self, client: LocalResearchClientApi | None = None) -> None:
        self.client = LocalResearchClientApi() if client is None else client

    def dispatch(
        self,
        method: str,
        target: str,
        body: bytes = b"",
        *,
        content_type: str | None = None,
    ) -> UiResponse:
        parsed_target = urlsplit(target)
        if parsed_target.query or parsed_target.fragment:
            return _json_response(
                {"category": "route_rejected", "status": "rejected"},
                status=HTTPStatus.NOT_FOUND,
            )
        path = parsed_target.path
        try:
            if method == "GET" and path == "/":
                return _asset("index.html", "text/html; charset=utf-8")
            if method == "GET" and path == "/assets/styles.css":
                return _asset("styles.css", "text/css; charset=utf-8")
            if method == "GET" and path == "/assets/app.js":
                return _asset("app.js", "text/javascript; charset=utf-8")
            if method == "GET" and path == "/api/v1/catalog":
                return _json_response(self.client.catalog())
            if method != "POST" or not path.startswith("/api/v1/"):
                return _json_response(
                    {"category": "route_rejected", "status": "rejected"},
                    status=HTTPStatus.NOT_FOUND,
                )
            if content_type != "application/json":
                raise ResearchUiError("unsupported content type")
            request = _decode_request(body)
            if path == "/api/v1/preview-policy":
                return _json_response(
                    self.client.preview_policy(request), transient=True
                )
            if path == "/api/v1/enroll":
                return _json_response(self.client.enroll(request).public_value())
            if path == "/api/v1/bootstrap":
                parsed = (
                    request
                    if isinstance(request, dict) and set(request) == {"receipt"}
                    else None
                )
                if parsed is None:
                    raise ResearchUiError("invalid bootstrap request")
                return _json_response(
                    self.client.bootstrap(parsed["receipt"]).public_value()
                )
            if path == "/api/v1/recover":
                return _json_response(self.client.recover(request).public_value())
            if path == "/api/v1/successor":
                return _json_response(
                    self.client.create_successor(request).public_value()
                )
            if path == "/api/v1/inspect":
                parsed = (
                    request
                    if isinstance(request, dict) and set(request) == {"receipt"}
                    else None
                )
                if parsed is None:
                    raise ResearchUiError("invalid inspection request")
                return _json_response(self.client.inspect(parsed["receipt"]))
            return _json_response(
                {"category": "route_rejected", "status": "rejected"},
                status=HTTPStatus.NOT_FOUND,
            )
        except Exception as exc:
            failure = public_failure(exc)
            status = (
                HTTPStatus.CONFLICT
                if failure["category"] == "operation_conflict"
                else HTTPStatus.BAD_REQUEST
            )
            return _json_response(failure, status=status)


SECURITY_HEADERS = {
    "Cache-Control": "no-store, max-age=0",
    "Content-Security-Policy": (
        "default-src 'none'; base-uri 'none'; connect-src 'self'; "
        "form-action 'self'; frame-ancestors 'none'; img-src 'self' data:; "
        "object-src 'none'; script-src 'self'; style-src 'self'"
    ),
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
    "Permissions-Policy": (
        "camera=(), clipboard-read=(), clipboard-write=(), geolocation=(), "
        "microphone=(), payment=(), usb=()"
    ),
    "Pragma": "no-cache",
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
}


class ResearchUiRequestHandler(BaseHTTPRequestHandler):
    server_version = "LOCUSResearchUI/1"
    sys_version = ""

    @property
    def application(self) -> ResearchUiApplication:
        application = getattr(self.server, "application", None)
        if not isinstance(application, ResearchUiApplication):
            raise ResearchUiError("UI application is unavailable")
        return application

    def do_GET(self) -> None:  # noqa: N802
        self._dispatch("GET")

    def do_POST(self) -> None:  # noqa: N802
        self._dispatch("POST")

    def _dispatch(self, method: str) -> None:
        body = b""
        content_type = None
        if method == "POST":
            raw_length = self.headers.get("Content-Length")
            try:
                length = int(raw_length or "")
            except ValueError:
                length = -1
            if length < 1 or length > MAX_UI_REQUEST_BYTES:
                response = _json_response(
                    {"category": "input_rejected", "status": "rejected"},
                    status=HTTPStatus.BAD_REQUEST,
                )
                self._send(response)
                return
            body = self.rfile.read(length)
            content_type = self.headers.get("Content-Type")
        response = self.application.dispatch(
            method, self.path, body, content_type=content_type
        )
        self._send(response)

    def _send(self, response: UiResponse) -> None:
        self.send_response(response.status)
        self.send_header("Content-Type", response.content_type)
        self.send_header("Content-Length", str(len(response.body)))
        for name, value in SECURITY_HEADERS.items():
            self.send_header(name, value)
        if response.content_type.startswith("text/html"):
            self.send_header("Clear-Site-Data", '"cache", "cookies", "storage"')
        if response.transient_secret_path:
            self.send_header("X-LOCUS-Transient", "active-client-only")
        self.end_headers()
        self.wfile.write(response.body)

    def log_message(self, _format: str, *args: object) -> None:
        # Request targets, bodies, exception text, and client addresses are
        # deliberately absent from the normal UI output path.
        del args


class ResearchUiServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(
        self,
        server_address: tuple[str, int],
        application: ResearchUiApplication,
    ) -> None:
        self.application = application
        super().__init__(server_address, ResearchUiRequestHandler)

    def handle_error(self, request: object, client_address: object) -> None:
        # The standard library's default prints a traceback. Suppress it so a
        # disconnected browser cannot move exception context into stderr.
        del request, client_address


def _loopback_host(value: str) -> str:
    if value == "localhost":
        return value
    try:
        address = ipaddress.ip_address(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("UI host must be loopback") from exc
    if not address.is_loopback:
        raise argparse.ArgumentTypeError("UI host must be loopback")
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the local LOCUS research UI")
    parser.add_argument("--host", type=_loopback_host, default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if not 1 <= args.port <= 65535:
        raise SystemExit("invalid UI port")
    application = ResearchUiApplication()
    with ResearchUiServer((args.host, args.port), application) as server:
        result: dict[str, object] = {
            "status": "ready",
            "ui_profile": LOCAL_RESEARCH_UI_PROFILE,
            "url": f"http://{args.host}:{server.server_port}/",
        }
        validate_public_output(result)
        print(json.dumps(result, sort_keys=True, separators=(",", ":")), flush=True)
        try:
            server.serve_forever(poll_interval=0.2)
        except KeyboardInterrupt:
            return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "LOCAL_RESEARCH_UI_PROFILE",
    "SECURITY_HEADERS",
    "ResearchUiApplication",
    "ResearchUiError",
    "ResearchUiServer",
    "UiResponse",
]
