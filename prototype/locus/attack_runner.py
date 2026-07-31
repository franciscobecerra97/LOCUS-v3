"""Versioned, redacted attack reports over deployed public service boundaries."""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping
from pathlib import Path
from types import MappingProxyType
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from .cloud_snapshot import (
    CLOUD_SNAPSHOT_INPUT_VERSION,
    CLOUD_SNAPSHOT_SCENARIO,
    SYNTHETIC_CANDIDATES,
    CloudSnapshotError,
    audit_cloud_snapshot,
)
from .combined_snapshot import (
    COMBINED_SNAPSHOT_INPUT_VERSION,
    COMBINED_SNAPSHOT_SCENARIO,
    CombinedSnapshotError,
    audit_combined_snapshot,
)
from .combined_snapshot import (
    SYNTHETIC_CANDIDATES as COMBINED_SNAPSHOT_CANDIDATES,
)
from .deployment import (
    DeploymentError,
    deployment_attempt_status,
    run_client,
    run_cross_epoch_lifecycle,
)
from .party_snapshot import (
    PARTY_SNAPSHOT_INPUT_VERSION,
    PARTY_SNAPSHOT_SCENARIO,
    PartySnapshotError,
    audit_party_snapshot,
)
from .party_snapshot import (
    SYNTHETIC_CANDIDATES as PARTY_SNAPSHOT_CANDIDATES,
)
from .redaction import validate_public_output

ATTACK_REPORT_VERSION = "LOCUS-attack-report-v1"

SCENARIO_REGISTRY: Mapping[str, Mapping[str, object]] = MappingProxyType(
    {
        CLOUD_SNAPSHOT_SCENARIO: MappingProxyType(
            {
                "expected_result": MappingProxyType(
                    {
                        "candidate_count": len(SYNTHETIC_CANDIDATES),
                        "candidate_signals": 0,
                        "excluded_path_accesses": 0,
                        "network_attempts": 0,
                        "prohibited_material": "absent",
                        "snapshot_validation": "passed",
                    }
                ),
                "interpretation": (
                    "The exact current S3-compatible cloud snapshot and the "
                    "registered offline candidate path exposed no local "
                    "candidate-correctness predicate or prohibited role "
                    "material. This is implementation evidence for this "
                    "bounded surface, not a cryptographic proof, real-provider "
                    "forensic result, or statement about cue strength."
                ),
                "parameters": MappingProxyType(
                    {
                        "candidate_count": len(SYNTHETIC_CANDIDATES),
                        "execution_boundary": "network-none-read-only-snapshot-v1",
                        "snapshot_version": CLOUD_SNAPSHOT_INPUT_VERSION,
                    }
                ),
                "prerequisites": (
                    "one canonical synthetic backup published through the S3-compatible adapter",
                    "exact two-file cloud-only snapshot with no client or party state",
                    "network-disabled runner with a read-only snapshot mount",
                ),
                "procedure": (
                    "validate the canonical object, manifest, locator, digest, size, and TPASS public metadata",
                    "reject excluded files, prohibited fields, malformed input, and object substitution",
                    "exercise two fixed synthetic attacker candidates under filesystem and network guards",
                    "emit only aggregate boundary counts through the versioned attack-report contract",
                ),
            }
        ),
        COMBINED_SNAPSHOT_SCENARIO: MappingProxyType(
            {
                "expected_result": MappingProxyType(
                    {
                        "candidate_count": len(COMBINED_SNAPSHOT_CANDIDATES),
                        "candidate_signals": 0,
                        "cloud_snapshot_validation": "passed",
                        "combined_binding": "matched",
                        "compromised_parties": 1,
                        "excluded_path_accesses": 0,
                        "network_attempts": 0,
                        "party_snapshot_validation": "passed",
                        "party_snapshots": 1,
                        "secret_output_exposures": 0,
                        "threshold": 2,
                    }
                ),
                "interpretation": (
                    "The exact manifest-bound union of the current synthetic "
                    "cloud snapshot and one matching stopped party snapshot "
                    "exposed no local candidate-correctness predicate in the "
                    "registered offline path. Secret-bearing party state and "
                    "ciphertext remained confined to the read-only input. This "
                    "is bounded implementation evidence, not a compromise "
                    "mechanism, cryptographic proof, live-role result, or "
                    "statement about cue strength."
                ),
                "parameters": MappingProxyType(
                    {
                        "candidate_count": len(COMBINED_SNAPSHOT_CANDIDATES),
                        "compromised_parties": 1,
                        "execution_boundary": (
                            "network-none-read-only-cloud-plus-one-party-snapshot-v1"
                        ),
                        "snapshot_version": COMBINED_SNAPSHOT_INPUT_VERSION,
                        "threshold": 2,
                    }
                ),
                "prerequisites": (
                    "one canonical synthetic cloud snapshot after a completed recovery",
                    "one matching stopped post-recovery synthetic party1 snapshot",
                    "network-disabled credential-free runner with only the manifest-bound union mounted read-only",
                ),
                "procedure": (
                    "validate both frozen sub-snapshots and their top-level canonical manifest",
                    "require matching backup identifier, epoch, digest, and TPASS public parameters across roles",
                    "exercise two fixed synthetic attacker candidates over both loaded surfaces under file and network guards",
                    "emit only aggregate boundary counts through the versioned attack-report contract",
                ),
            }
        ),
        PARTY_SNAPSHOT_SCENARIO: MappingProxyType(
            {
                "expected_result": MappingProxyType(
                    {
                        "candidate_count": len(PARTY_SNAPSHOT_CANDIDATES),
                        "candidate_signals": 0,
                        "cloud_material": "absent",
                        "compromised_parties": 1,
                        "excluded_path_accesses": 0,
                        "network_attempts": 0,
                        "secret_output_exposures": 0,
                        "snapshot_validation": "passed",
                        "threshold": 2,
                    }
                ),
                "interpretation": (
                    "The complete stopped persistent snapshot of one synthetic "
                    "party in the deployed two-of-three TPASS profile and the "
                    "registered offline candidate path exposed no local "
                    "candidate-correctness predicate. Secret-bearing party state "
                    "remained confined to the read-only input. This is bounded "
                    "implementation evidence, not a compromise mechanism, "
                    "cryptographic proof, live-party result, or statement about "
                    "cue strength."
                ),
                "parameters": MappingProxyType(
                    {
                        "candidate_count": len(PARTY_SNAPSHOT_CANDIDATES),
                        "compromised_parties": 1,
                        "execution_boundary": (
                            "network-none-read-only-one-party-snapshot-v1"
                        ),
                        "snapshot_version": PARTY_SNAPSHOT_INPUT_VERSION,
                        "threshold": 2,
                    }
                ),
                "prerequisites": (
                    "one stopped post-recovery synthetic party1 persistent volume",
                    "exact one-party snapshot with no cloud, client, resolver, or other-party state",
                    "network-disabled credential-free runner with a read-only snapshot mount",
                ),
                "procedure": (
                    "validate the canonical manifest and every persistent file in the stopped party volume",
                    "validate the one-party authorizer, TLS, native TPASS, and SQLite checkpoint bindings",
                    "exercise two fixed synthetic attacker candidates under filesystem and network guards",
                    "emit only aggregate boundary counts through the versioned attack-report contract",
                ),
            }
        ),
        "resolver-unavailable-v1": MappingProxyType(
            {
                "expected_result": MappingProxyType(
                    {
                        "attempt_delta": 0,
                        "failure_category": "resolver-unavailable",
                    }
                ),
                "interpretation": (
                    "A resolver availability failure stops before attempt "
                    "authorization; this is failure-boundary evidence, not an "
                    "offline-oracle result."
                ),
                "parameters": MappingProxyType(
                    {"resolver_path": "/v1/attack-unavailable"}
                ),
                "prerequisites": (
                    "provisioned synthetic deployment",
                    "healthy cloud and recovery parties",
                    "deterministic resolver service",
                ),
                "procedure": (
                    "read the redacted attempt count through party status interfaces",
                    "request recovery through a nonexistent resolver resource",
                    "read the redacted attempt count again",
                    "compare the observed failure category and attempt delta",
                ),
            }
        ),
        "cross-epoch-runtime-mix-v1": MappingProxyType(
            {
                "expected_result": MappingProxyType(
                    {
                        "cross_epoch_mix": "rejected",
                        "old_epoch_refusal": "rejected",
                        "old_epoch_status": "retired",
                        "party_restart": "verified",
                        "partial_new_active": 3,
                        "partial_old_active": 2,
                        "successor_epoch_status": "active",
                        "successor_recovery": "verified",
                    }
                ),
                "interpretation": (
                    "After the correct successor package is prepared, its binding "
                    "rejects substitution with predecessor-context party state. "
                    "A 3/2 partial activation exposes neither epoch quorum; full "
                    "activation retires the predecessor, reconstructs one party "
                    "after restart, and recovers through the successor. This is "
                    "one same-host execution, not first-delivery validation, "
                    "rollback resistance, or a global attempt-bound proof."
                ),
                "parameters": MappingProxyType(
                    {
                        "activation_order": [1, 2, 3, 4, 5],
                        "predecessor_epoch": 1,
                        "successor_epoch": 2,
                    }
                ),
                "prerequisites": (
                    "provisioned synthetic deployment",
                    "healthy cloud and five authenticated recovery parties",
                    "same authorizer membership across two epochs",
                ),
                "procedure": (
                    "publish an immutable successor backup and obtain old-quorum approvals",
                    "prepare each exact party runtime package and retry party one with predecessor-context party state",
                    "activate parties one through three and count active old/new parties",
                    "activate the remaining parties and restart activated party one",
                    "probe a retired-epoch vote after party one becomes healthy",
                    "recover through the successor and verify both final epoch states",
                ),
            }
        ),
    }
)


def _registry_value(scenario: Mapping[str, object], field: str) -> object:
    value = scenario[field]
    if isinstance(value, Mapping):
        return dict(value)
    if isinstance(value, tuple):
        return list(value)
    return value


class AttackReportError(Exception):
    """An attack scenario or report is invalid or misleading."""


def _exact_dict(value: object, fields: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        raise AttackReportError(f"invalid {label}")
    return value


def validate_attack_report(value: object) -> dict[str, object]:
    """Validate one exact attack report without secret-bearing fields."""

    report = _exact_dict(
        value,
        {
            "expected_result",
            "interpretation",
            "observed_result",
            "parameters",
            "prerequisites",
            "procedure",
            "profile",
            "scenario_id",
            "status",
            "version",
        },
        "attack report",
    )
    if report["version"] != ATTACK_REPORT_VERSION or report["profile"] != "attack":
        raise AttackReportError("invalid attack report version")
    scenario_id = report["scenario_id"]
    if not isinstance(scenario_id, str) or scenario_id not in SCENARIO_REGISTRY:
        raise AttackReportError("unknown attack scenario")
    scenario = SCENARIO_REGISTRY[scenario_id]
    for field in (
        "expected_result",
        "interpretation",
        "parameters",
        "prerequisites",
        "procedure",
    ):
        if report[field] != _registry_value(scenario, field):
            raise AttackReportError("attack report changed its registered scenario")
    if scenario_id == CLOUD_SNAPSHOT_SCENARIO:
        observed = _exact_dict(
            report["observed_result"],
            {
                "candidate_count",
                "candidate_signals",
                "excluded_path_accesses",
                "network_attempts",
                "prohibited_material",
                "snapshot_validation",
            },
            "cloud-snapshot observation",
        )
        if any(
            not isinstance(observed[field], int)
            or isinstance(observed[field], bool)
            or observed[field] < 0
            for field in (
                "candidate_count",
                "candidate_signals",
                "excluded_path_accesses",
                "network_attempts",
            )
        ) or any(
            not isinstance(observed[field], str)
            for field in ("prohibited_material", "snapshot_validation")
        ):
            raise AttackReportError("invalid cloud-snapshot observation")
    elif scenario_id == COMBINED_SNAPSHOT_SCENARIO:
        observed = _exact_dict(
            report["observed_result"],
            {
                "candidate_count",
                "candidate_signals",
                "cloud_snapshot_validation",
                "combined_binding",
                "compromised_parties",
                "excluded_path_accesses",
                "network_attempts",
                "party_snapshot_validation",
                "party_snapshots",
                "secret_output_exposures",
                "threshold",
            },
            "combined-snapshot observation",
        )
        if any(
            not isinstance(observed[field], int)
            or isinstance(observed[field], bool)
            or observed[field] < 0
            for field in (
                "candidate_count",
                "candidate_signals",
                "compromised_parties",
                "excluded_path_accesses",
                "network_attempts",
                "party_snapshots",
                "secret_output_exposures",
                "threshold",
            )
        ) or any(
            not isinstance(observed[field], str)
            for field in (
                "cloud_snapshot_validation",
                "combined_binding",
                "party_snapshot_validation",
            )
        ):
            raise AttackReportError("invalid combined-snapshot observation")
    elif scenario_id == PARTY_SNAPSHOT_SCENARIO:
        observed = _exact_dict(
            report["observed_result"],
            {
                "candidate_count",
                "candidate_signals",
                "cloud_material",
                "compromised_parties",
                "excluded_path_accesses",
                "network_attempts",
                "secret_output_exposures",
                "snapshot_validation",
                "threshold",
            },
            "party-snapshot observation",
        )
        if any(
            not isinstance(observed[field], int)
            or isinstance(observed[field], bool)
            or observed[field] < 0
            for field in (
                "candidate_count",
                "candidate_signals",
                "compromised_parties",
                "excluded_path_accesses",
                "network_attempts",
                "secret_output_exposures",
                "threshold",
            )
        ) or any(
            not isinstance(observed[field], str)
            for field in ("cloud_material", "snapshot_validation")
        ):
            raise AttackReportError("invalid party-snapshot observation")
    elif scenario_id == "resolver-unavailable-v1":
        observed = _exact_dict(
            report["observed_result"],
            {"attempt_delta", "failure_category"},
            "attack observation",
        )
        if (
            not isinstance(observed["attempt_delta"], int)
            or isinstance(observed["attempt_delta"], bool)
            or not isinstance(observed["failure_category"], str)
            or observed["failure_category"]
            not in {"resolver-unavailable", "unexpected-error", "unexpected-success"}
        ):
            raise AttackReportError("invalid attack observation")
    else:
        observed = _exact_dict(
            report["observed_result"],
            {
                "cross_epoch_mix",
                "old_epoch_refusal",
                "old_epoch_status",
                "party_restart",
                "partial_new_active",
                "partial_old_active",
                "successor_epoch_status",
                "successor_recovery",
            },
            "cross-epoch observation",
        )
        if any(
            not isinstance(observed[field], str)
            for field in (
                "cross_epoch_mix",
                "old_epoch_refusal",
                "old_epoch_status",
                "party_restart",
                "successor_epoch_status",
                "successor_recovery",
            )
        ) or any(
            not isinstance(observed[field], int) or isinstance(observed[field], bool)
            for field in ("partial_new_active", "partial_old_active")
        ):
            raise AttackReportError("invalid cross-epoch observation")
    if report["status"] not in {"passed", "failed"}:
        raise AttackReportError("invalid attack status")
    passed = observed == _registry_value(scenario, "expected_result")
    if (report["status"] == "passed") != passed:
        raise AttackReportError("attack status does not match the observation")
    validate_public_output(report)
    return report


def build_attack_report(
    *, scenario_id: str, observed_result: dict[str, object]
) -> dict[str, object]:
    """Build an exact report from immutable registry text and one observation."""

    try:
        scenario = SCENARIO_REGISTRY[scenario_id]
    except KeyError as exc:
        raise AttackReportError("unknown attack scenario") from exc
    report: dict[str, object] = {
        "expected_result": _registry_value(scenario, "expected_result"),
        "interpretation": _registry_value(scenario, "interpretation"),
        "observed_result": observed_result,
        "parameters": _registry_value(scenario, "parameters"),
        "prerequisites": _registry_value(scenario, "prerequisites"),
        "procedure": _registry_value(scenario, "procedure"),
        "profile": "attack",
        "scenario_id": scenario_id,
        "status": (
            "passed"
            if observed_result == _registry_value(scenario, "expected_result")
            else "failed"
        ),
        "version": ATTACK_REPORT_VERSION,
    }
    return validate_attack_report(report)


def _unavailable_resolver_url(resolver_url: str) -> str:
    parsed = urlsplit(resolver_url)
    if parsed.scheme != "http" or not parsed.netloc:
        raise AttackReportError("invalid resolver URL")
    return urlunsplit((parsed.scheme, parsed.netloc, "/v1/attack-unavailable", "", ""))


def run_scenario(
    *,
    scenario_id: str,
    client_root: Path | None = None,
    resolver_url: str | None = None,
    restart_checkpoint_dir: Path | None = None,
    snapshot_root: Path | None = None,
) -> dict[str, object]:
    """Run one registered scenario and return a report even on mismatch."""

    if scenario_id == CLOUD_SNAPSHOT_SCENARIO:
        if snapshot_root is None:
            raise AttackReportError("cloud-snapshot scenario requires a snapshot root")
        return build_attack_report(
            scenario_id=scenario_id,
            observed_result=audit_cloud_snapshot(snapshot_root),
        )
    if scenario_id == COMBINED_SNAPSHOT_SCENARIO:
        if snapshot_root is None:
            raise AttackReportError("combined scenario requires a snapshot root")
        return build_attack_report(
            scenario_id=scenario_id,
            observed_result=audit_combined_snapshot(snapshot_root),
        )
    if scenario_id == PARTY_SNAPSHOT_SCENARIO:
        if snapshot_root is None:
            raise AttackReportError("party-snapshot scenario requires a snapshot root")
        return build_attack_report(
            scenario_id=scenario_id,
            observed_result=audit_party_snapshot(snapshot_root),
        )
    if client_root is None or resolver_url is None:
        raise AttackReportError("deployed scenario requires client and resolver inputs")
    if scenario_id == "cross-epoch-runtime-mix-v1":
        return build_attack_report(
            scenario_id=scenario_id,
            observed_result=run_cross_epoch_lifecycle(
                client_root=client_root,
                resolver_url=resolver_url,
                restart_checkpoint_dir=restart_checkpoint_dir,
            ),
        )
    if scenario_id != "resolver-unavailable-v1":
        raise AttackReportError("scenario execution is not implemented")
    before = deployment_attempt_status(client_root)
    failure_category = "unexpected-success"
    try:
        run_client(
            client_root=client_root,
            resolver_url=_unavailable_resolver_url(resolver_url),
        )
    except DeploymentError:
        failure_category = "resolver-unavailable"
    except Exception:
        failure_category = "unexpected-error"
    after = deployment_attempt_status(client_root)
    return build_attack_report(
        scenario_id=scenario_id,
        observed_result={
            "attempt_delta": after["consumed"] - before["consumed"],
            "failure_category": failure_category,
        },
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a registered LOCUS attack")
    parser.add_argument("--scenario", choices=sorted(SCENARIO_REGISTRY), required=True)
    parser.add_argument("--client-root", type=Path)
    parser.add_argument("--resolver-url")
    parser.add_argument("--restart-checkpoint-dir", type=Path)
    parser.add_argument("--snapshot-root", type=Path)
    args = parser.parse_args()
    try:
        report = run_scenario(
            scenario_id=args.scenario,
            client_root=args.client_root,
            resolver_url=args.resolver_url,
            restart_checkpoint_dir=args.restart_checkpoint_dir,
            snapshot_root=args.snapshot_root,
        )
    except (
        AttackReportError,
        CloudSnapshotError,
        CombinedSnapshotError,
        DeploymentError,
        PartySnapshotError,
    ):
        return 2
    print(
        json.dumps(
            report,
            allow_nan=False,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
