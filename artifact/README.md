# Improvement-Project Artifact Workspace

This directory is the active artifact-documentation workspace for the expanded
LOCUS system.

The active builder now audits the versioned package definition under
`artifact/package-v2/`. That package has its own identifier, reviewer documents,
manifest schema, allowlist, tests, and release checklist. Release authorization
remains pending, so the audit path may be used but no v2 archive may be
published.

The integrated repository retains:

- frozen v1/v2 evidence under `experiments/`;
- the current manuscript and generated inputs under `paper/`; and
- the sealed verified v1 anonymous artifact under `dist/`.

Repository scope and anonymous-package scope are intentionally different. A
future package includes only its explicit licensed, privacy-safe allowlist. The
sealed v1 release remains baseline history and must not be overwritten.

The v2 allowlist excludes repository-facing planning documents and includes
only its package-specific reviewer guides. The anonymity scan remains unchanged
and fail closed. Extracted-tree verification continues to accept the sealed v1
manifest while the active builder emits only the new v2 identifier.
