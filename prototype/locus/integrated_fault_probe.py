"""Fixed, bounded operator probes for the disposable P7.5 system gate."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .codec import encode
from .contracts import CurrentDescriptorPointer
from .integrated_client import SUBJECT_ID, IntegratedResearchClientApi
from .integrated_rpc import IntegratedRpcError
from .provider_gateway import current_pointer_object_key, encode_pointer_cas
from .recovery_descriptor import CURRENT_POINTER_VERSION


def stale_cas(*, root: Path, receipt: object) -> None:
    client = IntegratedResearchClientApi(role_root=root)
    epoch = client._load(receipt)
    stale_envelope = json.loads(epoch.pointer_bytes)
    signature = str(stale_envelope["signature"]["value"])
    stale_envelope["signature"]["value"] = signature[:-1] + (
        "0" if signature[-1] != "0" else "1"
    )
    expected = CurrentDescriptorPointer(CURRENT_POINTER_VERSION, encode(stale_envelope))
    replacement_envelope = json.loads(epoch.pointer_bytes)
    replacement_signature = str(replacement_envelope["signature"]["value"])
    replacement_envelope["signature"]["value"] = (
        replacement_signature[:-2]
        + ("0" if replacement_signature[-2] != "0" else "1")
        + replacement_signature[-1]
    )
    replacement = CurrentDescriptorPointer(
        CURRENT_POINTER_VERSION, encode(replacement_envelope)
    )
    try:
        client._storage(
            operation="compare_and_swap",
            object_key=current_pointer_object_key(
                SUBJECT_ID, epoch.reference, epoch.context.recovery_id
            ),
            reference=epoch.reference,
            recovery_handle=epoch.context.recovery_id,
            payload=encode_pointer_cas(expected=expected, replacement=replacement),
        )
    except IntegratedRpcError as exc:
        if str(exc) == "object_stale":
            return
        raise ValueError("unexpected stale-CAS result") from exc
    raise ValueError("stale current-pointer CAS was accepted")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("operation", choices=("stale-cas",))
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    encoded = sys.stdin.buffer.read(32_769)
    if not encoded or len(encoded) > 32_768:
        raise SystemExit("invalid probe input")
    value = json.loads(encoded)
    if not isinstance(value, dict) or set(value) != {"receipt"}:
        raise SystemExit("invalid probe input")
    if args.operation == "stale-cas":
        stale_cas(root=args.root, receipt=value["receipt"])
    print(json.dumps({"status": "stale_rejected"}, sort_keys=True))


if __name__ == "__main__":
    main()
