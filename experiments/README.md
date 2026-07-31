# LOCUS Experiment Data

This directory contains the privacy-safe inherited experiment material and is
the versioned home for future approved evidence:

- `raw/` contains immutable, schema-validated aggregate records from the
  snapshot and same-host performance evaluations.
- `processed/` contains a deterministic summary derived from the retained
  performance records.

No record contains credentials, secret protocol state, real cue data,
candidate values, per-candidate outcomes, snapshots, databases, service logs,
packet captures, core dumps, or exception traces.

The v1 records are immutable superseded history. The retained v2 corpus is
baseline evidence only for the exact frozen profile and provenance it records.
New CuePolicy, descriptor, admission, topology, provider, lifecycle, UI, or
clean-client results require new identifiers and paths. Never mix inherited and
changed profiles in one processed corpus.

Run the retained-v2 verification pipeline from the repository root:

```console
uv run --frozen python tasks.py process-performance --verify
uv run --frozen python tasks.py generate-performance-paper
```
