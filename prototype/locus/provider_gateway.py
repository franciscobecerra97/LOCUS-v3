"""Admitted application gateway backend for LOCUS storage providers."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, cast

from .admission import pseudonymous_object_prefix
from .codec import encode
from .contracts import (
    CurrentDescriptorPointer,
    DescriptorDocument,
    DescriptorReference,
    GatewayRequest,
    GatewayResult,
    StorageOperation,
)
from .descriptor_store import (
    RecoveryBundleReference,
    validate_current_pointer,
    validate_descriptor_document,
)
from .object_store import (
    BackupReference,
    ObjectCorrupt,
    decode_backup_object,
    decode_versioned_backup_object,
    encode_backup_object,
    encode_versioned_backup_object,
)
from .recovery_descriptor import (
    CURRENT_POINTER_VERSION,
    DESCRIPTOR_VERSION,
    MAX_POINTER_BYTES,
)
from .storage_provider import StorageProvider

PROVIDER_GATEWAY_PROFILE = "LOCUS-application-storage-gateway-v1"
PROVIDER_GATEWAY_PROFILE_V2 = "LOCUS-application-storage-gateway-v2"
POINTER_CAS_FORMAT = "LOCUS-storage-pointer-cas-v1"
MAX_CAS_PAYLOAD_BYTES = 4 * MAX_POINTER_BYTES + 1024


class GatewayObjectKind(Enum):
    BACKUP = "backup"
    DESCRIPTOR = "descriptor"
    BUNDLE = "bundle"
    CURRENT_POINTER = "current"


def _digest(value: str, label: str) -> str:
    if re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ObjectCorrupt(f"invalid {label}")
    return value


def _pointer_handle_digest(recovery_handle: str) -> str:
    if (
        not isinstance(recovery_handle, str)
        or not recovery_handle
        or len(recovery_handle) > 255
        or not recovery_handle.isascii()
        or any(
            ord(character) < 0x21 or ord(character) > 0x7E
            for character in recovery_handle
        )
    ):
        raise ObjectCorrupt("invalid recovery handle")
    return hashlib.sha256(recovery_handle.encode("ascii")).hexdigest()


def backup_object_key(subject_id: str, reference: BackupReference) -> str:
    reference.validate()
    return (
        pseudonymous_object_prefix(subject_id, reference.bid)
        + f"epochs/{reference.epoch}/backup/{reference.backup_digest}.json"
    )


def descriptor_object_key(
    subject_id: str, backup: BackupReference, descriptor_digest: str
) -> str:
    backup.validate()
    digest = _digest(descriptor_digest, "descriptor digest")
    return (
        pseudonymous_object_prefix(subject_id, backup.bid)
        + f"epochs/{backup.epoch}/descriptor/{digest}.json"
    )


def bundle_object_key(
    subject_id: str,
    backup: BackupReference,
    bundle_digest: str,
    bundle_length: int,
) -> str:
    backup.validate()
    digest = _digest(bundle_digest, "bundle digest")
    if (
        isinstance(bundle_length, bool)
        or not isinstance(bundle_length, int)
        or bundle_length < 1
        or bundle_length > 2 * 1024 * 1024
    ):
        raise ObjectCorrupt("invalid bundle length")
    return (
        pseudonymous_object_prefix(subject_id, backup.bid)
        + f"epochs/{backup.epoch}/bundle/{digest}/{bundle_length}.zip"
    )


def current_pointer_object_key(
    subject_id: str, backup: BackupReference, recovery_handle: str
) -> str:
    backup.validate()
    handle_digest = _pointer_handle_digest(recovery_handle)
    return (
        pseudonymous_object_prefix(subject_id, backup.bid)
        + f"current/{handle_digest}.json"
    )


def encode_pointer_cas(
    *,
    expected: CurrentDescriptorPointer | None,
    replacement: CurrentDescriptorPointer,
) -> bytes:
    replacement_bytes = validate_current_pointer(replacement)
    expected_bytes = None if expected is None else validate_current_pointer(expected)
    payload = encode(
        {
            "expected_hex": None if expected_bytes is None else expected_bytes.hex(),
            "replacement_hex": replacement_bytes.hex(),
            "version": POINTER_CAS_FORMAT,
        }
    )
    if len(payload) > MAX_CAS_PAYLOAD_BYTES:
        raise ObjectCorrupt("pointer CAS payload exceeds size limit")
    return payload


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON member")
        result[key] = value
    return result


def decode_pointer_cas(
    value: bytes,
) -> tuple[CurrentDescriptorPointer | None, CurrentDescriptorPointer]:
    if not isinstance(value, bytes) or not value or len(value) > MAX_CAS_PAYLOAD_BYTES:
        raise ObjectCorrupt("invalid pointer CAS payload")
    try:
        decoded = json.loads(
            value.decode("utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=lambda _value: (_ for _ in ()).throw(
                ValueError("non-finite JSON number")
            ),
        )
        if (
            not isinstance(decoded, dict)
            or set(decoded) != {"expected_hex", "replacement_hex", "version"}
            or decoded["version"] != POINTER_CAS_FORMAT
            or encode(decoded) != value
            or decoded["expected_hex"] is not None
            and not isinstance(decoded["expected_hex"], str)
            or not isinstance(decoded["replacement_hex"], str)
        ):
            raise ValueError("invalid pointer CAS object")
        expected_bytes = (
            None
            if decoded["expected_hex"] is None
            else bytes.fromhex(decoded["expected_hex"])
        )
        replacement_bytes = bytes.fromhex(decoded["replacement_hex"])
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        raise ObjectCorrupt("invalid pointer CAS payload") from exc
    expected = (
        None
        if expected_bytes is None
        else CurrentDescriptorPointer(
            format_id=CURRENT_POINTER_VERSION, payload=expected_bytes
        )
    )
    replacement = CurrentDescriptorPointer(
        format_id=CURRENT_POINTER_VERSION, payload=replacement_bytes
    )
    if expected is not None:
        validate_current_pointer(expected)
    validate_current_pointer(replacement)
    return expected, replacement


def _pointer_binding(pointer: CurrentDescriptorPointer) -> tuple[str, int]:
    validate_current_pointer(pointer)
    try:
        envelope = json.loads(pointer.payload)
        payload = envelope["payload"]
        backup_id, epoch = payload["backup_id"], payload["epoch"]
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ObjectCorrupt("invalid current-pointer binding") from exc
    if not isinstance(backup_id, str) or not isinstance(epoch, int):
        raise ObjectCorrupt("invalid current-pointer binding")
    return backup_id, epoch


@dataclass
class ProviderStorageGatewayBackend:
    """Execute exact admitted operations without receiving a provider credential."""

    provider: StorageProvider
    subject_id: str
    recovery_handle: str
    profile_id: str = PROVIDER_GATEWAY_PROFILE

    def __post_init__(self) -> None:
        pseudonymous_object_prefix(self.subject_id, "00" * 16)
        _pointer_handle_digest(self.recovery_handle)

    def _relative_key(self, request: GatewayRequest) -> str:
        prefix = pseudonymous_object_prefix(
            self.subject_id, request.backup_reference.bid
        )
        if not request.object_key.startswith(prefix):
            raise ObjectCorrupt("gateway object key is outside account scope")
        relative = request.object_key[len(prefix) :]
        if not relative or any(part in {"", ".", ".."} for part in relative.split("/")):
            raise ObjectCorrupt("invalid gateway object key")
        return relative

    @staticmethod
    def _require_payload(request: GatewayRequest) -> bytes:
        if request.payload is None:
            raise ObjectCorrupt("gateway operation requires a payload")
        return request.payload

    def _backup(self, request: GatewayRequest) -> GatewayResult:
        if request.object_key != backup_object_key(
            self.subject_id, request.backup_reference
        ):
            raise ObjectCorrupt("backup gateway key mismatch")
        if request.operation is StorageOperation.CREATE_IMMUTABLE:
            _reference, backup = decode_backup_object(
                self._require_payload(request), expected=request.backup_reference
            )
            stored = self.provider.backups.create(backup)
            if stored != request.backup_reference:
                raise ObjectCorrupt("stored backup reference mismatch")
            return GatewayResult(reference=stored)
        if request.operation is StorageOperation.READ_EXACT:
            backup = self.provider.backups.read(request.backup_reference)
            reference, encoded = encode_backup_object(backup)
            if reference != request.backup_reference:
                raise ObjectCorrupt("stored backup reference mismatch")
            return GatewayResult(reference=reference, payload=encoded)
        if request.operation is StorageOperation.DELETE_EXACT:
            self.provider.backups.delete(request.backup_reference)
            return GatewayResult(reference=request.backup_reference)
        raise ObjectCorrupt("unsupported backup gateway operation")

    def _descriptor(self, request: GatewayRequest, relative: str) -> GatewayResult:
        match = re.fullmatch(
            rf"epochs/{request.backup_reference.epoch}/descriptor/([0-9a-f]{{64}})\.json",
            relative,
        )
        if match is None:
            raise ObjectCorrupt("invalid descriptor gateway key")
        digest = match.group(1)
        reference = DescriptorReference(
            locator=f"descriptors/{digest}.json", digest=digest
        )
        if request.operation is StorageOperation.CREATE_IMMUTABLE:
            document = DescriptorDocument(
                format_id=DESCRIPTOR_VERSION, payload=self._require_payload(request)
            )
            validate_descriptor_document(document)
            stored = self.provider.descriptors.publish_immutable(document)
            if stored != reference:
                raise ObjectCorrupt("descriptor gateway binding mismatch")
            return GatewayResult(reference=request.backup_reference)
        if request.operation is StorageOperation.READ_EXACT:
            document = self.provider.descriptors.read(reference)
            return GatewayResult(
                reference=request.backup_reference, payload=document.payload
            )
        raise ObjectCorrupt("unsupported descriptor gateway operation")

    def _bundle(self, request: GatewayRequest, relative: str) -> GatewayResult:
        match = re.fullmatch(
            rf"epochs/{request.backup_reference.epoch}/bundle/([0-9a-f]{{64}})/(\d{{1,7}})\.zip",
            relative,
        )
        if match is None:
            raise ObjectCorrupt("invalid bundle gateway key")
        digest, length = match.group(1), int(match.group(2))
        object_key = bundle_object_key(
            self.subject_id, request.backup_reference, digest, length
        )
        if request.object_key != object_key:
            raise ObjectCorrupt("bundle gateway key mismatch")
        if request.operation is StorageOperation.CREATE_IMMUTABLE:
            stored = self.provider.bundles.create_bundle(
                subject_id=self.subject_id,
                backup_id=request.backup_reference.bid,
                epoch=request.backup_reference.epoch,
                bundle=self._require_payload(request),
            )
            if stored.digest != digest or stored.length != length:
                raise ObjectCorrupt("bundle gateway binding mismatch")
            return GatewayResult(reference=request.backup_reference)
        if request.operation is StorageOperation.READ_EXACT:
            reference = RecoveryBundleReference(
                subject_id=self.subject_id,
                backup_id=request.backup_reference.bid,
                epoch=request.backup_reference.epoch,
                digest=digest,
                length=length,
                locator=(
                    f"subjects/{self.subject_id}/{request.backup_reference.bid}/"
                    f"bundles/{request.backup_reference.epoch}/{digest}.zip"
                ),
            )
            bundle = self.provider.bundles.read_bundle(reference)
            return GatewayResult(reference=request.backup_reference, payload=bundle)
        raise ObjectCorrupt("unsupported bundle gateway operation")

    def _current(self, request: GatewayRequest) -> GatewayResult:
        if request.object_key != current_pointer_object_key(
            self.subject_id, request.backup_reference, self.recovery_handle
        ):
            raise ObjectCorrupt("current-pointer gateway key mismatch")
        if request.operation is StorageOperation.READ_EXACT:
            pointer = self.provider.descriptors.read_current(self.recovery_handle)
            if _pointer_binding(pointer) != (
                request.backup_reference.bid,
                request.backup_reference.epoch,
            ):
                raise ObjectCorrupt("current-pointer gateway binding mismatch")
            return GatewayResult(
                reference=request.backup_reference, payload=pointer.payload
            )
        if request.operation is StorageOperation.COMPARE_AND_SWAP:
            expected, replacement = decode_pointer_cas(self._require_payload(request))
            if _pointer_binding(replacement) != (
                request.backup_reference.bid,
                request.backup_reference.epoch,
            ):
                raise ObjectCorrupt("replacement pointer binding mismatch")
            self.provider.descriptors.compare_and_swap_current(
                self.recovery_handle, expected, replacement
            )
            return GatewayResult(reference=request.backup_reference)
        raise ObjectCorrupt("unsupported current-pointer gateway operation")

    def execute(self, request: GatewayRequest) -> GatewayResult:
        relative = self._relative_key(request)
        if relative.startswith(f"epochs/{request.backup_reference.epoch}/backup/"):
            return self._backup(request)
        if relative.startswith(f"epochs/{request.backup_reference.epoch}/descriptor/"):
            return self._descriptor(request, relative)
        if relative.startswith(f"epochs/{request.backup_reference.epoch}/bundle/"):
            return self._bundle(request, relative)
        if relative.startswith("current/"):
            return self._current(request)
        raise ObjectCorrupt("unsupported gateway object role")


@dataclass
class VersionedProviderStorageGatewayBackend(ProviderStorageGatewayBackend):
    """Additive gateway for registered v5/v6 backup objects.

    All descriptor, bundle, pointer, admission, and object-key behavior is
    inherited unchanged.  Only the backup-envelope codec is replaced, leaving
    the frozen v1 gateway semantics intact for its retained evidence.
    """

    profile_id: str = PROVIDER_GATEWAY_PROFILE_V2

    def _backup(self, request: GatewayRequest) -> GatewayResult:
        if request.object_key != backup_object_key(
            self.subject_id, request.backup_reference
        ):
            raise ObjectCorrupt("backup gateway key mismatch")
        backups = cast(Any, self.provider.backups)
        if request.operation is StorageOperation.CREATE_IMMUTABLE:
            _reference, backup = decode_versioned_backup_object(
                self._require_payload(request), expected=request.backup_reference
            )
            stored = backups.create_versioned(backup)
            if stored != request.backup_reference:
                raise ObjectCorrupt("stored backup reference mismatch")
            return GatewayResult(reference=stored)
        if request.operation is StorageOperation.READ_EXACT:
            backup = backups.read_versioned(request.backup_reference)
            reference, encoded = encode_versioned_backup_object(backup)
            if reference != request.backup_reference:
                raise ObjectCorrupt("stored backup reference mismatch")
            return GatewayResult(reference=reference, payload=encoded)
        if request.operation is StorageOperation.DELETE_EXACT:
            backups.delete(request.backup_reference)
            return GatewayResult(reference=request.backup_reference)
        raise ObjectCorrupt("unsupported backup gateway operation")


def aws_prefix_policy(*, bucket: str, prefix: str) -> dict[str, Any]:
    """Return the narrow data-plane policy expected for the gateway role."""

    if re.fullmatch(r"[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]", bucket) is None:
        raise ValueError("invalid AWS S3 bucket")
    normalized = prefix.strip("/")
    if (
        not normalized
        or len(normalized) > 512
        or any(part in {"", ".", ".."} for part in normalized.split("/"))
        or re.fullmatch(r"[A-Za-z0-9._/-]+", normalized) is None
    ):
        raise ValueError("invalid AWS S3 prefix")
    return cast(
        dict[str, Any],
        {
            "Statement": [
                {
                    "Action": ["s3:DeleteObject", "s3:GetObject", "s3:PutObject"],
                    "Condition": {"Bool": {"aws:SecureTransport": "true"}},
                    "Effect": "Allow",
                    "Resource": f"arn:aws:s3:::{bucket}/{normalized}/*",
                }
            ],
            "Version": "2012-10-17",
        },
    )


__all__ = [
    "POINTER_CAS_FORMAT",
    "PROVIDER_GATEWAY_PROFILE",
    "GatewayObjectKind",
    "ProviderStorageGatewayBackend",
    "aws_prefix_policy",
    "backup_object_key",
    "bundle_object_key",
    "current_pointer_object_key",
    "decode_pointer_cas",
    "descriptor_object_key",
    "encode_pointer_cas",
]
