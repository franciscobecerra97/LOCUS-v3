# LOCUS Backup-Epoch And Re-enrollment Lifecycle

Status: P4.9 same-membership lifecycle implemented and live-verified in the
isolated Compose profile, 2026-07-22.

## Problem statement

Creating another active row for the same backup identifier would silently reset
the attempt count and make old-state replay ambiguous. Re-enrollment instead
needs an explicit, durable transition from one active epoch to its direct
successor. The transition must bind the old certified state and both backup and
authorizer configurations, keep the successor unusable while preparation is
partial, and make retirement irreversible at each honest party.

## Scope and threat assumptions

- This P4.9 slice keeps the party membership, public keys, fault bound, and quorum
  unchanged. Party replacement and counter migration remain P5.11.
- The compact profile has five authorizers, fault bound two, and quorum four.
- Old-authorizer signatures and new-party readiness signatures are
  unforgeable. Each honest store durably locks one transition per predecessor.
- Re-enrollment is an explicitly authorized creation of a fresh per-epoch
  attempt budget; it is not a reset of the predecessor. Public OIDC/DPoP and
  administrator authorization are still absent, so this is not yet a safe
  public re-enrollment API.
- A malicious client, coordinator, cloud, or minority of parties may replay,
  reorder, suppress, or cross-mix lifecycle objects. Coordinated rollback of all
  stores remains outside the implemented result.

## Canonical objects

`EpochTransition` binds:

- backup identifier and consecutive predecessor/successor epoch numbers;
- predecessor configuration and backup digests;
- predecessor installed head, consumed count, and effective budget;
- successor configuration and backup digests plus its disclosed fresh budget;
- lifecycle-policy version and a fresh 32-byte transition nonce.

An `EpochApproval` is an old-authorizer signature over the transition hash. A
`RuntimeEpochPackage` binds the transition, party identity, successor
authorizer configuration, and either no TPASS role or the hashes of the common
canonical public parameters and that party's canonical secret state. An
`EpochReady` statement signs both the transition hash and exact runtime-package
digest, and is emitted only after the ledger preparation and package bytes have
committed atomically. An `EpochActivationCertificate` contains at least the old
and new configured quorums, in canonical party order.

The public parameters and secret-state bytes never appear in readiness or
activation responses. A coordinator that provisions successor state necessarily
handles those bytes in this compact profile; they cross only the existing
pinned-mTLS channel and each party persists only its own state. This is a
bootstrap-authority limitation, not independent distributed key generation.

## State machine

1. `ACTIVE( j )`: ordinary attempts can be authorized only for epoch `j`.
2. `TRANSITION_LOCKED( j, j+1 )`: an old party has durably committed to one
   exact successor and may return only the same approval on retry. An unresolved
   attempt-ledger slot prevents this transition.
3. `SUCCESSOR_PREPARED( j+1 )`: the party has atomically stored the exact
   successor configuration, backup binding, runtime package, and readiness
   statement. Native encodings are parsed and the secret-state party identifier
   is checked before persistence. No epoch row exists for `j+1`, so voting,
   freshness, and TPASS routes cannot use it.
4. `ACTIVATED( j+1 )`: installing a valid activation certificate atomically
   changes epoch `j` to `RETIRED` and inserts epoch `j+1` as `ACTIVE` with
   genesis head, log index zero, and consumed count zero.
5. `RETIRED( j )`: new admission, votes, freshness, and commitments fail. The
   row, count, head, certificates, audit events, and immutable cloud object are
   retained as replay evidence rather than deleted.

There is no direct successor enrollment, reactivation, counter decrement, or
ordinary rollback transition. Exact activation retry returns the stored
certificate hash without changing either epoch.

## Partial installation and quorum behavior

Activation is atomic per party, not across all machines. During partial
delivery, a party exposes either the old active state or the new active state,
never both. With the frozen same-membership 4-of-5 profile, three transitioned
parties and two old parties cannot form either quorum. Once four parties install
the certificate, only the successor can form a quorum. This deliberately favors
safety over availability; a production coordinator still needs bounded retry,
reconciliation, and authenticated lifecycle transport.

An in-flight old attempt whose first secret-dependent message was already
authorized before retirement may finish under the existing narrow race rule;
retirement does not create another candidate evaluation. No new old-epoch
commitment can begin after the local status becomes `RETIRED`.

## Invariants

1. One backup identifier begins only at epoch one; every successor is exactly
   `j+1` and requires a certificate.
2. One honest party durably approves at most one transition from an epoch.
3. A prepared successor is not active and exposes no recovery route; its signed
   readiness binds the exact locally stored runtime-package digest.
4. Every activation preserves the predecessor's final head, count, budget, and
   backup/configuration bindings in the signed transition and retired row.
5. Activation never edits or deletes the predecessor count.
6. The successor begins at a new, explicitly disclosed per-epoch budget and
   zero consumed attempts; this reset is visible as re-enrollment, not mutation
   of the predecessor.
7. Old and new backup objects are immutable and keyed by distinct epochs.
8. Old/new cloud, party, certificate, or policy state cannot be cross-mixed
   without a digest, epoch, configuration, or transition mismatch.
9. Exact preparation and activation retries reproduce stored results; changed
   retries conflict.
10. Membership changes are rejected by this protocol and delegated to P5.11.

## Failure behavior

- Invalid, undersigned, duplicate, forged, nonconsecutive, stale-head, stale-
  count, stale-budget, or cross-mixed transitions are rejected before mutation.
- An unresolved old ledger slot prevents an approval.
- Missing local approval or preparation prevents activation.
- Missing, malformed, cross-party, or changed runtime-package bytes prevent
  readiness; changed exact-HTTP retries also conflict at the idempotency layer.
- A conflicting successor lock is durable and fails closed; it is never timed
  out or replaced locally.
- Fewer than four matching old or new parties cannot progress in the compact
  profile.
- A crash after preparation preserves the non-active package; reopening the
  database can install the same valid certificate.

## Authenticated service contract

All mutating lifecycle calls require the already pinned coordinator mTLS
identity, the normal 32-byte HTTP idempotency key, a strict API envelope, and an
exact request schema:

- `POST /v1/lifecycle/epoch-approvals` carries the transition and exact old/new
  authorizer configurations and returns one signed old-party approval.
- `POST /v1/lifecycle/epoch-preparations` additionally carries either `null`
  TPASS state for an authorizer-only party or canonical base64url public
  parameters plus only that recipient's canonical secret state. It returns one
  package-bound readiness statement.
- `POST /v1/lifecycle/epoch-activations` carries the canonical activation
  certificate and exact old/new configurations and returns only its hash.

Party identities may continue to call peer ledger/freshness routes but cannot
invoke lifecycle mutations. Exact retries reproduce stored response bytes;
changed reuse of an idempotency key conflicts. The server selects the
configuration and native service from the request's certified `(bid, epoch)`.
Prepared packages remain non-responsive. Activation drops any cached old
service, and restart reconstructs only an `ACTIVE` package.

## Current implementation and evidence

- `prototype/locus/epoch_lifecycle.py` defines strict canonical signed lifecycle
  objects and old/new quorum verification.
- Party database schema v5 adds durable transition locks, successor
  preparations, exact runtime-package persistence, and additive migration from
  the prior schema without weakening the existing epoch-status constraint.
- `PartyStore.enroll_epoch` now accepts only an initial epoch-one genesis.
- Store transitions durably approve, prepare, and atomically retire/activate;
  existing voting and TPASS guards reject retired epochs.
- Three coordinator-only pinned-mTLS routes enforce exact HTTP idempotency,
  validate each recipient's canonical native state before readiness, keep
  prepared packages non-responsive, select configuration/native state by
  certified epoch, and reconstruct only active state after process restart.
- `core.reenroll` creates a direct successor with the same backup identifier and
  fresh nonce, TPASS state, wrapping key, ciphertext, digest, and immutable cloud
  object.
- Deterministic tests cover successful re-enrollment/recovery, cloud/party
  cross-mixing, direct-activation refusal, exact retry, old-epoch refusal,
  insufficient old/new quorums during partial activation, conflicting replay,
  malformed quorum, restart before/after activation, role authorization, changed
  runtime packages, and successful successor native recovery across five party
  processes.
- `cross-epoch-runtime-mix-v1` packages the same transition into the existing
  Compose attack profile. It rejects post-preparation substitution with
  predecessor-context party state, pauses after activation so the host runner
  can restart party 1, refuses the retired predecessor, completes successor
  recovery, validates the exact report, scans output, and removes all resources.

## Remaining implementation work

- Public user/admin authorization, lifecycle idempotency retention/compaction,
  automated reconciliation, party replacement, and rollback anchors remain.
- The simple client helper regenerates a package if called again; a public client
  must durably retain and exactly retry one prepared package instead.

## Evaluation and paper implications

P7/P8 should measure preparation/activation latency, signed-object and persistent
storage growth, partial-installation availability, restart recovery, and old/new
object retention. Attack experiments must replay every lifecycle object, restore
old party/cloud snapshots, mix epochs/configurations, and vary certificate
delivery order.

This slice supports the narrow statement that authenticated same-host party
processes can durably prepare an exact direct successor, prevent partial
activation from forming either quorum, retire the predecessor, reconstruct active
successor state after restart, and complete successor recovery in the packaged
Compose profile. It does not support claims of party replacement, rollback
resistance, public lifecycle authorization, or a global attempt bound.
