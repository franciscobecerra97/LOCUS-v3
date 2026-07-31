"""Strict mutually authenticated HTTPS boundary for LOCUS authorizers.

The coordinator is deliberately an untrusted collector. Each endpoint invokes
the same durable PartyStore transition used by the in-process reference path;
no remote endpoint accepts an unsigned state update or raw counter value.
"""

from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import http.client
import json
import secrets
import ssl
import threading
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, BinaryIO, cast

from . import _tpass_native as native
from .attempt_certificates import (
    AttemptEntry,
    AuthorizationCertificate,
    AuthorizerConfig,
    AuthorizerSigner,
    CertificateError,
    EntryVote,
    FreshnessRequest,
    FreshnessVote,
    InstallVote,
    PrepareCertificate,
)
from .attempt_coordinator import (
    AttemptCoordinator,
    AuthorizerNode,
    AuthorizerPeer,
    AuthorizerState,
)
from .crypto import hash_bytes
from .epoch_lifecycle import (
    EpochActivationCertificate,
    EpochApproval,
    EpochReady,
    EpochTransition,
    LifecycleCertificateError,
    RuntimeEpochPackage,
)
from .party_service import CommitmentResult, NativePartyService
from .party_store import (
    BudgetExhausted,
    Conflict,
    EpochConfig,
    InvalidState,
    PartyStore,
    PartyStoreError,
    RequestInProgress,
    SessionLost,
)

API_VERSION = "locus-party-api-v1"
MAX_MESSAGE_BYTES = 1_048_576
MAX_TPASS_OBJECT_BYTES = 262_144


class PartyHttpError(PartyStoreError):
    """An authenticated remote authorizer was unavailable or malformed."""


class PartyUnavailable(PartyHttpError):
    """A remote operation failed before a trustworthy response was received."""


class PartyProtocolError(PartyHttpError):
    """A remote response was malformed, unauthenticated, or inconsistent."""


class _RequestError(Exception):
    pass


class _AuthorizationError(Exception):
    pass


def _exact_dict(value: object, fields: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        raise _RequestError(f"invalid {label}")
    return value


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _RequestError("duplicate JSON member")
        result[key] = value
    return result


def _decode_json(data: bytes) -> object:
    try:
        return json.loads(data.decode("utf-8"), object_pairs_hook=_unique_object)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _RequestError("invalid JSON") from exc


def _encode_json(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=True, allow_nan=False, sort_keys=True, separators=(",", ":")
    ).encode("ascii")


def _encode_base64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _decode_base64url(value: object, label: str) -> bytes:
    if (
        not isinstance(value, str)
        or not value
        or "=" in value
        or any(
            character
            not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
            for character in value
        )
    ):
        raise _RequestError(f"invalid {label}")
    padding = "=" * ((4 - len(value) % 4) % 4)
    try:
        decoded = base64.b64decode(value + padding, altchars=b"-_", validate=True)
    except (ValueError, binascii.Error) as exc:
        raise _RequestError(f"invalid {label}") from exc
    if (
        not decoded
        or len(decoded) > MAX_TPASS_OBJECT_BYTES
        or _encode_base64url(decoded) != value
    ):
        raise _RequestError(f"invalid {label}")
    return decoded


def _hex_text(value: object, label: str, *, bytes_length: int) -> str:
    if (
        not isinstance(value, str)
        or len(value) != bytes_length * 2
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise _RequestError(f"invalid {label}")
    return value


def _selected_parties(value: object) -> list[int]:
    if (
        not isinstance(value, list)
        or not value
        or len(value) > 255
        or any(isinstance(item, bool) or not isinstance(item, int) for item in value)
        or value != sorted(set(value))
        or value[0] < 1
        or value[-1] > 255
    ):
        raise _RequestError("invalid selected party set")
    return value


def certificate_sha256(path: str | Path) -> str:
    """Return the SHA-256 fingerprint of a PEM-encoded certificate."""

    pem = Path(path).read_text(encoding="ascii")
    der = ssl.PEM_cert_to_DER_cert(pem)
    return hashlib.sha256(der).hexdigest()


@dataclass
class PartyServerContext:
    store: PartyStore
    signer: AuthorizerSigner
    boot_config: AuthorizerConfig
    client_identities: dict[str, str]
    peer_nodes: tuple[AuthorizerPeer, ...] = ()
    native_role: bool = False
    _services: dict[tuple[str, int], NativePartyService] = field(
        default_factory=dict, init=False, repr=False
    )
    _service_lock: threading.RLock = field(
        default_factory=threading.RLock, init=False, repr=False
    )

    def validate(self) -> None:
        self.boot_config.validate()
        if self.signer.public_key_hex != self.boot_config.public_keys.get(
            self.signer.party_id
        ):
            raise CertificateError("authorizer signer does not match configuration")
        if not self.client_identities:
            raise CertificateError("no coordinator certificate is authorized")
        for fingerprint, role in self.client_identities.items():
            if len(fingerprint) != 64 or any(
                character not in "0123456789abcdef" for character in fingerprint
            ):
                raise CertificateError("invalid coordinator certificate fingerprint")
            if role != "coordinator" and not role.startswith("party:"):
                raise CertificateError("invalid service identity role")
            if role.startswith("party:"):
                try:
                    party_id = int(role.removeprefix("party:"))
                except ValueError as exc:
                    raise CertificateError("invalid party identity role") from exc
                if party_id not in self.boot_config.public_keys:
                    raise CertificateError("unknown party identity role")
        if len(set(self.client_identities.values())) != len(self.client_identities):
            raise CertificateError("duplicate service identity role")

    def config_for(self, bid: str, epoch: int) -> AuthorizerConfig:
        record = self.store.runtime_epoch_package(bid, epoch)
        config = record.authorizer_config
        if config.public_keys.get(self.signer.party_id) != self.signer.public_key_hex:
            raise InvalidState("epoch configuration does not contain local signer")
        return config

    def native_service_for(self, bid: str, epoch: int) -> NativePartyService:
        key = (bid, epoch)
        with self._service_lock:
            existing = self._services.get(key)
            if existing is not None:
                return existing
            record = self.store.runtime_epoch_package(bid, epoch, require_active=True)
            if record.parameters is None or record.party_state is None:
                raise InvalidState("native recovery is unavailable")
            try:
                parameters = native.PublicParameters.from_bytes(record.parameters)
                state = native.PartyState.from_secret_bytes(record.party_state)
            except native.NativeTpassError as exc:
                raise InvalidState(
                    "stored native runtime package is malformed"
                ) from exc
            if state.party_id != self.signer.party_id:
                raise InvalidState("stored TPASS state belongs to another party")
            service = NativePartyService(
                store=self.store,
                parameters=parameters,
                state=state,
                authorizer_config=record.authorizer_config,
                freshness_coordinator=AttemptCoordinator(
                    config=record.authorizer_config,
                    nodes=[AuthorizerNode(self.store, self.signer), *self.peer_nodes],
                ),
                recover_open_phases=False,
            )
            self._services[key] = service
            return service

    def activate(
        self,
        certificate: EpochActivationCertificate,
        predecessor_config: AuthorizerConfig,
        successor_config: AuthorizerConfig,
    ) -> str:
        certificate_hash = self.store.activate_successor_epoch(
            certificate, predecessor_config, successor_config
        )
        transition = certificate.transition
        with self._service_lock:
            self._services.pop((transition.bid, transition.predecessor_epoch), None)
            self._services.pop((transition.bid, transition.successor_epoch), None)
        return certificate_hash


class PartyHttpServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def handle_error(self, request: object, client_address: tuple[str, int]) -> None:
        # Never emit stack traces or peer addresses from malformed/aborted calls.
        return

    def __init__(
        self,
        address: tuple[str, int],
        *,
        context: PartyServerContext,
        certificate: str,
        private_key: str,
        client_ca: str,
    ) -> None:
        context.validate()
        self.party_context = context
        self.http_boot_nonce = secrets.token_hex(32)
        context.store.recover_http_requests()
        super().__init__(address, _PartyRequestHandler)
        tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        tls.minimum_version = ssl.TLSVersion.TLSv1_3
        tls.load_cert_chain(certificate, private_key)
        tls.load_verify_locations(cafile=client_ca)
        tls.verify_mode = ssl.CERT_REQUIRED
        self.socket = tls.wrap_socket(self.socket, server_side=True)


class _PartyRequestHandler(BaseHTTPRequestHandler):
    server: PartyHttpServer
    protocol_version = "HTTP/1.1"

    def setup(self) -> None:
        super().setup()
        self.connection.settimeout(5.0)

    def log_message(self, format: str, *args: object) -> None:
        # Do not emit request paths, identifiers, or cryptographic objects.
        return

    def _client_identity(self) -> tuple[str, str] | None:
        connection = cast(ssl.SSLSocket, self.connection)
        certificate = connection.getpeercert(binary_form=True)
        if not certificate:
            return None
        fingerprint = hashlib.sha256(certificate).hexdigest()
        role = self.server.party_context.client_identities.get(fingerprint)
        return None if role is None else (fingerprint, role)

    def _send_body(self, status: int, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)
        self.close_connection = True

    def _success_body(self, result: object) -> bytes:
        return _encode_json(
            {
                "api_version": API_VERSION,
                "party_id": self.server.party_context.signer.party_id,
                "result": result,
            }
        )

    def _error_body(self, code: str) -> bytes:
        return _encode_json(
            {
                "api_version": API_VERSION,
                "error": {"code": code},
                "party_id": self.server.party_context.signer.party_id,
            }
        )

    def _send(self, status: int, result: object) -> None:
        self._send_body(status, self._success_body(result))

    def _send_error_code(self, status: int, code: str) -> None:
        self._send_body(status, self._error_body(code))

    def _authorize_client(self) -> tuple[str, str] | None:
        identity = self._client_identity()
        if identity is not None:
            return identity
        self._send_error_code(403, "unauthorized_peer")
        return None

    def _read_idempotency_key(self) -> str:
        values = self.headers.get_all("Idempotency-Key", failobj=[])
        if len(values) != 1:
            raise _RequestError("exactly one idempotency key is required")
        return _hex_text(values[0], "idempotency key", bytes_length=32)

    def _complete_and_send(
        self,
        *,
        status: int,
        body: bytes,
        idempotency_key: str | None,
        owns_request: bool,
    ) -> None:
        if idempotency_key is not None and owns_request:
            try:
                self.server.party_context.store.complete_http_request(
                    idempotency_key=idempotency_key,
                    owner_boot_nonce=self.server.http_boot_nonce,
                    response_status=status,
                    response_body=body,
                )
            except PartyStoreError:
                self._make_retryable(idempotency_key)
                self._send_error_code(503, "authorizer_unavailable")
                return
        self._send_body(status, body)

    def _make_retryable(self, idempotency_key: str | None) -> None:
        if idempotency_key is None:
            return
        try:
            self.server.party_context.store.retry_http_request(
                idempotency_key=idempotency_key,
                owner_boot_nonce=self.server.http_boot_nonce,
            )
        except PartyStoreError:
            pass

    def _read_body(self) -> dict[str, Any]:
        if self.headers.get("Transfer-Encoding") is not None:
            raise _RequestError("transfer encoding is unsupported")
        if self.headers.get("Content-Type") != "application/json":
            raise _RequestError("invalid content type")
        length_text = self.headers.get("Content-Length")
        try:
            length = int(length_text) if length_text is not None else -1
        except ValueError as exc:
            raise _RequestError("invalid content length") from exc
        if length < 1 or length > MAX_MESSAGE_BYTES:
            raise _RequestError("invalid content length")
        stream = cast(BinaryIO, self.rfile)
        value = _decode_json(stream.read(length))
        request = _exact_dict(value, {"api_version", "request"}, "request envelope")
        if request["api_version"] != API_VERSION:
            raise _RequestError("unsupported API version")
        if not isinstance(request["request"], dict):
            raise _RequestError("invalid request")
        return request["request"]

    def do_GET(self) -> None:
        if self._authorize_client() is None:
            return
        if self.path != "/health/live":
            self._send_error_code(404, "not_found")
            return
        self._send(200, {"status": "live"})

    def do_POST(self) -> None:
        identity = self._authorize_client()
        if identity is None:
            return
        caller_fingerprint, role = identity
        idempotency_key: str | None = None
        owns_request = False
        try:
            request = self._read_body()
            if self.path != "/v1/ledger/state-summaries":
                idempotency_key = self._read_idempotency_key()
                reservation = self.server.party_context.store.begin_http_request(
                    idempotency_key=idempotency_key,
                    caller_fingerprint=caller_fingerprint,
                    method="POST",
                    route=self.path,
                    request_digest=hash_bytes(
                        "LOCUS/http-request/v1",
                        _encode_json({"api_version": API_VERSION, "request": request}),
                    ).hex(),
                    owner_boot_nonce=self.server.http_boot_nonce,
                )
                if reservation.state == "COMPLETE":
                    if (
                        reservation.response_status is None
                        or reservation.response_body is None
                    ):
                        raise PartyStoreError("incomplete stored HTTP response")
                    self._send_body(
                        reservation.response_status, reservation.response_body
                    )
                    return
                owns_request = True
            result = self._dispatch(request, role)
        except RequestInProgress:
            self._send_error_code(409, "request_in_progress")
            return
        except _AuthorizationError:
            self._complete_and_send(
                status=403,
                body=self._error_body("unauthorized_role"),
                idempotency_key=idempotency_key,
                owns_request=owns_request,
            )
            return
        except _RequestError:
            self._complete_and_send(
                status=400,
                body=self._error_body("invalid_request"),
                idempotency_key=idempotency_key,
                owns_request=owns_request,
            )
            return
        except (
            CertificateError,
            LifecycleCertificateError,
            InvalidState,
            SessionLost,
            native.NativeTpassError,
        ):
            self._complete_and_send(
                status=400,
                body=self._error_body("invalid_state"),
                idempotency_key=idempotency_key,
                owns_request=owns_request,
            )
            return
        except (Conflict, BudgetExhausted):
            self._complete_and_send(
                status=409,
                body=self._error_body("conflict"),
                idempotency_key=idempotency_key,
                owns_request=owns_request,
            )
            return
        except PartyStoreError:
            self._make_retryable(idempotency_key if owns_request else None)
            self._send_error_code(503, "authorizer_unavailable")
            return
        except Exception:
            self._make_retryable(idempotency_key if owns_request else None)
            self._send_error_code(500, "internal_error")
            return
        self._complete_and_send(
            status=200,
            body=self._success_body(result),
            idempotency_key=idempotency_key,
            owns_request=owns_request,
        )

    @staticmethod
    def _require_role(role: str, allowed: set[str]) -> None:
        if role not in allowed and not (
            "party" in allowed and role.startswith("party:")
        ):
            raise _AuthorizationError("caller role is not permitted")

    def _dispatch(self, request: dict[str, Any], role: str) -> object:
        context = self.server.party_context
        if self.path == "/v1/lifecycle/epoch-approvals":
            self._require_role(role, {"coordinator"})
            parsed = _exact_dict(
                request,
                {"predecessor_config", "successor_config", "transition"},
                "epoch-approval request",
            )
            predecessor_config = AuthorizerConfig.from_dict(
                parsed["predecessor_config"]
            )
            successor_config = AuthorizerConfig.from_dict(parsed["successor_config"])
            transition = EpochTransition.from_dict(parsed["transition"])
            return context.store.create_epoch_approval(
                transition,
                predecessor_config,
                successor_config,
                context.signer,
            ).to_dict()
        if self.path == "/v1/lifecycle/epoch-preparations":
            self._require_role(role, {"coordinator"})
            parsed = _exact_dict(
                request,
                {
                    "native_party",
                    "predecessor_config",
                    "successor_config",
                    "transition",
                },
                "epoch-preparation request",
            )
            predecessor_config = AuthorizerConfig.from_dict(
                parsed["predecessor_config"]
            )
            successor_config = AuthorizerConfig.from_dict(parsed["successor_config"])
            transition = EpochTransition.from_dict(parsed["transition"])
            parameters_bytes: bytes | None = None
            party_state_bytes: bytes | None = None
            if (parsed["native_party"] is not None) != context.native_role:
                raise InvalidState("successor changes the local TPASS role")
            if parsed["native_party"] is not None:
                native_package = _exact_dict(
                    parsed["native_party"],
                    {"parameters", "state"},
                    "native runtime package",
                )
                parameters_bytes = _decode_base64url(
                    native_package["parameters"], "public parameters"
                )
                party_state_bytes = _decode_base64url(
                    native_package["state"], "party state"
                )
                parameters = native.PublicParameters.from_bytes(parameters_bytes)
                state = native.PartyState.from_secret_bytes(party_state_bytes)
                if (
                    state.party_id != context.signer.party_id
                    or state.party_id > parameters.parties
                    or parameters.threshold > parameters.parties
                ):
                    raise InvalidState("native runtime package belongs elsewhere")
            ready = context.store.prepare_successor_epoch(
                EpochConfig(
                    bid=transition.bid,
                    epoch=transition.successor_epoch,
                    party_id=context.signer.party_id,
                    config_digest=transition.successor_config_digest,
                    backup_digest=transition.successor_backup_digest,
                    budget=transition.successor_budget,
                ),
                transition,
                predecessor_config,
                successor_config,
                context.signer,
                parameters=parameters_bytes,
                party_state=party_state_bytes,
            )
            return ready.to_dict()
        if self.path == "/v1/lifecycle/epoch-activations":
            self._require_role(role, {"coordinator"})
            parsed = _exact_dict(
                request,
                {"certificate", "predecessor_config", "successor_config"},
                "epoch-activation request",
            )
            predecessor_config = AuthorizerConfig.from_dict(
                parsed["predecessor_config"]
            )
            successor_config = AuthorizerConfig.from_dict(parsed["successor_config"])
            lifecycle_certificate = EpochActivationCertificate.from_dict(
                parsed["certificate"]
            )
            return {
                "certificate_hash": context.activate(
                    lifecycle_certificate, predecessor_config, successor_config
                )
            }
        if self.path == "/v1/ledger/state-summaries":
            self._require_role(role, {"coordinator", "party"})
            parsed = _exact_dict(
                request, {"bid", "epoch", "sid"}, "state-summary request"
            )
            installed_certificate = context.store.installed_certificate(
                parsed["bid"], parsed["epoch"], parsed["sid"]
            )
            return {
                "installed_certificate": (
                    None
                    if installed_certificate is None
                    else installed_certificate.to_dict()
                ),
                "next_slot_lock": context.store.next_slot_lock(
                    parsed["bid"], parsed["epoch"]
                ),
                "status": context.store.status(parsed["bid"], parsed["epoch"]),
            }
        if self.path == "/v1/ledger/entry-votes":
            self._require_role(role, {"coordinator"})
            parsed = _exact_dict(request, {"entry"}, "entry-vote request")
            entry = AttemptEntry.from_dict(parsed["entry"])
            return context.store.create_entry_vote(
                entry, context.config_for(entry.bid, entry.epoch), context.signer
            ).to_dict()
        if self.path == "/v1/ledger/install-votes":
            self._require_role(role, {"coordinator", "party"})
            parsed = _exact_dict(request, {"prepare"}, "install-vote request")
            prepare = PrepareCertificate.from_dict(parsed["prepare"])
            return context.store.create_install_vote(
                prepare,
                context.config_for(prepare.entry.bid, prepare.entry.epoch),
                context.signer,
            ).to_dict()
        if self.path == "/v1/ledger/authorization-certificates":
            self._require_role(role, {"coordinator", "party"})
            parsed = _exact_dict(
                request, {"certificate"}, "certificate-install request"
            )
            authorization_certificate = AuthorizationCertificate.from_dict(
                parsed["certificate"]
            )
            entry = authorization_certificate.prepare.entry
            context.store.install_certificate(
                authorization_certificate, context.config_for(entry.bid, entry.epoch)
            )
            return {"certificate_hash": authorization_certificate.certificate_hash}
        if self.path == "/v1/ledger/freshness-votes":
            parsed = _exact_dict(request, {"request"}, "freshness-vote request")
            freshness_request = FreshnessRequest.from_dict(parsed["request"])
            self._require_role(role, {f"party:{freshness_request.responding_party_id}"})
            return context.store.create_freshness_vote(
                freshness_request,
                context.config_for(freshness_request.bid, freshness_request.epoch),
                context.signer,
            ).to_dict()
        path = self.path.split("/")
        if (
            len(path) == 5
            and path[1] == "v1"
            and path[2] == "recoveries"
            and path[4] == "commitments"
        ):
            self._require_role(role, {"coordinator"})
            sid = _hex_text(path[3], "session identifier", bytes_length=32)
            parsed = _exact_dict(
                request,
                {"authorization_certificate", "request", "selected"},
                "commitment request",
            )
            authorization_certificate = AuthorizationCertificate.from_dict(
                parsed["authorization_certificate"]
            )
            if authorization_certificate.prepare.entry.sid != sid:
                raise Conflict("recovery route does not match authorization")
            entry = authorization_certificate.prepare.entry
            result = context.native_service_for(
                entry.bid, entry.epoch
            ).prepare_commitment(
                authorization_certificate=authorization_certificate,
                request=_decode_base64url(parsed["request"], "TPASS request"),
                selected=_selected_parties(parsed["selected"]),
            )
            return {
                "commitment": _encode_base64url(result.commitment),
                "phase_instance_id": result.phase_instance_id,
            }
        if (
            len(path) == 5
            and path[1] == "v1"
            and path[2] == "recoveries"
            and path[4] == "responses"
        ):
            self._require_role(role, {"coordinator"})
            sid = _hex_text(path[3], "session identifier", bytes_length=32)
            parsed = _exact_dict(
                request,
                {"commitments", "phase_instance_id", "request", "selected"},
                "response request",
            )
            selected = _selected_parties(parsed["selected"])
            if not isinstance(parsed["commitments"], list) or len(
                parsed["commitments"]
            ) != len(selected):
                raise _RequestError("invalid commitment collection")
            commitments = [
                _decode_base64url(commitment, "party commitment")
                for commitment in parsed["commitments"]
            ]
            phase_instance_id = _hex_text(
                parsed["phase_instance_id"],
                "phase instance identifier",
                bytes_length=32,
            )
            bid, epoch = context.store.phase_scope(phase_instance_id)
            response = context.native_service_for(bid, epoch).respond(
                sid=sid,
                phase_instance_id=phase_instance_id,
                request=_decode_base64url(parsed["request"], "TPASS request"),
                selected=selected,
                commitments=commitments,
            )
            return {"response": _encode_base64url(response)}
        raise _RequestError("unknown route")


class RemoteAuthorizerNode:
    """Pinned-mTLS implementation of the coordinator's authorizer peer."""

    def __init__(
        self,
        *,
        party_id: int,
        host: str,
        port: int,
        server_ca: str,
        client_certificate: str,
        client_private_key: str,
        server_certificate_sha256: str,
        timeout_seconds: float = 5.0,
        transport_attempts: int = 2,
    ) -> None:
        if (
            isinstance(party_id, bool)
            or not isinstance(party_id, int)
            or not 1 <= party_id <= 255
        ):
            raise ValueError("invalid party identifier")
        if not isinstance(host, str) or not host:
            raise ValueError("invalid authorizer host")
        if (
            isinstance(port, bool)
            or not isinstance(port, int)
            or not 1 <= port <= 65535
        ):
            raise ValueError("invalid authorizer port")
        if (
            isinstance(timeout_seconds, bool)
            or not isinstance(timeout_seconds, (int, float))
            or not 0 < timeout_seconds <= 60
        ):
            raise ValueError("invalid authorizer timeout")
        if (
            isinstance(transport_attempts, bool)
            or not isinstance(transport_attempts, int)
            or not 1 <= transport_attempts <= 3
        ):
            raise ValueError("invalid authorizer transport-attempt count")
        if len(server_certificate_sha256) != 64 or any(
            character not in "0123456789abcdef"
            for character in server_certificate_sha256
        ):
            raise ValueError("invalid server-certificate fingerprint")
        self._party_id = party_id
        self.host = host
        self.port = port
        self.server_certificate_sha256 = server_certificate_sha256
        self.client_certificate_sha256 = certificate_sha256(client_certificate)
        self.timeout_seconds = timeout_seconds
        self.transport_attempts = transport_attempts
        self._request_body_bytes = 0
        self._response_body_bytes = 0
        self._tls = ssl.create_default_context(
            ssl.Purpose.SERVER_AUTH, cafile=server_ca
        )
        self._tls.minimum_version = ssl.TLSVersion.TLSv1_3
        self._tls.load_cert_chain(client_certificate, client_private_key)

    @property
    def party_id(self) -> int:
        return self._party_id

    @property
    def application_bytes(self) -> dict[str, int]:
        """Return aggregate HTTP JSON body bytes for this client instance."""

        return {
            "received": self._response_body_bytes,
            "sent": self._request_body_bytes,
        }

    def _post_once(
        self,
        path: str,
        request: object,
        *,
        idempotency_key: str | None = None,
    ) -> object:
        connection = http.client.HTTPSConnection(
            self.host,
            self.port,
            context=self._tls,
            timeout=self.timeout_seconds,
        )
        body = _encode_json({"api_version": API_VERSION, "request": request})
        headers = {"Content-Type": "application/json"}
        if path != "/v1/ledger/state-summaries":
            if idempotency_key is None:
                idempotency_key = hash_bytes(
                    "LOCUS/http-idempotency-key/v1",
                    bytes.fromhex(self.client_certificate_sha256),
                    self.party_id.to_bytes(1, "big"),
                    path.encode("ascii"),
                    body,
                ).hex()
            try:
                _hex_text(idempotency_key, "idempotency key", bytes_length=32)
            except _RequestError as exc:
                raise ValueError("invalid idempotency key") from exc
            headers["Idempotency-Key"] = idempotency_key
        try:
            connection.connect()
            socket = connection.sock
            if socket is None:
                raise PartyUnavailable("authorizer TLS connection failed")
            peer_certificate = socket.getpeercert(binary_form=True)
            if (
                not peer_certificate
                or hashlib.sha256(peer_certificate).hexdigest()
                != self.server_certificate_sha256
            ):
                raise PartyProtocolError("authorizer certificate pin mismatch")
            self._request_body_bytes += len(body)
            connection.request("POST", path, body=body, headers=headers)
            response = connection.getresponse()
            response_body = response.read(MAX_MESSAGE_BYTES + 1)
            self._response_body_bytes += len(response_body)
            if len(response_body) > MAX_MESSAGE_BYTES:
                raise PartyProtocolError("oversized authorizer response")
            if response.getheader("Content-Type") != "application/json":
                raise PartyProtocolError("invalid authorizer content type")
            envelope = _decode_json(response_body)
            if response.status != 200:
                error = _exact_dict(
                    envelope,
                    {"api_version", "error", "party_id"},
                    "error response",
                )
                code = _exact_dict(error["error"], {"code"}, "error body")["code"]
                if (
                    error["api_version"] != API_VERSION
                    or error["party_id"] != self.party_id
                ):
                    raise PartyProtocolError("authorizer identity mismatch")
                if response.status == 409 and code == "conflict":
                    raise Conflict("remote authorizer conflict")
                if (
                    response.status in {500, 503}
                    and code in {"authorizer_unavailable", "internal_error"}
                ) or (response.status == 409 and code == "request_in_progress"):
                    raise PartyUnavailable("remote authorizer is unavailable")
                raise PartyProtocolError("remote authorizer rejected request")
            parsed = _exact_dict(
                envelope,
                {"api_version", "party_id", "result"},
                "authorizer response",
            )
            if (
                parsed["api_version"] != API_VERSION
                or parsed["party_id"] != self.party_id
            ):
                raise PartyProtocolError("authorizer response identity mismatch")
            return parsed["result"]
        except (OSError, ssl.SSLError, http.client.HTTPException) as exc:
            raise PartyUnavailable("authorizer transport failed") from exc
        except _RequestError as exc:
            raise PartyProtocolError("invalid authorizer response") from exc
        finally:
            connection.close()

    def _post(
        self,
        path: str,
        request: object,
        *,
        idempotency_key: str | None = None,
    ) -> object:
        """Retry only transport-ambiguous delivery of one exact request body."""

        last_error: PartyUnavailable | None = None
        for _ in range(self.transport_attempts):
            try:
                return self._post_once(path, request, idempotency_key=idempotency_key)
            except PartyUnavailable as exc:
                last_error = exc
        if last_error is None:  # pragma: no cover - constructor forbids zero attempts.
            raise AssertionError("transport retry loop did not run")
        raise last_error

    def state_summary(self, bid: str, epoch: int, sid: str) -> AuthorizerState:
        try:
            result = _exact_dict(
                self._post(
                    "/v1/ledger/state-summaries",
                    {"bid": bid, "epoch": epoch, "sid": sid},
                ),
                {"installed_certificate", "next_slot_lock", "status"},
                "state summary",
            )
            status = _exact_dict(
                result["status"],
                {
                    "backup_digest",
                    "budget",
                    "consumed",
                    "installed_head",
                    "installed_index",
                    "party_id",
                    "status",
                },
                "epoch status",
            )
            if status["party_id"] != self.party_id:
                raise PartyProtocolError("state-summary party mismatch")
            for field in ("budget", "consumed", "installed_index"):
                value = status[field]
                if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                    raise PartyProtocolError("invalid remote epoch status")
            if status["budget"] < 1 or status["status"] not in {
                "ACTIVE",
                "RETIRED",
                "FAILED_CLOSED",
            }:
                raise PartyProtocolError("invalid remote epoch status")
            backup_digest = status["backup_digest"]
            if (
                not isinstance(backup_digest, str)
                or len(backup_digest) != 64
                or any(
                    character not in "0123456789abcdef" for character in backup_digest
                )
            ):
                raise PartyProtocolError("invalid remote backup digest")
            installed_head = status["installed_head"]
            if (
                not isinstance(installed_head, str)
                or len(installed_head) != 64
                or any(
                    character not in "0123456789abcdef" for character in installed_head
                )
            ):
                raise PartyProtocolError("invalid remote epoch head")
            lock = result["next_slot_lock"]
            if lock is not None and (
                not isinstance(lock, str)
                or len(lock) != 64
                or any(character not in "0123456789abcdef" for character in lock)
            ):
                raise PartyProtocolError("invalid remote slot lock")
            encoded_certificate = result["installed_certificate"]
            certificate = (
                None
                if encoded_certificate is None
                else AuthorizationCertificate.from_dict(encoded_certificate)
            )
            return AuthorizerState(
                status=status, next_slot_lock=lock, installed_certificate=certificate
            )
        except (CertificateError, _RequestError) as exc:
            raise PartyProtocolError("invalid state-summary response") from exc

    def create_entry_vote(
        self,
        entry: AttemptEntry,
        config: AuthorizerConfig,
        *,
        idempotency_key: str | None = None,
    ) -> EntryVote:
        try:
            vote = EntryVote.from_dict(
                self._post(
                    "/v1/ledger/entry-votes",
                    {"entry": entry.to_dict()},
                    idempotency_key=idempotency_key,
                )
            )
            vote.verify(entry, config)
            return vote
        except (CertificateError, _RequestError) as exc:
            raise PartyProtocolError("invalid remote entry vote") from exc

    def create_install_vote(
        self,
        prepare: PrepareCertificate,
        config: AuthorizerConfig,
        *,
        idempotency_key: str | None = None,
    ) -> InstallVote:
        try:
            vote = InstallVote.from_dict(
                self._post(
                    "/v1/ledger/install-votes",
                    {"prepare": prepare.to_dict()},
                    idempotency_key=idempotency_key,
                )
            )
            vote.verify(prepare, config)
            return vote
        except (CertificateError, _RequestError) as exc:
            raise PartyProtocolError("invalid remote install vote") from exc

    def install_certificate(
        self,
        certificate: AuthorizationCertificate,
        config: AuthorizerConfig,
        *,
        idempotency_key: str | None = None,
    ) -> None:
        try:
            certificate.verify(config)
            result = _exact_dict(
                self._post(
                    "/v1/ledger/authorization-certificates",
                    {"certificate": certificate.to_dict()},
                    idempotency_key=idempotency_key,
                ),
                {"certificate_hash"},
                "certificate-install result",
            )
            if result["certificate_hash"] != certificate.certificate_hash:
                raise PartyProtocolError("installed-certificate hash mismatch")
        except (CertificateError, _RequestError) as exc:
            raise PartyProtocolError("invalid certificate-install response") from exc

    def create_freshness_vote(
        self,
        request: FreshnessRequest,
        config: AuthorizerConfig,
        *,
        idempotency_key: str | None = None,
    ) -> FreshnessVote:
        try:
            vote = FreshnessVote.from_dict(
                self._post(
                    "/v1/ledger/freshness-votes",
                    {"request": request.to_dict()},
                    idempotency_key=idempotency_key,
                )
            )
            vote.verify(request, config)
            return vote
        except (CertificateError, _RequestError) as exc:
            raise PartyProtocolError("invalid remote freshness vote") from exc

    def create_epoch_approval(
        self,
        transition: EpochTransition,
        predecessor_config: AuthorizerConfig,
        successor_config: AuthorizerConfig,
        *,
        idempotency_key: str | None = None,
    ) -> EpochApproval:
        try:
            transition.verify_configs(predecessor_config, successor_config)
            approval = EpochApproval.from_dict(
                self._post(
                    "/v1/lifecycle/epoch-approvals",
                    {
                        "predecessor_config": predecessor_config.to_dict(),
                        "successor_config": successor_config.to_dict(),
                        "transition": transition.to_dict(),
                    },
                    idempotency_key=idempotency_key,
                )
            )
            approval.verify(transition, predecessor_config)
            if approval.party_id != self.party_id:
                raise PartyProtocolError("lifecycle approval party mismatch")
            return approval
        except (CertificateError, LifecycleCertificateError, _RequestError) as exc:
            raise PartyProtocolError("invalid remote lifecycle approval") from exc

    def prepare_successor_epoch(
        self,
        transition: EpochTransition,
        predecessor_config: AuthorizerConfig,
        successor_config: AuthorizerConfig,
        *,
        parameters: bytes | None,
        party_state: bytes | None,
        idempotency_key: str | None = None,
    ) -> EpochReady:
        if (parameters is None) != (party_state is None):
            raise ValueError("incomplete native runtime package")
        try:
            transition.verify_configs(predecessor_config, successor_config)
            runtime_package = RuntimeEpochPackage.create(
                transition,
                successor_config,
                self.party_id,
                parameters=parameters,
                party_state=party_state,
            )
            ready = EpochReady.from_dict(
                self._post(
                    "/v1/lifecycle/epoch-preparations",
                    {
                        "native_party": (
                            None
                            if parameters is None
                            else {
                                "parameters": _encode_base64url(parameters),
                                "state": _encode_base64url(cast(bytes, party_state)),
                            }
                        ),
                        "predecessor_config": predecessor_config.to_dict(),
                        "successor_config": successor_config.to_dict(),
                        "transition": transition.to_dict(),
                    },
                    idempotency_key=idempotency_key,
                )
            )
            ready.verify(transition, successor_config)
            if (
                ready.party_id != self.party_id
                or ready.runtime_package_digest != runtime_package.package_digest
            ):
                raise PartyProtocolError("lifecycle readiness package mismatch")
            return ready
        except (CertificateError, LifecycleCertificateError, _RequestError) as exc:
            raise PartyProtocolError("invalid remote lifecycle readiness") from exc

    def activate_successor_epoch(
        self,
        certificate: EpochActivationCertificate,
        predecessor_config: AuthorizerConfig,
        successor_config: AuthorizerConfig,
        *,
        idempotency_key: str | None = None,
    ) -> str:
        try:
            certificate.verify(predecessor_config, successor_config)
            result = _exact_dict(
                self._post(
                    "/v1/lifecycle/epoch-activations",
                    {
                        "certificate": certificate.to_dict(),
                        "predecessor_config": predecessor_config.to_dict(),
                        "successor_config": successor_config.to_dict(),
                    },
                    idempotency_key=idempotency_key,
                ),
                {"certificate_hash"},
                "epoch-activation response",
            )
            if result["certificate_hash"] != certificate.certificate_hash:
                raise PartyProtocolError("activation-certificate hash mismatch")
            return result["certificate_hash"]
        except (CertificateError, LifecycleCertificateError, _RequestError) as exc:
            raise PartyProtocolError("invalid remote epoch activation") from exc


class RemotePartyClient(RemoteAuthorizerNode):
    """Coordinator-side native TPASS client over the same pinned TLS channel."""

    def prepare_commitment(
        self,
        *,
        sid: str,
        authorization_certificate: AuthorizationCertificate,
        request: bytes,
        selected: list[int],
        idempotency_key: str | None = None,
    ) -> CommitmentResult:
        if authorization_certificate.prepare.entry.sid != sid:
            raise PartyProtocolError("authorization session mismatch")
        try:
            _hex_text(sid, "session identifier", bytes_length=32)
            result = _exact_dict(
                self._post(
                    f"/v1/recoveries/{sid}/commitments",
                    {
                        "authorization_certificate": authorization_certificate.to_dict(),
                        "request": _encode_base64url(request),
                        "selected": selected,
                    },
                    idempotency_key=idempotency_key,
                ),
                {"commitment", "phase_instance_id"},
                "commitment response",
            )
            return CommitmentResult(
                phase_instance_id=_hex_text(
                    result["phase_instance_id"],
                    "phase instance identifier",
                    bytes_length=32,
                ),
                commitment=_decode_base64url(result["commitment"], "party commitment"),
            )
        except _RequestError as exc:
            raise PartyProtocolError("invalid remote commitment response") from exc

    def respond(
        self,
        *,
        sid: str,
        phase_instance_id: str,
        request: bytes,
        selected: list[int],
        commitments: list[bytes],
        idempotency_key: str | None = None,
    ) -> bytes:
        try:
            _hex_text(sid, "session identifier", bytes_length=32)
            _hex_text(phase_instance_id, "phase instance identifier", bytes_length=32)
            result = _exact_dict(
                self._post(
                    f"/v1/recoveries/{sid}/responses",
                    {
                        "commitments": [
                            _encode_base64url(commitment) for commitment in commitments
                        ],
                        "phase_instance_id": phase_instance_id,
                        "request": _encode_base64url(request),
                        "selected": selected,
                    },
                    idempotency_key=idempotency_key,
                ),
                {"response"},
                "party response",
            )
            return _decode_base64url(result["response"], "party response")
        except _RequestError as exc:
            raise PartyProtocolError("invalid remote party response") from exc


def _load_server(path: str | Path) -> tuple[PartyHttpServer, PartyStore]:
    encoded_config = Path(path).read_bytes()
    if not encoded_config or len(encoded_config) > MAX_MESSAGE_BYTES:
        raise _RequestError("invalid party service configuration size")
    raw = _decode_json(encoded_config)
    config_file = _exact_dict(
        raw,
        {
            "authorizer_config",
            "budget",
            "listen_host",
            "listen_port",
            "native_party",
            "party_id",
            "signer_private_key",
            "store_path",
            "tls",
            "version",
        },
        "party service configuration",
    )
    if config_file["version"] != "LOCUS-party-service-config-v1":
        raise _RequestError("unsupported party service configuration")
    tls = _exact_dict(
        config_file["tls"],
        {
            "certificate",
            "client_identities",
            "client_ca",
            "private_key",
        },
        "TLS configuration",
    )
    encoded_identities = tls["client_identities"]
    if not isinstance(encoded_identities, list) or not encoded_identities:
        raise _RequestError("invalid client identities")
    client_identities: dict[str, str] = {}
    for encoded_identity in encoded_identities:
        identity = _exact_dict(
            encoded_identity,
            {"certificate_sha256", "role"},
            "client identity",
        )
        fingerprint = identity["certificate_sha256"]
        role = identity["role"]
        if not isinstance(fingerprint, str) or not isinstance(role, str):
            raise _RequestError("invalid client identity")
        if fingerprint in client_identities:
            raise _RequestError("duplicate client identity")
        client_identities[fingerprint] = role
    config = AuthorizerConfig.from_dict(config_file["authorizer_config"])
    signer = AuthorizerSigner.from_private_key_hex(
        config_file["party_id"], config_file["signer_private_key"]
    )
    store = PartyStore(config_file["store_path"])
    try:
        store.enroll_epoch(
            EpochConfig(
                bid=config.bid,
                epoch=config.epoch,
                party_id=signer.party_id,
                config_digest=config.digest,
                backup_digest=config.backup_digest,
                budget=config_file["budget"],
            )
        )
        parameters_bytes: bytes | None = None
        party_state_bytes: bytes | None = None
        peer_nodes: list[AuthorizerPeer] = []
        encoded_native = config_file["native_party"]
        if encoded_native is not None:
            native_config = _exact_dict(
                encoded_native,
                {"outbound_tls", "parameters", "peers", "state"},
                "native party configuration",
            )
            outbound_tls = _exact_dict(
                native_config["outbound_tls"],
                {"client_certificate", "client_private_key", "server_ca"},
                "outbound TLS configuration",
            )
            outbound_fingerprint = certificate_sha256(
                outbound_tls["client_certificate"]
            )
            if (
                client_identities.get(outbound_fingerprint)
                != f"party:{signer.party_id}"
            ):
                raise CertificateError("outbound identity does not match party")
            if not isinstance(native_config["peers"], list):
                raise _RequestError("invalid authorizer peers")
            peer_ids: list[int] = []
            for encoded_peer in native_config["peers"]:
                peer = _exact_dict(
                    encoded_peer,
                    {
                        "host",
                        "party_id",
                        "port",
                        "server_certificate_sha256",
                        "timeout_seconds",
                    },
                    "authorizer peer",
                )
                peer_id = peer["party_id"]
                if isinstance(peer_id, bool) or not isinstance(peer_id, int):
                    raise _RequestError("invalid authorizer peer identifier")
                peer_ids.append(peer_id)
                peer_nodes.append(
                    RemoteAuthorizerNode(
                        party_id=peer_id,
                        host=peer["host"],
                        port=peer["port"],
                        server_ca=outbound_tls["server_ca"],
                        client_certificate=outbound_tls["client_certificate"],
                        client_private_key=outbound_tls["client_private_key"],
                        server_certificate_sha256=peer["server_certificate_sha256"],
                        timeout_seconds=peer["timeout_seconds"],
                    )
                )
            expected_peer_ids = sorted(set(config.public_keys) - {signer.party_id})
            if peer_ids != expected_peer_ids:
                raise _RequestError("noncanonical authorizer peer set")
            parameters_bytes = _decode_base64url(
                native_config["parameters"], "public parameters"
            )
            party_state_bytes = _decode_base64url(native_config["state"], "party state")
            parameters = native.PublicParameters.from_bytes(parameters_bytes)
            state = native.PartyState.from_secret_bytes(party_state_bytes)
            if state.party_id != signer.party_id:
                raise CertificateError("TPASS state belongs to another party")
            if state.party_id > parameters.parties:
                raise CertificateError("TPASS state exceeds configured parties")
        initial_epoch = EpochConfig(
            bid=config.bid,
            epoch=config.epoch,
            party_id=signer.party_id,
            config_digest=config.digest,
            backup_digest=config.backup_digest,
            budget=config_file["budget"],
        )
        store.register_initial_runtime_package(
            initial_epoch,
            config,
            parameters=parameters_bytes,
            party_state=party_state_bytes,
        )
        store.mark_open_phases_lost()
        context = PartyServerContext(
            store=store,
            signer=signer,
            boot_config=config,
            client_identities=client_identities,
            peer_nodes=tuple(peer_nodes),
            native_role=encoded_native is not None,
        )
        server = PartyHttpServer(
            (config_file["listen_host"], config_file["listen_port"]),
            context=context,
            certificate=tls["certificate"],
            private_key=tls["private_key"],
            client_ca=tls["client_ca"],
        )
    except BaseException:
        store.close()
        raise
    return server, store


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one LOCUS authorizer service")
    parser.add_argument("--config", required=True, help="strict JSON service config")
    args = parser.parse_args()
    server, store = _load_server(args.config)
    try:
        server.serve_forever(poll_interval=0.1)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        store.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
