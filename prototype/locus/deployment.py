"""Provision and exercise the isolated local LOCUS Compose deployment."""

from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import http.client
import ipaddress
import json
import math
import os
import re
import secrets
import ssl
import statistics
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor, wait
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, cast

from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

from . import _tpass_native as native
from .attempt_certificates import AttemptEntry, AuthorizerConfig, AuthorizerSigner
from .attempt_coordinator import AttemptCoordinator, AuthorizerPeer, AuthorizerState
from .codec import encode
from .core import (
    SECURITY_POLICY_VERSION,
    backup_associated_data,
    derive_wrap_key,
)
from .crypto import hash_bytes, open_sealed, random_bytes, seal
from .cue_policy import canonical_recovery_input
from .deployed_profile import (
    BACKUP_VERSION,
    CONTEXT_POLICY_VERSION,
    DEPLOYMENT_VERSION,
)
from .epoch_lifecycle import EpochActivationCertificate, EpochTransition
from .object_store import (
    BackupReference,
    backup_digest,
    decode_backup_object,
    encode_backup_object,
)
from .party_http import PartyProtocolError, RemoteAuthorizerNode, RemotePartyClient
from .party_store import GENESIS_HEAD, Conflict, PartyStoreError
from .redaction import validate_public_output
from .s3_object_store import S3BackupObjectStore

BENCHMARK_VERSION = "LOCUS-compose-benchmark-v1"
PERFORMANCE_CLIENT_VERSION = "LOCUS-performance-client-samples-v1"
PERFORMANCE_RESULT_VERSION = "LOCUS-compose-performance-result-v1"
PROVISION_METRIC_VERSION = "LOCUS-provision-metric-v1"
STORAGE_METRIC_VERSION = "LOCUS-storage-metric-v1"
RESOLVER_VERSION = "LOCUS-resolver-fixture-v1"
TPASS_ENCODING = "LOCUS-TPASS-wire-v1"
TPASS_BACKEND = "yi-zk-ristretto255-native-v1"
PARTY_COUNT = 5
TPASS_PARTIES = 3
TPASS_THRESHOLD = 2
ATTEMPT_BUDGET = 4
PARTY_PORT = 8443
RESOLVER_PORT = 8080
RUNTIME_ROOT = "/var/lib/locus"
AUTHORIZATION_OPERATION_TIMEOUT_SECONDS = 45.0
RECOVERY_PHASE_TIMEOUT_SECONDS = 12.0
PERFORMANCE_RUNS = 3
PERFORMANCE_SCENARIOS = (
    "enroll-recover-success-v1",
    "recover-one-party-unavailable-v1",
    "recover-wrong-input-v1",
)


def performance_scenario_order(seed: int) -> tuple[str, ...]:
    """Return the versioned deterministic scenario order for one block seed."""

    if (
        not isinstance(seed, int)
        or isinstance(seed, bool)
        or not 0 <= seed <= 2**64 - 1
    ):
        raise DeploymentError("invalid performance orchestration seed")
    encoded_seed = seed.to_bytes(8, "big")
    return tuple(
        sorted(
            PERFORMANCE_SCENARIOS,
            key=lambda scenario: hash_bytes(
                "LOCUS/performance-scenario-order/v1",
                encoded_seed,
                scenario.encode("ascii"),
            ),
        )
    )


class DeploymentError(Exception):
    """The local deployment could not be provisioned or exercised safely."""


def _exact_dict(value: object, fields: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        raise DeploymentError(f"invalid {label}")
    return value


def _json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=True,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("ascii")


def _load_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="ascii"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DeploymentError("invalid deployment data") from exc


def _base64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _decode_base64url(value: object) -> bytes:
    if not isinstance(value, str) or not value or "=" in value:
        raise DeploymentError("invalid deployment encoding")
    padding = "=" * ((4 - len(value) % 4) % 4)
    try:
        decoded = base64.b64decode(value + padding, altchars=b"-_", validate=True)
    except (ValueError, binascii.Error) as exc:
        raise DeploymentError("invalid deployment encoding") from exc
    if _base64url(decoded) != value:
        raise DeploymentError("noncanonical deployment encoding")
    return decoded


def _write_new(path: Path, data: bytes, *, mode: int) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
    try:
        with os.fdopen(descriptor, "wb", closefd=False) as output:
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
    finally:
        os.close(descriptor)
    path.chmod(mode)


def _private_key_pem(key: Ed25519PrivateKey) -> bytes:
    return key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )


def _certificate_pem(certificate: x509.Certificate) -> bytes:
    return certificate.public_bytes(serialization.Encoding.PEM)


def _certificate_fingerprint(certificate: x509.Certificate) -> str:
    return hashlib.sha256(
        certificate.public_bytes(serialization.Encoding.DER)
    ).hexdigest()


def _create_ca() -> tuple[Ed25519PrivateKey, x509.Certificate]:
    key = Ed25519PrivateKey.generate()
    subject = x509.Name(
        [x509.NameAttribute(NameOID.COMMON_NAME, "LOCUS synthetic deployment CA")]
    )
    now = datetime.now(UTC)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(days=1))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .sign(key, algorithm=None)
    )
    return key, certificate


def _create_leaf(
    *,
    name: str,
    ca_key: Ed25519PrivateKey,
    ca_certificate: x509.Certificate,
    server: bool,
) -> tuple[Ed25519PrivateKey, x509.Certificate]:
    key = Ed25519PrivateKey.generate()
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, name)])
    now = datetime.now(UTC)
    builder = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(ca_certificate.subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(days=1))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(
            x509.ExtendedKeyUsage(
                [
                    ExtendedKeyUsageOID.SERVER_AUTH
                    if server
                    else ExtendedKeyUsageOID.CLIENT_AUTH
                ]
            ),
            critical=False,
        )
    )
    if server:
        builder = builder.add_extension(
            x509.SubjectAlternativeName(
                [
                    x509.DNSName(name),
                    x509.DNSName("localhost"),
                    x509.IPAddress(ipaddress.ip_address("127.0.0.1")),
                ]
            ),
            critical=False,
        )
    return key, builder.sign(ca_key, algorithm=None)


def _load_fixture(path: Path) -> list[dict[str, Any]]:
    value = _load_json(path)
    if (
        not isinstance(value, dict)
        or set(value) != {"cues", "version"}
        or value["version"] != RESOLVER_VERSION
        or not isinstance(value["cues"], list)
    ):
        raise DeploymentError("invalid resolver fixture")
    cues = value["cues"]
    canonical_recovery_input(cues)
    return cues


def _claim_empty_layout(party_roots: list[Path], client_root: Path) -> bool:
    marker = client_root / "deployment.json"
    if marker.is_file() and all(
        (root / "service.json").is_file() for root in party_roots
    ):
        audit_layout(party_roots, client_root)
        return False
    roots = [*party_roots, client_root]
    if any(root.exists() and any(root.iterdir()) for root in roots):
        raise DeploymentError("partial deployment state requires clean volumes")
    for root in roots:
        root.mkdir(parents=True, exist_ok=True)
        root.chmod(0o700)
    return True


def _validate_deployed_backup_profile(backup: object) -> dict[str, Any]:
    """Require the exact backup and cue-policy versions used by this deployment."""

    if not isinstance(backup, dict) or backup.get("version") != BACKUP_VERSION:
        raise DeploymentError("unsupported deployed backup version")
    context_policy = backup.get("context_policy")
    if (
        not isinstance(context_policy, dict)
        or set(context_policy) != {"version"}
        or context_policy.get("version") != CONTEXT_POLICY_VERSION
    ):
        raise DeploymentError("unsupported deployed context policy")
    return backup


def _chown_layout(roots: list[Path], uid: int | None, gid: int | None) -> None:
    if uid is None or gid is None:
        return
    chown = getattr(os, "chown", None)
    if chown is None:
        raise DeploymentError("ownership changes are unsupported")
    for root in roots:
        chown(root, uid, gid)
        for path in root.iterdir():
            chown(path, uid, gid)


def provision(
    *,
    party_roots: list[Path],
    client_root: Path,
    fixture_path: Path,
    owner_uid: int | None = None,
    owner_gid: int | None = None,
) -> str:
    """Create one complete role-separated synthetic deployment layout."""

    if len(party_roots) != PARTY_COUNT or len(set(party_roots)) != PARTY_COUNT:
        raise DeploymentError("exactly five distinct party roots are required")
    if not _claim_empty_layout(party_roots, client_root):
        return "existing"
    cues = _load_fixture(fixture_path)
    recovery_input = canonical_recovery_input(cues)
    bid = random_bytes(16).hex()
    epoch = 1
    recovery_identifier = b"LOCUS-compose-recovery-v1:" + bytes.fromhex(bid)
    parameters, states, group_secret = native.setup(
        recovery_identifier,
        recovery_input,
        TPASS_THRESHOLD,
        TPASS_PARTIES,
    )
    encoded_parameters = _base64url(bytes(parameters.to_bytes()))
    encoded_states = {
        state.party_id: _base64url(bytes(state.to_secret_bytes())) for state in states
    }
    nonce = random_bytes(16).hex()
    backup: dict[str, Any] = {
        "version": BACKUP_VERSION,
        "bid": bid,
        "epoch": epoch,
        "nonce": nonce,
        "tpass_public_params": {
            "backend": TPASS_BACKEND,
            "encoding": TPASS_ENCODING,
            "parameters": encoded_parameters,
            "threshold": TPASS_THRESHOLD,
            "parties": TPASS_PARTIES,
        },
        "context_policy": {"version": CONTEXT_POLICY_VERSION},
        "security_policy": {
            "version": SECURITY_POLICY_VERSION,
            "max_attempts": ATTEMPT_BUDGET,
            "cooldown_seconds": 0,
        },
    }
    backup["ciphertext"] = seal(
        derive_wrap_key(bytes(group_secret), bid, epoch, nonce),
        random_bytes(32),
        aad=backup_associated_data(backup),
    )
    backup["digest"] = backup_digest(backup)

    signers = [
        AuthorizerSigner.generate(party_id) for party_id in range(1, PARTY_COUNT + 1)
    ]
    authorizer_config = AuthorizerConfig(
        bid=bid,
        epoch=epoch,
        backup_digest=backup["digest"],
        fault_bound=2,
        quorum=4,
        public_keys={signer.party_id: signer.public_key_hex for signer in signers},
    )
    ca_key, ca_certificate = _create_ca()
    coordinator_key, coordinator_certificate = _create_leaf(
        name="locus-client",
        ca_key=ca_key,
        ca_certificate=ca_certificate,
        server=False,
    )
    server_material: dict[int, tuple[Ed25519PrivateKey, x509.Certificate]] = {}
    peer_material: dict[int, tuple[Ed25519PrivateKey, x509.Certificate]] = {}
    for party_id in range(1, PARTY_COUNT + 1):
        server_material[party_id] = _create_leaf(
            name=f"party{party_id}",
            ca_key=ca_key,
            ca_certificate=ca_certificate,
            server=True,
        )
        peer_material[party_id] = _create_leaf(
            name=f"party{party_id}-peer",
            ca_key=ca_key,
            ca_certificate=ca_certificate,
            server=False,
        )
    identities = [
        {
            "certificate_sha256": _certificate_fingerprint(coordinator_certificate),
            "role": "coordinator",
        },
        *[
            {
                "certificate_sha256": _certificate_fingerprint(
                    peer_material[party_id][1]
                ),
                "role": f"party:{party_id}",
            }
            for party_id in range(1, PARTY_COUNT + 1)
        ],
    ]
    endpoints = [
        {
            "host": f"party{party_id}",
            "party_id": party_id,
            "port": PARTY_PORT,
            "server_certificate_sha256": _certificate_fingerprint(
                server_material[party_id][1]
            ),
        }
        for party_id in range(1, PARTY_COUNT + 1)
    ]
    ca_pem = _certificate_pem(ca_certificate)
    for root, signer in zip(party_roots, signers, strict=True):
        party_id = signer.party_id
        server_key, server_certificate = server_material[party_id]
        peer_key, peer_certificate = peer_material[party_id]
        peers = [
            {**endpoint, "timeout_seconds": 2.0}
            for endpoint in endpoints
            if endpoint["party_id"] != party_id
        ]
        native_party = (
            {
                "outbound_tls": {
                    "client_certificate": f"{RUNTIME_ROOT}/peer.pem",
                    "client_private_key": f"{RUNTIME_ROOT}/peer-key.pem",
                    "server_ca": f"{RUNTIME_ROOT}/ca.pem",
                },
                "parameters": encoded_parameters,
                "peers": peers,
                "state": encoded_states[party_id],
            }
            if party_id <= TPASS_PARTIES
            else None
        )
        service = {
            "authorizer_config": authorizer_config.to_dict(),
            "budget": ATTEMPT_BUDGET,
            "listen_host": "0.0.0.0",
            "listen_port": PARTY_PORT,
            "native_party": native_party,
            "party_id": party_id,
            "signer_private_key": signer.private_key_hex,
            "store_path": f"{RUNTIME_ROOT}/party.sqlite3",
            "tls": {
                "certificate": f"{RUNTIME_ROOT}/server.pem",
                "client_ca": f"{RUNTIME_ROOT}/ca.pem",
                "client_identities": identities,
                "private_key": f"{RUNTIME_ROOT}/server-key.pem",
            },
            "version": "LOCUS-party-service-config-v1",
        }
        _write_new(root / "ca.pem", ca_pem, mode=0o644)
        _write_new(
            root / "server.pem", _certificate_pem(server_certificate), mode=0o644
        )
        _write_new(root / "server-key.pem", _private_key_pem(server_key), mode=0o600)
        _write_new(root / "peer.pem", _certificate_pem(peer_certificate), mode=0o644)
        _write_new(root / "peer-key.pem", _private_key_pem(peer_key), mode=0o600)
        _write_new(root / "service.json", _json_bytes(service), mode=0o600)

    _write_new(client_root / "ca.pem", ca_pem, mode=0o644)
    _write_new(
        client_root / "coordinator.pem",
        _certificate_pem(coordinator_certificate),
        mode=0o644,
    )
    _write_new(
        client_root / "coordinator-key.pem",
        _private_key_pem(coordinator_key),
        mode=0o600,
    )
    deployment = {
        "authorizer_config": authorizer_config.to_dict(),
        "backup": backup,
        "parties": endpoints,
        "recovery_id": _base64url(recovery_identifier),
        "version": DEPLOYMENT_VERSION,
    }
    _write_new(client_root / "deployment.json", _json_bytes(deployment), mode=0o600)
    _chown_layout([*party_roots, client_root], owner_uid, owner_gid)
    audit_layout(party_roots, client_root)
    return "created"


def audit_layout(party_roots: list[Path], client_root: Path) -> dict[str, object]:
    """Recursively verify the provisioned role-state separation contract."""

    if len(party_roots) != PARTY_COUNT:
        raise DeploymentError("invalid party layout")
    party_static_files = {
        "ca.pem",
        "peer-key.pem",
        "peer.pem",
        "server-key.pem",
        "server.pem",
        "service.json",
    }
    party_runtime_files = {
        "party.sqlite3",
        "party.sqlite3-shm",
        "party.sqlite3-wal",
    }
    client_files = {
        "ca.pem",
        "coordinator-key.pem",
        "coordinator.pem",
        "deployment.json",
    }

    def snapshot(
        root: Path, *, required: set[str], allowed: set[str]
    ) -> dict[str, bytes]:
        if root.is_symlink() or not root.is_dir():
            raise DeploymentError("invalid deployment state directory")
        paths = list(root.iterdir())
        if any(path.is_symlink() or not path.is_file() for path in paths):
            raise DeploymentError("non-regular deployment state is forbidden")
        names = {path.name for path in paths}
        if not required <= names or not names <= allowed:
            raise DeploymentError("unexpected deployment state file")
        try:
            return {path.name: path.read_bytes() for path in paths}
        except OSError as exc:
            raise DeploymentError("deployment state is unreadable") from exc

    client_snapshot = snapshot(client_root, required=client_files, allowed=client_files)
    client_bytes = b"\x00".join(client_snapshot.values())
    deployment = _load_json(client_root / "deployment.json")
    if (
        not isinstance(deployment, dict)
        or deployment.get("version") != DEPLOYMENT_VERSION
        or not isinstance(deployment.get("backup"), dict)
    ):
        raise DeploymentError("invalid client deployment bundle")
    _validate_deployed_backup_profile(deployment["backup"])
    ciphertext = _json_bytes(deployment["backup"].get("ciphertext"))
    configs: list[dict[str, Any]] = []
    party_snapshots: list[bytes] = []
    states: dict[int, str] = {}
    signer_keys: list[str] = []
    identity_keys: list[bytes] = []
    for party_id, root in enumerate(party_roots, start=1):
        files = snapshot(
            root,
            required=party_static_files,
            allowed=party_static_files | party_runtime_files,
        )
        encoded = files["service.json"]
        party_snapshot = b"\x00".join(files.values())
        parsed = _load_json(root / "service.json")
        if not isinstance(parsed, dict) or parsed.get("party_id") != party_id:
            raise DeploymentError("party configuration mismatch")
        configs.append(parsed)
        party_snapshots.append(party_snapshot)
        identity_keys.extend([files["server-key.pem"], files["peer-key.pem"]])
        signer_key = parsed.get("signer_private_key")
        if not isinstance(signer_key, str):
            raise DeploymentError("party signer state is missing")
        signer_keys.append(signer_key)
        native_party = parsed.get("native_party")
        if party_id <= TPASS_PARTIES:
            if not isinstance(native_party, dict) or not isinstance(
                native_party.get("state"), str
            ):
                raise DeploymentError("party TPASS state is missing")
            states[party_id] = native_party["state"]
        elif native_party is not None:
            raise DeploymentError("authorizer-only party has TPASS state")
        if ciphertext in party_snapshot:
            raise DeploymentError("ciphertext entered party configuration")
    if len(states) != TPASS_PARTIES or len(set(states.values())) != TPASS_PARTIES:
        raise DeploymentError("party TPASS states are not distinct")
    for party_id, encoded in enumerate(party_snapshots, start=1):
        for state_id, state in states.items():
            present = state.encode("ascii") in encoded
            if present != (party_id == state_id):
                raise DeploymentError("party snapshot contains another state")
        for signer_id, signer_key in enumerate(signer_keys, start=1):
            present = signer_key.encode("ascii") in encoded
            if present != (party_id == signer_id):
                raise DeploymentError("party snapshot contains another signer key")
    for secret in [*states.values(), *signer_keys]:
        if secret.encode("ascii") in client_bytes:
            raise DeploymentError("party secret entered client bundle")
    coordinator_key = client_snapshot["coordinator-key.pem"]
    if len(set(identity_keys)) != PARTY_COUNT * 2:
        raise DeploymentError("party identity keys are not distinct")
    for owner_id, identity_key in enumerate(identity_keys):
        for party_id, party_snapshot in enumerate(party_snapshots):
            if (identity_key in party_snapshot) != (party_id == owner_id // 2):
                raise DeploymentError("party snapshot contains another identity key")
        if identity_key in client_bytes:
            raise DeploymentError("party identity key entered client bundle")
    if any(coordinator_key in party_snapshot for party_snapshot in party_snapshots):
        raise DeploymentError("coordinator identity key entered party snapshot")
    return {
        "client_has_party_secrets": False,
        "party_count": len(configs),
        "party_states_distinct": True,
        "status": "ok",
        "version": DEPLOYMENT_VERSION,
    }


def _tree_bytes(root: Path) -> int:
    if not root.is_dir() or root.is_symlink():
        raise DeploymentError("invalid storage metric root")
    total = 0
    for path in root.rglob("*"):
        if path.is_symlink():
            raise DeploymentError("storage metric root contains a link")
        if path.is_dir():
            continue
        if not path.is_file():
            raise DeploymentError("storage metric root contains a special file")
        try:
            total += path.stat().st_size
        except OSError as exc:
            raise DeploymentError("storage metric file is unavailable") from exc
    return total


def validate_storage_metric(value: object) -> dict[str, object]:
    """Validate aggregate role storage without exposing paths or content."""

    metric = _exact_dict(
        value,
        {"artifact", "client_bytes", "party_bytes", "status"},
        "storage metric",
    )
    party_bytes = metric["party_bytes"]
    if (
        metric["artifact"] != STORAGE_METRIC_VERSION
        or metric["status"] != "ok"
        or not isinstance(metric["client_bytes"], int)
        or isinstance(metric["client_bytes"], bool)
        or metric["client_bytes"] < 0
        or not isinstance(party_bytes, list)
        or len(party_bytes) != PARTY_COUNT
        or any(
            not isinstance(item, int) or isinstance(item, bool) or item < 0
            for item in party_bytes
        )
    ):
        raise DeploymentError("invalid storage metric")
    validate_public_output(metric)
    return metric


def storage_metric(party_roots: list[Path], client_root: Path) -> dict[str, object]:
    """Measure aggregate logical persistent bytes at each local role."""

    if len(party_roots) != PARTY_COUNT or len(set(party_roots)) != PARTY_COUNT:
        raise DeploymentError("exactly five distinct party roots are required")
    return validate_storage_metric(
        {
            "artifact": STORAGE_METRIC_VERSION,
            "client_bytes": _tree_bytes(client_root),
            "party_bytes": [_tree_bytes(root) for root in party_roots],
            "status": "ok",
        }
    )


class _ResolverServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address: tuple[str, int], fixture: dict[str, object]) -> None:
        self.fixture = fixture
        super().__init__(address, _ResolverHandler)


class _ResolverHandler(BaseHTTPRequestHandler):
    server: _ResolverServer
    protocol_version = "HTTP/1.1"

    def log_message(self, format: str, *args: object) -> None:
        return

    def do_GET(self) -> None:
        if self.path == "/health/live":
            body = _json_bytes({"status": "live"})
            status = 200
        elif self.path == "/v1/cues":
            body = _json_bytes(self.server.fixture)
            status = 200
        else:
            body = _json_bytes({"error": "not_found"})
            status = 404
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)
        self.close_connection = True


def serve_resolver(*, fixture_path: Path, host: str, port: int) -> None:
    cues = _load_fixture(fixture_path)
    server = _ResolverServer((host, port), {"cues": cues, "version": RESOLVER_VERSION})
    try:
        server.serve_forever(poll_interval=0.1)
    finally:
        server.server_close()


def _read_http_json_with_size(url: str) -> tuple[object, int]:
    request = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=5.0) as response:
            if (
                response.status != 200
                or response.headers.get_content_type() != "application/json"
            ):
                raise DeploymentError("deployment service rejected request")
            data = response.read(1_048_577)
    except (OSError, urllib.error.URLError) as exc:
        raise DeploymentError("deployment service is unavailable") from exc
    if len(data) > 1_048_576:
        raise DeploymentError("oversized deployment response")
    try:
        return json.loads(data.decode("ascii")), len(data)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DeploymentError("invalid deployment response") from exc


def _read_http_json(url: str) -> object:
    value, _ = _read_http_json_with_size(url)
    return value


def resolver_health(url: str) -> None:
    if _read_http_json(url) != {"status": "live"}:
        raise DeploymentError("resolver is not healthy")


def party_health(root: Path) -> None:
    context = ssl.create_default_context(
        ssl.Purpose.SERVER_AUTH, cafile=str(root / "ca.pem")
    )
    context.minimum_version = ssl.TLSVersion.TLSv1_3
    context.load_cert_chain(root / "peer.pem", root / "peer-key.pem")
    connection = http.client.HTTPSConnection(
        "localhost", PARTY_PORT, context=context, timeout=3.0
    )
    expected = hashlib.sha256(
        ssl.PEM_cert_to_DER_cert((root / "server.pem").read_text(encoding="ascii"))
    ).hexdigest()
    try:
        connection.connect()
        socket = connection.sock
        peer_certificate = (
            None if socket is None else socket.getpeercert(binary_form=True)
        )
        if (
            peer_certificate is None
            or hashlib.sha256(peer_certificate).hexdigest() != expected
        ):
            raise DeploymentError("party certificate pin mismatch")
        connection.request("GET", "/health/live")
        response = connection.getresponse()
        body = response.read(4097)
        if response.status != 200 or len(body) > 4096:
            raise DeploymentError("party is not healthy")
        parsed = json.loads(body.decode("ascii"))
        if parsed.get("result") != {"status": "live"}:
            raise DeploymentError("party is not healthy")
    except (OSError, ssl.SSLError, json.JSONDecodeError) as exc:
        raise DeploymentError("party is not healthy") from exc
    finally:
        connection.close()


def _resolver_cues_with_size(url: str) -> tuple[list[dict[str, Any]], int]:
    value, body_bytes = _read_http_json_with_size(url)
    if (
        not isinstance(value, dict)
        or set(value) != {"cues", "version"}
        or value["version"] != RESOLVER_VERSION
        or not isinstance(value["cues"], list)
    ):
        raise DeploymentError("invalid resolver result")
    canonical_recovery_input(value["cues"])
    return value["cues"], body_bytes


def _resolver_cues(url: str) -> list[dict[str, Any]]:
    cues, _ = _resolver_cues_with_size(url)
    return cues


def _s3_store() -> S3BackupObjectStore:
    required = {
        name: os.environ.get(name)
        for name in (
            "LOCUS_S3_ENDPOINT",
            "LOCUS_S3_BUCKET",
            "LOCUS_S3_ACCESS_KEY",
            "LOCUS_S3_SECRET_KEY",
            "LOCUS_S3_PREFIX",
        )
    }
    if any(not value for value in required.values()):
        raise DeploymentError("cloud configuration is unavailable")
    return S3BackupObjectStore.from_credentials(
        bucket=cast(str, required["LOCUS_S3_BUCKET"]),
        endpoint_url=cast(str, required["LOCUS_S3_ENDPOINT"]),
        access_key=cast(str, required["LOCUS_S3_ACCESS_KEY"]),
        secret_key=cast(str, required["LOCUS_S3_SECRET_KEY"]),
        prefix=cast(str, required["LOCUS_S3_PREFIX"]),
        allow_http=True,
        verify=False,
        timeout_seconds=2.0,
    )


def _client_nodes(
    client_root: Path,
    endpoints: list[dict[str, Any]],
) -> tuple[list[RemoteAuthorizerNode], dict[int, RemotePartyClient]]:
    nodes: list[RemoteAuthorizerNode] = []
    clients: dict[int, RemotePartyClient] = {}
    common: dict[str, Any] = {
        "server_ca": str(client_root / "ca.pem"),
        "client_certificate": str(client_root / "coordinator.pem"),
        "client_private_key": str(client_root / "coordinator-key.pem"),
        "timeout_seconds": 5.0,
    }
    for endpoint in endpoints:
        fields = {
            "party_id": endpoint["party_id"],
            "host": endpoint["host"],
            "port": endpoint["port"],
            "server_certificate_sha256": endpoint["server_certificate_sha256"],
            **common,
        }
        nodes.append(RemoteAuthorizerNode(**fields))
        if endpoint["party_id"] <= TPASS_PARTIES:
            clients[endpoint["party_id"]] = RemotePartyClient(**fields)
    return nodes, clients


def _current_head(
    nodes: list[RemoteAuthorizerNode], config: AuthorizerConfig, sid: str
) -> tuple[int, str, int, int]:
    summaries = AttemptCoordinator(
        config=config,
        nodes=cast(list[AuthorizerPeer], nodes),
        operation_timeout_seconds=AUTHORIZATION_OPERATION_TIMEOUT_SECONDS,
    ).state_summaries(config.bid, config.epoch, sid)
    return _head_from_summaries(summaries, config)


def _head_from_summaries(
    summaries: list[tuple[int, AuthorizerState]], config: AuthorizerConfig
) -> tuple[int, str, int, int]:
    states: Counter[tuple[int, str, int, int, str]] = Counter()
    for _, summary in summaries:
        status = summary.status
        states[
            (
                int(status["installed_index"]),
                str(status["installed_head"]),
                int(status["consumed"]),
                int(status["budget"]),
                str(status["backup_digest"]),
            )
        ] += 1
    state, count = states.most_common(1)[0]
    if count < config.quorum or state[4] != config.backup_digest:
        raise DeploymentError("party state did not reconcile")
    return state[0], state[1], state[2], state[3]


def _select_tpass_subset(
    clients: dict[int, RemotePartyClient],
    summaries: list[tuple[int, AuthorizerState]],
    config: AuthorizerConfig,
) -> list[int]:
    """Choose a healthy subset before authorization; never switch it mid-phase."""

    reconciled = _head_from_summaries(summaries, config)
    responsive = {
        party_id
        for party_id, summary in summaries
        if summary.status["status"] == "ACTIVE"
        and (
            int(summary.status["installed_index"]),
            str(summary.status["installed_head"]),
            int(summary.status["consumed"]),
            int(summary.status["budget"]),
        )
        == reconciled
        and summary.status["backup_digest"] == config.backup_digest
        and party_id in clients
    }
    preferred = [1, 3, 2]
    selected = [party_id for party_id in preferred if party_id in responsive][
        :TPASS_THRESHOLD
    ]
    if len(selected) < TPASS_THRESHOLD:
        raise DeploymentError("insufficient responsive recovery parties")
    return sorted(selected)


def _collect_selected[RecoveryResult](
    selected: list[int],
    operation: Callable[[int], RecoveryResult],
    *,
    timeout_seconds: float = RECOVERY_PHASE_TIMEOUT_SECONDS,
) -> list[RecoveryResult]:
    """Run one selected TPASS phase concurrently under one fixed deadline."""

    if (
        isinstance(timeout_seconds, bool)
        or not isinstance(timeout_seconds, (int, float))
        or not 0 < timeout_seconds <= RECOVERY_PHASE_TIMEOUT_SECONDS
    ):
        raise DeploymentError("invalid recovery phase timeout")
    executor = ThreadPoolExecutor(
        max_workers=len(selected), thread_name_prefix="locus-recovery"
    )
    futures: dict[int, Future[RecoveryResult]] = {
        party_id: executor.submit(operation, party_id) for party_id in selected
    }
    try:
        completed, pending = wait(futures.values(), timeout=timeout_seconds)
        if pending:
            raise DeploymentError("recovery party phase timed out")
        results: list[RecoveryResult] = []
        for party_id in selected:
            try:
                results.append(futures[party_id].result())
            except PartyStoreError as exc:
                raise DeploymentError("recovery party phase failed") from exc
        return results
    finally:
        for future in futures.values():
            future.cancel()
        executor.shutdown(wait=False, cancel_futures=True)


def deployment_attempt_status(client_root: Path) -> dict[str, int]:
    """Read privacy-safe attempt status through the normal party interfaces."""

    deployment = _load_json(client_root / "deployment.json")
    if not isinstance(deployment, dict) or not isinstance(
        deployment.get("parties"), list
    ):
        raise DeploymentError("invalid client deployment bundle")
    config = AuthorizerConfig.from_dict(deployment.get("authorizer_config"))
    nodes, _ = _client_nodes(client_root, deployment["parties"])
    installed_index, _, consumed, budget = _current_head(
        nodes, config, secrets.token_hex(32)
    )
    return {
        "budget": budget,
        "consumed": consumed,
        "installed_index": installed_index,
    }


def validate_benchmark_result(value: object) -> dict[str, object]:
    """Validate one exact redacted Compose benchmark result."""

    result = _exact_dict(
        value,
        {
            "artifact",
            "attempts",
            "latency_ms",
            "profile",
            "runs",
            "selected",
            "status",
        },
        "benchmark result",
    )
    runs = result["runs"]
    if not isinstance(runs, int) or isinstance(runs, bool) or not 1 <= runs <= 4:
        raise DeploymentError("invalid benchmark result")
    if (
        result["artifact"] != BENCHMARK_VERSION
        or result["profile"] != "benchmark"
        or result["selected"] != [1, 3]
        or result["status"] != "ok"
    ):
        raise DeploymentError("invalid benchmark result")
    attempts = _exact_dict(
        result["attempts"], {"after", "before", "budget"}, "benchmark attempts"
    )
    if (
        any(
            not isinstance(item, int) or isinstance(item, bool)
            for item in attempts.values()
        )
        or attempts["after"] != attempts["before"] + runs
    ):
        raise DeploymentError("invalid benchmark attempts")
    latency = _exact_dict(
        result["latency_ms"],
        {"max", "mean", "median", "min", "samples"},
        "benchmark latency",
    )
    samples = latency["samples"]
    if (
        not isinstance(samples, list)
        or len(samples) != runs
        or any(
            not isinstance(item, (int, float))
            or isinstance(item, bool)
            or not math.isfinite(item)
            or item <= 0
            for item in samples
        )
    ):
        raise DeploymentError("invalid benchmark latency")
    expected = {
        "max": max(samples),
        "mean": statistics.fmean(samples),
        "median": statistics.median(samples),
        "min": min(samples),
    }
    if any(
        latency[field] != expected_value for field, expected_value in expected.items()
    ):
        raise DeploymentError("invalid benchmark summary")
    validate_public_output(result)
    return result


def validate_performance_client_result(value: object) -> dict[str, object]:
    """Validate one exact set of three measured client operations."""

    result = _exact_dict(
        value,
        {"artifact", "runs", "samples", "scenario_id", "status"},
        "performance client result",
    )
    if (
        result["artifact"] != PERFORMANCE_CLIENT_VERSION
        or result["status"] != "ok"
        or result["runs"] != PERFORMANCE_RUNS
        or result["scenario_id"] not in PERFORMANCE_SCENARIOS
    ):
        raise DeploymentError("invalid performance client result")
    samples = result["samples"]
    if not isinstance(samples, list) or len(samples) != PERFORMANCE_RUNS:
        raise DeploymentError("invalid performance samples")
    expected_selected = (
        [2, 3]
        if result["scenario_id"] == "recover-one-party-unavailable-v1"
        else [1, 3]
    )
    expected_outcome = (
        "generic-rejection"
        if result["scenario_id"] == "recover-wrong-input-v1"
        else "success"
    )
    for offset, raw_sample in enumerate(samples, start=1):
        sample = _exact_dict(
            raw_sample,
            {
                "application_bytes",
                "artifact",
                "attempts",
                "latency_ms",
                "measurement",
                "outcome",
                "selected",
                "status",
            },
            "performance sample",
        )
        if (
            sample["artifact"] != PERFORMANCE_CLIENT_VERSION
            or sample["status"] != "ok"
            or sample["measurement"] != offset
            or sample["selected"] != expected_selected
            or sample["outcome"] != expected_outcome
        ):
            raise DeploymentError("invalid performance sample")
        attempts = _exact_dict(
            sample["attempts"], {"after", "before"}, "performance attempts"
        )
        if attempts != {"after": offset + 1, "before": offset}:
            raise DeploymentError("performance attempt sequence changed")
        application_bytes = _exact_dict(
            sample["application_bytes"],
            {"authorization", "cloud", "resolver", "tpass"},
            "performance application bytes",
        )
        for role_bytes in application_bytes.values():
            counts = _exact_dict(
                role_bytes, {"received", "sent"}, "performance role bytes"
            )
            if any(
                not isinstance(count, int) or isinstance(count, bool) or count < 0
                for count in counts.values()
            ):
                raise DeploymentError("invalid performance role bytes")
        latency = _exact_dict(
            sample["latency_ms"],
            {
                "authorization",
                "client_setup",
                "cloud",
                "commitment",
                "finalization",
                "resolver",
                "response",
                "status_check",
                "total",
                "unclassified",
            },
            "performance latency",
        )
        if (
            any(
                not isinstance(item, (int, float))
                or isinstance(item, bool)
                or not math.isfinite(item)
                or item < 0
                for item in latency.values()
            )
            or latency["total"] <= 0
        ):
            raise DeploymentError("invalid performance latency")
        covered = sum(
            float(latency[field])
            for field in latency
            if field not in {"total", "unclassified"}
        )
        if not math.isclose(
            covered + float(latency["unclassified"]),
            float(latency["total"]),
            rel_tol=1e-9,
            abs_tol=0.001,
        ):
            raise DeploymentError("performance phase timings do not cover total")
    validate_public_output(result)
    return result


def run_deployment_performance(
    *,
    client_root: Path,
    resolver_url: str,
    scenario_id: str,
    runs: int,
) -> dict[str, object]:
    """Run the frozen three measured operations after one host-run warm-up."""

    if scenario_id not in PERFORMANCE_SCENARIOS or runs != PERFORMANCE_RUNS:
        raise DeploymentError("invalid performance scenario")
    mode = "wrong-input" if scenario_id == "recover-wrong-input-v1" else "success"
    samples = []
    for measurement in range(1, runs + 1):
        sample = run_client(
            client_root=client_root,
            resolver_url=resolver_url,
            performance_mode=mode,
        )
        sample["measurement"] = measurement
        samples.append(sample)
    return validate_performance_client_result(
        {
            "artifact": PERFORMANCE_CLIENT_VERSION,
            "runs": runs,
            "samples": samples,
            "scenario_id": scenario_id,
            "status": "ok",
        }
    )


def validate_provision_metric(value: object) -> dict[str, object]:
    """Validate the aggregate client provisioning latency."""

    metric = _exact_dict(
        value,
        {"artifact", "latency_ms", "status"},
        "provision metric",
    )
    latency = metric["latency_ms"]
    if (
        metric["artifact"] != PROVISION_METRIC_VERSION
        or metric["status"] != "created"
        or not isinstance(latency, (int, float))
        or isinstance(latency, bool)
        or not math.isfinite(latency)
        or latency <= 0
    ):
        raise DeploymentError("invalid provision metric")
    validate_public_output(metric)
    return metric


def validate_performance_result(value: object) -> dict[str, object]:
    """Validate one host-composed frozen performance-scenario result."""

    result = _exact_dict(
        value,
        {
            "artifact",
            "block",
            "cleanup",
            "configuration",
            "enrollment_latency_ms",
            "orchestration_latency_ms",
            "orchestration_seed",
            "output_scan",
            "profile",
            "runtime",
            "samples",
            "scenario_position",
            "scenario_id",
            "status",
            "storage",
        },
        "performance result",
    )
    if (
        result["artifact"] != PERFORMANCE_RESULT_VERSION
        or result["profile"] != "performance"
        or result["status"] != "ok"
        or result["cleanup"] != "passed"
        or result["output_scan"] != "passed"
        or result["scenario_id"] not in PERFORMANCE_SCENARIOS
        or not isinstance(result["scenario_position"], int)
        or isinstance(result["scenario_position"], bool)
        or not 1 <= result["scenario_position"] <= len(PERFORMANCE_SCENARIOS)
        or not isinstance(result["block"], int)
        or isinstance(result["block"], bool)
        or not 1 <= result["block"] <= 10
        or not isinstance(result["orchestration_seed"], int)
        or isinstance(result["orchestration_seed"], bool)
        or not 0 <= result["orchestration_seed"] <= 2**64 - 1
        or not isinstance(result["orchestration_latency_ms"], (int, float))
        or isinstance(result["orchestration_latency_ms"], bool)
        or not math.isfinite(result["orchestration_latency_ms"])
        or result["orchestration_latency_ms"] <= 0
    ):
        raise DeploymentError("invalid performance result")
    if (
        performance_scenario_order(result["orchestration_seed"])[
            result["scenario_position"] - 1
        ]
        != result["scenario_id"]
    ):
        raise DeploymentError("performance scenario order changed")
    configuration = _exact_dict(
        result["configuration"],
        {
            "alternate_selected",
            "authorization_membership",
            "authorization_quorum",
            "baseline_selected",
            "measurements",
            "threshold",
            "topology",
            "tpass_parties",
            "warmups",
        },
        "performance configuration",
    )
    if configuration != {
        "alternate_selected": [2, 3],
        "authorization_membership": 5,
        "authorization_quorum": 4,
        "baseline_selected": [1, 3],
        "measurements": 3,
        "threshold": 2,
        "topology": "same-host-compose-5-party-v1",
        "tpass_parties": 3,
        "warmups": 1,
    }:
        raise DeploymentError("performance configuration changed")
    runtime = _exact_dict(
        result["runtime"],
        {
            "compose_version",
            "docker_engine_version",
            "reference_image_id",
            "s3_image",
        },
        "performance runtime",
    )
    for field in ("compose_version", "docker_engine_version"):
        value = runtime[field]
        if (
            not isinstance(value, str)
            or re.fullmatch(r"[A-Za-z0-9.+_-]{1,64}", value) is None
        ):
            raise DeploymentError("invalid performance runtime version")
    reference_image_id = runtime["reference_image_id"]
    if (
        not isinstance(reference_image_id, str)
        or re.fullmatch(r"sha256:[0-9a-f]{64}", reference_image_id) is None
        or runtime["s3_image"]
        != (
            "chrislusf/seaweedfs:4.29@"
            "sha256:d47c7ee99fcb951351d7194915f4e3a5ea604a8e8871183d713907dec4fb9bf5"
        )
    ):
        raise DeploymentError("invalid performance image identity")
    provision = validate_provision_metric(
        {
            "artifact": PROVISION_METRIC_VERSION,
            "latency_ms": result["enrollment_latency_ms"],
            "status": "created",
        }
    )
    if provision["latency_ms"] != result["enrollment_latency_ms"]:
        raise DeploymentError("invalid enrollment latency")
    client_result = validate_performance_client_result(
        {
            "artifact": PERFORMANCE_CLIENT_VERSION,
            "runs": PERFORMANCE_RUNS,
            "samples": result["samples"],
            "scenario_id": result["scenario_id"],
            "status": "ok",
        }
    )
    if client_result["samples"] != result["samples"]:
        raise DeploymentError("invalid performance samples")
    storage = _exact_dict(
        result["storage"],
        {"after", "before", "cloud_object_bytes"},
        "performance storage",
    )
    validate_storage_metric(storage["before"])
    validate_storage_metric(storage["after"])
    if (
        not isinstance(storage["cloud_object_bytes"], int)
        or isinstance(storage["cloud_object_bytes"], bool)
        or storage["cloud_object_bytes"] <= 0
    ):
        raise DeploymentError("invalid cloud object size")
    validate_public_output(result)
    return result


def run_deployment_benchmark(
    *, client_root: Path, resolver_url: str, runs: int
) -> dict[str, object]:
    """Measure repeated complete recoveries through the deployed interfaces."""

    if not 1 <= runs <= 4:
        raise DeploymentError("benchmark runs must be between 1 and 4")
    before = deployment_attempt_status(client_root)
    if runs > before["budget"] - before["consumed"]:
        raise DeploymentError("benchmark exceeds the remaining attempt budget")
    samples: list[float] = []
    for offset in range(1, runs + 1):
        started = time.perf_counter()
        result = run_client(client_root=client_root, resolver_url=resolver_url)
        samples.append((time.perf_counter() - started) * 1000)
        if result["consumed"] != before["consumed"] + offset:
            raise DeploymentError("benchmark attempt count changed unexpectedly")
    after = deployment_attempt_status(client_root)
    return validate_benchmark_result(
        {
            "artifact": BENCHMARK_VERSION,
            "attempts": {
                "after": after["consumed"],
                "before": before["consumed"],
                "budget": after["budget"],
            },
            "latency_ms": {
                "max": max(samples),
                "mean": statistics.fmean(samples),
                "median": statistics.median(samples),
                "min": min(samples),
                "samples": samples,
            },
            "profile": "benchmark",
            "runs": runs,
            "selected": [1, 3],
            "status": "ok",
        }
    )


def run_client(
    *,
    client_root: Path,
    resolver_url: str,
    deployment_override: dict[str, object] | None = None,
    performance_mode: str | None = None,
) -> dict[str, object]:
    """Perform one fresh recovery through S3 and the five network parties."""

    if performance_mode not in {None, "success", "wrong-input"}:
        raise DeploymentError("invalid performance mode")
    total_started = time.perf_counter()
    phase_latency_ms: dict[str, float] = {}
    deployment = (
        _load_json(client_root / "deployment.json")
        if deployment_override is None
        else deployment_override
    )
    if (
        not isinstance(deployment, dict)
        or set(deployment)
        != {"authorizer_config", "backup", "parties", "recovery_id", "version"}
        or deployment["version"] != DEPLOYMENT_VERSION
        or not isinstance(deployment["backup"], dict)
        or not isinstance(deployment["parties"], list)
    ):
        raise DeploymentError("invalid client deployment bundle")
    config = AuthorizerConfig.from_dict(deployment["authorizer_config"])
    backup = _validate_deployed_backup_profile(deployment["backup"])
    phase_started = time.perf_counter()
    store = _s3_store()
    expected_reference = BackupReference(
        bid=config.bid,
        epoch=config.epoch,
        backup_digest=config.backup_digest,
    )
    published_backup_bytes = b""
    if performance_mode is None:
        reference = store.create(backup)
        if reference != expected_reference:
            raise DeploymentError("cloud backup binding mismatch")
        _, published_backup_bytes = encode_backup_object(backup)
    stored_backup_bytes = store.read_encoded(expected_reference)
    _, stored_backup = decode_backup_object(
        stored_backup_bytes, expected=expected_reference
    )
    _validate_deployed_backup_profile(stored_backup)
    phase_latency_ms["cloud"] = (time.perf_counter() - phase_started) * 1000
    phase_started = time.perf_counter()
    cues, resolver_received_bytes = _resolver_cues_with_size(resolver_url)
    recovery_input = canonical_recovery_input(cues)
    if performance_mode == "wrong-input":
        recovery_input = hash_bytes(
            "LOCUS/performance-wrong-input/v1",
            recovery_input,
        )
    phase_latency_ms["resolver"] = (time.perf_counter() - phase_started) * 1000
    phase_started = time.perf_counter()
    parameters = native.PublicParameters.from_bytes(
        _decode_base64url(stored_backup["tpass_public_params"]["parameters"])
    )
    recovery_identifier = _decode_base64url(deployment["recovery_id"])
    session = native.begin_recovery(parameters, recovery_identifier, recovery_input)
    request = bytes(session.request_bytes())
    nodes, clients = _client_nodes(client_root, deployment["parties"])
    phase_latency_ms["client_setup"] = (time.perf_counter() - phase_started) * 1000
    phase_started = time.perf_counter()
    sid = secrets.token_hex(32)
    coordinator = AttemptCoordinator(
        config=config,
        nodes=cast(list[AuthorizerPeer], nodes),
        operation_timeout_seconds=AUTHORIZATION_OPERATION_TIMEOUT_SECONDS,
    )
    summaries = coordinator.state_summaries(config.bid, config.epoch, sid)
    installed_index, installed_head, consumed, budget = _head_from_summaries(
        summaries, config
    )
    if consumed >= budget:
        raise DeploymentError("attempt budget is exhausted")
    selected = _select_tpass_subset(clients, summaries, config)
    request_digest = hash_bytes(
        "LOCUS/recovery-request/v1",
        encode(
            {
                "bid": config.bid,
                "epoch": config.epoch,
                "recovery_id": deployment["recovery_id"],
                "selected": selected,
                "sid": sid,
            }
        ),
        request,
    ).hex()
    entry = AttemptEntry(
        bid=config.bid,
        epoch=config.epoch,
        config_digest=config.digest,
        log_index=installed_index + 1,
        previous_head=installed_head if installed_index else GENESIS_HEAD,
        sid=sid,
        request_digest=request_digest,
        tpass_request_hash=hash_bytes("LOCUS/tpass-request-bytes/v1", request).hex(),
        resulting_consumed=consumed + 1,
        effective_budget=budget,
    )
    certificate = coordinator.authorize(entry)
    phase_latency_ms["authorization"] = (time.perf_counter() - phase_started) * 1000
    phase_started = time.perf_counter()
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
    phase_latency_ms["commitment"] = (time.perf_counter() - phase_started) * 1000
    phase_started = time.perf_counter()
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
    phase_latency_ms["response"] = (time.perf_counter() - phase_started) * 1000
    phase_started = time.perf_counter()
    gateway = native.aggregate_responses(
        parameters, request, selected, commitments, responses
    )
    group_secret: Any | None = None
    rejected = False
    try:
        group_secret = native.finish_recovery(parameters, session, gateway)
    except native.NativeTpassError as exc:
        if performance_mode != "wrong-input":
            raise DeploymentError("native recovery failed") from exc
        rejected = True
    if performance_mode == "wrong-input" and not rejected:
        raise DeploymentError("wrong-input performance control unexpectedly recovered")
    if not rejected:
        if group_secret is None:
            raise DeploymentError("native recovery returned no group secret")
        private_key = open_sealed(
            derive_wrap_key(
                bytes(group_secret),
                stored_backup["bid"],
                stored_backup["epoch"],
                stored_backup["nonce"],
            ),
            stored_backup["ciphertext"],
            aad=backup_associated_data(stored_backup),
        )
        if len(private_key) != 32:
            raise DeploymentError("recovered key is invalid")
    phase_latency_ms["finalization"] = (time.perf_counter() - phase_started) * 1000
    phase_started = time.perf_counter()
    _, _, final_consumed, _ = _current_head(nodes, config, secrets.token_hex(32))
    if final_consumed != consumed + 1:
        raise DeploymentError("attempt count did not advance exactly once")
    phase_latency_ms["status_check"] = (time.perf_counter() - phase_started) * 1000
    total_latency_ms = (time.perf_counter() - total_started) * 1000
    if performance_mode is not None:
        covered = sum(phase_latency_ms.values())
        unclassified = total_latency_ms - covered
        if unclassified < 0 and abs(unclassified) < 0.001:
            unclassified = 0.0
        if unclassified < 0:
            raise DeploymentError("performance phases exceed total latency")
        authorization_bytes = {
            "received": sum(node.application_bytes["received"] for node in nodes),
            "sent": sum(node.application_bytes["sent"] for node in nodes),
        }
        tpass_bytes = {
            "received": sum(
                client.application_bytes["received"] for client in clients.values()
            ),
            "sent": sum(
                client.application_bytes["sent"] for client in clients.values()
            ),
        }
        performance_result: dict[str, object] = {
            "application_bytes": {
                "authorization": authorization_bytes,
                "cloud": {
                    "received": len(stored_backup_bytes),
                    "sent": len(published_backup_bytes),
                },
                "resolver": {"received": resolver_received_bytes, "sent": 0},
                "tpass": tpass_bytes,
            },
            "artifact": PERFORMANCE_CLIENT_VERSION,
            "attempts": {"after": final_consumed, "before": consumed},
            "latency_ms": {
                **phase_latency_ms,
                "total": total_latency_ms,
                "unclassified": unclassified,
            },
            "outcome": "generic-rejection" if rejected else "success",
            "selected": selected,
            "status": "ok",
        }
        validate_public_output(performance_result)
        return performance_result
    return {
        "artifact": DEPLOYMENT_VERSION,
        "backup_binding": "verified",
        "consumed": final_consumed,
        "recovery": "verified",
        "selected": selected,
        "status": "ok",
    }


def _wait_for_lifecycle_restart(checkpoint_dir: Path) -> None:
    if not checkpoint_dir.is_dir() or checkpoint_dir.is_symlink():
        raise DeploymentError("invalid lifecycle restart checkpoint")
    ready = checkpoint_dir / "locus-lifecycle-restart-ready"
    complete = checkpoint_dir / "locus-lifecycle-restart-complete"
    if ready.exists() or complete.exists():
        raise DeploymentError("stale lifecycle restart checkpoint")
    ready.touch(exist_ok=False)
    deadline = time.monotonic() + 120.0
    try:
        while not complete.is_file():
            if time.monotonic() >= deadline:
                raise DeploymentError("lifecycle party restart timed out")
            time.sleep(0.1)
    finally:
        ready.unlink(missing_ok=True)
        complete.unlink(missing_ok=True)


def run_cross_epoch_lifecycle(
    *,
    client_root: Path,
    resolver_url: str,
    restart_checkpoint_dir: Path | None = None,
) -> dict[str, object]:
    """Exercise certified re-enrollment and one deterministic cross-epoch mix."""

    deployment = _load_json(client_root / "deployment.json")
    if (
        not isinstance(deployment, dict)
        or set(deployment)
        != {"authorizer_config", "backup", "parties", "recovery_id", "version"}
        or deployment["version"] != DEPLOYMENT_VERSION
        or not isinstance(deployment["backup"], dict)
        or not isinstance(deployment["parties"], list)
    ):
        raise DeploymentError("invalid client deployment bundle")
    old_config = AuthorizerConfig.from_dict(deployment["authorizer_config"])
    old_backup = _validate_deployed_backup_profile(deployment["backup"])
    old_reference = _s3_store().create(old_backup)
    if _s3_store().read(old_reference) != old_backup:
        raise DeploymentError("old cloud epoch is not immutable")
    cues = _resolver_cues(resolver_url)
    recovery_input = canonical_recovery_input(cues)
    encoded_old_recovery_identifier = deployment.get("recovery_id")
    if not isinstance(encoded_old_recovery_identifier, str):
        raise DeploymentError("invalid predecessor recovery identifier")
    old_recovery_identifier = _decode_base64url(encoded_old_recovery_identifier)

    new_recovery_identifier = b"LOCUS-compose-recovery-v2:" + bytes.fromhex(
        old_config.bid
    )
    new_parameters, new_states, new_group_secret = native.setup(
        new_recovery_identifier,
        recovery_input,
        TPASS_THRESHOLD,
        TPASS_PARTIES,
    )
    new_parameters_bytes = bytes(new_parameters.to_bytes())
    new_state_bytes = {
        state.party_id: bytes(state.to_secret_bytes()) for state in new_states
    }
    new_nonce = random_bytes(16).hex()
    new_backup: dict[str, Any] = {
        "version": BACKUP_VERSION,
        "bid": old_config.bid,
        "epoch": old_config.epoch + 1,
        "nonce": new_nonce,
        "tpass_public_params": {
            "backend": TPASS_BACKEND,
            "encoding": TPASS_ENCODING,
            "parameters": _base64url(new_parameters_bytes),
            "threshold": TPASS_THRESHOLD,
            "parties": TPASS_PARTIES,
        },
        "context_policy": {"version": CONTEXT_POLICY_VERSION},
        "security_policy": {
            "version": SECURITY_POLICY_VERSION,
            "max_attempts": ATTEMPT_BUDGET,
            "cooldown_seconds": 0,
        },
    }
    new_backup["ciphertext"] = seal(
        derive_wrap_key(
            bytes(new_group_secret),
            old_config.bid,
            old_config.epoch + 1,
            new_nonce,
        ),
        random_bytes(32),
        aad=backup_associated_data(new_backup),
    )
    new_backup["digest"] = backup_digest(new_backup)
    new_config = AuthorizerConfig(
        bid=old_config.bid,
        epoch=old_config.epoch + 1,
        backup_digest=new_backup["digest"],
        fault_bound=old_config.fault_bound,
        quorum=old_config.quorum,
        public_keys=old_config.public_keys,
    )
    new_reference = _s3_store().create(new_backup)
    if new_reference == old_reference or _s3_store().read(new_reference) != new_backup:
        raise DeploymentError("successor cloud epoch is not immutable")

    nodes, _ = _client_nodes(client_root, deployment["parties"])
    installed_index, installed_head, consumed, budget = _current_head(
        nodes, old_config, secrets.token_hex(32)
    )
    transition = EpochTransition(
        bid=old_config.bid,
        predecessor_epoch=old_config.epoch,
        predecessor_config_digest=old_config.digest,
        predecessor_backup_digest=old_config.backup_digest,
        predecessor_head=installed_head,
        predecessor_consumed=consumed,
        predecessor_budget=budget,
        successor_epoch=new_config.epoch,
        successor_config_digest=new_config.digest,
        successor_backup_digest=new_config.backup_digest,
        successor_budget=ATTEMPT_BUDGET,
        policy_version="LOCUS-epoch-lifecycle-policy-v1",
        transition_nonce=secrets.token_hex(32),
    )
    approvals = [
        node.create_epoch_approval(transition, old_config, new_config) for node in nodes
    ]
    readiness = []
    for node in nodes:
        native_role = node.party_id <= TPASS_PARTIES
        readiness.append(
            node.prepare_successor_epoch(
                transition,
                old_config,
                new_config,
                parameters=new_parameters_bytes if native_role else None,
                party_state=(new_state_bytes[node.party_id] if native_role else None),
            )
        )

    _, predecessor_context_states, _ = native.setup(
        old_recovery_identifier,
        recovery_input,
        TPASS_THRESHOLD,
        TPASS_PARTIES,
    )
    predecessor_context_state = bytes(predecessor_context_states[0].to_secret_bytes())
    mix_result = "unexpected-success"
    try:
        nodes[0].prepare_successor_epoch(
            transition,
            old_config,
            new_config,
            parameters=new_parameters_bytes,
            party_state=predecessor_context_state,
            idempotency_key="91" * 32,
        )
    except Conflict:
        mix_result = "rejected"

    certificate = EpochActivationCertificate.create(
        transition,
        approvals[: old_config.quorum],
        readiness[: new_config.quorum],
        old_config,
        new_config,
    )
    for node in nodes[:3]:
        node.activate_successor_epoch(certificate, old_config, new_config)

    old_active = 0
    new_active = 0
    for node in nodes:
        try:
            if (
                node.state_summary(
                    old_config.bid, old_config.epoch, secrets.token_hex(32)
                ).status["status"]
                == "ACTIVE"
            ):
                old_active += 1
        except PartyStoreError:
            pass
        try:
            if (
                node.state_summary(
                    new_config.bid, new_config.epoch, secrets.token_hex(32)
                ).status["status"]
                == "ACTIVE"
            ):
                new_active += 1
        except PartyStoreError:
            pass
    if old_active >= old_config.quorum or new_active >= new_config.quorum:
        raise DeploymentError("partial lifecycle installation formed a quorum")

    for node in nodes[3:]:
        node.activate_successor_epoch(certificate, old_config, new_config)
    party_restart = "not-requested"
    if restart_checkpoint_dir is not None:
        _wait_for_lifecycle_restart(restart_checkpoint_dir)
        party_restart = "verified"
    retired_probe = AttemptEntry(
        bid=old_config.bid,
        epoch=old_config.epoch,
        config_digest=old_config.digest,
        log_index=installed_index + 1,
        previous_head=installed_head if installed_index else GENESIS_HEAD,
        sid=secrets.token_hex(32),
        request_digest=hash_bytes("LOCUS/retired-epoch-probe/v1", b"request").hex(),
        tpass_request_hash=hash_bytes(
            "LOCUS/tpass-request-bytes/v1", b"retired-probe"
        ).hex(),
        resulting_consumed=consumed + 1,
        effective_budget=budget,
    )
    old_refusal = "unexpected-success"
    try:
        nodes[0].create_entry_vote(retired_probe, old_config)
    except PartyProtocolError:
        old_refusal = "rejected"

    successor_deployment: dict[str, object] = {
        "authorizer_config": new_config.to_dict(),
        "backup": new_backup,
        "parties": deployment["parties"],
        "recovery_id": _base64url(new_recovery_identifier),
        "version": DEPLOYMENT_VERSION,
    }
    successor_result = run_client(
        client_root=client_root,
        resolver_url=resolver_url,
        deployment_override=successor_deployment,
    )
    old_statuses = [
        node.state_summary(
            old_config.bid, old_config.epoch, secrets.token_hex(32)
        ).status["status"]
        for node in nodes
    ]
    new_statuses = [
        node.state_summary(
            new_config.bid, new_config.epoch, secrets.token_hex(32)
        ).status["status"]
        for node in nodes
    ]
    result: dict[str, object] = {
        "cross_epoch_mix": mix_result,
        "old_epoch_refusal": old_refusal,
        "old_epoch_status": (
            "retired" if set(old_statuses) == {"RETIRED"} else "unexpected"
        ),
        "party_restart": party_restart,
        "partial_new_active": new_active,
        "partial_old_active": old_active,
        "successor_epoch_status": (
            "active" if set(new_statuses) == {"ACTIVE"} else "unexpected"
        ),
        "successor_recovery": successor_result["recovery"],
    }
    validate_public_output(result)
    return result


def _positive_port(value: str) -> int:
    try:
        port = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("invalid port") from exc
    if not 1 <= port <= 65535:
        raise argparse.ArgumentTypeError("invalid port")
    return port


def _benchmark_runs(value: str) -> int:
    try:
        runs = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("invalid benchmark run count") from exc
    if not 1 <= runs <= 4:
        raise argparse.ArgumentTypeError("benchmark runs must be between 1 and 4")
    return runs


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run LOCUS deployment roles")
    subparsers = parser.add_subparsers(dest="command", required=True)
    provision_parser = subparsers.add_parser("provision")
    provision_parser.add_argument("--party-root", action="append", required=True)
    provision_parser.add_argument("--client-root", required=True)
    provision_parser.add_argument("--fixture", required=True)
    provision_parser.add_argument("--owner-uid", type=int)
    provision_parser.add_argument("--owner-gid", type=int)
    provision_parser.add_argument("--measure", action="store_true")
    audit_parser = subparsers.add_parser("audit")
    audit_parser.add_argument("--party-root", action="append", required=True)
    audit_parser.add_argument("--client-root", required=True)
    storage_parser = subparsers.add_parser("storage-metric")
    storage_parser.add_argument("--party-root", action="append", required=True)
    storage_parser.add_argument("--client-root", required=True)
    resolver_parser = subparsers.add_parser("resolver")
    resolver_parser.add_argument("--fixture", required=True)
    resolver_parser.add_argument("--host", default="0.0.0.0")
    resolver_parser.add_argument("--port", type=_positive_port, default=RESOLVER_PORT)
    resolver_health_parser = subparsers.add_parser("resolver-health")
    resolver_health_parser.add_argument("--url", required=True)
    party_health_parser = subparsers.add_parser("party-health")
    party_health_parser.add_argument("--root", required=True)
    client_parser = subparsers.add_parser("client")
    client_parser.add_argument("--client-root", required=True)
    client_parser.add_argument("--resolver-url", required=True)
    benchmark_parser = subparsers.add_parser("benchmark")
    benchmark_parser.add_argument("--client-root", required=True)
    benchmark_parser.add_argument("--resolver-url", required=True)
    benchmark_parser.add_argument("--runs", type=_benchmark_runs, default=2)
    performance_parser = subparsers.add_parser("performance")
    performance_parser.add_argument("--client-root", required=True)
    performance_parser.add_argument("--resolver-url", required=True)
    performance_parser.add_argument(
        "--scenario", choices=PERFORMANCE_SCENARIOS, required=True
    )
    performance_parser.add_argument(
        "--runs", type=_benchmark_runs, default=PERFORMANCE_RUNS
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command == "provision":
            started = time.perf_counter()
            status = provision(
                party_roots=[Path(path) for path in args.party_root],
                client_root=Path(args.client_root),
                fixture_path=Path(args.fixture),
                owner_uid=args.owner_uid,
                owner_gid=args.owner_gid,
            )
            if args.measure:
                result: object = validate_provision_metric(
                    {
                        "artifact": PROVISION_METRIC_VERSION,
                        "latency_ms": (time.perf_counter() - started) * 1000,
                        "status": status,
                    }
                )
            else:
                result = {"status": status}
        elif args.command == "audit":
            result = audit_layout(
                [Path(path) for path in args.party_root], Path(args.client_root)
            )
        elif args.command == "storage-metric":
            result = storage_metric(
                [Path(path) for path in args.party_root], Path(args.client_root)
            )
        elif args.command == "resolver":
            serve_resolver(
                fixture_path=Path(args.fixture), host=args.host, port=args.port
            )
            return 0
        elif args.command == "resolver-health":
            resolver_health(args.url)
            return 0
        elif args.command == "party-health":
            party_health(Path(args.root))
            return 0
        elif args.command == "client":
            result = run_client(
                client_root=Path(args.client_root), resolver_url=args.resolver_url
            )
        elif args.command == "benchmark":
            result = run_deployment_benchmark(
                client_root=Path(args.client_root),
                resolver_url=args.resolver_url,
                runs=args.runs,
            )
        elif args.command == "performance":
            result = run_deployment_performance(
                client_root=Path(args.client_root),
                resolver_url=args.resolver_url,
                scenario_id=args.scenario,
                runs=args.runs,
            )
        else:  # pragma: no cover - argparse enforces subcommands.
            raise AssertionError("unknown deployment command")
    except Exception as exc:
        failure: dict[str, object] = {
            "artifact": DEPLOYMENT_VERSION,
            "status": "failed",
        }
        if os.environ.get("LOCUS_OPERATOR_DIAGNOSTICS") == "1":
            failure["error_category"] = type(exc).__name__
        validate_public_output(failure)
        print(_json_bytes(failure).decode("ascii"), file=sys.stderr)
        return 1
    validate_public_output(result)
    print(_json_bytes(result).decode("ascii"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
