"""Authenticated service entry points for the P7.5 integrated system."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from . import _tpass_native as native
from .admission import AdmissionBinding
from .appss_formats import canonical_decode, validate_request
from .appss_party import AppssPartyBinding, AppssPartyService, AppssPartyStore
from .codec import encode
from .contracts import AdmissionCapability, GatewayRequest, StorageOperation
from .integrated_rpc import serve_rpc
from .local_admission import (
    AdmissionReplayStore,
    LocalAdmissionStorageGateway,
    LocalAdmissionVerifier,
    LocalSyntheticAdmissionIssuer,
)
from .object_store import (
    BackupReference,
    ObjectConflict,
    ObjectCorrupt,
    ObjectNotFound,
    ObjectStale,
    ObjectStoreUnavailable,
)
from .provider_gateway import VersionedProviderStorageGatewayBackend
from .recovery_bootstrap import (
    create_party_current_summary,
    create_recovery_receipt,
)
from .recovery_descriptor import create_current_pointer, create_descriptor
from .storage_provider import S3CompatibleStorageProvider
from .yi_compat import YiTpassRecoveryAdapter

ADMISSION_ISSUER = "locus-integrated-admission"
ADMISSION_KEY_ID = "locus-integrated-admission-1"
OPERATOR_ISSUER = "locus-integrated-operator"
OPERATOR_KEY_ID = "locus-integrated-operator-1"
STORAGE_AUDIENCE = "locus-integrated-storage-gateway"


class IntegratedServiceError(ValueError):
    """An internal service request failed closed."""


def _private(path: Path) -> Ed25519PrivateKey:
    value = path.read_bytes()
    if len(value) != 32:
        raise IntegratedServiceError("invalid signing key")
    return Ed25519PrivateKey.from_private_bytes(value)


def _hex(value: object, label: str, maximum: int) -> bytes:
    if (
        not isinstance(value, str)
        or not value
        or len(value) > maximum * 2
        or len(value) % 2
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise IntegratedServiceError(f"invalid {label}")
    return bytes.fromhex(value)


def _clients_only(peer: str) -> None:
    if peer not in {"managed-client", "ui-client-a", "ui-client-b"}:
        raise IntegratedServiceError("caller is not a client gateway")


class AdmissionRole:
    def __init__(self, root: Path) -> None:
        self.issuer = LocalSyntheticAdmissionIssuer(
            issuer=ADMISSION_ISSUER,
            key_id=ADMISSION_KEY_ID,
            private_key=_private(root / "signing-key.bin"),
            allowed_subjects=frozenset({"11" * 32}),
        )

    def __call__(
        self, path: str, request: dict[str, Any], peer: str
    ) -> tuple[int, dict[str, Any]]:
        if path == "/health":
            return 200, {"role": "admission", "status": "ready"}
        _clients_only(peer)
        if path != "/v1/issue" or set(request) != {"binding"}:
            raise IntegratedServiceError("unsupported admission request")
        capability = self.issuer.issue(AdmissionBinding.from_dict(request["binding"]))
        return 200, {
            "capability_hex": capability.payload.hex(),
            "format_id": capability.format_id,
            "status": "issued",
        }


class OperatorRole:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.signer = _private(root / "signing-key.bin")
        self.database = sqlite3.connect(
            root / "operator.sqlite3", check_same_thread=False, isolation_level=None
        )
        self.database.execute("PRAGMA journal_mode=WAL")
        self.database.execute(
            "CREATE TABLE IF NOT EXISTS discovery (handle TEXT PRIMARY KEY, record BLOB NOT NULL)"
        )
        self.lock = threading.RLock()

    def __call__(
        self, path: str, request: dict[str, Any], peer: str
    ) -> tuple[int, dict[str, Any]]:
        if path == "/health":
            return 200, {"role": "operator", "status": "ready"}
        _clients_only(peer)
        if (
            path == "/v1/sign"
            and set(request) == {"kind", "payload"}
            and isinstance(request["payload"], dict)
        ):
            kind = request["kind"]
            if kind == "descriptor":
                encoded = create_descriptor(
                    request["payload"], signer=self.signer, key_id=OPERATOR_KEY_ID
                )
            elif kind == "pointer":
                encoded = create_current_pointer(
                    request["payload"], signer=self.signer, key_id=OPERATOR_KEY_ID
                )
            elif kind == "receipt":
                encoded = create_recovery_receipt(
                    request["payload"], signer=self.signer, key_id=OPERATOR_KEY_ID
                )
            else:
                raise IntegratedServiceError("unsupported signing object")
            return 200, {
                "object_hex": encoded.hex(),
                "sha256": hashlib.sha256(encoded).hexdigest(),
                "status": "signed",
            }
        if path == "/v1/discovery/publish" and set(request) == {"record"}:
            record = request["record"]
            required = {
                "backup_id",
                "backup_digest",
                "epoch",
                "public_fingerprint",
                "recovery_handle",
                "subject_id",
            }
            if not isinstance(record, dict) or set(record) != required:
                raise IntegratedServiceError("invalid discovery record")
            handle = str(record["recovery_handle"])
            encoded = encode(record)
            with self.lock:
                existing = self.database.execute(
                    "SELECT record FROM discovery WHERE handle=?", (handle,)
                ).fetchone()
                if existing is None:
                    self.database.execute(
                        "INSERT INTO discovery VALUES (?,?)", (handle, encoded)
                    )
                else:
                    prior = json.loads(bytes(existing[0]))
                    if int(record["epoch"]) <= int(prior["epoch"]):
                        if bytes(existing[0]) != encoded:
                            raise IntegratedServiceError("stale discovery publication")
                    else:
                        self.database.execute(
                            "UPDATE discovery SET record=? WHERE handle=?",
                            (encoded, handle),
                        )
            return 200, {"status": "published"}
        if path == "/v1/discovery/read" and set(request) == {"recovery_handle"}:
            with self.lock:
                row = self.database.execute(
                    "SELECT record FROM discovery WHERE handle=?",
                    (request["recovery_handle"],),
                ).fetchone()
            if row is None:
                raise IntegratedServiceError("discovery record not found")
            return 200, {"record": json.loads(bytes(row[0])), "status": "found"}
        raise IntegratedServiceError("unsupported operator request")


class ResolverRole:
    def __init__(self) -> None:
        self.contacts = 0
        self.lock = threading.Lock()

    def __call__(
        self, path: str, request: dict[str, Any], peer: str
    ) -> tuple[int, dict[str, Any]]:
        if path == "/health":
            return 200, {"role": "resolver", "status": "ready"}
        _clients_only(peer)
        if path == "/v1/count" and not request:
            return 200, {"contacts": self.contacts, "status": "ok"}
        if path != "/v1/resolve" or set(request) != {"policy_id", "values"}:
            raise IntegratedServiceError("unsupported resolver request")
        if request["policy_id"] != "LOCUS-location-person-set-v1":
            raise IntegratedServiceError("policy must use NoResolver")
        from .cue_policy_registry import DEFAULT_CUE_POLICY_REGISTRY

        policy = DEFAULT_CUE_POLICY_REGISTRY.require(str(request["policy_id"]))
        result = policy.process(request["values"])
        with self.lock:
            self.contacts += 1
        return 200, {
            "canonical_hex": result.canonical_bytes.hex(),
            "status": "resolved",
        }


class StorageGatewayRole:
    def __init__(
        self,
        root: Path,
        *,
        s3_endpoint: str,
        bucket: str,
        access_key: str,
        secret_key: str,
    ) -> None:
        trust = json.loads((root / "trust.json").read_bytes())
        issuer_public = bytes.fromhex(trust["admission_issuer_public_key"])
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

        self.verifier = LocalAdmissionVerifier(
            issuer=ADMISSION_ISSUER,
            issuer_key_id=ADMISSION_KEY_ID,
            issuer_public_key=Ed25519PublicKey.from_public_bytes(issuer_public),
            replay_store=AdmissionReplayStore(root / "admission-replay.sqlite3"),
        )
        self.provider = S3CompatibleStorageProvider.from_credentials(
            bucket=bucket,
            access_key=access_key,
            secret_key=secret_key,
            endpoint_url=s3_endpoint,
            allow_http=True,
            provider_prefix="locus/integrated",
        )

    def __call__(
        self, path: str, request: dict[str, Any], peer: str
    ) -> tuple[int, dict[str, Any]]:
        if path == "/health":
            return 200, {"role": "storage-gateway", "status": "ready"}
        _clients_only(peer)
        if path != "/v1/execute" or set(request) != {
            "binding",
            "capability",
            "client_proof",
            "gateway_request",
            "now",
            "recovery_handle",
        }:
            raise IntegratedServiceError("unsupported storage request")
        raw = request["gateway_request"]
        if not isinstance(raw, dict) or set(raw) != {
            "backup_reference",
            "object_key",
            "operation",
            "payload_hex",
        }:
            raise IntegratedServiceError("invalid gateway request")
        payload = (
            None
            if raw["payload_hex"] is None
            else _hex(raw["payload_hex"], "gateway payload", 2 * 1024 * 1024)
        )
        gateway_request = GatewayRequest(
            operation=StorageOperation(str(raw["operation"])),
            object_key=str(raw["object_key"]),
            backup_reference=BackupReference.from_dict(raw["backup_reference"]),
            payload=payload,
        )
        binding = AdmissionBinding.from_dict(request["binding"])
        capability = AdmissionCapability(
            format_id=str(request["capability"]["format_id"]),
            payload=_hex(request["capability"]["payload_hex"], "capability", 64 * 1024),
        )
        backend = VersionedProviderStorageGatewayBackend(
            provider=self.provider,
            subject_id=binding.subject,
            recovery_handle=str(request["recovery_handle"]),
        )
        gateway = LocalAdmissionStorageGateway(
            verifier=self.verifier, backend=backend, audience=STORAGE_AUDIENCE
        )
        try:
            result = gateway.execute(
                gateway_request,
                capability,
                binding,
                _hex(request["client_proof"], "client proof", 64 * 1024),
                now=int(request["now"]),
            )
        except ObjectNotFound:
            return 404, {"category": "object_not_found", "status": "error"}
        except ObjectConflict:
            return 409, {"category": "object_conflict", "status": "error"}
        except ObjectStale:
            return 409, {"category": "object_stale", "status": "error"}
        except ObjectCorrupt:
            return 400, {"category": "object_rejected", "status": "error"}
        except ObjectStoreUnavailable:
            return 503, {"category": "provider_unavailable", "status": "error"}
        return 200, {
            "payload_hex": None if result.payload is None else result.payload.hex(),
            "reference": result.reference.to_dict(),
            "status": "completed",
        }


class PartyRole:
    def __init__(self, root: Path, holder_id: int) -> None:
        self.root = root
        self.holder_id = holder_id
        self.signer = _private(root / "signing-key.bin")
        trust = json.loads((root / "trust.json").read_bytes())
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

        self.admission_verifier = LocalAdmissionVerifier(
            issuer=ADMISSION_ISSUER,
            issuer_key_id=ADMISSION_KEY_ID,
            issuer_public_key=Ed25519PublicKey.from_public_bytes(
                bytes.fromhex(trust["admission_issuer_public_key"])
            ),
            replay_store=AdmissionReplayStore(root / "admission-replay.sqlite3"),
        )
        self.database = sqlite3.connect(
            root / "party.sqlite3", check_same_thread=False, isolation_level=None
        )
        self.database.execute("PRAGMA journal_mode=WAL")
        self.database.execute(
            "CREATE TABLE IF NOT EXISTS yi_epochs (backup_id TEXT, epoch INTEGER, context BLOB, public_state BLOB, party_state BLOB, PRIMARY KEY(backup_id,epoch))"
        )
        self.database.execute(
            "CREATE TABLE IF NOT EXISTS current_epochs (backup_id TEXT, epoch INTEGER, summary_payload BLOB, PRIMARY KEY(backup_id,epoch))"
        )
        self.database.execute(
            "CREATE TABLE IF NOT EXISTS authorizations (grant_digest TEXT PRIMARY KEY, backup_id TEXT, epoch INTEGER, operation_id TEXT)"
        )
        self.lock = threading.RLock()
        self.ephemeral: dict[str, tuple[Any, Any, Any, list[int]]] = {}

    def _appss_service(
        self, context_digest: bytes, profile_id: str
    ) -> AppssPartyService:
        binding = AppssPartyBinding(
            holder_id=self.holder_id,
            context_digest=context_digest,
            profile_id=profile_id,
        )
        path = self.root / "appss" / f"{context_digest.hex()}.sqlite3"
        return AppssPartyService(AppssPartyStore(path, binding))

    def __call__(
        self, path: str, request: dict[str, Any], peer: str
    ) -> tuple[int, dict[str, Any]]:
        if path == "/health":
            return 200, {
                "holder_id": self.holder_id,
                "role": "party",
                "status": "ready",
            }
        _clients_only(peer)
        if path == "/v1/authorize" and set(request) == {
            "admitted_request_hex",
            "binding",
            "capability",
            "client_proof",
            "now",
        }:
            admitted = _hex(
                request["admitted_request_hex"], "admitted request", 64 * 1024
            )
            binding = AdmissionBinding.from_dict(request["binding"])
            if (
                binding.operation != "recovery_attempt"
                or binding.audience != "locus-integrated-recovery"
            ):
                raise IntegratedServiceError("invalid recovery authorization")
            capability = AdmissionCapability(
                format_id=str(request["capability"]["format_id"]),
                payload=_hex(
                    request["capability"]["payload_hex"], "capability", 64 * 1024
                ),
            )
            grant = self.admission_verifier.verify(
                capability,
                binding,
                _hex(request["client_proof"], "client proof", 64 * 1024),
                admitted,
                now=int(request["now"]),
            )
            admitted_value = json.loads(admitted)
            if not isinstance(admitted_value, dict) or set(admitted_value) != {
                "backup_id",
                "epoch",
                "operation_id",
                "recovery_handle",
            }:
                raise IntegratedServiceError("invalid admitted recovery request")
            current = self.database.execute(
                "SELECT summary_payload FROM current_epochs WHERE backup_id=? AND epoch=?",
                (admitted_value["backup_id"], admitted_value["epoch"]),
            ).fetchone()
            if (
                current is None
                or json.loads(bytes(current[0])).get("state") != "active"
            ):
                raise IntegratedServiceError("recovery epoch is not active")
            self.database.execute(
                "INSERT OR REPLACE INTO authorizations VALUES (?,?,?,?)",
                (
                    grant.grant_digest,
                    admitted_value["backup_id"],
                    admitted_value["epoch"],
                    admitted_value["operation_id"],
                ),
            )
            return 200, {
                "grant_digest": grant.grant_digest,
                "holder_id": self.holder_id,
                "status": "authorized",
            }
        if path == "/v1/yi/enroll" and set(request) == {
            "backup_id",
            "context",
            "epoch",
            "party_state_hex",
            "public_state_hex",
        }:
            state = _hex(request["party_state_hex"], "Yi state", 1024 * 1024)
            public = _hex(request["public_state_hex"], "Yi public state", 1024 * 1024)
            adapter = YiTpassRecoveryAdapter()
            from .contracts import PartyRecoveryState, PublicRecoveryState

            adapter.decode_public_state(
                PublicRecoveryState(
                    adapter.suite_id, adapter.public_state_format, public
                )
            )
            adapter.decode_party_state(
                PartyRecoveryState(
                    adapter.suite_id, adapter.party_state_format, self.holder_id, state
                )
            )
            context = encode(request["context"])
            values = (
                str(request["backup_id"]),
                int(request["epoch"]),
                context,
                public,
                state,
            )
            with self.lock:
                prior = self.database.execute(
                    "SELECT context,public_state,party_state FROM yi_epochs WHERE backup_id=? AND epoch=?",
                    values[:2],
                ).fetchone()
                if prior is None:
                    self.database.execute(
                        "INSERT INTO yi_epochs VALUES (?,?,?,?,?)", values
                    )
                elif tuple(bytes(item) for item in prior) != values[2:]:
                    raise IntegratedServiceError("Yi enrollment retry changed state")
            return 200, {
                "holder_id": self.holder_id,
                "state_digest": hashlib.sha256(state).hexdigest(),
                "status": "ready",
            }
        if path == "/v1/yi/prepare" and set(request) == {
            "backup_id",
            "epoch",
            "grant_digest",
            "request_hex",
            "selected",
            "session_id",
        }:
            authorized = self.database.execute(
                "SELECT 1 FROM authorizations WHERE grant_digest=? AND backup_id=? AND epoch=?",
                (request["grant_digest"], request["backup_id"], request["epoch"]),
            ).fetchone()
            if authorized is None:
                raise IntegratedServiceError("Yi recovery is not authorized")
            row = self.database.execute(
                "SELECT public_state,party_state FROM yi_epochs WHERE backup_id=? AND epoch=?",
                (request["backup_id"], request["epoch"]),
            ).fetchone()
            if row is None:
                raise IntegratedServiceError("Yi epoch unavailable")
            adapter = YiTpassRecoveryAdapter()
            params = native.PublicParameters.from_bytes(
                bytes.fromhex(json.loads(bytes(row[0]))["parameters"])
            )
            native_state = native.PartyState.from_secret_bytes(
                bytes.fromhex(json.loads(bytes(row[1]))["state"])
            )
            selected = [int(item) for item in request["selected"]]
            request_bytes = _hex(request["request_hex"], "Yi request", 256 * 1024)
            commitment, ephemeral = native.prepare_commitment(
                params, request_bytes, selected, native_state
            )
            with self.lock:
                self.ephemeral[str(request["session_id"])] = (
                    params,
                    native_state,
                    ephemeral,
                    selected,
                )
            return 200, {
                "commitment_hex": bytes(commitment).hex(),
                "holder_id": self.holder_id,
                "status": "prepared",
            }
        if path == "/v1/yi/respond" and set(request) == {
            "commitments",
            "request_hex",
            "session_id",
        }:
            session_id = str(request["session_id"])
            with self.lock:
                stored = self.ephemeral.pop(session_id, None)
            if stored is None:
                raise IntegratedServiceError("Yi session unavailable")
            params, state, ephemeral, selected = stored
            response = native.verify_and_respond(
                params,
                _hex(request["request_hex"], "Yi request", 256 * 1024),
                selected,
                state,
                ephemeral,
                [
                    _hex(item, "Yi commitment", 256 * 1024)
                    for item in request["commitments"]
                ],
            )
            return 200, {
                "holder_id": self.holder_id,
                "response_hex": bytes(response).hex(),
                "status": "responded",
            }
        if path in {"/v1/appss/initialize", "/v1/appss/evaluate"} and set(request) == {
            "request_hex"
        }:
            request_bytes = _hex(request["request_hex"], "aPPSS request", 256 * 1024)
            decoded = canonical_decode(
                request_bytes,
                maximum=256 * 1024,
                validator=validate_request,
                label="aPPSS request",
            )
            if decoded["holder_id"] != self.holder_id:
                raise IntegratedServiceError("aPPSS recipient mismatch")
            if (
                decoded["operation"] == "recover"
                and self.database.execute(
                    "SELECT 1 FROM authorizations WHERE grant_digest=?",
                    (decoded["admission_grant_digest"],),
                ).fetchone()
                is None
            ):
                raise IntegratedServiceError("aPPSS recovery is not authorized")
            response = self._appss_service(
                bytes.fromhex(decoded["context_digest"]), decoded["profile_id"]
            ).evaluate(request_bytes)
            return 200, {"response_hex": response.hex(), "status": "responded"}
        if path == "/v1/appss/install" and set(request) == {
            "context_digest",
            "install_hex",
            "profile_id",
        }:
            service = self._appss_service(
                _hex(request["context_digest"], "aPPSS context", 32),
                str(request["profile_id"]),
            )
            ready = service.install(
                _hex(request["install_hex"], "aPPSS install", 1024 * 1024)
            )
            return 200, {"ready_hex": ready.hex(), "status": "ready"}
        if path == "/v1/current/install" and set(request) == {"payload"}:
            payload = request["payload"]
            if (
                not isinstance(payload, dict)
                or payload.get("authorizer_id") != self.holder_id
            ):
                raise IntegratedServiceError("party-current recipient mismatch")
            summary = create_party_current_summary(
                payload, signer=self.signer, key_id=f"party-{self.holder_id}-current-1"
            )
            current_values = (
                str(payload["backup_id"]),
                int(payload["epoch"]),
                encode(payload),
            )
            with self.lock:
                prior = self.database.execute(
                    "SELECT summary_payload FROM current_epochs WHERE backup_id=? AND epoch=?",
                    current_values[:2],
                ).fetchone()
                if prior is None:
                    self.database.execute(
                        "INSERT INTO current_epochs VALUES (?,?,?)", current_values
                    )
                elif bytes(prior[0]) != current_values[2]:
                    raise IntegratedServiceError("party-current retry changed state")
            return 200, {"summary_hex": summary.hex(), "status": "active"}
        if path == "/v1/current/retire" and set(request) == {
            "backup_id",
            "predecessor_epoch",
            "successor_epoch",
        }:
            backup_id = str(request["backup_id"])
            predecessor_epoch = int(request["predecessor_epoch"])
            successor_epoch = int(request["successor_epoch"])
            if successor_epoch != predecessor_epoch + 1:
                raise IntegratedServiceError("invalid retirement epochs")
            with self.lock:
                predecessor_row = self.database.execute(
                    "SELECT summary_payload FROM current_epochs WHERE backup_id=? AND epoch=?",
                    (backup_id, predecessor_epoch),
                ).fetchone()
                successor_row = self.database.execute(
                    "SELECT summary_payload FROM current_epochs WHERE backup_id=? AND epoch=?",
                    (backup_id, successor_epoch),
                ).fetchone()
                if predecessor_row is None or successor_row is None:
                    raise IntegratedServiceError("retirement epoch unavailable")
                predecessor = json.loads(bytes(predecessor_row[0]))
                successor = json.loads(bytes(successor_row[0]))
                if successor.get("state") != "active":
                    raise IntegratedServiceError("successor epoch is not active")
                if predecessor.get("state") == "active":
                    predecessor["state"] = "retired"
                    self.database.execute(
                        "UPDATE current_epochs SET summary_payload=? WHERE backup_id=? AND epoch=?",
                        (encode(predecessor), backup_id, predecessor_epoch),
                    )
                elif predecessor.get("state") != "retired":
                    raise IntegratedServiceError("invalid predecessor state")
            return 200, {"status": "retired"}
        if path == "/v1/current/read" and set(request) == {"backup_id", "epoch"}:
            row = self.database.execute(
                "SELECT summary_payload FROM current_epochs WHERE backup_id=? AND epoch=?",
                (request["backup_id"], request["epoch"]),
            ).fetchone()
            if row is None:
                raise IntegratedServiceError("party current state unavailable")
            payload = json.loads(bytes(row[0]))
            if payload.get("state") != "active":
                raise IntegratedServiceError("party current state is not active")
            now = int(time.time())
            payload["issued_at"] = now
            payload["expires_at"] = now + 120
            summary = create_party_current_summary(
                payload, signer=self.signer, key_id=f"party-{self.holder_id}-current-1"
            )
            return 200, {"summary_hex": summary.hex(), "status": "active"}
        if path == "/v1/inspect" and not request:
            yi = int(
                self.database.execute("SELECT COUNT(*) FROM yi_epochs").fetchone()[0]
            )
            current_rows = self.database.execute(
                "SELECT summary_payload FROM current_epochs"
            ).fetchall()
            current = sum(
                json.loads(bytes(row[0])).get("state") == "active"
                for row in current_rows
            )
            retired = sum(
                json.loads(bytes(row[0])).get("state") == "retired"
                for row in current_rows
            )
            return 200, {
                "active_epochs": current,
                "holder_id": self.holder_id,
                "retired_epochs": retired,
                "yi_epochs": yi,
                "status": "ok",
            }
        raise IntegratedServiceError("unsupported party request")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run one P7.5 service role")
    parser.add_argument(
        "role",
        choices=("admission", "operator", "resolver", "storage-gateway", "party"),
    )
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8443)
    parser.add_argument("--holder-id", type=int)
    parser.add_argument(
        "--s3-endpoint", default=os.environ.get("LOCUS_S3_ENDPOINT", "http://s3:8333")
    )
    parser.add_argument("--s3-bucket", default=os.environ.get("LOCUS_S3_BUCKET"))
    parser.add_argument(
        "--s3-access-key", default=os.environ.get("LOCUS_S3_ACCESS_KEY")
    )
    parser.add_argument(
        "--s3-secret-key", default=os.environ.get("LOCUS_S3_SECRET_KEY")
    )
    args = parser.parse_args()
    handler: Any
    if args.role == "admission":
        handler = AdmissionRole(args.root)
    elif args.role == "operator":
        handler = OperatorRole(args.root)
    elif args.role == "resolver":
        handler = ResolverRole()
    elif args.role == "storage-gateway":
        if not args.s3_bucket or not args.s3_access_key or not args.s3_secret_key:
            raise SystemExit("storage gateway requires explicit S3 configuration")
        handler = StorageGatewayRole(
            args.root,
            s3_endpoint=args.s3_endpoint,
            bucket=args.s3_bucket,
            access_key=args.s3_access_key,
            secret_key=args.s3_secret_key,
        )
    else:
        if args.holder_id not in range(1, 6):
            raise SystemExit("party requires --holder-id 1..5")
        handler = PartyRole(args.root, args.holder_id)
    serve_rpc(host=args.host, port=args.port, role_root=args.root, handler=handler)


if __name__ == "__main__":
    main()
