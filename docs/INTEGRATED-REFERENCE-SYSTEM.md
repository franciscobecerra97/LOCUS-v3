# Integrated Reference System

Status: D023 owner-approved target; P7.5 implementation not started.

## Purpose

P7.5 replaces fragmentation as the future evaluation boundary. It does not
remove the smaller profiles: it composes their already approved contracts into
one new reference system whose browser workflow crosses the actual service,
container, network, credential, and persistent-state boundaries that P8 and P9
will evaluate.

The integrated profile is new. It does not modify or reinterpret frozen
`LOCUS-compose-deployment-v2`, retained v2 evidence, P6.3 process comparison
controls, the P7 same-process API facade, or the P7 UI profile.

## Deployment taxonomy

| Profile | Purpose after D023 | Full-system evidence status |
| --- | --- | --- |
| P7 same-process UI/API | Fast semantic and browser component control | Cannot support an integrated-system result |
| Frozen Compose v2 | Historical Yi-only deployment and retained v2 provenance | Remains frozen and non-transferable |
| P6.3/P6.4 process profiles | Suite/topology and endpoint/placement controls | Supporting only; same-host staging is not host independence |
| P7.5 integrated local reference | Primary UI-to-services implementation, assurance, evaluation, and artifact target | Required for new central P8/P9 results after its gates pass |
| Optional AWS or multi-host integrated variants | Supplemental provider or placement measurements | Separately authorized, versioned, and reported |

These profiles are intentionally distinct because they answer different
questions. D023 makes only the P7.5 family the future complete-system boundary;
it does not make the older profiles redundant or evidence-equivalent.

## Target system

```text
host browser
  |
  | loopback HTTP only
  v
ephemeral UI + client-API gateway container
  |-- admission network --> local synthetic admission/capability service
  |-- discovery network --> operator/discovery signing service
  |-- storage network ----> application storage gateway
  |                           |
  |                           +-- cloud network --> local S3-compatible store
  |-- resolver network ----> resolver service (only for resolver-backed policy)
  +-- recovery network ----> party1 ... party5 (pinned mutual TLS)
```

The browser never contacts recovery parties, the object store, or provider
credentials directly. The UI continues to call only `LOCUS-client-api-v1`.
The client gateway implements that stable contract through remote-service
adapters and keeps CuePolicy, suite, descriptor, admission, storage, and
lifecycle logic out of browser code.

## Required roles

| Role | Responsibility | Permitted durable state | Prohibited state |
| --- | --- | --- | --- |
| UI/client gateway | Serve the local UI; coordinate one active enrollment or recovery client | Public installed trust and bounded secret-free operation state only when explicitly required | Raw/canonical cues, password input, `S_R`, `K_wrap`, protected-key plaintext, provider credentials, or complete party state after the operation |
| Admission service | Authenticate the synthetic subject and issue proof-key-bound capabilities | Issuer key, allowlist, digest-only replay/audit state | Cue material, suite state, recovery outcome, storage-provider credentials |
| Operator/discovery service | Sign descriptors, pointers and receipts; expose account-scoped discovery | Operator key, public directory/current metadata | Cue material, suite secret state, plaintext protected key, provider credentials |
| Storage gateway | Validate exact admitted operations and invoke the provider | Narrow provider credential and digest-only replay state | Cues, suite password/state, recovery secret, wrapping key, plaintext key |
| S3-compatible store | Persist immutable backup/descriptor/bundle objects and mutable current pointer under their distinct contracts | Encrypted/public LOCUS objects and provider metadata | Cue hints/verifiers, party secrets, recovered/wrapping/plaintext keys |
| Resolver | Resolve only the frozen resolver-backed policy; atomic policies use `NoResolver` | Synthetic fixture and bounded service configuration | Suite, backup, party, recovery-secret, or private-key state |
| Parties 1--5 | Authorize and, when selected, hold exactly their own Yi or aPPSS state | Own identity, role-local suite state, public epoch/configuration, idempotency/lifecycle/local audit state | Another party's state, complete threshold state, cues, `S_R`, `K_wrap`, plaintext key, authoritative backup object |
| Networkless bootstrap | Generate synthetic service credentials, public configuration, empty role roots and fixtures | No runtime state after setup | Network access, recovery-suite state injection, cue-derived state, protected-key state |

Each runtime role is a distinct non-root container with a read-only root
filesystem where practical, exact network membership, an explicit health
check, bounded resources, disabled core dumps, and only its own volume and
credentials. The resolved Compose graph and the live graph must both be
validated before an end-to-end result is accepted.

## Deployment arms

One integrated family supports four separately bound arms:

1. Yi TPASS 2-of-3 holders, five authorizers, 4-of-5 authorization;
2. aPPSS 2-of-3 holders, five authorizers, 4-of-5 authorization;
3. Yi TPASS 3-of-5 holders, five authorizers, 4-of-5 authorization; and
4. aPPSS 3-of-5 holders, five authorizers, 4-of-5 authorization.

One epoch authenticates exactly one arm. Recovery has no suite override or
fallback. Same-suite and bidirectional cross-suite successors create fresh
state and a consecutive epoch. Every evidence row remains suite/topology
specific even when a comparative processor checks matched common conditions.

The exact integrated deployment/configuration identifiers are deliberately
unassigned until P7.5 work package 1 introduces the strict manifest/schema,
compatibility rules, validators, and first canonical synthetic configuration
together.

## Provider boundary

The reproducible system uses the existing local S3-compatible contract through
the application storage gateway. The client receives no provider credential,
requires no personal cloud account, and has no listing operation. "Cloud
services" means this provider-neutral cloud-object role. Apple iCloud is not a
selected adapter.

AWS S3 remains an optional D015 supplemental profile. A live AWS or other
provider run requires separate authorization, disposable synthetic resources,
a distinct deployment/evidence profile, and no reviewer credential
requirement. It cannot replace the local reproducible result.

## Enrollment and clean recovery

The full-system enrollment path is:

1. start Client A from the immutable UI/client image with a fresh proof and
   transport identity;
2. authenticate the synthetic subject and obtain exact capabilities;
3. process the selected CuePolicy locally;
4. initialize the selected suite through authenticated party APIs, with each
   aPPSS holder generating only its own OPRF key;
5. encrypt the synthetic protected key and publish backup, descriptor, bundle,
   pointer and party-current state through their authenticated services;
6. export the public receipt and report only safe placement/status; and
7. terminate Client A, make its root/identity inaccessible, and run a recursive
   post-enrollment audit with an inherited-state positive control.

The clean recovery path then:

1. starts Client B from the same immutable image with a fresh root, proof key
   and transport identity;
2. supplies only installed trust, the public receipt/handle, and fictional
   recovery input;
3. performs admitted discovery, validates the signed pointer/bundle/descriptor
   and matching party-current quorum before cue processing;
4. uses only the authenticated enrolled policy and suite;
5. recovers through an exact authorized threshold subset, decrypts the backup
   and verifies the original public-key fingerprint; and
6. optionally prepares and activates an explicitly selected successor before
   retiring the predecessor.

No active path may rely on direct party-volume state injection, a surviving
Client A credential, hidden developer state, or the P7 in-memory record store.

## Operator workflow target

P7.5 must provide:

- one cross-platform task that validates configuration, creates the disposable
  deployment, starts every required service, waits for health, and exposes the
  UI only on host loopback;
- one disposable smoke task that executes the fixed end-to-end acceptance
  matrix, scans outputs and state boundaries, and removes its exact labeled
  containers, networks, volumes and generated credentials; and
- explicit exact-target cleanup and status operations for an interactive run.

Final command names are assigned with the implementation. The browser does not
control Docker and receives no Docker socket or operator credential.

## P7.5 acceptance boundary

Before P8 begins, the same-host integrated system must demonstrate with
synthetic data:

- all four suite/topology arms through the UI/client API and real party APIs;
- all registered CuePolicies, including proof that direct policies never
  contact the resolver;
- exact-key enrollment, clean-client bootstrap/recovery and public identity
  verification;
- same-suite and cross-suite successor creation with explicit rotation choice;
- correct threshold subsets and below-threshold rejection;
- wrong-input normalization and no recovery-time suite fallback;
- party restart, one-party unavailability where satisfiable, quorum loss,
  provider outage, stale CAS, replay and exact retry;
- crash/restart at durable enrollment, publication and lifecycle boundaries;
- role-specific state, mount, environment, credential and network audits;
- prohibited-output and generated-canary scans; and
- deterministic exact-project cleanup.

These are implementation gates, not retained P8/P9 evidence or paper results.

## Assurance and evaluation dependency

P8 instantiates the existing C01--C26 contracts against the exact integrated
manifest. Component fuzzing and unit/property tests remain necessary, while
system-facing state, network, crash, replay, and output conclusions must be
observed on this deployment.

P9 freezes methodology and schemas only after P8 defines safe collection.
Central performance and resilience results use the integrated deployment and
bind its suite, topology, policy, provider, host tier, client boundary and
source provenance. Stable client-API timing is the primary end-to-end protocol
measure; optional browser-observed latency is reported separately so rendering
cost is not silently mixed with protocol cost. Native microbenchmarks may
explain components but cannot substitute for end-to-end results.

P10 packages the integrated system and its validated results for clean Linux
and Windows reproduction. Historical v2 results remain historical. Manuscript
wording changes only after independent suite mapping validation, P8/P9 closure,
artifact reproduction, claim-matrix closure, and a separate exact owner
approval.

## Explicit limitations

The first integrated profile is one-host, one-Docker-engine, one-operator
research infrastructure. It does not establish multi-host behavior,
independent administration, production IAM/PKI, real-provider behavior,
rollback-resistant global attempt limits, Byzantine availability, forensic
erasure, side-channel resistance, human memorability, accessibility
certification, usability, or production security.
