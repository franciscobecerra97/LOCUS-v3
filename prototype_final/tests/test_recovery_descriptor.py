from __future__ import annotations

import copy
import hashlib
import io
import json
import unittest
import warnings
import zipfile
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from locus.codec import encode
from locus.object_store import backup_digest
from locus.recovery_descriptor import (
    BACKUP_MEMBER,
    BUNDLE_MANIFEST_VERSION,
    BUNDLE_MEMBERS,
    BUNDLE_PROFILE,
    CONFIGURATION_VERSION,
    CURRENT_POINTER_VERSION,
    DESCRIPTOR_MEMBER,
    DESCRIPTOR_VERSION,
    MANIFEST_MEMBER,
    MAX_BACKUP_MEMBER_BYTES,
    MAX_DESCRIPTOR_BYTES,
    SIGNATURE_VERSION,
    RecoveryDescriptorError,
    configuration_digest,
    create_bundle,
    create_current_pointer,
    create_descriptor,
    create_manifest,
    decode_bundle,
    decode_current_pointer,
    decode_descriptor,
    decode_manifest,
    validate_descriptor_payload,
    verify_current_pointer_bundle,
)

ROOT = Path(__file__).resolve().parents[1]
VECTOR_PATH = ROOT / "docs/vectors/recovery-descriptor-v1.txt"
DESCRIPTOR_SCHEMA_PATH = ROOT / "docs/schemas/recovery-descriptor-v1.schema.json"
POINTER_SCHEMA_PATH = ROOT / "docs/schemas/descriptor-current-pointer-v1.schema.json"
MANIFEST_SCHEMA_PATH = ROOT / "docs/schemas/recovery-bundle-manifest-v1.schema.json"
ISSUER = "test-only-locus-issuer"
KEY_ID = "test-only-root-key-1"
SUBJECT_ID = "11" * 32
BACKUP_ID = "22" * 16
CONFIGURATION_INPUT_VERSION = CONFIGURATION_VERSION


def signer() -> Ed25519PrivateKey:
    return Ed25519PrivateKey.from_private_bytes(bytes(range(32)))


def public_key_hex() -> str:
    return (
        signer()
        .public_key()
        .public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        .hex()
    )


def synthetic_backup() -> dict[str, Any]:
    backup: dict[str, Any] = {
        "version": "LOCUS-reference-backup-v4",
        "bid": BACKUP_ID,
        "epoch": 1,
        "nonce": "33" * 16,
        "ciphertext": {
            "algorithm": "AES-256-GCM",
            "ciphertext": "44" * 48,
            "nonce": "55" * 12,
            "version": "LOCUS-AES-256-GCM-v1",
        },
        "tpass_public_params": {
            "backend": "yi-zk-ristretto255-native-v1",
            "encoding": "LOCUS-TPASS-wire-v1",
            "parameters": "dGVzdC1vbmx5LXBhcmFtZXRlcnM",
            "parties": 3,
            "threshold": 2,
        },
        "context_policy": {"version": "LOCUS-location-person-set-v1"},
        "security_policy": {
            "cooldown_seconds": 0,
            "max_attempts": 10,
            "version": "LOCUS-security-policy-v1",
        },
    }
    backup["digest"] = backup_digest(backup)
    return backup


def descriptor_payload(backup_bytes: bytes) -> dict[str, Any]:
    public_state = encode(synthetic_backup()["tpass_public_params"])
    payload: dict[str, Any] = {
        "authorization": {
            "admission_profile": "test-only:unassigned-p3.3",
            "audience": "locus-recovery",
            "authorizers": [
                {
                    "authorizer_id": party_id,
                    "endpoint": f"https://party-{party_id}.invalid/",
                    "identity_key_id": f"test-only-party-key-{party_id}",
                }
                for party_id in range(1, 6)
            ],
            "operation_namespace": "locus-recovery",
            "quorum": 4,
            "security_policy": "LOCUS-security-policy-v1",
        },
        "backup": {
            "format": "LOCUS-reference-backup-v4",
            "length": len(backup_bytes),
            "member": BACKUP_MEMBER,
            "sha256": hashlib.sha256(backup_bytes).hexdigest(),
        },
        "backup_id": BACKUP_ID,
        "cue_policy": {
            "id": "LOCUS-location-person-set-v1",
            "public_parameters_hex": encode({"cardinality": 3}).hex(),
            "resolver_profile": "LOCUS-deterministic-directory-v1",
        },
        "epoch": 1,
        "expires_at": 1893456000,
        "issued_at": 1767225600,
        "issuer": ISSUER,
        "lifecycle": {
            "configuration_digest": "00" * 32,
            "predecessor_descriptor_digest": None,
        },
        "recovery_id": f"test-only-recovery:{BACKUP_ID}:1",
        "recovery_suite": {
            "holders": [
                {"authorizer_id": party_id, "holder_id": party_id}
                for party_id in range(1, 4)
            ],
            "id": "LOCUS-TPASS-YI-ZK-RISTRETTO255-v1",
            "public_state_format": "LOCUS-TPASS-wire-v1",
            "public_state_hex": public_state.hex(),
            "threshold": {"k": 2, "n": 3},
        },
        "subject_id": SUBJECT_ID,
    }
    lifecycle = payload["lifecycle"]
    assert isinstance(lifecycle, dict)
    lifecycle["configuration_digest"] = configuration_digest(payload)
    return payload


def build_vector() -> dict[str, Any]:
    backup_bytes = encode(synthetic_backup())
    payload = descriptor_payload(backup_bytes)
    descriptor_bytes = create_descriptor(payload, signer=signer(), key_id=KEY_ID)
    manifest_bytes = create_manifest(
        backup_bytes=backup_bytes,
        descriptor_bytes=descriptor_bytes,
        backup_format="LOCUS-reference-backup-v4",
    )
    bundle_bytes = create_bundle(
        backup_bytes=backup_bytes,
        descriptor_bytes=descriptor_bytes,
        backup_format="LOCUS-reference-backup-v4",
    )
    pointer_payload = {
        "backup_id": BACKUP_ID,
        "bundle": {
            "length": len(bundle_bytes),
            "locator": "test-only:immutable-bundle-locator",
            "profile": BUNDLE_PROFILE,
            "sha256": hashlib.sha256(bundle_bytes).hexdigest(),
        },
        "configuration_digest": payload["lifecycle"]["configuration_digest"],
        "descriptor_sha256": hashlib.sha256(descriptor_bytes).hexdigest(),
        "epoch": 1,
        "expires_at": 1893456000,
        "issued_at": 1767225600,
        "issuer": ISSUER,
        "subject_id": SUBJECT_ID,
    }
    pointer_bytes = create_current_pointer(
        pointer_payload, signer=signer(), key_id=KEY_ID
    )
    return {
        "backup": backup_bytes,
        "bundle": bundle_bytes,
        "descriptor": descriptor_bytes,
        "issuer_public_key": public_key_hex(),
        "manifest": manifest_bytes,
        "pointer": pointer_bytes,
    }


def load_vector() -> dict[str, str]:
    return {
        key: value
        for line in VECTOR_PATH.read_text(encoding="ascii").splitlines()
        if line and not line.startswith("#")
        for key, value in [line.split("=", maxsplit=1)]
    }


def zip_with_members(
    members: list[tuple[str, bytes]], *, compression: int = zipfile.ZIP_STORED
) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=compression) as archive:
        for name, content in members:
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = compression
            info.create_system = 3
            info.create_version = 20
            info.extract_version = 20
            info.external_attr = 0o100600 << 16
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                archive.writestr(info, content)
    return output.getvalue()


class RecoveryDescriptorTests(unittest.TestCase):
    def test_schemas_freeze_exact_versions_shapes_and_limits(self) -> None:
        descriptor_schema = json.loads(
            DESCRIPTOR_SCHEMA_PATH.read_text(encoding="utf-8")
        )
        pointer_schema = json.loads(POINTER_SCHEMA_PATH.read_text(encoding="utf-8"))
        manifest_schema = json.loads(MANIFEST_SCHEMA_PATH.read_text(encoding="utf-8"))
        self.assertFalse(descriptor_schema["additionalProperties"])
        self.assertEqual(
            descriptor_schema["properties"]["version"]["const"],
            DESCRIPTOR_VERSION,
        )
        self.assertFalse(descriptor_schema["$defs"]["payload"]["additionalProperties"])
        self.assertEqual(
            descriptor_schema["$defs"]["payload"]["properties"]["backup"]["properties"][
                "length"
            ]["maximum"],
            MAX_BACKUP_MEMBER_BYTES,
        )
        self.assertEqual(
            pointer_schema["properties"]["version"]["const"],
            CURRENT_POINTER_VERSION,
        )
        self.assertFalse(
            pointer_schema["properties"]["payload"]["additionalProperties"]
        )
        self.assertEqual(
            manifest_schema["properties"]["version"]["const"],
            BUNDLE_MANIFEST_VERSION,
        )
        prefix = manifest_schema["properties"]["members"]["prefixItems"]
        self.assertEqual(
            [item["properties"]["name"]["const"] for item in prefix],
            [BACKUP_MEMBER, DESCRIPTOR_MEMBER],
        )
        self.assertFalse(manifest_schema["properties"]["members"]["items"])

    def test_canonical_descriptor_bundle_and_pointer_round_trip(self) -> None:
        vector = build_vector()
        descriptor = decode_descriptor(
            vector["descriptor"],
            issuer_public_key=signer().public_key(),
            expected_issuer=ISSUER,
            expected_key_id=KEY_ID,
        )
        bundle = decode_bundle(
            vector["bundle"],
            issuer_public_key=signer().public_key(),
            expected_issuer=ISSUER,
            expected_key_id=KEY_ID,
        )
        pointer = decode_current_pointer(
            vector["pointer"],
            issuer_public_key=signer().public_key(),
            expected_issuer=ISSUER,
            expected_key_id=KEY_ID,
        )
        verify_current_pointer_bundle(pointer, bundle)
        self.assertEqual(descriptor, bundle.descriptor)
        self.assertEqual(bundle.backup, synthetic_backup())
        self.assertEqual(bundle.manifest["version"], BUNDLE_MANIFEST_VERSION)
        self.assertEqual(pointer["version"], CURRENT_POINTER_VERSION)

    def test_pinned_canonical_vectors_are_stable(self) -> None:
        generated = build_vector()
        vector = load_vector()
        self.assertEqual(vector["issuer_public_key"], generated["issuer_public_key"])
        for name in ("backup", "descriptor", "manifest", "pointer"):
            value = generated[name]
            assert isinstance(value, bytes)
            self.assertEqual(
                vector[f"{name}_sha256"], hashlib.sha256(value).hexdigest()
            )
            self.assertEqual(int(vector[f"{name}_length"]), len(value))
        bundle = generated["bundle"]
        assert isinstance(bundle, bytes)
        self.assertEqual(vector["bundle_sha256"], hashlib.sha256(bundle).hexdigest())
        self.assertEqual(int(vector["bundle_length"]), len(bundle))
        descriptor = json.loads(generated["descriptor"])
        pointer = json.loads(generated["pointer"])
        self.assertEqual(
            vector["configuration_digest"],
            descriptor["payload"]["lifecycle"]["configuration_digest"],
        )
        self.assertEqual(
            vector["descriptor_signature"], descriptor["signature"]["value"]
        )
        self.assertEqual(vector["pointer_signature"], pointer["signature"]["value"])

    def test_descriptor_rejects_noncanonical_duplicate_unknown_and_oversized(
        self,
    ) -> None:
        descriptor_bytes = build_vector()["descriptor"]
        assert isinstance(descriptor_bytes, bytes)
        parsed = json.loads(descriptor_bytes)
        unsupported = copy.deepcopy(parsed)
        unsupported["version"] = "future-descriptor"
        wrong_algorithm = copy.deepcopy(parsed)
        wrong_algorithm["signature"]["algorithm"] = "future-signature"
        missing = copy.deepcopy(parsed)
        del missing["payload"]["backup"]
        mutations = [
            json.dumps(parsed, indent=2).encode("ascii"),
            descriptor_bytes.replace(b'{"payload":', b'{"unknown":1,"payload":', 1),
            (
                b'{"payload":{},"payload":{},"signature":{},'
                b'"version":"LOCUS-recovery-descriptor-v1"}'
            ),
            descriptor_bytes + b" ",
            b"x" * (MAX_DESCRIPTOR_BYTES + 1),
            encode(unsupported),
            encode(wrong_algorithm),
            encode(missing),
        ]
        for encoded in mutations:
            with self.subTest(size=len(encoded)):
                with self.assertRaises(RecoveryDescriptorError):
                    decode_descriptor(
                        encoded,
                        issuer_public_key=signer().public_key(),
                        expected_issuer=ISSUER,
                        expected_key_id=KEY_ID,
                    )

    def test_descriptor_signature_and_external_trust_root_fail_closed(self) -> None:
        descriptor_bytes = build_vector()["descriptor"]
        assert isinstance(descriptor_bytes, bytes)
        parsed = json.loads(descriptor_bytes)
        parsed["payload"]["expires_at"] += 1
        tampered = encode(parsed)

        with self.assertRaises(RecoveryDescriptorError):
            decode_descriptor(
                tampered,
                issuer_public_key=signer().public_key(),
                expected_issuer=ISSUER,
                expected_key_id=KEY_ID,
            )

        for public_key, issuer, key_id in (
            (
                Ed25519PrivateKey.from_private_bytes(
                    bytes(reversed(range(32)))
                ).public_key(),
                ISSUER,
                KEY_ID,
            ),
            (signer().public_key(), "another-issuer", KEY_ID),
            (signer().public_key(), ISSUER, "another-key"),
        ):
            with self.subTest(issuer=issuer, key_id=key_id):
                with self.assertRaises(RecoveryDescriptorError):
                    decode_descriptor(
                        descriptor_bytes,
                        issuer_public_key=public_key,
                        expected_issuer=issuer,
                        expected_key_id=key_id,
                    )

    def test_descriptor_membership_threshold_and_configuration_are_distinct(
        self,
    ) -> None:
        backup_bytes = encode(synthetic_backup())
        valid = descriptor_payload(backup_bytes)
        invalid_values: list[dict[str, Any]] = []

        mixed_holder = copy.deepcopy(valid)
        mixed_holder["recovery_suite"]["holders"][0]["authorizer_id"] = 9
        invalid_values.append(mixed_holder)

        conflated = copy.deepcopy(valid)
        conflated["authorization"]["quorum"] = 6
        invalid_values.append(conflated)

        duplicate_holder = copy.deepcopy(valid)
        duplicate_holder["recovery_suite"]["holders"][1]["holder_id"] = 1
        invalid_values.append(duplicate_holder)

        wrong_config = copy.deepcopy(valid)
        wrong_config["cue_policy"]["id"] = "future-policy"
        invalid_values.append(wrong_config)

        for payload in invalid_values:
            with self.assertRaises(RecoveryDescriptorError):
                validate_descriptor_payload(payload)

    def test_manifest_binds_only_backup_and_descriptor_without_self_digest(
        self,
    ) -> None:
        generated = build_vector()
        manifest_bytes = generated["manifest"]
        assert isinstance(manifest_bytes, bytes)
        manifest = decode_manifest(manifest_bytes)
        self.assertEqual(
            [member["name"] for member in manifest["members"]],
            [BACKUP_MEMBER, DESCRIPTOR_MEMBER],
        )
        self.assertNotIn(MANIFEST_MEMBER, manifest_bytes.decode("ascii"))
        self.assertNotIn("manifest_sha256", manifest)
        descriptor = json.loads(generated["descriptor"])
        self.assertNotIn("bundle", descriptor["payload"])
        self.assertNotIn("locator", descriptor["payload"])

        extra = copy.deepcopy(manifest)
        extra["unexpected"] = 1
        missing = copy.deepcopy(manifest)
        missing["members"].pop()
        self_member = copy.deepcopy(manifest)
        self_member["members"][1]["name"] = MANIFEST_MEMBER
        for invalid in (extra, missing, self_member):
            with self.assertRaises(RecoveryDescriptorError):
                decode_manifest(encode(invalid))

    def test_current_pointer_rejects_unknown_missing_and_unsupported_fields(
        self,
    ) -> None:
        pointer_bytes = build_vector()["pointer"]
        assert isinstance(pointer_bytes, bytes)
        parsed = json.loads(pointer_bytes)
        extra = copy.deepcopy(parsed)
        extra["payload"]["unexpected"] = 1
        missing = copy.deepcopy(parsed)
        del missing["payload"]["descriptor_sha256"]
        unsupported = copy.deepcopy(parsed)
        unsupported["payload"]["bundle"]["profile"] = "future-bundle"
        wrong_version = copy.deepcopy(parsed)
        wrong_version["version"] = "future-pointer"
        for invalid in (extra, missing, unsupported, wrong_version):
            with self.assertRaises(RecoveryDescriptorError):
                decode_current_pointer(
                    encode(invalid),
                    issuer_public_key=signer().public_key(),
                    expected_issuer=ISSUER,
                    expected_key_id=KEY_ID,
                )

    def test_bundle_rejects_member_set_path_compression_flags_and_trailing_data(
        self,
    ) -> None:
        generated = build_vector()
        backup = generated["backup"]
        descriptor = generated["descriptor"]
        manifest = generated["manifest"]
        assert isinstance(backup, bytes)
        assert isinstance(descriptor, bytes)
        assert isinstance(manifest, bytes)
        cases = {
            "missing": zip_with_members(
                [(BACKUP_MEMBER, backup), (DESCRIPTOR_MEMBER, descriptor)]
            ),
            "unknown": zip_with_members(
                [
                    (BACKUP_MEMBER, backup),
                    (DESCRIPTOR_MEMBER, descriptor),
                    ("unknown.json", manifest),
                ]
            ),
            "nested": zip_with_members(
                [
                    (BACKUP_MEMBER, backup),
                    (DESCRIPTOR_MEMBER, descriptor),
                    ("nested/manifest.json", manifest),
                ]
            ),
            "duplicate": zip_with_members(
                [
                    (BACKUP_MEMBER, backup),
                    (BACKUP_MEMBER, backup),
                    (MANIFEST_MEMBER, manifest),
                ]
            ),
            "unsupported-compression": zip_with_members(
                [
                    (BACKUP_MEMBER, backup),
                    (DESCRIPTOR_MEMBER, descriptor),
                    (MANIFEST_MEMBER, manifest),
                ],
                compression=zipfile.ZIP_DEFLATED,
            ),
            "over-compressed": zip_with_members(
                [
                    (BACKUP_MEMBER, b"A" * 100_000),
                    (DESCRIPTOR_MEMBER, descriptor),
                    (MANIFEST_MEMBER, manifest),
                ],
                compression=zipfile.ZIP_DEFLATED,
            ),
            "oversized": zip_with_members(
                [
                    (BACKUP_MEMBER, b"A" * (MAX_BACKUP_MEMBER_BYTES + 1)),
                    (DESCRIPTOR_MEMBER, descriptor),
                    (MANIFEST_MEMBER, manifest),
                ]
            ),
            "trailing": generated["bundle"] + b"trailing",
        }
        for label, bundle_bytes in cases.items():
            assert isinstance(bundle_bytes, bytes)
            with self.subTest(label=label):
                with self.assertRaises(RecoveryDescriptorError):
                    decode_bundle(
                        bundle_bytes,
                        issuer_public_key=signer().public_key(),
                        expected_issuer=ISSUER,
                        expected_key_id=KEY_ID,
                    )

        encrypted = bytearray(generated["bundle"])
        central = encrypted.find(b"PK\x01\x02")
        self.assertGreater(central, 0)
        encrypted[6:8] = (1).to_bytes(2, "little")
        encrypted[central + 8 : central + 10] = (1).to_bytes(2, "little")
        with self.assertRaises(RecoveryDescriptorError):
            decode_bundle(
                bytes(encrypted),
                issuer_public_key=signer().public_key(),
                expected_issuer=ISSUER,
                expected_key_id=KEY_ID,
            )

    def test_bundle_and_pointer_cross_bindings_fail_closed(self) -> None:
        generated = build_vector()
        bundle = decode_bundle(
            generated["bundle"],
            issuer_public_key=signer().public_key(),
            expected_issuer=ISSUER,
            expected_key_id=KEY_ID,
        )
        pointer = decode_current_pointer(
            generated["pointer"],
            issuer_public_key=signer().public_key(),
            expected_issuer=ISSUER,
            expected_key_id=KEY_ID,
        )
        wrong_pointer = copy.deepcopy(pointer)
        wrong_pointer["payload"]["bundle"]["sha256"] = "00" * 32
        with self.assertRaises(RecoveryDescriptorError):
            verify_current_pointer_bundle(wrong_pointer, bundle)

        changed_backup = bytearray(generated["backup"])
        changed_backup[-2] = ord("1") if changed_backup[-2] != ord("1") else ord("2")
        changed_bundle = create_bundle(
            backup_bytes=bytes(changed_backup),
            descriptor_bytes=generated["descriptor"],
            backup_format="LOCUS-reference-backup-v4",
        )
        with self.assertRaises(RecoveryDescriptorError):
            decode_bundle(
                changed_bundle,
                issuer_public_key=signer().public_key(),
                expected_issuer=ISSUER,
                expected_key_id=KEY_ID,
            )

    def test_disclosure_surface_contains_no_cue_or_secret_verifier(self) -> None:
        generated = build_vector()
        public_objects = b"".join(
            generated[name]
            for name in ("descriptor", "manifest", "pointer")
            if isinstance(generated[name], bytes)
        ).lower()
        forbidden = (
            b"raw_cue",
            b"cue_hash",
            b"candidate_hint",
            b"password_authenticator",
            b"password_input",
            b"p_m",
            b"z_m",
            b"recovery_secret",
            b"wrapping_key",
            b"private_key",
            b"issuer_public_key",
            b"trust_root",
        )
        for marker in forbidden:
            with self.subTest(marker=marker):
                self.assertNotIn(marker, public_objects)
        positive_control = public_objects + b'{"cue_hash":"fictional-control"}'
        self.assertIn(b"cue_hash", positive_control)
        self.assertEqual(CONFIGURATION_INPUT_VERSION, "LOCUS-recovery-configuration-v1")
        self.assertEqual(DESCRIPTOR_VERSION, "LOCUS-recovery-descriptor-v1")
        self.assertEqual(SIGNATURE_VERSION, "LOCUS-bootstrap-signature-v1")
        self.assertEqual(
            BUNDLE_MEMBERS, (BACKUP_MEMBER, DESCRIPTOR_MEMBER, MANIFEST_MEMBER)
        )


if __name__ == "__main__":
    unittest.main()
