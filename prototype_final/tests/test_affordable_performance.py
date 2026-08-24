from __future__ import annotations

import copy
import unittest
from typing import cast
from unittest.mock import patch

import tasks

from locus.affordable_performance_collection import ordered_arm_block_slots
from locus.affordable_performance_evidence import (
    ARMS,
    BODY_ROLES,
    PERSISTED_ROLES,
    build_comparison,
    build_metrics,
    build_observation,
    evidence_profile,
    preflight_profile,
    process_observations,
    scenario_manifest,
    scheduled_slots,
    validate_preflight_observations,
)
from locus.affordable_performance_methodology import (
    methodology_contract,
    validate_methodology,
)


def bindings(block: int) -> dict[str, object]:
    suffix = f"{block:016x}"
    return {
        "admission_profile_id": "LOCUS-local-synthetic-admission-v1",
        "backup_format_id": "LOCUS-reference-backup-v6",
        "client_api_id": "LOCUS-client-api-v2",
        "client_instance_profile_id": "LOCUS-managed-client-instance-v1",
        "collected_at_utc": "2026-08-21T12:00:00+00:00",
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


def observation(slot: dict[str, object]) -> dict[str, object]:
    status = (
        "warmup-passed"
        if not slot["measured"]
        else "valid-expected-rejection"
        if slot["scenario_id"] == "AP04"
        else "valid-success"
    )
    metrics = None
    if slot["measured"]:
        metrics = build_metrics(
            slot=slot,
            end_to_end_ns=1000 + cast(int, slot["block"]),
            phase_latency_ns={},
            application_body_bytes_by_role={"browser": 10},
            persisted_bytes_by_role={"provider": 20},
        )
    return build_observation(
        slot=slot,
        bindings=bindings(cast(int, slot["block"])),
        metrics=metrics,
        status=status,
    )


class AffordablePerformanceTests(unittest.TestCase):
    def test_exact_affordable_budget_and_pairing(self) -> None:
        contract = methodology_contract()
        self.assertEqual(contract["sample_plan"]["fresh_project_count"], 12)
        self.assertEqual(contract["sample_plan"]["scheduled_slot_count"], 324)
        self.assertEqual(contract["sample_plan"]["measured_slot_count"], 312)
        self.assertEqual(len(scheduled_slots()), 324)
        self.assertEqual(len(ARMS), 4)
        self.assertFalse(contract["retention_gate"]["collection_authorized"])
        self.assertEqual(
            evidence_profile()["retained_root"],
            "evidence/retained/managed-performance-v2",
        )

    def test_each_arm_block_has_one_warmup_and_26_measurements(self) -> None:
        for arm_id in ARMS:
            slots = ordered_arm_block_slots(arm_id, 1)
            self.assertEqual(len(slots), 27)
            self.assertEqual(slots[0]["scenario_id"], "AP00")
            self.assertEqual(sum(bool(slot["measured"]) for slot in slots), 26)

    def test_d031_preflight_is_exact_and_never_evidence(self) -> None:
        profile = preflight_profile()
        self.assertEqual(profile["arm_id"], "appss-3of5")
        self.assertEqual(profile["block"], 1)
        self.assertEqual(profile["scheduled_slot_count"], 27)
        self.assertEqual(profile["measured_slot_count"], 26)
        self.assertFalse(profile["evidence_eligible"])
        self.assertEqual(profile["retention"], "prohibited")
        selected = [
            observation(slot)
            for slot in scheduled_slots()
            if slot["arm_id"] == "appss-3of5" and slot["block"] == 1
        ]
        result = validate_preflight_observations(selected)
        self.assertEqual(result["scheduled_slot_count"], 27)
        self.assertFalse(result["retained"])

    def test_semantic_mutation_fails_closed(self) -> None:
        changed = copy.deepcopy(methodology_contract())
        changed["sample_plan"]["central"]["samples_per_arm"] = 14
        with self.assertRaises(ValueError):
            validate_methodology(changed)

    def test_complete_synthetic_schedule_processes_without_pooling(self) -> None:
        observations = [observation(slot) for slot in scheduled_slots()]
        summary = process_observations(observations)
        comparison = build_comparison(summary)
        self.assertEqual(summary["measured_slot_count"], 312)
        self.assertEqual(len(summary["groups"]), 24)
        self.assertEqual(comparison["comparison_count"], 12)
        self.assertFalse(comparison["pooling"])
        self.assertFalse(comparison["hypothesis_test"])
        self.assertEqual(scenario_manifest()["scenario_slot_counts"]["AP06"], 12)
        for group in summary["groups"]:
            expected = 3 if group["scenario_id"] == "AP06" else 15
            self.assertEqual(group["sample_count"], expected)
            self.assertIn("mean", group["metrics"]["end_to_end_ns"])

    def test_metric_roles_are_exact(self) -> None:
        slot = next(slot for slot in scheduled_slots() if slot["scenario_id"] == "AP01")
        value = build_metrics(
            slot=slot,
            end_to_end_ns=100,
            phase_latency_ns={},
            application_body_bytes_by_role={"browser": 3},
            persisted_bytes_by_role={"provider": 7},
        )
        self.assertEqual(set(value["application_body_bytes_by_role"]), set(BODY_ROLES))
        self.assertEqual(set(value["persisted_bytes_by_role"]), set(PERSISTED_ROLES))

    def test_shared_image_cleanup_does_not_remove_the_image(self) -> None:
        calls: list[list[str]] = []

        def capture(command: list[str], **_kwargs: object) -> str:
            calls.append(command)
            return ""

        with (
            patch("tasks.run_capture", side_effect=capture),
            patch("tasks._remove_dynamic_clients"),
            patch("tasks._remove_browser_edge_network"),
            patch("tasks._dynamic_client_ids", return_value=[]),
            patch("tasks.require", side_effect=lambda value: value),
        ):
            tasks._cleanup_smoke_project(
                "locus-affordable-test",
                {"LOCUS_INTEGRATED_IMAGE": "locus-managed-performance-v2:local"},
                remove_image=False,
            )
        flattened = [item for command in calls for item in command]
        self.assertNotIn("--rmi", flattened)
        self.assertFalse(any(command[:2] == ["docker", "image"] for command in calls))


if __name__ == "__main__":
    unittest.main()
