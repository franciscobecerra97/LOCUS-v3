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
  the earlier unimplemented personal-cloud and Google Drive choices;
- the D017/D018 aPPSS profile, P5A.1 formats, and independently versioned
  P5A.2 `locus-appss-core` implementation using the pinned RFC 9497/Ristretto,
  SHA-2, randomness, error, and zeroization dependencies already present in
  the project Rust dependency set.

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

## Independent repository

- Repository root: this directory (`LOCUS-v3/`)
- Initial import commit:
  `71836c304490db0984cbe2786edf414ff18a960b`
- Initial branch: `main`
- Remote: owner-created `LOCUS-v3` GitHub repository
- Imported parent history: none

The independent repository was initialized on 2026-07-31. Before the first
project-authored follow-up commit, all 307 manifest entries matched their
recorded sizes and SHA-256 digests, all 308 intended files were tracked, and no
ignored or untracked files were present.

The upstream `.git` directory and upstream history were not copied.

## LOCUS-v4 prototype reintegration

On 2026-08-14, the owner chose to continue P8--P10 in this LOCUS-v3
repository and authorized copying the newer active prototype back from the
independent `LOCUS-v4-claude` continuation. The imported source state was
commit `760f48e` on branch `claude/ui-manager-stop-control`. That repository
had renamed its active `prototype_final/` tree to `prototype/`; this import
mapped its 103 source-controlled files back to this repository's governed
`prototype_final/` boundary.

Only files reported by the source repository's tracked `prototype/` set were
copied. Environments, caches, Rust targets, bytecode/native build artifacts,
databases, credentials, logs, traces, and Docker state were excluded. Hash
comparison after copying found zero mismatches across the 103 imported files.

The imported delta supplied the starting P8.1 decoder/transition inventory and
two admission/discovery negative tests, and updates the thin
Manager/Client assets with interaction guards and layout changes. It changes
no protocol bytes, API route or result meaning, deployment manifest,
cryptographic profile, evidence identifier, retained result, or manuscript
source. P8.1 was then completed locally with the checked inventory, active
assurance corpus, containment fixes, and full-system schedules. LOCUS-v4
history remains external provenance; this LOCUS-v3 history
continues as the authoritative project history.

## Portable contents manifest

`PORTABLE-CONTENTS.json` contains a sorted path/size/SHA-256 record for every
other file in this seed. It excludes itself to avoid a recursive self-digest.
It permanently describes the initial portable seed and is not regenerated for
ordinary project changes. Its contents were verified immediately before the
first project-authored follow-up commit.
