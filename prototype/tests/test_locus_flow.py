from __future__ import annotations

import copy
import unittest

from locus.core import (
    LocusError,
    backup_digest,
    enroll,
    recover,
    state_separation_audit,
)
from locus.object_store import BackupReference
from locus.tpass import TpassConcreteBackend, TpassSimulator


def sample_cues() -> list[dict]:
    return [
        {
            "location": {
                "provider": "local",
                "record_id": "place-001",
                "name": "Example Library",
                "country": "LU",
            },
            "person": {
                "provider": "local",
                "record_id": "person-001",
                "label": "Example Friend",
            },
        },
        {
            "location": {
                "provider": "local",
                "record_id": "place-002",
                "name": "Example Campus",
                "country": "LU",
            },
            "person": {
                "provider": "local",
                "record_id": "person-002",
                "label": "Example Colleague",
            },
        },
    ]


def tamper_hex(value: str) -> str:
    replacement = "00" if value[:2] != "00" else "ff"
    return replacement + value[2:]


class LocusFlowTests(unittest.TestCase):
    def test_successful_recovery(self) -> None:
        private_key = b"synthetic-private-key-material"
        enrollment = enroll(
            user_id="user",
            private_key=private_key,
            cues=sample_cues(),
            threshold=2,
            parties=3,
        )
        recovered = recover(
            user_id="user",
            backup=enrollment.backup,
            party_records=enrollment.parties[:2],
            cues=sample_cues(),
        )
        self.assertEqual(private_key, recovered)
        self.assertEqual(enrollment.metrics["backend"], "yi-zk-ristretto255-native-v1")
        self.assertEqual(enrollment.backup["version"], "LOCUS-development-backup-v1")
        self.assertEqual(enrollment.backup["epoch"], 1)
        self.assertEqual(
            enrollment.backup["ciphertext"]["version"],
            "LOCUS-AES-256-GCM-v1",
        )
        self.assertEqual(enrollment.backup["ciphertext"]["algorithm"], "AES-256-GCM")
        self.assertEqual(
            enrollment.backup["tpass_public_params"]["encoding"],
            "LOCUS-TPASS-wire-v1",
        )
        self.assertTrue(
            all(
                party["tpass_state"]["encoding"] == "LOCUS-TPASS-wire-v1"
                for party in enrollment.parties
            )
        )

    def test_wrong_location_fails(self) -> None:
        enrollment = enroll(
            user_id="user",
            private_key=b"key",
            cues=sample_cues(),
            threshold=2,
            parties=3,
        )
        wrong = sample_cues()
        wrong[0]["location"]["record_id"] = "place-wrong"
        with self.assertRaises(LocusError):
            recover(
                user_id="user",
                backup=enrollment.backup,
                party_records=enrollment.parties[:2],
                cues=wrong,
            )

    def test_wrong_person_fails(self) -> None:
        enrollment = enroll(
            user_id="user",
            private_key=b"key",
            cues=sample_cues(),
            threshold=2,
            parties=3,
        )
        wrong = sample_cues()
        wrong[1]["person"]["record_id"] = "person-wrong"
        with self.assertRaises(LocusError):
            recover(
                user_id="user",
                backup=enrollment.backup,
                party_records=enrollment.parties[:2],
                cues=wrong,
            )

    def test_insufficient_parties_fail(self) -> None:
        enrollment = enroll(
            user_id="user",
            private_key=b"key",
            cues=sample_cues(),
            threshold=2,
            parties=3,
        )
        with self.assertRaises(LocusError):
            recover(
                user_id="user",
                backup=enrollment.backup,
                party_records=enrollment.parties[:1],
                cues=sample_cues(),
            )

    def test_any_valid_threshold_subset_succeeds(self) -> None:
        private_key = b"key"
        enrollment = enroll(
            user_id="user",
            private_key=private_key,
            cues=sample_cues(),
            threshold=2,
            parties=3,
        )
        recovered = recover(
            user_id="user",
            backup=enrollment.backup,
            party_records=[enrollment.parties[0], enrollment.parties[2]],
            cues=sample_cues(),
        )
        self.assertEqual(private_key, recovered)

    def test_reversed_cue_order_fails(self) -> None:
        enrollment = enroll(
            user_id="user",
            private_key=b"key",
            cues=sample_cues(),
            threshold=2,
            parties=3,
        )
        reversed_cues = list(reversed(sample_cues()))
        with self.assertRaises(LocusError):
            recover(
                user_id="user",
                backup=enrollment.backup,
                party_records=enrollment.parties[:2],
                cues=reversed_cues,
            )

    def test_tampered_ciphertext_fails(self) -> None:
        enrollment = enroll(
            user_id="user",
            private_key=b"key",
            cues=sample_cues(),
            threshold=2,
            parties=3,
        )
        backup = copy.deepcopy(enrollment.backup)
        backup["ciphertext"]["ciphertext"] = tamper_hex(
            backup["ciphertext"]["ciphertext"]
        )
        backup["digest"] = enrollment.backup["digest"]
        with self.assertRaises(LocusError):
            recover(
                user_id="user",
                backup=backup,
                party_records=enrollment.parties[:2],
                cues=sample_cues(),
            )

    def test_ciphertext_authentication_fails_after_digest_refresh(self) -> None:
        enrollment = enroll(
            user_id="user",
            private_key=b"key",
            cues=sample_cues(),
            threshold=2,
            parties=3,
        )
        backup = copy.deepcopy(enrollment.backup)
        backup["ciphertext"]["ciphertext"] = tamper_hex(
            backup["ciphertext"]["ciphertext"]
        )
        backup["digest"] = backup_digest(backup)
        parties = copy.deepcopy(enrollment.parties[:2])
        for party in parties:
            party["backup_digest"] = backup["digest"]
            party["cloud_ref"] = BackupReference.from_backup(backup).to_dict()
        with self.assertRaises(LocusError):
            recover(
                user_id="user",
                backup=backup,
                party_records=parties,
                cues=sample_cues(),
            )

    def test_ciphertext_substitution_fails_aead_authentication(self) -> None:
        first = enroll(
            user_id="user",
            private_key=b"first-key",
            cues=sample_cues(),
            threshold=2,
            parties=3,
        )
        second = enroll(
            user_id="user",
            private_key=b"second-key",
            cues=sample_cues(),
            threshold=2,
            parties=3,
        )
        backup = copy.deepcopy(first.backup)
        backup["ciphertext"] = copy.deepcopy(second.backup["ciphertext"])
        backup["digest"] = backup_digest(backup)
        parties = copy.deepcopy(first.parties[:2])
        for party in parties:
            party["backup_digest"] = backup["digest"]
            party["cloud_ref"] = BackupReference.from_backup(backup).to_dict()
        with self.assertRaises(LocusError):
            recover(
                user_id="user",
                backup=backup,
                party_records=parties,
                cues=sample_cues(),
            )

    def test_authenticated_public_metadata_substitution_fails(self) -> None:
        enrollment = enroll(
            user_id="user",
            private_key=b"key",
            cues=sample_cues(),
            threshold=2,
            parties=3,
        )
        backup = copy.deepcopy(enrollment.backup)
        backup["security_policy"]["cooldown_seconds"] = 1
        backup["digest"] = backup_digest(backup)
        parties = copy.deepcopy(enrollment.parties[:2])
        for party in parties:
            party["backup_digest"] = backup["digest"]
            party["cloud_ref"] = BackupReference.from_backup(backup).to_dict()
            party["security_policy"] = copy.deepcopy(backup["security_policy"])
        with self.assertRaises(LocusError):
            recover(
                user_id="user",
                backup=backup,
                party_records=parties,
                cues=sample_cues(),
            )

    def test_unsupported_ciphertext_format_fails_before_attempt(self) -> None:
        enrollment = enroll(
            user_id="user",
            private_key=b"key",
            cues=sample_cues(),
            threshold=2,
            parties=3,
        )
        backup = copy.deepcopy(enrollment.backup)
        backup["ciphertext"]["version"] = "LOCUS-AES-256-GCM-v0"
        backup["digest"] = backup_digest(backup)
        parties = copy.deepcopy(enrollment.parties[:2])
        for party in parties:
            party["backup_digest"] = backup["digest"]
            party["cloud_ref"] = BackupReference.from_backup(backup).to_dict()
        with self.assertRaises(LocusError):
            recover(
                user_id="user",
                backup=backup,
                party_records=parties,
                cues=sample_cues(),
            )
        self.assertEqual([party["attempt_count"] for party in parties], [0, 0])

    def test_party_digest_mismatch_fails(self) -> None:
        enrollment = enroll(
            user_id="user",
            private_key=b"key",
            cues=sample_cues(),
            threshold=2,
            parties=3,
        )
        parties = copy.deepcopy(enrollment.parties[:2])
        parties[0]["backup_digest"] = "bad"
        with self.assertRaises(LocusError):
            recover(
                user_id="user",
                backup=enrollment.backup,
                party_records=parties,
                cues=sample_cues(),
            )

    def test_explicit_rollback_backup_fails_by_party_digest(self) -> None:
        current = enroll(
            user_id="user",
            private_key=b"new-key",
            cues=sample_cues(),
            threshold=2,
            parties=3,
        )
        rollback = enroll(
            user_id="user",
            private_key=b"old-key",
            cues=sample_cues(),
            threshold=2,
            parties=3,
        )
        stale_backup = copy.deepcopy(rollback.backup)
        stale_backup["bid"] = current.backup["bid"]
        stale_backup["digest"] = backup_digest(stale_backup)
        with self.assertRaises(LocusError):
            recover(
                user_id="user",
                backup=stale_backup,
                party_records=current.parties[:2],
                cues=sample_cues(),
            )

    def test_unsupported_context_policy_version_fails(self) -> None:
        enrollment = enroll(
            user_id="user",
            private_key=b"key",
            cues=sample_cues(),
            threshold=2,
            parties=3,
        )
        backup = copy.deepcopy(enrollment.backup)
        backup["context_policy"]["version"] = "LOCUS-local-context-v0"
        backup["digest"] = backup_digest(backup)
        parties = copy.deepcopy(enrollment.parties[:2])
        for party in parties:
            party["backup_digest"] = backup["digest"]
            party["cloud_ref"] = BackupReference.from_backup(backup).to_dict()
        with self.assertRaises(LocusError):
            recover(
                user_id="user",
                backup=backup,
                party_records=parties,
                cues=sample_cues(),
            )

    def test_unsupported_security_policy_version_fails(self) -> None:
        enrollment = enroll(
            user_id="user",
            private_key=b"key",
            cues=sample_cues(),
            threshold=2,
            parties=3,
        )
        backup = copy.deepcopy(enrollment.backup)
        backup["security_policy"]["version"] = "LOCUS-security-policy-v0"
        backup["digest"] = backup_digest(backup)
        parties = copy.deepcopy(enrollment.parties[:2])
        for party in parties:
            party["backup_digest"] = backup["digest"]
            party["cloud_ref"] = BackupReference.from_backup(backup).to_dict()
            party["security_policy"] = copy.deepcopy(backup["security_policy"])
        with self.assertRaises(LocusError):
            recover(
                user_id="user",
                backup=backup,
                party_records=parties,
                cues=sample_cues(),
            )

    def test_party_security_policy_mismatch_fails(self) -> None:
        enrollment = enroll(
            user_id="user",
            private_key=b"key",
            cues=sample_cues(),
            threshold=2,
            parties=3,
        )
        parties = copy.deepcopy(enrollment.parties[:2])
        parties[0]["security_policy"]["max_attempts"] = 99
        with self.assertRaises(LocusError):
            recover(
                user_id="user",
                backup=enrollment.backup,
                party_records=parties,
                cues=sample_cues(),
            )

    def test_malformed_party_response_fails(self) -> None:
        enrollment = enroll(
            user_id="user",
            private_key=b"key",
            cues=sample_cues(),
            threshold=2,
            parties=3,
        )
        parties = copy.deepcopy(enrollment.parties[:2])
        del parties[0]["tpass_state"]["state"]
        with self.assertRaises(LocusError):
            recover(
                user_id="user",
                backup=enrollment.backup,
                party_records=parties,
                cues=sample_cues(),
            )

    def test_malformed_public_parameters_fail(self) -> None:
        enrollment = enroll(
            user_id="user",
            private_key=b"key",
            cues=sample_cues(),
            threshold=2,
            parties=3,
        )
        backup = copy.deepcopy(enrollment.backup)
        backup["tpass_public_params"]["threshold"] = 0
        backup["digest"] = backup_digest(backup)
        parties = copy.deepcopy(enrollment.parties[:2])
        for party in parties:
            party["backup_digest"] = backup["digest"]
            party["cloud_ref"] = BackupReference.from_backup(backup).to_dict()
        with self.assertRaises(LocusError):
            recover(
                user_id="user",
                backup=backup,
                party_records=parties,
                cues=sample_cues(),
            )

    def test_unsupported_tpass_backend_fails(self) -> None:
        enrollment = enroll(
            user_id="user",
            private_key=b"key",
            cues=sample_cues(),
            threshold=2,
            parties=3,
        )
        backup = copy.deepcopy(enrollment.backup)
        backup["tpass_public_params"]["backend"] = "unknown-backend"
        backup["digest"] = backup_digest(backup)
        parties = copy.deepcopy(enrollment.parties[:2])
        for party in parties:
            party["backup_digest"] = backup["digest"]
            party["cloud_ref"] = BackupReference.from_backup(backup).to_dict()
        with self.assertRaises(LocusError):
            recover(
                user_id="user",
                backup=backup,
                party_records=parties,
                cues=sample_cues(),
            )

    def test_attempt_limit_fails(self) -> None:
        enrollment = enroll(
            user_id="user",
            private_key=b"key",
            cues=sample_cues(),
            threshold=2,
            parties=3,
            max_attempts=1,
        )
        recover(
            user_id="user",
            backup=enrollment.backup,
            party_records=enrollment.parties[:2],
            cues=sample_cues(),
        )
        with self.assertRaises(LocusError):
            recover(
                user_id="user",
                backup=enrollment.backup,
                party_records=enrollment.parties[:2],
                cues=sample_cues(),
            )

    def test_state_separation_audit_passes(self) -> None:
        enrollment = enroll(
            user_id="user",
            private_key=b"key",
            cues=sample_cues(),
            threshold=2,
            parties=3,
        )
        audit = state_separation_audit(enrollment.backup, enrollment.parties)
        self.assertTrue(audit["ok"])

    def test_native_target_threshold_matrix_succeeds(self) -> None:
        for threshold, parties in ((2, 3), (3, 5), (5, 9)):
            with self.subTest(threshold=threshold, parties=parties):
                enrollment = enroll(
                    user_id="user",
                    private_key=b"key",
                    cues=sample_cues(),
                    threshold=threshold,
                    parties=parties,
                )
                selected = enrollment.parties[::2][:threshold]
                if len(selected) < threshold:
                    selected = enrollment.parties[-threshold:]
                recovered = recover(
                    user_id="user",
                    backup=enrollment.backup,
                    party_records=selected,
                    cues=sample_cues(),
                )
                self.assertEqual(recovered, b"key")

    def test_simulator_requires_explicit_selection(self) -> None:
        backend = TpassSimulator()
        enrollment = enroll(
            user_id="user",
            private_key=b"key",
            cues=sample_cues(),
            threshold=2,
            parties=3,
            tpass=backend,
        )
        recovered = recover(
            user_id="user",
            backup=enrollment.backup,
            party_records=enrollment.parties[:2],
            cues=sample_cues(),
            tpass=backend,
        )
        self.assertEqual(recovered, b"key")
        self.assertEqual(enrollment.metrics["backend"], backend.backend)

    def test_concrete_backend_successful_recovery(self) -> None:
        backend = TpassConcreteBackend()
        private_key = b"synthetic-private-key-material"
        enrollment = enroll(
            user_id="user",
            private_key=private_key,
            cues=sample_cues(),
            threshold=2,
            parties=3,
            tpass=backend,
        )
        recovered = recover(
            user_id="user",
            backup=enrollment.backup,
            party_records=enrollment.parties[:2],
            cues=sample_cues(),
            tpass=backend,
        )
        self.assertEqual(private_key, recovered)

    def test_concrete_backend_wrong_password_fails_digest_check(self) -> None:
        backend = TpassConcreteBackend()
        enrollment = enroll(
            user_id="user",
            private_key=b"key",
            cues=sample_cues(),
            threshold=2,
            parties=3,
            tpass=backend,
        )
        wrong = sample_cues()
        wrong[0]["person"]["record_id"] = "person-wrong"
        with self.assertRaises(LocusError):
            recover(
                user_id="user",
                backup=enrollment.backup,
                party_records=enrollment.parties[:2],
                cues=wrong,
                tpass=backend,
            )

    def test_concrete_backend_any_valid_threshold_subset_succeeds(self) -> None:
        backend = TpassConcreteBackend()
        private_key = b"key"
        enrollment = enroll(
            user_id="user",
            private_key=private_key,
            cues=sample_cues(),
            threshold=3,
            parties=5,
            tpass=backend,
        )
        recovered = recover(
            user_id="user",
            backup=enrollment.backup,
            party_records=[
                enrollment.parties[0],
                enrollment.parties[2],
                enrollment.parties[4],
            ],
            cues=sample_cues(),
            tpass=backend,
        )
        self.assertEqual(private_key, recovered)


if __name__ == "__main__":
    unittest.main()
