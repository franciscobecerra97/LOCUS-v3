"""Typed, suite-neutral contracts for the LOCUS improvement architecture.

These are in-memory interface types, not newly assigned protocol or wire
identifiers. Concrete formats remain owned by their adapters and must pass the
version gates in ``VERSION-REGISTRY.md`` before external serialization.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import ClassVar, Protocol, runtime_checkable

from .object_store import BackupObjectStore, BackupReference

MAX_OPAQUE_PUBLIC_BYTES = 1024 * 1024
MAX_OPAQUE_SECRET_STATE_BYTES = 1024 * 1024
MAX_OPAQUE_MESSAGE_BYTES = 256 * 1024
MAX_OPAQUE_CAPABILITY_BYTES = 64 * 1024
MAX_IDENTIFIER_CHARS = 255
MAX_EPOCH = 2**63 - 1
MAX_PARTIES = 65535


class ContractError(ValueError):
    """An in-memory contract value violates its public type boundary."""


def _identifier(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or len(value) > MAX_IDENTIFIER_CHARS
        or not value.isascii()
        or any(ord(character) < 0x21 or ord(character) > 0x7E for character in value)
    ):
        raise ContractError(f"invalid {label}")
    return value


def _positive_int(value: object, label: str, *, maximum: int = MAX_EPOCH) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < 1
        or value > maximum
    ):
        raise ContractError(f"invalid {label}")
    return value


def _opaque_bytes(value: object, label: str, *, maximum: int) -> bytes:
    if not isinstance(value, bytes) or not value or len(value) > maximum:
        raise ContractError(f"invalid {label}")
    return value


@dataclass(frozen=True)
class ThresholdParameters:
    """Typed recovery threshold; never an authorization quorum."""

    k: int
    n: int

    def __post_init__(self) -> None:
        _positive_int(self.k, "reconstruction threshold", maximum=MAX_PARTIES)
        _positive_int(self.n, "recovery party count", maximum=MAX_PARTIES)
        if self.k > self.n:
            raise ContractError("reconstruction threshold exceeds party count")


@dataclass(frozen=True)
class RecoveryContext:
    """Public context binding one recovery-suite epoch."""

    suite_id: str
    recovery_id: str
    backup_id: str
    epoch: int
    policy_id: str
    configuration_digest: str
    digest_context: str

    def __post_init__(self) -> None:
        _identifier(self.suite_id, "recovery suite identifier")
        _identifier(self.recovery_id, "recovery identifier")
        _identifier(self.backup_id, "backup identifier")
        _positive_int(self.epoch, "recovery epoch")
        _identifier(self.policy_id, "CuePolicy identifier")
        _identifier(self.configuration_digest, "configuration digest")
        _identifier(self.digest_context, "digest context")


@dataclass(frozen=True)
class PublicRecoveryState:
    suite_id: str
    format_id: str
    payload: bytes = field(repr=False)

    def __post_init__(self) -> None:
        _identifier(self.suite_id, "recovery suite identifier")
        _identifier(self.format_id, "public-state format")
        _opaque_bytes(
            self.payload, "public recovery state", maximum=MAX_OPAQUE_PUBLIC_BYTES
        )


@dataclass(frozen=True)
class PartyRecoveryState:
    suite_id: str
    format_id: str
    holder_id: int
    payload: bytes = field(repr=False)

    def __post_init__(self) -> None:
        _identifier(self.suite_id, "recovery suite identifier")
        _identifier(self.format_id, "party-state format")
        _positive_int(self.holder_id, "recovery holder identifier", maximum=MAX_PARTIES)
        _opaque_bytes(
            self.payload,
            "party recovery state",
            maximum=MAX_OPAQUE_SECRET_STATE_BYTES,
        )


@dataclass(frozen=True)
class RecoveryRequest:
    suite_id: str
    format_id: str
    session_id: str
    recipient_id: int
    payload: bytes = field(repr=False)

    def __post_init__(self) -> None:
        _identifier(self.suite_id, "recovery suite identifier")
        _identifier(self.format_id, "request format")
        _identifier(self.session_id, "recovery session identifier")
        _positive_int(self.recipient_id, "request recipient", maximum=MAX_PARTIES)
        _opaque_bytes(
            self.payload, "recovery request", maximum=MAX_OPAQUE_MESSAGE_BYTES
        )


@dataclass(frozen=True)
class RecoveryResponse:
    suite_id: str
    format_id: str
    session_id: str
    sender_id: int
    payload: bytes = field(repr=False)

    def __post_init__(self) -> None:
        _identifier(self.suite_id, "recovery suite identifier")
        _identifier(self.format_id, "response format")
        _identifier(self.session_id, "recovery session identifier")
        _positive_int(self.sender_id, "response sender", maximum=MAX_PARTIES)
        _opaque_bytes(
            self.payload, "recovery response", maximum=MAX_OPAQUE_MESSAGE_BYTES
        )


@dataclass(frozen=True)
class RecoveryClientSession:
    """Opaque transient client state with an intentionally redacted repr."""

    suite_id: str
    format_id: str
    session_id: str
    payload: object = field(repr=False, compare=False)

    def __post_init__(self) -> None:
        _identifier(self.suite_id, "recovery suite identifier")
        _identifier(self.format_id, "client-session format")
        _identifier(self.session_id, "recovery session identifier")
        if self.payload is None:
            raise ContractError("invalid client session")


@dataclass(frozen=True)
class RecoverySuiteEnrollment:
    public_state: PublicRecoveryState
    party_states: tuple[PartyRecoveryState, ...]
    recovery_secret: bytes = field(repr=False)

    def __post_init__(self) -> None:
        if not self.party_states:
            raise ContractError("recovery enrollment has no party state")
        holder_ids = [state.holder_id for state in self.party_states]
        if holder_ids != sorted(set(holder_ids)):
            raise ContractError("recovery holder identifiers are not canonical")
        if any(
            state.suite_id != self.public_state.suite_id for state in self.party_states
        ):
            raise ContractError("recovery enrollment mixes suites")
        if not isinstance(self.recovery_secret, bytes) or not self.recovery_secret:
            raise ContractError("invalid recovery secret")


@runtime_checkable
class PasswordProtectedSecretRecovery(Protocol):
    """Suite-neutral setup/recovery boundary.

    A transport-aware adapter may additionally use ``RecoveryRequest``,
    ``RecoveryResponse``, and ``RecoveryClientSession``. Those types are
    deliberately distinct even while the frozen Yi compatibility adapter keeps
    using its existing one-shot orchestration.
    """

    suite_id: str
    public_state_format: str
    party_state_format: str
    request_type: ClassVar[type[RecoveryRequest]]
    response_type: ClassVar[type[RecoveryResponse]]
    client_session_type: ClassVar[type[RecoveryClientSession]]

    def initialize(
        self,
        *,
        context: RecoveryContext,
        password_input: bytes,
        threshold: ThresholdParameters,
    ) -> RecoverySuiteEnrollment: ...

    def recover(
        self,
        *,
        context: RecoveryContext,
        password_input: bytes,
        public_state: PublicRecoveryState,
        party_states: tuple[PartyRecoveryState, ...],
    ) -> bytes: ...


@dataclass(frozen=True)
class CuePolicyResult:
    policy_id: str
    canonical_bytes: bytes = field(repr=False)

    def __post_init__(self) -> None:
        _identifier(self.policy_id, "CuePolicy identifier")
        _opaque_bytes(
            self.canonical_bytes,
            "canonical CuePolicy output",
            maximum=MAX_OPAQUE_PUBLIC_BYTES,
        )


@runtime_checkable
class CuePolicy(Protocol):
    policy_id: str

    def process(self, recovery_input: object) -> CuePolicyResult: ...


@dataclass(frozen=True)
class ResolverResult:
    resolver_profile: str
    policy_id: str
    canonical_bytes: bytes = field(repr=False)

    def __post_init__(self) -> None:
        _identifier(self.resolver_profile, "resolver profile")
        _identifier(self.policy_id, "CuePolicy identifier")
        _opaque_bytes(
            self.canonical_bytes,
            "resolved canonical input",
            maximum=MAX_OPAQUE_PUBLIC_BYTES,
        )


@runtime_checkable
class Resolver(Protocol):
    profile_id: str
    policy_id: str

    def resolve(self, query_result: object) -> ResolverResult: ...


@dataclass(frozen=True)
class DescriptorReference:
    locator: str
    digest: str

    def __post_init__(self) -> None:
        _identifier(self.locator, "descriptor locator")
        _identifier(self.digest, "descriptor digest")


@dataclass(frozen=True)
class DescriptorDocument:
    format_id: str
    payload: bytes = field(repr=False)

    def __post_init__(self) -> None:
        _identifier(self.format_id, "descriptor format")
        _opaque_bytes(self.payload, "descriptor", maximum=MAX_OPAQUE_PUBLIC_BYTES)


@dataclass(frozen=True)
class CurrentDescriptorPointer:
    format_id: str
    payload: bytes = field(repr=False)

    def __post_init__(self) -> None:
        _identifier(self.format_id, "current-pointer format")
        _opaque_bytes(
            self.payload, "descriptor current pointer", maximum=MAX_OPAQUE_PUBLIC_BYTES
        )


@runtime_checkable
class DescriptorStore(Protocol):
    def publish_immutable(
        self, descriptor: DescriptorDocument
    ) -> DescriptorReference: ...

    def read(self, reference: DescriptorReference) -> DescriptorDocument: ...

    def read_current(self, recovery_handle: str) -> CurrentDescriptorPointer: ...

    def compare_and_swap_current(
        self,
        recovery_handle: str,
        expected: CurrentDescriptorPointer | None,
        replacement: CurrentDescriptorPointer,
    ) -> None: ...


class StorageOperation(Enum):
    CREATE_IMMUTABLE = "create_immutable"
    READ_EXACT = "read_exact"
    COMPARE_AND_SWAP = "compare_and_swap"
    DELETE_EXACT = "delete_exact"


@dataclass(frozen=True)
class AdmissionBinding:
    subject: str
    backup_id: str
    epoch: int
    operation: str
    audience: str
    client_key_thumbprint: str
    nonce: str
    issued_at: int
    expires_at: int
    issuer: str
    profile_id: str

    def __post_init__(self) -> None:
        for value, label in (
            (self.subject, "admission subject"),
            (self.backup_id, "admission backup identifier"),
            (self.operation, "admission operation"),
            (self.audience, "admission audience"),
            (self.client_key_thumbprint, "client-key thumbprint"),
            (self.nonce, "admission nonce"),
            (self.issuer, "admission issuer"),
            (self.profile_id, "admission profile"),
        ):
            _identifier(value, label)
        _positive_int(self.epoch, "admission epoch")
        _positive_int(self.issued_at, "admission issuance time")
        _positive_int(self.expires_at, "admission expiry")
        if self.expires_at <= self.issued_at:
            raise ContractError("admission expiry is not after issuance")


@dataclass(frozen=True)
class AdmissionCapability:
    format_id: str
    payload: bytes = field(repr=False)

    def __post_init__(self) -> None:
        _identifier(self.format_id, "admission capability format")
        _opaque_bytes(
            self.payload,
            "admission capability",
            maximum=MAX_OPAQUE_CAPABILITY_BYTES,
        )


@dataclass(frozen=True)
class AdmissionGrant:
    binding: AdmissionBinding
    grant_digest: str

    def __post_init__(self) -> None:
        _identifier(self.grant_digest, "admission grant digest")


@runtime_checkable
class AdmissionVerifier(Protocol):
    profile_id: str

    def verify(
        self,
        capability: AdmissionCapability,
        expected: AdmissionBinding,
        client_proof: bytes,
    ) -> AdmissionGrant: ...


@runtime_checkable
class StorageCapabilityVerifier(Protocol):
    profile_id: str

    def verify(
        self,
        capability: AdmissionCapability,
        expected: AdmissionBinding,
        client_proof: bytes,
    ) -> AdmissionGrant: ...


@dataclass(frozen=True)
class GatewayRequest:
    operation: StorageOperation
    object_key: str
    backup_reference: BackupReference
    payload: bytes | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.operation, StorageOperation):
            raise ContractError("invalid storage operation")
        _identifier(self.object_key, "storage object key")
        self.backup_reference.validate()
        if self.payload is not None and (
            not isinstance(self.payload, bytes)
            or len(self.payload) > MAX_OPAQUE_PUBLIC_BYTES
        ):
            raise ContractError("invalid storage payload")


@dataclass(frozen=True)
class GatewayResult:
    reference: BackupReference
    payload: bytes | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        self.reference.validate()
        if self.payload is not None and (
            not isinstance(self.payload, bytes)
            or len(self.payload) > MAX_OPAQUE_PUBLIC_BYTES
        ):
            raise ContractError("invalid storage result")


@runtime_checkable
class ApplicationStorageGateway(Protocol):
    def execute(
        self, request: GatewayRequest, admission: AdmissionGrant
    ) -> GatewayResult: ...


@dataclass(frozen=True)
class AuthorizerEndpoint:
    authorizer_id: int
    endpoint: str
    identity_digest: str

    def __post_init__(self) -> None:
        _positive_int(self.authorizer_id, "authorizer identifier", maximum=MAX_PARTIES)
        _identifier(self.endpoint, "authorizer endpoint")
        _identifier(self.identity_digest, "authorizer identity digest")


@dataclass(frozen=True)
class RecoveryHolder:
    holder_id: int
    authorizer_id: int
    suite_id: str

    def __post_init__(self) -> None:
        _positive_int(self.holder_id, "recovery holder identifier", maximum=MAX_PARTIES)
        _positive_int(self.authorizer_id, "authorizer identifier", maximum=MAX_PARTIES)
        _identifier(self.suite_id, "recovery suite identifier")


@dataclass(frozen=True)
class PartyDirectorySnapshot:
    authorizers: tuple[AuthorizerEndpoint, ...]
    recovery_holders: tuple[RecoveryHolder, ...]
    authorization_quorum: int
    recovery_threshold: ThresholdParameters

    def __post_init__(self) -> None:
        authorizer_ids = [item.authorizer_id for item in self.authorizers]
        holder_ids = [item.holder_id for item in self.recovery_holders]
        if authorizer_ids != sorted(set(authorizer_ids)):
            raise ContractError("authorizer identifiers are not canonical")
        if holder_ids != sorted(set(holder_ids)):
            raise ContractError("recovery holder identifiers are not canonical")
        _positive_int(
            self.authorization_quorum,
            "authorization quorum",
            maximum=len(authorizer_ids),
        )
        if any(
            holder.authorizer_id not in authorizer_ids
            for holder in self.recovery_holders
        ):
            raise ContractError("recovery holder is not an authorizer")
        if len(self.recovery_holders) != self.recovery_threshold.n:
            raise ContractError("recovery membership does not match threshold")
        if len({holder.suite_id for holder in self.recovery_holders}) != 1:
            raise ContractError("recovery holder set mixes suites")


@runtime_checkable
class PartyDirectory(Protocol):
    def resolve(self, recovery_handle: str, epoch: int) -> PartyDirectorySnapshot: ...


class EnrollmentPhase(Enum):
    KEY = "key"
    POLICY = "policy"
    SUITE_SETUP = "suite_setup"
    KEY_WRAP = "key_wrap"
    BACKUP_PUBLICATION = "backup_publication"
    PARTY_PROVISIONING = "party_provisioning"
    DESCRIPTOR_PUBLICATION = "descriptor_publication"
    RECEIPT = "receipt"
    DISPOSAL = "disposal"
    COMPLETE = "complete"


class RecoveryPhase(Enum):
    BOOTSTRAP = "bootstrap"
    DESCRIPTOR_VERIFICATION = "descriptor_verification"
    CURRENT_STATE = "current_state"
    BACKUP_RETRIEVAL = "backup_retrieval"
    POLICY = "policy"
    THRESHOLD_SELECTION = "threshold_selection"
    AUTHORIZATION = "authorization"
    SUITE_RECOVERY = "suite_recovery"
    DECRYPTION = "decryption"
    KEY_IDENTITY = "key_identity"
    SUCCESSOR = "successor"
    COMPLETE = "complete"


@dataclass(frozen=True)
class EnrollmentClientState:
    operation_id: str
    phase: EnrollmentPhase
    backup_id: str | None = None
    epoch: int | None = None

    def __post_init__(self) -> None:
        _identifier(self.operation_id, "enrollment operation identifier")
        if not isinstance(self.phase, EnrollmentPhase):
            raise ContractError("invalid enrollment phase")
        if (self.backup_id is None) != (self.epoch is None):
            raise ContractError("incomplete enrollment epoch binding")
        if self.backup_id is not None:
            _identifier(self.backup_id, "enrollment backup identifier")
            _positive_int(self.epoch, "enrollment epoch")


@dataclass(frozen=True)
class RecoveryClientState:
    operation_id: str
    phase: RecoveryPhase
    recovery_handle: str
    backup_id: str | None = None
    epoch: int | None = None

    def __post_init__(self) -> None:
        _identifier(self.operation_id, "recovery operation identifier")
        _identifier(self.recovery_handle, "recovery handle")
        if not isinstance(self.phase, RecoveryPhase):
            raise ContractError("invalid recovery phase")
        if (self.backup_id is None) != (self.epoch is None):
            raise ContractError("incomplete recovery epoch binding")
        if self.backup_id is not None:
            _identifier(self.backup_id, "recovery backup identifier")
            _positive_int(self.epoch, "recovery epoch")


@runtime_checkable
class EnrollmentClientStateMachine(Protocol):
    def begin(self, operation_id: str) -> EnrollmentClientState: ...

    def advance(
        self, state: EnrollmentClientState, event: object
    ) -> EnrollmentClientState: ...


@runtime_checkable
class RecoveryClientStateMachine(Protocol):
    def begin(self, operation_id: str, recovery_handle: str) -> RecoveryClientState: ...

    def advance(
        self, state: RecoveryClientState, event: object
    ) -> RecoveryClientState: ...


@dataclass(frozen=True)
class LifecycleBinding:
    backup_id: str
    predecessor_epoch: int
    successor_epoch: int
    successor_configuration_digest: str

    def __post_init__(self) -> None:
        _identifier(self.backup_id, "lifecycle backup identifier")
        _positive_int(self.predecessor_epoch, "predecessor epoch")
        _positive_int(self.successor_epoch, "successor epoch")
        if self.successor_epoch != self.predecessor_epoch + 1:
            raise ContractError("successor epoch is not consecutive")
        _identifier(
            self.successor_configuration_digest,
            "successor configuration digest",
        )


@dataclass(frozen=True)
class LifecycleTransition:
    format_id: str
    binding: LifecycleBinding
    payload: bytes = field(repr=False)

    def __post_init__(self) -> None:
        _identifier(self.format_id, "lifecycle transition format")
        _opaque_bytes(
            self.payload, "lifecycle transition", maximum=MAX_OPAQUE_PUBLIC_BYTES
        )


@runtime_checkable
class LifecycleManager(Protocol):
    def prepare_successor(self, binding: LifecycleBinding) -> LifecycleTransition: ...

    def activate_successor(self, transition: LifecycleTransition) -> None: ...

    def retire_predecessor(self, transition: LifecycleTransition) -> None: ...


__all__ = [
    "AdmissionBinding",
    "AdmissionCapability",
    "AdmissionGrant",
    "AdmissionVerifier",
    "ApplicationStorageGateway",
    "AuthorizerEndpoint",
    "BackupObjectStore",
    "ContractError",
    "CuePolicy",
    "CuePolicyResult",
    "CurrentDescriptorPointer",
    "DescriptorDocument",
    "DescriptorReference",
    "DescriptorStore",
    "EnrollmentClientState",
    "EnrollmentClientStateMachine",
    "EnrollmentPhase",
    "GatewayRequest",
    "GatewayResult",
    "LifecycleBinding",
    "LifecycleManager",
    "LifecycleTransition",
    "PartyDirectory",
    "PartyDirectorySnapshot",
    "PartyRecoveryState",
    "PasswordProtectedSecretRecovery",
    "PublicRecoveryState",
    "RecoveryClientSession",
    "RecoveryClientState",
    "RecoveryClientStateMachine",
    "RecoveryContext",
    "RecoveryHolder",
    "RecoveryPhase",
    "RecoveryRequest",
    "RecoveryResponse",
    "RecoverySuiteEnrollment",
    "Resolver",
    "ResolverResult",
    "StorageCapabilityVerifier",
    "StorageOperation",
    "ThresholdParameters",
]
