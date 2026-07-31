"""Durable per-party state for the first LOCUS service vertical slice.

This module enforces local ordering and idempotency around verified attempt and
backup-epoch lifecycle certificates. Distributed rollback detection and the
complete attempt-bound argument belong to later P5 layers and are not implied.
"""

from __future__ import annotations

import json
import secrets
import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .attempt_certificates import (
    AttemptEntry,
    AuthorizationCertificate,
    AuthorizerConfig,
    AuthorizerSigner,
    EntryVote,
    FreshnessRequest,
    FreshnessVote,
    InstallVote,
    PrepareCertificate,
)
from .codec import encode
from .crypto import hash_bytes
from .epoch_lifecycle import (
    EpochActivationCertificate,
    EpochApproval,
    EpochReady,
    EpochTransition,
    LifecycleCertificateError,
    RuntimeEpochPackage,
)

SCHEMA_VERSION = 5
GENESIS_HEAD = "0" * 64
HEX_DIGEST_LENGTH = 64
MAX_IDEMPOTENCY_RESPONSE_BYTES = 1_048_576
MAX_RUNTIME_COMPONENT_BYTES = 262_144


class PartyStoreError(Exception):
    """Base error for durable party-state failures."""


class InvalidState(PartyStoreError):
    """The requested transition is invalid for the durable state."""


class Conflict(PartyStoreError):
    """An idempotency identifier or ledger slot was reused inconsistently."""


class BudgetExhausted(PartyStoreError):
    """The configured attempt budget has been consumed."""


class SessionLost(PartyStoreError):
    """A volatile TPASS phase cannot be resumed safely after interruption."""


class RequestInProgress(PartyStoreError):
    """An exact HTTP retry arrived while its original request was executing."""


def _exact_int(value: object, label: str, *, minimum: int = 1) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < minimum
        or value > 2**63 - 1
    ):
        raise InvalidState(f"invalid {label}")
    return value


def _hex(value: object, label: str, *, bytes_length: int) -> str:
    if (
        not isinstance(value, str)
        or len(value) != bytes_length * 2
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise InvalidState(f"invalid {label}")
    return value


@dataclass(frozen=True)
class EpochConfig:
    """Locally installed genesis state for one backup epoch."""

    bid: str
    epoch: int
    party_id: int
    config_digest: str
    backup_digest: str
    budget: int
    genesis_head: str = GENESIS_HEAD

    def validate(self) -> None:
        _hex(self.bid, "backup identifier", bytes_length=16)
        _exact_int(self.epoch, "epoch")
        party_id = _exact_int(self.party_id, "party identifier")
        if party_id > 255:
            raise InvalidState("invalid party identifier")
        _hex(self.config_digest, "configuration digest", bytes_length=32)
        _hex(self.backup_digest, "backup digest", bytes_length=32)
        _exact_int(self.budget, "attempt budget")
        _hex(self.genesis_head, "genesis head", bytes_length=32)


@dataclass(frozen=True)
class AttemptAuthorization:
    """Fields extracted from an already-verified authorization certificate.

    The coordinator constructs this object only after checking the distributed
    quorum signatures. The store deliberately does not treat this data class as
    a certificate or perform signature verification itself.
    """

    bid: str
    epoch: int
    config_digest: str
    log_index: int
    previous_head: str
    sid: str
    request_digest: str
    tpass_request_hash: str
    resulting_consumed: int
    effective_budget: int
    certificate_hash: str

    @classmethod
    def from_dict(cls, value: object) -> AttemptAuthorization:
        if not isinstance(value, dict):
            raise InvalidState("invalid attempt authorization")
        expected = {
            "bid",
            "epoch",
            "config_digest",
            "log_index",
            "previous_head",
            "sid",
            "request_digest",
            "tpass_request_hash",
            "resulting_consumed",
            "effective_budget",
            "certificate_hash",
        }
        if set(value) != expected:
            raise InvalidState("invalid attempt authorization")
        authorization = cls(**value)
        authorization.validate()
        return authorization

    def validate(self) -> None:
        _hex(self.bid, "backup identifier", bytes_length=16)
        _exact_int(self.epoch, "epoch")
        _hex(self.config_digest, "configuration digest", bytes_length=32)
        _exact_int(self.log_index, "log index")
        _hex(self.previous_head, "previous head", bytes_length=32)
        _hex(self.sid, "session identifier", bytes_length=32)
        _hex(self.request_digest, "request digest", bytes_length=32)
        _hex(self.tpass_request_hash, "TPASS request hash", bytes_length=32)
        _exact_int(self.resulting_consumed, "resulting consumed count")
        _exact_int(self.effective_budget, "effective budget")
        _hex(self.certificate_hash, "certificate hash", bytes_length=32)

    def entry_hash(self) -> str:
        value = {
            "bid": self.bid,
            "config_digest": self.config_digest,
            "effective_budget": self.effective_budget,
            "epoch": self.epoch,
            "log_index": self.log_index,
            "previous_head": self.previous_head,
            "request_digest": self.request_digest,
            "resulting_consumed": self.resulting_consumed,
            "sid": self.sid,
            "tpass_request_hash": self.tpass_request_hash,
            "type": "ATTEMPT",
            "version": "LOCUS-attempt-entry-v1",
        }
        return hash_bytes("LOCUS/attempt-entry/v1", encode(value)).hex()

    def to_dict(self) -> dict[str, Any]:
        return {
            "bid": self.bid,
            "epoch": self.epoch,
            "config_digest": self.config_digest,
            "log_index": self.log_index,
            "previous_head": self.previous_head,
            "sid": self.sid,
            "request_digest": self.request_digest,
            "tpass_request_hash": self.tpass_request_hash,
            "resulting_consumed": self.resulting_consumed,
            "effective_budget": self.effective_budget,
            "certificate_hash": self.certificate_hash,
        }


@dataclass(frozen=True)
class PhaseReservation:
    phase_instance_id: str
    state: str
    commitment: bytes | None
    response: bytes | None


@dataclass(frozen=True)
class HttpIdempotencyReservation:
    """Whether an HTTP request must execute or has an exact stored result."""

    state: str
    response_status: int | None = None
    response_body: bytes | None = None


@dataclass(frozen=True)
class RuntimeEpochPackageRecord:
    """One party's private, epoch-bound runtime material."""

    descriptor: RuntimeEpochPackage
    authorizer_config: AuthorizerConfig
    parameters: bytes | None
    party_state: bytes | None
    state: str


class PartyStore:
    """SQLite-backed local ledger and TPASS-phase idempotency state."""

    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        self._lock = threading.RLock()
        self._connection = sqlite3.connect(
            self.path,
            isolation_level=None,
            check_same_thread=False,
        )
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._connection.execute("PRAGMA journal_mode = WAL")
        self._connection.execute("PRAGMA synchronous = FULL")
        self._create_schema()

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    @contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        with self._lock:
            self._connection.execute("BEGIN IMMEDIATE")
            try:
                yield self._connection
            except BaseException:
                self._connection.execute("ROLLBACK")
                raise
            else:
                self._connection.execute("COMMIT")

    def _create_schema(self) -> None:
        with self._lock:
            self._connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS epochs (
                    bid TEXT NOT NULL,
                    epoch INTEGER NOT NULL,
                    party_id INTEGER NOT NULL,
                    config_digest TEXT NOT NULL,
                    backup_digest TEXT NOT NULL,
                    budget INTEGER NOT NULL CHECK (budget > 0),
                    consumed INTEGER NOT NULL CHECK (consumed >= 0),
                    installed_index INTEGER NOT NULL CHECK (installed_index >= 0),
                    installed_head TEXT NOT NULL,
                    status TEXT NOT NULL CHECK (status IN ('ACTIVE', 'RETIRED', 'FAILED_CLOSED')),
                    PRIMARY KEY (bid, epoch)
                );
                CREATE TABLE IF NOT EXISTS attempts (
                    bid TEXT NOT NULL,
                    epoch INTEGER NOT NULL,
                    sid TEXT NOT NULL,
                    request_digest TEXT NOT NULL,
                    tpass_request_hash TEXT NOT NULL,
                    log_index INTEGER NOT NULL,
                    previous_head TEXT NOT NULL,
                    entry_hash TEXT NOT NULL,
                    certificate_hash TEXT NOT NULL,
                    resulting_consumed INTEGER NOT NULL,
                    effective_budget INTEGER NOT NULL,
                    PRIMARY KEY (bid, epoch, sid),
                    UNIQUE (bid, epoch, log_index),
                    FOREIGN KEY (bid, epoch) REFERENCES epochs (bid, epoch)
                );
                CREATE TABLE IF NOT EXISTS phases (
                    bid TEXT NOT NULL,
                    epoch INTEGER NOT NULL,
                    sid TEXT NOT NULL,
                    party_id INTEGER NOT NULL,
                    phase_instance_id TEXT NOT NULL,
                    selected_digest TEXT NOT NULL,
                    freshness_digest TEXT NOT NULL,
                    state TEXT NOT NULL CHECK (state IN ('INTENT', 'COMMITMENT_STORED', 'RESPONDED', 'LOST')),
                    commitment BLOB,
                    response BLOB,
                    PRIMARY KEY (bid, epoch, sid, party_id),
                    UNIQUE (phase_instance_id),
                    FOREIGN KEY (bid, epoch, sid) REFERENCES attempts (bid, epoch, sid)
                );
                CREATE TABLE IF NOT EXISTS slot_locks (
                    bid TEXT NOT NULL,
                    epoch INTEGER NOT NULL,
                    log_index INTEGER NOT NULL,
                    sid TEXT NOT NULL,
                    entry_hash TEXT NOT NULL,
                    entry_bytes BLOB NOT NULL,
                    entry_vote_bytes BLOB,
                    prepare_hash TEXT,
                    prepare_bytes BLOB,
                    install_vote_bytes BLOB,
                    authorization_bytes BLOB,
                    state TEXT NOT NULL CHECK (state IN ('VOTED', 'PREPARED', 'INSTALL_VOTED', 'INSTALLED')),
                    PRIMARY KEY (bid, epoch, log_index),
                    UNIQUE (bid, epoch, sid),
                    FOREIGN KEY (bid, epoch) REFERENCES epochs (bid, epoch)
                );
                CREATE TABLE IF NOT EXISTS freshness_votes (
                    freshness_request_hash TEXT NOT NULL,
                    authorizer_id INTEGER NOT NULL,
                    request_bytes BLOB NOT NULL,
                    vote_bytes BLOB NOT NULL,
                    PRIMARY KEY (freshness_request_hash, authorizer_id)
                );
                CREATE TABLE IF NOT EXISTS epoch_transition_locks (
                    bid TEXT NOT NULL,
                    predecessor_epoch INTEGER NOT NULL,
                    transition_hash TEXT NOT NULL,
                    transition_bytes BLOB NOT NULL,
                    approval_bytes BLOB,
                    PRIMARY KEY (bid, predecessor_epoch),
                    FOREIGN KEY (bid, predecessor_epoch)
                        REFERENCES epochs (bid, epoch)
                );
                CREATE TABLE IF NOT EXISTS epoch_preparations (
                    bid TEXT NOT NULL,
                    successor_epoch INTEGER NOT NULL,
                    predecessor_epoch INTEGER NOT NULL,
                    party_id INTEGER NOT NULL,
                    transition_hash TEXT NOT NULL,
                    config_digest TEXT NOT NULL,
                    backup_digest TEXT NOT NULL,
                    budget INTEGER NOT NULL CHECK (budget > 0),
                    readiness_bytes BLOB NOT NULL,
                    state TEXT NOT NULL CHECK (state IN ('PREPARED', 'ACTIVATED')),
                    activation_certificate_hash TEXT,
                    PRIMARY KEY (bid, successor_epoch),
                    FOREIGN KEY (bid, predecessor_epoch)
                        REFERENCES epochs (bid, epoch),
                    CHECK (
                        (state = 'PREPARED' AND activation_certificate_hash IS NULL)
                        OR
                        (state = 'ACTIVATED'
                         AND activation_certificate_hash IS NOT NULL)
                    )
                );
                CREATE TABLE IF NOT EXISTS epoch_runtime_packages (
                    bid TEXT NOT NULL,
                    epoch INTEGER NOT NULL,
                    party_id INTEGER NOT NULL,
                    package_digest TEXT NOT NULL,
                    descriptor_bytes BLOB NOT NULL,
                    authorizer_config_bytes BLOB NOT NULL,
                    parameters_bytes BLOB,
                    party_state_bytes BLOB,
                    state TEXT NOT NULL CHECK (
                        state IN ('PREPARED', 'ACTIVE', 'RETIRED')
                    ),
                    PRIMARY KEY (bid, epoch),
                    CHECK (
                        (parameters_bytes IS NULL AND party_state_bytes IS NULL)
                        OR
                        (parameters_bytes IS NOT NULL AND party_state_bytes IS NOT NULL)
                    )
                );
                CREATE TABLE IF NOT EXISTS http_idempotency (
                    idempotency_key TEXT PRIMARY KEY,
                    caller_fingerprint TEXT NOT NULL,
                    method TEXT NOT NULL,
                    route TEXT NOT NULL,
                    request_digest TEXT NOT NULL,
                    owner_boot_nonce TEXT NOT NULL,
                    state TEXT NOT NULL CHECK (
                        state IN ('STARTED', 'RETRYABLE', 'COMPLETE')
                    ),
                    response_status INTEGER,
                    response_body BLOB,
                    CHECK (
                        (state = 'COMPLETE'
                         AND response_status BETWEEN 100 AND 599
                         AND response_body IS NOT NULL)
                        OR
                        (state != 'COMPLETE'
                         AND response_status IS NULL
                         AND response_body IS NULL)
                    )
                );
                CREATE TABLE IF NOT EXISTS audit_events (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    bid TEXT NOT NULL,
                    epoch INTEGER NOT NULL,
                    subject_digest TEXT NOT NULL,
                    previous_event_hash TEXT NOT NULL,
                    event_hash TEXT NOT NULL
                );
                """
            )
        with self._transaction() as connection:
            row = connection.execute(
                "SELECT value FROM metadata WHERE key = 'schema_version'"
            ).fetchone()
            if row is None:
                connection.execute(
                    "INSERT INTO metadata(key, value) VALUES('schema_version', ?)",
                    (str(SCHEMA_VERSION),),
                )
            elif row["value"] in {"2", "3", "4"}:
                connection.execute(
                    "UPDATE metadata SET value = ? WHERE key = 'schema_version'",
                    (str(SCHEMA_VERSION),),
                )
            elif row["value"] != str(SCHEMA_VERSION):
                raise InvalidState("unsupported party database schema")

    @staticmethod
    def _validate_http_binding(
        *,
        idempotency_key: str,
        caller_fingerprint: str,
        method: str,
        route: str,
        request_digest: str,
        owner_boot_nonce: str,
    ) -> None:
        _hex(idempotency_key, "idempotency key", bytes_length=32)
        _hex(caller_fingerprint, "caller fingerprint", bytes_length=32)
        _hex(request_digest, "HTTP request digest", bytes_length=32)
        _hex(owner_boot_nonce, "HTTP boot nonce", bytes_length=32)
        if method != "POST":
            raise InvalidState("invalid idempotent HTTP method")
        if (
            not isinstance(route, str)
            or not route.startswith("/")
            or len(route) > 2048
            or any(
                ord(character) < 0x21 or ord(character) > 0x7E for character in route
            )
        ):
            raise InvalidState("invalid idempotent HTTP route")

    def begin_http_request(
        self,
        *,
        idempotency_key: str,
        caller_fingerprint: str,
        method: str,
        route: str,
        request_digest: str,
        owner_boot_nonce: str,
    ) -> HttpIdempotencyReservation:
        """Durably bind a mutating request before dispatching it.

        The store is owned by one party process. A fresh process first calls
        ``recover_http_requests`` so only a request from the same live boot can
        remain in ``STARTED`` state.
        """

        self._validate_http_binding(
            idempotency_key=idempotency_key,
            caller_fingerprint=caller_fingerprint,
            method=method,
            route=route,
            request_digest=request_digest,
            owner_boot_nonce=owner_boot_nonce,
        )
        expected = (caller_fingerprint, method, route, request_digest)
        with self._transaction() as connection:
            row = connection.execute(
                "SELECT * FROM http_idempotency WHERE idempotency_key = ?",
                (idempotency_key,),
            ).fetchone()
            if row is None:
                connection.execute(
                    """INSERT INTO http_idempotency(
                           idempotency_key, caller_fingerprint, method, route,
                           request_digest, owner_boot_nonce, state,
                           response_status, response_body
                       ) VALUES (?, ?, ?, ?, ?, ?, 'STARTED', NULL, NULL)""",
                    (
                        idempotency_key,
                        caller_fingerprint,
                        method,
                        route,
                        request_digest,
                        owner_boot_nonce,
                    ),
                )
                return HttpIdempotencyReservation(state="EXECUTE")
            actual = (
                row["caller_fingerprint"],
                row["method"],
                row["route"],
                row["request_digest"],
            )
            if actual != expected:
                raise Conflict("idempotency key was reused with another request")
            if row["state"] == "COMPLETE":
                return HttpIdempotencyReservation(
                    state="COMPLETE",
                    response_status=row["response_status"],
                    response_body=bytes(row["response_body"]),
                )
            if row["state"] == "STARTED":
                raise RequestInProgress("idempotent request is still executing")
            connection.execute(
                """UPDATE http_idempotency
                   SET owner_boot_nonce = ?, state = 'STARTED'
                   WHERE idempotency_key = ?""",
                (owner_boot_nonce, idempotency_key),
            )
            return HttpIdempotencyReservation(state="EXECUTE")

    def complete_http_request(
        self,
        *,
        idempotency_key: str,
        owner_boot_nonce: str,
        response_status: int,
        response_body: bytes,
    ) -> None:
        """Store exact response bytes before they are released to the caller."""

        _hex(idempotency_key, "idempotency key", bytes_length=32)
        _hex(owner_boot_nonce, "HTTP boot nonce", bytes_length=32)
        if (
            isinstance(response_status, bool)
            or not isinstance(response_status, int)
            or not 100 <= response_status <= 599
        ):
            raise InvalidState("invalid HTTP response status")
        if (
            not isinstance(response_body, bytes)
            or not response_body
            or len(response_body) > MAX_IDEMPOTENCY_RESPONSE_BYTES
        ):
            raise InvalidState("invalid HTTP response body")
        with self._transaction() as connection:
            row = connection.execute(
                "SELECT * FROM http_idempotency WHERE idempotency_key = ?",
                (idempotency_key,),
            ).fetchone()
            if row is None or row["owner_boot_nonce"] != owner_boot_nonce:
                raise Conflict("HTTP request ownership changed")
            if row["state"] == "COMPLETE":
                if (
                    row["response_status"] != response_status
                    or bytes(row["response_body"]) != response_body
                ):
                    raise Conflict("completed HTTP result changed")
                return
            if row["state"] != "STARTED":
                raise InvalidState("HTTP request is not executing")
            connection.execute(
                """UPDATE http_idempotency
                   SET state = 'COMPLETE', response_status = ?, response_body = ?
                   WHERE idempotency_key = ?""",
                (response_status, response_body, idempotency_key),
            )

    def retry_http_request(
        self, *, idempotency_key: str, owner_boot_nonce: str
    ) -> None:
        """Permit an exact retry after a transient pre-response failure."""

        _hex(idempotency_key, "idempotency key", bytes_length=32)
        _hex(owner_boot_nonce, "HTTP boot nonce", bytes_length=32)
        with self._transaction() as connection:
            row = connection.execute(
                "SELECT state, owner_boot_nonce FROM http_idempotency "
                "WHERE idempotency_key = ?",
                (idempotency_key,),
            ).fetchone()
            if row is None or row["owner_boot_nonce"] != owner_boot_nonce:
                raise Conflict("HTTP request ownership changed")
            if row["state"] == "COMPLETE":
                return
            if row["state"] != "STARTED":
                raise InvalidState("HTTP request is not executing")
            connection.execute(
                """UPDATE http_idempotency
                   SET state = 'RETRYABLE'
                   WHERE idempotency_key = ?""",
                (idempotency_key,),
            )

    def recover_http_requests(self) -> int:
        """Make requests interrupted by a prior exclusive server boot retryable."""

        with self._transaction() as connection:
            cursor = connection.execute(
                """UPDATE http_idempotency
                   SET state = 'RETRYABLE'
                   WHERE state = 'STARTED'"""
            )
            return cursor.rowcount

    def _append_audit(
        self,
        connection: sqlite3.Connection,
        event_type: str,
        bid: str,
        epoch: int,
        subject_digest: str,
    ) -> None:
        row = connection.execute(
            "SELECT event_hash FROM audit_events ORDER BY sequence DESC LIMIT 1"
        ).fetchone()
        previous_hash = GENESIS_HEAD if row is None else row["event_hash"]
        event_hash = hash_bytes(
            "LOCUS/audit-event/v1",
            encode(
                {
                    "bid": bid,
                    "epoch": epoch,
                    "event_type": event_type,
                    "previous_event_hash": previous_hash,
                    "subject_digest": subject_digest,
                }
            ),
        ).hex()
        connection.execute(
            """INSERT INTO audit_events(
                   event_type, bid, epoch, subject_digest,
                   previous_event_hash, event_hash
               ) VALUES (?, ?, ?, ?, ?, ?)""",
            (event_type, bid, epoch, subject_digest, previous_hash, event_hash),
        )

    def enroll_epoch(self, config: EpochConfig) -> None:
        """Install only a backup's first genesis epoch.

        Successor epochs must use the certified prepare/activate transition below;
        direct insertion would silently reset the per-epoch attempt budget.
        """

        config.validate()
        with self._transaction() as connection:
            existing = connection.execute(
                "SELECT * FROM epochs WHERE bid = ? AND epoch = ?",
                (config.bid, config.epoch),
            ).fetchone()
            expected = (
                config.party_id,
                config.config_digest,
                config.backup_digest,
                config.budget,
            )
            if existing is not None:
                actual = (
                    existing["party_id"],
                    existing["config_digest"],
                    existing["backup_digest"],
                    existing["budget"],
                )
                if actual != expected or (
                    existing["installed_index"] == 0
                    and existing["installed_head"] != config.genesis_head
                ):
                    raise Conflict("conflicting epoch enrollment")
                return
            prior = connection.execute(
                "SELECT epoch FROM epochs WHERE bid = ? ORDER BY epoch DESC LIMIT 1",
                (config.bid,),
            ).fetchone()
            if config.epoch != 1 or prior is not None:
                raise InvalidState("successor epoch requires certified activation")
            connection.execute(
                """INSERT INTO epochs(
                       bid, epoch, party_id, config_digest, backup_digest, budget, consumed,
                       installed_index, installed_head, status
                   ) VALUES (?, ?, ?, ?, ?, ?, 0, 0, ?, 'ACTIVE')""",
                (
                    config.bid,
                    config.epoch,
                    config.party_id,
                    config.config_digest,
                    config.backup_digest,
                    config.budget,
                    config.genesis_head,
                ),
            )
            self._append_audit(
                connection,
                "EPOCH_ENROLLED",
                config.bid,
                config.epoch,
                config.config_digest,
            )

    @staticmethod
    def _validate_runtime_components(
        parameters: bytes | None, party_state: bytes | None
    ) -> None:
        if (parameters is None) != (party_state is None):
            raise InvalidState("incomplete native runtime package")
        for value in (parameters, party_state):
            if value is not None and (
                not isinstance(value, bytes)
                or not value
                or len(value) > MAX_RUNTIME_COMPONENT_BYTES
            ):
                raise InvalidState("invalid native runtime component")

    @staticmethod
    def _decode_runtime_record(row: sqlite3.Row) -> RuntimeEpochPackageRecord:
        try:
            descriptor = RuntimeEpochPackage.from_dict(
                json.loads(bytes(row["descriptor_bytes"]).decode("utf-8"))
            )
            authorizer_config = AuthorizerConfig.from_dict(
                json.loads(bytes(row["authorizer_config_bytes"]).decode("utf-8"))
            )
        except (
            UnicodeDecodeError,
            json.JSONDecodeError,
            LifecycleCertificateError,
        ) as exc:
            raise InvalidState("stored runtime package is malformed") from exc
        parameters = (
            None if row["parameters_bytes"] is None else bytes(row["parameters_bytes"])
        )
        party_state = (
            None
            if row["party_state_bytes"] is None
            else bytes(row["party_state_bytes"])
        )
        PartyStore._validate_runtime_components(parameters, party_state)
        if (
            descriptor.package_digest != row["package_digest"]
            or descriptor.config_digest != authorizer_config.digest
            or descriptor.backup_digest != authorizer_config.backup_digest
            or descriptor.native_enabled != (parameters is not None)
            or descriptor.parameters_hash
            != hash_bytes(
                "LOCUS/runtime-public-parameters/v1",
                b"" if parameters is None else parameters,
            ).hex()
            or descriptor.party_state_hash
            != hash_bytes(
                "LOCUS/runtime-party-state/v1",
                b"" if party_state is None else party_state,
            ).hex()
        ):
            raise InvalidState("stored runtime package binding is invalid")
        return RuntimeEpochPackageRecord(
            descriptor=descriptor,
            authorizer_config=authorizer_config,
            parameters=parameters,
            party_state=party_state,
            state=row["state"],
        )

    def register_initial_runtime_package(
        self,
        config: EpochConfig,
        authorizer_config: AuthorizerConfig,
        *,
        parameters: bytes | None,
        party_state: bytes | None,
    ) -> str:
        """Persist the boot epoch's package exactly once for dynamic selection."""

        config.validate()
        authorizer_config.validate()
        self._validate_runtime_components(parameters, party_state)
        if (
            config.bid != authorizer_config.bid
            or config.epoch != authorizer_config.epoch
            or config.config_digest != authorizer_config.digest
            or config.backup_digest != authorizer_config.backup_digest
            or config.party_id not in authorizer_config.public_keys
        ):
            raise InvalidState("initial runtime package configuration mismatch")
        descriptor = RuntimeEpochPackage(
            bid=config.bid,
            epoch=config.epoch,
            party_id=config.party_id,
            transition_hash=GENESIS_HEAD,
            config_digest=config.config_digest,
            backup_digest=config.backup_digest,
            native_enabled=parameters is not None,
            parameters_hash=hash_bytes(
                "LOCUS/runtime-public-parameters/v1",
                b"" if parameters is None else parameters,
            ).hex(),
            party_state_hash=hash_bytes(
                "LOCUS/runtime-party-state/v1",
                b"" if party_state is None else party_state,
            ).hex(),
        )
        descriptor.validate()
        descriptor_bytes = encode(descriptor.to_dict())
        config_bytes = encode(authorizer_config.to_dict())
        with self._transaction() as connection:
            epoch = connection.execute(
                "SELECT * FROM epochs WHERE bid = ? AND epoch = ?",
                (config.bid, config.epoch),
            ).fetchone()
            if epoch is None or epoch["party_id"] != config.party_id:
                raise InvalidState("initial epoch is unavailable")
            expected_state = epoch["status"]
            existing = connection.execute(
                "SELECT * FROM epoch_runtime_packages WHERE bid = ? AND epoch = ?",
                (config.bid, config.epoch),
            ).fetchone()
            expected = (
                config.party_id,
                descriptor.package_digest,
                descriptor_bytes,
                config_bytes,
                parameters,
                party_state,
                expected_state,
            )
            if existing is not None:
                actual = (
                    existing["party_id"],
                    existing["package_digest"],
                    bytes(existing["descriptor_bytes"]),
                    bytes(existing["authorizer_config_bytes"]),
                    None
                    if existing["parameters_bytes"] is None
                    else bytes(existing["parameters_bytes"]),
                    None
                    if existing["party_state_bytes"] is None
                    else bytes(existing["party_state_bytes"]),
                    existing["state"],
                )
                if actual != expected:
                    raise Conflict("conflicting initial runtime package")
                return descriptor.package_digest
            connection.execute(
                """INSERT INTO epoch_runtime_packages(
                       bid, epoch, party_id, package_digest, descriptor_bytes,
                       authorizer_config_bytes, parameters_bytes,
                       party_state_bytes, state
                   ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    config.bid,
                    config.epoch,
                    config.party_id,
                    descriptor.package_digest,
                    descriptor_bytes,
                    config_bytes,
                    parameters,
                    party_state,
                    expected_state,
                ),
            )
        return descriptor.package_digest

    def runtime_epoch_package(
        self, bid: str, epoch: int, *, require_active: bool = False
    ) -> RuntimeEpochPackageRecord:
        _hex(bid, "backup identifier", bytes_length=16)
        _exact_int(epoch, "epoch")
        with self._lock:
            row = self._connection.execute(
                "SELECT * FROM epoch_runtime_packages WHERE bid = ? AND epoch = ?",
                (bid, epoch),
            ).fetchone()
        if row is None:
            raise InvalidState("runtime epoch package is unavailable")
        record = self._decode_runtime_record(row)
        if require_active and record.state != "ACTIVE":
            raise InvalidState("runtime epoch package is not active")
        return record

    @staticmethod
    def _verify_transition(
        transition: EpochTransition,
        predecessor_config: AuthorizerConfig,
        successor_config: AuthorizerConfig,
    ) -> None:
        try:
            transition.verify_configs(predecessor_config, successor_config)
        except LifecycleCertificateError as exc:
            raise InvalidState("invalid epoch transition") from exc

    @staticmethod
    def _matching_predecessor(row: sqlite3.Row, transition: EpochTransition) -> bool:
        return (
            row["config_digest"] == transition.predecessor_config_digest
            and row["backup_digest"] == transition.predecessor_backup_digest
            and row["installed_head"] == transition.predecessor_head
            and row["consumed"] == transition.predecessor_consumed
            and row["budget"] == transition.predecessor_budget
        )

    def create_epoch_approval(
        self,
        transition: EpochTransition,
        predecessor_config: AuthorizerConfig,
        successor_config: AuthorizerConfig,
        signer: AuthorizerSigner,
    ) -> EpochApproval:
        """Durably lock one exact successor before returning an old-quorum vote."""

        self._verify_transition(transition, predecessor_config, successor_config)
        if predecessor_config.public_keys.get(signer.party_id) != signer.public_key_hex:
            raise InvalidState("lifecycle signer does not match predecessor")
        transition_bytes = encode(transition.to_dict())
        with self._transaction() as connection:
            existing = connection.execute(
                """SELECT * FROM epoch_transition_locks
                   WHERE bid = ? AND predecessor_epoch = ?""",
                (transition.bid, transition.predecessor_epoch),
            ).fetchone()
            if existing is not None:
                if (
                    existing["transition_hash"] != transition.transition_hash
                    or bytes(existing["transition_bytes"]) != transition_bytes
                ):
                    raise Conflict("predecessor is locked to another successor")
                if existing["approval_bytes"] is not None:
                    return EpochApproval.from_dict(
                        json.loads(bytes(existing["approval_bytes"]).decode("utf-8"))
                    )
            predecessor = connection.execute(
                "SELECT * FROM epochs WHERE bid = ? AND epoch = ?",
                (transition.bid, transition.predecessor_epoch),
            ).fetchone()
            if (
                predecessor is None
                or predecessor["status"] != "ACTIVE"
                or predecessor["party_id"] != signer.party_id
                or not self._matching_predecessor(predecessor, transition)
            ):
                raise InvalidState("predecessor epoch is not transition-ready")
            unresolved = connection.execute(
                """SELECT 1 FROM slot_locks
                   WHERE bid = ? AND epoch = ? AND state != 'INSTALLED'
                   LIMIT 1""",
                (transition.bid, transition.predecessor_epoch),
            ).fetchone()
            if unresolved is not None:
                raise Conflict("predecessor has an unresolved ledger slot")
            if existing is None:
                connection.execute(
                    """INSERT INTO epoch_transition_locks(
                           bid, predecessor_epoch, transition_hash, transition_bytes
                       ) VALUES (?, ?, ?, ?)""",
                    (
                        transition.bid,
                        transition.predecessor_epoch,
                        transition.transition_hash,
                        transition_bytes,
                    ),
                )
                self._append_audit(
                    connection,
                    "EPOCH_TRANSITION_LOCKED",
                    transition.bid,
                    transition.predecessor_epoch,
                    transition.transition_hash,
                )

        approval = EpochApproval.create(transition, signer)
        approval_bytes = encode(approval.to_dict())
        with self._transaction() as connection:
            row = connection.execute(
                """SELECT transition_hash, approval_bytes
                   FROM epoch_transition_locks
                   WHERE bid = ? AND predecessor_epoch = ?""",
                (transition.bid, transition.predecessor_epoch),
            ).fetchone()
            if row is None or row["transition_hash"] != transition.transition_hash:
                raise Conflict("lifecycle lock changed before approval")
            if row["approval_bytes"] is not None:
                if bytes(row["approval_bytes"]) != approval_bytes:
                    raise Conflict("stored lifecycle approval differs")
            else:
                connection.execute(
                    """UPDATE epoch_transition_locks SET approval_bytes = ?
                       WHERE bid = ? AND predecessor_epoch = ?""",
                    (
                        approval_bytes,
                        transition.bid,
                        transition.predecessor_epoch,
                    ),
                )
        return approval

    def prepare_successor_epoch(
        self,
        config: EpochConfig,
        transition: EpochTransition,
        predecessor_config: AuthorizerConfig,
        successor_config: AuthorizerConfig,
        signer: AuthorizerSigner,
        *,
        parameters: bytes | None = None,
        party_state: bytes | None = None,
    ) -> EpochReady:
        """Atomically persist one non-recoverable runtime package and readiness."""

        config.validate()
        self._verify_transition(transition, predecessor_config, successor_config)
        self._validate_runtime_components(parameters, party_state)
        if (
            config.bid != transition.bid
            or config.epoch != transition.successor_epoch
            or config.party_id != signer.party_id
            or config.config_digest != transition.successor_config_digest
            or config.backup_digest != transition.successor_backup_digest
            or config.budget != transition.successor_budget
            or config.genesis_head != GENESIS_HEAD
            or successor_config.public_keys.get(signer.party_id)
            != signer.public_key_hex
        ):
            raise InvalidState("successor package does not match transition")
        try:
            runtime_package = RuntimeEpochPackage.create(
                transition,
                successor_config,
                signer.party_id,
                parameters=parameters,
                party_state=party_state,
            )
        except LifecycleCertificateError as exc:
            raise InvalidState("invalid successor runtime package") from exc
        ready = EpochReady.create(transition, runtime_package, signer)
        ready_bytes = encode(ready.to_dict())
        descriptor_bytes = encode(runtime_package.to_dict())
        successor_config_bytes = encode(successor_config.to_dict())
        with self._transaction() as connection:
            existing = connection.execute(
                """SELECT * FROM epoch_preparations
                   WHERE bid = ? AND successor_epoch = ?""",
                (transition.bid, transition.successor_epoch),
            ).fetchone()
            expected = (
                transition.predecessor_epoch,
                signer.party_id,
                transition.transition_hash,
                config.config_digest,
                config.backup_digest,
                config.budget,
                ready_bytes,
            )
            if existing is not None:
                actual = (
                    existing["predecessor_epoch"],
                    existing["party_id"],
                    existing["transition_hash"],
                    existing["config_digest"],
                    existing["backup_digest"],
                    existing["budget"],
                    bytes(existing["readiness_bytes"]),
                )
                if actual != expected:
                    raise Conflict("conflicting successor preparation")
                stored_runtime = connection.execute(
                    """SELECT * FROM epoch_runtime_packages
                       WHERE bid = ? AND epoch = ?""",
                    (transition.bid, transition.successor_epoch),
                ).fetchone()
                if stored_runtime is None:
                    raise InvalidState("successor runtime package is missing")
                runtime_expected = (
                    signer.party_id,
                    runtime_package.package_digest,
                    descriptor_bytes,
                    successor_config_bytes,
                    parameters,
                    party_state,
                    existing["state"] == "ACTIVATED" and "ACTIVE" or "PREPARED",
                )
                runtime_actual = (
                    stored_runtime["party_id"],
                    stored_runtime["package_digest"],
                    bytes(stored_runtime["descriptor_bytes"]),
                    bytes(stored_runtime["authorizer_config_bytes"]),
                    None
                    if stored_runtime["parameters_bytes"] is None
                    else bytes(stored_runtime["parameters_bytes"]),
                    None
                    if stored_runtime["party_state_bytes"] is None
                    else bytes(stored_runtime["party_state_bytes"]),
                    stored_runtime["state"],
                )
                if runtime_actual != runtime_expected:
                    raise Conflict("conflicting successor runtime package")
                return EpochReady.from_dict(
                    json.loads(bytes(existing["readiness_bytes"]).decode("utf-8"))
                )
            predecessor = connection.execute(
                "SELECT * FROM epochs WHERE bid = ? AND epoch = ?",
                (transition.bid, transition.predecessor_epoch),
            ).fetchone()
            lifecycle_lock = connection.execute(
                """SELECT transition_hash, approval_bytes
                   FROM epoch_transition_locks
                   WHERE bid = ? AND predecessor_epoch = ?""",
                (transition.bid, transition.predecessor_epoch),
            ).fetchone()
            if (
                predecessor is None
                or predecessor["status"] != "ACTIVE"
                or predecessor["party_id"] != signer.party_id
                or not self._matching_predecessor(predecessor, transition)
                or lifecycle_lock is None
                or lifecycle_lock["transition_hash"] != transition.transition_hash
                or lifecycle_lock["approval_bytes"] is None
            ):
                raise InvalidState("predecessor approval is not durably prepared")
            active_successor = connection.execute(
                "SELECT * FROM epochs WHERE bid = ? AND epoch = ?",
                (transition.bid, transition.successor_epoch),
            ).fetchone()
            if active_successor is not None:
                raise Conflict("successor epoch already exists")
            connection.execute(
                """INSERT INTO epoch_preparations(
                       bid, successor_epoch, predecessor_epoch, party_id,
                       transition_hash, config_digest, backup_digest, budget,
                       readiness_bytes, state
                   ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'PREPARED')""",
                (
                    transition.bid,
                    transition.successor_epoch,
                    transition.predecessor_epoch,
                    signer.party_id,
                    transition.transition_hash,
                    config.config_digest,
                    config.backup_digest,
                    config.budget,
                    ready_bytes,
                ),
            )
            connection.execute(
                """INSERT INTO epoch_runtime_packages(
                       bid, epoch, party_id, package_digest, descriptor_bytes,
                       authorizer_config_bytes, parameters_bytes,
                       party_state_bytes, state
                   ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'PREPARED')""",
                (
                    transition.bid,
                    transition.successor_epoch,
                    signer.party_id,
                    runtime_package.package_digest,
                    descriptor_bytes,
                    successor_config_bytes,
                    parameters,
                    party_state,
                ),
            )
            self._append_audit(
                connection,
                "EPOCH_SUCCESSOR_PREPARED",
                transition.bid,
                transition.successor_epoch,
                transition.transition_hash,
            )
        return ready

    def activate_successor_epoch(
        self,
        certificate: EpochActivationCertificate,
        predecessor_config: AuthorizerConfig,
        successor_config: AuthorizerConfig,
    ) -> str:
        """Atomically retire the predecessor and activate its prepared successor."""

        try:
            certificate.verify(predecessor_config, successor_config)
        except LifecycleCertificateError as exc:
            raise InvalidState("invalid epoch activation certificate") from exc
        transition = certificate.transition
        certificate_hash = certificate.certificate_hash
        with self._transaction() as connection:
            predecessor = connection.execute(
                "SELECT * FROM epochs WHERE bid = ? AND epoch = ?",
                (transition.bid, transition.predecessor_epoch),
            ).fetchone()
            successor = connection.execute(
                "SELECT * FROM epochs WHERE bid = ? AND epoch = ?",
                (transition.bid, transition.successor_epoch),
            ).fetchone()
            preparation = connection.execute(
                """SELECT * FROM epoch_preparations
                   WHERE bid = ? AND successor_epoch = ?""",
                (transition.bid, transition.successor_epoch),
            ).fetchone()
            runtime_package = connection.execute(
                """SELECT * FROM epoch_runtime_packages
                   WHERE bid = ? AND epoch = ?""",
                (transition.bid, transition.successor_epoch),
            ).fetchone()
            lifecycle_lock = connection.execute(
                """SELECT transition_hash FROM epoch_transition_locks
                   WHERE bid = ? AND predecessor_epoch = ?""",
                (transition.bid, transition.predecessor_epoch),
            ).fetchone()
            if (
                successor is not None
                and predecessor is not None
                and predecessor["status"] == "RETIRED"
                and successor["status"] == "ACTIVE"
                and preparation is not None
                and preparation["state"] == "ACTIVATED"
                and preparation["activation_certificate_hash"] == certificate_hash
                and runtime_package is not None
                and runtime_package["state"] == "ACTIVE"
            ):
                return certificate_hash
            local_ready = (
                None
                if preparation is None
                else EpochReady.from_dict(
                    json.loads(bytes(preparation["readiness_bytes"]).decode("utf-8"))
                )
            )
            if (
                predecessor is None
                or predecessor["status"] != "ACTIVE"
                or not self._matching_predecessor(predecessor, transition)
                or successor is not None
                or preparation is None
                or preparation["state"] != "PREPARED"
                or preparation["transition_hash"] != transition.transition_hash
                or preparation["config_digest"] != transition.successor_config_digest
                or preparation["backup_digest"] != transition.successor_backup_digest
                or preparation["budget"] != transition.successor_budget
                or local_ready is None
                or runtime_package is None
                or runtime_package["state"] != "PREPARED"
                or runtime_package["package_digest"]
                != local_ready.runtime_package_digest
                or lifecycle_lock is None
                or lifecycle_lock["transition_hash"] != transition.transition_hash
            ):
                raise Conflict("local state does not match epoch activation")
            connection.execute(
                """UPDATE epochs SET status = 'RETIRED'
                   WHERE bid = ? AND epoch = ?""",
                (transition.bid, transition.predecessor_epoch),
            )
            connection.execute(
                """INSERT INTO epochs(
                       bid, epoch, party_id, config_digest, backup_digest, budget,
                       consumed, installed_index, installed_head, status
                   ) VALUES (?, ?, ?, ?, ?, ?, 0, 0, ?, 'ACTIVE')""",
                (
                    transition.bid,
                    transition.successor_epoch,
                    preparation["party_id"],
                    transition.successor_config_digest,
                    transition.successor_backup_digest,
                    transition.successor_budget,
                    GENESIS_HEAD,
                ),
            )
            connection.execute(
                """UPDATE epoch_runtime_packages SET state = 'RETIRED'
                   WHERE bid = ? AND epoch = ? AND state = 'ACTIVE'""",
                (transition.bid, transition.predecessor_epoch),
            )
            connection.execute(
                """UPDATE epoch_runtime_packages SET state = 'ACTIVE'
                   WHERE bid = ? AND epoch = ? AND state = 'PREPARED'""",
                (transition.bid, transition.successor_epoch),
            )
            connection.execute(
                """UPDATE epoch_preparations
                   SET state = 'ACTIVATED', activation_certificate_hash = ?
                   WHERE bid = ? AND successor_epoch = ?""",
                (
                    certificate_hash,
                    transition.bid,
                    transition.successor_epoch,
                ),
            )
            self._append_audit(
                connection,
                "EPOCH_RETIRED",
                transition.bid,
                transition.predecessor_epoch,
                transition.transition_hash,
            )
            self._append_audit(
                connection,
                "EPOCH_ACTIVATED",
                transition.bid,
                transition.successor_epoch,
                certificate_hash,
            )
        return certificate_hash

    def successor_preparation(self, bid: str, epoch: int) -> dict[str, int | str]:
        _hex(bid, "backup identifier", bytes_length=16)
        _exact_int(epoch, "successor epoch")
        with self._lock:
            row = self._connection.execute(
                """SELECT predecessor_epoch, party_id, transition_hash,
                          config_digest, backup_digest, budget, state,
                          activation_certificate_hash
                   FROM epoch_preparations
                   WHERE bid = ? AND successor_epoch = ?""",
                (bid, epoch),
            ).fetchone()
        if row is None:
            raise InvalidState("unknown successor preparation")
        return {
            "predecessor_epoch": row["predecessor_epoch"],
            "party_id": row["party_id"],
            "transition_hash": row["transition_hash"],
            "config_digest": row["config_digest"],
            "backup_digest": row["backup_digest"],
            "budget": row["budget"],
            "state": row["state"],
            "activation_certificate_hash": (
                ""
                if row["activation_certificate_hash"] is None
                else row["activation_certificate_hash"]
            ),
        }

    def install_authorization(self, authorization: AttemptAuthorization) -> str:
        authorization.validate()
        entry_hash = authorization.entry_hash()
        with self._transaction() as connection:
            epoch = connection.execute(
                "SELECT * FROM epochs WHERE bid = ? AND epoch = ?",
                (authorization.bid, authorization.epoch),
            ).fetchone()
            if epoch is None or epoch["status"] != "ACTIVE":
                raise InvalidState("epoch is not active")
            if epoch["config_digest"] != authorization.config_digest:
                raise InvalidState("configuration mismatch")

            existing = connection.execute(
                "SELECT * FROM attempts WHERE bid = ? AND epoch = ? AND sid = ?",
                (authorization.bid, authorization.epoch, authorization.sid),
            ).fetchone()
            if existing is not None:
                expected = (
                    authorization.request_digest,
                    authorization.tpass_request_hash,
                    authorization.log_index,
                    authorization.previous_head,
                    entry_hash,
                    authorization.certificate_hash,
                    authorization.resulting_consumed,
                    authorization.effective_budget,
                )
                actual = (
                    existing["request_digest"],
                    existing["tpass_request_hash"],
                    existing["log_index"],
                    existing["previous_head"],
                    existing["entry_hash"],
                    existing["certificate_hash"],
                    existing["resulting_consumed"],
                    existing["effective_budget"],
                )
                if actual != expected:
                    raise Conflict("session identifier reused for another attempt")
                return entry_hash

            if authorization.effective_budget != epoch["budget"]:
                raise InvalidState("effective budget mismatch")
            if authorization.resulting_consumed > authorization.effective_budget:
                raise BudgetExhausted("attempt budget exhausted")
            if authorization.log_index != epoch["installed_index"] + 1:
                raise InvalidState("authorization log index mismatch")
            if authorization.previous_head != epoch["installed_head"]:
                raise InvalidState("authorization predecessor mismatch")
            if authorization.resulting_consumed != epoch["consumed"] + 1:
                raise InvalidState("authorization consumed count mismatch")

            try:
                connection.execute(
                    """INSERT INTO attempts(
                           bid, epoch, sid, request_digest, tpass_request_hash,
                           log_index, previous_head, entry_hash, certificate_hash,
                           resulting_consumed, effective_budget
                       ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        authorization.bid,
                        authorization.epoch,
                        authorization.sid,
                        authorization.request_digest,
                        authorization.tpass_request_hash,
                        authorization.log_index,
                        authorization.previous_head,
                        entry_hash,
                        authorization.certificate_hash,
                        authorization.resulting_consumed,
                        authorization.effective_budget,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise Conflict("authorization slot conflict") from exc
            connection.execute(
                """UPDATE epochs
                   SET consumed = ?, installed_index = ?, installed_head = ?
                   WHERE bid = ? AND epoch = ?""",
                (
                    authorization.resulting_consumed,
                    authorization.log_index,
                    entry_hash,
                    authorization.bid,
                    authorization.epoch,
                ),
            )
            self._append_audit(
                connection,
                "ATTEMPT_AUTHORIZATION_INSTALLED",
                authorization.bid,
                authorization.epoch,
                authorization.request_digest,
            )
        return entry_hash

    def create_entry_vote(
        self,
        entry: AttemptEntry,
        config: AuthorizerConfig,
        signer: AuthorizerSigner,
    ) -> EntryVote:
        """Durably lock one slot before returning this party's signed vote."""

        entry.validate()
        config.validate()
        if (
            entry.bid != config.bid
            or entry.epoch != config.epoch
            or entry.config_digest != config.digest
        ):
            raise InvalidState("entry configuration mismatch")
        entry_bytes = encode(entry.to_dict())
        with self._transaction() as connection:
            epoch = connection.execute(
                "SELECT * FROM epochs WHERE bid = ? AND epoch = ?",
                (entry.bid, entry.epoch),
            ).fetchone()
            if epoch is None or epoch["status"] != "ACTIVE":
                raise InvalidState("epoch is not active")
            if epoch["party_id"] != signer.party_id:
                raise InvalidState("authorizer signer does not match party")
            if epoch["config_digest"] != config.digest:
                raise InvalidState("configuration mismatch")
            existing = connection.execute(
                """SELECT * FROM slot_locks
                   WHERE bid = ? AND epoch = ? AND log_index = ?""",
                (entry.bid, entry.epoch, entry.log_index),
            ).fetchone()
            if existing is not None:
                if existing["entry_hash"] != entry.entry_hash:
                    raise Conflict("authorizer slot is locked for another entry")
                if existing["entry_vote_bytes"] is not None:
                    return EntryVote.from_dict(
                        json.loads(bytes(existing["entry_vote_bytes"]).decode("utf-8"))
                    )
            else:
                if entry.log_index != epoch["installed_index"] + 1:
                    raise InvalidState("entry log index mismatch")
                if entry.previous_head != epoch["installed_head"]:
                    raise InvalidState("entry predecessor mismatch")
                if entry.resulting_consumed != epoch["consumed"] + 1:
                    raise InvalidState("entry consumed count mismatch")
                if entry.effective_budget != epoch["budget"]:
                    raise InvalidState("entry budget mismatch")
                connection.execute(
                    """INSERT INTO slot_locks(
                           bid, epoch, log_index, sid, entry_hash, entry_bytes, state
                       ) VALUES (?, ?, ?, ?, ?, ?, 'VOTED')""",
                    (
                        entry.bid,
                        entry.epoch,
                        entry.log_index,
                        entry.sid,
                        entry.entry_hash,
                        entry_bytes,
                    ),
                )
                self._append_audit(
                    connection,
                    "ENTRY_VOTE_LOCKED",
                    entry.bid,
                    entry.epoch,
                    entry.entry_hash,
                )

        vote = EntryVote.create(entry, signer)
        vote_bytes = encode(vote.to_dict())
        with self._transaction() as connection:
            row = connection.execute(
                """SELECT entry_hash, entry_vote_bytes FROM slot_locks
                   WHERE bid = ? AND epoch = ? AND log_index = ?""",
                (entry.bid, entry.epoch, entry.log_index),
            ).fetchone()
            if row is None or row["entry_hash"] != entry.entry_hash:
                raise Conflict("authorizer slot changed after durable lock")
            if row["entry_vote_bytes"] is not None:
                stored = bytes(row["entry_vote_bytes"])
                if stored != vote_bytes:
                    raise Conflict("stored entry vote differs")
            else:
                connection.execute(
                    """UPDATE slot_locks SET entry_vote_bytes = ?
                       WHERE bid = ? AND epoch = ? AND log_index = ?""",
                    (vote_bytes, entry.bid, entry.epoch, entry.log_index),
                )
        return vote

    def create_install_vote(
        self,
        prepare: PrepareCertificate,
        config: AuthorizerConfig,
        signer: AuthorizerSigner,
    ) -> InstallVote:
        """Persist a verified prepare certificate before returning an install vote."""

        prepare.verify(config)
        entry = prepare.entry
        prepare_bytes = encode(prepare.to_dict())
        with self._transaction() as connection:
            epoch = connection.execute(
                "SELECT party_id, config_digest, status FROM epochs WHERE bid = ? AND epoch = ?",
                (entry.bid, entry.epoch),
            ).fetchone()
            if (
                epoch is None
                or epoch["status"] != "ACTIVE"
                or epoch["party_id"] != signer.party_id
                or epoch["config_digest"] != config.digest
            ):
                raise InvalidState("party cannot install prepare certificate")
            lock = connection.execute(
                """SELECT * FROM slot_locks
                   WHERE bid = ? AND epoch = ? AND log_index = ?""",
                (entry.bid, entry.epoch, entry.log_index),
            ).fetchone()
            if (
                lock is None
                or lock["entry_hash"] != entry.entry_hash
                or lock["entry_vote_bytes"] is None
            ):
                raise Conflict("prepare certificate has no matching durable vote lock")
            if lock["prepare_hash"] not in {None, prepare.certificate_hash}:
                raise Conflict("conflicting prepare certificate")
            if lock["install_vote_bytes"] is not None:
                return InstallVote.from_dict(
                    json.loads(bytes(lock["install_vote_bytes"]).decode("utf-8"))
                )
            connection.execute(
                """UPDATE slot_locks
                   SET prepare_hash = ?, prepare_bytes = ?, state = 'PREPARED'
                   WHERE bid = ? AND epoch = ? AND log_index = ?""",
                (
                    prepare.certificate_hash,
                    prepare_bytes,
                    entry.bid,
                    entry.epoch,
                    entry.log_index,
                ),
            )
            self._append_audit(
                connection,
                "PREPARE_CERTIFICATE_STORED",
                entry.bid,
                entry.epoch,
                prepare.certificate_hash,
            )

        vote = InstallVote.create(prepare, signer)
        vote_bytes = encode(vote.to_dict())
        with self._transaction() as connection:
            row = connection.execute(
                """SELECT prepare_hash, install_vote_bytes FROM slot_locks
                   WHERE bid = ? AND epoch = ? AND log_index = ?""",
                (entry.bid, entry.epoch, entry.log_index),
            ).fetchone()
            if row is None or row["prepare_hash"] != prepare.certificate_hash:
                raise Conflict("prepare certificate changed before install vote")
            if row["install_vote_bytes"] is not None:
                stored = bytes(row["install_vote_bytes"])
                if stored != vote_bytes:
                    raise Conflict("stored install vote differs")
            else:
                connection.execute(
                    """UPDATE slot_locks
                       SET install_vote_bytes = ?, state = 'INSTALL_VOTED'
                       WHERE bid = ? AND epoch = ? AND log_index = ?""",
                    (vote_bytes, entry.bid, entry.epoch, entry.log_index),
                )
        return vote

    def install_certificate(
        self,
        certificate: AuthorizationCertificate,
        config: AuthorizerConfig,
    ) -> AttemptAuthorization:
        """Verify and install a complete two-phase authorization certificate."""

        certificate.verify(config)
        authorization = AttemptAuthorization.from_dict(
            certificate.authorization_fields()
        )
        entry = certificate.prepare.entry
        with self._lock:
            lock = self._connection.execute(
                """SELECT entry_hash FROM slot_locks
                   WHERE bid = ? AND epoch = ? AND log_index = ?""",
                (entry.bid, entry.epoch, entry.log_index),
            ).fetchone()
            if lock is not None and lock["entry_hash"] != entry.entry_hash:
                raise Conflict("authorization certificate conflicts with local lock")
            self.install_authorization(authorization)
            with self._transaction() as connection:
                if lock is None:
                    connection.execute(
                        """INSERT INTO slot_locks(
                               bid, epoch, log_index, sid, entry_hash, entry_bytes,
                               prepare_hash, prepare_bytes, authorization_bytes, state
                           ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'INSTALLED')""",
                        (
                            entry.bid,
                            entry.epoch,
                            entry.log_index,
                            entry.sid,
                            entry.entry_hash,
                            encode(entry.to_dict()),
                            certificate.prepare.certificate_hash,
                            encode(certificate.prepare.to_dict()),
                            encode(certificate.to_dict()),
                        ),
                    )
                else:
                    connection.execute(
                        """UPDATE slot_locks
                           SET authorization_bytes = ?, state = 'INSTALLED'
                           WHERE bid = ? AND epoch = ? AND log_index = ?""",
                        (
                            encode(certificate.to_dict()),
                            entry.bid,
                            entry.epoch,
                            entry.log_index,
                        ),
                    )
        return authorization

    def installed_certificate(
        self, bid: str, epoch: int, sid: str
    ) -> AuthorizationCertificate | None:
        _hex(bid, "backup identifier", bytes_length=16)
        _exact_int(epoch, "epoch")
        _hex(sid, "session identifier", bytes_length=32)
        with self._lock:
            row = self._connection.execute(
                """SELECT authorization_bytes FROM slot_locks
                   WHERE bid = ? AND epoch = ? AND sid = ? AND state = 'INSTALLED'""",
                (bid, epoch, sid),
            ).fetchone()
        if row is None or row["authorization_bytes"] is None:
            return None
        return AuthorizationCertificate.from_dict(
            json.loads(bytes(row["authorization_bytes"]).decode("utf-8"))
        )

    def next_slot_lock(self, bid: str, epoch: int) -> str | None:
        status = self.status(bid, epoch)
        with self._lock:
            row = self._connection.execute(
                """SELECT entry_hash FROM slot_locks
                   WHERE bid = ? AND epoch = ? AND log_index = ?
                     AND state != 'INSTALLED'""",
                (bid, epoch, int(status["installed_index"]) + 1),
            ).fetchone()
        return None if row is None else str(row["entry_hash"])

    def create_freshness_vote(
        self,
        request: FreshnessRequest,
        config: AuthorizerConfig,
        signer: AuthorizerSigner,
    ) -> FreshnessVote:
        """Sign current response freshness only for an installed active attempt."""

        request.validate()
        config.validate()
        if (
            request.bid != config.bid
            or request.epoch != config.epoch
            or request.config_digest != config.digest
        ):
            raise InvalidState("freshness configuration mismatch")
        with self._transaction() as connection:
            epoch = connection.execute(
                "SELECT party_id, config_digest, status FROM epochs WHERE bid = ? AND epoch = ?",
                (request.bid, request.epoch),
            ).fetchone()
            if (
                epoch is None
                or epoch["status"] != "ACTIVE"
                or epoch["party_id"] != signer.party_id
                or epoch["config_digest"] != config.digest
            ):
                raise InvalidState("authorizer is not ready for freshness")
            attempt = connection.execute(
                """SELECT request_digest FROM attempts
                   WHERE bid = ? AND epoch = ? AND certificate_hash = ?""",
                (request.bid, request.epoch, request.authorization_hash),
            ).fetchone()
            if attempt is None or attempt["request_digest"] != request.request_digest:
                raise InvalidState("freshness attempt is not installed")
            existing = connection.execute(
                """SELECT vote_bytes FROM freshness_votes
                   WHERE freshness_request_hash = ? AND authorizer_id = ?""",
                (request.request_hash, signer.party_id),
            ).fetchone()
            if existing is not None:
                return FreshnessVote.from_dict(
                    json.loads(bytes(existing["vote_bytes"]).decode("utf-8"))
                )
            vote = FreshnessVote.create(request, signer)
            connection.execute(
                """INSERT INTO freshness_votes(
                       freshness_request_hash, authorizer_id, request_bytes, vote_bytes
                   ) VALUES (?, ?, ?, ?)""",
                (
                    request.request_hash,
                    signer.party_id,
                    encode(request.to_dict()),
                    encode(vote.to_dict()),
                ),
            )
            self._append_audit(
                connection,
                "RESPONSE_FRESHNESS_VOTED",
                request.bid,
                request.epoch,
                request.request_hash,
            )
            return vote

    def reserve_commitment(
        self,
        *,
        bid: str,
        epoch: int,
        sid: str,
        party_id: int,
        request: bytes,
        selected: list[int],
        certificate_hash: str,
        freshness_digest: str,
    ) -> PhaseReservation:
        _hex(bid, "backup identifier", bytes_length=16)
        _exact_int(epoch, "epoch")
        _hex(sid, "session identifier", bytes_length=32)
        _exact_int(party_id, "party identifier")
        _hex(certificate_hash, "certificate hash", bytes_length=32)
        _hex(freshness_digest, "freshness digest", bytes_length=32)
        if not isinstance(request, bytes):
            raise InvalidState("invalid TPASS request")
        if (
            not isinstance(selected, list)
            or not selected
            or any(
                isinstance(value, bool) or not isinstance(value, int)
                for value in selected
            )
            or selected != sorted(set(selected))
            or selected[0] < 1
            or selected[-1] > 255
            or party_id not in selected
        ):
            raise InvalidState("invalid selected party set")
        request_hash = hash_bytes("LOCUS/tpass-request-bytes/v1", request).hex()
        selected_digest = hash_bytes(
            "LOCUS/selected-parties/v1", encode(selected)
        ).hex()

        with self._transaction() as connection:
            epoch_row = connection.execute(
                "SELECT party_id, status FROM epochs WHERE bid = ? AND epoch = ?",
                (bid, epoch),
            ).fetchone()
            if (
                epoch_row is None
                or epoch_row["status"] != "ACTIVE"
                or epoch_row["party_id"] != party_id
            ):
                raise InvalidState("party epoch is not active")
            attempt = connection.execute(
                "SELECT * FROM attempts WHERE bid = ? AND epoch = ? AND sid = ?",
                (bid, epoch, sid),
            ).fetchone()
            if attempt is None:
                raise InvalidState("attempt authorization is not installed")
            if (
                attempt["tpass_request_hash"] != request_hash
                or attempt["certificate_hash"] != certificate_hash
            ):
                raise Conflict("TPASS request does not match authorization")

            existing = connection.execute(
                """SELECT * FROM phases
                   WHERE bid = ? AND epoch = ? AND sid = ? AND party_id = ?""",
                (bid, epoch, sid, party_id),
            ).fetchone()
            if existing is not None:
                if existing["state"] in {"INTENT", "LOST"}:
                    raise SessionLost("TPASS phase cannot be resumed")
                if (
                    existing["selected_digest"] != selected_digest
                    or existing["freshness_digest"] != freshness_digest
                ):
                    raise Conflict("TPASS phase retry changed its binding")
                return PhaseReservation(
                    phase_instance_id=existing["phase_instance_id"],
                    state=existing["state"],
                    commitment=existing["commitment"],
                    response=existing["response"],
                )

            phase_instance_id = secrets.token_hex(32)
            connection.execute(
                """INSERT INTO phases(
                       bid, epoch, sid, party_id, phase_instance_id,
                       selected_digest, freshness_digest, state
                   ) VALUES (?, ?, ?, ?, ?, ?, ?, 'INTENT')""",
                (
                    bid,
                    epoch,
                    sid,
                    party_id,
                    phase_instance_id,
                    selected_digest,
                    freshness_digest,
                ),
            )
            self._append_audit(
                connection,
                "TPASS_COMMITMENT_INTENT",
                bid,
                epoch,
                attempt["request_digest"],
            )
            return PhaseReservation(phase_instance_id, "INTENT", None, None)

    def store_commitment(self, phase_instance_id: str, commitment: bytes) -> None:
        _hex(phase_instance_id, "phase instance identifier", bytes_length=32)
        if not isinstance(commitment, bytes) or not commitment:
            raise InvalidState("invalid party commitment")
        with self._transaction() as connection:
            row = connection.execute(
                "SELECT * FROM phases WHERE phase_instance_id = ?",
                (phase_instance_id,),
            ).fetchone()
            if row is None or row["state"] != "INTENT":
                raise InvalidState("commitment phase is not pending")
            connection.execute(
                """UPDATE phases SET state = 'COMMITMENT_STORED', commitment = ?
                   WHERE phase_instance_id = ?""",
                (commitment, phase_instance_id),
            )
            self._append_audit(
                connection,
                "TPASS_COMMITMENT_STORED",
                row["bid"],
                row["epoch"],
                hash_bytes("LOCUS/commitment/v1", commitment).hex(),
            )

    def store_response(self, phase_instance_id: str, response: bytes) -> None:
        _hex(phase_instance_id, "phase instance identifier", bytes_length=32)
        if not isinstance(response, bytes) or not response:
            raise InvalidState("invalid party response")
        with self._transaction() as connection:
            row = connection.execute(
                "SELECT * FROM phases WHERE phase_instance_id = ?",
                (phase_instance_id,),
            ).fetchone()
            if row is None or row["state"] != "COMMITMENT_STORED":
                raise InvalidState("response phase is not pending")
            connection.execute(
                """UPDATE phases SET state = 'RESPONDED', response = ?
                   WHERE phase_instance_id = ?""",
                (response, phase_instance_id),
            )
            self._append_audit(
                connection,
                "TPASS_RESPONSE_STORED",
                row["bid"],
                row["epoch"],
                hash_bytes("LOCUS/response/v1", response).hex(),
            )

    def mark_open_phases_lost(self) -> int:
        """Fail closed for phases whose non-serializable ephemeral was lost."""

        with self._transaction() as connection:
            rows = connection.execute(
                "SELECT * FROM phases WHERE state IN ('INTENT', 'COMMITMENT_STORED')"
            ).fetchall()
            for row in rows:
                connection.execute(
                    "UPDATE phases SET state = 'LOST' WHERE phase_instance_id = ?",
                    (row["phase_instance_id"],),
                )
                self._append_audit(
                    connection,
                    "TPASS_SESSION_LOST",
                    row["bid"],
                    row["epoch"],
                    row["phase_instance_id"],
                )
            return len(rows)

    def mark_phase_lost(self, phase_instance_id: str) -> None:
        _hex(phase_instance_id, "phase instance identifier", bytes_length=32)
        with self._transaction() as connection:
            row = connection.execute(
                "SELECT * FROM phases WHERE phase_instance_id = ?",
                (phase_instance_id,),
            ).fetchone()
            if row is None:
                raise InvalidState("unknown TPASS phase")
            if row["state"] == "RESPONDED":
                raise InvalidState("completed TPASS phase cannot be marked lost")
            if row["state"] == "LOST":
                return
            connection.execute(
                "UPDATE phases SET state = 'LOST' WHERE phase_instance_id = ?",
                (phase_instance_id,),
            )
            self._append_audit(
                connection,
                "TPASS_SESSION_LOST",
                row["bid"],
                row["epoch"],
                phase_instance_id,
            )

    def validate_phase_binding(
        self,
        phase_instance_id: str,
        *,
        sid: str | None = None,
        request: bytes,
        selected: list[int],
    ) -> PhaseReservation:
        """Return a phase only when its durable transcript binding matches."""

        _hex(phase_instance_id, "phase instance identifier", bytes_length=32)
        if sid is not None:
            _hex(sid, "session identifier", bytes_length=32)
        if not isinstance(request, bytes):
            raise InvalidState("invalid TPASS request")
        if (
            not isinstance(selected, list)
            or not selected
            or any(
                isinstance(value, bool) or not isinstance(value, int)
                for value in selected
            )
            or selected != sorted(set(selected))
        ):
            raise InvalidState("invalid selected party set")
        request_hash = hash_bytes("LOCUS/tpass-request-bytes/v1", request).hex()
        selected_digest = hash_bytes(
            "LOCUS/selected-parties/v1", encode(selected)
        ).hex()
        with self._lock:
            row = self._connection.execute(
                """SELECT phases.*, attempts.tpass_request_hash,
                          epochs.status AS epoch_status
                   FROM phases
                   JOIN attempts USING (bid, epoch, sid)
                   JOIN epochs USING (bid, epoch)
                   WHERE phase_instance_id = ?""",
                (phase_instance_id,),
            ).fetchone()
        if row is None:
            raise InvalidState("unknown TPASS phase")
        if (
            row["epoch_status"] != "ACTIVE"
            or (sid is not None and row["sid"] != sid)
            or row["tpass_request_hash"] != request_hash
            or row["selected_digest"] != selected_digest
        ):
            raise Conflict("TPASS response changed its transcript binding")
        return PhaseReservation(
            phase_instance_id=row["phase_instance_id"],
            state=row["state"],
            commitment=row["commitment"],
            response=row["response"],
        )

    def phase_scope(self, phase_instance_id: str) -> tuple[str, int]:
        """Return the durable epoch binding for selecting the native service."""

        _hex(phase_instance_id, "phase instance identifier", bytes_length=32)
        with self._lock:
            row = self._connection.execute(
                "SELECT bid, epoch FROM phases WHERE phase_instance_id = ?",
                (phase_instance_id,),
            ).fetchone()
        if row is None:
            raise InvalidState("unknown TPASS phase")
        return row["bid"], row["epoch"]

    def phase(self, phase_instance_id: str) -> PhaseReservation:
        _hex(phase_instance_id, "phase instance identifier", bytes_length=32)
        with self._lock:
            row = self._connection.execute(
                "SELECT * FROM phases WHERE phase_instance_id = ?",
                (phase_instance_id,),
            ).fetchone()
        if row is None:
            raise InvalidState("unknown TPASS phase")
        return PhaseReservation(
            phase_instance_id=row["phase_instance_id"],
            state=row["state"],
            commitment=row["commitment"],
            response=row["response"],
        )

    def status(self, bid: str, epoch: int) -> dict[str, int | str]:
        _hex(bid, "backup identifier", bytes_length=16)
        _exact_int(epoch, "epoch")
        with self._lock:
            row = self._connection.execute(
                "SELECT * FROM epochs WHERE bid = ? AND epoch = ?", (bid, epoch)
            ).fetchone()
        if row is None:
            raise InvalidState("unknown epoch")
        return {
            "party_id": row["party_id"],
            "status": row["status"],
            "backup_digest": row["backup_digest"],
            "consumed": row["consumed"],
            "budget": row["budget"],
            "installed_index": row["installed_index"],
            "installed_head": row["installed_head"],
        }
