# Owner Decision Register

The roadmap direction is approved: develop a more complete LOCUS reference
system while preserving the current thesis. The choices below remain explicit
gates before their affected implementation work.

| ID | Decision | Recommended default | Status |
| --- | --- | --- | --- |
| D001 | Clean-client discovery model | Account-scoped discovery of an authenticated current pointer and immutable recovery bundle, with an optional exported receipt | Approved |
| D002 | Whether cloud-account access is a default recovery prerequisite | Superseded by D015: no personal storage-provider account is required; the eventual D004 admission identity scopes access to application-operated storage | Superseded |
| D003 | Descriptor authenticity and rollback model | App-pinned issuer signature plus party-consistent current epoch; no coordinated-rollback claim without an external anchor | Approved |
| D004 | Public-client admission | Abstract proof-key-bound admission with a project-controlled local synthetic issuer; OIDC Authorization Code with PKCE/DPoP is an optional later adapter | Approved |
| D005 | Additional CuePolicies | Keep v1 immutable; add separate quantized-coordinate, canonical-phone, and canonical-email set policies | Approved |
| D006 | Cloud providers | Superseded by D015: replace the planned Google Drive adapter with the common S3 contract and an optional AWS S3 profile | Superseded |
| D007 | Evaluated recovery-suite profiles | Preserve the frozen Yi 2-of-3 baseline; evaluate aPPSS 2-of-3 first; add deployed aPPSS 3-of-5 only after configuration generalization | Approved |
| D008 | Meaning of party independence | Claim host separation after multi-host tests; reserve independent administration for actual independent operators | Approved |
| D009 | Attempt-control role | Local signed audit only; global rollback-resistant bound remains outside core | Approved |
| D010 | UI technology and platform | Cross-platform thin UI over stable local client APIs; framework selected after API freeze | Approved |
| D011 | General party replacement | Implement only after same-membership successor publication is integrated and crash-safe | Pending |
| D012 | External monotonic witness | Separate research profile, not mandatory LOCUS core | Pending |
| D013 | Human study | Separate future ethics-approved project; no current usability claims | Pending |
| D014 | Recovery bundle layout | Store each epoch as an immutable bounded ZIP containing a canonical backup object, signed descriptor, and manifest; keep the authenticated mutable current pointer outside the ZIP | Approved |
| D015 | S3 provider and user-access model | Application storage gateway over an account-scoped S3 namespace; local S3-compatible reference; optional AWS S3 profile; no client provider credentials | Approved |
| D016 | Password-protected recovery primitive | Make a new aPPSS suite the active profile for new enrollments after its gates pass; preserve the frozen Yi TPASS profile for legacy recovery; migrate only through a successor epoch | Approved |
| D017 | Exact aPPSS instantiation | Figure 4 aPPSS with a ristretto255/SHA-512 2HashDH OPRF, GF(2^128), SHA-256 commitment/secret derivation, abort-only robustness, and first 2-of-3 profile | Approved |

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

### D004 — Public-client admission boundary

Decision ID: D004
Date: 2026-08-01
Status: Approved
Chosen option: LOCUS defines one provider-neutral admission contract and first
implements it with a project-controlled local synthetic issuer. The issuer
authenticates a synthetic pseudonymous subject and issues a short-lived
capability bound to subject, backup identifier, epoch, operation, audience,
fresh client proof key, nonce, issuance time, and expiry. Every authorizer and
the application storage gateway independently validate the capability for
their exact audience and operation. The default prototype and artifact require
no external identity provider or identity-provider API. Any later approved
manuscript treatment may assume only the abstract authenticated pseudonymous
admission functionality rather than claim an identity protocol contribution.
OIDC Authorization Code with PKCE plus DPoP may later be implemented as an
optional adapter to the same contract, under a separately versioned provider
profile and separate evidence.
Alternatives considered: Making an external OIDC provider mandatory; treating
PKCE as a LOCUS-generated second factor; accepting a public backup, email, or
phone identifier as authentication; and omitting admission entirely.
New trust assumptions: The selected issuer is an authorization and
availability prerequisite. Its compromise can authorize online guesses or
cause denial of service, but does not reveal cue material or the recovery
secret by itself. The local issuer is a deterministic research test double,
not evidence about external federation, account recovery, or multifactor
authentication.
Privacy implications: The issuer, authorizers, and storage gateway may observe
a pseudonymous subject, backup/epoch scope, operation, audience, client-key
binding, and timing. They must not receive or retain raw email/phone
identifiers, cue values, `Z_M`, `p_M`, recovery-suite secret state, or final
recovery success. OIDC-specific identity leakage is outside the default
profile and must be evaluated if that adapter is added.
Compatibility/version impact: Requires a new abstract admission/capability
profile and local-issuer profile. Any OIDC/PKCE/DPoP adapter receives a distinct
identifier and cannot change the core request binding or CuePolicy/recovery
suite formats.
Required evidence: Valid local issuance plus wrong subject, backup, epoch,
operation, audience, client key, nonce, issuance/expiry, replay, and
cross-service negatives; issuer-unavailable and issuer-compromise limitations;
privacy-safe state/output inspection; and reviewer execution without external
credentials. An optional OIDC adapter requires separate conformance, privacy,
outage, and replay evidence.
Files or components authorized: `AdmissionVerifier`, local synthetic issuer,
proof-key-bound capability codec and replay state, authorizer and storage
gateway validation, test fixtures, and an optional later OIDC/PKCE/DPoP
adapter.
Manuscript implication: None authorized. Admission is an assumed
access-control/availability layer, not a LOCUS recovery factor, offline-oracle
improvement, identity contribution, or traceability mechanism.

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

### D007 — Evaluated recovery-suite profiles

Decision ID: D007
Date: 2026-08-01
Status: Approved
Chosen option: Preserve the frozen deployed Yi TPASS 2-of-3 profile as the
legacy baseline. Implement and evaluate the first aPPSS profile as 2-of-3
(`t_paper=1`, `k_LOCUS=2`, `n=3`). Add an aPPSS 3-of-5 deployment only after
threshold and membership configuration are generalized and the 2-of-3 gates
pass. The authorization quorum remains a separate 4-of-5 parameter in the
current reference topology.
Alternatives considered: Beginning with only 3-of-5; changing the frozen Yi
threshold; and conflating recovery threshold with authorization quorum.
New trust assumptions: None beyond each exact suite/profile; availability and
corruption statements are parameterized by the declared `k,n`.
Privacy implications: Larger profiles contact and expose bounded metadata to
more parties; evidence must report the exact coalition and topology.
Compatibility/version impact: New aPPSS 2-of-3 and later 3-of-5 deployment and
evidence profiles; no change to the frozen Yi identifiers or v2 evidence.
Required evidence: Every valid 2-of-3 subset, below-threshold and threshold
coalitions, one-party unavailability, and exact threshold/configuration
binding; repeat for 3-of-5 before making claims about it.
Files or components authorized: Parameterized suite-neutral configuration,
2-of-3 aPPSS implementation/evaluation, and later 3-of-5 deployment work after
its predecessor gates pass.
Manuscript implication: None authorized.

### D008 — Meaning of party independence

Decision ID: D008
Date: 2026-08-01
Status: Approved
Chosen option: Use "separate processes" for the current same-host deployment
and "host-separated" only after the multi-host profile passes. Reserve
"independently administered" for a profile actually operated by distinct
administrative principals with evidence of separate control.
Alternatives considered: Treating containers, hosts, or keys alone as proof of
independent administration.
New trust assumptions: Host separation reduces shared-host failure but does
not establish organizational independence.
Privacy implications: Each added operator can observe its own bounded service
metadata; cross-operator correlation remains a limitation.
Compatibility/version impact: Topology and administration scope are explicit
deployment/evidence profile fields and require new profiles when changed.
Required evidence: Host/key/state/network separation audits for multi-host
claims; separately documented operator/control evidence for any future
independent-administration claim.
Files or components authorized: Multi-host deployment tooling, topology
metadata, and claim/evidence wording limited to the tested scope.
Manuscript implication: None authorized.

### D009 — Attempt-control role

Decision ID: D009
Date: 2026-08-01
Status: Approved
Chosen option: Retain signed local attempt/audit state as an implementation and
diagnostic feature. Do not make a global, lifetime, or rollback-resistant
attempt bound part of the core LOCUS thesis or recovery-suite correctness
claim. A monotonic witness remains a separate D012 research profile.
Alternatives considered: Presenting the inherited quorum ledger as globally
rollback-resistant and making an external monotonic authority mandatory.
New trust assumptions: Local audit integrity applies only while the relevant
local state is current and not rolled back; coordinated rollback remains out
of scope.
Privacy implications: Audit records must remain aggregate and contain no cues,
password-derived values, raw admission credentials, or final secret material.
Compatibility/version impact: No change to frozen attempt formats; any global
authority requires a new architecture and evidence profile.
Required evidence: Preserve the rollback counterexample, validate local
signature/idempotency behavior, and scan audit outputs for prohibited data.
Files or components authorized: Local signed audit maintenance and UI wording
that accurately states its limited scope.
Manuscript implication: None authorized; attempt control is not promoted as a
contribution.

### D010 — UI technology and platform

Decision ID: D010
Date: 2026-08-01
Status: Approved
Chosen option: Build a cross-platform thin UI over stable enrollment and
recovery client APIs after those APIs are frozen. Select the framework at that
later gate using packaging, accessibility, persistence, and reviewer-workflow
evidence; do not let framework choice enter protocol semantics.
Alternatives considered: Selecting a web, Electron, native, or mobile framework
before API freeze and embedding canonicalization or recovery logic in the UI.
New trust assumptions: The UI process is part of the active-client boundary and
must not add telemetry or prohibited persistence.
Privacy implications: Cue input, clipboard, history, screenshots, crash output,
and telemetry require explicit prevention and testing.
Compatibility/version impact: Stable APIs precede the UI; a UI profile and
package version cannot change CuePolicy or recovery-suite bytes.
Required evidence: Cross-platform API conformance, persistence/log/history/
clipboard/crash-output scans, and exact-key recovery through the thin client.
Files or components authorized: Stable UI-facing APIs now and framework
selection/implementation only after the P7 predecessor gates pass.
Manuscript implication: None authorized; no usability claim follows.

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

### D016 — Versioned aPPSS successor

Decision ID: D016
Date: 2026-07-31
Status: Approved
Chosen option: LOCUS will implement Augmented Password-Protected Secret Sharing
(aPPSS) as a new, separately versioned recovery suite and make it the active
suite for new enrollments only after P5A's specification, implementation,
integration, evidence, and review gates pass. The aPPSS output `sk` is the
high-entropy LOCUS recovery secret `S_R` and is the sole input keying material
to the existing HKDF-SHA-256 wrapping-key derivation. Existing Yi TPASS epochs
remain recoverable through their frozen suite. Migration recovers the protected
key through the old epoch and creates a fresh aPPSS successor epoch; no Yi
party state, backup, identifier, or evidence is converted or reinterpreted in
place. One epoch binds exactly one recovery suite, with no automatic downgrade
or dual-suite fallback.
Alternatives considered: Mutating the frozen Yi implementation in place;
continuing Yi as the active profile; importing the paper's threshold-signature
construction rather than its aPPSS component; and retaining an independently
threshold-shared unmasked `S_R` behind aPPSS.
New trust assumptions: The exact aPPSS profile must satisfy the assumptions of
the approved Figure 4/Theorem 2 mapping, including a reviewed OPRF
instantiation, random-oracle hash mapping, authenticated initialization,
independent server OPRF state, authenticated server identities, and explicit
static/adaptive-corruption scope. The paper's threshold notation must be
translated as `k_LOCUS = t_paper + 1`.
Privacy implications: Below reconstruction threshold `k`, the intended aPPSS
state boundary exposes no local cue verifier under the stated assumptions. At
or above `k` compromised aPPSS servers, the adversary obtains an offline
dictionary-test capability; the high-entropy recovery secret is obtained after
a correct cue-derived password guess. This is delayed exposure, not continued
offline-guessing resistance, and its residual security depends on the
conditional cue distribution.
Compatibility/version impact: New recovery-suite, password-domain, public
parameter, party-state, wire, backup, descriptor, service, deployment, and
evidence identifiers are required. `LOCUS-TPASS-YI-ZK-RISTRETTO255-v1`,
`LOCUS-reference-backup-v4`, `LOCUS-compose-deployment-v2`, the Yi fixed vector,
and retained v2 evidence remain immutable and non-transferable.
Required evidence: Independent vectors and a consumer; bounded canonical-codec
and malformed-state tests; all valid small threshold subsets; authenticated
initialization; correct/wrong-input and cross-suite/epoch/session rejection;
crash/retry and successor migration; below-threshold, matching combined, and
at-threshold synthetic state views; an aggregate-only Yi/aPPSS compromise
comparator; new performance results; clean Linux/Windows reproduction; and
independent cryptographic review.
Files or components authorized: Suite-neutral planning and interfaces, a new
native aPPSS core and narrow binding after D017, new versioned service/storage
profiles, compatibility adapters, tests, documentation, and new evidence paths.
The supplied paper remains an ignored local research source and is not added to
the artifact without redistribution authorization.
Manuscript implication: None authorized. Proposed change set M-APPPSS-001
remains a separate owner gate.

### D017 — Exact aPPSS construction profile

Decision ID: D017
Date: 2026-08-01
Status: Approved
Chosen option: Instantiate only Section 3/Figure 4 aPPSS, not aptSIG. Use the
paper's 2HashDH shape concretized with the RFC 9497 OPRF-mode
ristretto255/SHA-512 group and canonical element rules, independently keyed per
server and per epoch. Set `lambda=128`; use degree-`k-1` Shamir sharing over
`GF(2^128)` with modulus `x^128+x^7+x^2+x+1` and one canonical 16-byte
big-endian polynomial-basis representation; derive each 16-byte mask from the
OPRF output; and instantiate Figure 4's 256-bit `[C || S_R]` random-oracle
mapping with domain-separated SHA-256. Bind all fixed cryptographic inputs to
one suite, backup identifier, epoch, CuePolicy, membership, threshold, and
configuration, and bind every online transcript additionally to the party,
operation, authorization, and fresh session. Public `omega=(e,C)` is canonical
and digest-bound into every party/backup/descriptor view. Use strict canonical
decoding and one generic recovery rejection. The first evaluated profile is
`k=2,n=3`. Adopt the base Figure 4 abort-only malicious-server behavior; do not
add the optional VOPRF robustness extension in the first profile. The exact
P1.2 contract is `docs/APPSS-PROFILE.md`; final protocol identifiers, wire
schemas, and vectors remain assigned together at P5A.1.
Alternatives considered: Importing aptSIG; using a separately specified VOPRF
extension; choosing 3-of-5 first; using a prime Shamir field; retaining an
independent unmasked recovery secret; and silently reusing Yi domains/formats.
New trust assumptions: Theorem 2 applies in the `(F_OPRF,F_AUTH)` hybrid with
its hash modeled as a random oracle. The concrete profile separately assumes
the security of the RFC 9497 OPRF-mode ristretto255/SHA-512 realization,
authenticated distributed initialization, independent honest server key
generation, authenticated server identities, secure randomness, and the
declared erasure/corruption boundary. The first implementation/evidence claim
is limited to static persistent-state compromise; stronger adaptive or
proactive claims require separate review.
Privacy implications: Fewer than `k` matching server states have no local cue
predicate under the declared assumptions. `k` or more server states plus
public `omega` enable unrate-limited offline candidate tests; a correct
candidate yields the 128-bit `S_R`. No conditional cue-entropy, memorability,
side-channel, or production-security claim follows.
Compatibility/version impact: All aPPSS domains, public/party/client state,
messages, backup/descriptor bindings, deployment, and evidence receive new
identifiers at P5A.1. Frozen Yi formats, vectors, legacy recovery, and retained
v2 evidence remain unchanged and cannot mix with this profile.
Required evidence: Independent and cross-language vectors, field/OPRF/hash
conformance, every 2-of-3 subset, authenticated initialization, strict decoding,
wrong-input and cross-context rejection, abort/retry behavior, client-state
disposal, below-threshold and exact-threshold state views with positive
controls, Yi comparison, migration, performance, clean Linux/Windows runs, and
independent cryptographic review. Tests demonstrate implementation behavior;
they do not prove Theorem 2.
Files or components authorized: The exact P1.2 specification and suite-neutral
interfaces now; new schemas/vectors and a separate native aPPSS core at P5A
after its chronological prerequisites. No modification of the frozen Yi core.
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

Approval of D001--D017 authorizes only the recorded architecture or
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

### M-APPPSS-001 — Active aPPSS profile and comparative compromise result

Change-set ID: M-APPPSS-001
Date proposed: 2026-07-31
Exact file and sections: `paper/main.tex` abstract, introduction and
contributions, threat model and attacker table, requirements, protocol
construction, implementation, evaluation, security analysis, lifecycle,
limitations, related work/comparison table, conclusion, open science, and
cryptographic appendix; plus the aPPSS bibliographic record in
`paper/references.bib`. No title change is proposed.
Before/after summary: Replace the paper-facing active Yi TPASS profile with the
implemented and evaluated aPPSS profile; retain Yi only as an explicitly frozen
legacy/baseline comparison; describe suite-bound migration; and add the scoped
result that below-threshold state gives neither profile a local cue verifier,
while reconstruction-threshold Yi state directly reconstructs its shared
password and recovery secret and reconstruction-threshold aPPSS state instead
enables unrate-limited offline guessing until the correct cue-derived password
reveals the recovery secret.
Claim and evidence basis: Theorem 2 and the Section 3 construction of
*Password-Protected Threshold Signatures*, the reviewed theorem-to-code mapping,
new aPPSS conformance/correctness/state-boundary evidence, the fixed
aggregate-only Yi/aPPSS comparator, and separately versioned performance data.
The cryptographic result is inherited; LOCUS claims only its exact composition
and implementation/evidence boundary.
Limitations affected: Random-oracle/OPRF/authenticated-initialization
assumptions; threshold-notation translation; conditional cue entropy after
threshold compromise; local unrate-limited guessing at threshold; malicious
server abort behavior; no proactive/mobile compromise, side-channel,
production-security, memorability, or usability claim; old performance/evidence
cannot support the new profile.
Owner status: Pending
Implementation/evidence commit: Pending P5A and P8/P9
Applied commit:
Rendered PDF SHA-256:
