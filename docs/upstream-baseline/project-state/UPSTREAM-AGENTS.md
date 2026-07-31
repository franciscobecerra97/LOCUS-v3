# AGENTS.md

## Authority And Scope

This is the authoritative project-level instruction file for Codex work in this repository. The file is named `AGENTS.md` because that is the convention Codex reads. If a user refers to `AGENT.md`, treat that as a reference to this file unless they explicitly ask to create a separate singular file.

Follow any more specific `AGENTS.md` in a subdirectory if one is added later.

## Authorized Defensive Security Scope

LOCUS is an academic private-key-recovery research prototype owned and operated
by the repository owner. The owner authorizes defensive security analysis of
this repository and its disposable local test environment solely to validate
documented claims, reproduce bounded counterexamples, and identify or correct
implementation defects.

This authorization covers only project-controlled code and state:

- this repository and its generated build/test artifacts;
- synthetic fixtures, synthetic identities/accounts, generated test keys,
  generated credentials, test doubles, and bounded synthetic candidate sets;
- explicitly named loopback services and disposable containers, networks, and
  volumes created by the LOCUS task runner for the current test; and
- local static analysis, protocol/state-machine exploration, malformed-input
  testing, fuzz/property testing, and bounded replay, rollback, concurrency,
  crash, availability, and snapshot simulations described in `PLAN.md`.

When a threat-model scenario assumes that a cloud, recovery party, resolver,
coordinator, client, or storage role is compromised, represent the compromise
by supplying pre-generated synthetic state, a read-only snapshot, a test double,
or an explicitly instrumented local role. Do not implement or exercise the
mechanism that would compromise a real system. Possession of synthetic party
state in an isolated regression test is an input assumption, not authorization
to obtain credentials or state from any external party.

All adversarial test traffic must remain inside the test's declared local trust
boundary. A networked security test may connect only to loopback endpoints or
to the exact service names in the disposable Compose project created for that
test. The resolved role graph must be checked before startup. A candidate-testing
process that is specified as offline must have no network, credentials, or
unrelated mounts; any attempted connection or excluded-path access must fail
the scenario. Ordinary toolchain setup may retrieve pinned dependencies or
container images from their normal official registries when separately allowed
by the execution environment, but no adversarial payload, scan, probe, or test
traffic may be directed at those registries.

Do not:

- target, enumerate, scan, probe, exploit, or connect to third-party or
  production systems;
- use real user accounts, credentials, recovery material, private keys,
  personal data, production logs, or production traffic;
- perform or facilitate credential theft, credential stuffing, phishing,
  password cracking against real data, persistence, stealth, evasion,
  exfiltration, destructive action, ransomware behavior, or denial of service;
- develop an exploit or compromise mechanism for a real recovery party, cloud
  account, resolver, coordinator, client endpoint, identity provider, or host;
- turn a scenario-specific, bounded regression harness into reusable offensive
  tooling or make it configurable for arbitrary targets;
- weaken isolation, authorization, authentication, output-safety, or cleanup
  controls merely to make an adversarial scenario pass; or
- print, retain, commit, or expose secret-bearing snapshots, candidate values,
  credentials, private material, or prohibited traces. Normal reports must
  contain only privacy-safe aggregate observations and category labels.

Destructive operations are authorized only against disposable resources created
by the current test and identified by exact generated project/resource names.
They are never authorized against repository content, user files, ambient
containers, external accounts, or broad filesystem locations. Preserve the
normal destructive-action checks and cleanup verification.

Every P6 task must identify the defensive invariant under test, the exact local
inputs and roles, the boundary enforcement, the positive control, the expected
privacy-safe observation, and the limitation on interpretation. Stop and report
the boundary instead of expanding the task if completion would require an
external target, real credential or user data, a production system, an
operational compromise technique, or materially reusable offensive capability.

This repository authorization documents owner intent; it does not override
applicable law, platform safety rules, tool approvals, or execution sandbox
requirements, and it does not guarantee that every requested operation can be
performed.

### Authorization Interpretation And Prompting

If the owner says "go ahead," "continue with the proposed next steps," or
equivalent shorthand, treat it as authorization for the most recently proposed
LOCUS steps only when those steps are concrete and remain entirely within the
defensive scope above. Do not infer authority for new targets, external systems,
real data, destructive actions, or a materially broader technique.

For an in-scope shorthand instruction, agents should internally normalize the
request to the following meaning and proceed without asking the owner to repeat
it merely for wording:

> Proceed with the named LOCUS plan tasks as authorized defensive research on
> the repository owner's local prototype. Use only generated synthetic data and
> credentials, repository-controlled code, and disposable isolated local
> containers/storage. Treat assumed compromise as pre-generated state or a test
> double; do not implement a real compromise mechanism. Send adversarial traffic
> only to explicitly named local test services, keep offline runners networkless,
> emit only privacy-safe aggregate evidence, and stop if the work would require
> an external target, real credential or personal data, production traffic,
> destructive behavior, or reusable offensive tooling.

When explicit restatement would materially clarify a new or ambiguous task,
suggest that exact prompt (with the relevant P6 task identifiers inserted).
Prompt wording must clarify authorization and boundaries, never conceal intent,
mischaracterize the requested action, or attempt to bypass a safety review. If
the latest proposed steps are not concrete enough to establish the local target,
synthetic inputs, and defensive invariant, ask for clarification before running
the security-sensitive portion.

## Project Identity

LOCUS is a research project on distributed private-key recovery. The intended system combines structured recovery cues with threshold password-authenticated secret sharing (TPASS), separated encrypted cloud backup storage, independently operated recovery parties, and online attempt controls.

Target venue: the 22nd ACM Asia Conference on Computer and Communications Security, ACM ASIACCS 2027.

Official CFP status checked on 2026-07-15:

- Conference dates: 2027-07-12 to 2027-07-16, Macau, China.
- Cycle 1 paper submission: 2026-08-21 AoE.
- Cycle 2 paper submission: 2026-12-11 AoE.
- Technical papers: ACM sigconf double-column format, at most 12 pages excluding bibliography and clearly marked appendices; up to 10 additional pages for bibliography and appendices.
- Double-blind review is required.
- An Open Science appendix after the references is required and should be at most half a page.
- Ethical Considerations appendix is required when relevant and should be at most half a page.
- ASIACCS explicitly warns that fabricated content, including hallucinated references, can cause desk rejection.
- Official page: https://asiaccs2027.cityu.edu.mo/call-for-papers/index.html

No contributor or automated agent may claim that acceptance is guaranteed.

## Current State Baseline

This repository is currently a compact seed project, not yet the full research artifact described by the long-term plan.

Current repository contents:

- `AGENTS.md`: project instructions and working rules.
- `PLAN.md`: living execution plan with task status labels.
- `paper/`: current LaTeX manuscript, bibliography, compiled PDF, ACM style files, generated table rows, and LaTeX build byproducts.
- `paper/main.tex`: current manuscript source. The compiled 2026-07-24 review
  PDF is 14 pages, with the main text ending and references beginning on page
  11; it includes cautious limitations, Open Science, Ethical Considerations,
  and a TPASS appendix.
- `paper/references.bib`: bibliography. Every entry cited by the current
  manuscript was verified during M4; unused entries remain outside that audit.
- `paper/related_work.tex`: separate related-work draft that is not currently included by `paper/main.tex`; treat it as stale or alternate material until reconciled.
- `paper/generated/`: generated table-row inputs derived from benchmark JSON.
- `prototype/`: local Python reference prototype.
- `prototype/locus/`: deterministic encoding, backup-cryptography helpers, the default native Rust/Ristretto TPASS adapter, explicit simulator/concrete toy backends, and the LOCUS state-machine flow.
- `prototype/tests/test_locus_flow.py`: current unit/failure tests.
- `prototype/scripts/`: demo, synthetic educational walkthrough, benchmark, and
  benchmark-table formatting scripts.
- `prototype/.benchmarks/`: generated benchmark JSON outputs. These are machine-specific and should eventually be treated as generated artifacts, normally ignored by version control.
- `tpass-core/`: Rust/Ristretto255 implementation of the Yi et al. zero-knowledge TPASS construction, including versioned canonical external encodings.
- `tpass-python/`: PyO3/maturin native binding that exposes the Rust protocol phases and wire messages to Python without serializing client blinders or party ephemerals.
- `docs/`: threat model, research question, cryptographic design, attempt-control design, recovery authorization, and claim/evidence tracking.
- `deploy/`: the digest-pinned default isolated Compose deployment and focused S3-only conformance slice.
- `pyproject.toml`, `uv.lock`, `.python-version`, and `rust-toolchain.toml`: pinned Python, quality-tool, native-build, and Rust environments.
- `tasks.py`: cross-platform setup, formatting, checking, testing, native-build,
  demo, synthetic walkthrough, benchmark, and smoke entry points.
- `.github/workflows/ci.yml`: frozen Linux/Windows checks plus a gated artifact-smoke job; its first remote green run still requires verification.
- `extra/TPASS.pdf`: local copy of the 2019 JPDC TPASS article by Yi et al.

Important current absences:

- No `configs/` or `attacks/` directories exist yet. `artifact/` now contains
  the allowlisted anonymous-package, installation, evaluation, manifest, and
  release-gate contract. The owner approved Apache-2.0 for project-authored
  software/configuration and CC-BY-4.0 for project-authored
  documentation/aggregate experiment material; archive creation still requires
  final validation and a clean tree. `experiments/` contains the retained
  aggregate-only P6.2-P6.4 and ten-block P7 corpus plus its deterministic
  processed summary. These results still need anonymous clean-host
  reproduction.
- Five recovery-party services now run in disjoint same-host containers with
  separate identities and volumes. No independently administered or multi-host
  party deployment exists.
- Strict filesystem and S3-compatible cloud-role adapters store bounded canonical
  immutable backup objects separately from party configurations/databases. The
  S3 adapter passes both its focused contract and a combined client/resolver/
  five-party recovery path against digest-pinned SeaweedFS with a dedicated
  volume/network. This is not an independent cloud deployment or real provider.
- A signed two-phase attempt ledger now has per-party durable SQLite state,
  exact retries, local concurrency locks, remote quorum collection, and restart
  catch-up. It still lacks rollback-resistant state, recovery-request admission,
  lifecycle handling, and evidence for the complete global attempt bound.
- A deterministic HTTP resolver fixture is integrated into the local deployment;
  no realistic external resolver integration exists.

## Research Objective

The project objective is to produce the strongest feasible ASIACCS 2027 research artifact and manuscript for the scoped LOCUS architecture defined in `docs/limitations-and-assumptions.md`. On 2026-07-22 the project deliberately stopped treating a complete rollback-resistant distributed attempt bound as a Cycle 1 requirement because P5.13 exposed a quorum-only rollback counterexample and adding a monotonic authority would materially change the architecture.

The likely strongest contribution is not TPASS itself. LOCUS should be positioned as an applied cryptography and distributed security systems contribution:

1. A distributed private-key recovery architecture that separates encrypted cloud backup storage from threshold recovery-party state.
2. A cue-policy abstraction that lets a client derive the TPASS password from reproducible structured recovery input without storing raw cues, cue identifiers, password verifiers, recovered group secrets, or wrapping keys at the cloud or recovery parties.
3. A concrete research prototype using standard cryptographic primitives, separately identified same-host recovery-party services, durable state, and a cloud-compatible object store, without claiming independent administration.
4. An explicit analysis of residual online guessing and a bounded negative result showing why the partial quorum ledger is not rollback-resistant global attempt control.
5. Attack-driven validation and performance/resilience evaluation limited to the architecture, storage-separation, deterministic-cue, cloud-binding, and exact tested failure claims.
6. A reproducible anonymous artifact and an evidence-backed manuscript with prominent assumptions and limitations.

The project should not be framed as inventing TPASS, proving location-person cue memorability, producing production-audited cryptography, enforcing global rate limits, resisting party-state rollback, providing public recovery admission, or demonstrating independently administered parties.

## Current Paper Status

The current paper already contains:

- A clear private-key recovery motivation.
- A threat model covering cloud compromise, fewer than `t` compromised parties, combined cloud and below-threshold compromise, online guessing, public/social knowledge, resolver observation, malicious cloud rollback/substitution, and threshold compromise as out of scope.
- A protocol construction using cue-derived TPASS password input, encrypted cloud backup, and party-stored threshold state.
- A Python reference-prototype implementation section.
- Retained same-host native 2-of-3 latency results generated from the exact
  ten-block P7 corpus.
- Security claims for correctness, cloud-only no offline oracle, below-threshold compromise, combined compromise, tamper detection, online guessing model, resolver-boundary leakage, and authority separation.
- Limitations, Open Science, Ethical Considerations, and a TPASS appendix.

Paper issues to fix before submission:

- The conservative cue-claim audit is complete: LOCUS-specific memorability,
  comparative recall/reproduction, and usability claims were removed. Prior
  human-memory work remains motivation only, and no human-subject evidence exists.
- The archived v1 evaluation binds the superseded metadata profile and is
  historical only. The corrected v2 same-host synthetic corpus is retained,
  processed, and switched into the manuscript. It still does not support strong
  practicality, scalability, concurrency, production, or independently
  administered deployment claims.
- The attempt-control implementation is a partial signed-ledger slice with durable
  per-party state and authenticated local process boundaries. P5.13 demonstrates
  a conflicting-certificate trace after one honest database restore and a
  restored-retirement trace. Global-bound, rollback-resistance, public-admission,
  and safe false-lockout claims must be removed rather than treated as Cycle 1
  implementation blockers.
- The manuscript must use "rate-limited", "auditable", "durable", and
  attempt-control wording only for exact local implementation facts or explicit
  deployment assumptions, never as a demonstrated LOCUS security property.
- The current review PDF is 14 pages including references and appendices, with
  main text and references meeting on page 11. M5.0 rebuilt it after the
  TPASS/authorizer notation correction with Tectonic 0.16.9 and visually
  inspected every page.
- `paper/related_work.tex` is an explicitly marked historical/unverified draft;
  `paper/main.tex` and `docs/related-work-comparison.md` are authoritative.
- Current cited bibliography entries and URLs are recorded in
  `docs/reference-audit.md`. Do not promote an unused entry into the manuscript
  without verifying it first.
- LaTeX build byproducts may exist in a developer checkout but are ignored and
  rejected if tracked. `paper/main.pdf` is an intentional derived review
  snapshot and currently matches `paper/main.tex`; its SHA-256 is
  `3b68869bf99572e8bafa3efa4fb0fc4567e76aec093c0bcde3313f8d9e32c8e3`.

## Current Prototype Status

The current prototype combines a local Python research scaffold with a native
Rust TPASS core, a narrow PyO3 boundary, a role-separated HTTPS adapter, and a
complete isolated same-host Compose path containing a client, deterministic
resolver, S3-compatible store, and five recovery parties. It is not an
independently administered or multi-host deployment.

Implemented:

- Deterministic JSON-style encoding with Unicode NFC normalization in `prototype/locus/codec.py`.
- Domain-separated hashing and secure random generation plus pinned-library HKDF-SHA-256 and AES-256-GCM in `prototype/locus/crypto.py`.
- A default native Rust/Ristretto TPASS adapter plus explicitly selected simulator and concrete toy safe-prime backends in `prototype/locus/tpass.py`.
- Enrollment and recovery flow in `prototype/locus/core.py`.
- Local synthetic location-person cue records.
- Backup digest binding.
- Party records with TPASS state and local attempt counters.
- Unit/failure tests for successful recovery, wrong cues, insufficient parties, threshold subsets, digest mismatch, rollback-like stale backup, ciphertext authentication failure, malformed metadata/state, unsupported versions, attempt limit, state-separation audit, and concrete backend success/failure.
- Benchmark scripts and generated table rows.
- A Rust/Ristretto255 implementation of enrollment, blinded client requests, server proofs, response shares, aggregation, and final digest validation.
- A versioned canonical binary format for public parameters, secret party state, client requests, party commitments, response shares, and gateway responses.
- A PyO3/maturin extension exposing the Rust phases to Python through canonical byte messages and redacted native state objects.
- Complete local LOCUS enrollment and recovery through the native backend, including serialized public parameters and independent serialized party state.
- A strict versioned AES-256-GCM backup format with canonical authenticated metadata and HKDF-SHA-256 wrapping-key derivation through `cryptography` 49.0.0.
- Cross-language tests for successful recovery, wrong-input rejection, and malformed secret-state rejection.
- Canonical Ed25519 two-phase attempt and response-freshness certificates with a
  transport-neutral untrusted coordinator.
- Per-party SQLite `FULL`-synchronous ledger, phase, idempotency, and redacted
  audit state with restart handling.
- Durable 32-byte HTTP idempotency keys bind the authenticated caller, method,
  exact route, and canonical request body before every mutating operation;
  completed response bytes survive restart and changed reuse fails closed.
- A bounded TLS 1.3 authorizer adapter with mutual CA validation, exact
  certificate pins, strict duplicate-free JSON, and client-side vote validation.
- A five-subprocess/five-database integration test covering remote exact retry,
  unauthorized and malformed requests, one-party loss, freshness, restart, and
  certificate catch-up.
- Native commitment/response service routes using strict unpadded base64url wire
  objects, distinct coordinator/party identities, and per-process secret state.
- Remote native tests for correct/wrong-input 2-of-3 recovery, alternate subsets,
  one-party loss, cross-session rejection, retry, catch-up, and fail-closed loss
  of an open commitment across restart.
- A bounded canonical `LOCUS-cloud-backup-object-v1` filesystem adapter with
  immutable atomic publication, exact `(bid, epoch, backup_digest)` references,
  and explicit not-found/unavailable/corrupt/conflict/oversized outcomes.
- The current deployed profile is the strict
  `LOCUS-reference-backup-v4`/`LOCUS-location-person-set-v1`/
  `LOCUS-compose-deployment-v2` combination. Signed
  `LOCUS-attempt-config-v2` and party database schema v4 bind the same backup
  epoch/digest; the authenticated five-process path validates and fetches the
  object before an attempt and decrypts its private key after recovery. The
  archived v3/legacy-label Cycle 1 corpus is immutable historical evidence.
- A local same-membership backup-epoch lifecycle uses canonical old-quorum
  approvals, new-quorum readiness statements, durable successor preparations,
  and atomic predecessor retirement/successor activation. Direct successor
  insertion and old/cross-mixed state are rejected. Authenticated lifecycle
  transport and successor native-state service loading remain absent.
- An explicit-credential `boto3==1.43.51` SigV4 S3 adapter with HTTPS-by-default
  configuration, conditional immutable writes, transfer checksum, bounded
  streaming reads/timeouts/retries, and application-authoritative canonical and
  digest validation.
- A one-command live S3 conformance path using runtime-generated credentials, a
  digest-pinned SeaweedFS 4.29 container, a dedicated network/named volume, and
  automatic cleanup. The service is loopback-only and plaintext by explicit
  local-test opt-in.
- A pinned multi-stage Linux reference image and default Compose deployment with
  a networkless one-shot provisioner, exact three-pair synthetic resolver, S3,
  five non-root parties, ephemeral client, three internal networks, no host
  ports, and pairwise-disjoint persistent party/cloud volumes.
- A one-command deployment smoke gate that validates the resolved and live role
  graph, audits provisioned snapshots, performs native S3-backed recovery,
  restarts one party, performs the next exactly-once recovery, scans output for
  known prohibited material, and removes all Docker resources.
- Versioned experiment provenance with exact Git/lock/configuration/randomness/
  time/host/output metadata and a strict paper-evidence gate.
- A versioned aggregate-only retained Compose evidence record with exact
  metadata/result cross-binding, fixed trace policy, recursive output safety,
  exclusive synchronized creation, byte-identical reread validation, and
  schemas for attack, benchmark, and performance results. Snapshot/database bytes,
  credentials, candidates, per-candidate outcomes, arbitrary logs, packet
  captures, core dumps, and exception traces are excluded. Every current
  Compose service disables core files; profile logs are scanned then discarded.
- A frozen minimum Cycle 1 performance methodology covering the implemented
  same-host native 2-of-3 path, ten randomized three-scenario blocks, declared
  warm-up/sample counts, phase/byte/storage metrics, no-outlier and invalid-run
  rules, descriptive statistics, raw/processed lifecycles, and explicit
  exclusions for concurrency, CPU/memory, VM/geographic, and production claims.
- A noninteractive three-scenario Compose performance-block runner with a
  versioned seed-derived order, one warm-up plus three measured operations per
  fresh project, a stable-label reference image built once before the block,
  exact phase/byte/storage metrics, runtime and image identities, strict
  provenance cross-binding, output scanning, and exact-label cleanup.
  Its current retained v2 corpus contains 30 measurements for each of the three
  frozen scenarios and binds clean commit `12ca815` and pseudonymous host
  `cycle1-v2-host-a`; the v1 corpus remains historical.
- A deterministic P7 corpus processor that requires the exact ten-block,
  three-scenario canonical raw layout; cross-checks commit, host, locks, runtime,
  seed-derived order, trace policy, and result bindings; and exclusively emits
  a versioned aggregate processed artifact with exact input hashes, source
  series, descriptive statistics, and deterministic bootstrap intervals.
  Generated-fixture regression tests pass, and the retained v2 30-file corpus
  produced `LOCUS-performance-processed-v2` with SHA-256
  `462e492795fafdd90a4f39851a612275193603d816f761728afe05e97a470a6b`.
- A deterministic P7.16 paper-input generator that accepts only the canonical
  processed artifact and emits fixed latency, phase, application-byte, and
  storage LaTeX rows plus a manifest binding the source and every output digest.
  Identical generation is idempotent and changed replacement is explicit.
  Generated-fixture tests pass; the retained v2 processed result produced four
  `LOCUS-performance-paper-inputs-v2` manifest-bound LaTeX row inputs.
- Recursive public-output validation integrated into demo, deployment, benchmark,
  experiment-configuration, and benchmark-table paths, plus dynamic deployment
  log canaries and an explicit output-safety contract.
- A synthetic-only in-process educational walkthrough with numbered fictional
  cue aliases, the exact three-pair canonicalizer, deployed v4 backup
  composition, native 2-of-3 TPASS enrollment/recovery, a bounded in-memory
  attempt counter, generic failure output, and no persistent protocol state.
  It is teaching material, not an experiment or deployed-role claim.
- Pinned cue-policy and resolver-drift corpora covering exact canonical bytes,
  ordering, precision, locale/Unicode rejection, rename/reindex stability,
  canonical drift, provider-version change, ambiguity, and missing records.
- A dependency-free bounded compact-profile attempt-control explorer with a
  strict report/schema and regression tests. It finds quorum-only rollback and
  restored-retirement counterexamples and finds no counterexample within the
  frozen ideal-anchor comparison bounds. This is a negative result, not a proof.
- A registered cloud-only snapshot scenario that copies the exact synthetic S3
  object and public manifest into a strict two-file volume, then tests two
  synthetic candidates in a separate non-root, credential-free, read-only,
  networkless container with positive controls and aggregate-only output. Its
  retained run passed from the clean Cycle 1 collection commit; it is not a
  cryptographic proof or real-provider result.
- A registered one-party snapshot scenario that copies every persistent file in
  a stopped post-recovery synthetic party-1 volume into a canonical manifest,
  then tests two candidates in a separate non-root, credential-free, read-only,
  networkless container. Exact authorizer/TLS/native/SQLite bindings, positive
  controls, aggregate-only output, scanning, and cleanup pass. The retained run
  is bounded evidence for one party in the deployed 2-of-3 profile, not a
  compromise mechanism or cryptographic proof.
- A registered combined-snapshot scenario that binds the exact cloud snapshot
  and matching stopped party-1 snapshot in a networklessly finalized canonical
  union, then tests two candidates in a separate non-root, credential-free,
  read-only, networkless container. Cross-role identifier/epoch/digest/TPASS
  bindings, positive controls, aggregate-only output, scanning, and cleanup
  pass. The retained run covers one deployed 2-of-3 profile; it is not a
  compromise mechanism or cryptographic proof.

Partially implemented:

- Paper-facing TPASS algebraic recovery path: implemented over Ristretto255,
  integrated into local and packaged same-host recovery paths, and measured in
  the retained P7 profile, but not independently reviewed.
- Attempt control: the signed ledger/freshness/pre-commitment slice is durable and
  networked in same-host tests, but it is only local implementation evidence.
  The scoped paper does not claim a complete attempt bound; admission, rollback
  resistance, arbitrary scheduling, and false-lockout safety are future work.
- State separation: recursive snapshots, resolved/live Compose inspection,
  disjoint volumes/networks/credentials, known-secret output scans, and the
  exact P6.2 cloud, P6.3 one-party, and P6.4 matching combined persistent-
  snapshot boundaries cover the default deployment and now have retained
  aggregate-only records. Runtime memory, crash dumps, arbitrary traces,
  hostile-host access, and independently administered volumes remain untested.
- Rollback detection: current honest signed/durable party bindings detect stale,
  substituted, or corrupt cloud objects, but party-state rollback, surviving-peer
  reconciliation, coordinated rollback, and external anchors remain unimplemented.
- Cue policy: the frozen exactly-three-pair canonicalizer is integrated with a
  deterministic deployment resolver fixture and pinned canonical/drift corpora.
  Clean Linux/Windows vector execution, alternate-client interoperability, and
  realistic external resolver behavior remain.

Absent:

- Authenticated transport for enrollment, OIDC/DPoP public-client admission,
  lifecycle, and audit operations beyond the coordinator/party service adapter.
- Deployment-grade provisioning and migration of durable transactional state.
- Complete OIDC/DPoP admission and credential replay protection.
- Concurrent networked TPASS recovery handling and systematic scheduling tests.
- Rollback-resistant distributed attempt-control reconciliation.
- Exportable privacy-minimized audit interfaces and evaluation.
- Recovery-request authorization.
- Party replacement, authenticated lifecycle services, and deployed successor
  TPASS-state activation.
- Resolver privacy analysis backed by implementation.
- Complete attack experiment suite beyond the registered P6.2 cloud, P6.3
  one-party, and P6.4 matching combined persistent-snapshot boundaries.
- Anonymous clean-host reproduction of the retained and processed paper-facing
  end-to-end performance results.

## Current Build, Test, And Execution Instructions

Install the pinned Python environment and build tools:

```powershell
uv sync --frozen
```

Run the complete quality, native-build, and test gate:

```powershell
uv run --frozen python tasks.py check
```

Expected current result: the parser passes 65 project Python files; Ruff and mypy
pass 66 source files including `tasks.py`; 151 default Python tests run with one
opt-in live S3 test skipped; 17 Rust core unit tests and one
fixed-vector integration test pass; and both Rust crates pass formatting and
clippy. The command builds the local abi3 Python extension with maturin before
running Python tests.

Run the optional synthetic-only in-process educational walkthrough:

```powershell
uv run --frozen python tasks.py walkthrough
```

This command accepts only numbered fictional pair aliases, generates its own
test key, writes no protocol state, and emits redacted stage summaries. It is
teaching material rather than experiment evidence or a deployed-role test.

Run the opt-in live S3 conformance path (Docker required):

```powershell
uv run --frozen python tasks.py s3-smoke
```

This command must pass one live test and remove its ephemeral container, network,
and volume. It is not part of the default cross-platform gate and is not a real
cloud-provider result.

Run the complete isolated deployment path (Docker required):

```powershell
uv run --frozen python tasks.py deployment-smoke
```

This command builds the pinned reference image; validates and starts the
client/resolver/S3/five-party topology; audits snapshots and live boundaries;
performs recovery around a party restart, then stops that party and recovers
through the alternate fixed subset; scans output; and removes all resources.
It is same-host synthetic evidence, not independent administration or a
paper-facing performance result.

Run one unretained frozen performance block (Docker required):

```powershell
uv run --frozen python tasks.py deployment-performance-block --block 1 --seed 20260723 --evidence-class development
```

This command runs only synthetic same-host services in three fresh disposable
projects, emits aggregate profile records to standard output, retains no raw
file, scans service output, and requires exact cleanup. Paper collection also
requires a clean commit, pseudonymous host label, and immutable `--out-dir`.

Validate and process the corrected v2 retained performance corpus:

```powershell
uv run --frozen python tasks.py process-performance
```

This command defaults to the exact 30 canonical `performance-v2` raw files,
validates their common provenance and frozen bindings, and exclusively writes
the matching v2 processed summary. Explicit v1 paths remain available only to
validate the immutable archived corpus. It does not collect data or create a
paper claim.

Generate the versioned paper inputs:

```powershell
uv run --frozen python tasks.py generate-performance-paper
```

This command validates the canonical processed source and creates four fixed
LaTeX row fragments plus their matching v2 provenance/digest manifest. The row
format emits no plot and does not promote generated fixtures to evidence.

Run the current artifact smoke path:

```powershell
uv run --frozen python tasks.py artifact-smoke
```

Run benchmarks without writing files:

```powershell
uv run --frozen python tasks.py benchmark --backend native --runs 1
```

Current benchmark JSON generation writes into `prototype/.benchmarks/`. Do not regenerate paper-facing benchmark files unless the task explicitly calls for it and the plan is updated with provenance.

The native Ristretto backend is the default local demo and benchmark backend. Simulator and toy safe-prime runs require explicit selection. These local smoke measurements are not paper-facing distributed-performance evidence.

## Architecture Boundaries

Maintain explicit separation among these components.

### Client

The client is responsible for:

- selecting or importing the protected private key;
- collecting the recovery input;
- resolving and canonicalizing cues locally;
- deriving the TPASS password;
- encrypting and decrypting the private key;
- orchestrating enrollment and recovery;
- validating party and cloud responses;
- presenting generic externally visible failures;
- managing backup epochs and re-enrollment.

The client must not persist raw cues, canonical descriptors, cue identifiers, the derived TPASS password, recovered group secrets, or wrapping keys after the operation unless a clearly marked test fixture requires them.

### Cloud Storage

The cloud stores the encrypted backup object and public policy metadata. It must not store recovery-party secret state, raw cues, cue identifiers, a password verifier, recovered group secrets, or wrapping keys.

### Recovery Parties

Each party stores only its own threshold state, backup binding information, durable attempt-control state, and privacy-minimized audit records. A party must not store the encrypted private key, raw cues, canonical descriptors, cue identifiers, recovered group secret, wrapping key, or password verifier.

### Resolver

Resolver behavior must be explicit. Support at least one deterministic local fixture mode for reproduction. Clearly document whether resolver queries leave the client and what metadata a resolver can observe.

### Attempt-Control Layer

Attempt control is a security-critical subsystem, not a logging convenience. It must define:

- the unit that is counted;
- when an attempt is durably committed;
- behavior under concurrent sessions;
- behavior under crashes and retries;
- replay prevention;
- threshold-subset rotation handling;
- rollback detection;
- backup-epoch binding;
- party replacement and counter migration;
- false-lockout recovery;
- malicious-party assumptions;
- denial-of-service implications.

## Threat Model Requirements

Keep the paper, `docs/threat-model.md` once created, implementation tests, and claim-evidence matrix synchronized.

At minimum, define these adversaries:

- cloud-only compromise;
- compromise of fewer than `t` recovery parties;
- combined cloud plus below-threshold party compromise;
- online cue guessing;
- public-information attacker;
- social-knowledge attacker;
- resolver observation or compromise;
- replay attacker;
- cloud rollback and party-state rollback attacker;
- malicious or unavailable recovery parties;
- concurrent-session attacker;
- lockout denial-of-service attacker;
- endpoint compromise;
- compromise of at least `t` parties.

For each adversary, state:

1. capabilities;
2. information obtained;
3. security property claimed;
4. residual risk;
5. implemented experiment, proof, or citation supporting the claim;
6. limitations and out-of-scope cases.

Do not use vague phrases such as "secure against compromise." Name the compromised components and exact property.

## Technical Scope And Primitive Rules

Use established cryptographic libraries and standard primitives wherever possible.

Paper-facing implementation should eventually use:

- a concrete group compatible with the selected TPASS construction or a justified alternate TPASS/PPSS construction;
- cryptographically secure random generation;
- standard AEAD; the current local path uses pinned-library AES-256-GCM with canonical associated data;
- HKDF or another justified standard KDF;
- explicit domain separation;
- canonical, unambiguous serialization;
- authenticated and confidential transport;
- validation of all public parameters and received group elements;
- secure handling and erasure of ephemeral secrets where the platform permits it.

Do not implement custom cryptographic primitives when a suitable reviewed implementation exists. When custom protocol code is unavoidable, keep it isolated, documented, reviewed, and covered by known-answer, property, malformed-input, and interoperability tests.

Never describe any prototype as production-ready or cryptographically audited unless an independent audit has occurred.

## Cue Policy Rules

The reference policy should use exactly three location-person pairs unless an experiment explicitly varies the number of cues. The current prototype uses two synthetic pairs in demos/tests and variable cue counts in benchmarks; this is acceptable only as scaffold behavior and must not be confused with the intended reference policy.

The policy must eventually define:

- cue ordering or order-insensitive serialization;
- map and contact resolver behavior;
- normalization of names and identifiers;
- locale and Unicode handling;
- coordinate precision or geographic representation;
- versioning and migration;
- ambiguity resolution;
- policy drift behavior;
- public metadata stored in the backup;
- information that must remain client-local.

Treat location-person cues conservatively:

- Do not claim long-term memorability without a human-subject study.
- Do not claim high entropy for personal cues.
- Do not present synthetic guessing analysis as human-subject evidence.
- Cite prior human-memory or cue-based authentication work only as motivation unless the result directly applies.

## Evaluation Requirements

All paper-facing claims must be linked to evidence in `docs/claim-evidence-matrix.md`. The following requirements are scoped by `docs/limitations-and-assumptions.md`: features listed there as non-claims or future work are not Cycle 1 implementation/evaluation gates and must instead remain explicit limitations.

Functional evaluation must cover:

- successful enrollment and recovery;
- wrong cues;
- insufficient parties;
- arbitrary valid threshold subsets;
- policy-version mismatch;
- stale or malformed backup objects;
- malformed party responses;
- successful re-enrollment and retirement of old epochs.

Security evaluation must cover:

- cloud snapshot and offline cue-dictionary attack;
- `t-1` party compromise;
- combined cloud plus `t-1` party compromise;
- cloud rollback and object substitution;
- malicious party returning malformed or inconsistent values;
- metadata and resolver leakage analysis;
- cross-epoch state mixing.
- the P5.13 bounded rollback counterexample and its non-proof interpretation.

Focused retry/replay, concurrency, restart, lifecycle, and partial-ledger tests may
be reported only as exact implementation facts. General subset-rotation,
party-state rollback resistance, public lockout prevention, and party replacement
are future work unless the scope is explicitly reopened.

Performance evaluation must measure end-to-end behavior over the scoped same-host research deployment, including:

- enrollment latency;
- successful and failed recovery latency;
- cryptographic computation time;
- network time;
- resolver time;
- bytes transmitted by role;
- cloud backup size;
- per-party persistent storage;
- CPU and memory utilization;
- recovery availability with unavailable parties;
- crash-recovery overhead;
- partial-ledger synchronization overhead if retained in the evaluated path.

Report medians and distributional information such as percentiles or confidence intervals, not only means. Record software versions, hardware, operating systems, VM/container details, run counts, warm-up policy, random seeds, and commit identifiers once version control exists.

## Research And Coding Conventions

- Prefer small, reviewable changes.
- Read relevant design documentation before modifying security-critical code.
- Preserve module boundaries and avoid coupling the cue UI directly to TPASS internals.
- Avoid hidden global state.
- Make failure behavior explicit and testable.
- Use structured logging and never log raw cues, derived cue identifiers, TPASS passwords, wrapping keys, private keys, recovered secrets, or resolver outputs tied to real people.
- Treat test secrets as test-only and clearly label them.
- Do not commit API keys, cloud credentials, private certificates, or human data.
- Do not silently expand paper claims beyond the implementation and evidence.
- If code and paper disagree, flag the inconsistency and update the plan.

## Reproducibility Conventions

- Every paper table and figure should be generated by a versioned script.
- Keep raw outputs immutable after collection.
- Store processed data separately from raw data.
- Record the Git commit, configuration, seed, environment, and timestamp for every experiment once version control exists.
- Prefer command-line experiment runners over manual notebook steps.
- Notebooks may explore data, but final figures and tables must be reproducible non-interactively.
- Add a single documented artifact smoke command and a documented full-evaluation path.

## Testing Conventions

For each implementation change:

- add or update focused unit tests;
- add integration tests for cross-component behavior when relevant;
- add negative tests for malformed and adversarial inputs;
- run formatters, linters, type checks, and tests once those tools exist;
- document any untested assumption.

Security-critical code should include:

- property-based tests where appropriate;
- boundary-value tests;
- serialization round-trip tests;
- concurrency tests;
- crash-consistency tests;
- replay tests;
- rollback tests;
- state-machine invariant checks.

Do not mark a research feature complete merely because local unit tests pass. Completion requires evidence matching the claim.

## Paper Editing Rules

When helping with the manuscript:

- maintain anonymity for double-blind review;
- avoid claims not supported by code, experiments, formal arguments, or cited prior work;
- identify the nearest related systems and explain mechanism-level differences;
- keep the contribution statement synchronized with actual results;
- use exact experiment configurations and sample sizes;
- include limitations prominently;
- avoid calling cues "memorable" as an established result;
- avoid suggesting that online guessing is eliminated;
- avoid describing local counters as a global bound unless the design proves it;
- preserve concise Open Science and Ethical Considerations appendices that satisfy ASIACCS limits;
- verify references and URLs before inclusion;
- remove or qualify toy-backend results before making practicality claims.

## Citation And Source Discipline

- Prefer primary sources: peer-reviewed papers, official specifications, and official documentation.
- Verify bibliographic details before editing `references.bib`.
- Never invent citations, authors, titles, venues, dates, findings, URLs, DOIs, or numerical results.
- Clearly mark inferences as inferences.
- Do not copy substantial text from sources.
- Treat hallucinated references as a submission blocker.

## Documentation Maintenance

As the project progresses:

- update `PLAN.md` whenever a task starts, completes, changes, is blocked, or is replaced;
- update `docs/claim-evidence-matrix.md` once created whenever a paper claim changes;
- update `docs/threat-model.md` once created whenever implementation behavior or assumptions change;
- update protocol/design docs in the same change as security-critical implementation behavior;
- update experiment methodology before collecting final results;
- update paper text only when there is evidence or a clear plan-backed decision;
- keep completed tasks in `PLAN.md` for project history.

## Instructions For Codex

For substantial work, follow this sequence:

1. Read this `AGENTS.md`, relevant subdirectory guidance, `PLAN.md`, and files related to the requested change.
2. Identify the research claim or system property affected by the change.
3. Update `PLAN.md` before or during the work if task status, dependencies, or scope changes.
4. State material assumptions and unresolved design choices in the work summary.
5. Implement the smallest coherent change that advances the plan.
6. Add or update tests, documentation, and reproducibility metadata.
7. Run relevant checks and report exact commands and outcomes.
8. Note security, privacy, reproducibility, and paper-claim implications.
9. Never claim that a test demonstrates more than it actually does.

When asked to design a feature, produce:

- problem statement;
- threat assumptions;
- protocol or state-machine design;
- invariants;
- failure behavior;
- test plan;
- evaluation plan;
- paper implications.

When asked to review code, prioritize:

1. violations of security invariants;
2. offline-oracle creation;
3. secret or cue leakage;
4. replay, rollback, and concurrency faults;
5. attempt-budget bypass;
6. authorization and lockout abuse;
7. cryptographic misuse;
8. reproducibility gaps;
9. performance problems;
10. style issues.

When uncertain whether a change affects a claimed security property, assume that it does and document the uncertainty.

## Definition Of Done For Research Features

A research feature is complete only when all applicable conditions hold:

- design and threat assumptions are documented;
- implementation is complete across affected components;
- failure behavior is explicit;
- tests cover normal, malformed, adversarial, concurrency, and crash cases as appropriate;
- the feature works in the isolated multi-party deployment when deployment is relevant;
- experiment configuration is versioned;
- raw and processed result formats are defined;
- claim-evidence matrix is updated;
- paper text is updated or a paper-update task is recorded;
- limitations are recorded;
- no secrets or sensitive cue data are logged or committed;
- relevant checks pass.

## Decision Principle

Prefer changes that strengthen the paper's central research argument over cosmetic expansion. A smaller system with a clearly defined security contribution, rigorous attack evaluation, and reproducible results is more valuable than a broad interface with weak security semantics.
