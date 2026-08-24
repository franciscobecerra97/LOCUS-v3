"""Strict D030/P9.3 affordable managed-performance evidence contracts."""

from __future__ import annotations

from collections import defaultdict
import hashlib
import json
import math
import os
from pathlib import Path
import re
from typing import Any, cast

from .affordable_performance_methodology import methodology_contract
from .performance_evidence import (
    BODY_ROLES,
    INVALID_CATEGORIES,
    PERSISTED_ROLES,
    PHASES,
    _validate_bindings,
    canonical_json,
    digest,
)

EVIDENCE_PROFILE_ID = "LOCUS-managed-performance-evidence-profile-v2"
INSTRUMENTATION_ID = "LOCUS-managed-performance-instrumentation-v2"
SCENARIO_MANIFEST_ID = "LOCUS-managed-performance-scenario-manifest-v2"
YI_RESULT_ID = "LOCUS-managed-performance-result-yi-v2"
APPSS_RESULT_ID = "LOCUS-managed-performance-result-appss-v2"
PROCESSOR_ID = "LOCUS-managed-performance-processor-v2"
SUMMARY_ID = "LOCUS-managed-performance-summary-v2"
COMPARISON_ID = "LOCUS-managed-performance-comparison-v2"
CORPUS_MANIFEST_ID = "LOCUS-managed-performance-corpus-manifest-v2"
CHECKPOINT_ID = "LOCUS-managed-performance-checkpoint-v1"
PREFLIGHT_ID = "LOCUS-managed-performance-preflight-v1"

RETAINED_ROOT = Path("evidence/retained/managed-performance-v2")
STAGING_ROOT = Path("evidence/retained/.managed-performance-v2-staging")

ARMS = {arm["arm_id"]: arm for arm in methodology_contract()["arms"]}
LIMITATIONS = tuple(methodology_contract()["limitations"])
RESULT_IDS = frozenset({YI_RESULT_ID, APPSS_RESULT_ID})
POSITIVE_CONTROLS = (
    "monotonic-clock",
    "phase-nonoverlap",
    "end-to-end-bounds-phases",
    "application-byte-reconciliation",
    "persisted-byte-reconciliation",
    "warmup-precedes-measurement",
    "graph-and-arm-binding",
    "expected-scenario-outcome",
    "failure-schedule-binding",
    "invalid-attempt-linkage",
    "block-checkpoint-binding",
    "prohibited-output-canary",
    "cleanup",
    "raw-to-processed-hash-closure",
)
SCENARIOS: dict[str, dict[str, Any]] = {
    "AP00": {"name": "warmup", "category": "warmup", "measured": False},
    "AP01": {"name": "enrollment", "category": "central", "measured": True},
    "AP02": {
        "name": "package-transfer-and-clean-bootstrap",
        "category": "central",
        "measured": True,
    },
    "AP03": {
        "name": "successful-recovery",
        "category": "central",
        "measured": True,
    },
    "AP04": {
        "name": "wrong-input-rejection",
        "category": "central",
        "measured": True,
    },
    "AP05": {
        "name": "one-party-unavailable-recovery",
        "category": "central",
        "measured": True,
    },
    "AP06": {
        "name": "storage-and-role-snapshot",
        "category": "structural",
        "measured": True,
    },
}
PHASES_BY_SCENARIO = {
    "AP01": frozenset(
        {
            "policy",
            "suite-initialization",
            "encryption-and-upload",
            "party-provisioning",
            "descriptor-publication-and-retrieval",
        }
    ),
    "AP02": frozenset({"descriptor-publication-and-retrieval", "authorization"}),
    "AP03": frozenset({"authorization", "recovery"}),
    "AP04": frozenset({"policy", "authorization", "recovery"}),
    "AP05": frozenset({"authorization", "recovery"}),
}


class AffordablePerformanceEvidenceError(ValueError):
    """An affordable performance contract or corpus is malformed."""


def evidence_profile() -> dict[str, object]:
    return {
        "format_id": EVIDENCE_PROFILE_ID,
        "decision_id": "D030",
        "methodology_id": methodology_contract()["format_id"],
        "instrumentation_id": INSTRUMENTATION_ID,
        "scenario_manifest_id": SCENARIO_MANIFEST_ID,
        "processor_id": PROCESSOR_ID,
        "result_ids": [YI_RESULT_ID, APPSS_RESULT_ID],
        "derived_ids": [SUMMARY_ID, COMPARISON_ID, CORPUS_MANIFEST_ID],
        "checkpoint_id": CHECKPOINT_ID,
        "scheduled_slot_count": 324,
        "measured_slot_count": 312,
        "retained_root": RETAINED_ROOT.as_posix(),
        "staging_root": STAGING_ROOT.as_posix(),
        "publication": "resumable-block-staging-then-exclusive-atomic-seal",
        "collection_authorized": False,
        "status": "assigned-preparation-only",
    }


def instrumentation_profile() -> dict[str, object]:
    return {
        "format_id": INSTRUMENTATION_ID,
        "clock": "client-monotonic-nanoseconds",
        "end_to_end": "client-observed",
        "phase_rule": "fixed-applicable-non-overlapping-and-bounded-by-end-to-end",
        "phases": list(PHASES[:-1]),
        "application_body_roles": list(BODY_ROLES),
        "persisted_roles": list(PERSISTED_ROLES),
        "positive_controls": list(POSITIVE_CONTROLS),
        "excluded_metrics": [
            "browser-rendering",
            "ui-round-trip",
            "lifecycle-latency",
            "concurrency-throughput",
            "successor-latency",
        ],
        "status": "assigned",
    }


def processor_profile() -> dict[str, object]:
    return {
        "format_id": PROCESSOR_ID,
        "methodology_id": methodology_contract()["format_id"],
        "quantile_method": "linear-type-7",
        "reported": ["count", "median", "q1", "q3", "min", "max", "mean"],
        "outlier_removal": "none",
        "confidence_intervals": False,
        "hypothesis_tests": False,
        "comparison_rule": "matched-side-by-side-no-pooling-or-advantage-claim",
        "status": "assigned",
    }


def _result_id(arm_id: str) -> str:
    return YI_RESULT_ID if ARMS[arm_id]["family"] == "yi" else APPSS_RESULT_ID


def _slot(
    scenario_id: str, arm_id: str, block: int, repetition: int
) -> dict[str, object]:
    failure_schedule: object = None
    if scenario_id == "AP05":
        topology = arm_id.split("-", 1)[1]
        failure_schedule = methodology_contract()["failure_schedules"][
            f"{topology}_one_party_unavailable"
        ]
    return {
        "slot_id": f"{scenario_id}:{arm_id}:b{block:02d}:r{repetition:02d}",
        "scenario_id": scenario_id,
        "category": SCENARIOS[scenario_id]["category"],
        "measured": SCENARIOS[scenario_id]["measured"],
        "arm_id": arm_id,
        "arm": ARMS[arm_id],
        "failure_schedule": failure_schedule,
        "block": block,
        "seed": methodology_contract()["blocking_and_randomization"]["seeds"][
            block - 1
        ],
        "repetition": repetition,
        "result_id": _result_id(arm_id),
    }


def scheduled_slots() -> tuple[dict[str, object], ...]:
    slots: list[dict[str, object]] = []
    for block in range(1, 4):
        for arm_id in ARMS:
            slots.append(_slot("AP00", arm_id, block, 1))
            for scenario_id in ("AP01", "AP02", "AP03", "AP04", "AP05"):
                for repetition in range(1, 6):
                    slots.append(_slot(scenario_id, arm_id, block, repetition))
            slots.append(_slot("AP06", arm_id, block, 1))
    if len(slots) != 324 or len({slot["slot_id"] for slot in slots}) != 324:
        raise AffordablePerformanceEvidenceError("affordable schedule changed")
    if sum(bool(slot["measured"]) for slot in slots) != 312:
        raise AffordablePerformanceEvidenceError("affordable measured count changed")
    return tuple(slots)


def scenario_manifest() -> dict[str, object]:
    counts: dict[str, int] = defaultdict(int)
    for slot in scheduled_slots():
        counts[cast(str, slot["scenario_id"])] += 1
    return {
        "format_id": SCENARIO_MANIFEST_ID,
        "evidence_profile_id": EVIDENCE_PROFILE_ID,
        "methodology_id": methodology_contract()["format_id"],
        "methodology_sha256": digest(methodology_contract()),
        "scenarios": SCENARIOS,
        "scenario_slot_counts": dict(sorted(counts.items())),
        "scheduled_slot_count": 324,
        "measured_slot_count": 312,
        "fresh_project_count": 12,
        "slot_digest": digest(list(scheduled_slots())),
        "attempt_statuses": [
            "warmup-passed",
            "valid-success",
            "valid-expected-rejection",
            "infrastructure-invalid",
        ],
        "invalid_categories": list(INVALID_CATEGORIES),
        "status": "assigned",
    }


def _expected_phases(slot: dict[str, object]) -> frozenset[str]:
    phases = PHASES_BY_SCENARIO.get(cast(str, slot["scenario_id"]), frozenset())
    if slot["scenario_id"] == "AP01":
        arm = ARMS[cast(str, slot["arm_id"])]
        if arm["n"] == 5:
            phases |= {"resolver"}
        if arm["family"] == "appss":
            phases |= {"appss-per-server-initialization"}
    return phases


def build_metrics(
    *,
    slot: dict[str, object],
    end_to_end_ns: int,
    phase_latency_ns: dict[str, int],
    application_body_bytes_by_role: dict[str, int],
    persisted_bytes_by_role: dict[str, int],
) -> dict[str, object]:
    expected = _expected_phases(slot)
    phases = {
        phase: max(0, int(phase_latency_ns.get(phase, 0)))
        if phase in expected
        else None
        for phase in PHASES[:-1]
    }
    if sum(cast(int, phases[phase]) for phase in expected) > end_to_end_ns:
        raise AffordablePerformanceEvidenceError("phases exceed end-to-end latency")
    body = {
        role: max(0, int(application_body_bytes_by_role.get(role, 0)))
        for role in BODY_ROLES
    }
    persisted = {
        role: max(0, int(persisted_bytes_by_role.get(role, 0)))
        for role in PERSISTED_ROLES
    }
    return {
        "end_to_end_ns": max(0, int(end_to_end_ns)),
        "phase_latency_ns": phases,
        "application_body_bytes_by_role": body,
        "application_body_bytes_total": sum(body.values()),
        "persisted_bytes_by_role": persisted,
        "persisted_bytes_total": sum(persisted.values()),
    }


def build_observation(
    *,
    slot: dict[str, object],
    bindings: dict[str, object],
    metrics: dict[str, object] | None,
    status: str,
    attempt_index: int = 1,
    replacement_of_sha256: str | None = None,
    invalid_category: str | None = None,
    cleanup_complete: bool = True,
) -> dict[str, object]:
    result = {
        "attempt_id": f"{slot['slot_id']}:a{attempt_index:02d}",
        "attempt_index": attempt_index,
        "bindings": bindings,
        "cleanup": {
            "complete": cleanup_complete,
            "resources_remaining": 0 if cleanup_complete else 1,
        },
        "evidence_profile_id": EVIDENCE_PROFILE_ID,
        "format_id": slot["result_id"],
        "infrastructure_invalid": None
        if invalid_category is None
        else {"category": invalid_category},
        "instrumentation_id": INSTRUMENTATION_ID,
        "limitations": list(LIMITATIONS),
        "methodology_id": methodology_contract()["format_id"],
        "methodology_sha256": digest(methodology_contract()),
        "metrics": metrics,
        "outcome": status,
        "output_safety": {"prohibited_findings": 0, "scan": "passed"},
        "positive_controls": {name: True for name in POSITIVE_CONTROLS},
        "replacement_of_sha256": replacement_of_sha256,
        "scenario_manifest_id": SCENARIO_MANIFEST_ID,
        "scenario_manifest_sha256": digest(scenario_manifest()),
        "slot": slot,
        "status": status,
    }
    validate_observation(result)
    return result


def validate_observation(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise AffordablePerformanceEvidenceError("observation is not an object")
    required = {
        "attempt_id",
        "attempt_index",
        "bindings",
        "cleanup",
        "evidence_profile_id",
        "format_id",
        "infrastructure_invalid",
        "instrumentation_id",
        "limitations",
        "methodology_id",
        "methodology_sha256",
        "metrics",
        "outcome",
        "output_safety",
        "positive_controls",
        "replacement_of_sha256",
        "scenario_manifest_id",
        "scenario_manifest_sha256",
        "slot",
        "status",
    }
    if set(value) != required:
        raise AffordablePerformanceEvidenceError("observation field set changed")
    fixed = {
        "evidence_profile_id": EVIDENCE_PROFILE_ID,
        "instrumentation_id": INSTRUMENTATION_ID,
        "methodology_id": methodology_contract()["format_id"],
        "methodology_sha256": digest(methodology_contract()),
        "scenario_manifest_id": SCENARIO_MANIFEST_ID,
        "scenario_manifest_sha256": digest(scenario_manifest()),
    }
    if any(value[key] != expected for key, expected in fixed.items()):
        raise AffordablePerformanceEvidenceError("observation binding changed")
    slot = value["slot"]
    expected_slots = {cast(str, item["slot_id"]): item for item in scheduled_slots()}
    if (
        not isinstance(slot, dict)
        or expected_slots.get(cast(str, slot.get("slot_id"))) != slot
    ):
        raise AffordablePerformanceEvidenceError("scheduled slot changed")
    if value["format_id"] != slot["result_id"] or value["format_id"] not in RESULT_IDS:
        raise AffordablePerformanceEvidenceError("suite result family mismatch")
    attempt_index = value["attempt_index"]
    if not isinstance(attempt_index, int) or not 1 <= attempt_index <= 99:
        raise AffordablePerformanceEvidenceError("attempt index invalid")
    if value["attempt_id"] != f"{slot['slot_id']}:a{attempt_index:02d}":
        raise AffordablePerformanceEvidenceError("attempt identifier changed")
    replacement = value["replacement_of_sha256"]
    if (attempt_index == 1 and replacement is not None) or (
        attempt_index > 1
        and (
            not isinstance(replacement, str)
            or re.fullmatch(r"[0-9a-f]{64}", replacement) is None
        )
    ):
        raise AffordablePerformanceEvidenceError("replacement linkage invalid")
    status = value["status"]
    expected_status = (
        "warmup-passed"
        if not slot["measured"]
        else (
            "valid-expected-rejection"
            if slot["scenario_id"] == "AP04"
            else "valid-success"
        )
    )
    invalid = value["infrastructure_invalid"]
    if status == "infrastructure-invalid":
        if (
            not isinstance(invalid, dict)
            or invalid.get("category") not in INVALID_CATEGORIES
            or value["metrics"] is not None
        ):
            raise AffordablePerformanceEvidenceError("infrastructure record invalid")
    elif (
        status != expected_status
        or invalid is not None
        or (slot["measured"] and value["metrics"] is None)
        or (not slot["measured"] and value["metrics"] is not None)
    ):
        raise AffordablePerformanceEvidenceError("observation status invalid")
    if value["outcome"] != status:
        raise AffordablePerformanceEvidenceError("outcome/status mismatch")
    _validate_bindings(value["bindings"])
    if value["positive_controls"] != {name: True for name in POSITIVE_CONTROLS}:
        raise AffordablePerformanceEvidenceError("positive controls changed")
    if value["output_safety"] != {"prohibited_findings": 0, "scan": "passed"}:
        raise AffordablePerformanceEvidenceError("output safety failed")
    if value["limitations"] != list(LIMITATIONS):
        raise AffordablePerformanceEvidenceError("limitations changed")
    metrics = value["metrics"]
    if isinstance(metrics, dict):
        if set(metrics) != {
            "end_to_end_ns",
            "phase_latency_ns",
            "application_body_bytes_by_role",
            "application_body_bytes_total",
            "persisted_bytes_by_role",
            "persisted_bytes_total",
        }:
            raise AffordablePerformanceEvidenceError("metric field set changed")
        if metrics != build_metrics(
            slot=slot,
            end_to_end_ns=cast(int, metrics["end_to_end_ns"]),
            phase_latency_ns={
                key: cast(int, item)
                for key, item in cast(
                    dict[str, object], metrics["phase_latency_ns"]
                ).items()
                if isinstance(item, int)
            },
            application_body_bytes_by_role=cast(
                dict[str, int], metrics["application_body_bytes_by_role"]
            ),
            persisted_bytes_by_role=cast(
                dict[str, int], metrics["persisted_bytes_by_role"]
            ),
        ):
            raise AffordablePerformanceEvidenceError("metric reconciliation failed")
    return value


def _type7(values: list[int], probability: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower, upper = math.floor(position), math.ceil(position)
    if lower == upper:
        return float(ordered[lower])
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def _statistics(values: list[int]) -> dict[str, object]:
    return {
        "count": len(values),
        "median": _type7(values, 0.5),
        "q1": _type7(values, 0.25),
        "q3": _type7(values, 0.75),
        "min": min(values),
        "max": max(values),
        "mean": sum(values) / len(values),
    }


def _terminal_attempts(
    observations: list[dict[str, object]],
    *,
    expected_slot_ids: set[str] | None = None,
) -> tuple[list[dict[str, object]], int]:
    scheduled = (
        {cast(str, slot["slot_id"]) for slot in scheduled_slots()}
        if expected_slot_ids is None
        else expected_slot_ids
    )
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for item in observations:
        validate_observation(item)
        grouped[cast(str, cast(dict[str, object], item["slot"])["slot_id"])].append(
            item
        )
    if set(grouped) != scheduled:
        raise AffordablePerformanceEvidenceError("corpus schedule incomplete")
    terminal: list[dict[str, object]] = []
    invalid_count = 0
    for slot_id in sorted(grouped):
        attempts = sorted(
            grouped[slot_id], key=lambda item: cast(int, item["attempt_index"])
        )
        if [item["attempt_index"] for item in attempts] != list(
            range(1, len(attempts) + 1)
        ):
            raise AffordablePerformanceEvidenceError("attempt chain is not contiguous")
        for index, item in enumerate(attempts):
            if index and item["replacement_of_sha256"] != digest(attempts[index - 1]):
                raise AffordablePerformanceEvidenceError("replacement digest mismatch")
            if index and attempts[index - 1]["status"] != "infrastructure-invalid":
                raise AffordablePerformanceEvidenceError("valid attempt was retried")
            invalid_count += item["status"] == "infrastructure-invalid"
        if attempts[-1]["status"] == "infrastructure-invalid":
            raise AffordablePerformanceEvidenceError(
                "slot has no terminal valid attempt"
            )
        terminal.append(attempts[-1])
    return terminal, invalid_count


def preflight_profile() -> dict[str, object]:
    return {
        "format_id": PREFLIGHT_ID,
        "decision_id": "D031",
        "arm_id": "appss-3of5",
        "block": 1,
        "scenario_ids": ["AP00", "AP01", "AP02", "AP03", "AP04", "AP05", "AP06"],
        "scheduled_slot_count": 27,
        "measured_slot_count": 26,
        "evidence_eligible": False,
        "retention": "prohibited",
        "prerequisite_for_retention": True,
        "collection_authorized": False,
        "status": "assigned-preparation-only",
    }


def validate_preflight_observations(
    observations: list[dict[str, object]],
) -> dict[str, object]:
    expected = {
        cast(str, slot["slot_id"])
        for slot in scheduled_slots()
        if slot["arm_id"] == "appss-3of5" and slot["block"] == 1
    }
    terminal, invalid_count = _terminal_attempts(
        observations, expected_slot_ids=expected
    )
    if (
        len(terminal) != 27
        or sum(
            bool(cast(dict[str, object], item["slot"])["measured"]) for item in terminal
        )
        != 26
    ):
        raise AffordablePerformanceEvidenceError("preflight coverage changed")
    warmup_position = next(
        index
        for index, item in enumerate(observations)
        if cast(dict[str, object], item["slot"])["scenario_id"] == "AP00"
        and item["status"] != "infrastructure-invalid"
    )
    if any(
        cast(dict[str, object], item["slot"])["measured"]
        and observations.index(item) <= warmup_position
        for item in terminal
    ):
        raise AffordablePerformanceEvidenceError(
            "preflight measurement preceded warmup"
        )
    return {
        "format_id": PREFLIGHT_ID,
        "scheduled_slot_count": 27,
        "measured_slot_count": 26,
        "raw_attempt_count": len(observations),
        "infrastructure_invalid_count": invalid_count,
        "evidence_eligible": False,
        "retained": False,
        "status": "passed",
    }


def process_observations(observations: list[dict[str, object]]) -> dict[str, object]:
    terminal, invalid_count = _terminal_attempts(observations)
    stable_fields = {
        "compose_sha256",
        "host_tier",
        "image_id",
        "live_graph_sha256",
        "lockfile_sha256",
        "managed_manifest_sha256",
        "network_topology_sha256",
        "resolved_graph_sha256",
        "service_identity_set_sha256",
        "source_commit",
        "source_tree_sha256",
        "deployment_id",
        "configuration_id",
        "provider_id",
    }
    first_bindings = cast(dict[str, object], observations[0]["bindings"])
    for item in observations[1:]:
        current = cast(dict[str, object], item["bindings"])
        if any(current[field] != first_bindings[field] for field in stable_fields):
            raise AffordablePerformanceEvidenceError("corpus provenance is not matched")
    groups: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    warmups: set[tuple[str, int]] = set()
    for item in terminal:
        slot = cast(dict[str, object], item["slot"])
        if slot["scenario_id"] == "AP00":
            warmups.add((cast(str, slot["arm_id"]), cast(int, slot["block"])))
        elif slot["measured"]:
            groups[(cast(str, slot["scenario_id"]), cast(str, slot["arm_id"]))].append(
                item
            )
    if len(warmups) != 12:
        raise AffordablePerformanceEvidenceError("warmup coverage changed")
    positions = {
        cast(str, item["attempt_id"]): index for index, item in enumerate(observations)
    }
    warmup_positions = {
        (
            cast(str, cast(dict[str, object], item["slot"])["arm_id"]),
            cast(int, cast(dict[str, object], item["slot"])["block"]),
        ): positions[cast(str, item["attempt_id"])]
        for item in terminal
        if cast(dict[str, object], item["slot"])["scenario_id"] == "AP00"
    }
    for item in terminal:
        slot = cast(dict[str, object], item["slot"])
        key = (cast(str, slot["arm_id"]), cast(int, slot["block"]))
        if (
            slot["measured"]
            and warmup_positions[key] >= positions[cast(str, item["attempt_id"])]
        ):
            raise AffordablePerformanceEvidenceError("measurement lacks prior warmup")
    summary_groups: list[dict[str, object]] = []
    for (scenario_id, arm_id), members in sorted(groups.items()):
        metrics: dict[str, list[int]] = defaultdict(list)
        for item in members:
            value = cast(dict[str, object], item["metrics"])
            metrics["end_to_end_ns"].append(cast(int, value["end_to_end_ns"]))
            metrics["application_body_bytes_total"].append(
                cast(int, value["application_body_bytes_total"])
            )
            metrics["persisted_bytes_total"].append(
                cast(int, value["persisted_bytes_total"])
            )
            for phase, latency in cast(
                dict[str, object], value["phase_latency_ns"]
            ).items():
                if isinstance(latency, int):
                    metrics[f"phase:{phase}"].append(latency)
        expected_count = 3 if scenario_id == "AP06" else 15
        if len(members) != expected_count:
            raise AffordablePerformanceEvidenceError("summary sample count changed")
        summary_groups.append(
            {
                "group_id": f"{scenario_id}:{arm_id}",
                "scenario_id": scenario_id,
                "arm_id": arm_id,
                "family": ARMS[arm_id]["family"],
                "sample_count": len(members),
                "metrics": {
                    key: _statistics(values) for key, values in sorted(metrics.items())
                },
                "observation_set_sha256": digest(
                    sorted(digest(item) for item in members)
                ),
            }
        )
    if len(summary_groups) != 24:
        raise AffordablePerformanceEvidenceError("summary group count changed")
    summary = {
        "format_id": SUMMARY_ID,
        "evidence_profile_id": EVIDENCE_PROFILE_ID,
        "methodology_id": methodology_contract()["format_id"],
        "processor_id": PROCESSOR_ID,
        "scenario_manifest_sha256": digest(scenario_manifest()),
        "scheduled_slot_count": 324,
        "measured_slot_count": 312,
        "raw_attempt_count": len(observations),
        "infrastructure_invalid_count": invalid_count,
        "outlier_removal": "none",
        "groups": summary_groups,
        "binding_set_sha256": digest(
            sorted(digest(item["bindings"]) for item in observations)
        ),
        "limitations": list(LIMITATIONS),
        "status": "processed",
    }
    validate_summary(summary)
    return summary


def validate_summary(value: object) -> dict[str, object]:
    if not isinstance(value, dict) or (
        value.get("format_id") != SUMMARY_ID
        or value.get("evidence_profile_id") != EVIDENCE_PROFILE_ID
        or value.get("methodology_id") != methodology_contract()["format_id"]
        or value.get("processor_id") != PROCESSOR_ID
        or value.get("scheduled_slot_count") != 324
        or value.get("measured_slot_count") != 312
        or value.get("outlier_removal") != "none"
        or value.get("status") != "processed"
        or not isinstance(value.get("groups"), list)
        or len(cast(list[object], value["groups"])) != 24
    ):
        raise AffordablePerformanceEvidenceError("summary contract changed")
    for group in cast(list[dict[str, object]], value["groups"]):
        for statistic in cast(dict[str, dict[str, object]], group["metrics"]).values():
            if set(statistic) != {"count", "median", "q1", "q3", "min", "max", "mean"}:
                raise AffordablePerformanceEvidenceError("summary statistic changed")
    return value


def build_comparison(summary: dict[str, object]) -> dict[str, object]:
    validate_summary(summary)
    groups = {
        cast(str, group["group_id"]): group
        for group in cast(list[dict[str, object]], summary["groups"])
    }
    pairs: list[dict[str, object]] = []
    for scenario_id in ("AP01", "AP02", "AP03", "AP04", "AP05", "AP06"):
        for topology in ("2of3", "3of5"):
            yi = groups[f"{scenario_id}:yi-{topology}"]
            appss = groups[f"{scenario_id}:appss-{topology}"]
            yi_metrics = cast(dict[str, dict[str, object]], yi["metrics"])
            appss_metrics = cast(dict[str, dict[str, object]], appss["metrics"])
            shared = set(yi_metrics) & set(appss_metrics)
            pairs.append(
                {
                    "comparison_id": f"{scenario_id}:{topology}",
                    "scenario_id": scenario_id,
                    "topology": topology,
                    "yi_group_sha256": digest(yi),
                    "appss_group_sha256": digest(appss),
                    "side_by_side_medians": {
                        metric: {
                            "yi": yi_metrics[metric]["median"],
                            "appss": appss_metrics[metric]["median"],
                        }
                        for metric in sorted(shared)
                    },
                }
            )
    comparison = {
        "format_id": COMPARISON_ID,
        "processor_id": PROCESSOR_ID,
        "summary_id": SUMMARY_ID,
        "summary_sha256": digest(summary),
        "comparison_count": 12,
        "pairs": pairs,
        "pooling": False,
        "hypothesis_test": False,
        "interpretation": "matched-side-by-side-descriptive-only-no-advantage-claim",
        "limitations": list(LIMITATIONS),
        "status": "derived",
    }
    validate_comparison(comparison)
    return comparison


def validate_comparison(value: object) -> dict[str, object]:
    if not isinstance(value, dict) or (
        value.get("format_id") != COMPARISON_ID
        or value.get("processor_id") != PROCESSOR_ID
        or value.get("summary_id") != SUMMARY_ID
        or value.get("comparison_count") != 12
        or not isinstance(value.get("pairs"), list)
        or len(cast(list[object], value["pairs"])) != 12
        or value.get("pooling") is not False
        or value.get("hypothesis_test") is not False
        or value.get("status") != "derived"
    ):
        raise AffordablePerformanceEvidenceError("comparison contract changed")
    return value


def _raw_relative_path(observation: dict[str, object]) -> Path:
    slot = cast(dict[str, object], observation["slot"])
    return (
        Path("raw")
        / cast(str, slot["slot_id"]).replace(":", "/")
        / f"attempt-{cast(int, observation['attempt_index']):02d}.json"
    )


def exclusive_write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(canonical_json(value))
        handle.flush()
        os.fsync(handle.fileno())


def checkpoint_profile(
    bindings: dict[str, object], completed_blocks: list[str], active_block: str | None
) -> dict[str, object]:
    return {
        "format_id": CHECKPOINT_ID,
        "evidence_profile_id": EVIDENCE_PROFILE_ID,
        "methodology_sha256": digest(methodology_contract()),
        "scenario_manifest_sha256": digest(scenario_manifest()),
        "bindings": bindings,
        "completed_arm_blocks": sorted(completed_blocks),
        "active_arm_block": active_block,
        "status": "coordination-only-not-evidence",
    }


def build_corpus_manifest(
    observations: list[dict[str, object]],
    summary: dict[str, object],
    comparison: dict[str, object],
) -> dict[str, object]:
    terminal, invalid_count = _terminal_attempts(observations)
    paths = [_raw_relative_path(item).as_posix() for item in observations]
    manifest = {
        "format_id": CORPUS_MANIFEST_ID,
        "evidence_profile_id": EVIDENCE_PROFILE_ID,
        "retained_root": RETAINED_ROOT.as_posix(),
        "scheduled_slot_count": 324,
        "terminal_slot_count": len(terminal),
        "measured_slot_count": 312,
        "raw_attempt_count": len(observations),
        "infrastructure_invalid_count": invalid_count,
        "raw_records_sha256": digest(
            sorted(
                (path, digest(item))
                for path, item in zip(paths, observations, strict=True)
            )
        ),
        "summary_path": "processed/summary.json",
        "summary_sha256": digest(summary),
        "comparison_path": "derived/comparison.json",
        "comparison_sha256": digest(comparison),
        "publication": "resumable-block-staging-then-exclusive-atomic-seal",
        "positive_controls": {name: True for name in POSITIVE_CONTROLS},
        "status": "sealed",
    }
    validate_corpus_manifest(manifest)
    return manifest


def validate_corpus_manifest(value: object) -> dict[str, object]:
    if not isinstance(value, dict) or (
        value.get("format_id") != CORPUS_MANIFEST_ID
        or value.get("evidence_profile_id") != EVIDENCE_PROFILE_ID
        or value.get("retained_root") != RETAINED_ROOT.as_posix()
        or value.get("scheduled_slot_count") != 324
        or value.get("terminal_slot_count") != 324
        or value.get("measured_slot_count") != 312
        or value.get("publication")
        != "resumable-block-staging-then-exclusive-atomic-seal"
        or value.get("status") != "sealed"
    ):
        raise AffordablePerformanceEvidenceError("corpus manifest changed")
    return value


def validate_staged_corpus(staging: Path) -> dict[str, object]:
    """Recompute derived bytes before the coordination checkpoint is removed."""

    observations: list[dict[str, object]] = []
    for path in sorted((staging / "raw").rglob("attempt-*.json")):
        value = json.loads(path.read_bytes())
        if canonical_json(value) != path.read_bytes():
            raise AffordablePerformanceEvidenceError("raw record is not canonical")
        observations.append(validate_observation(value))
    summary = process_observations(observations)
    comparison = build_comparison(summary)
    manifest = build_corpus_manifest(observations, summary, comparison)
    expected = {
        staging / "processed" / "summary.json": summary,
        staging / "derived" / "comparison.json": comparison,
        staging / "corpus-manifest.json": manifest,
    }
    for path, value in expected.items():
        if not path.is_file() or path.read_bytes() != canonical_json(value):
            raise AffordablePerformanceEvidenceError("staged derived output changed")
    return manifest


def assert_targets_absent(workspace: Path) -> None:
    if (workspace / RETAINED_ROOT).exists():
        raise AffordablePerformanceEvidenceError(
            "managed-performance-v2 target already exists"
        )
    if (workspace / STAGING_ROOT).exists():
        raise AffordablePerformanceEvidenceError(
            "managed-performance-v2 staging already exists"
        )


__all__ = [
    "APPSS_RESULT_ID",
    "ARMS",
    "CHECKPOINT_ID",
    "EVIDENCE_PROFILE_ID",
    "INSTRUMENTATION_ID",
    "PROCESSOR_ID",
    "PREFLIGHT_ID",
    "RETAINED_ROOT",
    "SCENARIO_MANIFEST_ID",
    "STAGING_ROOT",
    "YI_RESULT_ID",
    "assert_targets_absent",
    "build_comparison",
    "build_corpus_manifest",
    "build_metrics",
    "build_observation",
    "checkpoint_profile",
    "evidence_profile",
    "exclusive_write",
    "instrumentation_profile",
    "process_observations",
    "preflight_profile",
    "processor_profile",
    "scenario_manifest",
    "scheduled_slots",
    "validate_observation",
    "validate_preflight_observations",
    "validate_staged_corpus",
]
