# Active Claim/Evidence Matrix

This matrix separates what the retained baseline supports from what a changed
improvement profile would need. Baseline evidence never transfers merely
because code was derived from the same repository.

P1.4 protects the existing identifier corpus and reserves future evidence
families, but it creates no implementation or security evidence. A reservation
does not advance any claim status, and later claims must cite the exact assigned
profile and result schema.

Status values include `Supported for exact baseline`, `Partial for exact
baseline`, `Unsupported in improvement profile`, `In progress`, `Disproved`,
and `Explicit non-claim`.

| ID | Property | Frozen baseline status/evidence | Improvement-profile status/evidence required |
| --- | --- | --- | --- |
| C01 | Existing v1 CuePolicy remains byte-compatible | Supported by the frozen cue-policy vectors | P1.3 pins the frozen CuePolicy and TPASS-vector digests and verifies unchanged native-Yi behavior through thin typed adapters; aPPSS must later consume the same policy bytes only through its new suite-specific password domain |
| C02 | Common CuePolicy interface supports materially different policies | Unsupported | P1.3 supplies the common typed interface and frozen-v1 adapter only; P5 must add quantized-coordinate, canonical-phone, and canonical-email set implementations, shared conformance, `NoResolver`, and cross-policy rejection |
| C03 | Cloud state lacks a local cue verifier | Supported for the exact v2 cloud snapshot boundary | New cloud recovery-bundle/current-pointer/descriptor and storage-gateway persistent-state surface, candidate test, credential-safe collection, and positive control |
| C04 | Fewer-than-threshold party state lacks a local cue verifier | Supported for the exact v2 one-party Yi snapshot boundary | Every relevant coalition for each new exact suite/profile plus positive controls; aPPSS support additionally requires the reviewed theorem/profile mapping |
| C05 | Matching cloud plus below-threshold parties lack a local verifier | Supported for the exact v2 matching Yi combined snapshot | New suite-bound combined state-surface experiments with exact descriptor/backup/epoch binding |
| C06 | RecoveryDescriptor and recovery bundle do not add an offline predicate | Not part of baseline | Descriptor/bundle/manifest schema analysis, disclosure snapshot, candidate test, and positive control |
| C07 | Clean client authenticates descriptor, bundle, and current epoch | Not part of baseline | Account-scope, pointer, bundle, substitution, stale, cross-user, cross-epoch, party-current-state, and trust-root tests |
| C08 | Clean client recovers exact original key | Baseline proves a fresh process, not a clean device | Client A isolation/destruction, Client B recovery, byte equality, and public fingerprint |
| C09 | Enrollment uses authenticated confidential remote transport | Baseline uses trusted provisioner/direct volume writes | P1.3 defines suite-neutral enrollment and client-phase contracts only; P3 still requires cross-process provisioning and endpoint/recipient-binding tests |
| C10 | Provider-neutral public admission resists replay and cross-context reuse | Not part of baseline | P1.3 defines separate admission-verifier, storage-capability-verifier, and gateway contracts only; P3 must implement the D004 local synthetic issuer, binding negatives, and independent validation; external OIDC evidence remains optional |
| C11 | Successor publication is crash-safe | Partial inherited implementation | P1.3 defines lifecycle transition/binding contracts only; P6 still requires crash at every transition and exact retry in the new deployed profile |
| C12 | General party replacement is safe for tested membership changes | Not part of baseline | Old/new binding, readiness, activation, retirement, and crash matrix |
| C13 | Storage adapters obey the same immutable backup/descriptor/bundle contracts | Supported for inherited filesystem and S3-compatible backup adapters only | Shared conformance for extended local S3 contracts and the optional AWS S3 profile; provider access control is not treated as authenticity |
| C14 | Multi-host deployment has disjoint keys/state/network roles | Not part of baseline | Topology audit and role snapshots on exact hosts |
| C15 | Independently administered parties | Explicit non-claim | Actual independent operators and operational evidence |
| C16 | UI does not persist or expose prohibited material | Not part of baseline | Persistence, log, screenshot, history, clipboard, and crash-output scans |
| C17 | Global rollback-resistant attempt bound | Disproved for inherited quorum-only model | Separate owner-approved monotonic architecture and evidence |
| C18 | Human memorability or usability | Explicit non-claim | Separate ethics-approved human study |
| C19 | Cryptographic implementation independently audited | Explicit non-claim | Independent qualified review/audit |
| C20 | Production readiness | Explicit non-claim | Out of current scope |
| C21 | Recovery-bundle decoding and publication fail closed | Not part of baseline | Exact-member, path, duplicate, compression/size, manifest/digest, immutable retry, stale-pointer, and positive-control evidence for the new bundle profile |
| C22 | Storage access is narrowly scoped and nonpersistent at the client | Not part of baseline | Wrong subject/backup/prefix/operation/client-key/nonce/issuance/expiry, replay, no-list, credential-output scan, and provider-outage evidence for the D004 local-issuer/D015 gateway profile; external identity-provider behavior is not required or implied |
| C23 | The aPPSS profile correctly recovers the exact 16-byte high-entropy `S_R` only for the enrolled suite/password and a valid reconstruction subset | Not part of baseline; retained Yi results do not transfer | Approved D017 `docs/APPSS-PROFILE.md` contract; RFC 9497 OPRF-mode, GF(2^128), SHA-256 split, and canonical-format vectors; all valid 2-of-3 subsets; authenticated distributed initialization; correct/wrong-input, malformed-state, cross-suite, cross-epoch, and end-to-end exact-key tests |
| C24 | Fewer than reconstruction threshold `k` aPPSS server states provide no local offline cue-verification predicate under the declared assumptions | Not part of baseline | Theorem 2/Figure 4 mapping plus independent review of the exact D017 profile; every evaluated below-`k` static coalition; matching cloud/descriptor/omega state; networkless read-only candidate test; positive controls; explicit exclusion of side channels, stronger adaptive implementation claims, and online honest-server interactions |
| C25 | At least `k` compromised aPPSS server states enable offline dictionary testing but do not directly disclose `S_R` before a correct cue-derived password guess | Not part of baseline; the frozen Yi implementation has a different threshold-compromise failure mode | D017 2-of-3 profile and reviewed threshold mapping `k=t_paper+1`; fixed aggregate-only exact-threshold/all-server aPPSS scenario; correct/wrong fixed candidates; Yi comparator that directly reconstructs its shared password scalar and recovery secret; no retained candidates or secrets; explicit conditional-entropy and unrate-limited-guessing limitation |
| C26 | Yi-to-aPPSS migration and active-profile selection cannot mix suites, silently downgrade, or retire a predecessor before a recoverable successor exists | Not part of baseline | New suite/epoch identifiers; cross-suite and downgrade negatives; crash/retry matrix; old-profile recovery followed by fresh successor enrollment/readiness/activation/retirement; legacy recovery regression |

Update this matrix with exact profile identifiers, evidence paths, and owner
decisions as work progresses and before proposing corresponding manuscript
changes.
