# Information-Flow Contract

Status: P1.5 security and information-flow matrices implemented on 2026-08-01.
This is a design/evidence contract. Entries marked as gated do not claim that
the corresponding descriptor, admission, aPPSS, UI, provider, multi-host, or
replacement behavior is implemented or evidenced.

D020 activates the already implemented selectable-suite application/component
interface after provisional internal mapping acceptance. This does not promote
any gated paired-deployment or retained-evidence cell, and independent human
validation remains pending.

This table is the starting contract. Update it before implementing new roles or
retained observations.

Legend:

- `E` — allowed only ephemerally.
- `P` — allowed to persist.
- `F` — forbidden.
- `O` — role may observe as an explicit policy consequence.

| Material | Enrollment client | Backup store | Descriptor store | Resolver | TPASS holder | Authorizer-only | Recovery client |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Raw structured cues | E | F | F | O when used | F | F | E |
| Resolver queries/results | E | F | F | O when used | F | F | E |
| Selected provider IDs | E or F by policy | F | F | O | F | F | E or F |
| Canonical policy output `Z_M` | E | F | F | F | F | F | E |
| TPASS password input `p_M` | E | F | F | F | F | F | E |
| TPASS public parameters | P | P | P | F | P | P if required | P |
| One party's TPASS state | Transient during provisioning | F | F | F | P: own only | F | F |
| Complete TPASS setup states | E only | F | F | F | F | F | F |
| Recovered group secret `S_R` | E | F | F | F | F | F | E |
| Wrapping key `K_wrap` | E | F | F | F | F | F | E |
| Plaintext protected key | E/input | F | F | F | F | F | E/output |
| Encrypted backup | P or transient | P | Locator/digest only | F | Reference/digest only | Reference/digest if required | P or transient |
| Immutable recovery-bundle ZIP | E or P during publication | P in bundle-capable provider | P only when the same provider implements the bundle interface | F | Locator/digest only | Locator/digest if required | E or P during retrieval |
| Bundle manifest | E or P | P with bundle | P with descriptor/bundle | F | Safe digest only if required | Safe digest only if required | E or P |
| Backup identifier/epoch/digest | P | P | P | F | P | P | P |
| Policy identifier/public rules | P | P | P | Policy-dependent | P | P | P |
| Endpoint identities/membership | P | Public as required | P | F | P | P | P |
| Admission credential/token | E | F | F | F | F except validation input | F except validation input | E |
| Short-lived proof-key-bound storage capability | E | F behind gateway | F behind gateway | F | F | F unless separately acting as issuer | E |
| Local audit state | F after request | F | F | F | P: own | P: own | F |
| Descriptor signature/current pointer | P | F unless co-hosted adapter | P | F | P as required | P as required | P |

## Phase-by-view matrix

This matrix crosses every P1.5 phase with every required operational,
adversary, or evidence view. A view is not necessarily a protocol actor. In
particular, coalition and matching-combined entries describe bounded snapshots
that later evidence must construct.

Legend:

- `T` — may participate or observe allowed values transiently.
- `P` — may retain only the bounded state permitted by the material table and
  role invariants.
- `M` — may observe bounded role/network metadata but no protected payload.
- `V` — adversary/evidence view assembled from exact persistent state, not an
  additional runtime role.
- `G` — future phase-gated behavior; no implementation/evidence claim yet.
- `—` — no designed flow or participation in that phase.

View abbreviations:

- `CLD`: cloud/backup provider;
- `DS`: descriptor/current-pointer store;
- `GW`: application storage gateway;
- `RES`: resolver;
- `B<k`: every evaluated below-threshold party coalition;
- `A=k`: every exact-threshold aPPSS coalition used by C25;
- `COM`: matching cloud/descriptor plus below-threshold coalition;
- `A0`: enrollment client after persistent-state disposal;
- `B0`: clean client before cue entry;
- `B1`: clean client after cue entry;
- `IDP`: identity/admission issuer and verifier; and
- `NET`: network-role metadata.

| Phase | CLD | DS | GW | RES | B<k | A=k | COM | A0 | B0 | B1 | IDP | NET |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Enrollment | `T/P` encrypted backup | `G` descriptor/bundle | `G` exact writes | `T/M` if policy uses it | `T/P` own state | `G` aPPSS setup | `—` | `—` | `—` | `—` | `G` admission | `M` |
| Persistent-state disposal | `P` public/encrypted state | `G/P` public state | `—` no request retention | `—` | `P` own state | `G/P` own aPPSS state | `V` exact union | `V` disposed-state surface | `—` | `—` | `G/P` replay metadata only | `M` |
| Bootstrap | `T/P` exact object read | `G/T/P` pointer/bundle | `G/T` admitted read | `—` | `T/P` current summaries | `—` | `V` pre-cue public union | `—` | `T` approved bootstrap only | `—` | `G/T` admission | `M` |
| Recovery | `T/P` ciphertext read | `G/T/P` authenticated metadata | `G/T` exact read | `T/M` if policy uses it | `T/P/V` selected coalition | `V` fixed compromised-threshold regression view | `V` matching union | `—` | `T` before cue | `T` secret path | `G/T` admission | `M` |
| Successor publication | `T/P` new immutable object | `G/T/P` new descriptor/pointer | `G/T` exact create/CAS | `—` | `T/P` readiness/current state | `G` aPPSS successor | `V` crash snapshots | `—` | `—` | `T` active client | `G/T` admission | `M` |
| Party replacement | `G` | `G` | `G` | `—` | `G` old/new sets | `G` if aPPSS profile | `G/V` transition snapshots | `—` | `—` | `G` active client | `G` | `G/M` |

### Enrollment phase contract

The trusted active enrollment client may transiently hold the complete secret
path and complete suite setup output. It sends each holder only that holder's
recipient-bound state and publishes only the encrypted backup and approved
public metadata. Resolver use is policy-specific. The network may observe
bounded endpoint, timing, and size metadata but not plaintext provisioning
payloads. P3 must replace direct-volume provisioning before an authenticated
confidential enrollment-transport claim is available.

### Persistent-state disposal phase contract

After enrollment, Client A's allowed durable output is limited to an optional
public receipt and explicitly approved public references. Raw cues, selected
resolver records, `Z_M`, password input, complete suite setup state, `S_R`,
`K_wrap`, plaintext private-key bytes, credentials, and transient provisioning
messages are forbidden in its persistent surface. Cloud and parties retain only
their role-specific state. This phase supports bounded state deletion and
isolation testing, not forensic secure erasure.

### Bootstrap phase contract

Client B begins with the installed application, app-pinned issuer root, fresh
session/proof key, the approved admission/bootstrap input, and optionally a
public receipt or recovery handle. It authenticates subject scope, current
pointer, exact bundle/descriptor digests, issuer/signature, suite, policy,
membership, endpoints, configuration, and party-consistent current state before
cue entry. It receives no Client A state, provider credential, cue, candidate
hint, password-derived authenticator, or self-authenticating trust root. The
coordinated rollback of every authoritative source remains outside the claim.

### Recovery phase contract

Only the active clean client may combine entered cues, canonical policy output,
suite password input, threshold responses, `S_R`, `K_wrap`, ciphertext, and the
plaintext protected key. Remote roles receive only their exact admitted and
suite-bound request. Final AEAD/cue success is not disclosed to the issuer,
gateway, resolver, cloud, or parties. Coalition views are read-only,
networkless, synthetic-state experiments; they are not online guessing tools.
P5A.6 implements one fixed in-memory paired 2-of-3 regression for these views.
It emits only aggregate counts and categories, has no configurable input
interface, and is not retained evidence or a claim that tests prove either
suite's cryptographic theorem.
For new enrollment or successor creation, the client may explicitly select an
approved Yi or aPPSS profile before suite setup. Recovery instead uses only the
suite authenticated in the descriptor; suite choice is public metadata and is
never derived from cues or used as a fallback.
For direct coordinate, phone, and email policies, `NoResolver` performs no
lookup: it invokes the exact selected policy once inside the client. The frozen
composite policy remains bound to the deterministic resolver fixture. Neither
adapter enumerates alternatives or retries a recovery suite.

### Successor publication phase contract

The active client prepares and verifies fresh successor party state, immutable
backup/bundle, signed descriptor, and current summaries before current-pointer
activation. P4.3 verifies recovery against the prepared successor package while
the predecessor remains authorized, then invokes the frozen party lifecycle's
atomic predecessor-retirement/successor-activation transaction. Exact retries
are derived from one immutable public binding, and the durable journal stores
only public metadata and digests. This does not authorize automatic downgrade,
share conversion, general replacement, or global rollback-resistance claims.

### Party replacement phase contract

D011 defers party replacement until after the selectable-suite and paired-profile
work. A later owner-approved profile must distinguish old/new authorizers, suite
holders, threshold, quorum, endpoint identities, recipients, readiness,
activation, and retirement. Until then, every party-replacement cell is a
design/evidence requirement rather than implemented behavior.

## Coalition and combined-view matrix

| Evaluated profile/view | Required coalitions | Included public/persistent state | Permitted conclusion |
| --- | --- | --- | --- |
| Frozen Yi 2-of-3 below threshold | `{P1}`, `{P2}`, `{P3}` when new-profile evidence is collected; retained v2 covers only its exact recorded one-party boundary | Own Yi state, exact public parameters, configuration/epoch binding, local audit state, and matching cloud state only for C05 | No local offline predicate under the frozen Yi assumptions and exact captured boundary; never an aPPSS result |
| First aPPSS 2-of-3 below threshold | `{P1}`, `{P2}`, `{P3}` | Own independent OPRF state, party/index binding, public `omega`, exact configuration/epoch metadata, audit state, and matching cloud/descriptor state for C24 | Conditional below-`k` no-local-predicate statement after theorem/profile review; no adaptive, side-channel, or online-interaction claim |
| First aPPSS exact threshold | `{P1,P2}`, `{P1,P3}`, `{P2,P3}` | Exact two server states plus public `omega`, suite/epoch/configuration, and the fixed aggregate-only candidate-test harness | C25 offline dictionary-test capability; not direct release of `S_R` before a correct password guess under the declared conditional-entropy assumption |
| First aPPSS above threshold control | `{P1,P2,P3}` | All server states and the same public/matching state | Confirms the at-or-above-threshold behavior only; results remain separate from exact-threshold rows |
| Matching combined state | One exact cloud/descriptor/gateway snapshot plus one below-threshold coalition from the same suite, backup, epoch, policy, membership, and configuration | Complete union of the declared persistent views, with no client secrets or online honest-server access | C05/C24 only for the exact matching profile; mismatched snapshots are rejection tests, not evidence for the positive claim |

P6.3 assigns the paired Yi/aPPSS 3-of-5 configuration and same-host process
profiles. It does not assign a retained coalition-evidence profile; P8/P9 must
add those rows and paths before claim use. Each comparison pair binds matching
outer conditions, but suite-specific states and results remain separate.
Authorization quorum coalitions are not recovery-suite coalitions and must be
reported separately.

## Claim security-contract matrix

`security-matrix-v1.json`, validated by
`schemas/security-matrix-v1.schema.json`, is the normative P1.5 claim contract.
For every active C01--C26 row in the root `CLAIM-EVIDENCE-MATRIX.md`, it records:

- applicable phases and views;
- protected asset;
- adversary;
- assumptions;
- exact implementation/evidence boundary;
- positive control;
- expected privacy-safe observation; and
- interpretation limit.

The matrix is prospective where the claim/evidence matrix says unsupported or
explicit non-claim. Completing a row does not promote its status. Promotion
still requires the assigned implementation/evidence profile, new results, and
any separately approved manuscript delta.

## Additional rules

- A provider may implement backup and descriptor interfaces in one external
  service, but the logical data contracts remain distinct.
- Under D014, a bundle-capable provider may physically colocate the canonical
  encrypted backup, signed descriptor, and manifest in one immutable bounded
  ZIP. The authenticated mutable current pointer remains outside the ZIP, and
  physical colocation does not permit either logical store to retain prohibited
  material.
- ZIP filenames and manifests contain only registered public names, versions,
  sizes, and digests. They contain no user label, cue, selected record,
  candidate hint, credential, or secret-bearing value.
- Under D015, an application-operated S3 namespace is scoped by the admitted
  subject and backup identifier. AWS S3 is the optional external profile. The
  application operator and provider may observe namespace, object-key, timing,
  size, and access metadata; S3 access control is not the descriptor trust
  root.
- Clients receive no AWS access key and need no personal AWS account. The
  application storage gateway validates short-lived proof-key-bound
  authorization for the exact allowed prefix and operation. Normal recovery
  has no bucket-list permission.
- Public metadata must be reviewed for linkability and enumeration even when it
  is not secret.
- A role may not derive permission to persist a value merely because it observed
  it transiently.
- Logs, telemetry, screenshots, traces, dumps, exception messages, and UI state
  are storage channels and follow the same table.
- Positive controls must prove that audits detect deliberately inserted
  fictional forbidden material.
- Network-flow evidence records categories and byte counts, not payloads.

## Application storage gateway view

The D015 application storage gateway is a stateless protocol adapter within the
cloud-side compromise view. It may transiently observe the proof-key-bound
storage capability, pseudonymous subject scope, backup identifier, epoch,
exact object key, operation, encrypted backup, signed descriptor, current
pointer, manifest, and bundle bytes required for that operation. It may hold a
narrow server-side provider credential for the application namespace.

It must not receive raw or canonical cues, TPASS password input, party state,
recovered group secret, wrapping key, or plaintext private-key material. It
exposes no bucket listing to the client, emits no provider exception text, and
persists no request body, capability, or client proof material in logs or audit
records. Its compromise does not turn provider bytes into authenticated LOCUS
configuration and is included in future cloud-plus-descriptor/bundle snapshot
evidence.

P6.2 implements this boundary locally as
`LOCUS-application-storage-gateway-v1`. The existing P3.4 verifier runs before
the provider backend, and the backend rechecks exact logical keys, immutable
digests, bundle length, backup/epoch binding, and replacement-pointer binding.
The AWS specialization accepts explicit server credentials only and its policy
contains no listing action. These are component facts; the opt-in AWS gate has
not been executed and no real-provider observation is claimed.

## Clean-client boundary

Client B may receive only the inputs approved in D001--D004 and the implemented
local D004 admission decision, such as:

- installed application and pinned trust root;
- admission/identity authentication capability and a short-lived scoped
  storage capability;
- optional recovery receipt or handle;
- authenticated current pointer and immutable recovery bundle;
- user-entered fictional cues;
- fresh session/proof key.

It must not inherit:

- Client A volume or environment;
- coordinator private key from enrollment;
- long-lived or account-wide storage-provider credentials;
- deployment configuration not obtainable through the approved bootstrap;
- raw cues or canonical output;
- protected private key;
- TPASS group secret or wrapping key;
- party secret state.
