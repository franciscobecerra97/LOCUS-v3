from __future__ import annotations

import hashlib
import itertools
import json
import unittest
from pathlib import Path
from typing import Any

from locus.contracts import CuePolicy
from locus.cue_policy import CuePolicyError
from locus.cue_policy_registry import (
    DEFAULT_CUE_POLICY_REGISTRY,
    CuePolicyRegistry,
    CuePolicyRegistryError,
)

ROOT = Path(__file__).resolve().parents[2]
CORPUS_PATH = ROOT / "prototype/test-vectors/cue-policy-conformance-v1.json"
LEGACY_PATH = ROOT / "prototype/test-vectors/cue-policy-v1.json"


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AssertionError("invalid CuePolicy corpus")
    return value


class CuePolicyConformanceTests(unittest.TestCase):
    def test_registry_contains_four_independent_policy_adapters(self) -> None:
        self.assertEqual(
            DEFAULT_CUE_POLICY_REGISTRY.policy_ids,
            (
                "LOCUS-canonical-email-set-v1",
                "LOCUS-canonical-phone-set-v1",
                "LOCUS-location-person-set-v1",
                "LOCUS-quantized-coordinate-set-v1",
            ),
        )
        for policy_id in DEFAULT_CUE_POLICY_REGISTRY.policy_ids:
            policy = DEFAULT_CUE_POLICY_REGISTRY.require(policy_id)
            self.assertIsInstance(policy, CuePolicy)
            self.assertEqual(policy.policy_id, policy.metadata.policy_id)
            self.assertEqual(policy.metadata.cardinality, 3)
            self.assertEqual(policy.metadata.ambiguity_rule, "reject")

    def test_new_policy_vectors_are_order_independent_and_exact(self) -> None:
        corpus = load_json(CORPUS_PATH)
        self.assertEqual(corpus["corpus_version"], "LOCUS-cue-policy-conformance-v1")
        for policy_entry in corpus["policies"]:
            if "valid" not in policy_entry:
                continue
            policy = DEFAULT_CUE_POLICY_REGISTRY.require(policy_entry["policy_id"])
            for vector in policy_entry["valid"]:
                expected = bytes.fromhex(vector["canonical_hex"])
                self.assertEqual(expected.decode("ascii"), vector["canonical_json"])
                self.assertEqual(
                    hashlib.sha256(expected).hexdigest(),
                    vector["canonical_sha256"],
                )
                outputs = {
                    policy.process(list(permutation)).canonical_bytes
                    for permutation in itertools.permutations(vector["input"])
                }
                self.assertEqual(outputs, {expected})

    def test_invalid_corpus_has_exact_local_errors(self) -> None:
        corpus = load_json(CORPUS_PATH)
        for policy_entry in corpus["policies"]:
            if "invalid" not in policy_entry:
                continue
            policy = DEFAULT_CUE_POLICY_REGISTRY.require(policy_entry["policy_id"])
            for vector in policy_entry["invalid"]:
                with self.subTest(policy=policy.policy_id, vector=vector["id"]):
                    with self.assertRaisesRegex(CuePolicyError, f"^{vector['error']}$"):
                        policy.process(vector["input"])

    def test_cross_policy_inputs_fail_instead_of_being_reinterpreted(self) -> None:
        corpus = load_json(CORPUS_PATH)
        entries = [entry for entry in corpus["policies"] if "valid" in entry]
        for source in entries:
            input_value = source["valid"][0]["input"]
            for target in entries:
                if source["policy_id"] == target["policy_id"]:
                    continue
                policy = DEFAULT_CUE_POLICY_REGISTRY.require(target["policy_id"])
                with self.subTest(
                    source=source["policy_id"], target=target["policy_id"]
                ):
                    with self.assertRaises(CuePolicyError):
                        policy.process(input_value)

    def test_frozen_policy_still_uses_legacy_corpus_byte_for_byte(self) -> None:
        corpus = load_json(CORPUS_PATH)
        legacy_entry = corpus["policies"][0]
        self.assertEqual(legacy_entry["legacy_vector_source"], LEGACY_PATH.name)
        legacy = load_json(LEGACY_PATH)
        policy = DEFAULT_CUE_POLICY_REGISTRY.require(legacy_entry["policy_id"])
        vector = legacy["valid"][0]
        self.assertEqual(
            policy.process(vector["cues"]).canonical_bytes.hex(),
            vector["canonical_hex"],
        )
        self.assertEqual(
            hashlib.sha256(LEGACY_PATH.read_bytes()).hexdigest(),
            "24b8b1972eedc7f54c8cce51f8f21d176d09b70093fb1abb610fa23635919970",
        )

    def test_registry_rejects_unknown_duplicate_and_metadata_mismatch(self) -> None:
        with self.assertRaisesRegex(CuePolicyRegistryError, "unsupported CuePolicy"):
            DEFAULT_CUE_POLICY_REGISTRY.require("unsupported-policy")
        policy = DEFAULT_CUE_POLICY_REGISTRY.require("LOCUS-canonical-phone-set-v1")
        with self.assertRaisesRegex(
            CuePolicyRegistryError, "duplicate CuePolicy identifier"
        ):
            CuePolicyRegistry((policy, policy))


if __name__ == "__main__":
    unittest.main()
