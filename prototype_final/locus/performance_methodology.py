"""Frozen, non-collecting P9.1 managed performance methodology contract."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

METHODOLOGY_ID = "LOCUS-managed-performance-methodology-v1"


class PerformanceMethodologyError(ValueError):
    """The P9.1 methodology is malformed or no longer matches D028."""


def canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode() + b"\n"


def methodology_contract() -> dict[str, Any]:
    arms = [
        {
            "arm_id": "yi-2of3",
            "family": "yi",
            "holders": [1, 2, 3],
            "k": 2,
            "n": 3,
            "policy_id": "LOCUS-canonical-email-set-v1",
            "resolver_profile_id": "LOCUS-no-resolver-v1",
            "suite_id": "LOCUS-TPASS-YI-ZK-RISTRETTO255-v1",
            "topology_id": "LOCUS-paired-suite-deployment-2of3-v1",
        },
        {
            "arm_id": "appss-2of3",
            "family": "appss",
            "holders": [1, 2, 3],
            "k": 2,
            "n": 3,
            "policy_id": "LOCUS-canonical-email-set-v1",
            "resolver_profile_id": "LOCUS-no-resolver-v1",
            "suite_id": "LOCUS-APPSS-2HASHDH-RISTRETTO255-SHA512-GF128-v1",
            "topology_id": "LOCUS-paired-suite-deployment-2of3-v1",
        },
        {
            "arm_id": "yi-3of5",
            "family": "yi",
            "holders": [1, 2, 3, 4, 5],
            "k": 3,
            "n": 5,
            "policy_id": "LOCUS-location-person-set-v1",
            "resolver_profile_id": "LOCUS-deterministic-directory-v1",
            "suite_id": "LOCUS-TPASS-YI-ZK-RISTRETTO255-v1",
            "topology_id": "LOCUS-paired-suite-deployment-3of5-v1",
        },
        {
            "arm_id": "appss-3of5",
            "family": "appss",
            "holders": [1, 2, 3, 4, 5],
            "k": 3,
            "n": 5,
            "policy_id": "LOCUS-location-person-set-v1",
            "resolver_profile_id": "LOCUS-deterministic-directory-v1",
            "suite_id": "LOCUS-APPSS-2HASHDH-RISTRETTO255-SHA512-GF128-v1",
            "topology_id": "LOCUS-paired-suite-deployment-3of5-v1",
        },
    ]
    return {
        "format_id": METHODOLOGY_ID,
        "decision_id": "D028",
        "status": "approved-no-collection",
        "deployment": {
            "active_client_profile_id": "LOCUS-clean-client-isolation-v2",
            "authorization_quorum": 4,
            "authorizers": [1, 2, 3, 4, 5],
            "configuration_id": "LOCUS-integrated-manager-config-v1",
            "deployment_id": "LOCUS-integrated-manager-deployment-v1",
            "host_tier": "same-host-single-operator",
            "provider_id": "LOCUS-storage-provider-s3-compatible-v1",
            "runtime_boundary": "manager-created-client-to-authenticated-services",
        },
        "arms": arms,
        "blocking_and_randomization": {
            "blocks_per_arm": 10,
            "fresh_disposable_project_per_arm_block": True,
            "order_algorithm": "ascending-sha256-of-domain-seed-and-arm-id",
            "order_domain": "LOCUS/managed-performance-order/v1",
            "seeds": list(range(2026081701, 2026081711)),
            "synthetic_fixture_rule": "same-key-and-input-class-within-topology-block",
            "warmup": {
                "count_per_arm_block": 1,
                "measured": False,
                "scenario": "complete-enrollment-export-import-clean-bootstrap-recovery",
            },
        },
        "sample_plan": {
            "central": {
                "samples_per_arm": 30,
                "samples_per_arm_block": 3,
                "scenarios": [
                    "enrollment",
                    "package-export-import",
                    "clean-client-bootstrap",
                    "successful-recovery",
                    "wrong-input-rejection",
                    "one-party-unavailable-recovery",
                ],
            },
            "structural": {
                "samples_per_arm": 10,
                "samples_per_arm_block": 1,
                "scenarios": [
                    "below-threshold-rejection",
                    "party-restart-recovery",
                    "client-restart-reimport-recovery",
                    "preserved-system-restart",
                    "storage-and-role-snapshot",
                ],
            },
            "successor": {
                "directions": [
                    "yi-to-yi",
                    "yi-to-appss",
                    "appss-to-yi",
                    "appss-to-appss",
                ],
                "samples_per_direction_topology": 10,
                "samples_per_direction_topology_block": 1,
                "topologies": ["2of3", "3of5"],
            },
            "concurrency": {
                "batches_per_arm_level": 10,
                "levels": [1, 2, 4],
                "operation": "successful-recovery",
                "serialization_boundary": "one-managed-client",
            },
            "suite_neutral_lifecycle": {
                "samples_per_scenario": 10,
                "scenarios": [
                    "manager-system-startup",
                    "client-create",
                    "client-stop",
                    "client-start",
                    "client-restart",
                    "client-destroy",
                ],
            },
        },
        "failure_schedules": {
            "2of3_one_party_unavailable": {
                "recover_with": [2, 3],
                "stop_party": 1,
            },
            "3of5_one_party_unavailable": {
                "recover_with": [2, 3, 4],
                "stop_party": 1,
            },
            "below_threshold": {
                "expected": "bounded-rejection-only",
                "holder_count": "k-minus-1",
            },
            "party_restart": {
                "await": "authenticated-health",
                "recover_with_subset_containing": 1,
                "restart_party": 1,
            },
        },
        "metrics": {
            "latency_clock": "client-monotonic",
            "end_to_end": True,
            "non_overlapping_phases": [
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
            ],
            "application_body_bytes": "by-role-and-total",
            "persisted_bytes": "aggregate-by-role-and-total",
            "lifecycle_latency": "manager-and-client",
            "ui_latency": "host-loopback-http-round-trip-browser-rendering-excluded",
            "concurrency": ["batch-completion-latency", "operations-per-second"],
        },
        "statistics": {
            "outlier_removal": "none",
            "scheduled_valid_observations": "all-included-including-slow-and-expected-failure",
            "n30": {
                "bootstrap": {
                    "confidence": 0.95,
                    "domain": "LOCUS/managed-performance-bootstrap/v1",
                    "resamples": 10000,
                    "seed": 20260817,
                    "statistic": "median",
                },
                "reported": ["count", "median", "q1", "q3", "p5", "p95", "min", "max"],
            },
            "n10": {
                "reported": ["count", "median", "q1", "q3", "min", "max"],
            },
            "quantile_method": "linear-type-7",
            "means": "secondary-only",
            "infrastructure_invalid": {
                "handling": "retain-invalid-record-and-never-silently-retry-or-overwrite",
                "statistics": "exclude-from-valid-distribution-and-disclose-count",
                "replacement": "only-explicitly-linked-under-the-future-p9.2-schema",
            },
        },
        "retention_gate": {
            "p9_1_collection_authorized": False,
            "p9_2_required_before_collection": True,
            "result_identifiers": [],
            "retained_paths": [],
            "separation": [
                "p8-managed-state-v1",
                "p8-managed-flow-v1",
                "historical-v2",
            ],
        },
        "limitations": [
            "same-host-single-operator-only",
            "local-s3-compatible-provider-only",
            "single-managed-client-concurrency-is-serialization-not-scalability",
            "no-browser-rendering-measurement",
            "no-cpu-energy-wan-real-provider-or-production-capacity-claim",
            "multi-host-wan-and-external-provider-require-separate-p9.4-authorization",
            "no-manuscript-change-authorized",
        ],
    }


def validate_methodology(value: object) -> dict[str, Any]:
    expected = methodology_contract()
    if not isinstance(value, dict) or value != expected:
        raise PerformanceMethodologyError(
            "methodology does not exactly match approved D028"
        )
    return value


def validate_methodology_file(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_bytes()
        value = json.loads(raw)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PerformanceMethodologyError(
            "methodology file is not canonical JSON"
        ) from exc
    validated = validate_methodology(value)
    if raw != canonical_json(validated):
        raise PerformanceMethodologyError("methodology file is not canonical JSON")
    return validated
