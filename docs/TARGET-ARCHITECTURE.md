# Target Architecture

Status: owner-approved target design for D001, D003--D005,
D008--D010, D014--D018, D023, and D025. D015 supersedes D002/D006;
D018 supersedes D007/D016. D023's fully connected same-host reference system is
implemented. D025/P7.7's separately versioned Manager/controller and dynamic-
Client deployment is implemented and Assigned; P8.1 assurance is complete and
P8.2 is the next proposed step, but retained P8/P9 evidence remains gated. It
does not change any completed
component or frozen deployment profile. This document does not
supersede the implemented baseline architecture or current manuscript until the affected
implementation/evidence gates and a separate exact manuscript delta are
approved by the owner.

The D025 control plane has two disjoint internal networks: `management` joins
only Manager and controller, while `client-lifecycle` joins only controller and
managed Clients. A managed Client cannot reach the Manager UI/API. Only the
controller receives the root-equivalent Docker socket; neither UI does. The
two browser-publication networks are also disjoint: `manager-edge` contains
only the Manager and `browser-edge` only dynamic Clients, each with a separate
host-loopback path. Neither becomes a Manager-to-Client network. The assigned
client recovery package is additive and does not replace the local provider,
authenticated current state, admission, authorization, or online threshold
parties.

Client stop/start, restart, and kill/start retain the public client-instance ID
but rotate the process proof identity and clear the server-side key slot,
export/import cache, and operation/session set. Destroy removes the instance
and ID; already loaded browser content remains outside that process reset.
Managed bootstrap issues a
366-day CA and 365-day role TLS certificates with no in-place renewal. Default
stop preserves volumes; only explicit emergency `integrated-stop --reset-state`
removes all exact-project credentials and protocol/provider state.
The one-shot bootstrap runs as root with every Linux capability dropped except
exactly `CHOWN` and `DAC_READ_SEARCH`, uses `network_mode: none`, receives no
Docker socket, and exits before unprivileged runtime services start.

P1.3 now implements the suite-neutral in-memory contract layer described here,
including a thin frozen-Yi compatibility adapter and typed CuePolicy/resolver
adapters. See `SYSTEM-INTERFACES.md`. Descriptor, admission, gateway, lifecycle,
and client-state-machine entries remain contracts only until their later
chronological phases implement and evaluate them.

P1.4 freezes the allocation rules and protected-identifier ledger in
`VERSION-REGISTRY.md` and `version-registry-v1.json`. Future architecture
families are reserved by decision and chronological schema gate, not assigned
usable identifiers in advance.

P1.5 completes the prospective six-phase/twelve-view information-flow matrix
and the schema-checked C01--C26 security contracts. D025/P7.7 assigns a matrix-
v2 revision that preserves those meanings and adds M01--M05 for managed-control,
package, dynamic reset, credential-lifetime, edge-network, and transient-key-
display boundaries. These define later evidence obligations without promoting
unsupported claims.

P2.1 now implements the strict descriptor, signed current-pointer,
two-entry manifest, and deterministic bounded ZIP codecs described below.
P2.2 implements strict installed-trust, optional-receipt, party-current-summary,
and pure clean-client bootstrap validation over supplied discovery bytes.
P2.3 implements the provider-neutral filesystem/S3-compatible descriptor and
bundle stores, exact-key profile, and current-pointer CAS below a same-host
service boundary. Admitted retrieval remains P3 because its capability profile
is intentionally unassigned. P2.4 supplies aggregate development regression
scenarios; formal evidence remains under the later evidence gates.

P3.1 implements the suite-neutral enrollment phase machine as a secret-free
public retry-state coordinator. P3.2 implements its authenticated provisioning
boundary: clean party processes accept only recipient-bound initial packages
over pinned mutual TLS 1.3 with durable exact-request idempotency. The frozen Yi
codec is active. P5A.3 separately implements aPPSS server-local OPRF-key
creation, durable holder state, and pinned mutual-TLS recovery. P5A.4 adds
authenticated distributed initialization and common-public-state installation;
P5A.5 adds descriptor/bundle preparation and P4.3 successor integration in all
four suite directions. D020 activates this application/component interface
after provisional internal mapping acceptance. P6.3 adds matched same-host
process profiles; independent human validation, retained evidence, and actual
host separation remain later gates.

P3.3/P3.4 implement the provider-neutral local admission component boundary:
an allowlisted synthetic subject receives an Ed25519-signed, proof-key-bound,
short-lived exact-scope capability; each authorizer verifier and the storage
gateway keeps independent digest-only replay state. The gateway validates
before its storage backend call. This local test double adds no external IdP,
recovery factor, CuePolicy input, or recovery-suite transformation.

P4.1 implements the recovery state-machine spine. It fixes the authenticated
backup/epoch after descriptor verification, enforces exact ordered retries,
and keeps suite/decryption outcomes out of persisted state and party-visible
messages. P4.2 and P4.3 supply isolation and successor orchestration.

P4.2 implements a bounded clean-client isolation harness. Enrollment and
recovery use different client roots and transport identities; Client A's root
is absent before Client B starts in a sanitized subprocess. Client B receives
only public recovery configuration, installed trust material, a fresh key, and
transient recovery input, while all Yi state remains behind party APIs.

P4.3 implements the durable post-recovery successor coordinator. Its public
journal binds exact predecessor/successor metadata and digests, drives one
deterministically idempotent effect at a time, verifies the prepared successor
recovers the original key before cutover, and defaults to no key rotation. The
frozen party lifecycle then performs its existing atomic retire/activate
transaction; the following logical retirement phase confirms that result.

D023 inserted P7.5 before P8. P7.5 connects the existing loopback research UI
and stable client API to authenticated admission, operator/discovery,
storage-gateway, local S3-compatible, resolver, and five-party services in one
separately versioned Compose family. The current same-process UI remains a
component conformance control, and frozen `LOCUS-compose-deployment-v2`
remains historical evidence for its exact Yi-only meaning. The integrated
profile, identifiers, and operator commands were assigned together by the
P7.5 allocation and implementation gates. See
`INTEGRATED-REFERENCE-SYSTEM.md`.

D024 makes the self-contained `prototype_final/` copy of that implementation
the sole active P8+ source and later artifact boundary. Root implementations
remain historical/component controls and are not alternative final systems.

## Design principle

Keep the cryptographic data path stable and build realistic system behavior
around it through explicit interfaces.

```mermaid
flowchart LR
    UI["Enrollment / Recovery UI"] --> Client["Client state machines"]
    Client --> Policy["CuePolicy registry"]
    Policy --> Resolver["Resolver adapters"]
    Client --> Selector["Enrollment / successor suite selector"]
    Client --> Registry["Descriptor-bound suite registry"]
    Selector --> Registry
    Registry --> Suite["Yi or aPPSS recovery-suite client"]
    Client --> Admission["Admission issuer / verifier"]
    Admission --> Gateway["Application storage gateway"]
    Client --> Gateway
    Gateway --> Backup["BackupObjectStore"]
    Gateway --> Descriptor["DescriptorStore"]
    Gateway --> Bundle["RecoveryBundleStore"]
    Client --> Directory["Authenticated party directory"]
    Directory --> Parties["Authorizers and suite holders"]
    Suite --> Parties
    Parties --> Audit["Local signed audit state"]
    Client --> Lifecycle["Lifecycle manager"]
    Lifecycle --> Gateway
    Lifecycle --> Parties
```

## Components

### Client core

Owns:

- enrollment and recovery state machines;
- local CuePolicy invocation;
- explicit suite/profile selection for enrollment and successor creation;
- descriptor-bound suite dispatch for recovery, without fallback;
- recovery-suite client phases through a suite-neutral interface;
- backup encryption/decryption;
- descriptor validation;
- threshold and epoch consistency;
- exact protected-key identity verification;
- lifecycle orchestration.

The UI never implements these operations independently.

### CuePolicy registry

Maps an immutable policy identifier to:

- accepted structured input;
- resolver requirements;
- validation;
- canonicalization;
- ambiguity and duplicate behavior;
- public version metadata;
- deterministic vectors.

The registry preserves `LOCUS-location-person-set-v1` byte-for-byte and P5.3
adds three owner-approved atomic policy adapters under new identifiers:

- exactly three distinct quantized geographic coordinates;
- exactly three distinct canonical E.164 phone numbers; and
- exactly three distinct canonical constrained email addresses.

Direct-input forms of the three atomic policies use P5.4's exact `NoResolver`
adapter. The frozen composite location-person policy remains the resolver-backed
reference example. P5.2 freezes their exact design in
`docs/CUE-POLICY-PROFILES.md`; P5.3 assigns the policy and conformance-corpus
identifiers with implementations and canonical vectors.

### Resolver adapters

Possible profiles:

- deterministic fixture;
- implemented `NoResolver` for direct coordinate, phone, and email input;
- local user-controlled records;
- separately approved external provider.

Resolver output never becomes a stored cue verifier.

### BackupObjectStore

Stores immutable canonical encrypted backup objects. The existing filesystem and
S3-compatible adapters form the reference contract.

### DescriptorStore

Stores immutable signed descriptors and an authenticated current pointer with
compare-and-swap semantics. It is distinct from backup storage because current
configuration changes across epochs.

### Application storage gateway

P3.4 validates the D004/D015 proof-key-bound storage capability before mapping
one exact authorized operation to the provider-neutral backup, descriptor,
current-pointer, or bundle interface. It exposes no bucket listing, retains no
client credential, and returns only bounded LOCUS failure categories. Provider
credentials remain server-side and are scoped to the application namespace.

### RecoveryBundleStore

Provides an optional physical packaging layer for account-scoped providers.
Each immutable bounded ZIP contains exactly the canonical backup object, signed
descriptor, and manifest for one epoch. The authenticated mutable current
pointer remains outside the ZIP. The descriptor binds the canonical backup
member; the pointer binds the provider-assigned bundle locator, exact uploaded
bundle, and descriptor, avoiding self-referential digest and locator cycles.

An application-operated S3 namespace may implement backup, descriptor, pointer,
and bundle operations in one admitted account scope. Their logical contracts,
decoders, failure categories, and lifecycle rules remain distinct. S3 access
control is not a descriptor trust root.

### Party directory

Provides authenticated service identity and endpoint information. It must be
rooted in trust outside any unauthenticated descriptor.

### Authorizers and recovery-suite holders

Every service is an authorizer. A configured subset additionally stores one
native recovery-suite state. The frozen Yi holder and P5A.3 aPPSS holder are
disjoint adapters and state types. Authorization quorum and recovery
threshold remain separate. D018 permits both suites for new enrollments, but
one epoch and holder set binds exactly one suite.

### Admission

Authenticates and authorizes a client request independently from TPASS. The
default research path uses a deterministic local issuer; an external OIDC/DPoP
profile is optional.

The D004 profile also issues short-lived storage capabilities bound to
subject, backup identifier, object prefix, operation, client proof key, nonce,
and expiry. An application storage gateway validates the capability and
performs the exact S3 operation. Clients receive no provider credential and
need no personal AWS account. Direct S3 pre-signed bearer URLs are outside the
approved core profile.

### Lifecycle manager

Coordinates successor preparation, backup and descriptor publication,
activation, predecessor retirement, and eventual membership replacement.

## Recommended reference profiles

### Reproducible local integrated profile

- host browser connected only to a loopback UI/client-gateway container;
- deterministic local admission/capability service;
- authenticated operator/discovery/signing service;
- application storage gateway with narrow server-side credentials;
- local S3-compatible backup/descriptor/bundle/current-pointer store;
- fictional resolver fixture, contacted only by the resolver-backed policy;
- five authenticated authorizer/holder containers;
- paired selectable Yi/aPPSS 2-of-3 and 3-of-5 profiles;
- separately typed 4-of-5 authorization quorum;
- isolated Client A enrollment and clean Client B recovery roots; and
- no external accounts.

P7.5 implements this predecessor on one Docker engine. The browser neither
controls Docker nor contacts parties or object storage directly. A networkless
bootstrap step may create synthetic credentials, public configuration, empty
role roots, and fixtures, but it may not inject recovery-suite state or
secret-bearing client state.

D025/P7.7's assigned managed deployment is the mandatory full-system boundary
for P8 and later work. Its mode-free launcher starts the common service plane,
Manager, and controller with no Client. Manager-created Clients use Client API
v2 and the managed Client UI for enrollment and package-based recovery. The
controller alone holds the root-equivalent Docker socket. `management` is
Manager/controller only; `client-lifecycle` is Client/controller only; a
Client cannot reach the Manager UI/API. `manager-edge` and `browser-edge`
publish only the Manager and dynamic Client loopback paths respectively.
Stop/start, restart, and kill/start clear volatile Client state without changing
the public client ID; destroy/create changes it. The local provider and
authenticated protocol path remain mandatory. The implementation and matrix/
schema passed P7.7, but remain pre-evidence development observations.

The existing runnable local profiles remain narrower controls. The P6 endpoint
overlay is useful for exercising the eventual public host configuration while
all containers remain under one Docker engine. A separate-host endpoint file
is only placement input; actual distribution, firewalling, durable disks, and
tier validation remain external deployment work. Neither the frozen Compose
smoke command nor the current same-process UI command runs the D023 system;
the `integrated-*` commands do.

The current component adapters supply deterministic recovery-bundle and
current-pointer behavior so the bootstrap contract can be tested without an
external provider account.

### Clean-client multi-VM profile

- two isolated clients;
- separate VMs for cloud/descriptor roles and parties;
- distinct keys and storage;
- paired Yi/aPPSS 2-of-3 and 3-of-5 variants;
- explicit network topology;
- synthetic data.

### Supplemental provider profile

- AWS S3 backup/descriptor/current-pointer/bundle profile;
- application-operated account-scoped namespace;
- application storage gateway and proof-key-bound short-lived capability;
- disposable research account;
- benign functional and performance operations;
- no reviewer credential requirement;
- no independent-administration or production claim.

P6.2 implements the application-side AWS specialization and the exact admitted
gateway backend. Local fake-S3 conformance is the reproducible result. The
read-only AWS connectivity test remains separately execution-gated, so this is
not yet a real-provider result.

### Local research interface

P7 implements `LOCUS-local-research-ui-v1` after freezing the client API. The
semantic HTML/CSS/JavaScript layer delegates every policy, suite, descriptor,
admission, storage, recovery, successor, and inspection operation to
`LOCUS-client-api-v1`. It is served only on loopback by the pinned Python
runtime, uses no remote assets or browser persistence, and has no recovery
suite selector after bootstrap. The research inspector renders only the API's
safe public identifiers, digests, categories, placement, and aggregate counts.
See `RESEARCH-UI.md`.

This realizes the P7 component boundary only. Browser/OS capture and process
memory remain outside the UI's control, and no usability, external-service,
retained-evidence, or manuscript claim follows from it.

P7.5 reuses this frozen UI/API meaning in an ephemeral container and replaces
its same-process record-store bindings with authenticated remote-service
adapters. Enrollment, clean-client recovery, inspection, and same- or
cross-suite successor workflows traverse the deployed service graph. That
realization received a new deployment/configuration identity in P7.5 work
package 1; it does not rename either P7 identifier.

## Architecture boundaries

- Provider choice must not change CuePolicy or recovery-suite semantics.
- Normal clients must not require bucket-list permission or a long-lived cloud
  credential.
- Physical bundle colocation must not collapse the immutable-backup,
  immutable-descriptor, and mutable-current-pointer contracts.
- UI choice must not change canonical bytes.
- In D023, the browser may reach only the loopback UI/client gateway. In D025,
  it may reach the separate loopback Manager and a Manager-created Client UI;
  neither receives a provider credential, party credential, Docker socket, or
  operator secret.
- Central P8/P9 retained results must bind the exact D025 managed manifest and
  remain blocked until their applicable schema/trace/result gates; D023,
  component tests, and frozen deployments remain supporting controls.
- Admission failure must not become a recovery-suite correctness result.
- A descriptor cannot introduce a local cue test.
- The selected admission issuer is an explicit availability prerequisite. The
  default profile uses the local synthetic issuer; an external identity account
  exists only in an optional separately versioned adapter profile.
- A global attempt authority is not mandatory core architecture.
- A multi-host deployment is not automatically independently administered.
