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
- unchanged same-suite and cross-suite successor-core behavior retained as a
  compatibility control outside Client API v2 and the managed Client UI.

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

## Directory layout

| Path | Purpose |
| --- | --- |
| `tasks.py` | Only supported executor; exposes five `integrated-*` commands |
| `locus/` | Dependency-complete integrated Python implementation and UI assets |
| `appss-core/` | Native aPPSS core and public vector |
| `tpass-core/` | Frozen native Yi core and vector |
| `tpass-python/` | Narrow PyO3 binding for both native suites |
| `deploy/` | Integrated Dockerfile, Compose graph, and canonical manifest |
| `tests/` | Focused manifest, bootstrap, isolation, and service-boundary tests |
| `docs/security-matrix-v2.json` | Assigned additive managed-system security contract; not retained evidence |
| `docs/schemas/` | Integrated configuration, package, and assigned security-matrix schemas |

## Evidence boundary

`integrated-check`, `integrated-config`, and `integrated-smoke` produce ordinary
development output only. They do not create retained P8/P9 evidence. Future
collection must first assign the applicable schema, identifier, positive
controls, provenance, output-safety policy, and versioned result path.

Use generated keys, fictional cues, generated credentials, and disposable
local services only. Never supply real private keys, credentials, accounts, or
personal recovery information.
