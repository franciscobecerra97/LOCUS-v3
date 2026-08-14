from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from locus.codec import encode
from locus.core import LocusError, backup_digest, enroll, recover_from_store
from locus.object_store import (
    BackupReference,
    FilesystemBackupObjectStore,
    ObjectConflict,
    ObjectCorrupt,
    ObjectNotFound,
    ObjectStoreUnavailable,
    ObjectTooLarge,
)
from tests.object_store_contract import exercise_backend_contract


def sample_cues() -> list[dict]:
    return [
        {
            "location": {
                "provider": "local",
                "record_id": "cloud-test-place-1",
            },
            "person": {
                "provider": "local",
                "record_id": "cloud-test-person-1",
            },
        },
        {
            "location": {
                "provider": "local",
                "record_id": "cloud-test-place-2",
            },
            "person": {
                "provider": "local",
                "record_id": "cloud-test-person-2",
            },
        },
    ]


class FilesystemBackupObjectStoreTests(unittest.TestCase):
    def test_shared_backend_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            exercise_backend_contract(
                self, FilesystemBackupObjectStore(Path(temporary) / "cloud")
            )

    def test_separated_store_round_trip_and_exact_create_retry(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            store = FilesystemBackupObjectStore(Path(temporary) / "cloud")
            enrollment = enroll(
                user_id="user",
                private_key=b"synthetic-private-key-material",
                cues=sample_cues(),
                threshold=2,
                parties=3,
                object_store=store,
            )
            reference = BackupReference.from_dict(enrollment.cloud_reference)

            self.assertEqual(store.create(enrollment.backup), reference)
            self.assertEqual(store.read(reference), enrollment.backup)
            self.assertEqual(
                recover_from_store(
                    user_id="user",
                    cloud_reference=enrollment.cloud_reference,
                    object_store=store,
                    party_records=enrollment.parties[:2],
                    cues=sample_cues(),
                ),
                b"synthetic-private-key-material",
            )
            self.assertFalse(list(store.root.rglob(".pending-*")))

    def test_immutable_key_rejects_different_content(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            store = FilesystemBackupObjectStore(temporary)
            enrollment = enroll(
                user_id="user",
                private_key=b"first",
                cues=sample_cues(),
                threshold=2,
                parties=3,
            )
            store.create(enrollment.backup)
            changed = copy.deepcopy(enrollment.backup)
            changed["ciphertext"]["ciphertext"] = (
                "00" if changed["ciphertext"]["ciphertext"][:2] != "00" else "ff"
            ) + changed["ciphertext"]["ciphertext"][2:]
            changed["digest"] = backup_digest(changed)

            with self.assertRaises(ObjectConflict):
                store.create(changed)
            self.assertFalse(list(store.root.rglob(".pending-*")))

    def test_stale_epoch_substitution_and_corruption_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            store = FilesystemBackupObjectStore(temporary)
            old = enroll(
                user_id="user",
                private_key=b"old",
                cues=sample_cues(),
                threshold=2,
                parties=3,
                epoch=1,
            ).backup
            current = copy.deepcopy(old)
            current["epoch"] = 2
            current["digest"] = backup_digest(current)
            old_reference = store.create(old)
            current_reference = store.create(current)
            old_path = store.root / old_reference.bid / "1.json"
            current_path = store.root / current_reference.bid / "2.json"

            current_path.write_bytes(old_path.read_bytes())
            with self.assertRaises(ObjectCorrupt):
                store.read(current_reference)

            current_path.write_bytes(b'{"truncated":')
            with self.assertRaises(ObjectCorrupt):
                store.read(current_reference)

    def test_deletion_and_backend_unavailability_are_distinct(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            store = FilesystemBackupObjectStore(temporary)
            enrollment = enroll(
                user_id="user",
                private_key=b"key",
                cues=sample_cues(),
                threshold=2,
                parties=3,
            )
            reference = store.create(enrollment.backup)

            with mock.patch.object(Path, "lstat", side_effect=PermissionError):
                with self.assertRaises(ObjectStoreUnavailable):
                    store.read(reference)

            store.delete(reference)
            with self.assertRaises(ObjectNotFound):
                store.read(reference)
            with self.assertRaisesRegex(LocusError, "backup unavailable or invalid"):
                recover_from_store(
                    user_id="user",
                    cloud_reference=reference.to_dict(),
                    object_store=store,
                    party_records=enrollment.parties[:2],
                    cues=sample_cues(),
                )
            self.assertEqual(
                [party["attempt_count"] for party in enrollment.parties], [0] * 3
            )

    def test_noncanonical_oversized_and_mismatched_references_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            store = FilesystemBackupObjectStore(temporary)
            enrollment = enroll(
                user_id="user",
                private_key=b"key",
                cues=sample_cues(),
                threshold=2,
                parties=3,
            )
            reference = store.create(enrollment.backup)
            path = store.root / reference.bid / "1.json"
            canonical = path.read_bytes()
            path.write_bytes(canonical + b"\n")
            with self.assertRaises(ObjectCorrupt):
                store.read(reference)
            path.write_bytes(canonical)

            oversized = copy.deepcopy(enrollment.backup)
            oversized["ciphertext"]["ciphertext"] = "00" * (1024 * 1024)
            oversized["digest"] = backup_digest(oversized)
            with self.assertRaises(ObjectTooLarge):
                FilesystemBackupObjectStore(Path(temporary) / "large").create(oversized)

            mismatched = BackupReference(
                bid=reference.bid,
                epoch=reference.epoch,
                backup_digest="ff" * 32,
            )
            with self.assertRaises(ObjectCorrupt):
                FilesystemBackupObjectStore(temporary).read(mismatched)

    def test_symbolic_link_namespace_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            store = FilesystemBackupObjectStore(base / "cloud")
            enrollment = enroll(
                user_id="user",
                private_key=b"key",
                cues=sample_cues(),
                threshold=2,
                parties=3,
            )
            reference = BackupReference.from_backup(enrollment.backup)
            outside = base / "outside"
            outside.mkdir()
            try:
                (store.root / reference.bid).symlink_to(
                    outside, target_is_directory=True
                )
            except OSError as exc:
                self.skipTest(f"symbolic links unavailable: {exc}")
            with self.assertRaises(ObjectCorrupt):
                store.create(enrollment.backup)
            with self.assertRaises(ObjectCorrupt):
                store.read(reference)

    def test_cloud_and_party_snapshots_exclude_the_other_roles_secret_state(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            store = FilesystemBackupObjectStore(Path(temporary) / "cloud")
            enrollment = enroll(
                user_id="user",
                private_key=b"snapshot-private-key",
                cues=sample_cues(),
                threshold=2,
                parties=3,
                object_store=store,
            )
            reference = BackupReference.from_dict(enrollment.cloud_reference)
            cloud_bytes = (store.root / reference.bid / "1.json").read_bytes()
            party_bytes = encode(enrollment.parties)

            self.assertIn(
                enrollment.backup["ciphertext"]["ciphertext"].encode(), cloud_bytes
            )
            self.assertNotIn(
                enrollment.backup["ciphertext"]["ciphertext"].encode(), party_bytes
            )
            for party in enrollment.parties:
                encoded_state = party["tpass_state"]["state"].encode()
                self.assertIn(encoded_state, party_bytes)
                self.assertNotIn(encoded_state, cloud_bytes)
            for prohibited in (
                b"cloud-test-place-1",
                b"cloud-test-person-1",
                b"snapshot-private-key",
            ):
                self.assertNotIn(prohibited, cloud_bytes)
                self.assertNotIn(prohibited, party_bytes)


if __name__ == "__main__":
    unittest.main()
