# Protocol Invariants

## Protected-key path

For structured input \(M\) and immutable policy identifier \(v_M\):

```text
CuePolicy_vM(M) -> Z_M or failure
p_M = domain-separated hash-to-scalar(ID_R, Z_M)
TPASS.Setup(ID_R, p_M, t, n) -> public parameters, party states, S_R
K_wrap = HKDF-SHA-256(Encode(S_R), recovery nonce, backup context)
C_U = AES-256-GCM.Enc(K_wrap, sk_U, authenticated backup metadata)
```

Recovery repeats the same policy and password derivation, performs online TPASS
with a consistent threshold subset, validates the TPASS result, derives the same
wrapping key, and authenticates/decrypts the exact backup object.

There is no independent symmetric recovery key between TPASS and `K_wrap`.

### Approved selectable recovery-suite path

The TPASS path above remains frozen and supported. D017 authorizes the following
separately versioned aPPSS path, D018 keeps both Yi and aPPSS selectable for new
enrollments and successor epochs, and D020 activates the exact
application/component selector after provisional internal mapping acceptance:

```text
CuePolicy_vM(M) -> Z_M or failure
p_M = SHA-256(Tuple(aPPSS password domain, bound epoch context, Z_M))
aPPSS.Initialize / aPPSS.Recover -> 16-byte high-entropy output sk_appss
S_R = sk_appss (exactly 16 bytes)
K_wrap = HKDF-SHA-256(S_R, recovery nonce, backup context)
C_U = AES-256-GCM.Enc(K_wrap, sk_U, authenticated backup metadata)
```

The aPPSS output is the recovery secret; there is no additional independently
sampled or threshold-shared unmasked `S_R` between aPPSS and `K_wrap`. Every
epoch binds exactly one recovery suite. Existing Yi epochs use only the frozen
Yi path, and an aPPSS epoch never falls back to or combines shares/messages with
Yi. Suite switching is client-side predecessor recovery followed by fresh
successor enrollment under the selected suite, never state conversion.
Protected-key generation/import, key identity, HKDF-SHA-256, and AES-256-GCM
retain the same suite-neutral meaning in both paths.

P5A.5 implements that switching invariant in the active application/component
path. The
authenticated predecessor descriptor selects the only recovery adapter; the
new-epoch selector is consulted only after predecessor recovery. Fresh Yi
party state or fresh aPPSS holder/public state is created, the common backup
path preserves the protected-key identity, and the P4.3 journal binds the
successor backup/configuration/descriptor digests before activation. Old/new
and cross-suite state cannot be combined.

D017 freezes the exact recovery contract in `docs/APPSS-PROFILE.md`:
`lambda=128`, first profile `k=2,n=3`, RFC 9497 OPRF-mode
ristretto255/SHA-512 as the paper's 2HashDH realization, canonical
polynomial-basis `GF(2^128)` sharing, and domain-separated SHA-256 split into a
16-byte commitment `C` and 16-byte `S_R`. The public `omega=(e,C)` is
suite/epoch/configuration bound. The first profile is abort-only and has no
VOPRF robustness extension. D018 pairs Yi and aPPSS at `k=2,n=3` first and
`k=3,n=5` after configuration generalization, using the same outer system
conditions within each comparison. Final wire identifiers and schemas remain a
P5A.1 gate; none may reuse a Yi identifier or domain.

D020's assessment is non-independent and does not prove either construction.
D019 independent human confirmation remains mandatory before manuscript
reliance or a final reviewed release. The frozen Yi-only Compose deployment and
retained v2 evidence remain unchanged; paired deployment profiles begin in P6.

## Role-state invariants

### Enrollment client

May transiently hold:

- raw structured input;
- resolver queries and selected records;
- canonical policy output;
- the selected suite's password input;
- complete selected-suite setup/initialization output;
- wrapping key;
- plaintext protected private key.

After enrollment, the project may claim only bounded persistent-state deletion
and best-effort memory disposal unless stronger evidence exists.

### Cloud backup store

May hold:

- encrypted private-key backup;
- public selected-suite parameters/state (`TPASS` parameters or aPPSS `omega`);
- recovery nonce and AEAD metadata;
- public policy and security-policy versions;
- immutable identifier, epoch, and digest.

Must not hold:

- raw cues or selected resolver identifiers;
- canonical cue output or candidate hints;
- recovery-suite password input or verifier;
- recovery-suite party secret state;
- recovered group secret or wrapping key;
- plaintext protected private key.

### Descriptor store

May hold authenticated public configuration and a current pointer.

Must not contain any value that lets the store or a snapshot test cue candidates
offline.

An account-scoped provider may physically store an immutable bounded recovery
bundle containing the canonical encrypted backup, signed descriptor, and public
manifest. This does not merge the logical backup, descriptor, and mutable
current-pointer contracts. The current pointer remains outside the bundle, and
the bundle adds no permission to retain cue-derived or secret-bearing state.

### Application storage gateway

May transiently handle:

- a proof-key-bound admission/storage capability;
- pseudonymous subject scope, backup identifier, epoch, exact object key, and
  requested storage operation;
- encrypted backup, signed descriptor, current pointer, bundle, and public
  manifest bytes required by that exact operation.

May hold only the narrow server-side provider authority required for the
application-operated namespace. It exposes no bucket listing to the client and
must not receive or persist raw cues, canonical cue output, recovery-suite
password input, party state, recovered group secret, wrapping key, or plaintext
private key.
Gateway or provider compromise is included in the declared cloud-side view and
does not authenticate LOCUS contents.

### TPASS holder

May hold:

- its own native TPASS state;
- exact backup reference and digest;
- recovery identity, epoch, policy/security profile;
- identity, phase, idempotency, lifecycle, and local audit state.

Must not hold:

- another party's TPASS state;
- the encrypted backup object as its authoritative storage role;
- raw cues, canonical cue output, TPASS password, recovered group secret,
  wrapping key, or plaintext key;
- a local cue verifier.

### Implemented P5A.3/P5A.4 aPPSS holder boundary

The P5A.3/P5A.4 component implementation keeps only its own independent OPRF secret
state, its party/index binding, the common public `omega=(e,C)`, and the same
bounded public identity, epoch, policy, configuration, lifecycle, and audit
metadata permitted for a recovery party. It must not hold another server's OPRF
key, an unmasked Shamir share, `p_M`, `S_R`, `K_wrap`, or a separate local cue
verifier. Fewer than reconstruction threshold `k` holder states must not expose
a local predicate under the approved profile assumptions; `k` or more holder
states are explicitly modeled as enabling offline dictionary tests.

P5A.6 exercises this boundary only through a fixed aggregate development
regression. It retains no candidate, OPRF key, share, recovery output, private
key, or raw state. The absence observation below `k` does not prove the
construction; it checks only the exact serialized-state and bounded API surface.
At `k`, aPPSS is classified as unrate-limited offline dictionary testing whose
correct input yields `S_R`, while Yi is classified separately as direct
interpolation of its shared input scalar and protected exponent without a
dictionary search.

### Authorizer-only service

May hold identity, configuration, phase, admission, idempotency, and local audit
state. It holds no TPASS or aPPSS secret state.

### Admission issuer and verifier

The D004 reference profile uses a project-controlled local synthetic issuer to
authenticate a synthetic pseudonymous subject and issue a short-lived
proof-key-bound capability. Authorizers and the application storage gateway
validate the capability independently for the exact subject, backup, epoch,
operation, audience, client proof key, nonce, issuance time, and expiry.

The issuer/verifier must not receive or persist cue input, `Z_M`, `p_M`,
recovery-suite secret state, `S_R`, `K_wrap`, the plaintext protected key, or
the final recovery outcome. Admission is an access-control and availability
prerequisite, not an additional recovery factor or offline cue verifier. OIDC
Authorization Code with PKCE/DPoP is an optional later adapter and is not
required by the reference profile.

### Resolver

May observe queries and selected candidates when a policy requires resolution.
It must not receive recovery-suite state, cloud ciphertext, recovered secrets,
or private-key material.

### Recovery client

Begins with only the explicitly approved bootstrap inputs. It may transiently
reconstruct the secret path and return the recovered protected key.

### D023 deployed active-client boundary

For the integrated reference system, the host browser and the ephemeral
UI/client-gateway container together form the active-client boundary. The
browser may reach only the gateway's host-loopback endpoint and the gateway
alone coordinates the protected path. Browser code must not receive provider
credentials or connect directly to admission, discovery, storage, resolver, or
party services.

The gateway may transiently handle the same values already permitted to the
enrollment or recovery client, but containerization and transport do not add a
second secret path. The remote-service backend must preserve the exact
CuePolicy-to-suite-to-HKDF-to-AEAD composition and the normalized public error
boundary. Its durable state and logs may contain only explicitly permitted
public, bounded operation metadata; Client A state and credentials must not be
available to clean Client B.

## Cross-role invariants

P1.3 represents these boundaries as typed, in-memory contracts. The generic
recovery-suite contract carries opaque suite-bound state and messages, while
the frozen-Yi adapter delegates to the unchanged native backend and wire
profile. These contracts are not new serialization formats. They require one
suite per epoch and preserve distinct recovery-holder membership/threshold and
authorizer membership/quorum fields.

P1.5 records the phase/view flow contract in `docs/INFORMATION-FLOW.md` and the
normative C01--C26 security contracts in `docs/security-matrix-v1.json`.
Gated cells and prospective evidence boundaries are requirements, not claims of
implemented behavior.

- Recovery-suite threshold and authorization quorum are different types.
- Recovery-suite identity, public parameters, holder membership, threshold,
  backup, policy, recovery identity, and epoch bind to one enrollment.
- A descriptor never authenticates its own trust root.
- `LOCUS-recovery-descriptor-v1` and
  `LOCUS-descriptor-current-pointer-v1` verify only against an externally
  supplied expected issuer, key ID, and Ed25519 public key. The descriptor
  binds `backup.json`; the two-entry manifest binds backup and descriptor but
  never itself; the signed pointer alone binds the exact uploaded ZIP and its
  provider-assigned locator.
- The client validates a current consistent epoch before secret-dependent
  recovery.
- In `LOCUS-account-scoped-bootstrap-v1`, the installed trust configuration is
  the only source of the operator key, discovery endpoint, party endpoints,
  party key IDs, and party public keys. Descriptor values must exactly match
  it. A fresh matching party-current-summary set must reach the independently
  typed authorization quorum before cue processing.
- Trust-configuration predecessor digests detect accidental or substituted
  update chains but do not authenticate an update channel. Root/key/endpoint
  replacement arrives only through the trusted application installation path.
- A signed receipt is optional public metadata and an initial binding, not a
  recovery factor, provider credential, or monotonic freshness witness.
- Cloud substitution is checked against current honest party metadata.
- Descriptor, backup, party membership, policy, recovery identity, and epoch
  must bind to one enrollment.
- Unsupported versions and cross-policy or cross-epoch mixing fail closed.
- Error responses do not reveal the client's final recovery-suite or AEAD
  outcome to parties.
- A predecessor is not retired before the successor is durably recoverable.
- P4.3 enforces that client-side ordering by verifying the prepared successor
  against the original recovered-key identity before invoking the frozen
  lifecycle's atomic predecessor-retirement/successor-activation operation.
  Its durable journal retains only public bindings and digests, and key
  rotation remains an explicit Boolean choice that defaults to false in the
  implemented path.
- Historical protocol identifiers are never reinterpreted.
- Every externally serialized identifier is allocated through
  `VERSION-REGISTRY.md`; reserved families have no usable identifier until the
  named schema/vector gate passes, and unknown versions fail before dependent
  fields are interpreted.
- A recovery bundle is a transport container, not a trust root: the descriptor
  binds the canonical backup member, the externally authenticated current
  pointer binds the exact active bundle and descriptor, and the client rejects
  every cross-binding mismatch before secret-dependent recovery.
- `LOCUS-descriptor-bundle-store-v1` keeps immutable descriptors and bundles
  separate from the mutable current pointer. Exact-byte retries are idempotent;
  differing immutable bytes conflict; current replacement requires CAS; and
  S3 ETags are concurrency tokens rather than authenticity or content digests.
- P2.4 descriptor-security output is aggregate-only development regression
  data. Passing detectors and direct-digest positive controls do not prove the
  absence of every offline predicate or promote a manuscript/evidence claim.
- A client receives no storage-provider credential. The application gateway
  accepts only an unexpired D004/D015 capability bound to subject, backup,
  prefix, operation, client proof key, nonce, and audience.
- D023's integrated active path reaches admission, discovery, storage,
  resolution when required, enrollment, recovery, and lifecycle only through
  authenticated service routes. Direct party-volume suite-state injection and
  direct in-memory record injection are prohibited on that path.
- The application storage gateway remains outside the active-client secret
  path. It never receives cues, canonical policy output, suite password input,
  suite-holder state, `S_R`, `K_wrap`, or plaintext protected-key material,
  regardless of whether its provider is local S3-compatible storage or an
  approved external adapter.
- The integrated networkless bootstrap role may create synthetic service
  credentials, public configuration, empty role roots, and fixtures only. It
  must have no runtime network and cannot generate, deliver, or persist
  recovery-suite state or any client secret-path value.
