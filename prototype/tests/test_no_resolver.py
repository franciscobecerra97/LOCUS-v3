from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path
from typing import Any

from locus.contracts import Resolver
from locus.no_resolver import NoResolverAdapter, NoResolverError

ROOT = Path(__file__).resolve().parents[2]
VECTOR_PATH = ROOT / "prototype/test-vectors/no-resolver-v1.json"
CORPUS_PATH = ROOT / "prototype/test-vectors/cue-policy-conformance-v1.json"


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AssertionError("invalid NoResolver vector")
    return value


class NoResolverTests(unittest.TestCase):
    def test_exact_direct_policy_vectors_pass_without_lookup(self) -> None:
        vector = load_json(VECTOR_PATH)
        corpus = load_json(CORPUS_PATH)
        conformance = {
            item["valid"][0]["id"]: item["valid"][0]
            for item in corpus["policies"]
            if "valid" in item
        }
        observed_policy_ids: list[str] = []
        for case in vector["cases"]:
            adapter = NoResolverAdapter(case["policy_id"])
            self.assertIsInstance(adapter, Resolver)
            self.assertEqual(adapter.profile_id, vector["profile_id"])
            pinned = conformance[case["conformance_vector_id"]]
            result = adapter.resolve(pinned["input"])
            self.assertEqual(result.resolver_profile, vector["profile_id"])
            self.assertEqual(result.policy_id, case["policy_id"])
            self.assertEqual(
                hashlib.sha256(result.canonical_bytes).hexdigest(),
                case["canonical_sha256"],
            )
            observed_policy_ids.append(result.policy_id)
        self.assertEqual(sorted(observed_policy_ids), vector["accepted_policy_ids"])

    def test_resolver_backed_and_unknown_policies_are_rejected(self) -> None:
        vector = load_json(VECTOR_PATH)
        for policy_id in vector["rejected_policy_ids"]:
            with self.assertRaisesRegex(
                NoResolverError, "CuePolicy requires another resolver profile"
            ):
                NoResolverAdapter(policy_id)
        with self.assertRaisesRegex(
            NoResolverError, "unsupported direct-input CuePolicy"
        ):
            NoResolverAdapter("unsupported-policy")

    def test_malformed_or_multi_candidate_input_has_one_generic_failure(self) -> None:
        adapter = NoResolverAdapter("LOCUS-canonical-phone-set-v1")
        for value in (
            ["+352621123456", "+33123456789"],
            [["+352621123456", "+352621123457"], "+33123456789", "+12025550123"],
            ["+352 621 123456", "+33123456789", "+12025550123"],
        ):
            with self.subTest(value=value):
                with self.assertRaisesRegex(
                    NoResolverError, "^direct recovery input rejected$"
                ):
                    adapter.resolve(value)


if __name__ == "__main__":
    unittest.main()
