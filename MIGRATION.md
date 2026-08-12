# LOCUS-v3 to LOCUS-v4 Migration Guide

## Purpose and authority

This document defines a clean, source-only migration from LOCUS-v3 to a new
independent LOCUS-v4 repository. It is a migration plan and copy checklist. It
does not authorize a protocol change, an evidence-profile change, retained
P8/P9 collection, or a manuscript edit.

The intended LOCUS-v4 starting point contains:

- the complete self-contained `prototype_final/` implementation selected by
  D024 and updated by D025/P7.7;
- the complete manuscript workspace under `paper/`;
- enough governance, architecture, version, evidence, review, and provenance
  context to continue P8, P9, and P10 in the required order;
- the current immutable baseline evidence needed to understand and reproduce
  the existing manuscript boundary; and
- no second active implementation, generated runtime state, build cache,
  credential, or inherited Git history.

The audited pre-migration P7.7 source commit is:

```text
bf47675772b35039a312e76ba0fd7b49eddac49c
```

That commit is clean and has subject:

```text
P7.7 Replace CLI-selected clients with a Manager-controlled workflow
```

`MIGRATION.md` was created after that commit. Therefore, the actual migration
source should be a new clean LOCUS-v3 commit that includes this file. Record
that new commit in LOCUS-v4 before doing any P8 work.

## Migration rule

Copy source-controlled files only. Do not copy a directory by selecting every
visible filesystem entry, because `prototype_final/` currently may contain
large ignored environments, caches, Rust targets, and native build products.

Preserve every copied relative path. In particular, keep the active
implementation named `prototype_final/`; do not rename it to `prototype/` or
move its contents to the LOCUS-v4 root. Its executors, build context, schemas,
tests, and documentation rely on that self-contained boundary.

Do not copy the LOCUS-v3 `.git/` directory. LOCUS-v4 must receive a new Git
repository and its own initial migration commit.

## Required LOCUS-v4 contents

### 1. Root governance and project context

Copy these files to the LOCUS-v4 root:

```text
.dockerignore
.gitattributes
.gitignore
.python-version
AGENT.md
AGENTS.md
BASELINE.md
CLAIM-EVIDENCE-MATRIX.md
DECISIONS.md
EVIDENCE-POLICY.md
LICENSE
LICENSE-DOCUMENTATION.md
LICENSES.md
MANUSCRIPT-BOUNDARY.md
MIGRATION.md
PLAN.md
PROJECT-CHARTER.md
PROTOCOL-INVARIANTS.md
README.md
SOURCE-PROVENANCE.md
THESIS-GUARDRAILS.md
VERSION-REGISTRY.md
rust-toolchain.toml
```

These files jointly preserve the thesis, frozen and Assigned identifier
boundaries, D001--D025 decisions, P7.7 completion record, evidence rules,
manuscript approval gate, active claims, and the P8--P10 sequence.

Do **not** copy the root LOCUS-v3 `tasks.py`, `pyproject.toml`, or `uv.lock` into
the minimal LOCUS-v4 root. They belong to the broad historical/component
executor and would reintroduce a second active Python project. LOCUS-v4 uses
the corresponding files inside `prototype_final/`.

### 2. Active implementation

Copy the complete source-controlled `prototype_final/` tree, including its
hidden `.dockerignore`:

```text
prototype_final/
  .dockerignore
  README.md
  LICENSE
  LICENSE-DOCUMENTATION.md
  LICENSES.md
  pyproject.toml
  uv.lock
  tasks.py
  appss-core/
  deploy/
  docs/
  locus/
  tests/
  tpass-core/
  tpass-python/
```

At the audited commit this tree contains 102 source-controlled files. It is
dependency-complete and must not import runtime source or deployment assets
from outside `prototype_final/`.

Do not copy any of these entries if they exist inside the tree:

```text
prototype_final/.venv/
prototype_final/.uv-cache/
prototype_final/.mypy_cache/
prototype_final/.ruff_cache/
prototype_final/.pytest_cache/
prototype_final/__pycache__/
prototype_final/**/__pycache__/
prototype_final/**/target/
prototype_final/**/*.pyc
prototype_final/**/*.pyd
prototype_final/**/*.pdb
prototype_final/**/*.so
```

Do not copy `prototype_final.zip`. It is not the active source boundary and is
not a substitute for a source-controlled migration.

### 3. Manuscript workspace

Copy the complete source-controlled `paper/` tree:

```text
paper/
  AGENTS.md
  README.md
  main.tex
  main.pdf
  references.bib
  acmart.cls
  ACM-Reference-Format.bst
  acmnumeric.bbx
  acmnumeric.cbx
  popets.sty
  cc-by-4.pdf
  generated/
  related_work.tex
```

At the audited commit this tree contains 27 source-controlled files.
`paper/main.tex` is authoritative and `paper/main.pdf` is the intentional
review snapshot. `related_work.tex`, `generated/performance-v1/`, and the
legacy generated benchmark/guessing rows are historical even though they are
preserved. Do not promote or include them without reconciliation and owner
approval.

Do not copy LaTeX build byproducts:

```text
paper/*.aux
paper/*.bbl
paper/*.blg
paper/*.fdb_latexmk
paper/*.fls
paper/*.log
paper/*.out
paper/*.synctex.gz
paper/*.toc
paper/_build/
```

No manuscript narrative, table, figure, claim, limitation, or reference may
be changed merely because the repository was migrated. Follow
`MANUSCRIPT-BOUNDARY.md` and `paper/AGENTS.md`.

### 4. Active technical and review documentation

Copy the complete source-controlled `docs/` tree:

```text
docs/*.md
docs/*.json
docs/schemas/**
docs/upstream-baseline/**
```

At the audited commit this tree contains 129 source-controlled files. The
top-level files and `docs/schemas/` are active technical, threat-model,
interface, mapping, methodology, registry, and schema context.
`docs/upstream-baseline/` is a read-only provenance snapshot; preserve it but
never treat it as active authority or edit it.

Copying the complete tree avoids losing required P8/P10 inputs such as:

- `docs/INFORMATION-FLOW.md`;
- `docs/INTEGRATED-REFERENCE-SYSTEM.md`;
- `docs/SYSTEM-INTERFACES.md`;
- `docs/TARGET-ARCHITECTURE.md`;
- `docs/CLIENT-API.md` and `docs/RESEARCH-UI.md`;
- `docs/RECOVERY-DESCRIPTOR.md`;
- `docs/APPSS-PROFILE.md` and `docs/APPSS-WIRE-FORMAT.md`;
- `docs/P5A7-INTERNAL-MAPPING-ASSESSMENT.md`;
- `docs/RECOVERY-SUITE-DEVIATIONS.md` and
  `docs/RECOVERY-SUITE-MAPPING-REVIEW.md`;
- `docs/threat-model.md`, `docs/limitations-and-assumptions.md`, and both
  claim/evidence views;
- `docs/experiment-methodology.md`, `docs/experiment-metadata.md`, and
  `docs/output-safety.md`; and
- the protected registry and schema set.

### 5. Continuous integration

Copy:

```text
.github/workflows/ci.yml
```

The current workflow already installs from `prototype_final/`, runs its frozen
quality gate on Linux and Windows, and runs the disposable integrated smoke on
Linux. It does not yet build or visually verify the manuscript and does not
collect retained P8/P9 evidence.

### 6. Artifact planning context

Copy the complete source-controlled `artifact/` tree:

```text
artifact/
  README.md
  INSTALL.md
  EVALUATION.md
  MANIFEST.md
  RELEASE-CHECKLIST.md
  package-v2/
```

These ten files preserve reviewer-workflow and anonymity constraints needed to
design P10.3. They describe earlier artifact profiles and are planning/
compatibility context, not the new P10 artifact. P10.3 must allocate a new
artifact identifier, allowlist, manifest, and clean-host acceptance path.

### 7. Immutable baseline evidence used by the existing manuscript

Copy the complete source-controlled `experiments/` tree:

```text
experiments/
  README.md
  raw/
  processed/
```

At the audited commit this is 71 small source-controlled files. Preserve all
v1/v2 bytes to keep the current manuscript and provenance statements
internally consistent. V1 is superseded history and v2 is retained baseline
evidence for its exact frozen profile only. Neither may be mixed with,
overwritten by, or relabeled as D025/P8/P9 evidence.

The minimal LOCUS-v4 repository deliberately does not include the legacy root
processor that originally regenerated these historical rows. The copied
`paper/generated/` bytes and manifests remain sufficient to build the current
paper. If historical byte-for-byte regeneration is required, perform it from
LOCUS-v3 or its sealed historical artifact rather than making the old root
runtime a second LOCUS-v4 implementation. New P9 processors belong inside the
active LOCUS-v4 source/evidence boundary and require new identifiers and paths.

## Recommended optional provenance files

The following are not needed to implement P8--P10, but may be copied into a
clearly named read-only provenance archive if long-term audit continuity is
desired:

```text
PORTABILITY-CHECKLIST.md
PORTABLE-CONTENTS.json
dist/LOCUS-anonymous-artifact-v1.zip
dist/LOCUS-anonymous-artifact-v1.manifest.json
dist/README.md
```

Do not place `PORTABLE-CONTENTS.json` or `PORTABILITY-CHECKLIST.md` at the
LOCUS-v4 root as if they described the new repository. They describe the
earlier LOCUS-v3 seed and include legacy paths that the clean migration omits.
LOCUS-v4 needs newly generated equivalents after its copy set is final.

## Files and directories that must not be copied

Do not copy:

```text
.git/
.venv/
.uv-cache/
.mypy_cache/
.ruff_cache/
.pytest_cache/
__pycache__/
**/__pycache__/
**/target/
tmp/
extra/
prototype_final.zip
*.pyc
*.pyd
*.pdb
*.so
*.pem
*.key
*.p12
*.pfx
*.sqlite
*.sqlite3
*.db
*.log
*.trace
*.pcap
.env
.env.*
credentials/
secrets/
```

Also omit these legacy root implementation trees from the clean LOCUS-v4
working root:

```text
prototype/
deploy/
appss-core/
tpass-core/
tpass-python/
tasks.py
pyproject.toml
uv.lock
```

Their necessary active counterparts already exist inside `prototype_final/`.
If historical component reproduction is ever needed, use the preserved
LOCUS-v3 repository rather than silently restoring these paths into LOCUS-v4.

## Manual migration process

1. In LOCUS-v3, ensure the working tree is clean and create a commit containing
   this `MIGRATION.md`. Record that exact commit hash.
2. Stop any manually running LOCUS project through the Manager UI. Generated
   Docker state is not migration input.
3. Create `LOCUS-v4/` outside the LOCUS-v3 repository. Do not nest it under
   LOCUS-v3 and do not copy `.git/`.
4. Copy the required root files and directory trees listed above, preserving
   paths and excluding ignored/generated entries.
5. Compare source and destination file counts and hashes before editing the
   destination.
6. Initialize a new Git repository in LOCUS-v4. Review Git identity and remote
   visibility before any push.
7. Create a LOCUS-v4 portability manifest containing every migrated path,
   byte length, and SHA-256 digest. The manifest must identify the exact
   LOCUS-v3 source commit and exclude itself from its own digest list.
8. Update `SOURCE-PROVENANCE.md` in LOCUS-v4 with the v3 source commit, copy
   date, copy policy, exclusions, LOCUS-v4 initial commit, branch, and remote.
9. Replace the v3-specific portability checklist with a LOCUS-v4 checklist
   matching this smaller active boundary.
10. Reconcile the LOCUS-v4 `README.md`, `AGENT.md`, and `AGENTS.md` so they do
    not imply that omitted legacy root implementations are present. Preserve
    their historical meanings and frozen boundaries; do not reinterpret an
    identifier while normalizing repository-layout language.
11. Run the validation sequence below before starting P8.1.
12. Commit the verified migration as the LOCUS-v4 baseline. Begin P8.1 only
    from that clean commit.

## Post-copy validation

### Repository boundary

Confirm:

- LOCUS-v4 has its own `.git/` and is not inside LOCUS-v3;
- no ignored cache, environment, credential, database, Docker state, trace, or
  LaTeX byproduct was copied;
- only `prototype_final/` is an active executable implementation;
- `git status --short --ignored` has the expected result; and
- the migration manifest matches every copied byte.

### Active prototype

Use a fresh shell that is not carrying LOCUS-v3's `VIRTUAL_ENV`:

```console
cd prototype_final
uv sync --frozen
uv run --frozen python tasks.py integrated-check
uv run --frozen python tasks.py integrated-config
uv run --frozen python tasks.py integrated-smoke
```

Then confirm executor help lists only:

```text
integrated-check
integrated-config
integrated-start
integrated-stop
integrated-smoke
```

The smoke output is disposable development verification, not retained P8/P9
evidence.

### Manuscript boundary

Before any manuscript edit, verify the copied anchors:

```text
cab18dd54cb09f3d3c296786dd3b856d3891d48d54861b3a8fb7686e144130db  paper/main.tex
d4c5e66a0968884538d5446086569c60b51c55fe710acfd5b4082bc8e1b83e69  paper/references.bib
c42bb7766a08ad1cfe2c7d5d66a726c52277395df46fc12486e6749e111fec22  paper/main.pdf
```

Build from `paper/` with the documented LaTeX toolchain and visually inspect
the review PDF. A successful migration does not authorize replacing the
tracked PDF unless an approved manuscript change is being applied and all
paper governance steps are followed.

### Active implementation anchors

Verify these copied public/dependency anchors before the first LOCUS-v4 edit:

```text
4fbd85bc3c1c96cd95929e645294b44b521023f3329fdd00d13466c29ee0f29c  prototype_final/uv.lock
f27b370a746b8d9107fb96a40719d721060e81855f0669cbc3febbeae9953185  prototype_final/deploy/managed-manifest.json
c844ccc5b2dd4dfe188bc2c3bf53b932191409dc2ddefba64595582675cfb438  prototype_final/docs/security-matrix-v2.json
```

These are migration-integrity anchors, not permanent frozen identifiers. If
they change later, the applicable versioning, decision, test, evidence, and
documentation rules still apply.

## Information that does not yet exist and must be created in LOCUS-v4

The LOCUS-v3 repository intentionally does **not** contain completed P8/P9/P10
result infrastructure. Do not invent or pre-populate it during copying.

### Before P8 retained collection

P8.1 must first create a checked inventory of every externally reachable
decoder and durable mutating transition, map each to negative/integrated
coverage, and close gaps. P8.1 is assurance work, not retained evidence.

P8.2 must then assign and implement the exact aggregate-only security/state
result identifiers, schemas, versioned paths, scenario manifests, positive
controls, provenance, and exclusive-publication rules before collecting any
state-boundary evidence.

P8.3 must separately assign the privacy-safe network-flow trace identifier,
schema, permitted categories, positive controls, unexpected-contact rule,
versioned path, and output-safety checks. Packet captures are not retained.

P8.4 must preserve the documented attempt-control limitation and must not turn
local signed audit state into a global rollback-resistant claim.

### Before P9 retained collection

P9.1 must freeze sample sizes, randomization, warm-up, exclusions, statistics,
host/topology descriptions, metric definitions, and the no-outlier policy.

P9.2 must assign new suite/topology-specific performance and resilience result
families and schemas. Those schemas must bind the D025 managed deployment,
manifest and graph digests, images, identities, networks, provider, policy,
failure schedule, active-client boundary, source commit, and output scan.

Only after those gates may P9.3 collect the same-host integrated baseline.
Optional AWS or multi-host work remains separately authorized and separately
versioned under P9.4.

`integrated-smoke` is not a performance collector and its output is not paper
evidence.

### Before P10 and manuscript changes

LOCUS-v4 still needs:

- the independent human D019 cryptographic mapping review required by P10.1;
- the independent systems review required by P10.2;
- a new P10.3 artifact identifier, allowlist, manifest, archive builder,
  clean Linux/Windows reproduction record, and unfamiliar-reviewer workflow;
- P10.4 claim/evidence closure over the new retained profiles; and
- exact owner-approved manuscript change sets before any P10.6 edit.

The current manuscript build toolchain is documented but not yet pinned for
byte-identical cross-host reproduction. LOCUS-v4 should record a reproducible
LaTeX toolchain before paper release work.

The owner-supplied aPPSS research paper and `extra/TPASS.pdf` are not tracked
because redistribution authority was not established. An independent reviewer
must obtain required source publications through lawful channels; they must
not be copied from ignored local files into LOCUS-v4.

## Visual and architectural improvements after migration

Visual changes are permitted only while keeping the UI thin and preserving
the assigned API, privacy, no-storage, no-telemetry, transient-key, and
loopback boundaries. A purely visual implementation fix may remain within the
assigned UI profile only if it does not change its semantic contract.

Any change to request/result meaning, routes, package fields, private-key
handling, browser persistence, topology, role placement, provider, admission,
controller authority, lifecycle semantics, or measurement boundary requires
an owner decision where applicable and a new identifier/profile before its
evidence is collected. Update `DECISIONS.md`, `VERSION-REGISTRY.md`, `PLAN.md`,
the managed manifest/schema, security matrix, tests, and active technical docs
together.

Do not begin visual or architectural redesign before the copied LOCUS-v4
baseline passes unchanged. Otherwise a migration defect and a new design
change cannot be distinguished.

## Immediate LOCUS-v4 execution order

After the copy and unchanged validation pass:

1. create the LOCUS-v4 provenance and portability records;
2. normalize repository-layout documentation without changing technical
   semantics;
3. start P8.1 in `prototype_final/`;
4. assign P8.2/P8.3 evidence contracts before collection;
5. complete P8.4 and the applicable output-safety gates;
6. freeze P9.1 methodology and assign P9.2 result schemas;
7. collect and process P9.3 evidence append-only;
8. perform P10 independent reviews and build the new portable artifact;
9. close the claim/evidence matrix; and
10. propose, obtain approval for, and only then apply exact manuscript deltas.

This order keeps the clean migration separate from new assurance,
measurement, architecture, and paper-writing decisions.
