ARG PYTHON_IMAGE=python:3.12.13-slim-bookworm@sha256:d50fb7611f86d04a3b0471b46d7557818d88983fc3136726336b2a4c657aa30b
ARG RUST_IMAGE=rust:1.83.0-bookworm@sha256:a45bf1f5d9af0a23b26703b3500d70af1abff7f984a7abef5a104b42c02a292b

FROM ${PYTHON_IMAGE} AS python-base

FROM ${RUST_IMAGE} AS builder
COPY --from=python-base /usr/local /usr/local
ENV LD_LIBRARY_PATH=/usr/local/lib
WORKDIR /source
RUN python -m pip install --no-cache-dir maturin==1.14.1 uv==0.11.29
COPY pyproject.toml uv.lock README.md ./
COPY prototype/locus ./prototype/locus
COPY tpass-core ./tpass-core
COPY tpass-python ./tpass-python
RUN python -m maturin build --release --locked --out /wheels
RUN uv export --frozen --no-dev --no-editable --no-emit-project \
    --format requirements.txt --output-file /runtime-requirements.txt \
    && python -m pip wheel --no-cache-dir --require-hashes \
    --wheel-dir /wheels --requirement /runtime-requirements.txt

FROM ${PYTHON_IMAGE} AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
RUN groupadd --gid 65532 locus \
    && useradd --uid 65532 --gid 65532 --no-create-home --shell /usr/sbin/nologin locus
COPY --from=builder /wheels /wheels
RUN python -m pip install --no-cache-dir --no-index --find-links=/wheels \
    locus-research==0.1.0 \
    && rm -rf /wheels
LABEL org.opencontainers.image.title="LOCUS reference deployment" \
    org.opencontainers.image.version="0.1.0" \
    org.opencontainers.image.source="anonymous-artifact-pending"
USER 65532:65532
CMD ["python", "-m", "locus.deployment", "--help"]
