# Exact aPPSS Recovery Profile

Status: P1.2 recovery contract approved by D017 on 2026-08-01 and exact P5A.1
identifier/format profile frozen on 2026-08-03. This document does not claim
that the native implementation, selector release, evidence, independent
review, or manuscript wording is complete. `docs/APPSS-WIRE-FORMAT.md` owns the
strict schemas, bounds, canonical public vector, and compatibility rules.

## Scope and source mapping

The profile instantiates only Section 3, Figure 4, and Theorem 2 of
*Password-Protected Threshold Signatures*. The threshold-signature, aptSIG,
BLS, and PFS constructions are excluded.

The mapping is:

| Paper object | LOCUS object |
| --- | --- |
| Corruption bound `t` | `k - 1` |
| Reconstruction threshold `t + 1` | `k` |
| Party count `n` | `n` |
| Password `pw` | Suite-derived 32-byte `p_M` |
| Public `omega=(e,C)` | Suite public recovery record |
| Output `sk` | The 16-byte LOCUS recovery secret `S_R` |

The first evaluated profile has `k=2`, `n=3`, and therefore maps to the
paper's `t=1`, `n=3`. The recovery threshold is independent of the current
4-of-5 authorization quorum.

D018 keeps Yi and aPPSS independently selectable and requires paired profiles.
After the first `k=2,n=3` gate, the same aPPSS construction is also evaluated at
`k=3,n=5` (`t_paper=2,n=5`) alongside Yi 3-of-5. The field, OPRF, hash,
commitment, recovery-secret size, state split, and one-suite-per-epoch rules do
not change. Each topology receives exact configuration, deployment, vector, and
evidence bindings where required; all ten valid 3-of-5 reconstruction subsets
must pass before that profile is claimed.

## Fixed primitives

- Security parameter: `lambda=128`.
- OPRF shape: the paper's 2HashDH construction.
- Concrete OPRF group profile: RFC 9497 OPRF mode with
  `ristretto255-SHA512`; the optional VOPRF proof mode is not used.
- Group element encoding: the canonical 32-byte ristretto255 encoding from
  RFC 9496/RFC 9497. Decoding rejects non-canonical encodings and the identity.
- Shamir field: `GF(2^128)` in polynomial basis modulo
  `x^128 + x^7 + x^2 + x + 1`.
- Figure 4 random-oracle realization: domain-separated SHA-256 with a 32-byte
  output split into `C` (first 16 bytes) and `S_R` (last 16 bytes).
- Existing outer composition: HKDF-SHA-256 derives `K_wrap` directly from
  `S_R`; AES-256-GCM protects the private key.

The RFC 9497 OPRF security discussion and its assumptions apply to the
concrete OPRF realization separately from Theorem 2. Choosing an RFC-defined
encoding and hash-to-group function does not turn LOCUS tests into a proof of
the aPPSS construction.

## Canonical field representation

A field element is exactly 16 bytes. Decode the bytes as one unsigned
big-endian 128-bit integer `a`. Bit `j` of `a`, with bit zero the least
significant bit, is the coefficient of `x^j`. Addition is bitwise XOR.
Multiplication is carry-less polynomial multiplication reduced modulo
`x^128 + x^7 + x^2 + x + 1`. Encoding is the inverse 16-byte big-endian map;
there are no alternate or shortened encodings.

Party indices are positive integers in `[1,n]`, with `n <= 65535`. The field
coordinate for index `i` is the canonical field encoding of integer `i`.
Coordinates must be distinct and nonzero. A degree-`k-1` polynomial is sampled
with independent uniform 16-byte coefficients and constant term `s`; share
`s_i` is its value at party coordinate `i`.

This representation is deliberately specified independently of any library's
bit-reflected GCM multiplication API. The native core must have fixed
field-operation vectors before P5A.2 completes.

## Canonical tuple framing and context

Every cryptographic hash input is a sequence of fields encoded as:

```text
u32be(field_count) ||
  u32be(len(field_1)) || field_1 ||
  ... ||
  u32be(len(field_m)) || field_m
```

Integers inside a field use their fixed-width unsigned big-endian encoding.
Vectors carry an unsigned 16-bit count followed by entries sorted by party
index; every entry contains `u16be(index)` and its fixed-size value. Duplicate,
zero, out-of-range, missing, unsorted, or trailing entries are invalid.

The immutable epoch context contains, in this order:

1. the final aPPSS suite identifier;
2. backup identifier;
3. epoch;
4. CuePolicy identifier;
5. ordered recovery-holder membership, including each party identifier,
   index, and authenticated service identity;
6. `k` and `n`; and
7. the canonical configuration digest.

`context_digest` is SHA-256 over the canonical tuple whose first field is the
ASCII label `LOCUS/aPPSS/epoch-context/v1`. The assigned suite identifier is
`LOCUS-APPSS-2HASHDH-RISTRETTO255-SHA512-GF128-v1`; no implementation may
substitute an empty, default, or Yi identifier.

The configuration digest in this tuple is the canonical pre-setup public
configuration digest. It covers the already fixed backup identifier, epoch,
CuePolicy, holder membership, reconstruction threshold, and authenticated
service identities, but excludes `omega`, encrypted-backup bytes, and the
descriptor that cannot exist until setup finishes. RecoveryDescriptor v1 later
computes its separate full configuration digest over the resulting aPPSS public
state and exact backup binding. The two digests have different domains and must
not be substituted for one another.

Each server's fixed OPRF instance identifier is the canonical tuple of the
ASCII label `LOCUS/aPPSS/2HashDH/instance/v1`, `context_digest`, party
identifier, and party index. This is the paper's global OPRF initialization session for
that server and epoch. A fresh online recovery session is not folded into the
OPRF input because doing so would change the value used to mask the enrolled
share.

## Suite-derived password input

CuePolicy produces exact bytes `Z_M` or fails locally. The aPPSS password is:

```text
p_M = SHA-256(
  Tuple("LOCUS/aPPSS/password-input/v1", context_digest, Z_M)
)
```

`p_M` is an opaque 32-byte string. It is not interpreted as a Ristretto scalar,
stored, logged, or accepted across suites or epochs. This suite domain is
separate from the frozen Yi hash-to-scalar domain.

## Concrete 2HashDH OPRF

Each authenticated server independently samples and retains one nonzero
ristretto255 scalar `k_i` for the bound epoch. No production coordinator or
other server receives it. Key reuse across epochs, memberships, or suite
profiles is prohibited.

For server `i`, the RFC 9497 OPRF input is the canonical tuple of the ASCII
label `LOCUS/aPPSS/2HashDH/input/v1`, the server's OPRF instance identifier, and
`p_M`. RFC 9497 OPRF-mode `Blind`, `BlindEvaluate`, and `Finalize` are used with
the `ristretto255-SHA512` ciphersuite. The client samples a fresh nonzero blind
for every server evaluation and every online session. The 64-byte RFC OPRF
output is reduced to the Figure 4 mask as:

```text
rho_i = first_16_bytes(
  SHA-256(Tuple("LOCUS/aPPSS/2HashDH/mask/v1", instance_id_i,
                   rfc9497_oprf_output))
)
```

Thus `rho_i` is one canonical 16-byte field string. The server sees only a
canonical non-identity blinded element and authenticated public/session
metadata, not `p_M`, the unblinded element, `rho_i`, `s_i`, or `S_R`.

This is non-verifiable OPRF mode. The first profile does not add the paper's
optional verifiable-OPRF robustness sketch.

## Initialization

The active enrollment client:

1. validates the complete immutable epoch context and obtains one OPRF
   evaluation from every authenticated server;
2. samples uniform `s` in `GF(2^128)` and a degree-`k-1` Shamir polynomial;
3. computes `e_i = s_i XOR rho_i` for every party and orders the vector by
   party index;
4. encodes `e` canonically and computes:

   ```text
   h = SHA-256(Tuple("LOCUS/aPPSS/commit-secret/v1", context_digest,
                    p_M, canonical_e, encode_field(s)))
   C = h[0:16]
   S_R = h[16:32]
   ```

5. defines public `omega=(e,C)` and its digest as
   `SHA-256(Tuple("LOCUS/aPPSS/omega/v1", context_digest, canonical_omega))`;
6. sends the identical canonical `omega` to every authenticated intended
   server under the enrollment-session binding; and
7. uses `S_R` directly as HKDF input keying material for the existing backup
   protection path.

Each server atomically stores only its own `k_i`, party/index and epoch context,
canonical public `omega`, `omega_digest`, and bounded lifecycle/idempotency
metadata. Backup and descriptor records bind the same `context_digest` and
`omega_digest`. No server stores an unmasked Shamir share.

Initialization is not complete until every required server state, encrypted
backup, authenticated descriptor, and current-pointer transition meet the
later lifecycle readiness rule. The client must dispose of `p_M`, OPRF
blinders/outputs, polynomial coefficients, shares, `s`, and `S_R` after the
bounded enrollment operation, subject to the project's best-effort disposal
limitation.

## Recovery

A recovery request selects an explicit ordered set of exactly `k` distinct
parties from the bound membership and uses one fresh session identifier and
authorization binding. Every request and response binds:

- `context_digest` and `omega_digest`;
- party identifier and index;
- operation (`recover`);
- client proof key and admission-grant digest;
- fresh recovery session identifier and nonce; and
- exact request digest and idempotency key.

After authentication and replay checks, each selected server evaluates its
bound OPRF instance. The client finalizes each response, reconstructs
`s'` from `e_i XOR rho_i'`, and recomputes the commitment/secret hash using the
candidate `p_M'`, the complete canonical public `e`, and `s'`. It returns
`S_R'` only when the recomputed `C'` equals the bound `C` using constant-time
comparison. Otherwise it deletes transient state and returns one generic
recovery rejection. Servers are not told whether the commitment, HKDF, backup
authentication, or protected-key identity check eventually succeeded.

Every accepted subset must agree on the exact suite, context, membership,
threshold, `omega`, backup, descriptor, and epoch. Cross-suite, cross-version,
cross-epoch, cross-session, cross-membership, mixed-omega, replayed, malformed,
or non-canonical objects fail closed before their values can be combined.

## Failure and robustness policy

- Public parsing, authorization, identity, freshness, availability, and
  protocol failures are internally typed but externally bounded.
- Once candidate evaluation is admitted, wrong input, an incorrect OPRF
  response, reconstruction failure, commitment mismatch, and final backup
  failure collapse to the client-visible generic recovery rejection wherever
  doing so does not hide a pre-secret availability condition.
- A malicious selected server can abort or send an invalid evaluation. Without
  a VOPRF proof, the client cannot reliably attribute the failure.
- The client may retry the same candidate with a different explicit valid
  `k`-subset only under the separately approved admission/attempt policy and a
  fresh online session. This is availability retry, not fuzzy cue expansion or
  multi-candidate retry.
- No claim of robustness against `k` malicious servers, guaranteed completion,
  or global rollback-resistant attempt counting is made.

## Corruption, lifecycle, and erasure boundary

Theorem 2 is a random-oracle result in the `(F_OPRF,F_AUTH)` hybrid. Appendix C
models adaptive OPRF corruption, but the first LOCUS implementation/evidence
claim is deliberately narrower: static read-only compromise of declared
persistent role state for one bound epoch. The concrete claim additionally
assumes authenticated distributed initialization, correct and independent
honest server key generation, authenticated service identities and channels,
secure randomness, strict transcript binding, and absence of prohibited
secret-bearing logs or crash artifacts.

Per-epoch OPRF keys remain available while the epoch is recoverable and are
never rotated in place. A successor epoch creates fresh independent keys,
`omega`, backup, descriptor, and identifiers. The predecessor is retired only
after successor readiness and verified recovery. Retirement performs
best-effort key/state deletion; no forensic secure-erasure, proactive refresh,
mobile-adversary, adaptive implementation, side-channel, or production-HSM
claim is made.

## Exact security and comparison claims

Subject to the above model and D020's provisional internal mapping acceptance
of aPPSS, frozen Yi, and the LOCUS composition, with D019 independent human
confirmation still pending:

1. Public cloud/descriptor/`omega` state alone supplies no local cue-testing
   predicate.
2. Fewer than `k` matching server states plus the public state supply no local
   cue-testing predicate; testing a candidate still requires an honest
   server's online OPRF participation.
3. `k` or more matching server states plus public `omega` enable local,
   unrate-limited dictionary testing. A wrong candidate fails `C`; a correct
   candidate yields `S_R`.
4. The frozen Yi profile has a different reconstruction-threshold failure
   mode: `k` matching Yi party states directly interpolate its shared password
   scalar, secret exponent, and digest and therefore expose its high-entropy
   recovery secret without first guessing the cue-derived password.

Claim 3 is delayed exposure, not protection from offline guessing. Its residual
value depends on the adversary's conditional cue distribution. The profile
does not establish cue entropy, memory capacity, memorability, usability,
global rate limiting, independent administration, side-channel resistance, or
production readiness. The aPPSS and Yi constructions are inherited work; LOCUS
claims no new cryptographic construction or proof.

## Primary specification basis

- The supplied 2024 aPPSS paper and page anchors recorded in
  `docs/APPSS-MIGRATION.md` define Figure 4, Theorem 2, and 2HashDH.
- [RFC 9497](https://www.rfc-editor.org/rfc/rfc9497.html) defines the selected
  OPRF mode, ristretto255/SHA-512 ciphersuite, canonical validation rules, and
  concrete security considerations.
- [RFC 9496](https://www.rfc-editor.org/rfc/rfc9496.html) defines ristretto255
  group operations and canonical 32-byte element encoding.
- [RFC 9380](https://www.rfc-editor.org/rfc/rfc9380.html) defines the
  domain-separated hash-to-ristretto255 operation used by the RFC 9497
  ciphersuite.

## P5A.1 assignment boundary

P5A.1 assigns the complete aPPSS suite, OPRF, password-domain, state, message,
backup-v5, selector, and 2-of-3 profile identifiers in
`docs/APPSS-WIRE-FORMAT.md`. It also freezes strict schemas, maximum sizes,
typed failures, a public structural vector, one independent consumer, and the
separate native core/library choice. RecoveryDescriptor v1 is reused only
through its already suite-neutral fields; no descriptor bytes are
reinterpreted.

P6.3 later assigns the separate 3-of-5 aPPSS state/message formats, selector
v2, backup v6/AAD v3, public topology vector, and matched same-host process
deployment profiles. The v1 2-of-3 family remains unchanged. Trace, result,
artifact, and retained-performance identifiers remain unassigned at their
later gates; P6.3 conformance is not retained evidence or cryptographic proof.
