from __future__ import annotations

import json
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MATRIX_PATH = ROOT / "docs" / "security-matrix-v2.json"
SCHEMA_PATH = ROOT / "docs" / "schemas" / "security-matrix-v2.schema.json"

V1_ARTIFACT = "LOCUS-security-matrix-v1"
V1_SHA256 = "bdeb5cb1e0992c08e44e6bf4a47b6071952ad56474124613aaae81664f18cf89"
V1_CLAIM_IDS = [f"C{number:02d}" for number in range(1, 27)]
V1_PHASES = {
    "bootstrap",
    "enrollment",
    "party-replacement",
    "persistent-state-disposal",
    "recovery",
    "successor-publication",
}
V1_VIEWS = {
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
MANAGED_PHASES = {
    "client-lifecycle",
    "credential-reset",
    "package-export",
    "package-import",
    "system-control",
}
MANAGED_VIEWS = {
    "container-controller",
    "credential-state",
    "docker-engine-metadata",
    "managed-client-active-browser",
    "managed-client-after-destruction",
    "managed-client-after-process-reset",
    "manager-ui-api",
    "recovery-package",
}
CONTRACT_FIELDS = {
    "contract_id",
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
TEXT_FIELDS = CONTRACT_FIELDS - {"contract_id", "phases", "views"}


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AssertionError(f"{path} is not a JSON object")
    return value


class SecurityMatrixV2Tests(unittest.TestCase):
    def test_candidate_and_schema_have_exact_strict_shape(self) -> None:
        matrix = load_json(MATRIX_PATH)
        schema = load_json(SCHEMA_PATH)
        self.assertEqual(
            set(matrix),
            {"artifact", "predecessor", "phases", "views", "managed_contracts"},
        )
        self.assertEqual(matrix["artifact"], "LOCUS-security-matrix-v2")
        self.assertEqual(schema["properties"]["artifact"]["const"], matrix["artifact"])
        self.assertFalse(schema["additionalProperties"])
        predecessor_schema = schema["properties"]["predecessor"]
        self.assertFalse(predecessor_schema["additionalProperties"])
        self.assertEqual(
            set(predecessor_schema["required"]),
            {"artifact", "sha256", "preserved_claim_ids"},
        )
        contract_schema = schema["properties"]["managed_contracts"]["items"]
        self.assertFalse(contract_schema["additionalProperties"])
        self.assertEqual(set(contract_schema["required"]), CONTRACT_FIELDS)

    def test_candidate_pins_v1_and_preserves_c01_through_c26(self) -> None:
        matrix = load_json(MATRIX_PATH)
        predecessor = matrix["predecessor"]
        self.assertEqual(predecessor["artifact"], V1_ARTIFACT)
        self.assertEqual(predecessor["sha256"], V1_SHA256)
        self.assertEqual(predecessor["preserved_claim_ids"], V1_CLAIM_IDS)
        self.assertEqual(matrix["phases"], sorted(matrix["phases"]))
        self.assertEqual(matrix["views"], sorted(matrix["views"]))
        self.assertTrue(V1_PHASES.issubset(matrix["phases"]))
        self.assertTrue(V1_VIEWS.issubset(matrix["views"]))
        self.assertTrue(MANAGED_PHASES.issubset(matrix["phases"]))
        self.assertTrue(MANAGED_VIEWS.issubset(matrix["views"]))

    def test_managed_contracts_are_complete_and_bounded(self) -> None:
        matrix = load_json(MATRIX_PATH)
        contracts = matrix["managed_contracts"]
        self.assertEqual(
            [contract["contract_id"] for contract in contracts],
            ["M01", "M02", "M03", "M04", "M05"],
        )
        covered_phases: set[str] = set()
        covered_views: set[str] = set()
        for contract in contracts:
            self.assertEqual(set(contract), CONTRACT_FIELDS)
            self.assertEqual(len(contract["phases"]), len(set(contract["phases"])))
            self.assertEqual(len(contract["views"]), len(set(contract["views"])))
            self.assertTrue(set(contract["phases"]).issubset(matrix["phases"]))
            self.assertTrue(set(contract["views"]).issubset(matrix["views"]))
            covered_phases.update(contract["phases"])
            covered_views.update(contract["views"])
            for field in TEXT_FIELDS:
                self.assertIsInstance(contract[field], str)
                self.assertTrue(contract[field].strip())
        self.assertTrue(MANAGED_PHASES.issubset(covered_phases))
        self.assertTrue(MANAGED_VIEWS.issubset(covered_views))

    def test_required_managed_boundaries_are_explicit(self) -> None:
        contracts = {
            contract["contract_id"]: " ".join(str(value) for value in contract.values())
            for contract in load_json(MATRIX_PATH)["managed_contracts"]
        }
        for marker in (
            "manager-edge",
            "browser-edge",
            "management",
            "client-lifecycle",
            "Docker socket",
            "cross-project",
            "CSRF",
            "proof-bound",
            "arbitrary-image",
        ):
            self.assertIn(marker, contracts["M01"])
        for marker in (
            "untrusted",
            "canonical",
            "oversized",
            "duplicate",
            "unknown",
            "signature-invalid",
            "current-pointer",
            "private-key",
            "cannot override",
            "export scan",
        ):
            self.assertIn(marker, contracts["M02"])
        for marker in (
            "stop",
            "start",
            "restart",
            "kill",
            "server-side key slot",
            "public client ID",
        ):
            self.assertIn(marker, contracts["M03"])
        for marker in (
            "Synthetic plaintext private key",
            "Manager/controller",
            "browser storage",
            "already loaded",
        ):
            self.assertIn(marker, contracts["M04"])
        for marker in (
            "366-day",
            "365-day",
            "--reset-state",
            "No in-place renewal",
        ):
            self.assertIn(marker, contracts["M05"])


if __name__ == "__main__":
    unittest.main()
