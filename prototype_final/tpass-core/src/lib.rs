#![forbid(unsafe_code)]
//! Research-grade implementation of Yi et al.'s zero-knowledge-based TPASS
//! construction for LOCUS.
//!
//! The source protocol is expressed multiplicatively. This crate maps it to
//! additive Ristretto notation and uses domain-separated, length-prefixed
//! SHA-512 transcripts. It is not an audited production cryptographic library.

use core::fmt;
use std::collections::BTreeMap;

use curve25519_dalek::{
    constants::RISTRETTO_BASEPOINT_POINT,
    ristretto::{CompressedRistretto, RistrettoPoint},
    scalar::Scalar,
    traits::{Identity, IsIdentity},
};
use rand_core::{CryptoRng, RngCore};
use sha2::{Digest, Sha512};
use thiserror::Error;
use zeroize::Zeroize;

mod wire;

const PROTOCOL_DOMAIN: &[u8] = b"LOCUS-TPASS-YI-ZK-RISTRETTO255-v1";
const MAX_RECOVERY_ID_BYTES: usize = 1024;
/// A protocol-level resource bound for configurations accepted from an
/// attacker-controlled service boundary. LOCUS evaluation profiles use at
/// most nine parties; 255 leaves ample research headroom while preventing a
/// forged public-parameter object from driving multi-billion-element setup or
/// selected-set allocations.
pub const MAX_PARTIES: usize = 255;

/// Errors are deliberately typed for tests and service-side diagnostics. A
/// network service must normalize them before exposing a recovery result.
#[derive(Debug, Error, Clone, PartialEq, Eq)]
pub enum TpassError {
    #[error("invalid threshold parameters")]
    InvalidThreshold,
    #[error("invalid recovery identifier")]
    InvalidRecoveryId,
    #[error("insufficient recovery parties")]
    InsufficientParties,
    #[error("too many recovery parties")]
    TooManyParties,
    #[error("duplicate party identifier")]
    DuplicateParty,
    #[error("party identifier is outside the enrolled range")]
    InvalidPartyId,
    #[error("party is not in the selected recovery set")]
    PartyNotSelected,
    #[error("party state does not match the recovery request")]
    StateMismatch,
    #[error("missing party commitment")]
    MissingCommitment,
    #[error("missing party response")]
    MissingResponse,
    #[error("invalid canonical group encoding")]
    InvalidPoint,
    #[error("identity point is not valid in this proof position")]
    IdentityPoint,
    #[error("invalid canonical scalar encoding")]
    InvalidScalar,
    #[error("invalid or unsupported wire encoding")]
    InvalidEncoding,
    #[error("server proof verification failed")]
    InvalidProof,
    #[error("party response is inconsistent with the verified commitment set")]
    InconsistentResponse,
    #[error("aggregate challenge is zero")]
    ZeroChallenge,
    #[error("password or aggregate response is invalid")]
    InvalidPasswordOrResponse,
}

/// Public parameters for one enrolled TPASS configuration.
#[derive(Clone)]
pub struct PublicParameters {
    threshold: usize,
    parties: usize,
    g2: RistrettoPoint,
}

impl PublicParameters {
    pub fn new(threshold: usize, parties: usize) -> Result<Self, TpassError> {
        if threshold == 0 || parties < threshold {
            return Err(TpassError::InvalidThreshold);
        }
        if parties > MAX_PARTIES {
            return Err(TpassError::TooManyParties);
        }
        let g2 = derive_g2();
        if g2.is_identity() || g2 == RISTRETTO_BASEPOINT_POINT {
            return Err(TpassError::InvalidPoint);
        }
        Ok(Self {
            threshold,
            parties,
            g2,
        })
    }

    pub fn threshold(&self) -> usize {
        self.threshold
    }

    pub fn parties(&self) -> usize {
        self.parties
    }

    pub fn g1_bytes(&self) -> [u8; 32] {
        RISTRETTO_BASEPOINT_POINT.compress().to_bytes()
    }

    pub fn g2_bytes(&self) -> [u8; 32] {
        self.g2.compress().to_bytes()
    }
}

impl fmt::Debug for PublicParameters {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter
            .debug_struct("PublicParameters")
            .field("protocol", &"yi-zk-ristretto255-v1")
            .field("threshold", &self.threshold)
            .field("parties", &self.parties)
            .finish()
    }
}

/// A single party's long-lived TPASS state. Secret shares are private, redacted
/// from `Debug`, and zeroized on drop.
pub struct PartyState {
    recovery_id: Vec<u8>,
    threshold: usize,
    parties: usize,
    party_id: u32,
    password_share: Scalar,
    secret_share: Scalar,
    digest_share: Scalar,
}

impl PartyState {
    pub fn party_id(&self) -> u32 {
        self.party_id
    }
}

impl fmt::Debug for PartyState {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter
            .debug_struct("PartyState")
            .field("party_id", &self.party_id)
            .field("secrets", &"<redacted>")
            .finish()
    }
}

impl Drop for PartyState {
    fn drop(&mut self) {
        self.password_share.zeroize();
        self.secret_share.zeroize();
        self.digest_share.zeroize();
    }
}

pub struct SetupOutput {
    pub public_parameters: PublicParameters,
    pub party_states: Vec<PartyState>,
    pub group_secret: [u8; 32],
}

/// Public client request `A`, bound to one recovery identifier.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ClientRequest {
    recovery_id: Vec<u8>,
    a: [u8; 32],
}

impl ClientRequest {
    pub fn recovery_id(&self) -> &[u8] {
        &self.recovery_id
    }

    pub fn a_bytes(&self) -> [u8; 32] {
        self.a
    }
}

/// Client-only state for one recovery execution. The blinding scalar is never
/// serialized by this crate and is zeroized when the session is consumed.
pub struct ClientSession {
    request: ClientRequest,
    r: Scalar,
}

impl ClientSession {
    pub fn request(&self) -> &ClientRequest {
        &self.request
    }
}

impl fmt::Debug for ClientSession {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter
            .debug_struct("ClientSession")
            .field("request", &self.request)
            .field("r", &"<redacted>")
            .finish()
    }
}

impl Drop for ClientSession {
    fn drop(&mut self) {
        self.r.zeroize();
    }
}

/// Broadcast message `(B_i, C_i, D_i, delta_i)` from one selected party.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct PartyCommitment {
    pub party_id: u32,
    pub b: [u8; 32],
    pub c: [u8; 32],
    pub d: [u8; 32],
    pub delta: [u8; 32],
}

/// Party-local ephemeral witnesses for the response calculation.
pub struct PartyEphemeral {
    party_id: u32,
    selected: Vec<u32>,
    r_i: Scalar,
    c_i: Scalar,
    d_i: Scalar,
    commitment: PartyCommitment,
}

impl fmt::Debug for PartyEphemeral {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter
            .debug_struct("PartyEphemeral")
            .field("party_id", &self.party_id)
            .field("selected", &self.selected)
            .field("witnesses", &"<redacted>")
            .finish()
    }
}

impl Drop for PartyEphemeral {
    fn drop(&mut self) {
        self.r_i.zeroize();
        self.c_i.zeroize();
        self.d_i.zeroize();
    }
}

/// One server's response share. `C` and `D` are repeated as in the source
/// protocol so the gateway can reject inconsistent views before aggregation.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ServerResponseShare {
    pub party_id: u32,
    pub c: [u8; 32],
    pub d: [u8; 32],
    pub e: [u8; 32],
    pub f: [u8; 32],
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct GatewayResponse {
    recovery_id: Vec<u8>,
    selected: Vec<u32>,
    pub c: [u8; 32],
    pub d: [u8; 32],
    pub e: [u8; 32],
    pub f: [u8; 32],
}

/// Domain-separate and hash the canonical client-side recovery input to a
/// TPASS password scalar. Callers remain responsible for not persisting or
/// logging the input or returned scalar.
pub fn password_to_scalar(
    recovery_id: &[u8],
    canonical_recovery_input: &[u8],
) -> Result<Scalar, TpassError> {
    validate_recovery_id(recovery_id)?;
    Ok(hash_to_scalar(
        b"password",
        &[recovery_id, canonical_recovery_input],
    ))
}

/// Generate a nonzero secret exponent for enrollment.
pub fn random_secret_exponent<R>(rng: &mut R) -> Scalar
where
    R: RngCore + CryptoRng,
{
    random_nonzero_scalar(rng)
}

/// Secret-share the password, protected secret exponent, and secret digest.
pub fn setup<R>(
    recovery_id: &[u8],
    mut password: Scalar,
    mut secret_exponent: Scalar,
    threshold: usize,
    parties: usize,
    rng: &mut R,
) -> Result<SetupOutput, TpassError>
where
    R: RngCore + CryptoRng,
{
    validate_recovery_id(recovery_id)?;
    let public_parameters = PublicParameters::new(threshold, parties)?;
    let secret_point = secret_exponent * public_parameters.g2;
    let digest = secret_digest(recovery_id, &secret_point);

    let password_shares = split_secret(password, threshold, parties, rng);
    let secret_shares = split_secret(secret_exponent, threshold, parties, rng);
    let digest_shares = split_secret(digest, threshold, parties, rng);

    let party_states = (0..parties)
        .map(|offset| PartyState {
            recovery_id: recovery_id.to_vec(),
            threshold,
            parties,
            party_id: (offset + 1) as u32,
            password_share: password_shares[offset],
            secret_share: secret_shares[offset],
            digest_share: digest_shares[offset],
        })
        .collect();

    password.zeroize();
    secret_exponent.zeroize();

    Ok(SetupOutput {
        public_parameters,
        party_states,
        group_secret: secret_point.compress().to_bytes(),
    })
}

/// Create the client's blinded password request.
pub fn begin_recovery<R>(
    public_parameters: &PublicParameters,
    recovery_id: &[u8],
    mut password_attempt: Scalar,
    rng: &mut R,
) -> Result<ClientSession, TpassError>
where
    R: RngCore + CryptoRng,
{
    validate_recovery_id(recovery_id)?;
    let r = random_nonzero_scalar(rng);
    let a = r * RISTRETTO_BASEPOINT_POINT - password_attempt * public_parameters.g2;
    password_attempt.zeroize();
    Ok(ClientSession {
        request: ClientRequest {
            recovery_id: recovery_id.to_vec(),
            a: a.compress().to_bytes(),
        },
        r,
    })
}

/// Prepare one party's broadcast proof message for the selected recovery set.
///
/// This is the first operation that emits a message derived from the party's
/// password share. A service must durably install the exact attempt authorization
/// and required freshness evidence before calling it.
pub fn prepare_commitment<R>(
    public_parameters: &PublicParameters,
    request: &ClientRequest,
    selected: &[u32],
    state: &PartyState,
    rng: &mut R,
) -> Result<(PartyCommitment, PartyEphemeral), TpassError>
where
    R: RngCore + CryptoRng,
{
    validate_state(public_parameters, request, state)?;
    let selected = canonical_selected(public_parameters, selected)?;
    if selected.binary_search(&state.party_id).is_err() {
        return Err(TpassError::PartyNotSelected);
    }
    let a_request = decode_point(request.a, false)?;
    let coefficient = lagrange_coefficient(state.party_id, &selected)?;
    let r_i = random_nonzero_scalar(rng);
    let c_i = random_nonzero_scalar(rng);
    let d_i = random_nonzero_scalar(rng);

    let b = r_i * RISTRETTO_BASEPOINT_POINT
        + (coefficient * state.password_share) * public_parameters.g2;
    let c = c_i * RISTRETTO_BASEPOINT_POINT;
    let d = d_i * RISTRETTO_BASEPOINT_POINT;
    let h_i = proof_challenge(request, &selected, state.party_id, &b, &c, &d, &a_request);
    let big_h_i = second_proof_challenge(&h_i);
    let delta = h_i * c_i + big_h_i * d_i;

    let commitment = PartyCommitment {
        party_id: state.party_id,
        b: b.compress().to_bytes(),
        c: c.compress().to_bytes(),
        d: d.compress().to_bytes(),
        delta: delta.to_bytes(),
    };
    let ephemeral = PartyEphemeral {
        party_id: state.party_id,
        selected,
        r_i,
        c_i,
        d_i,
        commitment: commitment.clone(),
    };
    Ok((commitment, ephemeral))
}

/// Verify every selected proof and calculate one party's response share.
///
/// The attempt authorization must already have been installed before
/// `prepare_commitment`; the service must preserve the same authorization and
/// idempotency binding for this second phase.
pub fn verify_and_respond(
    public_parameters: &PublicParameters,
    request: &ClientRequest,
    selected: &[u32],
    state: &PartyState,
    ephemeral: &PartyEphemeral,
    commitments: &[PartyCommitment],
) -> Result<ServerResponseShare, TpassError> {
    validate_state(public_parameters, request, state)?;
    let selected = canonical_selected(public_parameters, selected)?;
    if ephemeral.party_id != state.party_id || ephemeral.selected != selected {
        return Err(TpassError::StateMismatch);
    }
    let own_commitment = commitments
        .iter()
        .find(|commitment| commitment.party_id == state.party_id)
        .ok_or(TpassError::MissingCommitment)?;
    if own_commitment != &ephemeral.commitment {
        return Err(TpassError::StateMismatch);
    }

    let verified = verify_commitments(public_parameters, request, &selected, commitments)?;
    let coefficient = lagrange_coefficient(state.party_id, &selected)?;
    let e = (coefficient * state.secret_share * verified.h) * public_parameters.g2
        - ephemeral.r_i * verified.c
        + ephemeral.c_i * verified.w;
    let f = (coefficient * state.digest_share * verified.h) * public_parameters.g2
        - ephemeral.r_i * verified.d
        + ephemeral.d_i * verified.w;

    Ok(ServerResponseShare {
        party_id: state.party_id,
        c: verified.c.compress().to_bytes(),
        d: verified.d.compress().to_bytes(),
        e: e.compress().to_bytes(),
        f: f.compress().to_bytes(),
    })
}

/// Aggregate exactly one response from every selected party.
pub fn aggregate_responses(
    public_parameters: &PublicParameters,
    request: &ClientRequest,
    selected: &[u32],
    commitments: &[PartyCommitment],
    responses: &[ServerResponseShare],
) -> Result<GatewayResponse, TpassError> {
    let selected = canonical_selected(public_parameters, selected)?;
    let verified = verify_commitments(public_parameters, request, &selected, commitments)?;
    let response_map = unique_responses(public_parameters, responses)?;
    if response_map.len() != selected.len() {
        return Err(TpassError::MissingResponse);
    }

    let expected_c = verified.c.compress().to_bytes();
    let expected_d = verified.d.compress().to_bytes();
    let mut e = RistrettoPoint::identity();
    let mut f = RistrettoPoint::identity();
    for party_id in &selected {
        let response = response_map
            .get(party_id)
            .ok_or(TpassError::MissingResponse)?;
        if response.c != expected_c || response.d != expected_d {
            return Err(TpassError::InconsistentResponse);
        }
        e += decode_point(response.e, true)?;
        f += decode_point(response.f, true)?;
    }

    Ok(GatewayResponse {
        recovery_id: request.recovery_id.clone(),
        selected,
        c: expected_c,
        d: expected_d,
        e: e.compress().to_bytes(),
        f: f.compress().to_bytes(),
    })
}

/// Consume the client session, validate the digest relation, and return the
/// canonical encoded group secret.
pub fn finish_recovery(
    public_parameters: &PublicParameters,
    mut session: ClientSession,
    response: &GatewayResponse,
) -> Result<[u8; 32], TpassError> {
    if response.recovery_id != session.request.recovery_id {
        return Err(TpassError::StateMismatch);
    }
    let selected = canonical_selected(public_parameters, &response.selected)?;
    let a = decode_point(session.request.a, false)?;
    let c = decode_point(response.c, true)?;
    let d = decode_point(response.d, true)?;
    let e = decode_point(response.e, true)?;
    let f = decode_point(response.f, true)?;
    let h = aggregate_challenge(&session.request, &selected, &a, &c, &d);
    if h == Scalar::ZERO {
        return Err(TpassError::ZeroChallenge);
    }
    let h_inverse = h.invert();
    let secret = h_inverse * (e - session.r * c);
    let digest_element = h_inverse * (f - session.r * d);
    let expected_digest =
        secret_digest(&session.request.recovery_id, &secret) * public_parameters.g2;
    session.r.zeroize();
    if digest_element != expected_digest {
        return Err(TpassError::InvalidPasswordOrResponse);
    }
    Ok(secret.compress().to_bytes())
}

struct VerifiedCommitments {
    c: RistrettoPoint,
    d: RistrettoPoint,
    w: RistrettoPoint,
    h: Scalar,
}

fn verify_commitments(
    public_parameters: &PublicParameters,
    request: &ClientRequest,
    selected: &[u32],
    commitments: &[PartyCommitment],
) -> Result<VerifiedCommitments, TpassError> {
    let commitment_map = unique_commitments(public_parameters, commitments)?;
    if commitment_map.len() != selected.len() {
        return Err(TpassError::MissingCommitment);
    }
    let a = decode_point(request.a, false)?;
    let mut aggregate_b = RistrettoPoint::identity();
    let mut aggregate_c = RistrettoPoint::identity();
    let mut aggregate_d = RistrettoPoint::identity();

    for party_id in selected {
        let commitment = commitment_map
            .get(party_id)
            .ok_or(TpassError::MissingCommitment)?;
        let b = decode_point(commitment.b, false)?;
        let c = decode_point(commitment.c, false)?;
        let d = decode_point(commitment.d, false)?;
        let delta = decode_scalar(commitment.delta)?;
        let h_i = proof_challenge(request, selected, *party_id, &b, &c, &d, &a);
        let big_h_i = second_proof_challenge(&h_i);
        if delta * RISTRETTO_BASEPOINT_POINT != h_i * c + big_h_i * d {
            return Err(TpassError::InvalidProof);
        }
        aggregate_b += b;
        aggregate_c += c;
        aggregate_d += d;
    }

    let h = aggregate_challenge(request, selected, &a, &aggregate_c, &aggregate_d);
    if h == Scalar::ZERO {
        return Err(TpassError::ZeroChallenge);
    }
    Ok(VerifiedCommitments {
        c: aggregate_c,
        d: aggregate_d,
        w: a + aggregate_b,
        h,
    })
}

fn unique_commitments<'a>(
    public_parameters: &PublicParameters,
    commitments: &'a [PartyCommitment],
) -> Result<BTreeMap<u32, &'a PartyCommitment>, TpassError> {
    let mut output = BTreeMap::new();
    for commitment in commitments {
        validate_party_id(public_parameters, commitment.party_id)?;
        if output.insert(commitment.party_id, commitment).is_some() {
            return Err(TpassError::DuplicateParty);
        }
    }
    Ok(output)
}

fn unique_responses<'a>(
    public_parameters: &PublicParameters,
    responses: &'a [ServerResponseShare],
) -> Result<BTreeMap<u32, &'a ServerResponseShare>, TpassError> {
    let mut output = BTreeMap::new();
    for response in responses {
        validate_party_id(public_parameters, response.party_id)?;
        if output.insert(response.party_id, response).is_some() {
            return Err(TpassError::DuplicateParty);
        }
    }
    Ok(output)
}

fn validate_state(
    public_parameters: &PublicParameters,
    request: &ClientRequest,
    state: &PartyState,
) -> Result<(), TpassError> {
    validate_recovery_id(&request.recovery_id)?;
    validate_party_id(public_parameters, state.party_id)?;
    if state.recovery_id != request.recovery_id
        || state.threshold != public_parameters.threshold
        || state.parties != public_parameters.parties
    {
        return Err(TpassError::StateMismatch);
    }
    Ok(())
}

fn validate_recovery_id(recovery_id: &[u8]) -> Result<(), TpassError> {
    if recovery_id.is_empty() || recovery_id.len() > MAX_RECOVERY_ID_BYTES {
        return Err(TpassError::InvalidRecoveryId);
    }
    Ok(())
}

fn validate_party_id(
    public_parameters: &PublicParameters,
    party_id: u32,
) -> Result<(), TpassError> {
    if party_id == 0 || party_id as usize > public_parameters.parties {
        return Err(TpassError::InvalidPartyId);
    }
    Ok(())
}

fn canonical_selected(
    public_parameters: &PublicParameters,
    selected: &[u32],
) -> Result<Vec<u32>, TpassError> {
    if selected.len() < public_parameters.threshold {
        return Err(TpassError::InsufficientParties);
    }
    if selected.len() > public_parameters.parties {
        return Err(TpassError::TooManyParties);
    }
    let mut output = selected.to_vec();
    output.sort_unstable();
    for party_id in &output {
        validate_party_id(public_parameters, *party_id)?;
    }
    if output.windows(2).any(|window| window[0] == window[1]) {
        return Err(TpassError::DuplicateParty);
    }
    Ok(output)
}

fn lagrange_coefficient(party_id: u32, selected: &[u32]) -> Result<Scalar, TpassError> {
    if party_id == 0 || !selected.contains(&party_id) {
        return Err(TpassError::PartyNotSelected);
    }
    let i = Scalar::from(party_id as u64);
    let mut numerator = Scalar::ONE;
    let mut denominator = Scalar::ONE;
    for other_id in selected {
        if *other_id == party_id {
            continue;
        }
        let j = Scalar::from(*other_id as u64);
        numerator *= j;
        denominator *= j - i;
    }
    if denominator == Scalar::ZERO {
        return Err(TpassError::DuplicateParty);
    }
    Ok(numerator * denominator.invert())
}

fn split_secret<R>(secret: Scalar, threshold: usize, parties: usize, rng: &mut R) -> Vec<Scalar>
where
    R: RngCore + CryptoRng,
{
    let mut coefficients = Vec::with_capacity(threshold);
    coefficients.push(secret);
    for _ in 1..threshold {
        coefficients.push(random_nonzero_scalar(rng));
    }
    let shares = (1..=parties)
        .map(|party_id| evaluate_polynomial(&coefficients, Scalar::from(party_id as u64)))
        .collect();
    coefficients.zeroize();
    shares
}

fn evaluate_polynomial(coefficients: &[Scalar], x: Scalar) -> Scalar {
    coefficients
        .iter()
        .rev()
        .fold(Scalar::ZERO, |accumulator, coefficient| {
            accumulator * x + coefficient
        })
}

fn random_nonzero_scalar<R>(rng: &mut R) -> Scalar
where
    R: RngCore + CryptoRng,
{
    loop {
        let scalar = Scalar::random(rng);
        if scalar != Scalar::ZERO {
            return scalar;
        }
    }
}

fn derive_g2() -> RistrettoPoint {
    let digest = Sha512::digest([PROTOCOL_DOMAIN, b"/generator-g2"].concat());
    let mut uniform = [0u8; 64];
    uniform.copy_from_slice(&digest);
    RistrettoPoint::from_uniform_bytes(&uniform)
}

fn proof_challenge(
    request: &ClientRequest,
    selected: &[u32],
    party_id: u32,
    b: &RistrettoPoint,
    c: &RistrettoPoint,
    d: &RistrettoPoint,
    a: &RistrettoPoint,
) -> Scalar {
    let selected_bytes = encode_party_ids(selected);
    let party_id_bytes = party_id.to_be_bytes();
    let a_bytes = a.compress().to_bytes();
    let b_bytes = b.compress().to_bytes();
    let c_bytes = c.compress().to_bytes();
    let d_bytes = d.compress().to_bytes();
    hash_to_scalar(
        b"server-proof-challenge",
        &[
            &request.recovery_id,
            &selected_bytes,
            &party_id_bytes,
            &a_bytes,
            &b_bytes,
            &c_bytes,
            &d_bytes,
        ],
    )
}

fn second_proof_challenge(first: &Scalar) -> Scalar {
    let first_bytes = first.to_bytes();
    hash_to_scalar(b"server-proof-second-challenge", &[&first_bytes])
}

fn aggregate_challenge(
    request: &ClientRequest,
    selected: &[u32],
    a: &RistrettoPoint,
    c: &RistrettoPoint,
    d: &RistrettoPoint,
) -> Scalar {
    let selected_bytes = encode_party_ids(selected);
    let a_bytes = a.compress().to_bytes();
    let c_bytes = c.compress().to_bytes();
    let d_bytes = d.compress().to_bytes();
    hash_to_scalar(
        b"aggregate-challenge",
        &[
            &request.recovery_id,
            &selected_bytes,
            &a_bytes,
            &c_bytes,
            &d_bytes,
        ],
    )
}

fn secret_digest(recovery_id: &[u8], secret: &RistrettoPoint) -> Scalar {
    let secret_bytes = secret.compress().to_bytes();
    hash_to_scalar(b"secret-digest", &[recovery_id, &secret_bytes])
}

fn hash_to_scalar(label: &[u8], fields: &[&[u8]]) -> Scalar {
    let mut hash = Sha512::new();
    update_length_prefixed(&mut hash, PROTOCOL_DOMAIN);
    update_length_prefixed(&mut hash, label);
    for field in fields {
        update_length_prefixed(&mut hash, field);
    }
    let digest = hash.finalize();
    let mut wide = [0u8; 64];
    wide.copy_from_slice(&digest);
    Scalar::from_bytes_mod_order_wide(&wide)
}

fn update_length_prefixed(hash: &mut Sha512, bytes: &[u8]) {
    hash.update((bytes.len() as u64).to_be_bytes());
    hash.update(bytes);
}

fn encode_party_ids(selected: &[u32]) -> Vec<u8> {
    let mut output = Vec::with_capacity(4 + selected.len() * 4);
    output.extend_from_slice(&(selected.len() as u32).to_be_bytes());
    for party_id in selected {
        output.extend_from_slice(&party_id.to_be_bytes());
    }
    output
}

fn decode_point(bytes: [u8; 32], allow_identity: bool) -> Result<RistrettoPoint, TpassError> {
    let point = CompressedRistretto(bytes)
        .decompress()
        .ok_or(TpassError::InvalidPoint)?;
    if !allow_identity && point.is_identity() {
        return Err(TpassError::IdentityPoint);
    }
    Ok(point)
}

fn decode_scalar(bytes: [u8; 32]) -> Result<Scalar, TpassError> {
    Option::<Scalar>::from(Scalar::from_canonical_bytes(bytes)).ok_or(TpassError::InvalidScalar)
}

#[cfg(test)]
mod tests {
    use super::*;
    use rand_chacha::{rand_core::SeedableRng, ChaCha20Rng};

    const RECOVERY_ID: &[u8] = b"locus-test-recovery-epoch-1";

    fn seeded_rng(seed_byte: u8) -> ChaCha20Rng {
        ChaCha20Rng::from_seed([seed_byte; 32])
    }

    fn enrollment(seed: u8) -> SetupOutput {
        let mut rng = seeded_rng(seed);
        let password = password_to_scalar(RECOVERY_ID, b"three-canonical-test-cues").unwrap();
        let secret = random_secret_exponent(&mut rng);
        setup(RECOVERY_ID, password, secret, 3, 5, &mut rng).unwrap()
    }

    fn run_recovery(
        output: &SetupOutput,
        selected: &[u32],
        password_input: &[u8],
        seed: u8,
    ) -> Result<[u8; 32], TpassError> {
        let mut rng = seeded_rng(seed);
        let password = password_to_scalar(RECOVERY_ID, password_input).unwrap();
        let session = begin_recovery(&output.public_parameters, RECOVERY_ID, password, &mut rng)?;
        let request = session.request().clone();

        let mut commitments = Vec::new();
        let mut ephemerals = Vec::new();
        for party_id in selected {
            let state = output
                .party_states
                .iter()
                .find(|state| state.party_id() == *party_id)
                .unwrap();
            let (commitment, ephemeral) = prepare_commitment(
                &output.public_parameters,
                &request,
                selected,
                state,
                &mut rng,
            )?;
            commitments.push(commitment);
            ephemerals.push(ephemeral);
        }

        let mut responses = Vec::new();
        for (party_id, ephemeral) in selected.iter().zip(ephemerals.iter()) {
            let state = output
                .party_states
                .iter()
                .find(|state| state.party_id() == *party_id)
                .unwrap();
            responses.push(verify_and_respond(
                &output.public_parameters,
                &request,
                selected,
                state,
                ephemeral,
                &commitments,
            )?);
        }

        let response = aggregate_responses(
            &output.public_parameters,
            &request,
            selected,
            &commitments,
            &responses,
        )?;
        finish_recovery(&output.public_parameters, session, &response)
    }

    #[test]
    fn correct_password_recovers_group_secret() {
        let output = enrollment(1);
        let recovered =
            run_recovery(&output, &[1, 2, 3], b"three-canonical-test-cues", 11).unwrap();
        assert_eq!(recovered, output.group_secret);
    }

    #[test]
    fn arbitrary_threshold_subset_recovers_group_secret() {
        let output = enrollment(2);
        let recovered =
            run_recovery(&output, &[2, 4, 5], b"three-canonical-test-cues", 12).unwrap();
        assert_eq!(recovered, output.group_secret);
    }

    #[test]
    fn selected_order_is_canonicalized() {
        let output = enrollment(3);
        let recovered =
            run_recovery(&output, &[5, 2, 4], b"three-canonical-test-cues", 13).unwrap();
        assert_eq!(recovered, output.group_secret);
    }

    #[test]
    fn threshold_subset_property_holds_across_small_configuration_matrix() {
        let mut recovery_seed = 64_u8;
        // Exhaustive through n=5 keeps this suitable for the default quality
        // gate (129 successful recoveries). Larger target configurations are
        // covered by the Python 2-of-3, 3-of-5, and 5-of-9 matrix.
        for parties in 1..=5 {
            for threshold in 1..=parties {
                let mut rng = seeded_rng((parties * 16 + threshold) as u8);
                let password =
                    password_to_scalar(RECOVERY_ID, b"three-canonical-test-cues").unwrap();
                let secret = random_secret_exponent(&mut rng);
                let output =
                    setup(RECOVERY_ID, password, secret, threshold, parties, &mut rng).unwrap();

                for mask in 1_u32..(1_u32 << parties) {
                    if mask.count_ones() < threshold as u32 {
                        continue;
                    }
                    let mut selected = (1..=parties)
                        .filter(|party_id| mask & (1_u32 << (party_id - 1)) != 0)
                        .map(|party_id| party_id as u32)
                        .collect::<Vec<_>>();
                    if mask % 2 == 0 {
                        selected.reverse();
                    }
                    let recovered = run_recovery(
                        &output,
                        &selected,
                        b"three-canonical-test-cues",
                        recovery_seed,
                    )
                    .unwrap();
                    assert_eq!(
                        recovered, output.group_secret,
                        "failed t={threshold}, n={parties}, selected={selected:?}"
                    );
                    recovery_seed = recovery_seed.wrapping_add(1);
                }
            }
        }
    }

    #[test]
    fn public_parameter_resource_bounds_are_enforced() {
        assert_eq!(
            PublicParameters::new(1, MAX_PARTIES + 1).unwrap_err(),
            TpassError::TooManyParties
        );
        assert_eq!(
            PublicParameters::new(MAX_PARTIES + 1, MAX_PARTIES + 1).unwrap_err(),
            TpassError::TooManyParties
        );
    }

    #[test]
    fn wrong_password_fails_final_digest_relation() {
        let output = enrollment(4);
        let error = run_recovery(&output, &[1, 3, 5], b"wrong-cues", 14).unwrap_err();
        assert_eq!(error, TpassError::InvalidPasswordOrResponse);
    }

    #[test]
    fn insufficient_parties_are_rejected() {
        let output = enrollment(5);
        let mut rng = seeded_rng(15);
        let password = password_to_scalar(RECOVERY_ID, b"three-canonical-test-cues").unwrap();
        let session =
            begin_recovery(&output.public_parameters, RECOVERY_ID, password, &mut rng).unwrap();
        let error = prepare_commitment(
            &output.public_parameters,
            session.request(),
            &[1, 2],
            &output.party_states[0],
            &mut rng,
        )
        .unwrap_err();
        assert_eq!(error, TpassError::InsufficientParties);
    }

    #[test]
    fn duplicate_parties_are_rejected() {
        let output = enrollment(6);
        let mut rng = seeded_rng(16);
        let password = password_to_scalar(RECOVERY_ID, b"three-canonical-test-cues").unwrap();
        let session =
            begin_recovery(&output.public_parameters, RECOVERY_ID, password, &mut rng).unwrap();
        let error = prepare_commitment(
            &output.public_parameters,
            session.request(),
            &[1, 1, 2],
            &output.party_states[0],
            &mut rng,
        )
        .unwrap_err();
        assert_eq!(error, TpassError::DuplicateParty);
    }

    #[test]
    fn tampered_server_proof_is_rejected() {
        let output = enrollment(7);
        let selected = [1, 2, 3];
        let mut rng = seeded_rng(17);
        let password = password_to_scalar(RECOVERY_ID, b"three-canonical-test-cues").unwrap();
        let session =
            begin_recovery(&output.public_parameters, RECOVERY_ID, password, &mut rng).unwrap();
        let request = session.request().clone();
        let mut commitments = Vec::new();
        let mut ephemerals = Vec::new();
        for party_id in selected {
            let state = &output.party_states[(party_id - 1) as usize];
            let (commitment, ephemeral) = prepare_commitment(
                &output.public_parameters,
                &request,
                &selected,
                state,
                &mut rng,
            )
            .unwrap();
            commitments.push(commitment);
            ephemerals.push(ephemeral);
        }
        let delta = decode_scalar(commitments[1].delta).unwrap() + Scalar::ONE;
        commitments[1].delta = delta.to_bytes();

        let error = verify_and_respond(
            &output.public_parameters,
            &request,
            &selected,
            &output.party_states[0],
            &ephemerals[0],
            &commitments,
        )
        .unwrap_err();
        assert_eq!(error, TpassError::InvalidProof);
    }

    #[test]
    fn tampered_gateway_response_is_rejected() {
        let output = enrollment(8);
        let selected = [1, 2, 3];
        let mut rng = seeded_rng(18);
        let password = password_to_scalar(RECOVERY_ID, b"three-canonical-test-cues").unwrap();
        let session =
            begin_recovery(&output.public_parameters, RECOVERY_ID, password, &mut rng).unwrap();
        let request = session.request().clone();
        let mut commitments = Vec::new();
        let mut ephemerals = Vec::new();
        for party_id in selected {
            let state = &output.party_states[(party_id - 1) as usize];
            let (commitment, ephemeral) = prepare_commitment(
                &output.public_parameters,
                &request,
                &selected,
                state,
                &mut rng,
            )
            .unwrap();
            commitments.push(commitment);
            ephemerals.push(ephemeral);
        }
        let responses = selected
            .iter()
            .zip(ephemerals.iter())
            .map(|(party_id, ephemeral)| {
                verify_and_respond(
                    &output.public_parameters,
                    &request,
                    &selected,
                    &output.party_states[(*party_id - 1) as usize],
                    ephemeral,
                    &commitments,
                )
                .unwrap()
            })
            .collect::<Vec<_>>();
        let mut response = aggregate_responses(
            &output.public_parameters,
            &request,
            &selected,
            &commitments,
            &responses,
        )
        .unwrap();
        let tampered_e = decode_point(response.e, true).unwrap() + RISTRETTO_BASEPOINT_POINT;
        response.e = tampered_e.compress().to_bytes();

        let error = finish_recovery(&output.public_parameters, session, &response).unwrap_err();
        assert_eq!(error, TpassError::InvalidPasswordOrResponse);
    }

    #[test]
    fn recovery_identifier_mismatch_is_rejected() {
        let output = enrollment(9);
        let mut rng = seeded_rng(19);
        let other_id = b"different-recovery-epoch";
        let password = password_to_scalar(other_id, b"three-canonical-test-cues").unwrap();
        let session =
            begin_recovery(&output.public_parameters, other_id, password, &mut rng).unwrap();
        let error = prepare_commitment(
            &output.public_parameters,
            session.request(),
            &[1, 2, 3],
            &output.party_states[0],
            &mut rng,
        )
        .unwrap_err();
        assert_eq!(error, TpassError::StateMismatch);
    }

    #[test]
    fn secret_state_debug_output_is_redacted() {
        let output = enrollment(10);
        let rendered = format!("{:?}", output.party_states[0]);
        assert!(rendered.contains("<redacted>"));
        assert!(!rendered.contains("password_share"));
        assert!(!rendered.contains("secret_share"));
        assert!(!rendered.contains("digest_share"));
    }
}
