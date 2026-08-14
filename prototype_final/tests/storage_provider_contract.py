"""One provider-level conformance suite for every LOCUS storage adapter."""

from __future__ import annotations

import unittest

from locus.contracts import DescriptorStore
from locus.object_store import (
    ObjectConflict,
    ObjectCorrupt,
    ObjectNotFound,
    ObjectStale,
)
from locus.storage_provider import StorageProvider
from tests.object_store_contract import exercise_backend_contract
from tests.test_descriptor_store import RECOVERY_HANDLE, objects, pointer_variant
from tests.test_recovery_descriptor import BACKUP_ID, SUBJECT_ID


def exercise_storage_provider_contract(
    testcase: unittest.TestCase, provider: StorageProvider
) -> None:
    """Exercise all four logical storage roles through one provider profile."""

    testcase.assertIsInstance(provider, StorageProvider)
    testcase.assertIsInstance(provider.descriptors, DescriptorStore)
    testcase.assertIs(provider.bundles, provider.descriptors)
    testcase.assertTrue(provider.properties.exact_reads_only)
    testcase.assertFalse(provider.properties.listing_required)
    testcase.assertTrue(provider.properties.immutable_backup_publication)
    testcase.assertTrue(provider.properties.immutable_descriptor_publication)
    testcase.assertTrue(provider.properties.current_pointer_cas)
    if provider.properties.network_scope == "nonlocal":
        testcase.assertEqual(provider.properties.transport, "tls")

    exercise_backend_contract(testcase, provider.backups)

    descriptor, pointer, bundle = objects()
    reference = provider.descriptors.publish_immutable(descriptor)
    testcase.assertEqual(provider.descriptors.publish_immutable(descriptor), reference)
    testcase.assertEqual(provider.descriptors.read(reference), descriptor)

    payload = descriptor.payload
    conflicting = type(descriptor)(
        format_id=descriptor.format_id,
        payload=payload[:-1] + (b"x" if payload[-1:] != b"x" else b"y"),
    )
    with testcase.assertRaises(ObjectCorrupt):
        provider.descriptors.publish_immutable(conflicting)

    bundle_reference = provider.bundles.create_bundle(
        subject_id=SUBJECT_ID,
        backup_id=BACKUP_ID,
        epoch=1,
        bundle=bundle,
    )
    testcase.assertEqual(
        provider.bundles.create_bundle(
            subject_id=SUBJECT_ID,
            backup_id=BACKUP_ID,
            epoch=1,
            bundle=bundle,
        ),
        bundle_reference,
    )
    testcase.assertEqual(provider.bundles.read_bundle(bundle_reference), bundle)
    testcase.assertNotEqual(reference.locator, bundle_reference.locator)

    with testcase.assertRaises(ObjectNotFound):
        provider.descriptors.read_current(RECOVERY_HANDLE)
    provider.descriptors.compare_and_swap_current(RECOVERY_HANDLE, None, pointer)
    provider.descriptors.compare_and_swap_current(RECOVERY_HANDLE, None, pointer)
    testcase.assertEqual(provider.descriptors.read_current(RECOVERY_HANDLE), pointer)
    successor = pointer_variant(1)
    provider.descriptors.compare_and_swap_current(RECOVERY_HANDLE, pointer, successor)
    provider.descriptors.compare_and_swap_current(RECOVERY_HANDLE, pointer, successor)
    with testcase.assertRaises(ObjectStale):
        provider.descriptors.compare_and_swap_current(
            RECOVERY_HANDLE, pointer, pointer_variant(2)
        )
    with testcase.assertRaises(ObjectConflict):
        provider.descriptors.compare_and_swap_current(
            RECOVERY_HANDLE, None, pointer_variant(2)
        )
