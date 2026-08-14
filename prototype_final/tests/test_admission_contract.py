from __future__ import annotations

import copy
import unittest
from pathlib import Path

from locus.admission import (
    ADMISSION_BINDING_FORMAT,
    LOCAL_ISSUER_PROFILE,
    MAX_ADMISSION_BYTES,
    RECOVERY_OPERATION,
    AdmissionBinding,
    AdmissionContractError,
    client_key_thumbprint,
    decode_binding,
    pseudonymous_object_prefix,
)

ROOT = Path(__file__).resolve().parents[1]
VECTOR_PATH = ROOT / "docs/vectors/admission-binding-v1.txt"
SUBJECT = "11" * 32
BACKUP_ID = "22" * 16


def recovery_binding() -> AdmissionBinding:
    return AdmissionBinding(
        subject=SUBJECT,
        backup_id=BACKUP_ID,
        epoch=7,
        operation=RECOVERY_OPERATION,
        audience="locus-authorizer-1",
        client_key_thumbprint=client_key_thumbprint(bytes(range(32))),
        nonce="33" * 32,
        issued_at=2_000_000_000,
        expires_at=2_000_000_120,
        issuer="locus-local-test-issuer",
    )


def vector() -> dict[str, str]:
    return dict(
        line.split("=", 1)
        for line in VECTOR_PATH.read_text(encoding="utf-8").splitlines()
    )


class AdmissionContractTests(unittest.TestCase):
    def test_recovery_and_storage_vectors_are_stable(self) -> None:
        expected = vector()
        binding = recovery_binding()
        self.assertEqual(binding.format_id, ADMISSION_BINDING_FORMAT)
        self.assertEqual(binding.profile_id, LOCAL_ISSUER_PROFILE)
        self.assertEqual(
            binding.client_key_thumbprint, expected["client_key_thumbprint"]
        )
        self.assertEqual(binding.digest, expected["binding_digest"])
        self.assertEqual(decode_binding(binding.canonical_bytes), binding)

        prefix = pseudonymous_object_prefix(SUBJECT, BACKUP_ID)
        self.assertEqual(prefix, expected["storage_prefix"])
        storage = AdmissionBinding(
            **{
                **binding.__dict__,
                "audience": "locus-storage-gateway",
                "object_prefix": prefix,
                "operation": "storage_read_exact",
            }
        )
        self.assertEqual(storage.digest, expected["storage_binding_digest"])

    def test_scope_lifetime_and_canonical_decoding_fail_closed(self) -> None:
        binding = recovery_binding()
        mutations: list[dict[str, object]] = [
            {"operation": "recover"},
            {"object_prefix": "subjects/public/"},
            {"expires_at": binding.issued_at},
            {"expires_at": binding.issued_at + 301},
            {"subject": "synthetic-subject"},
            {"backup_id": "AA" * 16},
            {"client_key_thumbprint": "00"},
            {"nonce": "44"},
            {"profile_id": "optional-oidc-profile"},
            {"format_id": ADMISSION_BINDING_FORMAT + "-unsupported"},
        ]
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                with self.assertRaises(AdmissionContractError):
                    AdmissionBinding(**{**binding.__dict__, **mutation}).validate()

        encoded = binding.canonical_bytes
        rejected = [
            encoded + b" ",
            encoded.replace(b'"epoch":7', b'"epoch":7,"epoch":7'),
            encoded.replace(b'"epoch":7', b'"extra":0,"epoch":7'),
            b"{" + b"a" * MAX_ADMISSION_BYTES + b"}",
            b'{"epoch":NaN}',
        ]
        for candidate in rejected:
            with self.assertRaises(AdmissionContractError):
                decode_binding(candidate)

    def test_storage_prefix_is_subject_and_backup_specific(self) -> None:
        prefix = pseudonymous_object_prefix(SUBJECT, BACKUP_ID)
        self.assertNotEqual(prefix, pseudonymous_object_prefix("12" * 32, BACKUP_ID))
        self.assertNotEqual(prefix, pseudonymous_object_prefix(SUBJECT, "23" * 16))
        storage = copy.copy(recovery_binding())
        with self.assertRaises(AdmissionContractError):
            AdmissionBinding(
                **{
                    **storage.__dict__,
                    "operation": "storage_read_exact",
                    "object_prefix": prefix + "other/",
                }
            ).validate()


if __name__ == "__main__":
    unittest.main()
