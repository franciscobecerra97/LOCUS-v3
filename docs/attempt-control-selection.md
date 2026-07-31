# LOCUS Attempt-Control Mechanism Selection

Status: P5.3 mechanism study, updated 2026-07-22 after the P5.13 bounded model and scope reduction. P5.2 specifies the aspirational state machine in `docs/attempt-control-state-machine.md`; `docs/attempt-control-model.md` shows why party-quorum reconciliation is insufficient. The scoped paper retains the implemented ledger only as partial local instrumentation and does not claim the complete mechanism.

## Decision

The implemented LOCUS prototype uses a **quorum-certified, hash-chained attempt ledger replicated by the recovery parties** as local research instrumentation. The complete property formerly targeted by this selection is future work.

For each backup epoch, a ledger entry binds one sequence position to one canonical recovery `request_digest`, the preceding certified head, the effective attempt budget, and the active party/configuration identifier. A certificate is a set of independently verifiable authorizer signatures meeting the configured quorum. Honest TPASS parties accept a recovery request only after validating its certificate and durably recording their response/idempotency state.

The recovery parties are also the baseline attempt authorizers. A coordinator may authenticate admission, serialize proposals, collect signatures, broadcast certificates, and recover interrupted proposals, but it is not part of the authorization quorum. Compromise or equivocation by the coordinator can delay or deny recovery; it cannot create a valid attempt certificate, fork a certified position, increase the budget, or recover the private key by itself.

This selection combines the useful parts of three candidates and the P5.13 correction:

- quorum-certified counters provide non-forking authorization while honest durable locks are not rolled back;
- the hash-chained replicated ledger provides durable history, reconciliation, and audit evidence;
- a one-use ticket is the request-bound certificate emitted by the ledger;
- an independently administered strongly consistent witness conditionally advances the certified head so restored party databases cannot make a stale quorum authoritative.

A standalone trusted recovery coordinator and a generic full-featured replicated database are not selected. P5.13 shows that a full rollback-resistant claim would require a narrow external checkpoint authority or an equivalent stronger consensus assumption. The scoped paper deliberately does not add that authority; it reports the current ledger as partial local enforcement and leaves the global bound as future work.

## Decision Drivers

A future complete mechanism would need to satisfy the exact P5.1 property under the synchronized threat model (now A1-A16), especially:

1. certify no more than `B_eff` distinct request digests;
2. produce zero safety overrun under concurrency and threshold-subset rotation;
3. bind every authorization to one backup, epoch, session, protocol/configuration, recovery identity, and TPASS request;
4. commit authorization before any honest secret-dependent TPASS response;
5. make exact retry idempotent and modified replay invalid;
6. preserve or conservatively consume budget across crashes;
7. detect or fail closed on partial rollback under the independent monotonic-witness assumption;
8. carry history through party replacement and configuration changes;
9. tolerate up to the stated number of Byzantine authorizers for safety;
10. keep cues, password material, party shares, recovered secrets, wrapping keys, and private keys out of the authorization layer;
11. expose the safety/availability tradeoff rather than hiding it;
12. remain implementable and experimentally testable before Cycle 1.

## Candidate Comparison

| Candidate | Global uniqueness and concurrency | Byzantine/rollback boundary | Availability and complexity | Cycle 1 decision |
| --- | --- | --- | --- | --- |
| Threshold- or quorum-signed one-use tickets | A ticket binds a request, but signatures alone do not ensure unique issuance or one-use redemption. Issuers still need shared ordered state. Pre-issued tickets create stockpiling, theft, and revocation problems. | Safe only if ticket issuance is backed by a non-forking counter/log; otherwise Byzantine issuers or rollback can mint conflicting tickets. | Compact verification, but the missing issuance protocol contains nearly all hard problems. | Reject as a standalone mechanism. Retain the request-bound certificate as the ledger's output artifact. |
| Quorum certificates over monotonic counters | Directly supports one certified value per position while quorum-intersecting honest signers retain durable locks. | Handles Byzantine equivocation under `2*q_a > n_a + f_a`, but P5.13 shows party-quorum summaries can certify a stale fork after one honest database restore. | Narrow state and message surface. Requires proposal serialization, durable locking, recovery of partial proposals, explicit reconfiguration, and an independent monotonic witness. | Select as the ordering core, not as a standalone rollback defense. |
| Replicated append-only attempt log | Naturally orders attempts, supports idempotency, lifecycle events, and audit. A hash or Merkle structure alone detects inconsistencies but does not prevent split views. | Byzantine safety requires a BFT ordering/consensus rule or equivalent quorum certificates; a crash-only replicated log is insufficient. | A generic BFT state-machine stack is robust but substantially increases implementation, deployment, and validation scope. | Select a purpose-built, hash-chained ledger whose heads are quorum-certified; do not build or claim a general BFT database. |
| Narrow coordination service | A serializable transaction can enforce a global counter and makes concurrency/crash handling comparatively simple. | The service becomes a trusted attempt-safety and rollback authority; its compromise or restored database can mint or restore budget unless externally anchored. | Lowest implementation cost and highest operational availability in the single-service case, but a central safety dependency and weak fit with the thesis. | Reject as a trusted authority. Permit an untrusted sequencer/collector whose outputs require party quorum certification. |

## Why Simpler Replication Is Insufficient

Raft is a strong reference for crash-recoverable replicated logs, leader changes, and overlapping configuration transitions, but its servers are assumed to stop rather than behave maliciously. It therefore does not satisfy A10's equivocation model by itself. LOCUS can reuse implementation ideas such as durable logs and explicit configuration transitions without describing a Raft deployment as Byzantine safe.

Certificate Transparency demonstrates useful append-only Merkle commitments and consistency proofs, but an append-only data structure is an audit mechanism rather than an ordering authority. A malicious operator can attempt split views; preventing LOCUS overrun requires parties to reject uncertified heads before TPASS responses, not merely detect inconsistent histories later.

PBFT and HotStuff demonstrate established Byzantine state-machine replication approaches. HotStuff states the usual partially synchronous `n >= 3f+1` setting and quorum-certified chained decisions. LOCUS does not claim to invent or faithfully implement either protocol. The selected mechanism is intentionally narrower: it certifies a small, per-epoch monotonic ledger and may sacrifice liveness by failing closed rather than implement a general BFT state machine under the Cycle 1 schedule.

## Former Target Trust And Quorum Profiles

Let `n_a` be the authorizer count, `f_a` the maximum Byzantine authorizers covered for safety, and `q_a` the certificate quorum. The selected rule remains:

`2*q_a > n_a + f_a`.

Every honest authorizer durably locks its vote for a sequence position and predecessor before releasing its signature and never signs a conflicting entry at that position. This is the non-equivocation fact supplied by quorum intersection; digital signatures alone do not supply it.

The following profiles were considered before the P5.13 scope reduction. They
are preserved as design history and future-work candidates; they are not the
evaluated Cycle 1 deployment:

| Profile | TPASS | Attempt authorization | Safety | Progress limitation |
| --- | --- | --- | --- | --- |
| Compact | `t=3, n=5` | `n_a=5, f_a=2, q_a=4` | Any two certificates intersect in at least three authorizers, hence at least one honest authorizer under `f_a=2`. | Requires four responsive authorizers. Two Byzantine authorizers can deny service by refusing, even though TPASS itself needs only three parties. |
| Resilient | `t=3, n=7` | `n_a=7, f_a=2, q_a=5` | Standard `3f_a+1`-sized profile with five-signature certificates for `f_a=2`. | Can progress with any five responsive honest/following authorizers after network stabilization; implementation still fails closed during unresolved conflicts or stale-head reconciliation. |

Safety and liveness are separate claims. The compact profile is valuable for measuring the cost of retaining five recovery parties, but it does not tolerate two authorizers that actively refuse. The resilient profile targets Byzantine safety with two faulty authorizers and progress when five honest/following authorizers remain responsive. Active equivocation may still force fail-closed denial unless the concrete P5.2 recovery protocol proves liveness for that case.

The evaluated Cycle 1 deployment instead uses TPASS `t=2,n=3` together with
five authenticated authorizer processes and a 4-of-5 local authorization
quorum. Parties 1--3 hold TPASS state; parties 4--5 are authorizer-only. This
profile supplies implementation and cost evidence only. P5.13 prevents it from
supporting a rollback-resistant global attempt-bound claim.

The baseline certificate will retain individual signer identities and signatures rather than introduce a custom or threshold-signature protocol. This makes quorum membership, double-sign evidence, and artifact verification explicit. Aggregation is an optional optimization only after the baseline is correct and measured.

## Protocol Shape Carried Into P5.2

P5.2 turns this shape into the exact state machine in `docs/attempt-control-state-machine.md`:

1. The client creates `sid` and the blinded TPASS request `A`.
2. The admission layer verifies the separate recovery-authorization credential without learning cue/password material.
3. The coordinator computes the canonical `request_digest` and proposes the next entry extending a certified head.
4. Each authorizer validates epoch, configuration, predecessor certificate, budget, admission evidence, and request fields.
5. In one local transaction, an authorizer records the proposal/lock and its idempotency mapping before releasing its signature.
6. The coordinator assembles `q_a` signatures into an authorization certificate and distributes it.
7. Each TPASS party verifies the certificate and request binding, persists its own response state, and only then emits the first secret-dependent TPASS message.
8. Retries reproduce the same certificate and persisted response state. A changed bound field requires another ledger position.
9. A stale or rolled-back party must reconcile to the independently witnessed certified head before voting or responding; party summaries locate history but cannot establish freshness.
10. Epoch/configuration changes are certified ledger transitions carrying the prior head and consumed budget forward.

The coordinator cannot instruct an authorizer to unlock and sign a conflicting entry. P5.2 deliberately rejects a general administrative/burn escape from an ambiguous slot because absence of a hidden prepare certificate cannot be proved under the stated model. An incomplete proposal is recovered and finalized as the same entry, or the epoch fails closed and requires out-of-band fresh-epoch recovery. Unilateral deletion or counter reset is forbidden.

## Fixed Safety Argument Skeleton

The later proof and tests must establish:

1. **Certificate authenticity:** fewer than `q_a` authorizer keys cannot forge a certificate.
2. **Single certified entry per position:** two conflicting certificates would intersect in more than `f_a` authorizers, including an honest authorizer that would need to violate its durable non-equivocation rule.
3. **Chain uniqueness:** every usable entry commits to the previous witnessed certificate/head and carries the witness's conditional-advance receipt, so only one witnessed history advances per epoch under the witness non-equivocation assumption.
4. **Budget bound:** authorizers reject ordinary entries above `B_eff`; therefore no more than `B_eff` request entries can be certified.
5. **Threshold enforcement:** with at most `t-1` compromised TPASS parties, every set of `t` responses includes an honest party that requires the matching certificate.
6. **Subset independence:** all party subsets verify the same epoch-wide certificate namespace.
7. **Retry/replay safety:** the request digest and persisted idempotency map make an exact retry the same attempt and reject altered or retired transcripts.
8. **Rollback boundary:** quorum votes may form conflicting raw certificates after party rollback, as P5.13 demonstrates, but only the certificate with a valid conditional-advance receipt is usable. Witness rollback, equivocation, or compromise remains out of scope and must be demonstrated as a limitation.

## Failure Behavior

- Invalid admission evidence: reject before ledger reservation; apply separate admission throttling.
- Stale predecessor or configuration: reject and return only non-sensitive reconciliation metadata.
- Conflicting proposal at a locked position: refuse; never unlock locally.
- Coordinator crash after some votes: a replacement/restarted coordinator queries durable votes and attempts to complete the same entry.
- Certificate assembled but not broadcast: authorizers retain votes; later reconciliation reconstructs the certificate from stored signatures.
- Uncertain durable state or missing history: fail closed until quorum reconciliation or explicit administrative recovery.
- Budget exhausted: refuse new request entries; no ordinary reset exists.
- Insufficient authorization quorum: recovery unavailable even if `t` TPASS parties are reachable.
- Partial database rollback: catch up from the witnessed certified head or refuse.
- Witness outage: refuse new votes, freshness, lifecycle transitions, and TPASS responses even if party quorums are available.
- Witness rollback/equivocation or global rollback of all authorizers and the witness: not covered; this remains an explicit residual risk.
- Malicious coordinator or authorizer equivocation: record verifiable evidence where available and fail closed; safety is prioritized over availability.

## Implementation Boundary

The state machine and service orchestration may be implemented in Python for schedule and experiment control, but signature, hashing, canonical serialization, and database operations must use established libraries and explicit transactions. No custom signature or consensus primitive is authorized by this decision.

Each recovery party has an independent durable ledger database and identity key. The coordinator has no authorizer signing key, TPASS share, cue data, password verifier, recovered secret, wrapping key, or private key. Normal logs contain only privacy-minimized identifiers/status and never the blinded request itself unless a test-only, synthetic transcript explicitly requires it.

Docker Compose will run the same ledger code in separate party containers and volumes. This demonstrates process/state separation and reproducibility, not independent administration.

## Required Tests And Measurements

In addition to the P5.1 suite, the selected mechanism requires:

- conflicting certificates attempted at every sequence position and configuration;
- coordinator equivocation, crash, restart, and replacement before/after each durable boundary;
- signer double-vote attempts and durable lock recovery;
- incomplete vote sets that are later completed without creating a second request;
- compact and resilient quorum availability matrices;
- reconciliation from one and multiple stale/rolled-back party databases;
- certificate verification by every valid TPASS subset;
- configuration transition with current and stale replacement parties;
- signature count/verification time, certificate bytes, per-entry storage, durable writes, coordination messages, latency percentiles, and throughput;
- measured difference between TPASS availability and attempt-authorization availability.

Tests demonstrate behavior of this implementation. They do not establish the full security of PBFT, HotStuff, TPASS, signatures, or the underlying libraries.

## Rejected Alternatives And Revisit Triggers

Revisit the selection only if one of these occurs:

- implementation shows that P5.2's fail-closed recovery from partial proposals is unusable in the intended deployment;
- the compact and resilient profiles cannot meet the required Cycle 1 performance or artifact complexity;
- independent review finds the quorum/locking argument insufficient for the claimed adversaries;
- a mature, narrowly embeddable BFT component offers materially lower implementation and validation risk;
- experiments show that a central coordination trust assumption is unavoidable, requiring the thesis to be weakened;
- an external monotonic/transparency anchor becomes required rather than optional for the paper's rollback claim.

Any change must update P5.1, the threat model, claim matrix, research question, tests, and manuscript wording.

## Source Basis

- Castro and Liskov, [Practical Byzantine Fault Tolerance](https://www.usenix.org/conference/osdi-99/presentation/practical-byzantine-fault-tolerance), OSDI 1999: primary reference for practical Byzantine state-machine replication.
- Yin et al., [HotStuff: BFT Consensus in the Lens of Blockchain](https://arxiv.org/abs/1803.05069), PODC 2019: primary reference for leader-based, quorum-certified chained BFT under partial synchrony and the `n >= 3f+1` setting.
- Ongaro and Ousterhout, [In Search of an Understandable Consensus Algorithm](https://raft.github.io/raft.pdf), 2014: primary reference for crash-fault replicated logs, durable recovery, and joint configuration changes; explicitly assumes servers fail by stopping rather than Byzantine behavior.
- Laurie, Messeri, and Stradling, [Certificate Transparency Version 2.0](https://www.rfc-editor.org/rfc/rfc9162.html), RFC 9162, 2021: primary specification for append-only Merkle trees, inclusion, and consistency proofs; used only as an audit-structure reference, not an authorization protocol.

These sources support the comparison vocabulary and design constraints. They do not constitute evidence that the selected LOCUS mechanism is correct; that requires implementation, tests, model analysis, and the security argument.
