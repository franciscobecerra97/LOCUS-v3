# Managed State Evidence Profile v1

Status: Assigned by owner-approved D026 and collected on 2026-08-17 from clean
source commit `6e304560222b8059292ae291586ee792cc39ed3d` after this profile,
its schemas, collector, tests, and command surface were committed.

This profile assigns `LOCUS-managed-state-evidence-profile-v1`, the fixed
scenario manifest `LOCUS-managed-state-scenario-manifest-v1`, suite-separated
result families `LOCUS-managed-state-result-yi-v1` and
`LOCUS-managed-state-result-appss-v1`, the suite-neutral
`LOCUS-managed-state-result-common-v1`, and
`LOCUS-managed-state-corpus-manifest-v1`.

The normative scenario membership is `managed-state-scenarios-v1.json`: 18 Yi,
18 aPPSS, and six managed-common reports, exactly 42 in total. Paired 2-of-3
arms use the canonical-email policy; paired 3-of-5 arms use the location-person
policy. Each pair uses the same synthetic key/input class, five authorizers,
4-of-5 authorization quorum, admission, provider, network schedule, and metric
definitions. Suite states and result paths never mix.

The live collector starts from the Manager, creates dynamic Clients, traverses
the authenticated service graph, and runs the complete managed smoke with the
paired policy conditions. Networkless read-only audit containers observe all
15 exact role volumes and retain only role, logical volume role, file count,
and total bytes. Their aggregate manifest digest binds the snapshot event; no
file content or secret-state digest is retained.

Allowed records contain assigned identifiers, counts, Booleans, bounded error
categories, public configuration/fixture digests, clean source provenance,
immutable image identity, graph digests, pseudonymous host tier, exact role
membership, positive-control status, output-scan status, cleanup status, and
fixed limitations. They contain no cues, candidates, per-candidate outcomes,
password inputs, suite secrets, wrapping/private keys, credentials,
certificates, databases, raw snapshots, logs, packet captures, screenshots,
absolute paths, user identity, or free-form diagnostics.

Exploratory execution writes no report. Retained execution requires a clean
commit and writes all reports into a same-filesystem staging directory. Every
record and the exact 42-member corpus are revalidated before an exclusive
directory rename to `evidence/retained/managed-state-v1/`. An existing target,
partial failure, failed positive control, output finding, incomplete cleanup,
or membership mismatch publishes nothing. The path is append-only; changed
semantics or membership require a new profile version.

The corpus is exact D025 same-host, single-operator implementation evidence.
It is not a cryptographic proof, independent-administration, multi-host,
real-provider, production-security, usability, forensic-erasure, or global
rollback-resistant attempt-control result. It authorizes no manuscript edit.

The exclusive retained directory contains exactly 42 canonical reports plus
`corpus-manifest.json`. Its 18 Yi, 18 aPPSS, and six common records cover all
14 fixed scenarios and close to
`records_sha256=e31b215c936ed6693ac84e2bcf2d497a986e6e7cfaf0445637a749836aab83d5`.
The retained run passed output scans and left zero disposable containers,
networks, volumes, or images.
