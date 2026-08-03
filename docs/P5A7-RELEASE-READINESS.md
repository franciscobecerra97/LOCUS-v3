# P5A.7 Selectable-Suite Release Readiness

Status: `In progress — D019 mapping review and release activation pending`

Recorded on: 2026-08-03

## Candidate boundary

The reviewed implementation candidate is commit `36ea1fe`. P5A.1 through
P5A.6 are commits `19f00e1`, `4fc6ef1`, `bd24386`, `f519e52`, `db62ac4`, and
`8795947`. Commit `36ea1fe` pins JSON, text-vector, and attribute files to LF so
fresh Windows checkouts preserve the exact frozen/public vector digests.

The candidate includes two independent recovery-suite implementations behind
an exact registry and one common outer `S_R -> HKDF-SHA-256 -> AES-256-GCM`
contract. The selectable epoch factory and all four same-suite/cross-suite
successor directions remain inactive at the application/deployment boundary
until the review gate passes. Released recovery therefore remains Yi-only at
this checkpoint.

## Gate record

| Gate | Result | Exact boundary |
|---|---|---|
| Frozen Yi core/vector/legacy regression | Passed | Complete gate at `8795947` on Linux and `36ea1fe` on Windows |
| aPPSS native/vector/adapter regression | Passed | Same complete gates |
| Python tests | Passed | 279 tests, one expected live-provider skip on both clean runs |
| Native suites | Passed | aPPSS 8 unit + 1 vector; Yi 17 unit + 1 vector; binding crate 0 tests |
| Formatting, lint, typing, repository boundary | Passed | Ruff, mypy, Cargo fmt/clippy, and source/generated-data boundary |
| Clean Linux | Passed for implementation commit `8795947` | Disposable `python:3.12.13-bookworm` container; `uv==0.11.29`; Rust `1.83.0`; fresh local clone; complete gate |
| Clean Windows | Passed for candidate `36ea1fe` | Fresh local clone; Python `3.12.13`; `uv==0.11.29`; Rust `1.83.0-x86_64-pc-windows-msvc`; empty dependency cache; complete gate |
| CI status | Not independently observed | The private GitHub Actions page was not authenticated in this execution context; `.github/workflows/ci.yml` still runs the complete gate on `ubuntu-latest` and `windows-latest` for every push/PR |
| Retained performance/evidence collection | Correctly not started | P9 schema/methodology/profile identifiers are not frozen; no P5A retained corpus was created |
| Independent TPASS/aPPSS claim-focused mapping review | Pending, release-blocking | Packet in `docs/RECOVERY-SUITE-MAPPING-REVIEW.md`; deviations in `docs/RECOVERY-SUITE-DEVIATIONS.md` |
| Manuscript change | Not authorized and not applied | Draft M-SELECTABLE-SUITES-001; P8/P9 and explicit owner approval remain required |
| Application/deployment activation | Pending, release-blocking | Must occur only after accepted D019 mapping review, with no automatic fallback |

The Linux result predates only the line-ending policy commit; the final release
commit must repeat clean Linux and Windows/CI checks after review remediation
and activation. These records therefore demonstrate candidate portability but
do not declare the release complete.

## Portability finding and correction

A fresh Windows checkout with the user's global `core.autocrlf=true` initially
failed three SHA-256 vector checks because `.gitattributes` did not cover
general JSON/TXT artifacts. No vector content or expected digest was changed.
Commit `36ea1fe` sets `*.json`, `*.txt`, and `.gitattributes` to `eol=lf`.
A second empty-cache Windows checkout then passed the entire gate, including
the formerly failing aPPSS format, frozen CuePolicy, and frozen Yi vector
digest checks.

## Release-blocking checklist

- [x] Independent Yi and aPPSS implementations solve the same outer LOCUS
  recovery-secret contract.
- [x] One epoch binds exactly one suite and recovery has no probe/fallback path.
- [x] Paired 2-of-3 component conditions and the fixed compromise regression
  are implemented.
- [x] Same-suite and bidirectional cross-suite successor preparation preserve
  protected-key identity and create fresh native state.
- [x] Frozen Yi identifiers, vectors, behavior, and retained v2 evidence remain
  unchanged.
- [x] No retained P5A performance corpus was collected.
- [x] Clean candidate Linux and Windows gates have passed at the boundaries
  recorded above.
- [ ] D019's independent review accepts or correctly qualifies the frozen Yi
  mapping, aPPSS mapping, and LOCUS composition for the exact stated claims.
- [ ] Every claim-critical deviation is accepted with an explicit qualification,
  corrected and re-reviewed, or causes removal of the dependent inherited
  result/LOCUS claim.
- [ ] Every entry in `docs/RECOVERY-SUITE-DEVIATIONS.md`, including any newly
  discovered difference, has a final reviewer classification.
- [ ] The application and reference deployment expose explicit Yi/aPPSS
  new-enrollment selection, preserve descriptor-bound recovery dispatch, and
  pass release tests with no fallback.
- [ ] Active architecture, protocol, threat, information-flow, lifecycle, API,
  storage, evidence, artifact, and version documentation is synchronized to
  the released behavior.
- [ ] The exact final release commit passes clean Linux and Windows CI.
- [ ] P8/P9 retained evidence exists before any comparison is promoted into
  manuscript wording.

## Post-review release sequence

1. Record the attributable D019 mapping-review finding for Yi, aPPSS, and the
   LOCUS composition, including the completed deviations register.
2. Resolve each claim-critical finding on a new exact commit or remove the
   dependent claim; re-run reviewer-required tests and obtain confirmation for
   every corrected mapping.
3. Activate explicit new-enrollment selection in the application/reference
   deployment while preserving descriptor-bound recovery and no fallback.
4. Synchronize the active technical documentation and exact version/release
   record; do not allocate P9 result identifiers early.
5. Run clean Linux and Windows complete gates on the final release commit and
   record CI/run links when authenticated access is available.
6. Continue chronologically to P6. No `paper/` edit occurs here.

M-SELECTABLE-SUITES-001 remains a draft replacement for the superseded
M-APPPSS-001 proposal. It is not eligible for owner approval until the P8/P9
evidence gates are complete, and it is never applied without a separate
explicit owner decision.
