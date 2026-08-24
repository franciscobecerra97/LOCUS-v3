# Managed performance preflight v1

Status: Assigned by D031 for preparation only. It has not been executed.

`LOCUS-managed-performance-preflight-v1` is a non-evidence operational gate
for D030's affordable v2 corpus. It runs exactly block 1 of `appss-3of5`: one
warm-up, five repetitions of AP01--AP05, and one AP06 snapshot. Total: 27
slots, 26 measured, one disposable project, and one image build.

Run it only after a later execution instruction:

```console
uv run --frozen python tasks.py integrated-performance-evidence --preflight
```

The option is mutually exclusive with `--retain`. It produces ephemeral
pass/fail output only, cannot publish a directory, cannot be processed as a
partial v2 corpus, and cannot support a paper claim.

After targeted checks and this preflight pass, the affordable path uses one
complete `--retain` run. That run validates every staged block and atomically
seals the 324-slot corpus only after full hash closure. The ordinary command
without an option remains an optional full-schedule developer run; D031 no
longer requires it before retention.
