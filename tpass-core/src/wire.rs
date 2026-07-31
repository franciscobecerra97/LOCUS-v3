//! Versioned canonical encodings for the external TPASS service boundary.
//!
//! Integer fields use unsigned big-endian encoding, variable-length fields are
//! length-prefixed, and points/scalars retain their canonical 32-byte Ristretto
//! encodings. Client sessions and party ephemerals are deliberately excluded:
//! their blinders and witnesses must remain process-local and short-lived.

use super::{
    canonical_selected, decode_point, decode_scalar, validate_party_id, validate_recovery_id,
    ClientRequest, GatewayResponse, PartyCommitment, PartyState, PublicParameters,
    ServerResponseShare, TpassError, MAX_RECOVERY_ID_BYTES,
};

const WIRE_MAGIC: [u8; 8] = *b"LCTPASS\x01";
const PUBLIC_PARAMETERS: u8 = 1;
const PARTY_STATE: u8 = 2;
const CLIENT_REQUEST: u8 = 3;
const PARTY_COMMITMENT: u8 = 4;
const SERVER_RESPONSE: u8 = 5;
const GATEWAY_RESPONSE: u8 = 6;

fn start_encoding(kind: u8) -> Vec<u8> {
    let mut output = Vec::new();
    output.extend_from_slice(&WIRE_MAGIC);
    output.push(kind);
    output
}

fn write_u32(output: &mut Vec<u8>, value: u32) {
    output.extend_from_slice(&value.to_be_bytes());
}

fn write_bytes(output: &mut Vec<u8>, value: &[u8]) {
    write_u32(
        output,
        u32::try_from(value.len()).expect("validated wire field fits in u32"),
    );
    output.extend_from_slice(value);
}

struct Decoder<'a> {
    input: &'a [u8],
    cursor: usize,
}

impl<'a> Decoder<'a> {
    fn new(input: &'a [u8], expected_kind: u8) -> Result<Self, TpassError> {
        let mut decoder = Self { input, cursor: 0 };
        if decoder.read_array::<8>()? != WIRE_MAGIC
            || decoder.read_array::<1>()?[0] != expected_kind
        {
            return Err(TpassError::InvalidEncoding);
        }
        Ok(decoder)
    }

    fn read_array<const N: usize>(&mut self) -> Result<[u8; N], TpassError> {
        let end = self
            .cursor
            .checked_add(N)
            .ok_or(TpassError::InvalidEncoding)?;
        let bytes = self
            .input
            .get(self.cursor..end)
            .ok_or(TpassError::InvalidEncoding)?;
        self.cursor = end;
        bytes.try_into().map_err(|_| TpassError::InvalidEncoding)
    }

    fn read_u32(&mut self) -> Result<u32, TpassError> {
        Ok(u32::from_be_bytes(self.read_array()?))
    }

    fn read_recovery_id(&mut self) -> Result<Vec<u8>, TpassError> {
        let length = self.read_u32()? as usize;
        if length == 0 || length > MAX_RECOVERY_ID_BYTES {
            return Err(TpassError::InvalidRecoveryId);
        }
        let end = self
            .cursor
            .checked_add(length)
            .ok_or(TpassError::InvalidEncoding)?;
        let bytes = self
            .input
            .get(self.cursor..end)
            .ok_or(TpassError::InvalidEncoding)?;
        self.cursor = end;
        Ok(bytes.to_vec())
    }

    fn finish(self) -> Result<(), TpassError> {
        if self.cursor == self.input.len() {
            Ok(())
        } else {
            Err(TpassError::InvalidEncoding)
        }
    }
}

impl PublicParameters {
    /// Encode the fixed group identity and threshold configuration.
    pub fn to_bytes(&self) -> Vec<u8> {
        let mut output = start_encoding(PUBLIC_PARAMETERS);
        write_u32(&mut output, self.threshold as u32);
        write_u32(&mut output, self.parties as u32);
        output.extend_from_slice(&self.g1_bytes());
        output.extend_from_slice(&self.g2_bytes());
        output
    }

    /// Decode and validate the exact protocol version, group, and parameters.
    pub fn from_bytes(encoded: &[u8]) -> Result<Self, TpassError> {
        let mut decoder = Decoder::new(encoded, PUBLIC_PARAMETERS)?;
        let threshold = decoder.read_u32()? as usize;
        let parties = decoder.read_u32()? as usize;
        let encoded_g1 = decoder.read_array::<32>()?;
        let encoded_g2 = decoder.read_array::<32>()?;
        decoder.finish()?;

        let parameters = Self::new(threshold, parties)?;
        if encoded_g1 != parameters.g1_bytes() || encoded_g2 != parameters.g2_bytes() {
            return Err(TpassError::InvalidEncoding);
        }
        Ok(parameters)
    }
}

impl PartyState {
    /// Encode one party's secret long-lived state for confidential storage.
    ///
    /// The returned buffer contains secret shares. Callers must protect it like
    /// the in-memory state, avoid logging it, and erase temporary copies where
    /// their platform permits.
    pub fn to_secret_bytes(&self) -> Vec<u8> {
        let mut output = start_encoding(PARTY_STATE);
        write_bytes(&mut output, &self.recovery_id);
        write_u32(&mut output, self.threshold as u32);
        write_u32(&mut output, self.parties as u32);
        write_u32(&mut output, self.party_id);
        output.extend_from_slice(&self.password_share.to_bytes());
        output.extend_from_slice(&self.secret_share.to_bytes());
        output.extend_from_slice(&self.digest_share.to_bytes());
        output
    }

    /// Restore one party's state after validating every external field.
    pub fn from_secret_bytes(encoded: &[u8]) -> Result<Self, TpassError> {
        let mut decoder = Decoder::new(encoded, PARTY_STATE)?;
        let recovery_id = decoder.read_recovery_id()?;
        let threshold = decoder.read_u32()? as usize;
        let parties = decoder.read_u32()? as usize;
        let party_id = decoder.read_u32()?;
        let password_share = decode_scalar(decoder.read_array()?)?;
        let secret_share = decode_scalar(decoder.read_array()?)?;
        let digest_share = decode_scalar(decoder.read_array()?)?;
        decoder.finish()?;

        validate_recovery_id(&recovery_id)?;
        let parameters = PublicParameters::new(threshold, parties)?;
        validate_party_id(&parameters, party_id)?;
        Ok(Self {
            recovery_id,
            threshold,
            parties,
            party_id,
            password_share,
            secret_share,
            digest_share,
        })
    }
}

impl ClientRequest {
    pub fn to_bytes(&self) -> Vec<u8> {
        let mut output = start_encoding(CLIENT_REQUEST);
        write_bytes(&mut output, &self.recovery_id);
        output.extend_from_slice(&self.a);
        output
    }

    pub fn from_bytes(encoded: &[u8]) -> Result<Self, TpassError> {
        let mut decoder = Decoder::new(encoded, CLIENT_REQUEST)?;
        let recovery_id = decoder.read_recovery_id()?;
        let a = decoder.read_array::<32>()?;
        decoder.finish()?;
        validate_recovery_id(&recovery_id)?;
        decode_point(a, false)?;
        Ok(Self { recovery_id, a })
    }
}

impl PartyCommitment {
    pub fn to_bytes(&self) -> Vec<u8> {
        let mut output = start_encoding(PARTY_COMMITMENT);
        write_u32(&mut output, self.party_id);
        output.extend_from_slice(&self.b);
        output.extend_from_slice(&self.c);
        output.extend_from_slice(&self.d);
        output.extend_from_slice(&self.delta);
        output
    }

    pub fn from_bytes(parameters: &PublicParameters, encoded: &[u8]) -> Result<Self, TpassError> {
        let mut decoder = Decoder::new(encoded, PARTY_COMMITMENT)?;
        let party_id = decoder.read_u32()?;
        let b = decoder.read_array::<32>()?;
        let c = decoder.read_array::<32>()?;
        let d = decoder.read_array::<32>()?;
        let delta = decoder.read_array::<32>()?;
        decoder.finish()?;
        validate_party_id(parameters, party_id)?;
        decode_point(b, false)?;
        decode_point(c, false)?;
        decode_point(d, false)?;
        decode_scalar(delta)?;
        Ok(Self {
            party_id,
            b,
            c,
            d,
            delta,
        })
    }
}

impl ServerResponseShare {
    pub fn to_bytes(&self) -> Vec<u8> {
        let mut output = start_encoding(SERVER_RESPONSE);
        write_u32(&mut output, self.party_id);
        output.extend_from_slice(&self.c);
        output.extend_from_slice(&self.d);
        output.extend_from_slice(&self.e);
        output.extend_from_slice(&self.f);
        output
    }

    pub fn from_bytes(parameters: &PublicParameters, encoded: &[u8]) -> Result<Self, TpassError> {
        let mut decoder = Decoder::new(encoded, SERVER_RESPONSE)?;
        let party_id = decoder.read_u32()?;
        let c = decoder.read_array::<32>()?;
        let d = decoder.read_array::<32>()?;
        let e = decoder.read_array::<32>()?;
        let f = decoder.read_array::<32>()?;
        decoder.finish()?;
        validate_party_id(parameters, party_id)?;
        decode_point(c, true)?;
        decode_point(d, true)?;
        decode_point(e, true)?;
        decode_point(f, true)?;
        Ok(Self {
            party_id,
            c,
            d,
            e,
            f,
        })
    }
}

impl GatewayResponse {
    pub fn to_bytes(&self) -> Vec<u8> {
        let mut output = start_encoding(GATEWAY_RESPONSE);
        write_bytes(&mut output, &self.recovery_id);
        write_u32(&mut output, self.selected.len() as u32);
        for party_id in &self.selected {
            write_u32(&mut output, *party_id);
        }
        output.extend_from_slice(&self.c);
        output.extend_from_slice(&self.d);
        output.extend_from_slice(&self.e);
        output.extend_from_slice(&self.f);
        output
    }

    pub fn from_bytes(parameters: &PublicParameters, encoded: &[u8]) -> Result<Self, TpassError> {
        let mut decoder = Decoder::new(encoded, GATEWAY_RESPONSE)?;
        let recovery_id = decoder.read_recovery_id()?;
        let selected_count = decoder.read_u32()? as usize;
        if selected_count > parameters.parties() {
            return Err(TpassError::InvalidEncoding);
        }
        let mut selected = Vec::with_capacity(selected_count);
        for _ in 0..selected_count {
            selected.push(decoder.read_u32()?);
        }
        let c = decoder.read_array::<32>()?;
        let d = decoder.read_array::<32>()?;
        let e = decoder.read_array::<32>()?;
        let f = decoder.read_array::<32>()?;
        decoder.finish()?;

        validate_recovery_id(&recovery_id)?;
        let canonical = canonical_selected(parameters, &selected)?;
        if canonical != selected {
            return Err(TpassError::InvalidEncoding);
        }
        decode_point(c, true)?;
        decode_point(d, true)?;
        decode_point(e, true)?;
        decode_point(f, true)?;
        Ok(Self {
            recovery_id,
            selected,
            c,
            d,
            e,
            f,
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{
        aggregate_responses, begin_recovery, finish_recovery, password_to_scalar,
        prepare_commitment, random_secret_exponent, setup, verify_and_respond,
    };
    use rand_chacha::{rand_core::SeedableRng, ChaCha20Rng};

    const RECOVERY_ID: &[u8] = b"locus-wire-test-epoch-1";
    const RECOVERY_INPUT: &[u8] = b"three-canonical-wire-test-cues";

    fn seeded_rng(seed: u8) -> ChaCha20Rng {
        ChaCha20Rng::from_seed([seed; 32])
    }

    fn assert_envelope_rejected<F>(encoded: &[u8], decode: F)
    where
        F: Fn(&[u8]) -> Result<(), TpassError>,
    {
        for end in 0..encoded.len() {
            assert!(
                decode(&encoded[..end]).is_err(),
                "accepted truncated encoding of length {end}"
            );
        }

        let mut wrong_kind = encoded.to_vec();
        wrong_kind[8] = if wrong_kind[8] == GATEWAY_RESPONSE {
            PUBLIC_PARAMETERS
        } else {
            GATEWAY_RESPONSE
        };
        assert!(decode(&wrong_kind).is_err());

        let mut trailing = encoded.to_vec();
        trailing.push(0);
        assert!(decode(&trailing).is_err());
    }

    #[test]
    fn public_parameters_reject_wrong_type_and_trailing_data() {
        let parameters = PublicParameters::new(3, 5).unwrap();
        let encoded = parameters.to_bytes();
        let decoded = PublicParameters::from_bytes(&encoded).unwrap();
        assert_eq!(decoded.to_bytes(), encoded);

        let mut wrong_type = encoded.clone();
        wrong_type[8] = PARTY_STATE;
        assert_eq!(
            PublicParameters::from_bytes(&wrong_type).unwrap_err(),
            TpassError::InvalidEncoding
        );

        let mut trailing = encoded;
        trailing.push(0);
        assert_eq!(
            PublicParameters::from_bytes(&trailing).unwrap_err(),
            TpassError::InvalidEncoding
        );
    }

    #[test]
    fn public_parameters_reject_invalid_threshold_bounds_and_generators() {
        let encoded = PublicParameters::new(3, 5).unwrap().to_bytes();

        let mut zero_threshold = encoded.clone();
        zero_threshold[9..13].copy_from_slice(&0_u32.to_be_bytes());
        assert_eq!(
            PublicParameters::from_bytes(&zero_threshold).unwrap_err(),
            TpassError::InvalidThreshold
        );

        let mut excessive_parties = encoded.clone();
        excessive_parties[13..17].copy_from_slice(&256_u32.to_be_bytes());
        assert_eq!(
            PublicParameters::from_bytes(&excessive_parties).unwrap_err(),
            TpassError::TooManyParties
        );

        for point_start in [17, 49] {
            let mut wrong_generator = encoded.clone();
            wrong_generator[point_start] ^= 1;
            assert_eq!(
                PublicParameters::from_bytes(&wrong_generator).unwrap_err(),
                TpassError::InvalidEncoding
            );
        }
    }

    #[test]
    fn party_state_rejects_noncanonical_secret_scalar() {
        let mut rng = seeded_rng(40);
        let password = password_to_scalar(RECOVERY_ID, RECOVERY_INPUT).unwrap();
        let secret = random_secret_exponent(&mut rng);
        let output = setup(RECOVERY_ID, password, secret, 3, 5, &mut rng).unwrap();
        let mut encoded = output.party_states[0].to_secret_bytes();
        let digest_share_start = encoded.len() - 32;
        encoded[digest_share_start..].fill(0xff);
        assert_eq!(
            PartyState::from_secret_bytes(&encoded).unwrap_err(),
            TpassError::InvalidScalar
        );
    }

    #[test]
    fn every_external_decoder_rejects_malformed_fields_and_envelopes() {
        let mut rng = seeded_rng(42);
        let password = password_to_scalar(RECOVERY_ID, RECOVERY_INPUT).unwrap();
        let secret = random_secret_exponent(&mut rng);
        let output = setup(RECOVERY_ID, password, secret, 3, 5, &mut rng).unwrap();
        let parameters = &output.public_parameters;
        let state = &output.party_states[0];
        let session = begin_recovery(
            parameters,
            RECOVERY_ID,
            password_to_scalar(RECOVERY_ID, RECOVERY_INPUT).unwrap(),
            &mut rng,
        )
        .unwrap();
        let request = session.request().clone();
        let selected = [1, 3, 5];

        let mut commitments = Vec::new();
        let mut ephemerals = Vec::new();
        for party_id in selected {
            let selected_state = &output.party_states[(party_id - 1) as usize];
            let (commitment, ephemeral) =
                prepare_commitment(parameters, &request, &selected, selected_state, &mut rng)
                    .unwrap();
            commitments.push(commitment);
            ephemerals.push(ephemeral);
        }
        let responses = selected
            .iter()
            .zip(ephemerals.iter())
            .map(|(party_id, ephemeral)| {
                verify_and_respond(
                    parameters,
                    &request,
                    &selected,
                    &output.party_states[(*party_id - 1) as usize],
                    ephemeral,
                    &commitments,
                )
                .unwrap()
            })
            .collect::<Vec<_>>();
        let gateway =
            aggregate_responses(parameters, &request, &selected, &commitments, &responses).unwrap();

        let public_bytes = parameters.to_bytes();
        assert_envelope_rejected(&public_bytes, |encoded| {
            PublicParameters::from_bytes(encoded).map(|_| ())
        });
        let state_bytes = state.to_secret_bytes();
        assert_envelope_rejected(&state_bytes, |encoded| {
            PartyState::from_secret_bytes(encoded).map(|_| ())
        });
        let request_bytes = request.to_bytes();
        assert_envelope_rejected(&request_bytes, |encoded| {
            ClientRequest::from_bytes(encoded).map(|_| ())
        });
        let commitment_bytes = commitments[0].to_bytes();
        assert_envelope_rejected(&commitment_bytes, |encoded| {
            PartyCommitment::from_bytes(parameters, encoded).map(|_| ())
        });
        let response_bytes = responses[0].to_bytes();
        assert_envelope_rejected(&response_bytes, |encoded| {
            ServerResponseShare::from_bytes(parameters, encoded).map(|_| ())
        });
        let gateway_bytes = gateway.to_bytes();
        assert_envelope_rejected(&gateway_bytes, |encoded| {
            GatewayResponse::from_bytes(parameters, encoded).map(|_| ())
        });

        let recovery_id_length_offset = 9;
        let state_party_id_offset = 9 + 4 + RECOVERY_ID.len() + 4 + 4;
        let state_scalar_offset = state_party_id_offset + 4;
        let request_point_offset = 9 + 4 + RECOVERY_ID.len();
        let message_party_id_offset = 9;
        let commitment_b_offset = message_party_id_offset + 4;
        let commitment_delta_offset = commitment_b_offset + 3 * 32;
        let response_c_offset = message_party_id_offset + 4;
        let gateway_count_offset = 9 + 4 + RECOVERY_ID.len();
        let gateway_selected_offset = gateway_count_offset + 4;
        let gateway_point_offset = gateway_selected_offset + selected.len() * 4;

        let mut oversized_recovery_id = state_bytes.clone();
        oversized_recovery_id[recovery_id_length_offset..recovery_id_length_offset + 4]
            .copy_from_slice(&1025_u32.to_be_bytes());
        assert_eq!(
            PartyState::from_secret_bytes(&oversized_recovery_id).unwrap_err(),
            TpassError::InvalidRecoveryId
        );

        let mut zero_party_state = state_bytes.clone();
        zero_party_state[state_party_id_offset..state_party_id_offset + 4]
            .copy_from_slice(&0_u32.to_be_bytes());
        assert_eq!(
            PartyState::from_secret_bytes(&zero_party_state).unwrap_err(),
            TpassError::InvalidPartyId
        );
        for scalar_offset in [
            state_scalar_offset,
            state_scalar_offset + 32,
            state_scalar_offset + 64,
        ] {
            let mut noncanonical_scalar = state_bytes.clone();
            noncanonical_scalar[scalar_offset..scalar_offset + 32].fill(0xff);
            assert_eq!(
                PartyState::from_secret_bytes(&noncanonical_scalar).unwrap_err(),
                TpassError::InvalidScalar
            );
        }

        let mut empty_request_id = request_bytes.clone();
        empty_request_id[recovery_id_length_offset..recovery_id_length_offset + 4]
            .copy_from_slice(&0_u32.to_be_bytes());
        assert_eq!(
            ClientRequest::from_bytes(&empty_request_id).unwrap_err(),
            TpassError::InvalidRecoveryId
        );
        for invalid_point in [[0_u8; 32], [0xff_u8; 32]] {
            let mut invalid_request = request_bytes.clone();
            invalid_request[request_point_offset..request_point_offset + 32]
                .copy_from_slice(&invalid_point);
            assert!(ClientRequest::from_bytes(&invalid_request).is_err());
        }

        let mut zero_commitment_party = commitment_bytes.clone();
        zero_commitment_party[message_party_id_offset..message_party_id_offset + 4]
            .copy_from_slice(&0_u32.to_be_bytes());
        assert_eq!(
            PartyCommitment::from_bytes(parameters, &zero_commitment_party).unwrap_err(),
            TpassError::InvalidPartyId
        );
        for point_offset in [
            commitment_b_offset,
            commitment_b_offset + 32,
            commitment_b_offset + 64,
        ] {
            let mut identity_commitment = commitment_bytes.clone();
            identity_commitment[point_offset..point_offset + 32].fill(0);
            assert_eq!(
                PartyCommitment::from_bytes(parameters, &identity_commitment).unwrap_err(),
                TpassError::IdentityPoint
            );
        }
        let mut noncanonical_delta = commitment_bytes.clone();
        noncanonical_delta[commitment_delta_offset..commitment_delta_offset + 32].fill(0xff);
        assert_eq!(
            PartyCommitment::from_bytes(parameters, &noncanonical_delta).unwrap_err(),
            TpassError::InvalidScalar
        );

        let mut zero_response_party = response_bytes.clone();
        zero_response_party[message_party_id_offset..message_party_id_offset + 4]
            .copy_from_slice(&0_u32.to_be_bytes());
        assert_eq!(
            ServerResponseShare::from_bytes(parameters, &zero_response_party).unwrap_err(),
            TpassError::InvalidPartyId
        );
        for point_offset in (0..4).map(|index| response_c_offset + index * 32) {
            let mut invalid_response = response_bytes.clone();
            invalid_response[point_offset..point_offset + 32].fill(0xff);
            assert_eq!(
                ServerResponseShare::from_bytes(parameters, &invalid_response).unwrap_err(),
                TpassError::InvalidPoint
            );
        }

        let mut insufficient_gateway = gateway_bytes.clone();
        insufficient_gateway[gateway_count_offset..gateway_count_offset + 4]
            .copy_from_slice(&0_u32.to_be_bytes());
        assert!(GatewayResponse::from_bytes(parameters, &insufficient_gateway).is_err());

        let mut noncanonical_gateway = gateway_bytes.clone();
        noncanonical_gateway[gateway_selected_offset..gateway_selected_offset + 4]
            .copy_from_slice(&3_u32.to_be_bytes());
        noncanonical_gateway[gateway_selected_offset + 4..gateway_selected_offset + 8]
            .copy_from_slice(&1_u32.to_be_bytes());
        assert_eq!(
            GatewayResponse::from_bytes(parameters, &noncanonical_gateway).unwrap_err(),
            TpassError::InvalidEncoding
        );

        let mut duplicate_gateway = gateway_bytes.clone();
        duplicate_gateway[gateway_selected_offset + 4..gateway_selected_offset + 8]
            .copy_from_slice(&1_u32.to_be_bytes());
        assert_eq!(
            GatewayResponse::from_bytes(parameters, &duplicate_gateway).unwrap_err(),
            TpassError::DuplicateParty
        );

        for point_offset in (0..4).map(|index| gateway_point_offset + index * 32) {
            let mut invalid_gateway = gateway_bytes.clone();
            invalid_gateway[point_offset..point_offset + 32].fill(0xff);
            assert_eq!(
                GatewayResponse::from_bytes(parameters, &invalid_gateway).unwrap_err(),
                TpassError::InvalidPoint
            );
        }
    }

    #[test]
    fn complete_protocol_round_trips_across_wire_boundary() {
        let mut rng = seeded_rng(41);
        let password = password_to_scalar(RECOVERY_ID, RECOVERY_INPUT).unwrap();
        let secret = random_secret_exponent(&mut rng);
        let output = setup(RECOVERY_ID, password, secret, 3, 5, &mut rng).unwrap();
        let expected_secret = output.group_secret;

        let parameters =
            PublicParameters::from_bytes(&output.public_parameters.to_bytes()).unwrap();
        let states = output
            .party_states
            .iter()
            .map(|state| PartyState::from_secret_bytes(&state.to_secret_bytes()).unwrap())
            .collect::<Vec<_>>();

        let password_attempt = password_to_scalar(RECOVERY_ID, RECOVERY_INPUT).unwrap();
        let session = begin_recovery(&parameters, RECOVERY_ID, password_attempt, &mut rng).unwrap();
        let request = ClientRequest::from_bytes(&session.request().to_bytes()).unwrap();
        let selected = [1, 3, 5];

        let mut commitments = Vec::new();
        let mut ephemerals = Vec::new();
        for party_id in selected {
            let state = &states[(party_id - 1) as usize];
            let (commitment, ephemeral) =
                prepare_commitment(&parameters, &request, &selected, state, &mut rng).unwrap();
            commitments
                .push(PartyCommitment::from_bytes(&parameters, &commitment.to_bytes()).unwrap());
            ephemerals.push(ephemeral);
        }

        let responses = selected
            .iter()
            .zip(ephemerals.iter())
            .map(|(party_id, ephemeral)| {
                let response = verify_and_respond(
                    &parameters,
                    &request,
                    &selected,
                    &states[(*party_id - 1) as usize],
                    ephemeral,
                    &commitments,
                )
                .unwrap();
                ServerResponseShare::from_bytes(&parameters, &response.to_bytes()).unwrap()
            })
            .collect::<Vec<_>>();

        let gateway =
            aggregate_responses(&parameters, &request, &selected, &commitments, &responses)
                .unwrap();
        let gateway = GatewayResponse::from_bytes(&parameters, &gateway.to_bytes()).unwrap();
        let recovered = finish_recovery(&parameters, session, &gateway).unwrap();
        assert_eq!(recovered, expected_secret);
    }
}
