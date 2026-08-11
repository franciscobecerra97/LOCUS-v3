from __future__ import annotations

import hashlib
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from locus.appss_formats import APPSS_SUITE_ID, YI_SUITE_ID
from locus.client_api import CLIENT_API_VERSION, ClientApiError, LocalResearchClientApi
from locus.paired_deployment_profiles import (
    PAIRED_DEPLOYMENT_2_OF_3,
    PAIRED_DEPLOYMENT_3_OF_5,
)
from locus.successor_publication import (
    PHASE_ORDER,
    DurableSuccessorPublication,
    SuccessorBinding,
    SuccessorPhase,
    SuccessorPublicationError,
)

NOW = 2_000_000_000
SYNTHETIC_KEY = bytes(range(32))
RECOVERY_INPUT = ["ada@example.com", "grace@example.net", "linus@example.org"]


def _private(value: int) -> Ed25519PrivateKey:
    return Ed25519PrivateKey.from_private_bytes(bytes([value]) * 32)


def _client() -> LocalResearchClientApi:
    return LocalResearchClientApi(
        clock=lambda: NOW,
        operator_signer=_private(9),
        admission_signer=_private(10),
        party_signers={index: _private(index) for index in range(1, 6)},
    )


def _enrollment(operation_id: str) -> dict[str, object]:
    return {
        "api_version": CLIENT_API_VERSION,
        "deployment_profile_id": PAIRED_DEPLOYMENT_2_OF_3,
        "operation_id": operation_id,
        "policy_id": "LOCUS-canonical-email-set-v1",
        "protected_key": {"hex": SYNTHETIC_KEY.hex(), "mode": "import-synthetic"},
        "recovery_input": RECOVERY_INPUT,
        "suite_id": YI_SUITE_ID,
    }


class _InjectedCrash(RuntimeError):
    pass


class _CrashBackend:
    def __init__(self, crash_after: SuccessorPhase) -> None:
        self.crash_after = crash_after
        self.completed: dict[SuccessorPhase, str] = {}
        self.recoverable = frozenset({1})
        self.activations = 0
        self.retirements = 0
        self.rotations = 0

    def _effect(
        self,
        phase: SuccessorPhase,
        key: str,
        binding: SuccessorBinding,
    ) -> None:
        previous = self.completed.get(phase)
        if previous is not None:
            if previous != key:
                raise SuccessorPublicationError("changed successor retry")
            return
        if phase is SuccessorPhase.ACTIVATE_SUCCESSOR:
            self.recoverable = frozenset({binding.successor_epoch})
            self.activations += 1
        elif phase is SuccessorPhase.RETIRE_PREDECESSOR:
            self.retirements += 1
        elif phase is SuccessorPhase.OPTIONAL_KEY_ROTATION:
            self.rotations += 1
        self.completed[phase] = key
        if self.crash_after is phase:
            raise _InjectedCrash(phase.value)

    def preserve_original_key(self, binding: SuccessorBinding, key: str) -> None:
        self._effect(SuccessorPhase.PRESERVE_ORIGINAL_KEY, key, binding)

    def prepare_parties(self, binding: SuccessorBinding, key: str) -> None:
        self._effect(SuccessorPhase.PREPARE_PARTIES, key, binding)

    def publish_backup(self, binding: SuccessorBinding, key: str) -> None:
        self._effect(SuccessorPhase.PUBLISH_BACKUP, key, binding)

    def publish_descriptor(self, binding: SuccessorBinding, key: str) -> None:
        self._effect(SuccessorPhase.PUBLISH_DESCRIPTOR, key, binding)

    def verify_readiness(self, binding: SuccessorBinding, key: str) -> None:
        self._effect(SuccessorPhase.VERIFY_READINESS, key, binding)

    def verify_successor_recovery(self, binding: SuccessorBinding, key: str) -> None:
        self._effect(SuccessorPhase.VERIFY_SUCCESSOR_RECOVERY, key, binding)

    def activate_successor(self, binding: SuccessorBinding, key: str) -> None:
        self._effect(SuccessorPhase.ACTIVATE_SUCCESSOR, key, binding)

    def retire_predecessor(self, binding: SuccessorBinding, key: str) -> None:
        self._effect(SuccessorPhase.RETIRE_PREDECESSOR, key, binding)

    def rotate_protected_key(self, binding: SuccessorBinding, key: str) -> None:
        self._effect(SuccessorPhase.OPTIONAL_KEY_ROTATION, key, binding)

    def authorized_recoverable_epochs(
        self, _binding: SuccessorBinding
    ) -> frozenset[int]:
        return self.recoverable


def _binding() -> SuccessorBinding:
    return SuccessorBinding(
        operation_id="successor-regression",
        backup_id="81" * 16,
        predecessor_epoch=1,
        successor_epoch=2,
        successor_configuration_digest="82" * 32,
        successor_backup_digest="83" * 32,
        successor_descriptor_digest="84" * 32,
        recovered_key_digest=hashlib.sha256(SYNTHETIC_KEY).hexdigest(),
        rotate_protected_key=True,
    )


class SuccessorRegressionTests(unittest.TestCase):
    def test_same_and_cross_suite_successors_preserve_key_and_retire_old_epoch(
        self,
    ) -> None:
        for index, successor_suite in enumerate((YI_SUITE_ID, APPSS_SUITE_ID)):
            with self.subTest(successor_suite=successor_suite):
                client = _client()
                predecessor = client.enroll(_enrollment(f"predecessor-{index}"))
                predecessor_receipt = predecessor.public_value()["receipt"]
                successor = client.create_successor(
                    {
                        "api_version": CLIENT_API_VERSION,
                        "operation_id": f"successor-{index}",
                        "receipt": predecessor_receipt,
                        "recovery_input": RECOVERY_INPUT,
                        "rotate_protected_key": False,
                        "successor_deployment_profile_id": (PAIRED_DEPLOYMENT_3_OF_5),
                        "successor_suite_id": successor_suite,
                    }
                )
                recovered = client.recover(
                    {
                        "api_version": CLIENT_API_VERSION,
                        "operation_id": f"recover-successor-{index}",
                        "receipt": successor.enrollment.public_value()["receipt"],
                        "recovery_input": RECOVERY_INPUT,
                    }
                )
                self.assertEqual(recovered.protected_key, SYNTHETIC_KEY)
                self.assertEqual(recovered.suite_id, successor_suite)
                with self.assertRaises(ClientApiError):
                    client.recover(
                        {
                            "api_version": CLIENT_API_VERSION,
                            "operation_id": f"recover-retired-{index}",
                            "receipt": predecessor_receipt,
                            "recovery_input": RECOVERY_INPUT,
                        }
                    )

    def test_every_successor_effect_resumes_once_after_crash(self) -> None:
        for phase in PHASE_ORDER[:-1]:
            with self.subTest(phase=phase.value), tempfile.TemporaryDirectory() as tmp:
                binding = replace(_binding(), operation_id=f"crash-{phase.value}")
                backend = _CrashBackend(phase)
                journal = Path(tmp) / "successor.sqlite3"
                with self.assertRaises(_InjectedCrash):
                    DurableSuccessorPublication(journal).run(binding, backend)
                completed = DurableSuccessorPublication(journal).run(binding, backend)
                self.assertEqual(completed.phase, SuccessorPhase.COMPLETE)
                self.assertEqual(backend.activations, 1)
                self.assertEqual(backend.retirements, 1)
                self.assertEqual(backend.rotations, 1)

    def test_changed_successor_binding_is_rejected_on_retry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            coordinator = DurableSuccessorPublication(Path(tmp) / "successor.sqlite3")
            original = _binding()
            coordinator.begin(original)
            changed = replace(original, successor_backup_digest="85" * 32)
            with self.assertRaisesRegex(
                SuccessorPublicationError, "operation binding changed"
            ):
                coordinator.begin(changed)


if __name__ == "__main__":
    unittest.main()
