from __future__ import annotations

import dataclasses
import threading
import unittest

from locus.contracts import EnrollmentClientStateMachine, EnrollmentPhase
from locus.enrollment_state import (
    EnrollmentStateError,
    EnrollmentTransitionEvent,
    StableEnrollmentStateMachine,
)

BACKUP_ID = "11" * 16


def event(
    phase: EnrollmentPhase,
    *,
    suffix: str | None = None,
    backup_id: str | None = None,
    epoch: int | None = None,
) -> EnrollmentTransitionEvent:
    return EnrollmentTransitionEvent(
        event_id=f"event-{suffix or phase.value}",
        completed_phase=phase,
        backup_id=backup_id,
        epoch=epoch,
    )


class EnrollmentStateMachineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.machine = StableEnrollmentStateMachine()

    def test_complete_ordered_enrollment_and_exact_retries(self) -> None:
        self.assertIsInstance(self.machine, EnrollmentClientStateMachine)
        state = self.machine.begin("operation-1")
        self.assertEqual(self.machine.begin("operation-1"), state)
        for phase in (
            EnrollmentPhase.KEY,
            EnrollmentPhase.POLICY,
            EnrollmentPhase.SUITE_SETUP,
            EnrollmentPhase.KEY_WRAP,
        ):
            transition = event(phase)
            result = self.machine.advance(state, transition)
            self.assertEqual(self.machine.advance(state, transition), result)
            state = result
        publication = event(
            EnrollmentPhase.BACKUP_PUBLICATION,
            backup_id=BACKUP_ID,
            epoch=1,
        )
        state = self.machine.advance(state, publication)
        self.assertEqual(state.backup_id, BACKUP_ID)
        self.assertEqual(state.epoch, 1)
        for phase in (
            EnrollmentPhase.PARTY_PROVISIONING,
            EnrollmentPhase.DESCRIPTOR_PUBLICATION,
            EnrollmentPhase.RECEIPT,
            EnrollmentPhase.DISPOSAL,
        ):
            state = self.machine.advance(state, event(phase))
        self.assertEqual(state.phase, EnrollmentPhase.COMPLETE)
        with self.assertRaises(EnrollmentStateError):
            self.machine.advance(state, event(EnrollmentPhase.DISPOSAL, suffix="again"))

    def test_skips_stale_states_and_event_reuse_fail_closed(self) -> None:
        initial = self.machine.begin("operation-2")
        with self.assertRaises(EnrollmentStateError):
            self.machine.advance(initial, event(EnrollmentPhase.POLICY))
        first = event(EnrollmentPhase.KEY, suffix="shared")
        policy = self.machine.advance(initial, first)
        with self.assertRaises(EnrollmentStateError):
            self.machine.advance(initial, event(EnrollmentPhase.KEY, suffix="new"))
        with self.assertRaises(EnrollmentStateError):
            self.machine.advance(
                policy,
                event(EnrollmentPhase.POLICY, suffix="shared"),
            )
        with self.assertRaises(EnrollmentStateError):
            self.machine.advance(policy, object())

    def test_backup_binding_is_required_once_and_cannot_change(self) -> None:
        state = self.machine.begin("operation-3")
        for phase in (
            EnrollmentPhase.KEY,
            EnrollmentPhase.POLICY,
            EnrollmentPhase.SUITE_SETUP,
            EnrollmentPhase.KEY_WRAP,
        ):
            state = self.machine.advance(state, event(phase))
        with self.assertRaises(EnrollmentStateError):
            self.machine.advance(state, event(EnrollmentPhase.BACKUP_PUBLICATION))
        state = self.machine.advance(
            state,
            event(
                EnrollmentPhase.BACKUP_PUBLICATION,
                suffix="bound",
                backup_id=BACKUP_ID,
                epoch=1,
            ),
        )
        with self.assertRaises(EnrollmentStateError):
            self.machine.advance(
                state,
                event(
                    EnrollmentPhase.PARTY_PROVISIONING,
                    backup_id="22" * 16,
                    epoch=2,
                ),
            )

    def test_concurrent_exact_event_has_one_idempotent_result(self) -> None:
        state = self.machine.begin("operation-4")
        transition = event(EnrollmentPhase.KEY)
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
        self.assertEqual(results[0].phase, EnrollmentPhase.POLICY)

    def test_retry_state_and_events_have_no_secret_payload_fields(self) -> None:
        state_fields = {
            field.name for field in dataclasses.fields(self.machine.begin("op"))
        }
        event_fields = {
            field.name for field in dataclasses.fields(event(EnrollmentPhase.KEY))
        }
        self.assertEqual(state_fields, {"operation_id", "phase", "backup_id", "epoch"})
        self.assertEqual(
            event_fields,
            {"event_id", "completed_phase", "backup_id", "epoch"},
        )
        for forbidden in (
            "private_key",
            "cue",
            "password",
            "secret",
            "share",
            "credential",
        ):
            self.assertNotIn(forbidden, state_fields | event_fields)


if __name__ == "__main__":
    unittest.main()
