# TPASS/aPPSS Construction and Security-Claim Mapping Review

Status: D020 internal mapping assessment issued with provisional qualified
acceptance; independent human validation remains pending.

## Purpose

LOCUS does not claim Yi TPASS or aPPSS as a new cryptographic construction.
The independent review therefore has a narrow purpose: determine whether the
two implemented recovery suites preserve enough of their respective source
constructions and assumptions to support the exact inherited security
statements used by LOCUS, and whether the LOCUS composition adds a prohibited
offline cue-testing predicate.

This is not a full cryptographic audit, production-readiness certification,
side-channel assessment, or new proof. It does not review every service,
storage adapter, deployment control, UI, or operational feature. Automated
tests, vectors, and the D020 internal assessment do not satisfy the independent
human-validation gate. The internal record is
`docs/P5A7-INTERNAL-MAPPING-ASSESSMENT.md`.

The implementation basis is P5A.1--P5A.6 plus the P5A.7 preparation through
commit `7fbed83`; the final finding must record the exact commit actually
reviewed. The reviewer must use:

- Yi, Tari, Hao, Chen, and Liu, *Efficient threshold
  password-authenticated secret sharing protocols* (2019), especially
  Protocol 2, Sections 3.2, 3.3, 4.2, and Figure 3, together with the relevant
  2015 TPASS predecessor where needed; and
- *Password-Protected Threshold Signatures* (2024), Section 3, Figure 4,
  Theorem 2, and the 2HashDH discussion. The threshold-signature and aptSIG
  constructions are out of scope.

The locally supplied 2024 PDF is an ignored research input and is not
redistributed by the repository. The reviewer is responsible for lawful access
to both publications.

## Decision rule

Engineering differences are acceptable when they are explicit and do not
change a claim-critical semantic. Examples include canonical wire encodings,
service routes, authenticated transport envelopes, storage schemas,
identifiers, bounded decoding, and generic error normalization.

The following are claim-critical and require independent acceptance:

- threshold notation and reconstruction semantics;
- algebra, sharing degree/field, interpolation, and recovery equations;
- OPRF construction, input/key separation, and initialization assumptions;
- password/cue binding, masks, commitments, and recovery-secret derivation;
- public, client, and persistent holder-state secrecy boundaries;
- corruption views below and at reconstruction threshold;
- source proof/hybrid/random-oracle assumptions used by each suite;
- the absence of a persisted local cue verifier in the LOCUS outer path; and
- one-suite-per-epoch dispatch, no fallback, and direct suite-output use as
  HKDF input keying material.

If a claim-critical mapping is not acceptable, the implementation must be
corrected and re-reviewed, or the dependent inherited result and LOCUS claim
must be removed. It is not sufficient to describe such a deviation as an
implementation approximation.

## Exact claims under review

The review is limited to whether the following statements are supportable
under each source construction's separately stated assumptions:

1. Cloud/public state alone gives neither suite a local cue-testing predicate.
2. Fewer than reconstruction threshold `k` matching persistent holder states,
   with the public state, give neither suite a local offline cue-testing
   predicate.
3. Matching threshold Yi state reconstructs the shared input scalar, protected
   exponent, and digest, so the high-entropy recovery output is derivable
   without a dictionary search.
4. Matching threshold aPPSS state plus public `omega` permits unrate-limited
   offline candidate testing; a correct candidate yields `S_R`.
5. Combining either below-threshold holder view with the encrypted cloud object
   does not add a local candidate predicate, because the encrypted object has
   no independently testable verifier or key.
6. The common LOCUS path uses the selected suite's authenticated output
   directly as `S_R`, derives `K_wrap` with suite-bound HKDF-SHA-256, and uses
   AES-256-GCM without adding a separately shared unmasked recovery secret.

These statements do not claim measured cue entropy, continued aPPSS protection
after threshold compromise, production security, proactive/adaptive
implementation security, robustness against malicious holders, side-channel
resistance, independent administration, memorability, usability, or a global
attempt bound.

## Yi TPASS mapping to review

The reviewer should confirm or qualify:

1. The frozen implementation maps Yi et al.'s zero-knowledge-based Protocol 2
   from multiplicative notation to additive Ristretto255 notation without
   changing the enrollment, request, proof, response, aggregation, or final
   digest relations.
2. LOCUS reconstruction threshold `k` is the Yi source threshold `t`; party
   state contains degree-`k-1` shares of the password scalar, secret exponent,
   and recovery-output digest.
3. Canonical Ristretto points/scalars, SHA-512 transcript-to-scalar domains,
   explicit framing, and zero/identity rejection are acceptable concrete
   instantiation choices.
4. Transparent domain-separated hash-to-Ristretto derivation of `G2` preserves
   the required unknown-discrete-log relation goal or is correctly qualified as
   a changed setup assumption relative to the paper's generator ceremony.
5. The one-equation proof implementation faithfully checks the source
   equation, while the source's proof-of-knowledge property remains an
   inherited assumption rather than something LOCUS tests establish.
6. Fewer than `k` serialized Yi states expose no local cue predicate under the
   source assumptions, while `k` states interpolate the password scalar,
   secret exponent, and digest directly.

Primary implementation/specification files are `docs/crypto-design.md`,
`docs/tpass-wire-format.md`, `tpass-core/src/lib.rs`, its fixed vector, the Yi
boundary in `tpass-python/src/lib.rs`, and
`prototype/locus/yi_compat.py`.

## aPPSS mapping to review

The reviewer should confirm or qualify:

1. LOCUS implements only Section 3/Figure 4 aPPSS and maps the paper's
   corruption bound `t` to reconstruction threshold `k=t+1`.
2. The paper's 2HashDH OPRF shape is acceptably instantiated with RFC 9497 base
   OPRF mode, ristretto255/SHA-512, independent per-holder/per-epoch keys,
   canonical decoding, and the specified input/key domains.
3. Degree-`k-1` sharing over the specified canonical `GF(2^128)`, mask
   derivation, public `e`, commitment `C`, and `S_R` derivation faithfully
   realize Figure 4 at `lambda=128`.
4. Authenticated distributed initialization realizes the required independent
   server-key/common-public-state boundary sufficiently for the scoped static
   persistent-state claim.
5. Holder state contains its OPRF key and public `omega`, but not `p_M`, an OPRF
   output, an unmasked share, Shamir secret, `S_R`, `K_wrap`, or a cue verifier.
6. Fewer than `k` matching states plus public `omega` have no local candidate
   predicate under the declared OPRF/random-oracle/authentication assumptions;
   `k` states enable the stated offline dictionary test and correct-candidate
   recovery of `S_R`.
7. Abort-only behavior and omission of the optional VOPRF robustness mechanism
   are correctly limited and do not support a stronger malicious-server claim.

Primary implementation/specification files are `docs/APPSS-PROFILE.md`,
`docs/APPSS-WIRE-FORMAT.md`, `docs/APPSS-MIGRATION.md`,
`appss-core/src/lib.rs`, the aPPSS boundary in `tpass-python/src/lib.rs`, and
`prototype/locus/appss.py`, `appss_client.py`, `appss_formats.py`,
`appss_party.py`, and `appss_party_http.py`.

## LOCUS composition to review

The reviewer should inspect `PROTOCOL-INVARIANTS.md`,
`docs/backup-cryptography.md`, `docs/SYSTEM-INTERFACES.md`,
`docs/INFORMATION-FLOW.md`, `docs/suite-compromise-regression.md`,
`prototype/locus/recovery_suite_registry.py`,
`prototype/locus/selectable_suite_lifecycle.py`, and the
backup-v5/selectable-suite tests. The finding
must answer:

1. Does CuePolicy output remain client-local and enter only a suite-bound
   password derivation?
2. Does either cloud, descriptor, backup, holder, lifecycle, or audit state add
   a password-derived authenticator or other local candidate verifier?
3. Does recovery use only the suite authenticated by the epoch and reject
   cross-suite mixing, probing, downgrade, and automatic fallback?
4. Does each suite return only its native high-entropy recovery output to the
   unchanged outer HKDF/AES path?
5. Are the two threshold-compromise outcomes compared without implying that
   their internal constructions, assumptions, or guarantees are equivalent?

## Deviations register

`docs/RECOVERY-SUITE-DEVIATIONS.md` is part of the review input. The reviewer
must classify every entry as:

- `accepted — engineering`: does not affect a claimed construction property;
- `accepted — qualified`: claim-critical choice is acceptable only with the
  recorded assumption/limitation;
- `correction required`: implementation or specification must change before
  the affected claim is used; or
- `claim removal required`: the source result cannot support the affected
  LOCUS statement.

Any newly discovered difference must be added to that register before the
final disposition.

## Reviewer and finding requirements

The reviewer should be independent of the implementation work and able to
assess threshold secret sharing, OPRFs, group/field mappings, random-oracle
assumptions, and protocol composition. A prior contribution or conflict must be
disclosed. This is a mapping judgment, not a requirement for a line-by-line
general security audit.

The final attributable record must include:

- reviewer identity or owner-held identity reference, qualifications,
  independence statement, and conflicts;
- exact commit, publications/sections, files, and deviations reviewed;
- explicit answers for every Yi, aPPSS, and LOCUS composition question above;
- each finding classified as `claim-blocking`, `correction-required`,
  `documentation`, or `out-of-scope`;
- a disposition for Yi mapping, aPPSS mapping, and LOCUS composition separately;
- one overall disposition: `accepted for the stated claims`, `accepted with
  required qualifications`, `correction and re-review required`, or `rejected`;
- residual assumptions and properties the review does not establish; and
- a digest, signature, or equivalent integrity binding to the final record.

Under D020, P5A.7 may complete for implementation chronology after the internal
assessment finds no unresolved claim-blocking or correction-required item and
the release regression/documentation gates pass. Independent human validation
still must complete before manuscript reliance, an independently-reviewed
label, or final reviewed release/submission. An accepted mapping review does
not itself authorize a manuscript edit, create P9 evidence, prove either
construction, or certify LOCUS for production use.
