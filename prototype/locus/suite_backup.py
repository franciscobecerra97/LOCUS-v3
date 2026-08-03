"""Versioned suite-neutral backups over the unchanged LOCUS HKDF/AES path."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .appss_formats import (
    APPSS_PROFILE_2_OF_3,
    APPSS_PROFILE_3_OF_5,
    APPSS_PUBLIC_STATE_FORMAT,
    APPSS_PUBLIC_STATE_FORMAT_V2,
    APPSS_SUITE_ID,
    BACKUP_AAD_V2,
    BACKUP_AAD_V3,
    REFERENCE_BACKUP_V5,
    REFERENCE_BACKUP_V6,
    YI_PROFILE_2_OF_3,
    YI_PROFILE_3_OF_5,
    YI_SUITE_ID,
)
from .codec import encode
from .contracts import (
    PartyRecoveryState,
    PasswordProtectedSecretRecovery,
    RecoveryContext,
    RecoverySuiteEnrollment,
    ThresholdParameters,
)
from .core import SECURITY_POLICY_VERSION, derive_wrap_key
from .crypto import (
    SEALED_ALGORITHM,
    SEALED_VERSION,
    CryptoError,
    open_sealed,
    random_bytes,
    seal,
    validate_sealed,
)
from .object_store import backup_digest
from .yi_compat import RecoverySuiteError


class SuiteBackupError(ValueError):
    """A suite backup is malformed, misbound, or cannot be opened."""


@dataclass(frozen=True)
class SuiteBackupEnrollment:
    backup: dict[str, Any]
    party_states: tuple[PartyRecoveryState, ...]


def backup_v5_associated_data(backup: dict[str, Any]) -> bytes:
    public = dict(backup)
    public["ciphertext"] = None
    public["digest"] = None
    validated = validate_backup_v5(
        public, require_digest=False, require_ciphertext=False
    )
    return encode(
        {
            "backup_version": REFERENCE_BACKUP_V5,
            "bid": validated["bid"],
            "cue_policy": validated["cue_policy"],
            "epoch": validated["epoch"],
            "recovery_nonce": validated["nonce"],
            "recovery_suite": validated["recovery_suite"],
            "sealed_algorithm": SEALED_ALGORITHM,
            "sealed_version": SEALED_VERSION,
            "security_policy": validated["security_policy"],
            "version": BACKUP_AAD_V2,
        }
    )


def backup_v6_associated_data(backup: dict[str, Any]) -> bytes:
    public = dict(backup)
    public["ciphertext"] = None
    public["digest"] = None
    validated = validate_backup_v6(
        public, require_digest=False, require_ciphertext=False
    )
    return encode(
        {
            "backup_version": REFERENCE_BACKUP_V6,
            "bid": validated["bid"],
            "cue_policy": validated["cue_policy"],
            "epoch": validated["epoch"],
            "recovery_nonce": validated["nonce"],
            "recovery_suite": validated["recovery_suite"],
            "sealed_algorithm": SEALED_ALGORITHM,
            "sealed_version": SEALED_VERSION,
            "security_policy": validated["security_policy"],
            "version": BACKUP_AAD_V3,
        }
    )


def _validate_suite_backup(
    value: object,
    *,
    backup_version: str,
    topologies: frozenset[tuple[int, int]],
    require_digest: bool = True,
    require_ciphertext: bool = True,
) -> dict[str, Any]:
    expected = {
        "bid",
        "ciphertext",
        "cue_policy",
        "digest",
        "epoch",
        "nonce",
        "recovery_suite",
        "security_policy",
        "version",
    }
    if not isinstance(value, dict) or set(value) != expected:
        raise SuiteBackupError("invalid suite backup")
    if value["version"] != backup_version:
        raise SuiteBackupError("unsupported backup version")
    _lower_hex(value["bid"], "backup identifier", 16)
    if (
        isinstance(value["epoch"], bool)
        or not isinstance(value["epoch"], int)
        or not 1 <= value["epoch"] <= 2**63 - 1
    ):
        raise SuiteBackupError("invalid backup epoch")
    _lower_hex(value["nonce"], "recovery nonce", 16)
    cue_policy = value["cue_policy"]
    if not isinstance(cue_policy, dict) or set(cue_policy) != {
        "id",
        "resolver_profile",
    }:
        raise SuiteBackupError("invalid backup CuePolicy binding")
    _identifier(cue_policy["id"], "CuePolicy identifier")
    _identifier(cue_policy["resolver_profile"], "resolver profile")
    suite = value["recovery_suite"]
    if not isinstance(suite, dict) or set(suite) != {
        "context_digest",
        "id",
        "k",
        "n",
        "profile_id",
        "public_state",
        "public_state_format",
    }:
        raise SuiteBackupError("invalid backup recovery-suite binding")
    for field in ("id", "profile_id", "public_state_format"):
        _identifier(suite[field], f"suite {field}")
    _lower_hex(suite["context_digest"], "suite context digest", 32)
    if (suite["k"], suite["n"]) not in topologies:
        raise SuiteBackupError("unsupported backup recovery topology")
    if backup_version == REFERENCE_BACKUP_V6:
        expected_profile_and_format = {
            (YI_SUITE_ID, 2, 3): (YI_PROFILE_2_OF_3, "LOCUS-TPASS-wire-v1"),
            (YI_SUITE_ID, 3, 5): (YI_PROFILE_3_OF_5, "LOCUS-TPASS-wire-v1"),
            (APPSS_SUITE_ID, 2, 3): (
                APPSS_PROFILE_2_OF_3,
                APPSS_PUBLIC_STATE_FORMAT,
            ),
            (APPSS_SUITE_ID, 3, 5): (
                APPSS_PROFILE_3_OF_5,
                APPSS_PUBLIC_STATE_FORMAT_V2,
            ),
        }.get((suite["id"], suite["k"], suite["n"]))
        if expected_profile_and_format != (
            suite["profile_id"],
            suite["public_state_format"],
        ):
            raise SuiteBackupError("backup suite profile mismatch")
    if (
        not isinstance(suite["public_state"], str)
        or not suite["public_state"]
        or len(suite["public_state"]) > 524288
        or len(suite["public_state"]) % 2
        or any(
            character not in "0123456789abcdef" for character in suite["public_state"]
        )
    ):
        raise SuiteBackupError("invalid backup public state")
    policy = value["security_policy"]
    if not isinstance(policy, dict) or set(policy) != {
        "cooldown_seconds",
        "max_attempts",
        "version",
    }:
        raise SuiteBackupError("invalid backup security policy")
    if policy["version"] != SECURITY_POLICY_VERSION:
        raise SuiteBackupError("unsupported backup security policy")
    for field, minimum in (("max_attempts", 1), ("cooldown_seconds", 0)):
        item = policy[field]
        if isinstance(item, bool) or not isinstance(item, int) or item < minimum:
            raise SuiteBackupError("invalid backup security policy")
    if require_ciphertext:
        try:
            validate_sealed(value["ciphertext"])
        except CryptoError as exc:
            raise SuiteBackupError("invalid backup ciphertext") from exc
    elif value["ciphertext"] is not None:
        raise SuiteBackupError("backup ciphertext placeholder is not null")
    if require_digest:
        digest = _lower_hex(value["digest"], "backup digest", 32)
        if backup_digest(value) != digest:
            raise SuiteBackupError("backup digest mismatch")
    elif value["digest"] is not None:
        raise SuiteBackupError("backup digest placeholder is not null")
    return value


def validate_backup_v5(
    value: object,
    *,
    require_digest: bool = True,
    require_ciphertext: bool = True,
) -> dict[str, Any]:
    return _validate_suite_backup(
        value,
        backup_version=REFERENCE_BACKUP_V5,
        topologies=frozenset({(2, 3)}),
        require_digest=require_digest,
        require_ciphertext=require_ciphertext,
    )


def validate_backup_v6(
    value: object,
    *,
    require_digest: bool = True,
    require_ciphertext: bool = True,
) -> dict[str, Any]:
    return _validate_suite_backup(
        value,
        backup_version=REFERENCE_BACKUP_V6,
        topologies=frozenset({(2, 3), (3, 5)}),
        require_digest=require_digest,
        require_ciphertext=require_ciphertext,
    )


def enroll_backup_v5(
    *,
    protected_key: bytes,
    context: RecoveryContext,
    cue_policy_id: str,
    resolver_profile: str,
    adapter: PasswordProtectedSecretRecovery,
    enrollment: RecoverySuiteEnrollment,
    profile_id: str,
    bid: bytes | None = None,
    nonce: bytes | None = None,
    max_attempts: int = 8,
    cooldown_seconds: int = 30,
) -> SuiteBackupEnrollment:
    if enrollment.public_state.suite_id != adapter.suite_id:
        raise SuiteBackupError("backup enrollment mixes suites")
    backup = seal_backup_v5(
        protected_key=protected_key,
        context=context,
        cue_policy_id=cue_policy_id,
        resolver_profile=resolver_profile,
        suite_id=adapter.suite_id,
        public_state_format=enrollment.public_state.format_id,
        public_state_payload=enrollment.public_state.payload,
        recovery_secret=enrollment.recovery_secret,
        profile_id=profile_id,
        bid=bid,
        nonce=nonce,
        max_attempts=max_attempts,
        cooldown_seconds=cooldown_seconds,
    )
    return SuiteBackupEnrollment(backup=backup, party_states=enrollment.party_states)


def enroll_backup_v6(
    *,
    protected_key: bytes,
    context: RecoveryContext,
    cue_policy_id: str,
    resolver_profile: str,
    adapter: PasswordProtectedSecretRecovery,
    enrollment: RecoverySuiteEnrollment,
    profile_id: str,
    threshold: ThresholdParameters,
    bid: bytes | None = None,
    nonce: bytes | None = None,
    max_attempts: int = 8,
    cooldown_seconds: int = 30,
) -> SuiteBackupEnrollment:
    if enrollment.public_state.suite_id != adapter.suite_id:
        raise SuiteBackupError("backup enrollment mixes suites")
    backup = seal_backup_v6(
        protected_key=protected_key,
        context=context,
        cue_policy_id=cue_policy_id,
        resolver_profile=resolver_profile,
        suite_id=adapter.suite_id,
        public_state_format=enrollment.public_state.format_id,
        public_state_payload=enrollment.public_state.payload,
        recovery_secret=enrollment.recovery_secret,
        profile_id=profile_id,
        threshold=threshold,
        bid=bid,
        nonce=nonce,
        max_attempts=max_attempts,
        cooldown_seconds=cooldown_seconds,
    )
    return SuiteBackupEnrollment(backup=backup, party_states=enrollment.party_states)


def _seal_suite_backup(
    *,
    protected_key: bytes,
    context: RecoveryContext,
    cue_policy_id: str,
    resolver_profile: str,
    suite_id: str,
    public_state_format: str,
    public_state_payload: bytes,
    recovery_secret: bytes,
    profile_id: str,
    threshold: ThresholdParameters,
    backup_version: str,
    bid: bytes | None = None,
    nonce: bytes | None = None,
    max_attempts: int = 8,
    cooldown_seconds: int = 30,
) -> dict[str, Any]:
    """Seal one suite's native recovery secret through the common outer path."""

    if not isinstance(protected_key, bytes) or not protected_key:
        raise SuiteBackupError("invalid protected key")
    if backup_version not in {REFERENCE_BACKUP_V5, REFERENCE_BACKUP_V6}:
        raise SuiteBackupError("unsupported backup version")
    if (
        context.suite_id != suite_id
        or not isinstance(public_state_payload, bytes)
        or not public_state_payload
        or not isinstance(recovery_secret, bytes)
        or not recovery_secret
    ):
        raise SuiteBackupError("backup enrollment mixes suites")
    if context.suite_context_digest is None:
        raise SuiteBackupError("backup suite context is missing")
    bid_bytes = random_bytes(16) if bid is None else bid
    nonce_bytes = random_bytes(16) if nonce is None else nonce
    if len(bid_bytes) != 16 or len(nonce_bytes) != 16:
        raise SuiteBackupError("invalid backup randomness")
    if context.backup_id != bid_bytes.hex():
        raise SuiteBackupError("backup identifier differs from recovery context")
    backup: dict[str, Any] = {
        "bid": bid_bytes.hex(),
        "ciphertext": None,
        "cue_policy": {"id": cue_policy_id, "resolver_profile": resolver_profile},
        "digest": None,
        "epoch": context.epoch,
        "nonce": nonce_bytes.hex(),
        "recovery_suite": {
            "context_digest": context.suite_context_digest,
            "id": suite_id,
            "k": threshold.k,
            "n": threshold.n,
            "profile_id": profile_id,
            "public_state": public_state_payload.hex(),
            "public_state_format": public_state_format,
        },
        "security_policy": {
            "cooldown_seconds": cooldown_seconds,
            "max_attempts": max_attempts,
            "version": SECURITY_POLICY_VERSION,
        },
        "version": backup_version,
    }
    validator = (
        validate_backup_v5
        if backup_version == REFERENCE_BACKUP_V5
        else validate_backup_v6
    )
    associated_data = (
        backup_v5_associated_data
        if backup_version == REFERENCE_BACKUP_V5
        else backup_v6_associated_data
    )
    validator(backup, require_digest=False, require_ciphertext=False)
    wrap_key = derive_wrap_key(
        recovery_secret,
        backup["bid"],
        backup["epoch"],
        backup["nonce"],
    )
    backup["ciphertext"] = seal(wrap_key, protected_key, aad=associated_data(backup))
    backup["digest"] = backup_digest(backup)
    validator(backup)
    return backup


def seal_backup_v5(
    *,
    protected_key: bytes,
    context: RecoveryContext,
    cue_policy_id: str,
    resolver_profile: str,
    suite_id: str,
    public_state_format: str,
    public_state_payload: bytes,
    recovery_secret: bytes,
    profile_id: str,
    bid: bytes | None = None,
    nonce: bytes | None = None,
    max_attempts: int = 8,
    cooldown_seconds: int = 30,
) -> dict[str, Any]:
    return _seal_suite_backup(
        protected_key=protected_key,
        context=context,
        cue_policy_id=cue_policy_id,
        resolver_profile=resolver_profile,
        suite_id=suite_id,
        public_state_format=public_state_format,
        public_state_payload=public_state_payload,
        recovery_secret=recovery_secret,
        profile_id=profile_id,
        threshold=ThresholdParameters(k=2, n=3),
        backup_version=REFERENCE_BACKUP_V5,
        bid=bid,
        nonce=nonce,
        max_attempts=max_attempts,
        cooldown_seconds=cooldown_seconds,
    )


def seal_backup_v6(
    *,
    protected_key: bytes,
    context: RecoveryContext,
    cue_policy_id: str,
    resolver_profile: str,
    suite_id: str,
    public_state_format: str,
    public_state_payload: bytes,
    recovery_secret: bytes,
    profile_id: str,
    threshold: ThresholdParameters,
    bid: bytes | None = None,
    nonce: bytes | None = None,
    max_attempts: int = 8,
    cooldown_seconds: int = 30,
) -> dict[str, Any]:
    return _seal_suite_backup(
        protected_key=protected_key,
        context=context,
        cue_policy_id=cue_policy_id,
        resolver_profile=resolver_profile,
        suite_id=suite_id,
        public_state_format=public_state_format,
        public_state_payload=public_state_payload,
        recovery_secret=recovery_secret,
        profile_id=profile_id,
        threshold=threshold,
        backup_version=REFERENCE_BACKUP_V6,
        bid=bid,
        nonce=nonce,
        max_attempts=max_attempts,
        cooldown_seconds=cooldown_seconds,
    )


def recover_backup_v5(
    *,
    backup: dict[str, Any],
    context: RecoveryContext,
    password_input: bytes,
    adapter: PasswordProtectedSecretRecovery,
    party_states: tuple[PartyRecoveryState, ...],
) -> bytes:
    validated = validate_backup_v5(backup)
    suite = validated["recovery_suite"]
    if (
        suite["id"] != adapter.suite_id
        or context.suite_id != adapter.suite_id
        or suite["context_digest"] != context.suite_context_digest
        or validated["bid"] != context.backup_id
        or validated["epoch"] != context.epoch
    ):
        raise SuiteBackupError("backup recovery binding mismatch")
    from .contracts import PublicRecoveryState

    public_state = PublicRecoveryState(
        suite_id=suite["id"],
        format_id=suite["public_state_format"],
        payload=bytes.fromhex(suite["public_state"]),
    )
    try:
        secret = adapter.recover(
            context=context,
            password_input=password_input,
            public_state=public_state,
            party_states=party_states,
        )
        return open_backup_v5_with_secret(backup=validated, recovery_secret=secret)
    except (RecoverySuiteError, CryptoError) as exc:
        raise SuiteBackupError("recovery rejected") from exc


def recover_backup_v6(
    *,
    backup: dict[str, Any],
    context: RecoveryContext,
    password_input: bytes,
    adapter: PasswordProtectedSecretRecovery,
    party_states: tuple[PartyRecoveryState, ...],
) -> bytes:
    validated = validate_backup_v6(backup)
    suite = validated["recovery_suite"]
    if (
        suite["id"] != adapter.suite_id
        or context.suite_id != adapter.suite_id
        or suite["context_digest"] != context.suite_context_digest
        or validated["bid"] != context.backup_id
        or validated["epoch"] != context.epoch
    ):
        raise SuiteBackupError("backup recovery binding mismatch")
    from .contracts import PublicRecoveryState

    public_state = PublicRecoveryState(
        suite_id=suite["id"],
        format_id=suite["public_state_format"],
        payload=bytes.fromhex(suite["public_state"]),
    )
    try:
        secret = adapter.recover(
            context=context,
            password_input=password_input,
            public_state=public_state,
            party_states=party_states,
        )
        return open_backup_v6_with_secret(backup=validated, recovery_secret=secret)
    except (RecoverySuiteError, CryptoError) as exc:
        raise SuiteBackupError("recovery rejected") from exc


def open_backup_v5_with_secret(
    *, backup: dict[str, Any], recovery_secret: bytes
) -> bytes:
    validated = validate_backup_v5(backup)
    if not isinstance(recovery_secret, bytes) or not recovery_secret:
        raise SuiteBackupError("invalid recovery secret")
    try:
        wrap_key = derive_wrap_key(
            recovery_secret,
            validated["bid"],
            validated["epoch"],
            validated["nonce"],
        )
        return open_sealed(
            wrap_key,
            validated["ciphertext"],
            aad=backup_v5_associated_data(validated),
        )
    except CryptoError as exc:
        raise SuiteBackupError("recovery rejected") from exc


def open_backup_v6_with_secret(
    *, backup: dict[str, Any], recovery_secret: bytes
) -> bytes:
    validated = validate_backup_v6(backup)
    if not isinstance(recovery_secret, bytes) or not recovery_secret:
        raise SuiteBackupError("invalid recovery secret")
    try:
        wrap_key = derive_wrap_key(
            recovery_secret,
            validated["bid"],
            validated["epoch"],
            validated["nonce"],
        )
        return open_sealed(
            wrap_key,
            validated["ciphertext"],
            aad=backup_v6_associated_data(validated),
        )
    except CryptoError as exc:
        raise SuiteBackupError("recovery rejected") from exc


def _identifier(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or len(value) > 255
        or not value.isascii()
        or any(ord(character) < 0x21 or ord(character) > 0x7E for character in value)
    ):
        raise SuiteBackupError(f"invalid {label}")
    return value


def _lower_hex(value: object, label: str, length: int) -> str:
    if (
        not isinstance(value, str)
        or len(value) != length * 2
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise SuiteBackupError(f"invalid {label}")
    return value


__all__ = [
    "SuiteBackupEnrollment",
    "SuiteBackupError",
    "backup_v5_associated_data",
    "backup_v6_associated_data",
    "enroll_backup_v5",
    "enroll_backup_v6",
    "open_backup_v5_with_secret",
    "open_backup_v6_with_secret",
    "recover_backup_v5",
    "recover_backup_v6",
    "seal_backup_v5",
    "seal_backup_v6",
    "validate_backup_v5",
    "validate_backup_v6",
]
