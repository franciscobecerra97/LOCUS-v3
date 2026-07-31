# LOCUS Artifact Evaluation

All commands run from the extracted artifact root. Normal output is
privacy-minimized and must not contain cues, password material, party secret
state, wrapping keys, private keys, credentials, or recovered secrets.

## A. Central local smoke

```console
uv sync --frozen
uv run --frozen python tasks.py check
uv run --frozen python tasks.py artifact-smoke
```

Expected result: native, simulator, and explicitly labeled toy flows pass; the
quality and test gates pass; state-separation checks report no prohibited
cross-role state.

### Optional educational walkthrough

```console
uv run --frozen python tasks.py walkthrough
```

Choose three numbered fictional pairs and two of the three TPASS holders.
Selecting the same three pairs for recovery reports `success`; changing one
reports only `generic-rejection` and permits a bounded retry. This command is
interactive teaching material, not an evaluation or evidence-collection path.
It accepts no free-form personal data and retains no state after exit.

## B. Attempt-control negative result

```console
uv run --frozen python tasks.py attempt-model
```

Expected result: the bounded quorum-only scenarios reproduce a conflicting
authorization trace after honest-state rollback and a restored-retirement
trace. The bounded ideal-anchor comparison scenarios report no counterexample
within their declared search bounds. This is a negative result and not a proof.

## C. Retained v2 performance processing

```console
uv run --frozen python tasks.py process-performance --verify
uv run --frozen python tasks.py generate-performance-paper
```

The verification mode regenerates the canonical result in memory and compares
it byte-for-byte with the checked-in output without overwriting it. The expected
canonical processed SHA-256 is:

`462e492795fafdd90a4f39851a612275193603d816f761728afe05e97a470a6b`

The paper-input generator should report the checked-in v2 bundle as unchanged.
The v1 corpus is historical and is not part of the anonymous package.

## D. Docker-backed same-host profiles

With the Docker Linux engine running:

```console
uv run --frozen python tasks.py s3-smoke
uv run --frozen python tasks.py deployment-smoke
```

Expected result: the S3 contract and complete client/resolver/S3/five-party path
pass, output scanning passes, and every exact generated container, network, and
volume is removed.

The three retained snapshot records are aggregate observations. Re-running
their live profiles is optional for a smoke evaluation and required for the
full clean-host evaluation:

```console
uv run --frozen python tasks.py deployment-attack --scenario cloud-snapshot-no-offline-predicate-v1
uv run --frozen python tasks.py deployment-attack --scenario t-minus-one-party-snapshot-no-offline-predicate-v1
uv run --frozen python tasks.py deployment-attack --scenario cloud-plus-t-minus-one-party-snapshot-no-offline-predicate-v1
```

These commands use fresh synthetic development evidence and do not overwrite or
replace the retained v2 records.

## E. Reproduction record

Record only:

- operating-system and runtime versions;
- command name and exit status;
- test counts and skip counts;
- expected aggregate scenario status;
- expected processed/generated hashes;
- output-scan status; and
- exact cleanup status.

Do not retain service logs, snapshot/database bytes, credentials, candidates,
per-candidate outcomes, packet captures, core dumps, exception traces, or local
user paths.
