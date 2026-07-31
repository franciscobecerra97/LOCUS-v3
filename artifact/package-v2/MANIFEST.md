# LOCUS Anonymous Package Manifest

`LOCUS-anonymous-artifact-v2` is built from an explicit allowlist. It contains:

- project software, documentation, and third-party licensing notices;
- pinned build metadata, lockfiles, task runner, and continuous-integration
  workflow;
- these package-specific reviewer instructions;
- Python and Rust implementation source, tests, and synthetic vectors;
- isolated same-host deployment configuration and fictional resolver fixtures;
- machine-readable schemas;
- frozen aggregate v2 attack and performance records;
- the deterministic processed v2 performance summary; and
- manifest-bound generated v2 performance-table inputs.

It excludes version-control metadata, author identity, internal planning
records, the manuscript and PDF, bibliography and LaTeX support files,
superseded evidence, external papers, build outputs, caches, logs, traces,
snapshots, databases, credentials, private keys, and real user or cue data.

`artifact_manifest.json` records the package identifier, clean source revision,
and every packaged source path, byte length, and SHA-256 digest. Entries are
sorted and unique. Extracted-tree validation accepts the sealed v1 format for
compatibility and this v2 format for the current package; neither format is
reinterpreted.

Included software and configuration are covered by Apache License 2.0. Included
project-authored documentation and aggregate experiment material are covered by
CC BY 4.0. The package excludes manuscript-only and unverified external
third-party material.
