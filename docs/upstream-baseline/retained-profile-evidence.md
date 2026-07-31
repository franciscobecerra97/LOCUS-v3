# LOCUS Retained Profile Evidence Contract

Status: frozen P1.11 retained-output contract, version 1; Cycle 1 P6.2-P6.4
and P7 collection completed 2026-07-23.

## Purpose

Paper-facing Compose attack, benchmark, and performance runs retain only the exact
aggregate result and its host-side provenance. They do not retain container
logs, snapshot bytes, database files, credentials, candidate values,
per-candidate outcomes, packet captures, core dumps, exception text, or
arbitrary process traces.

The current retained set contains exactly three attack records and 30
performance records, all bound to clean commit `812cb96`, pseudonymous host
`cycle1-host-a`, and the frozen trace policy. A post-collection audit found one
performance image ID and no remaining LOCUS containers, volumes, or networks.

The retained object is `LOCUS-compose-profile-evidence-v1`. Its normative JSON
shape is `docs/schemas/profile-evidence-v1.schema.json`; the stricter executable
validator and writer are in `prototype/locus/profile_evidence.py`.

## Exact Record

The record contains exactly:

- the fixed artifact version;
- one validated `LOCUS-experiment-metadata-v1` object;
- either one registry-bound `LOCUS-attack-report-v1`, one exact
  `LOCUS-compose-benchmark-v1`, or one exact
  `LOCUS-compose-performance-result-v1` result; and
- one fixed `LOCUS-profile-trace-policy-v1` object.

The executable validator binds an attack metadata configuration to its exact
scenario identifier. It binds benchmark metadata to the reported run count,
fixed selected parties, threshold, and topology. The complete record passes
the recursive output-safety validator before serialization. Performance
metadata is additionally bound to block, orchestration seed and its versioned
scenario position, scenario identifier, topology, and orchestrator randomness
record.

## Trace And Log Policy

Every service in the main Compose deployment, including the pinned local S3
service, has a zero soft and hard core-file limit. The resolved service graph
must contain that limit, and the default live deployment inspection verifies it
for recovery parties, the resolver, and S3. Containers drop all capabilities
unless an exact bootstrap or S3 capability is declared, use
`no-new-privileges`, publish no host ports, and do not collect packet captures
or debugger traces.

The task runner obtains service logs only to scan the completed disposable run
for static prohibited markers and per-run synthetic cue/credential canaries.
It does not place those logs in the retained record. Logs are discarded when
the exact generated Compose project is removed. A detected prohibited category
fails the run and reports only category labels.

This policy governs repository-created Compose evidence. It does not inspect or
control a privileged host, hypervisor, container-engine internals, host crash
collector, deleted storage blocks, or independently configured external
observability. Such artifacts are excluded from the evidence boundary and must
not be supplied to the artifact or treated as clean retained output.

## Immutable Publication

The writer:

1. validates the complete object and fixed trace policy;
2. serializes one canonical ASCII JSON line;
3. requires the metadata path to equal the resolved repository-relative output;
4. creates the `.json` file exclusively without overwrite;
5. flushes and synchronizes the file;
6. rereads the exact bytes; and
7. reparses, revalidates, and requires byte-identical canonical serialization.

For `paper` evidence, the existing metadata gate additionally requires a clean
Git worktree, labeled pseudonymous host, warning-free metadata, and a retained
path below `experiments/raw/`.

Raw files are append-only evidence. They are never edited or promoted from a
development console transcript. A failed or superseded run receives a new file
identifier; no tool overwrites the original.

## P6.2-P6.4 Collection Boundary

The cloud, one-party, and combined snapshot volumes are disposable test inputs,
not retained raw evidence. Only their already validated aggregate attack report
and provenance may be written below `experiments/raw/`. The first 2026-07-22 and
2026-07-23 runs remain dirty, unlabeled, unretained development checks and
cannot be cited as final paper results.

Final collection must use a clean committed worktree, one pseudonymous labeled
host, unique immutable output paths, successful prohibited-output scanning, and
complete Compose cleanup. Independent reproduction remains a later P9 gate.

The archived Cycle 1 v1 collection uses pseudonymous label `cycle1-host-a`,
`experiments/raw/attacks-v1/<scenario>.json` for the exact P6.2-P6.4 reports,
and `experiments/raw/performance-v1/{01..10}/<scenario>.json` for P7. Raw JSON
was ignored during acquisition so all 33 records bind clean source commit
`812cb96`. It remains immutable historical evidence for the old metadata
profile. The corrected cutover uses new `attacks-v2` and `performance-v2`
paths, a new clean commit binding, and no cross-version promotion.

The corrected collection is complete under pseudonymous host
`cycle1-v2-host-a`. Its three `attacks-v2` records and 30 `performance-v2`
records all bind clean commit
`12ca8157841088807863e2457b9fe5ee3e069e9f`, report no dirty provenance or
warnings, pass their output-safety and cleanup requirements, and use matching
`compose-attack-v2` or `compose-performance-v2` identifiers. The processed v2
summary digest is
`462e492795fafdd90a4f39851a612275193603d816f761728afe05e97a470a6b`.
