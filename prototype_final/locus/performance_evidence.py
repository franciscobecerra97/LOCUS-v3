"""Strict P9.2 contracts and P9.3 managed-performance publication helpers."""

from __future__ import annotations

import hashlib
import json
import math
import os
import random
import re
import secrets
import shutil
from collections import defaultdict
from pathlib import Path
from typing import Any, cast

from locus.performance_methodology import methodology_contract

EVIDENCE_PROFILE_ID = "LOCUS-managed-performance-evidence-profile-v1"
INSTRUMENTATION_ID = "LOCUS-managed-performance-instrumentation-v1"
SCENARIO_MANIFEST_ID = "LOCUS-managed-performance-scenario-manifest-v1"
COMMON_RESULT_ID = "LOCUS-managed-performance-result-common-v1"
YI_RESULT_ID = "LOCUS-managed-performance-result-yi-v1"
APPSS_RESULT_ID = "LOCUS-managed-performance-result-appss-v1"
PROCESSOR_ID = "LOCUS-managed-performance-processor-v1"
SUMMARY_ID = "LOCUS-managed-performance-summary-v1"
COMPARISON_ID = "LOCUS-managed-performance-comparison-v1"
CORPUS_MANIFEST_ID = "LOCUS-managed-performance-corpus-manifest-v1"
RESULT_IDS = frozenset({COMMON_RESULT_ID, YI_RESULT_ID, APPSS_RESULT_ID})
RETAINED_ROOT = Path("evidence/retained/managed-performance-v1")

SHA256 = re.compile(r"[0-9a-f]{64}\Z")
SOURCE_COMMIT = re.compile(r"[0-9a-f]{40}\Z")
PSEUDONYM = re.compile(r"(?:host|project|client|packages)-[0-9a-f]{16}\Z")
ATTEMPT_ID = re.compile(r"MP[0-1][0-9]:[a-z0-9:-]+:a[0-9]{2}\Z")
PROHIBITED_KEY = re.compile(
    r"(?:^|_)(?:payload|cue|canonical_cue|password|recovery_secret|private_key|"
    r"protected_key|credential|request_body|response_body|log|trace|packet|pcap|"
    r"host_path|account_id|developer|raw)(?:_|$)",
    re.I,
)

ARMS = {arm["arm_id"]: arm for arm in methodology_contract()["arms"]}
SEEDS = tuple(methodology_contract()["blocking_and_randomization"]["seeds"])
PHASES = (
    "policy",
    "resolver",
    "suite-initialization",
    "appss-per-server-initialization",
    "encryption-and-upload",
    "party-provisioning",
    "descriptor-publication-and-retrieval",
    "authorization",
    "recovery",
    "successor",
)
BODY_ROLES = (
    "browser",
    "manager-ui",
    "manager-controller",
    "managed-client",
    "admission",
    "operator",
    "storage-gateway",
    "provider",
    "resolver",
    "party-1",
    "party-2",
    "party-3",
    "party-4",
    "party-5",
    "docker-engine",
)
PERSISTED_ROLES = (
    "admission",
    "bootstrap",
    "managed-client-template",
    "managed-client-instance",
    "manager-controller",
    "manager-ui",
    "operator",
    "party-1",
    "party-2",
    "party-3",
    "party-4",
    "party-5",
    "resolver",
    "provider",
    "s3-role",
    "storage-gateway",
)
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
    "client-identity-rotation",
    "single-client-serialization",
    "invalid-attempt-linkage",
    "prohibited-output-canary",
    "cleanup",
    "raw-to-processed-hash-closure",
)
INVALID_CATEGORIES = (
    "build-failure",
    "startup-failure",
    "health-check-failure",
    "host-interruption",
    "orchestrator-failure",
    "provider-unavailable-outside-schedule",
    "measurement-integrity-failure",
    "cleanup-failure",
)
LIMITATIONS = (
    "same-host-single-operator-only",
    "local-s3-compatible-provider-only",
    "single-managed-client-serialization-is-not-scalability",
    "browser-rendering-excluded",
    "no-cpu-energy-wan-real-provider-or-production-capacity-claim",
    "implementation-measurement-is-not-cryptographic-proof",
    "no-manuscript-change-authorized",
)

SCENARIOS: dict[str, dict[str, Any]] = {
    "MP00": {"name": "warmup", "category": "warmup", "measured": False},
    "MP01": {"name": "enrollment", "category": "central", "measured": True},
    "MP02": {
        "name": "package-export-import",
        "category": "central",
        "measured": True,
    },
    "MP03": {
        "name": "clean-client-bootstrap",
        "category": "central",
        "measured": True,
    },
    "MP04": {
        "name": "successful-recovery",
        "category": "central",
        "measured": True,
    },
    "MP05": {
        "name": "wrong-input-rejection",
        "category": "central",
        "measured": True,
    },
    "MP06": {
        "name": "one-party-unavailable-recovery",
        "category": "central",
        "measured": True,
    },
    "MP07": {
        "name": "below-threshold-rejection",
        "category": "structural",
        "measured": True,
    },
    "MP08": {
        "name": "party-restart-recovery",
        "category": "structural",
        "measured": True,
    },
    "MP09": {
        "name": "client-restart-reimport-recovery",
        "category": "structural",
        "measured": True,
    },
    "MP10": {
        "name": "preserved-system-restart",
        "category": "structural",
        "measured": True,
    },
    "MP11": {
        "name": "storage-and-role-snapshot",
        "category": "structural",
        "measured": True,
    },
    "MP12": {
        "name": "successor-transition",
        "category": "successor",
        "measured": True,
    },
    "MP13": {
        "name": "concurrent-successful-recovery",
        "category": "concurrency",
        "measured": True,
    },
    "MP14": {
        "name": "manager-system-startup",
        "category": "lifecycle",
        "measured": True,
    },
    "MP15": {"name": "client-create", "category": "lifecycle", "measured": True},
    "MP16": {"name": "client-stop", "category": "lifecycle", "measured": True},
    "MP17": {"name": "client-start", "category": "lifecycle", "measured": True},
    "MP18": {
        "name": "client-restart",
        "category": "lifecycle",
        "measured": True,
    },
    "MP19": {
        "name": "client-destroy",
        "category": "lifecycle",
        "measured": True,
    },
}

PHASES_BY_SCENARIO = {
    "MP01": frozenset(
        {
            "policy",
            "suite-initialization",
            "encryption-and-upload",
            "party-provisioning",
            "descriptor-publication-and-retrieval",
        }
    ),
    "MP03": frozenset({"descriptor-publication-and-retrieval", "authorization"}),
    "MP04": frozenset({"authorization", "recovery"}),
    "MP05": frozenset({"policy", "authorization", "recovery"}),
    "MP06": frozenset({"authorization", "recovery"}),
    "MP07": frozenset({"authorization", "recovery"}),
    "MP08": frozenset({"authorization", "recovery"}),
    "MP09": frozenset({"authorization", "recovery"}),
    "MP10": frozenset({"authorization", "recovery"}),
    "MP12": frozenset({"successor"}),
    "MP13": frozenset({"authorization", "recovery"}),
}


class PerformanceEvidenceError(ValueError):
    """A P9.2 contract, observation, or derived object is malformed."""


def canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode() + b"\n"


def digest(value: object) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def _result_id(arm_id: str) -> str:
    if arm_id == "managed-common":
        return COMMON_RESULT_ID
    return YI_RESULT_ID if ARMS[arm_id]["family"] == "yi" else APPSS_RESULT_ID


def evidence_profile() -> dict[str, object]:
    return {
        "format_id": EVIDENCE_PROFILE_ID,
        "decision_id": "D029",
        "methodology_id": methodology_contract()["format_id"],
        "instrumentation_id": INSTRUMENTATION_ID,
        "scenario_manifest_id": SCENARIO_MANIFEST_ID,
        "processor_id": PROCESSOR_ID,
        "result_ids": [YI_RESULT_ID, APPSS_RESULT_ID, COMMON_RESULT_ID],
        "derived_ids": [SUMMARY_ID, COMPARISON_ID, CORPUS_MANIFEST_ID],
        "scheduled_slot_count": 1220,
        "measured_slot_count": 1180,
        "retained_root": RETAINED_ROOT.as_posix(),
        "publication": "append-only-unsealed-until-closing-manifest",
        "collection_authorized": False,
        "status": "assigned-non-collecting",
    }


def instrumentation_profile() -> dict[str, object]:
    return {
        "format_id": INSTRUMENTATION_ID,
        "clock": "client-monotonic-nanoseconds",
        "end_to_end": "client-observed",
        "phase_rule": "fixed-applicable-non-overlapping-and-bounded-by-end-to-end",
        "phases": list(PHASES),
        "application_body_roles": list(BODY_ROLES),
        "persisted_roles": list(PERSISTED_ROLES),
        "ui_observation": "host-loopback-http-round-trip-browser-rendering-excluded",
        "concurrency_observation": [
            "batch-completion-nanoseconds",
            "operations-per-second-milli",
        ],
        "positive_controls": list(POSITIVE_CONTROLS),
        "prohibited_content": [
            "payloads",
            "cues-or-canonical-cue-bytes",
            "passwords-or-recovery-secrets",
            "protected-or-private-keys",
            "credentials",
            "request-or-response-bodies",
            "logs-traces-or-packet-captures",
            "host-paths-or-stable-machine-account-identifiers",
        ],
        "status": "assigned",
    }


def processor_profile() -> dict[str, object]:
    statistics = methodology_contract()["statistics"]
    return {
        "format_id": PROCESSOR_ID,
        "methodology_id": methodology_contract()["format_id"],
        "quantile_method": statistics["quantile_method"],
        "bootstrap": statistics["n30"]["bootstrap"],
        "n30_reported": statistics["n30"]["reported"],
        "n10_reported": statistics["n10"]["reported"],
        "means": statistics["means"],
        "outlier_removal": statistics["outlier_removal"],
        "invalid_rule": "count-disclose-exclude-and-require-linked-replacement",
        "comparison_rule": "matched-side-by-side-no-pooling-or-hypothesis-test",
        "status": "assigned",
    }


def _slot(
    scenario_id: str,
    arm_id: str,
    block: int,
    repetition: int,
    *,
    target_arm_id: str | None = None,
    direction: str | None = None,
    concurrency_level: int | None = None,
) -> dict[str, object]:
    parts = [scenario_id, arm_id]
    if direction is not None:
        parts.append(direction)
    if concurrency_level is not None:
        parts.append(f"c{concurrency_level}")
    parts.extend((f"b{block:02d}", f"r{repetition:02d}"))
    failure_schedule: object = None
    if scenario_id == "MP06":
        topology = arm_id.split("-", 1)[1]
        failure_schedule = methodology_contract()["failure_schedules"][
            f"{topology}_one_party_unavailable"
        ]
    elif scenario_id == "MP07":
        failure_schedule = methodology_contract()["failure_schedules"][
            "below_threshold"
        ]
    elif scenario_id == "MP08":
        failure_schedule = methodology_contract()["failure_schedules"]["party_restart"]
    return {
        "slot_id": ":".join(parts),
        "scenario_id": scenario_id,
        "category": SCENARIOS[scenario_id]["category"],
        "measured": SCENARIOS[scenario_id]["measured"],
        "arm_id": arm_id,
        "arm": None if arm_id == "managed-common" else ARMS[arm_id],
        "target_arm_id": target_arm_id,
        "target_arm": None if target_arm_id is None else ARMS[target_arm_id],
        "direction": direction,
        "concurrency_level": concurrency_level,
        "failure_schedule": failure_schedule,
        "block": block,
        "seed": SEEDS[block - 1],
        "repetition": repetition,
        "result_id": _result_id(arm_id),
    }


def scheduled_slots() -> tuple[dict[str, object], ...]:
    slots: list[dict[str, object]] = []
    arm_ids = tuple(ARMS)
    for block in range(1, 11):
        for arm_id in arm_ids:
            slots.append(_slot("MP00", arm_id, block, 1))
    for scenario_id in ("MP01", "MP02", "MP03", "MP04", "MP05", "MP06"):
        for block in range(1, 11):
            for arm_id in arm_ids:
                for repetition in range(1, 4):
                    slots.append(_slot(scenario_id, arm_id, block, repetition))
    for scenario_id in ("MP07", "MP08", "MP09", "MP10", "MP11"):
        for block in range(1, 11):
            for arm_id in arm_ids:
                slots.append(_slot(scenario_id, arm_id, block, 1))
    directions = (
        ("yi-to-yi", "yi", "yi"),
        ("yi-to-appss", "yi", "appss"),
        ("appss-to-yi", "appss", "yi"),
        ("appss-to-appss", "appss", "appss"),
    )
    for topology in ("2of3", "3of5"):
        for direction, source, target in directions:
            source_arm = f"{source}-{topology}"
            target_arm = f"{target}-{topology}"
            for block in range(1, 11):
                slots.append(
                    _slot(
                        "MP12",
                        source_arm,
                        block,
                        1,
                        target_arm_id=target_arm,
                        direction=direction,
                    )
                )
    for level in (1, 2, 4):
        for block in range(1, 11):
            for arm_id in arm_ids:
                slots.append(_slot("MP13", arm_id, block, 1, concurrency_level=level))
    for scenario_id in ("MP14", "MP15", "MP16", "MP17", "MP18", "MP19"):
        for block in range(1, 11):
            slots.append(_slot(scenario_id, "managed-common", block, 1))
    if len(slots) != 1220 or len({slot["slot_id"] for slot in slots}) != 1220:
        raise PerformanceEvidenceError("scheduled slot construction changed")
    if sum(bool(slot["measured"]) for slot in slots) != 1180:
        raise PerformanceEvidenceError("measured slot count changed")
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
        "scheduled_slot_count": 1220,
        "measured_slot_count": 1180,
        "slot_digest": digest(list(scheduled_slots())),
        "invalid_categories": list(INVALID_CATEGORIES),
        "attempt_statuses": [
            "warmup-passed",
            "valid-success",
            "valid-expected-rejection",
            "infrastructure-invalid",
        ],
        "status": "assigned",
    }


def _walk_keys(value: object) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if PROHIBITED_KEY.search(str(key)):
                raise PerformanceEvidenceError(f"prohibited retained field: {key}")
            _walk_keys(child)
    elif isinstance(value, list):
        for child in value:
            _walk_keys(child)


def _validate_bindings(value: object) -> dict[str, object]:
    fields = {
        "admission_profile_id",
        "backup_format_id",
        "client_api_id",
        "client_instance_profile_id",
        "collected_at_utc",
        "compose_sha256",
        "configuration_id",
        "controller_api_id",
        "deployment_id",
        "descriptor_id",
        "host_tier",
        "image_id",
        "live_graph_sha256",
        "lockfile_sha256",
        "managed_manifest_sha256",
        "manager_api_id",
        "network_topology_sha256",
        "package_profile_id",
        "provider_id",
        "pseudonymous_client_id",
        "pseudonymous_host_id",
        "pseudonymous_package_set_id",
        "pseudonymous_project_id",
        "resolved_graph_sha256",
        "service_identity_set_sha256",
        "source_commit",
        "source_tree_sha256",
    }
    if not isinstance(value, dict) or set(value) != fields:
        raise PerformanceEvidenceError("binding field set changed")
    fixed = {
        "admission_profile_id": "LOCUS-local-synthetic-admission-v1",
        "backup_format_id": "LOCUS-reference-backup-v6",
        "client_api_id": "LOCUS-client-api-v2",
        "client_instance_profile_id": "LOCUS-managed-client-instance-v1",
        "configuration_id": "LOCUS-integrated-manager-config-v1",
        "controller_api_id": "LOCUS-container-controller-api-v1",
        "deployment_id": "LOCUS-integrated-manager-deployment-v1",
        "descriptor_id": "LOCUS-recovery-descriptor-v1",
        "host_tier": "same-host-single-operator",
        "manager_api_id": "LOCUS-manager-api-v1",
        "package_profile_id": "LOCUS-client-recovery-package-v1",
        "provider_id": "LOCUS-storage-provider-s3-compatible-v1",
    }
    if any(value[key] != expected for key, expected in fixed.items()):
        raise PerformanceEvidenceError("fixed deployment binding changed")
    digest_fields = {
        "compose_sha256",
        "live_graph_sha256",
        "lockfile_sha256",
        "managed_manifest_sha256",
        "network_topology_sha256",
        "resolved_graph_sha256",
        "service_identity_set_sha256",
        "source_tree_sha256",
    }
    if any(
        not isinstance(value[key], str)
        or SHA256.fullmatch(cast(str, value[key])) is None
        for key in digest_fields
    ):
        raise PerformanceEvidenceError("invalid binding digest")
    if (
        not isinstance(value["source_commit"], str)
        or SOURCE_COMMIT.fullmatch(value["source_commit"]) is None
        or not isinstance(value["image_id"], str)
        or re.fullmatch(r"sha256:[0-9a-f]{64}", value["image_id"]) is None
    ):
        raise PerformanceEvidenceError("invalid source or image identity")
    for key in (
        "pseudonymous_client_id",
        "pseudonymous_host_id",
        "pseudonymous_package_set_id",
        "pseudonymous_project_id",
    ):
        if (
            not isinstance(value[key], str)
            or PSEUDONYM.fullmatch(cast(str, value[key])) is None
        ):
            raise PerformanceEvidenceError("invalid pseudonym")
    return value


def _expected_phases(slot: dict[str, object]) -> frozenset[str]:
    phases = PHASES_BY_SCENARIO.get(cast(str, slot["scenario_id"]), frozenset())
    if slot["scenario_id"] == "MP01":
        arm = ARMS[cast(str, slot["arm_id"])]
        if arm["n"] == 5:
            phases = phases | {"resolver"}
        if arm["family"] == "appss":
            phases = phases | {"appss-per-server-initialization"}
    return phases


def _validate_metrics(slot: dict[str, object], value: object) -> dict[str, object]:
    fields = {
        "application_body_bytes_by_role",
        "application_body_bytes_total",
        "concurrency",
        "end_to_end_ns",
        "lifecycle_ns",
        "persisted_bytes_by_role",
        "persisted_bytes_total",
        "phase_latency_ns",
        "ui_http_round_trip_ns",
    }
    if not isinstance(value, dict) or set(value) != fields:
        raise PerformanceEvidenceError("metric field set changed")
    for field in (
        "end_to_end_ns",
        "application_body_bytes_total",
        "persisted_bytes_total",
    ):
        if not isinstance(value[field], int) or cast(int, value[field]) < 0:
            raise PerformanceEvidenceError("invalid aggregate metric")
    phase_values = value["phase_latency_ns"]
    if not isinstance(phase_values, dict) or tuple(phase_values) != PHASES:
        raise PerformanceEvidenceError("phase metric set changed")
    expected_phases = _expected_phases(slot)
    for phase in PHASES:
        phase_value = phase_values[phase]
        if phase in expected_phases:
            if not isinstance(phase_value, int) or phase_value < 0:
                raise PerformanceEvidenceError("applicable phase missing")
        elif phase_value is not None:
            raise PerformanceEvidenceError("inapplicable phase retained")
    if (
        sum(cast(int, phase_values[p]) for p in expected_phases)
        > value["end_to_end_ns"]
    ):
        raise PerformanceEvidenceError("phase latency exceeds end-to-end")
    for field, roles, total_field in (
        ("application_body_bytes_by_role", BODY_ROLES, "application_body_bytes_total"),
        ("persisted_bytes_by_role", PERSISTED_ROLES, "persisted_bytes_total"),
    ):
        role_values = value[field]
        if not isinstance(role_values, dict) or tuple(role_values) != roles:
            raise PerformanceEvidenceError("role metric set changed")
        if any(not isinstance(item, int) or item < 0 for item in role_values.values()):
            raise PerformanceEvidenceError("invalid role byte metric")
        if sum(cast(dict[str, int], role_values).values()) != value[total_field]:
            raise PerformanceEvidenceError("role byte total mismatch")
    scenario_id = slot["scenario_id"]
    ui_required = scenario_id in {
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
    ui_value = value["ui_http_round_trip_ns"]
    if (ui_required and (not isinstance(ui_value, int) or ui_value < 0)) or (
        not ui_required and ui_value is not None
    ):
        raise PerformanceEvidenceError("UI latency applicability changed")
    lifecycle_required = cast(str, slot["category"]) == "lifecycle"
    lifecycle = value["lifecycle_ns"]
    if (lifecycle_required and (not isinstance(lifecycle, int) or lifecycle < 0)) or (
        not lifecycle_required and lifecycle is not None
    ):
        raise PerformanceEvidenceError("lifecycle latency applicability changed")
    concurrency = value["concurrency"]
    if scenario_id == "MP13":
        if not isinstance(concurrency, dict) or set(concurrency) != {
            "batch_completion_ns",
            "completed_operations",
            "level",
            "operations_per_second_milli",
        }:
            raise PerformanceEvidenceError("concurrency metrics missing")
        if concurrency["level"] != slot["concurrency_level"]:
            raise PerformanceEvidenceError("concurrency level changed")
        if concurrency["completed_operations"] != slot["concurrency_level"]:
            raise PerformanceEvidenceError("concurrency completion count changed")
        if any(
            not isinstance(concurrency[key], int) or concurrency[key] <= 0
            for key in ("batch_completion_ns", "operations_per_second_milli")
        ):
            raise PerformanceEvidenceError("invalid concurrency metric")
    elif concurrency is not None:
        raise PerformanceEvidenceError("unexpected concurrency metric")
    return value


def validate_observation(value: object) -> dict[str, object]:
    fields = {
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
    if not isinstance(value, dict) or set(value) != fields:
        raise PerformanceEvidenceError("observation field set changed")
    _walk_keys(value)
    fixed = {
        "evidence_profile_id": EVIDENCE_PROFILE_ID,
        "instrumentation_id": INSTRUMENTATION_ID,
        "methodology_id": methodology_contract()["format_id"],
        "methodology_sha256": digest(methodology_contract()),
        "scenario_manifest_id": SCENARIO_MANIFEST_ID,
        "scenario_manifest_sha256": digest(scenario_manifest()),
    }
    if any(value[key] != expected for key, expected in fixed.items()):
        raise PerformanceEvidenceError("observation contract binding changed")
    slot = value["slot"]
    if not isinstance(slot, dict):
        raise PerformanceEvidenceError("slot is not an object")
    expected = {cast(str, item["slot_id"]): item for item in scheduled_slots()}.get(
        cast(str, slot.get("slot_id"))
    )
    if expected is None or slot != expected:
        raise PerformanceEvidenceError("scheduled slot changed")
    if value["format_id"] != slot["result_id"] or value["format_id"] not in RESULT_IDS:
        raise PerformanceEvidenceError("suite/common result family mismatch")
    attempt_index = value["attempt_index"]
    if not isinstance(attempt_index, int) or not 1 <= attempt_index <= 99:
        raise PerformanceEvidenceError("invalid attempt index")
    expected_attempt_id = f"{slot['slot_id']}:a{attempt_index:02d}"
    if (
        value["attempt_id"] != expected_attempt_id
        or ATTEMPT_ID.fullmatch(expected_attempt_id) is None
    ):
        raise PerformanceEvidenceError("attempt identifier changed")
    replacement = value["replacement_of_sha256"]
    if (attempt_index == 1 and replacement is not None) or (
        attempt_index > 1
        and (not isinstance(replacement, str) or SHA256.fullmatch(replacement) is None)
    ):
        raise PerformanceEvidenceError("invalid replacement linkage")
    status = value["status"]
    allowed_statuses = {
        "warmup-passed",
        "valid-success",
        "valid-expected-rejection",
        "infrastructure-invalid",
    }
    if status not in allowed_statuses:
        raise PerformanceEvidenceError("unknown observation status")
    expected_rejection = slot["scenario_id"] in {"MP05", "MP07"}
    expected_status = (
        "warmup-passed"
        if not slot["measured"]
        else "valid-expected-rejection"
        if expected_rejection
        else "valid-success"
    )
    invalid = value["infrastructure_invalid"]
    if status == "infrastructure-invalid":
        if (
            not isinstance(invalid, dict)
            or set(invalid) != {"category"}
            or invalid["category"] not in INVALID_CATEGORIES
            or value["metrics"] is not None
            or value["outcome"] != "infrastructure-invalid"
        ):
            raise PerformanceEvidenceError("invalid infrastructure record")
    elif (
        status != expected_status
        or invalid is not None
        or value["outcome"] != status
        or (slot["measured"] and value["metrics"] is None)
        or (not slot["measured"] and value["metrics"] is not None)
    ):
        raise PerformanceEvidenceError("valid/warmup outcome changed")
    if value["metrics"] is not None:
        _validate_metrics(slot, value["metrics"])
    _validate_bindings(value["bindings"])
    if value["positive_controls"] != {name: True for name in POSITIVE_CONTROLS}:
        raise PerformanceEvidenceError("positive control set changed")
    if value["output_safety"] != {"prohibited_findings": 0, "scan": "passed"}:
        raise PerformanceEvidenceError("output safety failed")
    cleanup = value["cleanup"]
    if cleanup not in (
        {"complete": True, "resources_remaining": 0},
        {"complete": False, "resources_remaining": 1},
    ):
        raise PerformanceEvidenceError("invalid cleanup status")
    if cleanup["complete"] is False and (
        status != "infrastructure-invalid"
        or cast(dict[str, str], invalid)["category"] != "cleanup-failure"
    ):
        raise PerformanceEvidenceError("cleanup failure not classified")
    if value["limitations"] != list(LIMITATIONS):
        raise PerformanceEvidenceError("limitations changed")
    return value


def _type7(values: list[int], probability: float) -> float:
    ordered = sorted(values)
    if not ordered:
        raise PerformanceEvidenceError("empty statistic")
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return float(ordered[lower])
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def _bootstrap_interval(values: list[int], group_id: str, metric: str) -> list[float]:
    profile = cast(dict[str, Any], processor_profile()["bootstrap"])
    material = f"{profile['domain']}\0{profile['seed']}\0{group_id}\0{metric}".encode()
    rng = random.Random(int.from_bytes(hashlib.sha256(material).digest()[:8], "big"))
    medians = [
        _type7([values[rng.randrange(len(values))] for _ in values], 0.5)
        for _ in range(cast(int, profile["resamples"]))
    ]
    return [
        _type7([int(value * 2) for value in medians], 0.025) / 2,
        _type7([int(value * 2) for value in medians], 0.975) / 2,
    ]


def _statistics(values: list[int], group_id: str, metric: str) -> dict[str, object]:
    count = len(values)
    result: dict[str, object] = {
        "count": count,
        "median": _type7(values, 0.5),
        "q1": _type7(values, 0.25),
        "q3": _type7(values, 0.75),
        "min": min(values),
        "max": max(values),
        "mean_secondary": sum(values) / count,
    }
    if count == 30:
        result.update(
            {
                "p5": _type7(values, 0.05),
                "p95": _type7(values, 0.95),
                "median_bootstrap_95": _bootstrap_interval(values, group_id, metric),
            }
        )
    elif count != 10:
        raise PerformanceEvidenceError("unexpected summary sample count")
    return result


def _metric_series(metrics: dict[str, object]) -> dict[str, int]:
    result = {
        "end_to_end_ns": cast(int, metrics["end_to_end_ns"]),
        "application_body_bytes_total": cast(
            int, metrics["application_body_bytes_total"]
        ),
        "persisted_bytes_total": cast(int, metrics["persisted_bytes_total"]),
    }
    for field in ("ui_http_round_trip_ns", "lifecycle_ns"):
        if metrics[field] is not None:
            result[field] = cast(int, metrics[field])
    for phase, value in cast(
        dict[str, int | None], metrics["phase_latency_ns"]
    ).items():
        if value is not None:
            result[f"phase:{phase}"] = value
    concurrency = metrics["concurrency"]
    if isinstance(concurrency, dict):
        result["batch_completion_ns"] = cast(int, concurrency["batch_completion_ns"])
        result["operations_per_second_milli"] = cast(
            int, concurrency["operations_per_second_milli"]
        )
    return result


def _group_id(slot: dict[str, object]) -> str:
    scenario = cast(str, slot["scenario_id"])
    if slot["category"] == "lifecycle":
        return f"{scenario}:managed-common"
    if scenario == "MP12":
        topology = cast(str, slot["arm_id"]).split("-", 1)[1]
        return f"{scenario}:{topology}:{slot['direction']}"
    if scenario == "MP13":
        return f"{scenario}:{slot['arm_id']}:c{slot['concurrency_level']}"
    return f"{scenario}:{slot['arm_id']}"


def _validate_attempt_chains(
    observations: list[dict[str, object]],
) -> tuple[list[dict[str, object]], int]:
    by_slot: dict[str, list[dict[str, object]]] = defaultdict(list)
    for observation in observations:
        validate_observation(observation)
        by_slot[
            cast(str, cast(dict[str, object], observation["slot"])["slot_id"])
        ].append(observation)
    expected_ids = {cast(str, slot["slot_id"]) for slot in scheduled_slots()}
    if set(by_slot) != expected_ids:
        raise PerformanceEvidenceError("scheduled corpus is incomplete or has extras")
    terminal: list[dict[str, object]] = []
    invalid_count = 0
    for slot_id in sorted(by_slot):
        attempts = sorted(
            by_slot[slot_id], key=lambda item: cast(int, item["attempt_index"])
        )
        if [item["attempt_index"] for item in attempts] != list(
            range(1, len(attempts) + 1)
        ):
            raise PerformanceEvidenceError("attempt indexes are not contiguous")
        for index, attempt in enumerate(attempts):
            if index:
                if attempt["replacement_of_sha256"] != digest(attempts[index - 1]):
                    raise PerformanceEvidenceError(
                        "replacement does not link prior attempt"
                    )
                if attempts[index - 1]["status"] != "infrastructure-invalid":
                    raise PerformanceEvidenceError("valid observation was retried")
            if attempt["status"] == "infrastructure-invalid":
                invalid_count += 1
        if attempts[-1]["status"] == "infrastructure-invalid":
            raise PerformanceEvidenceError(
                "slot lacks an accepted terminal observation"
            )
        terminal.append(attempts[-1])
    return terminal, invalid_count


def process_observations(observations: list[dict[str, object]]) -> dict[str, object]:
    terminal, invalid_count = _validate_attempt_chains(observations)
    stable_binding_fields = {
        "admission_profile_id",
        "backup_format_id",
        "client_api_id",
        "client_instance_profile_id",
        "compose_sha256",
        "configuration_id",
        "controller_api_id",
        "deployment_id",
        "descriptor_id",
        "host_tier",
        "image_id",
        "live_graph_sha256",
        "lockfile_sha256",
        "managed_manifest_sha256",
        "manager_api_id",
        "network_topology_sha256",
        "package_profile_id",
        "provider_id",
        "resolved_graph_sha256",
        "service_identity_set_sha256",
        "source_commit",
        "source_tree_sha256",
    }
    first_bindings = cast(dict[str, object], observations[0]["bindings"])
    for observation_item in observations[1:]:
        current = cast(dict[str, object], observation_item["bindings"])
        if any(
            current[field] != first_bindings[field] for field in stable_binding_fields
        ):
            raise PerformanceEvidenceError("corpus provenance is not matched")
    groups: dict[str, list[dict[str, object]]] = defaultdict(list)
    warmup_ids = {
        (
            cast(dict[str, object], item["slot"])["arm_id"],
            cast(dict[str, object], item["slot"])["block"],
        )
        for item in terminal
        if cast(dict[str, object], item["slot"])["scenario_id"] == "MP00"
    }
    if len(warmup_ids) != 40:
        raise PerformanceEvidenceError("warm-up coverage changed")
    positions = {
        cast(str, item["attempt_id"]): index for index, item in enumerate(observations)
    }
    warmup_positions = {
        (
            cast(dict[str, object], item["slot"])["arm_id"],
            cast(dict[str, object], item["slot"])["block"],
        ): positions[cast(str, item["attempt_id"])]
        for item in terminal
        if cast(dict[str, object], item["slot"])["scenario_id"] == "MP00"
    }
    for observation in terminal:
        slot = cast(dict[str, object], observation["slot"])
        if not slot["measured"]:
            continue
        warmup_key = (slot["arm_id"], slot["block"])
        if slot["arm_id"] != "managed-common" and (
            warmup_key not in warmup_ids
            or warmup_positions[warmup_key]
            >= positions[cast(str, observation["attempt_id"])]
        ):
            raise PerformanceEvidenceError("measurement lacks prior warm-up binding")
        groups[_group_id(slot)].append(observation)
    summaries: list[dict[str, object]] = []
    for group_id in sorted(groups):
        members = groups[group_id]
        series: dict[str, list[int]] = defaultdict(list)
        for member in members:
            for metric, value in _metric_series(
                cast(dict[str, object], member["metrics"])
            ).items():
                series[metric].append(value)
        if any(len(values) != len(members) for values in series.values()):
            raise PerformanceEvidenceError("metric applicability changed inside group")
        first_slot = cast(dict[str, object], members[0]["slot"])
        arm_id = cast(str, first_slot["arm_id"])
        family = (
            "common"
            if arm_id == "managed-common"
            else cast(str, ARMS[arm_id]["family"])
        )
        summaries.append(
            {
                "group_id": group_id,
                "scenario_id": first_slot["scenario_id"],
                "family": family,
                "arm_id": arm_id,
                "target_arm_id": first_slot["target_arm_id"],
                "direction": first_slot["direction"],
                "concurrency_level": first_slot["concurrency_level"],
                "sample_count": len(members),
                "metrics": {
                    metric: _statistics(values, group_id, metric)
                    for metric, values in sorted(series.items())
                },
                "observation_set_sha256": digest(
                    sorted(digest(member) for member in members)
                ),
            }
        )
    if len(summaries) != 70:
        raise PerformanceEvidenceError("summary group count changed")
    summary = {
        "format_id": SUMMARY_ID,
        "evidence_profile_id": EVIDENCE_PROFILE_ID,
        "methodology_id": methodology_contract()["format_id"],
        "processor_id": PROCESSOR_ID,
        "scenario_manifest_sha256": digest(scenario_manifest()),
        "scheduled_slot_count": 1220,
        "measured_slot_count": 1180,
        "raw_attempt_count": len(observations),
        "infrastructure_invalid_count": invalid_count,
        "outlier_removal": "none",
        "groups": summaries,
        "binding_set_sha256": digest(
            sorted(digest(item["bindings"]) for item in observations)
        ),
        "limitations": list(LIMITATIONS),
        "status": "processed",
    }
    validate_summary(summary)
    return summary


def validate_summary(value: object) -> dict[str, object]:
    fields = {
        "binding_set_sha256",
        "evidence_profile_id",
        "format_id",
        "groups",
        "infrastructure_invalid_count",
        "limitations",
        "measured_slot_count",
        "methodology_id",
        "outlier_removal",
        "processor_id",
        "raw_attempt_count",
        "scenario_manifest_sha256",
        "scheduled_slot_count",
        "status",
    }
    if not isinstance(value, dict) or set(value) != fields:
        raise PerformanceEvidenceError("summary field set changed")
    if (
        value["format_id"] != SUMMARY_ID
        or value["evidence_profile_id"] != EVIDENCE_PROFILE_ID
        or value["processor_id"] != PROCESSOR_ID
        or value["methodology_id"] != methodology_contract()["format_id"]
        or value["scenario_manifest_sha256"] != digest(scenario_manifest())
        or value["scheduled_slot_count"] != 1220
        or value["measured_slot_count"] != 1180
        or value["outlier_removal"] != "none"
        or value["status"] != "processed"
        or value["limitations"] != list(LIMITATIONS)
        or not isinstance(value["groups"], list)
        or len(value["groups"]) != 70
        or not isinstance(value["binding_set_sha256"], str)
        or SHA256.fullmatch(value["binding_set_sha256"]) is None
    ):
        raise PerformanceEvidenceError("summary contract changed")
    return value


def build_comparison(summary: dict[str, object]) -> dict[str, object]:
    validate_summary(summary)
    groups = {
        cast(str, group["group_id"]): group
        for group in cast(list[dict[str, object]], summary["groups"])
    }
    pairs: list[dict[str, object]] = []
    for scenario_id in tuple(f"MP{number:02d}" for number in range(1, 12)) + ("MP13",):
        for topology in ("2of3", "3of5"):
            levels = (1, 2, 4) if scenario_id == "MP13" else (None,)
            for level in levels:
                suffix = f":c{level}" if level is not None else ""
                yi_id = f"{scenario_id}:yi-{topology}{suffix}"
                appss_id = f"{scenario_id}:appss-{topology}{suffix}"
                yi_group, appss_group = groups[yi_id], groups[appss_id]
                yi_metrics = cast(dict[str, object], yi_group["metrics"])
                appss_metrics = cast(dict[str, object], appss_group["metrics"])
                shared_metrics = set(yi_metrics) & set(appss_metrics)
                unmatched_metrics = set(yi_metrics) ^ set(appss_metrics)
                if (
                    unmatched_metrics - {"phase:appss-per-server-initialization"}
                    or not {
                        "end_to_end_ns",
                        "application_body_bytes_total",
                        "persisted_bytes_total",
                    }
                    <= shared_metrics
                ):
                    raise PerformanceEvidenceError("comparison metric sets differ")
                pairs.append(
                    {
                        "comparison_id": f"{scenario_id}:{topology}{suffix}",
                        "scenario_id": scenario_id,
                        "topology": topology,
                        "concurrency_level": level,
                        "yi_group_id": yi_id,
                        "yi_group_sha256": digest(yi_group),
                        "appss_group_id": appss_id,
                        "appss_group_sha256": digest(appss_group),
                        "side_by_side_medians": {
                            metric: {
                                "yi": cast(dict[str, object], yi_metrics[metric])[
                                    "median"
                                ],
                                "appss": cast(dict[str, object], appss_metrics[metric])[
                                    "median"
                                ],
                            }
                            for metric in sorted(shared_metrics)
                        },
                    }
                )
    comparison = {
        "format_id": COMPARISON_ID,
        "processor_id": PROCESSOR_ID,
        "summary_id": SUMMARY_ID,
        "summary_sha256": digest(summary),
        "comparison_count": 28,
        "pairs": pairs,
        "pooling": False,
        "hypothesis_test": False,
        "interpretation": "matched-side-by-side-descriptive-only",
        "limitations": list(LIMITATIONS),
        "status": "derived",
    }
    validate_comparison(comparison)
    return comparison


def validate_comparison(value: object) -> dict[str, object]:
    fields = {
        "comparison_count",
        "format_id",
        "hypothesis_test",
        "interpretation",
        "limitations",
        "pairs",
        "pooling",
        "processor_id",
        "status",
        "summary_id",
        "summary_sha256",
    }
    if not isinstance(value, dict) or set(value) != fields:
        raise PerformanceEvidenceError("comparison field set changed")
    if (
        value["format_id"] != COMPARISON_ID
        or value["processor_id"] != PROCESSOR_ID
        or value["summary_id"] != SUMMARY_ID
        or value["comparison_count"] != 28
        or not isinstance(value["pairs"], list)
        or len(value["pairs"]) != 28
        or value["pooling"] is not False
        or value["hypothesis_test"] is not False
        or value["interpretation"] != "matched-side-by-side-descriptive-only"
        or value["limitations"] != list(LIMITATIONS)
        or value["status"] != "derived"
        or not isinstance(value["summary_sha256"], str)
        or SHA256.fullmatch(value["summary_sha256"]) is None
    ):
        raise PerformanceEvidenceError("comparison contract changed")
    return value


def build_corpus_manifest(
    observations: list[dict[str, object]],
    summary: dict[str, object],
    comparison: dict[str, object],
) -> dict[str, object]:
    terminal, invalid_count = _validate_attempt_chains(observations)
    validate_summary(summary)
    validate_comparison(comparison)
    if comparison["summary_sha256"] != digest(summary):
        raise PerformanceEvidenceError("comparison does not bind summary")
    paths = [
        f"raw/{cast(str, cast(dict[str, object], item['slot'])['slot_id']).replace(':', '/')}/attempt-{cast(int, item['attempt_index']):02d}.json"
        for item in observations
    ]
    if len(set(paths)) != len(paths):
        raise PerformanceEvidenceError("raw attempt path collision")
    manifest = {
        "format_id": CORPUS_MANIFEST_ID,
        "evidence_profile_id": EVIDENCE_PROFILE_ID,
        "retained_root": RETAINED_ROOT.as_posix(),
        "scheduled_slot_count": 1220,
        "terminal_slot_count": len(terminal),
        "measured_slot_count": 1180,
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
        "publication": "append-only-exclusive-create",
        "positive_controls": {name: True for name in POSITIVE_CONTROLS},
        "status": "sealed",
    }
    validate_corpus_manifest(manifest)
    return manifest


def validate_corpus_manifest(value: object) -> dict[str, object]:
    fields = {
        "comparison_path",
        "comparison_sha256",
        "evidence_profile_id",
        "format_id",
        "infrastructure_invalid_count",
        "measured_slot_count",
        "positive_controls",
        "publication",
        "raw_attempt_count",
        "raw_records_sha256",
        "retained_root",
        "scheduled_slot_count",
        "status",
        "summary_path",
        "summary_sha256",
        "terminal_slot_count",
    }
    if not isinstance(value, dict) or set(value) != fields:
        raise PerformanceEvidenceError("corpus manifest field set changed")
    if (
        value["format_id"] != CORPUS_MANIFEST_ID
        or value["evidence_profile_id"] != EVIDENCE_PROFILE_ID
        or value["retained_root"] != RETAINED_ROOT.as_posix()
        or value["scheduled_slot_count"] != 1220
        or value["terminal_slot_count"] != 1220
        or value["measured_slot_count"] != 1180
        or value["summary_path"] != "processed/summary.json"
        or value["comparison_path"] != "derived/comparison.json"
        or value["publication"] != "append-only-exclusive-create"
        or value["positive_controls"] != {name: True for name in POSITIVE_CONTROLS}
        or value["status"] != "sealed"
    ):
        raise PerformanceEvidenceError("corpus manifest contract changed")
    for field in ("raw_records_sha256", "summary_sha256", "comparison_sha256"):
        if (
            not isinstance(value[field], str)
            or SHA256.fullmatch(cast(str, value[field])) is None
        ):
            raise PerformanceEvidenceError("invalid corpus digest")
    return value


def assert_retained_target_absent(workspace: Path) -> None:
    target = workspace / RETAINED_ROOT
    if target.exists():
        raise PerformanceEvidenceError("managed-performance-v1 target already exists")


def _raw_relative_path(observation: dict[str, object]) -> str:
    slot = cast(dict[str, object], observation["slot"])
    return (
        "raw/"
        + cast(str, slot["slot_id"]).replace(":", "/")
        + f"/attempt-{cast(int, observation['attempt_index']):02d}.json"
    )


def _exclusive_write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = canonical_json(value)
    with path.open("xb") as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())


def publish_corpus(
    *, workspace: Path, observations: list[dict[str, object]]
) -> dict[str, object]:
    """Atomically publish the one D029 corpus from a complete validated run."""

    assert_retained_target_absent(workspace)
    retained_parent = workspace / RETAINED_ROOT.parent
    retained_parent.mkdir(parents=True, exist_ok=True)
    target = workspace / RETAINED_ROOT
    staging = retained_parent / f".{RETAINED_ROOT.name}.staging-{secrets.token_hex(8)}"
    try:
        summary = process_observations(observations)
        comparison = build_comparison(summary)
        manifest = build_corpus_manifest(observations, summary, comparison)
        for observation in observations:
            validate_observation(observation)
            _exclusive_write(staging / _raw_relative_path(observation), observation)
        _exclusive_write(staging / "processed" / "summary.json", summary)
        _exclusive_write(staging / "derived" / "comparison.json", comparison)
        _exclusive_write(staging / "corpus-manifest.json", manifest)
        validate_corpus_path(staging)
        os.rename(staging, target)
        return manifest
    except BaseException as error:
        resolved = staging.resolve()
        if resolved.parent != retained_parent.resolve() or not resolved.name.startswith(
            f".{RETAINED_ROOT.name}.staging-"
        ):
            raise PerformanceEvidenceError("unsafe performance staging path") from error
        shutil.rmtree(resolved, ignore_errors=True)
        raise


def validate_corpus_path(target: Path) -> dict[str, object]:
    """Validate every raw and derived byte in a sealed retained corpus."""

    manifest_path = target / "corpus-manifest.json"
    summary_path = target / "processed" / "summary.json"
    comparison_path = target / "derived" / "comparison.json"
    if not all(
        path.is_file() for path in (manifest_path, summary_path, comparison_path)
    ):
        raise PerformanceEvidenceError("retained performance corpus is unsealed")
    try:
        manifest = json.loads(manifest_path.read_bytes())
        summary = json.loads(summary_path.read_bytes())
        comparison = json.loads(comparison_path.read_bytes())
        raw_paths = sorted((target / "raw").rglob("attempt-*.json"))
        observations = [json.loads(path.read_bytes()) for path in raw_paths]
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PerformanceEvidenceError(
            "retained performance corpus is malformed"
        ) from exc
    if any(
        canonical_json(value) != path.read_bytes()
        for value, path in zip(observations, raw_paths, strict=True)
    ):
        raise PerformanceEvidenceError("raw performance record is not canonical")
    if (
        canonical_json(summary) != summary_path.read_bytes()
        or canonical_json(comparison) != comparison_path.read_bytes()
    ):
        raise PerformanceEvidenceError("derived performance output is not canonical")
    expected_summary = process_observations(observations)
    expected_comparison = build_comparison(expected_summary)
    expected_manifest = build_corpus_manifest(
        observations, expected_summary, expected_comparison
    )
    if summary != expected_summary or comparison != expected_comparison:
        raise PerformanceEvidenceError("derived performance output changed")
    if (
        manifest != expected_manifest
        or canonical_json(manifest) != manifest_path.read_bytes()
    ):
        raise PerformanceEvidenceError("performance corpus manifest changed")
    return manifest
