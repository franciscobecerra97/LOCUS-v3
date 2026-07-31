from typing import final

class NativeTpassError(Exception): ...

@final
class PublicParameters:
    @staticmethod
    def from_bytes(encoded: bytes) -> PublicParameters: ...
    def to_bytes(self) -> bytes: ...
    @property
    def threshold(self) -> int: ...
    @property
    def parties(self) -> int: ...

@final
class PartyState:
    @staticmethod
    def from_secret_bytes(encoded: bytes) -> PartyState: ...
    def to_secret_bytes(self) -> bytes: ...
    @property
    def party_id(self) -> int: ...

@final
class ClientSession:
    def request_bytes(self) -> bytes: ...

@final
class PartyEphemeral: ...

def setup(
    recovery_id: bytes,
    canonical_recovery_input: bytes,
    threshold: int,
    parties: int,
) -> tuple[PublicParameters, list[PartyState], bytes]: ...
def begin_recovery(
    parameters: PublicParameters,
    recovery_id: bytes,
    canonical_recovery_input: bytes,
) -> ClientSession: ...
def prepare_commitment(
    parameters: PublicParameters,
    request: bytes,
    selected: list[int],
    state: PartyState,
) -> tuple[bytes, PartyEphemeral]: ...
def verify_and_respond(
    parameters: PublicParameters,
    request: bytes,
    selected: list[int],
    state: PartyState,
    ephemeral: PartyEphemeral,
    commitments: list[bytes],
) -> bytes: ...
def aggregate_responses(
    parameters: PublicParameters,
    request: bytes,
    selected: list[int],
    commitments: list[bytes],
    responses: list[bytes],
) -> bytes: ...
def finish_recovery(
    parameters: PublicParameters,
    session: ClientSession,
    gateway_response: bytes,
) -> bytes: ...
