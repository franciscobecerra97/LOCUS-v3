from __future__ import annotations

import json
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

from locus import _tpass_native as native
from locus.attempt_certificates import AuthorizerConfig, AuthorizerSigner
from locus.party_http import (
    ENROLLMENT_TRANSPORT_PROFILE,
    PartyProtocolError,
    PartyUnavailable,
    RemoteAuthorizerNode,
    certificate_sha256,
)
from locus.party_store import Conflict, PartyStore
from locus.yi_compat import YI_RECOVERY_SUITE_ID

from tests.test_party_http import (
    BID,
    _base64url,
    _create_ca,
    _create_leaf,
    _free_port,
    _start_party_process,
)


class AuthenticatedEnrollmentTransportTests(unittest.TestCase):
    def test_recipient_bound_enrollment_across_clean_party_processes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            ca_key, ca_certificate, ca_path = _create_ca(directory)
            coordinator_certificate, coordinator_key = _create_leaf(
                directory,
                name="enrollment-coordinator",
                ca_key=ca_key,
                ca_certificate=ca_certificate,
                server=False,
            )
            peer_certificate, peer_key = _create_leaf(
                directory,
                name="enrollment-party-peer",
                ca_key=ca_key,
                ca_certificate=ca_certificate,
                server=False,
            )
            signers = [AuthorizerSigner.generate(party_id) for party_id in (1, 2)]
            config = AuthorizerConfig(
                bid=BID,
                epoch=1,
                backup_digest="cd" * 32,
                fault_bound=0,
                quorum=2,
                public_keys={
                    signer.party_id: signer.public_key_hex for signer in signers
                },
            )
            parameters, states, _ = native.setup(b"enrollment", b"cue", 1, 2)
            parameter_bytes = bytes(parameters.to_bytes())
            state_bytes = {
                state.party_id: bytes(state.to_secret_bytes()) for state in states
            }
            server_material: dict[int, tuple[Path, Path, int]] = {}
            for party_id in (1, 2):
                certificate, key = _create_leaf(
                    directory,
                    name=f"enrollment-party-{party_id}",
                    ca_key=ca_key,
                    ca_certificate=ca_certificate,
                    server=True,
                )
                server_material[party_id] = (certificate, key, _free_port())

            client_identities = [
                {
                    "certificate_sha256": certificate_sha256(coordinator_certificate),
                    "role": "coordinator",
                },
                {
                    "certificate_sha256": certificate_sha256(peer_certificate),
                    "role": "party:1",
                },
            ]
            config_paths: list[Path] = []
            nodes: list[RemoteAuthorizerNode] = []
            processes: list[subprocess.Popen[bytes]] = []
            database_paths: list[Path] = []
            try:
                for party_id, signer in enumerate(signers, start=1):
                    certificate, key, port = server_material[party_id]
                    database_path = directory / f"party-{party_id}.sqlite3"
                    database_paths.append(database_path)
                    native_party = None
                    if party_id == 1:
                        peer_certificate_path, _, peer_port = server_material[2]
                        native_party = {
                            "outbound_tls": {
                                "client_certificate": str(peer_certificate),
                                "client_private_key": str(peer_key),
                                "server_ca": str(ca_path),
                            },
                            "peers": [
                                {
                                    "host": "127.0.0.1",
                                    "party_id": 2,
                                    "port": peer_port,
                                    "server_certificate_sha256": certificate_sha256(
                                        peer_certificate_path
                                    ),
                                    "timeout_seconds": 0.5,
                                }
                            ],
                        }
                    config_path = directory / f"party-{party_id}.json"
                    config_path.write_text(
                        json.dumps(
                            {
                                "authorizer_config": config.to_dict(),
                                "budget": 3,
                                "listen_host": "127.0.0.1",
                                "listen_port": port,
                                "native_party": native_party,
                                "party_id": party_id,
                                "signer_private_key": signer.private_key_hex,
                                "store_path": str(database_path),
                                "tls": {
                                    "certificate": str(certificate),
                                    "client_ca": str(ca_path),
                                    "client_identities": client_identities,
                                    "private_key": str(key),
                                },
                                "version": "LOCUS-party-service-config-v2",
                            },
                            sort_keys=True,
                        ),
                        encoding="utf-8",
                    )
                    config_paths.append(config_path)
                    nodes.append(
                        RemoteAuthorizerNode(
                            party_id=party_id,
                            host="127.0.0.1",
                            port=port,
                            server_ca=str(ca_path),
                            client_certificate=str(coordinator_certificate),
                            client_private_key=str(coordinator_key),
                            server_certificate_sha256=certificate_sha256(certificate),
                            timeout_seconds=0.5,
                        )
                    )

                # The service files carry public topology only: neither native
                # state appears in any party's boot volume.
                for config_path in config_paths:
                    boot_text = config_path.read_text(encoding="utf-8")
                    self.assertNotIn(_base64url(state_bytes[1]), boot_text)
                    self.assertNotIn(_base64url(state_bytes[2]), boot_text)

                processes.extend(
                    _start_party_process(config_path) for config_path in config_paths
                )
                deadline = time.monotonic() + 10
                while True:
                    try:
                        package_digest = nodes[0].enroll_initial_epoch(
                            config,
                            budget=3,
                            recovery_suite_id=YI_RECOVERY_SUITE_ID,
                            parameters=parameter_bytes,
                            party_state=state_bytes[1],
                        )
                        break
                    except PartyUnavailable:
                        if time.monotonic() >= deadline:
                            self.fail("party service did not become ready")
                        time.sleep(0.05)
                self.assertEqual(len(package_digest), 64)
                self.assertEqual(
                    nodes[0].enroll_initial_epoch(
                        config,
                        budget=3,
                        recovery_suite_id=YI_RECOVERY_SUITE_ID,
                        parameters=parameter_bytes,
                        party_state=state_bytes[1],
                    ),
                    package_digest,
                )
                nodes[1].enroll_initial_epoch(
                    config,
                    budget=3,
                    recovery_suite_id=None,
                    parameters=None,
                    party_state=None,
                )

                with self.assertRaises(PartyProtocolError):
                    nodes[0]._post(  # noqa: SLF001 - exact negative wire test.
                        "/v1/enrollment/epochs",
                        {
                            "authorizer_config": config.to_dict(),
                            "budget": 3,
                            "native_party": {
                                "parameters": _base64url(parameter_bytes),
                                "state": _base64url(state_bytes[2]),
                            },
                            "profile_id": ENROLLMENT_TRANSPORT_PROFILE,
                            "recipient_party_id": 1,
                            "recovery_suite_id": YI_RECOVERY_SUITE_ID,
                        },
                    )
                reuse_key = "ef" * 32
                nodes[1].enroll_initial_epoch(
                    config,
                    budget=3,
                    recovery_suite_id=None,
                    parameters=None,
                    party_state=None,
                    idempotency_key=reuse_key,
                )
                with self.assertRaises(Conflict):
                    nodes[1].enroll_initial_epoch(
                        config,
                        budget=4,
                        recovery_suite_id=None,
                        parameters=None,
                        party_state=None,
                        idempotency_key=reuse_key,
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
                if processes:
                    time.sleep(0.2)

            first = PartyStore(database_paths[0])
            second = PartyStore(database_paths[1])
            try:
                first_record = first.runtime_epoch_package(BID, 1)
                second_record = second.runtime_epoch_package(BID, 1)
                self.assertEqual(first_record.party_state, state_bytes[1])
                self.assertIsNone(second_record.party_state)
                self.assertNotEqual(first_record.party_state, state_bytes[2])
                for store in (first, second):
                    rows = store._connection.execute(  # noqa: SLF001
                        "SELECT event_type, subject_digest FROM audit_events"
                    ).fetchall()
                    self.assertEqual(len(rows), 1)
                    self.assertEqual(rows[0]["event_type"], "EPOCH_ENROLLED")
                    self.assertEqual(rows[0]["subject_digest"], config.digest)
            finally:
                first.close()
                second.close()


if __name__ == "__main__":
    unittest.main()
