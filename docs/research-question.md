# LOCUS Research Question And Contribution Hierarchy

Status: reframed submission direction, 2026-07-22. The prior primary thesis
required a complete rollback-resistant distributed attempt bound. P5.13 exposed
a quorum-only rollback counterexample, and the project deliberately narrows the
paper rather than add a new monotonic authority. This decision is synchronized
with `docs/limitations-and-assumptions.md`, `PLAN.md`, the claim matrix, threat
model, and manuscript.

## Primary Research Question

> Can a private-key recovery architecture combine deterministic structured
> recovery input with TPASS and separated encrypted cloud storage so that cloud,
> below-threshold party, and combined cloud-plus-below-threshold snapshots do not
> become offline cue-testing oracles, while making the remaining online,
> resolver, lifecycle, and deployment limitations explicit and reproducible?

This question does not assume that personal cues are memorable or high entropy,
that TPASS is new, that Docker containers are independent operators, that online
attempts are globally bounded, or that the prototype is production-ready.

## Primary Thesis

LOCUS's scoped thesis is:

> Under the inherited TPASS and standard-primitive assumptions, separating an
> encrypted private-key backup from threshold recovery-party state preserves a
> no-offline-cue-verifier boundary for cloud-only and below-threshold snapshots.
> A deterministic cue-policy interface can realize this composition without
> storing raw cue material or a password verifier at the cloud or parties, while
> a concrete prototype exposes the residual online-guessing, resolver,
> lifecycle, and operational boundaries.

This is an architecture, composition, and implementation-validation thesis. It
is not a theorem that the complete deployed system is globally rate-limited,
rollback-resistant, available, usable, or secure against endpoint or threshold
compromise.

## Supporting Research Questions

### SQ1: Offline-oracle boundary

Do cloud-only, fewer-than-threshold party, and combined cloud-plus-fewer-than-
threshold snapshots lack an implemented local predicate for verifying candidate
recovery inputs?

Relevant claims: CLM-01, CLM-02, and CLM-05 through CLM-07.

### SQ2: Cue and resolver boundary

Can the exactly-three-pair reference policy be canonicalized deterministically
without storing raw cue material at the cloud or parties, and what drift,
ambiguity, observation, and attacker-side-information risks remain?

Relevant claims: CLM-02, CLM-13, CLM-20, and CLM-21.

### SQ3: Concrete feasibility

Can native TPASS, standard AEAD/KDF, separate party state, an S3-compatible
object store, authenticated service boundaries, and a fresh recovery client be
composed into a reproducible end-to-end prototype?

Relevant claims: CLM-03, CLM-04, CLM-16 through CLM-19, and CLM-22 through
CLM-24.

### SQ4: Failure and lifecycle boundaries

How does the prototype behave under wrong input, insufficient parties, malformed
state, stale or substituted cloud objects, resolver failure, party restart,
unavailability, and same-membership re-enrollment?

Relevant claims: CLM-08, CLM-09, CLM-15, CLM-22, and CLM-23.

### SQ5: Residual online risk

Which online-attempt properties are provided by the current partial ledger,
which are disproved by bounded rollback exploration, and which must remain
deployment assumptions or future work?

Relevant claims: CLM-10 through CLM-12. SQ5 is a boundary and negative-result
question, not a positive global-attempt-bound claim.

## Contribution Hierarchy

### C1: Storage-separated private-key recovery architecture

LOCUS separates:

- client-local cue resolution, canonicalization, and secret handling;
- the encrypted private-key object in S3-compatible storage;
- one TPASS secret state per recovery party;
- resolver observation from cloud/party storage privacy; and
- recovery orchestration from possession of the whole recovery secret.

The contribution is the precise composition and threat/evidence mapping for a
private-key recovery workflow, not the invention of TPASS or threshold secret
sharing.

### C2: Deterministic structured-cue policy boundary

The reference policy defines exactly three location-person pairs, canonical
ordering, coordinate precision, Unicode and locale handling, contact
normalization, versioning, ambiguity, and drift behavior. It demonstrates a
generic structured-input interface while explicitly making no memorability,
entropy, usability, or comparative-recall claim.

### C3: Concrete research prototype

The implementation combines a Rust/Ristretto255 TPASS core, Python orchestration,
AES-256-GCM and HKDF-SHA-256, immutable cloud-backup adapters, authenticated
party services with separate SQLite state, a deterministic resolver, and an
isolated same-host Compose deployment. This is reproducible research software,
not independent administration or production security.

### C4: Claim-scoped security and failure validation

Tests and experiments cover retained properties: successful and failed
recovery, cloud/party state separation, below-threshold behavior, malformed
inputs, cloud binding, party unavailability/restart, cross-epoch mixing,
resolver failure boundaries, and prohibited-output checks. An experiment
establishes only the configured behavior it executes.

### C5: Explicit negative result and limitation analysis

The bounded attempt-control model shows that quorum-only reconciliation can
produce conflicting certificates after one honest database restore and can
reauthorize a restored retired epoch. This result explains why the existing
ledger is not a rollback-resistant global rate limiter. Adding an independent
monotonic witness is one possible future direction, but is not part of the
scoped LOCUS architecture.

### C6: Reproducible performance and resilience characterization

The evaluation should measure the implemented core's end-to-end latency,
communication, storage, failure behavior, and same-host resilience with exact
provenance. It must not generalize local measurements to Internet-scale,
independently operated, or production deployments.

## Inherited, New, And Operational Results

| Category | LOCUS treatment |
| --- | --- |
| Inherited TPASS security | Below-threshold reconstruction and offline-password-testing resistance under the selected construction's assumptions; not claimed as new. |
| LOCUS architecture | Separation of cue processing, cloud ciphertext, party state, and resolver boundary in a private-key recovery workflow. |
| LOCUS implementation | Native TPASS composition, deterministic policy, cloud adapter, authenticated party services, lifecycle slice, and reproducible same-host deployment. |
| Negative result | Quorum-only party reconciliation is insufficient for rollback-resistant attempt bounding in the frozen compact model. |
| Conditional analysis | `min(1, k*2^-h)` applies only if a deployment independently enforces `k` and the cue input actually has conditional min-entropy `h`. |
| Operational assumptions | Trusted active client, authenticated enrollment, fewer than `t` compromised parties, current honest metadata for cloud rollback detection, sufficient availability, and deployment-provided abuse controls. |

## Minimum Evidence For The Scoped Thesis

The scoped thesis is ready only if:

1. the native TPASS mapping, backup encryption, and canonical encodings remain
   synchronized with their tests and documentation;
2. cloud, below-threshold, and combined snapshots are inspected for an
   implemented local cue-verification predicate;
3. successful recovery and relevant failures execute through the same prototype
   interfaces used by the artifact;
4. deterministic cue and drift vectors run reproducibly on the supported
   environments;
5. storage, logs, reports, and role snapshots exclude prohibited material within
   the tested observation boundary;
6. all attempt-control, rollback, admission, availability, privacy, and
   memorability limitations remain explicit;
7. performance results use frozen methodology and exact provenance;
8. bibliography, related-work distinctions, manuscript claims, and artifact
   instructions are verified; and
9. the anonymous artifact reproduces the central functional and negative-result
   evidence from a clean environment.

## Falsification And Reframing Conditions

The scoped thesis must be weakened further if:

- a cloud-only or cloud-plus-fewer-than-`t` snapshot exposes a practical local
  cue correctness predicate;
- party or cloud state contains raw cues, cue identifiers, a password verifier,
  a whole recovered secret, wrapping key, or protected private key contrary to
  its role;
- the native implementation does not match the stated TPASS construction or
  required validation assumptions;
- deterministic cue reproduction fails under the frozen policy and environment;
- paper-facing results cannot be reproduced through the artifact; or
- the manuscript implies global attempt control, human usability, independent
  administration, or production readiness despite their absence.

## Explicit Non-Goals

- a global or lifetime online-attempt bound;
- party-state rollback resistance;
- public-client OIDC/DPoP admission or false-lockout administration;
- general party replacement or proactive share refresh;
- protection after compromise of `t` parties or the active endpoint;
- guaranteed availability or denial-of-service prevention;
- hidden resolver activity or anonymous recovery metadata;
- fuzzy recovery from changed or approximately remembered cues;
- human memorability, entropy, or usability evidence;
- independently operated or production-grade deployment; and
- audited, side-channel-hardened cryptography.

## Paper Framing

The manuscript should present the no-offline-oracle storage composition first,
then the cue/resolver boundary, concrete prototype, retained evidence, and
limitations. The partial attempt ledger is implementation context; the bounded
rollback counterexample is a negative result. Neither is a primary positive
security contribution.

The complete scope contract is `docs/limitations-and-assumptions.md`.
