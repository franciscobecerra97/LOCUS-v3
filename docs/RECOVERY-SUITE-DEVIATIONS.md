# TPASS/aPPSS Mapping and Deviations Register

Status: `Prepared for D019 independent review`; reviewer classifications are
pending.

## Purpose

This register separates implementation choices that may legitimately differ
from the source papers from differences that can affect LOCUS's ability to
inherit a security statement. It is not a declaration that every listed choice
is correct. The independent reviewer must confirm or change each proposed
classification and add any omitted difference.

Classes are:

- `Claim-critical`: rejection requires an implementation/specification fix or
  removal of the dependent inherited result and LOCUS claim.
- `Engineering`: acceptable only if the reviewer confirms that it does not
  alter a claim-critical semantic.
- `Scope restriction`: LOCUS intentionally claims less than the source result;
  the narrower boundary must remain explicit.

The final review status for every entry is one of `accepted — engineering`,
`accepted — qualified`, `correction required`, or `claim removal required`.

## Frozen Yi TPASS mapping

| ID | Choice or difference from the source presentation | Proposed class | Claim relevance and required review | Review status |
|---|---|---|---|---|
| YI-001 | The source's multiplicative prime-order group is instantiated in additive notation with Ristretto255 rather than the paper's historical 1024/160-bit experimental group. | Claim-critical | Confirm the enrollment, request, proof, response, aggregation, and final-check equations preserve their algebra and required discrete-log/DDH assumptions. | Pending |
| YI-002 | `G1` is the canonical Ristretto basepoint; `G2` is derived by a fixed domain-separated SHA-512-to-Ristretto procedure instead of the source's referenced multiparty unknown-relation generator ceremony. | Claim-critical | Confirm the required unknown-discrete-log relation goal is acceptably realized or state the exact additional setup assumption/qualification. | Pending |
| YI-003 | Generic source hashes are realized as explicitly framed, role-separated SHA-512 transcripts reduced to canonical scalars. | Claim-critical | Confirm domains, included values, ordering, and reduction do not change the proof/recovery equations or introduce cross-role ambiguity. | Pending |
| YI-004 | LOCUS implements the paper's one-equation server proof check but does not independently prove the proof-of-knowledge property assumed by the source security argument. | Claim-critical | Confirm the equation mapping and require the source proof-of-knowledge property to remain an explicit inherited assumption. | Pending |
| YI-005 | LOCUS uses canonical bounded wire encodings, typed Rust/PyO3 boundaries, mutual-TLS service phases, durable idempotency, and generic external rejection; these mechanisms are not defined by TPASS. | Engineering | Confirm they preserve the same protocol messages/relations and add no password verifier or secret-bearing persistent state. | Pending |
| YI-006 | D018 uses common reconstruction notation `k`; for Yi, `k` equals the source protocol's threshold `t` and stored polynomials have degree `k-1`. | Claim-critical | Confirm all comparison, state, and compromise statements use this mapping and do not import aPPSS's `k=t+1` translation. | Pending |
| YI-007 | At `k` compromised Yi states, LOCUS's comparator interpolates the password scalar, protected exponent, and digest directly rather than modeling threshold compromise as a dictionary attack. | Claim-critical | Confirm this is the correct persistent-state consequence of the implemented/source sharing structure and supports the stated contrast with aPPSS. | Pending |

## D017 aPPSS mapping

| ID | Choice or difference from the source presentation | Proposed class | Claim relevance and required review | Review status |
|---|---|---|---|---|
| APPSS-001 | LOCUS instantiates only Section 3/Figure 4 aPPSS; aptSIG, BLS, PFS, and the threshold-signature construction are excluded. | Scope restriction | Confirm the selected algorithms and Theorem 2 boundary can be reviewed independently of the excluded signature construction. | Pending |
| APPSS-002 | The paper's corruption bound `t` maps to LOCUS reconstruction threshold `k=t+1`; the first profile is `k=2,n=3`. | Claim-critical | Confirm sharing degree, recovery subset size, and below/at-threshold statements consistently follow Figure 4 notation. | Pending |
| APPSS-003 | Abstract 2HashDH is concretized with RFC 9497 base OPRF mode using ristretto255/SHA-512 and canonical element validation. | Claim-critical | Confirm the RFC realization supplies the OPRF behavior assumed by the mapping and that base OPRF, not VOPRF, is represented accurately. | Pending |
| APPSS-004 | Each holder generates an independent nonzero OPRF key bound to one holder identity, membership, and epoch; no common master key or in-place key rotation is used. | Claim-critical | Confirm this realizes the independent-server/global-initialization assumption and that all context domains are correct. | Pending |
| APPSS-005 | Shamir sharing uses a specified polynomial-basis `GF(2^128)` with modulus `x^128+x^7+x^2+x+1`, big-endian 16-byte encoding, and integer party coordinates. | Claim-critical | Confirm field arithmetic, coordinate encoding, degree `k-1`, interpolation, and XOR masking faithfully realize Figure 4 at `lambda=128`. | Pending |
| APPSS-006 | Figure 4's random-oracle operations are realized with framed SHA-256; the 32-byte commitment/secret hash is split into 16-byte `C` and 16-byte `S_R`. | Claim-critical | Confirm hash inputs, mask derivation, output split, commitment check, and recovery-secret length preserve the intended construction and claimed security level. | Pending |
| APPSS-007 | CuePolicy output is first converted into suite/epoch-bound `p_M`; OPRF inputs and mask derivation add LOCUS instance/context domains. | Claim-critical | Confirm the domains prevent cross-suite/epoch use without changing the enrolled/recovered OPRF value for one bound epoch. | Pending |
| APPSS-008 | LOCUS realizes authenticated initialization with pinned identities and holder-local key generation; the client obtains initialization OPRF evaluations and installs identical public `omega` at all intended holders. | Claim-critical | Confirm this is a sufficient concrete realization for the scoped `F_AUTH`/independent-key assumptions and does not centralize or persist prohibited secret state. | Pending |
| APPSS-009 | The optional verifiable-OPRF robustness sketch is omitted; malformed or malicious selected-holder behavior is abort-only and may be unattributable. | Scope restriction | Confirm no robustness or malicious-server completion claim is inferred from the base-OPRF implementation. | Pending |
| APPSS-010 | The implementation/evidence claim is restricted to static read-only persistent-state compromise for one epoch, narrower than the paper's hybrid/adaptive discussion. | Scope restriction | Confirm the narrower below-threshold and threshold-compromise statements are supportable without claiming the broader theorem is implemented or experimentally proved. | Pending |
| APPSS-011 | The Figure 4 output is used directly as the 128-bit LOCUS `S_R`; there is no independently sampled or separately threshold-shared unmasked recovery secret. | Claim-critical | Confirm this is the correct paper-to-LOCUS output mapping and that holder/public state cannot recover `S_R` below threshold. | Pending |

## LOCUS outer composition

| ID | LOCUS choice beyond the source constructions | Proposed class | Claim relevance and required review | Review status |
|---|---|---|---|---|
| OUTER-001 | Yi returns a canonical 32-byte encoded group secret and aPPSS returns a 16-byte `S_R`; both are opaque suite outputs to suite-bound HKDF-SHA-256. | Claim-critical | Confirm variable native output encodings do not create cross-suite equivalence, fallback, or an external candidate test. | Pending |
| OUTER-002 | HKDF-SHA-256 derives `K_wrap`, and AES-256-GCM protects/authenticates the private-key backup and public metadata. | Claim-critical | Confirm cloud ciphertext/public metadata alone does not supply a candidate verifier and the selected suite output is the sole secret input keying material. | Pending |
| OUTER-003 | Descriptors, bundles, holders, cloud objects, lifecycle state, and audit records contain public bindings but prohibit raw cues, `Z_M`, `p_M`, OPRF outputs, unmasked shares, `S_R`, `K_wrap`, plaintext keys, and cue verifiers. | Claim-critical | Confirm the persistent-state inventory used by the cloud-only, below-threshold, and combined claims omits any equivalent local predicate. | Pending |
| OUTER-004 | One epoch authenticates exactly one suite. Recovery dispatches only to that suite; successor creation performs fresh setup; no automatic downgrade, fallback, mixed state, or in-place conversion exists. | Claim-critical | Confirm selection/lifecycle behavior preserves the suite-specific assumptions and does not create a second candidate-testing path. | Pending |
| OUTER-005 | Canonical storage schemas, mutual-TLS APIs, proof-key-bound admission, idempotency records, and generic errors are LOCUS system mechanisms rather than parts of either source construction. | Engineering | Confirm these mechanisms do not alter the reviewed algebra/state boundary; do not treat them as proof, production security, or a global attempt bound. | Pending |

## Explicit non-deviations and frozen boundaries

- Frozen Yi identifiers, vectors, wire formats, party state, recovery behavior,
  and retained v2 evidence are not changed or reinterpreted by the review.
- aPPSS identifiers and formats remain the exact D017/P5A.1 profile unless a
  correction is approved through a new versioned decision and implementation.
- Tests may reveal implementation defects but do not convert an engineering
  choice into a proved cryptographic mapping.
- A final `accepted — qualified` entry must identify the exact assumption or
  manuscript limitation that preserves acceptance.
- P8/P9 results remain suite/profile separated and cannot retroactively resolve
  a claim-critical mapping rejection.
