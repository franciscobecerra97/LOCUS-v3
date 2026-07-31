# Generated Paper Inputs

The active manuscript consumes manifest-bound generated inputs from this
directory. `performance-v2/` is the retained baseline bundle:

```text
performance-v2/latency_rows.tex
performance-v2/phase_rows.tex
performance-v2/traffic_rows.tex
performance-v2/storage_rows.tex
performance-v2/manifest.json
```

Do not hand-edit generated rows. Regenerate and verify the v2 bundle from the
repository root:

```console
uv run --frozen python tasks.py process-performance --verify
uv run --frozen python tasks.py generate-performance-paper
```

The generator accepts only the canonical processed result at
`experiments/processed/performance-v2/summary.json`. The manifest binds the
processed-source digest, experiment identifier, source revision, pseudonymous
host, processing configuration, and digest of every row file. Identical
regeneration is idempotent; the artifact command does not replace changed
outputs silently.

The tracked `performance-v1/` and legacy benchmark/guessing row files are
superseded historical material and are not included by `paper/main.tex`. New
profiles must use new versioned generated directories.

The complete manuscript is present in this integrated repository but remains
outside the anonymous artifact allowlist. Any change to manuscript inputs or
reported values requires an exact owner-approved manuscript delta.
