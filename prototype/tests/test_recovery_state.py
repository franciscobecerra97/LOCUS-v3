from __future__ import annotations

import dataclasses
import threading
import unittest

from locus.contracts import RecoveryClientStateMachine, RecoveryPhase
from locus.recovery_state import (
    RecoveryRejected,
    RecoveryStateError,
    RecoveryTransitionEvent,
    StableRecoveryStateMachine,
    normalize_recovery_failure,
)

BACKUP_ID = "11" * 16


def event(
    phase: RecoveryPhase,
    *,
    suffix: str | None = None,
    backup_id: str | None = None,
    epoch: int | None = None,
) -> RecoveryTransitionEvent:
    return RecoveryTransitionEvent(
        event_id=f"event-{suffix or phase.value}",
        completed_phase=phase,
        backup_id=backup_id,
        epoch=epoch,
    )


class RecoveryStateMachineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.machine = StableRecoveryStateMachine()

    def test_complete_ordered_recovery_and_exact_retries(self) -> None:
        self.assertIsInstance(self.machine, RecoveryClientStateMachine)
        state = self.machine.begin("operation-1", "recovery-handle-1")
        self.assertEqual(self.machine.begin("operation-1", "recovery-handle-1"), state)
        state = self.machine.advance(state, event(RecoveryPhase.BOOTSTRAP))
        descriptor = event(
            RecoveryPhase.DESCRIPTOR_VERIFICATION,
            backup_id=BACKUP_ID,
            epoch=3,
        )
        result = self.machine.advance(state, descriptor)
        self.assertEqual(self.machine.advance(state, descriptor), result)
        state = result
        for phase in (
            RecoveryPhase.CURRENT_STATE,
            RecoveryPhase.BACKUP_RETRIEVAL,
            RecoveryPhase.POLICY,
            RecoveryPhase.THRESHOLD_SELECTION,
            RecoveryPhase.AUTHORIZATION,
            RecoveryPhase.SUITE_RECOVERY,
            RecoveryPhase.DECRYPTION,
            RecoveryPhase.KEY_IDENTITY,
            RecoveryPhase.SUCCESSOR,
        ):
            state = self.machine.advance(state, event(phase))
        self.assertEqual(state.phase, RecoveryPhase.COMPLETE)
        self.assertEqual(state.backup_id, BACKUP_ID)
        self.assertEqual(state.epoch, 3)

    def test_skip_stale_rebinding_and_event_reuse_fail_closed(self) -> None:
        initial = self.machine.begin("operation-2", "recovery-handle-2")
        with self.assertRaises(RecoveryStateError):
            self.machine.begin("operation-2", "other-handle")
        with self.assertRaises(RecoveryStateError):
            self.machine.advance(initial, event(RecoveryPhase.CURRENT_STATE))
        descriptor_phase = self.machine.advance(
            initial, event(RecoveryPhase.BOOTSTRAP, suffix="shared")
        )
        with self.assertRaises(RecoveryStateError):
            self.machine.advance(initial, event(RecoveryPhase.BOOTSTRAP, suffix="new"))
        with self.assertRaises(RecoveryStateError):
            self.machine.advance(
                descriptor_phase,
                event(RecoveryPhase.DESCRIPTOR_VERIFICATION, suffix="shared"),
            )
        with self.assertRaises(RecoveryStateError):
            self.machine.advance(descriptor_phase, object())

    def test_descriptor_binding_is_required_and_immutable(self) -> None:
        state = self.machine.begin("operation-3", "recovery-handle-3")
        state = self.machine.advance(state, event(RecoveryPhase.BOOTSTRAP))
        with self.assertRaises(RecoveryStateError):
            self.machine.advance(state, event(RecoveryPhase.DESCRIPTOR_VERIFICATION))
        state = self.machine.advance(
            state,
            event(
                RecoveryPhase.DESCRIPTOR_VERIFICATION,
                suffix="bound",
                backup_id=BACKUP_ID,
                epoch=1,
            ),
        )
        with self.assertRaises(RecoveryStateError):
            self.machine.advance(
                state,
                event(
                    RecoveryPhase.CURRENT_STATE,
                    backup_id="22" * 16,
                    epoch=2,
                ),
            )

    def test_concurrent_exact_event_converges(self) -> None:
        state = self.machine.begin("operation-4", "recovery-handle-4")
        transition = event(RecoveryPhase.BOOTSTRAP)
        barrier = threading.Barrier(3)
        results = []

        def advance() -> None:
            barrier.wait()
            results.append(self.machine.advance(state, transition))

        threads = [threading.Thread(target=advance) for _ in range(2)]
        for thread in threads:
            thread.start()
        barrier.wait()
        for thread in threads:
            thread.join()
        self.assertEqual(results[0], results[1])
        self.assertEqual(results[0].phase, RecoveryPhase.DESCRIPTOR_VERIFICATION)

    def test_retry_state_has_no_secret_or_final_outcome_field(self) -> None:
        state_fields = {
            field.name
            for field in dataclasses.fields(
                self.machine.begin("operation-5", "recovery-handle-5")
            )
        }
        event_fields = {
            field.name for field in dataclasses.fields(event(RecoveryPhase.BOOTSTRAP))
        }
        self.assertEqual(
            state_fields,
            {"operation_id", "phase", "recovery_handle", "backup_id", "epoch"},
        )
        self.assertEqual(
            event_fields, {"event_id", "completed_phase", "backup_id", "epoch"}
        )
        for forbidden in (
            "private_key",
            "cue",
            "password",
            "secret",
            "share",
            "credential",
            "suite_success",
            "aead_success",
            "outcome",
        ):
            self.assertNotIn(forbidden, state_fields | event_fields)

    def test_wrong_input_and_malformed_remote_state_share_public_error(self) -> None:
        wrong_input = normalize_recovery_failure(ValueError("wrong cue details"))
        malformed = normalize_recovery_failure(ValueError("malformed party details"))
        self.assertIsInstance(wrong_input, RecoveryRejected)
        self.assertEqual(type(wrong_input), type(malformed))
        self.assertEqual(str(wrong_input), "recovery rejected")
        self.assertEqual(str(malformed), "recovery rejected")
        self.assertIsNone(wrong_input.__cause__)


if __name__ == "__main__":
    unittest.main()
