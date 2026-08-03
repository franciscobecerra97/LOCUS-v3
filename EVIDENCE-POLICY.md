# Evidence Policy

## Purpose

This project promotes a claim only after the exact implementation profile has
matching, privacy-safe, provenance-bound evidence.

## Retained baseline boundary

The retained v1/v2 corpora are stored under their exact versioned paths. V1 is
superseded historical material. V2 is baseline evidence only for the exact
frozen profile and provenance it records. It is not evidence for changed
CuePolicy, recovery suite, descriptor, admission, topology, provider, or
lifecycle semantics. In particular, no Yi TPASS v2 result supports aPPSS.

Raw records remain immutable. Deterministic verification and processing may be
rerun. Changed profiles use new identifiers and paths and must never be mixed
with the inherited corpora.

P1.4 records protected identifiers and reserved evidence families in
`docs/version-registry-v1.json`. Reservation is not evidence authorization:
trace and result identifiers remain unassigned until P8.3/P9.2 approve the
exact privacy boundary, schema, positive controls, metrics, and provenance.

P1.5's `docs/security-matrix-v1.json` supplies the minimum security contract
for every C01--C26 row. Before implementing or collecting a scenario, copy its
asset, adversary, assumptions, boundary, positive control, expected
privacy-safe observation, and interpretation limit into the assigned scenario
methodology and narrow them for the exact profile. The matrix itself is not
evidence and cannot promote a claim.

P2.1/P2.2 descriptor/bootstrap disclosure analyses, canonical vectors, and
unit positive controls, plus P2.3 storage conformance tests, are design and
implementation checks, not collected
C03/C06/C07/C21 evidence. P2.4 must use the exact registered trust,
receipt/summary, descriptor, pointer, manifest, and bundle bytes; include the
complete persistent role view; run the bounded networkless candidate test; and
retain only the privacy-safe observation defined by the security matrix.

P2.4 now supplies `LOCUS-descriptor-security-scenarios-v1` as an aggregate-only
development regression contract with positive controls and a bounded
networkless direct-digest candidate check. It does not allocate the P9 result
family or promote C03/C06/C07/C21 to supported evidence.

## Required scenario contract

Every security-sensitive experiment records:

- claim or invariant;
- protected asset;
- protocol phase;
- exact recovery-suite, policy, descriptor, backup, deployment, and schema
  versions;
- reconstruction threshold `k`, holder identities, and any source-paper
  threshold-notation mapping;
- for aPPSS, the D017/P1.2 profile from `docs/APPSS-PROFILE.md`, including
  final P5A.1 identifiers, and whether the view is below threshold or at/above
  threshold;
- for admission, the exact D004 issuer/adapter and capability profile; the
  local synthetic issuer does not support claims about OIDC, multifactor
  authentication, external account recovery, or identity privacy;
- authorizer quorum and identities;
- cloud/storage backend class;
- topology;
- exact synthetic inputs;
- adversary or failed-role view;
- enforced boundary;
- positive control;
- expected aggregate observation;
- cleanup status;
- output-scan status;
- limitation on interpretation;
- clean source commit, locks, runtime, and pseudonymous host.

## Data policy

Allowed retained output:

- counts;
- timings;
- byte and storage totals;
- scenario/category identifiers;
- Boolean gate results;
- safe digests of public or synthetic fixtures;
- privacy-safe error categories;
- configuration and provenance identifiers.

Forbidden retained output:

- raw or canonical cues;
- candidate values or per-candidate outcomes;
- recovery-suite password input, OPRF keys, masked or unmasked shares,
  high-entropy recovery secret, or wrapping key;
- plaintext private keys;
- credentials, certificates with private material, access tokens, or cookies;
- databases or raw snapshots;
- arbitrary service logs;
- packet captures;
- core dumps or exception traces containing state;
- real user or account identifiers;
- local absolute paths or developer identity.

## Positive controls

Every absence or isolation scenario needs a positive control that deliberately
introduces a fictional forbidden marker, inherited mount, incorrect digest, or
other detectable violation. The experiment must fail when the marker is
present.

## Evidence lifecycle

1. Design and approve the claim and architecture.
2. Define schema and experiment identifier.
3. Implement generated-fixture tests.
4. Run exploratory output outside retained paths.
5. Freeze methodology and source state.
6. Collect append-only raw aggregate records.
7. Validate exact corpus membership and provenance.
8. Deterministically process results.
9. Generate derived tables/figures from validated inputs.
10. Bind every output hash in a manifest.
11. Reproduce on clean hosts.
12. Obtain owner approval before external claim promotion.

## Versioning

Any change to policy semantics, recovery suite or concrete cryptographic
profile, descriptor, topology, threshold, admission, recovery-bundle format,
cloud backend, clean-client boundary, metric definition, or trace policy
requires a new profile and result version.

Do not mix profiles, commits, hosts, policies, thresholds, or topology in one
processed corpus unless the schema and methodology explicitly define that
comparison.

## aPPSS comparative evidence

Any evidence supporting the D017/D018 Yi/aPPSS comparison must keep three claims
separate:

1. below reconstruction threshold `k`, no local persistent-state cue predicate
   under the exact suite assumptions;
2. at or above `k` aPPSS server compromise, an offline dictionary-test
   capability whose correct guess yields `S_R`; and
3. at or above `k` frozen Yi party compromise, direct interpolation of the
   shared password scalar and protected high-entropy secret.

The comparison uses fixed synthetic state and fixed candidates, retains only
aggregate Boolean/category observations, and includes positive controls. It
must not retain per-candidate outcomes or become configurable guessing tooling.
The underlying cryptographic statements come from the cited constructions and
their reviewed LOCUS mappings; experiments show only the behavior of the exact
implementation and persistent-state boundary.

D019 requires one independent, claim-focused human mapping review of frozen
Yi, aPPSS, and the common LOCUS composition before manuscript reliance or a
final reviewed release. D020 permits a clearly labeled internal assessment to
close P5A implementation chronology and start P6; it does not satisfy that
independence requirement. An unresolved claim-critical deviation still
prevents the affected source result or LOCUS claim from being used. P8/P9
measurements do not repair a rejected mapping and do not replace human review.

D018 requires paired profiles rather than a sole-suite cutover. The first pair
is Yi/aPPSS `k=2,n=3`; the second pair is Yi/aPPSS `k=3,n=5` after P6.3. Within
one pair, both suites must bind the same CuePolicy, synthetic protected key,
holder count and reconstruction threshold, authorization topology/quorum,
admission, storage, network/failure schedule, host class, and metric
definitions. A common-condition manifest is required. Native state, messages,
results, and evidence paths remain suite-specific, and a paired processor must
reject rows whose common-condition bindings differ.

The first paired evidence profile is `k=2,n=3` and is limited to static
read-only persistent-state compromise. It must separately record conformance
to the RFC 9497 OPRF-mode ristretto255/SHA-512 realization, canonical
`GF(2^128)` operations, 16-byte mask/commitment/secret values, SHA-256 domain
framing, and abort-only robustness. Tests are not evidence for Theorem 2 itself
or for a stronger adaptive, proactive, or side-channel model.

P5A.6 supplies `LOCUS-recovery-suite-compromise-regression-v1` as a strict
aggregate-only development regression for this first pair. It evaluates every
2-of-3 below-threshold coalition, every exact-threshold subset, and the
all-server view under one common-condition manifest. The evaluator accepts no
arguments and writes no output. Its schema and in-memory report do not allocate
the P9 result family, authorize collection, or promote either inherited
cryptographic statement to supported evidence.

## External services

External provider experiments are benign functional/performance operations
using disposable research accounts and synthetic data. Adversarial testing
remains within the explicitly authorized local/disposable boundary.

The default admission evidence uses only the project-controlled local
synthetic issuer. An optional OIDC/PKCE/DPoP adapter is an external-service
profile with separate authorization, versioning, provenance, privacy analysis,
and results; it is never silently included in the default result family.

The approved supplemental AWS S3 profile must first pass the complete contract
against the deterministic local S3-compatible service. Any live execution
requires a separately authorized disposable research account, retains no
account or credential identifiers, gives the client no persistent provider
credential, and does not turn S3 access control, Versioning, or Object Lock into
evidence of descriptor freshness or rollback resistance.

Reviewer and CI workflows must not require external credentials.
