#![forbid(unsafe_code)]
//! Narrow Python boundary for the versioned LOCUS TPASS wire protocol.

use locus_appss_core::{
    blind as appss_core_blind, blind_evaluate as appss_core_blind_evaluate,
    derive_mask as appss_core_derive_mask, finalize as appss_core_finalize,
    initialize as appss_core_initialize, recover as appss_core_recover,
    AppssError as CoreAppssError, BlindedElement as CoreAppssBlindedElement,
    ClientBlind as CoreAppssClientBlind, EvaluatedElement as CoreAppssEvaluatedElement,
    MaskedShare as CoreAppssMaskedShare, PublicState as CoreAppssPublicState,
    ServerKey as CoreAppssServerKey,
};
use locus_tpass_core::{
    aggregate_responses as core_aggregate_responses, begin_recovery as core_begin_recovery,
    finish_recovery as core_finish_recovery, password_to_scalar,
    prepare_commitment as core_prepare_commitment, random_secret_exponent, setup as core_setup,
    verify_and_respond as core_verify_and_respond, ClientRequest as CoreClientRequest,
    ClientSession as CoreClientSession, GatewayResponse as CoreGatewayResponse,
    PartyCommitment as CorePartyCommitment, PartyEphemeral as CorePartyEphemeral,
    PartyState as CorePartyState, PublicParameters as CorePublicParameters,
    ServerResponseShare as CoreServerResponseShare, TpassError as CoreTpassError,
};
use pyo3::{
    create_exception,
    exceptions::PyException,
    prelude::*,
    types::{PyBytes, PyModule},
};
use rand_core::OsRng;

create_exception!(_tpass_native, NativeTpassError, PyException);
create_exception!(_tpass_native, NativeAppssError, PyException);

fn native_error(error: CoreTpassError) -> PyErr {
    NativeTpassError::new_err(error.to_string())
}

fn appss_error(error: CoreAppssError) -> PyErr {
    NativeAppssError::new_err(error.to_string())
}

fn py_bytes(py: Python<'_>, value: &[u8]) -> Py<PyBytes> {
    PyBytes::new(py, value).unbind()
}

#[pyclass(module = "locus._tpass_native")]
struct PublicParameters {
    inner: CorePublicParameters,
}

#[pymethods]
impl PublicParameters {
    #[staticmethod]
    fn from_bytes(encoded: &[u8]) -> PyResult<Self> {
        Ok(Self {
            inner: CorePublicParameters::from_bytes(encoded).map_err(native_error)?,
        })
    }

    fn to_bytes(&self, py: Python<'_>) -> Py<PyBytes> {
        py_bytes(py, &self.inner.to_bytes())
    }

    #[getter]
    fn threshold(&self) -> usize {
        self.inner.threshold()
    }

    #[getter]
    fn parties(&self) -> usize {
        self.inner.parties()
    }

    fn __repr__(&self) -> String {
        format!(
            "PublicParameters(protocol='yi-zk-ristretto255-v1', threshold={}, parties={})",
            self.inner.threshold(),
            self.inner.parties()
        )
    }
}

#[pyclass(module = "locus._tpass_native")]
struct PartyState {
    inner: CorePartyState,
}

#[pymethods]
impl PartyState {
    #[staticmethod]
    fn from_secret_bytes(encoded: &[u8]) -> PyResult<Self> {
        Ok(Self {
            inner: CorePartyState::from_secret_bytes(encoded).map_err(native_error)?,
        })
    }

    fn to_secret_bytes(&self, py: Python<'_>) -> Py<PyBytes> {
        py_bytes(py, &self.inner.to_secret_bytes())
    }

    #[getter]
    fn party_id(&self) -> u32 {
        self.inner.party_id()
    }

    fn __repr__(&self) -> String {
        format!(
            "PartyState(party_id={}, secrets='<redacted>')",
            self.party_id()
        )
    }
}

#[pyclass(module = "locus._tpass_native")]
struct ClientSession {
    inner: Option<CoreClientSession>,
}

#[pymethods]
impl ClientSession {
    fn request_bytes(&self, py: Python<'_>) -> PyResult<Py<PyBytes>> {
        let session = self
            .inner
            .as_ref()
            .ok_or_else(|| NativeTpassError::new_err("client session was already consumed"))?;
        Ok(py_bytes(py, &session.request().to_bytes()))
    }

    fn __repr__(&self) -> &'static str {
        "ClientSession(blinder='<redacted>')"
    }
}

#[pyclass(module = "locus._tpass_native")]
struct PartyEphemeral {
    inner: CorePartyEphemeral,
}

#[pyclass(module = "locus._tpass_native")]
struct AppssServerKey {
    inner: CoreAppssServerKey,
}

#[pymethods]
impl AppssServerKey {
    #[staticmethod]
    fn from_secret_bytes(encoded: &[u8]) -> PyResult<Self> {
        Ok(Self {
            inner: CoreAppssServerKey::from_secret_bytes(encoded).map_err(appss_error)?,
        })
    }

    fn to_secret_bytes(&self, py: Python<'_>) -> Py<PyBytes> {
        py_bytes(py, &self.inner.to_secret_bytes())
    }

    #[getter]
    fn holder_id(&self) -> u16 {
        self.inner.holder_id()
    }

    #[getter]
    fn context_digest(&self, py: Python<'_>) -> Py<PyBytes> {
        py_bytes(py, &self.inner.context_digest())
    }

    fn commitment(&self, py: Python<'_>) -> Py<PyBytes> {
        py_bytes(py, &self.inner.commitment())
    }

    fn __repr__(&self) -> String {
        format!(
            "AppssServerKey(holder_id={}, scalar='<redacted>')",
            self.inner.holder_id()
        )
    }
}

#[pyclass(module = "locus._tpass_native")]
struct AppssClientBlind {
    inner: Option<CoreAppssClientBlind>,
}

#[pymethods]
impl AppssClientBlind {
    fn __repr__(&self) -> &'static str {
        "AppssClientBlind(input='<redacted>', blind='<redacted>')"
    }
}

#[pyclass(module = "locus._tpass_native")]
struct AppssPublicState {
    inner: CoreAppssPublicState,
}

#[pymethods]
impl AppssPublicState {
    #[staticmethod]
    fn from_bytes(encoded: &[u8]) -> PyResult<Self> {
        Ok(Self {
            inner: CoreAppssPublicState::from_bytes(encoded).map_err(appss_error)?,
        })
    }

    fn to_bytes(&self, py: Python<'_>) -> Py<PyBytes> {
        py_bytes(py, &self.inner.to_bytes())
    }

    #[getter]
    fn threshold(&self) -> u16 {
        self.inner.threshold()
    }

    #[getter]
    fn parties(&self) -> u16 {
        self.inner.parties()
    }

    #[getter]
    fn context_digest(&self, py: Python<'_>) -> Py<PyBytes> {
        py_bytes(py, &self.inner.context_digest())
    }

    #[getter]
    fn commitment(&self, py: Python<'_>) -> Py<PyBytes> {
        py_bytes(py, &self.inner.commitment())
    }

    #[getter]
    fn omega_digest(&self, py: Python<'_>) -> Py<PyBytes> {
        py_bytes(py, &self.inner.omega_digest())
    }

    #[getter]
    fn masked_shares(&self) -> Vec<(u16, Vec<u8>)> {
        self.inner
            .masked_shares()
            .iter()
            .map(|share| (share.index, share.value.to_vec()))
            .collect()
    }

    fn __repr__(&self) -> String {
        format!(
            "AppssPublicState(profile='2-of-3-v1', threshold={}, parties={})",
            self.inner.threshold(),
            self.inner.parties()
        )
    }
}

fn appss_masks(values: Vec<(u16, Vec<u8>)>) -> PyResult<Vec<CoreAppssMaskedShare>> {
    values
        .into_iter()
        .map(|(index, value)| {
            let value: [u8; 16] = value
                .try_into()
                .map_err(|_| NativeAppssError::new_err("invalid aPPSS mask"))?;
            Ok(CoreAppssMaskedShare { index, value })
        })
        .collect()
}

#[pyfunction]
fn appss_generate_server_key(context_digest: &[u8], holder_id: u16) -> PyResult<AppssServerKey> {
    let context_digest: [u8; 32] = context_digest
        .try_into()
        .map_err(|_| NativeAppssError::new_err("invalid aPPSS context digest"))?;
    Ok(AppssServerKey {
        inner: CoreAppssServerKey::generate(holder_id, context_digest, &mut OsRng)
            .map_err(appss_error)?,
    })
}

#[pyfunction]
fn appss_blind(py: Python<'_>, input: &[u8]) -> PyResult<(AppssClientBlind, Py<PyBytes>)> {
    let (inner, blinded) = appss_core_blind(input, &mut OsRng).map_err(appss_error)?;
    Ok((
        AppssClientBlind { inner: Some(inner) },
        py_bytes(py, &blinded.to_bytes()),
    ))
}

#[pyfunction]
fn appss_blind_evaluate(
    py: Python<'_>,
    key: PyRef<'_, AppssServerKey>,
    context_digest: &[u8],
    blinded_element: &[u8],
) -> PyResult<Py<PyBytes>> {
    let context_digest: [u8; 32] = context_digest
        .try_into()
        .map_err(|_| NativeAppssError::new_err("invalid aPPSS context digest"))?;
    let blinded = CoreAppssBlindedElement::from_bytes(blinded_element).map_err(appss_error)?;
    let evaluated =
        appss_core_blind_evaluate(&key.inner, &context_digest, &blinded).map_err(appss_error)?;
    Ok(py_bytes(py, &evaluated.to_bytes()))
}

#[pyfunction]
fn appss_finalize(
    py: Python<'_>,
    mut session: PyRefMut<'_, AppssClientBlind>,
    evaluated_element: &[u8],
) -> PyResult<Py<PyBytes>> {
    let evaluated =
        CoreAppssEvaluatedElement::from_bytes(evaluated_element).map_err(appss_error)?;
    let session = session
        .inner
        .take()
        .ok_or_else(|| NativeAppssError::new_err("aPPSS blind was already consumed"))?;
    let output = appss_core_finalize(session, &evaluated).map_err(appss_error)?;
    Ok(py_bytes(py, &output))
}

#[pyfunction]
fn appss_derive_mask(
    py: Python<'_>,
    instance_id: &[u8],
    oprf_output: &[u8],
) -> PyResult<Py<PyBytes>> {
    let output: [u8; 64] = oprf_output
        .try_into()
        .map_err(|_| NativeAppssError::new_err("invalid aPPSS OPRF output"))?;
    Ok(py_bytes(py, &appss_core_derive_mask(instance_id, &output)))
}

#[pyfunction]
fn appss_initialize(
    py: Python<'_>,
    context_digest: &[u8],
    password_input: &[u8],
    threshold: u16,
    parties: u16,
    masks: Vec<(u16, Vec<u8>)>,
) -> PyResult<(AppssPublicState, Py<PyBytes>)> {
    let context_digest: [u8; 32] = context_digest
        .try_into()
        .map_err(|_| NativeAppssError::new_err("invalid aPPSS context digest"))?;
    let password_input: [u8; 32] = password_input
        .try_into()
        .map_err(|_| NativeAppssError::new_err("invalid aPPSS password input"))?;
    let masks = appss_masks(masks)?;
    let output = appss_core_initialize(
        context_digest,
        password_input,
        threshold,
        parties,
        &masks,
        &mut OsRng,
    )
    .map_err(appss_error)?;
    let recovery_secret = output.recovery_secret();
    Ok((
        AppssPublicState {
            inner: output.public_state,
        },
        py_bytes(py, &recovery_secret),
    ))
}

#[pyfunction]
fn appss_initialize_fixture(
    py: Python<'_>,
    context_digest: &[u8],
    password_input: &[u8],
    threshold: u16,
    parties: u16,
    masks: Vec<(u16, Vec<u8>)>,
) -> PyResult<(AppssPublicState, Py<PyBytes>)> {
    appss_initialize(
        py,
        context_digest,
        password_input,
        threshold,
        parties,
        masks,
    )
}

#[pyfunction]
fn appss_recover(
    py: Python<'_>,
    context_digest: &[u8],
    password_input: &[u8],
    public_state: PyRef<'_, AppssPublicState>,
    masks: Vec<(u16, Vec<u8>)>,
) -> PyResult<Py<PyBytes>> {
    let context_digest: [u8; 32] = context_digest
        .try_into()
        .map_err(|_| NativeAppssError::new_err("invalid aPPSS context digest"))?;
    let password_input: [u8; 32] = password_input
        .try_into()
        .map_err(|_| NativeAppssError::new_err("invalid aPPSS password input"))?;
    let masks = appss_masks(masks)?;
    let secret = appss_core_recover(context_digest, password_input, &public_state.inner, &masks)
        .map_err(appss_error)?;
    Ok(py_bytes(py, &secret))
}

#[pyfunction]
fn appss_recover_fixture(
    py: Python<'_>,
    context_digest: &[u8],
    password_input: &[u8],
    public_state: PyRef<'_, AppssPublicState>,
    masks: Vec<(u16, Vec<u8>)>,
) -> PyResult<Py<PyBytes>> {
    appss_recover(py, context_digest, password_input, public_state, masks)
}

#[pymethods]
impl PartyEphemeral {
    fn __repr__(&self) -> &'static str {
        "PartyEphemeral(witnesses='<redacted>')"
    }
}

#[pyfunction]
fn setup(
    py: Python<'_>,
    recovery_id: &[u8],
    canonical_recovery_input: &[u8],
    threshold: usize,
    parties: usize,
) -> PyResult<(PublicParameters, Vec<PartyState>, Py<PyBytes>)> {
    let password =
        password_to_scalar(recovery_id, canonical_recovery_input).map_err(native_error)?;
    let secret = random_secret_exponent(&mut OsRng);
    let output = core_setup(
        recovery_id,
        password,
        secret,
        threshold,
        parties,
        &mut OsRng,
    )
    .map_err(native_error)?;
    let parameters = PublicParameters {
        inner: output.public_parameters,
    };
    let states = output
        .party_states
        .into_iter()
        .map(|inner| PartyState { inner })
        .collect();
    Ok((parameters, states, py_bytes(py, &output.group_secret)))
}

#[pyfunction]
fn begin_recovery(
    parameters: PyRef<'_, PublicParameters>,
    recovery_id: &[u8],
    canonical_recovery_input: &[u8],
) -> PyResult<ClientSession> {
    let password =
        password_to_scalar(recovery_id, canonical_recovery_input).map_err(native_error)?;
    let inner = core_begin_recovery(&parameters.inner, recovery_id, password, &mut OsRng)
        .map_err(native_error)?;
    Ok(ClientSession { inner: Some(inner) })
}

#[pyfunction]
fn prepare_commitment(
    py: Python<'_>,
    parameters: PyRef<'_, PublicParameters>,
    request: &[u8],
    selected: Vec<u32>,
    state: PyRef<'_, PartyState>,
) -> PyResult<(Py<PyBytes>, PartyEphemeral)> {
    let request = CoreClientRequest::from_bytes(request).map_err(native_error)?;
    let (commitment, inner) = core_prepare_commitment(
        &parameters.inner,
        &request,
        &selected,
        &state.inner,
        &mut OsRng,
    )
    .map_err(native_error)?;
    Ok((
        py_bytes(py, &commitment.to_bytes()),
        PartyEphemeral { inner },
    ))
}

#[pyfunction]
fn verify_and_respond(
    py: Python<'_>,
    parameters: PyRef<'_, PublicParameters>,
    request: &[u8],
    selected: Vec<u32>,
    state: PyRef<'_, PartyState>,
    ephemeral: PyRef<'_, PartyEphemeral>,
    commitments: Vec<Vec<u8>>,
) -> PyResult<Py<PyBytes>> {
    let request = CoreClientRequest::from_bytes(request).map_err(native_error)?;
    let commitments = commitments
        .iter()
        .map(|encoded| CorePartyCommitment::from_bytes(&parameters.inner, encoded))
        .collect::<Result<Vec<_>, _>>()
        .map_err(native_error)?;
    let response = core_verify_and_respond(
        &parameters.inner,
        &request,
        &selected,
        &state.inner,
        &ephemeral.inner,
        &commitments,
    )
    .map_err(native_error)?;
    Ok(py_bytes(py, &response.to_bytes()))
}

#[pyfunction]
fn aggregate_responses(
    py: Python<'_>,
    parameters: PyRef<'_, PublicParameters>,
    request: &[u8],
    selected: Vec<u32>,
    commitments: Vec<Vec<u8>>,
    responses: Vec<Vec<u8>>,
) -> PyResult<Py<PyBytes>> {
    let request = CoreClientRequest::from_bytes(request).map_err(native_error)?;
    let commitments = commitments
        .iter()
        .map(|encoded| CorePartyCommitment::from_bytes(&parameters.inner, encoded))
        .collect::<Result<Vec<_>, _>>()
        .map_err(native_error)?;
    let responses = responses
        .iter()
        .map(|encoded| CoreServerResponseShare::from_bytes(&parameters.inner, encoded))
        .collect::<Result<Vec<_>, _>>()
        .map_err(native_error)?;
    let response = core_aggregate_responses(
        &parameters.inner,
        &request,
        &selected,
        &commitments,
        &responses,
    )
    .map_err(native_error)?;
    Ok(py_bytes(py, &response.to_bytes()))
}

#[pyfunction]
fn finish_recovery(
    py: Python<'_>,
    parameters: PyRef<'_, PublicParameters>,
    mut session: PyRefMut<'_, ClientSession>,
    gateway_response: &[u8],
) -> PyResult<Py<PyBytes>> {
    let response = CoreGatewayResponse::from_bytes(&parameters.inner, gateway_response)
        .map_err(native_error)?;
    let session = session
        .inner
        .take()
        .ok_or_else(|| NativeTpassError::new_err("client session was already consumed"))?;
    let secret =
        core_finish_recovery(&parameters.inner, session, &response).map_err(native_error)?;
    Ok(py_bytes(py, &secret))
}

#[pymodule]
fn _tpass_native(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add(
        "NativeTpassError",
        module.py().get_type::<NativeTpassError>(),
    )?;
    module.add(
        "NativeAppssError",
        module.py().get_type::<NativeAppssError>(),
    )?;
    module.add_class::<PublicParameters>()?;
    module.add_class::<PartyState>()?;
    module.add_class::<ClientSession>()?;
    module.add_class::<PartyEphemeral>()?;
    module.add_class::<AppssServerKey>()?;
    module.add_class::<AppssClientBlind>()?;
    module.add_class::<AppssPublicState>()?;
    module.add_function(wrap_pyfunction!(setup, module)?)?;
    module.add_function(wrap_pyfunction!(begin_recovery, module)?)?;
    module.add_function(wrap_pyfunction!(prepare_commitment, module)?)?;
    module.add_function(wrap_pyfunction!(verify_and_respond, module)?)?;
    module.add_function(wrap_pyfunction!(aggregate_responses, module)?)?;
    module.add_function(wrap_pyfunction!(finish_recovery, module)?)?;
    module.add_function(wrap_pyfunction!(appss_generate_server_key, module)?)?;
    module.add_function(wrap_pyfunction!(appss_blind, module)?)?;
    module.add_function(wrap_pyfunction!(appss_blind_evaluate, module)?)?;
    module.add_function(wrap_pyfunction!(appss_finalize, module)?)?;
    module.add_function(wrap_pyfunction!(appss_derive_mask, module)?)?;
    module.add_function(wrap_pyfunction!(appss_initialize, module)?)?;
    module.add_function(wrap_pyfunction!(appss_initialize_fixture, module)?)?;
    module.add_function(wrap_pyfunction!(appss_recover, module)?)?;
    module.add_function(wrap_pyfunction!(appss_recover_fixture, module)?)?;
    Ok(())
}
