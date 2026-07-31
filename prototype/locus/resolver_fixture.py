"""Strict client-side mapping for deterministic resolver drift simulations."""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from .cue_policy import CuePolicyError, canonical_recovery_input

RESOLVER_PROFILE_VERSION = "LOCUS-deterministic-directory-v1"
_RECORD_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z")


class ResolverFixtureError(Exception):
    """A resolver selection cannot safely produce one recovery input."""


def _fail() -> ResolverFixtureError:
    return ResolverFixtureError("resolver selection unavailable")


def _exact_dict(value: object, fields: set[str]) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        raise _fail()
    return value


def _display_text(value: object) -> None:
    if (
        not isinstance(value, str)
        or not value
        or len(value) > 256
        or value != unicodedata.normalize("NFC", value)
        or any(unicodedata.category(character).startswith("C") for character in value)
    ):
        raise _fail()


def _record_id(value: object) -> None:
    if not isinstance(value, str) or _RECORD_ID.fullmatch(value) is None:
        raise _fail()


def canonical_resolver_input(response: object) -> bytes:
    """Map one unambiguous directory response to canonical cue bytes."""

    envelope = _exact_dict(response, {"pairs", "profile_version", "status"})
    if (
        envelope["profile_version"] != RESOLVER_PROFILE_VERSION
        or envelope["status"] != "resolved"
        or not isinstance(envelope["pairs"], list)
        or len(envelope["pairs"]) != 3
    ):
        raise _fail()
    cues: list[dict[str, object]] = []
    for pair_value in envelope["pairs"]:
        pair = _exact_dict(pair_value, {"location", "person"})
        location = _exact_dict(
            pair["location"],
            {"display_name", "latitude", "longitude", "record_id"},
        )
        person = _exact_dict(
            pair["person"], {"display_name", "record_id", "selected_contact"}
        )
        _record_id(location["record_id"])
        _record_id(person["record_id"])
        _display_text(location["display_name"])
        _display_text(person["display_name"])
        cues.append(
            {
                "location": {
                    "latitude": location["latitude"],
                    "longitude": location["longitude"],
                },
                "person": person["selected_contact"],
            }
        )
    try:
        return canonical_recovery_input(cues)
    except CuePolicyError as exc:
        raise _fail() from exc
