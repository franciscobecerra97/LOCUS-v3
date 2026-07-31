# LOCUS Artifact Guide

This directory contains the reviewer instructions for the LOCUS research
artifact. The package includes the native Rust/Ristretto255 TPASS
implementation, Python orchestration, isolated same-host deployment, synthetic
fixtures, retained aggregate evidence, deterministic processing, and generated
paper-table inputs.

Read the files in this order:

1. `INSTALL.md` for pinned prerequisites and setup.
2. `EVALUATION.md` for commands and expected observations.
3. `MANIFEST.md` for the inclusion, provenance, and privacy boundary.

Project-authored software and configuration are licensed under Apache License
2.0. Project-authored documentation and aggregate experiment material are
licensed under CC BY 4.0 with `LOCUS Authors` as the designated attribution.

LOCUS is a research prototype. It is not production-ready, independently
audited, or suitable for real keys or personal recovery data. The artifact does
not demonstrate human cue memorability, a rollback-resistant global attempt
bound, public recovery admission, independently administered parties, or
Internet-scale practicality.
