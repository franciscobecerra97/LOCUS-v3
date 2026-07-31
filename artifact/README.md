# Improvement-Project Artifact Workspace

This directory is the active artifact-documentation workspace for the expanded
LOCUS system.

The inherited artifact builder still uses its old v1 allowlist and must not be
used to publish the expanded system until PLAN P0.4 and P10.3 update its version,
allowlist, schemas, tests, and release checks.

The integrated repository retains:

- frozen v1/v2 evidence under `experiments/`;
- the current manuscript and generated inputs under `paper/`; and
- the sealed verified v1 anonymous artifact under `dist/`.

Repository scope and anonymous-package scope are intentionally different. A
future package includes only its explicit licensed, privacy-safe allowlist. The
sealed v1 release remains baseline history and must not be overwritten.

Known migration gate: the inherited v1 `artifact-package --check` treats
project-management references in the integrated repository README and active
artifact planning documents as anonymity violations. That fail-closed result is
expected until P0.4 introduces a new package-specific README, allowlist, and
version. Do not weaken the existing anonymity scan merely to make it pass.
