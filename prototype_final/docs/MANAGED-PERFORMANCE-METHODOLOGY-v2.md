# Affordable managed performance methodology v2

Status: Assigned by D030 for preparation only. No test or collection has run.

`LOCUS-managed-performance-methodology-v2` replaces only the uncollected P9.3
execution plan. It does not modify D028/D029, their identifiers, or their
absent v1 retained path.

## Exact experiment

The system under test remains the D025 same-host/single-operator Manager-created
Client graph with the local S3-compatible provider, five authorizers, and a
separate 4-of-5 authorization quorum. The four matched arms remain Yi/aPPSS at
2-of-3 and 3-of-5 with their registered policy/resolver pairings.

There are three fresh-project blocks per arm (12 projects). Each project runs
one unmeasured end-to-end warm-up, five measurements each of enrollment,
package transfer plus clean bootstrap, successful recovery, wrong-input
rejection, and one-party-unavailable recovery, and one storage/role snapshot.
This gives 324 scheduled slots: 12 warm-ups and 312 measurements.

The collector builds one image and binds/reuses its immutable image digest for
all twelve projects. A block order is deterministic from the v2 domain, seed,
arm, and slot ID.

## Reporting boundary

Each group reports count, Type-7 median/Q1/Q3, min, max, and arithmetic mean;
the mean is secondary. There is no p5/p95, bootstrap confidence interval,
hypothesis test, pooling, outlier removal, statistical-power claim, or suite
advantage inference. Twelve matched topology/scenario pairs may present
side-by-side medians only.

Repeated timing of below-threshold rejection, party/Client/system restart,
successor transitions, concurrency, and Manager/Client lifecycle is excluded.
Existing functional controls still validate those behaviors but are not v2
performance rows.

## Execution gate

The checked contract records `collection_authorized=false`. Before any run, a
later owner instruction must authorize execution of the prepared tests and
`integrated-check`; a complete exploratory non-retaining run must pass before
retention is considered. No manuscript change is authorized.
