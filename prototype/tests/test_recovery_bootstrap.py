from __future__ import annotations

import copy
import hashlib
import json
import unittest
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from locus.codec import encode
from locus.recovery_bootstrap import (
    BOOTSTRAP_PROFILE,
    PARTY_CURRENT_SIGNATURE_VERSION,
    PARTY_CURRENT_SUMMARY_VERSION,
    RECOVERY_RECEIPT_VERSION,
    TRUST_CONFIGURATION_VERSION,
    BootstrapFailureCode,
    PartyCurrentObservation,
    RecoveryBootstrapError,
    authenticate_recovery_bootstrap,
    create_party_current_summary,
    create_recovery_receipt,
    decode_party_current_summary,
    decode_recovery_receipt,
    decode_trust_configuration,
    validate_trust_configuration_update,
)
from locus.recovery_descriptor import RecoveryDescriptorError

from tests.test_recovery_descriptor import (
    BACKUP_ID,
    ISSUER,
    KEY_ID,
    SUBJECT_ID,
    build_vector,
    signer,
)

ROOT = Path(__file__).resolve().parents[2]
VECTOR_PATH = ROOT / "prototype/test-vectors/recovery-bootstrap-v1.txt"
NOW = 1_800_000_000
RECOVERY_HANDLE = f"test-only-recovery:{BACKUP_ID}:1"
DISCOVERY_ENDPOINT = "https://discovery.invalid/"
DISCOVERY_AUDIENCE = "locus-storage-gateway"


def party_signer(authorizer_id: int) -> Ed25519PrivateKey:
    return Ed25519PrivateKey.from_private_bytes(bytes([authorizer_id]) * 32)


def public_hex(private_key: Ed25519PrivateKey) -> str:
    return (
        private_key.public_key()
        .public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        .hex()
    )


def trust_configuration() -> dict[str, Any]:
    return {
        "discovery": {
            "audience": DISCOVERY_AUDIENCE,
            "endpoint": DISCOVERY_ENDPOINT,
        },
        "generation": 1,
        "operator": {
            "issuer": ISSUER,
            "key_id": KEY_ID,
            "public_key_hex": public_hex(signer()),
        },
        "parties": [
            {
                "authorizer_id": party_id,
                "endpoint": f"https://party-{party_id}.invalid/",
                "identity_key_id": f"test-only-party-key-{party_id}",
                "public_key_hex": public_hex(party_signer(party_id)),
            }
            for party_id in range(1, 6)
        ],
        "previous_configuration_sha256": None,
        "profile": BOOTSTRAP_PROFILE,
        "valid_from": 1_767_225_600,
        "valid_until": 1_893_456_000,
        "version": TRUST_CONFIGURATION_VERSION,
    }


def descriptor_parts() -> tuple[bytes, bytes, dict[str, Any]]:
    vector = build_vector()
    pointer = vector["pointer"]
    bundle = vector["bundle"]
    descriptor_bytes = vector["descriptor"]
    assert isinstance(pointer, bytes)
    assert isinstance(bundle, bytes)
    assert isinstance(descriptor_bytes, bytes)
    return pointer, bundle, json.loads(descriptor_bytes)


def summary_payload(
    authorizer_id: int, *, overrides: dict[str, Any] | None = None
) -> dict[str, Any]:
    vector = build_vector()
    descriptor_bytes = vector["descriptor"]
    assert isinstance(descriptor_bytes, bytes)
    descriptor = json.loads(descriptor_bytes)
    payload = descriptor["payload"]
    result: dict[str, Any] = {
        "authorizer_id": authorizer_id,
        "backup_id": payload["backup_id"],
        "configuration_digest": payload["lifecycle"]["configuration_digest"],
        "cue_policy_id": payload["cue_policy"]["id"],
        "descriptor_sha256": hashlib.sha256(descriptor_bytes).hexdigest(),
        "epoch": payload["epoch"],
        "expires_at": NOW + 120,
        "issued_at": NOW - 30,
        "recovery_id": payload["recovery_id"],
        "recovery_suite_id": payload["recovery_suite"]["id"],
        "state": "active",
        "subject_id": payload["subject_id"],
    }
    if overrides:
        result.update(overrides)
    return result


def observation(
    authorizer_id: int, *, overrides: dict[str, Any] | None = None
) -> PartyCurrentObservation:
    encoded = create_party_current_summary(
        summary_payload(authorizer_id, overrides=overrides),
        signer=party_signer(authorizer_id),
        key_id=f"test-only-party-key-{authorizer_id}",
    )
    return PartyCurrentObservation(
        authorizer_id=authorizer_id,
        endpoint=f"https://party-{authorizer_id}.invalid/",
        summary_bytes=encoded,
    )


def recovery_receipt() -> bytes:
    vector = build_vector()
    descriptor_bytes = vector["descriptor"]
    assert isinstance(descriptor_bytes, bytes)
    descriptor = json.loads(descriptor_bytes)
    payload = descriptor["payload"]
    return create_recovery_receipt(
        {
            "discovery_endpoint": DISCOVERY_ENDPOINT,
            "discovery_profile": BOOTSTRAP_PROFILE,
            "initial": {
                "backup_id": payload["backup_id"],
                "configuration_digest": payload["lifecycle"]["configuration_digest"],
                "descriptor_sha256": hashlib.sha256(descriptor_bytes).hexdigest(),
                "epoch": payload["epoch"],
            },
            "issued_at": 1_767_225_600,
            "issuer": ISSUER,
            "operator_key_id": KEY_ID,
            "recovery_handle": RECOVERY_HANDLE,
            "subject_id": SUBJECT_ID,
        },
        signer=signer(),
        key_id=KEY_ID,
    )


def authenticate(
    *,
    observations: list[PartyCurrentObservation] | None = None,
    trust_bytes: bytes | None = None,
    endpoint: str = DISCOVERY_ENDPOINT,
    recovery_handle: str = RECOVERY_HANDLE,
    subject_id: str = SUBJECT_ID,
    pointer_bytes: bytes | None = None,
    bundle_bytes: bytes | None = None,
    receipt_bytes: bytes | None = None,
    now: int = NOW,
):
    pointer, bundle, _descriptor = descriptor_parts()
    return authenticate_recovery_bootstrap(
        trust_configuration_bytes=trust_bytes or encode(trust_configuration()),
        discovery_endpoint=endpoint,
        recovery_handle=recovery_handle,
        expected_subject_id=subject_id,
        current_pointer_bytes=pointer_bytes or pointer,
        bundle_bytes=bundle_bytes or bundle,
        current_state_observations=observations
        if observations is not None
        else [observation(party_id) for party_id in range(1, 5)],
        now=now,
        receipt_bytes=receipt_bytes,
    )


class RecoveryBootstrapTests(unittest.TestCase):
    def test_schemas_freeze_bootstrap_receipt_and_summary_shapes(self) -> None:
        expected = {
            "bootstrap-trust-config-v1.schema.json": TRUST_CONFIGURATION_VERSION,
            "recovery-receipt-v1.schema.json": RECOVERY_RECEIPT_VERSION,
            "party-current-summary-v1.schema.json": PARTY_CURRENT_SUMMARY_VERSION,
        }
        for filename, identifier in expected.items():
            schema = json.loads(
                (ROOT / "docs/schemas" / filename).read_text(encoding="utf-8")
            )
            self.assertEqual(schema["$id"], identifier)
            self.assertFalse(schema["additionalProperties"])
        receipt_schema = json.loads(
            (ROOT / "docs/schemas/recovery-receipt-v1.schema.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            receipt_schema["properties"]["signature"]["properties"]["version"]["const"],
            "LOCUS-bootstrap-signature-v1",
        )
        summary_schema = json.loads(
            (ROOT / "docs/schemas/party-current-summary-v1.schema.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            summary_schema["properties"]["signature"]["properties"]["version"]["const"],
            PARTY_CURRENT_SIGNATURE_VERSION,
        )

    def test_clean_client_authenticates_complete_bootstrap_with_optional_receipt(
        self,
    ) -> None:
        without_receipt = authenticate()
        self.assertFalse(without_receipt.receipt_verified)
        self.assertEqual(without_receipt.matching_authorizers, (1, 2, 3, 4))
        self.assertEqual(without_receipt.dissenting_authorizers, ())
        snapshot = without_receipt.directory.resolve(RECOVERY_HANDLE, 1)
        self.assertEqual(snapshot.authorization_quorum, 4)
        self.assertEqual(snapshot.recovery_threshold.k, 2)
        self.assertEqual(len(snapshot.authorizers), 5)

        with_receipt = authenticate(receipt_bytes=recovery_receipt())
        self.assertTrue(with_receipt.receipt_verified)
        with self.assertRaises(RecoveryBootstrapError):
            with_receipt.directory.resolve("wrong-handle", 1)

    def test_trust_configuration_is_strict_and_updates_only_by_installed_chain(
        self,
    ) -> None:
        original_bytes = encode(trust_configuration())
        decoded = decode_trust_configuration(original_bytes)
        self.assertEqual(decoded["generation"], 1)

        invalid_values: list[bytes] = []
        unknown = trust_configuration()
        unknown["unknown"] = True
        invalid_values.append(encode(unknown))
        unordered = trust_configuration()
        unordered["parties"] = list(reversed(unordered["parties"]))
        invalid_values.append(encode(unordered))
        invalid_values.append(original_bytes + b" ")
        invalid_values.append(
            original_bytes.replace(b'"generation":1', b'"generation":1,"generation":1')
        )
        for value in invalid_values:
            with self.assertRaises(RecoveryDescriptorError):
                decode_trust_configuration(value)

        replacement = copy.deepcopy(trust_configuration())
        replacement["generation"] = 2
        replacement["previous_configuration_sha256"] = hashlib.sha256(
            original_bytes
        ).hexdigest()
        replacement["parties"][0]["endpoint"] = "https://rotated-party.invalid/"
        replacement_bytes = encode(replacement)
        self.assertEqual(
            validate_trust_configuration_update(
                original_bytes, replacement_bytes, now=NOW
            )["generation"],
            2,
        )
        replacement["previous_configuration_sha256"] = "00" * 32
        with self.assertRaises(RecoveryDescriptorError):
            validate_trust_configuration_update(
                original_bytes, encode(replacement), now=NOW
            )

    def test_descriptor_cannot_introduce_operator_or_party_trust(self) -> None:
        wrong_operator = copy.deepcopy(trust_configuration())
        wrong_operator["operator"]["public_key_hex"] = public_hex(party_signer(5))
        with self.assertRaises(RecoveryBootstrapError) as context:
            authenticate(trust_bytes=encode(wrong_operator))
        self.assertEqual(
            context.exception.code, BootstrapFailureCode.INVALID_CURRENT_POINTER
        )

        wrong_party = copy.deepcopy(trust_configuration())
        wrong_party["parties"][0]["endpoint"] = "https://other-party.invalid/"
        with self.assertRaises(RecoveryBootstrapError) as context:
            authenticate(trust_bytes=encode(wrong_party))
        self.assertEqual(
            context.exception.code, BootstrapFailureCode.UNTRUSTED_PARTY_DIRECTORY
        )

    def test_discovery_trust_expiry_and_identity_fail_closed(self) -> None:
        cases = (
            (
                {"endpoint": "https://attacker.invalid/"},
                BootstrapFailureCode.UNTRUSTED_DISCOVERY_ENDPOINT,
            ),
            (
                {"recovery_handle": "wrong-handle"},
                BootstrapFailureCode.RECOVERY_IDENTITY_MISMATCH,
            ),
            (
                {"subject_id": "99" * 32},
                BootstrapFailureCode.RECOVERY_IDENTITY_MISMATCH,
            ),
            ({"now": 1_900_000_000}, BootstrapFailureCode.TRUST_CONFIGURATION_EXPIRED),
        )
        for kwargs, expected_code in cases:
            with self.subTest(expected_code=expected_code.value):
                with self.assertRaises(RecoveryBootstrapError) as context:
                    authenticate(**kwargs)
                self.assertEqual(context.exception.code, expected_code)

    def test_receipt_signature_scope_and_initial_binding_fail_closed(self) -> None:
        good = recovery_receipt()
        parsed = json.loads(good)
        parsed["payload"]["recovery_handle"] = "wrong-handle"
        with self.assertRaises(RecoveryBootstrapError) as context:
            authenticate(receipt_bytes=encode(parsed))
        self.assertEqual(context.exception.code, BootstrapFailureCode.INVALID_RECEIPT)

        payload = json.loads(good)["payload"]
        payload["initial"]["configuration_digest"] = "00" * 32
        mismatched = create_recovery_receipt(payload, signer=signer(), key_id=KEY_ID)
        with self.assertRaises(RecoveryBootstrapError) as context:
            authenticate(receipt_bytes=mismatched)
        self.assertEqual(context.exception.code, BootstrapFailureCode.INVALID_RECEIPT)

        decoded = decode_recovery_receipt(
            good,
            issuer_public_key=signer().public_key(),
            expected_issuer=ISSUER,
            expected_key_id=KEY_ID,
        )
        self.assertEqual(decoded["payload"]["subject_id"], SUBJECT_ID)

    def test_current_state_quorum_distinguishes_unavailable_and_mismatch(self) -> None:
        result = authenticate(
            observations=[
                observation(1),
                observation(2),
                observation(3),
                observation(4),
                observation(5, overrides={"epoch": 2}),
            ]
        )
        self.assertEqual(result.matching_authorizers, (1, 2, 3, 4))
        self.assertEqual(result.dissenting_authorizers, (5,))

        with self.assertRaises(RecoveryBootstrapError) as unavailable:
            authenticate(observations=[observation(i) for i in range(1, 4)])
        self.assertEqual(
            unavailable.exception.code,
            BootstrapFailureCode.CURRENT_STATE_QUORUM_UNAVAILABLE,
        )

        with self.assertRaises(RecoveryBootstrapError) as mismatch:
            authenticate(
                observations=[
                    observation(1),
                    observation(2),
                    observation(3),
                    observation(4, overrides={"configuration_digest": "00" * 32}),
                ]
            )
        self.assertEqual(
            mismatch.exception.code, BootstrapFailureCode.CLOUD_PARTY_STATE_MISMATCH
        )

    def test_party_summary_authentication_endpoint_freshness_and_duplicates(
        self,
    ) -> None:
        valid = observation(1)
        decoded = decode_party_current_summary(
            valid.summary_bytes,
            party_public_key=party_signer(1).public_key(),
            expected_key_id="test-only-party-key-1",
        )
        self.assertEqual(decoded["payload"]["authorizer_id"], 1)

        invalid_observation_sets = (
            [
                PartyCurrentObservation(
                    authorizer_id=1,
                    endpoint="https://attacker.invalid/",
                    summary_bytes=valid.summary_bytes,
                )
            ],
            [valid, valid],
            [observation(1, overrides={"expires_at": NOW})],
        )
        for observations in invalid_observation_sets:
            with self.assertRaises(RecoveryBootstrapError):
                authenticate(observations=observations)

        tampered = json.loads(valid.summary_bytes)
        tampered["payload"]["epoch"] = 2
        with self.assertRaises(RecoveryBootstrapError) as context:
            authenticate(
                observations=[
                    PartyCurrentObservation(
                        authorizer_id=1,
                        endpoint=valid.endpoint,
                        summary_bytes=encode(tampered),
                    )
                ]
            )
        self.assertEqual(
            context.exception.code, BootstrapFailureCode.INVALID_PARTY_SUMMARY
        )

    def test_pointer_and_bundle_substitution_fail_before_current_state(self) -> None:
        pointer, bundle, _descriptor = descriptor_parts()
        with self.assertRaises(RecoveryBootstrapError) as pointer_error:
            authenticate(pointer_bytes=pointer[:-1] + b"x")
        self.assertEqual(
            pointer_error.exception.code, BootstrapFailureCode.INVALID_CURRENT_POINTER
        )
        with self.assertRaises(RecoveryBootstrapError) as bundle_error:
            authenticate(bundle_bytes=bundle[:-1] + b"x")
        self.assertEqual(
            bundle_error.exception.code, BootstrapFailureCode.INVALID_RECOVERY_BUNDLE
        )

    def test_canonical_bootstrap_vector_is_stable_and_contains_no_private_key(
        self,
    ) -> None:
        trust_bytes = encode(trust_configuration())
        receipt_bytes = recovery_receipt()
        summaries = [observation(i).summary_bytes for i in range(1, 6)]
        lines = {
            "bootstrap_profile": BOOTSTRAP_PROFILE,
            "trust_configuration_sha256": hashlib.sha256(trust_bytes).hexdigest(),
            "trust_configuration_length": str(len(trust_bytes)),
            "recovery_receipt_sha256": hashlib.sha256(receipt_bytes).hexdigest(),
            "recovery_receipt_length": str(len(receipt_bytes)),
            **{
                f"party_{index}_summary_sha256": hashlib.sha256(summary).hexdigest()
                for index, summary in enumerate(summaries, start=1)
            },
        }
        expected = dict(
            line.split("=", 1)
            for line in VECTOR_PATH.read_text(encoding="utf-8").splitlines()
            if line and not line.startswith("#")
        )
        self.assertEqual(lines, expected)
        vector_text = VECTOR_PATH.read_text(encoding="utf-8").lower()
        self.assertNotIn("private", vector_text)
        self.assertNotIn("seed", vector_text)

    def test_bootstrap_public_state_has_no_cue_or_recovery_secret(self) -> None:
        result = authenticate(receipt_bytes=recovery_receipt())
        visible = encode(
            {
                "descriptor": result.bundle.descriptor,
                "pointer": result.current_pointer,
                "trust": trust_configuration(),
                "receipt": json.loads(recovery_receipt()),
                "summaries": [
                    json.loads(observation(i).summary_bytes) for i in range(1, 6)
                ],
            }
        ).lower()
        for forbidden in (
            b'"raw_cue"',
            b'"z_m"',
            b'"p_m"',
            b'"s_r"',
            b'"k_wrap"',
            b'"private_key"',
            b'"password_verifier"',
            b'"party_secret_state"',
        ):
            self.assertNotIn(forbidden, visible)
        self.assertIn(b'"configuration_digest"', visible)


if __name__ == "__main__":
    unittest.main()
