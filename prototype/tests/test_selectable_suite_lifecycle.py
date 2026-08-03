from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from locus.appss_client import AppssPartyEndpoint
from locus.appss_formats import (
    APPSS_SUITE_ID,
    YI_SUITE_ID,
    AppssHolderBinding,
    context_digest,
)
from locus.appss_party import AppssPartyBinding, AppssPartyService, AppssPartyStore
from locus.contracts import PartyRecoveryState
from locus.recovery_descriptor import decode_bundle
from locus.recovery_suite_registry import RecoverySuiteRegistry
from locus.selectable_suite_lifecycle import (
    InjectedSuccessorCrash,
    SelectableEpochRuntime,
    SelectableSuccessorBackend,
    SelectableSuiteEpochFactory,
    SelectableSuiteError,
    prepare_selectable_successor,
    recover_selectable_epoch,
    successor_binding,
)
from locus.successor_publication import (
    PHASE_ORDER,
    DurableSuccessorPublication,
    SuccessorPhase,
)

CANONICAL_INPUT = b"synthetic canonical structured recovery input"
PROTECTED_KEY = b"synthetic protected private key bytes"
ISSUER = "test-only:selectable-suite-issuer"
KEY_ID = "test-only:selectable-suite-key"
ADMISSION = "a1" * 32
PROOF_KEY = "a2" * 32


class _LocalEndpoint:
    def __init__(
        self, holder_id: int, service_identity: str, service: AppssPartyService
    ) -> None:
        self.holder_id = holder_id
        self.service_identity = service_identity
        self.service = service

    def evaluate(self, request_bytes: bytes, *, idempotency_key: str) -> bytes:
        del idempotency_key
        return self.service.evaluate(request_bytes)

    def initialize(self, request_bytes: bytes, *, idempotency_key: str) -> bytes:
        del idempotency_key
        return self.service.evaluate(request_bytes)

    def install(self, install_bytes: bytes, *, idempotency_key: str) -> bytes:
        del idempotency_key
        return self.service.install(install_bytes)


class SelectableSuiteLifecycleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.signer = Ed25519PrivateKey.generate()
        self.public_key = self.signer.public_key()
        self.registry = RecoverySuiteRegistry()
        self.factory = SelectableSuiteEpochFactory(
            signer=self.signer,
            issuer=ISSUER,
            key_id=KEY_ID,
            subject_id="a3" * 32,
            issued_at=1767225600,
            expires_at=1893456000,
            registry=self.registry,
        )
        self.material_counter = 0

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _appss_material(
        self,
        *,
        backup_id: bytes,
        epoch: int,
        configuration_digest: bytes,
    ) -> tuple[
        tuple[AppssHolderBinding, ...],
        dict[int, AppssPartyEndpoint],
    ]:
        self.material_counter += 1
        holders = tuple(
            AppssHolderBinding(
                index=holder_id,
                party_id=f"party-{holder_id}",
                service_identity=(
                    f"test-only:appss-service:{self.material_counter}:{holder_id}"
                ),
            )
            for holder_id in range(1, 4)
        )
        suite_context = context_digest(
            backup_id=backup_id,
            epoch=epoch,
            policy_id="LOCUS-canonical-email-set-v1",
            holders=holders,
            k=2,
            n=3,
            configuration_digest=configuration_digest,
        )
        endpoints: dict[int, AppssPartyEndpoint] = {}
        for holder in holders:
            store = AppssPartyStore(
                self.root
                / (f"appss-{self.material_counter}-{epoch}-{holder.index}.sqlite3"),
                AppssPartyBinding(holder.index, suite_context),
            )
            endpoints[holder.index] = _LocalEndpoint(
                holder.index,
                holder.service_identity,
                AppssPartyService(store),
            )
        return holders, endpoints

    def _prepare(
        self,
        *,
        suite_id: str,
        backup_id: bytes,
        epoch: int,
        configuration_digest: bytes,
        predecessor_descriptor_digest: str | None = None,
    ) -> SelectableEpochRuntime:
        holders: tuple[AppssHolderBinding, ...] = ()
        endpoints: dict[int, AppssPartyEndpoint] = {}
        if suite_id == APPSS_SUITE_ID:
            holders, endpoints = self._appss_material(
                backup_id=backup_id,
                epoch=epoch,
                configuration_digest=configuration_digest,
            )
        return self.factory.prepare_epoch(
            selector_bytes=self.registry.selector_bytes(suite_id=suite_id),
            recovery_id=f"selectable:{backup_id.hex()}:{epoch}",
            backup_id=backup_id,
            epoch=epoch,
            policy_id="LOCUS-canonical-email-set-v1",
            resolver_profile="LOCUS-no-resolver-v1",
            canonical_input=CANONICAL_INPUT,
            protected_key=PROTECTED_KEY,
            public_configuration_digest=configuration_digest,
            predecessor_descriptor_digest=predecessor_descriptor_digest,
            appss_holders=holders,
            appss_endpoints=endpoints,
            admission_grant_digest=ADMISSION,
            client_proof_key_digest=PROOF_KEY,
            nonce=bytes([0xB0 + epoch]) * 16,
        )

    def _recover(self, runtime: SelectableEpochRuntime) -> bytes:
        return recover_selectable_epoch(
            runtime,
            canonical_input=CANONICAL_INPUT,
            issuer_public_key=self.public_key,
            expected_issuer=ISSUER,
            expected_key_id=KEY_ID,
            admission_grant_digest=ADMISSION,
            client_proof_key_digest=PROOF_KEY,
            registry=self.registry,
        )

    def _successor(
        self,
        *,
        predecessor: SelectableEpochRuntime,
        suite_id: str,
        configuration_digest: bytes,
    ) -> SelectableEpochRuntime:
        holders: tuple[AppssHolderBinding, ...] = ()
        endpoints: dict[int, AppssPartyEndpoint] = {}
        if suite_id == APPSS_SUITE_ID:
            holders, endpoints = self._appss_material(
                backup_id=bytes.fromhex(predecessor.prepared.context.backup_id),
                epoch=predecessor.prepared.context.epoch + 1,
                configuration_digest=configuration_digest,
            )
        return prepare_selectable_successor(
            predecessor=predecessor,
            factory=self.factory,
            selector_bytes=self.registry.selector_bytes(suite_id=suite_id),
            canonical_input=CANONICAL_INPUT,
            issuer_public_key=self.public_key,
            expected_issuer=ISSUER,
            expected_key_id=KEY_ID,
            public_configuration_digest=configuration_digest,
            appss_holders=holders,
            appss_endpoints=endpoints,
            admission_grant_digest=ADMISSION,
            client_proof_key_digest=PROOF_KEY,
        )

    def test_new_enrollment_explicitly_selects_each_independent_suite(self) -> None:
        for suite_id, marker in ((YI_SUITE_ID, 0x31), (APPSS_SUITE_ID, 0x32)):
            with self.subTest(suite=suite_id):
                runtime = self._prepare(
                    suite_id=suite_id,
                    backup_id=bytes([marker]) * 16,
                    epoch=1,
                    configuration_digest=bytes([marker + 1]) * 32,
                )
                self.assertEqual(runtime.prepared.selection.suite_id, suite_id)
                self.assertEqual(self._recover(runtime), PROTECTED_KEY)
                bundle = decode_bundle(
                    runtime.prepared.bundle_bytes,
                    issuer_public_key=self.public_key,
                    expected_issuer=ISSUER,
                    expected_key_id=KEY_ID,
                )
                self.assertEqual(
                    bundle.descriptor["payload"]["recovery_suite"]["id"], suite_id
                )
                self.assertEqual(bundle.backup["recovery_suite"]["id"], suite_id)
                self.assertNotIn(PROTECTED_KEY, runtime.prepared.bundle_bytes)

    def test_all_same_and_cross_suite_successors_preserve_key_identity(self) -> None:
        transitions = (
            (YI_SUITE_ID, YI_SUITE_ID),
            (APPSS_SUITE_ID, APPSS_SUITE_ID),
            (YI_SUITE_ID, APPSS_SUITE_ID),
            (APPSS_SUITE_ID, YI_SUITE_ID),
        )
        for case, (predecessor_suite, successor_suite) in enumerate(
            transitions, start=1
        ):
            with self.subTest(predecessor=predecessor_suite, successor=successor_suite):
                backup_id = bytes([0x40 + case]) * 16
                predecessor = self._prepare(
                    suite_id=predecessor_suite,
                    backup_id=backup_id,
                    epoch=1,
                    configuration_digest=bytes([0x50 + case]) * 32,
                )
                successor = self._successor(
                    predecessor=predecessor,
                    suite_id=successor_suite,
                    configuration_digest=bytes([0x60 + case]) * 32,
                )
                self.assertEqual(self._recover(successor), PROTECTED_KEY)
                self.assertEqual(
                    successor.prepared.protected_key_digest,
                    predecessor.prepared.protected_key_digest,
                )
                if successor_suite == predecessor_suite == YI_SUITE_ID:
                    self.assertNotEqual(
                        [state.payload for state in successor.prepared.party_states],
                        [state.payload for state in predecessor.prepared.party_states],
                    )
                else:
                    self.assertNotEqual(
                        successor.prepared.public_state.payload,
                        predecessor.prepared.public_state.payload,
                    )
                bundle = decode_bundle(
                    successor.prepared.bundle_bytes,
                    issuer_public_key=self.public_key,
                    expected_issuer=ISSUER,
                    expected_key_id=KEY_ID,
                )
                self.assertEqual(
                    bundle.descriptor["payload"]["lifecycle"][
                        "predecessor_descriptor_digest"
                    ],
                    predecessor.prepared.descriptor_digest,
                )

                operation = successor_binding(
                    predecessor=predecessor,
                    successor=successor,
                    operation_id=f"selectable-transition-{case}",
                )
                backend = SelectableSuccessorBackend(
                    predecessor=predecessor,
                    successor=successor,
                    canonical_input=CANONICAL_INPUT,
                    issuer_public_key=self.public_key,
                    expected_issuer=ISSUER,
                    expected_key_id=KEY_ID,
                    admission_grant_digest=ADMISSION,
                    client_proof_key_digest=PROOF_KEY,
                )
                journal = self.root / f"transition-{case}.sqlite3"
                result = DurableSuccessorPublication(journal).run(operation, backend)
                self.assertEqual(result.phase, SuccessorPhase.COMPLETE)
                self.assertEqual(backend.recoverable, {2})
                self.assertEqual(backend.activation_count, 1)
                self.assertEqual(backend.retirement_count, 1)
                journal_bytes = journal.read_bytes()
                self.assertNotIn(CANONICAL_INPUT, journal_bytes)
                self.assertNotIn(PROTECTED_KEY, journal_bytes)

    def test_old_new_and_cross_suite_state_never_combine(self) -> None:
        backup_id = bytes.fromhex("71" * 16)
        predecessor = self._prepare(
            suite_id=YI_SUITE_ID,
            backup_id=backup_id,
            epoch=1,
            configuration_digest=bytes.fromhex("72" * 32),
        )
        successor = self._successor(
            predecessor=predecessor,
            suite_id=YI_SUITE_ID,
            configuration_digest=bytes.fromhex("73" * 32),
        )
        mixed_states = (
            predecessor.prepared.party_states[0],
            successor.prepared.party_states[1],
        )
        mixed_prepared = replace(successor.prepared, party_states=mixed_states)
        with self.assertRaises(SelectableSuiteError):
            self._recover(SelectableEpochRuntime(prepared=mixed_prepared))

        appss_successor = self._successor(
            predecessor=predecessor,
            suite_id=APPSS_SUITE_ID,
            configuration_digest=bytes.fromhex("74" * 32),
        )
        with self.assertRaises(SelectableSuiteError):
            SelectableEpochRuntime(
                prepared=appss_successor.prepared,
                appss_holders=appss_successor.appss_holders,
                appss_endpoints={},
            )
        with self.assertRaises(SelectableSuiteError):
            SelectableEpochRuntime(
                prepared=successor.prepared,
                appss_holders=appss_successor.appss_holders,
                appss_endpoints=appss_successor.appss_endpoints,
            )

        wrong_suite_state = PartyRecoveryState(
            suite_id=APPSS_SUITE_ID,
            format_id=appss_successor.prepared.public_state.format_id,
            holder_id=1,
            payload=b"test-only-cross-suite-state",
        )
        cross_prepared = replace(
            successor.prepared,
            party_states=(wrong_suite_state, successor.prepared.party_states[1]),
        )
        with self.assertRaises(SelectableSuiteError):
            self._recover(SelectableEpochRuntime(prepared=cross_prepared))

        appss_predecessor = self._prepare(
            suite_id=APPSS_SUITE_ID,
            backup_id=bytes.fromhex("75" * 16),
            epoch=1,
            configuration_digest=bytes.fromhex("76" * 32),
        )
        appss_fresh = self._successor(
            predecessor=appss_predecessor,
            suite_id=APPSS_SUITE_ID,
            configuration_digest=bytes.fromhex("77" * 32),
        )
        mixed_endpoints = dict(appss_fresh.appss_endpoints)
        mixed_endpoints[1] = appss_predecessor.appss_endpoints[1]
        with self.assertRaises(SelectableSuiteError):
            self._recover(
                SelectableEpochRuntime(
                    prepared=appss_fresh.prepared,
                    appss_holders=appss_fresh.appss_holders,
                    appss_endpoints=mixed_endpoints,
                )
            )

    def test_crash_after_each_selected_publication_effect_resumes_exactly(self) -> None:
        crash_phases = tuple(
            phase
            for phase in PHASE_ORDER
            if phase
            not in {SuccessorPhase.OPTIONAL_KEY_ROTATION, SuccessorPhase.COMPLETE}
        )
        for index, crash_phase in enumerate(crash_phases, start=1):
            with self.subTest(phase=crash_phase.value):
                backup_id = bytes([0x80 + index]) * 16
                predecessor = self._prepare(
                    suite_id=YI_SUITE_ID,
                    backup_id=backup_id,
                    epoch=1,
                    configuration_digest=bytes([0x90 + index]) * 32,
                )
                successor = self._successor(
                    predecessor=predecessor,
                    suite_id=APPSS_SUITE_ID,
                    configuration_digest=bytes([0xA0 + index]) * 32,
                )
                operation = successor_binding(
                    predecessor=predecessor,
                    successor=successor,
                    operation_id=f"crash-transition-{index}",
                )
                backend = SelectableSuccessorBackend(
                    predecessor=predecessor,
                    successor=successor,
                    canonical_input=CANONICAL_INPUT,
                    issuer_public_key=self.public_key,
                    expected_issuer=ISSUER,
                    expected_key_id=KEY_ID,
                    crash_after=crash_phase,
                    admission_grant_digest=ADMISSION,
                    client_proof_key_digest=PROOF_KEY,
                )
                journal = self.root / f"crash-{index}.sqlite3"
                with self.assertRaises(InjectedSuccessorCrash):
                    DurableSuccessorPublication(journal).run(operation, backend)
                result = DurableSuccessorPublication(journal).run(operation, backend)
                self.assertEqual(result.phase, SuccessorPhase.COMPLETE)
                self.assertEqual(backend.recoverable, {2})
                self.assertEqual(backend.activation_count, 1)
                self.assertEqual(backend.retirement_count, 1)


if __name__ == "__main__":
    unittest.main()
