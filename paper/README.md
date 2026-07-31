# LOCUS Manuscript Workspace

`main.tex` is the authoritative active manuscript and `main.pdf` is its
intentional review snapshot. The imported snapshot is 14 pages and has
SHA-256:

```text
c42bb7766a08ad1cfe2c7d5d66a726c52277395df46fc12486e6749e111fec22
```

The active ACM build uses:

- `main.tex`;
- `references.bib`;
- `acmart.cls`;
- `ACM-Reference-Format.bst`; and
- `generated/performance-v2/latency_rows.tex`.

The complete v2 generated bundle is retained together for deterministic
verification. `related_work.tex`, `generated/performance-v1/`, and the legacy
benchmark/guessing rows are historical and are not included by `main.tex`.

From this directory, the current conventional build is:

```console
latexmk -pdf main.tex
```

Equivalently, run `pdflatex`, `bibtex`, and then `pdflatex` twice. The baseline
snapshot was produced with MiKTeX pdfTeX/BibTeX. PLAN P0 should pin and document
one manuscript toolchain before relying on byte-identical output across hosts.

The build is currently known to contain overfull-box, accessibility-description,
and incomplete-bibliography-metadata warnings. Treat those as review tasks, not
as permission to change narrative automatically.

Read `paper/AGENTS.md` before any manuscript work. Every paper delta remains
owner-gated.
