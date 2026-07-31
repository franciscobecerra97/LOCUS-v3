"""Deterministic encoding helpers for the LOCUS reference prototype."""

from __future__ import annotations

import json
import unicodedata
from typing import Any


def normalize_text(value: Any) -> str:
    """Normalize text before it enters the deterministic encoding layer."""
    return unicodedata.normalize("NFC", str(value).strip())


def canonicalize(value: Any) -> Any:
    """Return a JSON-compatible value with stable string normalization."""
    if isinstance(value, dict):
        return {str(k): canonicalize(value[k]) for k in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [canonicalize(item) for item in value]
    if isinstance(value, str):
        return normalize_text(value)
    if isinstance(value, bytes):
        return {"__bytes_hex__": value.hex()}
    return value


def encode(value: Any) -> bytes:
    """Encode a value deterministically for hashing or storage measurement."""
    return json.dumps(
        canonicalize(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")


def encoded_size(value: Any) -> int:
    return len(encode(value))
