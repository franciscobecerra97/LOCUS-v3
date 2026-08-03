# LOCUS aPPSS Wire and State Format v1

Status: P5A.1 exact format contract with the separate P5A.2 native core and
narrow binding implemented. D017 fixes the construction and D018 fixes
selectable coexistence with frozen Yi TPASS. Authenticated distributed
integration and the exact selector application interface are implemented.
D020 records provisional internal mapping acceptance; D019 independent human
confirmation, paired deployment, and retained evidence remain later gates.

## Assigned profile

| Boundary | Identifier |
| --- | --- |
| Recovery suite | `LOCUS-APPSS-2HASHDH-RISTRETTO255-SHA512-GF128-v1` |
| First topology profile | `LOCUS-APPSS-2of3-v1` |
| OPRF profile | `LOCUS-APPSS-OPRF-RISTRETTO255-SHA512-v1` |
| Suite password domain | `LOCUS-APPSS-password-input-v1` |
| Wire family | `LOCUS-APPSS-wire-v1` |
| Public state | `LOCUS-APPSS-public-state-v1` |
| Pending party state | `LOCUS-APPSS-pending-party-state-v1` |
| Installed party state | `LOCUS-APPSS-party-state-v1` |
| OPRF request | `LOCUS-APPSS-request-v1` |
| OPRF response | `LOCUS-APPSS-response-v1` |
| Public-state installation | `LOCUS-APPSS-state-install-v1` |
| Ready acknowledgement | `LOCUS-APPSS-state-ready-v1` |
| Transient client session | `LOCUS-APPSS-client-session-v1` |
| Enrollment selector | `LOCUS-recovery-suite-selector-v1` |
| Public structural vector | `LOCUS-APPSS-format-vectors-v1` |
| Suite-neutral encrypted backup | `LOCUS-reference-backup-v5` |
| Backup associated-data domain | `LOCUS-backup-associated-data-v2` |

The frozen Yi suite remains `LOCUS-TPASS-YI-ZK-RISTRETTO255-v1`; its new
selector label is `LOCUS-TPASS-YI-2of3-v1`. That profile label does not change
the Yi suite, wire bytes, backup v4, or retained evidence.

## Native implementation selection

The implementation is the separate non-published Rust crate
`locus-appss-core`. It uses the pinned `curve25519-dalek 4.1.3`,
`sha2 0.10.8`, `rand_core 0.6.4`, and `zeroize 1.8.1` dependencies. The core
implements RFC 9497 OPRF mode directly and is exposed through the existing
narrow PyO3 extension as separate aPPSS classes and functions. Yi source,
types, and external encodings remain in the unchanged `locus-tpass-core`
crate.

The server public-key commitment is
`SHA-256(Tuple("LOCUS/aPPSS/oprf-key-commitment/v1", context_digest,
u16be(holder_id), SerializeElement(k_i*G)))`. It binds possession metadata
without enabling OPRF verification; the selected profile remains base OPRF,
not VOPRF.

The RFC context string is exactly
`"OPRFV1-" || 0x00 || "-ristretto255-SHA512"`. Hash-to-group uses
`expand_message_xmd` with SHA-512 and the RFC 9497 DST
`"HashToGroup-" || contextString`; canonical 32-byte Ristretto encodings and
identity rejection apply. The LOCUS application labels below do not replace or
modify those RFC domains.

## Cryptographic framing

Every LOCUS cryptographic tuple is:

```text
u32be(field_count) ||
  u32be(len(field_1)) || field_1 || ... ||
  u32be(len(field_m)) || field_m
```

P5A.1 versions the application labels as:

- `LOCUS/aPPSS/epoch-context/v1`;
- `LOCUS/aPPSS/password-input/v1`;
- `LOCUS/aPPSS/2HashDH/instance/v1`;
- `LOCUS/aPPSS/2HashDH/input/v1`;
- `LOCUS/aPPSS/2HashDH/mask/v1`;
- `LOCUS/aPPSS/commit-secret/v1`; and
- `LOCUS/aPPSS/omega/v1`.

The context tuple contains the label, suite ID, 16-byte backup ID, `u64be`
epoch, CuePolicy ID, canonical membership, `u16be(k)`, `u16be(n)`, and 32-byte
configuration digest. Membership starts with `u16be(count)`; every entry is
`u16be(index)`, `u16be(party_id_length)`, ASCII party ID,
`u16be(service_identity_length)`, and ASCII service identity. Entries are
strictly increasing by nonzero index. The first profile requires indices
1, 2, and 3, `k=2`, and `n=3`.

The masked-share vector is `u16be(count)` followed by strictly increasing
`u16be(index) || 16-byte-value` entries. Canonical `omega` is
`Tuple(canonical_masked_share_vector, C)`. P5A.1's public vector intentionally
contains only public structural inputs and outputs; it retains no cue,
password, OPRF key, blinder, unmasked share, recovery secret, or protected key.

## Canonical JSON envelope

Every external object is ASCII JSON with lexicographically sorted object keys,
no insignificant whitespace, JSON separators `,` and `:`, and no duplicate,
unknown, missing, trailing, or non-ASCII representation. Binary values are
lowercase hexadecimal of their exact fixed length. A decoder validates the
maximum encoded size before JSON parsing and re-encodes the accepted value to
require byte-for-byte canonical form.

The normative strict shapes are in
`docs/schemas/appss-wire-v1.schema.json`,
`docs/schemas/recovery-suite-selector-v1.schema.json`, and
`docs/schemas/reference-backup-v5.schema.json`. Python validators additionally
enforce cross-field conditions that JSON Schema cannot express, including
suite/profile pairing, operation/omega pairing, canonical membership order,
and recomputation of `omega_digest`.

## Public and secret state

`LOCUS-APPSS-public-state-v1` contains only the suite/profile/OPRF identifiers,
`context_digest`, `k`, `n`, three indexed masked shares, 16-byte commitment
`C`, and `omega_digest`. It is the canonical `public_state_hex` carried by
RecoveryDescriptor v1 and the canonical public state carried by backup v5.

Pending party state contains only the bound context, holder ID, one independently
generated canonical nonzero OPRF scalar, and its public key commitment. Installed
party state adds the exact public-state and omega digests. No party state stores
`p_M`, an OPRF output, an unmasked share, Shamir secret `s`, `S_R`, `K_wrap`, or
the protected key. Secret party-state JSON is never returned by a service or
written to general logs.

The client session identifier names an in-memory-only object. Client blinds,
OPRF outputs, polynomial coefficients, unmasked shares, `s`, and `S_R` have no
external client-session codec and must have redacted debug representations.

## Initialization and recovery messages

Requests and responses bind the suite, profile, context, holder, operation,
32-byte session ID, 32-byte operation ID, 32-byte fresh nonce, admission-grant
digest, client-proof-key digest, and canonical Ristretto element. Recovery
messages additionally require `omega_digest`; initialization OPRF messages
require it to be null because `omega` does not yet exist. A response repeats
the complete binding and adds the exact request digest and the server public-key
commitment.

After all three initialization OPRF evaluations, the client sends one
`LOCUS-APPSS-state-install-v1` object to each exact recipient. It carries the
identical validated public state plus an initialization transcript digest.
The party atomically converts only its matching pending state to installed
state and returns `LOCUS-APPSS-state-ready-v1`, binding the public-state and
secret-state digests without revealing the state.

## Suite selection, descriptor, and backup

`LOCUS-recovery-suite-selector-v1` is an enrollment/successor input, not a
recovery fallback list. It selects exactly one supported suite/profile and
fixes `k`, `n`, holder IDs, authorizer IDs, and authorization quorum. The first
release permits exactly Yi 2-of-3 or aPPSS 2-of-3 with holder IDs 1--3. Recovery
ignores caller selection and dispatches only from the authenticated descriptor.

RecoveryDescriptor v1 needs no new schema or semantic reinterpretation. Its
existing suite ID, public-state format/bytes, typed threshold, holder mapping,
authorizer topology, and lifecycle configuration digest fully bind either
suite. Cross-field validation must compare those fields with the decoded
aPPSS public state and backup v5.

Backup v4 remains Yi-only and frozen. Backup v5 replaces the TPASS-named field
with one suite-neutral recovery-suite object containing the exact suite/profile,
threshold, context digest, public-state format, and canonical public-state
bytes. Backup associated data v2 authenticates every v5 public field plus the
unchanged AES-256-GCM version. The native suite output is still the sole HKDF
input; no additional recovery key is introduced.

## Bounds and failures

| Object | Maximum canonical bytes |
| --- | ---: |
| Context/membership encoding | 4,096 |
| Public state | 4,096 |
| Pending or installed party state | 4,096 |
| Request or response | 4,096 |
| State install | 8,192 |
| Ready acknowledgement | 4,096 |
| Suite selector | 16,384 |
| Backup v5 | 1,048,576 |

Internal format failures are classified as size, syntax, canonicality, kind,
version, suite, profile, context, membership, threshold, identity element,
binding, replay, state, availability, or cryptographic rejection. Public
parsing and pre-secret availability failures may stay typed. After an admitted
candidate evaluation begins, incorrect evaluation, interpolation failure,
commitment mismatch, and final backup authentication are normalized to one
generic recovery rejection.

Every object fails closed on cross-suite, cross-version, cross-context,
cross-epoch, cross-session, cross-operation, cross-recipient,
cross-membership, mixed-omega, malformed, noncanonical, replayed, or oversized
input. There is no decoder fallback, format guessing, or Yi/aPPSS conversion.

## Compatibility and evidence boundary

The canonical public structural vector is
`prototype/test-vectors/appss-format-v1.json`; one independent test consumer
recomputes its context, omega digest, and JSON bytes without importing LOCUS.
It is conformance material, not cryptographic or performance evidence.

`appss-core/test-vectors/appss-2of3-public-v1.txt` is the P5A.2 public-only
native vector. Rust regenerates it with deterministic test randomness and the
Python boundary independently decodes the same bytes. It contains no password,
OPRF key, mask, recovery secret, or protected key. RFC 9497 Appendix A.1.1.1 is
also reproduced exactly by the native Rust tests.

The future 3-of-5 profile receives a separate profile identifier, topology
vector, deployment identity, and result path at P6.3. No 3-of-5 identifier is
assigned here. Deployment, trace, result, and artifact identifiers remain at
their later chronological gates.
