# Affordable managed performance evidence v2

Status: Assigned by D030 for preparation only. No staging directory, retained
directory, test execution, exploratory run, or P9 result exists.

D031 changes only the execution prerequisite. It requires the separate
non-evidence `LOCUS-managed-performance-preflight-v1` instead of a duplicate
complete non-retaining run. The v2 formats and 324-slot corpus are unchanged.

## Contract family

- `LOCUS-managed-performance-evidence-profile-v2`
- `LOCUS-managed-performance-instrumentation-v2`
- `LOCUS-managed-performance-scenario-manifest-v2`
- `LOCUS-managed-performance-result-yi-v2`
- `LOCUS-managed-performance-result-appss-v2`
- `LOCUS-managed-performance-processor-v2`
- `LOCUS-managed-performance-summary-v2`
- `LOCUS-managed-performance-comparison-v2`
- `LOCUS-managed-performance-corpus-manifest-v2`
- coordination-only `LOCUS-managed-performance-checkpoint-v1`

AP00 is the unmeasured warm-up. AP01--AP05 are the five central scenarios;
AP06 is the storage/role snapshot. Yi and aPPSS raw records and summary groups
remain disjoint. The processor requires every terminal slot and emits 24
groups and 12 non-pooled descriptive comparison pairs.

## Resumption and publication

The final path is:

```text
evidence/retained/managed-performance-v2/
```

During an explicitly authorized retained run, complete arm/block raw records
may be exclusive-created under
`evidence/retained/.managed-performance-v2-staging/`. Its checkpoint is mutable
coordination metadata, not evidence. Resume requires identical clean-source,
methodology/scenario, image, graph, host-tier, and pseudonymous-host bindings.
An active interrupted block is exact-cleaned, classified as a linked
`host-interruption`, and retried. The checkpoint is removed before atomic final
publication. A directory without the closing manifest, or containing the
checkpoint, is not a corpus.

Raw records retain only bounded aggregate timing/byte metrics, outcomes,
pseudonyms, and public provenance digests. Cues, canonical cue bytes,
passwords, recovery secrets, protected/private keys, credentials, payloads,
request/response bodies, logs, traces, packet captures, host paths, and stable
identities are prohibited.

## Interpretation

Even a later complete v2 corpus supports only descriptive same-host core
operation cost under the exact D025 graph. It does not establish scalability,
throughput, lifecycle/restart/successor latency distributions, WAN/external
provider behavior, production capacity, independent administration, usability,
or suite superiority.
