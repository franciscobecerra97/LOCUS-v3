# Owner Decision Register

The roadmap direction is approved: develop a more complete LOCUS reference
system while preserving the current thesis. The choices below remain explicit
gates before their affected implementation work.

| ID | Decision | Recommended default | Status |
| --- | --- | --- | --- |
| D001 | Clean-client discovery model | Account-scoped discovery of an authenticated current pointer and immutable recovery bundle, with an optional exported receipt | Approved |
| D002 | Whether cloud-account access is a default recovery prerequisite | Superseded by D015: no personal storage-provider account is required; the eventual D004 admission identity scopes access to application-operated storage | Superseded |
| D003 | Descriptor authenticity and rollback model | App-pinned issuer signature plus party-consistent current epoch; no coordinated-rollback claim without an external anchor | Approved |
| D004 | Public-client admission | Local test issuer first; later OIDC authorization-code/PKCE with DPoP-bound short-lived tokens | Pending |
| D005 | Additional CuePolicies | Keep v1 immutable; add separate quantized-coordinate, canonical-phone, and canonical-email set policies | Approved |
| D006 | Cloud providers | Superseded by D015: replace the planned Google Drive adapter with the common S3 contract and an optional AWS S3 profile | Superseded |
| D007 | Evaluated TPASS profiles | Preserve 2-of-3 baseline; add deployed 3-of-5 after configuration generalization | Pending |
| D008 | Meaning of party independence | Claim host separation after multi-host tests; reserve independent administration for actual independent operators | Pending |
| D009 | Attempt-control role | Local signed audit only; global rollback-resistant bound remains outside core | Pending |
| D010 | UI technology and platform | Cross-platform thin UI over stable local client APIs; framework selected after API freeze | Pending |
| D011 | General party replacement | Implement only after same-membership successor publication is integrated and crash-safe | Pending |
| D012 | External monotonic witness | Separate research profile, not mandatory LOCUS core | Pending |
| D013 | Human study | Separate future ethics-approved project; no current usability claims | Pending |
| D014 | Recovery bundle layout | Store each epoch as an immutable bounded ZIP containing a canonical backup object, signed descriptor, and manifest; keep the authenticated mutable current pointer outside the ZIP | Approved |
| D015 | S3 provider and user-access model | Application storage gateway over an account-scoped S3 namespace; local S3-compatible reference; optional AWS S3 profile; no client provider credentials | Approved |

## Approved architecture records

### D001 — Clean-client discovery model

Decision ID: D001  
Date: 2026-07-31  
Status: Approved  
Chosen option: Account-scoped discovery retrieves an authenticated current
pointer that names one immutable per-epoch recovery bundle. An optional exported
receipt may provide the provider profile, account/recovery scope, recovery
handle, and an issuer or initial public digest binding.  
Alternatives considered: Public enumeration, receipt-only discovery, and hidden
enrollment-client configuration.  
New trust assumptions: The eventual D004 admission/capability service and the
application-operated S3 namespace are required for availability in this
profile but are not trusted to authenticate descriptor contents.  
Privacy implications: The application operator and storage provider can
observe bounded account-scoped recovery objects and activity. The receipt may
create linkability and must contain no cue or secret material.  
Compatibility/version impact: Requires new current-pointer, descriptor, bundle,
and discovery-profile versions. Frozen baseline formats remain unchanged.  
Required evidence: Wrong-subject-scope, wrong-handle, substitution, stale-pointer,
receipt-mismatch, and provider-unavailable scenarios with positive controls.  
Files or components authorized: RecoveryDescriptor, DescriptorStore,
RecoveryBundleStore convenience layer, local discovery adapter, and the
supplemental AWS S3 discovery/storage profile defined by D015.  
Manuscript implication: None authorized; any future wording remains a separate
owner-gated change set.

### D002 — Cloud-account prerequisite

Decision ID: D002  
Date: 2026-07-31  
Status: Superseded by D015  
Chosen option: Access to the selected cloud account is a recovery prerequisite
for the account-scoped provider profile. It is an availability and admission
prerequisite, not a cue, TPASS share, or additional cryptographic factor.  
Alternatives considered: Public high-entropy locator and receipt-only recovery.  
New trust assumptions: Account loss, provider lockout, deletion, or outage can
block this discovery path.  
Privacy implications: The provider learns account identity and access metadata
subject to its service behavior.  
Compatibility/version impact: Recorded in the discovery and admission profiles;
the local reviewer profile continues to require no external account.  
Required evidence: Explicit unavailable, locked/missing-account test-double
outcomes and documentation of the availability limitation.  
Files or components authorized: Discovery state machine and provider adapters.  
Manuscript implication: None authorized.

Supersession note: D015 removes the personal storage-provider account
requirement. The user instead authenticates through the eventual D004 LOCUS
admission/identity profile and receives a short-lived capability scoped to an
application-operated storage namespace. Admission and service availability
remain explicit recovery prerequisites.

### D003 — Descriptor authenticity and rollback

Decision ID: D003  
Date: 2026-07-31  
Status: Approved  
Chosen option: The installed client authenticates descriptors and current
pointers through an application-pinned issuer root, then requires consistent
party-signed current epoch/configuration summaries before secret-dependent
recovery. A signature from inside the bundle never authenticates its own root.  
Alternatives considered: Trusting cloud ACLs, trusting a key carried only by the
descriptor, and treating a signed version number as sufficient freshness.  
New trust assumptions: The issuer root and the required current-state party
set are trusted within the declared profile. Coordinated rollback of all
authoritative state remains outside the demonstrated boundary.  
Privacy implications: Current-state queries reveal bounded recovery metadata to
the contacted parties.  
Compatibility/version impact: Requires issuer, validity, configuration-digest,
and current-state bindings in new formats.  
Required evidence: Invalid issuer/signature, stale epoch, mixed configuration,
endpoint substitution, and coordinated-rollback limitation tests and analysis.  
Files or components authorized: Descriptor validation, party current-state
summaries, trust-root configuration, and bootstrap state machine.  
Manuscript implication: None authorized.

### D005 — Additional CuePolicies

Decision ID: D005  
Date: 2026-07-31  
Status: Approved  
Chosen option: Preserve `LOCUS-location-person-set-v1` byte-for-byte and add
three atomic policies: exactly three distinct quantized geographic coordinates,
exactly three distinct canonical E.164 phone numbers, and exactly three
distinct canonical constrained email addresses. Direct-input profiles are
resolver-free.  
Alternatives considered: Two unrelated new policy families, one parameterized
contact policy, and changing the existing composite policy.  
New trust assumptions: None in the TPASS core. A resolver-backed coordinate
profile, if later approved, adds the separately documented resolver boundary.  
Privacy implications: The public policy identifier reveals the input category.
Phone, email, and location values may be guessable from public or social
knowledge; no entropy, memorability, or usability claim is authorized.  
Compatibility/version impact: Three new immutable policy identifiers and domain
separation labels are required after schemas are approved. The frozen v1
identifier and vectors do not change.  
Required evidence: Shared conformance, cross-policy rejection, frozen-v1
compatibility, clean Linux/Windows execution, and an independent vector
consumer.  
Files or components authorized: CuePolicy registry, three atomic policy
implementations, `NoResolver`, vectors, and conformance tests.  
Manuscript implication: None authorized.

### D006 — Cloud provider profile

Decision ID: D006  
Date: 2026-07-31  
Status: Superseded by D015  
Chosen option: Retain deterministic filesystem and S3-compatible adapters for
reproducible tests and add Google Drive as a supplemental account-scoped
backup/descriptor/bundle adapter.  
Alternatives considered: Making a real provider mandatory or replacing the
existing reference adapters.  
New trust assumptions: Provider authentication and availability apply only to
the supplemental profile; cryptographic authenticity continues to come from
LOCUS validation.  
Privacy implications: The provider observes account, object, timing, size, and
access metadata according to its service behavior.  
Compatibility/version impact: Requires a new provider profile and adapter
identifier without changing existing storage identifiers.  
Required evidence: Common storage conformance plus a separately authorized,
disposable, synthetic-account functional profile. CI and reviewer workflows
must not require Google credentials.  
Files or components authorized: Google Drive adapter and provider-specific test
profile after the local contract is complete.  
Manuscript implication: None authorized.

Supersession note: No Google Drive adapter is authorized for the active plan.
D015 adopts the common S3 contract and an optional AWS S3 profile instead.

### D014 — Recovery bundle layout

Decision ID: D014  
Date: 2026-07-31  
Status: Approved  
Chosen option: Each epoch may be represented by an immutable bounded ZIP with
exact members `backup.json`, `descriptor.json`, and `manifest.json`. The
descriptor binds the canonical backup-member digest; the manifest binds exact
backup/descriptor member sizes and digests without digesting itself; the
authenticated current pointer outside the ZIP
binds the provider-assigned locator and exact digest of the active
bundle/descriptor. The descriptor does not contain its enclosing bundle's
locator or digest.  
Alternatives considered: One self-digesting ZIP, mutable ZIP replacement, and
provider-native files without an exportable bundle.  
New trust assumptions: None; the ZIP is a transport container rather than a
trust root.  
Privacy implications: Bundle filenames, sizes, and access metadata are visible
to the application operator and selected storage provider; no cue-derived or
secret material may appear in filenames or manifests.  
Compatibility/version impact: Requires new recovery-bundle and bundle-manifest
formats. Backup, descriptor, and pointer remain distinct logical contracts even
when physically colocated.  
Required evidence: Duplicate/unknown/path-traversal member rejection,
compressed/decompressed bounds, unsupported compression/encryption rejection,
member-digest substitution, stale bundle, exact retry, and positive controls.  
Files or components authorized: Recovery-bundle codec, bounded decoder, local
adapter, tests, and later provider adapter.  
Manuscript implication: None authorized.

### D015 — S3 provider and user-access model

Decision ID: D015  
Date: 2026-07-31  
Status: Approved; supersedes D002 and D006  
Chosen option: LOCUS uses an application-operated, account-scoped S3 namespace.
Deterministic filesystem and local S3-compatible adapters remain the
reproducible reference. AWS S3 is the optional real-provider profile. A user
authenticates through the eventual owner-approved D004 admission/identity flow
and presents its short-lived, proof-key-bound admission capability to an
application storage gateway. The gateway performs only exact authorized S3
operations; the client never receives an AWS credential and needs no personal
AWS account. Direct S3 pre-signed bearer URLs are not part of this approved
profile.  
Alternatives considered: Direct personal Google Drive/iCloud-style storage,
personal AWS buckets, Azure Blob Storage, and Cloudflare R2.  
New trust assumptions: The admission/capability issuer and application storage
gateway are availability prerequisites. S3 authorization controls
ordinary access but does not authenticate descriptors or establish freshness.  
Privacy implications: The application operator and external provider can
observe bounded subject/namespace, object key, timing, size, and access
metadata. Object keys use pseudonymous identifiers and contain no user label,
cue, candidate, or secret value.  
Compatibility/version impact: The existing immutable S3 backup adapter remains
the storage-side implementation starting point. New strict gateway,
descriptor, current-pointer, bundle, capability, and AWS deployment profiles
are required; frozen S3 and backup identifiers are not reinterpreted.  
Required evidence: Shared local S3 contract tests; create-only bundle writes;
ETag-bound current-pointer compare-and-swap; no-list retrieval; expired,
wrong-subject, wrong-prefix, wrong-operation, and replayed capability rejection;
provider outage mapping; output/credential scans; and an optional separately
authorized AWS run with synthetic data. S3 Versioning or Object Lock is
operational defense only and is not LOCUS rollback-resistance evidence.  
Files or components authorized: Common S3 backup/descriptor/pointer/bundle
adapter, application storage gateway, local S3-compatible profile,
proof-key-bound storage capability boundary, and optional AWS S3 profile after
D004 and the local contract are complete.  
Manuscript implication: None authorized.

## Decision record template

When the owner decides an item, append:

```text
Decision ID:
Date:
Status: Approved | Rejected | Superseded
Chosen option:
Alternatives considered:
New trust assumptions:
Privacy implications:
Compatibility/version impact:
Required evidence:
Files or components authorized:
Manuscript implication:
```

## Manuscript change authorization

Approval of D001--D015 authorizes only the recorded architecture or
implementation scope. It does not authorize corresponding paper wording.

Record every proposed manuscript change separately:

```text
Change-set ID:
Date proposed:
Exact file and sections:
Before/after summary:
Claim and evidence basis:
Limitations affected:
Owner status: Approved | Skipped | Superseded
Implementation/evidence commit:
Applied commit:               # only after approval
Rendered PDF SHA-256:         # only after approval and visual verification
```
