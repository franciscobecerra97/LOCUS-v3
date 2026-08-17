# Active Claim/Evidence Matrix

This matrix separates what the retained baseline supports from what a changed
improvement profile would need. Baseline evidence never transfers merely
because code was derived from the same repository.

P1.4 protects the existing identifier corpus and reserves future evidence
families, but it creates no implementation or security evidence. A reservation
does not advance any claim status, and later claims must cite the exact assigned
profile and result schema.

P1.5's normative per-claim asset, adversary, assumption, boundary, positive
control, expected-observation, and interpretation-limit fields are in
`docs/security-matrix-v1.json`. That prospective contract does not promote the
statuses below; implementation and evidence gates remain controlling.

D023 makes the exact implemented P7.5 deployment manifest and its UI-to-service
graph the required system boundary for C07--C16 and C21--C26 wherever those
rows concern deployed behavior. Component tests and historical profiles remain
supporting controls only. P7.5's completed implementation gate creates no
retained evidence, changes no claim status, and does not authorize pooling
retained results with the new profile.

D024 makes `prototype_final/` the sole active source for that graph. Root
commands and component suites remain supporting controls and cannot satisfy a
new integrated-system evidence requirement.

D025/P7.7 changes the future system boundary to the now-assigned managed
deployment, including Manager/controller, dynamic Client, client recovery-
package, and clean-client-v2 surfaces. P7.7 is complete, but no retained P8/P9
evidence was collected. No row below changes status: the D023 development gate
remains a supporting predecessor, and only later evidence bound to the assigned
D025 profile may support a new central system claim. The assigned security-
matrix-v2 artifact pins v1/C01--C26 and adds managed contracts M01--M05; it is a
governance profile, not an evidence result.

D026/P8.2 now supplies the first separately versioned D025 managed-state
corpus: exactly 42 aggregate-only SB01--SB14 reports (18 Yi, 18 aPPSS, six
common) bound to clean commit `6e30456`. This adds exact-profile implementation
evidence but changes no manuscript claim status: D019 independent review,
P8.3 network-flow evidence, P9 evaluation, artifact reproduction, and a
separate manuscript delta remain open.

Status values include `Supported for exact baseline`, `Partial for exact
baseline`, `Unsupported in improvement profile`, `In progress`, `Disproved`,
and `Explicit non-claim`.

| ID | Property | Frozen baseline status/evidence | Improvement-profile status/evidence required |
| --- | --- | --- | --- |
| C01 | Existing v1 CuePolicy remains byte-compatible | Supported by the frozen cue-policy vectors | P1.3/P5.1 pin the frozen CuePolicy and Yi vector digests and preserve exact bytes/errors through the active adapters; P8 keeps this as a regression control rather than new retained evidence |
| C02 | Common CuePolicy interface supports materially different policies | Unsupported | P5.3/P5.4 implement the three atomic policies, shared corpus, exact registry, `NoResolver`, independent consumer, and cross-policy rejection; P7.5 exercises all four policies, while any promoted system claim still requires P8 evidence |
| C03 | Cloud state lacks a local cue verifier | Supported for the exact v2 cloud snapshot boundary | D026/P8.2 adds schema-bound aggregate cloud/gateway/provider observations for all four managed arms; interpretation remains implementation-scoped pending P8.3, D019, and artifact reproduction |
| C04 | Fewer-than-threshold party state lacks a local cue verifier | Supported for the exact v2 one-party Yi snapshot boundary | D026/P8.2 retains separate Yi/aPPSS 2-of-3 and 3-of-5 coalition reports with fixed positive controls; aPPSS manuscript reliance still requires D019 human validation and the result is not a proof |
| C05 | Matching cloud plus below-threshold parties lacks a local verifier | Supported for the exact v2 matching Yi combined snapshot | D026/P8.2 retains exact suite/topology-bound aggregate union reports without pooling or raw state; P8.3 and D019 remain open |
| C06 | RecoveryDescriptor and recovery bundle do not add an offline predicate | Not part of baseline | D026/P8.2 retains the exact managed disclosure/state view under newly assigned result schemas; endpoint-memory, traffic, and real-provider surfaces remain outside this result |
| C07 | Clean client authenticates descriptor, bundle, and current epoch | Not part of baseline | P7.5 drives distinct Client B through admitted discovery, signed pointer/bundle/descriptor validation, gateway retrieval, and party-current quorum; P8 must retain substitution, stale-state, rollback-boundary, and positive-control observations |
| C08 | Clean client recovers exact original key | Baseline proves a fresh process, not a clean device | P7.5 isolates ephemeral Client A/Client B roots and recovers the exact key through the full graph; P8/P9 must bind retained byte-equality/fingerprint observations to the exact manifest |
| C09 | Enrollment uses authenticated confidential remote transport | Baseline uses trusted provisioner/direct volume writes | P7.5 performs authenticated suite initialization and recipient-local delivery across the integrated graph; P8 must retain endpoint, replay, output, and role-state observations under the exact profile |
| C10 | Provider-neutral public admission resists replay and cross-context reuse | Not part of baseline | P7.5 places the local synthetic issuer, independent verifiers, and admitted gateway on the integrated path and rejects replay; P8 must complete the cross-context matrix there, while external OIDC remains optional and separate |
| C11 | Successor publication is crash-safe | Partial inherited implementation | P7.5 executes all four same-/cross-suite directions through the provider, descriptor, party, and client paths and resumes eight injected effects; P8 must close the complete deployed transition matrix and retain schema-bound observations |
| C12 | General party replacement is safe for tested membership changes | Not part of baseline | P7.5 does not promote general replacement. Any later approved replacement claim must use an exact newly versioned integrated graph with old/new binding, readiness, activation, retirement, and crash evidence |
| C13 | Storage adapters obey the same immutable backup/descriptor/bundle contracts | Supported for inherited filesystem and S3-compatible backup adapters only | P7.5 routes all four storage roles through the admitted gateway to the local S3-compatible service; P8 must retain exact integrated contract/failure observations, while optional AWS requires separate authorization/profile/evidence |
| C14 | Multi-host deployment has disjoint keys/state/network roles | Not part of baseline | P6.4 still requires topology audit and role snapshots on the exact separate hosts. D023's same-host integrated graph is a supporting configuration and does not satisfy or weaken the multi-host gate |
| C15 | Independently administered parties | Explicit non-claim | D023/P7.5 remains one-host, one-operator research infrastructure; only actual distinct operators with separately versioned operational evidence could change this non-claim |
| C16 | UI does not persist or expose prohibited material | Not part of baseline | P7.5 connects the UI/client gateway and passes dynamic output and role-state scans; P8 must retain exact integrated persistence/log/telemetry/history/clipboard/crash/post-operation observations with positive controls, without claiming forensic erasure or screenshot prevention |
| C17 | Global rollback-resistant attempt bound | Disproved for inherited quorum-only model | Separate owner-approved monotonic architecture and evidence |
| C18 | Human memorability or usability | Explicit non-claim | Separate ethics-approved human study |
| C19 | Cryptographic implementation independently audited | Explicit non-claim | Independent qualified review/audit |
| C20 | Production readiness | Explicit non-claim | Out of current scope |
| C21 | Recovery-bundle decoding and publication fail closed | Not part of baseline | P7.5 carries canonical bundles through the integrated gateway/provider/current-pointer workflow and checks stale CAS/exact retry; P8 must add malformed, digest, size, path, and publication negatives at that boundary before retained collection |
| C22 | Storage access is narrowly scoped and nonpersistent at the client | Not part of baseline | P7.5 exercises D004/D015 on the integrated UI/client-to-provider path with no client provider credential/list operation; P8 must complete the wrong-scope/key/nonce/expiry/replay/outage/output matrix. External identity-provider behavior remains optional and separate |
| C23 | The aPPSS profile correctly recovers the exact 16-byte high-entropy `S_R` only for the enrolled suite/password and a valid reconstruction subset | Not part of baseline; retained Yi results do not transfer | P7.5 demonstrates correct/wrong, no-fallback, every exact subset, below-threshold failure, and exact-key behavior for aPPSS 2-of-3 and 3-of-5 through authenticated services; P8/P9 retained evidence and D019 human mapping validation remain pending |
| C24 | Fewer than reconstruction threshold `k` aPPSS server states provide no local offline cue-verification predicate under the declared assumptions | Not part of baseline | Theorem 2/Figure 4 mapping and required human review remain independent prerequisites; P8 must capture every below-`k` coalition plus matching cloud/descriptor/omega state from the exact P7.5 integrated profile and run bounded networkless tests and positive controls without claiming side-channel, adaptive, or online-interaction security |
| C25 | At least `k` compromised aPPSS server states enable offline dictionary testing but do not directly disclose `S_R` before a correct cue-derived password guess | Not part of baseline; the frozen Yi implementation has a different threshold-compromise failure mode | P8 must derive fixed aggregate-only exact-threshold/all-server aPPSS views and matched Yi comparators from each applicable P7.5 suite/topology arm under one common-condition manifest; no candidates or secrets may be retained, and conditional entropy plus unrate-limited guessing remain explicit limitations |
| C26 | Explicit Yi/aPPSS enrollment selection and same-suite/cross-suite successors cannot mix suites, fall back during recovery, or retire a predecessor before a recoverable successor exists | Not part of baseline | P7.5 exercises both enrollment suites and all four successor directions through descriptor-bound dispatch, readiness, publication, activation, and retirement; P8 must retain the no-fallback, mixed-state, crash, and exact-retry matrix while preserving the frozen Yi regression |

Update this matrix with exact profile identifiers, evidence paths, and owner
decisions as work progresses and before proposing corresponding manuscript
changes.
