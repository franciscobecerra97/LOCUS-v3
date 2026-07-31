# LOCUS Party Timeout, Retry, And Failover Policy

Status: P4.8 implemented and live-verified, 2026-07-21.

## Problem statement

A recovery coordinator must not wait serially for every slow party, retry a
malformed response as if it were a network loss, change the TPASS selected set
after secret-dependent work begins, or accidentally turn an ambiguous timeout
into another counted attempt. The policy must preserve the certified attempt
ledger while allowing recovery whenever the configured authorization quorum and
TPASS threshold remain available.

## Threat assumptions

- A party may be unavailable, slow, selectively refusing, malformed, stale, or
  conflicting. Up to the configured fault bound may behave maliciously.
- Authenticated TLS endpoints and idempotency records work as specified; a
  malicious Docker host or endpoint-key compromise remains outside this result.
- A timed-out mutating request may still finish at the server. Timeout is not
  evidence that no durable lock, vote, certificate, commitment, or response was
  created.
- Coordinated rollback, admission abuse, traffic analysis, and lifecycle
  replacement remain separate P5/P6 work.

## Implemented policy

### Transport calls

The deployed client uses a five-second socket timeout. Internal party-to-party
freshness clients use two seconds. A remote client makes at most two deliveries
of one byte-identical request with the same deterministic or caller-supplied
idempotency key.

Only transport-ambiguous outcomes are retried: connection/TLS/HTTP failure,
`503 authorizer_unavailable`, `500 internal_error`, or
`409 request_in_progress`. A `409 conflict` fails closed. Invalid content type,
oversized/noncanonical JSON, wrong party identity, certificate-pin mismatch,
invalid signatures, and inconsistent result fields are protocol faults and are
never retried.

### Authorization quorum collection

State-summary, entry-vote, install-vote, certificate-install, and freshness-vote
requests are issued concurrently. Each phase has a ten-second deadline and one
authorization operation has a 45-second deadline. All valid replies received
within the phase deadline are sorted by party identifier before certificate
construction, so response arrival order alone cannot change the encoding. Exact
stored results remain authoritative for retry. The compact 4-of-5 profile
continues with four valid replies, including when the fifth party is slow,
unavailable, or malformed. Fewer than four replies produce a classified
`CoordinatorUnavailable` result.

An observed durable `Conflict` is not counted as mere unavailability: the
operation fails closed. Unexpected local programming exceptions also abort
rather than being reclassified as malicious-party tolerance.

### TPASS subset selection and phases

Before constructing or authorizing the attempt entry, the client obtains a
quorum of authenticated state summaries. A TPASS party is eligible only when it
is active and exactly matches the quorum-reconciled installed index, head,
consumed count, budget, and backup digest. The healthy baseline prefers parties
1 and 3; deterministic fallback order is 1, 3, then 2, and the chosen set is
canonically sorted.

If fewer than two eligible TPASS parties exist, recovery stops before attempt
authorization. Commitment and response calls to the fixed selected set then run
concurrently under separate 12-second phase deadlines. Once authorization has
committed, timeout, refusal, or malformed output from either selected party
aborts the recovery; the client never changes to another subset under that
certificate and the attempt remains consumed.

## Invariants

1. A retry preserves caller identity, route, canonical body, and idempotency key.
2. Protocol faults and conflicts are never transport-retried.
3. No quorum threshold is reduced because a party is slow or malicious.
4. Certificate inputs are canonicalized by party identifier, not response time.
5. Only a quorum-consistent TPASS party may be selected before authorization.
6. The selected set is fixed before authorization and never changes mid-phase.
7. Failure before authorization consumes no attempt; failure after the
   authorization certificate exists never restores the attempt.
8. A caller timeout does not cancel or roll back possible durable remote work;
   exact retry and reconciliation remain authoritative.
9. External failure output remains generic and contains no cues, TPASS material,
   private/wrapping keys, credentials, or unrestricted transcripts.

## Failure behavior

- Four valid authorizers plus two quorum-consistent TPASS parties can proceed.
- Two unavailable authorizers in the compact 4-of-5 profile fail before a new
  certificate can form.
- One malformed authorizer reply is excluded; two such failures prevent quorum.
- An observed conflict fails closed even if four other parties could reply.
- Insufficient eligible TPASS parties fail before authorization.
- A selected-party failure after authorization returns a generic recovery
  failure and leaves the certified consumed count unchanged at its incremented
  value.
- A party that missed certificates is excluded from TPASS selection until its
  ledger head is explicitly reconciled. Automatic history transfer remains
  P5.8 work.

## Test plan and current evidence

- Deterministic faulting-peer tests cover one slow-unavailable party, one
  malformed party, two unavailable parties, and an observed conflict.
- Transport tests prove one exact retry for timeout and `request_in_progress`,
  no retry for malformed responses, and a hard two-attempt ceiling.
- Recovery-orchestration tests cover baseline selection, party-1 and party-3
  fallback, stale-party exclusion, insufficient TPASS availability, concurrent
  ordered phases, phase deadline, and no post-authorization subset switch.
- The existing five-process TLS suite exercises 4-of-5 authorization and native
  recovery through parties 2 and 3 while party 1 is stopped.
- The default Compose smoke recovers through 1/3, verifies restart durability,
  then stops party 1 and recovers through 2/3. The certified consumed count
  advances exactly from zero to three and the disposable graph is removed.

## Evaluation plan

P7/P8 should measure healthy and failed-operation latency distributions, timeout
overhead, exact-retry counts, quorum response sets, selected subsets, message
bytes, and abandoned-but-later-completed remote operations. Experiments must
vary one and two unavailable parties, delayed parties at multiple phase
boundaries, malformed responses, and recovery after reconciliation. Development
smoke timings are diagnostic and not paper-facing evidence.

## Paper implications

This implementation can support a narrow claim that the compact local profile
uses bounded concurrent quorum collection, classified exact retries, and
pre-authorization subset fallback without resetting the certified attempt
count. It does not establish Internet deployment availability, Byzantine
liveness, automatic ledger-history repair, rollback resistance, a global
attempt theorem, or acceptable tail latency. Those claims remain gated on P5,
P6, and P8 evidence.
