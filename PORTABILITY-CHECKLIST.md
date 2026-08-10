# Portability Checklist

Use this after copying the seed to its independent directory.

## Required root files

- [x] `AGENT.md`
- [x] `AGENTS.md`
- [x] `PLAN.md`
- [x] `README.md`
- [x] `PROJECT-CHARTER.md`
- [x] `BASELINE.md`
- [x] `THESIS-GUARDRAILS.md`
- [x] `MANUSCRIPT-BOUNDARY.md`
- [x] `PROTOCOL-INVARIANTS.md`
- [x] `VERSION-REGISTRY.md`
- [x] `DECISIONS.md`
- [x] `EVIDENCE-POLICY.md`
- [x] `CLAIM-EVIDENCE-MATRIX.md`
- [x] `SOURCE-PROVENANCE.md`
- [x] `LICENSE`, `LICENSE-DOCUMENTATION.md`, `LICENSES.md`
- [x] `pyproject.toml`, `uv.lock`, `.python-version`
- [x] `rust-toolchain.toml`
- [x] `tasks.py`

## Required source directories

- [x] `prototype_final/` (sole active P8+ integrated workspace)
- [x] `prototype/locus/`
- [x] `prototype/tests/`
- [x] `prototype/test-vectors/`
- [x] `tpass-core/src/`
- [x] `tpass-core/tests/`
- [x] `tpass-core/test-vectors/`
- [x] `tpass-python/src/`
- [x] `deploy/`
- [x] `docs/schemas/`
- [x] `docs/upstream-baseline/`
- [x] `.github/workflows/`
- [x] Active baseline technical documents at `docs/*.md`
- [x] `docs/TARGET-ARCHITECTURE.md`, `docs/RECOVERY-DESCRIPTOR.md`,
      `docs/CUE-POLICY-REGISTRY.md`, and `docs/INFORMATION-FLOW.md`
- [x] `paper/main.tex`, `paper/references.bib`, and required ACM build inputs
- [x] `paper/main.pdf`
- [x] `paper/generated/performance-v2/`
- [x] `experiments/raw/attacks-v2/`
- [x] `experiments/raw/performance-v2/01/` through `10/`
- [x] `experiments/processed/performance-v2/summary.json`
- [x] `artifact/`
- [x] `dist/LOCUS-anonymous-artifact-v1.zip`
- [x] `dist/LOCUS-anonymous-artifact-v1.manifest.json`

## Must not be copied

- [x] No upstream `.git` directory or remotes
- [x] No `.venv`
- [x] No Rust `target` directories
- [x] No Python caches or native `.pyd`, `.pdb`, `.so` files
- [x] No `tmp` or scratch benchmarks
- [x] Manuscript source, required style inputs, generated rows, and intentional
      review PDF are present; LaTeX byproducts are absent
- [x] Frozen v2 evidence is present and labelled exact-profile baseline
- [x] V1 evidence is present only as immutable superseded history
- [x] Verified anonymous-artifact ZIP is present; duplicate extracted
      `artifact-submission/` is absent
- [x] No `extra/TPASS.pdf`
- [x] No `.env`, credentials, tokens, certificates, or private keys
- [x] No SQLite databases, snapshots, service logs, traces, or dumps
- [x] No developer username, email, local absolute path, or author identity in
      the imported portable seed

## New repository initialization

- [x] Run `git init` at the copied root
- [x] Inspect `.gitignore`
- [x] Inspect `git status --short --ignored`
- [x] Verify `PORTABLE-CONTENTS.json` before staging
- [x] Stage all intended portable files, including every allowlisted frozen
      raw v1/v2 JSON record
- [x] Review staged paths
- [x] Create initial import commit
- [x] Record the commit in `SOURCE-PROVENANCE.md`
- [x] Configure a remote only after checking its visibility and ownership

## Build validation

- [x] `cd prototype_final`
- [x] `uv sync --frozen`
- [x] `uv run --frozen python tasks.py integrated-check`
- [x] `uv run --frozen python tasks.py integrated-config`
- [x] `uv run --frozen python tasks.py integrated-smoke`
- [x] `uv sync --frozen`
- [x] `uv run --frozen python tasks.py check`
- [x] Native extension built from source
- [x] Python tests passed
- [x] Rust tests, formatting, and clippy passed
- [ ] Clean Linux CI passed
- [ ] Clean Windows CI passed

## Safety validation

- [ ] Recursive secret/prohibited-output scan passed
- [ ] All fixtures are fictional
- [ ] All keys and credentials are generated at runtime
- [ ] Docker profiles are loopback/internal or exact disposable services
- [ ] Cleanup identifies exact resources
- [ ] External provider profiles are disabled by default

## Baseline integrity

- [x] Existing v1 policy vectors remain unchanged
- [x] Existing TPASS fixed vector remains unchanged
- [ ] Frozen identifiers match `VERSION-REGISTRY.md`
- [ ] Retained evidence and review-PDF hashes match `BASELINE.md`
- [x] V2 may be verified/reprocessed only as the exact baseline profile
- [ ] New processors do not mix inherited v1/v2 evidence with changed profiles
