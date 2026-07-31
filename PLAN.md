# LOCUS Improvement Project Plan

## Purpose

This is the living integrated implementation, evidence, artifact, and
owner-approved manuscript plan for the portable LOCUS Improvement Project.

The roadmap has no conference-cycle deadline. Work should follow dependency and
evidence order rather than maximizing visible features quickly.

The owner has approved the overall direction: expand LOCUS into a realistic,
complete reference recovery system without changing the current thesis.
Architecture decisions listed in `DECISIONS.md` remain owner gates.

## Status model

- `Complete` — implemented, verified, and documented in this project.
- `In progress` — active work with an identified owner and acceptance gate.
- `Approved` — owner-approved but not started.
- `Proposed` — planned; affected decision gates remain unresolved.
- `Blocked` — cannot progress without a specific external decision or state.
- `Deferred` — intentionally outside the current active sequence.
- `Rejected` — considered and intentionally not pursued.
- `Historical` — inherited context, not active new-project evidence.
- `Retained baseline` — immutable imported evidence valid only for its exact
  frozen profile.

Do not mark a task `Complete` solely because code exists. Its declared tests,
documentation, and evidence gate must pass.

## Global rules

1. Preserve `PROTOCOL-INVARIANTS.md`.
2. Resolve and record owner decisions before affected implementation.
3. Never reinterpret frozen identifiers or retained/historical evidence.
4. Add a new version for every semantic change.
5. Keep UI, provider, and deployment adapters outside the cryptographic core.
6. Write claim/evidence and information-flow requirements before experiments.
7. Use synthetic data and project-controlled disposable services.
8. Before every manuscript edit, present the exact proposed delta and obtain
   explicit owner approval. The owner may approve or skip each change.

---

## P0 — Establish the independent project

### P0.1 Copy this seed to its independent root

Status: `Proposed`

Actions:

- Copy the complete `improvement project` directory to its intended location.
- Confirm `AGENTS.md`, `PLAN.md`, root configs, source directories, tests,
  vectors, active docs, manuscript, review PDF, retained evidence, artifact
  material, and licenses are at the copied repository root.
- Do not copy the upstream `.git`, caches, targets, environments, or credentials.

Acceptance:

- The copied root is not nested inside the original Git repository.
- Required files in `PORTABILITY-CHECKLIST.md` are present.

### P0.2 Initialize source control and freeze the import

Status: `Proposed`

Actions:

- Initialize a new Git repository.
- Review the Git identity and remote before any push.
- Stage the complete portable seed and verify it against
  `PORTABLE-CONTENTS.json`.
- Inspect ignored and untracked files.
- Confirm every frozen raw v1/v2 record is staged despite the default rule that
  ignores future unretained raw JSON.
- Create the initial import commit.
- Record the new commit in `SOURCE-PROVENANCE.md`.

Acceptance:

- The new repository has its own root `.git`.
- No upstream history, remote, local absolute path, credential, cache, binary
  extension, or disposable build product is tracked.
- The manuscript, review PDF, retained v1/v2 evidence, generated inputs, and
  sealed v1 artifact are tracked at their documented paths.

### P0.3 Run the clean baseline gate

Status: `Proposed`

Actions:

```console
uv sync --frozen
uv run --frozen python tasks.py check
```

- Run on the primary development platform.
- Run the same gate on clean Linux and Windows CI.
- Record actual test counts and any compatibility issues.
- Verify the retained v2 processor and generated-paper-input manifests.
- Build the manuscript using `paper/README.md`, render it, and compare the
  result with the imported review snapshot before accepting any paper delta.

Acceptance:

- Python and Rust quality gates pass.
- The native extension builds from source.
- Default tests do not require external accounts or real data.
- Any inherited tooling path retained only for compatibility is documented.

### P0.4 Reconcile manuscript/evidence/artifact tooling

Status: `Proposed`

Actions:

- Keep the exact retained v2 verification and manuscript-input regeneration
  path working.
- Rename paper-specific commands and paths only through an explicit versioned
  migration.
- Add generated-fixture tests before removing compatibility paths.
- Ensure new artifact packaging uses a new allowlist and package version.
- Keep repository scope distinct from the smaller anonymous-artifact allowlist.

Acceptance:

- `paper/main.tex` builds from the retained generated inputs.
- Retained v2 verification and regeneration remain byte-identical.
- New profiles write only to new versioned evidence/generated paths.
- The new artifact deliberately includes or excludes paper/evidence material
  through an explicit licensed, privacy-safe allowlist.

---

## P1 — Freeze active architecture contracts

### P1.1 Approve the initial decision set

Status: `Proposed`

Required decisions:

- Approved: D001, D003, D005, D014, and D015 establish account-scoped bundle
  discovery, descriptor trust, three atomic CuePolicies, the immutable bundle
  layout, and an application-operated S3 namespace with an optional AWS S3
  profile. D015 supersedes the personal-cloud-account and Google Drive choices
  in D002 and D006.
- Pending: D004 and D007--D010 cover admission, deployed profiles,
  independence wording, attempt role, and UI platform.

Acceptance:

- Approved decision records include trust, privacy, version, compatibility, and
  evidence consequences.

### P1.2 Create typed system interfaces

Status: `Proposed`

Define interfaces for:

- `CuePolicy`;
- `Resolver`;
- `BackupObjectStore` compatibility contract;
- `DescriptorStore`;
- `ApplicationStorageGateway` and storage-capability verifier;
- `PartyDirectory`;
- `AdmissionVerifier`;
- enrollment client state machine;
- recovery client state machine;
- lifecycle manager.

Rules:

- Interface definitions must not silently alter evaluated v1 bytes.
- TPASS-holder and authorizer roles must be distinct types.
- Strict decoders reject unknown, duplicate, oversized, and unsupported input.

Acceptance:

- Interface tests compile/run without changing current native recovery results.
- Existing cue and TPASS vectors remain byte-identical.

### P1.3 Freeze a new profile namespace

Status: `Proposed`

Actions:

- Assign identifiers only after schemas are approved.
- Register policy, descriptor, backup, admission, deployment, trace, result, and
  artifact versions in `VERSION-REGISTRY.md`.
- Define compatibility and upgrade rules.

Acceptance:

- No new identifier collides with or reinterprets a frozen upstream identifier.

### P1.4 Create security and information-flow matrices

Status: `Proposed`

Required phases:

- enrollment;
- persistent-state disposal;
- bootstrap;
- recovery;
- successor publication;
- party replacement.

Required views:

- cloud;
- descriptor store;
- application storage gateway;
- resolver;
- each below-threshold party coalition used by an evaluated profile;
- matching combined state;
- enrollment client after disposal;
- clean client before and after cue entry;
- identity/admission provider;
- network-role metadata.

Acceptance:

- Every active claim has an asset, adversary, assumptions, boundary, positive
  control, expected observation, and interpretation limit.

---

## P2 — RecoveryDescriptor and bootstrap

### P2.1 Specify `RecoveryDescriptor`

Status: `Approved`

Specify:

- canonical schema and maximum size;
- version;
- backup identifier, epoch, logical immutable backup reference, and digest;
- CuePolicy identifier and public parameters;
- TPASS public parameters and threshold;
- TPASS-holder membership;
- separate authorizer membership and quorum;
- endpoint identities or directory binding;
- admission profile;
- lifecycle predecessor/configuration digest;
- issuer, validity, and signature.

Specify the optional per-epoch recovery bundle alongside the descriptor:

- an immutable bounded ZIP containing exactly `backup.json`,
  `descriptor.json`, and `manifest.json`;
- a descriptor digest over the canonical backup member rather than the ZIP
  that contains the descriptor;
- a manifest binding the exact backup/descriptor member names, formats, sizes,
  and digests without attempting to digest itself;
- an authenticated mutable current pointer outside the ZIP that identifies the
  provider-assigned locator and exact digest of the active immutable bundle,
  plus the descriptor digest; and
- strict rejection of duplicate, unknown, nested, encrypted, unsafe-path,
  oversized, over-compressed, or unsupported members.

The backup object, descriptor, manifest, and current pointer remain distinct
logical contracts even when one provider stores them together.

Explicitly prohibit cue hints, cue hashes, `Z_M`, `p_M`, password-derived
authenticators, and a self-contained trust root.

Acceptance:

- Canonical vectors exist.
- Duplicate, extra, missing, oversized, and unsupported fields fail.
- Bundle vectors cover exact membership, bounded decompression, member digest
  binding, and the absence of self-referential digest computation.
- Disclosure analysis finds no new offline predicate within the declared model.

### P2.2 Specify discovery and trust bootstrap

Status: `Approved`

Approved profile:

- account-scoped discovery of an authenticated current pointer and immutable
  recovery bundle;
- app-pinned issuer or operator root;
- optional exported recovery receipt;
- party-signed current epoch/digest summaries;
- explicit behavior when cloud and parties disagree.

The user authenticates through the eventual owner-approved D004
admission/identity profile
and presents a short-lived proof-key-bound capability to the application
storage gateway. The gateway scopes exact operations to the
application-operated S3 namespace. A personal AWS or other storage-provider
account is not required, and the client receives no provider credential.
Admission, capability issuance, and storage availability are explicit recovery
prerequisites, not cues or cryptographic factors. The reproducible local
profile requires no external account.

Analyze:

- enumeration and linkability;
- account loss;
- endpoint/key rotation;
- descriptor substitution;
- stale/freeze/rollback;
- malicious cloud;
- compromised issuer;
- clean-client trust-root update.

Acceptance:

- A clean client can authenticate every endpoint and current-state assertion
  without trusting keys introduced only by the untrusted descriptor.

### P2.3 Implement `DescriptorStore`

Status: `Approved`

Required operations:

- immutable descriptor publication;
- exact retrieval;
- authenticated current pointer;
- compare-and-swap successor update;
- explicit not-found, conflict, stale, unavailable, corrupt, and oversized
  results.

Implement a deterministic filesystem adapter and a same-host service adapter
before an external provider. Add a `RecoveryBundleStore` convenience layer only
after the separate backup, descriptor, and current-pointer contracts pass their
shared tests. Extend the common S3 adapter with create-only bundle writes,
ETag-bound current-pointer compare-and-swap, exact no-list retrieval, and
explicit failure mapping. Place an application storage gateway above that
adapter to enforce the short-lived D004/D015 capability. AWS S3 is the optional
external profile; it is not required by CI or reviewer workflows.

Acceptance:

- Concurrent publication, stale CAS, substitution, and exact retry tests pass.
- Backup-object immutability and current-pointer mutation remain separate.
- Bundle upload/download preserves exact canonical member bytes and never
  treats provider access control as descriptor authenticity.

### P2.4 Implement descriptor security scenarios

Status: `Approved`

Scenarios:

- wrong recovery handle;
- wrong account scope;
- altered signature;
- wrong issuer;
- stale epoch;
- cross-user substitution;
- cross-policy substitution;
- cross-membership mix;
- descriptor/backup digest mismatch;
- descriptor/party current-state mismatch;
- altered, duplicate, unexpected, unsafe-path, oversized, or unsupported ZIP
  members;
- stale bundle and current-pointer rollback;
- positive controls for every detector.

Acceptance:

- Results use a new aggregate-only descriptor-security schema.

---

## P3 — Enrollment and admission

### P3.1 Refactor enrollment into a stable state machine

Status: `Proposed`

States:

```text
key import/generation
-> policy processing
-> TPASS setup
-> key wrapping
-> backup publication
-> party provisioning
-> descriptor publication
-> receipt
-> disposal
```

Acceptance:

- Unsafe transitions fail closed.
- Safe retries are idempotent.
- Secret state is never serialized for retry.

### P3.2 Implement authenticated enrollment transport

Status: `Proposed`

Replace paper-facing direct volume provisioning with:

- TLS 1.3;
- exact service identity validation;
- authenticated enrollment authorization;
- canonical bounded messages;
- recipient-bound native state;
- request idempotency;
- generic external failures;
- privacy-safe local audit.

Acceptance:

- Parties run in distinct processes without shared secret volumes.
- Wrong recipient, endpoint, identity, body, route, and idempotency reuse fail.
- No coordinator persists all TPASS states.

### P3.3 Specify the admission contract

Status: `Proposed`

Bind:

- subject;
- operation;
- backup identifier;
- epoch;
- audience;
- client proof key;
- nonce;
- issuance and expiry;
- issuer and authorization profile.

For D015 storage operations, also bind the exact pseudonymous object prefix,
storage operation, and storage-gateway audience. The capability authorizes no
bucket listing and carries no provider credential.

Keep admission independent from CuePolicy/TPASS correctness.

Acceptance:

- Threat model covers replay, stolen bearer token, malicious client,
  cross-account use, false-lockout attempts, identity-provider unavailability,
  and privacy leakage.

### P3.4 Implement local admission

Status: `Proposed`

Start with a deterministic local issuer/test double. Then implement the approved
OIDC/PKCE/DPoP profile.

Acceptance:

- Every authorizer validates independently.
- The application storage gateway validates its separate exact-operation
  capability independently before contacting S3.
- Replay, wrong key, wrong subject, wrong audience, wrong operation, wrong
  backup, wrong epoch, wrong prefix, expired token, and nonce reuse fail.
- Reviewer workflows need no external identity provider.

---

## P4 — Clean-client recovery and lifecycle

### P4.1 Refactor recovery into a stable state machine

Status: `Proposed`

States:

```text
bootstrap
-> descriptor verification
-> party current-state agreement
-> exact backup retrieval
-> policy processing
-> threshold selection
-> authorization
-> TPASS recovery
-> AEAD decryption
-> key identity verification
-> successor action
```

Acceptance:

- Wrong input and malformed remote state expose only the approved error
  boundary.
- The client does not disclose final TPASS/AEAD outcome to parties.

### P4.2 Implement Client A/Client B isolation

Status: `Proposed`

Procedure:

1. Client A generates/imports a synthetic private key.
2. Record its expected public fingerprint outside LOCUS as a test oracle.
3. Enroll and publish backup, party state, and descriptor.
4. Terminate Client A.
5. Remove or make Client A persistent state inaccessible.
6. Audit the post-enrollment state surface.
7. Start Client B with only approved bootstrap inputs.
8. Recover through a threshold subset.
9. Verify exact private-key bytes and public fingerprint.

Acceptance:

- Client B has no Client A mounts, environment, process state, or credentials
  beyond the approved bootstrap model.
- A deliberate inherited-state positive control fails the isolation gate.

### P4.3 Complete post-recovery successor publication

Status: `Proposed`

Order:

1. preserve the recovered original protected key;
2. prepare new party state;
3. publish immutable successor backup;
4. publish authenticated successor descriptor/current pointer;
5. verify readiness and reachability;
6. activate successor;
7. retire predecessor;
8. optionally rotate protected key after explicit user choice.

Acceptance:

- Crash tests at every boundary leave at least one authorized epoch recoverable.
- Exact retries complete without double activation or stale reauthorization.

### P4.4 General party replacement

Status: `Deferred`

Begin only after P4.3 is complete and D011 is approved.

Acceptance:

- Old-quorum authorization, new-recipient provisioning, new-threshold readiness,
  descriptor update, activation, and retirement are all bound to one successor
  configuration.

---

## P5 — CuePolicy and resolver generality

### P5.1 Wrap the existing policy without semantic change

Status: `Approved`

Acceptance:

- All v1 canonical bytes and errors are unchanged.
- TPASS input and backup vectors remain unchanged.
- Existing resolver-drift vectors pass through the new interface.

### P5.2 Design three atomic policies

Status: `Approved`

Requirements:

- a quantized-coordinate-set policy accepting exactly three distinct WGS84
  coordinate pairs with the existing half-even `10^-4`-degree quantization;
- a canonical-phone-set policy accepting exactly three distinct strict E.164
  values without local-format inference or extensions;
- a canonical-email-set policy accepting exactly three distinct values under a
  newly frozen constrained email grammar;
- direct-input profiles for all three policies are resolver-free;
- no stored selection hints or verifier;
- immutable identifier and public rule metadata;
- exact validation, normalization, ordering, duplicate, ambiguity, and failure
  behavior;
- domain separation from all other policies.

Shared coordinate, phone, and email canonicalization helpers may be reused, but
each policy requires its own top-level encoding, identifier, domain-separation
label, vectors, and error contract. The existing
`LOCUS-location-person-set-v1` policy remains an unchanged fourth policy and
the resolver-backed reference example.

Acceptance:

- D005 records the approved privacy and trust implications.
- The public policy identifier's disclosure of the input category is explicit.
- No policy is interpreted as evidence of cue entropy, memorability, or
  usability.

### P5.3 Build a shared conformance corpus

Status: `Approved`

Cover:

- Unicode and locale behavior;
- whitespace, case, punctuation, and length;
- ordering and duplicate rejection;
- missing and ambiguous data;
- policy/version mismatch;
- equivalent representation determinism;
- provider/resolver drift;
- cross-policy confusion;
- clean Linux and Windows execution;
- one independent vector consumer.

Acceptance:

- Four policies share one interface and unchanged TPASS internals.
- Frozen v1 vectors remain byte-identical after extracting shared
  canonicalization helpers.
- No test is interpreted as memorability, entropy, or usability evidence.

### P5.4 Formalize resolver adapters

Status: `Approved`

Implement:

- deterministic local fixture;
- explicit `NoResolver` adapter for direct coordinate, phone, and email input;
- an external location-provider adapter only after separate execution approval;
- explicit provider/version metadata;
- bounded query/results;
- ambiguity/drift outcomes;
- privacy-safe observation.

Acceptance:

- Policies declare exactly what the resolver learns.
- No resolver automatically enumerates cue alternatives through TPASS.

---

## P6 — Storage providers and deployment profiles

### P6.1 Extend storage conformance

Status: `Proposed`

Every backup/descriptor adapter must cover:

- TLS for nonlocal use;
- narrow credentials;
- immutable backup publication;
- descriptor CAS;
- bounded reads;
- exact digest and canonical validation;
- no unnecessary list operation;
- explicit unavailable/not-found/conflict/corrupt/stale outcomes;
- credential/output scans.

Acceptance:

- Deterministic filesystem and S3-compatible adapters pass one common suite.

### P6.2 Add one distinct provider adapter

Status: `Approved`

Provider: AWS S3. Its role is a supplemental application-operated
account-scoped compatibility profile, not a mandatory reviewer path or new
security claim. It implements the same logical immutable-backup,
immutable-descriptor, mutable-current-pointer, and optional recovery-bundle
contracts as the local S3-compatible reference adapter.

The client uses a short-lived,
subject/backup/prefix/operation/client-proof-key/nonce/expiry-bound capability
issued through the D004 admission flow. The application storage gateway
validates that capability and performs the exact S3 operation. The client
receives no AWS access key and needs no personal AWS account. Direct S3
pre-signed bearer URLs are outside this approved profile.

Acceptance:

- Uses a disposable research account and synthetic keys only.
- No credentials or personal account identifiers are retained.
- Bundle creation is conditional and non-overwriting; current-pointer updates
  require the previously authenticated ETag/version binding.
- Normal recovery requires no bucket listing permission.
- Local emulation remains sufficient for reproducibility.

### P6.3 Generalize threshold configuration

Status: `Proposed`

Support:

- existing deployed 2-of-3;
- new deployed 3-of-5;
- distinct authorization quorum for each profile;
- exact consistent threshold subset selection;
- satisfiable and unsatisfiable availability cases.

Acceptance:

- End-to-end deployment tests exist for every claimed profile.
- Local scaffold tests alone are not treated as deployment evidence.

### P6.4 Move parties to separate hosts

Status: `Proposed`

Tiers:

1. separate local VMs;
2. separate network hosts under one administrator;
3. independently administered parties, only with actual independent operators.

Validate:

- unique identities and certificates;
- disjoint storage;
- no shared secret mounts;
- firewall and route boundaries;
- endpoint discovery;
- restart/catch-up;
- topology before and after startup.

Acceptance:

- Claims use the exact tier demonstrated.

---

## P7 — User interface

### P7.1 Freeze client APIs before UI implementation

Status: `Proposed`

Acceptance:

- Enrollment and recovery complete through CLI/API tests.
- No UI framework contains a second canonicalizer or protocol implementation.

### P7.2 Implement enrollment UI

Status: `Proposed`

Screens:

- generate/import synthetic protected key;
- show public fingerprint;
- choose approved policy;
- enter and resolve structured cues;
- validate and preview normalized selections;
- select an authenticated preconfigured party profile;
- enroll;
- export recovery receipt;
- show redacted state placement;
- dispose of enrollment-client state.

Acceptance:

- No raw cue or secret reaches logs, browser persistence, analytics, telemetry,
  clipboard, crash output, or retained screenshot.

### P7.3 Implement recovery UI

Status: `Proposed`

Screens:

- clean-client bootstrap;
- LOCUS admission/identity authentication and short-lived storage capability;
- descriptor retrieval and validation;
- enrolled policy display;
- cue entry and validation;
- generic online recovery progress;
- recovered public-fingerprint verification;
- successor enrollment and optional key rotation.

Acceptance:

- The UI cannot silently change policy, epoch, party membership, or endpoint
  trust.
- Errors match the approved information boundary.

### P7.4 Implement researcher state inspector

Status: `Proposed`

May display:

- role names;
- versions;
- public identifiers;
- safe digests;
- message categories;
- byte/storage counts;
- status and failure categories.

Must not display:

- raw/canonical cues;
- TPASS password, shares, group secret, wrapping key;
- credentials/tokens;
- private key bytes.

Acceptance:

- Displayed state matches recursive persisted-state audits.

---

## P8 — Security, reliability, and information-flow assurance

### P8.1 Add decoder and state-machine assurance

Status: `Proposed`

Add:

- bounded property testing;
- malformed-input fuzzing;
- duplicate/unknown/member-order tests;
- cross-session and cross-epoch messages;
- concurrency scheduling;
- crash/restart at every durable transition;
- idempotency and replay;
- path and symlink containment;
- prohibited-output scans.

Acceptance:

- Every external decoder and mutating state transition has negative coverage.

### P8.2 Add state-boundary evidence

Status: `Proposed`

Required surfaces:

- cloud plus descriptor;
- application storage-gateway persistent state and safe synthetic provider
  authority surface;
- each relevant below-threshold party coalition;
- matching combined state;
- post-enrollment Client A;
- pre-cue Client B;
- resolver-visible categories;
- identity/admission provider metadata;
- lifecycle predecessor/successor states.

Acceptance:

- Each scenario has a positive control and aggregate-only report.

### P8.3 Add privacy-safe network-flow evidence

Status: `Proposed`

Prefer structured instrumentation that records:

- sender and receiver role;
- fixed message category;
- byte count;
- whether a prohibited category was detected;
- whether an unexpected role/contact occurred.

Packet captures are not retained. Any temporary inspection requires a new
approved trace policy and synthetic local traffic.

Acceptance:

- Reproducible aggregate evidence supports role-visibility statements without
  retaining payloads.

### P8.4 Preserve attempt control as a boundary

Status: `Proposed`

- Keep the rollback counterexample reproducible.
- Keep signed local auditing isolated from the TPASS correctness claim.
- Do not block core recovery on an unproven global bound.

Acceptance:

- Documentation and UI never describe the quorum-only ledger as globally
  rollback-resistant.

---

## P9 — Performance and resilience evaluation

### P9.1 Define revised methodology before collection

Status: `Proposed`

Measure:

- policy processing;
- resolver;
- TPASS setup;
- backup encryption/upload;
- party provisioning;
- descriptor publication/retrieval;
- clean-client bootstrap;
- successful and wrong-input recovery;
- one-party unavailable;
- fewer-than-threshold failure;
- successor transition;
- role bytes and storage;
- concurrency/throughput;
- restart effects;
- cross-host/WAN latency where authorized.

Acceptance:

- Frozen scenarios, sample sizes, randomization, warm-up, exclusion rules,
  topology, statistics, provenance, and no-outlier policy are documented before
  retained collection.

### P9.2 Implement new evidence schemas

Status: `Proposed`

Candidate result families:

- CuePolicy conformance;
- clean-client recovery;
- client-state disposal audit;
- descriptor security;
- information flow;
- distributed performance;
- multi-role state audit.

Acceptance:

- Schemas bind exact policy, descriptor, backup, profile, threshold, party
  identities, topology, backend, scenario, positive control, output scan, and
  limitations.

### P9.3 Collect same-host revised baseline

Status: `Proposed`

Acceptance:

- New versioned result paths.
- No v2 overwrite or mixed-profile processing.
- Complete raw-to-processed-to-derived hash closure.

### P9.4 Collect multi-host and provider profiles

Status: `Proposed`

Acceptance:

- Exact topology and administration scope disclosed.
- All credentials disposable and excluded.
- Claims limited to exact hosts, thresholds, providers, and workloads.

---

## P10 — Review, artifact, and external claim readiness

### P10.1 Independent cryptographic review

Status: `Proposed`

Review:

- mapping from Yi et al. to the Ristretto instantiation;
- setup and generator derivation;
- canonical wire formats;
- proof and aggregation validation;
- Python boundary;
- domain separation and malformed-state behavior.

Acceptance:

- Findings are tracked and resolved.
- The project uses "reviewed" or "audited" only to the exact degree performed.

### P10.2 Independent systems review

Status: `Proposed`

Review:

- descriptor trust and rollback;
- admission;
- clean-client boundary;
- lifecycle;
- party topology;
- privacy and logging;
- UI persistence;
- evidence methodology.

### P10.3 Build the new portable artifact

Status: `Proposed`

The artifact should reproduce:

- quality/native gate;
- all policy vectors;
- descriptor/bootstrap tests;
- Client A destruction and Client B recovery;
- required state-boundary scenarios;
- same-host reference deployment;
- feasible multi-host workflow;
- deterministic processing and derived outputs.

Acceptance:

- Deterministic archive with new version and manifest.
- Extracted archive passes without `.git` or developer-local state.
- Clean Linux and Windows reproduction passes.
- One unfamiliar reviewer completes the workflow.

### P10.4 Close the active claim/evidence matrix

Status: `Proposed`

Acceptance:

- Every promoted claim identifies exact profile, assumptions, adversary,
  evidence, and limitation.
- Global rate limiting, memorability, entropy, production readiness, independent
  administration, and audit remain non-claims unless separately established.

### P10.5 Propose manuscript deltas

Status: `Deferred`

After the relevant evidence closes, present each proposed title, abstract,
section, claim, limitation, table, figure, and reference delta to the owner.
Record its exact evidence basis and whether the owner approved or skipped it.
Do not edit `paper/` during this task.

### P10.6 Apply only approved manuscript deltas

Status: `Deferred`

For each approved change set:

- edit only the authorized manuscript content;
- synchronize the claim matrix, threat model, limitations, related work,
  generated inputs, and artifact instructions;
- rebuild and visually inspect the PDF; and
- record the applied commit, PDF digest, page status, and owner decision.

Skipped or unapproved deltas remain unchanged.

---

## Recommended first execution slice

After P0 and owner decisions D001--D004:

1. P1.2 — typed interfaces without semantic change;
2. P2.1 — RecoveryDescriptor specification and vectors;
3. P2.2 — bootstrap/trust model;
4. P2.3 — DescriptorStore;
5. P3.1 — enrollment state machine;
6. P3.2 — authenticated enrollment transport;
7. P4.1 — recovery state machine;
8. P4.2 — isolated Client A/Client B exact-key recovery;
9. P2.4 — descriptor adversarial regressions;
10. P8.2 — state-boundary evidence.

Do not begin the graphical UI, real cloud provider, or general party replacement
before this slice is complete.
