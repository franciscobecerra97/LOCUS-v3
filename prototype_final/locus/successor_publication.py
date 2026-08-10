"""P4.3 crash-resumable post-recovery successor publication coordinator."""

from __future__ import annotations

import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Protocol, runtime_checkable

from .codec import encode
from .crypto import hash_bytes

SUCCESSOR_PUBLICATION_JOURNAL = "LOCUS-successor-publication-journal-v1"


class SuccessorPublicationError(ValueError):
    """A successor operation is malformed, stale, or unsafe to continue."""


class SuccessorPhase(StrEnum):
    PRESERVE_ORIGINAL_KEY = "PRESERVE_ORIGINAL_KEY"
    PREPARE_PARTIES = "PREPARE_PARTIES"
    PUBLISH_BACKUP = "PUBLISH_BACKUP"
    PUBLISH_DESCRIPTOR = "PUBLISH_DESCRIPTOR"
    VERIFY_READINESS = "VERIFY_READINESS"
    VERIFY_SUCCESSOR_RECOVERY = "VERIFY_SUCCESSOR_RECOVERY"
    ACTIVATE_SUCCESSOR = "ACTIVATE_SUCCESSOR"
    RETIRE_PREDECESSOR = "RETIRE_PREDECESSOR"
    OPTIONAL_KEY_ROTATION = "OPTIONAL_KEY_ROTATION"
    COMPLETE = "COMPLETE"


PHASE_ORDER = tuple(SuccessorPhase)


def _identifier(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or len(value) > 255
        or not value.isascii()
        or any(ord(character) < 0x21 or ord(character) > 0x7E for character in value)
    ):
        raise SuccessorPublicationError(f"invalid {label}")
    return value


def _digest(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise SuccessorPublicationError(f"invalid {label}")
    return value


def _epoch(value: object, label: str) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < 1
        or value > 2**63 - 1
    ):
        raise SuccessorPublicationError(f"invalid {label}")
    return value


@dataclass(frozen=True)
class SuccessorBinding:
    """Public, immutable binding for one exact successor operation."""

    operation_id: str
    backup_id: str
    predecessor_epoch: int
    successor_epoch: int
    successor_configuration_digest: str
    successor_backup_digest: str
    successor_descriptor_digest: str
    recovered_key_digest: str
    rotate_protected_key: bool

    def __post_init__(self) -> None:
        _identifier(self.operation_id, "successor operation identifier")
        _identifier(self.backup_id, "successor backup identifier")
        predecessor = _epoch(self.predecessor_epoch, "predecessor epoch")
        successor = _epoch(self.successor_epoch, "successor epoch")
        if successor != predecessor + 1:
            raise SuccessorPublicationError("successor epoch is not consecutive")
        _digest(
            self.successor_configuration_digest,
            "successor configuration digest",
        )
        _digest(self.successor_backup_digest, "successor backup digest")
        _digest(self.successor_descriptor_digest, "successor descriptor digest")
        _digest(self.recovered_key_digest, "recovered key digest")
        if not isinstance(self.rotate_protected_key, bool):
            raise SuccessorPublicationError("invalid protected-key rotation choice")

    def to_dict(self) -> dict[str, object]:
        return {
            "backup_id": self.backup_id,
            "operation_id": self.operation_id,
            "predecessor_epoch": self.predecessor_epoch,
            "recovered_key_digest": self.recovered_key_digest,
            "rotate_protected_key": self.rotate_protected_key,
            "successor_backup_digest": self.successor_backup_digest,
            "successor_configuration_digest": self.successor_configuration_digest,
            "successor_descriptor_digest": self.successor_descriptor_digest,
            "successor_epoch": self.successor_epoch,
        }


@dataclass(frozen=True)
class SuccessorOperationState:
    binding: SuccessorBinding
    phase: SuccessorPhase


@runtime_checkable
class SuccessorPublicationBackend(Protocol):
    """Exactly-idempotent effects used by the durable coordinator.

    The frozen v1 party lifecycle activates the successor and retires its
    predecessor atomically. Implementations therefore make
    ``activate_successor`` perform that atomic switch and make
    ``retire_predecessor`` verify/retry the already certified retirement.
    ``verify_successor_recovery`` exercises the prepared package before that
    switch, while the predecessor is still the authorized online epoch.
    """

    def preserve_original_key(
        self, binding: SuccessorBinding, idempotency_key: str
    ) -> None: ...

    def prepare_parties(
        self, binding: SuccessorBinding, idempotency_key: str
    ) -> None: ...

    def publish_backup(
        self, binding: SuccessorBinding, idempotency_key: str
    ) -> None: ...

    def publish_descriptor(
        self, binding: SuccessorBinding, idempotency_key: str
    ) -> None: ...

    def verify_readiness(
        self, binding: SuccessorBinding, idempotency_key: str
    ) -> None: ...

    def activate_successor(
        self, binding: SuccessorBinding, idempotency_key: str
    ) -> None: ...

    def verify_successor_recovery(
        self, binding: SuccessorBinding, idempotency_key: str
    ) -> None: ...

    def retire_predecessor(
        self, binding: SuccessorBinding, idempotency_key: str
    ) -> None: ...

    def rotate_protected_key(
        self, binding: SuccessorBinding, idempotency_key: str
    ) -> None: ...

    def authorized_recoverable_epochs(
        self, binding: SuccessorBinding
    ) -> frozenset[int]: ...


class DurableSuccessorPublication:
    """Persist public progress and retry one exact external effect per phase."""

    def __init__(self, journal_path: Path) -> None:
        self._path = journal_path
        self._lock = threading.RLock()
        journal_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS successor_operations(
                       operation_id TEXT PRIMARY KEY,
                       binding_bytes BLOB NOT NULL,
                       phase TEXT NOT NULL,
                       journal_version TEXT NOT NULL
                   )"""
            )

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self._path, timeout=5)
        try:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA synchronous=FULL")
            yield connection
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def _binding_bytes(binding: SuccessorBinding) -> bytes:
        return encode(binding.to_dict())

    def begin(self, binding: SuccessorBinding) -> SuccessorOperationState:
        if not isinstance(binding, SuccessorBinding):
            raise SuccessorPublicationError("invalid successor binding")
        encoded = self._binding_bytes(binding)
        with self._lock, self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """SELECT binding_bytes, phase, journal_version
                   FROM successor_operations WHERE operation_id = ?""",
                (binding.operation_id,),
            ).fetchone()
            if row is None:
                connection.execute(
                    """INSERT INTO successor_operations(
                           operation_id, binding_bytes, phase, journal_version
                       ) VALUES (?, ?, ?, ?)""",
                    (
                        binding.operation_id,
                        encoded,
                        SuccessorPhase.PRESERVE_ORIGINAL_KEY.value,
                        SUCCESSOR_PUBLICATION_JOURNAL,
                    ),
                )
                phase = SuccessorPhase.PRESERVE_ORIGINAL_KEY
            else:
                if bytes(row[0]) != encoded or row[2] != SUCCESSOR_PUBLICATION_JOURNAL:
                    raise SuccessorPublicationError(
                        "successor operation binding changed"
                    )
                try:
                    phase = SuccessorPhase(row[1])
                except ValueError as exc:
                    raise SuccessorPublicationError(
                        "invalid successor journal phase"
                    ) from exc
        return SuccessorOperationState(binding=binding, phase=phase)

    @staticmethod
    def _idempotency_key(binding: SuccessorBinding, phase: SuccessorPhase) -> str:
        return hash_bytes(
            "LOCUS/successor-publication-action/v1",
            encode(binding.to_dict()),
            phase.value.encode("ascii"),
        ).hex()

    @staticmethod
    def _perform(
        backend: SuccessorPublicationBackend,
        binding: SuccessorBinding,
        phase: SuccessorPhase,
        idempotency_key: str,
    ) -> None:
        actions = {
            SuccessorPhase.PRESERVE_ORIGINAL_KEY: backend.preserve_original_key,
            SuccessorPhase.PREPARE_PARTIES: backend.prepare_parties,
            SuccessorPhase.PUBLISH_BACKUP: backend.publish_backup,
            SuccessorPhase.PUBLISH_DESCRIPTOR: backend.publish_descriptor,
            SuccessorPhase.VERIFY_READINESS: backend.verify_readiness,
            SuccessorPhase.ACTIVATE_SUCCESSOR: backend.activate_successor,
            SuccessorPhase.VERIFY_SUCCESSOR_RECOVERY: (
                backend.verify_successor_recovery
            ),
            SuccessorPhase.RETIRE_PREDECESSOR: backend.retire_predecessor,
        }
        if phase is SuccessorPhase.OPTIONAL_KEY_ROTATION:
            if binding.rotate_protected_key:
                backend.rotate_protected_key(binding, idempotency_key)
            return
        action = actions.get(phase)
        if action is None:
            raise SuccessorPublicationError("successor operation is already complete")
        action(binding, idempotency_key)

    @staticmethod
    def _verify_availability(
        backend: SuccessorPublicationBackend,
        binding: SuccessorBinding,
        completed_phase: SuccessorPhase,
    ) -> None:
        recoverable = backend.authorized_recoverable_epochs(binding)
        if not isinstance(recoverable, frozenset) or any(
            isinstance(epoch, bool) or not isinstance(epoch, int)
            for epoch in recoverable
        ):
            raise SuccessorPublicationError("invalid recoverability observation")
        if completed_phase in {
            SuccessorPhase.PRESERVE_ORIGINAL_KEY,
            SuccessorPhase.PREPARE_PARTIES,
            SuccessorPhase.PUBLISH_BACKUP,
            SuccessorPhase.PUBLISH_DESCRIPTOR,
            SuccessorPhase.VERIFY_READINESS,
            SuccessorPhase.VERIFY_SUCCESSOR_RECOVERY,
        }:
            if binding.predecessor_epoch not in recoverable:
                raise SuccessorPublicationError("predecessor recovery is unavailable")
        elif completed_phase in {
            SuccessorPhase.ACTIVATE_SUCCESSOR,
            SuccessorPhase.RETIRE_PREDECESSOR,
            SuccessorPhase.OPTIONAL_KEY_ROTATION,
        }:
            if binding.successor_epoch not in recoverable:
                raise SuccessorPublicationError("successor recovery is unavailable")

    def advance(
        self,
        binding: SuccessorBinding,
        backend: SuccessorPublicationBackend,
    ) -> SuccessorOperationState:
        state = self.begin(binding)
        if state.phase is SuccessorPhase.COMPLETE:
            return state
        idempotency_key = self._idempotency_key(binding, state.phase)
        self._perform(backend, binding, state.phase, idempotency_key)
        self._verify_availability(backend, binding, state.phase)
        next_phase = PHASE_ORDER[PHASE_ORDER.index(state.phase) + 1]
        with self._lock, self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            cursor = connection.execute(
                """UPDATE successor_operations SET phase = ?
                   WHERE operation_id = ? AND binding_bytes = ? AND phase = ?
                         AND journal_version = ?""",
                (
                    next_phase.value,
                    binding.operation_id,
                    self._binding_bytes(binding),
                    state.phase.value,
                    SUCCESSOR_PUBLICATION_JOURNAL,
                ),
            )
            if cursor.rowcount != 1:
                row = connection.execute(
                    """SELECT binding_bytes, phase, journal_version
                       FROM successor_operations WHERE operation_id = ?""",
                    (binding.operation_id,),
                ).fetchone()
                if (
                    row is None
                    or bytes(row[0]) != self._binding_bytes(binding)
                    or row[2] != SUCCESSOR_PUBLICATION_JOURNAL
                ):
                    raise SuccessorPublicationError(
                        "successor journal changed during transition"
                    )
                try:
                    current_phase = SuccessorPhase(row[1])
                except ValueError as exc:
                    raise SuccessorPublicationError(
                        "invalid successor journal phase"
                    ) from exc
                if PHASE_ORDER.index(current_phase) < PHASE_ORDER.index(next_phase):
                    raise SuccessorPublicationError(
                        "successor journal changed during transition"
                    )
                return SuccessorOperationState(binding=binding, phase=current_phase)
        return SuccessorOperationState(binding=binding, phase=next_phase)

    def run(
        self,
        binding: SuccessorBinding,
        backend: SuccessorPublicationBackend,
    ) -> SuccessorOperationState:
        state = self.begin(binding)
        while state.phase is not SuccessorPhase.COMPLETE:
            state = self.advance(binding, backend)
        return state


__all__ = [
    "DurableSuccessorPublication",
    "PHASE_ORDER",
    "SUCCESSOR_PUBLICATION_JOURNAL",
    "SuccessorBinding",
    "SuccessorOperationState",
    "SuccessorPhase",
    "SuccessorPublicationBackend",
    "SuccessorPublicationError",
]
