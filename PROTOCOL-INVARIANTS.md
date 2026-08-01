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

### Approved aPPSS successor path

The TPASS path above remains the active implemented invariant until P5A's
cutover gate passes. D016 authorizes the following separately versioned path
for new successor epochs:

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
Yi. Migration is client-side recovery followed by fresh successor enrollment,
not state conversion.

D017 freezes the exact recovery contract in `docs/APPSS-PROFILE.md`:
`lambda=128`, first profile `k=2,n=3`, RFC 9497 OPRF-mode
ristretto255/SHA-512 as the paper's 2HashDH realization, canonical
polynomial-basis `GF(2^128)` sharing, and domain-separated SHA-256 split into a
16-byte commitment `C` and 16-byte `S_R`. The public `omega=(e,C)` is
suite/epoch/configuration bound. The first profile is abort-only and has no
VOPRF robustness extension. Final wire identifiers and schemas remain a P5A.1
gate; none may reuse a Yi identifier or domain.

## Role-state invariants

### Enrollment client

May transiently hold:

- raw structured input;
- resolver queries and selected records;
- canonical policy output;
- TPASS password input;
- complete TPASS setup output;
- wrapping key;
- plaintext protected private key.

After enrollment, the project may claim only bounded persistent-state deletion
and best-effort memory disposal unless stronger evidence exists.

### Cloud backup store

May hold:

- encrypted private-key backup;
- public TPASS parameters;
- recovery nonce and AEAD metadata;
- public policy and security-policy versions;
- immutable identifier, epoch, and digest.

Must not hold:

- raw cues or selected resolver identifiers;
- canonical cue output or candidate hints;
- TPASS password input or verifier;
- TPASS party secret state;
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
must not receive or persist raw cues, canonical cue output, TPASS password,
party state, recovered group secret, wrapping key, or plaintext private key.
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

### Planned aPPSS holder

After P5A cutover, an aPPSS holder may keep only its own independent OPRF secret
state, its party/index binding, the common public `omega=(e,C)`, and the same
bounded public identity, epoch, policy, configuration, lifecycle, and audit
metadata permitted for a recovery party. It must not hold another server's OPRF
key, an unmasked Shamir share, `p_M`, `S_R`, `K_wrap`, or a separate local cue
verifier. Fewer than reconstruction threshold `k` holder states must not expose
a local predicate under the approved profile assumptions; `k` or more holder
states are explicitly modeled as enabling offline dictionary tests.

### Authorizer-only service

May hold identity, configuration, phase, admission, idempotency, and local audit
state. It holds no TPASS secret state.

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
It must not receive TPASS state, cloud ciphertext, recovered secrets, or private
key material.

### Recovery client

Begins with only the explicitly approved bootstrap inputs. It may transiently
reconstruct the secret path and return the recovered protected key.

## Cross-role invariants

P1.3 represents these boundaries as typed, in-memory contracts. The generic
recovery-suite contract carries opaque suite-bound state and messages, while
the frozen-Yi adapter delegates to the unchanged native backend and wire
profile. These contracts are not new serialization formats. They require one
suite per epoch and preserve distinct recovery-holder membership/threshold and
authorizer membership/quorum fields.

- Recovery-suite threshold and authorization quorum are different types.
- Recovery-suite identity, public parameters, holder membership, threshold,
  backup, policy, recovery identity, and epoch bind to one enrollment.
- A descriptor never authenticates its own trust root.
- The client validates a current consistent epoch before secret-dependent
  recovery.
- Cloud substitution is checked against current honest party metadata.
- Descriptor, backup, party membership, policy, recovery identity, and epoch
  must bind to one enrollment.
- Unsupported versions and cross-policy or cross-epoch mixing fail closed.
- Error responses do not reveal the client's final TPASS or AEAD outcome to
  parties.
- A predecessor is not retired before the successor is durably recoverable.
- Historical protocol identifiers are never reinterpreted.
- A recovery bundle is a transport container, not a trust root: the descriptor
  binds the canonical backup member, the externally authenticated current
  pointer binds the exact active bundle and descriptor, and the client rejects
  every cross-binding mismatch before secret-dependent recovery.
- A client receives no storage-provider credential. The application gateway
  accepts only an unexpired D004/D015 capability bound to subject, backup,
  prefix, operation, client proof key, nonce, and audience.
