# LOCUS Experiment Metadata Contract

Status: P1.10 implemented contract, version 1, 2026-07-21.

## Problem statement

Every measurement or attack result must identify the exact code, dependency
locks, host class, configuration, randomness policy, time interval, and retained
raw output that produced it. Console output without provenance may be used for
development smoke testing but cannot become paper evidence.

## Versioned record

`LOCUS-experiment-metadata-v1` is embedded in every benchmark, performance, or
attack result. Its
normative machine-readable shape is
`docs/schemas/experiment-metadata-v1.schema.json`; the stricter executable
validator is `prototype/locus/experiment_metadata.py`.

The record contains:

- a stable experiment identifier, profile, and `development` or `paper`
  evidence class;
- UTC start and finish timestamps;
- the exact Git commit and whether the complete worktree is dirty;
- SHA-256 hashes of `uv.lock` and both Cargo lockfiles;
- a user-supplied pseudonymous host identifier plus OS, release, architecture,
  processor class, and Python version, but never a hostname or username;
- the complete JSON experiment configuration;
- either unseeded operating-system CSPRNG provenance or a recorded 64-bit seed
  for deterministic orchestration only;
- a repository-relative retained raw-output path, or an explicit unretained
  development result; and
- canonical warnings for dirty, unlabeled, or unretained development runs.

Compose profile results embed this metadata inside the stricter
`LOCUS-compose-profile-evidence-v1` record defined by
`docs/retained-profile-evidence.md`. That wrapper binds metadata to the exact
attack scenario, benchmark configuration, or performance block/scenario/order,
fixes the trace/log policy, and is the only permitted retained raw format for
those profiles.

## Paper-evidence gate

A `paper` record fails closed unless:

1. the Git worktree is clean;
2. a pseudonymous host identifier is supplied;
3. output is retained below `experiments/raw/`;
4. all dependency lockfiles exist and hash correctly;
5. timestamps, identifiers, configuration, and randomness are canonical; and
6. the record contains no warning.

This gate does not by itself make a run scientifically adequate. Phase 7 must
still freeze scenarios, warm-up, repetitions, metrics, sample sizes, exclusion
rules, and statistical processing before paper-facing collection.

## Raw and processed data lifecycle

- `experiments/raw/` is append-only after collection and stores the original
  machine-readable aggregate profile evidence with embedded metadata.
- Snapshot volumes, databases, credentials, packet captures, core dumps,
  arbitrary service logs, exception traces, and per-candidate outcomes are
  excluded from retained raw output.
- `experiments/processed/` contains reproducibly derived tables/series.
- `paper/generated/` contains only script-generated manuscript inputs.
- Development smoke output may remain unretained and must carry the corresponding
  warning.
- Paths are repository-relative so no username, home directory, or machine path
  enters an artifact.

Cryptographic randomness remains operating-system generated and is never made
deterministic merely to reproduce a benchmark. A recorded orchestration seed may
control schedules, fault choices, or synthetic workloads; it must not replace
protocol CSPRNG use.
