from __future__ import annotations

import copy
import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.x509.oid import NameOID

from locus.codec import encode
from locus.integrated_bootstrap import (
    IntegratedBootstrapError,
    bootstrap_integrated_roles,
)
from locus.integrated_services import IntegratedServiceError, ResolverRole
from locus.integrated_state_audit import (
    audit_managed_client_template_root,
    audit_role_root,
)
from locus.managed_manifest import (
    CLEAN_CLIENT_PROFILE,
    CONTROLLER_API_VERSION,
    EXPECTED_BOOTSTRAP_ROLES,
    EXPECTED_NETWORKS,
    EXPECTED_STATIC_SERVICES,
    MANAGED_CLIENT_API_VERSION,
    MANAGED_CLIENT_INSTANCE_PROFILE,
    MANAGED_CLIENT_UI_PROFILE,
    MANAGED_CONFIG_VERSION,
    MANAGED_DEPLOYMENT_ID,
    MANAGER_API_VERSION,
    MANAGER_UI_PROFILE,
    RECOVERY_PACKAGE_VERSION,
    SECURITY_MATRIX_VERSION,
    ManagedManifestError,
    decode_managed_manifest,
    load_managed_manifest,
    validate_managed_manifest,
)

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "deploy" / "managed-manifest.json"
SCHEMA = ROOT / "docs" / "schemas" / "integrated-manager-config-v1.schema.json"
COMPOSE = ROOT / "deploy" / "compose.managed.yaml"


class ManagedManifestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.value = load_managed_manifest(MANIFEST)

    def test_canonical_manifest_binds_managed_system_without_a_client(self) -> None:
        self.assertEqual(self.value["version"], MANAGED_CONFIG_VERSION)
        self.assertEqual(self.value["deployment_id"], MANAGED_DEPLOYMENT_ID)
        self.assertEqual(len(self.value["arms"]), 4)
        self.assertEqual(len(self.value["services"]), 13)
        self.assertEqual(
            self.value["control_plane"],
            {
                "controller_api": CONTROLLER_API_VERSION,
                "controller_profile": "LOCUS-local-container-controller-v1",
                "manager_api": MANAGER_API_VERSION,
                "manager_ui_profile": MANAGER_UI_PROFILE,
            },
        )
        self.assertEqual(
            self.value["client_template"],
            {
                "api_version": MANAGED_CLIENT_API_VERSION,
                "clean_client_profile": CLEAN_CLIENT_PROFILE,
                "identity": "spiffe://locus.invalid/integrated/managed-client",
                "instance_profile": MANAGED_CLIENT_INSTANCE_PROFILE,
                "networks": [
                    "admission",
                    "browser-edge",
                    "client-lifecycle",
                    "control",
                    "recovery",
                    "resolver",
                    "storage",
                ],
                "package_format": RECOVERY_PACKAGE_VERSION,
                "ui_profile": MANAGED_CLIENT_UI_PROFILE,
            },
        )
        self.assertEqual(self.value["security_matrix"], SECURITY_MATRIX_VERSION)
        self.assertEqual(
            tuple(item["name"] for item in self.value["services"]),
            EXPECTED_STATIC_SERVICES,
        )
        self.assertNotIn("managed-client", EXPECTED_STATIC_SERVICES)
        self.assertNotIn("ui-client-a", encode(self.value).decode("ascii"))
        self.assertNotIn("ui-client-b", encode(self.value).decode("ascii"))
        self.assertEqual(encode(self.value) + b"\n", MANIFEST.read_bytes())

    def test_control_networks_are_separate_and_client_membership_is_exact(self) -> None:
        self.assertEqual(tuple(self.value["networks"]), EXPECTED_NETWORKS)
        services = {item["name"]: item for item in self.value["services"]}
        self.assertEqual(
            services["manager-ui"]["networks"], ["management", "manager-edge"]
        )
        self.assertEqual(
            services["manager-controller"]["networks"],
            ["client-lifecycle", "management"],
        )
        self.assertEqual(
            self.value["client_template"]["networks"],
            [
                "admission",
                "browser-edge",
                "client-lifecycle",
                "control",
                "recovery",
                "resolver",
                "storage",
            ],
        )
        self.assertNotIn("management", self.value["client_template"]["networks"])

    def test_unknown_duplicate_noncanonical_and_oversize_values_fail(self) -> None:
        with self.assertRaises(ManagedManifestError):
            decode_managed_manifest(b'{"version":"x","version":"y"}')
        changed = copy.deepcopy(self.value)
        changed["unknown"] = True
        with self.assertRaises(ManagedManifestError):
            validate_managed_manifest(changed)
        with self.assertRaises(ManagedManifestError):
            decode_managed_manifest(json.dumps(self.value).encode())
        with self.assertRaises(ManagedManifestError):
            decode_managed_manifest(b" " * (128 * 1024 + 1))

    def test_role_substitution_and_secret_bearing_metadata_fail(self) -> None:
        changed = copy.deepcopy(self.value)
        changed["services"][2]["networks"] = ["management"]
        with self.assertRaises(ManagedManifestError):
            validate_managed_manifest(changed)
        changed = copy.deepcopy(self.value)
        changed["client_template"]["networks"].append("management")
        with self.assertRaises(ManagedManifestError):
            validate_managed_manifest(changed)
        changed = copy.deepcopy(self.value)
        changed["client_template"]["package_format"] = "LOCUS-unknown-package-v1"
        with self.assertRaises(ManagedManifestError):
            validate_managed_manifest(changed)
        changed = copy.deepcopy(self.value)
        changed["control_plane"]["manager_api"] = "LOCUS-manager-api-v0"
        with self.assertRaises(ManagedManifestError):
            validate_managed_manifest(changed)
        changed = copy.deepcopy(self.value)
        changed["private_key"] = "00"
        with self.assertRaises(ManagedManifestError):
            validate_managed_manifest(changed)

    def test_schema_and_compose_bind_new_identifiers_and_socket_scope(self) -> None:
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        self.assertEqual(
            schema["properties"]["version"]["const"], MANAGED_CONFIG_VERSION
        )
        self.assertEqual(
            schema["properties"]["deployment_id"]["const"],
            MANAGED_DEPLOYMENT_ID,
        )
        self.assertEqual(
            schema["properties"]["security_matrix"]["const"],
            SECURITY_MATRIX_VERSION,
        )
        self.assertEqual(
            schema["properties"]["control_plane"]["properties"]["manager_api"]["const"],
            MANAGER_API_VERSION,
        )
        self.assertEqual(
            schema["properties"]["client_template"]["properties"]["package_format"][
                "const"
            ],
            RECOVERY_PACKAGE_VERSION,
        )
        compose = COMPOSE.read_text(encoding="utf-8")
        self.assertEqual(compose.count("source: /var/run/docker.sock"), 1)
        self.assertEqual(compose.count("target: /var/run/docker.sock"), 1)
        self.assertEqual(compose.count("cap_add: [CHOWN, DAC_READ_SEARCH]"), 1)
        self.assertNotIn("ui-client-a:", compose)
        self.assertNotIn("ui-client-b:", compose)
        self.assertIn("manager-controller:", compose)
        self.assertIn("manager-ui:", compose)


class ManagedBootstrapTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "roles"
        bootstrap_integrated_roles(root=self.root, manifest_path=MANIFEST)

    def test_managed_bootstrap_creates_template_and_control_roles(self) -> None:
        self.assertEqual(
            {item.name for item in self.root.iterdir()},
            set(EXPECTED_BOOTSTRAP_ROLES),
        )
        serials = set()
        for role in EXPECTED_BOOTSTRAP_ROLES:
            role_root = self.root / role
            self.assertTrue((role_root / "ca.pem").is_file())
            if role != "bootstrap":
                certificate = x509.load_pem_x509_certificate(
                    (role_root / "tls-cert.pem").read_bytes()
                )
                self.assertGreater(
                    certificate.not_valid_after_utc - dt.datetime.now(dt.UTC),
                    dt.timedelta(days=364),
                )
                serials.add(certificate.serial_number)
        self.assertEqual(len(serials), len(EXPECTED_BOOTSTRAP_ROLES) - 1)
        self.assertFalse((self.root / "managed-client" / "proof-key.bin").exists())
        self.assertEqual(
            (self.root / "manager-controller" / "lifecycle-secret.bin").stat().st_size,
            32,
        )
        audit_managed_client_template_root(self.root / "managed-client")
        self.assertEqual(
            audit_role_root(self.root / "manager-controller", "manager-controller"),
            (
                5,
                sum(
                    path.stat().st_size
                    for path in (self.root / "manager-controller").iterdir()
                    if path.is_file()
                ),
            ),
        )
        manager_ui = self.root / "manager-ui"
        self.assertEqual(
            audit_role_root(manager_ui, "manager-ui"),
            (
                4,
                sum(
                    path.stat().st_size
                    for path in manager_ui.iterdir()
                    if path.is_file()
                ),
            ),
        )

    def test_existing_template_is_exact_and_client_peer_is_accepted(self) -> None:
        bootstrap_integrated_roles(
            root=self.root, manifest_path=MANIFEST, allow_existing=True
        )
        resolver = ResolverRole()
        self.assertEqual(resolver("/v1/count", {}, "managed-client")[1]["contacts"], 0)
        with self.assertRaises(IntegratedServiceError):
            resolver("/v1/count", {}, "manager-ui")
        (self.root / "managed-client" / "unexpected.sqlite3").write_bytes(b"state")
        with self.assertRaises(IntegratedBootstrapError):
            bootstrap_integrated_roles(
                root=self.root, manifest_path=MANIFEST, allow_existing=True
            )

    def test_existing_expired_trust_domain_fails_closed(self) -> None:
        now = dt.datetime.now(dt.UTC)
        key = Ed25519PrivateKey.generate()
        name = x509.Name(
            [x509.NameAttribute(NameOID.COMMON_NAME, "expired managed test CA")]
        )
        expired = (
            x509.CertificateBuilder()
            .subject_name(name)
            .issuer_name(name)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - dt.timedelta(days=2))
            .not_valid_after(now - dt.timedelta(days=1))
            .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
            .sign(key, algorithm=None)
            .public_bytes(serialization.Encoding.PEM)
        )
        for role in EXPECTED_BOOTSTRAP_ROLES:
            (self.root / role / "ca.pem").write_bytes(expired)
        with self.assertRaisesRegex(
            IntegratedBootstrapError, "invalid or expired bootstrap CA"
        ):
            bootstrap_integrated_roles(
                root=self.root, manifest_path=MANIFEST, allow_existing=True
            )


if __name__ == "__main__":
    unittest.main()
