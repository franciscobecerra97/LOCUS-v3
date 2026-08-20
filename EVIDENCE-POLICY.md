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
`docs/version-registry-v1.json`. Reservation is not evidence authorization.
D027 assigns only P8.3's exact managed-flow trace/result family. D028 assigns
the non-collecting P9.1 methodology. D029 now assigns P9.2's non-collecting
performance/resilience contracts after their privacy boundary, schemas,
positive controls, metrics, provenance, processor, and path were approved;
P9.3 collection remains separately gated.

P1.5's `docs/security-matrix-v1.json` supplies the minimum security contract
for every C01--C26 row. Before implementing or collecting a scenario, copy its
asset, adversary, assumptions, boundary, positive control, expected
privacy-safe observation, and interpretation limit into the assigned scenario
methodology and narrow them for the exact profile. The matrix itself is not
evidence and cannot promote a claim.

D025/P7.7 assigns `LOCUS-security-matrix-v2`. Its JSON/schema pin the immutable
matrix-v1 digest and C01--C26 IDs and add M01--M05 for
Manager/controller, package, dynamic-client/reset, edge-network, credential-
lifetime, and transient-key-display boundaries. Assignment followed the full
P7.7 smoke/browser gate, not the focused matrix check alone. Matrix v1 stays
immutable, and neither matrix nor the P7.7 acceptance output authorizes retained
collection by itself.

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

## Primary integrated-system evidence boundary

D023 makes the P7.5 same-host integrated reference deployment the required
system under test for new paper-facing P8/P9 security, reliability,
information-flow, performance, resilience, and later artifact results. A
central system scenario must begin at the stable UI/client API boundary and
traverse the exact deployed admission, operator/discovery, storage gateway,
local S3-compatible provider, applicable resolver, and authenticated party
services declared by the validated configuration.

D024 makes `prototype_final/` the sole source boundary for that system. Every
new P8/P9 collection must bind and execute the implementation, manifest,
deployment assets, lockfile, and executor from that directory. A root command,
root test suite, copied component harness, or separately assembled graph may
support regression analysis but cannot substitute for the D024 system result.

D025 changes the active operator, UI/API, controller, package, and clean-client
boundaries. P7.7 is complete and the managed profiles are Assigned, so that
deployment is now the required system under test and D023 is a supporting
predecessor. No P8/P9 evidence was collected during P7.7; collection remains
prohibited until the applicable P8/P9 schema, trace, result, provenance, path,
positive-control, and output-safety gates pass. An integrated result must begin
with Manager-created dynamic Client instances
and exercise the Manager/controller and client recovery-package boundaries
wherever the scenario includes lifecycle, enrollment, export/import, or clean
recovery.

Primitive vectors, native tests, unit/property/fuzz tests, the P7 in-memory
backend, P6 process profiles, the frozen Compose deployment, and
microbenchmarks remain necessary supporting controls. They cannot substitute
for, be pooled with, or be relabeled as integrated-system evidence. P7.5 smoke
and P7.7 managed acceptance output are ordinary implementation verification;
retained evidence begins only after P8/P9 assign the applicable trace, result,
methodology, and collection profiles.

Every integrated result additionally binds:

- stable UI and client-API versions and the container-backed adapter version;
- for the managed profile, Manager UI/API, controller API/profile, managed-
  client-instance, client-recovery-package, and clean-client-isolation
  versions;
- integrated deployment/configuration identity and canonical manifest digest;
- resolved and live service-graph digests;
- immutable container image identities and runtime locks;
- service identities, certificate/trust profile, role placement, networks,
  mounts, and published loopback endpoint;
- bootstrap root execution with every capability dropped except exactly
  `CHOWN` and `DAC_READ_SEARCH`, `network_mode: none`, no Docker socket, and
  successful exit before unprivileged runtime services;
- exact `management`, `client-lifecycle`, `manager-edge`, and `browser-edge`
  membership plus absence of Client-to-Manager and UI-to-Docker reachability;
- provider mode, recovery suite, holder threshold/topology, authorization
  quorum, CuePolicy, admission profile, and failure schedule; and
- dynamic active-client A/B isolation and public instance bindings, Manager/
  controller trust boundary, exact Docker project, host tier, source commit,
  cleanup, and output-scan status.

Stable client-API latency is the primary full-system protocol measure. Any
browser-observed latency is a separately labeled UI observation and must not be
silently combined with protocol timing. Same-host local S3-compatible results
are the reproducible baseline. AWS and multi-host runs remain optional,
separately authorized profiles with separate results and cannot be required of
normal reviewers.

## Required scenario contract

Every security-sensitive experiment records:

- claim or invariant;
- protected asset;
- protocol phase;
- exact recovery-suite, policy, descriptor, backup, deployment, and schema
  versions;
- for an integrated-system scenario, the exact UI/API/backend,
  configuration/manifest, resolved/live graph, image, service-identity,
  network, provider, and active-client-boundary bindings required above;
- for a managed-system scenario, the exact Manager/controller action schedule,
  client-instance identities and transitions, package profile/digest, and
  whether the synthetic private key was exposed to the active browser;
- for Client process actions, the preserved public ID, rotated proof identity,
  cleared volatile-state observation, and whether the transition was stop/
  start, restart, kill/start, or destroy/create;
- credential CA/leaf validity, preserved-versus-reset volume mode, manifest-
  compatibility outcome, and explicit destructive-reset status without
  retaining raw keys or certificate subject identifiers;
- exact `management`, `client-lifecycle`, `manager-edge`, and `browser-edge`
  membership and observed contacts, including absence of managed-Client-to-
  Manager reachability;
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
profile, descriptor, topology, threshold, admission, recovery-bundle or export-
package format, cloud backend, Manager/controller API, client API/UI, clean-
client boundary, metric definition, or trace policy requires a new profile and
result version.

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

D026 assigns `LOCUS-managed-state-evidence-profile-v1` for P8.2. Its canonical
scenario manifest contains exactly 42 SB01--SB14 records, split into 18 Yi, 18
aPPSS, and six suite-neutral common reports. Retention is permitted only from a
clean committed collector after all four matched arms, the fixed role snapshot
sets, positive controls, output scan, and cleanup pass. Publication is one
exclusive directory rename into
`prototype_final/evidence/retained/managed-state-v1/`; partial or replacement
publication is prohibited. The records may retain only approved aggregate and
public provenance fields and must never retain raw state, secret-state content
digests, cues, candidate/per-candidate data, suite secrets, shares, keys,
credentials, certificates, databases, logs, traces, screenshots, absolute
paths, or developer identity. This implementation evidence does not prove an
inherited cryptographic result and does not satisfy D019 independent review.

The v1 corpus was collected once from clean source commit
`6e304560222b8059292ae291586ee792cc39ed3d`. Its exact 42 records close to
`records_sha256=e31b215c936ed6693ac84e2bcf2d497a986e6e7cfaf0445637a749836aab83d5`.
This completes P8.2 only; P8.3 trace and P9 performance/resilience collection
remain separately gated.

D027 assigns P8.3's seven managed-flow identifiers and its exact 30-report
NF01--NF12 manifest: 12 Yi, 12 aPPSS, and six common reports. Instrumentation
is limited to existing synthetic-browser, Manager/Client route, authenticated
RPC, logical provider, and constrained Docker adapters under explicit evidence
contexts. Health traffic is excluded. Packet capture, payloads, routes,
addresses, headers, timing, per-event timestamps, raw logs, and event ordering
are not retainable. Sender/receiver observations must reconcile where both are
available; provider and Docker retain only their fixed logical boundary.

Any unknown/prohibited contact, NoResolver violation, observation mismatch,
sequence or byte-bound failure, output finding, missing positive control,
incomplete scenario, or cleanup failure rejects the whole run. Raw structured
events and service logs are scanned and discarded. A retained run requires a
clean committed collector and may publish only by exclusive atomic rename into
`prototype_final/evidence/retained/managed-flow-v1/`; it publishes all 30
canonical records or none and never replaces an existing corpus. D027 assigns
no P9 metric and authorizes no manuscript change.

The v1 corpus was collected once from clean source commit
`cd5aaaf762a9b18bef681f496f704f772fe6e9be`. Its exact 30 reports close to
`corpus_sha256=1deb49fcf5a7550f16da28702d1364ce20603f573d872cf811f631d331cf842c`.
This completes P8.3 only; P9 remains separately scoped and gated.

P8.4 preserves the frozen `LOCUS-attempt-model-report-v1` counterexample,
schema, and signed-certificate controls inside `prototype_final/` and binds
their execution to the exact D025 4-of-5 managed manifest. The command emits
temporary public output only and retains no result. It is a bounded negative
regression and local implementation control, not evidence of a global,
lifetime, or rollback-resistant attempt bound. D012 and all P9 collection
remain separately gated.

D028 assigns only `LOCUS-managed-performance-methodology-v1`. Its canonical
P9.1 contract freezes the exact D025 four-arm same-host/local-provider block,
sample, warm-up, failure/restart, successor, concurrency, lifecycle, metric,
statistical, exclusion, and interpretation rules before collection. P9.1
retains nothing and allocates no result identifier or path. P9.2 must
separately approve strict performance/resilience schemas, positive controls,
privacy-safe fields, provenance/hash closure, invalid-run representation,
processors, and exclusive append-only paths before P9.3. No P8 or historical
v2 corpus may be pooled or relabeled. P9.4 external-provider, WAN, and
multi-host collection remains separately authorized.

D029 assigns P9.2's ten non-collecting managed-performance contracts. MP00--
MP19 expand deterministically to 1,220 scheduled slots, including 40
unmeasured warm-ups and 1,180 measurements. Yi, aPPSS, and common observations
remain separate. Infrastructure-invalid attempts are immutable, excluded with
counts disclosed, and may be followed only by a new record binding the prior
SHA-256 digest. The deterministic processor refuses incomplete schedules,
silent retries, outlier removal, mismatched provenance, historical/P8 inputs,
pooling, and unsealed output. P9.2 creates no retained directory. P9.3 alone
may exclusive-create append-only raw attempts, summary, comparison, and closing
manifest under `prototype_final/evidence/retained/managed-performance-v1/`.

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
