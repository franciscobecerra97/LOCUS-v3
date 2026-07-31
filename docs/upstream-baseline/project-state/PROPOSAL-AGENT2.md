# AGENT2.md — LOCUS ASIACCS 2027 Improvement Agent

## 0. Purpose and relationship to the existing project

This file is an **improvement agent** for the existing LOCUS Codex project. It is intended to be read **together with `AGENT.md` and `PLAN.md`**, not to replace them.

Use this file when working on the second-stage revision whose goal is to reduce the main rejection risks identified during an ASIACCS-style review of the current paper:

> **LOCUS: A Cue-Policy Interface for Storage-Separated Threshold Private-Key Recovery**

The existing paper is technically careful and well scoped, but it is at risk of rejection because the main systems novelty can be perceived as too close to a standard TPASS composition, while the evaluation is currently too narrow to compensate for that concern.

`AGENT2.md` defines the **new strategy, constraints, target architecture, technical corrections, evaluation goals, and paper-positioning rules** for the improvement phase.

`PLAN2.md` is the live execution plan for implementing this strategy. Every substantial implementation or paper change made under this agent must be reflected in `PLAN2.md`.

---

# 1. Mission

Transform LOCUS from a carefully scoped research prototype into a **convincing end-to-end reference system for threshold private-key recovery after device loss**, centered on a reusable and demonstrably general **CuePolicy abstraction**.

The revised paper must make a strong, defensible claim:

> LOCUS is an end-to-end private-key recovery system that converts deployment-defined human-facing recovery information into stable, versioned cryptographic input, then uses threshold password-authenticated secret sharing to recover independently generated keying material without placing an offline cue-testing verifier in cloud storage or below-threshold recovery-party state.

The paper must **not** claim that a particular cue family is memorable, high entropy, or user-optimal. Those questions belong to future human-subject research.

The current paper should be positioned as a **security systems / applied cryptography paper**, not as a usability paper.

---

# 2. Primary rejection risks to fix

All work in this revision should be prioritized against the following risks.

## RISK-A — Novelty can appear too close to standard TPASS usage

A skeptical reviewer may interpret the current architecture as:

> “Use TPASS with a human-supplied password to recover a random secret, derive an encryption key, and store the ciphertext separately.”

This is not enough by itself to establish strong systems novelty.

### Required response

Make **CuePolicy** the central systems contribution and demonstrate that it solves a real, under-specified systems problem:

> How does a deployment convert human-facing semantic recovery information into deterministic, stable, versioned bytes across enrollment and fresh-device recovery without exporting raw cues or a stored testing verifier?

The paper must explicitly acknowledge that LOCUS does not invent TPASS and does not claim the basic password-to-random-secret composition as novel.

---

## RISK-B — CuePolicy generality is claimed more strongly than demonstrated

The current prototype implements only one concrete location-person policy.

### Required response

Implement **multiple qualitatively different CuePolicy modules** behind one common interface and one unchanged TPASS layer.

At minimum, the revision should aim for:

1. `LocationPersonContact-v1`
   - Human-facing location + person/contact association.
   - Resolver-backed location selection.
   - Canonical location representation independent of a provider identifier where practical.
   - Person component represented by a stable normalized contact channel such as constrained email or E.164 phone number.

2. `StructuredPhrase-v1`
   - Human-entered phrase/sentence or structured textual cue.
   - Explicit Unicode normalization, whitespace rules, case policy, field ordering, length constraints, and versioning.

3. A third policy with a **different resolver/privacy model**, preferably one of:
   - `LocalEventLabels-v1`
   - `LocalLabels-v1`
   - another no-provider/local-first policy

The purpose is **not** to compare memorability. The purpose is to show that heterogeneous human-facing inputs can conform to one CuePolicy contract and feed the same cryptographic recovery system.

---

## RISK-C — Evaluation is too narrow and too same-host

The current implementation provides useful correctness and storage-boundary evidence but is mostly same-host and does not demonstrate a realistic clean-device lifecycle or independently hosted parties.

### Required response

Build and evaluate a realistic end-to-end deployment that includes:

- a user-facing client;
- a real or realistic cloud backend;
- genuinely separated recovery-party services;
- complete client-state destruction after enrollment;
- clean-client recovery;
- recovery bootstrap/discovery;
- multiple threshold profiles where feasible;
- realistic network measurements;
- failure and unavailable-party experiments;
- artifact-driven reproducibility.

---

## RISK-D — Fresh-device bootstrap/admission is currently assumed, not implemented

The current recovery algorithm assumes the fresh client already knows the exact cloud reference and authenticated party endpoints.

### Required response

Define and implement an explicit **fresh-device bootstrap model**.

A clean client must be able to answer:

- What recovery configuration belongs to this user/backup?
- Which CuePolicy version is active?
- Where is the encrypted backup?
- Which parties belong to the enrolled recovery set?
- What threshold applies?
- How are party endpoints authenticated?
- What non-secret handle or account context is required to locate the recovery state?

This must be explicit in the architecture and threat model.

---

## RISK-E — Online attempt control is incomplete

LOCUS moves residual guessing into online threshold interactions, but the current prototype does not establish a rollback-resistant global attempt bound.

### Required response

Choose one of two strategies and keep the paper consistent:

### Preferred scope-preserving strategy

Treat global attempt control as **orthogonal deployment infrastructure** and narrow the LOCUS claim to:

> below-threshold storage compromise does not create an offline cue-testing oracle; guesses must be exercised through online threshold recovery.

Retain the rollback counterexample as a useful negative result if it strengthens the analysis, but do not present the incomplete ledger as a core solved component.

### Optional stronger strategy

If time permits, add a separately justified monotonic/global attempt mechanism and evaluate it. Do this only if it can be implemented and argued convincingly without creating a much larger trust problem.

Do **not** weaken the paper by making strong rate-limiting claims that the implementation cannot establish.

---

# 3. End-to-end reference system to build

The new system should demonstrate the entire recovery lifecycle from first setup to recovery on a fresh client.

## 3.1 User-visible phases

The application should expose four high-level phases:

1. **Setup / Key Generation or Import**
2. **Enrollment / Backup**
3. **Device Loss / Local-State Destruction**
4. **Fresh-Device Recovery and Successor Re-enrollment**

The UI is useful only if it exposes and validates the real system architecture. A polished GUI alone is not a research contribution.

---

## 3.2 Correct enrollment flow

The implementation must follow the paper’s actual cryptographic construction.

1. Generate or import the private key `sk_U` to protect.
2. User selects a supported CuePolicy.
3. User provides structured recovery input `M` through the UI.
4. The active CuePolicy performs:
   - optional resolution;
   - validation;
   - normalization;
   - canonical ordering;
   - ambiguity handling;
   - canonical encoding;
   - version binding.
5. Produce canonical policy output `Z_M` or fail closed.
6. Generate fresh public backup identifier `bid` and explicit epoch `e`.
7. Construct the recovery identity `ID_R` from the protocol version and `bid`.
8. Derive the TPASS password input `p_M` from `ID_R` and `Z_M` using the protocol’s domain-separated scalar hash.
9. Select an enrolled recovery-party set and threshold `(t,n)`.
10. Run `TPASS.Setup(ID_R, p_M, t, n)`.
11. TPASS returns:
    - public parameters;
    - one server state for each TPASS party;
    - independently generated group secret `S_R`.
12. Generate the recovery nonce required by the backup format.
13. Derive `K_wrap` from `S_R` using the defined HKDF construction.
14. Encrypt `sk_U` under `K_wrap` using AEAD and authenticated backup metadata.
15. Construct the canonical cloud backup object and digest/bindings.
16. Upload the encrypted backup object to the configured cloud backend.
17. Provision each recovery party with **only its own TPASS state and required public bindings** over authenticated/confidential setup channels.
18. Erase client-local enrollment secrets including:
    - raw cues;
    - resolved provider objects not required for display during the session;
    - canonical cue output `Z_M`;
    - cue-derived password `p_M`;
    - recovered/generated group secret `S_R`;
    - wrapping key `K_wrap`;
    - setup randomness.
19. Optionally expose a **Research State Inspector** showing redacted state placement based on the actual persisted system state.

### Critical correctness rule

Do **not** independently generate a fresh symmetric backup key and then protect that key with TPASS.

The paper’s construction is:

`cues -> Z_M -> p_M -> TPASS -> S_R -> HKDF -> K_wrap -> encrypt(sk_U)`

The recovered TPASS group secret is what deterministically yields the wrapping key.

---

## 3.3 Device-loss simulation

The system must support a convincing clean-device experiment.

After enrollment:

- terminate the original client;
- delete its entire local persistent state, not just the private-key file;
- verify that no LOCUS-maintained cue verifier, `Z_M`, `p_M`, `S_R`, `K_wrap`, or protected private key remains locally;
- launch recovery in a **new process/container/VM/device** that does not mount or inherit the old client volume.

Prefer wording such as **“clean-client recovery”** or **“fresh-device recovery”** over a superficial “simulate device loss” mode.

---

## 3.4 Fresh-device bootstrap

Introduce an explicit non-secret recovery/bootstrap object, tentatively named `RecoveryDescriptor`.

Its exact design may evolve, but it should contain enough public information for a fresh client to locate the recovery system without containing a cue-testing verifier or secret recovery value.

Potential fields:

- protocol version;
- public recovery handle;
- `bid`;
- active epoch;
- CuePolicy identifier/version;
- cloud backend identifier and object locator;
- recovery-party identities;
- recovery-party authenticated endpoints or pinned authentication material;
- threshold `t` and party count `n`;
- public protocol metadata needed before contacting parties.

It must contain **none** of:

- raw cues;
- canonical cue output `Z_M`;
- cue-derived password `p_M`;
- TPASS secret shares;
- `S_R`;
- `K_wrap`;
- a cue/password verifier.

The paper must explicitly state **what the user or fresh client still needs after device loss**. Possible models include:

- a non-secret recovery handle + remembered cues;
- authenticated cloud-account access + remembered cues;
- another explicitly documented discovery mechanism.

Do not leave this implicit.

---

## 3.5 Correct recovery flow

1. Launch a completely clean LOCUS client.
2. Obtain or enter the non-secret recovery handle/account context.
3. Retrieve and validate the RecoveryDescriptor.
4. Discover the enrolled cloud reference, policy version, recovery parties, threshold, and endpoint authentication material.
5. Download the encrypted backup object.
6. Validate:
   - canonical envelope;
   - exact backup identity/epoch;
   - digest/bindings;
   - protocol parameters;
   - policy version;
   - supported deployment profile.
7. Ask the user for the cues required by the enrolled CuePolicy.
8. Resolve, validate, normalize, and canonicalize the candidate input into `Z_M'` or fail.
9. Derive `p_M'` using the **enrolled recovery identity**.
10. Select a healthy threshold subset from the **enrolled party set**.
11. Perform any deployment-authorized/countable recovery admission step that is actually implemented.
12. Run `TPASS.Recover(...)`.
13. On success, obtain `S_R'`.
14. Derive `K_wrap'` from `S_R'`, recovery nonce, `bid`, epoch, and the defined domain-separated HKDF inputs.
15. Authenticate/decrypt the cloud ciphertext.
16. Return the **original protected private key `sk_U`**.
17. Treat successful recovery as the beginning of a successor recovery epoch.
18. If loss may indicate compromise, optionally rotate the protected private key and retire the previous recovery state.

### Critical correctness rule

A fresh client does **not** generate a new protected private key before attempting recovery.

Any new protected key is generated only after recovery if key rotation is desired.

---

# 4. CuePolicy architecture

## 4.1 Common interface

The implementation should make CuePolicy a first-class module, not form-specific application logic.

Conceptual interface:

```text
CuePolicy
  id() / version()
  resolve(input, context) -> resolved | error
  validate(resolved) -> valid | error
  normalize(resolved) -> normalized | error
  canonicalize(normalized) -> Z_M | error
  public_context() -> non-secret policy metadata
  conformance_vectors() -> deterministic test vectors
```

The exact code API may differ, but the research contract must capture:

- accepted input structure;
- cardinality;
- resolver behavior;
- normalization rules;
- canonical ordering;
- duplicate behavior;
- ambiguity behavior;
- drift behavior;
- versioning;
- canonical encoding;
- fail-closed semantics.

---

## 4.2 Location-person policy guidance

The existing UI for location-person cues is valuable and should be reused, but the underlying cryptographic representation must be designed for long-term stability.

### Location

The UI may use Google Maps or another provider for human-facing resolution, but avoid making a provider-specific Place ID the permanent long-term secret unless the policy explicitly chooses and documents that tradeoff.

Preferred pattern:

`human place selection -> resolver -> canonical geographic representation -> versioned encoding`

Provider identifiers should usually be treated as resolver metadata/display data rather than the cryptographic secret representation.

### Person

For the primary reference policy, prefer stable normalized contact channels such as:

- constrained canonical email;
- E.164 phone number.

Social-media profile URLs may be supported as a separate experimental provider-dependent policy, but they have stronger long-term drift, reassignment, privacy, and resolver-dependence risks.

---

## 4.3 UI wording rules

The UI should say **recovery cues**, not password.

Avoid text such as:

> “the Google place ID is stored internally for hashing”

Prefer wording such as:

> “LOCUS resolves your selection and converts it into a canonical representation according to the active recovery policy.”

The system should not imply that raw cues or provider identifiers remain stored after enrollment unless they truly do.

Normal UI should not expose `p_M`.

An optional developer/research panel may show:

- policy ID/version;
- normalized/canonical values;
- validation outcome;
- ordering result;
- redacted storage destination;
- protocol phase.

---

# 5. Cloud storage strategy

Abstract cloud storage behind a provider-independent interface.

Conceptual interface:

```text
CloudBackend
  put_backup(...)
  get_backup(...)
  put_descriptor(...)
  get_descriptor(...)
```

The existing S3-compatible backend can remain.

Add at least one real cloud-backed deployment if feasible. If using iCloud/CloudKit, explicitly define whether recovery assumes:

- access to the user’s private iCloud database/account; or
- retrieval of a public/non-confidential encrypted object via a public handle.

The paper must not silently depend on recovering iCloud credentials through LOCUS if iCloud access is itself required before LOCUS can start.

Cloud confidentiality must not be trusted for LOCUS security claims. The encrypted backup may be assumed obtainable by an adversary.

---

# 6. Recovery-party deployment

Move beyond same-host-only evidence.

Target implementation/evaluation should support multiple threshold profiles when practical, e.g.:

- 2-of-3;
- 3-of-5;
- optionally 4-of-7.

At least one evaluation configuration should place recovery parties on **genuinely distinct hosts or VMs**, preferably with independent network paths/administrative separation.

Party-selection UI may select from a registry/configuration of known recovery providers/party identities, but do not let an untrusted user input silently redefine the authenticated party set for an existing enrollment.

The paper must distinguish:

- TPASS party selection during enrollment;
- threshold subset selection during recovery;
- authenticated endpoint discovery;
- operational admission/rate control.

---

# 7. Evaluation strategy

The revised evaluation should be organized around explicit research questions.

## RQ1 — Does CuePolicy provide a reusable systems boundary?

Evaluate multiple policy families with one shared conformance framework.

Test:

- deterministic equivalent-input mapping;
- canonical ordering;
- format normalization;
- Unicode/text normalization where relevant;
- provider display-name changes;
- provider reindexing where supported;
- duplicate rejection;
- ambiguity rejection;
- missing-record failure;
- unsupported version failure;
- cross-policy separation;
- cross-client/test-vector reproducibility.

Do not interpret these tests as memorability evidence.

---

## RQ2 — Can LOCUS recover after complete client loss?

Demonstrate:

`Client A enrollment -> destroy all Client A local state -> clean Client B bootstrap -> cue entry -> threshold recovery -> decrypt original sk_U`

Verify that the clean client does not inherit hidden enrollment secrets.

---

## RQ3 — Does realistic state separation preserve the intended offline-oracle boundary?

Inspect/capture real persisted state for:

- cloud backend;
- each recovery party;
- optional resolver logs where relevant;
- client before and after erasure.

Check absence of:

- raw cues;
- `Z_M`;
- `p_M`;
- `S_R`;
- `K_wrap`;
- unintended verifiers.

Retain positive controls where useful.

Snapshot tests may remain, but should be described as implementation-boundary evidence rather than cryptographic proof.

---

## RQ4 — What is the practical recovery cost?

Measure at least:

- enrollment latency;
- successful recovery latency;
- wrong-input recovery latency;
- unavailable-party recovery;
- bytes sent/received by role;
- cloud object size;
- persistent storage size;
- threshold-scaling cost;
- realistic network/WAN cost where possible;
- multiple threshold profiles;
- optional moderate concurrency if implementable.

Report hardware/network/environment details precisely.

---

## RQ5 — What is the resolver privacy boundary?

For resolver-backed policies, instrument or inspect outbound requests and document what the provider can observe.

Show that raw resolver queries may be visible to the resolver but should not be forwarded to cloud storage or recovery parties as protocol state.

Contrast resolver-backed and local/no-provider policies.

---

# 8. Security claim discipline

Maintain the existing paper’s strongest trait: careful claim scoping.

The revised paper must continue to distinguish:

- storage privacy vs resolver privacy;
- offline guessing vs online guessing;
- below-threshold compromise vs threshold compromise;
- correctness vs implementation evidence;
- artifact tests vs cryptographic proofs;
- client compromise vs storage compromise;
- availability failures vs confidentiality failures.

Do not claim:

- that human cues are high entropy;
- that the reference policies are memorable;
- that a UI implies usability;
- globally enforced rate limiting unless actually established;
- rollback resistance unless actually established;
- production-readiness or independent cryptographic audit unless true.

---

# 9. Paper positioning strategy

## 9.1 Central narrative

The revised introduction should focus on the missing systems boundary:

1. TPASS can protect a random recovery secret behind a human-supplied password.
2. Real recovery systems still need a durable way to convert human-facing semantic input into stable protocol input after device loss.
3. Naive representations can be ambiguous, provider-dependent, drifting, or create stored verifiers.
4. LOCUS introduces CuePolicy as the explicit versioned boundary.
5. LOCUS integrates that boundary into a complete storage-separated recovery system with clean-device recovery.

---

## 9.2 Contribution hierarchy

Prioritize contributions approximately as follows:

1. **CuePolicy abstraction**
   - formal/explicit contract;
   - multiple implemented policy families;
   - fail-closed/versioned behavior;
   - reproducible conformance vectors.

2. **End-to-end recovery architecture**
   - fresh-device bootstrap;
   - cloud/party state separation;
   - lifecycle and re-enrollment;
   - clear authority/trust boundary.

3. **Reference implementation**
   - UI/client;
   - native TPASS core;
   - cloud backend(s);
   - independently hosted party services;
   - recovery descriptor/bootstrap mechanism.

4. **Evaluation**
   - clean-device recovery;
   - multi-policy conformance;
   - distributed/WAN behavior;
   - state-boundary evidence;
   - performance/failure measurements.

5. **Security analysis**
   - inherited TPASS assumptions;
   - offline-oracle claims;
   - resolver boundary;
   - online residual risk;
   - lifecycle and rollback limits.

Do not lead with storage separation as if the basic TPASS-to-encrypted-backup composition were the primary novelty.

---

# 10. Artifact and reproducibility requirements

The revision should include an anonymous artifact suitable for ASIACCS review.

Target artifact contents:

- source code;
- CuePolicy modules;
- conformance vectors;
- UI/client code;
- TPASS implementation;
- deployment scripts;
- party service configuration;
- cloud backend abstraction and reproducible local fallback;
- clean-device recovery scripts;
- evaluation scripts;
- raw/aggregate experiment records as appropriate;
- scripts that regenerate paper tables/figures;
- documentation of expected threat boundaries and unsupported production assumptions.

Run at least one clean-host reproduction before submission.

Do not include identifying human data or real personal cues in the review artifact.

---

# 11. Human studies are future work, not missing validation

The revised paper must not frame itself as an incomplete usability study.

Preferred framing:

> LOCUS studies the systems and security boundary that converts deployment-defined human-facing recovery information into reproducible threshold-recovery input while avoiding a stored offline verifier below threshold. Whether a specific cue policy is memorable, comprehensible, or sufficiently unpredictable is a distinct empirical question requiring separate human-subject evaluation.

Future research may study:

- long-term memorability;
- cue-selection behavior;
- reproducibility after months/years;
- user comprehension;
- comparative cue-family performance;
- guessability under public/social knowledge;
- recovery error rates.

No current implementation test may be described as evidence for those properties.

---

# 12. Development priorities

Use this priority order unless `PLAN2.md` records an explicit decision to change it.

## P0 — Architecture correctness and novelty

- formalize the common CuePolicy interface;
- implement multiple policy families;
- define recovery bootstrap/descriptor;
- ensure the enrollment/recovery flow exactly matches the paper’s TPASS construction;
- define the cloud-account/discovery assumption;
- define recovery-party authentication/discovery.

## P1 — End-to-end reference system

- integrate UI;
- real enrollment;
- persistent cloud backup;
- distributed party provisioning;
- full local-state erasure;
- clean-client recovery;
- successor epoch after recovery.

## P2 — Stronger evaluation

- independent hosts/VMs;
- threshold variants;
- realistic network measurements;
- multi-policy conformance;
- state inspection;
- failure tests;
- cross-client/reproducibility evidence.

## P3 — Paper rewrite

- reframe novelty;
- rewrite contributions;
- add system architecture figure;
- add bootstrap/admission section;
- restructure evaluation around research questions;
- strengthen related-work comparison;
- narrow rate-control claims;
- update limitations/open-science/ethics.

## P4 — Submission hardening

- artifact anonymization;
- clean-host reproduction;
- consistency audit between code, algorithms, tables, and claims;
- terminology audit;
- page-budget optimization;
- final ASIACCS compliance check.

---

# 13. Non-negotiable technical invariants

Any code or paper change under this agent must preserve these unless an explicit, documented architectural redesign is approved in `PLAN2.md`.

1. The cue-derived value `p_M` is **not** the encryption key.
2. TPASS recovers independently generated group secret `S_R`.
3. `K_wrap` is derived from `S_R` using the defined KDF.
4. The protected private key is encrypted under `K_wrap`.
5. Cloud storage does not store TPASS secret states.
6. A below-threshold recovery-party view does not include the cloud ciphertext unless cloud compromise is separately assumed.
7. No party record contains a local cue/password verifier.
8. Raw cues, canonical policy output, cue-derived password, recovered group secret, and wrapping key are erased from the client after enrollment.
9. A fresh client must recover the **original** protected private key.
10. The paper must not claim human memorability or entropy without a proper human study.
11. Provider-specific resolver identifiers should not silently become long-term cryptographic cue identities unless the policy explicitly chooses and analyzes that tradeoff.
12. Any numerical online-guessing bound must be conditioned on a deployment that actually enforces the stated attempt limit.

---

# 14. Working protocol for Codex

When modifying this project:

1. Read `AGENT.md`, `PLAN.md`, `AGENT2.md`, and `PLAN2.md` before substantial work.
2. Treat `AGENT2.md` as the revision strategy and `PLAN2.md` as the live execution record.
3. Before changing protocol behavior, identify whether the change affects:
   - CuePolicy semantics;
   - protocol messages;
   - persisted state;
   - threat model;
   - recovery bootstrap;
   - paper algorithms/equations;
   - evaluation claims.
4. Update tests together with code.
5. Update paper text together with any behavior that invalidates existing descriptions.
6. After every completed task, update `PLAN2.md` with:
   - status;
   - date;
   - affected files;
   - evidence/tests;
   - paper sections changed;
   - remaining risks.
7. Never mark a task complete only because code compiles. Completion requires the task-specific acceptance criteria in `PLAN2.md`.
8. If implementation and paper disagree, treat that as a release-blocking defect.
9. Prefer small, reviewable changes with explicit tests and plan updates.

---

# 15. Definition of success

This revision is successful when an ASIACCS reviewer can answer **yes** to all of the following:

- Is CuePolicy clearly more than a serialization helper?
- Is its generality demonstrated by multiple substantially different policies?
- Can the full system recover after the original client state is truly gone?
- Is fresh-device discovery/bootstrap explicit rather than assumed?
- Are cloud storage and recovery-party roles genuinely separated in the implementation?
- Is at least one deployment meaningfully distributed beyond one host?
- Does the evaluation test the claimed system properties rather than only restating cryptographic assumptions?
- Are the TPASS, KDF, and backup-key relationships described correctly and consistently?
- Are online guessing and resolver leakage scoped honestly?
- Does the paper present a complete systems/security contribution even without a human study?
- Is the artifact reproducible and aligned with the paper?

The target outcome is a paper that no longer depends on “future usability work” to justify its current contribution. The current paper must stand on its own as a strong **end-to-end recovery systems contribution**.
