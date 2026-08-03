from __future__ import annotations

import copy
import unittest
from typing import cast

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from locus.appss_formats import APPSS_SUITE_ID, YI_SUITE_ID
from locus.client_api import (
    CLIENT_API_VERSION,
    ClientApiError,
    LocalResearchClientApi,
    public_failure,
)
from locus.paired_deployment_profiles import (
    PAIRED_DEPLOYMENT_2_OF_3,
    PAIRED_DEPLOYMENT_3_OF_5,
)
from locus.redaction import validate_public_output

NOW = 2_000_000_000
SYNTHETIC_KEY = bytes(range(32))


def private_key(value: int) -> Ed25519PrivateKey:
    return Ed25519PrivateKey.from_private_bytes(bytes([value]) * 32)


def api() -> LocalResearchClientApi:
    return LocalResearchClientApi(
        clock=lambda: NOW,
        operator_signer=private_key(9),
        admission_signer=private_key(10),
        party_signers={party_id: private_key(party_id) for party_id in range(1, 6)},
    )


def email_input() -> list[str]:
    return ["Ada@Example.COM", "grace@example.net", "linus@example.org"]


def enrollment_request(
    *,
    operation_id: str,
    suite_id: str,
    deployment_profile_id: str,
) -> dict[str, object]:
    return {
        "api_version": CLIENT_API_VERSION,
        "deployment_profile_id": deployment_profile_id,
        "operation_id": operation_id,
        "policy_id": "LOCUS-canonical-email-set-v1",
        "protected_key": {
            "hex": SYNTHETIC_KEY.hex(),
            "mode": "import-synthetic",
        },
        "recovery_input": email_input(),
        "suite_id": suite_id,
    }


class ClientApiTests(unittest.TestCase):
    def test_catalog_and_all_policy_previews_use_registered_canonicalizers(
        self,
    ) -> None:
        client = api()
        catalog = client.catalog()
        self.assertEqual(catalog["api_version"], CLIENT_API_VERSION)
        self.assertEqual(len(cast(list[object], catalog["policies"])), 4)
        self.assertEqual(len(cast(list[object], catalog["profiles"])), 2)
        validate_public_output(catalog)

        samples: dict[str, object] = {
            "LOCUS-canonical-email-set-v1": email_input(),
            "LOCUS-canonical-phone-set-v1": [
                "+352621000001",
                "+352621000002",
                "+352621000003",
            ],
            "LOCUS-quantized-coordinate-set-v1": [
                {"latitude": "49.61160001", "longitude": "6.13190001"},
                {"latitude": "48.8566", "longitude": "2.3522"},
                {"latitude": "51.5074", "longitude": "-0.1278"},
            ],
            "LOCUS-location-person-set-v1": [
                {
                    "location": {"latitude": "49.6116", "longitude": "6.1319"},
                    "person": {"type": "email", "value": "Ada@Example.COM"},
                },
                {
                    "location": {"latitude": "48.8566", "longitude": "2.3522"},
                    "person": {"type": "phone", "value": "+352621000002"},
                },
                {
                    "location": {"latitude": "51.5074", "longitude": "-0.1278"},
                    "person": {"type": "email", "value": "linus@example.org"},
                },
            ],
        }
        for policy_id, recovery_input in samples.items():
            with self.subTest(policy_id=policy_id):
                preview = client.preview_policy(
                    {
                        "api_version": CLIENT_API_VERSION,
                        "policy_id": policy_id,
                        "recovery_input": recovery_input,
                    }
                )
                self.assertEqual(preview["status"], "input_validated")
                self.assertEqual(preview["policy_id"], policy_id)

    def test_all_suite_topology_arms_enroll_bootstrap_and_recover_exact_key(
        self,
    ) -> None:
        client = api()
        combinations = (
            (YI_SUITE_ID, PAIRED_DEPLOYMENT_2_OF_3),
            (APPSS_SUITE_ID, PAIRED_DEPLOYMENT_2_OF_3),
            (YI_SUITE_ID, PAIRED_DEPLOYMENT_3_OF_5),
            (APPSS_SUITE_ID, PAIRED_DEPLOYMENT_3_OF_5),
        )
        for index, (suite_id, deployment_profile_id) in enumerate(combinations):
            with self.subTest(suite_id=suite_id, profile=deployment_profile_id):
                enrolled = client.enroll(
                    enrollment_request(
                        operation_id=f"enroll-{index}",
                        suite_id=suite_id,
                        deployment_profile_id=deployment_profile_id,
                    )
                )
                public_enrollment = enrolled.public_value()
                self.assertEqual(public_enrollment["status"], "enrolled")
                self.assertNotIn(SYNTHETIC_KEY.hex(), repr(enrolled))
                bootstrap = client.bootstrap(public_enrollment["receipt"])
                self.assertTrue(bootstrap.receipt_verified)
                self.assertEqual(bootstrap.suite_id, suite_id)
                recovered = client.recover(
                    {
                        "api_version": CLIENT_API_VERSION,
                        "operation_id": f"recover-{index}",
                        "receipt": public_enrollment["receipt"],
                        "recovery_input": email_input(),
                    }
                )
                self.assertEqual(recovered.protected_key, SYNTHETIC_KEY)
                self.assertEqual(recovered.suite_id, suite_id)
                self.assertEqual(recovered.public_value()["status"], "recovered")
                self.assertEqual(len(recovered.completed_phases), 11)

    def test_recovery_has_no_suite_override_and_normalizes_secret_failure(self) -> None:
        client = api()
        enrolled = client.enroll(
            enrollment_request(
                operation_id="enroll-one",
                suite_id=YI_SUITE_ID,
                deployment_profile_id=PAIRED_DEPLOYMENT_2_OF_3,
            )
        )
        request: dict[str, object] = {
            "api_version": CLIENT_API_VERSION,
            "operation_id": "recover-one",
            "receipt": enrolled.public_value()["receipt"],
            "recovery_input": [
                "wrong1@example.com",
                "wrong2@example.com",
                "wrong3@example.com",
            ],
        }
        with self.assertRaisesRegex(ClientApiError, "recovery_rejected"):
            client.recover(request)
        changed = copy.deepcopy(request)
        changed["operation_id"] = "recover-two"
        changed["suite_id"] = APPSS_SUITE_ID
        with self.assertRaisesRegex(ClientApiError, "recovery_rejected"):
            client.recover(changed)
        failure = public_failure(ClientApiError("recovery_rejected"))
        self.assertEqual(
            failure,
            {
                "api_version": CLIENT_API_VERSION,
                "category": "recovery_rejected",
                "status": "rejected",
            },
        )

    def test_explicit_cross_suite_successor_preserves_key_and_retires_predecessor(
        self,
    ) -> None:
        client = api()
        predecessor = client.enroll(
            enrollment_request(
                operation_id="enroll-predecessor",
                suite_id=YI_SUITE_ID,
                deployment_profile_id=PAIRED_DEPLOYMENT_2_OF_3,
            )
        )
        predecessor_receipt = predecessor.public_value()["receipt"]
        successor = client.create_successor(
            {
                "api_version": CLIENT_API_VERSION,
                "operation_id": "enroll-successor",
                "receipt": predecessor_receipt,
                "recovery_input": email_input(),
                "rotate_protected_key": False,
                "successor_deployment_profile_id": PAIRED_DEPLOYMENT_3_OF_5,
                "successor_suite_id": APPSS_SUITE_ID,
            }
        )
        self.assertEqual(successor.predecessor_epoch, 1)
        self.assertEqual(successor.enrollment.epoch, 2)
        self.assertFalse(successor.protected_key_rotated)
        self.assertEqual(
            successor.enrollment.public_fingerprint,
            predecessor.public_fingerprint,
        )
        recovered = client.recover(
            {
                "api_version": CLIENT_API_VERSION,
                "operation_id": "recover-successor",
                "receipt": successor.enrollment.public_value()["receipt"],
                "recovery_input": email_input(),
            }
        )
        self.assertEqual(recovered.protected_key, SYNTHETIC_KEY)
        with self.assertRaises(ClientApiError):
            client.recover(
                {
                    "api_version": CLIENT_API_VERSION,
                    "operation_id": "recover-retired",
                    "receipt": predecessor_receipt,
                    "recovery_input": email_input(),
                }
            )

    def test_inspector_is_aggregate_public_and_request_retries_fail_closed(
        self,
    ) -> None:
        client = api()
        request = enrollment_request(
            operation_id="enroll-inspect",
            suite_id=APPSS_SUITE_ID,
            deployment_profile_id=PAIRED_DEPLOYMENT_2_OF_3,
        )
        enrolled = client.enroll(request)
        with self.assertRaisesRegex(ClientApiError, "operation_conflict"):
            client.enroll(request)
        inspection = client.inspect(enrolled.public_value()["receipt"])
        self.assertEqual(inspection["status"], "active")
        self.assertEqual(len(cast(list[object], inspection["role_placement"])), 5)
        validate_public_output(inspection)
        encoded = repr(inspection)
        for marker in (*email_input(), SYNTHETIC_KEY.hex()):
            self.assertNotIn(marker, encoded)


if __name__ == "__main__":
    unittest.main()
