from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any, ClassVar

from locus.performance_paper import (
    LATENCY_ROWS,
    MANIFEST,
    PAPER_INPUTS_VERSION,
    PAPER_INPUTS_VERSION_V2,
    PHASE_ROWS,
    STORAGE_ROWS,
    TRAFFIC_ROWS,
    PerformancePaperError,
    build_performance_paper_inputs,
    serialize_performance_paper_manifest,
    validate_performance_paper_manifest,
    write_performance_paper_inputs,
)
from locus.performance_processing import (
    process_performance_corpus,
    serialize_processed_performance,
)

from tests.test_performance_processing import write_performance_corpus_fixture


class PerformancePaperTests(unittest.TestCase):
    temporary: ClassVar[tempfile.TemporaryDirectory[str]]
    root: ClassVar[Path]
    processed: ClassVar[dict[str, Any]]
    source_bytes: ClassVar[bytes]
    source_path: ClassVar[str]

    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temporary.name)
        cls.processed = process_performance_corpus(
            repo_root=cls.root,
            raw_root=write_performance_corpus_fixture(cls.root),
            bootstrap_seed=42,
            bootstrap_resamples=1000,
        )
        cls.source_bytes = serialize_processed_performance(cls.processed)
        cls.source_path = "experiments/processed/performance-v1/fixture.json"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def build(self, *, source_path: str | None = None):
        return build_performance_paper_inputs(
            processed=self.processed,
            source_path=self.source_path if source_path is None else source_path,
            source_bytes=self.source_bytes,
        )

    def test_generation_is_deterministic_complete_and_manifest_bound(self) -> None:
        manifest, outputs = self.build()
        repeated_manifest, repeated_outputs = self.build()
        self.assertEqual(manifest, repeated_manifest)
        self.assertEqual(outputs, repeated_outputs)
        self.assertEqual(manifest["artifact"], PAPER_INPUTS_VERSION)
        self.assertEqual(
            validate_performance_paper_manifest(manifest, outputs=outputs),
            manifest,
        )
        self.assertEqual(
            set(outputs),
            {LATENCY_ROWS, PHASE_ROWS, TRAFFIC_ROWS, STORAGE_ROWS},
        )
        expected_rows = {
            LATENCY_ROWS: 4,
            PHASE_ROWS: 27,
            TRAFFIC_ROWS: 12,
            STORAGE_ROWS: 21,
        }
        for name, expected in expected_rows.items():
            with self.subTest(name=name):
                encoded = outputs[name]
                encoded.decode("ascii")
                self.assertTrue(encoded.endswith(b"\n"))
                self.assertEqual(
                    sum(line.endswith(b"\\\\") for line in encoded.splitlines()),
                    expected,
                )
                self.assertNotIn(b"nan", encoded.lower())
                self.assertNotIn(b"inf", encoded.lower())
        self.assertEqual(
            json.loads(serialize_performance_paper_manifest(manifest)),
            manifest,
        )

    def test_source_manifest_and_output_tampering_fail_closed(self) -> None:
        manifest, outputs = self.build()
        with self.assertRaises(PerformancePaperError):
            build_performance_paper_inputs(
                processed=self.processed,
                source_path="../fixture.json",
                source_bytes=self.source_bytes,
            )
        with self.assertRaises(PerformancePaperError):
            build_performance_paper_inputs(
                processed=self.processed,
                source_path=self.source_path,
                source_bytes=self.source_bytes + b" ",
            )

        cases = []
        changed_source = copy.deepcopy(manifest)
        changed_source["source"]["git_commit"] = "not-a-commit"
        cases.append(changed_source)
        changed_format = copy.deepcopy(manifest)
        changed_format["format"]["decimal_places"] = 2
        cases.append(changed_format)
        extra = copy.deepcopy(manifest)
        extra["private_key"] = "forbidden"
        cases.append(extra)
        changed_output = copy.deepcopy(manifest)
        changed_output["outputs"][0]["sha256"] = "f" * 64
        cases.append(changed_output)
        for case in cases:
            with self.subTest(case=case):
                with self.assertRaises(PerformancePaperError):
                    validate_performance_paper_manifest(case, outputs=outputs)

        corrupted = dict(outputs)
        corrupted[LATENCY_ROWS] += b"% changed\n"
        with self.assertRaises(PerformancePaperError):
            validate_performance_paper_manifest(manifest, outputs=corrupted)

    def test_writer_is_scoped_idempotent_and_requires_explicit_replacement(
        self,
    ) -> None:
        manifest, outputs = self.build()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output_dir = root / "paper" / "generated" / "performance-v1"
            self.assertEqual(
                write_performance_paper_inputs(
                    repo_root=root,
                    output_dir=output_dir,
                    manifest=manifest,
                    outputs=outputs,
                ),
                "created",
            )
            self.assertEqual(
                write_performance_paper_inputs(
                    repo_root=root,
                    output_dir=output_dir,
                    manifest=manifest,
                    outputs=outputs,
                ),
                "unchanged",
            )
            self.assertEqual(
                (output_dir / MANIFEST).read_bytes(),
                serialize_performance_paper_manifest(manifest),
            )

            replacement, replacement_outputs = self.build(
                source_path="experiments/processed/performance-v1/fixture2.json"
            )
            with self.assertRaises(PerformancePaperError):
                write_performance_paper_inputs(
                    repo_root=root,
                    output_dir=output_dir,
                    manifest=replacement,
                    outputs=replacement_outputs,
                )
            self.assertEqual(
                write_performance_paper_inputs(
                    repo_root=root,
                    output_dir=output_dir,
                    manifest=replacement,
                    outputs=replacement_outputs,
                    replace=True,
                ),
                "replaced",
            )
            retained = json.loads((output_dir / MANIFEST).read_text(encoding="ascii"))
            self.assertEqual(retained["source"]["path"], replacement["source"]["path"])

            with self.assertRaises(PerformancePaperError):
                write_performance_paper_inputs(
                    repo_root=root,
                    output_dir=root / "outside",
                    manifest=manifest,
                    outputs=outputs,
                )

    def test_writer_rejects_partial_or_unexpected_existing_output(self) -> None:
        manifest, outputs = self.build()
        for existing_name in (LATENCY_ROWS, "unexpected.txt"):
            with self.subTest(existing_name=existing_name):
                with tempfile.TemporaryDirectory() as temporary:
                    root = Path(temporary)
                    output_dir = root / "paper" / "generated" / "performance-v1"
                    output_dir.mkdir(parents=True)
                    (output_dir / existing_name).write_bytes(b"existing")
                    with self.assertRaises(PerformancePaperError):
                        write_performance_paper_inputs(
                            repo_root=root,
                            output_dir=output_dir,
                            manifest=manifest,
                            outputs=outputs,
                        )

    def test_v2_source_generates_only_v2_manifest_and_output_paths(self) -> None:
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
            source_bytes = serialize_processed_performance(processed)
            manifest, outputs = build_performance_paper_inputs(
                processed=processed,
                source_path="experiments/processed/performance-v2/summary.json",
                source_bytes=source_bytes,
            )
            self.assertEqual(manifest["artifact"], PAPER_INPUTS_VERSION_V2)
            self.assertTrue(
                all(
                    output["path"].startswith("paper/generated/performance-v2/")
                    for output in manifest["outputs"]
                )
            )
            self.assertEqual(
                write_performance_paper_inputs(
                    repo_root=root,
                    output_dir=root / "paper" / "generated" / "performance-v2",
                    manifest=manifest,
                    outputs=outputs,
                ),
                "created",
            )
            with self.assertRaises(PerformancePaperError):
                write_performance_paper_inputs(
                    repo_root=root,
                    output_dir=root / "paper" / "generated" / "performance-v1",
                    manifest=manifest,
                    outputs=outputs,
                )


if __name__ == "__main__":
    unittest.main()
