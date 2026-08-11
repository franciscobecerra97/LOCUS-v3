"""Loopback health probe for the managed deployment's Manager UI."""

from __future__ import annotations

import json
import urllib.request


def main() -> None:
    request = urllib.request.Request("http://127.0.0.1:8080/api/manager/v1/session")
    with urllib.request.urlopen(request, timeout=2) as response:  # noqa: S310
        value = json.loads(response.read(32 * 1024))
    if response.status != 200 or value.get("status") != "ready":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
