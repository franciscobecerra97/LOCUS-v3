"""Versioned, privacy-aware provenance for LOCUS experiment outputs."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .redaction import OutputSafetyError, validate_public_output

METADATA_VERSION = "LOCUS-experiment-metadata-v1"
UNLABELED_HOST = "unlabeled-local-host"

_IDENTIFIER = re.compile(r"[a-z0-9][a-z0-9._-]{0,63}\Z")
_COMMIT = re.compile(r"[0-9a-f]{40}\Z")
_DIGEST = re.compile(r"[0-9a-f]{64}\Z")
_LOCK_PATHS = (
    "uv.lock",
    "tpass-core/Cargo.lock",
    "tpass-python/Cargo.lock",
)


class ExperimentMetadataError(Exception):
    """Experiment provenance is incomplete, unsafe, or noncanonical."""


def utc_timestamp() -> str:
    """Return one timezone-explicit ISO 8601 UTC timestamp."""

    return datetime.now(UTC).isoformat()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as source:
            while block := source.read(1024 * 1024):
                digest.update(block)
    except OSError as exc:
        raise ExperimentMetadataError(
            "required dependency lock is unavailable"
        ) from exc
    return digest.hexdigest()


def _git_state(repo_root: Path) -> tuple[str, bool]:
    manifest_path = repo_root / "artifact_manifest.json"
    if not (repo_root / ".git").exists() and manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="ascii"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ExperimentMetadataError("artifact provenance is unavailable") from exc
        if (
            not isinstance(manifest, dict)
            or set(manifest) != {"artifact", "entries", "source_commit"}
            or manifest["artifact"] != "LOCUS-anonymous-artifact-v1"
            or not isinstance(manifest["source_commit"], str)
            or _COMMIT.fullmatch(manifest["source_commit"]) is None
        ):
            raise ExperimentMetadataError("artifact provenance is invalid")
        return manifest["source_commit"], False

    git_environment = os.environ.copy()
    git_environment.update(
        {
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_OPTIONAL_LOCKS": "0",
        }
    )

    def git(*arguments: str) -> subprocess.CompletedProcess[str]:
        try:
            return subprocess.run(
                ["git", *arguments],
                cwd=repo_root,
                env=git_environment,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=5,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ExperimentMetadataError("git provenance is unavailable") from exc

    revision = git("rev-parse", "--verify", "HEAD")
    status = git("status", "--porcelain=v1", "--untracked-files=normal")
    if revision.returncode != 0 or status.returncode != 0:
        raise ExperimentMetadataError("git provenance is unavailable")
    return revision.stdout.strip().lower(), bool(status.stdout)


def _relative_output(repo_root: Path, output_path: Path | None) -> str | None:
    if output_path is None:
        return None
    try:
        return output_path.resolve().relative_to(repo_root.resolve()).as_posix()
    except (OSError, ValueError) as exc:
        raise ExperimentMetadataError(
            "experiment output must stay inside the repository"
        ) from exc


def _timestamp(value: object, label: str) -> datetime:
    if not isinstance(value, str) or not value or len(value) > 64:
        raise ExperimentMetadataError(f"invalid {label}")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ExperimentMetadataError(f"invalid {label}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != UTC.utcoffset(parsed):
        raise ExperimentMetadataError(f"invalid {label}")
    return parsed


def _exact_dict(value: object, fields: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        raise ExperimentMetadataError(f"invalid {label}")
    return value


def _short_text(value: object, label: str, *, allow_empty: bool = False) -> str:
    if (
        not isinstance(value, str)
        or (not value and not allow_empty)
        or len(value) > 256
        or any(character in value for character in "\r\n\x00")
    ):
        raise ExperimentMetadataError(f"invalid {label}")
    return value


def validate_experiment_metadata(value: object) -> dict[str, Any]:
    """Validate and return one exact experiment metadata object."""

    metadata = _exact_dict(
        value,
        {
            "configuration",
            "evidence_class",
            "experiment_id",
            "finished_at",
            "git",
            "host",
            "locks",
            "profile",
            "randomness",
            "raw_output",
            "started_at",
            "version",
            "warnings",
        },
        "experiment metadata",
    )
    if metadata["version"] != METADATA_VERSION:
        raise ExperimentMetadataError("unsupported experiment metadata version")
    for field in ("experiment_id", "profile"):
        item = metadata[field]
        if not isinstance(item, str) or _IDENTIFIER.fullmatch(item) is None:
            raise ExperimentMetadataError(f"invalid {field}")
    evidence_class = metadata["evidence_class"]
    if evidence_class not in {"development", "paper"}:
        raise ExperimentMetadataError("invalid evidence_class")

    started = _timestamp(metadata["started_at"], "started_at")
    finished = _timestamp(metadata["finished_at"], "finished_at")
    if finished < started:
        raise ExperimentMetadataError("experiment timestamps are reversed")

    git = _exact_dict(metadata["git"], {"commit", "dirty"}, "git provenance")
    if not isinstance(git["commit"], str) or _COMMIT.fullmatch(git["commit"]) is None:
        raise ExperimentMetadataError("invalid git commit")
    if not isinstance(git["dirty"], bool):
        raise ExperimentMetadataError("invalid git dirty flag")

    locks = _exact_dict(metadata["locks"], set(_LOCK_PATHS), "lock provenance")
    if any(
        not isinstance(item, str) or _DIGEST.fullmatch(item) is None
        for item in locks.values()
    ):
        raise ExperimentMetadataError("invalid dependency lock digest")

    host = _exact_dict(
        metadata["host"],
        {"id", "machine", "processor", "python", "release", "system"},
        "host provenance",
    )
    for field in ("id", "machine", "python", "release", "system"):
        _short_text(host[field], f"host {field}")
    _short_text(host["processor"], "host processor", allow_empty=True)
    if _IDENTIFIER.fullmatch(host["id"]) is None:
        raise ExperimentMetadataError("invalid host id")

    configuration = metadata["configuration"]
    if not isinstance(configuration, dict):
        raise ExperimentMetadataError("invalid experiment configuration")
    try:
        json.dumps(configuration, allow_nan=False, sort_keys=True)
        validate_public_output(configuration)
    except (OutputSafetyError, TypeError, ValueError) as exc:
        raise ExperimentMetadataError("invalid experiment configuration") from exc

    randomness = _exact_dict(
        metadata["randomness"], {"kind", "seed"}, "randomness provenance"
    )
    if randomness["kind"] == "os-csprng":
        if randomness["seed"] is not None:
            raise ExperimentMetadataError("OS CSPRNG runs must not claim a seed")
    elif randomness["kind"] == "orchestrator-prng-v1":
        if (
            not isinstance(randomness["seed"], int)
            or isinstance(randomness["seed"], bool)
            or not 0 <= randomness["seed"] <= 2**64 - 1
        ):
            raise ExperimentMetadataError("invalid orchestrator seed")
    else:
        raise ExperimentMetadataError("invalid randomness kind")

    raw_output = _exact_dict(
        metadata["raw_output"], {"path", "retained"}, "raw output provenance"
    )
    if not isinstance(raw_output["retained"], bool):
        raise ExperimentMetadataError("invalid raw output retention flag")
    if raw_output["retained"]:
        path = _short_text(raw_output["path"], "raw output path")
        path_parts = Path(path).parts
        if (
            Path(path).is_absolute()
            or re.match(r"^[A-Za-z]:/", path) is not None
            or path.startswith("//")
            or ".." in path_parts
            or "\\" in path
        ):
            raise ExperimentMetadataError("raw output path must be repository-relative")
    elif raw_output["path"] is not None:
        raise ExperimentMetadataError("unretained output must not claim a path")

    warnings = metadata["warnings"]
    allowed_warnings = {"dirty-worktree", "unlabeled-host", "unretained-output"}
    if (
        not isinstance(warnings, list)
        or warnings != sorted(set(warnings))
        or any(item not in allowed_warnings for item in warnings)
    ):
        raise ExperimentMetadataError("invalid experiment warnings")

    if evidence_class == "paper":
        if git["dirty"] or host["id"] == UNLABELED_HOST or not raw_output["retained"]:
            raise ExperimentMetadataError("paper evidence provenance is incomplete")
        if not str(raw_output["path"]).startswith("experiments/raw/"):
            raise ExperimentMetadataError("paper evidence must use experiments/raw")
        if warnings:
            raise ExperimentMetadataError("paper evidence must not contain warnings")
    return metadata


def collect_experiment_metadata(
    *,
    repo_root: Path,
    experiment_id: str,
    profile: str,
    evidence_class: str,
    configuration: dict[str, object],
    randomness_kind: str,
    seed: int | None,
    started_at: str,
    finished_at: str,
    output_path: Path | None,
    host_id: str | None = None,
) -> dict[str, Any]:
    """Collect one validated metadata record without host-identifying names."""

    commit, dirty = _git_state(repo_root)
    relative_output = _relative_output(repo_root, output_path)
    selected_host_id = host_id or os.environ.get("LOCUS_EXPERIMENT_HOST_ID")
    selected_host_id = selected_host_id or UNLABELED_HOST
    warnings = []
    if dirty:
        warnings.append("dirty-worktree")
    if selected_host_id == UNLABELED_HOST:
        warnings.append("unlabeled-host")
    if relative_output is None:
        warnings.append("unretained-output")
    metadata: dict[str, Any] = {
        "configuration": configuration,
        "evidence_class": evidence_class,
        "experiment_id": experiment_id,
        "finished_at": finished_at,
        "git": {"commit": commit, "dirty": dirty},
        "host": {
            "id": selected_host_id,
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python": sys.version,
            "release": platform.release(),
            "system": platform.system(),
        },
        "locks": {
            relative_path: _sha256(repo_root / relative_path)
            for relative_path in _LOCK_PATHS
        },
        "profile": profile,
        "randomness": {"kind": randomness_kind, "seed": seed},
        "raw_output": {
            "path": relative_output,
            "retained": relative_output is not None,
        },
        "started_at": started_at,
        "version": METADATA_VERSION,
        "warnings": sorted(warnings),
    }
    return validate_experiment_metadata(metadata)
