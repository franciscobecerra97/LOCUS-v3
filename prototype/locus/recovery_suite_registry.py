"""Exact recovery-suite registry and no-fallback selector dispatch."""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from .appss import AppssRecoveryAdapter
from .appss_formats import (
    APPSS_PROFILE_2_OF_3,
    APPSS_SUITE_ID,
    MAX_SELECTOR_BYTES,
    RECOVERY_SUITE_SELECTOR,
    YI_PROFILE_2_OF_3,
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
        authorizer_ids: tuple[int, ...] = (1, 2, 3, 4, 5),
        authorization_quorum: int = 4,
    ) -> bytes:
        profile_id = {
            YI_SUITE_ID: YI_PROFILE_2_OF_3,
            APPSS_SUITE_ID: APPSS_PROFILE_2_OF_3,
        }.get(suite_id)
        if profile_id is None:
            raise RecoverySuiteError("unsupported recovery suite")
        value = {
            "authorization_quorum": authorization_quorum,
            "authorizer_ids": list(authorizer_ids),
            "holder_ids": [1, 2, 3],
            "k": 2,
            "n": 3,
            "profile_id": profile_id,
            "suite_id": suite_id,
            "version": RECOVERY_SUITE_SELECTOR,
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
