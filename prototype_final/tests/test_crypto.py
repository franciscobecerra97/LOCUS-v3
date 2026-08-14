from __future__ import annotations

import copy
import unittest

from locus.crypto import CryptoError, hkdf, open_sealed, seal, validate_sealed


class StandardCryptoTests(unittest.TestCase):
    key = bytes(range(32))
    plaintext = b"synthetic private key material"
    aad = b"canonical LOCUS backup metadata"

    def test_aes_256_gcm_round_trip_and_fresh_nonce(self) -> None:
        first = seal(self.key, self.plaintext, aad=self.aad)
        second = seal(self.key, self.plaintext, aad=self.aad)

        self.assertEqual(open_sealed(self.key, first, aad=self.aad), self.plaintext)
        self.assertEqual(open_sealed(self.key, second, aad=self.aad), self.plaintext)
        self.assertNotEqual(first["nonce"], second["nonce"])
        self.assertEqual(len(bytes.fromhex(first["nonce"])), 12)
        self.assertEqual(
            len(bytes.fromhex(first["ciphertext"])), 16 + len(self.plaintext)
        )

    def test_wrong_associated_data_fails_authentication(self) -> None:
        sealed = seal(self.key, self.plaintext, aad=self.aad)
        with self.assertRaisesRegex(CryptoError, "authentication failed"):
            open_sealed(self.key, sealed, aad=b"different metadata")

    def test_tampered_nonce_and_ciphertext_fail_authentication(self) -> None:
        sealed = seal(self.key, self.plaintext, aad=self.aad)
        for field in ("nonce", "ciphertext"):
            with self.subTest(field=field):
                tampered = copy.deepcopy(sealed)
                encoded = tampered[field]
                tampered[field] = ("00" if encoded[:2] != "00" else "ff") + encoded[2:]
                with self.assertRaisesRegex(CryptoError, "authentication failed"):
                    open_sealed(self.key, tampered, aad=self.aad)

    def test_exact_format_rejects_malformed_or_unsupported_values(self) -> None:
        sealed = seal(self.key, self.plaintext, aad=self.aad)
        mutations = []

        missing = copy.deepcopy(sealed)
        del missing["algorithm"]
        mutations.append(missing)

        extra = copy.deepcopy(sealed)
        extra["tag"] = "00" * 16
        mutations.append(extra)

        wrong_version = copy.deepcopy(sealed)
        wrong_version["version"] = "LOCUS-AES-256-GCM-v0"
        mutations.append(wrong_version)

        wrong_algorithm = copy.deepcopy(sealed)
        wrong_algorithm["algorithm"] = "AES-128-GCM"
        mutations.append(wrong_algorithm)

        short_nonce = copy.deepcopy(sealed)
        short_nonce["nonce"] = "00" * 11
        mutations.append(short_nonce)

        short_ciphertext = copy.deepcopy(sealed)
        short_ciphertext["ciphertext"] = "00" * 15
        mutations.append(short_ciphertext)

        noncanonical_hex = copy.deepcopy(sealed)
        noncanonical_hex["nonce"] = "AA" + noncanonical_hex["nonce"][2:]
        mutations.append(noncanonical_hex)

        for mutation in mutations:
            with self.subTest(mutation=mutation):
                with self.assertRaises(CryptoError):
                    validate_sealed(mutation)

    def test_aes_256_key_length_is_enforced(self) -> None:
        with self.assertRaisesRegex(CryptoError, "key length"):
            seal(b"short", self.plaintext, aad=self.aad)
        sealed = seal(self.key, self.plaintext, aad=self.aad)
        with self.assertRaisesRegex(CryptoError, "key length"):
            open_sealed(b"short", sealed, aad=self.aad)

    def test_hkdf_sha256_matches_rfc_5869_test_case_one(self) -> None:
        output = hkdf(
            bytes.fromhex("0b" * 22),
            salt=bytes.fromhex("000102030405060708090a0b0c"),
            info=bytes.fromhex("f0f1f2f3f4f5f6f7f8f9"),
            length=42,
        )
        self.assertEqual(
            output.hex(),
            "3cb25f25faacd57a90434f64d0362f2a"
            "2d2d0a90cf1a5a4c5db02d56ecc4c5bf"
            "34007208d5b887185865",
        )


if __name__ == "__main__":
    unittest.main()
