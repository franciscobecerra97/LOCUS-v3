from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path
from types import MappingProxyType
from unittest.mock import patch

from locus.attack_runner import (
    ATTACK_REPORT_VERSION,
    SCENARIO_REGISTRY,
    AttackReportError,
    build_attack_report,
    validate_attack_report,
)
from locus.deployment import (
    BENCHMARK_VERSION,
    DeploymentError,
    validate_benchmark_result,
)

import tasks


class DeploymentProfileContractTests(unittest.TestCase):
    def test_performance_image_uses_one_stable_build_identity(self) -> None:
        image_id = f"sha256:{'d' * 64}"
        with (
            patch.object(tasks, "require", return_value="docker"),
            patch.object(tasks, "_validate_deployment_compose") as validate,
            patch.object(tasks, "run") as run,
            patch.object(
                tasks,
                "run_capture",
                side_effect=["{}", image_id],
            ) as capture,
        ):
            self.assertEqual(
                tasks._build_performance_reference_image(),
                ("locus-reference:performance-v2", image_id),
            )
        validate.assert_called_once_with(
            {}, reference_image="locus-reference:performance-v2"
        )
        build_command = run.call_args.args[0]
        self.assertEqual(
            build_command[0:4],
            [
                "docker",
                "compose",
                "-p",
                "locus-performance-image-v2",
            ],
        )
        self.assertEqual(build_command[-3:], ["build", "--pull", "provisioner"])
        self.assertEqual(capture.call_count, 2)

    def test_attack_report_schema_lists_the_registered_scenarios(self) -> None:
        root = Path(__file__).resolve().parents[2]
        schema = json.loads(
            (root / "docs" / "schemas" / "attack-report-v1.schema.json").read_text(
                encoding="utf-8"
            )
        )
        scenario_ids = schema["properties"]["scenario_id"]["enum"]
        self.assertEqual(set(scenario_ids), set(SCENARIO_REGISTRY))
        branches = {
            branch["if"]["properties"]["scenario_id"]["const"]: branch["then"][
                "properties"
            ]
            for branch in schema["allOf"]
        }
        self.assertEqual(set(branches), set(SCENARIO_REGISTRY))
        for scenario_id, scenario in SCENARIO_REGISTRY.items():
            for field in (
                "expected_result",
                "interpretation",
                "parameters",
                "prerequisites",
                "procedure",
            ):
                expected = scenario[field]
                if isinstance(expected, MappingProxyType):
                    expected = dict(expected)
                elif isinstance(expected, tuple):
                    expected = list(expected)
                with self.subTest(scenario_id=scenario_id, field=field):
                    self.assertEqual(branches[scenario_id][field]["const"], expected)

    def test_profile_evidence_schema_registers_performance_results(self) -> None:
        root = Path(__file__).resolve().parents[2]
        profile_schema = json.loads(
            (root / "docs" / "schemas" / "profile-evidence-v1.schema.json").read_text(
                encoding="utf-8"
            )
        )
        references = {
            item["$ref"] for item in profile_schema["properties"]["result"]["oneOf"]
        }
        self.assertEqual(
            references,
            {
                "attack-report-v1.schema.json",
                "benchmark-result-v1.schema.json",
                "performance-result-v1.schema.json",
            },
        )
        performance_schema = json.loads(
            (root / "docs" / "schemas" / "performance-result-v1.schema.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            performance_schema["properties"]["artifact"]["const"],
            "LOCUS-compose-performance-result-v1",
        )
        processed_schema = json.loads(
            (
                root / "docs" / "schemas" / "performance-processed-v1.schema.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(
            processed_schema["properties"]["artifact"]["const"],
            "LOCUS-performance-processed-v1",
        )
        self.assertEqual(
            processed_schema["properties"]["processing"]["properties"][
                "samples_per_scenario"
            ]["const"],
            30,
        )
        paper_inputs_schema = json.loads(
            (
                root / "docs" / "schemas" / "performance-paper-inputs-v1.schema.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(
            paper_inputs_schema["properties"]["artifact"]["const"],
            "LOCUS-performance-paper-inputs-v1",
        )
        self.assertEqual(
            paper_inputs_schema["properties"]["format"]["properties"]["version"][
                "const"
            ],
            "LOCUS-performance-latex-rows-v1",
        )
        processed_v2_schema = json.loads(
            (
                root / "docs" / "schemas" / "performance-processed-v2.schema.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(
            processed_v2_schema["properties"]["artifact"]["const"],
            "LOCUS-performance-processed-v2",
        )
        self.assertEqual(
            processed_v2_schema["properties"]["source"]["properties"]["experiment_id"][
                "const"
            ],
            "compose-performance-v2",
        )
        paper_inputs_v2_schema = json.loads(
            (
                root / "docs" / "schemas" / "performance-paper-inputs-v2.schema.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(
            paper_inputs_v2_schema["properties"]["artifact"]["const"],
            "LOCUS-performance-paper-inputs-v2",
        )

    def test_benchmark_result_is_exact_and_summary_bound(self) -> None:
        result = {
            "artifact": BENCHMARK_VERSION,
            "attempts": {"after": 2, "before": 0, "budget": 4},
            "latency_ms": {
                "max": 12.0,
                "mean": 11.0,
                "median": 11.0,
                "min": 10.0,
                "samples": [10.0, 12.0],
            },
            "profile": "benchmark",
            "runs": 2,
            "selected": [1, 3],
            "status": "ok",
        }
        self.assertEqual(validate_benchmark_result(result), result)
        for mutate in ("attempts", "summary", "field"):
            invalid = copy.deepcopy(result)
            if mutate == "attempts":
                attempts = invalid["attempts"]
                assert isinstance(attempts, dict)
                attempts["after"] = 3
            elif mutate == "summary":
                latency = invalid["latency_ms"]
                assert isinstance(latency, dict)
                latency["median"] = 99.0
            else:
                invalid["raw_cues"] = "forbidden"
            with self.subTest(mutate=mutate):
                with self.assertRaises(DeploymentError):
                    validate_benchmark_result(invalid)

    def test_attack_report_is_registry_bound_and_redacted(self) -> None:
        self.assertEqual(
            set(SCENARIO_REGISTRY),
            {
                "cloud-plus-t-minus-one-party-snapshot-no-offline-predicate-v1",
                "cloud-snapshot-no-offline-predicate-v1",
                "cross-epoch-runtime-mix-v1",
                "resolver-unavailable-v1",
                "t-minus-one-party-snapshot-no-offline-predicate-v1",
            },
        )
        self.assertIsInstance(SCENARIO_REGISTRY, MappingProxyType)
        for scenario in SCENARIO_REGISTRY.values():
            self.assertIsInstance(scenario, MappingProxyType)
            self.assertIsInstance(scenario["expected_result"], MappingProxyType)
        report = build_attack_report(
            scenario_id="resolver-unavailable-v1",
            observed_result={
                "attempt_delta": 0,
                "failure_category": "resolver-unavailable",
            },
        )
        self.assertEqual(report["version"], ATTACK_REPORT_VERSION)
        self.assertEqual(report["status"], "passed")
        self.assertEqual(validate_attack_report(report), report)

        changed = copy.deepcopy(report)
        changed["procedure"] = ["claim a different procedure"]
        with self.assertRaises(AttackReportError):
            validate_attack_report(changed)

        failed = build_attack_report(
            scenario_id="resolver-unavailable-v1",
            observed_result={
                "attempt_delta": 1,
                "failure_category": "unexpected-success",
            },
        )
        self.assertEqual(failed["status"], "failed")

        lifecycle = build_attack_report(
            scenario_id="cross-epoch-runtime-mix-v1",
            observed_result={
                "cross_epoch_mix": "rejected",
                "old_epoch_refusal": "rejected",
                "old_epoch_status": "retired",
                "party_restart": "verified",
                "partial_new_active": 3,
                "partial_old_active": 2,
                "successor_epoch_status": "active",
                "successor_recovery": "verified",
            },
        )
        self.assertEqual(lifecycle["status"], "passed")
        self.assertEqual(validate_attack_report(lifecycle), lifecycle)

        malformed = copy.deepcopy(lifecycle)
        observed = malformed["observed_result"]
        assert isinstance(observed, dict)
        observed["raw_cues"] = "forbidden"
        with self.assertRaises(AttackReportError):
            validate_attack_report(malformed)

        cloud_snapshot = build_attack_report(
            scenario_id="cloud-snapshot-no-offline-predicate-v1",
            observed_result={
                "candidate_count": 2,
                "candidate_signals": 0,
                "excluded_path_accesses": 0,
                "network_attempts": 0,
                "prohibited_material": "absent",
                "snapshot_validation": "passed",
            },
        )
        self.assertEqual(cloud_snapshot["status"], "passed")
        self.assertEqual(validate_attack_report(cloud_snapshot), cloud_snapshot)
        secret_bearing = copy.deepcopy(cloud_snapshot)
        cloud_observed = secret_bearing["observed_result"]
        assert isinstance(cloud_observed, dict)
        cloud_observed["raw_cues"] = "forbidden"
        with self.assertRaises(AttackReportError):
            validate_attack_report(secret_bearing)


if __name__ == "__main__":
    unittest.main()
