"""P2.2 clean-client discovery and trust-bootstrap validation.

The caller obtains pointer and bundle bytes through the account-scoped gateway.
This module authenticates those untrusted bytes against an installed trust
configuration and a quorum of short-lived party current-state summaries.  It
does not implement the P2.3 store or the P3 admission transport.
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from .codec import encode
from .contracts import (
    AuthorizerEndpoint,
    PartyDirectory,
    PartyDirectorySnapshot,
    RecoveryHolder,
    ThresholdParameters,
)
from .recovery_descriptor import (
    RecoveryBundle,
    RecoveryDescriptorError,
    _decode_canonical_json,
    _endpoint,
    _exact_dict,
    _identifier,
    _integer,
    _lower_hex,
    _sign_envelope,
    _verify_envelope,
    decode_bundle,
    decode_current_pointer,
    verify_current_pointer_bundle,
)

BOOTSTRAP_PROFILE = "LOCUS-account-scoped-bootstrap-v1"
TRUST_CONFIGURATION_VERSION = "LOCUS-bootstrap-trust-config-v1"
RECOVERY_RECEIPT_VERSION = "LOCUS-recovery-receipt-v1"
PARTY_CURRENT_SUMMARY_VERSION = "LOCUS-party-current-summary-v1"
PARTY_CURRENT_SIGNATURE_VERSION = "LOCUS-party-current-signature-v1"

PARTY_SIGNATURE_ALGORITHM = "Ed25519"
MAX_TRUST_CONFIGURATION_BYTES = 64 * 1024
MAX_RECOVERY_RECEIPT_BYTES = 16 * 1024
MAX_PARTY_CURRENT_SUMMARY_BYTES = 16 * 1024
MAX_CURRENT_SUMMARY_LIFETIME_SECONDS = 300
MAX_PARTIES = 65535


class BootstrapFailureCode(Enum):
    INVALID_TRUST_CONFIGURATION = "invalid_trust_configuration"
    TRUST_CONFIGURATION_EXPIRED = "trust_configuration_expired"
    UNTRUSTED_DISCOVERY_ENDPOINT = "untrusted_discovery_endpoint"
    INVALID_RECEIPT = "invalid_receipt"
    INVALID_CURRENT_POINTER = "invalid_current_pointer"
    INVALID_RECOVERY_BUNDLE = "invalid_recovery_bundle"
    EXPIRED_RECOVERY_STATE = "expired_recovery_state"
    RECOVERY_IDENTITY_MISMATCH = "recovery_identity_mismatch"
    UNTRUSTED_PARTY_DIRECTORY = "untrusted_party_directory"
    INVALID_PARTY_SUMMARY = "invalid_party_summary"
    CURRENT_STATE_QUORUM_UNAVAILABLE = "current_state_quorum_unavailable"
    CLOUD_PARTY_STATE_MISMATCH = "cloud_party_state_mismatch"


class RecoveryBootstrapError(ValueError):
    """Fail-closed P2.2 error with a bounded, non-secret category."""

    def __init__(self, code: BootstrapFailureCode, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class PartyCurrentObservation:
    """One response observed at an externally pinned party endpoint."""

    authorizer_id: int
    endpoint: str
    summary_bytes: bytes = field(repr=False)


@dataclass(frozen=True)
class AuthenticatedPartyDirectory:
    """P1.3 directory contract backed by one authenticated bootstrap result."""

    recovery_handle: str
    epoch: int
    snapshot: PartyDirectorySnapshot

    def resolve(self, recovery_handle: str, epoch: int) -> PartyDirectorySnapshot:
        if recovery_handle != self.recovery_handle or epoch != self.epoch:
            raise RecoveryBootstrapError(
                BootstrapFailureCode.RECOVERY_IDENTITY_MISMATCH,
                "authenticated party directory binding mismatch",
            )
        return self.snapshot


@dataclass(frozen=True)
class RecoveryBootstrapResult:
    """Public authenticated bootstrap state; contains no cue or recovery secret."""

    bundle: RecoveryBundle = field(repr=False)
    current_pointer: dict[str, Any] = field(repr=False)
    directory: AuthenticatedPartyDirectory
    matching_authorizers: tuple[int, ...]
    dissenting_authorizers: tuple[int, ...]
    receipt_verified: bool


def _active_interval(
    value: dict[str, Any], *, now: int, issued: str, expires: str
) -> bool:
    return value[issued] <= now < value[expires]


def _public_key(value: str, label: str) -> Ed25519PublicKey:
    _lower_hex(value, label, byte_length=32)
    try:
        return Ed25519PublicKey.from_public_bytes(bytes.fromhex(value))
    except ValueError as exc:
        raise RecoveryDescriptorError(f"invalid {label}") from exc


def _validate_operator(value: object) -> dict[str, Any]:
    operator = _exact_dict(
        value,
        {"issuer", "key_id", "public_key_hex"},
        "bootstrap operator trust",
    )
    _identifier(operator["issuer"], "bootstrap issuer")
    _identifier(operator["key_id"], "bootstrap operator key identifier")
    _public_key(operator["public_key_hex"], "bootstrap operator public key")
    return operator


def _validate_discovery(value: object) -> dict[str, Any]:
    discovery = _exact_dict(
        value,
        {"audience", "endpoint"},
        "bootstrap discovery trust",
    )
    _identifier(discovery["audience"], "bootstrap discovery audience")
    _endpoint(discovery["endpoint"])
    return discovery


def _validate_trusted_party(value: object) -> dict[str, Any]:
    party = _exact_dict(
        value,
        {"authorizer_id", "endpoint", "identity_key_id", "public_key_hex"},
        "bootstrap party trust",
    )
    _integer(
        party["authorizer_id"],
        "bootstrap authorizer identifier",
        minimum=1,
        maximum=MAX_PARTIES,
    )
    _endpoint(party["endpoint"])
    _identifier(party["identity_key_id"], "bootstrap party key identifier")
    _public_key(party["public_key_hex"], "bootstrap party public key")
    return party


def validate_trust_configuration(value: object) -> dict[str, Any]:
    configuration = _exact_dict(
        value,
        {
            "discovery",
            "generation",
            "operator",
            "parties",
            "previous_configuration_sha256",
            "profile",
            "valid_from",
            "valid_until",
            "version",
        },
        "bootstrap trust configuration",
    )
    if configuration["version"] != TRUST_CONFIGURATION_VERSION:
        raise RecoveryDescriptorError("unsupported bootstrap trust configuration")
    if configuration["profile"] != BOOTSTRAP_PROFILE:
        raise RecoveryDescriptorError("unsupported bootstrap profile")
    _integer(
        configuration["generation"],
        "bootstrap trust generation",
        minimum=1,
        maximum=2**63 - 1,
    )
    _integer(
        configuration["valid_from"],
        "bootstrap trust validity start",
        minimum=1,
        maximum=2**63 - 1,
    )
    _integer(
        configuration["valid_until"],
        "bootstrap trust validity end",
        minimum=1,
        maximum=2**63 - 1,
    )
    if configuration["valid_until"] <= configuration["valid_from"]:
        raise RecoveryDescriptorError("invalid bootstrap trust validity interval")
    previous = configuration["previous_configuration_sha256"]
    if configuration["generation"] == 1:
        if previous is not None:
            raise RecoveryDescriptorError("initial trust configuration has predecessor")
    else:
        _lower_hex(previous, "previous trust configuration digest", byte_length=32)
    _validate_operator(configuration["operator"])
    _validate_discovery(configuration["discovery"])
    parties = configuration["parties"]
    if not isinstance(parties, list) or not parties or len(parties) > MAX_PARTIES:
        raise RecoveryDescriptorError("invalid bootstrap trusted party set")
    validated = [_validate_trusted_party(item) for item in parties]
    party_ids = [item["authorizer_id"] for item in validated]
    if party_ids != sorted(set(party_ids)):
        raise RecoveryDescriptorError("noncanonical bootstrap trusted party set")
    endpoints = [item["endpoint"] for item in validated]
    key_ids = [item["identity_key_id"] for item in validated]
    if len(endpoints) != len(set(endpoints)) or len(key_ids) != len(set(key_ids)):
        raise RecoveryDescriptorError("duplicate bootstrap party trust binding")
    return configuration


def decode_trust_configuration(encoded: bytes) -> dict[str, Any]:
    value = _decode_canonical_json(
        encoded,
        maximum=MAX_TRUST_CONFIGURATION_BYTES,
        label="bootstrap trust configuration",
    )
    return validate_trust_configuration(value)


def validate_trust_configuration_update(
    previous_bytes: bytes, replacement_bytes: bytes, *, now: int
) -> dict[str, Any]:
    """Validate continuity between two already trusted installation inputs.

    This does not authenticate the update channel.  The replacement must be
    delivered by the application's trusted installation/update mechanism.
    """

    previous = decode_trust_configuration(previous_bytes)
    replacement = decode_trust_configuration(replacement_bytes)
    if replacement["generation"] != previous["generation"] + 1:
        raise RecoveryDescriptorError("nonconsecutive trust configuration update")
    if replacement["profile"] != previous["profile"]:
        raise RecoveryDescriptorError("bootstrap profile changed during trust update")
    if (
        replacement["previous_configuration_sha256"]
        != hashlib.sha256(previous_bytes).hexdigest()
    ):
        raise RecoveryDescriptorError("trust configuration predecessor mismatch")
    if not _active_interval(
        replacement, now=now, issued="valid_from", expires="valid_until"
    ):
        raise RecoveryDescriptorError("replacement trust configuration is not active")
    return replacement


def validate_recovery_receipt_payload(value: object) -> dict[str, Any]:
    payload = _exact_dict(
        value,
        {
            "discovery_endpoint",
            "discovery_profile",
            "initial",
            "issued_at",
            "issuer",
            "operator_key_id",
            "recovery_handle",
            "subject_id",
        },
        "recovery receipt payload",
    )
    _identifier(payload["issuer"], "recovery receipt issuer")
    _integer(
        payload["issued_at"],
        "recovery receipt issuance time",
        minimum=1,
        maximum=2**63 - 1,
    )
    _lower_hex(payload["subject_id"], "recovery receipt subject", byte_length=32)
    _identifier(payload["recovery_handle"], "recovery receipt handle")
    if payload["discovery_profile"] != BOOTSTRAP_PROFILE:
        raise RecoveryDescriptorError("unsupported recovery receipt profile")
    _endpoint(payload["discovery_endpoint"])
    _identifier(payload["operator_key_id"], "recovery receipt operator key")
    initial = payload["initial"]
    if initial is not None:
        initial = _exact_dict(
            initial,
            {
                "backup_id",
                "configuration_digest",
                "descriptor_sha256",
                "epoch",
            },
            "recovery receipt initial binding",
        )
        _lower_hex(initial["backup_id"], "receipt backup identifier", byte_length=16)
        _integer(
            initial["epoch"],
            "receipt initial epoch",
            minimum=1,
            maximum=2**63 - 1,
        )
        _lower_hex(
            initial["configuration_digest"],
            "receipt initial configuration digest",
            byte_length=32,
        )
        _lower_hex(
            initial["descriptor_sha256"],
            "receipt initial descriptor digest",
            byte_length=32,
        )
    return payload


def create_recovery_receipt(
    payload: dict[str, Any], *, signer: Ed25519PrivateKey, key_id: str
) -> bytes:
    validated = validate_recovery_receipt_payload(payload)
    encoded = _sign_envelope(
        object_version=RECOVERY_RECEIPT_VERSION,
        payload=validated,
        signer=signer,
        key_id=key_id,
    )
    if len(encoded) > MAX_RECOVERY_RECEIPT_BYTES:
        raise RecoveryDescriptorError("recovery receipt exceeds size limit")
    return encoded


def decode_recovery_receipt(
    encoded: bytes,
    *,
    issuer_public_key: Ed25519PublicKey,
    expected_issuer: str,
    expected_key_id: str,
) -> dict[str, Any]:
    return _verify_envelope(
        encoded,
        object_version=RECOVERY_RECEIPT_VERSION,
        maximum=MAX_RECOVERY_RECEIPT_BYTES,
        label="recovery receipt",
        payload_validator=validate_recovery_receipt_payload,
        issuer_public_key=issuer_public_key,
        expected_issuer=expected_issuer,
        expected_key_id=expected_key_id,
    )


def validate_party_current_summary_payload(value: object) -> dict[str, Any]:
    payload = _exact_dict(
        value,
        {
            "authorizer_id",
            "backup_id",
            "configuration_digest",
            "cue_policy_id",
            "descriptor_sha256",
            "epoch",
            "expires_at",
            "issued_at",
            "recovery_id",
            "recovery_suite_id",
            "state",
            "subject_id",
        },
        "party current-state summary payload",
    )
    _integer(
        payload["authorizer_id"],
        "current-state authorizer identifier",
        minimum=1,
        maximum=MAX_PARTIES,
    )
    _lower_hex(payload["subject_id"], "current-state subject", byte_length=32)
    _lower_hex(payload["backup_id"], "current-state backup identifier", byte_length=16)
    _identifier(payload["recovery_id"], "current-state recovery identifier")
    _integer(
        payload["epoch"],
        "current-state epoch",
        minimum=1,
        maximum=2**63 - 1,
    )
    for member, label in (
        ("descriptor_sha256", "current-state descriptor digest"),
        ("configuration_digest", "current-state configuration digest"),
    ):
        _lower_hex(payload[member], label, byte_length=32)
    _identifier(payload["cue_policy_id"], "current-state CuePolicy identifier")
    _identifier(payload["recovery_suite_id"], "current-state suite identifier")
    if payload["state"] != "active":
        raise RecoveryDescriptorError("party current state is not active")
    for member, label in (
        ("issued_at", "current-state issuance time"),
        ("expires_at", "current-state expiry"),
    ):
        _integer(payload[member], label, minimum=1, maximum=2**63 - 1)
    lifetime = payload["expires_at"] - payload["issued_at"]
    if lifetime < 1 or lifetime > MAX_CURRENT_SUMMARY_LIFETIME_SECONDS:
        raise RecoveryDescriptorError("invalid current-state summary lifetime")
    return payload


def _party_signature_message(*, payload: dict[str, Any], key_id: str) -> bytes:
    signed = {
        "object_version": PARTY_CURRENT_SUMMARY_VERSION,
        "payload": payload,
        "signature": {
            "algorithm": PARTY_SIGNATURE_ALGORITHM,
            "key_id": key_id,
            "version": PARTY_CURRENT_SIGNATURE_VERSION,
        },
    }
    return b"LOCUS/party-current-summary/v1\x00" + encode(signed)


def create_party_current_summary(
    payload: dict[str, Any], *, signer: Ed25519PrivateKey, key_id: str
) -> bytes:
    validated = validate_party_current_summary_payload(payload)
    _identifier(key_id, "party current-state signing key")
    signature = signer.sign(_party_signature_message(payload=validated, key_id=key_id))
    encoded = encode(
        {
            "payload": validated,
            "signature": {
                "algorithm": PARTY_SIGNATURE_ALGORITHM,
                "key_id": key_id,
                "value": signature.hex(),
                "version": PARTY_CURRENT_SIGNATURE_VERSION,
            },
            "version": PARTY_CURRENT_SUMMARY_VERSION,
        }
    )
    if len(encoded) > MAX_PARTY_CURRENT_SUMMARY_BYTES:
        raise RecoveryDescriptorError("party current-state summary exceeds size limit")
    return encoded


def decode_party_current_summary(
    encoded: bytes,
    *,
    party_public_key: Ed25519PublicKey,
    expected_key_id: str,
) -> dict[str, Any]:
    envelope = _decode_canonical_json(
        encoded,
        maximum=MAX_PARTY_CURRENT_SUMMARY_BYTES,
        label="party current-state summary",
    )
    envelope = _exact_dict(
        envelope,
        {"payload", "signature", "version"},
        "party current-state summary",
    )
    if envelope["version"] != PARTY_CURRENT_SUMMARY_VERSION:
        raise RecoveryDescriptorError("unsupported party current-state summary")
    payload = validate_party_current_summary_payload(envelope["payload"])
    signature = _exact_dict(
        envelope["signature"],
        {"algorithm", "key_id", "value", "version"},
        "party current-state signature",
    )
    if (
        signature["version"] != PARTY_CURRENT_SIGNATURE_VERSION
        or signature["algorithm"] != PARTY_SIGNATURE_ALGORITHM
    ):
        raise RecoveryDescriptorError("unsupported party current-state signature")
    _identifier(signature["key_id"], "party current-state signing key")
    _lower_hex(signature["value"], "party current-state signature", byte_length=64)
    if signature["key_id"] != expected_key_id:
        raise RecoveryDescriptorError("party current-state signing key mismatch")
    try:
        party_public_key.verify(
            bytes.fromhex(signature["value"]),
            _party_signature_message(payload=payload, key_id=signature["key_id"]),
        )
    except (InvalidSignature, ValueError) as exc:
        raise RecoveryDescriptorError("invalid party current-state signature") from exc
    return envelope


def _require_active_public_object(
    payload: dict[str, Any], *, now: int, label: str
) -> None:
    if not _active_interval(payload, now=now, issued="issued_at", expires="expires_at"):
        raise RecoveryBootstrapError(
            BootstrapFailureCode.EXPIRED_RECOVERY_STATE,
            f"{label} is not currently valid",
        )


def _trusted_directory(
    descriptor_payload: dict[str, Any], trust: dict[str, Any]
) -> PartyDirectorySnapshot:
    descriptor_authorizers = descriptor_payload["authorization"]["authorizers"]
    trusted_parties = trust["parties"]
    if len(descriptor_authorizers) != len(trusted_parties):
        raise RecoveryBootstrapError(
            BootstrapFailureCode.UNTRUSTED_PARTY_DIRECTORY,
            "descriptor party set differs from installed trust configuration",
        )
    authorizers: list[AuthorizerEndpoint] = []
    for descriptor_party, trusted_party in zip(
        descriptor_authorizers, trusted_parties, strict=True
    ):
        if (
            descriptor_party["authorizer_id"] != trusted_party["authorizer_id"]
            or descriptor_party["endpoint"] != trusted_party["endpoint"]
            or descriptor_party["identity_key_id"] != trusted_party["identity_key_id"]
        ):
            raise RecoveryBootstrapError(
                BootstrapFailureCode.UNTRUSTED_PARTY_DIRECTORY,
                "descriptor party binding differs from installed trust configuration",
            )
        authorizers.append(
            AuthorizerEndpoint(
                authorizer_id=trusted_party["authorizer_id"],
                endpoint=trusted_party["endpoint"],
                identity_digest=hashlib.sha256(
                    bytes.fromhex(trusted_party["public_key_hex"])
                ).hexdigest(),
            )
        )
    suite = descriptor_payload["recovery_suite"]
    holders = tuple(
        RecoveryHolder(
            holder_id=item["holder_id"],
            authorizer_id=item["authorizer_id"],
            suite_id=suite["id"],
        )
        for item in suite["holders"]
    )
    return PartyDirectorySnapshot(
        authorizers=tuple(authorizers),
        recovery_holders=holders,
        authorization_quorum=descriptor_payload["authorization"]["quorum"],
        recovery_threshold=ThresholdParameters(
            k=suite["threshold"]["k"], n=suite["threshold"]["n"]
        ),
    )


def _expected_current_summary(
    descriptor_bytes: bytes, descriptor_payload: dict[str, Any]
) -> dict[str, Any]:
    return {
        "backup_id": descriptor_payload["backup_id"],
        "configuration_digest": descriptor_payload["lifecycle"]["configuration_digest"],
        "cue_policy_id": descriptor_payload["cue_policy"]["id"],
        "descriptor_sha256": hashlib.sha256(descriptor_bytes).hexdigest(),
        "epoch": descriptor_payload["epoch"],
        "recovery_id": descriptor_payload["recovery_id"],
        "recovery_suite_id": descriptor_payload["recovery_suite"]["id"],
        "state": "active",
        "subject_id": descriptor_payload["subject_id"],
    }


def _receipt_matches(
    receipt_payload: dict[str, Any],
    *,
    trust: dict[str, Any],
    recovery_handle: str,
    subject_id: str,
    descriptor_payload: dict[str, Any],
    descriptor_bytes: bytes,
    now: int,
) -> bool:
    operator = trust["operator"]
    discovery = trust["discovery"]
    if (
        receipt_payload["issued_at"] > now
        or receipt_payload["subject_id"] != subject_id
        or receipt_payload["recovery_handle"] != recovery_handle
        or receipt_payload["discovery_profile"] != trust["profile"]
        or receipt_payload["discovery_endpoint"] != discovery["endpoint"]
        or receipt_payload["issuer"] != operator["issuer"]
        or receipt_payload["operator_key_id"] != operator["key_id"]
    ):
        return False
    initial = receipt_payload["initial"]
    if initial is None:
        return True
    if (
        descriptor_payload["backup_id"] != initial["backup_id"]
        or descriptor_payload["epoch"] < initial["epoch"]
    ):
        return False
    if descriptor_payload["epoch"] == initial["epoch"]:
        return (
            descriptor_payload["backup_id"] == initial["backup_id"]
            and descriptor_payload["lifecycle"]["configuration_digest"]
            == initial["configuration_digest"]
            and hashlib.sha256(descriptor_bytes).hexdigest()
            == initial["descriptor_sha256"]
        )
    return True


def authenticate_recovery_bootstrap(
    *,
    trust_configuration_bytes: bytes,
    discovery_endpoint: str,
    recovery_handle: str,
    expected_subject_id: str,
    current_pointer_bytes: bytes,
    bundle_bytes: bytes,
    current_state_observations: Sequence[PartyCurrentObservation],
    now: int,
    receipt_bytes: bytes | None = None,
) -> RecoveryBootstrapResult:
    """Authenticate one untrusted discovery response before cue processing."""

    _integer(now, "bootstrap current time", minimum=1, maximum=2**63 - 1)
    _identifier(recovery_handle, "recovery handle")
    _lower_hex(expected_subject_id, "expected recovery subject", byte_length=32)
    try:
        trust = decode_trust_configuration(trust_configuration_bytes)
    except RecoveryDescriptorError as exc:
        raise RecoveryBootstrapError(
            BootstrapFailureCode.INVALID_TRUST_CONFIGURATION,
            "installed bootstrap trust configuration is invalid",
        ) from exc
    if not _active_interval(trust, now=now, issued="valid_from", expires="valid_until"):
        raise RecoveryBootstrapError(
            BootstrapFailureCode.TRUST_CONFIGURATION_EXPIRED,
            "installed bootstrap trust configuration is not active",
        )
    if discovery_endpoint != trust["discovery"]["endpoint"]:
        raise RecoveryBootstrapError(
            BootstrapFailureCode.UNTRUSTED_DISCOVERY_ENDPOINT,
            "discovery response came from an untrusted endpoint",
        )
    operator = trust["operator"]
    operator_key = _public_key(
        operator["public_key_hex"], "bootstrap operator public key"
    )
    try:
        pointer = decode_current_pointer(
            current_pointer_bytes,
            issuer_public_key=operator_key,
            expected_issuer=operator["issuer"],
            expected_key_id=operator["key_id"],
        )
    except RecoveryDescriptorError as exc:
        raise RecoveryBootstrapError(
            BootstrapFailureCode.INVALID_CURRENT_POINTER,
            "current pointer failed authentication",
        ) from exc
    try:
        bundle = decode_bundle(
            bundle_bytes,
            issuer_public_key=operator_key,
            expected_issuer=operator["issuer"],
            expected_key_id=operator["key_id"],
        )
        verify_current_pointer_bundle(pointer=pointer, bundle=bundle)
    except RecoveryDescriptorError as exc:
        raise RecoveryBootstrapError(
            BootstrapFailureCode.INVALID_RECOVERY_BUNDLE,
            "recovery bundle failed authentication or pointer binding",
        ) from exc
    pointer_payload = pointer["payload"]
    descriptor_payload = bundle.descriptor["payload"]
    _require_active_public_object(pointer_payload, now=now, label="current pointer")
    _require_active_public_object(descriptor_payload, now=now, label="descriptor")
    if (
        pointer_payload["subject_id"] != expected_subject_id
        or descriptor_payload["subject_id"] != expected_subject_id
        or descriptor_payload["recovery_id"] != recovery_handle
    ):
        raise RecoveryBootstrapError(
            BootstrapFailureCode.RECOVERY_IDENTITY_MISMATCH,
            "discovered recovery identity does not match bootstrap input",
        )
    receipt_verified = False
    if receipt_bytes is not None:
        try:
            receipt = decode_recovery_receipt(
                receipt_bytes,
                issuer_public_key=operator_key,
                expected_issuer=operator["issuer"],
                expected_key_id=operator["key_id"],
            )
        except RecoveryDescriptorError as exc:
            raise RecoveryBootstrapError(
                BootstrapFailureCode.INVALID_RECEIPT,
                "recovery receipt failed authentication",
            ) from exc
        if not _receipt_matches(
            receipt["payload"],
            trust=trust,
            recovery_handle=recovery_handle,
            subject_id=expected_subject_id,
            descriptor_payload=descriptor_payload,
            descriptor_bytes=bundle.descriptor_bytes,
            now=now,
        ):
            raise RecoveryBootstrapError(
                BootstrapFailureCode.INVALID_RECEIPT,
                "recovery receipt binding mismatch",
            )
        receipt_verified = True
    directory_snapshot = _trusted_directory(descriptor_payload, trust)
    trusted_parties = {item["authorizer_id"]: item for item in trust["parties"]}
    if len(current_state_observations) > len(trusted_parties):
        raise RecoveryBootstrapError(
            BootstrapFailureCode.INVALID_PARTY_SUMMARY,
            "too many party current-state observations",
        )
    expected_summary = _expected_current_summary(
        bundle.descriptor_bytes, descriptor_payload
    )
    seen: set[int] = set()
    matching: list[int] = []
    dissenting: list[int] = []
    for observation in current_state_observations:
        if (
            not isinstance(observation, PartyCurrentObservation)
            or observation.authorizer_id in seen
            or observation.authorizer_id not in trusted_parties
        ):
            raise RecoveryBootstrapError(
                BootstrapFailureCode.INVALID_PARTY_SUMMARY,
                "invalid or duplicate party current-state observation",
            )
        seen.add(observation.authorizer_id)
        trusted_party = trusted_parties[observation.authorizer_id]
        if observation.endpoint != trusted_party["endpoint"]:
            raise RecoveryBootstrapError(
                BootstrapFailureCode.UNTRUSTED_PARTY_DIRECTORY,
                "party response came from an untrusted endpoint",
            )
        try:
            summary = decode_party_current_summary(
                observation.summary_bytes,
                party_public_key=_public_key(
                    trusted_party["public_key_hex"], "bootstrap party public key"
                ),
                expected_key_id=trusted_party["identity_key_id"],
            )
        except RecoveryDescriptorError as exc:
            raise RecoveryBootstrapError(
                BootstrapFailureCode.INVALID_PARTY_SUMMARY,
                "party current-state summary failed authentication",
            ) from exc
        summary_payload = summary["payload"]
        if summary_payload["authorizer_id"] != observation.authorizer_id:
            raise RecoveryBootstrapError(
                BootstrapFailureCode.INVALID_PARTY_SUMMARY,
                "party current-state identity mismatch",
            )
        if not _active_interval(
            summary_payload, now=now, issued="issued_at", expires="expires_at"
        ):
            raise RecoveryBootstrapError(
                BootstrapFailureCode.INVALID_PARTY_SUMMARY,
                "party current-state summary is not fresh",
            )
        observed_binding = {key: summary_payload[key] for key in expected_summary}
        if observed_binding == expected_summary:
            matching.append(observation.authorizer_id)
        else:
            dissenting.append(observation.authorizer_id)
    quorum = directory_snapshot.authorization_quorum
    if len(matching) < quorum:
        code = (
            BootstrapFailureCode.CLOUD_PARTY_STATE_MISMATCH
            if dissenting
            else BootstrapFailureCode.CURRENT_STATE_QUORUM_UNAVAILABLE
        )
        raise RecoveryBootstrapError(
            code,
            "current party state does not authenticate the discovered cloud state",
        )
    directory = AuthenticatedPartyDirectory(
        recovery_handle=recovery_handle,
        epoch=descriptor_payload["epoch"],
        snapshot=directory_snapshot,
    )
    if not isinstance(directory, PartyDirectory):
        raise AssertionError("authenticated directory does not implement contract")
    return RecoveryBootstrapResult(
        bundle=bundle,
        current_pointer=pointer,
        directory=directory,
        matching_authorizers=tuple(sorted(matching)),
        dissenting_authorizers=tuple(sorted(dissenting)),
        receipt_verified=receipt_verified,
    )


__all__ = [
    "BOOTSTRAP_PROFILE",
    "BootstrapFailureCode",
    "MAX_CURRENT_SUMMARY_LIFETIME_SECONDS",
    "MAX_PARTY_CURRENT_SUMMARY_BYTES",
    "MAX_RECOVERY_RECEIPT_BYTES",
    "MAX_TRUST_CONFIGURATION_BYTES",
    "PARTY_CURRENT_SIGNATURE_VERSION",
    "PARTY_CURRENT_SUMMARY_VERSION",
    "PartyCurrentObservation",
    "RECOVERY_RECEIPT_VERSION",
    "RecoveryBootstrapError",
    "RecoveryBootstrapResult",
    "TRUST_CONFIGURATION_VERSION",
    "authenticate_recovery_bootstrap",
    "create_party_current_summary",
    "create_recovery_receipt",
    "decode_party_current_summary",
    "decode_recovery_receipt",
    "decode_trust_configuration",
    "validate_party_current_summary_payload",
    "validate_recovery_receipt_payload",
    "validate_trust_configuration",
    "validate_trust_configuration_update",
]
