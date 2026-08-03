"""Separate aPPSS adapter for the suite-neutral LOCUS recovery contract."""

from __future__ import annotations

import hashlib
from typing import Any

from . import _tpass_native as native
from .appss_formats import (
    APPSS_PARTY_STATE_FORMAT,
    APPSS_PROFILE_2_OF_3,
    APPSS_PUBLIC_STATE_FORMAT,
    APPSS_SUITE_ID,
    MAX_PARTY_STATE_BYTES,
    MAX_PUBLIC_STATE_BYTES,
    AppssFormatError,
    AppssHolderBinding,
    canonical_decode,
    encode_checked,
    instance_id,
    oprf_input,
    validate_party_state,
    validate_public_state,
)
from .contracts import (
    PartyRecoveryState,
    PublicRecoveryState,
    RecoveryClientSession,
    RecoveryContext,
    RecoveryRequest,
    RecoveryResponse,
    RecoverySuiteEnrollment,
    ThresholdParameters,
)
from .yi_compat import RecoverySuiteError


class AppssRecoveryAdapter:
    """D017 aPPSS behind the same high-entropy recovery-secret contract.

    ``initialize`` is a centrally orchestrated unit fixture required by the
    original in-memory protocol. It is never used as evidence for authenticated
    distributed initialization; P5A.4 owns that path.
    """

    suite_id = APPSS_SUITE_ID
    public_state_format = APPSS_PUBLIC_STATE_FORMAT
    party_state_format = APPSS_PARTY_STATE_FORMAT
    request_type = RecoveryRequest
    response_type = RecoveryResponse
    client_session_type = RecoveryClientSession

    @staticmethod
    def _holder(index: int) -> AppssHolderBinding:
        return AppssHolderBinding(
            index=index,
            party_id=f"party-{index}",
            service_identity="fixture-only",
        )

    @staticmethod
    def _context_digest(context: RecoveryContext) -> bytes:
        if context.suite_id != APPSS_SUITE_ID:
            raise RecoverySuiteError("recovery context selects another suite")
        if context.suite_context_digest is None:
            raise RecoverySuiteError("aPPSS context digest is missing")
        return bytes.fromhex(context.suite_context_digest)

    @staticmethod
    def _password(password_input: bytes) -> bytes:
        if not isinstance(password_input, bytes) or len(password_input) != 32:
            raise RecoverySuiteError("invalid aPPSS password input")
        return password_input

    @staticmethod
    def _topology(threshold: ThresholdParameters) -> None:
        if threshold != ThresholdParameters(k=2, n=3):
            raise RecoverySuiteError("unsupported aPPSS topology")

    @staticmethod
    def _key_from_state(state: dict[str, Any]) -> native.AppssServerKey:
        context = bytes.fromhex(state["context_digest"])
        holder = int(state["holder_id"])
        key_bytes = (
            b"LAK1\x01"
            + holder.to_bytes(2, "big")
            + context
            + bytes.fromhex(state["oprf_key"])
        )
        try:
            key = native.AppssServerKey.from_secret_bytes(key_bytes)
        except native.NativeAppssError as exc:
            raise RecoverySuiteError("invalid aPPSS party state") from exc
        if key.commitment().hex() != state["key_commitment"]:
            raise RecoverySuiteError("aPPSS key commitment mismatch")
        return key

    @classmethod
    def _evaluate_masks(
        cls,
        *,
        context_digest: bytes,
        password_input: bytes,
        keys: tuple[native.AppssServerKey, ...],
    ) -> list[tuple[int, bytes]]:
        masks: list[tuple[int, bytes]] = []
        for key in keys:
            holder = cls._holder(key.holder_id)
            instance = instance_id(context_digest, holder)
            try:
                session, blinded = native.appss_blind(
                    oprf_input(instance, password_input)
                )
                evaluated = native.appss_blind_evaluate(key, context_digest, blinded)
                output = native.appss_finalize(session, evaluated)
                masks.append((holder.index, native.appss_derive_mask(instance, output)))
            except native.NativeAppssError as exc:
                raise RecoverySuiteError("aPPSS OPRF evaluation failed") from exc
        return masks

    @staticmethod
    def _public_mapping(state: native.AppssPublicState) -> dict[str, Any]:
        mapping = {
            "commitment": state.commitment.hex(),
            "context_digest": state.context_digest.hex(),
            "k": state.threshold,
            "masked_shares": [
                {"index": index, "value": value.hex()}
                for index, value in state.masked_shares
            ],
            "n": state.parties,
            "omega_digest": state.omega_digest.hex(),
            "oprf_profile": "LOCUS-APPSS-OPRF-RISTRETTO255-SHA512-v1",
            "profile_id": APPSS_PROFILE_2_OF_3,
            "suite_id": APPSS_SUITE_ID,
            "version": APPSS_PUBLIC_STATE_FORMAT,
        }
        validate_public_state(mapping)
        return mapping

    def decode_public_state(self, state: PublicRecoveryState) -> dict[str, Any]:
        if (
            state.suite_id != self.suite_id
            or state.format_id != self.public_state_format
        ):
            raise RecoverySuiteError("unsupported aPPSS public state")
        try:
            return canonical_decode(
                state.payload,
                maximum=MAX_PUBLIC_STATE_BYTES,
                validator=validate_public_state,
                label="aPPSS public state",
            )
        except AppssFormatError as exc:
            raise RecoverySuiteError("invalid aPPSS public state") from exc

    def decode_party_state(self, state: PartyRecoveryState) -> dict[str, Any]:
        if (
            state.suite_id != self.suite_id
            or state.format_id != self.party_state_format
        ):
            raise RecoverySuiteError("unsupported aPPSS party state")
        try:
            decoded = canonical_decode(
                state.payload,
                maximum=MAX_PARTY_STATE_BYTES,
                validator=validate_party_state,
                label="aPPSS party state",
            )
        except AppssFormatError as exc:
            raise RecoverySuiteError("invalid aPPSS party state") from exc
        if decoded["holder_id"] != state.holder_id:
            raise RecoverySuiteError("aPPSS party-state holder mismatch")
        return decoded

    def initialize(
        self,
        *,
        context: RecoveryContext,
        password_input: bytes,
        threshold: ThresholdParameters,
    ) -> RecoverySuiteEnrollment:
        self._topology(threshold)
        context_digest = self._context_digest(context)
        password = self._password(password_input)
        try:
            keys = tuple(
                native.appss_generate_server_key(context_digest, holder)
                for holder in range(1, 4)
            )
            masks = self._evaluate_masks(
                context_digest=context_digest,
                password_input=password,
                keys=keys,
            )
            public, secret = native.appss_initialize_fixture(
                context_digest, password, 2, 3, masks
            )
            public_mapping = self._public_mapping(public)
            public_payload = encode_checked(
                public_mapping,
                maximum=MAX_PUBLIC_STATE_BYTES,
                validator=validate_public_state,
                label="aPPSS public state",
            )
            public_digest = hashlib.sha256(public_payload).hexdigest()
            party_states: list[PartyRecoveryState] = []
            for key in keys:
                native_key = key.to_secret_bytes()
                mapping = {
                    "context_digest": context_digest.hex(),
                    "holder_id": key.holder_id,
                    "key_commitment": key.commitment().hex(),
                    "omega_digest": public.omega_digest.hex(),
                    "oprf_key": native_key[39:71].hex(),
                    "profile_id": APPSS_PROFILE_2_OF_3,
                    "public_state_digest": public_digest,
                    "suite_id": APPSS_SUITE_ID,
                    "version": APPSS_PARTY_STATE_FORMAT,
                }
                payload = encode_checked(
                    mapping,
                    maximum=MAX_PARTY_STATE_BYTES,
                    validator=validate_party_state,
                    label="aPPSS party state",
                )
                party_states.append(
                    PartyRecoveryState(
                        suite_id=APPSS_SUITE_ID,
                        format_id=APPSS_PARTY_STATE_FORMAT,
                        holder_id=key.holder_id,
                        payload=payload,
                    )
                )
            return RecoverySuiteEnrollment(
                public_state=PublicRecoveryState(
                    suite_id=APPSS_SUITE_ID,
                    format_id=APPSS_PUBLIC_STATE_FORMAT,
                    payload=public_payload,
                ),
                party_states=tuple(party_states),
                recovery_secret=secret,
            )
        except (native.NativeAppssError, AppssFormatError) as exc:
            raise RecoverySuiteError("aPPSS enrollment failed") from exc

    def recover(
        self,
        *,
        context: RecoveryContext,
        password_input: bytes,
        public_state: PublicRecoveryState,
        party_states: tuple[PartyRecoveryState, ...],
    ) -> bytes:
        context_digest = self._context_digest(context)
        password = self._password(password_input)
        public_mapping = self.decode_public_state(public_state)
        if public_mapping["context_digest"] != context_digest.hex():
            raise RecoverySuiteError("aPPSS public-state context mismatch")
        if len(party_states) != 2:
            raise RecoverySuiteError("aPPSS recovery requires exactly two holders")
        if [state.holder_id for state in party_states] != sorted(
            {state.holder_id for state in party_states}
        ):
            raise RecoverySuiteError("noncanonical aPPSS holder selection")
        decoded = tuple(self.decode_party_state(state) for state in party_states)
        public_digest = hashlib.sha256(public_state.payload).hexdigest()
        for state in decoded:
            if (
                state["context_digest"] != context_digest.hex()
                or state["omega_digest"] != public_mapping["omega_digest"]
                or state["public_state_digest"] != public_digest
            ):
                raise RecoverySuiteError("aPPSS state binding mismatch")
        keys = tuple(self._key_from_state(state) for state in decoded)
        masks = self._evaluate_masks(
            context_digest=context_digest,
            password_input=password,
            keys=keys,
        )
        native_public = native.AppssPublicState.from_bytes(
            self._native_public_bytes(public_mapping)
        )
        try:
            return native.appss_recover_fixture(
                context_digest, password, native_public, masks
            )
        except native.NativeAppssError as exc:
            raise RecoverySuiteError("aPPSS recovery failed") from exc

    @staticmethod
    def _native_public_bytes(mapping: dict[str, Any]) -> bytes:
        output = bytearray(b"LAP1\x01")
        output.extend(bytes.fromhex(mapping["context_digest"]))
        output.extend(int(mapping["k"]).to_bytes(2, "big"))
        output.extend(int(mapping["n"]).to_bytes(2, "big"))
        output.extend(len(mapping["masked_shares"]).to_bytes(2, "big"))
        for share in mapping["masked_shares"]:
            output.extend(int(share["index"]).to_bytes(2, "big"))
            output.extend(bytes.fromhex(share["value"]))
        output.extend(bytes.fromhex(mapping["commitment"]))
        output.extend(bytes.fromhex(mapping["omega_digest"]))
        return bytes(output)


__all__ = ["AppssRecoveryAdapter"]
