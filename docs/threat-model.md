# LOCUS Threat Model

Status date: 2026-07-22. This document describes the scoped paper-facing system and explicitly distinguishes current evidence, deployment assumptions, non-claims, and future mechanisms. It must remain synchronized with `paper/main.tex`, `docs/limitations-and-assumptions.md`, `docs/claim-evidence-matrix.md`, `docs/crypto-design.md`, and security-critical implementation behavior.

## System And Security Objective

LOCUS protects a private key by encrypting it under material derived from a TPASS-recovered group secret. The encrypted backup is stored separately from threshold recovery-party state. A client derives the TPASS password from exactly three structured location-person pairs under a versioned cue policy. Recovery requires the encrypted backup, reproduction of the enrolled canonical recovery input, and online participation from an authorized threshold set.

The primary objective is not to make personal cues unpredictable. It is to prevent cloud compromise, fewer-than-threshold party compromise, or their combination from turning likely cue guesses into an offline correctness test. The remaining online tests are an explicit residual risk; the scoped paper does not claim that LOCUS globally bounds them.

## Roles And Trust Boundaries

### Client

The enrollment and recovery client is trusted while it handles the private key, raw cues, canonical resolver output, the TPASS password, recovered group secret, and wrapping key. The client coordinates protocol messages; any gateway or relay function it performs is not an additional custodian. A fresh recovery client must be able to recover without secret enrollment-client state.

### Cloud object store

The cloud stores a bounded canonical object containing the encrypted backup and public metadata. Filesystem and S3-compatible adapters keep this object outside party configurations/databases and require an exact `(bid, epoch, backup_digest)` reference. The default isolated deployment combines the S3 adapter with five authenticated parties: digest-pinned SeaweedFS receives one generated credential and one dedicated volume on the internal `cloud` network; no party receives that credential, volume, or network. The cloud remains untrusted for confidentiality, integrity, freshness, and availability: it may snapshot, read, delete, corrupt, replay, or substitute objects. Plain HTTP inside the private same-host network is a local-test exception. This is not evidence of independent cloud administration or real-provider behavior.

### Recovery parties

Party `P_i` stores only its own TPASS state, backup/epoch binding, service identity, durable attempt-control state, and privacy-minimized audit records. Parties may crash, be unavailable, be compromised, equivocate, return malformed responses, or selectively refuse service. Fewer than `t` compromised TPASS parties are within the confidentiality model; at least `t` compromised parties are outside it.

### Resolver

The resolver maps user selections to canonical cue records before client-local hashing. The default deployment serves an exactly-three-pair synthetic fixture over a dedicated internal network reached only by the ephemeral client; the fixture is trusted only for reproducibility and the resolver suppresses request logs. An external resolver is outside the storage-privacy boundary and may observe or manipulate queries, candidates, timing, account metadata, and returned records.

### Attempt-control authorization layer

The prototype includes a quorum-certified, hash-chained attempt-ledger slice replicated by the recovery parties. It provides local ordering, exact retry, durable pre-response accounting, and selected crash behavior in the tested same-host execution. It is not part of the scoped positive security claim. P5.13 finds a quorum-only fork after one honest database restore and reauthorization after restored retirement state. An independent monotonic witness is modeled only as one possible future remedy; it is not implemented or assumed by the current architecture. Consequently LOCUS is not claimed to be globally rate-limited, rollback-resistant, or safe against arbitrary subset/concurrency schedules.

### Identity provider and recovery admission

D004 provider-neutral recovery admission with a local synthetic issuer is a
future design in `docs/recovery-authorization.md`; it is not implemented. An
OIDC/PKCE/DPoP adapter is optional. The current deployment authenticates a
synthetic coordinator with pinned mTLS credentials and therefore does not
establish public-client admission, account recovery, or third-party lockout
prevention.

### Administrative authorizers

Threshold administrative authorization is a future design, not an implemented role. Current lifecycle routes are coordinator-only research interfaces using synthetic pinned-mTLS identities. They do not establish public lifecycle authorization, replacement, or safe budget extension.

### Transport and relay

Networks and relays are untrusted. They may observe metadata, delay, drop, replay, reorder, duplicate, or alter traffic. Enrollment shares and recovery messages require authenticated confidential transport and transcript/session binding. A relay may aggregate public response messages but must not be trusted with cues, passwords, private keys, whole secrets, or party states.

### Docker and host operator

Docker Compose is the reproducible local deployment boundary, not an independent-administrator boundary. The host operating system, container engine, and a host administrator with volume/process access are trusted in local experiments. Compromise of that host can expose every local container and is equivalent to broad component compromise. VM/multi-host evaluation is required for stronger isolation evidence.

### Debug, benchmark, and attack tooling

Normal profiles must redact secrets. An unsafe educational mode may reveal synthetic test shares only when explicitly enabled and must never be used for paper-facing security, benchmark, or attack evidence. Raw traces, exception messages, metrics, and attack reports are treated as possible leakage surfaces.

## Assets

- protected private key `sk_U`;
- raw cue selections, resolver queries/results, canonical descriptors, and complete canonical recovery input;
- cue-derived TPASS password scalar `p_M`;
- TPASS party shares and ephemeral witnesses;
- recovered group secret, recovery exponent, HKDF output, and wrapping key;
- service identity and administrative authorization keys;
- active backup identifier, epoch, and freshness state;
- attempt budget, reservations, monotonic history, and audit records;
- recovery availability for an authorized user;
- integrity and reproducibility of experiment results.

## Cryptographic And Operational Assumptions

1. Ristretto255 discrete logarithm and DDH assumptions are adequate for the selected TPASS instantiation.
2. The Yi et al. zero-knowledge variant's stated non-interactive proof-of-knowledge assumption holds for the faithfully mapped proof equation; D019's independent claim-focused mapping review must confirm the equation mapping while retaining that inherited assumption.
3. `G2` has no known discrete logarithm relative to `G1`; LOCUS derives it transparently by domain-separated hash-to-group rather than the source paper's multiparty ceremony.
4. SHA-512 transcript hashing, HKDF-SHA-256, and AES-256-GCM are used with correct domains, encodings, keys, associated data, and nonce uniqueness.
5. Enrollment and recovery transport authenticates endpoints and protects confidential messages.
6. Randomness comes from the operating-system CSPRNG outside deterministic test-only executions.
7. At most `t-1` TPASS parties are compromised for below-threshold confidentiality claims.
8. The implemented compact attempt-ledger profile uses `(n_a=5, f_a=2, q_a=4)`, separate from TPASS threshold `t`. Its local test results are not a global attempt-bound claim.
9. Online rate limiting, abuse prevention, public admission, and false-lockout recovery are supplied by the deployment if required. The paper's conditional guessing equation may use a value `k` only when that external deployment premise is stated; the prototype's configured budget is not evidence of it.
10. Client-side erasure is best effort and does not protect against an already compromised endpoint, swap capture, crash dumps, or forensic recovery outside the platform's guarantees.
11. Human cue min-entropy is not assumed or measured. Any online guessing equation is conditional on an explicitly assumed `h`.
12. Software dependencies, container images, build tools, and the host platform are not malicious. Supply-chain security is checked operationally but is not proved by LOCUS.
13. The active client and current synthetic coordinator credentials are trusted in the present prototype. D004 local-issuer or optional OIDC-adapter behavior is not assumed as an implemented property.
14. Lifecycle and false-lockout administration are deployment responsibilities outside the scoped claim; current coordinator-only lifecycle evidence is explicitly same-host and same-membership.

## Security Properties

- `S1 No offline oracle`: cloud-only, below-threshold, and combined snapshots do not contain a local predicate for cue guesses.
- `S2 Threshold confidentiality`: fewer than `t` TPASS states do not reconstruct the protected secret under TPASS assumptions.
- `S3 Backup confidentiality/integrity`: the private key remains encrypted and modifications fail authentication.
- `S4 State separation`: prohibited cue/key material is absent from cloud, party, log, trace, and normal observability state.
- `S5 Attempt safety target/non-claim`: the design target is documented, but the scoped prototype does not establish a global bound. Only exact local ordering/retry behaviors are claimed where tested.
- `S6 Replay/idempotency`: duplicate delivery or retry of one authorized session does not create a new password evaluation or consume unintended additional budget.
- `S7 Freshness/lifecycle`: stale or mixed cloud objects are rejected when current honest party binding metadata is available; selected same-host lifecycle mixes are rejected. Party-database snapshot rollback is not defended.
- `S8 Error normalization`: external failures reveal no finer cue-correctness signal than one counted online recovery outcome.
- `S9 Resolver-boundary clarity`: storage privacy is not misrepresented as resolver privacy.
- `S10 Conditional availability`: tested recovery succeeds when its required TPASS parties, compact ledger participants, cloud object, resolver behavior, credentials, and client endpoint are available. No general liveness guarantee is made.

## Adversary Classes

Each adversary entry gives capabilities, information obtained, claimed property, residual risk, required evidence, and limitations.

### A1 Cloud-only compromise

1. **Capabilities:** read/snapshot all cloud objects and public metadata; delete, corrupt, replay, or substitute objects; observe cloud access metadata.
2. **Information obtained:** ciphertext, nonce, backup identifier, public TPASS parameters, cue/security policy metadata, sizes, versions, and access timing.
3. **Claimed property:** S1/S3 - the snapshot does not decrypt the private key or provide an offline cue predicate; modification is detected when current honest party binding metadata is available. Claim IDs CLM-05 and CLM-08.
4. **Residual risk:** deletion, traffic analysis, policy leakage, stale-object availability attacks, and online guessing remain.
5. **Evidence:** current paper argument; pinned local AES-256-GCM/HKDF path; bounded canonical filesystem and SigV4 S3-compatible adapters; conditional immutable create/exact retry; explicit not-found/unavailable/corrupt/conflict outcomes; and digest, exact-format, AAD, tamper, stale-epoch, substitution, deletion, and snapshot-separation tests. P6.2 adds `cloud-snapshot-no-offline-predicate-v1`: a one-shot collector copies the exact stored S3 bytes plus public locator/integrity metadata into a strict two-file volume, then a separate non-root, credential-free, read-only, networkless container validates and exercises two synthetic candidates. Its retained 2026-07-23 record reports zero candidate signals, network attempts, excluded-path accesses, or prohibited-material findings; positive controls detect an injected verifier and attempted file/network access. The normal Compose gate separately stores/reads the backup through SeaweedFS and recovers through five mTLS parties.
6. **Limitations:** the retained P6.2 run is bounded implementation evidence, not a cryptographic proof or real-provider experiment, and still needs independent clean-host reproduction. A malicious cloud can delete data or observe access metadata. The tested backend is local SeaweedFS over one internal plaintext network. Host memory, deleted blocks, provider logs/control planes, multi-epoch correlation, real-provider forensics, independent cloud administration, and rollback of every trusted freshness source remain outside this result.

### A2 Fewer-than-threshold party compromise

1. **Capabilities:** compromise up to `t-1` parties; read their serialized state, counters, logs, service keys, and retained messages; make compromised parties deviate or collude.
2. **Information obtained:** fewer than `t` password/secret/digest shares, public recovery metadata, local attempt history, and any metadata improperly logged.
3. **Claimed property:** S1/S2/S4 - the coalition cannot reconstruct the secret or validate cue guesses offline. Claim ID CLM-06.
4. **Residual risk:** coalition members can refuse, leak metadata, spend or bypass their own local counters, accumulate shares across poorly retired epochs, and participate in online guesses.
5. **Evidence:** Yi et al. assumptions, Rust threshold tests, and storage design. P6.3 adds `t-minus-one-party-snapshot-no-offline-predicate-v1` for the deployed 2-of-3 profile: after one normal synthetic recovery, party 1 is stopped and a trusted networkless collector copies every regular persistent file into a canonical manifest-bound snapshot. A separate non-root, credential-free, read-only, networkless process validates the authorizer/TLS material, party-1 native share and public parameters, and exact SQLite checkpoint before exercising two synthetic candidates. The retained 2026-07-23 record reports one compromised party at threshold two, zero candidate signals, network attempts, excluded-path accesses, or secret-output exposures, valid snapshot state, and no cloud material; positive controls detect a test-only Boolean verifier and file/network attempts.
6. **Limitations:** the retained P6.3 run is bounded implementation evidence, not a cryptographic proof or real compromise, and still needs independent clean-host reproduction. It covers one stopped persistent snapshot, one party/profile/epoch/checkpoint, and no live memory, logs, traces, side channels, cumulative or multi-epoch compromise, malicious online behavior, or other-party/cloud state. The claim ends at `t` compromised parties and assumes no offline verifier is introduced by uninspected state or artifacts. P6.4 separately tests only the exact matching cloud-plus-party union described below.

### A3 Cloud plus fewer-than-threshold parties

1. **Capabilities:** combine A1 and A2 snapshots and coordinate online activity.
2. **Information obtained:** encrypted backup/public metadata plus fewer than `t` complete party records and histories.
3. **Claimed property:** S1 - the combined snapshot still lacks an implemented local cue correctness predicate. Claim ID CLM-07.
4. **Residual risk:** online attempts, metadata-assisted candidate ranking, deletion/refusal, accumulated compromise, and future threshold compromise remain.
5. **Evidence:** composition argument plus P6.4 `cloud-plus-t-minus-one-party-snapshot-no-offline-predicate-v1`. After one normal synthetic recovery, the disposable profile stops party 1 and uses the existing trusted collectors to create the exact P6.2 cloud and P6.3 party sub-snapshots. A separate credential-free, networkless finalizer independently validates both and exclusively publishes a top-level manifest only when backup identifier, epoch, backup digest, and TPASS public parameters match. A separate non-root, credential-free, read-only, networkless process validates the complete union and tests two fixed synthetic candidates. The retained 2026-07-23 record reports one compromised party at threshold two, zero candidate signals, network attempts, excluded-path accesses, or secret-output exposures, valid sub-snapshots, and a matched combined binding. Output scanning and exact-project cleanup passed; positive controls detect an injected verifier, file/socket access, malformed or extra inputs, sub-manifest substitution, and manifest-consistent mismatched enrollments.
6. **Limitations:** the retained P6.4 run is bounded implementation evidence, not a cryptographic proof or compromise mechanism, and still needs independent clean-host reproduction. It covers one matching cloud object and one stopped party-1 persistent snapshot at one profile/epoch/checkpoint. It excludes live memory, logs, arbitrary traces, side channels, multiple/cumulative or cross-epoch compromise, independently administered roles, endpoint compromise, leaked group/wrapping secrets, and cloud plus `t` parties. Online attempts and metadata-assisted candidate ranking remain possible.

### A4 Online cue-guessing client

1. **Capabilities:** submit chosen candidate cues/password-derived requests, choose and rotate party subsets, retry, abort before completion, and observe generic accept/reject outcomes.
2. **Information obtained:** public backup policy, service availability, authorization decisions, timing, and one correctness outcome per completed counted session.
3. **Claimed property:** S1/S8 only - candidate checks remain online rather than becoming a cloud/below-threshold offline oracle, and tested external failures are normalized. The equation `min(1, k*2^-h)` is conditional on a deployment independently enforcing `k`; LOCUS does not establish that premise. Claim IDs CLM-09 and CLM-10.
4. **Residual risk:** the attacker may submit unbounded online sessions if deployment controls permit it; obvious cues can succeed quickly; controls can cause lockout; timing/metadata may aid ranking.
5. **Evidence:** conditional mathematical bound, exact local retry tests, and the P5.13 counterexample showing that the current quorum ledger is not rollback-resistant global enforcement.
6. **Limitations:** TPASS does not eliminate or bound online guessing, and LOCUS does not claim a measured value for `h` or an enforced value for `k`.

### A5 Public-information attacker

1. **Capabilities:** collect public posts, photos, workplaces, travel history, family/social links, breaches, and public directory data to rank cues.
2. **Information obtained:** auxiliary information correlated with the user's three selected cue pairs.
3. **Claimed property:** S1 - public knowledge does not become an offline storage oracle; guesses still require online TPASS sessions. Claim IDs CLM-05, CLM-10, and CLM-20.
4. **Residual risk:** conditional cue uncertainty may be very low and the correct input may appear early.
5. **Evidence:** threat analysis; planned synthetic guessing curves under configured budgets.
6. **Limitations:** no claim that personal cues have high entropy or resist targeted public-information guessing.

### A6 Social-knowledge attacker

1. **Capabilities:** use personal knowledge of friends, relatives, schools, workplaces, frequent locations, relationships, and life events.
2. **Information obtained:** stronger user-specific candidate information than an ordinary public attacker.
3. **Claimed property:** S1 - social knowledge changes guess ranking, not the offline-oracle boundary; tests remain online but are not claimed to be globally bounded by LOCUS.
4. **Residual risk:** a close acquaintance may guess within a very small budget.
5. **Evidence:** threat analysis and planned synthetic/persona attacker models.
6. **Limitations:** LOCUS does not hide facts already known to the attacker and provides no empirical human-memory or social-guessing result.

### A7 Resolver observer or compromise

1. **Capabilities:** observe, log, correlate, delay, modify, omit, or reorder external resolver queries/results; associate them with an account or network identity.
2. **Information obtained:** raw query terms, candidates, selected records, timing, locale, provider identifiers, and possibly all three cue relationships.
3. **Claimed property:** S9/S4 - cloud and parties need not receive raw resolver data, but resolver privacy is not claimed. Claim ID CLM-13.
4. **Residual risk:** observation reduces `h`; manipulation causes failure or controlled canonicalization drift; collusion can improve online guesses.
5. **Evidence:** paper data-flow argument; frozen cue policy; and a deterministic HTTP fixture on an isolated `resolver` network reached only by the client. The deployment client canonicalizes exactly three synthetic pairs and completes recovery while the resolver omits request logs. The fixture is bound to exact canonical bytes and locale/Unicode rejection vectors. A versioned drift corpus defines stable rename/reindex behavior, across-grid/contact drift, and generic local failure for provider-profile changes, ambiguity, and missing results. Network trace analysis, external/self-hosted comparisons, counted-attempt integration, and quantitative leakage evaluation remain required.
6. **Limitations:** hashing after lookup cannot conceal the lookup; private lookup is outside the baseline unless implemented as an optional mode.

### A8 Network and replay attacker

1. **Capabilities:** observe metadata; delay, drop, reorder, duplicate, replay, or alter enrollment/recovery messages; attempt role impersonation.
2. **Information obtained:** endpoints, timing, sizes, availability patterns, and any plaintext traffic if transport is misconfigured.
3. **Claimed property:** S3/S6 - authenticated confidential transport and session/epoch/request binding reject alteration, impersonation, and replay as fresh work. Claim ID CLM-24.
4. **Residual risk:** traffic analysis and denial of service remain; compromised endpoint credentials allow impersonation.
5. **Evidence:** initial enrollment, ledger, live freshness, native commitment, and native response operations use TLS 1.3, mutual CA validation, exact client/server certificate pins, bounded duplicate-free JSON, canonical signed objects, strict base64url TPASS encodings, and exact remote retries across local subprocesses. Every mutating POST requires a 32-byte HTTP idempotency key durably bound to the authenticated certificate, route, and canonical body before dispatch; exact status/body bytes survive restart. P3.2 starts party processes without native state in their boot files, delivers one recipient's state per request, rejects wrong-recipient state and changed-body key reuse, and confirms separate databases retain only their own packages. Existing tests reject a missing key, cross-session reuse, delayed transcript replay, same-CA but unpinned clients, duplicate JSON, wrong roles, unknown routes, and cross-session response use. D004 public admission, arbitrary packet scheduling, certificate lifecycle, and rollback tests remain.
6. **Limitations:** the current evidence is a same-host test using synthetic credentials and test-provisioned configuration. Transport security does not fix an authorized malicious client, compromised party process, leaked service key, rollback, denial of service, or traffic analysis.

### A9 Cloud and party-state rollback attacker

1. **Capabilities:** restore prior cloud objects, party databases, counters, logs, certificates, or complete container volumes; mix versions across parties and epochs.
2. **Information obtained:** old valid ciphertext/state and an opportunity to reset or fork freshness/attempt history.
3. **Claimed property:** S7 only for cloud binding and tested lifecycle mixes - stale cloud content is rejected when current honest party metadata identifies the intended object. No party-state rollback property is claimed. Claim IDs CLM-08 and CLM-15.
4. **Residual risk:** restored party databases can fork attempt history or reactivate retired state; coordinated cloud/party rollback can present a consistent old view; fail-closed handling can deny service.
5. **Evidence:** the cloud reference binds `(bid, epoch, backup_digest)`; signed authorizer configuration v2 and each durable party database schema v5 pin the same backup digest and exact active runtime package. The P4.9 lifecycle signs consecutive epochs and preserves predecessor head/count/budget through retirement. The registered Compose scenario passed cross-epoch substitution, partial activation, restart, predecessor refusal, successor recovery, scanning, and cleanup. Separately, the P5.13 bounded model finds a conflicting 4-of-5 certificate after one honest database restore and authorization after retired-state restoration under quorum-only reconciliation; the corresponding ideal-witness scenarios have no counterexample within their frozen bounds. Runtime snapshot restoration and a real witness remain required.
6. **Limitations:** bounded model exploration is not a proof or runtime evidence. Ordinary durability, live party freshness, signed forward transitions, and party-quorum summaries are not rollback resistance. The current lifecycle is same-membership, lacks public administrator authorization and party replacement, and has not restored attacker-controlled database snapshots. The ideal witness is not implemented.

### A10 Malicious or unavailable recovery parties

1. **Capabilities:** crash, delay, selectively refuse, equivocate, send malformed proofs/responses, expose inconsistent state, or collude below threshold.
2. **Information obtained:** their own states, authorized request transcripts, participating-set metadata, and local audit information.
3. **Claimed property:** S2/S8/S10 - malformed values are rejected, below-threshold deviation does not reveal the secret, and recovery succeeds when required honest quorums remain available. Claim IDs CLM-04, CLM-09, and CLM-22.
4. **Residual risk:** denial of service, latency inflation, metadata leakage, and authorization-quorum unavailability remain.
5. **Evidence:** Rust tampered-proof/response tests; classified transport tests prove one exact retry for ambiguous timeout/`request_in_progress`, no retry for protocol faults, and a hard two-delivery ceiling. Deterministic coordinator tests tolerate one slow-unavailable or malformed authorizer, fail with two unavailable authorizers, and fail closed on an observed conflict. Recovery tests exclude stale parties, freeze the pre-authorization TPASS subset, enforce phase deadlines, and prohibit a post-authorization subset switch. The live five-process and Compose paths recover through parties 2 and 3 while party 1 is stopped, with the certified count advancing rather than resetting.
6. **Limitations:** availability cannot be guaranteed below required TPASS and attempt-authorization quorums. The evidence is same-host and deterministic; arbitrary Byzantine scheduling, equivocation across network deliveries, independent-host faults, and tail-latency distributions remain P6/P8 work.

### A11 Concurrent-session attacker

1. **Capabilities:** open many simultaneous sessions against overlapping or disjoint subsets; race checks/updates; induce retries, timeouts, and crashes at state transitions.
2. **Information obtained:** multiple authorization decisions and any responses issued before counters converge.
3. **Claimed property:** S6 only at the tested service boundary - exact duplicate delivery maps to stored local work and selected conflicting local races fail closed. No arbitrary-schedule overrun bound is claimed. Claim IDs CLM-11/12 are removed as positive system claims.
4. **Residual risk:** strict serialization reduces throughput; abandoned reservations can consume budget; recovery administration may be needed.
5. **Evidence:** SQLite `BEGIN IMMEDIATE` serializes durable HTTP-key and ledger locks. A focused two-thread same-key race yields one executor and one `request_in_progress`; a separate two-coordinator conflicting-slot race yields at most one local certificate; changed reuse fails before dispatch. The coordinator now collects quorum phases concurrently under explicit phase/operation deadlines and exact transport retries preserve the idempotency key and body. Recovery phases concurrently call one subset fixed before authorization and never switch after consumption. The subprocess/Compose suites cover duplicate delivery, restart recovery, and one-party fallback. Systematic concurrent network scheduling, crash injection at every boundary, broad subset rotation, and measured overrun remain required.
6. **Limitations:** current HTTP startup recovery assumes one exclusive process owns each party database. Completed idempotency records have no bounded compaction policy, so an enrolled caller can cause database growth. These focused races do not establish any global bound.

### A12 Lockout denial-of-service attacker

1. **Capabilities:** target a known/public backup or account identifier with authorized-looking requests to exhaust attempt budget without knowing cues.
2. **Information obtained:** admission decisions, cooldown/lockout timing, and service availability.
3. **Claimed property:** none in the current prototype. P3.3 specifies that a public identifier alone is insufficient: admission additionally requires an issuer-signed, short-lived, exact-scope capability and its bound client proof key. Deployment abuse controls remain required.
4. **Residual risk:** compromise of the admitted identity/client proof key,
   selected issuer, administrator threshold, or sufficient parties can still
   cause false lockout; pre-authentication bandwidth denial remains.
5. **Evidence:** `docs/recovery-authorization.md`, the strict P3.3 codec/schema,
   and its fixed vector specify subject/backup/epoch/operation/audience/key/
   nonce/time/prefix bindings. P3.3 negatives cover cross-account/prefix use,
   malformed scope, excessive lifetime, and noncanonical input. Issuance,
   P3.4 implements proof validation and digest-only replay persistence across
   separate verifier databases. It does not establish deployment-wide false-
   lockout prevention or a paper claim.
6. **Limitations:** preventing guessing and preventing lockout are conflicting goals; no design eliminates denial of service by sufficiently privileged parties.

### A13 Endpoint compromise

1. **Capabilities:** control the enrollment or recovery client, read memory/keystrokes/files, alter UI/resolver output, steal credentials/private keys, or replace binaries.
2. **Information obtained:** raw cues, canonical input, TPASS password, protected private key, recovered secret, wrapping key, and all client-side messages.
3. **Claimed property:** none for confidentiality during active endpoint compromise. This is explicitly outside S1-S5 and claim scope.
4. **Residual risk:** complete key/cue theft, malicious enrollment, silent redirection, and persistent compromise.
5. **Evidence:** limitation statement and planned secret-lifetime/logging controls only.
6. **Limitations:** best-effort erasure protects neither a compromised endpoint nor platform-level forensic capture.

### A14 At-least-threshold party compromise

1. **Capabilities:** obtain `k` or more matching holder states, use the selected suite's threshold-compromise path, forge holder participation, and bypass honest-holder availability.
2. **Information obtained:** Yi threshold state directly reconstructs the shared input scalar, protected exponent, and digest; aPPSS threshold state plus public `omega` enables unrate-limited offline dictionary testing and releases `S_R` for a correct input. With the matching cloud object, either successful path can recover the protected key.
3. **Claimed property:** no threshold-confidentiality guarantee. Detection, replacement, monitoring, and post-compromise rotation are operational mitigations only.
4. **Residual risk:** Yi exposes its recovery output without guessing; aPPSS security at threshold degrades to offline guessing and is only as strong as the input distribution. Retrospective compromise of unretired epochs remains possible.
5. **Evidence:** P5A.6 supplies a fixed, aggregate-only, non-retained 2-of-3 implementation regression over every exact-threshold subset and all-server view. The inherited cryptographic results require separate review.
6. **Limitations:** the regression is not proof, retained evidence, an entropy result, or a proactive/adaptive guarantee. LOCUS is not proactive secret sharing until a reviewed refresh/re-sharing mechanism is implemented.

### A15 Host, operator, observability, or debug compromise

1. **Capabilities:** read Docker volumes/process memory, enable unsafe flags, collect logs/traces/crash dumps, alter images/configuration, or combine all locally deployed roles.
2. **Information obtained:** potentially every local secret and all component state if the host/operator is privileged.
3. **Claimed property:** normal observability and artifacts exclude prohibited material; no security claim survives a malicious all-powerful local host. Claim IDs CLM-02, CLM-17, and CLM-23.
4. **Residual risk:** accidental logging, synthetic/real mode confusion, image tampering, and administrative misuse.
5. **Evidence:** Rust debug redaction test, `.gitignore`, the application-layer output-safety contract, and the default deployment gate. Recursive validation rejects prohibited nested fields and private-key markers before benchmark or deployment serialization; experiment configurations use the same guard; operator diagnostics omit exception messages. The deployment gate validates pinned images, read-only roots, capabilities, disjoint mounts/networks, provisioned role snapshots, and combined output against generated credentials and known cue/key/state markers. It also exposed and corrected upstream SeaweedFS informational logging of the access key. Process-memory/crash-dump/trace scans, future-profile gating, clean-host review, and independent-host evidence remain required.
6. **Limitations:** Docker isolation is not a defense against the host administrator and must not be presented as one.

### A16 Identity-provider or administrative-authority compromise

1. **Capabilities:** a compromised D004 issuer can mint or deny ordinary
   admission capabilities, observe bounded authentication metadata, and
   correlate its pseudonymous subject; a compromised administrator threshold
   can sign configured high-impact actions. An optional OIDC adapter adds its
   provider's observations and account behavior.
2. **Information obtained:** pseudonymous identity/authentication metadata,
   recovery timing and identifiers exposed to the issuer, or administrative
   action/head metadata. These roles do not receive cues, TPASS
   passwords/shares, recovered secrets, wrapping keys, or private keys by
   design.
3. **Claimed property:** none for issuer or administrator compromise. The local
   synthetic issuer is implemented only as a research test double. CLM-14 has partial evidence for the
   implemented cloud, party, resolver, and coordinator roles only; the design
   observation that a future IdP or administrator role would lack recovery
   material is not implementation evidence.
4. **Residual risk:** bounded online guessing, lockout, account denial, identity correlation, emergency retirement, and policy-bounded budget extension are possible; collusion with sufficient recovery parties or endpoint compromise is stronger.
5. **Evidence:** D004 and P3.3 now freeze the provider-neutral contract. A
   stolen bearer capability must still satisfy the exact audience/operation/
   backup/epoch/prefix and possess its proof key; a malicious admitted client
   can request permitted online attempts and cause lockout; issuer compromise
   can mint such capabilities; issuer unavailability denies new capabilities;
   and the issuer/authorizers/gateway observe pseudonymous subject, scope, and
   timing. P3.4 tests exact-scope theft/key/replay negatives, unauthorized
   synthetic subjects, digest-only state, and independent verifier databases.
   It cannot model external account recovery, issuer outages beyond denial,
   or production abuse. Administrator-threshold work stays separate. OIDC/DPoP
   tests apply only if that optional adapter is added.
6. **Limitations:** LOCUS does not solve real issuer account recovery or prove
   multifactor/phishing resistance. Multi-administrator approval distributes
   but does not eliminate administrative trust.

## Cross-Adversary Composition

Claims compose only where stated. In particular:

- cloud plus `t-1` parties is within CLM-07, but cloud plus `t` parties is not;
- resolver observation plus public/social knowledge reduces candidate uncertainty and must be reflected in assumed `h`;
- a network attacker with stolen service credentials is an endpoint/identity compromise, not merely A8;
- partial rollback plus concurrency directly targets the attempt-control property and must be tested together;
- a future IdP compromise plus public/social cue knowledge could authorize online guesses; the current project does not claim those guesses are globally budget-bounded, although the IdP alone still receives no offline cue verifier by design;
- administrator-threshold compromise plus the ledger quorum can increase the disclosed `B_eff` up to policy limits and must be analyzed as combined authorization compromise;
- a malicious local Docker host collapses the component boundaries and cannot be used as evidence of below-threshold isolation.

## Failure And Disclosure Policy

External recovery returns a generic rejection for wrong cues, malformed protocol messages, stale state, policy mismatch, proof failure, digest failure, and AEAD failure. Parties may record only the minimum admission/reservation/protocol status needed for operations and evidence. Normal logs and status commands must not contain raw cues, canonical descriptors, cue identifiers, password scalars, party shares, ephemeral witnesses, whole group secrets, wrapping/private keys, resolver results tied to real people, or unrestricted client credentials.

Availability failures remain distinguishable where needed for operations, but the public interface must be evaluated to ensure that detailed timing/status does not create a cheaper cue-testing channel.

## Evidence Synchronization Checklist

For each security-relevant change:

1. update the matching CLM rows in `docs/claim-evidence-matrix.md`;
2. update the adversary capabilities, assumptions, and residual risk here;
3. add normal, malformed, adversarial, concurrency, crash, replay, or rollback tests as applicable;
4. update `docs/attempt-control.md` if admission, reservation, retry, counter, or lifecycle behavior changes;
5. update manuscript wording only to the strength demonstrated by the resulting evidence.
