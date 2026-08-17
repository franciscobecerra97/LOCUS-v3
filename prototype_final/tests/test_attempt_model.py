from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path
from typing import Any, ClassVar, cast

from locus.attempt_model import (
    MODEL_REPORT_VERSION,
    SCENARIO_REGISTRY,
    AttemptModelError,
    build_model_report,
    validate_model_report,
)


class AttemptModelTests(unittest.TestCase):
    report: ClassVar[dict[str, object]]

    @classmethod
    def setUpClass(cls) -> None:
        cls.report = build_model_report()

    def scenarios(self) -> dict[str, dict[str, Any]]:
        scenarios = cast(list[dict[str, Any]], self.report["scenarios"])
        return {scenario["scenario_id"]: scenario for scenario in scenarios}

    def test_frozen_report_passes_and_matches_schema_registry(self) -> None:
        self.assertEqual(self.report["version"], MODEL_REPORT_VERSION)
        self.assertEqual(self.report["status"], "passed")
        self.assertEqual(validate_model_report(self.report), self.report)

        root = Path(__file__).resolve().parents[2]
        schema = json.loads(
            (
                root / "docs" / "schemas" / "attempt-model-report-v1.schema.json"
            ).read_text(encoding="utf-8")
        )
        scenario_enum = schema["$defs"]["scenario"]["properties"]["scenario_id"]["enum"]
        self.assertEqual(set(scenario_enum), set(SCENARIO_REGISTRY))

    def test_quorum_only_reconciliation_has_shortest_rollback_forks(self) -> None:
        scenarios = self.scenarios()
        single = scenarios["single-honest-rollback-quorum-v1"]["observed"]
        self.assertEqual(single["outcome"], "counterexample")
        self.assertEqual(single["violation"], "conflicting-authorization-certificates")
        trace = single["trace"]
        self.assertTrue(any(step.startswith("rollback:") for step in trace))
        self.assertTrue(any(step.startswith("reconcile-quorum:") for step in trace))
        self.assertEqual(
            sum(step.startswith("certify:") for step in trace),
            2,
        )

        retired = scenarios["retired-epoch-double-rollback-quorum-v1"]["observed"]
        self.assertEqual(retired["violation"], "authorization-after-final-retirement")

    def test_ideal_monotonic_anchor_removes_bounded_counterexamples(self) -> None:
        scenarios = self.scenarios()
        for scenario_id in (
            "single-honest-rollback-anchor-v1",
            "double-honest-rollback-anchor-v1",
            "retired-epoch-double-rollback-anchor-v1",
        ):
            with self.subTest(scenario_id=scenario_id):
                observed = scenarios[scenario_id]["observed"]
                self.assertEqual(observed["outcome"], "no-counterexample-within-bound")
                self.assertFalse(observed["truncated"])
                self.assertIsNone(observed["violation"])

    def test_report_validator_rejects_changed_result_or_unknown_field(self) -> None:
        changed_status = copy.deepcopy(self.report)
        first = cast(list[dict[str, Any]], changed_status["scenarios"])[0]
        first["status"] = "failed"
        changed_status["status"] = "failed"
        with self.assertRaises(AttemptModelError):
            validate_model_report(changed_status)

        changed_shape = copy.deepcopy(self.report)
        changed_shape["raw_cues"] = "forbidden"
        with self.assertRaises(AttemptModelError):
            validate_model_report(changed_shape)


if __name__ == "__main__":
    unittest.main()
