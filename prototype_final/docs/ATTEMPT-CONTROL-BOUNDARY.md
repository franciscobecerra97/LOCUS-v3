# LOCUS Bounded Attempt-Control Model

Status: P8.4 self-contained preservation of the P5.13 executable
counterexample. The model source, signed-certificate implementation, and strict
schema are byte-for-byte unchanged from their frozen historical controls. They
are bounded supporting controls, not a proof or runtime rollback-resistance
evidence.

## Problem Statement

The compact attempt-authorizer profile uses five authorizers, tolerates at most
two Byzantine authorizers for safety, and requires four signatures. Quorum
intersection prevents conflicting certificates while every honest signer
retains its durable lock. It does not by itself answer what happens when an
attacker restores an honest database while another honest authorizer never
learned the latest certificate.

P5.13 therefore asks two narrow questions:

1. Can quorum-only startup reconciliation recreate a spent sequence position or
   reactivate a retired epoch after snapshot rollback?
2. Does the same bounded counterexample remain when every security-sensitive
   transition is fenced by an ideal independent monotonic checkpoint?

## Threat Assumptions And Abstraction

`locus/attempt_model.py` performs deterministic breadth-first search
with honest-party symmetry reduction. The frozen model contains:

- compact `(n_a=5, f_a=2, q_a=4)` authorization;
- three explicit honest authorizer states and two implicit Byzantine
  authorizers that may support every conflicting quorum;
- budget two and two distinct request identities;
- an installed certificate chain, one next-slot lock, prepare/install phase,
  readiness, and active/retired state per honest authorizer;
- vote, install-vote, certificate, installation, evaluation, crash,
  reconciliation, and snapshot-rollback transitions;
- exact retries collapsed to the existing durable lock or certificate; and
- a seeded finalized-retirement case with restored pre-retirement snapshots.

The adversary may withhold a valid assembled certificate from an honest party,
restore allowed honest snapshots, schedule every transition, and use both
Byzantine signatures on conflicting histories. This is intentional: a
certificate held by a coordinator or subset is not the same as an installed
checkpoint known to every honest party.

The optional anchor mode is deliberately idealized. It assumes one
non-equivocating, non-rolled-back compare-and-set checkpoint that is consulted
before voting and advanced atomically when a certificate becomes usable. The
model does not establish how that service is implemented or protected.

## Invariants And Failure Behavior

Every explored state checks:

1. no two authorization certificates form conflicting chains;
2. no certificate or threshold evaluation occurs after finalized retirement;
3. no certificate exceeds budget or repeats one request identity;
4. no evaluated request lacks a certificate;
5. installed party locks extend exactly one installed predecessor; and
6. an anchor checkpoint names an existing certificate and never reports
   retirement before the modeled retirement decision.

A discovered violation returns the shortest breadth-first trace. Exhausting the
frozen state space returns `no-counterexample-within-bound`. Reaching the state
limit fails the report rather than being interpreted as safety.

## Frozen Results

Run:

```console
uv run --frozen python tasks.py integrated-attempt-boundary
```

The command emits one canonical `LOCUS-attempt-model-report-v1` object validated
by `docs/schemas/attempt-model-report-v1.schema.json` and the stricter in-code
registry contract.

Before running the unchanged model, the P8.4 wrapper validates the exact D025
managed manifest, its five authorizers and distinct 4-of-5 authorization
quorum, the frozen model/certificate/schema digests, and the absence of a
monotonic-witness role. A changed quorum, frozen source, schema, or witness
boundary fails closed. The signed-certificate unit control verifies strict
4-of-5 signatures, quorum intersection, canonical decoding, and configuration/
entry binding. It remains isolated supporting behavior and is not wired into
recovery-suite correctness. This binds the negative model to the current
deployment assumptions; it is not a claim that the abstract trace was executed
against live containers.

| Scenario | Reconciliation | Bound explored | Result |
| --- | --- | --- | --- |
| Baseline concurrency, no rollback | Party quorum | depth 12; 766 states; 2,480 transitions | No counterexample within bound |
| One restored honest database | Party quorum | depth 12; 2,228 states; 9,374 transitions | Conflicting slot-one certificates |
| One restored honest database | Ideal anchor | depth 14; 2,526 states; 11,151 transitions | No counterexample within bound |
| Up to two restored honest databases | Party quorum | depth 12; 3,372 states; 15,751 transitions | Conflicting slot-one certificates; shortest trace still uses one restore |
| Up to two restored honest databases | Ideal anchor | depth 14; 3,794 states; 18,678 transitions | No counterexample within bound |
| Final retirement plus two old snapshots | Party quorum | depth 7; 72 states; 180 transitions | Authorization after final retirement |
| Final retirement plus two old snapshots | Ideal anchor | depth 5; 9 states; 17 transitions | No counterexample within bound |

The shortest active-epoch fork is:

1. two honest parties vote and install-vote for request A while the third honest
   party remains at genesis;
2. the two Byzantine signatures complete a 4-of-5 certificate for A;
3. one participating honest database is restored to genesis;
4. that restored party, the honest party that never advanced, and the two
   Byzantine parties present four matching genesis summaries;
5. the two honest genesis parties vote and install-vote for request B; and
6. the Byzantine parties complete a conflicting 4-of-5 certificate for B.

This trace disproves the prior intuition that one restored honest database was
safe because a quorum needed two restored honest parties. One honest party can
be stale without rollback because certificate dissemination and installation
are not atomic across all parties.

## Scope Decision

Party-quorum summaries remain useful for fetching certificates and detecting
ordinary disagreement, but they are not a rollback anchor. A full
rollback-resistant attempt-bound claim would require an independently
administered, strongly consistent monotonic witness with at least this contract:

- one checkpoint namespace per exact `(bid, epoch, config_digest)`;
- an authenticated read returning sequence, head/certificate digest, and
  active/retired status;
- conditional advance from one exact checkpoint to the next only after
  validating the matching quorum certificate;
- a signed or otherwise independently verifiable receipt bound to that advance;
- no usable authorization, freshness statement, TPASS response, lifecycle
  activation, or retirement without the matching current receipt; and
- fail-closed behavior when the witness is unavailable, rolled back, forks, or
  disagrees with local state.

The scoped paper does not add this witness or claim the corresponding property.
Doing so would change the architecture by introducing another safety and
availability authority, so it is future work rather than a Cycle 1 requirement.
If pursued later, the witness should store only public identifiers, hashes,
sequence/status, and timing;
it receives no cues, blinded password material, TPASS shares, recovered secret,
wrapping key, or private key. It nevertheless becomes a safety and availability
dependency. Its compromise may fork or restore attempt budget, its outage blocks
new recovery work, and its metadata can correlate recovery activity. Those
tradeoffs must be measured and stated in the paper.

## Future Test And Evaluation Plan

Any future rollback-resistant runtime slice should turn the two shortest model traces into service
tests with attacker-controlled SQLite/volume restoration. It must also test
anchor compare-and-set races, stale and forged receipts, outage, restart,
retirement, exact retry, and privacy-safe output. Evaluation must report witness
round trips, certificate/receipt bytes, recovery latency overhead, availability
loss during witness outage, and recovery behavior after party restore.

The model should later expand to the resilient 5-of-7 profile, more request
identities, budget boundaries, explicit response freshness, admission replay,
configuration replacement, and crash points. Those extensions supplement but do
not replace a semi-formal security argument or runtime adversarial evidence.

## Paper Implication

The model supports reporting a concrete design counterexample and explaining why
the current attempt ledger is only best-effort local enforcement. It does not
support saying that LOCUS is rollback-resistant or globally rate-limited. The
scoped paper therefore treats online attempt bounding as a deployment assumption
and future mechanism, not a LOCUS result.
