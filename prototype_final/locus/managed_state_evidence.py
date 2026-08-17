"""Strict aggregate-only P8.2 managed state-evidence records."""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import shutil
from pathlib import Path
from typing import Any, cast

EVIDENCE_PROFILE_ID = "LOCUS-managed-state-evidence-profile-v1"
SCENARIO_MANIFEST_ID = "LOCUS-managed-state-scenario-manifest-v1"
COMMON_RESULT_ID = "LOCUS-managed-state-result-common-v1"
YI_RESULT_ID = "LOCUS-managed-state-result-yi-v1"
APPSS_RESULT_ID = "LOCUS-managed-state-result-appss-v1"
CORPUS_MANIFEST_ID = "LOCUS-managed-state-corpus-manifest-v1"
RESULT_IDS = frozenset({COMMON_RESULT_ID, YI_RESULT_ID, APPSS_RESULT_ID})
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
SOURCE_COMMIT = re.compile(r"[0-9a-f]{40}\Z")

YI_SUITE = "LOCUS-TPASS-YI-ZK-RISTRETTO255-v1"
APPSS_SUITE = "LOCUS-APPSS-2HASHDH-RISTRETTO255-SHA512-GF128-v1"

ARMS: dict[str, dict[str, Any]] = {
    "yi-2of3": {
        "authorization_quorum": 4,
        "family": "yi",
        "holders": [1, 2, 3],
        "k": 2,
        "n": 3,
        "policy_id": "LOCUS-canonical-email-set-v1",
        "result_id": YI_RESULT_ID,
        "suite_id": YI_SUITE,
        "topology_id": "LOCUS-paired-suite-deployment-2of3-v1",
    },
    "appss-2of3": {
        "authorization_quorum": 4,
        "family": "appss",
        "holders": [1, 2, 3],
        "k": 2,
        "n": 3,
        "policy_id": "LOCUS-canonical-email-set-v1",
        "result_id": APPSS_RESULT_ID,
        "suite_id": APPSS_SUITE,
        "topology_id": "LOCUS-paired-suite-deployment-2of3-v1",
    },
    "yi-3of5": {
        "authorization_quorum": 4,
        "family": "yi",
        "holders": [1, 2, 3, 4, 5],
        "k": 3,
        "n": 5,
        "policy_id": "LOCUS-location-person-set-v1",
        "result_id": YI_RESULT_ID,
        "suite_id": YI_SUITE,
        "topology_id": "LOCUS-paired-suite-deployment-3of5-v1",
    },
    "appss-3of5": {
        "authorization_quorum": 4,
        "family": "appss",
        "holders": [1, 2, 3, 4, 5],
        "k": 3,
        "n": 5,
        "policy_id": "LOCUS-location-person-set-v1",
        "result_id": APPSS_RESULT_ID,
        "suite_id": APPSS_SUITE,
        "topology_id": "LOCUS-paired-suite-deployment-3of5-v1",
    },
}

ARM_SCENARIOS = ("SB01", "SB02", "SB03", "SB04", "SB05", "SB06", "SB07", "SB09", "SB14")
COMMON_SCENARIOS = {
    "SB08": ("2of3-paired", "3of5-paired"),
    "SB10": ("managed-common",),
    "SB11": ("managed-common",),
    "SB12": ("managed-common",),
    "SB13": ("managed-common",),
}
SCENARIO_CONTRACTS = {
    "SB01": ["C03", "C06", "C13", "C21", "C22"],
    "SB02": ["C04", "C24"],
    "SB03": ["C05", "C24"],
    "SB04": ["C19", "C23", "C25"],
    "SB05": ["C26"],
    "SB06": ["C07", "C08", "C16", "M03"],
    "SB07": ["C10", "C22"],
    "SB08": ["C11", "C26"],
    "SB09": ["C06", "C21", "M02"],
    "SB10": ["C14", "C15", "M01"],
    "SB11": ["C08", "C16", "M03"],
    "SB12": ["C16", "M04"],
    "SB13": ["C07", "M05"],
    "SB14": ["C03", "C04", "C05", "C20", "M01", "M02", "M03", "M04", "M05"],
}
SNAPSHOT_BY_SCENARIO = {
    "SB01": "post_enrollment",
    "SB02": "post_enrollment",
    "SB03": "post_enrollment",
    "SB04": "post_recovery",
    "SB05": "post_recovery",
    "SB06": "post_recovery",
    "SB07": "post_enrollment",
    "SB08": "preserved_restart",
    "SB09": "post_recovery",
    "SB10": "preserved_restart",
    "SB11": "preserved_restart",
    "SB12": "post_recovery",
    "SB13": "fresh_reset",
    "SB14": "preserved_restart",
}
EXPECTED_ROLES = (
    "admission",
    "bootstrap",
    "managed-client-template",
    "manager-controller",
    "manager-ui",
    "operator",
    "party",
    "party",
    "party",
    "party",
    "party",
    "resolver",
    "provider",
    "s3-role",
    "storage-gateway",
)


class ManagedStateEvidenceError(ValueError):
    """A P8.2 state-evidence object or publication is unsafe or malformed."""


def canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode() + b"\n"


def _digest(value: object) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def scenario_manifest() -> dict[str, object]:
    reports = [
        {
            "arm_id": arm_id,
            "result_id": ARMS[arm_id]["result_id"],
            "scenario_id": scenario,
        }
        for scenario in ARM_SCENARIOS
        for arm_id in ARMS
    ]
    reports.extend(
        {
            "arm_id": arm_id,
            "result_id": COMMON_RESULT_ID,
            "scenario_id": scenario,
        }
        for scenario, arm_ids in COMMON_SCENARIOS.items()
        for arm_id in arm_ids
    )
    return {
        "arms": ARMS,
        "evidence_profile_id": EVIDENCE_PROFILE_ID,
        "format_id": SCENARIO_MANIFEST_ID,
        "report_count": 42,
        "reports": reports,
        "scenario_contracts": SCENARIO_CONTRACTS,
        "status": "assigned",
    }


def _checks(scenario_id: str, arm: dict[str, Any] | None) -> int:
    if scenario_id in {"SB02", "SB03"} and arm is not None:
        return 3 if arm["k"] == 2 else 15
    if scenario_id == "SB04" and arm is not None:
        return 3 if arm["k"] == 2 else 10
    if scenario_id == "SB08":
        return 4
    if scenario_id == "SB14":
        return 15
    return 1


def expected_report_paths() -> tuple[str, ...]:
    paths: list[str] = []
    specifications = cast(list[dict[str, object]], scenario_manifest()["reports"])
    for specification in specifications:
        arm_id = cast(str, specification["arm_id"])
        result_id = cast(str, specification["result_id"])
        scenario_id = cast(str, specification["scenario_id"])
        arm = ARMS.get(arm_id)
        if result_id == COMMON_RESULT_ID:
            family = "common"
        elif arm is not None:
            family = cast(str, arm["family"])
        else:  # pragma: no cover - fixed manifest construction prevents this
            raise ManagedStateEvidenceError("suite report omitted its arm")
        topology = arm_id if family == "common" else arm_id.split("-", 1)[1]
        paths.append(f"{family}/{topology}/{scenario_id}.json")
    return tuple(paths)


def _snapshot(summary: dict[str, object], scenario_id: str) -> dict[str, object]:
    snapshots = summary.get("state_snapshots")
    if not isinstance(snapshots, dict):
        raise ManagedStateEvidenceError("missing state snapshot sets")
    label = SNAPSHOT_BY_SCENARIO[scenario_id]
    observations = snapshots.get(label)
    if not isinstance(observations, list) or len(observations) != 15:
        raise ManagedStateEvidenceError("incomplete state snapshot set")
    roles: list[dict[str, object]] = []
    for value in observations:
        if (
            not isinstance(value, dict)
            or set(value) != {"files", "role", "total_bytes", "volume_role"}
            or not isinstance(value["files"], int)
            or not isinstance(value["total_bytes"], int)
            or not isinstance(value["role"], str)
            or not isinstance(value["volume_role"], str)
        ):
            raise ManagedStateEvidenceError("invalid role snapshot observation")
        roles.append(dict(value))
    if tuple(value["role"] for value in roles) != EXPECTED_ROLES:
        raise ManagedStateEvidenceError("role snapshot order changed")
    aggregate = {"label": label, "roles": roles}
    return {"aggregate_sha256": _digest(aggregate), **aggregate}


def _base_bindings(provenance: dict[str, object]) -> dict[str, object]:
    required = {
        "collected_at_utc",
        "compose_sha256",
        "host_tier",
        "image_id",
        "live_graph_sha256",
        "lockfile_sha256",
        "managed_manifest_sha256",
        "pseudonymous_host_id",
        "resolved_graph_sha256",
        "source_commit",
        "source_tree_sha256",
    }
    if set(provenance) != required:
        raise ManagedStateEvidenceError("provenance field set changed")
    for field in required - {
        "collected_at_utc",
        "host_tier",
        "image_id",
        "pseudonymous_host_id",
        "source_commit",
    }:
        candidate = provenance[field]
        if not isinstance(candidate, str) or SHA256.fullmatch(candidate) is None:
            raise ManagedStateEvidenceError(f"invalid provenance digest: {field}")
    if (
        not isinstance(provenance["source_commit"], str)
        or SOURCE_COMMIT.fullmatch(provenance["source_commit"]) is None
    ):
        raise ManagedStateEvidenceError("invalid source commit")
    return {
        **provenance,
        "admission_profile_id": "LOCUS-local-synthetic-admission-v1",
        "client_api_id": "LOCUS-client-api-v2",
        "client_instance_profile_id": "LOCUS-managed-client-instance-v1",
        "configuration_id": "LOCUS-integrated-manager-config-v1",
        "controller_api_id": "LOCUS-container-controller-api-v1",
        "deployment_id": "LOCUS-integrated-manager-deployment-v1",
        "manager_api_id": "LOCUS-manager-api-v1",
        "package_profile_id": "LOCUS-client-recovery-package-v1",
        "provider_id": "LOCUS-storage-provider-s3-compatible-v1",
    }


def build_reports(
    *, provenance: dict[str, object], summary: dict[str, object]
) -> list[tuple[str, dict[str, object]]]:
    if (
        summary.get("status") != "passed"
        or summary.get("output_scan") != "passed"
        or summary.get("paired_policy_conditions") is not True
        or summary.get("arms") != 4
    ):
        raise ManagedStateEvidenceError("integrated state run did not pass")
    bindings = _base_bindings(provenance)
    manifest_sha256 = _digest(scenario_manifest())
    reports: list[tuple[str, dict[str, object]]] = []
    specifications = cast(list[object], scenario_manifest()["reports"])
    for specification in specifications:
        if not isinstance(specification, dict):
            raise ManagedStateEvidenceError("invalid report specification")
        scenario_id = str(specification["scenario_id"])
        arm_id = str(specification["arm_id"])
        result_id = str(specification["result_id"])
        arm = ARMS.get(arm_id)
        checks = _checks(scenario_id, arm)
        report: dict[str, object] = {
            "arm": None if arm is None else arm,
            "arm_id": arm_id,
            "bindings": bindings,
            "cleanup": {
                "containers_remaining": 0,
                "images_remaining": 0,
                "networks_remaining": 0,
                "status": "passed",
                "volumes_remaining": 0,
            },
            "evidence_profile_id": EVIDENCE_PROFILE_ID,
            "format_id": result_id,
            "limitations": [
                "same-host-single-operator",
                "implementation-behavior-not-cryptographic-proof",
                "no-human-usability-or-production-readiness",
                "no-global-rollback-resistant-attempt-bound",
                "no-forensic-erasure",
            ],
            "metrics": {
                "ordinary_checks": checks,
                "ordinary_violations": 0,
                "positive_control_checks": checks,
                "positive_control_detections": checks,
            },
            "output_safety": {
                "forbidden_retained_fields": 0,
                "logs_retained": False,
                "output_scan": "passed",
                "packet_captures_retained": False,
                "snapshots_retained": False,
            },
            "scenario_contracts": SCENARIO_CONTRACTS[scenario_id],
            "scenario_id": scenario_id,
            "scenario_manifest_sha256": manifest_sha256,
            "snapshot_set": _snapshot(summary, scenario_id),
            "status": "passed",
        }
        validate_result(report)
        if result_id == COMMON_RESULT_ID:
            family = "common"
        elif arm is not None:
            family = str(arm["family"])
        else:  # pragma: no cover - manifest construction guarantees this pairing
            raise ManagedStateEvidenceError("suite result omitted its arm")
        topology = (
            arm_id if family == "common" else ("2of3" if "2of3" in arm_id else "3of5")
        )
        reports.append((f"{family}/{topology}/{scenario_id}.json", report))
    if len(reports) != 42 or len({path for path, _report in reports}) != 42:
        raise ManagedStateEvidenceError("retained report membership changed")
    return reports


def validate_result(value: object) -> None:
    fields = {
        "arm",
        "arm_id",
        "bindings",
        "cleanup",
        "evidence_profile_id",
        "format_id",
        "limitations",
        "metrics",
        "output_safety",
        "scenario_contracts",
        "scenario_id",
        "scenario_manifest_sha256",
        "snapshot_set",
        "status",
    }
    if not isinstance(value, dict) or set(value) != fields:
        raise ManagedStateEvidenceError("state result field set changed")
    if (
        value["format_id"] not in RESULT_IDS
        or value["evidence_profile_id"] != EVIDENCE_PROFILE_ID
    ):
        raise ManagedStateEvidenceError("state result identifier changed")
    if value["status"] != "passed" or value["scenario_id"] not in SCENARIO_CONTRACTS:
        raise ManagedStateEvidenceError("state result status or scenario changed")
    scenario_id = cast(str, value["scenario_id"])
    if value["scenario_contracts"] != SCENARIO_CONTRACTS[scenario_id]:
        raise ManagedStateEvidenceError("scenario contract binding changed")
    expected_manifest_sha256 = _digest(scenario_manifest())
    if value["scenario_manifest_sha256"] != expected_manifest_sha256:
        raise ManagedStateEvidenceError("scenario manifest binding changed")
    arm_id = value["arm_id"]
    arm = value["arm"]
    if not isinstance(arm_id, str):
        raise ManagedStateEvidenceError("invalid arm identifier")
    expected_arm = ARMS.get(arm_id)
    if expected_arm is None:
        if arm is not None or value["format_id"] != COMMON_RESULT_ID:
            raise ManagedStateEvidenceError("common result has a suite arm")
    elif arm != expected_arm or value["format_id"] != expected_arm["result_id"]:
        raise ManagedStateEvidenceError("suite result arm binding changed")
    bindings = value["bindings"]
    expected_binding_fields = {
        "admission_profile_id",
        "client_api_id",
        "client_instance_profile_id",
        "collected_at_utc",
        "compose_sha256",
        "configuration_id",
        "controller_api_id",
        "deployment_id",
        "host_tier",
        "image_id",
        "live_graph_sha256",
        "lockfile_sha256",
        "managed_manifest_sha256",
        "manager_api_id",
        "package_profile_id",
        "provider_id",
        "pseudonymous_host_id",
        "resolved_graph_sha256",
        "source_commit",
        "source_tree_sha256",
    }
    if not isinstance(bindings, dict) or set(bindings) != expected_binding_fields:
        raise ManagedStateEvidenceError("provenance binding field set changed")
    digest_fields = {
        "compose_sha256",
        "live_graph_sha256",
        "lockfile_sha256",
        "managed_manifest_sha256",
        "resolved_graph_sha256",
        "source_tree_sha256",
    }
    if any(
        not isinstance(bindings[field], str)
        or SHA256.fullmatch(bindings[field]) is None
        for field in digest_fields
    ):
        raise ManagedStateEvidenceError("invalid provenance digest")
    fixed_bindings = {
        "admission_profile_id": "LOCUS-local-synthetic-admission-v1",
        "client_api_id": "LOCUS-client-api-v2",
        "client_instance_profile_id": "LOCUS-managed-client-instance-v1",
        "configuration_id": "LOCUS-integrated-manager-config-v1",
        "controller_api_id": "LOCUS-container-controller-api-v1",
        "deployment_id": "LOCUS-integrated-manager-deployment-v1",
        "host_tier": "same-host-single-operator",
        "manager_api_id": "LOCUS-manager-api-v1",
        "package_profile_id": "LOCUS-client-recovery-package-v1",
        "provider_id": "LOCUS-storage-provider-s3-compatible-v1",
    }
    if any(bindings[field] != expected for field, expected in fixed_bindings.items()):
        raise ManagedStateEvidenceError("fixed provenance binding changed")
    if (
        not isinstance(bindings["source_commit"], str)
        or SOURCE_COMMIT.fullmatch(bindings["source_commit"]) is None
        or not isinstance(bindings["image_id"], str)
        or re.fullmatch(r"sha256:[0-9a-f]{64}", bindings["image_id"]) is None
        or not isinstance(bindings["pseudonymous_host_id"], str)
        or re.fullmatch(r"host-[0-9a-f]{16}", bindings["pseudonymous_host_id"]) is None
    ):
        raise ManagedStateEvidenceError("invalid provenance identity")
    cleanup = value["cleanup"]
    if cleanup != {
        "containers_remaining": 0,
        "images_remaining": 0,
        "networks_remaining": 0,
        "status": "passed",
        "volumes_remaining": 0,
    }:
        raise ManagedStateEvidenceError("cleanup did not pass exactly")
    snapshot = value["snapshot_set"]
    if not isinstance(snapshot, dict) or set(snapshot) != {
        "aggregate_sha256",
        "label",
        "roles",
    }:
        raise ManagedStateEvidenceError("state snapshot field set changed")
    roles = snapshot["roles"]
    if (
        not isinstance(roles, list)
        or len(roles) != 15
        or snapshot["label"] != SNAPSHOT_BY_SCENARIO[scenario_id]
        or tuple(item.get("role") for item in roles if isinstance(item, dict))
        != EXPECTED_ROLES
        or snapshot["aggregate_sha256"]
        != _digest({"label": snapshot["label"], "roles": roles})
    ):
        raise ManagedStateEvidenceError("state snapshot binding changed")
    metrics = value["metrics"]
    if (
        not isinstance(metrics, dict)
        or set(metrics)
        != {
            "ordinary_checks",
            "ordinary_violations",
            "positive_control_checks",
            "positive_control_detections",
        }
        or metrics["ordinary_violations"] != 0
        or metrics["ordinary_checks"] != metrics["positive_control_checks"]
        or metrics["positive_control_checks"] != metrics["positive_control_detections"]
    ):
        raise ManagedStateEvidenceError("state result controls did not pass")
    safety = value["output_safety"]
    if not isinstance(safety, dict) or safety != {
        "forbidden_retained_fields": 0,
        "logs_retained": False,
        "output_scan": "passed",
        "packet_captures_retained": False,
        "snapshots_retained": False,
    }:
        raise ManagedStateEvidenceError("unsafe retained output policy")
    encoded = canonical_json(value).lower()
    for prohibited in (
        b"private_key",
        b"recovery_input",
        b"candidate_value",
        b"certificate_pem",
        b"absolute_path",
        b"traceback",
    ):
        if prohibited in encoded:
            raise ManagedStateEvidenceError("prohibited retained field")


def publish_corpus(
    *, root: Path, reports: list[tuple[str, dict[str, object]]]
) -> dict[str, object]:
    retained_root = root / "evidence" / "retained"
    target = retained_root / "managed-state-v1"
    if target.exists():
        raise ManagedStateEvidenceError("managed state corpus already exists")
    retained_root.mkdir(parents=True, exist_ok=True)
    staging = retained_root / f".managed-state-v1-staging-{secrets.token_hex(8)}"
    staging.mkdir()
    try:
        paths = [path for path, _report in reports]
        if tuple(paths) != expected_report_paths():
            raise ManagedStateEvidenceError("retained report membership changed")
        entries: list[dict[str, object]] = []
        for relative, report in reports:
            validate_result(report)
            path = staging / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            encoded = canonical_json(report)
            with path.open("xb") as handle:
                handle.write(encoded)
                handle.flush()
                os.fsync(handle.fileno())
            entries.append(
                {
                    "path": relative,
                    "sha256": hashlib.sha256(encoded).hexdigest(),
                    "size": len(encoded),
                }
            )
        entries.sort(key=lambda item: str(item["path"]))
        records_sha256 = _digest(entries)
        manifest = {
            "entries": entries,
            "format_id": CORPUS_MANIFEST_ID,
            "record_count": 42,
            "records_sha256": records_sha256,
            "scenario_manifest_sha256": _digest(scenario_manifest()),
            "status": "complete",
        }
        with (staging / "corpus-manifest.json").open("xb") as handle:
            handle.write(canonical_json(manifest))
            handle.flush()
            os.fsync(handle.fileno())
        validate_corpus_path(staging)
        os.rename(staging, target)
        return manifest
    except BaseException as error:
        resolved = staging.resolve()
        if resolved.parent != retained_root.resolve() or not resolved.name.startswith(
            ".managed-state-v1-staging-"
        ):
            raise ManagedStateEvidenceError("unsafe evidence staging path") from error
        shutil.rmtree(resolved, ignore_errors=True)
        raise


def validate_corpus_path(target: Path) -> dict[str, object]:
    manifest_path = target / "corpus-manifest.json"
    try:
        encoded_manifest = manifest_path.read_bytes()
        manifest = json.loads(encoded_manifest)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ManagedStateEvidenceError("invalid corpus manifest") from error
    if canonical_json(manifest) != encoded_manifest or not isinstance(manifest, dict):
        raise ManagedStateEvidenceError("corpus manifest is not canonical")
    if set(manifest) != {
        "entries",
        "format_id",
        "record_count",
        "records_sha256",
        "scenario_manifest_sha256",
        "status",
    }:
        raise ManagedStateEvidenceError("corpus manifest field set changed")
    entries = manifest["entries"]
    if (
        manifest["format_id"] != CORPUS_MANIFEST_ID
        or manifest["record_count"] != 42
        or manifest["status"] != "complete"
        or manifest["scenario_manifest_sha256"] != _digest(scenario_manifest())
        or not isinstance(entries, list)
        or [item.get("path") for item in entries if isinstance(item, dict)]
        != sorted(expected_report_paths())
        or manifest["records_sha256"] != _digest(entries)
    ):
        raise ManagedStateEvidenceError("corpus manifest binding changed")
    expected_files = {"corpus-manifest.json"}
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {"path", "sha256", "size"}:
            raise ManagedStateEvidenceError("invalid corpus entry")
        relative = entry["path"]
        if not isinstance(relative, str) or relative not in expected_report_paths():
            raise ManagedStateEvidenceError("invalid corpus entry path")
        expected_files.add(relative)
        path = target / relative
        try:
            encoded = path.read_bytes()
            report = json.loads(encoded)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ManagedStateEvidenceError("invalid corpus result") from error
        if (
            canonical_json(report) != encoded
            or entry["size"] != len(encoded)
            or entry["sha256"] != hashlib.sha256(encoded).hexdigest()
        ):
            raise ManagedStateEvidenceError("corpus result hash changed")
        validate_result(report)
    actual_files = {
        path.relative_to(target).as_posix()
        for path in target.rglob("*")
        if path.is_file()
    }
    if actual_files != expected_files:
        raise ManagedStateEvidenceError("corpus contains an unexpected file")
    return cast(dict[str, object], manifest)


__all__ = [
    "APPSS_RESULT_ID",
    "COMMON_RESULT_ID",
    "CORPUS_MANIFEST_ID",
    "EVIDENCE_PROFILE_ID",
    "ManagedStateEvidenceError",
    "SCENARIO_MANIFEST_ID",
    "YI_RESULT_ID",
    "build_reports",
    "canonical_json",
    "expected_report_paths",
    "publish_corpus",
    "scenario_manifest",
    "validate_corpus_path",
    "validate_result",
]
