# Suite-Neutral System Interfaces

Status: P1.3 typed interface layer implemented and tested on 2026-08-01. This
document freezes interface responsibilities, not external wire schemas or
identifiers. The frozen Yi implementation remains the active recovery path;
aPPSS is not implemented or activated.

## Purpose

P1.3 separates protocol roles before later descriptor, admission, lifecycle,
and aPPSS work. The implementation lives in:

- `prototype/locus/contracts.py` for typed values and structural protocols;
- `prototype/locus/yi_compat.py` for the frozen Yi compatibility adapter;
- `FrozenLocationPersonCuePolicy` in `prototype/locus/cue_policy.py`; and
- `DeterministicResolverAdapter` in
  `prototype/locus/resolver_fixture.py`.

These are in-memory contracts. They do not assign a new suite, state, message,
descriptor, admission, lifecycle, or deployment identifier. P1.4 and the later
schema phases remain responsible for those assignments.

## Recovery-suite boundary

`PasswordProtectedSecretRecovery` owns only password-protected recovery-suite
behavior. It receives:

- a public `RecoveryContext` binding suite, recovery identifier, backup,
  epoch, CuePolicy, configuration, and digest context;
- a typed `ThresholdParameters(k,n)` value that cannot be substituted for an
  authorization quorum; and
- opaque suite-specific password input bytes.

It returns `RecoverySuiteEnrollment`, containing:

- opaque `PublicRecoveryState`;
- a canonical tuple of distinct opaque `PartyRecoveryState` values; and
- the transient high-entropy recovery secret for the active enrollment client.

Recovery consumes the same public context, password input, public state, and
an explicit holder subset. It returns only the recovered high-entropy secret or
fails.

`RecoveryRequest`, `RecoveryResponse`, and `RecoveryClientSession` are distinct
opaque typed boundaries for P3/P4 transport integration. Their payloads are
redacted from object representations. P1.3 does not invent a generic wire
envelope or serialize client-session state. Multi-phase Yi and aPPSS message
semantics remain owned by their suite adapters and later versioned schemas.

### Frozen Yi compatibility adapter

`YiTpassRecoveryAdapter` is the only implemented recovery-suite adapter in
P1.3. It:

- binds to frozen suite `LOCUS-TPASS-YI-ZK-RISTRETTO255-v1`;
- calls the unchanged `NativeTpassBackend` setup/recovery methods;
- preserves embedded `LOCUS-TPASS-wire-v1` public-parameter and party-state
  bytes exactly;
- places the existing strict Python dictionaries into opaque in-memory
  payloads through the existing canonical encoder;
- strictly rejects duplicate, unknown, noncanonical, oversized,
  cross-suite, wrong-format, and mismatched-holder payloads before native
  recovery; and
- does not change `core.py`, Rust code, native messages, domains, backups,
  party records, or retained evidence.

The adapter's canonical wrapper is an internal compatibility representation,
not a newly assigned external Yi format. It cannot be persisted or described
as a migration of frozen Yi state.

No aPPSS adapter exists yet. P5A must create it under new identifiers after the
chronological descriptor, enrollment, recovery, and CuePolicy prerequisites.

## CuePolicy and Resolver boundaries

`CuePolicy` maps structured input to `CuePolicyResult(policy_id,
canonical_bytes)` or fails. `FrozenLocationPersonCuePolicy` delegates directly
to the existing `canonical_recovery_input` function. It does not alter any
validation, ordering, canonical bytes, error, or identifier.

`Resolver` maps one bounded provider result to `ResolverResult` or fails.
`DeterministicResolverAdapter` delegates directly to the existing deterministic
fixture and binds its output to the frozen location-person policy. Direct-input
`NoResolver` and additional policies remain P5 work.

The resolver and policy are separate types even though the frozen resolver
currently produces final canonical policy bytes. Later adapters may return
structured selections, but no adapter may enumerate recovery candidates or
persist a verifier.

## Storage, descriptor, admission, and directory contracts

| Contract | P1.3 responsibility | Current implementation status |
| --- | --- | --- |
| `BackupObjectStore` | Immutable create, exact read, and exact delete through `BackupReference` | Existing filesystem and S3-compatible implementations; now runtime-checkable without semantic change |
| `DescriptorStore` | Immutable descriptor publication/read plus authenticated current-pointer read/CAS | P2.3 filesystem and S3-compatible adapters implement exact-byte immutable publication/read and current-pointer CAS; authentication remains the P2.2 client check |
| `AdmissionVerifier` | Validate a capability and client proof against the complete D004 binding, exact request, and verifier time | P3.4 implements the project-controlled local profile with durable replay state |
| `StorageCapabilityVerifier` | Same validation signature at a distinct storage-gateway trust boundary | P3.4 uses an independent verifier/database rather than accepting an authorizer's decision |
| `ApplicationStorageGateway` | Validate and execute one exact admitted storage operation | P3.4 checks operation, prefix, request digest, proof, and replay state before invoking the P2.3 storage backend |
| `PartyDirectory` | Resolve authenticated authorizer and suite-holder membership for one epoch | P2.2 supplies an exact bootstrap-bound adapter after installed endpoint/key checks and a matching current-state authorization quorum |

`AdmissionBinding` contains exactly the D004 fields: subject, backup, epoch,
operation, audience, client-key thumbprint, nonce, issuance/expiry, issuer, and
profile. `AdmissionCapability` is opaque and secret-bearing. `AdmissionGrant`
contains the validated binding and a safe digest, never the raw credential.

`PartyDirectorySnapshot` holds authorizers and recovery holders in distinct
typed tuples. A recovery holder references an authorizer identity, but the
roles cannot be inferred from one threshold number. The snapshot validates:

- sorted unique authorizer and holder identifiers;
- every holder maps to an authorizer;
- one suite per holder set;
- holder count equals recovery `n`; and
- authorization quorum is independently bounded by authorizer membership.

This represents the current five authorizers / three Yi holders / 4-of-5
authorization / 2-of-3 recovery topology without conflating its parameters.

## Client state-machine contracts

P1.3 freezes public phase names and state snapshots. P3.1 implements the
ordered enrollment state machine with public-metadata-only, idempotent event
retries. P3.2 implements recipient-specific initial provisioning over the
existing authenticated party API. P3.3/P3.4 implement the strict local
admission contract and component boundary.

P2.2 implements the `bootstrap -> descriptor verification -> current state`
prefix as one pure validator over already retrieved bytes. It returns the
authenticated P1.3 `PartyDirectory` adapter only after the operator signature,
P2.1 cross-bindings, external subject/handle, installed directory, and fresh
party quorum agree. Storage fetching remains P2.3 and admitted transport P3.

`EnrollmentClientStateMachine` progresses through:

```text
key -> policy -> suite setup -> key wrap -> backup publication
-> party provisioning -> descriptor publication -> receipt -> disposal
-> complete
```

`RecoveryClientStateMachine` progresses through:

```text
bootstrap -> descriptor verification -> current state -> backup retrieval
-> policy -> threshold selection -> authorization -> suite recovery
-> decryption -> key identity -> successor -> complete
```

P4.1 implements this exact order. Descriptor verification fixes the public
backup/epoch binding; subsequent phases cannot replace it. Retry events and
state deliberately contain no secret-path value or final suite/AEAD outcome,
and wrong input or malformed remote secret-path state normalizes to one public
rejection.

The corresponding dataclasses contain only operation, phase, backup, epoch,
and recovery-handle metadata. They contain no field for private-key bytes,
canonical cues, password input, client blinders, recovery secrets, or wrapping
keys. Implementations must hold those values only in transient active-client
objects and must not serialize them for retry.

`LifecycleManager` exposes prepare-successor, activate-successor, and
retire-predecessor operations around a consecutive-epoch `LifecycleBinding`.
Its interface does not replace the existing lifecycle implementation or
authorize general membership replacement.

## Decoder and compatibility requirements

Every concrete external decoder behind these interfaces must:

- enforce an exact supported version/format before interpreting payloads;
- enforce bounded input size before allocating or parsing;
- reject duplicate, unknown, missing, noncanonical, truncated, and trailing
  data;
- bind suite, epoch, session, party, membership, and configuration where the
  object requires them;
- reject cross-suite or automatic downgrade before secret-dependent work; and
- normalize external failures without weakening internal typed diagnostics.

In-memory opaque values perform basic identifier, type, size, role, and
cross-object checks. They are not a substitute for the strict schema decoders
that P2, P3, P4, and P5A will add.

## P1.3 verification boundary

`prototype/tests/test_system_interfaces.py` verifies:

- the Yi adapter satisfies the runtime recovery-suite protocol and recovers
  the same secret through a 2-of-3 subset;
- the exact native parameter/state payloads from the frozen vector survive the
  compatibility wrapper unchanged;
- the frozen TPASS and CuePolicy vector files retain their pinned SHA-256
  digests;
- noncanonical, duplicate, unknown, oversized, wrong-suite, and wrong-format
  values fail;
- the frozen CuePolicy and deterministic resolver adapters produce their
  existing canonical bytes;
- the existing filesystem store satisfies the structural backup contract;
- authorizer quorum and recovery threshold remain separate; and
- public client-state snapshots contain no secret fields.

These tests establish interface compatibility and rejection behavior. They do
not implement aPPSS, RecoveryDescriptor, public admission, clean-client
recovery, new CuePolicies, or a new cryptographic proof. P3.2 separately adds
remote initial enrollment without changing these P1 interface tests.

## Manuscript and evidence boundary

P1.3 changes no manuscript source or retained evidence. It creates no new
paper claim. Frozen v2 results remain evidence only for the exact inherited Yi
profile, not for the new interface architecture. Later implementation and
evidence profiles require their own identifiers, schemas, provenance, and
owner-gated manuscript deltas.
