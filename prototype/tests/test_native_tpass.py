import copy
import unittest
from pathlib import Path

from locus import _tpass_native as native
from locus.tpass import NativeTpassBackend, TpassError

RECOVERY_ID = b"locus-python-native-test-epoch-1"
RECOVERY_INPUT = b"three-canonical-python-test-cues"
VECTOR_PATH = (
    Path(__file__).resolve().parents[2]
    / "tpass-core"
    / "test-vectors"
    / "yi-zk-ristretto255-v1.txt"
)


def load_vector() -> dict[str, str]:
    return {
        key: value
        for line in VECTOR_PATH.read_text(encoding="utf-8").splitlines()
        if line and not line.startswith("#")
        for key, value in [line.split("=", maxsplit=1)]
    }


def execute_recovery(recovery_input: bytes) -> tuple[bytes, bytes]:
    parameters, states, expected_secret = native.setup(
        RECOVERY_ID, RECOVERY_INPUT, 3, 5
    )
    parameters = native.PublicParameters.from_bytes(parameters.to_bytes())
    states = [
        native.PartyState.from_secret_bytes(state.to_secret_bytes()) for state in states
    ]
    selected = [1, 3, 5]
    session = native.begin_recovery(parameters, RECOVERY_ID, recovery_input)
    request = session.request_bytes()

    commitments: list[bytes] = []
    ephemerals: list[native.PartyEphemeral] = []
    for party_id in selected:
        commitment, ephemeral = native.prepare_commitment(
            parameters, request, selected, states[party_id - 1]
        )
        commitments.append(commitment)
        ephemerals.append(ephemeral)

    responses = [
        native.verify_and_respond(
            parameters,
            request,
            selected,
            states[party_id - 1],
            ephemeral,
            commitments,
        )
        for party_id, ephemeral in zip(selected, ephemerals, strict=True)
    ]
    gateway = native.aggregate_responses(
        parameters, request, selected, commitments, responses
    )
    recovered = native.finish_recovery(parameters, session, gateway)
    return recovered, expected_secret


class NativeTpassTests(unittest.TestCase):
    def test_cross_language_protocol_succeeds(self) -> None:
        recovered, expected = execute_recovery(RECOVERY_INPUT)
        self.assertEqual(recovered, expected)

    def test_wrong_recovery_input_fails_final_digest(self) -> None:
        with self.assertRaises(native.NativeTpassError):
            execute_recovery(b"wrong-canonical-recovery-input")

    def test_secret_state_rejects_trailing_data(self) -> None:
        _, states, _ = native.setup(RECOVERY_ID, RECOVERY_INPUT, 3, 5)
        encoded = states[0].to_secret_bytes() + b"\x00"
        with self.assertRaises(native.NativeTpassError):
            native.PartyState.from_secret_bytes(encoded)

    def test_frozen_synthetic_party_state_vector_recovers(self) -> None:
        vector = load_vector()
        recovery_id = bytes.fromhex(vector["recovery_id"])
        recovery_input = bytes.fromhex(vector["recovery_input"])
        parameters = native.PublicParameters.from_bytes(
            bytes.fromhex(vector["parameters"])
        )
        selected = [int(value) for value in vector["selected"].split(",")]
        states = {
            party_id: native.PartyState.from_secret_bytes(
                bytes.fromhex(vector[f"state_{party_id}"])
            )
            for party_id in selected
        }

        session = native.begin_recovery(parameters, recovery_id, recovery_input)
        request = session.request_bytes()
        commitments: list[bytes] = []
        ephemerals: list[native.PartyEphemeral] = []
        for party_id in selected:
            commitment, ephemeral = native.prepare_commitment(
                parameters, request, selected, states[party_id]
            )
            commitments.append(commitment)
            ephemerals.append(ephemeral)
        responses = [
            native.verify_and_respond(
                parameters,
                request,
                selected,
                states[party_id],
                ephemeral,
                commitments,
            )
            for party_id, ephemeral in zip(selected, ephemerals, strict=True)
        ]
        gateway = native.aggregate_responses(
            parameters, request, selected, commitments, responses
        )
        self.assertEqual(
            native.finish_recovery(parameters, session, gateway),
            bytes.fromhex(vector["group_secret"]),
        )

    def test_native_phase_boundary_rejects_malformed_messages_and_sets(self) -> None:
        parameters, states, _ = native.setup(RECOVERY_ID, RECOVERY_INPUT, 2, 3)
        selected = [1, 3]

        invalid_session = native.begin_recovery(parameters, RECOVERY_ID, RECOVERY_INPUT)
        invalid_request = bytearray(invalid_session.request_bytes())
        invalid_request[-32:] = bytes(32)
        with self.assertRaises(native.NativeTpassError):
            native.prepare_commitment(
                parameters, bytes(invalid_request), selected, states[0]
            )
        with self.assertRaises(native.NativeTpassError):
            native.prepare_commitment(
                parameters,
                invalid_session.request_bytes(),
                [1, 1],
                states[0],
            )

        session = native.begin_recovery(parameters, RECOVERY_ID, RECOVERY_INPUT)
        request = session.request_bytes()
        commitments: list[bytes] = []
        ephemerals: list[native.PartyEphemeral] = []
        for party_id in selected:
            commitment, ephemeral = native.prepare_commitment(
                parameters, request, selected, states[party_id - 1]
            )
            commitments.append(commitment)
            ephemerals.append(ephemeral)

        malformed_commitments = commitments.copy()
        malformed_commitment = bytearray(malformed_commitments[1])
        malformed_commitment[-32:] = b"\xff" * 32
        malformed_commitments[1] = bytes(malformed_commitment)
        with self.assertRaises(native.NativeTpassError):
            native.verify_and_respond(
                parameters,
                request,
                selected,
                states[0],
                ephemerals[0],
                malformed_commitments,
            )

        responses = [
            native.verify_and_respond(
                parameters,
                request,
                selected,
                states[party_id - 1],
                ephemeral,
                commitments,
            )
            for party_id, ephemeral in zip(selected, ephemerals, strict=True)
        ]
        malformed_responses = responses.copy()
        malformed_response = bytearray(malformed_responses[0])
        malformed_response[-32:] = b"\xff" * 32
        malformed_responses[0] = bytes(malformed_response)
        with self.assertRaises(native.NativeTpassError):
            native.aggregate_responses(
                parameters,
                request,
                selected,
                commitments,
                malformed_responses,
            )

        gateway = bytearray(
            native.aggregate_responses(
                parameters, request, selected, commitments, responses
            )
        )
        gateway[-32:] = b"\xff" * 32
        with self.assertRaises(native.NativeTpassError):
            native.finish_recovery(parameters, session, bytes(gateway))

    def test_python_composition_boundary_requires_canonical_metadata(self) -> None:
        backend = NativeTpassBackend()
        enrollment = backend.setup(
            recovery_id="canonical-boundary-test",
            password=7,
            digest_context="unused-native-context",
            threshold=2,
            parties=3,
        )

        cases: list[tuple[dict, list[dict]]] = []
        string_threshold = copy.deepcopy(enrollment.public_params)
        string_threshold["threshold"] = "2"
        cases.append((string_threshold, copy.deepcopy(enrollment.party_states)))

        uppercase_parameters = copy.deepcopy(enrollment.public_params)
        uppercase_parameters["parameters"] = uppercase_parameters["parameters"].upper()
        cases.append((uppercase_parameters, copy.deepcopy(enrollment.party_states)))

        extra_public_field = copy.deepcopy(enrollment.public_params)
        extra_public_field["unexpected"] = 1
        cases.append((extra_public_field, copy.deepcopy(enrollment.party_states)))

        string_party_id = copy.deepcopy(enrollment.party_states)
        string_party_id[0]["party_id"] = "1"
        cases.append((copy.deepcopy(enrollment.public_params), string_party_id))

        uppercase_state = copy.deepcopy(enrollment.party_states)
        uppercase_state[0]["state"] = uppercase_state[0]["state"].upper()
        cases.append((copy.deepcopy(enrollment.public_params), uppercase_state))

        extra_state_field = copy.deepcopy(enrollment.party_states)
        extra_state_field[0]["unexpected"] = 1
        cases.append((copy.deepcopy(enrollment.public_params), extra_state_field))

        for public_params, party_states in cases:
            with self.subTest(public_params=public_params, party_states=party_states):
                with self.assertRaises(TpassError):
                    backend.recover(
                        recovery_id="canonical-boundary-test",
                        password_attempt=7,
                        digest_context="unused-native-context",
                        public_params=public_params,
                        party_states=party_states,
                    )


if __name__ == "__main__":
    unittest.main()
