# Licensing and redistribution

## Project-authored material

The project owner has confirmed authority to distribute the packaged
project-authored material under the following license split:

- Software, scripts, build metadata, and deployment configuration are licensed
  under the Apache License, Version 2.0 (`Apache-2.0`). The complete license
  text is in `LICENSE`.
- Documentation, aggregate-only experiment records, deterministic processed
  summaries, and generated paper-table inputs are licensed under the Creative
  Commons Attribution 4.0 International License (`CC-BY-4.0`). The scope and
  attribution notice are in `LICENSE-DOCUMENTATION.md`; the designated
  attribution is `LOCUS Authors`.

The integrated repository maintains the manuscript and its LaTeX support
files. They are not part of the anonymous artifact and are not covered by this
license statement.

## Third-party dependencies

Third-party source is not vendored by this artifact. Each dependency retains
its own terms:

| Material | Distribution status |
| --- | --- |
| Python and Rust dependencies | Not vendored. The lockfiles record exact versions and integrity information but do not relicense dependency source. |
| SeaweedFS 4.29 container image | Not vendored. Optional Docker-backed evaluation retrieves the upstream Apache-2.0 image by OCI digest. |
| GitHub Actions used by `.github/workflows/ci.yml` | Referenced by immutable commit digest and retrieved by the hosting platform; each action retains its upstream license. |

If any dependency or container image is redistributed instead of retrieved from
its upstream source, its applicable notices and license terms must be preserved.
