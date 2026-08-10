"""S3-compatible implementation of the frozen LOCUS backup-store contract."""

from __future__ import annotations

import base64
import hashlib
import importlib
import re
from collections.abc import Mapping
from typing import Any, Protocol
from urllib.parse import urlsplit

from .object_store import (
    MAX_BACKUP_OBJECT_BYTES,
    BackupReference,
    ObjectConflict,
    ObjectCorrupt,
    ObjectNotFound,
    ObjectStoreError,
    ObjectStoreUnavailable,
    ObjectTooLarge,
    decode_backup_object,
    decode_versioned_backup_object,
    encode_backup_object,
    encode_versioned_backup_object,
)

DEFAULT_REGION = "us-east-1"
DEFAULT_PREFIX = "locus/backups"
MAX_CONDITIONAL_WRITE_ATTEMPTS = 3


class _StreamingBody(Protocol):
    def read(self, amount: int | None = None) -> bytes: ...

    def close(self) -> None: ...


class S3Client(Protocol):
    """Narrow client surface, enabling deterministic adapter tests."""

    def put_object(self, **kwargs: Any) -> dict[str, Any]: ...

    def get_object(self, **kwargs: Any) -> dict[str, Any]: ...

    def head_object(self, **kwargs: Any) -> dict[str, Any]: ...

    def delete_object(self, **kwargs: Any) -> dict[str, Any]: ...

    def head_bucket(self, **kwargs: Any) -> dict[str, Any]: ...


def _validate_bucket(bucket: object) -> str:
    if (
        not isinstance(bucket, str)
        or len(bucket) < 3
        or len(bucket) > 63
        or re.fullmatch(r"[a-z0-9][a-z0-9.-]*[a-z0-9]", bucket) is None
        or ".." in bucket
        or bucket.startswith(("xn--", "sthree-", "amzn_s3_demo_"))
    ):
        raise ObjectCorrupt("invalid S3 bucket name")
    return bucket


def _validate_prefix(prefix: object) -> str:
    if not isinstance(prefix, str) or not prefix or len(prefix) > 256:
        raise ObjectCorrupt("invalid S3 object prefix")
    normalized = prefix.strip("/")
    components = normalized.split("/")
    if (
        not normalized
        or any(component in {"", ".", ".."} for component in components)
        or any(
            re.fullmatch(r"[A-Za-z0-9._-]+", component) is None
            for component in components
        )
    ):
        raise ObjectCorrupt("invalid S3 object prefix")
    return normalized


def _error_details(error: BaseException) -> tuple[str, int | None]:
    response = getattr(error, "response", None)
    if not isinstance(response, Mapping):
        return "", None
    error_value = response.get("Error")
    metadata = response.get("ResponseMetadata")
    code = ""
    status: int | None = None
    if isinstance(error_value, Mapping):
        raw_code = error_value.get("Code")
        if isinstance(raw_code, str):
            code = raw_code
    if isinstance(metadata, Mapping):
        raw_status = metadata.get("HTTPStatusCode")
        if isinstance(raw_status, int) and not isinstance(raw_status, bool):
            status = raw_status
    return code, status


def _is_not_found(error: BaseException) -> bool:
    code, status = _error_details(error)
    return status == 404 or code in {"404", "NoSuchKey", "NotFound", "NoSuchBucket"}


def _is_precondition_failed(error: BaseException) -> bool:
    code, status = _error_details(error)
    return status == 412 or code in {"412", "PreconditionFailed"}


def _is_conditional_conflict(error: BaseException) -> bool:
    code, status = _error_details(error)
    return status == 409 or code in {"409", "ConditionalRequestConflict"}


class S3BackupObjectStore:
    """Immutable S3 adapter using SigV4 conditional writes.

    The client must have access only to the configured bucket/prefix. This class
    never lists buckets or objects and never trusts ETags or mutable metadata for
    backup acceptance; the canonical envelope and party-pinned digest remain the
    authority.
    """

    def __init__(
        self,
        *,
        client: S3Client,
        bucket: str,
        prefix: str = DEFAULT_PREFIX,
    ) -> None:
        self._client = client
        self.bucket = _validate_bucket(bucket)
        self.prefix = _validate_prefix(prefix)

    @classmethod
    def from_credentials(
        cls,
        *,
        bucket: str,
        access_key: str,
        secret_key: str,
        session_token: str | None = None,
        endpoint_url: str | None = None,
        region: str = DEFAULT_REGION,
        prefix: str = DEFAULT_PREFIX,
        allow_http: bool = False,
        verify: bool | str = True,
        timeout_seconds: float = 2.0,
    ) -> S3BackupObjectStore:
        """Build a pinned SigV4 client without using ambient credential lookup."""

        if (
            not isinstance(access_key, str)
            or not access_key
            or len(access_key) > 128
            or not isinstance(secret_key, str)
            or len(secret_key) < 8
            or len(secret_key) > 256
            or session_token is not None
            and (
                not isinstance(session_token, str)
                or not session_token
                or len(session_token) > 4096
            )
        ):
            raise ObjectCorrupt("invalid S3 credentials")
        if (
            not isinstance(region, str)
            or re.fullmatch(r"[a-z0-9-]{1,64}", region) is None
        ):
            raise ObjectCorrupt("invalid S3 region")
        if (
            isinstance(timeout_seconds, bool)
            or not isinstance(timeout_seconds, (int, float))
            or timeout_seconds <= 0
            or timeout_seconds > 60
        ):
            raise ObjectCorrupt("invalid S3 timeout")
        if endpoint_url is not None:
            if not isinstance(endpoint_url, str) or len(endpoint_url) > 2048:
                raise ObjectCorrupt("invalid S3 endpoint")
            parsed = urlsplit(endpoint_url)
            try:
                port = parsed.port
            except ValueError as exc:
                raise ObjectCorrupt("invalid S3 endpoint") from exc
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.hostname
                or parsed.username is not None
                or parsed.password is not None
                or parsed.query
                or parsed.fragment
                or parsed.path not in {"", "/"}
                or port is not None
                and not 1 <= port <= 65535
            ):
                raise ObjectCorrupt("invalid S3 endpoint")
            if parsed.scheme == "http" and not allow_http:
                raise ObjectCorrupt("plaintext S3 endpoint requires explicit opt-in")

        try:
            boto3 = importlib.import_module("boto3")
            config_class = importlib.import_module("botocore.config").Config
            client = boto3.client(
                "s3",
                endpoint_url=endpoint_url,
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                aws_session_token=session_token,
                region_name=region,
                verify=verify,
                config=config_class(
                    signature_version="s3v4",
                    connect_timeout=float(timeout_seconds),
                    read_timeout=float(timeout_seconds),
                    retries={"max_attempts": 2, "mode": "standard"},
                    s3={"addressing_style": "path"},
                ),
            )
        except (ImportError, AttributeError, TypeError, ValueError) as exc:
            raise ObjectStoreUnavailable("S3 client could not be initialized") from exc
        return cls(client=client, bucket=bucket, prefix=prefix)

    def object_key(self, reference: BackupReference) -> str:
        reference.validate()
        return f"{self.prefix}/{reference.bid}/{reference.epoch}.json"

    def probe(self) -> None:
        """Verify that the configured bucket is reachable without listing data."""

        try:
            self._client.head_bucket(Bucket=self.bucket)
        except Exception as exc:
            if _is_not_found(exc):
                raise ObjectNotFound("S3 bucket was not found") from exc
            raise ObjectStoreUnavailable("S3 object store is unavailable") from exc

    def _read_encoded(self, reference: BackupReference) -> bytes:
        key = self.object_key(reference)
        try:
            response = self._client.get_object(Bucket=self.bucket, Key=key)
        except Exception as exc:
            if _is_not_found(exc):
                raise ObjectNotFound("cloud backup object was not found") from exc
            raise ObjectStoreUnavailable("S3 object store is unavailable") from exc
        if not isinstance(response, dict):
            raise ObjectStoreUnavailable("invalid S3 response")
        content_length = response.get("ContentLength")
        if (
            isinstance(content_length, bool)
            or not isinstance(content_length, int)
            or content_length < 0
        ):
            raise ObjectStoreUnavailable("invalid S3 content length")
        body = response.get("Body")
        if body is None or not hasattr(body, "read") or not hasattr(body, "close"):
            raise ObjectStoreUnavailable("invalid S3 response body")
        streaming_body: _StreamingBody = body
        try:
            if content_length > MAX_BACKUP_OBJECT_BYTES:
                raise ObjectTooLarge("cloud backup object exceeds size limit")
            encoded = streaming_body.read(MAX_BACKUP_OBJECT_BYTES + 1)
        except ObjectStoreError:
            raise
        except Exception as exc:
            raise ObjectStoreUnavailable("S3 object read failed") from exc
        finally:
            try:
                streaming_body.close()
            except Exception:
                pass
        if not isinstance(encoded, bytes):
            raise ObjectStoreUnavailable("invalid S3 response body")
        if len(encoded) > MAX_BACKUP_OBJECT_BYTES:
            raise ObjectTooLarge("cloud backup object exceeds size limit")
        if len(encoded) != content_length:
            raise ObjectStoreUnavailable("incomplete S3 object read")
        return encoded

    def read_encoded(self, reference: BackupReference) -> bytes:
        """Return exact validated stored bytes for a cloud-snapshot capture."""

        reference.validate()
        encoded = self._read_encoded(reference)
        decode_backup_object(encoded, expected=reference)
        return encoded

    def create(self, backup: dict[str, Any]) -> BackupReference:
        reference, encoded = encode_backup_object(backup)
        key = self.object_key(reference)
        checksum = base64.b64encode(hashlib.sha256(encoded).digest()).decode("ascii")
        for attempt in range(MAX_CONDITIONAL_WRITE_ATTEMPTS):
            try:
                self._client.put_object(
                    Bucket=self.bucket,
                    Key=key,
                    Body=encoded,
                    ContentLength=len(encoded),
                    ContentType="application/json",
                    ChecksumSHA256=checksum,
                    IfNoneMatch="*",
                    Metadata={
                        "locus-backup-digest": reference.backup_digest,
                        "locus-object-version": "v1",
                    },
                )
                return reference
            except Exception as exc:
                if _is_precondition_failed(exc):
                    try:
                        existing = self._read_encoded(reference)
                    except ObjectNotFound:
                        if attempt + 1 < MAX_CONDITIONAL_WRITE_ATTEMPTS:
                            continue
                        raise ObjectStoreUnavailable(
                            "S3 conditional write raced with deletion"
                        ) from exc
                    if existing == encoded:
                        return reference
                    raise ObjectConflict(
                        "immutable cloud backup object already exists"
                    ) from None
                if _is_conditional_conflict(exc) and (
                    attempt + 1 < MAX_CONDITIONAL_WRITE_ATTEMPTS
                ):
                    continue
                raise ObjectStoreUnavailable("S3 object store is unavailable") from exc
        raise ObjectStoreUnavailable("S3 conditional write did not converge")

    def create_versioned(self, backup: dict[str, Any]) -> BackupReference:
        """Publish a v5/v6 object without widening the frozen v1 operation."""

        reference, encoded = encode_versioned_backup_object(backup)
        key = self.object_key(reference)
        checksum = base64.b64encode(hashlib.sha256(encoded).digest()).decode("ascii")
        for attempt in range(MAX_CONDITIONAL_WRITE_ATTEMPTS):
            try:
                self._client.put_object(
                    Bucket=self.bucket,
                    Key=key,
                    Body=encoded,
                    ContentLength=len(encoded),
                    ContentType="application/json",
                    ChecksumSHA256=checksum,
                    IfNoneMatch="*",
                    Metadata={
                        "locus-backup-digest": reference.backup_digest,
                        "locus-object-version": "v2",
                    },
                )
                return reference
            except Exception as exc:
                if _is_precondition_failed(exc):
                    try:
                        existing = self._read_encoded(reference)
                    except ObjectNotFound:
                        if attempt + 1 < MAX_CONDITIONAL_WRITE_ATTEMPTS:
                            continue
                        raise ObjectStoreUnavailable(
                            "S3 conditional write raced with deletion"
                        ) from exc
                    if existing == encoded:
                        return reference
                    raise ObjectConflict(
                        "immutable cloud backup object already exists"
                    ) from None
                if _is_conditional_conflict(exc) and (
                    attempt + 1 < MAX_CONDITIONAL_WRITE_ATTEMPTS
                ):
                    continue
                raise ObjectStoreUnavailable("S3 object store is unavailable") from exc
        raise ObjectStoreUnavailable("S3 conditional write did not converge")

    def read(self, reference: BackupReference) -> dict[str, Any]:
        reference.validate()
        encoded = self._read_encoded(reference)
        _, backup = decode_backup_object(encoded, expected=reference)
        return backup

    def read_versioned(self, reference: BackupReference) -> dict[str, Any]:
        """Read and validate the exact v5/v6 envelope."""

        reference.validate()
        encoded = self._read_encoded(reference)
        _, backup = decode_versioned_backup_object(encoded, expected=reference)
        return backup

    def delete(self, reference: BackupReference) -> None:
        key = self.object_key(reference)
        try:
            self._client.head_object(Bucket=self.bucket, Key=key)
        except Exception as exc:
            if _is_not_found(exc):
                raise ObjectNotFound("cloud backup object was not found") from exc
            raise ObjectStoreUnavailable("S3 object store is unavailable") from exc
        try:
            self._client.delete_object(Bucket=self.bucket, Key=key)
        except Exception as exc:
            raise ObjectStoreUnavailable("S3 object store is unavailable") from exc
