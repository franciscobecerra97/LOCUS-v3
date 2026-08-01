from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from locus import _tpass_native as native
from locus.attempt_certificates import AuthorizerConfig, AuthorizerSigner
from locus.clean_client import (
    CLEAN_CLIENT_PROFILE,
    CleanClientError,
    audit_clean_client_surface,
)
from locus.core import (
    BACKUP_VERSION,
    CONTEXT_POLICY_VERSION,
    SECURITY_POLICY_VERSION,
    backup_associated_data,
    derive_wrap_key,
)
from locus.crypto import seal
from locus.object_store import backup_digest
from locus.party_http import RemoteAuthorizerNode, certificate_sha256
from locus.yi_compat import YI_RECOVERY_SUITE_ID

from tests.test_party_http import (
    _base64url,
    _create_ca,
    _create_leaf,
    _free_port,
    _start_party_process,
)

ROOT = Path(__file__).resolve().parents[2]
BACKUP_ID = "71" * 16
RECOVERY_ID = b"LOCUS-clean-client-isolation-test"
RECOVERY_INPUT = b"three-canonical-clean-client-cues"


class CleanClientIsolationTests(unittest.TestCase):
    def test_client_b_recovers_after_client_a_surface_is_removed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            client_a_root = directory / "client-a"
            client_b_root = directory / "client-b"
            client_a_root.mkdir()
            client_b_root.mkdir()
            ca_key, ca_certificate, ca_path = _create_ca(directory)
            client_a_certificate, client_a_key = _create_leaf(
                client_a_root,
                name="client-a",
                ca_key=ca_key,
                ca_certificate=ca_certificate,
                server=False,
            )
            client_b_certificate, client_b_key = _create_leaf(
                client_b_root,
                name="client",
                ca_key=ca_key,
                ca_certificate=ca_certificate,
                server=False,
            )
            shutil.copyfile(ca_path, client_b_root / "ca.pem")
            signers = [AuthorizerSigner.generate(party_id) for party_id in range(1, 6)]
            parameters, states, group_secret = native.setup(
                RECOVERY_ID, RECOVERY_INPUT, 2, 3
            )
            parameter_bytes = bytes(parameters.to_bytes())
            state_bytes = {
                state.party_id: bytes(state.to_secret_bytes()) for state in states
            }
            protected_private_key = bytes(range(32))
            public_key = (
                Ed25519PrivateKey.from_private_bytes(protected_private_key)
                .public_key()
                .public_bytes(
                    serialization.Encoding.Raw, serialization.PublicFormat.Raw
                )
            )
            expected_key_digest = hashlib.sha256(protected_private_key).hexdigest()
            expected_public_fingerprint = hashlib.sha256(public_key).hexdigest()
            nonce = "72" * 16
            backup: dict[str, Any] = {
                "version": BACKUP_VERSION,
                "bid": BACKUP_ID,
                "epoch": 1,
                "nonce": nonce,
                "tpass_public_params": {
                    "backend": "yi-zk-ristretto255-native-v1",
                    "encoding": "LOCUS-TPASS-wire-v1",
                    "parameters": _base64url(parameter_bytes),
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
                derive_wrap_key(bytes(group_secret), BACKUP_ID, 1, nonce),
                protected_private_key,
                aad=backup_associated_data(backup),
            )
            backup["digest"] = backup_digest(backup)
            authorizer_config = AuthorizerConfig(
                bid=BACKUP_ID,
                epoch=1,
                backup_digest=backup["digest"],
                fault_bound=2,
                quorum=4,
                public_keys={
                    signer.party_id: signer.public_key_hex for signer in signers
                },
            )

            server_material: dict[int, tuple[Path, Path, int]] = {}
            peer_material: dict[int, tuple[Path, Path]] = {}
            for party_id in range(1, 6):
                server_certificate, server_key = _create_leaf(
                    directory,
                    name=f"isolation-party-{party_id}",
                    ca_key=ca_key,
                    ca_certificate=ca_certificate,
                    server=True,
                )
                peer_certificate, peer_key = _create_leaf(
                    directory,
                    name=f"isolation-peer-{party_id}",
                    ca_key=ca_key,
                    ca_certificate=ca_certificate,
                    server=False,
                )
                server_material[party_id] = (
                    server_certificate,
                    server_key,
                    _free_port(),
                )
                peer_material[party_id] = (peer_certificate, peer_key)

            def identities(client_certificate: Path) -> list[dict[str, str]]:
                return [
                    {
                        "certificate_sha256": certificate_sha256(client_certificate),
                        "role": "coordinator",
                    },
                    *[
                        {
                            "certificate_sha256": certificate_sha256(
                                peer_material[party_id][0]
                            ),
                            "role": f"party:{party_id}",
                        }
                        for party_id in range(1, 6)
                    ],
                ]

            config_paths: list[Path] = []
            database_paths: list[Path] = []
            party_public: list[dict[str, object]] = []

            def write_party_config(party_id: int, client_certificate: Path) -> Path:
                server_certificate, server_key, port = server_material[party_id]
                peer_certificate, peer_key = peer_material[party_id]
                peers = [
                    {
                        "host": "127.0.0.1",
                        "party_id": other_id,
                        "port": server_material[other_id][2],
                        "server_certificate_sha256": certificate_sha256(
                            server_material[other_id][0]
                        ),
                        "timeout_seconds": 0.5,
                    }
                    for other_id in range(1, 6)
                    if other_id != party_id
                ]
                native_party = (
                    {
                        "outbound_tls": {
                            "client_certificate": str(peer_certificate),
                            "client_private_key": str(peer_key),
                            "server_ca": str(ca_path),
                        },
                        "peers": peers,
                    }
                    if party_id <= 3
                    else None
                )
                path = directory / f"party-{party_id}.json"
                path.write_text(
                    json.dumps(
                        {
                            "authorizer_config": authorizer_config.to_dict(),
                            "budget": 4,
                            "listen_host": "127.0.0.1",
                            "listen_port": port,
                            "native_party": native_party,
                            "party_id": party_id,
                            "signer_private_key": signers[party_id - 1].private_key_hex,
                            "store_path": str(database_paths[party_id - 1]),
                            "tls": {
                                "certificate": str(server_certificate),
                                "client_ca": str(ca_path),
                                "client_identities": identities(client_certificate),
                                "private_key": str(server_key),
                            },
                            "version": "LOCUS-party-service-config-v2",
                        },
                        sort_keys=True,
                    ),
                    encoding="utf-8",
                )
                return path

            for party_id in range(1, 6):
                database_paths.append(directory / f"party-{party_id}.sqlite3")
                config_paths.append(write_party_config(party_id, client_a_certificate))
                party_public.append(
                    {
                        "host": "127.0.0.1",
                        "native_role": party_id <= 3,
                        "party_id": party_id,
                        "port": server_material[party_id][2],
                        "server_certificate_sha256": certificate_sha256(
                            server_material[party_id][0]
                        ),
                    }
                )

            processes: list[subprocess.Popen[bytes]] = []

            def stop_processes() -> None:
                while processes:
                    process = processes.pop()
                    if process.poll() is None:
                        process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=5)
                    if process.stderr is not None:
                        process.stderr.close()
                time.sleep(0.2)

            try:
                processes.extend(
                    _start_party_process(config_path) for config_path in config_paths
                )
                enrollment_nodes = [
                    RemoteAuthorizerNode(
                        party_id=party_id,
                        host="127.0.0.1",
                        port=server_material[party_id][2],
                        server_ca=str(ca_path),
                        client_certificate=str(client_a_certificate),
                        client_private_key=str(client_a_key),
                        server_certificate_sha256=certificate_sha256(
                            server_material[party_id][0]
                        ),
                        timeout_seconds=0.5,
                    )
                    for party_id in range(1, 6)
                ]
                deadline = time.monotonic() + 15
                for party_id, node in enumerate(enrollment_nodes, start=1):
                    while True:
                        try:
                            node.enroll_initial_epoch(
                                authorizer_config,
                                budget=4,
                                recovery_suite_id=(
                                    YI_RECOVERY_SUITE_ID if party_id <= 3 else None
                                ),
                                parameters=(parameter_bytes if party_id <= 3 else None),
                                party_state=(
                                    state_bytes[party_id] if party_id <= 3 else None
                                ),
                            )
                            break
                        except Exception:
                            if time.monotonic() >= deadline:
                                raise
                            time.sleep(0.05)
                stop_processes()

                # Client A is terminated and its entire persistent surface is
                # removed before the recovery transport identity is activated.
                client_a_private_material = client_a_key.read_bytes()
                shutil.rmtree(client_a_root)
                self.assertFalse(client_a_root.exists())
                config_paths = [
                    write_party_config(party_id, client_b_certificate)
                    for party_id in range(1, 6)
                ]
                processes.extend(
                    _start_party_process(config_path) for config_path in config_paths
                )

                recovery_config = {
                    "authorizer_config": authorizer_config.to_dict(),
                    "backup": backup,
                    "parties": party_public,
                    "recovery_id": _base64url(RECOVERY_ID),
                    "tls": {
                        "ca": "ca.pem",
                        "certificate": "client.pem",
                        "private_key": "client-key.pem",
                    },
                    "version": CLEAN_CLIENT_PROFILE,
                }
                (client_b_root / "recovery-config.json").write_text(
                    json.dumps(recovery_config, sort_keys=True, separators=(",", ":")),
                    encoding="ascii",
                )
                isolation = audit_clean_client_surface(
                    client_b_root,
                    unavailable_enrollment_root=client_a_root,
                    forbidden_markers=(
                        protected_private_key,
                        client_a_private_material,
                        RECOVERY_INPUT,
                        *tuple(state_bytes.values()),
                    ),
                )
                self.assertEqual(isolation["status"], "isolated")

                inherited = client_b_root / "client-a-state.json"
                inherited.write_text("{}", encoding="ascii")
                with self.assertRaises(CleanClientError):
                    audit_clean_client_surface(
                        client_b_root,
                        unavailable_enrollment_root=client_a_root,
                        forbidden_markers=(),
                    )
                inherited.unlink()

                environment = {
                    "PYTHONPATH": str(ROOT / "prototype"),
                    "PATH": os.environ.get("PATH", ""),
                }
                if os.name == "nt":
                    environment["SYSTEMROOT"] = os.environ.get("SYSTEMROOT", "")
                process = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        "-m",
                        "locus.clean_client",
                        "--config",
                        str(client_b_root / "recovery-config.json"),
                    ],
                    cwd=ROOT,
                    env=environment,
                    input=json.dumps(
                        {"recovery_input": _base64url(RECOVERY_INPUT)}
                    ).encode("ascii"),
                    capture_output=True,
                    timeout=30,
                    check=False,
                )
                if process.returncode != 0:
                    self.fail(
                        "clean client failed with a privacy-safe rejection: "
                        + process.stdout.decode("ascii", errors="replace")
                    )
                result = json.loads(process.stdout.decode("ascii"))
                self.assertEqual(result["status"], "recovered")
                self.assertEqual(result["key_sha256"], expected_key_digest)
                self.assertEqual(
                    result["public_fingerprint"], expected_public_fingerprint
                )
                self.assertNotIn(protected_private_key, process.stdout)
                self.assertNotIn(RECOVERY_INPUT, process.stdout)
                self.assertEqual(process.stderr, b"")
            finally:
                stop_processes()


if __name__ == "__main__":
    unittest.main()
