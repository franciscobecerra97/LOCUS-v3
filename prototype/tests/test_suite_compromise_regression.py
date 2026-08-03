from __future__ import annotations

import copy
import json
import socket
import unittest
from pathlib import Path
from typing import Any, ClassVar
from unittest.mock import patch

from locus.appss_formats import APPSS_SUITE_ID, YI_SUITE_ID
from locus.suite_compromise_regression import (
    REPORT_VERSION,
    SuiteCompromiseRegressionError,
    run_fixed_suite_compromise_regression,
    validate_suite_compromise_report,
)


class SuiteCompromiseRegressionTests(unittest.TestCase):
    report: ClassVar[dict[str, Any]]

    @classmethod
    def setUpClass(cls) -> None:
        with patch.object(
            socket,
            "socket",
            side_effect=AssertionError("network access is forbidden"),
        ):
            cls.report = run_fixed_suite_compromise_regression()

    def test_every_below_threshold_view_is_aggregate_and_networkless(self) -> None:
        report = self.report
        self.assertEqual(
            [item["coalitions_evaluated"] for item in report["scenarios"]],
            [1, 4, 4, 1, 4, 4],
        )
        self.assertEqual(
            {item["suite"] for item in report["scenarios"]},
            {YI_SUITE_ID, APPSS_SUITE_ID},
        )
        for item in report["scenarios"]:
            self.assertFalse(item["local_tested_predicate_found"])
            self.assertFalse(item["network_access"])
            self.assertTrue(item["positive_control_detected"])

    def test_threshold_compromise_behaviors_remain_distinct(self) -> None:
        observations = self.report["compromise_boundary"]
        yi = observations["yi"]
        self.assertTrue(yi["low_entropy_input_scalar_reconstructed"])
        self.assertTrue(yi["protected_exponent_reconstructed"])
        self.assertTrue(yi["recovery_output_directly_derivable"])
        self.assertEqual(yi["fixed_inputs_tested"], 0)

        appss = observations["appss"]
        self.assertTrue(appss["offline_dictionary_test_capability"])
        self.assertFalse(appss["output_without_correct_input"])
        self.assertTrue(appss["output_after_correct_input"])
        self.assertEqual(appss["fixed_inputs_tested"], 2)
        self.assertEqual(
            yi["exact_threshold_subsets_evaluated"],
            appss["exact_threshold_subsets_evaluated"],
        )

    def test_report_schema_and_output_are_strict_and_secret_free(self) -> None:
        root = Path(__file__).resolve().parents[2]
        schema = json.loads(
            (
                root
                / "docs/schemas/recovery-suite-compromise-regression-v1.schema.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(schema["$id"], REPORT_VERSION)
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(validate_suite_compromise_report(self.report), self.report)

        encoded = json.dumps(self.report, sort_keys=True).lower()
        for forbidden in (
            "oprf_key",
            "masked_share",
            "unmasked_share",
            "candidate_value",
            "private_key",
            "recovery_secret",
            "party_state",
            "wrap_key",
        ):
            self.assertNotIn(forbidden, encoded)
        self.assertFalse(self.report["hygiene"]["per_input_outcomes_retained"])
        self.assertFalse(self.report["hygiene"]["raw_views_retained"])

    def test_changed_report_or_manifest_fails_closed(self) -> None:
        changed = copy.deepcopy(self.report)
        changed["compromise_boundary"]["appss"]["output_without_correct_input"] = True
        with self.assertRaises(SuiteCompromiseRegressionError):
            validate_suite_compromise_report(changed)
        changed = copy.deepcopy(self.report)
        changed["common_conditions"]["authorization_quorum"] = 3
        with self.assertRaises(SuiteCompromiseRegressionError):
            validate_suite_compromise_report(changed)
        changed = copy.deepcopy(self.report)
        changed["unexpected"] = True
        with self.assertRaises(SuiteCompromiseRegressionError):
            validate_suite_compromise_report(changed)


if __name__ == "__main__":
    unittest.main()
