from __future__ import annotations

import copy
import unittest

from locus.attempt_certificates import (
    AttemptEntry,
    AuthorizationCertificate,
    AuthorizerConfig,
    AuthorizerSigner,
    CertificateError,
    EntryVote,
    InstallVote,
    PrepareCertificate,
)

BID = "ab" * 16
BACKUP_DIGEST = "bc" * 32
GENESIS_HEAD = "00" * 32


def configuration() -> tuple[AuthorizerConfig, list[AuthorizerSigner]]:
    signers = [AuthorizerSigner.generate(party_id) for party_id in range(1, 6)]
    config = AuthorizerConfig(
        bid=BID,
        epoch=1,
        backup_digest=BACKUP_DIGEST,
        fault_bound=2,
        quorum=4,
        public_keys={signer.party_id: signer.public_key_hex for signer in signers},
    )
    config.validate()
    return config, signers


def entry(config: AuthorizerConfig, *, sid_byte: str = "01") -> AttemptEntry:
    return AttemptEntry(
        bid=BID,
        epoch=1,
        config_digest=config.digest,
        log_index=1,
        previous_head=GENESIS_HEAD,
        sid=sid_byte * 32,
        request_digest="23" * 32,
        tpass_request_hash="34" * 32,
        resulting_consumed=1,
        effective_budget=3,
    )


def certificate(
    config: AuthorizerConfig,
    signers: list[AuthorizerSigner],
    attempt: AttemptEntry,
) -> AuthorizationCertificate:
    prepare = PrepareCertificate.create(
        attempt,
        [EntryVote.create(attempt, signer) for signer in signers[: config.quorum]],
        config,
    )
    return AuthorizationCertificate.create(
        prepare,
        [InstallVote.create(prepare, signer) for signer in signers[: config.quorum]],
        config,
    )


class AttemptCertificateTests(unittest.TestCase):
    def test_four_of_five_two_phase_certificate_round_trips(self) -> None:
        config, signers = configuration()
        attempt = entry(config)
        authorization = certificate(config, signers, attempt)
        authorization.verify(config)

        encoded = authorization.to_dict()
        decoded = AuthorizationCertificate.from_dict(encoded)
        decoded.verify(config)
        self.assertEqual(decoded.to_dict(), encoded)
        self.assertEqual(decoded.certificate_hash, authorization.certificate_hash)
        self.assertEqual(decoded.authorization_fields()["config_digest"], config.digest)

    def test_insufficient_duplicate_and_forged_votes_are_rejected(self) -> None:
        config, signers = configuration()
        attempt = entry(config)
        votes = [EntryVote.create(attempt, signer) for signer in signers]

        with self.assertRaises(CertificateError):
            PrepareCertificate.create(attempt, votes[:3], config)
        with self.assertRaises(CertificateError):
            PrepareCertificate.create(
                attempt, [votes[0], votes[0], *votes[1:3]], config
            )

        forged = copy.deepcopy(votes[:4])
        forged[0] = EntryVote(
            forged[0].authorizer_id,
            forged[0].entry_hash,
            "00" * 64,
        )
        with self.assertRaises(CertificateError):
            PrepareCertificate.create(attempt, forged, config)

        prepare = PrepareCertificate.create(attempt, votes[:4], config)
        install_votes = [InstallVote.create(prepare, signer) for signer in signers]
        with self.assertRaises(CertificateError):
            AuthorizationCertificate.create(prepare, install_votes[:3], config)
        with self.assertRaises(CertificateError):
            AuthorizationCertificate.create(
                prepare,
                [install_votes[0], install_votes[0], *install_votes[1:3]],
                config,
            )

    def test_certificate_is_bound_to_entry_and_configuration(self) -> None:
        config, signers = configuration()
        attempt = entry(config)
        authorization = certificate(config, signers, attempt)

        changed = copy.deepcopy(authorization.to_dict())
        changed["prepare"]["entry"]["sid"] = "99" * 32
        with self.assertRaises(CertificateError):
            AuthorizationCertificate.from_dict(changed).verify(config)

        other_signer = AuthorizerSigner.generate(5)
        other_config = AuthorizerConfig(
            bid=config.bid,
            epoch=config.epoch,
            backup_digest="cd" * 32,
            fault_bound=config.fault_bound,
            quorum=config.quorum,
            public_keys={**config.public_keys, 5: other_signer.public_key_hex},
        )
        with self.assertRaises(CertificateError):
            authorization.verify(other_config)

    def test_schema_and_quorum_intersection_are_strict(self) -> None:
        config, signers = configuration()
        authorization = certificate(config, signers, entry(config))
        encoded = authorization.to_dict()

        with self.assertRaises(CertificateError):
            AuthorizationCertificate.from_dict({**encoded, "unexpected": 1})
        with self.assertRaises(CertificateError):
            AuthorizerConfig(
                bid=BID,
                epoch=1,
                backup_digest=BACKUP_DIGEST,
                fault_bound=2,
                quorum=3,
                public_keys=config.public_keys,
            ).validate()

        decoded_config = AuthorizerConfig.from_dict(config.to_dict())
        self.assertEqual(decoded_config.digest, config.digest)
        restored_signer = AuthorizerSigner.from_private_key_hex(
            signers[0].party_id, signers[0].private_key_hex
        )
        self.assertEqual(restored_signer.public_key_hex, signers[0].public_key_hex)

        noncanonical = copy.deepcopy(config.to_dict())
        noncanonical["public_keys"].reverse()
        with self.assertRaises(CertificateError):
            AuthorizerConfig.from_dict(noncanonical)


if __name__ == "__main__":
    unittest.main()
