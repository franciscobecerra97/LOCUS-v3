from __future__ import annotations

import base64
import hashlib
import json
import shutil
import socket
import sqlite3
import tempfile
import unittest
from collections.abc import Mapping
from pathlib import Path
from typing import Any, ClassVar

from locus.attack_runner import build_attack_report
from locus.attempt_certificates import AuthorizerConfig
from locus.codec import encode
from locus.deployment import ATTEMPT_BUDGET, provision
from locus.party_snapshot import (
    PARTY_SNAPSHOT_INPUT_VERSION,
    PARTY_SNAPSHOT_SCENARIO,
    PartySnapshotError,
    audit_party_snapshot,
    capture_party_snapshot,
    validate_party_snapshot,
)
from locus.party_store import (
    GENESIS_HEAD,
    AttemptAuthorization,
    EpochConfig,
    PartyStore,
)

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "deploy" / "fixtures" / "cues.json"


def _decode_base64url(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * ((4 - len(value) % 4) % 4))


class PartySnapshotAttackTests(unittest.TestCase):
    _provisioned: ClassVar[tempfile.TemporaryDirectory[str]]
    party_source: ClassVar[Path]

    @classmethod
    def setUpClass(cls) -> None:
        cls._provisioned = tempfile.TemporaryDirectory()
        root = Path(cls._provisioned.name)
        party_roots = [root / f"party{party_id}" for party_id in range(1, 6)]
        provision(
            party_roots=party_roots,
            client_root=root / "client",
            fixture_path=FIXTURE,
        )
        cls.party_source = party_roots[0]

    @classmethod
    def tearDownClass(cls) -> None:
        cls._provisioned.cleanup()

    def _party_checkpoint(self, root: Path) -> tuple[Path, dict[str, Any]]:
        party_root = root / "party-source"
        shutil.copytree(self.party_source, party_root)
        service = json.loads((party_root / "service.json").read_text(encoding="ascii"))
        config = AuthorizerConfig.from_dict(service["authorizer_config"])
        native_party = service["native_party"]
        parameters = _decode_base64url(native_party["parameters"])
        state = _decode_base64url(native_party["state"])
        epoch = EpochConfig(
            bid=config.bid,
            epoch=config.epoch,
            party_id=1,
            config_digest=config.digest,
            backup_digest=config.backup_digest,
            budget=ATTEMPT_BUDGET,
        )
        store = PartyStore(party_root / "party.sqlite3")
        store.enroll_epoch(epoch)
        store.register_initial_runtime_package(
            epoch,
            config,
            parameters=parameters,
            party_state=state,
        )
        store.install_authorization(
            AttemptAuthorization(
                bid=config.bid,
                epoch=config.epoch,
                config_digest=config.digest,
                log_index=1,
                previous_head=GENESIS_HEAD,
                sid="11" * 32,
                request_digest="22" * 32,
                tpass_request_hash="33" * 32,
                resulting_consumed=1,
                effective_budget=ATTEMPT_BUDGET,
                certificate_hash="44" * 32,
            )
        )
        store.close()
        return party_root, service

    def _snapshot(self, root: Path) -> tuple[Path, dict[str, Any]]:
        party_root, service = self._party_checkpoint(root)
        snapshot_root = root / "snapshot"
        result = capture_party_snapshot(
            party_root=party_root, snapshot_root=snapshot_root
        )
        self.assertEqual(
            result,
            {"artifact": PARTY_SNAPSHOT_INPUT_VERSION, "status": "captured"},
        )
        return snapshot_root, service

    def _rebind_manifest_file(self, snapshot_root: Path, name: str) -> None:
        manifest_path = snapshot_root / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="ascii"))
        value = (snapshot_root / "party" / name).read_bytes()
        matches = [entry for entry in manifest["files"] if entry["path"] == name]
        self.assertEqual(len(matches), 1)
        matches[0]["bytes"] = len(value)
        matches[0]["sha256"] = hashlib.sha256(value).hexdigest()
        manifest_path.chmod(0o600)
        manifest_path.write_bytes(encode(manifest))

    def test_valid_snapshot_has_no_registered_candidate_signal(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            snapshot_root, service = self._snapshot(Path(temporary))
            snapshot = validate_party_snapshot(snapshot_root)
            self.assertEqual(snapshot.service["party_id"], 1)
            observation = audit_party_snapshot(snapshot_root)
            self.assertEqual(
                observation,
                {
                    "candidate_count": 2,
                    "candidate_signals": 0,
                    "cloud_material": "absent",
                    "compromised_parties": 1,
                    "excluded_path_accesses": 0,
                    "network_attempts": 0,
                    "secret_output_exposures": 0,
                    "snapshot_validation": "passed",
                    "threshold": 2,
                },
            )
            report = build_attack_report(
                scenario_id=PARTY_SNAPSHOT_SCENARIO,
                observed_result=observation,
            )
            self.assertEqual(report["status"], "passed")
            encoded_report = json.dumps(report, sort_keys=True)
            self.assertNotIn(service["authorizer_config"]["bid"], encoded_report)
            self.assertNotIn(service["signer_private_key"], encoded_report)
            self.assertNotIn(service["native_party"]["state"], encoded_report)
            self.assertNotIn("BEGIN PRIVATE KEY", encoded_report)

    def test_positive_control_exposes_a_candidate_signal_and_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            snapshot_root, _service = self._snapshot(Path(temporary))

            def synthetic_verifier(
                _service: Mapping[str, Any], candidate: bytes
            ) -> bool:
                return candidate.endswith(b"alpha-v1")

            observation = audit_party_snapshot(
                snapshot_root, candidate_probe=synthetic_verifier
            )
            self.assertEqual(observation["candidate_signals"], 2)
            report = build_attack_report(
                scenario_id=PARTY_SNAPSHOT_SCENARIO,
                observed_result=observation,
            )
            self.assertEqual(report["status"], "failed")

    def test_network_and_excluded_path_attempts_are_counted(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            snapshot_root, _service = self._snapshot(root)

            def network_probe(_service: Mapping[str, Any], _candidate: bytes) -> None:
                socket.create_connection(("127.0.0.1", 9))

            network = audit_party_snapshot(snapshot_root, candidate_probe=network_probe)
            self.assertEqual(network["network_attempts"], 2)
            self.assertEqual(
                build_attack_report(
                    scenario_id=PARTY_SNAPSHOT_SCENARIO,
                    observed_result=network,
                )["status"],
                "failed",
            )

            excluded = root / "cloud-object.json"
            excluded.write_text("excluded", encoding="ascii")

            def path_probe(_service: Mapping[str, Any], _candidate: bytes) -> None:
                excluded.read_bytes()

            path_result = audit_party_snapshot(
                snapshot_root, candidate_probe=path_probe
            )
            self.assertEqual(path_result["excluded_path_accesses"], 2)

    def test_extra_noncanonical_substituted_and_bad_checkpoint_fail_closed(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)

            extra, _service = self._snapshot(root / "extra")
            (extra / "party").chmod(0o700)
            (extra / "party" / "cloud-object.json").write_text("{}", encoding="ascii")
            with self.assertRaises(PartySnapshotError):
                audit_party_snapshot(extra)

            noncanonical, _service = self._snapshot(root / "noncanonical")
            manifest = json.loads(
                (noncanonical / "manifest.json").read_text(encoding="ascii")
            )
            (noncanonical / "manifest.json").chmod(0o600)
            (noncanonical / "manifest.json").write_text(
                json.dumps(manifest, indent=2), encoding="ascii"
            )
            with self.assertRaises(PartySnapshotError):
                audit_party_snapshot(noncanonical)

            substituted, _service = self._snapshot(root / "substituted")
            service_path = substituted / "party" / "service.json"
            changed = json.loads(service_path.read_text(encoding="ascii"))
            changed["party_id"] = 2
            service_path.chmod(0o600)
            service_path.write_text(
                json.dumps(changed, sort_keys=True, separators=(",", ":")),
                encoding="ascii",
            )
            self._rebind_manifest_file(substituted, "service.json")
            with self.assertRaises(PartySnapshotError):
                audit_party_snapshot(substituted)

            checkpoint, _service = self._snapshot(root / "checkpoint")
            (checkpoint / "party").chmod(0o700)
            database = checkpoint / "party" / "party.sqlite3"
            database.chmod(0o600)
            connection = sqlite3.connect(database)
            connection.execute("UPDATE epochs SET consumed = 0")
            connection.commit()
            connection.close()
            self._rebind_manifest_file(checkpoint, "party.sqlite3")
            with self.assertRaises(PartySnapshotError):
                audit_party_snapshot(checkpoint)

    def test_collector_rejects_unexpected_source_state(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            party_root, _service = self._party_checkpoint(root)
            (party_root / "client.json").write_text("{}", encoding="ascii")
            with self.assertRaises(PartySnapshotError):
                capture_party_snapshot(
                    party_root=party_root, snapshot_root=root / "snapshot"
                )


if __name__ == "__main__":
    unittest.main()
