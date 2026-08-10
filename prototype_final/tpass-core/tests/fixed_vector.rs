use std::{collections::BTreeMap, fmt::Write as _};

use curve25519_dalek::scalar::Scalar;
use locus_tpass_core::{
    aggregate_responses, begin_recovery, finish_recovery, password_to_scalar, prepare_commitment,
    setup, verify_and_respond,
};
use rand_chacha::{rand_core::SeedableRng, ChaCha20Rng};

fn vector() -> BTreeMap<&'static str, &'static str> {
    include_str!("../test-vectors/yi-zk-ristretto255-v1.txt")
        .lines()
        .filter(|line| !line.is_empty() && !line.starts_with('#'))
        .map(|line| line.split_once('=').expect("vector line has key=value"))
        .collect()
}

fn decode_hex(value: &str) -> Vec<u8> {
    assert_eq!(value.len() % 2, 0);
    (0..value.len())
        .step_by(2)
        .map(|offset| u8::from_str_radix(&value[offset..offset + 2], 16).unwrap())
        .collect()
}

fn encode_hex(value: &[u8]) -> String {
    let mut encoded = String::with_capacity(value.len() * 2);
    for byte in value {
        write!(&mut encoded, "{byte:02x}").unwrap();
    }
    encoded
}

#[test]
fn synthetic_protocol_vector_is_stable() {
    let values = vector();
    let recovery_id = decode_hex(values["recovery_id"]);
    let recovery_input = decode_hex(values["recovery_input"]);
    let threshold = values["threshold"].parse::<usize>().unwrap();
    let parties = values["parties"].parse::<usize>().unwrap();
    let selected = values["selected"]
        .split(',')
        .map(|value| value.parse::<u32>().unwrap())
        .collect::<Vec<_>>();

    let password = password_to_scalar(&recovery_id, &recovery_input).unwrap();
    assert_eq!(encode_hex(&password.to_bytes()), values["password"]);

    let setup_seed: [u8; 32] = decode_hex(values["setup_seed"]).try_into().unwrap();
    let mut setup_rng = ChaCha20Rng::from_seed(setup_seed);
    let secret_bytes: [u8; 32] = decode_hex(values["secret_scalar"]).try_into().unwrap();
    let secret = Option::<Scalar>::from(Scalar::from_canonical_bytes(secret_bytes)).unwrap();
    let output = setup(
        &recovery_id,
        password,
        secret,
        threshold,
        parties,
        &mut setup_rng,
    )
    .unwrap();
    assert_eq!(
        encode_hex(&output.public_parameters.to_bytes()),
        values["parameters"]
    );
    assert_eq!(encode_hex(&output.group_secret), values["group_secret"]);
    for state in &output.party_states {
        let key = format!("state_{}", state.party_id());
        assert_eq!(encode_hex(&state.to_secret_bytes()), values[key.as_str()]);
    }

    let recovery_seed: [u8; 32] = decode_hex(values["recovery_seed"]).try_into().unwrap();
    let mut recovery_rng = ChaCha20Rng::from_seed(recovery_seed);
    let session = begin_recovery(
        &output.public_parameters,
        &recovery_id,
        password_to_scalar(&recovery_id, &recovery_input).unwrap(),
        &mut recovery_rng,
    )
    .unwrap();
    let request = session.request().clone();
    assert_eq!(encode_hex(&request.to_bytes()), values["request"]);

    let mut commitments = Vec::new();
    let mut ephemerals = Vec::new();
    for party_id in &selected {
        let (commitment, ephemeral) = prepare_commitment(
            &output.public_parameters,
            &request,
            &selected,
            &output.party_states[(*party_id - 1) as usize],
            &mut recovery_rng,
        )
        .unwrap();
        let key = format!("commitment_{party_id}");
        assert_eq!(encode_hex(&commitment.to_bytes()), values[key.as_str()]);
        commitments.push(commitment);
        ephemerals.push(ephemeral);
    }

    let responses = selected
        .iter()
        .zip(ephemerals.iter())
        .map(|(party_id, ephemeral)| {
            let response = verify_and_respond(
                &output.public_parameters,
                &request,
                &selected,
                &output.party_states[(*party_id - 1) as usize],
                ephemeral,
                &commitments,
            )
            .unwrap();
            let key = format!("response_{party_id}");
            assert_eq!(encode_hex(&response.to_bytes()), values[key.as_str()]);
            response
        })
        .collect::<Vec<_>>();
    let gateway = aggregate_responses(
        &output.public_parameters,
        &request,
        &selected,
        &commitments,
        &responses,
    )
    .unwrap();
    assert_eq!(encode_hex(&gateway.to_bytes()), values["gateway"]);
    assert_eq!(
        finish_recovery(&output.public_parameters, session, &gateway).unwrap(),
        output.group_secret
    );
}
