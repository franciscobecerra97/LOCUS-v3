from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path
from typing import cast

from locus.attempt_boundary import (
    CERTIFICATE_SOURCE_SHA256,
    MODEL_SCHEMA_SHA256,
    MODEL_SOURCE_SHA256,
    AttemptBoundaryError,
    build_integrated_attempt_boundary_report,
    validate_managed_attempt_boundary,
)

ROOT = Path(__file__).resolve().parents[1]


class AttemptBoundaryTests(unittest.TestCase):
    def test_frozen_model_is_bound_to_exact_managed_profile(self) -> None:
        report = build_integrated_attempt_boundary_report(ROOT)
        self.assertEqual(report["version"], "LOCUS-attempt-model-report-v1")
        self.assertEqual(report["status"], "passed")
        self.assertEqual(len(cast(list[object], report["scenarios"])), 7)
        self.assertEqual(len(MODEL_SOURCE_SHA256), 64)
        self.assertEqual(len(MODEL_SCHEMA_SHA256), 64)
        self.assertEqual(len(CERTIFICATE_SOURCE_SHA256), 64)

    def test_changed_quorum_or_witness_role_fails_closed(self) -> None:
        manifest = json.loads(
            (ROOT / "deploy" / "managed-manifest.json").read_text(encoding="utf-8")
        )
        changed_quorum = copy.deepcopy(manifest)
        changed_quorum["authorization"]["quorum"] = 3
        with self.assertRaises(AttemptBoundaryError):
            validate_managed_attempt_boundary(changed_quorum)

        added_witness = copy.deepcopy(manifest)
        added_witness["services"].append({"name": "monotonic-witness"})
        with self.assertRaises(AttemptBoundaryError):
            validate_managed_attempt_boundary(added_witness)

    def test_client_ui_states_the_non_claim(self) -> None:
        html = (ROOT / "locus" / "client_assets" / "index.html").read_text(
            encoding="utf-8"
        )
        self.assertIn("Local attempt records are diagnostic only", html)
        self.assertIn("no global or rollback-resistant attempt limit", html)


if __name__ == "__main__":
    unittest.main()
