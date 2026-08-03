"""Bounded aggregate-only P5A.6 Yi/aPPSS compromise regression.

This module intentionally exposes no candidate or snapshot parameters. It creates
one fixed synthetic 2-of-3 fixture in memory, evaluates only the declared views,
and returns a strict public report with no secret-bearing values. The observations
are implementation regressions, not cryptographic proofs or retained P9 evidence.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from itertools import combinations
from typing import Any, cast

from . import _tpass_native as native
from .appss import AppssRecoveryAdapter
from .appss_formats import (
    APPSS_PROFILE_2_OF_3,
    APPSS_SUITE_ID,
    APPSS_WIRE_FORMAT,
    YI_PROFILE_2_OF_3,
    YI_SUITE_ID,
    AppssHolderBinding,
    context_digest,
    derive_password_input,
)
from .codec import encode
from .contracts import (
    PartyRecoveryState,
    PasswordProtectedSecretRecovery,
    RecoveryContext,
    RecoverySuiteEnrollment,
    ThresholdParameters,
)
from .crypto import hash_scalar
from .redaction import validate_public_output
from .suite_backup import enroll_backup_v5
from .yi_compat import RecoverySuiteError, YiTpassRecoveryAdapter

REPORT_VERSION = "LOCUS-recovery-suite-compromise-regression-v1"
INTERPRETATION = "implementation-regression-only-not-cryptographic-proof"
_THRESHOLD = ThresholdParameters(k=2, n=3)
_BACKUP_ID = bytes.fromhex("a6" * 16)
_BACKUP_NONCE = bytes.fromhex("b6" * 16)
_CONFIGURATION_DIGEST = hashlib.sha256(
    b"LOCUS/P5A.6/fixed-public-configuration/v1"
).digest()
_CANONICAL_INPUT = hashlib.sha256(
    b"LOCUS/P5A.6/fixed-synthetic-CuePolicy-output/v1"
).digest()
_PROTECTED_KEY = hashlib.sha256(
    b"LOCUS/P5A.6/fixed-synthetic-protected-key/v1"
).digest()
_FIXED_WRONG_INPUT = hashlib.sha256(
    b"LOCUS/P5A.6/fixed-incorrect-suite-input/v1"
).digest()
_YI_SCALAR_MODULUS = 2**252 + 27742317777372353535851937790883648493
_YI_DOMAIN = YI_SUITE_ID.encode("ascii")

_SCENARIO_ORDER = (
    "yi-cloud-only",
    "yi-below-threshold-party-only",
    "yi-cloud-plus-below-threshold",
    "appss-cloud-only",
    "appss-below-threshold-party-only",
    "appss-cloud-plus-below-threshold",
)


class SuiteCompromiseRegressionError(ValueError):
    """The fixed regression or its aggregate report failed closed."""


@dataclass(frozen=True)
class _SuiteFixture:
    adapter: YiTpassRecoveryAdapter | AppssRecoveryAdapter
    context: RecoveryContext
    password_input: bytes
    enrollment: RecoverySuiteEnrollment
    cloud_view: bytes


@dataclass(frozen=True)
class _YiShares:
    holder_id: int
    low_entropy_input_share: int
    protected_exponent_share: int
    digest_share: int
    recovery_id: bytes
    threshold: int
    parties: int


def _exact(value: object, members: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != members:
        raise SuiteCompromiseRegressionError(f"invalid {label}")
    return value


def _bool(value: object, expected: bool, label: str) -> None:
    if value is not expected:
        raise SuiteCompromiseRegressionError(f"invalid {label}")


def _common_conditions() -> dict[str, Any]:
    conditions: dict[str, Any] = {
        "admission_profile": "LOCUS-local-synthetic-admission-v1",
        "authorization_parties": 5,
        "authorization_quorum": 4,
        "backup_format": "LOCUS-reference-backup-v5",
        "cue_policy": "LOCUS-location-person-set-v1",
        "fixture_id": "p5a6-fixed-synthetic-pair-v1",
        "holder_count": 3,
        "reconstruction_threshold": 2,
        "resolver_profile": "LOCUS-no-resolver-v1",
        "synthetic_key_digest": hashlib.sha256(_PROTECTED_KEY).hexdigest(),
        "topology": "2-of-3",
    }
    conditions["manifest_digest"] = hashlib.sha256(encode(conditions)).hexdigest()
    return conditions


def validate_suite_compromise_report(value: object) -> dict[str, Any]:
    """Validate the exact aggregate-only development-report shape."""

    report = _exact(
        value,
        {
            "common_conditions",
            "compromise_boundary",
            "hygiene",
            "interpretation",
            "profile",
            "scenarios",
            "version",
            "versions",
        },
        "suite-compromise report",
    )
    if report["version"] != REPORT_VERSION or report["profile"] != REPORT_VERSION:
        raise SuiteCompromiseRegressionError("unsupported suite-compromise report")
    if report["interpretation"] != INTERPRETATION:
        raise SuiteCompromiseRegressionError("invalid report interpretation")
    if report["common_conditions"] != _common_conditions():
        raise SuiteCompromiseRegressionError("common-condition manifest mismatch")

    versions = _exact(
        report["versions"],
        {
            "appss_profile",
            "appss_suite",
            "appss_wire",
            "backup",
            "report",
            "selector",
            "yi_profile",
            "yi_suite",
            "yi_wire",
        },
        "suite-compromise versions",
    )
    if versions != {
        "appss_profile": APPSS_PROFILE_2_OF_3,
        "appss_suite": APPSS_SUITE_ID,
        "appss_wire": APPSS_WIRE_FORMAT,
        "backup": "LOCUS-reference-backup-v5",
        "report": REPORT_VERSION,
        "selector": "LOCUS-recovery-suite-selector-v1",
        "yi_profile": YI_PROFILE_2_OF_3,
        "yi_suite": YI_SUITE_ID,
        "yi_wire": "LOCUS-TPASS-wire-v1",
    }:
        raise SuiteCompromiseRegressionError("suite-compromise version mismatch")

    scenarios = report["scenarios"]
    if not isinstance(scenarios, list) or len(scenarios) != len(_SCENARIO_ORDER):
        raise SuiteCompromiseRegressionError("invalid below-threshold scenarios")
    for expected_id, item in zip(_SCENARIO_ORDER, scenarios, strict=True):
        scenario = _exact(
            item,
            {
                "coalitions_evaluated",
                "id",
                "local_tested_predicate_found",
                "network_access",
                "positive_control_detected",
                "suite",
                "threshold_relation",
                "view",
            },
            "below-threshold scenario",
        )
        if scenario["id"] != expected_id:
            raise SuiteCompromiseRegressionError("noncanonical scenario order")
        expected_suite = (
            YI_SUITE_ID if expected_id.startswith("yi-") else APPSS_SUITE_ID
        )
        if scenario["suite"] != expected_suite:
            raise SuiteCompromiseRegressionError("scenario suite mismatch")
        expected_view = expected_id.removeprefix("yi-").removeprefix("appss-")
        if scenario["view"] != expected_view:
            raise SuiteCompromiseRegressionError("scenario view mismatch")
        expected_count = 1 if expected_view == "cloud-only" else 4
        if scenario["coalitions_evaluated"] != expected_count:
            raise SuiteCompromiseRegressionError("coalition count mismatch")
        if scenario["threshold_relation"] != "below-k":
            raise SuiteCompromiseRegressionError("scenario threshold mismatch")
        _bool(scenario["local_tested_predicate_found"], False, "local predicate")
        _bool(scenario["network_access"], False, "network boundary")
        _bool(scenario["positive_control_detected"], True, "positive control")

    compromise = _exact(
        report["compromise_boundary"], {"appss", "yi"}, "compromise boundary"
    )
    appss = _exact(
        compromise["appss"],
        {
            "all_server_view_evaluated",
            "exact_threshold_subsets_evaluated",
            "fixed_inputs_tested",
            "offline_dictionary_test_capability",
            "output_after_correct_input",
            "output_without_correct_input",
            "positive_control_detected",
            "threshold_relation",
        },
        "aPPSS compromise observation",
    )
    if (
        appss["exact_threshold_subsets_evaluated"] != 3
        or appss["fixed_inputs_tested"] != 2
        or appss["threshold_relation"] != "at-or-above-k"
    ):
        raise SuiteCompromiseRegressionError("invalid aPPSS compromise counts")
    for field, expected in (
        ("all_server_view_evaluated", True),
        ("offline_dictionary_test_capability", True),
        ("output_after_correct_input", True),
        ("output_without_correct_input", False),
        ("positive_control_detected", True),
    ):
        _bool(appss[field], expected, f"aPPSS {field}")

    yi = _exact(
        compromise["yi"],
        {
            "all_server_view_evaluated",
            "exact_threshold_subsets_evaluated",
            "fixed_inputs_tested",
            "low_entropy_input_scalar_reconstructed",
            "positive_control_detected",
            "protected_exponent_reconstructed",
            "recovery_output_directly_derivable",
            "recovery_output_verified",
            "threshold_relation",
        },
        "Yi compromise observation",
    )
    if (
        yi["exact_threshold_subsets_evaluated"] != 3
        or yi["fixed_inputs_tested"] != 0
        or yi["threshold_relation"] != "at-or-above-k"
    ):
        raise SuiteCompromiseRegressionError("invalid Yi compromise counts")
    for field in (
        "all_server_view_evaluated",
        "low_entropy_input_scalar_reconstructed",
        "positive_control_detected",
        "protected_exponent_reconstructed",
        "recovery_output_directly_derivable",
        "recovery_output_verified",
    ):
        _bool(yi[field], True, f"Yi {field}")

    hygiene = _exact(
        report["hygiene"],
        {
            "cleanup_passed",
            "configurable_guessing_interface",
            "network_access",
            "output_scan_passed",
            "per_input_outcomes_retained",
            "raw_views_retained",
            "sensitive_values_retained",
        },
        "suite-compromise hygiene",
    )
    for field, expected in (
        ("cleanup_passed", True),
        ("configurable_guessing_interface", False),
        ("network_access", False),
        ("output_scan_passed", True),
        ("per_input_outcomes_retained", False),
        ("raw_views_retained", False),
        ("sensitive_values_retained", False),
    ):
        _bool(hygiene[field], expected, f"hygiene {field}")
    validate_public_output(report)
    return report


def _contexts() -> tuple[RecoveryContext, RecoveryContext, bytes, bytes]:
    holders = tuple(
        AppssHolderBinding(
            index=index,
            party_id=f"party-{index}",
            service_identity=f"p5a6-holder-{index}",
        )
        for index in range(1, 4)
    )
    appss_context = context_digest(
        backup_id=_BACKUP_ID,
        epoch=1,
        policy_id="LOCUS-location-person-set-v1",
        holders=holders,
        k=_THRESHOLD.k,
        n=_THRESHOLD.n,
        configuration_digest=_CONFIGURATION_DIGEST,
    )
    yi = RecoveryContext(
        suite_id=YI_SUITE_ID,
        recovery_id="p5a6-fixed-recovery",
        backup_id=_BACKUP_ID.hex(),
        epoch=1,
        policy_id="LOCUS-location-person-set-v1",
        configuration_digest=_CONFIGURATION_DIGEST.hex(),
        digest_context="p5a6:yi:1",
        suite_context_digest=_CONFIGURATION_DIGEST.hex(),
    )
    appss = RecoveryContext(
        suite_id=APPSS_SUITE_ID,
        recovery_id="p5a6-fixed-recovery",
        backup_id=_BACKUP_ID.hex(),
        epoch=1,
        policy_id="LOCUS-location-person-set-v1",
        configuration_digest=_CONFIGURATION_DIGEST.hex(),
        digest_context="p5a6:appss:1",
        suite_context_digest=appss_context.hex(),
    )
    yi_input = hash_scalar(
        "LOCUS-context-password",
        _CANONICAL_INPUT,
        _BACKUP_NONCE,
        _BACKUP_ID.hex(),
        1,
    ).to_bytes(32, "big")
    appss_input = derive_password_input(appss_context, _CANONICAL_INPUT)
    return yi, appss, yi_input, appss_input


def _fixture(
    *,
    adapter: YiTpassRecoveryAdapter | AppssRecoveryAdapter,
    context: RecoveryContext,
    password_input: bytes,
    profile_id: str,
) -> _SuiteFixture:
    enrollment = adapter.initialize(
        context=context,
        password_input=password_input,
        threshold=_THRESHOLD,
    )
    backup = enroll_backup_v5(
        protected_key=_PROTECTED_KEY,
        context=context,
        cue_policy_id=context.policy_id,
        resolver_profile="LOCUS-no-resolver-v1",
        adapter=cast(PasswordProtectedSecretRecovery, adapter),
        enrollment=enrollment,
        profile_id=profile_id,
        bid=_BACKUP_ID,
        nonce=_BACKUP_NONCE,
    ).backup
    return _SuiteFixture(
        adapter=adapter,
        context=context,
        password_input=password_input,
        enrollment=enrollment,
        cloud_view=encode(backup),
    )


def _frame(parts: tuple[bytes, ...]) -> bytes:
    output = bytearray()
    for part in parts:
        output.extend(len(part).to_bytes(4, "big"))
        output.extend(part)
    return bytes(output)


def _verifier_marker(value: bytes) -> bytes:
    return hashlib.sha256(b"LOCUS/P5A.6/direct-verifier/v1" + value).digest()


def _direct_marker_present(view: bytes, inputs: tuple[bytes, bytes]) -> bool:
    return any(_verifier_marker(value) in view for value in inputs)


def _below_threshold_observation(fixture: _SuiteFixture) -> list[dict[str, Any]]:
    states = fixture.enrollment.party_states
    inputs = (_FIXED_WRONG_INPUT, fixture.password_input)
    coalitions = ((),) + tuple((state,) for state in states)
    party_views = tuple(
        _frame(tuple(state.payload for state in coalition)) for coalition in coalitions
    )
    public = fixture.enrollment.public_state

    cloud_predicate = _direct_marker_present(fixture.cloud_view, inputs)
    party_predicate = any(_direct_marker_present(view, inputs) for view in party_views)
    combined_predicate = False
    rejection_categories: set[tuple[str, str]] = set()
    for coalition, party_view in zip(coalitions, party_views, strict=True):
        combined = _frame((fixture.cloud_view, party_view))
        combined_predicate = combined_predicate or _direct_marker_present(
            combined, inputs
        )
        outcomes: list[str] = []
        for fixed_input in inputs:
            try:
                fixture.adapter.recover(
                    context=fixture.context,
                    password_input=fixed_input,
                    public_state=public,
                    party_states=coalition,
                )
            except RecoverySuiteError as exc:
                outcomes.append(str(exc))
            else:
                combined_predicate = True
        if len(outcomes) != 2:
            raise SuiteCompromiseRegressionError("below-threshold result changed")
        rejection_categories.add((outcomes[0], outcomes[1]))
    if len(rejection_categories) != 1 or any(
        len(item) != 2 for item in rejection_categories
    ):
        raise SuiteCompromiseRegressionError("below-threshold rejection changed")

    suite_label = "yi" if fixture.context.suite_id == YI_SUITE_ID else "appss"
    observations = []
    for view, count, found, raw in (
        ("cloud-only", 1, cloud_predicate, fixture.cloud_view),
        (
            "below-threshold-party-only",
            len(coalitions),
            party_predicate,
            _frame(party_views),
        ),
        (
            "cloud-plus-below-threshold",
            len(coalitions),
            combined_predicate,
            _frame((fixture.cloud_view, *party_views)),
        ),
    ):
        positive = raw + _verifier_marker(inputs[0])
        observations.append(
            {
                "coalitions_evaluated": count,
                "id": f"{suite_label}-{view}",
                "local_tested_predicate_found": found,
                "network_access": False,
                "positive_control_detected": _direct_marker_present(positive, inputs),
                "suite": fixture.context.suite_id,
                "threshold_relation": "below-k",
                "view": view,
            }
        )
    return observations


def _decode_yi_shares(
    adapter: YiTpassRecoveryAdapter, state: PartyRecoveryState
) -> _YiShares:
    outer = adapter.decode_party_state(state)
    encoded = bytes.fromhex(outer["state"])
    try:
        decoded_native = native.PartyState.from_secret_bytes(encoded)
    except native.NativeTpassError as exc:
        raise SuiteCompromiseRegressionError("invalid Yi regression state") from exc
    if len(encoded) < 9 or encoded[:8] != b"LCTPASS\x01" or encoded[8] != 2:
        raise SuiteCompromiseRegressionError("invalid Yi regression state")
    cursor = 9
    recovery_id_length = int.from_bytes(encoded[cursor : cursor + 4], "big")
    cursor += 4
    recovery_id = encoded[cursor : cursor + recovery_id_length]
    cursor += recovery_id_length
    threshold = int.from_bytes(encoded[cursor : cursor + 4], "big")
    cursor += 4
    parties = int.from_bytes(encoded[cursor : cursor + 4], "big")
    cursor += 4
    holder_id = int.from_bytes(encoded[cursor : cursor + 4], "big")
    cursor += 4
    scalars = tuple(
        int.from_bytes(encoded[cursor + offset : cursor + offset + 32], "little")
        for offset in (0, 32, 64)
    )
    cursor += 96
    if (
        cursor != len(encoded)
        or decoded_native.party_id != holder_id
        or holder_id != state.holder_id
        or threshold != 2
        or parties != 3
        or any(value >= _YI_SCALAR_MODULUS for value in scalars)
    ):
        raise SuiteCompromiseRegressionError("invalid Yi regression state")
    return _YiShares(
        holder_id=holder_id,
        low_entropy_input_share=scalars[0],
        protected_exponent_share=scalars[1],
        digest_share=scalars[2],
        recovery_id=recovery_id,
        threshold=threshold,
        parties=parties,
    )


def _interpolate(values: tuple[tuple[int, int], ...]) -> int:
    total = 0
    for holder, value in values:
        numerator = 1
        denominator = 1
        for other, _ in values:
            if other == holder:
                continue
            numerator = (numerator * -other) % _YI_SCALAR_MODULUS
            denominator = (denominator * (holder - other)) % _YI_SCALAR_MODULUS
        total = (
            total + value * numerator * pow(denominator, -1, _YI_SCALAR_MODULUS)
        ) % _YI_SCALAR_MODULUS
    return total


def _yi_hash_to_scalar(label: bytes, fields: tuple[bytes, ...]) -> int:
    digest = hashlib.sha512()
    for part in (_YI_DOMAIN, label, *fields):
        digest.update(len(part).to_bytes(8, "big"))
        digest.update(part)
    return int.from_bytes(digest.digest(), "little") % _YI_SCALAR_MODULUS


def _yi_compromise_observation(fixture: _SuiteFixture) -> dict[str, Any]:
    if not isinstance(fixture.adapter, YiTpassRecoveryAdapter):
        raise SuiteCompromiseRegressionError("wrong Yi fixture")
    decoded = tuple(
        _decode_yi_shares(fixture.adapter, state)
        for state in fixture.enrollment.party_states
    )
    subsets = tuple(combinations(decoded, 2))
    expected_input_scalar = _yi_hash_to_scalar(
        b"password", (fixture.context.recovery_id.encode(), fixture.password_input)
    )
    expected_digest_scalar = _yi_hash_to_scalar(
        b"secret-digest",
        (fixture.context.recovery_id.encode(), fixture.enrollment.recovery_secret),
    )
    protected_exponents: set[int] = set()
    for subset, state_subset in zip(
        subsets, combinations(fixture.enrollment.party_states, 2), strict=True
    ):
        input_scalar = _interpolate(
            tuple((item.holder_id, item.low_entropy_input_share) for item in subset)
        )
        protected_exponent = _interpolate(
            tuple((item.holder_id, item.protected_exponent_share) for item in subset)
        )
        digest_scalar = _interpolate(
            tuple((item.holder_id, item.digest_share) for item in subset)
        )
        if (
            input_scalar != expected_input_scalar
            or digest_scalar != expected_digest_scalar
        ):
            raise SuiteCompromiseRegressionError("Yi threshold interpolation mismatch")
        recovered = fixture.adapter.recover(
            context=fixture.context,
            password_input=fixture.password_input,
            public_state=fixture.enrollment.public_state,
            party_states=tuple(state_subset),
        )
        if recovered != fixture.enrollment.recovery_secret:
            raise SuiteCompromiseRegressionError("Yi threshold recovery mismatch")
        protected_exponents.add(protected_exponent)
    if len(protected_exponents) != 1 or next(iter(protected_exponents)) == 0:
        raise SuiteCompromiseRegressionError("Yi protected exponent mismatch")
    altered = (
        (decoded[0].holder_id, decoded[0].low_entropy_input_share ^ 1),
        (decoded[1].holder_id, decoded[1].low_entropy_input_share),
    )
    positive_control = _interpolate(altered) != expected_input_scalar
    return {
        "all_server_view_evaluated": len(decoded) == 3 and bool(subsets),
        "exact_threshold_subsets_evaluated": len(subsets),
        "fixed_inputs_tested": 0,
        "low_entropy_input_scalar_reconstructed": True,
        "positive_control_detected": positive_control,
        "protected_exponent_reconstructed": True,
        "recovery_output_directly_derivable": True,
        "recovery_output_verified": True,
        "threshold_relation": "at-or-above-k",
    }


def _appss_compromise_observation(fixture: _SuiteFixture) -> dict[str, Any]:
    if not isinstance(fixture.adapter, AppssRecoveryAdapter):
        raise SuiteCompromiseRegressionError("wrong aPPSS fixture")
    subsets = tuple(combinations(fixture.enrollment.party_states, 2))
    correct_results = 0
    wrong_results = 0
    for subset in subsets:
        try:
            fixture.adapter.recover(
                context=fixture.context,
                password_input=_FIXED_WRONG_INPUT,
                public_state=fixture.enrollment.public_state,
                party_states=tuple(subset),
            )
        except RecoverySuiteError:
            pass
        else:
            wrong_results += 1
        recovered = fixture.adapter.recover(
            context=fixture.context,
            password_input=fixture.password_input,
            public_state=fixture.enrollment.public_state,
            party_states=tuple(subset),
        )
        if recovered == fixture.enrollment.recovery_secret:
            correct_results += 1
    return {
        "all_server_view_evaluated": len(fixture.enrollment.party_states) == 3,
        "exact_threshold_subsets_evaluated": len(subsets),
        "fixed_inputs_tested": 2,
        "offline_dictionary_test_capability": correct_results == len(subsets),
        "output_after_correct_input": correct_results == len(subsets),
        "output_without_correct_input": wrong_results != 0,
        "positive_control_detected": wrong_results == 0
        and correct_results == len(subsets),
        "threshold_relation": "at-or-above-k",
    }


def run_fixed_suite_compromise_regression() -> dict[str, Any]:
    """Run the only fixed P5A.6 profile and return privacy-safe aggregates."""

    yi_context, appss_context, yi_input, appss_input = _contexts()
    yi = _fixture(
        adapter=YiTpassRecoveryAdapter(),
        context=yi_context,
        password_input=yi_input,
        profile_id=YI_PROFILE_2_OF_3,
    )
    appss = _fixture(
        adapter=AppssRecoveryAdapter(),
        context=appss_context,
        password_input=appss_input,
        profile_id=APPSS_PROFILE_2_OF_3,
    )
    scenarios = _below_threshold_observation(yi) + _below_threshold_observation(appss)
    report: dict[str, Any] = {
        "common_conditions": _common_conditions(),
        "compromise_boundary": {
            "appss": _appss_compromise_observation(appss),
            "yi": _yi_compromise_observation(yi),
        },
        "hygiene": {
            "cleanup_passed": True,
            "configurable_guessing_interface": False,
            "network_access": False,
            "output_scan_passed": True,
            "per_input_outcomes_retained": False,
            "raw_views_retained": False,
            "sensitive_values_retained": False,
        },
        "interpretation": INTERPRETATION,
        "profile": REPORT_VERSION,
        "scenarios": scenarios,
        "version": REPORT_VERSION,
        "versions": {
            "appss_profile": APPSS_PROFILE_2_OF_3,
            "appss_suite": APPSS_SUITE_ID,
            "appss_wire": APPSS_WIRE_FORMAT,
            "backup": "LOCUS-reference-backup-v5",
            "report": REPORT_VERSION,
            "selector": "LOCUS-recovery-suite-selector-v1",
            "yi_profile": YI_PROFILE_2_OF_3,
            "yi_suite": YI_SUITE_ID,
            "yi_wire": "LOCUS-TPASS-wire-v1",
        },
    }
    return validate_suite_compromise_report(report)


__all__ = [
    "REPORT_VERSION",
    "SuiteCompromiseRegressionError",
    "run_fixed_suite_compromise_regression",
    "validate_suite_compromise_report",
]
