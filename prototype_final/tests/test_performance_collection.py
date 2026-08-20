from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from typing import cast
from unittest.mock import patch

import tasks
from locus.performance_collection import (
    build_metrics,
    common_block_slots,
    ordered_arm_block_slots,
)
from locus.performance_evidence import (
    ARMS,
    BODY_ROLES,
    PERSISTED_ROLES,
    RETAINED_ROOT,
    canonical_json,
    publish_corpus,
)


class PerformanceCollectionTests(unittest.TestCase):
    def test_arm_block_order_is_complete_deterministic_and_warmup_first(self) -> None:
        for arm_id in ARMS:
            first = ordered_arm_block_slots(arm_id, 1)
            second = ordered_arm_block_slots(arm_id, 1)
            self.assertEqual(first, second)
            self.assertEqual(len(first), 29)
            self.assertEqual(first[0]["scenario_id"], "MP00")
            self.assertTrue(all(item["block"] == 1 for item in first))
            self.assertTrue(all(item["arm_id"] == arm_id for item in first))
            self.assertEqual(len({item["slot_id"] for item in first}), 29)

    def test_common_lifecycle_block_is_exact(self) -> None:
        slots = common_block_slots(7)
        self.assertEqual(len(slots), 6)
        self.assertEqual(
            [item["scenario_id"] for item in slots],
            ["MP14", "MP15", "MP16", "MP17", "MP18", "MP19"],
        )

    def test_metrics_reconcile_roles_phases_and_totals(self) -> None:
        slot = next(
            item
            for item in ordered_arm_block_slots("appss-3of5", 1)
            if item["scenario_id"] == "MP01"
        )
        metrics = build_metrics(
            slot=slot,
            end_to_end_ns=100,
            phase_latency_ns={"policy": 10, "suite-initialization": 20},
            application_body_bytes_by_role={"browser": 3},
            persisted_bytes_by_role={"provider": 7},
            ui_http_round_trip_ns=100,
        )
        body = cast(dict[str, int], metrics["application_body_bytes_by_role"])
        persisted = cast(dict[str, int], metrics["persisted_bytes_by_role"])
        self.assertEqual(set(body), set(BODY_ROLES))
        self.assertEqual(set(persisted), set(PERSISTED_ROLES))
        self.assertEqual(metrics["application_body_bytes_total"], 3)
        self.assertEqual(metrics["persisted_bytes_total"], 7)
        phases = cast(dict[str, int | None], metrics["phase_latency_ns"])
        self.assertEqual(phases["policy"], 10)
        self.assertEqual(phases["suite-initialization"], 20)
        self.assertIsNone(phases["authorization"])

    def test_parser_exposes_only_explicit_retention(self) -> None:
        parser = tasks.build_integrated_parser()
        exploratory = parser.parse_args(["integrated-performance-evidence"])
        retained = parser.parse_args(["integrated-performance-evidence", "--retain"])
        self.assertFalse(exploratory.retain)
        self.assertTrue(retained.retain)

    def test_publication_uses_exclusive_staging_and_closing_manifest(self) -> None:
        observation = {"attempt_index": 1, "slot": {"slot_id": "MP00:test"}}
        summary = {"format_id": "summary"}
        comparison = {"format_id": "comparison"}
        manifest = {"format_id": "manifest"}
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            with (
                patch(
                    "locus.performance_evidence.process_observations",
                    return_value=summary,
                ),
                patch(
                    "locus.performance_evidence.build_comparison",
                    return_value=comparison,
                ),
                patch(
                    "locus.performance_evidence.build_corpus_manifest",
                    return_value=manifest,
                ),
                patch("locus.performance_evidence.validate_observation"),
                patch(
                    "locus.performance_evidence.validate_corpus_path",
                    return_value=manifest,
                ),
            ):
                self.assertEqual(
                    publish_corpus(workspace=workspace, observations=[observation]),
                    manifest,
                )
            target = workspace / RETAINED_ROOT
            self.assertEqual(
                (target / "raw" / "MP00" / "test" / "attempt-01.json").read_bytes(),
                canonical_json(observation),
            )
            self.assertEqual(
                (target / "corpus-manifest.json").read_bytes(),
                canonical_json(manifest),
            )
            with self.assertRaises(ValueError):
                publish_corpus(workspace=workspace, observations=[observation])


if __name__ == "__main__":
    unittest.main()
