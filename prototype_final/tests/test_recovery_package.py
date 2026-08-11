from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from locus.client_api import ClientApiError
from locus.integrated_client import IntegratedResearchClientApi
from locus.recovery_bootstrap import RECOVERY_RECEIPT_VERSION
from locus.recovery_descriptor import BUNDLE_PROFILE
from locus.recovery_package import (
    MAX_RECOVERY_PACKAGE_BYTES,
    RECOVERY_PACKAGE_VERSION,
    RecoveryPackageError,
    create_recovery_package,
    decode_recovery_package,
)

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "docs" / "schemas" / "client-recovery-package-v1.schema.json"
VECTOR = ROOT / "docs" / "vectors" / "client-recovery-package-v1.json"


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


class RecoveryPackageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.receipt = b"operator-signed-public-receipt"
        self.bundle = b"encrypted-backup-and-authenticated-descriptor"
        self.encoded = create_recovery_package(
            receipt_bytes=self.receipt, bundle_bytes=self.bundle
        )

    def test_round_trip_is_deterministic_and_schema_identifiers_match(self) -> None:
        self.assertEqual(
            self.encoded,
            create_recovery_package(
                receipt_bytes=self.receipt, bundle_bytes=self.bundle
            ),
        )
        decoded = decode_recovery_package(self.encoded)
        self.assertEqual(decoded.receipt_bytes, self.receipt)
        self.assertEqual(decoded.bundle_bytes, self.bundle)
        schema = json.loads(SCHEMA.read_bytes())
        self.assertEqual(
            schema["properties"]["version"]["const"], RECOVERY_PACKAGE_VERSION
        )
        self.assertEqual(
            schema["$defs"]["receipt"]["properties"]["format"]["const"],
            RECOVERY_RECEIPT_VERSION,
        )
        self.assertEqual(
            schema["$defs"]["bundle"]["properties"]["format"]["const"],
            BUNDLE_PROFILE,
        )

    def test_retained_canonical_vector_and_live_authentication_boundary(self) -> None:
        vector = json.loads(VECTOR.read_bytes())
        self.assertEqual(
            set(vector),
            {
                "bundle_hex",
                "canonical_package_sha256",
                "canonical_package_utf8",
                "fixture_scope",
                "receipt_hex",
            },
        )
        expected = vector["canonical_package_utf8"].encode("utf-8")
        generated = create_recovery_package(
            receipt_bytes=bytes.fromhex(vector["receipt_hex"]),
            bundle_bytes=bytes.fromhex(vector["bundle_hex"]),
        )
        self.assertEqual(generated, expected)
        self.assertEqual(
            hashlib.sha256(generated).hexdigest(), vector["canonical_package_sha256"]
        )
        self.assertIn("codec-only", vector["fixture_scope"])

        client = object.__new__(IntegratedResearchClientApi)
        with patch.object(
            client,
            "_load",
            side_effect=ClientApiError("bootstrap_rejected"),
        ):
            with self.assertRaisesRegex(ClientApiError, "package_import_rejected"):
                client.authenticate_recovery_package(generated)

    def test_stale_package_bundle_cannot_replace_authenticated_current_state(
        self,
    ) -> None:
        client = object.__new__(IntegratedResearchClientApi)
        current = SimpleNamespace(
            bundle=SimpleNamespace(bundle_bytes=b"different-current-bundle")
        )
        with patch.object(client, "_load", return_value=current):
            with self.assertRaisesRegex(ClientApiError, "package_import_rejected"):
                client.authenticate_recovery_package(self.encoded)

    def test_unknown_missing_and_duplicate_members_are_rejected(self) -> None:
        value = json.loads(self.encoded)
        value["unexpected"] = True
        with self.assertRaises(RecoveryPackageError):
            decode_recovery_package(_canonical(value))
        value = json.loads(self.encoded)
        del value["receipt"]
        with self.assertRaises(RecoveryPackageError):
            decode_recovery_package(_canonical(value))
        duplicate = self.encoded.replace(
            b'{"bundle":',
            (b'{"version":"' + RECOVERY_PACKAGE_VERSION.encode() + b'","bundle":'),
            1,
        )
        with self.assertRaises(RecoveryPackageError):
            decode_recovery_package(duplicate)

    def test_version_format_digest_length_and_encoding_are_bound(self) -> None:
        mutations: list[dict[str, object]] = []
        version = json.loads(self.encoded)
        version["version"] = "LOCUS-client-recovery-package-v2"
        mutations.append(version)
        member_format = json.loads(self.encoded)
        member_format["bundle"]["format"] = "LOCUS-recovery-bundle-v2"
        mutations.append(member_format)
        digest = json.loads(self.encoded)
        digest["receipt"]["sha256"] = "00" * 32
        mutations.append(digest)
        length = json.loads(self.encoded)
        length["bundle"]["length"] += 1
        mutations.append(length)
        padded = json.loads(self.encoded)
        padded["receipt"]["value"] += "="
        mutations.append(padded)
        for value in mutations:
            with self.subTest(value=value):
                with self.assertRaises(RecoveryPackageError):
                    decode_recovery_package(_canonical(value))

    def test_noncanonical_and_oversized_encodings_are_rejected(self) -> None:
        with self.assertRaises(RecoveryPackageError):
            decode_recovery_package(b" " + self.encoded)
        with self.assertRaises(RecoveryPackageError):
            decode_recovery_package(b"x" * (MAX_RECOVERY_PACKAGE_BYTES + 1))
        with self.assertRaises(RecoveryPackageError):
            create_recovery_package(receipt_bytes=b"", bundle_bytes=self.bundle)


if __name__ == "__main__":
    unittest.main()
