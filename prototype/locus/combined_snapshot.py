"""Strict combined cloud-plus-one-party snapshot and offline audit."""

from __future__ import annotations

import argparse
import builtins
import hashlib
import io
import json
import os
import re
import socket
import stat
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Never

from .attempt_certificates import AuthorizerConfig, CertificateError
from .cloud_snapshot import (
    CLOUD_SNAPSHOT_INPUT_VERSION,
    CloudSnapshot,
    CloudSnapshotError,
    validate_cloud_snapshot,
)
from .codec import encode
from .party_snapshot import (
    PARTY_SNAPSHOT_INPUT_VERSION,
    PartySnapshot,
    PartySnapshotError,
    validate_party_snapshot,
)
from .redaction import validate_public_output

COMBINED_SNAPSHOT_INPUT_VERSION = "LOCUS-combined-snapshot-input-v1"
COMBINED_SNAPSHOT_SCENARIO = (
    "cloud-plus-t-minus-one-party-snapshot-no-offline-predicate-v1"
)
COMBINED_SNAPSHOT_PROFILE = "same-host-compose-cloud-plus-one-party-2-of-3-v1"
CAPTURE_CHECKPOINT = "after-one-recovery-party-stopped-v1"
SNAPSHOT_MANIFEST_NAME = "manifest.json"
CLOUD_DIRECTORY = "cloud"
PARTY_DIRECTORY = "party"
MAX_MANIFEST_BYTES = 64 * 1024
SYNTHETIC_CANDIDATES = (
    b"LOCUS-synthetic-combined-candidate-alpha-v1",
    b"LOCUS-synthetic-combined-candidate-beta-v1",
)


class CombinedSnapshotError(Exception):
    """The combined snapshot, finalizer, or offline boundary is invalid."""


@dataclass(frozen=True)
class CombinedSnapshot:
    """Validated internal combined view; never serialize this structure."""

    cloud: CloudSnapshot
    party: PartySnapshot
    manifest: dict[str, Any]


CandidateProbe = Callable[[CombinedSnapshot, bytes], object | None]


def _exact_dict(value: object, fields: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        raise CombinedSnapshotError(f"invalid {label}")
    return value


def _canonical_json(encoded: bytes, *, label: str) -> dict[str, Any]:
    try:
        value = json.loads(encoded.decode("ascii"))
        if not isinstance(value, dict) or encode(value) != encoded:
            raise ValueError("noncanonical JSON")
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
        ValueError,
        RecursionError,
    ) as exc:
        raise CombinedSnapshotError(f"invalid {label}") from exc
    return value


def _lower_hex(value: object, *, length: int, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != length
        or re.fullmatch(r"[0-9a-f]+", value) is None
    ):
        raise CombinedSnapshotError(f"invalid {label}")
    return value


def _regular_file_bytes(path: Path, *, limit: int, label: str) -> bytes:
    try:
        metadata = path.lstat()
        if path.is_symlink() or not stat.S_ISREG(metadata.st_mode):
            raise CombinedSnapshotError(f"invalid {label}")
        with path.open("rb") as handle:
            value = handle.read(limit + 1)
    except CombinedSnapshotError:
        raise
    except OSError as exc:
        raise CombinedSnapshotError(f"invalid {label}") from exc
    if not value or len(value) > limit:
        raise CombinedSnapshotError(f"invalid {label}")
    return value


def _directory_entries(root: Path, *, label: str) -> dict[str, Path]:
    try:
        if root.is_symlink() or not root.is_dir():
            raise CombinedSnapshotError(f"invalid {label}")
        entries = {entry.name: entry for entry in root.iterdir()}
    except CombinedSnapshotError:
        raise
    except OSError as exc:
        raise CombinedSnapshotError(f"invalid {label}") from exc
    return entries


def _validate_subdirectory(path: Path, *, label: str) -> None:
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise CombinedSnapshotError(f"invalid {label}") from exc
    if path.is_symlink() or not stat.S_ISDIR(metadata.st_mode):
        raise CombinedSnapshotError(f"invalid {label}")


def _submanifest_bytes(root: Path, *, label: str) -> bytes:
    return _regular_file_bytes(
        root / SNAPSHOT_MANIFEST_NAME,
        limit=MAX_MANIFEST_BYTES,
        label=f"{label} manifest",
    )


def _validate_manifest(
    manifest: dict[str, Any], *, cloud_manifest: bytes, party_manifest: bytes
) -> None:
    parsed = _exact_dict(
        manifest,
        {
            "capture_checkpoint",
            "cloud_manifest_sha256",
            "cloud_snapshot_version",
            "compromised_parties",
            "party_manifest_sha256",
            "party_snapshot_version",
            "profile",
            "threshold",
            "version",
        },
        "combined snapshot manifest",
    )
    if (
        parsed["version"] != COMBINED_SNAPSHOT_INPUT_VERSION
        or parsed["profile"] != COMBINED_SNAPSHOT_PROFILE
        or parsed["capture_checkpoint"] != CAPTURE_CHECKPOINT
        or parsed["cloud_snapshot_version"] != CLOUD_SNAPSHOT_INPUT_VERSION
        or parsed["party_snapshot_version"] != PARTY_SNAPSHOT_INPUT_VERSION
        or parsed["compromised_parties"] != 1
        or parsed["threshold"] != 2
        or _lower_hex(
            parsed["cloud_manifest_sha256"],
            length=64,
            label="cloud sub-manifest digest",
        )
        != hashlib.sha256(cloud_manifest).hexdigest()
        or _lower_hex(
            parsed["party_manifest_sha256"],
            length=64,
            label="party sub-manifest digest",
        )
        != hashlib.sha256(party_manifest).hexdigest()
    ):
        raise CombinedSnapshotError("combined snapshot manifest mismatch")


def _validate_cross_binding(cloud: CloudSnapshot, party: PartySnapshot) -> None:
    try:
        config = AuthorizerConfig.from_dict(party.service["authorizer_config"])
    except (CertificateError, KeyError, TypeError, ValueError) as exc:
        raise CombinedSnapshotError("invalid combined authorizer binding") from exc
    backup = cloud.backup
    cloud_parameters = backup.get("tpass_public_params")
    party_native = party.service.get("native_party")
    if not isinstance(cloud_parameters, dict) or not isinstance(party_native, dict):
        raise CombinedSnapshotError("invalid combined TPASS binding")
    if (
        config.bid != backup.get("bid")
        or config.epoch != backup.get("epoch")
        or config.backup_digest != backup.get("digest")
        or cloud_parameters.get("threshold") != 2
        or cloud_parameters.get("parties") != 3
        or cloud_parameters.get("parameters") != party_native.get("parameters")
    ):
        raise CombinedSnapshotError("cloud and party snapshots do not match")


def validate_combined_snapshot(root: Path) -> CombinedSnapshot:
    """Validate the exact combined snapshot before candidate testing."""

    entries = _directory_entries(root, label="combined snapshot directory")
    if set(entries) != {SNAPSHOT_MANIFEST_NAME, CLOUD_DIRECTORY, PARTY_DIRECTORY}:
        raise CombinedSnapshotError("combined snapshot has unexpected entries")
    cloud_root = entries[CLOUD_DIRECTORY]
    party_root = entries[PARTY_DIRECTORY]
    _validate_subdirectory(cloud_root, label="cloud sub-snapshot")
    _validate_subdirectory(party_root, label="party sub-snapshot")
    manifest_bytes = _regular_file_bytes(
        entries[SNAPSHOT_MANIFEST_NAME],
        limit=MAX_MANIFEST_BYTES,
        label="combined snapshot manifest",
    )
    cloud_manifest = _submanifest_bytes(cloud_root, label="cloud sub-snapshot")
    party_manifest = _submanifest_bytes(party_root, label="party sub-snapshot")
    manifest = _canonical_json(manifest_bytes, label="combined snapshot manifest")
    _validate_manifest(
        manifest,
        cloud_manifest=cloud_manifest,
        party_manifest=party_manifest,
    )
    try:
        cloud = validate_cloud_snapshot(cloud_root)
        party = validate_party_snapshot(party_root)
    except (CloudSnapshotError, PartySnapshotError) as exc:
        raise CombinedSnapshotError("invalid combined sub-snapshot") from exc
    _validate_cross_binding(cloud, party)
    return CombinedSnapshot(cloud=cloud, party=party, manifest=manifest)


def _write_new(path: Path, value: bytes) -> None:
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444)
        try:
            with os.fdopen(descriptor, "wb", closefd=False) as output:
                output.write(value)
                output.flush()
                os.fsync(output.fileno())
        finally:
            os.close(descriptor)
    except OSError as exc:
        raise CombinedSnapshotError("combined snapshot publication failed") from exc


def finalize_combined_snapshot(root: Path) -> dict[str, object]:
    """Validate both pre-generated sub-snapshots and bind their manifests."""

    entries = _directory_entries(root, label="combined snapshot directory")
    if set(entries) != {CLOUD_DIRECTORY, PARTY_DIRECTORY}:
        raise CombinedSnapshotError("combined snapshot is not ready for finalization")
    cloud_root = entries[CLOUD_DIRECTORY]
    party_root = entries[PARTY_DIRECTORY]
    _validate_subdirectory(cloud_root, label="cloud sub-snapshot")
    _validate_subdirectory(party_root, label="party sub-snapshot")
    try:
        cloud = validate_cloud_snapshot(cloud_root)
        party = validate_party_snapshot(party_root)
    except (CloudSnapshotError, PartySnapshotError) as exc:
        raise CombinedSnapshotError("invalid combined sub-snapshot") from exc
    _validate_cross_binding(cloud, party)
    cloud_manifest = _submanifest_bytes(cloud_root, label="cloud sub-snapshot")
    party_manifest = _submanifest_bytes(party_root, label="party sub-snapshot")
    manifest = {
        "capture_checkpoint": CAPTURE_CHECKPOINT,
        "cloud_manifest_sha256": hashlib.sha256(cloud_manifest).hexdigest(),
        "cloud_snapshot_version": CLOUD_SNAPSHOT_INPUT_VERSION,
        "compromised_parties": 1,
        "party_manifest_sha256": hashlib.sha256(party_manifest).hexdigest(),
        "party_snapshot_version": PARTY_SNAPSHOT_INPUT_VERSION,
        "profile": COMBINED_SNAPSHOT_PROFILE,
        "threshold": 2,
        "version": COMBINED_SNAPSHOT_INPUT_VERSION,
    }
    _write_new(root / SNAPSHOT_MANIFEST_NAME, encode(manifest))
    validate_combined_snapshot(root)
    result: dict[str, object] = {
        "artifact": COMBINED_SNAPSHOT_INPUT_VERSION,
        "status": "finalized",
    }
    validate_public_output(result)
    return result


@dataclass
class _BoundaryCounters:
    excluded_path_accesses: int = 0
    network_attempts: int = 0


class _BoundaryViolation(Exception):
    pass


class _OfflineCandidateGuard:
    """Count candidate attempts beyond the loaded combined snapshot."""

    def __init__(self, counters: _BoundaryCounters) -> None:
        self._counters = counters
        self._originals: list[tuple[object, str, object]] = []

    def _replace(self, owner: object, name: str, replacement: object) -> None:
        self._originals.append((owner, name, getattr(owner, name)))
        setattr(owner, name, replacement)

    def __enter__(self) -> _OfflineCandidateGuard:
        def block_path(*_args: object, **_kwargs: object) -> Never:
            self._counters.excluded_path_accesses += 1
            raise _BoundaryViolation("candidate attempted filesystem access")

        def block_network(*_args: object, **_kwargs: object) -> Never:
            self._counters.network_attempts += 1
            raise _BoundaryViolation("candidate attempted network access")

        self._replace(builtins, "open", block_path)
        self._replace(io, "open", block_path)
        self._replace(os, "open", block_path)
        self._replace(socket, "socket", block_network)
        self._replace(socket, "create_connection", block_network)
        self._replace(socket, "getaddrinfo", block_network)
        return self

    def __exit__(
        self,
        _exception_type: object,
        _exception: object,
        _traceback: object,
    ) -> None:
        for owner, name, original in reversed(self._originals):
            setattr(owner, name, original)
        self._originals.clear()


def _candidate_preprocessing(
    snapshot: CombinedSnapshot, candidate: bytes
) -> object | None:
    """Exercise both snapshot surfaces without constructing a verifier."""

    native_party = snapshot.party.service["native_party"]
    if not isinstance(native_party, dict) or not isinstance(
        native_party.get("state"), str
    ):
        raise CombinedSnapshotError("invalid in-memory party state")
    digest = hashlib.sha256()
    digest.update(b"LOCUS/combined-snapshot-candidate-audit/v1\x00")
    digest.update(snapshot.cloud.object_bytes)
    digest.update(native_party["state"].encode("ascii"))
    digest.update(candidate)
    digest.digest()
    return None


def audit_combined_snapshot(
    root: Path, *, candidate_probe: CandidateProbe | None = None
) -> dict[str, object]:
    """Return a privacy-safe aggregate over the combined offline path."""

    snapshot = validate_combined_snapshot(root)
    counters = _BoundaryCounters()
    signals = 0
    probe = candidate_probe or _candidate_preprocessing
    for candidate in SYNTHETIC_CANDIDATES:
        try:
            with _OfflineCandidateGuard(counters):
                signal = probe(snapshot, candidate)
        except _BoundaryViolation:
            continue
        except Exception:
            signals += 1
            continue
        if signal is not None:
            signals += 1
    observation: dict[str, object] = {
        "candidate_count": len(SYNTHETIC_CANDIDATES),
        "candidate_signals": signals,
        "cloud_snapshot_validation": "passed",
        "combined_binding": "matched",
        "compromised_parties": 1,
        "excluded_path_accesses": counters.excluded_path_accesses,
        "network_attempts": counters.network_attempts,
        "party_snapshot_validation": "passed",
        "party_snapshots": 1,
        "secret_output_exposures": 0,
        "threshold": 2,
    }
    validate_public_output(observation)
    return observation


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Finalize a strict LOCUS combined snapshot"
    )
    parser.add_argument("--snapshot-root", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = finalize_combined_snapshot(args.snapshot_root)
    except CombinedSnapshotError:
        return 1
    print(
        json.dumps(
            result,
            allow_nan=False,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
