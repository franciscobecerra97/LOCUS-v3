"""Fail-closed output checks for privacy- and secret-sensitive LOCUS data."""

from __future__ import annotations

import math
import re
from collections.abc import Mapping


class OutputSafetyError(Exception):
    """A value is unsafe for normal terminal, log, trace, or artifact output."""


_FORBIDDEN_FIELDS = frozenset(
    {
        "access_key",
        "canonical_cue",
        "canonical_cues",
        "cue",
        "cue_id",
        "cue_identifier",
        "cue_records",
        "cues",
        "derived_cue_id",
        "derived_password",
        "gateway_response",
        "group_secret",
        "party_randomness",
        "party_state",
        "password",
        "passphrase",
        "private_key",
        "raw_cue",
        "raw_cues",
        "recovered_group_secret",
        "recovered_secret",
        "response_share",
        "secret_key",
        "secret_party_state",
        "signer_private_key",
        "state",
        "tpass_password",
        "tpass_share",
        "tpass_state",
        "wrap_key",
        "wrapping_key",
    }
)
_STATIC_TEXT_MARKERS = {
    "private-key-block": "-----BEGIN PRIVATE KEY-----",
    "encrypted-private-key-block": "-----BEGIN ENCRYPTED PRIVATE KEY-----",
    "openssh-private-key-block": "-----BEGIN OPENSSH PRIVATE KEY-----",
}
_MAX_DEPTH = 16
_MAX_ITEMS = 100_000


def _field_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_")


def validate_public_output(value: object) -> None:
    """Reject secret-bearing fields, private-key markers, and non-JSON values."""

    seen = 0

    def visit(item: object, depth: int) -> None:
        nonlocal seen
        seen += 1
        if seen > _MAX_ITEMS or depth > _MAX_DEPTH:
            raise OutputSafetyError("public output exceeds safety limits")
        if item is None or isinstance(item, (bool, int)):
            return
        if isinstance(item, float):
            if not math.isfinite(item):
                raise OutputSafetyError("public output contains a non-finite number")
            return
        if isinstance(item, str):
            if any(marker in item for marker in _STATIC_TEXT_MARKERS.values()):
                raise OutputSafetyError("public output contains private-key material")
            return
        if isinstance(item, list):
            for child in item:
                visit(child, depth + 1)
            return
        if isinstance(item, dict):
            for key, child in item.items():
                if not isinstance(key, str):
                    raise OutputSafetyError("public output contains a non-string field")
                if _field_name(key) in _FORBIDDEN_FIELDS:
                    raise OutputSafetyError("public output contains a prohibited field")
                visit(child, depth + 1)
            return
        raise OutputSafetyError("public output contains a non-JSON value")

    visit(value, 0)


def exposed_categories(
    text: str, known_sensitive_values: Mapping[str, str | bytes]
) -> list[str]:
    """Return labels, never values, for prohibited material found in text."""

    found = {label for label, marker in _STATIC_TEXT_MARKERS.items() if marker in text}
    folded = text.casefold()
    for field in _FORBIDDEN_FIELDS:
        if f'"{field}"' in folded or f'"{field.replace("_", "-")}"' in folded:
            found.add(f"field:{field}")
    for label, raw_value in known_sensitive_values.items():
        value = (
            raw_value.decode("utf-8", errors="ignore")
            if isinstance(raw_value, bytes)
            else raw_value
        )
        if value and value in text:
            found.add(label)
    return sorted(found)
