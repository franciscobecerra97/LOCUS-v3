from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from locus.experiment_metadata import (
    ExperimentMetadataError,
    _git_state,
    collect_experiment_metadata,
    utc_timestamp,
    validate_experiment_metadata,
)

ROOT = Path(__file__).resolve().parents[2]


def sample_metadata() -> dict:
    digest = "a" * 64
    return {
        "configuration": {"backend": "native", "runs": 1},
        "evidence_class": "development",
        "experiment_id": "metadata-test",
        "finished_at": "2026-07-21T10:00:01+00:00",
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
        "profile": "benchmark",
        "randomness": {"kind": "os-csprng", "seed": None},
        "raw_output": {"path": None, "retained": False},
        "started_at": "2026-07-21T10:00:00+00:00",
        "version": "LOCUS-experiment-metadata-v1",
        "warnings": ["dirty-worktree", "unretained-output"],
    }


class ExperimentMetadataTests(unittest.TestCase):
    def test_artifact_manifest_supplies_clean_source_commit_without_git(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "artifact_manifest.json").write_text(
                json.dumps(
                    {
                        "artifact": "LOCUS-anonymous-artifact-v1",
                        "entries": [],
                        "source_commit": "c" * 40,
                    }
                ),
                encoding="ascii",
            )
            self.assertEqual(_git_state(root), ("c" * 40, False))

    def test_collects_current_commit_lock_hashes_and_privacy_safe_host(self) -> None:
        timestamp = utc_timestamp()
        metadata = collect_experiment_metadata(
            repo_root=ROOT,
            experiment_id="metadata-collection-test",
            profile="test",
            evidence_class="development",
            configuration={"case": "synthetic"},
            randomness_kind="os-csprng",
            seed=None,
            started_at=timestamp,
            finished_at=timestamp,
            output_path=None,
        )
        self.assertEqual(metadata["version"], "LOCUS-experiment-metadata-v1")
        self.assertRegex(metadata["git"]["commit"], r"^[0-9a-f]{40}$")
        self.assertNotIn("hostname", metadata["host"])
        self.assertEqual(
            set(metadata["locks"]),
            {
                "uv.lock",
                "tpass-core/Cargo.lock",
                "tpass-python/Cargo.lock",
            },
        )

    def test_paper_evidence_requires_clean_labeled_retained_raw_output(self) -> None:
        metadata = sample_metadata()
        metadata["evidence_class"] = "paper"
        with self.assertRaises(ExperimentMetadataError):
            validate_experiment_metadata(metadata)

        metadata["git"]["dirty"] = False
        metadata["raw_output"] = {
            "path": "experiments/raw/benchmark/run.json",
            "retained": True,
        }
        metadata["warnings"] = []
        self.assertEqual(validate_experiment_metadata(metadata), metadata)

    def test_rejects_noncanonical_or_misleading_metadata(self) -> None:
        cases: list[dict] = []
        reversed_time = copy.deepcopy(sample_metadata())
        reversed_time["finished_at"] = "2026-07-21T09:59:59+00:00"
        cases.append(reversed_time)
        seeded_csprng = copy.deepcopy(sample_metadata())
        seeded_csprng["randomness"]["seed"] = 7
        cases.append(seeded_csprng)
        absolute_output = copy.deepcopy(sample_metadata())
        absolute_output["raw_output"] = {"path": "C:/secret/run.json", "retained": True}
        cases.append(absolute_output)
        unknown_field = copy.deepcopy(sample_metadata())
        unknown_field["hostname"] = "must-not-appear"
        cases.append(unknown_field)
        for metadata in cases:
            with self.subTest(metadata=metadata):
                with self.assertRaises(ExperimentMetadataError):
                    validate_experiment_metadata(metadata)


if __name__ == "__main__":
    unittest.main()
