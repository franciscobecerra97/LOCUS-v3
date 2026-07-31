from __future__ import annotations

import copy
import sqlite3
import tempfile
import unittest
from pathlib import Path

from locus.attempt_certificates import (
    AttemptEntry,
    AuthorizerConfig,
    AuthorizerSigner,
)
from locus.attempt_coordinator import (
    AttemptCoordinator,
    AuthorizerNode,
    AuthorizerPeer,
    CoordinatorUnavailable,
)
from locus.core import LocusError, enroll, recover, reenroll
from locus.crypto import hash_bytes
from locus.epoch_lifecycle import (
    EpochActivationCertificate,
    EpochTransition,
    LifecycleCertificateError,
)
from locus.object_store import BackupReference, FilesystemBackupObjectStore
from locus.party_store import Conflict, EpochConfig, InvalidState, PartyStore
from locus.tpass import TpassSimulator

BID = "ab" * 16
OLD_BACKUP_DIGEST = "11" * 32
NEW_BACKUP_DIGEST = "22" * 32


def sample_cues() -> list[dict]:
    return [
        {
            "location": {"provider": "fixture", "record_id": "place-1"},
            "person": {"provider": "fixture", "record_id": "person-1"},
        },
        {
            "location": {"provider": "fixture", "record_id": "place-2"},
            "person": {"provider": "fixture", "record_id": "person-2"},
        },
    ]


def attempt_entry(
    config: AuthorizerConfig,
    status: dict[str, int | str],
    *,
    sid_byte: str,
) -> AttemptEntry:
    sid = sid_byte * 32
    request = f"request-{sid_byte}".encode("ascii")
    return AttemptEntry(
        bid=config.bid,
        epoch=config.epoch,
        config_digest=config.digest,
        log_index=int(status["installed_index"]) + 1,
        previous_head=str(status["installed_head"]),
        sid=sid,
        request_digest=hash_bytes(
            "LOCUS/lifecycle-test-request/v1", sid.encode("ascii"), request
        ).hex(),
        tpass_request_hash=hash_bytes("LOCUS/tpass-request-bytes/v1", request).hex(),
        resulting_consumed=int(status["consumed"]) + 1,
        effective_budget=int(status["budget"]),
    )


class LifecycleFixture:
    def __init__(self, root: Path) -> None:
        self.signers = [AuthorizerSigner.generate(party_id) for party_id in range(1, 6)]
        keys = {signer.party_id: signer.public_key_hex for signer in self.signers}
        self.old_config = AuthorizerConfig(
            bid=BID,
            epoch=1,
            backup_digest=OLD_BACKUP_DIGEST,
            fault_bound=2,
            quorum=4,
            public_keys=keys,
        )
        self.new_config = AuthorizerConfig(
            bid=BID,
            epoch=2,
            backup_digest=NEW_BACKUP_DIGEST,
            fault_bound=2,
            quorum=4,
            public_keys=keys,
        )
        self.stores = [
            PartyStore(root / f"party-{signer.party_id}.sqlite3")
            for signer in self.signers
        ]
        for store, signer in zip(self.stores, self.signers, strict=True):
            store.enroll_epoch(
                EpochConfig(
                    bid=BID,
                    epoch=1,
                    party_id=signer.party_id,
                    config_digest=self.old_config.digest,
                    backup_digest=OLD_BACKUP_DIGEST,
                    budget=3,
                )
            )
        coordinator = AttemptCoordinator(
            config=self.old_config,
            nodes=[
                AuthorizerNode(store, signer)
                for store, signer in zip(self.stores, self.signers, strict=True)
            ],
        )
        self.old_authorization = coordinator.authorize(
            attempt_entry(self.old_config, self.stores[0].status(BID, 1), sid_byte="31")
        )
        old_status = self.stores[0].status(BID, 1)
        self.transition = EpochTransition(
            bid=BID,
            predecessor_epoch=1,
            predecessor_config_digest=self.old_config.digest,
            predecessor_backup_digest=OLD_BACKUP_DIGEST,
            predecessor_head=str(old_status["installed_head"]),
            predecessor_consumed=int(old_status["consumed"]),
            predecessor_budget=int(old_status["budget"]),
            successor_epoch=2,
            successor_config_digest=self.new_config.digest,
            successor_backup_digest=NEW_BACKUP_DIGEST,
            successor_budget=2,
            policy_version="LOCUS-epoch-lifecycle-policy-v1",
            transition_nonce="44" * 32,
        )

    def prepare(self) -> EpochActivationCertificate:
        approvals = []
        readiness = []
        for store, signer in zip(self.stores, self.signers, strict=True):
            approvals.append(
                store.create_epoch_approval(
                    self.transition,
                    self.old_config,
                    self.new_config,
                    signer,
                )
            )
            readiness.append(
                store.prepare_successor_epoch(
                    EpochConfig(
                        bid=BID,
                        epoch=2,
                        party_id=signer.party_id,
                        config_digest=self.new_config.digest,
                        backup_digest=NEW_BACKUP_DIGEST,
                        budget=2,
                    ),
                    self.transition,
                    self.old_config,
                    self.new_config,
                    signer,
                )
            )
        return EpochActivationCertificate.create(
            self.transition,
            approvals[: self.old_config.quorum],
            readiness[: self.new_config.quorum],
            self.old_config,
            self.new_config,
        )

    def close(self) -> None:
        for store in self.stores:
            store.close()


class EpochLifecycleTests(unittest.TestCase):
    def test_reenrollment_creates_separated_consecutive_cloud_epoch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            object_store = FilesystemBackupObjectStore(Path(directory) / "cloud")
            backend = TpassSimulator()
            original = enroll(
                user_id="synthetic-user",
                private_key=b"old-private-key",
                cues=sample_cues(),
                threshold=2,
                parties=3,
                object_store=object_store,
                tpass=backend,
            )
            successor = reenroll(
                current_backup=original.backup,
                user_id="synthetic-user",
                private_key=b"new-private-key",
                cues=sample_cues(),
                threshold=2,
                parties=3,
                max_attempts=4,
                object_store=object_store,
                tpass=backend,
            )

            self.assertEqual(successor.backup["bid"], original.backup["bid"])
            self.assertEqual(successor.backup["epoch"], 2)
            self.assertNotEqual(successor.backup["nonce"], original.backup["nonce"])
            self.assertNotEqual(successor.backup["digest"], original.backup["digest"])
            self.assertEqual(
                object_store.read(BackupReference.from_backup(original.backup)),
                original.backup,
            )
            self.assertEqual(
                object_store.read(BackupReference.from_backup(successor.backup)),
                successor.backup,
            )
            self.assertEqual(
                recover(
                    user_id="synthetic-user",
                    backup=successor.backup,
                    party_records=successor.parties[:2],
                    cues=sample_cues(),
                    tpass=backend,
                ),
                b"new-private-key",
            )
            with self.assertRaises(LocusError):
                recover(
                    user_id="synthetic-user",
                    backup=successor.backup,
                    party_records=original.parties[:2],
                    cues=sample_cues(),
                    tpass=backend,
                )
            malformed = copy.deepcopy(original.backup)
            malformed["digest"] = "00" * 32
            with self.assertRaises(LocusError):
                reenroll(
                    current_backup=malformed,
                    user_id="synthetic-user",
                    private_key=b"unused",
                    cues=sample_cues(),
                    threshold=2,
                    parties=3,
                    object_store=object_store,
                    tpass=backend,
                )

    def test_quorum_activation_retires_old_epoch_and_exact_retry_is_stable(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = LifecycleFixture(Path(directory))
            try:
                with self.assertRaises(InvalidState):
                    fixture.stores[0].enroll_epoch(
                        EpochConfig(
                            bid=BID,
                            epoch=2,
                            party_id=1,
                            config_digest=fixture.new_config.digest,
                            backup_digest=NEW_BACKUP_DIGEST,
                            budget=2,
                        )
                    )
                certificate = fixture.prepare()
                self.assertEqual(
                    EpochActivationCertificate.from_dict(certificate.to_dict()),
                    certificate,
                )
                for store in fixture.stores:
                    with self.assertRaises(InvalidState):
                        store.status(BID, 2)
                    self.assertEqual(
                        store.successor_preparation(BID, 2)["state"], "PREPARED"
                    )
                    installed = store.activate_successor_epoch(
                        certificate, fixture.old_config, fixture.new_config
                    )
                    self.assertEqual(installed, certificate.certificate_hash)
                    self.assertEqual(
                        store.activate_successor_epoch(
                            certificate, fixture.old_config, fixture.new_config
                        ),
                        installed,
                    )
                    self.assertEqual(store.status(BID, 1)["status"], "RETIRED")
                    self.assertEqual(store.status(BID, 1)["consumed"], 1)
                    self.assertEqual(store.status(BID, 2)["status"], "ACTIVE")
                    self.assertEqual(store.status(BID, 2)["consumed"], 0)
                    self.assertEqual(
                        store.successor_preparation(BID, 2)["state"], "ACTIVATED"
                    )

                self.assertEqual(
                    fixture.stores[0]
                    .create_epoch_approval(
                        fixture.transition,
                        fixture.old_config,
                        fixture.new_config,
                        fixture.signers[0],
                    )
                    .transition_hash,
                    fixture.transition.transition_hash,
                )
                self.assertEqual(
                    fixture.stores[0]
                    .prepare_successor_epoch(
                        EpochConfig(
                            bid=BID,
                            epoch=2,
                            party_id=1,
                            config_digest=fixture.new_config.digest,
                            backup_digest=NEW_BACKUP_DIGEST,
                            budget=2,
                        ),
                        fixture.transition,
                        fixture.old_config,
                        fixture.new_config,
                        fixture.signers[0],
                    )
                    .transition_hash,
                    fixture.transition.transition_hash,
                )

                with self.assertRaises(InvalidState):
                    fixture.stores[0].install_certificate(
                        fixture.old_authorization, fixture.old_config
                    )
                with self.assertRaises(InvalidState):
                    fixture.stores[0].create_entry_vote(
                        attempt_entry(
                            fixture.old_config,
                            fixture.stores[0].status(BID, 1),
                            sid_byte="32",
                        ),
                        fixture.old_config,
                        fixture.signers[0],
                    )
                new_coordinator = AttemptCoordinator(
                    config=fixture.new_config,
                    nodes=[
                        AuthorizerNode(store, signer)
                        for store, signer in zip(
                            fixture.stores, fixture.signers, strict=True
                        )
                    ],
                )
                new_coordinator.authorize(
                    attempt_entry(
                        fixture.new_config,
                        fixture.stores[0].status(BID, 2),
                        sid_byte="33",
                    )
                )
                self.assertTrue(
                    all(
                        store.status(BID, 2)["consumed"] == 1
                        for store in fixture.stores
                    )
                )
            finally:
                fixture.close()

    def test_partial_activation_cannot_form_old_or_new_quorum(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = LifecycleFixture(Path(directory))
            try:
                certificate = fixture.prepare()
                for store in fixture.stores[:3]:
                    store.activate_successor_epoch(
                        certificate, fixture.old_config, fixture.new_config
                    )
                nodes: list[AuthorizerPeer] = [
                    AuthorizerNode(store, signer)
                    for store, signer in zip(
                        fixture.stores, fixture.signers, strict=True
                    )
                ]
                old_coordinator = AttemptCoordinator(
                    config=fixture.old_config,
                    nodes=nodes,
                    operation_timeout_seconds=0.5,
                    phase_timeout_seconds=0.1,
                )
                with self.assertRaises(CoordinatorUnavailable):
                    old_coordinator.authorize(
                        attempt_entry(
                            fixture.old_config,
                            fixture.stores[3].status(BID, 1),
                            sid_byte="34",
                        )
                    )
                new_coordinator = AttemptCoordinator(
                    config=fixture.new_config,
                    nodes=nodes,
                    operation_timeout_seconds=0.5,
                    phase_timeout_seconds=0.1,
                )
                with self.assertRaises(CoordinatorUnavailable):
                    new_coordinator.state_summaries(BID, 2, "35" * 32)

                fixture.stores[3].activate_successor_epoch(
                    certificate, fixture.old_config, fixture.new_config
                )
                self.assertEqual(
                    len(new_coordinator.state_summaries(BID, 2, "36" * 32)), 4
                )
                fixture.stores[4].activate_successor_epoch(
                    certificate, fixture.old_config, fixture.new_config
                )
            finally:
                fixture.close()

    def test_conflicting_replay_cross_mix_and_restart_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture = LifecycleFixture(root)
            try:
                certificate = fixture.prepare()
                conflicting = EpochTransition(
                    **{
                        **fixture.transition.__dict__,
                        "transition_nonce": "55" * 32,
                    }
                )
                with self.assertRaises(Conflict):
                    fixture.stores[0].create_epoch_approval(
                        conflicting,
                        fixture.old_config,
                        fixture.new_config,
                        fixture.signers[0],
                    )
                mixed_config = AuthorizerConfig(
                    bid=BID,
                    epoch=2,
                    backup_digest="66" * 32,
                    fault_bound=2,
                    quorum=4,
                    public_keys=fixture.new_config.public_keys,
                )
                with self.assertRaises(InvalidState):
                    fixture.stores[0].prepare_successor_epoch(
                        EpochConfig(
                            bid=BID,
                            epoch=2,
                            party_id=1,
                            config_digest=mixed_config.digest,
                            backup_digest=mixed_config.backup_digest,
                            budget=2,
                        ),
                        fixture.transition,
                        fixture.old_config,
                        mixed_config,
                        fixture.signers[0],
                    )
                replacement_signers = [
                    *fixture.signers[:4],
                    AuthorizerSigner.generate(5),
                ]
                replacement_config = AuthorizerConfig(
                    bid=BID,
                    epoch=2,
                    backup_digest=NEW_BACKUP_DIGEST,
                    fault_bound=2,
                    quorum=4,
                    public_keys={
                        signer.party_id: signer.public_key_hex
                        for signer in replacement_signers
                    },
                )
                replacement_transition = EpochTransition(
                    **{
                        **fixture.transition.__dict__,
                        "successor_config_digest": replacement_config.digest,
                    }
                )
                with self.assertRaises(LifecycleCertificateError):
                    replacement_transition.verify_configs(
                        fixture.old_config, replacement_config
                    )
                with self.assertRaises(LifecycleCertificateError):
                    EpochActivationCertificate.create(
                        fixture.transition,
                        list(certificate.approvals[:3]),
                        list(certificate.readiness),
                        fixture.old_config,
                        fixture.new_config,
                    )
                tampered = copy.deepcopy(certificate.to_dict())
                tampered["approvals"][0]["signature"] = "00" * 64
                with self.assertRaises(LifecycleCertificateError):
                    EpochActivationCertificate.from_dict(tampered).verify(
                        fixture.old_config, fixture.new_config
                    )

                fixture.stores[0].close()
                reopened = PartyStore(root / "party-1.sqlite3")
                fixture.stores[0] = reopened
                self.assertEqual(
                    reopened.successor_preparation(BID, 2)["state"], "PREPARED"
                )
                reopened.activate_successor_epoch(
                    certificate, fixture.old_config, fixture.new_config
                )
                self.assertEqual(reopened.status(BID, 1)["status"], "RETIRED")
                self.assertEqual(reopened.status(BID, 2)["status"], "ACTIVE")
            finally:
                fixture.close()

    def test_unresolved_attempt_slot_blocks_lifecycle_lock(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = LifecycleFixture(Path(directory))
            try:
                store = fixture.stores[0]
                store.create_entry_vote(
                    attempt_entry(
                        fixture.old_config,
                        store.status(BID, 1),
                        sid_byte="37",
                    ),
                    fixture.old_config,
                    fixture.signers[0],
                )
                with self.assertRaises(Conflict):
                    store.create_epoch_approval(
                        fixture.transition,
                        fixture.old_config,
                        fixture.new_config,
                        fixture.signers[0],
                    )
            finally:
                fixture.close()

    def test_schema_three_adds_lifecycle_and_runtime_tables(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "party.sqlite3"
            store = PartyStore(path)
            store.close()
            connection = sqlite3.connect(path)
            connection.execute("DROP TABLE epoch_preparations")
            connection.execute("DROP TABLE epoch_transition_locks")
            connection.execute("DROP TABLE epoch_runtime_packages")
            connection.execute(
                "UPDATE metadata SET value = '3' WHERE key = 'schema_version'"
            )
            connection.commit()
            connection.close()

            migrated = PartyStore(path)
            migrated.close()
            connection = sqlite3.connect(path)
            table_names = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
            version = connection.execute(
                "SELECT value FROM metadata WHERE key = 'schema_version'"
            ).fetchone()
            connection.close()
            self.assertIn("epoch_preparations", table_names)
            self.assertIn("epoch_transition_locks", table_names)
            self.assertIn("epoch_runtime_packages", table_names)
            self.assertEqual(version, ("5",))


if __name__ == "__main__":
    unittest.main()
