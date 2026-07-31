# LOCUS Anonymous Package Evaluation

All commands run from the extracted package root. Output must not contain cues,
password material, party secret state, wrapping keys, private keys, credentials,
or recovered secrets.

## Local gates

```console
uv sync --frozen
uv run --frozen python tasks.py check
uv run --frozen python tasks.py artifact-smoke
```

Expected result: the native, simulator, and explicitly labeled toy flows pass;
the quality and test gates pass; and state-separation checks report no
prohibited cross-role state.

## Retained v2 processing

```console
uv run --frozen python tasks.py process-performance --verify
uv run --frozen python tasks.py generate-performance-paper
```

Verification regenerates the canonical result in memory and compares it
byte-for-byte with the retained output. The expected processed SHA-256 is
`462e492795fafdd90a4f39851a612275193603d816f761728afe05e97a470a6b`.
The generator must report the checked-in performance bundle as unchanged.

## Optional same-host profiles

With Docker Linux and Docker Compose running:

```console
uv run --frozen python tasks.py s3-smoke
uv run --frozen python tasks.py deployment-smoke
```

These profiles use generated synthetic credentials and disposable local
resources. Do not use real keys, accounts, cues, or personal data.

Record only runtime versions, commands and exit status, test/skip counts,
aggregate scenario status, expected hashes, output-scan status, and cleanup
status. Do not retain service logs, databases, credentials, candidates,
per-candidate outcomes, packet captures, core dumps, exception traces, or local
user paths.
