"""Privacy-safe mTLS health probe for integrated service containers."""

from __future__ import annotations

import argparse
from pathlib import Path

from .integrated_rpc import rpc_request


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    result = rpc_request(
        endpoint=args.endpoint,
        path="/health",
        role_root=args.root,
        value={},
        timeout=2,
    )
    if result.get("status") != "ready":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
