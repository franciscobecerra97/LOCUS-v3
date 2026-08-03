from __future__ import annotations

import json
import threading
import unittest
import urllib.request
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from locus.appss_formats import YI_SUITE_ID
from locus.client_api import CLIENT_API_VERSION, LocalResearchClientApi
from locus.paired_deployment_profiles import PAIRED_DEPLOYMENT_2_OF_3
from locus.research_ui import (
    ASSET_ROOT,
    LOCAL_RESEARCH_UI_PROFILE,
    SECURITY_HEADERS,
    ResearchUiApplication,
    ResearchUiServer,
)

NOW = 2_000_000_000
SYNTHETIC_KEY = bytes(range(32))
ROOT = Path(__file__).resolve().parents[2]


def private_key(value: int) -> Ed25519PrivateKey:
    return Ed25519PrivateKey.from_private_bytes(bytes([value]) * 32)


def client() -> LocalResearchClientApi:
    return LocalResearchClientApi(
        clock=lambda: NOW,
        operator_signer=private_key(9),
        admission_signer=private_key(10),
        party_signers={party_id: private_key(party_id) for party_id in range(1, 6)},
    )


def cues() -> list[str]:
    return ["ada@example.com", "grace@example.net", "linus@example.org"]


def request_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def decoded(response_body: bytes) -> dict[str, object]:
    value = json.loads(response_body)
    if not isinstance(value, dict):
        raise AssertionError("expected object response")
    return value


class ResearchUiTests(unittest.TestCase):
    def test_assets_are_local_accessible_and_have_no_persistence_or_telemetry(
        self,
    ) -> None:
        html = (ASSET_ROOT / "index.html").read_text(encoding="utf-8")
        css = (ASSET_ROOT / "styles.css").read_text(encoding="utf-8")
        script = (ASSET_ROOT / "app.js").read_text(encoding="utf-8")
        self.assertIn('<main id="workspace"', html)
        self.assertIn('aria-live="polite"', html)
        self.assertIn('autocomplete="new-password"', html)
        self.assertIn("@media print", css)
        self.assertIn("[hidden] { display: none !important; }", css)
        self.assertIn("grid-template-columns: repeat(3, minmax(0, 1fr))", css)
        self.assertIn('id="enrollment-placement"', html)
        self.assertIn('document.addEventListener("copy"', script)
        self.assertIn("function renderRolePlacement", script)
        for prohibited in (
            "localStorage",
            "sessionStorage",
            "indexedDB",
            "navigator.clipboard",
            "document.cookie",
            "console.",
            "innerHTML",
            "eval(",
            "http://",
            "https://",
        ):
            with self.subTest(prohibited=prohibited):
                self.assertNotIn(prohibited, html + css + script)

    def test_application_routes_full_enrollment_recovery_and_inspection(self) -> None:
        application = ResearchUiApplication(client())
        catalog = application.dispatch("GET", "/api/v1/catalog")
        self.assertEqual(catalog.status, 200)
        self.assertEqual(decoded(catalog.body)["status"], "ready")

        preview = application.dispatch(
            "POST",
            "/api/v1/preview-policy",
            request_bytes(
                {
                    "api_version": CLIENT_API_VERSION,
                    "policy_id": "LOCUS-canonical-email-set-v1",
                    "recovery_input": cues(),
                }
            ),
            content_type="application/json",
        )
        self.assertTrue(preview.transient_secret_path)
        self.assertEqual(decoded(preview.body)["status"], "input_validated")

        enrollment = application.dispatch(
            "POST",
            "/api/v1/enroll",
            request_bytes(
                {
                    "api_version": CLIENT_API_VERSION,
                    "deployment_profile_id": PAIRED_DEPLOYMENT_2_OF_3,
                    "operation_id": "ui-enroll-test",
                    "policy_id": "LOCUS-canonical-email-set-v1",
                    "protected_key": {
                        "hex": SYNTHETIC_KEY.hex(),
                        "mode": "import-synthetic",
                    },
                    "recovery_input": cues(),
                    "suite_id": YI_SUITE_ID,
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(enrollment.status, 200)
        enrollment_value = decoded(enrollment.body)
        receipt = enrollment_value["receipt"]
        self.assertIsInstance(receipt, str)
        self.assertNotIn(SYNTHETIC_KEY.hex(), enrollment.body.decode("utf-8"))

        bootstrap = application.dispatch(
            "POST",
            "/api/v1/bootstrap",
            request_bytes({"receipt": receipt}),
            content_type="application/json",
        )
        self.assertEqual(decoded(bootstrap.body)["status"], "bootstrap_authenticated")
        recovery = application.dispatch(
            "POST",
            "/api/v1/recover",
            request_bytes(
                {
                    "api_version": CLIENT_API_VERSION,
                    "operation_id": "ui-recover-test",
                    "receipt": receipt,
                    "recovery_input": cues(),
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(decoded(recovery.body)["status"], "recovered")
        self.assertNotIn(SYNTHETIC_KEY.hex(), recovery.body.decode("utf-8"))
        inspection = application.dispatch(
            "POST",
            "/api/v1/inspect",
            request_bytes({"receipt": receipt}),
            content_type="application/json",
        )
        self.assertEqual(decoded(inspection.body)["status"], "active")
        for marker in (*cues(), SYNTHETIC_KEY.hex()):
            self.assertNotIn(marker, inspection.body.decode("utf-8"))

    def test_route_content_type_duplicate_and_query_fail_closed(self) -> None:
        application = ResearchUiApplication(client())
        wrong_type = application.dispatch(
            "POST", "/api/v1/bootstrap", b"{}", content_type="text/plain"
        )
        self.assertEqual(wrong_type.status, 400)
        duplicate = application.dispatch(
            "POST",
            "/api/v1/bootstrap",
            b'{"receipt":"a","receipt":"b"}',
            content_type="application/json",
        )
        self.assertEqual(duplicate.status, 400)
        query = application.dispatch("GET", "/?receipt=forbidden")
        self.assertEqual(query.status, 404)
        missing = application.dispatch("GET", "/unknown")
        self.assertEqual(missing.status, 404)

    def test_live_loopback_server_applies_security_headers_and_stays_quiet(
        self,
    ) -> None:
        server = ResearchUiServer(("127.0.0.1", 0), ResearchUiApplication(client()))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with urllib.request.urlopen(
                f"http://127.0.0.1:{server.server_port}/", timeout=5
            ) as response:
                body = response.read()
                self.assertIn(b"LOCUS", body)
                self.assertEqual(
                    response.headers["Cache-Control"], SECURITY_HEADERS["Cache-Control"]
                )
                self.assertEqual(response.headers["X-Frame-Options"], "DENY")
                self.assertEqual(
                    response.headers["Clear-Site-Data"],
                    '"cache", "cookies", "storage"',
                )
            request = urllib.request.Request(
                f"http://127.0.0.1:{server.server_port}/api/v1/catalog",
                method="GET",
            )
            with urllib.request.urlopen(request, timeout=5) as response:
                self.assertEqual(decoded(response.read())["status"], "ready")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    def test_ui_profile_is_registered_without_changing_manuscript(self) -> None:
        registry = json.loads(
            (ROOT / "docs" / "version-registry-v1.json").read_text(encoding="utf-8")
        )
        self.assertIn(LOCAL_RESEARCH_UI_PROFILE, registry["protected_identifiers"])


if __name__ == "__main__":
    unittest.main()
