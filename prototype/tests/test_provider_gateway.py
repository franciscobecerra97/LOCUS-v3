from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from locus.admission import (
    AdmissionBinding,
    client_key_thumbprint,
    pseudonymous_object_prefix,
)
from locus.contracts import (
    CurrentDescriptorPointer,
    GatewayRequest,
    GatewayResult,
    StorageOperation,
)
from locus.local_admission import (
    AdmissionReplayStore,
    AdmissionVerificationError,
    LocalAdmissionStorageGateway,
    LocalAdmissionVerifier,
    create_client_proof,
    gateway_request_bytes,
)
from locus.object_store import ObjectStale, encode_backup_object
from locus.provider_gateway import (
    ProviderStorageGatewayBackend,
    aws_prefix_policy,
    backup_object_key,
    bundle_object_key,
    current_pointer_object_key,
    descriptor_object_key,
    encode_pointer_cas,
)
from locus.recovery_descriptor import CURRENT_POINTER_VERSION
from locus.storage_provider import AWS_S3_PROVIDER_ID, AwsS3StorageProvider

from tests.test_descriptor_store import FakeCasS3Client, pointer_variant
from tests.test_local_admission import (
    ISSUER_ID,
    ISSUER_KEY_ID,
    NOW,
    issuer,
    private_key,
    raw_public_key,
)
from tests.test_recovery_descriptor import (
    BACKUP_ID,
    SUBJECT_ID,
    build_vector,
    synthetic_backup,
)

AUDIENCE = "locus-storage-gateway"
RECOVERY_HANDLE = f"test-only-recovery:{BACKUP_ID}:1"


class ProviderGatewayTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.client = FakeCasS3Client()
        self.provider = AwsS3StorageProvider(
            client=self.client,
            bucket="locus-aws-provider-tests",
            backup_prefix="application/test/backups",
            descriptor_prefix="application/test/recovery",
        )
        self.backend = ProviderStorageGatewayBackend(
            provider=self.provider,
            subject_id=SUBJECT_ID,
            recovery_handle=RECOVERY_HANDLE,
        )
        local_issuer = issuer()
        self.verifier = LocalAdmissionVerifier(
            issuer=ISSUER_ID,
            issuer_key_id=ISSUER_KEY_ID,
            issuer_public_key=local_issuer.public_key,
            replay_store=AdmissionReplayStore(
                Path(self.temporary.name) / "gateway-replay.sqlite3"
            ),
        )
        self.addCleanup(self.verifier._replay_store.close)
        self.gateway = LocalAdmissionStorageGateway(
            verifier=self.verifier,
            backend=self.backend,
            audience=AUDIENCE,
        )
        self.client_key = private_key(32)
        self.operation_index = 0
        backup = synthetic_backup()
        self.backup_reference, self.encoded_backup = encode_backup_object(backup)
        self.assertEqual(self.backup_reference.bid, BACKUP_ID)
        self.vector = build_vector()

    def execute(self, request: GatewayRequest) -> GatewayResult:
        self.operation_index += 1
        operation = f"storage_{request.operation.value}"
        expected = AdmissionBinding(
            subject=SUBJECT_ID,
            backup_id=request.backup_reference.bid,
            epoch=request.backup_reference.epoch,
            operation=operation,
            audience=AUDIENCE,
            client_key_thumbprint=client_key_thumbprint(
                raw_public_key(self.client_key)
            ),
            nonce=f"{self.operation_index:064x}",
            issued_at=NOW - 10,
            expires_at=NOW + 110,
            issuer=ISSUER_ID,
            object_prefix=pseudonymous_object_prefix(
                SUBJECT_ID, request.backup_reference.bid
            ),
        )
        capability = issuer().issue(expected)
        proof = create_client_proof(
            capability, self.client_key, gateway_request_bytes(request)
        )
        return self.gateway.execute(request, capability, expected, proof, now=NOW)

    def test_all_provider_roles_execute_through_admitted_exact_keys(self) -> None:
        backup_create = GatewayRequest(
            operation=StorageOperation.CREATE_IMMUTABLE,
            object_key=backup_object_key(SUBJECT_ID, self.backup_reference),
            backup_reference=self.backup_reference,
            payload=self.encoded_backup,
        )
        self.execute(backup_create)
        backup_read = GatewayRequest(
            operation=StorageOperation.READ_EXACT,
            object_key=backup_create.object_key,
            backup_reference=self.backup_reference,
        )
        self.assertEqual(self.execute(backup_read).payload, self.encoded_backup)

        descriptor = self.vector["descriptor"]
        bundle = self.vector["bundle"]
        pointer = self.vector["pointer"]
        assert isinstance(descriptor, bytes)
        assert isinstance(bundle, bytes)
        assert isinstance(pointer, bytes)
        descriptor_digest = hashlib.sha256(descriptor).hexdigest()
        descriptor_key = descriptor_object_key(
            SUBJECT_ID, self.backup_reference, descriptor_digest
        )
        self.execute(
            GatewayRequest(
                operation=StorageOperation.CREATE_IMMUTABLE,
                object_key=descriptor_key,
                backup_reference=self.backup_reference,
                payload=descriptor,
            )
        )
        self.assertEqual(
            self.execute(
                GatewayRequest(
                    operation=StorageOperation.READ_EXACT,
                    object_key=descriptor_key,
                    backup_reference=self.backup_reference,
                )
            ).payload,
            descriptor,
        )

        bundle_digest = hashlib.sha256(bundle).hexdigest()
        bundle_key = bundle_object_key(
            SUBJECT_ID, self.backup_reference, bundle_digest, len(bundle)
        )
        self.execute(
            GatewayRequest(
                operation=StorageOperation.CREATE_IMMUTABLE,
                object_key=bundle_key,
                backup_reference=self.backup_reference,
                payload=bundle,
            )
        )
        self.assertEqual(
            self.execute(
                GatewayRequest(
                    operation=StorageOperation.READ_EXACT,
                    object_key=bundle_key,
                    backup_reference=self.backup_reference,
                )
            ).payload,
            bundle,
        )

        current_key = current_pointer_object_key(
            SUBJECT_ID, self.backup_reference, RECOVERY_HANDLE
        )
        initial = CurrentDescriptorPointer(CURRENT_POINTER_VERSION, pointer)
        self.execute(
            GatewayRequest(
                operation=StorageOperation.COMPARE_AND_SWAP,
                object_key=current_key,
                backup_reference=self.backup_reference,
                payload=encode_pointer_cas(expected=None, replacement=initial),
            )
        )
        self.assertEqual(
            self.execute(
                GatewayRequest(
                    operation=StorageOperation.READ_EXACT,
                    object_key=current_key,
                    backup_reference=self.backup_reference,
                )
            ).payload,
            pointer,
        )
        successor = pointer_variant(1)
        self.execute(
            GatewayRequest(
                operation=StorageOperation.COMPARE_AND_SWAP,
                object_key=current_key,
                backup_reference=self.backup_reference,
                payload=encode_pointer_cas(expected=initial, replacement=successor),
            )
        )
        with self.assertRaises(ObjectStale):
            self.execute(
                GatewayRequest(
                    operation=StorageOperation.COMPARE_AND_SWAP,
                    object_key=current_key,
                    backup_reference=self.backup_reference,
                    payload=encode_pointer_cas(
                        expected=initial, replacement=pointer_variant(2)
                    ),
                )
            )
        self.assertEqual(self.client.list_calls, 0)

    def test_cross_account_key_is_denied_before_backend_access(self) -> None:
        request = GatewayRequest(
            operation=StorageOperation.READ_EXACT,
            object_key=backup_object_key("12" * 32, self.backup_reference),
            backup_reference=self.backup_reference,
        )
        with self.assertRaises(AdmissionVerificationError):
            self.execute(request)
        self.assertFalse(self.client.objects)

    def test_aws_profile_and_policy_are_tls_exact_prefix_and_no_list(self) -> None:
        self.assertEqual(self.provider.properties.provider_id, AWS_S3_PROVIDER_ID)
        self.assertEqual(self.provider.properties.transport, "tls")
        prefix = pseudonymous_object_prefix(SUBJECT_ID, BACKUP_ID).rstrip("/")
        policy = aws_prefix_policy(bucket=self.provider.bucket, prefix=prefix)
        encoded = json.dumps(policy, sort_keys=True)
        self.assertIn(f"arn:aws:s3:::{self.provider.bucket}/{prefix}/*", encoded)
        self.assertIn("aws:SecureTransport", encoded)
        self.assertNotIn("List", encoded)
        self.assertNotIn(SUBJECT_ID, encoded)

    def test_aws_constructor_forwards_explicit_session_credentials_only(self) -> None:
        captured: dict[str, object] = {}

        class FakeConfig:
            def __init__(self, **kwargs: object) -> None:
                captured["config"] = kwargs

        class FakeBoto:
            @staticmethod
            def client(name: str, **kwargs: object) -> FakeCasS3Client:
                captured["name"] = name
                captured["kwargs"] = kwargs
                return self.client

        def imported(name: str) -> object:
            if name == "boto3":
                return FakeBoto
            if name == "botocore.config":
                return type("ConfigModule", (), {"Config": FakeConfig})
            raise AssertionError(name)

        with mock.patch(
            "locus.s3_object_store.importlib.import_module", side_effect=imported
        ):
            provider = AwsS3StorageProvider.from_aws_credentials(
                bucket="locus-aws-provider-tests",
                access_key="synthetic-access",
                secret_key="synthetic-secret",
                session_token="synthetic-session",
                region="eu-west-1",
                provider_prefix="application/account-test",
            )
        kwargs = captured["kwargs"]
        assert isinstance(kwargs, dict)
        self.assertEqual(kwargs["aws_access_key_id"], "synthetic-access")
        self.assertEqual(kwargs["aws_secret_access_key"], "synthetic-secret")
        self.assertEqual(kwargs["aws_session_token"], "synthetic-session")
        self.assertIsNone(kwargs["endpoint_url"])
        self.assertEqual(provider.properties.provider_id, AWS_S3_PROVIDER_ID)
        representation = repr(provider)
        self.assertNotIn("synthetic-access", representation)
        self.assertNotIn("synthetic-secret", representation)
        self.assertNotIn("synthetic-session", representation)


if __name__ == "__main__":
    unittest.main()
