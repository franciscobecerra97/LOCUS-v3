# LOCUS Recovery-Request And Administrative Authorization

Status: deferred future security design, originally selected by P5.4 on
2026-07-16. Public OIDC/DPoP admission and administrative authorization are
outside the frozen Cycle 1 implementation and positive claims. This document
specifies a possible future interface only; it is not implementation,
deployment, or attempt-bound evidence.

## Decision Summary

LOCUS separates two kinds of authority:

1. **Ordinary recovery admission** uses a short-lived, audience-restricted OAuth/OIDC access token bound to a fresh client key with DPoP. Every recovery-party authorizer independently validates the token, sender proof, stable enrolled subject binding, and exact LOCUS request before it votes to consume an attempt.
2. **High-impact administration** uses an enrollment-pinned `m_admin`-of-`k_admin` signature policy, in addition to the recovery-party ledger quorum. Budget extension additionally requires a fresh ordinary user admission proof and is bounded by a disclosed lifetime `X_max`.

The former target profile used a pairwise OIDC subject, a JWT access token
intended only for the LOCUS recovery audience, OAuth Authorization Code with
PKCE for browser-capable clients, and the Device Authorization Grant only for
genuinely headless CLI use. Tokens would be sender-constrained with DPoP. The
current Compose artifact does not run an identity provider and does not
implement this profile.

This future design would introduce an identity provider as an admission and
availability dependency. It would not give that provider cue or key material,
but compromise could authorize guesses and cause lockout. No statement that
such guesses are bounded by `B_eff` applies to the current prototype: P5.13
demonstrates rollback counterexamples in the quorum-only ledger.

## Problem Statement

If knowledge of a public account or backup identifier is sufficient to reserve an attempt, any outsider can spend the entire scarce budget and lock out the legitimate user. Conversely, if recovery admission requires a secret stored only on the lost device, fresh-device recovery fails.

The selected solution relies on a separately recoverable account-authentication system for ordinary admission. This matches the intended CLI flow in which the user first enters or completes account credentials and then independently supplies LOCUS cues. The two inputs have different purposes:

- the account credential decides who may spend a scarce online attempt;
- the cue-derived TPASS password decides whether the threshold recovery succeeds.

The account credential is not included in key derivation and is not a verifier for the cues.

## Security Objectives

The design must ensure:

1. a public identifier alone cannot reserve an attempt;
2. a stolen access token alone is insufficient when the DPoP private key is not stolen;
3. admission is bound to one enrolled identity, backup, epoch, session, and blinded TPASS request;
4. the coordinator cannot mint admission evidence;
5. every authorizer independently checks the evidence before voting;
6. exact retry is idempotent, while a changed TPASS request requires a new counted attempt;
7. ordinary admission cannot reset or extend the budget;
8. no single administrator can extend budget or replace authorization configuration;
9. administrative changes preserve the certified attempt head and disclosed `B_eff`;
10. no authorization component becomes a key custodian or receives cue/password material;
11. tokens and personally identifying claims are minimized and never stored or logged in raw form;
12. the failure and availability costs of identity-provider or administrator loss are explicit.

## Enrollment-Time Authorization Policy

The certified `AttemptConfig` records:

- exact permitted issuer identifier;
- issuer-metadata/JWKS policy and allowed asymmetric signature algorithms;
- LOCUS resource-server audience and permitted client identifiers;
- required recovery scope, fixed as `locus:recover` for the baseline;
- requirement for a pairwise OIDC `sub` value;
- hash of the enrolled `(issuer, pairwise_sub, bid, identity_salt)` binding;
- required assurance policy expressed as configured `acr`/`amr` rules without claiming that a specific factor is phishing-resistant unless the provider proves it;
- DPoP requirement and permitted DPoP algorithms;
- maximum token/proof age and accepted clock skew;
- `m_admin`, `k_admin`, administrator identifiers, and verification keys;
- `X_max`, the maximum cumulative budget extension permitted for the epoch;
- permitted administrative action types;
- optional offline admission public key, disabled in the baseline profile.

Parties do not store an email address, telephone number, display name, username, password hash, cue identifier, or raw identity token. Hashing a public email address is not treated as privacy protection.

The identity-provider account and recovery-party configuration should be operated separately from the S3-compatible object store when feasible. Local Compose co-location is a reproducibility setup, not an independence claim.

## Ordinary Admission Credential

### Access-token profile

The baseline requires a signed JWT access token compatible with the OAuth JWT access-token profile. Authorizers validate, at minimum:

- exact issuer and configured verification key/algorithm;
- token type and signature;
- audience containing only the configured LOCUS recovery resource;
- pairwise subject matching the enrolled subject binding;
- `exp`, `nbf`, and `iat` under configured skew;
- unique token identifier where supplied by the selected profile;
- authorized client identifier (`client_id` or `azp`, as applicable);
- scope containing `locus:recover` and no interpretation of unrelated scopes;
- `cnf.jkt` matching the DPoP proof key thumbprint;
- configured assurance claims when the action requires them.

A future provider would need to issue minimal tokens without email, profile,
group, address, or telephone claims. A provider that cannot supply an
audience-restricted, sender-constrained token with a stable pairwise subject
would not conform to this design.

### Client authorization flow

For a browser-capable client, LOCUS uses Authorization Code with PKCE and exact registered redirects. The authorization code is additionally bound to the DPoP key when provider support permits it.

For a genuinely headless recovery CLI, the provider may expose the OAuth Device Authorization Grant. The CLI displays the verification URI and user code, and the user authenticates on a separate trusted browser. Device flow is not used merely for convenience when a safe browser-based native-app flow is available; its remote-phishing and user-code rate-limit risks must be tested and documented.

The CLI generates a fresh DPoP key for the authorization transaction, holds it only for the recovery session, and requests a short-lived access token. Refresh tokens are not persisted in the baseline recovery container.

### DPoP request proof

Each request to an authorizer carries:

- the DPoP-bound access token;
- a unique DPoP proof targeted to that authorizer's exact HTTPS endpoint and method;
- the authorizer-provided DPoP nonce when required;
- the access-token hash required by DPoP;
- a LOCUS private claim `locus_req` equal to the canonical LOCUS `request_digest`.

The authorizer performs all standard DPoP checks, verifies the access-token key binding, rejects reused proof identifiers except for the exact idempotent retry, and explicitly validates `locus_req`. DPoP proof of key possession is not treated as identity authentication by itself; it is accepted only with the valid bound access token.

Because `htu` and the resource-server nonce are endpoint-specific, the client creates one proof per party. The coordinator may relay those proofs but cannot rewrite or reuse them for another party or request.

## LOCUS Request And Admission Digests

P5.2's digest construction is refined to avoid a circular dependency and to permit equivalent fresh credentials to resume the same not-yet-authorized request.

`request_digest` is:

`H("LOCUS/attempt-request/v1" || protocol_version || bid || epoch || config_digest || recovery_identity || sid || encode(A) || policy_digest || admission_policy_digest)`.

It does not contain an access-token identifier, expiry, or DPoP proof identifier. Those values are evidence that the stable request was authorized, not part of the password attempt itself.

After validating a token and proof, each authorizer constructs an `AdmissionRecord` containing only:

- issuer-configuration digest;
- enrolled pairwise-subject binding digest;
- resource audience and recovery scope digest;
- assurance-policy result/class;
- DPoP public-key thumbprint;
- token identifier and expiry;
- party-specific DPoP proof identifier and nonce digest;
- `request_digest`;
- validation time and policy version.

The ledger entry stores a canonical `admission_grant_digest` over the shared issuer, subject binding, audience, scope, assurance result, DPoP key, token identifier, token expiry, and `request_digest`. It does not store the token, proof JWT, raw subject, or authentication claims. Party-specific proof identifiers and nonce digests remain only in each party's local `AdmissionRecord` and may differ without changing the common ledger entry.

A renewed token for the same enrolled subject may resume a request that has no conflicting slot lock. Once a proposal is durably locked, recovery completes using the same canonical entry and admission grant or fails closed; token renewal never permits substituting a different `A` at that position.

## Admission State Machine

### A0: Unauthenticated request

The service performs bounded parsing, request-size limits, connection controls, and coarse pre-authentication throttling. Unknown backup and invalid-credential responses are externally normalized to reduce account enumeration. No attempt-ledger state changes.

### A1: Issue party nonce

After syntactic checks, an authorizer returns a short-lived unpredictable DPoP nonce associated with a privacy-minimized connection/session handle. Issuing a nonce consumes no recovery attempt. Nonce endpoints are separately throttled and may use a stateless authenticated nonce format or bounded server cache.

### A2: Validate evidence

The authorizer validates TLS/session context, issuer metadata, access-token signature and claims, DPoP signature/key binding, endpoint/method, token hash, proof freshness, nonce, proof identifier, `locus_req`, and enrolled subject binding.

Validation failure consumes no attempt and returns a generic admission rejection. Detailed causes are recorded only as coarse authenticated metrics, without raw tokens.

### A3: Persist admission replay record

Before releasing an attempt-ledger first-phase vote, the authorizer transactionally stores the proof replay/idempotency mapping and `AdmissionRecord` digest. Exact replay for the same party, proof identifier, `sid`, and request returns the stored decision. Reuse for another request is rejected.

### A4: Enter attempt state machine

Only a valid admission record allows transition to P5.2 `T1: Receive proposal`. The P5.2 durable slot lock and two-phase authorization determine when the attempt is counted.

Admission success is not cue/password success. Parties do not learn whether TPASS or AEAD later succeeds.

## Administrative Authorization

Administrative actions are not accepted through an ordinary user token alone.

### Administrative identities

Enrollment pins `k_admin` administrator verification keys and a threshold `m_admin`. The paper-facing default is `2-of-3`. Administrator keys are distinct from the coordinator key and should be distinct from recovery-party service keys. Docker test keys are synthetic and artifact-only.

An `AdminAction` contains:

- protocol version and action type;
- `bid`, epoch, active configuration, and current certified head;
- exact canonical action parameters;
- expected resulting `consumed`, `B_eff`, configuration, and epoch status;
- random action nonce;
- creation and expiry bounds;
- reason-code category without free-form sensitive text.

`m_admin` distinct administrators sign its domain-separated digest. Authorizers verify the signatures and exact current-head binding before considering the corresponding ledger transition.

### Budget extension

A budget extension requires all of:

1. a fresh ordinary OIDC/DPoP admission proof for the enrolled user, meeting the configured higher-assurance rule;
2. a valid `m_admin`-of-`k_admin` action certificate;
3. the normal attempt-ledger authorization quorum;
4. positive extension amount within per-action and cumulative `X_max` limits;
5. a certified `BUDGET_EXTENSION` entry that increases `X` and leaves `consumed` unchanged.

There is no reset. All extensions are visible in `B_eff`, audit evidence, evaluation, and the guessing equation. Repeated extensions beyond `X_max` are invalid even with administrator signatures; changing `X_max` requires joint reconfiguration and must be disclosed as a changed security policy.

### Configuration change and party replacement

`CONFIG_PREPARE` requires the current ledger quorum and an administrator certificate bound to the new configuration. `CONFIG_ACTIVATE` additionally requires the P5.2 old/new joint certificates. Replacement carries the current head, `consumed`, `B_eff`, subject binding, issuer policy, administrator policy, and retirement status.

An unavailable old quorum cannot be bypassed by administrator signatures. If continuity cannot be certified, the deployment must create a fresh epoch through an explicitly out-of-band process and must not claim preservation of the old attempt bound.

### Epoch retirement

Retirement requires the current ledger quorum and an administrator certificate. A fresh user admission proof is recommended for user-initiated retirement but is not required for emergency operator retirement, because retirement can only deny old recovery rather than increase guessing budget. The policy and reason must distinguish these cases.

## Optional Offline Admission Capability

A deployment may allow the user to export a random public-key admission credential at enrollment. The public key is certified in `AttemptConfig`; the private key is stored by the user as a recovery file, hardware credential, or printed/encoded high-entropy backup.

This key could substitute for future OIDC ordinary admission by signing the
exact request and party challenge. It would not derive or decrypt the private
key and would not be a cue verifier. Loss would prevent this fallback; theft
would let an attacker spend whatever attempt budget the deployment actually
enforces. The scoped Cycle 1 artifact does not implement this option because it
would silently turn LOCUS into a two-secret recovery scheme.

The optional capability cannot by itself extend budget, replace parties, or change issuer/admin policy.

## Failure Behavior

- Public identifier without credentials: generic rejection before ledger mutation.
- Invalid/expired token, issuer, audience, scope, assurance, or subject: generic admission rejection.
- Valid token without matching DPoP key: reject.
- Replayed DPoP proof for the same request: return the stored idempotent decision; changed request: reject.
- Token expiry during an uncommitted partial proposal: resume only if enough durable authorizer decisions can safely complete the identical entry; otherwise fail closed. Do not substitute a new request into the locked slot.
- Identity provider unavailable or unknown signing key: use only valid policy-compliant cached metadata/keys; otherwise fail closed before counting.
- Coordinator compromised: it can delay or discard evidence but cannot forge issuer, DPoP, authorizer, or administrator signatures.
- One administrator compromised: insufficient under the default threshold.
- Administrator quorum compromised: can deny service or authorize policy-bounded extensions/changes, but still cannot reconstruct the private key without TPASS/cue requirements.
- Identity provider compromised: can mint admission tokens and cause bounded guesses/lockout; cannot exceed the ledger budget or recover the key alone.
- User account compromised with DPoP-capable login: attacker can spend the current `B_eff`; this is an explicit residual risk.
- All admission methods lost: recovery is unavailable. There is no public-identifier bypass.

## Privacy And Logging Rules

Authorizers may persist:

- issuer-configuration digest;
- pseudonymous enrolled subject-binding digest;
- audience/scope/assurance result;
- token/proof identifiers or keyed digests needed for replay prevention;
- DPoP key thumbprint;
- expiration and validation timestamps;
- request/session/ledger bindings;
- administrator identifiers and signed action digests.

They must not persist or emit:

- access or refresh tokens;
- DPoP private keys or complete proof JWTs after validation;
- email, username, phone, display name, address, profile/group claims, or IdP passwords;
- raw WebAuthn/passkey assertions unless the IdP itself—not LOCUS—is being evaluated;
- raw cues, canonical resolver records, TPASS password/scalars/shares, recovered secrets, wrapping keys, or private keys.

Pairwise subject identifiers reduce cross-client correlation but do not make the identity provider anonymous. Parties still observe that repeated attempts target the same enrolled recovery identity, which is necessary for budget enforcement.

## Threat Analysis

| Adversary | Admission result | Remaining capability |
| --- | --- | --- |
| Public-information attacker with only `bid`/account name | Rejected before reservation. | Can cause network/pre-authentication load and attempt account enumeration. |
| Stolen bearer token without DPoP key | Rejected by sender binding. | May reveal minimal token metadata if leakage occurred; token issuer must still revoke/expire it. |
| Stolen token and DPoP key or compromised authenticated client | Accepted as the user. | Can spend at most the certified `B_eff` under ledger assumptions and cause lockout. |
| Malicious coordinator | Cannot mint admission or admin evidence. | Can suppress, reorder, or split proposals and cause denial of service. |
| Cloud object-store compromise | Does not imply issuer or DPoP authority. | Can delete/rollback ciphertext and cause availability loss. |
| Identity-provider compromise | Can mint ordinary admission. | Can drive bounded online guesses and lockout, observe identity/authentication, and deny service; cannot recover the key alone. |
| Fewer than `m_admin` administrators | Cannot authorize high-impact action. | Can refuse their approvals or leak operational metadata. |
| `m_admin` compromised administrators | Can approve configured admin actions. | Can extend up to policy limits, replace configuration with ledger/joint approval, or deny service; this trust must be disclosed. |
| Recovery-party coalition below `q_a` | Cannot certify attempts or admin ledger entries alone. | May validate credentials locally, leak metadata, or refuse service. |

Admission authorization prevents inexpensive unauthenticated budget exhaustion; it does not eliminate denial of service by the IdP, authenticated account attacker, administrators, coordinator, cloud, network, or sufficient parties.

## Required Tests

P5.5-P5.13 and P6 must include:

- valid browser/PKCE and headless/device flows using synthetic accounts;
- wrong issuer, key, algorithm, audience, client, subject, scope, assurance, expiry, and clock skew;
- bearer-token theft with and without the DPoP private key;
- DPoP `htu`, `htm`, `ath`, `iat`, `jti`, nonce, key-thumbprint, and `locus_req` mutations;
- proof replay to the same and different parties, requests, sessions, backups, and epochs;
- token expiry and issuer-key rotation at every attempt-state transition;
- identity-provider and JWKS outage with valid/invalid caches;
- account enumeration and pre-authentication flood behavior;
- compromised coordinator relay/substitution attempts;
- one and threshold administrator signature cases;
- budget-extension boundaries at `X_max`, repeated extension, changed-head replay, and hidden-reset attempts;
- replacement and retirement with stale admin actions;
- recursive database, log, trace, crash-dump, and CLI-history scans for prohibited credentials/identity claims;
- optional offline-capability loss, theft, replay, and request-binding tests.

The artifact uses only synthetic identities and credentials. Test mode must be visibly distinct from ordinary mode and must never accept a hard-coded bypass in paper-facing runs.

## Evaluation Plan

Measure and report:

- interactive login time separately from protocol/server latency;
- token and DPoP validation latency per party;
- issuer metadata/JWKS cache-hit and rotation costs;
- admission bytes and added round trips;
- party nonce and proof replay-store growth;
- latency/availability with the IdP online, cached, slow, and unavailable;
- overhead of `m_admin` verification and budget-extension entries;
- pre-authentication rejection throughput without consuming attempts;
- privacy-minimized persistent bytes per admission;
- compact/resilient end-to-end recovery latency with and without authorization overhead.

Human usability, passkey recovery success, IdP account-recovery quality, and phishing resistance are not established by these system experiments.

## Paper Implications

The manuscript must state:

- ordinary LOCUS recovery is not publicly callable: it requires separate account admission before a cue attempt is consumed;
- the account credential gates scarce attempts but does not decrypt the key or replace the cue-derived TPASS password;
- the IdP is a central admission/availability dependency and can cause bounded guessing or lockout if compromised;
- administrative extensions change `B_eff` and require threshold operator approval;
- the baseline does not eliminate lockout or IdP account-recovery risk;
- optional offline admission adds a separate retained secret and is not silently part of the baseline;
- OIDC/OAuth/DPoP integration is an operational mechanism, not LOCUS's cryptographic novelty.

Until implemented and attacked, the paper may describe this as the selected design only. It may not claim that public lockout abuse, token replay, or administrative extension abuse is already prevented by the artifact.

## Source Basis

- OpenID Foundation, [OpenID Connect Core 1.0 incorporating errata set 2](https://openid.net/specs/openid-connect-core-1_0-errata2.html): identity layer, issuer/subject processing, and pairwise subject identifiers.
- IETF, [RFC 9700: Best Current Practice for OAuth 2.0 Security](https://www.rfc-editor.org/rfc/rfc9700.html): Authorization Code/PKCE guidance, sender-constrained tokens, issuer handling, and current OAuth threat mitigations.
- IETF, [RFC 9449: OAuth 2.0 Demonstrating Proof of Possession](https://www.rfc-editor.org/rfc/rfc9449.html): DPoP token binding, proof validation, nonces, and replay considerations.
- IETF, [RFC 9068: JWT Profile for OAuth 2.0 Access Tokens](https://www.rfc-editor.org/rfc/rfc9068.html): interoperable signed JWT access-token structure.
- IETF, [RFC 7636: Proof Key for Code Exchange](https://www.rfc-editor.org/rfc/rfc7636.html): PKCE for public OAuth clients.
- IETF, [RFC 8628: OAuth 2.0 Device Authorization Grant](https://www.rfc-editor.org/rfc/rfc8628.html): optional limited-input/headless authorization flow and its security constraints.
- IETF, [RFC 9207: OAuth 2.0 Authorization Server Issuer Identification](https://www.rfc-editor.org/rfc/rfc9207.html): issuer identification and mix-up protection.

These specifications define the external mechanisms. They do not prove the LOCUS composition, policy, implementation, or user experience.
