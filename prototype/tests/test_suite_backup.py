from __future__ import annotations

import copy
import unittest

from locus.appss_formats import (
    APPSS_PROFILE_2_OF_3,
    APPSS_PROFILE_3_OF_5,
    APPSS_SUITE_ID,
    YI_PROFILE_2_OF_3,
    YI_PROFILE_3_OF_5,
    YI_SUITE_ID,
)
from locus.contracts import RecoveryContext, ThresholdParameters
from locus.object_store import BackupReference, ObjectCorrupt, encode_backup_object
from locus.recovery_suite_registry import RecoverySuiteRegistry
from locus.suite_backup import (
    SuiteBackupError,
    backup_v5_associated_data,
    backup_v6_associated_data,
    enroll_backup_v5,
    enroll_backup_v6,
    recover_backup_v5,
    recover_backup_v6,
    validate_backup_v5,
    validate_backup_v6,
)


class SuiteBackupTests(unittest.TestCase):
    def test_v6_paired_topologies_use_one_outer_backup_path(self) -> None:
        registry = RecoverySuiteRegistry()
        protected_key = b"paired-deployment-protected-key"
        password = b"paired-password".ljust(32, b"\x00")
        profiles = (
            (YI_SUITE_ID, YI_PROFILE_2_OF_3, ThresholdParameters(2, 3), 0x61),
            (APPSS_SUITE_ID, APPSS_PROFILE_2_OF_3, ThresholdParameters(2, 3), 0x62),
            (YI_SUITE_ID, YI_PROFILE_3_OF_5, ThresholdParameters(3, 5), 0x63),
            (APPSS_SUITE_ID, APPSS_PROFILE_3_OF_5, ThresholdParameters(3, 5), 0x64),
        )
        for suite_id, profile_id, threshold, marker in profiles:
            with self.subTest(suite_id=suite_id, profile_id=profile_id):
                context = RecoveryContext(
                    suite_id=suite_id,
                    recovery_id=f"paired-v6-{marker}",
                    backup_id=bytes([marker] * 16).hex(),
                    epoch=1,
                    policy_id="LOCUS-canonical-email-set-v1",
                    configuration_digest=bytes([marker + 1] * 32).hex(),
                    digest_context=f"paired-v6:{marker}",
                    suite_context_digest=bytes([marker + 2] * 32).hex(),
                )
                adapter = registry.for_authenticated_descriptor(suite_id)
                enrollment = adapter.initialize(
                    context=context,
                    password_input=password,
                    threshold=threshold,
                )
                result = enroll_backup_v6(
                    protected_key=protected_key,
                    context=context,
                    cue_policy_id=context.policy_id,
                    resolver_profile="LOCUS-no-resolver-v1",
                    adapter=adapter,
                    enrollment=enrollment,
                    profile_id=profile_id,
                    threshold=threshold,
                    bid=bytes([marker] * 16),
                    nonce=bytes([marker + 3] * 16),
                )
                backup = validate_backup_v6(result.backup)
                self.assertEqual(
                    (backup["recovery_suite"]["k"], backup["recovery_suite"]["n"]),
                    (threshold.k, threshold.n),
                )
                self.assertEqual(
                    recover_backup_v6(
                        backup=backup,
                        context=context,
                        password_input=password,
                        adapter=adapter,
                        party_states=result.party_states[: threshold.k],
                    ),
                    protected_key,
                )
                with self.assertRaisesRegex(SuiteBackupError, "recovery rejected"):
                    recover_backup_v6(
                        backup=backup,
                        context=context,
                        password_input=password,
                        adapter=adapter,
                        party_states=result.party_states[: threshold.k - 1],
                    )
                aad = backup_v6_associated_data(backup)
                self.assertIn(profile_id.encode(), aad)
                self.assertNotIn(backup["ciphertext"]["ciphertext"].encode(), aad)

    def test_both_suites_use_the_same_backup_hkdf_aes_boundary(self) -> None:
        registry = RecoverySuiteRegistry()
        protected_key = b"synthetic-protected-key-material"
        password = b"correct".ljust(32, b"\x00")
        for suite_id, profile_id, marker in (
            (YI_SUITE_ID, YI_PROFILE_2_OF_3, 0x31),
            (APPSS_SUITE_ID, APPSS_PROFILE_2_OF_3, 0x32),
        ):
            context = RecoveryContext(
                suite_id=suite_id,
                recovery_id=f"backup-v5-{marker}",
                backup_id=bytes([marker] * 16).hex(),
                epoch=1,
                policy_id="LOCUS-canonical-email-set-v1",
                configuration_digest=bytes([marker] * 32).hex(),
                digest_context=f"backup-v5:{marker}",
                suite_context_digest=bytes([marker + 1] * 32).hex(),
            )
            adapter = registry.for_authenticated_descriptor(suite_id)
            enrollment = adapter.initialize(
                context=context,
                password_input=password,
                threshold=ThresholdParameters(k=2, n=3),
            )
            result = enroll_backup_v5(
                protected_key=protected_key,
                context=context,
                cue_policy_id=context.policy_id,
                resolver_profile="LOCUS-no-resolver-v1",
                adapter=adapter,
                enrollment=enrollment,
                profile_id=profile_id,
                bid=bytes([marker] * 16),
                nonce=bytes([marker + 2] * 16),
            )
            backup = validate_backup_v5(result.backup)
            self.assertEqual(backup["ciphertext"]["algorithm"], "AES-256-GCM")
            self.assertEqual(backup["ciphertext"]["version"], "LOCUS-AES-256-GCM-v1")
            self.assertEqual(backup["recovery_suite"]["id"], suite_id)
            self.assertEqual(
                recover_backup_v5(
                    backup=backup,
                    context=context,
                    password_input=password,
                    adapter=adapter,
                    party_states=result.party_states[:2],
                ),
                protected_key,
            )
            reference = BackupReference.from_backup(backup)
            self.assertEqual((reference.bid, reference.epoch), (context.backup_id, 1))
            with self.assertRaises(ObjectCorrupt):
                encode_backup_object(backup)

    def test_wrong_input_cross_suite_and_tampering_are_generic_rejection(self) -> None:
        registry = RecoverySuiteRegistry()
        context = RecoveryContext(
            suite_id=APPSS_SUITE_ID,
            recovery_id="backup-reject",
            backup_id="45" * 16,
            epoch=1,
            policy_id="LOCUS-canonical-email-set-v1",
            configuration_digest="46" * 32,
            digest_context="backup-reject:1",
            suite_context_digest="47" * 32,
        )
        adapter = registry.for_authenticated_descriptor(APPSS_SUITE_ID)
        password = b"correct".ljust(32, b"\x00")
        enrollment = adapter.initialize(
            context=context,
            password_input=password,
            threshold=ThresholdParameters(k=2, n=3),
        )
        result = enroll_backup_v5(
            protected_key=b"synthetic-key",
            context=context,
            cue_policy_id=context.policy_id,
            resolver_profile="LOCUS-no-resolver-v1",
            adapter=adapter,
            enrollment=enrollment,
            profile_id=APPSS_PROFILE_2_OF_3,
            bid=bytes.fromhex(context.backup_id),
            nonce=b"\x48" * 16,
        )
        with self.assertRaisesRegex(SuiteBackupError, "recovery rejected"):
            recover_backup_v5(
                backup=result.backup,
                context=context,
                password_input=b"wrong".ljust(32, b"\x00"),
                adapter=adapter,
                party_states=result.party_states[:2],
            )
        yi = registry.for_authenticated_descriptor(YI_SUITE_ID)
        with self.assertRaisesRegex(SuiteBackupError, "binding mismatch"):
            recover_backup_v5(
                backup=result.backup,
                context=context,
                password_input=password,
                adapter=yi,
                party_states=result.party_states[:2],
            )
        altered = copy.deepcopy(result.backup)
        altered["recovery_suite"]["public_state"] = "00"
        altered["digest"] = result.backup["digest"]
        with self.assertRaises(SuiteBackupError):
            validate_backup_v5(altered)

    def test_associated_data_excludes_ciphertext_but_binds_suite(self) -> None:
        registry = RecoverySuiteRegistry()
        context = RecoveryContext(
            suite_id=APPSS_SUITE_ID,
            recovery_id="aad-test",
            backup_id="51" * 16,
            epoch=1,
            policy_id="LOCUS-canonical-phone-set-v1",
            configuration_digest="52" * 32,
            digest_context="aad:1",
            suite_context_digest="53" * 32,
        )
        adapter = registry.for_authenticated_descriptor(APPSS_SUITE_ID)
        enrollment = adapter.initialize(
            context=context,
            password_input=b"p" * 32,
            threshold=ThresholdParameters(k=2, n=3),
        )
        result = enroll_backup_v5(
            protected_key=b"key",
            context=context,
            cue_policy_id=context.policy_id,
            resolver_profile="LOCUS-no-resolver-v1",
            adapter=adapter,
            enrollment=enrollment,
            profile_id=APPSS_PROFILE_2_OF_3,
            bid=bytes.fromhex(context.backup_id),
            nonce=b"\x54" * 16,
        )
        aad = backup_v5_associated_data(result.backup)
        self.assertIn(APPSS_SUITE_ID.encode(), aad)
        self.assertNotIn(result.backup["ciphertext"]["ciphertext"].encode(), aad)


if __name__ == "__main__":
    unittest.main()
