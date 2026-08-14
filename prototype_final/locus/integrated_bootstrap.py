"""Networkless credential and empty-role bootstrap for P7.5."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import stat
from pathlib import Path

from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.x509.oid import NameOID

from .codec import encode
from .integrated_manifest import (
    EXPECTED_SERVICES,
    IntegratedManifestError,
    load_integrated_manifest,
)
from .managed_manifest import EXPECTED_BOOTSTRAP_ROLES, load_managed_manifest

SIGNING_ROLES = (
    "admission",
    "operator",
    "party1",
    "party2",
    "party3",
    "party4",
    "party5",
)
LEGACY_CLIENT_ROLES = ("ui-client-a", "ui-client-b")


def _manifest_contract(
    manifest_path: str | Path,
) -> tuple[
    dict[str, object],
    tuple[str, ...],
    frozenset[str],
    frozenset[str],
    frozenset[str],
]:
    """Load either immutable deployment family and return bootstrap semantics."""

    try:
        manifest = load_integrated_manifest(manifest_path)
    except IntegratedManifestError:
        manifest = load_managed_manifest(manifest_path)
        return (
            manifest,
            EXPECTED_BOOTSTRAP_ROLES,
            frozenset(),
            frozenset({"managed-client"}),
            frozenset({"manager-controller"}),
        )
    return (
        manifest,
        EXPECTED_SERVICES,
        frozenset(LEGACY_CLIENT_ROLES),
        frozenset(),
        frozenset(),
    )


class IntegratedBootstrapError(ValueError):
    """The networkless bootstrap contract was violated."""


def _write_new(path: Path, value: bytes, *, private: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0),
        0o600 if private else 0o644,
    )
    try:
        os.write(descriptor, value)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    if private:
        path.chmod(stat.S_IRUSR | stat.S_IWUSR)


def _raw_private(key: Ed25519PrivateKey) -> bytes:
    return key.private_bytes(
        serialization.Encoding.Raw,
        serialization.PrivateFormat.Raw,
        serialization.NoEncryption(),
    )


def _raw_public(key: Ed25519PrivateKey) -> bytes:
    return key.public_key().public_bytes(
        serialization.Encoding.Raw,
        serialization.PublicFormat.Raw,
    )


def _validate_ca_certificate(
    certificate: x509.Certificate, *, now: dt.datetime
) -> None:
    try:
        public = certificate.public_key()
        constraints = certificate.extensions.get_extension_for_class(
            x509.BasicConstraints
        ).value
        if (
            not isinstance(public, Ed25519PublicKey)
            or certificate.subject != certificate.issuer
            or not constraints.ca
            or constraints.path_length != 0
            or not certificate.not_valid_before_utc
            <= now
            <= certificate.not_valid_after_utc
        ):
            raise ValueError
        public.verify(certificate.signature, certificate.tbs_certificate_bytes)
    except (x509.ExtensionNotFound, InvalidSignature, TypeError, ValueError) as exc:
        raise IntegratedBootstrapError("invalid or expired bootstrap CA") from exc


def _validate_role_certificate(
    certificate: x509.Certificate,
    *,
    ca_certificate: x509.Certificate,
    role: str,
    now: dt.datetime,
) -> None:
    try:
        ca_public = ca_certificate.public_key()
        constraints = certificate.extensions.get_extension_for_class(
            x509.BasicConstraints
        ).value
        alternative_names = certificate.extensions.get_extension_for_class(
            x509.SubjectAlternativeName
        ).value
        common_names = certificate.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
        if (
            not isinstance(ca_public, Ed25519PublicKey)
            or certificate.issuer != ca_certificate.subject
            or constraints.ca
            or constraints.path_length is not None
            or [item.value for item in common_names] != [role]
            or alternative_names.get_values_for_type(x509.DNSName) != [role]
            or alternative_names.get_values_for_type(x509.UniformResourceIdentifier)
            != [f"spiffe://locus.invalid/integrated/{role}"]
            or not certificate.not_valid_before_utc
            <= now
            <= certificate.not_valid_after_utc
            or certificate.not_valid_after_utc > ca_certificate.not_valid_after_utc
        ):
            raise ValueError
        ca_public.verify(certificate.signature, certificate.tbs_certificate_bytes)
    except (x509.ExtensionNotFound, InvalidSignature, TypeError, ValueError) as exc:
        raise IntegratedBootstrapError(
            f"invalid or expired transport identity: {role}"
        ) from exc


def _validate_existing(
    target: Path,
    manifest: dict[str, object],
    *,
    roles: tuple[str, ...],
    proof_roles: frozenset[str],
    template_roles: frozenset[str],
    lifecycle_roles: frozenset[str],
) -> None:
    """Validate bootstrap-owned state without reading later runtime state."""

    if {item.name for item in target.iterdir()} != set(roles):
        raise IntegratedBootstrapError("integrated role inventory changed")
    manifest_bytes = encode(manifest) + b"\n"
    ca_bytes: bytes | None = None
    ca_certificate: x509.Certificate | None = None
    now = dt.datetime.now(dt.UTC)
    for role in roles:
        role_root = target / role
        if role_root.is_symlink() or not role_root.is_dir():
            raise IntegratedBootstrapError("invalid integrated role root")
        expected_files = [role_root / "ca.pem", role_root / "manifest.json"]
        if role != "bootstrap":
            expected_files.extend(
                [role_root / "tls-cert.pem", role_root / "tls-key.pem"]
            )
        if role in SIGNING_ROLES:
            expected_files.append(role_root / "signing-key.bin")
        if role in proof_roles:
            expected_files.append(role_root / "proof-key.bin")
        if role in lifecycle_roles:
            expected_files.append(role_root / "lifecycle-secret.bin")
        if role in {
            *proof_roles,
            *template_roles,
            "admission",
            "operator",
            "storage-gateway",
            *[f"party{i}" for i in range(1, 6)],
        }:
            expected_files.append(role_root / "trust.json")
        if any(path.is_symlink() or not path.is_file() for path in expected_files):
            raise IntegratedBootstrapError("bootstrap-owned role state is incomplete")
        if role in template_roles and {path.name for path in role_root.iterdir()} != {
            path.name for path in expected_files
        }:
            raise IntegratedBootstrapError("managed-client template state changed")
        observed_ca = (role_root / "ca.pem").read_bytes()
        if ca_bytes is None:
            ca_bytes = observed_ca
            ca_certificate = x509.load_pem_x509_certificate(ca_bytes)
            _validate_ca_certificate(ca_certificate, now=now)
        elif observed_ca != ca_bytes:
            raise IntegratedBootstrapError("role trust roots differ")
        if (role_root / "manifest.json").read_bytes() != manifest_bytes:
            raise IntegratedBootstrapError("integrated manifest changed")
        if (
            role in SIGNING_ROLES
            and (role_root / "signing-key.bin").stat().st_size != 32
        ):
            raise IntegratedBootstrapError("invalid signing key")
        if role in proof_roles and (role_root / "proof-key.bin").stat().st_size != 32:
            raise IntegratedBootstrapError("invalid client proof key")
        if (
            role in lifecycle_roles
            and (role_root / "lifecycle-secret.bin").stat().st_size != 32
        ):
            raise IntegratedBootstrapError("invalid lifecycle-controller secret")
        if role != "bootstrap":
            assert ca_certificate is not None
            certificate = x509.load_pem_x509_certificate(
                (role_root / "tls-cert.pem").read_bytes()
            )
            _validate_role_certificate(
                certificate,
                ca_certificate=ca_certificate,
                role=role,
                now=now,
            )
            private = serialization.load_pem_private_key(
                (role_root / "tls-key.pem").read_bytes(), password=None
            )
            if not isinstance(private, Ed25519PrivateKey) or (
                certificate.public_key().public_bytes(
                    serialization.Encoding.Raw, serialization.PublicFormat.Raw
                )
                != _raw_public(private)
            ):
                raise IntegratedBootstrapError("transport identity mismatch")


def bootstrap_integrated_roles(
    *,
    root: str | Path,
    manifest_path: str | Path,
    owner_uid: int | None = None,
    owner_gid: int | None = None,
    allow_existing: bool = False,
) -> None:
    """Create fresh credentials and otherwise empty role roots exactly once."""

    target = Path(root)
    (
        manifest,
        roles,
        proof_roles,
        template_roles,
        lifecycle_roles,
    ) = _manifest_contract(manifest_path)
    managed_profile = "manager-controller" in roles
    if target.is_symlink():
        raise IntegratedBootstrapError("integrated role root is a symbolic link")
    if target.exists():
        entries = {item.name: item for item in target.iterdir()}
        if (
            allow_existing
            and set(entries) == set(roles)
            and all((item / "manifest.json").is_file() for item in entries.values())
        ):
            _validate_existing(
                target,
                manifest,
                roles=roles,
                proof_roles=proof_roles,
                template_roles=template_roles,
                lifecycle_roles=lifecycle_roles,
            )
            return
        if set(entries) - set(roles) or any(
            item.is_file() or any(item.iterdir()) for item in entries.values()
        ):
            raise IntegratedBootstrapError("integrated role root is not empty")
    target.mkdir(parents=True, exist_ok=True)

    now = dt.datetime.now(dt.UTC)
    ca_key = Ed25519PrivateKey.generate()
    ca_name = x509.Name(
        [x509.NameAttribute(NameOID.COMMON_NAME, "LOCUS integrated test CA")]
    )
    ca_cert = (
        x509.CertificateBuilder()
        .subject_name(ca_name)
        .issuer_name(ca_name)
        .public_key(ca_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - dt.timedelta(minutes=1))
        .not_valid_after(now + dt.timedelta(days=366 if managed_profile else 7))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .sign(ca_key, algorithm=None)
    )
    ca_bytes = ca_cert.public_bytes(serialization.Encoding.PEM)

    public_keys: dict[str, str] = {}
    signing_keys: dict[str, Ed25519PrivateKey] = {}
    for role in SIGNING_ROLES:
        key = Ed25519PrivateKey.generate()
        signing_keys[role] = key
        public_keys[role] = _raw_public(key).hex()

    for role in roles:
        role_root = target / role
        role_root.mkdir(parents=True, exist_ok=True)
        _write_new(role_root / "ca.pem", ca_bytes)
        _write_new(role_root / "manifest.json", encode(manifest) + b"\n")
        if role != "bootstrap":
            transport_key = Ed25519PrivateKey.generate()
            subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, role)])
            certificate = (
                x509.CertificateBuilder()
                .subject_name(subject)
                .issuer_name(ca_name)
                .public_key(transport_key.public_key())
                .serial_number(x509.random_serial_number())
                .not_valid_before(now - dt.timedelta(minutes=1))
                .not_valid_after(now + dt.timedelta(days=365 if managed_profile else 2))
                .add_extension(
                    x509.SubjectAlternativeName(
                        [
                            x509.DNSName(role),
                            x509.UniformResourceIdentifier(
                                f"spiffe://locus.invalid/integrated/{role}"
                            ),
                        ]
                    ),
                    critical=False,
                )
                .add_extension(
                    x509.BasicConstraints(ca=False, path_length=None), critical=True
                )
                .sign(ca_key, algorithm=None)
            )
            _write_new(
                role_root / "tls-key.pem",
                transport_key.private_bytes(
                    serialization.Encoding.PEM,
                    serialization.PrivateFormat.PKCS8,
                    serialization.NoEncryption(),
                ),
                private=True,
            )
            _write_new(
                role_root / "tls-cert.pem",
                certificate.public_bytes(serialization.Encoding.PEM),
            )
        if role in signing_keys:
            _write_new(
                role_root / "signing-key.bin",
                _raw_private(signing_keys[role]),
                private=True,
            )
        if role in proof_roles:
            proof_key = Ed25519PrivateKey.generate()
            _write_new(
                role_root / "proof-key.bin", _raw_private(proof_key), private=True
            )
        if role in lifecycle_roles:
            _write_new(role_root / "lifecycle-secret.bin", os.urandom(32), private=True)

    trust = encode(
        {
            "admission_issuer_public_key": public_keys["admission"],
            "operator_public_key": public_keys["operator"],
            "party_public_keys": {
                str(index): public_keys[f"party{index}"] for index in range(1, 6)
            },
            "synthetic_subject": "11" * 32,
            "version": "integrated-trust/1",
        }
    )
    for role in (
        *proof_roles,
        *template_roles,
        "admission",
        "operator",
        "storage-gateway",
        *[f"party{i}" for i in range(1, 6)],
    ):
        _write_new(target / role / "trust.json", trust)

    if owner_uid is not None and owner_gid is not None:
        chown = getattr(os, "chown", None)
        if chown is None:
            raise IntegratedBootstrapError("ownership assignment is unavailable")
        for path in target.rglob("*"):
            relative = path.relative_to(target)
            controller_owned = (
                managed_profile
                and bool(relative.parts)
                and relative.parts[0] == "manager-controller"
            )
            chown(
                path,
                0 if controller_owned else owner_uid,
                0 if controller_owned else owner_gid,
            )

    # The CA private key deliberately dies here. Bootstrap never creates suite,
    # cue-derived, backup, or protected-key state.


def main() -> None:
    parser = argparse.ArgumentParser(description="Create P7.5 synthetic role roots")
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--owner-uid", type=int)
    parser.add_argument("--owner-gid", type=int)
    parser.add_argument("--allow-existing", action="store_true")
    args = parser.parse_args()
    bootstrap_integrated_roles(
        root=args.root,
        manifest_path=args.manifest,
        owner_uid=args.owner_uid,
        owner_gid=args.owner_gid,
        allow_existing=args.allow_existing,
    )
    role_count = len(_manifest_contract(args.manifest)[1])
    print(json.dumps({"status": "ready", "roles": role_count}, sort_keys=True))


if __name__ == "__main__":
    main()
