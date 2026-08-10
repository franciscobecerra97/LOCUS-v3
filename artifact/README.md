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

D020's provisional internal Yi/aPPSS mapping assessment and active
selectable-suite implementation do not reinterpret either historical artifact.
A later artifact may include the completed P7.5 system only after P8, P9, the
applicable P6 gates, independent human validation, a new allowlist/profile, and
explicit owner release approval. P6.4 may remain blocked on external
infrastructure; any later host-separation result must be an optional, exactly
tiered profile rather than an implied property of the same-host artifact.

D023 adds a prerequisite for that later artifact: its primary reviewer workflow
must exercise the implemented P7.5 path from the loopback UI/client gateway through
the authenticated admission, discovery, storage, resolver, and party
containers, for the declared suite/topology arm. The current in-memory P7 UI
and frozen Compose deployment remain useful component controls, but running
them separately is not the expanded-system artifact result. The implemented
`integrated-config`, `integrated-start`, `integrated-stop`, and
`integrated-smoke` commands may be named as pre-evidence controls, but P10 must
package them with the later P8/P9 results under a new artifact profile.

D024 fixes the future package's implementation source: it must package the
self-contained `prototype_final/` workspace and its five-command executor.
The broad root command surface, root test suite, in-memory UI, frozen Compose
profile, and component harnesses may be retained only as explicitly labeled
supporting controls; they are not the primary reviewer workflow.
