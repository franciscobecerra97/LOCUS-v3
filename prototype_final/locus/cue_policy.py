"""Frozen LOCUS three-pair reference cue canonicalization."""

from __future__ import annotations

import re
import unicodedata
from decimal import ROUND_HALF_EVEN, Decimal, InvalidOperation
from typing import Any

from .codec import encode
from .contracts import CuePolicy, CuePolicyMetadata, CuePolicyResult
from .crypto import hash_bytes

POLICY_VERSION = "LOCUS-location-person-set-v1"
PAIR_VERSION = "LOCUS-location-person-pair-v1"
COORDINATE_SET_POLICY_VERSION = "LOCUS-quantized-coordinate-set-v1"
PHONE_SET_POLICY_VERSION = "LOCUS-canonical-phone-set-v1"
EMAIL_SET_POLICY_VERSION = "LOCUS-canonical-email-set-v1"
NO_RESOLVER_PROFILE_VERSION = "LOCUS-no-resolver-v1"

_FROZEN_MEMBER_ORDER_DOMAIN = "LOCUS/cue-pair/v1"
_COORDINATE_MEMBER_ORDER_DOMAIN = "LOCUS/quantized-coordinate-set/member-order/v1"
_PHONE_MEMBER_ORDER_DOMAIN = "LOCUS/canonical-phone-set/member-order/v1"
_EMAIL_MEMBER_ORDER_DOMAIN = "LOCUS/canonical-email-set/member-order/v1"

_DECIMAL = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]{1,8})?\Z")
_PHONE = re.compile(r"\+[1-9][0-9]{7,14}\Z")
_ATOMIC_PHONE = re.compile(r"\+[1-9][0-9]{1,14}\Z")
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


class FrozenLocationPersonCuePolicy:
    """Adapter for the byte-frozen v1 CuePolicy implementation."""

    metadata = CuePolicyMetadata(
        policy_id=POLICY_VERSION,
        input_category="location-person-pair-set",
        input_schema="exact-list[3]<location-person-pair-v1>",
        cardinality=3,
        resolver_profile_id="LOCUS-deterministic-directory-v1",
        member_order_domain=_FROZEN_MEMBER_ORDER_DOMAIN,
        ambiguity_rule="reject",
        duplicate_rule="reject-after-canonicalization",
    )
    policy_id = metadata.policy_id

    def process(self, recovery_input: object) -> CuePolicyResult:
        return CuePolicyResult(
            policy_id=self.policy_id,
            canonical_bytes=canonical_recovery_input(recovery_input),
        )


def _exact_three(value: object, category: str) -> list[object]:
    if not isinstance(value, list) or len(value) != 3:
        raise CuePolicyError(f"exactly three {category} are required")
    return value


def _canonical_atomic_email(value: object) -> str:
    if not isinstance(value, str) or len(value) > 254 or "@" not in value:
        raise CuePolicyError("invalid email")
    local, separator, domain = value.rpartition("@")
    if separator != "@" or len(local) > 64 or not domain or len(domain) > 253:
        raise CuePolicyError("invalid email")
    try:
        return _email(value)
    except CuePolicyError as exc:
        raise CuePolicyError("invalid email") from exc


def _canonical_atomic_phone(value: object) -> str:
    if not isinstance(value, str) or _ATOMIC_PHONE.fullmatch(value) is None:
        raise CuePolicyError("invalid phone")
    return value


def _ordered_distinct_members[Member](
    members: list[Member], *, domain: str, duplicate_label: str
) -> list[Member]:
    encodings = [encode(member) for member in members]
    if len(set(encodings)) != len(encodings):
        raise CuePolicyError(f"duplicate canonical {duplicate_label} are not allowed")
    return [
        member
        for _, member in sorted(
            zip(encodings, members, strict=True),
            key=lambda item: (hash_bytes(domain, item[0]), item[0]),
        )
    ]


class QuantizedCoordinateSetCuePolicy:
    """Exactly three distinct WGS84 coordinates quantized to 10^-4 degrees."""

    metadata = CuePolicyMetadata(
        policy_id=COORDINATE_SET_POLICY_VERSION,
        input_category="quantized-coordinate-set",
        input_schema="exact-list[3]<latitude-longitude-decimal-strings>",
        cardinality=3,
        resolver_profile_id=NO_RESOLVER_PROFILE_VERSION,
        member_order_domain=_COORDINATE_MEMBER_ORDER_DOMAIN,
        ambiguity_rule="reject",
        duplicate_rule="reject-after-quantization",
    )
    policy_id = metadata.policy_id

    def process(self, recovery_input: object) -> CuePolicyResult:
        values = _exact_three(recovery_input, "coordinates")
        members = [canonical_location(value) for value in values]
        ordered = _ordered_distinct_members(
            members,
            domain=self.metadata.member_order_domain,
            duplicate_label="coordinates",
        )
        return CuePolicyResult(
            policy_id=self.policy_id,
            canonical_bytes=encode({"coordinates": ordered, "version": self.policy_id}),
        )


class CanonicalPhoneSetCuePolicy:
    """Exactly three distinct phone numbers in bounded E.164 lexical form."""

    metadata = CuePolicyMetadata(
        policy_id=PHONE_SET_POLICY_VERSION,
        input_category="canonical-phone-set",
        input_schema="exact-list[3]<e164-lexical-string>",
        cardinality=3,
        resolver_profile_id=NO_RESOLVER_PROFILE_VERSION,
        member_order_domain=_PHONE_MEMBER_ORDER_DOMAIN,
        ambiguity_rule="reject",
        duplicate_rule="reject-after-canonicalization",
    )
    policy_id = metadata.policy_id

    def process(self, recovery_input: object) -> CuePolicyResult:
        values = _exact_three(recovery_input, "phone numbers")
        members = [_canonical_atomic_phone(value) for value in values]
        ordered = _ordered_distinct_members(
            members,
            domain=self.metadata.member_order_domain,
            duplicate_label="phone numbers",
        )
        return CuePolicyResult(
            policy_id=self.policy_id,
            canonical_bytes=encode({"phones": ordered, "version": self.policy_id}),
        )


class CanonicalEmailSetCuePolicy:
    """Exactly three distinct addresses under the constrained LOCUS grammar."""

    metadata = CuePolicyMetadata(
        policy_id=EMAIL_SET_POLICY_VERSION,
        input_category="canonical-email-set",
        input_schema="exact-list[3]<constrained-ascii-email-string>",
        cardinality=3,
        resolver_profile_id=NO_RESOLVER_PROFILE_VERSION,
        member_order_domain=_EMAIL_MEMBER_ORDER_DOMAIN,
        ambiguity_rule="reject",
        duplicate_rule="reject-after-lowercasing",
    )
    policy_id = metadata.policy_id

    def process(self, recovery_input: object) -> CuePolicyResult:
        values = _exact_three(recovery_input, "email addresses")
        members = [_canonical_atomic_email(value) for value in values]
        ordered = _ordered_distinct_members(
            members,
            domain=self.metadata.member_order_domain,
            duplicate_label="email addresses",
        )
        return CuePolicyResult(
            policy_id=self.policy_id,
            canonical_bytes=encode({"emails": ordered, "version": self.policy_id}),
        )


FROZEN_LOCATION_PERSON_POLICY: CuePolicy = FrozenLocationPersonCuePolicy()
QUANTIZED_COORDINATE_SET_POLICY: CuePolicy = QuantizedCoordinateSetCuePolicy()
CANONICAL_PHONE_SET_POLICY: CuePolicy = CanonicalPhoneSetCuePolicy()
CANONICAL_EMAIL_SET_POLICY: CuePolicy = CanonicalEmailSetCuePolicy()


__all__ = [
    "CANONICAL_EMAIL_SET_POLICY",
    "CANONICAL_PHONE_SET_POLICY",
    "COORDINATE_SET_POLICY_VERSION",
    "CuePolicyError",
    "EMAIL_SET_POLICY_VERSION",
    "FROZEN_LOCATION_PERSON_POLICY",
    "CanonicalEmailSetCuePolicy",
    "CanonicalPhoneSetCuePolicy",
    "FrozenLocationPersonCuePolicy",
    "NO_RESOLVER_PROFILE_VERSION",
    "PAIR_VERSION",
    "PHONE_SET_POLICY_VERSION",
    "POLICY_VERSION",
    "QUANTIZED_COORDINATE_SET_POLICY",
    "QuantizedCoordinateSetCuePolicy",
    "canonical_location",
    "canonical_pair",
    "canonical_person",
    "canonical_recovery_input",
]
