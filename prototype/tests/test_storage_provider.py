from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from locus.object_store import ObjectStoreUnavailable
from locus.storage_provider import (
    FILESYSTEM_PROVIDER_ID,
    S3_COMPATIBLE_PROVIDER_ID,
    FilesystemStorageProvider,
    S3CompatibleStorageProvider,
    StorageProviderProperties,
)

from tests.storage_provider_contract import exercise_storage_provider_contract
from tests.test_descriptor_store import FakeCasS3Client, objects


class FilesystemStorageProviderTests(unittest.TestCase):
    def test_common_provider_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            provider = FilesystemStorageProvider(Path(temporary) / "provider")
            exercise_storage_provider_contract(self, provider)
            self.assertEqual(provider.properties.provider_id, FILESYSTEM_PROVIDER_ID)
            self.assertEqual(provider.properties.credential_mode, "none")


class S3CompatibleStorageProviderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = FakeCasS3Client()
        self.provider = S3CompatibleStorageProvider(
            client=self.client,
            bucket="locus-provider-tests",
            backup_prefix="account/test/backups",
            descriptor_prefix="account/test/recovery",
        )

    def test_common_provider_contract(self) -> None:
        exercise_storage_provider_contract(self, self.provider)
        self.assertEqual(
            self.provider.properties.provider_id, S3_COMPATIBLE_PROVIDER_ID
        )
        self.assertEqual(
            self.provider.properties.credential_mode, "explicit-prefix-scoped"
        )
        self.assertEqual(self.client.list_calls, 0)

    def test_outage_maps_without_credential_or_client_disclosure(self) -> None:
        descriptor, _pointer, _bundle = objects()
        reference = self.provider.descriptors.publish_immutable(descriptor)
        self.client.available = False
        with self.assertRaises(ObjectStoreUnavailable) as failure:
            self.provider.descriptors.read(reference)
        self.assertNotIn("FakeCasS3Client", str(failure.exception))
        self.assertNotIn("client", repr(self.provider).lower())

    def test_nonlocal_plaintext_profile_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "requires TLS"):
            StorageProviderProperties(
                provider_id=S3_COMPATIBLE_PROVIDER_ID,
                network_scope="nonlocal",
                transport="local-test-plaintext",
                credential_mode="explicit-prefix-scoped",
            )


if __name__ == "__main__":
    unittest.main()
