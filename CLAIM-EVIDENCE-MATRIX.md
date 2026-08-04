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

D023 makes the exact P7.5 integrated deployment manifest and its UI-to-service
graph the required future system boundary for C07--C16 and C21--C26 wherever
those rows concern deployed behavior. Component tests and historical profiles
remain supporting controls only. D023 and P7.5 planning create no evidence,
change no status, and do not authorize pooling retained results with the new
profile.

Status values include `Supported for exact baseline`, `Partial for exact
baseline`, `Unsupported in improvement profile`, `In progress`, `Disproved`,
and `Explicit non-claim`.

| ID | Property | Frozen baseline status/evidence | Improvement-profile status/evidence required |
| --- | --- | --- | --- |
| C01 | Existing v1 CuePolicy remains byte-compatible | Supported by the frozen cue-policy vectors | P1.3 pins the frozen CuePolicy and TPASS-vector digests and verifies unchanged native-Yi behavior through thin typed adapters; aPPSS must later consume the same policy bytes only through its new suite-specific password domain |
| C02 | Common CuePolicy interface supports materially different policies | Unsupported | P1.3 supplies the common typed interface and frozen-v1 adapter only; P5 must add quantized-coordinate, canonical-phone, and canonical-email set implementations, shared conformance, `NoResolver`, and cross-policy rejection |
| C03 | Cloud state lacks a local cue verifier | Supported for the exact v2 cloud snapshot boundary | P2.1 specifies the new descriptor/bundle disclosure surface and unit positive control; P2.3/P2.4 still require the complete cloud/current-pointer/gateway persistent-state capture, bounded candidate test, and credential-safe evidence |
| C04 | Fewer-than-threshold party state lacks a local cue verifier | Supported for the exact v2 one-party Yi snapshot boundary | Every relevant coalition for each new exact suite/profile plus positive controls; aPPSS support additionally requires the reviewed theorem/profile mapping |
| C05 | Matching cloud plus below-threshold parties lack a local verifier | Supported for the exact v2 matching Yi combined snapshot | New suite-bound combined state-surface experiments with exact descriptor/backup/epoch binding |
| C06 | RecoveryDescriptor and recovery bundle do not add an offline predicate | Not part of baseline | P2.1/P2.2 supply strict descriptor/bootstrap schemas, forbidden-field analysis, canonical vectors, and unit positive controls; P2.4 still requires the exact disclosure snapshot, networkless candidate test, and evidence positive control |
| C07 | Clean client authenticates descriptor, bundle, and current epoch | Not part of baseline | P2.2--P2.4 component contracts remain prerequisites; P7.5 must drive a distinct Client B through admitted discovery, signed descriptor/current-state validation, gateway retrieval, and the exact integrated party graph before P8 collects substitution, stale-state, and rollback observations |
| C08 | Clean client recovers exact original key | Baseline proves a fresh process, not a clean device | P7.5 must isolate ephemeral Client A and Client B roots and recover through the integrated UI/client, admission, storage, resolver, and party services; P8/P9 must bind byte equality and public fingerprint to that exact manifest |
| C09 | Enrollment uses authenticated confidential remote transport | Baseline uses trusted provisioner/direct volume writes | Existing enrollment transport checks remain component controls; P7.5 must perform authenticated suite initialization and recipient-bound delivery across the integrated service graph, with endpoint-binding, replay, output, and role-state observations collected later under the exact profile |
| C10 | Provider-neutral public admission resists replay and cross-context reuse | Not part of baseline | The D004 local synthetic issuer, independent verifiers, and gateway negatives remain component controls; P7.5 must place them on the actual integrated request path and P8 must exercise cross-context and replay failures there; external OIDC evidence remains optional and separate |
| C11 | Successor publication is crash-safe | Partial inherited implementation | Existing lifecycle journal and exact-retry tests remain component controls; P7.5 must execute same-suite and cross-suite successor publication through the integrated provider, descriptor, party, and client paths, then P8 must inject crashes at every deployed transition boundary |
| C12 | General party replacement is safe for tested membership changes | Not part of baseline | P7.5 does not promote general replacement. Any later approved replacement claim must use an exact newly versioned integrated graph with old/new binding, readiness, activation, retirement, and crash evidence |
| C13 | Storage adapters obey the same immutable backup/descriptor/bundle contracts | Supported for inherited filesystem and S3-compatible backup adapters only | P2.3 conformance remains component evidence; P7.5 must route all four storage roles through the application gateway to the local S3-compatible service in the integrated graph. Optional AWS execution requires its own authorization, profile, and evidence and cannot make provider access control an authenticity result |
| C14 | Multi-host deployment has disjoint keys/state/network roles | Not part of baseline | P6.4 still requires topology audit and role snapshots on the exact separate hosts. D023's same-host integrated graph is a supporting configuration and does not satisfy or weaken the multi-host gate |
| C15 | Independently administered parties | Explicit non-claim | D023/P7.5 remains one-host, one-operator research infrastructure; only actual distinct operators with separately versioned operational evidence could change this non-claim |
| C16 | UI does not persist or expose prohibited material | Not part of baseline | P7 component checks remain supporting controls; after P7.5 connects the UI/client gateway to the deployed services, P8 must scan the exact integrated profile's persistence, logs, telemetry, history, clipboard, screenshots, crash output, and post-operation state with positive controls |
| C17 | Global rollback-resistant attempt bound | Disproved for inherited quorum-only model | Separate owner-approved monotonic architecture and evidence |
| C18 | Human memorability or usability | Explicit non-claim | Separate ethics-approved human study |
| C19 | Cryptographic implementation independently audited | Explicit non-claim | Independent qualified review/audit |
| C20 | Production readiness | Explicit non-claim | Out of current scope |
| C21 | Recovery-bundle decoding and publication fail closed | Not part of baseline | P2 strict decoding/publication regressions remain component controls; P7.5 must carry canonical bundles through the integrated gateway/provider/current-pointer workflow, and P8 must apply malformed, stale, digest, size, and exact-retry controls at that boundary before any retained result |
| C22 | Storage access is narrowly scoped and nonpersistent at the client | Not part of baseline | P7.5 must exercise the D004 local issuer and D015 gateway on the integrated UI/client-to-S3-compatible path; P8 must cover wrong subject/backup/prefix/operation/client-key/nonce/issuance/expiry, replay, no-list, credential-output, and outage controls. External identity-provider behavior remains optional and separate |
| C23 | The aPPSS profile correctly recovers the exact 16-byte high-entropy `S_R` only for the enrolled suite/password and a valid reconstruction subset | Not part of baseline; retained Yi results do not transfer | Existing D017 vectors and component tests remain prerequisites; P7.5 must demonstrate correct/wrong, malformed, cross-suite, cross-epoch, subset, and exact-key behavior for aPPSS 2-of-3 and 3-of-5 through the integrated authenticated service graph before P8/P9 evidence |
| C24 | Fewer than reconstruction threshold `k` aPPSS server states provide no local offline cue-verification predicate under the declared assumptions | Not part of baseline | Theorem 2/Figure 4 mapping and required human review remain independent prerequisites; P8 must capture every below-`k` coalition plus matching cloud/descriptor/omega state from the exact P7.5 integrated profile and run bounded networkless tests and positive controls without claiming side-channel, adaptive, or online-interaction security |
| C25 | At least `k` compromised aPPSS server states enable offline dictionary testing but do not directly disclose `S_R` before a correct cue-derived password guess | Not part of baseline; the frozen Yi implementation has a different threshold-compromise failure mode | P8 must derive fixed aggregate-only exact-threshold/all-server aPPSS views and matched Yi comparators from each applicable P7.5 suite/topology arm under one common-condition manifest; no candidates or secrets may be retained, and conditional entropy plus unrate-limited guessing remain explicit limitations |
| C26 | Explicit Yi/aPPSS enrollment selection and same-suite/cross-suite successors cannot mix suites, fall back during recovery, or retire a predecessor before a recoverable successor exists | Not part of baseline | P7.5 must exercise Yi and aPPSS new enrollment plus all four same-/cross-suite successor directions through descriptor-bound integrated dispatch, provider publication, party readiness, activation, and retirement; P8 must add no-fallback, mixed-state, crash, and exact-retry controls while preserving the frozen Yi regression |

Update this matrix with exact profile identifiers, evidence paths, and owner
decisions as work progresses and before proposing corresponding manuscript
changes.
