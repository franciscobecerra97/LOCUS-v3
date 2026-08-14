from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from typing import Any, cast
from unittest.mock import patch

from cryptography import x509

from locus import _tpass_native as native
from locus.admission import (
    ADMISSION_BINDING_FORMAT,
    ADMISSION_CAPABILITY_FORMAT,
    LOCAL_ISSUER_PROFILE,
)
from locus.appss_formats import instance_id, oprf_input
from locus.contracts import GatewayResult, RecoveryContext, ThresholdParameters
from locus.cue_policy import CuePolicyError
from locus.integrated_bootstrap import (
    IntegratedBootstrapError,
    bootstrap_integrated_roles,
)
from locus.integrated_client import IntegratedResearchClientApi
from locus.integrated_manifest import EXPECTED_SERVICES
from locus.integrated_services import (
    ADMISSION_ISSUER,
    AdmissionRole,
    OperatorRole,
    PartyRole,
    ResolverRole,
    StorageGatewayRole,
)
from locus.integrated_state_audit import ALLOWED_CLIENT_FILES, audit_client_root
from locus.object_store import (
    BackupReference,
    ObjectConflict,
    ObjectCorrupt,
    ObjectNotFound,
    ObjectStale,
    ObjectStoreUnavailable,
)
from locus.provider_gateway import backup_object_key
from locus.yi_compat import YiTpassRecoveryAdapter
from tests.test_appss_party import CONTEXT, holder, request_bytes

ROOT = Path(__file__).resolve().parents[1]
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

    def test_networkless_bootstrap_rejects_symbolic_link_root(self) -> None:
        linked = Path(self.temporary.name) / "linked-roles"
        outside = Path(self.temporary.name) / "outside-roles"
        outside.mkdir()
        try:
            linked.symlink_to(outside, target_is_directory=True)
        except OSError as exc:
            self.skipTest(f"symbolic links unavailable: {exc}")
        with self.assertRaises(IntegratedBootstrapError):
            bootstrap_integrated_roles(root=linked, manifest_path=MANIFEST)

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

    def _recovery_binding(self, *, epoch: int = 1) -> dict[str, object]:
        issued_at = 1_900_000_000
        return {
            "audience": "locus-integrated-recovery",
            "backup_id": "11" * 16,
            "client_key_thumbprint": "22" * 32,
            "epoch": epoch,
            "expires_at": issued_at + 60,
            "format_id": ADMISSION_BINDING_FORMAT,
            "issued_at": issued_at,
            "issuer": ADMISSION_ISSUER,
            "nonce": "33" * 32,
            "object_prefix": None,
            "operation": "recovery_attempt",
            "profile_id": LOCAL_ISSUER_PROFILE,
            "subject": "11" * 32,
        }

    def test_admission_issue_rejects_non_client_caller_and_malformed_binding(
        self,
    ) -> None:
        # P8.1 coverage: AdmissionRole./v1/issue caller enforcement and
        # malformed/unauthorized-binding rejection (see
        # docs/p8.1-decoder-transition-inventory.md, Part A.1).
        admission = AdmissionRole(self.root / "admission")
        with self.assertRaises(ValueError):
            admission("/v1/issue", {"binding": self._recovery_binding()}, "party1")
        with self.assertRaises(ValueError):
            admission(
                "/v1/issue",
                {"binding": self._recovery_binding(), "extra": 1},
                "ui-client-a",
            )
        malformed = self._recovery_binding()
        del malformed["nonce"]
        with self.assertRaises(ValueError):
            admission("/v1/issue", {"binding": malformed}, "ui-client-a")
        wrong_subject = self._recovery_binding()
        wrong_subject["subject"] = "44" * 32
        with self.assertRaises(ValueError):
            admission("/v1/issue", {"binding": wrong_subject}, "ui-client-a")
        result = admission(
            "/v1/issue", {"binding": self._recovery_binding()}, "ui-client-a"
        )[1]
        self.assertEqual(result["status"], "issued")
        self.assertTrue(result["capability_hex"])

    def _discovery_record(
        self, *, epoch: int, handle: str = "handle-1"
    ) -> dict[str, object]:
        return {
            "backup_id": "11" * 16,
            "backup_digest": "22" * 32,
            "epoch": epoch,
            "public_fingerprint": "33" * 32,
            "recovery_handle": handle,
            "subject_id": "11" * 32,
        }

    def test_operator_discovery_publish_enforces_schema_and_epoch_monotonicity(
        self,
    ) -> None:
        # P8.1 coverage: OperatorRole ./v1/discovery/publish schema rejection,
        # idempotent same-epoch republish, stale-epoch rejection, and
        # higher-epoch overwrite; ./v1/discovery/read not-found rejection
        # (see docs/p8.1-decoder-transition-inventory.md, Part A.1).
        operator = OperatorRole(self.root / "operator")
        self.addCleanup(operator.database.close)
        malformed = self._discovery_record(epoch=1)
        del malformed["subject_id"]
        with self.assertRaises(ValueError):
            operator("/v1/discovery/publish", {"record": malformed}, "ui-client-a")
        first = self._discovery_record(epoch=1)
        published = operator("/v1/discovery/publish", {"record": first}, "ui-client-a")[
            1
        ]
        self.assertEqual(published["status"], "published")
        repeated = operator("/v1/discovery/publish", {"record": first}, "ui-client-a")[
            1
        ]
        self.assertEqual(repeated["status"], "published")
        stale = dict(first)
        stale["backup_digest"] = "44" * 32
        with self.assertRaises(ValueError):
            operator("/v1/discovery/publish", {"record": stale}, "ui-client-a")
        second = self._discovery_record(epoch=2)
        second["backup_digest"] = "55" * 32
        updated = operator("/v1/discovery/publish", {"record": second}, "ui-client-a")[
            1
        ]
        self.assertEqual(updated["status"], "published")
        read = operator(
            "/v1/discovery/read", {"recovery_handle": "handle-1"}, "ui-client-a"
        )[1]
        self.assertEqual(read["record"]["epoch"], 2)
        self.assertEqual(read["record"]["backup_digest"], "55" * 32)
        with self.assertRaises(ValueError):
            operator(
                "/v1/discovery/read",
                {"recovery_handle": "unknown-handle"},
                "ui-client-a",
            )

    def test_operator_sign_and_resolver_decoders_reject_wrong_shape_and_caller(
        self,
    ) -> None:
        operator = OperatorRole(self.root / "operator")
        self.addCleanup(operator.database.close)
        resolver = ResolverRole()
        with self.assertRaises(ValueError):
            operator(
                "/v1/sign",
                {"kind": "descriptor", "payload": {}},
                "party1",
            )
        with self.assertRaises(ValueError):
            operator(
                "/v1/sign",
                {"kind": "unsupported", "payload": {}},
                "ui-client-a",
            )
        with self.assertRaises(ValueError):
            operator(
                "/v1/sign",
                {"kind": "descriptor", "payload": {}, "unknown": True},
                "ui-client-a",
            )
        with self.assertRaises(ValueError):
            resolver(
                "/v1/resolve",
                {"policy_id": "LOCUS-location-person-set-v1", "values": []},
                "party1",
            )
        for values in cast(tuple[object, ...], (None, {}, [], [None] * 65)):
            with self.subTest(values_type=type(values).__name__):
                with self.assertRaises(CuePolicyError):
                    resolver(
                        "/v1/resolve",
                        {
                            "policy_id": "LOCUS-location-person-set-v1",
                            "values": values,
                        },
                        "ui-client-a",
                    )

    def _storage_request(self) -> dict[str, object]:
        binding = self._recovery_binding()
        reference = BackupReference("11" * 16, 1, "44" * 32)
        return {
            "binding": binding,
            "capability": {
                "format_id": ADMISSION_CAPABILITY_FORMAT,
                "payload_hex": "55" * 64,
            },
            "client_proof": "66" * 64,
            "gateway_request": {
                "backup_reference": reference.to_dict(),
                "object_key": backup_object_key(str(binding["subject"]), reference),
                "operation": "read_exact",
                "payload_hex": None,
            },
            "now": 1_900_000_001,
            "recovery_handle": "handle-1",
        }

    def test_storage_gateway_route_is_bounded_and_maps_backend_categories(self) -> None:
        role = object.__new__(StorageGatewayRole)
        role.verifier = cast(Any, object())
        role.provider = cast(Any, object())
        request = self._storage_request()

        with self.assertRaises(ValueError):
            role("/v1/execute", request, "party1")
        changed = dict(request)
        changed["unknown"] = True
        with self.assertRaises(ValueError):
            role("/v1/execute", changed, "ui-client-a")
        changed = {**request, "gateway_request": {"operation": "read_exact"}}
        with self.assertRaises(ValueError):
            role("/v1/execute", changed, "ui-client-a")
        oversized = self._storage_request()
        oversized_gateway = dict(cast(dict[str, object], oversized["gateway_request"]))
        oversized_gateway["payload_hex"] = "00" * (2 * 1024 * 1024 + 1)
        oversized["gateway_request"] = oversized_gateway
        with self.assertRaises(ValueError):
            role("/v1/execute", oversized, "ui-client-a")

        reference = BackupReference("11" * 16, 1, "44" * 32)
        outcomes = (
            (ObjectNotFound("missing"), 404, "object_not_found"),
            (ObjectConflict("conflict"), 409, "object_conflict"),
            (ObjectStale("stale"), 409, "object_stale"),
            (ObjectCorrupt("corrupt"), 400, "object_rejected"),
            (ObjectStoreUnavailable("down"), 503, "provider_unavailable"),
        )
        for failure, status, category in outcomes:
            with self.subTest(category=category):
                with patch(
                    "locus.integrated_services.LocalAdmissionStorageGateway.execute",
                    side_effect=failure,
                ):
                    observed_status, observed = role(
                        "/v1/execute", request, "ui-client-a"
                    )
                self.assertEqual(observed_status, status)
                self.assertEqual(observed["category"], category)
        with patch(
            "locus.integrated_services.LocalAdmissionStorageGateway.execute",
            return_value=GatewayResult(reference=reference, payload=b"safe"),
        ):
            status, observed = role("/v1/execute", request, "ui-client-a")
        self.assertEqual(status, 200)
        self.assertEqual(observed["payload_hex"], b"safe".hex())

    def test_party_route_retries_sessions_and_retirement_fail_closed(self) -> None:
        party = PartyRole(self.root / "party1", 1)
        self.addCleanup(party.database.close)
        self.addCleanup(party.admission_verifier._replay_store.close)

        payload = {
            "authorizer_id": 1,
            "backup_id": "11" * 16,
            "configuration_digest": "22" * 32,
            "cue_policy_id": "LOCUS-canonical-email-set-v1",
            "descriptor_sha256": "33" * 32,
            "epoch": 1,
            "expires_at": 1_900_000_120,
            "issued_at": 1_900_000_000,
            "recovery_id": "integrated-recovery:test",
            "recovery_suite_id": "LOCUS-TPASS-YI-ZK-RISTRETTO255-v1",
            "state": "active",
            "subject_id": "11" * 32,
        }
        party("/v1/current/install", {"payload": payload}, "ui-client-a")
        changed = dict(payload)
        changed["configuration_digest"] = "44" * 32
        with self.assertRaises(ValueError):
            party("/v1/current/install", {"payload": changed}, "ui-client-a")
        wrong_recipient = dict(payload)
        wrong_recipient["authorizer_id"] = 2
        with self.assertRaises(ValueError):
            party("/v1/current/install", {"payload": wrong_recipient}, "ui-client-a")
        with self.assertRaises(ValueError):
            party(
                "/v1/current/retire",
                {
                    "backup_id": "11" * 16,
                    "predecessor_epoch": 1,
                    "successor_epoch": 3,
                },
                "ui-client-a",
            )
        with self.assertRaises(ValueError):
            party(
                "/v1/yi/prepare",
                {
                    "backup_id": "11" * 16,
                    "epoch": 1,
                    "grant_digest": "unauthorized",
                    "request_hex": "00",
                    "selected": [1, 2],
                    "session_id": "session",
                },
                "ui-client-a",
            )
        with self.assertRaises(ValueError):
            party(
                "/v1/yi/respond",
                {"commitments": [], "request_hex": "00", "session_id": "missing"},
                "ui-client-a",
            )

    def test_party_yi_and_appss_decoders_bind_recipient_and_exact_retry(self) -> None:
        party = PartyRole(self.root / "party1", 1)
        self.addCleanup(party.database.close)
        self.addCleanup(party.admission_verifier._replay_store.close)

        context = RecoveryContext(
            suite_id="LOCUS-TPASS-YI-ZK-RISTRETTO255-v1",
            recovery_id="p8-route-assurance",
            backup_id="11" * 16,
            epoch=1,
            policy_id="LOCUS-canonical-email-set-v1",
            configuration_digest="22" * 32,
            digest_context="p8-route-assurance:1",
        )
        adapter = YiTpassRecoveryAdapter()
        enrollment = adapter.initialize(
            context=context,
            password_input=b"correct".ljust(32, b"\x00"),
            threshold=ThresholdParameters(2, 3),
        )
        yi_request = {
            "backup_id": context.backup_id,
            "context": context.__dict__,
            "epoch": context.epoch,
            "party_state_hex": enrollment.party_states[0].payload.hex(),
            "public_state_hex": enrollment.public_state.payload.hex(),
        }
        self.assertEqual(
            party("/v1/yi/enroll", yi_request, "ui-client-a")[1]["status"],
            "ready",
        )
        self.assertEqual(
            party("/v1/yi/enroll", yi_request, "ui-client-a")[1]["status"],
            "ready",
        )
        replacement = adapter.initialize(
            context=context,
            password_input=b"correct".ljust(32, b"\x00"),
            threshold=ThresholdParameters(2, 3),
        )
        changed_yi = dict(yi_request)
        changed_yi["party_state_hex"] = replacement.party_states[0].payload.hex()
        changed_yi["public_state_hex"] = replacement.public_state.payload.hex()
        with self.assertRaises(ValueError):
            party("/v1/yi/enroll", changed_yi, "ui-client-a")

        session, blinded = native.appss_blind(
            oprf_input(instance_id(CONTEXT, holder(1)), b"password".ljust(32, b"\x00"))
        )
        del session
        initialize = request_bytes(
            holder_id=1,
            operation="initialize",
            operation_id="71" * 32,
            session_id="72" * 32,
            nonce="73" * 32,
            blinded=blinded,
            omega_digest=None,
        )
        self.assertEqual(
            party(
                "/v1/appss/initialize",
                {"request_hex": initialize.hex()},
                "ui-client-a",
            )[1]["status"],
            "responded",
        )
        _session, wrong_blinded = native.appss_blind(
            oprf_input(instance_id(CONTEXT, holder(2)), b"password".ljust(32, b"\x00"))
        )
        wrong_recipient = request_bytes(
            holder_id=2,
            operation="initialize",
            operation_id="74" * 32,
            session_id="75" * 32,
            nonce="76" * 32,
            blinded=wrong_blinded,
            omega_digest=None,
        )
        with self.assertRaises(ValueError):
            party(
                "/v1/appss/initialize",
                {"request_hex": wrong_recipient.hex()},
                "ui-client-a",
            )
        recover = request_bytes(
            holder_id=1,
            operation="recover",
            operation_id="77" * 32,
            session_id="78" * 32,
            nonce="79" * 32,
            blinded=blinded,
            omega_digest="7a" * 32,
        )
        with self.assertRaises(ValueError):
            party(
                "/v1/appss/evaluate",
                {"request_hex": recover.hex()},
                "ui-client-a",
            )


if __name__ == "__main__":
    unittest.main()
