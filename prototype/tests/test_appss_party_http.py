from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

from locus import _tpass_native as native
from locus.appss_client import AppssClientError, recover_with_parties
from locus.appss_formats import (
    APPSS_INSTALL_FORMAT,
    APPSS_PROFILE_2_OF_3,
    APPSS_PUBLIC_STATE_FORMAT,
    APPSS_REQUEST_FORMAT,
    APPSS_SUITE_ID,
    MAX_INSTALL_BYTES,
    MAX_REQUEST_BYTES,
    AppssHolderBinding,
    canonical_decode,
    context_digest,
    encode_checked,
    instance_id,
    oprf_input,
    validate_install,
    validate_request,
    validate_response,
)
from locus.appss_party import AppssPartyBinding, AppssPartyService, AppssPartyStore
from locus.appss_party_http import AppssRemoteParty
from locus.contracts import PublicRecoveryState, RecoveryContext
from locus.party_http import certificate_sha256

from tests.test_party_http import _create_ca, _create_leaf, _free_port

ADMISSION = "32" * 32
PROOF_KEY = "33" * 32


def _request(
    *,
    context: bytes,
    holder_id: int,
    blinded: bytes,
    operation_id: str,
) -> bytes:
    return encode_checked(
        {
            "admission_grant_digest": ADMISSION,
            "blinded_element": blinded.hex(),
            "client_proof_key_digest": PROOF_KEY,
            "context_digest": context.hex(),
            "holder_id": holder_id,
            "nonce": bytes([0x40 + holder_id] * 32).hex(),
            "omega_digest": None,
            "operation": "initialize",
            "operation_id": operation_id,
            "profile_id": APPSS_PROFILE_2_OF_3,
            "session_id": bytes([0x50 + holder_id] * 32).hex(),
            "suite_id": APPSS_SUITE_ID,
            "version": APPSS_REQUEST_FORMAT,
        },
        maximum=MAX_REQUEST_BYTES,
        validator=validate_request,
        label="aPPSS request",
    )


def _public_mapping(state: native.AppssPublicState) -> dict[str, object]:
    return {
        "commitment": state.commitment.hex(),
        "context_digest": state.context_digest.hex(),
        "k": state.threshold,
        "masked_shares": [
            {"index": index, "value": value.hex()}
            for index, value in state.masked_shares
        ],
        "n": state.parties,
        "omega_digest": state.omega_digest.hex(),
        "oprf_profile": "LOCUS-APPSS-OPRF-RISTRETTO255-SHA512-v1",
        "profile_id": APPSS_PROFILE_2_OF_3,
        "suite_id": APPSS_SUITE_ID,
        "version": APPSS_PUBLIC_STATE_FORMAT,
    }


def _initialize_parties(
    services: list[AppssPartyService],
    holders: tuple[AppssHolderBinding, ...],
    context: bytes,
    password: bytes,
) -> tuple[PublicRecoveryState, bytes]:
    operation_id = "61" * 32
    masks: list[tuple[int, bytes]] = []
    responses: list[bytes] = []
    for holder, service in zip(holders, services, strict=True):
        instance = instance_id(context, holder)
        session, blinded = native.appss_blind(oprf_input(instance, password))
        response_bytes = service.evaluate(
            _request(
                context=context,
                holder_id=holder.index,
                blinded=blinded,
                operation_id=operation_id,
            )
        )
        response = canonical_decode(
            response_bytes,
            maximum=4096,
            validator=validate_response,
            label="aPPSS response",
        )
        output = native.appss_finalize(
            session, bytes.fromhex(response["evaluated_element"])
        )
        masks.append((holder.index, native.appss_derive_mask(instance, output)))
        responses.append(response_bytes)
    public, secret = native.appss_initialize_fixture(context, password, 2, 3, masks)
    mapping = _public_mapping(public)
    public_bytes = json.dumps(mapping, sort_keys=True, separators=(",", ":")).encode()
    transcript = hashlib.sha256(b"".join(responses)).hexdigest()
    for holder, service in zip(holders, services, strict=True):
        install = encode_checked(
            {
                "context_digest": context.hex(),
                "holder_id": holder.index,
                "initialization_transcript_digest": transcript,
                "operation_id": operation_id,
                "profile_id": APPSS_PROFILE_2_OF_3,
                "public_state": mapping,
                "suite_id": APPSS_SUITE_ID,
                "version": APPSS_INSTALL_FORMAT,
            },
            maximum=MAX_INSTALL_BYTES,
            validator=validate_install,
            label="aPPSS state install",
        )
        service.install(install)
    return (
        PublicRecoveryState(
            suite_id=APPSS_SUITE_ID,
            format_id=APPSS_PUBLIC_STATE_FORMAT,
            payload=public_bytes,
        ),
        secret,
    )


class AppssPartyHttpTests(unittest.TestCase):
    def test_recovery_across_distinct_mutually_authenticated_processes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            ca_key, ca_certificate, ca_path = _create_ca(root)
            client_certificate, client_key = _create_leaf(
                root,
                name="appss-client",
                ca_key=ca_key,
                ca_certificate=ca_certificate,
                server=False,
            )
            bad_certificate, bad_key = _create_leaf(
                root,
                name="untrusted-appss-client",
                ca_key=ca_key,
                ca_certificate=ca_certificate,
                server=False,
            )
            server_material: list[tuple[Path, Path, int]] = []
            holders: list[AppssHolderBinding] = []
            for holder_id in range(1, 4):
                certificate, key = _create_leaf(
                    root,
                    name=f"appss-party-{holder_id}",
                    ca_key=ca_key,
                    ca_certificate=ca_certificate,
                    server=True,
                )
                server_material.append((certificate, key, _free_port()))
                holders.append(
                    AppssHolderBinding(
                        index=holder_id,
                        party_id=f"party-{holder_id}",
                        service_identity=(
                            "certificate-sha256:" + certificate_sha256(certificate)
                        ),
                    )
                )

            backup_id = bytes.fromhex("71" * 16)
            configuration_digest = bytes.fromhex("72" * 32)
            holder_tuple = tuple(holders)
            appss_context = context_digest(
                backup_id=backup_id,
                epoch=1,
                policy_id="LOCUS-canonical-email-set-v1",
                holders=holder_tuple,
                k=2,
                n=3,
                configuration_digest=configuration_digest,
            )
            stores = [
                AppssPartyStore(
                    root / f"party-{holder_id}.sqlite3",
                    AppssPartyBinding(holder_id, appss_context),
                )
                for holder_id in range(1, 4)
            ]
            services = [AppssPartyService(store) for store in stores]

            password = b"network-correct".ljust(32, b"\x00")
            public, expected = _initialize_parties(
                services, holder_tuple, appss_context, password
            )
            config_paths: list[Path] = []
            remotes: dict[int, AppssRemoteParty] = {}
            processes: list[subprocess.Popen[bytes]] = []
            try:
                for holder_id, (certificate, key, port) in enumerate(
                    server_material, start=1
                ):
                    config = {
                        "context_digest": appss_context.hex(),
                        "epoch_context": {
                            "backup_id": backup_id.hex(),
                            "configuration_digest": configuration_digest.hex(),
                            "epoch": 1,
                            "holders": [
                                {
                                    "index": holder.index,
                                    "party_id": holder.party_id,
                                    "service_identity": holder.service_identity,
                                }
                                for holder in holder_tuple
                            ],
                            "k": 2,
                            "n": 3,
                            "policy_id": "LOCUS-canonical-email-set-v1",
                            "profile_id": APPSS_PROFILE_2_OF_3,
                            "suite_id": APPSS_SUITE_ID,
                        },
                        "holder_id": holder_id,
                        "listen_host": "127.0.0.1",
                        "listen_port": port,
                        "store_path": str(stores[holder_id - 1].path),
                        "tls": {
                            "certificate": str(certificate),
                            "client_ca": str(ca_path),
                            "client_certificate_sha256": [
                                certificate_sha256(client_certificate)
                            ],
                            "private_key": str(key),
                        },
                    }
                    config_path = root / f"party-{holder_id}.json"
                    config_path.write_text(
                        json.dumps(config, sort_keys=True), encoding="utf-8"
                    )
                    config_paths.append(config_path)
                    config_text = config_path.read_text(encoding="utf-8")
                    self.assertNotIn("oprf_key", config_text)
                    remotes[holder_id] = AppssRemoteParty(
                        holder_id=holder_id,
                        host="127.0.0.1",
                        port=port,
                        server_ca=str(ca_path),
                        client_certificate=str(client_certificate),
                        client_private_key=str(client_key),
                        server_certificate_sha256=certificate_sha256(certificate),
                    )
                    processes.append(
                        subprocess.Popen(
                            [
                                sys.executable,
                                "-m",
                                "locus.appss_party_http",
                                "--config",
                                str(config_path),
                            ],
                            stdin=subprocess.DEVNULL,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                        )
                    )

                context = RecoveryContext(
                    recovery_id="appss-network-recovery",
                    backup_id=backup_id.hex(),
                    epoch=1,
                    suite_id=APPSS_SUITE_ID,
                    policy_id="LOCUS-canonical-email-set-v1",
                    configuration_digest=configuration_digest.hex(),
                    digest_context="73" * 32,
                    suite_context_digest=appss_context.hex(),
                )
                deadline = time.monotonic() + 10
                while True:
                    try:
                        recovered = recover_with_parties(
                            context=context,
                            password_input=password,
                            public_state=public,
                            holders=(holders[0], holders[2]),
                            endpoints=remotes,
                            admission_grant_digest=ADMISSION,
                            client_proof_key_digest=PROOF_KEY,
                        )
                        break
                    except AppssClientError:
                        if time.monotonic() >= deadline:
                            self.fail("aPPSS party processes did not become ready")
                        time.sleep(0.05)
                self.assertEqual(recovered, expected)
                with self.assertRaisesRegex(AppssClientError, "recovery rejected"):
                    recover_with_parties(
                        context=context,
                        password_input=b"wrong".ljust(32, b"\x00"),
                        public_state=public,
                        holders=(holders[0], holders[1]),
                        endpoints=remotes,
                        admission_grant_digest=ADMISSION,
                        client_proof_key_digest=PROOF_KEY,
                    )

                certificate, _, port = server_material[0]
                unauthorized = AppssRemoteParty(
                    holder_id=1,
                    host="127.0.0.1",
                    port=port,
                    server_ca=str(ca_path),
                    client_certificate=str(bad_certificate),
                    client_private_key=str(bad_key),
                    server_certificate_sha256=certificate_sha256(certificate),
                )
                with self.assertRaises(AppssClientError):
                    recover_with_parties(
                        context=context,
                        password_input=password,
                        public_state=public,
                        holders=(holders[0], holders[1]),
                        endpoints={1: unauthorized, 2: remotes[2]},
                        admission_grant_digest=ADMISSION,
                        client_proof_key_digest=PROOF_KEY,
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


if __name__ == "__main__":
    unittest.main()
