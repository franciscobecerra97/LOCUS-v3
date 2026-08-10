# LOCUS Final Integrated Prototype

This directory is the self-contained active implementation workspace selected
by D024 for P8 and later LOCUS implementation, assurance, evidence, and
artifact work. It contains only the dependency-complete D023 integrated
reference system and its focused controls. Existing root implementations remain
historical or component controls and are not dependencies of this workspace.

## Scope

The prototype provides one same-host Docker system with:

- an ephemeral loopback UI/client gateway;
- local synthetic admission and proof-key-bound capabilities;
- operator-signed discovery, descriptors, bundles, receipts, and current state;
- an application storage gateway and local S3-compatible provider;
- the resolver service required by the frozen composite CuePolicy;
- five authenticated authorizer/recovery-party services;
- selectable Yi and aPPSS suites at 2-of-3 and 3-of-5;
- a separate 4-of-5 authorization quorum;
- all four registered CuePolicies; and
- clean-client recovery plus same-suite and cross-suite successors.

This remains a one-host, one-Docker-engine, one-operator research profile. It
does not establish host separation, independent administration, real-provider
behavior, usability, production security, forensic erasure, or independent
cryptographic review.

## Prerequisites

- Python 3.12
- uv 0.11.29
- Rust/Cargo for `integrated-check`
- Docker with Compose for the deployment commands

Run all commands from this directory.

## Command surface

Install the pinned environment:

```console
uv sync --frozen
```

Run the focused Python/native quality gate:

```console
uv run --frozen python tasks.py integrated-check
```

Validate the canonical manifest and both resolved Compose graphs:

```console
uv run --frozen python tasks.py integrated-config
```

Start enrollment Client A and the service plane:

```console
uv run --frozen python tasks.py integrated-start --mode enrollment
```

Open the printed loopback URL, complete synthetic enrollment, and retain only
the public receipt. Replace Client A with isolated recovery Client B:

```console
uv run --frozen python tasks.py integrated-start --mode recovery
```

Stop the ephemeral client containers while retaining the service plane:

```console
uv run --frozen python tasks.py integrated-stop
```

Remove the exact project, volumes, and locally built image:

```console
uv run --frozen python tasks.py integrated-stop --destroy
```

Run the complete disposable pre-evidence acceptance matrix:

```console
uv run --frozen python tasks.py integrated-smoke
```

## Directory layout

| Path | Purpose |
| --- | --- |
| `tasks.py` | Only supported executor; exposes five `integrated-*` commands |
| `locus/` | Dependency-complete integrated Python implementation and UI assets |
| `appss-core/` | Native aPPSS core and public vector |
| `tpass-core/` | Frozen native Yi core and vector |
| `tpass-python/` | Narrow PyO3 binding for both native suites |
| `deploy/` | Integrated Dockerfile, Compose graph, and canonical manifest |
| `tests/` | Focused manifest, bootstrap, isolation, and service-boundary tests |
| `docs/schemas/` | Integrated configuration schema |

## Evidence boundary

`integrated-check`, `integrated-config`, and `integrated-smoke` produce ordinary
development output only. They do not create retained P8/P9 evidence. Future
collection must first assign the applicable schema, identifier, positive
controls, provenance, output-safety policy, and versioned result path.

Use generated keys, fictional cues, generated credentials, and disposable
local services only. Never supply real private keys, credentials, accounts, or
personal recovery information.
