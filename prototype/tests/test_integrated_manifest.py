from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from locus.codec import encode
from locus.integrated_manifest import (
    INTEGRATED_CONFIG_VERSION,
    INTEGRATED_DEPLOYMENT_ID,
    IntegratedManifestError,
    decode_integrated_manifest,
    load_integrated_manifest,
    validate_integrated_manifest,
)

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "deploy" / "integrated-manifest.json"


class IntegratedManifestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.value = load_integrated_manifest(MANIFEST)

    def test_canonical_manifest_binds_complete_system(self) -> None:
        self.assertEqual(self.value["version"], INTEGRATED_CONFIG_VERSION)
        self.assertEqual(self.value["deployment_id"], INTEGRATED_DEPLOYMENT_ID)
        self.assertEqual(len(self.value["arms"]), 4)
        self.assertEqual(len(self.value["services"]), 13)
        self.assertEqual(self.value["authorization"]["quorum"], 4)
        self.assertEqual(encode(self.value) + b"\n", MANIFEST.read_bytes())

    def test_duplicate_unknown_missing_and_noncanonical_json_fail(self) -> None:
        with self.assertRaises(IntegratedManifestError):
            decode_integrated_manifest(b'{"version":"x","version":"y"}')
        changed = copy.deepcopy(self.value)
        changed["unknown"] = True
        with self.assertRaises(IntegratedManifestError):
            validate_integrated_manifest(changed)
        changed = copy.deepcopy(self.value)
        del changed["provider"]
        with self.assertRaises(IntegratedManifestError):
            validate_integrated_manifest(changed)
        with self.assertRaises(IntegratedManifestError):
            decode_integrated_manifest(json.dumps(self.value).encode())

    def test_cross_arm_order_membership_and_endpoint_substitution_fail(self) -> None:
        for mutate in (
            lambda value: value["arms"].reverse(),
            lambda value: value["arms"][0].__setitem__("holders", [1, 2, 4]),
            lambda value: value["services"][0].__setitem__(
                "endpoint", "https://operator:8443"
            ),
            lambda value: value["networks"].reverse(),
        ):
            changed = copy.deepcopy(self.value)
            mutate(changed)
            with self.assertRaises(IntegratedManifestError):
                validate_integrated_manifest(changed)

    def test_manifest_rejects_secret_bearing_members(self) -> None:
        changed = copy.deepcopy(self.value)
        changed["private_key"] = "00"
        with self.assertRaises(IntegratedManifestError):
            validate_integrated_manifest(changed)
        changed = copy.deepcopy(self.value)
        changed["provider"]["password"] = "synthetic"
        with self.assertRaises(IntegratedManifestError):
            validate_integrated_manifest(changed)

    def test_manifest_size_is_bounded(self) -> None:
        with self.assertRaises(IntegratedManifestError):
            decode_integrated_manifest(b" " * (128 * 1024 + 1))


if __name__ == "__main__":
    unittest.main()
