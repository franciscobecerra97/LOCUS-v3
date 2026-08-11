"""Owner-approved P6.3 paired deployment controls.

These profiles define comparison controls, not cryptographic suites or retained
evidence.  Each arm still authenticates exactly one suite through its selector.
"""

from __future__ import annotations

from dataclasses import dataclass

from .appss_formats import APPSS_SUITE_ID, YI_SUITE_ID
from .contracts import ThresholdParameters
from .recovery_suite_registry import RecoverySuiteRegistry, RecoverySuiteSelection

PAIRED_DEPLOYMENT_2_OF_3 = "LOCUS-paired-suite-deployment-2of3-v1"
PAIRED_DEPLOYMENT_3_OF_5 = "LOCUS-paired-suite-deployment-3of5-v1"


@dataclass(frozen=True)
class PairedDeploymentProfile:
    profile_id: str
    threshold: ThresholdParameters
    authorizer_ids: tuple[int, ...] = (1, 2, 3, 4, 5)
    authorization_quorum: int = 4
    cue_policy_id: str = "LOCUS-canonical-email-set-v1"
    resolver_profile_id: str = "LOCUS-no-resolver-v1"
    admission_profile_id: str = "LOCUS-local-synthetic-admission-v1"
    storage_profile_id: str = "LOCUS-storage-provider-filesystem-v1"
    network_schedule: tuple[str, ...] = (
        "authorize-exact-4-of-5",
        "contact-exact-recovery-threshold",
        "recover-one-suite",
        "open-reference-backup-v6",
    )
    measurements: tuple[str, ...] = (
        "enrollment-wall-time",
        "recovery-wall-time",
        "request-response-bytes",
        "persistent-bytes-by-role",
        "availability-outcome",
    )

    def selector_for(self, suite_id: str) -> bytes:
        if suite_id not in {YI_SUITE_ID, APPSS_SUITE_ID}:
            raise ValueError("unsupported paired-deployment suite")
        return RecoverySuiteRegistry.selector_bytes(
            suite_id=suite_id,
            threshold=self.threshold,
            authorizer_ids=self.authorizer_ids,
            authorization_quorum=self.authorization_quorum,
        )

    def validate_selection(self, selection: RecoverySuiteSelection) -> None:
        if (
            selection.threshold != self.threshold
            or selection.holder_ids != tuple(range(1, self.threshold.n + 1))
            or selection.authorizer_ids != self.authorizer_ids
            or selection.authorization_quorum != self.authorization_quorum
        ):
            raise ValueError("selection does not match paired deployment")


PAIRED_PROFILES = {
    PAIRED_DEPLOYMENT_2_OF_3: PairedDeploymentProfile(
        profile_id=PAIRED_DEPLOYMENT_2_OF_3,
        threshold=ThresholdParameters(k=2, n=3),
    ),
    PAIRED_DEPLOYMENT_3_OF_5: PairedDeploymentProfile(
        profile_id=PAIRED_DEPLOYMENT_3_OF_5,
        threshold=ThresholdParameters(k=3, n=5),
    ),
}


def paired_profile(profile_id: str) -> PairedDeploymentProfile:
    try:
        return PAIRED_PROFILES[profile_id]
    except (KeyError, TypeError) as exc:
        raise ValueError("unsupported paired deployment profile") from exc


def paired_profile_for_selection(
    selection: RecoverySuiteSelection,
) -> PairedDeploymentProfile:
    """Return the unique approved deployment profile for an authenticated selector."""

    matches: list[PairedDeploymentProfile] = []
    for profile in PAIRED_PROFILES.values():
        try:
            profile.validate_selection(selection)
        except ValueError:
            continue
        matches.append(profile)
    if len(matches) != 1:
        raise ValueError("selection does not identify one paired deployment profile")
    return matches[0]


__all__ = [
    "PAIRED_DEPLOYMENT_2_OF_3",
    "PAIRED_DEPLOYMENT_3_OF_5",
    "PAIRED_PROFILES",
    "PairedDeploymentProfile",
    "paired_profile",
    "paired_profile_for_selection",
]
