from __future__ import annotations

import threading
import time
import unittest
from unittest import mock

from locus.attempt_certificates import AuthorizerConfig
from locus.attempt_coordinator import AuthorizerState
from locus.deployment import (
    DeploymentError,
    _collect_selected,
    _select_tpass_subset,
)
from locus.party_http import PartyUnavailable, RemotePartyClient
from locus.party_store import GENESIS_HEAD

CONFIG = AuthorizerConfig(
    bid="ab" * 16,
    epoch=1,
    backup_digest="bc" * 32,
    fault_bound=2,
    quorum=4,
    public_keys={party_id: "00" * 32 for party_id in range(1, 6)},
)


def _summary(
    party_id: int, *, status: str = "ACTIVE", installed_index: int = 0
) -> tuple[int, AuthorizerState]:
    return (
        party_id,
        AuthorizerState(
            status={
                "backup_digest": CONFIG.backup_digest,
                "budget": 4,
                "consumed": installed_index,
                "installed_head": GENESIS_HEAD if installed_index == 0 else "11" * 32,
                "installed_index": installed_index,
                "status": status,
            },
            next_slot_lock=None,
            installed_certificate=None,
        ),
    )


def _clients() -> dict[int, RemotePartyClient]:
    return {
        party_id: mock.create_autospec(RemotePartyClient, instance=True)
        for party_id in range(1, 4)
    }


class RecoveryResilienceTests(unittest.TestCase):
    def test_pre_authorization_subset_selection_has_deterministic_fallback(
        self,
    ) -> None:
        clients = _clients()
        cases = (
            ([1, 2, 3, 4, 5], [1, 3]),
            ([2, 3, 4, 5], [2, 3]),
            ([1, 2, 4, 5], [1, 2]),
        )
        for responsive, expected in cases:
            with self.subTest(responsive=responsive):
                self.assertEqual(
                    _select_tpass_subset(
                        clients,
                        [_summary(party_id) for party_id in responsive],
                        CONFIG,
                    ),
                    expected,
                )

        with self.assertRaises(DeploymentError):
            _select_tpass_subset(
                clients, [_summary(1), _summary(4), _summary(5)], CONFIG
            )

        stale_party = [
            _summary(1, installed_index=0),
            *[_summary(party_id, installed_index=1) for party_id in range(2, 6)],
        ]
        self.assertEqual(_select_tpass_subset(clients, stale_party, CONFIG), [2, 3])

    def test_selected_phase_is_concurrent_ordered_and_deadline_bounded(self) -> None:
        rendezvous = threading.Barrier(2)

        def operation(party_id: int) -> str:
            rendezvous.wait(timeout=0.1)
            return f"party-{party_id}"

        self.assertEqual(
            _collect_selected([1, 3], operation, timeout_seconds=0.2),
            ["party-1", "party-3"],
        )

        def slow_operation(party_id: int) -> int:
            time.sleep(0.1)
            return party_id

        with self.assertRaises(DeploymentError):
            _collect_selected(
                [1, 3],
                slow_operation,
                timeout_seconds=0.01,
            )

    def test_selected_phase_failure_never_switches_subset(self) -> None:
        called: list[int] = []

        def operation(party_id: int) -> int:
            called.append(party_id)
            if party_id == 3:
                raise PartyUnavailable("synthetic post-authorization failure")
            return party_id

        with self.assertRaises(DeploymentError):
            _collect_selected([1, 3], operation, timeout_seconds=0.1)
        self.assertEqual(set(called), {1, 3})
        self.assertNotIn(2, called)


if __name__ == "__main__":
    unittest.main()
