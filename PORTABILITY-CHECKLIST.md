# Portability Checklist

Use this after copying the seed to its independent directory.

## Required root files

- [ ] `AGENT.md`
- [ ] `AGENTS.md`
- [ ] `PLAN.md`
- [ ] `README.md`
- [ ] `PROJECT-CHARTER.md`
- [ ] `BASELINE.md`
- [ ] `THESIS-GUARDRAILS.md`
- [ ] `MANUSCRIPT-BOUNDARY.md`
- [ ] `PROTOCOL-INVARIANTS.md`
- [ ] `VERSION-REGISTRY.md`
- [ ] `DECISIONS.md`
- [ ] `EVIDENCE-POLICY.md`
- [ ] `CLAIM-EVIDENCE-MATRIX.md`
- [ ] `SOURCE-PROVENANCE.md`
- [ ] `LICENSE`, `LICENSE-DOCUMENTATION.md`, `LICENSES.md`
- [ ] `pyproject.toml`, `uv.lock`, `.python-version`
- [ ] `rust-toolchain.toml`
- [ ] `tasks.py`

## Required source directories

- [ ] `prototype/locus/`
- [ ] `prototype/tests/`
- [ ] `prototype/test-vectors/`
- [ ] `tpass-core/src/`
- [ ] `tpass-core/tests/`
- [ ] `tpass-core/test-vectors/`
- [ ] `tpass-python/src/`
- [ ] `deploy/`
- [ ] `docs/schemas/`
- [ ] `docs/upstream-baseline/`
- [ ] `.github/workflows/`
- [ ] Active baseline technical documents at `docs/*.md`
- [ ] `docs/TARGET-ARCHITECTURE.md`, `docs/RECOVERY-DESCRIPTOR.md`,
      `docs/CUE-POLICY-REGISTRY.md`, and `docs/INFORMATION-FLOW.md`
- [ ] `paper/main.tex`, `paper/references.bib`, and required ACM build inputs
- [ ] `paper/main.pdf`
- [ ] `paper/generated/performance-v2/`
- [ ] `experiments/raw/attacks-v2/`
- [ ] `experiments/raw/performance-v2/01/` through `10/`
- [ ] `experiments/processed/performance-v2/summary.json`
- [ ] `artifact/`
- [ ] `dist/LOCUS-anonymous-artifact-v1.zip`
- [ ] `dist/LOCUS-anonymous-artifact-v1.manifest.json`

## Must not be copied

- [ ] No upstream `.git` directory or remotes
- [ ] No `.venv`
- [ ] No Rust `target` directories
- [ ] No Python caches or native `.pyd`, `.pdb`, `.so` files
- [ ] No `tmp` or scratch benchmarks
- [ ] Manuscript source, required style inputs, generated rows, and intentional
      review PDF are present; LaTeX byproducts are absent
- [ ] Frozen v2 evidence is present and labelled exact-profile baseline
- [ ] V1 evidence is present only as immutable superseded history
- [ ] Verified anonymous-artifact ZIP is present; duplicate extracted
      `artifact-submission/` is absent
- [ ] No `extra/TPASS.pdf`
- [ ] No `.env`, credentials, tokens, certificates, or private keys
- [ ] No SQLite databases, snapshots, service logs, traces, or dumps
- [ ] No developer username, email, local absolute path, or author identity

## New repository initialization

- [ ] Run `git init` at the copied root
- [ ] Inspect `.gitignore`
- [ ] Inspect `git status --short --ignored`
- [ ] Verify `PORTABLE-CONTENTS.json` before staging
- [ ] Stage all intended portable files, including every allowlisted frozen
      raw v1/v2 JSON record
- [ ] Review staged paths
- [ ] Create initial import commit
- [ ] Record the commit in `SOURCE-PROVENANCE.md`
- [ ] Configure a remote only after checking its visibility and ownership

## Build validation

- [ ] `uv sync --frozen`
- [ ] `uv run --frozen python tasks.py check`
- [ ] Native extension built from source
- [ ] Python tests passed
- [ ] Rust tests, formatting, and clippy passed
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

- [ ] Existing v1 policy vectors remain unchanged
- [ ] Existing TPASS fixed vector remains unchanged
- [ ] Frozen identifiers match `VERSION-REGISTRY.md`
- [ ] Retained evidence and review-PDF hashes match `BASELINE.md`
- [ ] V2 may be verified/reprocessed only as the exact baseline profile
- [ ] New processors do not mix inherited v1/v2 evidence with changed profiles
