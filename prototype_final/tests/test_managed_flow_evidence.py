from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from typing import cast

import tasks
from locus.managed_flow_evidence import (
    APPSS_RESULT_ID,
    COMMON_RESULT_ID,
    POSITIVE_CONTROLS,
    YI_RESULT_ID,
    ManagedFlowEvidenceError,
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
        "pseudonymous_client_set_id": "clients-0123456789abcdef",
        "pseudonymous_host_id": "host-0123456789abcdef",
        "pseudonymous_package_set_id": "packages-0123456789abcdef",
        "pseudonymous_project_id": "project-0123456789abcdef",
        "resolved_graph_sha256": "66" * 32,
        "source_commit": "77" * 20,
        "source_tree_sha256": "88" * 32,
    }


def summary() -> dict[str, object]:
    contacts: dict[str, object] = {}
    for item in cast(list[dict[str, str]], scenario_manifest()["reports"]):
        context = f"{item['scenario_id']}:{item['arm_id']}"
        scenario = item["scenario_id"]
        required = {
            "NF01": {"enroll", "admission-issue", "storage-execute"},
            "NF02": {"recover", "authorize", "storage-execute"},
            "NF03": {"package-export", "package-import"},
            "NF04": {"recover"},
            "NF05": {"policy-preview"},
            "NF06": {"package-import", "storage-execute"},
            "NF07": {"client-create", "container-create"},
            "NF08": {"container-action", "container-restart", "container-kill"},
            "NF09": {"self-destroy", "container-remove"},
            "NF10": {"system-stop", "container-stop", "recover"},
            "NF11": {"system-stop", "client-create", "package-import"},
            "NF12": {"manager-status", "client-session"},
        }[scenario]
        arm_id = item["arm_id"]
        if scenario == "NF01" and arm_id.startswith("yi-"):
            required.add("yi-enroll")
        if scenario == "NF01" and arm_id.startswith("appss-"):
            required.update({"appss-initialize", "appss-install"})
        if scenario == "NF02" and arm_id.startswith("yi-"):
            required.update({"yi-prepare", "yi-respond"})
        if scenario == "NF02" and arm_id.startswith("appss-"):
            required.add("appss-evaluate")
        if scenario == "NF05" and arm_id.endswith("3of5"):
            required.add("resolver-resolve")
        contacts[context] = [
            {
                "category": category,
                "receiver_role": "managed-client",
                "reconciliation": "matched",
                "rejected_count": int(
                    scenario in {"NF04", "NF06", "NF11"} and index == 0
                ),
                "request_body_bytes": 0,
                "request_count": 1,
                "response_body_bytes": 100,
                "sender_role": "browser",
                "success_count": int(
                    not (scenario in {"NF04", "NF06", "NF11"} and index == 0)
                ),
                "unavailable_count": 0,
            }
            for index, category in enumerate(sorted(required))
        ]
    return {
        "flow_contacts": contacts,
        "output_scan": "passed",
        "positive_controls": POSITIVE_CONTROLS,
        "status": "passed",
    }


class ManagedFlowEvidenceTests(unittest.TestCase):
    def test_checked_manifest_and_exact_family_counts(self) -> None:
        encoded = canonical_json(scenario_manifest())
        self.assertEqual(
            (ROOT / "docs" / "managed-flow-scenarios-v1.json").read_bytes(), encoded
        )
        reports = build_reports(provenance=provenance(), summary=summary())
        self.assertEqual(len(reports), 30)
        families = {YI_RESULT_ID: 0, APPSS_RESULT_ID: 0, COMMON_RESULT_ID: 0}
        for _path, report in reports:
            validate_result(report)
            families[cast(str, report["format_id"])] += 1
        self.assertEqual(
            families, {YI_RESULT_ID: 12, APPSS_RESULT_ID: 12, COMMON_RESULT_ID: 6}
        )

    def test_unsafe_or_incomplete_report_fails_closed(self) -> None:
        _path, report = build_reports(provenance=provenance(), summary=summary())[0]
        changed = copy.deepcopy(report)
        changed["packet_capture"] = "no"
        with self.assertRaises(ManagedFlowEvidenceError):
            validate_result(changed)
        incomplete = summary()
        incomplete["positive_controls"] = {}
        with self.assertRaises(ManagedFlowEvidenceError):
            build_reports(provenance=provenance(), summary=incomplete)
        missing_contact = summary()
        contexts = cast(
            dict[str, list[dict[str, object]]], missing_contact["flow_contacts"]
        )
        contexts["NF01:yi-2of3"] = [
            item for item in contexts["NF01:yi-2of3"] if item["category"] != "yi-enroll"
        ]
        with self.assertRaises(ManagedFlowEvidenceError):
            build_reports(provenance=provenance(), summary=missing_contact)

    def test_atomic_exclusive_hash_closed_publication(self) -> None:
        reports = build_reports(provenance=provenance(), summary=summary())
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = publish_corpus(root=root, reports=reports)
            target = root / "evidence" / "retained" / "managed-flow-v1"
            self.assertEqual(manifest["record_count"], 30)
            self.assertEqual(
                validate_corpus_path(target)["corpus_sha256"], manifest["corpus_sha256"]
            )
            for entry in cast(list[dict[str, object]], manifest["entries"]):
                encoded = (target / cast(str, entry["path"])).read_bytes()
                self.assertEqual(hashlib.sha256(encoded).hexdigest(), entry["sha256"])
                self.assertEqual(canonical_json(json.loads(encoded)), encoded)
            with self.assertRaises(ManagedFlowEvidenceError):
                publish_corpus(root=root, reports=reports)

    def test_command_is_additive_and_retention_is_explicit(self) -> None:
        parser = tasks.build_integrated_parser()
        exploratory = parser.parse_args(["integrated-flow-evidence"])
        retained = parser.parse_args(["integrated-flow-evidence", "--retain"])
        self.assertFalse(exploratory.retain)
        self.assertTrue(retained.retain)


if __name__ == "__main__":
    unittest.main()
