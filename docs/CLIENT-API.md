# P7 Stable Research-Client API

Status: P7.1 implemented and tested on 2026-08-03. D023 preserves this API, and
the P7.5 deployment-backed realization and pre-evidence gate are complete.

D025/P7.7 assigns `LOCUS-client-api-v2` for the implemented managed Client
workflow; v1 remains immutable. V2 freezes key generation/transient reveal,
client recovery-package export/import, authenticated recovery/key replacement,
and exact self-destruction semantics while keeping recovery configuration
descriptor-bound. The separate
Manager API and controller API are not Client API operations, and a managed
Client cannot reach the Manager UI/API.

Manager-issued Client stop/start, restart, and kill/start are outside Client
API v2. They preserve the public client-instance ID but start a fresh process
proof identity with an empty server-side key slot, export/import cache, and
operation/session set. Client API v2 self-destruction removes the exact
container and ID through the separately authenticated `client-lifecycle`
controller route. Neither behavior is session continuity or forensic erasure.

Client API v2 does not add a successor-enrollment route. The existing same- and
cross-suite successor core remains unchanged and must continue to pass its
compatibility/crash controls outside the D025 Manager/Client UX.

## Managed Client API v2

The managed HTTP adapter in `prototype_final/` has this exact same-origin,
no-store surface. JSON requests reject missing, duplicate, unknown, oversized,
or wrong-version fields. Every POST requires the current process CSRF token and
exact loopback origin; package import instead receives bounded bytes with media
type `application/vnd.locus.recovery-package+json`.

| Route | Exact request | Result boundary |
| --- | --- | --- |
| `GET /api/v2/session` | None | Public client ID, managed-instance/proof binding, current public key fingerprint, UI/API profiles, and CSRF token |
| `GET /api/v2/catalog` | None | Four policies, two suites, fixed paired 2-of-3/3-of-5 holder profiles, and separate 4-of-5 authorization quorum |
| `POST /api/v2/key/generate` | `api_version`, `operation_id` | Fresh volatile synthetic Ed25519 seed and public fingerprint on a transient-secret response |
| `POST /api/v2/key/reveal` | `api_version` | Current synthetic seed and public fingerprint on a transient-secret response |
| `POST /api/v2/preview-policy` | `api_version`, `policy_id`, `recovery_input` | Transient normalized preview produced by the registered CuePolicy |
| `POST /api/v2/enroll` | `api_version`, `deployment_profile_id`, `operation_id`, `policy_id`, `recovery_input`, `suite_id` | Authenticated enrollment result plus one opaque download capability; the server-side key slot supplies the protected key |
| `POST /api/v2/package/export` | `api_version`, `download_id` | Exact `LOCUS-client-recovery-package-v1` attachment |
| `POST /api/v2/package/import` | Raw package bytes | Descriptor/current/party-authenticated suite, policy, paired profile, threshold, holders, quorum, and public key identity; no browser-selected override |
| `POST /api/v2/recover` | `api_version`, `operation_id`, `recovery_input`, `selected_holder_ids` | Exact-threshold recovery, key-identity verification, and atomic replacement of the volatile key slot |
| `POST /api/v2/self-destroy` | `api_version`, `operation_id` | Accepted one-instance destruction request through the isolated Client/controller route |

The server reports only completed protocol phases returned by the underlying
operation. While a synchronous request is running, the UI shows an honest busy
state; it does not fabricate live intermediate events. Suite, policy,
membership, endpoints, and thresholds restored from an imported package are
locked after authentication. Missing authenticated metadata fails closed.

The generated/recovered private-key seed is the one intentional v2 change from
the non-serializing v1 HTTP boundary. It exists only in the active Client
process and transient response/document state: never in the package, Manager,
controller, logs, URLs, browser storage, role volumes, or retained output.

## Boundary

`LOCUS-client-api-v1` is the stable local research-client facade implemented
by `prototype/locus/client_api.py`. It orchestrates existing components and
does not define a new CuePolicy, recovery suite, password domain, backup,
descriptor, admission, or lifecycle protocol.

The API is the only boundary a P7 UI may call. It routes through:

- the exact four-policy CuePolicy registry;
- the explicit Yi/aPPSS selector and descriptor-only recovery dispatch;
- both approved 2-of-3 and 3-of-5 paired profiles;
- reference backup v6 and the unchanged HKDF/AES protected-key path;
- signed descriptor, bundle, current pointer, receipt, installed trust, and
  fresh party-current-summary validation;
- the local proof-key-bound admission profile; and
- the existing secret-free enrollment and recovery state machines.

Recovery accepts no suite field. The authenticated descriptor chooses exactly
one suite and the facade never retries through the other adapter. Successor
creation accepts one explicit new-epoch suite/profile choice only after the
predecessor has recovered successfully.

## Public operations

The frozen operations are:

| Operation | Purpose | Public result |
| --- | --- | --- |
| `catalog` | List exact policies, suites, and paired profiles | Identifiers, labels, thresholds, and resolver profiles |
| `preview_policy` | Validate one transient structured input | Transient no-store normalized preview inside the active-client boundary |
| `enroll` | Generate/import one synthetic key and create epoch 1 | Receipt, public fingerprint, suite/policy/profile, threshold, and completed phases |
| `bootstrap` | Authenticate a supplied receipt and current public state | Enrolled suite/policy/profile, threshold, quorum, and public fingerprint |
| `recover` | Evaluate the enrolled policy and descriptor-selected suite | Verified public fingerprint and public phase completion; protected-key bytes remain a typed non-serializing return value |
| `create_successor` | Recover, then create one fresh same- or cross-suite epoch | New receipt and explicit rotation status |
| `inspect` | Report safe research metadata | Role names, versions, public identifiers, safe digests, categories, and byte counts |

Every normal serializable result passes the existing public-output validator.
Failures expose only a fixed category. Exception text, candidates, suite
outcomes, credentials, and secret-path values are not returned.

Policy preview is the one deliberately transient exception to the normal
public-output path: the active client must show the user the exact normalized
selection before enrollment. The future HTTP layer must make this POST-only,
no-store, non-logged, and clear it from the document after use. It is never an
artifact, terminal, trace, or inspector result.

## Implemented conformance

The P7.1 tests cover all four suite/topology arms:

- Yi 2-of-3;
- aPPSS 2-of-3;
- Yi 3-of-5; and
- aPPSS 3-of-5.

Each arm imports the same synthetic Ed25519 seed, enrolls, authenticates the
signed clean-client bootstrap, validates local admission, recovers through the
descriptor-selected adapter, and checks the exact key and public fingerprint.
Additional tests cover all four CuePolicy previews, wrong-input normalization,
rejection of a recovery suite override, cross-suite successor enrollment,
predecessor retirement, operation conflicts, and aggregate-only inspection.

P7.1 also closes an integration gap by permitting the already assigned
reference-backup v6 shape at the generic immutable backup-reference boundary.
The v4 and v5 meanings remain unchanged.

## P7.5 deployment-backed realization

The integrated reference system keeps the operations, request meanings,
response categories, and non-serializing recovered-key boundary above. The
host browser still calls only the loopback route adapter, and the
UI/client-gateway container satisfies each operation through authenticated
remote-service adapters:

- admission and proof-key-bound capability issuance;
- operator-signed discovery, receipt, descriptor, and current-state handling;
- exact admitted storage-gateway operations against the local S3-compatible
  provider;
- resolver service access only for the resolver-backed policy; and
- authenticated initialization, recovery, authorization, and lifecycle calls
  to the five parties.

Enrollment and recovery run under separate ephemeral Client A and Client B
roots, identities, and proof keys. Client B receives only installed trust, the
public receipt or handle, and transient fictional recovery input. No operation
may use direct party/provider volume access or the current in-memory record
store in the full-system path.

P7.5 adds deployment-specific adapters and validation without changing this
API identifier. `LOCUS-integrated-reference-deployment-v1` and
`LOCUS-integrated-reference-config-v1` bind that realization. Its operator
commands are `integrated-config`, `integrated-start`, `integrated-stop`, and
`integrated-smoke`. Multi-host placement and live AWS remain optional,
separately versioned profiles and are not prerequisites for the reproducible
same-host system.

## Limitations

The P7 implementation is a same-process research component facade. Its
internal record store logically separates encrypted backup and holder records,
but it is not deployment or role-separation evidence and remains a component
control. P7.5 separately realizes the same API across the integrated graph;
its completed smoke is implementation verification, not retained P8/P9
evidence. The local issuer, `.invalid` endpoints, and synthetic keys are
deliberate. No external provider, production admission, human usability,
secure-erasure, or manuscript claim follows.
