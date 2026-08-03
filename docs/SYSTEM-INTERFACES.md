# Suite-Neutral System Interfaces

Status: P1.3 typed interface layer implemented and tested on 2026-08-01; P5.1
completed frozen-policy application routing, P5.3 added the exact four-policy
registry, P5A.3 implemented the separate aPPSS adapter and no-fallback suite
registry, P5A.4 added authenticated distributed aPPSS initialization, and P5A.5
added explicit selection and four-direction successor preparation on
2026-08-03. D020 activates this application/component interface after
provisional internal mapping acceptance. P6.3 adds the matched 2-of-3 and
3-of-5 same-host process deployment profiles; independent human validation and
retained evidence remain pending.

## Purpose

P1.3 separates protocol roles before later descriptor, admission, lifecycle,
and aPPSS work. The implementation lives in:

- `prototype/locus/contracts.py` for typed values and structural protocols;
- `prototype/locus/yi_compat.py` for the frozen Yi compatibility adapter;
- `prototype/locus/appss.py` and `prototype/locus/appss_client.py` for the
  independent aPPSS adapter and transient distributed client;
- `prototype/locus/recovery_suite_registry.py` for exact selection and
  descriptor-bound dispatch;
- `prototype/locus/appss_party.py` and `prototype/locus/appss_party_http.py`
  for durable per-holder state and pinned mutual-TLS transport;
- `prototype/locus/suite_backup.py` for the common backup-v5/v6 HKDF/AES path;
- `prototype/locus/paired_deployment_profiles.py` for the two matched P6.3
  comparison-control profiles;
- `prototype/locus/party_endpoint_setup.py` for the strict P6.4 public
  endpoint-setup boundary used by local staging and later host placement;
- `prototype/locus/selectable_suite_lifecycle.py` for active explicit
  enrollment selection and P4.3 successor integration;
- `prototype/locus/storage_provider.py` for the P6.1 provider-level
  filesystem/S3-compatible composition and common conformance properties;
- `prototype/locus/provider_gateway.py` for the P6.2 exact admitted provider
  operations and AWS prefix-policy boundary;
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

D018 requires a registry of independent Yi and aPPSS adapters. Enrollment and
successor creation take one explicit approved suite/profile selection before
suite setup. Recovery does not take a free suite choice: it dispatches only to
the suite authenticated in `RecoveryContext` and the descriptor. Both adapters
return opaque `S_R` bytes to the unchanged HKDF/AES caller; they do not share
native state, messages, password domains, or compromise semantics. The common
conformance harness runs both adapters at 2-of-3 and 3-of-5 under the exact
matched P6.3 outer conditions.

`RecoveryRequest`, `RecoveryResponse`, and `RecoveryClientSession` are distinct
opaque typed boundaries for P3/P4 transport integration. Their payloads are
redacted from object representations. P1.3 does not invent a generic wire
envelope or serialize client-session state. Multi-phase Yi and aPPSS message
semantics remain owned by their suite adapters and later versioned schemas.

### Independent recovery-suite adapters

`YiTpassRecoveryAdapter` remains the frozen compatibility adapter. It:

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

`AppssRecoveryAdapter` separately consumes only the assigned P5A.1 aPPSS
formats and native objects. Its central `initialize` method is explicitly a
unit fixture, not distributed-initialization evidence. The P5A.3/P5A.4 network
client keeps each OPRF blinder transient, validates every response binding,
initializes through all `n` authenticated holders, installs one common public
state, and recovers through exactly `k` authenticated holder endpoints. Each
holder generates and persists only its own OPRF key. The registry uses the
selector only for new epochs; recovery dispatches from one authenticated suite
identifier and never tries the other adapter.

Both adapters return their native high-entropy output to `suite_backup.py`,
which applies the same existing HKDF-SHA-256 and AES-256-GCM functions and
preserves the same protected-key interface. Their password domains, native
state, wire messages, compromise behavior, and errors remain disjoint.

## CuePolicy and Resolver boundaries

`CuePolicy` maps structured input to `CuePolicyResult(policy_id,
canonical_bytes)` or fails. Its public `CuePolicyMetadata` declares input
category/shape, cardinality, resolver profile, member ordering domain,
ambiguity, and duplicate behavior. `FrozenLocationPersonCuePolicy` delegates directly
to the existing `canonical_recovery_input` function. It does not alter any
validation, ordering, canonical bytes, error, or identifier.

P5.1 exposes one typed `FROZEN_LOCATION_PERSON_POLICY` instance and routes
deployment provisioning/recovery, same-membership successor creation, the
synthetic walkthrough, and resolver-produced inputs through its `process`
method. The legacy function remains the internal compatibility implementation
and direct vector-test oracle; no application path outside `cue_policy.py`
calls it directly.

P5.3 adds independent quantized-coordinate-set, canonical-phone-set, and
canonical-email-set adapters plus `DEFAULT_CUE_POLICY_REGISTRY`. Exact lookup
never guesses a policy from input shape, and cross-policy values fail rather
than being reinterpreted. The registry changes no recovery suite, password
domain, protected-key generation, HKDF, AES, backup, or storage behavior.

`Resolver` maps one bounded provider result to `ResolverResult` or fails.
`DeterministicResolverAdapter` maps the existing deterministic fixture into
structured cues and invokes the same frozen policy instance, binding its output
to the frozen location-person policy. P5.4's `NoResolverAdapter` accepts only
the three direct-input policy identifiers, invokes the exact selected adapter
once, and exposes no discovery, alternative enumeration, provider metadata, or
recovery-suite retry path.

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
| `ApplicationStorageGateway` | Validate and execute one exact admitted storage operation | P3.4 checks operation, prefix, request digest, proof, and replay state; P6.2 supplies the concrete provider backend for backup, descriptor, bundle, and pointer roles |
| `StorageProvider` | Keep backup, descriptor, bundle, and current-pointer roles distinct while exposing one provider-conformance boundary | P6.1 filesystem and S3-compatible composites pass the same full role suite; nonlocal profiles require TLS and no profile requires listing |
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

This represents either P6.3 topology without conflating its parameters: five
authorizers and 4-of-5 authorization, with either three holders/2-of-3 recovery
or five holders/3-of-5 recovery. The frozen Compose deployment remains Yi-only
and is not reinterpreted. The paired profiles use distinct selector/backup and
aPPSS v2 formats for the second topology.

`PartyEndpointSetup` is public, secret-free deployment input rather than
recovery-suite state. It binds exactly parties 1--5 to canonical advertised
hosts and ports. The same-host tier is fixed to the five Compose service names;
the separate-network-host tier requires five distinct nonlocal addresses. The
provisioner uses the checked endpoints consistently for certificate SANs,
client and native-peer directories, and listener ports. Loading a five-host
file configures those identities but does not distribute services or prove
host or administrative separation.

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

P4.3 implements the stricter client-side sequencing boundary as
`DurableSuccessorPublication` and `SuccessorPublicationBackend`. The durable
journal contains only the exact public operation binding, digests, explicit
rotation choice, and current phase. Backend effects receive deterministic
idempotency keys; prepared-package recovery verification precedes the frozen
lifecycle's atomic retire/activate operation. No protected-key bytes, recovery
input, suite secret, wrapping key, party state, or capability is serializable
through this interface.

P5A.5 supplies a concrete suite-neutral backend for that boundary. One explicit
selector prepares either suite under a signed descriptor and backup v5.
Successor preparation recovers the predecessor through its authenticated suite,
creates fresh state under one explicit successor suite, and verifies the same
protected-key digest before the P4.3 activation phase. The journal commits the
successor backup/configuration/descriptor digests; the descriptor commits the
suite. It serializes no recovery input, protected key, recovery secret, or party
state. This component is not wired into the released Yi application path until
the P5A release gate passes.

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

`prototype/tests/test_system_interfaces.py` and the P5A.3 suite tests verify:

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
- public client-state snapshots contain no secret fields;
- both independent adapters satisfy the common recovery-secret contract;
- selector and descriptor dispatch reject unsupported/cross-suite state with
  no fallback;
- backup v5 uses one common protected-key/HKDF/AES path for Yi and aPPSS; and
- correct and wrong aPPSS recovery cross distinct pinned mutual-TLS party
  subprocesses whose boot files contain no OPRF key; and
- distributed initialization verifies exact public epoch/certificate bindings,
  returns only after all ready acknowledgements, and rejects changed
  caller/route/body idempotency reuse and partial installation; and
- all four same-suite/cross-suite successor directions preserve the
  protected-key identity, reject mixed old/new or cross-suite state, and resume
  every selected P4.3 publication effect without double activation.

These tests establish interface compatibility and bounded implementation
behavior. They do not prove aPPSS security, release selectable-suite
enrollment, provide retained deployment evidence, or pass the P5A.7 review gate.
P3.2 separately adds remote initial Yi enrollment without
changing the frozen P1 interface tests.

## Manuscript and evidence boundary

P1.3 changes no manuscript source or retained evidence. It creates no new
paper claim. Frozen v2 results remain evidence only for the exact inherited Yi
profile, not for the new interface architecture. Later implementation and
evidence profiles require their own identifiers, schemas, provenance, and
owner-gated manuscript deltas.
