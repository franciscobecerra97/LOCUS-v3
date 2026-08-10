"""Strict P2.1 RecoveryDescriptor, current-pointer, and bundle codecs."""

from __future__ import annotations

import hashlib
import io
import json
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, cast
from urllib.parse import urlsplit

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from .codec import encode
from .crypto import hash_bytes
from .object_store import BackupReference, ObjectCorrupt

DESCRIPTOR_VERSION = "LOCUS-recovery-descriptor-v1"
CURRENT_POINTER_VERSION = "LOCUS-descriptor-current-pointer-v1"
BUNDLE_MANIFEST_VERSION = "LOCUS-recovery-bundle-manifest-v1"
BUNDLE_PROFILE = "LOCUS-recovery-bundle-v1"
SIGNATURE_VERSION = "LOCUS-bootstrap-signature-v1"
CONFIGURATION_VERSION = "LOCUS-recovery-configuration-v1"

SIGNATURE_ALGORITHM = "Ed25519"
BACKUP_MEMBER = "backup.json"
DESCRIPTOR_MEMBER = "descriptor.json"
MANIFEST_MEMBER = "manifest.json"
BUNDLE_MEMBERS = (BACKUP_MEMBER, DESCRIPTOR_MEMBER, MANIFEST_MEMBER)

MAX_DESCRIPTOR_BYTES = 64 * 1024
MAX_POINTER_BYTES = 16 * 1024
MAX_MANIFEST_BYTES = 16 * 1024
MAX_BACKUP_MEMBER_BYTES = 1024 * 1024
MAX_BUNDLE_BYTES = 2 * 1024 * 1024
MAX_TOTAL_MEMBER_BYTES = (
    MAX_BACKUP_MEMBER_BYTES + MAX_DESCRIPTOR_BYTES + MAX_MANIFEST_BYTES
)
MAX_PUBLIC_PARAMETERS_BYTES = 256 * 1024
MAX_IDENTIFIER_CHARS = 255
MAX_ENDPOINT_CHARS = 512
MAX_LOCATOR_CHARS = 1024
MAX_PARTIES = 255
MAX_EPOCH = 2**63 - 1
MAX_COMPRESSION_RATIO = 20
ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
ZIP_EXTERNAL_ATTRIBUTES = 0o100600 << 16


class RecoveryDescriptorError(ValueError):
    """A descriptor, pointer, manifest, or bundle failed closed."""


@dataclass(frozen=True)
class RecoveryBundle:
    backup: dict[str, Any]
    backup_bytes: bytes
    descriptor: dict[str, Any]
    descriptor_bytes: bytes
    manifest: dict[str, Any]
    manifest_bytes: bytes
    bundle_bytes: bytes

    @property
    def bundle_digest(self) -> str:
        return hashlib.sha256(self.bundle_bytes).hexdigest()


def _exact_dict(value: object, fields: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        raise RecoveryDescriptorError(f"invalid {label}")
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
        raise RecoveryDescriptorError(f"invalid {label}")
    return value


def _lower_hex(value: object, label: str, *, byte_length: int) -> str:
    if (
        not isinstance(value, str)
        or len(value) != byte_length * 2
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise RecoveryDescriptorError(f"invalid {label}")
    return value


def _opaque_hex(value: object, label: str, *, maximum_bytes: int) -> str:
    if (
        not isinstance(value, str)
        or not value
        or len(value) % 2
        or len(value) > maximum_bytes * 2
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise RecoveryDescriptorError(f"invalid {label}")
    return value


def _integer(
    value: object, label: str, *, minimum: int = 0, maximum: int = MAX_EPOCH
) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < minimum
        or value > maximum
    ):
        raise RecoveryDescriptorError(f"invalid {label}")
    return value


def _endpoint(value: object) -> str:
    endpoint = _identifier(value, "authorizer endpoint", maximum=MAX_ENDPOINT_CHARS)
    parsed = urlsplit(endpoint)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or parsed.path not in {"", "/"}
    ):
        raise RecoveryDescriptorError("invalid authorizer endpoint")
    try:
        _ = parsed.port
    except ValueError as exc:
        raise RecoveryDescriptorError("invalid authorizer endpoint") from exc
    return endpoint


def _reject_duplicate_members(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON member")
        result[key] = value
    return result


def _decode_canonical_json(
    encoded: bytes, *, maximum: int, label: str
) -> dict[str, Any]:
    if not isinstance(encoded, bytes) or not encoded or len(encoded) > maximum:
        raise RecoveryDescriptorError(f"invalid {label}")
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
        TypeError,
        ValueError,
        RecursionError,
    ) as exc:
        raise RecoveryDescriptorError(f"invalid {label}") from exc
    return cast(dict[str, Any], value)


def _validate_signature_metadata(value: object) -> dict[str, Any]:
    signature = _exact_dict(
        value,
        {"algorithm", "key_id", "value", "version"},
        "bootstrap signature",
    )
    if (
        signature["version"] != SIGNATURE_VERSION
        or signature["algorithm"] != SIGNATURE_ALGORITHM
    ):
        raise RecoveryDescriptorError("unsupported bootstrap signature")
    _identifier(signature["key_id"], "bootstrap signing key identifier")
    _lower_hex(signature["value"], "bootstrap signature", byte_length=64)
    return signature


def _signature_message(
    *, object_version: str, payload: dict[str, Any], key_id: str
) -> bytes:
    signed = {
        "object_version": object_version,
        "payload": payload,
        "signature": {
            "algorithm": SIGNATURE_ALGORITHM,
            "key_id": key_id,
            "version": SIGNATURE_VERSION,
        },
    }
    return b"LOCUS/bootstrap-signed-object/v1\x00" + encode(signed)


def _sign_envelope(
    *,
    object_version: str,
    payload: dict[str, Any],
    signer: Ed25519PrivateKey,
    key_id: str,
) -> bytes:
    _identifier(key_id, "bootstrap signing key identifier")
    signature = signer.sign(
        _signature_message(
            object_version=object_version,
            payload=payload,
            key_id=key_id,
        )
    )
    return encode(
        {
            "payload": payload,
            "signature": {
                "algorithm": SIGNATURE_ALGORITHM,
                "key_id": key_id,
                "value": signature.hex(),
                "version": SIGNATURE_VERSION,
            },
            "version": object_version,
        }
    )


def _verify_envelope(
    encoded: bytes,
    *,
    object_version: str,
    maximum: int,
    label: str,
    payload_validator: Callable[[object], dict[str, Any]],
    issuer_public_key: Ed25519PublicKey,
    expected_issuer: str,
    expected_key_id: str,
) -> dict[str, Any]:
    envelope = _decode_canonical_json(encoded, maximum=maximum, label=label)
    envelope = _exact_dict(envelope, {"payload", "signature", "version"}, label)
    if envelope["version"] != object_version:
        raise RecoveryDescriptorError(f"unsupported {label}")
    payload = payload_validator(envelope["payload"])
    if payload["issuer"] != expected_issuer:
        raise RecoveryDescriptorError(f"{label} issuer mismatch")
    signature = _validate_signature_metadata(envelope["signature"])
    if signature["key_id"] != expected_key_id:
        raise RecoveryDescriptorError(f"{label} signing key mismatch")
    try:
        issuer_public_key.verify(
            bytes.fromhex(signature["value"]),
            _signature_message(
                object_version=object_version,
                payload=payload,
                key_id=signature["key_id"],
            ),
        )
    except (InvalidSignature, ValueError) as exc:
        raise RecoveryDescriptorError(f"invalid {label} signature") from exc
    return envelope


def _validate_backup_binding(value: object) -> dict[str, Any]:
    binding = _exact_dict(
        value,
        {"format", "length", "member", "sha256"},
        "descriptor backup binding",
    )
    _identifier(binding["format"], "backup format")
    if binding["member"] != BACKUP_MEMBER:
        raise RecoveryDescriptorError("invalid descriptor backup member")
    _integer(
        binding["length"],
        "backup member length",
        minimum=1,
        maximum=MAX_BACKUP_MEMBER_BYTES,
    )
    _lower_hex(binding["sha256"], "backup member digest", byte_length=32)
    return binding


def _validate_cue_policy(value: object) -> dict[str, Any]:
    policy = _exact_dict(
        value,
        {"id", "public_parameters_hex", "resolver_profile"},
        "descriptor CuePolicy binding",
    )
    _identifier(policy["id"], "CuePolicy identifier")
    _opaque_hex(
        policy["public_parameters_hex"],
        "CuePolicy public parameters",
        maximum_bytes=MAX_PUBLIC_PARAMETERS_BYTES,
    )
    _identifier(policy["resolver_profile"], "resolver profile")
    return policy


def _validate_recovery_suite(value: object) -> dict[str, Any]:
    suite = _exact_dict(
        value,
        {
            "holders",
            "id",
            "public_state_format",
            "public_state_hex",
            "threshold",
        },
        "descriptor recovery-suite binding",
    )
    _identifier(suite["id"], "recovery-suite identifier")
    _identifier(suite["public_state_format"], "recovery-suite public-state format")
    _opaque_hex(
        suite["public_state_hex"],
        "recovery-suite public state",
        maximum_bytes=MAX_PUBLIC_PARAMETERS_BYTES,
    )
    threshold = _exact_dict(suite["threshold"], {"k", "n"}, "recovery threshold")
    k = _integer(
        threshold["k"], "reconstruction threshold", minimum=1, maximum=MAX_PARTIES
    )
    n = _integer(
        threshold["n"], "recovery holder count", minimum=1, maximum=MAX_PARTIES
    )
    if k > n:
        raise RecoveryDescriptorError("invalid recovery threshold")
    if not isinstance(suite["holders"], list) or len(suite["holders"]) != n:
        raise RecoveryDescriptorError("invalid recovery holder membership")
    holder_ids: list[int] = []
    for raw_holder in suite["holders"]:
        holder = _exact_dict(
            raw_holder,
            {"authorizer_id", "holder_id"},
            "recovery holder",
        )
        holder_ids.append(
            _integer(
                holder["holder_id"],
                "recovery holder identifier",
                minimum=1,
                maximum=MAX_PARTIES,
            )
        )
        _integer(
            holder["authorizer_id"],
            "holder authorizer identifier",
            minimum=1,
            maximum=MAX_PARTIES,
        )
    if holder_ids != sorted(set(holder_ids)):
        raise RecoveryDescriptorError("noncanonical recovery holder membership")
    return suite


def _validate_authorization(value: object) -> dict[str, Any]:
    authorization = _exact_dict(
        value,
        {
            "admission_profile",
            "audience",
            "authorizers",
            "operation_namespace",
            "quorum",
            "security_policy",
        },
        "descriptor authorization binding",
    )
    for field, label in (
        ("admission_profile", "admission profile"),
        ("audience", "admission audience"),
        ("operation_namespace", "operation namespace"),
        ("security_policy", "security-policy identifier"),
    ):
        _identifier(authorization[field], label)
    if (
        not isinstance(authorization["authorizers"], list)
        or not authorization["authorizers"]
        or len(authorization["authorizers"]) > MAX_PARTIES
    ):
        raise RecoveryDescriptorError("invalid authorizer membership")
    authorizer_ids: list[int] = []
    for raw_authorizer in authorization["authorizers"]:
        authorizer = _exact_dict(
            raw_authorizer,
            {"authorizer_id", "endpoint", "identity_key_id"},
            "descriptor authorizer",
        )
        authorizer_ids.append(
            _integer(
                authorizer["authorizer_id"],
                "authorizer identifier",
                minimum=1,
                maximum=MAX_PARTIES,
            )
        )
        _endpoint(authorizer["endpoint"])
        _identifier(authorizer["identity_key_id"], "authorizer identity key")
    if authorizer_ids != sorted(set(authorizer_ids)):
        raise RecoveryDescriptorError("noncanonical authorizer membership")
    _integer(
        authorization["quorum"],
        "authorization quorum",
        minimum=1,
        maximum=len(authorizer_ids),
    )
    return authorization


def _configuration_input(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "authorization": payload["authorization"],
        "backup": payload["backup"],
        "backup_id": payload["backup_id"],
        "cue_policy": payload["cue_policy"],
        "epoch": payload["epoch"],
        "recovery_id": payload["recovery_id"],
        "recovery_suite": payload["recovery_suite"],
        "subject_id": payload["subject_id"],
        "version": CONFIGURATION_VERSION,
    }


def configuration_digest(payload: dict[str, Any]) -> str:
    """Return the P2.1 digest binding the complete public configuration."""

    return hash_bytes(
        CONFIGURATION_VERSION,
        encode(_configuration_input(payload)),
    ).hex()


def validate_descriptor_payload(value: object) -> dict[str, Any]:
    payload = _exact_dict(
        value,
        {
            "authorization",
            "backup",
            "backup_id",
            "cue_policy",
            "epoch",
            "expires_at",
            "issued_at",
            "issuer",
            "lifecycle",
            "recovery_id",
            "recovery_suite",
            "subject_id",
        },
        "RecoveryDescriptor payload",
    )
    _identifier(payload["issuer"], "descriptor issuer")
    _lower_hex(payload["subject_id"], "pseudonymous subject identifier", byte_length=32)
    _lower_hex(payload["backup_id"], "backup identifier", byte_length=16)
    _integer(payload["epoch"], "descriptor epoch", minimum=1)
    _identifier(payload["recovery_id"], "recovery identifier")
    issued_at = _integer(payload["issued_at"], "descriptor issuance time", minimum=1)
    expires_at = _integer(payload["expires_at"], "descriptor expiry", minimum=1)
    if expires_at <= issued_at:
        raise RecoveryDescriptorError("descriptor expiry is not after issuance")
    _validate_backup_binding(payload["backup"])
    _validate_cue_policy(payload["cue_policy"])
    suite = _validate_recovery_suite(payload["recovery_suite"])
    authorization = _validate_authorization(payload["authorization"])
    authorizer_ids = {
        authorizer["authorizer_id"] for authorizer in authorization["authorizers"]
    }
    if any(
        holder["authorizer_id"] not in authorizer_ids for holder in suite["holders"]
    ):
        raise RecoveryDescriptorError("recovery holder is not an authorizer")
    lifecycle = _exact_dict(
        payload["lifecycle"],
        {"configuration_digest", "predecessor_descriptor_digest"},
        "descriptor lifecycle binding",
    )
    _lower_hex(
        lifecycle["configuration_digest"],
        "configuration digest",
        byte_length=32,
    )
    predecessor = lifecycle["predecessor_descriptor_digest"]
    if predecessor is not None:
        _lower_hex(predecessor, "predecessor descriptor digest", byte_length=32)
    if lifecycle["configuration_digest"] != configuration_digest(payload):
        raise RecoveryDescriptorError("descriptor configuration digest mismatch")
    return payload


def create_descriptor(
    payload: dict[str, Any], *, signer: Ed25519PrivateKey, key_id: str
) -> bytes:
    validate_descriptor_payload(payload)
    encoded = _sign_envelope(
        object_version=DESCRIPTOR_VERSION,
        payload=payload,
        signer=signer,
        key_id=key_id,
    )
    if len(encoded) > MAX_DESCRIPTOR_BYTES:
        raise RecoveryDescriptorError("RecoveryDescriptor exceeds size limit")
    return encoded


def decode_descriptor(
    encoded: bytes,
    *,
    issuer_public_key: Ed25519PublicKey,
    expected_issuer: str,
    expected_key_id: str,
) -> dict[str, Any]:
    return _verify_envelope(
        encoded,
        object_version=DESCRIPTOR_VERSION,
        maximum=MAX_DESCRIPTOR_BYTES,
        label="RecoveryDescriptor",
        payload_validator=validate_descriptor_payload,
        issuer_public_key=issuer_public_key,
        expected_issuer=expected_issuer,
        expected_key_id=expected_key_id,
    )


def validate_pointer_payload(value: object) -> dict[str, Any]:
    payload = _exact_dict(
        value,
        {
            "backup_id",
            "bundle",
            "configuration_digest",
            "descriptor_sha256",
            "epoch",
            "expires_at",
            "issued_at",
            "issuer",
            "subject_id",
        },
        "descriptor current-pointer payload",
    )
    _identifier(payload["issuer"], "current-pointer issuer")
    _lower_hex(payload["subject_id"], "pseudonymous subject identifier", byte_length=32)
    _lower_hex(payload["backup_id"], "backup identifier", byte_length=16)
    _integer(payload["epoch"], "current-pointer epoch", minimum=1)
    issued_at = _integer(
        payload["issued_at"], "current-pointer issuance time", minimum=1
    )
    expires_at = _integer(payload["expires_at"], "current-pointer expiry", minimum=1)
    if expires_at <= issued_at:
        raise RecoveryDescriptorError("current-pointer expiry is not after issuance")
    _lower_hex(payload["descriptor_sha256"], "descriptor digest", byte_length=32)
    _lower_hex(payload["configuration_digest"], "configuration digest", byte_length=32)
    bundle = _exact_dict(
        payload["bundle"],
        {"length", "locator", "profile", "sha256"},
        "current-pointer bundle binding",
    )
    if bundle["profile"] != BUNDLE_PROFILE:
        raise RecoveryDescriptorError("unsupported recovery-bundle profile")
    _identifier(
        bundle["locator"], "immutable bundle locator", maximum=MAX_LOCATOR_CHARS
    )
    _integer(bundle["length"], "bundle length", minimum=1, maximum=MAX_BUNDLE_BYTES)
    _lower_hex(bundle["sha256"], "bundle digest", byte_length=32)
    return payload


def create_current_pointer(
    payload: dict[str, Any], *, signer: Ed25519PrivateKey, key_id: str
) -> bytes:
    validate_pointer_payload(payload)
    encoded = _sign_envelope(
        object_version=CURRENT_POINTER_VERSION,
        payload=payload,
        signer=signer,
        key_id=key_id,
    )
    if len(encoded) > MAX_POINTER_BYTES:
        raise RecoveryDescriptorError("descriptor current pointer exceeds size limit")
    return encoded


def decode_current_pointer(
    encoded: bytes,
    *,
    issuer_public_key: Ed25519PublicKey,
    expected_issuer: str,
    expected_key_id: str,
) -> dict[str, Any]:
    return _verify_envelope(
        encoded,
        object_version=CURRENT_POINTER_VERSION,
        maximum=MAX_POINTER_BYTES,
        label="descriptor current pointer",
        payload_validator=validate_pointer_payload,
        issuer_public_key=issuer_public_key,
        expected_issuer=expected_issuer,
        expected_key_id=expected_key_id,
    )


def _manifest_member(*, name: str, format_id: str, content: bytes) -> dict[str, Any]:
    return {
        "format": format_id,
        "length": len(content),
        "name": name,
        "sha256": hashlib.sha256(content).hexdigest(),
    }


def validate_manifest(value: object) -> dict[str, Any]:
    manifest = _exact_dict(
        value,
        {"bundle_profile", "members", "version"},
        "recovery-bundle manifest",
    )
    if (
        manifest["version"] != BUNDLE_MANIFEST_VERSION
        or manifest["bundle_profile"] != BUNDLE_PROFILE
    ):
        raise RecoveryDescriptorError("unsupported recovery-bundle manifest")
    if not isinstance(manifest["members"], list) or len(manifest["members"]) != 2:
        raise RecoveryDescriptorError("invalid recovery-bundle manifest members")
    expected_names = (BACKUP_MEMBER, DESCRIPTOR_MEMBER)
    maximums = (MAX_BACKUP_MEMBER_BYTES, MAX_DESCRIPTOR_BYTES)
    for raw_member, expected_name, maximum in zip(
        manifest["members"], expected_names, maximums, strict=True
    ):
        member = _exact_dict(
            raw_member,
            {"format", "length", "name", "sha256"},
            "recovery-bundle manifest member",
        )
        if member["name"] != expected_name:
            raise RecoveryDescriptorError("noncanonical recovery-bundle manifest order")
        _identifier(member["format"], "bundle member format")
        _integer(member["length"], "bundle member length", minimum=1, maximum=maximum)
        _lower_hex(member["sha256"], "bundle member digest", byte_length=32)
    return manifest


def create_manifest(
    *, backup_bytes: bytes, descriptor_bytes: bytes, backup_format: str
) -> bytes:
    _identifier(backup_format, "backup format")
    if not backup_bytes or len(backup_bytes) > MAX_BACKUP_MEMBER_BYTES:
        raise RecoveryDescriptorError("invalid backup member")
    if not descriptor_bytes or len(descriptor_bytes) > MAX_DESCRIPTOR_BYTES:
        raise RecoveryDescriptorError("invalid descriptor member")
    manifest = {
        "bundle_profile": BUNDLE_PROFILE,
        "members": [
            _manifest_member(
                name=BACKUP_MEMBER,
                format_id=backup_format,
                content=backup_bytes,
            ),
            _manifest_member(
                name=DESCRIPTOR_MEMBER,
                format_id=DESCRIPTOR_VERSION,
                content=descriptor_bytes,
            ),
        ],
        "version": BUNDLE_MANIFEST_VERSION,
    }
    validate_manifest(manifest)
    encoded = encode(manifest)
    if len(encoded) > MAX_MANIFEST_BYTES:
        raise RecoveryDescriptorError("recovery-bundle manifest exceeds size limit")
    return encoded


def decode_manifest(encoded: bytes) -> dict[str, Any]:
    return validate_manifest(
        _decode_canonical_json(
            encoded,
            maximum=MAX_MANIFEST_BYTES,
            label="recovery-bundle manifest",
        )
    )


def _zip_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(filename=name, date_time=ZIP_TIMESTAMP)
    info.compress_type = zipfile.ZIP_STORED
    info.create_system = 3
    info.create_version = 20
    info.extract_version = 20
    info.flag_bits = 0
    info.internal_attr = 0
    info.external_attr = ZIP_EXTERNAL_ATTRIBUTES
    info.extra = b""
    info.comment = b""
    return info


def create_bundle(
    *, backup_bytes: bytes, descriptor_bytes: bytes, backup_format: str
) -> bytes:
    manifest_bytes = create_manifest(
        backup_bytes=backup_bytes,
        descriptor_bytes=descriptor_bytes,
        backup_format=backup_format,
    )
    destination = io.BytesIO()
    with zipfile.ZipFile(destination, "w", allowZip64=False) as archive:
        for name, content in (
            (BACKUP_MEMBER, backup_bytes),
            (DESCRIPTOR_MEMBER, descriptor_bytes),
            (MANIFEST_MEMBER, manifest_bytes),
        ):
            archive.writestr(_zip_info(name), content)
    bundle = destination.getvalue()
    if not bundle or len(bundle) > MAX_BUNDLE_BYTES:
        raise RecoveryDescriptorError("recovery bundle exceeds size limit")
    return bundle


def _validate_zip_envelope(bundle_bytes: bytes) -> None:
    if (
        not isinstance(bundle_bytes, bytes)
        or not bundle_bytes
        or len(bundle_bytes) > MAX_BUNDLE_BYTES
        or not bundle_bytes.startswith(b"PK\x03\x04")
        or len(bundle_bytes) < 22
        or bundle_bytes[-22:-18] != b"PK\x05\x06"
        or bundle_bytes[-2:] != b"\x00\x00"
    ):
        raise RecoveryDescriptorError("invalid recovery-bundle ZIP envelope")


def _read_bundle_members(bundle_bytes: bytes) -> dict[str, bytes]:
    _validate_zip_envelope(bundle_bytes)
    try:
        with zipfile.ZipFile(
            io.BytesIO(bundle_bytes), "r", allowZip64=False
        ) as archive:
            if archive.comment:
                raise RecoveryDescriptorError(
                    "recovery-bundle ZIP comment is forbidden"
                )
            infos = archive.infolist()
            if [info.filename for info in infos] != list(BUNDLE_MEMBERS):
                raise RecoveryDescriptorError("invalid recovery-bundle member set")
            if len({info.filename for info in infos}) != len(BUNDLE_MEMBERS):
                raise RecoveryDescriptorError("duplicate recovery-bundle member")
            total_compressed = 0
            total_uncompressed = 0
            members: dict[str, bytes] = {}
            maximums = {
                BACKUP_MEMBER: MAX_BACKUP_MEMBER_BYTES,
                DESCRIPTOR_MEMBER: MAX_DESCRIPTOR_BYTES,
                MANIFEST_MEMBER: MAX_MANIFEST_BYTES,
            }
            for info in infos:
                if (
                    info.filename not in BUNDLE_MEMBERS
                    or "/" in info.filename
                    or "\\" in info.filename
                    or ":" in info.filename
                    or ".." in info.filename
                    or info.is_dir()
                ):
                    raise RecoveryDescriptorError("unsafe recovery-bundle member")
                if info.flag_bits & 0x1:
                    raise RecoveryDescriptorError("encrypted recovery-bundle member")
                if info.flag_bits != 0:
                    raise RecoveryDescriptorError(
                        "unsupported recovery-bundle ZIP flags"
                    )
                total_compressed += info.compress_size
                total_uncompressed += info.file_size
                if (
                    info.file_size < 1
                    or info.file_size > maximums[info.filename]
                    or total_compressed > MAX_BUNDLE_BYTES
                    or total_uncompressed > MAX_TOTAL_MEMBER_BYTES
                ):
                    raise RecoveryDescriptorError(
                        "recovery-bundle member exceeds size limit"
                    )
                ratio = info.file_size / max(1, info.compress_size)
                if ratio > MAX_COMPRESSION_RATIO:
                    raise RecoveryDescriptorError(
                        "recovery-bundle compression ratio exceeded"
                    )
                if info.compress_type != zipfile.ZIP_STORED:
                    raise RecoveryDescriptorError(
                        "unsupported recovery-bundle compression"
                    )
                if (
                    info.date_time != ZIP_TIMESTAMP
                    or info.create_system != 3
                    or info.create_version != 20
                    or info.extract_version != 20
                    or info.internal_attr != 0
                    or info.external_attr != ZIP_EXTERNAL_ATTRIBUTES
                    or info.extra
                    or info.comment
                ):
                    raise RecoveryDescriptorError(
                        "noncanonical recovery-bundle ZIP metadata"
                    )
                try:
                    content = archive.read(info)
                except (RuntimeError, zipfile.BadZipFile, NotImplementedError) as exc:
                    raise RecoveryDescriptorError(
                        "invalid recovery-bundle member"
                    ) from exc
                if len(content) != info.file_size:
                    raise RecoveryDescriptorError("truncated recovery-bundle member")
                members[info.filename] = content
            return members
    except (zipfile.BadZipFile, zipfile.LargeZipFile, OSError, EOFError) as exc:
        raise RecoveryDescriptorError("invalid recovery-bundle ZIP") from exc


def decode_bundle(
    bundle_bytes: bytes,
    *,
    issuer_public_key: Ed25519PublicKey,
    expected_issuer: str,
    expected_key_id: str,
) -> RecoveryBundle:
    members = _read_bundle_members(bundle_bytes)
    backup_bytes = members[BACKUP_MEMBER]
    descriptor_bytes = members[DESCRIPTOR_MEMBER]
    manifest_bytes = members[MANIFEST_MEMBER]
    descriptor = decode_descriptor(
        descriptor_bytes,
        issuer_public_key=issuer_public_key,
        expected_issuer=expected_issuer,
        expected_key_id=expected_key_id,
    )
    manifest = decode_manifest(manifest_bytes)
    payload = descriptor["payload"]
    backup_binding = payload["backup"]
    backup = _decode_canonical_json(
        backup_bytes,
        maximum=MAX_BACKUP_MEMBER_BYTES,
        label="canonical backup member",
    )
    if (
        backup.get("version") != backup_binding["format"]
        or backup.get("bid") != payload["backup_id"]
        or backup.get("epoch") != payload["epoch"]
    ):
        raise RecoveryDescriptorError("descriptor backup identity mismatch")
    try:
        reference = BackupReference.from_backup(backup)
    except (ObjectCorrupt, ValueError, TypeError) as exc:
        raise RecoveryDescriptorError("invalid canonical backup member") from exc
    if reference.bid != payload["backup_id"] or reference.epoch != payload["epoch"]:
        raise RecoveryDescriptorError("descriptor backup reference mismatch")
    expected_manifest = create_manifest(
        backup_bytes=backup_bytes,
        descriptor_bytes=descriptor_bytes,
        backup_format=backup_binding["format"],
    )
    if manifest_bytes != expected_manifest:
        raise RecoveryDescriptorError("recovery-bundle manifest binding mismatch")
    if (
        backup_binding["length"] != len(backup_bytes)
        or backup_binding["sha256"] != hashlib.sha256(backup_bytes).hexdigest()
    ):
        raise RecoveryDescriptorError("descriptor backup member binding mismatch")
    return RecoveryBundle(
        backup=backup,
        backup_bytes=backup_bytes,
        descriptor=descriptor,
        descriptor_bytes=descriptor_bytes,
        manifest=manifest,
        manifest_bytes=manifest_bytes,
        bundle_bytes=bundle_bytes,
    )


def verify_current_pointer_bundle(
    pointer: dict[str, Any], bundle: RecoveryBundle
) -> None:
    payload = validate_pointer_payload(pointer["payload"])
    descriptor_payload = bundle.descriptor["payload"]
    if (
        payload["subject_id"] != descriptor_payload["subject_id"]
        or payload["backup_id"] != descriptor_payload["backup_id"]
        or payload["epoch"] != descriptor_payload["epoch"]
        or payload["configuration_digest"]
        != descriptor_payload["lifecycle"]["configuration_digest"]
        or payload["descriptor_sha256"]
        != hashlib.sha256(bundle.descriptor_bytes).hexdigest()
        or payload["bundle"]["length"] != len(bundle.bundle_bytes)
        or payload["bundle"]["sha256"] != bundle.bundle_digest
    ):
        raise RecoveryDescriptorError("current-pointer bundle binding mismatch")


__all__ = [
    "BACKUP_MEMBER",
    "BUNDLE_MANIFEST_VERSION",
    "BUNDLE_MEMBERS",
    "BUNDLE_PROFILE",
    "CONFIGURATION_VERSION",
    "CURRENT_POINTER_VERSION",
    "DESCRIPTOR_MEMBER",
    "DESCRIPTOR_VERSION",
    "MANIFEST_MEMBER",
    "MAX_BACKUP_MEMBER_BYTES",
    "MAX_BUNDLE_BYTES",
    "MAX_DESCRIPTOR_BYTES",
    "MAX_MANIFEST_BYTES",
    "MAX_POINTER_BYTES",
    "RecoveryBundle",
    "RecoveryDescriptorError",
    "SIGNATURE_VERSION",
    "configuration_digest",
    "create_bundle",
    "create_current_pointer",
    "create_descriptor",
    "create_manifest",
    "decode_bundle",
    "decode_current_pointer",
    "decode_descriptor",
    "decode_manifest",
    "validate_descriptor_payload",
    "validate_manifest",
    "validate_pointer_payload",
    "verify_current_pointer_bundle",
]
