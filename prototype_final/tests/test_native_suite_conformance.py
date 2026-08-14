from __future__ import annotations

import unittest
from collections.abc import Callable
from typing import Any

from locus import _tpass_native as native
from locus.appss_formats import AppssHolderBinding, instance_id, oprf_input
from locus.contracts import RecoveryContext, ThresholdParameters
from locus.yi_compat import RecoverySuiteError, YiTpassRecoveryAdapter

Initialize = Callable[[], tuple[bytes, Any]]
Recover = Callable[[Any, bytes, tuple[int, ...]], bytes]
CORRECT = b"correct".ljust(32, b"\x00")
WRONG = b"wrong".ljust(32, b"\x00")


def run_conformance(
    testcase: unittest.TestCase,
    initialize: Initialize,
    recover: Recover,
) -> None:
    expected, state = initialize()
    for subset in ((1, 2), (1, 3), (2, 3)):
        testcase.assertEqual(recover(state, CORRECT, subset), expected)
    with testcase.assertRaises((RecoverySuiteError, native.NativeAppssError)):
        recover(state, WRONG, (1, 2))


class NativeSuiteConformanceTests(unittest.TestCase):
    def test_yi_and_appss_satisfy_the_same_recovery_secret_contract(self) -> None:
        context = RecoveryContext(
            suite_id="LOCUS-TPASS-YI-ZK-RISTRETTO255-v1",
            recovery_id="conformance-recovery",
            backup_id="00112233445566778899aabbccddeeff",
            epoch=1,
            policy_id="LOCUS-canonical-email-set-v1",
            configuration_digest="11" * 32,
            digest_context="conformance:1",
        )
        yi = YiTpassRecoveryAdapter()

        def initialize_yi() -> tuple[bytes, Any]:
            enrollment = yi.initialize(
                context=context,
                password_input=CORRECT,
                threshold=ThresholdParameters(k=2, n=3),
            )
            return enrollment.recovery_secret, enrollment

        def recover_yi(state: Any, password: bytes, subset: tuple[int, ...]) -> bytes:
            enrollment = state
            return yi.recover(
                context=context,
                password_input=password,
                public_state=enrollment.public_state,
                party_states=tuple(
                    enrollment.party_states[index - 1] for index in subset
                ),
            )

        run_conformance(self, initialize_yi, recover_yi)

        appss_context = bytes.fromhex("ab" * 32)
        holders = [
            AppssHolderBinding(
                index=index,
                party_id=f"party-{index}",
                service_identity="spki-sha256:" + bytes([index] * 32).hex(),
            )
            for index in range(1, 4)
        ]
        keys = [
            native.appss_generate_server_key(appss_context, index)
            for index in range(1, 4)
        ]

        def masks(password: bytes) -> list[tuple[int, bytes]]:
            result: list[tuple[int, bytes]] = []
            for key, holder in zip(keys, holders, strict=True):
                instance = instance_id(appss_context, holder)
                session, blinded = native.appss_blind(oprf_input(instance, password))
                evaluated = native.appss_blind_evaluate(key, appss_context, blinded)
                output = native.appss_finalize(session, evaluated)
                result.append(
                    (holder.index, native.appss_derive_mask(instance, output))
                )
            return result

        def initialize_appss() -> tuple[bytes, Any]:
            correct_masks = masks(CORRECT)
            public, secret = native.appss_initialize_fixture(
                appss_context,
                CORRECT,
                2,
                3,
                correct_masks,
            )
            return secret, public

        def recover_appss(
            state: Any, password: bytes, subset: tuple[int, ...]
        ) -> bytes:
            candidate_masks = masks(password)
            selected = [candidate_masks[index - 1] for index in subset]
            return native.appss_recover_fixture(
                appss_context,
                password,
                state,
                selected,
            )

        run_conformance(self, initialize_appss, recover_appss)


if __name__ == "__main__":
    unittest.main()
