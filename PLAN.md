# LOCUS Improvement Project Plan

## Purpose

This is the living integrated implementation, evidence, artifact, and
owner-approved manuscript plan for the portable LOCUS Improvement Project.

The roadmap has no conference-cycle deadline. Work should follow dependency and
evidence order rather than maximizing visible features quickly.

The owner has approved the overall direction: expand LOCUS into a realistic,
complete reference recovery system while preserving the storage-separation and
below-threshold no-offline-oracle thesis. D017 approves a versioned aPPSS
construction, and D018 keeps frozen Yi TPASS and aPPSS as independent
first-class suites selected explicitly per enrollment or successor epoch. Yi
and aPPSS are now implemented at the application/component boundary. D023
requires their complete UI-to-container composition in one new integrated
reference system before P8/P9. D024 isolates that implementation under
`prototype_final/` and makes its reduced `integrated-*` command surface the
only active P8+ implementation path. D025 approves a newly versioned Manager-
controlled deployment and dynamic Client UI workflow inside that same source
boundary. P7.7 completed that migration and its new security/version gates
before P8. The twelve D025 managed identifiers
are Assigned; the completed D023 deployment remains an immutable supporting
predecessor. P8.1 is the next ready step. Architecture decisions listed in
`DECISIONS.md` remain owner gates.

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

1. Preserve the implemented Yi path in `PROTOCOL-INVARIANTS.md` while adding
   the independently versioned aPPSS path and explicit one-suite-per-epoch
   selector through its acceptance gates.
2. Resolve and record owner decisions before affected implementation.
3. Never reinterpret frozen identifiers or retained/historical evidence.
4. Add a new version for every semantic change.
5. Keep UI, provider, and deployment adapters outside the cryptographic core.
6. Write claim/evidence and information-flow requirements before experiments.
7. Use synthetic data and project-controlled disposable services.
8. Before every manuscript edit, present the exact proposed delta and obtain
   explicit owner approval. The owner may approve or skip each change.
9. P7.7 assigned and verified the D025 managed implementation without collecting
   retained P8/P9 evidence. Treat that Manager-controlled integrated deployment
   as the primary
   system under test for new system-security, information-flow, performance,
   resilience, artifact, and later proposed manuscript results. The completed
   D023 deployment then remains a supporting predecessor, and frozen evidence
   remains non-transferable. Begin collection only after the applicable P8/P9
   schema, identifier, positive-control, provenance, path, and output gate.
10. Implement and run P8+ work only from the self-contained
    `prototype_final/` D024 boundary. Root implementations, commands, and tests
    remain frozen historical/component controls and are not a second active
    development path.

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

- Approved: D001, D003, D005, D014, and D015 establish account-scoped
  bundle discovery, descriptor trust, three atomic CuePolicies, the immutable
  bundle layout, and an application-operated S3 namespace with an optional AWS
  S3 profile.
  D015 supersedes the personal-cloud-account and Google Drive choices in D002
  and D006.
- Approved: D004, D008--D010, D017, and D018 select the local provider-neutral
  admission profile, exact independence wording, local audit boundary, thin
  cross-platform UI direction, exact aPPSS recovery contract, and independent
  selectable Yi/aPPSS suites with paired 2-of-3 and later 3-of-5 profiles.
- Superseded: D018 replaces D007's asymmetric profile plan and D016's
  sole-aPPSS active-suite cutover while retaining frozen Yi compatibility and
  all D017 aPPSS primitives.

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
- D007--D010 originally preserved the Yi 2-of-3 baseline and selected aPPSS
  2-of-3 first,
  reserve independent-administration wording for actual independent operators,
  keep attempt control local/audit-only, and defer UI-framework choice until
  the client APIs are frozen.
- D017 authorizes the exact P1.2 profile but no manuscript wording. Final aPPSS
  identifiers and wire schemas remain a P5A.1 gate with canonical vectors.
- D018 supersedes D007's asymmetric topology plan and D016's sole-aPPSS
  cutover. Yi and aPPSS remain independent selectable suites, evaluated in
  paired 2-of-3 and later 3-of-5 profiles with one suite bound to each epoch.

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
  tests. D020 permits provisional internal mapping acceptance for chronology;
  D019 independent human confirmation of aPPSS, frozen Yi, and the LOCUS
  composition remains mandatory before manuscript/final reviewed release.
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

The user authenticates through the owner-approved D004 local
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

Status: `Complete`

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

Completion record (2026-08-01):

- `prototype/locus/enrollment_state.py` implements the P1.3
  `EnrollmentClientStateMachine` contract across the exact ordered P3.1 phase
  sequence. It retains only operation ID, phase, backup ID, and epoch.
- Transition events contain only an event ID, completed phase, and optional
  public backup/epoch binding. Exact event retries return the same state;
  event-ID reuse with different metadata, stale states, skipped/reordered
  phases, changed epoch bindings, incomplete publication, and post-completion
  advances fail closed.
- Threaded exact-retry tests converge on one result. Dataclass field audits and
  negative tests confirm that retry state has no field for keys, cues,
  passwords, suite state, shares, secrets, or credentials.
- P3.1 introduces no external serialization or protocol identifier and does
  not change enrollment transport, admission, frozen Yi behavior, evidence, or
  manuscript wording.
- The complete pinned repository gate passes with 206 Python tests (one
  intentional skip), 17 native Rust tests, the frozen Rust protocol vector,
  formatting, linting, strict typing, and source-boundary validation.

### P3.2 Implement authenticated enrollment transport

Status: `Complete`

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

Completion record (2026-08-01):

- `LOCUS-authenticated-enrollment-transport-v1` adds an exact initial-epoch
  enrollment route to the existing pinned mutual-TLS 1.3 party API. The
  authenticated coordinator delivers only one explicitly named recipient's
  package per request; the service verifies its local signer, frozen Yi suite,
  authorizer configuration, role, budget, parameters, and native state.
- `LOCUS-party-service-config-v2` starts party processes with public topology,
  local service/signing credentials, separate databases, and no suite secret
  state. Native holders receive their individual Yi state only through the
  authenticated route; authorizer-only parties receive an explicit null suite
  package. The v1 boot format remains readable for the frozen deployment.
- The route inherits bounded duplicate-free canonical JSON, exact certificate
  pinning, authenticated client roles, generic external errors, and durable
  idempotency bound to certificate, route, and canonical request body. Success
  returns only recipient, profile, and package digest; local audit retains the
  public configuration digest rather than suite state.
- A subprocess test starts clean services with separate SQLite files, performs
  exact retry, and rejects wrong-party state and changed-body key reuse.
  Post-stop inspection confirms each database contains only its own package.
  Existing endpoint, identity, malformed-body, unknown-route, and replay
  negatives remain applicable to the shared HTTP boundary.
- P5A must still implement D017 aPPSS server-local OPRF-key generation. P3.2
  creates no production aPPSS key, public admission, evidence result, or
  manuscript wording.
- The complete pinned repository gate passes with 207 Python tests (one
  intentional skip), 17 native Rust tests, the frozen Rust protocol vector,
  formatting, linting, strict typing, and source-boundary validation.

### P3.3 Specify the admission contract

Status: `Complete`

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

Completion record (2026-08-01):

- The provider-neutral binding is frozen as bounded canonical JSON under
  `LOCUS-admission-binding-v1`. It binds a 32-byte pseudonymous subject,
  backup, epoch, enumerated operation, audience, Ed25519 proof-key thumbprint,
  32-byte nonce, issuance/expiry with a 300-second maximum lifetime, issuer,
  profile, and operation-dependent object prefix.
- Recovery admits only `recovery_attempt` with no prefix. Storage admits four
  exact operations and derives one subject/backup-specific prefix; there is no
  listing operation or provider credential.
- The capability, client-proof, local-issuer, and replay identifiers are
  assigned with their exact validation semantics for P3.4. The client proof
  binds the signed capability to the exact service request; exact replay may
  return a stored result, while nonce reuse with changed work fails.
- A strict codec, JSON schema, and fixed digest/prefix vectors reject unknown,
  duplicate, noncanonical, cross-profile, malformed, overlong-lifetime, and
  wrong-prefix scopes before cryptographic work.
- `docs/threat-model.md` now covers replay and stolen-capability behavior,
  malicious admitted clients, cross-account/prefix use, false lockout, issuer
  compromise/unavailability, and pseudonymous scope/timing leakage. These are
  specified risks and requirements, not implementation or manuscript claims.
- The complete pinned repository gate passes with 210 Python tests (one
  intentional skip), 17 native Rust tests, the frozen Rust protocol vector,
  formatting, linting, strict typing, and source-boundary validation.

### P3.4 Implement local admission

Status: `Complete`

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

Completion record (2026-08-01):

- `LocalSyntheticAdmissionIssuer` authenticates an explicit allowlist of
  project-generated pseudonymous subjects and deterministically signs the
  exact P3.3 binding with Ed25519. It has no network or external identity-
  provider dependency and receives no cue, suite-state, recovery-secret, or
  final-success value.
- Each `LocalAdmissionVerifier` independently validates the issuer key and
  signature, exact expected binding, current time, client public-key
  thumbprint, sender signature, capability/nonce/request digests, and its own
  durable replay database. Exact retry returns the same grant; changed-request
  nonce reuse fails.
- `LocalAdmissionStorageGateway` independently checks the storage audience,
  exact operation, backup, epoch, derived object prefix, traversal, and
  request-bound proof before invoking its backend. Negative tests confirm the
  backend is untouched on wrong key or operation.
- Three separately stored authorizer verifier instances accept their own exact
  audiences and retain independent replay records. A separate gateway verifier
  implements the same contract without trusting an authorizer decision.
- Tests reject wrong subject, proof key, audience, operation, backup, epoch,
  prefix, signature, expiry, request, and nonce reuse. Replay databases contain
  only domain-separated digests, not raw subjects, capabilities, proofs, or
  requests. A fixed signature/proof vector freezes deterministic behavior.
- The local issuer is a research test double, not OIDC, multifactor
  authentication, production identity, or false-lockout prevention. It adds no
  recovery factor and changes no CuePolicy, suite, offline-oracle argument,
  retained evidence, or manuscript wording.
- The complete pinned repository gate passes with 217 Python tests (one
  intentional skip), 17 native Rust tests, the frozen Rust protocol vector,
  formatting, linting, strict typing, and source-boundary validation.

---

## P4 — Clean-client recovery and lifecycle

### P4.1 Refactor recovery into a stable state machine

Status: `Complete`

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

Completion record (2026-08-01):

- `StableRecoveryStateMachine` implements the P1.3 recovery contract across
  the exact ordered P4.1 sequence. Its retry state contains only operation,
  phase, recovery handle, authenticated backup identifier, and epoch.
- The backup/epoch binding is required immediately after descriptor
  verification and cannot change. Exact event retries converge; stale states,
  skipped/reordered phases, event-ID reuse, changed handles, and post-complete
  transitions fail closed.
- Transition events contain no cues, credentials, suite state, keys, secret
  values, or suite/AEAD success bit. The state machine is local to the client,
  so parties receive no final recovery or decryption outcome.
- `normalize_recovery_failure` collapses wrong-input and malformed secret-path
  failures to the same public `recovery rejected` boundary without copying
  internal exception text.
- P4.1 changes no bootstrap codec, recovery suite, admission protocol, retained
  evidence, or manuscript wording.
- The complete pinned repository gate passes with 223 Python tests (one
  intentional skip), 17 native Rust tests, the frozen Rust protocol vector,
  formatting, linting, strict typing, and source-boundary validation.

### P4.2 Implement Client A/Client B isolation

Status: `Complete`

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

Completion record (2026-08-01):

- `LOCUS-clean-client-isolation-v1` defines an exact Client B surface containing
  only the authenticated public recovery configuration, installed CA, and a
  fresh recovery-only transport certificate/key. Client B receives recovery
  input transiently over standard input; neither it nor the recovered key is
  persisted or printed.
- A synthetic Client A provisions five separate P3.2 party processes, three
  holding recipient-specific Yi state. The processes are stopped, Client A's
  complete credential root is removed, and the parties restart with a distinct
  Client B identity before recovery.
- Client B runs as a separate sanitized-environment subprocess, reads no party
  database or Client A path, and recovers through an authenticated 2-of-3
  subset. It emits only a private-key SHA-256 oracle and Ed25519 public-key
  fingerprint; both exactly match values recorded outside LOCUS at enrollment.
- The isolation audit requires the exact four-file Client B allowlist, rejects
  symlinks/special files, requires Client A's root to be unavailable, and scans
  for the synthetic private key, Client A credential, recovery input, and every
  party state. A deliberately added inherited-state file fails the gate.
- The scenario consumes already authenticated public recovery configuration;
  P2.2 separately verifies how a clean client obtains that configuration from
  the signed pointer/bundle and party-current quorum. This phase does not claim
  forensic erasure, independent administration, or production process
  isolation and changes no retained evidence or manuscript wording.

### P4.3 Complete post-recovery successor publication

Status: `Complete`

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

Completion record (2026-08-01):

- `LOCUS-successor-publication-journal-v1` durably binds one operation to the
  predecessor/successor epochs and exact configuration, backup, descriptor,
  and recovered-key digests. The journal contains no protected-key bytes,
  recovery input, suite secret, wrapping key, party state, or authorization
  credential.
- The coordinator orders original-key identity preservation, party
  preparation, immutable backup publication, authenticated descriptor/current
  publication, readiness, prepared-successor recovery verification, certified
  activation, predecessor-retirement confirmation, and the explicit optional
  rotation choice. The default path preserves the recovered original key and
  performs no key rotation.
- Every external action receives a deterministic binding-and-phase
  idempotency key. Reopening the SQLite journal resumes the exact action;
  changing any bound digest or epoch under the same operation identifier fails
  before another authorization or publication.
- The existing `LOCUS-epoch-lifecycle-policy-v1` party operation intentionally
  activates the successor and retires the predecessor atomically. P4.3 first
  verifies recovery from the prepared successor package while the predecessor
  remains authorized, then performs that atomic switch; its logical retirement
  step confirms/retries the certified result rather than creating a second
  non-atomic party transition.
- Synthetic crash injection after each of the nine effect boundaries, including
  an explicitly selected rotation path, leaves an authorized predecessor or
  successor recoverable and resumes with exactly one activation and retirement
  confirmation. The ordinary no-rotation path, secret-free journal property,
  changed-binding rejection, and wrong-key early failure are separate tests.
- This is a component-level orchestration and deterministic failure result over
  the existing same-membership lifecycle/storage interfaces. It does not add
  general replacement, coordinated rollback resistance, external-provider
  evidence, or manuscript wording.

### P4.4 General party replacement

Status: `Deferred`

D011 approves deferral until after the selectable-suite and paired-profile work.
Begin only if a later owner decision authorizes implementation after those
gates.

Acceptance:

- Old-quorum authorization, new-recipient provisioning, new-threshold readiness,
  descriptor update, activation, and retirement are all bound to one successor
  configuration.

---

## P5 — CuePolicy and resolver generality

### P5.1 Wrap the existing policy without semantic change

Status: `Complete`

Acceptance:

- All v1 canonical bytes and errors are unchanged.
- Frozen Yi TPASS input and backup vectors remain unchanged. Each new policy's
  canonical bytes enter a recovery suite only through that suite's separately
  versioned password-input domain.
- Existing resolver-drift vectors pass through the new interface.

Completion record (2026-08-03):

- `FROZEN_LOCATION_PERSON_POLICY` exposes the existing implementation through
  the typed `CuePolicy` interface while retaining
  `canonical_recovery_input` as the byte-frozen compatibility implementation.
- Deployment provisioning/recovery, lifecycle successors, the synthetic
  walkthrough, and the deterministic resolver now obtain canonical bytes only
  through the frozen adapter.
- Corpus regression compares adapter and compatibility-function bytes and exact
  error messages. Frozen cue, Yi, backup, deployment, resolver-drift, and
  walkthrough tests remain unchanged and pass.
- No identifier, password domain, backup format, suite behavior, retained
  evidence, or manuscript wording changed.

### P5.2 Design three atomic policies

Status: `Complete`

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

Completion record (2026-08-03):

- `docs/CUE-POLICY-PROFILES.md` freezes exact accepted shapes, lexical and
  length bounds, cardinality, canonicalization, ordering, duplicate behavior,
  top-level encodings, resolver behavior, privacy disclosure, and non-claims.
- The coordinate policy reuses the frozen decimal/half-even interpretation
  without changing the composite policy. Phone and email use strict bounded
  direct-input grammars with no inference or external lookup.
- Exact policy and member-order names plus `LOCUS-no-resolver-v1` are reserved,
  not assigned or accepted. P5.3 assigns them only with implementations,
  canonical vectors, and registry tests.
- Suite-specific password-input domains remain separate: P5 does not
  reinterpret the frozen Yi/composite input or assign the future aPPSS domain.

### P5.3 Build a shared conformance corpus

Status: `Complete`

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

Completion record (2026-08-03):

- Three independent atomic policy adapters and an exact four-policy registry
  implement the P5.2 contracts through the existing `CuePolicy` interface.
- `CuePolicyMetadata` publicly declares each policy's exact input category,
  input shape, cardinality, resolver profile, ordering domain, ambiguity rule,
  and duplicate rule without containing cue-derived data.
- `cue-policy-conformance-v1.json` pins canonical JSON, bytes, SHA-256 digests,
  exact local errors, order invariance, length/Unicode/locale/punctuation/case
  behavior, post-canonicalization duplicates, and cross-policy rejection.
- The existing resolver-drift corpus continues through the frozen policy
  adapter; direct atomic policies have no provider drift because P5.4 binds
  them to `NoResolver`.
- A consumer test that imports no LOCUS implementation independently checks
  the canonical JSON/hex/digest triples. The frozen v1 corpus hash and every
  frozen policy vector remain unchanged.
- The three policy identifiers and conformance-corpus identifier are assigned
  with their implementations and vectors. `LOCUS-no-resolver-v1` remains
  protected but unimplemented until P5.4.
- The complete gate passes on Windows and in a fresh isolated Ubuntu clone of
  commit `87540e2`: 239 Python tests, 17 Rust tests, the fixed Yi vector,
  formatting, linting, typing, and repository-boundary checks. The temporary
  Linux clone and downloaded toolchain shim were removed after verification.

### P5.4 Formalize resolver adapters

Status: `Complete`

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

Completion record (2026-08-03):

- The frozen `DeterministicResolverAdapter` and resolver-drift corpus remain
  unchanged and continue to feed only the frozen composite policy.
- `NoResolverAdapter` binds one exact direct-input policy at construction,
  invokes it once, and returns its exact policy identifier/canonical bytes under
  `LOCUS-no-resolver-v1` without lookup, enumeration, inference, or retry.
- The adapter accepts only the three P5.3 atomic policies. Unknown policies and
  the resolver-backed frozen composite policy fail before input processing;
  malformed or multi-candidate values produce one generic local failure.
- The pinned NoResolver vector binds all three accepted policy/digest pairs and
  the rejected resolver-backed policy. Existing resolver-drift and frozen
  policy vectors remain byte-identical.
- No external location-provider adapter or execution is authorized, and no
  resolver result is treated as entropy, usability, or security evidence.

---

## P5A — Independent selectable Yi TPASS and aPPSS suites

Direction: `Approved` by D017 and D018
Execution status: `Complete`

Independent human confirmation under D019 remains a mandatory
pre-manuscript/pre-release gate; it does not change the implementation status.

This phase begins only after P1 has frozen the suite-neutral contract, P2 binds
the suite in authenticated recovery metadata, P3 supplies authenticated
enrollment, P4.1--P4.3 supply recovery and successor state machines, P5 has
shown that CuePolicy is independent of the recovery suite, and D017 is
approved. P4.4 general membership replacement is not a prerequisite.

For this phase, Yi TPASS and aPPSS independently implement the same
password-protected recovery-secret interface. New enrollment explicitly selects
either suite. Recovery follows the suite authenticated by the epoch descriptor
and cannot override it or try another suite. A fresh successor epoch may keep
the current suite or explicitly switch in either direction after recovering the
same protected key client-side. One epoch contains exactly one suite. There is
no in-place state conversion, dual-suite fallback, automatic downgrade, or
reinterpretation of an old identifier, backup, vector, or evidence record.

Both suites feed their native high-entropy output `S_R` into the same existing
HKDF-SHA-256 and AES-256-GCM path. Protected-key generation/import, key identity,
storage, bootstrap, admission, lifecycle, and common test orchestration remain
suite-neutral. Paired evaluation runs Yi and aPPSS first at `k=2,n=3` and later
at `k=3,n=5` under matching policy, key, authorization, storage, topology,
failure-schedule, and measurement conditions. Intrinsic suite operations and
security properties remain distinct.

### P5A.1 Freeze the exact aPPSS profile and formats

Status: `Complete`

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
  optional verifiable-OPRF robustness sketch;
- new bounded canonical wire and state formats, with no serializable client
  blinder or secret-bearing debug/log representation; and
- an authenticated suite-selection/profile field that fixes exactly one suite,
  `k`, `n`, holder membership, and authorization topology for the epoch.

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
- The selector offers Yi and aPPSS for new enrollments but is not consulted as
  a fallback during recovery.

Completed 2026-08-03: `docs/APPSS-WIRE-FORMAT.md` assigns the exact suite,
2-of-3 profile, OPRF, password-domain, state, message, selector, backup-v5, and
associated-data identifiers with strict schemas, byte limits, typed failures,
canonical public structural vector, and an independent consumer. The existing
RecoveryDescriptor v1 remains suite-neutral and binds the exact aPPSS public
state without a schema change. The selector format permits exactly one suite;
its implementation/release remains P5A.3--P5A.5.

### P5A.2 Implement the native aPPSS core

Status: `Complete`

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
- The shared conformance harness runs against both independent adapters without
  importing one suite's native state or messages into the other.

Completed 2026-08-03: the separate `locus-appss-core` crate implements RFC
9497 OPRF-mode ristretto255/SHA-512, independent per-server key lifecycle,
canonical nonidentity group decoding, GF(2^128) Shamir setup/interpolation,
share masking, commitment verification, and direct 16-byte `S_R` derivation.
It has strict native codecs, redacted secret types, zeroization where supported,
production `OsRng` at the binding, and deterministic randomness only in native
tests. Eight unit tests plus the public fixed-vector integration test cover the
official RFC vector, every 2-of-3 subset, internal 3-of-5 generality, wrong
input, malformed/altered/trailing state, identity, duplicate, range, context,
and direct-versus-oblivious evaluation. The narrow PyO3 boundary exposes only
separate `Appss*` objects/functions; its centrally orchestrated initialize and
recover functions are explicitly named fixtures and are not distributed-
initialization evidence. Frozen Yi source and vectors remain unchanged.

### P5A.3 Integrate the generic client and party protocol

Status: `Complete`

Actions:

- add a narrow PyO3 binding and register Yi and aPPSS as distinct
  `PasswordProtectedSecretRecovery` adapters;
- add an explicit suite registry/selector used at enrollment and successor
  creation, while recovery dispatches only from authenticated descriptor state;
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
  processes for both selected suites under the paired profile.
- No coordinator or provisioner persists all OPRF keys, and each server creates
  and retains only its own key.
- Cross-suite substitution and automatic downgrade fail before
  secret-dependent recovery.
- Selecting Yi or aPPSS changes only the suite adapter and suite-bound
  state/messages; the protected-key, HKDF, AES, storage, and client-state
  interfaces remain common.

Completed 2026-08-03: `AppssRecoveryAdapter` and the frozen
`YiTpassRecoveryAdapter` are independently registered behind the suite-neutral
contract. New-epoch selection is explicit; recovery lookup accepts only the
authenticated suite identifier and has no fallback. Backup v5 carries either
suite's opaque public state through the same HKDF-SHA-256/AES-256-GCM and
protected-key interfaces. The separate aPPSS client emits only the P5A.1
request/response formats, maintains its blinder in transient native state, and
normalizes wrong input and remote protocol failure. Each durable holder creates
and stores only its own OPRF key in a separate SQLite database; authorization
metadata is committed before the first OPRF evaluation, exact request retry
returns the stored response after restart, changed reuse fails, and partial
public-state installation is not ready. A pinned mutual-TLS 1.3 route with
explicit client/server certificate fingerprints exercises correct and
wrong-input recovery across three distinct subprocesses and recipient
databases. Cross-suite selection/substitution fails before recovery dispatch.
The new route and database use only the already assigned P5A.1 request,
response, pending-state, party-state, install, and ready formats; no deployment
or evidence identifier is assigned. Frozen Yi source, vectors, backup v4,
deployment, and retained v2 evidence remain unchanged.

### P5A.4 Integrate authenticated initialization

Status: `Complete`

Use P3's enrollment transport so the client performs the approved OPRF
initialization with each authenticated server and distributes the common
`omega=(e,C)` record under exact recipient, suite, backup, epoch, policy,
membership, threshold, and configuration bindings. The existing networkless
central provisioner may remain only as a frozen Yi compatibility path or
generated test fixture; it cannot support an aPPSS distributed-initialization
claim.

Acceptance:

- Wrong server, recipient, suite, epoch, body, replay, and idempotency reuse
  fail closed.
- Each ready party proves possession of the exact bound state without exposing
  its OPRF key or a cue verifier.
- Initialization interruption cannot activate a partially provisioned epoch.

Completed 2026-08-03: the transient aPPSS client now performs the production
initialization algorithm through three certificate-pinned mutual-TLS party
processes. Each clean process receives only public epoch configuration, derives
and verifies the exact suite context over backup, epoch, CuePolicy, membership,
threshold, configuration, and certificate identity, and creates its own OPRF
key only after an authenticated initialization request arrives. The client
collects the three blinded OPRF results, creates `omega=(e,C)` with production
CSPRNG use, distributes the exact common public state, verifies every bound
ready acknowledgement, and returns the high-entropy recovery secret only after
all holders are ready. No server key crosses the process boundary.

The `/v1` initialization and state-install routes reuse the already assigned
P5A.1 request, response, install, and ready objects. Their HTTP idempotency
records durably bind the authenticated caller certificate, exact route, and
body digest before protocol dispatch; exact completion survives restart,
whereas changed caller/route/body reuse conflicts. Tests reject wrong server,
recipient, suite, context/epoch, route, body, replay, and install transcript.
An injected third-holder install interruption returns no initialization result
and leaves only non-activated holder-local pending/installed state; descriptor
and lifecycle activation remain P5A.5. The networkless central initializer
remains fixture-only and supplies no distributed-initialization evidence.

### P5A.5 Implement suite selection and successor switching

Status: `Complete`

Selection and switching procedure:

1. For a new enrollment, explicitly select Yi or aPPSS and bind that suite and
   profile to the authenticated descriptor before suite setup.
2. For a successor, recover the protected key client-side through the exact
   predecessor suite, then explicitly retain that suite or select the other.
3. Create fresh selected-suite recovery state, backup, descriptor, and epoch;
   never translate, reuse, or combine predecessor suite state.
4. Durably prepare and verify every required party, storage object, bundle,
   descriptor, and current-state binding.
5. Recover the same protected-key identity through the prepared successor,
   activate it through the P4 lifecycle protocol, and only then retire the
   predecessor.

Acceptance:

- Crash and exact retry are tested at every transition.
- Old and new state never combine into a threshold result.
- Recovery never silently falls back from its descriptor-bound suite.
- New enrollment supports both Yi and aPPSS only after the complete P5A
  acceptance gate; suite choice is explicit and persisted as authenticated
  public configuration.
- Same-suite Yi-to-Yi and aPPSS-to-aPPSS successors and explicit Yi-to-aPPSS
  and aPPSS-to-Yi successors preserve the protected-key identity and create
  fresh independent suite state.

Completed 2026-08-03: the selector registry now drives an explicit
suite-neutral epoch factory that accepts exactly one Yi or aPPSS choice, creates
fresh selected-suite state, seals backup v5 through the common HKDF/AES path,
and emits one signed RecoveryDescriptor v1 and deterministic recovery bundle.
Recovery authenticates the bundle first, dispatches only from its exact suite
identifier, and never consults the enrollment selector or another adapter as a
fallback. Yi retains its frozen context-password derivation including nonce,
backup identifier, and epoch; aPPSS uses its separate context-bound password
domain and distributed holder runtime.

Successor preparation first recovers the protected key through the predecessor
suite client-side, then creates a fresh consecutive epoch under an explicit
same-suite or cross-suite selection. Yi freshness is checked on its secret
party states; aPPSS freshness is checked on its context-bound public state and
new holder keys. The successor descriptor binds the predecessor descriptor
digest, and prepared recovery must reproduce the original protected-key digest
before activation. The existing P4.3 durable publication journal binds every
effect through the successor backup/configuration/descriptor digests. Tests
exercise Yi-to-Yi, aPPSS-to-aPPSS, Yi-to-aPPSS, and aPPSS-to-Yi, reject mixed
old/new Yi state, mixed old/new aPPSS endpoints, and all cross-suite state, and
resume after an injected crash following every selected publication effect
without double activation or retirement. The journal contains neither the
canonical recovery input nor protected-key bytes. This is a prepared component
path. D020 later activates it at the application/component boundary. The frozen
Yi-only Compose deployment remains unchanged until P6 assigns paired profiles.

### P5A.6 Validate the comparative security boundary

Status: `Complete`

Add fixed, bounded, synthetic scenarios for:

- cloud-only aPPSS state;
- every evaluated coalition below reconstruction threshold `k`;
- matching cloud plus below-threshold aPPSS state;
- exact-threshold and all-server aPPSS state;
- a fixed Yi comparator showing that `k` serialized Yi party states directly
  reconstruct the shared password scalar and high-entropy recovery secret,
  while `k` aPPSS states expose an offline dictionary-test capability and
  reveal `S_R` only after the fixed correct candidate; and
- matched Yi/aPPSS `2-of-3` rows first and `3-of-5` rows after P6.3, using the
  same synthetic key/cues, CuePolicy, authorization quorum, storage, topology,
  failure schedule, and metric definitions within each pair.

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
- Comparison processors may pair matched rows but retained evidence remains
  separately versioned by suite and topology.

Completed 2026-08-03: `LOCUS-recovery-suite-compromise-regression-v1` now
defines a strict, aggregate-only, non-retained development report for the
matched 2-of-3 pair. Its zero-argument evaluator generates one fixed synthetic
CuePolicy/key/topology/authorization/storage profile in memory, uses independent
suite password domains, and writes no view or result. For each suite it checks
cloud-only, all four below-threshold coalitions, and every matching
cloud-plus-coalition view under a socket-forbidden test boundary. A transient
direct-verifier injection supplies the positive control; ordinary views expose
no tested predicate through the bounded interface.

All three exact-threshold subsets and the all-server view are evaluated. The Yi
comparator validates and parses the frozen canonical party wire without changing
the Yi core, interpolates its shared input scalar, protected exponent, and
digest, and verifies ordinary recovery without testing a dictionary. The aPPSS
comparator uses exactly the compromised serialized OPRF keys and public state
locally against two fixed transient inputs: the incorrect input releases no
output and the correct input reproduces `S_R`. The report retains only aggregate
Booleans/counts/categories and its common-condition digest; it rejects altered
conditions, extra fields, unsafe output, or per-input/raw-state retention. The
methodology explicitly limits this to implementation regression rather than a
proof of either inherited construction, retained P9 evidence, or a 3-of-5
result.

### P5A.7 Complete selectable-suite documentation and review gates

Status: `Complete`

Independent human validation remains a mandatory pre-manuscript/pre-release
gate under D019/D020.

Actions:

- pass clean Linux and Windows builds and the complete legacy-regression gate;
- collect no retained performance corpus until P9 freezes a new methodology
  and result schema;
- update active architecture, protocol, threat, information-flow, lifecycle,
  API, storage, evidence, artifact, and version documentation at suite release;
- perform D020's explicitly non-independent internal
  paper-to-specification-to-code assessment for both frozen Yi TPASS and aPPSS,
  provisionally classify every deviation, and retain D019's independent human
  confirmation as a later mandatory gate before manuscript reliance or final
  reviewed release;
- prepare a replacement for superseded M-APPPSS-001 that describes selectable
  paired suites, but do not edit `paper/` until the replacement change set has
  separate owner approval and the P8/P9 evidence gates are complete.

Acceptance:

- Frozen Yi regression and retained-v2 verification remain unchanged.
- The selectable-suite release commit, selector/profile identifiers,
  clean-host results, review findings, and known limitations are recorded.
- The internal assessment provisionally accepts or explicitly qualifies the Yi
  mapping, the aPPSS mapping, the two below-threshold claim boundaries, both
  distinct reconstruction-threshold compromise outcomes, and the common LOCUS
  composition, with no unresolved claim-blocking or correction-required item.
  Independent human confirmation remains required under D020.
- Yi remains available for new enrollment alongside aPPSS; neither suite is a
  fallback for an epoch enrolled under the other.
- Manuscript wording remains unchanged unless a new D018--D020-aligned exact change
  set is explicitly approved and later applied under P10.6.

Implementation note (2026-08-03): the P5A.1--P5A.6 implementation candidate
passed a disposable clean Linux complete gate at `8795947`. A fresh Windows
checkout then exposed line-ending conversion in three frozen/public vector
digest tests; commit `36ea1fe` fixed checkout policy only, without changing any
vector or expected digest, and a second fresh empty-cache Windows checkout
passed all 279 Python tests (one expected live-provider skip), both native
suite/vector gates, formatting, lint, typing, and repository-boundary checks.
No retained performance/evidence corpus was collected. D019 now scopes the
external gate as a claim-focused review rather than a full production
cryptographic audit. The attributable review packet is ready in
`docs/RECOVERY-SUITE-MAPPING-REVIEW.md`, its deviations register is in
`docs/RECOVERY-SUITE-DEVIATIONS.md`, the release checklist is in
`docs/P5A7-RELEASE-READINESS.md`, and draft
M-SELECTABLE-SUITES-001 replaces the stale sole-active-aPPSS proposal without
authorizing or applying any `paper/` change. D020 records the owner's decision
to use a rigorous but explicitly non-independent internal assessment to close
P5A implementation chronology while deferring independent human validation.
The internal assessment in `docs/P5A7-INTERNAL-MAPPING-ASSESSMENT.md`
provisionally accepts Yi, aPPSS, and the outer composition with required
qualifications; every deviations-register entry is provisionally classified
and no claim-blocking or correction-required item remains. The already
implemented exact selector, authenticated descriptor dispatch, and
four-direction successor interface are active application components with no
fallback. The frozen Yi-only Compose profile and retained v2 evidence remain
unchanged; the exact paired deployment identities and profiles were assigned
later by P6.3. No
retained P9 corpus or manuscript change was made. A qualified independent human
must confirm the mapping before manuscript reliance, a final reviewed release,
or submission.

---

## P6 — Storage providers and deployment profiles

### P6.1 Extend storage conformance

Status: `Complete`

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

Completion record (2026-08-03):

- `LOCUS-storage-provider-profile-v1` composes the distinct backup,
  descriptor, recovery-bundle, and current-pointer roles without merging their
  formats or mutability rules. Its filesystem and S3-compatible provider IDs
  remain explicit.
- One shared provider-level conformance function now runs unchanged against
  both adapters. It covers immutable backup and descriptor publication, exact
  retry/read, canonical bundle preservation, current-pointer create/CAS/stale
  outcomes, bounded/digest-bound decoding inherited from the component
  contracts, explicit failure classes, and zero required list operations.
- Nonlocal provider properties fail closed unless the transport is TLS. The
  S3-compatible provider uses an explicitly constructed client and
  prefix-scoped credential mode; the filesystem provider is local and
  credential-free. Plain HTTP remains an explicit local-test-only exception.
- This phase adds no provider credential, real-provider execution, retained
  evidence, deployment claim, or manuscript wording. P6.2 places the admitted
  application gateway above this provider boundary.
- The complete pinned gate passes with 283 Python tests (one intentional
  live-provider skip), 8 aPPSS core tests plus its fixed vector, 17 Yi core
  tests plus its frozen vector, native formatting/Clippy, Python formatting,
  linting, strict typing, syntax, and repository-boundary validation.

### P6.2 Add one distinct provider adapter

Status: `Complete`

The reproducible implementation is complete. Separately authorized live AWS
validation remains an optional open supplemental gate.

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

Completion record (2026-08-03):

- `LOCUS-storage-provider-aws-s3-v1` is a TLS-only AWS specialization of the
  P6.1 provider contract. Construction requires explicit application-side
  access key, secret key, optional session token, region, bucket, and exact
  prefix; there is no custom endpoint or ambient credential discovery.
- `LOCUS-application-storage-gateway-v1` executes backup create/read/delete,
  descriptor create/read, bundle create/read, and current-pointer read/CAS only
  after the existing P3.4 verifier accepts a short-lived subject/backup/epoch/
  prefix/operation/proof-key/nonce/expiry-bound capability and client proof.
  Logical keys redundantly bind every immutable digest and bundle length.
- `LOCUS-storage-pointer-cas-v1` strictly transports the optional expected and
  required replacement pointer. The backend verifies the replacement's backup
  and epoch before delegating to the existing exact-byte/ETag CAS contract.
- The generated AWS data-plane policy is bucket/prefix-scoped, TLS-conditioned,
  and contains only exact object Get/Put/Delete permissions; it grants no list
  operation. Clients receive neither this policy nor any AWS credential.
- Fake-S3 tests cover all four logical roles through real D004 capability and
  proof validation, exact retries/reads, stale CAS, cross-account rejection
  before backend access, zero list calls, TLS/profile properties, explicit
  session-token forwarding, and credential-safe object representations.
- A second opt-in test provides a read-only AWS TLS/connectivity gate. It is
  skipped by default and must not run without separate authorization and a
  disposable synthetic research account. No live AWS result, provider
  credential, retained evidence, or manuscript wording is included here.
- The complete pinned gate passes with 288 Python tests (the local S3 and AWS
  external-service gates are the two intentional skips), 8 aPPSS core tests
  plus its fixed vector, 17 Yi core tests plus its frozen vector, native
  formatting/Clippy, Python formatting, linting, strict typing, syntax, and
  repository-boundary validation.

### P6.3 Generalize threshold configuration

Status: `Complete`

Support:

- paired deployed Yi/aPPSS 2-of-3 profiles;
- paired deployed Yi/aPPSS 3-of-5 profiles;
- explicit recovery-suite identity and user-selectable enrollment profile,
  with exactly one suite authenticated per epoch;
- distinct authorization quorum for each profile;
- exact consistent threshold subset selection;
- satisfiable and unsatisfiable availability cases.

Acceptance:

- End-to-end deployment tests exist for every claimed profile.
- Within each paired topology, both suites use the same CuePolicy, synthetic
  protected key, authorization topology/quorum, storage, admission, network
  schedule, and measurement definitions.
- Local scaffold tests alone are not treated as deployment evidence.

Completion record (2026-08-03):

- D021 is implemented as two exact comparison-control profiles:
  `LOCUS-paired-suite-deployment-2of3-v1` and
  `LOCUS-paired-suite-deployment-3of5-v1`. Each holds constant the direct
  canonical-email CuePolicy, NoResolver path, synthetic protected-key
  interface, five authorizers, independent 4-of-5 authorization quorum, local
  synthetic admission, filesystem provider, network schedule, and measurement
  definitions for the Yi and aPPSS arms.
- Selector v1 remains exact 2-of-3. `LOCUS-recovery-suite-selector-v2`
  authenticates the matched 2-of-3/3-of-5 matrix and still binds exactly one
  suite to an epoch with no fallback. It rejects suite/profile/topology,
  holder-membership, authorizer-membership, and quorum mismatches.
- Frozen Yi native wire/state is unchanged. The 3-of-5 Yi profile receives the
  distinct label `LOCUS-TPASS-YI-3of5-v1` because the existing native wire
  already carries and checks `(k,n)`.
- Frozen aPPSS v1 remains exact 2-of-3. The 3-of-5 aPPSS profile receives
  separate public/pending/party/request/response/install/ready/client-session
  v2 formats, strict schema, and public-only topology vector; no v1 object is
  reinterpreted.
- Backup v6/AAD v3 preserve the same suite-output to HKDF-SHA-256 to
  AES-256-GCM protected-key path while permitting only the four exact
  suite/topology/profile/public-format combinations. Exact-threshold recovery
  succeeds and below-threshold recovery rejects for every arm.
- The aPPSS deployment test starts five distinct pinned-mTLS processes, each
  generating and storing only its own OPRF key, requires all five ready
  acknowledgements for initialization, and recovers through the non-contiguous
  exact subset `[1,3,5]`. The Yi 3-of-5 test starts five native-holder plus
  authorizer processes, obtains a separate 4-of-5 authorization certificate,
  and recovers through `[1,3,5]`; two responses cannot aggregate.
- The pre-existing authenticated Yi and aPPSS 2-of-3 process tests remain the
  matching first-topology deployment paths. These tests are same-host process
  conformance, not retained P9 evidence, multi-host behavior, or independent
  administration. The frozen Compose profile and retained v2 corpus remain
  unchanged.
- The complete pinned gate passes with 298 Python tests (the local S3 and AWS
  external-service gates are the two intentional skips), 8 aPPSS core tests
  plus its fixed vector, 17 Yi core tests plus its frozen vector, native
  formatting/Clippy, Python formatting, linting, strict typing, syntax, and
  repository-boundary validation.

### P6.4 Move parties to separate hosts

Status: `Blocked`

Same-host configurable staging is complete. The actual host-separation
objective is blocked until suitable multi-VM or multi-host infrastructure is
available.

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

Readiness record (2026-08-03):

- `docs/P6.4-HOST-SEPARATION.md` records the exact execution checklist and the
  workstation capability audit. Docker Desktop runs through one engine/VM;
  WSL has one Ubuntu distribution plus Docker Desktop. No Multipass, Vagrant,
  Hyper-V PowerShell, QEMU, VirtualBox, or VMware CLI is available.
- Additional Docker containers or WSL distributions would remain one-host
  isolation and are deliberately not relabeled as P6.4 evidence.
- P6.4 can resume without a protocol decision once five disposable local VMs
  or five disposable network hosts containing synthetic state are available.
  Tier 3 remains separately dependent on genuine independent operators.
- No P6.4 deployment result, retained evidence, or manuscript change is
  claimed.
- `LOCUS-party-endpoint-setup-v1` now provides one strict secret-free file for
  party IDs 1--5, advertised DNS/IP hosts, and ports. The checked-in default
  runs all five party containers through the existing internal recovery
  network; a separate synthetic example shows the five fields to replace when
  hosts become available.
- The endpoint setup drives the certificate SAN, client directory, native peer
  directory, and listener port from one validated value. A read-only Compose
  overlay and `deployment-configurable-smoke` command exercise the complete
  same-host graph without modifying the frozen Compose file or deployment
  identifier.
- The future five-host setup mode rejects repeated, loopback, link-local,
  unspecified, multicast, noncanonical, uppercase, or structurally invalid
  addresses. Selecting that mode remains configuration intent only; actual
  placement and the tier validation above are still required.
- The configurable same-host smoke completed on 2026-08-03: all five parties
  became healthy, correct/restart/one-party-unavailable recovery passed, output
  scanning passed, and all disposable containers, networks, and volumes were
  removed. The container image now explicitly includes both native suite
  crates. This closes local staging only and does not advance the demonstrated
  P6.4 tier.

---

## P7 — User interface

### P7.1 Freeze client APIs before UI implementation

Status: `Complete`

Acceptance:

- Enrollment and recovery complete through CLI/API tests.
- No UI framework contains a second canonicalizer or protocol implementation.

Completion record:

- `LOCUS-client-api-v1` exposes typed catalog, transient policy preview,
  enrollment, bootstrap, recovery, successor, and aggregate inspector
  operations over the existing component boundaries.
- Tests cover Yi/aPPSS at both 2-of-3 and 3-of-5, exact imported synthetic-key
  recovery, descriptor-only suite dispatch, local admission, all four policy
  previews, cross-suite successor creation, wrong-input normalization, and
  safe inspection.
- Recovery has no suite-override field. Normal results pass the existing
  output-safety validator; protected-key bytes remain non-serializing typed
  return data and are absent from object representations.
- The facade is same-process component conformance, not P6 deployment or
  retained evidence. No UI framework was selected until this gate passed.

### P7.2 Implement enrollment UI

Status: `Complete`

Screens:

- generate/import synthetic protected key;
- show public fingerprint;
- select an approved Yi or aPPSS enrollment profile;
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

Completion record:

- D022 selects `LOCUS-local-research-ui-v1`: semantic HTML, local CSS and
  JavaScript, and the pinned Python loopback server over the frozen client API.
  There is no third-party runtime, remote asset, browser persistence,
  telemetry, service worker, request logging, or UI-side canonicalizer.
- Enrollment requires an explicit Yi/aPPSS suite, preconfigured 2-of-3 or
  3-of-5 holder profile, and registered policy. It supports synthetic key
  generation/import, transient API-produced normalized preview, public
  fingerprint, public receipt export, redacted role placement, and input
  clearing after success and page teardown.
- Source guards and strict HTTP tests enforce the no-persistence/no-telemetry
  boundary. Browser checks confirmed transient cue/key clearing and responsive
  desktop/mobile presentation. The application produces no retained
  screenshot; browser/OS capture remains outside its control and is documented
  as a limitation.

### P7.3 Implement recovery UI

Status: `Complete`

Screens:

- clean-client bootstrap;
- LOCUS admission/identity authentication and short-lived storage capability;
- descriptor retrieval and validation;
- enrolled policy display;
- cue entry and validation;
- generic online recovery progress;
- recovered public-fingerprint verification;
- successor enrollment with an explicit same-suite or other-suite choice; and
- optional protected-key rotation as a separate choice.

Acceptance:

- The UI cannot silently change policy, epoch, party membership, or endpoint
  trust.
- Recovery displays and uses the authenticated enrolled suite; it cannot offer
  another suite as a retry or fallback.
- Errors match the approved information boundary.

Completion record:

- Recovery starts from the public receipt and calls authenticated bootstrap
  before cue entry. The authenticated suite, policy, epoch, holder threshold,
  and separate 4-of-5 authorization quorum are displayed; the recovery form
  contains no suite, policy, membership, or endpoint override.
- The client API performs local proof-key admission, descriptor/bundle/pointer
  validation, exact suite dispatch, recovery, decryption, and public-key
  identity verification. The UI displays generic busy/rejection status and
  only the verified public fingerprint on success.
- Successor preparation appears only after recovery and requires an explicit
  suite, 2-of-3/3-of-5 profile, and independent protected-key rotation choice.
  It uses the existing lifecycle path and exports a new public receipt.
- Application and browser checks covered clean bootstrap/recovery and a
  Yi-to-aPPSS successor. This is local component conformance, not public
  admission, external provider behavior, retained evidence, or usability.

### P7.4 Implement researcher state inspector

Status: `Complete`

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

Completion record:

- The inspector accepts only a public receipt and calls the frozen client API's
  recursive safe inspection. It renders role placement, public identifiers,
  safe digests, fixed message categories, and aggregate byte/item counts.
- The result omits raw/canonical cues, password input, suite-private state,
  recovery/wrapping/protected-key bytes, and credentials. Normal results pass
  the existing recursive public-output validator.
- Full application tests cross-check the inspector against an enrolled record
  and scan its JSON for synthetic cue and key markers. Live browser inspection
  displayed the same safe categories with no warning/error output.
- P7 changes active implementation documentation and component-conformance
  records only. It creates no P8/P9 retained corpus and makes no manuscript
  change.

### P7.5 Construct the primary integrated reference system

Direction: `Approved` by D023

Execution status: `Complete`

P7.5 composes the already implemented UI,
client API, admission, descriptor/bootstrap, provider gateway, resolver,
recovery-suite, party, and lifecycle components into one new system. It does
not modify the frozen Yi-only Compose profile or reinterpret any retained v2
result. See `docs/INTEGRATED-REFERENCE-SYSTEM.md`.

The reproducible target is one same-host Docker Compose graph. The browser
remains outside Docker and reaches only a host-loopback endpoint served by an
ephemeral UI/client-gateway container. The gateway preserves
`LOCUS-client-api-v1` but replaces the current in-memory record backend with
authenticated remote-service adapters. The graph contains:

- UI/client API gateway;
- project-controlled local synthetic admission/capability service;
- operator/discovery and descriptor/pointer/receipt signing service;
- application storage gateway;
- local S3-compatible backup/descriptor/bundle/current-pointer store;
- resolver service for the frozen resolver-backed policy;
- five authenticated authorizer/recovery-party services; and
- a networkless bootstrap role limited to generated service credentials,
  public configuration, empty role roots, and synthetic fixtures.

The active enrollment path may not inject native suite state or client secrets
through direct volume writes. Each aPPSS holder generates and retains only its
own key; all Yi state is delivered only to its authenticated recipient. Client
A and Client B use distinct ephemeral roots, proof keys, transport identities,
and sessions.

#### Work package 1 — Freeze the integrated deployment contract

Status: `Complete`

Define and validate:

- the exact service inventory, role ownership, image/runtime provenance,
  startup/readiness dependencies, health checks, and shutdown behavior;
- strict public deployment/configuration manifest and maximum size;
- exact suite/topology/policy/provider arm bindings;
- certificate identities, installed trust, audiences, endpoint directory, and
  credential ownership;
- exact internal networks and permitted sender/receiver/message categories;
- per-role volumes, filesystem mode, allowed persistent objects, tmpfs, core-
  dump policy, and resource bounds;
- fresh Client A/Client B construction and destruction boundary;
- resolved/live graph validation and exact-project cleanup rules; and
- new integrated deployment/configuration identifiers assigned only with the
  schema, canonical synthetic manifest, compatibility rules, validator, and
  tests.

Acceptance:

- D023 and the version registry agree on one primary integrated family and
  preserve every frozen/component profile without reinterpretation.
- The manifest cannot carry cues, protected-key material, suite secrets,
  provider credentials, or generated private keys.
- Unknown, duplicate, missing, reordered, cross-suite, cross-topology,
  cross-policy, cross-provider, unsafe endpoint, and unsupported-version
  configurations fail before container startup.
- One validated graph supports the four separately bound Yi/aPPSS ×
  2-of-3/3-of-5 arms with five authorizers and a distinct 4-of-5 authorization
  quorum.

#### Work package 2 — Implement the container service plane

Status: `Complete`

Implement container/service entry points for admission, operator/discovery,
storage gateway, resolver, and the five parties using their already assigned
protocol objects. Reuse one pinned image where appropriate while retaining
distinct processes, identities, networks, volumes, commands, and least-
authority credentials.

Acceptance:

- Every runtime container is non-root with a read-only root filesystem where
  practical, no Docker socket, no unnecessary host port, disabled core dumps,
  bounded health checks, and exact network/volume membership.
- The object store is reachable only through the storage gateway from the
  client plane; the browser and client receive no provider credential or list
  operation.
- Parties start without recovery-suite state. Authenticated enrollment creates
  or delivers only recipient-local state and survives exact retry/restart.
- The networkless bootstrap role has no runtime network and cannot persist or
  distribute cue-derived, protected-key, or recovery-suite secret state.

#### Work package 3 — Connect the frozen UI/API to the deployed services

Status: `Complete`

Retain the P7 semantic HTML/CSS/JavaScript and exact public API operations.
Introduce a deployment-backed implementation of those operations that uses
the admitted discovery/storage routes and authenticated party protocols. The
same-process facade remains a fast component profile and is never selected by
the integrated evidence path.

Acceptance:

- The UI has no Docker control, provider credential, second canonicalizer,
  suite implementation, descriptor validator, or direct party/S3 connection.
- Enrollment, bootstrap, recovery, successor, and inspection cross the exact
  container boundaries declared by the manifest.
- Recovery dispatches only from the authenticated descriptor and offers no
  suite/topology/policy/endpoint fallback or override.
- Browser and server persistence, cache, telemetry, log, clipboard, history,
  crash-output, and prohibited-output controls remain at least as strict as
  `LOCUS-local-research-ui-v1`.

#### Work package 4 — Implement the complete enrollment/recovery/lifecycle workflow

Status: `Complete`

For every selected arm, drive synthetic key generation/import, policy
processing, authenticated suite initialization, encryption, provider
publication, descriptor/current publication, receipt export, Client A
termination/inaccessibility, fresh Client B bootstrap, exact threshold
recovery, public-key identity verification, and optional successor creation.

Acceptance:

- All four registered CuePolicies work through the system; the three direct
  policies make no resolver contact.
- Yi and aPPSS at 2-of-3 and 3-of-5 recover the exact original synthetic key
  through real party APIs under matching outer conditions.
- Same-suite and bidirectional cross-suite successors create fresh native
  state, verify the protected-key identity before cutover, and preserve one
  recoverable authorized epoch across every injected crash boundary.
- Client B receives only installed trust, a public receipt/handle, fresh
  identities/capabilities, and transient fictional recovery input; a deliberate
  inherited Client A marker fails the isolation audit.

#### Work package 5 — Close the pre-evidence full-system gate

Status: `Complete`

Provide one cross-platform interactive start path and one disposable full-
system smoke path. The smoke matrix covers correct and wrong input,
below-threshold failure, every required exact-threshold subset, one-party
unavailability where satisfiable, authorization-quorum loss, process restart,
provider outage, stale CAS, replay/exact retry, cross-suite/downgrade attempts,
successor crashes, role-state audits, output scans, and cleanup.

Acceptance:

- Resolved and live graph validation, health, complete UI-to-service workflow,
  role-state/network/output controls, positive controls, and exact cleanup pass
  on the primary development host.
- A second clean checkout reproduces the complete same-host smoke without
  external credentials or hidden developer state.
- Results remain ordinary test output. No P8/P9 retained corpus, real-provider
  claim, host-independence claim, usability claim, or manuscript change is
  created by P7.5.

Implementation snapshot (2026-08-04):

- `LOCUS-integrated-reference-config-v1` and
  `LOCUS-integrated-reference-deployment-v1` now bind the strict canonical
  manifest, Compose graph, all four arms, all four policies, exact identities,
  networks, role volumes and local provider.
- `LOCUS-cloud-backup-object-v2` and
  `LOCUS-application-storage-gateway-v2` add the v5/v6 backup envelope behind
  the admitted integrated gateway without widening frozen v1 operations.
- The networkless bootstrap, mutual-TLS JSON service plane, remote client API,
  loopback UI, role-state audit, configuration validator, interactive launcher
  and disposable smoke are implemented. Windows raw-key creation is explicitly
  binary-safe.
- One live same-host run passed all four suite/topology arms, all four policy
  enrollment/recovery paths, Client A destruction/audit, Client B recovery,
  wrong-input rejection, four normal successor/recovery paths and exact
  cleanup. This is ordinary development output, not retained evidence.
- The deployed successor path now uses the existing
  `LOCUS-successor-publication-journal-v1` phase coordinator. It verifies
  recovery through freshly prepared remote party state before pointer cutover,
  explicitly retires the predecessor at every party, rejects retired-current
  authorization, and resumes after injected failures following each of the
  eight selected publication effects without duplicating effects.
- The disposable full-system gate passes 26 exact-threshold recoveries: all
  three 2-of-3 subsets and all ten 3-of-5 subsets for both Yi and aPPSS. It
  separately demonstrates below-threshold suite failure after successful
  4-of-5 authorization, one-party availability, authorization-quorum loss,
  replay rejection, stale CAS rejection, party restart, provider outage and
  restoration, suite-override rejection, and wrong-input normalization.
- The same gate validates eleven live service-network memberships, audits
  Client A plus thirteen stopped role/provider volumes, scans all container
  output against dynamic cue/key/provider-credential canaries, and verifies
  exact labeled container/network/volume cleanup. These are ordinary test
  observations, not retained evidence.
- Commit `d4a8da5` reproduced `uv sync --frozen`, `integrated-config`, and the
  complete `integrated-smoke` from a fresh checkout with an empty checkout-local
  uv cache and no host native-extension installation. The primary workspace
  also passed the complete gate with 322 Python tests (two intentional skips),
  all native tests/vectors, formatting, linting, typing, and boundary checks.
- P7.5 creates no P8/P9 retained corpus, real-provider or host-independence
  result, usability claim, production-security claim, or manuscript change.

### P7.6 Isolate the final integrated prototype

Status: `Complete`

D024 requires one self-contained `prototype_final/` workspace containing the
dependency-complete D023 system without moving or deleting historical source.
Its executor exposes only:

- `integrated-check`;
- `integrated-config`;
- `integrated-start`;
- `integrated-stop`; and
- `integrated-smoke`.

Required contents:

- pinned Python environment and lockfile;
- dependency-complete integrated Python package and thin UI assets;
- frozen Yi core, aPPSS core, and narrow native binding;
- integrated Dockerfile, Compose graph, canonical manifest, and schema;
- focused integrated manifest/bootstrap/isolation/service tests;
- licenses and one operator README; and
- no retained evidence, manuscript, credentials, generated state, caches,
  logs, databases, or legacy demo/deployment/artifact command surface.

Acceptance:

- The workspace does not import source or deployment assets from outside
  `prototype_final/` at runtime.
- `integrated-check` passes the reduced Python/native gate.
- `integrated-config` validates both resolved graphs.
- `integrated-smoke` reproduces the complete P7.5 matrix and exact cleanup from
  the isolated build context.
- Executor help lists only the five approved `integrated-*` commands.
- P8+, artifact, contributor, and operator documentation identifies
  `prototype_final/` as the sole active implementation path.

This isolation preserves all D023 and protocol identifiers because it changes
only source organization and the operator command surface. Any semantic system
change still follows the existing version-allocation gates.

Completion record (2026-08-10):

- `prototype_final/` contains the dependency-complete integrated Python
  package, both native suite cores and binding, pinned environment, deployment
  graph, manifest/schema, focused tests, licenses, executor, and one operator
  README. No legacy source path is imported at runtime.
- Executor help exposes exactly the five approved `integrated-*` commands.
  The active Python surface is 46 checked files (including the executor and
  focused tests), with two test modules and 10 Python tests instead of the
  root control suite's 72 test modules and 322 tests.
- `integrated-check` passed formatting, linting, typing, native builds, 10
  focused Python tests, and all Rust tests/vectors. `integrated-config`
  validated both graphs.
- `integrated-smoke` passed all four suite/topology arms, 26 subset
  recoveries, five fault classes, eight lifecycle crash phases, state/network/
  output audits, and exact cleanup from a bounded 12.6 MB Docker context.
- Contributor, CI, artifact, evidence, and roadmap guidance now treats this
  workspace as the sole active P8+ implementation boundary. Existing root
  commands, sources, and tests remain unchanged historical/component controls.

### P7.7 Replace CLI-selected clients with a Manager-controlled workflow

Direction: `Approved` by D025

Status: `Complete`

D025 changes the active deployment, UI/API, clean-client, operator-control,
and evaluation boundaries without changing the Yi or aPPSS constructions,
CuePolicy semantics, protected-key encryption, descriptor/current-state,
admission, authorization, recovery-party, or local-provider protocols. Work
remains entirely inside `prototype_final/`. The completed D023/P7.5 system is
the verified predecessor and cannot be relabeled as the managed system.

#### Work package 1 — Assign the managed-system contracts

P7.7 reviewed each exact D025 identifier together with its strict manifest or
schema, bounds, compatibility rule, canonical vector, negative tests, and first
implementation, and assigns all twelve identifiers as follows:

- `LOCUS-integrated-manager-deployment-v1` and
  `LOCUS-integrated-manager-config-v1`;
- `LOCUS-manager-api-v1` and `LOCUS-local-manager-ui-v1`;
- `LOCUS-container-controller-api-v1` and
  `LOCUS-local-container-controller-v1`;
- `LOCUS-client-api-v2` and `LOCUS-managed-client-ui-v1`;
- `LOCUS-managed-client-instance-v1`;
- `LOCUS-client-recovery-package-v1`;
- `LOCUS-clean-client-isolation-v2`; and
- `LOCUS-security-matrix-v2`, preserving every C01--C26 meaning while adding
  explicit Manager/controller, package-decoder, dynamic-client, and private-
  key-display contracts.

The assigned matrix artifact and strict schema are
`prototype_final/docs/security-matrix-v2.json` and
`prototype_final/docs/schemas/security-matrix-v2.schema.json`. They pin the
immutable v1 bytes and C01--C26 IDs and add managed contracts M01--M05. Their
focused validation and the complete managed acceptance gate assign
`LOCUS-security-matrix-v2`; assignment is not retained evidence or claim
promotion. No P8/P9 trace or result identifier is allocated by this work
package.

#### Work package 2 — Implement the Manager and constrained controller

`integrated-start` accepts no enrollment/recovery mode. It validates and starts
the common service plane, loopback Manager UI/API, and internal lifecycle
controller, waits for health, and creates no Client UI container. The Manager
may request status, start, stop, restart, kill, create/destroy client, and stop-
system transitions only through typed, bounded operations.

Only the dedicated controller may receive the local Docker socket. It is a
root-equivalent trusted same-host role with no host-published endpoint. It
receives Manager and Client self-lifecycle requests only on the exact internal
networks described below. It must enforce the exact project, service allowlist,
labels, fixed image and client template, bounded instance count, port
allocation, volume policy, and transition state machine. No browser request may
supply an image, command, mount, host path, network, environment, label,
Compose project, or arbitrary Docker identifier. The Manager and Client
containers never receive the socket.

The one-shot bootstrap is separately constrained. It runs as root with all
Linux capabilities dropped except exactly `CHOWN` and `DAC_READ_SEARCH`, uses
`network_mode: none`, receives no Docker socket, and exits before unprivileged
runtime services start. Those capabilities are used only to create and
revalidate owner-only per-role files; bootstrap remains limited to synthetic
credentials, public configuration, empty role roots, and fixtures.

The controller alone joins both lifecycle networks. `management` permits only
Manager-to-controller requests. `client-lifecycle` permits only a Client-to-
controller request scoped to that Client's exact instance. Managed Clients are
not attached to `management`, cannot reach the Manager UI/API, and do not use
the lifecycle networks for admission, discovery, storage, resolver, or party
protocol traffic.

The two browser publication networks are also distinct. `manager-edge` joins
only the Manager and carries its host-loopback-published UI path.
`browser-edge` joins only dynamic Clients and carries their separately
published loopback UI paths. Neither edge network is a Manager-to-Client
channel, and Clients cannot join or reach `manager-edge`.

Stopping the complete system through the Manager is the normal manual
workflow. A CLI stop/cleanup path may remain only as exact-project emergency
recovery and automated-smoke cleanup; it is not the documented enrollment or
recovery workflow. Emergency `integrated-stop` preserves role/provider volumes
by default. `integrated-stop --reset-state` is an explicit irreversible local
reset that deletes every exact-project role/provider volume, credential, and
enrolled epoch; it is never a normal stop or recovery action.

A fresh managed bootstrap creates a 366-day synthetic CA and 365-day role TLS
certificates. Default stop/start reuses those credentials and protocol volumes
only when the exact manifest and role-root inventory still validate. There is
no in-place credential renewal: expiry or an incompatible manifest fails
closed and requires the explicit full-state reset above. This bounded research
lifetime and destructive recovery path are not production PKI rotation.

#### Work package 3 — Implement dynamic Client instances and one Client UI

Each created Client container receives fresh bounded client state and a public
instance identifier under the managed-client-instance profile. The UI displays
that identifier so a reviewer can distinguish the enrollment and recovery
clients. Stop/start/restart behavior and destruction of the exact client-
scoped container and state are explicit. Destruction is not forensic erasure.

Client `stop` and `kill` make its UI unavailable while retaining the container
and public client-instance identifier. A later `start`, and every `restart`,
rotates the process proof identity and clears the volatile server-side key slot,
export/import cache, and operation/session set under that same identifier.
`destroy` removes the
container and identifier; a later `create` receives a distinct identifier.
Manager controls and confirmations must call stop/start, restart, and kill
destructive volatile resets rather than session-preserving operations.

The same thin Client UI supports:

- generation and optional transient reveal of a synthetic private key;
- enrollment under one explicitly selected registered suite, paired holder
  profile, and CuePolicy;
- authenticated threshold setup, common HKDF/AES protection, provider
  publication, and client recovery-package download;
- bounded package import, authenticated configuration restoration, exact
  threshold recovery, decryption, replacement of the transient current key,
  and public identity verification;
- an authenticated request to destroy its own exact client instance.

P7.7 does not add a successor route to Client API v2 or the managed Client UI.
The existing same-suite and cross-suite successor core remains unchanged and
must stay green as a compatibility control outside this UX.

The browser remains a thin caller. It contains no CuePolicy canonicalizer,
suite implementation, descriptor verifier, admission logic, storage adapter,
or Docker control logic. A revealed key is synthetic active-client data only:
it is never logged, cached, persisted, placed in browser storage, sent to the
Manager/controller, or included in an export.

#### Work package 4 — Preserve authenticated protocol selection and storage

Enrollment offers only the approved 2-of-3 holders `1,2,3` and 3-of-5 holders
`1,2,3,4,5`, with the separately typed 4-of-5 authorizer quorum. Recovery may
choose a valid threshold subset only from the authenticated descriptor's
declared holders. It has no arbitrary `k,n`, membership, endpoint, suite,
policy, downgrade, or fallback control.

`LOCUS-client-recovery-package-v1` is an additive bounded transport for the
existing encrypted backup and authenticated public recovery metadata. Import
bytes and metadata are untrusted until exact decoding, length/digest checks,
operator signatures, discovery/current-pointer binding, and the required
current-party quorum pass. Missing or unsupported authenticated configuration
fails closed. The package does not replace admission, the storage gateway and
local S3-compatible provider, current-state validation, authorization, or
online threshold-party participation, and it contains no party state or
plaintext secret.

#### Work package 5 — Close the managed pre-P8 gate

Extend focused tests and the disposable integrated smoke through the Manager
and controller APIs. Preserve the complete P7.5 suite/topology, CuePolicy,
threshold-subset, authorization, wrong-input, unavailable-role, restart,
provider-outage, replay, stale-CAS, downgrade, role-state, network, output-scan,
and cleanup matrix while adding the new management and package boundaries.
Keep the existing successor/crash suite green as a separate protocol-
compatibility control; P7.7 completion does not require a successor UI route.

Acceptance:

- `integrated-start` has no `--mode`, publishes only the documented loopback
  Manager endpoint initially, and reaches a healthy base graph with zero
  Client containers.
- The resolved and live graph match the newly assigned managed configuration;
  only the controller has a Docker-socket mount, and Manager/Client containers
  cannot contact the Docker engine directly.
- `management` contains only Manager and controller; `client-lifecycle`
  contains only the controller and managed Clients. A managed Client cannot
  reach the Manager UI/API, and its lifecycle request cannot name another
  instance or invoke an operator-only action.
- `manager-edge` contains only the Manager and `browser-edge` only dynamic
  Clients. Each publishes a distinct host-loopback UI path; neither creates a
  container-level Manager-to-Client route.
- Manager lifecycle actions are idempotent and exact-project scoped. Unknown,
  stale, cross-project, duplicate, forged, replayed, cross-origin, arbitrary-
  specification, and disallowed-transition requests fail without changing an
  allowed container.
- Client creation produces a fresh public instance identity and proof-key
  binding. Destruction makes that UI unavailable, removes its exact client-
  scoped state, and a fresh client rejects a deliberate inherited-state marker.
- Client stop/start, restart, and kill/start retain the public instance ID but
  rotate the proof identity and clear the volatile server-side key, export/
  import, and operation/session state; the UI labels and confirms those
  destructive reset semantics.
- Both suites at both paired topologies and all four registered CuePolicies
  complete enrollment, package download, original-client destruction, fresh-
  client package import, authenticated recovery, key replacement, and public-
  identity verification through the deployed services.
- Every exact threshold subset succeeds only under 4-of-5 authorization;
  below-threshold, wrong-input, invalid-package, unauthenticated-metadata,
  override, downgrade, unavailable-role, replay, stale-pointer, and injected
  lifecycle-failure cases fail in their registered categories.
- Package/parser positive controls, Manager/controller containment positive
  controls, Client A/Client B isolation controls, prohibited-output scans,
  role-state/network audits, and exact disposable cleanup all pass.
- Default stop/start preserves exact credential identities and enrolled state;
  expired or incompatible credentials fail closed, while explicit emergency
  `integrated-stop --reset-state` removes all exact-project role/provider state
  and produces a fresh trust domain and empty deployment on the next start.
- The security-matrix-v2 schema and focused preservation tests pin v1 and
  C01--C26 exactly and cover managed contracts M01--M05; the complete P7.7 gate,
  rather than that focused check alone, assigns the matrix profile.
- Existing same-suite and cross-suite successor/crash regression controls stay
  green without adding successor operations to Client API v2 or its UI.
- Normal operator documentation uses one `integrated-start` command followed
  by Manager and Client UI actions. Emergency CLI cleanup is separately labeled
  and never substitutes for the Manager-controlled smoke path.
- Active architecture, evidence, artifact, contributor, and operator documents
  identify the managed profiles as implemented and Assigned while preserving
  the separate P8/P9 collection and manuscript gates.

Completion record (2026-08-11):

- The enhanced disposable Docker smoke passed all four suite/topology arms, 26
  threshold subsets, four isolated clean Clients, live control-plane isolation,
  all documented lifecycle actions, prohibited-output scans, 15 bootstrap-role
  and 15 post-operation role audits, and exact cleanup.
- Normal stop/restart recovered the enrolled key with an unchanged CA. The
  explicit destructive reset created a fresh CA and empty remote state, rejected
  the old package, and left no exact-project resources after cleanup.
- After the final controller/bootstrap fixes, `integrated-check`, 27 focused
  tests, formatting, linting, typing, managed configuration validation, and the
  final browser acceptance all passed.
- The exact bootstrap capability/network boundary, lifecycle/reset semantics,
  package and key-display limitations, network separation, and credential
  lifetime are documented. All twelve D025 managed identifiers are `Assigned`,
  not `Frozen`.
- These are pre-evidence implementation observations. No retained P8/P9 result,
  trace, or result-schema identifier was created, no claim status changed, and
  no manuscript edit was authorized.

---

## P8 — Security, reliability, and information-flow assurance

Entry gate: P7.5 work package 5, P7.6, and P7.7 passed. P8 applies the
P7.7-assigned `LOCUS-security-matrix-v2` contracts to the exact managed
deployment manifest from the self-contained `prototype_final/` workspace.
Unit, property, and component assurance remains necessary, but every system-
facing conclusion must also exercise the Manager-created container-backed
Client UI/API path, controller boundary, imported/exported package boundary,
and actual role state or traffic boundary.

### P8.0 Reconcile the implemented baseline and freeze the assurance sequence

Status: `Complete`

Before P8 implementation or retained collection:

- reconcile every active technical, artifact, registry, and claim-status
  document with the completed P7.5 implementation while preserving the
  distinction between implementation verification and retained evidence;
- normalize roadmap statuses to the status model in this plan;
- make P8.1 responsible for a checked inventory of every externally reachable
  decoder and durable mutating transition and its existing/required coverage;
- make P8.2 responsible for assigning the state-boundary/security result
  schemas and paths before any retained state-boundary collection;
- make P8.3 responsible for assigning the privacy-safe network-flow trace
  profile and schema before any retained flow collection; and
- limit P9.2 to performance and resilience result schemas so that P9 does not
  retroactively define P8 evidence.

Acceptance:

- No active document describes P7.5 or its operator commands as unimplemented.
- The version registry consistently records every assigned P2/P7.5 identifier.
- Claim matrices distinguish completed implementation gates from still-pending
  P8 retained evidence and do not promote a paper claim.
- P8/P9 chronology prohibits collection before the applicable schema,
  identifier, positive-control contract, and retained-output policy exist.

Completion record (2026-08-10):

- The completed P7.5 status and commands were synchronized across the active
  planning, architecture, API/UI, deployment, artifact, registry,
  information-flow, output-safety, and claim-status documents.
- Roadmap status values were normalized without changing the qualified open
  gates for independent human review, optional live AWS, or P6.4 host
  separation.
- State/security schemas now belong chronologically to P8.2, flow trace schemas
  to P8.3, and performance/resilience schemas to P9.2. No retained P8/P9 result
  was collected or identifier assigned by this reconciliation.

D025 postdates this completion record. P7.7 separately completed the managed-
system reconciliation; P8.0 remains an accurate record of the earlier D023/
P7.5 normalization rather than evidence for the D025 profile.

### P8.1 Add decoder and state-machine assurance

Status: `Proposed`

Readiness: P7.7's implementation and assignment gate is satisfied. P8.1 is the
next ready step; it must not collect retained evidence assigned to P8.2/P8.3.

Add:

- a checked coverage inventory mapping every external decoder and durable
  transition in `prototype_final/` to its existing and required
  negative/integrated tests;

- bounded property testing;
- malformed-input fuzzing;
- duplicate/unknown/member-order tests;
- cross-session and cross-epoch messages;
- concurrency scheduling;
- crash/restart at every durable transition;
- idempotency and replay;
- path and symlink containment;
- prohibited-output scans;
- integrated service decoder coverage for admission, discovery, storage,
  resolver, party, managed Client UI/API, Manager UI/API, controller,
  client-recovery-package, health, and operator endpoints;
- resolved/live Compose graph mutation tests; and
- full-system concurrency and restart schedules through the public Manager and
  Client APIs, including simultaneous or stale lifecycle operations.

Acceptance:

- Every external decoder and mutating state transition has negative coverage,
  and the integrated system reaches each externally reachable transition
  through its authenticated transport rather than a test-only direct call.

### P8.2 Add state-boundary evidence

Status: `Proposed`

Before collection, freeze and register the exact aggregate-only security/state
result families, schemas, versioned paths, positive controls, scenario
manifests, provenance fields, and exclusive-publication rules. Exploratory
development reports remain outside retained paths until that gate passes.

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
- lifecycle predecessor/successor states;
- UI/client-gateway container after enrollment and after recovery;
- Manager and controller state/configuration, sanitized lifecycle records, and
  Docker-socket exposure boundary;
- every live and destroyed managed-client instance boundary plus the exported-
  package holder view;
- admission, operator/discovery, storage-gateway, resolver, object-store, and
  every party container/volume in the integrated graph; and
- exact matching unions of those views for each suite/topology arm.

Acceptance:

- Each scenario has a positive control and aggregate-only report bound to the
  integrated deployment/configuration manifest, suite, topology, policy,
  provider, source commit, and exact role snapshot set.
- Every retained report validates against a P8.2-assigned schema and identifier;
  no P9.2 performance schema is used to authorize security/state collection.

### P8.3 Add privacy-safe network-flow evidence

Status: `Proposed`

Before collection, assign the exact trace-policy identifier, aggregate trace
schema, permitted categories, positive controls, unexpected-contact rule,
versioned path, and provenance binding required by `EVIDENCE-POLICY.md`.

Prefer structured instrumentation that records:

- sender and receiver role;
- fixed message category;
- byte count;
- whether a prohibited category was detected;
- whether an unexpected role/contact occurred.

Instrumentation is attached to the integrated service adapters and fixed role
directory. Component-only traffic cannot support a system information-flow
claim. Browser-to-Manager, Manager-to-controller, controller-to-Docker,
browser-to-Client, Client-to-service, package upload/download, and every inter-
service contact are included by category without retaining payloads.

Packet captures are not retained. Any temporary inspection requires a new
approved trace policy and synthetic local traffic.

Acceptance:

- Reproducible aggregate evidence supports role-visibility statements without
  retaining payloads, and the expected graph is checked against both resolved
  configuration and observed integrated-system contacts.
- Collection cannot begin until the P8.3 trace profile/schema and prohibited-
  output checks are registered and tested.

### P8.4 Preserve attempt control as a boundary

Status: `Proposed`

- Keep the rollback counterexample reproducible.
- Keep signed local auditing isolated from recovery-suite correctness claims.
- Do not block core recovery on an unproven global bound.

Acceptance:

- Documentation and UI never describe the quorum-only ledger as globally
  rollback-resistant.
- The integrated deployment reproduces the rollback counterexample or its
  exact boundary without presenting container durability as a global bound.

---

## P9 — Performance and resilience evaluation

Entry gate: P7.7 and the applicable P8 trace, state, and output-safety gates
must pass. The managed integrated deployment is the primary measurement
system. Native and component microbenchmarks may explain costs but cannot
substitute for or be pooled with end-to-end results.

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
- cross-host/WAN latency where authorized;
- loopback browser-to-client request latency as a separately labeled UI
  observation; and
- Manager startup plus managed-client create, stop/start, restart, destroy,
  export, and import latency as separately labeled operator/UI observations;
- end-to-end client-API latency across every required integrated service,
  excluding browser rendering from protocol timings.

Acceptance:

- Frozen scenarios, sample sizes, randomization, warm-up, exclusion rules,
  topology, statistics, provenance, and no-outlier policy are documented before
  retained collection.
- Every central scenario binds the exact integrated deployment manifest,
  suite/topology arm, policy, provider, active-client boundary, host tier, and
  instrumentation version.
- Yi/aPPSS comparisons within one topology use the same integrated graph,
  synthetic protected key/input class, policy, admission, storage, failure
  schedule, warm-up, sample count, and metric definitions.

### P9.2 Implement new evidence schemas

Status: `Proposed`

Implement only the performance and resilience result families needed by the
P9.1 methodology, including end-to-end integrated performance, failure and
restart schedules, concurrency/throughput, role/storage bytes, and any
separately labeled browser-observed latency. P8.2 owns security/state result
schemas and P8.3 owns network-flow trace schemas.

Acceptance:

- Schemas bind exact recovery suite, policy, descriptor, backup, profile,
  threshold, party identities, topology, backend, scenario, positive control,
  output scan, and limitations.
- Integrated schemas additionally bind the UI/client API and backend versions,
  deployment/configuration identity, canonical manifest digest, resolved/live
  graph digests, immutable image identities, service identities and roles,
  network topology, provider mode, suite/topology arm, policy, active-client
  boundary, and failure schedule.
- aPPSS and frozen Yi results use separate result families. A comparative
  processor may consume both only under a new schema that preserves both
  provenance records and never relabels or pools retained v2 measurements.
- No result schema accepts the P7 in-memory profile, P6 component controls, or
  frozen Compose v2 identifier where an integrated-system result is required.
- P9.2 cannot redefine, broaden, or retroactively authorize a P8.2 security/
  state result or P8.3 flow trace.

### P9.3 Collect the same-host integrated baseline

Status: `Proposed`

Acceptance:

- New versioned result paths.
- No v2 overwrite or mixed-profile processing.
- Complete raw-to-processed-to-derived hash closure.
- Successful, wrong-input, below-threshold, unavailable-party, restart,
  successor, concurrency, storage/role-byte, and clean-client rows all execute
  through the container-backed client API under the same validated graph.

### P9.4 Collect supplemental integrated multi-host and provider profiles

Status: `Proposed`

Acceptance:

- Exact topology and administration scope disclosed.
- All credentials disposable and excluded.
- Claims limited to exact hosts, thresholds, providers, and workloads.
- Supplemental rows retain the same logical full-system path and receive new
  deployment/result identities; they are never silently pooled with the local
  S3-compatible same-host baseline.

---

## P10 — Review, artifact, and external claim readiness

### P10.1 Independent cryptographic review

Status: `Proposed`

Review:

- independently confirm, change, or reject every provisional D020 status in
  `docs/RECOVERY-SUITE-DEVIATIONS.md` using the mandatory checklist in
  `docs/P5A7-INTERNAL-MAPPING-ASSESSMENT.md`;
- disclose reviewer identity/qualifications, independence, and conflicts and
  bind the finding to the exact final implementation commit;
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
- Separate Yi, aPPSS, LOCUS-composition, and overall dispositions satisfy
  D019, with correction/re-review or claim removal for every rejected
  claim-critical mapping.
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
- evidence methodology;
- the resolved and live D025 managed service graph, Manager/controller trust
  boundary, role identities, credentials, networks, mounts, provider boundary,
  package boundary, and dynamic active-client isolation; and
- one complete enrollment, clean recovery, and successor workflow through the
  container-backed client API, without direct state injection.

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
- deterministic processing and derived outputs;
- the D025 Manager-to-dynamic-Client integrated deployment and all required
  services;
- enrollment and clean-client recovery for all four suite/topology arms; and
- at least one same-suite and one cross-suite successor flow.

Acceptance:

- Deterministic archive with new version and manifest.
- Extracted archive passes without `.git` or developer-local state.
- Clean Linux and Windows reproduction passes.
- One unfamiliar reviewer completes the workflow.
- The reviewer uses no external credential and does not need the P7 in-memory
  profile to reproduce a central system result.

### P10.4 Close the active claim/evidence matrix

Status: `Proposed`

Acceptance:

- Every promoted claim identifies exact profile, assumptions, adversary,
  evidence, and limitation.
- Every new promoted system/performance result identifies the D025 managed
  integrated deployment family and exact suite/topology/policy/provider
  scenario; D023, legacy, and component evidence remains explicitly scoped.
- Global rate limiting, memorability, entropy, production readiness, independent
  administration, and audit remain non-claims unless separately established.

### P10.5 Propose manuscript deltas

Status: `Deferred`

After the integrated P8/P9 evidence, clean-host artifact reproduction, and
independent recovery-suite mapping review close, present each proposed title,
abstract, section, claim, limitation, table, figure, and reference delta to the
owner.
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

## Recommended next execution slice

Execution remains chronological. P0--P5A, P6.1--P6.3, and P7.1--P7.7 are
complete for implementation chronology. P6.4's
actual host-separation tiers remain blocked on infrastructure and do not block
the honest same-host managed integrated profile.

The next sequence is:

1. P8.1 — create the checked decoder/state-machine inventory and close its
   assurance gaps in `prototype_final/`;
2. P8.2--P8.4 — assign the required security/trace schemas, assure the exact
   integrated system, and preserve the attempt-control boundary;
3. P9 — collect new suite/topology-specific performance/resilience results
   from that system; and
4. P10 — complete independent review, integrated artifact reproduction, claim
   closure, and separately owner-approved manuscript changes.

Do not collect retained P8/P9 evidence, promote a system result, or propose a
manuscript delta from the new direction before its applicable predecessor
gate. The optional AWS run, actual multi-host work, general party replacement,
and monotonic witness remain separate owner/infrastructure gates.
