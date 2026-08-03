from __future__ import annotations

import copy
import hashlib
import json
import unittest
from pathlib import Path

from locus.appss_formats import (
    APPSS_PUBLIC_STATE_FORMAT,
    APPSS_SUITE_ID,
    APPSS_WIRE_FORMAT,
    MAX_PUBLIC_STATE_BYTES,
    MAX_SELECTOR_BYTES,
    AppssFormatError,
    AppssHolderBinding,
    canonical_decode,
    context_digest,
    encode_checked,
    omega_digest,
    validate_public_state,
    validate_selector,
)

ROOT = Path(__file__).resolve().parents[2]
VECTOR = ROOT / "prototype/test-vectors/appss-format-v1.json"


class AppssFormatTests(unittest.TestCase):
    def setUp(self) -> None:
        self.vector = json.loads(VECTOR.read_text(encoding="utf-8"))

    def test_public_structural_vector_regenerates(self) -> None:
        holders = tuple(AppssHolderBinding(**item) for item in self.vector["holders"])
        context = context_digest(
            backup_id=bytes.fromhex(self.vector["backup_id"]),
            epoch=self.vector["epoch"],
            policy_id=self.vector["policy_id"],
            holders=holders,
            k=2,
            n=3,
            configuration_digest=bytes.fromhex(self.vector["configuration_digest"]),
        )
        self.assertEqual(context.hex(), self.vector["context_digest"])
        shares = tuple(
            (item["index"], bytes.fromhex(item["value"]))
            for item in self.vector["masked_shares"]
        )
        self.assertEqual(
            omega_digest(
                context,
                shares,
                bytes.fromhex(self.vector["commitment"]),
            ).hex(),
            self.vector["omega_digest"],
        )
        public_bytes = encode_checked(
            self.vector["public_state"],
            maximum=MAX_PUBLIC_STATE_BYTES,
            validator=validate_public_state,
            label="aPPSS public state",
        )
        self.assertEqual(public_bytes.hex(), self.vector["public_state_canonical_hex"])
        self.assertEqual(
            canonical_decode(
                public_bytes,
                maximum=MAX_PUBLIC_STATE_BYTES,
                validator=validate_public_state,
                label="aPPSS public state",
            ),
            self.vector["public_state"],
        )
        selector_bytes = encode_checked(
            self.vector["selector"],
            maximum=MAX_SELECTOR_BYTES,
            validator=validate_selector,
            label="suite selector",
        )
        self.assertEqual(selector_bytes.hex(), self.vector["selector_canonical_hex"])

    def test_profile_identifiers_are_distinct(self) -> None:
        self.assertNotEqual(APPSS_SUITE_ID, APPSS_WIRE_FORMAT)
        self.assertNotEqual(APPSS_SUITE_ID, APPSS_PUBLIC_STATE_FORMAT)

    def test_public_state_rejects_cross_suite_and_mixed_omega(self) -> None:
        wrong_suite = copy.deepcopy(self.vector["public_state"])
        wrong_suite["suite_id"] = "LOCUS-TPASS-YI-ZK-RISTRETTO255-v1"
        with self.assertRaises(AppssFormatError):
            validate_public_state(wrong_suite)

        mixed_omega = copy.deepcopy(self.vector["public_state"])
        mixed_omega["masked_shares"][0]["value"] = "00" * 16
        with self.assertRaisesRegex(AppssFormatError, "omega digest mismatch"):
            validate_public_state(mixed_omega)

    def test_canonical_decoder_rejects_trailing_and_noncanonical_bytes(self) -> None:
        canonical = bytes.fromhex(self.vector["public_state_canonical_hex"])
        for malformed in (canonical + b"\n", canonical + b"{}"):
            with self.assertRaises(AppssFormatError):
                canonical_decode(
                    malformed,
                    maximum=MAX_PUBLIC_STATE_BYTES,
                    validator=validate_public_state,
                    label="aPPSS public state",
                )
        reordered = json.dumps(
            self.vector["public_state"], separators=(",", ":")
        ).encode("ascii")
        if reordered != canonical:
            with self.assertRaisesRegex(AppssFormatError, "noncanonical"):
                canonical_decode(
                    reordered,
                    maximum=MAX_PUBLIC_STATE_BYTES,
                    validator=validate_public_state,
                    label="aPPSS public state",
                )

    def test_selector_rejects_suite_profile_mismatch_and_fallback_shape(self) -> None:
        mismatch = copy.deepcopy(self.vector["selector"])
        mismatch["suite_id"] = "LOCUS-TPASS-YI-ZK-RISTRETTO255-v1"
        with self.assertRaises(AppssFormatError):
            validate_selector(mismatch)

        fallback = copy.deepcopy(self.vector["selector"])
        fallback["fallback_suite_id"] = "LOCUS-TPASS-YI-ZK-RISTRETTO255-v1"
        with self.assertRaises(AppssFormatError):
            validate_selector(fallback)

    def test_public_vector_contains_no_secret_path_fields(self) -> None:
        forbidden = {
            "cue_policy_output",
            "password_input",
            "oprf_key",
            "blind",
            "unmasked_share",
            "recovery_secret",
            "private_key",
        }
        observed: set[str] = set()

        def visit(value: object) -> None:
            if isinstance(value, dict):
                observed.update(value)
                for nested in value.values():
                    visit(nested)
            elif isinstance(value, list):
                for nested in value:
                    visit(nested)

        visit(self.vector)
        self.assertFalse(forbidden & observed)
        self.assertEqual(
            hashlib.sha256(VECTOR.read_bytes()).hexdigest(),
            "6004b0d04ea5fcda9515a175dca6ddf961e068d096dde7eb73bf27228570da26",
        )


if __name__ == "__main__":
    unittest.main()
