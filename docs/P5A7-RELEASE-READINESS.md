# P5A.7 Selectable-Suite Release Readiness

Status: `Complete for implementation chronology under D020; independent human validation remains open`

Recorded on: 2026-08-03

## Exact boundary

P5A.1 through P5A.6 are commits `19f00e1`, `4fc6ef1`, `bd24386`,
`f519e52`, `db62ac4`, and `8795947`. Commit `36ea1fe` pins JSON, text-vector,
and attribute files to LF. Commit `f92b302` is the exact cryptographic
implementation and review-packet boundary used by D020's internal assessment.

The candidate contains two independent suite implementations behind an exact
registry and one common `S_R -> HKDF-SHA-256 -> AES-256-GCM` contract. D020
activates the existing explicit selector, descriptor-only recovery dispatch,
and four same-suite/cross-suite successor directions at the post-baseline
application/component boundary. The frozen `LOCUS-compose-deployment-v2`
profile and retained v2 evidence remain Yi-only and unchanged. P6.3 later
assigns separate paired same-host process profiles and does not reinterpret
either frozen boundary.

## Mapping disposition

D020's internal assessment is
`docs/P5A7-INTERNAL-MAPPING-ASSESSMENT.md`, SHA-256
`1479de1f09709e6e9b3fde1b07267b1cda485d0e23690718cbe0413be7a46c2e`.
It is bound to cryptographic implementation commit `f92b302` and records:

- provisional `accepted with required qualifications` dispositions for frozen
  Yi, D017 aPPSS, and the LOCUS outer composition;
- no unresolved claim-blocking or correction-required finding;
- provisional classification of every entry in
  `docs/RECOVERY-SUITE-DEVIATIONS.md`; and
- an explicit independence/conflict disclosure and mandatory human checklist.

This record is not independent. It closes P5A implementation chronology only.
D019 independent human validation remains mandatory before manuscript reliance,
an “independently reviewed” label, a final reviewed release, or submission.

## Gate record

| Gate | Result | Exact boundary |
|---|---|---|
| Frozen Yi core/vector/legacy regression | Passed | Complete gate at `8795947` on Linux and `36ea1fe` on Windows; no Yi code/vector change in P5A.7 |
| aPPSS native/vector/adapter regression | Passed | Same candidate gates; no aPPSS semantic/code/vector change in P5A.7 |
| Python and native suites | Passed | 279 Python tests with one expected live-provider skip; aPPSS 8 unit + 1 vector; Yi 17 unit + 1 vector; binding crate 0 tests |
| Formatting, lint, typing, repository boundary | Passed | Ruff format/lint, mypy, Cargo fmt/clippy, source/generated-data boundary, and Python syntax on the complete P5A.7 tree |
| Clean Linux | Passed for implementation commit `8795947` | Disposable `python:3.12.13-bookworm`, `uv==0.11.29`, Rust `1.83.0`, fresh clone, complete gate |
| Clean Windows | Passed for implementation candidate `36ea1fe` | Fresh empty-cache clone, Python `3.12.13`, `uv==0.11.29`, Rust `1.83.0-x86_64-pc-windows-msvc`, complete gate |
| D020 internal mapping assessment | Provisionally accepted with qualifications | Exact record and digest above; not independent |
| D019 independent human validation | Pending, deferred external gate | Required before manuscript/final reviewed release, not before P6 implementation work |
| Application selector | Active | Exact selector is mandatory for new setup; recovery uses only the authenticated descriptor suite; no fallback |
| Paired deployment activation | Completed later in P6.3 | New same-host process profiles are separate; frozen Yi Compose evidence is not reinterpreted |
| Retained performance/evidence collection | Correctly not started | P9 schema/methodology/profile identifiers are not frozen |
| Manuscript change | Not authorized and not applied | Draft M-SELECTABLE-SUITES-001 still requires P8/P9, human validation, and exact owner approval |

The prior clean Linux/Windows runs cover the cryptographic implementation and
fixed vectors. P5A.7 changes only governance, mapping documentation, active
application-interface status, and claim boundaries; the final repository gate
below still checks the complete combined tree.

## Portability finding retained

A fresh Windows checkout with global `core.autocrlf=true` initially failed
three SHA-256 vector checks because `.gitattributes` did not cover general
JSON/TXT artifacts. No vector content or expected digest changed. Commit
`36ea1fe` sets `*.json`, `*.txt`, and `.gitattributes` to `eol=lf`; the second
empty-cache Windows checkout passed the complete gate.

## Chronology-complete checklist

- [x] Yi and aPPSS solve the same outer LOCUS recovery-secret contract while
  retaining independent native state, messages, and assumptions.
- [x] One epoch binds exactly one suite and recovery has no probe, downgrade,
  or fallback path.
- [x] Paired 2-of-3 component conditions and fixed compromise regression are
  implemented.
- [x] Same-suite and bidirectional cross-suite successors preserve protected-key
  identity, create fresh native state, and reject mixed state.
- [x] Frozen Yi identifiers, vectors, behavior, Compose deployment, and retained
  v2 evidence remain unchanged.
- [x] D020 internal review provisionally accepts/qualifies every scoped mapping
  with no correction-required finding.
- [x] Every deviations-register entry has a provisional internal status and
  explicit qualification where required.
- [x] The application interface exposes explicit Yi/aPPSS new-epoch selection
  and descriptor-bound recovery with no fallback.
- [x] Active architecture, protocol, threat, information-flow, lifecycle, API,
  storage, evidence, artifact, and version documentation records the D020
  boundary.
- [x] The final combined repository gate passes after this record is complete.
- [ ] A qualified independent human confirms or changes every provisional
  mapping status before manuscript reliance/final reviewed release.
- [ ] P8/P9 retained evidence exists before any comparison is promoted into
  manuscript wording.

## Human follow-up and next phase

The human reviewer must follow the checklist in
`docs/P5A7-INTERNAL-MAPPING-ASSESSMENT.md`, issue separate Yi/aPPSS/composition
dispositions, resolve every rejected claim-critical mapping, and bind the
finding to the then-current implementation commit. This deferred gate does not
block P6 implementation but remains visible in P10/external-review work.

After this historical P5A.7 record, chronology continues through P6.1 storage
conformance, P6.2 AWS adapter boundaries, and P6.3 paired topology profiles.
No `paper/` edit occurs in P5A.7 or those implementation steps.

M-SELECTABLE-SUITES-001 remains a draft replacement for the superseded
M-APPPSS-001 proposal. It is not eligible for owner approval until P8/P9 and
independent human validation complete, and it is never applied without a
separate explicit owner decision.
