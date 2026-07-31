"""Cryptographic helpers for the local LOCUS composition."""

from __future__ import annotations

import hashlib
import secrets
from collections.abc import Iterable

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from .codec import encode

FIELD_Q = (1 << 127) - 1
SCALAR_BYTES = 32
AES_256_KEY_BYTES = 32
AES_GCM_NONCE_BYTES = 12
AES_GCM_TAG_BYTES = 16
SEALED_VERSION = "LOCUS-AES-256-GCM-v1"
SEALED_ALGORITHM = "AES-256-GCM"


class CryptoError(Exception):
    """Raised when KDF, encoding, or authenticated encryption fails."""


def scalar_to_bytes(value: int) -> bytes:
    return int(value % FIELD_Q).to_bytes(SCALAR_BYTES, "big")


def random_scalar() -> int:
    while True:
        value = secrets.randbelow(FIELD_Q)
        if value != 0:
            return value


def random_bytes(length: int) -> bytes:
    return secrets.token_bytes(length)


def _flatten(parts: Iterable[object]) -> bytes:
    out = bytearray()
    for part in parts:
        if isinstance(part, bytes):
            data = part
        elif isinstance(part, int):
            data = scalar_to_bytes(part)
        else:
            data = encode(part)
        out.extend(len(data).to_bytes(4, "big"))
        out.extend(data)
    return bytes(out)


def hash_bytes(tag: str, *parts: object, length: int = 32) -> bytes:
    digest = hashlib.sha256()
    digest.update(tag.encode("utf-8"))
    digest.update(b"\x00")
    digest.update(_flatten(parts))
    output = digest.digest()
    if length <= len(output):
        return output[:length]
    blocks = bytearray(output)
    counter = 1
    while len(blocks) < length:
        counter += 1
        blocks.extend(hashlib.sha256(output + counter.to_bytes(4, "big")).digest())
    return bytes(blocks[:length])


def hash_scalar(tag: str, *parts: object) -> int:
    return int.from_bytes(hash_bytes(tag, *parts, length=64), "big") % FIELD_Q


def hkdf(
    ikm: bytes, *, salt: bytes = b"", info: bytes = b"", length: int = 32
) -> bytes:
    if length < 1 or length > 255 * hashlib.sha256().digest_size:
        raise CryptoError("invalid HKDF output length")
    return HKDF(
        algorithm=hashes.SHA256(),
        length=length,
        salt=salt or None,
        info=info,
    ).derive(ikm)


def _require_aes_256_key(key: bytes) -> None:
    if len(key) != AES_256_KEY_BYTES:
        raise CryptoError("invalid AES-256-GCM key length")


def _decode_canonical_hex(value: object, label: str) -> bytes:
    if not isinstance(value, str) or len(value) % 2 != 0:
        raise CryptoError(f"malformed {label}")
    try:
        decoded = bytes.fromhex(value)
    except ValueError as exc:
        raise CryptoError(f"malformed {label}") from exc
    if decoded.hex() != value:
        raise CryptoError(f"non-canonical {label}")
    return decoded


def validate_sealed(sealed: object) -> tuple[bytes, bytes]:
    """Validate and decode the exact versioned AES-GCM ciphertext format."""

    if not isinstance(sealed, dict):
        raise CryptoError("malformed sealed backup")
    expected_fields = {"version", "algorithm", "nonce", "ciphertext"}
    if set(sealed) != expected_fields:
        raise CryptoError("malformed sealed backup")
    if sealed["version"] != SEALED_VERSION:
        raise CryptoError("unsupported sealed-backup version")
    if sealed["algorithm"] != SEALED_ALGORITHM:
        raise CryptoError("unsupported sealed-backup algorithm")
    nonce = _decode_canonical_hex(sealed["nonce"], "AEAD nonce")
    ciphertext = _decode_canonical_hex(sealed["ciphertext"], "AEAD ciphertext")
    if len(nonce) != AES_GCM_NONCE_BYTES:
        raise CryptoError("invalid AEAD nonce length")
    if len(ciphertext) < AES_GCM_TAG_BYTES:
        raise CryptoError("invalid AEAD ciphertext length")
    return nonce, ciphertext


def seal(key: bytes, plaintext: bytes, *, aad: bytes) -> dict[str, str]:
    """Encrypt with AES-256-GCM and a fresh 96-bit random nonce."""

    _require_aes_256_key(key)
    nonce = random_bytes(AES_GCM_NONCE_BYTES)
    ciphertext = AESGCM(key).encrypt(nonce, plaintext, aad)
    return {
        "version": SEALED_VERSION,
        "algorithm": SEALED_ALGORITHM,
        "nonce": nonce.hex(),
        "ciphertext": ciphertext.hex(),
    }


def open_sealed(key: bytes, sealed: object, *, aad: bytes) -> bytes:
    """Authenticate and decrypt the exact versioned AES-256-GCM format."""

    _require_aes_256_key(key)
    nonce, ciphertext = validate_sealed(sealed)
    try:
        return AESGCM(key).decrypt(nonce, ciphertext, aad)
    except InvalidTag as exc:
        raise CryptoError("ciphertext authentication failed") from exc
    except (OverflowError, ValueError) as exc:
        raise CryptoError("ciphertext decryption failed") from exc
