from __future__ import annotations

import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from locus.admission import (
    LOCAL_ISSUER_PROFILE,
    RECOVERY_OPERATION,
    AdmissionBinding,
    client_key_thumbprint,
    decode_canonical_object,
    pseudonymous_object_prefix,
)
from locus.contracts import (
    AdmissionVerifier,
    ApplicationStorageGateway,
    GatewayRequest,
    GatewayResult,
    StorageCapabilityVerifier,
    StorageOperation,
)
from locus.local_admission import (
    AdmissionReplayConflict,
    AdmissionReplayStore,
    AdmissionVerificationError,
    LocalAdmissionStorageGateway,
    LocalAdmissionVerifier,
    LocalSyntheticAdmissionIssuer,
    capability_digest,
    create_client_proof,
    gateway_request_bytes,
    request_digest,
)
from locus.object_store import BackupReference

SUBJECT = "11" * 32
OTHER_SUBJECT = "12" * 32
BACKUP_ID = "22" * 16
ISSUER_ID = "locus-local-test-issuer"
ISSUER_KEY_ID = "local-admission-key-1"
NOW = 2_000_000_010
ROOT = Path(__file__).resolve().parents[2]
VECTOR_PATH = ROOT / "prototype/test-vectors/local-admission-v1.txt"


def private_key(seed_start: int) -> Ed25519PrivateKey:
    return Ed25519PrivateKey.from_private_bytes(
        bytes(range(seed_start, seed_start + 32))
    )


def raw_public_key(key: Ed25519PrivateKey) -> bytes:
    return key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )


def issuer() -> LocalSyntheticAdmissionIssuer:
    return LocalSyntheticAdmissionIssuer(
        issuer=ISSUER_ID,
        key_id=ISSUER_KEY_ID,
        private_key=private_key(0),
        allowed_subjects=frozenset({SUBJECT}),
    )


def binding(
    *,
    audience: str = "locus-authorizer-1",
    operation: str = RECOVERY_OPERATION,
    object_prefix: str | None = None,
    client_key: Ed25519PrivateKey | None = None,
    nonce: str = "33" * 32,
) -> AdmissionBinding:
    key = private_key(32) if client_key is None else client_key
    return AdmissionBinding(
        subject=SUBJECT,
        backup_id=BACKUP_ID,
        epoch=7,
        operation=operation,
        audience=audience,
        client_key_thumbprint=client_key_thumbprint(raw_public_key(key)),
        nonce=nonce,
        issued_at=2_000_000_000,
        expires_at=2_000_000_120,
        issuer=ISSUER_ID,
        object_prefix=object_prefix,
    )


def verifier(path: Path) -> LocalAdmissionVerifier:
    local_issuer = issuer()
    return LocalAdmissionVerifier(
        issuer=ISSUER_ID,
        issuer_key_id=ISSUER_KEY_ID,
        issuer_public_key=local_issuer.public_key,
        replay_store=AdmissionReplayStore(path),
    )


@dataclass
class _Backend:
    calls: int = 0

    def execute(self, request: GatewayRequest) -> GatewayResult:
        self.calls += 1
        return GatewayResult(reference=request.backup_reference, payload=b"stored")


class LocalAdmissionTests(unittest.TestCase):
    def test_deterministic_issuer_and_client_proof_vector(self) -> None:
        expected_vector = dict(
            line.split("=", 1)
            for line in VECTOR_PATH.read_text(encoding="utf-8").splitlines()
        )
        expected = binding()
        capability = issuer().issue(expected)
        request = b"one exact blinded recovery request"
        proof = create_client_proof(capability, private_key(32), request)
        capability_payload = decode_canonical_object(
            capability.payload, "admission capability"
        )
        proof_payload = decode_canonical_object(proof, "admission client proof")
        self.assertEqual(expected_vector["profile_id"], LOCAL_ISSUER_PROFILE)
        self.assertEqual(
            expected_vector["issuer_signature"], capability_payload["signature"]
        )
        self.assertEqual(
            expected_vector["capability_digest"], capability_digest(capability)
        )
        self.assertEqual(expected_vector["request_digest"], request_digest(request))
        self.assertEqual(
            expected_vector["client_signature"], proof_payload["signature"]
        )

    def test_concrete_verifiers_and_gateway_satisfy_stable_interfaces(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            local_verifier = verifier(Path(temporary) / "interface.sqlite3")
            gateway = LocalAdmissionStorageGateway(
                verifier=local_verifier,
                backend=_Backend(),
                audience="locus-storage-gateway",
            )
            try:
                self.assertIsInstance(local_verifier, AdmissionVerifier)
                self.assertIsInstance(local_verifier, StorageCapabilityVerifier)
                self.assertIsInstance(gateway, ApplicationStorageGateway)
            finally:
                local_verifier._replay_store.close()

    def test_each_authorizer_validates_and_replays_independently(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            client_key = private_key(32)
            for party_id in (1, 2, 3):
                expected = binding(
                    audience=f"locus-authorizer-{party_id}",
                    nonce=f"{party_id + 40:02x}" * 32,
                )
                capability = issuer().issue(expected)
                request = f"counted-request-{party_id}".encode("ascii")
                proof = create_client_proof(capability, client_key, request)
                local_verifier = verifier(directory / f"party-{party_id}.sqlite3")
                try:
                    first = local_verifier.verify(
                        capability, expected, proof, request, now=NOW
                    )
                    second = local_verifier.verify(
                        capability, expected, proof, request, now=NOW
                    )
                    self.assertEqual(first, second)
                    self.assertEqual(local_verifier._replay_store.record_count(), 1)
                finally:
                    local_verifier._replay_store.close()

    def test_wrong_scope_key_time_signature_and_nonce_reuse_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            local_verifier = verifier(Path(temporary) / "authorizer.sqlite3")
            client_key = private_key(32)
            expected = binding()
            capability = issuer().issue(expected)
            request = b"one exact blinded recovery request"
            proof = create_client_proof(capability, client_key, request)
            try:
                local_verifier.verify(capability, expected, proof, request, now=NOW)
                mutations: list[dict[str, object]] = [
                    {"subject": OTHER_SUBJECT},
                    {"audience": "locus-authorizer-2"},
                    {"operation": "storage_read_exact"},
                    {"backup_id": "23" * 16},
                    {"epoch": 8},
                    {"nonce": "34" * 32},
                ]
                for mutation in mutations:
                    with self.subTest(mutation=mutation):
                        changed = AdmissionBinding(
                            **{
                                **expected.__dict__,
                                **mutation,
                                "object_prefix": (
                                    pseudonymous_object_prefix(
                                        str(mutation.get("subject", SUBJECT)),
                                        str(mutation.get("backup_id", BACKUP_ID)),
                                    )
                                    if mutation.get("operation") == "storage_read_exact"
                                    else None
                                ),
                            }
                        )
                        with self.assertRaises(AdmissionVerificationError):
                            local_verifier.verify(
                                capability, changed, proof, request, now=NOW
                            )

                with self.assertRaises(AdmissionVerificationError):
                    local_verifier.verify(
                        capability, expected, proof, request, now=expected.expires_at
                    )
                tampered = type(capability)(
                    capability.format_id,
                    capability.payload.replace(b'"epoch":7', b'"epoch":8'),
                )
                with self.assertRaises(AdmissionVerificationError):
                    local_verifier.verify(tampered, expected, proof, request, now=NOW)
                with self.assertRaises(AdmissionVerificationError):
                    create_client_proof(capability, private_key(64), request)

                changed_request = b"different blinded recovery request"
                changed_proof = create_client_proof(
                    capability, client_key, changed_request
                )
                with self.assertRaises(AdmissionReplayConflict):
                    local_verifier.verify(
                        capability,
                        expected,
                        changed_proof,
                        changed_request,
                        now=NOW,
                    )
            finally:
                local_verifier._replay_store.close()

    def test_storage_gateway_validates_before_backend_access(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            local_verifier = verifier(Path(temporary) / "gateway.sqlite3")
            backend = _Backend()
            gateway = LocalAdmissionStorageGateway(
                verifier=local_verifier,
                backend=backend,
                audience="locus-storage-gateway",
            )
            reference = BackupReference(bid=BACKUP_ID, epoch=7, backup_digest="44" * 32)
            prefix = pseudonymous_object_prefix(SUBJECT, BACKUP_ID)
            request = GatewayRequest(
                operation=StorageOperation.READ_EXACT,
                object_key=prefix + "bundle.zip",
                backup_reference=reference,
            )
            expected = binding(
                audience="locus-storage-gateway",
                operation="storage_read_exact",
                object_prefix=prefix,
                nonce="55" * 32,
            )
            capability = issuer().issue(expected)
            proof = create_client_proof(
                capability, private_key(32), gateway_request_bytes(request)
            )
            try:
                result = gateway.execute(request, capability, expected, proof, now=NOW)
                self.assertEqual(result.payload, b"stored")
                self.assertEqual(backend.calls, 1)

                wrong_key_request = GatewayRequest(
                    operation=StorageOperation.READ_EXACT,
                    object_key=prefix + "../other.zip",
                    backup_reference=reference,
                )
                with self.assertRaises(AdmissionVerificationError):
                    gateway.execute(
                        wrong_key_request, capability, expected, proof, now=NOW
                    )
                self.assertEqual(backend.calls, 1)

                wrong_operation = GatewayRequest(
                    operation=StorageOperation.DELETE_EXACT,
                    object_key=request.object_key,
                    backup_reference=reference,
                )
                with self.assertRaises(AdmissionVerificationError):
                    gateway.execute(
                        wrong_operation, capability, expected, proof, now=NOW
                    )
                self.assertEqual(backend.calls, 1)
            finally:
                local_verifier._replay_store.close()

    def test_deterministic_profile_has_no_external_identity_dependency(self) -> None:
        expected = binding()
        capability_a = issuer().issue(expected)
        capability_b = issuer().issue(expected)
        self.assertEqual(capability_a, capability_b)
        self.assertEqual(
            capability_digest(capability_a), capability_digest(capability_b)
        )
        with self.assertRaises(AdmissionVerificationError):
            issuer().issue(
                AdmissionBinding(**{**expected.__dict__, "subject": OTHER_SUBJECT})
            )

    def test_replay_database_retains_only_digests(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            database_path = Path(temporary) / "privacy-safe-replay.sqlite3"
            local_verifier = verifier(database_path)
            expected = binding()
            capability = issuer().issue(expected)
            request = b"privacy-safe admitted request"
            proof = create_client_proof(capability, private_key(32), request)
            local_verifier.verify(capability, expected, proof, request, now=NOW)
            local_verifier._replay_store.close()
            database_bytes = database_path.read_bytes()
            self.assertNotIn(capability.payload, database_bytes)
            self.assertNotIn(proof, database_bytes)
            self.assertNotIn(bytes.fromhex(SUBJECT), database_bytes)
            self.assertNotIn(request, database_bytes)


if __name__ == "__main__":
    unittest.main()
