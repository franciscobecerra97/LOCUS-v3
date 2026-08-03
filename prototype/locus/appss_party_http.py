"""Pinned mutual-TLS transport for one durable aPPSS holder service."""

from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import ssl
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import cast

from .appss_formats import MAX_REQUEST_BYTES, MAX_RESPONSE_BYTES
from .appss_party import (
    AppssPartyBinding,
    AppssPartyError,
    AppssPartyService,
    AppssPartyStore,
)

EVALUATE_ROUTE = "/v1/recovery-suites/appss/evaluations"
MAX_ERROR_BYTES = 256


class AppssPartyTransportError(AppssPartyError):
    """An authenticated party was unavailable or returned invalid bytes."""


@dataclass(frozen=True)
class AppssRemoteParty:
    holder_id: int
    host: str
    port: int
    server_ca: str
    client_certificate: str
    client_private_key: str
    server_certificate_sha256: str
    timeout_seconds: float = 1.0

    def __post_init__(self) -> None:
        if (
            not 1 <= self.holder_id <= 255
            or not self.host
            or not 1 <= self.port <= 65535
            or not 0 < self.timeout_seconds <= 30
        ):
            raise AppssPartyTransportError("invalid aPPSS endpoint")
        _lower_hex(self.server_certificate_sha256, "server certificate fingerprint")

    def evaluate(self, request_bytes: bytes, *, idempotency_key: str) -> bytes:
        if not isinstance(request_bytes, bytes) or not (
            0 < len(request_bytes) <= MAX_REQUEST_BYTES
        ):
            raise AppssPartyTransportError("invalid aPPSS request body")
        _lower_hex(idempotency_key, "idempotency key")
        tls = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=self.server_ca)
        tls.minimum_version = ssl.TLSVersion.TLSv1_3
        tls.check_hostname = False
        tls.load_cert_chain(self.client_certificate, self.client_private_key)
        connection = http.client.HTTPSConnection(
            self.host, self.port, context=tls, timeout=self.timeout_seconds
        )
        try:
            connection.connect()
            socket = connection.sock
            if socket is None:
                raise AppssPartyTransportError("aPPSS party unavailable")
            peer = cast(ssl.SSLSocket, socket).getpeercert(binary_form=True)
            if (
                peer is None
                or hashlib.sha256(peer).hexdigest() != self.server_certificate_sha256
            ):
                raise AppssPartyTransportError("aPPSS server identity mismatch")
            connection.request(
                "POST",
                EVALUATE_ROUTE,
                body=request_bytes,
                headers={
                    "Content-Type": "application/json",
                    "Idempotency-Key": idempotency_key,
                },
            )
            response = connection.getresponse()
            body = response.read(MAX_RESPONSE_BYTES + 1)
            if response.status != 200 or not 0 < len(body) <= MAX_RESPONSE_BYTES:
                raise AppssPartyTransportError("aPPSS party rejected request")
            return body
        except (OSError, ssl.SSLError, http.client.HTTPException) as exc:
            raise AppssPartyTransportError("aPPSS party unavailable") from exc
        finally:
            connection.close()


class _Server(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(
        self,
        address: tuple[str, int],
        *,
        service: AppssPartyService,
        certificate: str,
        private_key: str,
        client_ca: str,
        client_fingerprints: frozenset[str],
    ) -> None:
        self.appss_service = service
        self.client_fingerprints = client_fingerprints
        super().__init__(address, _Handler)
        tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        tls.minimum_version = ssl.TLSVersion.TLSv1_3
        tls.load_cert_chain(certificate, private_key)
        tls.load_verify_locations(cafile=client_ca)
        tls.verify_mode = ssl.CERT_REQUIRED
        self.socket = tls.wrap_socket(self.socket, server_side=True)

    def handle_error(self, request: object, client_address: tuple[str, int]) -> None:
        return


class _Handler(BaseHTTPRequestHandler):
    server: _Server
    protocol_version = "HTTP/1.1"

    def log_message(self, format: str, *args: object) -> None:
        return

    def _send(self, status: int, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)
        self.close_connection = True

    def _reject(self, status: int = 400) -> None:
        self._send(status, b'{"error":"rejected"}')

    def do_POST(self) -> None:  # noqa: N802 - stdlib handler contract.
        connection = cast(ssl.SSLSocket, self.connection)
        certificate = connection.getpeercert(binary_form=True)
        if (
            not certificate
            or hashlib.sha256(certificate).hexdigest()
            not in self.server.client_fingerprints
        ):
            self._reject(403)
            return
        if self.path != EVALUATE_ROUTE:
            self._reject(404)
            return
        content_types = self.headers.get_all("Content-Type", failobj=[])
        idempotency_keys = self.headers.get_all("Idempotency-Key", failobj=[])
        lengths = self.headers.get_all("Content-Length", failobj=[])
        if (
            content_types != ["application/json"]
            or len(idempotency_keys) != 1
            or len(lengths) != 1
        ):
            self._reject()
            return
        try:
            _lower_hex(idempotency_keys[0], "idempotency key")
            length = int(lengths[0])
        except (AppssPartyTransportError, ValueError):
            self._reject()
            return
        if not 0 < length <= MAX_REQUEST_BYTES:
            self._reject(413)
            return
        body = self.rfile.read(length)
        if len(body) != length:
            self._reject()
            return
        try:
            response = self.server.appss_service.evaluate(body)
        except AppssPartyError:
            self._reject()
            return
        self._send(200, response)


def _load_config(path: Path) -> tuple[_Server, AppssPartyStore]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AppssPartyTransportError("invalid aPPSS service configuration") from exc
    if not isinstance(value, dict) or set(value) != {
        "context_digest",
        "holder_id",
        "listen_host",
        "listen_port",
        "store_path",
        "tls",
    }:
        raise AppssPartyTransportError("invalid aPPSS service configuration")
    tls = value["tls"]
    if not isinstance(tls, dict) or set(tls) != {
        "certificate",
        "client_ca",
        "client_certificate_sha256",
        "private_key",
    }:
        raise AppssPartyTransportError("invalid aPPSS TLS configuration")
    fingerprints = tls["client_certificate_sha256"]
    if (
        not isinstance(fingerprints, list)
        or not fingerprints
        or fingerprints != sorted(set(fingerprints))
    ):
        raise AppssPartyTransportError("invalid aPPSS client identities")
    for fingerprint in fingerprints:
        _lower_hex(fingerprint, "client certificate fingerprint")
    try:
        context_digest = bytes.fromhex(value["context_digest"])
        holder_id = int(value["holder_id"])
        host = str(value["listen_host"])
        port = int(value["listen_port"])
    except (TypeError, ValueError) as exc:
        raise AppssPartyTransportError("invalid aPPSS service binding") from exc
    if (
        len(context_digest) != 32
        or isinstance(value["holder_id"], bool)
        or isinstance(value["listen_port"], bool)
        or not host
        or not 1 <= port <= 65535
    ):
        raise AppssPartyTransportError("invalid aPPSS service binding")
    binding = AppssPartyBinding(holder_id, context_digest)
    store = AppssPartyStore(Path(str(value["store_path"])), binding)
    server = _Server(
        (host, port),
        service=AppssPartyService(store),
        certificate=str(tls["certificate"]),
        private_key=str(tls["private_key"]),
        client_ca=str(tls["client_ca"]),
        client_fingerprints=frozenset(fingerprints),
    )
    return server, store


def _lower_hex(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise AppssPartyTransportError(f"invalid {label}")
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run one LOCUS aPPSS holder")
    parser.add_argument("--config", type=Path, required=True)
    arguments = parser.parse_args(argv)
    server, _ = _load_config(arguments.config)
    try:
        server.serve_forever(poll_interval=0.05)
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised by subprocess tests.
    raise SystemExit(main())


__all__ = [
    "AppssPartyTransportError",
    "AppssRemoteParty",
    "EVALUATE_ROUTE",
]
