# LOCUS Artifact Installation

## Required for the local evaluation

- 64-bit Linux or Windows
- uv 0.11.29
- Rust 1.83.0 with Cargo, rustfmt, and clippy
- Python 3.12.13, installed automatically by uv when supported

Git is required for development-checkout hygiene checks but is not required
inside the extracted anonymous artifact. The extracted gate validates source
paths and bytes against `artifact_manifest.json`.

Docker and Docker Compose are required only for the live S3 and complete
same-host deployment profiles.

## Setup

From the extracted artifact root:

```console
uv sync --frozen
```

The lockfile must not change. Then run:

```console
uv run --frozen python tasks.py check
```

This builds the local abi3 Python extension with maturin, checks Python and Rust
formatting/static analysis, and runs both test suites.

## Expected local gate

The packaged baseline has:

- 151 Python tests with one opt-in live-S3 test skipped;
- 17 Rust core unit tests;
- one Rust fixed-vector integration test; and
- passing Ruff, mypy, rustfmt, and clippy checks.

A decrease or an unexpected skip is a reproduction failure and should be
recorded.

## Docker setup

Start the Docker Linux engine before running Docker-backed profiles. The
artifact uses only generated synthetic credentials and disposable, isolated
same-host containers, networks, and volumes. It does not contact external
targets; normal dependency and pinned image retrieval may use their official
registries.
