"""Shared behavioral contract for filesystem and S3 backup adapters."""

from __future__ import annotations

import copy
import unittest
from typing import Any

from locus.core import LocusError, backup_digest, enroll, recover_from_store
from locus.object_store import (
    BackupObjectStore,
    BackupReference,
    ObjectConflict,
    ObjectNotFound,
)


def sample_cues() -> list[dict[str, dict[str, Any]]]:
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


def exercise_backend_contract(
    testcase: unittest.TestCase, store: BackupObjectStore
) -> None:
    """Exercise semantics that every separated object backend must preserve."""

    enrollment = enroll(
        user_id="s3-contract-user",
        private_key=b"backend-contract-private-key",
        cues=sample_cues(),
        threshold=2,
        parties=3,
        object_store=store,
    )
    reference = BackupReference.from_dict(enrollment.cloud_reference)
    testcase.assertEqual(store.create(enrollment.backup), reference)
    testcase.assertEqual(store.read(reference), enrollment.backup)
    testcase.assertEqual(
        recover_from_store(
            user_id="s3-contract-user",
            cloud_reference=reference.to_dict(),
            object_store=store,
            party_records=enrollment.parties[:2],
            cues=sample_cues(),
        ),
        b"backend-contract-private-key",
    )

    changed = copy.deepcopy(enrollment.backup)
    changed["ciphertext"]["ciphertext"] = (
        "00" if changed["ciphertext"]["ciphertext"][:2] != "00" else "ff"
    ) + changed["ciphertext"]["ciphertext"][2:]
    changed["digest"] = backup_digest(changed)
    with testcase.assertRaises(ObjectConflict):
        store.create(changed)

    store.delete(reference)
    with testcase.assertRaises(ObjectNotFound):
        store.read(reference)
    attempts_before = [party["attempt_count"] for party in enrollment.parties]
    with testcase.assertRaisesRegex(LocusError, "backup unavailable or invalid"):
        recover_from_store(
            user_id="s3-contract-user",
            cloud_reference=reference.to_dict(),
            object_store=store,
            party_records=enrollment.parties[:2],
            cues=sample_cues(),
        )
    testcase.assertEqual(
        [party["attempt_count"] for party in enrollment.parties], attempts_before
    )
