from __future__ import annotations

import os
import unittest

from locus.s3_object_store import S3BackupObjectStore

from tests.object_store_contract import exercise_backend_contract


def _live_s3_configured() -> bool:
    required = (
        "LOCUS_S3_TEST_ENDPOINT",
        "LOCUS_S3_TEST_BUCKET",
        "LOCUS_S3_TEST_ACCESS_KEY",
        "LOCUS_S3_TEST_SECRET_KEY",
        "LOCUS_S3_TEST_PREFIX",
    )
    return os.environ.get("LOCUS_RUN_S3_LIVE_TEST") == "1" and all(
        os.environ.get(name) for name in required
    )


@unittest.skipUnless(_live_s3_configured(), "live S3 test not requested")
class LiveS3BackupObjectStoreTests(unittest.TestCase):
    def test_shared_contract_against_live_s3_compatible_service(self) -> None:
        store = S3BackupObjectStore.from_credentials(
            bucket=os.environ["LOCUS_S3_TEST_BUCKET"],
            endpoint_url=os.environ["LOCUS_S3_TEST_ENDPOINT"],
            access_key=os.environ["LOCUS_S3_TEST_ACCESS_KEY"],
            secret_key=os.environ["LOCUS_S3_TEST_SECRET_KEY"],
            prefix=os.environ["LOCUS_S3_TEST_PREFIX"],
            allow_http=True,
            verify=False,
            timeout_seconds=5.0,
        )
        exercise_backend_contract(self, store)


if __name__ == "__main__":
    unittest.main()
