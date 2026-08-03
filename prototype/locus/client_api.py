"""P7 stable research-client API over the existing LOCUS component boundaries."""

from __future__ import annotations

import base64
import hashlib
import json
import secrets
import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
)

from .admission import RECOVERY_OPERATION, AdmissionBinding, client_key_thumbprint
from .appss_formats import (
    APPSS_SUITE_ID,
    REFERENCE_BACKUP_V6,
    YI_SUITE_ID,
    AppssHolderBinding,
    context_digest,
    derive_password_input,
)
from .codec import encode
from .contracts import PartyRecoveryState, RecoveryContext, RecoveryPhase
from .crypto import hash_scalar, random_bytes
from .cue_policy import CuePolicyError
from .cue_policy_registry import DEFAULT_CUE_POLICY_REGISTRY, CuePolicyRegistry
from .enrollment_state import (
    PHASE_ORDER as ENROLLMENT_PHASE_ORDER,
)
from .enrollment_state import (
    EnrollmentTransitionEvent,
    StableEnrollmentStateMachine,
)
from .local_admission import (
    AdmissionReplayStore,
    LocalAdmissionVerifier,
    LocalSyntheticAdmissionIssuer,
    create_client_proof,
)
from .paired_deployment_profiles import PAIRED_PROFILES, paired_profile
from .recovery_bootstrap import (
    BOOTSTRAP_PROFILE,
    RECOVERY_RECEIPT_VERSION,
    TRUST_CONFIGURATION_VERSION,
    PartyCurrentObservation,
    authenticate_recovery_bootstrap,
    create_party_current_summary,
    create_recovery_receipt,
    decode_recovery_receipt,
)
from .recovery_descriptor import (
    BACKUP_MEMBER,
    BUNDLE_PROFILE,
    configuration_digest,
    create_bundle,
    create_current_pointer,
    create_descriptor,
)
from .recovery_state import (
    PHASE_ORDER as RECOVERY_PHASE_ORDER,
)
from .recovery_state import (
    RecoveryTransitionEvent,
    StableRecoveryStateMachine,
)
from .recovery_suite_registry import RecoverySuiteRegistry, RecoverySuiteSelection
from .redaction import validate_public_output
from .suite_backup import enroll_backup_v6, recover_backup_v6

CLIENT_API_VERSION = "LOCUS-client-api-v1"
MAX_RECEIPT_BYTES = 16 * 1024
MAX_OPERATION_ID_CHARS = 128
DISCOVERY_ENDPOINT = "https://local-discovery.invalid/"
ISSUER_ID = "locus-local-research-operator"
OPERATOR_KEY_ID = "locus-local-research-root-1"
ADMISSION_ISSUER_ID = "locus-local-research-admission"
ADMISSION_KEY_ID = "locus-local-research-admission-1"


class ClientApiError(ValueError):
    """A stable privacy-safe client API failure category."""

    def __init__(self, category: str) -> None:
        self.category = category
        super().__init__(category)


@dataclass(frozen=True)
class EnrollmentResult:
    operation_id: str
    recovery_handle: str
    backup_id: str
    epoch: int
    policy_id: str
    suite_id: str
    profile_id: str
    threshold_k: int
    threshold_n: int
    public_fingerprint: str
    receipt_bytes: bytes = field(repr=False)
    completed_phases: tuple[str, ...] = ()

    def public_value(self) -> dict[str, object]:
        value: dict[str, object] = {
            "api_version": CLIENT_API_VERSION,
            "backup_id": self.backup_id,
            "completed_phases": list(self.completed_phases),
            "disposal_status": "transient-inputs-released",
            "epoch": self.epoch,
            "operation_id": self.operation_id,
            "policy_id": self.policy_id,
            "profile_id": self.profile_id,
            "public_fingerprint": self.public_fingerprint,
            "receipt": _base64url(self.receipt_bytes),
            "receipt_format": RECOVERY_RECEIPT_VERSION,
            "recovery_handle": self.recovery_handle,
            "status": "enrolled",
            "suite_id": self.suite_id,
            "threshold": {"k": self.threshold_k, "n": self.threshold_n},
        }
        validate_public_output(value)
        return value


@dataclass(frozen=True)
class BootstrapResult:
    recovery_handle: str
    backup_id: str
    epoch: int
    policy_id: str
    resolver_profile_id: str
    suite_id: str
    profile_id: str
    threshold_k: int
    threshold_n: int
    authorization_quorum: int
    public_fingerprint: str
    receipt_verified: bool

    def public_value(self) -> dict[str, object]:
        value: dict[str, object] = {
            "api_version": CLIENT_API_VERSION,
            "authorization_quorum": self.authorization_quorum,
            "backup_id": self.backup_id,
            "epoch": self.epoch,
            "policy_id": self.policy_id,
            "profile_id": self.profile_id,
            "public_fingerprint": self.public_fingerprint,
            "receipt_verified": self.receipt_verified,
            "recovery_handle": self.recovery_handle,
            "resolver_profile_id": self.resolver_profile_id,
            "status": "bootstrap_authenticated",
            "suite_id": self.suite_id,
            "threshold": {"k": self.threshold_k, "n": self.threshold_n},
        }
        validate_public_output(value)
        return value


@dataclass(frozen=True)
class RecoveryResult:
    operation_id: str
    recovery_handle: str
    backup_id: str
    epoch: int
    suite_id: str
    public_fingerprint: str
    protected_key: bytes = field(repr=False)
    completed_phases: tuple[str, ...] = ()

    def public_value(self) -> dict[str, object]:
        value: dict[str, object] = {
            "api_version": CLIENT_API_VERSION,
            "backup_id": self.backup_id,
            "completed_phases": list(self.completed_phases),
            "epoch": self.epoch,
            "key_identity_verified": True,
            "operation_id": self.operation_id,
            "public_fingerprint": self.public_fingerprint,
            "recovery_handle": self.recovery_handle,
            "status": "recovered",
            "suite_id": self.suite_id,
        }
        validate_public_output(value)
        return value


@dataclass(frozen=True)
class SuccessorResult:
    recovery: RecoveryResult = field(repr=False)
    enrollment: EnrollmentResult
    predecessor_epoch: int
    protected_key_rotated: bool

    def public_value(self) -> dict[str, object]:
        value = self.enrollment.public_value()
        value.update(
            {
                "predecessor_epoch": self.predecessor_epoch,
                "protected_key_rotated": self.protected_key_rotated,
                "status": "successor_enrolled",
            }
        )
        validate_public_output(value)
        return value


@dataclass(frozen=True)
class _EpochRecord:
    selection: RecoverySuiteSelection
    context: RecoveryContext
    backup: dict[str, Any] = field(repr=False)
    party_records: tuple[PartyRecoveryState, ...] = field(repr=False)
    descriptor_bytes: bytes = field(repr=False)
    bundle_bytes: bytes = field(repr=False)
    pointer_bytes: bytes = field(repr=False)
    trust_configuration_bytes: bytes = field(repr=False)
    receipt_bytes: bytes = field(repr=False)
    recovery_handle: str
    policy_id: str
    resolver_profile_id: str
    public_fingerprint: str
    predecessor_descriptor_digest: str | None
    active: bool = True


def _base64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _decode_base64url(value: object, *, maximum: int) -> bytes:
    if (
        not isinstance(value, str)
        or not value
        or len(value) > maximum * 2
        or "=" in value
        or any(
            character
            not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
            for character in value
        )
    ):
        raise ClientApiError("bootstrap_rejected")
    try:
        decoded = base64.b64decode(
            value + "=" * ((4 - len(value) % 4) % 4),
            altchars=b"-_",
            validate=True,
        )
    except ValueError as exc:
        raise ClientApiError("bootstrap_rejected") from exc
    if not decoded or len(decoded) > maximum:
        raise ClientApiError("bootstrap_rejected")
    return decoded


def _exact_dict(value: object, fields: set[str], category: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        raise ClientApiError(category)
    return value


def _operation_id(value: object) -> str:
    if (
        not isinstance(value, str)
        or not value
        or len(value) > MAX_OPERATION_ID_CHARS
        or not value.isascii()
        or any(ord(character) < 0x21 or ord(character) > 0x7E for character in value)
    ):
        raise ClientApiError("input_rejected")
    return value


def _raw_public_key(key: Ed25519PrivateKey) -> bytes:
    return key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )


def _public_fingerprint(protected_key: bytes) -> str:
    public_key = (
        Ed25519PrivateKey.from_private_bytes(protected_key)
        .public_key()
        .public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    )
    return hashlib.sha256(public_key).hexdigest()


class LocalResearchClientApi:
    """One-session local research facade; no cue or plaintext key is retained."""

    def __init__(
        self,
        *,
        clock: Callable[[], int] | None = None,
        policy_registry: CuePolicyRegistry = DEFAULT_CUE_POLICY_REGISTRY,
        suite_registry: RecoverySuiteRegistry | None = None,
        operator_signer: Ed25519PrivateKey | None = None,
        admission_signer: Ed25519PrivateKey | None = None,
        party_signers: Mapping[int, Ed25519PrivateKey] | None = None,
    ) -> None:
        self._clock = (lambda: int(time.time())) if clock is None else clock
        self._policies = policy_registry
        self._suites = (
            RecoverySuiteRegistry() if suite_registry is None else suite_registry
        )
        self._operator_signer = (
            Ed25519PrivateKey.generate() if operator_signer is None else operator_signer
        )
        self._admission_signer = (
            Ed25519PrivateKey.generate()
            if admission_signer is None
            else admission_signer
        )
        self._party_signers = (
            {party_id: Ed25519PrivateKey.generate() for party_id in range(1, 6)}
            if party_signers is None
            else dict(party_signers)
        )
        if set(self._party_signers) != set(range(1, 6)):
            raise ValueError("exactly five party signers are required")
        self._subject_id = hashlib.sha256(
            b"LOCUS local research synthetic subject v1"
        ).hexdigest()
        self._records: dict[str, _EpochRecord] = {}
        self._enrollment_operations: set[str] = set()
        self._recovery_operations: set[str] = set()
        self._enrollment_states = StableEnrollmentStateMachine()
        self._recovery_states = StableRecoveryStateMachine()
        self._lock = threading.RLock()

    def catalog(self) -> dict[str, object]:
        policy_labels = {
            "LOCUS-canonical-email-set-v1": "Three canonical email addresses",
            "LOCUS-canonical-phone-set-v1": "Three canonical phone numbers",
            "LOCUS-location-person-set-v1": "Three location and person pairs",
            "LOCUS-quantized-coordinate-set-v1": "Three quantized coordinates",
        }
        value: dict[str, object] = {
            "api_version": CLIENT_API_VERSION,
            "policies": [
                {
                    "cardinality": self._policies.require(
                        policy_id
                    ).metadata.cardinality,
                    "input_category": self._policies.require(
                        policy_id
                    ).metadata.input_category,
                    "label": policy_labels[policy_id],
                    "policy_id": policy_id,
                    "resolver_profile_id": self._policies.require(
                        policy_id
                    ).metadata.resolver_profile_id,
                }
                for policy_id in self._policies.policy_ids
            ],
            "profiles": [
                {
                    "authorization_quorum": profile.authorization_quorum,
                    "label": f"{profile.threshold.k}-of-{profile.threshold.n} holders",
                    "profile_id": profile.profile_id,
                    "threshold": {
                        "k": profile.threshold.k,
                        "n": profile.threshold.n,
                    },
                }
                for profile in PAIRED_PROFILES.values()
            ],
            "status": "ready",
            "suites": [
                {"label": "Augmented PPSS", "suite_id": APPSS_SUITE_ID},
                {"label": "Yi TPASS", "suite_id": YI_SUITE_ID},
            ],
        }
        validate_public_output(value)
        return value

    def preview_policy(self, request: object) -> dict[str, object]:
        parsed = _exact_dict(
            request,
            {"api_version", "policy_id", "recovery_input"},
            "input_rejected",
        )
        if parsed["api_version"] != CLIENT_API_VERSION:
            raise ClientApiError("input_rejected")
        try:
            policy = self._policies.require(parsed["policy_id"])
            result = policy.process(parsed["recovery_input"])
            normalized = json.loads(result.canonical_bytes)
        except (CuePolicyError, TypeError, ValueError):
            raise ClientApiError("input_rejected") from None
        # This response is transient active-client UI data. The HTTP layer marks
        # it no-store and never sends it through normal logs or retained output.
        return {
            "api_version": CLIENT_API_VERSION,
            "normalized_preview": normalized,
            "policy_id": policy.policy_id,
            "status": "input_validated",
        }

    def enroll(self, request: object) -> EnrollmentResult:
        parsed = _exact_dict(
            request,
            {
                "api_version",
                "deployment_profile_id",
                "operation_id",
                "policy_id",
                "protected_key",
                "recovery_input",
                "suite_id",
            },
            "input_rejected",
        )
        if parsed["api_version"] != CLIENT_API_VERSION:
            raise ClientApiError("input_rejected")
        operation_id = _operation_id(parsed["operation_id"])
        with self._lock:
            if operation_id in self._enrollment_operations:
                raise ClientApiError("operation_conflict")
            try:
                policy = self._policies.require(parsed["policy_id"])
                policy_result = policy.process(parsed["recovery_input"])
                profile = paired_profile(parsed["deployment_profile_id"])
                selector = profile.selector_for(parsed["suite_id"])
                selection, adapter = self._suites.select_new_epoch(selector)
                profile.validate_selection(selection)
                protected_key = self._protected_key(parsed["protected_key"])
                record = self._create_record(
                    selection=selection,
                    adapter=adapter,
                    policy_id=policy.policy_id,
                    resolver_profile_id=policy.metadata.resolver_profile_id,
                    canonical_input=policy_result.canonical_bytes,
                    protected_key=protected_key,
                    backup_id=random_bytes(16),
                    epoch=1,
                    predecessor_descriptor_digest=None,
                )
                self._records[record.recovery_handle] = record
                phases = self._complete_enrollment_state(
                    operation_id, record.context.backup_id, record.context.epoch
                )
                self._enrollment_operations.add(operation_id)
                return EnrollmentResult(
                    operation_id=operation_id,
                    recovery_handle=record.recovery_handle,
                    backup_id=record.context.backup_id,
                    epoch=record.context.epoch,
                    policy_id=record.policy_id,
                    suite_id=selection.suite_id,
                    profile_id=selection.profile_id,
                    threshold_k=selection.threshold.k,
                    threshold_n=selection.threshold.n,
                    public_fingerprint=record.public_fingerprint,
                    receipt_bytes=record.receipt_bytes,
                    completed_phases=phases,
                )
            except ClientApiError:
                raise
            except Exception:
                raise ClientApiError("enrollment_rejected") from None

    def bootstrap(self, receipt: object) -> BootstrapResult:
        with self._lock:
            try:
                record, result = self._authenticate_receipt(receipt)
                suite_payload = result.bundle.descriptor["payload"]["recovery_suite"]
                if suite_payload["id"] != record.selection.suite_id or suite_payload[
                    "threshold"
                ] != {
                    "k": record.selection.threshold.k,
                    "n": record.selection.threshold.n,
                }:
                    raise ClientApiError("bootstrap_rejected")
                return BootstrapResult(
                    recovery_handle=record.recovery_handle,
                    backup_id=record.context.backup_id,
                    epoch=record.context.epoch,
                    policy_id=record.policy_id,
                    resolver_profile_id=record.resolver_profile_id,
                    suite_id=record.selection.suite_id,
                    profile_id=record.selection.profile_id,
                    threshold_k=record.selection.threshold.k,
                    threshold_n=record.selection.threshold.n,
                    authorization_quorum=record.selection.authorization_quorum,
                    public_fingerprint=record.public_fingerprint,
                    receipt_verified=result.receipt_verified,
                )
            except ClientApiError:
                raise
            except Exception:
                raise ClientApiError("bootstrap_rejected") from None

    def recover(self, request: object) -> RecoveryResult:
        parsed = _exact_dict(
            request,
            {"api_version", "operation_id", "receipt", "recovery_input"},
            "recovery_rejected",
        )
        if parsed["api_version"] != CLIENT_API_VERSION:
            raise ClientApiError("recovery_rejected")
        operation_id = _operation_id(parsed["operation_id"])
        with self._lock:
            if operation_id in self._recovery_operations:
                raise ClientApiError("operation_conflict")
            try:
                record, bootstrap_result = self._authenticate_receipt(parsed["receipt"])
                if not record.active:
                    raise ClientApiError("recovery_rejected")
                policy = self._policies.require(
                    bootstrap_result.bundle.descriptor["payload"]["cue_policy"]["id"]
                )
                policy_result = policy.process(parsed["recovery_input"])
                self._authorize_recovery(record, operation_id)
                adapter = self._suites.for_authenticated_descriptor(
                    bootstrap_result.bundle.descriptor["payload"]["recovery_suite"][
                        "id"
                    ]
                )
                protected_key = recover_backup_v6(
                    backup=record.backup,
                    context=record.context,
                    password_input=self._password_input(
                        record=record,
                        canonical_input=policy_result.canonical_bytes,
                    ),
                    adapter=adapter,
                    party_states=record.party_records[: record.selection.threshold.k],
                )
                public_fingerprint = _public_fingerprint(protected_key)
                if public_fingerprint != record.public_fingerprint:
                    raise ClientApiError("recovery_rejected")
                phases = self._complete_recovery_state(
                    operation_id,
                    record.recovery_handle,
                    record.context.backup_id,
                    record.context.epoch,
                )
                self._recovery_operations.add(operation_id)
                return RecoveryResult(
                    operation_id=operation_id,
                    recovery_handle=record.recovery_handle,
                    backup_id=record.context.backup_id,
                    epoch=record.context.epoch,
                    suite_id=record.selection.suite_id,
                    public_fingerprint=public_fingerprint,
                    protected_key=protected_key,
                    completed_phases=phases,
                )
            except ClientApiError:
                raise
            except Exception:
                raise ClientApiError("recovery_rejected") from None

    def create_successor(self, request: object) -> SuccessorResult:
        parsed = _exact_dict(
            request,
            {
                "api_version",
                "operation_id",
                "receipt",
                "recovery_input",
                "rotate_protected_key",
                "successor_deployment_profile_id",
                "successor_suite_id",
            },
            "successor_rejected",
        )
        if parsed["api_version"] != CLIENT_API_VERSION or not isinstance(
            parsed["rotate_protected_key"], bool
        ):
            raise ClientApiError("successor_rejected")
        operation_id = _operation_id(parsed["operation_id"])
        with self._lock:
            try:
                predecessor, _bootstrap = self._authenticate_receipt(parsed["receipt"])
                if not predecessor.active:
                    raise ClientApiError("successor_rejected")
                recovery = self.recover(
                    {
                        "api_version": CLIENT_API_VERSION,
                        "operation_id": f"{operation_id}:recover",
                        "receipt": parsed["receipt"],
                        "recovery_input": parsed["recovery_input"],
                    }
                )
                policy = self._policies.require(predecessor.policy_id)
                policy_result = policy.process(parsed["recovery_input"])
                profile = paired_profile(parsed["successor_deployment_profile_id"])
                selector = profile.selector_for(parsed["successor_suite_id"])
                selection, adapter = self._suites.select_new_epoch(selector)
                profile.validate_selection(selection)
                protected_key = (
                    random_bytes(32)
                    if parsed["rotate_protected_key"]
                    else recovery.protected_key
                )
                successor = self._create_record(
                    selection=selection,
                    adapter=adapter,
                    policy_id=predecessor.policy_id,
                    resolver_profile_id=predecessor.resolver_profile_id,
                    canonical_input=policy_result.canonical_bytes,
                    protected_key=protected_key,
                    backup_id=bytes.fromhex(predecessor.context.backup_id),
                    epoch=predecessor.context.epoch + 1,
                    predecessor_descriptor_digest=hashlib.sha256(
                        predecessor.descriptor_bytes
                    ).hexdigest(),
                )
                self._records[successor.recovery_handle] = successor
                predecessor_key = predecessor.recovery_handle
                self._records[predecessor_key] = _EpochRecord(
                    **{**predecessor.__dict__, "active": False}
                )
                phases = self._complete_enrollment_state(
                    operation_id,
                    successor.context.backup_id,
                    successor.context.epoch,
                )
                enrollment = EnrollmentResult(
                    operation_id=operation_id,
                    recovery_handle=successor.recovery_handle,
                    backup_id=successor.context.backup_id,
                    epoch=successor.context.epoch,
                    policy_id=successor.policy_id,
                    suite_id=successor.selection.suite_id,
                    profile_id=successor.selection.profile_id,
                    threshold_k=successor.selection.threshold.k,
                    threshold_n=successor.selection.threshold.n,
                    public_fingerprint=successor.public_fingerprint,
                    receipt_bytes=successor.receipt_bytes,
                    completed_phases=phases,
                )
                self._enrollment_operations.add(operation_id)
                return SuccessorResult(
                    recovery=recovery,
                    enrollment=enrollment,
                    predecessor_epoch=predecessor.context.epoch,
                    protected_key_rotated=parsed["rotate_protected_key"],
                )
            except ClientApiError:
                raise
            except Exception:
                raise ClientApiError("successor_rejected") from None

    def inspect(self, receipt: object) -> dict[str, object]:
        with self._lock:
            try:
                record, _result = self._authenticate_receipt(receipt)
            except Exception:
                raise ClientApiError("inspection_rejected") from None
            backup_bytes = encode(record.backup)
            party_bytes = [len(item.payload) for item in record.party_records]
            value: dict[str, object] = {
                "api_version": CLIENT_API_VERSION,
                "byte_counts": {
                    "cloud_backup": len(backup_bytes),
                    "descriptor": len(record.descriptor_bytes),
                    "party_records_total": sum(party_bytes),
                    "recovery_bundle": len(record.bundle_bytes),
                },
                "message_categories": [
                    "bootstrap",
                    "authorization",
                    "suite_recovery",
                    "key_identity",
                ],
                "public_identifiers": {
                    "backup_id": record.context.backup_id,
                    "epoch": record.context.epoch,
                    "policy_id": record.policy_id,
                    "recovery_handle": record.recovery_handle,
                    "suite_id": record.selection.suite_id,
                },
                "role_placement": [
                    {
                        "bytes": len(backup_bytes),
                        "items": 1,
                        "role": "cloud-backup",
                    },
                    {
                        "bytes": len(record.descriptor_bytes)
                        + len(record.pointer_bytes)
                        + len(record.bundle_bytes),
                        "items": 3,
                        "role": "descriptor-and-bundle",
                    },
                    *[
                        {
                            "bytes": size,
                            "items": 1,
                            "role": f"recovery-party-{index}",
                        }
                        for index, size in enumerate(party_bytes, start=1)
                    ],
                ],
                "safe_digests": {
                    "backup_sha256": hashlib.sha256(backup_bytes).hexdigest(),
                    "descriptor_sha256": hashlib.sha256(
                        record.descriptor_bytes
                    ).hexdigest(),
                },
                "status": "active" if record.active else "retired",
                "versions": {
                    "api": CLIENT_API_VERSION,
                    "backup": REFERENCE_BACKUP_V6,
                    "receipt": RECOVERY_RECEIPT_VERSION,
                },
            }
            validate_public_output(value)
            return value

    def _protected_key(self, value: object) -> bytes:
        parsed = _exact_dict(value, {"hex", "mode"}, "input_rejected")
        if parsed["mode"] == "generate-synthetic" and parsed["hex"] is None:
            return random_bytes(32)
        if parsed["mode"] != "import-synthetic" or not isinstance(parsed["hex"], str):
            raise ClientApiError("input_rejected")
        encoded = parsed["hex"]
        if len(encoded) != 64 or any(c not in "0123456789abcdef" for c in encoded):
            raise ClientApiError("input_rejected")
        result = bytes.fromhex(encoded)
        Ed25519PrivateKey.from_private_bytes(result)
        return result

    def _holder_bindings(
        self, selection: RecoverySuiteSelection
    ) -> tuple[AppssHolderBinding, ...]:
        return tuple(
            AppssHolderBinding(
                index=holder_id,
                party_id=f"party-{holder_id}",
                service_identity="spki-sha256:"
                + hashlib.sha256(f"party-{holder_id}".encode("ascii")).hexdigest(),
            )
            for holder_id in selection.holder_ids
        )

    def _create_record(
        self,
        *,
        selection: RecoverySuiteSelection,
        adapter: Any,
        policy_id: str,
        resolver_profile_id: str,
        canonical_input: bytes,
        protected_key: bytes,
        backup_id: bytes,
        epoch: int,
        predecessor_descriptor_digest: str | None,
    ) -> _EpochRecord:
        now = self._clock()
        if now < 2:
            raise ClientApiError("enrollment_rejected")
        nonce = random_bytes(16)
        recovery_handle = f"local-recovery:{backup_id.hex()}:{epoch}"
        public_configuration_digest = hashlib.sha256(
            encode(
                {
                    "api_version": CLIENT_API_VERSION,
                    "authorization_quorum": selection.authorization_quorum,
                    "backup_id": backup_id.hex(),
                    "epoch": epoch,
                    "holder_ids": list(selection.holder_ids),
                    "policy_id": policy_id,
                    "profile_id": selection.profile_id,
                    "suite_id": selection.suite_id,
                }
            )
        ).digest()
        holders = self._holder_bindings(selection)
        suite_context = (
            context_digest(
                backup_id=backup_id,
                epoch=epoch,
                policy_id=policy_id,
                holders=holders,
                k=selection.threshold.k,
                n=selection.threshold.n,
                configuration_digest=public_configuration_digest,
            )
            if selection.suite_id == APPSS_SUITE_ID
            else public_configuration_digest
        )
        context = RecoveryContext(
            suite_id=selection.suite_id,
            recovery_id=recovery_handle,
            backup_id=backup_id.hex(),
            epoch=epoch,
            policy_id=policy_id,
            configuration_digest=public_configuration_digest.hex(),
            digest_context=f"client-api:{backup_id.hex()}:{epoch}",
            suite_context_digest=suite_context.hex(),
        )
        password_input = self._password_input_parts(
            suite_id=selection.suite_id,
            context=context,
            canonical_input=canonical_input,
            nonce=nonce,
        )
        enrollment = adapter.initialize(
            context=context,
            password_input=password_input,
            threshold=selection.threshold,
        )
        backup_enrollment = enroll_backup_v6(
            protected_key=protected_key,
            context=context,
            cue_policy_id=policy_id,
            resolver_profile=resolver_profile_id,
            adapter=adapter,
            enrollment=enrollment,
            profile_id=selection.profile_id,
            threshold=selection.threshold,
            bid=backup_id,
            nonce=nonce,
        )
        backup_bytes = encode(backup_enrollment.backup)
        descriptor_payload: dict[str, Any] = {
            "authorization": {
                "admission_profile": "LOCUS-local-synthetic-admission-v1",
                "audience": "locus-recovery",
                "authorizers": [
                    {
                        "authorizer_id": authorizer_id,
                        "endpoint": f"https://party-{authorizer_id}.invalid/",
                        "identity_key_id": f"local-party-key-{authorizer_id}",
                    }
                    for authorizer_id in selection.authorizer_ids
                ],
                "operation_namespace": "locus-recovery",
                "quorum": selection.authorization_quorum,
                "security_policy": "LOCUS-security-policy-v1",
            },
            "backup": {
                "format": REFERENCE_BACKUP_V6,
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
            "issuer": ISSUER_ID,
            "lifecycle": {
                "configuration_digest": "00" * 32,
                "predecessor_descriptor_digest": predecessor_descriptor_digest,
            },
            "recovery_id": recovery_handle,
            "recovery_suite": {
                "holders": [
                    {"authorizer_id": holder_id, "holder_id": holder_id}
                    for holder_id in selection.holder_ids
                ],
                "id": selection.suite_id,
                "public_state_format": enrollment.public_state.format_id,
                "public_state_hex": enrollment.public_state.payload.hex(),
                "threshold": {
                    "k": selection.threshold.k,
                    "n": selection.threshold.n,
                },
            },
            "subject_id": self._subject_id,
        }
        descriptor_payload["lifecycle"]["configuration_digest"] = configuration_digest(
            descriptor_payload
        )
        descriptor_bytes = create_descriptor(
            descriptor_payload,
            signer=self._operator_signer,
            key_id=OPERATOR_KEY_ID,
        )
        bundle_bytes = create_bundle(
            backup_bytes=backup_bytes,
            descriptor_bytes=descriptor_bytes,
            backup_format=REFERENCE_BACKUP_V6,
        )
        pointer_bytes = create_current_pointer(
            {
                "backup_id": backup_id.hex(),
                "bundle": {
                    "length": len(bundle_bytes),
                    "locator": f"local-ui-bundle:{hashlib.sha256(bundle_bytes).hexdigest()}",
                    "profile": BUNDLE_PROFILE,
                    "sha256": hashlib.sha256(bundle_bytes).hexdigest(),
                },
                "configuration_digest": descriptor_payload["lifecycle"][
                    "configuration_digest"
                ],
                "descriptor_sha256": hashlib.sha256(descriptor_bytes).hexdigest(),
                "epoch": epoch,
                "expires_at": now + 86_400,
                "issued_at": now,
                "issuer": ISSUER_ID,
                "subject_id": self._subject_id,
            },
            signer=self._operator_signer,
            key_id=OPERATOR_KEY_ID,
        )
        trust_configuration_bytes = encode(
            {
                "discovery": {
                    "audience": "locus-storage-gateway",
                    "endpoint": DISCOVERY_ENDPOINT,
                },
                "generation": 1,
                "operator": {
                    "issuer": ISSUER_ID,
                    "key_id": OPERATOR_KEY_ID,
                    "public_key_hex": _raw_public_key(self._operator_signer).hex(),
                },
                "parties": [
                    {
                        "authorizer_id": party_id,
                        "endpoint": f"https://party-{party_id}.invalid/",
                        "identity_key_id": f"local-party-key-{party_id}",
                        "public_key_hex": _raw_public_key(
                            self._party_signers[party_id]
                        ).hex(),
                    }
                    for party_id in range(1, 6)
                ],
                "previous_configuration_sha256": None,
                "profile": BOOTSTRAP_PROFILE,
                "valid_from": now - 1,
                "valid_until": now + 86_400,
                "version": TRUST_CONFIGURATION_VERSION,
            }
        )
        receipt_bytes = create_recovery_receipt(
            {
                "discovery_endpoint": DISCOVERY_ENDPOINT,
                "discovery_profile": BOOTSTRAP_PROFILE,
                "initial": {
                    "backup_id": backup_id.hex(),
                    "configuration_digest": descriptor_payload["lifecycle"][
                        "configuration_digest"
                    ],
                    "descriptor_sha256": hashlib.sha256(descriptor_bytes).hexdigest(),
                    "epoch": epoch,
                },
                "issued_at": now,
                "issuer": ISSUER_ID,
                "operator_key_id": OPERATOR_KEY_ID,
                "recovery_handle": recovery_handle,
                "subject_id": self._subject_id,
            },
            signer=self._operator_signer,
            key_id=OPERATOR_KEY_ID,
        )
        return _EpochRecord(
            selection=selection,
            context=context,
            backup=backup_enrollment.backup,
            party_records=backup_enrollment.party_states,
            descriptor_bytes=descriptor_bytes,
            bundle_bytes=bundle_bytes,
            pointer_bytes=pointer_bytes,
            trust_configuration_bytes=trust_configuration_bytes,
            receipt_bytes=receipt_bytes,
            recovery_handle=recovery_handle,
            policy_id=policy_id,
            resolver_profile_id=resolver_profile_id,
            public_fingerprint=_public_fingerprint(protected_key),
            predecessor_descriptor_digest=predecessor_descriptor_digest,
        )

    def _password_input(self, *, record: _EpochRecord, canonical_input: bytes) -> bytes:
        return self._password_input_parts(
            suite_id=record.selection.suite_id,
            context=record.context,
            canonical_input=canonical_input,
            nonce=bytes.fromhex(record.backup["nonce"]),
        )

    @staticmethod
    def _password_input_parts(
        *,
        suite_id: str,
        context: RecoveryContext,
        canonical_input: bytes,
        nonce: bytes,
    ) -> bytes:
        if suite_id == APPSS_SUITE_ID:
            return derive_password_input(
                bytes.fromhex(context.suite_context_digest or ""), canonical_input
            )
        if suite_id == YI_SUITE_ID:
            return hash_scalar(
                "LOCUS-context-password",
                canonical_input,
                nonce,
                context.backup_id,
                context.epoch,
            ).to_bytes(32, "big")
        raise ClientApiError("recovery_rejected")

    def _authenticate_receipt(self, receipt: object) -> tuple[_EpochRecord, Any]:
        receipt_bytes = _decode_base64url(receipt, maximum=MAX_RECEIPT_BYTES)
        decoded = decode_recovery_receipt(
            receipt_bytes,
            issuer_public_key=self._operator_signer.public_key(),
            expected_issuer=ISSUER_ID,
            expected_key_id=OPERATOR_KEY_ID,
        )
        recovery_handle = decoded["payload"]["recovery_handle"]
        record = self._records.get(recovery_handle)
        if record is None or receipt_bytes != record.receipt_bytes:
            raise ClientApiError("bootstrap_rejected")
        now = self._clock()
        result = authenticate_recovery_bootstrap(
            trust_configuration_bytes=record.trust_configuration_bytes,
            discovery_endpoint=DISCOVERY_ENDPOINT,
            recovery_handle=record.recovery_handle,
            expected_subject_id=self._subject_id,
            current_pointer_bytes=record.pointer_bytes,
            bundle_bytes=record.bundle_bytes,
            current_state_observations=self._current_observations(record, now),
            now=now,
            receipt_bytes=record.receipt_bytes,
        )
        return record, result

    def _current_observations(
        self, record: _EpochRecord, now: int
    ) -> list[PartyCurrentObservation]:
        descriptor_digest = hashlib.sha256(record.descriptor_bytes).hexdigest()
        configuration = json.loads(record.descriptor_bytes)["payload"]["lifecycle"][
            "configuration_digest"
        ]
        return [
            PartyCurrentObservation(
                authorizer_id=party_id,
                endpoint=f"https://party-{party_id}.invalid/",
                summary_bytes=create_party_current_summary(
                    {
                        "authorizer_id": party_id,
                        "backup_id": record.context.backup_id,
                        "configuration_digest": configuration,
                        "cue_policy_id": record.policy_id,
                        "descriptor_sha256": descriptor_digest,
                        "epoch": record.context.epoch,
                        "expires_at": now + 120,
                        "issued_at": now - 1,
                        "recovery_id": record.context.recovery_id,
                        "recovery_suite_id": record.selection.suite_id,
                        "state": "active" if record.active else "retired",
                        "subject_id": self._subject_id,
                    },
                    signer=self._party_signers[party_id],
                    key_id=f"local-party-key-{party_id}",
                ),
            )
            for party_id in range(1, 6)
        ]

    def _authorize_recovery(self, record: _EpochRecord, operation_id: str) -> None:
        now = self._clock()
        client_key = Ed25519PrivateKey.generate()
        binding = AdmissionBinding(
            subject=self._subject_id,
            backup_id=record.context.backup_id,
            epoch=record.context.epoch,
            operation=RECOVERY_OPERATION,
            audience="locus-recovery",
            client_key_thumbprint=client_key_thumbprint(_raw_public_key(client_key)),
            nonce=secrets.token_hex(32),
            issued_at=now,
            expires_at=now + 120,
            issuer=ADMISSION_ISSUER_ID,
        )
        issuer = LocalSyntheticAdmissionIssuer(
            issuer=ADMISSION_ISSUER_ID,
            key_id=ADMISSION_KEY_ID,
            private_key=self._admission_signer,
            allowed_subjects=frozenset({self._subject_id}),
        )
        capability = issuer.issue(binding)
        admitted_request = encode(
            {
                "backup_id": record.context.backup_id,
                "epoch": record.context.epoch,
                "operation_id": operation_id,
                "recovery_handle": record.recovery_handle,
            }
        )
        proof = create_client_proof(capability, client_key, admitted_request)
        replay = AdmissionReplayStore(":memory:")
        verifier = LocalAdmissionVerifier(
            issuer=ADMISSION_ISSUER_ID,
            issuer_key_id=ADMISSION_KEY_ID,
            issuer_public_key=issuer.public_key,
            replay_store=replay,
        )
        try:
            verifier.verify(
                capability,
                binding,
                proof,
                admitted_request,
                now=now,
            )
        finally:
            replay.close()

    def _complete_enrollment_state(
        self, operation_id: str, backup_id: str, epoch: int
    ) -> tuple[str, ...]:
        state = self._enrollment_states.begin(operation_id)
        completed: list[str] = []
        for phase in ENROLLMENT_PHASE_ORDER[:-1]:
            state = self._enrollment_states.advance(
                state,
                EnrollmentTransitionEvent(
                    event_id=f"{operation_id}:{phase.value}",
                    completed_phase=phase,
                    backup_id=(
                        backup_id if phase.value == "backup_publication" else None
                    ),
                    epoch=(epoch if phase.value == "backup_publication" else None),
                ),
            )
            completed.append(phase.value)
        return tuple(completed)

    def _complete_recovery_state(
        self, operation_id: str, recovery_handle: str, backup_id: str, epoch: int
    ) -> tuple[str, ...]:
        state = self._recovery_states.begin(operation_id, recovery_handle)
        completed: list[str] = []
        for phase in RECOVERY_PHASE_ORDER[:-1]:
            state = self._recovery_states.advance(
                state,
                RecoveryTransitionEvent(
                    event_id=f"{operation_id}:{phase.value}",
                    completed_phase=phase,
                    backup_id=(
                        backup_id
                        if phase is RecoveryPhase.DESCRIPTOR_VERIFICATION
                        else None
                    ),
                    epoch=(
                        epoch
                        if phase is RecoveryPhase.DESCRIPTOR_VERIFICATION
                        else None
                    ),
                ),
            )
            completed.append(phase.value)
        return tuple(completed)


def public_failure(error: BaseException) -> dict[str, object]:
    category = (
        error.category if isinstance(error, ClientApiError) else "operation_rejected"
    )
    value: dict[str, object] = {
        "api_version": CLIENT_API_VERSION,
        "category": category,
        "status": "rejected",
    }
    validate_public_output(value)
    return value


__all__ = [
    "CLIENT_API_VERSION",
    "BootstrapResult",
    "ClientApiError",
    "EnrollmentResult",
    "LocalResearchClientApi",
    "RecoveryResult",
    "SuccessorResult",
    "public_failure",
]
