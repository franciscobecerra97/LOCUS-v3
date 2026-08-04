"""Audit one destroyed integrated client root without printing its contents."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ALLOWED_CLIENT_FILES = {
    "ca.pem",
    "manifest.json",
    "proof-key.bin",
    "tls-cert.pem",
    "tls-key.pem",
    "trust.json",
}

COMMON_SERVICE_FILES = {
    "ca.pem",
    "manifest.json",
    "tls-cert.pem",
    "tls-key.pem",
}
SIGNING_ROLES = {"admission", "operator", "party"}
TRUST_ROLES = {"admission", "operator", "party", "storage-gateway"}


def audit_client_root(root: Path) -> None:
    observed = {
        path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()
    }
    if observed != ALLOWED_CLIENT_FILES:
        raise ValueError("client root contains dynamic or missing state")
    prohibited = (
        "backup",
        "cue",
        "password",
        "protected",
        "recovery-secret",
        "share",
        "sqlite",
        "state",
    )
    if any(any(token in name.lower() for token in prohibited) for name in observed):
        raise ValueError("client root contains prohibited state")


def audit_role_root(root: Path, role: str) -> int:
    if role == "client":
        audit_client_root(root)
        return len(ALLOWED_CLIENT_FILES)
    paths = [path for path in root.rglob("*") if path.is_file()]
    if any(path.is_symlink() for path in root.rglob("*")):
        raise ValueError("role root contains a symbolic link")
    observed = {path.relative_to(root).as_posix() for path in paths}
    if role == "provider":
        if not observed:
            raise ValueError("provider root is unexpectedly empty")
        return len(observed)
    if role == "bootstrap":
        required = {"ca.pem", "manifest.json"}
    else:
        required = set(COMMON_SERVICE_FILES)
        if role in SIGNING_ROLES:
            required.add("signing-key.bin")
        if role in TRUST_ROLES:
            required.add("trust.json")
    if not required <= observed:
        raise ValueError("role root is missing bootstrap-owned state")
    dynamic = observed - required
    allowed_dynamic: set[str] = set()
    if role == "operator":
        allowed_dynamic = {
            "operator.sqlite3",
            "operator.sqlite3-shm",
            "operator.sqlite3-wal",
        }
    elif role == "storage-gateway":
        allowed_dynamic = {
            "admission-replay.sqlite3",
            "admission-replay.sqlite3-shm",
            "admission-replay.sqlite3-wal",
        }
    elif role == "party":
        allowed_dynamic = {
            "admission-replay.sqlite3",
            "admission-replay.sqlite3-shm",
            "admission-replay.sqlite3-wal",
            "party.sqlite3",
            "party.sqlite3-shm",
            "party.sqlite3-wal",
        }
        allowed_dynamic.update(
            name
            for name in dynamic
            if name.startswith("appss/")
            and (
                name.endswith(".sqlite3")
                or name.endswith(".sqlite3-shm")
                or name.endswith(".sqlite3-wal")
            )
        )
    if dynamic - allowed_dynamic:
        raise ValueError("role root contains an unexpected persistent object")
    prohibited = ("cue", "password", "protected", "recovery-secret")
    if any(any(token in name.lower() for token in prohibited) for name in observed):
        raise ValueError("role root exposes a prohibited filename")
    return len(observed)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument(
        "--role",
        choices=(
            "admission",
            "bootstrap",
            "client",
            "operator",
            "party",
            "provider",
            "resolver",
            "s3-role",
            "storage-gateway",
        ),
        default="client",
    )
    args = parser.parse_args()
    files = audit_role_root(args.root, args.role)
    print(
        json.dumps(
            {"files": files, "role": args.role, "status": "clean"}, sort_keys=True
        )
    )


if __name__ == "__main__":
    main()
