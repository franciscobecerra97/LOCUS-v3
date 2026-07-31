"""Strict cloud-only snapshot collection and offline-predicate audit."""

from __future__ import annotations

import argparse
import base64
import binascii
import builtins
import hashlib
import io
import json
import os
import re
import socket
import stat
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Never

from .codec import encode
from .core import SECURITY_POLICY_VERSION
from .crypto import validate_sealed
from .deployed_profile import (
    BACKUP_VERSION,
    CONTEXT_POLICY_VERSION,
)
from .object_store import (
    MAX_BACKUP_OBJECT_BYTES,
    BackupReference,
    ObjectStoreError,
    decode_backup_object,
    encode_backup_object,
)
from .redaction import validate_public_output
from .s3_object_store import S3BackupObjectStore

CLOUD_SNAPSHOT_INPUT_VERSION = "LOCUS-cloud-snapshot-input-v1"
CLOUD_SNAPSHOT_SCENARIO = "cloud-snapshot-no-offline-predicate-v1"
SNAPSHOT_OBJECT_NAME = "object.json"
SNAPSHOT_MANIFEST_NAME = "manifest.json"
MAX_MANIFEST_BYTES = 16 * 1024
SYNTHETIC_CANDIDATES = (
    b"LOCUS-synthetic-offline-candidate-alpha-v1",
    b"LOCUS-synthetic-offline-candidate-beta-v1",
)


class CloudSnapshotError(Exception):
    """The snapshot, collection path, or offline boundary is invalid."""


@dataclass(frozen=True)
class CloudSnapshot:
    """Validated internal snapshot view; never serialize this structure."""

    backup: dict[str, Any]
    manifest: dict[str, Any]
    object_bytes: bytes
    reference: BackupReference


CandidateProbe = Callable[[Mapping[str, Any], bytes], object | None]


def _exact_dict(value: object, fields: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        raise CloudSnapshotError(f"invalid {label}")
    return value


def _canonical_json(encoded: bytes, *, label: str) -> dict[str, Any]:
    try:
        value = json.loads(encoded.decode("ascii"))
        if not isinstance(value, dict) or encode(value) != encoded:
            raise ValueError("noncanonical JSON")
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
        ValueError,
        RecursionError,
    ) as exc:
        raise CloudSnapshotError(f"invalid {label}") from exc
    return value


def _regular_file_bytes(path: Path, *, limit: int, label: str) -> bytes:
    try:
        metadata = path.lstat()
        if path.is_symlink() or not stat.S_ISREG(metadata.st_mode):
            raise CloudSnapshotError(f"invalid {label}")
        with path.open("rb") as handle:
            value = handle.read(limit + 1)
    except CloudSnapshotError:
        raise
    except OSError as exc:
        raise CloudSnapshotError(f"invalid {label}") from exc
    if not value or len(value) > limit:
        raise CloudSnapshotError(f"invalid {label}")
    return value


def _validate_snapshot_root(root: Path) -> tuple[Path, Path]:
    try:
        if root.is_symlink() or not root.is_dir():
            raise CloudSnapshotError("invalid snapshot directory")
        entries = {entry.name: entry for entry in root.iterdir()}
    except CloudSnapshotError:
        raise
    except OSError as exc:
        raise CloudSnapshotError("invalid snapshot directory") from exc
    if set(entries) != {SNAPSHOT_OBJECT_NAME, SNAPSHOT_MANIFEST_NAME}:
        raise CloudSnapshotError("snapshot directory must contain exactly two files")
    return entries[SNAPSHOT_OBJECT_NAME], entries[SNAPSHOT_MANIFEST_NAME]


def _lower_hex(value: object, *, length: int, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != length
        or re.fullmatch(r"[0-9a-f]+", value) is None
    ):
        raise CloudSnapshotError(f"invalid {label}")
    return value


def _validate_bucket(value: object) -> str:
    if (
        not isinstance(value, str)
        or len(value) < 3
        or len(value) > 63
        or re.fullmatch(r"[a-z0-9][a-z0-9.-]*[a-z0-9]", value) is None
        or ".." in value
    ):
        raise CloudSnapshotError("invalid snapshot bucket")
    return value


def _validate_object_key(value: object, reference: BackupReference) -> str:
    if not isinstance(value, str) or len(value) > 1024 or "\\" in value:
        raise CloudSnapshotError("invalid snapshot object key")
    parts = PurePosixPath(value).parts
    if (
        len(parts) < 3
        or any(part in {"", ".", ".."} for part in parts)
        or parts[-2:] != (reference.bid, f"{reference.epoch}.json")
    ):
        raise CloudSnapshotError("snapshot object key does not match the object")
    return value


def _decode_base64url(value: object, *, label: str) -> bytes:
    if not isinstance(value, str) or not value or "=" in value:
        raise CloudSnapshotError(f"invalid {label}")
    padding = "=" * ((4 - len(value) % 4) % 4)
    try:
        decoded = base64.b64decode(value + padding, altchars=b"-_", validate=True)
    except (ValueError, binascii.Error) as exc:
        raise CloudSnapshotError(f"invalid {label}") from exc
    if base64.urlsafe_b64encode(decoded).rstrip(b"=").decode("ascii") != value:
        raise CloudSnapshotError(f"invalid {label}")
    return decoded


_PROHIBITED_SNAPSHOT_FIELDS = frozenset(
    {
        "access_key",
        "canonical_cue",
        "canonical_cues",
        "correctness_label",
        "credential",
        "cue",
        "cue_id",
        "cue_identifier",
        "cue_records",
        "cues",
        "derived_password",
        "group_secret",
        "party_state",
        "password",
        "plaintext",
        "private_key",
        "raw_cue",
        "raw_cues",
        "recovered_secret",
        "secret_key",
        "secret_party_state",
        "signer_private_key",
        "tpass_password",
        "tpass_share",
        "tpass_state",
        "verifier",
        "wrap_key",
        "wrapping_key",
    }
)


def _field_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_")


def _reject_prohibited_material(value: object, *, depth: int = 0) -> None:
    if depth > 16:
        raise CloudSnapshotError("snapshot structure exceeds the audit bound")
    if isinstance(value, dict):
        for key, child in value.items():
            if (
                not isinstance(key, str)
                or _field_name(key) in _PROHIBITED_SNAPSHOT_FIELDS
            ):
                raise CloudSnapshotError("snapshot contains prohibited material")
            _reject_prohibited_material(child, depth=depth + 1)
    elif isinstance(value, list):
        for child in value:
            _reject_prohibited_material(child, depth=depth + 1)


def _validate_backup_surface(backup: dict[str, Any]) -> None:
    if backup["version"] != BACKUP_VERSION:
        raise CloudSnapshotError("unsupported snapshot backup version")
    _lower_hex(backup["nonce"], length=32, label="snapshot recovery nonce")
    try:
        validate_sealed(backup["ciphertext"])
    except Exception as exc:
        raise CloudSnapshotError("invalid snapshot ciphertext") from exc
    context_policy = _exact_dict(
        backup["context_policy"], {"version"}, "snapshot context policy"
    )
    if context_policy["version"] != CONTEXT_POLICY_VERSION:
        raise CloudSnapshotError("unsupported snapshot context policy")
    security_policy = _exact_dict(
        backup["security_policy"],
        {"version", "max_attempts", "cooldown_seconds"},
        "snapshot security policy",
    )
    if security_policy["version"] != SECURITY_POLICY_VERSION:
        raise CloudSnapshotError("unsupported snapshot security policy")
    parameters = _exact_dict(
        backup["tpass_public_params"],
        {"backend", "encoding", "parameters", "parties", "threshold"},
        "snapshot TPASS public parameters",
    )
    if (
        parameters["backend"] != "yi-zk-ristretto255-native-v1"
        or parameters["encoding"] != "LOCUS-TPASS-wire-v1"
        or isinstance(parameters["threshold"], bool)
        or not isinstance(parameters["threshold"], int)
        or isinstance(parameters["parties"], bool)
        or not isinstance(parameters["parties"], int)
        or not 1 <= parameters["threshold"] <= parameters["parties"] <= 255
    ):
        raise CloudSnapshotError("invalid snapshot TPASS public parameters")
    encoded_parameters = _decode_base64url(
        parameters["parameters"], label="snapshot TPASS public encoding"
    )
    try:
        from . import _tpass_native as native

        parsed = native.PublicParameters.from_bytes(encoded_parameters)
    except (ImportError, ValueError) as exc:
        raise CloudSnapshotError("invalid snapshot TPASS public encoding") from exc
    if (
        parsed.threshold != parameters["threshold"]
        or parsed.parties != parameters["parties"]
    ):
        raise CloudSnapshotError("snapshot TPASS metadata mismatch")
    _reject_prohibited_material(backup)


def validate_cloud_snapshot(root: Path) -> CloudSnapshot:
    """Validate the exact two-file cloud snapshot before candidate testing."""

    object_path, manifest_path = _validate_snapshot_root(root)
    object_bytes = _regular_file_bytes(
        object_path, limit=MAX_BACKUP_OBJECT_BYTES, label="snapshot object"
    )
    manifest_bytes = _regular_file_bytes(
        manifest_path, limit=MAX_MANIFEST_BYTES, label="snapshot manifest"
    )
    manifest = _exact_dict(
        _canonical_json(manifest_bytes, label="snapshot manifest"),
        {"backend", "bucket", "object_bytes", "object_key", "object_sha256", "version"},
        "snapshot manifest",
    )
    if (
        manifest["version"] != CLOUD_SNAPSHOT_INPUT_VERSION
        or manifest["backend"] != "s3-compatible"
        or isinstance(manifest["object_bytes"], bool)
        or not isinstance(manifest["object_bytes"], int)
        or manifest["object_bytes"] != len(object_bytes)
        or _lower_hex(
            manifest["object_sha256"], length=64, label="snapshot object digest"
        )
        != hashlib.sha256(object_bytes).hexdigest()
    ):
        raise CloudSnapshotError("snapshot manifest does not match the object")
    _validate_bucket(manifest["bucket"])
    try:
        reference, backup = decode_backup_object(object_bytes)
    except ObjectStoreError as exc:
        raise CloudSnapshotError("invalid canonical snapshot object") from exc
    _validate_object_key(manifest["object_key"], reference)
    _validate_backup_surface(backup)
    return CloudSnapshot(
        backup=backup,
        manifest=manifest,
        object_bytes=object_bytes,
        reference=reference,
    )


@dataclass
class _BoundaryCounters:
    excluded_path_accesses: int = 0
    network_attempts: int = 0


class _BoundaryViolation(Exception):
    pass


class _OfflineCandidateGuard:
    """Make boundary attempts observable in addition to container network isolation."""

    def __init__(self, counters: _BoundaryCounters) -> None:
        self._counters = counters
        self._originals: list[tuple[object, str, object]] = []

    def _replace(self, owner: object, name: str, replacement: object) -> None:
        self._originals.append((owner, name, getattr(owner, name)))
        setattr(owner, name, replacement)

    def __enter__(self) -> _OfflineCandidateGuard:
        def block_path(*_args: object, **_kwargs: object) -> Never:
            self._counters.excluded_path_accesses += 1
            raise _BoundaryViolation("candidate path attempted filesystem access")

        def block_network(*_args: object, **_kwargs: object) -> Never:
            self._counters.network_attempts += 1
            raise _BoundaryViolation("candidate path attempted network access")

        self._replace(builtins, "open", block_path)
        self._replace(io, "open", block_path)
        self._replace(os, "open", block_path)
        self._replace(socket, "socket", block_network)
        self._replace(socket, "create_connection", block_network)
        self._replace(socket, "getaddrinfo", block_network)
        return self

    def __exit__(
        self,
        _exception_type: object,
        _exception: object,
        _traceback: object,
    ) -> None:
        for owner, name, original in reversed(self._originals):
            setattr(owner, name, original)
        self._originals.clear()


def _candidate_preprocessing(
    backup: Mapping[str, Any], candidate: bytes
) -> object | None:
    """Exercise a public candidate-dependent transform without exposing a verifier."""

    digest = hashlib.sha256()
    digest.update(b"LOCUS/cloud-snapshot-candidate-audit/v1\x00")
    digest.update(bytes.fromhex(backup["bid"]))
    digest.update(int(backup["epoch"]).to_bytes(8, "big"))
    digest.update(bytes.fromhex(backup["nonce"]))
    digest.update(candidate)
    digest.digest()
    return None


def audit_cloud_snapshot(
    root: Path, *, candidate_probe: CandidateProbe | None = None
) -> dict[str, object]:
    """Return one aggregate observation over the strict offline candidate path."""

    snapshot = validate_cloud_snapshot(root)
    counters = _BoundaryCounters()
    signals = 0
    probe = candidate_probe or _candidate_preprocessing
    for candidate in SYNTHETIC_CANDIDATES:
        try:
            with _OfflineCandidateGuard(counters):
                signal = probe(snapshot.backup, candidate)
        except _BoundaryViolation:
            continue
        except Exception:
            signals += 1
            continue
        if signal is not None:
            signals += 1
    observation: dict[str, object] = {
        "candidate_count": len(SYNTHETIC_CANDIDATES),
        "candidate_signals": signals,
        "excluded_path_accesses": counters.excluded_path_accesses,
        "network_attempts": counters.network_attempts,
        "prohibited_material": "absent",
        "snapshot_validation": "passed",
    }
    validate_public_output(observation)
    return observation


def _load_deployment_backup(client_root: Path) -> dict[str, Any]:
    path = client_root / "deployment.json"
    encoded = _regular_file_bytes(
        path, limit=MAX_BACKUP_OBJECT_BYTES, label="deployment bundle"
    )
    deployment = _canonical_json(encoded, label="deployment bundle")
    backup = deployment.get("backup")
    if not isinstance(backup, dict):
        raise CloudSnapshotError("invalid deployment backup")
    return backup


def _s3_store_from_environment() -> S3BackupObjectStore:
    names = (
        "LOCUS_S3_ACCESS_KEY",
        "LOCUS_S3_BUCKET",
        "LOCUS_S3_ENDPOINT",
        "LOCUS_S3_PREFIX",
        "LOCUS_S3_SECRET_KEY",
    )
    values = {name: os.environ.get(name) for name in names}
    if any(not value for value in values.values()):
        raise CloudSnapshotError("snapshot collection configuration is unavailable")
    return S3BackupObjectStore.from_credentials(
        access_key=values["LOCUS_S3_ACCESS_KEY"] or "",
        bucket=values["LOCUS_S3_BUCKET"] or "",
        endpoint_url=values["LOCUS_S3_ENDPOINT"],
        prefix=values["LOCUS_S3_PREFIX"] or "",
        secret_key=values["LOCUS_S3_SECRET_KEY"] or "",
        allow_http=True,
    )


def _write_new(path: Path, value: bytes) -> None:
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444)
        try:
            with os.fdopen(descriptor, "wb", closefd=False) as output:
                output.write(value)
                output.flush()
                os.fsync(output.fileno())
        finally:
            os.close(descriptor)
    except OSError as exc:
        raise CloudSnapshotError("snapshot publication failed") from exc


def capture_cloud_snapshot(
    *, client_root: Path, snapshot_root: Path
) -> dict[str, object]:
    """Capture exact stored S3 bytes into the two-file offline snapshot volume."""

    try:
        snapshot_root.mkdir(parents=True, exist_ok=True)
        if snapshot_root.is_symlink() or any(snapshot_root.iterdir()):
            raise CloudSnapshotError("snapshot output must be an empty directory")
    except CloudSnapshotError:
        raise
    except OSError as exc:
        raise CloudSnapshotError("snapshot output is unavailable") from exc
    backup = _load_deployment_backup(client_root)
    expected_reference, expected_bytes = encode_backup_object(backup)
    store = _s3_store_from_environment()
    reference = store.create(backup)
    object_bytes = store.read_encoded(reference)
    if reference != expected_reference or object_bytes != expected_bytes:
        raise CloudSnapshotError("stored cloud object changed during capture")
    manifest = {
        "backend": "s3-compatible",
        "bucket": store.bucket,
        "object_bytes": len(object_bytes),
        "object_key": store.object_key(reference),
        "object_sha256": hashlib.sha256(object_bytes).hexdigest(),
        "version": CLOUD_SNAPSHOT_INPUT_VERSION,
    }
    _write_new(snapshot_root / SNAPSHOT_OBJECT_NAME, object_bytes)
    _write_new(snapshot_root / SNAPSHOT_MANIFEST_NAME, encode(manifest))
    validate_cloud_snapshot(snapshot_root)
    result: dict[str, object] = {
        "artifact": CLOUD_SNAPSHOT_INPUT_VERSION,
        "status": "captured",
    }
    validate_public_output(result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Collect a strict LOCUS cloud snapshot"
    )
    parser.add_argument("--client-root", type=Path, required=True)
    parser.add_argument("--snapshot-root", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = capture_cloud_snapshot(
            client_root=args.client_root, snapshot_root=args.snapshot_root
        )
    except (CloudSnapshotError, ObjectStoreError):
        return 1
    print(
        json.dumps(
            result,
            allow_nan=False,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
