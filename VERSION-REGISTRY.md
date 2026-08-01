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

The table highlights the principal upstream boundaries. The complete protected
ledger, including superseded development, internal wire, lifecycle, snapshot,
trace, result, and synthetic-fixture identifiers, is
`docs/version-registry-v1.json`. Inclusion in that ledger prevents reuse; it
does not promote a historical or test-only identifier to an active profile.

## Rules

- Do not rename an identifier for readability.
- Do not change canonicalization while retaining the old policy identifier.
- Do not add fields to a strict canonical format without a new format version.
- Do not reuse a schema version for a changed required field or interpretation.
- Do not reinterpret historical results under a new architecture.
- A policy change normally requires a new policy identifier and recovery epoch.
- A topology, admission, descriptor, trace-policy, or metric-definition change
  requires a new deployment/evidence profile.

## P1.4 namespace and allocation contract

The machine-readable registry is `docs/version-registry-v1.json`, validated by
`docs/schemas/version-registry-v1.schema.json`. Its own identifier,
`LOCUS-version-registry-v1`, is the only new identifier assigned by P1.4; its
schema and tests are introduced in the same change. Later protocol and evidence
families remain reservations without candidate identifiers until their named
schema/vector gate passes.

### Syntax and collision rules

- Assigned identifiers use printable ASCII and the form
  `LOCUS-<semantic-name>-v<unsigned-integer>`.
- Matching is exact and case-sensitive, while allocation also rejects a
  case-folded collision to avoid identifiers that differ only by case.
- A protected identifier is never deleted or reused, including when its format
  is superseded, experimental, development-only, or test-only.
- The numeric suffix versions one semantic family; it is not a global release
  number and does not imply compatibility with another family.
- Prefix similarity does not establish compatibility. Compatibility exists
  only when the registered adapter or decoder rule says so.
- Domain-separation labels, canonical wire/state formats, deployment profiles,
  trace policies, result schemas, and artifact manifests are separate versioned
  boundaries even when they are introduced together.

### Allocation states

| State | Meaning | Permitted transition |
| --- | --- | --- |
| Protected existing | Identifier already occurs in the imported or integrated project and cannot be reinterpreted | May be documented as active, frozen, superseded, or test-only; never returns to an allocatable state |
| Reserved family | Semantic boundary and allocation phase are approved, but no exact identifier exists | Becomes assigned only with its strict schema, compatibility rule, and canonical vectors/tests |
| Assigned | Exact identifier, meaning, schema/profile, and first implementation are reviewed together | Becomes frozen or superseded; its original meaning remains permanent |
| Frozen/superseded | No new enrollment/evidence uses the profile, but compatible legacy reads may remain | Never changes meaning and never transfers evidence to a successor |

### Registered family gates

| Family | Current protected boundary | Future allocation gate |
| --- | --- | --- |
| Recovery suite | Frozen Yi suite and wire identifiers | P5A.1 assigns aPPSS suite/domain/state/message/wire identifiers only with D017 schemas and fixed vectors |
| CuePolicy/resolver | Frozen composite, atom, and deterministic-resolver identifiers | P5.2 assigns each atomic policy and `NoResolver` only after its grammar, domain, and vectors are approved |
| Descriptor | No implemented descriptor identifier | P2.1 assigns descriptor and current-pointer identifiers with strict schemas, signatures, bounds, and vectors |
| Backup/bundle | Frozen backup and cloud-object/reference identifiers | P2.1 assigns bundle/manifest boundaries without changing the backup member; any later suite-bound backup change receives a separate identifier |
| Admission | No implemented public-admission identifier | P3.3 assigns the provider-neutral capability and local-issuer profiles after binding/replay schemas and vectors are approved |
| Deployment | Frozen same-host Yi deployment identifier | P6.3 assigns exact suite/topology/provider profiles; host separation and independent administration remain distinct |
| Trace | Frozen retained trace-policy identifier | P8.3 assigns a new trace profile only after the collection and retained-output schema is approved |
| Result | Frozen retained attack/performance/evidence families | P9.2 assigns new schemas before collection and keeps Yi/aPPSS and topology results disjoint |
| Artifact | Frozen v1 and active-audit v2 anonymous package identifiers | P10.3 assigns a later portable-artifact identifier with a new manifest and allowlist |

### Upgrade and compatibility rules

1. A decoder accepts only an explicit allowlist of exact identifiers and must
   reject unknown, malformed, or unsupported versions before interpreting
   dependent fields.
2. An in-family reader may support multiple immutable versions through explicit
   adapters. It must not silently reinterpret old bytes as a new version.
3. A changed CuePolicy, recovery suite, threshold/topology, descriptor binding,
   admission contract, or backup semantics requires a new recovery epoch and
   every affected profile identifier.
4. One epoch selects exactly one recovery suite. Yi and aPPSS state, messages,
   shares, and evidence cannot be mixed, converted in place, or used as an
   automatic downgrade path.
5. Evidence compatibility is stricter than implementation compatibility. A
   legacy decoder does not authorize pooling or relabeling historical results.
6. Publication is additive: new schemas, vectors, results, and artifacts use
   new paths. Frozen files and retained v1/v2 evidence are never overwritten.

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

P1.3 implements only typed, in-memory boundaries for these planned families.
P1.4 protects all existing identifiers and records the future family gates but
assigns no new protocol, wire-format, deployment, or evidence identifier. The
frozen Yi, CuePolicy, backup, deployment, and retained-evidence identifiers
remain unchanged.

## Approved but unassigned families

D001, D003--D005, D007--D010, and D014--D017 approve the architecture direction
for the following families without assigning final protocol identifiers. D015
supersedes the unassigned personal-cloud-account and Google Drive families from
D002/D006:

| Family | Approved semantic boundary | Compatibility rule |
| --- | --- | --- |
| aPPSS recovery-suite successor | D017 freezes Figure 4 aPPSS with RFC 9497 OPRF-mode ristretto255/SHA-512 as the concrete 2HashDH realization, `lambda=128`, canonical polynomial-basis GF(2^128), SHA-256-derived 16-byte `C` and 16-byte `S_R`, abort-only robustness, and first `k=2,n=3` evaluation | Final identifiers are assigned with schemas/vectors at P5A.1; new epoch only; frozen Yi TPASS remains legacy-recovery compatible and is never reinterpreted |
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
| Local synthetic admission issuer | Project-controlled issuer supplies the D004 pseudonymous, proof-key-bound capability for the default prototype and reviewer path | New provider-neutral capability/local-issuer profiles; no external identity provider, recovery-factor, or CuePolicy semantics |
| Optional OIDC admission adapter | A later Authorization Code with PKCE/DPoP adapter may produce evidence for the same D004 admission contract | Separate adapter/profile/evidence only; never required by the default artifact and cannot change the core request binding |
| Evaluated recovery-suite topology | Frozen Yi 2-of-3 baseline; aPPSS 2-of-3 first; aPPSS 3-of-5 only after configuration generalization | Each topology receives distinct deployment/evidence identity; authorization quorum remains a separate typed field |
| Host/administration scope | Same-host process separation, later host separation, and actual independent administration are distinct meanings | A changed topology or administrative principal set requires a new deployment/evidence profile |
| Local attempt audit | Signed local records are diagnostic evidence without a global rollback-resistant bound | Existing frozen attempt formats are not reinterpreted; any monotonic authority is a separate D012 profile |
| Thin cross-platform UI | UI calls stable client APIs and contains no protocol/canonicalization logic | Framework/profile assigned only after API freeze; no change to protocol bytes or usability claim |
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
