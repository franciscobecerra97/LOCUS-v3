"""Explicit selectable-suite enrollment and crash-safe successor integration."""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from .appss_client import (
    AppssInitializationResult,
    AppssPartyEndpoint,
    initialize_with_parties,
    recover_with_parties,
)
from .appss_formats import (
    APPSS_SUITE_ID,
    REFERENCE_BACKUP_V5,
    YI_SUITE_ID,
    AppssHolderBinding,
    context_digest,
    derive_password_input,
)
from .codec import encode
from .contracts import (
    PartyRecoveryState,
    PublicRecoveryState,
    RecoveryContext,
)
from .crypto import hash_scalar, random_bytes
from .recovery_descriptor import (
    BACKUP_MEMBER,
    RecoveryDescriptorError,
    create_bundle,
    create_descriptor,
    decode_bundle,
)
from .recovery_descriptor import (
    configuration_digest as descriptor_configuration_digest,
)
from .recovery_suite_registry import (
    RecoverySuiteRegistry,
    RecoverySuiteSelection,
)
from .successor_publication import (
    SuccessorBinding,
    SuccessorPhase,
    SuccessorPublicationError,
)
from .suite_backup import (
    SuiteBackupError,
    open_backup_v5_with_secret,
    recover_backup_v5,
    seal_backup_v5,
)
from .yi_compat import RecoverySuiteError


class SelectableSuiteError(ValueError):
    """Suite selection, preparation, recovery, or cutover failed closed."""


class InjectedSuccessorCrash(RuntimeError):
    """Synthetic crash after a durable publication effect."""


@dataclass(frozen=True)
class PreparedSelectableEpoch:
    """Complete but inactive suite-bound epoch package with no recovery secret."""

    selection: RecoverySuiteSelection
    context: RecoveryContext
    backup: dict[str, Any]
    backup_bytes: bytes = field(repr=False)
    descriptor_bytes: bytes = field(repr=False)
    bundle_bytes: bytes = field(repr=False)
    public_state: PublicRecoveryState
    protected_key_digest: str
    descriptor_configuration_digest: str
    party_states: tuple[PartyRecoveryState, ...] = field(repr=False)
    ready_digests: tuple[tuple[int, str], ...] = ()

    @property
    def descriptor_digest(self) -> str:
        return hashlib.sha256(self.descriptor_bytes).hexdigest()

    @property
    def bundle_digest(self) -> str:
        return hashlib.sha256(self.bundle_bytes).hexdigest()


@dataclass(frozen=True)
class SelectableEpochRuntime:
    prepared: PreparedSelectableEpoch
    appss_holders: tuple[AppssHolderBinding, ...] = ()
    appss_endpoints: Mapping[int, AppssPartyEndpoint] = field(
        default_factory=dict, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        if self.prepared.selection.suite_id == APPSS_SUITE_ID:
            if len(self.appss_holders) != 3 or set(self.appss_endpoints) != {1, 2, 3}:
                raise SelectableSuiteError("incomplete aPPSS runtime")
        elif self.appss_holders or self.appss_endpoints:
            raise SelectableSuiteError("Yi runtime contains aPPSS endpoints")


class SelectableSuiteEpochFactory:
    """Build an inactive epoch only after one explicit selector is validated."""

    def __init__(
        self,
        *,
        signer: Ed25519PrivateKey,
        issuer: str,
        key_id: str,
        subject_id: str,
        issued_at: int,
        expires_at: int,
        registry: RecoverySuiteRegistry | None = None,
    ) -> None:
        self.signer = signer
        self.issuer = issuer
        self.key_id = key_id
        self.subject_id = subject_id
        self.issued_at = issued_at
        self.expires_at = expires_at
        self.registry = RecoverySuiteRegistry() if registry is None else registry

    def prepare_epoch(
        self,
        *,
        selector_bytes: bytes,
        recovery_id: str,
        backup_id: bytes,
        epoch: int,
        policy_id: str,
        resolver_profile: str,
        canonical_input: bytes,
        protected_key: bytes,
        public_configuration_digest: bytes,
        predecessor_descriptor_digest: str | None,
        appss_holders: tuple[AppssHolderBinding, ...] = (),
        appss_endpoints: Mapping[int, AppssPartyEndpoint] | None = None,
        admission_grant_digest: str = "00" * 32,
        client_proof_key_digest: str = "00" * 32,
        nonce: bytes | None = None,
    ) -> SelectableEpochRuntime:
        if (
            len(backup_id) != 16
            or len(public_configuration_digest) != 32
            or not canonical_input
            or not protected_key
        ):
            raise SelectableSuiteError("invalid selectable epoch input")
        backup_nonce = random_bytes(16) if nonce is None else nonce
        if len(backup_nonce) != 16:
            raise SelectableSuiteError("invalid selectable backup nonce")
        try:
            selection, adapter = self.registry.select_new_epoch(selector_bytes)
        except RecoverySuiteError as exc:
            raise SelectableSuiteError("invalid explicit suite selection") from exc
        if selection.threshold.k != 2 or selection.threshold.n != 3:
            raise SelectableSuiteError("unsupported selectable topology")

        endpoints = {} if appss_endpoints is None else appss_endpoints
        if selection.suite_id == APPSS_SUITE_ID:
            if [holder.index for holder in appss_holders] != [1, 2, 3] or set(
                endpoints
            ) != {1, 2, 3}:
                raise SelectableSuiteError("aPPSS selection has no exact membership")
            suite_context = context_digest(
                backup_id=backup_id,
                epoch=epoch,
                policy_id=policy_id,
                holders=appss_holders,
                k=2,
                n=3,
                configuration_digest=public_configuration_digest,
            )
        elif selection.suite_id == YI_SUITE_ID:
            if appss_holders or endpoints:
                raise SelectableSuiteError("Yi selection contains aPPSS state")
            # Backup v5 requires a suite-bound public context. Yi password and
            # frozen wire bytes do not consume or reinterpret this digest.
            suite_context = public_configuration_digest
        else:  # Registry already fails closed; keep this boundary explicit.
            raise SelectableSuiteError("unsupported selectable suite")

        context = RecoveryContext(
            suite_id=selection.suite_id,
            recovery_id=recovery_id,
            backup_id=backup_id.hex(),
            epoch=epoch,
            policy_id=policy_id,
            configuration_digest=public_configuration_digest.hex(),
            digest_context=f"selectable-suite:{backup_id.hex()}:{epoch}",
            suite_context_digest=suite_context.hex(),
        )
        try:
            if selection.suite_id == APPSS_SUITE_ID:
                password_input = derive_password_input(suite_context, canonical_input)
                initialized: AppssInitializationResult = initialize_with_parties(
                    context=context,
                    password_input=password_input,
                    holders=appss_holders,
                    endpoints=endpoints,
                    admission_grant_digest=admission_grant_digest,
                    client_proof_key_digest=client_proof_key_digest,
                )
                public_state = initialized.public_state
                party_states: tuple[PartyRecoveryState, ...] = ()
                ready_digests = initialized.ready_digests
                recovery_secret = initialized.recovery_secret
            else:
                password_input = hash_scalar(
                    "LOCUS-context-password",
                    canonical_input,
                    backup_nonce,
                    backup_id.hex(),
                    epoch,
                ).to_bytes(32, "big")
                enrollment = adapter.initialize(
                    context=context,
                    password_input=password_input,
                    threshold=selection.threshold,
                )
                public_state = enrollment.public_state
                party_states = enrollment.party_states
                ready_digests = ()
                recovery_secret = enrollment.recovery_secret
            backup = seal_backup_v5(
                protected_key=protected_key,
                context=context,
                cue_policy_id=policy_id,
                resolver_profile=resolver_profile,
                suite_id=selection.suite_id,
                public_state_format=public_state.format_id,
                public_state_payload=public_state.payload,
                recovery_secret=recovery_secret,
                profile_id=selection.profile_id,
                bid=backup_id,
                nonce=backup_nonce,
            )
        except (RecoverySuiteError, SuiteBackupError, ValueError) as exc:
            raise SelectableSuiteError("selectable epoch preparation failed") from exc

        backup_bytes = encode(backup)
        payload = self._descriptor_payload(
            selection=selection,
            recovery_id=recovery_id,
            backup_id=backup_id,
            epoch=epoch,
            policy_id=policy_id,
            resolver_profile=resolver_profile,
            backup_bytes=backup_bytes,
            public_state=public_state,
            predecessor_descriptor_digest=predecessor_descriptor_digest,
        )
        try:
            descriptor_bytes = create_descriptor(
                payload, signer=self.signer, key_id=self.key_id
            )
            bundle_bytes = create_bundle(
                backup_bytes=backup_bytes,
                descriptor_bytes=descriptor_bytes,
                backup_format=REFERENCE_BACKUP_V5,
            )
        except RecoveryDescriptorError as exc:
            raise SelectableSuiteError(
                "selectable descriptor preparation failed"
            ) from exc
        prepared = PreparedSelectableEpoch(
            selection=selection,
            context=context,
            backup=backup,
            backup_bytes=backup_bytes,
            descriptor_bytes=descriptor_bytes,
            bundle_bytes=bundle_bytes,
            public_state=public_state,
            protected_key_digest=hashlib.sha256(protected_key).hexdigest(),
            descriptor_configuration_digest=payload["lifecycle"][
                "configuration_digest"
            ],
            party_states=party_states,
            ready_digests=ready_digests,
        )
        return SelectableEpochRuntime(
            prepared=prepared,
            appss_holders=appss_holders,
            appss_endpoints=endpoints,
        )

    def _descriptor_payload(
        self,
        *,
        selection: RecoverySuiteSelection,
        recovery_id: str,
        backup_id: bytes,
        epoch: int,
        policy_id: str,
        resolver_profile: str,
        backup_bytes: bytes,
        public_state: PublicRecoveryState,
        predecessor_descriptor_digest: str | None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "authorization": {
                "admission_profile": "LOCUS-local-synthetic-admission-v1",
                "audience": "locus-recovery",
                "authorizers": [
                    {
                        "authorizer_id": authorizer_id,
                        "endpoint": f"https://party-{authorizer_id}.invalid/",
                        "identity_key_id": f"party-key-{authorizer_id}",
                    }
                    for authorizer_id in selection.authorizer_ids
                ],
                "operation_namespace": "locus-recovery",
                "quorum": selection.authorization_quorum,
                "security_policy": "LOCUS-security-policy-v1",
            },
            "backup": {
                "format": REFERENCE_BACKUP_V5,
                "length": len(backup_bytes),
                "member": BACKUP_MEMBER,
                "sha256": hashlib.sha256(backup_bytes).hexdigest(),
            },
            "backup_id": backup_id.hex(),
            "cue_policy": {
                "id": policy_id,
                "public_parameters_hex": encode({"cardinality": 3}).hex(),
                "resolver_profile": resolver_profile,
            },
            "epoch": epoch,
            "expires_at": self.expires_at,
            "issued_at": self.issued_at,
            "issuer": self.issuer,
            "lifecycle": {
                "configuration_digest": "00" * 32,
                "predecessor_descriptor_digest": predecessor_descriptor_digest,
            },
            "recovery_id": recovery_id,
            "recovery_suite": {
                "holders": [
                    {"authorizer_id": holder_id, "holder_id": holder_id}
                    for holder_id in selection.holder_ids
                ],
                "id": selection.suite_id,
                "public_state_format": public_state.format_id,
                "public_state_hex": public_state.payload.hex(),
                "threshold": {
                    "k": selection.threshold.k,
                    "n": selection.threshold.n,
                },
            },
            "subject_id": self.subject_id,
        }
        payload["lifecycle"]["configuration_digest"] = descriptor_configuration_digest(
            payload
        )
        return payload


def recover_selectable_epoch(
    runtime: SelectableEpochRuntime,
    *,
    canonical_input: bytes,
    issuer_public_key: Ed25519PublicKey,
    expected_issuer: str,
    expected_key_id: str,
    admission_grant_digest: str = "00" * 32,
    client_proof_key_digest: str = "00" * 32,
    registry: RecoverySuiteRegistry | None = None,
) -> bytes:
    """Recover only through the authenticated descriptor's exact suite."""

    selected_registry = RecoverySuiteRegistry() if registry is None else registry
    prepared = runtime.prepared
    try:
        bundle = decode_bundle(
            prepared.bundle_bytes,
            issuer_public_key=issuer_public_key,
            expected_issuer=expected_issuer,
            expected_key_id=expected_key_id,
        )
        payload = bundle.descriptor["payload"]
        suite = payload["recovery_suite"]
        adapter = selected_registry.for_authenticated_descriptor(suite["id"])
        if (
            suite["id"] != prepared.selection.suite_id
            or suite["public_state_format"] != prepared.public_state.format_id
            or bytes.fromhex(suite["public_state_hex"]) != prepared.public_state.payload
            or bundle.backup != prepared.backup
            or payload["epoch"] != prepared.context.epoch
            or payload["backup_id"] != prepared.context.backup_id
        ):
            raise SelectableSuiteError("authenticated selectable epoch changed")
        if suite["id"] == APPSS_SUITE_ID:
            password_input = derive_password_input(
                bytes.fromhex(prepared.context.suite_context_digest or ""),
                canonical_input,
            )
            secret = recover_with_parties(
                context=prepared.context,
                password_input=password_input,
                public_state=prepared.public_state,
                holders=(runtime.appss_holders[0], runtime.appss_holders[2]),
                endpoints=runtime.appss_endpoints,
                admission_grant_digest=admission_grant_digest,
                client_proof_key_digest=client_proof_key_digest,
            )
            protected_key = open_backup_v5_with_secret(
                backup=bundle.backup, recovery_secret=secret
            )
        else:
            if len(prepared.party_states) < prepared.selection.threshold.k:
                raise SelectableSuiteError("insufficient Yi holder state")
            password_input = hash_scalar(
                "LOCUS-context-password",
                canonical_input,
                bytes.fromhex(bundle.backup["nonce"]),
                prepared.context.backup_id,
                prepared.context.epoch,
            ).to_bytes(32, "big")
            protected_key = recover_backup_v5(
                backup=bundle.backup,
                context=prepared.context,
                password_input=password_input,
                adapter=adapter,
                party_states=prepared.party_states[: prepared.selection.threshold.k],
            )
        if hashlib.sha256(protected_key).hexdigest() != prepared.protected_key_digest:
            raise SelectableSuiteError("protected-key identity mismatch")
        return protected_key
    except (
        RecoveryDescriptorError,
        RecoverySuiteError,
        SuiteBackupError,
        ValueError,
    ) as exc:
        raise SelectableSuiteError("selectable recovery rejected") from exc


def prepare_selectable_successor(
    *,
    predecessor: SelectableEpochRuntime,
    factory: SelectableSuiteEpochFactory,
    selector_bytes: bytes,
    canonical_input: bytes,
    issuer_public_key: Ed25519PublicKey,
    expected_issuer: str,
    expected_key_id: str,
    public_configuration_digest: bytes,
    appss_holders: tuple[AppssHolderBinding, ...] = (),
    appss_endpoints: Mapping[int, AppssPartyEndpoint] | None = None,
    admission_grant_digest: str = "00" * 32,
    client_proof_key_digest: str = "00" * 32,
) -> SelectableEpochRuntime:
    """Recover the predecessor client-side, then create a wholly fresh epoch."""

    protected_key = recover_selectable_epoch(
        predecessor,
        canonical_input=canonical_input,
        issuer_public_key=issuer_public_key,
        expected_issuer=expected_issuer,
        expected_key_id=expected_key_id,
        admission_grant_digest=admission_grant_digest,
        client_proof_key_digest=client_proof_key_digest,
    )
    successor = factory.prepare_epoch(
        selector_bytes=selector_bytes,
        recovery_id=(
            f"selectable-successor:{predecessor.prepared.context.backup_id}:"
            f"{predecessor.prepared.context.epoch + 1}"
        ),
        backup_id=bytes.fromhex(predecessor.prepared.context.backup_id),
        epoch=predecessor.prepared.context.epoch + 1,
        policy_id=predecessor.prepared.context.policy_id,
        resolver_profile=predecessor.prepared.backup["cue_policy"]["resolver_profile"],
        canonical_input=canonical_input,
        protected_key=protected_key,
        public_configuration_digest=public_configuration_digest,
        predecessor_descriptor_digest=predecessor.prepared.descriptor_digest,
        appss_holders=appss_holders,
        appss_endpoints=appss_endpoints,
        admission_grant_digest=admission_grant_digest,
        client_proof_key_digest=client_proof_key_digest,
    )
    if (
        successor.prepared.protected_key_digest
        != predecessor.prepared.protected_key_digest
        or successor.prepared.bundle_digest == predecessor.prepared.bundle_digest
    ):
        raise SelectableSuiteError("successor state is not fresh")
    if (
        successor.prepared.selection.suite_id
        == predecessor.prepared.selection.suite_id
        == APPSS_SUITE_ID
        and successor.prepared.public_state.payload
        == predecessor.prepared.public_state.payload
    ):
        raise SelectableSuiteError("successor aPPSS state is not fresh")
    if (
        successor.prepared.selection.suite_id
        == predecessor.prepared.selection.suite_id
        == YI_SUITE_ID
        and [state.payload for state in successor.prepared.party_states]
        == [state.payload for state in predecessor.prepared.party_states]
    ):
        raise SelectableSuiteError("successor Yi state is not fresh")
    return successor


def successor_binding(
    *,
    predecessor: SelectableEpochRuntime,
    successor: SelectableEpochRuntime,
    operation_id: str,
) -> SuccessorBinding:
    if (
        successor.prepared.context.epoch != predecessor.prepared.context.epoch + 1
        or successor.prepared.context.backup_id
        != predecessor.prepared.context.backup_id
    ):
        raise SelectableSuiteError("invalid selectable successor epochs")
    return SuccessorBinding(
        operation_id=operation_id,
        backup_id=predecessor.prepared.context.backup_id,
        predecessor_epoch=predecessor.prepared.context.epoch,
        successor_epoch=successor.prepared.context.epoch,
        successor_configuration_digest=(
            successor.prepared.descriptor_configuration_digest
        ),
        successor_backup_digest=hashlib.sha256(
            successor.prepared.backup_bytes
        ).hexdigest(),
        successor_descriptor_digest=successor.prepared.descriptor_digest,
        recovered_key_digest=predecessor.prepared.protected_key_digest,
        rotate_protected_key=False,
    )


class SelectableSuccessorBackend:
    """P4.3 backend that binds every effect to one prepared suite descriptor."""

    def __init__(
        self,
        *,
        predecessor: SelectableEpochRuntime,
        successor: SelectableEpochRuntime,
        canonical_input: bytes,
        issuer_public_key: Ed25519PublicKey,
        expected_issuer: str,
        expected_key_id: str,
        crash_after: SuccessorPhase | None = None,
        admission_grant_digest: str = "00" * 32,
        client_proof_key_digest: str = "00" * 32,
    ) -> None:
        self.predecessor = predecessor
        self.successor = successor
        self.canonical_input = canonical_input
        self.issuer_public_key = issuer_public_key
        self.expected_issuer = expected_issuer
        self.expected_key_id = expected_key_id
        self.crash_after = crash_after
        self.admission_grant_digest = admission_grant_digest
        self.client_proof_key_digest = client_proof_key_digest
        self.completed: dict[SuccessorPhase, str] = {}
        self.recoverable = {predecessor.prepared.context.epoch}
        self.published_backup: bytes | None = None
        self.published_bundle: bytes | None = None
        self.preserved = False
        self.parties_prepared = False
        self.ready = False
        self.successor_verified = False
        self.activation_count = 0
        self.retirement_count = 0

    def _effect(
        self,
        phase: SuccessorPhase,
        idempotency_key: str,
        action: Callable[[], None],
    ) -> None:
        prior = self.completed.get(phase)
        if prior is not None:
            if prior != idempotency_key:
                raise SuccessorPublicationError("stale selectable-suite action")
            return
        action()
        self.completed[phase] = idempotency_key
        if self.crash_after is phase:
            self.crash_after = None
            raise InjectedSuccessorCrash(phase.value)

    def preserve_original_key(
        self, binding: SuccessorBinding, idempotency_key: str
    ) -> None:
        def action() -> None:
            key = recover_selectable_epoch(
                self.predecessor,
                canonical_input=self.canonical_input,
                issuer_public_key=self.issuer_public_key,
                expected_issuer=self.expected_issuer,
                expected_key_id=self.expected_key_id,
                admission_grant_digest=self.admission_grant_digest,
                client_proof_key_digest=self.client_proof_key_digest,
            )
            if hashlib.sha256(key).hexdigest() != binding.recovered_key_digest:
                raise SuccessorPublicationError("predecessor key identity changed")
            self.preserved = True

        self._effect(SuccessorPhase.PRESERVE_ORIGINAL_KEY, idempotency_key, action)

    def prepare_parties(self, binding: SuccessorBinding, idempotency_key: str) -> None:
        del binding

        def action() -> None:
            if not self.preserved:
                raise SuccessorPublicationError("original key was not preserved")
            if (
                self.successor.prepared.selection.suite_id == APPSS_SUITE_ID
                and len(self.successor.prepared.ready_digests) != 3
            ):
                raise SuccessorPublicationError("aPPSS parties are not ready")
            self.parties_prepared = True

        self._effect(SuccessorPhase.PREPARE_PARTIES, idempotency_key, action)

    def publish_backup(self, binding: SuccessorBinding, idempotency_key: str) -> None:
        def action() -> None:
            if not self.parties_prepared:
                raise SuccessorPublicationError("successor parties are not prepared")
            if (
                hashlib.sha256(self.successor.prepared.backup_bytes).hexdigest()
                != binding.successor_backup_digest
            ):
                raise SuccessorPublicationError("successor backup binding changed")
            self.published_backup = self.successor.prepared.backup_bytes

        self._effect(SuccessorPhase.PUBLISH_BACKUP, idempotency_key, action)

    def publish_descriptor(
        self, binding: SuccessorBinding, idempotency_key: str
    ) -> None:
        def action() -> None:
            if self.published_backup is None:
                raise SuccessorPublicationError("successor backup is not published")
            if self.successor.prepared.descriptor_digest != (
                binding.successor_descriptor_digest
            ):
                raise SuccessorPublicationError("successor descriptor binding changed")
            self.published_bundle = self.successor.prepared.bundle_bytes

        self._effect(SuccessorPhase.PUBLISH_DESCRIPTOR, idempotency_key, action)

    def verify_readiness(self, binding: SuccessorBinding, idempotency_key: str) -> None:
        del binding

        def action() -> None:
            if self.published_bundle is None:
                raise SuccessorPublicationError("successor bundle is not published")
            try:
                decode_bundle(
                    self.published_bundle,
                    issuer_public_key=self.issuer_public_key,
                    expected_issuer=self.expected_issuer,
                    expected_key_id=self.expected_key_id,
                )
            except RecoveryDescriptorError as exc:
                raise SuccessorPublicationError("successor is not ready") from exc
            self.ready = True

        self._effect(SuccessorPhase.VERIFY_READINESS, idempotency_key, action)

    def verify_successor_recovery(
        self, binding: SuccessorBinding, idempotency_key: str
    ) -> None:
        def action() -> None:
            if not self.ready:
                raise SuccessorPublicationError("successor is not ready")
            key = recover_selectable_epoch(
                self.successor,
                canonical_input=self.canonical_input,
                issuer_public_key=self.issuer_public_key,
                expected_issuer=self.expected_issuer,
                expected_key_id=self.expected_key_id,
                admission_grant_digest=self.admission_grant_digest,
                client_proof_key_digest=self.client_proof_key_digest,
            )
            if hashlib.sha256(key).hexdigest() != binding.recovered_key_digest:
                raise SuccessorPublicationError("successor key identity changed")
            self.successor_verified = True

        self._effect(SuccessorPhase.VERIFY_SUCCESSOR_RECOVERY, idempotency_key, action)

    def activate_successor(
        self, binding: SuccessorBinding, idempotency_key: str
    ) -> None:
        def action() -> None:
            if not self.successor_verified:
                raise SuccessorPublicationError("successor recovery is unverified")
            self.recoverable = {binding.successor_epoch}
            self.activation_count += 1

        self._effect(SuccessorPhase.ACTIVATE_SUCCESSOR, idempotency_key, action)

    def retire_predecessor(
        self, binding: SuccessorBinding, idempotency_key: str
    ) -> None:
        def action() -> None:
            if self.recoverable != {binding.successor_epoch}:
                raise SuccessorPublicationError("predecessor retirement is unsafe")
            self.retirement_count += 1

        self._effect(SuccessorPhase.RETIRE_PREDECESSOR, idempotency_key, action)

    def rotate_protected_key(
        self, binding: SuccessorBinding, idempotency_key: str
    ) -> None:
        del binding, idempotency_key
        raise SuccessorPublicationError("protected-key rotation was not selected")

    def authorized_recoverable_epochs(
        self, binding: SuccessorBinding
    ) -> frozenset[int]:
        del binding
        return frozenset(self.recoverable)


__all__ = [
    "InjectedSuccessorCrash",
    "PreparedSelectableEpoch",
    "SelectableEpochRuntime",
    "SelectableSuccessorBackend",
    "SelectableSuiteEpochFactory",
    "SelectableSuiteError",
    "prepare_selectable_successor",
    "recover_selectable_epoch",
    "successor_binding",
]
