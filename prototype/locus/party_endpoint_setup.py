"""Strict public endpoint setup for local and future five-host deployments."""

from __future__ import annotations

import ipaddress
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PARTY_ENDPOINT_SETUP_VERSION = "LOCUS-party-endpoint-setup-v1"
SAME_HOST_CONTAINERS = "same-host-containers"
SEPARATE_HOSTS_SINGLE_ADMIN = "separate-network-hosts-single-admin"
MAX_ENDPOINT_SETUP_BYTES = 16 * 1024
PARTY_COUNT = 5

_DNS_LABEL = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")


class PartyEndpointSetupError(ValueError):
    """The public party endpoint setup is malformed or unsafe."""


@dataclass(frozen=True)
class PartyEndpoint:
    party_id: int
    host: str
    port: int


@dataclass(frozen=True)
class PartyEndpointSetup:
    deployment_tier: str
    parties: tuple[PartyEndpoint, ...]
    version: str = PARTY_ENDPOINT_SETUP_VERSION


def _exact_dict(value: object, fields: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        raise PartyEndpointSetupError(f"invalid {label}")
    return value


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, item in pairs:
        if key in value:
            raise PartyEndpointSetupError("duplicate endpoint setup field")
        value[key] = item
    return value


def canonical_host(value: object) -> str:
    if not isinstance(value, str) or not value or len(value) > 253:
        raise PartyEndpointSetupError("invalid party host")
    if not value.isascii() or value != value.lower():
        raise PartyEndpointSetupError("party host must be lowercase ASCII")
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        if value.endswith("."):
            raise PartyEndpointSetupError(
                "party DNS name must not have a trailing dot"
            ) from None
        labels = value.split(".")
        if not all(_DNS_LABEL.fullmatch(label) for label in labels):
            raise PartyEndpointSetupError("invalid party DNS name") from None
        return value
    if str(address) != value:
        raise PartyEndpointSetupError("party IP address is not canonical")
    if address.is_unspecified or address.is_multicast:
        raise PartyEndpointSetupError("unsafe party IP address")
    return value


def validate_party_endpoint_setup(value: object) -> PartyEndpointSetup:
    setup = _exact_dict(
        value,
        {"deployment_tier", "parties", "version"},
        "party endpoint setup",
    )
    if setup["version"] != PARTY_ENDPOINT_SETUP_VERSION:
        raise PartyEndpointSetupError("unsupported party endpoint setup version")
    tier = setup["deployment_tier"]
    if tier not in {SAME_HOST_CONTAINERS, SEPARATE_HOSTS_SINGLE_ADMIN}:
        raise PartyEndpointSetupError("unsupported deployment tier")
    raw_parties = setup["parties"]
    if not isinstance(raw_parties, list) or len(raw_parties) != PARTY_COUNT:
        raise PartyEndpointSetupError("exactly five party endpoints are required")
    parties: list[PartyEndpoint] = []
    for expected_id, raw in enumerate(raw_parties, start=1):
        endpoint = _exact_dict(raw, {"host", "party_id", "port"}, "party endpoint")
        party_id = endpoint["party_id"]
        port = endpoint["port"]
        if party_id != expected_id:
            raise PartyEndpointSetupError("party endpoints must be ordered 1 through 5")
        if (
            isinstance(port, bool)
            or not isinstance(port, int)
            or not 1 <= port <= 65535
        ):
            raise PartyEndpointSetupError("invalid party port")
        parties.append(
            PartyEndpoint(
                party_id=party_id,
                host=canonical_host(endpoint["host"]),
                port=port,
            )
        )
    if tier == SAME_HOST_CONTAINERS:
        if [(party.host, party.port) for party in parties] != [
            (f"party{party_id}", 8443) for party_id in range(1, PARTY_COUNT + 1)
        ]:
            raise PartyEndpointSetupError(
                "same-host container endpoints must use the Compose service names"
            )
    else:
        hosts = [party.host for party in parties]
        if len(set(hosts)) != PARTY_COUNT:
            raise PartyEndpointSetupError("separate hosts must be distinct")
        for host in hosts:
            try:
                address = ipaddress.ip_address(host)
            except ValueError:
                if host == "localhost":
                    raise PartyEndpointSetupError(
                        "separate hosts cannot use localhost"
                    ) from None
            else:
                if address.is_loopback or address.is_link_local:
                    raise PartyEndpointSetupError(
                        "separate hosts cannot use loopback or link-local addresses"
                    )
    return PartyEndpointSetup(deployment_tier=tier, parties=tuple(parties))


def load_party_endpoint_setup(path: Path) -> PartyEndpointSetup:
    try:
        if path.is_symlink() or not path.is_file():
            raise PartyEndpointSetupError("endpoint setup must be a regular file")
        encoded = path.read_bytes()
    except OSError as exc:
        raise PartyEndpointSetupError("endpoint setup is unavailable") from exc
    if not encoded or len(encoded) > MAX_ENDPOINT_SETUP_BYTES:
        raise PartyEndpointSetupError("endpoint setup size is invalid")
    try:
        text = encoded.decode("ascii")
        value = json.loads(text, object_pairs_hook=_unique_object)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PartyEndpointSetupError(
            "endpoint setup is not strict ASCII JSON"
        ) from exc
    return validate_party_endpoint_setup(value)


def endpoint_setup_public_value(setup: PartyEndpointSetup) -> dict[str, object]:
    return {
        "deployment_tier": setup.deployment_tier,
        "parties": [
            {"host": party.host, "party_id": party.party_id, "port": party.port}
            for party in setup.parties
        ],
        "version": setup.version,
    }


__all__ = [
    "PARTY_ENDPOINT_SETUP_VERSION",
    "SAME_HOST_CONTAINERS",
    "SEPARATE_HOSTS_SINGLE_ADMIN",
    "PartyEndpoint",
    "PartyEndpointSetup",
    "PartyEndpointSetupError",
    "canonical_host",
    "endpoint_setup_public_value",
    "load_party_endpoint_setup",
    "validate_party_endpoint_setup",
]
