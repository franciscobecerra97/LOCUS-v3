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

The v2 package boundary and audit are frozen for the current Yi baseline. Later
expanded-system packaging must add newly evidenced profiles through another
reviewed version change, including:

- CuePolicy conformance;
- RecoveryDescriptor and bootstrap tests;
- enrollment-client state disposal;
- clean-client exact-key recovery;
- state and information-flow scenarios;
- same-host and feasible multi-host deployment;
- deterministic evidence processing.

Audit the active v2 source allowlist without creating an archive:

```console
uv run --frozen python tasks.py artifact-package --check
```

The sealed v1 ZIP and external manifest under `dist/` remain unchanged and can
still be verified independently. V2 archive creation remains blocked by its
pending release checklist.

Use fictional inputs and generated credentials only.
