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
- [ ] Clean-client workflow passes.
- [ ] State and information-flow positive controls pass.
- [ ] Clean Linux and Windows reproduction passes.
- [ ] Required Docker/multi-host workflow passes.
- [ ] Anonymity and prohibited-output scans pass.
- [ ] Licenses and third-party inventory are complete.
- [ ] Deterministic archive and extracted-tree validation pass.
- [ ] One unfamiliar reviewer completes the smoke workflow.
- [ ] Owner explicitly approves release.
