"""Loopback-published UI container backed by authenticated P7.5 services."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .integrated_client import IntegratedResearchClientApi
from .research_ui import (
    LOCAL_RESEARCH_UI_PROFILE,
    ResearchUiApplication,
    ResearchUiServer,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    application = ResearchUiApplication(
        IntegratedResearchClientApi(role_root=args.root)
    )
    with ResearchUiServer((args.host, args.port), application) as server:
        print(
            json.dumps(
                {
                    "backend": "integrated-services",
                    "status": "ready",
                    "ui_profile": LOCAL_RESEARCH_UI_PROFILE,
                },
                sort_keys=True,
                separators=(",", ":"),
            ),
            flush=True,
        )
        server.serve_forever(poll_interval=0.2)


if __name__ == "__main__":
    main()
