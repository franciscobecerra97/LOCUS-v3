# Evidence Policy

## Purpose

This project promotes a claim only after the exact implementation profile has
matching, privacy-safe, provenance-bound evidence.

## Retained baseline boundary

The retained v1/v2 corpora are stored under their exact versioned paths. V1 is
superseded historical material. V2 is baseline evidence only for the exact
frozen profile and provenance it records. It is not evidence for changed
CuePolicy, descriptor, admission, topology, provider, or lifecycle semantics.

Raw records remain immutable. Deterministic verification and processing may be
rerun. Changed profiles use new identifiers and paths and must never be mixed
with the inherited corpora.

## Required scenario contract

Every security-sensitive experiment records:

- claim or invariant;
- protected asset;
- protocol phase;
- exact policy, descriptor, backup, deployment, and schema versions;
- TPASS threshold and holder identities;
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
- TPASS password input, group secret, shares, or wrapping key;
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

Any change to policy semantics, descriptor, topology, threshold, admission,
recovery-bundle format, cloud backend, clean-client boundary, metric definition,
or trace policy
requires a new profile and result version.

Do not mix profiles, commits, hosts, policies, thresholds, or topology in one
processed corpus unless the schema and methodology explicitly define that
comparison.

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
