#![forbid(unsafe_code)]
//! Native core for the D017 LOCUS Figure 4 aPPSS profile.
//!
//! This crate is intentionally independent of the frozen Yi TPASS crate. It
//! implements RFC 9497 OPRF mode for ristretto255/SHA-512, GF(2^128) Shamir
//! sharing, share masking, and the aPPSS commitment/recovery relation.

use core::fmt;

use curve25519_dalek::{
    ristretto::{CompressedRistretto, RistrettoPoint},
    scalar::Scalar,
};
use rand_core::{CryptoRng, RngCore};
use sha2::{Digest, Sha256, Sha512};
use subtle::ConstantTimeEq;
use thiserror::Error;
use zeroize::{Zeroize, Zeroizing};

pub const SUITE_ID: &str = "LOCUS-APPSS-2HASHDH-RISTRETTO255-SHA512-GF128-v1";
pub const PROFILE_ID: &str = "LOCUS-APPSS-2of3-v1";
pub const OPRF_PROFILE_ID: &str = "LOCUS-APPSS-OPRF-RISTRETTO255-SHA512-v1";
pub const PASSWORD_INPUT_BYTES: usize = 32;
pub const FIELD_BYTES: usize = 16;
pub const COMMITMENT_BYTES: usize = 16;
pub const RECOVERY_SECRET_BYTES: usize = 16;
pub const OPRF_OUTPUT_BYTES: usize = 64;
pub const ELEMENT_BYTES: usize = 32;
pub const MAX_PARTIES: usize = 255;
pub const MAX_OPRF_INPUT_BYTES: usize = u16::MAX as usize;

const OPRF_CONTEXT: &[u8] = b"OPRFV1-\x00-ristretto255-SHA512";
const HASH_TO_GROUP_PREFIX: &[u8] = b"HashToGroup-";
const FINALIZE_LABEL: &[u8] = b"Finalize";
const SERVER_KEY_MAGIC: &[u8; 4] = b"LAK1";
const PUBLIC_STATE_MAGIC: &[u8; 4] = b"LAP1";
const NATIVE_VERSION: u8 = 1;

#[derive(Debug, Error, Clone, Copy, PartialEq, Eq)]
pub enum AppssError {
    #[error("invalid aPPSS parameter")]
    InvalidParameter,
    #[error("invalid or noncanonical aPPSS encoding")]
    InvalidEncoding,
    #[error("aPPSS input exceeds its resource bound")]
    ResourceLimit,
    #[error("aPPSS object has the wrong context")]
    ContextMismatch,
    #[error("aPPSS object has the wrong threshold or membership")]
    MembershipMismatch,
    #[error("aPPSS reconstruction has insufficient parties")]
    InsufficientParties,
    #[error("aPPSS reconstruction contains a duplicate party")]
    DuplicateParty,
    #[error("aPPSS group identity is forbidden")]
    IdentityElement,
    #[error("aPPSS recovery rejected")]
    RecoveryRejected,
}

#[derive(Clone, Copy, PartialEq, Eq)]
struct Field(u128);

impl Zeroize for Field {
    fn zeroize(&mut self) {
        self.0.zeroize();
    }
}

impl Field {
    const ZERO: Self = Self(0);
    const ONE: Self = Self(1);

    fn from_bytes(value: [u8; FIELD_BYTES]) -> Self {
        Self(u128::from_be_bytes(value))
    }

    fn to_bytes(self) -> [u8; FIELD_BYTES] {
        self.0.to_be_bytes()
    }

    fn add(self, rhs: Self) -> Self {
        Self(self.0 ^ rhs.0)
    }

    fn multiply(self, rhs: Self) -> Self {
        // Polynomial-basis GF(2^128) multiplication modulo
        // x^128 + x^7 + x^2 + x + 1. The low reduction word is 0x87.
        let mut left = self.0;
        let mut right = rhs.0;
        let mut product = 0_u128;
        for _ in 0..128 {
            if right & 1 == 1 {
                product ^= left;
            }
            right >>= 1;
            let carry = left >> 127;
            left <<= 1;
            if carry == 1 {
                left ^= 0x87;
            }
        }
        Self(product)
    }

    fn square(self) -> Self {
        self.multiply(self)
    }

    fn inverse(self) -> Result<Self, AppssError> {
        if self == Self::ZERO {
            return Err(AppssError::InvalidParameter);
        }
        // a^(2^128-2): start at a and repeatedly square/multiply to build
        // exponents 2^(j+1)-1, then perform the final square.
        let mut result = self;
        for _ in 1..127 {
            result = result.square().multiply(self);
        }
        Ok(result.square())
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct MaskedShare {
    pub index: u16,
    pub value: [u8; FIELD_BYTES],
}

pub struct ServerKey {
    holder_id: u16,
    context_digest: [u8; 32],
    scalar: Scalar,
}

impl fmt::Debug for ServerKey {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter
            .debug_struct("ServerKey")
            .field("holder_id", &self.holder_id)
            .field("context_digest", &"<public-binding>")
            .field("scalar", &"<redacted>")
            .finish()
    }
}

impl Drop for ServerKey {
    fn drop(&mut self) {
        self.scalar.zeroize();
    }
}

impl ServerKey {
    pub fn generate<R>(
        holder_id: u16,
        context_digest: [u8; 32],
        rng: &mut R,
    ) -> Result<Self, AppssError>
    where
        R: RngCore + CryptoRng,
    {
        validate_holder(holder_id)?;
        let scalar = random_nonzero_scalar(rng);
        Ok(Self {
            holder_id,
            context_digest,
            scalar,
        })
    }

    pub fn holder_id(&self) -> u16 {
        self.holder_id
    }

    pub fn context_digest(&self) -> [u8; 32] {
        self.context_digest
    }

    pub fn commitment(&self) -> [u8; 32] {
        let point = RistrettoPoint::mul_base(&self.scalar).compress().to_bytes();
        sha256_tuple(&[
            b"LOCUS/aPPSS/oprf-key-commitment/v1",
            &self.context_digest,
            &self.holder_id.to_be_bytes(),
            &point,
        ])
    }

    pub fn to_secret_bytes(&self) -> Vec<u8> {
        let mut output = Vec::with_capacity(71);
        output.extend_from_slice(SERVER_KEY_MAGIC);
        output.push(NATIVE_VERSION);
        output.extend_from_slice(&self.holder_id.to_be_bytes());
        output.extend_from_slice(&self.context_digest);
        output.extend_from_slice(&self.scalar.to_bytes());
        output
    }

    pub fn from_secret_bytes(encoded: &[u8]) -> Result<Self, AppssError> {
        if encoded.len() != 71 || &encoded[..4] != SERVER_KEY_MAGIC || encoded[4] != NATIVE_VERSION
        {
            return Err(AppssError::InvalidEncoding);
        }
        let holder_id = u16::from_be_bytes([encoded[5], encoded[6]]);
        validate_holder(holder_id)?;
        let context_digest = encoded[7..39]
            .try_into()
            .map_err(|_| AppssError::InvalidEncoding)?;
        let scalar_bytes: [u8; 32] = encoded[39..71]
            .try_into()
            .map_err(|_| AppssError::InvalidEncoding)?;
        let scalar = Option::<Scalar>::from(Scalar::from_canonical_bytes(scalar_bytes))
            .filter(|candidate| candidate != &Scalar::ZERO)
            .ok_or(AppssError::InvalidEncoding)?;
        Ok(Self {
            holder_id,
            context_digest,
            scalar,
        })
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct BlindedElement([u8; ELEMENT_BYTES]);

impl BlindedElement {
    pub fn from_bytes(encoded: &[u8]) -> Result<Self, AppssError> {
        decode_element(encoded)?;
        Ok(Self(
            encoded
                .try_into()
                .map_err(|_| AppssError::InvalidEncoding)?,
        ))
    }

    pub fn to_bytes(self) -> [u8; ELEMENT_BYTES] {
        self.0
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct EvaluatedElement([u8; ELEMENT_BYTES]);

impl EvaluatedElement {
    pub fn from_bytes(encoded: &[u8]) -> Result<Self, AppssError> {
        decode_element(encoded)?;
        Ok(Self(
            encoded
                .try_into()
                .map_err(|_| AppssError::InvalidEncoding)?,
        ))
    }

    pub fn to_bytes(self) -> [u8; ELEMENT_BYTES] {
        self.0
    }
}

pub struct ClientBlind {
    input: Zeroizing<Vec<u8>>,
    blind: Scalar,
}

impl fmt::Debug for ClientBlind {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter
            .debug_struct("ClientBlind")
            .field("input", &"<redacted>")
            .field("blind", &"<redacted>")
            .finish()
    }
}

impl Drop for ClientBlind {
    fn drop(&mut self) {
        self.blind.zeroize();
    }
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct PublicState {
    context_digest: [u8; 32],
    threshold: u16,
    parties: u16,
    masked_shares: Vec<MaskedShare>,
    commitment: [u8; COMMITMENT_BYTES],
    omega_digest: [u8; 32],
}

impl PublicState {
    pub fn context_digest(&self) -> [u8; 32] {
        self.context_digest
    }

    pub fn threshold(&self) -> u16 {
        self.threshold
    }

    pub fn parties(&self) -> u16 {
        self.parties
    }

    pub fn masked_shares(&self) -> &[MaskedShare] {
        &self.masked_shares
    }

    pub fn commitment(&self) -> [u8; COMMITMENT_BYTES] {
        self.commitment
    }

    pub fn omega_digest(&self) -> [u8; 32] {
        self.omega_digest
    }

    pub fn to_bytes(&self) -> Vec<u8> {
        let mut output = Vec::with_capacity(91 + self.masked_shares.len() * 18);
        output.extend_from_slice(PUBLIC_STATE_MAGIC);
        output.push(NATIVE_VERSION);
        output.extend_from_slice(&self.context_digest);
        output.extend_from_slice(&self.threshold.to_be_bytes());
        output.extend_from_slice(&self.parties.to_be_bytes());
        output.extend_from_slice(&(self.masked_shares.len() as u16).to_be_bytes());
        for share in &self.masked_shares {
            output.extend_from_slice(&share.index.to_be_bytes());
            output.extend_from_slice(&share.value);
        }
        output.extend_from_slice(&self.commitment);
        output.extend_from_slice(&self.omega_digest);
        output
    }

    pub fn from_bytes(encoded: &[u8]) -> Result<Self, AppssError> {
        if encoded.len() < 91
            || encoded.len() > 91 + MAX_PARTIES * 18
            || &encoded[..4] != PUBLIC_STATE_MAGIC
            || encoded[4] != NATIVE_VERSION
        {
            return Err(AppssError::InvalidEncoding);
        }
        let context_digest = encoded[5..37]
            .try_into()
            .map_err(|_| AppssError::InvalidEncoding)?;
        let threshold = u16::from_be_bytes([encoded[37], encoded[38]]);
        let parties = u16::from_be_bytes([encoded[39], encoded[40]]);
        let count = u16::from_be_bytes([encoded[41], encoded[42]]) as usize;
        validate_topology(threshold, parties)?;
        if count != parties as usize || encoded.len() != 91 + count * 18 {
            return Err(AppssError::InvalidEncoding);
        }
        let mut offset = 43;
        let mut shares = Vec::with_capacity(count);
        for expected in 1..=count {
            let index = u16::from_be_bytes([encoded[offset], encoded[offset + 1]]);
            if index as usize != expected {
                return Err(AppssError::InvalidEncoding);
            }
            let value = encoded[offset + 2..offset + 18]
                .try_into()
                .map_err(|_| AppssError::InvalidEncoding)?;
            shares.push(MaskedShare { index, value });
            offset += 18;
        }
        let commitment = encoded[offset..offset + 16]
            .try_into()
            .map_err(|_| AppssError::InvalidEncoding)?;
        let omega_digest = encoded[offset + 16..offset + 48]
            .try_into()
            .map_err(|_| AppssError::InvalidEncoding)?;
        let state = Self {
            context_digest,
            threshold,
            parties,
            masked_shares: shares,
            commitment,
            omega_digest,
        };
        if state.compute_omega_digest() != omega_digest {
            return Err(AppssError::InvalidEncoding);
        }
        Ok(state)
    }

    fn compute_omega_digest(&self) -> [u8; 32] {
        omega_digest(&self.context_digest, &self.masked_shares, &self.commitment)
    }
}

pub struct SetupOutput {
    pub public_state: PublicState,
    recovery_secret: Zeroizing<[u8; RECOVERY_SECRET_BYTES]>,
}

impl SetupOutput {
    pub fn recovery_secret(&self) -> [u8; RECOVERY_SECRET_BYTES] {
        *self.recovery_secret
    }
}

pub fn blind<R>(input: &[u8], rng: &mut R) -> Result<(ClientBlind, BlindedElement), AppssError>
where
    R: RngCore + CryptoRng,
{
    let input_point = hash_to_group(input)?;
    let blind = random_nonzero_scalar(rng);
    let blinded = (blind * input_point).compress().to_bytes();
    Ok((
        ClientBlind {
            input: Zeroizing::new(input.to_vec()),
            blind,
        },
        BlindedElement(blinded),
    ))
}

pub fn blind_with_scalar(
    input: &[u8],
    blind_bytes: [u8; 32],
) -> Result<(ClientBlind, BlindedElement), AppssError> {
    let blind = Option::<Scalar>::from(Scalar::from_canonical_bytes(blind_bytes))
        .filter(|candidate| candidate != &Scalar::ZERO)
        .ok_or(AppssError::InvalidEncoding)?;
    let input_point = hash_to_group(input)?;
    let blinded = (blind * input_point).compress().to_bytes();
    Ok((
        ClientBlind {
            input: Zeroizing::new(input.to_vec()),
            blind,
        },
        BlindedElement(blinded),
    ))
}

pub fn blind_evaluate(
    key: &ServerKey,
    context_digest: &[u8; 32],
    blinded: &BlindedElement,
) -> Result<EvaluatedElement, AppssError> {
    if &key.context_digest != context_digest {
        return Err(AppssError::ContextMismatch);
    }
    let point = decode_element(&blinded.0)?;
    let evaluated = (key.scalar * point).compress().to_bytes();
    Ok(EvaluatedElement(evaluated))
}

pub fn finalize(
    mut session: ClientBlind,
    evaluated: &EvaluatedElement,
) -> Result<[u8; OPRF_OUTPUT_BYTES], AppssError> {
    let point = decode_element(&evaluated.0)?;
    let unblinded = (session.blind.invert() * point).compress().to_bytes();
    let input_length = u16::try_from(session.input.len()).map_err(|_| AppssError::ResourceLimit)?;
    let mut hash_input = Vec::with_capacity(session.input.len() + 44);
    hash_input.extend_from_slice(&input_length.to_be_bytes());
    hash_input.extend_from_slice(&session.input);
    hash_input.extend_from_slice(&(ELEMENT_BYTES as u16).to_be_bytes());
    hash_input.extend_from_slice(&unblinded);
    hash_input.extend_from_slice(FINALIZE_LABEL);
    let output: [u8; OPRF_OUTPUT_BYTES] = Sha512::digest(hash_input).into();
    session.blind.zeroize();
    Ok(output)
}

pub fn direct_evaluate(
    key: &ServerKey,
    input: &[u8],
) -> Result<[u8; OPRF_OUTPUT_BYTES], AppssError> {
    let point = hash_to_group(input)?;
    let evaluated = (key.scalar * point).compress().to_bytes();
    let input_length = u16::try_from(input.len()).map_err(|_| AppssError::ResourceLimit)?;
    let mut hash_input = Vec::with_capacity(input.len() + 44);
    hash_input.extend_from_slice(&input_length.to_be_bytes());
    hash_input.extend_from_slice(input);
    hash_input.extend_from_slice(&(ELEMENT_BYTES as u16).to_be_bytes());
    hash_input.extend_from_slice(&evaluated);
    hash_input.extend_from_slice(FINALIZE_LABEL);
    Ok(Sha512::digest(hash_input).into())
}

pub fn derive_mask(instance_id: &[u8], oprf_output: &[u8; 64]) -> [u8; 16] {
    let digest = sha256_tuple(&[b"LOCUS/aPPSS/2HashDH/mask/v1", instance_id, oprf_output]);
    digest[..16].try_into().expect("fixed SHA-256 prefix")
}

pub fn initialize<R>(
    context_digest: [u8; 32],
    password_input: [u8; PASSWORD_INPUT_BYTES],
    threshold: u16,
    parties: u16,
    masks: &[MaskedShare],
    rng: &mut R,
) -> Result<SetupOutput, AppssError>
where
    R: RngCore + CryptoRng,
{
    validate_topology(threshold, parties)?;
    validate_indexed_values(masks, parties)?;
    let mut coefficients = Zeroizing::new(Vec::with_capacity(threshold as usize));
    for _ in 0..threshold {
        let mut bytes = [0_u8; FIELD_BYTES];
        rng.fill_bytes(&mut bytes);
        coefficients.push(Field::from_bytes(bytes));
        bytes.zeroize();
    }
    let secret = coefficients[0];
    let mut masked_shares = Vec::with_capacity(parties as usize);
    for mask in masks {
        let share = evaluate_polynomial(&coefficients, Field(mask.index as u128));
        let value = share.add(Field::from_bytes(mask.value)).to_bytes();
        masked_shares.push(MaskedShare {
            index: mask.index,
            value,
        });
    }
    let (commitment, recovery_secret) = commit_and_secret(
        &context_digest,
        &password_input,
        &masked_shares,
        secret.to_bytes(),
    );
    let digest = omega_digest(&context_digest, &masked_shares, &commitment);
    let public_state = PublicState {
        context_digest,
        threshold,
        parties,
        masked_shares,
        commitment,
        omega_digest: digest,
    };
    Ok(SetupOutput {
        public_state,
        recovery_secret: Zeroizing::new(recovery_secret),
    })
}

pub fn recover(
    context_digest: [u8; 32],
    password_input: [u8; PASSWORD_INPUT_BYTES],
    public_state: &PublicState,
    masks: &[MaskedShare],
) -> Result<[u8; RECOVERY_SECRET_BYTES], AppssError> {
    if public_state.context_digest != context_digest {
        return Err(AppssError::ContextMismatch);
    }
    if masks.len() < public_state.threshold as usize {
        return Err(AppssError::InsufficientParties);
    }
    if masks.len() != public_state.threshold as usize {
        return Err(AppssError::MembershipMismatch);
    }
    let mut previous = 0_u16;
    let mut points = Zeroizing::new(Vec::with_capacity(masks.len()));
    for mask in masks {
        if mask.index == previous {
            return Err(AppssError::DuplicateParty);
        }
        if mask.index <= previous || mask.index > public_state.parties {
            return Err(AppssError::MembershipMismatch);
        }
        previous = mask.index;
        let public = public_state
            .masked_shares
            .get(mask.index as usize - 1)
            .ok_or(AppssError::MembershipMismatch)?;
        if public.index != mask.index {
            return Err(AppssError::MembershipMismatch);
        }
        let share = Field::from_bytes(public.value).add(Field::from_bytes(mask.value));
        points.push((Field(mask.index as u128), share));
    }
    let secret = interpolate_at_zero(&points)?;
    let (commitment, recovery_secret) = commit_and_secret(
        &context_digest,
        &password_input,
        &public_state.masked_shares,
        secret.to_bytes(),
    );
    if !bool::from(commitment.ct_eq(&public_state.commitment)) {
        return Err(AppssError::RecoveryRejected);
    }
    Ok(recovery_secret)
}

fn validate_holder(holder_id: u16) -> Result<(), AppssError> {
    if holder_id == 0 || holder_id as usize > MAX_PARTIES {
        return Err(AppssError::InvalidParameter);
    }
    Ok(())
}

fn validate_topology(threshold: u16, parties: u16) -> Result<(), AppssError> {
    if threshold == 0 || parties == 0 || threshold > parties || parties as usize > MAX_PARTIES {
        return Err(AppssError::InvalidParameter);
    }
    Ok(())
}

fn validate_indexed_values(values: &[MaskedShare], parties: u16) -> Result<(), AppssError> {
    if values.len() != parties as usize {
        return Err(AppssError::MembershipMismatch);
    }
    for (position, value) in values.iter().enumerate() {
        if value.index as usize != position + 1 {
            return Err(AppssError::MembershipMismatch);
        }
    }
    Ok(())
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

fn decode_element(encoded: &[u8]) -> Result<RistrettoPoint, AppssError> {
    let bytes: [u8; 32] = encoded
        .try_into()
        .map_err(|_| AppssError::InvalidEncoding)?;
    let point = CompressedRistretto(bytes)
        .decompress()
        .ok_or(AppssError::InvalidEncoding)?;
    if point == RistrettoPoint::default() {
        return Err(AppssError::IdentityElement);
    }
    Ok(point)
}

fn hash_to_group(input: &[u8]) -> Result<RistrettoPoint, AppssError> {
    if input.len() > MAX_OPRF_INPUT_BYTES {
        return Err(AppssError::ResourceLimit);
    }
    let mut dst = Vec::with_capacity(HASH_TO_GROUP_PREFIX.len() + OPRF_CONTEXT.len());
    dst.extend_from_slice(HASH_TO_GROUP_PREFIX);
    dst.extend_from_slice(OPRF_CONTEXT);
    let uniform = expand_message_xmd_sha512(input, &dst)?;
    let point = RistrettoPoint::from_uniform_bytes(&uniform);
    if point == RistrettoPoint::default() {
        return Err(AppssError::IdentityElement);
    }
    Ok(point)
}

fn expand_message_xmd_sha512(message: &[u8], dst: &[u8]) -> Result<[u8; 64], AppssError> {
    if dst.len() > u8::MAX as usize {
        return Err(AppssError::ResourceLimit);
    }
    let mut dst_prime = Vec::with_capacity(dst.len() + 1);
    dst_prime.extend_from_slice(dst);
    dst_prime.push(dst.len() as u8);
    let mut b0_input = Vec::with_capacity(128 + message.len() + 3 + dst_prime.len());
    b0_input.extend_from_slice(&[0_u8; 128]);
    b0_input.extend_from_slice(message);
    b0_input.extend_from_slice(&64_u16.to_be_bytes());
    b0_input.push(0);
    b0_input.extend_from_slice(&dst_prime);
    let b0 = Sha512::digest(b0_input);
    let mut b1_input = Vec::with_capacity(64 + 1 + dst_prime.len());
    b1_input.extend_from_slice(&b0);
    b1_input.push(1);
    b1_input.extend_from_slice(&dst_prime);
    Ok(Sha512::digest(b1_input).into())
}

fn evaluate_polynomial(coefficients: &[Field], x: Field) -> Field {
    coefficients
        .iter()
        .rev()
        .fold(Field::ZERO, |value, coefficient| {
            value.multiply(x).add(*coefficient)
        })
}

fn interpolate_at_zero(points: &[(Field, Field)]) -> Result<Field, AppssError> {
    if points.is_empty() {
        return Err(AppssError::InsufficientParties);
    }
    let mut result = Field::ZERO;
    for (position, (x_i, y_i)) in points.iter().enumerate() {
        let mut numerator = Field::ONE;
        let mut denominator = Field::ONE;
        for (other_position, (x_j, _)) in points.iter().enumerate() {
            if position == other_position {
                continue;
            }
            if x_i == x_j {
                return Err(AppssError::DuplicateParty);
            }
            numerator = numerator.multiply(*x_j);
            denominator = denominator.multiply(x_i.add(*x_j));
        }
        let basis = numerator.multiply(denominator.inverse()?);
        result = result.add(y_i.multiply(basis));
    }
    Ok(result)
}

fn tuple_frame(fields: &[&[u8]]) -> Vec<u8> {
    let mut output = Vec::new();
    output.extend_from_slice(&(fields.len() as u32).to_be_bytes());
    for field in fields {
        output.extend_from_slice(&(field.len() as u32).to_be_bytes());
        output.extend_from_slice(field);
    }
    output
}

fn sha256_tuple(fields: &[&[u8]]) -> [u8; 32] {
    Sha256::digest(tuple_frame(fields)).into()
}

fn canonical_masked_shares(shares: &[MaskedShare]) -> Vec<u8> {
    let mut output = Vec::with_capacity(2 + shares.len() * 18);
    output.extend_from_slice(&(shares.len() as u16).to_be_bytes());
    for share in shares {
        output.extend_from_slice(&share.index.to_be_bytes());
        output.extend_from_slice(&share.value);
    }
    output
}

fn omega_digest(
    context_digest: &[u8; 32],
    shares: &[MaskedShare],
    commitment: &[u8; 16],
) -> [u8; 32] {
    let canonical_e = canonical_masked_shares(shares);
    let canonical_omega = tuple_frame(&[&canonical_e, commitment]);
    sha256_tuple(&[b"LOCUS/aPPSS/omega/v1", context_digest, &canonical_omega])
}

fn commit_and_secret(
    context_digest: &[u8; 32],
    password_input: &[u8; 32],
    shares: &[MaskedShare],
    secret: [u8; 16],
) -> ([u8; 16], [u8; 16]) {
    let canonical_e = canonical_masked_shares(shares);
    let digest = sha256_tuple(&[
        b"LOCUS/aPPSS/commit-secret/v1",
        context_digest,
        password_input,
        &canonical_e,
        &secret,
    ]);
    (
        digest[..16].try_into().expect("fixed SHA-256 prefix"),
        digest[16..].try_into().expect("fixed SHA-256 suffix"),
    )
}

#[cfg(test)]
mod tests {
    use super::*;
    use rand_chacha::{rand_core::SeedableRng, ChaCha20Rng};

    fn rng(byte: u8) -> ChaCha20Rng {
        ChaCha20Rng::from_seed([byte; 32])
    }

    fn sample_masks(parties: u16) -> Vec<MaskedShare> {
        (1..=parties)
            .map(|index| MaskedShare {
                index,
                value: [index as u8; 16],
            })
            .collect()
    }

    #[test]
    fn rfc9497_ristretto255_oprf_vector_one_matches() {
        let key = ServerKey {
            holder_id: 1,
            context_digest: [7; 32],
            scalar: Scalar::from_canonical_bytes([
                0x5e, 0xbc, 0xea, 0x5e, 0xe3, 0x70, 0x23, 0xcc, 0xb9, 0xfc, 0x2d, 0x20, 0x19, 0xf9,
                0xd7, 0x73, 0x7b, 0xe8, 0x55, 0x91, 0xae, 0x86, 0x52, 0xff, 0xa9, 0xef, 0x0f, 0x4d,
                0x37, 0x06, 0x3b, 0x0e,
            ])
            .unwrap(),
        };
        let blind = [
            0x64, 0xd3, 0x7a, 0xed, 0x22, 0xa2, 0x7f, 0x51, 0x91, 0xde, 0x1c, 0x1d, 0x69, 0xfa,
            0xdb, 0x89, 0x9d, 0x88, 0x62, 0xb5, 0x8e, 0xb4, 0x22, 0x00, 0x29, 0xe0, 0x36, 0xec,
            0x4c, 0x1f, 0x67, 0x06,
        ];
        let (session, blinded) = blind_with_scalar(&[0], blind).unwrap();
        assert_eq!(
            blinded.to_bytes(),
            hex32("609a0ae68c15a3cf6903766461307e5c8bb2f95e7e6550e1ffa2dc99e412803c")
        );
        let evaluated = blind_evaluate(&key, &[7; 32], &blinded).unwrap();
        assert_eq!(
            evaluated.to_bytes(),
            hex32("7ec6578ae5120958eb2db1745758ff379e77cb64fe77b0b2d8cc917ea0869c7e")
        );
        let output = finalize(session, &evaluated).unwrap();
        assert_eq!(
            output,
            hex64("527759c3d9366f277d8c6020418d96bb393ba2afb20ff90df23fb7708264e2f3ab9135e3bd69955851de4b1f9fe8a0973396719b7912ba9ee8aa7d0b5e24bcf6")
        );
    }

    #[test]
    fn field_multiplication_and_inverse_are_consistent() {
        let x = Field(0x80000000000000000000000000000000);
        assert!(x.multiply(Field(2)) == Field(0x87));
        for value in [1_u128, 2, 3, 0x1234, u128::MAX] {
            let field = Field(value);
            assert!(field.multiply(field.inverse().unwrap()) == Field::ONE);
        }
    }

    #[test]
    fn every_two_of_three_subset_recovers_and_wrong_password_rejects() {
        let context = [0x11; 32];
        let password = [0x22; 32];
        let masks = sample_masks(3);
        let setup = initialize(context, password, 2, 3, &masks, &mut rng(1)).unwrap();
        for subset in [[0_usize, 1_usize], [0, 2], [1, 2]] {
            let selected = [masks[subset[0]], masks[subset[1]]];
            assert_eq!(
                recover(context, password, &setup.public_state, &selected).unwrap(),
                setup.recovery_secret()
            );
        }
        assert_eq!(
            recover(context, [0x23; 32], &setup.public_state, &masks[..2]),
            Err(AppssError::RecoveryRejected)
        );
    }

    #[test]
    fn bounded_small_topologies_recover_all_threshold_subsets() {
        for (threshold, parties) in [(2_u16, 3_u16), (3, 5)] {
            let masks = sample_masks(parties);
            let setup = initialize(
                [threshold as u8; 32],
                [parties as u8; 32],
                threshold,
                parties,
                &masks,
                &mut rng((threshold + parties) as u8),
            )
            .unwrap();
            for subset in combinations(parties as usize, threshold as usize) {
                let selected: Vec<_> = subset.iter().map(|index| masks[*index]).collect();
                assert_eq!(
                    recover(
                        [threshold as u8; 32],
                        [parties as u8; 32],
                        &setup.public_state,
                        &selected,
                    )
                    .unwrap(),
                    setup.recovery_secret()
                );
            }
        }
    }

    #[test]
    fn strict_state_and_key_codecs_reject_alteration() {
        let context = [0x33; 32];
        let key = ServerKey::generate(1, context, &mut rng(2)).unwrap();
        let encoded = key.to_secret_bytes();
        let decoded = ServerKey::from_secret_bytes(&encoded).unwrap();
        assert_eq!(decoded.holder_id(), 1);
        assert_eq!(decoded.context_digest(), context);
        assert_eq!(decoded.commitment(), key.commitment());
        for malformed in [&encoded[..70], &[encoded.as_slice(), &[0]].concat()] {
            assert!(ServerKey::from_secret_bytes(malformed).is_err());
        }

        let setup = initialize(context, [0x44; 32], 2, 3, &sample_masks(3), &mut rng(3)).unwrap();
        let public = setup.public_state.to_bytes();
        assert_eq!(
            PublicState::from_bytes(&public).unwrap(),
            setup.public_state
        );
        let mut altered = public.clone();
        altered[50] ^= 1;
        assert_eq!(
            PublicState::from_bytes(&altered),
            Err(AppssError::InvalidEncoding)
        );
        assert!(PublicState::from_bytes(&public[..public.len() - 1]).is_err());
        assert!(PublicState::from_bytes(&[public.as_slice(), &[0]].concat()).is_err());
    }

    #[test]
    fn identity_duplicate_range_and_context_fail_closed() {
        assert_eq!(
            BlindedElement::from_bytes(&[0; 32]),
            Err(AppssError::IdentityElement)
        );
        let context = [0x55; 32];
        let masks = sample_masks(3);
        let setup = initialize(context, [0x66; 32], 2, 3, &masks, &mut rng(4)).unwrap();
        assert_eq!(
            recover(context, [0x66; 32], &setup.public_state, &masks[..1]),
            Err(AppssError::InsufficientParties)
        );
        assert_eq!(
            recover(
                context,
                [0x66; 32],
                &setup.public_state,
                &[masks[0], masks[0]],
            ),
            Err(AppssError::DuplicateParty)
        );
        assert_eq!(
            recover([0x56; 32], [0x66; 32], &setup.public_state, &masks[..2]),
            Err(AppssError::ContextMismatch)
        );
    }

    #[test]
    fn secret_debug_representations_are_redacted() {
        let key = ServerKey::generate(1, [8; 32], &mut rng(8)).unwrap();
        let (session, _) = blind(b"input", &mut rng(9)).unwrap();
        assert!(format!("{key:?}").contains("<redacted>"));
        assert!(format!("{session:?}").contains("<redacted>"));
        assert!(!format!("{key:?}").contains(&hex_string(&key.scalar.to_bytes())));
    }

    #[test]
    fn direct_and_oblivious_evaluation_match() {
        let context = [0x77; 32];
        let key = ServerKey::generate(1, context, &mut rng(10)).unwrap();
        let input = b"bounded synthetic OPRF input";
        let direct = direct_evaluate(&key, input).unwrap();
        let (session, blinded) = blind(input, &mut rng(11)).unwrap();
        let evaluated = blind_evaluate(&key, &context, &blinded).unwrap();
        assert_eq!(finalize(session, &evaluated).unwrap(), direct);
    }

    fn combinations(n: usize, k: usize) -> Vec<Vec<usize>> {
        fn visit(
            start: usize,
            n: usize,
            k: usize,
            current: &mut Vec<usize>,
            output: &mut Vec<Vec<usize>>,
        ) {
            if current.len() == k {
                output.push(current.clone());
                return;
            }
            for index in start..n {
                current.push(index);
                visit(index + 1, n, k, current, output);
                current.pop();
            }
        }
        let mut output = Vec::new();
        visit(0, n, k, &mut Vec::new(), &mut output);
        output
    }

    fn hex_string(value: &[u8]) -> String {
        use core::fmt::Write as _;

        let mut output = String::with_capacity(value.len() * 2);
        for byte in value {
            write!(&mut output, "{byte:02x}").unwrap();
        }
        output
    }

    fn hex32(value: &str) -> [u8; 32] {
        let decoded = decode_hex(value);
        decoded.try_into().unwrap()
    }

    fn hex64(value: &str) -> [u8; 64] {
        let decoded = decode_hex(value);
        decoded.try_into().unwrap()
    }

    fn decode_hex(value: &str) -> Vec<u8> {
        value
            .as_bytes()
            .chunks_exact(2)
            .map(|chunk| {
                let high = (chunk[0] as char).to_digit(16).unwrap();
                let low = (chunk[1] as char).to_digit(16).unwrap();
                ((high << 4) | low) as u8
            })
            .collect()
    }
}
