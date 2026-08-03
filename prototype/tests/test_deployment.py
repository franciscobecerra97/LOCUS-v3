from __future__ import annotations

import json
import tempfile
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from locus.cue_policy import POLICY_VERSION
from locus.deployed_profile import BACKUP_VERSION, DEPLOYMENT_VERSION
from locus.deployment import (
    DeploymentError,
    _validate_deployed_backup_profile,
    _wait_for_lifecycle_restart,
    audit_layout,
    provision,
)

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "deploy" / "fixtures" / "cues.json"


class DeploymentProvisioningTests(unittest.TestCase):
    def test_container_image_includes_both_native_suite_crates(self) -> None:
        dockerfile = (ROOT / "deploy" / "Dockerfile").read_text(encoding="utf-8")
        self.assertIn("COPY appss-core ./appss-core", dockerfile)
        self.assertIn("COPY tpass-core ./tpass-core", dockerfile)
        self.assertLess(
            dockerfile.index("COPY appss-core ./appss-core"),
            dockerfile.index("RUN python -m maturin build"),
        )

    def test_lifecycle_restart_checkpoint_requires_host_acknowledgement(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            checkpoint_dir = Path(temporary)
            ready = checkpoint_dir / "locus-lifecycle-restart-ready"
            complete = checkpoint_dir / "locus-lifecycle-restart-complete"
            with ThreadPoolExecutor(max_workers=1) as executor:
                pending = executor.submit(_wait_for_lifecycle_restart, checkpoint_dir)
                deadline = time.monotonic() + 2.0
                while not ready.is_file():
                    self.assertLess(time.monotonic(), deadline)
                    time.sleep(0.01)
                complete.touch(exist_ok=False)
                pending.result(timeout=2.0)
            self.assertFalse(ready.exists())
            self.assertFalse(complete.exists())

    def test_provisioning_is_idempotent_and_role_separated(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            party_roots = [root / f"party{party_id}" for party_id in range(1, 6)]
            client_root = root / "client"
            self.assertEqual(
                provision(
                    party_roots=party_roots,
                    client_root=client_root,
                    fixture_path=FIXTURE,
                ),
                "created",
            )
            self.assertEqual(
                audit_layout(party_roots, client_root),
                {
                    "client_has_party_secrets": False,
                    "party_count": 5,
                    "party_states_distinct": True,
                    "status": "ok",
                    "version": DEPLOYMENT_VERSION,
                },
            )
            self.assertEqual(
                provision(
                    party_roots=party_roots,
                    client_root=client_root,
                    fixture_path=FIXTURE,
                ),
                "existing",
            )

            client_bytes = (client_root / "deployment.json").read_bytes()
            states: list[str] = []
            for party_id, party_root in enumerate(party_roots, start=1):
                config = json.loads(
                    (party_root / "service.json").read_text(encoding="ascii")
                )
                native_party = config["native_party"]
                if party_id <= 3:
                    states.append(native_party["state"])
                else:
                    self.assertIsNone(native_party)
                self.assertNotIn("fixture.friend@example.org", json.dumps(config))
            self.assertEqual(len(set(states)), 3)
            self.assertTrue(
                all(state.encode("ascii") not in client_bytes for state in states)
            )
            self.assertNotIn(b"signer_private_key", client_bytes)
            self.assertNotIn(b"fixture.friend@example.org", client_bytes)

            deployment = json.loads(client_bytes)
            self.assertEqual(deployment["backup"]["version"], BACKUP_VERSION)
            self.assertEqual(
                deployment["backup"]["context_policy"],
                {"version": POLICY_VERSION},
            )
            self.assertIs(
                _validate_deployed_backup_profile(deployment["backup"]),
                deployment["backup"],
            )

            (party_roots[1] / "party.sqlite3").write_text(states[0], encoding="ascii")
            with self.assertRaises(DeploymentError):
                audit_layout(party_roots, client_root)

    def test_deployed_profile_rejects_legacy_and_mismatched_policy_labels(
        self,
    ) -> None:
        valid = {
            "version": BACKUP_VERSION,
            "context_policy": {"version": POLICY_VERSION},
        }
        self.assertIs(_validate_deployed_backup_profile(valid), valid)

        legacy = {
            "version": "LOCUS-reference-backup-v3",
            "context_policy": {"version": "LOCUS-local-context-v1"},
        }
        with self.assertRaisesRegex(
            DeploymentError, "unsupported deployed backup version"
        ):
            _validate_deployed_backup_profile(legacy)

        wrong_policy = {
            "version": BACKUP_VERSION,
            "context_policy": {"version": "LOCUS-local-context-v1"},
        }
        with self.assertRaisesRegex(
            DeploymentError, "unsupported deployed context policy"
        ):
            _validate_deployed_backup_profile(wrong_policy)

        for mixed in (
            {
                "version": "LOCUS-reference-backup-v3",
                "context_policy": {"version": POLICY_VERSION},
            },
            {
                "version": "LOCUS-development-backup-v1",
                "context_policy": {"version": "LOCUS-development-context-v1"},
            },
            {
                "version": BACKUP_VERSION,
                "context_policy": {
                    "version": POLICY_VERSION,
                    "pair_count": 3,
                },
            },
        ):
            with self.subTest(mixed=mixed):
                with self.assertRaises(DeploymentError):
                    _validate_deployed_backup_profile(mixed)

    def test_partial_layout_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            party_roots = [root / f"party{party_id}" for party_id in range(1, 6)]
            client_root = root / "client"
            party_roots[0].mkdir()
            (party_roots[0] / "partial").write_text("incomplete", encoding="ascii")
            with self.assertRaises(DeploymentError):
                provision(
                    party_roots=party_roots,
                    client_root=client_root,
                    fixture_path=FIXTURE,
                )


if __name__ == "__main__":
    unittest.main()
