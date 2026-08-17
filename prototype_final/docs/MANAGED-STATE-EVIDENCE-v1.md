# Managed State Evidence Profile v1

Status: Assigned by owner-approved D026 on 2026-08-17. Collection is allowed
only after this profile, its schemas, collector, tests, and command surface are
committed and the complete source tree is clean.

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
