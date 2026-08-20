from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any, cast

from locus.performance_evidence import (
    APPSS_RESULT_ID,
    BODY_ROLES,
    COMMON_RESULT_ID,
    INSTRUMENTATION_ID,
    LIMITATIONS,
    PERSISTED_ROLES,
    PHASES,
    POSITIVE_CONTROLS,
    PROCESSOR_ID,
    RETAINED_ROOT,
    SCENARIO_MANIFEST_ID,
    SUMMARY_ID,
    YI_RESULT_ID,
    PerformanceEvidenceError,
    assert_retained_target_absent,
    build_comparison,
    build_corpus_manifest,
    canonical_json,
    digest,
    evidence_profile,
    instrumentation_profile,
    process_observations,
    processor_profile,
    scenario_manifest,
    scheduled_slots,
    validate_observation,
)
from locus.performance_methodology import methodology_contract

ROOT = Path(__file__).resolve().parents[1]


def bindings(block: int) -> dict[str, object]:
    suffix = f"{block:016x}"
    return {
        "admission_profile_id": "LOCUS-local-synthetic-admission-v1",
        "backup_format_id": "LOCUS-reference-backup-v6",
        "client_api_id": "LOCUS-client-api-v2",
        "client_instance_profile_id": "LOCUS-managed-client-instance-v1",
        "collected_at_utc": "2026-08-20T12:00:00+00:00",
        "compose_sha256": "11" * 32,
        "configuration_id": "LOCUS-integrated-manager-config-v1",
        "controller_api_id": "LOCUS-container-controller-api-v1",
        "deployment_id": "LOCUS-integrated-manager-deployment-v1",
        "descriptor_id": "LOCUS-recovery-descriptor-v1",
        "host_tier": "same-host-single-operator",
        "image_id": "sha256:" + "22" * 32,
        "live_graph_sha256": "33" * 32,
        "lockfile_sha256": "44" * 32,
        "managed_manifest_sha256": "55" * 32,
        "manager_api_id": "LOCUS-manager-api-v1",
        "network_topology_sha256": "66" * 32,
        "package_profile_id": "LOCUS-client-recovery-package-v1",
        "provider_id": "LOCUS-storage-provider-s3-compatible-v1",
        "pseudonymous_client_id": f"client-{suffix}",
        "pseudonymous_host_id": "host-0123456789abcdef",
        "pseudonymous_package_set_id": f"packages-{suffix}",
        "pseudonymous_project_id": f"project-{suffix}",
        "resolved_graph_sha256": "77" * 32,
        "service_identity_set_sha256": "88" * 32,
        "source_commit": "99" * 20,
        "source_tree_sha256": "aa" * 32,
    }


def metrics(slot: dict[str, object]) -> dict[str, object]:
    from locus.performance_evidence import _expected_phases

    phases = _expected_phases(slot)
    phase_values = {phase: 10 if phase in phases else None for phase in PHASES}
    body_values = {role: 1 for role in BODY_ROLES}
    persisted_values = {
        role: int(slot["scenario_id"] == "MP11") for role in PERSISTED_ROLES
    }
    ui_required = slot["scenario_id"] in {
        "MP01",
        "MP02",
        "MP03",
        "MP04",
        "MP05",
        "MP06",
        "MP14",
        "MP15",
        "MP16",
        "MP17",
        "MP18",
        "MP19",
    }
    lifecycle = slot["category"] == "lifecycle"
    concurrency = None
    if slot["scenario_id"] == "MP13":
        level = cast(int, slot["concurrency_level"])
        concurrency = {
            "batch_completion_ns": 1000 + level,
            "completed_operations": level,
            "level": level,
            "operations_per_second_milli": 2000 + level,
        }
    return {
        "application_body_bytes_by_role": body_values,
        "application_body_bytes_total": sum(body_values.values()),
        "concurrency": concurrency,
        "end_to_end_ns": 1000 + cast(int, slot["block"]),
        "lifecycle_ns": 700 if lifecycle else None,
        "persisted_bytes_by_role": persisted_values,
        "persisted_bytes_total": sum(persisted_values.values()),
        "phase_latency_ns": phase_values,
        "ui_http_round_trip_ns": 100 if ui_required else None,
    }


def observation(
    slot: dict[str, object],
    *,
    attempt_index: int = 1,
    invalid: bool = False,
    replacement_of_sha256: str | None = None,
) -> dict[str, object]:
    if invalid:
        status = "infrastructure-invalid"
    elif not slot["measured"]:
        status = "warmup-passed"
    elif slot["scenario_id"] in {"MP05", "MP07"}:
        status = "valid-expected-rejection"
    else:
        status = "valid-success"
    value = {
        "attempt_id": f"{slot['slot_id']}:a{attempt_index:02d}",
        "attempt_index": attempt_index,
        "bindings": bindings(cast(int, slot["block"])),
        "cleanup": {"complete": True, "resources_remaining": 0},
        "evidence_profile_id": evidence_profile()["format_id"],
        "format_id": slot["result_id"],
        "infrastructure_invalid": (
            {
                "category": "measurement-integrity-failure",
            }
            if invalid
            else None
        ),
        "instrumentation_id": INSTRUMENTATION_ID,
        "limitations": list(LIMITATIONS),
        "methodology_id": methodology_contract()["format_id"],
        "methodology_sha256": digest(methodology_contract()),
        "metrics": None if invalid or not slot["measured"] else metrics(slot),
        "outcome": status,
        "output_safety": {"prohibited_findings": 0, "scan": "passed"},
        "positive_controls": {name: True for name in POSITIVE_CONTROLS},
        "replacement_of_sha256": replacement_of_sha256,
        "scenario_manifest_id": SCENARIO_MANIFEST_ID,
        "scenario_manifest_sha256": digest(scenario_manifest()),
        "slot": slot,
        "status": status,
    }
    validate_observation(value)
    return value


class PerformanceEvidenceTests(unittest.TestCase):
    def test_checked_profiles_and_exact_schedule(self) -> None:
        checked = {
            "managed-performance-evidence-profile-v1.json": evidence_profile(),
            "managed-performance-instrumentation-v1.json": instrumentation_profile(),
            "managed-performance-processor-v1.json": processor_profile(),
            "managed-performance-scenarios-v1.json": scenario_manifest(),
        }
        for name, expected in checked.items():
            with self.subTest(name=name):
                self.assertEqual(
                    (ROOT / "docs" / name).read_bytes(), canonical_json(expected)
                )
        slots = scheduled_slots()
        self.assertEqual(len(slots), 1220)
        self.assertEqual(sum(bool(slot["measured"]) for slot in slots), 1180)
        counts: dict[str, int] = {}
        for slot in slots:
            scenario = cast(str, slot["scenario_id"])
            counts[scenario] = counts.get(scenario, 0) + 1
        self.assertEqual(counts["MP00"], 40)
        self.assertTrue(
            all(
                counts[item] == 120
                for item in ("MP01", "MP02", "MP03", "MP04", "MP05", "MP06", "MP13")
            )
        )
        self.assertTrue(
            all(counts[item] == 40 for item in ("MP07", "MP08", "MP09", "MP10", "MP11"))
        )
        self.assertEqual(counts["MP12"], 80)
        self.assertTrue(
            all(
                counts[item] == 10
                for item in ("MP14", "MP15", "MP16", "MP17", "MP18", "MP19")
            )
        )

    def test_suite_common_families_and_observation_mutations_fail_closed(self) -> None:
        slots = scheduled_slots()
        yi = next(
            slot
            for slot in slots
            if slot["scenario_id"] == "MP04" and slot["arm_id"] == "yi-2of3"
        )
        appss = next(
            slot
            for slot in slots
            if slot["scenario_id"] == "MP04" and slot["arm_id"] == "appss-2of3"
        )
        common = next(slot for slot in slots if slot["scenario_id"] == "MP14")
        self.assertEqual(observation(yi)["format_id"], YI_RESULT_ID)
        self.assertEqual(observation(appss)["format_id"], APPSS_RESULT_ID)
        self.assertEqual(observation(common)["format_id"], COMMON_RESULT_ID)
        base = observation(yi)
        mutations: list[dict[str, Any]] = []
        for change in (
            lambda v: v.__setitem__("format_id", APPSS_RESULT_ID),
            lambda v: cast(dict[str, object], v["bindings"]).__setitem__(
                "provider_id", "wrong"
            ),
            lambda v: cast(dict[str, object], v["metrics"]).__setitem__(
                "end_to_end_ns", 1
            ),
            lambda v: cast(dict[str, object], v["metrics"]).__setitem__(
                "application_body_bytes_total", 1
            ),
            lambda v: cast(dict[str, object], v["positive_controls"]).__setitem__(
                "cleanup", False
            ),
            lambda v: v.__setitem__("instrumentation_id", "wrong"),
            lambda v: v.__setitem__("format_id", "LOCUS-performance-client-samples-v2"),
            lambda v: v.__setitem__("status", "valid-expected-rejection"),
            lambda v: v.__setitem__(
                "cleanup", {"complete": False, "resources_remaining": 1}
            ),
            lambda v: v.__setitem__("payload", "fictional-canary"),
            lambda v: cast(dict[str, object], v["slot"]).__setitem__("seed", 1),
        ):
            changed = copy.deepcopy(base)
            change(changed)
            mutations.append(changed)
        for changed in mutations:
            with self.subTest(keys=changed.keys()):
                with self.assertRaises(PerformanceEvidenceError):
                    validate_observation(changed)

    def test_full_synthetic_processor_invalid_link_comparison_and_closure(self) -> None:
        slots = scheduled_slots()
        target = next(
            slot
            for slot in slots
            if slot["scenario_id"] == "MP04" and slot["arm_id"] == "yi-2of3"
        )
        invalid = observation(target, invalid=True)
        records: list[dict[str, object]] = []
        for slot in slots:
            if slot["slot_id"] == target["slot_id"]:
                records.extend(
                    [
                        invalid,
                        observation(
                            slot,
                            attempt_index=2,
                            replacement_of_sha256=digest(invalid),
                        ),
                    ]
                )
            else:
                records.append(observation(slot))
        summary = process_observations(records)
        self.assertEqual(summary["format_id"], SUMMARY_ID)
        self.assertEqual(summary["raw_attempt_count"], 1221)
        self.assertEqual(summary["infrastructure_invalid_count"], 1)
        self.assertEqual(len(cast(list[object], summary["groups"])), 70)
        comparison = build_comparison(summary)
        self.assertEqual(comparison["comparison_count"], 28)
        self.assertFalse(comparison["pooling"])
        manifest = build_corpus_manifest(records, summary, comparison)
        self.assertEqual(manifest["status"], "sealed")
        self.assertEqual(manifest["raw_attempt_count"], 1221)

        mismatched = copy.deepcopy(records)
        cast(dict[str, object], mismatched[-1]["bindings"])["live_graph_sha256"] = (
            "ff" * 32
        )
        with self.assertRaises(PerformanceEvidenceError):
            process_observations(mismatched)

        reordered = list(records)
        first_warmup = reordered.pop(0)
        reordered.append(first_warmup)
        with self.assertRaises(PerformanceEvidenceError):
            process_observations(reordered)

        mismatched_summary = copy.deepcopy(summary)
        groups = cast(list[dict[str, object]], mismatched_summary["groups"])
        appss_group = next(
            group for group in groups if group["group_id"] == "MP04:appss-2of3"
        )
        cast(dict[str, object], appss_group["metrics"]).pop("end_to_end_ns")
        with self.assertRaises(PerformanceEvidenceError):
            build_comparison(mismatched_summary)

        silent_retry = copy.deepcopy(records)
        replacement = silent_retry[1]
        replacement["replacement_of_sha256"] = "00" * 32
        with self.assertRaises(PerformanceEvidenceError):
            process_observations(silent_retry)

    def test_retained_target_guard_is_non_collecting(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            assert_retained_target_absent(workspace)
            target = workspace / RETAINED_ROOT
            target.mkdir(parents=True)
            with self.assertRaises(PerformanceEvidenceError):
                assert_retained_target_absent(workspace)
        self.assertFalse((ROOT / RETAINED_ROOT).exists())

    def test_schemas_are_strict_and_ten_identifiers_are_registered(self) -> None:
        schemas = (
            "managed-performance-evidence-profile-v1.schema.json",
            "managed-performance-instrumentation-v1.schema.json",
            "managed-performance-scenario-manifest-v1.schema.json",
            "managed-performance-result-v1.schema.json",
            "managed-performance-summary-v1.schema.json",
            "managed-performance-comparison-v1.schema.json",
            "managed-performance-corpus-manifest-v1.schema.json",
        )
        for name in schemas:
            schema = json.loads((ROOT / "docs" / "schemas" / name).read_bytes())
            self.assertFalse(schema["additionalProperties"], name)
        registry = json.loads((ROOT / "docs" / "version-registry-v1.json").read_bytes())
        protected = set(registry["protected_identifiers"])
        expected = {
            evidence_profile()["format_id"],
            INSTRUMENTATION_ID,
            SCENARIO_MANIFEST_ID,
            YI_RESULT_ID,
            APPSS_RESULT_ID,
            COMMON_RESULT_ID,
            PROCESSOR_ID,
            SUMMARY_ID,
            "LOCUS-managed-performance-comparison-v1",
            "LOCUS-managed-performance-corpus-manifest-v1",
        }
        self.assertTrue(expected <= protected)
        self.assertEqual(len(expected), 10)


if __name__ == "__main__":
    unittest.main()
