# LOCUS Repository Hygiene And Data Lifecycle

Status: P1.9 source/generated separation contract, 2026-07-21.

## Tracked source and reproducibility inputs

Track manuscript source, bibliography, required ACM style inputs, Python/Rust
source, tests, schemas, configuration, dependency locks, committed synthetic
fixtures/vectors, experiment scripts, and documentation. `paper/main.pdf` is an
intentional compiled manuscript snapshot for review; it is derived, must match
`paper/main.tex`, and is not a source of claims or results.

`paper/generated/` contains small tracked LaTeX inputs produced by versioned
scripts. Each current file is historical/legacy until its source result and
provenance satisfy the experiment contract. Future paper inputs must derive from
`experiments/processed/` and identify their generating command/source metadata.
P7.16 writes corrected outputs only below
`paper/generated/performance-v2/` after validating a matching canonical v2
processed artifact. The v1 directory is immutable historical output. Identical
generation is idempotent; replacing a changed complete bundle requires an
explicit flag, and cross-version publication is rejected.

## Scratch and build output

The following are never tracked:

- Python bytecode/caches, type/lint/test caches, coverage output, build wheels,
  native-extension build trees, and Rust `target/` trees;
- root-level LaTeX build products such as `.aux`, `.bbl`, `.blg`, `.fls`,
  `.fdb_latexmk`, `.log`, `.out`, `.synctex.gz`, `.toc`, and `paper/_build/`; and
- `prototype/.benchmarks/`, which is development scratch space only.

Existing ignored files may remain in a developer checkout, but they are not part
of the artifact. A repository hygiene check runs inside the normal quality gate
and rejects tracked caches, scratch benchmarks, or LaTeX byproducts.

## Experiment lifecycle

- `experiments/raw/` contains immutable, provenance-complete original outputs.
- `experiments/processed/` contains reproducibly derived analysis data.
- `paper/generated/` contains only final script-derived LaTeX/figure inputs.
- A development console or `prototype/.benchmarks/` run is disposable and can
  never be promoted by copying values manually into the manuscript.

Paper evidence must pass `LOCUS-experiment-metadata-v1`: clean exact commit,
pseudonymous host label, dependency-lock hashes, complete configuration,
randomness provenance, timestamps, no warnings, and retained repository-relative
output under `experiments/raw/`. Raw results are append-only after collection;
corrections create a new run. Processed and paper outputs may be regenerated but
must not overwrite or edit their raw inputs.

Retained JSON below `experiments/raw/` is ignored during multi-file acquisition.
Otherwise, the first immutable output would make the tree dirty and prevent
later records from binding the same clean source commit. After the complete
corpus passes its versioned validators, force-add only the exact reviewed raw
paths; never force-add the directory blindly. Tracked raw files remain tracked
normally. Their embedded source commit intentionally identifies the clean
collection code, not the later evidence-packaging commit.

Human data, real cue records, credentials, private keys, and secret protocol state
are forbidden in all of these paths. Synthetic inputs remain clearly labeled.

## Anonymous artifact lifecycle

The development repository is not the anonymous artifact. The package contract
in `artifact/MANIFEST.md` uses an explicit allowlist, excludes Git
history/remotes and manuscript-only third-party material, and includes only the
authoritative v2 retained/processed/generated evidence paths. `dist/` remains
ignored build output.

`tasks.py artifact-package --check` may audit a development tree without
creating an archive. Archive creation requires a clean committed state,
successful anonymity scanning, and an explicit approved release status in
`artifact/RELEASE-CHECKLIST.md`. The resulting ZIP contains a canonical member
manifest with content hashes; it is never treated as a new experiment result.
