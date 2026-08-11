"""Non-secret health probe for a dynamically managed Client UI."""

from __future__ import annotations

import json
import urllib.request

from .managed_client_ui import browser_edge_bind_address


def main() -> None:
    address = browser_edge_bind_address()
    request = urllib.request.Request(f"http://{address}:8080/healthz")
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(request, timeout=2) as response:
        value = json.loads(response.read(64 * 1024))
    if response.status != 200 or value != {"status": "ok"}:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
