# LOCUS Reference Prototype

The reference prototype provides Python orchestration around the frozen native
Rust/Ristretto255 Yi TPASS implementation and the separate P5A.2 native aPPSS
core, pinned-library HKDF-SHA-256 and
AES-256-GCM backup cryptography, immutable object-store adapters, authenticated
same-host recovery-party services, synthetic fixtures, and regression tests.

The simulator and fixed safe-prime toy backend are explicitly labeled testing
options. They are not evidence for the expanded reference profile. No backend
is independently audited or production-ready.

## Layout

```text
prototype/
  locus/          implementation modules
  scripts/        demo, walkthrough, and benchmark entry points
  test-vectors/   deterministic cue-policy and resolver-drift vectors
  tests/          unit, integration, failure, and evidence-tooling tests
```

Important implementation modules include:

- `core.py`: LOCUS enrollment and recovery flow;
- `cue_policy.py`: exact reference cue-policy canonicalization;
- `tpass.py`: frozen Yi native adapter plus explicit simulator and toy backends;
- `appss_formats.py`: exact P5A.1 aPPSS framing and strict public formats;
- `crypto.py`: backup encryption and wrapping-key derivation;
- `object_store.py` and `s3_object_store.py`: immutable backup storage;
- `party_store.py`, `party_service.py`, and `party_http.py`: durable party state
  and authenticated local protocol handling;
- `deployment.py`: isolated deployment provisioning and boundary checks;
- `attempt_model.py`: bounded attempt-control counterexample exploration; and
- `performance_processing.py`: deterministic aggregate-result processing.

## Verification

Run from the project root:

```console
uv sync --frozen
uv run --frozen python tasks.py check
uv run --frozen python tasks.py artifact-smoke
```

Optional Docker-backed paths:

```console
uv run --frozen python tasks.py s3-smoke
uv run --frozen python tasks.py deployment-smoke
```

The interactive walkthrough accepts only numbered fictional cue pairs,
generates its own test key, prints redacted stage summaries, and writes no
protocol state:

```console
uv run --frozen python tasks.py walkthrough
```

The project uses generated credentials, temporary databases, synthetic cue
records, and disposable same-host containers. Do not supply real private keys,
accounts, credentials, or personal recovery data.
