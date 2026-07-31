"""Frozen LOCUS three-pair reference cue canonicalization."""

from __future__ import annotations

import re
import unicodedata
from decimal import ROUND_HALF_EVEN, Decimal, InvalidOperation
from typing import Any

from .codec import encode
from .crypto import hash_bytes

POLICY_VERSION = "LOCUS-location-person-set-v1"
PAIR_VERSION = "LOCUS-location-person-pair-v1"

_DECIMAL = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]{1,8})?\Z")
_PHONE = re.compile(r"\+[1-9][0-9]{7,14}\Z")
_EMAIL_LOCAL = re.compile(
    r"[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+)*\Z"
)
_DOMAIN_LABEL = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\Z")


class CuePolicyError(Exception):
    """The recovery input does not conform to the frozen cue policy."""


def _exact_dict(value: object, fields: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        raise CuePolicyError(f"invalid {label}")
    return value


def _coordinate(value: object, label: str, *, minimum: int, maximum: int) -> int:
    if not isinstance(value, str) or _DECIMAL.fullmatch(value) is None:
        raise CuePolicyError(f"invalid {label}")
    if value.startswith("-0"):
        try:
            if Decimal(value) == 0:
                raise CuePolicyError(f"invalid {label}")
        except InvalidOperation as exc:
            raise CuePolicyError(f"invalid {label}") from exc
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise CuePolicyError(f"invalid {label}") from exc
    if parsed < minimum or parsed > maximum:
        raise CuePolicyError(f"invalid {label}")
    quantized = (parsed * 10000).to_integral_value(rounding=ROUND_HALF_EVEN)
    return int(quantized)


def canonical_location(value: object) -> dict[str, int]:
    location = _exact_dict(value, {"latitude", "longitude"}, "location")
    return {
        "latitude_e4": _coordinate(
            location["latitude"], "latitude", minimum=-90, maximum=90
        ),
        "longitude_e4": _coordinate(
            location["longitude"], "longitude", minimum=-180, maximum=180
        ),
    }


def _email(value: object) -> str:
    if not isinstance(value, str) or not value or not value.isascii():
        raise CuePolicyError("invalid email contact")
    if value != unicodedata.normalize("NFC", value) or "@" not in value:
        raise CuePolicyError("invalid email contact")
    local, separator, domain = value.rpartition("@")
    if separator != "@" or _EMAIL_LOCAL.fullmatch(local) is None:
        raise CuePolicyError("invalid email contact")
    labels = domain.split(".")
    if len(labels) < 2 or any(
        _DOMAIN_LABEL.fullmatch(label) is None for label in labels
    ):
        raise CuePolicyError("invalid email contact")
    return f"{local.lower()}@{domain.lower()}"


def _phone(value: object) -> str:
    if not isinstance(value, str) or _PHONE.fullmatch(value) is None:
        raise CuePolicyError("invalid phone contact")
    return value


def canonical_person(value: object) -> dict[str, str]:
    person = _exact_dict(value, {"type", "value"}, "person")
    contact_type = person["type"]
    if contact_type == "email":
        contact_value = _email(person["value"])
    elif contact_type == "phone":
        contact_value = _phone(person["value"])
    else:
        raise CuePolicyError("unsupported person contact type")
    return {"type": contact_type, "value": contact_value}


def canonical_pair(value: object) -> dict[str, Any]:
    pair = _exact_dict(value, {"location", "person"}, "location-person pair")
    return {
        "location": canonical_location(pair["location"]),
        "person": canonical_person(pair["person"]),
        "version": PAIR_VERSION,
    }


def canonical_recovery_input(cues: object) -> bytes:
    if not isinstance(cues, list) or len(cues) != 3:
        raise CuePolicyError("exactly three cue pairs are required")
    pairs = [canonical_pair(cue) for cue in cues]
    locations = [encode(pair["location"]) for pair in pairs]
    people = [encode(pair["person"]) for pair in pairs]
    pair_encodings = [encode(pair) for pair in pairs]
    if len(set(locations)) != 3:
        raise CuePolicyError("duplicate canonical locations are not allowed")
    if len(set(people)) != 3:
        raise CuePolicyError("duplicate canonical people are not allowed")
    if len(set(pair_encodings)) != 3:
        raise CuePolicyError("duplicate cue pairs are not allowed")
    ordered = sorted(
        pairs,
        key=lambda pair: (
            hash_bytes("LOCUS/cue-pair/v1", encode(pair)),
            encode(pair),
        ),
    )
    return encode({"pairs": ordered, "version": POLICY_VERSION})
