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

P5.1 routes active application calls through the typed frozen-v1 CuePolicy
adapter. It assigns no identifier and does not reinterpret
`LOCUS-location-person-set-v1`, `LOCUS-location-person-pair-v1`, the resolver
profile, Yi password input, backup formats, deployment profiles, or evidence.

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

P1.5 subsequently assigns `LOCUS-security-matrix-v1` to the governance-only
claim and information-flow contract in `docs/security-matrix-v1.json`, with its
schema introduced in the same change. It is not a protocol, trace, result, or
evidence-profile identifier and does not advance any claim status.

### P2.1 assigned descriptor and bundle profiles

| Identifier | Exact semantic boundary | Compatibility rule |
| --- | --- | --- |
| `LOCUS-recovery-descriptor-v1` | Canonical signed public recovery configuration with separate recovery-holder and authorizer memberships | New field or interpretation requires a new descriptor identifier; it never changes a frozen backup, CuePolicy, or suite format |
| `LOCUS-descriptor-current-pointer-v1` | Canonical signed mutable binding to one exact uploaded bundle, descriptor, subject, backup, epoch, and configuration | P2.3 concurrency token remains provider metadata outside these bytes; changed pointer semantics require a new identifier |
| `LOCUS-bootstrap-signature-v1` | Ed25519 signature metadata and domain for descriptor/current-pointer objects | Expected issuer, key ID, and public key come from the installed trust configuration, never the signed object |
| `LOCUS-recovery-configuration-v1` | Domain-separated SHA-256 binding of the complete public descriptor configuration | Any change to the included field set or framing requires a new digest-domain identifier |
| `LOCUS-recovery-bundle-manifest-v1` | Canonical two-entry manifest binding `backup.json` and `descriptor.json` only | It never lists or hashes itself; changed membership or digest semantics require a new identifier |
| `LOCUS-recovery-bundle-v1` | Deterministic bounded three-member `ZIP_STORED` container | Exact ZIP metadata and limits are frozen; another encoding or member set requires a new bundle identifier |

All six P2.1 identifiers are introduced with strict schemas or an exact binary
profile, canonical vector, decoder, compatibility rules, and negative tests.
They do not assign the P3.3 admission profile or, by themselves, implement
P2.2 discovery/P2.3 storage. The canonical vector's
`test-only:unassigned-p3.3` value is explicitly non-deployable and is not a
LOCUS admission identifier.

### P2.2 assigned discovery and trust-bootstrap profiles

| Identifier | Exact semantic boundary | Compatibility rule |
| --- | --- | --- |
| `LOCUS-account-scoped-bootstrap-v1` | Clean-client algorithm that authenticates one exact gateway endpoint, current pointer, bundle, recovery identity, installed directory, and current-state authorization quorum | It performs no provider fetch or admission and cannot be relabeled as P2.3/P3 evidence |
| `LOCUS-bootstrap-trust-config-v1` | Canonical application-installed operator/discovery/party trust configuration with generation, validity, and predecessor binding | A descriptor cannot add keys; replacement bytes require the trusted application update channel and a consecutive predecessor binding |
| `LOCUS-recovery-receipt-v1` | Optional operator-signed subject/handle/discovery binding with an optional initial epoch/configuration/descriptor anchor | It is public recovery metadata, not a cue, factor, provider credential, or independent freshness authority |
| `LOCUS-party-current-summary-v1` | Short-lived party-signed active subject/backup/recovery/epoch/descriptor/configuration/policy/suite assertion | Its lifetime is at most 300 seconds and acceptance requires the descriptor's distinct authorization quorum |
| `LOCUS-party-current-signature-v1` | Ed25519 party-summary signature domain and metadata | The expected party endpoint, key ID, and public key come only from the installed trust configuration |

These five identifiers have strict schemas or an exact algorithm profile,
canonical synthetic vectors, bounded decoders, and negative tests. P2.2 does
not assign the P3 admission/capability format, implement P2.3 storage/CAS, or
claim coordinated rollback resistance.

### P2.3 assigned storage profile

`LOCUS-descriptor-bundle-store-v1` freezes the provider-neutral exact-key
grammar and behavior for immutable descriptors, immutable recovery bundles,
hashed-handle current pointers, exact retry, and current-pointer compare-and-
swap. Filesystem and S3-compatible adapters share the profile. S3 ETags are
opaque CAS tokens only; storage authorization never authenticates LOCUS
content. Changed key grammar, mutability, retry, or CAS semantics require a new
profile identifier. The profile has a canonical locator vector and shared
filesystem/S3 tests; it does not assign the P3 capability or gateway profile.

### P6.1 assigned provider-conformance profiles

`LOCUS-storage-provider-profile-v1` groups the already separate backup,
descriptor, bundle, and current-pointer contracts behind one conformance
boundary. `LOCUS-storage-provider-filesystem-v1` identifies the deterministic
credential-free local adapter and `LOCUS-storage-provider-s3-compatible-v1`
identifies the explicitly credentialed exact-prefix S3-compatible adapter.
The latter requires TLS for nonlocal use; an explicitly enabled plaintext
endpoint is classified only as a local-test transport. All three profiles
prohibit listing as a required operation and preserve the P2.3 locator,
immutability, digest-validation, and CAS semantics without reinterpretation.

### P6.2 assigned AWS and admitted-gateway profiles

`LOCUS-storage-provider-aws-s3-v1` is the supplemental TLS-only AWS S3
application profile. It accepts only explicitly supplied application-side
access key, secret key, optional session token, region, bucket, and exact
prefix; it has no custom endpoint and does not use ambient credential lookup.
It reuses the P6.1 S3-compatible logical contracts without claiming that local
conformance establishes AWS behavior.

`LOCUS-application-storage-gateway-v1` maps one already validated D004
capability to one exact subject/backup/epoch-scoped backup, descriptor, bundle,
or current-pointer operation. Its logical keys are redundant bindings and do
not replace the frozen provider locators. `LOCUS-storage-pointer-cas-v1` is its
bounded canonical transport object for an optional exact expected pointer and
one required replacement pointer. Changed roles, key grammar, admission
binding, or CAS fields require new identifiers.

### P6.3 assigned paired topology and deployment profiles

`LOCUS-recovery-suite-selector-v2` admits only the matched D021 2-of-3 and
3-of-5 Yi/aPPSS choices with five authorizers and an independent 4-of-5
authorization quorum. The frozen selector v1 remains exact 2-of-3. The newly
assigned `LOCUS-TPASS-YI-3of5-v1` and `LOCUS-APPSS-3of5-v1` profile identifiers
bind topology only; they do not change either underlying suite construction.

The aPPSS 3-of-5 profile uses distinct `LOCUS-APPSS-*-v2` public, pending,
party, request, response, install, ready, and client-session formats described
by `docs/schemas/appss-wire-v2.schema.json` and the public-only
`LOCUS-APPSS-format-vectors-v2` corpus. No v1 aPPSS byte is reinterpreted.
Yi continues to use the frozen `LOCUS-TPASS-wire-v1` native encoding because
that encoding already carries and validates its threshold and party count.

`LOCUS-reference-backup-v6` and `LOCUS-backup-associated-data-v3` extend the
suite-neutral outer encryption boundary to the two exact topologies. Their
strict profile/suite/public-format matrix rejects cross-suite and cross-
topology mixing. Backup v5 remains exact 2-of-3.

`LOCUS-paired-suite-deployment-2of3-v1` and
`LOCUS-paired-suite-deployment-3of5-v1` freeze the controlled comparison
settings: one selected suite per epoch, five authorizers, 4-of-5 authorization,
the same direct email CuePolicy, local synthetic admission, filesystem storage,
network schedule, and measurement definitions. They are same-host process
deployment profiles, not independent-administration or retained-evidence
identifiers. Any provider, admission, policy, quorum, host-tier, schedule, or
measurement change requires a new deployment profile.

### P6.4 assigned public endpoint setup

`LOCUS-party-endpoint-setup-v1` is a bounded, secret-free operator input that
maps party IDs 1--5 to exact lowercase DNS names or canonical IP addresses and
ports. Its `same-host-containers` tier is fixed to Compose service names
`party1`--`party5` on port 8443. Its
`separate-network-hosts-single-admin` tier requires five distinct non-loopback,
non-link-local hosts, but the label is configuration intent rather than proof
that the hosts exist or are isolated. The setup drives certificate SANs,
client endpoints, peer endpoints, and listener ports together. It never
selects a suite, threshold, authorization quorum, credential, or fallback
endpoint. Changed fields or interpretation require a new identifier.

### P2.4 assigned development scenario contract

`LOCUS-descriptor-security-scenarios-v1` is the strict aggregate-only
implementation-regression report for the sixteen approved P2.4 detector
families, their positive controls, and a two-candidate networkless direct-
verifier check. It retains only scenario/category identifiers, Boolean gates,
counts, and exact public profile versions. It is not a P9 evidence result,
cryptographic proof, entropy claim, or production-security result; P9 retains
the separately reserved evidence-result allocation gate.

### Syntax and collision rules

P3.2 assigns `LOCUS-authenticated-enrollment-transport-v1` to the strict
recipient-bound initial-epoch operation carried by the existing party API. It
uses mutual TLS 1.3, exact identities, canonical bounded JSON, and durable
certificate/route/body-bound idempotency. It supports the frozen Yi runtime
package or an explicit authorizer-only null package; it assigns no aPPSS state
format or admission capability.

P3.2 also assigns `LOCUS-party-service-config-v2` to a clean party boot
configuration containing public topology, local service credentials, and
native-role network configuration but no initial suite state. Version 1 stays
protected and readable; v2 state arrives through authenticated enrollment.

P3.3 assigns `LOCUS-admission-binding-v1`,
`LOCUS-admission-capability-v1`, `LOCUS-admission-client-proof-v1`,
`LOCUS-local-synthetic-admission-v1`, and `LOCUS-admission-replay-v1` together
with the strict binding schema and fixed vector. The provider-neutral objects
are valid only for their exact issuer, pseudonymous subject, backup, epoch,
operation, audience, proof key, nonce, time window, and optional derived
storage prefix. They carry no provider credential, listing authority, cue
material, or offline verifier. Any OIDC adapter requires a distinct identifier.
P3.4 implements these exact local profiles without assigning an external
provider identifier; its fixed local signature/proof vector cannot be used as
evidence for OIDC, multifactor authentication, or production identity.

P4.2 assigns `LOCUS-clean-client-isolation-v1` to the bounded local process/
persistent-surface scenario. Its exact Client B inputs are authenticated public
recovery configuration, an installed CA, and a fresh recovery-only transport
identity; recovery input is transient. It is not a deployment, evidence,
forensic-erasure, or independent-administration profile.

P4.3 assigns `LOCUS-successor-publication-journal-v1` to the secret-free durable
client progress record and deterministic phase-action idempotency domain for one
exact same-membership successor. It binds public epochs and configuration,
backup, descriptor, and recovered-key digests; it stores no recovered key or
suite secret. It does not change `LOCUS-epoch-lifecycle-policy-v1`, authorize
party replacement, or establish rollback-resistant publication.

### P5.3 assigned atomic CuePolicy profiles

| Identifier | Exact semantic boundary | Compatibility rule |
| --- | --- | --- |
| `LOCUS-quantized-coordinate-set-v1` | Exactly three distinct WGS84 decimal coordinate pairs, round-half-even quantized to `10^-4` degrees and canonically ordered under its own domain | Any input, quantization, ordering, duplicate, member, or top-level encoding change requires a new policy identifier and epoch |
| `LOCUS-canonical-phone-set-v1` | Exactly three distinct ASCII strings in the bounded `+[1-9][0-9]{1,14}` lexical form, identity-canonicalized and domain-ordered | No local-format inference, extension, lookup, or normalization may be added under this identifier |
| `LOCUS-canonical-email-set-v1` | Exactly three distinct addresses under the bounded constrained ASCII grammar, lowercase-canonicalized and domain-ordered | Any grammar, case, IDNA, provider-alias, ordering, duplicate, or encoding change requires a new identifier and epoch |
| `LOCUS-cue-policy-conformance-v1` | Pinned four-policy source binding plus canonical JSON/hex/SHA-256 and exact-error corpus for the three atomic implementations | It is implementation conformance, not retained security evidence or a usability/entropy result |
| `LOCUS-no-resolver-v1` | Resolver-free adapter binding one exact direct-input atomic policy and returning that policy's canonical bytes after one invocation | It performs no lookup, inference, alternatives, provider interaction, or suite retry; changed behavior requires a new identifier |

None of these identifiers changes the frozen composite policy or supplies a
recovery-suite password-input domain.

### P5A.1 assigned aPPSS and selectable-suite formats

P5A.1 assigns `LOCUS-APPSS-2HASHDH-RISTRETTO255-SHA512-GF128-v1` with the
2-of-3 profile `LOCUS-APPSS-2of3-v1`, OPRF profile
`LOCUS-APPSS-OPRF-RISTRETTO255-SHA512-v1`, and suite password domain
`LOCUS-APPSS-password-input-v1`. Its external family is
`LOCUS-APPSS-wire-v1`, with separate public, pending-party, installed-party,
request, response, state-install, state-ready, and transient-client-session
identifiers listed in the protected ledger. The strict shapes and cross-field
rules are frozen by `docs/APPSS-WIRE-FORMAT.md` and
`docs/schemas/appss-wire-v1.schema.json`.

`LOCUS-recovery-suite-selector-v1` selects exactly one of the frozen Yi suite
or the new aPPSS suite for a fresh 2-of-3 enrollment/epoch. The paired Yi
selector label `LOCUS-TPASS-YI-2of3-v1` does not change the frozen Yi suite,
wire, backup, vector, or evidence. Recovery is descriptor-bound and never
consults the selector as a fallback.

`LOCUS-reference-backup-v5` is the first suite-neutral encrypted-backup shape;
`LOCUS-backup-associated-data-v2` authenticates its public metadata. Backup v4
remains frozen and Yi-specific. RecoveryDescriptor v1 already has exact
suite-neutral suite/public-state/threshold/membership fields and is not
reinterpreted or replaced. `LOCUS-APPSS-format-vectors-v1` is a public-only
structural conformance corpus with an independent consumer; it is not security
or performance evidence.

P5A.2 implements these assigned native boundaries in the separate
`locus-appss-core` crate and adds a public-only native vector consumed through
the narrow Python binding. It assigns no new protocol identifier. Deployment,
trace, result, artifact, 3-of-5 topology, and retained-performance identifiers
remain unassigned until their later gates.

P5A.3 implements the exact selector registry, aPPSS adapter, backup-v5 common
composition, durable holder state, transient client, and pinned mutual-TLS
evaluation route using only the assigned request, response, pending-state,
party-state, install, and ready formats. The `/v1` route does not introduce a
new protocol object or deployment profile. Its subprocess test is component
verification, not retained evidence. Runtime deployment, evidence, trace, and
artifact identifiers remain unassigned.

P5A.4 adds authenticated `/v1` initialization and state-install routes without
assigning a new protocol object: request/response and install/ready bodies are
the exact P5A.1 formats, and pending/installed databases retain the exact P5A.1
state formats. The public process configuration recomputes the assigned epoch
context and pins certificate identities; it is not a portable deployment or
evidence profile. Deployment, trace, result, and artifact identifiers remain
unassigned.

P5A.5 implements explicit selection and same-suite/cross-suite
successor preparation using only the assigned selector, backup-v5, descriptor,
bundle, suite-state, and P4.3 journal boundaries. The existing successor journal
already commits the exact successor configuration, backup, and descriptor
digests; the authenticated descriptor commits the one selected suite. No state
conversion, dual-suite object, fallback format, deployment profile, or evidence
identifier is introduced. D020 activates this exact application/component
interface after provisional internal mapping acceptance. It assigns no
deployment, trace, result, or artifact identifier; the paired deployment
profiles are assigned separately by the later P6.3 gate.

P5A.6 assigns `LOCUS-recovery-suite-compromise-regression-v1` solely to the
strict aggregate-only development report in
`docs/schemas/recovery-suite-compromise-regression-v1.schema.json`. It binds one
fixed matched Yi/aPPSS 2-of-3 synthetic profile and covers cloud-only, every
below-threshold coalition, matching combined, every exact-threshold subset, and
all-server views with positive controls. Its evaluator accepts no inputs and
writes no results. This is not a P9 result identifier, retained evidence,
deployment profile, cryptographic proof, or 3-of-5 profile. P9 must allocate
separate suite/topology evidence paths before collection.

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
| Recovery suite | Frozen Yi suite/wire; exact aPPSS v1 2-of-3 and v2 3-of-5 formats; selector v1/v2; backup v5/v6; D020 internal mapping assessment provisionally accepted with human validation pending | D019 independent human confirmation remains mandatory before manuscript/final reviewed release; retained-evidence identities remain at P9 |
| CuePolicy/resolver | Frozen composite identifiers plus the three P5.3 atomic policies/conformance corpus and P5.4 `NoResolver` adapter | Every later policy or resolver semantic change requires a new identifier, implementation, vector/corpus, and exact registry rule |
| Descriptor | No implemented descriptor identifier | P2.1 assigns descriptor and current-pointer identifiers with strict schemas, signatures, bounds, and vectors |
| Backup/bundle | Frozen backup-v4, suite-neutral backup-v5, paired-topology backup-v6, and P2 bundle/manifest identifiers | Any later suite/topology or bundle semantic change receives a separate identifier |
| Admission | P3.3 provider-neutral binding/capability/proof/replay and local synthetic issuer identifiers | Any OIDC or other provider adapter requires a distinct profile, schema, vector, and evidence path without changing the core binding |
| Deployment | Frozen same-host Yi profile plus P6.3 matched same-host process profiles for Yi/aPPSS 2-of-3 and 3-of-5 | P6.4 host separation is a distinct profile; independent administration requires actual operators and separate approval |
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

- release implementation of the assigned recovery-suite registry and
  suite-neutral client/party interfaces;
- aPPSS-bound service/API, runtime-package, deployment,
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

## Approved family gates

D001, D003--D005, D008--D010, and D014--D018 approve the architecture direction
for the following families. P2.1 assignments are listed above; remaining exact
identifiers stay unassigned until their recorded gate passes. D015 supersedes
the unassigned personal-cloud-account and Google Drive families from D002/D006;
D018 supersedes D007's asymmetric topology order and D016's sole-aPPSS cutover:

| Family | Approved semantic boundary | Compatibility rule |
| --- | --- | --- |
| aPPSS recovery suite | D017 freezes Figure 4 aPPSS with RFC 9497 OPRF-mode ristretto255/SHA-512 as the concrete 2HashDH realization, `lambda=128`, canonical polynomial-basis GF(2^128), SHA-256-derived 16-byte `C` and 16-byte `S_R`, abort-only robustness, and first `k=2,n=3` evaluation | P5A.1 assigns its exact identifiers, schemas, bounds, and public vector; later implementation/release gates must preserve them and frozen Yi remains independently selectable |
| Recovery-suite password derivation | CuePolicy output enters an immutable suite-specific password-input domain | New domain per suite; identical CuePolicy bytes do not authorize cross-suite message or state reuse |
| Recovery-suite selection and switching | Select Yi or aPPSS for new enrollment; recover an existing epoch only with its authenticated suite; retain or explicitly switch suites through fresh successor setup | No state conversion, mixed-suite threshold, dual-state fallback, recovery-time suite override, automatic downgrade, or in-place backup migration |
| Paired Yi/aPPSS evidence | Correctness, below-threshold, matching combined, exact-threshold compromise, switching, and performance results under matched 2-of-3 and later 3-of-5 conditions | New schemas and suite/topology-specific paths; retained v2 Yi evidence remains frozen and cannot be pooled or relabeled; paired processors require exact common-condition manifests |
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
| Evaluated recovery-suite topology | Frozen Yi 2-of-3 baseline; paired selectable Yi/aPPSS 2-of-3 first; paired Yi/aPPSS 3-of-5 after configuration generalization | Each suite/topology receives distinct deployment/evidence identity; paired rows bind the same outer conditions and authorization quorum remains a separate typed field |
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
