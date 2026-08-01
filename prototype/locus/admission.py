"""Strict provider-neutral P3 admission contract and canonical wire codecs."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, cast

from .codec import encode
from .crypto import hash_bytes

ADMISSION_BINDING_FORMAT = "LOCUS-admission-binding-v1"
ADMISSION_CAPABILITY_FORMAT = "LOCUS-admission-capability-v1"
CLIENT_PROOF_FORMAT = "LOCUS-admission-client-proof-v1"
LOCAL_ISSUER_PROFILE = "LOCUS-local-synthetic-admission-v1"
ADMISSION_REPLAY_PROFILE = "LOCUS-admission-replay-v1"

RECOVERY_OPERATION = "recovery_attempt"
STORAGE_OPERATIONS = frozenset(
    {
        "storage_compare_and_swap",
        "storage_create_immutable",
        "storage_delete_exact",
        "storage_read_exact",
    }
)
OPERATIONS = frozenset({RECOVERY_OPERATION, *STORAGE_OPERATIONS})

MAX_ADMISSION_BYTES = 16 * 1024
MAX_IDENTIFIER_CHARS = 255
MAX_PREFIX_CHARS = 512
MAX_CAPABILITY_LIFETIME_SECONDS = 300
MAX_EPOCH = 2**63 - 1


class AdmissionContractError(ValueError):
    """Admission input failed before issuer or proof-key validation."""


def _exact_dict(value: object, fields: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        raise AdmissionContractError(f"invalid {label}")
    return cast(dict[str, Any], value)


def _identifier(
    value: object, label: str, *, maximum: int = MAX_IDENTIFIER_CHARS
) -> str:
    if (
        not isinstance(value, str)
        or not value
        or len(value) > maximum
        or not value.isascii()
        or any(ord(character) < 0x21 or ord(character) > 0x7E for character in value)
    ):
        raise AdmissionContractError(f"invalid {label}")
    return value


def _lower_hex(value: object, label: str, *, byte_length: int) -> str:
    if (
        not isinstance(value, str)
        or len(value) != byte_length * 2
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise AdmissionContractError(f"invalid {label}")
    return value


def _positive_int(value: object, label: str) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < 1
        or value > MAX_EPOCH
    ):
        raise AdmissionContractError(f"invalid {label}")
    return value


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON member")
        result[key] = value
    return result


def decode_canonical_object(encoded: bytes, label: str) -> dict[str, Any]:
    if (
        not isinstance(encoded, bytes)
        or not encoded
        or len(encoded) > MAX_ADMISSION_BYTES
    ):
        raise AdmissionContractError(f"invalid {label}")
    try:
        value = json.loads(
            encoded.decode("utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=lambda _value: (_ for _ in ()).throw(
                ValueError("non-finite JSON number")
            ),
        )
        if not isinstance(value, dict) or encode(value) != encoded:
            raise ValueError("noncanonical JSON")
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
        TypeError,
        ValueError,
        RecursionError,
    ) as exc:
        raise AdmissionContractError(f"invalid {label}") from exc
    return cast(dict[str, Any], value)


def pseudonymous_object_prefix(subject: str, backup_id: str) -> str:
    """Derive the only storage prefix a subject/backup binding may authorize."""

    subject_bytes = bytes.fromhex(
        _lower_hex(subject, "admission subject", byte_length=32)
    )
    backup_bytes = bytes.fromhex(
        _lower_hex(backup_id, "admission backup identifier", byte_length=16)
    )
    account = hash_bytes("LOCUS/storage-pseudonymous-subject/v1", subject_bytes).hex()
    return f"subjects/{account}/backups/{backup_bytes.hex()}/"


@dataclass(frozen=True)
class AdmissionBinding:
    subject: str
    backup_id: str
    epoch: int
    operation: str
    audience: str
    client_key_thumbprint: str
    nonce: str
    issued_at: int
    expires_at: int
    issuer: str
    profile_id: str = LOCAL_ISSUER_PROFILE
    object_prefix: str | None = None
    format_id: str = ADMISSION_BINDING_FORMAT

    def validate(self) -> None:
        if self.format_id != ADMISSION_BINDING_FORMAT:
            raise AdmissionContractError("unsupported admission binding format")
        _lower_hex(self.subject, "admission subject", byte_length=32)
        _lower_hex(self.backup_id, "admission backup identifier", byte_length=16)
        _positive_int(self.epoch, "admission epoch")
        if self.operation not in OPERATIONS:
            raise AdmissionContractError("invalid admission operation")
        _identifier(self.audience, "admission audience")
        _lower_hex(self.client_key_thumbprint, "client-key thumbprint", byte_length=32)
        _lower_hex(self.nonce, "admission nonce", byte_length=32)
        _positive_int(self.issued_at, "admission issuance time")
        _positive_int(self.expires_at, "admission expiry")
        if (
            self.expires_at <= self.issued_at
            or self.expires_at - self.issued_at > MAX_CAPABILITY_LIFETIME_SECONDS
        ):
            raise AdmissionContractError("invalid admission lifetime")
        _identifier(self.issuer, "admission issuer")
        if self.profile_id != LOCAL_ISSUER_PROFILE:
            raise AdmissionContractError("unsupported admission profile")
        if self.operation == RECOVERY_OPERATION:
            if self.object_prefix is not None:
                raise AdmissionContractError("recovery admission carries a prefix")
        else:
            if self.object_prefix != pseudonymous_object_prefix(
                self.subject, self.backup_id
            ):
                raise AdmissionContractError("storage admission prefix mismatch")
            _identifier(
                self.object_prefix, "storage object prefix", maximum=MAX_PREFIX_CHARS
            )

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "audience": self.audience,
            "backup_id": self.backup_id,
            "client_key_thumbprint": self.client_key_thumbprint,
            "epoch": self.epoch,
            "expires_at": self.expires_at,
            "format_id": self.format_id,
            "issued_at": self.issued_at,
            "issuer": self.issuer,
            "nonce": self.nonce,
            "object_prefix": self.object_prefix,
            "operation": self.operation,
            "profile_id": self.profile_id,
            "subject": self.subject,
        }

    @classmethod
    def from_dict(cls, value: object) -> AdmissionBinding:
        parsed = _exact_dict(
            value,
            {
                "audience",
                "backup_id",
                "client_key_thumbprint",
                "epoch",
                "expires_at",
                "format_id",
                "issued_at",
                "issuer",
                "nonce",
                "object_prefix",
                "operation",
                "profile_id",
                "subject",
            },
            "admission binding",
        )
        binding = cls(**parsed)
        binding.validate()
        return binding

    @property
    def canonical_bytes(self) -> bytes:
        return encode(self.to_dict())

    @property
    def digest(self) -> str:
        return hash_bytes("LOCUS/admission-binding/v1", self.canonical_bytes).hex()


def decode_binding(encoded: bytes) -> AdmissionBinding:
    return AdmissionBinding.from_dict(
        decode_canonical_object(encoded, "admission binding")
    )


def client_key_thumbprint(public_key: bytes) -> str:
    if not isinstance(public_key, bytes) or len(public_key) != 32:
        raise AdmissionContractError("invalid client proof key")
    return hash_bytes("LOCUS/admission-client-key/v1", public_key).hex()


__all__ = [
    "ADMISSION_BINDING_FORMAT",
    "ADMISSION_CAPABILITY_FORMAT",
    "ADMISSION_REPLAY_PROFILE",
    "CLIENT_PROOF_FORMAT",
    "LOCAL_ISSUER_PROFILE",
    "MAX_CAPABILITY_LIFETIME_SECONDS",
    "RECOVERY_OPERATION",
    "STORAGE_OPERATIONS",
    "AdmissionBinding",
    "AdmissionContractError",
    "client_key_thumbprint",
    "decode_binding",
    "pseudonymous_object_prefix",
]
