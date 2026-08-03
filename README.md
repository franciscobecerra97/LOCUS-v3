# LOCUS Improvement Project

This directory is a portable seed for the integrated, long-horizon continuation
of LOCUS. It carries forward the implementation, tests, deterministic vectors,
deployment fixtures, pinned build environments, active technical
documentation, manuscript source, rendered review snapshot, retained versioned
evidence, generated manuscript inputs, and artifact tooling.

Imported material remains bound to its original identifiers and provenance. No
implementation, evidence, or planning change automatically authorizes a
manuscript change. Before every manuscript edit, describe the exact proposed
delta and obtain the owner's explicit approval; the owner may approve or skip
each change.

The objective is to turn the compact LOCUS prototype into a complete reference
recovery system while preserving the existing thesis:

> LOCUS combines a versioned structured-input boundary with TPASS and separated
> encrypted backup storage so that the cloud and fewer than the TPASS threshold
> do not obtain an offline cue-testing predicate.

This is the working repository for both the reference system and its
owner-approved manuscript revisions.

## Start here

Read these files in order:

1. `AGENTS.md` — authoritative instructions for Codex and contributors.
2. `PROJECT-CHARTER.md` — objective, thesis, scope, and non-goals.
3. `BASELINE.md` — exact upstream status at the time of extraction.
4. `PLAN.md` — ordered development roadmap and acceptance gates.
5. `DECISIONS.md` — owner decisions that must be made before affected work.
6. `PROTOCOL-INVARIANTS.md` and `EVIDENCE-POLICY.md` — technical and
   evidentiary constraints.

`AGENT.md` is included because it was explicitly requested. Codex convention
uses the plural filename `AGENTS.md`, so that file is authoritative.

`PORTABLE-CONTENTS.json` records the path, size, and SHA-256 digest of every
other file in the seed. The manifest intentionally excludes its own digest.

## Creating an independent project

Copy this entire directory to its intended location, then initialize a new
repository:

```console
git init
git add .
git status --short --ignored
git diff --cached --stat
git commit -m "Import LOCUS improvement baseline"
uv sync --frozen
uv run --frozen python tasks.py check
```

The initial commit is important because the repository-hygiene and evidence
tools bind results to source-control state.

Docker is required only for the live S3-compatible and complete deployment
profiles. External cloud, identity-provider, or independently operated party
profiles must use synthetic data and separately authorized disposable
resources.

## Active source layout

| Path | Purpose |
| --- | --- |
| `prototype/` | Python orchestration, storage, services, tests, and evidence tooling |
| `appss-core/` | Separate Rust aPPSS/OPRF/GF(2¹²⁸) core and public fixed vector |
| `tpass-core/` | Rust/Ristretto255 TPASS implementation and fixed vectors |
| `tpass-python/` | Narrow PyO3 binding for the independent Rust suites |
| `deploy/` | Existing isolated same-host deployment and synthetic fixtures |
| `docs/` | Active baseline documentation, target-design drafts, schemas, and provenance snapshots |
| `experiments/` | Frozen v1/v2 records plus separately versioned future evidence |
| `paper/` | Authoritative manuscript, bibliography, build inputs, generated rows, and review PDF |
| `artifact/` | Active installation, evaluation, packaging, and release planning |
| `dist/` | Sealed verified v1 anonymous-artifact release and manifest |

## Immediate development priority

The first implementation milestone is not the graphical interface or a real
cloud provider. It is:

1. a semantics-preserving `CuePolicy` interface;
2. an authenticated, versioned `RecoveryDescriptor`;
3. an immutable bounded per-epoch recovery bundle plus a separately
   authenticated mutable current pointer;
4. an explicit account-scoped bootstrap and trust model;
5. a proof-key-bound application storage gateway over the common S3 contract;
6. authenticated enrollment transport;
7. destruction or inaccessibility of the enrollment client state;
8. recovery by an isolated replacement client;
9. exact verification of the original private-key identity; and
10. new descriptor, bundle, gateway, and clean-client security evidence.

The frozen composite CuePolicy will then be joined by separate
quantized-coordinate, canonical-phone, and canonical-email set policies. The
UI, supplemental AWS S3 profile, multi-host deployment, and broader
lifecycle work follow the local, evidence-backed foundation.

## Paper and evidence workflow

The retained v2 corpus is baseline evidence only for the exact frozen profile
and provenance it records. It is not evidence for changed CuePolicy,
descriptor, admission, topology, provider, or lifecycle semantics. Raw records
are immutable; deterministic verification and processing may be rerun. Changed
profiles use new identifiers and paths.

Prototype work reaches the manuscript through an explicit gate:

1. implement and test an owner-approved change;
2. collect and close evidence for its exact profile;
3. present the exact proposed manuscript delta to the owner;
4. edit `paper/` only after approval;
5. synchronize claims, limitations, technical documentation, generated inputs,
   and artifact instructions; and
6. rebuild and visually inspect the review PDF.

## Safety

Use generated private keys, fictional cues, generated credentials, test doubles,
and isolated disposable services only. Do not use this project with real private
keys, personal recovery information, production accounts, or external targets.

## Licensing

Project-authored software and configuration are licensed under Apache License
2.0. Project-authored documentation and aggregate experiment material are
licensed under Creative Commons Attribution 4.0 International. See `LICENSE`,
`LICENSE-DOCUMENTATION.md`, and `LICENSES.md`. Those notices do not
automatically license the manuscript or third-party style material.
