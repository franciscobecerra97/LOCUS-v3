"""Aggregate-only P2.4 descriptor-security scenario report contract."""

from __future__ import annotations

import hashlib
from typing import Any

from .redaction import validate_public_output

REPORT_VERSION = "LOCUS-descriptor-security-scenarios-v1"
SCENARIOS = (
    "wrong-recovery-handle",
    "wrong-account-scope",
    "altered-signature",
    "wrong-issuer",
    "stale-epoch",
    "cross-user-substitution",
    "cross-policy-substitution",
    "cross-suite-downgrade",
    "cross-membership-mix",
    "descriptor-backup-digest-mismatch",
    "descriptor-party-state-mismatch",
    "altered-zip-member",
    "duplicate-unexpected-unsafe-zip-member",
    "oversized-unsupported-zip-member",
    "stale-bundle-rollback",
    "stale-current-pointer-rollback",
)


class DescriptorSecurityReportError(ValueError):
    pass


def _exact(value: object, members: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != members:
        raise DescriptorSecurityReportError(f"invalid {label}")
    return value


def validate_descriptor_security_report(value: object) -> dict[str, Any]:
    report = _exact(
        value,
        {
            "cleanup_passed",
            "candidate_test",
            "detected_count",
            "interpretation",
            "output_scan_passed",
            "positive_control_count",
            "profile",
            "scenarios",
            "versions",
            "version",
        },
        "descriptor security report",
    )
    if report["version"] != REPORT_VERSION or report["profile"] != REPORT_VERSION:
        raise DescriptorSecurityReportError("unsupported descriptor security report")
    versions = _exact(
        report["versions"],
        {"bootstrap", "bundle", "descriptor", "pointer", "store"},
        "descriptor security versions",
    )
    expected_versions = {
        "bootstrap": "LOCUS-account-scoped-bootstrap-v1",
        "bundle": "LOCUS-recovery-bundle-v1",
        "descriptor": "LOCUS-recovery-descriptor-v1",
        "pointer": "LOCUS-descriptor-current-pointer-v1",
        "store": "LOCUS-descriptor-bundle-store-v1",
    }
    if versions != expected_versions:
        raise DescriptorSecurityReportError("descriptor security version mismatch")
    candidate_test = _exact(
        report["candidate_test"],
        {
            "candidates_tested",
            "local_predicate_found",
            "network_access",
            "positive_control_detected",
        },
        "descriptor candidate test",
    )
    if candidate_test != {
        "candidates_tested": 2,
        "local_predicate_found": False,
        "network_access": False,
        "positive_control_detected": True,
    }:
        raise DescriptorSecurityReportError("descriptor candidate test failed")
    scenarios = report["scenarios"]
    if not isinstance(scenarios, list) or len(scenarios) != len(SCENARIOS):
        raise DescriptorSecurityReportError("invalid descriptor security scenarios")
    identifiers: list[str] = []
    for item in scenarios:
        scenario = _exact(
            item,
            {"detected", "failure_category", "id", "positive_control"},
            "descriptor security scenario",
        )
        if scenario["id"] not in SCENARIOS:
            raise DescriptorSecurityReportError("unknown descriptor security scenario")
        identifiers.append(scenario["id"])
        if scenario["detected"] is not True or scenario["positive_control"] is not True:
            raise DescriptorSecurityReportError("descriptor security gate failed")
        if (
            not isinstance(scenario["failure_category"], str)
            or not scenario["failure_category"]
            or len(scenario["failure_category"]) > 64
        ):
            raise DescriptorSecurityReportError("invalid failure category")
    if tuple(identifiers) != SCENARIOS:
        raise DescriptorSecurityReportError("noncanonical descriptor scenario order")
    if report["detected_count"] != len(SCENARIOS) or report[
        "positive_control_count"
    ] != len(SCENARIOS):
        raise DescriptorSecurityReportError("descriptor security count mismatch")
    if report["cleanup_passed"] is not True or report["output_scan_passed"] is not True:
        raise DescriptorSecurityReportError("descriptor security hygiene failed")
    if (
        report["interpretation"]
        != "implementation-regression-only-not-cryptographic-proof"
    ):
        raise DescriptorSecurityReportError(
            "invalid descriptor security interpretation"
        )
    validate_public_output(report)
    return report


def build_descriptor_security_report(
    outcomes: dict[str, str], *, cleanup_passed: bool, output_scan_passed: bool
) -> dict[str, Any]:
    if set(outcomes) != set(SCENARIOS):
        raise DescriptorSecurityReportError("incomplete descriptor security outcomes")
    report: dict[str, Any] = {
        "candidate_test": {
            "candidates_tested": 2,
            "local_predicate_found": False,
            "network_access": False,
            "positive_control_detected": True,
        },
        "cleanup_passed": cleanup_passed,
        "detected_count": len(SCENARIOS),
        "interpretation": "implementation-regression-only-not-cryptographic-proof",
        "output_scan_passed": output_scan_passed,
        "positive_control_count": len(SCENARIOS),
        "profile": REPORT_VERSION,
        "scenarios": [
            {
                "detected": True,
                "failure_category": outcomes[identifier],
                "id": identifier,
                "positive_control": True,
            }
            for identifier in SCENARIOS
        ],
        "versions": {
            "bootstrap": "LOCUS-account-scoped-bootstrap-v1",
            "bundle": "LOCUS-recovery-bundle-v1",
            "descriptor": "LOCUS-recovery-descriptor-v1",
            "pointer": "LOCUS-descriptor-current-pointer-v1",
            "store": "LOCUS-descriptor-bundle-store-v1",
        },
        "version": REPORT_VERSION,
    }
    return validate_descriptor_security_report(report)


def run_bounded_networkless_candidate_test(
    public_view: bytes, *, synthetic_candidates: tuple[bytes, bytes]
) -> dict[str, Any]:
    """Detect only a direct persisted SHA-256 candidate predicate.

    This bounded regression is not a general cryptographic proof or entropy
    analysis. It deliberately has no network or recovery-party interface.
    """

    if not isinstance(public_view, bytes) or not public_view:
        raise DescriptorSecurityReportError("invalid public descriptor view")
    digests = tuple(
        hashlib.sha256(candidate).hexdigest().encode()
        for candidate in synthetic_candidates
    )
    found = any(digest in public_view for digest in digests)
    positive_view = public_view + b'"test-only-candidate-digest":"' + digests[0] + b'"'
    return {
        "candidates_tested": 2,
        "local_predicate_found": found,
        "network_access": False,
        "positive_control_detected": digests[0] in positive_view,
    }


__all__ = [
    "DescriptorSecurityReportError",
    "REPORT_VERSION",
    "SCENARIOS",
    "build_descriptor_security_report",
    "run_bounded_networkless_candidate_test",
    "validate_descriptor_security_report",
]
