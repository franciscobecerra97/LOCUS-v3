"""In-process recovery-party core guarded by durable attempt state."""

from __future__ import annotations

import secrets
from dataclasses import dataclass

from . import _tpass_native as native
from .attempt_certificates import AuthorizationCertificate, AuthorizerConfig
from .attempt_coordinator import AttemptCoordinator
from .party_store import (
    Conflict,
    InvalidState,
    PartyStore,
    SessionLost,
)


@dataclass(frozen=True)
class CommitmentResult:
    phase_instance_id: str
    commitment: bytes


class NativePartyService:
    """One native TPASS party with a durable pre-commitment guard.

    The object is deliberately transport-agnostic. The current HTTP adapter maps
    its failures to coarse authenticated-service responses; it delegates signed
    authorization installation and live freshness collection back to this core
    before any native secret-dependent operation.
    """

    def __init__(
        self,
        *,
        store: PartyStore,
        parameters: native.PublicParameters,
        state: native.PartyState,
        authorizer_config: AuthorizerConfig,
        freshness_coordinator: AttemptCoordinator,
        recover_open_phases: bool = True,
    ) -> None:
        self.store = store
        self.parameters = parameters
        self.state = state
        self.authorizer_config = authorizer_config
        self.freshness_coordinator = freshness_coordinator
        self._boot_nonce = secrets.token_hex(32)
        self._ephemerals: dict[str, native.PartyEphemeral] = {}
        self._freshness_by_sid: dict[str, str] = {}
        if recover_open_phases:
            self.store.mark_open_phases_lost()

    @property
    def party_id(self) -> int:
        return self.state.party_id

    def prepare_commitment(
        self,
        *,
        authorization_certificate: AuthorizationCertificate,
        request: bytes,
        selected: list[int],
    ) -> CommitmentResult:
        """Install authorization and prepare exactly one guarded commitment."""

        authorization = self.store.install_certificate(
            authorization_certificate, self.authorizer_config
        )
        freshness_digest = self._freshness_by_sid.get(authorization.sid)
        if freshness_digest is None:
            freshness = self.freshness_coordinator.certify_freshness(
                authorization=authorization_certificate,
                responding_party_id=self.party_id,
                boot_nonce=self._boot_nonce,
                response_nonce=secrets.token_hex(32),
            )
            freshness.verify(self.authorizer_config)
            freshness_digest = freshness.certificate_hash
            self._freshness_by_sid[authorization.sid] = freshness_digest
        reservation = self.store.reserve_commitment(
            bid=authorization.bid,
            epoch=authorization.epoch,
            sid=authorization.sid,
            party_id=self.party_id,
            request=request,
            selected=selected,
            certificate_hash=authorization.certificate_hash,
            freshness_digest=freshness_digest,
        )
        if reservation.state == "RESPONDED":
            if reservation.commitment is None:
                raise InvalidState("stored response has no commitment")
            return CommitmentResult(
                reservation.phase_instance_id, reservation.commitment
            )
        if reservation.state == "COMMITMENT_STORED":
            if reservation.phase_instance_id not in self._ephemerals:
                raise SessionLost("TPASS ephemeral is unavailable")
            if reservation.commitment is None:
                raise InvalidState("stored commitment is missing")
            return CommitmentResult(
                reservation.phase_instance_id, reservation.commitment
            )
        if reservation.state != "INTENT":
            raise InvalidState("invalid commitment reservation state")

        try:
            commitment, ephemeral = native.prepare_commitment(
                self.parameters,
                request,
                selected,
                self.state,
            )
            commitment_bytes = bytes(commitment)
            self.store.store_commitment(reservation.phase_instance_id, commitment_bytes)
        except Exception:
            self.store.mark_phase_lost(reservation.phase_instance_id)
            raise
        self._ephemerals[reservation.phase_instance_id] = ephemeral
        return CommitmentResult(reservation.phase_instance_id, commitment_bytes)

    def respond(
        self,
        *,
        sid: str | None = None,
        phase_instance_id: str,
        request: bytes,
        selected: list[int],
        commitments: list[bytes],
    ) -> bytes:
        reservation = self.store.validate_phase_binding(
            phase_instance_id,
            sid=sid,
            request=request,
            selected=selected,
        )
        if reservation.state == "RESPONDED":
            if reservation.response is None:
                raise InvalidState("stored TPASS response is missing")
            return reservation.response
        if reservation.state == "LOST":
            raise SessionLost("TPASS phase cannot be resumed")
        if reservation.state != "COMMITMENT_STORED":
            raise InvalidState("TPASS response is not ready")
        ephemeral = self._ephemerals.get(phase_instance_id)
        if ephemeral is None:
            raise SessionLost("TPASS ephemeral is unavailable")
        if reservation.commitment not in commitments:
            raise Conflict("own commitment is absent from transcript")
        try:
            response = bytes(
                native.verify_and_respond(
                    self.parameters,
                    request,
                    selected,
                    self.state,
                    ephemeral,
                    commitments,
                )
            )
            self.store.store_response(phase_instance_id, response)
        except Exception:
            self.store.mark_phase_lost(phase_instance_id)
            raise
        self._ephemerals.pop(phase_instance_id, None)
        return response
