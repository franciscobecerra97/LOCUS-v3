"""Explicit resolver-free adapter for direct-input atomic CuePolicies."""

from __future__ import annotations

from .contracts import ResolverResult
from .cue_policy import NO_RESOLVER_PROFILE_VERSION, CuePolicyError
from .cue_policy_registry import (
    DEFAULT_CUE_POLICY_REGISTRY,
    CuePolicyRegistry,
    CuePolicyRegistryError,
)


class NoResolverError(ValueError):
    """Direct input cannot be processed by the exact selected policy."""


class NoResolverAdapter:
    """Invoke one exact direct-input policy without lookup or alternatives."""

    profile_id = NO_RESOLVER_PROFILE_VERSION

    def __init__(
        self,
        policy_id: str,
        *,
        registry: CuePolicyRegistry = DEFAULT_CUE_POLICY_REGISTRY,
    ) -> None:
        try:
            policy = registry.require(policy_id)
        except CuePolicyRegistryError as exc:
            raise NoResolverError("unsupported direct-input CuePolicy") from exc
        if policy.metadata.resolver_profile_id != self.profile_id:
            raise NoResolverError("CuePolicy requires another resolver profile")
        self.policy_id = policy.policy_id
        self._policy = policy

    def resolve(self, query_result: object) -> ResolverResult:
        try:
            result = self._policy.process(query_result)
        except CuePolicyError as exc:
            raise NoResolverError("direct recovery input rejected") from exc
        if result.policy_id != self.policy_id:
            raise NoResolverError("direct-input CuePolicy binding mismatch")
        return ResolverResult(
            resolver_profile=self.profile_id,
            policy_id=self.policy_id,
            canonical_bytes=result.canonical_bytes,
        )


__all__ = ["NoResolverAdapter", "NoResolverError"]
