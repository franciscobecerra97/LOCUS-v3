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
| `prototype_final/` | Sole active P8+ integrated implementation, focused tests, native dependencies, deployment, and five-command executor |
| `prototype/`, root native crates, `deploy/`, and root `tasks.py` | Preserved historical/component implementations and controls |
| `docs/` | Active baseline documentation, target-design drafts, schemas, and provenance snapshots |
| `experiments/` | Frozen v1/v2 records plus separately versioned future evidence |
| `paper/` | Authoritative manuscript, bibliography, build inputs, generated rows, and review PDF |
| `artifact/` | Active installation, evaluation, packaging, and release planning |
| `dist/` | Sealed verified v1 anonymous-artifact release and manifest |

## Current chronological priority

P1--P5A, P6.1--P6.3, and P7.1--P7.7 are complete for implementation chronology.
D020's internal recovery-suite mapping assessment is provisional; independent
human validation remains mandatory before manuscript reliance or final
reviewed release. D025/P7.7 replaced CLI-selected clients with a separately
versioned Manager/controller,
dynamic Client UI, and client-recovery-package workflow inside
`prototype_final/` and assigned all twelve managed identifiers. P8.1 is the
next ready step. No retained P8/P9 collection occurred during P7.7; later
collection still requires its applicable schema, trace, result, provenance,
path, positive-control, and output gate.

The completed P7.5 predecessor is one reproducible same-host system in which the loopback UI
and client gateway call the authenticated admission, discovery, storage,
resolver, and five-party container services. The existing P7 in-memory UI and
the frozen `LOCUS-compose-deployment-v2` deployment remain regression controls;
neither is silently reinterpreted as the integrated system. The integrated run
commands and their lifecycle/fault/reproducibility gates now pass.

P7.7 preserves that protocol/service path while changing the operator,
UI/API, clean-client, package, and Docker-control boundaries. Its dedicated
controller is the only role permitted to receive the root-equivalent Docker
socket; Manager and Client containers never receive it. The local
S3-compatible provider remains part of the reference path, and a downloaded
client recovery package does not replace current-state checks or online
threshold parties.

The managed graph keeps `management` (Manager/controller) and
`client-lifecycle` (Client/controller) internal and disjoint. `manager-edge`
publishes only the Manager loopback path, while `browser-edge` publishes only
dynamic Client loopback paths; neither is a container-level Manager-to-Client
channel. Client stop/start, restart, and kill/start preserve the public client
ID but deliberately rotate proof identity and erase volatile key/session state.

The one-shot bootstrap runs as root with every Linux capability dropped except
exactly `CHOWN` and `DAC_READ_SEARCH`, has no network or Docker socket, and exits
before unprivileged runtime services start. Its scope is limited to approved
synthetic credentials, public configuration, empty role roots, fixtures, and
their owner-only files.

P6.4 remains open at its infrastructure gate: the strict endpoint file and
additive Compose overlay run all five parties locally, but actual VMs or hosts
remain necessary for a higher tier. A same-host P7.5 system does not close that
gate. Live AWS validation remains a separately authorized optional gate.

For active work, enter `prototype_final/`, install its pinned environment, and
run `uv run --frozen python tasks.py integrated-check`. Validate its graph with
`integrated-config` and use `integrated-smoke` for disposable development
verification. The normal interactive entry point is one mode-free
`integrated-start`, followed by Manager and Client UI actions; Manager stop is
the normal stop path and CLI cleanup is emergency-only. That implemented
workflow passed the complete P7.7 gate. The old `--mode enrollment` and
`--mode recovery` workflow is the D023 predecessor, not the P8 target. The root
executor remains only for historical/component reproduction. These commands
create no retained evidence, usability claim, real-provider result, or
manuscript change.

Emergency `integrated-stop` preserves exact-project role/provider volumes.
`integrated-stop --reset-state` is an explicit irreversible local reset that
also removes credentials and enrolled remote state; it is required after
expiry or an incompatible preserved manifest because the 366-day CA and
365-day role certificates are not renewed in place.

## Foundation and integrated-system sequence

The completed foundation established:

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

The frozen composite CuePolicy was then joined by separate
quantized-coordinate, canonical-phone, and canonical-email set policies. The
local UI, provider contracts, paired suite/topology deployment controls, and
lifecycle work now exist as separately scoped components.

P7.5 connects those components without changing their protocol meanings. It
first freezes the deployment contract, then implements the container service
plane, connects the frozen client API and UI through authenticated remote
adapters, completes enrollment/clean-client recovery/successor workflows, and
passes one pre-evidence system gate. P7.7 assigned and validated the managed
Manager/Client deployment family without changing the underlying protocol.
Its enhanced smoke covered all four suite/topology arms, 26 subsets, four clean
Clients, live control and lifecycle isolation, role/output audits, preserved-CA
restart, fresh-CA destructive reset with old-package rejection, and cleanup.
Existing successor-core behavior remains an unchanged compatibility control
outside Client API v2 and the managed Client UI. P8.1 assurance may now begin.
Only after the applicable future evidence gates may P8/P9 collection produce
retained results from the managed system; component-only and D023 runs remain
supporting controls.

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
