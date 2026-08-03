from __future__ import annotations

import copy
import hashlib
import itertools
import json
import unittest
from pathlib import Path
from typing import Any, cast

from locus.cue_policy import (
    FROZEN_LOCATION_PERSON_POLICY,
    CuePolicyError,
    canonical_location,
    canonical_person,
    canonical_recovery_input,
)

ROOT = Path(__file__).resolve().parents[2]


def sample_cues() -> list[dict]:
    return [
        {
            "location": {"latitude": "49.59875", "longitude": "6.13445"},
            "person": {"type": "phone", "value": "+352621123456"},
        },
        {
            "location": {"latitude": "49.61160", "longitude": "6.13190"},
            "person": {"type": "email", "value": "Friend@Example.org"},
        },
        {
            "location": {"latitude": "49.62610", "longitude": "6.12750"},
            "person": {"type": "phone", "value": "+33123456789"},
        },
    ]


class CuePolicyTests(unittest.TestCase):
    def test_frozen_adapter_preserves_valid_bytes_and_invalid_errors(self) -> None:
        corpus = json.loads(
            (ROOT / "prototype/test-vectors/cue-policy-v1.json").read_text(
                encoding="utf-8"
            )
        )
        vector = corpus["valid"][0]
        expected = bytes.fromhex(vector["canonical_hex"])
        for order in vector["input_orders"]:
            cues = [vector["cues"][index] for index in order]
            result = FROZEN_LOCATION_PERSON_POLICY.process(cues)
            self.assertEqual(result.policy_id, corpus["policy_version"])
            self.assertEqual(result.canonical_bytes, expected)

        for mutation in corpus["invalid_mutations"]:
            cues = copy.deepcopy(vector["cues"])
            cursor: Any = cues
            path = cast(list[int | str], mutation["path"])
            for component in path[:-1]:
                cursor = cursor[component]
            cursor[path[-1]] = mutation["replacement"]
            with self.subTest(mutation=mutation["id"]):
                with self.assertRaises(CuePolicyError) as direct_error:
                    canonical_recovery_input(cues)
                with self.assertRaises(CuePolicyError) as adapter_error:
                    FROZEN_LOCATION_PERSON_POLICY.process(cues)
                self.assertEqual(
                    str(adapter_error.exception), str(direct_error.exception)
                )

    def test_pinned_corpus_matches_resolver_fixture_and_exact_bytes(self) -> None:
        corpus = json.loads(
            (ROOT / "prototype/test-vectors/cue-policy-v1.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(corpus["policy_version"], "LOCUS-location-person-set-v1")
        vector = corpus["valid"][0]
        fixture = json.loads(
            (ROOT / "deploy/fixtures/cues.json").read_text(encoding="ascii")
        )
        self.assertEqual(vector["cues"], fixture["cues"])
        expected = bytes.fromhex(vector["canonical_hex"])
        self.assertEqual(
            hashlib.sha256(expected).hexdigest(), vector["canonical_sha256"]
        )
        for order in vector["input_orders"]:
            cues = [vector["cues"][index] for index in order]
            self.assertEqual(canonical_recovery_input(cues), expected)

        for mutation in corpus["invalid_mutations"]:
            cues = copy.deepcopy(vector["cues"])
            cursor: Any = cues
            path = cast(list[int | str], mutation["path"])
            for component in path[:-1]:
                cursor = cursor[component]
            cursor[path[-1]] = mutation["replacement"]
            with self.subTest(mutation=mutation["id"]):
                with self.assertRaises(CuePolicyError):
                    canonical_recovery_input(cues)

    def test_all_six_pair_orders_have_one_canonical_encoding(self) -> None:
        encodings = {
            canonical_recovery_input(list(permutation))
            for permutation in itertools.permutations(sample_cues())
        }
        self.assertEqual(len(encodings), 1)
        encoded = encodings.pop()
        self.assertIn(b"LOCUS-location-person-set-v1", encoded)
        self.assertNotIn(b"Friend", encoded)

    def test_coordinate_rounding_is_exact_half_even(self) -> None:
        self.assertEqual(
            canonical_location({"latitude": "1.23445", "longitude": "-1.23455"}),
            {"latitude_e4": 12344, "longitude_e4": -12346},
        )
        for latitude in ("-0", "-0.0", "+1", "1e1", " 1", "91"):
            with self.subTest(latitude=latitude):
                with self.assertRaises(CuePolicyError):
                    canonical_location({"latitude": latitude, "longitude": "1"})

    def test_email_and_phone_normalization_is_strict(self) -> None:
        self.assertEqual(
            canonical_person({"type": "email", "value": "Friend@Example.ORG"}),
            {"type": "email", "value": "friend@example.org"},
        )
        self.assertEqual(
            canonical_person({"type": "phone", "value": "+352621123456"}),
            {"type": "phone", "value": "+352621123456"},
        )
        for person in (
            {"type": "email", "value": "friend@example"},
            {"type": "email", "value": "a..b@example.org"},
            {"type": "phone", "value": "+352 621 123456"},
            {"type": "phone", "value": "00352621123456"},
            {"type": "name", "value": "Friend"},
        ):
            with self.subTest(person=person):
                with self.assertRaises(CuePolicyError):
                    canonical_person(person)

    def test_pair_count_duplicates_unknown_fields_and_drift_fail(self) -> None:
        cues = sample_cues()
        for invalid in (cues[:2], [*cues, cues[0]]):
            with self.assertRaises(CuePolicyError):
                canonical_recovery_input(invalid)

        duplicate_location = sample_cues()
        duplicate_location[1]["location"] = duplicate_location[0]["location"].copy()
        with self.assertRaises(CuePolicyError):
            canonical_recovery_input(duplicate_location)

        duplicate_person = sample_cues()
        duplicate_person[1]["person"] = duplicate_person[0]["person"].copy()
        with self.assertRaises(CuePolicyError):
            canonical_recovery_input(duplicate_person)

        unknown = sample_cues()
        unknown[0]["location"]["name"] = "must not enter canonical input"
        with self.assertRaises(CuePolicyError):
            canonical_recovery_input(unknown)

        original = canonical_recovery_input(sample_cues())
        drifted = sample_cues()
        drifted[0]["location"]["latitude"] = "49.59895"
        self.assertNotEqual(original, canonical_recovery_input(drifted))


if __name__ == "__main__":
    unittest.main()
