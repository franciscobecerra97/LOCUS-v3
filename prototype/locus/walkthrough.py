"""Synthetic-only, in-process educational walkthrough of the LOCUS protocol."""

from __future__ import annotations

import base64
import binascii
import json
from collections.abc import Callable, Sequence
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from . import _tpass_native as native
from .codec import encoded_size
from .core import SECURITY_POLICY_VERSION, backup_associated_data, derive_wrap_key
from .crypto import CryptoError, hash_bytes, open_sealed, random_bytes, seal
from .cue_policy import canonical_recovery_input
from .deployed_profile import BACKUP_VERSION, CONTEXT_POLICY_VERSION
from .object_store import backup_digest
from .redaction import validate_public_output

WALKTHROUGH_VERSION = "LOCUS-in-process-walkthrough-v1"
TPASS_BACKEND = "yi-zk-ristretto255-native-v1"
TPASS_ENCODING = "LOCUS-TPASS-wire-v1"
TPASS_HOLDERS = 3
TPASS_THRESHOLD = 2
ATTEMPT_BUDGET = 3

InputFunction = Callable[[str], str]
OutputFunction = Callable[[str], None]


class WalkthroughError(Exception):
    """The bounded educational walkthrough cannot continue."""


@dataclass(frozen=True)
class CatalogEntry:
    identifier: int
    label: str
    record: dict[str, dict[str, str]]


@dataclass(repr=False)
class WalkthroughEnrollment:
    """Secret-bearing in-memory state; never serialize or print this object."""

    cloud_backup: dict[str, Any]
    holder_material: tuple[Any, ...]
    recovery_identifier: bytes
    expected_key_digest: bytes
    canonical_input_bytes: int
    attempts: int = 0
    attempt_budget: int = ATTEMPT_BUDGET


@dataclass(frozen=True)
class WalkthroughRecovery:
    success: bool
    attempt_number: int
    attempts_remaining: int
    selected_holders: tuple[int, ...]

    def public_report(self) -> dict[str, object]:
        report: dict[str, object] = {
            "artifact": WALKTHROUGH_VERSION,
            "attempt_number": self.attempt_number,
            "attempts_remaining": self.attempts_remaining,
            "outcome": "success" if self.success else "generic-rejection",
            "selected_holders": list(self.selected_holders),
            "stage": "recovery",
            "status": "complete",
            "threshold": TPASS_THRESHOLD,
        }
        validate_public_output(report)
        return report


_CATALOG = (
    CatalogEntry(
        1,
        "Fictional observatory + synthetic contact Alpha",
        {
            "location": {"latitude": "10.1001", "longitude": "20.1001"},
            "person": {"type": "email", "value": "alpha@example.org"},
        },
    ),
    CatalogEntry(
        2,
        "Fictional library + synthetic contact Beta",
        {
            "location": {"latitude": "11.2002", "longitude": "21.2002"},
            "person": {"type": "email", "value": "beta@example.org"},
        },
    ),
    CatalogEntry(
        3,
        "Fictional garden + synthetic contact Gamma",
        {
            "location": {"latitude": "12.3003", "longitude": "22.3003"},
            "person": {"type": "email", "value": "gamma@example.org"},
        },
    ),
    CatalogEntry(
        4,
        "Fictional museum + synthetic contact Delta",
        {
            "location": {"latitude": "13.4004", "longitude": "23.4004"},
            "person": {"type": "email", "value": "delta@example.org"},
        },
    ),
    CatalogEntry(
        5,
        "Fictional station + synthetic contact Epsilon",
        {
            "location": {"latitude": "14.5005", "longitude": "24.5005"},
            "person": {"type": "email", "value": "epsilon@example.org"},
        },
    ),
)
_CATALOG_BY_ID = {entry.identifier: entry for entry in _CATALOG}


def catalog_labels() -> tuple[tuple[int, str], ...]:
    """Return display-safe aliases without returning canonical cue material."""

    return tuple((entry.identifier, entry.label) for entry in _CATALOG)


def parse_identifiers(
    raw_value: str,
    *,
    expected_count: int,
    allowed: Sequence[int],
    default: tuple[int, ...] | None = None,
) -> tuple[int, ...]:
    """Parse one bounded comma-separated selection."""

    text = raw_value.strip()
    if len(text) > 64:
        raise WalkthroughError("selection input is too long")
    if not text and default is not None:
        return default
    fields = [field.strip() for field in text.split(",")]
    if len(fields) != expected_count or any(
        not field.isascii() or not field.isdecimal() for field in fields
    ):
        raise WalkthroughError(f"select exactly {expected_count} numbered entries")
    identifiers = tuple(int(field) for field in fields)
    if len(set(identifiers)) != expected_count:
        raise WalkthroughError("selections must be distinct")
    allowed_set = set(allowed)
    if any(identifier not in allowed_set for identifier in identifiers):
        raise WalkthroughError("selection is outside the displayed catalog")
    return identifiers


def _selected_records(identifiers: Sequence[int]) -> list[dict[str, Any]]:
    if len(identifiers) != 3 or len(set(identifiers)) != 3:
        raise WalkthroughError("exactly three distinct fictional pairs are required")
    try:
        return [
            deepcopy(_CATALOG_BY_ID[identifier].record) for identifier in identifiers
        ]
    except KeyError as exc:
        raise WalkthroughError("selection is outside the fictional catalog") from exc


def _base64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _decode_base64url(value: object) -> bytes:
    if not isinstance(value, str) or not value or not value.isascii():
        raise WalkthroughError("educational backup is unavailable")
    try:
        return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    except (ValueError, binascii.Error) as exc:
        raise WalkthroughError("educational backup is unavailable") from exc


def enroll_walkthrough(identifiers: Sequence[int]) -> WalkthroughEnrollment:
    """Enroll one generated test key using the exact three-pair cue policy."""

    recovery_input = canonical_recovery_input(_selected_records(identifiers))
    bid = random_bytes(16).hex()
    recovery_identifier = b"LOCUS-compose-recovery-v1:" + bytes.fromhex(bid)
    try:
        parameters, holder_material, group_secret = native.setup(
            recovery_identifier,
            recovery_input,
            TPASS_THRESHOLD,
            TPASS_HOLDERS,
        )
    except native.NativeTpassError as exc:
        raise WalkthroughError("educational enrollment is unavailable") from exc

    nonce = random_bytes(16).hex()
    protected_key = random_bytes(32)
    backup: dict[str, Any] = {
        "version": BACKUP_VERSION,
        "bid": bid,
        "epoch": 1,
        "nonce": nonce,
        "tpass_public_params": {
            "backend": TPASS_BACKEND,
            "encoding": TPASS_ENCODING,
            "parameters": _base64url(bytes(parameters.to_bytes())),
            "threshold": TPASS_THRESHOLD,
            "parties": TPASS_HOLDERS,
        },
        "context_policy": {"version": CONTEXT_POLICY_VERSION},
        "security_policy": {
            "version": SECURITY_POLICY_VERSION,
            "max_attempts": ATTEMPT_BUDGET,
            "cooldown_seconds": 0,
        },
    }
    backup["ciphertext"] = seal(
        derive_wrap_key(bytes(group_secret), bid, 1, nonce),
        protected_key,
        aad=backup_associated_data(backup),
    )
    backup["digest"] = backup_digest(backup)
    return WalkthroughEnrollment(
        cloud_backup=backup,
        holder_material=tuple(holder_material),
        recovery_identifier=recovery_identifier,
        expected_key_digest=hash_bytes(
            "LOCUS/walkthrough-key-check/v1",
            protected_key,
        ),
        canonical_input_bytes=len(recovery_input),
    )


def enrollment_report(enrollment: WalkthroughEnrollment) -> dict[str, object]:
    """Return a privacy-safe description of the in-memory enrollment."""

    report: dict[str, object] = {
        "artifact": WALKTHROUGH_VERSION,
        "backend": TPASS_BACKEND,
        "backup_version": BACKUP_VERSION,
        "canonical_input_bytes": enrollment.canonical_input_bytes,
        "encrypted_backup_bytes": encoded_size(enrollment.cloud_backup),
        "holder_count": len(enrollment.holder_material),
        "holder_record_bytes": [
            len(bytes(material.to_secret_bytes()))
            for material in enrollment.holder_material
        ],
        "logical_separation": {
            "client_material": "ephemeral",
            "cloud_material": "encrypted-backup-only",
            "holder_material": "one-independent-record-each",
        },
        "selected_pairs": 3,
        "stage": "enrollment",
        "status": "complete",
        "threshold": TPASS_THRESHOLD,
    }
    validate_public_output(report)
    return report


def recover_walkthrough(
    enrollment: WalkthroughEnrollment,
    identifiers: Sequence[int],
    selected_holders: Sequence[int],
) -> WalkthroughRecovery:
    """Run one counted native recovery and return only a generic outcome."""

    if enrollment.attempts >= enrollment.attempt_budget:
        raise WalkthroughError("the educational attempt budget is exhausted")
    holder_ids = tuple(selected_holders)
    if (
        len(holder_ids) != TPASS_THRESHOLD
        or len(set(holder_ids)) != TPASS_THRESHOLD
        or any(
            identifier < 1 or identifier > TPASS_HOLDERS for identifier in holder_ids
        )
    ):
        raise WalkthroughError("select exactly two distinct TPASS holders")

    recovery_input = canonical_recovery_input(_selected_records(identifiers))
    enrollment.attempts += 1
    success = False
    try:
        encoded_parameters = enrollment.cloud_backup["tpass_public_params"][
            "parameters"
        ]
        parameters = native.PublicParameters.from_bytes(
            _decode_base64url(encoded_parameters)
        )
        session = native.begin_recovery(
            parameters,
            enrollment.recovery_identifier,
            recovery_input,
        )
        request = bytes(session.request_bytes())
        materials = [
            enrollment.holder_material[identifier - 1] for identifier in holder_ids
        ]
        commitments: list[bytes] = []
        ephemerals: list[Any] = []
        for material in materials:
            commitment, ephemeral = native.prepare_commitment(
                parameters,
                request,
                list(holder_ids),
                material,
            )
            commitments.append(bytes(commitment))
            ephemerals.append(ephemeral)
        responses = [
            bytes(
                native.verify_and_respond(
                    parameters,
                    request,
                    list(holder_ids),
                    material,
                    ephemeral,
                    commitments,
                )
            )
            for material, ephemeral in zip(materials, ephemerals, strict=True)
        ]
        gateway = native.aggregate_responses(
            parameters,
            request,
            list(holder_ids),
            commitments,
            responses,
        )
        group_secret = native.finish_recovery(parameters, session, gateway)
        restored_key = open_sealed(
            derive_wrap_key(
                bytes(group_secret),
                enrollment.cloud_backup["bid"],
                enrollment.cloud_backup["epoch"],
                enrollment.cloud_backup["nonce"],
            ),
            enrollment.cloud_backup["ciphertext"],
            aad=backup_associated_data(enrollment.cloud_backup),
        )
        success = (
            hash_bytes("LOCUS/walkthrough-key-check/v1", restored_key)
            == enrollment.expected_key_digest
        )
    except (native.NativeTpassError, CryptoError, WalkthroughError):
        success = False

    return WalkthroughRecovery(
        success=success,
        attempt_number=enrollment.attempts,
        attempts_remaining=enrollment.attempt_budget - enrollment.attempts,
        selected_holders=holder_ids,
    )


def _emit(report: dict[str, object], output: OutputFunction) -> None:
    validate_public_output(report)
    output(json.dumps(report, indent=2, sort_keys=True))


def _prompt_identifiers(
    *,
    prompt: str,
    expected_count: int,
    allowed: Sequence[int],
    default: tuple[int, ...],
    input_function: InputFunction,
    output: OutputFunction,
) -> tuple[int, ...] | None:
    while True:
        try:
            raw_value = input_function(prompt)
        except (EOFError, KeyboardInterrupt):
            output("Walkthrough cancelled; no protocol material was retained.")
            return None
        try:
            return parse_identifiers(
                raw_value,
                expected_count=expected_count,
                allowed=allowed,
                default=default,
            )
        except WalkthroughError as exc:
            output(f"Invalid selection: {exc}.")


def _prompt_retry(input_function: InputFunction, output: OutputFunction) -> bool | None:
    while True:
        try:
            value = input_function("Try another recovery selection? [y/N]: ")
        except (EOFError, KeyboardInterrupt):
            output("Walkthrough cancelled; no protocol material was retained.")
            return None
        normalized = value.strip().casefold()
        if normalized in {"", "n", "no"}:
            return False
        if normalized in {"y", "yes"}:
            return True
        output("Please enter y or n.")


def run_interactive(
    *,
    input_function: InputFunction = input,
    output: OutputFunction = print,
) -> int:
    """Run the bounded educational walkthrough without writing protocol state."""

    output("LOCUS synthetic in-process walkthrough")
    output(
        "Use only the numbered fictional choices below. "
        "Do not enter real people, places, accounts, or key material."
    )
    output(
        "This demonstrates the paper-facing cue mapping and native 2-of-3 TPASS "
        "flow without networking, durable ledgers, or independent services."
    )
    output("")
    output("Fictional recovery-pair catalog:")
    for identifier, label in catalog_labels():
        output(f"  {identifier}. {label}")

    enrollment_ids = _prompt_identifiers(
        prompt="Choose three enrollment pairs [1,2,3]: ",
        expected_count=3,
        allowed=tuple(_CATALOG_BY_ID),
        default=(1, 2, 3),
        input_function=input_function,
        output=output,
    )
    if enrollment_ids is None:
        return 1
    output("")
    output("[1/4] Canonicalizing the three selected fictional pairs locally.")
    output("[2/4] Enrolling a generated test key with native 2-of-3 TPASS.")
    try:
        enrollment = enroll_walkthrough(enrollment_ids)
    except WalkthroughError:
        output("Enrollment could not be completed; no protocol details were emitted.")
        return 1
    _emit(enrollment_report(enrollment), output)
    output("")
    output(
        "[3/4] Simulating loss of the client key. Only the encrypted backup, "
        "public binding, three logical holder records, and a one-way digest of "
        "the random test key remain in memory."
    )

    while enrollment.attempts < enrollment.attempt_budget:
        recovery_ids = _prompt_identifiers(
            prompt="Choose three recovery pairs [same default: 1,2,3]: ",
            expected_count=3,
            allowed=tuple(_CATALOG_BY_ID),
            default=(1, 2, 3),
            input_function=input_function,
            output=output,
        )
        if recovery_ids is None:
            return 1
        holder_ids = _prompt_identifiers(
            prompt="Choose two TPASS holders [1,2]: ",
            expected_count=2,
            allowed=(1, 2, 3),
            default=(1, 2),
            input_function=input_function,
            output=output,
        )
        if holder_ids is None:
            return 1
        output("")
        output(
            "[4/4] Counting the attempt, running blinded native recovery, "
            "and authenticating the encrypted backup."
        )
        result = recover_walkthrough(enrollment, recovery_ids, holder_ids)
        _emit(result.public_report(), output)
        if result.success:
            output(
                "The generated test key was restored and verified in memory. "
                "No key or protocol secret was printed or saved."
            )
            return 0
        output(
            "Recovery returned a generic rejection. The walkthrough does not "
            "reveal which input or verification step failed."
        )
        if result.attempts_remaining == 0:
            output("The educational attempt budget is exhausted.")
            return 0
        retry = _prompt_retry(input_function, output)
        if retry is None:
            return 1
        if not retry:
            return 0
    return 0


def main() -> int:
    try:
        return run_interactive()
    except Exception:
        print(
            "The walkthrough stopped safely; no protocol details or retained "
            "state were emitted."
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
