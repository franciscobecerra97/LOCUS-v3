# Managed Performance Methodology v1

`LOCUS-managed-performance-methodology-v1` is the D028/P9.1 methodology for
the exact D025 Manager-created Client system. The canonical checked contract is
`managed-performance-methodology-v1.json`; its Python validator deliberately
accepts only that exact object. P9.1 freezes the experiment before collection.
It assigns no result identifier or retained path and authorizes no measurement.

## System and matched arms

The primary system is `LOCUS-integrated-manager-deployment-v1` with
`LOCUS-integrated-manager-config-v1`, five authorizers, the distinct 4-of-5
authorization quorum, one transient Manager-created Client, and the local
S3-compatible provider on one host under one operator. The four arms are:

| Arm | Suite | Recovery holders | Policy and resolver |
| --- | --- | --- | --- |
| `yi-2of3` | Yi | 2 of parties 1--3 | canonical-email / NoResolver |
| `appss-2of3` | aPPSS | 2 of parties 1--3 | canonical-email / NoResolver |
| `yi-3of5` | Yi | 3 of parties 1--5 | location-person / deterministic directory |
| `appss-3of5` | aPPSS | 3 of parties 1--5 | location-person / deterministic directory |

Every `(arm, block)` uses a fresh disposable project. There are ten blocks with
fixed seeds `2026081701` through `2026081710`. Arm order is the ascending SHA-256
order of the methodology's fixed domain, seed, and arm identifier. Within one
topology block, Yi and aPPSS use the same synthetic protected-key and input
class. Each arm/block first executes one complete enrollment, package export/
import, clean bootstrap, and recovery warm-up; it is never measured.

## Scheduled observations

Each central scenario has 30 observations per arm, three in each block:
enrollment, package export/import, clean-client bootstrap, successful recovery,
wrong-input rejection, and one-party-unavailable recovery.

Each structural scenario has ten observations per arm, one in each block:
below-threshold rejection, party restart and recovery, Client restart/reimport/
recovery, preserved-system restart, and aggregate storage/role snapshots.
Each of Yi-to-Yi, Yi-to-aPPSS, aPPSS-to-Yi, and aPPSS-to-aPPSS successor
directions has ten observations at each topology. Concurrency uses levels 1, 2,
and 4 with ten batches per arm and level. Because one managed Client serializes
its operations, this reports that boundary and is not a scalability result.

Manager/system startup and Client create, stop, start, restart, and destroy each
receive ten suite-neutral observations.

## Failure schedules

- At 2-of-3, stop party 1 and recover with parties 2 and 3.
- At 3-of-5, stop party 1 and recover with parties 2, 3, and 4.
- Below threshold, supply exactly `k-1` holders and accept only bounded failure.
- For restart, restart party 1, await authenticated health, then recover with a
  threshold subset containing party 1.

These schedules do not redefine the separate 4-of-5 authorization quorum.

## Metrics and analysis

Client-observed end-to-end and non-overlapping phase latency use a monotonic
clock. Phases cover policy, resolver, suite initialization (including aPPSS
per-server initialization), encryption/upload, provisioning, descriptor,
authorization, recovery, and successor work. Application body bytes are
reported by role and in aggregate; persisted bytes are aggregate role totals.
Manager/Client lifecycle latency is separate. Host-loopback UI HTTP round trip
is separately labeled and excludes browser rendering. Concurrency reports
batch completion latency and operations per second.

For 30-observation rows, report count, median, Type-7 quartiles, p5/p95, range,
and a deterministic 10,000-resample 95% bootstrap interval for the median. For
ten-observation rows, report count, median, Type-7 quartiles, and range. Means
are secondary only. There is no outlier removal: slow valid operations and
expected failures remain. Infrastructure-invalid observations must be retained
as invalid under the future P9.2 schema, never silently retried or overwritten,
excluded from the valid distribution with the count disclosed, and linked to
any explicit replacement.

## Interpretation and collection gate

This profile measures no CPU, energy, WAN, real-provider, browser-rendering, or
production capacity property. It cannot establish scalability, host
separation, independent administration, Internet behavior, or usability.
P9.4 multi-host, WAN, or external-provider work needs separate authorization.

P9.2 must separately assign result identifiers, schemas, positive controls,
privacy/provenance fields, and append-only paths before any P9.3 collection.
P8 state/flow corpora and historical v2 results remain disjoint. No manuscript
wording is authorized by D028 or P9.1.
