# Source Provenance

## Upstream

- Project: LOCUS distributed private-key recovery prototype
- Upstream commit:
  `771fccd14d918b697bfb48fd24a0202c52c7f7ac`
- Extraction date: 2026-07-29
- Extraction type: integrated continuation snapshot

## Copied active material

- pinned Python and Rust configuration and lockfiles;
- Python source, tests, scripts, type stub, and deterministic vectors;
- Rust TPASS core, binding source, tests, locks, and fixed vectors;
- same-host deployment configuration and fictional resolver fixture;
- evidence schemas;
- CI configuration;
- project software/documentation licenses;
- active technical documentation plus a read-only upstream snapshot;
- active manuscript source, bibliography, required style/build inputs, and
  intentional compiled review snapshot;
- retained v1/v2 raw and processed evidence;
- generated paper inputs, including the manifest-bound v2 bundle;
- the sealed v1 anonymous-artifact ZIP and its external manifest.

## New project-authored material

- `AGENT.md` and `AGENTS.md`;
- new `PLAN.md`;
- project charter, baseline, thesis, manuscript, protocol, version, decision,
  evidence, portability, and claim/evidence documents;
- artifact and experiment lifecycle/governance material;
- target-architecture, RecoveryDescriptor, and information-flow planning
  documents;
- the owner-approved CuePolicy registry target design; and
- the owner-approved recovery-bundle and account-scoped discovery direction;
  and
- the D015 proof-key-bound application storage gateway, application-operated
  S3 access model, and supplemental AWS S3 provider direction that supersede
  the earlier unimplemented personal-cloud and Google Drive choices.

## Deliberately excluded

- `.git` and all upstream history/remotes;
- duplicate anonymous-artifact extraction;
- caches, environments, targets, native binaries, scratch output, and LaTeX
  byproducts other than the intentional review PDF;
- credentials, certificates, keys, databases, snapshots, logs, and traces;
- third-party PDFs under upstream `extra/` because redistribution authority was
  not established.

## Retained evidence boundary

The exact inherited hashes are recorded in `BASELINE.md` and
`PORTABLE-CONTENTS.json`. V1 is superseded history. V2 remains baseline evidence
for its exact frozen profile and can be deterministically verified, processed,
and used to reproduce the current manuscript inputs. Neither family supports
changed implementation profiles.

## Portability note

This directory is currently nested only as a staging location. After copying it
to the intended independent directory:

1. initialize a new Git repository;
2. make an initial import commit;
3. run the frozen environment synchronization;
4. run the complete quality/test gate;
5. record the new repository commit as the starting point for all future
   evidence.

Do not copy the upstream `.git` directory.

## Portable contents manifest

`PORTABLE-CONTENTS.json` contains a sorted path/size/SHA-256 record for every
other file in this seed. It excludes itself to avoid a recursive self-digest.
Verify that manifest immediately after copying and before initializing the new
project.
