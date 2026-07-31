from __future__ import annotations

import copy
import hashlib
import json
import unittest
from pathlib import Path
from typing import Any, cast

from locus.resolver_fixture import ResolverFixtureError, canonical_resolver_input

ROOT = Path(__file__).resolve().parents[2]


class ResolverDriftTests(unittest.TestCase):
    def test_versioned_drift_corpus_has_defined_generic_outcomes(self) -> None:
        corpus = json.loads(
            (ROOT / "prototype/test-vectors/resolver-drift-v1.json").read_text(
                encoding="utf-8"
            )
        )
        baseline = canonical_resolver_input(corpus["baseline"])
        self.assertEqual(
            hashlib.sha256(baseline).hexdigest(),
            corpus["expected_baseline_sha256"],
        )
        outcomes: dict[str, str] = {}
        errors: set[str] = set()
        for scenario in corpus["scenarios"]:
            response = copy.deepcopy(corpus["baseline"])
            for mutation in scenario["mutations"]:
                cursor: Any = response
                path = cast(list[int | str], mutation["path"])
                for component in path[:-1]:
                    cursor = cursor[component]
                cursor[path[-1]] = mutation["replacement"]
            try:
                changed = canonical_resolver_input(response)
            except ResolverFixtureError as exc:
                outcomes[scenario["id"]] = "local-rejection"
                errors.add(str(exc))
            else:
                outcomes[scenario["id"]] = (
                    "stable" if changed == baseline else "canonical-drift"
                )
            self.assertEqual(outcomes[scenario["id"]], scenario["expected"])
        self.assertEqual(errors, {"resolver selection unavailable"})


if __name__ == "__main__":
    unittest.main()
