# LOCUS Final Integrated Prototype

This directory is the self-contained active implementation workspace selected
by D024 for P8 and later LOCUS implementation, assurance, evidence, and
artifact work. It contains the dependency-complete D023 predecessor and the
implemented D025 managed deployment plus their focused controls.
Existing root implementations remain historical or component controls and are
not dependencies of this workspace.

D025/P7.7 is complete inside this directory. Its mode-free `integrated-start`
exposes a Manager UI, creates
no Client automatically, and lets the Manager control fixed dynamic Client
containers. The same Client UI exposes enrollment and authenticated client-
recovery-package import. All twelve D025 managed profiles are Assigned, not
Frozen. Their implementation and acceptance output are not retained P8/P9
evidence; collection still requires the applicable later PLAN gates.

D028/P9.1 is also complete. It freezes the exact managed performance and
resilience methodology but intentionally provides no collector, result
identifier, or retained path. D029 subsequently closes the separate P9.2 gate.

D029/P9.2 is complete. Ten managed-performance identifiers,
the 1,220-slot scenario expansion, strict observation/invalid-attempt schemas,
deterministic processor, matched comparison, closing manifest, and synthetic
positive controls are checked by `integrated-check`. The owner has now opened
P9.3, and its separately gated collector is implemented for clean-source
exploratory validation. No retained performance directory exists yet.

## Scope

The managed implementation provides one same-host Docker system with:

- a loopback Manager UI, constrained root-equivalent lifecycle controller, and
  dynamically created loopback Client UIs;
- disjoint Manager/controller, Client/controller, Manager/browser, and Client/
  browser network boundaries;
- local synthetic admission and proof-key-bound capabilities;
- operator-signed discovery, descriptors, bundles, receipts, and current state;
- an application storage gateway and local S3-compatible provider;
- the resolver service required by the frozen composite CuePolicy;
- five authenticated authorizer/recovery-party services;
- selectable Yi and aPPSS suites at 2-of-3 and 3-of-5;
- a separate 4-of-5 authorization quorum;
- all four registered CuePolicies;
- clean-client recovery; and
- unchanged same-suite and cross-suite successor behavior, with a narrowly
  gated measurement-only Client API route and no new user-facing UI control.

This remains a one-host, one-Docker-engine, one-operator research profile. It
does not establish host separation, independent administration, real-provider
behavior, usability, production security, forensic erasure, or independent
cryptographic review.

The one-shot networkless bootstrap runs as root with only `CHOWN` and
`DAC_READ_SEARCH` added after dropping all capabilities. Those capabilities
are required to create and later revalidate the per-role owner-only credential
files before the unprivileged services start; bootstrap has no Docker socket or
network and exits before normal operation.

## Prerequisites

- Python 3.12
- uv 0.11.29
- Rust/Cargo for `integrated-check`
- Docker with Compose for the deployment commands

Run all commands from this directory.

## Command surface

Install the pinned environment:

```console
uv sync --frozen
```

Run the focused Python/native quality gate:

```console
uv run --frozen python tasks.py integrated-check
```

Validate the canonical manifest and resolved managed Compose graph:

```console
uv run --frozen python tasks.py integrated-config
```

The normal interactive entry point is:

```console
uv run --frozen python tasks.py integrated-start
```

It starts the service plane plus the loopback Manager UI and no Client
container. Client creation, destruction, recovery-client replacement, and
normal whole-system stop then occur through the Manager UI. `management`
connects Manager/controller only; `client-lifecycle` connects Client/controller
only. `manager-edge` publishes only the Manager path, while `browser-edge`
publishes only dynamic Client paths. A Client cannot reach the Manager UI/API.
This is the assigned implementation boundary for P8.1 and later work. Its P7.7
verification is pre-evidence development output, not a retained P8/P9 result.

The Manager's header contains the complete-system stop control and locks its
other mutating controls after shutdown begins. In each Client, enrollment stays
locked until the backend confirms a transient key is loaded; authenticated
package recovery remains available on a clean Client without a preexisting
key. These interaction guards do not change the assigned API or protocol
semantics.

The D023 `--mode enrollment`, `--mode recovery`, and `--destroy` options are no
longer accepted by this executor. Their source history remains provenance only.

Client `stop` and `kill` make that endpoint unavailable but retain its container
and public client ID. A later `start`, and every `restart`, rotates the process
proof identity and clears the server-side key slot, export/import cache, and
operation/session set under the same public client ID. `destroy` removes the container
and ID; a later `create` receives a new ID. These are destructive volatile
resets, not session-preserving actions or forensic erasure. A Client document
already loaded in the external browser can remain rendered until closed or
reloaded.

`integrated-stop` may remain available during and after migration only for
exact-project emergency/orphan recovery and automated-smoke cleanup:

```console
uv run --frozen python tasks.py integrated-stop
```

That emergency command preserves the exact-project role/provider volumes and
credentials. Use the following only when an irreversible full local reset is
intended:

```console
uv run --frozen python tasks.py integrated-stop --reset-state
```

`--reset-state` deletes all exact-project volumes, including the synthetic
trust domain, provider objects, party state, and enrolled epochs. The next
start creates fresh credentials and empty protocol state, so packages whose
remote epoch existed only in the erased project can no longer recover. There
is no in-place credential renewal: the managed CA is valid for 366 days and
role TLS certificates for 365 days; expired or manifest-incompatible preserved
state fails closed until this explicit reset.

Run the complete disposable pre-evidence acceptance matrix:

```console
uv run --frozen python tasks.py integrated-smoke
```

P7.7's accepted run covered all four suite/topology arms, 26 threshold subsets,
four isolated clean Clients, live control isolation and lifecycle actions,
output scans, 15 bootstrap-role plus 15 post-operation role audits, normal
stop/restart recovery with the same CA, destructive reset with a fresh CA and
old-package rejection, and exact cleanup. These observations close the
implementation gate only; they were not retained as P8/P9 evidence.

Reproduce the P8.4 attempt-control boundary:

```console
uv run --frozen python tasks.py integrated-attempt-boundary
```

This command verifies the unchanged frozen model, signed-certificate control,
strict schema, exact D025 five-authorizer/4-of-5 binding, and absence of a
monotonic-witness role before reproducing all seven bounded scenarios. Its
quorum-only rollback counterexamples are negative regression controls, not a
global, lifetime, or rollback-resistant attempt bound. The command retains no
output and does not exercise a live-container rollback attack.

D026 assigns the aggregate-only P8.2 collector. An exploratory run writes no
retained output:

```console
uv run --frozen python tasks.py integrated-state-evidence
```

After committing and validating a clean collector source state, the explicit
`--retain` form publishes exactly one complete 42-report corpus under
`evidence/retained/managed-state-v1/`. It fails if the worktree is dirty or the
exclusive target already exists.

P8.2's retained run completed on 2026-08-17 from clean source commit
`6e304560222b8059292ae291586ee792cc39ed3d`. The checked-in corpus contains 18
Yi, 18 aPPSS, and six common reports and closes to
`e31b215c936ed6693ac84e2bcf2d497a986e6e7cfaf0445637a749836aab83d5`.

D027 assigns the payload-free P8.3 flow collector. Its exploratory form writes
no retained output:

```console
uv run --frozen python tasks.py integrated-flow-evidence
```

The sole v1 `--retain` run completed on 2026-08-17 from clean source commit
`cd5aaaf762a9b18bef681f496f704f772fe6e9be`. It atomically published 12 Yi,
12 aPPSS, and six common reports under
`evidence/retained/managed-flow-v1/`, closing to
`1deb49fcf5a7550f16da28702d1364ce20603f573d872cf811f631d331cf842c`.
The exclusive target cannot be replaced by another v1 run.

The checked P9.1 methodology is documented in
`docs/MANAGED-PERFORMANCE-METHODOLOGY-v1.md` and encoded canonically in
`docs/managed-performance-methodology-v1.json`. Its validator is exercised by
`integrated-check`. P9.3's exploratory collector executes all 40 fresh
arm/block projects and writes no retained output:

```console
uv run --frozen python tasks.py integrated-performance-evidence
```

Only after the collector source is committed and clean may the one explicit
`--retain` run exclusively publish
`evidence/retained/managed-performance-v1/`. The target must not already
exist. The command uses only synthetic fixtures and the exact local-provider,
same-host D025 graph; it does not authorize P9.4 external-provider or
multi-host work.

## Directory layout

| Path | Purpose |
| --- | --- |
| `tasks.py` | Only supported executor; exposes nine `integrated-*` commands |
| `locus/` | Dependency-complete integrated Python implementation and UI assets |
| `appss-core/` | Native aPPSS core and public vector |
| `tpass-core/` | Frozen native Yi core and vector |
| `tpass-python/` | Narrow PyO3 binding for both native suites |
| `deploy/` | Integrated Dockerfile, Compose graph, and canonical manifest |
| `tests/` | Focused manifest, bootstrap, isolation, and service-boundary tests |
| `docs/security-matrix-v2.json` | Assigned additive managed-system security contract; not retained evidence |
| `docs/ATTEMPT-CONTROL-BOUNDARY.md` | Frozen negative model and local signed-certificate boundary |
| `docs/MANAGED-PERFORMANCE-METHODOLOGY-v1.md` | D028/P9.1 non-collecting managed evaluation design |
| `docs/MANAGED-PERFORMANCE-EVIDENCE-v1.md` | D029 schemas, P9.3 collector boundary, processor, and retention gate |
| `docs/schemas/` | Integrated configuration, package, and assigned security-matrix schemas |

## Evidence boundary

`integrated-check`, `integrated-config`, `integrated-smoke`,
`integrated-attempt-boundary`, exploratory `integrated-state-evidence`, and
exploratory `integrated-flow-evidence` produce ordinary development output
only. Exploratory `integrated-performance-evidence` is likewise non-retaining.
D026's
explicit `integrated-state-evidence --retain` is the sole P8.2 retained path;
it uses the assigned schema, identifiers, positive controls, provenance,
output-safety policy, and versioned result path. D027's separate
`integrated-flow-evidence --retain` is the sole P8.3 retained path; its v1
target is now complete and immutable. It cannot emit P9 metrics. P9.3 alone
may use `integrated-performance-evidence --retain` from its clean collector
commit; P9.4 remains prohibited.

Use generated keys, fictional cues, generated credentials, and disposable
local services only. Never supply real private keys, credentials, accounts, or
personal recovery information.
