"""P3.1 secret-free enrollment client state machine."""

from __future__ import annotations

import threading
from dataclasses import dataclass

from .codec import encode
from .contracts import (
    ContractError,
    EnrollmentClientState,
    EnrollmentClientStateMachine,
    EnrollmentPhase,
)


class EnrollmentStateError(ContractError):
    """An enrollment transition is unsafe, stale, or non-idempotent."""


PHASE_ORDER = (
    EnrollmentPhase.KEY,
    EnrollmentPhase.POLICY,
    EnrollmentPhase.SUITE_SETUP,
    EnrollmentPhase.KEY_WRAP,
    EnrollmentPhase.BACKUP_PUBLICATION,
    EnrollmentPhase.PARTY_PROVISIONING,
    EnrollmentPhase.DESCRIPTOR_PUBLICATION,
    EnrollmentPhase.RECEIPT,
    EnrollmentPhase.DISPOSAL,
    EnrollmentPhase.COMPLETE,
)


def _identifier(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or len(value) > 255
        or not value.isascii()
        or any(ord(character) < 0x21 or ord(character) > 0x7E for character in value)
    ):
        raise EnrollmentStateError(f"invalid {label}")
    return value


@dataclass(frozen=True)
class EnrollmentTransitionEvent:
    event_id: str
    completed_phase: EnrollmentPhase
    backup_id: str | None = None
    epoch: int | None = None

    def __post_init__(self) -> None:
        _identifier(self.event_id, "enrollment event identifier")
        if not isinstance(self.completed_phase, EnrollmentPhase):
            raise EnrollmentStateError("invalid completed enrollment phase")
        if self.completed_phase is EnrollmentPhase.COMPLETE:
            raise EnrollmentStateError("complete is not a transition event")
        if (self.backup_id is None) != (self.epoch is None):
            raise EnrollmentStateError("incomplete event epoch binding")
        if self.backup_id is not None:
            _identifier(self.backup_id, "event backup identifier")
            if (
                isinstance(self.epoch, bool)
                or not isinstance(self.epoch, int)
                or self.epoch < 1
                or self.epoch > 2**63 - 1
            ):
                raise EnrollmentStateError("invalid event epoch")

    def fingerprint(self) -> bytes:
        return encode(
            {
                "backup_id": self.backup_id,
                "completed_phase": self.completed_phase.value,
                "epoch": self.epoch,
                "event_id": self.event_id,
            }
        )


class StableEnrollmentStateMachine:
    """Thread-safe public-metadata state machine implementing the P1.3 contract."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._states: dict[str, EnrollmentClientState] = {}
        self._events: dict[tuple[str, str], tuple[bytes, EnrollmentClientState]] = {}

    def begin(self, operation_id: str) -> EnrollmentClientState:
        _identifier(operation_id, "enrollment operation identifier")
        with self._lock:
            state = self._states.get(operation_id)
            if state is not None:
                return state
            state = EnrollmentClientState(
                operation_id=operation_id,
                phase=EnrollmentPhase.KEY,
            )
            self._states[operation_id] = state
            return state

    def advance(
        self, state: EnrollmentClientState, event: object
    ) -> EnrollmentClientState:
        if not isinstance(state, EnrollmentClientState):
            raise EnrollmentStateError("invalid enrollment state")
        if not isinstance(event, EnrollmentTransitionEvent):
            raise EnrollmentStateError("invalid enrollment transition event")
        key = (state.operation_id, event.event_id)
        fingerprint = event.fingerprint()
        with self._lock:
            prior = self._events.get(key)
            if prior is not None:
                prior_fingerprint, prior_result = prior
                if prior_fingerprint != fingerprint:
                    raise EnrollmentStateError("enrollment event identifier was reused")
                return prior_result
            current = self._states.get(state.operation_id)
            if current is None or current != state:
                raise EnrollmentStateError("stale or unknown enrollment state")
            if current.phase is EnrollmentPhase.COMPLETE:
                raise EnrollmentStateError("enrollment is already complete")
            if event.completed_phase is not current.phase:
                raise EnrollmentStateError("enrollment phase was skipped or reordered")
            index = PHASE_ORDER.index(current.phase)
            next_phase = PHASE_ORDER[index + 1]
            backup_id = current.backup_id
            epoch = current.epoch
            if current.phase is EnrollmentPhase.BACKUP_PUBLICATION:
                if event.backup_id is None:
                    raise EnrollmentStateError("backup publication lacks epoch binding")
                backup_id, epoch = event.backup_id, event.epoch
            elif event.backup_id is not None and (
                event.backup_id != backup_id or event.epoch != epoch
            ):
                raise EnrollmentStateError("enrollment epoch binding changed")
            result = EnrollmentClientState(
                operation_id=current.operation_id,
                phase=next_phase,
                backup_id=backup_id,
                epoch=epoch,
            )
            self._states[state.operation_id] = result
            self._events[key] = (fingerprint, result)
            return result


assert isinstance(StableEnrollmentStateMachine(), EnrollmentClientStateMachine)


__all__ = [
    "EnrollmentStateError",
    "EnrollmentTransitionEvent",
    "PHASE_ORDER",
    "StableEnrollmentStateMachine",
]
