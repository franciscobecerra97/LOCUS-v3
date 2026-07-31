#![forbid(unsafe_code)]
//! Narrow Python boundary for the versioned LOCUS TPASS wire protocol.

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

fn native_error(error: CoreTpassError) -> PyErr {
    NativeTpassError::new_err(error.to_string())
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
    module.add_class::<PublicParameters>()?;
    module.add_class::<PartyState>()?;
    module.add_class::<ClientSession>()?;
    module.add_class::<PartyEphemeral>()?;
    module.add_function(wrap_pyfunction!(setup, module)?)?;
    module.add_function(wrap_pyfunction!(begin_recovery, module)?)?;
    module.add_function(wrap_pyfunction!(prepare_commitment, module)?)?;
    module.add_function(wrap_pyfunction!(verify_and_respond, module)?)?;
    module.add_function(wrap_pyfunction!(aggregate_responses, module)?)?;
    module.add_function(wrap_pyfunction!(finish_recovery, module)?)?;
    Ok(())
}
