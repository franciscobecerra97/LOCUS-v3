from __future__ import annotations

import hashlib
import json
import struct
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
VECTOR = ROOT / "prototype/test-vectors/appss-format-v1.json"
SUITE = b"LOCUS-APPSS-2HASHDH-RISTRETTO255-SHA512-GF128-v1"


def frame(*fields: bytes) -> bytes:
    return struct.pack(">I", len(fields)) + b"".join(
        struct.pack(">I", len(field)) + field for field in fields
    )


def membership(items: list[dict[str, Any]]) -> bytes:
    result = bytearray(struct.pack(">H", len(items)))
    for item in items:
        party = str(item["party_id"]).encode("ascii")
        identity = str(item["service_identity"]).encode("ascii")
        result.extend(struct.pack(">H", int(item["index"])))
        result.extend(struct.pack(">H", len(party)) + party)
        result.extend(struct.pack(">H", len(identity)) + identity)
    return bytes(result)


class IndependentAppssVectorTests(unittest.TestCase):
    def test_public_format_vector_without_locus_imports(self) -> None:
        vector = json.loads(VECTOR.read_text(encoding="utf-8"))
        context = hashlib.sha256(
            frame(
                b"LOCUS/aPPSS/epoch-context/v1",
                SUITE,
                bytes.fromhex(vector["backup_id"]),
                struct.pack(">Q", vector["epoch"]),
                vector["policy_id"].encode("ascii"),
                membership(vector["holders"]),
                struct.pack(">H", 2),
                struct.pack(">H", 3),
                bytes.fromhex(vector["configuration_digest"]),
            )
        ).digest()
        self.assertEqual(context.hex(), vector["context_digest"])
        shares = struct.pack(">H", 3) + b"".join(
            struct.pack(">H", item["index"]) + bytes.fromhex(item["value"])
            for item in vector["masked_shares"]
        )
        omega = frame(shares, bytes.fromhex(vector["commitment"]))
        digest = hashlib.sha256(
            frame(b"LOCUS/aPPSS/omega/v1", context, omega)
        ).hexdigest()
        self.assertEqual(digest, vector["omega_digest"])
        canonical_public = json.dumps(
            vector["public_state"],
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("ascii")
        canonical_selector = json.dumps(
            vector["selector"],
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("ascii")
        self.assertEqual(canonical_public.hex(), vector["public_state_canonical_hex"])
        self.assertEqual(canonical_selector.hex(), vector["selector_canonical_hex"])


if __name__ == "__main__":
    unittest.main()
