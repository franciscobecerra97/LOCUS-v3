"""Transient aPPSS client orchestration over opaque authenticated endpoints."""

from __future__ import annotations

import hashlib
import secrets
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Protocol

from . import _tpass_native as native
from .appss import AppssRecoveryAdapter
from .appss_formats import (
    APPSS_SUITE_ID,
    MAX_INSTALL_BYTES,
    MAX_PUBLIC_STATE_BYTES,
    MAX_READY_BYTES,
    MAX_REQUEST_BYTES,
    MAX_RESPONSE_BYTES,
    AppssFormatError,
    AppssHolderBinding,
    appss_format,
    appss_profile,
    canonical_decode,
    encode_checked,
    instance_id,
    oprf_input,
    validate_install,
    validate_public_state,
    validate_ready,
    validate_request,
    validate_response,
)
from .contracts import PublicRecoveryState, RecoveryContext, ThresholdParameters
from .yi_compat import RecoverySuiteError


class AppssPartyEndpoint(Protocol):
    """One authenticated recipient-bound aPPSS evaluation endpoint."""

    @property
    def holder_id(self) -> int: ...

    @property
    def service_identity(self) -> str: ...

    def evaluate(self, request_bytes: bytes, *, idempotency_key: str) -> bytes: ...

    def initialize(self, request_bytes: bytes, *, idempotency_key: str) -> bytes: ...

    def install(self, install_bytes: bytes, *, idempotency_key: str) -> bytes: ...


class AppssClientError(RecoverySuiteError):
    """The distributed aPPSS client failed without exposing a cue predicate."""


@dataclass(frozen=True)
class AppssInitializationResult:
    """Client output returned only after every holder proves ready."""

    public_state: PublicRecoveryState
    ready_digests: tuple[tuple[int, str], ...]
    recovery_secret: bytes = field(repr=False)


def initialize_with_parties(
    *,
    context: RecoveryContext,
    password_input: bytes,
    holders: Sequence[AppssHolderBinding],
    endpoints: Mapping[int, AppssPartyEndpoint],
    admission_grant_digest: str,
    client_proof_key_digest: str,
    operation_id: str | None = None,
    threshold: ThresholdParameters | None = None,
) -> AppssInitializationResult:
    """Run distributed OPRF setup and install one common omega at every holder."""

    adapter = AppssRecoveryAdapter()
    try:
        context_digest = adapter._context_digest(context)  # noqa: SLF001
        password = adapter._password(password_input)  # noqa: SLF001
    except RecoverySuiteError as exc:
        raise AppssClientError("aPPSS initialization rejected") from exc
    selected_threshold = (
        ThresholdParameters(k=2, n=3) if threshold is None else threshold
    )
    try:
        profile_id = appss_profile(selected_threshold.k, selected_threshold.n)
    except AppssFormatError as exc:
        raise AppssClientError("invalid aPPSS initialization topology") from exc
    selected = tuple(holders)
    if (
        len(selected) != selected_threshold.n
        or [holder.index for holder in selected]
        != list(range(1, selected_threshold.n + 1))
        or any(endpoints.get(holder.index) is None for holder in selected)
    ):
        raise AppssClientError("invalid aPPSS initialization membership")
    _validate_endpoint_bindings(selected, endpoints)
    _lower_hex(admission_grant_digest, "admission grant digest")
    _lower_hex(client_proof_key_digest, "client proof-key digest")
    operation = secrets.token_hex(32) if operation_id is None else operation_id
    _lower_hex(operation, "operation identifier")

    masks: list[tuple[int, bytes]] = []
    response_bytes_by_holder: list[bytes] = []
    for holder in selected:
        endpoint = endpoints[holder.index]
        instance = instance_id(context_digest, holder)
        session_id = secrets.token_hex(32)
        nonce = secrets.token_hex(32)
        try:
            session, blinded = native.appss_blind(oprf_input(instance, password))
            request = {
                "admission_grant_digest": admission_grant_digest,
                "blinded_element": blinded.hex(),
                "client_proof_key_digest": client_proof_key_digest,
                "context_digest": context_digest.hex(),
                "holder_id": holder.index,
                "nonce": nonce,
                "omega_digest": None,
                "operation": "initialize",
                "operation_id": operation,
                "profile_id": profile_id,
                "session_id": session_id,
                "suite_id": APPSS_SUITE_ID,
                "version": appss_format(profile_id, "request"),
            }
            request_bytes = encode_checked(
                request,
                maximum=MAX_REQUEST_BYTES,
                validator=validate_request,
                label="aPPSS request",
            )
            response_bytes = endpoint.initialize(
                request_bytes, idempotency_key=secrets.token_hex(32)
            )
            response = canonical_decode(
                response_bytes,
                maximum=MAX_RESPONSE_BYTES,
                validator=validate_response,
                label="aPPSS response",
            )
            _validate_response_binding(
                response=response,
                request_bytes=request_bytes,
                holder_id=holder.index,
                context_digest=context_digest,
                admission_grant_digest=admission_grant_digest,
                client_proof_key_digest=client_proof_key_digest,
                nonce=nonce,
                omega_digest=None,
                operation="initialize",
                operation_id=operation,
                profile_id=profile_id,
                session_id=session_id,
            )
            output = native.appss_finalize(
                session, bytes.fromhex(response["evaluated_element"])
            )
            masks.append((holder.index, native.appss_derive_mask(instance, output)))
            response_bytes_by_holder.append(response_bytes)
        except (native.NativeAppssError, AppssFormatError, ValueError) as exc:
            raise AppssClientError("aPPSS initialization rejected") from exc

    try:
        public, recovery_secret = native.appss_initialize(
            context_digest,
            password,
            selected_threshold.k,
            selected_threshold.n,
            masks,
        )
        public_mapping = adapter._public_mapping(public)  # noqa: SLF001
        public_bytes = encode_checked(
            public_mapping,
            maximum=MAX_PUBLIC_STATE_BYTES,
            validator=validate_public_state,
            label="aPPSS public state",
        )
    except (native.NativeAppssError, AppssFormatError) as exc:
        raise AppssClientError("aPPSS initialization rejected") from exc

    transcript_digest = hashlib.sha256(b"".join(response_bytes_by_holder)).hexdigest()
    public_digest = hashlib.sha256(public_bytes).hexdigest()
    ready_digests: list[tuple[int, str]] = []
    for holder in selected:
        install = {
            "context_digest": context_digest.hex(),
            "holder_id": holder.index,
            "initialization_transcript_digest": transcript_digest,
            "operation_id": operation,
            "profile_id": profile_id,
            "public_state": public_mapping,
            "suite_id": APPSS_SUITE_ID,
            "version": appss_format(profile_id, "install"),
        }
        try:
            install_bytes = encode_checked(
                install,
                maximum=MAX_INSTALL_BYTES,
                validator=validate_install,
                label="aPPSS state install",
            )
            ready_bytes = endpoints[holder.index].install(
                install_bytes, idempotency_key=secrets.token_hex(32)
            )
            ready = canonical_decode(
                ready_bytes,
                maximum=MAX_READY_BYTES,
                validator=validate_ready,
                label="aPPSS ready acknowledgement",
            )
            if (
                ready["version"] != appss_format(profile_id, "ready")
                or ready["context_digest"] != context_digest.hex()
                or ready["holder_id"] != holder.index
                or ready["operation_id"] != operation
                or ready["public_state_digest"] != public_digest
            ):
                raise AppssClientError("aPPSS ready binding mismatch")
            ready_digests.append(
                (holder.index, hashlib.sha256(ready_bytes).hexdigest())
            )
        except (AppssFormatError, ValueError) as exc:
            raise AppssClientError("aPPSS initialization rejected") from exc
    return AppssInitializationResult(
        public_state=PublicRecoveryState(
            suite_id=APPSS_SUITE_ID,
            format_id=appss_format(profile_id, "public"),
            payload=public_bytes,
        ),
        ready_digests=tuple(ready_digests),
        recovery_secret=recovery_secret,
    )


def recover_with_parties(
    *,
    context: RecoveryContext,
    password_input: bytes,
    public_state: PublicRecoveryState,
    holders: Sequence[AppssHolderBinding],
    endpoints: Mapping[int, AppssPartyEndpoint],
    admission_grant_digest: str,
    client_proof_key_digest: str,
    operation_id: str | None = None,
) -> bytes:
    """Recover through exactly the profile threshold with no suite fallback."""

    adapter = AppssRecoveryAdapter()
    try:
        context_digest = adapter._context_digest(context)  # noqa: SLF001
        password = adapter._password(password_input)  # noqa: SLF001
        public = adapter.decode_public_state(public_state)
    except RecoverySuiteError as exc:
        raise AppssClientError("aPPSS recovery rejected") from exc
    if public["context_digest"] != context_digest.hex():
        raise AppssClientError("aPPSS recovery rejected")
    profile_id = str(public["profile_id"])
    threshold = int(public["k"])
    selected = tuple(holders)
    if (
        len(selected) != threshold
        or [holder.index for holder in selected]
        != sorted({holder.index for holder in selected})
        or any(endpoints.get(holder.index) is None for holder in selected)
    ):
        raise AppssClientError("invalid aPPSS holder selection")
    _validate_endpoint_bindings(selected, endpoints)
    _lower_hex(admission_grant_digest, "admission grant digest")
    _lower_hex(client_proof_key_digest, "client proof-key digest")
    operation = secrets.token_hex(32) if operation_id is None else operation_id
    _lower_hex(operation, "operation identifier")

    masks: list[tuple[int, bytes]] = []
    for holder in selected:
        endpoint = endpoints[holder.index]
        instance = instance_id(context_digest, holder)
        session_id = secrets.token_hex(32)
        nonce = secrets.token_hex(32)
        idempotency_key = secrets.token_hex(32)
        try:
            session, blinded = native.appss_blind(oprf_input(instance, password))
            request = {
                "admission_grant_digest": admission_grant_digest,
                "blinded_element": blinded.hex(),
                "client_proof_key_digest": client_proof_key_digest,
                "context_digest": context_digest.hex(),
                "holder_id": holder.index,
                "nonce": nonce,
                "omega_digest": public["omega_digest"],
                "operation": "recover",
                "operation_id": operation,
                "profile_id": profile_id,
                "session_id": session_id,
                "suite_id": APPSS_SUITE_ID,
                "version": appss_format(profile_id, "request"),
            }
            request_bytes = encode_checked(
                request,
                maximum=MAX_REQUEST_BYTES,
                validator=validate_request,
                label="aPPSS request",
            )
            response_bytes = endpoint.evaluate(
                request_bytes, idempotency_key=idempotency_key
            )
            response = canonical_decode(
                response_bytes,
                maximum=MAX_RESPONSE_BYTES,
                validator=validate_response,
                label="aPPSS response",
            )
            _validate_response_binding(
                response=response,
                request_bytes=request_bytes,
                holder_id=holder.index,
                context_digest=context_digest,
                admission_grant_digest=admission_grant_digest,
                client_proof_key_digest=client_proof_key_digest,
                nonce=nonce,
                omega_digest=public["omega_digest"],
                operation="recover",
                operation_id=operation,
                profile_id=profile_id,
                session_id=session_id,
            )
            output = native.appss_finalize(
                session, bytes.fromhex(response["evaluated_element"])
            )
            masks.append((holder.index, native.appss_derive_mask(instance, output)))
        except (native.NativeAppssError, AppssFormatError, ValueError) as exc:
            raise AppssClientError("aPPSS recovery rejected") from exc
    try:
        native_public = native.AppssPublicState.from_bytes(
            adapter._native_public_bytes(public)  # noqa: SLF001
        )
        return native.appss_recover(context_digest, password, native_public, masks)
    except native.NativeAppssError as exc:
        raise AppssClientError("aPPSS recovery rejected") from exc


def _lower_hex(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise AppssClientError(f"invalid {label}")
    return value


def _validate_endpoint_bindings(
    holders: Sequence[AppssHolderBinding],
    endpoints: Mapping[int, AppssPartyEndpoint],
) -> None:
    for holder in holders:
        endpoint = endpoints[holder.index]
        if (
            endpoint.holder_id != holder.index
            or endpoint.service_identity != holder.service_identity
        ):
            raise AppssClientError("aPPSS endpoint identity mismatch")


def _validate_response_binding(
    *,
    response: dict[str, object],
    request_bytes: bytes,
    holder_id: int,
    context_digest: bytes,
    admission_grant_digest: str,
    client_proof_key_digest: str,
    nonce: str,
    omega_digest: str | None,
    operation: str,
    operation_id: str,
    profile_id: str,
    session_id: str,
) -> None:
    if (
        response["admission_grant_digest"] != admission_grant_digest
        or response["client_proof_key_digest"] != client_proof_key_digest
        or response["context_digest"] != context_digest.hex()
        or response["holder_id"] != holder_id
        or response["nonce"] != nonce
        or response["omega_digest"] != omega_digest
        or response["operation"] != operation
        or response["operation_id"] != operation_id
        or response["profile_id"] != profile_id
        or response["request_digest"] != hashlib.sha256(request_bytes).hexdigest()
        or response["session_id"] != session_id
    ):
        raise AppssClientError("aPPSS response binding mismatch")


__all__ = [
    "AppssClientError",
    "AppssInitializationResult",
    "AppssPartyEndpoint",
    "initialize_with_parties",
    "recover_with_parties",
]
