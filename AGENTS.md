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
CuePolicy, derives TPASS password input locally, stores only an encrypted
private-key backup in a cloud-object role, and distributes native threshold
state across separately identified recovery parties.

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
- Keep TPASS threshold and authorization quorum distinct in types, schemas,
  UI, logs, and evidence.
- Separate hosts do not prove independent administration.

### Admission

- Keep admission independent of CuePolicy and TPASS.
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
  clipboard use, screenshots, and crash output.
- "Clean client" means isolated from the enrollment client state. It does not
  mean forensic secure erasure.

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

## Build and verification

Install the pinned environment:

```console
uv sync --frozen
```

Run the complete default gate:

```console
uv run --frozen python tasks.py check
```

Optional synthetic walkthrough:

```console
uv run --frozen python tasks.py walkthrough
```

Optional disposable same-host deployment:

```console
uv run --frozen python tasks.py deployment-smoke
```

Do not run real-provider or external-service profiles without the corresponding
owner decision and execution authorization.
