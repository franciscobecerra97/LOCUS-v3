from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cryptography import x509
from locus.integrated_bootstrap import (
    IntegratedBootstrapError,
    bootstrap_integrated_roles,
)
from locus.integrated_client import IntegratedResearchClientApi
from locus.integrated_manifest import EXPECTED_SERVICES
from locus.integrated_services import (
    AdmissionRole,
    OperatorRole,
    PartyRole,
    ResolverRole,
)
from locus.integrated_state_audit import ALLOWED_CLIENT_FILES, audit_client_root
from locus.object_store import BackupReference

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "deploy" / "integrated-manifest.json"


class IntegratedServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "roles"
        bootstrap_integrated_roles(root=self.root, manifest_path=MANIFEST)

    def test_networkless_bootstrap_creates_distinct_empty_role_roots(self) -> None:
        self.assertEqual(
            {item.name for item in self.root.iterdir()}, set(EXPECTED_SERVICES)
        )
        serials = set()
        for role in EXPECTED_SERVICES:
            role_root = self.root / role
            self.assertTrue((role_root / "ca.pem").is_file())
            if role != "bootstrap":
                certificate = x509.load_pem_x509_certificate(
                    (role_root / "tls-cert.pem").read_bytes()
                )
                serials.add(certificate.serial_number)
        self.assertEqual(len(serials), len(EXPECTED_SERVICES) - 1)
        self.assertNotEqual(
            (self.root / "ui-client-a" / "proof-key.bin").read_bytes(),
            (self.root / "ui-client-b" / "proof-key.bin").read_bytes(),
        )
        names = {path.name.lower() for path in self.root.rglob("*") if path.is_file()}
        self.assertFalse(
            any(
                "suite" in name or "backup" in name or "share" in name for name in names
            )
        )
        with self.assertRaises(IntegratedBootstrapError):
            bootstrap_integrated_roles(root=self.root, manifest_path=MANIFEST)
        (self.root / "party1" / "runtime.sqlite3").write_bytes(b"runtime-state")
        bootstrap_integrated_roles(
            root=self.root, manifest_path=MANIFEST, allow_existing=True
        )

    def test_client_roots_pass_isolation_audit_and_positive_control_fails(self) -> None:
        audit_client_root(self.root / "ui-client-a")
        observed = {
            path.name
            for path in (self.root / "ui-client-a").iterdir()
            if path.is_file()
        }
        self.assertEqual(observed, ALLOWED_CLIENT_FILES)
        marker = self.root / "ui-client-a" / "inherited-state.sqlite3"
        marker.write_bytes(b"positive-control")
        with self.assertRaises(ValueError):
            audit_client_root(self.root / "ui-client-a")

    def test_admission_operator_and_resolver_enforce_caller_and_route(self) -> None:
        admission = AdmissionRole(self.root / "admission")
        operator = OperatorRole(self.root / "operator")
        self.addCleanup(operator.database.close)
        resolver = ResolverRole()
        self.assertEqual(admission("/health", {}, "party1")[1]["status"], "ready")
        self.assertEqual(operator("/health", {}, "party1")[1]["status"], "ready")
        with self.assertRaises(ValueError):
            resolver(
                "/v1/resolve",
                {"policy_id": "LOCUS-canonical-email-set-v1", "values": []},
                "ui-client-a",
            )
        result = resolver(
            "/v1/resolve",
            {
                "policy_id": "LOCUS-location-person-set-v1",
                "values": [
                    {
                        "location": {"latitude": "49.6116", "longitude": "6.1319"},
                        "person": {"type": "email", "value": "ada@example.test"},
                    },
                    {
                        "location": {"latitude": "48.8566", "longitude": "2.3522"},
                        "person": {"type": "phone", "value": "+352621000002"},
                    },
                    {
                        "location": {"latitude": "51.5074", "longitude": "-0.1278"},
                        "person": {"type": "email", "value": "linus@example.test"},
                    },
                ],
            },
            "ui-client-a",
        )[1]
        self.assertEqual(result["status"], "resolved")
        self.assertEqual(resolver("/v1/count", {}, "ui-client-a")[1]["contacts"], 1)
        self.assertIsInstance(json.loads(bytes.fromhex(result["canonical_hex"])), dict)

    def test_current_observations_tolerate_one_unavailable_authorizer(self) -> None:
        client = object.__new__(IntegratedResearchClientApi)
        reference = BackupReference("11" * 16, 1, "22" * 32)

        def current(index: int, _path: str, _request: object) -> dict[str, str]:
            if index == 1:
                raise ValueError("synthetic unavailability")
            return {"summary_hex": f"{index:02x}"}

        with patch.object(client, "_party", side_effect=current):
            observations = client._current_observations(reference)
        self.assertEqual([item.authorizer_id for item in observations], [2, 3, 4, 5])

    def test_party_current_retirement_is_exact_and_successor_preserving(self) -> None:
        party = PartyRole(self.root / "party1", 1)
        self.addCleanup(party.database.close)
        self.addCleanup(party.admission_verifier._replay_store.close)

        def payload(epoch: int) -> dict[str, object]:
            return {
                "authorizer_id": 1,
                "backup_id": "11" * 16,
                "configuration_digest": f"{epoch:02x}" * 32,
                "cue_policy_id": "LOCUS-canonical-email-set-v1",
                "descriptor_sha256": f"{epoch + 2:02x}" * 32,
                "epoch": epoch,
                "expires_at": 1_900_000_120,
                "issued_at": 1_900_000_000,
                "recovery_id": "integrated-recovery:test",
                "recovery_suite_id": "LOCUS-TPASS-YI-ZK-RISTRETTO255-v1",
                "state": "active",
                "subject_id": "11" * 32,
            }

        for epoch in (1, 2):
            result = party(
                "/v1/current/install", {"payload": payload(epoch)}, "ui-client-b"
            )[1]
            self.assertEqual(result["status"], "active")
        request = {
            "backup_id": "11" * 16,
            "predecessor_epoch": 1,
            "successor_epoch": 2,
        }
        self.assertEqual(
            party("/v1/current/retire", request, "ui-client-b")[1]["status"],
            "retired",
        )
        self.assertEqual(
            party("/v1/current/retire", request, "ui-client-b")[1]["status"],
            "retired",
        )
        with self.assertRaises(ValueError):
            party(
                "/v1/current/read",
                {"backup_id": "11" * 16, "epoch": 1},
                "ui-client-b",
            )
        self.assertEqual(
            party(
                "/v1/current/read",
                {"backup_id": "11" * 16, "epoch": 2},
                "ui-client-b",
            )[1]["status"],
            "active",
        )
        inspected = party("/v1/inspect", {}, "ui-client-b")[1]
        self.assertEqual(inspected["active_epochs"], 1)
        self.assertEqual(inspected["retired_epochs"], 1)


if __name__ == "__main__":
    unittest.main()
