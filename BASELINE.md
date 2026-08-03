# Upstream Baseline

## Extraction record

- Extraction date: 2026-07-29
- Upstream repository commit:
  `771fccd14d918b697bfb48fd24a0202c52c7f7ac`
- Upstream branch at inspection: `codex/v4-consistency-cutover`
- Upstream working tree at inspection: no tracked changes; `AGENT2.md` and
  `PLAN2.md` were untracked proposal documents.
- Portable-copy policy: the integrated continuation includes active source,
  technical documentation, manuscript, retained versioned evidence, generated
  paper inputs, and the sealed anonymous-artifact release. Git history,
  duplicate artifact extraction, generated build directories, caches, scratch
  output, credentials, and unlicensed external PDFs were excluded.

The untracked upstream `AGENT2.md` and `PLAN2.md` mixed existing facts,
proposed architecture, and unapproved manuscript decisions. Their useful
long-horizon ideas are incorporated into this repository's `PLAN.md`, and the
original bytes are preserved under
`docs/upstream-baseline/project-state/` as proposal history rather than active
authority.

## Verified upstream quality state

The complete upstream default gate was run before extraction:

- Python syntax, formatting, linting, and type checking passed.
- 152 Python tests passed.
- One opt-in live-S3 test was skipped.
- The native PyO3 extension built successfully.
- Rust formatting and clippy passed.
- 17 Rust core unit tests and the fixed-vector integration test passed.

This is an upstream baseline fact. The portable project must run its own clean
gate after it is copied to a separate directory and initialized as a new Git
repository.

## Imported manuscript baseline

- Authoritative source: `paper/main.tex`
- Bibliography: `paper/references.bib`
- Intentional review snapshot: `paper/main.pdf`
- Review snapshot: 14 pages
- `paper/main.tex` SHA-256:
  `cab18dd54cb09f3d3c296786dd3b856d3891d48d54861b3a8fb7686e144130db`
- `paper/references.bib` SHA-256:
  `d4c5e66a0968884538d5446086569c60b51c55fe710acfd5b4082bc8e1b83e69`
- `paper/main.pdf` SHA-256:
  `c42bb7766a08ad1cfe2c7d5d66a726c52277395df46fc12486e6749e111fec22`

The PDF hash above is the value measured from upstream commit
`771fccd14d918b697bfb48fd24a0202c52c7f7ac`; an older hash in upstream
project instructions was stale. `paper/related_work.tex` and legacy generated
v1/benchmark rows are retained for history but are not included by
`paper/main.tex`.

## Integrated-repository artifact boundary

The sealed v1 anonymous ZIP remains independently verified and unchanged. P0.4
introduced the separate `LOCUS-anonymous-artifact-v2` source package boundary:
package-specific reviewer documents, a strict manifest schema, an explicit
privacy-safe allowlist, deterministic-package tests, and a separate pending
release checklist. The anonymity scanner was not weakened. The active v2 audit
excludes repository-facing planning documents, manuscript source/PDF,
superseded results, and external papers while retaining only the exact frozen
v2 aggregate evidence and generated performance inputs. Archive publication is
not authorized while the v2 release checklist remains pending.

## Inherited evaluated profile

- Cue policy: `LOCUS-location-person-set-v1`
- Cue cardinality: exactly three location-person pairs
- Location representation: WGS84 coordinates quantized to \(10^{-4}\) degrees
- Person representation: constrained lowercase ASCII email or E.164 phone
- TPASS implementation: native Rust/Ristretto255
- TPASS holders: parties 1--3
- Deployed TPASS threshold: 2-of-3
- Authenticated authorizers: five processes
- Authorization quorum: 4-of-5
- Parties 4--5: authorizer-only, no TPASS state
- Backup format: `LOCUS-reference-backup-v4`
- Deployment profile: `LOCUS-compose-deployment-v2`
- Cloud adapter: immutable filesystem and S3-compatible implementations
- Deployment evidence: isolated same-host containers, not independent
  administration

## Inherited implementation capabilities

- deterministic canonical JSON-style encoding with Unicode NFC normalization;
- domain-separated hashing and secure random generation;
- HKDF-SHA-256 and AES-256-GCM backup protection;
- native TPASS setup, request, proof, response, aggregation, and validation;
- canonical external encodings and malformed-wire rejection;
- PyO3 boundary that does not serialize client blinders or party ephemerals;
- strict immutable backup-object creation and exact-reference retrieval;
- per-party SQLite state with full synchronous durability;
- request-bound idempotency and exact retry;
- pinned mutual-TLS recovery-party transport;
- signed attempt and freshness certificates;
- same-host recovery, restart, alternate-subset, and failure tests;
- deterministic resolver fixture and pinned cue-policy/drift vectors;
- same-membership successor preparation, readiness, activation, retirement,
  restart reconstruction, and successor recovery;
- bounded attempt-control counterexample exploration;
- cloud, one-party, and combined persistent-snapshot harnesses;
- deterministic aggregate evidence processing and output-safety tooling.

## Important inherited limitations

- The deployment's "fresh client" mounts surviving `client-data` containing
  configuration, CA material, a coordinator certificate, and a coordinator
  private key. It proves a fresh process, not complete clean-device recovery.
- P4.2 adds a separate bounded isolation profile in which Client A's credential
  root is removed and Client B uses a distinct sanitized process/root and fresh
  transport identity. This does not reinterpret the retained Compose evidence
  or establish forensic erasure.
- No `RecoveryDescriptor` or discovery protocol exists.
- P3.3/P3.4 specify and implement the provider-neutral local admission
  contract, deterministic synthetic issuer, proof-key validation, independent
  replay stores, and an admitted storage-gateway wrapper. It is component-level
  same-host research behavior, not external identity-provider or production
  admission evidence.
- P4.1 implements the stable, secret-free recovery phase/retry state machine
  and generic secret-path rejection boundary. It does not itself perform the
  P4.2 clean-client isolation scenario.
- P4.3 adds a durable secret-free successor-publication journal, exact action
  retries, prepared-package recovery verification, and explicit no-rotation by
  default over the existing same-membership lifecycle boundary. Its crash
  adapter is synthetic and does not establish external-provider, rollback, or
  general-replacement evidence.
- P3.2 implements authenticated, recipient-bound initial enrollment across
  clean same-host party processes. The retained/evaluated v2 deployment still
  uses its frozen trusted networkless provisioner and direct volume writes, so
  its historical evidence is not reinterpreted as P3.2 evidence.
- Only one CuePolicy is implemented.
- No graphical UI exists.
- No real-provider result is retained.
- No genuine multi-host or independently administered party deployment exists.
- General membership replacement is absent.
- Global rollback-resistant attempt limiting is disproved for the current
  quorum-only model and remains a non-claim.
- Persistent-state absence is tested in bounded roles, but forensic memory,
  swap, crash-dump, and privileged-host erasure are not.
- The native TPASS instantiation is not independently audited.
- No human memorability or usability evidence exists.

## Retained baseline evidence

The integrated repository retains the upstream evidence at its exact versioned
paths:

- retained v1 attack records: 3;
- retained v1 performance records: 30;
- retained v2 attack records: 3;
- retained v2 performance records: 30;
- performance collection commit:
  `12ca8157841088807863e2457b9fe5ee3e069e9f`;
- pseudonymous host: `cycle1-v2-host-a`;
- processed summary SHA-256:
  `462e492795fafdd90a4f39851a612275193603d816f761728afe05e97a470a6b`;
- anonymous artifact source commit:
  `c3352a924f39b7437aff7da412429506c6dae93f`;
- anonymous artifact ZIP SHA-256:
  `6170b81ec86f60a8adfdfb2fc53e5c88e07b00f5128dbe8c3552ada8fe214c0c`.

The v1 family is superseded historical material. The v2 corpus is baseline
evidence only for the exact frozen profile and provenance it records. It is not
evidence for RecoveryDescriptor, clean-client, multi-policy, real-cloud,
multi-host, UI, admission, or changed lifecycle behavior. Never overwrite or
reinterpret either family; new profiles require new identifiers and paths.

## Post-baseline selectable-suite note

aPPSS is not part of the imported implementation, manuscript baseline, sealed
artifact, or retained v1/v2 evidence. D017 approves its exact future
construction and D018 requires it to coexist with frozen Yi as an independent
selectable suite in paired 2-of-3 and later 3-of-5 profiles. P5A.1 now assigns
the exact aPPSS format/profile identifiers, strict schemas, public structural
vector, and separate native-core boundary. P5A.2 implements that core and its
narrow binding with public fixed vectors and regression tests. P5A.3 adds the
independent aPPSS adapter, exact no-fallback suite registry, suite-neutral
backup-v5 composition, durable per-holder state, transient distributed client,
and a pinned mutual-TLS subprocess recovery path. P5A.4 adds authenticated
distributed aPPSS initialization: each clean process creates only its own key,
the client installs one common public state after exact context-bound OPRF
evaluation, and durable caller/route/body idempotency protects the new `/v1`
component routes. P5A.5 adds an explicit-selector
epoch factory and P4.3-backed same-suite/cross-suite successor component. All
four Yi/aPPSS directions preserve the protected-key identity with fresh native
state and reject fallback and mixed state. D020 activates this post-baseline
application interface after an explicitly non-independent internal mapping
assessment. The frozen Compose deployment remains Yi-only until P6 assigns new
paired deployment profiles. P5A.6 adds one zero-argument,
aggregate-only, non-retained paired 2-of-3 compromise regression. It covers all
below-threshold coalitions and all exact-threshold subsets, confirms the
suite-specific threshold-compromise behavior, and emits no candidate, holder,
or recovery value. It is component regression rather than retained evidence or
cryptographic proof. P5A.7 is in progress. The candidate passed a disposable
clean Linux complete gate; a fresh Windows checkout then found that unpinned
JSON/TXT line endings changed three byte-digest regressions under
`core.autocrlf=true`. Commit `36ea1fe` pins those text artifacts to LF without
changing a frozen/public vector or expected digest, and the corrected fresh
Windows checkout passes the complete gate. D019 now defines the remaining
external gate as an independent, claim-focused mapping review of frozen Yi,
aPPSS, and their LOCUS composition rather than a full production cryptographic
audit. D020's internal assessment provisionally accepts all three boundaries
with required qualifications and no correction-required finding, but is not an
independent review. Its human confirmation remains mandatory before manuscript
reliance or final reviewed release. The explicit selector is active at the
post-baseline application/component boundary; the frozen Yi-only Compose
deployment and retained evidence are not reinterpreted. No retained P9
evidence or manuscript authorization exists. The locally supplied
2024 paper is an ignored research input; it is not tracked or included in an
artifact, and its redistribution status has not been established. None of these
planning facts changes the inherited Yi TPASS baseline described above.

## Post-baseline interface note

P1.3 adds suite-neutral in-memory contracts and a thin frozen-Yi compatibility
adapter in the integrated project. It also wraps the existing CuePolicy and
deterministic resolver functions behind typed interfaces. This is post-baseline
scaffolding, not an imported capability, new wire format, aPPSS implementation,
deployment result, or evidence profile. The adapter delegates to the unchanged
native Yi backend and preserves the frozen TPASS and cue vectors byte-for-byte.
P5.1 completes application routing through that frozen CuePolicy adapter for
deployment, lifecycle, walkthrough, and deterministic-resolver paths without
changing the compatibility function, identifier, canonical bytes, errors,
password input, backup, or retained evidence.
P5.3 adds three post-baseline atomic policy implementations, public metadata,
an exact registry, and a new conformance corpus. They demonstrate interface
generality only and are not yet integrated into enrollment or either recovery
suite. They change no frozen policy, Yi vector, backup, deployment, manuscript,
or retained evidence.
P5.4 adds the post-baseline resolver-free adapter used only by those atomic
policies. It performs no lookup or alternative enumeration and rejects the
frozen resolver-backed policy. The external-provider profile remains
unimplemented and separately execution-gated.

## Post-baseline namespace note

P1.4 adds a machine-checkable protected-identifier ledger and future-family
allocation gates. This is integrated-project governance, not an imported
capability or new protocol profile. The registry protects historical,
development, test, trace, result, and artifact identifiers from reuse without
changing their original status or meaning. Descriptor and local-admission
identifiers are now assigned by P2/P3; remaining future policy, aPPSS,
deployment, trace, result, artifact, and optional provider-admission identifiers
stay unassigned until their chronological schema/vector gates pass.

## Post-baseline security-matrix note

P1.5 adds prospective phase/view and claim-security contracts for the
improvement project. These matrices preserve the retained baseline boundary:
they do not make later descriptor/admission components, clean-client, aPPSS,
provider, multi-host, UI, replacement, or production claims supported. Frozen
v2 evidence remains unchanged and non-transferable.

## Post-baseline RecoveryDescriptor note

P2.1 adds new strict descriptor, current-pointer, manifest, and deterministic
bundle codecs. P2.2 adds an application-installed trust configuration,
optional signed receipt, party-current-summary format, and a pure clean-client
bootstrap validator over already supplied discovery bytes. P2.3 adds
filesystem and S3-compatible immutable descriptor/bundle stores and exact-byte
current-pointer CAS below a same-host service boundary. These are
post-baseline formats and do not change the frozen backup, Yi, CuePolicy,
deployment, manuscript, or retained evidence. Admitted gateway retrieval,
complete clean-client recovery, and descriptor evidence remain unimplemented
until P3--P4 and the later evidence gates. P2.4 adds a strict aggregate-only
development scenario report and bounded networkless direct-verifier regression
with positive controls; it is not P9 evidence and changes no baseline claim.
P3.1 adds a post-baseline suite-neutral enrollment phase coordinator with
idempotent public-metadata events. It does not alter imported enrollment,
transport, frozen Yi state, retained evidence, or manuscript behavior.

P6.1 adds a post-baseline provider-level composition and common conformance
suite over the already separate backup, descriptor, bundle, and current-pointer
contracts. Deterministic filesystem and S3-compatible composites pass the same
role suite; nonlocal profiles require TLS and no profile requires listing. This
does not create a real-provider result, change the frozen Compose deployment,
or reinterpret retained evidence.

## Excluded material

The portable copy excludes:

- upstream `.git`, remotes, history, and local author identity;
- the duplicate `artifact-submission/` extraction, because the verified ZIP and
  its external manifest are retained under `dist/`;
- LaTeX build byproducts other than the intentional `paper/main.pdf` snapshot;
- `extra/TPASS.pdf`, whose redistribution status was not established;
- virtual environments and tool caches;
- Rust `target` directories and native extension binaries;
- scratch benchmarks, temporary output, databases, snapshots, logs, traces,
  credentials, certificates, and private keys.

Current upstream technical Markdown is available at the normal active
`docs/*.md` paths. A byte-for-byte provenance snapshot remains under
`docs/upstream-baseline/` and must not be edited.
