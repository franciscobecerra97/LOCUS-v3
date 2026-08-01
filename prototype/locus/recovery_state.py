"""P4.1 secret-free clean-client recovery state machine."""

from __future__ import annotations

import threading
from dataclasses import dataclass

from .codec import encode
from .contracts import (
    ContractError,
    RecoveryClientState,
    RecoveryClientStateMachine,
    RecoveryPhase,
)


class RecoveryStateError(ContractError):
    """A recovery transition is unsafe, stale, or non-idempotent."""


class RecoveryRejected(RecoveryStateError):
    """The single public rejection for secret-dependent and malformed input."""

    def __init__(self) -> None:
        super().__init__("recovery rejected")


PHASE_ORDER = (
    RecoveryPhase.BOOTSTRAP,
    RecoveryPhase.DESCRIPTOR_VERIFICATION,
    RecoveryPhase.CURRENT_STATE,
    RecoveryPhase.BACKUP_RETRIEVAL,
    RecoveryPhase.POLICY,
    RecoveryPhase.THRESHOLD_SELECTION,
    RecoveryPhase.AUTHORIZATION,
    RecoveryPhase.SUITE_RECOVERY,
    RecoveryPhase.DECRYPTION,
    RecoveryPhase.KEY_IDENTITY,
    RecoveryPhase.SUCCESSOR,
    RecoveryPhase.COMPLETE,
)


def _identifier(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or len(value) > 255
        or not value.isascii()
        or any(ord(character) < 0x21 or ord(character) > 0x7E for character in value)
    ):
        raise RecoveryStateError(f"invalid {label}")
    return value


@dataclass(frozen=True)
class RecoveryTransitionEvent:
    """One public completion marker; secret outcomes never enter retry state."""

    event_id: str
    completed_phase: RecoveryPhase
    backup_id: str | None = None
    epoch: int | None = None

    def __post_init__(self) -> None:
        _identifier(self.event_id, "recovery event identifier")
        if not isinstance(self.completed_phase, RecoveryPhase):
            raise RecoveryStateError("invalid completed recovery phase")
        if self.completed_phase is RecoveryPhase.COMPLETE:
            raise RecoveryStateError("complete is not a transition event")
        if (self.backup_id is None) != (self.epoch is None):
            raise RecoveryStateError("incomplete recovery event binding")
        if self.backup_id is not None:
            _identifier(self.backup_id, "recovery event backup identifier")
            if (
                isinstance(self.epoch, bool)
                or not isinstance(self.epoch, int)
                or self.epoch < 1
                or self.epoch > 2**63 - 1
            ):
                raise RecoveryStateError("invalid recovery event epoch")

    def fingerprint(self) -> bytes:
        return encode(
            {
                "backup_id": self.backup_id,
                "completed_phase": self.completed_phase.value,
                "epoch": self.epoch,
                "event_id": self.event_id,
            }
        )


class StableRecoveryStateMachine:
    """Thread-safe P1.3 recovery state machine with exact event retries."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._states: dict[str, RecoveryClientState] = {}
        self._events: dict[tuple[str, str], tuple[bytes, RecoveryClientState]] = {}

    def begin(self, operation_id: str, recovery_handle: str) -> RecoveryClientState:
        _identifier(operation_id, "recovery operation identifier")
        _identifier(recovery_handle, "recovery handle")
        with self._lock:
            state = self._states.get(operation_id)
            if state is not None:
                if state.recovery_handle != recovery_handle:
                    raise RecoveryStateError("recovery operation binding changed")
                return state
            state = RecoveryClientState(
                operation_id=operation_id,
                phase=RecoveryPhase.BOOTSTRAP,
                recovery_handle=recovery_handle,
            )
            self._states[operation_id] = state
            return state

    def advance(self, state: RecoveryClientState, event: object) -> RecoveryClientState:
        if not isinstance(state, RecoveryClientState):
            raise RecoveryStateError("invalid recovery state")
        if not isinstance(event, RecoveryTransitionEvent):
            raise RecoveryStateError("invalid recovery transition event")
        key = (state.operation_id, event.event_id)
        fingerprint = event.fingerprint()
        with self._lock:
            prior = self._events.get(key)
            if prior is not None:
                prior_fingerprint, prior_result = prior
                if prior_fingerprint != fingerprint:
                    raise RecoveryStateError("recovery event identifier was reused")
                return prior_result
            current = self._states.get(state.operation_id)
            if current is None or current != state:
                raise RecoveryStateError("stale or unknown recovery state")
            if current.phase is RecoveryPhase.COMPLETE:
                raise RecoveryStateError("recovery is already complete")
            if event.completed_phase is not current.phase:
                raise RecoveryStateError("recovery phase was skipped or reordered")
            backup_id = current.backup_id
            epoch = current.epoch
            if current.phase is RecoveryPhase.DESCRIPTOR_VERIFICATION:
                if event.backup_id is None:
                    raise RecoveryStateError(
                        "descriptor verification lacks epoch binding"
                    )
                backup_id, epoch = event.backup_id, event.epoch
            elif event.backup_id is not None and (
                event.backup_id != backup_id or event.epoch != epoch
            ):
                raise RecoveryStateError("recovery epoch binding changed")
            next_phase = PHASE_ORDER[PHASE_ORDER.index(current.phase) + 1]
            result = RecoveryClientState(
                operation_id=current.operation_id,
                phase=next_phase,
                recovery_handle=current.recovery_handle,
                backup_id=backup_id,
                epoch=epoch,
            )
            self._states[state.operation_id] = result
            self._events[key] = (fingerprint, result)
            return result


def normalize_recovery_failure(_error: BaseException) -> RecoveryRejected:
    """Collapse wrong input and malformed secret-path state to one public error."""

    return RecoveryRejected()


assert isinstance(StableRecoveryStateMachine(), RecoveryClientStateMachine)


__all__ = [
    "PHASE_ORDER",
    "RecoveryRejected",
    "RecoveryStateError",
    "RecoveryTransitionEvent",
    "StableRecoveryStateMachine",
    "normalize_recovery_failure",
]
