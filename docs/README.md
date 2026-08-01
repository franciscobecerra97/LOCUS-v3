# Active Technical Documentation

This directory contains both the active imported baseline documentation and
clearly marked target-design drafts for the improvement project.

For current implemented/paper-facing behavior, start with the lower-case
baseline documents:

- `threat-model.md`
- `limitations-and-assumptions.md`
- `claim-evidence-matrix.md`
- `paper-protocol-mapping.md`
- `architecture.md`

For proposed architecture, start with:

- `TARGET-ARCHITECTURE.md`
- `APPSS-MIGRATION.md`
- `APPSS-PROFILE.md`
- `RECOVERY-DESCRIPTOR.md`
- `CUE-POLICY-REGISTRY.md`
- `INFORMATION-FLOW.md`
- root `PROTOCOL-INVARIANTS.md`

`schemas/` contains inherited active evidence schemas. New schemas must receive
new identifiers rather than changing the meaning of existing versions.

The lower-case baseline documents remain active and must be synchronized with
approved implementation and manuscript changes. An upper-case target-design
file may record an owner-approved architecture direction in its status line,
but it does not supersede implemented baseline behavior or the manuscript until
the matching implementation/evidence gates and a separate manuscript delta are
approved.

`upstream-baseline/` is a byte-for-byte provenance snapshot. Do not edit it;
maintain current facts at the normal active paths.
