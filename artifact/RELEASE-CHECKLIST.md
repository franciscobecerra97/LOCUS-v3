# Release Checklist

Release authorization: PENDING

The inherited v1 ZIP under `dist/` is a sealed, previously verified baseline
release. This checklist governs a future expanded artifact, which is not yet
approved.

- [ ] New architecture and profile versions are frozen.
- [ ] New artifact allowlist and package identifier are implemented.
- [ ] All active claims have closed evidence.
- [ ] Retained v2 results are included or omitted according to the new
      allowlist and, if included, visibly bound to the exact frozen baseline.
- [ ] Full quality/native gate passes.
- [ ] The versioned P7.5 integrated deployment profile and manifest are frozen.
- [ ] The primary smoke workflow starts the complete service plane and exercises
      the loopback UI/client-gateway API through authenticated admission,
      discovery, application storage, resolver, and five-party containers.
- [ ] Each declared Yi/aPPSS and 2-of-3/3-of-5 artifact arm passes through the
      integrated system; component-only runs are labeled supporting controls.
- [ ] Clean-client workflow passes.
- [ ] State and information-flow positive controls pass.
- [ ] Clean Linux and Windows reproduction passes.
- [ ] Required Docker workflow passes, and any multi-host result states the
      exact P6.4 separation tier actually demonstrated.
- [ ] Anonymity and prohibited-output scans pass.
- [ ] Licenses and third-party inventory are complete.
- [ ] Deterministic archive and extracted-tree validation pass.
- [ ] One unfamiliar reviewer completes the smoke workflow.
- [ ] A qualified independent human confirms the provisional D020 recovery-suite
      mapping assessment before any reviewed selectable-suite release claim.
- [ ] Owner explicitly approves release.
