"""Strict public contract for the managed integrated deployment."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast
from urllib.parse import urlsplit

from .appss_formats import APPSS_SUITE_ID, YI_SUITE_ID
from .codec import encode
from .cue_policy_registry import DEFAULT_CUE_POLICY_REGISTRY

MANAGED_DEPLOYMENT_ID = "LOCUS-integrated-manager-deployment-v1"
MANAGED_CONFIG_VERSION = "LOCUS-integrated-manager-config-v1"
MANAGER_API_VERSION = "LOCUS-manager-api-v1"
MANAGER_UI_PROFILE = "LOCUS-local-manager-ui-v1"
CONTROLLER_API_VERSION = "LOCUS-container-controller-api-v1"
CONTROLLER_PROFILE = "LOCUS-local-container-controller-v1"
MANAGED_CLIENT_API_VERSION = "LOCUS-client-api-v2"
MANAGED_CLIENT_UI_PROFILE = "LOCUS-managed-client-ui-v1"
MANAGED_CLIENT_INSTANCE_PROFILE = "LOCUS-managed-client-instance-v1"
RECOVERY_PACKAGE_VERSION = "LOCUS-client-recovery-package-v1"
CLEAN_CLIENT_PROFILE = "LOCUS-clean-client-isolation-v2"
SECURITY_MATRIX_VERSION = "LOCUS-security-matrix-v2"
MAX_MANAGED_CONFIG_BYTES = 128 * 1024

EXPECTED_STATIC_SERVICES = (
    "admission",
    "bootstrap",
    "manager-controller",
    "manager-ui",
    "operator",
    "party1",
    "party2",
    "party3",
    "party4",
    "party5",
    "resolver",
    "s3",
    "storage-gateway",
)
EXPECTED_BOOTSTRAP_ROLES = (
    "admission",
    "bootstrap",
    "managed-client",
    "manager-controller",
    "manager-ui",
    "operator",
    "party1",
    "party2",
    "party3",
    "party4",
    "party5",
    "resolver",
    "s3",
    "storage-gateway",
)
EXPECTED_NETWORKS = (
    "admission",
    "browser-edge",
    "client-lifecycle",
    "cloud",
    "control",
    "management",
    "manager-edge",
    "recovery",
    "resolver",
    "storage",
)
EXPECTED_POLICIES = DEFAULT_CUE_POLICY_REGISTRY.policy_ids
EXPECTED_PROFILES = (
    "LOCUS-paired-suite-deployment-2of3-v1",
    "LOCUS-paired-suite-deployment-3of5-v1",
)
MANAGED_CLIENT_NETWORKS = (
    "admission",
    "browser-edge",
    "client-lifecycle",
    "control",
    "recovery",
    "resolver",
    "storage",
)


class ManagedManifestError(ValueError):
    """The managed deployment contract failed closed."""


def _duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate JSON member")
        value[key] = item
    return value


def _exact(value: object, fields: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        raise ManagedManifestError(f"invalid {label}")
    return cast(dict[str, Any], value)


def _identifier(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or len(value) > 255
        or not value.isascii()
        or any(ord(character) < 0x21 or ord(character) > 0x7E for character in value)
    ):
        raise ManagedManifestError(f"invalid {label}")
    return value


def _https_endpoint(value: object, label: str) -> str:
    endpoint = _identifier(value, label)
    parsed = urlsplit(endpoint)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or parsed.path not in {"", "/"}
        or parsed.port != 8443
    ):
        raise ManagedManifestError(f"invalid {label}")
    return endpoint


def _manager_endpoint(value: object) -> str:
    endpoint = _identifier(value, "Manager endpoint")
    parsed = urlsplit(endpoint)
    if (
        parsed.scheme != "http"
        or parsed.hostname != "127.0.0.1"
        or parsed.port != 8765
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or parsed.path not in {"", "/"}
    ):
        raise ManagedManifestError("invalid Manager endpoint")
    return endpoint


def _canonical_names(value: object, expected: tuple[str, ...], label: str) -> None:
    if value != list(expected):
        raise ManagedManifestError(f"invalid {label}")


def _reject_prohibited_content(value: object, *, path: str = "$") -> None:
    prohibited = {
        "cue",
        "lifecycle_secret",
        "password",
        "private_key",
        "proof_key",
        "protected_key",
        "provider_credential",
        "recovery_secret",
        "secret_key",
        "share",
        "wrapping_key",
    }
    if isinstance(value, dict):
        for key, item in value.items():
            normalized = key.lower().replace("-", "_")
            if normalized in prohibited:
                raise ManagedManifestError(
                    f"prohibited managed-manifest member at {path}"
                )
            _reject_prohibited_content(item, path=f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _reject_prohibited_content(item, path=f"{path}[{index}]")


def validate_managed_manifest(value: object) -> dict[str, Any]:
    manifest = _exact(
        value,
        {
            "arms",
            "authorization",
            "client_template",
            "control_plane",
            "deployment_id",
            "networks",
            "policies",
            "provider",
            "security_matrix",
            "services",
            "version",
        },
        "managed manifest",
    )
    if manifest["version"] != MANAGED_CONFIG_VERSION:
        raise ManagedManifestError("unsupported managed configuration")
    if manifest["deployment_id"] != MANAGED_DEPLOYMENT_ID:
        raise ManagedManifestError("unsupported managed deployment")
    if manifest["security_matrix"] != SECURITY_MATRIX_VERSION:
        raise ManagedManifestError("unsupported managed security matrix")
    _reject_prohibited_content(manifest)

    control = _exact(
        manifest["control_plane"],
        {
            "controller_api",
            "controller_profile",
            "manager_api",
            "manager_ui_profile",
        },
        "control plane",
    )
    if control != {
        "controller_api": CONTROLLER_API_VERSION,
        "controller_profile": CONTROLLER_PROFILE,
        "manager_api": MANAGER_API_VERSION,
        "manager_ui_profile": MANAGER_UI_PROFILE,
    }:
        raise ManagedManifestError("invalid managed control plane")

    client = _exact(
        manifest["client_template"],
        {
            "api_version",
            "clean_client_profile",
            "identity",
            "instance_profile",
            "networks",
            "package_format",
            "ui_profile",
        },
        "managed-client template",
    )
    if client != {
        "api_version": MANAGED_CLIENT_API_VERSION,
        "clean_client_profile": CLEAN_CLIENT_PROFILE,
        "identity": "spiffe://locus.invalid/integrated/managed-client",
        "instance_profile": MANAGED_CLIENT_INSTANCE_PROFILE,
        "networks": list(MANAGED_CLIENT_NETWORKS),
        "package_format": RECOVERY_PACKAGE_VERSION,
        "ui_profile": MANAGED_CLIENT_UI_PROFILE,
    }:
        raise ManagedManifestError("invalid managed-client template")

    provider = _exact(
        manifest["provider"],
        {
            "adapter",
            "backup_object_format",
            "endpoint",
            "gateway_profile",
            "list_allowed",
            "tls_mode",
        },
        "provider",
    )
    if provider != {
        "adapter": "s3-compatible-local",
        "backup_object_format": "LOCUS-cloud-backup-object-v2",
        "endpoint": "http://s3:8333",
        "gateway_profile": "LOCUS-application-storage-gateway-v2",
        "list_allowed": False,
        "tls_mode": "internal-emulation-only",
    }:
        raise ManagedManifestError("invalid provider binding")

    authorization = _exact(
        manifest["authorization"], {"authorizers", "quorum"}, "authorization"
    )
    if authorization != {"authorizers": [1, 2, 3, 4, 5], "quorum": 4}:
        raise ManagedManifestError("invalid authorization binding")

    _canonical_names(manifest["networks"], EXPECTED_NETWORKS, "networks")
    _canonical_names(manifest["policies"], EXPECTED_POLICIES, "policies")

    arms = manifest["arms"]
    if not isinstance(arms, list) or len(arms) != 4:
        raise ManagedManifestError("invalid deployment arms")
    expected_arms = [
        (profile_id, suite_id)
        for profile_id in EXPECTED_PROFILES
        for suite_id in (APPSS_SUITE_ID, YI_SUITE_ID)
    ]
    observed_arms: list[tuple[str, str]] = []
    for raw in arms:
        arm = _exact(raw, {"holders", "profile_id", "suite_id"}, "arm")
        profile_id = _identifier(arm["profile_id"], "profile identifier")
        suite_id = _identifier(arm["suite_id"], "suite identifier")
        holders = arm["holders"]
        if profile_id.endswith("2of3-v1"):
            expected_holders = [1, 2, 3]
        elif profile_id.endswith("3of5-v1"):
            expected_holders = [1, 2, 3, 4, 5]
        else:
            raise ManagedManifestError("invalid deployment profile")
        if holders != expected_holders:
            raise ManagedManifestError("invalid holder membership")
        observed_arms.append((profile_id, suite_id))
    if observed_arms != expected_arms:
        raise ManagedManifestError("noncanonical or incomplete deployment arms")

    expected_membership = {
        "admission": ["admission"],
        "bootstrap": [],
        "manager-controller": ["client-lifecycle", "management"],
        "manager-ui": ["management", "manager-edge"],
        "operator": ["control"],
        **{f"party{index}": ["recovery"] for index in range(1, 6)},
        "resolver": ["resolver"],
        "s3": ["cloud"],
        "storage-gateway": ["cloud", "storage"],
    }
    services = manifest["services"]
    if not isinstance(services, list) or len(services) != len(EXPECTED_STATIC_SERVICES):
        raise ManagedManifestError("invalid static service inventory")
    observed_services: list[str] = []
    for raw in services:
        service = _exact(
            raw,
            {"endpoint", "identity", "name", "networks", "persistent_role"},
            "service",
        )
        name = _identifier(service["name"], "service name")
        if name not in expected_membership:
            raise ManagedManifestError("unknown managed service")
        if service["identity"] != f"spiffe://locus.invalid/integrated/{name}":
            raise ManagedManifestError("invalid service identity")
        if service["networks"] != expected_membership[name]:
            raise ManagedManifestError("invalid service network membership")
        endpoint = service["endpoint"]
        if name == "bootstrap":
            if endpoint is not None:
                raise ManagedManifestError("bootstrap must be networkless")
        elif name == "s3":
            if endpoint != "http://s3:8333":
                raise ManagedManifestError("invalid S3 endpoint")
        elif name == "manager-ui":
            if _manager_endpoint(endpoint) != "http://127.0.0.1:8765":
                raise ManagedManifestError("invalid Manager UI endpoint")
        elif _https_endpoint(endpoint, "service endpoint") != f"https://{name}:8443":
            raise ManagedManifestError("service endpoint/name mismatch")
        if not isinstance(service["persistent_role"], bool):
            raise ManagedManifestError("invalid service persistence flag")
        observed_services.append(name)
    if tuple(observed_services) != EXPECTED_STATIC_SERVICES:
        raise ManagedManifestError("noncanonical static service inventory")
    return manifest


def decode_managed_manifest(encoded: bytes) -> dict[str, Any]:
    if (
        not isinstance(encoded, bytes)
        or not encoded
        or len(encoded) > MAX_MANAGED_CONFIG_BYTES
    ):
        raise ManagedManifestError("invalid managed manifest")
    try:
        canonical_bytes = encoded[:-1] if encoded.endswith(b"\n") else encoded
        if not canonical_bytes or b"\n" in canonical_bytes:
            raise ValueError("invalid canonical JSON framing")
        value = json.loads(
            canonical_bytes.decode("utf-8"),
            object_pairs_hook=_duplicates,
            parse_constant=lambda _item: (_ for _ in ()).throw(ValueError()),
        )
        validated = validate_managed_manifest(value)
        if encode(validated) != canonical_bytes:
            raise ValueError("noncanonical JSON")
        return validated
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError, TypeError) as exc:
        if isinstance(exc, ManagedManifestError):
            raise
        raise ManagedManifestError("invalid managed manifest") from exc


def load_managed_manifest(path: str | Path) -> dict[str, Any]:
    return decode_managed_manifest(Path(path).read_bytes())


__all__ = [
    "CLEAN_CLIENT_PROFILE",
    "CONTROLLER_API_VERSION",
    "CONTROLLER_PROFILE",
    "EXPECTED_BOOTSTRAP_ROLES",
    "EXPECTED_NETWORKS",
    "EXPECTED_POLICIES",
    "EXPECTED_PROFILES",
    "EXPECTED_STATIC_SERVICES",
    "MANAGED_CLIENT_API_VERSION",
    "MANAGED_CLIENT_INSTANCE_PROFILE",
    "MANAGED_CLIENT_NETWORKS",
    "MANAGED_CLIENT_UI_PROFILE",
    "MANAGED_CONFIG_VERSION",
    "MANAGED_DEPLOYMENT_ID",
    "MANAGER_API_VERSION",
    "MANAGER_UI_PROFILE",
    "RECOVERY_PACKAGE_VERSION",
    "SECURITY_MATRIX_VERSION",
    "ManagedManifestError",
    "decode_managed_manifest",
    "load_managed_manifest",
    "validate_managed_manifest",
]
