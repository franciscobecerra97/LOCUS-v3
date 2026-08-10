use locus_appss_core::{initialize, MaskedShare};
use rand_chacha::{rand_core::SeedableRng, ChaCha20Rng};
use sha2::{Digest, Sha256};

const VECTOR: &str = include_str!("../test-vectors/appss-2of3-public-v1.txt");

#[test]
fn synthetic_public_state_vector_is_stable() {
    let masks = [
        MaskedShare {
            index: 1,
            value: [0x11; 16],
        },
        MaskedShare {
            index: 2,
            value: [0x22; 16],
        },
        MaskedShare {
            index: 3,
            value: [0x33; 16],
        },
    ];
    let output = initialize(
        [0x24; 32],
        [0x42; 32],
        2,
        3,
        &masks,
        &mut ChaCha20Rng::from_seed([0x81; 32]),
    )
    .unwrap();
    let values = VECTOR
        .lines()
        .map(|line| line.split_once('=').unwrap())
        .collect::<std::collections::BTreeMap<_, _>>();
    assert_eq!(values["profile"], "LOCUS-APPSS-2of3-v1");
    assert_eq!(values["kind"], "public-native-state");
    assert!(!VECTOR.contains("password"));
    assert!(!VECTOR.contains("recovery_secret"));
    assert!(!VECTOR.contains("oprf_key"));
    let encoded = output.public_state.to_bytes();
    assert_eq!(hex(&encoded), values["public_state_hex"]);
    assert_eq!(
        hex(&Sha256::digest(&encoded)),
        values["public_state_sha256"]
    );
}

fn hex(value: &[u8]) -> String {
    const DIGITS: &[u8; 16] = b"0123456789abcdef";
    let mut output = String::with_capacity(value.len() * 2);
    for byte in value {
        output.push(DIGITS[(byte >> 4) as usize] as char);
        output.push(DIGITS[(byte & 0x0f) as usize] as char);
    }
    output
}
