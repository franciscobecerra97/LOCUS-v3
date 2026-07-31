from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

from locus import _tpass_native as native
from locus.attempt_certificates import AttemptEntry, AuthorizerConfig, AuthorizerSigner
from locus.attempt_coordinator import AttemptCoordinator, CoordinatorError
from locus.crypto import hash_bytes
from locus.epoch_lifecycle import EpochActivationCertificate, EpochTransition
from locus.party_http import (
    PartyProtocolError,
    RemoteAuthorizerNode,
    RemotePartyClient,
    certificate_sha256,
)
from locus.party_store import GENESIS_HEAD, Conflict, PartyStoreError

from tests.test_party_http import (
    _base64url,
    _create_ca,
    _create_leaf,
    _free_port,
    _PartyEndpoint,
    _start_party_process,
)

BID = "c1" * 16
OLD_BACKUP_DIGEST = "d1" * 32
NEW_BACKUP_DIGEST = "d2" * 32
OLD_RECOVERY_ID = b"lifecycle-old-native-recovery"
NEW_RECOVERY_ID = b"lifecycle-new-native-recovery"
OLD_RECOVERY_INPUT = b"old-three-canonical-cue-pairs"
NEW_RECOVERY_INPUT = b"new-three-canonical-cue-pairs"


def _entry(
    config: AuthorizerConfig,
    status: dict[str, int | str],
    request: bytes,
    *,
    marker: str,
) -> AttemptEntry:
    sid = marker * 32
    return AttemptEntry(
        bid=config.bid,
        epoch=config.epoch,
        config_digest=config.digest,
        log_index=int(status["installed_index"]) + 1,
        previous_head=str(status["installed_head"]),
        sid=sid,
        request_digest=hash_bytes(
            "LOCUS/lifecycle-http-request/v1", bytes.fromhex(sid), request
        ).hex(),
        tpass_request_hash=hash_bytes("LOCUS/tpass-request-bytes/v1", request).hex(),
        resulting_consumed=int(status["consumed"]) + 1,
        effective_budget=int(status["budget"]),
    )


class EpochLifecycleHttpTests(unittest.TestCase):
    def test_five_process_native_successor_survives_restart_and_retires_old(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            ca_key, ca_certificate, ca_path = _create_ca(directory)
            coordinator_certificate, coordinator_key = _create_leaf(
                directory,
                name="lifecycle-coordinator",
                ca_key=ca_key,
                ca_certificate=ca_certificate,
                server=False,
            )
            signers = [AuthorizerSigner.generate(party_id) for party_id in range(1, 6)]
            public_keys = {signer.party_id: signer.public_key_hex for signer in signers}
            old_config = AuthorizerConfig(
                bid=BID,
                epoch=1,
                backup_digest=OLD_BACKUP_DIGEST,
                fault_bound=2,
                quorum=4,
                public_keys=public_keys,
            )
            new_config = AuthorizerConfig(
                bid=BID,
                epoch=2,
                backup_digest=NEW_BACKUP_DIGEST,
                fault_bound=2,
                quorum=4,
                public_keys=public_keys,
            )
            old_parameters, old_states, _ = native.setup(
                OLD_RECOVERY_ID, OLD_RECOVERY_INPUT, 2, 3
            )
            new_parameters, new_states, expected_new_secret = native.setup(
                NEW_RECOVERY_ID, NEW_RECOVERY_INPUT, 2, 3
            )
            old_parameters_bytes = bytes(old_parameters.to_bytes())
            new_parameters_bytes = bytes(new_parameters.to_bytes())
            old_state_bytes = {
                state.party_id: bytes(state.to_secret_bytes()) for state in old_states
            }
            new_state_bytes = {
                state.party_id: bytes(state.to_secret_bytes()) for state in new_states
            }

            endpoints: list[_PartyEndpoint] = []
            for party_id in range(1, 6):
                server_certificate, server_key = _create_leaf(
                    directory,
                    name=f"lifecycle-party-{party_id}",
                    ca_key=ca_key,
                    ca_certificate=ca_certificate,
                    server=True,
                )
                peer_certificate, peer_key = _create_leaf(
                    directory,
                    name=f"lifecycle-peer-{party_id}",
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
            config_paths: list[Path] = []
            processes: list[subprocess.Popen[bytes]] = []
            clients: list[RemotePartyClient] = []

            def start(index: int) -> subprocess.Popen[bytes]:
                return _start_party_process(config_paths[index])

            def wait_ready(index: int, epoch: int) -> None:
                deadline = time.monotonic() + 10
                while True:
                    process = processes[index]
                    if process.poll() is not None:
                        stderr = (
                            process.stderr.read().decode("utf-8", errors="replace")
                            if process.stderr is not None
                            else ""
                        )
                        self.fail(f"party service exited during startup: {stderr}")
                    try:
                        clients[index].state_summary(BID, epoch, "00" * 32)
                        return
                    except PartyStoreError:
                        if time.monotonic() >= deadline:
                            self.fail("party service did not become ready")
                        time.sleep(0.05)

            def restart(index: int, epoch: int) -> None:
                process = processes[index]
                process.terminate()
                process.wait(timeout=5)
                if process.stderr is not None:
                    process.stderr.close()
                processes[index] = start(index)
                wait_ready(index, epoch)

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
                            "timeout_seconds": 2.0,
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
                            "parameters": _base64url(old_parameters_bytes),
                            "peers": peers,
                            "state": _base64url(old_state_bytes[endpoint.party_id]),
                        }
                        if endpoint.party_id <= 3
                        else None
                    )
                    config_path = directory / f"party-{endpoint.party_id}.json"
                    config_path.write_text(
                        json.dumps(
                            {
                                "authorizer_config": old_config.to_dict(),
                                "budget": 4,
                                "listen_host": "127.0.0.1",
                                "listen_port": endpoint.port,
                                "native_party": native_config,
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
                    clients.append(
                        RemotePartyClient(
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
                    )
                processes.extend(start(index) for index in range(5))
                for index in range(5):
                    wait_ready(index, 1)

                old_session = native.begin_recovery(
                    old_parameters, OLD_RECOVERY_ID, OLD_RECOVERY_INPUT
                )
                old_request = bytes(old_session.request_bytes())
                old_coordinator = AttemptCoordinator(
                    config=old_config,
                    nodes=list(clients),
                    operation_timeout_seconds=8,
                    phase_timeout_seconds=3,
                )
                old_authorization = old_coordinator.authorize(
                    _entry(
                        old_config,
                        clients[0].state_summary(BID, 1, "01" * 32).status,
                        old_request,
                        marker="31",
                    )
                )
                old_status = clients[0].state_summary(BID, 1, "02" * 32).status
                transition = EpochTransition(
                    bid=BID,
                    predecessor_epoch=1,
                    predecessor_config_digest=old_config.digest,
                    predecessor_backup_digest=old_config.backup_digest,
                    predecessor_head=str(old_status["installed_head"]),
                    predecessor_consumed=int(old_status["consumed"]),
                    predecessor_budget=int(old_status["budget"]),
                    successor_epoch=2,
                    successor_config_digest=new_config.digest,
                    successor_backup_digest=new_config.backup_digest,
                    successor_budget=3,
                    policy_version="LOCUS-epoch-lifecycle-policy-v1",
                    transition_nonce="41" * 32,
                )

                approvals = [
                    client.create_epoch_approval(transition, old_config, new_config)
                    for client in clients
                ]
                self.assertEqual(
                    clients[0].create_epoch_approval(
                        transition, old_config, new_config
                    ),
                    approvals[0],
                )
                peer_caller = RemoteAuthorizerNode(
                    party_id=1,
                    host="127.0.0.1",
                    port=endpoints[0].port,
                    server_ca=str(ca_path),
                    client_certificate=str(endpoints[0].peer_certificate),
                    client_private_key=str(endpoints[0].peer_key),
                    server_certificate_sha256=certificate_sha256(
                        endpoints[0].server_certificate
                    ),
                    timeout_seconds=2.0,
                )
                with self.assertRaises(PartyProtocolError):
                    peer_caller.create_epoch_approval(
                        transition, old_config, new_config
                    )

                readiness = []
                for client in clients:
                    native_party = client.party_id <= 3
                    readiness.append(
                        client.prepare_successor_epoch(
                            transition,
                            old_config,
                            new_config,
                            parameters=(new_parameters_bytes if native_party else None),
                            party_state=(
                                new_state_bytes[client.party_id]
                                if native_party
                                else None
                            ),
                        )
                    )
                self.assertEqual(
                    clients[0].prepare_successor_epoch(
                        transition,
                        old_config,
                        new_config,
                        parameters=new_parameters_bytes,
                        party_state=new_state_bytes[1],
                    ),
                    readiness[0],
                )
                with self.assertRaises(Conflict):
                    clients[0].prepare_successor_epoch(
                        transition,
                        old_config,
                        new_config,
                        parameters=new_parameters_bytes,
                        party_state=old_state_bytes[1],
                        idempotency_key="51" * 32,
                    )

                restart(0, 1)
                self.assertEqual(
                    clients[0].prepare_successor_epoch(
                        transition,
                        old_config,
                        new_config,
                        parameters=new_parameters_bytes,
                        party_state=new_state_bytes[1],
                    ),
                    readiness[0],
                )
                activation = EpochActivationCertificate.create(
                    transition,
                    approvals[: old_config.quorum],
                    readiness[: new_config.quorum],
                    old_config,
                    new_config,
                )

                for client in clients[:3]:
                    client.activate_successor_epoch(activation, old_config, new_config)
                with self.assertRaises(PartyProtocolError):
                    clients[0].prepare_commitment(
                        sid=old_authorization.prepare.entry.sid,
                        authorization_certificate=old_authorization,
                        request=old_request,
                        selected=[1, 2],
                    )

                old_next = _entry(
                    old_config,
                    clients[3].state_summary(BID, 1, "03" * 32).status,
                    old_request,
                    marker="32",
                )
                with self.assertRaises(CoordinatorError):
                    old_coordinator.authorize(old_next)
                new_coordinator = AttemptCoordinator(
                    config=new_config,
                    nodes=list(clients),
                    operation_timeout_seconds=8,
                    phase_timeout_seconds=3,
                )
                new_session = native.begin_recovery(
                    new_parameters, NEW_RECOVERY_ID, NEW_RECOVERY_INPUT
                )
                new_request = bytes(new_session.request_bytes())
                new_first = _entry(
                    new_config,
                    {
                        "budget": 3,
                        "consumed": 0,
                        "installed_head": GENESIS_HEAD,
                        "installed_index": 0,
                    },
                    new_request,
                    marker="33",
                )
                with self.assertRaises(CoordinatorError):
                    new_coordinator.authorize(new_first)

                clients[3].activate_successor_epoch(activation, old_config, new_config)
                new_authorization = new_coordinator.authorize(new_first)
                clients[4].activate_successor_epoch(activation, old_config, new_config)
                self.assertEqual(
                    clients[4].activate_successor_epoch(
                        activation, old_config, new_config
                    ),
                    activation.certificate_hash,
                )

                restart(0, 2)
                self.assertEqual(
                    clients[0].activate_successor_epoch(
                        activation, old_config, new_config
                    ),
                    activation.certificate_hash,
                )
                selected = [1, 2]
                commitments = [
                    clients[party_id - 1].prepare_commitment(
                        sid=new_first.sid,
                        authorization_certificate=new_authorization,
                        request=new_request,
                        selected=selected,
                    )
                    for party_id in selected
                ]
                commitment_bytes = [item.commitment for item in commitments]
                responses = [
                    clients[party_id - 1].respond(
                        sid=new_first.sid,
                        phase_instance_id=commitments[index].phase_instance_id,
                        request=new_request,
                        selected=selected,
                        commitments=commitment_bytes,
                    )
                    for index, party_id in enumerate(selected)
                ]
                gateway = native.aggregate_responses(
                    new_parameters,
                    new_request,
                    selected,
                    commitment_bytes,
                    responses,
                )
                self.assertEqual(
                    bytes(
                        native.finish_recovery(
                            new_parameters, new_session, bytes(gateway)
                        )
                    ),
                    bytes(expected_new_secret),
                )
                self.assertTrue(
                    all(
                        client.state_summary(BID, 1, "04" * 32).status["status"]
                        == "RETIRED"
                        for client in clients
                    )
                )
                self.assertTrue(
                    all(
                        client.state_summary(BID, 2, "05" * 32).status["status"]
                        == "ACTIVE"
                        for client in clients
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
