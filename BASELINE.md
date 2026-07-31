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
- No `RecoveryDescriptor` or discovery protocol exists.
- No public-client admission exists.
- Evaluated enrollment uses a trusted networkless provisioner and direct volume
  writes rather than authenticated remote enrollment.
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

## Post-baseline aPPSS migration note

aPPSS is not part of the imported implementation, manuscript baseline, sealed
artifact, or retained v1/v2 evidence. D016 authorizes a future separately
versioned successor, but no aPPSS implementation or result exists until P5A is
completed. The locally supplied 2024 paper is an ignored research input; it is
not tracked or included in an artifact, and its redistribution status has not
been established. None of these planning facts changes the inherited Yi TPASS
baseline described above.

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
