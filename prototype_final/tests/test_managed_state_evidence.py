from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any, cast

import tasks
from locus.managed_state_evidence import (
    APPSS_RESULT_ID,
    COMMON_RESULT_ID,
    YI_RESULT_ID,
    ManagedStateEvidenceError,
    build_reports,
    canonical_json,
    publish_corpus,
    scenario_manifest,
    validate_corpus_path,
    validate_result,
)

ROOT = Path(__file__).resolve().parents[1]


def provenance() -> dict[str, object]:
    return {
        "collected_at_utc": "2026-08-17T12:00:00+00:00",
        "compose_sha256": "11" * 32,
        "host_tier": "same-host-single-operator",
        "image_id": "sha256:" + "22" * 32,
        "live_graph_sha256": "33" * 32,
        "lockfile_sha256": "44" * 32,
        "managed_manifest_sha256": "55" * 32,
        "pseudonymous_host_id": "host-0123456789abcdef",
        "resolved_graph_sha256": "66" * 32,
        "source_commit": "77" * 20,
        "source_tree_sha256": "88" * 32,
    }


def summary() -> dict[str, object]:
    roles = (
        ("admission-data", "admission"),
        ("bootstrap-data", "bootstrap"),
        ("managed-client-data", "managed-client-template"),
        ("manager-controller-data", "manager-controller"),
        ("manager-ui-data", "manager-ui"),
        ("operator-data", "operator"),
        ("party1-data", "party"),
        ("party2-data", "party"),
        ("party3-data", "party"),
        ("party4-data", "party"),
        ("party5-data", "party"),
        ("resolver-data", "resolver"),
        ("s3-data", "provider"),
        ("s3-role-data", "s3-role"),
        ("storage-gateway-data", "storage-gateway"),
    )
    observed = [
        {
            "files": index + 1,
            "role": role,
            "total_bytes": 100 + index,
            "volume_role": volume,
        }
        for index, (volume, role) in enumerate(roles)
    ]
    return {
        "arms": 4,
        "output_scan": "passed",
        "paired_policy_conditions": True,
        "state_snapshots": {
            label: copy.deepcopy(observed)
            for label in (
                "post_enrollment",
                "post_recovery",
                "preserved_restart",
                "fresh_reset",
            )
        },
        "status": "passed",
    }


class ManagedStateEvidenceTests(unittest.TestCase):
    def test_checked_scenario_manifest_is_canonical_and_exact(self) -> None:
        expected = canonical_json(scenario_manifest())
        path = ROOT / "docs" / "managed-state-scenarios-v1.json"
        self.assertEqual(path.read_bytes(), expected)
        value = json.loads(expected)
        self.assertEqual(value["report_count"], 42)
        self.assertEqual(len(value["reports"]), 42)
        self.assertEqual(
            len({tuple(sorted(item.items())) for item in value["reports"]}), 42
        )

    def test_suite_families_paths_and_controls_are_exact(self) -> None:
        reports = build_reports(provenance=provenance(), summary=summary())
        self.assertEqual(len(reports), 42)
        families = {YI_RESULT_ID: 0, APPSS_RESULT_ID: 0, COMMON_RESULT_ID: 0}
        for path, report in reports:
            validate_result(report)
            families[str(report["format_id"])] += 1
            self.assertNotIn("\\", path)
            metrics = cast(dict[str, object], report["metrics"])
            self.assertEqual(metrics["ordinary_violations"], 0)
        self.assertEqual(
            families,
            {YI_RESULT_ID: 18, APPSS_RESULT_ID: 18, COMMON_RESULT_ID: 6},
        )

    def test_unsafe_changed_or_incomplete_reports_fail_closed(self) -> None:
        _path, report = build_reports(provenance=provenance(), summary=summary())[0]
        changed = copy.deepcopy(report)
        changed_metrics = cast(dict[str, object], changed["metrics"])
        changed_metrics["ordinary_violations"] = 1
        with self.assertRaises(ManagedStateEvidenceError):
            validate_result(changed)
        changed = copy.deepcopy(report)
        changed["private_key"] = "00" * 32
        with self.assertRaises(ManagedStateEvidenceError):
            validate_result(changed)
        incomplete = summary()
        snapshots = cast(dict[str, Any], incomplete["state_snapshots"])
        cast(list[object], snapshots["post_enrollment"]).pop()
        with self.assertRaises(ManagedStateEvidenceError):
            build_reports(provenance=provenance(), summary=incomplete)

    def test_publication_is_complete_canonical_and_exclusive(self) -> None:
        reports = build_reports(provenance=provenance(), summary=summary())
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = publish_corpus(root=root, reports=reports)
            target = root / "evidence" / "retained" / "managed-state-v1"
            self.assertEqual(manifest["record_count"], 42)
            self.assertEqual(len(list(target.rglob("SB*.json"))), 42)
            entries = cast(list[dict[str, object]], manifest["entries"])
            for entry in entries:
                encoded = (target / cast(str, entry["path"])).read_bytes()
                self.assertEqual(hashlib.sha256(encoded).hexdigest(), entry["sha256"])
                self.assertEqual(canonical_json(json.loads(encoded)), encoded)
            with self.assertRaises(ManagedStateEvidenceError):
                publish_corpus(root=root, reports=reports)

    def test_checked_in_corpus_is_hash_closed_when_present(self) -> None:
        target = ROOT / "evidence" / "retained" / "managed-state-v1"
        if target.exists():
            manifest = validate_corpus_path(target)
            self.assertEqual(manifest["record_count"], 42)

    def test_command_is_additive_and_requires_explicit_retain_flag(self) -> None:
        parser = tasks.build_integrated_parser()
        exploratory = parser.parse_args(["integrated-state-evidence"])
        retained = parser.parse_args(["integrated-state-evidence", "--retain"])
        self.assertFalse(exploratory.retain)
        self.assertTrue(retained.retain)


if __name__ == "__main__":
    unittest.main()
