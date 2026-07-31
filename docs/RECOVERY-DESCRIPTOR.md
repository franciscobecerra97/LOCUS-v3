# RecoveryDescriptor And Recovery-Bundle Design

Status: owner-approved target-design direction under D001, D003, D014, and
D015. D015 supersedes the former personal-cloud-account and Google Drive
choices in D002 and D006. No final identifier has been assigned, and this
design does not supersede the implemented baseline or current manuscript until
implementation and evidence gates pass.

## Purpose

A clean recovery client needs authenticated information that the inherited
prototype currently receives from a pre-provisioned client volume:

- which recovery record to use;
- the active epoch;
- the exact encrypted backup;
- the enrolled CuePolicy;
- TPASS public parameters and membership;
- authorization membership and quorum;
- authenticated party endpoints;
- the admission profile;
- lifecycle state.

The descriptor makes those assumptions explicit. It must not create an offline
cue-verification predicate.

For the account-scoped profile, each epoch is carried in one immutable recovery
bundle stored in an application-operated S3 namespace scoped to the admitted
subject and backup identifier. The bundle colocates the canonical encrypted
backup, signed descriptor, and a manifest for portability. Logical backup,
descriptor, and current-pointer contracts remain separate even when the same
provider stores them.

## Proposed public fields

### Envelope

- format identifier and version;
- issuer identifier;
- subject/account scope or pseudonymous recovery scope;
- issuance and expiry/refresh policy;
- canonical payload;
- signature and algorithm identifier.

### Recovery binding

- backup identifier;
- positive epoch;
- recovery identity;
- predecessor/configuration digest where applicable.

### Cloud binding

- backend/profile identifier;
- logical immutable backup reference (`backup.json` in the bundle profile);
- exact canonical backup-member digest;
- bundle-manifest format;
- backup format identifier.

The provider-assigned immutable bundle locator and exact uploaded bundle digest
belong to the separately authenticated current pointer, not to the descriptor
inside that bundle.

### Cue-policy binding

- CuePolicy identifier;
- public policy parameters needed to parse user input;
- resolver profile and version;
- no selected cue or selection identifier.

### TPASS binding

- canonical public parameters;
- TPASS-holder identities;
- threshold;
- endpoint/directory references;
- TPASS protocol/wire profile.

### Authorization binding

- authorizer identities;
- quorum;
- admission profile;
- audience/operation namespace;
- security-policy version.

### Lifecycle binding

- configuration digest;
- predecessor descriptor digest;
- phase/active-state assertion;
- successor pointer only when the publication protocol defines it safely.

## Forbidden fields

- raw cue or user-entered label;
- selected provider record identifier;
- individual canonical cue descriptor;
- cue hash or per-cue digest;
- complete `Z_M`;
- `p_M`;
- password-derived authenticator;
- TPASS secret state;
- recovered group secret;
- wrapping key;
- plaintext private key;
- credential or bearer token;
- an endpoint trust root that is trusted only because the descriptor says so.

## Recovery-bundle format

The approved per-epoch container is an immutable bounded ZIP with exactly these
root members:

```text
backup.json
descriptor.json
manifest.json
```

- `backup.json` is the canonical encrypted backup object and contains the
  ciphertext `c`, nonce, authentication data, and approved public bindings.
- `descriptor.json` is the canonical signed `RecoveryDescriptor`; its cloud
  binding contains the SHA-256 digest and exact byte length of `backup.json`.
- `manifest.json` binds the exact names, format identifiers, byte lengths, and
  SHA-256 digests of `backup.json` and `descriptor.json`.

The descriptor contains neither the digest nor a provider-assigned locator of
the ZIP that contains it. The authenticated current pointer outside the ZIP
binds the active bundle locator, bundle byte length and digest, descriptor
digest, backup identifier, epoch, and configuration digest. This avoids both a
self-referential digest cycle and an upload-assigned-locator cycle.

The ZIP decoder must reject:

- missing, duplicate, unknown, nested, or directory members;
- absolute paths, path separators, `..`, alternate data streams, or names that
  are not the exact registered ASCII member names;
- encrypted members, unsupported compression methods, data descriptors or
  ambiguous metadata not admitted by the frozen profile;
- per-member, aggregate compressed, aggregate decompressed, nesting, and
  compression-ratio limit violations; and
- noncanonical member bytes or any manifest/digest/length mismatch.

ZIP timestamps, entry order, platform attributes, and compression choices are
transport metadata rather than descriptor semantics. The bundle profile must
either freeze them for deterministic generation or exclude them from semantic
identity while the current pointer still binds the exact uploaded ZIP bytes.

## Approved discovery profile

### Account-scoped discovery

The user first authenticates through the eventual owner-approved D004 LOCUS
admission/identity profile. The client then receives a short-lived capability
limited to that subject, backup identifier, object prefix, operation, client
proof key, nonce, and expiry. The application storage gateway validates the
capability and performs the exact operation within the application-operated S3
namespace.

Advantages:

- reduces public enumeration;
- familiar replacement-device flow;
- provider-neutral client workflow; and
- reuses the local S3-compatible contract.

Costs:

- admission/identity access and capability issuance are recovery prerequisites;
- the application operator and storage provider learn bounded recovery
  metadata; and
- admission, gateway, or storage outage blocks availability.

This is the approved default for the account-scoped provider profile. A
personal AWS or other storage-provider account is not required. Admission,
capability issuance, and storage availability are explicit prerequisites, not
cues, TPASS shares, or cryptographic factors. The deterministic local reviewer
profile implements the same interface without an external account.

### Exported recovery receipt

Enrollment exports a QR, file, or printed receipt containing a locator and
trusted public configuration.

Advantages:

- independent of account search;
- can carry a high-entropy locator and initial trust digest.

Costs:

- receipt possession becomes another operational factor;
- loss prevents this bootstrap route;
- public metadata may create linkability.

### Combined profile

Account discovery is the default and the receipt is an optional disaster path.
This direction is approved by D001--D003. The receipt may identify the provider
profile, account/recovery scope, high-entropy recovery handle, and an issuer or
initial public digest binding. It contains no cues, candidate hints, private
key material, or credentials.

## Authenticity

Recommended layers:

1. an application-pinned issuer/operator root authenticates the descriptor;
2. the descriptor authenticates configuration and endpoint identities;
3. recovery parties independently sign current epoch/configuration summaries;
4. the client requires a consistent threshold/current-state result before
   secret-dependent recovery.

The clean client must not bootstrap trust from an unauthenticated key in the
same descriptor.

Provider authentication and access control authorize ordinary retrieval but do
not authenticate LOCUS contents. An application-operator or provider snapshot
remains inside the cloud-compromise model.

The storage capability must not grant general bucket listing. It authorizes
only exact object operations required by the state machine, is bound to the
client proof key, and expires before the recovery session can be replayed as a
new admission. Direct S3 pre-signed bearer URLs are outside the approved core
profile.

## Rollback

A valid old signature proves that an old descriptor was once issued; it does not
prove freshness to a client with no trusted current state.

The base profile should:

- query current party state;
- reject descriptor/party disagreement;
- reject mixed epochs/configurations;
- disclose that coordinated rollback of authoritative party state remains
  outside the demonstrated boundary.

A monotonic external witness may be designed as a separate profile. It is not
silently required by the core thesis.

## Publication sequence

Enrollment:

1. provision party state;
2. verify required readiness;
3. produce the canonical encrypted backup member;
4. produce the signed descriptor that binds that member;
5. produce and locally revalidate the exact bundle manifest and bounded ZIP;
6. publish the immutable recovery bundle;
7. atomically install the authenticated current pointer; and
8. return/export the recovery receipt.

Successor:

1. prepare successor parties;
2. produce and validate the successor backup, descriptor, manifest, and bundle;
3. publish the immutable successor bundle;
4. compare-and-swap the authenticated current pointer;
5. activate successor; and
6. retire predecessor only after durable reachability.

The final ordering must be validated by crash analysis before implementation is
called complete.

## Required tests

- canonical round trip;
- duplicate/unknown/missing member rejection;
- unsupported version/algorithm;
- size/depth/string bounds;
- invalid issuer/signature;
- wrong subject/account scope;
- stale epoch;
- cross-user substitution;
- cross-policy substitution;
- cross-membership mix;
- descriptor/backup digest mismatch;
- descriptor/party current-state mismatch;
- endpoint key mismatch;
- expiry and rotation;
- concurrent current-pointer CAS;
- exact bundle member set and manifest binding;
- duplicate, unknown, nested, encrypted, unsafe-path, oversized,
  over-compressed, and unsupported ZIP member rejection;
- altered backup/descriptor member and whole-bundle digest rejection;
- stale valid bundle and rolled-back current-pointer rejection within the
  declared party-current-state model;
- positive controls for signature, freshness, and cross-binding checks.

## Provider profiles

The deterministic filesystem and same-host adapters are the reproducible
reference path. The common S3 contract uses create-only immutable publication
for bundles and descriptors, exact no-list retrieval, and ETag/version-bound
compare-and-swap for the mutable current pointer.

Conceptually, the admitted namespace contains only exact pseudonymous keys:

```text
<subject-scope>/<backup-id>/bundles/<epoch>/<bundle-digest>.zip
<subject-scope>/<backup-id>/current.json
```

The final key grammar and limits require a new registered provider profile. No
key contains an email address, phone number, location, display label, cue hash,
or other secret-derived identifier.

Required S3 behavior:

- create an immutable bundle only when its exact object key is absent;
- create an initial current pointer only when absent;
- replace a current pointer only when the previously authenticated ETag or
  provider version token still matches;
- retrieve only exact keys supplied by authenticated discovery, without bucket
  listing;
- use TLS and short-lived authorization limited to the admitted prefix and
  operation; and
- map precondition conflict, missing, unavailable, access-denied, oversized,
  and corrupt results into the registered LOCUS failure categories.

An S3 ETag or provider version token is a concurrency token, not a LOCUS
content digest. The client verifies the registered SHA-256 bundle, descriptor,
manifest, and backup bindings independently.

AWS S3 is the approved supplemental account-scoped adapter under D015. It must
implement the same bounded immutable-bundle and authenticated current-pointer
outcomes, use synthetic data and a separately authorized disposable research
account, and remain optional for CI and reviewers. The client receives only a
short-lived proof-key-bound capability accepted by the application storage
gateway, never an AWS access key.

S3 Versioning or Object Lock may be enabled as operational defense. Neither is
treated as proof of descriptor freshness or coordinated rollback resistance;
the signed current pointer and party-consistent current-state check remain
mandatory.
