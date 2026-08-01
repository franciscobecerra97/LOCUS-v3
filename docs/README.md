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
- `SYSTEM-INTERFACES.md`
- `APPSS-MIGRATION.md`
- `APPSS-PROFILE.md`
- `RECOVERY-DESCRIPTOR.md`
- `CUE-POLICY-REGISTRY.md`
- `INFORMATION-FLOW.md`
- `security-matrix-v1.json` for the schema-checked C01--C26 security contracts
- root `PROTOCOL-INVARIANTS.md`
- root `VERSION-REGISTRY.md` plus machine-readable
  `version-registry-v1.json`

`schemas/` contains inherited active evidence schemas, the P1.4/P1.5
governance schemas, the P2.1 descriptor/current-pointer/manifest schemas, and
the P2.2 installed-trust/recovery-receipt/party-current-summary schemas. New
schemas must receive new identifiers rather than changing the meaning of
existing versions.

The lower-case baseline documents remain active and must be synchronized with
approved implementation and manuscript changes. An upper-case target-design
file may record an owner-approved architecture direction in its status line,
but it does not supersede implemented baseline behavior or the manuscript until
the matching implementation/evidence gates and a separate manuscript delta are
approved.

`upstream-baseline/` is a byte-for-byte provenance snapshot. Do not edit it;
maintain current facts at the normal active paths.
