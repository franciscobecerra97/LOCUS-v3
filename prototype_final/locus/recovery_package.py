"""Strict transport package for an encrypted LOCUS recovery epoch.

The package is not a new backup construction or trust root.  It carries the
existing encrypted recovery bundle and the existing operator-signed public
receipt so a fresh managed client can authenticate them against installed
trust, account-scoped discovery, the current pointer, and party observations.
"""

from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import dataclass
from typing import Any, cast

from .codec import encode
from .recovery_bootstrap import RECOVERY_RECEIPT_VERSION
from .recovery_descriptor import BUNDLE_PROFILE, MAX_BUNDLE_BYTES

RECOVERY_PACKAGE_VERSION = "LOCUS-client-recovery-package-v1"
RECOVERY_PACKAGE_MEDIA_TYPE = "application/vnd.locus.recovery-package+json"
MAX_RECOVERY_PACKAGE_BYTES = 3 * 1024 * 1024
MAX_RECOVERY_RECEIPT_BYTES = 16 * 1024


class RecoveryPackageError(ValueError):
    """The encrypted recovery package is malformed or misbound."""


@dataclass(frozen=True)
class RecoveryPackage:
    receipt_bytes: bytes
    bundle_bytes: bytes

    @property
    def bundle_sha256(self) -> str:
        return hashlib.sha256(self.bundle_bytes).hexdigest()

    @property
    def receipt_sha256(self) -> str:
        return hashlib.sha256(self.receipt_bytes).hexdigest()


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise RecoveryPackageError("duplicate recovery-package member")
        result[key] = value
    return result


def _exact(value: object, fields: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        raise RecoveryPackageError(f"invalid {label}")
    return cast(dict[str, Any], value)


def _positive_size(value: object, *, maximum: int, label: str) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not 1 <= value <= maximum
    ):
        raise RecoveryPackageError(f"invalid {label}")
    return value


def _lower_hex(value: object, *, byte_length: int, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != byte_length * 2
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise RecoveryPackageError(f"invalid {label}")
    return value


def _base64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _decode_base64url(value: object, *, maximum: int, label: str) -> bytes:
    if (
        not isinstance(value, str)
        or not value
        or len(value) > ((maximum + 2) // 3) * 4
        or "=" in value
        or any(
            character
            not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
            for character in value
        )
    ):
        raise RecoveryPackageError(f"invalid {label}")
    try:
        decoded = base64.b64decode(
            value + "=" * ((4 - len(value) % 4) % 4),
            altchars=b"-_",
            validate=True,
        )
    except ValueError as exc:
        raise RecoveryPackageError(f"invalid {label}") from exc
    if not decoded or len(decoded) > maximum or _base64url(decoded) != value:
        raise RecoveryPackageError(f"invalid {label}")
    return decoded


def _member(
    value: object,
    *,
    expected_format: str,
    maximum: int,
    label: str,
) -> bytes:
    member = _exact(value, {"format", "length", "sha256", "value"}, label)
    if member["format"] != expected_format:
        raise RecoveryPackageError(f"unsupported {label} format")
    length = _positive_size(member["length"], maximum=maximum, label=f"{label} length")
    digest = _lower_hex(member["sha256"], byte_length=32, label=f"{label} digest")
    decoded = _decode_base64url(member["value"], maximum=maximum, label=label)
    if len(decoded) != length or hashlib.sha256(decoded).hexdigest() != digest:
        raise RecoveryPackageError(f"{label} binding mismatch")
    return decoded


def create_recovery_package(*, receipt_bytes: bytes, bundle_bytes: bytes) -> bytes:
    """Create the canonical public transport package from existing objects."""

    if (
        not isinstance(receipt_bytes, bytes)
        or not 1 <= len(receipt_bytes) <= MAX_RECOVERY_RECEIPT_BYTES
        or not isinstance(bundle_bytes, bytes)
        or not 1 <= len(bundle_bytes) <= MAX_BUNDLE_BYTES
    ):
        raise RecoveryPackageError("invalid recovery-package member")
    value = {
        "bundle": {
            "format": BUNDLE_PROFILE,
            "length": len(bundle_bytes),
            "sha256": hashlib.sha256(bundle_bytes).hexdigest(),
            "value": _base64url(bundle_bytes),
        },
        "receipt": {
            "format": RECOVERY_RECEIPT_VERSION,
            "length": len(receipt_bytes),
            "sha256": hashlib.sha256(receipt_bytes).hexdigest(),
            "value": _base64url(receipt_bytes),
        },
        "version": RECOVERY_PACKAGE_VERSION,
    }
    encoded = encode(value)
    if len(encoded) > MAX_RECOVERY_PACKAGE_BYTES:
        raise RecoveryPackageError("recovery package exceeds size limit")
    return encoded


def decode_recovery_package(encoded: bytes) -> RecoveryPackage:
    """Decode canonical bytes without treating the package as a trust root."""

    if (
        not isinstance(encoded, bytes)
        or not encoded
        or len(encoded) > MAX_RECOVERY_PACKAGE_BYTES
    ):
        raise RecoveryPackageError("invalid recovery-package size")
    try:
        value = json.loads(
            encoded.decode("utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=lambda _item: (_ for _ in ()).throw(
                RecoveryPackageError("non-finite recovery-package number")
            ),
        )
        package = _exact(value, {"bundle", "receipt", "version"}, "recovery package")
        if package["version"] != RECOVERY_PACKAGE_VERSION:
            raise RecoveryPackageError("unsupported recovery-package version")
        receipt = _member(
            package["receipt"],
            expected_format=RECOVERY_RECEIPT_VERSION,
            maximum=MAX_RECOVERY_RECEIPT_BYTES,
            label="recovery receipt",
        )
        bundle = _member(
            package["bundle"],
            expected_format=BUNDLE_PROFILE,
            maximum=MAX_BUNDLE_BYTES,
            label="recovery bundle",
        )
        if encode(package) != encoded:
            raise RecoveryPackageError("noncanonical recovery package")
        return RecoveryPackage(receipt_bytes=receipt, bundle_bytes=bundle)
    except RecoveryPackageError:
        raise
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
        RecursionError,
        TypeError,
        ValueError,
    ) as exc:
        raise RecoveryPackageError("invalid recovery package") from exc


__all__ = [
    "MAX_RECOVERY_PACKAGE_BYTES",
    "RECOVERY_PACKAGE_MEDIA_TYPE",
    "RECOVERY_PACKAGE_VERSION",
    "RecoveryPackage",
    "RecoveryPackageError",
    "create_recovery_package",
    "decode_recovery_package",
]
