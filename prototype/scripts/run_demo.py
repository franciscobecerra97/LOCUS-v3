from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from locus.core import enroll, recover, state_separation_audit
from locus.redaction import validate_public_output
from locus.tpass import (
    NativeTpassBackend,
    TpassBackend,
    TpassConcreteBackend,
    TpassSimulator,
)


def sample_cues() -> list[dict]:
    return [
        {
            "location": {
                "provider": "local",
                "record_id": "place-001",
                "name": "Example Library",
                "country": "LU",
            },
            "person": {
                "provider": "local",
                "record_id": "person-001",
                "label": "Example Friend",
            },
        },
        {
            "location": {
                "provider": "local",
                "record_id": "place-002",
                "name": "Example Campus",
                "country": "LU",
            },
            "person": {
                "provider": "local",
                "record_id": "person-002",
                "label": "Example Colleague",
            },
        },
    ]


def main() -> None:
    selected = {flag for flag in ("--simulator", "--concrete") if flag in sys.argv}
    if len(selected) > 1:
        raise SystemExit("select at most one TPASS backend")
    backend: TpassBackend
    if "--simulator" in selected:
        backend = TpassSimulator()
    elif "--concrete" in selected:
        backend = TpassConcreteBackend()
    else:
        backend = NativeTpassBackend()
    private_key = b"synthetic-private-key-material"
    enrollment = enroll(
        user_id="synthetic-user",
        private_key=private_key,
        cues=sample_cues(),
        threshold=2,
        parties=3,
        tpass=backend,
    )
    recovered = recover(
        user_id="synthetic-user",
        backup=enrollment.backup,
        party_records=enrollment.parties[:2],
        cues=sample_cues(),
        tpass=backend,
    )
    output = {
        "recovered_matches": recovered == private_key,
        "metrics": enrollment.metrics,
        "state_separation": state_separation_audit(
            enrollment.backup, enrollment.parties
        ),
    }
    validate_public_output(output)
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
