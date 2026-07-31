# LOCUS Cryptographic Design

Status: implementation design for the paper-facing TPASS core. This is research-grade code, not audited or production-ready cryptography.

## Decision

LOCUS retains Python for client orchestration, service integration, tests, and experiments. The paper-facing TPASS primitive is implemented as a Rust library in `tpass-core/`. A narrow PyO3 boundary exposes the versioned protocol phases and canonical encodings to the Python LOCUS flow while keeping group/scalar operations and non-serializable witnesses in Rust.

The source construction is Protocol 2, the zero-knowledge-proof-based `t`-out-of-`n` TPASS protocol in Yi, Tari, Hao, Chen, and Liu, *Efficient threshold password-authenticated secret sharing protocols*, Journal of Parallel and Distributed Computing 128 (2019), 57-70, DOI 10.1016/j.jpdc.2019.01.013. The local source is `extra/TPASS.pdf`, especially Sections 3.2, 3.3, 4.2, and Figure 3.

The authors report an experimental implementation using the Java SE 1.7 system library, a 1024-bit group, and a 160-bit group order. The article does not provide source code or test vectors. LOCUS does not copy those obsolete parameters or treat the historical implementation language as a requirement.

## Problem Statement

The primitive distributes a password, a secret exponent, and a digest of the resulting group secret among `n` parties using degree-`t-1` Shamir polynomials. A client that presents the enrolled password to any valid threshold set recovers the group secret. A wrong password produces a value that fails the final digest relation. Fewer than `t` stored party states should not provide a local password-verification oracle under the construction's assumptions.

The cryptographic primitive does not itself implement durable attempt control, request authorization, transport security, replay protection, rollback protection, or party lifecycle. Those are separate LOCUS mechanisms and must not be inferred from successful TPASS tests.

## Threat Assumptions

The implementation preserves the source construction's relevant assumptions:

- the discrete-logarithm and decisional Diffie-Hellman problems are hard in the selected prime-order group;
- no participant knows the discrete logarithm of `g2` with respect to `g1`;
- the transcript hash is collision resistant and is modeled as producing unbiased scalars for this implementation mapping;
- the one-phase proof `(C_i, D_i, delta_i)` has the non-interactive proof-of-knowledge property assumed in Section 4.2 of the source article;
- enrollment shares reach the intended party over authenticated confidential channels;
- the client endpoint is not compromised during enrollment or recovery;
- at least one party remains honest for claims that depend on the threshold adversary bound.

The source article assumes, rather than reduces to a standard named proof system, the proof-of-knowledge property of its one-equation server proof. Faithfully implementing and testing the verification equation does not independently establish that assumption. This point requires cryptographic review before the paper makes a strong active-security claim.

## Primitive And Parameter Mapping

The source article uses multiplicative notation. The implementation uses additive Ristretto notation:

| Source | Rust implementation |
| --- | --- |
| prime-order group `G` | Ristretto255 via `curve25519-dalek` |
| `g1` | canonical Ristretto basepoint `G1` |
| independently generated `g2` | `G2`, derived by SHA-512-to-Ristretto with a fixed LOCUS domain |
| scalar field `Z_q` | canonical `curve25519_dalek::Scalar` |
| generic `H` | SHA-512 transcripts reduced to a scalar with explicit domain separation and length-prefixing |
| group multiplication/division | point addition/subtraction |
| exponentiation | scalar multiplication |

`G2` is derived with a transparent hash-to-group procedure so its discrete-logarithm relation to `G1` is not known. This replaces the article's referenced multiparty generator-generation ceremony. It retains the required unknown-relation goal but changes the parameter-generation assumption and must be stated as a LOCUS instantiation choice.

Ristretto255 targets approximately 128-bit classical security. Production executions use operating-system cryptographic randomness through `rand_core::OsRng`; seeded generators are confined to tests and reproducible test vectors.

For the surrounding LOCUS backup path, the implemented primitives are
HKDF-SHA-256 to derive a 32-byte wrapping key directly from the recovered encoded
group secret, and AES-256-GCM with a fresh 96-bit nonce per independently derived
key. The 16-byte recovery nonce is the HKDF salt; the canonical info binds the
backup identifier and explicit positive epoch. Canonical backup metadata is
authenticated as associated data. Nonce uniqueness is mandatory. These
operations use pinned `cryptography` 49.0.0 rather than custom implementations;
`docs/backup-cryptography.md` defines the exact format and evidence boundary,
and `docs/paper-protocol-mapping.md` fixes the complete evaluated composition.

Dependencies are pinned in `tpass-core/Cargo.toml` and `tpass-core/Cargo.lock`. Unsafe Rust is forbidden in the crate. The cryptographic library provides canonical point encodings, canonical scalar parsing, and prime-order group behavior.

## Protocol Mapping

### Enrollment

For recovery identifier `ID`, password scalar `pw`, secret exponent `s`, threshold `t`, and party count `n`:

1. Compute group secret `S = s * G2`.
2. Compute digest scalar `theta = H_digest(ID, encode(S))`.
3. Sample independent degree-`t-1` polynomials `f1`, `f2`, and `f3` with constant terms `pw`, `s`, and `theta`.
4. Party `i` receives only `(ID, i, f1(i), f2(i), f3(i))`.

### Client request

The client samples nonzero `r` and sends:

`A = r * G1 - pw_attempt * G2`.

The local client session retains `r` until final retrieval and then zeroizes it.

### One-phase server proof and response

For the selected party identifiers, party `i` computes its Lagrange coefficient at zero:

`a_i = product_{j != i} j / (j - i)`.

It samples nonzero `r_i`, `c_i`, and `d_i` and computes:

`B_i = r_i * G1 + (a_i * f1(i)) * G2`

`C_i = c_i * G1`

`D_i = d_i * G1`

`h_i = H_proof(ID, A, i, B_i, C_i, D_i)`

`H_i = H_proof_2(h_i)`

`delta_i = h_i * c_i + H_i * d_i`.

Every selected party verifies every proof using:

`delta_j * G1 == h_j * C_j + H_j * D_j`.

After verification, define:

`C = sum C_j`, `D = sum D_j`, `h = H_aggregate(ID, A, selected_ids, C, D)`, and `W = A + sum B_j`.

Party `i` returns:

`E_i = (a_i * f2(i) * h) * G2 - r_i * C + c_i * W`

`F_i = (a_i * f3(i) * h) * G2 - r_i * D + d_i * W`.

The gateway adds the response shares to obtain `E` and `F`.

### Client finish

The client computes:

`S = h^-1 * (E - r * C)`

`T = h^-1 * (F - r * D)`

and accepts only when:

`T == H_digest(ID, encode(S)) * G2`.

The implementation rejects a zero aggregate challenge rather than attempting to invert it.

## Domain Separation And Encoding

All transcript hashes start with the protocol version and a distinct operation label. Every variable-length field is length-prefixed. Party identifiers and selected-party ordering are explicitly included where they affect a message. Points use canonical 32-byte compressed Ristretto encodings. Scalars entering from an external boundary must use canonical 32-byte encodings.

These rules remove serialization ambiguity and prevent a hash from one protocol role being reused in another role. They are a concrete LOCUS encoding choice; the source article specifies only a generic hash function.

The implemented external boundary is specified in `docs/tpass-wire-format.md`.
It uses an eight-byte magic/version prefix, a one-byte object kind, big-endian
fixed-width integers, length-prefixed recovery identifiers, canonical 32-byte
Ristretto points/scalars, canonical selected-party ordering, and exact
end-of-input checks. Public parameters, long-lived party state, client requests,
party commitments, server response shares, and gateway responses are encoded.
Client blinders and party proof witnesses are deliberately not serializable.

`tpass-python/` exposes these types and protocol phases through a PyO3 abi3
extension built by pinned maturin. Secret party state crosses Python only as an
explicitly named secret byte encoding or a redacted native object; the binding
does not use JSON, a global handle registry, or a Python reimplementation of the
group equations. Native errors remain internal and must be normalized by the
future network service.

## Invariants

- A party state is bound to one recovery identifier and one `(t,n)` parameter set.
- Party identifiers are nonzero, unique, within the enrolled party range, and ordered canonically for transcripts.
- A recovery set contains at least `t` parties and no duplicates.
- A public configuration contains at most 255 parties, bounding allocations
  induced by attacker-controlled parameters while exceeding all planned profiles.
- A party responds only after all selected proof messages validate.
- All received points decode canonically and required proof points are not the identity.
- A client returns a secret only after the final digest relation succeeds.
- Whole passwords, whole secret exponents, and whole digest scalars are never stored in party state.
- Secret-bearing Rust types redact their debug representation and zeroize ephemeral or retired scalar material where the platform and dependency permit it.

## Failure Behavior

Malformed parameters, mismatched recovery identifiers, duplicate or out-of-range party identifiers, insufficient parties, missing commitments or responses, invalid point encodings, identity proof points, invalid proof equations, zero challenges, and final digest mismatches return typed errors. The library does not log secret inputs. A service layer must map these internal failures to a generic external recovery rejection.

No TPASS failure is itself an attempt-control decision. `prepare_commitment` is
already secret-state-dependent, so the service must durably install the exact
attempt authorization and freshness evidence before invoking it, not merely
before `verify_and_respond`.

At the deployed orchestration boundary, the TPASS subset is selected from
quorum-consistent party summaries before authorization and is then immutable for
the commitment and response phases. Those selected calls run concurrently under
bounded phase deadlines. Failure after authorization is generic, never causes a
mid-attempt subset switch, and does not restore the attempt. These service-level
semantics are specified in `docs/party-failure-policy.md`; they do not change the
TPASS algebra or establish Byzantine liveness.

## Test Plan

The initial Rust test suite covers:

- successful recovery;
- a wrong-password final-check failure;
- arbitrary valid threshold subsets;
- insufficient and duplicate party sets;
- tampered proof rejection;
- tampered response rejection;
- recovery-identifier mismatch;
- deterministic execution using a seeded test-only random generator;
- secret-state debug redaction.

The Rust suite now includes external serialization round trips; exhaustive
small-configuration threshold-subset properties; and malformed envelope, field,
point, scalar, identifier, selected-set, generator, and resource-bound tests for
every external wire object. A full deterministic synthetic 2-of-3 vector is
regenerated by a Rust integration test and its frozen public/secret-state
encodings are consumed by a separate Python/PyO3 recovery test. The complete
local LOCUS flow uses the native backend by default and succeeds for `(2,3)`,
`(3,5)`, and `(5,9)` with non-contiguous threshold subsets.

The frozen vector is regression and cross-language interoperability evidence,
not an independent implementation of the group algebra. The commitment and
response encodings now cross the pinned-mTLS party-service boundary in correct
and wrong-input 2-of-3 tests with per-process secret state. Independent
cryptographic review, independent-host deployment, and adversarial network evaluation
remain required before stronger implementation-security claims.

## Evaluation Plan

Measure enrollment, request, proof preparation and verification, response generation, aggregation, and client finish separately. Also measure serialized bytes by role and complete distributed latency. Report medians and distributional results over pinned builds. Do not compare the Rust/Ristretto measurements directly with the article's Java 7 and 1024/160-bit measurements as if they were the same environment or security level.

## Paper Implications

- State that LOCUS instantiates the algebra of Yi et al.'s zero-knowledge-based Protocol 2 over Ristretto255 with explicit transcript domains and transparent `G2` derivation.
- Distinguish the inherited TPASS property from LOCUS attempt control, authorization, storage separation, and lifecycle mechanisms.
- Disclose the source proof-of-knowledge assumption and the changed generator-generation method.
- Do not call the implementation production-ready or audited.
- Use only the retained native distributed measurements for paper-facing
  performance claims. Simulator and toy-backend measurements remain development
  checks and must not support practicality claims.
- Follow `docs/paper-protocol-mapping.md` for the exact cue-to-password,
  recovery-identifier, wrapping-key, and authenticated-backup mapping.
