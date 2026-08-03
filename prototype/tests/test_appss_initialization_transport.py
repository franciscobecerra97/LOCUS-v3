from __future__ import annotations

import json
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

from locus import _tpass_native as native
from locus.appss_client import (
    AppssClientError,
    AppssInitializationResult,
    AppssPartyEndpoint,
    initialize_with_parties,
    recover_with_parties,
)
from locus.appss_formats import (
    APPSS_PROFILE_2_OF_3,
    APPSS_REQUEST_FORMAT,
    APPSS_SUITE_ID,
    MAX_PUBLIC_STATE_BYTES,
    MAX_REQUEST_BYTES,
    AppssHolderBinding,
    canonical_decode,
    context_digest,
    derive_password_input,
    encode_checked,
    instance_id,
    oprf_input,
    validate_public_state,
    validate_request,
)
from locus.appss_party import AppssPartyBinding, AppssPartyStore
from locus.appss_party_http import AppssPartyTransportError, AppssRemoteParty
from locus.contracts import RecoveryContext
from locus.party_http import certificate_sha256

from tests.test_party_http import _create_ca, _create_leaf, _free_port

ADMISSION = "81" * 32
PROOF_KEY = "82" * 32


class _FailInstall:
    def __init__(self, inner: AppssRemoteParty) -> None:
        self.inner = inner

    @property
    def holder_id(self) -> int:
        return self.inner.holder_id

    @property
    def service_identity(self) -> str:
        return self.inner.service_identity

    def evaluate(self, request_bytes: bytes, *, idempotency_key: str) -> bytes:
        return self.inner.evaluate(request_bytes, idempotency_key=idempotency_key)

    def initialize(self, request_bytes: bytes, *, idempotency_key: str) -> bytes:
        return self.inner.initialize(request_bytes, idempotency_key=idempotency_key)

    def install(self, install_bytes: bytes, *, idempotency_key: str) -> bytes:
        raise AppssPartyTransportError("synthetic install interruption")


class AuthenticatedAppssInitializationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        ca_key, ca_certificate, self.ca_path = _create_ca(self.root)
        self.client_certificate, self.client_key = _create_leaf(
            self.root,
            name="appss-initialization-client",
            ca_key=ca_key,
            ca_certificate=ca_certificate,
            server=False,
        )
        self.alternate_certificate, self.alternate_key = _create_leaf(
            self.root,
            name="appss-initialization-client-alternate",
            ca_key=ca_key,
            ca_certificate=ca_certificate,
            server=False,
        )
        server_material: list[tuple[Path, Path, int]] = []
        holders: list[AppssHolderBinding] = []
        for holder_id in range(1, 4):
            certificate, key = _create_leaf(
                self.root,
                name=f"appss-initialization-party-{holder_id}",
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
        self.holders = tuple(holders)
        self.backup_id = bytes.fromhex("83" * 16)
        self.configuration_digest = bytes.fromhex("84" * 32)
        self.context_digest = context_digest(
            backup_id=self.backup_id,
            epoch=1,
            policy_id="LOCUS-canonical-email-set-v1",
            holders=self.holders,
            k=2,
            n=3,
            configuration_digest=self.configuration_digest,
        )
        self.context = RecoveryContext(
            suite_id=APPSS_SUITE_ID,
            recovery_id="appss-authenticated-initialization",
            backup_id=self.backup_id.hex(),
            epoch=1,
            policy_id="LOCUS-canonical-email-set-v1",
            configuration_digest=self.configuration_digest.hex(),
            digest_context="85" * 32,
            suite_context_digest=self.context_digest.hex(),
        )
        self.password = derive_password_input(
            self.context_digest, b"synthetic canonical recovery input"
        )
        self.database_paths: list[Path] = []
        self.remotes: dict[int, AppssRemoteParty] = {}
        self.processes: list[subprocess.Popen[bytes]] = []
        client_fingerprints = sorted(
            [
                certificate_sha256(self.client_certificate),
                certificate_sha256(self.alternate_certificate),
            ]
        )
        for holder_id, (certificate, key, port) in enumerate(server_material, start=1):
            database_path = self.root / f"party-{holder_id}.sqlite3"
            self.database_paths.append(database_path)
            config = {
                "context_digest": self.context_digest.hex(),
                "epoch_context": {
                    "backup_id": self.backup_id.hex(),
                    "configuration_digest": self.configuration_digest.hex(),
                    "epoch": 1,
                    "holders": [
                        {
                            "index": holder.index,
                            "party_id": holder.party_id,
                            "service_identity": holder.service_identity,
                        }
                        for holder in self.holders
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
                "store_path": str(database_path),
                "tls": {
                    "certificate": str(certificate),
                    "client_ca": str(self.ca_path),
                    "client_certificate_sha256": client_fingerprints,
                    "private_key": str(key),
                },
            }
            config_path = self.root / f"party-{holder_id}.json"
            config_path.write_text(json.dumps(config, sort_keys=True), encoding="utf-8")
            self.assertNotIn("oprf_key", config_path.read_text(encoding="utf-8"))
            self.remotes[holder_id] = AppssRemoteParty(
                holder_id=holder_id,
                host="127.0.0.1",
                port=port,
                server_ca=str(self.ca_path),
                client_certificate=str(self.client_certificate),
                client_private_key=str(self.client_key),
                server_certificate_sha256=certificate_sha256(certificate),
            )
            self.processes.append(
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
            self._wait_for_port(port, self.processes[-1])

    def tearDown(self) -> None:
        self._stop_processes()
        self.temporary.cleanup()

    @staticmethod
    def _wait_for_port(port: int, process: subprocess.Popen[bytes]) -> None:
        deadline = time.monotonic() + 10
        while True:
            if process.poll() is not None:
                raise AssertionError("aPPSS initialization service exited")
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=0.1):
                    return
            except OSError as exc:
                if time.monotonic() >= deadline:
                    raise AssertionError(
                        "aPPSS initialization service did not listen"
                    ) from exc
                time.sleep(0.05)

    def _stop_processes(self) -> None:
        for process in self.processes:
            if process.poll() is None:
                process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        self.processes.clear()

    def _initialize(self) -> AppssInitializationResult:
        return initialize_with_parties(
            context=self.context,
            password_input=self.password,
            holders=self.holders,
            endpoints=self.remotes,
            admission_grant_digest=ADMISSION,
            client_proof_key_digest=PROOF_KEY,
            operation_id="86" * 32,
        )

    def test_each_server_creates_own_key_and_all_ready_before_result(self) -> None:
        initialized = self._initialize()
        self.assertEqual(len(initialized.ready_digests), 3)
        recovered = recover_with_parties(
            context=self.context,
            password_input=self.password,
            public_state=initialized.public_state,
            holders=(self.holders[0], self.holders[2]),
            endpoints=self.remotes,
            admission_grant_digest=ADMISSION,
            client_proof_key_digest=PROOF_KEY,
        )
        self.assertEqual(recovered, initialized.recovery_secret)

        self._stop_processes()
        states: list[bytes] = []
        for holder_id, path in enumerate(self.database_paths, start=1):
            store = AppssPartyStore(
                path, AppssPartyBinding(holder_id, self.context_digest)
            )
            state = store.load_state()
            self.assertIsNotNone(state)
            self.assertEqual(state[0], "installed")  # type: ignore[index]
            states.append(state[1])  # type: ignore[index]
        self.assertEqual(len(set(states)), 3)

    def test_route_body_recipient_epoch_caller_and_idempotency_bindings(self) -> None:
        initialized = self._initialize()
        public = canonical_decode(
            initialized.public_state.payload,
            maximum=MAX_PUBLIC_STATE_BYTES,
            validator=validate_public_state,
            label="aPPSS public state",
        )
        holder = self.holders[0]
        instance = instance_id(self.context_digest, holder)
        _, blinded = native.appss_blind(oprf_input(instance, self.password))
        request = {
            "admission_grant_digest": ADMISSION,
            "blinded_element": blinded.hex(),
            "client_proof_key_digest": PROOF_KEY,
            "context_digest": self.context_digest.hex(),
            "holder_id": 1,
            "nonce": "87" * 32,
            "omega_digest": public["omega_digest"],
            "operation": "recover",
            "operation_id": "88" * 32,
            "profile_id": APPSS_PROFILE_2_OF_3,
            "session_id": "89" * 32,
            "suite_id": APPSS_SUITE_ID,
            "version": APPSS_REQUEST_FORMAT,
        }
        request_bytes = encode_checked(
            request,
            maximum=MAX_REQUEST_BYTES,
            validator=validate_request,
            label="aPPSS request",
        )
        key = "8a" * 32
        response = self.remotes[1].evaluate(request_bytes, idempotency_key=key)
        self.assertEqual(
            self.remotes[1].evaluate(request_bytes, idempotency_key=key), response
        )

        changed = dict(request)
        changed["nonce"] = "8b" * 32
        changed_bytes = encode_checked(
            changed,
            maximum=MAX_REQUEST_BYTES,
            validator=validate_request,
            label="aPPSS request",
        )
        with self.assertRaises(AppssPartyTransportError):
            self.remotes[1].evaluate(changed_bytes, idempotency_key=key)
        with self.assertRaises(AppssPartyTransportError):
            self.remotes[1].initialize(request_bytes, idempotency_key=key)
        with self.assertRaises(AppssPartyTransportError):
            self.remotes[2].evaluate(request_bytes, idempotency_key="8c" * 32)

        wrong_context = dict(request)
        wrong_context["context_digest"] = "8d" * 32
        with self.assertRaises(AppssPartyTransportError):
            self.remotes[1].evaluate(
                encode_checked(
                    wrong_context,
                    maximum=MAX_REQUEST_BYTES,
                    validator=validate_request,
                    label="aPPSS request",
                ),
                idempotency_key="8e" * 32,
            )
        wrong_suite = dict(request)
        wrong_suite["suite_id"] = "LOCUS-TPASS-YI-ZK-RISTRETTO255-v1"
        with self.assertRaises(AppssPartyTransportError):
            self.remotes[1].evaluate(
                json.dumps(wrong_suite, sort_keys=True, separators=(",", ":")).encode(),
                idempotency_key="8f" * 32,
            )
        with self.assertRaises(AppssPartyTransportError):
            self.remotes[1].evaluate(b"{}", idempotency_key="90" * 32)

        alternate = AppssRemoteParty(
            holder_id=1,
            host=self.remotes[1].host,
            port=self.remotes[1].port,
            server_ca=str(self.ca_path),
            client_certificate=str(self.alternate_certificate),
            client_private_key=str(self.alternate_key),
            server_certificate_sha256=self.remotes[1].server_certificate_sha256,
        )
        with self.assertRaises(AppssPartyTransportError):
            alternate.evaluate(request_bytes, idempotency_key=key)

    def test_interrupted_install_returns_no_active_initialization(self) -> None:
        interrupted: dict[int, AppssPartyEndpoint] = dict(self.remotes)
        interrupted[3] = _FailInstall(self.remotes[3])
        with self.assertRaisesRegex(AppssClientError, "initialization rejected"):
            initialize_with_parties(
                context=self.context,
                password_input=self.password,
                holders=self.holders,
                endpoints=interrupted,
                admission_grant_digest=ADMISSION,
                client_proof_key_digest=PROOF_KEY,
                operation_id="91" * 32,
            )
        self._stop_processes()
        phases: list[str] = []
        for holder_id, path in enumerate(self.database_paths, start=1):
            store = AppssPartyStore(
                path, AppssPartyBinding(holder_id, self.context_digest)
            )
            state = store.load_state()
            self.assertIsNotNone(state)
            phases.append(state[0])  # type: ignore[index]
        self.assertEqual(phases, ["installed", "installed", "pending"])


if __name__ == "__main__":
    unittest.main()
