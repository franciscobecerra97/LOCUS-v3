"""Transient aPPSS client orchestration over opaque authenticated endpoints."""

from __future__ import annotations

import hashlib
import secrets
from collections.abc import Mapping, Sequence
from typing import Protocol

from . import _tpass_native as native
from .appss import AppssRecoveryAdapter
from .appss_formats import (
    APPSS_PROFILE_2_OF_3,
    APPSS_REQUEST_FORMAT,
    APPSS_SUITE_ID,
    MAX_REQUEST_BYTES,
    MAX_RESPONSE_BYTES,
    AppssFormatError,
    AppssHolderBinding,
    canonical_decode,
    encode_checked,
    instance_id,
    oprf_input,
    validate_request,
    validate_response,
)
from .contracts import PublicRecoveryState, RecoveryContext
from .yi_compat import RecoverySuiteError


class AppssPartyEndpoint(Protocol):
    """One authenticated recipient-bound aPPSS evaluation endpoint."""

    @property
    def holder_id(self) -> int: ...

    def evaluate(self, request_bytes: bytes, *, idempotency_key: str) -> bytes: ...


class AppssClientError(RecoverySuiteError):
    """The distributed aPPSS client failed without exposing a cue predicate."""


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
    """Recover through exactly two authenticated holders with no suite fallback."""

    adapter = AppssRecoveryAdapter()
    try:
        context_digest = adapter._context_digest(context)  # noqa: SLF001
        password = adapter._password(password_input)  # noqa: SLF001
        public = adapter.decode_public_state(public_state)
    except RecoverySuiteError as exc:
        raise AppssClientError("aPPSS recovery rejected") from exc
    if public["context_digest"] != context_digest.hex():
        raise AppssClientError("aPPSS recovery rejected")
    selected = tuple(holders)
    if (
        len(selected) != 2
        or [holder.index for holder in selected]
        != sorted({holder.index for holder in selected})
        or any(endpoints.get(holder.index) is None for holder in selected)
    ):
        raise AppssClientError("invalid aPPSS holder selection")
    _lower_hex(admission_grant_digest, "admission grant digest")
    _lower_hex(client_proof_key_digest, "client proof-key digest")
    operation = secrets.token_hex(32) if operation_id is None else operation_id
    _lower_hex(operation, "operation identifier")

    masks: list[tuple[int, bytes]] = []
    for holder in selected:
        endpoint = endpoints[holder.index]
        if endpoint.holder_id != holder.index:
            raise AppssClientError("aPPSS endpoint recipient mismatch")
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
                "profile_id": APPSS_PROFILE_2_OF_3,
                "session_id": session_id,
                "suite_id": APPSS_SUITE_ID,
                "version": APPSS_REQUEST_FORMAT,
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
            if (
                response["admission_grant_digest"] != admission_grant_digest
                or response["client_proof_key_digest"] != client_proof_key_digest
                or response["context_digest"] != context_digest.hex()
                or response["holder_id"] != holder.index
                or response["nonce"] != nonce
                or response["omega_digest"] != public["omega_digest"]
                or response["operation"] != "recover"
                or response["operation_id"] != operation
                or response["request_digest"]
                != hashlib.sha256(request_bytes).hexdigest()
                or response["session_id"] != session_id
            ):
                raise AppssClientError("aPPSS response binding mismatch")
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
        return native.appss_recover_fixture(
            context_digest, password, native_public, masks
        )
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


__all__ = [
    "AppssClientError",
    "AppssPartyEndpoint",
    "recover_with_parties",
]
