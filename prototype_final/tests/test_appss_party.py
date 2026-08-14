from __future__ import annotations

import hashlib
import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from locus import _tpass_native as native
from locus.appss_formats import (
    APPSS_INSTALL_FORMAT,
    APPSS_PROFILE_2_OF_3,
    APPSS_PUBLIC_STATE_FORMAT,
    APPSS_REQUEST_FORMAT,
    APPSS_SUITE_ID,
    MAX_INSTALL_BYTES,
    MAX_REQUEST_BYTES,
    AppssHolderBinding,
    canonical_decode,
    encode_checked,
    instance_id,
    oprf_input,
    validate_install,
    validate_request,
    validate_response,
)
from locus.appss_party import (
    AppssPartyBinding,
    AppssPartyError,
    AppssPartyService,
    AppssPartyStore,
)

CONTEXT = bytes.fromhex("91" * 32)
ADMISSION = "92" * 32
PROOF_KEY = "93" * 32


def holder(index: int) -> AppssHolderBinding:
    return AppssHolderBinding(
        index=index,
        party_id=f"party-{index}",
        service_identity="spki-sha256:" + bytes([index] * 32).hex(),
    )


def request_bytes(
    *,
    holder_id: int,
    operation: str,
    operation_id: str,
    session_id: str,
    nonce: str,
    blinded: bytes,
    omega_digest: str | None,
) -> bytes:
    value = {
        "admission_grant_digest": ADMISSION,
        "blinded_element": blinded.hex(),
        "client_proof_key_digest": PROOF_KEY,
        "context_digest": CONTEXT.hex(),
        "holder_id": holder_id,
        "nonce": nonce,
        "omega_digest": omega_digest,
        "operation": operation,
        "operation_id": operation_id,
        "profile_id": APPSS_PROFILE_2_OF_3,
        "session_id": session_id,
        "suite_id": APPSS_SUITE_ID,
        "version": APPSS_REQUEST_FORMAT,
    }
    return encode_checked(
        value,
        maximum=MAX_REQUEST_BYTES,
        validator=validate_request,
        label="aPPSS request",
    )


def public_mapping(state: native.AppssPublicState) -> dict[str, object]:
    return {
        "commitment": state.commitment.hex(),
        "context_digest": state.context_digest.hex(),
        "k": state.threshold,
        "masked_shares": [
            {"index": index, "value": value.hex()}
            for index, value in state.masked_shares
        ],
        "n": state.parties,
        "omega_digest": state.omega_digest.hex(),
        "oprf_profile": "LOCUS-APPSS-OPRF-RISTRETTO255-SHA512-v1",
        "profile_id": APPSS_PROFILE_2_OF_3,
        "suite_id": APPSS_SUITE_ID,
        "version": APPSS_PUBLIC_STATE_FORMAT,
    }


class AppssPartyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        self.stores = [
            AppssPartyStore(
                root / f"party-{index}.sqlite3",
                AppssPartyBinding(index, CONTEXT),
            )
            for index in range(1, 4)
        ]
        self.services = [AppssPartyService(store) for store in self.stores]

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _initialize(
        self, password: bytes
    ) -> tuple[
        native.AppssPublicState,
        bytes,
        list[tuple[int, bytes]],
        list[bytes],
        list[bytes],
    ]:
        operation_id = "a1" * 32
        masks: list[tuple[int, bytes]] = []
        responses: list[bytes] = []
        requests: list[bytes] = []
        for index, service in enumerate(self.services, start=1):
            instance = instance_id(CONTEXT, holder(index))
            session, blinded = native.appss_blind(oprf_input(instance, password))
            request = request_bytes(
                holder_id=index,
                operation="initialize",
                operation_id=operation_id,
                session_id=bytes([0xA0 + index] * 32).hex(),
                nonce=bytes([0xB0 + index] * 32).hex(),
                blinded=blinded,
                omega_digest=None,
            )
            response_bytes = service.evaluate(request)
            requests.append(request)
            response = canonical_decode(
                response_bytes,
                maximum=4096,
                validator=validate_response,
                label="aPPSS response",
            )
            output = native.appss_finalize(
                session, bytes.fromhex(response["evaluated_element"])
            )
            masks.append((index, native.appss_derive_mask(instance, output)))
            responses.append(response_bytes)
        public, secret = native.appss_initialize_fixture(CONTEXT, password, 2, 3, masks)
        mapping = public_mapping(public)
        transcript = hashlib.sha256(b"".join(responses)).hexdigest()
        for index, service in enumerate(self.services, start=1):
            install = {
                "context_digest": CONTEXT.hex(),
                "holder_id": index,
                "initialization_transcript_digest": transcript,
                "operation_id": operation_id,
                "profile_id": APPSS_PROFILE_2_OF_3,
                "public_state": mapping,
                "suite_id": APPSS_SUITE_ID,
                "version": APPSS_INSTALL_FORMAT,
            }
            install_bytes = encode_checked(
                install,
                maximum=MAX_INSTALL_BYTES,
                validator=validate_install,
                label="aPPSS state install",
            )
            ready = json.loads(service.install(install_bytes))
            self.assertEqual(ready["holder_id"], index)
            self.assertEqual(
                ready["public_state_digest"],
                hashlib.sha256(
                    json.dumps(mapping, sort_keys=True, separators=(",", ":")).encode()
                ).hexdigest(),
            )
        return public, secret, masks, responses, requests

    def test_independent_durable_parties_initialize_and_recover(self) -> None:
        password = b"correct".ljust(32, b"\x00")
        public, expected, _, _, _ = self._initialize(password)
        selected_masks: list[tuple[int, bytes]] = []
        operation_id = "c1" * 32
        for index in (1, 3):
            instance = instance_id(CONTEXT, holder(index))
            session, blinded = native.appss_blind(oprf_input(instance, password))
            request = request_bytes(
                holder_id=index,
                operation="recover",
                operation_id=operation_id,
                session_id="c2" * 32,
                nonce=bytes([0xC0 + index] * 32).hex(),
                blinded=blinded,
                omega_digest=public.omega_digest.hex(),
            )
            response_bytes = self.services[index - 1].evaluate(request)
            response = canonical_decode(
                response_bytes,
                maximum=4096,
                validator=validate_response,
                label="aPPSS response",
            )
            output = native.appss_finalize(
                session, bytes.fromhex(response["evaluated_element"])
            )
            selected_masks.append((index, native.appss_derive_mask(instance, output)))
            restarted = AppssPartyService(self.stores[index - 1])
            self.assertEqual(restarted.evaluate(request), response_bytes)
        self.assertEqual(
            native.appss_recover_fixture(CONTEXT, password, public, selected_masks),
            expected,
        )

        secret_states = [store.load_state()[1] for store in self.stores]  # type: ignore[index]
        self.assertEqual(len(set(secret_states)), 3)
        for index, state_bytes in enumerate(secret_states, start=1):
            state = json.loads(state_bytes)
            self.assertEqual(state["holder_id"], index)
            self.assertNotIn("recovery_secret", state)
            self.assertNotIn("password", state)

    def test_wrong_recipient_suite_omega_replay_and_idempotency_fail_closed(
        self,
    ) -> None:
        public, _, _, _, _ = self._initialize(b"p" * 32)
        instance = instance_id(CONTEXT, holder(1))
        _, blinded = native.appss_blind(oprf_input(instance, b"p" * 32))
        base = request_bytes(
            holder_id=1,
            operation="recover",
            operation_id="d1" * 32,
            session_id="d2" * 32,
            nonce="d3" * 32,
            blinded=blinded,
            omega_digest=public.omega_digest.hex(),
        )
        self.services[0].evaluate(base)
        changed = json.loads(base)
        changed["nonce"] = "d4" * 32
        changed_bytes = json.dumps(
            changed, sort_keys=True, separators=(",", ":")
        ).encode()
        with self.assertRaisesRegex(AppssPartyError, "idempotency"):
            self.services[0].evaluate(changed_bytes)
        wrong_recipient = json.loads(base)
        wrong_recipient["holder_id"] = 2
        with self.assertRaisesRegex(AppssPartyError, "recipient"):
            self.services[0].evaluate(
                json.dumps(
                    wrong_recipient, sort_keys=True, separators=(",", ":")
                ).encode()
            )
        wrong_omega = json.loads(base)
        wrong_omega["operation_id"] = "d5" * 32
        wrong_omega["omega_digest"] = "00" * 32
        with self.assertRaisesRegex(AppssPartyError, "omega"):
            self.services[0].evaluate(
                json.dumps(wrong_omega, sort_keys=True, separators=(",", ":")).encode()
            )
        wrong_suite = json.loads(base)
        wrong_suite["suite_id"] = "LOCUS-TPASS-YI-ZK-RISTRETTO255-v1"
        with self.assertRaisesRegex(AppssPartyError, "invalid aPPSS request"):
            self.services[0].evaluate(
                json.dumps(wrong_suite, sort_keys=True, separators=(",", ":")).encode()
            )

    def test_authorization_is_durable_before_secret_dependent_evaluation(self) -> None:
        operation_id = "e1" * 32
        request = request_bytes(
            holder_id=1,
            operation="initialize",
            operation_id=operation_id,
            session_id="e2" * 32,
            nonce="e3" * 32,
            blinded=b"\x00" * 32,
            omega_digest=None,
        )
        with self.assertRaisesRegex(AppssPartyError, "evaluation rejected"):
            self.services[0].evaluate(request)
        with closing(sqlite3.connect(self.stores[0].path)) as connection:
            row = connection.execute(
                "SELECT authorization_digest, response_bytes FROM appss_requests "
                "WHERE operation_id = ?",
                (operation_id,),
            ).fetchone()
        self.assertEqual(bytes(row[0]), bytes.fromhex(ADMISSION))
        self.assertIsNone(row[1])

    def test_partial_install_never_makes_other_parties_ready(self) -> None:
        operation_id = "f1" * 32
        for index, service in enumerate(self.services, start=1):
            instance = instance_id(CONTEXT, holder(index))
            _, blinded = native.appss_blind(oprf_input(instance, b"z" * 32))
            service.evaluate(
                request_bytes(
                    holder_id=index,
                    operation="initialize",
                    operation_id=operation_id,
                    session_id=bytes([0xF0 + index] * 32).hex(),
                    nonce=bytes([0xD0 + index] * 32).hex(),
                    blinded=blinded,
                    omega_digest=None,
                )
            )
        states = [store.load_state() for store in self.stores]
        self.assertTrue(
            all(state is not None and state[0] == "pending" for state in states)
        )
        with self.assertRaisesRegex(AppssPartyError, "not ready"):
            self.services[1].evaluate(
                request_bytes(
                    holder_id=2,
                    operation="recover",
                    operation_id="f2" * 32,
                    session_id="f3" * 32,
                    nonce="f4" * 32,
                    blinded=b"\x00" * 31 + b"\x01",
                    omega_digest="f5" * 32,
                )
            )

    def test_installed_party_replays_exact_initialization_and_install_only(
        self,
    ) -> None:
        public, _, _, responses, requests = self._initialize(b"r" * 32)
        # The original response is durable and remains retryable after install.
        original_request = requests[0]
        self.assertEqual(
            AppssPartyService(self.stores[0]).evaluate(original_request), responses[0]
        )
        # A changed request under the original operation cannot replace it.
        changed_request = json.loads(original_request)
        changed_request["nonce"] = "ff" * 32
        with self.assertRaisesRegex(AppssPartyError, "idempotency"):
            self.services[0].evaluate(
                json.dumps(
                    changed_request, sort_keys=True, separators=(",", ":")
                ).encode()
            )

        mapping = public_mapping(public)
        transcript = hashlib.sha256(b"".join(responses)).hexdigest()
        install = {
            "context_digest": CONTEXT.hex(),
            "holder_id": 1,
            "initialization_transcript_digest": transcript,
            "operation_id": "a1" * 32,
            "profile_id": APPSS_PROFILE_2_OF_3,
            "public_state": mapping,
            "suite_id": APPSS_SUITE_ID,
            "version": APPSS_INSTALL_FORMAT,
        }
        encoded = encode_checked(
            install,
            maximum=MAX_INSTALL_BYTES,
            validator=validate_install,
            label="aPPSS state install",
        )
        ready = self.services[0].install(encoded)
        self.assertEqual(AppssPartyService(self.stores[0]).install(encoded), ready)
        changed = dict(install)
        changed["initialization_transcript_digest"] = "ff" * 32
        with self.assertRaisesRegex(AppssPartyError, "install retry"):
            self.services[0].install(
                encode_checked(
                    changed,
                    maximum=MAX_INSTALL_BYTES,
                    validator=validate_install,
                    label="aPPSS state install",
                )
            )

    def test_http_claim_recovers_exact_in_progress_request_after_restart(self) -> None:
        key = "aa" * 32
        caller = bytes.fromhex("ab" * 32)
        digest = bytes.fromhex("ac" * 32)
        self.assertIsNone(
            self.stores[0].claim_http_request(
                idempotency_key=key,
                caller_digest=caller,
                route="/v1/test",
                request_digest=digest,
            )
        )
        restarted = AppssPartyStore(self.stores[0].path, self.stores[0].binding)
        self.assertIsNone(
            restarted.claim_http_request(
                idempotency_key=key,
                caller_digest=caller,
                route="/v1/test",
                request_digest=digest,
            )
        )
        response = b'{"ok":true}'
        restarted.complete_http_request(
            idempotency_key=key, status=200, response_bytes=response
        )
        self.assertEqual(
            restarted.claim_http_request(
                idempotency_key=key,
                caller_digest=caller,
                route="/v1/test",
                request_digest=digest,
            ),
            (200, response),
        )
        with self.assertRaisesRegex(AppssPartyError, "binding changed"):
            restarted.claim_http_request(
                idempotency_key=key,
                caller_digest=caller,
                route="/v1/changed",
                request_digest=digest,
            )


if __name__ == "__main__":
    unittest.main()
