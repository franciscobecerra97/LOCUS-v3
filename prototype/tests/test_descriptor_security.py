from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from locus.contracts import CurrentDescriptorPointer
from locus.descriptor_security import (
    REPORT_VERSION,
    SCENARIOS,
    DescriptorSecurityReportError,
    build_descriptor_security_report,
    run_bounded_networkless_candidate_test,
    validate_descriptor_security_report,
)
from locus.descriptor_store import FilesystemDescriptorBundleStore
from locus.object_store import ObjectStale
from locus.recovery_bootstrap import (
    BootstrapFailureCode,
    RecoveryBootstrapError,
)
from locus.recovery_descriptor import (
    CURRENT_POINTER_VERSION,
    RecoveryDescriptorError,
    validate_descriptor_payload,
)

from tests.test_descriptor_store import RECOVERY_HANDLE, objects, pointer_variant
from tests.test_recovery_bootstrap import authenticate, observation
from tests.test_recovery_descriptor import build_vector

FAILURES = {
    "wrong-recovery-handle": "recovery_identity_mismatch",
    "wrong-account-scope": "recovery_identity_mismatch",
    "altered-signature": "invalid_current_pointer",
    "wrong-issuer": "invalid_current_pointer",
    "stale-epoch": "cloud_party_state_mismatch",
    "cross-user-substitution": "recovery_identity_mismatch",
    "cross-policy-substitution": "cloud_party_state_mismatch",
    "cross-suite-downgrade": "cloud_party_state_mismatch",
    "cross-membership-mix": "invalid_descriptor",
    "descriptor-backup-digest-mismatch": "invalid_recovery_bundle",
    "descriptor-party-state-mismatch": "cloud_party_state_mismatch",
    "altered-zip-member": "invalid_recovery_bundle",
    "duplicate-unexpected-unsafe-zip-member": "invalid_recovery_bundle",
    "oversized-unsupported-zip-member": "invalid_recovery_bundle",
    "stale-bundle-rollback": "invalid_recovery_bundle",
    "stale-current-pointer-rollback": "stale_current_pointer",
}


class DescriptorSecurityScenarioTests(unittest.TestCase):
    def test_registered_detectors_and_positive_controls_build_aggregate_report(
        self,
    ) -> None:
        positive = authenticate()
        self.assertEqual(positive.matching_authorizers, (1, 2, 3, 4))

        for operation in (
            lambda: authenticate(recovery_handle="wrong-handle"),
            lambda: authenticate(subject_id="99" * 32),
        ):
            with self.assertRaises(RecoveryBootstrapError) as context:
                operation()
            self.assertEqual(
                context.exception.code,
                BootstrapFailureCode.RECOVERY_IDENTITY_MISMATCH,
            )

        pointer = build_vector()["pointer"]
        assert isinstance(pointer, bytes)
        with self.assertRaises(RecoveryBootstrapError):
            authenticate(pointer_bytes=pointer[:-1] + b"x")
        with self.assertRaises(RecoveryBootstrapError) as mismatch:
            authenticate(
                observations=[
                    observation(1),
                    observation(2),
                    observation(3),
                    observation(4, overrides={"epoch": 2}),
                ]
            )
        self.assertEqual(
            mismatch.exception.code, BootstrapFailureCode.CLOUD_PARTY_STATE_MISMATCH
        )

        descriptor = json.loads(build_vector()["descriptor"])
        mixed = copy.deepcopy(descriptor["payload"])
        mixed["recovery_suite"]["holders"][1]["holder_id"] = 1
        with self.assertRaises(RecoveryDescriptorError):
            validate_descriptor_payload(mixed)

        bundle = build_vector()["bundle"]
        assert isinstance(bundle, bytes)
        with self.assertRaises(RecoveryBootstrapError):
            authenticate(bundle_bytes=bundle[:-1] + b"x")

        with tempfile.TemporaryDirectory() as directory:
            store = FilesystemDescriptorBundleStore(directory)
            _descriptor, initial, _bundle = objects()
            store.compare_and_swap_current(RECOVERY_HANDLE, None, initial)
            successor = pointer_variant(1)
            store.compare_and_swap_current(RECOVERY_HANDLE, initial, successor)
            with self.assertRaises(ObjectStale):
                store.compare_and_swap_current(
                    RECOVERY_HANDLE,
                    CurrentDescriptorPointer(
                        format_id=CURRENT_POINTER_VERSION,
                        payload=initial.payload,
                    ),
                    pointer_variant(2),
                )

        report = build_descriptor_security_report(
            FAILURES, cleanup_passed=True, output_scan_passed=True
        )
        public_view = (
            build_vector()["descriptor"]
            + build_vector()["pointer"]
            + build_vector()["bundle"]
        )
        candidate_result = run_bounded_networkless_candidate_test(
            public_view,
            synthetic_candidates=(b"test-only-candidate-a", b"test-only-candidate-b"),
        )
        self.assertEqual(candidate_result, report["candidate_test"])
        self.assertEqual(validate_descriptor_security_report(report), report)
        self.assertEqual(report["detected_count"], len(SCENARIOS))
        self.assertEqual(report["positive_control_count"], len(SCENARIOS))

    def test_schema_and_report_are_exact_aggregate_only_contracts(self) -> None:
        schema_path = (
            Path(__file__).resolve().parents[2]
            / "docs/schemas/descriptor-security-scenarios-v1.schema.json"
        )
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        self.assertEqual(schema["$id"], REPORT_VERSION)
        self.assertFalse(schema["additionalProperties"])

        report = build_descriptor_security_report(
            FAILURES, cleanup_passed=True, output_scan_passed=True
        )
        encoded = json.dumps(report, sort_keys=True).lower()
        for forbidden in (
            "raw_cue",
            "candidate_value",
            "private_key",
            "credential",
            "party_secret_state",
            "k_wrap",
        ):
            self.assertNotIn(forbidden, encoded)
        changed = copy.deepcopy(report)
        changed["scenarios"][0]["detected"] = False
        with self.assertRaises(DescriptorSecurityReportError):
            validate_descriptor_security_report(changed)
        changed = copy.deepcopy(report)
        changed["unexpected"] = True
        with self.assertRaises(DescriptorSecurityReportError):
            validate_descriptor_security_report(changed)


if __name__ == "__main__":
    unittest.main()
