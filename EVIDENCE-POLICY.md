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

## Required scenario contract

Every security-sensitive experiment records:

- claim or invariant;
- protected asset;
- protocol phase;
- exact recovery-suite, policy, descriptor, backup, deployment, and schema
  versions;
- reconstruction threshold `k`, holder identities, and any source-paper
  threshold-notation mapping;
- for aPPSS, the exact OPRF/field/hash/theorem profile and whether the view is
  below threshold or at/above threshold;
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

Any evidence supporting the D016/M-APPPSS-001 comparison must keep three claims
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

## External services

External provider experiments are benign functional/performance operations
using disposable research accounts and synthetic data. Adversarial testing
remains within the explicitly authorized local/disposable boundary.

The approved supplemental AWS S3 profile must first pass the complete contract
against the deterministic local S3-compatible service. Any live execution
requires a separately authorized disposable research account, retains no
account or credential identifiers, gives the client no persistent provider
credential, and does not turn S3 access control, Versioning, or Object Lock into
evidence of descriptor freshness or rollback resistance.

Reviewer and CI workflows must not require external credentials.
