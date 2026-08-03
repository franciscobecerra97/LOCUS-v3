from __future__ import annotations

import base64
import json
import os
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

from locus import _tpass_native as native
from locus.attempt_certificates import AuthorizerConfig, AuthorizerSigner
from locus.attempt_coordinator import AttemptCoordinator, AuthorizerPeer
from locus.party_http import (
    RemoteAuthorizerNode,
    RemotePartyClient,
    certificate_sha256,
)
from locus.party_store import PartyStoreError

from tests.test_party_http import (
    BID,
    RECOVERY_ID,
    RECOVERY_INPUT,
    _attempt,
    _create_ca,
    _create_leaf,
    _free_port,
    _PartyEndpoint,
    _start_party_process,
)


def _base64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


class YiThreeOfFiveAuthenticatedTransportTests(unittest.TestCase):
    def test_three_of_five_holders_with_distinct_four_of_five_authorization(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            ca_key, ca_certificate, ca_path = _create_ca(directory)
            coordinator_certificate, coordinator_key = _create_leaf(
                directory,
                name="yi-three-of-five-coordinator",
                ca_key=ca_key,
                ca_certificate=ca_certificate,
                server=False,
            )
            signers = [AuthorizerSigner.generate(party_id) for party_id in range(1, 6)]
            parameters, states, expected_secret = native.setup(
                RECOVERY_ID, RECOVERY_INPUT, 3, 5
            )
            encoded_parameters = _base64url(bytes(parameters.to_bytes()))
            encoded_states = {
                state.party_id: _base64url(bytes(state.to_secret_bytes()))
                for state in states
            }
            endpoints: list[_PartyEndpoint] = []
            for party_id in range(1, 6):
                server_certificate, server_key = _create_leaf(
                    directory,
                    name=f"yi-three-of-five-party-{party_id}",
                    ca_key=ca_key,
                    ca_certificate=ca_certificate,
                    server=True,
                )
                peer_certificate, peer_key = _create_leaf(
                    directory,
                    name=f"yi-three-of-five-peer-{party_id}",
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
            config = AuthorizerConfig(
                bid=BID,
                epoch=1,
                backup_digest="bc" * 32,
                fault_bound=2,
                quorum=4,
                public_keys={
                    signer.party_id: signer.public_key_hex for signer in signers
                },
            )
            config_paths: list[Path] = []
            nodes: list[AuthorizerPeer] = []
            clients: dict[int, RemotePartyClient] = {}
            processes: list[subprocess.Popen[bytes]] = []
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
                    config_path = directory / f"party-{endpoint.party_id}.json"
                    config_path.write_text(
                        json.dumps(
                            {
                                "authorizer_config": config.to_dict(),
                                "budget": 2,
                                "listen_host": "127.0.0.1",
                                "listen_port": endpoint.port,
                                "native_party": {
                                    "outbound_tls": {
                                        "client_certificate": str(
                                            endpoint.peer_certificate
                                        ),
                                        "client_private_key": str(endpoint.peer_key),
                                        "server_ca": str(ca_path),
                                    },
                                    "parameters": encoded_parameters,
                                    "peers": peers,
                                    "state": encoded_states[endpoint.party_id],
                                },
                                "party_id": endpoint.party_id,
                                "signer_private_key": signer.private_key_hex,
                                "store_path": str(
                                    directory / f"party-{endpoint.party_id}.sqlite3"
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
                    server_fingerprint = certificate_sha256(endpoint.server_certificate)
                    nodes.append(
                        RemoteAuthorizerNode(
                            party_id=endpoint.party_id,
                            host="127.0.0.1",
                            port=endpoint.port,
                            server_ca=str(ca_path),
                            client_certificate=str(coordinator_certificate),
                            client_private_key=str(coordinator_key),
                            server_certificate_sha256=server_fingerprint,
                            timeout_seconds=0.5,
                        )
                    )
                    clients[endpoint.party_id] = RemotePartyClient(
                        party_id=endpoint.party_id,
                        host="127.0.0.1",
                        port=endpoint.port,
                        server_ca=str(ca_path),
                        client_certificate=str(coordinator_certificate),
                        client_private_key=str(coordinator_key),
                        server_certificate_sha256=server_fingerprint,
                        timeout_seconds=2.0,
                    )

                # Every holder process receives exactly one native state.
                for party_id, config_path in enumerate(config_paths, start=1):
                    encoded = config_path.read_text(encoding="utf-8")
                    self.assertIn(encoded_states[party_id], encoded)
                    self.assertTrue(
                        all(
                            state not in encoded
                            for other_id, state in encoded_states.items()
                            if other_id != party_id
                        )
                    )

                processes.extend(
                    _start_party_process(config_path) for config_path in config_paths
                )
                deadline = time.monotonic() + 15
                for process, node in zip(processes, nodes, strict=True):
                    while True:
                        if process.poll() is not None:
                            self.fail("Yi 3-of-5 party exited during startup")
                        try:
                            node.state_summary(BID, 1, "00" * 32)
                            break
                        except PartyStoreError:
                            if time.monotonic() >= deadline:
                                self.fail("Yi 3-of-5 party did not become ready")
                            time.sleep(0.05)

                session = native.begin_recovery(parameters, RECOVERY_ID, RECOVERY_INPUT)
                request = bytes(session.request_bytes())
                entry = _attempt(
                    config,
                    index=1,
                    previous_head="00" * 32,
                    marker="71",
                    request=request,
                    budget=2,
                )
                certificate = AttemptCoordinator(config=config, nodes=nodes).authorize(
                    entry
                )
                selected = [1, 3, 5]
                commitments = [
                    clients[party_id].prepare_commitment(
                        sid=entry.sid,
                        authorization_certificate=certificate,
                        request=request,
                        selected=selected,
                    )
                    for party_id in selected
                ]
                commitment_bytes = [item.commitment for item in commitments]
                responses = [
                    clients[party_id].respond(
                        sid=entry.sid,
                        phase_instance_id=item.phase_instance_id,
                        request=request,
                        selected=selected,
                        commitments=commitment_bytes,
                    )
                    for party_id, item in zip(selected, commitments, strict=True)
                ]
                gateway = native.aggregate_responses(
                    parameters,
                    request,
                    selected,
                    commitment_bytes,
                    responses,
                )
                self.assertEqual(
                    native.finish_recovery(parameters, session, gateway),
                    expected_secret,
                )

                # Two available holders cannot satisfy the native 3-of-5 API.
                with self.assertRaises(native.NativeTpassError):
                    native.aggregate_responses(
                        parameters,
                        request,
                        selected[:2],
                        commitment_bytes[:2],
                        responses[:2],
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
