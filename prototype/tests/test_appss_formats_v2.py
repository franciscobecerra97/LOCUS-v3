from __future__ import annotations

import json
import unittest
from pathlib import Path

from locus.appss_formats import (
    APPSS_FORMAT_VECTORS_V2,
    APPSS_PROFILE_3_OF_5,
    MAX_PUBLIC_STATE_BYTES,
    MAX_SELECTOR_BYTES,
    canonical_decode,
    encode_checked,
    validate_public_state,
    validate_selector,
)

ROOT = Path(__file__).resolve().parents[2]
VECTOR = ROOT / "prototype/test-vectors/appss-format-v2.json"


class AppssFormatV2VectorTests(unittest.TestCase):
    def test_public_vector_and_both_selectors_are_canonical_and_strict(self) -> None:
        vector = json.loads(VECTOR.read_text(encoding="utf-8"))
        self.assertEqual(vector["artifact"], APPSS_FORMAT_VECTORS_V2)
        public_bytes = encode_checked(
            vector["public_state"],
            maximum=MAX_PUBLIC_STATE_BYTES,
            validator=validate_public_state,
            label="aPPSS public state",
        )
        decoded_public = canonical_decode(
            public_bytes,
            maximum=MAX_PUBLIC_STATE_BYTES,
            validator=validate_public_state,
            label="aPPSS public state",
        )
        self.assertEqual(decoded_public["profile_id"], APPSS_PROFILE_3_OF_5)
        self.assertEqual(
            [share["index"] for share in decoded_public["masked_shares"]],
            [1, 2, 3, 4, 5],
        )
        for name in ("selector_yi", "selector_appss"):
            encoded = encode_checked(
                vector[name],
                maximum=MAX_SELECTOR_BYTES,
                validator=validate_selector,
                label="recovery-suite selector",
            )
            self.assertEqual(
                json.loads(encoded),
                vector[name],
            )

    def test_independent_shape_checks_reject_topology_reinterpretation(self) -> None:
        vector = json.loads(VECTOR.read_text(encoding="utf-8"))
        public = vector["public_state"]
        self.assertEqual(
            set(public),
            {
                "commitment",
                "context_digest",
                "k",
                "masked_shares",
                "n",
                "omega_digest",
                "oprf_profile",
                "profile_id",
                "suite_id",
                "version",
            },
        )
        self.assertEqual((public["k"], public["n"]), (3, 5))
        changed = dict(public)
        changed["version"] = "LOCUS-APPSS-public-state-v1"
        with self.assertRaises(ValueError):
            validate_public_state(changed)


if __name__ == "__main__":
    unittest.main()
