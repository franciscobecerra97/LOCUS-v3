# Version Registry

This registry prevents semantic reinterpretation. Update it whenever a new
format or profile is approved.

## Frozen upstream identifiers

| Identifier | Meaning | Status |
| --- | --- | --- |
| `LOCUS-location-person-set-v1` | Exactly three canonical location-person pairs | Frozen |
| `LOCUS-location-person-pair-v1` | One quantized location plus canonical contact channel | Frozen |
| `LOCUS-reference-backup-v4` | Current canonical encrypted backup | Frozen |
| `LOCUS-cloud-backup-object-v1` | Canonical cloud envelope | Frozen |
| `LOCUS-cloud-backup-reference-v1` | Exact immutable cloud reference | Frozen |
| `LOCUS-compose-deployment-v2` | Same-host five-authorizer reference profile | Frozen |
| `LOCUS-TPASS-YI-ZK-RISTRETTO255-v1` | Native TPASS domain and wire profile | Frozen |
| `LOCUS-attempt-config-v2` | Existing signed-ledger configuration | Frozen |
| performance/attack evidence `v1` | Superseded historical result family | Frozen superseded |
| performance/attack evidence `v2` | Retained baseline evidence for exact deployed profile | Frozen; non-transferable |
| `LOCUS-anonymous-artifact-v1` | Sealed imported anonymous artifact and manifest envelope | Frozen; verification only |
| `LOCUS-anonymous-artifact-v2` | Integrated-repository anonymous package with package-specific reviewer documents and strict manifest schema | Active audit profile; release pending |

## Rules

- Do not rename an identifier for readability.
- Do not change canonicalization while retaining the old policy identifier.
- Do not add fields to a strict canonical format without a new format version.
- Do not reuse a schema version for a changed required field or interpretation.
- Do not reinterpret historical results under a new architecture.
- A policy change normally requires a new policy identifier and recovery epoch.
- A topology, admission, descriptor, trace-policy, or metric-definition change
  requires a new deployment/evidence profile.

## Planned version families

No final identifiers are assigned until the corresponding design is approved.
The following families are reserved conceptually:

- recovery-suite registry and suite-neutral client/party interfaces;
- aPPSS suite, password-input domain, OPRF profile, public parameters, party
  state, protocol messages, canonical wire format, and fixed vectors;
- aPPSS-bound backup, descriptor, service/API, runtime-package, deployment,
  migration, performance, and security-evidence profiles;
- RecoveryDescriptor and descriptor-current-pointer;
- immutable recovery-bundle ZIP and bundle manifest;
- CuePolicy registry plus quantized-coordinate-set, canonical-phone-set, and
  canonical-email-set policies;
- explicit `NoResolver` profile;
- clean-client deployment;
- public admission;
- multi-host deployment;
- additional provider adapters;
- distributed performance results;
- clean-client and information-flow evidence;
- post-v2 revised artifact package for later aPPSS/expanded-system evidence.

Record the exact identifier, schema, compatibility rule, owner decision, and
first implementing commit here before collecting evidence.

## Approved but unassigned families

D001, D003, D005, D014, D015, and D016 approve the architecture direction for the
following families without assigning protocol identifiers. D015 supersedes the
unassigned personal-cloud-account and Google Drive families from D002/D006:

| Family | Approved semantic boundary | Compatibility rule |
| --- | --- | --- |
| aPPSS recovery-suite successor | Section 3 aPPSS supplies the high-entropy `S_R` for new enrollments after P5A; exact OPRF, field, hash, wire, robustness, and theorem profile remain gated by D017 | New identifiers and epoch only; frozen Yi TPASS remains legacy-recovery compatible and is never reinterpreted |
| Recovery-suite password derivation | CuePolicy output enters an immutable suite-specific password-input domain | New domain per suite; identical CuePolicy bytes do not authorize cross-suite message or state reuse |
| Yi-to-aPPSS migration | Recover the old epoch client-side, create and verify a fresh aPPSS successor, activate it, then retire the predecessor | No share conversion, mixed-suite threshold, dual-state fallback, automatic downgrade, or in-place backup migration |
| aPPSS evidence | Correctness, below-threshold, matching combined, exact-threshold offline-dictionary, migration, and performance results for one exact profile | New schemas and paths; retained v2 Yi evidence remains frozen and cannot be pooled or relabeled |
| RecoveryDescriptor | Signed public recovery configuration authenticated from an app-pinned root and checked against party current state | New strict format; no change to frozen backup or TPASS formats |
| Descriptor current pointer | Authenticated mutable binding to one active bundle, descriptor, backup identifier, epoch, and configuration | New strict format with compare-and-swap semantics |
| Recovery bundle | Immutable bounded ZIP containing exactly canonical backup, signed descriptor, and manifest members | New container profile; descriptor binds the backup member and the external pointer binds the exact bundle |
| Bundle manifest | Exact backup/descriptor member name, format, length, and digest bindings | New strict canonical format; it does not digest itself |
| Quantized-coordinate set | Exactly three distinct directly entered quantized WGS84 coordinates | New policy identifier and domain; frozen composite policy unchanged |
| Canonical-phone set | Exactly three distinct strict E.164 values | New policy identifier and domain; frozen phone atom behavior remains compatible |
| Canonical-email set | Exactly three distinct values under a frozen constrained ASCII email grammar | New policy identifier and domain; frozen email atom behavior remains compatible |
| NoResolver | Explicit declaration that policy processing performs no resolver lookup | New resolver profile; no implicit fallback or enumeration |
| Storage capability | Short-lived subject/backup/prefix/operation/client-key/nonce/expiry-bound authority validated by the application storage gateway | New admission/storage profile; no client provider credential or direct pre-signed bearer URL |
| AWS S3 provider | Supplemental application-operated implementation of the logical backup, descriptor, current-pointer, and bundle contracts | New provider profile; local/S3-compatible identifiers unchanged |

## Assigned artifact package profiles

`LOCUS-anonymous-artifact-v2` uses archive root `locus-artifact-v2`, schema
`docs/schemas/artifact-manifest-v2.schema.json`, and reviewer files under
`artifact/package-v2/`. Its manifest retains the strict v1 field set
(`artifact`, sorted unique `entries`, and `source_commit`) while assigning a new
package identifier and allowlist. Extracted-tree readers accept both v1 and v2;
the builder emits only v2. V1 archives and manifests are never rewritten.

Assign final identifiers only with the corresponding schemas and canonical
vectors in the same reviewed change.
