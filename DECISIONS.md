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
| D007 | Evaluated recovery-suite profiles | Preserve the frozen Yi 2-of-3 baseline; evaluate aPPSS 2-of-3 first; add deployed aPPSS 3-of-5 only after configuration generalization | Superseded by D018 |
| D008 | Meaning of party independence | Claim host separation after multi-host tests; reserve independent administration for actual independent operators | Approved |
| D009 | Attempt-control role | Local signed audit only; global rollback-resistant bound remains outside core | Approved |
| D010 | UI technology and platform | Cross-platform thin UI over stable local client APIs; framework selected after API freeze | Approved |
| D011 | General party replacement | Defer until after the selectable-suite and paired-profile work; same-membership successors remain the active lifecycle scope | Approved — Deferred |
| D012 | External monotonic witness | Separate research profile, not mandatory LOCUS core | Pending |
| D013 | Human study | Separate future ethics-approved project; no current usability claims | Pending |
| D014 | Recovery bundle layout | Store each epoch as an immutable bounded ZIP containing a canonical backup object, signed descriptor, and manifest; keep the authenticated mutable current pointer outside the ZIP | Approved |
| D015 | S3 provider and user-access model | Application storage gateway over an account-scoped S3 namespace; local S3-compatible reference; optional AWS S3 profile; no client provider credentials | Approved |
| D016 | Password-protected recovery primitive | Make a new aPPSS suite the active profile for new enrollments after its gates pass; preserve the frozen Yi TPASS profile for legacy recovery; migrate only through a successor epoch | Superseded by D018 |
| D017 | Exact aPPSS instantiation | Figure 4 aPPSS with a ristretto255/SHA-512 2HashDH OPRF, GF(2^128), SHA-256 commitment/secret derivation, abort-only robustness, and first 2-of-3 profile | Approved |
| D018 | Selectable recovery suites and paired profiles | Keep Yi TPASS and aPPSS as independent first-class suites; select exactly one per enrollment/epoch; evaluate both under paired 2-of-3 and 3-of-5 conditions | Approved |
| D019 | Recovery-suite review scope | Independent claim-focused mapping review of both Yi TPASS and aPPSS, including their LOCUS composition and documented deviations; not a full production cryptographic audit | Approved |
| D020 | Provisional internal review and deferred human validation | Permit an explicitly non-independent internal mapping assessment to close P5A implementation chronology and allow P6 work, while retaining human cryptographic validation as a mandatory pre-manuscript/pre-release gate | Approved |
| D021 | P6 paired topology and honest deployment tier | Use matched Yi/aPPSS 2-of-3 and 3-of-5 recovery profiles with a separately typed 4-of-5 authorization quorum; target local-VM host separation without claiming independent administration | Approved |
| D022 | P7 local research UI runtime | Standards-based HTML/CSS/JavaScript served only on loopback by the pinned Python runtime over `LOCUS-client-api-v1`; no third-party web framework, telemetry, or browser storage | Approved |
| D023 | Primary integrated reference system and evidence target | One separately versioned, same-host Docker reference system connects the loopback UI/client gateway to every authenticated LOCUS service and becomes the mandatory P8/P9 system-under-test; component and historical profiles remain supporting controls only | Approved |
| D024 | Final prototype source and command boundary | Create a self-contained `prototype_final/` workspace containing only the D023 integrated implementation, focused tests, native dependencies, deployment assets, documentation, and `integrated-*` executor commands; direct all P8+ implementation and evidence work to it while preserving existing paths as historical/component controls | Approved |
| D025 | Manager-controlled integrated deployment and transient client workflow | Replace the D023 enrollment/recovery startup profiles in the active D024 workspace with a newly versioned loopback Manager UI, an internal narrow Docker lifecycle controller, and dynamically created transient Client UI containers; preserve the approved protocol profiles and local provider path while adding a client recovery-package export/import transport | Approved |

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
Status: Superseded by D018
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

### D011 — General party replacement timing

Decision ID: D011
Date: 2026-08-03
Status: Approved — Deferred
Chosen option: Do not implement general recovery-party membership replacement
before P5 and P5A. Keep the implemented same-membership successor-publication
path as the active lifecycle scope while Yi TPASS and aPPSS are made independent
selectable suites and evaluated under paired profiles. Revisit general
replacement only through a later owner decision after those gates pass.
Alternatives considered: Implement replacement immediately after P4.3, or make
it a prerequisite for CuePolicy generality or selectable recovery suites.
New trust assumptions: None. This decision adds no replacement authority or new
membership-transition trust root.
Privacy implications: None beyond the current same-membership lifecycle. No new
recipient or endpoint-discovery metadata is introduced.
Compatibility/version impact: No format or behavior changes. A later
replacement profile requires new configuration, lifecycle, deployment, and
evidence identifiers and may not reinterpret same-membership evidence.
Required evidence: None for the deferral. Any later implementation requires the
complete old/new authorization, recipient, readiness, activation, retirement,
crash/retry, and mixed-state rejection matrix defined by P4.4 and C12.
Files or components authorized: Planning and active technical documentation may
record the deferral. No general replacement implementation is authorized.
Manuscript implication: None authorized; general replacement remains an
explicit limitation unless a later implementation/evidence gate and separate
manuscript change are approved.

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
Status: Superseded by D018
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
identifiers at P5A.1. Frozen Yi formats, vectors, recovery behavior, and retained
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

### D018 — Selectable recovery suites and paired profiles

Decision ID: D018
Date: 2026-08-03
Status: Approved
Chosen option: Keep frozen Yi TPASS and the new D017 aPPSS construction as
independent, first-class password-protected recovery suites solving the same
LOCUS recovery-secret problem. A user or test profile explicitly selects one
suite when creating a new enrollment or successor epoch. Recovery must use the
single suite authenticated by that epoch's descriptor; it never probes another
suite or silently falls back. A successor may explicitly retain the current
suite or switch in either direction by recovering the protected key client-side
and performing fresh setup under the selected suite. There is no in-place state
conversion or mixed-suite epoch.

Both suites implement one common outer contract:

```text
CuePolicy output -> suite-bound password input -> selected suite -> S_R
-> unchanged HKDF-SHA-256 -> unchanged AES-256-GCM protected-key backup
```

Protected-key generation/import, key-identity checks, encryption, storage,
bootstrap, admission, lifecycle, UI-facing APIs, and common correctness/failure
tests remain suite-neutral. Intrinsic Yi and aPPSS setup, state, message,
threshold-compromise behavior, and `S_R` encodings remain independent and are
not forced into a shared cryptographic construction.

The paired evaluated profiles are `k=2,n=3` first and `k=3,n=5` after threshold
configuration generalization. Yi and aPPSS must run under the same CuePolicy,
synthetic protected keys, holder membership size, reconstruction threshold,
authorization topology/quorum, admission, storage, network/failure schedule,
and measurement definitions within each paired comparison. All valid
reconstruction subsets and the corresponding below-threshold, exact-threshold,
unavailability, wrong-input, crash/retry, and cross-suite cases are required for
both suites. Protocol-specific operations and costs are reported rather than
artificially equalized.

Alternatives considered: Making aPPSS the sole active suite after cutover;
retaining Yi only for legacy recovery; allowing recovery-time automatic
fallback; placing both suites in one epoch; and forcing different internal
constructions to use identical state or message formats.
New trust assumptions: No combined assumption is created. Each selected epoch
inherits only its suite's reviewed assumptions. Explicit selection and paired
testing do not make Yi and aPPSS security properties equivalent.
Privacy implications: The shared below-threshold system boundary is evaluated
under matched conditions, while threshold compromise remains suite-specific:
matching Yi threshold state directly exposes its high-entropy recovery secret;
matching aPPSS threshold state enables offline dictionary testing and yields
`S_R` after a correct guess. Suite selection is public authenticated metadata
and must not depend on or reveal cue values.
Compatibility/version impact: D018 supersedes D007's asymmetric topology plan
and D016's sole-aPPSS active-profile cutover. D017's exact aPPSS primitives and
first `2-of-3` order remain approved. Frozen Yi identifiers, vector, behavior,
backup/deployment profiles, and retained v2 evidence remain immutable. aPPSS
receives new formats and identifiers. New selectable, `3-of-5`, deployment, and
evidence profiles receive their own identifiers where their semantics change.
One epoch continues to bind exactly one suite.
Required evidence: One suite-neutral conformance harness consumed independently
by Yi and aPPSS; paired `2-of-3` and `3-of-5` correctness, subset, availability,
wrong-input, restart, crash/retry, and performance runs; exact common-input and
topology manifests; strict suite-selection and no-fallback tests; same-suite and
bidirectional cross-suite successor tests; separate below-threshold and
threshold-compromise matrices; frozen Yi regression; clean Linux/Windows
reproduction; and independent aPPSS mapping review. Evidence remains separated
by suite and profile even when a comparison processor consumes matched rows.
Files or components authorized: Suite selector and registry, common conformance
interfaces, independent Yi/aPPSS adapters and native cores, paired topology
profiles, successor-selection flow, UI/API selection field, tests, active
technical documentation, and new evidence paths after their chronological
gates. No modification or reinterpretation of the frozen Yi core or formats is
authorized.
Manuscript implication: None authorized. M-APPPSS-001's sole-active-aPPSS
wording is stale under D018 and must be superseded by a separately presented
exact manuscript change set before any file under `paper/` changes.

### D019 — Claim-focused recovery-suite mapping review

Decision ID: D019
Date: 2026-08-03
Status: Approved
Chosen option: Replace P5A.7's aPPSS-only independent cryptographic-audit
wording with an independent, claim-focused construction and security-mapping
review covering both frozen Yi TPASS and D017 aPPSS. The review determines
whether each implementation preserves the source construction semantics and
assumptions needed for the exact LOCUS security statements, and whether the
outer LOCUS composition introduces a prohibited local cue-testing predicate.
It does not certify the primitives as new LOCUS constructions or audit the
whole system for production use.

The review permits documented engineering latitude in canonical wire formats,
service APIs, transport envelopes, storage layouts, identifiers, transcript
framing, and generic error handling when those choices do not alter the
construction's algebra, secret/state boundary, threshold meaning, corruption
model, or candidate-testing behavior. It requires independent acceptance of
all claim-critical mappings: Yi's Protocol 2 equations and proof assumption;
Yi's Ristretto255/hash/`G2` instantiation choices; aPPSS Figure 4 threshold
translation, OPRF, field, sharing, mask, commitment, and secret derivation;
both suites' below-threshold persistent-state boundary; their distinct
reconstruction-threshold compromise behavior; and the common
`S_R -> HKDF-SHA-256 -> AES-256-GCM` composition without fallback or a stored
verifier.

An unresolved claim-critical deviation has only two acceptable outcomes: fix
the implementation and re-review it, or stop attributing the affected behavior
to the source construction/result and remove the dependent LOCUS claim. Tests
and fixed vectors remain implementation evidence, not a substitute for this
mapping judgment.
Alternatives considered: Retaining an aPPSS-only review; requiring a full
production cryptographic/security audit of all LOCUS code; accepting the
implementation based only on regression tests; or allowing approximate
claim-critical mappings while continuing to inherit the source results.
New trust assumptions: None. The review makes the already inherited Yi and
aPPSS assumptions explicit and separate; it does not strengthen either proof
or create a combined theorem.
Privacy implications: The reviewer must verify only the claim-relevant state
and information-flow boundaries. No real cues, credentials, private keys, or
secret-bearing traces are supplied. Review records remain attributable but may
use an owner-held identity reference for public privacy.
Compatibility/version impact: No protocol identifier, wire format, vector,
state, or retained evidence changes. D019 supersedes only the review-scope
wording in D016--D018 and P5A.7. The frozen Yi and assigned aPPSS profiles
remain unchanged.
Required evidence: An exact-commit review of both paper-to-specification-to-code
mappings; a completed deviations register; explicit answers for the two
below-threshold mappings, both threshold-compromise outcomes, and the outer
composition; classification and resolution of claim-critical findings; and an
attributable final disposition. Clean-host tests and P8/P9 suite-separated
evidence remain separate gates.
Files or components authorized: Review packet, deviations register, planning,
claim/evidence, release-readiness, mapping, and technical-documentation updates.
No frozen Yi implementation change, aPPSS semantic change, retained-evidence
reinterpretation, or manuscript edit is authorized by this decision.
Manuscript implication: None authorized. M-SELECTABLE-SUITES-001 may cite the
completed mapping review as a basis only after P8/P9 and a separate exact owner
approval.

### D020 — Provisional internal review and deferred human validation

Decision ID: D020
Date: 2026-08-03
Status: Approved
Chosen option: At the owner's request, Codex may perform and record a rigorous
paper-to-specification-to-code mapping assessment for frozen Yi TPASS, D017
aPPSS, and the LOCUS outer composition. Because Codex contributed to the
implementation and documentation, this assessment is explicitly internal and
non-independent. If it finds no unresolved claim-blocking or
correction-required issue, P5A.7 may be marked complete for implementation
chronology, the existing explicit selectable-suite application interface may
be activated, and work may continue to P6. Independent human cryptographic
validation remains mandatory before the project describes the mapping as
independently reviewed, relies on it in manuscript wording, promotes the
comparative result as paper evidence, or makes a final reviewed release or
submission.
Alternatives considered: Stop all work until an external reviewer is
available; treat Codex as an independent reviewer; remove the review gate; or
continue to P6 without recording the assessment and residual validation debt.
New trust assumptions: None for either recovery construction. This decision
changes project sequencing and assurance labeling only. It does not strengthen
the Yi or aPPSS source results, convert tests into proofs, or broaden the
persistent-state adversary model.
Privacy implications: The internal assessment uses repository-controlled
source, public specifications, the owner-supplied aPPSS paper, synthetic
fixtures, and aggregate-only tests. It requires no real cue, credential,
private key, account, or production service state.
Compatibility/version impact: No cryptographic identifier, wire format,
threshold, state, vector, backup, descriptor, retained evidence, or frozen Yi
behavior changes. The P5A.5 selectable-suite application interface becomes an
active post-baseline component. Exact paired deployment identifiers and
profiles remain assigned chronologically in P6.3; the frozen Yi-only Compose
deployment and retained v2 evidence are not reinterpreted.
Required evidence: An attributable internal assessment bound to an exact
reviewed commit and source sections; a provisionally completed deviations
register; explicit dispositions for Yi, aPPSS, and the LOCUS composition; no
open claim-blocking or correction-required finding; the complete regression
gate after documentation/activation; and a clearly recorded human-validation
checklist that remains open.
Files or components authorized: Review/deviation/readiness records, planning,
baseline, protocol, architecture, information-flow, lifecycle, API, storage,
evidence, artifact, version, and project-instruction documentation; tests and
the existing explicit selectable-suite application boundary. No semantic
change to either cryptographic core and no retained P9 collection are
authorized.
Manuscript implication: None authorized. The internal assessment must not be
cited as independent review. Any selectable-suite manuscript delta still
requires P8/P9, independent human validation, and a separate exact owner
approval before `paper/` changes.

### D021 — P6 paired topology and honest deployment tier

Decision ID: D021

Date: 2026-08-03

Status: Approved

Chosen option: Implement P6 chronologically with matched Yi and aPPSS
deployment profiles at recovery thresholds 2-of-3 and 3-of-5. Both topologies
use five authorizers and a separately represented 4-of-5 authorization quorum;
the quorum is never inferred from or conflated with the recovery threshold.
Within each topology the two suites use the same CuePolicy, synthetic protected
key, authorization membership, storage, admission boundary, network schedule,
and measurement definitions. For P6.4, demonstrate the highest honest tier
available locally, targeting separate local VMs; do not label same-host,
separate-process, or one-operator infrastructure as independent administration.

Alternatives considered: Retain only the frozen Yi 2-of-3 deployment; compare
the suites under unmatched thresholds or authorization conditions; change the
authorization quorum with the recovery suite; require a live provider or
independent operators before local work; or simulate independent
administration.

New trust assumptions: The paired local profiles continue to trust one test
operator and host/virtualization control plane. A local VM boundary strengthens
host separation testing but is not administrative independence. Tier 2 and
Tier 3 claims require actual network hosts and operators respectively.

Privacy implications: Only synthetic protected keys, cues, identities, and
credentials are permitted. Paired profiles expose the same pseudonymous
subject/backup/epoch/topology metadata to the same logical roles. No profile
may add a cue, candidate, verifier, recovery secret, provider credential, or
other secret-bearing value to ordinary output or shared configuration.

Compatibility/version impact: Frozen `LOCUS-compose-deployment-v2` and its
retained v2 evidence remain unchanged. P6.3 must assign new exact deployment
identifiers for the four suite/topology combinations and must not convert,
reinterpret, or mix suite state. The 3-of-5 suite profiles require new
configuration identities while preserving each suite's existing cryptographic
format and password domain.

Required evidence: Common P6.1 storage conformance; locally reproducible P6.2
gateway/provider tests; end-to-end positive, subset, unavailable, mixed-suite,
and wrong-profile tests for all four P6.3 profiles; resolved topology and
output/credential scans; and exact P6.4 tier documentation. A live AWS run is
optional and separately execution-authorized. Tier 2/3 results remain external
gates unless actual infrastructure is supplied.

Files or components authorized: Provider-level storage composition and tests;
the application storage gateway and optional AWS profile; new paired
deployment configuration, schemas, vectors, tasks, tests, and documentation;
and local-VM orchestration and validation if the host supports it. No real
account, personal data, production credential, general replacement, external
witness, retained P9 corpus, or manuscript edit is authorized.

Manuscript implication: None authorized. Any paired-suite, provider, or host-
separation wording still requires its exact later evidence and a separate
owner-approved manuscript delta.

### D022 — P7 local research UI runtime

Decision ID: D022

Date: 2026-08-03

Status: Approved

Chosen option: After the P7.1 API freeze, implement the cross-platform research
UI as standards-based semantic HTML, CSS, and JavaScript served on loopback by
Python's pinned standard-library HTTP runtime. The UI calls only
`LOCUS-client-api-v1`; it contains no CuePolicy canonicalizer, suite adapter,
descriptor validator, admission implementation, or lifecycle mechanism. No
third-party web package, remote asset, analytics service, or automatic update
channel is added.

Alternatives considered: Electron or another bundled browser runtime; a native
desktop toolkit; a third-party Python or JavaScript web framework; a hosted
site; or delaying all interface testing until multi-host infrastructure exists.

New trust assumptions: The local browser document and loopback UI server are
inside the active-client boundary. The operating system, browser process,
extensions, download manager, screenshot tooling, crash collector, and host
administrator remain trusted and outside the bounded UI controls.

Privacy implications: Every response is no-store and same-origin; the UI uses
no cookies, browser storage, telemetry, remote fonts/assets, or console
logging. Request logging is disabled. Copy/cut and printing are disabled as
best-effort accidental-disclosure controls, not secure-erasure or screenshot
prevention. Structured-input preview is transient active-client data and is
cleared after use. Only the explicitly exported public recovery receipt is
downloaded.

Compatibility/version impact: `LOCUS-local-research-ui-v1` binds the exact
route, asset, persistence, and presentation boundary to `LOCUS-client-api-v1`.
It cannot alter protocol bytes. A hosted origin, third-party runtime, browser
persistence, changed API contract, or secret-export behavior requires a new UI
profile and review.

Required evidence: Strict route/body/content-type tests; security-header and
loopback-only tests; source scans for persistence, telemetry, dynamic HTML,
remote assets, and console output; exact synthetic enrollment/recovery/
successor/inspection tests; public-output scans; and browser interaction plus
desktop/mobile visual inspection. These checks are implementation evidence,
not human usability evidence.

Files or components authorized: Local UI server, static assets, tests, task
runner entry point, public UI/API documentation, and version-registry entries.
No external service, real account, production key, retained P9 result, hosted
deployment, or manuscript edit is authorized.

Manuscript implication: None authorized. A working UI does not establish
usability, memorability, accessibility conformance, production security, or
paper-facing evidence.

### D023 — Primary integrated reference system and evidence target

Decision ID: D023

Date: 2026-08-04

Status: Approved

Chosen option: Before P8, construct one new, separately versioned primary
reference system in which the unchanged thin P7 UI and `LOCUS-client-api-v1`
are served from an ephemeral active-client container and the API is backed by
authenticated remote-service adapters rather than the current same-process
record model. One reproducible same-host Docker Compose graph contains the
local synthetic admission/capability service, operator/discovery and signing
service, application storage gateway, local S3-compatible object store,
resolver service, and five authenticated authorizer/recovery-party services.
The browser remains outside Docker and reaches only a host-loopback UI
endpoint. An operator command, never browser code, creates and validates the
disposable deployment.

The active path must use authenticated enrollment transport and service APIs;
no networkless provisioner may inject recovery-suite state or secret-bearing
client state into runtime volumes. A bounded networkless bootstrap role may
create service credentials, public configuration, empty role volumes, and
synthetic fixtures only. Clean-client evaluation destroys or makes Client A's
container/root/identity inaccessible and starts Client B from the same
immutable client image with fresh client proof and transport identities,
installed trust, the public receipt, and fictional recovery input only.

The integrated family exposes the four matched suite/topology arms—Yi and
aPPSS at 2-of-3 and 3-of-5—with five authorizers and a separate 4-of-5
authorization quorum. It supports the four registered CuePolicies, exact
descriptor/bundle/current-pointer bootstrap, same-suite and cross-suite
successors, and explicit optional protected-key rotation. The reproducible
cloud-storage role is the local S3-compatible provider under D015; optional
AWS S3 and actual multi-host executions remain separately authorized,
separately identified supplemental profiles. “Cloud services” does not mean
Apple iCloud or a personal provider account.

The new integrated deployment is the mandatory system-under-test for central
P8 security/reliability/information-flow assurance, P9 performance/resilience
evaluation, P10 artifact reproduction, and any later proposed system result in
the manuscript. Native vectors, unit tests, component tests, the P7 same-process
UI, P6 process controls, and frozen v2 results remain necessary supporting or
historical controls, but none substitutes for integrated-system evidence.

Alternatives considered: Perform P8/P9 over the disconnected UI and component
profiles and integrate afterward; modify or reinterpret frozen
`LOCUS-compose-deployment-v2`; let the browser contact parties or S3 directly;
make a personal cloud account or AWS credentials mandatory; or treat several
component harnesses as equivalent to one end-to-end system.

New trust assumptions: The reproducible profile trusts one operator, host,
Docker engine, build/provisioning boundary, application installation trust
root, and local synthetic admission issuer. The browser, operating system, and
ephemeral client container are inside the active-client boundary. Container
separation does not establish host separation, independent administration,
production PKI, or resistance to a malicious Docker administrator.

Privacy implications: Only the active client may transiently receive the
complete cue-to-protected-key path. Each service receives only its approved
role view. The UI and every service must disable secret-bearing logs, telemetry,
browser persistence, crash output, and retained payload traces. The operator,
admission service, parties, resolver, storage gateway, and provider still
observe their documented pseudonymous identifiers, message categories,
timing, sizes, endpoints, and access metadata. P8 must measure these views
through privacy-safe structured instrumentation and aggregate state audits.

Compatibility/version impact: Frozen `LOCUS-compose-deployment-v2`, its
retained v2 evidence, the P6.3 comparison-control profiles, P6.4 endpoint
setup, `LOCUS-client-api-v1`, and `LOCUS-local-research-ui-v1` retain their
exact meanings. P7.5 work package 1 assigns a new integrated
deployment/configuration profile only together with a strict
service/topology/role-state manifest, validation rules, compatibility
statement, and tests. Changed topology, provider, admission adapter, UI/API
semantics, role placement, or measurement boundary requires a distinct profile
and evidence path.

Required evidence: Exact resolved/live Compose-graph validation; role-specific
identity, certificate, network, mount, environment, and persistent-state
audits; complete UI-to-service enrollment, clean bootstrap/recovery, and
successor flows for all four suite/topology arms; registered-policy coverage;
correct, wrong-input, below-threshold, unavailable-party, restart, crash,
replay, cross-suite, downgrade, stale-pointer, and storage-failure scenarios;
Client A/Client B isolation with a positive control; prohibited-output scans;
privacy-safe network-role observations; deterministic cleanup; clean-host
reproduction; and P9 methodology/results bound to the exact integrated
manifest. Tests remain implementation behavior, not cryptographic proof,
human usability, host independence, production readiness, or audit.

Files or components authorized: P7.5 planning and architecture records; a new
Compose graph and strict deployment manifest/schema; container-backed client,
admission, discovery/operator, storage-gateway, resolver, party, and provider
service adapters; task-runner start/smoke/cleanup commands; generated synthetic
credentials and fixtures; system tests; and later new P8/P9/P10 profiles after
their chronological gates. No real account, personal data, production key,
general party replacement, external monotonic witness, retained result
collection before P9.2, or manuscript edit is authorized.

Manuscript implication: None authorized now. After the integrated system,
suite mapping review, P8/P9 evidence, clean-host artifact reproduction, and
claim matrix close, P10.5 must present exact proposed manuscript deltas. Any
approved result must identify this integrated deployment and its exact
suite/topology/policy/provider scenario; historical v2 or component results
remain explicitly scoped and cannot be relabeled.

### D024 — Final prototype source and command boundary

Decision ID: D024

Date: 2026-08-10

Status: Approved

Chosen option: Create `prototype_final/` as a self-contained copy of the exact
D023 integrated implementation and make it the only active implementation
workspace for P8 and later implementation, assurance, evidence, and artifact
work. It contains the dependency-complete Python package, both native recovery
cores and their narrow binding, pinned environment, integrated Compose graph
and manifest, thin UI assets, focused integrated tests, licenses, README, and a
small executor exposing only `integrated-check`, `integrated-config`,
`integrated-start`, `integrated-stop`, and `integrated-smoke`. Existing root
source, commands, tests, deployments, and evidence remain in place as frozen,
historical, or component controls; they are not moved, deleted, or silently
used as the P8+ system under test.

Alternatives considered: Continue using the root multi-profile task runner;
delete historical/component implementations; make the P7 in-memory UI or
frozen Yi Compose profile the active artifact; or let the new executor call
back into root source and tooling.

New trust assumptions: None. The isolated workspace preserves the D023
same-host, one-operator, synthetic-service trust model and does not add host
separation, independent administration, production PKI, real-provider trust,
or a new cryptographic assumption.

Privacy implications: The copied implementation retains the existing
active-client, role-state, output-safety, no-real-data, and exact-cleanup
boundaries. The reduced workspace must not copy retained raw evidence,
credentials, generated role state, logs, databases, caches, build products, or
manuscript material.

Compatibility/version impact: A byte- and semantics-preserving source-layout
isolation does not rename `LOCUS-integrated-reference-deployment-v1`,
`LOCUS-integrated-reference-config-v1`, `LOCUS-client-api-v1`, or any protocol
format. The new workspace and executor are implementation/artifact-source
boundaries, not a protocol migration. Any later change to the manifest,
topology, provider, admission adapter, UI/API meaning, role placement, or
measurement boundary still requires the new profile/version mandated by D023.

Required evidence: The new workspace must pass its focused unit/native quality
gate, validate both resolved Compose profiles, reproduce the complete
integrated smoke independently of root Python source, scan output/state, and
remove its exact Docker resources. P8/P9 retained evidence must bind the
`prototype_final/` source state and may not execute through the legacy root
task runner.

Files or components authorized: New `prototype_final/` source, native crates,
tests, deployment assets, environment/lock files, executor, README, licenses,
and necessary project governance/documentation updates. Existing source and
evidence may be copied but not moved, deleted, overwritten, or reinterpreted.

Manuscript implication: None authorized. The current manuscript remains bound
to the frozen evaluated profile. A future approved manuscript delta may
describe `prototype_final/` only after P8/P9, independent human validation,
artifact reproduction, claim closure, and the separate P10 owner gate.

### D025 — Manager-controlled integrated deployment and transient client workflow

Decision ID: D025

Date: 2026-08-11

Status: Approved

Chosen option: Replace the active D024 deployment's CLI-selected enrollment and
recovery clients with one `integrated-start` entry point that starts the common
service plane, a loopback-only Manager UI, and a separate internal lifecycle
controller. The Manager creates, starts, stops, restarts, kills, and destroys
transient Client UI containers from one fixed image and exact project-scoped
template. Each client receives a fresh in-memory proof key and displays its
public client-instance identifier under the assigned managed-client-instance
profile. The same Client UI exposes key generation, enrollment, client
recovery-package export, authenticated package import, recovery, key
replacement, and self-destruction. The existing Yi/aPPSS, CuePolicy,
admission, 4-of-5 authorization, storage-gateway/local-provider, descriptor,
and party protocols remain the implementation underneath those workflows.

The Manager UI has no Docker socket. A separate controller receives the local
Docker socket and has no host-published endpoint. It accepts authenticated
Manager requests only on `management` and authenticated Client self-lifecycle
requests only on `client-lifecycle`, validates exact project labels and fixed
container templates, and never accepts caller-supplied images, commands,
mounts, networks, or host paths. Docker-socket access is nevertheless
root-equivalent control of the local Docker engine; this is an explicit
same-host research/operator trust assumption and not a production control
plane.

The controller is the only bridge between two disjoint lifecycle networks.
`management` carries only authenticated Manager-to-controller status and
operator lifecycle requests. `client-lifecycle` carries only an authenticated
managed Client's narrowly scoped request concerning its own exact instance,
including self-destruction. A managed Client is not attached to `management`
and cannot reach the Manager UI/API; the Manager is not attached to
`client-lifecycle`. Neither network carries LOCUS cue, suite, backup, or party
protocol traffic.

Browser publication also uses distinct networks. `manager-edge` is attached
only to the Manager and carries its host-loopback-published UI path;
`browser-edge` is attached only to dynamic Clients and carries their separately
published loopback UI paths. Neither is a Manager-to-Client network, and a
managed Client never joins or directly reaches `manager-edge`.

The Client UI may show a generated or recovered synthetic private key only as
a transient active-client response. It must not log, persist, place in browser
storage, or include that key in an exported artifact. Client destruction
removes the container and its memory. It is bounded state disposal, not
forensic erasure. The browser remains part of the active-client boundary, so
screen capture and a malicious local browser environment remain limitations.

Client process actions have deliberately destructive volatile-state semantics.
`stop` and `kill` make the Client endpoint unavailable but retain its container
and public client-instance identifier. A later `start`, and every `restart`,
starts with a fresh proof identity and empty server-side key slot, export/import
cache, and operation/session set under that same public client-instance
identifier. `destroy` removes the container
and identifier; a later `create` produces a distinct identifier. These actions
are not session continuity or forensic erasure and must be labeled accordingly
in the Manager UI. A document already loaded in the external browser can remain
rendered until it is closed or reloaded.

The downloadable `LOCUS-client-recovery-package-v1` contains the encrypted
backup and authenticated public recovery metadata needed to bind an import to
the existing remote epoch. It contains no raw cue, private key, password,
recovery secret, wrapping key, provider credential, or party state. Importing
the package does not replace the threshold parties, current-pointer checks,
discovery, admission, authorization, or local S3-compatible storage path. A
real external cloud provider remains out of scope.

Every imported package and all metadata it carries are untrusted until bounded
canonical decoding, exact length and digest checks, operator-signature
validation, current-pointer/discovery authentication, and the required current-
party quorum succeed. The Client UI may display an explicitly marked untrusted
summary before that gate, but it must not use unauthenticated package fields to
select a suite, CuePolicy, holder membership, threshold, endpoint, or fallback.
Missing or unsupported authenticated configuration fails closed rather than
becoming a manual recovery-time override.

The UI exposes only the already approved paired profiles: 2-of-3 holders
`1,2,3` and 3-of-5 holders `1,2,3,4,5`, with the separate 4-of-5 authorizer
quorum. It may let the recovering client choose a valid threshold subset of
the descriptor-declared holders. It does not create arbitrary `k,n`, change
membership, reinterpret a suite profile, or permit recovery-time suite or
policy override.

Alternatives considered: Continue requiring CLI enrollment/recovery modes;
mount the Docker socket directly into the browser-facing Manager UI; permit
arbitrary container specifications or arbitrary holder memberships; remove
the storage/provider and descriptor path in favor of a downloaded ciphertext
alone; or return the private key through the frozen v1 client API/UI.

New trust assumptions: The local operator trusts the narrow lifecycle
controller and Docker engine. All managed clients share the deployment's
synthetic transport-client identity but receive distinct proof keys bound into
admission capabilities; this is not independent client administration or
production device identity. Manager access is loopback-only and intended for a
single local research operator.

The managed bootstrap credentials are bounded research credentials, not a
production PKI: the generated CA is valid for 366 days and role TLS
certificates for 365 days. Normal Manager stop and emergency CLI cleanup
without state reset preserve the exact-project volumes and credentials. There
is no in-place renewal. Expired or manifest-incompatible state fails closed;
the explicit emergency `integrated-stop --reset-state` path removes all exact-
project role/provider volumes so the next start creates a new trust domain and
empty protocol state. Reset therefore also destroys local recoverability for
prior exported packages whose party/provider epoch state existed only there.

The one-shot bootstrap runs as root with every Linux capability dropped except
exactly `CHOWN` and `DAC_READ_SEARCH`, uses `network_mode: none`, receives no
Docker socket, and exits before the unprivileged runtime roles start. The two
capabilities are limited to creating and revalidating owner-only per-role files;
they do not authorize runtime networking or secret-bearing protocol state.

Privacy implications: The private key is intentionally visible inside the
active browser/client boundary and therefore susceptible to screen capture or
a compromised browser. It remains prohibited from logs, durable client state,
manager/controller messages, and the client recovery package. Manager status is
limited to public container/client identifiers, health, ports, and lifecycle
state. Docker inspection data and environment values must not be returned to
the browser.

Compatibility/version impact: Do not reinterpret
`LOCUS-integrated-reference-deployment-v1`,
`LOCUS-integrated-reference-config-v1`, `LOCUS-client-api-v1`, or
`LOCUS-local-research-ui-v1`. D025 approved the exact names
`LOCUS-integrated-manager-deployment-v1`,
`LOCUS-integrated-manager-config-v1`, `LOCUS-manager-api-v1`,
`LOCUS-local-manager-ui-v1`, `LOCUS-container-controller-api-v1`,
`LOCUS-local-container-controller-v1`, `LOCUS-client-api-v2`,
`LOCUS-managed-client-ui-v1`, `LOCUS-client-recovery-package-v1`,
`LOCUS-clean-client-isolation-v2`, `LOCUS-managed-client-instance-v1`, and
`LOCUS-security-matrix-v2`. P7.7 reviewed each strict manifest or schema,
compatibility rule, canonical vector, negative tests, and first implementation
together and assigned all twelve identifiers. They are `Assigned`, not
`Frozen`; frozen suite, backup, CuePolicy, admission, descriptor, and evidence
identifiers retain their meanings.

Required implementation gate: Before P8, freeze the expanded security contract without
changing the C01--C26 meanings; validate the exact managed graph; demonstrate
that startup creates no Client UI container; exercise Manager lifecycle
allowlists and rejection paths; complete enrollment, package download, client
destruction, fresh-client import/recovery/key replacement, and fresh client-ID
checks for both suites, both paired topologies, and all four registered
CuePolicies; verify exact threshold-subset and 4-of-5 behavior; preserve wrong-
input, unavailability, restart, replay, stale-pointer, downgrade, storage-
failure, and successor-core compatibility coverage; scan output and role/client
state; validate Manager/client edge separation, destructive volatile process
resets, credential reuse/expiry rejection, and explicit full-state reset; and
stop/clean the exact disposable project. These are implementation
observations only until later P8 schemas and retained collection gates pass.

P7.7 acceptance record (2026-08-11): The enhanced disposable smoke passed all
four suite/topology arms, 26 threshold subsets, four isolated clean Clients,
live control isolation and lifecycle actions, prohibited-output scans, 15 plus
15 role audits, normal stop/restart recovery with the same CA, destructive reset
with a fresh CA and old-package rejection, and exact cleanup. After the final
focused controller/bootstrap fixes, the full integrated check, 27 focused
tests, formatting, linting, typing, configuration validation, and final browser
acceptance passed. This assigns the managed profiles and closes
P7.7, but creates no retained P8/P9 evidence and authorizes no manuscript edit.

Files or components authorized: `prototype_final/` task runner, manifest and
schema, Compose/Docker assets, bootstrap roles, lifecycle controller, Manager
UI, managed Client UI/API, client recovery-package codec/schema, focused tests,
smoke workflow, and corresponding project/architecture/evidence/artifact
documentation. Historical root implementations remain unchanged controls.

The managed Client API/UI need not expose successor enrollment. The existing
successor core and its same-/cross-suite crash-resumable behavior remain
unchanged compatibility controls outside this Manager/Client UX.

Manuscript implication: None authorized. The new Manager/Client workflow,
private-key visibility, Docker-controller assumption, package transport, and
results may be described in the manuscript only through a later exact owner-
approved delta after independent validation, P8/P9 evidence, artifact
reproduction, and claim closure.

### D026 — Managed aggregate-only state-evidence contract

Decision ID: D026

Date: 2026-08-17

Status: Approved

Chosen option: Assign the exact P8.2 managed state-evidence family proposed to
the owner on 2026-08-14 and approved verbatim on 2026-08-17. The profile uses
the identifiers `LOCUS-managed-state-evidence-profile-v1`,
`LOCUS-managed-state-scenario-manifest-v1`,
`LOCUS-managed-state-result-common-v1`,
`LOCUS-managed-state-result-yi-v1`,
`LOCUS-managed-state-result-appss-v1`, and
`LOCUS-managed-state-corpus-manifest-v1`. Its immutable manifest contains
exactly 42 reports: 18 Yi, 18 aPPSS, and six suite-neutral managed-system
reports over SB01--SB14. Paired 2-of-3 suites use the canonical-email policy;
paired 3-of-5 suites use the location-person policy under otherwise matched
synthetic conditions. Retained publication is aggregate-only, exclusive,
all-or-nothing, clean-commit-bound, and append-only.

Alternatives considered: Reusing frozen v1/v2 evidence; pooling Yi and aPPSS;
using the P7.7 smoke output as retained evidence without a schema; retaining
raw snapshots, databases, logs, packet captures, candidates, or secret-state
digests; collecting before a clean contract commit; or waiting for P9.2 and
mixing state/security with performance schemas.

New trust assumptions: The evidence profile trusts the exact D025 same-host
single-operator Docker/Manager/controller boundary, clean source commit,
networkless read-only audit containers, local synthetic issuer, and local
S3-compatible provider. It adds no independent-administration, multi-host,
real-provider, production-PKI, endpoint-compromise, or monotonic-witness
assumption.

Privacy implications: Retained fields are limited to approved identifiers,
counts, Booleans, bounded categories, public/configuration digests,
pseudonymous provenance, exact role membership, file counts/byte totals, and
positive-control/output/cleanup status. Raw/canonical cues, candidates and
per-candidate results, suite secrets, shares, keys, credentials, certificates,
databases, snapshots, logs, traces, screenshots, absolute paths, developer
identity, free-form diagnostics, and content digests of secret-bearing state
are prohibited.

Compatibility/version impact: The six identifiers are Assigned with their
schemas, compatibility rules, fixed scenario manifest, tests, and first
implementation. Yi, aPPSS, and common reports remain separate. The retained
path is `prototype_final/evidence/retained/managed-state-v1/`; an existing path
is never overwritten. Any changed scenario membership, retained field,
deployment/provider/admission/UI/API boundary, topology, policy, suite, or
publication rule requires a new version. Frozen v1/v2 and D023/P7.7 outputs are
not reinterpreted.

Required evidence: The committed collector must run the exact Manager-created
Client graph with all four matched arms, validate 15 role volumes at the fixed
snapshot points, pass every ordinary and positive-control observation, retain
exactly 42 schema-valid reports plus a hash-closing corpus manifest, scan and
discard logs, and prove exact-project cleanup. Retained collection may occur
only from the clean contract implementation commit.

Files or components authorized: `prototype_final/` evidence profile, fixed
scenario manifest, schemas, state-audit aggregation, collector, tests, the new
`integrated-state-evidence` command, append-only retained corpus, and the
project governance/registry/status documentation needed for P8.2. No P8.3
trace collection, P9 metric schema, external provider, real data, general
replacement, monotonic witness, or manuscript edit is authorized.

Manuscript implication: None authorized. The P8.2 corpus remains
implementation evidence subject to D019 independent review, later P8/P9 and
artifact gates, claim closure, and a separately presented exact manuscript
delta.

### D027 — Managed privacy-safe flow-evidence contract

Decision ID: D027

Date: 2026-08-17

Status: Approved

Chosen option: Assign the exact P8.3 contract presented to and approved
verbatim by the owner on 2026-08-17. The assigned identifiers are
`LOCUS-managed-flow-evidence-profile-v1`,
`LOCUS-managed-flow-trace-policy-v1`,
`LOCUS-managed-flow-scenario-manifest-v1`,
`LOCUS-managed-flow-result-common-v1`,
`LOCUS-managed-flow-result-yi-v1`,
`LOCUS-managed-flow-result-appss-v1`, and
`LOCUS-managed-flow-corpus-manifest-v1`. The immutable corpus contains exactly
30 reports: 12 Yi, 12 aPPSS, and six suite-neutral common reports over
NF01--NF12. The four suite/topology/policy arms remain exactly matched to
D026/P8.2.

Instrumentation boundary: Fixed payload-free observation is attached only to
the synthetic browser driver and Manager/Client route adapters, authenticated
RPC callers and servers, the storage-gateway logical provider adapter, and the
constrained Docker Engine adapter. It creates no service, network, volume,
socket, mount, endpoint, or protocol route. Authenticated HTTP observations
reconcile sender and receiver; browser, S3, and Docker boundaries use their
fixed available observation point. Packet capture is prohibited.

Retained fields: Sender/receiver role, registered message category, request
count, request/response application-body byte totals, bounded success/rejection
counts, reconciliation status, fixed expected-absence/positive-control status,
public configuration/provenance digests, pseudonymous project/host/client/
package-set bindings, output scan, cleanup, and fixed limitations only. No
timing field is a P8.3 metric.

Unexpected-contact rule: An unknown role, edge, or category; a scenario-
forbidden category; Client-to-Manager, Manager-to-Client-container, UI-to-
Docker, Client-to-S3, or browser-to-service contact; resolver contact under a
NoResolver policy; missing/mismatched paired observation; malformed event
sequence; prohibited output; incomplete cleanup; or incomplete corpus fails
the entire run without publication.

Positive controls: Every scenario must observe its required allowed edge.
Tests and the live run detect unknown edges/categories, sequence gaps, byte-
bound violations, sender/receiver mismatches, fabricated resolver contact,
and fictional prohibited markers. Allowed Manager/controller and Client/
controller contacts succeed while prohibited network/socket probes remain
blocked. Raw structured events and service logs are scanned and discarded.

Compatibility/version impact: The seven identifiers are Assigned with strict
schemas, fixed category/edge/scenario manifests, tests, and first
implementation. The exclusive retained path is
`prototype_final/evidence/retained/managed-flow-v1/`. Publication is clean-
commit-bound, append-only, all-or-nothing, and atomic. Any changed role, edge,
category, scenario, byte meaning, instrumentation point, deployment/provider/
admission/UI/API boundary, topology, policy, suite, retained field, or
publication rule requires a new version. Frozen trace-policy v1, D023, P7.7,
and P8.2 outputs retain their meanings and cannot be pooled or reinterpreted.

Files or components authorized: `prototype_final/` flow instrumentation,
policy/scenario manifests, schemas, collector, tests, an additive
`integrated-flow-evidence` command, append-only retained corpus, and the
governance/registry/status documentation needed for P8.3. Two P8.3 commits are
required: the clean contract/collector commit first, then retained corpus and
completion documentation. No P9 metric/result family, packet capture, external
provider, real data, new runtime role, protocol/API expansion, or manuscript
edit is authorized.

Manuscript implication: None authorized. The result remains same-host single-
operator implementation evidence subject to D019, P9, artifact reproduction,
claim closure, and a separately approved exact manuscript delta.

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

Approval of D001--D025 authorizes only the recorded architecture or
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
Owner status: Superseded by D018 before any manuscript edit
Implementation/evidence commit: Pending P5A and P8/P9
Applied commit:
Rendered PDF SHA-256:

### M-SELECTABLE-SUITES-001 — Selectable Yi/aPPSS construction and comparison

Change-set ID: M-SELECTABLE-SUITES-001
Date proposed: 2026-08-03
Exact file and sections: `paper/main.tex` abstract; Introduction; Problem
Setting and Threat Model; LOCUS Requirements; Protocol Construction, including
Notation, Cue-Derived Recovery Password, recovery-suite interface, Recovery
Secret and Key Wrapping, Backup Object and Recovery-Party Records, Backup
Phase, Recovery Phase, and State Separation; Implementation; Evaluation;
Security Analysis; Lifecycle and Recovery State Management; Limitations;
Related Work; Conclusion; Open Science; and the cryptographic appendix. Add the
aPPSS source record to `paper/references.bib`. No title change is proposed.
Before/after summary: Replace the stale sole-active-aPPSS proposal with two
independent, explicitly selectable recovery suites. One enrollment or epoch
authenticates exactly one suite; recovery dispatches only to that suite and
never probes or falls back to the other. Frozen Yi and D017 aPPSS both produce
the high-entropy LOCUS recovery secret consumed by the unchanged
HKDF-SHA-256/AES-256-GCM path. Describe same-suite and bidirectional
cross-suite successor creation as fresh setup, not state conversion. Compare
the suites only under matched 2-of-3 and, after P6.3, 3-of-5 conditions.
Separate the below-threshold no-local-predicate boundary from the distinct
threshold-compromise outcomes: matching Yi threshold state reconstructs its
shared input and protected recovery secret without a dictionary search, while
matching aPPSS threshold state plus public `omega` enables unrate-limited
offline dictionary testing and yields `S_R` for a correct candidate.
Claim and evidence basis: D017--D020; the Section 3/Figure 4 aPPSS construction
and Theorem 2 from *Password-Protected Threshold Signatures*; the frozen Yi
construction; the exact reviewed paper-to-code mappings; suite-neutral
conformance, selection/no-fallback, successor, and common-condition tests; new
suite-separated P8/P9 retained evidence; and clean Linux/Windows reproduction.
The underlying cryptographic constructions and results remain inherited. The
current P5A.6 comparator is development regression only and cannot support a
paper result by itself.
Limitations affected: Keep the suites' assumptions separate; record the
random-oracle, OPRF, authenticated-initialization, threshold-notation, and
abort-only aPPSS assumptions; retain Yi proof/instantiation limitations; state
that threshold aPPSS compromise gives an unrate-limited offline dictionary
attack whose residual protection depends on the conditional cue distribution;
make no proactive/adaptive, side-channel, production-security, memorability,
usability, independent-administration, or global attempt-bound claim; and do
not reuse retained v2 Yi results for aPPSS or selectable-suite claims.
Owner status: Draft — not offered for approval until D019 independent human
mapping validation and the P8/P9 evidence gates complete; D020 internal
assessment is insufficient
Implementation/evidence commit: P5A implementation through `8795947`; clean
checkout normalization `36ea1fe`; P8/P9 evidence pending
Applied commit:
Rendered PDF SHA-256:
