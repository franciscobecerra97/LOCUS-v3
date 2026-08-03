"""Separately authorized, read-only AWS S3 connectivity gate."""

from __future__ import annotations

import os
import unittest

from locus.storage_provider import AWS_S3_PROVIDER_ID, AwsS3StorageProvider


def _aws_test_configured() -> bool:
    required = (
        "LOCUS_AWS_S3_TEST_BUCKET",
        "LOCUS_AWS_S3_TEST_ACCESS_KEY",
        "LOCUS_AWS_S3_TEST_SECRET_KEY",
        "LOCUS_AWS_S3_TEST_REGION",
        "LOCUS_AWS_S3_TEST_PREFIX",
    )
    return os.environ.get("LOCUS_RUN_AWS_S3_TEST") == "1" and all(
        os.environ.get(name) for name in required
    )


@unittest.skipUnless(
    _aws_test_configured(), "separately authorized AWS S3 test not requested"
)
class LiveAwsS3ConnectivityTests(unittest.TestCase):
    def test_explicit_tls_profile_can_reach_the_disposable_bucket(self) -> None:
        provider = AwsS3StorageProvider.from_aws_credentials(
            bucket=os.environ["LOCUS_AWS_S3_TEST_BUCKET"],
            access_key=os.environ["LOCUS_AWS_S3_TEST_ACCESS_KEY"],
            secret_key=os.environ["LOCUS_AWS_S3_TEST_SECRET_KEY"],
            session_token=os.environ.get("LOCUS_AWS_S3_TEST_SESSION_TOKEN"),
            region=os.environ["LOCUS_AWS_S3_TEST_REGION"],
            provider_prefix=os.environ["LOCUS_AWS_S3_TEST_PREFIX"],
            timeout_seconds=5.0,
        )
        self.assertEqual(provider.properties.provider_id, AWS_S3_PROVIDER_ID)
        self.assertEqual(provider.properties.transport, "tls")
        provider.backups.probe()


if __name__ == "__main__":
    unittest.main()
