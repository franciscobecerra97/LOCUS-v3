# LOCUS Distributed Attempt-Control Property

Status: P5.1 future security-property definition, updated 2026-07-22 after the scope reduction. This document records the former complete target and its assumptions so partial implementation facts are not confused with a security claim. P5.13 found a compact-profile counterexample showing that party-quorum reconciliation can fork after one honest database restore when another honest party never installed the latest certificate; `docs/attempt-control-model.md` records the bounded result. The current prototype implements a partial signed-ledger, responding-party freshness, guarded native-TPASS slice, durable HTTP retry/replay binding, and a same-membership lifecycle slice. The scoped paper does not require or claim the rollback anchor, public-client admission, general replacement, systematic global schedules, or complete security argument.

## Problem Statement

TPASS moves cue guessing from an offline snapshot attack to an online threshold protocol, but TPASS alone does not limit how many online candidates a client can test. Independent per-party counters are insufficient: an attacker can rotate threshold subsets, race concurrent checks, replay messages, exploit retries/crashes, or restore old party snapshots.

LOCUS needs a system-wide attempt property for one active backup epoch. The property must remain meaningful when up to the stated number of parties are malicious, when clients are malicious, and when honest parties crash or retry. It must also state when safety is preserved at the cost of availability.

## Parameters And Terms

- `n`: number of enrolled TPASS recovery parties.
- `t`: TPASS reconstruction threshold.
- `f_t`: maximum compromised TPASS parties covered by confidentiality claims; `f_t <= t-1`.
- `f_a`: maximum Byzantine attempt-authorizers covered by attempt-log safety.
- `q_a`: attempt-authorization quorum size.
- `bid`: backup identifier.
- `epoch`: monotonically identified enrollment/recovery epoch.
- `B`: configured base attempt budget for `(bid, epoch)`.
- `X`: sum of explicit quorum-authorized budget extensions, if administrative recovery permits any.
- `B_eff = B + X`: effective disclosed budget used in the guessing bound.
- `sid`: globally unique recovery session identifier.
- `A`: the TPASS blinded client request for one password attempt.
- `request_digest`: domain-separated hash of protocol version, `bid`, `epoch`, recovery identity, `sid`, and canonical encoding of `A`.
- `authorization entry`: a uniquely sequenced, durable decision binding one `request_digest` to one budget position.
- `authorization certificate`: evidence accepted by honest parties that an authorization entry was committed under the active attempt-control configuration.
- `attempt head`: the latest committed sequence number and hash-chain value for the epoch.

The recovery parties are the selected baseline attempt-control authorizers. An optional coordinator may sequence proposals and collect certificates but has no authorizer key or independent authorization power. Neither role may silently become a recovery custodian or receive cue/password/private-key material.

## One Counted Attempt

A counted attempt is created when an authorization entry for a previously unseen `(sid, request_digest)` is durably committed, before any honest recovery party emits its first secret-state-dependent TPASS message for that request.

The entry consumes one budget position even if:

- the client disconnects or withholds later messages;
- fewer than `t` parties ultimately respond;
- the password is correct;
- the request fails for a malformed later message;
- a party or client crashes;
- the cloud object is unavailable after authorization;
- the client never reports the final TPASS or AEAD outcome.

This conservative point is necessary because parties do not reliably learn whether the client accepted the final result. Admission failures that occur before a certificate is committed and before any secret-dependent party message are not counted, but they must be separately rate-limited to resist admission-layer denial of service.

## Distinct Evaluation Binding

One authorization certificate is valid for exactly one canonical `request_digest`. Honest parties reject it if `A`, `sid`, `bid`, `epoch`, recovery identity, protocol version, or policy/configuration binding differs.

Retries carrying the identical `(sid, request_digest)` are the same counted attempt. A different `A`, a different `sid`, or a different bound field requires a new authorization entry. Each honest party persists idempotency state before responding so duplicate delivery cannot cause an unintended new reservation or a response under a different transcript.

At the implemented HTTP boundary, every mutating call additionally binds one
32-byte idempotency key to the authenticated caller certificate, method, exact
route, and canonical request-envelope digest before dispatch. Completed retries
return the exact stored status/body bytes. Changed caller, route, session, phase,
epoch, request, selection, or commitment fields conflict before protocol state is
re-entered. An interrupted HTTP record is retryable only after exclusive process
restart; the lower durable ledger/phase record then returns the same result or
fails closed. This layer does not provide DPoP admission replay protection and
does not add rollback resistance.

The implemented P4.8 transport policy retries only transport-ambiguous outcomes,
at most once, with the byte-identical body and same idempotency key. Protocol
faults and durable conflicts are not retried. Authorization calls run
concurrently under a ten-second phase deadline and one 45-second operation
deadline. A timeout never proves that remote durable work was cancelled: exact
retry and ledger reconciliation remain authoritative. The client fixes one
quorum-consistent TPASS subset before authorization; it never switches subsets
after the certificate commits, and any later failure leaves the attempt
consumed. See `docs/party-failure-policy.md` for the complete contract and
limitations.

The TPASS request `A = r*G1 - pw_attempt*G2` computationally binds the client to one attempted password without revealing it, assuming the discrete-log relation between `G1` and `G2` is unknown. Reusing a certificate with a different password request therefore requires a changed `A` and is rejected by the digest binding.

## Target Safety Property

### Global distinct-attempt bound

For any probabilistic polynomial-time adversary controlling clients, the cloud/relay, the network, and at most the stated faulty parties/authorizers, the number of distinct request digests for one `(bid, epoch)` that obtain enough accepted TPASS responses to evaluate a candidate is at most `B_eff`, except with negligible cryptographic probability.

The stronger operational invariant is that at most `B_eff` distinct authorization entries can be certified, whether or not they reach threshold evaluation. Thus abandoned and failed sessions can reduce availability but cannot increase the guessing budget.

### Zero-overrun target

The target safety overrun is zero: concurrency, subset rotation, retry, replay, and crash do not authorize sequence numbers beyond `B_eff` and do not create two different certified entries for the same sequence position.

The selected P5.3 mechanism retains the zero-overrun target. If P5.2 or implementation analysis instead finds a nonzero bounded overrun, this document, the claim-evidence matrix, tests, analytic bound, and paper must be changed to the measured/proved bound `B_eff + omega`. No implementation may be described as globally bounded while `omega` is unknown.

### From authorization to TPASS enforcement

Every honest TPASS party verifies the authorization certificate and request binding before its first secret-dependent response. Because at most `t-1` TPASS parties are compromised, every set of `t` accepted TPASS responses contains at least one honest party. Therefore, a threshold result cannot be obtained for an uncertified request unless the TPASS threshold assumption is already violated.

## Authorization-Quorum Assumption

For a quorum-certificate realization over `n` authorizers with at most `f_a` Byzantine authorizers, require:

`2*q_a > n + f_a`.

This ensures that any two authorization quorums intersect in more than `f_a` members and therefore contain at least one honest common member. An honest authorizer durably records a signed/accepted entry before releasing its authorization contribution and never authorizes two different entries for the same sequence position or predecessor.

Safety and liveness are separate:

- safety requires quorum intersection, signatures, durable local history, and an independent non-equivocating monotonic checkpoint that survives party-database rollback;
- progress requires at least `q_a` responsive authorizers that will follow the protocol;
- tolerating all `f_a` Byzantine authorizers as unavailable additionally requires `q_a <= n-f_a`, which may not be achievable for every `(n, f_a)` choice;
- when safety and progress conflict, honest parties fail closed and recovery can be denied.

Example: for `n=5` and `f_a=2`, `q_a=4` satisfies safety intersection, but the three honest authorizers cannot make progress if both Byzantine authorizers refuse. This limitation must be reported; TPASS's 3-of-5 availability does not automatically imply attempt-authorization availability.

The selected recovery-party ledger uses this quorum-certificate rule. Any later replacement must provide an equivalent non-forking authorization abstraction and state its trust/availability tradeoff explicitly.

## Required Invariants

1. **Epoch binding:** every entry and certificate is bound to exactly one active `(bid, epoch)` and attempt-control configuration.
2. **Sequential uniqueness:** one sequence number has at most one certified entry.
3. **Hash-chain continuity:** entry `j` commits to the certified head of `j-1`; forks are rejected.
4. **Budget monotonicity:** ordinary recovery never decreases the committed sequence or increases `B_eff`.
5. **Pre-response durability:** authorization and party idempotency state are durable before a secret-dependent message leaves an honest process.
6. **Request binding:** a certificate cannot authorize a different TPASS request or recovery identity.
7. **Subset independence:** authorization is global to the epoch, not scoped to one threshold subset.
8. **Idempotent retry:** exact retry returns the stored decision/state or resumes the same session without another budget position.
9. **Replay rejection:** retired epochs, expired configurations, altered requests, and previously completed/aborted sessions cannot be replayed as fresh.
10. **Fail-closed inconsistency:** conflicting heads, missing durable state, unverifiable certificates, or uncertain rollback state cause refusal or administrative recovery, never counter reset.
11. **No correctness report dependency:** counting does not depend on the client reporting password/decryption success.
12. **Privacy-minimized audit:** entries contain request/session bindings and policy evidence, not cues, password scalars, party shares, recovered secrets, wrapping keys, or private keys.

## Concurrency, Crash, And Retry Semantics

Concurrent proposals are serialized into unique sequence positions by the chosen authorization mechanism. A proposal that loses a conflict either receives no certificate or is assigned a different still-available position; the system never certifies two entries at the same position.

Crash points must be tested before and after:

1. proposal receipt;
2. durable local reservation;
3. authorization contribution/signature release;
4. certificate assembly;
5. certificate persistence;
6. party idempotency persistence;
7. first TPASS commitment/proof message;
8. final party response;
9. client aggregation and completion.

After restart, a party or authorizer recovers the durable session and head. It may resume or reproduce only the same bound transcript. If it cannot determine whether a reservation/certificate was committed, it fails closed or reconciles with a valid higher quorum certificate. Ambiguity may consume budget but may not restore it.

## Replay Semantics

- Replaying the same certificate and exact request is an idempotent retry, not a new guess.
- Replaying an exact completed mutating HTTP request returns its stored bytes,
  including after process restart; a changed reuse of the key is rejected before
  dispatch.
- Replaying a certificate with modified fields is rejected.
- Replaying a response under another session, party set, backup, epoch, or protocol version is rejected by transcript binding.
- Replaying an old-epoch certificate after retirement is rejected even if it was valid historically.
- A party responds at most according to its persisted state for one `(sid, request_digest)`; response regeneration must not create a different authorized request. A stored commitment may be redelivered after restart, but a lost volatile TPASS ephemeral is never reconstructed, so an unfinished response phase fails closed while the attempt stays consumed.

## Rollback Property And Limit

Quorum intersection protects a durable honest lock, but party-quorum reconciliation alone is not rollback resistance. The P5.13 bounded model produces conflicting 4-of-5 slot-one certificates after only one honest database restore: a different honest party may still be at the predecessor because certificate dissemination is not atomic, and those two stale honest views plus two Byzantine summaries form another quorum.

A full P5.9 solution would require an independently administered, strongly consistent monotonic witness. A usable authorization would be a party-quorum certificate plus a witness compare-and-set receipt advancing the exact prior `(bid, epoch, config_digest, head, status)` checkpoint. Every authorizer would consult the witness before voting, freshness, or TPASS response; a rolled-back node would catch up to the witnessed head or fail closed. Party summaries remain certificate-retrieval evidence, not the rollback authority. The scoped paper does not implement this architectural extension and makes no rollback-resistant global-bound claim.

The mechanism must detect or fail closed for:

- one party database restored to an earlier head;
- several parties restored while a sufficient current quorum survives;
- old container volumes reintroduced;
- cloud objects and party state restored to different epochs;
- a replacement party initialized from stale state.

LOCUS cannot claim detection if the independent witness and every party are rolled back or if the witness equivocates. The witness is a new safety/availability and metadata-correlation dependency: outage blocks recovery work, and compromise may restore or fork budget. This is an explicit trust tradeoff, not an implementation detail. The current model idealizes the witness; no runtime anchor is implemented yet.

## Party Replacement And Configuration Change

A replacement party cannot authorize or answer until it has authenticated the current attempt head, remaining budget, epoch, configuration, and retirement set. Configuration change creates a quorum-certified transition that carries forward the consumed budget and hash-chain head. Retired identities are invalid under the new configuration.

Replacement, re-sharing, or container recreation must never initialize an active epoch with a zero counter merely because local storage is absent.

## False Lockout And Budget Extension

Ordinary recovery has no counter-reset operation. A false-lockout procedure may choose one of two explicit outcomes:

1. recover through a separate out-of-band process and create a fresh backup/key epoch; or
2. issue a quorum-authorized, auditable budget-extension entry that increases `X` by a disclosed amount.

The analytic success bound must use `B_eff = B + X`. Administrative extensions must not be hidden or described as preserving the original `B`. Authorization of an extension introduces administrative trust and denial-of-service tradeoffs that P5.4 must document.

## Recovery-Request Authorization And Lockout Abuse

The attempt bound limits guesses even if an attacker can spend the whole budget, but it does not by itself prevent a third party from locking out the user. Before reserving a scarce attempt, the deployment must require a recovery-request authorization signal stronger than knowledge of a public account or backup identifier.

P5.4 defines the credential, challenge, privacy leakage, lost-device behavior, revocation, and abuse assumptions in `docs/recovery-authorization.md`. Ordinary admission uses an audience-restricted OIDC access token sender-bound with DPoP; high-impact actions additionally require enrollment-pinned threshold administrator signatures and policy bounds. Pre-authorization requests require separate throttling. These mechanisms gate attempts but are neither cue-password verifiers nor capabilities to reconstruct the private key.

## Security Argument Shape

The final P5.15 argument must establish:

1. certificate unforgeability and request binding;
2. non-forking sequence uniqueness from the selected coordination assumption;
3. pre-response enforcement by at least one honest member of every TPASS threshold set;
4. idempotency under retry/replay;
5. crash consistency at every durable transition;
6. partial rollback detection under the independent monotonic-witness assumption;
7. budget preservation across replacement and epoch/configuration transitions;
8. the exact relationship between `B_eff` and the online guessing equation.

## Test Plan

At minimum, execute and report:

- sequential attempts at `B-1`, `B`, and `B+1` boundaries;
- all valid TPASS subset rotations;
- simultaneous requests against overlapping and disjoint subsets;
- same-session identical retry before/after every message;
- modified-request replay with the same certificate;
- old response/certificate replay across sessions and epochs;
- crash injection at every listed transition;
- rollback of one and multiple party/authorizer databases;
- global rollback demonstration recorded as an explicit limitation unless externally anchored;
- malicious authorizer double-sign attempts and conflicting proposals;
- unavailable/slow authorizers and parties;
- party replacement from current and stale heads;
- explicit budget extension and false-lockout recovery;
- unauthenticated third-party lockout attempts;
- audit/log scans for prohibited secrets.

Tests must record the maximum observed certified entries, evaluated distinct request digests, temporary reservations, abandoned attempts, overrun, and recovery availability.

## Evaluation Plan

Measure:

- authorization latency and tail latency;
- synchronization/network bytes;
- durable writes and storage growth per attempt;
- throughput under concurrent requests;
- crash-recovery and reconciliation time;
- party/authorizer unavailability thresholds;
- rollback-detection overhead;
- false-lockout and abandoned-reservation frequency in synthetic scenarios;
- overhead added to total enrollment/recovery latency.

Results must distinguish authorization quorum `q_a` from TPASS threshold `t` and report configurations where attempt safety reduces recovery availability.

## Paper Claim Gate

Until the mechanism, tests, and security argument exist, the paper may say:

- TPASS makes residual cue testing online under its assumptions;
- LOCUS targets the property defined here;
- current local counters are scaffold behavior only;
- `min(1, B_eff*2^-h)` is a conditional bound if the premise is enforced.

The paper may not yet say that LOCUS recovery is globally rate-limited, rollback-resistant, durably auditable, concurrency-safe, replay-safe, or bounded across threshold subsets.

## P5.3 Selected Realization

P5.3 selected a quorum-certified, hash-chained attempt ledger replicated by the recovery parties. Request-bound one-use certificates are outputs of this ledger, and an optional coordinator is an untrusted sequencer/collector rather than an authorization authority. The comparison, quorum profiles, trust tradeoffs, protocol shape, and rejected alternatives are recorded in `docs/attempt-control-selection.md`.

P5.2 specifies the concrete proposal, durable vote/lock, two-phase certificate, reconciliation, pre-response freshness, retry, rollback, and joint-reconfiguration state machines in `docs/attempt-control-state-machine.md`. It deliberately forbids unsafe timeout unlock or slot reuse: an ambiguous partial proposal is completed as the same entry or the epoch fails closed. No implementation claim is unlocked by the specification alone.
