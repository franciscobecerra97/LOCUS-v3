"""P4.2 clean-client network recovery and persistent-surface isolation checks."""

from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import json
import secrets
import sys
from pathlib import Path
from typing import Any, cast

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from . import _tpass_native as native
from .attempt_certificates import AttemptEntry, AuthorizerConfig
from .attempt_coordinator import AttemptCoordinator, AuthorizerPeer
from .codec import encode
from .core import backup_associated_data, derive_wrap_key
from .crypto import hash_bytes, open_sealed
from .deployment import (
    AUTHORIZATION_OPERATION_TIMEOUT_SECONDS,
    _collect_selected,
    _head_from_summaries,
    _select_tpass_subset,
)
from .object_store import backup_digest
from .party_http import RemoteAuthorizerNode, RemotePartyClient
from .party_store import GENESIS_HEAD
from .redaction import validate_public_output

CLEAN_CLIENT_PROFILE = "LOCUS-clean-client-isolation-v1"
MAX_CONFIG_BYTES = 1024 * 1024
MAX_RECOVERY_INPUT_BYTES = 64 * 1024
ALLOWED_CLIENT_FILES = frozenset(
    {"ca.pem", "client-key.pem", "client.pem", "recovery-config.json"}
)


class CleanClientError(ValueError):
    """The clean-client boundary or recovery failed closed."""


def _exact_dict(value: object, fields: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        raise CleanClientError(f"invalid {label}")
    return cast(dict[str, Any], value)


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise CleanClientError("duplicate clean-client configuration field")
        value[key] = item
    return value


def _decode_base64url(value: object, label: str, *, maximum: int) -> bytes:
    if (
        not isinstance(value, str)
        or not value
        or "=" in value
        or any(
            character
            not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
            for character in value
        )
    ):
        raise CleanClientError(f"invalid {label}")
    padding = "=" * ((4 - len(value) % 4) % 4)
    try:
        decoded = base64.b64decode(value + padding, altchars=b"-_", validate=True)
    except (ValueError, binascii.Error) as exc:
        raise CleanClientError(f"invalid {label}") from exc
    if not decoded or len(decoded) > maximum:
        raise CleanClientError(f"invalid {label}")
    return decoded


def _load_config(path: Path) -> dict[str, Any]:
    encoded = path.read_bytes()
    if not encoded or len(encoded) > MAX_CONFIG_BYTES:
        raise CleanClientError("invalid clean-client configuration")
    try:
        value = json.loads(encoded.decode("utf-8"), object_pairs_hook=_unique_object)
        if encode(value) != encoded:
            raise CleanClientError("non-canonical clean-client configuration")
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        raise CleanClientError("invalid clean-client configuration") from exc
    config = _exact_dict(
        value,
        {
            "authorizer_config",
            "backup",
            "parties",
            "recovery_id",
            "tls",
            "version",
        },
        "clean-client configuration",
    )
    if config["version"] != CLEAN_CLIENT_PROFILE:
        raise CleanClientError("unsupported clean-client profile")
    return config


def audit_clean_client_surface(
    client_root: Path,
    *,
    unavailable_enrollment_root: Path,
    forbidden_markers: tuple[bytes, ...],
) -> dict[str, object]:
    """Require an exact public/fresh-key surface and no reachable Client A root."""

    root = client_root.resolve(strict=True)
    enrollment_root = unavailable_enrollment_root.resolve(strict=False)
    if root == enrollment_root or unavailable_enrollment_root.exists():
        raise CleanClientError("enrollment client state remains accessible")
    paths = list(root.iterdir())
    if any(path.is_symlink() or not path.is_file() for path in paths):
        raise CleanClientError("clean-client surface contains a non-file")
    names = {path.name for path in paths}
    if names != ALLOWED_CLIENT_FILES:
        raise CleanClientError("clean-client surface contains inherited state")
    surface = b"\x00".join(path.read_bytes() for path in sorted(paths))
    if any(marker and marker in surface for marker in forbidden_markers):
        raise CleanClientError("clean-client surface contains forbidden state")
    result: dict[str, object] = {
        "files": len(paths),
        "profile": CLEAN_CLIENT_PROFILE,
        "status": "isolated",
    }
    validate_public_output(result)
    return result


def _clients(
    config: dict[str, Any], config_path: Path
) -> tuple[list[RemoteAuthorizerNode], dict[int, RemotePartyClient]]:
    tls = _exact_dict(config["tls"], {"ca", "certificate", "private_key"}, "client TLS")
    if tls != {
        "ca": "ca.pem",
        "certificate": "client.pem",
        "private_key": "client-key.pem",
    }:
        raise CleanClientError("invalid clean-client TLS paths")
    root = config_path.parent
    ca = str(root / tls["ca"])
    certificate = str(root / tls["certificate"])
    private_key = str(root / tls["private_key"])
    parties = config["parties"]
    if not isinstance(parties, list) or len(parties) != 5:
        raise CleanClientError("invalid clean-client party set")
    nodes: list[RemoteAuthorizerNode] = []
    clients: dict[int, RemotePartyClient] = {}
    party_ids: list[int] = []
    for encoded_party in parties:
        party = _exact_dict(
            encoded_party,
            {
                "host",
                "native_role",
                "party_id",
                "port",
                "server_certificate_sha256",
            },
            "clean-client party",
        )
        if not isinstance(party["native_role"], bool):
            raise CleanClientError("invalid clean-client party role")
        constructor = (
            RemotePartyClient if party["native_role"] else RemoteAuthorizerNode
        )
        peer = constructor(
            party_id=party["party_id"],
            host=party["host"],
            port=party["port"],
            server_ca=ca,
            client_certificate=certificate,
            client_private_key=private_key,
            server_certificate_sha256=party["server_certificate_sha256"],
            timeout_seconds=2.0,
        )
        nodes.append(peer)
        party_ids.append(peer.party_id)
        if isinstance(peer, RemotePartyClient):
            clients[peer.party_id] = peer
    if party_ids != [1, 2, 3, 4, 5] or sorted(clients) != [1, 2, 3]:
        raise CleanClientError("invalid clean-client party topology")
    return nodes, clients


def recover_clean_client(config_path: Path, recovery_input: bytes) -> bytes:
    """Recover only through public configuration and authenticated party APIs."""

    if not recovery_input or len(recovery_input) > MAX_RECOVERY_INPUT_BYTES:
        raise CleanClientError("invalid recovery input")
    config_data = _load_config(config_path)
    authorizer_config = AuthorizerConfig.from_dict(config_data["authorizer_config"])
    backup = config_data["backup"]
    if (
        not isinstance(backup, dict)
        or backup.get("bid") != authorizer_config.bid
        or backup.get("epoch") != authorizer_config.epoch
        or backup.get("digest") != authorizer_config.backup_digest
        or backup_digest(backup) != authorizer_config.backup_digest
    ):
        raise CleanClientError("clean-client backup binding mismatch")
    parameters = native.PublicParameters.from_bytes(
        _decode_base64url(
            backup["tpass_public_params"]["parameters"],
            "public parameters",
            maximum=256 * 1024,
        )
    )
    recovery_id = _decode_base64url(
        config_data["recovery_id"], "recovery identifier", maximum=4096
    )
    session = native.begin_recovery(parameters, recovery_id, recovery_input)
    request = bytes(session.request_bytes())
    nodes, clients = _clients(config_data, config_path)
    sid = secrets.token_hex(32)
    coordinator = AttemptCoordinator(
        config=authorizer_config,
        nodes=cast(list[AuthorizerPeer], nodes),
        operation_timeout_seconds=AUTHORIZATION_OPERATION_TIMEOUT_SECONDS,
    )
    summaries = coordinator.state_summaries(
        authorizer_config.bid, authorizer_config.epoch, sid
    )
    installed_index, installed_head, consumed, budget = _head_from_summaries(
        summaries, authorizer_config
    )
    if consumed >= budget:
        raise CleanClientError("recovery is unavailable")
    selected = _select_tpass_subset(clients, summaries, authorizer_config)
    entry = AttemptEntry(
        bid=authorizer_config.bid,
        epoch=authorizer_config.epoch,
        config_digest=authorizer_config.digest,
        log_index=installed_index + 1,
        previous_head=installed_head if installed_index else GENESIS_HEAD,
        sid=sid,
        request_digest=hash_bytes(
            "LOCUS/recovery-request/v1",
            encode(
                {
                    "bid": authorizer_config.bid,
                    "epoch": authorizer_config.epoch,
                    "recovery_id": config_data["recovery_id"],
                    "selected": selected,
                    "sid": sid,
                }
            ),
            request,
        ).hex(),
        tpass_request_hash=hash_bytes("LOCUS/tpass-request-bytes/v1", request).hex(),
        resulting_consumed=consumed + 1,
        effective_budget=budget,
    )
    certificate = coordinator.authorize(entry)
    commitment_results = _collect_selected(
        selected,
        lambda party_id: clients[party_id].prepare_commitment(
            sid=sid,
            authorization_certificate=certificate,
            request=request,
            selected=selected,
        ),
    )
    commitments = [result.commitment for result in commitment_results]
    phase_instances = {
        party_id: result.phase_instance_id
        for party_id, result in zip(selected, commitment_results, strict=True)
    }
    responses = _collect_selected(
        selected,
        lambda party_id: clients[party_id].respond(
            sid=sid,
            phase_instance_id=phase_instances[party_id],
            request=request,
            selected=selected,
            commitments=commitments,
        ),
    )
    gateway = native.aggregate_responses(
        parameters, request, selected, commitments, responses
    )
    group_secret = native.finish_recovery(parameters, session, gateway)
    private_key = open_sealed(
        derive_wrap_key(
            bytes(group_secret), backup["bid"], backup["epoch"], backup["nonce"]
        ),
        backup["ciphertext"],
        aad=backup_associated_data(backup),
    )
    if len(private_key) != 32:
        raise CleanClientError("recovery rejected")
    return private_key


def _public_result(private_key: bytes) -> dict[str, object]:
    public_key = (
        Ed25519PrivateKey.from_private_bytes(private_key)
        .public_key()
        .public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    )
    result: dict[str, object] = {
        "key_sha256": hashlib.sha256(private_key).hexdigest(),
        "profile": CLEAN_CLIENT_PROFILE,
        "public_fingerprint": hashlib.sha256(public_key).hexdigest(),
        "status": "recovered",
    }
    validate_public_output(result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the P4.2 clean client")
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    try:
        request = json.loads(sys.stdin.buffer.read(MAX_RECOVERY_INPUT_BYTES + 1024))
        request = _exact_dict(request, {"recovery_input"}, "clean-client input")
        recovery_input = _decode_base64url(
            request["recovery_input"],
            "recovery input",
            maximum=MAX_RECOVERY_INPUT_BYTES,
        )
        result = _public_result(recover_clean_client(Path(args.config), recovery_input))
    except Exception:
        result = {
            "profile": CLEAN_CLIENT_PROFILE,
            "status": "recovery_rejected",
        }
        validate_public_output(result)
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
        return 1
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "ALLOWED_CLIENT_FILES",
    "CLEAN_CLIENT_PROFILE",
    "CleanClientError",
    "audit_clean_client_surface",
    "recover_clean_client",
]
