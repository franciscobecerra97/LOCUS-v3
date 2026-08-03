"""Strict P5A.1 formats and domain framing for the LOCUS aPPSS suite.

This module deliberately contains no group or secret-sharing implementation.
It freezes the public byte boundary consumed by the separate native core.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import struct
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .codec import encode

APPSS_SUITE_ID = "LOCUS-APPSS-2HASHDH-RISTRETTO255-SHA512-GF128-v1"
APPSS_OPRF_PROFILE = "LOCUS-APPSS-OPRF-RISTRETTO255-SHA512-v1"
APPSS_PASSWORD_DOMAIN = "LOCUS-APPSS-password-input-v1"
APPSS_PROFILE_2_OF_3 = "LOCUS-APPSS-2of3-v1"
APPSS_WIRE_FORMAT = "LOCUS-APPSS-wire-v1"
APPSS_PUBLIC_STATE_FORMAT = "LOCUS-APPSS-public-state-v1"
APPSS_PARTY_STATE_FORMAT = "LOCUS-APPSS-party-state-v1"
APPSS_PENDING_STATE_FORMAT = "LOCUS-APPSS-pending-party-state-v1"
APPSS_REQUEST_FORMAT = "LOCUS-APPSS-request-v1"
APPSS_RESPONSE_FORMAT = "LOCUS-APPSS-response-v1"
APPSS_INSTALL_FORMAT = "LOCUS-APPSS-state-install-v1"
APPSS_READY_FORMAT = "LOCUS-APPSS-state-ready-v1"
APPSS_CLIENT_SESSION_FORMAT = "LOCUS-APPSS-client-session-v1"
APPSS_FORMAT_VECTORS = "LOCUS-APPSS-format-vectors-v1"
RECOVERY_SUITE_SELECTOR = "LOCUS-recovery-suite-selector-v1"
REFERENCE_BACKUP_V5 = "LOCUS-reference-backup-v5"
BACKUP_AAD_V2 = "LOCUS-backup-associated-data-v2"

YI_SUITE_ID = "LOCUS-TPASS-YI-ZK-RISTRETTO255-v1"
YI_PROFILE_2_OF_3 = "LOCUS-TPASS-YI-2of3-v1"

MAX_CONTEXT_BYTES = 4096
MAX_PUBLIC_STATE_BYTES = 4096
MAX_PARTY_STATE_BYTES = 4096
MAX_PENDING_STATE_BYTES = 4096
MAX_REQUEST_BYTES = 4096
MAX_RESPONSE_BYTES = 4096
MAX_INSTALL_BYTES = 8192
MAX_READY_BYTES = 4096
MAX_SELECTOR_BYTES = 16384
MAX_BACKUP_BYTES = 1024 * 1024
MAX_IDENTIFIER_CHARS = 255
MAX_SERVICE_IDENTITY_CHARS = 512
MAX_PARTIES = 255


class AppssFormatError(ValueError):
    """A public aPPSS object is malformed, unsupported, or misbound."""


@dataclass(frozen=True)
class AppssHolderBinding:
    index: int
    party_id: str
    service_identity: str

    def __post_init__(self) -> None:
        _positive_int(self.index, "party index", maximum=MAX_PARTIES)
        _identifier(self.party_id, "party identifier")
        _identifier(
            self.service_identity,
            "service identity",
            maximum=MAX_SERVICE_IDENTITY_CHARS,
        )


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
        raise AppssFormatError(f"invalid {label}")
    return value


def _positive_int(value: object, label: str, *, maximum: int) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not 1 <= value <= maximum
    ):
        raise AppssFormatError(f"invalid {label}")
    return value


def _lower_hex(value: object, label: str, *, bytes_length: int) -> str:
    if (
        not isinstance(value, str)
        or len(value) != bytes_length * 2
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise AppssFormatError(f"invalid {label}")
    return value


def _exact_dict(value: object, fields: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        raise AppssFormatError(f"invalid {label}")
    return value


def _u16(value: int) -> bytes:
    return struct.pack(">H", value)


def _u32(value: int) -> bytes:
    return struct.pack(">I", value)


def _u64(value: int) -> bytes:
    return struct.pack(">Q", value)


def tuple_frame(*fields: bytes) -> bytes:
    """Encode the exact u32-count/u32-length cryptographic tuple."""
    if len(fields) > 2**32 - 1:
        raise AppssFormatError("too many tuple fields")
    output = bytearray(_u32(len(fields)))
    for field in fields:
        if not isinstance(field, bytes) or len(field) > 2**32 - 1:
            raise AppssFormatError("invalid tuple field")
        output.extend(_u32(len(field)))
        output.extend(field)
    return bytes(output)


def encode_membership(holders: tuple[AppssHolderBinding, ...]) -> bytes:
    if not holders or len(holders) > MAX_PARTIES:
        raise AppssFormatError("invalid recovery membership")
    indices = [holder.index for holder in holders]
    if indices != sorted(set(indices)):
        raise AppssFormatError("noncanonical recovery membership")
    output = bytearray(_u16(len(holders)))
    for holder in holders:
        party = holder.party_id.encode("ascii")
        identity = holder.service_identity.encode("ascii")
        output.extend(_u16(holder.index))
        output.extend(_u16(len(party)))
        output.extend(party)
        output.extend(_u16(len(identity)))
        output.extend(identity)
    if len(output) > MAX_CONTEXT_BYTES:
        raise AppssFormatError("recovery membership exceeds size limit")
    return bytes(output)


def context_digest(
    *,
    backup_id: bytes,
    epoch: int,
    policy_id: str,
    holders: tuple[AppssHolderBinding, ...],
    k: int,
    n: int,
    configuration_digest: bytes,
) -> bytes:
    if len(backup_id) != 16 or len(configuration_digest) != 32:
        raise AppssFormatError("invalid epoch context digest input")
    _positive_int(epoch, "epoch", maximum=2**63 - 1)
    _identifier(policy_id, "CuePolicy identifier")
    _positive_int(k, "reconstruction threshold", maximum=MAX_PARTIES)
    _positive_int(n, "party count", maximum=MAX_PARTIES)
    if k > n or len(holders) != n:
        raise AppssFormatError("threshold does not match membership")
    framed = tuple_frame(
        b"LOCUS/aPPSS/epoch-context/v1",
        APPSS_SUITE_ID.encode("ascii"),
        backup_id,
        _u64(epoch),
        policy_id.encode("ascii"),
        encode_membership(holders),
        _u16(k),
        _u16(n),
        configuration_digest,
    )
    return hashlib.sha256(framed).digest()


def instance_id(context: bytes, holder: AppssHolderBinding) -> bytes:
    if len(context) != 32:
        raise AppssFormatError("invalid context digest")
    return tuple_frame(
        b"LOCUS/aPPSS/2HashDH/instance/v1",
        context,
        holder.party_id.encode("ascii"),
        _u16(holder.index),
    )


def derive_password_input(context: bytes, cue_policy_output: bytes) -> bytes:
    if len(context) != 32 or not isinstance(cue_policy_output, bytes):
        raise AppssFormatError("invalid password-input material")
    return hashlib.sha256(
        tuple_frame(b"LOCUS/aPPSS/password-input/v1", context, cue_policy_output)
    ).digest()


def oprf_input(instance: bytes, password_input: bytes) -> bytes:
    if not instance or len(password_input) != 32:
        raise AppssFormatError("invalid OPRF input material")
    return tuple_frame(b"LOCUS/aPPSS/2HashDH/input/v1", instance, password_input)


def oprf_mask(instance: bytes, output: bytes) -> bytes:
    if not instance or len(output) != 64:
        raise AppssFormatError("invalid OPRF output material")
    return hashlib.sha256(
        tuple_frame(b"LOCUS/aPPSS/2HashDH/mask/v1", instance, output)
    ).digest()[:16]


def encode_masked_shares(shares: tuple[tuple[int, bytes], ...]) -> bytes:
    if not shares or len(shares) > MAX_PARTIES:
        raise AppssFormatError("invalid masked-share vector")
    indices = [index for index, _ in shares]
    if indices != sorted(set(indices)):
        raise AppssFormatError("noncanonical masked-share vector")
    output = bytearray(_u16(len(shares)))
    for index, share in shares:
        _positive_int(index, "masked-share index", maximum=MAX_PARTIES)
        if not isinstance(share, bytes) or len(share) != 16:
            raise AppssFormatError("invalid masked share")
        output.extend(_u16(index))
        output.extend(share)
    return bytes(output)


def canonical_omega(shares: tuple[tuple[int, bytes], ...], commitment: bytes) -> bytes:
    if len(commitment) != 16:
        raise AppssFormatError("invalid aPPSS commitment")
    return tuple_frame(encode_masked_shares(shares), commitment)


def commit_and_secret(
    context: bytes,
    password_input: bytes,
    shares: tuple[tuple[int, bytes], ...],
    secret: bytes,
) -> tuple[bytes, bytes]:
    if len(context) != 32 or len(password_input) != 32 or len(secret) != 16:
        raise AppssFormatError("invalid commitment input")
    digest = hashlib.sha256(
        tuple_frame(
            b"LOCUS/aPPSS/commit-secret/v1",
            context,
            password_input,
            encode_masked_shares(shares),
            secret,
        )
    ).digest()
    return digest[:16], digest[16:]


def omega_digest(
    context: bytes, shares: tuple[tuple[int, bytes], ...], commitment: bytes
) -> bytes:
    if len(context) != 32:
        raise AppssFormatError("invalid context digest")
    return hashlib.sha256(
        tuple_frame(
            b"LOCUS/aPPSS/omega/v1",
            context,
            canonical_omega(shares, commitment),
        )
    ).digest()


def _validate_common(value: dict[str, Any], version: str) -> None:
    if value["version"] != version or value["suite_id"] != APPSS_SUITE_ID:
        raise AppssFormatError("unsupported aPPSS object")
    if value["profile_id"] != APPSS_PROFILE_2_OF_3:
        raise AppssFormatError("unsupported aPPSS profile")
    _lower_hex(value["context_digest"], "context digest", bytes_length=32)


def validate_public_state(value: object) -> dict[str, Any]:
    state = _exact_dict(
        value,
        {
            "commitment",
            "context_digest",
            "k",
            "masked_shares",
            "n",
            "omega_digest",
            "oprf_profile",
            "profile_id",
            "suite_id",
            "version",
        },
        "aPPSS public state",
    )
    _validate_common(state, APPSS_PUBLIC_STATE_FORMAT)
    if (
        state["oprf_profile"] != APPSS_OPRF_PROFILE
        or state["k"] != 2
        or state["n"] != 3
    ):
        raise AppssFormatError("unsupported aPPSS public parameters")
    if not isinstance(state["masked_shares"], list) or len(state["masked_shares"]) != 3:
        raise AppssFormatError("invalid aPPSS masked shares")
    shares: list[tuple[int, bytes]] = []
    for expected, raw in enumerate(state["masked_shares"], start=1):
        item = _exact_dict(raw, {"index", "value"}, "aPPSS masked share")
        if item["index"] != expected:
            raise AppssFormatError("noncanonical aPPSS masked shares")
        shares.append(
            (
                expected,
                bytes.fromhex(
                    _lower_hex(item["value"], "masked share", bytes_length=16)
                ),
            )
        )
    commitment = bytes.fromhex(
        _lower_hex(state["commitment"], "commitment", bytes_length=16)
    )
    expected_digest = omega_digest(
        bytes.fromhex(state["context_digest"]), tuple(shares), commitment
    )
    if not hmac.compare_digest(state["omega_digest"], expected_digest.hex()):
        raise AppssFormatError("aPPSS omega digest mismatch")
    return state


def validate_party_state(value: object, *, pending: bool = False) -> dict[str, Any]:
    fields = {
        "context_digest",
        "holder_id",
        "key_commitment",
        "oprf_key",
        "profile_id",
        "suite_id",
        "version",
    }
    if not pending:
        fields |= {"omega_digest", "public_state_digest"}
    state = _exact_dict(value, fields, "aPPSS party state")
    _validate_common(
        state, APPSS_PENDING_STATE_FORMAT if pending else APPSS_PARTY_STATE_FORMAT
    )
    _positive_int(state["holder_id"], "holder identifier", maximum=3)
    _lower_hex(state["oprf_key"], "OPRF key", bytes_length=32)
    _lower_hex(state["key_commitment"], "OPRF key commitment", bytes_length=32)
    if not pending:
        _lower_hex(state["omega_digest"], "omega digest", bytes_length=32)
        _lower_hex(state["public_state_digest"], "public-state digest", bytes_length=32)
    return state


def _validate_message_binding(value: dict[str, Any]) -> None:
    _lower_hex(value["session_id"], "session identifier", bytes_length=32)
    _lower_hex(value["operation_id"], "operation identifier", bytes_length=32)
    _lower_hex(value["nonce"], "message nonce", bytes_length=32)
    _lower_hex(
        value["admission_grant_digest"], "admission grant digest", bytes_length=32
    )
    _lower_hex(
        value["client_proof_key_digest"], "client proof-key digest", bytes_length=32
    )
    _positive_int(value["holder_id"], "holder identifier", maximum=3)
    if value["operation"] not in {"initialize", "recover"}:
        raise AppssFormatError("invalid aPPSS operation")


def validate_request(value: object) -> dict[str, Any]:
    request = _exact_dict(
        value,
        {
            "admission_grant_digest",
            "blinded_element",
            "client_proof_key_digest",
            "context_digest",
            "holder_id",
            "nonce",
            "omega_digest",
            "operation",
            "operation_id",
            "profile_id",
            "session_id",
            "suite_id",
            "version",
        },
        "aPPSS request",
    )
    _validate_common(request, APPSS_REQUEST_FORMAT)
    _validate_message_binding(request)
    _lower_hex(request["blinded_element"], "blinded element", bytes_length=32)
    omega = request["omega_digest"]
    if request["operation"] == "initialize":
        if omega is not None:
            raise AppssFormatError("initialization request carries omega")
    else:
        _lower_hex(omega, "omega digest", bytes_length=32)
    return request


def validate_response(value: object) -> dict[str, Any]:
    response = _exact_dict(
        value,
        {
            "admission_grant_digest",
            "client_proof_key_digest",
            "context_digest",
            "evaluated_element",
            "holder_id",
            "key_commitment",
            "nonce",
            "omega_digest",
            "operation",
            "operation_id",
            "profile_id",
            "request_digest",
            "session_id",
            "suite_id",
            "version",
        },
        "aPPSS response",
    )
    _validate_common(response, APPSS_RESPONSE_FORMAT)
    _validate_message_binding(response)
    _lower_hex(response["evaluated_element"], "evaluated element", bytes_length=32)
    _lower_hex(response["key_commitment"], "OPRF key commitment", bytes_length=32)
    _lower_hex(response["request_digest"], "request digest", bytes_length=32)
    omega = response["omega_digest"]
    if response["operation"] == "initialize":
        if omega is not None:
            raise AppssFormatError("initialization response carries omega")
    else:
        _lower_hex(omega, "omega digest", bytes_length=32)
    return response


def validate_install(value: object) -> dict[str, Any]:
    install = _exact_dict(
        value,
        {
            "context_digest",
            "holder_id",
            "initialization_transcript_digest",
            "operation_id",
            "profile_id",
            "public_state",
            "suite_id",
            "version",
        },
        "aPPSS state install",
    )
    _validate_common(install, APPSS_INSTALL_FORMAT)
    _positive_int(install["holder_id"], "holder identifier", maximum=3)
    _lower_hex(install["operation_id"], "operation identifier", bytes_length=32)
    _lower_hex(
        install["initialization_transcript_digest"],
        "initialization transcript digest",
        bytes_length=32,
    )
    public_state = validate_public_state(install["public_state"])
    if public_state["context_digest"] != install["context_digest"]:
        raise AppssFormatError("state install context mismatch")
    return install


def validate_ready(value: object) -> dict[str, Any]:
    ready = _exact_dict(
        value,
        {
            "context_digest",
            "holder_id",
            "operation_id",
            "party_state_digest",
            "profile_id",
            "public_state_digest",
            "suite_id",
            "version",
        },
        "aPPSS state-ready acknowledgement",
    )
    _validate_common(ready, APPSS_READY_FORMAT)
    _positive_int(ready["holder_id"], "holder identifier", maximum=3)
    _lower_hex(ready["operation_id"], "operation identifier", bytes_length=32)
    _lower_hex(ready["party_state_digest"], "party-state digest", bytes_length=32)
    _lower_hex(ready["public_state_digest"], "public-state digest", bytes_length=32)
    return ready


def validate_selector(value: object) -> dict[str, Any]:
    selector = _exact_dict(
        value,
        {
            "authorization_quorum",
            "authorizer_ids",
            "holder_ids",
            "k",
            "n",
            "profile_id",
            "suite_id",
            "version",
        },
        "recovery-suite selection",
    )
    if selector["version"] != RECOVERY_SUITE_SELECTOR:
        raise AppssFormatError("unsupported suite selector")
    if selector["suite_id"] == APPSS_SUITE_ID:
        if selector["profile_id"] != APPSS_PROFILE_2_OF_3:
            raise AppssFormatError("aPPSS selector profile mismatch")
    elif selector["suite_id"] == YI_SUITE_ID:
        if selector["profile_id"] != YI_PROFILE_2_OF_3:
            raise AppssFormatError("Yi selector profile mismatch")
    else:
        raise AppssFormatError("unsupported recovery suite")
    if selector["k"] != 2 or selector["n"] != 3:
        raise AppssFormatError("unsupported recovery topology")
    if selector["holder_ids"] != [1, 2, 3]:
        raise AppssFormatError("noncanonical holder membership")
    authorizers = selector["authorizer_ids"]
    if (
        not isinstance(authorizers, list)
        or not authorizers
        or authorizers != sorted(set(authorizers))
        or any(
            isinstance(item, bool)
            or not isinstance(item, int)
            or not 1 <= item <= MAX_PARTIES
            for item in authorizers
        )
    ):
        raise AppssFormatError("noncanonical authorizer membership")
    quorum = _positive_int(
        selector["authorization_quorum"],
        "authorization quorum",
        maximum=len(authorizers),
    )
    if quorum <= len(authorizers) // 2:
        raise AppssFormatError("authorization quorum is not a majority")
    return selector


def canonical_decode(
    encoded: bytes,
    *,
    maximum: int,
    validator: Callable[[object], dict[str, Any]],
    label: str,
) -> dict[str, Any]:
    if not isinstance(encoded, bytes) or not encoded or len(encoded) > maximum:
        raise AppssFormatError(f"invalid {label}")
    try:
        value = json.loads(encoded.decode("ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AppssFormatError(f"invalid {label}") from exc
    validated = validator(value)
    if encode(validated) != encoded:
        raise AppssFormatError(f"noncanonical {label}")
    return validated


def encode_checked(
    value: object,
    *,
    maximum: int,
    validator: Callable[[object], dict[str, Any]],
    label: str,
) -> bytes:
    validated = validator(value)
    encoded = encode(validated)
    if len(encoded) > maximum:
        raise AppssFormatError(f"{label} exceeds size limit")
    return encoded


__all__ = [name for name in globals() if name.startswith("APPSS_")] + [
    "BACKUP_AAD_V2",
    "REFERENCE_BACKUP_V5",
    "RECOVERY_SUITE_SELECTOR",
    "YI_PROFILE_2_OF_3",
    "YI_SUITE_ID",
    "AppssFormatError",
    "AppssHolderBinding",
    "canonical_decode",
    "canonical_omega",
    "commit_and_secret",
    "context_digest",
    "derive_password_input",
    "encode_checked",
    "encode_masked_shares",
    "encode_membership",
    "instance_id",
    "omega_digest",
    "oprf_input",
    "oprf_mask",
    "tuple_frame",
    "validate_install",
    "validate_party_state",
    "validate_public_state",
    "validate_ready",
    "validate_request",
    "validate_response",
    "validate_selector",
]
