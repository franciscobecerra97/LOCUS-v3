from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from locus.performance_methodology import (
    METHODOLOGY_ID,
    PerformanceMethodologyError,
    canonical_json,
    methodology_contract,
    validate_methodology,
    validate_methodology_file,
)

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "docs" / "managed-performance-methodology-v1.json"
SCHEMA = ROOT / "docs" / "schemas" / "managed-performance-methodology-v1.schema.json"


class PerformanceMethodologyTests(unittest.TestCase):
    def test_checked_contract_is_canonical_and_exact(self) -> None:
        value = validate_methodology_file(CONTRACT)
        self.assertEqual(CONTRACT.read_bytes(), canonical_json(methodology_contract()))
        self.assertEqual(value["format_id"], METHODOLOGY_ID)
        self.assertFalse(value["retention_gate"]["p9_1_collection_authorized"])
        self.assertEqual(value["retention_gate"]["result_identifiers"], [])
        self.assertEqual(value["retention_gate"]["retained_paths"], [])

    def test_exact_arms_blocks_samples_and_failures_are_frozen(self) -> None:
        value = methodology_contract()
        self.assertEqual(
            [arm["arm_id"] for arm in value["arms"]],
            ["yi-2of3", "appss-2of3", "yi-3of5", "appss-3of5"],
        )
        blocking = value["blocking_and_randomization"]
        self.assertEqual(blocking["seeds"], list(range(2026081701, 2026081711)))
        self.assertEqual(blocking["warmup"]["count_per_arm_block"], 1)
        self.assertFalse(blocking["warmup"]["measured"])
        self.assertEqual(value["sample_plan"]["central"]["samples_per_arm"], 30)
        self.assertEqual(value["sample_plan"]["structural"]["samples_per_arm"], 10)
        self.assertEqual(value["sample_plan"]["concurrency"]["levels"], [1, 2, 4])
        self.assertEqual(
            value["failure_schedules"]["below_threshold"]["holder_count"], "k-minus-1"
        )
        self.assertEqual(value["statistics"]["outlier_removal"], "none")

    def test_any_semantic_mutation_fails_closed(self) -> None:
        mutations = []
        for mutate in (
            lambda v: v["arms"][0].__setitem__("policy_id", "wrong"),
            lambda v: v["blocking_and_randomization"]["seeds"].__setitem__(0, 1),
            lambda v: v["sample_plan"]["central"].__setitem__("samples_per_arm", 29),
            lambda v: v["statistics"].__setitem__("outlier_removal", "iqr"),
            lambda v: v["failure_schedules"]["2of3_one_party_unavailable"].__setitem__(
                "stop_party", 2
            ),
            lambda v: v["deployment"].__setitem__("host_tier", "multi-host"),
            lambda v: v["retention_gate"]["result_identifiers"].append(
                "LOCUS-result-v1"
            ),
        ):
            changed = copy.deepcopy(methodology_contract())
            mutate(changed)
            mutations.append(changed)
        for changed in mutations:
            with self.subTest(changed=changed):
                with self.assertRaises(PerformanceMethodologyError):
                    validate_methodology(changed)

    def test_schema_is_strict_and_registry_contains_d028_and_d029_ids(self) -> None:
        schema = json.loads(SCHEMA.read_bytes())
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(schema["properties"]["format_id"]["const"], METHODOLOGY_ID)
        registry = json.loads((ROOT / "docs" / "version-registry-v1.json").read_bytes())
        protected = registry["protected_identifiers"]
        self.assertIn(METHODOLOGY_ID, protected)
        self.assertEqual(
            {
                item
                for item in protected
                if item.startswith("LOCUS-managed-performance-")
            },
            {
                METHODOLOGY_ID,
                "LOCUS-managed-performance-evidence-profile-v1",
                "LOCUS-managed-performance-instrumentation-v1",
                "LOCUS-managed-performance-scenario-manifest-v1",
                "LOCUS-managed-performance-result-common-v1",
                "LOCUS-managed-performance-result-yi-v1",
                "LOCUS-managed-performance-result-appss-v1",
                "LOCUS-managed-performance-processor-v1",
                "LOCUS-managed-performance-summary-v1",
                "LOCUS-managed-performance-comparison-v1",
                "LOCUS-managed-performance-corpus-manifest-v1",
                "LOCUS-managed-performance-methodology-v2",
                "LOCUS-managed-performance-evidence-profile-v2",
                "LOCUS-managed-performance-instrumentation-v2",
                "LOCUS-managed-performance-scenario-manifest-v2",
                "LOCUS-managed-performance-result-yi-v2",
                "LOCUS-managed-performance-result-appss-v2",
                "LOCUS-managed-performance-processor-v2",
                "LOCUS-managed-performance-summary-v2",
                "LOCUS-managed-performance-comparison-v2",
                "LOCUS-managed-performance-corpus-manifest-v2",
                "LOCUS-managed-performance-checkpoint-v1",
            },
        )


if __name__ == "__main__":
    unittest.main()
