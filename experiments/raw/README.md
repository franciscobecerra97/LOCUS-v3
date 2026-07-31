# Retained Aggregate Results

V1 records in this tree are immutable superseded history. V2 records are
retained exact-profile baseline evidence. The description below applies to the
v2 corpus used by the current manuscript and anonymous artifact.

The packaged corpus contains:

- three aggregate-only snapshot-scenario records under `attacks-v2/`; and
- ten randomized blocks containing three same-host performance scenarios under
  `performance-v2/`, for 30 records in total.

Every JSON file is an immutable `LOCUS-compose-profile-evidence-v1` envelope
with exact schema, configuration, runtime, source-revision, and
pseudonymous-host provenance. The corrected records bind the deployed v4/v2
profile and must not be mixed with evidence from another profile version.

The snapshot scenarios are:

- `cloud-snapshot-no-offline-predicate-v1`;
- `t-minus-one-party-snapshot-no-offline-predicate-v1`; and
- `cloud-plus-t-minus-one-party-snapshot-no-offline-predicate-v1`.

The performance scenarios are:

- `enroll-recover-success-v1`;
- `recover-one-party-unavailable-v1`; and
- `recover-wrong-input-v1`.

The files retain only aggregate observations and provenance. They do not retain
snapshot volumes, databases, credentials, candidates, per-candidate outcomes,
core dumps, packet captures, arbitrary service logs, or exception traces.

Do not edit a retained record. A changed procedure or configuration requires a
new versioned experiment identifier and output path.
