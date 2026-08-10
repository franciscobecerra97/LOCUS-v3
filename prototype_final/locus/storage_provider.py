"""Provider-level composition for LOCUS storage contracts.

The backup object, immutable descriptor, recovery bundle, and mutable current
pointer retain their distinct contracts.  This module only groups adapters
that share one provider namespace so the same conformance and gateway layers
can exercise them without weakening those boundaries.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, runtime_checkable

from .contracts import DescriptorStore
from .descriptor_store import (
    DEFAULT_DESCRIPTOR_PREFIX,
    FilesystemDescriptorBundleStore,
    RecoveryBundleStore,
    S3DescriptorBundleStore,
)
from .object_store import BackupObjectStore, FilesystemBackupObjectStore
from .s3_object_store import DEFAULT_PREFIX, S3BackupObjectStore, S3Client

STORAGE_PROVIDER_PROFILE = "LOCUS-storage-provider-profile-v1"
FILESYSTEM_PROVIDER_ID = "LOCUS-storage-provider-filesystem-v1"
S3_COMPATIBLE_PROVIDER_ID = "LOCUS-storage-provider-s3-compatible-v1"
AWS_S3_PROVIDER_ID = "LOCUS-storage-provider-aws-s3-v1"
DEFAULT_PROVIDER_PREFIX = "locus/account"


@dataclass(frozen=True)
class StorageProviderProperties:
    """Public conformance properties; never contains provider credentials."""

    provider_id: str
    network_scope: str
    transport: str
    credential_mode: str
    exact_reads_only: bool = True
    listing_required: bool = False
    immutable_backup_publication: bool = True
    immutable_descriptor_publication: bool = True
    current_pointer_cas: bool = True

    def __post_init__(self) -> None:
        if self.provider_id not in {
            FILESYSTEM_PROVIDER_ID,
            S3_COMPATIBLE_PROVIDER_ID,
            AWS_S3_PROVIDER_ID,
        }:
            raise ValueError("unsupported storage provider")
        if self.network_scope not in {"local", "nonlocal"}:
            raise ValueError("invalid storage network scope")
        if self.transport not in {"none", "tls", "local-test-plaintext"}:
            raise ValueError("invalid storage transport")
        if self.credential_mode not in {"none", "explicit-prefix-scoped"}:
            raise ValueError("invalid storage credential mode")
        if self.network_scope == "nonlocal" and self.transport != "tls":
            raise ValueError("nonlocal storage requires TLS")
        if self.listing_required:
            raise ValueError("LOCUS storage must not require listing")


@runtime_checkable
class StorageProvider(Protocol):
    """Composite provider boundary with deliberately separate object roles."""

    @property
    def profile_id(self) -> str: ...

    @property
    def properties(self) -> StorageProviderProperties: ...

    @property
    def backups(self) -> BackupObjectStore: ...

    @property
    def descriptors(self) -> DescriptorStore: ...

    @property
    def bundles(self) -> RecoveryBundleStore: ...


@dataclass
class FilesystemStorageProvider:
    """Deterministic local provider used by the default reviewer path."""

    root: Path
    profile_id: str = field(default=STORAGE_PROVIDER_PROFILE, init=False)
    properties: StorageProviderProperties = field(init=False)
    backups: FilesystemBackupObjectStore = field(init=False, repr=False)
    descriptors: FilesystemDescriptorBundleStore = field(init=False, repr=False)
    bundles: RecoveryBundleStore = field(init=False, repr=False)

    def __post_init__(self) -> None:
        requested = Path(self.root)
        self.backups = FilesystemBackupObjectStore(requested / "backups")
        self.descriptors = FilesystemDescriptorBundleStore(requested / "recovery")
        self.bundles = self.descriptors
        self.root = requested.resolve(strict=True)
        self.properties = StorageProviderProperties(
            provider_id=FILESYSTEM_PROVIDER_ID,
            network_scope="local",
            transport="none",
            credential_mode="none",
        )


@dataclass
class S3CompatibleStorageProvider:
    """One explicitly scoped S3 client shared by disjoint LOCUS namespaces."""

    client: S3Client = field(repr=False)
    bucket: str
    backup_prefix: str = DEFAULT_PREFIX
    descriptor_prefix: str = DEFAULT_DESCRIPTOR_PREFIX
    network_scope: str = "nonlocal"
    transport: str = "tls"
    profile_id: str = field(default=STORAGE_PROVIDER_PROFILE, init=False)
    properties: StorageProviderProperties = field(init=False)
    backups: S3BackupObjectStore = field(init=False, repr=False)
    descriptors: S3DescriptorBundleStore = field(init=False, repr=False)
    bundles: RecoveryBundleStore = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self.backups = S3BackupObjectStore(
            client=self.client,
            bucket=self.bucket,
            prefix=self.backup_prefix,
        )
        self.descriptors = S3DescriptorBundleStore(
            client=self.client,
            bucket=self.bucket,
            prefix=self.descriptor_prefix,
        )
        self.bundles = self.descriptors
        self.bucket = self.backups.bucket
        self.backup_prefix = self.backups.prefix
        self.descriptor_prefix = self.descriptors.prefix
        self.properties = StorageProviderProperties(
            provider_id=S3_COMPATIBLE_PROVIDER_ID,
            network_scope=self.network_scope,
            transport=self.transport,
            credential_mode="explicit-prefix-scoped",
        )

    @classmethod
    def from_credentials(
        cls,
        *,
        bucket: str,
        access_key: str,
        secret_key: str,
        session_token: str | None = None,
        endpoint_url: str | None = None,
        region: str = "us-east-1",
        provider_prefix: str = DEFAULT_PROVIDER_PREFIX,
        allow_http: bool = False,
        verify: bool | str = True,
        timeout_seconds: float = 2.0,
    ) -> S3CompatibleStorageProvider:
        """Create one non-ambient client and split its exact provider prefix."""

        transport = "tls"
        network_scope = "nonlocal"
        if endpoint_url is not None and endpoint_url.startswith("http://"):
            transport = "local-test-plaintext"
            network_scope = "local"
        bootstrap = S3BackupObjectStore.from_credentials(
            bucket=bucket,
            access_key=access_key,
            secret_key=secret_key,
            session_token=session_token,
            endpoint_url=endpoint_url,
            region=region,
            prefix=f"{provider_prefix.strip('/')}/backups",
            allow_http=allow_http,
            verify=verify,
            timeout_seconds=timeout_seconds,
        )
        return cls(
            client=bootstrap._client,
            bucket=bootstrap.bucket,
            backup_prefix=bootstrap.prefix,
            descriptor_prefix=f"{provider_prefix.strip('/')}/recovery",
            network_scope=network_scope,
            transport=transport,
        )


@dataclass
class AwsS3StorageProvider(S3CompatibleStorageProvider):
    """AWS S3 profile with no custom endpoint or ambient credential lookup."""

    def __post_init__(self) -> None:
        super().__post_init__()
        self.properties = StorageProviderProperties(
            provider_id=AWS_S3_PROVIDER_ID,
            network_scope="nonlocal",
            transport="tls",
            credential_mode="explicit-prefix-scoped",
        )

    @classmethod
    def from_aws_credentials(
        cls,
        *,
        bucket: str,
        access_key: str,
        secret_key: str,
        session_token: str | None,
        region: str,
        provider_prefix: str,
        timeout_seconds: float = 2.0,
    ) -> AwsS3StorageProvider:
        bootstrap = S3BackupObjectStore.from_credentials(
            bucket=bucket,
            access_key=access_key,
            secret_key=secret_key,
            session_token=session_token,
            endpoint_url=None,
            region=region,
            prefix=f"{provider_prefix.strip('/')}/backups",
            verify=True,
            timeout_seconds=timeout_seconds,
        )
        return cls(
            client=bootstrap._client,
            bucket=bootstrap.bucket,
            backup_prefix=bootstrap.prefix,
            descriptor_prefix=f"{provider_prefix.strip('/')}/recovery",
            network_scope="nonlocal",
            transport="tls",
        )


__all__ = [
    "AWS_S3_PROVIDER_ID",
    "FILESYSTEM_PROVIDER_ID",
    "S3_COMPATIBLE_PROVIDER_ID",
    "STORAGE_PROVIDER_PROFILE",
    "AwsS3StorageProvider",
    "FilesystemStorageProvider",
    "S3CompatibleStorageProvider",
    "StorageProvider",
    "StorageProviderProperties",
]
