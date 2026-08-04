# P7 Stable Research-Client API

Status: P7.1 implemented and tested on 2026-08-03. D023 preserves this API and
requires a deployment-backed realization in P7.5; that realization is not yet
implemented.

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
host browser still calls only the loopback route adapter, but the
UI/client-gateway container must satisfy each operation through authenticated
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

P7.5 will add deployment-specific adapters and validation without changing
this API identifier. Its new deployment/configuration identity and runnable
operator commands are allocated with the P7.5 implementation, not in this
document. Multi-host placement and live AWS remain optional, separately
versioned profiles and are not prerequisites for the reproducible same-host
system.

## Limitations

The current implementation is a same-process research component facade. Its
internal record store logically separates encrypted backup and holder records,
but it is not deployment or role-separation evidence and will remain a
component control after P7.5. The local issuer, `.invalid` endpoints, and
synthetic keys are deliberate. Until P7.5 is implemented and accepted, this
API does not demonstrate the fully connected system. No external provider,
production admission, human usability, secure-erasure, or manuscript claim
follows.
