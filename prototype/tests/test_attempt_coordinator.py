from __future__ import annotations

import copy
import tempfile
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from locus.attempt_certificates import (
    AttemptEntry,
    AuthorizationCertificate,
    AuthorizerConfig,
    AuthorizerSigner,
    CertificateError,
    EntryVote,
    FreshnessRequest,
    FreshnessVote,
    InstallVote,
    PrepareCertificate,
    ResponseFreshnessCertificate,
)
from locus.attempt_coordinator import (
    AttemptCoordinator,
    AuthorizerNode,
    AuthorizerPeer,
    AuthorizerState,
    CoordinatorError,
    CoordinatorUnavailable,
)
from locus.party_http import PartyProtocolError, PartyUnavailable
from locus.party_store import GENESIS_HEAD, Conflict, EpochConfig, PartyStore

BID = "ab" * 16
BACKUP_DIGEST = "bc" * 32


def network(
    directory: str,
) -> tuple[AuthorizerConfig, list[PartyStore], AttemptCoordinator]:
    signers = [AuthorizerSigner.generate(party_id) for party_id in range(1, 6)]
    config = AuthorizerConfig(
        bid=BID,
        epoch=1,
        backup_digest=BACKUP_DIGEST,
        fault_bound=2,
        quorum=4,
        public_keys={signer.party_id: signer.public_key_hex for signer in signers},
    )
    stores = []
    for signer in signers:
        store = PartyStore(Path(directory) / f"party-{signer.party_id}.sqlite3")
        store.enroll_epoch(
            EpochConfig(
                bid=BID,
                epoch=1,
                party_id=signer.party_id,
                config_digest=config.digest,
                backup_digest=config.backup_digest,
                budget=3,
            )
        )
        stores.append(store)
    coordinator = AttemptCoordinator(
        config=config,
        nodes=[
            AuthorizerNode(store, signer)
            for store, signer in zip(stores, signers, strict=True)
        ],
    )
    return config, stores, coordinator


def entry(config: AuthorizerConfig, sid_byte: str) -> AttemptEntry:
    return AttemptEntry(
        bid=BID,
        epoch=1,
        config_digest=config.digest,
        log_index=1,
        previous_head=GENESIS_HEAD,
        sid=sid_byte * 32,
        request_digest=("1" + sid_byte[0]) * 32,
        tpass_request_hash=("2" + sid_byte[0]) * 32,
        resulting_consumed=1,
        effective_budget=3,
    )


class FaultingPeer:
    def __init__(
        self,
        delegate: AuthorizerPeer,
        *,
        mode: str,
        conflict_on_entry: bool = False,
    ) -> None:
        self.delegate = delegate
        self.mode = mode
        self.conflict_on_entry = conflict_on_entry

    @property
    def party_id(self) -> int:
        return self.delegate.party_id

    def _fault(self) -> None:
        if self.mode == "slow-unavailable":
            time.sleep(0.2)
            raise PartyUnavailable("synthetic unavailable party")
        if self.mode == "protocol":
            raise PartyProtocolError("synthetic malformed party response")
        if self.mode == "unavailable":
            raise PartyUnavailable("synthetic unavailable party")

    def state_summary(self, bid: str, epoch: int, sid: str) -> AuthorizerState:
        self._fault()
        return self.delegate.state_summary(bid, epoch, sid)

    def create_entry_vote(
        self, candidate: AttemptEntry, config: AuthorizerConfig
    ) -> EntryVote:
        if self.conflict_on_entry:
            raise Conflict("synthetic conflicting party")
        self._fault()
        return self.delegate.create_entry_vote(candidate, config)

    def create_install_vote(
        self, prepare: PrepareCertificate, config: AuthorizerConfig
    ) -> InstallVote:
        self._fault()
        return self.delegate.create_install_vote(prepare, config)

    def install_certificate(
        self, certificate: AuthorizationCertificate, config: AuthorizerConfig
    ) -> None:
        self._fault()
        self.delegate.install_certificate(certificate, config)

    def create_freshness_vote(
        self, request: FreshnessRequest, config: AuthorizerConfig
    ) -> FreshnessVote:
        self._fault()
        return self.delegate.create_freshness_vote(request, config)


class AttemptCoordinatorTests(unittest.TestCase):
    def test_parallel_quorum_tolerates_one_slow_or_malformed_party(self) -> None:
        for mode in ("slow-unavailable", "protocol"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                config, stores, healthy = network(directory)
                try:
                    nodes: list[AuthorizerPeer] = [
                        FaultingPeer(healthy.nodes[0], mode=mode),
                        *healthy.nodes[1:],
                    ]
                    coordinator = AttemptCoordinator(
                        config=config,
                        nodes=nodes,
                        operation_timeout_seconds=1.5,
                        phase_timeout_seconds=0.5,
                    )
                    started = time.monotonic()
                    authorization = coordinator.authorize(entry(config, "29"))
                    self.assertEqual(authorization.prepare.entry.resulting_consumed, 1)
                    self.assertLess(time.monotonic() - started, 1.2)
                finally:
                    for store in stores:
                        store.close()

    def test_parallel_quorum_fails_with_two_unavailable_parties(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config, stores, healthy = network(directory)
            nodes: list[AuthorizerPeer] = [
                FaultingPeer(healthy.nodes[0], mode="unavailable"),
                FaultingPeer(healthy.nodes[1], mode="unavailable"),
                *healthy.nodes[2:],
            ]
            coordinator = AttemptCoordinator(
                config=config,
                nodes=nodes,
                operation_timeout_seconds=0.1,
                phase_timeout_seconds=0.05,
            )
            with self.assertRaises(CoordinatorUnavailable):
                coordinator.authorize(entry(config, "39"))
            self.assertTrue(
                all(int(store.status(BID, 1)["consumed"]) == 0 for store in stores)
            )
            for store in stores:
                store.close()

    def test_observed_conflict_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config, stores, healthy = network(directory)
            nodes: list[AuthorizerPeer] = [
                FaultingPeer(healthy.nodes[0], mode="healthy", conflict_on_entry=True),
                *healthy.nodes[1:],
            ]
            coordinator = AttemptCoordinator(config=config, nodes=nodes)
            with self.assertRaises(Conflict):
                coordinator.authorize(entry(config, "49"))
            self.assertTrue(
                all(int(store.status(BID, 1)["consumed"]) == 0 for store in stores)
            )
            for store in stores:
                store.close()

    def test_exact_authorization_and_freshness_retries_are_stable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config, stores, coordinator = network(directory)
            attempt = entry(config, "33")
            authorization = coordinator.authorize(attempt)
            retry = coordinator.authorize(attempt)
            self.assertEqual(retry.certificate_hash, authorization.certificate_hash)

            freshness = coordinator.certify_freshness(
                authorization=authorization,
                responding_party_id=1,
                boot_nonce="44" * 32,
                response_nonce="55" * 32,
            )
            freshness_retry = coordinator.certify_freshness(
                authorization=authorization,
                responding_party_id=1,
                boot_nonce="44" * 32,
                response_nonce="55" * 32,
            )
            self.assertEqual(
                freshness_retry.certificate_hash, freshness.certificate_hash
            )

            changed = copy.deepcopy(freshness.to_dict())
            changed["request"]["response_nonce"] = "66" * 32
            with self.assertRaises(CertificateError):
                ResponseFreshnessCertificate.from_dict(changed).verify(config)
            for store in stores:
                store.close()

    def test_concurrent_coordinators_cannot_certify_conflicting_slot_entries(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config, stores, first = network(directory)
            second = AttemptCoordinator(config=config, nodes=first.nodes.copy())
            attempts = (entry(config, "77"), entry(config, "88"))

            def authorize(args: tuple[AttemptCoordinator, AttemptEntry]) -> str:
                coordinator, candidate = args
                try:
                    return coordinator.authorize(candidate).certificate_hash
                except (Conflict, CoordinatorError):
                    return "rejected"

            with ThreadPoolExecutor(max_workers=2) as executor:
                results = list(
                    executor.map(authorize, zip((first, second), attempts, strict=True))
                )

            certificates = {result for result in results if result != "rejected"}
            self.assertLessEqual(len(certificates), 1)
            self.assertTrue(
                all(int(store.status(BID, 1)["consumed"]) <= 1 for store in stores)
            )
            locks = {
                lock
                for store in stores
                if (lock := store.next_slot_lock(BID, 1)) is not None
            }
            self.assertLessEqual(len(certificates), 1)
            if not certificates:
                self.assertGreaterEqual(len(locks), 1)
            for store in stores:
                store.close()


if __name__ == "__main__":
    unittest.main()
