from __future__ import annotations

import base64
import copy
import hashlib
import unittest
from io import BytesIO
from typing import Any

from locus.core import backup_digest, enroll
from locus.object_store import (
    MAX_BACKUP_OBJECT_BYTES,
    BackupReference,
    ObjectCorrupt,
    ObjectStoreUnavailable,
    ObjectTooLarge,
    encode_backup_object,
)
from locus.s3_object_store import S3BackupObjectStore

from tests.object_store_contract import exercise_backend_contract, sample_cues


class FakeS3Error(Exception):
    def __init__(self, code: str, status: int) -> None:
        super().__init__(code)
        self.response = {
            "Error": {"Code": code},
            "ResponseMetadata": {"HTTPStatusCode": status},
        }


class FakeStreamingBody:
    def __init__(self, encoded: bytes) -> None:
        self._stream = BytesIO(encoded)
        self.closed = False

    def read(self, amount: int | None = None) -> bytes:
        return self._stream.read(-1 if amount is None else amount)

    def close(self) -> None:
        self.closed = True
        self._stream.close()


class FakeS3Client:
    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], bytes] = {}
        self.available = True
        self.conditional_conflicts = 0
        self.put_calls = 0

    def _require_available(self) -> None:
        if not self.available:
            raise ConnectionError("synthetic S3 outage")

    def put_object(self, **kwargs: Any) -> dict[str, Any]:
        self._require_available()
        self.put_calls += 1
        if self.conditional_conflicts:
            self.conditional_conflicts -= 1
            raise FakeS3Error("ConditionalRequestConflict", 409)
        testcase_body = kwargs["Body"]
        if not isinstance(testcase_body, bytes):
            raise AssertionError("adapter did not provide canonical bytes")
        checksum = base64.b64encode(hashlib.sha256(testcase_body).digest()).decode(
            "ascii"
        )
        if kwargs.get("ChecksumSHA256") != checksum:
            raise AssertionError("adapter did not bind the transport checksum")
        if kwargs.get("IfNoneMatch") != "*":
            raise AssertionError("adapter did not use create-if-absent")
        key = (kwargs["Bucket"], kwargs["Key"])
        if key in self.objects:
            raise FakeS3Error("PreconditionFailed", 412)
        self.objects[key] = testcase_body
        return {"ChecksumSHA256": checksum}

    def get_object(self, **kwargs: Any) -> dict[str, Any]:
        self._require_available()
        key = (kwargs["Bucket"], kwargs["Key"])
        try:
            encoded = self.objects[key]
        except KeyError as exc:
            raise FakeS3Error("NoSuchKey", 404) from exc
        return {
            "Body": FakeStreamingBody(encoded),
            "ContentLength": len(encoded),
        }

    def head_object(self, **kwargs: Any) -> dict[str, Any]:
        self._require_available()
        key = (kwargs["Bucket"], kwargs["Key"])
        if key not in self.objects:
            raise FakeS3Error("NotFound", 404)
        return {"ContentLength": len(self.objects[key])}

    def head_bucket(self, **kwargs: Any) -> dict[str, Any]:
        self._require_available()
        if kwargs["Bucket"] != "locus-backup-tests":
            raise FakeS3Error("NoSuchBucket", 404)
        return {}

    def delete_object(self, **kwargs: Any) -> dict[str, Any]:
        self._require_available()
        self.objects.pop((kwargs["Bucket"], kwargs["Key"]), None)
        return {}


class S3BackupObjectStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = FakeS3Client()
        self.store = S3BackupObjectStore(
            client=self.client,
            bucket="locus-backup-tests",
            prefix="contract/backups",
        )

    def test_shared_backend_contract(self) -> None:
        exercise_backend_contract(self, self.store)

    def test_conditional_conflict_is_retried_without_overwrite(self) -> None:
        enrollment = enroll(
            user_id="user",
            private_key=b"key",
            cues=sample_cues(),
            threshold=2,
            parties=3,
        )
        self.client.conditional_conflicts = 1
        reference = self.store.create(enrollment.backup)
        self.assertEqual(self.client.put_calls, 2)
        self.assertEqual(self.store.read(reference), enrollment.backup)
        self.assertEqual(
            self.store.read_encoded(reference),
            encode_backup_object(enrollment.backup)[1],
        )

    def test_probe_maps_reachability_without_listing(self) -> None:
        self.store.probe()
        self.client.available = False
        with self.assertRaises(ObjectStoreUnavailable):
            self.store.probe()

    def test_corrupt_noncanonical_and_oversized_objects_are_rejected(self) -> None:
        enrollment = enroll(
            user_id="user",
            private_key=b"key",
            cues=sample_cues(),
            threshold=2,
            parties=3,
        )
        reference = self.store.create(enrollment.backup)
        object_key = (self.store.bucket, self.store.object_key(reference))
        canonical = self.client.objects[object_key]

        self.client.objects[object_key] = canonical + b"\n"
        with self.assertRaises(ObjectCorrupt):
            self.store.read(reference)

        self.client.objects[object_key] = b"x" * (MAX_BACKUP_OBJECT_BYTES + 1)
        with self.assertRaises(ObjectTooLarge):
            self.store.read(reference)

    def test_reference_substitution_and_backend_outage_fail_closed(self) -> None:
        enrollment = enroll(
            user_id="user",
            private_key=b"key",
            cues=sample_cues(),
            threshold=2,
            parties=3,
        )
        reference = self.store.create(enrollment.backup)
        wrong = copy.deepcopy(enrollment.backup)
        wrong["epoch"] = 2
        wrong["digest"] = backup_digest(wrong)
        wrong_reference = BackupReference.from_backup(wrong)
        self.client.objects[
            (self.store.bucket, self.store.object_key(wrong_reference))
        ] = self.client.objects[(self.store.bucket, self.store.object_key(reference))]
        with self.assertRaises(ObjectCorrupt):
            self.store.read(wrong_reference)

        self.client.available = False
        with self.assertRaises(ObjectStoreUnavailable):
            self.store.read(reference)

    def test_configuration_rejects_unsafe_names_and_plaintext_default(self) -> None:
        for bucket in ("UPPERCASE", "ab", "bad..dots"):
            with self.subTest(bucket=bucket):
                with self.assertRaises(ObjectCorrupt):
                    S3BackupObjectStore(client=self.client, bucket=bucket)
        with self.assertRaisesRegex(ObjectCorrupt, "plaintext"):
            S3BackupObjectStore.from_credentials(
                bucket="locus-backups",
                endpoint_url="http://127.0.0.1:9000",
                access_key="test-access",
                secret_key="test-secret-key",
            )


if __name__ == "__main__":
    unittest.main()
