"""TPASS-interface simulator for the LOCUS reference prototype."""

from __future__ import annotations

import secrets
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol, TypedDict

from . import _tpass_native as native
from .crypto import FIELD_Q, hash_scalar


class TpassError(Exception):
    """Raised when threshold recovery fails."""


@dataclass(frozen=True)
class TpassPublicParams:
    backend: str
    threshold: int
    parties: int

    def to_dict(self) -> dict:
        return {
            "backend": self.backend,
            "threshold": self.threshold,
            "parties": self.parties,
        }


@dataclass(frozen=True)
class TpassEnrollmentResult:
    public_params: dict
    party_states: list[dict]
    group_secret: bytes


class TpassBackend(Protocol):
    """Structural interface shared by native and explicit test backends."""

    backend: str

    def setup(
        self,
        *,
        recovery_id: str,
        password: int,
        digest_context: str,
        threshold: int,
        parties: int,
    ) -> TpassEnrollmentResult: ...

    def recover(
        self,
        *,
        recovery_id: str,
        password_attempt: int,
        digest_context: str,
        public_params: dict,
        party_states: list[dict],
    ) -> bytes: ...


class _RoundOneItem(TypedDict):
    state: dict[str, int]
    a_i: int
    rho: int
    alpha: int
    beta: int
    B: int
    C: int
    D: int


def _random_nonzero(modulus: int) -> int:
    while True:
        value = secrets.randbelow(modulus)
        if value != 0:
            return value


def _eval_poly(coeffs: list[int], x_value: int, modulus: int) -> int:
    total = 0
    power = 1
    for coeff in coeffs:
        total = (total + coeff * power) % modulus
        power = (power * x_value) % modulus
    return total


def split_secret(
    secret: int,
    threshold: int,
    parties: int,
    *,
    modulus: int = FIELD_Q,
) -> list[tuple[int, int]]:
    if threshold < 1:
        raise ValueError("threshold must be positive")
    if parties < threshold:
        raise ValueError("parties must be at least threshold")
    coeffs = [secret % modulus] + [
        _random_nonzero(modulus) for _ in range(threshold - 1)
    ]
    return [(idx, _eval_poly(coeffs, idx, modulus)) for idx in range(1, parties + 1)]


def interpolate_zero(
    points: Iterable[tuple[int, int]], *, modulus: int = FIELD_Q
) -> int:
    pts = list(points)
    if not pts:
        raise ValueError("at least one point is required")
    secret = 0
    for i, y_i in pts:
        numerator = 1
        denominator = 1
        for j, _ in pts:
            if i == j:
                continue
            numerator = (numerator * (-j)) % modulus
            denominator = (denominator * (i - j)) % modulus
        lagrange = numerator * pow(denominator, -1, modulus)
        secret = (secret + y_i * lagrange) % modulus
    return secret


def _as_int(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TpassError(f"malformed {label}")
    return value


def _validate_public_params(public_params: dict, backend: str) -> tuple[int, int]:
    if not isinstance(public_params, dict):
        raise TpassError("malformed public parameters")
    if public_params.get("backend") != backend:
        raise TpassError("unsupported TPASS backend")
    threshold = _as_int(public_params.get("threshold"), "threshold")
    parties = _as_int(public_params.get("parties"), "party count")
    if threshold < 1 or parties < threshold:
        raise TpassError("invalid threshold parameters")
    return threshold, parties


def _validate_party_state(state: dict, *, modulus: int = FIELD_Q) -> dict[str, int]:
    if not isinstance(state, dict):
        raise TpassError("malformed party state")
    required = ("party_id", "p_i", "z_i", "theta_i")
    for key in required:
        if key not in state:
            raise TpassError("malformed party state")
    return {
        "party_id": _as_int(state["party_id"], "party id"),
        "p_i": _as_int(state["p_i"], "password share") % modulus,
        "z_i": _as_int(state["z_i"], "secret share") % modulus,
        "theta_i": _as_int(state["theta_i"], "digest share") % modulus,
    }


def _inv(value: int, modulus: int) -> int:
    return pow(value % modulus, -1, modulus)


def _group_mul(modulus: int, *values: int) -> int:
    out = 1
    for value in values:
        out = (out * value) % modulus
    return out


def _group_div(value: int, divisor: int, modulus: int) -> int:
    return (value * pow(divisor, -1, modulus)) % modulus


def _encode_group(value: int, modulus: int) -> bytes:
    length = (modulus.bit_length() + 7) // 8
    return int(value % modulus).to_bytes(length, "big")


def _digest_exponent(group_secret: bytes, digest_context: str) -> int:
    return hash_scalar("LOCUS-YHCLZK-digest", group_secret, digest_context)


def _password_bytes(password: int) -> bytes:
    if password < 0 or password >= 1 << 256:
        raise TpassError("invalid context password")
    return password.to_bytes(32, "big")


def _hex_bytes(value: object, label: str) -> bytes:
    if (
        not isinstance(value, str)
        or len(value) % 2 != 0
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise TpassError(f"malformed {label}")
    try:
        return bytes.fromhex(value)
    except ValueError as exc:
        raise TpassError(f"malformed {label}") from exc


class NativeTpassBackend:
    """Paper-facing Yi et al. TPASS backend over native Ristretto255 code."""

    backend = "yi-zk-ristretto255-native-v1"
    encoding = "LOCUS-TPASS-wire-v1"
    max_parties = 255

    def setup(
        self,
        *,
        recovery_id: str,
        password: int,
        digest_context: str,
        threshold: int,
        parties: int,
    ) -> TpassEnrollmentResult:
        del (
            digest_context
        )  # The Rust protocol binds and checks its own digest relation.
        try:
            parameters, states, group_secret = native.setup(
                recovery_id.encode("utf-8"),
                _password_bytes(password),
                threshold,
                parties,
            )
        except native.NativeTpassError as exc:
            raise TpassError("native TPASS enrollment failed") from exc
        public_params = {
            "backend": self.backend,
            "threshold": parameters.threshold,
            "parties": parameters.parties,
            "encoding": self.encoding,
            "parameters": parameters.to_bytes().hex(),
        }
        party_states = [
            {
                "party_id": state.party_id,
                "encoding": self.encoding,
                "state": state.to_secret_bytes().hex(),
            }
            for state in states
        ]
        return TpassEnrollmentResult(
            public_params=public_params,
            party_states=party_states,
            group_secret=bytes(group_secret),
        )

    def recover(
        self,
        *,
        recovery_id: str,
        password_attempt: int,
        digest_context: str,
        public_params: dict,
        party_states: list[dict],
    ) -> bytes:
        del digest_context  # Checked inside the native final-recovery relation.
        threshold, parties = _validate_public_params(public_params, self.backend)
        if set(public_params) != {
            "backend",
            "threshold",
            "parties",
            "encoding",
            "parameters",
        }:
            raise TpassError("malformed public parameters")
        if parties > self.max_parties:
            raise TpassError("too many parties")
        if public_params.get("encoding") != self.encoding:
            raise TpassError("unsupported TPASS encoding")
        if len(party_states) < threshold:
            raise TpassError("not enough parties")
        try:
            parameters = native.PublicParameters.from_bytes(
                _hex_bytes(public_params.get("parameters"), "public parameters")
            )
            if parameters.threshold != threshold or parameters.parties != parties:
                raise TpassError("TPASS parameter metadata mismatch")

            selected_states: list[native.PartyState] = []
            selected: list[int] = []
            for encoded_state in party_states[:threshold]:
                if not isinstance(encoded_state, dict):
                    raise TpassError("malformed party state")
                if set(encoded_state) != {"party_id", "encoding", "state"}:
                    raise TpassError("malformed party state")
                if encoded_state.get("encoding") != self.encoding:
                    raise TpassError("unsupported TPASS encoding")
                state = native.PartyState.from_secret_bytes(
                    _hex_bytes(encoded_state.get("state"), "party state")
                )
                party_id = _as_int(encoded_state.get("party_id"), "party id")
                if state.party_id != party_id:
                    raise TpassError("party state metadata mismatch")
                selected.append(party_id)
                selected_states.append(state)

            session = native.begin_recovery(
                parameters,
                recovery_id.encode("utf-8"),
                _password_bytes(password_attempt),
            )
            request = session.request_bytes()
            commitments: list[bytes] = []
            ephemerals: list[native.PartyEphemeral] = []
            for state in selected_states:
                commitment, ephemeral = native.prepare_commitment(
                    parameters, request, selected, state
                )
                commitments.append(bytes(commitment))
                ephemerals.append(ephemeral)

            responses = [
                bytes(
                    native.verify_and_respond(
                        parameters,
                        request,
                        selected,
                        state,
                        ephemeral,
                        commitments,
                    )
                )
                for state, ephemeral in zip(selected_states, ephemerals, strict=True)
            ]
            gateway = native.aggregate_responses(
                parameters, request, selected, commitments, responses
            )
            return bytes(native.finish_recovery(parameters, session, gateway))
        except native.NativeTpassError as exc:
            raise TpassError("native TPASS recovery failed") from exc


class TpassSimulator:
    """A threshold interface simulator.

    It preserves the setup/recover API and threshold failure behavior that LOCUS
    needs for system tests. It does not implement the real Yi et al. TPASS
    zero-knowledge protocol and must not be used for production-security claims.
    """

    backend = "reference-tpass-simulator-v1"
    modulus = FIELD_Q

    def _group_secret_from_exponent(self, secret_exponent: int) -> bytes:
        return _encode_group(
            hash_scalar("LOCUS-reference-group-secret-v1", secret_exponent),
            self.modulus,
        )

    def setup(
        self,
        *,
        recovery_id: str,
        password: int,
        digest_context: str,
        threshold: int,
        parties: int,
    ) -> TpassEnrollmentResult:
        del recovery_id
        secret_exponent = _random_nonzero(self.modulus)
        group_secret = self._group_secret_from_exponent(secret_exponent)
        digest_exponent = _digest_exponent(group_secret, digest_context)
        p_shares = split_secret(password, threshold, parties, modulus=self.modulus)
        z_shares = split_secret(
            secret_exponent, threshold, parties, modulus=self.modulus
        )
        theta_shares = split_secret(
            digest_exponent, threshold, parties, modulus=self.modulus
        )
        params = TpassPublicParams(self.backend, threshold, parties).to_dict()
        states = []
        for idx in range(parties):
            party_id = idx + 1
            states.append(
                {
                    "party_id": party_id,
                    "p_i": p_shares[idx][1],
                    "z_i": z_shares[idx][1],
                    "theta_i": theta_shares[idx][1],
                }
            )
        return TpassEnrollmentResult(params, states, group_secret)

    def recover(
        self,
        *,
        recovery_id: str,
        password_attempt: int,
        digest_context: str,
        public_params: dict,
        party_states: list[dict],
    ) -> bytes:
        del recovery_id
        threshold, _ = _validate_public_params(public_params, self.backend)
        if len(party_states) < threshold:
            raise TpassError("not enough parties")
        selected = [
            _validate_party_state(state, modulus=self.modulus)
            for state in party_states[:threshold]
        ]
        try:
            p_value = interpolate_zero(
                ((s["party_id"], s["p_i"]) for s in selected),
                modulus=self.modulus,
            )
        except (ValueError, ZeroDivisionError) as exc:
            raise TpassError("malformed party state") from exc
        if p_value != password_attempt % self.modulus:
            raise TpassError("password check failed")
        try:
            z_value = interpolate_zero(
                ((s["party_id"], s["z_i"]) for s in selected),
                modulus=self.modulus,
            )
            theta_value = interpolate_zero(
                ((s["party_id"], s["theta_i"]) for s in selected),
                modulus=self.modulus,
            )
        except (ValueError, ZeroDivisionError) as exc:
            raise TpassError("malformed party state") from exc
        group_secret = self._group_secret_from_exponent(z_value)
        expected_digest = _digest_exponent(group_secret, digest_context)
        if theta_value != expected_digest % self.modulus:
            raise TpassError("TPASS digest check failed")
        return group_secret


class TpassConcreteBackend:
    """Concrete TPASS-style backend for research evaluation.

    This backend implements the recovery equations documented in the LOCUS
    appendix over a fixed toy safe-prime group. It is useful for checking the
    protocol composition and benchmarking equation overhead, but it is not an
    audited production cryptographic implementation.
    """

    backend = "concrete-yhclzk-style-v1"
    q = 126445677247212878163804978075962545073
    p = 252891354494425756327609956151925090147
    g1 = 4
    g2 = 9
    modulus = q

    def _group_secret_from_exponent(self, secret_exponent: int) -> bytes:
        return _encode_group(pow(self.g2, secret_exponent % self.q, self.p), self.p)

    def setup(
        self,
        *,
        recovery_id: str,
        password: int,
        digest_context: str,
        threshold: int,
        parties: int,
    ) -> TpassEnrollmentResult:
        del recovery_id
        secret_exponent = _random_nonzero(self.q)
        group_secret = self._group_secret_from_exponent(secret_exponent)
        digest_exponent = _digest_exponent(group_secret, digest_context)
        p_shares = split_secret(password, threshold, parties, modulus=self.q)
        z_shares = split_secret(secret_exponent, threshold, parties, modulus=self.q)
        theta_shares = split_secret(digest_exponent, threshold, parties, modulus=self.q)
        params = {
            "backend": self.backend,
            "threshold": threshold,
            "parties": parties,
            "group": "toy-safe-prime-128",
            "p": self.p,
            "q": self.q,
            "g1": self.g1,
            "g2": self.g2,
        }
        states = []
        for idx in range(parties):
            party_id = idx + 1
            states.append(
                {
                    "party_id": party_id,
                    "p_i": p_shares[idx][1],
                    "z_i": z_shares[idx][1],
                    "theta_i": theta_shares[idx][1],
                }
            )
        return TpassEnrollmentResult(params, states, group_secret)

    def recover(
        self,
        *,
        recovery_id: str,
        password_attempt: int,
        digest_context: str,
        public_params: dict,
        party_states: list[dict],
    ) -> bytes:
        threshold, _ = _validate_public_params(public_params, self.backend)
        for key in ("p", "q", "g1", "g2"):
            if int(public_params.get(key, -1)) != getattr(self, key):
                raise TpassError("unsupported TPASS group parameters")
        if len(party_states) < threshold:
            raise TpassError("not enough parties")
        selected = [
            _validate_party_state(state, modulus=self.q)
            for state in party_states[:threshold]
        ]
        party_ids = [state["party_id"] for state in selected]
        if len(set(party_ids)) != len(party_ids):
            raise TpassError("malformed party state")
        lagrange = {}
        for i in party_ids:
            numerator = 1
            denominator = 1
            for j in party_ids:
                if i == j:
                    continue
                numerator = (numerator * j) % self.q
                denominator = (denominator * (j - i)) % self.q
            lagrange[i] = numerator * _inv(denominator, self.q) % self.q

        r = _random_nonzero(self.q)
        a_value = _group_mul(
            self.p,
            pow(self.g1, r, self.p),
            pow(self.g2, -(password_attempt % self.q), self.p),
        )

        round_one: list[_RoundOneItem] = []
        for state in selected:
            coeff = lagrange[state["party_id"]]
            rho = _random_nonzero(self.q)
            alpha = _random_nonzero(self.q)
            beta = _random_nonzero(self.q)
            b_i = _group_mul(
                self.p,
                pow(self.g1, rho, self.p),
                pow(self.g2, coeff * state["p_i"], self.p),
            )
            c_i = pow(self.g1, alpha, self.p)
            d_i = pow(self.g1, beta, self.p)
            h_i = (
                hash_scalar(
                    "LOCUS-YHCLZK-hi",
                    recovery_id,
                    a_value,
                    b_i,
                    c_i,
                    d_i,
                )
                % self.q
            )
            h_i2 = hash_scalar("LOCUS-YHCLZK-Hi", h_i) % self.q
            delta_i = (h_i * alpha + h_i2 * beta) % self.q
            if pow(self.g1, delta_i, self.p) != _group_mul(
                self.p,
                pow(c_i, h_i, self.p),
                pow(d_i, h_i2, self.p),
            ):
                raise TpassError("proof verification failed")
            round_one.append(
                {
                    "state": state,
                    "a_i": coeff,
                    "rho": rho,
                    "alpha": alpha,
                    "beta": beta,
                    "B": b_i,
                    "C": c_i,
                    "D": d_i,
                }
            )

        c_value = _group_mul(self.p, *(item["C"] for item in round_one))
        d_value = _group_mul(self.p, *(item["D"] for item in round_one))
        h_value = (
            hash_scalar(
                "LOCUS-YHCLZK-hagg",
                recovery_id,
                a_value,
                c_value,
                d_value,
            )
            % self.q
        )
        if h_value == 0:
            raise TpassError("invalid aggregate challenge")
        w_value = _group_mul(self.p, a_value, *(item["B"] for item in round_one))

        e_values = []
        f_values = []
        for item in round_one:
            state = item["state"]
            e_i = _group_mul(
                self.p,
                pow(self.g2, item["a_i"] * state["z_i"] * h_value, self.p),
                pow(c_value, -item["rho"], self.p),
                pow(w_value, item["alpha"], self.p),
            )
            f_i = _group_mul(
                self.p,
                pow(self.g2, item["a_i"] * state["theta_i"] * h_value, self.p),
                pow(d_value, -item["rho"], self.p),
                pow(w_value, item["beta"], self.p),
            )
            e_values.append(e_i)
            f_values.append(f_i)

        e_value = _group_mul(self.p, *e_values)
        f_value = _group_mul(self.p, *f_values)
        s_blinded = _group_div(e_value, pow(c_value, r, self.p), self.p)
        t_blinded = _group_div(f_value, pow(d_value, r, self.p), self.p)
        h_inv = _inv(h_value, self.q)
        s_value = pow(s_blinded, h_inv, self.p)
        t_value = pow(t_blinded, h_inv, self.p)
        group_secret = _encode_group(s_value, self.p)
        expected_digest = _digest_exponent(group_secret, digest_context)
        expected_element = pow(self.g2, expected_digest % self.q, self.p)
        if t_value != expected_element:
            raise TpassError("TPASS digest check failed")
        return group_secret
