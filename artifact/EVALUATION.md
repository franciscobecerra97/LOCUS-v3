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

This optional command exercises the frozen deployment profile; the current
local UI is a separate in-memory component control. Neither command is the
D023 integrated reference system.

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

Under D023, the future expanded-system evaluation must add one reviewed
end-to-end workflow that begins at the loopback UI/client gateway and traverses
the authenticated admission, discovery, application-storage, resolver, and
five-party container roles. It must cover the declared Yi/aPPSS and 2-of-3/
3-of-5 arms, clean-client recovery, and supported lifecycle transitions before
P8/P9 security, reliability, performance, or resilience results are promoted
as system results. Component tests and the commands above remain supporting
controls. No integrated command is available yet; P7.5 must define and validate
it before this guide can prescribe it.

Audit the active v2 source allowlist without creating an archive:

```console
uv run --frozen python tasks.py artifact-package --check
```

The sealed v1 ZIP and external manifest under `dist/` remain unchanged and can
still be verified independently. V2 archive creation remains blocked by its
pending release checklist.

Use fictional inputs and generated credentials only.
