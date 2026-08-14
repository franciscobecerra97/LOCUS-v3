from __future__ import annotations

import json
import struct
import unittest
from pathlib import Path

from locus import _tpass_native as native
from locus.appss_formats import AppssHolderBinding, instance_id, oprf_input

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_VECTOR = ROOT / "docs/vectors/appss-format-v1.json"
NATIVE_VECTOR = ROOT / "appss-core/test-vectors/appss-2of3-public-v1.txt"


def evaluate_masks(
    keys: list[native.AppssServerKey],
    context: bytes,
    password_input: bytes,
) -> list[tuple[int, bytes]]:
    holders = [
        AppssHolderBinding(
            index=index,
            party_id=f"party-{index}",
            service_identity="spki-sha256:" + bytes([index] * 32).hex(),
        )
        for index in range(1, 4)
    ]
    masks: list[tuple[int, bytes]] = []
    for key, holder in zip(keys, holders, strict=True):
        instance = instance_id(context, holder)
        session, blinded = native.appss_blind(oprf_input(instance, password_input))
        evaluated = native.appss_blind_evaluate(key, context, blinded)
        output = native.appss_finalize(session, evaluated)
        masks.append((holder.index, native.appss_derive_mask(instance, output)))
    return masks


class NativeAppssTests(unittest.TestCase):
    def test_distributed_oprf_and_every_two_of_three_subset(self) -> None:
        context = bytes.fromhex("9a" * 32)
        password = bytes.fromhex("7b" * 32)
        keys = [
            native.appss_generate_server_key(context, index) for index in range(1, 4)
        ]
        masks = evaluate_masks(keys, context, password)
        public, expected_secret = native.appss_initialize_fixture(
            context, password, 2, 3, masks
        )
        self.assertEqual((public.threshold, public.parties), (2, 3))
        self.assertEqual(public.context_digest, context)
        self.assertEqual(len(expected_secret), 16)
        for subset in ((0, 1), (0, 2), (1, 2)):
            selected = [masks[index] for index in subset]
            self.assertEqual(
                native.appss_recover_fixture(context, password, public, selected),
                expected_secret,
            )

    def test_wrong_password_and_cross_context_reject(self) -> None:
        context = bytes.fromhex("8c" * 32)
        correct = bytes.fromhex("6d" * 32)
        wrong = bytes.fromhex("6e" * 32)
        keys = [
            native.appss_generate_server_key(context, index) for index in range(1, 4)
        ]
        correct_masks = evaluate_masks(keys, context, correct)
        public, _ = native.appss_initialize_fixture(
            context, correct, 2, 3, correct_masks
        )
        wrong_masks = evaluate_masks(keys, context, wrong)
        with self.assertRaises(native.NativeAppssError):
            native.appss_recover_fixture(context, wrong, public, wrong_masks[:2])
        with self.assertRaises(native.NativeAppssError):
            native.appss_recover_fixture(
                bytes.fromhex("8d" * 32), correct, public, correct_masks[:2]
            )

    def test_party_key_and_public_state_codecs_are_strict_and_redacted(self) -> None:
        context = bytes.fromhex("5a" * 32)
        key = native.appss_generate_server_key(context, 1)
        encoded = key.to_secret_bytes()
        decoded = native.AppssServerKey.from_secret_bytes(encoded)
        self.assertEqual(decoded.holder_id, 1)
        self.assertEqual(decoded.context_digest, context)
        self.assertEqual(decoded.commitment(), key.commitment())
        self.assertIn("<redacted>", repr(decoded))
        for malformed in (encoded[:-1], encoded + b"\x00", b"\x00" * len(encoded)):
            with self.assertRaises(native.NativeAppssError):
                native.AppssServerKey.from_secret_bytes(malformed)

        masks = [(1, b"\x01" * 16), (2, b"\x02" * 16), (3, b"\x03" * 16)]
        public, _ = native.appss_initialize_fixture(context, b"\x04" * 32, 2, 3, masks)
        public_bytes = public.to_bytes()
        self.assertEqual(
            native.AppssPublicState.from_bytes(public_bytes).to_bytes(), public_bytes
        )
        for malformed in (public_bytes[:-1], public_bytes + b"\x00"):
            with self.assertRaises(native.NativeAppssError):
                native.AppssPublicState.from_bytes(malformed)

    def test_public_format_vector_crosses_native_boundary_without_secrets(self) -> None:
        vector = json.loads(PUBLIC_VECTOR.read_text(encoding="utf-8"))
        native_bytes = bytearray(b"LAP1\x01")
        native_bytes.extend(bytes.fromhex(vector["context_digest"]))
        native_bytes.extend(struct.pack(">HHH", 2, 3, 3))
        for item in vector["masked_shares"]:
            native_bytes.extend(struct.pack(">H", item["index"]))
            native_bytes.extend(bytes.fromhex(item["value"]))
        native_bytes.extend(bytes.fromhex(vector["commitment"]))
        native_bytes.extend(bytes.fromhex(vector["omega_digest"]))
        state = native.AppssPublicState.from_bytes(bytes(native_bytes))
        self.assertEqual(state.to_bytes(), bytes(native_bytes))
        self.assertEqual(state.omega_digest.hex(), vector["omega_digest"])
        self.assertEqual(
            state.masked_shares,
            [
                (item["index"], bytes.fromhex(item["value"]))
                for item in vector["masked_shares"]
            ],
        )

        native_vector = dict(
            line.split("=", 1)
            for line in NATIVE_VECTOR.read_text(encoding="ascii").splitlines()
        )
        native_state = bytes.fromhex(native_vector["public_state_hex"])
        self.assertEqual(
            native.AppssPublicState.from_bytes(native_state).to_bytes(), native_state
        )
        self.assertNotIn("password", native_vector)
        self.assertNotIn("recovery_secret", native_vector)
        self.assertNotIn("oprf_key", native_vector)

    def test_identity_and_consumed_blind_fail_closed(self) -> None:
        context = bytes.fromhex("4f" * 32)
        key = native.appss_generate_server_key(context, 1)
        with self.assertRaises(native.NativeAppssError):
            native.appss_blind_evaluate(key, context, b"\x00" * 32)
        session, blinded = native.appss_blind(b"synthetic bounded input")
        evaluated = native.appss_blind_evaluate(key, context, blinded)
        self.assertEqual(len(native.appss_finalize(session, evaluated)), 64)
        with self.assertRaises(native.NativeAppssError):
            native.appss_finalize(session, evaluated)


if __name__ == "__main__":
    unittest.main()
