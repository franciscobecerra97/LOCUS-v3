from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CORPUS_PATH = ROOT / "docs/vectors/cue-policy-conformance-v1.json"


class IndependentCuePolicyVectorTests(unittest.TestCase):
    def test_pinned_json_hex_and_digest_agree_without_locus_imports(self) -> None:
        corpus: dict[str, Any] = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
        for policy in corpus["policies"]:
            for vector in policy.get("valid", []):
                canonical = vector["canonical_json"].encode("ascii")
                independently_encoded = json.dumps(
                    json.loads(vector["canonical_json"]),
                    ensure_ascii=True,
                    separators=(",", ":"),
                    sort_keys=True,
                ).encode("ascii")
                self.assertEqual(canonical, independently_encoded)
                self.assertEqual(canonical.hex(), vector["canonical_hex"])
                self.assertEqual(
                    hashlib.sha256(canonical).hexdigest(),
                    vector["canonical_sha256"],
                )


if __name__ == "__main__":
    unittest.main()
