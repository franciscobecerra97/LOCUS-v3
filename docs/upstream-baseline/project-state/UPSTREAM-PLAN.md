# PLAN.md

## Living Plan Rules

This is the authoritative execution plan for LOCUS. Keep it current throughout the project.

Status labels:

- `Todo`: the task has not started.
- `Doing`: the task is currently in progress.
- `Done`: the task has been completed and verified.
- `Deferred`: the task is intentionally outside the frozen Cycle 1 scope.
- `Scoped`: only the explicitly recorded subset is required or complete.
- `Accepted risk`: the issue remains true but is consciously carried as a
  limitation rather than treated as unfinished implementation work.

Maintenance rules:

- Update task status whenever work starts, completes, changes, is blocked, or is replaced.
- Record relevant results, decisions, outputs, and follow-up tasks.
- Do not mark a task `Done` until its completion criteria are satisfied and verified.
- Keep completed tasks in this document to preserve project history.
- Keep only a small number of tasks marked `Doing` at the same time.
- Add references to relevant files, commits, experiments, figures, or paper sections when useful.
- Any paper-facing claim must map to implementation, experiment, proof, or citation evidence before it appears in the abstract or contribution list.

Last plan refresh: 2026-07-28.

## Progress Summary

Current phase: Phase 2 local crypto freeze, the novelty/interface gate, P4.9
same-membership lifecycle, the scoped P5.13 bounded negative result, and the
original P6/P7 Cycle 1 corpus are complete. M4 reconstruction and its
consistency cutover are complete: the current deployed profile uses
`LOCUS-reference-backup-v4`, authenticates the exact
`LOCUS-location-person-set-v1` cue-policy identifier, and identifies the
deployment as `LOCUS-compose-deployment-v2`. The immutable v1 evidence remains
historical; a complete 33-record v2 corpus and generated v2 inputs now bind
clean cutover commit `12ca815`.
Rollback anchors, public admission, global attempt-bound proof, general
replacement, and independent administration remain deferred non-claims.

Active `Doing` tasks:

- `Doing` M5.3: reproduce the frozen local and evidence-processing paths from
  the inspected anonymous package on clean Linux and Windows/CI.
- `Doing` P1.7: obtain a verified clean remote Linux/Windows CI result for the
  final artifact state.

Next submission-critical technical task: M5 clean-host reproduction. The
implementation and evidence tooling reject profile-version mixing; the clean
v2 collection, processed summary, generated inputs, manuscript switch,
cue-policy narrative consolidation, current PDF inspection, approved license
split, and deterministic anonymous-package inspection are complete.

P3.4/P3.8, P4.12/P4.13, and other feature/evaluation breadth are parked as
`Todo` unless required by a retained-claim experiment. P4.2/P4.3/P4.4/P4.9,
P5.8, and P5.10 have scoped completions below; P5.6 is deferred after P5.13.

### Submission Execution Board

This board is the authoritative short-form sequence. Detailed phase entries
below preserve history and design context; they do not override this order.

| Order | Milestone | Status | Completion gate |
| --- | --- | --- | --- |
| M0 | Reconcile project state and freeze a clean baseline | `Done` | Current summaries match the verified implementation; the complete local gate and default Compose smoke pass; clean commit `1eaf18f` contains the P6.4/P7.17 tranche. |
| M1 | P7.15 deterministic result processing | `Done` | Generated fixtures prove exact ten-block validation, rejection rules, descriptive statistics, and raw-to-processed provenance without requiring paper data. |
| M2 | P7.16 generated manuscript inputs | `Done` | Versioned processing emits deterministic table inputs only from validated processed results; no plot is justified for version 1. |
| M3 | Retained P6.2-P6.4 and P7 collection | `Done` | A clean committed tree and pseudonymous host produce immutable aggregate-only attack evidence plus ten valid performance blocks; no development output is promoted. |
| M4 | Protocol, citation, manuscript, and consistency cutover | `Done` | The paper-facing construction and evidence use the unambiguous v4/v2 profile; all cited sources are verified; every headline claim maps to retained evidence or an explicit limitation; a fresh PDF passes page, anonymity, and visual checks. |
| M5 | Anonymous artifact and clean-host reproduction | `Doing` | Release authority and third-party redistribution are resolved; an allowlisted package contains no identifying metadata and reproduces the scoped smoke, negative-model, attack, and performance paths from clean Linux and Windows/CI environments. |
| M6 | Independent review and submission audit | `Todo` | Security, cryptographic, systems, paper-to-code, provenance, and submission-readiness blockers are closed or explicitly accepted. |

M5 work breakdown:

- `Done` M5.0 Reconcile `PLAN.md`, project guides, experiment documentation,
  attack/deployment status, and manuscript notation with the authoritative v2
  profile and evidence.
- `Done` M5.0.1 Add an optional synthetic-only in-process educational
  walkthrough for the exact three-pair canonicalizer, deployed v4 backup
  composition, and native 2-of-3 TPASS flow. The interface offers only
  numbered fictional aliases, generates its own test key, emits redacted stage
  summaries and generic recovery outcomes, writes no state, and is explicitly
  excluded from experiment evidence.
- `Done` M5.1 Freeze the release and anonymity contract: obtain the
  owner/institution license decision; inventory redistributed files; exclude
  incomplete or unverified third-party material; and define an allowlisted
  package with identity, credential, local-path, and prohibited-output checks.
  - Completion 2026-07-28: the owner confirmed distribution authority and
    approved Apache-2.0 for project-authored software/configuration and
    CC-BY-4.0 for project-authored documentation and aggregate experiment
    material. `LOCUS Authors` is the anonymous-review attribution. The
    read-only preflight passed for all 183 post-license candidate files with
    `archive_created: false`, release authorization `approved`, and the
    development tree still non-clean. The controlling license files are
    mandatory allowlist entries.
- `Done` M5.2 Build the anonymous artifact candidate from a clean committed
  state. The archive must exclude `.git`, development history/remotes,
  `extra/`, local build outputs, credentials, manuscript-only third-party
  files, and superseded evidence unless explicitly documented.
  - Initial post-license gate 2026-07-28: the complete gate validates
    repository boundaries, parses 65 Python files, passes Ruff and mypy over 66
    sources, runs 148 Python tests with one opt-in skip, passes 17 Rust core
    tests plus the fixed vector, and passes both Rust formatting/Clippy gates.
    The native build reports inclusion of `LICENSE`,
    `LICENSE-DOCUMENTATION.md`, and `LICENSES.md`. The clean-source candidate
    build and extracted-archive inspection are recorded below.
  - Candidate inspection 2026-07-28: clean commit `0a9caa2` produced a
    183-file archive and byte-identical repeat with SHA-256
    `9fbdb5ef86f05d3ed41216e57feded9835c4ef9cb7837b5d6a77819f21ea3cdb`.
    Every manifest size and digest matched the extracted files; the controlling
    licenses were present; forbidden/superseded paths were absent; and the
    extracted anonymity scan passed. The checklist and plan record were then
    committed before the final rebuild and inspection below.
  - Superseded candidate 2026-07-28: clean checklist-record commit `1a6e2d3`
    produced a 183-file archive with SHA-256
    `665ae663fb75c26dd0e1e94ddfe29573f291366067e9b4daf2693d40634f28a8`.
    A second build was byte-identical. Every manifest path, size, and digest
    matched the extracted files; the Apache-2.0, CC-BY-4.0, and inventory files
    were present; no forbidden or superseded path was present; and the
    extracted anonymity scan passed. The disposable repeat archive and
    extraction directory were removed. The first extracted-package check later
    exposed Git-only source/provenance assumptions, so this candidate was
    replaced rather than released.
  - Superseded packaged candidate 2026-07-28: clean commit
    `848f8142d9975230c6558f193ecd9ad5f1570341` adds strict extracted-manifest
    source validation, manifest-bound clean-commit provenance, and cold-run
    coordinator-test cleanup/timing robustness. Its 183-file archive had
    SHA-256
    `b231a5e192e2689da9d61608be8353cf38561b546eea20a2b2dfe52d9404743f`.
    A repeat build was byte-identical; every member path, size, digest,
    timestamp, file mode, and source-commit binding validated; controlling
    licenses were present; forbidden paths were absent; and the extracted
    anonymity scan passed. It was replaced because its landing and supporting
    documents still exposed internal planning labels and development-workspace
    commentary.
  - Reviewer-repository completion 2026-07-28: clean source commit
    `c3352a924f39b7437aff7da412429506c6dae93f` replaces the landing page and
    data guides with self-contained artifact documentation; restricts
    distributed documentation to reviewer guides and machine-readable schemas;
    excludes the internal release checklist and design notebooks; and rejects
    planning labels or submission-management language in packaged Markdown.
    The resulting 149-file archive has SHA-256
    `6170b81ec86f60a8adfdfb2fc53e5c88e07b00f5128dbe8c3552ada8fe214c0c`.
    A repeat build was byte-identical. All 149 manifest sizes and digests
    matched, forbidden reviewer paths were absent, and the extracted
    `artifact-submission/` language audit found no planning references. The
    complete source gate passes 152 Python tests with one opt-in live-S3 skip,
    17 Rust tests plus the fixed vector, and all formatting, linting, typing,
    and native-build checks.
- `Doing` M5.3 Reproduce the frozen quality, artifact-smoke, attempt-model,
  retained-v2 processing, and generated-paper-input paths on a clean Linux
  host; run the deterministic cue/drift vectors on clean Linux and Windows/CI.
  - Local package progress 2026-07-28: an isolated extraction on the existing
    Windows host, without `.git`, completed `uv sync --frozen`, the complete
    151-test gate, `artifact-smoke`, all seven bounded attempt-model scenarios,
    byte-identical v2 processing verification with canonical SHA-256
    `462e492795fafdd90a4f39851a612275193603d816f761728afe05e97a470a6b`,
    and unchanged v2 generated paper inputs. This is package-level Windows
    evidence on the development host, not a clean external-host or independent
    reproduction; Linux and Windows/CI clean-host execution remain.
  - Reproduction findings 2026-07-28: the first extracted candidate could not
    run repository hygiene or experiment metadata without Git history, and a
    cold-build run exposed an overly tight coordinator test deadline plus
    incomplete failure cleanup. The manifest now authenticates source paths,
    bytes, and the clean source commit; experiment provenance uses that commit
    when Git is intentionally absent; two manifest regressions, one provenance
    regression, and robust slow-party cleanup/deadlines cover the findings.
- `Done` M5.4 With Docker available, rerun the isolated deployment and S3
  gates from the package and record a privacy-safe machine-readable
  reproduction result with expected hashes.
  - Local package completion 2026-07-28: the extracted Windows package passed
    live S3 conformance, the complete same-host deployment smoke, and fresh
    development reruns of the cloud-only, one-party, and matching
    combined-snapshot scenarios. Each attack reported two synthetic candidates,
    zero candidate signals, zero network attempts, zero excluded-path accesses,
    valid snapshot/binding checks, and no prohibited/secret output under its
    exact schema. Final inventory found zero LOCUS containers, volumes, or
    networks. These unretained same-host reruns do not replace retained v2
    evidence or satisfy clean external-host/independent reproduction.
- `Todo` M5.5 Give the candidate to an unfamiliar reviewer and record every
  reproduction failure and fix without mutating retained v2 evidence.

M5.0 completion record (2026-07-27): current planning, experiment, deployment,
attack, authorization, limitation, and repository-hygiene documents now make
the corrected v4/v2 profile authoritative while preserving v1 as historical.
The manuscript distinguishes three TPASS holders from five authorizers and
treats all adversarial attempt bounds as deployment assumptions. The
allowlisted anonymous-package audit covers 181 candidate files and passes
without emitting matched identity values; archive creation remains blocked by
the explicit `PENDING` release decision and the dirty development tree. The
complete gate parses 65 Python files, passes Ruff/mypy over 66 sources, runs 148
Python tests with one opt-in live-S3 skip, and passes all Rust tests, formatting,
and Clippy. The complete artifact smoke, all seven bounded attempt-model
scenarios, byte-identical v2 processing verification, and unchanged v2
paper-input generation pass. Tectonic 0.16.9 rebuilt the visually inspected
14-page PDF; references begin on page 11 and its SHA-256 is
`3b68869bf99572e8bafa3efa4fb0fc4567e76aec093c0bcde3313f8d9e32c8e3`.
The live S3 conformance and complete same-host deployment smoke also pass from
the development tree, including party restart, alternate `[2,3]` recovery,
output scanning, and exact cleanup. Fresh development reruns of the registered
P6.2 cloud-only, P6.3 one-party, and P6.4 matching combined-snapshot scenarios
also pass with two synthetic candidates, zero candidate signals, zero network
attempts, zero excluded-path accesses, no prohibited output, and successful
snapshot/binding validation. A final Docker inventory found zero remaining
LOCUS containers, volumes, or networks. These unretained dirty-tree reruns are
preflight checks, not replacements for the immutable v2 evidence. Repeating
the gates from the clean anonymous package remains M5.4.

M5.0.1 completion record (2026-07-28): `tasks.py walkthrough` now presents five
display-safe fictional pair aliases, accepts only three numbered selections,
executes the exact deployed cue canonicalizer and native 2-of-3 TPASS
enrollment/recovery in process, and allows any two holders plus bounded retry.
The generated test key, canonical input, holder records, transcript material,
recovered secret, wrapping key, and ciphertext are never printed or persisted.
Five focused tests cover success with reordered input and an alternate holder
subset, wrong-selection generic rejection followed by success, budget
exhaustion, malformed/duplicate/out-of-range selection, interactive retry, and
known-value/output-category scanning. The post-change complete gate passes with
the 65/66-file and 148-test counts above. This interface is optional teaching
material and does not replace the service deployment or create evidence.

M4 work breakdown:

- `Done` M4.1 Freeze the exact paper-facing implementation mapping: cue input,
  recovery identifier, native password mapping, protected-secret digest,
  wrapping-key KDF, backup object, epoch/digest bindings, and AEAD associated
  data.
- `Done` M4.2 Reconcile the construction, algorithms, security arguments,
  abstract, introduction, and evaluation wording against M4.1 and the retained
  corpus.
- `Done` M4.3 Verify every cited bibliography entry against an authoritative
  source and rebuild mechanism-level related work around SafetyPin, SVR3, PPKR,
  TPASS, and the exact LOCUS delta.
- `Done` M4.4 Regenerate every included table from the immutable retained
  corpus, audit table/claim provenance, and remove all stale development-only
  wording.
- `Done` M4.5 Build a fresh review PDF and verify the 12-page main-text limit,
  appendix placement, anonymity, references, equations, tables, and visual
  layout.
- `Done` M4.6 Replace the ambiguous deployed metadata with
  `LOCUS-reference-backup-v4` plus the exact
  `LOCUS-location-person-set-v1` policy identifier, retain the generic scaffold
  under development-only identifiers, reject every legacy/mixed deployed
  profile before authorization, and provide immutable v1 plus strict v2
  evidence-processing paths.
- `Done` M4.7 From the clean M4.6 commit, collect P6/P7 v2 evidence under new
  immutable paths, process it as `LOCUS-performance-processed-v2`, generate
  `LOCUS-performance-paper-inputs-v2`, switch the manuscript inputs and
  disclosures, rebuild the PDF, and rerun the complete gate.

Current manuscript presentation record (2026-07-28): the contribution and
claim scope remain frozen. The abstract now foregrounds the implemented
cue-policy boundary, native TPASS composition, storage separation, retained
snapshot observations, and same-host latency results. The introduction
integrates the essential motivation and user-study context without a separate
background-and-motivation section; detailed human-study evidence remains in
related work, and the exactly-three location--person pairs remain only the
evaluated reference policy. Tectonic 0.16.9 produced a visually inspected
16-page `paper/main.pdf`; the main text ends and references begin on page 12.
All 28 cited keys resolve without undefined citation or reference warnings.
The PDF SHA-256 is
`3df29eca18b7ab29f85fcf9e8e4b9d9ac2e2c8f91ffda49549a452c2244481b0`.
This presentation record does not reopen M4, Phase 8, or Phase 10 and creates
no new implementation or human-subject evidence requirement.

Historical pre-cutover M4 completion record (2026-07-24): the complete pinned quality gate passed
(136 Python tests with one opt-in live-S3 skip, 17 Rust unit tests, one fixed
vector, formatting, lint, typing, and Clippy). Tectonic 0.16.9 produced the
visually inspected 14-page `paper/main.pdf`; main text ends and references begin
on page 11. Its SHA-256 is
`85bd106dc736917794807d46a5287e978e8ab3db03e699a8290d80f5d1a685b3`.
The paper-input generator also reported `status: unchanged`.

M4 consistency-cutover completion record (2026-07-24): clean commit
`12ca8157841088807863e2457b9fe5ee3e069e9f` introduced the strict
`LOCUS-reference-backup-v4` / `LOCUS-location-person-set-v1` /
`LOCUS-compose-deployment-v2` profile, development-only generic identifiers,
and exact v1/v2 evidence separation. The complete gate passed 139 Python tests
with one opt-in live-S3 skip, 17 Rust unit tests, one fixed vector, formatting,
lint, typing, and Clippy; the corrected deployment smoke passed with exact
cleanup. Three v2 snapshot records and 30 v2 performance records bind that
clean commit and pseudonymous host `cycle1-v2-host-a`. The processed summary
digest is
`462e492795fafdd90a4f39851a612275193603d816f761728afe05e97a470a6b`.
Tectonic 0.16.9 produced the visually inspected 14-page `paper/main.pdf`;
main text ends and references begin on page 11, and the PDF SHA-256 is
`019868297cc3bfd0311f4b2f285946eabdbdfebcb51f371ccdf013471b512a22`.

Submission-scope parking lot: VM/geographic deployment, realistic external
resolver integration, public OIDC/DPoP admission, global rollback-resistant
attempt control, general party replacement, full interactive client UX,
CPU/memory/concurrency/throughput breadth, broad cue-guessing studies, and
human-subject work are deferred unless the scoped paper is deliberately
reopened. They must not displace M0-M6.

Recently completed:

- `Done` M3 retained Cycle 1 collection: clean commit
  `812cb96cc5fba9d4332ae349eb6d664bac0f17b1` and pseudonymous host
  `cycle1-host-a` produced the three P6.2-P6.4 aggregate-only records and the
  exact 30-file P7 corpus for blocks `01`--`10` with seeds
  `2026072301`--`2026072310`. Every scenario passed output scanning and exact
  cleanup; a final audit found 33 records, one clean commit, one host label,
  one performance image ID, zero residual LOCUS Docker resources, and no dirty
  provenance. P7.15 accepted the corpus and emitted canonical summary digest
  `7c43963619c7e56a4c8716da19b11aeb06ccfa736b750a496caf37ee613cb2f5`;
  P7.16 emitted four manifest-bound LaTeX row files. Median enrollment was
  249.744 ms; median correct, one-party-unavailable, and wrong-input recovery
  latencies were 431.151, 453.017, and 444.740 ms respectively, with 30 samples
  each. These are same-host synthetic results, not production practicality or
  independent-administration evidence.
- `Done` M3 preflight correction: the first three paper-mode P6 runs on
  `2dcc62b` passed their exact aggregate reports and cleanup, but the
  performance preflight showed that Compose injects each disposable project
  label into the image configuration, producing a different image ID and a
  corpus P7.15 would reject. Those three otherwise valid records were moved to
  an ignored superseded-evidence path and will not be packaged. The runner now
  builds once per block under stable identity `locus-performance-image-v1` and
  passes the one inspected ID into all three scenarios. Two consecutive builds
  produced byte-identical ID
  `sha256:29e4e233ad6b6a8947e8cd6c9cc15b5d557902480ce2c3039cc9fadf25504cd5`;
  an unretained three-scenario block used that ID throughout and passed all
  outcomes, scanning, and exact cleanup.
- `Done` M2/P7.16 deterministic manuscript inputs:
  `LOCUS-performance-paper-inputs-v1` validates canonical processed bytes and
  emits fixed latency, phase, role-traffic, and storage LaTeX rows plus a
  manifest binding the source commit/host/path/digest, processing configuration,
  and every output digest. Generation is ASCII, deterministic, idempotent for
  identical content, refuses partial/unexpected output, and requires explicit
  replacement for changed content. Generated fixtures exercise the complete
  path without creating paper evidence. Version 1 deliberately emits no plot
  because the four tables are more precise and page-efficient. The complete
  gate parses 59 Python files; formatting, linting, and typing pass over 60
  sources; 136 Python tests pass with one opt-in skip; and all Rust tests, the
  fixed vector, formatting, and Clippy pass.
- `Done` M1/P7.15 deterministic performance-corpus processing:
  `LOCUS-performance-processed-v1` accepts only the exact ten-block,
  three-scenario canonical layout; rejects missing, extra, duplicate-member,
  noncanonical, wrong-path, mixed-commit/host/lock/runtime, unsafe, or
  derivation-inconsistent inputs; and exclusively emits exact input hashes,
  source series, Type 7 descriptive statistics, and deterministic
  SHA-256-indexed bootstrap median intervals. The normative schema, operator
  command, methodology, processed-data contract, and generated-fixture tests
  are synchronized. The complete gate parses 57 Python files; formatting,
  linting, and typing pass over 58 sources; 131 Python tests pass with one
  opt-in skip; and all Rust tests, the fixed vector, formatting, and Clippy
  pass. No retained performance data was created.
- `Done` M0/T1.4 project-state reconciliation and clean-baseline gate:
  synchronized the plan, root guide, attack/deployment status documents, threat
  model, claim-matrix date, and stale PDF page description with the implemented
  P6.4/P7.17 tranche. The authoritative board now parks non-scoped breadth and
  orders processing, retained collection, manuscript, artifact, and review
  work. The complete gate passes 128 Python tests with one opt-in skip, 17 Rust
  tests plus the fixed vector, repository hygiene, formatting, linting, typing,
  and Clippy; the unchanged current code also passes the default Compose
  recovery/restart/fallback/output-scan/cleanup gate.
- `Done` P7.17 frozen performance block runner and raw contract: `LOCUS-compose-performance-result-v1` now records the exact three-scenario configuration, seed-derived scenario position, per-sample index, one warm-up plus three attempts, phase and total latency, application-body bytes by role, canonical cloud-object size, aggregate client/party storage, Docker/Compose and image identities, output scan, and exact-label cleanup. It is cross-bound to provenance inside `LOCUS-compose-profile-evidence-v1`; paper mode requires a clean committed tree, labeled host, and immutable output path. The final unretained 2026-07-23 block with seed `20260723` ran wrong input, success, and party-1-unavailable recovery in the versioned order; all nine measured operations matched their expected generic outcome/subset, all three projects passed scanning and exact cleanup, and no raw file was retained. The complete gate passes 128 Python tests with one opt-in skip plus all Rust, formatting, typing, and lint checks. This is dirty, unlabeled development validation, not a paper-facing performance result.
- `Done` P7.1-P7.3 minimum Cycle 1 performance methodology: `docs/experiment-methodology.md` freezes the exact same-host claim boundary, native 2-of-3 TPASS over the five-service authenticated deployment, ten randomized three-scenario blocks, one warm-up plus three measured operations per fresh project, 30 recovery samples per scenario, enrollment/phase/bytes/storage metrics, no-outlier policy, invalid-run handling, descriptive statistics, immutable raw/processed/generated lifecycles, and limitations. Required scenarios are successful recovery, fixed wrong-input rejection, and recovery through `[2,3]` with party 1 stopped. CPU/memory, concurrency, throughput, VM/geographic, malicious-slow-party, and production claims are explicitly outside the minimum result.
- `Done` P1.11 retained-profile output safety: froze `LOCUS-compose-profile-evidence-v1` as the only retained Compose attack/benchmark/performance record. It binds exact experiment metadata to a registry-validated result and includes a fixed machine-readable trace policy. The exclusive writer validates, canonically serializes, synchronizes, rereads, and revalidates the byte-identical JSON file. Snapshot/database bytes, credentials, candidates, per-candidate outcomes, arbitrary logs, packet captures, core dumps, and exception traces are excluded. Every main/S3 Compose service has a zero core-file limit; the resolved graph requires it, and live default-deployment inspection verifies it for parties, resolver, and S3. Profile logs are canary-scanned then discarded at exact-project cleanup. The complete 55/56-file, 128-Python-test, Rust/Clippy gate and unchanged live deployment smoke pass. Privileged-host memory/crash collectors, engine internals, deleted blocks, and future external observability remain outside this evidence boundary.
- `Done` P6.4 combined cloud-plus-one-party persistent-snapshot attack: registered `cloud-plus-t-minus-one-party-snapshot-no-offline-predicate-v1`; bound the exact frozen P6.2 cloud and P6.3 party sub-snapshots in one exclusively published canonical manifest; independently validated matching backup identifier, epoch, digest, and TPASS public parameters; and tested two candidates in a separate non-root, credential-free, read-only, networkless container. Positive verifier, path/network, malformed, extra-file, sub-manifest substitution, and mismatched-enrollment controls fail closed. The unsaved 2026-07-23 Compose run was the development predecessor; M3 later collected the clean immutable retained record. Both matched the exact aggregate observation and cleanup. The result remains bounded implementation evidence, not a compromise mechanism, cryptographic proof, or cryptanalytic review.
- `Done` P6.3 one-party persistent-snapshot attack: registered `t-minus-one-party-snapshot-no-offline-predicate-v1`; froze and captured every persistent file from a stopped post-one-recovery synthetic `party1` volume; validated exact manifest, authorizer/TLS/native-TPASS/SQLite bindings; and tested two candidates in a separate non-root, credential-free, read-only, networkless container. Positive verifier, path/network, malformed, extra-file, manifest-consistent service substitution, and checkpoint-rollback controls fail closed. The unsaved 2026-07-22 Compose run was the development predecessor; M3 later collected the clean immutable retained record. Both matched the exact aggregate observation and cleanup. This remains bounded implementation evidence, not a compromise mechanism or cryptographic proof.
- `Done` P0.11 authorized defensive-security scope: `AGENTS.md` now records the repository owner's authorization for claim-scoped defensive testing of LOCUS using only repository-controlled code, synthetic state, bounded candidates, and disposable local services/storage. It requires assumed compromise to be represented by pre-generated state or test doubles; restricts adversarial traffic to explicitly named local endpoints; keeps offline runners networkless; prohibits external targets, real credentials/data, operational compromise techniques, destructive behavior, and reusable offensive tooling; and defines how shorthand approval of concrete proposed steps is normalized without expanding authority or bypassing safety/tool approvals.
- `Done` P6.2 cloud-only snapshot attack: registered `cloud-snapshot-no-offline-predicate-v1` and its exact report/schema contract; added a strict two-file `LOCUS-cloud-snapshot-input-v1`; captured exact S3 bytes through a one-shot cloud/client collection boundary; and executed two synthetic candidates in a separate non-root, credential-free, read-only, networkless container with counted file/socket guards. Focused positive-control, malformed, noncanonical, substitution, extra-file, schema, and redaction tests pass. The unsaved 2026-07-22 Compose run was the development predecessor; M3 later collected the clean immutable retained record with the same aggregate observation and cleanup. This is bounded implementation evidence, not a cryptographic proof, real-provider compromise, or statement about cue strength.
- `Done` P4.9/P6.9 same-membership lifecycle and cross-epoch profile: schema v5, signed old/new quorums, exact per-party runtime packages, pinned-mTLS lifecycle routes, retirement/activation, restart reconstruction, and successor recovery now pass locally, across five processes, and in the disposable Compose profile. The live profile also rejects post-preparation predecessor-context state substitution, preserves a 3/2 no-quorum split, validates a strict report, scans output, and removes all resources. This is not public administrator authorization, party replacement, rollback resistance, or a global attempt-bound result.
- `Done` P4.8 party timeout/retry/failover policy: added bounded classification-aware exact transport retries; concurrent 4-of-5 quorum collection under ten-second phase and 45-second operation deadlines; quorum-consistent 2-of-3 TPASS selection before authorization; concurrent 12-second TPASS phases; and no post-authorization subset switch or attempt restoration. Deterministic tests cover slow, unavailable, malformed, stale, conflicting, insufficient-quorum, timeout, exact-retry, and fixed-set cases. The live Compose gate recovered through `[1,3]`, preserved state across party-1 restart, then stopped party 1 and recovered through `[2,3]` at exactly `consumed=3`. The complete gate passed 95 Python tests with one opt-in skip, 17 Rust core tests plus the fixed vector, repository hygiene, Ruff, mypy, rustfmt, and Clippy. This is same-host compact-profile evidence, not Byzantine liveness, rollback resistance, or a global attempt-bound proof.
- `Done` 2026-07-21 foundation verification gate: repository hygiene, Ruff, mypy over 39 sources, 83 Python tests with one opt-in live S3 skip, 17 Rust unit tests, the Rust fixed vector, rustfmt, and clippy passed. Artifact smoke passed all three demos plus unsaved native/toy benchmark samples with explicit development warnings. The isolated Compose gate rebuilt the pinned image, validated role boundaries, recovered before/after party restart, passed the expanded output scan, and removed its resources. The final post-edit Python regression gate remained green.
- `Done` Phase 3 cue-claim audit/CLM-21: removed LOCUS-specific “human-memorable,” “personal-memorable,” claimed usability improvement, and comparative recall/reproducibility wording from the manuscript. The text now distinguishes exact deterministic software processing from the unevaluated human ability to retain/resupply cues, keeps prior work as motivation only, and retains explicit human-study/ethics limitations. `paper/main.pdf` remains stale because no LaTeX compiler is installed.
- `Done` P1.9 repository hygiene: documented tracked source/derived exceptions, ignored build/scratch outputs, and the immutable raw → reproducible processed → generated-paper lifecycle. Added tracked experiment directory contracts and a normal quality-gate check that rejects tracked Python caches, scratch benchmarks, or LaTeX byproducts. `paper/main.pdf` remains an intentional derived review snapshot; existing `paper/generated` toy rows are explicitly historical and not current paper evidence.
- `Done` P3.9 cue privacy data-flow diagram: added a Mermaid role/boundary flow plus a normative role-visible/prohibited-data table. It synchronizes the implemented resolver/client/party/cloud/output paths and explicitly separates storage/output evidence from unproven memory, trace, host, and independent-administration claims.
- `Done` P3.7 resolver drift simulation: added a strict client-side mapping for versioned deterministic directory responses and a committed scenario corpus. Renamed display entries and reindexed/within-grid map records preserve canonical bytes; map movement across the `e4` boundary and a changed selected contact produce canonical drift; profile-version changes, ambiguity, and missing results stop locally. Every local rejection uses one generic category, and the test-only stable/drift comparator is explicitly forbidden as a stored runtime verifier.
- `Done` P1.10/P1.11.1/P1.11.2/P3.2/P3.5/P3.6 foundation cleanup: added exact versioned experiment metadata with Git/lock/config/randomness/timestamp/host/raw-output provenance and a strict paper-evidence gate; added recursive output validation plus dynamic log canaries and a non-implemented, two-factor-gated design for any future unsafe synthetic inspection; bound the deterministic Compose fixture to one 511-byte canonical cue vector and SHA-256 digest; added locale/Unicode rejection cases; and confirmed the deployed client-only cue flow with recursive role-state audits. Privileged-host process memory, crash dumps, engine internals, deleted blocks, and future external observability remain explicit non-evidence boundaries rather than unfinished P1.11 claims.
- `Done` P4.10.1/P4.10.2 complete isolated deployment: added one digest-pinned multi-stage Linux image and a default Compose topology containing a networkless one-shot provisioner, deterministic three-pair resolver, SeaweedFS, five non-root recovery parties, and an ephemeral client. Three internal networks expose no host ports; five party volumes and the cloud volume are disjoint; each party receives only its own state/identity/database; only the client receives the runtime S3 credential and joins all role networks. The one-command `deployment-smoke` gate validates the resolved graph and live mounts/networks/users/environments, recursively audits provisioned snapshots, completes native 2-of-3 recovery through the S3 object, restarts party 1, completes the next exactly-once attempt, rejects known secret/cue/state markers in output, and removes all resources. The live gate passed on 2026-07-21. This is synthetic one-host container evidence, not independent administration, VM isolation, production cloud IAM, or the complete attempt-bound result.
- `Done` P4.7 end-to-end idempotency/replay slice: every implemented mutating POST requires one strict 32-byte key, durably binds it to the authenticated certificate fingerprint, method, exact route, and canonical request envelope before dispatch, and stores the exact completed HTTP status/body bytes before release. Schema v3 migrates schema v2 additively. Exact results survive reconstructed coordinators and process restart; changed caller/route/body/session/phase reuse conflicts; same-boot concurrent duplicates cannot execute twice. Lower ledger and native-phase state remains the authority after interrupted requests. Focused and subprocess tests cover missing keys, concurrent duplicate delivery, changed-body and cross-session reuse, delayed response replay, restart recovery, and deliberate fail-closed loss of native ephemerals. The full gate and artifact smoke are green with 72 passing Python tests plus one opt-in skip, 17 Rust unit tests, one fixed vector, and all quality checks. This does not establish DPoP admission replay protection, rollback resistance, or the global attempt bound.
- `Done` P4.5/P4.5.2 S3-compatible cloud adapter: added an explicit-credential `boto3==1.43.51` SigV4 adapter with path-style local addressing, HTTPS-by-default configuration, conditional `PutObject` create, SHA-256 transfer checksum, bounded streaming reads/timeouts/retries, exact-byte retry comparison, and application-level canonical/reference/digest validation independent of ETags or metadata. The shared filesystem/S3 contract covers enrollment/recovery, exact retry, immutable conflict, deletion, unavailable storage before attempt consumption, stale/substituted/corrupt/noncanonical/oversized data, and 409 retry behavior. `deploy/compose.s3.yaml` pins SeaweedFS 4.29 by OCI digest; `tasks.py s3-smoke` generates ephemeral credentials and a unique prefix, validates the resolved single-service loopback/network/volume boundary without printing credentials, runs the live contract, and removes the container/network/volume. The live gate and complete frozen gate at completion were green: 70 default Python tests passed with one opt-in live test skipped in default discovery, the live S3 test passed separately, 17 Rust unit tests and one Rust vector test passed, and Ruff/mypy/rustfmt/clippy passed. This focused result is local S3 conformance, not a real-provider result; P4.10.1/P4.10.2 later combined it with the parties.
- `Done` P4.5.1/P4.6 separated immutable-backup slice: added a 1 MiB bounded canonical cloud object/reference contract with atomic non-overwriting filesystem publication, exact-retry idempotency, safe key derivation, symlink/non-regular-file rejection, and explicit not-found/unavailable/corrupt/conflict/oversized outcomes. `LOCUS-reference-backup-v3` binds an explicit epoch into the TPASS context, HKDF info, AEAD associated data, backup digest, cloud reference, and party record. `LOCUS-attempt-config-v2` signs the backup digest and party database schema v2 persists it. Tests cover successful separated recovery, immutable conflict, stale-epoch substitution, corruption, noncanonical and oversized data, deletion/unavailability before attempt consumption, mismatched references, and recursive cloud/party snapshot separation. The authenticated five-process path now fetches the exact pinned object before authorization and decrypts its private key after remote native recovery. The full frozen gate passes 63 Python tests, 17 Rust unit tests, one Rust vector integration test, Ruff, mypy, rustfmt, and clippy. This remains a same-host filesystem adapter without S3, independent volumes, party-state rollback resistance, or global rollback detection.
- `Done` P4.2/P5.5 authenticated native-recovery slice: exposed strict unpadded-base64url commitment and response routes through the existing TLS 1.3 service. Each TPASS-capable process loads only its own canonical secret `PartyState`; authorizer-only processes load no TPASS state. Distinct pinned `party:<id>` certificates collect freshness only for that exact responding party, while the coordinator certificate can sequence ledger and recovery calls but cannot request freshness. A five-subprocess test completes correct 2-of-3 Ristretto recovery over noncontiguous and alternate subsets, maps exact commitment/response retries to stored bytes, consumes a wrong-input attempt whose final digest fails only at the client, continues recovery with one process down, catches it up after restart, rejects cross-session response reuse, and makes a commitment phase permanently unusable after process restart without restoring the count. This remains synthetic same-host evidence without admission, rollback resistance, cloud storage, or independent administration.
- `Done` Initial authenticated process-separation slice: refactored the coordinator behind a transport-neutral peer contract and added a strict TLS 1.3 HTTPS adapter for state summaries, durable entry/install votes, authorization-certificate installation, and live freshness votes. Both client and server certificates are CA-validated and exactly pinned; JSON is bounded, duplicate-free, and exact-schema. A five-subprocess test uses five SQLite databases, verifies generic malformed-request rejection and same-CA unauthorized-client rejection, installs/retries a 4-of-5 certificate, continues after one process is terminated, obtains live freshness, restarts that process, and catches it up to the identical installed certificate. The test also exposed and fixed restart enrollment incorrectly comparing a progressed ledger head with genesis. This is one-host ledger/process evidence only; TPASS routes, admission, rollback anchors, and independent deployment remain.
- `Done` Initial coordinator/freshness slice: added an untrusted collector with no signing key, quorum matching-head checks, conflicting-lock refusal, exact installed-certificate recovery/catch-up, durable two-phase collection, and quorum installation. Added party-signed response-freshness requests bound to the authorization, request, responding party, phase, process boot nonce, and fresh response nonce. Native parties now obtain and verify this certificate internally. Concurrent coordinators produce at most one conflicting-slot certificate; split locks fail closed.
- `Done` Initial P5.6 signed-certificate slice: added canonical Ed25519 authorizer configurations, attempt entries, entry votes, prepare certificates, install votes, and authorization certificates. Parties durably lock before returning entry votes and persist the full prepare certificate before install votes. The native party service now verifies a complete 4-of-5 two-phase certificate instead of accepting caller-asserted preverification. Focused tests reject insufficient, duplicate, forged, changed-entry, wrong-configuration, and conflicting durable votes.
- `Done` Initial P3.6 canonicalization slice: implemented the frozen exactly-three-pair policy with strict decimal coordinate parsing and half-even `e4` quantization, strict email/E.164 channels, duplicate/unknown-field rejection, association preservation, and order-independent sorting. All six permutations produce identical bytes; the legacy end-to-end flow remains intentionally unchanged until resolver fixtures and migration are ready.
- `Done` Initial P4.2/P4.4/P5.5 vertical slice: added a strict SQLite party store and transport-agnostic native party core. Authorization/head/count and phase intent commit before `prepare_commitment`; public commitment/response bytes are idempotent; concurrent local slot conflicts consume at most one position; open non-serializable phases fail closed on restart without restoring the count. The initial full frozen gate passed 44 Python tests, 17 Rust unit tests, one Rust vector integration test, Ruff, mypy, rustfmt, and clippy. Signed quorum verification was added by the next P5.6 slice; live freshness remains preverified, so this is not global attempt-control evidence.
- `Done` P4.1: Froze `docs/recovery-party-api.md`, covering two-step enrollment, OIDC/DPoP admission relay, ledger voting/install/catch-up, pre-commitment freshness, two TPASS phases, lifecycle/admin transitions, health/status/audit, bounds, idempotency, failure behavior, tests, and evaluation. The audit corrected the enforcement point: Rust `prepare_commitment`, not only the later response-share phase, is the first secret-dependent party operation.
- `Done` P3.1: Froze `LOCUS-location-person-set-v1`: exactly three distinct order-independent pairs, WGS 84 coordinates quantized to four decimal degrees, one strict email/E.164 person channel per pair, no public cue hints or hashes, explicit ambiguity/drift failure, and new-epoch-only migration. The retained deployment uses this policy; the variable-count/order-sensitive local core remains separate development scaffolding.
- `Done` P0.7: Completed the primary-source mechanism comparison. SafetyPin and SVR3 rule out a broad claim to first distributed, rollback-resistant, rate-limited recovery. The former candidate contribution was hardware-independent TPASS parties plus an exact request-bound budget; the 2026-07-22 scope decision below supersedes that candidate after P5.13 exposed the rollback gap.
- `Done` P2.6/P2.7/P2.8: Completed the attacker-controlled TPASS boundary audit, imposed a 255-party resource bound, made Python metadata/hex parsing canonical, added malformed coverage for every wire object, exhausted all valid subsets for `1 <= t <= n <= 5`, and added a frozen full-protocol synthetic vector regenerated in Rust and consumed through Python/PyO3. The exact frozen gate passes 38 Python tests, 17 Rust unit tests, one Rust vector integration test, Ruff, mypy, rustfmt, and clippy. The vector is not an independent cryptographic implementation or audit.
- `Done` P2.5: Replaced custom backup encryption and KDF code with pinned `cryptography` 49.0.0 AES-256-GCM and HKDF-SHA-256, introduced the strict `LOCUS-reference-backup-v2` format and canonical authenticated metadata, and added focused malformed/tamper/substitution tests plus the RFC 5869 vector.
- `Done` P2.4: Integrated the native Rust/Ristretto TPASS phases and canonical party-state encodings into the complete local LOCUS enrollment/recovery flow, made native the default, retained simulator/toy backends only through explicit selection, and verified `(2,3)`, `(3,5)`, and `(5,9)` recovery.
- `Done` P2.3: Added and documented a versioned canonical binary format for all external TPASS parameters/messages and secret party state while deliberately keeping client blinders and party ephemerals non-serializable.
- `Done` P1.6: Pinned Ruff 0.15.20 and mypy 2.3.0, formatted the Python scaffold, added stable lint/type configuration and task commands, introduced an explicit shared TPASS backend protocol, and passed all local quality and test gates.
- `Done` P1.2: Added the root project guide, safe-scope warning, setup and task commands, research boundaries, and anonymous-artifact warning.
- `Done` P1.3: Recorded the initial no-license-granted decision, third-party
  inventory, incomplete ACM LaTeX vendoring issue, and artifact release gates
  in `LICENSES.md`; M5.1 later superseded that initial decision with the
  approved Apache-2.0/CC-BY-4.0 artifact split.
- `Done` P1.4: Added `pyproject.toml`, `.python-version`, and `uv.lock`, pinning uv 0.11.29 and Python 3.12.13 without a user-specific runtime path.
- `Done` P1.5: Added the cross-platform `tasks.py` entry point for tests, checks, demos, scaffold benchmarks, local smoke testing, and the current artifact smoke path.
- `Done` P0.1: Completed read-only assessment of repository, paper, prototype, project instructions, and ASIACCS 2027 CFP.
- `Done` P0.2: Updated `AGENTS.md` and `PLAN.md` to reflect current state and working rules.
- `Done` P0.3: Selected ASIACCS 2027 Cycle 1 (2026-08-21 AoE). The original full-system scope was superseded by the explicit 2026-07-22 claim-scope decision after the bounded rollback counterexample.
- `Done` P2.1/P2.2: Documented the Yi et al. zero-knowledge TPASS mapping and selected the hybrid Python/Rust primitive and package-management stack.
- `Done` P0.4/P0.9: Created `docs/claim-evidence-matrix.md`, mapped every major manuscript claim to evidence or removal work, and identified unsupported present-tense attempt-control and memorability wording.
- `Done` P0.5/P5.1: Created the synchronized threat model and defined the exact distributed attempt-control target, assumptions, invariants, zero-overrun goal, failure behavior, tests, and evaluation requirements.
- `Done` P0.6: Froze the original research question around storage separation plus global rollback-resistant online-attempt control; TPASS is inherited rather than novel.
- `Done` P0.10 Scope preservation decision, 2026-07-22: P5.13 found a quorum-only conflicting-certificate trace after one honest database restore and a retired-epoch reauthorization trace. Rather than add an independent monotonic authority and change the LOCUS architecture, the Cycle 1 paper is reframed around storage-separated TPASS recovery, deterministic cue processing, concrete prototype evidence, and explicit boundaries. Global attempt bounding, party-state rollback resistance, public admission, general replacement, human memorability, independent administration, and production readiness are non-claims/future work. `docs/limitations-and-assumptions.md` is the scope contract; `docs/research-question.md` contains the revised contribution hierarchy.
- `Done` P5.3: Compared four attempt-control candidates and selected a recovery-party quorum-certified, hash-chained attempt ledger with an untrusted sequencing coordinator, explicit compact/resilient quorum profiles, and fail-closed availability tradeoffs.
- `Done` P5.2: Specified the selected ledger's entries, two-phase durable certificate protocol, coordinator/authorizer states, counted-attempt commit point, idempotency, crash recovery, live rollback freshness check, joint reconfiguration, invariants, and fail-closed partial-proposal behavior.
- `Done` P5.4: Selected request-bound OIDC/DPoP admission for ordinary attempts and enrollment-pinned threshold administrator signatures plus capped, disclosed extensions for high-impact actions; documented fresh-device flow, abuse, privacy, replay, identity-provider trust, and failure behavior.
- `Done` P1.1: Established the canonical `main` repository, pushed initial commit `7ee5cbeb178c6986b15139f7eff01d5a232dac1c` to `origin/main`, and excluded the local third-party `extra/` folder from version control.

Immediate execution gates, in order:

1. **Clean baseline gate:** complete for the scoped implementation and the
   corrected v4/v2 profile.
2. **Processing gate:** complete; P7.15 and P7.16 deterministically reproduce
   the retained v2 summary and generated paper inputs.
3. **Retained-evidence gate:** complete; three P6 records and 30 P7 records bind
   clean cutover commit `12ca815` and pseudonymous host `cycle1-v2-host-a`.
4. **Artifact preflight gate:** reconcile current documentation, resolve
   project and third-party redistribution decisions, and freeze an allowlisted
   anonymous-package contract.
5. **Clean-host gate:** reproduce the package on clean Linux and Windows/CI,
   including Docker-backed paths where available, then proceed to independent
   review. Do not reopen parked feature breadth.

Cycle 1 schedule checkpoints:

- **2026-07-22:** local crypto/repository gate passed; the first green remote CI
  remains unverified and rolls into M5.
- **2026-07-24:** mechanism-level novelty challenge, reference cue-policy
  contract, and service API are frozen ahead of checkpoint; M0 clean baseline
  freeze remains.
- **2026-08-02:** scoped architecture, prototype, threat model, and experiment methodology are consistent and reproducible.
- **2026-08-08:** retained-claim attack tests and core paper-facing measurements pass with provenance.
- **2026-08-12:** central attack and performance raw results collected with provenance.
- **2026-08-16:** manuscript and anonymous-artifact candidates exist with claim-evidence links.
- **2026-08-20:** final paper/artifact consistency, anonymity, reference, formatting, and reproducibility gates complete ahead of the 2026-08-21 AoE deadline.

These are risk-control checkpoints, not evidence that the compressed schedule is safe. Missing the 2026-08-02 or 2026-08-08 scoped-evidence checkpoints triggers an explicit Cycle 1 viability review; it must not be hidden by stronger wording or unrelated implementation breadth.

Current blockers and unresolved decisions:

- `Done` D1: Target ASIACCS 2027 Cycle 1 on 2026-08-21 AoE. The scoped architecture/implementation paper replaces the original full attempt-control thesis.
- `Done` D2: This folder is the canonical git repository; it was initialized on branch `main` on 2026-07-16.
- `Done` D3: Use Python for LOCUS orchestration, services, and experiments, with `uv`, `pyproject.toml`, and `uv.lock` for reproducible Python dependency management. Use Rust and Cargo for the security-critical TPASS core, with exact direct-dependency pins and committed `Cargo.lock`. P1.4 pins uv 0.11.29 and Python 3.12.13; P2.4 pins Rust 1.83.0, maturin 1.14.1, and PyO3 0.29.0; P2.5 pins `cryptography` 49.0.0. Contributors install uv as the documented bootstrap prerequisite rather than depending on a user-specific bundled runtime.
- `Done` D4: Use local S3-compatible storage for required reproducible experiments, with real cloud deployment optional. Decision update 2026-07-20: the planned MinIO image was rejected because the community repository is archived and the last official container predates a later security release. The local conformance service is now maintained SeaweedFS 4.29, pinned by OCI digest and accepted only after its S3 endpoint passed LOCUS's conditional-write contract. This does not treat the emulator as real-cloud evidence.
- `Done` D5: Use Docker and Docker Compose for isolated local recovery parties and supporting services. The 2026-07-27 audit used Docker 29.6.1 and Compose 5.3.0; after starting the local engine, the live S3 and complete deployment smoke gates passed with exact cleanup. Runtime version and engine availability are environment facts, not paper evidence. VM/cloud resources remain optional for extended evaluation.
- `Done` D6: Remove "human-memorable" from the title and abstract; do not make an unsupported human-memory claim.
- `Done` D7: Selected and implemented the zero-knowledge-proof-based TPASS construction from `extra/TPASS.pdf` as a Rust/Ristretto255 core in `tpass-core/`. The mapping, assumptions, deviations, and canonical external wire format are documented in `docs/crypto-design.md` and `docs/tpass-wire-format.md`; 17 focused Rust unit tests, one Rust vector integration test, 6 direct native-boundary Python tests, and 38 total Python tests pass. The complete local LOCUS flow uses this backend by default. Service integration and independent cryptographic review remain tracked and do not permit a production-ready or audited claim.
- `Done` D8: Use one Docker Compose project to orchestrate the complete local infrastructure. The default deployment will include an ephemeral client CLI, separately identified recovery-party containers with independent durable state, an S3-compatible object store, and a deterministic resolver. Scriptable commands are the reproducible interface; an interactive menu wraps them. Separate profiles provide benchmark and attack runners. Normal observability is redacted, while any secret-revealing educational mode is synthetic-only, explicitly unsafe, and excluded from paper-facing runs.
- `Todo` D9: The current GitHub origin and initial commit contain personal identity metadata. Treat this as the development/backup repository only; before double-blind submission, P9 must create and inspect a sanitized anonymous artifact with anonymous commit/package metadata and no personal repository URL.
- `Done` D10: Do not add a monotonic witness, public OIDC/DPoP admission, or another safety authority for Cycle 1. These would materially change the paper idea. Record them as possible future remedies and state that the current prototype is not globally rate-limited or rollback-resistant.

## Current State Baseline

`Done` Verified working-tree assessment, 2026-07-27:

- The complete local gate parses 65 project Python files; Ruff formatting,
  Ruff linting, and mypy pass over 66 sources; 148 Python tests pass with one
  opt-in live-S3 test skipped; 17 Rust core tests plus the fixed-vector test
  pass; and both Rust crates pass formatting and Clippy.
- The native Rust/Ristretto255 TPASS core, canonical wire format,
  HKDF-SHA-256/AES-256-GCM backup format, filesystem/S3-compatible stores,
  deterministic three-pair resolver, authenticated five-party services,
  per-party SQLite state, same-membership lifecycle, and output-safety
  controls are implemented for the exact documented same-host scope.
- The default Compose smoke rebuilds the reference image, audits the role graph,
  recovers before and after a party restart, recovers through `[2,3]` with
  party 1 stopped, scans output, and removes all exact-project resources.
- P5.13 reproducibly finds the quorum-only rollback fork and restored-retirement
  counterexample. Global rate limiting and party-state rollback resistance are
  non-claims.
- P6.2, P6.3, and P6.4 have retained aggregate-only observations. P7 has 30
  retained measurements per scenario across ten blocks, a canonical processed
  summary, and manifest-bound generated table rows.
- `experiments/raw/` contains the authoritative 33-record v2 set plus the
  immutable historical 33-record v1 set. The current deterministic summary is
  `experiments/processed/performance-v2/summary.json`, and the current
  manifest-bound inputs are below `paper/generated/performance-v2/`.
- `paper/main.tex` and `paper/main.pdf` match the corrected v2 manuscript. The
  visually inspected PDF is 14 pages, with references beginning on page 11;
  its SHA-256 is
  `3b68869bf99572e8bafa3efa4fb0fc4567e76aec093c0bcde3313f8d9e32c8e3`.
  Every currently cited entry has been verified; unused bibliography entries
  remain outside that audit.
- The development repository and Git history contain identifying metadata.
  No anonymous artifact package or independently reproduced clean-host result
  exists. Project release authority and third-party redistribution decisions
  are unresolved, and the configured GitHub workflow still needs a verified
  remote green run for the final committed state. The local 2026-07-27
  Docker-backed S3 and deployment preflight passed, but a clean-package
  external-host reproduction does not yet exist.

The release-authority portion of this dated assessment was superseded by the
M5.1 authorization record on 2026-07-28; the remaining package, clean-host, and
remote-CI gaps still apply.

Highest acceptance risks:

- `Accepted risk` R1: The scoped LOCUS paper may look like integration of known TPASS and backup ideas. Mitigate through precise composition, concrete native implementation, negative-result analysis, reproducible evaluation, and mechanism-level comparison; do not hide the risk by claiming unfinished attempt control.
- `Accepted risk` R2: Current paper-facing results are retained but
  same-host/local and do not support strong practicality claims.
- `Done` R3: The M4 claim audit removed unsupported human-memorability and
  positive global attempt-control wording; keep this closed by rerunning the
  claim audit after manuscript edits.
- `Accepted risk` R4: One pinned Compose path provides explicit same-host role
  boundaries but not independent administration, credential lifecycle,
  VM/multi-host operation, or realistic Internet failure evidence.
- `Doing` R5: Local reproducibility, retained provenance, and deterministic
  processing exist; anonymous clean-host reproduction and a verified remote CI
  run remain.
- `Done` R6: Every currently cited source was verified in M4. Unused
  bibliography entries must be removed or verified before artifact release.

## Target Contribution Strategy

Primary technical thesis:

> LOCUS should show how a storage-separated private-key recovery architecture combines deterministic structured input with TPASS so that cloud and below-threshold snapshots do not become offline cue-testing oracles, while exposing the residual online, resolver, lifecycle, and deployment limitations through a reproducible prototype.

Contribution outcome trackers (these are end-state targets, not phase-task statuses):

- C1: End-to-end LOCUS architecture separating cloud backup storage, recovery-party state, cue processing, and resolver privacy boundary.
- C2: Deterministic structured-cue policy with explicit normalization, drift, ambiguity, and privacy behavior.
- C3: Concrete native-cryptography research prototype with durable same-host role separation.
- C4: Claim-scoped security and failure evaluation for the retained architecture properties.
- C5: Bounded negative result showing why the partial ledger is not rollback-resistant global attempt control.
- C6: Reproducible core performance and resilience characterization without practicality overclaiming.

Active non-goal guardrails (continuous constraints, not unfinished work):

- NG1: Do not claim paper acceptance is guaranteed.
- NG2: Do not prove or claim long-term cue memorability without a human-subject study.
- NG3: Do not claim personal cues have high entropy.
- NG4: Do not claim production-ready or audited cryptography.
- NG5: Do not solve confidentiality after compromise of at least `t` recovery parties.
- NG6: Do not guarantee availability with fewer than `t` reachable parties.

## Paper Claim Gate

Before adding or retaining a major claim, apply this recurring gate:

- G1: What exact property is claimed?
- G2: Under which adversary and assumptions?
- G3: Is the property inherited from TPASS, introduced by LOCUS, or operational?
- G4: What proof, test, experiment, or citation supports it?
- G5: Can the result be reproduced?
- G6: What residual risk remains?
- G7: Is the wording stronger than the evidence?

If any answer is missing, the claim is not ready for the abstract or contribution list.

## Current Paper Claims Requiring Evidence

The evidence-state labels in this table are descriptive claim-audit labels, not task-status labels.

| Evidence State | Claim Area | Current Support | Required Before Submission |
| --- | --- | --- | --- |
| `Partial` | Correct native recovery and threshold behavior | Local/native tests, five authenticated processes, default Compose recovery/restart/fallback, and provenance-bound retained performance runs pass | Anonymous clean-host reproduction and independent cryptographic/systems review |
| `Partial` | Cloud-only no offline cue verifier | P6.2 strict snapshot and retained networkless bounded run pass with immutable aggregate provenance | Preserve the claim-scoped argument and limitations; complete anonymous clean-host reproduction |
| `Partial` | Below-threshold party snapshot | P6.3 exact stopped-party snapshot and retained networkless bounded run pass with immutable aggregate provenance | Preserve the inherited-TPASS argument and limitations; complete independent review and anonymous reproduction |
| `Partial` | Matching cloud plus below-threshold snapshot | P6.4 manifest-bound union and retained networkless bounded run pass with immutable aggregate provenance | Preserve the inherited-TPASS argument and limitations; complete independent review and anonymous reproduction |
| `Partial` | Cloud-object integrity and lifecycle mixing | Canonical digest/epoch binding, malformed/tamper tests, and cross-epoch Compose scenario pass | Retained claim-scoped evidence and clean-host reproduction; preserve the honest-current-metadata condition |
| `Supported` only conditionally | Online guessing equation | Elementary `min(1,k*2^-h)` bound | Preserve the explicit premise that deployment—not LOCUS—enforces `k`; do not claim measured `h` |
| `To remove` as a positive claim | Global rate limiting, rollback resistance, and durable audit security | P5.13 reproduces quorum-only rollback and restored-retirement counterexamples | Keep only exact local implementation facts and the bounded negative result |
| `Partial` | Deterministic cue and resolver boundary | Frozen policy/vector/drift corpora and isolated resolver path pass | Clean Linux/Windows execution, retained boundary evidence, and conservative metadata analysis |
| `Partial` | End-to-end prototype cost | Ten retained three-scenario blocks, canonical processed summary, manifest-bound generated rows, and manuscript latency-table integration | Anonymous clean-host reproduction; retain same-host/synthetic limitations and avoid scalability, concurrency, geographic, or production claims |
| `Partial` | Reproducible artifact | Frozen dependencies, local gates, schemas, profiles, and metadata contracts exist | Remote CI, sanitized anonymous package, clean-machine and independent reproduction |
| `Supported` as a non-claim | Human memorability/usability | Manuscript and claim matrix explicitly disclaim LOCUS-specific human evidence | Preserve wording unless a separately approved human-subject study exists |

## Phase 0 - Scope, Claims, And Decision Baseline

Objective: freeze the research objective, evidence plan, and highest-risk decisions before large implementation changes.

Dependencies:

- `Done` Current assessment.
- `Done` User decisions D1-D7.

Tasks:

- `Done` P0.1 Read-only repository, paper, prototype, planning, and ASIACCS CFP assessment.
  - Result: current project is promising but not submission-ready; primary gap is distributed durable attempt control.
- `Done` P0.2 Refresh `AGENTS.md` and `PLAN.md`.
  - Result: documents now reflect current state, risks, and living-plan rules.
- `Done` P0.3 Decide target ASIACCS cycle and scope.
  - Subtask `Done` P0.3.1 Target ASIACCS 2027 Cycle 1 on 2026-08-21 AoE.
  - Subtask `Done` P0.3.2 Retain the full-system paper scope and the complete action plan; compress execution rather than removing steps.
  - Result: Cycle 1 and the full-system scope are fixed. The deadline is schedule-critical, but completion and evidence requirements are unchanged.
- `Done` P0.4 Create `docs/claim-evidence-matrix.md`.
  - Subtask `Done` P0.4.1 Added 24 scoped claim rows covering the current manuscript and planned systems/artifact claims.
  - Subtask `Done` P0.4.2 Marked every claim as supported, partial, planned, or to remove.
  - Subtask `Done` P0.4.3 Linked every claim to required implementation, experiment, proof, citation, limitation, or removal work.
  - Result: every abstract/introduction claim has an evidence path or removal task; current rate-limit/audit and memorability overclaims are explicitly gated.
- `Done` P0.5 Create `docs/threat-model.md`.
  - Subtask `Done` P0.5.1 Defined 16 adversary classes covering cloud-only, below-threshold, combined, online/public/social guessing, resolver, replay/network, rollback, malicious/unavailable parties, concurrency, lockout DoS, endpoint, threshold, Docker-host/debug, identity-provider, and administrative-authority compromise.
  - Subtask `Done` P0.5.2 Recorded capabilities, information obtained, claimed property, residual risk, evidence, and limits for every adversary.
  - Result: the threat model matches the intended Docker/service architecture, current evidence boundaries, claim matrix, and P5.1 assumptions.
- `Done` P0.6 Create `docs/research-question.md`.
  - Historical result: the original research question and contribution hierarchy centered distributed request-bound attempt control. This was superseded on 2026-07-22 by P0.10 and the architecture/prototype scope in `docs/research-question.md` after the P5.13 counterexample.
- `Done` P0.7 Create `docs/related-work-comparison.md`.
  - Subtask `Done` P0.7.1 Compared LOCUS against TPASS/PPSS, password-protected backups, recovery codes, social recovery, cloud/HSM retrieval, privacy-preserving account recovery, guardian/audit systems, and fuzzy/biometric recovery using primary sources.
  - Subtask `Done` P0.7.2 Identified SafetyPin and SVR3 as the nearest systems and serious novelty challenges.
  - Result: broad distributed/rate-limited/rollback-resistant recovery novelty is rejected. The conditional candidate is exact request-bound accounting across arbitrary TPASS subsets, concurrent/failure cases, and joint lifecycle changes without HSM/enclave trust; `docs/related-work-comparison.md` records the evidence required before that wording may enter the paper.
- `Done` P0.8 Decide paper title/abstract direction.
  - Result: "human-memorable" was removed from the title and abstract source on
    2026-07-16 and replaced with conservative structured-recovery-cue wording.
    The 2026-07-24 M4 audit rebuilt and visually checked the current source and
    found no remaining LOCUS memorability or comparative-usability claim.
- `Done` P0.9 Audit current manuscript claims.
  - Result: every major claim in `paper/main.tex` is represented in `docs/claim-evidence-matrix.md`; required wording corrections remain tracked in that matrix and Phase 10.
- `Done` P0.10 Reconcile stale `paper/related_work.tex`.
  - Result 2026-07-21: the file is explicitly labeled as a historical, unverified, non-authoritative draft and remains excluded from `paper/main.tex`. It must not be cited, included, or shipped as submission evidence unless it is reconciled against verified primary sources; the authoritative comparison is `docs/related-work-comparison.md` and the included Related Work section in `paper/main.tex`.
  - Completion: file is either integrated, removed in a later hygiene step, or explicitly marked as historical draft.

Phase 0 completion criteria:

- `Done` Every headline claim has planned evidence or a removal path.
- `Done` No headline claim requires an unplanned human-subject study.
- `Done` The novelty can be explained without calling TPASS novel.
- `Done` The submission cycle and scope are recorded.

## Phase 1 - Reproducible Repository Foundation

Objective: create a clean development and artifact foundation.

Dependencies:

- `Done` Phase 0 decisions.

Tasks:

- `Done` P1.1 Initialize or confirm canonical git repository.
  - Subtask `Done` P1.1.1 Added `.gitignore` for Python caches, LaTeX byproducts, benchmark outputs, local credentials, temporary PDF-review files, and Rust build outputs.
  - Subtask `Done` P1.1.2 Preserved the reviewed project files, created initial commit `7ee5cbeb178c6986b15139f7eff01d5a232dac1c`, and synchronized `main` with `origin/main`.
  - Subtask `Done` P1.1.3 Excluded `extra/` and confirmed `extra/TPASS.pdf` is ignored and untracked because third-party redistribution rights are not established.
  - Result: a clean version-control baseline exists. The personal GitHub origin is development-only and must not be used as the double-blind artifact link.
- `Done` P1.2 Add root `README.md`.
  - Result: the guide explains the research goal, current implementation boundary, layout, prerequisites, frozen setup, task commands, security/privacy constraints, and double-blind artifact warning.
  - Completion: explains project status, layout, setup, tests, and non-production warning.
- `Done` P1.3 Add license or record license decision.
  - Result: `LICENSES.md` initially recorded that no public reuse license had
    been granted, inventoried known third-party material, identified incomplete
    ACM LaTeX vendoring and unresolved auxiliary-file provenance, and defined
    the release gate. M5.1 later records the authorized Apache-2.0 software and
    CC-BY-4.0 documentation/aggregate-material split while continuing to
    exclude the manuscript and unresolved third-party files.
  - Completion: artifact redistribution policy is clear.
- `Done` P1.4 Add Python project/dependency management.
  - Subtask `Done` P1.4.1 Use `uv`, as fixed by D3.
  - Subtask `Done` P1.4.2 Pin uv 0.11.29, Python 3.12.13, the supported Python 3.12 range, and the dependency-empty Python environment in committed metadata and `uv.lock`.
  - Subtask `Done` P1.4.3 Ordinary setup uses `uv sync --frozen`; the repository no longer documents a user-specific bundled Python path as its normal setup.
  - Verification: `uv sync --frozen` completed with CPython 3.12.13 on 2026-07-17.
  - Completion: clean checkout can install dependencies reproducibly.
- `Done` P1.5 Add `Makefile` or equivalent task runner.
  - Subtask `Done` P1.5.1 Document `uv sync --frozen` as the reproducible setup command.
  - Subtask `Done` P1.5.2 Add a cross-platform test command covering the Python and Rust suites.
  - Subtask `Done` P1.5.3 Add the initial check command for Python syntax, Rust formatting, Rust clippy, and tests; P1.6 subsequently added pinned Python formatting, lint, and type checks.
  - Subtask `Done` P1.5.4 Add the local smoke command for tests and both reference demos.
  - Subtask `Done` P1.5.5 Add an artifact smoke command covering checks, tests, both demos, and one unsaved scaffold benchmark sample.
  - Subtask `Scoped` P1.5.6 Add one-command Docker Compose deployment,
    benchmark, performance, and attack entry points.
    - Progress 2026-07-21: `deployment-smoke`, `deployment-demo`, `deployment-benchmark`, and `deployment-attack` now create, exercise, and fully remove disposable Compose graphs. Explicit long-lived startup/shutdown and the fuller lifecycle CLI remain dependent on P4.9 and the P3.4/P5 admission interface.
    - Scope decision 2026-07-23: the disposable commands plus
      `deployment-performance-block` satisfy the scoped artifact/experiment
      interface. Long-lived operator startup/shutdown and a public lifecycle UI
      are deferred.
  - Verification: `uv run --frozen python tasks.py check`, `smoke`, and `artifact-smoke` passed on 2026-07-17; 21 Python tests and 10 Rust tests passed, and Rust formatting/clippy were clean.
  - Completion: common tasks are documented and runnable.
- `Done` P1.6 Add formatter, linter, type checker, and test configuration.
  - Result: `pyproject.toml` pins Ruff 0.15.20 and mypy 2.3.0 and contains stable Python 3.12 configuration. `tasks.py format` performs deterministic formatting/safe fixes, while `tasks.py check` enforces Ruff formatting/linting, mypy, Rust formatting/clippy, and both test suites.
  - Result: static checking motivated an explicit structural `TpassBackend` interface, typed concrete-backend round state, stricter integer input narrowing, explicit equal-length `zip` behavior, and bound benchmark closures. These changes preserve the reference protocol behavior and all failure tests pass.
  - Verification: 11 Python files pass Ruff and mypy; 21 Python tests and 10 Rust tests pass under the pinned environment; the full artifact smoke command passes.
  - Completion: checks run locally and produce stable results.
- `Doing` P1.7 Add CI workflow.
  - Result to date: `.github/workflows/ci.yml` uses read-only permissions and immutable action SHAs, runs frozen checks on `ubuntu-latest` and `windows-latest`, and gates an Ubuntu artifact-smoke job on both platform checks. `rust-toolchain.toml` pins Rust 1.83.0 with rustfmt and clippy.
  - Remaining verification: run the final artifact state through clean remote
    Linux and Windows jobs and record the first green result. A local workflow
    definition cannot satisfy this remote completion criterion by itself.
    Repository publication and pushing remain owner-controlled actions.
  - Completion: CI runs tests and basic checks on clean checkout.
- `Done` P1.8 Create initial `docs/` structure.
  - Result 2026-07-21: `docs/` contains the architecture, research question, threat model, cryptographic/protocol designs, attempt-control design, cue policy, deployment contract, experiment metadata contract, and claim-evidence matrix. Later phases extend these living documents rather than creating a second structure.
  - Completion: docs include architecture, threat model, protocol, attempt control, cue policy, deployment, experiment methodology, and claim-evidence matrix placeholders.
- `Done` P1.9 Separate generated artifacts from source.
  - Result 2026-07-21: `docs/repository-hygiene.md` classifies tracked source, intentional derived snapshots/LaTeX inputs, ignored caches/build products, disposable benchmark scratch, immutable raw results, reproducible processed data, and generated manuscript inputs. `experiments/raw/` and `experiments/processed/` now have explicit contracts; `.gitignore` covers Python/Rust/LaTeX/coverage/build scratch; normal `tasks.py check` rejects prohibited tracked outputs.
  - Subtask `Done` P1.9.1 Root `paper/*.aux`, `.log`, `.bbl`, `.blg`, `.fls`, `.fdb_latexmk`, `.out`, `.synctex.gz`, `.toc`, `paper/_build/`, and Python cache/coverage/build outputs are ignored and rejected if tracked. `paper/main.pdf` is a deliberate derived review snapshot and must match source.
  - Subtask `Done` P1.9.2 `prototype/.benchmarks/` is ignored development scratch and cannot be promoted manually; paper evidence must be clean, provenance-complete, retained raw output under `experiments/raw/`.
  - Completion: repository hygiene is explicit and reproducible.
- `Done` P1.10 Define experiment metadata schema.
  - Result 2026-07-21: `LOCUS-experiment-metadata-v1` has an exact JSON schema and stricter executable validator. Benchmark results now record UTC interval, exact Git commit/dirty state, SHA-256 of all Python/Rust locks, pseudonymous host class, complete configuration, explicit CSPRNG/orchestrator-seed provenance, and repository-relative raw-output retention. `paper` evidence fails closed for a dirty tree, unlabeled host, unretained result, warning, or path outside `experiments/raw/`; unsaved development smoke results remain clearly warned and cannot be mistaken for paper evidence.
  - Verification: focused metadata tests, both unsaved benchmark backends, the 39-source full quality gate, and artifact smoke passed on 2026-07-21. Development samples correctly recorded dirty/unlabeled/unretained warnings and were not written.
  - Completion: future runs record commit, dependency lock hash, host, configuration, seed, timestamps, and raw output locations.
- `Done` P1.11 Add secret-redaction/logging guardrails.
  - Result 2026-07-23: `prototype/locus/redaction.py` rejects prohibited fields at any JSON depth, private-key blocks, non-finite/non-JSON values, and pathological output. Demo, deployment, benchmark, and benchmark-table paths validate before serialization; experiment configurations use the same guard; paper-table output additionally requires validated `paper` evidence metadata. Operator diagnostics expose an exception class only, never its potentially sensitive message. Deployment/profile paths scan combined logs/output for static markers and per-run secret/cue canaries and report labels only.
  - Subtask `Done` P1.11.1 Tests or checks catch logging of raw cues, derived cue IDs, TPASS passwords, TPASS shares/states, wrapping keys, private keys, recovered secrets, or party-local cryptographic randomness.
  - Subtask `Done` P1.11.2 `docs/output-safety.md` defines a future two-factor, committed-synthetic-fixture-only inspection mode that must refuse normal, benchmark, attack-result, paper, CI, retained-output, and network-service use. The mode is deliberately not implemented or activatable yet.
  - Subtask `Done` P1.11.3 Freeze `docs/retained-profile-evidence.md`, `LOCUS-profile-trace-policy-v1`, the exact profile-evidence/report schemas, metadata/result cross-binding, canonical exclusive synchronized publication, and aggregate-only P6.2-P6.4 retention. Every current Compose service disables core files; resolved/live checks enforce the existing boundary; arbitrary service logs are scanned then discarded instead of retained.
  - Verification 2026-07-23: focused exact/binding/redaction/path/exclusive-write tests and the complete gate pass; repository boundaries parse 55 Python files; Ruff and mypy pass 56 sources; 127 Python tests run with one live-S3 skip; 17 Rust tests plus the fixed vector and both Rust format/Clippy gates pass. The live default deployment verifies zero core-file limits on parties/resolver/S3, recovers across restart and fallback, scans output, and removes every resource. An initial validator mismatch against Compose's zero-eliding JSON failed before startup and cleaned up; the corrected validator and Docker live inspection passed.
  - Completion: normal implemented terminals, status outputs, profile logs, retained evidence, and repository-created Compose trace policy expose no prohibited secret material. Privileged-host memory/crash collection, engine internals, deleted blocks, and future external observability are explicit non-evidence boundaries rather than hidden coverage claims.

Phase 1 completion criteria:

- `Scoped` The current checkout installs and passes documented local commands;
  a truly clean external-host reproduction remains M5.3.
- `Done` Current unit tests pass through the task runner: 83 Python tests passed with one opt-in live S3 test skipped; 17 Rust unit tests plus one fixed-vector integration test passed; Ruff, mypy, rustfmt, and clippy were green on 2026-07-21.
- `Done` Generated and source files are clearly separated and checked by the normal quality gate.
- `Doing` The final artifact state passes Linux and Windows CI.

## Phase 2 - Concrete Cryptographic Core

Objective: replace toy/demo cryptography for paper-facing experiments while preserving clear research-prototype boundaries.

Dependencies:

- `Done` Phase 0 claim and protocol decisions.
- `Done` Phase 1 test foundation.

Tasks:

- `Done` P2.1 Create `docs/crypto-design.md`.
  - Subtask `Done` P2.1.1 Documented the selected Yi et al. zero-knowledge-proof-based TPASS construction and its additive protocol mapping.
  - Subtask `Done` P2.1.2 Documented Ristretto255, approximate security level, generators, encodings, SHA-512 hash-to-scalar, AES-256-GCM, HKDF-SHA-256, randomness, parameter validation, assumptions, and limitations.
  - Result: the design was reviewed against `extra/TPASS.pdf` before implementation.
- `Done` P2.2 Decide concrete primitive stack.
  - Result: Python plus `uv` for orchestration and experiments; Rust plus Cargo and `curve25519-dalek` Ristretto255 for TPASS; SHA-512 protocol transcripts; HKDF-SHA-256 and AES-256-GCM through the Python `cryptography` library for the backup path.
- `Done` P2.3 Implement canonical binary serialization.
  - Result: `tpass-core/src/wire.rs` defines an exact versioned format for public parameters, secret party state, client requests, party commitments, response shares, and gateway responses using big-endian integers, length-prefixed identifiers, canonical Ristretto point/scalar encodings, canonical party ordering, exact type/version tags, and trailing-data rejection.
  - Result: client sessions/blinders and party proof ephemerals are deliberately non-serializable. `docs/tpass-wire-format.md` records the layout, threat assumptions, invariants, failure behavior, and evidence boundary.
  - Verification: a complete 3-of-5 Rust protocol round-trips every external object; tests reject wrong object types, trailing bytes, and a non-canonical secret scalar.
  - Completion: serialization is unambiguous and round-trip tested.
- `Done` P2.4 Implement paper-facing TPASS/PPSS backend.
  - Result: `tpass-core/` implements enrollment, client request, one-phase server proofs, proof verification, response shares, gateway aggregation, final digest validation, and canonical external encodings over Ristretto255. `tpass-python/` exposes those phases through a pinned PyO3 abi3 extension built by maturin; it uses canonical byte messages, redacted native secret objects, operating-system randomness, and no global handle registry.
  - Result: `prototype/locus/core.py` uses the native backend by default for complete local enrollment and private-key recovery. Public parameters and independent party states are persisted as typed, versioned wire encodings; simulator and toy safe-prime paths require explicit selection.
  - Verification: complete native LOCUS recovery succeeds for `(2,3)`, `(3,5)`, and `(5,9)` including non-contiguous threshold subsets; wrong cues, malformed state, metadata mismatch, insufficient parties, and backup/ciphertext failure cases reject. The current frozen gate passes 35 Python tests and 13 Rust tests, all three demos pass, and one unsaved native benchmark smoke run covers the configured matrix.
  - Limitation: this is local composition evidence. Network services, durable state, distributed attempt control, fixed vectors, property tests, and independent cryptographic review remain separate tasks.
  - Completion: correct recovery succeeds across target `(t,n)` configurations with realistic parameters.
- `Done` P2.5 Replace demo encryption for paper-facing path with standard AEAD.
  - Result: `prototype/locus/crypto.py` uses `cryptography==49.0.0` for AES-256-GCM and HKDF-SHA-256. `LOCUS-reference-backup-v2` stores an exact four-field `LOCUS-AES-256-GCM-v1` object with a fresh 96-bit nonce, full appended 128-bit tag, strict lowercase-hex encoding, and exact 256-bit key enforcement.
  - Result: canonical associated data authenticates the backup/AAD versions, backup identifier, recovery nonce, TPASS public parameters, context/security policies, and cipher-suite identifiers. `docs/backup-cryptography.md` specifies the format, invariants, failure behavior, tests, evaluation, and claim limits.
  - Verification: direct tests cover round trip, nonce freshness, wrong AAD, nonce/ciphertext tampering, strict format/key/length rejection, and RFC 5869 HKDF test case 1. Complete-flow tests cover ciphertext substitution, authenticated-policy substitution, and malformed-format rejection before attempt consumption. The frozen suite passes 35 Python and 13 Rust tests.
  - Verification: the native demo passes, and an unsaved benchmark smoke run records `cryptography` 49.0.0 and OpenSSL 4.0.1 provenance. `paper/main.tex` now describes the implemented stack and marks the pre-migration toy table as legacy; `paper/main.pdf` was not regenerated because no LaTeX compiler is available in the current environment.
  - Limitation: local tests do not establish a cryptographic audit, high-volume nonce lifecycle, secure erasure, distributed cloud behavior, or production readiness.
  - Completion: encryption uses reviewed library primitives and authenticated associated data.
- `Done` P2.6 Validate public parameters and group elements.
  - Result: every external wire object rejects truncated/wrong-kind/trailing envelopes and focused malformed fields; public configurations are capped at 255 parties; recovery identifiers are bounded before allocation; Rust validates point/scalar/party/set positions; Python requires exact integer metadata, exact object fields, and lowercase even-length hex.
  - Verification: the complete frozen gate passes; the malformed suite covers public parameters, secret state, client requests, commitments, response shares, and gateway responses at Rust and PyO3/Python boundaries.
  - Completion: malformed inputs fail safely and are tested.
- `Done` P2.7 Add cryptographic tests.
  - Subtask `Done` P2.7.1 Because the source article provides no vectors, added a synthetic deterministic full-protocol vector. Rust regenerates every byte from fixed inputs and seeds; Python separately consumes frozen parameter/state bytes and completes recovery. This is cross-language regression/interoperability evidence, not an independent cryptographic implementation.
  - Subtask `Done` P2.7.2 Seventeen Rust unit tests cover correctness, adversarial cases, every external decoder, and exhaustive valid subsets for `1 <= t <= n <= 5`; one Rust integration test freezes the full vector; six direct native Python tests cover the phase boundary and vector consumption; the complete 38-test Python suite covers local composition and target `(t,n)` configurations.
  - Completion: tests cover normal and adversarial inputs.
- `Done` P2.8 Add test vectors to artifact path.
  - Result: `tpass-core/test-vectors/yi-zk-ristretto255-v1.txt` records inputs, deterministic seeds, synthetic secret material, parameters, all party states, request, commitments, responses, and gateway response with an explicit evidence limitation.
  - Completion: independent implementations can consume the stable vector, although no such independent algebra implementation has yet been run.
- `Deferred` P2.9 Measure isolated crypto costs; the frozen Cycle 1 minimum
  prioritizes end-to-end P7 measurements.
  - Completion: results are clearly labeled as component costs, not end-to-end performance.
- `Todo` P2.10 Arrange internal cryptographic review if possible.
  - Completion: review notes are recorded and blockers resolved or scoped.

Phase 2 completion criteria:

- `Done` Legacy toy-group results are clearly excluded from current evidence, and every new paper-facing experiment must use the native TPASS plus standard AEAD path.
- `Done` Security assumptions are documented.
- `Done` Failure behavior is explicit and tested at the local/native boundary; network normalization remains a Phase 4 task.

## Phase 3 - Cue Policy And Client Workflow

Objective: implement the reference location-person cue policy and client workflow while avoiding unsupported human-memory claims.

Dependencies:

- `Done` Phase 0 cue-claim decision.
- `Done` Phase 1 foundation.
- `Done` Phase 2 crypto API for final integration.

Tasks:

- `Done` P3.1 Create `docs/cue-policy.md`.
  - Subtask `Done` P3.1.1 Defined exactly three distinct location-person pairs with order-independent set encoding and association-sensitive pair encoding.
  - Subtask `Done` P3.1.2 Defined coordinate precision/rounding, strict email/E.164 normalization, duplicate rejection, Unicode/locale boundaries, public metadata, ambiguity/drift failure, versioning, and new-epoch migration.
  - Result: `LOCUS-location-person-set-v1` is precise enough for implementation and vectors. It publishes no user-specific cue identifiers or hashes and explicitly rejects the current scaffold's variable-count/order-sensitive behavior as paper-facing evidence.
- `Done` P3.2 Implement deterministic local resolver fixtures.
  - Result 2026-07-21: the default isolated deployment serves one committed synthetic three-pair fixture over a resolver-only internal network; the fresh client fetches and canonicalizes it without any external API. The fixture is byte-for-byte bound to the P3.6 corpus.
  - Completion: artifact can reproduce cue canonicalization without external APIs.
- `Deferred` P3.3 Implement realistic resolver mode or self-hosted directory
  mode; the scoped paper reports only the deterministic local fixture boundary.
  - Completion: deployment evaluation can include nontrivial resolver behavior.
- `Deferred` P3.4 Implement the complete public enrollment and recovery client
  interface.
  - Progress 2026-07-21: the isolated deployment has scriptable synthetic provisioning, audited fresh-client recovery, and exact redacted JSON results. This is an experiment harness, not yet the complete user-facing enrollment/import/re-enrollment/status interface.
  - Dependency note: P4.10.3 may expose only the existing tested demo/recovery commands without inventing a second implementation. Public key-import, general re-enrollment/status, admission, replacement, and rollback-resistant behavior are deferred and must not be faked by a local-only CLI.
  - Subtask `Todo` P3.4.1 Add scriptable commands for key generation/import, credential setup, cue configuration, enrollment, recovery, re-enrollment, and redacted status inspection.
  - Subtask `Todo` P3.4.2 Add an interactive CLI menu as a thin wrapper over the same tested commands.
  - Subtask `Done` P3.4.3 The deployment client recovers from its public backup/configuration and fresh resolver output without the enrollment private key, recovery input, recovered group secret, wrapping key, or party state in its persisted bundle.
  - Subtask `Done` P3.4.4 The deployment client emits exact machine-readable status/verification fields through the P1.11 output validator; broader public commands must reuse this boundary.
  - Completion: target user workflow can be exercised interactively and non-interactively end to end.
- `Done` P3.5 Ensure raw cues and selected records are not sent to cloud or parties.
  - Result 2026-07-21: resolver connectivity exists only at the client; parties receive one distinct TPASS state and no fixture/cloud credential; S3 receives only the encrypted canonical backup object. Provisioned role snapshots, live networks/mounts/environments, and output canaries are checked by the deployment gate. This does not cover client memory, a malicious host, or a future external resolver.
  - Completion: code and tests enforce data-flow boundary.
- `Done` P3.6 Add canonicalization test corpus.
  - Result 2026-07-21: `prototype/test-vectors/cue-policy-v1.json` binds the committed resolver fixture to an exact 511-byte encoding and SHA-256 digest. Focused tests cover all six orders, half-even precision, strict email/E.164 normalization, duplicates/unknown fields, coordinate drift, locale decimal/national-phone forms, Arabic-Indic digits, nonbreaking space, decomposed/fullwidth email, and fullwidth plus rejection.
  - Completion: Unicode, locale, ordering, precision, and drift cases are tested.
- `Done` P3.7 Add resolver drift simulation.
  - Result 2026-07-21: `prototype/locus/resolver_fixture.py` validates and strips record identifiers/display labels before canonicalization. The versioned corpus covers renamed entries, map reindexing and within/across-grid movement, contact change, provider-profile change, ambiguity, and missing data with `stable`, `canonical-drift`, or generic `local-rejection` outcomes. `docs/resolver-behavior.md` defines the pre-attempt/counted-failure boundary and forbids a stored baseline verifier.
  - Completion: changed contacts, changed map records, renamed entries, provider version changes, and ambiguity have defined outcomes.
- `Scoped` P3.8 Define generic user-visible failure behavior.
  - Progress 2026-07-21: all resolver-local failures collapse to `resolver selection unavailable`; the default deployment CLI emits only `{artifact,status:failed}` and the optional operator path exposes an exception class without its message. Wrong canonical input still fails only after the counted native client check. The remaining public enrollment/import/re-enrollment commands and timing/size evaluation do not yet exist.
  - Dependency note: finish alongside the public P3.4 commands and P5 admission errors, then measure response-size/timing leakage under P6.8 rather than declaring generic text alone sufficient.
  - Completion: external failures do not reveal which cue failed.
- `Done` P3.9 Add cue privacy data-flow diagram.
  - Result 2026-07-21: `docs/cue-data-flow.md` maps user/resolver input through client-only canonicalization, blinded TPASS messages, encrypted cloud storage, party-local state, and generic output. Its role table records permitted and prohibited information plus resolver/endpoint/host limitations.
  - Completion: diagram supports paper and threat model.
- `Deferred` P3.10 Add full public CLI workflow tests.
  - Dependency note: start once P3.4.1 public commands and P8.1 lifecycle transitions exist; the current deployment smoke already covers the fresh-client recovery and redacted machine-output slice but cannot cover missing commands.
  - Completion: key generation/import, cue setup, enrollment, fresh-client recovery, wrong-cue rejection, re-enrollment, and generic failure behavior are tested through the public command interface.

Phase 3 completion criteria:

- `Done` Reference policy is implemented and tested.
- `Done` No raw cue material is stored by cloud or parties in the implemented deterministic deployment; client memory, host compromise, and future modes remain explicit limits.
- `Done` Drift cases have defined stable, new-epoch migration, counted generic failure, or pre-attempt safe-rejection outcomes.
- `Done` Paper text avoids measured memorability, comparative recall/reproduction, entropy, or usability claims for the LOCUS cue policy; prior human-memory work remains motivation and future-study context only.

## Phase 4 - Distributed Services And Cloud Storage

Objective: turn the local prototype into a realistic distributed system.

Dependencies:

- `Done` Phase 1 foundation.
- `Done` Phase 2 crypto path.
- `Doing` Phase 3 cue workflow. Phase 4 service/storage tasks may proceed against the frozen cue interface; public client/drift tasks retain their own Phase 3 dependencies.
- `Done` VM/container/cloud resource decision.

Tasks:

- `Done` P4.1 Design recovery-party service API.
  - Result: `docs/recovery-party-api.md` freezes enrollment, admission/ledger, recovery commitment/response, lifecycle/admin, health/status/audit, transport, schema/bounds, idempotency, crash, test, evaluation, and paper-claim contracts. It places authorization install plus live freshness before `prepare_commitment`, the first password-share-dependent output.
- `Done` P4.2 Implement recovery-party service for the scoped authenticated recovery and same-membership lifecycle paths.
  - Progress 2026-07-21: the strict HTTPS adapter exposes ledger, live freshness, native commitment, and native response operations. One pinned image is instantiated as five non-root services with distinct generated identities/configurations and pairwise-disjoint volumes. Static, live, and recursive snapshot audits verify that each runtime receives only its own database, identity, authorizer key, and TPASS state when applicable. Correct recovery and exact retry cross this public boundary before/after restart. P4.9 now supplies local certified lifecycle/store transitions, but enrollment/lifecycle HTTP routes and successor native-state loading remain absent; independent administration is not implemented.
  - Subtask `Done` P4.2.1 Build one versioned party-service image instantiated with distinct party identities and configuration.
  - Subtask `Done` P4.2.2 Ensure each party process can access only its own database, identity material, TPASS state, counters, and audit records.
  - Completion: parties run as separate processes/services with independently mounted state and no cross-party volume access.
- `Done` P4.3 Add service identities and authenticated confidential transport at the implemented coordinator/party boundary.
  - Progress 2026-07-21: all implemented ledger/freshness/recovery routes require TLS 1.3, CA-valid client/server certificates, exact pins, bounded exact-schema JSON, and verified signed responses. The networkless deployment provisioner now generates and installs distinct ephemeral coordinator, party-server, and party-peer identities; live recovery and restart use them across the internal recovery network with no host ports. OIDC/DPoP client admission and certificate rotation/revocation remain.
  - Completion: client and parties authenticate each other; transport assumptions are documented.
- `Done` P4.4 Implement durable party storage for the scoped same-host prototype.
  - Progress 2026-07-21: the per-party SQLite store provides versioning, foreign keys, WAL, `synchronous=FULL`, atomic epoch/attempt/phase/idempotency transitions, monotonic heads, and hash-chained redacted events. Schema v4 adds durable one-successor transition locks and non-active preparations; local activation atomically retires the predecessor and creates the successor without editing the predecessor count. Schema-v3 migration and restart-after-preparation tests pass. The default deployment enforces one named volume per party and its schema-v4 regression smoke preserves restart/fallback behavior. General backup/restore reconciliation, rollback resistance, lifecycle native-state loading, and systematic process-crash fault injection remain.
  - Completion: party state survives restart and supports transactional updates.
- `Done` P4.5 Implement cloud object-storage adapter.
  - Result 2026-07-21: the strict filesystem-backed adapter and explicit-credential SigV4 S3-compatible adapter share one green semantic contract. The S3 path uses conditional `PutObject` with `If-None-Match: *`, a SHA-256 transfer checksum, bounded streaming reads/timeouts/retries, exact-byte retry comparison, and application-level canonical/reference/digest verification. It passes focused fake/live SeaweedFS tests and is now combined with the authenticated five-party path by P4.10.1/P4.10.2.
  - Subtask `Done` P4.5.1 Add local S3-compatible or filesystem adapter for tests.
  - Subtask `Done` P4.5.2 Add an S3-compatible adapter and local service; a real cloud-provider run remains optional if credentials/resources are available.
  - Completion: cloud backup object is stored separately from party state.
- `Done` P4.6 Add backup versioning and digest binding.
  - Result 2026-07-20: `LOCUS-reference-backup-v3` and `LOCUS-cloud-backup-reference-v1` bind a positive epoch and complete backup digest; `LOCUS-attempt-config-v2` signs that digest and SQLite schema v2 stores it in every party epoch. Current honest bindings reject stale/substituted/corrupt objects before a counted attempt. Coordinated rollback of the cloud and every authoritative party remains outside this result and requires P5 rollback anchors.
  - Completion: stale/substituted/corrupt backup objects are detected.
- `Done` P4.7 Add idempotency keys and replay protection.
  - Result 2026-07-21: every implemented mutating POST now requires one strict 32-byte key and schema v3 durably binds it to caller certificate, method, exact route, and canonical request digest before dispatch. Exact completed status/body bytes survive coordinator reconstruction and process restart; changed reuse conflicts without dispatch; same-boot concurrency yields one executor; interrupted requests resume only through existing ledger/phase semantics. Tests cover missing keys, changed payload/session, delayed response replay, concurrency, schema migration, restart, and fail-closed volatile TPASS state. The full check and artifact smoke gates pass. DPoP credential replay, arbitrary packet scheduling, database rollback, and bounded idempotency-record retention/compaction remain later work.
  - Completion: retries do not create unintended extra attempts or responses.
- `Done` P4.8 Add party health, timeout, retry, and slow/malicious-party handling.
  - Result 2026-07-21: `docs/party-failure-policy.md` freezes a maximum of two byte-identical deliveries for transport-ambiguous outcomes, no retry for protocol faults/conflicts, concurrent 4-of-5 authorization collection under ten-second phase and 45-second operation deadlines, quorum-consistent TPASS selection before authorization, concurrent 12-second TPASS phases, and a fixed selected set after authorization. Failures after authorization remain consumed. Tests cover one slow/unavailable/malformed party, two-party quorum loss, conflicts, delayed exact retry, stale-party exclusion, deterministic fallback, insufficient threshold, phase timeout, and no post-authorization switch. The default isolated deployment recovered twice through `[1,3]` around a party-1 restart, then stopped party 1 and recovered through `[2,3]` at exactly `consumed=3` before full cleanup.
  - Verification 2026-07-21: the complete frozen gate passed repository hygiene, Ruff/mypy over 43 Python sources, 95 Python tests with one opt-in live-S3 skip, 17 Rust core tests plus the fixed vector, rustfmt, and Clippy for both crates. The default five-party Compose smoke passed separately. Limitations remain explicit: same-host deterministic evidence, one unavailable authorizer in the compact profile, no arbitrary Byzantine network schedule, rollback defense, independent-host evidence, or tail-latency result.
  - Completion: failure behavior is explicit and tested.
- `Done` P4.9 Implement backup epochs and re-enrollment lifecycle.
  - Started 2026-07-21: freeze and implement a quorum-certified successor transition that binds the predecessor's exact head/count/budget and both backup/configuration digests. Direct second-epoch activation must be impossible; prepared state is non-recoverable; installing one valid transition atomically retires the predecessor and activates the successor at a fresh, explicitly authorized per-epoch budget. Add exact-retry, partial-installation, retired-state, replay, and cross-mixing tests before exposing public lifecycle commands.
  - Result 2026-07-22: `docs/epoch-lifecycle.md` freezes a same-membership direct-successor protocol. `EpochTransition`, durable old-party approvals, package-bound new-party readiness statements, and an old/new quorum activation certificate are canonical and signed. Party schema v5 adds one transition lock, non-active preparation, and exact epoch runtime package per successor; direct epoch-two insertion is rejected; activation atomically retains epoch one as `RETIRED` and inserts epoch two as `ACTIVE` while preserving the predecessor's final head/count/budget. `core.reenroll` creates a fresh consecutive TPASS/AEAD/cloud object under the same `bid`. Three strict coordinator-only pinned-mTLS lifecycle routes use durable exact HTTP idempotency, parse each party's own canonical native state before readiness, select authorizer/native state by certified epoch, discard old cached services on activation, and reconstruct only active native state after restart. Local, five-process, and Compose paths cover exact retries, restart before/after activation, insufficient 3/2 quorums, old vote/certificate/commitment refusal, unresolved-slot refusal, changed-transition/package replay, role authorization, membership/cross-backup mixing, schema migration, and successful successor native recovery. Public administrator authorization and general party replacement remain separate P5 work.
  - Subtask `Done` P4.9.1 Freeze canonical same-membership transition objects, local database states, invariants, failure behavior, tests, and claim limits.
  - Subtask `Done` P4.9.2 Implement client-side consecutive re-enrollment plus immutable two-epoch cloud-object and cross-mixing tests.
  - Subtask `Done` P4.9.3 Add authenticated approval/readiness/activation routes and durably load the activated epoch's native party state after restart.
    - Result 2026-07-21: readiness v2 signs the exact `RuntimeEpochPackage` digest. Schema v5 atomically persists successor authorizer configuration plus either an authorizer-only marker or canonical public parameters and only the local party's secret state. Coordinator-only pinned-mTLS approval/preparation/activation routes use exact durable HTTP idempotency. The process selects configuration/native state by certified epoch, rejects prepared or retired packages, and reconstructs the activated epoch after restart. One five-process test covers unauthorized role, exact retry, changed package, restart while prepared, 3/2 no-quorum split, retired commitment refusal, restart after activation, and successful epoch-two native recovery.
  - Subtask `Done` P4.9.4 Exercise re-enrollment, partial activation/reconciliation, old-epoch refusal, and successor recovery in the isolated five-party deployment.
    - Result 2026-07-22: `cross-epoch-runtime-mix-v1` is synchronized across the registry, CLI, strict portable schema, task runner, Compose command contract, tests, and documentation. The first live attempt exposed a stale single-scenario task-runner check. The next exposed an invalid experiment assumption: native public parameters are identical for unchanged `(t,n)`, so substituting predecessor public parameters was an exact equivalent retry rather than a mix. The corrected scenario substitutes genuinely different synthetic predecessor-context party state after the exact successor package is prepared, rejects that change, preserves the 3/2 no-quorum split, restarts party 1, refuses the retired predecessor, recovers under the successor, validates the report, scans output, and removes all containers, volumes, and networks.
  - Verification 2026-07-22: repository hygiene and parsing of 45 project Python files pass; Ruff/mypy pass over 46 sources; 104 Python tests pass with one opt-in live-S3 skip; the native extension rebuild passes; and 17 Rust core tests plus the fixed vector, rustfmt, and Clippy for both crates pass. The monolithic wrapper was stopped after it again failed to return a completion signal, so every component was rerun individually and passed. The P4.9.4 Compose profile passed separately under schema v5.
  - Completion: old epochs can be retired and are not silently reusable.
- `Done` P4.10 Build reproducible local isolated deployment.
  - Result 2026-07-21: P4.10.1/P4.10.2 are green under `docs/deployment.md`. `deploy/compose.yaml` and the pinned multi-stage image reuse the existing native HTTP/S3 adapters across a networkless provisioner, deterministic resolver, SeaweedFS, five non-root party services, and an ephemeral client. Base images use OCI digests and the runtime Python dependency closure is exported with hashes from `uv.lock`. `cloud`, `resolver`, and `recovery` are internal with no published ports; five party volumes and the object-store volume are disjoint; runtime credentials, identities, and mounts follow the frozen role matrix. `tasks.py deployment-smoke` validates the resolved and live topology, audits every allowed provisioned/runtime state file, performs S3-backed recovery through parties `[1,3]`, restarts party 1 and repeats at `consumed=2`, then stops party 1 and recovers through `[2,3]` at `consumed=3`; it scans output for known prohibited material and cleans all resources. SeaweedFS informational logs are confined to ephemeral `/tmp` because its upstream startup output includes the access key. The current live and 101-test frozen gates are green; P4.10's previously recorded artifact smoke was also green. This is one-host synthetic container isolation, not independent administration, VM evidence, real-cloud evidence, Byzantine liveness, or a global attempt bound.
  - Subtask `Done` P4.10.1 Add a default Docker Compose deployment containing the ephemeral client CLI, multiple parties, S3-compatible storage, deterministic resolver, and provisioning job.
  - Subtask `Done` P4.10.2 Add persistent per-party and object-store volumes, service identities, health checks, deterministic startup, and explicit network boundaries.
  - Subtask `Done` P4.10.3 Add separate demo, benchmark, and attack profiles without changing the evaluated protocol implementation.
    - Result 2026-07-21: three opt-in Compose services reuse the exact client runtime identity, read-only volume, internal networks, cloud environment, provisioned state, and packaged HTTP/S3/native TPASS implementation. The task runner validates all resolved commands and role boundaries, generates per-run credentials/prefixes, scans logs/results with credential and complete fixture canaries, and always removes resources. The live demo recovered once; the development benchmark completed two full recoveries, advanced exactly from zero to two consumed attempts, and emitted validated samples plus P1.10 provenance; the P6.1 resolver-unavailable scenario produced an exact passing report with zero attempt delta. These runs are artifact validation, not paper-facing performance or central attack evidence.
    - Verification 2026-07-21: all three optional profiles and the unchanged default recovery/restart smoke passed and cleaned up. The repository-wide gate passed hygiene, Ruff and mypy over 41 sources, 85 Python tests with one opt-in live-S3 skip, 17 Rust core tests plus the fixed vector, rustfmt, and Clippy for both crates.
  - Completion: the complete local infrastructure starts from one documented command and supports terminal access to each redacted role interface.
- `Deferred` P4.11 Build VM deployment path.
  - Completion: parties can run in separate VM-like trust/failure domains.
- `Scoped` P4.12 Add only remaining end-to-end integration tests required by a
  retained claim.
  - Progress 2026-07-21: five-subprocess tests cover signed ledger assembly, exact retry, malformed and unauthorized calls, role separation, correct/wrong-input native recovery, alternate subsets, party loss, restart/catch-up, cross-session rejection, and fail-closed volatile phases. Deterministic P4.8 tests add classified timeout/protocol faults, quorum loss, stale-party exclusion, concurrent deadlines, and fixed fallback. P4.9 local integration tests add two immutable epochs, successful successor recovery, signed retirement/activation, partial-installation quorum loss, restart, and cross-mixing refusal. The default Compose smoke remains a single-epoch schema-v4 regression with restart and `[2,3]` fallback. Malicious response substitution, arbitrary network scheduling, timeout distributions, broader crash/rollback restoration, and deployed lifecycle remain.
  - Completion: tests cover party loss, cloud failure, stale objects, malformed responses, and restart.
- `Deferred` P4.13 Add broader privacy-safe operational observability beyond
  the exact retained-output contract.
  - Subtask `Todo` P4.13.1 Expose health, software version, epoch, attempt reservations/counters, replay status, redacted audit events, timings, and message sizes through party status commands and structured logs.
  - Subtask `Todo` P4.13.2 Extend the implemented normal-output guards to remaining observability, trace, and crash-artifact surfaces.
    - Progress 2026-07-21: all default/profile results use exact schemas plus recursive prohibited-field validation; Compose output, service logs, and provisioner diagnostics are checked with generated credentials and every synthetic fixture value before display. Process traces, crash dumps, third-party logging, and future profiles remain to be audited under P1.11.
  - Subtask `Todo` P4.13.3 Gate any educational secret-sharing inspection behind an unmistakable synthetic-only unsafe option and visibly mark its output as non-paper-facing.
  - Completion: operators can inspect protocol progress and attempt control without violating storage-separation or secret-leakage claims.

Phase 4 completion criteria:

- `Scoped` A fresh client enrolls and recovers through separately identified
  same-host party processes; independent administration and multi-host
  deployment are explicit non-claims.
- `Done` Recovery succeeds through tested authorized 2-of-3 subsets and fails
  below threshold.
- `Scoped` Party state survives the tested restart/catch-up paths; arbitrary
  rollback and crash scheduling are explicit non-claims.
- `Done` The tested backup substitution, corruption, and stale-epoch cases are
  detected when current honest party metadata is available.

## Phase 5 - Distributed Attempt Control And Recovery Authorization

Objective: record and test the partial attempt-ledger behavior without overstating it. The former objective of a global bound under subset rotation, concurrency, replay, rollback, crashes, and partial compromise is deferred after P5.13; it is not a scoped paper claim.

Dependencies:

- `Done` Phase 0 property definition.
- `Doing` Phase 4 service/storage foundation. The implemented service/storage slice is sufficient for current P5 work; lifecycle and adversarial deployment tasks remain.

Tasks:

- `Done` P5.1 Define attempt-control security property.
  - Subtask `Done` P5.1.1 A counted attempt is durably committed before any honest party emits its first secret-dependent TPASS message and consumes budget even if later abandoned or failed.
  - Subtask `Done` P5.1.2 Defined a global per-epoch `B_eff` bound with a zero-overrun target across subset rotation, concurrency, retry, replay, and crash; any selected nonzero overrun must revise all dependent claims.
  - Subtask `Done` P5.1.3 Defined separate TPASS and attempt-authorizer fault assumptions, quorum-intersection and surviving-rollback-anchor requirements, and explicit safety/availability tradeoffs.
  - Result: `docs/attempt-control.md` defines a property precise enough to test and state conditionally in the paper; no implementation claim is made.
- `Done` P5.2 Create `docs/attempt-control.md` and specify the concrete state machine.
  - Result: `docs/attempt-control-state-machine.md` defines canonical protocol objects, authorizer/coordinator states, durable first-phase locks, prepare and install certificates, the exact attempt commit point, TPASS pre-response enforcement, response-freshness quorums, concurrency and crash recovery, rollback reconciliation, joint reconfiguration, budget/retirement behavior, database guarantees, invariants, and test mappings. Ambiguous partial proposals cannot be unlocked or burned unsafely; they complete as the same entry or fail the epoch closed. No implementation claim is made.
- `Done` P5.3 Evaluate design candidates.
  - Subtask `Done` P5.3.1 Threshold-signed one-use attempt tickets.
  - Subtask `Done` P5.3.2 Quorum certificates over monotonic counters.
  - Subtask `Done` P5.3.3 Replicated append-only attempt logs.
  - Subtask `Done` P5.3.4 Narrow coordination service with explicit trust tradeoffs.
  - Result: `docs/attempt-control-selection.md` selects a quorum-certified, hash-chained ledger replicated by recovery parties. Request-bound tickets are ledger certificates; an optional coordinator is an untrusted sequencer/collector. Compact `(n_a=5, f_a=2, q_a=4)` and resilient `(n_a=7, f_a=2, q_a=5)` profiles make the safety/availability tradeoff explicit. No implementation claim is made.
- `Done` P5.4 Create `docs/recovery-authorization.md`.
  - Result: ordinary admission uses minimal audience-restricted OIDC JWT access tokens sender-bound with DPoP and independently verified by every authorizer against the exact LOCUS request. High-impact actions require enrollment-pinned `m_admin`-of-`k_admin` signatures plus the ledger quorum; budget extensions also require fresh user admission and cannot exceed disclosed `X_max`. The document covers fresh-device CLI flows, optional offline capability, replay/idempotency, IdP/admin compromise, privacy/logging, failures, tests, evaluation, and paper limits. No implementation claim is made.
  - Subtask `Deferred` P5.4.1 Implement bounded OIDC JWT and DPoP validation at every authorizer, including exact audience/issuer/time/key-thumbprint/request binding and replay state.
  - Subtask `Deferred` P5.4.2 Add negative, replay, concurrency, restart, privacy, and IdP-compromise-boundary tests before exposing the public recovery client.
  - Scope decision 2026-07-22: the design remains documented future work; public admission and third-party lockout prevention are explicit non-claims for the scoped paper.
- `Done` P5.5 Implement transactional attempt reservation before TPASS response.
  - Result 2026-07-20: every implemented native commitment route verifies/installs the signed authorization, obtains responding-party-bound live freshness, and commits durable phase intent before Rust `prepare_commitment`; response routes require the exact stored phase/transcript. Local ordering tests inspect state at the native call boundary, and remote process tests cover correct, wrong-input, retry, unavailability, and restart loss without restoring `consumed`. This completes the transactional pre-secret-dependent-response boundary, not the broader P5 global bound; rollback, admission, subset/concurrency proof, and lifecycle work remain separate tasks.
  - Completion: parties cannot respond without durable attempt accounting.
- `Deferred` P5.6 Complete global concurrency control.
  - Progress 2026-07-20: canonical Ed25519 two-phase certificates and per-party SQLite vote locks are implemented for the compact 4-of-5 profile. The untrusted coordinator requires quorum matching-head state, resumes/catches up an installed certificate, rejects conflicting observed locks, and collects both phases through either local or pinned-mTLS peers. A two-coordinator in-process race produces at most one conflicting-slot certificate; the network test preserves quorum progress with one unavailable party and catches it up after restart. Concurrent network scheduling and broader interleavings remain.
  - Scope decision 2026-07-22: retain the implemented local race behavior as prototype evidence, but do not make a global-overrun claim or require exhaustive network scheduling for the scoped paper.
  - Future completion: concurrent sessions have measured and justified maximum overrun.
- `Deferred` P5.7 Implement global subset-rotation protection.
  - Completion: rotating threshold subsets does not permit unbounded guesses.
- `Done` P5.8 Implement replay protection and idempotent retries at the current authenticated service boundary.
  - Progress 2026-07-21: certificate encodings require sorted distinct signers and exact entry/configuration binding. Every implemented mutating HTTP route now requires a 32-byte key durably bound to caller certificate, method, exact route, and canonical body before dispatch; exact completed status/body bytes survive restart, while changed reuse conflicts. Lower entry/install/freshness/commitment/response state remains semantically idempotent. Tests cover a missing key, same-key concurrency, two logical coordinators, changed-body and cross-session reuse, delayed completed response replay, schema migration, restart recovery, and fail-closed volatile phase loss. Arbitrary active-network scheduling, database rollback, and DPoP admission replay tests remain.
  - Scoped completion: replayed requests/responses at the tested mTLS/HTTP/native boundary fail or map to one stored operation; this is not OIDC/DPoP admission or rollback evidence.
- `Deferred` P5.9 Implement rollback resistance.
  - Scope decision 2026-07-22: party-quorum reconciliation is insufficient after snapshot restore. An independent monotonic witness or stronger reviewed consensus would change the architecture and is future work. The paper must state that party-state rollback is not defended.
- `Done` P5.10 Implement crash recovery at the tested same-host process boundary.
  - Progress 2026-07-20: process restart creates a new boot nonce, marks non-serializable TPASS phases lost, and requires a new quorum freshness certificate before any new eligible phase. Subprocess tests terminate one authorizer, advance the surviving 4-of-5 quorum through full native recovery, restart/catch up the same database/identity, and separately restart after a stored commitment to verify that the response route rejects the lost ephemeral while the attempt count remains consumed. Systematic crash injection at every ledger transaction remains.
  - Scoped completion: the tested restarts preserve durable installed state and lose volatile phases closed; systematic transaction-boundary crash proof remains future work because no global bound is claimed.
- `Deferred` P5.11 Implement party replacement and counter migration.
  - Completion: replacing parties does not reset attack budget silently.
- `Deferred` P5.12 Implement false-lockout administration.
  - Completion: legitimate recovery path is documented without silently restoring attacker budget.
- `Done` P5.13 Implement executable state-machine exploration.
  - Result 2026-07-22: the dependency-free compact 4-of-5 bounded explorer emits a strict versioned report. No counterexample appears in the depth-12 no-rollback baseline. Quorum-only reconciliation produces the shortest conflicting-certificate trace after one honest database restore and produces authorization after restored final-retirement state. The corresponding ideal monotonic-anchor scenarios have no counterexample within their frozen bounds. This is a negative design result and bounded regression oracle, not a proof or runtime rollback evidence. It is documented in `docs/attempt-control-model.md` and run with `tasks.py attempt-model`.
  - Verification 2026-07-22: the strict seven-scenario report and four focused tests pass; repository hygiene passes; 47 Python files parse; Ruff and mypy pass 48 sources; 108 default Python tests pass with one live-S3 skip; 17 Rust core tests plus the fixed vector pass; both Rust crates pass formatting and Clippy. The combined task wrapper again stopped producing output in this Codex session, so the same component gates were run separately and observed green.
- `Scoped` P5.14 Add adversarial tests matching retained claims.
  - Subtask `Todo` P5.14.1 Subset rotation.
  - Subtask `Todo` P5.14.2 Concurrent guessing.
  - Subtask `Todo` P5.14.3 Replay.
  - Subtask `Todo` P5.14.4 Rollback.
  - Subtask `Todo` P5.14.5 Crash consistency.
  - Subtask `Todo` P5.14.6 Lockout denial of service.
  - Scope decision 2026-07-22: subset/concurrency/global rollback/lockout tests are no longer submission gates because their positive property is not claimed. Retained-claim cloud/party snapshots, malformed inputs, cross-epoch mixing, resolver, and output-safety attacks remain P6 work.
  - Completion: tests match only the claims retained in `docs/limitations-and-assumptions.md`.
- `Deferred` P5.15 Write a complete global attempt-bound security argument.
  - Scope decision: the paper instead states the bounded counterexample and makes no exact system-bound claim.

Phase 5 scoped completion criteria:

- `Done` The counted-attempt target and partial implementation are documented without being presented as a completed security property.
- `Done` The rollback counterexample and ideal-anchor comparison are reproducible.
- `Done` Global rate limiting, rollback resistance, public admission, and false-lockout safety are explicit non-claims.
- `Done` Manuscript, threat model, research question, claim matrix, related-work positioning, README, AGENTS.md, and plan are synchronized with `docs/limitations-and-assumptions.md`; final citation, page, PDF-render, and independent review gates remain.

## Phase 6 - Security And Privacy Attack Evaluation

Objective: validate only the retained architecture, storage-separation, cue-boundary, integrity, and failure claims against executable adversarial scenarios; record attempt-control counterexamples as limitations.

Dependencies:

- `Done` Scoped Phase 5 boundary is stable: exact local ledger behaviors are retained, P5.13 records the rollback counterexamples, and the complete global attempt property is an explicit non-claim.
- `Done` Claim-evidence matrix; it remains a living gate during implementation and evaluation.

Tasks:

- `Done` P6.1 Create attack-report template.
  - Result 2026-07-21: `LOCUS-attack-report-v1`, its exact JSON Schema, in-code validator, registry binding, report builder, and design/threat/test/evaluation contract require scenario, prerequisites, procedure, parameters, expected and observed results, status, and narrow interpretation. Extra/secret-bearing fields, rewritten scenarios, contradictory statuses, and malformed observations fail closed. The bootstrap `resolver-unavailable-v1` profile passed with an observed zero attempt delta; it is explicitly failure-boundary evidence rather than an offline-oracle result.
  - Completion: every attack records scenario, prerequisites, procedure, expected result, observed result, and interpretation.
- `Done` P6.2 Implement cloud snapshot offline guessing attack.
  - Subtask `Done` P6.2.1 Freeze the cloud-only adversary input as the exact canonical cloud backup object and public configuration/metadata persisted at that role; exclude party databases, TPASS secret states, client-local cues, credentials, and online party access.
    - Result 2026-07-22: `docs/cloud-snapshot-attack.md` freezes `LOCUS-cloud-snapshot-input-v1` as the byte-exact canonical cloud envelope plus a six-field public locator/integrity manifest. It defines attacker-chosen candidates, the local-predicate decision rule, zero-online-call execution, prohibited artifacts, fail-closed collection/validation, and the limits of the future result. Live access timing, provider internals, host/container memory, multi-epoch correlation, and real-provider forensics remain separate metadata/deployment questions rather than hidden P6.2 inputs.
  - Subtask `Done` P6.2.2 Register one versioned `cloud-snapshot-no-offline-predicate-v1` scenario with strict prerequisites, procedure, parameters, expected observation, interpretation, report schema binding, and privacy-safe output.
  - Subtask `Done` P6.2.3 Implement the snapshot audit and candidate-test harness so the scenario fails if the cloud surface exposes a local cue/password correctness predicate or contacts a resolver, recovery party, coordinator, or other online oracle.
  - Subtask `Done` P6.2.4 Add positive, malformed, substitution, prohibited-access, schema, and redaction tests; run the scenario first as unsaved development evidence.
  - Subtask `Done` P6.2.5 Update `docs/threat-model.md`, `docs/claim-evidence-matrix.md`, attack documentation, and paper wording with the exact outcome and limitations.
  - Result 2026-07-22: the exact registered observation and isolated profile passed as unsaved development evidence. The collector receives only the read-only client bundle, cloud credential/network, and fresh snapshot volume; the attacker receives only the two snapshot files read-only with no network or credentials. The dirty, unlabeled, unretained run cannot be cited as final paper evidence; privacy-reviewed trace freezing and clean immutable recollection remain required.
  - Verification 2026-07-22: the complete frozen gate validated repository boundaries, parsed 49 Python files, confirmed formatting for 50 files, passed Ruff and mypy over 50 source files, ran 112 Python tests with one opt-in live-S3 skip, passed 17 Rust core tests plus the fixed vector, and passed rustfmt/Clippy and the binding crate. The unchanged default Compose smoke then passed recovery, party restart, the next recovery, party-1 shutdown, `[2,3]` fallback at the third consumed attempt, output scanning, and complete resource cleanup. The dedicated P6.2 Compose run passed separately with its exact aggregate report and cleanup.
  - Completion: the implemented cloud-only snapshot surface exposes no local candidate-correctness predicate in the registered scenario, no online role is contacted, the strict report passes, and the result is described as implementation evidence rather than a cryptographic proof.
- `Done` P6.3 Implement `t-1` party compromise attack.
  - Subtask `Done` P6.3.1 Freeze the exact input and defensive decision rule for the deployed two-of-three TPASS profile.
    - Result 2026-07-22: `docs/party-snapshot-attack.md` defines `LOCUS-party-snapshot-input-v1` as every regular persistent file in one stopped, post-recovery synthetic `party1` volume, bound by a canonical manifest. It includes the party's native share, signer/TLS keys, authorization configuration, durable attempt state, and exact SQLite companion files when present; it excludes cloud/client/resolver/other-party state, credentials for other roles, live memory, logs, traces, and all online access. The scenario is a bounded local-predicate audit with aggregate-only output and a test-only positive verifier, not a party-compromise mechanism or cryptographic proof.
  - Subtask `Done` P6.3.2 Implement strict snapshot collection, validation, and the bounded networkless candidate audit with counted file/socket guards.
  - Subtask `Done` P6.3.3 Register `t-minus-one-party-snapshot-no-offline-predicate-v1` in the attack runner, exact schema, tests, and development-only Compose profile.
  - Subtask `Done` P6.3.4 Run focused positive-control, malformed, manifest-consistent substitution, redaction, schema, and isolated live-development verification with complete cleanup.
    - Result 2026-07-22: the resolved profile accepts only a trusted networkless collector with the stopped read-only `party1` volume and a fresh output volume, followed by a non-root, credential-free, read-only, networkless attacker. The unsaved Compose run matched `candidate_count=2`, `candidate_signals=0`, `compromised_parties=1`, `threshold=2`, `network_attempts=0`, `excluded_path_accesses=0`, `secret_output_exposures=0`, `snapshot_validation=passed`, and `cloud_material=absent`; dynamic output scanning passed and all containers, networks, and volumes were removed.
  - Subtask `Done` P6.3.5 Synchronize the exact result and limitations across the threat model, claim-evidence matrix, paper, and this plan; then run the complete regression and unchanged default deployment gates.
  - Verification 2026-07-22: the complete frozen gate validated repository boundaries, parsed 51 Python files, confirmed formatting for 52 files, passed Ruff and mypy over 52 source files, ran 117 Python tests with one opt-in live-S3 skip, passed 17 Rust core tests plus the fixed vector, and passed rustfmt/Clippy and the binding crate. The unchanged default Compose smoke passed healthy recovery, party-1 restart, the next recovery, party-1 shutdown, `[2,3]` fallback at the third consumed attempt, output scanning, and complete cleanup. The dedicated P6.3 profile passed separately with its exact aggregate report and cleanup.
  - Completion: the complete stopped persistent snapshot of one synthetic party in the deployed 2-of-3 profile exposes no local candidate-correctness predicate in the registered scenario, no online role is contacted, and no secret-bearing input is emitted. This is bounded implementation evidence under inherited TPASS assumptions, not a proof, live compromise, cumulative-compromise analysis, or combined cloud-plus-party result.
- `Done` P6.4 Implement combined cloud plus `t-1` party compromise attack.
  - Subtask `Done` P6.4.1 Freeze the exact combined input, cross-role binding checks, candidate-predicate decision rule, positive controls, aggregate observation, and interpretation limits.
    - Result 2026-07-23: `docs/combined-snapshot-attack.md` defines `LOCUS-combined-snapshot-input-v1` as exactly the canonical P6.2 cloud sub-snapshot, canonical P6.3 party-1 sub-snapshot, and a top-level canonical manifest binding both sub-manifests. A networkless finalizer must validate matching backup identifier, epoch, backup digest, and TPASS public parameters before publication. The offline runner receives only this read-only union; mismatched enrollments, candidate signals, socket/file attempts, malformed input, and secret-bearing output fail closed. The result remains bounded implementation evidence, not a compromise mechanism or proof.
  - Subtask `Done` P6.4.2 Implement combined finalization, independent validation, cross-binding enforcement, and the bounded offline candidate audit.
    - Result 2026-07-23: `prototype/locus/combined_snapshot.py` accepts only the two frozen sub-snapshot directories before finalization, independently validates each canonical sub-snapshot, binds their exact manifest digests in one exclusive canonical top-level manifest, and rejects mismatched backup identifiers, epochs, backup digests, or TPASS public parameters. The bounded audit validates the complete union before testing two fixed synthetic candidates and counts candidate signals, socket attempts, excluded-path access, and secret-output exposure without emitting candidate or secret material.
  - Subtask `Done` P6.4.3 Register the scenario/report schema and add positive verifier, mismatched-enrollment, malformed, extra-file, boundary, and redaction tests.
    - Verification 2026-07-23: `cloud-plus-t-minus-one-party-snapshot-no-offline-predicate-v1` is registered in the noninteractive runner and strict report schema. Nine focused combined-snapshot/profile tests pass, including the valid aggregate-only observation, positive-verifier failure, socket and excluded-path accounting, manifest-consistent mismatched enrollment, noncanonical input, sub-manifest substitution, unexpected files, exclusive finalization, schema validation, and report redaction.
  - Subtask `Done` P6.4.4 Add and run the disposable combined-snapshot Compose profile with both existing collectors, a networkless finalizer, a non-root offline attacker, scanning, and cleanup.
    - Result 2026-07-23: the disposable same-host profile completed one synthetic recovery, stopped party 1, collected both frozen sub-snapshots, finalized their manifest-bound union without network or credentials, and ran the separate non-root, credential-free, read-only, networkless audit. The exact observation matched: two candidates, zero signals, one compromised party at threshold two, both sub-snapshots valid, combined binding matched, and zero network attempts, excluded-path accesses, or secret-output exposures. Output scanning passed. Compose removed every generated resource, and an independent exact-project-label query found no remaining container, volume, or network. This dirty, unlabeled, unretained run is development evidence only.
  - Subtask `Done` P6.4.5 Synchronize the exact result and limitations across the threat model, claim-evidence matrix, manuscript, AGENTS, and this plan; then run the complete regression and unchanged default deployment gates.
    - Verification 2026-07-23: the exact development result and limitations are synchronized across the combined-attack design, threat model, claim-evidence matrix, manuscript, AGENTS, and plan. The complete gate validated repository boundaries, parsed 53 Python files, confirmed formatting for 54 files, passed Ruff and mypy over 54 source files, ran 123 Python tests with one opt-in live-S3 skip, passed 17 Rust core tests plus the fixed vector, and passed rustfmt/Clippy and the binding crate. The unchanged default Compose smoke passed state audit, healthy recovery, party-1 restart, the next recovery, party-1 shutdown, `[2,3]` fallback at the third consumed attempt, output scanning, and complete cleanup. Exact-project-label queries after both P6.4 and default smoke found no remaining containers, volumes, or networks.
- `Deferred` P6.5 Implement global threshold-subset rotation attack; no positive global-budget claim remains.
- `Deferred` P6.6 Implement arbitrary-schedule concurrent guessing attack; retain existing focused races only as local facts.
- `Scoped` P6.7 Retain focused request/response replay tests at the implemented authenticated boundary; public-admission replay is deferred.
- `Scoped` P6.8 Implement the retained cloud-object rollback/binding attack. Party-state rollback is an explicit non-claim supported by the P5.13 counterexample rather than a fix target.
- `Done` P6.9 Implement cross-epoch state-mixing attack.
  - Result 2026-07-22: `cross-epoch-runtime-mix-v1` exercises successor publication, old/new quorum certificates, exact per-party runtime packages, post-preparation predecessor-context state substitution, a 3/2 no-quorum partial installation, retired-epoch refusal, party restart, and successor recovery. Its strict report matched, output scanning passed, and all Docker resources were removed. This is narrow same-host lifecycle evidence; it does not validate the first package delivered by an authorized coordinator, restore snapshots, prove rollback resistance, or establish the global attempt bound.
- `Todo` P6.10 Implement malformed/equivocated party response tests.
- `Todo` P6.11 Implement selective refusal and availability tests.
- `Deferred` P6.12 Implement public lockout denial-of-service tests; public admission and false-lockout safety are non-claims.
- `Todo` P6.13 Analyze resolver, cloud, party, log, exception, timing, and network metadata leakage.
- `Todo` P6.14 Run static and dependency security scans.
- `Done` P6.15 Update the claim-evidence matrix for the frozen Cycle 1 attack set.
  - Result 2026-07-24: the resolver bootstrap, cross-epoch lifecycle result,
    P5.13 bounded counterexamples, retained P6.2 cloud snapshot, retained P6.3
    one-party persistent snapshot, and retained P6.4 matching combined snapshot
    are recorded with their narrow limitations. Reopen this living gate if a
    new paper-facing P6 result is added.
- `Done` P6.16 Build the automated attack-runner interface and Docker profile
  for every retained Cycle 1 P6 scenario.
  - Subtask `Done` P6.16.1 Make each retained P6 scenario invokable
    non-interactively with versioned parameters and seeds.
    - Result 2026-07-24: the registry, noninteractive CLI, strict schema, and
      live Compose orchestration cover the resolver-unavailable bootstrap, P6.9
      cross-epoch lifecycle scenario, P6.2 collection-plus-networkless cloud
      snapshot, P6.3 stopped-collection-plus-networkless one-party snapshot,
      and P6.4 combined snapshot. P6.8 and P6.10-P6.14 remain out of the frozen
      retained corpus unless a later claim explicitly requires them.
  - Subtask `Done` P6.16.2 Produce one structured aggregate-only report per run
    using the P6.1 template without prohibited secret-bearing traces.
    - Historical v1 result 2026-07-24: the privacy-reviewed
      `LOCUS-compose-profile-evidence-v1` format, fixed trace policy, exact
      schemas/validators, host-side provenance, result/configuration binding,
      and exclusive synchronized reread-validated creation produced the three
      immutable retained attack records from clean commit
      `812cb96cc5fba9d4332ae349eb6d664bac0f17b1` and host label
      `cycle1-host-a`.
    - Current v2 result 2026-07-24: the same aggregate-only envelope produced
      three authoritative `compose-attack-v2` records under
      `experiments/raw/attacks-v2/`, bound to clean cutover commit `12ca815` and
      pseudonymous host `cycle1-v2-host-a`. The v1 records remain immutable
      historical evidence for the superseded metadata profile.
  - Completion: the attack profile can reproduce retained-claim adversarial scenarios from documented commands without modifying the normal deployment image.

Phase 6 completion criteria:

- `Done` Every security claim retained for the scoped Cycle 1 manuscript maps
  to an inherited argument, implementation test, retained bounded attack
  experiment, explicit deployment assumption, or limitation; M4 must preserve
  those mappings exactly.
- `Done` The exact registered cloud plus `t-1` persistent snapshot yields no
  implemented offline correctness test for the two bounded synthetic
  candidates in the retained profile; this is bounded implementation evidence,
  not a cryptographic proof.
- `Done` Attempt-budget bypass is not a retained positive claim; the bounded rollback counterexample is documented and reproducible.
- `Done` Every observed retained-scope failure is either fixed, rejected by a
  fail-closed check, or recorded as an explicit limitation.

## Phase 7 - Performance, Resilience, And Scalability Evaluation

Objective: characterize the implemented core's cost and resilience without claiming complete-system or Internet-scale practicality.

Dependencies:

- `Done` Feature freeze for the scoped evaluated protocol and non-claims.
- `Done` Stable disposable same-host deployment automation.
- `Done` Frozen minimum experiment methodology.

Tasks:

- `Done` P7.1 Create `docs/experiment-methodology.md` before final collection.
  - Result 2026-07-23: version 1 freezes questions, scenario blocks, sample counts, warm-up, metrics, host controls, exclusion rules, statistics, raw/processed outputs, and interpretation before any retained performance collection.
  - Completion: experiment matrix is frozen before final runs.
- `Done` P7.2 Select representative `(t,n)` configurations.
  - Result 2026-07-23: the required end-to-end configuration is the implemented native TPASS `(2,3)` path, baseline subset `[1,3]`, alternate subset `[2,3]`, and five-service 4-of-5 authenticated authorization membership. Optional local `(3,5)`/`(5,9)` results may be labeled only as core microbenchmarks.
  - Completion: configurations map to research questions.
- `Done` P7.3 Define the required local scenario; VM/cloud/geographic scenarios are optional future evidence and must not be implied if absent.
  - Result 2026-07-23: the required scope is one labeled same-host Windows/Docker-Linux deployment using the pinned resolver, SeaweedFS, native TPASS, and separated party volumes. No VM, geographic, independent-administration, or real-provider result is implied.
- `Done` P7.4 Measure enrollment latency.
- `Done` P7.5 Measure successful and failed recovery latency.
- `Done` P7.6 Measure cryptographic, resolver, network, storage, and partial-ledger sub-costs without treating ledger overhead as evidence of global security.
- `Done` P7.7 Measure bytes transmitted by role.
- `Done` P7.8 Measure backup size and per-party storage.
- `Deferred` P7.9 Measure CPU and memory; excluded from the frozen Cycle 1
  minimum methodology.
- `Deferred` P7.10 Measure concurrent throughput and tail latency; excluded
  from the frozen Cycle 1 minimum methodology.
- `Done` P7.11 Evaluate party unavailability and threshold reachability for the
  frozen one-party-unavailable same-host scenario.
- `Deferred` P7.12 Evaluate systematic crashes at attempt-control transitions;
  existing focused restart behavior remains an implementation fact.
- `Deferred` P7.13 Evaluate cloud unavailability and stale backups beyond the
  existing correctness tests; excluded from the minimum performance corpus.
- `Deferred` P7.14 Evaluate malicious or slow parties beyond existing focused
  policy tests; excluded from the minimum performance corpus.
- `Done` P7.15 Automate exact raw-data validation and deterministic processing;
  reserve paper-facing table/figure generation for P7.16.
  - Historical v1 result 2026-07-23: `process-performance` validates the fixed 30-file corpus,
    exact common provenance and scenario bindings, canonical bytes and ordered
    input hashes; recomputes all source-series summaries and deterministic
    median intervals; validates the strict processed schema; and exclusively
    publishes below `experiments/processed/performance-v1/`.
  - Verification: generated fixtures cover all ten blocks and three scenarios;
    missing, extra, duplicate-member, noncanonical, mixed provenance/runtime,
    wrong-path, changed-summary, output-scope, and overwrite cases fail closed.
    The complete 57/58-file gate and 131 Python tests with one opt-in skip pass,
    plus all Rust and static-quality checks.
  - Current v2 result 2026-07-24: the default command accepts only the corrected
    `experiments/raw/performance-v2/` corpus and emits
    `LOCUS-performance-processed-v2`. The retained output has canonical
    SHA-256
    `462e492795fafdd90a4f39851a612275193603d816f761728afe05e97a470a6b`
    and was reproduced byte-for-byte during the 2026-07-27 audit. Explicit v1
    paths remain historical-only compatibility.
- `Done` P7.16 Generate the scoped performance paper inputs from scripts.
  - Historical v1 result 2026-07-23: `generate-performance-paper` validates canonical P7.15
    bytes and emits fixed total-latency, phase, logical-role traffic, and
    client/cloud/per-party storage rows plus a strict provenance/digest
    manifest below `paper/generated/performance-v1/`.
  - Verification: generated fixtures prove deterministic row counts/bytes,
    source and output hash binding, schema validation, output scoping,
    idempotence, partial/unexpected-output rejection, changed-output refusal,
    and explicit replacement. No fixture output is retained. A plot is excluded
    from version 1 because it adds no material interpretive value over the
    compact exact tables.
  - Current v2 result 2026-07-24: the default command accepts only the canonical
    v2 processed summary and generates the four
    `LOCUS-performance-paper-inputs-v2` row files and manifest below
    `paper/generated/performance-v2/`. The 2026-07-27 audit returned
    `status: unchanged`.
- `Done` P7.17 Build the frozen automated benchmark-runner interface over fresh disposable Compose projects.
  - Subtask `Done` P7.17.1 Run the minimum frozen enrollment/provisioning, successful recovery, wrong-input rejection, and one-party-unavailable scenarios through public role interfaces. Concurrency and broader failure/resilience cases remain explicitly outside P7.1-P7.3 rather than silently claimed.
  - Subtask `Done` P7.17.2 Emit exact immutable-capable JSON with configuration, seed and versioned scenario order, dependency locks, Docker/Compose and container image identifiers, host metadata, timestamps, phase timings, role bytes, storage, output scan, and cleanup.
  - Result 2026-07-23: the documented development command completed one unretained block with nine validated measured operations and exact cleanup; paper mode remains correctly gated on clean/labeled retained provenance.
  - Completion: the documented command produced the retained schema- and
    cross-binding-validated raw corpus consumed by P7.15.

Phase 7 completion criteria:

- `Done` Every reported number is reproducible from raw data and versioned scripts.
- `Done` Measurements include the exact native crypto and same-host
  network/service boundaries.
- `Done` Percentile ranges and the frozen wrong-input/one-party-unavailable
  behaviors are reported.
- `Done` Implemented security-critical phases have measured latency and
  application-byte costs without implying the unimplemented global bound.

## Phase 8 - Cue Robustness And Guessing Analysis Without Human Subjects

Objective: provide technical evidence about cue policy behavior without claiming human memorability.

Scope status: deferred beyond the frozen Cycle 1 minimum. The implemented cue
and drift corpora remain part of the artifact; a new candidate-ranking study is
not required for the scoped thesis and must not delay retained evidence,
manuscript reconstruction, or anonymous reproduction.

Dependencies:

- `Done` Stable cue-policy implementation and synthetic corpora.
- `Deferred` Ethical/privacy review of any additional data source.

Tasks:

- `Done` P8.1 Document prior work as motivation only and remove LOCUS-specific
  memorability/usability claims.
- `Deferred` P8.2 Build a synthetic-persona generator or select a licensed
  non-sensitive dataset.
- `Deferred` P8.3 Define and evaluate population, public-profile,
  social-knowledge, resolver-observation, and public-policy attacker models.
- `Deferred` P8.4 Implement candidate-ranking strategies.
- `Deferred` P8.5 Report guessing curves under externally enforced attempt
  budgets.
- `Deferred` P8.6 Measure marginal leakage from public policy fields.
- `Deferred` P8.7 Measure correlation among three pairs.
- `Todo` P8.8 Run the existing deterministic cue/drift corpora on clean
  supported Linux and Windows environments as an artifact/interoperability gate,
  not a guessing study.
- `Deferred` P8.9 Run realistic external resolver/contact drift experiments.
- `Deferred` P8.10 Convert any future guessing results into deployment guidance.

Phase 8 completion criteria:

- `Deferred` No new cue-guessing or human-subject result is required for the
  frozen Cycle 1 paper.
- `Done` The paper does not convert synthetic vectors into claims about human
  memory.
- `Deferred` Pair-correlation and attacker-side-information measurements are
  required only if a future guessing study is added.

## Phase 9 - Artifact Packaging And Independent Reproduction

Objective: prepare anonymous artifact for review and later public release.

Dependencies:

- `Done` Frozen evaluated v4/v2 implementation and retained corpus.
- `Done` Final retained-result processing scripts, paper-input generator, and
  expected v2 digest.

Tasks:

- `Done` P9.1 Create anonymous artifact package.
- `Done` P9.2 Create `artifact/README.md`.
- `Done` P9.3 Create `artifact/INSTALL.md`.
- `Done` P9.4 Create `artifact/EVALUATION.md`.
- `Done` P9.5 Provide deterministic local fixtures and canonical/drift corpora
  for cue resolution.
- `Scoped` P9.6 Provide smoke evaluation and full evaluation profiles.
  - Subtask `Done` P9.6.1 Provide deterministic smoke, model, retained-result
    processing, generated-table, and Docker-backed attack/deployment entry
    points over the same versioned implementation.
  - Subtask `Done` P9.6.2 Ensure normal artifact profiles disable synthetic secret inspection and redact identifying or secret material.
- `Done` P9.7 Provide scripts to regenerate principal tables; no figure is
  justified by the frozen methodology.
- `Done` P9.8 The allowlisted package audit excludes credentials, human data,
  sensitive records, Git history/remotes, local user paths, and identifying
  metadata. Final archive member, manifest, extracted-content, license, and
  anonymity inspection passed during M5.2.
- `Todo` P9.9 Verify artifact from clean machine or VM.
- `Todo` P9.10 Ask independent person to reproduce smoke path.
- `Done` P9.11 Record the current package-reproduction failures and fixes;
  additional independent-review findings remain possible.
- `Todo` P9.12 Create anonymous artifact link for ASIACCS review.

Phase 9 completion criteria:

- `Todo` Clean environment can reproduce central functional and attack results.
- `Done` Principal tables can be regenerated from the retained v2 corpus; no
  figure is justified by the frozen methodology.
- `Done` No identifying or sensitive information is present in the inspected
  archive under the implemented anonymity and prohibited-output scans.
- `Todo` Open Science appendix contains required artifact statement/link.

## Phase 10 - Manuscript Reconstruction

Objective: rebuild the manuscript around final contribution and evidence.

Dependencies:

- `Done` Stable scoped technical contribution and explicit non-claims.
- `Done` Minimum retained Cycle 1 attack and performance experiments.
- `Done` Claim-evidence matrix for the frozen retained claim set.

Tasks:

- `Done` P10.1 Rewrite title and abstract after final results exist.
- `Done` P10.2 Rebuild introduction around the offline-oracle problem, storage-separated TPASS composition, structured-cue boundary, concrete prototype, measured results, and explicit online limitations.
- `Done` P10.3 State contributions using completed work only.
- `Done` P10.4 Separate inherited TPASS security, new LOCUS mechanisms, implementation validation, and operational assumptions.
- `Done` P10.5 Reduce attempt control to partial implementation context, bounded negative result, deployment assumption, and future work.
- `Done` P10.6 Remove unimplemented public recovery authorization from the positive contribution; retain its absence as a limitation.
- `Done` P10.7 Replace toy benchmark results with retained end-to-end same-host measurements.
- `Done` P10.8 Add retained attack-evaluation methodology, outcomes, and narrow interpretation limits.
- `Done` P10.9 Add conservative cue-policy robustness/guessing analysis without human memorability or measured-entropy claims.
- `Done` P10.10 Strengthen mechanism-level related work.
- `Done` P10.11 Keep limitations prominent.
- `Done` P10.12 Update Open Science appendix to ASIACCS half-page constraint.
- `Done` P10.13 Update Ethical Considerations appendix to ASIACCS half-page constraint if relevant.
- `Done` P10.14 Verify anonymity, page limit, formatting, references, equations, figures, and tables.
- `Done` P10.15 Remove speculative or future-tense contribution language.

Phase 10 completion criteria:

- `Done` Every abstract and introduction claim maps to evidence.
- `Done` Novelty is understandable without appendices.
- `Done` No toy-backend result supports practicality.
- `Done` Manuscript is anonymous and within ASIACCS format/page requirements.
- `Done` References and numerical results are verified.

## Phase 11 - Internal Review, Red Teaming, And Submission Readiness

Objective: identify technical and presentation weaknesses before external review.

Dependencies:

- `Done` Complete scoped manuscript.
- `Todo` Artifact candidate.

Tasks:

- `Todo` P11.1 Conduct internal security review.
  - Subtask `Todo` P11.1.1 Offline-oracle creation.
  - Subtask `Todo` P11.1.2 Attempt-budget bypass.
  - Subtask `Todo` P11.1.3 Lockout denial of service.
  - Subtask `Todo` P11.1.4 Replay and rollback.
  - Subtask `Todo` P11.1.5 Malicious-party behavior.
  - Subtask `Todo` P11.1.6 Secret leakage.
  - Subtask `Todo` P11.1.7 Cryptographic misuse.
- `Todo` P11.2 Ask external/unfamiliar reader to summarize contribution.
- `Todo` P11.3 Ask cryptography-oriented reviewer to inspect protocol mapping.
- `Todo` P11.4 Ask systems-oriented reviewer to inspect deployment/evaluation.
- `Todo` P11.5 Ask usable-security-oriented reviewer to flag unsupported human claims.
- `Todo` P11.6 Run artifact from clean environment again.
- `Todo` P11.7 Perform paper-to-code consistency audit.
- `Todo` P11.8 Perform table/figure provenance audit.
- `Todo` P11.9 Check anonymity, metadata, repository links, acknowledgments, and artifact link.
- `Todo` P11.10 Prepare likely reviewer questions and evidence-based answers.
- `Todo` P11.11 Rank all remaining issues as blocking, major limitation, minor, or post-submission.
- `Todo` P11.12 Submit only when all blocking issues are closed or explicitly accepted as risks.

Phase 11 completion criteria:

- `Todo` Independent readers agree on the primary contribution.
- `Todo` No unresolved issue invalidates a headline claim.
- `Todo` Artifact reproduces central results.
- `Todo` Manuscript acknowledges all material limitations.
- `Todo` ASIACCS submission requirements are satisfied.

## Priority Tiers

Tier 1 - submission blockers for the scoped paper:

- `Done` T1.1 Research question, scope/non-claims, threat model, novelty
  comparison, and claim-evidence matrix.
- `Done` T1.2 Native cryptographic core, standard backup cryptography,
  deterministic cue policy, separated cloud/party roles, and same-host
  authenticated deployment.
- `Done` T1.3 Bounded rollback negative result and development-validated P6.2,
  P6.3, P6.4, lifecycle, output-safety, and performance-runner paths.
- `Done` T1.4 Freeze the clean verified implementation/documentation baseline.
- `Done` T1.5 Complete P7.15/P7.16 deterministic processing and generated
  paper inputs.
- `Done` T1.6 Collect the minimum retained attack and performance corpus from a
  clean labeled commit.
- `Done` T1.7 Verify every cited source and reconstruct the manuscript around
  retained results and explicit limitations.
- `Todo` T1.8 Build and independently reproduce the anonymous artifact.
- `Todo` T1.9 Complete internal review, paper-to-code/provenance audit,
  anonymity, formatting, and submission checks.

Tier 2 - strongly valuable only when it directly reduces a Tier 1 risk:

- `Todo` T2.1 Clean Linux/Windows cue-vector and artifact execution.
- `Todo` T2.2 Focused resolver/cloud/party/log/exception/timing metadata analysis
  required by retained wording.
- `Todo` T2.3 Static and dependency security scans.
- `Todo` T2.4 Independent cryptographic mapping review.
- `Todo` T2.5 Additional malformed/equivocation or selective-refusal scenarios
  only if the manuscript retains the matching claim.

Tier 3 - deferred beyond the scoped Cycle 1 paper:

- `Deferred` T3.1 Global rollback-resistant attempt control, public OIDC/DPoP
  admission, false-lockout administration, and general party replacement.
- `Deferred` T3.2 VM/geographic/independently administered or real-provider
  deployment.
- `Deferred` T3.3 CPU/memory, concurrency, throughput, malicious-slow-party,
  and broad crash-schedule evaluation beyond the frozen minimum methodology.
- `Deferred` T3.4 Full interactive client UX, mobile client, alternate cue
  families, and private resolver mechanisms.
- `Deferred` T3.5 Broad cue-ranking/guessing studies and any human-subject
  memorability or usability study.
- `Deferred` T3.6 Production orchestration, formal machine-checked proof, and
  audited/side-channel-hardened cryptography.

Tier 2 and Tier 3 work must not delay M0-M6.

## Submission-Readiness Checklist

Do not submit until all applicable items are `Done` or explicitly accepted as residual risk.

- `Done` S1: Target cycle and submission scope recorded.
- `Done` S2: Manuscript uses latest ACM sigconf style and satisfies ASIACCS page limits.
- `Done` S3: Manuscript is anonymized.
- `Done` S4: Open Science appendix is present after references and within ASIACCS guidance.
- `Done` S5: Ethical Considerations appendix is present if relevant and within ASIACCS guidance.
- `Done` S6: No fabricated, unverified, or suspicious cited references remain.
- `Done` S7: Every abstract/introduction claim maps to evidence.
- `Done` S8: No unsupported LOCUS human memorability/comparative usability claim remains; CLM-21 records the completed claim-scope audit.
- `Done` S9: Toy crypto results are removed from the evaluation table, and the
  retained local profile is explicitly not used for a production-practicality
  claim.
- `Todo` S10: Distributed prototype can be reproduced from clean checkout.
- `Todo` S11: Attack evaluation reproduces central security claims.
- `Todo` S12: Performance evaluation reproduces central quantitative claims.
- `Todo` S13: Artifact is anonymous, accessible, and independently smoke-tested.
- `Done` S14: Paper-to-code consistency audit completed.
- `Done` S15: Table/figure provenance audit completed.
- `Todo` S16: All known submission blockers resolved or deliberately scoped out.
- `Done` S17: Project release authority, artifact license terms, and
  third-party redistribution inventory are resolved.

## First Task To Start

Recommended next task:

- Complete **M5**:
  1. reproduce the scoped quality, artifact-smoke, negative-model,
     deterministic cue/drift, attack, and retained-result processing paths on
     clean Linux and Windows/CI;
  2. rerun Docker-backed deployment/S3 gates where the engine is available;
  3. record privacy-safe reproduction evidence, obtain an unfamiliar-reviewer
     smoke result, and reconcile the Open Science appendix with the final
     package entry points.
- Keep the retained corpus immutable. Any changed collection code or source
  state requires a new evidence version/path rather than overwriting M3.
- Repository publication and remote CI are owner-managed manual steps and do
  not block the local manuscript audit.

Reason: M4 closed the paper-to-code, citation, generated-table, page-limit,
anonymity, and visual-layout gaps. Clean anonymous reproduction is now the
largest unclosed submission risk and the prerequisite for independent review.
