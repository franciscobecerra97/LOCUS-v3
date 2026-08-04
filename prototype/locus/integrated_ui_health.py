"""Loopback-only UI health probe."""

from __future__ import annotations

import json
import urllib.request


def main() -> None:
    request = urllib.request.Request("http://127.0.0.1:8080/api/v1/catalog")
    with urllib.request.urlopen(request, timeout=2) as response:  # noqa: S310
        value = json.loads(response.read(64 * 1024))
    if response.status != 200 or value.get("status") != "ready":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
