"""Exact registry for immutable LOCUS CuePolicy implementations."""

from __future__ import annotations

from collections.abc import Iterable

from .contracts import CuePolicy
from .cue_policy import (
    CANONICAL_EMAIL_SET_POLICY,
    CANONICAL_PHONE_SET_POLICY,
    FROZEN_LOCATION_PERSON_POLICY,
    QUANTIZED_COORDINATE_SET_POLICY,
)


class CuePolicyRegistryError(ValueError):
    """A CuePolicy registry or exact lookup is invalid."""


class CuePolicyRegistry:
    """Map exact immutable identifiers to independent policy adapters."""

    def __init__(self, policies: Iterable[CuePolicy]) -> None:
        registered: dict[str, CuePolicy] = {}
        for policy in policies:
            if policy.policy_id != policy.metadata.policy_id:
                raise CuePolicyRegistryError("CuePolicy metadata mismatch")
            if policy.policy_id in registered:
                raise CuePolicyRegistryError("duplicate CuePolicy identifier")
            registered[policy.policy_id] = policy
        if not registered:
            raise CuePolicyRegistryError("empty CuePolicy registry")
        self._policies = registered

    @property
    def policy_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._policies))

    def require(self, policy_id: str) -> CuePolicy:
        try:
            return self._policies[policy_id]
        except (KeyError, TypeError) as exc:
            raise CuePolicyRegistryError("unsupported CuePolicy") from exc


DEFAULT_CUE_POLICY_REGISTRY = CuePolicyRegistry(
    (
        FROZEN_LOCATION_PERSON_POLICY,
        QUANTIZED_COORDINATE_SET_POLICY,
        CANONICAL_PHONE_SET_POLICY,
        CANONICAL_EMAIL_SET_POLICY,
    )
)


__all__ = [
    "CuePolicyRegistry",
    "CuePolicyRegistryError",
    "DEFAULT_CUE_POLICY_REGISTRY",
]
