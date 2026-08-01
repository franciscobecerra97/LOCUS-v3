from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from locus.contracts import (
    MAX_OPAQUE_PUBLIC_BYTES,
    AdmissionBinding,
    AuthorizerEndpoint,
    BackupObjectStore,
    ContractError,
    CuePolicy,
    EnrollmentClientState,
    EnrollmentPhase,
    PartyDirectorySnapshot,
    PasswordProtectedSecretRecovery,
    PublicRecoveryState,
    RecoveryClientSession,
    RecoveryContext,
    RecoveryHolder,
    RecoveryPhase,
    RecoveryRequest,
    RecoveryResponse,
    Resolver,
    ThresholdParameters,
)
from locus.cue_policy import FrozenLocationPersonCuePolicy
from locus.object_store import FilesystemBackupObjectStore
from locus.resolver_fixture import DeterministicResolverAdapter
from locus.yi_compat import (
    YI_RECOVERY_SUITE_ID,
    RecoverySuiteError,
    YiTpassRecoveryAdapter,
)

ROOT = Path(__file__).resolve().parents[2]
TPASS_VECTOR = ROOT / "tpass-core/test-vectors/yi-zk-ristretto255-v1.txt"
CUE_VECTOR = ROOT / "prototype/test-vectors/cue-policy-v1.json"
RESOLVER_VECTOR = ROOT / "prototype/test-vectors/resolver-drift-v1.json"


def load_tpass_vector() -> dict[str, str]:
    return {
        key: value
        for line in TPASS_VECTOR.read_text(encoding="utf-8").splitlines()
        if line and not line.startswith("#")
        for key, value in [line.split("=", maxsplit=1)]
    }


def recovery_context(*, suite_id: str = YI_RECOVERY_SUITE_ID) -> RecoveryContext:
    return RecoveryContext(
        suite_id=suite_id,
        recovery_id="typed-interface-user:00000000000000000000000000000000:1",
        backup_id="00000000000000000000000000000000",
        epoch=1,
        policy_id="LOCUS-location-person-set-v1",
        configuration_digest="00" * 32,
        digest_context="00000000000000000000000000000000:1",
    )


class SystemInterfaceTests(unittest.TestCase):
    def test_frozen_vector_files_are_byte_identical(self) -> None:
        self.assertEqual(
            hashlib.sha256(TPASS_VECTOR.read_bytes()).hexdigest(),
            "a25fe5589c76f26607452c52267a9fb2d4ddb91250f8ec8331f34c7c85497c99",
        )
        self.assertEqual(
            hashlib.sha256(CUE_VECTOR.read_bytes()).hexdigest(),
            "24b8b1972eedc7f54c8cce51f8f21d176d09b70093fb1abb610fa23635919970",
        )

    def test_yi_adapter_satisfies_contract_and_recovers_same_secret(self) -> None:
        adapter = YiTpassRecoveryAdapter()
        self.assertIsInstance(adapter, PasswordProtectedSecretRecovery)
        self.assertIs(adapter.request_type, RecoveryRequest)
        self.assertIs(adapter.response_type, RecoveryResponse)
        self.assertIs(adapter.client_session_type, RecoveryClientSession)

        password = bytes(range(32))
        enrollment = adapter.initialize(
            context=recovery_context(),
            password_input=password,
            threshold=ThresholdParameters(k=2, n=3),
        )
        recovered = adapter.recover(
            context=recovery_context(),
            password_input=password,
            public_state=enrollment.public_state,
            party_states=(enrollment.party_states[0], enrollment.party_states[2]),
        )
        self.assertEqual(recovered, enrollment.recovery_secret)
        self.assertEqual(enrollment.public_state.format_id, "LOCUS-TPASS-wire-v1")
        self.assertEqual(
            [state.holder_id for state in enrollment.party_states], [1, 2, 3]
        )
        self.assertNotIn(enrollment.party_states[0].payload.hex(), repr(enrollment))

    def test_yi_adapter_preserves_frozen_native_payload_bytes(self) -> None:
        vector = load_tpass_vector()
        adapter = YiTpassRecoveryAdapter()
        public = {
            "backend": "yi-zk-ristretto255-native-v1",
            "threshold": int(vector["threshold"]),
            "parties": int(vector["parties"]),
            "encoding": "LOCUS-TPASS-wire-v1",
            "parameters": vector["parameters"],
        }
        wrapped_public = adapter.public_state_from_legacy(public)
        self.assertEqual(
            adapter.decode_public_state(wrapped_public)["parameters"],
            vector["parameters"],
        )
        for party_id in (1, 2, 3):
            legacy = {
                "party_id": party_id,
                "encoding": "LOCUS-TPASS-wire-v1",
                "state": vector[f"state_{party_id}"],
            }
            wrapped = adapter.party_state_from_legacy(legacy)
            self.assertEqual(
                adapter.decode_party_state(wrapped)["state"],
                vector[f"state_{party_id}"],
            )

    def test_yi_adapter_rejects_cross_suite_and_noncanonical_state(self) -> None:
        adapter = YiTpassRecoveryAdapter()
        with self.assertRaises(RecoverySuiteError):
            adapter.initialize(
                context=recovery_context(suite_id="future-suite"),
                password_input=bytes(32),
                threshold=ThresholdParameters(k=2, n=3),
            )

        valid = {
            "backend": "yi-zk-ristretto255-native-v1",
            "threshold": 2,
            "parties": 3,
            "encoding": "LOCUS-TPASS-wire-v1",
            "parameters": "00",
        }
        mutations = (
            json.dumps(valid, indent=2).encode("ascii"),
            json.dumps({**valid, "unexpected": 1}, separators=(",", ":")).encode(
                "ascii"
            ),
            (
                b'{"backend":"yi-zk-ristretto255-native-v1",'
                b'"backend":"yi-zk-ristretto255-native-v1",'
                b'"encoding":"LOCUS-TPASS-wire-v1","parameters":"00",'
                b'"parties":3,"threshold":2}'
            ),
        )
        for payload in mutations:
            with self.subTest(payload=payload):
                state = PublicRecoveryState(
                    suite_id=YI_RECOVERY_SUITE_ID,
                    format_id="LOCUS-TPASS-wire-v1",
                    payload=payload,
                )
                with self.assertRaises(RecoverySuiteError):
                    adapter.decode_public_state(state)

        with self.assertRaises(ContractError):
            PublicRecoveryState(
                suite_id=YI_RECOVERY_SUITE_ID,
                format_id="LOCUS-TPASS-wire-v1",
                payload=b"x" * (MAX_OPAQUE_PUBLIC_BYTES + 1),
            )

    def test_frozen_cue_and_resolver_adapters_preserve_canonical_bytes(self) -> None:
        cue_corpus = json.loads(CUE_VECTOR.read_text(encoding="utf-8"))
        cue_vector = cue_corpus["valid"][0]
        policy = FrozenLocationPersonCuePolicy()
        self.assertIsInstance(policy, CuePolicy)
        result = policy.process(copy.deepcopy(cue_vector["cues"]))
        self.assertEqual(result.policy_id, cue_corpus["policy_version"])
        self.assertEqual(result.canonical_bytes.hex(), cue_vector["canonical_hex"])

        resolver_corpus = json.loads(RESOLVER_VECTOR.read_text(encoding="utf-8"))
        resolver = DeterministicResolverAdapter()
        self.assertIsInstance(resolver, Resolver)
        resolved = resolver.resolve(copy.deepcopy(resolver_corpus["baseline"]))
        self.assertEqual(resolved.policy_id, result.policy_id)
        self.assertEqual(
            hashlib.sha256(resolved.canonical_bytes).hexdigest(),
            resolver_corpus["expected_baseline_sha256"],
        )

    def test_backup_contract_remains_structural(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = FilesystemBackupObjectStore(directory)
            self.assertIsInstance(store, BackupObjectStore)

    def test_authorizers_and_recovery_holders_are_distinct_typed_sets(self) -> None:
        authorizers = tuple(
            AuthorizerEndpoint(
                authorizer_id=party_id,
                endpoint=f"https://party-{party_id}.invalid",
                identity_digest=f"identity-{party_id}",
            )
            for party_id in range(1, 6)
        )
        holders = tuple(
            RecoveryHolder(
                holder_id=party_id,
                authorizer_id=party_id,
                suite_id=YI_RECOVERY_SUITE_ID,
            )
            for party_id in range(1, 4)
        )
        directory = PartyDirectorySnapshot(
            authorizers=authorizers,
            recovery_holders=holders,
            authorization_quorum=4,
            recovery_threshold=ThresholdParameters(k=2, n=3),
        )
        self.assertEqual(directory.authorization_quorum, 4)
        self.assertEqual(directory.recovery_threshold.k, 2)
        self.assertEqual(len(directory.authorizers), 5)
        self.assertEqual(len(directory.recovery_holders), 3)

        with self.assertRaises(ContractError):
            PartyDirectorySnapshot(
                authorizers=authorizers,
                recovery_holders=(
                    RecoveryHolder(
                        holder_id=1,
                        authorizer_id=1,
                        suite_id=YI_RECOVERY_SUITE_ID,
                    ),
                    RecoveryHolder(
                        holder_id=2,
                        authorizer_id=2,
                        suite_id="future-suite",
                    ),
                ),
                authorization_quorum=4,
                recovery_threshold=ThresholdParameters(k=2, n=2),
            )

    def test_state_and_admission_types_exclude_secret_payloads(self) -> None:
        state = EnrollmentClientState(
            operation_id="operation-1",
            phase=EnrollmentPhase.POLICY,
        )
        self.assertEqual(state.phase, EnrollmentPhase.POLICY)
        self.assertNotIn("private_key", state.__dataclass_fields__)
        self.assertNotIn("password", state.__dataclass_fields__)
        self.assertEqual(RecoveryPhase.AUTHORIZATION.value, "authorization")

        binding = AdmissionBinding(
            subject="synthetic-subject",
            backup_id="00000000000000000000000000000000",
            epoch=1,
            operation="recover",
            audience="party-1",
            client_key_thumbprint="synthetic-thumbprint",
            nonce="nonce-1",
            issued_at=1,
            expires_at=2,
            issuer="local-test-issuer",
            profile_id="local-test-profile",
        )
        self.assertEqual(binding.operation, "recover")
        with self.assertRaises(ContractError):
            AdmissionBinding(**{**binding.__dict__, "expires_at": 1})


if __name__ == "__main__":
    unittest.main()
