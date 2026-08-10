"""Exact recovery-suite registry and no-fallback selector dispatch."""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from .appss import AppssRecoveryAdapter
from .appss_formats import (
    APPSS_PROFILE_2_OF_3,
    APPSS_PROFILE_3_OF_5,
    APPSS_SUITE_ID,
    MAX_SELECTOR_BYTES,
    RECOVERY_SUITE_SELECTOR,
    RECOVERY_SUITE_SELECTOR_V2,
    YI_PROFILE_2_OF_3,
    YI_PROFILE_3_OF_5,
    YI_SUITE_ID,
    AppssFormatError,
    canonical_decode,
    encode_checked,
    validate_selector,
)
from .contracts import PasswordProtectedSecretRecovery, ThresholdParameters
from .yi_compat import RecoverySuiteError, YiTpassRecoveryAdapter


@dataclass(frozen=True)
class RecoverySuiteSelection:
    suite_id: str
    profile_id: str
    threshold: ThresholdParameters
    holder_ids: tuple[int, ...]
    authorizer_ids: tuple[int, ...]
    authorization_quorum: int


class RecoverySuiteRegistry:
    """Registry used for explicit enrollment and descriptor-only recovery."""

    def __init__(self) -> None:
        self._adapters: dict[str, PasswordProtectedSecretRecovery] = {
            YI_SUITE_ID: cast(
                PasswordProtectedSecretRecovery, YiTpassRecoveryAdapter()
            ),
            APPSS_SUITE_ID: cast(
                PasswordProtectedSecretRecovery, AppssRecoveryAdapter()
            ),
        }

    @property
    def suite_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._adapters))

    def for_authenticated_descriptor(
        self, suite_id: str
    ) -> PasswordProtectedSecretRecovery:
        """Dispatch one authenticated suite ID with no retry or downgrade."""
        try:
            return self._adapters[suite_id]
        except (KeyError, TypeError) as exc:
            raise RecoverySuiteError("unsupported descriptor recovery suite") from exc

    def select_new_epoch(
        self, encoded_selector: bytes
    ) -> tuple[RecoverySuiteSelection, PasswordProtectedSecretRecovery]:
        """Validate one enrollment/successor choice; never accept a list."""
        try:
            decoded = canonical_decode(
                encoded_selector,
                maximum=MAX_SELECTOR_BYTES,
                validator=validate_selector,
                label="recovery-suite selector",
            )
        except AppssFormatError as exc:
            raise RecoverySuiteError("invalid recovery-suite selection") from exc
        selection = RecoverySuiteSelection(
            suite_id=decoded["suite_id"],
            profile_id=decoded["profile_id"],
            threshold=ThresholdParameters(k=decoded["k"], n=decoded["n"]),
            holder_ids=tuple(decoded["holder_ids"]),
            authorizer_ids=tuple(decoded["authorizer_ids"]),
            authorization_quorum=decoded["authorization_quorum"],
        )
        return selection, self.for_authenticated_descriptor(selection.suite_id)

    @staticmethod
    def selector_bytes(
        *,
        suite_id: str,
        threshold: ThresholdParameters | None = None,
        selector_version: str | None = None,
        authorizer_ids: tuple[int, ...] = (1, 2, 3, 4, 5),
        authorization_quorum: int = 4,
    ) -> bytes:
        selected_threshold = (
            ThresholdParameters(k=2, n=3) if threshold is None else threshold
        )
        selected_version = (
            RECOVERY_SUITE_SELECTOR
            if selected_threshold == ThresholdParameters(k=2, n=3)
            else RECOVERY_SUITE_SELECTOR_V2
        )
        if selector_version is not None:
            selected_version = selector_version
        profiles = {
            (YI_SUITE_ID, 2, 3): YI_PROFILE_2_OF_3,
            (YI_SUITE_ID, 3, 5): YI_PROFILE_3_OF_5,
            (APPSS_SUITE_ID, 2, 3): APPSS_PROFILE_2_OF_3,
            (APPSS_SUITE_ID, 3, 5): APPSS_PROFILE_3_OF_5,
        }
        profile_id = profiles.get(
            (suite_id, selected_threshold.k, selected_threshold.n)
        )
        if profile_id is None:
            raise RecoverySuiteError("unsupported recovery suite profile")
        if selected_version not in {
            RECOVERY_SUITE_SELECTOR,
            RECOVERY_SUITE_SELECTOR_V2,
        }:
            raise RecoverySuiteError("unsupported selector version")
        value = {
            "authorization_quorum": authorization_quorum,
            "authorizer_ids": list(authorizer_ids),
            "holder_ids": list(range(1, selected_threshold.n + 1)),
            "k": selected_threshold.k,
            "n": selected_threshold.n,
            "profile_id": profile_id,
            "suite_id": suite_id,
            "version": selected_version,
        }
        try:
            return encode_checked(
                value,
                maximum=MAX_SELECTOR_BYTES,
                validator=validate_selector,
                label="recovery-suite selector",
            )
        except AppssFormatError as exc:
            raise RecoverySuiteError("invalid recovery-suite selection") from exc


__all__ = ["RecoverySuiteRegistry", "RecoverySuiteSelection"]
