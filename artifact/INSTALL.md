# Installation

## Prerequisites

- Git
- pinned `uv` version from `pyproject.toml`
- Python version from `.python-version`
- Rust toolchain from `rust-toolchain.toml`
- Docker only for deployment profiles

Initialize the copied project as a new Git repository, then run:

```console
uv sync --frozen
uv run --frozen python tasks.py check
```

No external cloud or identity-provider account is required for the default
quality gate.
