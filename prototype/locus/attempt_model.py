"""Bounded executable model for the LOCUS attempt-control state machine.

This module explores an intentionally small abstraction of the compact 4-of-5
authorizer profile. It is a counterexample finder and regression oracle, not a
formal proof or a replacement for service-level crash and rollback tests.
"""

from __future__ import annotations

import argparse
import json
from collections import deque
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Literal

from .redaction import validate_public_output

MODEL_REPORT_VERSION = "LOCUS-attempt-model-report-v1"
Chain = tuple[str, ...]
ReconciliationMode = Literal["none", "quorum", "monotonic-anchor"]


class AttemptModelError(Exception):
    """The bounded model or its report contract is invalid."""


@dataclass(frozen=True)
class PartyState:
    """One honest authorizer's security-relevant abstract state."""

    chain: Chain = ()
    lock: Chain | None = None
    phase: int = 0
    ready: bool = True
    active: bool = True

    def validate(self) -> None:
        if self.phase not in {0, 1, 2}:
            raise AttemptModelError("invalid party phase")
        if (self.lock is None) != (self.phase == 0):
            raise AttemptModelError("party lock and phase disagree")
        if self.lock is not None and (
            len(self.lock) != len(self.chain) + 1 or self.lock[:-1] != self.chain
        ):
            raise AttemptModelError("party lock does not extend its installed chain")


@dataclass(frozen=True)
class ModelState:
    """Canonical global state used as the exhaustive-search key."""

    parties: tuple[PartyState, ...]
    certificates: tuple[Chain, ...] = ()
    evaluated: tuple[str, ...] = ()
    rollback_count: int = 0
    retired_finalized: bool = False
    post_retirement_certificate: bool = False
    post_retirement_evaluation: bool = False
    anchor_chain: Chain = ()
    anchor_retired: bool = False


@dataclass(frozen=True)
class ModelScenario:
    scenario_id: str
    reconciliation: ReconciliationMode
    rollback_limit: int
    max_depth: int
    max_states: int
    retired_snapshot_seed: bool
    expected_violation: str | None


@dataclass(frozen=True)
class SearchResult:
    outcome: str
    violation: str | None
    trace: tuple[str, ...]
    states_explored: int
    transitions_explored: int
    maximum_depth_reached: int
    truncated: bool


N_AUTHORIZERS = 5
FAULT_BOUND = 2
QUORUM = 4
HONEST_AUTHORIZERS = N_AUTHORIZERS - FAULT_BOUND
BUDGET = 2
REQUESTS = ("request-a", "request-b")

SCENARIOS: tuple[ModelScenario, ...] = (
    ModelScenario(
        scenario_id="baseline-concurrency-no-rollback-v1",
        reconciliation="quorum",
        rollback_limit=0,
        max_depth=12,
        max_states=120_000,
        retired_snapshot_seed=False,
        expected_violation=None,
    ),
    ModelScenario(
        scenario_id="single-honest-rollback-quorum-v1",
        reconciliation="quorum",
        rollback_limit=1,
        max_depth=14,
        max_states=160_000,
        retired_snapshot_seed=False,
        expected_violation="conflicting-authorization-certificates",
    ),
    ModelScenario(
        scenario_id="single-honest-rollback-anchor-v1",
        reconciliation="monotonic-anchor",
        rollback_limit=1,
        max_depth=14,
        max_states=160_000,
        retired_snapshot_seed=False,
        expected_violation=None,
    ),
    ModelScenario(
        scenario_id="double-honest-rollback-quorum-v1",
        reconciliation="quorum",
        rollback_limit=2,
        max_depth=14,
        max_states=180_000,
        retired_snapshot_seed=False,
        expected_violation="conflicting-authorization-certificates",
    ),
    ModelScenario(
        scenario_id="double-honest-rollback-anchor-v1",
        reconciliation="monotonic-anchor",
        rollback_limit=2,
        max_depth=14,
        max_states=180_000,
        retired_snapshot_seed=False,
        expected_violation=None,
    ),
    ModelScenario(
        scenario_id="retired-epoch-double-rollback-quorum-v1",
        reconciliation="quorum",
        rollback_limit=2,
        max_depth=8,
        max_states=40_000,
        retired_snapshot_seed=True,
        expected_violation="authorization-after-final-retirement",
    ),
    ModelScenario(
        scenario_id="retired-epoch-double-rollback-anchor-v1",
        reconciliation="monotonic-anchor",
        rollback_limit=2,
        max_depth=8,
        max_states=40_000,
        retired_snapshot_seed=True,
        expected_violation=None,
    ),
)

SCENARIO_REGISTRY = MappingProxyType(
    {scenario.scenario_id: scenario for scenario in SCENARIOS}
)


def _is_prefix(prefix: Chain, value: Chain) -> bool:
    return len(prefix) <= len(value) and value[: len(prefix)] == prefix


def _party_key(party: PartyState) -> tuple[object, ...]:
    return (
        party.chain,
        party.lock is not None,
        () if party.lock is None else party.lock,
        party.phase,
        party.ready,
        party.active,
    )


def _canonical_parties(parties: list[PartyState]) -> tuple[PartyState, ...]:
    for party in parties:
        party.validate()
    return tuple(sorted(parties, key=_party_key))


def _replace_party(
    state: ModelState, index: int, replacement: PartyState
) -> ModelState:
    parties = list(state.parties)
    parties[index] = replacement
    return ModelState(
        parties=_canonical_parties(parties),
        certificates=state.certificates,
        evaluated=state.evaluated,
        rollback_count=state.rollback_count,
        retired_finalized=state.retired_finalized,
        post_retirement_certificate=state.post_retirement_certificate,
        post_retirement_evaluation=state.post_retirement_evaluation,
        anchor_chain=state.anchor_chain,
        anchor_retired=state.anchor_retired,
    )


def _replace_globals(
    state: ModelState,
    *,
    certificates: tuple[Chain, ...] | None = None,
    evaluated: tuple[str, ...] | None = None,
    rollback_count: int | None = None,
    post_retirement_certificate: bool | None = None,
    post_retirement_evaluation: bool | None = None,
    anchor_chain: Chain | None = None,
) -> ModelState:
    return ModelState(
        parties=state.parties,
        certificates=state.certificates if certificates is None else certificates,
        evaluated=state.evaluated if evaluated is None else evaluated,
        rollback_count=(
            state.rollback_count if rollback_count is None else rollback_count
        ),
        retired_finalized=state.retired_finalized,
        post_retirement_certificate=(
            state.post_retirement_certificate
            if post_retirement_certificate is None
            else post_retirement_certificate
        ),
        post_retirement_evaluation=(
            state.post_retirement_evaluation
            if post_retirement_evaluation is None
            else post_retirement_evaluation
        ),
        anchor_chain=state.anchor_chain if anchor_chain is None else anchor_chain,
        anchor_retired=state.anchor_retired,
    )


def _initial_state(scenario: ModelScenario) -> tuple[ModelState, tuple[str, ...]]:
    if scenario.retired_snapshot_seed:
        parties = _canonical_parties(
            [
                PartyState(ready=False, active=True),
                PartyState(ready=False, active=True),
                PartyState(ready=True, active=False),
            ]
        )
        return (
            ModelState(
                parties=parties,
                rollback_count=2,
                retired_finalized=True,
                anchor_retired=scenario.reconciliation == "monotonic-anchor",
            ),
            (
                "seed: finalize epoch retirement",
                "seed: restore two honest pre-retirement snapshots",
            ),
        )
    return (
        ModelState(
            parties=_canonical_parties(
                [PartyState() for _ in range(HONEST_AUTHORIZERS)]
            )
        ),
        (),
    )


def _unique_party_indices(state: ModelState) -> list[int]:
    indices: list[int] = []
    previous: PartyState | None = None
    for index, party in enumerate(state.parties):
        if party != previous:
            indices.append(index)
            previous = party
    return indices


def _vote_successors(
    state: ModelState, scenario: ModelScenario
) -> list[tuple[str, ModelState]]:
    successors: list[tuple[str, ModelState]] = []
    for index in _unique_party_indices(state):
        party = state.parties[index]
        if not party.ready or not party.active or party.lock is not None:
            continue
        if scenario.reconciliation == "monotonic-anchor" and (
            state.anchor_retired or party.chain != state.anchor_chain
        ):
            continue
        for request in REQUESTS:
            if request in party.chain or len(party.chain) >= BUDGET:
                continue
            candidate = (*party.chain, request)
            replacement = PartyState(
                chain=party.chain,
                lock=candidate,
                phase=1,
                ready=True,
                active=True,
            )
            successors.append(
                (
                    f"vote: honest state class {index} locks {request} "
                    f"at slot {len(candidate)}",
                    _replace_party(state, index, replacement),
                )
            )
    return successors


def _prepare_successors(state: ModelState) -> list[tuple[str, ModelState]]:
    successors: list[tuple[str, ModelState]] = []
    for index in _unique_party_indices(state):
        party = state.parties[index]
        if party.phase != 1 or party.lock is None or not party.ready:
            continue
        support = FAULT_BOUND + sum(
            candidate.lock == party.lock and candidate.phase >= 1
            for candidate in state.parties
        )
        if support < QUORUM:
            continue
        replacement = PartyState(
            chain=party.chain,
            lock=party.lock,
            phase=2,
            ready=party.ready,
            active=party.active,
        )
        successors.append(
            (
                f"install-vote: honest state class {index} stores prepare "
                f"for {'/'.join(party.lock)}",
                _replace_party(state, index, replacement),
            )
        )
    return successors


def _certificate_successors(
    state: ModelState, scenario: ModelScenario
) -> list[tuple[str, ModelState]]:
    candidates = sorted(
        {
            party.lock
            for party in state.parties
            if party.phase == 2 and party.lock is not None
        }
    )
    successors: list[tuple[str, ModelState]] = []
    for candidate in candidates:
        assert candidate is not None
        if candidate in state.certificates:
            continue
        support = FAULT_BOUND + sum(
            party.lock == candidate and party.phase == 2 for party in state.parties
        )
        if support < QUORUM:
            continue
        if scenario.reconciliation == "monotonic-anchor" and (
            state.anchor_retired or candidate[:-1] != state.anchor_chain
        ):
            continue
        certificates = tuple(sorted((*state.certificates, candidate)))
        successors.append(
            (
                f"certify: quorum authorizes {'/'.join(candidate)}",
                _replace_globals(
                    state,
                    certificates=certificates,
                    post_retirement_certificate=(
                        state.post_retirement_certificate or state.retired_finalized
                    ),
                    anchor_chain=(
                        candidate
                        if scenario.reconciliation == "monotonic-anchor"
                        else state.anchor_chain
                    ),
                ),
            )
        )
    return successors


def _install_successors(state: ModelState) -> list[tuple[str, ModelState]]:
    successors: list[tuple[str, ModelState]] = []
    for index in _unique_party_indices(state):
        party = state.parties[index]
        if not party.ready:
            continue
        for certificate in state.certificates:
            if certificate[:-1] != party.chain or (
                party.lock is not None and party.lock != certificate
            ):
                continue
            replacement = PartyState(
                chain=certificate,
                ready=True,
                active=party.active,
            )
            successors.append(
                (
                    f"install: honest state class {index} advances to "
                    f"{'/'.join(certificate)}",
                    _replace_party(state, index, replacement),
                )
            )
    return successors


def _crash_successors(state: ModelState) -> list[tuple[str, ModelState]]:
    successors: list[tuple[str, ModelState]] = []
    for index in _unique_party_indices(state):
        party = state.parties[index]
        if not party.ready:
            continue
        replacement = PartyState(
            chain=party.chain,
            lock=party.lock,
            phase=party.phase,
            ready=False,
            active=party.active,
        )
        successors.append(
            (
                f"crash: honest state class {index} restarts with durable state",
                _replace_party(state, index, replacement),
            )
        )
    return successors


def _reconcile_successors(
    state: ModelState, scenario: ModelScenario
) -> list[tuple[str, ModelState]]:
    successors: list[tuple[str, ModelState]] = []
    observed = sorted({(party.chain, party.active) for party in state.parties})
    for index in _unique_party_indices(state):
        party = state.parties[index]
        if party.ready:
            continue
        if scenario.reconciliation == "none":
            replacement = PartyState(
                chain=party.chain,
                lock=party.lock,
                phase=party.phase,
                ready=True,
                active=party.active,
            )
            successors.append(
                (
                    f"reconcile-none: honest state class {index} trusts its snapshot",
                    _replace_party(state, index, replacement),
                )
            )
            continue
        if scenario.reconciliation == "monotonic-anchor":
            if not _is_prefix(party.chain, state.anchor_chain):
                continue
            target_active = not state.anchor_retired
            if not party.active and target_active:
                continue
            preserve_lock = party.chain == state.anchor_chain
            replacement = PartyState(
                chain=state.anchor_chain,
                lock=party.lock if preserve_lock else None,
                phase=party.phase if preserve_lock else 0,
                ready=True,
                active=target_active,
            )
            successors.append(
                (
                    f"reconcile-anchor: honest state class {index} adopts "
                    f"anchor slot {len(state.anchor_chain)}",
                    _replace_party(state, index, replacement),
                )
            )
            continue
        for target_chain, target_active in observed:
            if not _is_prefix(party.chain, target_chain):
                continue
            if not party.active and target_active:
                continue
            support = FAULT_BOUND + sum(
                candidate.chain == target_chain and candidate.active == target_active
                for candidate in state.parties
            )
            if support < QUORUM:
                continue
            preserve_lock = party.chain == target_chain
            replacement = PartyState(
                chain=target_chain,
                lock=party.lock if preserve_lock else None,
                phase=party.phase if preserve_lock else 0,
                ready=True,
                active=target_active,
            )
            successors.append(
                (
                    f"reconcile-quorum: honest state class {index} accepts "
                    f"slot {len(target_chain)} active={str(target_active).lower()}",
                    _replace_party(state, index, replacement),
                )
            )
    return successors


def _rollback_successors(
    state: ModelState, scenario: ModelScenario
) -> list[tuple[str, ModelState]]:
    if state.rollback_count >= scenario.rollback_limit:
        return []
    successors: list[tuple[str, ModelState]] = []
    for index in _unique_party_indices(state):
        party = state.parties[index]
        for prefix_length in range(len(party.chain) + 1):
            target_chain = party.chain[:prefix_length]
            replacement = PartyState(
                chain=target_chain,
                ready=False,
                active=True,
            )
            if replacement == party:
                continue
            rolled = _replace_party(state, index, replacement)
            rolled = _replace_globals(rolled, rollback_count=state.rollback_count + 1)
            successors.append(
                (
                    f"rollback: restore honest state class {index} to "
                    f"slot {prefix_length} and clear later locks",
                    rolled,
                )
            )
    return successors


def _evaluate_successors(state: ModelState) -> list[tuple[str, ModelState]]:
    successors: list[tuple[str, ModelState]] = []
    for certificate in state.certificates:
        request = certificate[-1]
        if request in state.evaluated:
            continue
        freshness_support = FAULT_BOUND + sum(
            party.ready and party.active and _is_prefix(certificate, party.chain)
            for party in state.parties
        )
        if freshness_support < QUORUM:
            continue
        evaluated = tuple(sorted((*state.evaluated, request)))
        successors.append(
            (
                f"evaluate: TPASS threshold evaluates {request}",
                _replace_globals(
                    state,
                    evaluated=evaluated,
                    post_retirement_evaluation=(
                        state.post_retirement_evaluation or state.retired_finalized
                    ),
                ),
            )
        )
    return successors


def _successors(
    state: ModelState, scenario: ModelScenario
) -> list[tuple[str, ModelState]]:
    successors = [
        *_vote_successors(state, scenario),
        *_prepare_successors(state),
        *_certificate_successors(state, scenario),
        *_install_successors(state),
        *_crash_successors(state),
        *_reconcile_successors(state, scenario),
        *_rollback_successors(state, scenario),
        *_evaluate_successors(state),
    ]
    return sorted(successors, key=lambda item: (item[0], repr(item[1])))


def _violation(state: ModelState, scenario: ModelScenario) -> str | None:
    del scenario
    for party in state.parties:
        party.validate()
    if state.post_retirement_certificate:
        return "authorization-after-final-retirement"
    if state.post_retirement_evaluation:
        return "evaluation-after-final-retirement"
    for left_index, left in enumerate(state.certificates):
        if len(left) > BUDGET or len(set(left)) != len(left):
            return "certificate-budget-or-retry-violation"
        for right in state.certificates[left_index + 1 :]:
            if not _is_prefix(left, right) and not _is_prefix(right, left):
                return "conflicting-authorization-certificates"
    if len(state.evaluated) > BUDGET:
        return "distinct-evaluation-budget-overrun"
    certified_requests = {
        request for certificate in state.certificates for request in certificate
    }
    if not set(state.evaluated).issubset(certified_requests):
        return "uncertified-threshold-evaluation"
    if state.anchor_retired and not state.retired_finalized:
        return "invalid-anchor-retirement"
    if state.anchor_chain and state.anchor_chain not in state.certificates:
        return "anchor-without-certificate"
    return None


def _trace(
    state: ModelState,
    parents: dict[ModelState, tuple[ModelState, str]],
    seed_trace: tuple[str, ...],
) -> tuple[str, ...]:
    actions: list[str] = []
    cursor = state
    while cursor in parents:
        previous, action = parents[cursor]
        actions.append(action)
        cursor = previous
    actions.reverse()
    return (*seed_trace, *actions)


def explore_scenario(scenario: ModelScenario) -> SearchResult:
    """Breadth-first search one bounded scenario for the shortest violation."""

    initial, seed_trace = _initial_state(scenario)
    queue: deque[tuple[ModelState, int]] = deque([(initial, 0)])
    seen = {initial}
    parents: dict[ModelState, tuple[ModelState, str]] = {}
    transitions = 0
    maximum_depth = 0
    truncated = False

    while queue:
        state, depth = queue.popleft()
        maximum_depth = max(maximum_depth, depth)
        violation = _violation(state, scenario)
        if violation is not None:
            return SearchResult(
                outcome="counterexample",
                violation=violation,
                trace=_trace(state, parents, seed_trace),
                states_explored=len(seen),
                transitions_explored=transitions,
                maximum_depth_reached=maximum_depth,
                truncated=False,
            )
        if depth >= scenario.max_depth:
            continue
        for action, successor in _successors(state, scenario):
            transitions += 1
            if successor in seen:
                continue
            if len(seen) >= scenario.max_states:
                truncated = True
                queue.clear()
                break
            seen.add(successor)
            parents[successor] = (state, action)
            queue.append((successor, depth + 1))

    return SearchResult(
        outcome=(
            "state-limit-reached" if truncated else "no-counterexample-within-bound"
        ),
        violation=None,
        trace=(),
        states_explored=len(seen),
        transitions_explored=transitions,
        maximum_depth_reached=maximum_depth,
        truncated=truncated,
    )


def _scenario_report(
    scenario: ModelScenario, result: SearchResult
) -> dict[str, object]:
    expected_outcome = (
        "no-counterexample-within-bound"
        if scenario.expected_violation is None
        else "counterexample"
    )
    matches = (
        result.outcome == expected_outcome
        and result.violation == scenario.expected_violation
        and not result.truncated
    )
    return {
        "bounds": {
            "budget": BUDGET,
            "byzantine_authorizers": FAULT_BOUND,
            "honest_authorizers": HONEST_AUTHORIZERS,
            "max_depth": scenario.max_depth,
            "max_states": scenario.max_states,
            "request_identities": len(REQUESTS),
            "rollback_limit": scenario.rollback_limit,
            "total_authorizers": N_AUTHORIZERS,
            "authorization_quorum": QUORUM,
        },
        "expected": {
            "outcome": expected_outcome,
            "violation": scenario.expected_violation,
        },
        "initial_state": (
            "two-honest-pre-retirement-snapshots"
            if scenario.retired_snapshot_seed
            else "active-genesis"
        ),
        "observed": {
            "maximum_depth_reached": result.maximum_depth_reached,
            "outcome": result.outcome,
            "states_explored": result.states_explored,
            "trace": list(result.trace),
            "transitions_explored": result.transitions_explored,
            "truncated": result.truncated,
            "violation": result.violation,
        },
        "reconciliation": scenario.reconciliation,
        "scenario_id": scenario.scenario_id,
        "status": "passed" if matches else "failed",
    }


def build_model_report() -> dict[str, object]:
    """Run every frozen scenario and return one strict public report."""

    scenario_reports = [
        _scenario_report(scenario, explore_scenario(scenario)) for scenario in SCENARIOS
    ]
    report: dict[str, object] = {
        "interpretation": (
            "This bounded explorer is a counterexample finder, not a proof. "
            "Quorum-only reconciliation admits the reported rollback forks; the "
            "monotonic-anchor mode assumes an ideal non-rolled-back compare-and-set "
            "checkpoint consulted before votes and advanced atomically with "
            "certification."
        ),
        "model": {
            "byzantine_behavior": (
                "fault-bound authorizers may support every conflicting quorum"
            ),
            "exact_retry": "collapsed to the existing durable lock or certificate",
            "honest_state": (
                "installed chain, next-slot lock, install phase, readiness, "
                "and epoch-active flag"
            ),
            "search": "breadth-first with honest-party symmetry reduction",
        },
        "scenarios": scenario_reports,
        "status": (
            "passed"
            if all(scenario["status"] == "passed" for scenario in scenario_reports)
            else "failed"
        ),
        "version": MODEL_REPORT_VERSION,
    }
    validate_model_report(report)
    validate_public_output(report)
    return report


def _exact_dict(value: object, fields: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        raise AttemptModelError(f"invalid {label}")
    return value


def validate_model_report(value: object) -> dict[str, object]:
    """Validate the exact report shape and frozen scenario binding."""

    report = _exact_dict(
        value,
        {"interpretation", "model", "scenarios", "status", "version"},
        "attempt-model report",
    )
    if (
        report["version"] != MODEL_REPORT_VERSION
        or report["status"] not in {"passed", "failed"}
        or not isinstance(report["interpretation"], str)
        or not isinstance(report["scenarios"], list)
    ):
        raise AttemptModelError("invalid attempt-model report header")
    _exact_dict(
        report["model"],
        {"byzantine_behavior", "exact_retry", "honest_state", "search"},
        "attempt-model description",
    )
    if len(report["scenarios"]) != len(SCENARIOS):
        raise AttemptModelError("attempt-model scenario count changed")
    statuses: list[str] = []
    for raw, frozen in zip(report["scenarios"], SCENARIOS, strict=True):
        scenario = _exact_dict(
            raw,
            {
                "bounds",
                "expected",
                "initial_state",
                "observed",
                "reconciliation",
                "scenario_id",
                "status",
            },
            "attempt-model scenario",
        )
        if (
            scenario["scenario_id"] != frozen.scenario_id
            or scenario["reconciliation"] != frozen.reconciliation
            or scenario["status"] not in {"passed", "failed"}
            or scenario["initial_state"]
            != (
                "two-honest-pre-retirement-snapshots"
                if frozen.retired_snapshot_seed
                else "active-genesis"
            )
        ):
            raise AttemptModelError("attempt-model scenario binding changed")
        bounds = _exact_dict(
            scenario["bounds"],
            {
                "authorization_quorum",
                "budget",
                "byzantine_authorizers",
                "honest_authorizers",
                "max_depth",
                "max_states",
                "request_identities",
                "rollback_limit",
                "total_authorizers",
            },
            "attempt-model bounds",
        )
        expected_bounds = {
            "authorization_quorum": QUORUM,
            "budget": BUDGET,
            "byzantine_authorizers": FAULT_BOUND,
            "honest_authorizers": HONEST_AUTHORIZERS,
            "max_depth": frozen.max_depth,
            "max_states": frozen.max_states,
            "request_identities": len(REQUESTS),
            "rollback_limit": frozen.rollback_limit,
            "total_authorizers": N_AUTHORIZERS,
        }
        if bounds != expected_bounds:
            raise AttemptModelError("attempt-model bounds changed")
        expected = _exact_dict(
            scenario["expected"], {"outcome", "violation"}, "expected model result"
        )
        expected_violation = frozen.expected_violation
        if expected != {
            "outcome": (
                "no-counterexample-within-bound"
                if expected_violation is None
                else "counterexample"
            ),
            "violation": expected_violation,
        }:
            raise AttemptModelError("attempt-model expectation changed")
        observed = _exact_dict(
            scenario["observed"],
            {
                "maximum_depth_reached",
                "outcome",
                "states_explored",
                "trace",
                "transitions_explored",
                "truncated",
                "violation",
            },
            "observed model result",
        )
        if (
            observed["outcome"]
            not in {
                "counterexample",
                "no-counterexample-within-bound",
                "state-limit-reached",
            }
            or not isinstance(observed["trace"], list)
            or any(not isinstance(item, str) for item in observed["trace"])
            or not isinstance(observed["truncated"], bool)
            or (
                observed["violation"] is not None
                and not isinstance(observed["violation"], str)
            )
        ):
            raise AttemptModelError("invalid observed model result")
        for field in (
            "maximum_depth_reached",
            "states_explored",
            "transitions_explored",
        ):
            if (
                isinstance(observed[field], bool)
                or not isinstance(observed[field], int)
                or observed[field] < 0
            ):
                raise AttemptModelError("invalid model counter")
        observed_matches = (
            observed["outcome"] == expected["outcome"]
            and observed["violation"] == expected["violation"]
            and not observed["truncated"]
        )
        expected_scenario_status = "passed" if observed_matches else "failed"
        if scenario["status"] != expected_scenario_status:
            raise AttemptModelError("attempt-model scenario status mismatch")
        statuses.append(scenario["status"])
    expected_status = "passed" if set(statuses) == {"passed"} else "failed"
    if report["status"] != expected_status:
        raise AttemptModelError("attempt-model summary status mismatch")
    return dict(report)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Explore the frozen bounded LOCUS attempt-control model."
    )
    parser.parse_args()
    try:
        report = build_model_report()
    except AttemptModelError:
        return 2
    print(
        json.dumps(
            report,
            allow_nan=False,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
