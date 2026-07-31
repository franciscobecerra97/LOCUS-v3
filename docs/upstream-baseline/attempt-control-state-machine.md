# LOCUS Attempt-Control State Machine

Status: P5.2 aspirational protocol specification, updated 2026-07-22 after the scope reduction. This document refines the former P5.1 global property and records future design requirements. P5.5/P5.6 implement an SQLite-backed guard, canonical Ed25519 4-of-5 entry/install certificates, an untrusted coordinator, responding-party-bound live freshness, and native TPASS routes over pinned mutual TLS across five local processes/databases. P4.9.3 adds same-membership lifecycle handling. P5.13 disproves quorum-only rollback reconciliation in the frozen model. The scoped paper claims only exact tested local behaviors; rollback-aware reconciliation, public-client admission, general replacement, and a global security argument are future work.

## Scope

This specification defines:

- authorizer and coordinator states;
- ledger entries, votes, prepare certificates, and authorization certificates;
- exact durable transitions and the counted-attempt commit point;
- request binding, idempotency, concurrency, crash recovery, and partial rollback behavior;
- TPASS pre-response enforcement;
- epoch retirement, budget extension, and party/configuration replacement;
- fail-closed behavior for ambiguous or conflicting state.

P5.4 selects the user-facing recovery-admission and administrative mechanisms in `docs/recovery-authorization.md`. This protocol consumes independently validated OIDC/DPoP admission evidence and binds its stable policy/result to the request; the credential is not the cue-derived TPASS password.

## Roles And Fault Assumptions

- The **client** constructs the blinded TPASS request and verifies party responses.
- The **coordinator** validates the admission interface, serializes proposals, collects votes, assembles certificates, and resumes interrupted proposals. It has no authorizer signing key or TPASS share. It is trusted for ordinary liveness and privacy-minimized handling, but not for attempt-bound safety.
- Each **recovery party** is both a TPASS party and an **attempt authorizer**. It has one authorizer identity key, its TPASS state, and an independent durable database.
- A certificate requires `q_a` distinct active authorizers and satisfies `2*q_a > n_a + f_a`.
- At most `f_a` authorizers are Byzantine for attempt-ledger safety.
- At most `t-1` TPASS parties are compromised for threshold enforcement.
- Every honest authorizer durably locks a first-phase vote before releasing it and never votes for a conflicting entry at the same log position.
- Partial rollback safety requires an independent non-equivocating monotonic checkpoint; P5.13 shows that a surviving party-quorum intersection is insufficient after one honest database restore.
- The coordinator, network, cloud, client, and up to the stated faulty parties may collude. They may deny service; safety fails closed.

The compact profile is `(t=3, n_a=5, f_a=2, q_a=4)`. The resilient profile is `(t=3, n_a=7, f_a=2, q_a=5)`.

## Canonical Objects

Every signed object begins with a protocol-version and domain-separation label. Every field is encoded using the project canonical binary encoding selected under P1.3. Variable-size collections are length-prefixed and authorizer identifiers are sorted for certificate encoding.

### Configuration

`AttemptConfig` contains:

- `protocol_version`;
- `bid` and `epoch`;
- `config_no` and `config_digest`;
- active authorizer identifiers and verification keys;
- `n_a`, `f_a`, and `q_a`;
- active coordinator identity;
- base budget `B` and accumulated extension `X`;
- policy and TPASS public-parameter digests;
- predecessor configuration/epoch certificate digest, if any.

`config_digest` commits to the entire canonical configuration. Parties reject parameters supplied outside the signed configuration.

### Request digest

`request_digest` is:

`H("LOCUS/attempt-request/v1" || protocol_version || bid || epoch || config_digest || recovery_identity || sid || encode(A) || policy_digest || admission_policy_digest)`.

`sid` is a client-generated 256-bit random session identifier. `A` is the canonical blinded TPASS request. `admission_policy_digest` binds the certified issuer, subject-binding, audience, assurance, and sender-constraint policy, not a volatile access-token identifier or raw credential. The common entry stores the privacy-minimized `admission_grant_digest`; each party separately stores its local `AdmissionRecord`, as defined in `docs/recovery-authorization.md`.

A changed field produces a different request digest and therefore requires a new attempt position. The same `sid` with a different digest is a conflict and is rejected rather than treated as a retry.

### Ledger state

The certified state after log position `j` is:

- `log_index = j`;
- `head_hash`;
- `consumed`, the number of attempt positions consumed in this epoch;
- `B_eff = B + X`;
- active `config_digest`;
- exact `backup_digest` for the canonical `(bid, epoch)` cloud object;
- epoch status: `ACTIVE` or `RETIRED`;
- optional lifecycle metadata digest.

Genesis has `log_index = 0`, `consumed = 0`, an exact backup digest, and a configuration certificate created during enrollment. The current `LOCUS-attempt-config-v2` digest covers this backup binding as well as the authorizer membership/quorum. Genesis is not an online attempt.

### Entry types

All entries contain `entry_version`, `bid`, `epoch`, `config_digest`, `log_index`, `previous_head_hash`, `entry_type`, `resulting_consumed`, `resulting_B_eff`, and an entry-specific body.

- `ATTEMPT`: contains `sid`, `request_digest`, and the common `admission_grant_digest`; requires `resulting_consumed = previous_consumed + 1 <= B_eff`.
- `BUDGET_EXTENSION`: contains a separately authorized administrative evidence digest and positive extension amount; does not decrement or reset `consumed`.
- `CONFIG_PREPARE`: commits to the next configuration and migration snapshot digest; does not change the active configuration yet.
- `CONFIG_ACTIVATE`: contains the prepare certificate and new-party readiness certificate; activates the next configuration without changing `consumed` or `B_eff`.
- `RETIRE_EPOCH`: permanently changes the epoch to `RETIRED`; no later attempt or extension entry is valid.

There is no ordinary `RESET`, `DELETE_ATTEMPT`, `UNLOCK`, or counter-decrement entry.

No general `BURN` transition is permitted for an ambiguous slot. Proving that a hidden prepare certificate does not exist is not generally possible in the stated asynchronous/Byzantine model. An incomplete slot must be completed as the same entry or the epoch fails closed and requires out-of-band creation of a fresh epoch. This deliberately sacrifices availability rather than risk a fork or restored budget.

### First-phase vote and prepare certificate

An `EntryVote` signs:

`H("LOCUS/attempt-vote/v1" || config_digest || entry_hash)`.

A `PrepareCertificate` contains the complete entry and at least `q_a` valid, distinct `EntryVote` signatures under the active configuration.

The prepare certificate proves that a unique entry obtained enough durable locks. It is not yet sufficient for a TPASS response.

### Install vote and authorization certificate

After validating and durably storing the complete prepare certificate, an authorizer signs an `InstallVote` over:

`H("LOCUS/attempt-install/v1" || config_digest || prepare_certificate_hash)`.

An `AuthorizationCertificate` contains the prepare certificate and at least `q_a` valid, distinct install votes. This is the certificate accepted by TPASS parties.

The two phases ensure that install voters have the whole prepare certificate durably available before they release an install signature. A lost coordinator can reconstruct certificates from stored votes when a sufficient responsive set remains. Byzantine voters may fail to persist or later withhold data; this can deny recovery but cannot create a conflicting authorization certificate under the quorum-intersection assumption.

## Authorizer Durable State

Each authorizer stores, transactionally where fields change together:

- active and historical certified configurations;
- the latest installed authorization certificate and certified state;
- all later valid certificates required to verify continuity;
- at most one `SlotLock` for `latest.log_index + 1`;
- stored prepare certificate and install vote for that lock, when reached;
- `sid -> request_digest, log_index, entry_hash, state` idempotency records;
- response records keyed by request, TPASS phase, and party identity;
- privacy-minimized audit event digests;
- database schema/version and integrity metadata.

`SlotLock.state` is one of:

- `VOTED`: entry and durable first-phase signature exist;
- `PREPARED`: a valid prepare certificate is durable;
- `INSTALL_VOTED`: the prepare certificate and durable install signature exist;
- `INSTALLED`: a complete authorization certificate is durable and is the local certified head.

The implementation may collapse `PREPARED` and `INSTALL_VOTED` into one transaction if the install signature is deterministically regenerated from durable state. It may not release either vote before the prerequisite state commits.

## Authorizer State Machine

### T0: Start and reconcile

On every process start, the party generates a fresh volatile 256-bit `boot_nonce` from the operating-system CSPRNG. The nonce is never loaded from a database snapshot. Before voting or emitting a TPASS response, the party verifies its database and reconciles with the authorization quorum as described below.

States are `STARTING -> RECONCILING -> READY` or `FAILED_CLOSED`.

### T1: Receive proposal

For a proposal `E`, the authorizer verifies:

1. authenticated coordinator identity and protocol version;
2. active backup, epoch, and configuration;
3. a valid installed predecessor certificate matching `E.previous_head_hash`;
4. `E.log_index = predecessor.log_index + 1`;
5. entry-type transition rules and budget arithmetic;
6. OIDC/DPoP admission evidence for `ATTEMPT`, using the P5.4 validation and replay interface;
7. canonical request and entry encodings;
8. no conflicting `sid` or request idempotency record;
9. no conflicting local slot lock.

If the same entry is already locked, the party returns the stored first-phase vote. If another entry is locked at that position, it returns a generic conflict/fail-closed result and no signature.

### T2: Durable vote lock

In one local transaction, the authorizer:

1. inserts the complete entry;
2. inserts `SlotLock(VOTED, entry_hash)` with a unique database constraint on `(bid, epoch, config_digest, log_index)`;
3. inserts or verifies the `sid` idempotency mapping;
4. persists the vote bytes or sufficient deterministic signing input;
5. commits and synchronizes according to the selected durable database settings.

Only after the transaction succeeds does the authorizer return `EntryVote`. Transaction failure returns no vote.

### T3: Install prepare certificate

Upon receiving a prepare certificate, the authorizer verifies all signers, quorum size, configuration, entry, predecessor, and its own lock. It rejects any certificate for a conflicting local lock.

In one transaction, it stores the complete prepare certificate, advances the lock to `PREPARED/INSTALL_VOTED`, and persists the install-vote signing input. Only after commit does it return `InstallVote`.

### T4: Install authorization certificate

Upon receiving a valid authorization certificate, the authorizer:

1. verifies the prepare and install quorums and exact entry binding;
2. verifies continuity from its certified head;
3. stores the full certificate;
4. applies the deterministic entry transition;
5. advances `latest installed head`;
6. marks the slot `INSTALLED` and clears only transient proposal data that is reproducible from the certificate;
7. commits before acknowledging installation.

If the party is behind, it installs every missing valid certificate in order. If it is ahead, it returns its higher valid certificate for reconciliation. If it observes two valid conflicting certificates, it records evidence and enters `FAILED_CLOSED`; such a condition contradicts the safety assumptions and must never be auto-repaired.

### T5: Exact retry

For the same `(sid, request_digest)`, the authorizer returns the stored vote, certificate, or response corresponding to its durable state. It never allocates another log position. The same `sid` with a different digest is rejected.

## Coordinator State Machine

The coordinator maintains no authoritative security state. Its durable queue improves liveness and observability but is reconstructible from party certificates and votes.

Coordinator states are:

`RECEIVED -> ADMISSION_VALID -> HEAD_RECONCILED -> PROPOSED -> PREPARED -> AUTHORIZED -> DISPATCHED`, with terminal `REJECTED` and `FAILED_CLOSED`.

### C1: Admission and idempotency

The coordinator obtains party-specific admission proofs but cannot validate on behalf of the authorizers. Each authorizer independently validates the P5.4 evidence. The coordinator computes `request_digest` and looks up `sid`; an exact retry resumes the recorded state, while a conflicting use of `sid` is rejected.

### C2: Reconcile head and pending slot

The coordinator queries authorizers for signed state summaries, installed certificates, and any lock/vote at the next position. It requires `q_a` valid summaries agreeing on the reconciled installed head before treating a slot as empty.

- If a valid higher installed certificate exists, it catches other parties up before proposing.
- If `q_a` signed summaries for the reconciled head report the next slot empty, it may propose the requested entry. Locks hidden only among the remaining `n_a-q_a` parties cannot combine with the newly locked quorum to certify a conflicting entry under the intersection rule.
- If one entry hash is locked by any honest/credible respondent, it must resume that same entry and may not substitute the new request.
- If different entry hashes are locked at the same position, it must not choose, merge, unlock, or burn the position. It enters `FAILED_CLOSED` for that epoch pending security review or fresh-epoch administrative recovery.
- A missing or unreachable party is not evidence that it has no lock.

The normal deployment admits proposals only through the configured coordinator identity, limiting accidental split locks. Coordinator compromise remains a denial-of-service risk.

### C3: Prepare

The coordinator sends the identical canonical entry to authorizers and collects first-phase votes. At `q_a` valid votes it assembles the prepare certificate. Fewer votes produce no prepare certificate and no TPASS response. It stores received votes for restart but treats authorizer databases as the durable source.

### C4: Authorize

The coordinator broadcasts the prepare certificate and collects install votes. At `q_a` valid install votes it assembles the authorization certificate. This is the counted-attempt commit point for an `ATTEMPT` entry.

The coordinator broadcasts the authorization certificate to all parties. It may report success to the client after the certificate is formed; lack of acknowledgements can reduce availability but cannot allow the slot to be reused.

### C5: Dispatch

Only the complete authorization certificate is dispatched with the TPASS request. A party that did not participate in either certificate may still respond after validating and durably installing the certificate and satisfying the response-freshness rule.

## Exact Counted-Attempt Commit Point

An attempt is committed when `q_a` valid install votes over one prepare certificate exist and therefore form an `AuthorizationCertificate` for an `ATTEMPT` entry.

Before that point:

- no honest TPASS party may emit a secret-dependent response;
- a first-phase lock may nevertheless make the position permanently unavailable if safe completion becomes impossible;
- ambiguity never permits reuse of the position for another request.

After that point:

- `consumed` has increased by exactly one;
- client disconnect, coordinator loss, cloud failure, wrong cues, malformed later messages, insufficient TPASS replies, or missing final correctness report do not restore the position;
- every exact retry maps to the same request and position;
- no entry with `resulting_consumed > B_eff` is valid.

This definition has zero safety overrun. It may have conservative under-utilization because locked but uncompleted positions can make the epoch unavailable.

## TPASS Pre-Response Enforcement

Before an honest party emits its first secret-dependent TPASS message, it must:

1. validate and durably install the authorization certificate;
2. verify that the certificate is for its backup, epoch, active/historical configuration, `sid`, and exact blinded request `A`;
3. verify the `ATTEMPT` entry is on the unique certified chain and within `B_eff`;
4. obtain a live `ResponseFreshnessCertificate` as described below;
5. in one local transaction, persist the request/phase idempotency record and the certificate/freshness digests;
6. only after commit compute or release the TPASS response.

The response is bound to the protocol transcript, party identity, session, request, phase, and authorization-certificate hash. A modified or cross-party response is invalid.

Because any `t` responses contain an honest party when at most `t-1` parties are compromised, a client cannot evaluate a distinct uncertified TPASS request without violating the TPASS threshold assumption.

## Response Freshness Under Partial Rollback

A historically valid authorization certificate is intentionally replayable only for the exact same blinded request. However, a rolled-back party must not blindly resume an old or retired epoch without consulting surviving current authorizers.

Immediately before a secret-dependent response, the party generates a fresh, internal `response_nonce` that is not supplied by the client or loaded from persistent state. It requests authorizer statements over:

`H("LOCUS/response-freshness/v1" || bid || epoch || config_digest || authorization_certificate_hash || request_digest || party_id || tpass_phase || boot_nonce || response_nonce)`.

An authorizer signs only after reconciling its current certified head and verifying that:

- the attempt certificate is on the canonical certified chain;
- the epoch is not retired;
- the configuration is valid for that attempt;
- no recorded lifecycle rule forbids the response.

`q_a` such signatures form a `ResponseFreshnessCertificate`. It does not consume another attempt and cannot authorize another request, party, phase, boot, or nonce.

The party obtains a new freshness certificate for each first secret-dependent response after restart and does not accept a client-supplied cached certificate. A later retirement does not retroactively invalidate a response already released under a valid freshness quorum; this narrow in-flight race is an availability/lifecycle limitation, not an additional password guess.

This live quorum check is necessary for responding-party liveness, but it is not a rollback anchor. Before accepting freshness or responding, a party must also validate the current independent monotonic-witness receipt. Coordinated rollback or equivocation of that witness remains outside the property.

## Concurrency And Subset Rotation

- All threshold subsets use the same epoch-wide ledger and certificate namespace.
- A database uniqueness constraint and durable slot lock prevent an honest authorizer from voting for two concurrent proposals at one position.
- Quorum intersection prevents two conflicting prepare or authorization certificates.
- A proposal losing the race is not silently moved to another position; the client must submit it as a new request after the winning certificate installs.
- Exact delivery duplicates return stored state.
- A client cannot reuse one certificate with another `A`, `sid`, epoch, party configuration, or policy because those values are in `request_digest` and the ledger entry.
- A malicious coordinator can split first-phase votes and deny progress. It cannot create two certificates or cause a safety overrun; there is no unsafe timeout unlock.

The implemented coordinator sends each quorum phase concurrently, waits within
the smaller of its ten-second phase budget and remaining 45-second operation
budget, and requires the configured `q_a` valid replies. Transport-ambiguous
calls receive at most one byte-identical retry under the same durable
idempotency key. A missing response is never an unlock signal, and an observed
durable conflict fails the operation closed. Before authorization, the client
selects only TPASS parties whose authenticated summaries exactly match the
quorum-reconciled head; after authorization, that set is fixed and failure does
not restore the consumed position. The detailed P4.8 boundary and evidence are
in `docs/party-failure-policy.md`.

## Crash Recovery

| Crash point | Recovery rule |
| --- | --- |
| Before durable first-phase lock | No vote exists; the identical proposal may be processed normally. |
| After lock commit, before vote delivery | Retry deterministically returns the stored vote. |
| After some votes, before prepare certificate | Coordinator queries locks/votes and completes only the same entry. Conflicting locks fail closed. |
| After prepare assembly, before broadcast | Prepare certificate is reconstructed from durable votes when possible; the slot is never reassigned. |
| After prepare storage, before install-vote delivery | Authorizer returns the stored/deterministically regenerated install vote. |
| After some install votes, before authorization certificate | Coordinator reconstructs the certificate from durable install state when possible; otherwise the slot remains unavailable. |
| After authorization assembly, before party installation | Any holder rebroadcasts it; parties install in chain order. The attempt remains consumed. |
| After party response record, before network send | Retry returns the same bound response or safely regenerates it only under the same persisted transcript and fresh-response rules. |
| After response send, before acknowledgement | Duplicate request is idempotent and does not allocate a new attempt. |
| Client crash before final result | Attempt remains consumed; correctness reporting is not required. |

Every restart begins in `RECONCILING`. Local database absence for an enrolled party is not treated as a fresh empty database.

## Rollback Reconciliation

An authorizer in `RECONCILING` first reads the authenticated independent monotonic checkpoint, then collects signed summaries and certificates from the configured authorizers.

1. It verifies the witness receipt and binds it to the exact backup, epoch, configuration, head, and active/retired status.
2. It verifies all certificate signatures and chain continuity from genesis to that witnessed head.
3. It installs missing certificates in order; signed party summaries may locate data but cannot override the witnessed checkpoint.
4. It preserves or reconstructs a pending lock only for the same entry and predecessor.
5. It enters `FAILED_CLOSED` on a fork, missing required history, invalid receipt, unavailable witness, local state ahead of the witness, or uncertainty that cannot be resolved without reusing a slot.

A local snapshot behind a witnessed certified head is detectable and recoverable. Party signatures still prevent ordinary equivocation, but quorum summaries cannot decide freshness after rollback. P5.13 finds a conflicting-certificate trace after one honest restore because another honest party can legitimately remain stale. A certificate becomes usable only after the witness conditionally advances the exact predecessor and returns a matching receipt.

Rollback or equivocation of the independent witness, or restoration of every party plus that witness, is outside the detection claim. Witness outage fails closed. Its implementation, administration, privacy leakage, and performance are P5.9/P8 requirements rather than silently assumed infrastructure.

## Reconfiguration And Party Replacement

Reconfiguration uses a joint transition so replacement cannot reset budget or history.

1. The old configuration certifies `CONFIG_PREPARE`, which includes the full new configuration, current head, `consumed`, `B_eff`, epoch status, and migration snapshot digest.
2. Every new authorizer verifies the complete certified chain and stores the migration snapshot.
3. At least `q_new` new authorizers sign a `NewConfigReadyCertificate` over the prepare certificate and imported head.
4. The old configuration certifies `CONFIG_ACTIVATE` containing the readiness certificate.
5. The activation certificate additionally carries at least `q_new` new-authorizer activation signatures. Both the old and new quorum requirements must verify.
6. Entries after activation use only the new `config_digest`; retired identities cannot vote or respond for new attempts.

Reconfiguration begins only with no unresolved next-slot conflict. If the old quorum cannot certify activation, availability is lost; administrators may create a fresh key/backup epoch through an out-of-band process, but may not assert continuity of the old attempt bound unless the certified head is carried forward.

## Budget Extension, Exhaustion, And Retirement

- Ordinary recovery cannot change `B_eff`.
- `BUDGET_EXTENSION` requires fresh enrolled-user OIDC/DPoP admission, the enrollment-pinned administrator signature threshold, the ledger authorization quorum, and the configured cumulative `X_max` bound from P5.4/P5.12.
- Extensions increase `X`; the paper's guessing equation uses the resulting `B_eff`.
- Budget exhaustion produces a generic refusal before a new proposal lock.
- `RETIRE_EPOCH` is irreversible in the certified chain.
- A retired epoch signs no new attempt, extension, configuration, or response-freshness statement.
- Correctness of the client password or AEAD result never resets or decrements the counter.

The implemented P4.9 store slice realizes the narrower same-membership
re-enrollment case, not general configuration replacement. One signed transition
binds the predecessor's exact head, consumed count, budget, configuration, and
backup plus the direct successor's configuration, backup, and disclosed fresh
per-epoch budget. Old and new 4-of-5 quorums are required. A prepared successor
has no active epoch row; certificate installation atomically retires the old row
and activates the successor locally. Direct epoch-two enrollment, reactivation,
changed retry, old-certificate reuse, and membership change are rejected. The
full contract and deployment gaps are in `docs/epoch-lifecycle.md`.

## Validation And Failure Responses

Internal diagnostics distinguish malformed encoding, bad signature, stale head, configuration mismatch, lock conflict, exhausted budget, failed admission, rollback uncertainty, and unavailable quorum. The external recovery interface normalizes security failures so it does not create a cheaper cue oracle.

Operational status may reveal availability and high-level ledger position only to authenticated administrators. It must not expose `A`, raw admission credentials, raw cues, cue identifiers, password scalars, TPASS shares, recovered secrets, wrapping/private keys, or unrestricted response transcripts.

## Required Database Guarantees

The chosen per-party database must provide:

- atomic transactions for locks, idempotency records, certificates, and head changes;
- uniqueness constraints for slot and `sid` bindings;
- durable commit configuration documented and tested under process/container crashes;
- integrity checking and explicit schema migrations;
- no automatic recreation of missing enrolled state;
- backup/restore tooling that always triggers reconciliation;
- deterministic fault injection at each transaction boundary.

Ordinary database durability and quorum reconciliation are not rollback resistance. The independent monotonic-witness receipt supplies the required freshness boundary once implemented.

## Safety Invariants

The implementation and model tests must continuously check:

1. One honest authorizer has at most one entry hash locked per `(bid, epoch, config_digest, log_index)`.
2. Two valid prepare certificates cannot contain conflicting entries at one position.
3. Two valid authorization certificates cannot contain conflicting entries at one position.
4. Every installed head is genesis or extends exactly one valid predecessor certificate.
5. `consumed` never decreases and increases by one only for `ATTEMPT`.
6. `B_eff` changes only through a valid positive extension and never falls below `consumed`.
7. No `ATTEMPT` certificate has `resulting_consumed > B_eff`.
8. One `sid` maps to exactly one request digest and entry.
9. A TPASS response record refers to one valid authorization and freshness certificate.
10. No honest secret-dependent response precedes the authorization commit point and local durable response record.
11. Configuration activation preserves head, `consumed`, `B_eff`, epoch, and retirement state.
12. Retired configurations cannot authorize new entries, and retired epochs cannot authorize freshness statements.
13. Conflicting or uncertain state never triggers counter reset, local unlock, or fresh empty enrollment state.
14. Persistent and observable state excludes prohibited cue/password/key material.
15. Every authorization certificate is transitively bound through
    `config_digest` to the exact backup digest durably installed for that epoch.

## Test And Evaluation Mapping

P5.5-P5.13 must turn each transition and invariant into executable tests. At minimum:

- crash before and after every transaction commit and every signature/network release;
- all sequential budget boundaries and concurrent proposals;
- exact retry and changed-field replay at every protocol state;
- coordinator equivocation and loss of every subset of votes/certificates;
- compact/resilient quorum response matrices;
- all valid TPASS subset rotations using one global certificate;
- rollback of every party subset, including cases that must fail closed;
- response-freshness checks after database restore and epoch retirement;
- old/new configuration overlap, stale replacement, and failed activation;
- extension, exhaustion, false-lockout, and retirement traces;
- recursive database/log/trace secret scans;
- authorization latency, prepare/install/freshness messages, certificate bytes, durable writes, storage growth, throughput, tail latency, and recovery time.

The P5.13 executable model now enumerates the frozen compact-profile interleavings and records quorum-only rollback and retirement counterexamples in `docs/attempt-control-model.md`. Its ideal-anchor scenarios have no counterexample within their bounds. These results supplement but do not replace a proof or service crash/rollback tests.

## Remaining Inputs, Not P5.2 Ambiguities

- P5.4 selects OIDC/DPoP ordinary admission and threshold-signed, policy-bounded administrative authorization; implementation remains pending.
- P2.3 freezes the canonical binary encoding used by signed objects.
- P1.4/P2.8 select exact maintained libraries for signatures, hashing, database access, and service integration.
- P5.5 onward implements and tests the specified transitions.
- P5.15 supplies the complete security argument and explicitly reports fail-closed liveness and global-rollback limits.

These dependencies fill named interfaces; they do not change the state-machine safety rule. If any later choice requires an unlock, slot reuse, weaker quorum, cached freshness bypass, or coordinator authorization power, P5.2 must be reopened and all dependent claims updated.

## Paper Claim Effect

This specification records the former global-attempt-bound target and the
implemented local subset. It does **not** support describing the current LOCUS
artifact as designed or demonstrated to enforce a global bound.
`prototype/locus/party_store.py`,
`party_service.py`, and `party_http.py` now demonstrate narrower invariants: an
authorization certificate is cryptographically verified and transactionally
installed before native `prepare_commitment`; exact retries are idempotent;
concurrent local slot installation consumes at most one position; and an
interrupted volatile phase fails closed without restoring its local count. The
signed two-phase attempt/freshness protocol and native TPASS messages now cross
role-separated pinned mutual-TLS boundaries among five local databases and
per-party secret states. The tests preserve complete recovery with one process
unavailable, catch it up after restart, reject cross-session response use, and
lose an open volatile phase closed without restoring the count. There is no
rollback anchor, public-client admission, broad network scheduler, general
party-replacement mechanism, or global security argument. The implemented
same-membership lifecycle does not supply those missing properties. Therefore
the slice supports only exact local ordering, retry, persistence, and failure
observations. It does not support present-tense claims that
the prototype is globally rate-limited, rollback-resistant, concurrency-safe
across arbitrary deployments, or durably auditable. Those properties are future
work that would require a materially stronger architecture, such as an
independently administered monotonic witness or a reviewed consensus design,
plus new implementation and evidence.
