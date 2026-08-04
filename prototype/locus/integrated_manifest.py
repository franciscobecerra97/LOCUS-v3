"""Strict public contract for the P7.5 integrated reference deployment."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast
from urllib.parse import urlsplit

from .appss_formats import APPSS_SUITE_ID, YI_SUITE_ID
from .codec import encode
from .cue_policy_registry import DEFAULT_CUE_POLICY_REGISTRY
from .paired_deployment_profiles import PAIRED_PROFILES

INTEGRATED_DEPLOYMENT_ID = "LOCUS-integrated-reference-deployment-v1"
INTEGRATED_CONFIG_VERSION = "LOCUS-integrated-reference-config-v1"
MAX_INTEGRATED_CONFIG_BYTES = 128 * 1024

EXPECTED_SERVICES = (
    "admission",
    "bootstrap",
    "operator",
    "party1",
    "party2",
    "party3",
    "party4",
    "party5",
    "resolver",
    "s3",
    "storage-gateway",
    "ui-client-a",
    "ui-client-b",
)
EXPECTED_NETWORKS = (
    "admission",
    "browser-edge",
    "cloud",
    "control",
    "recovery",
    "resolver",
    "storage",
)
EXPECTED_POLICIES = DEFAULT_CUE_POLICY_REGISTRY.policy_ids
EXPECTED_PROFILES = tuple(sorted(PAIRED_PROFILES))


class IntegratedManifestError(ValueError):
    """The integrated deployment contract failed closed."""


def _duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate JSON member")
        value[key] = item
    return value


def _exact(value: object, fields: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        raise IntegratedManifestError(f"invalid {label}")
    return cast(dict[str, Any], value)


def _identifier(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or len(value) > 255
        or not value.isascii()
        or any(ord(character) < 0x21 or ord(character) > 0x7E for character in value)
    ):
        raise IntegratedManifestError(f"invalid {label}")
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
        raise IntegratedManifestError(f"invalid {label}")
    return endpoint


def _canonical_names(value: object, expected: tuple[str, ...], label: str) -> None:
    if value != list(expected):
        raise IntegratedManifestError(f"invalid {label}")


def _reject_prohibited_content(value: object, *, path: str = "$") -> None:
    prohibited = {
        "cue",
        "password",
        "protected_key",
        "private_key",
        "recovery_secret",
        "provider_credential",
        "secret_key",
        "share",
        "wrapping_key",
    }
    if isinstance(value, dict):
        for key, item in value.items():
            normalized = key.lower().replace("-", "_")
            if normalized in prohibited:
                raise IntegratedManifestError(f"prohibited manifest member at {path}")
            _reject_prohibited_content(item, path=f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _reject_prohibited_content(item, path=f"{path}[{index}]")


def validate_integrated_manifest(value: object) -> dict[str, Any]:
    manifest = _exact(
        value,
        {
            "arms",
            "authorization",
            "clients",
            "deployment_id",
            "networks",
            "policies",
            "provider",
            "services",
            "version",
        },
        "integrated manifest",
    )
    if manifest["version"] != INTEGRATED_CONFIG_VERSION:
        raise IntegratedManifestError("unsupported integrated configuration")
    if manifest["deployment_id"] != INTEGRATED_DEPLOYMENT_ID:
        raise IntegratedManifestError("unsupported integrated deployment")
    _reject_prohibited_content(manifest)

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
        raise IntegratedManifestError("invalid provider binding")

    authorization = _exact(
        manifest["authorization"],
        {"authorizers", "quorum"},
        "authorization",
    )
    if authorization != {"authorizers": [1, 2, 3, 4, 5], "quorum": 4}:
        raise IntegratedManifestError("invalid authorization binding")

    clients = _exact(
        manifest["clients"],
        {"enrollment", "recovery"},
        "clients",
    )
    if clients != {
        "enrollment": "ui-client-a",
        "recovery": "ui-client-b",
    }:
        raise IntegratedManifestError("invalid clean-client binding")

    _canonical_names(manifest["networks"], EXPECTED_NETWORKS, "networks")
    _canonical_names(manifest["policies"], EXPECTED_POLICIES, "policies")

    arms = manifest["arms"]
    if not isinstance(arms, list) or len(arms) != 4:
        raise IntegratedManifestError("invalid deployment arms")
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
            raise IntegratedManifestError("invalid deployment profile")
        if holders != expected_holders:
            raise IntegratedManifestError("invalid holder membership")
        observed_arms.append((profile_id, suite_id))
    if observed_arms != expected_arms:
        raise IntegratedManifestError("noncanonical or incomplete deployment arms")

    services = manifest["services"]
    if not isinstance(services, list) or len(services) != len(EXPECTED_SERVICES):
        raise IntegratedManifestError("invalid service inventory")
    observed_services: list[str] = []
    for raw in services:
        service = _exact(
            raw,
            {"endpoint", "identity", "name", "networks", "persistent_role"},
            "service",
        )
        name = _identifier(service["name"], "service name")
        if service["identity"] != f"spiffe://locus.invalid/integrated/{name}":
            raise IntegratedManifestError("invalid service identity")
        networks = service["networks"]
        if (
            not isinstance(networks, list)
            or networks != sorted(set(networks))
            or any(item not in EXPECTED_NETWORKS for item in networks)
        ):
            raise IntegratedManifestError("invalid service network membership")
        endpoint = service["endpoint"]
        if name == "bootstrap":
            if endpoint is not None or networks:
                raise IntegratedManifestError("bootstrap must be networkless")
        elif name == "s3":
            if endpoint != "http://s3:8333":
                raise IntegratedManifestError("invalid S3 endpoint")
        elif name in {"ui-client-a", "ui-client-b"}:
            if endpoint != "http://127.0.0.1:8765":
                raise IntegratedManifestError("invalid loopback UI endpoint")
            if "browser-edge" not in networks:
                raise IntegratedManifestError("UI is missing the browser edge")
        else:
            if _https_endpoint(endpoint, "service endpoint") != f"https://{name}:8443":
                raise IntegratedManifestError("service endpoint/name mismatch")
        if not isinstance(service["persistent_role"], bool):
            raise IntegratedManifestError("invalid service persistence flag")
        observed_services.append(name)
    if tuple(observed_services) != EXPECTED_SERVICES:
        raise IntegratedManifestError("noncanonical service inventory")
    return manifest


def decode_integrated_manifest(encoded: bytes) -> dict[str, Any]:
    if (
        not isinstance(encoded, bytes)
        or not encoded
        or len(encoded) > MAX_INTEGRATED_CONFIG_BYTES
    ):
        raise IntegratedManifestError("invalid integrated manifest")
    try:
        canonical_bytes = encoded[:-1] if encoded.endswith(b"\n") else encoded
        if not canonical_bytes or b"\n" in canonical_bytes:
            raise ValueError("invalid canonical JSON framing")
        value = json.loads(
            canonical_bytes.decode("utf-8"),
            object_pairs_hook=_duplicates,
            parse_constant=lambda _item: (_ for _ in ()).throw(ValueError()),
        )
        validated = validate_integrated_manifest(value)
        if encode(validated) != canonical_bytes:
            raise ValueError("noncanonical JSON")
        return validated
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError, TypeError) as exc:
        if isinstance(exc, IntegratedManifestError):
            raise
        raise IntegratedManifestError("invalid integrated manifest") from exc


def load_integrated_manifest(path: str | Path) -> dict[str, Any]:
    return decode_integrated_manifest(Path(path).read_bytes())


__all__ = [
    "EXPECTED_NETWORKS",
    "EXPECTED_POLICIES",
    "EXPECTED_PROFILES",
    "EXPECTED_SERVICES",
    "INTEGRATED_CONFIG_VERSION",
    "INTEGRATED_DEPLOYMENT_ID",
    "IntegratedManifestError",
    "decode_integrated_manifest",
    "load_integrated_manifest",
    "validate_integrated_manifest",
]
