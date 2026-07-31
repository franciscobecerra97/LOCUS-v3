from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

from locus.attack_runner import build_attack_report
from locus.profile_evidence import (
    ProfileEvidenceError,
    build_profile_evidence,
    serialize_profile_evidence,
    validate_profile_evidence,
    write_profile_evidence,
)


def sample_metadata(
    *,
    profile: str,
    configuration: dict[str, object],
    output_path: str | None = None,
    randomness_kind: str = "os-csprng",
    seed: int | None = None,
) -> dict[str, object]:
    digest = "a" * 64
    return {
        "configuration": configuration,
        "evidence_class": "development",
        "experiment_id": "profile-evidence-test",
        "finished_at": "2026-07-23T10:00:01+00:00",
        "git": {"commit": "b" * 40, "dirty": True},
        "host": {
            "id": "test-host",
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
        "profile": profile,
        "randomness": {"kind": randomness_kind, "seed": seed},
        "raw_output": {
            "path": output_path,
            "retained": output_path is not None,
        },
        "started_at": "2026-07-23T10:00:00+00:00",
        "version": "LOCUS-experiment-metadata-v1",
        "warnings": ["dirty-worktree"]
        if output_path is not None
        else [
            "dirty-worktree",
            "unretained-output",
        ],
    }


def sample_attack_report() -> dict[str, object]:
    return build_attack_report(
        scenario_id="resolver-unavailable-v1",
        observed_result={
            "attempt_delta": 0,
            "failure_category": "resolver-unavailable",
        },
    )


def sample_benchmark_result() -> dict[str, object]:
    return {
        "artifact": "LOCUS-compose-benchmark-v1",
        "attempts": {"after": 2, "before": 0, "budget": 4},
        "latency_ms": {
            "max": 12.0,
            "mean": 11.0,
            "median": 11.0,
            "min": 10.0,
            "samples": [10.0, 12.0],
        },
        "profile": "benchmark",
        "runs": 2,
        "selected": [1, 3],
        "status": "ok",
    }


def sample_performance_result() -> dict[str, object]:
    latency = {
        "authorization": 1.0,
        "client_setup": 1.0,
        "cloud": 1.0,
        "commitment": 1.0,
        "finalization": 1.0,
        "resolver": 1.0,
        "response": 1.0,
        "status_check": 1.0,
        "total": 9.0,
        "unclassified": 1.0,
    }
    application_bytes = {
        role: {"received": 20, "sent": 10}
        for role in ("authorization", "cloud", "resolver", "tpass")
    }
    storage = {
        "artifact": "LOCUS-storage-metric-v1",
        "client_bytes": 100,
        "party_bytes": [200, 200, 200, 150, 150],
        "status": "ok",
    }
    return {
        "artifact": "LOCUS-compose-performance-result-v1",
        "block": 1,
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
        "enrollment_latency_ms": 10.0,
        "orchestration_latency_ms": 100.0,
        "orchestration_seed": 7,
        "output_scan": "passed",
        "profile": "performance",
        "samples": [
            {
                "application_bytes": application_bytes,
                "artifact": "LOCUS-performance-client-samples-v1",
                "attempts": {"after": offset + 1, "before": offset},
                "latency_ms": latency,
                "measurement": offset,
                "outcome": "success",
                "selected": [1, 3],
                "status": "ok",
            }
            for offset in range(1, 4)
        ],
        "runtime": {
            "compose_version": "2.39.1",
            "docker_engine_version": "28.3.2",
            "reference_image_id": f"sha256:{'c' * 64}",
            "s3_image": (
                "chrislusf/seaweedfs:4.29@"
                "sha256:d47c7ee99fcb951351d7194915f4e3a5ea604a8e8871183d713907dec4fb9bf5"
            ),
        },
        "scenario_position": 2,
        "scenario_id": "enroll-recover-success-v1",
        "status": "ok",
        "storage": {
            "after": storage,
            "before": storage,
            "cloud_object_bytes": 800,
        },
    }


class ProfileEvidenceTests(unittest.TestCase):
    def test_attack_benchmark_and_performance_records_are_exact_and_bound(self) -> None:
        attack = build_profile_evidence(
            metadata=sample_metadata(
                profile="compose-attack",
                configuration={
                    "scenario": "resolver-unavailable-v1",
                    "topology": "same-host-compose-5-party-v1",
                },
            ),
            result=sample_attack_report(),
        )
        self.assertEqual(validate_profile_evidence(attack), attack)

        benchmark = build_profile_evidence(
            metadata=sample_metadata(
                profile="compose-benchmark",
                configuration={
                    "runs": 2,
                    "selected": [1, 3],
                    "threshold": 2,
                    "topology": "same-host-compose-5-party-v1",
                },
            ),
            result=sample_benchmark_result(),
        )
        self.assertEqual(validate_profile_evidence(benchmark), benchmark)

        performance = build_profile_evidence(
            metadata=sample_metadata(
                profile="compose-performance",
                configuration={
                    "block": 1,
                    "orchestration_seed": 7,
                    "scenario": "enroll-recover-success-v1",
                    "scenario_position": 2,
                    "topology": "same-host-compose-5-party-v1",
                },
                randomness_kind="orchestrator-prng-v1",
                seed=7,
            ),
            result=sample_performance_result(),
        )
        self.assertEqual(validate_profile_evidence(performance), performance)

        mismatched = copy.deepcopy(performance)
        mismatched["metadata"]["configuration"]["orchestration_seed"] = 8
        with self.assertRaises(ProfileEvidenceError):
            validate_profile_evidence(mismatched)

    def test_binding_trace_and_redaction_changes_fail_closed(self) -> None:
        evidence = build_profile_evidence(
            metadata=sample_metadata(
                profile="compose-attack",
                configuration={
                    "scenario": "resolver-unavailable-v1",
                    "topology": "same-host-compose-5-party-v1",
                },
            ),
            result=sample_attack_report(),
        )
        cases: list[dict] = []
        wrong_scenario = copy.deepcopy(evidence)
        wrong_scenario["metadata"]["configuration"]["scenario"] = (
            "cloud-snapshot-no-offline-predicate-v1"
        )
        cases.append(wrong_scenario)
        trace_changed = copy.deepcopy(evidence)
        trace_changed["trace_policy"]["service_log_policy"] = "retained"
        cases.append(trace_changed)
        secret_field = copy.deepcopy(evidence)
        secret_field["metadata"]["configuration"]["private_key"] = "forbidden"
        cases.append(secret_field)
        extra_field = copy.deepcopy(evidence)
        extra_field["logs"] = []
        cases.append(extra_field)
        for case in cases:
            with self.subTest(case=case):
                with self.assertRaises(ProfileEvidenceError):
                    validate_profile_evidence(case)

    def test_retained_write_is_canonical_synced_and_exclusive(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            relative = "experiments/raw/attack/run-1.json"
            output = root / relative
            evidence = build_profile_evidence(
                metadata=sample_metadata(
                    profile="compose-attack",
                    configuration={
                        "scenario": "resolver-unavailable-v1",
                        "topology": "same-host-compose-5-party-v1",
                    },
                    output_path=relative,
                ),
                result=sample_attack_report(),
            )
            write_profile_evidence(
                repo_root=root,
                output_path=output,
                evidence=evidence,
            )
            self.assertEqual(output.read_bytes(), serialize_profile_evidence(evidence))
            with self.assertRaises(ProfileEvidenceError):
                write_profile_evidence(
                    repo_root=root,
                    output_path=output,
                    evidence=evidence,
                )

    def test_retained_write_rejects_path_or_format_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            evidence = build_profile_evidence(
                metadata=sample_metadata(
                    profile="compose-attack",
                    configuration={
                        "scenario": "resolver-unavailable-v1",
                        "topology": "same-host-compose-5-party-v1",
                    },
                    output_path="experiments/raw/attack/run-1.json",
                ),
                result=sample_attack_report(),
            )
            for output in (
                root / "experiments/raw/attack/run-2.json",
                root / "experiments/raw/attack/run-1.txt",
                root.parent / "escaped.json",
            ):
                with self.subTest(output=output):
                    with self.assertRaises(ProfileEvidenceError):
                        write_profile_evidence(
                            repo_root=root,
                            output_path=output,
                            evidence=evidence,
                        )


if __name__ == "__main__":
    unittest.main()
