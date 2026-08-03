from typing import final

class NativeTpassError(Exception): ...
class NativeAppssError(Exception): ...

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

@final
class AppssServerKey:
    @staticmethod
    def from_secret_bytes(encoded: bytes) -> AppssServerKey: ...
    def to_secret_bytes(self) -> bytes: ...
    def commitment(self) -> bytes: ...
    @property
    def holder_id(self) -> int: ...
    @property
    def context_digest(self) -> bytes: ...

@final
class AppssClientBlind: ...

@final
class AppssPublicState:
    @staticmethod
    def from_bytes(encoded: bytes) -> AppssPublicState: ...
    def to_bytes(self) -> bytes: ...
    @property
    def threshold(self) -> int: ...
    @property
    def parties(self) -> int: ...
    @property
    def context_digest(self) -> bytes: ...
    @property
    def commitment(self) -> bytes: ...
    @property
    def omega_digest(self) -> bytes: ...
    @property
    def masked_shares(self) -> list[tuple[int, bytes]]: ...

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
def appss_generate_server_key(
    context_digest: bytes, holder_id: int
) -> AppssServerKey: ...
def appss_blind(input: bytes) -> tuple[AppssClientBlind, bytes]: ...
def appss_blind_evaluate(
    key: AppssServerKey,
    context_digest: bytes,
    blinded_element: bytes,
) -> bytes: ...
def appss_finalize(session: AppssClientBlind, evaluated_element: bytes) -> bytes: ...
def appss_derive_mask(instance_id: bytes, oprf_output: bytes) -> bytes: ...
def appss_initialize(
    context_digest: bytes,
    password_input: bytes,
    threshold: int,
    parties: int,
    masks: list[tuple[int, bytes]],
) -> tuple[AppssPublicState, bytes]: ...
def appss_initialize_fixture(
    context_digest: bytes,
    password_input: bytes,
    threshold: int,
    parties: int,
    masks: list[tuple[int, bytes]],
) -> tuple[AppssPublicState, bytes]: ...
def appss_recover(
    context_digest: bytes,
    password_input: bytes,
    public_state: AppssPublicState,
    masks: list[tuple[int, bytes]],
) -> bytes: ...
def appss_recover_fixture(
    context_digest: bytes,
    password_input: bytes,
    public_state: AppssPublicState,
    masks: list[tuple[int, bytes]],
) -> bytes: ...
