from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from locus.artifact_package import (
    RELEASE_STATUS_PATH,
    build_archive,
    find_anonymity_violations,
    release_is_approved,
    select_artifact_paths,
)

import tasks


class ArtifactPackageTests(unittest.TestCase):
    def test_extracted_manifest_validates_without_git_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            data = b"LOCUS\n"
            (root / "README.md").write_bytes(data)
            (root / "artifact_manifest.json").write_text(
                json.dumps(
                    {
                        "artifact": "LOCUS-anonymous-artifact-v2",
                        "entries": [
                            {
                                "path": "README.md",
                                "sha256": hashlib.sha256(data).hexdigest(),
                                "size": len(data),
                            }
                        ],
                        "source_commit": "a" * 40,
                    }
                ),
                encoding="ascii",
            )
            self.assertEqual(
                tasks.extracted_artifact_paths(root),
                ("README.md",),
            )

    def test_extracted_manifest_rejects_changed_source_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "README.md").write_bytes(b"changed\n")
            (root / "artifact_manifest.json").write_text(
                json.dumps(
                    {
                        "artifact": "LOCUS-anonymous-artifact-v1",
                        "entries": [
                            {
                                "path": "README.md",
                                "sha256": hashlib.sha256(b"LOCUS\n").hexdigest(),
                                "size": len(b"LOCUS\n"),
                            }
                        ],
                        "source_commit": "a" * 40,
                    }
                ),
                encoding="ascii",
            )
            with self.assertRaisesRegex(
                RuntimeError,
                "artifact source digest mismatch",
            ):
                tasks.extracted_artifact_paths(root)

    def test_v2_allowlist_excludes_repository_docs_paper_and_old_evidence(self) -> None:
        selected = select_artifact_paths(
            (
                ".git/config",
                "LICENSE",
                "LICENSE-DOCUMENTATION.md",
                "README.md",
                "artifact/README.md",
                "artifact/package-v2/README.md",
                "artifact/RELEASE-CHECKLIST.md",
                "docs/architecture.md",
                "docs/schemas/attack-report-v1.schema.json",
                "paper/main.tex",
                "experiments/raw/performance-v1/01/result.json",
                "experiments/raw/performance-v2/01/result.json",
                "prototype/locus/core.py",
            )
        )
        self.assertEqual(
            selected,
            (
                "LICENSE",
                "LICENSE-DOCUMENTATION.md",
                "artifact/package-v2/README.md",
                "docs/schemas/attack-report-v1.schema.json",
                "experiments/raw/performance-v2/01/result.json",
                "prototype/locus/core.py",
            ),
        )

    def test_anonymity_scan_reports_categories_without_values(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "README.md").write_text(
                "built under "
                + "C:"
                + "\\Users\\"
                + "named-user and developer@example.invalid",
                encoding="utf-8",
            )
            violations = find_anonymity_violations(
                root, ("README.md",), ("developer@example.invalid",)
            )
        self.assertEqual(
            violations,
            (
                "development-identity:README.md",
                "local-user-path:README.md",
            ),
        )
        self.assertNotIn("named-user", repr(violations))

    def test_anonymity_scan_rejects_project_management_language(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "README.md").write_text(
                "Complete planning task " + "P" + "4.9 before " + "Cycle " + "1.\n",
                encoding="utf-8",
            )
            violations = find_anonymity_violations(root, ("README.md",), ())
        self.assertEqual(
            violations,
            ("project-management-language:README.md",),
        )

    def test_archive_is_byte_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "dist").mkdir()
            (root / "README.md").write_text("LOCUS\n", encoding="utf-8")
            first = root / "dist" / "first.zip"
            second = root / "dist" / "second.zip"
            build_archive(
                root,
                ("README.md",),
                first,
                replace=False,
                source_commit="a" * 40,
            )
            build_archive(
                root,
                ("README.md",),
                second,
                replace=False,
                source_commit="a" * 40,
            )
            self.assertEqual(
                hashlib.sha256(first.read_bytes()).digest(),
                hashlib.sha256(second.read_bytes()).digest(),
            )

    def test_release_status_ignores_approval_text_in_instructions(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            checklist = root / RELEASE_STATUS_PATH
            checklist.parent.mkdir(parents=True)
            checklist.write_text(
                "Release authorization: PENDING\n"
                "Change the field to `Release authorization: APPROVED` later.\n",
                encoding="utf-8",
            )
            self.assertFalse(release_is_approved(root))


if __name__ == "__main__":
    unittest.main()
