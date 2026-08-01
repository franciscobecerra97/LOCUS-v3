"""Strict separated backup-object storage for the LOCUS reference prototype.

The filesystem implementation is a reproducible test adapter, not a claim that
the local filesystem is an independently administered cloud service. Objects
are published immutably at an exact ``(bid, epoch)`` path. Readers also require
the expected content digest pinned by recovery-party configuration.
"""

from __future__ import annotations

import json
import os
import stat
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from .codec import encode
from .crypto import hash_bytes

CLOUD_OBJECT_VERSION = "LOCUS-cloud-backup-object-v1"
CLOUD_REFERENCE_VERSION = "LOCUS-cloud-backup-reference-v1"
MAX_BACKUP_OBJECT_BYTES = 1024 * 1024
MAX_EPOCH = 2**63 - 1


class ObjectStoreError(Exception):
    """Base class for explicit object-storage failures."""


class ObjectNotFound(ObjectStoreError):
    """The exact immutable object reference does not exist."""


class ObjectStoreUnavailable(ObjectStoreError):
    """The storage backend could not complete an operation."""


class ObjectCorrupt(ObjectStoreError):
    """Stored bytes are malformed, noncanonical, or violate their binding."""


class ObjectConflict(ObjectStoreError):
    """An immutable object key already contains different bytes."""


class ObjectStale(ObjectStoreError):
    """A mutable-object compare-and-swap expectation is no longer current."""


class ObjectTooLarge(ObjectStoreError):
    """A backup object exceeds the frozen storage bound."""


def _lower_hex(value: object, label: str, *, byte_length: int) -> str:
    if (
        not isinstance(value, str)
        or len(value) != byte_length * 2
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ObjectCorrupt(f"invalid {label}")
    return value


def _positive_epoch(value: object) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < 1
        or value > MAX_EPOCH
    ):
        raise ObjectCorrupt("invalid backup epoch")
    return value


@dataclass(frozen=True)
class BackupReference:
    """Exact party-pinned reference to one immutable cloud backup object."""

    bid: str
    epoch: int
    backup_digest: str

    def validate(self) -> None:
        _lower_hex(self.bid, "backup identifier", byte_length=16)
        _positive_epoch(self.epoch)
        _lower_hex(self.backup_digest, "backup digest", byte_length=32)

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "version": CLOUD_REFERENCE_VERSION,
            "bid": self.bid,
            "epoch": self.epoch,
            "backup_digest": self.backup_digest,
        }

    @classmethod
    def from_dict(cls, value: object) -> BackupReference:
        expected = {"version", "bid", "epoch", "backup_digest"}
        if not isinstance(value, dict) or set(value) != expected:
            raise ObjectCorrupt("invalid cloud backup reference")
        if value["version"] != CLOUD_REFERENCE_VERSION:
            raise ObjectCorrupt("unsupported cloud backup reference")
        reference = cls(
            bid=value["bid"],
            epoch=value["epoch"],
            backup_digest=value["backup_digest"],
        )
        reference.validate()
        return reference

    @classmethod
    def from_backup(cls, backup: object) -> BackupReference:
        _validate_backup_shape(backup)
        assert isinstance(backup, dict)
        return cls(
            bid=backup["bid"],
            epoch=backup["epoch"],
            backup_digest=backup["digest"],
        )


@runtime_checkable
class BackupObjectStore(Protocol):
    """Small storage boundary used by enrollment and recovery clients."""

    def create(self, backup: dict[str, Any]) -> BackupReference:
        """Publish once; an exact retry is idempotent and mutation conflicts."""

    def read(self, reference: BackupReference) -> dict[str, Any]:
        """Read and validate the exact party-pinned immutable object."""

    def delete(self, reference: BackupReference) -> None:
        """Delete an exact object for lifecycle or adversarial tests."""


def backup_digest(backup: dict[str, Any]) -> str:
    """Digest the complete public backup except its self-describing digest."""

    public_backup = {key: value for key, value in backup.items() if key != "digest"}
    return hash_bytes("LOCUS-backup-digest-v1", encode(public_backup)).hex()


def _validate_backup_shape(backup: object) -> None:
    expected = {
        "version",
        "bid",
        "epoch",
        "nonce",
        "ciphertext",
        "tpass_public_params",
        "context_policy",
        "security_policy",
        "digest",
    }
    if not isinstance(backup, dict) or set(backup) != expected:
        raise ObjectCorrupt("invalid cloud backup object")
    _lower_hex(backup["bid"], "backup identifier", byte_length=16)
    _positive_epoch(backup["epoch"])
    digest = _lower_hex(backup["digest"], "backup digest", byte_length=32)
    try:
        calculated = backup_digest(backup)
    except (RecursionError, TypeError, ValueError) as exc:
        raise ObjectCorrupt("invalid cloud backup object") from exc
    if calculated != digest:
        raise ObjectCorrupt("cloud backup digest mismatch")


def _reject_duplicate_members(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate JSON member")
        value[key] = item
    return value


def _decode_canonical_json(encoded: bytes) -> dict[str, Any]:
    try:
        value = json.loads(
            encoded.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_members,
            parse_constant=lambda _value: (_ for _ in ()).throw(
                ValueError("non-finite JSON number")
            ),
        )
        if not isinstance(value, dict) or encode(value) != encoded:
            raise ValueError("noncanonical JSON")
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
        ValueError,
        RecursionError,
    ) as exc:
        raise ObjectCorrupt("invalid canonical cloud object") from exc
    return value


def encode_backup_object(backup: dict[str, Any]) -> tuple[BackupReference, bytes]:
    """Validate and encode the canonical cloud object for any storage backend."""

    _validate_backup_shape(backup)
    reference = BackupReference.from_backup(backup)
    encoded = encode(
        {
            "version": CLOUD_OBJECT_VERSION,
            "bid": reference.bid,
            "epoch": reference.epoch,
            "backup_digest": reference.backup_digest,
            "backup": backup,
        }
    )
    if len(encoded) > MAX_BACKUP_OBJECT_BYTES:
        raise ObjectTooLarge("cloud backup object exceeds size limit")
    return reference, encoded


def decode_backup_object(
    encoded: bytes, *, expected: BackupReference | None = None
) -> tuple[BackupReference, dict[str, Any]]:
    """Decode and verify one bounded canonical cloud object."""

    if not encoded or len(encoded) > MAX_BACKUP_OBJECT_BYTES:
        if len(encoded) > MAX_BACKUP_OBJECT_BYTES:
            raise ObjectTooLarge("cloud backup object exceeds size limit")
        raise ObjectCorrupt("empty cloud backup object")
    envelope = _decode_canonical_json(encoded)
    keys = {"version", "bid", "epoch", "backup_digest", "backup"}
    if set(envelope) != keys or envelope["version"] != CLOUD_OBJECT_VERSION:
        raise ObjectCorrupt("unsupported cloud backup object")
    reference = BackupReference(
        bid=envelope["bid"],
        epoch=envelope["epoch"],
        backup_digest=envelope["backup_digest"],
    )
    reference.validate()
    backup = envelope["backup"]
    _validate_backup_shape(backup)
    assert isinstance(backup, dict)
    if BackupReference.from_backup(backup) != reference:
        raise ObjectCorrupt("cloud envelope binding mismatch")
    if expected is not None and reference != expected:
        raise ObjectCorrupt("cloud object does not match expected reference")
    return reference, backup


class FilesystemBackupObjectStore:
    """Filesystem test adapter with immutable, atomic object publication.

    Publication writes and fsyncs a temporary file in the destination directory,
    then creates the final name with an atomic non-overwriting hard link. This
    gives concurrent adapters create-if-absent semantics on filesystems that
    support same-filesystem hard links. Unsupported storage fails explicitly.
    """

    def __init__(self, root: str | Path) -> None:
        self._lock = threading.RLock()
        requested = Path(root)
        try:
            requested.mkdir(parents=True, exist_ok=True)
            if requested.is_symlink() or not requested.is_dir():
                raise OSError("object-store root is not a plain directory")
            self.root = requested.resolve(strict=True)
        except OSError as exc:
            raise ObjectStoreUnavailable("cloud object store is unavailable") from exc

    def _object_path(self, reference: BackupReference) -> Path:
        reference.validate()
        return self.root / reference.bid / f"{reference.epoch}.json"

    @staticmethod
    def _fsync_directory(path: Path) -> None:
        try:
            descriptor = os.open(path, os.O_RDONLY)
        except OSError:
            return
        try:
            os.fsync(descriptor)
        except OSError:
            pass
        finally:
            os.close(descriptor)

    def _read_bytes(self, path: Path) -> bytes:
        try:
            metadata = path.lstat()
            if path.is_symlink() or not stat.S_ISREG(metadata.st_mode):
                raise ObjectCorrupt("cloud object path is not a regular file")
            with path.open("rb") as handle:
                encoded = handle.read(MAX_BACKUP_OBJECT_BYTES + 1)
        except FileNotFoundError as exc:
            raise ObjectNotFound("cloud backup object was not found") from exc
        except ObjectStoreError:
            raise
        except OSError as exc:
            raise ObjectStoreUnavailable("cloud object store is unavailable") from exc
        if len(encoded) > MAX_BACKUP_OBJECT_BYTES:
            raise ObjectTooLarge("cloud backup object exceeds size limit")
        return encoded

    def create(self, backup: dict[str, Any]) -> BackupReference:
        reference, encoded = encode_backup_object(backup)
        path = self._object_path(reference)
        with self._lock:
            temporary_path: Path | None = None
            try:
                path.parent.mkdir(exist_ok=True)
                if path.parent.is_symlink() or not path.parent.is_dir():
                    raise OSError("backup namespace is not a plain directory")
                with tempfile.NamedTemporaryFile(
                    mode="wb", dir=path.parent, prefix=".pending-", delete=False
                ) as handle:
                    temporary_path = Path(handle.name)
                    handle.write(encoded)
                    handle.flush()
                    os.fsync(handle.fileno())
                try:
                    os.link(temporary_path, path)
                except FileExistsError:
                    existing = self._read_bytes(path)
                    if existing != encoded:
                        raise ObjectConflict(
                            "immutable cloud backup object already exists"
                        ) from None
                self._fsync_directory(path.parent)
            except ObjectStoreError:
                raise
            except OSError as exc:
                raise ObjectStoreUnavailable(
                    "cloud object store is unavailable"
                ) from exc
            finally:
                if temporary_path is not None:
                    try:
                        temporary_path.unlink(missing_ok=True)
                    except OSError:
                        pass
        return reference

    def read(self, reference: BackupReference) -> dict[str, Any]:
        reference.validate()
        encoded = self._read_bytes(self._object_path(reference))
        _, backup = decode_backup_object(encoded, expected=reference)
        return backup

    def delete(self, reference: BackupReference) -> None:
        """Delete an exact object for lifecycle tests and cloud-adversary simulation."""

        path = self._object_path(reference)
        with self._lock:
            try:
                metadata = path.lstat()
                if path.is_symlink() or not stat.S_ISREG(metadata.st_mode):
                    raise ObjectCorrupt("cloud object path is not a regular file")
                path.unlink()
                self._fsync_directory(path.parent)
            except FileNotFoundError as exc:
                raise ObjectNotFound("cloud backup object was not found") from exc
            except ObjectStoreError:
                raise
            except OSError as exc:
                raise ObjectStoreUnavailable(
                    "cloud object store is unavailable"
                ) from exc
