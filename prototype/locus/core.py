"""LOCUS enrollment and recovery flow for the reference prototype."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .codec import encode, encoded_size, normalize_text
from .crypto import (
    SEALED_ALGORITHM,
    SEALED_VERSION,
    CryptoError,
    hash_bytes,
    hash_scalar,
    hkdf,
    open_sealed,
    random_bytes,
    seal,
    validate_sealed,
)
from .object_store import (
    BackupObjectStore,
    BackupReference,
    ObjectStoreError,
    backup_digest,
)
from .tpass import NativeTpassBackend, TpassBackend, TpassError


class LocusError(Exception):
    """Raised when LOCUS enrollment or recovery fails."""


BACKUP_VERSION = "LOCUS-development-backup-v1"
BACKUP_AAD_VERSION = "LOCUS-backup-associated-data-v1"
PARTY_RECORD_VERSION = "LOCUS-reference-party-v1"
CONTEXT_POLICY_VERSION = "LOCUS-development-context-v1"
SECURITY_POLICY_VERSION = "LOCUS-security-policy-v1"


@dataclass
class Enrollment:
    backup: dict
    cloud_reference: dict
    parties: list[dict]
    metrics: dict


def _canonical_record(record: dict[str, Any]) -> dict[str, Any]:
    canonical = {}
    for key, value in sorted(record.items()):
        if isinstance(value, str):
            text = normalize_text(value)
            if key in {"provider", "record_id", "platform", "url"}:
                text = text.lower()
            canonical[key] = text
        else:
            canonical[key] = value
    return canonical


def context_tuple(cues: list[dict[str, dict[str, Any]]]) -> list[tuple[str, str]]:
    out = []
    for cue in cues:
        loc = _canonical_record(cue["location"])
        person = _canonical_record(cue["person"])
        x_j = hash_bytes("LOCUS-loc-id-v1", encode(loc)).hex()
        y_j = hash_bytes("LOCUS-person-id-v1", encode(person)).hex()
        out.append((x_j, y_j))
    return out


def derive_context_password(
    cues: list[dict[str, dict[str, Any]]], bid: str, epoch: int, nonce_hex: str
) -> int:
    z_value = context_tuple(cues)
    return hash_scalar(
        "LOCUS-context-password",
        encode(z_value),
        bytes.fromhex(nonce_hex),
        bid,
        epoch,
    )


def derive_wrap_key(group_secret: bytes, bid: str, epoch: int, nonce_hex: str) -> bytes:
    return hkdf(
        group_secret,
        salt=bytes.fromhex(nonce_hex),
        info=encode({"purpose": "LOCUS-wrap", "bid": bid, "epoch": epoch}),
        length=32,
    )


def recovery_id(user_id: str, bid: str, epoch: int) -> str:
    return f"{user_id}:{bid}:{epoch}"


def backup_associated_data(backup: dict) -> bytes:
    """Encode public backup metadata authenticated by the wrapping key."""

    _require_keys(
        backup,
        (
            "version",
            "bid",
            "epoch",
            "nonce",
            "tpass_public_params",
            "context_policy",
            "security_policy",
        ),
        "backup associated data",
    )
    return encode(
        {
            "version": BACKUP_AAD_VERSION,
            "backup_version": backup["version"],
            "bid": backup["bid"],
            "epoch": backup["epoch"],
            "recovery_nonce": backup["nonce"],
            "tpass_public_params": backup["tpass_public_params"],
            "context_policy": backup["context_policy"],
            "security_policy": backup["security_policy"],
            "sealed_version": SEALED_VERSION,
            "sealed_algorithm": SEALED_ALGORITHM,
        }
    )


def _require_keys(value: dict, keys: tuple[str, ...], label: str) -> None:
    if not isinstance(value, dict):
        raise LocusError(f"malformed {label}")
    missing = [key for key in keys if key not in value]
    if missing:
        raise LocusError(f"malformed {label}: missing {', '.join(missing)}")


def _require_exact_keys(value: object, keys: tuple[str, ...], label: str) -> dict:
    if not isinstance(value, dict) or set(value) != set(keys):
        raise LocusError(f"malformed {label}")
    return value


def _as_positive_int(value: object, label: str) -> int:
    if isinstance(value, bool):
        raise LocusError(f"malformed {label}")
    if not isinstance(value, (int, str)):
        raise LocusError(f"malformed {label}")
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise LocusError(f"malformed {label}") from exc
    if parsed < 1:
        raise LocusError(f"invalid {label}")
    return parsed


def _as_nonnegative_int(value: object, label: str) -> int:
    if isinstance(value, bool):
        raise LocusError(f"malformed {label}")
    if not isinstance(value, (int, str)):
        raise LocusError(f"malformed {label}")
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise LocusError(f"malformed {label}") from exc
    if parsed < 0:
        raise LocusError(f"invalid {label}")
    return parsed


def _as_exact_positive_int(value: object, label: str) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < 1
        or value > 2**63 - 1
    ):
        raise LocusError(f"invalid {label}")
    return value


def _as_backup_id(value: object) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 32
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise LocusError("invalid backup identifier")
    return value


def _validate_security_policy(policy: dict) -> dict:
    _require_exact_keys(
        policy, ("version", "max_attempts", "cooldown_seconds"), "security policy"
    )
    if policy["version"] != SECURITY_POLICY_VERSION:
        raise LocusError("unsupported security policy version")
    max_attempts = _as_positive_int(policy["max_attempts"], "max attempts")
    cooldown = _as_nonnegative_int(policy["cooldown_seconds"], "cooldown")
    return {
        "version": policy["version"],
        "max_attempts": max_attempts,
        "cooldown_seconds": cooldown,
    }


def _validate_backup(backup: dict, tpass: TpassBackend) -> tuple[int, int, dict]:
    _require_exact_keys(
        backup,
        (
            "version",
            "bid",
            "epoch",
            "nonce",
            "ciphertext",
            "tpass_public_params",
            "context_policy",
            "security_policy",
            "digest",
        ),
        "backup",
    )
    if backup["version"] != BACKUP_VERSION:
        raise LocusError("unsupported backup version")
    if not isinstance(backup["bid"], str) or not backup["bid"]:
        raise LocusError("malformed backup identifier")
    if len(backup["bid"]) != 32 or any(
        character not in "0123456789abcdef" for character in backup["bid"]
    ):
        raise LocusError("malformed backup identifier")
    _as_exact_positive_int(backup["epoch"], "backup epoch")
    if not isinstance(backup["nonce"], str):
        raise LocusError("malformed backup nonce")
    try:
        recovery_nonce = bytes.fromhex(backup["nonce"])
    except (TypeError, ValueError) as exc:
        raise LocusError("malformed backup nonce") from exc
    if len(recovery_nonce) != 16 or recovery_nonce.hex() != backup["nonce"]:
        raise LocusError("malformed backup nonce")
    try:
        validate_sealed(backup["ciphertext"])
    except CryptoError as exc:
        raise LocusError(str(exc)) from exc
    _require_exact_keys(backup["context_policy"], ("version",), "context policy")
    if backup["context_policy"]["version"] != CONTEXT_POLICY_VERSION:
        raise LocusError("unsupported context policy version")
    policy = _validate_security_policy(backup["security_policy"])
    params = backup["tpass_public_params"]
    _require_keys(
        params, ("backend", "threshold", "parties"), "TPASS public parameters"
    )
    if params["backend"] != tpass.backend:
        raise LocusError("unsupported TPASS backend")
    threshold = _as_positive_int(params["threshold"], "threshold")
    parties = _as_positive_int(params["parties"], "party count")
    if parties < threshold:
        raise LocusError("invalid threshold parameters")
    return threshold, parties, policy


def _validate_party_record(
    record: dict,
    *,
    expected_bid: str,
    expected_epoch: int,
    expected_digest: str,
    expected_cloud_reference: dict,
    expected_policy: dict,
) -> None:
    _require_exact_keys(
        record,
        (
            "version",
            "bid",
            "epoch",
            "recovery_id",
            "tpass_state",
            "cloud_ref",
            "backup_digest",
            "security_policy",
            "attempt_count",
            "locked",
        ),
        "party record",
    )
    if record["version"] != PARTY_RECORD_VERSION:
        raise LocusError("unsupported party record version")
    if record["bid"] != expected_bid:
        raise LocusError("party record does not match backup")
    if record["epoch"] != expected_epoch:
        raise LocusError("party epoch does not match backup")
    if record["cloud_ref"] != expected_cloud_reference:
        raise LocusError("party cloud reference mismatch")
    if record["backup_digest"] != expected_digest:
        raise LocusError("party backup digest mismatch")
    policy = _validate_security_policy(record["security_policy"])
    if policy != expected_policy:
        raise LocusError("party security policy mismatch")
    if not isinstance(record["tpass_state"], dict):
        raise LocusError("malformed party state")


def enroll(
    *,
    user_id: str,
    private_key: bytes,
    cues: list[dict[str, dict[str, Any]]],
    threshold: int,
    parties: int,
    max_attempts: int = 3,
    epoch: int = 1,
    bid: str | None = None,
    object_store: BackupObjectStore | None = None,
    tpass: TpassBackend | None = None,
) -> Enrollment:
    if threshold < 1 or parties < threshold:
        raise LocusError("invalid threshold parameters")
    if not cues:
        raise LocusError("at least one cue is required")
    epoch = _as_exact_positive_int(epoch, "backup epoch")

    tpass = tpass or NativeTpassBackend()
    bid = random_bytes(16).hex() if bid is None else _as_backup_id(bid)
    nonce_hex = random_bytes(16).hex()
    rec_id = recovery_id(user_id, bid, epoch)
    password = derive_context_password(cues, bid, epoch, nonce_hex)
    enrollment = tpass.setup(
        recovery_id=rec_id,
        password=password,
        digest_context=f"{bid}:{epoch}",
        threshold=threshold,
        parties=parties,
    )
    group_secret = enrollment.group_secret
    wrap_key = derive_wrap_key(group_secret, bid, epoch, nonce_hex)
    public_params = enrollment.public_params
    tpass_states = enrollment.party_states
    backup: dict[str, Any] = {
        "version": BACKUP_VERSION,
        "bid": bid,
        "epoch": epoch,
        "nonce": nonce_hex,
        "tpass_public_params": public_params,
        "context_policy": {"version": CONTEXT_POLICY_VERSION},
        "security_policy": {
            "version": SECURITY_POLICY_VERSION,
            "max_attempts": max_attempts,
            "cooldown_seconds": 0,
        },
    }
    backup["ciphertext"] = seal(
        wrap_key,
        private_key,
        aad=backup_associated_data(backup),
    )
    backup["digest"] = backup_digest(backup)
    cloud_reference = BackupReference.from_backup(backup).to_dict()
    if object_store is not None:
        try:
            stored_reference = object_store.create(backup)
        except ObjectStoreError as exc:
            raise LocusError("backup storage failed") from exc
        if stored_reference.to_dict() != cloud_reference:
            raise LocusError("backup storage returned a mismatched reference")
    party_records = []
    for state in tpass_states:
        party_records.append(
            {
                "version": PARTY_RECORD_VERSION,
                "bid": bid,
                "epoch": epoch,
                "recovery_id": rec_id,
                "tpass_state": state,
                "cloud_ref": dict(cloud_reference),
                "backup_digest": backup["digest"],
                "security_policy": dict(backup["security_policy"]),
                "attempt_count": 0,
                "locked": False,
            }
        )
    metrics = {
        "backup_bytes": encoded_size(backup),
        "party_record_bytes": [encoded_size(record) for record in party_records],
        "total_party_record_bytes": sum(
            encoded_size(record) for record in party_records
        ),
        "backend": public_params["backend"],
        "threshold": threshold,
        "parties": parties,
        "cue_count": len(cues),
    }
    return Enrollment(
        backup=backup,
        cloud_reference=dict(cloud_reference),
        parties=party_records,
        metrics=metrics,
    )


def reenroll(
    *,
    current_backup: dict[str, Any],
    user_id: str,
    private_key: bytes,
    cues: list[dict[str, dict[str, Any]]],
    threshold: int,
    parties: int,
    max_attempts: int = 3,
    object_store: BackupObjectStore | None = None,
    tpass: TpassBackend | None = None,
) -> Enrollment:
    """Create the direct successor of one validated immutable backup epoch."""

    backend = tpass or NativeTpassBackend()
    _validate_backup(current_backup, backend)
    if backup_digest(current_backup) != current_backup.get("digest"):
        raise LocusError("backup digest mismatch")
    current_epoch = _as_exact_positive_int(current_backup["epoch"], "backup epoch")
    if current_epoch >= 2**63 - 1:
        raise LocusError("backup epoch is exhausted")
    return enroll(
        user_id=user_id,
        private_key=private_key,
        cues=cues,
        threshold=threshold,
        parties=parties,
        max_attempts=max_attempts,
        epoch=current_epoch + 1,
        bid=_as_backup_id(current_backup["bid"]),
        object_store=object_store,
        tpass=backend,
    )


def _check_and_increment_attempts(records: list[dict]) -> None:
    for record in records:
        policy = _validate_security_policy(record["security_policy"])
        if record.get("locked"):
            raise LocusError("recovery party is locked")
        if int(record.get("attempt_count", 0)) >= int(policy["max_attempts"]):
            record["locked"] = True
            raise LocusError("attempt limit exceeded")
    for record in records:
        record["attempt_count"] = int(record.get("attempt_count", 0)) + 1
        policy = _validate_security_policy(record["security_policy"])
        if record["attempt_count"] >= int(policy["max_attempts"]):
            record["locked"] = True


def recover(
    *,
    user_id: str,
    backup: dict,
    party_records: list[dict],
    cues: list[dict[str, dict[str, Any]]],
    tpass: TpassBackend | None = None,
) -> bytes:
    tpass = tpass or NativeTpassBackend()
    threshold, _, policy = _validate_backup(backup, tpass)
    if backup_digest(backup) != backup.get("digest"):
        raise LocusError("backup digest mismatch")
    expected_digest = backup["digest"]
    expected_cloud_reference = BackupReference.from_backup(backup).to_dict()
    if len(party_records) < threshold:
        raise LocusError("not enough recovery parties")
    selected = party_records[:threshold]
    for record in selected:
        _validate_party_record(
            record,
            expected_bid=backup["bid"],
            expected_epoch=backup["epoch"],
            expected_digest=expected_digest,
            expected_cloud_reference=expected_cloud_reference,
            expected_policy=policy,
        )

    _check_and_increment_attempts(selected)
    password_attempt = derive_context_password(
        cues, backup["bid"], backup["epoch"], backup["nonce"]
    )
    try:
        group_secret = tpass.recover(
            recovery_id=recovery_id(user_id, backup["bid"], backup["epoch"]),
            password_attempt=password_attempt,
            digest_context=f"{backup['bid']}:{backup['epoch']}",
            public_params=backup["tpass_public_params"],
            party_states=[record["tpass_state"] for record in selected],
        )
    except TpassError as exc:
        raise LocusError(str(exc)) from exc

    wrap_key = derive_wrap_key(
        group_secret, backup["bid"], backup["epoch"], backup["nonce"]
    )
    try:
        return open_sealed(
            wrap_key,
            backup["ciphertext"],
            aad=backup_associated_data(backup),
        )
    except CryptoError as exc:
        raise LocusError(str(exc)) from exc


def recover_from_store(
    *,
    user_id: str,
    cloud_reference: dict,
    object_store: BackupObjectStore,
    party_records: list[dict],
    cues: list[dict[str, dict[str, Any]]],
    tpass: TpassBackend | None = None,
) -> bytes:
    """Fetch a party-pinned object before entering the counted recovery flow."""

    try:
        reference = BackupReference.from_dict(cloud_reference)
        backup = object_store.read(reference)
        if BackupReference.from_backup(backup) != reference:
            raise LocusError("backup unavailable or invalid")
    except ObjectStoreError as exc:
        raise LocusError("backup unavailable or invalid") from exc
    return recover(
        user_id=user_id,
        backup=backup,
        party_records=party_records,
        cues=cues,
        tpass=tpass,
    )


def state_separation_audit(backup: dict, party_records: list[dict]) -> dict:
    forbidden_backup_keys = {
        "raw_cues",
        "context_tuple",
        "context_password",
        "wrapping_key",
        "group_secret",
        "tpass_state",
    }
    forbidden_party_keys = {
        "raw_cues",
        "context_tuple",
        "context_password",
        "wrapping_key",
        "group_secret",
        "ciphertext",
    }
    backup_hits = sorted(forbidden_backup_keys.intersection(backup.keys()))
    party_hits = sorted(
        {
            key
            for record in party_records
            for key in forbidden_party_keys.intersection(record.keys())
        }
    )
    return {
        "ok": not backup_hits and not party_hits,
        "backup_hits": backup_hits,
        "party_hits": party_hits,
    }
