# LOCUS Reference Architecture

Status: living architecture boundary, synchronized 2026-08-11. The frozen
same-host Yi deployment below remains historical/component scope. D023 approves
a new P7.5 integrated reference predecessor.
Its manifest, service plane, deployed UI bridge, lifecycle workflow, expanded
fault matrix, and clean-checkout gate are implemented and pass.

D025/P7.7's separately versioned Manager/controller, dynamic Client, and client
recovery-package transition is implemented and all twelve managed identifiers
are Assigned. Only its
controller may hold the root-equivalent Docker socket. `management` connects
Manager/controller only, `client-lifecycle` connects Client/controller only,
`manager-edge` publishes only the Manager loopback path, and `browser-edge`
publishes only dynamic Client loopback paths. A Client cannot join
`manager-edge` or reach the Manager UI/API. Stop/start, restart, and kill/start
retain the public client ID but rotate proof identity and clear volatile key/
session state. The 366-day CA and 365-day role certificates have no in-place
renewal; an explicit emergency full-state reset is destructive. D023 remains
a supporting immutable predecessor. The one-shot bootstrap runs as root with
only `CHOWN` and `DAC_READ_SEARCH`, no network or Docker socket, and exits before
unprivileged services. P8.1 is ready, but no retained D025 evidence exists yet.

The cue-specific boundary and role-visible data are diagrammed in
`docs/cue-data-flow.md`.

## Objective and evidence boundary

LOCUS separates an encrypted private-key backup from threshold recovery state
while mediating recovery through a counted online TPASS protocol. The reference
architecture defines role ownership, interfaces, and prohibited data flows. It
does not claim production security, independent administration, resolver
privacy, rollback resistance, or a complete global attempt bound merely because
the current same-host deployment runs successfully.

## Roles

- **Client:** resolves and canonicalizes exactly three synthetic or user-selected
  location-person pairs, derives the TPASS input, encrypts/decrypts the protected
  key, validates cloud/party responses, and presents generic failures. Raw cues,
  the TPASS password, recovered secret, wrapping key, and private key remain
  client-local and ephemeral.
- **Cloud object store:** stores one bounded canonical encrypted backup plus
  public policy metadata under an exact `(backup_id, epoch, backup_digest)`
  reference. It receives no party state, cue record, password verifier, recovered
  secret, or wrapping key.
- **Recovery parties:** each party stores only its own TPASS state when
  applicable, authorizer identity/key, durable attempt ledger, recovery-phase
  state, and privacy-minimized audit chain. A party receives no encrypted private
  key, raw cue, resolver fixture, cloud credential, or another party's state.
- **Resolver:** maps client selections to canonical records. The reproducible
  baseline is a deterministic synthetic fixture on a client-only network. A real
  external resolver may observe or manipulate queries and is outside the storage
  privacy boundary.
- **Attempt-control layer:** a quorum-certified hash-chained ledger authorizes a
  request before the first secret-dependent TPASS operation. This supplies
  tested local ordering and retry behavior only. Rollback-resistant global
  attempt control, public admission, and arbitrary-schedule safety are outside
  the current positive claims rather than unfinished prerequisites to one.
- **Provisioner:** a trusted, networkless, one-shot local-artifact authority that
  generates synthetic state and role identities. It is not a production
  enrollment service or an independently administered role.

## Reference data flow

1. Enrollment canonicalizes the three-pair recovery input on the client.
2. Native TPASS setup creates public parameters and one secret state per TPASS
   party; only the matching party receives each state.
3. The client encrypts a synthetic/private key under material derived from the
   TPASS group secret and publishes only the canonical encrypted backup to the
   cloud role.
4. Recovery resolves/canonicalizes cues on a fresh client, fetches the exact
   cloud object, and constructs a blinded native TPASS request.
5. Recovery parties certify and durably count the request before producing
   secret-dependent commitments/responses over pinned mutual TLS.
6. The client aggregates a threshold subset, validates the native TPASS result,
   derives the wrapping key, and authenticates/decrypts the backup locally.

## Invariants

1. Cloud state and every party's secret state remain in disjoint role storage.
2. No cloud or party record contains raw cues, a cue identifier, password
   verifier, recovered group secret, wrapping key, or decrypted private key.
3. Each party has one durable database and no mount or configuration path to
   another party's state.
4. The cloud backup digest, authorizer configuration, party enrollment record,
   and client reference identify the same backup epoch.
5. A counted attempt is durably authorized before native
   `prepare_commitment`.
6. Retries with the same authenticated caller/route/body/idempotency key map to
   one stored result; changed reuse conflicts.
7. Normal output is machine-readable and privacy-minimized; known prohibited
   values or fields fail artifact checks.

## D023 primary integrated implementation

P7.5 now composes the component contracts into one disposable
same-host system. The host browser reaches only a loopback UI/client-gateway
container. That gateway coordinates authenticated local admission,
operator/discovery/signing, application storage gateway, resolver, and five
authorizer/holder services. The storage gateway alone reaches the local
S3-compatible cloud-object role with a narrow server-side credential.

The system has four explicitly bound arms: Yi and aPPSS at 2-of-3 and 3-of-5,
each over five authorizers with a separately typed 4-of-5 authorization quorum.
One epoch binds one suite and topology, with no recovery override or fallback.
Same-suite and cross-suite successors create fresh consecutive epochs.

Enrollment and clean recovery use separate ephemeral Client A and Client B
roots, transport identities, and proof keys. A networkless bootstrap may create
synthetic credentials, public configuration, empty role roots, and resolver
fixtures, but it may not inject suite state or secret-bearing client state.
The full-system path may not read party or provider volumes directly.

This first integrated profile remains one-host, one-Docker-engine, and
one-operator research infrastructure. Multi-host placement and AWS S3 are
optional, separately versioned profiles; neither is implied by the same-host
result. `LOCUS-integrated-reference-deployment-v1` and
`LOCUS-integrated-reference-config-v1` bind the implementation and canonical
manifest. The additive v5/v6 cloud envelope/gateway are
`LOCUS-cloud-backup-object-v2` and
`LOCUS-application-storage-gateway-v2`; frozen v1 paths remain unchanged.

## Implemented frozen reference boundary

`deploy/compose.yaml` currently instantiates the provisioner, deterministic
resolver, SeaweedFS, five recovery parties, and an ephemeral client with pinned
images, read-only roots, disjoint internal networks, no host ports, and separate
named volumes. `tasks.py deployment-smoke` validates the declared and live role
graph, audits role snapshots, performs recovery around a party restart, scans
output, and removes all resources.

This is one-host synthetic artifact evidence. The authoritative detailed
contracts are `docs/threat-model.md`, `docs/cue-policy.md`,
`docs/recovery-party-api.md`, `docs/attempt-control-state-machine.md`, and
`docs/deployment.md`. It retains the exact
`LOCUS-compose-deployment-v2` meaning and is not the D023 integrated system.
The P7 same-process UI/API remains a component conformance control for the same
reason. Central P8/P9 system evidence must bind and traverse the new integrated
managed manifest rather than infer full-system behavior from D023 or either
narrower profile. P7.7's green smoke is development verification; collection
remains unauthorized until the applicable P8/P9 evidence gates pass.
