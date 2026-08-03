# Recovery-party service API

Status: P4.1 frozen service contract for the ASIACCS 2027 Cycle 1 reference
artifact, updated 2026-07-21. This document maps the P5 attempt-control and admission
designs to network operations. The first P4.2/P4.3/P4.4/P5.5/P5.6 slice now
implements the transport-agnostic native party core, local SQLite
installation/idempotency guard, canonical signed two-phase attempt certificates,
and a bounded mutually authenticated HTTPS adapter for ledger, freshness, native
commitment, and native response operations. A five-process test exercises
per-party TPASS state, separate party databases, role-separated identities,
correct and wrong-input recovery, exact retry, alternate subsets, one-party loss,
process restart/catch-up, durable HTTP idempotency, changed-request replay
rejection, and fail-closed loss of a volatile phase. This is
authenticated same-host process-boundary evidence for the party protocol; it is
not yet an independently deployed recovery system or global-bound proof.

## Problem statement

The local prototype calls TPASS functions over in-memory dictionaries. A
paper-facing recovery party must instead expose a bounded, authenticated API,
store only its own share and ledger state, make retries idempotent, and refuse to
cross the attempt-control boundary out of order.

The most important boundary is earlier than the final TPASS response share:
`prepare_commitment` uses the party's password share and is the first
secret-dependent TPASS message. Therefore a party must durably install the exact
attempt authorization and live freshness evidence before it calls
`prepare_commitment` or releases a `PartyCommitment`.

## Roles and trust assumptions

- A fresh **client** creates the blinded TPASS request and checks the final result.
  It has no client certificate in the baseline; HTTPS server authentication plus
  D004 proof-key-bound admission authenticates its right to spend attempts;
  the default future profile uses the local synthetic issuer.
- The untrusted **coordinator** sequences proposals, relays party-specific
  admission proofs, collects votes/certificates, and relays public TPASS messages.
  It cannot sign as a party or authorizer.
- Each **party** has a distinct service identity, authorizer signing key, TPASS
  state, and durable database. Peer and coordinator calls use mutual TLS.
- **Administrators** sign exact lifecycle actions. Their signatures supplement,
  but never replace, the active ledger quorum.
- Networks, the coordinator, the client, and up to the documented faulty parties
  may replay, reorder, alter, withhold, or duplicate messages. Safety fails closed.

The quorum, rollback, TPASS, admission-provider, and administrator assumptions are
those in `docs/attempt-control-state-machine.md`, `docs/attempt-control.md`, and
`docs/recovery-authorization.md`.

## Transport and representation profile

- API version: `locus-party-api-v1` under path prefix `/v1`.
- TLS 1.3 is required. Peer, coordinator, enrollment, audit, and administrative
  routes require mutually authenticated service certificates pinned by deployment
  configuration. Client-facing nonce and TPASS routes require server-authenticated
  TLS and the specified client-proof-key-bound admission context.
- Requests and responses use `application/json`; exact object key sets are
  required. Unknown, duplicate, missing, or type-coerced fields are rejected.
- Cryptographic protocol objects are their canonical binary encodings represented
  as unpadded base64url. They are decoded only after the JSON body passes bounds.
- `bid` is 16 bytes as 32 lowercase hexadecimal characters. `sid`, digests,
  nonces, and certificate identifiers are 32 bytes as 64 lowercase hexadecimal
  characters. Epoch and log indices are JSON integers in `[1, 2^63-1]`, except
  genesis log index `0`. Party identifiers are integers in `[1, 255]`.
- A request body is at most 1 MiB; an individual encoded TPASS object is at most
  256 KiB; collection counts are checked before allocation. Deployment may set
  tighter bounds but not silently accept a wider paper-facing profile.
- Every mutating request carries `Idempotency-Key`, a 32-byte value encoded as
  lowercase hex. A general client generates and durably retains a random value;
  the current coordinator derives it with domain separation from its enrolled
  certificate fingerprint, target party, exact route, and canonical request
  envelope so a reconstructed coordinator can retry deterministically. The
  durable party-local key maps to the authenticated certificate fingerprint,
  method, exact route, and canonical request digest. Exact completed reuse
  returns the stored HTTP status and response bytes; changed reuse is a conflict.
- Success responses include `api_version`, `request_id`, and a stable result
  object. `request_id` is diagnostic correlation data and is never an attempt or
  cryptographic identifier.

Raw cues, canonical cue descriptors, resolver results, TPASS passwords, client
blinders, whole secrets, wrapping/private keys, raw admission capabilities, and
raw client proof material never appear in response bodies, status, audit
output, or ordinary logs.

### Implemented idempotency and replay bindings

| Operation | Durable request binding | Stored result / replay behavior |
| --- | --- | --- |
| `POST /v1/ledger/entry-votes` | caller, route, canonical entry | Exact vote bytes; a changed entry under the key conflicts before dispatch. |
| `POST /v1/ledger/install-votes` | caller, route, canonical prepare certificate | Exact install-vote bytes; certificate replay is also checked by the signed ledger state. |
| `POST /v1/ledger/authorization-certificates` | caller, route, canonical authorization certificate | Exact install result; semantic retry maps to the same ledger entry and slot. |
| `POST /v1/ledger/freshness-votes` | exact party caller, route, canonical freshness request | Exact signed freshness vote; caller/party or nonce changes conflict. |
| `POST /v1/recoveries/{sid}/commitments` | coordinator caller, route including `sid`, certificate, request, selected set | Exact phase identifier and commitment bytes; cross-session, epoch, request, selection, or certificate reuse conflicts. |
| `POST /v1/recoveries/{sid}/responses` | coordinator caller, route including `sid`, phase, request, selected set, commitment transcript | Exact response bytes; a changed or delayed cross-transcript replay conflicts. |

`POST /v1/ledger/state-summaries` is read-only and intentionally has no key.
The canonical request digest carries the backup/epoch/protocol fields present in
the signed objects and body; the target party is implicit in its independently
owned database and explicit in the coordinator's derived key. One exclusive
party process owns a database at a time. Same-boot concurrent duplicates receive
`request_in_progress`; process startup changes unfinished HTTP records to
retryable before accepting traffic. Lower ledger/phase idempotency then decides
whether the exact operation returns stored data or fails closed.

The current slice deliberately keeps completed records indefinitely so a retry
cannot age into fresh execution. A bounded, epoch/lifecycle-aware compaction
policy and authenticated-request storage quota are not implemented; until they
are, an enrolled caller can grow a party database with unique failed requests.
Compaction must never delete the underlying counted ledger/phase binding or make
a completed key executable again.

### P5A.3/P5A.4 aPPSS component routes

P5A.3 adds the separate component route
`POST /v1/recovery-suites/appss/evaluations`. It accepts exactly one bounded
canonical `LOCUS-APPSS-request-v1` body over TLS 1.3 after mutual-certificate
authentication and returns exactly one `LOCUS-APPSS-response-v1` body. Both
client and server certificates are pinned by SHA-256 fingerprint. The route
does not accept Yi objects, a suite preference list, client-session state, raw
cues, or an exported OPRF key.

P5A.4 adds `POST /v1/recovery-suites/appss/initializations` for the exact
`operation=initialize` request and
`POST /v1/recovery-suites/appss/state-installs` for the exact P5A.1 install
object. A clean service boot file contains the public backup, epoch, CuePolicy,
membership, threshold, configuration, suite/profile, and certificate identity
bindings. The service recomputes their context digest and rejects any mismatch
before accepting traffic. Each holder creates its own OPRF key after its first
authenticated initialization request; the client never receives that key.

Each process opens one holder-bound SQLite database. The database contains only
that holder's pending or installed P5A.1 state, public `omega`, exact request
hash/bindings, authorization-grant digest, and stored response. It commits the
authorization metadata before invoking the secret-dependent OPRF evaluation.
Exact request retry returns the durable response after restart; changed reuse,
wrong recipient/context/suite/omega, malformed group input, and use before
state installation fail closed. The transient client validates the complete
response binding before finalization and normalizes wrong input and remote
protocol errors.

Every mutating aPPSS component call first commits a transport record binding the
authenticated client-certificate digest, exact `/v1` route, idempotency key,
and body digest. An exact completed response survives restart; changed caller,
route, or body reuse conflicts. The client creates the common public state only
after all three OPRF responses and returns an initialization result only after
all three exact ready acknowledgements. Partial installation does not publish
or activate a descriptor-bound epoch.

These are component boundaries, not the released party API or a new
deployment/evidence profile. P5A.5 must integrate descriptor-bound new
enrollment and successor switching. The existing Yi
ledger/commitment/response API and retained deployment are unchanged.

## Common error contract

Unauthenticated or client-facing failures return one of two coarse bodies:

```json
{"api_version":"locus-party-api-v1","error":"recovery_rejected","request_id":"..."}
```

```json
{"api_version":"locus-party-api-v1","error":"service_unavailable","request_id":"..."}
```

Wrong cues, unknown backup, admission failure, stale/malformed certificates,
TPASS proof failure, policy mismatch, and retired state are externally normalized
to `recovery_rejected`. A clearly pre-password infrastructure outage may return
`service_unavailable`, subject to timing/error-oracle tests.

Authenticated peer/operator calls additionally use stable internal codes such as
`invalid_message`, `not_ready`, `head_mismatch`, `slot_conflict`,
`certificate_missing`, `session_lost`, and `failed_closed`. Bodies never include
secrets, token claims, raw signatures beyond the requested certificate object, or
database/stack traces. HTTP status codes express transport/API class; clients must
not infer cue correctness from them.

## Enrollment API

Enrollment is a two-step, idempotent provisioning operation so partial delivery
does not expose an active party with an uncertified genesis.

### `POST /v1/enrollments/prepare`

Caller: authenticated provisioning coordinator.

Input `EnrollmentPackage` contains:

- `api_version`, `bid`, `epoch = 1`, and this `party_id`;
- canonical TPASS public parameters and only this party's canonical secret state;
- `recovery_id_digest`, backup-object reference, and backup digest;
- cue-policy, security-policy, admission-policy, and TPASS-parameter digests;
- complete proposed `AttemptConfig`, administrator verification policy, and
  coordinator/peer identity pins;
- expected schema/software compatibility bounds.

The party validates all encodings and cross-digests, rejects another party's
state, and transactionally stores the package as `PREPARED`, inaccessible to
recovery routes. It returns a signed `EnrollmentReady` digest. It never receives
the encrypted private-key object, cues, password, group secret, or wrapping key.

### `POST /v1/enrollments/activate`

Caller: authenticated provisioning coordinator.

Input contains the exact package digest, a genesis configuration certificate,
and the required distinct `EnrollmentReady` statements. The party verifies the
configured quorum and transactionally changes the epoch to `ACTIVE` with
`consumed = 0`, `B_eff = B`, and certified log index `0`. Exact retry returns the
stored activation result. Conflicting activation enters `FAILED_CLOSED`.

There is no remote endpoint that exports secret TPASS state or deletes an active
epoch. Test fixtures provision synthetic state through the same contract.

## Admission and attempt-ledger API

### `POST /v1/admission/nonces`

Caller: client or coordinator relay over server-authenticated TLS.

Input contains only the syntactically bounded `bid`, `epoch`, `sid`, and
`request_digest`. The party returns a short-lived party-specific proof nonce and
opaque handle. This route is independently throttled and does not mutate the
attempt ledger.

### `POST /v1/ledger/state-summaries`

Caller: mutually authenticated coordinator or active peer.

Input identifies `bid`, epoch, configuration, and the caller's known head. The
party returns a signed privacy-minimized summary of its latest installed head and
next-slot lock state. It may return required missing certificates, subject to
bounded pagination. A missing party is never interpreted as an empty slot.

### `POST /v1/ledger/entry-votes`

Caller: configured coordinator over mutual TLS.

Input contains one canonical proposed entry, predecessor certificate, and, for an
`ATTEMPT`, the party-specific D004 capability and client proof plus nonce handle. The
party validates admission independently, persists its replay record and durable
slot lock in one transaction, and only then returns the stored `EntryVote`. An
exact retry returns the same vote. A conflicting slot or `sid` returns no
signature.

### `POST /v1/ledger/install-votes`

Caller: configured coordinator or active peer.

Input contains a complete `PrepareCertificate`. The party validates it against
its durable lock, stores the certificate and install-vote input transactionally,
and only after commit returns `InstallVote`.

### `POST /v1/ledger/authorization-certificates`

Caller: configured coordinator or active peer.

Input contains a complete `AuthorizationCertificate`. The party verifies both
quorums and chain continuity and installs every required certificate in order in
one or more atomic transitions. For an `ATTEMPT`, successful assembly of the
certificate is the global counted-attempt commit point; local installation is a
precondition for this party's TPASS work. Conflicting valid certificates force
`FAILED_CLOSED`.

### `POST /v1/ledger/freshness-votes`

Caller: active party over peer mutual TLS, never the client or coordinator.

Input contains the installed authorization-certificate hash, request digest,
responding party, TPASS phase `commitment`, and fresh `boot_nonce`/`response_nonce`
commitments. The authorizer reconciles current state and signs only if the exact
attempt remains on the canonical chain and the epoch/configuration is permitted.
The vote cannot authorize another party, phase, boot, nonce, or request.

Ledger certificate and catch-up responses are bounded and paginated. No route
permits unlocking, decrementing `consumed`, resetting a budget, filling an
ambiguous slot with another entry, or accepting a coordinator-only decision.

## TPASS recovery API

The public recovery path has two protocol phases. Both are idempotent for one
`(bid, epoch, sid, request_digest, party_id)`.

### `POST /v1/recoveries/{sid}/commitments`

Caller: client or coordinator relay after attempt authorization.

Input contains:

- `bid`, epoch, `request_digest`, and canonical client-request bytes `A`;
- sorted distinct selected TPASS party identifiers;
- the complete `AuthorizationCertificate` for this `sid` and exact `A`;
- no client-supplied freshness certificate.

The party performs this order:

1. validate request bounds, selected set, certificate, request digest, and local
   party membership;
2. install any missing certificate chain and reconcile current lifecycle state;
3. use the process-start `boot_nonce`, generate a fresh volatile `response_nonce`,
   and obtain `q_a` peer freshness votes for its own `commitment` phase;
4. transactionally persist the phase idempotency record, selected set,
   authorization/freshness digests, and response intent;
5. only after the transaction commits, call Rust `prepare_commitment`, then store
   the canonical `PartyCommitment` and random opaque `phase_instance_id` before
   returning them. The secret `PartyEphemeral` remains only in locked memory.

Step 5 is the first secret-dependent TPASS operation. No commitment may be
computed speculatively, cached before certification, or released from a rolled-
back process that cannot obtain current freshness.

If a crash occurs after the response intent commits but before the commitment is
durably stored, startup marks the phase lost and never recomputes it. The native
`PartyEphemeral` deliberately has no external serialization. It remains
in locked process memory, keyed by `phase_instance_id`, and is erased after the
response or expiry. If the process restarts after returning a commitment but
before persisting the final response, the exact phase returns `session_lost` and
does not generate a second commitment. The counted attempt remains consumed. A
new password request requires a new `sid`, blinded request, and counted entry.
This fail-closed baseline preserves the protocol boundary at an explicit crash-
availability cost; later encrypted ephemeral persistence requires a separate
cryptographic review and plan change.

If the HTTP result containing a commitment was already completed before restart,
an exact HTTP retry still returns those same stored bytes. This does not revive
the volatile `PartyEphemeral`: any response step that was not already completed
fails with `session_lost`, and no second commitment or attempt slot is created.

### `POST /v1/recoveries/{sid}/responses`

Caller: client or coordinator relay.

Input contains the exact `phase_instance_id`, client request, sorted selected set,
and all selected canonical party commitments. The party verifies equality with
its stored request and own commitment, calls Rust `verify_and_respond`, and
transactionally stores the canonical response bytes before releasing them. Exact
retry returns the stored response. Changed commitments, selection, request,
certificate, or phase instance are rejected. After the response and a bounded
retry-retention interval, secret ephemeral state is erased while the response
digest/idempotency record remains durable.

A party never receives the client's final TPASS aggregate, recovered group
secret, wrapping key, ciphertext plaintext, or final success bit.

## Lifecycle and administrative API

Lifecycle changes use the same ledger vote/install routes, with exact
administrator evidence and entry types from the P5 state machine:

- `BUDGET_EXTENSION` increases disclosed `B_eff` within policy; no reset exists.
- `CONFIG_PREPARE` carries the current head and migration snapshot digest.
- `POST /v1/configurations/readiness` lets a proposed new party import only its
  own provisioned share/configuration, validate the certified head/consumed/budget
  snapshot, and return a signed readiness statement.
- `CONFIG_ACTIVATE` requires the specified old/new joint certificates before the
  new configuration can vote or respond. Retired party identities become invalid.
- `RETIRE_EPOCH` is irreversible. After installation, admission, voting,
  freshness, and TPASS routes reject the epoch.

`POST /v1/admin/actions/validate` is an authenticated diagnostic route that checks
canonical administrator signatures and current-head binding without changing
state. It never substitutes for a certified ledger transition. There are no
ordinary remote delete, rollback, secret export, force-unlock, or counter-edit
routes.

P4.9.3 freezes three strict coordinator-only pinned-mTLS mutations:
`POST /v1/lifecycle/epoch-approvals`,
`POST /v1/lifecycle/epoch-preparations`, and
`POST /v1/lifecycle/epoch-activations`. Every call uses the existing exact HTTP
idempotency binding. Preparation carries only the recipient party's canonical
native state (or an explicit authorizer-only marker), persists it atomically
with the successor ledger package, and returns a readiness signature over that
exact runtime-package digest. Activation selects the epoch-bound authorizer
configuration and runtime state; a prepared package cannot vote or respond.
Implementation and five-process verification now pass, including restart before
and after activation, 3/2 partial installation, retired-epoch refusal, and
successor native recovery. The disposable Compose profile is implemented but not
yet live-verified, and the public administrator authorization above remains
absent. See `docs/epoch-lifecycle.md`.

## Health, status, and audit API

### `GET /health/live`

Unauthenticated, coarse process liveness only. It exposes no backup identifiers,
party state, configuration, database status, or dependency detail.

### `GET /health/ready`

Mutually authenticated deployment health check. Reports only whether startup
reconciliation completed and whether the party is `READY` or `FAILED_CLOSED`.
It is never a recovery-validity oracle.

### `GET /v1/status`

Authorized operator route. Returns software/schema versions, party identity,
active epoch/configuration digests, certified head, `consumed`, `B_eff`, coarse
pending-lock state, certificate lag, and redacted dependency health. It never
returns TPASS state, individual recovery requests, subject/token data, ephemeral
state, or cue-related information.

### `GET /v1/audit/events?cursor=...&limit=...`

Authorized read-only auditor route with a maximum page size. Returns a hash-
chained sequence of privacy-minimized events: enrollment/configuration digest,
ledger transition digest/type/index, coarse admission result, TPASS phase result,
restart/reconciliation result, lifecycle action, and software/schema version.
Requests are identified only by scoped digests. Raw credentials, network
addresses, free-form text, and cryptographic secrets are forbidden. Audit data is
evidence and detection support, not a substitute for authorization safety.

## State-machine invariants

1. No first-phase vote leaves a party before its admission replay record and
   unique slot lock commit.
2. No install vote leaves before the full prepare certificate commits.
3. No authorization certificate is accepted without both valid `q_a` quorums and
   exact predecessor continuity.
4. No honest party calls `prepare_commitment` before local authorization install,
   current freshness quorum, and durable phase intent.
5. One `sid` cannot bind two request digests; exact retries never consume another
   position or create another commitment instance.
6. No response share is released for a changed request, selected set, commitment
   transcript, party, epoch, configuration, or phase instance.
7. Restart/rollback without reconciliation to the independent witnessed checkpoint cannot vote or respond; party-quorum summaries alone are not authoritative freshness evidence.
8. Lifecycle changes preserve the certified head, `consumed`, and `B_eff`; retired
   epochs and identities never reactivate.
9. Each process and database can access only its party's secret state and keys.
10. Normal APIs and logs reveal no prohibited cue, password, share, whole-secret,
    wrapping-key, private-key, or raw credential material.

## Failure behavior

- Bounds, parsing, authentication, and admission failures occur before ledger
  mutation and return no vote.
- Database commit/synchronization failure returns no signature or TPASS message.
- Crash ambiguity, conflicting locks/certificates, unavailable freshness quorum,
  and unrecoverable ephemeral state fail closed; they never restore budget.
- Coordinator loss is recovered from party votes/certificates. It may reduce
  liveness but cannot authorize alone.
- A slow/malicious party is timed out by the caller. Honest parties never weaken
  quorum or selected-set validation to compensate.
- Public errors remain generic. Authenticated operator detail is coarse and
  redacted; stack traces stay local and disabled in the artifact profile.

The implemented P4.8 caller policy is frozen in
`docs/party-failure-policy.md`. Remote calls make at most two byte-identical
deliveries under the same idempotency key and retry only transport-ambiguous
outcomes. Authorization phases collect concurrently under ten-second phase and
45-second operation deadlines. The TPASS set is chosen from quorum-consistent
state before authorization and then remains fixed; a selected-party failure
after authorization aborts generically and leaves the attempt consumed.

## Test plan

- Schema/bounds tests for every route, unknown fields, oversized bodies and
  collections, invalid base64url/hex, type coercion, and certificate bombs.
- Mutual-TLS role/identity tests and client D004 nonce, audience, endpoint,
  replay, expiry, subject, and request-binding tests.
- Idempotency tests for every mutating route and changed-payload key reuse.
- Crash injection before/after every admission, lock, vote, certificate install,
  response-intent, commitment, and stored-response boundary.
- Concurrent conflicting proposals, rotating TPASS subsets, coordinator restart,
  response replay, and malicious selected/commitment transcript tests.
- Database and whole-party snapshot rollback with surviving current peers;
  coordinated rollback is recorded as outside the detection assumption.
- Budget `B-1`, `B`, `B+1`, extension, joint replacement, and retirement tests.
- Cross-party filesystem/database access tests and recursive secret/log/trace
  inspection.
- External error/timing/size comparison for wrong input, malformed messages,
  unknown backup, policy mismatch, and stale state.

## Evaluation plan

Record enrollment and both recovery-phase latency, authorization/freshness quorum
latency, durable writes/fsync cost, bytes per role, certificate/storage growth,
throughput, CPU/memory, crash recovery, and availability separately for TPASS
threshold `t` and authorizer quorum `q_a`. Report distributions, not only means,
under Compose and separate-VM profiles. Measure fail-closed loss from the volatile
ephemeral rule and compare the exact-budget cost with a clearly labeled
non-paper-facing local baseline.

## Paper implications and implementation sequence

This contract supports future-tense wording that LOCUS is designed to count an
attempt before its first secret-dependent TPASS commitment. The implemented
sub-profile now supports the narrower statement that signed attempt/freshness
certificates and native TPASS recovery messages can be assembled across
authenticated local processes with per-party secret state and separate durable
databases. It does not support a present-tense claim that the system is
independently deployed, rollback-resistant, admission-controlled, or globally
rate-limited.

As of 2026-07-22, `prototype/locus/party_store.py` transactionally locks entry
votes, persists prepare certificates before install votes, verifies a complete
authorization certificate, and stores phase intent before
`prototype/locus/party_service.py` invokes native `prepare_commitment`. It uses
SQLite foreign keys, WAL, `synchronous=FULL`, unique session/slot constraints,
monotonic local heads/counts, stored commitment/response idempotency, durable
caller/method/route/body HTTP bindings, and hash-chained redacted events. Schema
v5 additively migrates earlier schemas and persists exact successor runtime
packages. Tests cover guarded native recovery, restart loss of a volatile phase,
exact retry, budget exhaustion, malformed authorization, concurrent conflicts,
and direct-successor preparation/activation.

That slice verifies canonical Ed25519 votes/signatures, a safe 4-of-5 attempt
quorum, and response-freshness certificates bound to party-generated boot/response
nonces. `prototype/locus/party_http.py` exposes state summary, entry vote, install
vote, authorization-certificate install, freshness vote, native commitment, and
native response operations. It requires TLS 1.3, CA verification, exact
client/server certificate pins, bounded JSON bodies, exact/duplicate-free
schemas, canonical unpadded-base64url TPASS objects, generic errors, and
client-side verification of every returned signature. The collector still owns
no authorizer key. Coordinator and `party:<id>` certificates have distinct route
permissions; only the exact responding-party identity can request its freshness
votes. Each TPASS process loads public parameters plus its own secret state only.

The current adapter is deliberately narrower than the frozen final contract:
configuration is provisioned by a trusted synthetic bootstrap rather than a
public enrollment/admission flow, and health remains on the mutually
authenticated listener. Every implemented mutating POST requires a strict HTTP
idempotency key and stores the exact completed result before release. Party
schema v5 binds the backup/configuration digest, signed attempt state, and exact
active runtime epoch package. The default Compose path combines these parties
with the S3-compatible adapter and disjoint volumes; the lifecycle Compose
scenario passed with a party restart and complete cleanup. D004 admission,
administrator authorization, rollback anchors, certificate lifecycle management,
and broad
malicious-network scheduling remain absent.

The five-process tests complete correct and counted-wrong-input recovery,
continue with one process unavailable, catch it up after restart, map exact
retries to stored bytes, reject cross-session replay, lose non-serializable
phases closed without restoring budget, activate a direct successor through
old/new quorums, reconstruct its native state after restart, reject the retired
predecessor, and recover under epoch two. Thus they establish
process/database/state separation, authenticated transport, pre-commitment
accounting, and selected lifecycle/crash/availability behavior for one host
only; they must not be reported as the P5 global bound, rollback resistance,
independent-operator evidence, or a practicality result.

The following items are future extensions, not scoped Cycle 1 gates:

1. public-client D004 local-issuer admission and replay protection;
2. an independent monotonic witness, witness-receipt validation, and party-history reconciliation;
3. broader formal state-machine exploration plus systematic interleaving/crash tests;
4. general party replacement and administrator authorization;
5. privacy-minimized audit export and adversarial evaluation; and
6. a security argument and measured deployment overhead matching the claim.
