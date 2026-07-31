# TPASS canonical wire format

Status: implemented external boundary for the research-grade Rust TPASS core.
This format is versioned but not yet frozen as a long-term compatibility promise.

## Problem statement

Recovery parties, the client, and the gateway need an unambiguous representation
of TPASS parameters and messages before they can run in separate processes. An
ad hoc JSON representation would introduce integer, ordering, Unicode, and
canonical-group-encoding ambiguity and could accidentally expose process-local
secret witnesses. The wire format therefore uses fixed binary fields and validates
every value when it crosses the Rust boundary.

## Threat assumptions and scope

The decoder treats every byte string as attacker-controlled. It detects malformed,
truncated, trailing, wrong-version, wrong-type, non-canonical scalar, invalid point,
duplicate-party, out-of-range-party, and non-canonical selected-set inputs where
applicable. Recovery identifiers are bounded before allocation, and public
configurations are limited to 255 parties to prevent hostile parameters from
driving impractical setup or selected-set allocations. Encoding does not provide confidentiality, authentication, replay
protection, authorization, or attempt control; those properties belong to the
transport and LOCUS service layers.

The party-state encoding contains secret shares. It must be encrypted at rest,
transported only over authenticated confidential channels, excluded from logs,
and erased from temporary buffers where the platform permits.

## Common encoding

Every object begins with:

| Field | Size | Value |
| --- | ---: | --- |
| Magic and version | 8 bytes | ASCII `LCTPASS` followed by byte `0x01` |
| Object kind | 1 byte | Type identifier from the table below |

Unsigned integers are 32-bit big-endian. A variable byte string is encoded as a
32-bit big-endian length followed by exactly that many bytes. Points are canonical
32-byte compressed Ristretto encodings. Scalars are canonical 32-byte scalar
encodings. Decoders reject any unconsumed trailing byte.

## Object layouts

| Kind | Object | Fields after common header |
| ---: | --- | --- |
| 1 | Public parameters | `threshold`, `parties`, `G1[32]`, `G2[32]` |
| 2 | Secret party state | `bytes(recovery_id)`, `threshold`, `parties`, `party_id`, `password_share[32]`, `secret_share[32]`, `digest_share[32]` |
| 3 | Client request | `bytes(recovery_id)`, `A[32]` |
| 4 | Party commitment | `party_id`, `B[32]`, `C[32]`, `D[32]`, `delta[32]` |
| 5 | Server response share | `party_id`, `C[32]`, `D[32]`, `E[32]`, `F[32]` |
| 6 | Gateway response | `bytes(recovery_id)`, `selected_count`, ordered `party_id[selected_count]`, `C[32]`, `D[32]`, `E[32]`, `F[32]` |

Public-parameter decoding reconstructs the configured group and rejects mismatched
`G1` or `G2` bytes. Party-state decoding revalidates threshold parameters, recovery
identifier length, party range, and all three secret scalars. Commitment and
response decoding validates party range and every point/scalar. Gateway selected
identifiers must already be unique and ascending; accepting multiple encodings of
the same set is forbidden.

## Deliberately non-serializable state

`ClientSession` contains the client's blinding scalar. `PartyEphemeral` contains a
party's per-attempt proof witnesses. Neither type has an external encoding. The
Python extension holds them in redacted native objects and consumes the client
session during finalization. A crash discards these values and requires a new
counted recovery session rather than resuming from serialized witnesses.

## Failure behavior

Rust returns typed `TpassError` values. The native Python module maps them to
`NativeTpassError` for internal orchestration. The current authenticated service
maps these and parsing/state failures to coarse response codes without stack
traces or field detail; the future public admission layer must further normalize
them to the generic externally visible recovery rejection defined by the LOCUS
protocol. No response may reveal which proof, password, or digest check failed.

## Tests and evidence boundary

The Rust suite round-trips every external object through a complete 3-of-5
protocol execution. For all six external object types it rejects every truncated
prefix, wrong object kind, and trailing data. Focused mutations cover invalid
threshold/resource bounds, generator substitution, empty/oversized recovery
identifiers, zero/out-of-range/duplicate party identifiers, non-canonical selected
sets, invalid or identity points by protocol position, and non-canonical scalars.

The synthetic deterministic vector at
`tpass-core/test-vectors/yi-zk-ristretto255-v1.txt` freezes a full 2-of-3
enrollment and recovery transcript. A Rust integration test regenerates every
field from declared ChaCha20 test seeds, while Python separately loads the frozen
parameter and party-state encodings and completes a fresh recovery through PyO3.
The property matrix exhaustively recovers with every valid subset for all
`1 <= t <= n <= 5`, including reversed input ordering; the complete Python flow
separately covers `(2,3)`, `(3,5)`, and `(5,9)`.

These tests establish encoding consistency, deterministic regression coverage,
and local cross-language interoperability. Because both paths ultimately use the
same Rust algebraic core, they are not an independent cryptographic implementation
or audit and do not establish transport security, durable isolation, or a global
attempt bound.
