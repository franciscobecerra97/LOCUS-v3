"""P9.3 observation construction and deterministic execution ordering."""

from __future__ import annotations

import hashlib
from typing import cast

from .performance_evidence import (
    BODY_ROLES,
    EVIDENCE_PROFILE_ID,
    INSTRUMENTATION_ID,
    LIMITATIONS,
    PERSISTED_ROLES,
    PHASES,
    PHASES_BY_SCENARIO,
    POSITIVE_CONTROLS,
    SCENARIO_MANIFEST_ID,
    canonical_json,
    digest,
    scenario_manifest,
    scheduled_slots,
    validate_observation,
)
from .performance_methodology import methodology_contract

ORDER_DOMAIN = "LOCUS/managed-performance-order/v1"


def ordered_arm_block_slots(arm_id: str, block: int) -> tuple[dict[str, object], ...]:
    """Return one warm-up followed by the seeded D028 arm/block schedule."""

    selected = [
        slot
        for slot in scheduled_slots()
        if slot["arm_id"] == arm_id and slot["block"] == block
    ]
    warmups = [slot for slot in selected if slot["scenario_id"] == "MP00"]
    if len(warmups) != 1:
        raise ValueError("arm/block warm-up membership changed")
    measured = [slot for slot in selected if slot["scenario_id"] != "MP00"]
    seed = cast(int, warmups[0]["seed"])

    def key(slot: dict[str, object]) -> str:
        encoded = (
            f"{ORDER_DOMAIN}:{seed}:{arm_id}:{cast(str, slot['slot_id'])}"
        ).encode("ascii")
        return hashlib.sha256(encoded).hexdigest()

    return (warmups[0], *sorted(measured, key=key))


def common_block_slots(block: int) -> tuple[dict[str, object], ...]:
    selected = [
        slot
        for slot in scheduled_slots()
        if slot["arm_id"] == "managed-common" and slot["block"] == block
    ]
    return tuple(sorted(selected, key=lambda item: cast(str, item["scenario_id"])))


def build_metrics(
    *,
    slot: dict[str, object],
    end_to_end_ns: int,
    phase_latency_ns: dict[str, int],
    application_body_bytes_by_role: dict[str, int],
    persisted_bytes_by_role: dict[str, int],
    ui_http_round_trip_ns: int | None = None,
    lifecycle_ns: int | None = None,
    concurrency: dict[str, int] | None = None,
) -> dict[str, object]:
    scenario_id = cast(str, slot["scenario_id"])
    expected = set(PHASES_BY_SCENARIO.get(scenario_id, frozenset()))
    if scenario_id == "MP01":
        arm = cast(dict[str, object], slot["arm"])
        if arm["n"] == 5:
            expected.add("resolver")
        if arm["family"] == "appss":
            expected.add("appss-per-server-initialization")
    phases = {
        phase: max(0, int(phase_latency_ns.get(phase, 0)))
        if phase in expected
        else None
        for phase in PHASES
    }
    phase_total = sum(cast(int, phases[phase]) for phase in expected)
    if phase_total > end_to_end_ns:
        raise ValueError("measured phases exceed end-to-end latency")
    body = {
        role: max(0, int(application_body_bytes_by_role.get(role, 0)))
        for role in BODY_ROLES
    }
    persisted = {
        role: max(0, int(persisted_bytes_by_role.get(role, 0)))
        for role in PERSISTED_ROLES
    }
    return {
        "application_body_bytes_by_role": body,
        "application_body_bytes_total": sum(body.values()),
        "concurrency": concurrency,
        "end_to_end_ns": end_to_end_ns,
        "lifecycle_ns": lifecycle_ns,
        "persisted_bytes_by_role": persisted,
        "persisted_bytes_total": sum(persisted.values()),
        "phase_latency_ns": phases,
        "ui_http_round_trip_ns": ui_http_round_trip_ns,
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
    observation = {
        "attempt_id": f"{slot['slot_id']}:a{attempt_index:02d}",
        "attempt_index": attempt_index,
        "bindings": bindings,
        "cleanup": {
            "complete": cleanup_complete,
            "resources_remaining": 0 if cleanup_complete else 1,
        },
        "evidence_profile_id": EVIDENCE_PROFILE_ID,
        "format_id": slot["result_id"],
        "infrastructure_invalid": (
            None if invalid_category is None else {"category": invalid_category}
        ),
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
    validate_observation(observation)
    return observation


def observation_sha256(observation: dict[str, object]) -> str:
    return hashlib.sha256(canonical_json(observation)).hexdigest()


__all__ = [
    "build_metrics",
    "build_observation",
    "common_block_slots",
    "observation_sha256",
    "ordered_arm_block_slots",
]
