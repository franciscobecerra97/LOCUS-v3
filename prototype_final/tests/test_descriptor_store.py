from __future__ import annotations

import base64
import hashlib
import json
import tempfile
import threading
import unittest
from io import BytesIO
from pathlib import Path
from typing import Any

from locus.contracts import (
    CurrentDescriptorPointer,
    DescriptorDocument,
    DescriptorStore,
)
from locus.descriptor_store import (
    DESCRIPTOR_STORE_PROFILE,
    FilesystemDescriptorBundleStore,
    RecoveryBundleStore,
    S3DescriptorBundleStore,
    SameHostDescriptorService,
)
from locus.object_store import (
    ObjectConflict,
    ObjectCorrupt,
    ObjectNotFound,
    ObjectStale,
    ObjectStoreUnavailable,
    ObjectTooLarge,
)
from locus.recovery_descriptor import (
    CURRENT_POINTER_VERSION,
    DESCRIPTOR_VERSION,
    MAX_BUNDLE_BYTES,
    create_current_pointer,
)
from tests.test_recovery_descriptor import (
    BACKUP_ID,
    KEY_ID,
    SUBJECT_ID,
    build_vector,
    signer,
)

RECOVERY_HANDLE = f"test-only-recovery:{BACKUP_ID}:1"
ROOT = Path(__file__).resolve().parents[1]


class FakeS3Error(Exception):
    def __init__(self, code: str, status: int) -> None:
        super().__init__(code)
        self.response = {
            "Error": {"Code": code},
            "ResponseMetadata": {"HTTPStatusCode": status},
        }


class FakeBody:
    def __init__(self, value: bytes) -> None:
        self.stream = BytesIO(value)

    def read(self, amount: int | None = None) -> bytes:
        return self.stream.read(-1 if amount is None else amount)

    def close(self) -> None:
        self.stream.close()


class FakeCasS3Client:
    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], tuple[bytes, str]] = {}
        self.counter = 0
        self.available = True
        self.list_calls = 0

    def _available(self) -> None:
        if not self.available:
            raise ConnectionError("synthetic outage")

    def put_object(self, **kwargs: Any) -> dict[str, Any]:
        self._available()
        body = kwargs["Body"]
        if not isinstance(body, bytes):
            raise AssertionError("non-byte S3 body")
        expected_checksum = base64.b64encode(hashlib.sha256(body).digest()).decode()
        if kwargs.get("ChecksumSHA256") != expected_checksum:
            raise AssertionError("missing exact checksum")
        key = (kwargs["Bucket"], kwargs["Key"])
        current = self.objects.get(key)
        if kwargs.get("IfNoneMatch") == "*" and current is not None:
            raise FakeS3Error("PreconditionFailed", 412)
        if "IfMatch" in kwargs and (current is None or current[1] != kwargs["IfMatch"]):
            raise FakeS3Error("PreconditionFailed", 412)
        self.counter += 1
        etag = f'"synthetic-{self.counter}"'
        self.objects[key] = (body, etag)
        return {"ETag": etag}

    def get_object(self, **kwargs: Any) -> dict[str, Any]:
        self._available()
        key = (kwargs["Bucket"], kwargs["Key"])
        try:
            body, etag = self.objects[key]
        except KeyError as exc:
            raise FakeS3Error("NoSuchKey", 404) from exc
        return {"Body": FakeBody(body), "ContentLength": len(body), "ETag": etag}

    def head_object(self, **kwargs: Any) -> dict[str, Any]:
        self._available()
        key = (kwargs["Bucket"], kwargs["Key"])
        if key not in self.objects:
            raise FakeS3Error("NotFound", 404)
        body, etag = self.objects[key]
        return {"ContentLength": len(body), "ETag": etag}

    def delete_object(self, **kwargs: Any) -> dict[str, Any]:
        self._available()
        self.objects.pop((kwargs["Bucket"], kwargs["Key"]), None)
        return {}

    def head_bucket(self, **kwargs: Any) -> dict[str, Any]:
        self._available()
        return {}

    def list_objects_v2(self, **kwargs: Any) -> dict[str, Any]:
        self.list_calls += 1
        raise AssertionError("descriptor store must never list")


def objects() -> tuple[DescriptorDocument, CurrentDescriptorPointer, bytes]:
    vector = build_vector()
    descriptor = vector["descriptor"]
    pointer = vector["pointer"]
    bundle = vector["bundle"]
    assert isinstance(descriptor, bytes)
    assert isinstance(pointer, bytes)
    assert isinstance(bundle, bytes)
    return (
        DescriptorDocument(format_id=DESCRIPTOR_VERSION, payload=descriptor),
        CurrentDescriptorPointer(format_id=CURRENT_POINTER_VERSION, payload=pointer),
        bundle,
    )


def pointer_variant(offset: int) -> CurrentDescriptorPointer:
    vector = build_vector()
    pointer = vector["pointer"]
    assert isinstance(pointer, bytes)
    payload = json.loads(pointer)["payload"]
    payload["expires_at"] += offset
    return CurrentDescriptorPointer(
        format_id=CURRENT_POINTER_VERSION,
        payload=create_current_pointer(payload, signer=signer(), key_id=KEY_ID),
    )


class DescriptorStoreContractMixin:
    store: Any

    def exercise_contract(self) -> None:
        testcase = self
        assert isinstance(testcase, unittest.TestCase)
        descriptor, pointer, bundle = objects()
        testcase.assertIsInstance(self.store, DescriptorStore)
        reference = self.store.publish_immutable(descriptor)
        testcase.assertEqual(self.store.publish_immutable(descriptor), reference)
        testcase.assertEqual(self.store.read(reference), descriptor)

        bundle_reference = self.store.create_bundle(
            subject_id=SUBJECT_ID,
            backup_id=BACKUP_ID,
            epoch=1,
            bundle=bundle,
        )
        testcase.assertEqual(
            self.store.create_bundle(
                subject_id=SUBJECT_ID,
                backup_id=BACKUP_ID,
                epoch=1,
                bundle=bundle,
            ),
            bundle_reference,
        )
        testcase.assertEqual(self.store.read_bundle(bundle_reference), bundle)
        testcase.assertNotEqual(reference.locator, bundle_reference.locator)

        with testcase.assertRaises(ObjectNotFound):
            self.store.read_current(RECOVERY_HANDLE)
        self.store.compare_and_swap_current(RECOVERY_HANDLE, None, pointer)
        self.store.compare_and_swap_current(RECOVERY_HANDLE, None, pointer)
        testcase.assertEqual(self.store.read_current(RECOVERY_HANDLE), pointer)
        successor = pointer_variant(1)
        self.store.compare_and_swap_current(RECOVERY_HANDLE, pointer, successor)
        self.store.compare_and_swap_current(RECOVERY_HANDLE, pointer, successor)
        with testcase.assertRaises(ObjectStale):
            self.store.compare_and_swap_current(
                RECOVERY_HANDLE, pointer, pointer_variant(2)
            )
        with testcase.assertRaises(ObjectConflict):
            self.store.compare_and_swap_current(
                RECOVERY_HANDLE, None, pointer_variant(2)
            )


class FilesystemDescriptorStoreTests(unittest.TestCase, DescriptorStoreContractMixin):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.store = FilesystemDescriptorBundleStore(self.temporary.name)

    def test_shared_descriptor_and_bundle_contract(self) -> None:
        self.exercise_contract()

    def test_exact_key_profile_vector_is_stable(self) -> None:
        descriptor, pointer, bundle = objects()
        descriptor_reference = self.store.publish_immutable(descriptor)
        bundle_reference = self.store.create_bundle(
            subject_id=SUBJECT_ID,
            backup_id=BACKUP_ID,
            epoch=1,
            bundle=bundle,
        )
        expected = dict(
            line.split("=", 1)
            for line in (ROOT / "docs/vectors/descriptor-store-v1.txt")
            .read_text(encoding="utf-8")
            .splitlines()
            if line and not line.startswith("#")
        )
        self.assertEqual(expected["profile"], DESCRIPTOR_STORE_PROFILE)
        self.assertEqual(expected["descriptor_locator"], descriptor_reference.locator)
        self.assertEqual(expected["bundle_locator"], bundle_reference.locator)
        self.store.compare_and_swap_current(RECOVERY_HANDLE, None, pointer)
        pointer_files = list((Path(self.temporary.name) / "current").glob("*.json"))
        self.assertEqual(len(pointer_files), 1)
        self.assertEqual(
            pointer_files[0].relative_to(self.temporary.name).as_posix(),
            expected["pointer_locator"],
        )

    def test_same_host_service_exposes_distinct_structural_contracts(self) -> None:
        service = SameHostDescriptorService(self.store)
        self.assertIsInstance(service.descriptor_store(), DescriptorStore)
        self.assertIsInstance(service.bundle_store(), RecoveryBundleStore)

    def test_concurrent_pointer_cas_has_one_winner_and_one_stale_writer(self) -> None:
        _descriptor, initial, _bundle = objects()
        self.store.compare_and_swap_current(RECOVERY_HANDLE, None, initial)
        barrier = threading.Barrier(3)
        outcomes: list[str] = []

        def update(replacement: CurrentDescriptorPointer) -> None:
            barrier.wait()
            try:
                self.store.compare_and_swap_current(
                    RECOVERY_HANDLE, initial, replacement
                )
                outcomes.append("updated")
            except ObjectStale:
                outcomes.append("stale")

        threads = [
            threading.Thread(target=update, args=(pointer_variant(index),))
            for index in (1, 2)
        ]
        for thread in threads:
            thread.start()
        barrier.wait()
        for thread in threads:
            thread.join()
        self.assertCountEqual(outcomes, ["updated", "stale"])

    def test_corrupt_substituted_and_oversized_files_fail_closed(self) -> None:
        descriptor, _pointer, bundle = objects()
        reference = self.store.publish_immutable(descriptor)
        path = Path(self.temporary.name) / reference.locator
        path.write_bytes(descriptor.payload + b" ")
        with self.assertRaises(ObjectCorrupt):
            self.store.read(reference)
        with self.assertRaises(ObjectConflict):
            self.store.publish_immutable(descriptor)

        bundle_reference = self.store.create_bundle(
            subject_id=SUBJECT_ID,
            backup_id=BACKUP_ID,
            epoch=1,
            bundle=bundle,
        )
        bundle_path = Path(self.temporary.name) / bundle_reference.locator
        bundle_path.write_bytes(b"x" * (MAX_BUNDLE_BYTES + 1))
        with self.assertRaises(ObjectTooLarge):
            self.store.read_bundle(bundle_reference)

    def test_symbolic_link_ancestor_cannot_escape_store_root(self) -> None:
        descriptor, _pointer, _bundle = objects()
        root = Path(self.temporary.name)
        outside = root.parent / f"{root.name}-outside"
        outside.mkdir()
        self.addCleanup(outside.rmdir)
        try:
            (root / "descriptors").symlink_to(outside, target_is_directory=True)
        except OSError as exc:
            self.skipTest(f"symbolic links unavailable: {exc}")
        with self.assertRaises(ObjectCorrupt):
            self.store.publish_immutable(descriptor)


class S3DescriptorStoreTests(unittest.TestCase, DescriptorStoreContractMixin):
    def setUp(self) -> None:
        self.client = FakeCasS3Client()
        self.store = S3DescriptorBundleStore(
            client=self.client,
            bucket="locus-descriptor-tests",
            prefix="contract/recovery",
        )

    def test_shared_descriptor_and_bundle_contract(self) -> None:
        self.exercise_contract()
        self.assertEqual(self.client.list_calls, 0)

    def test_etag_cas_rejects_concurrent_replacement(self) -> None:
        _descriptor, initial, _bundle = objects()
        self.store.compare_and_swap_current(RECOVERY_HANDLE, None, initial)
        successor = pointer_variant(1)
        original_put = self.client.put_object

        def racing_put(**kwargs: Any) -> dict[str, Any]:
            if "IfMatch" in kwargs:
                key = (kwargs["Bucket"], kwargs["Key"])
                body, _etag = self.client.objects[key]
                self.client.counter += 1
                self.client.objects[key] = (body, f'"race-{self.client.counter}"')
            return original_put(**kwargs)

        self.client.put_object = racing_put  # type: ignore[method-assign]
        with self.assertRaises(ObjectStale):
            self.store.compare_and_swap_current(RECOVERY_HANDLE, initial, successor)

    def test_s3_substitution_outage_and_oversize_are_explicit(self) -> None:
        descriptor, _pointer, bundle = objects()
        reference = self.store.publish_immutable(descriptor)
        key = (self.store.bucket, self.store._key(reference.locator))
        _body, etag = self.client.objects[key]
        self.client.objects[key] = (descriptor.payload + b" ", etag)
        with self.assertRaises(ObjectCorrupt):
            self.store.read(reference)

        bundle_reference = self.store.create_bundle(
            subject_id=SUBJECT_ID,
            backup_id=BACKUP_ID,
            epoch=1,
            bundle=bundle,
        )
        bundle_key = (self.store.bucket, self.store._key(bundle_reference.locator))
        _body, etag = self.client.objects[bundle_key]
        self.client.objects[bundle_key] = (b"x" * (MAX_BUNDLE_BYTES + 1), etag)
        with self.assertRaises(ObjectTooLarge):
            self.store.read_bundle(bundle_reference)

        self.client.available = False
        with self.assertRaises(ObjectStoreUnavailable):
            self.store.read(reference)


if __name__ == "__main__":
    unittest.main()
