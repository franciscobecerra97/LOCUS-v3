from __future__ import annotations

import copy
import hashlib
import json
import socket
import tempfile
import unittest
from collections.abc import Mapping
from pathlib import Path
from typing import Any, ClassVar

from locus.attack_runner import build_attack_report
from locus.cloud_snapshot import (
    CLOUD_SNAPSHOT_INPUT_VERSION,
    CLOUD_SNAPSHOT_SCENARIO,
    CloudSnapshotError,
    audit_cloud_snapshot,
    validate_cloud_snapshot,
)
from locus.codec import encode
from locus.deployment import provision
from locus.object_store import backup_digest, encode_backup_object

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "deploy" / "fixtures" / "cues.json"


class CloudSnapshotAttackTests(unittest.TestCase):
    backup: dict[str, Any]
    _provisioned: ClassVar[tempfile.TemporaryDirectory[str]]

    @classmethod
    def setUpClass(cls) -> None:
        cls._provisioned = tempfile.TemporaryDirectory()
        root = Path(cls._provisioned.name)
        client_root = root / "client"
        provision(
            party_roots=[root / f"party{party_id}" for party_id in range(1, 6)],
            client_root=client_root,
            fixture_path=FIXTURE,
        )
        deployment = json.loads(
            (client_root / "deployment.json").read_text(encoding="ascii")
        )
        cls.backup = deployment["backup"]

    @classmethod
    def tearDownClass(cls) -> None:
        cls._provisioned.cleanup()

    def _snapshot(
        self,
        root: Path,
        *,
        backup: dict[str, Any] | None = None,
        canonical_manifest: bool = True,
    ) -> Path:
        snapshot_root = root / "snapshot"
        snapshot_root.mkdir(parents=True)
        reference, object_bytes = encode_backup_object(backup or self.backup)
        manifest = {
            "backend": "s3-compatible",
            "bucket": "locus-backups",
            "object_bytes": len(object_bytes),
            "object_key": f"attack/test/{reference.bid}/{reference.epoch}.json",
            "object_sha256": hashlib.sha256(object_bytes).hexdigest(),
            "version": CLOUD_SNAPSHOT_INPUT_VERSION,
        }
        (snapshot_root / "object.json").write_bytes(object_bytes)
        manifest_bytes = (
            encode(manifest)
            if canonical_manifest
            else json.dumps(manifest, indent=2).encode("ascii")
        )
        (snapshot_root / "manifest.json").write_bytes(manifest_bytes)
        return snapshot_root

    def test_valid_snapshot_has_no_registered_candidate_signal(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            snapshot_root = self._snapshot(Path(temporary))
            snapshot = validate_cloud_snapshot(snapshot_root)
            self.assertEqual(snapshot.backup, self.backup)
            observation = audit_cloud_snapshot(snapshot_root)
            self.assertEqual(
                observation,
                {
                    "candidate_count": 2,
                    "candidate_signals": 0,
                    "excluded_path_accesses": 0,
                    "network_attempts": 0,
                    "prohibited_material": "absent",
                    "snapshot_validation": "passed",
                },
            )
            report = build_attack_report(
                scenario_id=CLOUD_SNAPSHOT_SCENARIO,
                observed_result=observation,
            )
            self.assertEqual(report["status"], "passed")
            encoded_report = json.dumps(report, sort_keys=True)
            self.assertNotIn("ciphertext", encoded_report)
            self.assertNotIn(self.backup["bid"], encoded_report)

    def test_positive_control_exposes_a_candidate_signal_and_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            snapshot_root = self._snapshot(Path(temporary))

            def synthetic_verifier(
                _backup: Mapping[str, Any], candidate: bytes
            ) -> bool:
                return candidate.endswith(b"alpha-v1")

            observation = audit_cloud_snapshot(
                snapshot_root, candidate_probe=synthetic_verifier
            )
            self.assertEqual(observation["candidate_signals"], 2)
            report = build_attack_report(
                scenario_id=CLOUD_SNAPSHOT_SCENARIO,
                observed_result=observation,
            )
            self.assertEqual(report["status"], "failed")

    def test_network_and_excluded_path_attempts_are_counted(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            snapshot_root = self._snapshot(root)

            def network_probe(_backup: Mapping[str, Any], _candidate: bytes) -> None:
                socket.create_connection(("127.0.0.1", 9))

            network = audit_cloud_snapshot(snapshot_root, candidate_probe=network_probe)
            self.assertEqual(network["network_attempts"], 2)
            self.assertEqual(
                build_attack_report(
                    scenario_id=CLOUD_SNAPSHOT_SCENARIO,
                    observed_result=network,
                )["status"],
                "failed",
            )

            excluded = root / "party.sqlite3"
            excluded.write_text("excluded", encoding="ascii")

            def path_probe(_backup: Mapping[str, Any], _candidate: bytes) -> None:
                excluded.read_bytes()

            path_result = audit_cloud_snapshot(
                snapshot_root, candidate_probe=path_probe
            )
            self.assertEqual(path_result["excluded_path_accesses"], 2)

    def test_extra_malformed_noncanonical_and_substituted_inputs_fail_closed(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            extra_snapshot = self._snapshot(root / "extra")
            (extra_snapshot / "deployment.json").write_text("{}", encoding="ascii")
            with self.assertRaises(CloudSnapshotError):
                audit_cloud_snapshot(extra_snapshot)

            noncanonical = self._snapshot(
                root / "noncanonical", canonical_manifest=False
            )
            with self.assertRaises(CloudSnapshotError):
                audit_cloud_snapshot(noncanonical)

            substituted = self._snapshot(root / "substituted")
            changed = copy.deepcopy(self.backup)
            changed["nonce"] = "00" * 16
            changed["digest"] = backup_digest(changed)
            _, changed_bytes = encode_backup_object(changed)
            (substituted / "object.json").write_bytes(changed_bytes)
            with self.assertRaises(CloudSnapshotError):
                audit_cloud_snapshot(substituted)

            malformed = self._snapshot(root / "malformed")
            (malformed / "manifest.json").write_bytes(b"{}")
            with self.assertRaises(CloudSnapshotError):
                audit_cloud_snapshot(malformed)


if __name__ == "__main__":
    unittest.main()
