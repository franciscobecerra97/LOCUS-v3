# RecoveryDescriptor And Recovery-Bundle Design

Status: P2.1 formats and P2.2 discovery/trust-bootstrap validation, strict
codecs, schemas, and canonical vectors implemented on 2026-08-01 under D001,
D003, D014, and D015. D015 supersedes the former personal-cloud-account and
Google Drive choices in D002 and D006. P2.3 storage and P2.4 development
security regressions are implemented; public admission, complete clean-client
recovery, and formal evidence remain later gates. This design does not
supersede the imported baseline or current manuscript.

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

## P2.1 registered formats

| Boundary | Identifier | Maximum canonical size | Compatibility rule |
| --- | --- | --- | --- |
| Signed descriptor | `LOCUS-recovery-descriptor-v1` | 65,536 bytes | New payload field or interpretation requires a new descriptor identifier |
| Signed current pointer | `LOCUS-descriptor-current-pointer-v1` | 16,384 bytes | Mutable replacement uses P2.3 compare-and-swap; signed bytes remain canonical and immutable per value |
| Bootstrap signature | `LOCUS-bootstrap-signature-v1` | Ed25519, 64-byte signature | Key comes from the installed trust root, never from the signed object |
| Configuration digest | `LOCUS-recovery-configuration-v1` | SHA-256 output | Binds subject, backup, epoch, recovery ID, backup member, policy, suite, and authorization configuration |
| Bundle manifest | `LOCUS-recovery-bundle-manifest-v1` | 16,384 bytes | Binds only `backup.json` and `descriptor.json`; never itself |
| Bundle container | `LOCUS-recovery-bundle-v1` | 2,097,152 bytes | Exact deterministic three-member stored ZIP; any changed ZIP profile receives a new identifier |

The normative JSON schemas are:

- `schemas/recovery-descriptor-v1.schema.json`;
- `schemas/descriptor-current-pointer-v1.schema.json`; and
- `schemas/recovery-bundle-manifest-v1.schema.json`.

The strict executable codec is `prototype/locus/recovery_descriptor.py`. The
synthetic canonical vector is
`prototype/test-vectors/recovery-descriptor-v1.txt`.

## Canonical signed-object envelope

The descriptor and current pointer use the same exact outer shape:

```json
{
  "payload": {},
  "signature": {
    "algorithm": "Ed25519",
    "key_id": "externally-pinned-key-id",
    "value": "128 lowercase hexadecimal characters",
    "version": "LOCUS-bootstrap-signature-v1"
  },
  "version": "object-specific identifier"
}
```

The Ed25519 message is the ASCII domain
`LOCUS/bootstrap-signed-object/v1`, a zero byte, and the canonical encoding of
the object version, complete payload, and signature metadata excluding only the
signature value. This binds the algorithm, key ID, object type, and payload.
The decoder receives the expected issuer, key ID, and Ed25519 public key from
the installed application trust configuration. No public key or trust root is
accepted from the descriptor, pointer, bundle, provider, or admission result.

## Exact `RecoveryDescriptor` payload

The v1 payload has exactly these top-level members:

| Member | Meaning |
| --- | --- |
| `issuer`, `issued_at`, `expires_at` | Externally expected issuer and positive integer validity interval |
| `subject_id` | 32-byte lowercase-hex pseudonymous admission/storage scope; never an email, phone, label, or cue-derived identifier |
| `backup_id`, `epoch`, `recovery_id` | 16-byte backup ID, positive epoch, and bounded public recovery identity |
| `backup` | Exact `backup.json` member name, registered backup format, byte length, and ordinary SHA-256 digest |
| `cue_policy` | Registered policy ID, opaque canonical public-parameter bytes encoded as lowercase hex, and resolver profile |
| `recovery_suite` | Suite ID, public-state format and canonical bytes, typed `k,n`, and sorted holder-to-authorizer membership |
| `authorization` | Sorted authorizer IDs, HTTPS endpoints, external identity-key IDs, distinct quorum, admission profile, audience, operation namespace, and security policy |
| `lifecycle` | Configuration digest and nullable predecessor-descriptor digest |

The descriptor uses opaque canonical hex for CuePolicy public parameters and
suite public state so their own registered adapters—not the descriptor—own
their semantics. The descriptor still binds their exact bytes and identifiers.
Holder membership is separate from authorizer membership; every holder maps to
one authorizer, while recovery `k,n` and authorization quorum are validated as
different values.

The configuration digest is:

```text
HashBytes(
  "LOCUS-recovery-configuration-v1",
  Encode({
    version, subject_id, backup_id, epoch, recovery_id,
    backup, cue_policy, recovery_suite, authorization
  })
)
```

Validity timestamps limit acceptance but do not by themselves establish
freshness. The P2.2 party-current-state check remains mandatory.

The canonical vector uses `test-only:unassigned-p3.3` as a non-deployable
admission-profile fixture because P3.3 has not assigned the real admission
identifier. The descriptor grammar can carry a registered admission profile,
but no implementation may treat that test value as usable admission.

## Exact authenticated current pointer

The current-pointer payload contains exactly:

- issuer, pseudonymous subject ID, backup ID, epoch, issuance, and expiry;
- `LOCUS-recovery-bundle-v1`, provider-assigned immutable locator, exact ZIP
  byte length, and ordinary SHA-256 digest;
- exact descriptor SHA-256 digest; and
- exact configuration digest.

It contains no backup-member digest because the signed descriptor supplies that
binding, and no concurrency token because the P2.3 store keeps ETag/provider
version state outside the canonical LOCUS pointer. Verification requires the
pointer, bundle, descriptor, subject, backup, epoch, and configuration bindings
to agree before any cue-dependent work.

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

P2.1 freezes deterministic ZIP transport metadata rather than treating multiple
ZIP encodings as equivalent:

- member order is exactly `backup.json`, `descriptor.json`, `manifest.json`;
- all three are regular files at the archive root;
- compression method is `ZIP_STORED`;
- timestamp is 1980-01-01 00:00:00;
- creator system is Unix, creator/extractor version is 2.0, and regular-file
  mode is `0600`;
- general-purpose flags, internal attributes, extra fields, member comments,
  and archive comment are empty; and
- no ZIP64, prefix, suffix, encryption, data descriptor, nested archive, or
  alternate member order is accepted.

The maximum canonical member sizes are 1,048,576 bytes for `backup.json`,
65,536 bytes for `descriptor.json`, and 16,384 bytes for `manifest.json`.
Aggregate member bytes and the 2,097,152-byte ZIP limit are checked before
reading. A compression-ratio ceiling of 20 is checked before rejecting a
non-stored method, so an over-compressed input receives a bounded failure even
though compression is unsupported by v1.

The ZIP decoder must reject:

- missing, duplicate, unknown, nested, or directory members;
- absolute paths, path separators, `..`, alternate data streams, or names that
  are not the exact registered ASCII member names;
- encrypted members, unsupported compression methods, data descriptors or
  ambiguous metadata not admitted by the frozen profile;
- per-member, aggregate compressed, aggregate decompressed, nesting, and
  compression-ratio limit violations; and
- noncanonical member bytes or any manifest/digest/length mismatch.

The ZIP's exact uploaded bytes are its identity in the current pointer. Member
digests are ordinary SHA-256 because the signed objects provide contextual
authentication; the configuration digest uses the separately registered LOCUS
domain. The manifest does not contain a `manifest.json` entry or any digest of
itself.

## P2.1 disclosure analysis

The descriptor, manifest, bundle metadata, and current pointer disclose a
pseudonymous subject scope, backup ID, epoch, public formats, policy category,
suite, thresholds, membership, endpoints, issuer/key IDs, validity, object
sizes, locators, and digests. The application operator, provider, issuer, and
parties may therefore correlate recovery activity and configuration. This is a
privacy and enumeration limitation.

They contain no raw cue, selected record, per-cue descriptor, cue hash,
candidate hint, `Z_M`, `p_M`, password-derived authenticator, party secret
state, `S_R`, `K_wrap`, plaintext private key, credential, or final recovery
outcome. Ordinary SHA-256 digests bind already-public canonical objects; none
is computed over cue-derived or password-derived material. Within the declared
cloud/descriptor snapshot model, these fields add no local predicate for cue
candidates. That conclusion remains conditional on the suite assumptions and
must be tested again against the exact P2.4 persistent-state surface with a
positive control. It does not cover client compromise, online party access,
side channels, weak cue distributions, issuer compromise, or coordinated
rollback.

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
profile will implement the same interface without an external account in
P2.3/P3. P2.2 authenticates already supplied gateway response bytes; it does
not simulate capability issuance or provider retrieval early.

### Exported recovery receipt

`LOCUS-recovery-receipt-v1` is an optional operator-signed QR, file, or printed
object. It contains the pseudonymous subject, recovery handle, bootstrap
profile, exact discovery endpoint, issuer/key ID, issuance time, and an
optional initial backup/epoch/configuration/descriptor digest anchor.

Advantages:

- independent of account search;
- can carry a high-entropy locator and initial trust digest.

Costs:

- receipt possession becomes another operational factor;
- loss prevents this bootstrap route;
- public metadata may create linkability.

### Combined profile

Account discovery is the default and the receipt is optional bootstrap input.
This direction is approved by D001--D003. The receipt may identify the provider
profile, account/recovery scope, high-entropy recovery handle, and an issuer or
initial public digest binding. It contains no cues, candidate hints, private
key material, or credentials. It is not an independent freshness witness: a
later epoch still requires a live party-current-state quorum.

## P2.2 installed trust and authenticity

`LOCUS-bootstrap-trust-config-v1` is a canonical file delivered with the
trusted LOCUS application installation or update. It contains exactly:

- profile, generation, validity interval, and previous-configuration SHA-256;
- one operator issuer, Ed25519 key ID, and public key;
- one HTTPS discovery endpoint and audience; and
- a sorted exact authorizer set with HTTPS endpoint, identity-key ID, and
  Ed25519 public key for each party.

The initial generation has no predecessor. A later generation must be exactly
one greater and bind the exact previous bytes. This continuity check does not
authenticate an update downloaded from an untrusted source: replacement trust
configuration must arrive through the application's trusted installation or
update channel. Endpoint, operator-key, party-key, and root rotation therefore
fail closed until such an installed replacement exists.

The implemented bootstrap order is:

1. strictly decode the installed configuration and check its validity;
2. require the observed discovery endpoint to equal the installed endpoint;
3. authenticate the signed current pointer and bundle/descriptor with the
   installed operator key and verify all P2.1 cross-bindings;
4. require the external subject and recovery handle to match the pointer and
   descriptor, and authenticate the optional receipt if supplied;
5. require every descriptor party endpoint and identity-key ID to equal the
   installed exact party directory; and
6. verify short-lived party current-state summaries and require the
   descriptor's authorization quorum to match the cloud descriptor before any
   cue processing.

The descriptor authenticates configuration content but introduces no trusted
key or endpoint. `LOCUS-party-current-summary-v1` binds active state, party,
subject, backup, recovery identity, epoch, descriptor digest, configuration
digest, CuePolicy, and recovery suite. It has its own
`LOCUS-party-current-signature-v1` domain and a maximum 300-second validity
window. Valid signed dissent is reported separately. Four matching summaries
in the current 4-of-5 authorization profile permit bootstrap even if a fifth
party is unavailable or reports different state; fewer than four matching
summaries fail explicitly as unavailable or cloud/party mismatch.

The normative P2.2 schemas are
`schemas/bootstrap-trust-config-v1.schema.json`,
`schemas/recovery-receipt-v1.schema.json`, and
`schemas/party-current-summary-v1.schema.json`. The executable validator is
`prototype/locus/recovery_bootstrap.py`; its canonical public-object vector is
`prototype/test-vectors/recovery-bootstrap-v1.txt`.

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

The base profile now:

- requires a fresh authorization quorum of party state;
- rejects descriptor/party disagreement below that matching quorum;
- rejects mixed epochs/configurations and untrusted endpoints/keys;
- discloses that coordinated rollback of authoritative party state remains
  outside the demonstrated boundary.

A monotonic external witness may be designed as a separate profile. It is not
silently required by the core thesis.

An operator-key compromise can forge cloud objects and receipts but cannot
forge the independently pinned party quorum. Compromise of the operator and
the required party quorum defeats this bootstrap profile. Likewise, a
coordinated restoration of cloud state, required party states and keys, and
the client clock/trust view can present a consistent old world; signed version
numbers and short-lived summaries do not provide a global monotonic anchor.

Account/admission loss, gateway outage, storage loss, and insufficient live
party summaries are availability failures. Discovery and current-state
queries expose the pseudonymous subject/handle, endpoint set, backup/epoch,
configuration and descriptor digests, timing, and access pattern to the
operator and contacted parties. None of the P2.2 formats contains cue input,
`Z_M`, `p_M`, a verifier, party secret state, `S_R`, `K_wrap`, a plaintext key,
or provider/admission credentials.

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

P2.3 implements the deterministic filesystem and same-host service adapters as
the reproducible reference path. The common S3-compatible contract uses
create-only immutable publication for bundles and descriptors, exact no-list
retrieval, and ETag-bound compare-and-swap for the mutable current pointer.
Both implement `LOCUS-descriptor-bundle-store-v1` and preserve exact P2.1 bytes.

Conceptually, the admitted namespace contains only exact pseudonymous keys:

```text
<subject-scope>/<backup-id>/bundles/<epoch>/<bundle-digest>.zip
<subject-scope>/<backup-id>/current.json
```

The registered key grammar hashes the recovery handle for the mutable pointer
and uses only pseudonymous subject/backup IDs and public content digests. No key
contains an email address, phone number, location, display label, cue hash, or
other secret-derived identifier.

Implemented S3-compatible behavior:

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
