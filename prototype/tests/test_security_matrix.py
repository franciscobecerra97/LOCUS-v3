from __future__ import annotations

import json
import re
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
MATRIX_PATH = ROOT / "docs/security-matrix-v1.json"
SCHEMA_PATH = ROOT / "docs/schemas/security-matrix-v1.schema.json"
CLAIMS_PATH = ROOT / "CLAIM-EVIDENCE-MATRIX.md"
FLOW_PATH = ROOT / "docs/INFORMATION-FLOW.md"

REQUIRED_PHASES = {
    "bootstrap",
    "enrollment",
    "party-replacement",
    "persistent-state-disposal",
    "recovery",
    "successor-publication",
}
REQUIRED_VIEWS = {
    "application-storage-gateway",
    "below-threshold-party-coalition",
    "clean-client-after-cue-entry",
    "clean-client-before-cue-entry",
    "cloud",
    "descriptor-store",
    "enrollment-client-after-disposal",
    "exact-threshold-appss-coalition",
    "identity-admission-provider",
    "matching-combined-state",
    "network-role-metadata",
    "resolver",
}
CLAIM_FIELDS = {
    "claim_id",
    "phases",
    "views",
    "asset",
    "adversary",
    "assumptions",
    "boundary",
    "positive_control",
    "expected_observation",
    "interpretation_limit",
}
TEXT_FIELDS = CLAIM_FIELDS - {"claim_id", "phases", "views"}


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AssertionError(f"{path} is not a JSON object")
    return value


class SecurityMatrixTests(unittest.TestCase):
    def test_matrix_and_schema_have_exact_public_shape(self) -> None:
        matrix = load_json(MATRIX_PATH)
        schema = load_json(SCHEMA_PATH)
        self.assertEqual(set(matrix), {"artifact", "phases", "views", "claims"})
        self.assertEqual(matrix["artifact"], "LOCUS-security-matrix-v1")
        self.assertEqual(schema["properties"]["artifact"]["const"], matrix["artifact"])
        self.assertFalse(schema["additionalProperties"])
        claim_schema = schema["properties"]["claims"]["items"]
        self.assertFalse(claim_schema["additionalProperties"])
        self.assertEqual(set(claim_schema["required"]), CLAIM_FIELDS)

    def test_required_phases_views_and_cross_document_claims_are_complete(self) -> None:
        matrix = load_json(MATRIX_PATH)
        self.assertEqual(matrix["phases"], sorted(REQUIRED_PHASES))
        self.assertEqual(matrix["views"], sorted(REQUIRED_VIEWS))

        markdown_claims = re.findall(
            r"^\| (C[0-9]{2}) \|", CLAIMS_PATH.read_text(encoding="utf-8"), re.M
        )
        matrix_claims = [claim["claim_id"] for claim in matrix["claims"]]
        self.assertEqual(markdown_claims, [f"C{number:02d}" for number in range(1, 27)])
        self.assertEqual(matrix_claims, markdown_claims)
        self.assertEqual(len(matrix_claims), len(set(matrix_claims)))

    def test_every_claim_has_a_complete_bounded_security_contract(self) -> None:
        matrix = load_json(MATRIX_PATH)
        covered_phases: set[str] = set()
        covered_views: set[str] = set()
        for claim in matrix["claims"]:
            self.assertEqual(set(claim), CLAIM_FIELDS)
            self.assertTrue(claim["phases"])
            self.assertTrue(claim["views"])
            self.assertEqual(len(claim["phases"]), len(set(claim["phases"])))
            self.assertEqual(len(claim["views"]), len(set(claim["views"])))
            self.assertTrue(set(claim["phases"]).issubset(REQUIRED_PHASES))
            self.assertTrue(set(claim["views"]).issubset(REQUIRED_VIEWS))
            covered_phases.update(claim["phases"])
            covered_views.update(claim["views"])
            for field in TEXT_FIELDS:
                self.assertIsInstance(claim[field], str)
                self.assertTrue(claim[field].strip())
        self.assertEqual(covered_phases, REQUIRED_PHASES)
        self.assertEqual(covered_views, REQUIRED_VIEWS)

    def test_threshold_and_nonclaim_boundaries_are_explicit(self) -> None:
        claims = {
            claim["claim_id"]: claim for claim in load_json(MATRIX_PATH)["claims"]
        }
        self.assertIn("below-threshold-party-coalition", claims["C24"]["views"])
        self.assertNotIn("exact-threshold-appss-coalition", claims["C24"]["views"])
        self.assertIn("exact-threshold-appss-coalition", claims["C25"]["views"])
        self.assertIn("offline guessing", claims["C25"]["interpretation_limit"])
        for claim_id in ("C15", "C17", "C18", "C19", "C20"):
            combined = " ".join(str(value) for value in claims[claim_id].values())
            self.assertIn("non-claim", combined)

    def test_information_flow_document_covers_every_phase_and_view(self) -> None:
        document = FLOW_PATH.read_text(encoding="utf-8")
        for phase in (
            "Enrollment",
            "Persistent-state disposal",
            "Bootstrap",
            "Recovery",
            "Successor publication",
            "Party replacement",
        ):
            self.assertIn(f"### {phase} phase contract", document)
        for abbreviation in (
            "CLD",
            "DS",
            "GW",
            "RES",
            "B<k",
            "A=k",
            "COM",
            "A0",
            "B0",
            "B1",
            "IDP",
            "NET",
        ):
            self.assertIn(f"`{abbreviation}`", document)
        self.assertIn("{P1,P2}", document)
        self.assertIn("{P1,P3}", document)
        self.assertIn("{P2,P3}", document)


if __name__ == "__main__":
    unittest.main()
