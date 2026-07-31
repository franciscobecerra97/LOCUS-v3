# LOCUS Anonymous Package Installation

## Required for local evaluation

- 64-bit Linux or Windows
- uv 0.11.29
- Rust 1.83.0 with Cargo, rustfmt, and clippy
- Python 3.12.13, installed automatically by uv when supported

Git is not required inside the extracted package. The source gate validates
packaged paths and bytes against `artifact_manifest.json`.

Docker and Docker Compose are required only for the live S3-compatible and
same-host deployment profiles.

## Setup

From the extracted package root:

```console
uv sync --frozen
uv run --frozen python tasks.py check
```

The lockfile must not change. The gate builds the abi3 Python extension with
maturin, checks Python and Rust formatting and static analysis, and runs both
test suites.

The packaged baseline has 152 Python tests with one opt-in live-S3 test skipped,
17 Rust core unit tests, and one Rust fixed-vector integration test. A decrease
or an unexpected skip is a reproduction failure.
