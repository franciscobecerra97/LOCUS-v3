"""Canonical signed objects for the LOCUS two-phase attempt ledger."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from .codec import encode
from .crypto import hash_bytes


class CertificateError(Exception):
    """A signed attempt-control object is malformed or invalid."""


def _integer(value: object, label: str, *, minimum: int = 1) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise CertificateError(f"invalid {label}")
    return value


def _hex(value: object, label: str, *, bytes_length: int) -> str:
    if (
        not isinstance(value, str)
        or len(value) != bytes_length * 2
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise CertificateError(f"invalid {label}")
    return value


def _exact_dict(value: object, expected: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != expected:
        raise CertificateError(f"invalid {label}")
    return value


@dataclass(frozen=True)
class AuthorizerConfig:
    bid: str
    epoch: int
    backup_digest: str
    fault_bound: int
    quorum: int
    public_keys: dict[int, str]

    def validate(self) -> None:
        _hex(self.bid, "backup identifier", bytes_length=16)
        _integer(self.epoch, "epoch")
        _hex(self.backup_digest, "backup digest", bytes_length=32)
        if (
            isinstance(self.fault_bound, bool)
            or not isinstance(self.fault_bound, int)
            or self.fault_bound < 0
        ):
            raise CertificateError("invalid fault bound")
        quorum = _integer(self.quorum, "quorum")
        if not isinstance(self.public_keys, dict) or not self.public_keys:
            raise CertificateError("invalid authorizer keys")
        party_ids = sorted(self.public_keys)
        if (
            any(
                isinstance(party_id, bool) or not isinstance(party_id, int)
                for party_id in party_ids
            )
            or party_ids[0] < 1
            or party_ids[-1] > 255
        ):
            raise CertificateError("invalid authorizer identifier")
        for public_key in self.public_keys.values():
            _hex(public_key, "authorizer public key", bytes_length=32)
        party_count = len(party_ids)
        if self.fault_bound >= party_count or quorum > party_count:
            raise CertificateError("invalid authorizer threshold")
        if 2 * quorum <= party_count + self.fault_bound:
            raise CertificateError("unsafe authorizer quorum intersection")

    @property
    def digest(self) -> str:
        self.validate()
        return hash_bytes("LOCUS/attempt-config/v2", encode(self.to_dict())).hex()

    @classmethod
    def from_dict(cls, value: object) -> AuthorizerConfig:
        parsed = _exact_dict(
            value,
            {
                "bid",
                "epoch",
                "backup_digest",
                "fault_bound",
                "public_keys",
                "quorum",
                "version",
            },
            "authorizer configuration",
        )
        if parsed["version"] != "LOCUS-attempt-config-v2" or not isinstance(
            parsed["public_keys"], list
        ):
            raise CertificateError("unsupported authorizer configuration")
        public_keys: dict[int, str] = {}
        previous_party_id = 0
        for item in parsed["public_keys"]:
            key = _exact_dict(
                item,
                {"party_id", "public_key"},
                "authorizer public-key entry",
            )
            party_id = _integer(key["party_id"], "authorizer identifier")
            if party_id > 255 or party_id <= previous_party_id:
                raise CertificateError("noncanonical authorizer identifiers")
            _hex(key["public_key"], "authorizer public key", bytes_length=32)
            public_keys[party_id] = key["public_key"]
            previous_party_id = party_id
        config = cls(
            bid=parsed["bid"],
            epoch=parsed["epoch"],
            backup_digest=parsed["backup_digest"],
            fault_bound=parsed["fault_bound"],
            quorum=parsed["quorum"],
            public_keys=public_keys,
        )
        config.validate()
        return config

    def to_dict(self) -> dict[str, Any]:
        return {
            "bid": self.bid,
            "epoch": self.epoch,
            "backup_digest": self.backup_digest,
            "fault_bound": self.fault_bound,
            "public_keys": [
                {"party_id": party_id, "public_key": self.public_keys[party_id]}
                for party_id in sorted(self.public_keys)
            ],
            "quorum": self.quorum,
            "version": "LOCUS-attempt-config-v2",
        }


@dataclass(frozen=True)
class AuthorizerSigner:
    party_id: int
    _private_key: Ed25519PrivateKey

    @classmethod
    def generate(cls, party_id: int) -> AuthorizerSigner:
        _integer(party_id, "authorizer identifier")
        if party_id > 255:
            raise CertificateError("invalid authorizer identifier")
        return cls(party_id, Ed25519PrivateKey.generate())

    @property
    def public_key_hex(self) -> str:
        return (
            self._private_key.public_key()
            .public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw,
            )
            .hex()
        )

    @property
    def private_key_hex(self) -> str:
        return self._private_key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption(),
        ).hex()

    @classmethod
    def from_private_key_hex(
        cls, party_id: int, private_key_hex: object
    ) -> AuthorizerSigner:
        _integer(party_id, "authorizer identifier")
        if party_id > 255:
            raise CertificateError("invalid authorizer identifier")
        encoded = _hex(private_key_hex, "authorizer private key", bytes_length=32)
        return cls(
            party_id, Ed25519PrivateKey.from_private_bytes(bytes.fromhex(encoded))
        )

    def sign(self, message: bytes) -> str:
        return self._private_key.sign(message).hex()


@dataclass(frozen=True)
class AttemptEntry:
    bid: str
    epoch: int
    config_digest: str
    log_index: int
    previous_head: str
    sid: str
    request_digest: str
    tpass_request_hash: str
    resulting_consumed: int
    effective_budget: int

    def validate(self) -> None:
        _hex(self.bid, "backup identifier", bytes_length=16)
        _integer(self.epoch, "epoch")
        _hex(self.config_digest, "configuration digest", bytes_length=32)
        _integer(self.log_index, "log index")
        _hex(self.previous_head, "previous head", bytes_length=32)
        _hex(self.sid, "session identifier", bytes_length=32)
        _hex(self.request_digest, "request digest", bytes_length=32)
        _hex(self.tpass_request_hash, "TPASS request hash", bytes_length=32)
        _integer(self.resulting_consumed, "resulting consumed count")
        _integer(self.effective_budget, "effective budget")
        if self.resulting_consumed > self.effective_budget:
            raise CertificateError("attempt budget exhausted")

    @classmethod
    def from_dict(cls, value: object) -> AttemptEntry:
        parsed = _exact_dict(
            value,
            {
                "bid",
                "config_digest",
                "effective_budget",
                "epoch",
                "log_index",
                "previous_head",
                "request_digest",
                "resulting_consumed",
                "sid",
                "tpass_request_hash",
                "type",
                "version",
            },
            "attempt entry",
        )
        if parsed["version"] != "LOCUS-attempt-entry-v1" or parsed["type"] != "ATTEMPT":
            raise CertificateError("unsupported attempt entry")
        entry = cls(
            bid=parsed["bid"],
            epoch=parsed["epoch"],
            config_digest=parsed["config_digest"],
            log_index=parsed["log_index"],
            previous_head=parsed["previous_head"],
            sid=parsed["sid"],
            request_digest=parsed["request_digest"],
            tpass_request_hash=parsed["tpass_request_hash"],
            resulting_consumed=parsed["resulting_consumed"],
            effective_budget=parsed["effective_budget"],
        )
        entry.validate()
        return entry

    def to_dict(self) -> dict[str, Any]:
        return {
            "bid": self.bid,
            "config_digest": self.config_digest,
            "effective_budget": self.effective_budget,
            "epoch": self.epoch,
            "log_index": self.log_index,
            "previous_head": self.previous_head,
            "request_digest": self.request_digest,
            "resulting_consumed": self.resulting_consumed,
            "sid": self.sid,
            "tpass_request_hash": self.tpass_request_hash,
            "type": "ATTEMPT",
            "version": "LOCUS-attempt-entry-v1",
        }

    @property
    def entry_hash(self) -> str:
        self.validate()
        return hash_bytes("LOCUS/attempt-entry/v1", encode(self.to_dict())).hex()


def _entry_vote_message(config_digest: str, entry_hash: str) -> bytes:
    return hash_bytes(
        "LOCUS/attempt-vote/v1",
        bytes.fromhex(config_digest),
        bytes.fromhex(entry_hash),
    )


def _install_vote_message(config_digest: str, prepare_hash: str) -> bytes:
    return hash_bytes(
        "LOCUS/attempt-install/v1",
        bytes.fromhex(config_digest),
        bytes.fromhex(prepare_hash),
    )


@dataclass(frozen=True)
class EntryVote:
    authorizer_id: int
    entry_hash: str
    signature: str

    @classmethod
    def create(cls, entry: AttemptEntry, signer: AuthorizerSigner) -> EntryVote:
        signature = signer.sign(
            _entry_vote_message(entry.config_digest, entry.entry_hash)
        )
        return cls(signer.party_id, entry.entry_hash, signature)

    @classmethod
    def from_dict(cls, value: object) -> EntryVote:
        parsed = _exact_dict(
            value,
            {"authorizer_id", "entry_hash", "signature", "version"},
            "entry vote",
        )
        if parsed["version"] != "LOCUS-entry-vote-v1":
            raise CertificateError("unsupported entry vote")
        vote = cls(parsed["authorizer_id"], parsed["entry_hash"], parsed["signature"])
        vote.validate_shape()
        return vote

    def validate_shape(self) -> None:
        party_id = _integer(self.authorizer_id, "authorizer identifier")
        if party_id > 255:
            raise CertificateError("invalid authorizer identifier")
        _hex(self.entry_hash, "entry hash", bytes_length=32)
        _hex(self.signature, "entry-vote signature", bytes_length=64)

    def verify(self, entry: AttemptEntry, config: AuthorizerConfig) -> None:
        entry.validate()
        config.validate()
        public_key = config.public_keys.get(self.authorizer_id)
        if (
            public_key is None
            or entry.config_digest != config.digest
            or self.entry_hash != entry.entry_hash
        ):
            raise CertificateError("entry vote does not match request")
        self.validate_shape()
        _verify_signature(
            public_key,
            self.signature,
            _entry_vote_message(config.digest, entry.entry_hash),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "authorizer_id": self.authorizer_id,
            "entry_hash": self.entry_hash,
            "signature": self.signature,
            "version": "LOCUS-entry-vote-v1",
        }


def _verify_signature(public_key_hex: str, signature_hex: str, message: bytes) -> None:
    try:
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_key_hex)).verify(
            bytes.fromhex(signature_hex), message
        )
    except (InvalidSignature, ValueError) as exc:
        raise CertificateError("invalid authorizer signature") from exc


@dataclass(frozen=True)
class PrepareCertificate:
    entry: AttemptEntry
    votes: tuple[EntryVote, ...]

    @classmethod
    def create(
        cls,
        entry: AttemptEntry,
        votes: list[EntryVote],
        config: AuthorizerConfig,
    ) -> PrepareCertificate:
        certificate = cls(
            entry, tuple(sorted(votes, key=lambda vote: vote.authorizer_id))
        )
        certificate.verify(config)
        return certificate

    @classmethod
    def from_dict(cls, value: object) -> PrepareCertificate:
        parsed = _exact_dict(
            value, {"entry", "votes", "version"}, "prepare certificate"
        )
        if parsed["version"] != "LOCUS-prepare-certificate-v1" or not isinstance(
            parsed["votes"], list
        ):
            raise CertificateError("unsupported prepare certificate")
        return cls(
            AttemptEntry.from_dict(parsed["entry"]),
            tuple(EntryVote.from_dict(vote) for vote in parsed["votes"]),
        )

    def verify(self, config: AuthorizerConfig) -> None:
        config.validate()
        self.entry.validate()
        if (
            self.entry.bid != config.bid
            or self.entry.epoch != config.epoch
            or self.entry.config_digest != config.digest
        ):
            raise CertificateError("prepare certificate configuration mismatch")
        authorizer_ids = [vote.authorizer_id for vote in self.votes]
        if authorizer_ids != sorted(set(authorizer_ids)):
            raise CertificateError("duplicate or noncanonical entry votes")
        if len(authorizer_ids) < config.quorum:
            raise CertificateError("insufficient entry-vote quorum")
        for vote in self.votes:
            vote.validate_shape()
            public_key = config.public_keys.get(vote.authorizer_id)
            if public_key is None or vote.entry_hash != self.entry.entry_hash:
                raise CertificateError("entry vote does not match certificate")
            _verify_signature(
                public_key,
                vote.signature,
                _entry_vote_message(config.digest, self.entry.entry_hash),
            )

    @property
    def certificate_hash(self) -> str:
        return hash_bytes("LOCUS/prepare-certificate/v1", encode(self.to_dict())).hex()

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry": self.entry.to_dict(),
            "votes": [vote.to_dict() for vote in self.votes],
            "version": "LOCUS-prepare-certificate-v1",
        }


@dataclass(frozen=True)
class InstallVote:
    authorizer_id: int
    prepare_hash: str
    signature: str

    @classmethod
    def create(
        cls, prepare: PrepareCertificate, signer: AuthorizerSigner
    ) -> InstallVote:
        signature = signer.sign(
            _install_vote_message(prepare.entry.config_digest, prepare.certificate_hash)
        )
        return cls(signer.party_id, prepare.certificate_hash, signature)

    @classmethod
    def from_dict(cls, value: object) -> InstallVote:
        parsed = _exact_dict(
            value,
            {"authorizer_id", "prepare_hash", "signature", "version"},
            "install vote",
        )
        if parsed["version"] != "LOCUS-install-vote-v1":
            raise CertificateError("unsupported install vote")
        vote = cls(parsed["authorizer_id"], parsed["prepare_hash"], parsed["signature"])
        vote.validate_shape()
        return vote

    def validate_shape(self) -> None:
        party_id = _integer(self.authorizer_id, "authorizer identifier")
        if party_id > 255:
            raise CertificateError("invalid authorizer identifier")
        _hex(self.prepare_hash, "prepare certificate hash", bytes_length=32)
        _hex(self.signature, "install-vote signature", bytes_length=64)

    def verify(self, prepare: PrepareCertificate, config: AuthorizerConfig) -> None:
        prepare.verify(config)
        public_key = config.public_keys.get(self.authorizer_id)
        if public_key is None or self.prepare_hash != prepare.certificate_hash:
            raise CertificateError("install vote does not match request")
        self.validate_shape()
        _verify_signature(
            public_key,
            self.signature,
            _install_vote_message(config.digest, prepare.certificate_hash),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "authorizer_id": self.authorizer_id,
            "prepare_hash": self.prepare_hash,
            "signature": self.signature,
            "version": "LOCUS-install-vote-v1",
        }


@dataclass(frozen=True)
class AuthorizationCertificate:
    prepare: PrepareCertificate
    install_votes: tuple[InstallVote, ...]

    @classmethod
    def create(
        cls,
        prepare: PrepareCertificate,
        install_votes: list[InstallVote],
        config: AuthorizerConfig,
    ) -> AuthorizationCertificate:
        certificate = cls(
            prepare,
            tuple(sorted(install_votes, key=lambda vote: vote.authorizer_id)),
        )
        certificate.verify(config)
        return certificate

    @classmethod
    def from_dict(cls, value: object) -> AuthorizationCertificate:
        parsed = _exact_dict(
            value,
            {"install_votes", "prepare", "version"},
            "authorization certificate",
        )
        if parsed["version"] != "LOCUS-authorization-certificate-v1" or not isinstance(
            parsed["install_votes"], list
        ):
            raise CertificateError("unsupported authorization certificate")
        return cls(
            PrepareCertificate.from_dict(parsed["prepare"]),
            tuple(InstallVote.from_dict(vote) for vote in parsed["install_votes"]),
        )

    def verify(self, config: AuthorizerConfig) -> None:
        self.prepare.verify(config)
        authorizer_ids = [vote.authorizer_id for vote in self.install_votes]
        if authorizer_ids != sorted(set(authorizer_ids)):
            raise CertificateError("duplicate or noncanonical install votes")
        if len(authorizer_ids) < config.quorum:
            raise CertificateError("insufficient install-vote quorum")
        for vote in self.install_votes:
            vote.validate_shape()
            public_key = config.public_keys.get(vote.authorizer_id)
            if public_key is None or vote.prepare_hash != self.prepare.certificate_hash:
                raise CertificateError("install vote does not match certificate")
            _verify_signature(
                public_key,
                vote.signature,
                _install_vote_message(config.digest, self.prepare.certificate_hash),
            )

    @property
    def certificate_hash(self) -> str:
        return hash_bytes(
            "LOCUS/authorization-certificate/v1", encode(self.to_dict())
        ).hex()

    def authorization_fields(self) -> dict[str, Any]:
        entry = self.prepare.entry
        return {
            "bid": entry.bid,
            "epoch": entry.epoch,
            "config_digest": entry.config_digest,
            "log_index": entry.log_index,
            "previous_head": entry.previous_head,
            "sid": entry.sid,
            "request_digest": entry.request_digest,
            "tpass_request_hash": entry.tpass_request_hash,
            "resulting_consumed": entry.resulting_consumed,
            "effective_budget": entry.effective_budget,
            "certificate_hash": self.certificate_hash,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "install_votes": [vote.to_dict() for vote in self.install_votes],
            "prepare": self.prepare.to_dict(),
            "version": "LOCUS-authorization-certificate-v1",
        }


@dataclass(frozen=True)
class FreshnessRequest:
    bid: str
    epoch: int
    config_digest: str
    authorization_hash: str
    request_digest: str
    responding_party_id: int
    phase: str
    boot_nonce: str
    response_nonce: str

    def validate(self) -> None:
        _hex(self.bid, "backup identifier", bytes_length=16)
        _integer(self.epoch, "epoch")
        _hex(self.config_digest, "configuration digest", bytes_length=32)
        _hex(self.authorization_hash, "authorization hash", bytes_length=32)
        _hex(self.request_digest, "request digest", bytes_length=32)
        party_id = _integer(self.responding_party_id, "responding party identifier")
        if party_id > 255 or self.phase != "commitment":
            raise CertificateError("invalid freshness phase")
        _hex(self.boot_nonce, "boot nonce", bytes_length=32)
        _hex(self.response_nonce, "response nonce", bytes_length=32)

    @classmethod
    def from_dict(cls, value: object) -> FreshnessRequest:
        parsed = _exact_dict(
            value,
            {
                "authorization_hash",
                "bid",
                "boot_nonce",
                "config_digest",
                "epoch",
                "phase",
                "request_digest",
                "responding_party_id",
                "response_nonce",
                "version",
            },
            "freshness request",
        )
        if parsed["version"] != "LOCUS-response-freshness-request-v1":
            raise CertificateError("unsupported freshness request")
        request = cls(
            bid=parsed["bid"],
            epoch=parsed["epoch"],
            config_digest=parsed["config_digest"],
            authorization_hash=parsed["authorization_hash"],
            request_digest=parsed["request_digest"],
            responding_party_id=parsed["responding_party_id"],
            phase=parsed["phase"],
            boot_nonce=parsed["boot_nonce"],
            response_nonce=parsed["response_nonce"],
        )
        request.validate()
        return request

    @property
    def request_hash(self) -> str:
        self.validate()
        return hash_bytes("LOCUS/response-freshness/v1", encode(self.to_dict())).hex()

    def to_dict(self) -> dict[str, Any]:
        return {
            "authorization_hash": self.authorization_hash,
            "bid": self.bid,
            "boot_nonce": self.boot_nonce,
            "config_digest": self.config_digest,
            "epoch": self.epoch,
            "phase": self.phase,
            "request_digest": self.request_digest,
            "responding_party_id": self.responding_party_id,
            "response_nonce": self.response_nonce,
            "version": "LOCUS-response-freshness-request-v1",
        }


@dataclass(frozen=True)
class FreshnessVote:
    authorizer_id: int
    freshness_request_hash: str
    signature: str

    @classmethod
    def create(
        cls, request: FreshnessRequest, signer: AuthorizerSigner
    ) -> FreshnessVote:
        return cls(
            signer.party_id,
            request.request_hash,
            signer.sign(bytes.fromhex(request.request_hash)),
        )

    @classmethod
    def from_dict(cls, value: object) -> FreshnessVote:
        parsed = _exact_dict(
            value,
            {"authorizer_id", "freshness_request_hash", "signature", "version"},
            "freshness vote",
        )
        if parsed["version"] != "LOCUS-response-freshness-vote-v1":
            raise CertificateError("unsupported freshness vote")
        vote = cls(
            parsed["authorizer_id"],
            parsed["freshness_request_hash"],
            parsed["signature"],
        )
        vote.validate_shape()
        return vote

    def validate_shape(self) -> None:
        party_id = _integer(self.authorizer_id, "authorizer identifier")
        if party_id > 255:
            raise CertificateError("invalid authorizer identifier")
        _hex(self.freshness_request_hash, "freshness request hash", bytes_length=32)
        _hex(self.signature, "freshness signature", bytes_length=64)

    def verify(self, request: FreshnessRequest, config: AuthorizerConfig) -> None:
        request.validate()
        config.validate()
        public_key = config.public_keys.get(self.authorizer_id)
        if (
            public_key is None
            or request.config_digest != config.digest
            or self.freshness_request_hash != request.request_hash
        ):
            raise CertificateError("freshness vote does not match request")
        self.validate_shape()
        _verify_signature(
            public_key, self.signature, bytes.fromhex(request.request_hash)
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "authorizer_id": self.authorizer_id,
            "freshness_request_hash": self.freshness_request_hash,
            "signature": self.signature,
            "version": "LOCUS-response-freshness-vote-v1",
        }


@dataclass(frozen=True)
class ResponseFreshnessCertificate:
    request: FreshnessRequest
    votes: tuple[FreshnessVote, ...]

    @classmethod
    def create(
        cls,
        request: FreshnessRequest,
        votes: list[FreshnessVote],
        config: AuthorizerConfig,
    ) -> ResponseFreshnessCertificate:
        certificate = cls(
            request,
            tuple(sorted(votes, key=lambda vote: vote.authorizer_id)),
        )
        certificate.verify(config)
        return certificate

    @classmethod
    def from_dict(cls, value: object) -> ResponseFreshnessCertificate:
        parsed = _exact_dict(
            value,
            {"request", "votes", "version"},
            "response freshness certificate",
        )
        if parsed[
            "version"
        ] != "LOCUS-response-freshness-certificate-v1" or not isinstance(
            parsed["votes"], list
        ):
            raise CertificateError("unsupported response freshness certificate")
        return cls(
            FreshnessRequest.from_dict(parsed["request"]),
            tuple(FreshnessVote.from_dict(vote) for vote in parsed["votes"]),
        )

    def verify(self, config: AuthorizerConfig) -> None:
        config.validate()
        self.request.validate()
        if (
            self.request.bid != config.bid
            or self.request.epoch != config.epoch
            or self.request.config_digest != config.digest
        ):
            raise CertificateError("freshness configuration mismatch")
        authorizer_ids = [vote.authorizer_id for vote in self.votes]
        if authorizer_ids != sorted(set(authorizer_ids)):
            raise CertificateError("duplicate or noncanonical freshness votes")
        if len(authorizer_ids) < config.quorum:
            raise CertificateError("insufficient freshness quorum")
        for vote in self.votes:
            vote.validate_shape()
            public_key = config.public_keys.get(vote.authorizer_id)
            if (
                public_key is None
                or vote.freshness_request_hash != self.request.request_hash
            ):
                raise CertificateError("freshness vote does not match request")
            _verify_signature(
                public_key,
                vote.signature,
                bytes.fromhex(self.request.request_hash),
            )

    @property
    def certificate_hash(self) -> str:
        return hash_bytes(
            "LOCUS/response-freshness-certificate/v1", encode(self.to_dict())
        ).hex()

    def to_dict(self) -> dict[str, Any]:
        return {
            "request": self.request.to_dict(),
            "votes": [vote.to_dict() for vote in self.votes],
            "version": "LOCUS-response-freshness-certificate-v1",
        }
