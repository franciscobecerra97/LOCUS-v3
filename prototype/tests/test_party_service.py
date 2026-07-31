from __future__ import annotations

import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest import mock

from locus import _tpass_native as native
from locus.attempt_certificates import (
    AttemptEntry,
    AuthorizationCertificate,
    AuthorizerConfig,
    AuthorizerSigner,
    EntryVote,
    InstallVote,
    PrepareCertificate,
)
from locus.attempt_coordinator import AttemptCoordinator, AuthorizerNode
from locus.crypto import hash_bytes
from locus.party_service import NativePartyService
from locus.party_store import (
    GENESIS_HEAD,
    AttemptAuthorization,
    BudgetExhausted,
    Conflict,
    EpochConfig,
    InvalidState,
    PartyStore,
    RequestInProgress,
    SessionLost,
)

BID = "ab" * 16
CONFIG_DIGEST = "cd" * 32
BACKUP_DIGEST = "de" * 32
RECOVERY_ID = b"durable-party-service-test"
RECOVERY_INPUT = b"three-canonical-cue-pairs"


def request_hash(request: bytes) -> str:
    return hash_bytes("LOCUS/tpass-request-bytes/v1", request).hex()


def authorization(
    *,
    request: bytes,
    sid_byte: str = "01",
    log_index: int = 1,
    previous_head: str = GENESIS_HEAD,
    resulting_consumed: int = 1,
    budget: int = 3,
) -> AttemptAuthorization:
    sid = sid_byte * 32
    return AttemptAuthorization(
        bid=BID,
        epoch=1,
        config_digest=CONFIG_DIGEST,
        log_index=log_index,
        previous_head=previous_head,
        sid=sid,
        request_digest=hash_bytes(
            "LOCUS/test-request-digest/v1", sid.encode("ascii"), request
        ).hex(),
        tpass_request_hash=request_hash(request),
        resulting_consumed=resulting_consumed,
        effective_budget=budget,
        certificate_hash=hash_bytes(
            "LOCUS/test-certificate/v1", sid.encode("ascii"), request
        ).hex(),
    )


def enroll_store(
    path: Path,
    *,
    party_id: int,
    budget: int = 3,
    config_digest: str = CONFIG_DIGEST,
) -> PartyStore:
    store = PartyStore(path)
    store.enroll_epoch(
        EpochConfig(
            bid=BID,
            epoch=1,
            party_id=party_id,
            config_digest=config_digest,
            backup_digest=BACKUP_DIGEST,
            budget=budget,
        )
    )
    return store


def signed_configuration() -> tuple[AuthorizerConfig, list[AuthorizerSigner]]:
    signers = [AuthorizerSigner.generate(party_id) for party_id in range(1, 6)]
    config = AuthorizerConfig(
        bid=BID,
        epoch=1,
        backup_digest=BACKUP_DIGEST,
        fault_bound=2,
        quorum=4,
        public_keys={signer.party_id: signer.public_key_hex for signer in signers},
    )
    return config, signers


def signed_certificate(
    *,
    request: bytes,
    config: AuthorizerConfig,
    signers: list[AuthorizerSigner],
    sid_byte: str = "01",
    log_index: int = 1,
    previous_head: str = GENESIS_HEAD,
    resulting_consumed: int = 1,
) -> AuthorizationCertificate:
    sid = sid_byte * 32
    entry = AttemptEntry(
        bid=BID,
        epoch=1,
        config_digest=config.digest,
        log_index=log_index,
        previous_head=previous_head,
        sid=sid,
        request_digest=hash_bytes(
            "LOCUS/test-request-digest/v1", sid.encode("ascii"), request
        ).hex(),
        tpass_request_hash=request_hash(request),
        resulting_consumed=resulting_consumed,
        effective_budget=3,
    )
    prepare = PrepareCertificate.create(
        entry,
        [EntryVote.create(entry, signer) for signer in signers[: config.quorum]],
        config,
    )
    return AuthorizationCertificate.create(
        prepare,
        [InstallVote.create(prepare, signer) for signer in signers[: config.quorum]],
        config,
    )


def authorizer_network(
    directory: str,
) -> tuple[
    AuthorizerConfig,
    list[AuthorizerSigner],
    list[PartyStore],
    AttemptCoordinator,
]:
    config, signers = signed_configuration()
    stores = [
        enroll_store(
            Path(directory) / f"authorizer-{signer.party_id}.sqlite3",
            party_id=signer.party_id,
            config_digest=config.digest,
        )
        for signer in signers
    ]
    coordinator = AttemptCoordinator(
        config=config,
        nodes=[
            AuthorizerNode(store, signer)
            for store, signer in zip(stores, signers, strict=True)
        ],
    )
    return config, signers, stores, coordinator


class PartyStoreTests(unittest.TestCase):
    def test_http_idempotency_is_exact_concurrent_and_restart_durable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "party.sqlite3"
            store = PartyStore(path)
            binding = {
                "idempotency_key": "11" * 32,
                "caller_fingerprint": "22" * 32,
                "method": "POST",
                "route": "/v1/ledger/entry-votes",
                "request_digest": "33" * 32,
                "owner_boot_nonce": "44" * 32,
            }

            def reserve() -> str:
                try:
                    return store.begin_http_request(**binding).state
                except RequestInProgress:
                    return "IN_PROGRESS"

            with ThreadPoolExecutor(max_workers=2) as executor:
                results = list(executor.map(lambda _: reserve(), range(2)))
            self.assertCountEqual(results, ["EXECUTE", "IN_PROGRESS"])

            response = b'{"api_version":"test","result":"same-bytes"}'
            store.complete_http_request(
                idempotency_key=binding["idempotency_key"],
                owner_boot_nonce=binding["owner_boot_nonce"],
                response_status=200,
                response_body=response,
            )
            completed = store.begin_http_request(**binding)
            self.assertEqual(completed.state, "COMPLETE")
            self.assertEqual(completed.response_status, 200)
            self.assertEqual(completed.response_body, response)
            for changed in (
                {"caller_fingerprint": "55" * 32},
                {"route": "/v1/ledger/install-votes"},
                {"request_digest": "66" * 32},
            ):
                with self.subTest(changed=changed), self.assertRaises(Conflict):
                    store.begin_http_request(**{**binding, **changed})

            interrupted = {
                **binding,
                "idempotency_key": "77" * 32,
                "request_digest": "88" * 32,
            }
            self.assertEqual(
                store.begin_http_request(**interrupted).state,
                "EXECUTE",
            )
            store.close()

            reopened = PartyStore(path)
            self.assertEqual(reopened.recover_http_requests(), 1)
            retried = reopened.begin_http_request(
                **{**interrupted, "owner_boot_nonce": "99" * 32}
            )
            self.assertEqual(retried.state, "EXECUTE")
            reopened.retry_http_request(
                idempotency_key=interrupted["idempotency_key"],
                owner_boot_nonce="99" * 32,
            )
            self.assertEqual(
                reopened.begin_http_request(
                    **{**interrupted, "owner_boot_nonce": "aa" * 32}
                ).state,
                "EXECUTE",
            )
            reopened.close()

    def test_schema_two_is_migrated_for_http_idempotency(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "party.sqlite3"
            store = PartyStore(path)
            store.close()
            connection = sqlite3.connect(path)
            connection.execute("DROP TABLE http_idempotency")
            connection.execute(
                "UPDATE metadata SET value = '2' WHERE key = 'schema_version'"
            )
            connection.commit()
            connection.close()

            migrated = PartyStore(path)
            self.assertEqual(
                migrated.begin_http_request(
                    idempotency_key="ab" * 32,
                    caller_fingerprint="bc" * 32,
                    method="POST",
                    route="/v1/ledger/entry-votes",
                    request_digest="cd" * 32,
                    owner_boot_nonce="de" * 32,
                ).state,
                "EXECUTE",
            )
            migrated.close()

    def test_authorization_is_durable_idempotent_and_budget_bounded(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "party.sqlite3"
            store = enroll_store(path, party_id=1, budget=2)
            first = authorization(request=b"request-one", budget=2)
            first_head = store.install_authorization(first)
            self.assertEqual(first_head, store.install_authorization(first))
            self.assertEqual(store.status(BID, 1)["consumed"], 1)

            changed_sid = AttemptAuthorization(
                **{
                    **first.to_dict(),
                    "request_digest": "99" * 32,
                }
            )
            with self.assertRaises(Conflict):
                store.install_authorization(changed_sid)

            second = authorization(
                request=b"request-two",
                sid_byte="02",
                log_index=2,
                previous_head=first_head,
                resulting_consumed=2,
                budget=2,
            )
            second_head = store.install_authorization(second)
            self.assertEqual(store.status(BID, 1)["installed_head"], second_head)

            third = authorization(
                request=b"request-three",
                sid_byte="03",
                log_index=3,
                previous_head=second_head,
                resulting_consumed=3,
                budget=2,
            )
            with self.assertRaises(BudgetExhausted):
                store.install_authorization(third)
            self.assertEqual(store.status(BID, 1)["consumed"], 2)
            store.close()

            reopened = PartyStore(path)
            self.assertEqual(reopened.status(BID, 1)["consumed"], 2)
            self.assertEqual(reopened.status(BID, 1)["installed_head"], second_head)
            reopened.close()

    def test_concurrent_conflicting_authorizations_consume_one_slot(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = enroll_store(Path(directory) / "party.sqlite3", party_id=1)
            first = authorization(request=b"candidate-one", sid_byte="11")
            second = authorization(request=b"candidate-two", sid_byte="22")

            def install(candidate: AttemptAuthorization) -> str:
                try:
                    return store.install_authorization(candidate)
                except InvalidState:
                    return "rejected"

            with ThreadPoolExecutor(max_workers=2) as executor:
                results = list(executor.map(install, (first, second)))

            self.assertEqual(sum(result != "rejected" for result in results), 1)
            self.assertEqual(store.status(BID, 1)["consumed"], 1)
            self.assertEqual(store.status(BID, 1)["installed_index"], 1)
            store.close()

    def test_authorization_schema_and_numeric_types_are_strict(self) -> None:
        valid = authorization(request=b"strict").to_dict()
        self.assertEqual(AttemptAuthorization.from_dict(valid).to_dict(), valid)

        for changed in (
            {**valid, "unexpected": 1},
            {key: value for key, value in valid.items() if key != "sid"},
            {**valid, "epoch": "1"},
            {**valid, "log_index": True},
            {**valid, "config_digest": valid["config_digest"].upper()},
        ):
            with self.subTest(changed=changed):
                with self.assertRaises(InvalidState):
                    AttemptAuthorization.from_dict(changed)

    def test_durable_two_phase_votes_build_and_install_quorum_certificate(self) -> None:
        config, signers = signed_configuration()
        attempt = AttemptEntry(
            bid=BID,
            epoch=1,
            config_digest=config.digest,
            log_index=1,
            previous_head=GENESIS_HEAD,
            sid="45" * 32,
            request_digest="56" * 32,
            tpass_request_hash="67" * 32,
            resulting_consumed=1,
            effective_budget=3,
        )
        with tempfile.TemporaryDirectory() as directory:
            stores = [
                enroll_store(
                    Path(directory) / f"authorizer-{signer.party_id}.sqlite3",
                    party_id=signer.party_id,
                    config_digest=config.digest,
                )
                for signer in signers[: config.quorum]
            ]
            votes = [
                store.create_entry_vote(attempt, config, signer)
                for store, signer in zip(stores, signers[: config.quorum], strict=True)
            ]
            self.assertEqual(
                stores[0].create_entry_vote(attempt, config, signers[0]), votes[0]
            )
            prepare = PrepareCertificate.create(attempt, votes, config)
            install_votes = [
                store.create_install_vote(prepare, config, signer)
                for store, signer in zip(stores, signers[: config.quorum], strict=True)
            ]
            authorization_certificate = AuthorizationCertificate.create(
                prepare, install_votes, config
            )
            for store in stores:
                installed = store.install_certificate(authorization_certificate, config)
                self.assertEqual(
                    installed.certificate_hash,
                    authorization_certificate.certificate_hash,
                )
                self.assertEqual(store.status(BID, 1)["consumed"], 1)

            conflict = AttemptEntry.from_dict({**attempt.to_dict(), "sid": "89" * 32})
            with self.assertRaises(Conflict):
                stores[0].create_entry_vote(conflict, config, signers[0])
            for store in stores:
                store.close()


class NativePartyServiceTests(unittest.TestCase):
    def test_complete_native_recovery_crosses_durable_party_guards(self) -> None:
        parameters, states, expected_secret = native.setup(
            RECOVERY_ID, RECOVERY_INPUT, 2, 3
        )
        session = native.begin_recovery(parameters, RECOVERY_ID, RECOVERY_INPUT)
        request = bytes(session.request_bytes())
        selected = [1, 3]

        with tempfile.TemporaryDirectory() as directory:
            config, signers, stores, coordinator = authorizer_network(directory)
            unsigned = signed_certificate(
                request=request, config=config, signers=signers
            ).prepare.entry
            attempt = coordinator.authorize(unsigned)
            services = [
                NativePartyService(
                    store=stores[party_id - 1],
                    parameters=parameters,
                    state=states[party_id - 1],
                    authorizer_config=config,
                    freshness_coordinator=coordinator,
                )
                for party_id in selected
            ]
            commitment_results = [
                service.prepare_commitment(
                    authorization_certificate=attempt,
                    request=request,
                    selected=selected,
                )
                for service in services
            ]
            commitments = [result.commitment for result in commitment_results]
            responses = [
                service.respond(
                    phase_instance_id=result.phase_instance_id,
                    request=request,
                    selected=selected,
                    commitments=commitments,
                )
                for service, result in zip(services, commitment_results, strict=True)
            ]
            gateway = native.aggregate_responses(
                parameters, request, selected, commitments, responses
            )
            self.assertEqual(
                native.finish_recovery(parameters, session, gateway), expected_secret
            )
            for store in stores:
                self.assertEqual(store.status(BID, 1)["consumed"], 1)
                store.close()

    def test_native_commitment_runs_only_after_durable_install_and_intent(self) -> None:
        parameters, states, _ = native.setup(RECOVERY_ID, RECOVERY_INPUT, 2, 3)
        session = native.begin_recovery(parameters, RECOVERY_ID, RECOVERY_INPUT)
        request = bytes(session.request_bytes())

        with tempfile.TemporaryDirectory() as directory:
            config, signers, stores, coordinator = authorizer_network(directory)
            attempt = coordinator.authorize(
                signed_certificate(
                    request=request, config=config, signers=signers
                ).prepare.entry
            )
            store = stores[0]
            service = NativePartyService(
                store=store,
                parameters=parameters,
                state=states[0],
                authorizer_config=config,
                freshness_coordinator=coordinator,
            )
            real_prepare = native.prepare_commitment

            def checked_prepare(
                checked_parameters: native.PublicParameters,
                checked_request: bytes,
                checked_selected: list[int],
                checked_state: native.PartyState,
            ) -> tuple[bytes, native.PartyEphemeral]:
                self.assertEqual(store.status(BID, 1)["consumed"], 1)
                return real_prepare(
                    checked_parameters,
                    checked_request,
                    checked_selected,
                    checked_state,
                )

            with mock.patch(
                "locus.party_service.native.prepare_commitment",
                side_effect=checked_prepare,
            ) as prepare:
                result = service.prepare_commitment(
                    authorization_certificate=attempt,
                    request=request,
                    selected=[1, 3],
                )
            self.assertEqual(prepare.call_count, 1)
            self.assertEqual(
                store.phase(result.phase_instance_id).state, "COMMITMENT_STORED"
            )

            stale = signed_certificate(
                request=b"another request",
                config=config,
                signers=signers,
                sid_byte="02",
                previous_head=GENESIS_HEAD,
                log_index=1,
                resulting_consumed=1,
            )
            with mock.patch("locus.party_service.native.prepare_commitment") as blocked:
                with self.assertRaises(Conflict):
                    service.prepare_commitment(
                        authorization_certificate=stale,
                        request=b"another request",
                        selected=[1, 3],
                    )
            blocked.assert_not_called()
            for authorizer_store in stores:
                authorizer_store.close()

    def test_restart_fails_open_commitment_closed_without_restoring_budget(
        self,
    ) -> None:
        parameters, states, _ = native.setup(RECOVERY_ID, RECOVERY_INPUT, 2, 3)
        session = native.begin_recovery(parameters, RECOVERY_ID, RECOVERY_INPUT)
        request = bytes(session.request_bytes())

        with tempfile.TemporaryDirectory() as directory:
            config, signers, stores, coordinator = authorizer_network(directory)
            attempt = coordinator.authorize(
                signed_certificate(
                    request=request, config=config, signers=signers
                ).prepare.entry
            )
            store = stores[0]
            service = NativePartyService(
                store=store,
                parameters=parameters,
                state=states[0],
                authorizer_config=config,
                freshness_coordinator=coordinator,
            )
            result = service.prepare_commitment(
                authorization_certificate=attempt,
                request=request,
                selected=[1, 3],
            )
            store.close()

            reopened = PartyStore(Path(directory) / "authorizer-1.sqlite3")
            stores[0] = reopened
            restarted_coordinator = AttemptCoordinator(
                config=config,
                nodes=[
                    AuthorizerNode(authorizer_store, signer)
                    for authorizer_store, signer in zip(stores, signers, strict=True)
                ],
            )
            restarted = NativePartyService(
                store=reopened,
                parameters=parameters,
                state=states[0],
                authorizer_config=config,
                freshness_coordinator=restarted_coordinator,
            )
            self.assertEqual(reopened.phase(result.phase_instance_id).state, "LOST")
            with self.assertRaises(SessionLost):
                restarted.respond(
                    phase_instance_id=result.phase_instance_id,
                    request=request,
                    selected=[1, 3],
                    commitments=[result.commitment],
                )
            with self.assertRaises(SessionLost):
                restarted.prepare_commitment(
                    authorization_certificate=attempt,
                    request=request,
                    selected=[1, 3],
                )
            self.assertEqual(reopened.status(BID, 1)["consumed"], 1)
            for authorizer_store in stores:
                authorizer_store.close()


if __name__ == "__main__":
    unittest.main()
