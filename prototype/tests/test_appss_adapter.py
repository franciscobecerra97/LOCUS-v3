from __future__ import annotations

import copy
import unittest

from locus.appss import AppssRecoveryAdapter
from locus.appss_formats import APPSS_SUITE_ID
from locus.contracts import (
    PartyRecoveryState,
    PublicRecoveryState,
    RecoveryContext,
    ThresholdParameters,
)
from locus.yi_compat import RecoverySuiteError


def appss_context(*, digest: str = "ab" * 32) -> RecoveryContext:
    return RecoveryContext(
        suite_id=APPSS_SUITE_ID,
        recovery_id="appss-adapter-test",
        backup_id="00112233445566778899aabbccddeeff",
        epoch=1,
        policy_id="LOCUS-canonical-email-set-v1",
        configuration_digest="cd" * 32,
        digest_context="adapter-test:1",
        suite_context_digest=digest,
    )


class AppssAdapterTests(unittest.TestCase):
    def test_every_two_of_three_subset_and_wrong_input(self) -> None:
        adapter = AppssRecoveryAdapter()
        context = appss_context()
        password = b"correct".ljust(32, b"\x00")
        enrollment = adapter.initialize(
            context=context,
            password_input=password,
            threshold=ThresholdParameters(k=2, n=3),
        )
        self.assertEqual(enrollment.public_state.suite_id, APPSS_SUITE_ID)
        self.assertEqual(
            [state.holder_id for state in enrollment.party_states], [1, 2, 3]
        )
        for subset in ((0, 1), (0, 2), (1, 2)):
            selected = tuple(enrollment.party_states[index] for index in subset)
            self.assertEqual(
                adapter.recover(
                    context=context,
                    password_input=password,
                    public_state=enrollment.public_state,
                    party_states=selected,
                ),
                enrollment.recovery_secret,
            )
        with self.assertRaisesRegex(RecoverySuiteError, "recovery failed"):
            adapter.recover(
                context=context,
                password_input=b"wrong".ljust(32, b"\x00"),
                public_state=enrollment.public_state,
                party_states=enrollment.party_states[:2],
            )

    def test_cross_suite_context_state_and_mixed_omega_fail_closed(self) -> None:
        adapter = AppssRecoveryAdapter()
        context = appss_context()
        enrollment = adapter.initialize(
            context=context,
            password_input=b"x" * 32,
            threshold=ThresholdParameters(k=2, n=3),
        )
        with self.assertRaises(RecoverySuiteError):
            adapter.recover(
                context=appss_context(digest="ac" * 32),
                password_input=b"x" * 32,
                public_state=enrollment.public_state,
                party_states=enrollment.party_states[:2],
            )
        wrong_suite = PublicRecoveryState(
            suite_id="LOCUS-TPASS-YI-ZK-RISTRETTO255-v1",
            format_id=enrollment.public_state.format_id,
            payload=enrollment.public_state.payload,
        )
        with self.assertRaises(RecoverySuiteError):
            adapter.decode_public_state(wrong_suite)

        first = adapter.decode_party_state(enrollment.party_states[0])
        altered = copy.deepcopy(first)
        altered["omega_digest"] = "00" * 32
        from locus.codec import encode

        mixed = PartyRecoveryState(
            suite_id=APPSS_SUITE_ID,
            format_id=enrollment.party_states[0].format_id,
            holder_id=1,
            payload=encode(altered),
        )
        with self.assertRaises(RecoverySuiteError):
            adapter.recover(
                context=context,
                password_input=b"x" * 32,
                public_state=enrollment.public_state,
                party_states=(mixed, enrollment.party_states[1]),
            )

    def test_requires_exact_first_profile_and_explicit_context_digest(self) -> None:
        adapter = AppssRecoveryAdapter()
        context = appss_context()
        with self.assertRaises(RecoverySuiteError):
            adapter.initialize(
                context=context,
                password_input=b"x" * 32,
                threshold=ThresholdParameters(k=3, n=5),
            )
        missing = RecoveryContext(
            suite_id=APPSS_SUITE_ID,
            recovery_id=context.recovery_id,
            backup_id=context.backup_id,
            epoch=context.epoch,
            policy_id=context.policy_id,
            configuration_digest=context.configuration_digest,
            digest_context=context.digest_context,
        )
        with self.assertRaises(RecoverySuiteError):
            adapter.initialize(
                context=missing,
                password_input=b"x" * 32,
                threshold=ThresholdParameters(k=2, n=3),
            )


if __name__ == "__main__":
    unittest.main()
