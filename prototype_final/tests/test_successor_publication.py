from __future__ import annotations

import hashlib
import tempfile
import unittest
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

from locus.successor_publication import (
    PHASE_ORDER,
    DurableSuccessorPublication,
    SuccessorBinding,
    SuccessorPhase,
    SuccessorPublicationError,
)

ORIGINAL_KEY = b"synthetic-original-protected-key"


class InjectedCrash(RuntimeError):
    pass


class SyntheticSuccessorBackend:
    """Synthetic adapter that models the frozen atomic party cutover."""

    def __init__(
        self,
        *,
        original_key: bytes = ORIGINAL_KEY,
        crash_after: SuccessorPhase | None = None,
    ) -> None:
        self.original_key = original_key
        self.crash_after = crash_after
        self.completed: dict[SuccessorPhase, str] = {}
        self.recoverable = {1}
        self.history: list[frozenset[int]] = []
        self.activation_count = 0
        self.retirement_confirmation_count = 0
        self.rotation_count = 0
        self.preserved = False
        self.parties_prepared = False
        self.backup_published = False
        self.descriptor_published = False
        self.ready = False
        self.successor_verified = False

    def _effect(
        self,
        phase: SuccessorPhase,
        idempotency_key: str,
        action: Callable[[], None],
    ) -> None:
        prior = self.completed.get(phase)
        if prior is not None:
            if prior != idempotency_key:
                raise SuccessorPublicationError("stale successor authorization")
            return
        action()
        self.completed[phase] = idempotency_key
        self.history.append(frozenset(self.recoverable))
        if self.crash_after is phase:
            self.crash_after = None
            raise InjectedCrash(phase.value)

    def preserve_original_key(
        self, binding: SuccessorBinding, idempotency_key: str
    ) -> None:
        def action() -> None:
            if (
                hashlib.sha256(self.original_key).hexdigest()
                != binding.recovered_key_digest
            ):
                raise SuccessorPublicationError("recovered key identity changed")
            self.preserved = True

        self._effect(SuccessorPhase.PRESERVE_ORIGINAL_KEY, idempotency_key, action)

    def prepare_parties(self, binding: SuccessorBinding, idempotency_key: str) -> None:
        del binding

        def action() -> None:
            if not self.preserved:
                raise SuccessorPublicationError("original key was not preserved")
            self.parties_prepared = True

        self._effect(SuccessorPhase.PREPARE_PARTIES, idempotency_key, action)

    def publish_backup(self, binding: SuccessorBinding, idempotency_key: str) -> None:
        del binding

        def action() -> None:
            if not self.parties_prepared:
                raise SuccessorPublicationError("parties are not prepared")
            self.backup_published = True

        self._effect(SuccessorPhase.PUBLISH_BACKUP, idempotency_key, action)

    def publish_descriptor(
        self, binding: SuccessorBinding, idempotency_key: str
    ) -> None:
        del binding

        def action() -> None:
            if not self.backup_published:
                raise SuccessorPublicationError("successor backup is not published")
            self.descriptor_published = True

        self._effect(SuccessorPhase.PUBLISH_DESCRIPTOR, idempotency_key, action)

    def verify_readiness(self, binding: SuccessorBinding, idempotency_key: str) -> None:
        del binding

        def action() -> None:
            if not (self.parties_prepared and self.descriptor_published):
                raise SuccessorPublicationError("successor is not durably ready")
            self.ready = True

        self._effect(SuccessorPhase.VERIFY_READINESS, idempotency_key, action)

    def activate_successor(
        self, binding: SuccessorBinding, idempotency_key: str
    ) -> None:
        def action() -> None:
            if not self.ready or not self.successor_verified:
                raise SuccessorPublicationError("successor is not ready")
            # This mirrors PartyStore.activate_successor_epoch: one certified
            # transaction retires the predecessor and activates the successor.
            self.recoverable = {binding.successor_epoch}
            self.activation_count += 1

        self._effect(SuccessorPhase.ACTIVATE_SUCCESSOR, idempotency_key, action)

    def verify_successor_recovery(
        self, binding: SuccessorBinding, idempotency_key: str
    ) -> None:
        def action() -> None:
            if not self.ready:
                raise SuccessorPublicationError("successor is not ready")
            if (
                hashlib.sha256(self.original_key).hexdigest()
                != binding.recovered_key_digest
            ):
                raise SuccessorPublicationError("successor key identity changed")
            self.successor_verified = True

        self._effect(SuccessorPhase.VERIFY_SUCCESSOR_RECOVERY, idempotency_key, action)

    def retire_predecessor(
        self, binding: SuccessorBinding, idempotency_key: str
    ) -> None:
        def action() -> None:
            if (
                not self.successor_verified
                or binding.predecessor_epoch in self.recoverable
                or binding.successor_epoch not in self.recoverable
            ):
                raise SuccessorPublicationError("retirement is not certified")
            self.retirement_confirmation_count += 1

        self._effect(SuccessorPhase.RETIRE_PREDECESSOR, idempotency_key, action)

    def rotate_protected_key(
        self, binding: SuccessorBinding, idempotency_key: str
    ) -> None:
        def action() -> None:
            if not binding.rotate_protected_key or not self.successor_verified:
                raise SuccessorPublicationError("key rotation was not authorized")
            self.rotation_count += 1

        self._effect(SuccessorPhase.OPTIONAL_KEY_ROTATION, idempotency_key, action)

    def authorized_recoverable_epochs(
        self, binding: SuccessorBinding
    ) -> frozenset[int]:
        del binding
        return frozenset(self.recoverable)


def binding(*, rotate: bool = False) -> SuccessorBinding:
    return SuccessorBinding(
        operation_id="successor-operation-1",
        backup_id="81" * 16,
        predecessor_epoch=1,
        successor_epoch=2,
        successor_configuration_digest="82" * 32,
        successor_backup_digest="83" * 32,
        successor_descriptor_digest="84" * 32,
        recovered_key_digest=hashlib.sha256(ORIGINAL_KEY).hexdigest(),
        rotate_protected_key=rotate,
    )


class DurableSuccessorPublicationTests(unittest.TestCase):
    def test_default_path_preserves_original_key_without_rotation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            journal = Path(temporary) / "successor.sqlite3"
            coordinator = DurableSuccessorPublication(journal)
            backend = SyntheticSuccessorBackend()
            result = coordinator.run(binding(), backend)

            self.assertEqual(result.phase, SuccessorPhase.COMPLETE)
            self.assertEqual(backend.recoverable, {2})
            self.assertEqual(backend.activation_count, 1)
            self.assertEqual(backend.retirement_confirmation_count, 1)
            self.assertEqual(backend.rotation_count, 0)
            self.assertTrue(backend.successor_verified)
            self.assertNotIn(ORIGINAL_KEY, journal.read_bytes())

    def test_crash_after_every_effect_resumes_without_double_activation(self) -> None:
        for crash_phase in PHASE_ORDER[:-1]:
            with (
                self.subTest(phase=crash_phase.value),
                tempfile.TemporaryDirectory() as temporary,
            ):
                journal = Path(temporary) / "successor.sqlite3"
                coordinator = DurableSuccessorPublication(journal)
                backend = SyntheticSuccessorBackend(
                    crash_after=crash_phase,
                )
                operation = binding(rotate=True)
                with self.assertRaises(InjectedCrash):
                    coordinator.run(operation, backend)
                self.assertTrue(backend.recoverable)

                resumed = DurableSuccessorPublication(journal)
                self.assertEqual(
                    resumed.run(operation, backend).phase,
                    SuccessorPhase.COMPLETE,
                )
                self.assertEqual(backend.activation_count, 1)
                self.assertEqual(backend.retirement_confirmation_count, 1)
                self.assertEqual(backend.rotation_count, 1)
                self.assertTrue(all(observation for observation in backend.history))

    def test_operation_binding_cannot_be_changed_on_retry(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            coordinator = DurableSuccessorPublication(
                Path(temporary) / "successor.sqlite3"
            )
            operation = binding()
            backend = SyntheticSuccessorBackend()
            coordinator.advance(operation, backend)
            stale = replace(
                operation,
                successor_configuration_digest="85" * 32,
            )
            with self.assertRaisesRegex(
                SuccessorPublicationError, "operation binding changed"
            ):
                coordinator.run(stale, backend)

    def test_wrong_recovered_key_fails_before_party_preparation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            coordinator = DurableSuccessorPublication(
                Path(temporary) / "successor.sqlite3"
            )
            backend = SyntheticSuccessorBackend(original_key=b"wrong-key")
            with self.assertRaisesRegex(
                SuccessorPublicationError, "recovered key identity changed"
            ):
                coordinator.run(binding(), backend)
            self.assertFalse(backend.parties_prepared)
            self.assertEqual(
                coordinator.begin(binding()).phase,
                SuccessorPhase.PRESERVE_ORIGINAL_KEY,
            )


if __name__ == "__main__":
    unittest.main()
