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

from .appss_formats import (
    APPSS_PROFILE_2_OF_3,
    APPSS_SUITE_ID,
    MAX_INSTALL_BYTES,
    MAX_READY_BYTES,
    MAX_REQUEST_BYTES,
    MAX_RESPONSE_BYTES,
    AppssFormatError,
    AppssHolderBinding,
    canonical_decode,
    context_digest,
    validate_request,
)
from .appss_party import (
    AppssPartyBinding,
    AppssPartyError,
    AppssPartyService,
    AppssPartyStore,
)
from .party_http import certificate_sha256

EVALUATE_ROUTE = "/v1/recovery-suites/appss/evaluations"
INITIALIZE_ROUTE = "/v1/recovery-suites/appss/initializations"
INSTALL_ROUTE = "/v1/recovery-suites/appss/state-installs"
MAX_ERROR_BYTES = 256
REJECTED_BODY = b'{"error":"rejected"}'


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

    @property
    def service_identity(self) -> str:
        return "certificate-sha256:" + self.server_certificate_sha256

    def evaluate(self, request_bytes: bytes, *, idempotency_key: str) -> bytes:
        return self._post(
            EVALUATE_ROUTE,
            request_bytes,
            idempotency_key=idempotency_key,
            maximum_request=MAX_REQUEST_BYTES,
            maximum_response=MAX_RESPONSE_BYTES,
        )

    def initialize(self, request_bytes: bytes, *, idempotency_key: str) -> bytes:
        return self._post(
            INITIALIZE_ROUTE,
            request_bytes,
            idempotency_key=idempotency_key,
            maximum_request=MAX_REQUEST_BYTES,
            maximum_response=MAX_RESPONSE_BYTES,
        )

    def install(self, install_bytes: bytes, *, idempotency_key: str) -> bytes:
        return self._post(
            INSTALL_ROUTE,
            install_bytes,
            idempotency_key=idempotency_key,
            maximum_request=MAX_INSTALL_BYTES,
            maximum_response=MAX_READY_BYTES,
        )

    def _post(
        self,
        route: str,
        request_bytes: bytes,
        *,
        idempotency_key: str,
        maximum_request: int,
        maximum_response: int,
    ) -> bytes:
        if not isinstance(request_bytes, bytes) or not (
            0 < len(request_bytes) <= maximum_request
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
                route,
                body=request_bytes,
                headers={
                    "Content-Type": "application/json",
                    "Idempotency-Key": idempotency_key,
                },
            )
            response = connection.getresponse()
            body = response.read(maximum_response + 1)
            if response.status != 200 or not 0 < len(body) <= maximum_response:
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
        self._send(status, REJECTED_BODY)

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
        route_limits = {
            EVALUATE_ROUTE: MAX_REQUEST_BYTES,
            INITIALIZE_ROUTE: MAX_REQUEST_BYTES,
            INSTALL_ROUTE: MAX_INSTALL_BYTES,
        }
        maximum = route_limits.get(self.path)
        if maximum is None:
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
        if not 0 < length <= maximum:
            self._reject(413)
            return
        body = self.rfile.read(length)
        if len(body) != length:
            self._reject()
            return
        caller_digest = hashlib.sha256(certificate).digest()
        request_digest = hashlib.sha256(body).digest()
        try:
            cached = self.server.appss_service.store.claim_http_request(
                idempotency_key=idempotency_keys[0],
                caller_digest=caller_digest,
                route=self.path,
                request_digest=request_digest,
            )
        except AppssPartyError:
            self._reject(409)
            return
        if cached is not None:
            self._send(*cached)
            return
        status = 200
        try:
            if self.path in {EVALUATE_ROUTE, INITIALIZE_ROUTE}:
                request = canonical_decode(
                    body,
                    maximum=MAX_REQUEST_BYTES,
                    validator=validate_request,
                    label="aPPSS request",
                )
                expected_operation = (
                    "recover" if self.path == EVALUATE_ROUTE else "initialize"
                )
                if request["operation"] != expected_operation:
                    raise AppssPartyError("aPPSS operation route mismatch")
                response = self.server.appss_service.evaluate(body)
            else:
                response = self.server.appss_service.install(body)
        except (AppssPartyError, AppssFormatError):
            status = 400
            response = REJECTED_BODY
        try:
            self.server.appss_service.store.complete_http_request(
                idempotency_key=idempotency_keys[0],
                status=status,
                response_bytes=response,
            )
        except AppssPartyError:
            self._reject(500)
            return
        self._send(status, response)


def _load_config(path: Path) -> tuple[_Server, AppssPartyStore]:
    try:
        encoded = path.read_bytes()
        if not 0 < len(encoded) <= 65_536:
            raise AppssPartyTransportError("invalid aPPSS service configuration")
        value = json.loads(encoded.decode("utf-8"), object_pairs_hook=_unique_object)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AppssPartyTransportError("invalid aPPSS service configuration") from exc
    if not isinstance(value, dict) or set(value) != {
        "context_digest",
        "epoch_context",
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
    if any(
        not isinstance(tls[field], str) or not tls[field]
        for field in ("certificate", "client_ca", "private_key")
    ):
        raise AppssPartyTransportError("invalid aPPSS TLS configuration")
    try:
        configured_context = bytes.fromhex(
            _lower_hex(value["context_digest"], "context digest")
        )
        holder_id = value["holder_id"]
        host = value["listen_host"]
        port = value["listen_port"]
        derived_context, holders = _epoch_context(value["epoch_context"])
    except (TypeError, ValueError, AppssFormatError) as exc:
        raise AppssPartyTransportError("invalid aPPSS service binding") from exc
    if (
        configured_context != derived_context
        or isinstance(holder_id, bool)
        or not isinstance(holder_id, int)
        or isinstance(port, bool)
        or not isinstance(port, int)
        or not isinstance(host, str)
        or not host
        or not 1 <= port <= 65535
        or holder_id not in {holder.index for holder in holders}
    ):
        raise AppssPartyTransportError("invalid aPPSS service binding")
    local_holder = holders[holder_id - 1]
    expected_identity = "certificate-sha256:" + certificate_sha256(
        str(tls["certificate"])
    )
    if (
        local_holder.index != holder_id
        or local_holder.service_identity != expected_identity
    ):
        raise AppssPartyTransportError("invalid aPPSS service identity binding")
    binding = AppssPartyBinding(holder_id, configured_context)
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


def _epoch_context(value: object) -> tuple[bytes, tuple[AppssHolderBinding, ...]]:
    if not isinstance(value, dict) or set(value) != {
        "backup_id",
        "configuration_digest",
        "epoch",
        "holders",
        "k",
        "n",
        "policy_id",
        "profile_id",
        "suite_id",
    }:
        raise AppssPartyTransportError("invalid aPPSS epoch context")
    if (
        value["suite_id"] != APPSS_SUITE_ID
        or value["profile_id"] != APPSS_PROFILE_2_OF_3
        or value["k"] != 2
        or value["n"] != 3
        or isinstance(value["epoch"], bool)
        or not isinstance(value["epoch"], int)
        or not 1 <= value["epoch"] <= 2**63 - 1
        or not isinstance(value["policy_id"], str)
    ):
        raise AppssPartyTransportError("invalid aPPSS epoch context")
    encoded_holders = value["holders"]
    if not isinstance(encoded_holders, list) or len(encoded_holders) != 3:
        raise AppssPartyTransportError("invalid aPPSS epoch membership")
    holders: list[AppssHolderBinding] = []
    for item in encoded_holders:
        if not isinstance(item, dict) or set(item) != {
            "index",
            "party_id",
            "service_identity",
        }:
            raise AppssPartyTransportError("invalid aPPSS epoch membership")
        holders.append(
            AppssHolderBinding(
                index=item["index"],
                party_id=item["party_id"],
                service_identity=item["service_identity"],
            )
        )
    holder_tuple = tuple(holders)
    if [holder.index for holder in holder_tuple] != [1, 2, 3]:
        raise AppssPartyTransportError("invalid aPPSS epoch membership")
    derived = context_digest(
        backup_id=bytes.fromhex(
            _lower_hex(value["backup_id"], "backup identifier", bytes_length=16)
        ),
        epoch=value["epoch"],
        policy_id=value["policy_id"],
        holders=holder_tuple,
        k=2,
        n=3,
        configuration_digest=bytes.fromhex(
            _lower_hex(value["configuration_digest"], "configuration digest")
        ),
    )
    return derived, holder_tuple


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise AppssPartyTransportError("duplicate aPPSS configuration member")
        result[key] = value
    return result


def _lower_hex(value: object, label: str, *, bytes_length: int = 32) -> str:
    if (
        not isinstance(value, str)
        or len(value) != bytes_length * 2
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
    "INITIALIZE_ROUTE",
    "INSTALL_ROUTE",
]
