"""Durable per-holder aPPSS protocol service used by P5A.3/P5A.4."""

from __future__ import annotations

import hashlib
import sqlite3
import threading
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import _tpass_native as native
from .appss_formats import (
    APPSS_PROFILE_2_OF_3,
    APPSS_SUITE_ID,
    MAX_INSTALL_BYTES,
    MAX_PARTY_STATE_BYTES,
    MAX_PENDING_STATE_BYTES,
    MAX_PUBLIC_STATE_BYTES,
    MAX_READY_BYTES,
    MAX_REQUEST_BYTES,
    MAX_RESPONSE_BYTES,
    AppssFormatError,
    appss_format,
    appss_topology,
    canonical_decode,
    encode_checked,
    validate_install,
    validate_party_state,
    validate_public_state,
    validate_ready,
    validate_request,
    validate_response,
)


class AppssPartyError(ValueError):
    """A party state transition or protocol binding failed."""


@dataclass(frozen=True)
class AppssPartyBinding:
    holder_id: int
    context_digest: bytes
    profile_id: str = APPSS_PROFILE_2_OF_3

    def __post_init__(self) -> None:
        try:
            _k, parties = appss_topology(self.profile_id)
        except AppssFormatError as exc:
            raise AppssPartyError("invalid aPPSS party binding") from exc
        if not 1 <= self.holder_id <= parties or len(self.context_digest) != 32:
            raise AppssPartyError("invalid aPPSS party binding")


class AppssPartyStore:
    """One local durable database containing at most one holder's OPRF key."""

    def __init__(self, path: str | Path, binding: AppssPartyBinding) -> None:
        self.path = Path(path)
        self.binding = binding
        self._lock = threading.RLock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=5.0, isolation_level=None)
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=FULL")
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def _initialize(self) -> None:
        with closing(self._connect()) as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS appss_epoch_state (
                    singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
                    context_digest BLOB NOT NULL CHECK (length(context_digest) = 32),
                    holder_id INTEGER NOT NULL,
                    phase TEXT NOT NULL CHECK (phase IN ('pending', 'installed', 'retired')),
                    state_bytes BLOB NOT NULL,
                    public_state_bytes BLOB,
                    operation_id TEXT NOT NULL,
                    install_digest BLOB
                );
                CREATE TABLE IF NOT EXISTS appss_requests (
                    operation TEXT NOT NULL,
                    operation_id TEXT NOT NULL,
                    holder_id INTEGER NOT NULL,
                    request_digest BLOB NOT NULL CHECK (length(request_digest) = 32),
                    request_bytes BLOB NOT NULL,
                    authorization_digest BLOB NOT NULL CHECK (length(authorization_digest) = 32),
                    response_bytes BLOB,
                    PRIMARY KEY (operation, operation_id, holder_id)
                );
                CREATE TABLE IF NOT EXISTS appss_http_requests (
                    idempotency_key TEXT PRIMARY KEY,
                    caller_digest BLOB NOT NULL CHECK (length(caller_digest) = 32),
                    route TEXT NOT NULL,
                    request_digest BLOB NOT NULL CHECK (length(request_digest) = 32),
                    phase TEXT NOT NULL CHECK (
                        phase IN ('in_progress', 'retryable', 'completed')
                    ),
                    status INTEGER,
                    response_bytes BLOB
                );
                """
            )
            connection.execute(
                "UPDATE appss_http_requests SET phase = 'retryable' "
                "WHERE phase = 'in_progress'"
            )

    def load_state(self) -> tuple[str, bytes, bytes | None, str] | None:
        with self._lock, closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT phase, state_bytes, public_state_bytes, operation_id "
                "FROM appss_epoch_state WHERE singleton = 1"
            ).fetchone()
        if row is None:
            return None
        phase, state, public, operation_id = row
        return (
            str(phase),
            bytes(state),
            None if public is None else bytes(public),
            str(operation_id),
        )

    def create_pending(self, *, operation_id: str) -> native.AppssServerKey:
        _hex(operation_id, "operation identifier", 32)
        with self._lock:
            current = self.load_state()
            if current is not None:
                phase, state_bytes, _, stored_operation = current
                if phase == "pending" and stored_operation == operation_id:
                    decoded = _decode_party_state(state_bytes, pending=True)
                    return _native_key(decoded)
                raise AppssPartyError("aPPSS epoch state already exists")
            key = native.appss_generate_server_key(
                self.binding.context_digest, self.binding.holder_id
            )
            secret = key.to_secret_bytes()
            mapping = {
                "context_digest": self.binding.context_digest.hex(),
                "holder_id": self.binding.holder_id,
                "key_commitment": key.commitment().hex(),
                "oprf_key": secret[39:71].hex(),
                "profile_id": self.binding.profile_id,
                "suite_id": APPSS_SUITE_ID,
                "version": appss_format(self.binding.profile_id, "pending"),
            }
            state_bytes = encode_checked(
                mapping,
                maximum=MAX_PENDING_STATE_BYTES,
                validator=lambda value: validate_party_state(value, pending=True),
                label="pending aPPSS party state",
            )
            with closing(self._connect()) as connection:
                connection.execute("BEGIN IMMEDIATE")
                connection.execute(
                    "INSERT INTO appss_epoch_state "
                    "(singleton, context_digest, holder_id, phase, state_bytes, "
                    "public_state_bytes, operation_id, install_digest) "
                    "VALUES (1, ?, ?, 'pending', ?, NULL, ?, NULL)",
                    (
                        self.binding.context_digest,
                        self.binding.holder_id,
                        state_bytes,
                        operation_id,
                    ),
                )
                connection.commit()
            return key

    def install(
        self,
        *,
        operation_id: str,
        install_digest: bytes,
        public_state_bytes: bytes,
    ) -> bytes:
        if len(install_digest) != 32:
            raise AppssPartyError("invalid aPPSS install digest")
        with self._lock:
            current = self.load_state()
            if current is None:
                raise AppssPartyError("aPPSS pending state is missing")
            phase, state_bytes, existing_public, stored_operation = current
            if stored_operation != operation_id:
                raise AppssPartyError("aPPSS install operation mismatch")
            if phase == "installed":
                with closing(self._connect()) as connection:
                    row = connection.execute(
                        "SELECT install_digest FROM appss_epoch_state "
                        "WHERE singleton = 1"
                    ).fetchone()
                if (
                    existing_public != public_state_bytes
                    or row is None
                    or row[0] is None
                    or bytes(row[0]) != install_digest
                ):
                    raise AppssPartyError("aPPSS install retry changed public state")
                return state_bytes
            if phase != "pending":
                raise AppssPartyError("aPPSS party state is not installable")
            pending = _decode_party_state(state_bytes, pending=True)
            public = _decode_public_state(public_state_bytes)
            if (
                public["context_digest"] != self.binding.context_digest.hex()
                or public["profile_id"] != self.binding.profile_id
            ):
                raise AppssPartyError("aPPSS install context mismatch")
            installed = {
                "context_digest": pending["context_digest"],
                "holder_id": pending["holder_id"],
                "key_commitment": pending["key_commitment"],
                "omega_digest": public["omega_digest"],
                "oprf_key": pending["oprf_key"],
                "profile_id": self.binding.profile_id,
                "public_state_digest": hashlib.sha256(public_state_bytes).hexdigest(),
                "suite_id": APPSS_SUITE_ID,
                "version": appss_format(self.binding.profile_id, "party"),
            }
            installed_bytes = encode_checked(
                installed,
                maximum=MAX_PARTY_STATE_BYTES,
                validator=validate_party_state,
                label="installed aPPSS party state",
            )
            with closing(self._connect()) as connection:
                connection.execute("BEGIN IMMEDIATE")
                updated = connection.execute(
                    "UPDATE appss_epoch_state SET phase = 'installed', "
                    "state_bytes = ?, public_state_bytes = ?, install_digest = ? "
                    "WHERE singleton = 1 AND phase = 'pending' AND operation_id = ?",
                    (
                        installed_bytes,
                        public_state_bytes,
                        install_digest,
                        operation_id,
                    ),
                ).rowcount
                if updated != 1:
                    connection.rollback()
                    raise AppssPartyError("aPPSS install state changed")
                connection.commit()
            return installed_bytes

    def retire(self) -> None:
        with self._lock, closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "UPDATE appss_epoch_state SET phase = 'retired', "
                "state_bytes = zeroblob(length(state_bytes)), public_state_bytes = NULL "
                "WHERE singleton = 1 AND phase = 'installed'"
            )
            connection.commit()

    def authorize_request(
        self,
        *,
        operation: str,
        operation_id: str,
        request_digest: bytes,
        request_bytes: bytes,
        authorization_digest: bytes,
    ) -> bytes | None:
        if len(request_digest) != 32 or len(authorization_digest) != 32:
            raise AppssPartyError("invalid aPPSS request authorization")
        with self._lock, closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT request_digest, request_bytes, authorization_digest, response_bytes "
                "FROM appss_requests WHERE operation = ? AND operation_id = ? "
                "AND holder_id = ?",
                (operation, operation_id, self.binding.holder_id),
            ).fetchone()
            if row is not None:
                stored_digest, stored_request, stored_authorization, response = row
                if (
                    bytes(stored_digest) != request_digest
                    or bytes(stored_request) != request_bytes
                    or bytes(stored_authorization) != authorization_digest
                ):
                    raise AppssPartyError("aPPSS idempotency binding changed")
                return None if response is None else bytes(response)
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "INSERT INTO appss_requests "
                "(operation, operation_id, holder_id, request_digest, request_bytes, "
                "authorization_digest, response_bytes) VALUES (?, ?, ?, ?, ?, ?, NULL)",
                (
                    operation,
                    operation_id,
                    self.binding.holder_id,
                    request_digest,
                    request_bytes,
                    authorization_digest,
                ),
            )
            connection.commit()
            return None

    def store_response(
        self, *, operation: str, operation_id: str, response_bytes: bytes
    ) -> bytes:
        with self._lock, closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT response_bytes FROM appss_requests WHERE operation = ? "
                "AND operation_id = ? AND holder_id = ?",
                (operation, operation_id, self.binding.holder_id),
            ).fetchone()
            if row is None:
                connection.rollback()
                raise AppssPartyError("aPPSS request was not authorized")
            existing = row[0]
            if existing is not None:
                connection.rollback()
                if bytes(existing) != response_bytes:
                    raise AppssPartyError("aPPSS response retry changed")
                return bytes(existing)
            connection.execute(
                "UPDATE appss_requests SET response_bytes = ? WHERE operation = ? "
                "AND operation_id = ? AND holder_id = ?",
                (response_bytes, operation, operation_id, self.binding.holder_id),
            )
            connection.commit()
            return response_bytes

    def claim_http_request(
        self,
        *,
        idempotency_key: str,
        caller_digest: bytes,
        route: str,
        request_digest: bytes,
    ) -> tuple[int, bytes] | None:
        """Durably bind caller, route, and body before protocol dispatch."""

        _hex(idempotency_key, "HTTP idempotency key", 32)
        if (
            len(caller_digest) != 32
            or len(request_digest) != 32
            or not route
            or len(route) > 255
            or not route.isascii()
        ):
            raise AppssPartyError("invalid aPPSS HTTP request binding")
        with self._lock, closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT caller_digest, route, request_digest, phase, status, "
                "response_bytes FROM appss_http_requests "
                "WHERE idempotency_key = ?",
                (idempotency_key,),
            ).fetchone()
            if row is not None:
                caller, stored_route, digest, phase, status, response = row
                if (
                    bytes(caller) != caller_digest
                    or str(stored_route) != route
                    or bytes(digest) != request_digest
                ):
                    raise AppssPartyError("aPPSS HTTP idempotency binding changed")
                if phase == "completed":
                    if status is None or response is None:
                        raise AppssPartyError("invalid completed aPPSS HTTP request")
                    return int(status), bytes(response)
                if phase == "in_progress":
                    raise AppssPartyError("aPPSS HTTP request is in progress")
                connection.execute("BEGIN IMMEDIATE")
                updated = connection.execute(
                    "UPDATE appss_http_requests SET phase = 'in_progress' "
                    "WHERE idempotency_key = ? AND phase = 'retryable'",
                    (idempotency_key,),
                ).rowcount
                if updated != 1:
                    connection.rollback()
                    raise AppssPartyError("aPPSS HTTP request state changed")
                connection.commit()
                return None
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "INSERT INTO appss_http_requests "
                "(idempotency_key, caller_digest, route, request_digest, phase, "
                "status, response_bytes) VALUES (?, ?, ?, ?, 'in_progress', NULL, NULL)",
                (idempotency_key, caller_digest, route, request_digest),
            )
            connection.commit()
            return None

    def complete_http_request(
        self, *, idempotency_key: str, status: int, response_bytes: bytes
    ) -> None:
        if (
            isinstance(status, bool)
            or not isinstance(status, int)
            or not 100 <= status <= 599
            or not isinstance(response_bytes, bytes)
            or not 0 < len(response_bytes) <= MAX_INSTALL_BYTES
        ):
            raise AppssPartyError("invalid aPPSS HTTP response")
        with self._lock, closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            updated = connection.execute(
                "UPDATE appss_http_requests SET phase = 'completed', status = ?, "
                "response_bytes = ? WHERE idempotency_key = ? "
                "AND phase = 'in_progress'",
                (status, response_bytes, idempotency_key),
            ).rowcount
            if updated != 1:
                connection.rollback()
                raise AppssPartyError("aPPSS HTTP request is not completable")
            connection.commit()


class AppssPartyService:
    """Bounded service logic with durable pre-evaluation authorization."""

    def __init__(self, store: AppssPartyStore) -> None:
        self.store = store
        self.binding = store.binding

    def evaluate(self, request_bytes: bytes) -> bytes:
        try:
            request = canonical_decode(
                request_bytes,
                maximum=MAX_REQUEST_BYTES,
                validator=validate_request,
                label="aPPSS request",
            )
        except AppssFormatError as exc:
            raise AppssPartyError("invalid aPPSS request") from exc
        if (
            request["context_digest"] != self.binding.context_digest.hex()
            or request["holder_id"] != self.binding.holder_id
            or request["profile_id"] != self.binding.profile_id
        ):
            raise AppssPartyError("aPPSS request recipient binding mismatch")
        operation = request["operation"]
        request_digest = hashlib.sha256(request_bytes).digest()
        authorization_digest = bytes.fromhex(request["admission_grant_digest"])
        prior = self.store.authorize_request(
            operation=operation,
            operation_id=request["operation_id"],
            request_digest=request_digest,
            request_bytes=request_bytes,
            authorization_digest=authorization_digest,
        )
        if prior is not None:
            return prior
        if operation == "initialize":
            key = self.store.create_pending(operation_id=request["operation_id"])
        else:
            current = self.store.load_state()
            if current is None or current[0] != "installed" or current[2] is None:
                raise AppssPartyError("aPPSS party is not ready")
            state = _decode_party_state(current[1], pending=False)
            if request["omega_digest"] != state["omega_digest"]:
                raise AppssPartyError("aPPSS request omega mismatch")
            key = _native_key(state)
        try:
            evaluated = native.appss_blind_evaluate(
                key,
                self.binding.context_digest,
                bytes.fromhex(request["blinded_element"]),
            )
        except native.NativeAppssError as exc:
            raise AppssPartyError("aPPSS evaluation rejected") from exc
        response = {
            "admission_grant_digest": request["admission_grant_digest"],
            "client_proof_key_digest": request["client_proof_key_digest"],
            "context_digest": request["context_digest"],
            "evaluated_element": evaluated.hex(),
            "holder_id": request["holder_id"],
            "key_commitment": key.commitment().hex(),
            "nonce": request["nonce"],
            "omega_digest": request["omega_digest"],
            "operation": operation,
            "operation_id": request["operation_id"],
            "profile_id": self.binding.profile_id,
            "request_digest": request_digest.hex(),
            "session_id": request["session_id"],
            "suite_id": APPSS_SUITE_ID,
            "version": appss_format(self.binding.profile_id, "response"),
        }
        response_bytes = encode_checked(
            response,
            maximum=MAX_RESPONSE_BYTES,
            validator=validate_response,
            label="aPPSS response",
        )
        return self.store.store_response(
            operation=operation,
            operation_id=request["operation_id"],
            response_bytes=response_bytes,
        )

    def install(self, install_bytes: bytes) -> bytes:
        try:
            install = canonical_decode(
                install_bytes,
                maximum=MAX_INSTALL_BYTES,
                validator=validate_install,
                label="aPPSS state install",
            )
        except AppssFormatError as exc:
            raise AppssPartyError("invalid aPPSS state install") from exc
        if (
            install["context_digest"] != self.binding.context_digest.hex()
            or install["holder_id"] != self.binding.holder_id
            or install["profile_id"] != self.binding.profile_id
        ):
            raise AppssPartyError("aPPSS install recipient binding mismatch")
        public_state_bytes = encode_checked(
            install["public_state"],
            maximum=MAX_PUBLIC_STATE_BYTES,
            validator=validate_public_state,
            label="aPPSS public state",
        )
        state_bytes = self.store.install(
            operation_id=install["operation_id"],
            install_digest=hashlib.sha256(install_bytes).digest(),
            public_state_bytes=public_state_bytes,
        )
        ready = {
            "context_digest": install["context_digest"],
            "holder_id": self.binding.holder_id,
            "operation_id": install["operation_id"],
            "party_state_digest": hashlib.sha256(state_bytes).hexdigest(),
            "profile_id": self.binding.profile_id,
            "public_state_digest": hashlib.sha256(public_state_bytes).hexdigest(),
            "suite_id": APPSS_SUITE_ID,
            "version": appss_format(self.binding.profile_id, "ready"),
        }
        return encode_checked(
            ready,
            maximum=MAX_READY_BYTES,
            validator=validate_ready,
            label="aPPSS ready acknowledgement",
        )


def _decode_party_state(encoded: bytes, *, pending: bool) -> dict[str, Any]:
    try:
        return canonical_decode(
            encoded,
            maximum=MAX_PENDING_STATE_BYTES if pending else MAX_PARTY_STATE_BYTES,
            validator=lambda value: validate_party_state(value, pending=pending),
            label="aPPSS party state",
        )
    except AppssFormatError as exc:
        raise AppssPartyError("invalid stored aPPSS party state") from exc


def _decode_public_state(encoded: bytes) -> dict[str, Any]:
    try:
        return canonical_decode(
            encoded,
            maximum=MAX_PUBLIC_STATE_BYTES,
            validator=validate_public_state,
            label="aPPSS public state",
        )
    except AppssFormatError as exc:
        raise AppssPartyError("invalid stored aPPSS public state") from exc


def _native_key(state: dict[str, Any]) -> native.AppssServerKey:
    encoded = (
        b"LAK1\x01"
        + int(state["holder_id"]).to_bytes(2, "big")
        + bytes.fromhex(state["context_digest"])
        + bytes.fromhex(state["oprf_key"])
    )
    try:
        key = native.AppssServerKey.from_secret_bytes(encoded)
    except native.NativeAppssError as exc:
        raise AppssPartyError("invalid stored aPPSS OPRF key") from exc
    if key.commitment().hex() != state["key_commitment"]:
        raise AppssPartyError("stored aPPSS key commitment mismatch")
    return key


def _hex(value: object, label: str, length: int) -> str:
    if (
        not isinstance(value, str)
        or len(value) != length * 2
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise AppssPartyError(f"invalid {label}")
    return value


__all__ = [
    "AppssPartyBinding",
    "AppssPartyError",
    "AppssPartyService",
    "AppssPartyStore",
]
