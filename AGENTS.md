# AGENTS.md

## Authority and scope

This is the authoritative project-level instruction file for the LOCUS
Improvement Project. It applies to the entire repository unless a more specific
`AGENTS.md` is added in a subdirectory.

`AGENT.md` is a requested entry point only. This plural `AGENTS.md` controls
Codex work.

Read `PROJECT-CHARTER.md`, `BASELINE.md`, `PLAN.md`, `DECISIONS.md`,
`PROTOCOL-INVARIANTS.md`, `VERSION-REGISTRY.md`, `EVIDENCE-POLICY.md`, and
`MANUSCRIPT-BOUNDARY.md` before making architectural or evidence-facing changes.

## Project identity

LOCUS is a research system for distributed private-key recovery. A client
converts structured recovery input into deterministic bytes through a versioned
CuePolicy, derives suite-bound password input locally, stores only an encrypted
private-key backup in a cloud-object role, and distributes native threshold
state across separately identified recovery parties. The current implementation
preserves the frozen Yi TPASS suite and adds the separately versioned aPPSS
suite. D018 keeps both independently selectable. D020 permits P6 work after a
non-independent internal mapping assessment while retaining mandatory
independent human validation before manuscript reliance or a final reviewed
release.
D021 fixes the paired P6 deployment direction: Yi and aPPSS each receive
matched 2-of-3 and 3-of-5 recovery profiles over five authorizers with a
separately typed 4-of-5 authorization quorum. Host-separation claims must use
the exact demonstrated tier; independent administration requires actual
independent operators.
D023 makes a new same-host integrated reference system the primary target for
P8/P9 and the later artifact: the loopback UI/client gateway must traverse the
authenticated admission, discovery, storage-gateway/provider, resolver, and
five-party service boundaries. The frozen Compose deployment, P6 process
profiles, and P7 same-process UI/API remain historical or component controls
and cannot substitute for integrated-system evidence.
D024 isolates that system under `prototype_final/`. All P8 and later
implementation, tests, evidence collection, and artifact work must execute from
that self-contained workspace through its `integrated-*` command surface.
Existing root `prototype/`, `deploy/`, native crates, and `tasks.py` remain
historical/component controls and migration provenance; do not extend them for
new P8+ behavior or use them as the primary system under test.
D025 approves a newly versioned Manager-controlled deployment in that same
workspace. P7.7 is complete: it replaces CLI-selected enrollment/recovery
clients with a loopback Manager UI, a narrowly scoped internal Docker
controller, dynamically created Client UI containers, and authenticated client
recovery-package export/import. The twelve D025 managed identifiers are
Assigned, not Frozen. This implementation milestone does not authorize retained
P8/P9 collection or manuscript wording.

This repository is the integrated continuation of LOCUS. It maintains the
implementation, active technical documentation, manuscript source and rendered
review snapshot, retained versioned evidence, generated manuscript inputs, and
artifact tooling.

Imported material remains bound to its original identifiers and provenance. No
implementation, evidence, or planning change automatically authorizes a
manuscript change. Before every manuscript edit, describe the exact proposed
delta and obtain the owner's explicit approval; the owner may approve or skip
each change.

## Frozen thesis

Unless the owner explicitly approves a thesis change, all development must
preserve this statement:

> LOCUS composes deterministic structured-input processing with TPASS and
> separated encrypted storage so that cloud-only, below-threshold party, and
> matching cloud-plus-below-threshold persistent states do not expose a local
> offline cue-testing predicate, while candidate evaluation requires online
> threshold-party participation under explicit assumptions.

Consequences:

- TPASS security is inherited and is not a new LOCUS construction.
- The basic TPASS-to-random-secret and encrypted-backup composition is not
  claimed as novel by itself.
- CuePolicy and system interfaces may be strengthened without becoming human
  memorability or usability claims.
- Admission, discovery, lifecycle, cloud providers, and UI are system
  completeness layers. They do not alter the offline-oracle argument unless
  they add a prohibited verifier or new secret-bearing state.
- Global rollback-resistant attempt control is not part of the core thesis.

### Owner-approved selectable-suite direction

D018 supersedes D016's sole-aPPSS active-profile cutover while preserving its
suite-separation requirements. Until P5A's selectable-suite acceptance gate
passes, the frozen TPASS thesis and protected path below remain the implemented
and paper boundary. Selectable-suite work must:

- use new domains, formats, epochs, profiles, schemas, evidence paths, and
  identifiers;
- preserve the frozen Yi implementation, vector, recovery behavior, and
  retained v2 evidence without reinterpretation;
- keep protected-key generation/import, key identity, HKDF-SHA-256,
  AES-256-GCM, storage, bootstrap, admission, lifecycle, and common client APIs
  suite-neutral and unchanged in meaning;
- use the aPPSS output directly as the high-entropy LOCUS recovery secret that
  feeds HKDF, without retaining an independently threshold-shared unmasked
  recovery secret;
- bind one and only one explicitly selected recovery suite to each epoch and
  prohibit automatic fallback, cross-suite mixing, and in-place state
  conversion; an explicit suite change creates a fresh successor epoch;
- implement and evaluate both suites first at `k=2,n=3` and later at
  `k=3,n=5` under paired policy, key, authorization, storage, topology,
  failure-schedule, and measurement conditions;
- treat fewer-than-reconstruction-threshold no-offline-predicate behavior,
  reconstruction-threshold Yi direct reconstruction, and
  reconstruction-threshold aPPSS offline-dictionary behavior as separate
  claims; and
- preserve the approved D017/P1.2 OPRF, field, hash, robustness, corruption,
  and theorem profile in `docs/APPSS-PROFILE.md`; assign final wire identifiers,
  schemas, and vectors together at P5A.1 before cryptographic implementation.

D020 does not satisfy D019's independence requirement. The internal assessment
may close P5A implementation chronology only. Never describe it as an
independent review, audit, proof, or final cryptographic validation. A qualified
human reviewer must confirm or change every provisional mapping classification
before manuscript reliance, a final reviewed release, or submission.

The aPPSS and Yi constructions are inherited cryptographic work, not LOCUS
novelty. D019 requires an independent, claim-focused review of both
paper-to-specification-to-code mappings and the common LOCUS composition. It
is not a full production cryptographic audit: documented engineering choices
may be accepted when they preserve claim-critical semantics. An unresolved
claim-critical deviation requires correction and re-review or removal of the
dependent inherited result and LOCUS claim. D018/D019 do not authorize
M-APPPSS-001, M-SELECTABLE-SUITES-001, or any other manuscript wording.

## Protocol invariants

The protected path remains:

```text
structured input M
  -> CuePolicy_v(M) = Z_M or failure
  -> domain-separated TPASS password p_M
  -> TPASS.Setup / TPASS.Recover
  -> recovered group secret S_R
  -> HKDF-SHA-256 wrapping key K_wrap
  -> AES-256-GCM protection of the private key
```

Do not replace this with an independently sampled symmetric recovery key unless
the owner approves a protocol and thesis change.

Raw cues, resolver records, canonical selected descriptors, `Z_M`, `p_M`,
`S_R`, `K_wrap`, the plaintext protected key, and a cue-testing verifier must
not be stored by the cloud or recovery parties.

Only the active client may transiently handle the complete secret path.

## Frozen identifiers and historical evidence

Existing protocol and evidence identifiers are immutable, including:

- `LOCUS-location-person-set-v1`;
- `LOCUS-location-person-pair-v1`;
- `LOCUS-reference-backup-v4`;
- `LOCUS-compose-deployment-v2`;
- `LOCUS-TPASS-YI-ZK-RISTRETTO255-v1`;
- the retained v2 attack and performance corpus.

Never rename, reinterpret, overwrite, or silently migrate them. Semantic changes
require new identifiers, formats, epochs, schemas, profiles, and evidence paths.

The retained v2 results are baseline evidence only for the exact frozen profile
and provenance they record. They do not support a changed implementation,
policy, descriptor, admission layer, topology, provider, or lifecycle.

## Current inherited baseline

The portable source was extracted from upstream commit
`771fccd14d918b697bfb48fd24a0202c52c7f7ac`.

Inherited capabilities include:

- deterministic encoding and cue-policy processing;
- one concrete exactly-three-pair location-person policy;
- native Rust/Ristretto255 TPASS with canonical wire formats;
- Python bindings and orchestration;
- HKDF-SHA-256 and AES-256-GCM backup protection;
- immutable filesystem and S3-compatible object stores;
- five authenticated authorizer processes, of which parties 1--3 hold TPASS
  state;
- deployed TPASS 2-of-3 and authorization 4-of-5;
- durable local SQLite state, idempotency, signed attempt records, and bounded
  negative-result exploration;
- authenticated recovery and lifecycle service routes;
- same-membership successor preparation, activation, retirement, restart
  reconstruction, and successor recovery;
- same-host Compose deployment, snapshot-boundary tooling, deterministic
  evidence processing, and output-safety controls.

The inherited baseline does not provide:

- a true clean-client bootstrap and discovery flow;
- an authenticated `RecoveryDescriptor`;
- public-client admission;
- authenticated enrollment transport used by the evaluated deployment;
- multiple CuePolicy implementations behind one registry;
- a UI;
- a real-provider reference result;
- a genuine multi-host or independently administered deployment;
- general party replacement;
- rollback-resistant global attempt control;
- complete secure-erasure, concurrency, scalability, human-memory, usability,
  or production-security evidence.

See `BASELINE.md` for details.

## Authorized defensive security scope

This repository is owner-controlled defensive research. Work may use:

- repository-controlled source and generated build/test artifacts;
- generated private keys, generated credentials, fictional cues, and synthetic
  identities;
- test doubles and pre-generated synthetic role state;
- loopback services and exact disposable containers, networks, volumes, or
  local VMs created for the current test;
- bounded malformed-input, property, fuzz, replay, rollback, concurrency,
  crash, availability, and snapshot testing;
- privacy-safe aggregate observations.

Assumed compromise must be represented by supplied synthetic state, a read-only
snapshot, or an instrumented local role. Do not implement a mechanism for
compromising a real account, cloud, resolver, party, client, identity provider,
or host.

Do not:

- target, enumerate, scan, probe, exploit, or connect adversarial tooling to
  third-party or production systems;
- use real private keys, recovery material, credentials, personal data,
  production logs, or production traffic;
- perform credential theft, phishing, credential stuffing, persistence,
  stealth, evasion, exfiltration, destructive action, or denial of service;
- turn bounded LOCUS regression scenarios into configurable offensive tools;
- weaken isolation, authentication, authorization, output safety, or cleanup to
  make a scenario pass;
- print, retain, or commit secret-bearing snapshots, credentials, candidate
  values, private material, packet captures, or prohibited traces.

External cloud, identity-provider, or independently operated party testing
requires a separately approved, disposable research profile with synthetic
data. Normal reviewer workflows must not require external credentials.

## Architecture rules

### CuePolicy

- First wrap the existing v1 policy byte-for-byte behind an interface.
- Policies declare accepted input, cardinality, resolver behavior,
  canonicalization, ambiguity, duplicate, and version rules.
- No policy may emit hints, fuzzy alternatives, multi-candidate retries, or a
  persisted offline verifier.
- Additional policies demonstrate interface generality only.

### RecoveryDescriptor

- Treat descriptor design as a trust-model task, not only a schema task.
- The descriptor may contain public configuration, immutable backup
  references, policy versions, thresholds, memberships, endpoint identities,
  admission profile, and lifecycle bindings.
- It must not contain raw cues, selected-cue hashes, candidate hints,
  password-derived authenticators, or a self-authenticating trust root.
- A clean client must authenticate the descriptor through a root that does not
  originate solely inside the descriptor.
- Signed version numbers alone do not establish rollback resistance for a
  client with no trusted current state.

### Party roles

- Model every remote process as an authorizer and optionally a TPASS holder.
- Successor interfaces may model it as a recovery-suite holder, with TPASS and
  aPPSS as disjoint suite-specific state types.
- Keep recovery-suite threshold and authorization quorum distinct in types,
  schemas, UI, logs, and evidence.
- Separate hosts do not prove independent administration.

### Admission

- Keep admission independent of CuePolicy and recovery-suite correctness.
- Bind authorization to subject, backup identifier, epoch, operation, audience,
  client proof key, nonce, and expiry.
- A cloud or identity account used for discovery is an explicit prerequisite,
  not an invisible LOCUS security factor.

### Storage

- Keep immutable backup-object storage separate from mutable descriptor/current
  pointer storage.
- Every adapter must enforce bounded canonical decoding, exact digest binding,
  TLS for nonlocal use, narrow credentials, and explicit failure categories.
- Local emulation remains the default reproducible artifact path.

### Client and UI

- Enrollment and recovery state machines live behind stable APIs.
- The UI is a thin caller and must not duplicate protocol or canonicalization
  logic.
- Disable telemetry and prohibit secret-bearing logs, persistence, history,
  clipboard use, retained screenshots, and crash output. D025 alone permits an
  explicitly requested synthetic private key to appear transiently inside the
  active Client UI/browser boundary; it must never reach the Manager,
  controller, logs, storage, exported package, or retained evidence.
- "Clean client" means isolated from the enrollment client state. It does not
  mean forensic secure erasure.

### Integrated reference deployments

- Implement D023 as a new deployment/configuration family; never repurpose
  `LOCUS-compose-deployment-v2`, a P6 process profile,
  `LOCUS-client-api-v1`, or `LOCUS-local-research-ui-v1`.
- The completed D023 predecessor keeps the browser outside Docker and publishes
  only its UI/client-gateway endpoint on host loopback.
- The D025 profile initially publishes only its loopback Manager endpoint and
  creates no Client container. A Manager-created Client receives a separate
  loopback UI endpoint. Neither browser interface may contact the provider,
  resolver, admission service, operator service, parties, or Docker engine
  directly.
- The integrated client backend must use authenticated remote-service adapters
  for admission, discovery, storage, resolution, enrollment, recovery, and
  lifecycle operations. Deployment mode is operator configuration, never an
  API request or recovery-time override.
- A networkless bootstrap role may create synthetic service credentials,
  public configuration, empty role roots, and fixtures only. It must not inject
  recovery-suite state, cues, protected-key material, or secret-bearing client
  state into runtime volumes.
- In the assigned D025 deployment, that one-shot bootstrap runs as root with
  all capabilities dropped except exactly `CHOWN` and `DAC_READ_SEARCH`, has
  `network_mode: none`, receives no Docker socket, and exits before unprivileged
  runtime services start. Those capabilities are limited to creating and
  revalidating owner-only per-role files; they do not expand its allowed data.
- The default reproducible provider is local S3-compatible storage behind the
  application gateway. AWS and actual multi-host profiles are optional,
  separately authorized, separately versioned variants.
- Same-host container/process separation does not establish host separation or
  independent administration.
- Only the dedicated D025 controller may receive the local Docker socket. The
  Manager and Client containers must never mount it. Treat the controller and
  socket as root-equivalent trusted operator infrastructure; do not publish a
  controller host endpoint, and isolate Manager requests on `management` from
  Client self-lifecycle requests on `client-lifecycle`. Accept only fixed,
  project-labeled lifecycle operations over its authenticated API. Never
  accept caller-supplied images, commands, mounts, host paths, networks,
  environment, labels, projects, or arbitrary Docker identifiers.
- Keep lifecycle authority on two disjoint internal networks: `management`
  contains only Manager and controller, while `client-lifecycle` contains only
  controller and managed Clients. A managed Client must not join `management`
  or reach the Manager UI/API; its controller operation must be scoped to its
  own exact instance.
- Keep browser publication on two further disjoint networks: `manager-edge`
  contains only the Manager, while `browser-edge` contains only dynamic
  Clients. They expose separate host-loopback UI paths and must never become a
  container-level Manager-to-Client route. Clients must not join or reach
  `manager-edge`.
- Treat every imported client recovery package and its metadata as untrusted
  until bounded decoding, digest/signature, current-pointer/discovery, and
  current-party checks succeed. Missing authenticated configuration fails
  closed;
  recovery never gains a manual suite, policy, membership, endpoint, or
  fallback override.
- The D025 UI exposes only the registered 2-of-3 and 3-of-5 holder profiles and
  the distinct 4-of-5 authorization quorum. It does not implement arbitrary
  `k,n` or general membership change.
- Treat Client stop/start, restart, and kill/start as destructive volatile
  resets: the public client-instance ID remains, but the process proof identity
  rotates and its server-side key slot, export/import cache, and operation/
  session set are empty. Destroy removes the exact Client and ID; a later create
  receives a fresh ID. UI labels, confirmations, tests, and documentation must
  not imply session continuity or that an already loaded browser document was
  erased.
- Managed bootstrap credentials have a bounded 366-day CA/365-day leaf
  lifetime and no in-place renewal. Normal Manager stop and emergency
  `integrated-stop` preserve exact-project volumes. Only explicit emergency
  `integrated-stop --reset-state` may remove all exact-project role/provider
  volumes and credentials; describe it as an irreversible local reset that
  also destroys the deployment state required by prior packages.
- `prototype_final/` is the D024 active source boundary. It must remain
  dependency-complete and must not import source, scripts, tests, deployment
  assets, or generated state from outside that directory at runtime.
- Expose only `integrated-check`, `integrated-config`, `integrated-start`,
  `integrated-stop`, and `integrated-smoke` from its executor. Add a new command
  only when a later approved PLAN gate requires it and keep the
  `integrated-*` namespace.
- Under D025, normal manual operation uses `integrated-start` without a mode
  and then the Manager and Client UIs. Manager stop-system is the normal stop
  path. `integrated-stop` may remain only for exact-project emergency/orphan
  cleanup and automated smoke cleanup; it preserves role volumes unless the
  operator explicitly supplies `--reset-state`, and it is not an enrollment/
  recovery mode.
- P8+ tests belong under `prototype_final/tests/`; do not add new behavior tests
  to the legacy root `prototype/tests/` unless they specifically preserve a
  frozen compatibility boundary.

### Lifecycle

- Never retire a predecessor until successor parties, backup, and authenticated
  descriptor are durably ready.
- Crash and exact-retry behavior must be tested at every transition.
- General membership change and rollback anchoring require separate design and
  evidence.

### Attempt control

- Signed local audit evidence may remain an implementation feature.
- Do not claim a rollback-resistant global or lifetime attempt bound.
- A monotonic authority, consensus system, or transparency witness is a
  separate owner-approved architecture profile.

## Owner decision gates

Do not make an architectural or manuscript-facing decision on behalf of the
owner when it affects:

- bootstrap/discovery and its trust root;
- whether cloud-account access is a recovery prerequisite;
- descriptor metadata and privacy;
- public admission and identity leakage;
- the number or semantics of CuePolicies;
- a real external provider;
- threshold or party topology;
- the exact aPPSS cryptographic profile or selectable-suite release gate;
- the meaning of independent administration;
- general replacement or a monotonic rollback anchor;
- attempt control as a contribution;
- human studies or usability claims;
- the title, abstract, thesis, contribution hierarchy, claims, or limitations
  of the current manuscript.

Record decisions in `DECISIONS.md` before implementation.

## Evidence rules

Every security-sensitive scenario must document:

1. defensive invariant;
2. exact synthetic inputs and roles;
3. adversary or failed-role view;
4. enforced local trust boundary;
5. positive control;
6. expected privacy-safe observation;
7. limitation on interpretation;
8. exact versioned result path and schema.

Raw retained output is append-only, aggregate-only, and provenance-bound.
Never overwrite v2 or mix old and new profiles in one processed corpus.

The principal P8/P9 system-facing evidence and later artifact
results must exercise the exact D025 Manager-created Client-to-service graph,
Manager/controller and package boundaries, and bind its validated manifest,
resolved graph, images, service identities, network topology, provider, suite,
threshold, policy, failure schedule, client instances, and source state. P7.7
assigned and verified the implementation, but collected no retained P8/P9
evidence. Primitive vectors,
unit/property tests, D023 predecessor runs, component harnesses,
microbenchmarks, P6 profiles, and frozen deployments remain supporting controls
only; do not pool or relabel them as integrated-system results.

The assigned `LOCUS-security-matrix-v2` artifact at
`prototype_final/docs/security-matrix-v2.json` and its schema pin v1/C01--C26
and define managed contracts M01--M05. Assignment and P7.7 acceptance are
implementation governance, not retained evidence or claim promotion.

New implementation claims require new evidence. Tests show implementation
behavior, not cryptographic proof, human usability, or production readiness.

## Manuscript governance

`paper/main.tex` is the authoritative continuation manuscript and
`paper/main.pdf` is the intentional rendered review snapshot.

Never edit manuscript wording merely because implementation or evidence
changed. For every proposed manuscript change:

1. identify the exact sections, claims, tables, figures, or references;
2. show the owner the proposed delta and its implementation/evidence basis;
3. record whether the owner approved or skipped it;
4. edit `paper/` only after approval;
5. synchronize the claim matrix, threat model, limitations, related work,
   generated inputs, and artifact documentation as applicable; and
6. rebuild, render, visually inspect, and record the resulting PDF status.

Approval of an architecture or implementation decision is not automatically
approval of corresponding paper language.

## Working rules

- Inspect before editing and preserve unrelated user changes.
- Prefer `rg` and explicit paths.
- Use noninteractive, cross-platform commands where possible.
- Use `apply_patch` for normal local edits.
- Do not delete, reset, overwrite, or migrate broad paths without explicit
  authorization and exact target verification.
- Never commit credentials, certificates, private keys, real cues, databases,
  service logs, traces, dumps, or generated build directories.
- Keep external inputs strictly bounded and canonically decoded.
- Add tests with every behavior change.
- Update `PLAN.md`, `BASELINE.md`, `VERSION-REGISTRY.md`, active technical
  documentation, and the claim/evidence matrix when their facts change.
- Maintain current baseline documents at their normal `docs/*.md` paths.
  `docs/upstream-baseline/` is a read-only provenance snapshot only.
- For P8 and later implementation work, make changes in `prototype_final/`
  first. Update a legacy copy only when a frozen compatibility test or explicit
  migration task requires it; never make the legacy tree the hidden source of
  truth.

## Build and verification

Install and validate the active D024 prototype from its own directory:

```console
cd prototype_final
uv sync --frozen
uv run --frozen python tasks.py integrated-check
```

Validate the integrated graph and run its complete disposable gate:

```console
uv run --frozen python tasks.py integrated-config
uv run --frozen python tasks.py integrated-smoke
```

The root `tasks.py check`, walkthrough, P7 UI, S3, frozen deployment, and
artifact commands remain historical/component controls. They are not the P8+
default gate and must not collect new integrated evidence. The assigned managed
profiles and P7.7 smoke are implementation controls only; do not collect P8/P9
evidence before the applicable PLAN schema, trace, path, and output gates.

Do not run real-provider or external-service profiles without the corresponding
owner decision and execution authorization.
