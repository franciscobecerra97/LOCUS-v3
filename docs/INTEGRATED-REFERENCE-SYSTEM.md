# Integrated Reference System

Status: D023 implementation and pre-evidence gate complete; D024 isolated it
under `prototype_final/`. D025/P7.7 Manager-controlled deployment and assignment
gate complete. P8.1 assurance is complete; no retained P8/P9 evidence has
been collected.

## Purpose

P7.5 first replaced fragmentation with the completed D023 predecessor. D025/
P7.7 now makes the assigned managed deployment the P8+ system boundary. Neither
removes the smaller profiles: the managed graph composes their approved
contracts across the service, container, network, credential, and persistent-
state boundaries that later assurance and evidence must evaluate.

D025 assigns a separately versioned deployment rather than reinterpreting this
completed profile. Its implementation starts a loopback Manager and constrained
controller with no Client, creates transient Client containers from the
Manager, and exposes enrollment plus authenticated recovery-package import in
one Client UI. Only the root-equivalent controller receives the Docker socket.
`management` is Manager-to-controller only; `client-lifecycle` is managed-
Client-to-controller only. `manager-edge` publishes only the Manager loopback
path and `browser-edge` only dynamic Client loopback paths. Neither edge is a
Manager-to-Client network; a Client cannot join `manager-edge` or reach the
Manager UI/API. The local provider and every authenticated protocol boundary
below remain. The twelve D025 managed identifiers are Assigned, not Frozen;
this D023 profile is an immutable supporting predecessor. Assignment does not
authorize P8/P9 collection before its separate schema and evidence gates.

The integrated profile is new. It does not modify or reinterpret frozen
`LOCUS-compose-deployment-v2`, retained v2 evidence, P6.3 process comparison
controls, the P7 same-process API facade, or the P7 UI profile.

## Deployment taxonomy

| Profile | Purpose after D023 | Full-system evidence status |
| --- | --- | --- |
| P7 same-process UI/API | Fast semantic and browser component control | Cannot support an integrated-system result |
| Frozen Compose v2 | Historical Yi-only deployment and retained v2 provenance | Remains frozen and non-transferable |
| P6.3/P6.4 process profiles | Suite/topology and endpoint/placement controls | Supporting only; same-host staging is not host independence |
| P7.5 integrated local reference | Completed UI-to-services predecessor and migration control | Immutable supporting predecessor; cannot support a D025 managed-system result |
| D025 managed integrated deployment | Manager/controller plus dynamically created Client UI/API over the unchanged service plane | Assigned and implementation-verified at P7.7; P8/P9 retained evidence remains gated |
| Optional AWS or multi-host integrated variants | Supplemental provider or placement measurements | Separately authorized, versioned, and reported |

These profiles are intentionally distinct because they answer different
questions. D023 makes only the P7.5 family the future complete-system boundary;
it does not make the older profiles redundant or evidence-equivalent.

## Completed D023 predecessor system

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

The exact family is `LOCUS-integrated-reference-deployment-v1` with canonical
manifest `LOCUS-integrated-reference-config-v1`. The admitted storage path uses
the separately versioned `LOCUS-cloud-backup-object-v2` and
`LOCUS-application-storage-gateway-v2` for registered backup v5/v6 objects;
frozen cloud-object/gateway v1 behavior remains unchanged.

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

## D025 managed operator and lifecycle profile

The implemented normal workflow uses one mode-free `integrated-start`. It
starts the service plane, controller, and Manager UI with zero Client
containers. The Manager creates a dynamic Client and is the normal whole-system
stop path. The Client UI handles enrollment/export and package-import recovery;
the Manager UI never handles protocol material.

The current thin-UI interaction guards do not change those API or protocol
semantics. The Client keeps enrollment controls locked until its backend
confirms that a transient key is loaded, while clean-client package recovery
remains available without a preexisting key. The Manager places the complete-
system stop control in its header and locks further mutating controls after
shutdown begins; read-only status refresh remains available.

Client process controls are intentionally destructive to volatile state.
`stop` and `kill` make the UI unavailable but retain its container and public
client ID. A later `start`, and every `restart`, rotates the proof identity and
clears the server-side key slot, export/import cache, and operation/session set
under that same ID. `destroy` removes the container and ID; a later create
receives a new ID. These semantics must be confirmed in the UI and do not
establish forensic erasure. An already loaded external browser document may
remain rendered until closed or reloaded.

Normal Manager stop and emergency `integrated-stop` preserve exact-project
role/provider volumes. The explicit emergency
`integrated-stop --reset-state` option deletes those volumes, credentials,
provider objects, party state, and enrolled epochs. The next start creates a
fresh trust domain. There is no in-place renewal of the managed 366-day CA or
365-day role TLS certificates; expired or manifest-incompatible preserved state
fails closed until full reset. A package cannot recover an epoch whose only
compatible remote state was erased.

The one-shot bootstrap runs as root with all Linux capabilities dropped except
exactly `CHOWN` and `DAC_READ_SEARCH`, uses `network_mode: none`, receives no
Docker socket, and exits before the unprivileged runtime services start. Those
capabilities are used only to create and revalidate owner-only per-role files;
bootstrap remains limited to synthetic credentials, public configuration,
empty role roots, and fixtures.

P7.7 acceptance exercised all four suite/topology arms, 26 threshold subsets,
four isolated clean Clients, live controller/network isolation, all documented
lifecycle actions, browser behavior, output scans, 15 bootstrap-role and 15
post-operation role audits, state-preserving normal restart with the same CA,
destructive reset with a fresh CA and old-package rejection, and exact cleanup.
The final integrated check and focused controller/bootstrap checks are green.
These are implementation observations, not retained P8/P9 evidence.

## Historical D023 predecessor operator workflow

P7.5 provides the last completed predecessor workflow:

- one cross-platform task that validates configuration, creates the disposable
  deployment, starts every required service, waits for health, and exposes the
  UI only on host loopback;
- one disposable smoke task that executes the fixed end-to-end acceptance
  matrix, scans outputs and state boundaries, and removes its exact labeled
  containers, networks, volumes and generated credentials; and
- explicit exact-target cleanup and status operations for an interactive run.

That predecessor used separate enrollment/recovery startup modes and a CLI
destroy option. Those flags are recorded only as migration provenance; they are
not commands for the active executor. Its browser did not control Docker and
received no Docker socket or operator credential.

P7.7 replaced this as the normal interactive workflow with a mode-free
`integrated-start`, Manager-created Clients, and Manager stop-system. The old
mode and CLI-destroy options are no longer accepted by the active executor;
their source history is provenance only. Exact-project CLI cleanup remains an
emergency and automated-smoke path, not the normal workflow.

The root executor and source tree are retained historical/component controls.
They are not active P8+ implementation or evidence paths and cannot replace a
run built wholly from `prototype_final/`.

The confirmed development gate covers all four suite/topology arms, all four
policy paths, clean-client isolation, wrong input, suite-bound dispatch, and
same-/cross-suite successors through the P4.3 crash-resumable publication
phases and explicit predecessor retirement. It runs all 26 suite-specific
exact-threshold subset recoveries, separates suite-threshold loss from 4-of-5
authorization loss, and checks replay, stale CAS, party/provider failure and
restart, live network membership, stopped role/provider state, dynamic output
canaries, and exact cleanup. Commit `d4a8da5` reproduced the same smoke from a
fresh checkout with an empty checkout-local uv cache and no host native
extension. These are completed implementation gates, not retained P8/P9
evidence or paper results.

## P7.5 acceptance boundary

The completed pre-P8 gate demonstrates with synthetic data:

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

P7.7 and P8.1 are complete, so P8.2 is the next proposed gate. The assigned
`prototype_final/docs/security-matrix-v2.json`/schema pin v1 and C01--C26 and
add managed contracts M01--M05. P8.1 instantiated their implementation-
assurance controls against the exact managed manifest. Component fuzzing and
unit/property tests remain necessary controls, while retained system-facing
state, network, crash, replay, lifecycle-
control, package, and output conclusions must be observed on the Manager-
created Client deployment. This D023 profile remains a supporting predecessor.

P9 freezes methodology and schemas only after P8 defines safe collection.
Central performance and resilience results use the managed integrated
deployment and bind its suite, topology, policy, provider, host tier, Manager/
controller, package, and client boundaries plus source provenance. Stable
client-API timing is the primary end-to-end protocol
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
