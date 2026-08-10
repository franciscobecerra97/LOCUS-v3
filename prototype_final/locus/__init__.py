"""LOCUS reference prototype package."""

from __future__ import annotations

from importlib import import_module
from typing import Any

_EXPORTS = {
    "BackupReference": (".object_store", "BackupReference"),
    "CuePolicy": (".contracts", "CuePolicy"),
    "CuePolicyRegistry": (".cue_policy_registry", "CuePolicyRegistry"),
    "DEFAULT_CUE_POLICY_REGISTRY": (
        ".cue_policy_registry",
        "DEFAULT_CUE_POLICY_REGISTRY",
    ),
    "FilesystemBackupObjectStore": (
        ".object_store",
        "FilesystemBackupObjectStore",
    ),
    "NoResolverAdapter": (".no_resolver", "NoResolverAdapter"),
    "PasswordProtectedSecretRecovery": (
        ".contracts",
        "PasswordProtectedSecretRecovery",
    ),
    "RecoveryContext": (".contracts", "RecoveryContext"),
    "S3BackupObjectStore": (".s3_object_store", "S3BackupObjectStore"),
    "ThresholdParameters": (".contracts", "ThresholdParameters"),
    "YiTpassRecoveryAdapter": (".yi_compat", "YiTpassRecoveryAdapter"),
    "enroll": (".core", "enroll"),
    "recover": (".core", "recover"),
    "recover_from_store": (".core", "recover_from_store"),
}


def __getattr__(name: str) -> Any:
    target = _EXPORTS.get(name)
    if target is None:
        raise AttributeError(name)
    module_name, attribute = target
    value = getattr(import_module(module_name, __name__), attribute)
    globals()[name] = value
    return value


__all__ = [
    "BackupReference",
    "CuePolicy",
    "CuePolicyRegistry",
    "DEFAULT_CUE_POLICY_REGISTRY",
    "FilesystemBackupObjectStore",
    "NoResolverAdapter",
    "PasswordProtectedSecretRecovery",
    "RecoveryContext",
    "S3BackupObjectStore",
    "ThresholdParameters",
    "YiTpassRecoveryAdapter",
    "enroll",
    "recover",
    "recover_from_store",
]
