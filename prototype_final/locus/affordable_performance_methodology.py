"""Owner-approved affordable P9.3 managed-performance methodology."""

from __future__ import annotations

from typing import Any

METHODOLOGY_ID = "LOCUS-managed-performance-methodology-v2"

_ARMS = [
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

_CONTRACT: dict[str, Any] = {
    "format_id": METHODOLOGY_ID,
    "decision_id": "D030",
    "status": "approved-preparation-only",
    "deployment": {
        "deployment_id": "LOCUS-integrated-manager-deployment-v1",
        "configuration_id": "LOCUS-integrated-manager-config-v1",
        "runtime_boundary": "manager-created-client-to-authenticated-services",
        "provider_id": "LOCUS-storage-provider-s3-compatible-v1",
        "host_tier": "same-host-single-operator",
        "authorizers": [1, 2, 3, 4, 5],
        "authorization_quorum": 4,
        "active_client_profile_id": "LOCUS-clean-client-isolation-v2",
    },
    "arms": _ARMS,
    "blocking_and_randomization": {
        "blocks_per_arm": 3,
        "fresh_disposable_project_per_arm_block": True,
        "shared_image_build_per_run": True,
        "seeds": [2026082101, 2026082102, 2026082103],
        "order_algorithm": "ascending-sha256-of-domain-seed-and-arm-id",
        "order_domain": "LOCUS/managed-performance-order/v2",
        "warmup": {
            "count_per_arm_block": 1,
            "measured": False,
            "scenario": "complete-enrollment-export-import-clean-bootstrap-recovery",
        },
    },
    "sample_plan": {
        "central": {
            "samples_per_arm": 15,
            "samples_per_arm_block": 5,
            "scenarios": [
                "enrollment",
                "package-transfer-and-clean-bootstrap",
                "successful-recovery",
                "wrong-input-rejection",
                "one-party-unavailable-recovery",
            ],
        },
        "structural": {
            "samples_per_arm": 3,
            "samples_per_arm_block": 1,
            "scenarios": ["storage-and-role-snapshot"],
        },
        "scheduled_slot_count": 324,
        "measured_slot_count": 312,
        "fresh_project_count": 12,
    },
    "failure_schedules": {
        "2of3_one_party_unavailable": {"stop_party": 1, "recover_with": [2, 3]},
        "3of5_one_party_unavailable": {
            "stop_party": 1,
            "recover_with": [2, 3, 4],
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
        ],
        "application_body_bytes": "by-role-and-total",
        "persisted_bytes": "aggregate-by-role-and-total",
    },
    "statistics": {
        "reported": ["count", "median", "q1", "q3", "min", "max", "mean"],
        "quantile_method": "linear-type-7",
        "means": "secondary-only",
        "outlier_removal": "none",
        "confidence_intervals": "none",
        "hypothesis_tests": "none",
        "infrastructure_invalid": {
            "handling": "retain-invalid-record-and-never-silently-overwrite",
            "replacement": "linked-retry-within-the-same-arm-block",
            "statistics": "exclude-from-valid-distribution-and-disclose-count",
        },
    },
    "resumption": {
        "unit": "completed-arm-block",
        "raw_records": "exclusive-create-after-completed-arm-block",
        "checkpoint": "coordination-only-not-retained-evidence",
        "required_equal_bindings": [
            "source_commit",
            "source_tree_sha256",
            "methodology_sha256",
            "scenario_manifest_sha256",
            "image_id",
            "resolved_graph_sha256",
            "host_tier",
            "pseudonymous_host_id",
        ],
        "interrupted_active_block": "classify-host-interruption-clean-and-retry",
        "finalization": "only-after-complete-validation-and-hash-closure",
    },
    "retention_gate": {
        "collection_authorized": False,
        "tests_required_before_collection": True,
        "exploratory_run_required_before_retention": True,
        "result_identifiers": [],
        "retained_paths": [],
        "separation": [
            "managed-performance-v1",
            "p8-managed-state-v1",
            "p8-managed-flow-v1",
            "historical-v2",
        ],
    },
    "limitations": [
        "same-host-single-operator-only",
        "local-s3-compatible-provider-only",
        "descriptive-central-operation-cost-only",
        "no-scalability-throughput-or-concurrency-claim",
        "no-lifecycle-restart-successor-or-below-threshold-latency-distribution",
        "no-cpu-energy-wan-real-provider-or-production-capacity-claim",
        "no-suite-advantage-or-hypothesis-test",
        "functional-resilience-remains-supported-by-p7-p8-controls-not-this-corpus",
        "no-manuscript-change-authorized",
    ],
}


def methodology_contract() -> dict[str, Any]:
    """Return a detached copy of the immutable D030 contract."""

    import copy

    return copy.deepcopy(_CONTRACT)


def validate_methodology(value: object) -> dict[str, Any]:
    """Reject any semantic drift from the owner-approved contract."""

    if value != _CONTRACT:
        raise ValueError("affordable managed-performance methodology changed")
    return methodology_contract()


__all__ = ["METHODOLOGY_ID", "methodology_contract", "validate_methodology"]
