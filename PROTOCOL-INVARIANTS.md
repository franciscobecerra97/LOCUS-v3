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

### Authorizer-only service

May hold identity, configuration, phase, admission, idempotency, and local audit
state. It holds no TPASS secret state.

### Resolver

May observe queries and selected candidates when a policy requires resolution.
It must not receive TPASS state, cloud ciphertext, recovered secrets, or private
key material.

### Recovery client

Begins with only the explicitly approved bootstrap inputs. It may transiently
reconstruct the secret path and return the recovered protected key.

## Cross-role invariants

- TPASS threshold and authorization quorum are different types.
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
