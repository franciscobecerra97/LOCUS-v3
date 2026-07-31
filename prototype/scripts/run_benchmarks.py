from __future__ import annotations

import argparse
import json
import platform
import statistics
import sys
import time
from pathlib import Path

import cryptography
from cryptography.hazmat.backends.openssl import backend as openssl_backend

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from locus.codec import encoded_size
from locus.core import enroll, recover
from locus.experiment_metadata import (
    ExperimentMetadataError,
    collect_experiment_metadata,
    utc_timestamp,
)
from locus.redaction import validate_public_output
from locus.tpass import NativeTpassBackend, TpassConcreteBackend, TpassSimulator

ROOT = Path(__file__).resolve().parents[2]


def make_cues(count: int) -> list[dict]:
    cues = []
    for idx in range(count):
        cues.append(
            {
                "location": {
                    "provider": "local",
                    "record_id": f"place-{idx:03d}",
                    "name": f"Synthetic Place {idx}",
                    "country": "ZZ",
                },
                "person": {
                    "provider": "local",
                    "record_id": f"person-{idx:03d}",
                    "label": f"Synthetic Person {idx}",
                },
            }
        )
    return cues


def timed(callable_obj):
    start = time.perf_counter()
    result = callable_obj()
    elapsed = time.perf_counter() - start
    return result, elapsed


def summarize(values: list[float]) -> dict:
    return {
        "min_ms": min(values) * 1000,
        "median_ms": statistics.median(values) * 1000,
        "mean_ms": statistics.mean(values) * 1000,
        "max_ms": max(values) * 1000,
    }


def make_backend(name: str):
    if name == "native":
        return NativeTpassBackend()
    if name == "simulator":
        return TpassSimulator()
    if name == "concrete":
        return TpassConcreteBackend()
    raise ValueError(f"unknown backend: {name}")


def run_config(
    threshold: int, parties: int, cue_count: int, runs: int, backend_name: str
) -> dict:
    enroll_times = []
    recover_times = []
    backup_bytes = []
    total_party_bytes = []
    recovery_message_bytes = []
    private_key = b"synthetic-private-key-material"
    cues = make_cues(cue_count)
    backend_label = ""
    for _ in range(runs):
        backend = make_backend(backend_name)
        enrollment, enroll_time = timed(
            lambda backend=backend: enroll(
                user_id="synthetic-user",
                private_key=private_key,
                cues=cues,
                threshold=threshold,
                parties=parties,
                tpass=backend,
            )
        )
        recovered, recover_time = timed(
            lambda enrollment=enrollment, backend=backend: recover(
                user_id="synthetic-user",
                backup=enrollment.backup,
                party_records=enrollment.parties[:threshold],
                cues=cues,
                tpass=backend,
            )
        )
        if recovered != private_key:
            raise RuntimeError("benchmark recovery mismatch")
        enroll_times.append(enroll_time)
        recover_times.append(recover_time)
        backup_bytes.append(enrollment.metrics["backup_bytes"])
        total_party_bytes.append(enrollment.metrics["total_party_record_bytes"])
        recovery_message_bytes.append(
            sum(
                encoded_size(record["tpass_state"])
                for record in enrollment.parties[:threshold]
            )
        )
        backend_label = enrollment.metrics["backend"]
    return {
        "threshold": threshold,
        "parties": parties,
        "cue_count": cue_count,
        "runs": runs,
        "backend": backend_label,
        "enroll_time": summarize(enroll_times),
        "recover_time": summarize(recover_times),
        "backup_bytes_mean": statistics.mean(backup_bytes),
        "total_party_record_bytes_mean": statistics.mean(total_party_bytes),
        "recovery_message_bytes_mean": statistics.mean(recovery_message_bytes),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run LOCUS reference-prototype benchmarks."
    )
    parser.add_argument("--runs", type=int, default=30, help="runs per configuration")
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="optional JSON output path; parent directories are created",
    )
    parser.add_argument(
        "--backend",
        choices=("native", "simulator", "concrete"),
        default="native",
        help="TPASS backend to benchmark",
    )
    parser.add_argument(
        "--evidence-class",
        choices=("development", "paper"),
        default="development",
        help="paper mode requires clean, labeled, retained provenance",
    )
    parser.add_argument(
        "--experiment-id",
        default="reference-benchmark",
        help="stable lowercase experiment identifier",
    )
    parser.add_argument(
        "--host-id",
        default=None,
        help="pseudonymous host label required for paper evidence",
    )
    args = parser.parse_args()
    if args.runs < 1:
        raise SystemExit("--runs must be at least 1")
    started_at = utc_timestamp()
    matrix = [(2, 3), (3, 5), (5, 9)]
    cue_counts = [1, 2, 3, 5]
    results = [
        run_config(threshold, parties, cue_count, args.runs, args.backend)
        for threshold, parties in matrix
        for cue_count in cue_counts
    ]
    finished_at = utc_timestamp()
    try:
        metadata = collect_experiment_metadata(
            repo_root=ROOT,
            experiment_id=args.experiment_id,
            profile="reference-benchmark",
            evidence_class=args.evidence_class,
            configuration={
                "backend": args.backend,
                "cue_counts": cue_counts,
                "matrix": [list(item) for item in matrix],
                "runs_per_configuration": args.runs,
            },
            randomness_kind="os-csprng",
            seed=None,
            started_at=started_at,
            finished_at=finished_at,
            output_path=args.out,
            host_id=args.host_id,
        )
    except ExperimentMetadataError as exc:
        raise SystemExit(str(exc)) from exc
    payload = {
        "generated_at": finished_at,
        "artifact": "LOCUS reference benchmark",
        "backend_requested": args.backend,
        "metadata": metadata,
        "warning": "research prototype; not production cryptography",
        "platform": {
            "python": sys.version,
            "cryptography": cryptography.__version__,
            "openssl": openssl_backend.openssl_version_text(),
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "processor": platform.processor(),
        },
        "results": results,
    }
    validate_public_output(payload)
    output = json.dumps(payload, indent=2, sort_keys=True)
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(output + "\n", encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
