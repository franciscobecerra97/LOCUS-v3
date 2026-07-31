"""Exact privacy-safe retained evidence for LOCUS Compose profiles."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .attack_runner import (
    ATTACK_REPORT_VERSION,
    AttackReportError,
    validate_attack_report,
)
from .deployment import (
    BENCHMARK_VERSION,
    PERFORMANCE_RESULT_VERSION,
    DeploymentError,
    validate_benchmark_result,
    validate_performance_result,
)
from .experiment_metadata import (
    ExperimentMetadataError,
    validate_experiment_metadata,
)
from .redaction import OutputSafetyError, validate_public_output

PROFILE_EVIDENCE_VERSION = "LOCUS-compose-profile-evidence-v1"
TRACE_POLICY_VERSION = "LOCUS-profile-trace-policy-v1"

_TRACE_POLICY: dict[str, str] = {
    "core_dump_policy": "disabled-by-container-ulimit",
    "network_trace_policy": "not-collected",
    "retained_content": "aggregate-result-and-provenance-only",
    "service_log_policy": "scanned-then-discarded",
    "version": TRACE_POLICY_VERSION,
}


class ProfileEvidenceError(Exception):
    """A retained profile record is malformed, unsafe, or inconsistently bound."""


def _exact_dict(value: object, fields: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        raise ProfileEvidenceError(f"invalid {label}")
    return value


def trace_policy() -> dict[str, str]:
    """Return the fixed privacy-reviewed profile trace policy."""

    return dict(_TRACE_POLICY)


def validate_profile_evidence(value: object) -> dict[str, Any]:
    """Validate one exact aggregate-only profile evidence record."""

    evidence = _exact_dict(
        value,
        {"artifact", "metadata", "result", "trace_policy"},
        "profile evidence",
    )
    if evidence["artifact"] != PROFILE_EVIDENCE_VERSION:
        raise ProfileEvidenceError("unsupported profile evidence version")
    if evidence["trace_policy"] != _TRACE_POLICY:
        raise ProfileEvidenceError("invalid profile trace policy")
    try:
        metadata = validate_experiment_metadata(evidence["metadata"])
        result = evidence["result"]
        if not isinstance(result, dict):
            raise ProfileEvidenceError("invalid profile result")
        configuration = metadata["configuration"]
        if result.get("version") == ATTACK_REPORT_VERSION:
            validate_attack_report(result)
            if (
                metadata["profile"] != "compose-attack"
                or configuration.get("scenario") != result["scenario_id"]
                or configuration.get("topology") != "same-host-compose-5-party-v1"
            ):
                raise ProfileEvidenceError("attack evidence binding mismatch")
        elif result.get("artifact") == BENCHMARK_VERSION:
            validate_benchmark_result(result)
            if (
                metadata["profile"] != "compose-benchmark"
                or configuration.get("runs") != result["runs"]
                or configuration.get("selected") != result["selected"]
                or configuration.get("threshold") != 2
                or configuration.get("topology") != "same-host-compose-5-party-v1"
            ):
                raise ProfileEvidenceError("benchmark evidence binding mismatch")
        elif result.get("artifact") == PERFORMANCE_RESULT_VERSION:
            validate_performance_result(result)
            if (
                metadata["profile"] != "compose-performance"
                or configuration.get("block") != result["block"]
                or configuration.get("orchestration_seed")
                != result["orchestration_seed"]
                or configuration.get("scenario") != result["scenario_id"]
                or configuration.get("scenario_position") != result["scenario_position"]
                or configuration.get("topology") != "same-host-compose-5-party-v1"
                or metadata["randomness"]
                != {
                    "kind": "orchestrator-prng-v1",
                    "seed": result["orchestration_seed"],
                }
            ):
                raise ProfileEvidenceError("performance evidence binding mismatch")
        else:
            raise ProfileEvidenceError("unknown profile result")
        validate_public_output(evidence)
    except ProfileEvidenceError:
        raise
    except (
        AttackReportError,
        DeploymentError,
        ExperimentMetadataError,
        OutputSafetyError,
    ) as exc:
        raise ProfileEvidenceError("invalid profile evidence") from exc
    return evidence


def build_profile_evidence(
    *, metadata: dict[str, object], result: dict[str, object]
) -> dict[str, Any]:
    """Build and validate one aggregate-only profile evidence record."""

    return validate_profile_evidence(
        {
            "artifact": PROFILE_EVIDENCE_VERSION,
            "metadata": metadata,
            "result": result,
            "trace_policy": trace_policy(),
        }
    )


def serialize_profile_evidence(value: object) -> bytes:
    """Return one canonical newline-terminated evidence encoding."""

    evidence = validate_profile_evidence(value)
    return (
        json.dumps(
            evidence,
            allow_nan=False,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("ascii")


def write_profile_evidence(
    *, repo_root: Path, output_path: Path, evidence: object
) -> None:
    """Exclusively write, sync, reread, and revalidate one retained record."""

    serialized = serialize_profile_evidence(evidence)
    if output_path.suffix != ".json":
        raise ProfileEvidenceError("profile evidence output must be JSON")
    try:
        relative_path = (
            output_path.resolve().relative_to(repo_root.resolve()).as_posix()
        )
    except (OSError, ValueError) as exc:
        raise ProfileEvidenceError(
            "profile evidence output escaped repository"
        ) from exc
    metadata = validate_profile_evidence(evidence)["metadata"]
    if metadata["raw_output"] != {"path": relative_path, "retained": True}:
        raise ProfileEvidenceError("profile evidence output path mismatch")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with output_path.open("xb") as target:
            target.write(serialized)
            target.flush()
            os.fsync(target.fileno())
    except FileExistsError as exc:
        raise ProfileEvidenceError("profile evidence output already exists") from exc
    try:
        retained = output_path.read_bytes()
        decoded = json.loads(retained)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProfileEvidenceError("retained profile evidence is unreadable") from exc
    if retained != serialized or serialize_profile_evidence(decoded) != serialized:
        raise ProfileEvidenceError("retained profile evidence changed after write")
