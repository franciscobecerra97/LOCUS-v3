"""P2.3 descriptor, current-pointer, and recovery-bundle storage adapters."""

from __future__ import annotations

import base64
import hashlib
import os
import stat
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, cast, runtime_checkable

from .contracts import (
    CurrentDescriptorPointer,
    DescriptorDocument,
    DescriptorReference,
    DescriptorStore,
)
from .object_store import (
    BackupReference,
    ObjectConflict,
    ObjectCorrupt,
    ObjectNotFound,
    ObjectStale,
    ObjectStoreError,
    ObjectStoreUnavailable,
    ObjectTooLarge,
)
from .recovery_descriptor import (
    BACKUP_MEMBER,
    CURRENT_POINTER_VERSION,
    DESCRIPTOR_MEMBER,
    DESCRIPTOR_VERSION,
    MANIFEST_MEMBER,
    MAX_BUNDLE_BYTES,
    MAX_DESCRIPTOR_BYTES,
    MAX_POINTER_BYTES,
    RecoveryDescriptorError,
    _decode_canonical_json,
    _exact_dict,
    _identifier,
    _read_bundle_members,
    _validate_signature_metadata,
    create_manifest,
    decode_manifest,
    validate_descriptor_payload,
    validate_pointer_payload,
)
from .s3_object_store import (
    MAX_CONDITIONAL_WRITE_ATTEMPTS,
    S3Client,
    _is_conditional_conflict,
    _is_not_found,
    _is_precondition_failed,
    _validate_bucket,
    _validate_prefix,
)

DEFAULT_DESCRIPTOR_PREFIX = "locus/recovery"
DESCRIPTOR_STORE_PROFILE = "LOCUS-descriptor-bundle-store-v1"
MAX_RECOVERY_HANDLE_BYTES = 255


@dataclass(frozen=True)
class RecoveryBundleReference:
    subject_id: str
    backup_id: str
    epoch: int
    digest: str
    length: int
    locator: str

    def validate(self) -> None:
        _lower_hex(self.subject_id, "bundle subject", 32)
        _lower_hex(self.backup_id, "bundle backup identifier", 16)
        _positive_epoch(self.epoch)
        _lower_hex(self.digest, "bundle digest", 32)
        if (
            isinstance(self.length, bool)
            or not isinstance(self.length, int)
            or self.length < 1
            or self.length > MAX_BUNDLE_BYTES
        ):
            raise ObjectCorrupt("invalid bundle length")
        _safe_locator(self.locator)


@runtime_checkable
class RecoveryBundleStore(Protocol):
    def create_bundle(
        self, *, subject_id: str, backup_id: str, epoch: int, bundle: bytes
    ) -> RecoveryBundleReference: ...

    def read_bundle(self, reference: RecoveryBundleReference) -> bytes: ...


def _lower_hex(value: object, label: str, size: int) -> str:
    if (
        not isinstance(value, str)
        or len(value) != size * 2
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ObjectCorrupt(f"invalid {label}")
    return value


def _positive_epoch(value: object) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < 1
        or value > 2**63 - 1
    ):
        raise ObjectCorrupt("invalid bundle epoch")
    return value


def _safe_locator(value: object) -> str:
    if (
        not isinstance(value, str)
        or not value
        or len(value) > 1024
        or value.startswith(("/", "\\"))
        or "\\" in value
        or any(part in {"", ".", ".."} for part in value.split("/"))
    ):
        raise ObjectCorrupt("invalid storage locator")
    return value


def _handle_digest(recovery_handle: str) -> str:
    try:
        _identifier(recovery_handle, "recovery handle")
    except RecoveryDescriptorError as exc:
        raise ObjectCorrupt("invalid recovery handle") from exc
    return hashlib.sha256(recovery_handle.encode("ascii")).hexdigest()


def _descriptor_locator(digest: str) -> str:
    return f"descriptors/{digest}.json"


def _bundle_locator(subject_id: str, backup_id: str, epoch: int, digest: str) -> str:
    return f"subjects/{subject_id}/{backup_id}/bundles/{epoch}/{digest}.zip"


def _pointer_locator(recovery_handle: str) -> str:
    return f"current/{_handle_digest(recovery_handle)}.json"


def _validate_unsigned_envelope(
    encoded: bytes, *, version: str, maximum: int, label: str
) -> dict[str, Any]:
    try:
        envelope = _decode_canonical_json(encoded, maximum=maximum, label=label)
        envelope = _exact_dict(envelope, {"payload", "signature", "version"}, label)
        if envelope["version"] != version:
            raise RecoveryDescriptorError(f"unsupported {label}")
        if version == DESCRIPTOR_VERSION:
            validate_descriptor_payload(envelope["payload"])
        else:
            validate_pointer_payload(envelope["payload"])
        _validate_signature_metadata(envelope["signature"])
        return envelope
    except RecoveryDescriptorError as exc:
        raise ObjectCorrupt(f"invalid stored {label}") from exc


def validate_descriptor_document(document: DescriptorDocument) -> bytes:
    if document.format_id != DESCRIPTOR_VERSION:
        raise ObjectCorrupt("unsupported descriptor document")
    if len(document.payload) > MAX_DESCRIPTOR_BYTES:
        raise ObjectTooLarge("descriptor exceeds size limit")
    _validate_unsigned_envelope(
        document.payload,
        version=DESCRIPTOR_VERSION,
        maximum=MAX_DESCRIPTOR_BYTES,
        label="descriptor",
    )
    return document.payload


def validate_current_pointer(pointer: CurrentDescriptorPointer) -> bytes:
    if pointer.format_id != CURRENT_POINTER_VERSION:
        raise ObjectCorrupt("unsupported current pointer")
    if len(pointer.payload) > MAX_POINTER_BYTES:
        raise ObjectTooLarge("current pointer exceeds size limit")
    _validate_unsigned_envelope(
        pointer.payload,
        version=CURRENT_POINTER_VERSION,
        maximum=MAX_POINTER_BYTES,
        label="current pointer",
    )
    return pointer.payload


def validate_bundle_storage_bytes(
    bundle: bytes,
    *,
    expected_subject_id: str,
    expected_backup_id: str,
    expected_epoch: int,
) -> bytes:
    if not isinstance(bundle, bytes) or not bundle:
        raise ObjectCorrupt("invalid stored recovery bundle")
    if len(bundle) > MAX_BUNDLE_BYTES:
        raise ObjectTooLarge("recovery bundle exceeds size limit")
    _lower_hex(expected_subject_id, "bundle subject", 32)
    _lower_hex(expected_backup_id, "bundle backup identifier", 16)
    _positive_epoch(expected_epoch)
    try:
        members = _read_bundle_members(bundle)
        descriptor_bytes = members[DESCRIPTOR_MEMBER]
        descriptor = _validate_unsigned_envelope(
            descriptor_bytes,
            version=DESCRIPTOR_VERSION,
            maximum=MAX_DESCRIPTOR_BYTES,
            label="descriptor",
        )
        backup = _decode_canonical_json(
            members[BACKUP_MEMBER], maximum=1024 * 1024, label="backup member"
        )
        backup_reference = BackupReference.from_backup(backup)
        payload = descriptor["payload"]
        if (
            payload["subject_id"] != expected_subject_id
            or payload["backup_id"] != expected_backup_id
            or payload["epoch"] != expected_epoch
            or backup_reference.bid != expected_backup_id
            or backup_reference.epoch != expected_epoch
        ):
            raise RecoveryDescriptorError("bundle storage identity mismatch")
        manifest = decode_manifest(members[MANIFEST_MEMBER])
        backup_format = manifest["members"][0]["format"]
        if members[MANIFEST_MEMBER] != create_manifest(
            backup_bytes=members[BACKUP_MEMBER],
            descriptor_bytes=descriptor_bytes,
            backup_format=backup_format,
        ):
            raise RecoveryDescriptorError("bundle storage manifest mismatch")
        return bundle
    except (RecoveryDescriptorError, ObjectStoreError) as exc:
        if isinstance(exc, ObjectTooLarge):
            raise
        raise ObjectCorrupt("invalid stored recovery bundle") from exc


def _descriptor_reference(document: DescriptorDocument) -> DescriptorReference:
    encoded = validate_descriptor_document(document)
    digest = hashlib.sha256(encoded).hexdigest()
    return DescriptorReference(locator=_descriptor_locator(digest), digest=digest)


def _bundle_reference(
    *, subject_id: str, backup_id: str, epoch: int, bundle: bytes
) -> RecoveryBundleReference:
    validate_bundle_storage_bytes(
        bundle,
        expected_subject_id=subject_id,
        expected_backup_id=backup_id,
        expected_epoch=epoch,
    )
    digest = hashlib.sha256(bundle).hexdigest()
    reference = RecoveryBundleReference(
        subject_id=subject_id,
        backup_id=backup_id,
        epoch=epoch,
        digest=digest,
        length=len(bundle),
        locator=_bundle_locator(subject_id, backup_id, epoch, digest),
    )
    reference.validate()
    return reference


_LOCKS_GUARD = threading.Lock()
_ROOT_LOCKS: dict[Path, threading.RLock] = {}


def _root_lock(root: Path) -> threading.RLock:
    with _LOCKS_GUARD:
        return _ROOT_LOCKS.setdefault(root, threading.RLock())


class FilesystemDescriptorBundleStore:
    """Deterministic same-host adapter with exact-byte CAS semantics."""

    def __init__(self, root: str | Path) -> None:
        requested = Path(root)
        try:
            requested.mkdir(parents=True, exist_ok=True)
            if requested.is_symlink() or not requested.is_dir():
                raise OSError("descriptor-store root is not a plain directory")
            self.root = requested.resolve(strict=True)
        except OSError as exc:
            raise ObjectStoreUnavailable("descriptor store is unavailable") from exc
        self._lock = _root_lock(self.root)

    def _path(self, locator: str) -> Path:
        locator = _safe_locator(locator)
        path = self.root.joinpath(*locator.split("/"))
        try:
            path.relative_to(self.root)
        except ValueError as exc:
            raise ObjectCorrupt("storage locator escapes root") from exc
        return path

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

    def _read(self, locator: str, maximum: int) -> bytes:
        path = self._path(locator)
        try:
            metadata = path.lstat()
            if path.is_symlink() or not stat.S_ISREG(metadata.st_mode):
                raise ObjectCorrupt("stored object is not a regular file")
            with path.open("rb") as handle:
                value = handle.read(maximum + 1)
        except FileNotFoundError as exc:
            raise ObjectNotFound("stored object was not found") from exc
        except ObjectStoreError:
            raise
        except OSError as exc:
            raise ObjectStoreUnavailable("descriptor store is unavailable") from exc
        if len(value) > maximum:
            raise ObjectTooLarge("stored object exceeds size limit")
        return value

    def _atomic_write(self, locator: str, value: bytes, *, replace: bool) -> None:
        path = self._path(locator)
        temporary: Path | None = None
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.parent.is_symlink() or not path.parent.is_dir():
                raise OSError("storage namespace is not a plain directory")
            with tempfile.NamedTemporaryFile(
                mode="wb", dir=path.parent, prefix=".pending-", delete=False
            ) as handle:
                temporary = Path(handle.name)
                handle.write(value)
                handle.flush()
                os.fsync(handle.fileno())
            if replace:
                os.replace(temporary, path)
                temporary = None
            else:
                os.link(temporary, path)
            self._fsync_directory(path.parent)
        except FileExistsError:
            raise
        except OSError as exc:
            raise ObjectStoreUnavailable("descriptor store is unavailable") from exc
        finally:
            if temporary is not None:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError:
                    pass

    def _publish(self, locator: str, value: bytes, maximum: int) -> None:
        if not value or len(value) > maximum:
            raise ObjectTooLarge("stored object exceeds size limit")
        with self._lock:
            try:
                self._atomic_write(locator, value, replace=False)
            except FileExistsError:
                if self._read(locator, maximum) != value:
                    raise ObjectConflict("immutable stored object conflicts") from None

    def publish_immutable(self, descriptor: DescriptorDocument) -> DescriptorReference:
        reference = _descriptor_reference(descriptor)
        self._publish(reference.locator, descriptor.payload, MAX_DESCRIPTOR_BYTES)
        return reference

    def read(self, reference: DescriptorReference) -> DescriptorDocument:
        _lower_hex(reference.digest, "descriptor digest", 32)
        if reference.locator != _descriptor_locator(reference.digest):
            raise ObjectCorrupt("descriptor locator/digest mismatch")
        encoded = self._read(reference.locator, MAX_DESCRIPTOR_BYTES)
        if hashlib.sha256(encoded).hexdigest() != reference.digest:
            raise ObjectCorrupt("stored descriptor digest mismatch")
        document = DescriptorDocument(format_id=DESCRIPTOR_VERSION, payload=encoded)
        validate_descriptor_document(document)
        return document

    def read_current(self, recovery_handle: str) -> CurrentDescriptorPointer:
        encoded = self._read(_pointer_locator(recovery_handle), MAX_POINTER_BYTES)
        pointer = CurrentDescriptorPointer(
            format_id=CURRENT_POINTER_VERSION, payload=encoded
        )
        validate_current_pointer(pointer)
        return pointer

    def compare_and_swap_current(
        self,
        recovery_handle: str,
        expected: CurrentDescriptorPointer | None,
        replacement: CurrentDescriptorPointer,
    ) -> None:
        replacement_bytes = validate_current_pointer(replacement)
        expected_bytes = (
            None if expected is None else validate_current_pointer(expected)
        )
        locator = _pointer_locator(recovery_handle)
        with self._lock:
            try:
                current = self._read(locator, MAX_POINTER_BYTES)
            except ObjectNotFound:
                if expected_bytes is not None:
                    raise ObjectStale("current pointer is absent") from None
                try:
                    self._atomic_write(locator, replacement_bytes, replace=False)
                except FileExistsError:
                    raise ObjectStale("current pointer changed concurrently") from None
                return
            if current == replacement_bytes:
                return
            if expected_bytes is None:
                raise ObjectConflict("current pointer already exists")
            if current != expected_bytes:
                raise ObjectStale("current pointer expectation is stale")
            self._atomic_write(locator, replacement_bytes, replace=True)

    def create_bundle(
        self, *, subject_id: str, backup_id: str, epoch: int, bundle: bytes
    ) -> RecoveryBundleReference:
        reference = _bundle_reference(
            subject_id=subject_id, backup_id=backup_id, epoch=epoch, bundle=bundle
        )
        self._publish(reference.locator, bundle, MAX_BUNDLE_BYTES)
        return reference

    def read_bundle(self, reference: RecoveryBundleReference) -> bytes:
        reference.validate()
        if reference.locator != _bundle_locator(
            reference.subject_id,
            reference.backup_id,
            reference.epoch,
            reference.digest,
        ):
            raise ObjectCorrupt("bundle locator/digest mismatch")
        bundle = self._read(reference.locator, MAX_BUNDLE_BYTES)
        if len(bundle) != reference.length or hashlib.sha256(bundle).hexdigest() != (
            reference.digest
        ):
            raise ObjectCorrupt("stored bundle binding mismatch")
        return validate_bundle_storage_bytes(
            bundle,
            expected_subject_id=reference.subject_id,
            expected_backup_id=reference.backup_id,
            expected_epoch=reference.epoch,
        )


class SameHostDescriptorService:
    """Service-shaped local adapter; P3 places admission in front of it."""

    def __init__(self, store: FilesystemDescriptorBundleStore) -> None:
        self.store = store

    def descriptor_store(self) -> DescriptorStore:
        return cast(DescriptorStore, self.store)

    def bundle_store(self) -> RecoveryBundleStore:
        return cast(RecoveryBundleStore, self.store)


class S3DescriptorBundleStore:
    """Exact-key S3 adapter; never lists data or authenticates LOCUS signatures."""

    def __init__(
        self, *, client: S3Client, bucket: str, prefix: str = DEFAULT_DESCRIPTOR_PREFIX
    ) -> None:
        self._client = client
        self.bucket = _validate_bucket(bucket)
        self.prefix = _validate_prefix(prefix)

    def _key(self, locator: str) -> str:
        return f"{self.prefix}/{_safe_locator(locator)}"

    def _read_key(self, locator: str, maximum: int) -> tuple[bytes, str]:
        try:
            response = self._client.get_object(
                Bucket=self.bucket, Key=self._key(locator)
            )
        except Exception as exc:
            if _is_not_found(exc):
                raise ObjectNotFound("stored S3 object was not found") from exc
            raise ObjectStoreUnavailable("S3 descriptor store is unavailable") from exc
        if not isinstance(response, dict):
            raise ObjectStoreUnavailable("invalid S3 response")
        length, body, etag = (
            response.get("ContentLength"),
            response.get("Body"),
            response.get("ETag"),
        )
        if (
            isinstance(length, bool)
            or not isinstance(length, int)
            or length < 0
            or not isinstance(etag, str)
            or not etag
            or body is None
            or not hasattr(body, "read")
            or not hasattr(body, "close")
        ):
            raise ObjectStoreUnavailable("invalid S3 response")
        try:
            if length > maximum:
                raise ObjectTooLarge("stored S3 object exceeds size limit")
            value = body.read(maximum + 1)
        except ObjectStoreError:
            raise
        except Exception as exc:
            raise ObjectStoreUnavailable("S3 object read failed") from exc
        finally:
            try:
                body.close()
            except Exception:
                pass
        if not isinstance(value, bytes) or len(value) != length:
            raise ObjectStoreUnavailable("incomplete S3 object read")
        if len(value) > maximum:
            raise ObjectTooLarge("stored S3 object exceeds size limit")
        return value, etag

    def _put(
        self,
        locator: str,
        value: bytes,
        *,
        condition: dict[str, str],
        content_type: str,
    ) -> None:
        checksum = base64.b64encode(hashlib.sha256(value).digest()).decode("ascii")
        self._client.put_object(
            Bucket=self.bucket,
            Key=self._key(locator),
            Body=value,
            ContentLength=len(value),
            ContentType=content_type,
            ChecksumSHA256=checksum,
            **condition,
        )

    def _publish(
        self, locator: str, value: bytes, maximum: int, content_type: str
    ) -> None:
        if not value or len(value) > maximum:
            raise ObjectTooLarge("stored object exceeds size limit")
        for attempt in range(MAX_CONDITIONAL_WRITE_ATTEMPTS):
            try:
                self._put(
                    locator,
                    value,
                    condition={"IfNoneMatch": "*"},
                    content_type=content_type,
                )
                return
            except Exception as exc:
                if _is_precondition_failed(exc):
                    existing, _etag = self._read_key(locator, maximum)
                    if existing == value:
                        return
                    raise ObjectConflict("immutable S3 object conflicts") from None
                if (
                    _is_conditional_conflict(exc)
                    and attempt + 1 < MAX_CONDITIONAL_WRITE_ATTEMPTS
                ):
                    continue
                raise ObjectStoreUnavailable(
                    "S3 descriptor store is unavailable"
                ) from exc
        raise ObjectStoreUnavailable("S3 conditional write did not converge")

    def publish_immutable(self, descriptor: DescriptorDocument) -> DescriptorReference:
        reference = _descriptor_reference(descriptor)
        self._publish(
            reference.locator,
            descriptor.payload,
            MAX_DESCRIPTOR_BYTES,
            "application/json",
        )
        return reference

    def read(self, reference: DescriptorReference) -> DescriptorDocument:
        _lower_hex(reference.digest, "descriptor digest", 32)
        if reference.locator != _descriptor_locator(reference.digest):
            raise ObjectCorrupt("descriptor locator/digest mismatch")
        encoded, _etag = self._read_key(reference.locator, MAX_DESCRIPTOR_BYTES)
        if hashlib.sha256(encoded).hexdigest() != reference.digest:
            raise ObjectCorrupt("stored descriptor digest mismatch")
        document = DescriptorDocument(format_id=DESCRIPTOR_VERSION, payload=encoded)
        validate_descriptor_document(document)
        return document

    def read_current(self, recovery_handle: str) -> CurrentDescriptorPointer:
        encoded, _etag = self._read_key(
            _pointer_locator(recovery_handle), MAX_POINTER_BYTES
        )
        pointer = CurrentDescriptorPointer(
            format_id=CURRENT_POINTER_VERSION, payload=encoded
        )
        validate_current_pointer(pointer)
        return pointer

    def compare_and_swap_current(
        self,
        recovery_handle: str,
        expected: CurrentDescriptorPointer | None,
        replacement: CurrentDescriptorPointer,
    ) -> None:
        replacement_bytes = validate_current_pointer(replacement)
        expected_bytes = (
            None if expected is None else validate_current_pointer(expected)
        )
        locator = _pointer_locator(recovery_handle)
        try:
            current, etag = self._read_key(locator, MAX_POINTER_BYTES)
        except ObjectNotFound:
            if expected_bytes is not None:
                raise ObjectStale("current pointer is absent") from None
            try:
                self._put(
                    locator,
                    replacement_bytes,
                    condition={"IfNoneMatch": "*"},
                    content_type="application/json",
                )
                return
            except Exception as exc:
                if _is_precondition_failed(exc) or _is_conditional_conflict(exc):
                    raise ObjectStale("current pointer changed concurrently") from None
                raise ObjectStoreUnavailable(
                    "S3 descriptor store is unavailable"
                ) from exc
        if current == replacement_bytes:
            return
        if expected_bytes is None:
            raise ObjectConflict("current pointer already exists")
        if current != expected_bytes:
            raise ObjectStale("current pointer expectation is stale")
        try:
            self._put(
                locator,
                replacement_bytes,
                condition={"IfMatch": etag},
                content_type="application/json",
            )
        except Exception as exc:
            if _is_precondition_failed(exc) or _is_conditional_conflict(exc):
                raise ObjectStale("current pointer changed concurrently") from None
            raise ObjectStoreUnavailable("S3 descriptor store is unavailable") from exc

    def create_bundle(
        self, *, subject_id: str, backup_id: str, epoch: int, bundle: bytes
    ) -> RecoveryBundleReference:
        reference = _bundle_reference(
            subject_id=subject_id, backup_id=backup_id, epoch=epoch, bundle=bundle
        )
        self._publish(reference.locator, bundle, MAX_BUNDLE_BYTES, "application/zip")
        return reference

    def read_bundle(self, reference: RecoveryBundleReference) -> bytes:
        reference.validate()
        if reference.locator != _bundle_locator(
            reference.subject_id, reference.backup_id, reference.epoch, reference.digest
        ):
            raise ObjectCorrupt("bundle locator/digest mismatch")
        bundle, _etag = self._read_key(reference.locator, MAX_BUNDLE_BYTES)
        if (
            len(bundle) != reference.length
            or hashlib.sha256(bundle).hexdigest() != reference.digest
        ):
            raise ObjectCorrupt("stored bundle binding mismatch")
        return validate_bundle_storage_bytes(
            bundle,
            expected_subject_id=reference.subject_id,
            expected_backup_id=reference.backup_id,
            expected_epoch=reference.epoch,
        )


__all__ = [
    "DESCRIPTOR_STORE_PROFILE",
    "FilesystemDescriptorBundleStore",
    "RecoveryBundleReference",
    "RecoveryBundleStore",
    "S3DescriptorBundleStore",
    "SameHostDescriptorService",
    "validate_bundle_storage_bytes",
    "validate_current_pointer",
    "validate_descriptor_document",
]
