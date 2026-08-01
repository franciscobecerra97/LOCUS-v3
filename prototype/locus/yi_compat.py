"""Suite-neutral compatibility adapter for the frozen native Yi TPASS path."""

from __future__ import annotations

import json
from typing import Any, cast

from .codec import encode
from .contracts import (
    MAX_OPAQUE_PUBLIC_BYTES,
    MAX_OPAQUE_SECRET_STATE_BYTES,
    PartyRecoveryState,
    PublicRecoveryState,
    RecoveryClientSession,
    RecoveryContext,
    RecoveryRequest,
    RecoveryResponse,
    RecoverySuiteEnrollment,
    ThresholdParameters,
)
from .tpass import NativeTpassBackend, TpassError

YI_RECOVERY_SUITE_ID = "LOCUS-TPASS-YI-ZK-RISTRETTO255-v1"


class RecoverySuiteError(Exception):
    """A suite-neutral recovery operation or adapter boundary failed."""


def _reject_duplicate_members(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate JSON member")
        value[key] = item
    return value


def _decode_canonical_mapping(
    payload: bytes,
    *,
    expected_keys: set[str],
    maximum: int,
    label: str,
) -> dict[str, Any]:
    if not payload or len(payload) > maximum:
        raise RecoverySuiteError(f"invalid {label}")
    try:
        decoded = json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_members,
            parse_constant=lambda _value: (_ for _ in ()).throw(
                ValueError("non-finite JSON number")
            ),
        )
        if (
            not isinstance(decoded, dict)
            or set(decoded) != expected_keys
            or encode(decoded) != payload
        ):
            raise ValueError("noncanonical mapping")
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
        TypeError,
        ValueError,
        RecursionError,
    ) as exc:
        raise RecoverySuiteError(f"invalid {label}") from exc
    return cast(dict[str, Any], decoded)


class YiTpassRecoveryAdapter:
    """Expose the frozen Yi backend through the P1.3 suite-neutral contract.

    The adapter adds no new Yi encoding. Its opaque payloads contain the exact
    canonical representation of the existing Python dictionaries, whose
    embedded native ``parameters`` and ``state`` bytes retain
    ``LOCUS-TPASS-wire-v1`` unchanged.
    """

    suite_id = YI_RECOVERY_SUITE_ID
    public_state_format = NativeTpassBackend.encoding
    party_state_format = NativeTpassBackend.encoding
    request_type = RecoveryRequest
    response_type = RecoveryResponse
    client_session_type = RecoveryClientSession

    _public_keys = {
        "backend",
        "threshold",
        "parties",
        "encoding",
        "parameters",
    }
    _party_keys = {"party_id", "encoding", "state"}

    def __init__(self, backend: NativeTpassBackend | None = None) -> None:
        self._backend = backend or NativeTpassBackend()

    @staticmethod
    def _password_scalar(password_input: bytes) -> int:
        if not isinstance(password_input, bytes) or len(password_input) != 32:
            raise RecoverySuiteError("invalid Yi password input")
        return int.from_bytes(password_input, "big")

    def _validate_context(self, context: RecoveryContext) -> None:
        if context.suite_id != self.suite_id:
            raise RecoverySuiteError("recovery context selects another suite")

    def public_state_from_legacy(
        self, public_params: dict[str, Any]
    ) -> PublicRecoveryState:
        payload = encode(public_params)
        state = PublicRecoveryState(
            suite_id=self.suite_id,
            format_id=self.public_state_format,
            payload=payload,
        )
        self.decode_public_state(state)
        return state

    def party_state_from_legacy(
        self, party_state: dict[str, Any]
    ) -> PartyRecoveryState:
        payload = encode(party_state)
        decoded = _decode_canonical_mapping(
            payload,
            expected_keys=self._party_keys,
            maximum=MAX_OPAQUE_SECRET_STATE_BYTES,
            label="Yi party state",
        )
        party_id = decoded.get("party_id")
        if isinstance(party_id, bool) or not isinstance(party_id, int):
            raise RecoverySuiteError("invalid Yi party state")
        state = PartyRecoveryState(
            suite_id=self.suite_id,
            format_id=self.party_state_format,
            holder_id=party_id,
            payload=payload,
        )
        self.decode_party_state(state)
        return state

    def decode_public_state(self, state: PublicRecoveryState) -> dict[str, Any]:
        if (
            state.suite_id != self.suite_id
            or state.format_id != self.public_state_format
        ):
            raise RecoverySuiteError("unsupported Yi public state")
        decoded = _decode_canonical_mapping(
            state.payload,
            expected_keys=self._public_keys,
            maximum=MAX_OPAQUE_PUBLIC_BYTES,
            label="Yi public state",
        )
        if (
            decoded.get("backend") != self._backend.backend
            or decoded.get("encoding") != self.public_state_format
        ):
            raise RecoverySuiteError("unsupported Yi public state")
        return decoded

    def decode_party_state(self, state: PartyRecoveryState) -> dict[str, Any]:
        if (
            state.suite_id != self.suite_id
            or state.format_id != self.party_state_format
        ):
            raise RecoverySuiteError("unsupported Yi party state")
        decoded = _decode_canonical_mapping(
            state.payload,
            expected_keys=self._party_keys,
            maximum=MAX_OPAQUE_SECRET_STATE_BYTES,
            label="Yi party state",
        )
        if (
            decoded.get("party_id") != state.holder_id
            or decoded.get("encoding") != self.party_state_format
        ):
            raise RecoverySuiteError("Yi party-state binding mismatch")
        return decoded

    def initialize(
        self,
        *,
        context: RecoveryContext,
        password_input: bytes,
        threshold: ThresholdParameters,
    ) -> RecoverySuiteEnrollment:
        self._validate_context(context)
        try:
            enrollment = self._backend.setup(
                recovery_id=context.recovery_id,
                password=self._password_scalar(password_input),
                digest_context=context.digest_context,
                threshold=threshold.k,
                parties=threshold.n,
            )
            public_state = self.public_state_from_legacy(enrollment.public_params)
            party_states = tuple(
                self.party_state_from_legacy(state) for state in enrollment.party_states
            )
            if len(party_states) != threshold.n:
                raise RecoverySuiteError("Yi enrollment party count mismatch")
            return RecoverySuiteEnrollment(
                public_state=public_state,
                party_states=party_states,
                recovery_secret=enrollment.group_secret,
            )
        except TpassError as exc:
            raise RecoverySuiteError("Yi enrollment failed") from exc

    def recover(
        self,
        *,
        context: RecoveryContext,
        password_input: bytes,
        public_state: PublicRecoveryState,
        party_states: tuple[PartyRecoveryState, ...],
    ) -> bytes:
        self._validate_context(context)
        public_params = self.decode_public_state(public_state)
        threshold = public_params.get("threshold")
        if isinstance(threshold, bool) or not isinstance(threshold, int):
            raise RecoverySuiteError("invalid Yi public state")
        if len(party_states) < threshold:
            raise RecoverySuiteError("not enough Yi recovery holders")
        selected = party_states[:threshold]
        holder_ids = [state.holder_id for state in selected]
        if len(holder_ids) != len(set(holder_ids)):
            raise RecoverySuiteError("duplicate Yi recovery holder")
        decoded_states = [self.decode_party_state(state) for state in selected]
        try:
            return self._backend.recover(
                recovery_id=context.recovery_id,
                password_attempt=self._password_scalar(password_input),
                digest_context=context.digest_context,
                public_params=public_params,
                party_states=decoded_states,
            )
        except TpassError as exc:
            raise RecoverySuiteError("Yi recovery failed") from exc


__all__ = [
    "RecoverySuiteError",
    "YI_RECOVERY_SUITE_ID",
    "YiTpassRecoveryAdapter",
]
