from __future__ import annotations

import hashlib
import json
import secrets
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from locus.appss_formats import YI_PROFILE_2_OF_3, YI_SUITE_ID
from locus.client_api import (
    BootstrapResult,
    ClientApiError,
    EnrollmentResult,
    RecoveryResult,
)
from locus.codec import encode
from locus.contracts import ThresholdParameters
from locus.integrated_client import (
    AuthenticatedRecoveryPackage,
    IntegratedResearchClientApi,
    _validate_authenticated_epoch_metadata,
)
from locus.managed_client_ui import (
    ASSET_ROOT,
    MANAGED_CLIENT_API_VERSION,
    MANAGED_CLIENT_INSTANCE_PROFILE,
    MANAGED_CLIENT_UI_PROFILE,
    ManagedClientApi,
    ManagedClientApplication,
    ManagedClientError,
    _loopback_origin,
    browser_edge_bind_address,
)
from locus.paired_deployment_profiles import PAIRED_DEPLOYMENT_2_OF_3
from locus.recovery_package import (
    RECOVERY_PACKAGE_MEDIA_TYPE,
    create_recovery_package,
    decode_recovery_package,
)
from locus.recovery_suite_registry import RecoverySuiteSelection


def _fingerprint(private_key: bytes) -> str:
    public = (
        Ed25519PrivateKey.from_private_bytes(private_key)
        .public_key()
        .public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    )
    return hashlib.sha256(public).hexdigest()


class _FakeProtocol:
    def __init__(self) -> None:
        self.proof_key = Ed25519PrivateKey.generate()
        self.receipt = b"authenticated-receipt"
        self.bundle = b"encrypted-recovery-bundle"
        self.package = create_recovery_package(
            receipt_bytes=self.receipt, bundle_bytes=self.bundle
        )
        self.recovered_key = b"r" * 32
        self.enrolled_key: bytes | None = None
        self.selected: tuple[int, ...] | None = None
        self.recovery_request: dict[str, Any] | None = None
        self.fail_recovery = False

    def catalog(self) -> dict[str, object]:
        return {"policies": [], "profiles": [], "suites": []}

    def preview_policy(self, request: dict[str, Any]) -> dict[str, object]:
        return {
            "normalized_preview": {"count": len(request["recovery_input"])},
            "policy_id": request["policy_id"],
            "status": "input_validated",
        }

    def enroll(self, request: dict[str, Any]) -> EnrollmentResult:
        self.enrolled_key = bytes.fromhex(request["protected_key"]["hex"])
        return EnrollmentResult(
            operation_id=request["operation_id"],
            recovery_handle="integrated-recovery:test",
            backup_id="11" * 16,
            epoch=1,
            policy_id=str(request["policy_id"]),
            suite_id=str(request["suite_id"]),
            profile_id=YI_PROFILE_2_OF_3,
            threshold_k=2,
            threshold_n=3,
            public_fingerprint=_fingerprint(self.enrolled_key),
            receipt_bytes=self.receipt,
            completed_phases=("key_generation", "completion"),
        )

    def export_recovery_package(self, receipt: object) -> bytes:
        if not isinstance(receipt, str):
            raise ClientApiError("package_export_rejected")
        return self.package

    def authenticate_recovery_package(
        self, encoded: bytes
    ) -> AuthenticatedRecoveryPackage:
        decoded = decode_recovery_package(encoded)
        if not secrets.compare_digest(decoded.bundle_bytes, self.bundle):
            raise ClientApiError("package_import_rejected")
        return AuthenticatedRecoveryPackage(
            bootstrap=BootstrapResult(
                recovery_handle="integrated-recovery:test",
                backup_id="11" * 16,
                epoch=1,
                policy_id="LOCUS-location-person-set-v1",
                resolver_profile_id="LOCUS-deterministic-directory-v2",
                suite_id=YI_SUITE_ID,
                profile_id=YI_PROFILE_2_OF_3,
                threshold_k=2,
                threshold_n=3,
                authorization_quorum=4,
                public_fingerprint=_fingerprint(self.recovered_key),
                receipt_verified=True,
            ),
            deployment_profile_id=PAIRED_DEPLOYMENT_2_OF_3,
            receipt="YXV0aGVudGljYXRlZC1yZWNlaXB0",
            holder_ids=(1, 2, 3),
            package_sha256=hashlib.sha256(encoded).hexdigest(),
        )

    def recover(
        self,
        request: dict[str, Any],
        *,
        selected_holder_ids: tuple[int, ...],
    ) -> RecoveryResult:
        self.selected = selected_holder_ids
        self.recovery_request = request
        if self.fail_recovery:
            raise ClientApiError("recovery_rejected")
        return RecoveryResult(
            operation_id=request["operation_id"],
            recovery_handle="integrated-recovery:test",
            backup_id="11" * 16,
            epoch=1,
            suite_id="LOCUS-TPASS-YI-ZK-RISTRETTO255-v1",
            public_fingerprint=_fingerprint(self.recovered_key),
            protected_key=self.recovered_key,
            completed_phases=("authorization", "suite_recovery", "completion"),
        )


class ManagedClientApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.protocol = _FakeProtocol()
        self.destroyed: list[tuple[str, str, str]] = []

        def destroy(client_id: str, token: str, operation_id: str) -> dict[str, Any]:
            self.destroyed.append((client_id, token, operation_id))
            return {
                "client_id": client_id,
                "operation_id": operation_id,
                "self_destroy_status": "destroying",
                "status": "destroying",
            }

        self.api = ManagedClientApi(
            protocol=self.protocol,
            client_id="client-0123456789abcdef",
            lifecycle_token="a" * 64,
            destroy_callback=destroy,
        )

    @staticmethod
    def operation(name: str) -> dict[str, str]:
        return {"api_version": MANAGED_CLIENT_API_VERSION, "operation_id": name}

    def test_identity_binds_controller_id_profile_and_fresh_proof_key(self) -> None:
        status = self.api.client_status()
        expected = hashlib.sha256(
            encode(
                {
                    "client_id": status["client_id"],
                    "profile": MANAGED_CLIENT_INSTANCE_PROFILE,
                    "proof_key_thumbprint": status["proof_key_thumbprint"],
                }
            )
        ).hexdigest()
        self.assertEqual(status["client_identity"], expected)
        self.assertEqual(
            status["client_identity_profile"], MANAGED_CLIENT_INSTANCE_PROFILE
        )
        self.assertEqual(status["ui_profile"], MANAGED_CLIENT_UI_PROFILE)
        successor = ManagedClientApi(
            protocol=_FakeProtocol(),
            client_id="client-0123456789abcdef",
            lifecycle_token="c" * 64,
            destroy_callback=lambda client, _token, operation: {
                "client_id": client,
                "operation_id": operation,
                "status": "destroying",
            },
        )
        self.assertNotEqual(
            successor.client_status()["client_identity"], status["client_identity"]
        )

    def test_performance_observation_fails_closed_when_not_enabled(self) -> None:
        with (
            patch.dict("os.environ", {}, clear=True),
            self.assertRaises(ManagedClientError),
        ):
            self.api.performance_observation(
                {
                    "api_version": MANAGED_CLIENT_API_VERSION,
                    "instrumentation_id": (
                        "LOCUS-managed-performance-instrumentation-v1"
                    ),
                }
            )

    def test_successor_route_fails_closed_when_not_enabled(self) -> None:
        with (
            patch.dict("os.environ", {}, clear=True),
            self.assertRaises(ManagedClientError),
        ):
            self.api.create_successor(
                {
                    "api_version": MANAGED_CLIENT_API_VERSION,
                    "operation_id": "successor-disabled",
                    "recovery_input": [],
                    "rotate_protected_key": False,
                    "successor_deployment_profile_id": PAIRED_DEPLOYMENT_2_OF_3,
                    "successor_suite_id": YI_SUITE_ID,
                }
            )

    def test_performance_fixture_key_is_reproducible_and_scoped(self) -> None:
        environment = {
            "LOCUS_PERFORMANCE_EVIDENCE": "1",
            "LOCUS_PERFORMANCE_FIXTURE_ID": "topology:block-01",
        }
        with patch.dict("os.environ", environment, clear=True):
            first = self.api.generate_key(self.operation("fixture-1"))
            self.api.clear()
            second = self.api.generate_key(self.operation("fixture-2"))
        self.assertEqual(first["private_key"], second["private_key"])

    def test_enrollment_uses_current_volatile_key_and_exports_package(self) -> None:
        generated = self.api.generate_key(self.operation("generate-1"))
        generated_private_key = str(generated["private_key"])
        self.assertEqual(len(generated_private_key), 64)
        enrolled = self.api.enroll(
            {
                "api_version": MANAGED_CLIENT_API_VERSION,
                "deployment_profile_id": PAIRED_DEPLOYMENT_2_OF_3,
                "operation_id": "enroll-1",
                "policy_id": "LOCUS-location-person-set-v1",
                "recovery_input": [],
                "suite_id": "LOCUS-TPASS-YI-ZK-RISTRETTO255-v1",
            }
        )
        self.assertIsNotNone(self.protocol.enrolled_key)
        assert self.protocol.enrolled_key is not None
        self.assertEqual(self.protocol.enrolled_key.hex(), generated_private_key)
        self.assertNotIn("receipt", enrolled)
        self.assertEqual(enrolled["deployment_profile_id"], PAIRED_DEPLOYMENT_2_OF_3)
        self.assertEqual(
            enrolled["suite_profile_id"],
            YI_PROFILE_2_OF_3,
        )
        exported = self.api.exported_package(
            {
                "api_version": MANAGED_CLIENT_API_VERSION,
                "download_id": enrolled["download_id"],
            }
        )
        self.assertEqual(exported, self.protocol.package)

    def test_import_exact_k_recovery_and_atomic_key_replacement(self) -> None:
        generated = self.api.generate_key(self.operation("generate-before-recovery"))
        imported = self.api.import_package(self.protocol.package)
        self.assertEqual(imported["holder_ids"], [1, 2, 3])
        self.assertEqual(imported["deployment_profile_id"], PAIRED_DEPLOYMENT_2_OF_3)
        self.assertEqual(
            imported["suite_profile_id"],
            YI_PROFILE_2_OF_3,
        )
        with self.assertRaises(ManagedClientError):
            self.api.recover(
                {
                    "api_version": MANAGED_CLIENT_API_VERSION,
                    "operation_id": "recover-invalid",
                    "recovery_input": [],
                    "selected_holder_ids": [1, 2, 3],
                }
            )
        recovered = self.api.recover(
            {
                "api_version": MANAGED_CLIENT_API_VERSION,
                "operation_id": "recover-valid",
                "recovery_input": [],
                "selected_holder_ids": [1, 3],
            }
        )
        self.assertEqual(self.protocol.selected, (1, 3))
        self.assertEqual(
            recovered["previous_public_fingerprint"],
            generated["public_fingerprint"],
        )
        self.assertEqual(recovered["public_fingerprint"], _fingerprint(b"r" * 32))
        revealed = self.api.reveal_key({"api_version": MANAGED_CLIENT_API_VERSION})
        self.assertEqual(revealed["private_key"], (b"r" * 32).hex())

    def test_rejected_recovery_preserves_current_key(self) -> None:
        generated = self.api.generate_key(self.operation("generate-preserved"))
        self.api.import_package(self.protocol.package)
        self.protocol.fail_recovery = True
        with self.assertRaises(ClientApiError):
            self.api.recover(
                {
                    "api_version": MANAGED_CLIENT_API_VERSION,
                    "operation_id": "recover-fails",
                    "recovery_input": [],
                    "selected_holder_ids": [1, 2],
                }
            )
        revealed = self.api.reveal_key({"api_version": MANAGED_CLIENT_API_VERSION})
        self.assertEqual(revealed["private_key"], generated["private_key"])

    def test_failed_import_clears_prior_authenticated_package(self) -> None:
        self.api.import_package(self.protocol.package)
        with self.assertRaisesRegex(ManagedClientError, "package_import_rejected"):
            self.api.import_package(b"not-a-package")
        with self.assertRaisesRegex(ManagedClientError, "package_required"):
            self.api.recover(
                {
                    "api_version": MANAGED_CLIENT_API_VERSION,
                    "operation_id": "stale-import",
                    "recovery_input": [],
                    "selected_holder_ids": [1, 2],
                }
            )

    def test_self_destroy_clears_key_and_uses_exact_lifecycle_binding(self) -> None:
        self.api.generate_key(self.operation("generate-destroyed"))
        result = self.api.self_destroy(self.operation("destroy-1"))
        self.assertEqual(result["status"], "destroying")
        self.assertEqual(
            self.destroyed,
            [("client-0123456789abcdef", "a" * 64, "destroy-1")],
        )
        self.assertEqual(self.api.self_destroy(self.operation("destroy-1")), result)
        self.assertEqual(len(self.destroyed), 1)
        with self.assertRaisesRegex(ManagedClientError, "key_unavailable"):
            self.api.reveal_key({"api_version": MANAGED_CLIENT_API_VERSION})
        with self.assertRaisesRegex(ManagedClientError, "operation_conflict"):
            self.api.generate_key(self.operation("destroy-1"))

    def test_self_destroy_callback_failure_preserves_state_and_exact_retry_is_safe(
        self,
    ) -> None:
        calls: list[str] = []

        def destroy(client_id: str, _token: str, operation_id: str) -> dict[str, Any]:
            calls.append(operation_id)
            if len(calls) == 1:
                raise RuntimeError("injected controller response loss")
            return {
                "client_id": client_id,
                "operation_id": operation_id,
                "self_destroy_status": "destroying",
                "status": "destroying",
            }

        api = ManagedClientApi(
            protocol=_FakeProtocol(),
            client_id="client-1111111111111111",
            lifecycle_token="d" * 64,
            destroy_callback=destroy,
        )
        generated = api.generate_key(self.operation("generate-before-destroy"))
        request = self.operation("destroy-retry")
        with self.assertRaisesRegex(ManagedClientError, "self_destroy_rejected"):
            api.self_destroy(request)
        self.assertEqual(api.client_status()["self_destroy_status"], "retry_required")
        self.assertEqual(
            api.reveal_key({"api_version": MANAGED_CLIENT_API_VERSION})["private_key"],
            generated["private_key"],
        )
        accepted = api.self_destroy(request)
        self.assertEqual(accepted["status"], "destroying")
        self.assertEqual(calls, ["destroy-retry", "destroy-retry"])
        self.assertEqual(api.self_destroy(request), accepted)
        self.assertEqual(len(calls), 2)


class IntegratedClientExtensionTests(unittest.TestCase):
    def test_authenticated_epoch_metadata_cross_binds_backup_and_descriptor(
        self,
    ) -> None:
        selection = RecoverySuiteSelection(
            suite_id=YI_SUITE_ID,
            profile_id=YI_PROFILE_2_OF_3,
            threshold=ThresholdParameters(k=2, n=3),
            holder_ids=(1, 2, 3),
            authorizer_ids=(1, 2, 3, 4, 5),
            authorization_quorum=4,
        )
        descriptor = {
            "cue_policy": {"id": "policy", "resolver_profile": "resolver"},
            "recovery_suite": {
                "id": YI_SUITE_ID,
                "public_state_format": "public-state",
                "public_state_hex": "aa",
                "threshold": {"k": 2, "n": 3},
            },
        }
        backup = {
            "cue_policy": {"id": "policy", "resolver_profile": "resolver"},
            "recovery_suite": {
                "id": YI_SUITE_ID,
                "k": 2,
                "n": 3,
                "profile_id": YI_PROFILE_2_OF_3,
                "public_state": "aa",
                "public_state_format": "public-state",
            },
        }
        _validate_authenticated_epoch_metadata(descriptor, backup, selection)
        for field, changed in (
            ("profile_id", "wrong-profile"),
            ("public_state", "bb"),
            ("n", 5),
        ):
            invalid = json.loads(json.dumps(backup))
            invalid["recovery_suite"][field] = changed
            with self.subTest(field=field):
                with self.assertRaisesRegex(ClientApiError, "bootstrap_rejected"):
                    _validate_authenticated_epoch_metadata(
                        descriptor, invalid, selection
                    )

    def test_injected_proof_key_and_deployment_binding_are_instance_scoped(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            operator = Ed25519PrivateKey.generate()
            operator_public = operator.public_key().public_bytes(
                serialization.Encoding.Raw, serialization.PublicFormat.Raw
            )
            (root / "trust.json").write_text(
                json.dumps({"operator_public_key": operator_public.hex()}),
                encoding="utf-8",
            )
            injected = Ed25519PrivateKey.generate()
            client = IntegratedResearchClientApi(
                role_root=root,
                proof_key=injected,
                deployment_id="LOCUS-integrated-manager-deployment-v1",
            )
            self.assertIs(client.proof_key, injected)
            self.assertEqual(
                client.deployment_id, "LOCUS-integrated-manager-deployment-v1"
            )
            legacy_proof = Ed25519PrivateKey.generate()
            (root / "proof-key.bin").write_bytes(
                legacy_proof.private_bytes(
                    serialization.Encoding.Raw,
                    serialization.PrivateFormat.Raw,
                    serialization.NoEncryption(),
                )
            )
            legacy = IntegratedResearchClientApi(role_root=root)
            self.assertEqual(
                legacy.deployment_id, "LOCUS-integrated-reference-deployment-v1"
            )
            self.assertEqual(
                legacy.proof_key.public_key().public_bytes(
                    serialization.Encoding.Raw, serialization.PublicFormat.Raw
                ),
                legacy_proof.public_key().public_bytes(
                    serialization.Encoding.Raw, serialization.PublicFormat.Raw
                ),
            )
            with self.assertRaises(ValueError):
                IntegratedResearchClientApi(
                    role_root=root,
                    proof_key=injected,
                    deployment_id="LOCUS-unassigned-deployment-v1",
                )

    def test_exact_recovery_subset_accepts_only_sorted_unique_k_holders(self) -> None:
        selection = RecoverySuiteSelection(
            suite_id="suite",
            profile_id="profile",
            threshold=ThresholdParameters(k=2, n=3),
            holder_ids=(1, 2, 3),
            authorizer_ids=(1, 2, 3, 4, 5),
            authorization_quorum=4,
        )
        self.assertEqual(
            IntegratedResearchClientApi._exact_recovery_subset(selection, (1, 3)),
            [1, 3],
        )
        for rejected in ((1,), (1, 1), (3, 1), (1, 4), (1, 2, 3), (True, 2)):
            with self.subTest(rejected=rejected):
                with self.assertRaises(ClientApiError):
                    IntegratedResearchClientApi._exact_recovery_subset(
                        selection, rejected
                    )


class ManagedClientApplicationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.protocol = _FakeProtocol()
        self.api = ManagedClientApi(
            protocol=self.protocol,
            client_id="client-fedcba9876543210",
            lifecycle_token="b" * 64,
            destroy_callback=lambda client, _token, operation: {
                "client_id": client,
                "operation_id": operation,
                "status": "destroying",
            },
        )
        self.application = ManagedClientApplication(self.api)
        self.origin = "http://127.0.0.1:49152"

    def test_session_health_and_transient_key_routes_are_separated(self) -> None:
        health = self.application.dispatch("GET", "/healthz")
        self.assertEqual(json.loads(health.body), {"status": "ok"})
        session = self.application.dispatch("GET", "/api/v2/session")
        session_value = json.loads(session.body)
        self.assertEqual(session_value["status"], "ready")
        rejected = self.application.dispatch(
            "POST",
            "/api/v2/key/generate",
            json.dumps(self._operation("generate-no-csrf")).encode(),
            content_type="application/json",
            origin=self.origin,
            expected_origin=self.origin,
        )
        self.assertEqual(rejected.status, 400)
        wrong_origin = self.application.dispatch(
            "POST",
            "/api/v2/key/generate",
            json.dumps(self._operation("generate-wrong-origin")).encode(),
            content_type="application/json",
            csrf_token=session_value["csrf_token"],
            origin="http://attacker.example",
            expected_origin=self.origin,
        )
        self.assertEqual(
            json.loads(wrong_origin.body)["category"],
            "request_authentication_rejected",
        )
        generated = self.application.dispatch(
            "POST",
            "/api/v2/key/generate",
            json.dumps(self._operation("generate-valid")).encode(),
            content_type="application/json",
            csrf_token=session_value["csrf_token"],
            origin=self.origin,
            expected_origin=self.origin,
        )
        self.assertTrue(generated.transient_secret_path)
        self.assertIn("private_key", json.loads(generated.body))

    def _operation(self, name: str) -> dict[str, str]:
        return {"api_version": MANAGED_CLIENT_API_VERSION, "operation_id": name}

    def test_client_json_decoder_rejects_duplicates_constants_and_nonobjects(
        self,
    ) -> None:
        session = json.loads(self.application.dispatch("GET", "/api/v2/session").body)
        for body in (
            b'{"api_version":"LOCUS-client-api-v2","operation_id":"one",'
            b'"operation_id":"two"}',
            b'{"api_version":"LOCUS-client-api-v2","operation_id":NaN}',
            b"[]",
            b"\xff",
        ):
            with self.subTest(body=body):
                response = self.application.dispatch(
                    "POST",
                    "/api/v2/key/generate",
                    body,
                    content_type="application/json",
                    csrf_token=session["csrf_token"],
                    origin=self.origin,
                    expected_origin=self.origin,
                )
                self.assertEqual(response.status, 400)
                self.assertEqual(
                    json.loads(response.body)["category"], "input_rejected"
                )

    def test_loopback_host_validation_rejects_dns_rebinding_names(self) -> None:
        self.assertEqual(_loopback_origin("127.0.0.1:49152"), "http://127.0.0.1:49152")
        self.assertEqual(_loopback_origin("[::1]:49152"), "http://[::1]:49152")
        with self.assertRaises(ManagedClientError):
            _loopback_origin("attacker.example:49152")
        with self.assertRaises(ManagedClientError):
            _loopback_origin("172.18.0.4:8080")

    def test_bind_address_uses_validated_browser_gateway_and_rejects_loopback(
        self,
    ) -> None:
        with patch("locus.managed_client_ui.socket.socket") as constructor:
            probe = constructor.return_value.__enter__.return_value
            probe.getsockname.return_value = ("172.20.0.7", 43123)
            self.assertEqual(browser_edge_bind_address("172.20.0.1"), "172.20.0.7")
            probe.connect.assert_called_once_with(("172.20.0.1", 9))
        with patch("locus.managed_client_ui.socket.socket") as constructor:
            probe = constructor.return_value.__enter__.return_value
            probe.getsockname.return_value = ("127.0.0.1", 43123)
            with self.assertRaises(ManagedClientError):
                browser_edge_bind_address("172.20.0.1")
        with self.assertRaises(ManagedClientError):
            browser_edge_bind_address("127.0.0.1")

    def test_package_export_has_exact_binary_transport_contract(self) -> None:
        self.api.generate_key(self._operation("generate-package"))
        enrolled = self.api.enroll(
            {
                "api_version": MANAGED_CLIENT_API_VERSION,
                "deployment_profile_id": PAIRED_DEPLOYMENT_2_OF_3,
                "operation_id": "enroll-package",
                "policy_id": "LOCUS-location-person-set-v1",
                "recovery_input": [],
                "suite_id": "LOCUS-TPASS-YI-ZK-RISTRETTO255-v1",
            }
        )
        session = json.loads(self.application.dispatch("GET", "/api/v2/session").body)
        response = self.application.dispatch(
            "POST",
            "/api/v2/package/export",
            json.dumps(
                {
                    "api_version": MANAGED_CLIENT_API_VERSION,
                    "download_id": enrolled["download_id"],
                }
            ).encode(),
            content_type="application/json",
            csrf_token=session["csrf_token"],
            origin=self.origin,
            expected_origin=self.origin,
        )
        self.assertEqual(response.content_type, RECOVERY_PACKAGE_MEDIA_TYPE)
        self.assertIn("attachment", response.content_disposition or "")
        self.assertEqual(response.body, self.protocol.package)

    def test_ui_has_no_persistence_telemetry_or_inline_protocol_logic(self) -> None:
        source = "\n".join(
            path.read_text(encoding="utf-8")
            for path in sorted(ASSET_ROOT.iterdir())
            if path.is_file()
        )
        for prohibited in (
            "localStorage",
            "sessionStorage",
            "indexedDB",
            "sendBeacon",
            "WebSocket",
            "console.",
            "innerHTML",
            "HKDF",
            "AES-GCM",
        ):
            with self.subTest(prohibited=prohibited):
                self.assertNotIn(prohibited, source)
        self.assertIn("window.confirm", source)

    def test_ui_locks_enrollment_until_backend_reports_a_key(self) -> None:
        html = (ASSET_ROOT / "index.html").read_text(encoding="utf-8")
        script = (ASSET_ROOT / "client.js").read_text(encoding="utf-8")

        self.assertIn('id="enrollment-lock-note"', html)
        self.assertIn("Recovery does not require a private key", html)
        self.assertIn("Local attempt records are diagnostic only", html)
        self.assertIn("no global or rollback-resistant attempt limit", html)
        self.assertIn("function updateEnrollmentLock(keyLoaded)", script)
        self.assertIn('byId("enrollment-form")', script)
        self.assertIn("updateEnrollmentLock(state.keyLoaded)", script)
        self.assertGreaterEqual(script.count("updateEnrollmentLock(true)"), 2)
        self.assertNotIn('byId("recovery-form").setAttribute("aria-disabled"', script)


if __name__ == "__main__":
    unittest.main()
