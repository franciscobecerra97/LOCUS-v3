# Evaluation

The current portable seed should first reproduce the inherited source gate:

```console
uv run --frozen python tasks.py check
uv run --frozen python tasks.py walkthrough
```

Verify the retained paper-facing v2 chain:

```console
uv run --frozen python tasks.py process-performance --verify
uv run --frozen python tasks.py generate-performance-paper
```

The second command must leave byte-identical outputs when the retained
processed result and generated bundle are unchanged.

Optional same-host deployment:

```console
uv run --frozen python tasks.py deployment-smoke
```

The expanded artifact workflow is not yet frozen. Its required future contents
are defined by PLAN P10.3:

- CuePolicy conformance;
- RecoveryDescriptor and bootstrap tests;
- enrollment-client state disposal;
- clean-client exact-key recovery;
- state and information-flow scenarios;
- same-host and feasible multi-host deployment;
- deterministic evidence processing.

The inherited `artifact-package --check` is expected to fail closed on the new
integrated project-management documentation until PLAN P0.4 separates
repository documentation from the next anonymous package. The sealed v1 ZIP
and external manifest under `dist/` can still be verified independently.

Use fictional inputs and generated credentials only.
