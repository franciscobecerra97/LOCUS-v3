from __future__ import annotations

import base64
import http.client
import ipaddress
import json
import os
import socket
import ssl
import subprocess
import sys
import tempfile
import time
import unittest
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID
from locus import _tpass_native as native
from locus.attempt_certificates import (
    AttemptEntry,
    AuthorizerConfig,
    AuthorizerSigner,
)
from locus.attempt_coordinator import AttemptCoordinator, CoordinatorError
from locus.core import (
    BACKUP_VERSION,
    CONTEXT_POLICY_VERSION,
    SECURITY_POLICY_VERSION,
    backup_associated_data,
    derive_wrap_key,
)
from locus.crypto import hash_bytes, open_sealed, random_bytes, seal
from locus.object_store import (
    BackupReference,
    FilesystemBackupObjectStore,
    backup_digest,
)
from locus.party_http import (
    API_VERSION,
    PartyHttpError,
    RemoteAuthorizerNode,
    RemotePartyClient,
    certificate_sha256,
)
from locus.party_store import GENESIS_HEAD, Conflict, PartyStoreError

BID = "ab" * 16
BACKUP_DIGEST = "bc" * 32
ROOT = Path(__file__).resolve().parents[2]
RECOVERY_ID = b"remote-native-party-test"
RECOVERY_INPUT = b"three-canonical-cue-pairs"


@dataclass(frozen=True)
class _PartyEndpoint:
    party_id: int
    port: int
    server_certificate: Path
    server_key: Path
    peer_certificate: Path
    peer_key: Path


def _write_private_key(path: Path, key: Ed25519PrivateKey) -> None:
    path.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )


def _write_certificate(path: Path, certificate: x509.Certificate) -> None:
    path.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))


def _create_ca(directory: Path) -> tuple[Ed25519PrivateKey, x509.Certificate, Path]:
    key = Ed25519PrivateKey.generate()
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "LOCUS test CA")])
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
    path = directory / "ca.pem"
    _write_certificate(path, certificate)
    return key, certificate, path


def _create_leaf(
    directory: Path,
    *,
    name: str,
    ca_key: Ed25519PrivateKey,
    ca_certificate: x509.Certificate,
    server: bool,
) -> tuple[Path, Path]:
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
                    x509.DNSName("localhost"),
                    x509.IPAddress(ipaddress.ip_address("127.0.0.1")),
                ]
            ),
            critical=False,
        )
    certificate = builder.sign(ca_key, algorithm=None)
    certificate_path = directory / f"{name}.pem"
    key_path = directory / f"{name}-key.pem"
    _write_certificate(certificate_path, certificate)
    _write_private_key(key_path, key)
    return certificate_path, key_path


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def _base64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _start_party_process(config_path: Path) -> subprocess.Popen[bytes]:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(ROOT / "prototype")
    creation_flags = (
        int(getattr(subprocess, "CREATE_NO_WINDOW", 0)) if os.name == "nt" else 0
    )
    return subprocess.Popen(
        [
            sys.executable,
            "-B",
            "-m",
            "locus.party_http",
            "--config",
            str(config_path),
        ],
        cwd=ROOT,
        env=environment,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        creationflags=creation_flags,
    )


def _attempt(
    config: AuthorizerConfig,
    *,
    index: int,
    previous_head: str,
    marker: str,
    request: bytes | None = None,
    budget: int = 3,
) -> AttemptEntry:
    sid = marker * 32
    request_digest = (
        ("1" + marker[0]) * 32
        if request is None
        else hash_bytes(
            "LOCUS/test-request-digest/v1", sid.encode("ascii"), request
        ).hex()
    )
    tpass_request_hash = (
        ("2" + marker[0]) * 32
        if request is None
        else hash_bytes("LOCUS/tpass-request-bytes/v1", request).hex()
    )
    return AttemptEntry(
        bid=BID,
        epoch=1,
        config_digest=config.digest,
        log_index=index,
        previous_head=previous_head,
        sid=sid,
        request_digest=request_digest,
        tpass_request_hash=tpass_request_hash,
        resulting_consumed=index,
        effective_budget=budget,
    )


class PartyHttpIntegrationTests(unittest.TestCase):
    def test_remote_quorum_authentication_failure_and_process_recovery(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            ca_key, ca_certificate, ca_path = _create_ca(directory)
            client_certificate, client_key = _create_leaf(
                directory,
                name="coordinator",
                ca_key=ca_key,
                ca_certificate=ca_certificate,
                server=False,
            )
            unauthorized_certificate, unauthorized_key = _create_leaf(
                directory,
                name="unauthorized-coordinator",
                ca_key=ca_key,
                ca_certificate=ca_certificate,
                server=False,
            )
            peer_certificate, peer_key = _create_leaf(
                directory,
                name="party-peer-1",
                ca_key=ca_key,
                ca_certificate=ca_certificate,
                server=False,
            )
            client_fingerprint = certificate_sha256(client_certificate)
            peer_fingerprint = certificate_sha256(peer_certificate)
            signers = [AuthorizerSigner.generate(party_id) for party_id in range(1, 6)]
            config = AuthorizerConfig(
                bid=BID,
                epoch=1,
                backup_digest=BACKUP_DIGEST,
                fault_bound=2,
                quorum=4,
                public_keys={
                    signer.party_id: signer.public_key_hex for signer in signers
                },
            )
            processes: list[subprocess.Popen[bytes]] = []
            config_paths: list[Path] = []
            nodes: list[RemoteAuthorizerNode] = []
            peer_nodes: list[RemoteAuthorizerNode] = []

            def start(config_path: Path) -> subprocess.Popen[bytes]:
                return _start_party_process(config_path)

            try:
                for signer in signers:
                    server_certificate, server_key = _create_leaf(
                        directory,
                        name=f"party-{signer.party_id}",
                        ca_key=ca_key,
                        ca_certificate=ca_certificate,
                        server=True,
                    )
                    port = _free_port()
                    config_path = directory / f"party-{signer.party_id}.json"
                    config_path.write_text(
                        json.dumps(
                            {
                                "authorizer_config": config.to_dict(),
                                "budget": 3,
                                "listen_host": "127.0.0.1",
                                "listen_port": port,
                                "native_party": None,
                                "party_id": signer.party_id,
                                "signer_private_key": signer.private_key_hex,
                                "store_path": str(
                                    directory / f"party-{signer.party_id}.sqlite3"
                                ),
                                "tls": {
                                    "client_identities": [
                                        {
                                            "certificate_sha256": client_fingerprint,
                                            "role": "coordinator",
                                        },
                                        {
                                            "certificate_sha256": peer_fingerprint,
                                            "role": "party:1",
                                        },
                                    ],
                                    "certificate": str(server_certificate),
                                    "client_ca": str(ca_path),
                                    "private_key": str(server_key),
                                },
                                "version": "LOCUS-party-service-config-v1",
                            },
                            sort_keys=True,
                        ),
                        encoding="utf-8",
                    )
                    config_paths.append(config_path)
                    processes.append(start(config_path))
                    nodes.append(
                        RemoteAuthorizerNode(
                            party_id=signer.party_id,
                            host="127.0.0.1",
                            port=port,
                            server_ca=str(ca_path),
                            client_certificate=str(client_certificate),
                            client_private_key=str(client_key),
                            server_certificate_sha256=certificate_sha256(
                                server_certificate
                            ),
                            timeout_seconds=2.0,
                        )
                    )
                    peer_nodes.append(
                        RemoteAuthorizerNode(
                            party_id=signer.party_id,
                            host="127.0.0.1",
                            port=port,
                            server_ca=str(ca_path),
                            client_certificate=str(peer_certificate),
                            client_private_key=str(peer_key),
                            server_certificate_sha256=certificate_sha256(
                                server_certificate
                            ),
                            timeout_seconds=2.0,
                        )
                    )

                deadline = time.monotonic() + 10
                for process, node in zip(processes, nodes, strict=True):
                    while True:
                        if process.poll() is not None:
                            stderr = (
                                process.stderr.read().decode("utf-8", errors="replace")
                                if process.stderr is not None
                                else ""
                            )
                            self.fail(f"party service exited during startup: {stderr}")
                        try:
                            summary = node.state_summary(BID, 1, "00" * 32)
                            self.assertEqual(
                                summary.status["backup_digest"],
                                config.backup_digest,
                            )
                            break
                        except PartyStoreError:
                            if time.monotonic() >= deadline:
                                self.fail("party service did not become ready")
                            time.sleep(0.05)

                # A different valid client certificate chains to the CA but is not
                # the enrollment-pinned coordinator identity.
                unauthorized_tls = ssl.create_default_context(
                    ssl.Purpose.SERVER_AUTH, cafile=str(ca_path)
                )
                unauthorized_tls.minimum_version = ssl.TLSVersion.TLSv1_3
                unauthorized_tls.load_cert_chain(
                    unauthorized_certificate, unauthorized_key
                )
                unauthorized = http.client.HTTPSConnection(
                    "127.0.0.1",
                    nodes[0].port,
                    context=unauthorized_tls,
                    timeout=2,
                )
                unauthorized.request("GET", "/health/live")
                self.assertEqual(unauthorized.getresponse().status, 403)
                unauthorized.close()

                # An allowed peer still receives a generic rejection for a
                # noncanonical envelope with duplicate members.
                allowed_tls = ssl.create_default_context(
                    ssl.Purpose.SERVER_AUTH, cafile=str(ca_path)
                )
                allowed_tls.minimum_version = ssl.TLSVersion.TLSv1_3
                allowed_tls.load_cert_chain(client_certificate, client_key)
                malformed = http.client.HTTPSConnection(
                    "127.0.0.1", nodes[0].port, context=allowed_tls, timeout=2
                )
                malformed.request(
                    "POST",
                    "/v1/ledger/state-summaries",
                    body=(
                        b'{"api_version":"'
                        + API_VERSION.encode("ascii")
                        + b'","api_version":"duplicate","request":{}}'
                    ),
                    headers={"Content-Type": "application/json"},
                )
                malformed_response = malformed.getresponse()
                self.assertEqual(malformed_response.status, 400)
                malformed_error = json.loads(malformed_response.read())
                self.assertEqual(
                    malformed_error,
                    {
                        "api_version": API_VERSION,
                        "error": {"code": "invalid_request"},
                        "party_id": 1,
                    },
                )
                malformed.close()

                first_attempt = _attempt(
                    config, index=1, previous_head=GENESIS_HEAD, marker="33"
                )
                missing_key = http.client.HTTPSConnection(
                    "127.0.0.1", nodes[0].port, context=allowed_tls, timeout=2
                )
                missing_key.request(
                    "POST",
                    "/v1/ledger/entry-votes",
                    body=json.dumps(
                        {
                            "api_version": API_VERSION,
                            "request": {"entry": first_attempt.to_dict()},
                        },
                        sort_keys=True,
                        separators=(",", ":"),
                    ).encode("ascii"),
                    headers={"Content-Type": "application/json"},
                )
                missing_key_response = missing_key.getresponse()
                self.assertEqual(missing_key_response.status, 400)
                self.assertEqual(
                    json.loads(missing_key_response.read()),
                    {
                        "api_version": API_VERSION,
                        "error": {"code": "invalid_request"},
                        "party_id": 1,
                    },
                )
                missing_key.close()

                # Two logical coordinator clients sharing the same enrolled
                # identity receive one durable result for the same explicit key.
                alternate_coordinator = RemoteAuthorizerNode(
                    party_id=1,
                    host=nodes[0].host,
                    port=nodes[0].port,
                    server_ca=str(ca_path),
                    client_certificate=str(client_certificate),
                    client_private_key=str(client_key),
                    server_certificate_sha256=nodes[0].server_certificate_sha256,
                    timeout_seconds=2.0,
                )
                shared_key = "91" * 32
                direct_vote = nodes[0].create_entry_vote(
                    first_attempt, config, idempotency_key=shared_key
                )
                self.assertEqual(
                    alternate_coordinator.create_entry_vote(
                        first_attempt, config, idempotency_key=shared_key
                    ),
                    direct_vote,
                )
                changed_attempt = _attempt(
                    config, index=1, previous_head=GENESIS_HEAD, marker="34"
                )
                with self.assertRaises(Conflict):
                    alternate_coordinator.create_entry_vote(
                        changed_attempt, config, idempotency_key=shared_key
                    )

                coordinator = AttemptCoordinator(config=config, nodes=list(nodes))
                first = coordinator.authorize(first_attempt)
                self.assertEqual(
                    coordinator.authorize(first_attempt).certificate_hash,
                    first.certificate_hash,
                )

                processes[0].terminate()
                processes[0].wait(timeout=5)
                if processes[0].stderr is not None:
                    processes[0].stderr.close()
                second_attempt = _attempt(
                    config,
                    index=2,
                    previous_head=first_attempt.entry_hash,
                    marker="44",
                )
                second = coordinator.authorize(second_attempt)
                with self.assertRaises(CoordinatorError):
                    coordinator.certify_freshness(
                        authorization=second,
                        responding_party_id=1,
                        boot_nonce="55" * 32,
                        response_nonce="66" * 32,
                    )
                freshness_coordinator = AttemptCoordinator(
                    config=config, nodes=list(peer_nodes)
                )
                freshness = freshness_coordinator.certify_freshness(
                    authorization=second,
                    responding_party_id=1,
                    boot_nonce="55" * 32,
                    response_nonce="66" * 32,
                )
                freshness.verify(config)
                self.assertTrue(
                    all(
                        int(node.state_summary(BID, 1, "77" * 32).status["consumed"])
                        == 2
                        for node in nodes[1:]
                    )
                )

                # Restarting the failed process over the same private database lets
                # the untrusted coordinator catch it up from the installed quorum.
                processes[0] = start(config_paths[0])
                deadline = time.monotonic() + 10
                while True:
                    try:
                        nodes[0].state_summary(BID, 1, "00" * 32)
                        break
                    except PartyStoreError:
                        if processes[0].poll() is not None:
                            stderr = (
                                processes[0]
                                .stderr.read()
                                .decode("utf-8", errors="replace")
                                if processes[0].stderr is not None
                                else ""
                            )
                            self.fail(f"restarted party service exited: {stderr}")
                        if time.monotonic() >= deadline:
                            self.fail("restarted party service did not become ready")
                        time.sleep(0.05)
                reconciled = coordinator.authorize(second_attempt)
                self.assertEqual(reconciled.certificate_hash, second.certificate_hash)
                self.assertEqual(
                    alternate_coordinator.create_entry_vote(
                        first_attempt, config, idempotency_key=shared_key
                    ),
                    direct_vote,
                )
                self.assertEqual(
                    nodes[0].state_summary(BID, 1, "77" * 32).status["consumed"],
                    2,
                )

                database_paths = {
                    str(directory / f"party-{party_id}.sqlite3")
                    for party_id in range(1, 6)
                }
                self.assertEqual(len(database_paths), 5)
                self.assertTrue(all(Path(path).is_file() for path in database_paths))
            finally:
                for process in processes:
                    if process.poll() is None:
                        process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=5)
                    if process.stderr is not None:
                        process.stderr.close()
                if os.name == "nt":
                    # TerminateProcess can report exit just before the final
                    # SQLite file handles become deletable on loaded CI hosts.
                    time.sleep(0.2)

    def test_native_recovery_crosses_authenticated_party_processes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            ca_key, ca_certificate, ca_path = _create_ca(directory)
            coordinator_certificate, coordinator_key = _create_leaf(
                directory,
                name="native-coordinator",
                ca_key=ca_key,
                ca_certificate=ca_certificate,
                server=False,
            )
            signers = [AuthorizerSigner.generate(party_id) for party_id in range(1, 6)]
            parameters, states, expected_secret = native.setup(
                RECOVERY_ID, RECOVERY_INPUT, 2, 3
            )
            encoded_parameters = _base64url(bytes(parameters.to_bytes()))
            recovery_nonce = random_bytes(16).hex()
            stored_private_key = b"remote-separated-cloud-private-key"
            backup: dict[str, Any] = {
                "version": BACKUP_VERSION,
                "bid": BID,
                "epoch": 1,
                "nonce": recovery_nonce,
                "tpass_public_params": {
                    "backend": "yi-zk-ristretto255-native-v1",
                    "encoding": "LOCUS-TPASS-wire-v1",
                    "parameters": encoded_parameters,
                    "threshold": 2,
                    "parties": 3,
                },
                "context_policy": {"version": CONTEXT_POLICY_VERSION},
                "security_policy": {
                    "version": SECURITY_POLICY_VERSION,
                    "max_attempts": 4,
                    "cooldown_seconds": 0,
                },
            }
            backup["ciphertext"] = seal(
                derive_wrap_key(bytes(expected_secret), BID, 1, recovery_nonce),
                stored_private_key,
                aad=backup_associated_data(backup),
            )
            backup["digest"] = backup_digest(backup)
            cloud_store = FilesystemBackupObjectStore(directory / "cloud-objects")
            cloud_reference = cloud_store.create(backup)
            config = AuthorizerConfig(
                bid=BID,
                epoch=1,
                backup_digest=cloud_reference.backup_digest,
                fault_bound=2,
                quorum=4,
                public_keys={
                    signer.party_id: signer.public_key_hex for signer in signers
                },
            )
            endpoints: list[_PartyEndpoint] = []
            for party_id in range(1, 6):
                server_certificate, server_key = _create_leaf(
                    directory,
                    name=f"native-party-{party_id}",
                    ca_key=ca_key,
                    ca_certificate=ca_certificate,
                    server=True,
                )
                peer_certificate, peer_key = _create_leaf(
                    directory,
                    name=f"native-party-peer-{party_id}",
                    ca_key=ca_key,
                    ca_certificate=ca_certificate,
                    server=False,
                )
                endpoints.append(
                    _PartyEndpoint(
                        party_id=party_id,
                        port=_free_port(),
                        server_certificate=server_certificate,
                        server_key=server_key,
                        peer_certificate=peer_certificate,
                        peer_key=peer_key,
                    )
                )

            client_identities = [
                {
                    "certificate_sha256": certificate_sha256(coordinator_certificate),
                    "role": "coordinator",
                },
                *[
                    {
                        "certificate_sha256": certificate_sha256(
                            endpoint.peer_certificate
                        ),
                        "role": f"party:{endpoint.party_id}",
                    }
                    for endpoint in endpoints
                ],
            ]
            encoded_states = {
                state.party_id: _base64url(bytes(state.to_secret_bytes()))
                for state in states
            }
            config_paths: list[Path] = []
            processes: list[subprocess.Popen[bytes]] = []
            nodes: list[RemoteAuthorizerNode] = []
            native_clients: dict[int, RemotePartyClient] = {}

            try:
                for endpoint, signer in zip(endpoints, signers, strict=True):
                    peers = [
                        {
                            "host": "127.0.0.1",
                            "party_id": peer.party_id,
                            "port": peer.port,
                            "server_certificate_sha256": certificate_sha256(
                                peer.server_certificate
                            ),
                            "timeout_seconds": 0.5,
                        }
                        for peer in endpoints
                        if peer.party_id != endpoint.party_id
                    ]
                    native_config = (
                        {
                            "outbound_tls": {
                                "client_certificate": str(endpoint.peer_certificate),
                                "client_private_key": str(endpoint.peer_key),
                                "server_ca": str(ca_path),
                            },
                            "parameters": encoded_parameters,
                            "peers": peers,
                            "state": encoded_states[endpoint.party_id],
                        }
                        if endpoint.party_id <= 3
                        else None
                    )
                    config_path = directory / f"native-party-{endpoint.party_id}.json"
                    config_path.write_text(
                        json.dumps(
                            {
                                "authorizer_config": config.to_dict(),
                                "budget": 4,
                                "listen_host": "127.0.0.1",
                                "listen_port": endpoint.port,
                                "native_party": native_config,
                                "party_id": endpoint.party_id,
                                "signer_private_key": signer.private_key_hex,
                                "store_path": str(
                                    directory
                                    / f"native-party-{endpoint.party_id}.sqlite3"
                                ),
                                "tls": {
                                    "certificate": str(endpoint.server_certificate),
                                    "client_ca": str(ca_path),
                                    "client_identities": client_identities,
                                    "private_key": str(endpoint.server_key),
                                },
                                "version": "LOCUS-party-service-config-v1",
                            },
                            sort_keys=True,
                        ),
                        encoding="utf-8",
                    )
                    config_paths.append(config_path)
                    nodes.append(
                        RemoteAuthorizerNode(
                            party_id=endpoint.party_id,
                            host="127.0.0.1",
                            port=endpoint.port,
                            server_ca=str(ca_path),
                            client_certificate=str(coordinator_certificate),
                            client_private_key=str(coordinator_key),
                            server_certificate_sha256=certificate_sha256(
                                endpoint.server_certificate
                            ),
                            timeout_seconds=0.5,
                        )
                    )
                    if endpoint.party_id <= 3:
                        native_clients[endpoint.party_id] = RemotePartyClient(
                            party_id=endpoint.party_id,
                            host="127.0.0.1",
                            port=endpoint.port,
                            server_ca=str(ca_path),
                            client_certificate=str(coordinator_certificate),
                            client_private_key=str(coordinator_key),
                            server_certificate_sha256=certificate_sha256(
                                endpoint.server_certificate
                            ),
                            timeout_seconds=2.0,
                        )

                # Each native service configuration contains only its own secret
                # state; authorizer-only services contain none.
                for party_id, config_path in enumerate(config_paths, start=1):
                    encoded_config = config_path.read_text(encoding="utf-8")
                    if party_id <= 3:
                        self.assertIn(encoded_states[party_id], encoded_config)
                        self.assertTrue(
                            all(
                                encoded_state not in encoded_config
                                for other_id, encoded_state in encoded_states.items()
                                if other_id != party_id
                            )
                        )
                    else:
                        self.assertIn('"native_party": null', encoded_config)
                    self.assertNotIn(backup["ciphertext"]["ciphertext"], encoded_config)

                cloud_snapshot = (
                    cloud_store.root / cloud_reference.bid / "1.json"
                ).read_text(encoding="utf-8")
                self.assertIn(backup["ciphertext"]["ciphertext"], cloud_snapshot)
                for encoded_state in encoded_states.values():
                    self.assertNotIn(encoded_state, cloud_snapshot)

                processes.extend(
                    _start_party_process(config_path) for config_path in config_paths
                )
                deadline = time.monotonic() + 15
                for process, node in zip(processes, nodes, strict=True):
                    while True:
                        if process.poll() is not None:
                            stderr = (
                                process.stderr.read().decode("utf-8", errors="replace")
                                if process.stderr is not None
                                else ""
                            )
                            self.fail(f"native party exited during startup: {stderr}")
                        try:
                            summary = node.state_summary(BID, 1, "00" * 32)
                            self.assertEqual(
                                summary.status["backup_digest"],
                                cloud_reference.backup_digest,
                            )
                            break
                        except PartyStoreError:
                            if time.monotonic() >= deadline:
                                self.fail("native party did not become ready")
                            time.sleep(0.05)

                coordinator = AttemptCoordinator(config=config, nodes=list(nodes))
                pinned_reference = BackupReference(
                    bid=config.bid,
                    epoch=config.epoch,
                    backup_digest=config.backup_digest,
                )
                self.assertEqual(pinned_reference, cloud_reference)
                stored_backup = cloud_store.read(pinned_reference)
                session = native.begin_recovery(parameters, RECOVERY_ID, RECOVERY_INPUT)
                request = bytes(session.request_bytes())
                first_entry = _attempt(
                    config,
                    index=1,
                    previous_head=GENESIS_HEAD,
                    marker="31",
                    request=request,
                    budget=4,
                )
                first = coordinator.authorize(first_entry)
                selected = [1, 3]
                commitment_results = [
                    native_clients[party_id].prepare_commitment(
                        sid=first_entry.sid,
                        authorization_certificate=first,
                        request=request,
                        selected=selected,
                    )
                    for party_id in selected
                ]
                retry = native_clients[1].prepare_commitment(
                    sid=first_entry.sid,
                    authorization_certificate=first,
                    request=request,
                    selected=selected,
                )
                self.assertEqual(retry, commitment_results[0])
                commitments = [result.commitment for result in commitment_results]
                with self.assertRaises(PartyStoreError):
                    native_clients[1].respond(
                        sid="ff" * 32,
                        phase_instance_id=commitment_results[0].phase_instance_id,
                        request=request,
                        selected=selected,
                        commitments=commitments,
                    )
                responses = [
                    native_clients[party_id].respond(
                        sid=first_entry.sid,
                        phase_instance_id=result.phase_instance_id,
                        request=request,
                        selected=selected,
                        commitments=commitments,
                    )
                    for party_id, result in zip(
                        selected, commitment_results, strict=True
                    )
                ]
                response_retry = native_clients[1].respond(
                    sid=first_entry.sid,
                    phase_instance_id=commitment_results[0].phase_instance_id,
                    request=request,
                    selected=selected,
                    commitments=commitments,
                )
                self.assertEqual(response_retry, responses[0])
                replay_key = "92" * 32
                self.assertEqual(
                    native_clients[1].respond(
                        sid=first_entry.sid,
                        phase_instance_id=commitment_results[0].phase_instance_id,
                        request=request,
                        selected=selected,
                        commitments=commitments,
                        idempotency_key=replay_key,
                    ),
                    responses[0],
                )
                with self.assertRaises(Conflict):
                    native_clients[1].respond(
                        sid="fe" * 32,
                        phase_instance_id=commitment_results[0].phase_instance_id,
                        request=request,
                        selected=selected,
                        commitments=commitments,
                        idempotency_key=replay_key,
                    )
                gateway = native.aggregate_responses(
                    parameters, request, selected, commitments, responses
                )
                recovered_secret = native.finish_recovery(parameters, session, gateway)
                self.assertEqual(recovered_secret, expected_secret)
                self.assertEqual(
                    open_sealed(
                        derive_wrap_key(
                            bytes(recovered_secret),
                            stored_backup["bid"],
                            stored_backup["epoch"],
                            stored_backup["nonce"],
                        ),
                        stored_backup["ciphertext"],
                        aad=backup_associated_data(stored_backup),
                    ),
                    stored_private_key,
                )

                wrong_session = native.begin_recovery(
                    parameters, RECOVERY_ID, b"incorrect-recovery-input"
                )
                wrong_request = bytes(wrong_session.request_bytes())
                second_entry = _attempt(
                    config,
                    index=2,
                    previous_head=first_entry.entry_hash,
                    marker="42",
                    request=wrong_request,
                    budget=4,
                )
                second = coordinator.authorize(second_entry)
                wrong_selected = [2, 3]
                wrong_commitment_results = [
                    native_clients[party_id].prepare_commitment(
                        sid=second_entry.sid,
                        authorization_certificate=second,
                        request=wrong_request,
                        selected=wrong_selected,
                    )
                    for party_id in wrong_selected
                ]
                wrong_commitments = [
                    result.commitment for result in wrong_commitment_results
                ]
                wrong_responses = [
                    native_clients[party_id].respond(
                        sid=second_entry.sid,
                        phase_instance_id=result.phase_instance_id,
                        request=wrong_request,
                        selected=wrong_selected,
                        commitments=wrong_commitments,
                    )
                    for party_id, result in zip(
                        wrong_selected, wrong_commitment_results, strict=True
                    )
                ]
                wrong_gateway = native.aggregate_responses(
                    parameters,
                    wrong_request,
                    wrong_selected,
                    wrong_commitments,
                    wrong_responses,
                )
                with self.assertRaises(native.NativeTpassError):
                    native.finish_recovery(parameters, wrong_session, wrong_gateway)

                # The compact authorizer profile continues with one process down;
                # the selected TPASS subset excludes that process.
                processes[0].terminate()
                processes[0].wait(timeout=5)
                if processes[0].stderr is not None:
                    processes[0].stderr.close()
                final_session = native.begin_recovery(
                    parameters, RECOVERY_ID, RECOVERY_INPUT
                )
                final_request = bytes(final_session.request_bytes())
                third_entry = _attempt(
                    config,
                    index=3,
                    previous_head=second_entry.entry_hash,
                    marker="53",
                    request=final_request,
                    budget=4,
                )
                third = coordinator.authorize(third_entry)
                final_selected = [2, 3]
                final_commitment_results = [
                    native_clients[party_id].prepare_commitment(
                        sid=third_entry.sid,
                        authorization_certificate=third,
                        request=final_request,
                        selected=final_selected,
                    )
                    for party_id in final_selected
                ]
                final_commitments = [
                    result.commitment for result in final_commitment_results
                ]
                final_responses = [
                    native_clients[party_id].respond(
                        sid=third_entry.sid,
                        phase_instance_id=result.phase_instance_id,
                        request=final_request,
                        selected=final_selected,
                        commitments=final_commitments,
                    )
                    for party_id, result in zip(
                        final_selected, final_commitment_results, strict=True
                    )
                ]
                final_gateway = native.aggregate_responses(
                    parameters,
                    final_request,
                    final_selected,
                    final_commitments,
                    final_responses,
                )
                self.assertEqual(
                    native.finish_recovery(parameters, final_session, final_gateway),
                    expected_secret,
                )

                processes[0] = _start_party_process(config_paths[0])
                deadline = time.monotonic() + 15
                while True:
                    try:
                        nodes[0].state_summary(BID, 1, "00" * 32)
                        break
                    except PartyStoreError:
                        if processes[0].poll() is not None:
                            stderr = (
                                processes[0]
                                .stderr.read()
                                .decode("utf-8", errors="replace")
                                if processes[0].stderr is not None
                                else ""
                            )
                            self.fail(f"restarted native party exited: {stderr}")
                        if time.monotonic() >= deadline:
                            self.fail("restarted native party did not become ready")
                        time.sleep(0.05)
                reconciled = coordinator.authorize(third_entry)
                self.assertEqual(reconciled.certificate_hash, third.certificate_hash)
                self.assertEqual(
                    native_clients[1].respond(
                        sid=first_entry.sid,
                        phase_instance_id=commitment_results[0].phase_instance_id,
                        request=request,
                        selected=selected,
                        commitments=commitments,
                    ),
                    responses[0],
                )

                lost_session = native.begin_recovery(
                    parameters, RECOVERY_ID, RECOVERY_INPUT
                )
                lost_request = bytes(lost_session.request_bytes())
                fourth_entry = _attempt(
                    config,
                    index=4,
                    previous_head=third_entry.entry_hash,
                    marker="64",
                    request=lost_request,
                    budget=4,
                )
                fourth = coordinator.authorize(fourth_entry)
                lost_result = native_clients[1].prepare_commitment(
                    sid=fourth_entry.sid,
                    authorization_certificate=fourth,
                    request=lost_request,
                    selected=[1, 3],
                )
                processes[0].terminate()
                processes[0].wait(timeout=5)
                if processes[0].stderr is not None:
                    processes[0].stderr.close()
                processes[0] = _start_party_process(config_paths[0])
                deadline = time.monotonic() + 15
                while True:
                    try:
                        nodes[0].state_summary(BID, 1, "00" * 32)
                        break
                    except PartyStoreError:
                        if processes[0].poll() is not None:
                            self.fail("party with open TPASS phase did not restart")
                        if time.monotonic() >= deadline:
                            self.fail("party with open TPASS phase was not ready")
                        time.sleep(0.05)
                self.assertEqual(
                    native_clients[1].prepare_commitment(
                        sid=fourth_entry.sid,
                        authorization_certificate=fourth,
                        request=lost_request,
                        selected=[1, 3],
                    ),
                    lost_result,
                )
                with self.assertRaises(PartyHttpError):
                    native_clients[1].respond(
                        sid=fourth_entry.sid,
                        phase_instance_id=lost_result.phase_instance_id,
                        request=lost_request,
                        selected=[1, 3],
                        commitments=[lost_result.commitment, lost_result.commitment],
                    )
                self.assertTrue(
                    all(
                        node.state_summary(BID, 1, "00" * 32).status["consumed"] == 4
                        for node in nodes
                    )
                )
            finally:
                for process in processes:
                    if process.poll() is None:
                        process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=5)
                    if process.stderr is not None:
                        process.stderr.close()
                if os.name == "nt":
                    time.sleep(0.2)


if __name__ == "__main__":
    unittest.main()
