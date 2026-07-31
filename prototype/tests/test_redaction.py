from __future__ import annotations

import unittest

from locus.redaction import (
    OutputSafetyError,
    exposed_categories,
    validate_public_output,
)


class OutputSafetyTests(unittest.TestCase):
    def test_accepts_metrics_and_privacy_safe_status(self) -> None:
        validate_public_output(
            {
                "configuration": {"cue_count": 3, "threshold": 2},
                "latency_ms": 12.5,
                "selected": [1, 3],
                "status": "ok",
            }
        )

    def test_rejects_every_prohibited_secret_category(self) -> None:
        fields = (
            "raw_cues",
            "cue_id",
            "tpass_password",
            "tpass_share",
            "tpass_state",
            "wrapping_key",
            "private_key",
            "recovered_secret",
            "party_randomness",
        )
        for field in fields:
            with self.subTest(field=field):
                with self.assertRaises(OutputSafetyError):
                    validate_public_output({"nested": [{field: "test-only-secret"}]})

    def test_scanner_reports_categories_without_echoing_values(self) -> None:
        cue_value = "fixture.person@example.org"
        output = (
            '{"wrapping_key":"not-safe"}\n'
            f"resolver returned {cue_value}\n"
            "-----BEGIN PRIVATE KEY-----\n"
        )
        exposed = exposed_categories(output, {"raw-cue": cue_value})
        self.assertEqual(
            exposed,
            ["field:wrapping_key", "private-key-block", "raw-cue"],
        )
        self.assertNotIn(cue_value, repr(exposed))


if __name__ == "__main__":
    unittest.main()
