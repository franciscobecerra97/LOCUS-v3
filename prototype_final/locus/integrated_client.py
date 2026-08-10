"""Deployment-backed realization of the frozen LOCUS client API v1."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from . import _tpass_native as native
from .admission import (
    RECOVERY_OPERATION,
    AdmissionBinding,
    client_key_thumbprint,
    pseudonymous_object_prefix,
)
from .appss_client import (
    AppssPartyEndpoint,
    initialize_with_parties,
    recover_with_parties,
)
from .appss_formats import (
    APPSS_SUITE_ID,
    YI_SUITE_ID,
    AppssHolderBinding,
    context_digest,
    derive_password_input,
)
from .client_api import (
    CLIENT_API_VERSION,
    BootstrapResult,
    ClientApiError,
    EnrollmentResult,
    LocalResearchClientApi,
    RecoveryResult,
    SuccessorResult,
)
from .codec import encode
from .contracts import PublicRecoveryState, RecoveryContext, ThresholdParameters
from .crypto import hash_scalar, random_bytes
from .cue_policy_registry import DEFAULT_CUE_POLICY_REGISTRY
from .integrated_rpc import IntegratedRpcError, rpc_request
from .integrated_services import (
    ADMISSION_ISSUER,
    OPERATOR_ISSUER,
    OPERATOR_KEY_ID,
    STORAGE_AUDIENCE,
)
from .local_admission import create_client_proof, gateway_request_bytes
from .object_store import BackupReference
from .paired_deployment_profiles import paired_profile
from .provider_gateway import (
    backup_object_key,
    bundle_object_key,
    current_pointer_object_key,
    descriptor_object_key,
    encode_pointer_cas,
)
from .recovery_bootstrap import (
    BOOTSTRAP_PROFILE,
    TRUST_CONFIGURATION_VERSION,
    PartyCurrentObservation,
    authenticate_recovery_bootstrap,
    decode_recovery_receipt,
)
from .recovery_descriptor import (
    BACKUP_MEMBER,
    BUNDLE_PROFILE,
    configuration_digest,
    create_bundle,
    decode_bundle,
)
from .recovery_suite_registry import RecoverySuiteRegistry, RecoverySuiteSelection
from .redaction import validate_public_output
from .successor_publication import (
    DurableSuccessorPublication,
    SuccessorBinding,
    SuccessorPhase,
    SuccessorPublicationBackend,
)
from .suite_backup import open_backup_v6_with_secret, seal_backup_v6
from .yi_compat import YiTpassRecoveryAdapter

DISCOVERY_ENDPOINT = "https://operator:8443"
RECOVERY_AUDIENCE = "locus-integrated-recovery"
SUBJECT_ID = "11" * 32


def _raw_public(key: Ed25519PrivateKey) -> bytes:
    return key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )


def _fingerprint(private_key: bytes) -> str:
    public = (
        Ed25519PrivateKey.from_private_bytes(private_key)
        .public_key()
        .public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    )
    return hashlib.sha256(public).hexdigest()


def _decode_receipt(value: object) -> bytes:
    if not isinstance(value, str) or not value or "=" in value or len(value) > 32768:
        raise ClientApiError("bootstrap_rejected")
    try:
        return base64.b64decode(
            value + "=" * ((4 - len(value) % 4) % 4), altchars=b"-_", validate=True
        )
    except ValueError as exc:
        raise ClientApiError("bootstrap_rejected") from exc


def _context_dict(context: RecoveryContext) -> dict[str, object]:
    return {
        "backup_id": context.backup_id,
        "configuration_digest": context.configuration_digest,
        "digest_context": context.digest_context,
        "epoch": context.epoch,
        "policy_id": context.policy_id,
        "recovery_id": context.recovery_id,
        "suite_context_digest": context.suite_context_digest,
        "suite_id": context.suite_id,
    }


@dataclass(frozen=True)
class _RemoteEpoch:
    receipt_bytes: bytes
    pointer_bytes: bytes
    bundle: Any
    descriptor: dict[str, Any]
    backup: dict[str, Any]
    reference: BackupReference
    selection: RecoverySuiteSelection
    context: RecoveryContext
    public_fingerprint: str


@dataclass(frozen=True)
class _PreparedIntegratedEpoch:
    """One fresh epoch prepared in memory and at recipient parties only."""

    selection: RecoverySuiteSelection
    context: RecoveryContext
    policy_id: str
    resolver_profile_id: str
    canonical: bytes
    protected_key: bytes
    backup: dict[str, Any]
    backup_bytes: bytes
    descriptor_payload: dict[str, Any]
    descriptor: bytes
    bundle: bytes
    bundle_digest: str
    pointer: bytes
    receipt: bytes
    reference: BackupReference
    recovery_handle: str
    public_fingerprint: str
    expected_pointer: bytes | None

    @property
    def descriptor_digest(self) -> str:
        return hashlib.sha256(self.descriptor).hexdigest()

    def result(self) -> dict[str, Any]:
        return {
            "recovery_handle": self.recovery_handle,
            "backup_id": self.reference.bid,
            "epoch": self.reference.epoch,
            "policy_id": self.policy_id,
            "suite_id": self.selection.suite_id,
            "profile_id": self.selection.profile_id,
            "threshold_k": self.selection.threshold.k,
            "threshold_n": self.selection.threshold.n,
            "public_fingerprint": self.public_fingerprint,
            "receipt_bytes": self.receipt,
        }


class _InjectedIntegratedSuccessorCrash(RuntimeError):
    pass


class _DeployedSuccessorBackend(SuccessorPublicationBackend):
    """Bind the P4.3 publication phases to the deployed P7.5 services."""

    def __init__(
        self,
        *,
        client: IntegratedResearchClientApi,
        prepared: _PreparedIntegratedEpoch,
        predecessor_epoch: int,
        predecessor_key_digest: str,
        operation_id: str,
    ) -> None:
        self.client = client
        self.prepared = prepared
        self.predecessor_epoch = predecessor_epoch
        self.predecessor_key_digest = predecessor_key_digest
        self.operation_id = operation_id
        self.completed: dict[SuccessorPhase, str] = {}
        configured = os.environ.get(
            "LOCUS_INTEGRATED_SUCCESSOR_CRASH_PHASES", ""
        ).split(",")
        self.crash_phases = {
            SuccessorPhase(value)
            for value in configured
            if value in {phase.value for phase in SuccessorPhase}
        }
        self.injected: set[SuccessorPhase] = set()
        self.activated = False

    def _effect(
        self,
        phase: SuccessorPhase,
        idempotency_key: str,
        action: Any,
    ) -> None:
        prior = self.completed.get(phase)
        if prior is not None:
            if prior != idempotency_key:
                raise ClientApiError("successor_rejected")
            return
        action()
        self.completed[phase] = idempotency_key
        if phase in self.crash_phases and phase not in self.injected:
            self.injected.add(phase)
            raise _InjectedIntegratedSuccessorCrash(phase.value)

    def preserve_original_key(
        self, binding: SuccessorBinding, idempotency_key: str
    ) -> None:
        def action() -> None:
            if binding.recovered_key_digest != self.predecessor_key_digest:
                raise ClientApiError("successor_rejected")

        self._effect(SuccessorPhase.PRESERVE_ORIGINAL_KEY, idempotency_key, action)

    def prepare_parties(self, binding: SuccessorBinding, idempotency_key: str) -> None:
        del binding
        self._effect(SuccessorPhase.PREPARE_PARTIES, idempotency_key, lambda: None)

    def publish_backup(self, binding: SuccessorBinding, idempotency_key: str) -> None:
        del binding
        self._effect(
            SuccessorPhase.PUBLISH_BACKUP,
            idempotency_key,
            lambda: self.client._publish_prepared_backup(self.prepared),
        )

    def publish_descriptor(
        self, binding: SuccessorBinding, idempotency_key: str
    ) -> None:
        del binding
        self._effect(
            SuccessorPhase.PUBLISH_DESCRIPTOR,
            idempotency_key,
            lambda: self.client._publish_prepared_descriptor(self.prepared),
        )

    def verify_readiness(self, binding: SuccessorBinding, idempotency_key: str) -> None:
        del binding
        self._effect(
            SuccessorPhase.VERIFY_READINESS,
            idempotency_key,
            lambda: self.client._install_prepared_current(self.prepared),
        )

    def verify_successor_recovery(
        self, binding: SuccessorBinding, idempotency_key: str
    ) -> None:
        del binding
        self._effect(
            SuccessorPhase.VERIFY_SUCCESSOR_RECOVERY,
            idempotency_key,
            lambda: self.client._verify_prepared_recovery(
                self.prepared, f"{self.operation_id}:prepared-recovery"
            ),
        )

    def activate_successor(
        self, binding: SuccessorBinding, idempotency_key: str
    ) -> None:
        del binding

        def action() -> None:
            self.client._publish_prepared_pointer(self.prepared)
            self.client._publish_prepared_discovery(self.prepared)
            self.activated = True

        self._effect(SuccessorPhase.ACTIVATE_SUCCESSOR, idempotency_key, action)

    def retire_predecessor(
        self, binding: SuccessorBinding, idempotency_key: str
    ) -> None:
        del binding
        self._effect(
            SuccessorPhase.RETIRE_PREDECESSOR,
            idempotency_key,
            lambda: self.client._retire_predecessor(
                self.prepared, self.predecessor_epoch
            ),
        )

    def rotate_protected_key(
        self, binding: SuccessorBinding, idempotency_key: str
    ) -> None:
        del binding
        self._effect(
            SuccessorPhase.OPTIONAL_KEY_ROTATION, idempotency_key, lambda: None
        )

    def authorized_recoverable_epochs(
        self, binding: SuccessorBinding
    ) -> frozenset[int]:
        return frozenset(
            {binding.successor_epoch} if self.activated else {binding.predecessor_epoch}
        )


class _RemoteAppssEndpoint(AppssPartyEndpoint):
    def __init__(
        self, client: IntegratedResearchClientApi, holder: AppssHolderBinding
    ) -> None:
        self.client = client
        self.binding = holder

    @property
    def holder_id(self) -> int:
        return self.binding.index

    @property
    def service_identity(self) -> str:
        return self.binding.service_identity

    def evaluate(self, request_bytes: bytes, *, idempotency_key: str) -> bytes:
        del idempotency_key
        result = self.client._party(
            self.holder_id, "/v1/appss/evaluate", {"request_hex": request_bytes.hex()}
        )
        return bytes.fromhex(result["response_hex"])

    def initialize(self, request_bytes: bytes, *, idempotency_key: str) -> bytes:
        del idempotency_key
        result = self.client._party(
            self.holder_id, "/v1/appss/initialize", {"request_hex": request_bytes.hex()}
        )
        return bytes.fromhex(result["response_hex"])

    def install(self, install_bytes: bytes, *, idempotency_key: str) -> bytes:
        del idempotency_key
        value = json.loads(install_bytes)
        result = self.client._party(
            self.holder_id,
            "/v1/appss/install",
            {
                "context_digest": value["context_digest"],
                "install_hex": install_bytes.hex(),
                "profile_id": value["profile_id"],
            },
        )
        return bytes.fromhex(result["ready_hex"])


class IntegratedResearchClientApi:
    """Ephemeral client coordinator whose durable state lives only in remote roles."""

    def __init__(self, *, role_root: str | Path, clock: Any | None = None) -> None:
        self.root = Path(role_root)
        self.clock = (lambda: int(time.time())) if clock is None else clock
        self.proof_key = Ed25519PrivateKey.from_private_bytes(
            (self.root / "proof-key.bin").read_bytes()
        )
        self.trust = json.loads((self.root / "trust.json").read_bytes())
        self.operator_public = Ed25519PublicKey.from_public_bytes(
            bytes.fromhex(self.trust["operator_public_key"])
        )
        self.suites = RecoverySuiteRegistry()
        self.operations: set[str] = set()
        self.holder_schedule_index = 0
        self._stage = "idle"

    def _mark(self, stage: str) -> None:
        self._stage = stage

    def _report_rejection(self, category: str, error: BaseException) -> None:
        if os.environ.get("LOCUS_OPERATOR_DIAGNOSTICS") == "1":
            service_category = (
                str(error)
                if isinstance(error, IntegratedRpcError)
                else "local_rejected"
            )
            print(
                json.dumps(
                    {
                        "category": category,
                        "service_category": service_category,
                        "stage": self._stage,
                        "status": "rejected",
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                ),
                file=sys.stderr,
                flush=True,
            )

    def _rpc(self, service: str, path: str, value: dict[str, Any]) -> dict[str, Any]:
        return rpc_request(
            endpoint=f"https://{service}:8443",
            path=path,
            role_root=self.root,
            value=value,
        )

    def _party(
        self, holder_id: int, path: str, value: dict[str, Any]
    ) -> dict[str, Any]:
        return self._rpc(f"party{holder_id}", path, value)

    def catalog(self) -> dict[str, object]:
        return LocalResearchClientApi().catalog()

    def _canonical(self, policy_id: object, recovery_input: object) -> bytes:
        policy = DEFAULT_CUE_POLICY_REGISTRY.require(str(policy_id))
        if policy.metadata.resolver_profile_id == "LOCUS-deterministic-directory-v2":
            resolved = self._rpc(
                "resolver",
                "/v1/resolve",
                {"policy_id": policy.policy_id, "values": recovery_input},
            )
            return bytes.fromhex(resolved["canonical_hex"])
        return policy.process(recovery_input).canonical_bytes

    def preview_policy(self, request: object) -> dict[str, object]:
        if (
            not isinstance(request, dict)
            or set(request) != {"api_version", "policy_id", "recovery_input"}
            or request["api_version"] != CLIENT_API_VERSION
        ):
            raise ClientApiError("input_rejected")
        try:
            self._mark("policy-processing")
            canonical = self._canonical(request["policy_id"], request["recovery_input"])
            return {
                "api_version": CLIENT_API_VERSION,
                "normalized_preview": json.loads(canonical),
                "policy_id": request["policy_id"],
                "status": "input_validated",
            }
        except Exception:
            raise ClientApiError("input_rejected") from None

    def _protected_key(self, value: object) -> bytes:
        if not isinstance(value, dict) or set(value) != {"hex", "mode"}:
            raise ClientApiError("input_rejected")
        if value["mode"] == "generate-synthetic" and value["hex"] is None:
            return random_bytes(32)
        if (
            value["mode"] != "import-synthetic"
            or not isinstance(value["hex"], str)
            or len(value["hex"]) != 64
        ):
            raise ClientApiError("input_rejected")
        result = bytes.fromhex(value["hex"])
        Ed25519PrivateKey.from_private_bytes(result)
        return result

    @staticmethod
    def _holders(selection: RecoverySuiteSelection) -> tuple[AppssHolderBinding, ...]:
        return tuple(
            AppssHolderBinding(
                index=index,
                party_id=f"party{index}",
                service_identity=f"spiffe://locus.invalid/integrated/party{index}",
            )
            for index in selection.holder_ids
        )

    @staticmethod
    def _password(
        *, suite_id: str, context: RecoveryContext, canonical: bytes, nonce: bytes
    ) -> bytes:
        if suite_id == APPSS_SUITE_ID:
            return derive_password_input(
                bytes.fromhex(context.suite_context_digest or ""), canonical
            )
        if suite_id == YI_SUITE_ID:
            return hash_scalar(
                "LOCUS-context-password",
                canonical,
                nonce,
                context.backup_id,
                context.epoch,
            ).to_bytes(32, "big")
        raise ClientApiError("recovery_rejected")

    def _sign(self, kind: str, payload: dict[str, Any]) -> bytes:
        result = self._rpc("operator", "/v1/sign", {"kind": kind, "payload": payload})
        return bytes.fromhex(result["object_hex"])

    def _issue(self, binding: AdmissionBinding) -> tuple[dict[str, str], Any]:
        result = self._rpc("admission", "/v1/issue", {"binding": binding.to_dict()})
        from .contracts import AdmissionCapability

        capability = AdmissionCapability(
            format_id=result["format_id"],
            payload=bytes.fromhex(result["capability_hex"]),
        )
        return {
            "format_id": capability.format_id,
            "payload_hex": capability.payload.hex(),
        }, capability

    def _storage(
        self,
        *,
        operation: str,
        object_key: str,
        reference: BackupReference,
        recovery_handle: str,
        payload: bytes | None = None,
    ) -> bytes | None:
        from .contracts import GatewayRequest, StorageOperation

        request = GatewayRequest(
            StorageOperation(operation), object_key, reference, payload
        )
        now = self.clock()
        operation_name = {
            "create_immutable": "storage_create_immutable",
            "read_exact": "storage_read_exact",
            "compare_and_swap": "storage_compare_and_swap",
            "delete_exact": "storage_delete_exact",
        }[operation]
        binding = AdmissionBinding(
            subject=SUBJECT_ID,
            backup_id=reference.bid,
            epoch=reference.epoch,
            operation=operation_name,
            audience=STORAGE_AUDIENCE,
            client_key_thumbprint=client_key_thumbprint(_raw_public(self.proof_key)),
            nonce=secrets.token_hex(32),
            issued_at=now,
            expires_at=now + 120,
            issuer=ADMISSION_ISSUER,
            object_prefix=pseudonymous_object_prefix(SUBJECT_ID, reference.bid),
        )
        capability_wire, capability = self._issue(binding)
        proof = create_client_proof(
            capability, self.proof_key, gateway_request_bytes(request)
        )
        result = self._rpc(
            "storage-gateway",
            "/v1/execute",
            {
                "binding": binding.to_dict(),
                "capability": capability_wire,
                "client_proof": proof.hex(),
                "gateway_request": {
                    "backup_reference": reference.to_dict(),
                    "object_key": object_key,
                    "operation": operation,
                    "payload_hex": None if payload is None else payload.hex(),
                },
                "now": now,
                "recovery_handle": recovery_handle,
            },
        )
        return (
            None
            if result["payload_hex"] is None
            else bytes.fromhex(result["payload_hex"])
        )

    def _trust_configuration(self, now: int) -> bytes:
        return encode(
            {
                "discovery": {
                    "audience": "locus-integrated-discovery",
                    "endpoint": DISCOVERY_ENDPOINT,
                },
                "generation": 1,
                "operator": {
                    "issuer": OPERATOR_ISSUER,
                    "key_id": OPERATOR_KEY_ID,
                    "public_key_hex": self.trust["operator_public_key"],
                },
                "parties": [
                    {
                        "authorizer_id": index,
                        "endpoint": f"https://party{index}:8443",
                        "identity_key_id": f"party-{index}-current-1",
                        "public_key_hex": self.trust["party_public_keys"][str(index)],
                    }
                    for index in range(1, 6)
                ],
                "previous_configuration_sha256": None,
                "profile": BOOTSTRAP_PROFILE,
                "valid_from": now - 60,
                "valid_until": now + 86_400,
                "version": TRUST_CONFIGURATION_VERSION,
            }
        )

    def enroll(self, request: object) -> EnrollmentResult:
        fields = {
            "api_version",
            "deployment_profile_id",
            "operation_id",
            "policy_id",
            "protected_key",
            "recovery_input",
            "suite_id",
        }
        if (
            not isinstance(request, dict)
            or set(request) != fields
            or request["api_version"] != CLIENT_API_VERSION
        ):
            raise ClientApiError("input_rejected")
        operation_id = str(request["operation_id"])
        if operation_id in self.operations:
            raise ClientApiError("operation_conflict")
        try:
            canonical = self._canonical(request["policy_id"], request["recovery_input"])
            policy = DEFAULT_CUE_POLICY_REGISTRY.require(str(request["policy_id"]))
            profile = paired_profile(str(request["deployment_profile_id"]))
            selection, adapter = self.suites.select_new_epoch(
                profile.selector_for(str(request["suite_id"]))
            )
            profile.validate_selection(selection)
            self._mark("epoch-enrollment")
            result = self._enroll_epoch(
                selection=selection,
                adapter=adapter,
                policy_id=policy.policy_id,
                resolver_profile_id=policy.metadata.resolver_profile_id,
                canonical=canonical,
                protected_key=self._protected_key(request["protected_key"]),
                backup_id=random_bytes(16),
                epoch=1,
                predecessor_digest=None,
                expected_pointer=None,
            )
            self.operations.add(operation_id)
            return EnrollmentResult(
                operation_id=operation_id,
                completed_phases=(
                    "key_generation",
                    "cue_processing",
                    "suite_initialization",
                    "backup_publication",
                    "descriptor_publication",
                    "completion",
                ),
                **result,
            )
        except ClientApiError:
            raise
        except Exception as exc:
            self._report_rejection("enrollment_rejected", exc)
            raise ClientApiError("enrollment_rejected") from None

    def _prepare_epoch(
        self,
        *,
        selection: RecoverySuiteSelection,
        adapter: Any,
        policy_id: str,
        resolver_profile_id: str,
        canonical: bytes,
        protected_key: bytes,
        backup_id: bytes,
        epoch: int,
        predecessor_digest: str | None,
        expected_pointer: bytes | None,
    ) -> _PreparedIntegratedEpoch:
        now = self.clock()
        nonce = random_bytes(16)
        handle = f"integrated-recovery:{backup_id.hex()}"
        public_configuration = hashlib.sha256(
            encode(
                {
                    "authorization_quorum": selection.authorization_quorum,
                    "backup_id": backup_id.hex(),
                    "deployment_id": "LOCUS-integrated-reference-deployment-v1",
                    "epoch": epoch,
                    "holder_ids": list(selection.holder_ids),
                    "policy_id": policy_id,
                    "profile_id": selection.profile_id,
                    "suite_id": selection.suite_id,
                }
            )
        ).digest()
        holders = self._holders(selection)
        suite_context = (
            context_digest(
                backup_id=backup_id,
                epoch=epoch,
                policy_id=policy_id,
                holders=holders,
                k=selection.threshold.k,
                n=selection.threshold.n,
                configuration_digest=public_configuration,
            )
            if selection.suite_id == APPSS_SUITE_ID
            else public_configuration
        )
        context = RecoveryContext(
            selection.suite_id,
            handle,
            backup_id.hex(),
            epoch,
            policy_id,
            public_configuration.hex(),
            f"integrated:{backup_id.hex()}:{epoch}",
            suite_context.hex(),
        )
        password = self._password(
            suite_id=selection.suite_id,
            context=context,
            canonical=canonical,
            nonce=nonce,
        )
        self._mark("suite-initialization")
        if selection.suite_id == APPSS_SUITE_ID:
            endpoints = {
                holder.index: _RemoteAppssEndpoint(self, holder) for holder in holders
            }
            initialized = initialize_with_parties(
                context=context,
                password_input=password,
                holders=holders,
                endpoints=endpoints,
                admission_grant_digest="00" * 32,
                client_proof_key_digest=hashlib.sha256(
                    _raw_public(self.proof_key)
                ).hexdigest(),
                operation_id=secrets.token_hex(32),
                threshold=selection.threshold,
            )
            public_state = initialized.public_state
            recovery_secret = initialized.recovery_secret
        else:
            initialized = adapter.initialize(
                context=context, password_input=password, threshold=selection.threshold
            )
            public_state = initialized.public_state
            recovery_secret = initialized.recovery_secret
            for state in initialized.party_states:
                self._party(
                    state.holder_id,
                    "/v1/yi/enroll",
                    {
                        "backup_id": backup_id.hex(),
                        "context": _context_dict(context),
                        "epoch": epoch,
                        "party_state_hex": state.payload.hex(),
                        "public_state_hex": public_state.payload.hex(),
                    },
                )
        self._mark("backup-sealing")
        backup = seal_backup_v6(
            protected_key=protected_key,
            context=context,
            cue_policy_id=policy_id,
            resolver_profile=resolver_profile_id,
            suite_id=selection.suite_id,
            public_state_format=public_state.format_id,
            public_state_payload=public_state.payload,
            recovery_secret=recovery_secret,
            profile_id=selection.profile_id,
            threshold=selection.threshold,
            bid=backup_id,
            nonce=nonce,
        )
        backup_bytes = encode(backup)
        descriptor_payload: dict[str, Any] = {
            "authorization": {
                "admission_profile": "LOCUS-local-synthetic-admission-v1",
                "audience": RECOVERY_AUDIENCE,
                "authorizers": [
                    {
                        "authorizer_id": index,
                        "endpoint": f"https://party{index}:8443",
                        "identity_key_id": f"party-{index}-current-1",
                    }
                    for index in range(1, 6)
                ],
                "operation_namespace": "locus-integrated-recovery",
                "quorum": 4,
                "security_policy": "LOCUS-security-policy-v1",
            },
            "backup": {
                "format": "LOCUS-reference-backup-v6",
                "length": len(backup_bytes),
                "member": BACKUP_MEMBER,
                "sha256": hashlib.sha256(backup_bytes).hexdigest(),
            },
            "backup_id": backup_id.hex(),
            "cue_policy": {
                "id": policy_id,
                "public_parameters_hex": encode({"cardinality": 3}).hex(),
                "resolver_profile": resolver_profile_id,
            },
            "epoch": epoch,
            "expires_at": now + 86_400,
            "issued_at": now,
            "issuer": OPERATOR_ISSUER,
            "lifecycle": {
                "configuration_digest": "00" * 32,
                "predecessor_descriptor_digest": predecessor_digest,
            },
            "recovery_id": handle,
            "recovery_suite": {
                "holders": [
                    {"authorizer_id": index, "holder_id": index}
                    for index in selection.holder_ids
                ],
                "id": selection.suite_id,
                "public_state_format": public_state.format_id,
                "public_state_hex": public_state.payload.hex(),
                "threshold": {"k": selection.threshold.k, "n": selection.threshold.n},
            },
            "subject_id": SUBJECT_ID,
        }
        descriptor_payload["lifecycle"]["configuration_digest"] = configuration_digest(
            descriptor_payload
        )
        self._mark("descriptor-signing")
        descriptor = self._sign("descriptor", descriptor_payload)
        bundle = create_bundle(
            backup_bytes=backup_bytes,
            descriptor_bytes=descriptor,
            backup_format="LOCUS-reference-backup-v6",
        )
        bundle_digest = hashlib.sha256(bundle).hexdigest()
        pointer_payload = {
            "backup_id": backup_id.hex(),
            "bundle": {
                "length": len(bundle),
                "locator": f"integrated-bundle:{bundle_digest}",
                "profile": BUNDLE_PROFILE,
                "sha256": bundle_digest,
            },
            "configuration_digest": descriptor_payload["lifecycle"][
                "configuration_digest"
            ],
            "descriptor_sha256": hashlib.sha256(descriptor).hexdigest(),
            "epoch": epoch,
            "expires_at": now + 86_400,
            "issued_at": now,
            "issuer": OPERATOR_ISSUER,
            "subject_id": SUBJECT_ID,
        }
        pointer = self._sign("pointer", pointer_payload)
        receipt = self._sign(
            "receipt",
            {
                "discovery_endpoint": DISCOVERY_ENDPOINT,
                "discovery_profile": BOOTSTRAP_PROFILE,
                "initial": {
                    "backup_id": backup_id.hex(),
                    "configuration_digest": descriptor_payload["lifecycle"][
                        "configuration_digest"
                    ],
                    "descriptor_sha256": hashlib.sha256(descriptor).hexdigest(),
                    "epoch": epoch,
                },
                "issued_at": now,
                "issuer": OPERATOR_ISSUER,
                "operator_key_id": OPERATOR_KEY_ID,
                "recovery_handle": handle,
                "subject_id": SUBJECT_ID,
            },
        )
        reference = BackupReference.from_backup(backup)
        return _PreparedIntegratedEpoch(
            selection=selection,
            context=context,
            policy_id=policy_id,
            resolver_profile_id=resolver_profile_id,
            canonical=canonical,
            protected_key=protected_key,
            backup=backup,
            backup_bytes=backup_bytes,
            descriptor_payload=descriptor_payload,
            descriptor=descriptor,
            bundle=bundle,
            bundle_digest=bundle_digest,
            pointer=pointer,
            receipt=receipt,
            reference=reference,
            recovery_handle=handle,
            public_fingerprint=_fingerprint(protected_key),
            expected_pointer=expected_pointer,
        )

    def _publish_prepared_backup(self, prepared: _PreparedIntegratedEpoch) -> None:
        from .object_store import encode_versioned_backup_object

        self._mark("backup-publication")
        self._storage(
            operation="create_immutable",
            object_key=backup_object_key(SUBJECT_ID, prepared.reference),
            reference=prepared.reference,
            recovery_handle=prepared.recovery_handle,
            payload=encode_versioned_backup_object(prepared.backup)[1],
        )

    def _publish_prepared_descriptor(self, prepared: _PreparedIntegratedEpoch) -> None:
        self._mark("descriptor-publication")
        self._storage(
            operation="create_immutable",
            object_key=descriptor_object_key(
                SUBJECT_ID, prepared.reference, prepared.descriptor_digest
            ),
            reference=prepared.reference,
            recovery_handle=prepared.recovery_handle,
            payload=prepared.descriptor,
        )
        self._mark("bundle-publication")
        self._storage(
            operation="create_immutable",
            object_key=bundle_object_key(
                SUBJECT_ID,
                prepared.reference,
                prepared.bundle_digest,
                len(prepared.bundle),
            ),
            reference=prepared.reference,
            recovery_handle=prepared.recovery_handle,
            payload=prepared.bundle,
        )

    @staticmethod
    def _party_current_payload(
        prepared: _PreparedIntegratedEpoch, index: int
    ) -> dict[str, object]:
        issued_at = int(prepared.descriptor_payload["issued_at"])
        return {
            "authorizer_id": index,
            "backup_id": prepared.reference.bid,
            "configuration_digest": prepared.descriptor_payload["lifecycle"][
                "configuration_digest"
            ],
            "cue_policy_id": prepared.policy_id,
            "descriptor_sha256": prepared.descriptor_digest,
            "epoch": prepared.reference.epoch,
            "expires_at": issued_at + 120,
            "issued_at": issued_at,
            "recovery_id": prepared.recovery_handle,
            "recovery_suite_id": prepared.selection.suite_id,
            "state": "active",
            "subject_id": SUBJECT_ID,
        }

    def _install_prepared_current(self, prepared: _PreparedIntegratedEpoch) -> None:
        self._mark("party-current-publication")
        for index in range(1, 6):
            self._party(
                index,
                "/v1/current/install",
                {"payload": self._party_current_payload(prepared, index)},
            )

    def _publish_prepared_pointer(self, prepared: _PreparedIntegratedEpoch) -> None:
        from .contracts import CurrentDescriptorPointer
        from .recovery_descriptor import CURRENT_POINTER_VERSION

        expected = (
            None
            if prepared.expected_pointer is None
            else CurrentDescriptorPointer(
                CURRENT_POINTER_VERSION, prepared.expected_pointer
            )
        )
        replacement = CurrentDescriptorPointer(
            CURRENT_POINTER_VERSION, prepared.pointer
        )
        self._mark("pointer-publication")
        self._storage(
            operation="compare_and_swap",
            object_key=current_pointer_object_key(
                SUBJECT_ID, prepared.reference, prepared.recovery_handle
            ),
            reference=prepared.reference,
            recovery_handle=prepared.recovery_handle,
            payload=encode_pointer_cas(expected=expected, replacement=replacement),
        )

    def _publish_prepared_discovery(self, prepared: _PreparedIntegratedEpoch) -> None:
        self._mark("discovery-publication")
        self._rpc(
            "operator",
            "/v1/discovery/publish",
            {
                "record": {
                    "backup_id": prepared.reference.bid,
                    "backup_digest": prepared.reference.backup_digest,
                    "epoch": prepared.reference.epoch,
                    "public_fingerprint": prepared.public_fingerprint,
                    "recovery_handle": prepared.recovery_handle,
                    "subject_id": SUBJECT_ID,
                }
            },
        )

    def _prepared_remote_epoch(
        self, prepared: _PreparedIntegratedEpoch
    ) -> _RemoteEpoch:
        bundle = decode_bundle(
            prepared.bundle,
            issuer_public_key=self.operator_public,
            expected_issuer=OPERATOR_ISSUER,
            expected_key_id=OPERATOR_KEY_ID,
        )
        return _RemoteEpoch(
            prepared.receipt,
            prepared.pointer,
            bundle,
            prepared.descriptor_payload,
            prepared.backup,
            prepared.reference,
            prepared.selection,
            prepared.context,
            prepared.public_fingerprint,
        )

    def _verify_prepared_recovery(
        self, prepared: _PreparedIntegratedEpoch, operation_id: str
    ) -> None:
        epoch = self._prepared_remote_epoch(prepared)
        password = self._password(
            suite_id=prepared.selection.suite_id,
            context=prepared.context,
            canonical=prepared.canonical,
            nonce=bytes.fromhex(prepared.backup["nonce"]),
        )
        grant = self._authorize(epoch, operation_id)
        secret = self._recover_secret(epoch, password, grant, operation_id)
        protected = open_backup_v6_with_secret(
            backup=prepared.backup, recovery_secret=secret
        )
        if _fingerprint(protected) != prepared.public_fingerprint:
            raise ClientApiError("successor_rejected")

    def _retire_predecessor(
        self, prepared: _PreparedIntegratedEpoch, predecessor_epoch: int
    ) -> None:
        self._mark("predecessor-retirement")
        for index in range(1, 6):
            self._party(
                index,
                "/v1/current/retire",
                {
                    "backup_id": prepared.reference.bid,
                    "predecessor_epoch": predecessor_epoch,
                    "successor_epoch": prepared.reference.epoch,
                },
            )

    def _enroll_epoch(
        self,
        *,
        selection: RecoverySuiteSelection,
        adapter: Any,
        policy_id: str,
        resolver_profile_id: str,
        canonical: bytes,
        protected_key: bytes,
        backup_id: bytes,
        epoch: int,
        predecessor_digest: str | None,
        expected_pointer: bytes | None,
    ) -> dict[str, Any]:
        prepared = self._prepare_epoch(
            selection=selection,
            adapter=adapter,
            policy_id=policy_id,
            resolver_profile_id=resolver_profile_id,
            canonical=canonical,
            protected_key=protected_key,
            backup_id=backup_id,
            epoch=epoch,
            predecessor_digest=predecessor_digest,
            expected_pointer=expected_pointer,
        )
        self._publish_prepared_backup(prepared)
        self._publish_prepared_descriptor(prepared)
        self._install_prepared_current(prepared)
        self._publish_prepared_pointer(prepared)
        self._publish_prepared_discovery(prepared)
        return prepared.result()

    def _load(self, receipt_value: object) -> _RemoteEpoch:
        receipt = _decode_receipt(receipt_value)
        decoded_receipt = decode_recovery_receipt(
            receipt,
            issuer_public_key=self.operator_public,
            expected_issuer=OPERATOR_ISSUER,
            expected_key_id=OPERATOR_KEY_ID,
        )
        handle = decoded_receipt["payload"]["recovery_handle"]
        record = self._rpc(
            "operator", "/v1/discovery/read", {"recovery_handle": handle}
        )["record"]
        reference = BackupReference(
            record["backup_id"], record["epoch"], record["backup_digest"]
        )
        pointer = self._storage(
            operation="read_exact",
            object_key=current_pointer_object_key(SUBJECT_ID, reference, handle),
            reference=reference,
            recovery_handle=handle,
        )
        if pointer is None:
            raise ClientApiError("bootstrap_rejected")
        pointer_payload = json.loads(pointer)["payload"]
        bundle_binding = pointer_payload["bundle"]
        bundle_bytes = self._storage(
            operation="read_exact",
            object_key=bundle_object_key(
                SUBJECT_ID,
                reference,
                bundle_binding["sha256"],
                bundle_binding["length"],
            ),
            reference=reference,
            recovery_handle=handle,
        )
        if bundle_bytes is None:
            raise ClientApiError("bootstrap_rejected")
        observations = self._current_observations(reference)
        now = self.clock()
        authenticated = authenticate_recovery_bootstrap(
            trust_configuration_bytes=self._trust_configuration(now),
            discovery_endpoint=DISCOVERY_ENDPOINT,
            recovery_handle=handle,
            expected_subject_id=SUBJECT_ID,
            current_pointer_bytes=pointer,
            bundle_bytes=bundle_bytes,
            current_state_observations=observations,
            now=now,
            receipt_bytes=receipt,
        )
        descriptor = authenticated.bundle.descriptor["payload"]
        suite = descriptor["recovery_suite"]
        threshold = ThresholdParameters(**suite["threshold"])
        selector = RecoverySuiteRegistry.selector_bytes(
            suite_id=suite["id"],
            threshold=threshold,
            authorizer_ids=(1, 2, 3, 4, 5),
            authorization_quorum=4,
        )
        selection, _adapter = self.suites.select_new_epoch(selector)
        backup = authenticated.bundle.backup
        context = RecoveryContext(
            suite["id"],
            descriptor["recovery_id"],
            descriptor["backup_id"],
            descriptor["epoch"],
            descriptor["cue_policy"]["id"],
            descriptor["lifecycle"]["configuration_digest"],
            f"integrated:{descriptor['backup_id']}:{descriptor['epoch']}",
            backup["recovery_suite"]["context_digest"],
        )
        public_fingerprint = str(record["public_fingerprint"])
        return _RemoteEpoch(
            receipt,
            pointer,
            authenticated.bundle,
            descriptor,
            backup,
            reference,
            selection,
            context,
            public_fingerprint,
        )

    def _current_observations(
        self, reference: BackupReference
    ) -> list[PartyCurrentObservation]:
        observations: list[PartyCurrentObservation] = []
        for index in range(1, 6):
            try:
                result = self._party(
                    index,
                    "/v1/current/read",
                    {"backup_id": reference.bid, "epoch": reference.epoch},
                )
            except Exception:
                continue
            observations.append(
                PartyCurrentObservation(
                    index,
                    f"https://party{index}:8443",
                    bytes.fromhex(result["summary_hex"]),
                )
            )
        return observations

    def bootstrap(self, receipt: object) -> BootstrapResult:
        try:
            epoch = self._load(receipt)
            fingerprint = epoch.public_fingerprint
            return BootstrapResult(
                epoch.context.recovery_id,
                epoch.reference.bid,
                epoch.reference.epoch,
                epoch.context.policy_id,
                epoch.descriptor["cue_policy"]["resolver_profile"],
                epoch.selection.suite_id,
                epoch.selection.profile_id,
                epoch.selection.threshold.k,
                epoch.selection.threshold.n,
                epoch.selection.authorization_quorum,
                fingerprint,
                True,
            )
        except Exception:
            raise ClientApiError("bootstrap_rejected") from None

    def _authorize(self, epoch: _RemoteEpoch, operation_id: str) -> str:
        now = self.clock()
        binding = AdmissionBinding(
            subject=SUBJECT_ID,
            backup_id=epoch.reference.bid,
            epoch=epoch.reference.epoch,
            operation=RECOVERY_OPERATION,
            audience=RECOVERY_AUDIENCE,
            client_key_thumbprint=client_key_thumbprint(_raw_public(self.proof_key)),
            nonce=secrets.token_hex(32),
            issued_at=now,
            expires_at=now + 120,
            issuer=ADMISSION_ISSUER,
        )
        wire, capability = self._issue(binding)
        admitted = encode(
            {
                "backup_id": epoch.reference.bid,
                "epoch": epoch.reference.epoch,
                "operation_id": operation_id,
                "recovery_handle": epoch.context.recovery_id,
            }
        )
        proof = create_client_proof(capability, self.proof_key, admitted)
        grants = []
        for index in range(1, 6):
            try:
                result = self._party(
                    index,
                    "/v1/authorize",
                    {
                        "admitted_request_hex": admitted.hex(),
                        "binding": binding.to_dict(),
                        "capability": wire,
                        "client_proof": proof.hex(),
                        "now": now,
                    },
                )
                grants.append(result["grant_digest"])
            except Exception:
                continue
        if len(grants) < 4 or len(set(grants)) != 1:
            raise ClientApiError("recovery_rejected")
        return grants[0]

    def _recover_secret(
        self, epoch: _RemoteEpoch, password: bytes, grant: str, operation_id: str
    ) -> bytes:
        suite = epoch.descriptor["recovery_suite"]
        public = PublicRecoveryState(
            suite["id"],
            suite["public_state_format"],
            bytes.fromhex(suite["public_state_hex"]),
        )
        holder_order = list(epoch.selection.holder_ids)
        configured_order = os.environ.get("LOCUS_INTEGRATED_HOLDER_ORDER", "")
        schedule = os.environ.get("LOCUS_INTEGRATED_HOLDER_SCHEDULE", "")
        if schedule:
            entries = schedule.split(";")
            if self.holder_schedule_index >= len(entries):
                raise ClientApiError("recovery_rejected")
            configured_order = entries[self.holder_schedule_index]
            self.holder_schedule_index += 1
        if configured_order:
            try:
                requested_order = [int(value) for value in configured_order.split(",")]
            except ValueError as exc:
                raise ClientApiError("recovery_rejected") from exc
            if (
                len(requested_order) != len(holder_order)
                or len(set(requested_order)) != len(requested_order)
                or set(requested_order) != set(holder_order)
            ):
                raise ClientApiError("recovery_rejected")
            holder_order = requested_order
        available: list[int] = []
        disabled_raw = os.environ.get("LOCUS_INTEGRATED_DISABLED_HOLDERS", "")
        try:
            disabled = {int(value) for value in disabled_raw.split(",") if value}
        except ValueError as exc:
            raise ClientApiError("recovery_rejected") from exc
        if not disabled <= set(epoch.selection.holder_ids):
            raise ClientApiError("recovery_rejected")
        for index in holder_order:
            if index in disabled:
                continue
            try:
                health = self._party(index, "/health", {})
                if health.get("status") == "ready":
                    available.append(index)
            except Exception:
                continue
        if len(available) < epoch.selection.threshold.k:
            raise ClientApiError("recovery_rejected")
        selected_ids = available[: epoch.selection.threshold.k]
        if suite["id"] == APPSS_SUITE_ID:
            holders = tuple(
                holder
                for holder in self._holders(epoch.selection)
                if holder.index in selected_ids
            )
            endpoints = {
                holder.index: _RemoteAppssEndpoint(self, holder) for holder in holders
            }
            return recover_with_parties(
                context=epoch.context,
                password_input=password,
                public_state=public,
                holders=holders,
                endpoints=endpoints,
                admission_grant_digest=grant,
                client_proof_key_digest=hashlib.sha256(
                    _raw_public(self.proof_key)
                ).hexdigest(),
                operation_id=hashlib.sha256(operation_id.encode()).hexdigest(),
            )
        params_mapping = YiTpassRecoveryAdapter().decode_public_state(public)
        params = native.PublicParameters.from_bytes(
            bytes.fromhex(params_mapping["parameters"])
        )
        session = native.begin_recovery(
            params, epoch.context.recovery_id.encode(), password
        )
        request_bytes = session.request_bytes()
        session_id = secrets.token_hex(32)
        commitments = [
            bytes.fromhex(
                self._party(
                    index,
                    "/v1/yi/prepare",
                    {
                        "backup_id": epoch.reference.bid,
                        "epoch": epoch.reference.epoch,
                        "grant_digest": grant,
                        "request_hex": request_bytes.hex(),
                        "selected": selected_ids,
                        "session_id": session_id,
                    },
                )["commitment_hex"]
            )
            for index in selected_ids
        ]
        responses = [
            bytes.fromhex(
                self._party(
                    index,
                    "/v1/yi/respond",
                    {
                        "commitments": [item.hex() for item in commitments],
                        "request_hex": request_bytes.hex(),
                        "session_id": session_id,
                    },
                )["response_hex"]
            )
            for index in selected_ids
        ]
        gateway = native.aggregate_responses(
            params, request_bytes, selected_ids, commitments, responses
        )
        return bytes(native.finish_recovery(params, session, gateway))

    def recover(self, request: object) -> RecoveryResult:
        if (
            not isinstance(request, dict)
            or set(request)
            != {"api_version", "operation_id", "receipt", "recovery_input"}
            or request["api_version"] != CLIENT_API_VERSION
        ):
            raise ClientApiError("recovery_rejected")
        operation_id = str(request["operation_id"])
        if operation_id in self.operations:
            raise ClientApiError("operation_conflict")
        try:
            epoch = self._load(request["receipt"])
            canonical = self._canonical(
                epoch.context.policy_id, request["recovery_input"]
            )
            password = self._password(
                suite_id=epoch.selection.suite_id,
                context=epoch.context,
                canonical=canonical,
                nonce=bytes.fromhex(epoch.backup["nonce"]),
            )
            self._mark("authorization")
            grant = self._authorize(epoch, operation_id)
            self._mark("suite-recovery")
            secret = self._recover_secret(epoch, password, grant, operation_id)
            protected = open_backup_v6_with_secret(
                backup=epoch.backup, recovery_secret=secret
            )
            fingerprint = _fingerprint(protected)
            expected = epoch.public_fingerprint
            if fingerprint != expected:
                raise ClientApiError("recovery_rejected")
            self.operations.add(operation_id)
            return RecoveryResult(
                operation_id,
                epoch.context.recovery_id,
                epoch.reference.bid,
                epoch.reference.epoch,
                epoch.selection.suite_id,
                fingerprint,
                protected,
                (
                    "bootstrap",
                    "descriptor_verification",
                    "authorization",
                    "suite_recovery",
                    "key_decryption",
                    "completion",
                ),
            )
        except ClientApiError as exc:
            self._report_rejection("recovery_rejected", exc)
            raise
        except Exception as exc:
            self._report_rejection("recovery_rejected", exc)
            raise ClientApiError("recovery_rejected") from None

    def create_successor(self, request: object) -> SuccessorResult:
        fields = {
            "api_version",
            "operation_id",
            "receipt",
            "recovery_input",
            "rotate_protected_key",
            "successor_deployment_profile_id",
            "successor_suite_id",
        }
        if (
            not isinstance(request, dict)
            or set(request) != fields
            or request["api_version"] != CLIENT_API_VERSION
            or not isinstance(request["rotate_protected_key"], bool)
        ):
            raise ClientApiError("successor_rejected")
        operation_id = str(request["operation_id"])
        if operation_id in self.operations:
            raise ClientApiError("operation_conflict")
        try:
            predecessor = self._load(request["receipt"])
            recovery = self.recover(
                {
                    "api_version": CLIENT_API_VERSION,
                    "operation_id": f"{operation_id}:recover",
                    "receipt": request["receipt"],
                    "recovery_input": request["recovery_input"],
                }
            )
            profile = paired_profile(str(request["successor_deployment_profile_id"]))
            selection, adapter = self.suites.select_new_epoch(
                profile.selector_for(str(request["successor_suite_id"]))
            )
            canonical = self._canonical(
                predecessor.context.policy_id, request["recovery_input"]
            )
            protected = (
                random_bytes(32)
                if request["rotate_protected_key"]
                else recovery.protected_key
            )
            prepared = self._prepare_epoch(
                selection=selection,
                adapter=adapter,
                policy_id=predecessor.context.policy_id,
                resolver_profile_id=predecessor.descriptor["cue_policy"][
                    "resolver_profile"
                ],
                canonical=canonical,
                protected_key=protected,
                backup_id=bytes.fromhex(predecessor.reference.bid),
                epoch=predecessor.reference.epoch + 1,
                predecessor_digest=hashlib.sha256(
                    predecessor.bundle.descriptor_bytes
                ).hexdigest(),
                expected_pointer=predecessor.pointer_bytes,
            )
            binding = SuccessorBinding(
                operation_id=operation_id,
                backup_id=predecessor.reference.bid,
                predecessor_epoch=predecessor.reference.epoch,
                successor_epoch=prepared.reference.epoch,
                successor_configuration_digest=prepared.descriptor_payload["lifecycle"][
                    "configuration_digest"
                ],
                successor_backup_digest=hashlib.sha256(
                    prepared.backup_bytes
                ).hexdigest(),
                successor_descriptor_digest=prepared.descriptor_digest,
                recovered_key_digest=hashlib.sha256(recovery.protected_key).hexdigest(),
                rotate_protected_key=request["rotate_protected_key"],
            )
            backend = _DeployedSuccessorBackend(
                client=self,
                prepared=prepared,
                predecessor_epoch=predecessor.reference.epoch,
                predecessor_key_digest=hashlib.sha256(
                    recovery.protected_key
                ).hexdigest(),
                operation_id=operation_id,
            )
            journal_name = hashlib.sha256(operation_id.encode("ascii")).hexdigest()
            coordinator = DurableSuccessorPublication(
                Path(os.environ.get("LOCUS_INTEGRATED_JOURNAL_ROOT", "/tmp"))
                / f"successor-{journal_name}.sqlite3"
            )
            while True:
                try:
                    coordinator.run(binding, backend)
                    break
                except _InjectedIntegratedSuccessorCrash as exc:
                    if os.environ.get("LOCUS_OPERATOR_DIAGNOSTICS") == "1":
                        print(
                            json.dumps(
                                {
                                    "category": "successor_crash_resumed",
                                    "phase": str(exc),
                                    "status": "resuming",
                                },
                                sort_keys=True,
                                separators=(",", ":"),
                            ),
                            file=sys.stderr,
                            flush=True,
                        )
            enrolled = prepared.result()
            self.operations.add(operation_id)
            enrollment = EnrollmentResult(
                operation_id=operation_id,
                completed_phases=(
                    "preserve_original_key",
                    "prepare_parties",
                    "backup_publication",
                    "descriptor_publication",
                    "readiness_verification",
                    "successor_recovery_verification",
                    "successor_activation",
                    "predecessor_retirement",
                    "completion",
                ),
                **enrolled,
            )
            return SuccessorResult(
                recovery,
                enrollment,
                predecessor.reference.epoch,
                request["rotate_protected_key"],
            )
        except ClientApiError:
            raise
        except Exception:
            raise ClientApiError("successor_rejected") from None

    def inspect(self, receipt: object) -> dict[str, object]:
        try:
            epoch = self._load(receipt)
            parties = [self._party(index, "/v1/inspect", {}) for index in range(1, 6)]
            value: dict[str, object] = {
                "api_version": CLIENT_API_VERSION,
                "byte_counts": {
                    "cloud_backup": len(epoch.bundle.backup_bytes),
                    "descriptor": len(epoch.bundle.descriptor_bytes),
                    "recovery_bundle": len(epoch.bundle.bundle_bytes),
                },
                "message_categories": [
                    "bootstrap",
                    "authorization",
                    "suite_recovery",
                    "storage_gateway",
                ],
                "placements": [
                    {"items": 1, "role": "cloud-backup"},
                    *[
                        {
                            "active_epochs": item["active_epochs"],
                            "holder_id": item["holder_id"],
                            "role": f"recovery-party-{item['holder_id']}",
                        }
                        for item in parties
                    ],
                ],
                "safe_digests": {
                    "backup_sha256": hashlib.sha256(
                        epoch.bundle.backup_bytes
                    ).hexdigest(),
                    "descriptor_sha256": hashlib.sha256(
                        epoch.bundle.descriptor_bytes
                    ).hexdigest(),
                },
                "status": "active",
                "versions": {
                    "api": CLIENT_API_VERSION,
                    "backup": "LOCUS-reference-backup-v6",
                    "deployment": "LOCUS-integrated-reference-deployment-v1",
                },
            }
            validate_public_output(value)
            return value
        except Exception:
            raise ClientApiError("inspection_rejected") from None


__all__ = ["IntegratedResearchClientApi"]
