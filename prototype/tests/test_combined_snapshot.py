from __future__ import annotations

import base64
import hashlib
import json
import shutil
import socket
import tempfile
import unittest
from pathlib import Path
from typing import Any

from locus.attack_runner import build_attack_report
from locus.attempt_certificates import AuthorizerConfig
from locus.cloud_snapshot import CLOUD_SNAPSHOT_INPUT_VERSION
from locus.codec import encode
from locus.combined_snapshot import (
    CAPTURE_CHECKPOINT,
    CLOUD_DIRECTORY,
    COMBINED_SNAPSHOT_INPUT_VERSION,
    COMBINED_SNAPSHOT_PROFILE,
    COMBINED_SNAPSHOT_SCENARIO,
    PARTY_DIRECTORY,
    CombinedSnapshot,
    CombinedSnapshotError,
    audit_combined_snapshot,
    finalize_combined_snapshot,
    validate_combined_snapshot,
)
from locus.deployment import ATTEMPT_BUDGET, provision
from locus.object_store import encode_backup_object
from locus.party_snapshot import (
    PARTY_SNAPSHOT_INPUT_VERSION,
    capture_party_snapshot,
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


class CombinedSnapshotAttackTests(unittest.TestCase):
    def _deployment_checkpoint(
        self, root: Path
    ) -> tuple[dict[str, Any], Path, dict[str, Any]]:
        party_roots = [root / f"party{party_id}" for party_id in range(1, 6)]
        client_root = root / "client"
        provision(
            party_roots=party_roots,
            client_root=client_root,
            fixture_path=FIXTURE,
        )
        deployment = json.loads(
            (client_root / "deployment.json").read_text(encoding="ascii")
        )
        backup = deployment["backup"]
        party_root = party_roots[0]
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
        return backup, party_root, service

    def _cloud_subsnapshot(self, root: Path, backup: dict[str, Any]) -> None:
        root.mkdir(parents=True)
        reference, object_bytes = encode_backup_object(backup)
        manifest = {
            "backend": "s3-compatible",
            "bucket": "locus-backups",
            "object_bytes": len(object_bytes),
            "object_key": f"combined/test/{reference.bid}/{reference.epoch}.json",
            "object_sha256": hashlib.sha256(object_bytes).hexdigest(),
            "version": CLOUD_SNAPSHOT_INPUT_VERSION,
        }
        (root / "object.json").write_bytes(object_bytes)
        (root / "manifest.json").write_bytes(encode(manifest))

    def _subsnapshots(self, root: Path) -> tuple[Path, dict[str, Any], dict[str, Any]]:
        backup, party_root, service = self._deployment_checkpoint(root / "source")
        combined_root = root / "combined"
        self._cloud_subsnapshot(combined_root / CLOUD_DIRECTORY, backup)
        capture_party_snapshot(
            party_root=party_root,
            snapshot_root=combined_root / PARTY_DIRECTORY,
        )
        return combined_root, backup, service

    def _top_manifest(self, root: Path) -> dict[str, object]:
        cloud_manifest = (root / CLOUD_DIRECTORY / "manifest.json").read_bytes()
        party_manifest = (root / PARTY_DIRECTORY / "manifest.json").read_bytes()
        return {
            "capture_checkpoint": CAPTURE_CHECKPOINT,
            "cloud_manifest_sha256": hashlib.sha256(cloud_manifest).hexdigest(),
            "cloud_snapshot_version": CLOUD_SNAPSHOT_INPUT_VERSION,
            "compromised_parties": 1,
            "party_manifest_sha256": hashlib.sha256(party_manifest).hexdigest(),
            "party_snapshot_version": PARTY_SNAPSHOT_INPUT_VERSION,
            "profile": COMBINED_SNAPSHOT_PROFILE,
            "threshold": 2,
            "version": COMBINED_SNAPSHOT_INPUT_VERSION,
        }

    def _snapshot(self, root: Path) -> tuple[Path, dict[str, Any], dict[str, Any]]:
        combined_root, backup, service = self._subsnapshots(root)
        result = finalize_combined_snapshot(combined_root)
        self.assertEqual(
            result,
            {
                "artifact": COMBINED_SNAPSHOT_INPUT_VERSION,
                "status": "finalized",
            },
        )
        return combined_root, backup, service

    def test_valid_union_has_no_registered_candidate_signal(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            snapshot_root, backup, service = self._snapshot(Path(temporary))
            snapshot = validate_combined_snapshot(snapshot_root)
            self.assertEqual(snapshot.cloud.backup, backup)
            self.assertEqual(snapshot.party.service["party_id"], 1)
            observation = audit_combined_snapshot(snapshot_root)
            self.assertEqual(
                observation,
                {
                    "candidate_count": 2,
                    "candidate_signals": 0,
                    "cloud_snapshot_validation": "passed",
                    "combined_binding": "matched",
                    "compromised_parties": 1,
                    "excluded_path_accesses": 0,
                    "network_attempts": 0,
                    "party_snapshot_validation": "passed",
                    "party_snapshots": 1,
                    "secret_output_exposures": 0,
                    "threshold": 2,
                },
            )
            report = build_attack_report(
                scenario_id=COMBINED_SNAPSHOT_SCENARIO,
                observed_result=observation,
            )
            self.assertEqual(report["status"], "passed")
            encoded_report = json.dumps(report, sort_keys=True)
            self.assertNotIn(backup["bid"], encoded_report)
            self.assertNotIn(backup["ciphertext"]["ciphertext"], encoded_report)
            self.assertNotIn(service["signer_private_key"], encoded_report)
            self.assertNotIn(service["native_party"]["state"], encoded_report)

    def test_positive_verifier_produces_signals_and_failed_report(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            snapshot_root, _backup, _service = self._snapshot(Path(temporary))

            def verifier(_snapshot: CombinedSnapshot, candidate: bytes) -> bool:
                return candidate.endswith(b"alpha-v1")

            observation = audit_combined_snapshot(
                snapshot_root, candidate_probe=verifier
            )
            self.assertEqual(observation["candidate_signals"], 2)
            self.assertEqual(
                build_attack_report(
                    scenario_id=COMBINED_SNAPSHOT_SCENARIO,
                    observed_result=observation,
                )["status"],
                "failed",
            )

    def test_network_and_excluded_path_attempts_are_counted(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            snapshot_root, _backup, _service = self._snapshot(root)

            def network_probe(_snapshot: CombinedSnapshot, _candidate: bytes) -> None:
                socket.create_connection(("127.0.0.1", 9))

            network = audit_combined_snapshot(
                snapshot_root, candidate_probe=network_probe
            )
            self.assertEqual(network["network_attempts"], 2)

            excluded = root / "other-party.sqlite3"
            excluded.write_text("excluded", encoding="ascii")

            def path_probe(_snapshot: CombinedSnapshot, _candidate: bytes) -> None:
                excluded.read_bytes()

            path_result = audit_combined_snapshot(
                snapshot_root, candidate_probe=path_probe
            )
            self.assertEqual(path_result["excluded_path_accesses"], 2)

    def test_manifest_consistent_mismatched_enrollments_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first, _first_backup, _first_service = self._subsnapshots(root / "first")
            second, _second_backup, _second_service = self._subsnapshots(
                root / "second"
            )
            mixed = root / "mixed"
            shutil.copytree(first / CLOUD_DIRECTORY, mixed / CLOUD_DIRECTORY)
            shutil.copytree(second / PARTY_DIRECTORY, mixed / PARTY_DIRECTORY)
            with self.assertRaises(CombinedSnapshotError):
                finalize_combined_snapshot(mixed)
            (mixed / "manifest.json").write_bytes(encode(self._top_manifest(mixed)))
            with self.assertRaises(CombinedSnapshotError):
                validate_combined_snapshot(mixed)

    def test_extra_noncanonical_and_submanifest_substitution_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)

            extra, _backup, _service = self._snapshot(root / "extra")
            (extra / "client.json").write_text("{}", encoding="ascii")
            with self.assertRaises(CombinedSnapshotError):
                audit_combined_snapshot(extra)

            noncanonical, _backup, _service = self._snapshot(root / "noncanonical")
            manifest_path = noncanonical / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="ascii"))
            manifest_path.chmod(0o600)
            manifest_path.write_text(json.dumps(manifest, indent=2), encoding="ascii")
            with self.assertRaises(CombinedSnapshotError):
                audit_combined_snapshot(noncanonical)

            substituted, _backup, _service = self._snapshot(root / "substituted")
            cloud_manifest = substituted / CLOUD_DIRECTORY / "manifest.json"
            cloud_manifest.chmod(0o600)
            cloud_manifest.write_bytes(cloud_manifest.read_bytes() + b" ")
            with self.assertRaises(CombinedSnapshotError):
                audit_combined_snapshot(substituted)

    def test_finalizer_refuses_an_existing_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            snapshot_root, _backup, _service = self._snapshot(Path(temporary))
            with self.assertRaises(CombinedSnapshotError):
                finalize_combined_snapshot(snapshot_root)


if __name__ == "__main__":
    unittest.main()
