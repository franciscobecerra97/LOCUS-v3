"""Deterministic local D004 issuer, proof validation, and replay enforcement."""

from __future__ import annotations

import sqlite3
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, cast

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from .admission import (
    ADMISSION_CAPABILITY_FORMAT,
    CLIENT_PROOF_FORMAT,
    LOCAL_ISSUER_PROFILE,
    AdmissionBinding,
    AdmissionContractError,
    client_key_thumbprint,
    decode_canonical_object,
)
from .codec import encode
from .contracts import (
    AdmissionCapability,
    AdmissionGrant,
    GatewayRequest,
    GatewayResult,
)
from .crypto import hash_bytes

SIGNATURE_ALGORITHM = "Ed25519"
MAX_REQUEST_BYTES = 1024 * 1024


class AdmissionVerificationError(ValueError):
    """A capability is invalid; callers should expose only a generic denial."""


class AdmissionReplayConflict(AdmissionVerificationError):
    """A nonce tuple was reused for different work."""


def _lower_hex(value: object, label: str, byte_length: int) -> str:
    if (
        not isinstance(value, str)
        or len(value) != byte_length * 2
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise AdmissionVerificationError(f"invalid {label}")
    return value


def _identifier(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or len(value) > 255
        or not value.isascii()
        or any(ord(character) < 0x21 or ord(character) > 0x7E for character in value)
    ):
        raise AdmissionVerificationError(f"invalid {label}")
    return value


def _exact_dict(value: object, fields: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        raise AdmissionVerificationError(f"invalid {label}")
    return cast(dict[str, Any], value)


def request_digest(request: bytes) -> str:
    if (
        not isinstance(request, bytes)
        or not request
        or len(request) > MAX_REQUEST_BYTES
    ):
        raise AdmissionVerificationError("invalid admitted request")
    return hash_bytes("LOCUS/admission-request/v1", request).hex()


def capability_digest(capability: AdmissionCapability) -> str:
    if capability.format_id != ADMISSION_CAPABILITY_FORMAT:
        raise AdmissionVerificationError("unsupported admission capability")
    return hash_bytes("LOCUS/admission-capability/v1", capability.payload).hex()


def _issuer_message(binding: AdmissionBinding, key_id: str) -> bytes:
    return hash_bytes(
        "LOCUS/admission-capability-signature/v1",
        binding.canonical_bytes,
        key_id.encode("ascii"),
    )


def _client_message(
    capability_hash: str, nonce: str, admitted_request_digest: str
) -> bytes:
    return hash_bytes(
        "LOCUS/admission-client-proof-signature/v1",
        bytes.fromhex(capability_hash),
        bytes.fromhex(nonce),
        bytes.fromhex(admitted_request_digest),
    )


class LocalSyntheticAdmissionIssuer:
    """Project-controlled deterministic test issuer for synthetic subjects."""

    profile_id = LOCAL_ISSUER_PROFILE

    def __init__(
        self,
        *,
        issuer: str,
        key_id: str,
        private_key: Ed25519PrivateKey,
        allowed_subjects: frozenset[str],
    ) -> None:
        self.issuer = _identifier(issuer, "admission issuer")
        self.key_id = _identifier(key_id, "admission issuer key")
        if not isinstance(private_key, Ed25519PrivateKey):
            raise ValueError("invalid admission issuer private key")
        if not allowed_subjects:
            raise ValueError("no synthetic admission subjects")
        for subject in allowed_subjects:
            _lower_hex(subject, "synthetic subject", 32)
        self._private_key = private_key
        self._allowed_subjects = allowed_subjects

    @property
    def public_key(self) -> Ed25519PublicKey:
        return self._private_key.public_key()

    def issue(self, binding: AdmissionBinding) -> AdmissionCapability:
        binding.validate()
        if (
            binding.profile_id != self.profile_id
            or binding.issuer != self.issuer
            or binding.subject not in self._allowed_subjects
        ):
            raise AdmissionVerificationError("synthetic admission denied")
        signature = self._private_key.sign(_issuer_message(binding, self.key_id)).hex()
        payload = encode(
            {
                "binding": binding.to_dict(),
                "format_id": ADMISSION_CAPABILITY_FORMAT,
                "issuer_key_id": self.key_id,
                "signature": signature,
                "signature_algorithm": SIGNATURE_ALGORITHM,
            }
        )
        return AdmissionCapability(
            format_id=ADMISSION_CAPABILITY_FORMAT, payload=payload
        )


def create_client_proof(
    capability: AdmissionCapability,
    private_key: Ed25519PrivateKey,
    request: bytes,
) -> bytes:
    if not isinstance(private_key, Ed25519PrivateKey):
        raise ValueError("invalid admission client private key")
    capability_hash = capability_digest(capability)
    payload = _decode_capability(capability)
    binding = AdmissionBinding.from_dict(payload["binding"])
    public_key = private_key.public_key().public_bytes(
        serialization.Encoding.Raw,
        serialization.PublicFormat.Raw,
    )
    if client_key_thumbprint(public_key) != binding.client_key_thumbprint:
        raise AdmissionVerificationError("client proof key does not match capability")
    admitted_request_digest = request_digest(request)
    signature = private_key.sign(
        _client_message(capability_hash, binding.nonce, admitted_request_digest)
    ).hex()
    return encode(
        {
            "capability_digest": capability_hash,
            "client_public_key": public_key.hex(),
            "format_id": CLIENT_PROOF_FORMAT,
            "nonce": binding.nonce,
            "request_digest": admitted_request_digest,
            "signature": signature,
            "signature_algorithm": SIGNATURE_ALGORITHM,
        }
    )


def _decode_capability(capability: AdmissionCapability) -> dict[str, Any]:
    if capability.format_id != ADMISSION_CAPABILITY_FORMAT:
        raise AdmissionVerificationError("unsupported admission capability")
    try:
        payload = decode_canonical_object(capability.payload, "admission capability")
    except AdmissionContractError as exc:
        raise AdmissionVerificationError("invalid admission capability") from exc
    parsed = _exact_dict(
        payload,
        {
            "binding",
            "format_id",
            "issuer_key_id",
            "signature",
            "signature_algorithm",
        },
        "admission capability",
    )
    if (
        parsed["format_id"] != ADMISSION_CAPABILITY_FORMAT
        or parsed["signature_algorithm"] != SIGNATURE_ALGORITHM
    ):
        raise AdmissionVerificationError("unsupported admission capability")
    _identifier(parsed["issuer_key_id"], "admission issuer key")
    _lower_hex(parsed["signature"], "admission issuer signature", 64)
    return parsed


class AdmissionReplayStore:
    """Durable privacy-minimized exact-use state for one independent verifier."""

    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        self._lock = threading.RLock()
        self._connection = sqlite3.connect(
            self.path, isolation_level=None, check_same_thread=False
        )
        self._connection.execute("PRAGMA journal_mode = WAL")
        self._connection.execute("PRAGMA synchronous = FULL")
        self._connection.execute(
            """CREATE TABLE IF NOT EXISTS admission_replay (
                   replay_key TEXT PRIMARY KEY,
                   binding_digest TEXT NOT NULL,
                   request_digest TEXT NOT NULL,
                   grant_digest TEXT NOT NULL
               )"""
        )

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def reserve(
        self,
        *,
        replay_key: str,
        binding_digest: str,
        admitted_request_digest: str,
        grant_digest: str,
    ) -> None:
        for value, label in (
            (replay_key, "admission replay key"),
            (binding_digest, "admission binding digest"),
            (admitted_request_digest, "admitted request digest"),
            (grant_digest, "admission grant digest"),
        ):
            _lower_hex(value, label, 32)
        with self._lock:
            self._connection.execute("BEGIN IMMEDIATE")
            try:
                row = self._connection.execute(
                    "SELECT * FROM admission_replay WHERE replay_key = ?",
                    (replay_key,),
                ).fetchone()
                expected = (binding_digest, admitted_request_digest, grant_digest)
                if row is None:
                    self._connection.execute(
                        "INSERT INTO admission_replay VALUES (?, ?, ?, ?)",
                        (replay_key, *expected),
                    )
                elif tuple(row[1:]) != expected:
                    raise AdmissionReplayConflict("admission nonce reuse")
                self._connection.execute("COMMIT")
            except BaseException:
                self._connection.execute("ROLLBACK")
                raise

    def record_count(self) -> int:
        with self._lock:
            row = self._connection.execute(
                "SELECT COUNT(*) FROM admission_replay"
            ).fetchone()
        return int(row[0]) if row is not None else 0


class LocalAdmissionVerifier:
    """Independent issuer, proof-key, scope, time, and replay validator."""

    profile_id = LOCAL_ISSUER_PROFILE

    def __init__(
        self,
        *,
        issuer: str,
        issuer_key_id: str,
        issuer_public_key: Ed25519PublicKey,
        replay_store: AdmissionReplayStore,
    ) -> None:
        self.issuer = _identifier(issuer, "admission issuer")
        self.issuer_key_id = _identifier(issuer_key_id, "admission issuer key")
        if not isinstance(issuer_public_key, Ed25519PublicKey):
            raise ValueError("invalid admission issuer public key")
        self._issuer_public_key = issuer_public_key
        self._replay_store = replay_store

    def verify(
        self,
        capability: AdmissionCapability,
        expected: AdmissionBinding,
        client_proof: bytes,
        request: bytes,
        *,
        now: int,
    ) -> AdmissionGrant:
        try:
            expected.validate()
            if isinstance(now, bool) or not isinstance(now, int):
                raise AdmissionVerificationError("invalid verifier time")
            payload = _decode_capability(capability)
            binding = AdmissionBinding.from_dict(payload["binding"])
            if (
                binding != expected
                or binding.issuer != self.issuer
                or binding.profile_id != self.profile_id
                or payload["issuer_key_id"] != self.issuer_key_id
                or not binding.issued_at <= now < binding.expires_at
            ):
                raise AdmissionVerificationError("admission binding rejected")
            self._issuer_public_key.verify(
                bytes.fromhex(payload["signature"]),
                _issuer_message(binding, self.issuer_key_id),
            )
            proof = _exact_dict(
                decode_canonical_object(client_proof, "admission client proof"),
                {
                    "capability_digest",
                    "client_public_key",
                    "format_id",
                    "nonce",
                    "request_digest",
                    "signature",
                    "signature_algorithm",
                },
                "admission client proof",
            )
            if (
                proof["format_id"] != CLIENT_PROOF_FORMAT
                or proof["signature_algorithm"] != SIGNATURE_ALGORITHM
            ):
                raise AdmissionVerificationError("unsupported client proof")
            capability_hash = capability_digest(capability)
            admitted_request_digest = request_digest(request)
            if (
                proof["capability_digest"] != capability_hash
                or proof["request_digest"] != admitted_request_digest
                or proof["nonce"] != binding.nonce
            ):
                raise AdmissionVerificationError("client proof binding mismatch")
            public_key_bytes = bytes.fromhex(
                _lower_hex(proof["client_public_key"], "client public key", 32)
            )
            _lower_hex(proof["signature"], "client proof signature", 64)
            if client_key_thumbprint(public_key_bytes) != binding.client_key_thumbprint:
                raise AdmissionVerificationError("client proof key mismatch")
            Ed25519PublicKey.from_public_bytes(public_key_bytes).verify(
                bytes.fromhex(proof["signature"]),
                _client_message(
                    capability_hash, binding.nonce, admitted_request_digest
                ),
            )
            grant_digest = hash_bytes(
                "LOCUS/admission-grant/v1",
                bytes.fromhex(binding.digest),
                bytes.fromhex(capability_hash),
                bytes.fromhex(admitted_request_digest),
            ).hex()
            replay_key = hash_bytes(
                "LOCUS/admission-replay-key/v1",
                binding.issuer.encode("ascii"),
                bytes.fromhex(binding.subject),
                bytes.fromhex(binding.nonce),
                binding.audience.encode("ascii"),
            ).hex()
            self._replay_store.reserve(
                replay_key=replay_key,
                binding_digest=binding.digest,
                admitted_request_digest=admitted_request_digest,
                grant_digest=grant_digest,
            )
            return AdmissionGrant(binding=binding, grant_digest=grant_digest)
        except (
            AdmissionContractError,
            InvalidSignature,
            TypeError,
            ValueError,
        ) as exc:
            if isinstance(exc, AdmissionVerificationError):
                raise
            raise AdmissionVerificationError("admission denied") from exc


class StorageGatewayBackend(Protocol):
    def execute(self, request: GatewayRequest) -> GatewayResult: ...


_STORAGE_OPERATION_NAMES = {
    "compare_and_swap": "storage_compare_and_swap",
    "create_immutable": "storage_create_immutable",
    "delete_exact": "storage_delete_exact",
    "read_exact": "storage_read_exact",
}


def gateway_request_bytes(request: GatewayRequest) -> bytes:
    return encode(
        {
            "backup_reference": request.backup_reference.to_dict(),
            "object_key": request.object_key,
            "operation": request.operation.value,
            "payload_digest": (
                None
                if request.payload is None
                else hash_bytes(
                    "LOCUS/storage-request-payload/v1", request.payload
                ).hex()
            ),
        }
    )


@dataclass
class LocalAdmissionStorageGateway:
    """Validate exact storage authority locally before calling its backend."""

    verifier: LocalAdmissionVerifier
    backend: StorageGatewayBackend
    audience: str

    def execute(
        self,
        request: GatewayRequest,
        capability: AdmissionCapability,
        expected: AdmissionBinding,
        client_proof: bytes,
        *,
        now: int,
    ) -> GatewayResult:
        operation = _STORAGE_OPERATION_NAMES.get(request.operation.value)
        if (
            operation is None
            or expected.operation != operation
            or expected.audience != self.audience
            or expected.backup_id != request.backup_reference.bid
            or expected.epoch != request.backup_reference.epoch
            or expected.object_prefix is None
            or not request.object_key.startswith(expected.object_prefix)
            or any(part in {"", ".", ".."} for part in request.object_key.split("/"))
        ):
            raise AdmissionVerificationError("storage admission denied")
        self.verifier.verify(
            capability,
            expected,
            client_proof,
            gateway_request_bytes(request),
            now=now,
        )
        return self.backend.execute(request)


__all__ = [
    "AdmissionReplayConflict",
    "AdmissionReplayStore",
    "AdmissionVerificationError",
    "LocalAdmissionStorageGateway",
    "LocalAdmissionVerifier",
    "LocalSyntheticAdmissionIssuer",
    "capability_digest",
    "create_client_proof",
    "gateway_request_bytes",
    "request_digest",
]
