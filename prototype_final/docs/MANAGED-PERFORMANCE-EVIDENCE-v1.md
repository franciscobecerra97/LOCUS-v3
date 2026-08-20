# Managed Performance Evidence v1

D029 assigns the non-collecting P9.2 contracts for the exact D028 methodology.
The evidence profile, instrumentation, scenario manifest, processor, three raw
result families, summary, matched comparison, and closing corpus manifest are
Assigned. No P9 measurement has been collected.

## Immutable schedule

| IDs | Scope | Scheduled | Measured |
| --- | --- | ---: | ---: |
| MP00 | One complete warm-up for each arm/block | 40 | 0 |
| MP01--MP06 | Six central scenarios, four arms, 30 each | 720 | 720 |
| MP07--MP11 | Five structural scenarios, four arms, 10 each | 200 | 200 |
| MP12 | Four successor directions, two topologies, 10 each | 80 | 80 |
| MP13 | Four arms, concurrency 1/2/4, 10 batches each | 120 | 120 |
| MP14--MP19 | Six suite-neutral lifecycle scenarios, 10 each | 60 | 60 |
| **Total** |  | **1,220** | **1,180** |

`managed-performance-scenarios-v1.json` binds the compact schedule and the
SHA-256 digest of its deterministic 1,220-slot expansion. Yi, aPPSS, and common
observations have distinct result identifiers. A successor observation uses
its predecessor suite family and also binds the target arm and direction.

## Observation and invalid-attempt rules

Every attempt binds the D025 deployment/configuration, D028 methodology,
instrumentation, scenario slot, source state, image and graph, service identity
set, network topology, provider, API/profile versions, exact suite/topology/
policy/resolver/holder/quorum arm, block/seed, and pseudonymous host/project/
Client/package set. The accepted statuses are:

- `warmup-passed`;
- `valid-success`;
- `valid-expected-rejection`; and
- `infrastructure-invalid`.

An invalid attempt retains only a bounded category. It has no
measurement metrics and never enters a valid distribution. A later attempt is
a new exclusive record whose `replacement_of_sha256` binds the immediately
prior invalid attempt. Attempts are contiguous; a valid result can never be
retried. The processor refuses an omitted slot, an unlinked retry, an invalid
terminal slot, or more than one accepted terminal observation.

Slow valid operations and expected protocol failures remain valid. There is no
outlier removal. The final summary discloses every invalid-attempt count.

## Metrics and output safety

The client monotonic clock supplies end-to-end nanoseconds. Only the fixed
applicable non-overlapping phase set is accepted and its total may not exceed
end-to-end latency. Body and persisted bytes reconcile against fixed role
sets. Host-loopback UI HTTP latency excludes rendering. Lifecycle and
concurrency fields are accepted only for their registered scenarios; the
concurrency rate uses integer milli-operations per second.

Retained objects prohibit payloads, cues/canonical cue bytes, passwords,
recovery secrets, protected/private keys, credentials, request/response bodies,
logs, traces, packet captures, host paths, stable machine/account identifiers,
and developer identity. Fixed positive controls cover clock/phase/byte
integrity, schedule and graph binding, expected outcomes, failure schedules,
identity rotation, one-Client serialization, invalid linkage, output canaries,
cleanup, and hash closure.

## Processing and comparison

The processor first requires all 1,220 terminal slots. It emits 70 groups:
suite/topology/scenario groups, direction-specific successor groups,
level-specific concurrency groups, and suite-neutral lifecycle groups. It uses
Type-7 quantiles, n=30 p5/p95/range plus the deterministic 10,000-resample 95%
median interval, n=10 quartiles/range, secondary-only means, and no outlier
removal.

The comparison contains 28 matched Yi/aPPSS pairs for MP01--MP11 and MP13 at
each topology/concurrency level. It reports shared metrics side by side, never
pools samples, and performs no hypothesis test. The aPPSS-only per-server
initialization phase remains in the aPPSS summary rather than being falsely
matched to Yi.

## Retention gate

P9.3 alone may create:

```text
evidence/retained/managed-performance-v1/
  raw/<slot-id>/attempt-<NN>.json
  processed/summary.json
  derived/comparison.json
  corpus-manifest.json
```

Every file is exclusive-create and immutable. Until the final manifest exists
and closes all raw/processed/derived digests, the directory is unsealed and
cannot support a result. P9.2 provides no collector or collection command, and
tests assert that the retained root is absent.

This is same-host, single-operator, local-provider systems methodology. It is
not evidence of CPU/energy/WAN/real-provider behavior, production capacity,
scalability, independent administration, cryptographic proof, usability, or a
suite advantage. No manuscript change is authorized.
