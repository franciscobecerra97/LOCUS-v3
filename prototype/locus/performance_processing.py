"""Deterministic validation and processing for the frozen LOCUS P7 corpus."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import statistics
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from .deployment import PERFORMANCE_SCENARIOS
from .profile_evidence import (
    ProfileEvidenceError,
    serialize_profile_evidence,
    validate_profile_evidence,
)
from .redaction import OutputSafetyError, validate_public_output

PROCESSED_PERFORMANCE_VERSION = "LOCUS-performance-processed-v1"
PROCESSED_PERFORMANCE_VERSION_V2 = "LOCUS-performance-processed-v2"
BOOTSTRAP_ALGORITHM = "sha256-counter-index-v1"
QUANTILE_METHOD = "linear-type-7"
BLOCK_COUNT = 10
SAMPLES_PER_BLOCK = 3
SAMPLES_PER_SCENARIO = BLOCK_COUNT * SAMPLES_PER_BLOCK
DEFAULT_BOOTSTRAP_SEED = 20260723
DEFAULT_BOOTSTRAP_RESAMPLES = 10_000
MAX_RAW_EVIDENCE_BYTES = 1024 * 1024
MAX_PROCESSED_PERFORMANCE_BYTES = 4 * 1024 * 1024

_LATENCY_FIELDS = (
    "authorization",
    "client_setup",
    "cloud",
    "commitment",
    "finalization",
    "resolver",
    "response",
    "status_check",
    "total",
    "unclassified",
)
_BYTE_ROLES = ("authorization", "cloud", "resolver", "tpass")
_BYTE_DIRECTIONS = ("received", "sent")
_LOCK_PATHS = (
    "tpass-core/Cargo.lock",
    "tpass-python/Cargo.lock",
    "uv.lock",
)
_S3_IMAGE = (
    "chrislusf/seaweedfs:4.29@"
    "sha256:d47c7ee99fcb951351d7194915f4e3a5ea604a8e8871183d713907dec4fb9bf5"
)
_IDENTIFIER = re.compile(r"[a-z0-9][a-z0-9._-]{0,63}\Z")
_COMMIT = re.compile(r"[0-9a-f]{40}\Z")
_DIGEST = re.compile(r"[0-9a-f]{64}\Z")
_IMAGE_ID = re.compile(r"sha256:[0-9a-f]{64}\Z")
_RUNTIME_VERSION = re.compile(r"[A-Za-z0-9.+_-]{1,64}\Z")
_CORPUS_VERSION = re.compile(r"performance-v([12])\Z")


class PerformanceProcessingError(Exception):
    """The retained corpus or deterministic processed result is invalid."""


def _exact_dict(value: object, fields: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        raise PerformanceProcessingError(f"invalid {label}")
    return value


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise PerformanceProcessingError("duplicate JSON member")
        result[key] = value
    return result


def _relative_path(repo_root: Path, path: Path, *, label: str) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except (OSError, ValueError) as exc:
        raise PerformanceProcessingError(f"{label} escaped repository") from exc


def _regular_file_bytes(path: Path, *, limit: int, label: str) -> bytes:
    try:
        if path.is_symlink() or not path.is_file():
            raise PerformanceProcessingError(f"invalid {label}")
        size = path.stat().st_size
        if size < 1 or size > limit:
            raise PerformanceProcessingError(f"invalid {label}")
        value = path.read_bytes()
    except OSError as exc:
        raise PerformanceProcessingError(f"invalid {label}") from exc
    if len(value) != size:
        raise PerformanceProcessingError(f"unstable {label}")
    return value


def _read_raw_evidence(path: Path) -> tuple[dict[str, Any], bytes]:
    encoded = _regular_file_bytes(
        path, limit=MAX_RAW_EVIDENCE_BYTES, label="raw performance evidence"
    )
    try:
        decoded = json.loads(
            encoded.decode("ascii"),
            object_pairs_hook=_unique_object,
            parse_constant=lambda _value: (_ for _ in ()).throw(
                PerformanceProcessingError("non-finite JSON number")
            ),
        )
        evidence = validate_profile_evidence(decoded)
        canonical = serialize_profile_evidence(evidence)
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
        ProfileEvidenceError,
        OutputSafetyError,
    ) as exc:
        raise PerformanceProcessingError("invalid raw performance evidence") from exc
    if encoded != canonical:
        raise PerformanceProcessingError("raw performance evidence is noncanonical")
    return evidence, encoded


def _quantile(values: Iterable[float], probability: float) -> float:
    ordered = sorted(float(value) for value in values)
    if not ordered or not 0.0 <= probability <= 1.0:
        raise PerformanceProcessingError("invalid quantile input")
    if len(ordered) == 1:
        return ordered[0]
    rank = (len(ordered) - 1) * probability
    lower = math.floor(rank)
    upper = math.ceil(rank)
    if lower == upper:
        return ordered[lower]
    fraction = rank - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def _bootstrap_index(
    *,
    seed: int,
    label: str,
    replicate: int,
    draw: int,
    sample_count: int,
) -> int:
    digest = hashlib.sha256()
    digest.update(b"LOCUS/performance-bootstrap/v1\x00")
    digest.update(seed.to_bytes(8, "big"))
    digest.update(label.encode("ascii"))
    digest.update(b"\x00")
    digest.update(replicate.to_bytes(8, "big"))
    digest.update(draw.to_bytes(8, "big"))
    return int.from_bytes(digest.digest()[:8], "big") % sample_count


def _latency_summary(
    values: list[float],
    *,
    label: str,
    bootstrap_seed: int,
    bootstrap_resamples: int,
) -> dict[str, object]:
    if (
        not values
        or any(not math.isfinite(value) or value < 0 for value in values)
        or not 0 <= bootstrap_seed <= 2**64 - 1
        or not 1_000 <= bootstrap_resamples <= 100_000
    ):
        raise PerformanceProcessingError("invalid latency series")
    medians = []
    for replicate in range(bootstrap_resamples):
        sample = [
            values[
                _bootstrap_index(
                    seed=bootstrap_seed,
                    label=label,
                    replicate=replicate,
                    draw=draw,
                    sample_count=len(values),
                )
            ]
            for draw in range(len(values))
        ]
        medians.append(statistics.median(sample))
    return {
        "count": len(values),
        "max": max(values),
        "mean": statistics.fmean(values),
        "median": statistics.median(values),
        "median_ci95": {
            "lower": _quantile(medians, 0.025),
            "upper": _quantile(medians, 0.975),
        },
        "min": min(values),
        "p05": _quantile(values, 0.05),
        "p25": _quantile(values, 0.25),
        "p75": _quantile(values, 0.75),
        "p95": _quantile(values, 0.95),
    }


def _latency_distribution(
    values: Iterable[object],
    *,
    label: str,
    bootstrap_seed: int,
    bootstrap_resamples: int,
) -> dict[str, object]:
    series = []
    for value in values:
        if (
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not math.isfinite(value)
            or value < 0
        ):
            raise PerformanceProcessingError("invalid latency series")
        series.append(float(value))
    return {
        "series": series,
        "summary": _latency_summary(
            series,
            label=label,
            bootstrap_seed=bootstrap_seed,
            bootstrap_resamples=bootstrap_resamples,
        ),
    }


def _integer_distribution(values: Iterable[object]) -> dict[str, object]:
    series = []
    for value in values:
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise PerformanceProcessingError("invalid integer series")
        series.append(value)
    if not series:
        raise PerformanceProcessingError("invalid integer series")
    return {
        "series": series,
        "summary": {
            "count": len(series),
            "distinct": sorted(set(series)),
            "max": max(series),
            "min": min(series),
        },
    }


def _performance_corpus_version(
    *, repo_root: Path, root: Path, prefix: str, label: str
) -> str:
    relative = _relative_path(repo_root, root, label=label)
    expected_prefix = f"{prefix}/"
    if not relative.startswith(expected_prefix):
        raise PerformanceProcessingError(f"unexpected {label} path")
    version = relative.removeprefix(expected_prefix)
    if _CORPUS_VERSION.fullmatch(version) is None:
        raise PerformanceProcessingError(f"unsupported {label} version")
    return version


def _expected_raw_paths(corpus_version: str) -> list[str]:
    return [
        (f"experiments/raw/{corpus_version}/{block:02d}/{scenario_id}.json")
        for block in range(1, BLOCK_COUNT + 1)
        for scenario_id in PERFORMANCE_SCENARIOS
    ]


def _load_corpus(
    *, repo_root: Path, raw_root: Path
) -> tuple[dict[tuple[int, str], dict[str, Any]], list[dict[str, str]], str]:
    corpus_version = _performance_corpus_version(
        repo_root=repo_root,
        root=raw_root,
        prefix="experiments/raw",
        label="raw performance corpus",
    )
    expected_directories = {f"{block:02d}" for block in range(1, BLOCK_COUNT + 1)}
    try:
        if raw_root.is_symlink() or not raw_root.is_dir():
            raise PerformanceProcessingError("invalid raw performance corpus")
        entries = {entry.name: entry for entry in raw_root.iterdir()}
    except OSError as exc:
        raise PerformanceProcessingError("invalid raw performance corpus") from exc
    if set(entries) != expected_directories:
        raise PerformanceProcessingError("raw performance block set changed")

    records: dict[tuple[int, str], dict[str, Any]] = {}
    inputs = []
    expected_files = {f"{scenario_id}.json" for scenario_id in PERFORMANCE_SCENARIOS}
    for block in range(1, BLOCK_COUNT + 1):
        block_root = entries[f"{block:02d}"]
        try:
            if block_root.is_symlink() or not block_root.is_dir():
                raise PerformanceProcessingError("invalid raw performance block")
            block_entries = {entry.name: entry for entry in block_root.iterdir()}
        except OSError as exc:
            raise PerformanceProcessingError("invalid raw performance block") from exc
        if set(block_entries) != expected_files:
            raise PerformanceProcessingError("raw performance scenario set changed")
        for scenario_id in PERFORMANCE_SCENARIOS:
            path = block_entries[f"{scenario_id}.json"]
            evidence, encoded = _read_raw_evidence(path)
            actual_path = _relative_path(repo_root, path, label="raw evidence")
            metadata = evidence["metadata"]
            result = evidence["result"]
            if (
                metadata["evidence_class"] != "paper"
                or metadata["git"]["dirty"]
                or metadata["warnings"]
                or metadata["raw_output"] != {"path": actual_path, "retained": True}
                or result["block"] != block
                or result["scenario_id"] != scenario_id
            ):
                raise PerformanceProcessingError("raw performance binding changed")
            records[(block, scenario_id)] = evidence
            inputs.append(
                {
                    "path": actual_path,
                    "sha256": hashlib.sha256(encoded).hexdigest(),
                }
            )
    if [item["path"] for item in inputs] != _expected_raw_paths(corpus_version):
        raise PerformanceProcessingError("raw performance input order changed")
    return records, inputs, corpus_version


def _validate_corpus_consistency(
    records: dict[tuple[int, str], dict[str, Any]],
) -> dict[str, Any]:
    first = records[(1, PERFORMANCE_SCENARIOS[0])]
    first_metadata = first["metadata"]
    first_result = first["result"]
    source = {
        "experiment_id": first_metadata["experiment_id"],
        "git_commit": first_metadata["git"]["commit"],
        "host": first_metadata["host"],
        "locks": first_metadata["locks"],
        "runtime": first_result["runtime"],
    }
    for block in range(1, BLOCK_COUNT + 1):
        seed: int | None = None
        positions = set()
        for scenario_id in PERFORMANCE_SCENARIOS:
            evidence = records[(block, scenario_id)]
            metadata = evidence["metadata"]
            result = evidence["result"]
            if (
                metadata["experiment_id"] != source["experiment_id"]
                or metadata["git"] != {"commit": source["git_commit"], "dirty": False}
                or metadata["host"] != source["host"]
                or metadata["locks"] != source["locks"]
                or result["runtime"] != source["runtime"]
            ):
                raise PerformanceProcessingError(
                    "raw performance provenance is inconsistent"
                )
            if seed is None:
                seed = result["orchestration_seed"]
            elif result["orchestration_seed"] != seed:
                raise PerformanceProcessingError(
                    "raw performance block seed is inconsistent"
                )
            positions.add(result["scenario_position"])
        if positions != {1, 2, 3}:
            raise PerformanceProcessingError(
                "raw performance scenario positions are incomplete"
            )
    return source


def _scenario_processed(
    *,
    records: dict[tuple[int, str], dict[str, Any]],
    scenario_id: str,
    bootstrap_seed: int,
    bootstrap_resamples: int,
) -> dict[str, object]:
    results = [
        records[(block, scenario_id)]["result"] for block in range(1, BLOCK_COUNT + 1)
    ]
    samples = [sample for result in results for sample in result["samples"]]
    if len(samples) != SAMPLES_PER_SCENARIO:
        raise PerformanceProcessingError("performance sample count changed")
    expected_selected = (
        [2, 3] if scenario_id == "recover-one-party-unavailable-v1" else [1, 3]
    )
    expected_outcome = (
        "generic-rejection" if scenario_id == "recover-wrong-input-v1" else "success"
    )
    latency = {
        field: _latency_distribution(
            [sample["latency_ms"][field] for sample in samples],
            label=f"scenario/{scenario_id}/latency/{field}",
            bootstrap_seed=bootstrap_seed,
            bootstrap_resamples=bootstrap_resamples,
        )
        for field in _LATENCY_FIELDS
    }
    application_bytes = {
        role: {
            direction: _integer_distribution(
                [sample["application_bytes"][role][direction] for sample in samples]
            )
            for direction in _BYTE_DIRECTIONS
        }
        for role in _BYTE_ROLES
    }

    def storage_phase(phase: str) -> dict[str, object]:
        return {
            "client_bytes": _integer_distribution(
                [result["storage"][phase]["client_bytes"] for result in results]
            ),
            "party_bytes": [
                {
                    "party": party,
                    "values": _integer_distribution(
                        [
                            result["storage"][phase]["party_bytes"][party - 1]
                            for result in results
                        ]
                    ),
                }
                for party in range(1, 6)
            ],
        }

    return {
        "application_bytes": application_bytes,
        "latency_ms": latency,
        "orchestration_latency_ms": _latency_distribution(
            [result["orchestration_latency_ms"] for result in results],
            label=f"scenario/{scenario_id}/orchestration",
            bootstrap_seed=bootstrap_seed,
            bootstrap_resamples=bootstrap_resamples,
        ),
        "outcome": expected_outcome,
        "sample_count": len(samples),
        "selected": expected_selected,
        "storage": {
            "after": storage_phase("after"),
            "before": storage_phase("before"),
            "cloud_object_bytes": _integer_distribution(
                [result["storage"]["cloud_object_bytes"] for result in results]
            ),
        },
    }


def process_performance_corpus(
    *,
    repo_root: Path,
    raw_root: Path,
    bootstrap_seed: int = DEFAULT_BOOTSTRAP_SEED,
    bootstrap_resamples: int = DEFAULT_BOOTSTRAP_RESAMPLES,
) -> dict[str, Any]:
    """Validate all 30 retained records and return one deterministic result."""

    records, inputs, corpus_version = _load_corpus(
        repo_root=repo_root, raw_root=raw_root
    )
    source = _validate_corpus_consistency(records)
    if source["experiment_id"] != f"compose-{corpus_version}":
        raise PerformanceProcessingError(
            "raw performance experiment version does not match its corpus"
        )
    source["inputs"] = inputs
    enrollment_values = [
        records[(block, scenario_id)]["result"]["enrollment_latency_ms"]
        for block in range(1, BLOCK_COUNT + 1)
        for scenario_id in PERFORMANCE_SCENARIOS
    ]
    processed = {
        "artifact": (
            PROCESSED_PERFORMANCE_VERSION_V2
            if corpus_version == "performance-v2"
            else PROCESSED_PERFORMANCE_VERSION
        ),
        "enrollment_latency_ms": _latency_distribution(
            enrollment_values,
            label="enrollment",
            bootstrap_seed=bootstrap_seed,
            bootstrap_resamples=bootstrap_resamples,
        ),
        "processing": {
            "blocks": BLOCK_COUNT,
            "bootstrap": {
                "algorithm": BOOTSTRAP_ALGORITHM,
                "confidence": 0.95,
                "resamples": bootstrap_resamples,
                "seed": bootstrap_seed,
            },
            "quantile_method": QUANTILE_METHOD,
            "samples_per_scenario": SAMPLES_PER_SCENARIO,
            "scenarios": list(PERFORMANCE_SCENARIOS),
        },
        "scenarios": {
            scenario_id: _scenario_processed(
                records=records,
                scenario_id=scenario_id,
                bootstrap_seed=bootstrap_seed,
                bootstrap_resamples=bootstrap_resamples,
            )
            for scenario_id in PERFORMANCE_SCENARIOS
        },
        "source": source,
    }
    return validate_processed_performance(processed)


def _validate_latency_distribution(
    value: object,
    *,
    count: int,
    label: str,
    bootstrap_seed: int,
    bootstrap_resamples: int,
) -> dict[str, Any]:
    distribution = _exact_dict(value, {"series", "summary"}, label)
    series = distribution["series"]
    if not isinstance(series, list) or len(series) != count:
        raise PerformanceProcessingError(f"invalid {label}")
    expected = _latency_distribution(
        series,
        label=label,
        bootstrap_seed=bootstrap_seed,
        bootstrap_resamples=bootstrap_resamples,
    )
    if distribution != expected:
        raise PerformanceProcessingError(f"invalid {label}")
    return distribution


def _validate_integer_distribution(
    value: object, *, count: int, label: str
) -> dict[str, Any]:
    distribution = _exact_dict(value, {"series", "summary"}, label)
    series = distribution["series"]
    if not isinstance(series, list) or len(series) != count:
        raise PerformanceProcessingError(f"invalid {label}")
    if distribution != _integer_distribution(series):
        raise PerformanceProcessingError(f"invalid {label}")
    return distribution


def _validate_runtime(value: object) -> dict[str, Any]:
    runtime = _exact_dict(
        value,
        {
            "compose_version",
            "docker_engine_version",
            "reference_image_id",
            "s3_image",
        },
        "processed runtime",
    )
    if (
        not isinstance(runtime["compose_version"], str)
        or _RUNTIME_VERSION.fullmatch(runtime["compose_version"]) is None
        or not isinstance(runtime["docker_engine_version"], str)
        or _RUNTIME_VERSION.fullmatch(runtime["docker_engine_version"]) is None
        or not isinstance(runtime["reference_image_id"], str)
        or _IMAGE_ID.fullmatch(runtime["reference_image_id"]) is None
        or runtime["s3_image"] != _S3_IMAGE
    ):
        raise PerformanceProcessingError("invalid processed runtime")
    return runtime


def validate_processed_performance(value: object) -> dict[str, Any]:
    """Validate a deterministic processed result and every derived statistic."""

    processed = _exact_dict(
        value,
        {
            "artifact",
            "enrollment_latency_ms",
            "processing",
            "scenarios",
            "source",
        },
        "processed performance result",
    )
    if processed["artifact"] not in {
        PROCESSED_PERFORMANCE_VERSION,
        PROCESSED_PERFORMANCE_VERSION_V2,
    }:
        raise PerformanceProcessingError("unsupported processed performance version")
    processing = _exact_dict(
        processed["processing"],
        {
            "blocks",
            "bootstrap",
            "quantile_method",
            "samples_per_scenario",
            "scenarios",
        },
        "processing configuration",
    )
    bootstrap = _exact_dict(
        processing["bootstrap"],
        {"algorithm", "confidence", "resamples", "seed"},
        "bootstrap configuration",
    )
    if (
        processing["blocks"] != BLOCK_COUNT
        or processing["samples_per_scenario"] != SAMPLES_PER_SCENARIO
        or processing["scenarios"] != list(PERFORMANCE_SCENARIOS)
        or processing["quantile_method"] != QUANTILE_METHOD
        or bootstrap["algorithm"] != BOOTSTRAP_ALGORITHM
        or bootstrap["confidence"] != 0.95
        or not isinstance(bootstrap["seed"], int)
        or isinstance(bootstrap["seed"], bool)
        or not 0 <= bootstrap["seed"] <= 2**64 - 1
        or not isinstance(bootstrap["resamples"], int)
        or isinstance(bootstrap["resamples"], bool)
        or not 1_000 <= bootstrap["resamples"] <= 100_000
    ):
        raise PerformanceProcessingError("invalid processing configuration")
    seed = bootstrap["seed"]
    resamples = bootstrap["resamples"]
    _validate_latency_distribution(
        processed["enrollment_latency_ms"],
        count=BLOCK_COUNT * len(PERFORMANCE_SCENARIOS),
        label="enrollment",
        bootstrap_seed=seed,
        bootstrap_resamples=resamples,
    )

    source = _exact_dict(
        processed["source"],
        {
            "experiment_id",
            "git_commit",
            "host",
            "inputs",
            "locks",
            "runtime",
        },
        "processed source",
    )
    if (
        not isinstance(source["experiment_id"], str)
        or _IDENTIFIER.fullmatch(source["experiment_id"]) is None
        or not isinstance(source["git_commit"], str)
        or _COMMIT.fullmatch(source["git_commit"]) is None
    ):
        raise PerformanceProcessingError("invalid processed source")
    host = _exact_dict(
        source["host"],
        {"id", "machine", "processor", "python", "release", "system"},
        "processed host",
    )
    if (
        not isinstance(host["id"], str)
        or _IDENTIFIER.fullmatch(host["id"]) is None
        or host["id"] == "unlabeled-local-host"
        or any(
            not isinstance(host[field], str)
            or len(host[field]) > 256
            or (field != "processor" and not host[field])
            or any(character in host[field] for character in "\r\n\x00")
            for field in ("machine", "processor", "python", "release", "system")
        )
    ):
        raise PerformanceProcessingError("invalid processed host")
    locks = _exact_dict(source["locks"], set(_LOCK_PATHS), "processed locks")
    if any(
        not isinstance(digest, str) or _DIGEST.fullmatch(digest) is None
        for digest in locks.values()
    ):
        raise PerformanceProcessingError("invalid processed locks")
    _validate_runtime(source["runtime"])
    inputs = source["inputs"]
    if not isinstance(inputs, list) or len(inputs) != BLOCK_COUNT * len(
        PERFORMANCE_SCENARIOS
    ):
        raise PerformanceProcessingError("invalid processed inputs")
    first_input = inputs[0] if inputs else None
    if not isinstance(first_input, dict) or not isinstance(
        first_input.get("path"), str
    ):
        raise PerformanceProcessingError("invalid processed input")
    match = re.fullmatch(
        r"experiments/raw/(performance-v[12])/\d{2}/[a-z0-9._-]+\.json",
        first_input["path"],
    )
    if match is None:
        raise PerformanceProcessingError("invalid processed input")
    corpus_version = match.group(1)
    expected_artifact = (
        PROCESSED_PERFORMANCE_VERSION_V2
        if corpus_version == "performance-v2"
        else PROCESSED_PERFORMANCE_VERSION
    )
    if processed["artifact"] != expected_artifact:
        raise PerformanceProcessingError(
            "processed artifact version does not match its corpus"
        )
    if source["experiment_id"] != f"compose-{corpus_version}":
        raise PerformanceProcessingError(
            "processed experiment version does not match its corpus"
        )
    expected_paths = _expected_raw_paths(corpus_version)
    for expected_path, raw_input in zip(expected_paths, inputs, strict=True):
        item = _exact_dict(raw_input, {"path", "sha256"}, "processed input")
        if (
            item["path"] != expected_path
            or not isinstance(item["sha256"], str)
            or _DIGEST.fullmatch(item["sha256"]) is None
        ):
            raise PerformanceProcessingError("invalid processed input")

    scenarios = _exact_dict(
        processed["scenarios"], set(PERFORMANCE_SCENARIOS), "processed scenarios"
    )
    for scenario_id in PERFORMANCE_SCENARIOS:
        scenario = _exact_dict(
            scenarios[scenario_id],
            {
                "application_bytes",
                "latency_ms",
                "orchestration_latency_ms",
                "outcome",
                "sample_count",
                "selected",
                "storage",
            },
            "processed scenario",
        )
        expected_selected = (
            [2, 3] if scenario_id == "recover-one-party-unavailable-v1" else [1, 3]
        )
        expected_outcome = (
            "generic-rejection"
            if scenario_id == "recover-wrong-input-v1"
            else "success"
        )
        if (
            scenario["sample_count"] != SAMPLES_PER_SCENARIO
            or scenario["selected"] != expected_selected
            or scenario["outcome"] != expected_outcome
        ):
            raise PerformanceProcessingError("invalid processed scenario")
        latency = _exact_dict(
            scenario["latency_ms"], set(_LATENCY_FIELDS), "processed latency"
        )
        for field in _LATENCY_FIELDS:
            _validate_latency_distribution(
                latency[field],
                count=SAMPLES_PER_SCENARIO,
                label=f"scenario/{scenario_id}/latency/{field}",
                bootstrap_seed=seed,
                bootstrap_resamples=resamples,
            )
        _validate_latency_distribution(
            scenario["orchestration_latency_ms"],
            count=BLOCK_COUNT,
            label=f"scenario/{scenario_id}/orchestration",
            bootstrap_seed=seed,
            bootstrap_resamples=resamples,
        )
        application_bytes = _exact_dict(
            scenario["application_bytes"],
            set(_BYTE_ROLES),
            "processed application bytes",
        )
        for role in _BYTE_ROLES:
            directions = _exact_dict(
                application_bytes[role],
                set(_BYTE_DIRECTIONS),
                "processed byte directions",
            )
            for direction in _BYTE_DIRECTIONS:
                _validate_integer_distribution(
                    directions[direction],
                    count=SAMPLES_PER_SCENARIO,
                    label="processed byte series",
                )
        storage = _exact_dict(
            scenario["storage"],
            {"after", "before", "cloud_object_bytes"},
            "processed storage",
        )
        _validate_integer_distribution(
            storage["cloud_object_bytes"],
            count=BLOCK_COUNT,
            label="processed cloud storage",
        )
        for phase in ("before", "after"):
            phase_storage = _exact_dict(
                storage[phase],
                {"client_bytes", "party_bytes"},
                "processed storage phase",
            )
            _validate_integer_distribution(
                phase_storage["client_bytes"],
                count=BLOCK_COUNT,
                label="processed client storage",
            )
            party_bytes = phase_storage["party_bytes"]
            if not isinstance(party_bytes, list) or len(party_bytes) != 5:
                raise PerformanceProcessingError("invalid processed party storage")
            for party, raw_party in enumerate(party_bytes, start=1):
                item = _exact_dict(
                    raw_party, {"party", "values"}, "processed party storage"
                )
                if item["party"] != party:
                    raise PerformanceProcessingError("invalid processed party storage")
                _validate_integer_distribution(
                    item["values"],
                    count=BLOCK_COUNT,
                    label="processed party storage values",
                )
    try:
        validate_public_output(processed)
    except OutputSafetyError as exc:
        raise PerformanceProcessingError(
            "processed performance output is unsafe"
        ) from exc
    return processed


def serialize_processed_performance(value: object) -> bytes:
    """Return one canonical newline-terminated processed-result encoding."""

    processed = validate_processed_performance(value)
    return (
        json.dumps(
            processed,
            allow_nan=False,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("ascii")


def read_processed_performance(path: Path) -> tuple[dict[str, Any], bytes]:
    """Read one canonical processed artifact from a bounded regular file."""

    encoded = _regular_file_bytes(
        path,
        limit=MAX_PROCESSED_PERFORMANCE_BYTES,
        label="processed performance artifact",
    )
    try:
        decoded = json.loads(
            encoded.decode("ascii"),
            object_pairs_hook=_unique_object,
            parse_constant=lambda _value: (_ for _ in ()).throw(
                PerformanceProcessingError("non-finite JSON number")
            ),
        )
        processed = validate_processed_performance(decoded)
        canonical = serialize_processed_performance(processed)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PerformanceProcessingError(
            "invalid processed performance artifact"
        ) from exc
    if encoded != canonical:
        raise PerformanceProcessingError(
            "processed performance artifact is noncanonical"
        )
    return processed, encoded


def write_processed_performance(
    *, repo_root: Path, output_path: Path, processed: object
) -> None:
    """Exclusively publish one validated processed result below its fixed root."""

    relative_path = _relative_path(repo_root, output_path, label="processed output")
    parts = relative_path.split("/")
    if (
        output_path.suffix != ".json"
        or len(parts) != 4
        or parts[:2] != ["experiments", "processed"]
        or _CORPUS_VERSION.fullmatch(parts[2]) is None
    ):
        raise PerformanceProcessingError("invalid processed performance output path")
    inputs = validate_processed_performance(processed)["source"]["inputs"]
    raw_version = inputs[0]["path"].split("/")[2]
    if parts[2] != raw_version:
        raise PerformanceProcessingError(
            "processed output version does not match its corpus"
        )
    serialized = serialize_processed_performance(processed)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with output_path.open("xb") as target:
            target.write(serialized)
            target.flush()
            os.fsync(target.fileno())
    except FileExistsError as exc:
        raise PerformanceProcessingError(
            "processed performance output already exists"
        ) from exc
    try:
        retained = output_path.read_bytes()
        decoded, reread = read_processed_performance(output_path)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PerformanceProcessingError(
            "processed performance output is unreadable"
        ) from exc
    if (
        retained != serialized
        or reread != serialized
        or serialize_processed_performance(decoded) != serialized
    ):
        raise PerformanceProcessingError(
            "processed performance output changed after write"
        )
