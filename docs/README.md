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
- `INTEGRATED-REFERENCE-SYSTEM.md` for D023's approved P7.5 UI-to-services
  construction, trust boundaries, four suite/topology arms, and pre-evidence
  acceptance matrix
- `APPSS-MIGRATION.md`
- `APPSS-PROFILE.md`
- `RECOVERY-SUITE-MAPPING-REVIEW.md` for D019's claim-focused Yi/aPPSS and
  LOCUS-composition review packet
- `P5A7-INTERNAL-MAPPING-ASSESSMENT.md` for D020's explicitly
  non-independent provisional assessment and mandatory human follow-up
- `RECOVERY-SUITE-DEVIATIONS.md` for the required engineering-versus-
  claim-critical mapping register
- `P5A7-RELEASE-READINESS.md` for the candidate build/release gate record
- `P6.4-HOST-SEPARATION.md` for the exact multi-VM/multi-host readiness gate
  and current configurable same-host limitation
- `CLIENT-API.md` for the frozen P7.1 UI-facing orchestration boundary
- `RESEARCH-UI.md` for the P7.2--P7.4 local enrollment, recovery, and safe
  inspector interface and its privacy limitations
- `RECOVERY-DESCRIPTOR.md`
- `CUE-POLICY-REGISTRY.md`
- `INFORMATION-FLOW.md`
- `security-matrix-v1.json` for the schema-checked C01--C26 security contracts
- root `PROTOCOL-INVARIANTS.md`
- root `VERSION-REGISTRY.md` plus machine-readable
  `version-registry-v1.json`

`schemas/` contains inherited active evidence schemas, the P1.4/P1.5
governance schemas, the P2.1 descriptor/current-pointer/manifest schemas, the
P2.2 installed-trust/recovery-receipt/party-current-summary schemas, and the
P2.4 aggregate descriptor-security development schema. New schemas must receive
new identifiers rather than changing the meaning of existing versions.

`prototype/test-vectors/descriptor-store-v1.txt` pins the P2.3 provider-neutral
descriptor, bundle, and hashed-handle current-pointer key grammar to the P2.1
public vectors. It contains no provider credential or secret material.

P6.1 adds `prototype/tests/storage_provider_contract.py`, which runs the same
provider-level role suite against deterministic filesystem and S3-compatible
composites without merging their distinct object contracts.

`AWS-S3-PROFILE.md` records the P6.2 TLS-only AWS application profile, admitted
gateway operations, narrow no-list IAM shape, locally reproducible tests, and
the still-open separately authorized live-provider gate.

P6.3 adds strict aPPSS wire v2, selector v2, and reference-backup v6 schemas,
plus a public-only 3-of-5 topology vector. The two paired deployment-control
profiles are same-host process conformance only; they are not retained evidence
or independent administration.

The lower-case baseline documents remain active and must be synchronized with
approved implementation and manuscript changes. An upper-case target-design
file may record an owner-approved architecture direction in its status line,
but it does not supersede implemented baseline behavior or the manuscript until
the matching implementation/evidence gates and a separate manuscript delta are
approved.

D023 makes P7.5 the next implementation phase. The current P7 in-memory UI and
the frozen same-host Compose deployment remain separately identified controls;
the planned integrated profile must connect the UI/client gateway to all
authenticated service roles before P8/P9 system evidence is collected. P7.5
does not yet have a run command, and its same-host construction will not satisfy
the still-open P6.4 VM/host-separation gate.

`upstream-baseline/` is a byte-for-byte provenance snapshot. Do not edit it;
maintain current facts at the normal active paths.
