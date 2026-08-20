# Project Charter

## Objective

Develop LOCUS from a compact same-host research prototype into a complete,
realistically deployable reference recovery system while preserving the
existing storage-separation and no-offline-oracle thesis. D023 defines that
reference as one fully connected system: its loopback browser workflow must
traverse the deployed client, admission, discovery, storage, resolver when
required, and recovery-party boundaries rather than stop at an in-memory UI
facade or a separate component harness.

This repository jointly advances the reference system, its evidence, and the
owner-approved manuscript. The imported manuscript remains the authoritative
baseline until the owner approves an exact narrative delta; implementation
progress alone does not change it.

The target system should eventually provide:

- explicit clean-client bootstrap and recovery discovery;
- an authenticated, versioned RecoveryDescriptor;
- authenticated enrollment and recovery transport;
- public-client admission through a separately modeled authorization layer;
- exact original-key recovery and post-recovery successor enrollment;
- multiple immutable CuePolicy implementations behind one contract;
- provider-neutral backup and descriptor storage;
- multi-host recovery parties with distinct identities and suite-bound state;
- a safe, instrumented enrollment and recovery UI;
- one reproducible integrated local deployment connecting that UI to all
  authenticated services and the cloud-storage role;
- reproducible security, failure, information-flow, and performance evidence;
- independent clean-host reproduction and external technical review.

## Scientific thesis

The active imported baseline combines:

1. local, deterministic processing of structured recovery input;
2. TPASS-mediated recovery of a random group secret;
3. derivation of a symmetric wrapping key from that secret;
4. encrypted private-key storage at a separate cloud role; and
5. threshold state held by recovery parties.

The intended security boundary is that the cloud, fewer than the TPASS
threshold, or their matching persistent snapshots do not gain an offline test
for candidate cues.

D018 supersedes D016's sole-aPPSS cutover without changing that below-threshold
system thesis. D020 activates the P5A application/component interface after a
provisional internal mapping assessment: frozen Yi TPASS and D017 aPPSS are
independent first-class suites selected explicitly for each enrollment or fresh
successor epoch. Both solve the same password-protected recovery-secret problem
and feed the same HKDF/AES protected-key path, but retain distinct state,
messages, assumptions, and threshold-compromise behavior. Enough aPPSS server
state enables offline guessing but does not directly reveal `S_R` before a
correct password guess; matching Yi threshold state directly exposes its
high-entropy recovery secret. No low-entropy-cue, rate-limit, or continued
threshold-security claim follows.

D017 and `docs/APPSS-PROFILE.md` freeze the initial successor recovery contract:
Figure 4 aPPSS with a concrete ristretto255/SHA-512 2HashDH OPRF,
`GF(2^128)`, a SHA-256-derived 16-byte commitment and 16-byte `S_R`, first
2-of-3 evaluation, and abort-only robustness. D018 additionally requires paired
Yi/aPPSS 2-of-3 and later 3-of-5 profiles under matching system conditions.
The 2-of-3 application/component path is implemented and provisionally accepted
with explicit qualifications under D020. P6.3 adds matched same-host process
deployment profiles for 2-of-3 and 3-of-5; this is not independent human
validation, retained evidence, host independence, or manuscript wording.
D021 authorizes those paired deployments at 2-of-3 and 3-of-5 over five
authorizers with a separate 4-of-5 authorization quorum. P6.4 may claim only
the exact host-separation tier actually demonstrated; administrative
independence still requires genuine independent operators. Its current
endpoint-driven Compose staging runs all five parties under one Docker engine
and is therefore still the same-host tier.

D023 makes a new same-host integrated deployment the principal implementation,
assurance, evaluation, and artifact target. It must exercise Yi and aPPSS at
2-of-3 and 3-of-5 through the same UI-to-service graph, with the separate
4-of-5 authorization quorum and the registered CuePolicies. The local
S3-compatible provider is the reproducible cloud-storage role; AWS and actual
multi-host operation remain supplemental, separately versioned profiles. This
direction does not reinterpret the frozen Compose deployment or establish
independent administration merely through containers on one host.

D024 fixes the source boundary for that system: `prototype_final/` is the sole
active implementation, assurance, evidence, and later artifact workspace for
P8 and beyond. Root implementations remain preserved historical/component
controls and cannot substitute for a result from the D024 workspace. This
organizational isolation changes no protocol, deployment, or evidence
identifier.

D025 approves a separately versioned managed deployment inside that workspace.
The implemented mode-free launcher starts the common service plane, a loopback
Manager UI, and a dedicated internal container controller, but no Client
container. The Manager creates and destroys transient Client UI containers; one
Client UI exposes the existing enrollment and recovery protocols plus an additive
client recovery-package export/import transport. The controller's Docker-socket
access is root-equivalent trusted operator infrastructure. The local provider,
authenticated current-state path, fixed paired holder profiles, distinct 4-of-
5 authorization, and online threshold-party requirement remain. P7.7 is
complete and all twelve managed identifiers are Assigned. The profile is the
P8/P9 system under test; P8.2 aggregate-state and P8.3 managed-flow corpora are
retained, and P8.4 preserves the attempt-control non-claim. P9 results do not
yet exist. D028/P9.1 freezes the exact four-arm managed performance and
resilience methodology. D029/P9.2 assigns its non-collecting schemas,
instrumentation, processor, invalid-attempt rules, controls, and reserved path,
but no retained measurement exists. The owner opened P9.3 on 2026-08-20; its
collector is confined to the exact same-host/local-provider profile and must
pass the clean-source, exploratory, output-safety, and exclusive-publication
gates before any result exists.

The managed control plane uses internal `management` (Manager/controller) and
`client-lifecycle` (Client/controller) networks plus separate `manager-edge`
and `browser-edge` loopback-publication paths. Client process restart actions
clear volatile secret/session state even when the public client ID remains.
Normal stop preserves project state; emergency `integrated-stop --reset-state`
deletes all role/provider volumes and credentials. The bounded 366/365-day CA/
leaf credential lifetime has no in-place renewal and is not a production PKI
claim.

The one-shot bootstrap runs as root with every capability dropped except
exactly `CHOWN` and `DAC_READ_SEARCH`, has no network or Docker socket, and exits
before unprivileged runtime services start. It may create and revalidate only
the approved synthetic credentials, public configuration, empty role roots,
fixtures, and their owner-only files.

## What is inherited

- TPASS construction and security assumptions.
- Password-to-random-secret recovery.
- HKDF and AEAD primitives.
- The current versioned location-person CuePolicy.
- The current native TPASS and backup implementation.

The aPPSS paper, future profile, implementation, and evidence are not inherited
baseline facts and must receive new identifiers and provenance.

## What LOCUS contributes as a system

- the precise semantic-input-to-protocol boundary;
- versioning and failure behavior for structured CuePolicies;
- storage and role separation;
- explicit bootstrap, admission, lifecycle, and information-flow contracts;
- an integrated reference implementation;
- bounded, reproducible evidence and limitations.

## Non-goals without separate approval and evidence

- claiming either Yi TPASS or aPPSS as a new LOCUS construction;
- proving cue memorability, entropy, or usability;
- fuzzy matching or automatic candidate enumeration;
- preventing offline guessing or guaranteeing recovery-secret confidentiality
  after aPPSS reconstruction-threshold compromise;
- hiding resolver use from the resolver;
- global rollback-resistant attempt limiting;
- Byzantine availability;
- forensic secure erasure;
- production security or side-channel resistance;
- independent administration based only on separate local hosts;
- real-user or production-account experimentation.

## Success condition

The project succeeds when an unfamiliar reviewer can start the integrated
environment once, use its loopback Manager UI to create an enrollment Client,
generate a synthetic key, complete enrollment, export the client recovery
package, destroy that Client, and create a distinct clean recovery Client. The
new Client must authenticate the imported package and current configuration,
traverse the deployed admission, discovery, storage-gateway/provider,
applicable resolver, and recovery-party boundaries, recover the exact original
synthetic private key, and verify its public identity. The reviewer must also
reproduce the bounded security and performance evidence from that same managed
integrated system, built only from `prototype_final/`, without external
credentials or hidden developer state. The
manuscript, claim/evidence matrix, technical documentation, generated inputs,
artifact, and rendered PDF must eventually describe that exact evaluated
system consistently, after each manuscript delta receives separate approval.
