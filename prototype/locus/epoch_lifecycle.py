"""Canonical signed objects for backup-epoch re-enrollment transitions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .attempt_certificates import AuthorizerConfig, AuthorizerSigner
from .codec import encode
from .crypto import hash_bytes


class LifecycleCertificateError(Exception):
    """A backup-epoch lifecycle object is malformed or invalid."""


def _integer(value: object, label: str, *, minimum: int = 0) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < minimum
        or value > 2**63 - 1
    ):
        raise LifecycleCertificateError(f"invalid {label}")
    return value


def _hex(value: object, label: str, *, bytes_length: int) -> str:
    if (
        not isinstance(value, str)
        or len(value) != bytes_length * 2
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise LifecycleCertificateError(f"invalid {label}")
    return value


def _exact_dict(value: object, fields: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        raise LifecycleCertificateError(f"invalid {label}")
    return value


def _verify_signature(public_key: str, signature: str, message: bytes) -> None:
    try:
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_key)).verify(
            bytes.fromhex(signature), message
        )
    except (InvalidSignature, ValueError) as exc:
        raise LifecycleCertificateError("invalid lifecycle signature") from exc


@dataclass(frozen=True)
class EpochTransition:
    """One explicit transition from an active epoch to its direct successor."""

    bid: str
    predecessor_epoch: int
    predecessor_config_digest: str
    predecessor_backup_digest: str
    predecessor_head: str
    predecessor_consumed: int
    predecessor_budget: int
    successor_epoch: int
    successor_config_digest: str
    successor_backup_digest: str
    successor_budget: int
    policy_version: str
    transition_nonce: str

    def validate(self) -> None:
        _hex(self.bid, "backup identifier", bytes_length=16)
        predecessor = _integer(self.predecessor_epoch, "predecessor epoch", minimum=1)
        successor = _integer(self.successor_epoch, "successor epoch", minimum=1)
        if successor != predecessor + 1:
            raise LifecycleCertificateError("successor epoch is not consecutive")
        _hex(
            self.predecessor_config_digest,
            "predecessor configuration digest",
            bytes_length=32,
        )
        _hex(
            self.predecessor_backup_digest,
            "predecessor backup digest",
            bytes_length=32,
        )
        _hex(self.predecessor_head, "predecessor head", bytes_length=32)
        consumed = _integer(self.predecessor_consumed, "predecessor consumed count")
        budget = _integer(self.predecessor_budget, "predecessor budget", minimum=1)
        if consumed > budget:
            raise LifecycleCertificateError("predecessor count exceeds budget")
        _hex(
            self.successor_config_digest,
            "successor configuration digest",
            bytes_length=32,
        )
        _hex(
            self.successor_backup_digest,
            "successor backup digest",
            bytes_length=32,
        )
        _integer(self.successor_budget, "successor budget", minimum=1)
        if self.policy_version != "LOCUS-epoch-lifecycle-policy-v1":
            raise LifecycleCertificateError("unsupported lifecycle policy")
        _hex(self.transition_nonce, "transition nonce", bytes_length=32)

    def verify_configs(
        self, predecessor: AuthorizerConfig, successor: AuthorizerConfig
    ) -> None:
        self.validate()
        predecessor.validate()
        successor.validate()
        if (
            predecessor.bid != self.bid
            or predecessor.epoch != self.predecessor_epoch
            or predecessor.digest != self.predecessor_config_digest
            or predecessor.backup_digest != self.predecessor_backup_digest
            or successor.bid != self.bid
            or successor.epoch != self.successor_epoch
            or successor.digest != self.successor_config_digest
            or successor.backup_digest != self.successor_backup_digest
        ):
            raise LifecycleCertificateError("lifecycle configuration mismatch")
        if (
            predecessor.public_keys != successor.public_keys
            or predecessor.quorum != successor.quorum
            or predecessor.fault_bound != successor.fault_bound
        ):
            raise LifecycleCertificateError(
                "party replacement requires the separate reconfiguration protocol"
            )

    @property
    def transition_hash(self) -> str:
        self.validate()
        return hash_bytes("LOCUS/epoch-transition/v1", encode(self.to_dict())).hex()

    def to_dict(self) -> dict[str, Any]:
        return {
            "bid": self.bid,
            "policy_version": self.policy_version,
            "predecessor_backup_digest": self.predecessor_backup_digest,
            "predecessor_budget": self.predecessor_budget,
            "predecessor_config_digest": self.predecessor_config_digest,
            "predecessor_consumed": self.predecessor_consumed,
            "predecessor_epoch": self.predecessor_epoch,
            "predecessor_head": self.predecessor_head,
            "successor_backup_digest": self.successor_backup_digest,
            "successor_budget": self.successor_budget,
            "successor_config_digest": self.successor_config_digest,
            "successor_epoch": self.successor_epoch,
            "transition_nonce": self.transition_nonce,
            "type": "REENROLL",
            "version": "LOCUS-epoch-transition-v1",
        }

    @classmethod
    def from_dict(cls, value: object) -> EpochTransition:
        parsed = _exact_dict(
            value,
            {
                "bid",
                "policy_version",
                "predecessor_backup_digest",
                "predecessor_budget",
                "predecessor_config_digest",
                "predecessor_consumed",
                "predecessor_epoch",
                "predecessor_head",
                "successor_backup_digest",
                "successor_budget",
                "successor_config_digest",
                "successor_epoch",
                "transition_nonce",
                "type",
                "version",
            },
            "epoch transition",
        )
        if (
            parsed["version"] != "LOCUS-epoch-transition-v1"
            or parsed["type"] != "REENROLL"
        ):
            raise LifecycleCertificateError("unsupported epoch transition")
        transition = cls(
            **{key: parsed[key] for key in parsed if key not in {"type", "version"}}
        )
        transition.validate()
        return transition


@dataclass(frozen=True)
class EpochApproval:
    party_id: int
    transition_hash: str
    signature: str

    @staticmethod
    def _message(transition_hash: str) -> bytes:
        return hash_bytes("LOCUS/epoch-approval/v1", bytes.fromhex(transition_hash))

    @classmethod
    def create(
        cls, transition: EpochTransition, signer: AuthorizerSigner
    ) -> EpochApproval:
        transition_hash = transition.transition_hash
        return cls(
            party_id=signer.party_id,
            transition_hash=transition_hash,
            signature=signer.sign(cls._message(transition_hash)),
        )

    def verify(self, transition: EpochTransition, config: AuthorizerConfig) -> None:
        party_id = _integer(self.party_id, "approval party identifier", minimum=1)
        _hex(self.transition_hash, "transition hash", bytes_length=32)
        _hex(self.signature, "approval signature", bytes_length=64)
        if self.transition_hash != transition.transition_hash:
            raise LifecycleCertificateError("approval transition mismatch")
        public_key = config.public_keys.get(party_id)
        if public_key is None:
            raise LifecycleCertificateError("approval signer is not configured")
        _verify_signature(
            public_key, self.signature, self._message(self.transition_hash)
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "party_id": self.party_id,
            "signature": self.signature,
            "transition_hash": self.transition_hash,
            "version": "LOCUS-epoch-approval-v1",
        }

    @classmethod
    def from_dict(cls, value: object) -> EpochApproval:
        parsed = _exact_dict(
            value,
            {"party_id", "signature", "transition_hash", "version"},
            "epoch approval",
        )
        if parsed["version"] != "LOCUS-epoch-approval-v1":
            raise LifecycleCertificateError("unsupported epoch approval")
        approval = cls(
            party_id=parsed["party_id"],
            transition_hash=parsed["transition_hash"],
            signature=parsed["signature"],
        )
        _integer(approval.party_id, "approval party identifier", minimum=1)
        _hex(approval.transition_hash, "transition hash", bytes_length=32)
        _hex(approval.signature, "approval signature", bytes_length=64)
        return approval


@dataclass(frozen=True)
class RuntimeEpochPackage:
    """Public binding for one party's durable epoch-specific runtime package.

    The descriptor contains only hashes. Canonical public parameters and the
    recipient's secret state travel separately over the authenticated channel
    and are stored only by that party.
    """

    bid: str
    epoch: int
    party_id: int
    transition_hash: str
    config_digest: str
    backup_digest: str
    native_enabled: bool
    parameters_hash: str
    party_state_hash: str

    @classmethod
    def create(
        cls,
        transition: EpochTransition,
        config: AuthorizerConfig,
        party_id: int,
        *,
        parameters: bytes | None,
        party_state: bytes | None,
    ) -> RuntimeEpochPackage:
        if (parameters is None) != (party_state is None):
            raise LifecycleCertificateError("incomplete native runtime package")
        native_enabled = parameters is not None
        descriptor = cls(
            bid=transition.bid,
            epoch=transition.successor_epoch,
            party_id=party_id,
            transition_hash=transition.transition_hash,
            config_digest=config.digest,
            backup_digest=config.backup_digest,
            native_enabled=native_enabled,
            parameters_hash=hash_bytes(
                "LOCUS/runtime-public-parameters/v1",
                b"" if parameters is None else parameters,
            ).hex(),
            party_state_hash=hash_bytes(
                "LOCUS/runtime-party-state/v1",
                b"" if party_state is None else party_state,
            ).hex(),
        )
        descriptor.verify_successor(transition, config)
        return descriptor

    def validate(self) -> None:
        _hex(self.bid, "runtime-package backup identifier", bytes_length=16)
        _integer(self.epoch, "runtime-package epoch", minimum=1)
        party_id = _integer(
            self.party_id, "runtime-package party identifier", minimum=1
        )
        if party_id > 255:
            raise LifecycleCertificateError("invalid runtime-package party identifier")
        _hex(self.transition_hash, "runtime-package transition hash", bytes_length=32)
        _hex(
            self.config_digest, "runtime-package configuration digest", bytes_length=32
        )
        _hex(self.backup_digest, "runtime-package backup digest", bytes_length=32)
        if not isinstance(self.native_enabled, bool):
            raise LifecycleCertificateError("invalid native runtime marker")
        _hex(self.parameters_hash, "runtime public-parameters hash", bytes_length=32)
        _hex(self.party_state_hash, "runtime party-state hash", bytes_length=32)

    def verify_successor(
        self, transition: EpochTransition, config: AuthorizerConfig
    ) -> None:
        self.validate()
        transition.validate()
        config.validate()
        if (
            self.bid != transition.bid
            or self.epoch != transition.successor_epoch
            or self.transition_hash != transition.transition_hash
            or self.config_digest != transition.successor_config_digest
            or self.config_digest != config.digest
            or self.backup_digest != transition.successor_backup_digest
            or self.backup_digest != config.backup_digest
            or self.party_id not in config.public_keys
        ):
            raise LifecycleCertificateError("runtime package does not match successor")

    @property
    def package_digest(self) -> str:
        self.validate()
        return hash_bytes(
            "LOCUS/runtime-epoch-package/v1", encode(self.to_dict())
        ).hex()

    def to_dict(self) -> dict[str, Any]:
        return {
            "backup_digest": self.backup_digest,
            "bid": self.bid,
            "config_digest": self.config_digest,
            "epoch": self.epoch,
            "native_enabled": self.native_enabled,
            "parameters_hash": self.parameters_hash,
            "party_id": self.party_id,
            "party_state_hash": self.party_state_hash,
            "transition_hash": self.transition_hash,
            "version": "LOCUS-runtime-epoch-package-v1",
        }

    @classmethod
    def from_dict(cls, value: object) -> RuntimeEpochPackage:
        parsed = _exact_dict(
            value,
            {
                "backup_digest",
                "bid",
                "config_digest",
                "epoch",
                "native_enabled",
                "parameters_hash",
                "party_id",
                "party_state_hash",
                "transition_hash",
                "version",
            },
            "runtime epoch package",
        )
        if parsed["version"] != "LOCUS-runtime-epoch-package-v1":
            raise LifecycleCertificateError("unsupported runtime epoch package")
        package = cls(**{key: parsed[key] for key in parsed if key != "version"})
        package.validate()
        return package


@dataclass(frozen=True)
class EpochReady:
    party_id: int
    transition_hash: str
    runtime_package_digest: str
    signature: str

    @staticmethod
    def _message(
        transition_hash: str, party_id: int, runtime_package_digest: str
    ) -> bytes:
        return hash_bytes(
            "LOCUS/epoch-ready/v2",
            bytes.fromhex(transition_hash),
            party_id.to_bytes(1, "big"),
            bytes.fromhex(runtime_package_digest),
        )

    @classmethod
    def create(
        cls,
        transition: EpochTransition,
        runtime_package: RuntimeEpochPackage,
        signer: AuthorizerSigner,
    ) -> EpochReady:
        transition_hash = transition.transition_hash
        if (
            runtime_package.party_id != signer.party_id
            or runtime_package.transition_hash != transition_hash
        ):
            raise LifecycleCertificateError("readiness package does not match signer")
        package_digest = runtime_package.package_digest
        return cls(
            party_id=signer.party_id,
            transition_hash=transition_hash,
            runtime_package_digest=package_digest,
            signature=signer.sign(
                cls._message(transition_hash, signer.party_id, package_digest)
            ),
        )

    def verify(self, transition: EpochTransition, config: AuthorizerConfig) -> None:
        party_id = _integer(self.party_id, "ready party identifier", minimum=1)
        _hex(self.transition_hash, "transition hash", bytes_length=32)
        _hex(
            self.runtime_package_digest,
            "runtime package digest",
            bytes_length=32,
        )
        _hex(self.signature, "ready signature", bytes_length=64)
        if self.transition_hash != transition.transition_hash:
            raise LifecycleCertificateError("readiness transition mismatch")
        public_key = config.public_keys.get(party_id)
        if public_key is None:
            raise LifecycleCertificateError("readiness signer is not configured")
        _verify_signature(
            public_key,
            self.signature,
            self._message(self.transition_hash, party_id, self.runtime_package_digest),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "party_id": self.party_id,
            "runtime_package_digest": self.runtime_package_digest,
            "signature": self.signature,
            "transition_hash": self.transition_hash,
            "version": "LOCUS-epoch-ready-v2",
        }

    @classmethod
    def from_dict(cls, value: object) -> EpochReady:
        parsed = _exact_dict(
            value,
            {
                "party_id",
                "runtime_package_digest",
                "signature",
                "transition_hash",
                "version",
            },
            "epoch readiness",
        )
        if parsed["version"] != "LOCUS-epoch-ready-v2":
            raise LifecycleCertificateError("unsupported epoch readiness")
        ready = cls(
            party_id=parsed["party_id"],
            transition_hash=parsed["transition_hash"],
            runtime_package_digest=parsed["runtime_package_digest"],
            signature=parsed["signature"],
        )
        _integer(ready.party_id, "ready party identifier", minimum=1)
        _hex(ready.transition_hash, "transition hash", bytes_length=32)
        _hex(ready.runtime_package_digest, "runtime package digest", bytes_length=32)
        _hex(ready.signature, "ready signature", bytes_length=64)
        return ready


@dataclass(frozen=True)
class EpochActivationCertificate:
    transition: EpochTransition
    approvals: tuple[EpochApproval, ...]
    readiness: tuple[EpochReady, ...]

    @classmethod
    def create(
        cls,
        transition: EpochTransition,
        approvals: list[EpochApproval],
        readiness: list[EpochReady],
        predecessor_config: AuthorizerConfig,
        successor_config: AuthorizerConfig,
    ) -> EpochActivationCertificate:
        certificate = cls(
            transition=transition,
            approvals=tuple(sorted(approvals, key=lambda item: item.party_id)),
            readiness=tuple(sorted(readiness, key=lambda item: item.party_id)),
        )
        certificate.verify(predecessor_config, successor_config)
        return certificate

    def verify(
        self,
        predecessor_config: AuthorizerConfig,
        successor_config: AuthorizerConfig,
    ) -> None:
        self.transition.verify_configs(predecessor_config, successor_config)
        approval_ids = [approval.party_id for approval in self.approvals]
        ready_ids = [ready.party_id for ready in self.readiness]
        if (
            approval_ids != sorted(set(approval_ids))
            or ready_ids != sorted(set(ready_ids))
            or len(approval_ids) < predecessor_config.quorum
            or len(ready_ids) < successor_config.quorum
        ):
            raise LifecycleCertificateError("invalid lifecycle quorum")
        for approval in self.approvals:
            approval.verify(self.transition, predecessor_config)
        for ready in self.readiness:
            ready.verify(self.transition, successor_config)

    @property
    def certificate_hash(self) -> str:
        return hash_bytes(
            "LOCUS/epoch-activation-certificate/v1", encode(self.to_dict())
        ).hex()

    def to_dict(self) -> dict[str, Any]:
        return {
            "approvals": [approval.to_dict() for approval in self.approvals],
            "readiness": [ready.to_dict() for ready in self.readiness],
            "transition": self.transition.to_dict(),
            "version": "LOCUS-epoch-activation-certificate-v1",
        }

    @classmethod
    def from_dict(cls, value: object) -> EpochActivationCertificate:
        parsed = _exact_dict(
            value,
            {"approvals", "readiness", "transition", "version"},
            "epoch activation certificate",
        )
        if parsed["version"] != "LOCUS-epoch-activation-certificate-v1":
            raise LifecycleCertificateError("unsupported activation certificate")
        if not isinstance(parsed["approvals"], list) or not isinstance(
            parsed["readiness"], list
        ):
            raise LifecycleCertificateError("invalid lifecycle certificate lists")
        return cls(
            transition=EpochTransition.from_dict(parsed["transition"]),
            approvals=tuple(
                EpochApproval.from_dict(item) for item in parsed["approvals"]
            ),
            readiness=tuple(EpochReady.from_dict(item) for item in parsed["readiness"]),
        )
