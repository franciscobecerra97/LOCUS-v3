"""Strict one-party snapshot collection and offline-predicate audit."""

from __future__ import annotations

import argparse
import base64
import binascii
import builtins
import hashlib
import io
import json
import os
import re
import socket
import sqlite3
import stat
import tempfile
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Never

from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from .attempt_certificates import (
    AuthorizerConfig,
    AuthorizerSigner,
    CertificateError,
)
from .codec import encode
from .deployment import (
    ATTEMPT_BUDGET,
    PARTY_COUNT,
    PARTY_PORT,
    RUNTIME_ROOT,
    TPASS_PARTIES,
    TPASS_THRESHOLD,
)
from .party_store import SCHEMA_VERSION
from .redaction import validate_public_output

PARTY_SNAPSHOT_INPUT_VERSION = "LOCUS-party-snapshot-input-v1"
PARTY_SNAPSHOT_SCENARIO = "t-minus-one-party-snapshot-no-offline-predicate-v1"
PARTY_SNAPSHOT_PROFILE = "same-host-compose-2-of-3-v1"
CAPTURE_CHECKPOINT = "after-one-recovery-party-stopped-v1"
SNAPSHOT_MANIFEST_NAME = "manifest.json"
SNAPSHOT_PARTY_DIRECTORY = "party"
SNAPSHOT_PARTY_ID = 1
MAX_MANIFEST_BYTES = 64 * 1024
MAX_SMALL_FILE_BYTES = 1 * 1024 * 1024
MAX_DATABASE_FILE_BYTES = 64 * 1024 * 1024
SYNTHETIC_CANDIDATES = (
    b"LOCUS-synthetic-party-candidate-alpha-v1",
    b"LOCUS-synthetic-party-candidate-beta-v1",
)

_STATIC_FILES = frozenset(
    {
        "ca.pem",
        "peer-key.pem",
        "peer.pem",
        "server-key.pem",
        "server.pem",
        "service.json",
    }
)
_DATABASE_FILE = "party.sqlite3"
_DATABASE_COMPANIONS = frozenset({"party.sqlite3-shm", "party.sqlite3-wal"})
_REQUIRED_FILES = _STATIC_FILES | {_DATABASE_FILE}
_ALLOWED_FILES = _REQUIRED_FILES | _DATABASE_COMPANIONS
_EXPECTED_TABLES = frozenset(
    {
        "attempts",
        "audit_events",
        "epoch_preparations",
        "epoch_runtime_packages",
        "epoch_transition_locks",
        "epochs",
        "freshness_votes",
        "http_idempotency",
        "metadata",
        "phases",
        "slot_locks",
        "sqlite_sequence",
    }
)


class PartySnapshotError(Exception):
    """The snapshot, collector, or offline boundary is invalid."""


@dataclass(frozen=True)
class PartySnapshot:
    """Validated internal snapshot view; never serialize this structure."""

    service: dict[str, Any]
    manifest: dict[str, Any]
    files: dict[str, bytes]


CandidateProbe = Callable[[Mapping[str, Any], bytes], object | None]


def _exact_dict(value: object, fields: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        raise PartySnapshotError(f"invalid {label}")
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
        raise PartySnapshotError(f"invalid {label}") from exc
    return value


def _lower_hex(value: object, *, length: int, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != length
        or re.fullmatch(r"[0-9a-f]+", value) is None
    ):
        raise PartySnapshotError(f"invalid {label}")
    return value


def _exact_int(value: object, *, minimum: int, maximum: int, label: str) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not minimum <= value <= maximum
    ):
        raise PartySnapshotError(f"invalid {label}")
    return value


def _decode_base64url(value: object, *, label: str) -> bytes:
    if not isinstance(value, str) or not value or "=" in value:
        raise PartySnapshotError(f"invalid {label}")
    padding = "=" * ((4 - len(value) % 4) % 4)
    try:
        decoded = base64.b64decode(value + padding, altchars=b"-_", validate=True)
    except (ValueError, binascii.Error) as exc:
        raise PartySnapshotError(f"invalid {label}") from exc
    if base64.urlsafe_b64encode(decoded).rstrip(b"=").decode("ascii") != value:
        raise PartySnapshotError(f"invalid {label}")
    return decoded


def _file_limit(name: str) -> int:
    if name == _DATABASE_FILE or name in _DATABASE_COMPANIONS:
        return MAX_DATABASE_FILE_BYTES
    return MAX_SMALL_FILE_BYTES


def _read_regular(path: Path, *, limit: int, label: str) -> bytes:
    try:
        metadata = path.lstat()
        if path.is_symlink() or not stat.S_ISREG(metadata.st_mode):
            raise PartySnapshotError(f"invalid {label}")
        with path.open("rb") as handle:
            value = handle.read(limit + 1)
    except PartySnapshotError:
        raise
    except OSError as exc:
        raise PartySnapshotError(f"invalid {label}") from exc
    if not value or len(value) > limit:
        raise PartySnapshotError(f"invalid {label}")
    return value


def _directory_entries(root: Path, *, label: str) -> dict[str, Path]:
    try:
        if root.is_symlink() or not root.is_dir():
            raise PartySnapshotError(f"invalid {label}")
        entries = {entry.name: entry for entry in root.iterdir()}
    except PartySnapshotError:
        raise
    except OSError as exc:
        raise PartySnapshotError(f"invalid {label}") from exc
    return entries


def _validate_source_files(root: Path) -> dict[str, Path]:
    entries = _directory_entries(root, label="party source directory")
    names = set(entries)
    if not _REQUIRED_FILES <= names or not names <= _ALLOWED_FILES:
        raise PartySnapshotError("unexpected party source file set")
    companions = names & _DATABASE_COMPANIONS
    if companions and companions != _DATABASE_COMPANIONS:
        raise PartySnapshotError("incomplete SQLite companion set")
    for path in entries.values():
        try:
            metadata = path.lstat()
        except OSError as exc:
            raise PartySnapshotError("party source is unreadable") from exc
        if path.is_symlink() or not stat.S_ISREG(metadata.st_mode):
            raise PartySnapshotError("party source contains a non-regular entry")
    return entries


def _stable_source_bytes(path: Path, *, limit: int) -> tuple[bytes, int]:
    try:
        before = path.lstat()
        if path.is_symlink() or not stat.S_ISREG(before.st_mode):
            raise PartySnapshotError("invalid party source file")
        first = _read_regular(path, limit=limit, label="party source file")
        second = _read_regular(path, limit=limit, label="party source file")
        after = path.lstat()
    except PartySnapshotError:
        raise
    except OSError as exc:
        raise PartySnapshotError("party source changed during collection") from exc
    identity_before = (
        before.st_dev,
        before.st_ino,
        before.st_size,
        before.st_mtime_ns,
        before.st_mode,
    )
    identity_after = (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
        after.st_mode,
    )
    if identity_before != identity_after or first != second:
        raise PartySnapshotError("party source changed during collection")
    return first, stat.S_IMODE(before.st_mode)


def _write_new(path: Path, value: bytes, *, mode: int = 0o444) -> None:
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
        try:
            with os.fdopen(descriptor, "wb", closefd=False) as output:
                output.write(value)
                output.flush()
                os.fsync(output.fileno())
        finally:
            os.close(descriptor)
    except OSError as exc:
        raise PartySnapshotError("snapshot publication failed") from exc


def _validate_manifest(value: dict[str, Any], files: dict[str, bytes]) -> None:
    manifest = _exact_dict(
        value,
        {
            "capture_checkpoint",
            "files",
            "party_id",
            "profile",
            "tpass_parties",
            "tpass_threshold",
            "version",
        },
        "party snapshot manifest",
    )
    if (
        manifest["version"] != PARTY_SNAPSHOT_INPUT_VERSION
        or manifest["profile"] != PARTY_SNAPSHOT_PROFILE
        or manifest["capture_checkpoint"] != CAPTURE_CHECKPOINT
        or manifest["party_id"] != SNAPSHOT_PARTY_ID
        or manifest["tpass_threshold"] != TPASS_THRESHOLD
        or manifest["tpass_parties"] != TPASS_PARTIES
    ):
        raise PartySnapshotError("invalid party snapshot profile binding")
    encoded_files = manifest["files"]
    if not isinstance(encoded_files, list) or len(encoded_files) != len(files):
        raise PartySnapshotError("invalid party snapshot file manifest")
    paths: list[str] = []
    for encoded in encoded_files:
        entry = _exact_dict(
            encoded,
            {"bytes", "mode", "path", "sha256"},
            "party snapshot file entry",
        )
        path = entry["path"]
        if not isinstance(path, str) or path not in _ALLOWED_FILES:
            raise PartySnapshotError("invalid party snapshot file path")
        paths.append(path)
        content = files.get(path)
        if content is None:
            raise PartySnapshotError("party snapshot manifest names a missing file")
        if (
            _exact_int(
                entry["bytes"], minimum=1, maximum=_file_limit(path), label="file size"
            )
            != len(content)
            or _exact_int(entry["mode"], minimum=0, maximum=0o777, label="file mode")
            != entry["mode"]
            or _lower_hex(entry["sha256"], length=64, label="file digest")
            != hashlib.sha256(content).hexdigest()
        ):
            raise PartySnapshotError("party snapshot file binding mismatch")
    if paths != sorted(files) or len(set(paths)) != len(paths):
        raise PartySnapshotError("noncanonical party snapshot file list")


def _validate_certificate_pair(certificate: bytes, private_key: bytes) -> None:
    try:
        parsed_certificate = x509.load_pem_x509_certificate(certificate)
        parsed_private_key = serialization.load_pem_private_key(
            private_key, password=None
        )
        if not isinstance(parsed_private_key, Ed25519PrivateKey):
            raise ValueError("unexpected private-key type")
        certificate_key = parsed_certificate.public_key().public_bytes(
            serialization.Encoding.Raw,
            serialization.PublicFormat.Raw,
        )
        private_public_key = parsed_private_key.public_key().public_bytes(
            serialization.Encoding.Raw,
            serialization.PublicFormat.Raw,
        )
    except (TypeError, ValueError) as exc:
        raise PartySnapshotError("invalid party identity material") from exc
    if certificate_key != private_public_key:
        raise PartySnapshotError("party certificate and key do not match")


def _validate_service(files: dict[str, bytes]) -> tuple[dict[str, Any], bytes, bytes]:
    service = _exact_dict(
        _canonical_json(files["service.json"], label="party service configuration"),
        {
            "authorizer_config",
            "budget",
            "listen_host",
            "listen_port",
            "native_party",
            "party_id",
            "signer_private_key",
            "store_path",
            "tls",
            "version",
        },
        "party service configuration",
    )
    if (
        service["version"] != "LOCUS-party-service-config-v1"
        or service["party_id"] != SNAPSHOT_PARTY_ID
        or service["budget"] != ATTEMPT_BUDGET
        or service["listen_host"] != "0.0.0.0"
        or service["listen_port"] != PARTY_PORT
        or service["store_path"] != f"{RUNTIME_ROOT}/party.sqlite3"
    ):
        raise PartySnapshotError("party service profile changed")
    try:
        config = AuthorizerConfig.from_dict(service["authorizer_config"])
        signer = AuthorizerSigner.from_private_key_hex(
            SNAPSHOT_PARTY_ID, service["signer_private_key"]
        )
    except (CertificateError, TypeError, ValueError) as exc:
        raise PartySnapshotError("invalid party authorizer material") from exc
    if (
        sorted(config.public_keys) != list(range(1, PARTY_COUNT + 1))
        or config.fault_bound != 2
        or config.quorum != 4
        or signer.public_key_hex != config.public_keys[SNAPSHOT_PARTY_ID]
    ):
        raise PartySnapshotError("party authorizer profile changed")

    tls = _exact_dict(
        service["tls"],
        {"certificate", "client_ca", "client_identities", "private_key"},
        "party TLS configuration",
    )
    if (
        tls["certificate"] != f"{RUNTIME_ROOT}/server.pem"
        or tls["client_ca"] != f"{RUNTIME_ROOT}/ca.pem"
        or tls["private_key"] != f"{RUNTIME_ROOT}/server-key.pem"
        or not isinstance(tls["client_identities"], list)
        or len(tls["client_identities"]) != PARTY_COUNT + 1
    ):
        raise PartySnapshotError("party TLS profile changed")
    roles: list[str] = []
    fingerprints: list[str] = []
    for value in tls["client_identities"]:
        identity = _exact_dict(
            value, {"certificate_sha256", "role"}, "party client identity"
        )
        if not isinstance(identity["role"], str):
            raise PartySnapshotError("invalid party client identity")
        roles.append(identity["role"])
        fingerprints.append(
            _lower_hex(
                identity["certificate_sha256"],
                length=64,
                label="party client certificate fingerprint",
            )
        )
    if roles != ["coordinator", *[f"party:{item}" for item in range(1, 6)]] or len(
        set(fingerprints)
    ) != len(fingerprints):
        raise PartySnapshotError("party client identity set changed")
    try:
        x509.load_pem_x509_certificate(files["ca.pem"])
    except ValueError as exc:
        raise PartySnapshotError("invalid party CA certificate") from exc
    _validate_certificate_pair(files["server.pem"], files["server-key.pem"])
    _validate_certificate_pair(files["peer.pem"], files["peer-key.pem"])

    native_party = _exact_dict(
        service["native_party"],
        {"outbound_tls", "parameters", "peers", "state"},
        "native party configuration",
    )
    outbound_tls = _exact_dict(
        native_party["outbound_tls"],
        {"client_certificate", "client_private_key", "server_ca"},
        "outbound TLS configuration",
    )
    if outbound_tls != {
        "client_certificate": f"{RUNTIME_ROOT}/peer.pem",
        "client_private_key": f"{RUNTIME_ROOT}/peer-key.pem",
        "server_ca": f"{RUNTIME_ROOT}/ca.pem",
    }:
        raise PartySnapshotError("native party TLS profile changed")
    peers = native_party["peers"]
    if not isinstance(peers, list) or len(peers) != PARTY_COUNT - 1:
        raise PartySnapshotError("invalid native party peer set")
    peer_ids: list[int] = []
    for value in peers:
        peer = _exact_dict(
            value,
            {
                "host",
                "party_id",
                "port",
                "server_certificate_sha256",
                "timeout_seconds",
            },
            "native party peer",
        )
        party_id = _exact_int(
            peer["party_id"], minimum=1, maximum=PARTY_COUNT, label="peer identifier"
        )
        if (
            party_id == SNAPSHOT_PARTY_ID
            or peer["host"] != f"party{party_id}"
            or peer["port"] != PARTY_PORT
            or peer["timeout_seconds"] != 2.0
        ):
            raise PartySnapshotError("native party peer profile changed")
        _lower_hex(
            peer["server_certificate_sha256"],
            length=64,
            label="peer certificate fingerprint",
        )
        peer_ids.append(party_id)
    if peer_ids != list(range(2, PARTY_COUNT + 1)):
        raise PartySnapshotError("noncanonical native party peer set")

    parameters_bytes = _decode_base64url(
        native_party["parameters"], label="native public parameters"
    )
    state_bytes = _decode_base64url(native_party["state"], label="native party state")
    try:
        from . import _tpass_native as native

        parameters = native.PublicParameters.from_bytes(parameters_bytes)
        state = native.PartyState.from_secret_bytes(state_bytes)
    except (ImportError, ValueError) as exc:
        raise PartySnapshotError("invalid native party state") from exc
    if (
        parameters.threshold != TPASS_THRESHOLD
        or parameters.parties != TPASS_PARTIES
        or state.party_id != SNAPSHOT_PARTY_ID
    ):
        raise PartySnapshotError("native TPASS profile changed")
    return service, parameters_bytes, state_bytes


def _validate_database(
    files: dict[str, bytes],
    service: dict[str, Any],
    parameters_bytes: bytes,
    state_bytes: bytes,
) -> None:
    with tempfile.TemporaryDirectory(prefix="locus-party-snapshot-") as temporary:
        root = Path(temporary)
        for name in [_DATABASE_FILE, *sorted(set(files) & _DATABASE_COMPANIONS)]:
            destination = root / name
            destination.write_bytes(files[name])
            destination.chmod(0o600)
        try:
            connection = sqlite3.connect(root / _DATABASE_FILE, timeout=1.0)
            connection.execute("PRAGMA query_only = ON")
            if connection.execute("PRAGMA quick_check(1)").fetchall() != [("ok",)]:
                raise PartySnapshotError("party database consistency check failed")
            if connection.execute("PRAGMA foreign_key_check").fetchone() is not None:
                raise PartySnapshotError("party database foreign-key check failed")
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                ).fetchall()
            }
            if tables != _EXPECTED_TABLES:
                raise PartySnapshotError("party database schema changed")
            metadata = connection.execute(
                "SELECT value FROM metadata WHERE key = 'schema_version'"
            ).fetchall()
            if metadata != [(str(SCHEMA_VERSION),)]:
                raise PartySnapshotError("invalid party database schema version")
            config = AuthorizerConfig.from_dict(service["authorizer_config"])
            epochs = connection.execute(
                "SELECT bid, epoch, party_id, config_digest, backup_digest, budget, "
                "consumed, status FROM epochs"
            ).fetchall()
            if epochs != [
                (
                    config.bid,
                    config.epoch,
                    SNAPSHOT_PARTY_ID,
                    config.digest,
                    config.backup_digest,
                    ATTEMPT_BUDGET,
                    1,
                    "ACTIVE",
                )
            ]:
                raise PartySnapshotError("party database checkpoint changed")
            if connection.execute("SELECT COUNT(*) FROM attempts").fetchone() != (1,):
                raise PartySnapshotError("party database attempt checkpoint changed")
            runtime = connection.execute(
                "SELECT party_id, parameters_bytes, party_state_bytes, state "
                "FROM epoch_runtime_packages"
            ).fetchall()
            if runtime != [
                (SNAPSHOT_PARTY_ID, parameters_bytes, state_bytes, "ACTIVE")
            ]:
                raise PartySnapshotError("party runtime package changed")
        except PartySnapshotError:
            raise
        except (CertificateError, sqlite3.DatabaseError, OSError) as exc:
            raise PartySnapshotError("invalid party database snapshot") from exc
        finally:
            try:
                connection.close()
            except UnboundLocalError:
                pass


def validate_party_snapshot(root: Path) -> PartySnapshot:
    """Validate the exact party snapshot before candidate testing."""

    entries = _directory_entries(root, label="party snapshot directory")
    if set(entries) != {SNAPSHOT_MANIFEST_NAME, SNAPSHOT_PARTY_DIRECTORY}:
        raise PartySnapshotError("party snapshot has an unexpected top-level entry")
    manifest_path = entries[SNAPSHOT_MANIFEST_NAME]
    party_root = entries[SNAPSHOT_PARTY_DIRECTORY]
    manifest_bytes = _read_regular(
        manifest_path, limit=MAX_MANIFEST_BYTES, label="party snapshot manifest"
    )
    party_entries = _validate_source_files(party_root)
    files = {
        name: _read_regular(path, limit=_file_limit(name), label="party snapshot file")
        for name, path in party_entries.items()
    }
    manifest = _canonical_json(manifest_bytes, label="party snapshot manifest")
    _validate_manifest(manifest, files)
    service, parameters_bytes, state_bytes = _validate_service(files)
    _validate_database(files, service, parameters_bytes, state_bytes)
    return PartySnapshot(service=service, manifest=manifest, files=files)


@dataclass
class _BoundaryCounters:
    excluded_path_accesses: int = 0
    network_attempts: int = 0


class _BoundaryViolation(Exception):
    pass


class _OfflineCandidateGuard:
    """Count candidate attempts that exceed the in-memory offline boundary."""

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
    service: Mapping[str, Any], candidate: bytes
) -> object | None:
    """Exercise candidate-dependent work without constructing a verifier."""

    config = service["authorizer_config"]
    if not isinstance(config, Mapping):
        raise PartySnapshotError("invalid in-memory authorizer configuration")
    digest = hashlib.sha256()
    digest.update(b"LOCUS/party-snapshot-candidate-audit/v1\x00")
    digest.update(bytes.fromhex(str(config["bid"])))
    digest.update(int(config["epoch"]).to_bytes(8, "big"))
    digest.update(candidate)
    digest.digest()
    return None


def audit_party_snapshot(
    root: Path, *, candidate_probe: CandidateProbe | None = None
) -> dict[str, object]:
    """Return one privacy-safe aggregate over the strict offline candidate path."""

    snapshot = validate_party_snapshot(root)
    counters = _BoundaryCounters()
    signals = 0
    probe = candidate_probe or _candidate_preprocessing
    for candidate in SYNTHETIC_CANDIDATES:
        try:
            with _OfflineCandidateGuard(counters):
                signal = probe(snapshot.service, candidate)
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
        "cloud_material": "absent",
        "compromised_parties": 1,
        "excluded_path_accesses": counters.excluded_path_accesses,
        "network_attempts": counters.network_attempts,
        "secret_output_exposures": 0,
        "snapshot_validation": "passed",
        "threshold": TPASS_THRESHOLD,
    }
    validate_public_output(observation)
    return observation


def capture_party_snapshot(
    *, party_root: Path, snapshot_root: Path
) -> dict[str, object]:
    """Copy one stopped synthetic party volume into an exact offline artifact."""

    source_entries = _validate_source_files(party_root)
    try:
        snapshot_root.mkdir(parents=True, exist_ok=True)
        if snapshot_root.is_symlink() or any(snapshot_root.iterdir()):
            raise PartySnapshotError("snapshot output must be an empty directory")
        output_party = snapshot_root / SNAPSHOT_PARTY_DIRECTORY
        output_party.mkdir(mode=0o755)
    except PartySnapshotError:
        raise
    except OSError as exc:
        raise PartySnapshotError("snapshot output is unavailable") from exc
    manifest_files: list[dict[str, object]] = []
    for name in sorted(source_entries):
        value, mode = _stable_source_bytes(
            source_entries[name], limit=_file_limit(name)
        )
        _write_new(output_party / name, value)
        manifest_files.append(
            {
                "bytes": len(value),
                "mode": mode,
                "path": name,
                "sha256": hashlib.sha256(value).hexdigest(),
            }
        )
    manifest = {
        "capture_checkpoint": CAPTURE_CHECKPOINT,
        "files": manifest_files,
        "party_id": SNAPSHOT_PARTY_ID,
        "profile": PARTY_SNAPSHOT_PROFILE,
        "tpass_parties": TPASS_PARTIES,
        "tpass_threshold": TPASS_THRESHOLD,
        "version": PARTY_SNAPSHOT_INPUT_VERSION,
    }
    _write_new(snapshot_root / SNAPSHOT_MANIFEST_NAME, encode(manifest))
    try:
        output_party.chmod(0o555)
    except OSError as exc:
        raise PartySnapshotError("snapshot publication failed") from exc
    validate_party_snapshot(snapshot_root)
    result: dict[str, object] = {
        "artifact": PARTY_SNAPSHOT_INPUT_VERSION,
        "status": "captured",
    }
    validate_public_output(result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Collect one strict LOCUS recovery-party snapshot"
    )
    parser.add_argument("--party-root", type=Path, required=True)
    parser.add_argument("--snapshot-root", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = capture_party_snapshot(
            party_root=args.party_root, snapshot_root=args.snapshot_root
        )
    except PartySnapshotError:
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
