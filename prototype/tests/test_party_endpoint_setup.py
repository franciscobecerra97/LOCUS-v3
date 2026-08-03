from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from cryptography import x509
from locus.deployment import DeploymentError, provision
from locus.party_endpoint_setup import (
    PARTY_ENDPOINT_SETUP_VERSION,
    SAME_HOST_CONTAINERS,
    SEPARATE_HOSTS_SINGLE_ADMIN,
    PartyEndpointSetupError,
    endpoint_setup_public_value,
    load_party_endpoint_setup,
    validate_party_endpoint_setup,
)

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "deploy" / "fixtures" / "cues.json"
LOCAL_SETUP = ROOT / "deploy" / "party-endpoints.json"
FIVE_HOST_SETUP = ROOT / "deploy" / "party-endpoints.five-host.example.json"


class PartyEndpointSetupTests(unittest.TestCase):
    def test_checked_in_local_and_five_host_setups_are_strict(self) -> None:
        local = load_party_endpoint_setup(LOCAL_SETUP)
        self.assertEqual(local.version, PARTY_ENDPOINT_SETUP_VERSION)
        self.assertEqual(local.deployment_tier, SAME_HOST_CONTAINERS)
        self.assertEqual(
            [(party.host, party.port) for party in local.parties],
            [(f"party{party_id}", 8443) for party_id in range(1, 6)],
        )
        separate = load_party_endpoint_setup(FIVE_HOST_SETUP)
        self.assertEqual(separate.deployment_tier, SEPARATE_HOSTS_SINGLE_ADMIN)
        self.assertEqual(len({party.host for party in separate.parties}), 5)

    def test_invalid_tier_order_host_and_extra_fields_fail_closed(self) -> None:
        valid = endpoint_setup_public_value(load_party_endpoint_setup(LOCAL_SETUP))
        cases: list[dict[str, object]] = []
        wrong_tier = copy.deepcopy(valid)
        wrong_tier["deployment_tier"] = "independent-admin-hosts"
        cases.append(wrong_tier)
        wrong_order = copy.deepcopy(valid)
        wrong_order["parties"][0]["party_id"] = 2  # type: ignore[index]
        cases.append(wrong_order)
        uppercase = copy.deepcopy(valid)
        uppercase["parties"][0]["host"] = "Party1"  # type: ignore[index]
        cases.append(uppercase)
        extra = copy.deepcopy(valid)
        extra["fallback_host"] = "party1"
        cases.append(extra)
        for value in cases:
            with self.subTest(value=value):
                with self.assertRaises(PartyEndpointSetupError):
                    validate_party_endpoint_setup(value)

        separate = endpoint_setup_public_value(
            load_party_endpoint_setup(FIVE_HOST_SETUP)
        )
        separate["parties"][1]["host"] = "10.10.0.11"  # type: ignore[index]
        with self.assertRaisesRegex(PartyEndpointSetupError, "must be distinct"):
            validate_party_endpoint_setup(separate)

    def test_custom_hosts_bind_client_peers_listeners_and_certificates(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            party_roots = [root / f"party{party_id}" for party_id in range(1, 6)]
            client_root = root / "client"
            self.assertEqual(
                provision(
                    party_roots=party_roots,
                    client_root=client_root,
                    fixture_path=FIXTURE,
                    endpoint_setup_path=FIVE_HOST_SETUP,
                ),
                "created",
            )
            deployment = json.loads(
                (client_root / "deployment.json").read_text(encoding="ascii")
            )
            self.assertEqual(
                [endpoint["host"] for endpoint in deployment["parties"]],
                [f"10.10.0.{number}" for number in range(11, 16)],
            )
            for party_id, party_root in enumerate(party_roots, start=1):
                service = json.loads(
                    (party_root / "service.json").read_text(encoding="ascii")
                )
                self.assertEqual(service["listen_port"], 8443)
                if service["native_party"] is not None:
                    self.assertTrue(
                        all(
                            peer["host"].startswith("10.10.0.")
                            for peer in service["native_party"]["peers"]
                        )
                    )
                certificate = x509.load_pem_x509_certificate(
                    (party_root / "server.pem").read_bytes()
                )
                alternatives = certificate.extensions.get_extension_for_class(
                    x509.SubjectAlternativeName
                ).value
                self.assertIn(
                    f"10.10.0.{10 + party_id}",
                    [
                        str(address)
                        for address in alternatives.get_values_for_type(x509.IPAddress)
                    ],
                )

            self.assertEqual(
                provision(
                    party_roots=party_roots,
                    client_root=client_root,
                    fixture_path=FIXTURE,
                    endpoint_setup_path=FIVE_HOST_SETUP,
                ),
                "existing",
            )
            changed = endpoint_setup_public_value(
                load_party_endpoint_setup(FIVE_HOST_SETUP)
            )
            changed["parties"][4]["host"] = "10.10.0.99"  # type: ignore[index]
            changed_path = root / "changed.json"
            changed_path.write_text(json.dumps(changed), encoding="ascii")
            with self.assertRaisesRegex(DeploymentError, "different endpoint setup"):
                provision(
                    party_roots=party_roots,
                    client_root=client_root,
                    fixture_path=FIXTURE,
                    endpoint_setup_path=changed_path,
                )


if __name__ == "__main__":
    unittest.main()
