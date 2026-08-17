"""Strict aggregate-only P8.3 managed network-flow evidence records."""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import shutil
from pathlib import Path
from typing import Any, cast

EVIDENCE_PROFILE_ID = "LOCUS-managed-flow-evidence-profile-v1"
TRACE_POLICY_ID = "LOCUS-managed-flow-trace-policy-v1"
SCENARIO_MANIFEST_ID = "LOCUS-managed-flow-scenario-manifest-v1"
COMMON_RESULT_ID = "LOCUS-managed-flow-result-common-v1"
YI_RESULT_ID = "LOCUS-managed-flow-result-yi-v1"
APPSS_RESULT_ID = "LOCUS-managed-flow-result-appss-v1"
CORPUS_MANIFEST_ID = "LOCUS-managed-flow-corpus-manifest-v1"
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
SOURCE_COMMIT = re.compile(r"[0-9a-f]{40}\Z")
PSEUDONYM = re.compile(r"(?:host|project|clients|packages)-[0-9a-f]{16}\Z")

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
ARM_SCENARIOS = ("NF01", "NF02", "NF03", "NF04", "NF05", "NF06")
COMMON_SCENARIOS = ("NF07", "NF08", "NF09", "NF10", "NF11", "NF12")
SCENARIO_CONTRACTS = {
    "NF01": ["C07", "C08", "C09", "C10", "C11", "C12", "C13"],
    "NF02": ["C07", "C08", "C09", "C10", "C11", "C13", "C16"],
    "NF03": ["C08", "C09", "C10", "M02"],
    "NF04": ["C08", "C09", "C11", "C12", "C13", "C16"],
    "NF05": ["C09", "C11"],
    "NF06": ["C11", "C12", "C13"],
    "NF07": ["C14", "C15", "M01"],
    "NF08": ["C14", "C15", "M03"],
    "NF09": ["C14", "C15", "M04"],
    "NF10": ["C14", "C15", "M03"],
    "NF11": ["C14", "C15", "M05"],
    "NF12": [
        "C07",
        "C08",
        "C09",
        "C10",
        "C11",
        "C12",
        "C13",
        "C14",
        "C15",
        "C16",
        "C21",
        "C22",
        "C26",
        "M01",
        "M02",
        "M03",
        "M04",
        "M05",
    ],
}
EXPECTED_ABSENCES = (
    "browser-to-service",
    "client-to-manager",
    "client-to-provider",
    "manager-to-client-container",
    "ui-to-docker",
    "unknown-edge-or-category",
)
POSITIVE_CONTROLS = {
    "allowed_edge_observed": True,
    "byte_bound_detected": True,
    "client_controller_success": True,
    "fabricated_noresolver_detected": True,
    "fictional_marker_detected": True,
    "manager_controller_success": True,
    "mismatch_detected": True,
    "raw_events_discarded": True,
    "sequence_gap_detected": True,
    "service_logs_discarded": True,
    "unknown_category_detected": True,
    "unknown_role_detected": True,
    "blocked_isolation_probes": True,
}
CONTACT_FIELDS = {
    "category",
    "receiver_role",
    "reconciliation",
    "rejected_count",
    "request_body_bytes",
    "request_count",
    "response_body_bytes",
    "sender_role",
    "success_count",
    "unavailable_count",
}
PROHIBITED_KEYS = re.compile(
    r"(?:^|_)(?:payload|route|url|ip|port|header|certificate|credential|cue|package_bytes|private_key|share|candidate|timestamp|event|log|pcap|ordering)(?:_|$)",
    re.I,
)


class ManagedFlowEvidenceError(ValueError):
    """A P8.3 flow object or publication is unsafe or malformed."""


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
            "arm_id": "managed-common",
            "result_id": COMMON_RESULT_ID,
            "scenario_id": scenario,
        }
        for scenario in COMMON_SCENARIOS
    )
    return {
        "arms": ARMS,
        "evidence_profile_id": EVIDENCE_PROFILE_ID,
        "format_id": SCENARIO_MANIFEST_ID,
        "report_count": 30,
        "reports": reports,
        "scenario_contracts": SCENARIO_CONTRACTS,
        "status": "assigned",
        "trace_policy_id": TRACE_POLICY_ID,
    }


def expected_report_paths() -> tuple[str, ...]:
    result: list[str] = []
    for item in cast(list[dict[str, str]], scenario_manifest()["reports"]):
        arm_id, scenario = item["arm_id"], item["scenario_id"]
        if arm_id == "managed-common":
            result.append(f"common/managed-common/{scenario}.json")
        else:
            arm = ARMS[arm_id]
            result.append(f"{arm['family']}/{arm_id.split('-', 1)[1]}/{scenario}.json")
    return tuple(result)


def _bindings(provenance: dict[str, object]) -> dict[str, object]:
    required = {
        "collected_at_utc",
        "compose_sha256",
        "host_tier",
        "image_id",
        "live_graph_sha256",
        "lockfile_sha256",
        "managed_manifest_sha256",
        "pseudonymous_client_set_id",
        "pseudonymous_host_id",
        "pseudonymous_package_set_id",
        "pseudonymous_project_id",
        "resolved_graph_sha256",
        "source_commit",
        "source_tree_sha256",
    }
    if set(provenance) != required:
        raise ManagedFlowEvidenceError("provenance field set changed")
    for key in required - {
        "collected_at_utc",
        "host_tier",
        "image_id",
        "source_commit",
        "pseudonymous_client_set_id",
        "pseudonymous_host_id",
        "pseudonymous_package_set_id",
        "pseudonymous_project_id",
    }:
        if (
            not isinstance(provenance[key], str)
            or SHA256.fullmatch(cast(str, provenance[key])) is None
        ):
            raise ManagedFlowEvidenceError(f"invalid provenance digest: {key}")
    if (
        not isinstance(provenance["source_commit"], str)
        or SOURCE_COMMIT.fullmatch(provenance["source_commit"]) is None
    ):
        raise ManagedFlowEvidenceError("invalid source commit")
    for key in (
        "pseudonymous_client_set_id",
        "pseudonymous_host_id",
        "pseudonymous_package_set_id",
        "pseudonymous_project_id",
    ):
        if (
            not isinstance(provenance[key], str)
            or PSEUDONYM.fullmatch(cast(str, provenance[key])) is None
        ):
            raise ManagedFlowEvidenceError(f"invalid pseudonym: {key}")
    if provenance["host_tier"] != "same-host-single-operator":
        raise ManagedFlowEvidenceError("unsupported host tier")
    return dict(provenance)


def _validate_scenario_contacts(
    scenario: str, arm: dict[str, Any] | None, contacts: list[object]
) -> None:
    categories = {item.get("category") for item in contacts if isinstance(item, dict)}
    required = {
        "NF01": {"enroll", "admission-issue", "storage-execute"},
        "NF02": {"recover", "authorize", "storage-execute"},
        "NF03": {"package-export", "package-import"},
        "NF04": {"recover"},
        "NF05": {"policy-preview"},
        "NF06": {"package-import", "storage-execute"},
        "NF07": {"client-create", "container-create"},
        "NF08": {"container-action", "container-restart", "container-kill"},
        "NF09": {"self-destroy", "container-remove"},
        "NF10": {"system-stop", "container-stop", "recover"},
        "NF11": {"system-stop", "client-create", "package-import"},
        "NF12": {"manager-status", "client-session"},
    }[scenario]
    if not required <= categories:
        raise ManagedFlowEvidenceError(f"required allowed contact missing: {scenario}")
    if arm is not None:
        suite_required = (
            {"yi-enroll"} if scenario == "NF01" and arm["family"] == "yi" else set()
        )
        if scenario == "NF01" and arm["family"] == "appss":
            suite_required = {"appss-initialize", "appss-install"}
        if scenario == "NF02" and arm["family"] == "yi":
            suite_required = {"yi-prepare", "yi-respond"}
        if scenario == "NF02" and arm["family"] == "appss":
            suite_required = {"appss-evaluate"}
        if not suite_required <= categories:
            raise ManagedFlowEvidenceError("suite-specific contact missing")
        if scenario == "NF05":
            resolver_observed = "resolver-resolve" in categories
            if resolver_observed != (arm["n"] == 5):
                raise ManagedFlowEvidenceError(
                    "resolver routing observation changed: "
                    f"{arm['family']}-{arm['k']}of{arm['n']}/"
                    f"observed={resolver_observed}"
                )

    def rejected(item: object) -> bool:
        if not isinstance(item, dict):
            return False
        rejected_count = item.get("rejected_count")
        unavailable_count = item.get("unavailable_count")
        return (
            isinstance(rejected_count, int)
            and isinstance(unavailable_count, int)
            and rejected_count + unavailable_count > 0
        )

    if scenario in {"NF04", "NF06", "NF11"} and not any(
        rejected(item) for item in contacts
    ):
        raise ManagedFlowEvidenceError("required rejection observation missing")


def build_reports(
    *, provenance: dict[str, object], summary: dict[str, object]
) -> list[tuple[str, dict[str, object]]]:
    if summary.get("status") != "passed" or summary.get("output_scan") != "passed":
        raise ManagedFlowEvidenceError("flow run did not pass")
    contacts_by_context = summary.get("flow_contacts")
    controls = summary.get("positive_controls")
    if not isinstance(contacts_by_context, dict) or not isinstance(controls, dict):
        raise ManagedFlowEvidenceError("flow summary is incomplete")
    if controls != POSITIVE_CONTROLS:
        raise ManagedFlowEvidenceError("positive controls incomplete")
    bindings = _bindings(provenance)
    manifest_digest = _digest(scenario_manifest())
    reports: list[tuple[str, dict[str, object]]] = []
    paths = expected_report_paths()
    specifications = cast(list[dict[str, str]], scenario_manifest()["reports"])
    for path, specification in zip(paths, specifications, strict=True):
        arm_id, scenario = specification["arm_id"], specification["scenario_id"]
        context = f"{scenario}:{arm_id}"
        contacts = contacts_by_context.get(context)
        if not isinstance(contacts, list) or not contacts:
            raise ManagedFlowEvidenceError(f"missing contacts for {context}")
        arm = None if arm_id == "managed-common" else ARMS[arm_id]
        _validate_scenario_contacts(scenario, arm, contacts)
        report: dict[str, object] = {
            "arm": arm,
            "arm_id": arm_id,
            "bindings": bindings,
            "cleanup": {"complete": True, "raw_observations_discarded": True},
            "contacts": contacts,
            "evidence_profile_id": EVIDENCE_PROFILE_ID,
            "expected_absences": {name: True for name in EXPECTED_ABSENCES},
            "format_id": specification["result_id"],
            "limitations": [
                "same-host single-operator observation only",
                "application-boundary aggregates are not packet capture",
                "counts do not establish cryptographic proof",
                "no latency throughput or resilience metric is reported",
                "managed UI does not expose successor lifecycle operations",
            ],
            "metrics": {
                "contact_categories": len(contacts),
                "reconciliation_failures": 0,
            },
            "output_safety": {"prohibited_findings": 0, "scan": "passed"},
            "positive_controls": controls,
            "scenario_contracts": SCENARIO_CONTRACTS[scenario],
            "scenario_id": scenario,
            "scenario_manifest_sha256": manifest_digest,
            "status": "passed",
            "trace_policy_id": TRACE_POLICY_ID,
        }
        validate_result(report)
        reports.append((path, report))
    return reports


def _walk_keys(value: object) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if PROHIBITED_KEYS.search(str(key)):
                raise ManagedFlowEvidenceError(f"prohibited retained field: {key}")
            _walk_keys(child)
    elif isinstance(value, list):
        for child in value:
            _walk_keys(child)


def validate_result(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ManagedFlowEvidenceError("result is not an object")
    required = {
        "arm",
        "arm_id",
        "bindings",
        "cleanup",
        "contacts",
        "evidence_profile_id",
        "expected_absences",
        "format_id",
        "limitations",
        "metrics",
        "output_safety",
        "positive_controls",
        "scenario_contracts",
        "scenario_id",
        "scenario_manifest_sha256",
        "status",
        "trace_policy_id",
    }
    if set(value) != required:
        raise ManagedFlowEvidenceError("result field set changed")
    _walk_keys(value)
    if (
        value["evidence_profile_id"] != EVIDENCE_PROFILE_ID
        or value["trace_policy_id"] != TRACE_POLICY_ID
        or value["status"] != "passed"
    ):
        raise ManagedFlowEvidenceError("result profile or status changed")
    if value["format_id"] not in {YI_RESULT_ID, APPSS_RESULT_ID, COMMON_RESULT_ID}:
        raise ManagedFlowEvidenceError("unknown result format")
    if value["scenario_id"] not in ARM_SCENARIOS + COMMON_SCENARIOS:
        raise ManagedFlowEvidenceError("unknown scenario")
    contacts = value["contacts"]
    if not isinstance(contacts, list) or not contacts:
        raise ManagedFlowEvidenceError("empty contacts")
    for contact in contacts:
        if not isinstance(contact, dict) or set(contact) != CONTACT_FIELDS:
            raise ManagedFlowEvidenceError("contact field set changed")
        for field in (
            "request_body_bytes",
            "request_count",
            "response_body_bytes",
            "success_count",
            "rejected_count",
            "unavailable_count",
        ):
            if not isinstance(contact[field], int) or contact[field] < 0:
                raise ManagedFlowEvidenceError("invalid contact aggregate")
        if (
            contact["request_count"]
            != contact["success_count"]
            + contact["rejected_count"]
            + contact["unavailable_count"]
        ):
            raise ManagedFlowEvidenceError("contact counts do not reconcile")
        if contact["reconciliation"] not in {"matched", "fixed-available"}:
            raise ManagedFlowEvidenceError("invalid reconciliation")
    if value["expected_absences"] != {name: True for name in EXPECTED_ABSENCES}:
        raise ManagedFlowEvidenceError("expected absence failed")
    if value["cleanup"] != {"complete": True, "raw_observations_discarded": True}:
        raise ManagedFlowEvidenceError("cleanup incomplete")
    if value["output_safety"] != {"prohibited_findings": 0, "scan": "passed"}:
        raise ManagedFlowEvidenceError("output safety failed")
    return cast(dict[str, object], value)


def publish_corpus(
    *, root: Path, reports: list[tuple[str, dict[str, object]]]
) -> dict[str, object]:
    target = root / "evidence" / "retained" / "managed-flow-v1"
    if target.exists():
        raise ManagedFlowEvidenceError("managed-flow corpus already exists")
    if tuple(path for path, _ in reports) != expected_report_paths():
        raise ManagedFlowEvidenceError("report membership or order changed")
    temporary = target.parent / f".{target.name}.tmp-{secrets.token_hex(8)}"
    entries: list[dict[str, object]] = []
    try:
        for path, report in reports:
            validate_result(report)
            encoded = canonical_json(report)
            destination = temporary / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(encoded)
            entries.append(
                {"path": path, "sha256": hashlib.sha256(encoded).hexdigest()}
            )
        manifest = {
            "corpus_sha256": _digest(entries),
            "entries": entries,
            "evidence_profile_id": EVIDENCE_PROFILE_ID,
            "format_id": CORPUS_MANIFEST_ID,
            "record_count": 30,
            "scenario_manifest_sha256": _digest(scenario_manifest()),
            "status": "complete",
            "trace_policy_id": TRACE_POLICY_ID,
        }
        (temporary / "manifest.json").write_bytes(canonical_json(manifest))
        target.parent.mkdir(parents=True, exist_ok=True)
        os.rename(temporary, target)
        return manifest
    except BaseException:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def validate_corpus_path(target: Path) -> dict[str, object]:
    manifest_path = target / "manifest.json"
    if not manifest_path.is_file():
        raise ManagedFlowEvidenceError("missing corpus manifest")
    manifest = json.loads(manifest_path.read_bytes())
    if (
        manifest.get("format_id") != CORPUS_MANIFEST_ID
        or manifest.get("record_count") != 30
    ):
        raise ManagedFlowEvidenceError("invalid corpus manifest")
    entries = manifest.get("entries")
    if not isinstance(entries, list) or [
        item.get("path") for item in entries if isinstance(item, dict)
    ] != list(expected_report_paths()):
        raise ManagedFlowEvidenceError("corpus membership changed")
    expected_files = {"manifest.json", *expected_report_paths()}
    actual_files = {
        path.relative_to(target).as_posix()
        for path in target.rglob("*")
        if path.is_file()
    }
    if actual_files != expected_files:
        raise ManagedFlowEvidenceError("corpus contains unexpected files")
    for item in entries:
        encoded = (target / item["path"]).read_bytes()
        if (
            hashlib.sha256(encoded).hexdigest() != item["sha256"]
            or canonical_json(json.loads(encoded)) != encoded
        ):
            raise ManagedFlowEvidenceError("corpus digest or canonical encoding failed")
        validate_result(json.loads(encoded))
    if manifest.get("corpus_sha256") != _digest(entries):
        raise ManagedFlowEvidenceError("corpus closure failed")
    return cast(dict[str, object], manifest)


__all__ = [
    "APPSS_RESULT_ID",
    "COMMON_RESULT_ID",
    "YI_RESULT_ID",
    "ManagedFlowEvidenceError",
    "build_reports",
    "canonical_json",
    "publish_corpus",
    "scenario_manifest",
    "validate_corpus_path",
    "validate_result",
]
