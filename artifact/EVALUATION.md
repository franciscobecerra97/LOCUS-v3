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

Completed P7.7 provides the assigned managed integrated-system workflow,
isolated by D024
under `prototype_final/`, beginning at the loopback Manager UI and traversing a
dynamically created Client, authenticated admission, discovery,
application-storage, resolver, and five-party container roles. From that
directory, use `tasks.py integrated-config` for graph validation and `tasks.py
integrated-smoke` for the disposable pre-evidence matrix. The interactive path
uses one mode-free `integrated-start`; Client creation, enrollment, recovery,
destruction, and normal system stop are Manager/Client UI actions. The
emergency `integrated-stop` preserves role state, while its explicit
`--reset-state` option irreversibly removes exact-project synthetic state. The
gate passed across the declared Yi/aPPSS and 2-of-3/3-of-5 arms, clean-client exact-key
recovery, and supported lifecycle transitions. Its output is ordinary
implementation verification: P8/P9 must collect newly versioned retained
results before any security, reliability, performance, or resilience result is
promoted. Component commands remain supporting controls.

Audit the active v2 source allowlist without creating an archive:

```console
uv run --frozen python tasks.py artifact-package --check
```

The sealed v1 ZIP and external manifest under `dist/` remain unchanged and can
still be verified independently. V2 archive creation remains blocked by its
pending release checklist.

Use fictional inputs and generated credentials only.
