# aPPSS Independent Cryptographic Review Packet

Status: `Ready for independent review`; no acceptance finding has been issued.

## Purpose and release boundary

P5A.7 requires an independent cryptographic review of the aPPSS
paper-to-code mapping before LOCUS calls the implemented profile
"augmented", exposes it as a released new-enrollment choice, or promotes the
P5A.6 Yi/aPPSS comparison into a research result. The implementer, this
repository's automated tests, and an AI-assisted self-review do not satisfy
that independence requirement.

The review target is code commit `36ea1fe`, whose cryptographic implementation
history is P5A.1 through P5A.6 (`19f00e1` through `8795947`). The local source
paper is `extra/2024 - Augmented Password-Protected Secret Sharing
(aPPSS).pdf`. It is not distributed by the repository; the reviewer must have
lawful access to the paper.

No retained performance corpus is in scope. P5A.6 is a fixed,
aggregate-only, non-retained development regression, not evidence of either
construction's theorem.

## Reviewer independence and qualifications

The reviewer should be identifiable in the private project record, independent
of the implementation work, and able to assess OPRFs, threshold secret sharing,
random-oracle mappings, canonical encodings, and protocol composition. A
conflict or prior contribution to the reviewed code must be disclosed.

The public artifact need not expose personal contact information. A future
privacy-safe review record may name the reviewer only with their consent or use
an owner-retained identity record plus a public role/qualification statement.

## Normative mapping to review

The intended construction is only Section 3/Figure 4 aPPSS, not the paper's
threshold-signature construction. The following mapping is normative:

1. LOCUS reconstruction threshold `k` maps to the paper's `t + 1`.
2. The OPRF follows the paper's 2HashDH shape, concretized as RFC 9497 OPRF
   mode with ristretto255/SHA-512 and canonical element encodings.
3. Each holder creates an independent OPRF key for one holder identity and one
   epoch. Keys are neither derived from a common master nor reused across
   epochs.
4. Shamir sharing uses degree `k - 1` over `GF(2^128)` with modulus
   `x^128 + x^7 + x^2 + x + 1` and one canonical 16-byte field encoding.
5. The approved SHA-256 domains, mask derivation, commitment `C`, public
   `omega = (e, C)`, context bindings, state formats, and wire formats are
   exactly those in `docs/APPSS-PROFILE.md` and
   `docs/APPSS-WIRE-FORMAT.md`.
6. The aPPSS output is the 128-bit LOCUS recovery secret `S_R`; there is no
   independently sampled, separately threshold-shared unmasked `S_R` behind
   aPPSS.
7. `S_R` enters the unchanged suite-bound HKDF-SHA-256 and AES-256-GCM backup
   path. One epoch authenticates exactly one recovery suite.
8. Initialization is authenticated and distributed: each holder process
   creates and retains only its own OPRF key, and the client installs one
   common public state after context-bound OPRF evaluation.
9. The profile is abort-only against malformed or malicious holder behavior.
   It does not claim VOPRF-style verifiability, robustness, proactive refresh,
   adaptive security, or side-channel resistance.
10. Recovery, lifecycle, storage, and descriptor dispatch reject mixed-suite,
    mixed-epoch, mixed-session, downgrade, and automatic-fallback paths.

## Files in scope

The reviewer should inspect at least:

- `DECISIONS.md` records D017, D018, and M-SELECTABLE-SUITES-001;
- `PROTOCOL-INVARIANTS.md` and `VERSION-REGISTRY.md`;
- `docs/APPSS-PROFILE.md`, `docs/APPSS-WIRE-FORMAT.md`,
  `docs/APPSS-MIGRATION.md`, `docs/SYSTEM-INTERFACES.md`, and
  `docs/suite-compromise-regression.md`;
- `appss-core/src/lib.rs` and its fixed-vector tests;
- the aPPSS boundary in `tpass-python/src/lib.rs`;
- `prototype/locus/appss.py`, `appss_client.py`, `appss_formats.py`,
  `appss_party.py`, `appss_party_http.py`, `recovery_suite_registry.py`,
  `suite_epoch_factory.py`, and `suite_successor.py`; and
- the corresponding `prototype/tests/test_appss_*`, selectable-suite,
  lifecycle/successor, backup-v5, and compromise-regression tests.

Frozen `tpass-core` is comparison context only. The review must flag any aPPSS
change that would require changing or reinterpreting frozen Yi state, vectors,
or retained v2 evidence.

## Required review questions

The finding must answer each question explicitly:

1. Does the implementation faithfully instantiate the approved
   Section 3/Figure 4 aPPSS algorithms and the `k = t + 1` translation?
2. Are OPRF input hashing, blinding, evaluation, unblinding, key separation,
   identity/epoch binding, and canonical decoding correct and domain-separated?
3. Are `GF(2^128)` arithmetic, point assignment, interpolation, byte order,
   secret sharing, masking, commitment verification, and `S_R` derivation
   correct for every supported `k,n`?
4. Do public, client, holder, and wire states match the paper's secrecy
   boundary without persisting a cue verifier or unmasked recovery secret?
5. Does authenticated initialization supply the assumptions required by the
   mapped construction, including independent server keys and one common
   public state?
6. Are cross-suite, cross-epoch, cross-session, duplicate-holder,
   noncanonical, and fallback cases rejected before secret release?
7. Is the following scoped interpretation accurate under the stated
   assumptions: fewer than `k` matching states expose no local offline cue
   predicate, whereas `k` aPPSS states plus public `omega` enable an
   unrate-limited offline dictionary test and release `S_R` for a correct
   candidate?
8. Are the Yi/aPPSS comparison and its limitations stated without implying
   equivalent internal security, proof by testing, measured cue entropy, or
   a production-security result?
9. Are any missing assumptions, ambiguous mappings, implementation defects, or
   additional mandatory tests release-blocking?

## Required finding format

The reviewer should return a signed or otherwise attributable record containing:

- reviewer name or owner-held identity reference, qualifications, independence
  statement, and disclosed conflicts;
- review date, exact commit, source-paper version/pages, and files reviewed;
- one answer for every required review question;
- findings classified as `blocking`, `major`, `minor`, or `informational`,
  with file/line references and recommended remediation;
- final disposition: `accepted`, `accepted with mandatory corrections`, or
  `rejected`;
- explicit statement of residual assumptions and claims the review does not
  establish; and
- digest/signature or other integrity binding for the final review record.

All blocking and major findings must be resolved and re-reviewed against a new
exact commit. P5A.7 remains incomplete until an acceptable final disposition is
recorded. Review acceptance still does not authorize a manuscript edit or a
retained P9 result.
