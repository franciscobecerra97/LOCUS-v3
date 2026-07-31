# Active Claim/Evidence Matrix

This matrix separates what the retained baseline supports from what a changed
improvement profile would need. Baseline evidence never transfers merely
because code was derived from the same repository.

Status values include `Supported for exact baseline`, `Partial for exact
baseline`, `Unsupported in improvement profile`, `In progress`, `Disproved`,
and `Explicit non-claim`.

| ID | Property | Frozen baseline status/evidence | Improvement-profile status/evidence required |
| --- | --- | --- | --- |
| C01 | Existing v1 CuePolicy remains byte-compatible | Supported by the frozen cue-policy vectors | Reverify vectors and unchanged backup/TPASS behavior after interface refactor |
| C02 | Common CuePolicy interface supports materially different policies | Unsupported | Frozen composite v1 plus quantized-coordinate, canonical-phone, and canonical-email set implementations; shared conformance; `NoResolver`; and cross-policy rejection |
| C03 | Cloud state lacks a local cue verifier | Supported for the exact v2 cloud snapshot boundary | New cloud recovery-bundle/current-pointer/descriptor and storage-gateway persistent-state surface, candidate test, credential-safe collection, and positive control |
| C04 | Fewer-than-threshold party state lacks a local cue verifier | Supported for the exact v2 one-party snapshot boundary | Every relevant coalition in the new profile plus positive controls |
| C05 | Matching cloud plus below-threshold parties lack a local verifier | Supported for the exact v2 matching combined snapshot | New combined state-surface experiment |
| C06 | RecoveryDescriptor and recovery bundle do not add an offline predicate | Not part of baseline | Descriptor/bundle/manifest schema analysis, disclosure snapshot, candidate test, and positive control |
| C07 | Clean client authenticates descriptor, bundle, and current epoch | Not part of baseline | Account-scope, pointer, bundle, substitution, stale, cross-user, cross-epoch, party-current-state, and trust-root tests |
| C08 | Clean client recovers exact original key | Baseline proves a fresh process, not a clean device | Client A isolation/destruction, Client B recovery, byte equality, and public fingerprint |
| C09 | Enrollment uses authenticated confidential remote transport | Baseline uses trusted provisioner/direct volume writes | Cross-process provisioning and endpoint/recipient-binding tests |
| C10 | Public admission resists replay and cross-context reuse | Not part of baseline | Subject/audience/bid/epoch/key/nonce/expiry negative tests |
| C11 | Successor publication is crash-safe | Partial inherited implementation | Crash at every transition and exact retry in the new deployed profile |
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
| C22 | Storage access is narrowly scoped and nonpersistent at the client | Not part of baseline | Wrong subject/backup/prefix/operation/key/nonce/expiry, replay, no-list, credential-output scan, and provider-outage evidence for the D004/D015 profile |

Update this matrix with exact profile identifiers, evidence paths, and owner
decisions as work progresses and before proposing corresponding manuscript
changes.
