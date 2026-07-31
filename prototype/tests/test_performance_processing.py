from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

from locus.deployment import PERFORMANCE_SCENARIOS, performance_scenario_order
from locus.performance_processing import (
    PerformanceProcessingError,
    process_performance_corpus,
    read_processed_performance,
    serialize_processed_performance,
    validate_processed_performance,
    write_processed_performance,
)
from locus.profile_evidence import (
    build_profile_evidence,
    serialize_profile_evidence,
)

_S3_IMAGE = (
    "chrislusf/seaweedfs:4.29@"
    "sha256:d47c7ee99fcb951351d7194915f4e3a5ea604a8e8871183d713907dec4fb9bf5"
)


def _sample_result(*, block: int, scenario_id: str, seed: int) -> dict[str, object]:
    order = performance_scenario_order(seed)
    selected = [2, 3] if scenario_id == "recover-one-party-unavailable-v1" else [1, 3]
    outcome = (
        "generic-rejection" if scenario_id == "recover-wrong-input-v1" else "success"
    )
    samples = []
    for measurement in range(1, 4):
        base = float(block * 10 + measurement)
        latency = {
            "authorization": base + 0.1,
            "client_setup": base + 0.2,
            "cloud": base + 0.3,
            "commitment": base + 0.4,
            "finalization": base + 0.5,
            "resolver": base + 0.6,
            "response": base + 0.7,
            "status_check": base + 0.8,
            "unclassified": base + 0.9,
        }
        latency["total"] = sum(latency.values())
        samples.append(
            {
                "application_bytes": {
                    role: {
                        "received": block * 100 + measurement * 10 + role_index,
                        "sent": block * 50 + measurement * 10 + role_index,
                    }
                    for role_index, role in enumerate(
                        ("authorization", "cloud", "resolver", "tpass"), start=1
                    )
                },
                "artifact": "LOCUS-performance-client-samples-v1",
                "attempts": {
                    "after": measurement + 1,
                    "before": measurement,
                },
                "latency_ms": latency,
                "measurement": measurement,
                "outcome": outcome,
                "selected": selected,
                "status": "ok",
            }
        )
    storage_before: dict[str, Any] = {
        "artifact": "LOCUS-storage-metric-v1",
        "client_bytes": 1000 + block,
        "party_bytes": [2000 + block + party for party in range(1, 6)],
        "status": "ok",
    }
    storage_after = copy.deepcopy(storage_before)
    storage_after["client_bytes"] += 10
    storage_after["party_bytes"] = [
        value + block for value in storage_before["party_bytes"]
    ]
    return {
        "artifact": "LOCUS-compose-performance-result-v1",
        "block": block,
        "cleanup": "passed",
        "configuration": {
            "alternate_selected": [2, 3],
            "authorization_membership": 5,
            "authorization_quorum": 4,
            "baseline_selected": [1, 3],
            "measurements": 3,
            "threshold": 2,
            "topology": "same-host-compose-5-party-v1",
            "tpass_parties": 3,
            "warmups": 1,
        },
        "enrollment_latency_ms": float(100 + block),
        "orchestration_latency_ms": float(1000 + block),
        "orchestration_seed": seed,
        "output_scan": "passed",
        "profile": "performance",
        "runtime": {
            "compose_version": "2.39.1",
            "docker_engine_version": "28.3.2",
            "reference_image_id": f"sha256:{'c' * 64}",
            "s3_image": _S3_IMAGE,
        },
        "samples": samples,
        "scenario_id": scenario_id,
        "scenario_position": order.index(scenario_id) + 1,
        "status": "ok",
        "storage": {
            "after": storage_after,
            "before": storage_before,
            "cloud_object_bytes": 800 + block,
        },
    }


def _sample_metadata(
    *,
    block: int,
    scenario_id: str,
    scenario_position: int,
    seed: int,
    output_path: str,
    corpus_version: str = "performance-v1",
) -> dict[str, object]:
    digest = "a" * 64
    return {
        "configuration": {
            "block": block,
            "orchestration_seed": seed,
            "scenario": scenario_id,
            "scenario_position": scenario_position,
            "topology": "same-host-compose-5-party-v1",
        },
        "evidence_class": "paper",
        "experiment_id": f"compose-{corpus_version}",
        "finished_at": "2026-07-23T10:00:01+00:00",
        "git": {"commit": "b" * 40, "dirty": False},
        "host": {
            "id": "paper-host-a",
            "machine": "x86_64",
            "processor": "synthetic",
            "python": "3.12.13",
            "release": "test",
            "system": "TestOS",
        },
        "locks": {
            "tpass-core/Cargo.lock": digest,
            "tpass-python/Cargo.lock": digest,
            "uv.lock": digest,
        },
        "profile": "compose-performance",
        "randomness": {"kind": "orchestrator-prng-v1", "seed": seed},
        "raw_output": {"path": output_path, "retained": True},
        "started_at": "2026-07-23T10:00:00+00:00",
        "version": "LOCUS-experiment-metadata-v1",
        "warnings": [],
    }


def write_performance_corpus_fixture(
    root: Path, *, corpus_version: str = "performance-v1"
) -> Path:
    raw_root = root / "experiments" / "raw" / corpus_version
    for block in range(1, 11):
        seed = 20260723 + block
        for scenario_id in PERFORMANCE_SCENARIOS:
            relative = (
                f"experiments/raw/{corpus_version}/{block:02d}/{scenario_id}.json"
            )
            result = _sample_result(
                block=block,
                scenario_id=scenario_id,
                seed=seed,
            )
            scenario_position = result["scenario_position"]
            assert isinstance(scenario_position, int)
            evidence = build_profile_evidence(
                metadata=_sample_metadata(
                    block=block,
                    scenario_id=scenario_id,
                    scenario_position=scenario_position,
                    seed=seed,
                    output_path=relative,
                    corpus_version=corpus_version,
                ),
                result=result,
            )
            output = root / relative
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(serialize_profile_evidence(evidence))
    return raw_root


class PerformanceProcessingTests(unittest.TestCase):
    def test_complete_corpus_is_deterministic_and_summary_bound(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            raw_root = write_performance_corpus_fixture(root)
            processed = process_performance_corpus(
                repo_root=root,
                raw_root=raw_root,
                bootstrap_seed=42,
                bootstrap_resamples=1000,
            )
            self.assertEqual(validate_processed_performance(processed), processed)
            self.assertEqual(processed["processing"]["samples_per_scenario"], 30)
            self.assertEqual(len(processed["source"]["inputs"]), 30)
            success = processed["scenarios"]["enroll-recover-success-v1"]
            self.assertEqual(success["latency_ms"]["total"]["summary"]["count"], 30)
            self.assertEqual(
                serialize_processed_performance(processed),
                serialize_processed_performance(
                    process_performance_corpus(
                        repo_root=root,
                        raw_root=raw_root,
                        bootstrap_seed=42,
                        bootstrap_resamples=1000,
                    )
                ),
            )

            changed = copy.deepcopy(processed)
            changed["scenarios"]["enroll-recover-success-v1"]["latency_ms"]["total"][
                "summary"
            ]["median"] = 0
            with self.assertRaises(PerformanceProcessingError):
                validate_processed_performance(changed)

    def test_missing_extra_noncanonical_and_mixed_provenance_fail_closed(self) -> None:
        mutations = (
            "missing",
            "extra",
            "noncanonical",
            "duplicate-member",
            "mixed-commit",
            "mixed-host",
            "mixed-lock",
            "mixed-runtime",
            "wrong-raw-path",
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                with tempfile.TemporaryDirectory() as temporary:
                    root = Path(temporary)
                    raw_root = write_performance_corpus_fixture(root)
                    target = raw_root / "01" / "enroll-recover-success-v1.json"
                    if mutation == "missing":
                        target.unlink()
                    elif mutation == "extra":
                        (raw_root / "unexpected.json").write_text(
                            "{}", encoding="ascii"
                        )
                    else:
                        decoded = json.loads(target.read_text(encoding="ascii"))
                        if mutation == "mixed-commit":
                            decoded["metadata"]["git"]["commit"] = "d" * 40
                            target.write_bytes(serialize_profile_evidence(decoded))
                        elif mutation == "mixed-host":
                            decoded["metadata"]["host"]["id"] = "paper-host-b"
                            target.write_bytes(serialize_profile_evidence(decoded))
                        elif mutation == "mixed-lock":
                            decoded["metadata"]["locks"]["uv.lock"] = "e" * 64
                            target.write_bytes(serialize_profile_evidence(decoded))
                        elif mutation == "mixed-runtime":
                            decoded["result"]["runtime"]["compose_version"] = "2.40.0"
                            target.write_bytes(serialize_profile_evidence(decoded))
                        elif mutation == "wrong-raw-path":
                            decoded["metadata"]["raw_output"]["path"] = (
                                "experiments/raw/performance-v1/02/"
                                "enroll-recover-success-v1.json"
                            )
                            target.write_bytes(serialize_profile_evidence(decoded))
                        elif mutation == "duplicate-member":
                            canonical = target.read_text(encoding="ascii")
                            target.write_text(
                                canonical.replace(
                                    '{"artifact":',
                                    '{"artifact":"duplicate","artifact":',
                                    1,
                                ),
                                encoding="ascii",
                            )
                        else:
                            target.write_text(
                                json.dumps(decoded, indent=2) + "\n",
                                encoding="ascii",
                            )
                    with self.assertRaises(PerformanceProcessingError):
                        process_performance_corpus(
                            repo_root=root,
                            raw_root=raw_root,
                            bootstrap_seed=42,
                            bootstrap_resamples=1000,
                        )

    def test_processed_writer_is_scoped_exclusive_and_reread_validated(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            processed = process_performance_corpus(
                repo_root=root,
                raw_root=write_performance_corpus_fixture(root),
                bootstrap_seed=42,
                bootstrap_resamples=1000,
            )
            output = (
                root / "experiments" / "processed" / "performance-v1" / "summary.json"
            )
            write_processed_performance(
                repo_root=root,
                output_path=output,
                processed=processed,
            )
            self.assertEqual(
                output.read_bytes(), serialize_processed_performance(processed)
            )
            reread, encoded = read_processed_performance(output)
            self.assertEqual(reread, processed)
            self.assertEqual(encoded, output.read_bytes())
            with self.assertRaises(PerformanceProcessingError):
                write_processed_performance(
                    repo_root=root,
                    output_path=output,
                    processed=processed,
                )
            with self.assertRaises(PerformanceProcessingError):
                write_processed_performance(
                    repo_root=root,
                    output_path=root / "outside.json",
                    processed=processed,
                )

            noncanonical = root / "noncanonical.json"
            noncanonical.write_text(
                json.dumps(processed, indent=2) + "\n",
                encoding="ascii",
            )
            with self.assertRaises(PerformanceProcessingError):
                read_processed_performance(noncanonical)

            duplicate = root / "duplicate.json"
            duplicate.write_text(
                output.read_text(encoding="ascii").replace(
                    '{"artifact":',
                    '{"artifact":"duplicate","artifact":',
                    1,
                ),
                encoding="ascii",
            )
            with self.assertRaises(PerformanceProcessingError):
                read_processed_performance(duplicate)

    def test_v2_corpus_uses_v2_artifact_and_rejects_cross_version_output(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            processed = process_performance_corpus(
                repo_root=root,
                raw_root=write_performance_corpus_fixture(
                    root, corpus_version="performance-v2"
                ),
                bootstrap_seed=42,
                bootstrap_resamples=1000,
            )
            self.assertEqual(processed["artifact"], "LOCUS-performance-processed-v2")
            output = (
                root / "experiments" / "processed" / "performance-v2" / "summary.json"
            )
            write_processed_performance(
                repo_root=root,
                output_path=output,
                processed=processed,
            )
            with self.assertRaises(PerformanceProcessingError):
                write_processed_performance(
                    repo_root=root,
                    output_path=(
                        root
                        / "experiments"
                        / "processed"
                        / "performance-v1"
                        / "summary.json"
                    ),
                    processed=processed,
                )


if __name__ == "__main__":
    unittest.main()
