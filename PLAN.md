# LOCUS Improvement Project Plan

## Purpose

This is the living integrated implementation, evidence, artifact, and
owner-approved manuscript plan for the portable LOCUS Improvement Project.

The roadmap has no conference-cycle deadline. Work should follow dependency and
evidence order rather than maximizing visible features quickly.

The owner has approved the overall direction: expand LOCUS into a realistic,
complete reference recovery system while preserving the storage-separation and
below-threshold no-offline-oracle thesis. D016 additionally approves a
versioned aPPSS successor for new enrollments. The frozen Yi TPASS profile
remains active until the successor completes its explicit cutover gate.
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

1. Preserve the active path in `PROTOCOL-INVARIANTS.md` until an approved,
   versioned successor passes its cutover gate.
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

Status: `Complete`

Actions:

- Copy the complete `improvement project` directory to its intended location.
- Confirm `AGENTS.md`, `PLAN.md`, root configs, source directories, tests,
  vectors, active docs, manuscript, review PDF, retained evidence, artifact
  material, and licenses are at the copied repository root.
- Do not copy the upstream `.git`, caches, targets, environments, or credentials.

Acceptance:

- The copied root is not nested inside the original Git repository.
- Required files in `PORTABILITY-CHECKLIST.md` are present.

Completion record (2026-07-31):

- Git identifies this directory as the independent `LOCUS-v3` repository root.
- Git reports no enclosing superproject.
- Every required root file and source directory in
  `PORTABILITY-CHECKLIST.md` is present.

### P0.2 Initialize source control and freeze the import

Status: `Complete`

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

Completion record (2026-07-31):

- The independent repository was initialized with initial import commit
  `71836c304490db0984cbe2786edf414ff18a960b`.
- All 307 entries in `PORTABLE-CONTENTS.json` matched by size and SHA-256; the
  manifest plus those entries comprise the 308 files in the initial commit.
- The initial commit has no imported parent history, and `origin` points to the
  owner-created LOCUS-v3 repository rather than the upstream repository.
- The initial import had no ignored or untracked files. Subsequent project
  records may change without modifying the immutable import manifest.

### P0.3 Run the clean baseline gate

Status: `Complete`

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

Progress record (2026-07-31, commit
`5516b9db7221f4f64ae0dab66b176ee486f0d16a`):

- The frozen environment synchronized under CPython 3.12.13 with 18 pinned
  packages.
- The complete local Windows gate passed: 65 Python files parsed; Ruff format
  and lint passed for 66 files; mypy passed for 66 source files; 152 Python
  tests passed with the opt-in live-S3 test skipped; 17 Rust core unit tests and
  one fixed-vector integration test passed; rustfmt and clippy passed for both
  Rust crates; and the PyO3 extension built from source.
- The first gate attempt could not create `tpass-python/target` under the
  controlled execution environment. Creating that exact ignored build
  directory and retrying the unchanged command succeeded. This is recorded as
  a local execution-environment constraint, not a source compatibility result.
- Regenerating the retained 30-input v2 performance summary produced the
  recorded SHA-256
  `462e492795fafdd90a4f39851a612275193603d816f761728afe05e97a470a6b`.
  The manifest-bound `LOCUS-performance-paper-inputs-v2` bundle verified as
  `unchanged` without replacement.
- MiKTeX pdfTeX/BibTeX rebuilt the manuscript as a 14-page, letter-size PDF.
  Its binary digest differed from the imported snapshot and its observed PDF
  creation/modification timestamps differed, but all 14 page renders were
  byte-identical under the same Poppler renderer. Visual inspection found no
  new layout difference. It reconfirmed the inherited page-13 overfull line in
  which the frozen TPASS identifier reaches into the adjacent column; this is a
  baseline review issue and does not authorize a manuscript edit.
- GitHub Actions run 7 for commit
  `d80dbe3a7e66f2f091087d44fe412eae08778f47` passed on clean
  `ubuntu-latest` (job `91174703539`) and `windows-latest` (job
  `91174703595`); the dependent artifact smoke job `91176596063` also passed.
- Clean-run compatibility fixes were limited to typed access to the optional
  Windows subprocess flag, portable mutation of intentionally read-only test
  snapshots, and bounded test-network deadlines aligned with the existing
  deployment profile. The complete local gate remained green after each final
  patch.

### P0.4 Reconcile manuscript/evidence/artifact tooling

Status: `Complete`

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

Completion record (2026-07-31):

- The active builder now emits `LOCUS-anonymous-artifact-v2` under archive root
  `locus-artifact-v2`, uses the strict
  `docs/schemas/artifact-manifest-v2.schema.json`, and reads release status only
  from the separate v2 checklist. The sealed v1 archive and manifest remain
  unchanged and verification-only.
- Extracted-tree source and experiment-provenance readers accept both frozen v1
  and active v2 manifest envelopes. Package creation emits only v2, preventing
  silent reinterpretation or overwrite of v1.
- The v2 audit passed over 149 explicitly allowlisted files. It includes only
  package-specific reviewer documentation, licensed source/synthetic fixtures,
  schemas, frozen aggregate v2 evidence, its processed summary, and generated
  performance inputs. It excludes repository planning documents, manuscript
  source/PDF, bibliography and LaTeX support, superseded evidence, external
  papers, and prohibited state. Release remains `pending`, so no v2 ZIP was
  created.
- Eleven focused artifact/provenance tests passed, including deterministic ZIP
  construction and v1/v2 extracted-manifest compatibility. The complete local
  gate passed with 152 Python tests (one opt-in live-S3 skip), 17 Rust core tests,
  the fixed vector, native extension build, Ruff, mypy, rustfmt, and clippy.
- Retained performance-v2 processing verified byte-identically at SHA-256
  `462e492795fafdd90a4f39851a612275193603d816f761728afe05e97a470a6b`;
  the manifest-bound `LOCUS-performance-paper-inputs-v2` bundle reported
  `unchanged`. The P0.3 manuscript rebuild/14-page render comparison remains
  applicable because neither manuscript source nor generated inputs changed.

---

## P1 — Freeze active architecture contracts

### P1.1 Approve the initial decision set

Status: `Complete`

Required decisions:

- Approved: D001, D003, D005, D014, D015, and D016 establish account-scoped
  bundle discovery, descriptor trust, three atomic CuePolicies, the immutable
  bundle layout, and an application-operated S3 namespace with an optional AWS
  S3 profile, plus a versioned aPPSS successor with frozen Yi compatibility.
  D015 supersedes the personal-cloud-account and Google Drive choices in D002
  and D006.
- Approved: D004, D007--D010, and D017 select the local provider-neutral
  admission profile, evaluated suite order, exact independence wording, local
  audit boundary, thin cross-platform UI direction, and exact initial aPPSS
  recovery contract.

Acceptance:

- Approved decision records include trust, privacy, version, compatibility, and
  evidence consequences.

Completion record (2026-08-01):

- The owner approved the complete recommended P1.1 bundle. `DECISIONS.md`
  records every selected option and its trust, privacy, compatibility,
  evidence, implementation, and manuscript boundary.
- D004 makes the project-controlled local synthetic issuer the required
  reference implementation of one proof-key-bound admission contract. OIDC
  Authorization Code with PKCE/DPoP is an optional later adapter, not an
  external dependency, recovery factor, traceability feature, or paper
  contribution.
- D007--D010 preserve the Yi 2-of-3 baseline, evaluate aPPSS 2-of-3 first,
  reserve independent-administration wording for actual independent operators,
  keep attempt control local/audit-only, and defer UI-framework choice until
  the client APIs are frozen.
- D017 authorizes the exact P1.2 profile but no manuscript wording. Final aPPSS
  identifiers and wire schemas remain a P5A.1 gate with canonical vectors.

### P1.2 Freeze the password-protected recovery contract

Status: `Complete`

Before implementation, map the aPPSS construction in Section 3, Figure 4, and
Theorem 2 of *Password-Protected Threshold Signatures* to LOCUS:

- distinguish the paper's corruption bound `t` and reconstruction threshold
  `t+1` from LOCUS reconstruction threshold `k`, with `k = t+1`;
- define the exact password space, high-entropy recovery-secret output,
  server/public/client state, initialization and recovery messages, and failure
  behavior;
- state the random-oracle, OPRF, authenticated-initialization, server-identity,
  erasure, corruption-timing, and availability assumptions;
- define precisely that fewer than `k` static party states expose no local cue
  predicate under those assumptions, while `k` or more aPPSS server states
  enable unrate-limited offline password tests and reveal `S_R` after a correct
  guess;
- record that the existing Yi profile instead Shamir-shares the password,
  secret exponent, and digest, so `k` Yi states directly interpolate the
  password and high-entropy recovery secret;
- use the aPPSS output `sk` directly as LOCUS `S_R`, followed by the existing
  HKDF-SHA-256 and AES-256-GCM path; and
- reject importing aptSIG, retaining an independently threshold-shared unmasked
  `S_R`, or treating implementation tests as a new cryptographic proof.

Acceptance:

- D017 records the exact OPRF, field/security parameter, hashes, domains,
  canonical formats, robustness choice, and theorem-to-LOCUS claim mapping.
- `docs/APPSS-MIGRATION.md` and the claim/evidence matrix agree on thresholds,
  assumptions, claims, and non-claims.

Completion record (2026-08-01):

- `docs/APPSS-PROFILE.md` freezes the D017 contract: Figure 4 aPPSS only;
  RFC 9497 OPRF-mode ristretto255/SHA-512 as the concrete 2HashDH realization;
  `lambda=128`; canonical polynomial-basis `GF(2^128)` Shamir sharing;
  domain-separated SHA-256 for 16-byte `C` and 16-byte `S_R`; canonical public
  `omega`; authenticated epoch/session bindings; generic rejection; and
  abort-only robustness without the optional VOPRF extension.
- The first evaluated profile is `k=2,n=3`, mapping to `t_paper=1,n=3`.
  `S_R` is the aPPSS output and feeds the existing HKDF/AES path directly.
- The first LOCUS implementation/evidence claim is limited to static
  persistent-state compromise. Theorem 2's hybrid/random-oracle statement and
  the concrete RFC 9497 OPRF assumptions remain separate from implementation
  tests and require independent review.
- Final identifiers, strict wire schemas, size bounds, vectors, and native
  library selection remain intentionally deferred to P5A.1; the approved
  primitives and claim boundary may not change there without a new decision.

### P1.3 Create typed system interfaces

Status: `Complete`

Define interfaces for:

- `PasswordProtectedSecretRecovery`, with opaque versioned public, party,
  request, response, and client-session types;
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
- Recovery-suite holder and authorizer roles must be distinct types.
- The frozen Yi implementation is one compatibility adapter; the new aPPSS
  suite is a separate adapter and never reuses Yi wire objects or domains.
- Strict decoders reject unknown, duplicate, oversized, and unsupported input.

Acceptance:

- Interface tests compile/run without changing current native Yi recovery
  results.
- Existing cue and Yi TPASS vectors remain byte-identical.

Completion record (2026-08-01):

- `prototype/locus/contracts.py` defines distinct typed boundaries for
  recovery-suite public/party/request/response/client-session state,
  CuePolicy, Resolver, backup/descriptor storage, admission/storage
  capability validation, application storage gateway, party directory,
  enrollment/recovery state machines, and lifecycle management.
- `YiTpassRecoveryAdapter` wraps the unchanged `NativeTpassBackend` under the
  suite-neutral `PasswordProtectedSecretRecovery` protocol. Its in-memory
  opaque wrappers preserve embedded `LOCUS-TPASS-wire-v1` parameter and party
  state bytes and assign no new external format.
- The frozen location-person policy and deterministic resolver now have thin
  adapters that delegate to their existing functions without changing bytes or
  failure behavior. `BackupObjectStore` remains the existing compatibility
  contract and is now runtime-checkable.
- Interface tests pin the frozen TPASS and CuePolicy vector-file digests,
  exercise native 2-of-3 recovery through the Yi adapter, preserve exact vector
  payloads, reject malformed/cross-suite opaque state, and keep authorizer and
  recovery-holder memberships/thresholds distinct.
- `docs/SYSTEM-INTERFACES.md` records which contracts are implemented adapters
  and which remain interface-only for P2--P4. No aPPSS, descriptor, admission,
  new policy, UI, evidence, or manuscript behavior is claimed.
- The complete default gate passed with 160 Python tests (one expected opt-in
  live-S3 skip), 17 Rust core tests, the fixed-vector integration test, native
  binding build, formatting, lint, type, and repository-boundary checks.

### P1.4 Freeze a new profile namespace

Status: `Complete`

Actions:

- Assign identifiers only after schemas are approved.
- Register recovery-suite, policy, descriptor, backup, admission, deployment,
  trace, result, and artifact versions in `VERSION-REGISTRY.md`.
- Define compatibility and upgrade rules.

Acceptance:

- No new identifier collides with or reinterprets a frozen upstream identifier.

Completion record (2026-08-01):

- `docs/version-registry-v1.json` is the machine-readable P1.4 allocation
  ledger, and `docs/schemas/version-registry-v1.schema.json` freezes its exact
  shape. `LOCUS-version-registry-v1` is the only new identifier assigned by
  this phase, with its schema and tests introduced in the same change.
- At P1.4 completion, the ledger protected 76 existing and registry identifiers
  against exact or case-folded collision. Protection includes frozen,
  superseded, development,
  test, wire, lifecycle, snapshot, trace, result, and artifact identifiers but
  does not promote their status or reinterpret their meaning.
- Nine future families—recovery suite, policy/resolver, descriptor,
  backup/bundle, admission, deployment, trace, result, and artifact—are
  reserved by owner decision and chronological allocation phase without
  premature candidate identifiers.
- `VERSION-REGISTRY.md` defines syntax, allocation states, schema/vector gates,
  and upgrade rules. Unknown versions fail closed; suite/policy/topology and
  evidence changes receive distinct identifiers and, where applicable, a new
  epoch. Frozen evidence is never pooled or relabeled.
- `prototype/tests/test_version_registry.py` checks the registry/schema shape,
  canonical ordering, exact and case-folded uniqueness, frozen minimum set,
  active-source coverage, reservation completeness, and absence of identifier
  fields from pre-schema reservations.
- No recovery protocol, wire format, descriptor, admission mechanism,
  deployment, evidence corpus, or manuscript wording changes in P1.4.
- The complete default gate passed with 164 Python tests (one expected opt-in
  live-S3 skip), 17 Rust core tests, the fixed-vector integration test, native
  binding build, formatting, lint, type, and repository-boundary checks.

### P1.5 Create security and information-flow matrices

Status: `Complete`

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
- each exact-reconstruction-threshold aPPSS coalition used by the comparative
  compromise claim;
- matching combined state;
- enrollment client after disposal;
- clean client before and after cue entry;
- identity/admission provider;
- network-role metadata.

Acceptance:

- Every active claim has an asset, adversary, assumptions, boundary, positive
  control, expected observation, and interpretation limit.

Completion record (2026-08-01):

- `docs/INFORMATION-FLOW.md` now crosses all six required phases with all
  twelve operational, adversary, and evidence views. Its legend distinguishes
  transient, persistent, metadata-only, snapshot, phase-gated, and absent
  flows so planned behavior is not mistaken for implementation.
- Phase contracts define allowed and forbidden enrollment, disposal,
  bootstrap, recovery, successor-publication, and replacement flows. The
  original material-by-role table remains controlling for individual values.
- The coalition matrix enumerates every one-party below-threshold and every
  two-party exact-threshold coalition for the first 2-of-3 aPPSS profile,
  separates the all-server control, and requires every matching combined view
  to bind the same suite, backup, epoch, policy, membership, and configuration.
- `docs/security-matrix-v1.json` and its strict schema record phases, views,
  asset, adversary, assumptions, boundary, positive control, expected
  observation, and interpretation limit for every C01--C26 row.
  `LOCUS-security-matrix-v1` is a governance identifier, not a protocol, trace,
  result, or evidence profile.
- Automated tests require exact cross-document claim coverage, complete
  nonempty contracts, all phase/view coverage, explicit C24/C25 threshold
  separation, preservation of non-claims, coalition enumeration, and P1.4
  registry inclusion.
- No implementation claim is promoted, no evidence is collected or
  reinterpreted, and no manuscript wording changes in P1.5.
- The complete default gate passed with 169 Python tests (one expected opt-in
  live-S3 skip), 17 Rust core tests, the fixed-vector integration test, native
  binding build, formatting, lint, type, and repository-boundary checks.

---

## P2 — RecoveryDescriptor and bootstrap

### P2.1 Specify `RecoveryDescriptor`

Status: `Complete`

Specify:

- canonical schema and maximum size;
- version;
- backup identifier, epoch, logical immutable backup reference, and digest;
- CuePolicy identifier and public parameters;
- recovery-suite identifier, suite public parameters, and reconstruction
  threshold `k`;
- recovery secret-state-holder membership;
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

Completion record (2026-08-01):

- P2.1 assigns separate immutable identifiers for the signed descriptor,
  signed current pointer, bootstrap signature, configuration digest, two-entry
  manifest, and deterministic bundle. `VERSION-REGISTRY.md` records exact
  compatibility rules; no P3.3 admission identifier is assigned early.
- Strict JSON schemas freeze exact descriptor, current-pointer, and manifest
  shapes and bounds. `prototype/locus/recovery_descriptor.py` implements
  duplicate-rejecting canonical JSON, external-root Ed25519 verification,
  configuration/cross-object digest binding, and exact membership/quorum
  validation.
- The descriptor contains public policy/suite bytes and distinct recovery
  holder/authorizer sets but no trust key, cue hint/hash, password-derived
  authenticator, party secret state, `S_R`, `K_wrap`, credential, or plaintext
  key. The expected issuer, key ID, and public key are external inputs.
- `LOCUS-recovery-bundle-v1` freezes exact member order, stored compression,
  timestamps, attributes, flags, and size/ratio limits. Its manifest lists only
  `backup.json` and `descriptor.json`; the signed pointer outside the ZIP binds
  its uploaded locator, bytes, descriptor, subject, backup, epoch, and
  configuration.
- The synthetic canonical vector pins member, signature, descriptor, pointer,
  manifest, and bundle digests/lengths without retaining a private signing key.
  Negative tests cover missing, duplicate, unknown, noncanonical, nested,
  encrypted, flagged, unsupported, oversized, over-compressed, trailing,
  signature, issuer/key, membership/quorum, digest, and cross-binding cases.
- `docs/RECOVERY-DESCRIPTOR.md` records exact formats, signature/configuration
  framing, limits, publication boundary, forbidden fields, visible metadata,
  linkability, and the conditional no-offline-predicate disclosure analysis.
- The complete pinned repository gate passes with 180 Python tests (one
  intentional skip), 17 native Rust tests, the frozen Rust protocol vector,
  formatting, linting, strict typing, and source-boundary validation.
- P2.1 does not implement discovery, DescriptorStore/CAS, admission,
  clean-client recovery, security evidence, or manuscript wording.

### P2.2 Specify discovery and trust bootstrap

Status: `Complete`

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

Completion record (2026-08-01):

- P2.2 assigns `LOCUS-account-scoped-bootstrap-v1`, the canonical installed
  trust configuration, optional signed receipt, party-current summary, and
  party-current signature profiles. The registry records separate compatibility
  boundaries and the three new JSON schemas freeze exact shapes and bounds.
- `prototype/locus/recovery_bootstrap.py` authenticates already supplied
  account-scoped discovery bytes. It validates installed trust validity and
  endpoint, the operator-signed P2.1 pointer/bundle/descriptor chain, external
  subject and recovery handle, optional receipt, exact installed party
  endpoint/key bindings, and a fresh matching authorization quorum before any
  cue-dependent processing.
- The returned adapter implements the P1.3 `PartyDirectory` contract with
  recovery threshold and authorization quorum still distinct. Valid dissent is
  reported; fewer than the required matching summaries fail explicitly as
  unavailable or cloud/party mismatch.
- Trust updates require a consecutive generation and exact predecessor digest
  but are accepted only as already trusted application-installation inputs.
  Descriptor-, bundle-, receipt-, or discovery-supplied keys never become trust
  roots. Root/key/endpoint rotation therefore fails closed until a trusted app
  update installs the replacement.
- Synthetic vectors and unit tests cover a complete clean-client positive
  control, receipt/no-receipt paths, invalid or expired trust, wrong discovery
  endpoint, wrong subject/handle, pointer/bundle substitution, untrusted
  operator/party keys and endpoints, malformed/tampered/stale/duplicate party
  summaries, quorum unavailability, signed state disagreement, trust-update
  continuity, and forbidden secret fields.
- The disclosure/rollback analysis states that admission/account/storage and
  live-party availability are prerequisites; operator and parties observe
  linkable public recovery metadata; operator compromise alone cannot forge the
  pinned party quorum; and coordinated rollback or compromise of all required
  authorities remains outside the profile.
- The complete pinned repository gate passes with 191 Python tests (one
  intentional skip), 17 native Rust tests, the frozen Rust protocol vector,
  formatting, linting, strict typing, and source-boundary validation.
- P2.2 does not implement DescriptorStore/CAS, admitted gateway retrieval,
  P2.4 evidence, complete clean-client recovery, or manuscript wording.

### P2.3 Implement `DescriptorStore`

Status: `Complete`

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

Completion record (2026-08-01):

- `LOCUS-descriptor-bundle-store-v1` freezes the exact provider-neutral key
  grammar and semantics for immutable descriptors, immutable bundles, and the
  separately mutable hashed-handle current pointer. A synthetic locator vector
  pins the P2.1 descriptor/bundle inputs to their exact storage keys.
- `prototype/locus/descriptor_store.py` implements strict structural storage
  validation, exact SHA-256/length/subject/backup/epoch/manifest bindings,
  filesystem and S3-compatible adapters, a typed recovery-bundle contract, and
  a same-host service-shaped adapter. Storage never treats an S3 ETag, ACL, or
  successful read as descriptor authenticity.
- Immutable descriptor and bundle publication is create-only and idempotent
  only for exact bytes. Current-pointer creation and replacement use exact-byte
  compare-and-swap; the S3 adapter binds replacement to the observed ETag while
  treating it only as an opaque concurrency token.
- Shared tests cover exact retry, immutable conflict, absent objects,
  corruption/substitution, oversize, outage, exact-byte preservation, no-list
  S3 behavior, initial/current pointer separation, stale writers, two-writer
  concurrency, and an injected ETag race.
- `ObjectStale` is a separate failure from not-found, immutable conflict,
  unavailable, corrupt, and oversized outcomes. The frozen backup-object store
  remains a separate unchanged contract and namespace.
- The complete pinned repository gate passes with 199 Python tests (one
  intentional skip), 17 native Rust tests, the frozen Rust protocol vector,
  formatting, linting, strict typing, and source-boundary validation.
- P2.3 exposes the same-host storage service below admission. It does not
  invent the still-unassigned P3.3 capability format: the application gateway
  will consume P3's independently validated D004/D015 grant before invoking
  this service. No AWS execution, external credential, or manuscript wording
  is included.

### P2.4 Implement descriptor security scenarios

Status: `Complete`

Scenarios:

- wrong recovery handle;
- wrong account scope;
- altered signature;
- wrong issuer;
- stale epoch;
- cross-user substitution;
- cross-policy substitution;
- cross-suite substitution or downgrade;
- cross-membership mix;
- descriptor/backup digest mismatch;
- descriptor/party current-state mismatch;
- altered, duplicate, unexpected, unsafe-path, oversized, or unsupported ZIP
  members;
- stale bundle and current-pointer rollback;
- positive controls for every detector.

Acceptance:

- Results use a new aggregate-only descriptor-security schema.

Completion record (2026-08-01):

- `LOCUS-descriptor-security-scenarios-v1` defines a strict aggregate-only
  development regression report for all sixteen approved detector families,
  one positive control per family, exact P2.1--P2.3 versions, cleanup/output
  gates, and a bounded two-candidate networkless direct-verifier check.
- The synthetic scenarios exercise wrong handle/scope, altered authentication,
  stale or cross-bound state, policy/suite/membership mismatches, backup and
  party-state disagreement, malformed bundle classes, and stale bundle/pointer
  rollback using the registered P2.1--P2.3 validators and stores.
- The report retains only identifiers, safe failure categories, counts, and
  Boolean observations. Validators reject unknown fields, missing/failed
  controls, reordered scenarios, version changes, secret-bearing output, and
  contradictory counts.
- This is implementation-regression output, not P9 evidence, cryptographic
  proof, a general offline-oracle proof, entropy analysis, production-security
  evidence, or coordinated-rollback resistance. The P9 result family remains
  reserved and no manuscript wording is authorized.
- The complete pinned repository gate passes with 201 Python tests (one
  intentional skip), 17 native Rust tests, the frozen Rust protocol vector,
  formatting, linting, strict typing, and source-boundary validation.

---

## P3 — Enrollment and admission

### P3.1 Refactor enrollment into a stable state machine

Status: `Proposed`

States:

```text
key import/generation
-> policy processing
-> recovery-suite setup
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
- No coordinator persists all recovery-suite secret states. An aPPSS production
  enrollment has each server create and retain its own OPRF key; a central
  fixture may exist only for bounded unit tests.

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

Keep admission independent from CuePolicy/recovery-suite correctness.

Acceptance:

- Threat model covers replay, stolen bearer token, malicious client,
  cross-account use, false-lockout attempts, identity-provider unavailability,
  and privacy leakage.

### P3.4 Implement local admission

Status: `Proposed`

Implement the D004 provider-neutral contract with a project-controlled
deterministic local synthetic issuer/test double. An OIDC Authorization Code
with PKCE/DPoP adapter is optional later work under a distinct profile and is
not required for the core prototype, artifact, paper assumption, or reviewer
workflow.

Acceptance:

- Every authorizer validates independently.
- The application storage gateway validates its separate exact-operation
  capability independently before contacting S3.
- Replay, wrong key, wrong subject, wrong audience, wrong operation, wrong
  backup, wrong epoch, wrong prefix, expired token, and nonce reuse fail.
- Reviewer workflows need no external identity provider.
- Adding or omitting an external OIDC adapter does not change CuePolicy,
  recovery-suite correctness, or the offline-oracle claim.

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
-> recovery-suite recovery
-> AEAD decryption
-> key identity verification
-> successor action
```

Acceptance:

- Wrong input and malformed remote state expose only the approved error
  boundary.
- The client does not disclose the final recovery-suite/AEAD outcome to parties.

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
- Frozen Yi TPASS input and backup vectors remain unchanged. Each new policy's
  canonical bytes enter a recovery suite only through that suite's separately
  versioned password-input domain.
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

- Four policies share one interface without changing either recovery-suite
  implementation.
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
- No resolver automatically enumerates cue alternatives through a recovery
  suite.

---

## P5A — Versioned aPPSS successor and Yi-to-aPPSS migration

Direction: `Approved` by D016
Execution status: `Proposed`

This phase begins only after P1 has frozen the suite-neutral contract, P2 binds
the suite in authenticated recovery metadata, P3 supplies authenticated
enrollment, P4.1--P4.3 supply recovery and successor state machines, P5 has
shown that CuePolicy is independent of the recovery suite, and D017 is
approved. P4.4 general membership replacement is not a prerequisite.

For this phase, "replacement" means that aPPSS becomes the active suite for new
enrollments after cutover. The frozen Yi suite remains available only for
legacy recovery and migration. One epoch contains exactly one suite. There is
no in-place share conversion, dual-state fallback, automatic downgrade, or
reinterpretation of an old identifier, backup, vector, or evidence record.

### P5A.1 Freeze the exact aPPSS profile and formats

Status: `Proposed`

Specify:

- the Section 3, Figure 4 aPPSS protocol and Theorem 2 mapping, excluding the
  paper's aptSIG and threshold-signature layers;
- LOCUS reconstruction threshold `k`, party count `n`, and the explicit mapping
  `k = t_paper + 1`;
- the concrete OPRF construction and proof basis, security parameter, Shamir
  field, hash-to-group/hash/random-oracle functions, and domain separation;
- public `omega=(e,C)`, public parameters, independent per-server OPRF state,
  transient client state, request/response messages, and typed failures;
- authenticated initialization, server identity, session, backup identifier,
  epoch, CuePolicy, membership, threshold, configuration, and operation
  bindings;
- malicious-server abort behavior and the approved decision on the paper's
  optional verifiable-OPRF robustness sketch; and
- new bounded canonical wire and state formats, with no serializable client
  blinder or secret-bearing debug/log representation.

The recovered aPPSS output `sk` is LOCUS `S_R`. It feeds the existing
HKDF-SHA-256 wrapping-key derivation directly. Do not add or retain an
independently threshold-shared unmasked recovery secret.

Acceptance:

- D017 is approved and fully reflected in `docs/APPSS-MIGRATION.md`, a new
  exact profile specification, and a new wire-format specification.
- The version registry assigns identifiers only alongside approved schemas and
  canonical vectors.
- Cross-suite, cross-version, cross-epoch, cross-session, and cross-membership
  objects fail closed.

### P5A.2 Implement the native aPPSS core

Status: `Proposed`

Implement a separate research-grade Rust core using the approved profile:

- OPRF blind/evaluate/finalize and server-key lifecycle;
- field/Shamir operations, share masking, interpolation, `C` verification, and
  recovery-secret derivation;
- strict bounded canonical codecs for every external object;
- secret redaction, zeroization where supported, and production CSPRNG use;
- deterministic randomness only in tests and frozen vectors; and
- typed internal errors that can be normalized at service boundaries.

Tests cover correct and wrong passwords, every valid subset for bounded small
`k,n`, insufficient/duplicate/out-of-range parties, inconsistent `omega`,
malformed/truncated/trailing/wrong-kind/noncanonical objects, identity or
invalid group elements where applicable, altered state/messages, resource
bounds, and deterministic regeneration.

Acceptance:

- A frozen synthetic vector is regenerated by Rust and consumed independently
  across the narrow Python boundary.
- The frozen Yi crate, wire format, vector, and behavior remain byte-identical.
- Unit fixtures that centrally orchestrate setup are explicitly labeled and do
  not count as evidence of authenticated distributed initialization.

### P5A.3 Integrate the generic client and party protocol

Status: `Proposed`

Actions:

- add a narrow PyO3 binding and register Yi and aPPSS as distinct
  `PasswordProtectedSecretRecovery` adapters;
- replace TPASS-specific orchestration assumptions with opaque,
  suite-versioned messages while retaining the frozen Yi adapter;
- version request hashes, SQLite state, runtime packages, service routes,
  backup fields, descriptor fields, redaction rules, snapshot parsers, and
  build-lock provenance;
- keep authorization durable before the first secret-dependent OPRF response;
  and
- define exact retry, timeout, subset, crash, restart, and generic external
  failure behavior for the aPPSS flow.

Acceptance:

- Correct and wrong-input recovery works through distinct authenticated party
  processes for the new profile.
- No coordinator or provisioner persists all OPRF keys, and each server creates
  and retains only its own key.
- Cross-suite substitution and downgrade fail before secret-dependent recovery.

### P5A.4 Integrate authenticated initialization

Status: `Proposed`

Use P3's enrollment transport so the client performs the approved OPRF
initialization with each authenticated server and distributes the common
`omega=(e,C)` record under exact recipient, suite, backup, epoch, policy,
membership, threshold, and configuration bindings. The existing networkless
central provisioner may remain only as a legacy Yi path or generated test
fixture; it cannot support an aPPSS distributed-initialization claim.

Acceptance:

- Wrong server, recipient, suite, epoch, body, replay, and idempotency reuse
  fail closed.
- Each ready party proves possession of the exact bound state without exposing
  its OPRF key or a cue verifier.
- Initialization interruption cannot activate a partially provisioned epoch.

### P5A.5 Implement successor migration and cutover

Status: `Proposed`

Migration procedure:

1. Recover the protected key client-side through the frozen Yi predecessor.
2. Create a fresh aPPSS recovery secret, party state, backup, descriptor, and
   epoch under new identifiers.
3. Durably prepare and verify every required party, storage object, bundle,
   descriptor, and current-state binding.
4. Activate the aPPSS successor through the P4 lifecycle protocol.
5. Retire the Yi predecessor only after successor recovery succeeds.

Acceptance:

- Crash and exact retry are tested at every transition.
- Old and new state never combine into a threshold result.
- A new aPPSS epoch never silently falls back to Yi.
- New enrollments select aPPSS only after the complete P5A acceptance gate;
  existing Yi epochs remain recoverable without reinterpretation.

### P5A.6 Validate the comparative security boundary

Status: `Proposed`

Add fixed, bounded, synthetic scenarios for:

- cloud-only aPPSS state;
- every evaluated coalition below reconstruction threshold `k`;
- matching cloud plus below-threshold aPPSS state;
- exact-threshold and all-server aPPSS state; and
- a fixed Yi comparator showing that `k` serialized Yi party states directly
  reconstruct the shared password scalar and high-entropy recovery secret,
  while `k` aPPSS states expose an offline dictionary-test capability and
  reveal `S_R` only after the fixed correct candidate.

Retain only aggregate Boolean/category observations. Never retain candidates,
per-candidate outcomes, OPRF keys, masked or unmasked shares, passwords,
recovery secrets, private keys, raw snapshots, or configurable attack tooling.

Acceptance:

- Every scenario has the invariant, exact synthetic roles, enforced read-only
  and networkless boundary, positive control, expected observation,
  interpretation limit, and new schema/path.
- Documentation states that the no-offline-predicate and augmented-compromise
  properties are inherited from their respective constructions under explicit
  assumptions; tests demonstrate only the exact implementation boundary.
- Threshold compromise is described as unrate-limited offline guessing, not as
  continued threshold security or protection for low-entropy cues.

### P5A.7 Complete cutover documentation and review gates

Status: `Proposed`

Actions:

- pass clean Linux and Windows builds and the complete legacy-regression gate;
- collect no retained performance corpus until P9 freezes a new methodology
  and result schema;
- update active architecture, protocol, threat, information-flow, lifecycle,
  API, storage, evidence, artifact, and version documentation at cutover;
- obtain independent cryptographic review of the paper-to-code mapping before
  calling the profile "augmented" or promoting the comparative result; and
- prepare M-APPPSS-001, but do not edit `paper/` until its separate owner
  approval and the P8/P9 evidence gates are complete.

Acceptance:

- Frozen Yi regression and retained-v2 verification remain unchanged.
- The active-profile cutover commit, identifiers, clean-host results, review
  findings, and known limitations are recorded.
- Manuscript wording remains unchanged unless M-APPPSS-001 is explicitly
  approved and later applied under P10.6.

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
- explicit recovery-suite identity for every profile, with aPPSS active for new
  profiles after P5A and Yi labeled legacy-only;
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
- recovery-suite password input, OPRF keys, masked or unmasked shares,
  recovery secret, wrapping key;
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
- each exact-threshold aPPSS coalition supporting the augmented-compromise
  comparison, kept separate from below-threshold no-oracle evidence;
- cross-suite and downgrade views;
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
- Keep signed local auditing isolated from recovery-suite correctness claims.
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
- recovery-suite initialization, including per-server OPRF work;
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

- Schemas bind exact recovery suite, policy, descriptor, backup, profile,
  threshold, party identities, topology, backend, scenario, positive control,
  output scan, and limitations.
- aPPSS and frozen Yi results use separate result families. A comparative
  processor may consume both only under a new schema that preserves both
  provenance records and never relabels or pools retained v2 measurements.

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

- the aPPSS Section 3/Figure 4/Theorem 2 paper-to-code mapping;
- the concrete OPRF, field, hashes, domains, authenticated initialization, and
  threshold-notation translation;
- canonical aPPSS wire/state formats and server-key lifecycle;
- reconstruction, commitment check, malformed-state, and downgrade behavior;
- the scoped claim comparing Yi direct threshold-state reconstruction with
  aPPSS offline-dictionary degradation;
- continued correctness of the frozen Yi compatibility path;
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

Execution is chronological. P0, P1.1--P1.5, and P2.1--P2.4 are complete; begin
with P3.1 and do not begin a later phase while an applicable predecessor gate is incomplete,
except for a task explicitly marked deferred and not named as a dependency.

The next sequence is:

1. P3.1--P3.4 — generic enrollment and authenticated admission/transport;
2. P4.1--P4.3 — generic recovery, clean-client isolation, and crash-safe
   successor publication; P4.4 remains deferred unless D011 is approved;
3. P5.1--P5.4 — CuePolicy and resolver generality without changing either
   recovery suite;
4. P5A.1--P5A.7 — aPPSS implementation, authenticated integration, migration,
   comparative boundary validation, and active-profile cutover; and
5. P6 onward — storage/deployment expansion, UI, assurance, performance,
   external review, artifact, and separately approved manuscript changes.

Do not begin the graphical UI, external provider run, expanded deployment
profiles, or general party replacement before the applicable preceding gates
are complete.
