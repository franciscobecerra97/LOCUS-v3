# Artifact Release Checklist

Release authorization: APPROVED

Authorization record (2026-07-28): the project owner confirmed authority to
distribute the project-authored material and approved Apache License 2.0 for
software and configuration plus Creative Commons Attribution 4.0 International
for documentation and aggregate experiment material. `LOCUS Authors` is the
designated attribution for the anonymous artifact.

- [x] Confirm authority to distribute project-authored software,
  documentation, and aggregate experiment material.
- [x] Select and record software and documentation license terms, or explicitly
  authorize reviewer-only distribution without a public reuse grant.
- [x] Confirm that the artifact excludes the partial ACM LaTeX vendoring,
  unverified `popets.sty`, `cc-by-4.pdf`, and local `extra/` material.
- [x] Run `uv run --frozen python tasks.py artifact-package --check`.
- [x] Commit the artifact source state and require a clean working tree.
- [x] Build a deterministic archive and a byte-identical repeat candidate.
- [x] Inspect the archive member list, generated manifest, and extracted files.
- [x] Confirm there is no `.git`, author name/email, personal repository URL,
  local user path, credential, real cue/identity data, or prohibited output.
- [ ] Keep the personal development repository non-public and unlinked during
  double-blind review.
- [ ] Reproduce the archive on clean Linux and Windows/CI.
- [ ] Complete the Docker-backed smoke/full profile from a clean host.
- [ ] Obtain an unfamiliar-reviewer smoke result.

Candidate inspection record (2026-07-28): clean development commit `0a9caa2`
produced a 183-file archive and a byte-identical repeat with SHA-256
`9fbdb5ef86f05d3ed41216e57feded9835c4ef9cb7837b5d6a77819f21ea3cdb`.
Every manifest size/digest matched the extracted file, the three controlling
license files were present, no forbidden path was present, and the extracted
anonymity scan passed. The final archive rebuilt after this checklist record
requires its own external digest and inspection record.
