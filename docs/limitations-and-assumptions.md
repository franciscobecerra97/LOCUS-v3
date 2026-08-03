# LOCUS Submission Scope, Assumptions, And Limitations

Status: scope decision for the ASIACCS 2027 Cycle 1 manuscript, 2026-07-22.
This document preserves the core LOCUS idea without requiring every distributed
security problem to be solved in the current prototype.

## Scoped Paper Idea

LOCUS is a storage-separated private-key recovery architecture. A client turns
reproducible structured recovery input into the password input of TPASS; the
cloud stores an encrypted private-key backup; recovery parties store separate
threshold states; and no cloud or below-threshold party snapshot contains a
standalone password verifier.

The paper studies this composition, its deterministic cue-policy and resolver
boundary, its concrete Rust/Python prototype, and the exact point at which
residual guessing becomes an online deployment problem. It does not claim to
solve distributed rate limiting, rollback-resistant state, human memorability,
or production deployment.

This narrower framing accepts a novelty risk: reviewers may view LOCUS as a
careful integration of known TPASS and encrypted-backup techniques. The project
will address that risk through precise architecture, implementation depth,
negative-result analysis, and reproducible evaluation rather than by adding a
new trust authority late in the submission cycle.

## Claims Retained

| Retained claim | Required scope |
| --- | --- |
| Storage separation | The cloud backup excludes party secret states; each party excludes the encrypted private key and whole recovery secret. |
| No cloud-only offline cue oracle | Under the TPASS, AEAD, KDF, hash, and endpoint assumptions, the cloud object alone provides no local predicate for a guessed cue input. |
| No below-threshold offline cue oracle | Fewer than `t` party states do not reconstruct the TPASS secret or provide a local password verifier under the inherited TPASS assumptions. |
| Combined cloud plus fewer than `t` parties | Their combination still lacks a local correctness predicate under the same assumptions. |
| Deterministic cue processing | The frozen exactly-three-pair synthetic policy has canonical ordering, normalization, precision, versioning, and drift behavior. |
| Concrete prototype functionality | The native Rust/Ristretto TPASS, Python orchestration, AES-256-GCM backup, S3-compatible adapter, authenticated party services, and same-host Compose path perform the tested enrollment/recovery flows. |
| Cloud-object integrity binding | A client with honest current party metadata rejects stale, substituted, malformed, or corrupted cloud objects in the tested cases. |
| Conditional online-guessing equation | If an external deployment actually enforces at most `k` online evaluations and cue input has conditional min-entropy `h`, success is bounded by `min(1, k*2^-h)`; LOCUS does not establish either premise empirically. |
| Negative attempt-control result | The bounded model demonstrates that quorum-only reconciliation can fork after one honest database restore; this is a limitation result, not a repaired security property. |

## Claims Explicitly Not Made

- LOCUS is not globally rate-limited, rollback-resistant, durably auditable, or
  concurrency-safe across arbitrary deployments.
- The configured local attempt budget is not an adversarially enforced global
  value of `k` for the paper's guessing equation.
- Party-quorum freshness, signed forward transitions, SQLite durability, and
  same-host restart tests do not protect against attacker-controlled snapshots.
- The current coordinator-authenticated mTLS interface is not public-client
  recovery admission and does not prevent a third party from causing lockout.
- Docker Compose containers are not independently administered recovery parties.
- SeaweedFS is an S3-compatible local conformance service, not real-cloud
  evidence.
- The prototype is not production-ready, independently audited, side-channel
  hardened, or safe for real private keys or personal cue data.
- Location--Person cues are not claimed to be memorable, high entropy, usable,
  stable over time, or better than passwords or recovery codes.
- Synthetic cue vectors and drift tests are not human-subject evidence.
- The current measurements do not establish practical Internet-scale latency,
  throughput, availability, or cost.
- Recovery availability, party replacement, false-lockout recovery, and secure
  lifecycle administration are not complete system properties.

## Cryptographic And Client Assumptions

1. The Yi et al. TPASS security assumptions apply to the implemented parameter
   mapping, including the relevant discrete-log and proof-of-knowledge
   assumptions.
2. Fewer than `t` TPASS parties are compromised. Compromise of `t` or more
   parties is outside confidentiality claims.
3. AES-256-GCM, HKDF-SHA-256, SHA-256, Ed25519, Ristretto255, secure randomness,
   and their pinned library implementations behave as assumed.
4. Canonical encodings and domain separation are used exactly as specified.
5. Enrollment and active recovery endpoints are trusted. Malware, keyloggers,
   memory inspection, and a malicious client can expose cues, the private key,
   recovery secrets, and credentials.
6. Secret erasure is best effort only; managed runtimes, operating systems,
   crash dumps, swap, and host forensics may retain material.

## System And Operational Assumptions

1. Enrollment transport is authenticated and confidential, and party identity
   keys are provisioned correctly.
2. At least `t` correct TPASS parties, the cloud object, and the resolver inputs
   needed by the policy are available during recovery.
3. For cloud rollback detection, the client reaches honest current party
   metadata for the intended backup and epoch.
4. The deployment handles online authorization, rate limiting, abuse prevention,
   monitoring, and false-lockout recovery outside the scoped LOCUS claim.
5. Operators do not present restored party databases as current secure state.
   The prototype cannot reliably detect that event.
6. A successful or compromise-suspected recovery is followed by key rotation or
   re-enrollment according to deployment policy.
7. Resolver records and provider behavior remain reproducible enough for exact
   canonicalization, or the client fails and uses an out-of-band refresh path.
8. The same-host artifact is operated by a trusted host administrator. A
   malicious Docker host collapses all modeled component boundaries.

## Security Limitations

### Online guessing and lockout

TPASS moves residual cue testing online; it does not limit the number of online
sessions. The implemented signed ledger provides useful local ordering,
idempotency, and crash behavior, but not a proven global budget. Weak or publicly
inferable cues may therefore be guessed online, and strict local controls may
deny service to the legitimate user.

### Party-state rollback

The P5.13 model finds a conflicting-certificate trace after one honest database
restore because another honest party may never have installed the latest
certificate. It also finds reauthorization after restored pre-retirement state.
An independent monotonic witness or a stronger reviewed consensus design could
address this class, but either would add trust, metadata leakage, latency, and an
availability dependency. It is future work, not part of the scoped architecture.

### Admission and authorization

D004 provider-neutral admission, credential replay protection, public administrator
authorization, and false-lockout administration are specified but not
implemented. The current mTLS coordinator is a research harness, not an account
recovery authorization system.

### Lifecycle and replacement

The tested lifecycle supports one same-membership direct successor on one host.
It does not implement general party replacement, independent administration,
secure counter migration, authenticated public lifecycle control, or protection
against restored predecessor volumes. A fresh epoch intentionally has a new
disclosed budget and is not continuity of a global lifetime limit.

### Availability and denial of service

Parties, the cloud, resolver, network, coordinator, and host can deny recovery.
The compact 4-of-5 authorizer profile may require more responsive parties than
the TPASS threshold. LOCUS offers no unconditional liveness guarantee.

### Resolver and metadata privacy

An external resolver may observe queries, candidates, account context, timing,
and IP metadata. Parties and the cloud still observe protocol timing, backup or
session identifiers, sizes, and participation. Local canonicalization prevents
raw cue storage at those roles but does not make recovery activity anonymous.

### Cue quality and drift

Exact canonicalization does not supply entropy or tolerant recall. Obvious cues
can be guessed; forgotten cues and provider drift can cause permanent recovery
failure. No fuzzy matching is provided because it could broaden the guessing
surface and change the security construction.

### Implementation and evaluation

The TPASS implementation has regression vectors and tests but no independent
cryptographic audit. The deployment is synthetic and same-host. Runtime memory,
side channels, crash dumps, hostile traces, real providers, independent hosts,
and realistic Internet failure distributions are not evaluated. The retained
v2 corpus provides 30 samples for each of three frozen same-host scenarios; it
does not support production, scale, throughput, concurrency, geographic, or
independent-administration claims.

## Evidence And Reproducibility Limitations

- Bounded state exploration finds counterexamples but does not prove safety when
  none is found.
- Unit and same-host integration tests establish only their exact configured
  behavior.
- Every currently cited bibliography entry and URL was verified during M4.
  Unused bibliography entries remain outside that audit and must be removed or
  verified before artifact-source release.
- `paper/main.pdf` must be rebuilt and visually checked after source edits.
- The corrected v2 paper-facing experiment set is frozen. Anonymous packaging,
  clean-host reproduction, remote CI, and D019's independent human
  Yi/aPPSS/LOCUS mapping validation remain incomplete. D020's internal
  assessment is provisional and does not replace them.
  The project-owner authorization and Apache-2.0/CC-BY-4.0 artifact license
  split are complete.

## Scope-Preserving Next Work

1. Keep the manuscript, threat model, claim matrix, and artifact instructions
   synchronized with the corrected v2 profile.
2. Keep P5.9 rollback anchors, P5.4 public admission, general party replacement,
   and a complete global attempt-bound proof as future work rather than Cycle 1
   blockers.
3. Reproduce the frozen implemented core and retained v2 processing from clean
   Linux and Windows/CI environments; rerun Docker-backed gates where available.
4. Add no new attack or performance breadth unless a retained claim requires
   it; the current P6/P7 corpus is frozen.
5. Complete the anonymous package, D019 human mapping validation, and final
   page/anonymity gates under the approved license split.

This scope permits the project to continue without pretending that an
unfinished distributed rate limiter is part of the demonstrated LOCUS security
boundary.
