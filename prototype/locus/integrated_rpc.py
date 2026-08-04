"""Bounded canonical JSON over mutually authenticated TLS for P7.5 roles."""

from __future__ import annotations

import http.client
import json
import ssl
import threading
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, cast
from urllib.parse import urlsplit

from .codec import encode

MAX_RPC_BYTES = 2 * 1024 * 1024
RpcHandler = Callable[[str, dict[str, Any], str], tuple[int, dict[str, Any]]]


class IntegratedRpcError(ValueError):
    """An authenticated internal RPC failed closed."""


def decode_rpc(encoded: bytes) -> dict[str, Any]:
    if not encoded or len(encoded) > MAX_RPC_BYTES:
        raise IntegratedRpcError("invalid RPC body")
    try:
        value = json.loads(
            encoded.decode("utf-8"),
            object_pairs_hook=lambda pairs: _unique(pairs),
            parse_constant=lambda _item: (_ for _ in ()).throw(ValueError()),
        )
        if not isinstance(value, dict) or encode(value) != encoded:
            raise ValueError("noncanonical JSON")
        return cast(dict[str, Any], value)
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        raise IntegratedRpcError("invalid RPC body") from exc


def _unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON member")
        result[key] = value
    return result


def _peer_role(handler: BaseHTTPRequestHandler) -> str:
    certificate = handler.connection.getpeercert()
    subject = certificate.get("subject", ())
    for group in subject:
        for key, value in group:
            if key == "commonName" and isinstance(value, str):
                return value
    raise IntegratedRpcError("client identity unavailable")


class _Server(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address: tuple[str, int], rpc_handler: RpcHandler) -> None:
        self.rpc_handler = rpc_handler
        super().__init__(address, _RequestHandler)


class _RequestHandler(BaseHTTPRequestHandler):
    server: _Server

    def log_message(self, _format: str, *_args: object) -> None:
        return

    def _reply(self, status: int, value: dict[str, Any]) -> None:
        body = encode(value)
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path != "/health":
            self._reply(404, {"category": "not_found", "status": "error"})
            return
        try:
            peer = _peer_role(self)
            status, value = self.server.rpc_handler(self.path, {}, peer)
            self._reply(status, value)
        except Exception:
            self._reply(503, {"category": "unavailable", "status": "error"})

    def do_POST(self) -> None:  # noqa: N802
        try:
            length = int(self.headers.get("Content-Length", "-1"))
            if length < 1 or length > MAX_RPC_BYTES:
                raise IntegratedRpcError("invalid RPC length")
            request = decode_rpc(self.rfile.read(length))
            peer = _peer_role(self)
            status, value = self.server.rpc_handler(self.path, request, peer)
            self._reply(status, value)
        except IntegratedRpcError:
            self._reply(400, {"category": "input_rejected", "status": "error"})
        except Exception:
            self._reply(503, {"category": "unavailable", "status": "error"})


def serve_rpc(
    *, host: str, port: int, role_root: str | Path, handler: RpcHandler
) -> None:
    root = Path(role_root)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_3
    context.maximum_version = ssl.TLSVersion.TLSv1_3
    context.load_cert_chain(root / "tls-cert.pem", root / "tls-key.pem")
    context.load_verify_locations(root / "ca.pem")
    context.verify_mode = ssl.CERT_REQUIRED
    server = _Server((host, port), handler)
    server.socket = context.wrap_socket(server.socket, server_side=True)
    server.serve_forever()


def rpc_request(
    *,
    endpoint: str,
    path: str,
    role_root: str | Path,
    value: dict[str, Any],
    timeout: float = 5.0,
) -> dict[str, Any]:
    parsed = urlsplit(endpoint)
    if parsed.scheme != "https" or not parsed.hostname or parsed.port != 8443:
        raise IntegratedRpcError("invalid RPC endpoint")
    root = Path(role_root)
    context = ssl.create_default_context(cafile=str(root / "ca.pem"))
    context.minimum_version = ssl.TLSVersion.TLSv1_3
    context.maximum_version = ssl.TLSVersion.TLSv1_3
    context.load_cert_chain(root / "tls-cert.pem", root / "tls-key.pem")
    connection = http.client.HTTPSConnection(
        parsed.hostname, parsed.port, context=context, timeout=timeout
    )
    body = encode(value)
    try:
        connection.request(
            "POST", path, body=body, headers={"Content-Type": "application/json"}
        )
        response = connection.getresponse()
        encoded = response.read(MAX_RPC_BYTES + 1)
        decoded = decode_rpc(encoded)
        if response.status != 200:
            raise IntegratedRpcError(str(decoded.get("category", "request_rejected")))
        return decoded
    except (OSError, ssl.SSLError, http.client.HTTPException) as exc:
        raise IntegratedRpcError("service unavailable") from exc
    finally:
        connection.close()


class RpcServerThread:
    """Loopback test helper; production containers call :func:`serve_rpc`."""

    def __init__(self, *, role_root: Path, handler: RpcHandler) -> None:
        self.role_root = role_root
        self.handler = handler
        self.server = _Server(("127.0.0.1", 0), handler)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.minimum_version = ssl.TLSVersion.TLSv1_3
        context.maximum_version = ssl.TLSVersion.TLSv1_3
        context.load_cert_chain(role_root / "tls-cert.pem", role_root / "tls-key.pem")
        context.load_verify_locations(role_root / "ca.pem")
        context.verify_mode = ssl.CERT_REQUIRED
        self.server.socket = context.wrap_socket(self.server.socket, server_side=True)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    @property
    def port(self) -> int:
        return int(self.server.server_address[1])

    def __enter__(self) -> RpcServerThread:
        self.thread.start()
        return self

    def __exit__(self, *_args: object) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)


__all__ = [
    "IntegratedRpcError",
    "RpcServerThread",
    "decode_rpc",
    "rpc_request",
    "serve_rpc",
]
