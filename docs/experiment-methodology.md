# LOCUS Performance Methodology

> This document remains the frozen historical P7/v2 methodology. D028/P9.1
> assigns the separate, non-collecting D025 managed-system methodology at
> `prototype_final/docs/MANAGED-PERFORMANCE-METHODOLOGY-v1.md`. The two profiles
> cannot be pooled or reinterpreted. D029/P9.2 now supplies the non-collecting
> schemas and processor for that managed methodology; P9.3 remains required
> for a result. D030 supersedes only the uncollected execution plan with the
> affordable `LOCUS-managed-performance-methodology-v2`: 324 total slots over
> 12 projects, descriptive statistics only, resumable block staging, and no
> scalability or suite-advantage interpretation. No v2 execution has occurred;
> the new profile must pass its later execution gates before collection.

Status: the frozen minimum P7.1-P7.3 methodology is unchanged. The original v1
collection is archived; corrected v2 collection is required for the
`LOCUS-reference-backup-v4` / `LOCUS-compose-deployment-v2` cutover.

## Objective And Claim Boundary

The required evaluation characterizes the implemented same-host LOCUS research
prototype. It does not claim Internet-scale performance, independent
administration, production readiness, mobile usability, human memorability,
global rate limiting, or rollback-resistant attempt control.

Only measurements collected after this document is committed, from a clean
labeled worktree, through the versioned runner and retained-evidence contract
may enter the manuscript. Existing local/toy benchmarks and dirty Compose
samples remain development checks.

The archived Cycle 1 v1 collection used clean commit `812cb96`, pseudonymous host
`cycle1-host-a`, blocks `01`--`10`, and seeds `2026072301`--`2026072310`.
All 30 scenario records passed the strict corpus validator. The canonical
processed summary is `experiments/processed/performance-v1/summary.json`; its
SHA-256 digest is
`7c43963619c7e56a4c8716da19b11aeb06ccfa736b750a496caf37ee613cb2f5`.
The generated paper-input manifest binds that summary and all four LaTeX row
files. Because that corpus binds the superseded legacy metadata profile, it is
historical and is not current evidence for v4. A fresh v2 collection from the
clean cutover commit must precede M5.

The corrected v2 collection used clean commit
`12ca8157841088807863e2457b9fe5ee3e069e9f`, pseudonymous host
`cycle1-v2-host-a`, blocks `01`--`10`, and the same preregistered seeds
`2026072301`--`2026072310`. All 30 records passed the strict v2 corpus
validator. The canonical summary is
`experiments/processed/performance-v2/summary.json`, with SHA-256
`462e492795fafdd90a4f39851a612275193603d816f761728afe05e97a470a6b`.
The `LOCUS-performance-paper-inputs-v2` manifest binds that summary and every
generated row file. Anonymous clean-host reproduction remains M5.

The minimum paper-facing questions are:

1. What is the client-observed cost of enrollment and successful native
   end-to-end recovery across the implemented resolver, cloud, authorization,
   TPASS, and decryption boundaries?
2. Where is recovery time spent at those implemented phases?
3. How does a wrong recovery input change client-observed cost while preserving
   the generic failure boundary?
4. What is the recovery cost and success behavior when one TPASS-capable party
   is unavailable and the fixed alternate subset is used?
5. How many application bytes and persistent bytes does the implemented path
   use by role?

## Frozen Deployment Configuration

The required configuration is the default digest-pinned Linux Compose
deployment on one labeled host:

- five separately identified authenticated recovery-party services;
- native Rust/Ristretto255 TPASS with three TPASS-capable parties, threshold
  two, baseline subset `[1,3]`, and alternate subset `[2,3]`;
- the implemented 4-of-5 authorization profile, reported only as local partial
  attempt-control instrumentation;
- one deterministic exactly-three-pair synthetic resolver fixture;
- one digest-pinned SeaweedFS S3-compatible service;
- AES-256-GCM backup encryption and HKDF-SHA-256 wrapping-key derivation;
- no host ports, three internal networks, disjoint persistent volumes, non-root
  role services, read-only roots, and zero container core-file limits; and
- the same pinned source image and dependency locks for every scenario.

The corrected runner builds `locus-reference:performance-v2` once before each
block under the fixed Compose build identity `locus-performance-image-v2`, then passes that
single inspected image identifier into all three fresh scenario projects. A
disposable scenario project must never rebuild the image under its own project
label because Compose labels would change the image identifier and invalidate
cross-record provenance.

This single configuration is the required end-to-end result. Local native core
measurements for `(3,5)` or `(5,9)` may appear only as clearly labeled
microbenchmarks if time permits; they must not be presented as distributed
deployment results or used to claim scalability.

## Scenario Matrix

Collection consists of ten blocks. Each block runs the following three
scenarios as fresh, uniquely named disposable Compose projects. A recorded
64-bit orchestration seed determines scenario order within each block through
`LOCUS/performance-scenario-order/v1`, which sorts the fixed identifiers by
their domain-separated seed-bound SHA-256 values. Cryptographic randomness
remains operating-system generated.

The paper corpus fixes the orchestration seed for block `01` through `10` to
`2026072301` through `2026072310`, respectively. This schedule is committed
before collection and is independent of observed timings or outcomes.

| ID | Setup after healthy startup | Unmeasured warm-up | Measured operations | Expected outcome |
| --- | --- | --- | --- | --- |
| `enroll-recover-success-v1` | Fresh provisioned deployment | One correct recovery through `[1,3]` | Three correct recoveries through `[1,3]` | Three successful recoveries |
| `recover-wrong-input-v1` | Fresh provisioned deployment | One correct recovery through `[1,3]` | Three fixed synthetic wrong-input recoveries through `[1,3]` | Three generic client rejections, each counted once |
| `recover-one-party-unavailable-v1` | Fresh provisioned deployment; stop party 1 after warm-up | One correct recovery through `[1,3]` | Three correct recoveries through fixed subset `[2,3]` | Three successful recoveries with party 1 stopped |

The configured four-attempt budget permits exactly one warm-up plus three
measurements per fresh deployment. Ten blocks therefore provide 30 measured
recovery samples per scenario. Provisioning/enrollment is measured once in
every fresh project, yielding 30 enrollment samples under the same deployment
configuration. Image build/pull, container creation, health waiting, and
cleanup are recorded as orchestration duration but excluded from protocol
latency.

Default restart, stale-object, cloud-unavailable, malformed-input, and
cross-epoch paths remain functional/security tests unless a later version of
this methodology explicitly promotes them to quantitative scenarios. No
concurrency, throughput, geographic, VM-to-VM, malicious-slow-party, CPU, or
memory result is required for the minimum Cycle 1 claim.

## Metrics

Every measured operation records privacy-safe numeric or fixed-label fields
only.

### Latency

Use a monotonic clock and record milliseconds for:

- total networkless client enrollment/provisioning logic, excluding
  image/container setup and cloud publication;
- total client-observed recovery;
- resolver request and canonicalization;
- exact cloud-object fetch and validation;
- authorization and freshness collection;
- native TPASS commitment phase;
- native TPASS response/aggregation/final digest validation; and
- wrapping-key derivation plus AEAD decryption.

Phase intervals must be non-overlapping and their declared covered total must
be checked against end-to-end latency. Any intentionally unclassified client
overhead is reported as a derived remainder rather than silently assigned.
Server clocks are not combined with the client clock.

The warm-up publishes the immutable backup object before measured recovery.
Measured recoveries perform the bound cloud fetch only. The enrollment metric
therefore characterizes local provisioning and cryptographic setup, not remote
backup-upload latency; the manuscript must preserve that limitation.

### Bytes And Storage

Record application-message body bytes sent and received by logical role for
resolver, cloud, coordinator/authorization, and TPASS commitment/response
traffic. State explicitly that TLS, TCP/IP, container-network, and Docker
overhead are excluded.

Record:

- canonical cloud backup-object bytes;
- aggregate persistent bytes per party after provisioning;
- aggregate persistent bytes per party after the scenario; and
- aggregate client bundle bytes.

Storage output contains role labels and counts only, never paths, filenames,
database rows, identifiers, ciphertext, keys, or other stored content.

### Correctness And Boundary Checks

Each sample records only:

- fixed scenario/outcome category;
- selected party identifiers;
- attempt count before and after;
- whether the expected generic success/rejection occurred; and
- whether output scanning and cleanup passed.

Wrong-input samples are valid expected outcomes, not failed measurements.
Candidate values and per-candidate diagnostic causes are never retained.

## Warm-Up, Host Control, And Run Order

Before collection:

1. use a clean committed worktree and pseudonymous host label;
2. record OS, CPU class, Python, Docker, Compose, dependency locks, image
   identifier, and configuration through existing provenance;
3. ensure no unrelated user-started containers are running;
4. use external power and a stable host power mode;
5. build/pull the pinned image before the measured block sequence; and
6. perform one complete unretained development block as runner validation.

The one per-project correct recovery is the declared warm-up and is never mixed
with measured samples. Blocks are interleaved by the recorded orchestration
seed to reduce monotonic time/thermal bias. The runner must not sleep to shape
results or retry a protocol outcome invisibly.

## Failure And Exclusion Rules

No latency outlier is removed.

A project is invalid only for a pre-measurement or measurement-infrastructure
failure such as operator interruption, host suspend/reboot/update, loss of the
Docker engine, provenance/schema/output-safety failure, or failure to create or
remove the exact disposable project. The runner emits a separate privacy-safe
invalid-run category when possible; it never retains unsafe diagnostics.

Expected protocol outcomes, slow operations, party unavailability in its named
scenario, and wrong-input rejection remain included. A failed block is rerun
only under a new immutable run identifier; the original safe record is not
overwritten. The paper reports the count and categories of invalid blocks.

## Statistical Processing

For each scenario and latency metric, report:

- sample count;
- median;
- 25th and 75th percentiles;
- 5th and 95th percentiles; and
- minimum and maximum.

Means may appear only as secondary descriptive values. A deterministic
processing script computes a 95% percentile-bootstrap confidence interval for
the median. P7.15 fixes the default resampling seed to `20260723`, the resample
count to 10,000, and each draw to
`SHA-256("LOCUS/performance-bootstrap/v1\0" || uint64be(seed) || metric-label ||
"\0" || uint64be(replicate) || uint64be(draw))[0:8] mod n`. Quantiles use the
linear Type 7 rule. The seed governs resampling only, never protocol randomness.
With 30 samples per scenario, tail values are descriptive and must not be called
service-level objectives or production tail guarantees.

Bytes and deterministic object sizes are reported as exact counts, with ranges
where mutable state changes across attempts. Every table and figure is generated
from validated raw files; manual transcription is prohibited.

## Raw, Processed, And Paper Outputs

P7.17 must add one exact `LOCUS-compose-performance-result-v1` schema and
validator before collection. It must fit inside
`LOCUS-compose-profile-evidence-v1` and bind:

- scenario/block/run identifiers and orchestration seed;
- the frozen configuration above;
- warm-up and measured sample counts;
- phase latency arrays;
- role byte counts;
- aggregate storage counts;
- attempt/outcome labels; and
- output-scan and cleanup status.

The record also binds the seed-derived scenario position, per-sample
measurement index, Docker Engine and Compose versions, the locally built
reference-image content identifier, and the digest-pinned S3 image identifier.

One immutable raw JSON file is written below
`experiments/raw/performance-v2/<block>/<scenario>.json`. Files contain no
arbitrary logs or traces. `experiments/processed/` contains only deterministic
derived series/tables, and `paper/generated/` contains only generated LaTeX
rows or figures. Processing fails if a file has the wrong version,
configuration, commit, host label, lock hashes, sample count, scenario order,
trace policy, or result binding.

P7.15 implements the exact
`LOCUS-performance-processed-v2` contract in
`docs/schemas/performance-processed-v2.schema.json`. It accepts only ten
directories named `01` through `10`, each containing exactly the three
canonical evidence files. It rejects symlinks, extra or missing entries,
non-ASCII/noncanonical/duplicate-member JSON, mixed experiment identifiers,
commits, hosts, lock hashes or runtime identities, incomplete seed-derived
positions, unsafe output, and altered derived statistics. The output embeds an
ordered SHA-256 manifest of all 30 inputs and preserves the 30-sample latency
and byte series plus ten per-project orchestration/storage observations.

One unretained validation block is:

```powershell
uv run --frozen python tasks.py deployment-performance-block `
  --block 1 --seed 20260723 --evidence-class development
```

After an owner-created clean commit and assignment of a pseudonymous host
label, one retained block uses:

```powershell
uv run --frozen python tasks.py deployment-performance-block `
  --block 1 --seed <uint64> --evidence-class paper `
  --host-id <pseudonymous-id> `
  --out-dir experiments/raw/performance-v2/01
```

The writer is exclusive: an existing raw file is never overwritten.
Retained raw JSON is ignored by Git during multi-file acquisition so every
record sees and binds the same clean source commit. After all attack and
performance records validate, only their exact paths are force-added for the
evidence-packaging commit.

After all ten retained blocks exist, deterministic processing is:

```powershell
uv run --frozen python tasks.py process-performance
```

The processed writer is also exclusive. A changed processing seed or resample
count therefore requires a new output path; paper generation must consume one
explicitly selected validated processed artifact rather than silently
overwriting it.

## Generated Manuscript Inputs

P7.16 defines `LOCUS-performance-paper-inputs-v2` and the normative
`docs/schemas/performance-paper-inputs-v2.schema.json`. Generation accepts only
canonical `LOCUS-performance-processed-v2` bytes from the fixed processed
directory. It emits four ASCII, newline-terminated LaTeX row fragments:

- enrollment and scenario-total latency with count, median, interquartile
  range, descriptive 5th--95th percentile range, and the deterministic median
  interval;
- all declared non-total phase medians and interquartile ranges by scenario;
- sent and received application-body byte medians and ranges by logical role;
  and
- cloud-object, client-bundle, and each party's before/after persistent byte
  medians and ranges by scenario.

The command is:

```powershell
uv run --frozen python tasks.py generate-performance-paper
```

Its canonical manifest binds the processed source path/digest, experiment,
collection commit, pseudonymous host, processing configuration, output paths,
and every output digest. Fixed labels are generated by code rather than read
from experiment text. Identical regeneration is idempotent; a changed bundle
requires explicit `--replace`. Tests use generated fixtures only. Fixture rows
are never retained, copied into the manuscript, or interpreted as evidence.

The row format remains `LOCUS-performance-latex-rows-v1` and intentionally
emits no plot. Four compact tables preserve exact
values and the distinctions among scenarios, phases, bytes, and storage more
clearly within the page budget. A future figure requires a version bump and a
documented interpretation benefit.

## Interpretation

Passing results support only a host-specific same-host prototype-cost claim and
the exact tested one-party-unavailability behavior. They do not establish
independent administration, wide-area performance, scalability, production
availability, constant-time behavior, resistance to malicious scheduling, or
the security of the partial attempt ledger.
