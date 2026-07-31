# PLAN2.md — LOCUS ASIACCS 2027 Live Improvement Plan

**Document type:** Live execution plan  
**Companion files:** `AGENT.md`, `PLAN.md`, `AGENT2.md`  
**Scope:** Second-stage revision to reduce ASIACCS rejection risk  
**Primary objective:** Turn LOCUS into a convincing end-to-end reference system centered on a demonstrably general CuePolicy abstraction, realistic fresh-device recovery, stronger deployment evidence, and sharper novelty positioning.

---

# 0. How to use this live document

This file must be updated continuously while the revision is in progress.

Every meaningful implementation, experiment, architecture, or paper change must update at least one task below.

## Status legend

- `[ ]` Not started
- `[-]` In progress
- `[x]` Completed and verified
- `[!]` Blocked
- `[~]` Deferred intentionally

## Required update fields for completed tasks

When changing a task to `[x]`, record:

- **Completed:** YYYY-MM-DD
- **Code/files:** paths or commit(s)
- **Tests/evidence:** exact test, experiment, screenshot, artifact, or result
- **Paper impact:** section(s), figure(s), algorithm(s), or table(s) updated
- **Notes:** remaining limitations or follow-up

Do not mark a task complete because code merely compiles.

## Change log

Add one row whenever a substantial project decision or milestone is completed.

| Date | Change | Why | Evidence / Commit | Paper impact |
|---|---|---|---|---|
| TBD | Initial PLAN2 created | Start ASIACCS strengthening phase | `PLAN2.md` | Revision planning |

---

# 1. Current baseline and target

## 1.1 Current baseline

The current paper/prototype already provides:

- versioned CuePolicy concept;
- one concrete three location-person-pair policy;
- Rust/Ristretto255 TPASS core;
- AES-256-GCM encrypted backup;
- S3-compatible cloud storage;
- same-host authenticated recovery-party services;
- 2-of-3 TPASS recovery in the evaluated profile;
- state-separation and snapshot experiments;
- careful no-offline-oracle claim scoping;
- explicit acknowledgment that global rollback-resistant attempt control is not established;
- no human-subject memorability claim.

## 1.2 Main rejection risks to eliminate

1. CuePolicy can be perceived as only a serialization/canonicalization helper.
2. Only one policy is implemented, weakening the claim of a generic cue-policy abstraction.
3. End-to-end device-loss recovery is not fully demonstrated.
4. Fresh-device bootstrap/admission is assumed rather than designed.
5. Evaluation is mainly same-host and narrow.
6. Online attempt control is incomplete and may distract from the stronger offline-oracle result.
7. The paper can still look too close to a standard TPASS-based encrypted-backup composition.
8. The artifact needs stronger clean-host reproducibility and alignment with the new system.

## 1.3 Target system

The target reference system should support:

`Setup -> Enrollment -> CuePolicy -> TPASS -> Cloud backup + distributed party states -> complete client loss -> fresh-client bootstrap -> cue reproduction -> threshold recovery -> derive K_wrap -> decrypt original sk_U -> successor epoch`

The target paper should be defensible as an **applied cryptography/security systems paper**, independent of any future human study.

---

# 2. P0 — Freeze the revised scientific claim and architecture

## 2.1 Rewrite the internal project claim

- [ ] Define the one-sentence primary research claim.

**Target wording:**

> LOCUS provides an end-to-end threshold private-key recovery system in which a versioned CuePolicy converts deployment-defined human-facing recovery information into reproducible client-local TPASS input, while cloud-only and below-threshold recovery-party compromise do not create an offline cue-testing oracle under the inherited TPASS assumptions.

**Acceptance criteria:**

- Claim does not imply LOCUS invents TPASS.
- Claim does not imply storage separation alone is novel.
- Claim does not claim memorability, entropy, usability, or global rate limiting.

**Tracking:**
- Completed:
- Code/files:
- Tests/evidence:
- Paper impact:
- Notes:

---

## 2.2 Decide the final scope of online attempt control

- [ ] Decide whether the revised paper will:
  - keep global attempt control explicitly outside the LOCUS guarantee; or
  - implement a stronger globally monotonic mechanism.

**Recommended default:** keep it external and narrow the core contribution to elimination of offline checking below threshold.

**Acceptance criteria:**

- Introduction, threat model, requirements, evaluation, claims, limitations, and conclusion all use consistent language.
- No prototype-local counter is used as if it were a globally adversarially enforced limit.
- Existing rollback counterexample is retained only if it clarifies the boundary and does not dominate the paper.

**Tracking:**
- Decision:
- Completed:
- Paper impact:
- Notes:

---

# 3. P0 — Formalize CuePolicy as the primary systems contribution

## 3.1 Define a common CuePolicy interface

- [ ] Refactor or formalize policy logic behind a common policy interface.

**Required policy responsibilities:**

- policy ID/version;
- accepted input structure;
- resolver profile;
- validation;
- normalization;
- ordering;
- duplicate handling;
- ambiguity handling;
- drift behavior;
- canonical encoding;
- public non-secret context metadata;
- fail-closed behavior.

**Acceptance criteria:**

- TPASS code consumes only policy output and policy identity, not policy-specific data types.
- Adding a new policy does not require modifying TPASS internals.
- Unsupported or ambiguous inputs fail before TPASS recovery starts.

**Tracking:**
- Completed:
- Code/files:
- Tests/evidence:
- Paper impact: Section 4.2 / implementation / evaluation
- Notes:

---

## 3.2 Rename/clarify the main location-person policy

- [ ] Define the primary production/reference policy as a stable location-person-contact policy.

Suggested name:

`LocationPersonContact-v1`

### Location design

- [ ] Use Google Maps or another provider only as the human-facing resolver.
- [ ] Canonicalize to a provider-independent location representation where practical.
- [ ] Decide exact quantization/normalization rule.
- [ ] Ensure display-name or provider record reindexing does not silently change the canonical location when the physical selection is equivalent under policy rules.

### Person design

- [ ] Prefer canonical email or E.164 phone number for the primary stable reference policy.
- [ ] Treat display name and relationship label as UI-only.
- [ ] Decide whether social-media URLs belong in a separate policy rather than this primary policy.

**Acceptance criteria:**

- UI wording and persisted state match the policy definition.
- Provider-specific IDs are not silently used as long-term cryptographic cue identities unless explicitly documented.

**Tracking:**
- Completed:
- Code/files:
- Tests/evidence:
- Paper impact:
- Notes:

---

## 3.3 Add a structured textual CuePolicy

- [ ] Implement `StructuredPhrase-v1` or equivalent.

**Must define:**

- Unicode normalization form;
- whitespace behavior;
- case behavior;
- punctuation policy;
- field/cardinality constraints;
- length limits;
- versioning;
- exact encoding.

**Acceptance criteria:**

- Equivalent admitted forms canonicalize deterministically.
- Non-equivalent forms remain distinct when policy says they should.
- No policy-specific changes are required in TPASS.
- Test vectors are published in the artifact.

**Tracking:**
- Completed:
- Code/files:
- Tests/evidence:
- Paper impact:
- Notes:

---

## 3.4 Add a third CuePolicy with a different resolver/privacy model

- [ ] Implement a third policy, preferably local/no-provider.

Possible target:

`LocalEventLabels-v1` or `LocalLabels-v1`

**Goal:** demonstrate that CuePolicy spans materially different human-facing input/resolver assumptions.

**Acceptance criteria:**

- No public resolver is contacted during enrollment/recovery for this policy.
- The same TPASS path is used unchanged.
- The paper uses this policy to explain storage privacy vs resolver privacy.

**Tracking:**
- Completed:
- Code/files:
- Tests/evidence:
- Paper impact:
- Notes:

---

## 3.5 Optional provider-dependent social-profile policy

- [ ] / [~] Decide whether to retain the existing social-media profile URL UI as a separate experimental policy.

Suggested name:

`LocationPersonProfile-v1`

**If implemented, explicitly analyze:**

- URL/username changes;
- reassignment risk;
- account deletion;
- provider dependence;
- resolver privacy leakage;
- recovery drift.

**Acceptance criteria:**

- It is not presented as the strongest long-term reference policy.
- Its tradeoffs are explicit.

**Tracking:**
- Decision:
- Completed:
- Notes:

---

# 4. P0/P1 — Build the end-to-end enrollment client

## 4.1 Setup / private-key screen

- [ ] Add a user-facing setup flow to generate or import the protected private key `sk_U`.

**Acceptance criteria:**

- The protected key can be deterministically identified in testing.
- The test suite can prove the recovered key is byte-for-byte the original protected key.

**Tracking:**
- Completed:
- Code/files:
- Tests/evidence:
- Notes:

---

## 4.2 Integrate CuePolicy selection into UI

- [ ] Add a supported-policy selection screen or workflow.
- [ ] Reuse the existing location-person cue UI for the relevant policy.
- [ ] Add UI for the new phrase/local policies.

**UI rules:**

- Say “recovery cues”, not “password”.
- Do not say raw values are “stored internally for hashing” unless they are actually persisted.
- Explain that LOCUS resolves/validates/canonicalizes the selection under the active policy.
- Keep `p_M` hidden in normal mode.

**Acceptance criteria:**

- UI maps to the actual policy implementation.
- Screenshots can be used directly in the paper/artifact documentation without contradicting the security model.

**Tracking:**
- Completed:
- Code/files:
- Tests/evidence:
- Paper impact:
- Notes:

---

## 4.3 Correct the enrollment cryptographic flow

- [ ] Ensure implementation order matches the paper:

`M -> Z_M -> bid/e/ID_R -> p_M -> TPASS.Setup -> S_R -> HKDF -> K_wrap -> AEAD(sk_U)`

**Do not:** generate an independent symmetric key and treat that key as the TPASS-recovered object unless the entire paper is deliberately redesigned.

**Acceptance criteria:**

- Code path matches algorithms/equations.
- Tests verify the exact data dependency chain.
- No legacy code path contradicts the paper-facing construction.

**Tracking:**
- Completed:
- Code/files:
- Tests/evidence:
- Paper impact:
- Notes:

---

## 4.4 Add party selection/provisioning

- [ ] Add enrollment-time selection of a configured authenticated recovery-party set.
- [ ] Support threshold selection allowed by deployment policy.
- [ ] Provision party records over authenticated/confidential channels.

**Acceptance criteria:**

- Each party receives only its own TPASS state and required bindings.
- Party identities/endpoints are fixed in enrolled metadata and cannot be silently replaced at recovery.

**Tracking:**
- Completed:
- Code/files:
- Tests/evidence:
- Notes:

---

## 4.5 Add real post-enrollment erasure checks

- [ ] Erase all client-local enrollment secrets after successful enrollment.

Verify absence of:

- raw cues;
- resolver records not intended to persist;
- canonical descriptors;
- `Z_M`;
- `p_M`;
- `S_R`;
- `K_wrap`;
- setup randomness;
- plaintext protected key outside the intended application/key store state.

**Acceptance criteria:**

- Automated test inspects persistent client state after enrollment.
- Clean-device recovery does not depend on hidden leftover client files.

**Tracking:**
- Completed:
- Code/files:
- Tests/evidence:
- Paper impact:
- Notes:

---

# 5. P0/P1 — Design and implement fresh-device bootstrap

## 5.1 Choose the recovery-discovery model

- [ ] Decide what a user/fresh client retains or can access after device loss.

Candidate models:

A. Non-secret recovery handle + remembered cues  
B. Authenticated cloud account + remembered cues  
C. Another explicitly documented discovery mechanism

**Decision must answer:**

- How is the backup found?
- How is the active epoch found?
- How is the policy version found?
- How are the recovery parties found?
- How are their endpoints authenticated?
- What attacker can enumerate this metadata?

**Acceptance criteria:**

- Threat model documents the choice.
- Recovery UI implements the same choice.
- No hidden original-device state is required.

**Tracking:**
- Decision:
- Completed:
- Paper impact:
- Notes:

---

## 5.2 Define `RecoveryDescriptor`

- [ ] Specify a versioned public/non-secret recovery descriptor.

Candidate fields:

- descriptor version;
- recovery handle;
- `bid`;
- epoch;
- policy ID/version;
- cloud backend/locator;
- party IDs;
- authenticated endpoints/pins;
- threshold profile;
- required public protocol metadata.

**Explicitly forbidden fields:**

- raw cues;
- `Z_M`;
- `p_M`;
- secret party state;
- `S_R`;
- `K_wrap`;
- local verifier.

**Acceptance criteria:**

- Descriptor is sufficient for bootstrap under the chosen discovery model.
- Possession of the descriptor does not enable offline cue checking below threshold.
- Descriptor tampering/substitution behavior is defined.

**Tracking:**
- Completed:
- Code/files:
- Tests/evidence:
- Paper impact:
- Notes:

---

## 5.3 Implement descriptor publication/retrieval

- [ ] Persist and retrieve the descriptor through the chosen discovery mechanism.

**Acceptance criteria:**

- Fresh client can obtain the descriptor without access to the old client state.
- Version/epoch mismatches fail closed.

**Tracking:**
- Completed:
- Code/files:
- Tests/evidence:
- Notes:

---

# 6. P1 — Cloud backend improvements

## 6.1 Abstract cloud storage

- [ ] Introduce a provider-independent cloud-backend interface.

Minimum operations:

- store backup;
- retrieve backup;
- store/retrieve descriptor if applicable;
- exact object identity/reference validation.

**Acceptance criteria:**

- Existing S3-compatible path still works.
- Protocol logic does not depend on one provider API.

**Tracking:**
- Completed:
- Code/files:
- Tests/evidence:
- Notes:

---

## 6.2 Add a real cloud-backed implementation

- [ ] Evaluate feasibility of CloudKit/iCloud or another real provider.
- [ ] Implement one real provider if feasible within schedule.

**If CloudKit is used, decide explicitly:**

- private-account database model; or
- public/retrievable encrypted-object model.

**Acceptance criteria:**

- The paper states whether prior cloud-account access is required before LOCUS recovery can begin.
- Cloud compromise is still within the intended confidentiality threat model.

**Tracking:**
- Decision:
- Completed:
- Code/files:
- Tests/evidence:
- Paper impact:
- Notes:

---

# 7. P1 — Build true clean-device recovery

## 7.1 Implement “destroy local client” workflow

- [ ] Add a reproducible command/test that destroys the original client’s entire local LOCUS state.

**Preferred implementation:** separate container/VM profile for enrollment and recovery.

**Acceptance criteria:**

- Recovery client has no mount/access to original client volume.
- Test confirms sensitive enrollment state is gone before recovery begins.

**Tracking:**
- Completed:
- Code/files:
- Tests/evidence:
- Notes:

---

## 7.2 Implement clean-client recovery bootstrap

- [ ] Launch clean Client B.
- [ ] Obtain recovery descriptor/context.
- [ ] Retrieve exact encrypted backup.
- [ ] Discover authenticated enrolled party set.
- [ ] Load enrolled CuePolicy version.

**Acceptance criteria:**

- No manual injection of hidden test-only values such as exact internal paths or old client secrets.
- Any human-visible recovery handle is explicit in the paper.

**Tracking:**
- Completed:
- Code/files:
- Tests/evidence:
- Notes:

---

## 7.3 Implement candidate cue reproduction

- [ ] Collect cues through the UI.
- [ ] Apply the enrolled policy.
- [ ] Derive `Z_M'` and `p_M'` under the enrolled `ID_R`.

**Acceptance criteria:**

- Correct equivalent cue inputs reproduce the enrollment canonical output.
- Incorrect/ambiguous inputs fail as designed.

**Tracking:**
- Completed:
- Code/files:
- Tests/evidence:
- Notes:

---

## 7.4 Execute threshold recovery

- [ ] Select a healthy threshold subset from the enrolled party set.
- [ ] Run TPASS recovery.
- [ ] Obtain `S_R'` on success.
- [ ] Derive `K_wrap'`.
- [ ] Authenticate/decrypt backup.
- [ ] Recover the original `sk_U`.

**Acceptance criteria:**

- Byte-for-byte identity with enrolled protected key.
- Wrong cues do not yield a decrypting key.
- Insufficient parties fail.
- Wrong/stale backup binding fails.

**Tracking:**
- Completed:
- Code/files:
- Tests/evidence:
- Paper impact:
- Notes:

---

## 7.5 Implement successor epoch after successful recovery

- [ ] On successful recovery, support new recovery state under a successor epoch.
- [ ] Optionally rotate `sk_U` if the loss scenario assumes possible compromise.
- [ ] Retire old state in the implemented lifecycle path where feasible.

**Acceptance criteria:**

- Epoch transition is explicit and versioned.
- Tests reject cross-epoch mixing.

**Tracking:**
- Completed:
- Code/files:
- Tests/evidence:
- Paper impact:
- Notes:

---

# 8. P1/P2 — Strengthen recovery-party deployment

## 8.1 Separate parties onto independent hosts/VMs

- [ ] Move at least one evaluation profile off same-host-only deployment.

**Minimum target:** 3 parties on 3 distinct hosts/VMs.

**Stronger target:** different networks/regions/administrative domains where feasible.

**Acceptance criteria:**

- Paper reports host/network topology.
- Recovery works with real network separation.

**Tracking:**
- Completed:
- Deployment:
- Tests/evidence:
- Paper impact:
- Notes:

---

## 8.2 Add multiple threshold profiles

- [ ] 2-of-3
- [ ] 3-of-5
- [ ] Optional 4-of-7

**Acceptance criteria:**

- Same protocol implementation supports each profile.
- Evaluation reports latency/bytes/storage impact.

**Tracking:**
- Completed profiles:
- Tests/evidence:
- Notes:

---

## 8.3 Unavailable-party behavior

- [ ] Test recovery when one or more parties are unavailable but threshold remains satisfiable.
- [ ] Test failure when fewer than threshold remain available.

**Acceptance criteria:**

- Fixed/healthy subset selection behavior is deterministic and documented.

**Tracking:**
- Completed:
- Tests/evidence:
- Paper impact:
- Notes:

---

# 9. P2 — Build the new CuePolicy evaluation

## 9.1 Shared conformance corpus

- [ ] Create a common test-vector format across all policies.

Each vector should record:

- policy ID/version;
- human-facing/synthetic structured input;
- resolver fixture/state if relevant;
- expected canonical output or expected failure;
- expected reason/category.

**Acceptance criteria:**

- All policies run through the same conformance harness.
- Artifact can reproduce results deterministically.

**Tracking:**
- Completed:
- Code/files:
- Evidence:
- Notes:

---

## 9.2 Location-person conformance tests

- [ ] all cue-order permutations;
- [ ] coordinate normalization/quantization;
- [ ] equivalent provider display changes;
- [ ] duplicate location rejection;
- [ ] duplicate person rejection;
- [ ] malformed contact rejection;
- [ ] phone normalization;
- [ ] email normalization;
- [ ] ambiguous location failure;
- [ ] resolver missing-record failure;
- [ ] provider drift behavior;
- [ ] unsupported version failure.

**Tracking:**
- Completed:
- Evidence:
- Notes:

---

## 9.3 StructuredPhrase conformance tests

- [ ] Unicode equivalent forms;
- [ ] whitespace variants;
- [ ] case behavior;
- [ ] punctuation behavior;
- [ ] malformed/overlong inputs;
- [ ] version separation;
- [ ] deterministic encoding.

**Tracking:**
- Completed:
- Evidence:
- Notes:

---

## 9.4 Local/no-provider policy conformance tests

- [ ] deterministic local mapping;
- [ ] version behavior;
- [ ] no resolver network access;
- [ ] malformed input failure;
- [ ] canonical ordering as applicable.

**Tracking:**
- Completed:
- Evidence:
- Notes:

---

## 9.5 Cross-policy separation

- [ ] Verify that semantically similar inputs under different policy IDs cannot collide through accidental reinterpretation.

**Acceptance criteria:**

- Policy identity is cryptographically bound into canonical/derived input as designed.

**Tracking:**
- Completed:
- Evidence:
- Notes:

---

# 10. P2 — End-to-end recovery experiments

## 10.1 Clean-device success experiment

- [ ] Run:

`Enrollment Client A -> persist cloud/party state -> destroy Client A -> launch Client B -> bootstrap -> reproduce cues -> TPASS recover -> decrypt original sk_U`

Repeat for each implemented CuePolicy where practical.

**Acceptance criteria:**

- Original key matches exactly.
- No enrollment-only client secret is available to Client B.

**Tracking:**
- Completed:
- Runs:
- Evidence:
- Paper table/figure:
- Notes:

---

## 10.2 Wrong-cue experiment

- [ ] Verify wrong cues require online threshold interaction when they pass policy validation.
- [ ] Verify wrong cues do not decrypt the key.

**Important:** do not interpret number of guesses as cue entropy evidence.

**Tracking:**
- Completed:
- Evidence:
- Notes:

---

## 10.3 Wrong/stale descriptor or backup experiment

- [ ] wrong `bid`;
- [ ] stale epoch;
- [ ] substituted cloud object;
- [ ] digest mismatch;
- [ ] policy-version mismatch;
- [ ] mixed enrollment state.

**Tracking:**
- Completed:
- Evidence:
- Notes:

---

# 11. P2 — State-separation and information-flow evidence

## 11.1 Research State Inspector

- [ ] Implement an optional developer/research UI view showing redacted actual state placement.

Suggested matrix:

- cloud ciphertext/public metadata;
- party-local TPASS state;
- client-erased secrets;
- resolver-visible lookup data;
- descriptor metadata.

**Acceptance criteria:**

- View is derived from real state inspection or authoritative runtime metadata, not a hard-coded diagram.

**Tracking:**
- Completed:
- Screenshot/evidence:
- Paper impact:
- Notes:

---

## 11.2 Persistent-state audit

- [ ] Inspect cloud persistent state.
- [ ] Inspect each party persistent state.
- [ ] Inspect post-enrollment client state.
- [ ] Inspect clean recovery client before cue entry.

Search for prohibited material:

- raw cues;
- canonical cues;
- `Z_M`;
- `p_M`;
- `S_R`;
- `K_wrap`;
- password verifier;
- plaintext protected key where not intended.

**Acceptance criteria:**

- Automated report with positive controls where meaningful.

**Tracking:**
- Completed:
- Evidence:
- Notes:

---

## 11.3 Network-flow audit

- [ ] Capture enrollment network traffic.
- [ ] Capture recovery network traffic.
- [ ] Document which role receives which information.

For resolver-backed policy, distinguish:

- resolver-visible raw lookup;
- cloud-visible backup/public metadata;
- party-visible TPASS messages/state;
- client-only canonical cue material.

**Acceptance criteria:**

- Paper can state the implemented information-flow boundary with concrete evidence.

**Tracking:**
- Completed:
- Evidence:
- Paper impact:
- Notes:

---

# 12. P2 — Performance and deployment evaluation

## 12.1 Measurement harness

- [ ] Create deterministic measurement harness and metadata schema.

Record:

- commit;
- dependency versions;
- host IDs/pseudonyms;
- topology;
- CPU/RAM/OS;
- party profile;
- policy;
- network placement;
- sample count;
- operation;
- latency phases;
- total latency;
- bytes by role;
- persistent bytes;
- failure mode.

**Tracking:**
- Completed:
- Code/files:
- Notes:

---

## 12.2 Enrollment/recovery benchmarks

- [ ] 2-of-3 same-host baseline
- [ ] 2-of-3 distributed
- [ ] 3-of-5 distributed
- [ ] optional additional profile

Measure:

- enrollment;
- correct recovery;
- wrong-input recovery;
- unavailable-party recovery;
- insufficient-party failure.

**Tracking:**
- Completed:
- Evidence:
- Paper tables:
- Notes:

---

## 12.3 Policy overhead

- [ ] Measure canonicalization/resolution overhead separately from TPASS where meaningful.

**Goal:** show CuePolicy cost does not dominate the cryptographic path, while making no usability claim.

**Tracking:**
- Completed:
- Evidence:
- Notes:

---

## 12.4 Optional concurrency test

- [ ] / [~] Add moderate concurrent recovery benchmark if schedule allows.

**Do not** prioritize this above clean-device recovery, multiple policies, or distributed-party evaluation.

**Tracking:**
- Decision:
- Evidence:
- Notes:

---

# 13. P2 — Resolver/privacy experiments

## 13.1 Resolver-backed policy observation

- [ ] Record what the external resolver sees during enrollment/recovery.

**Acceptance criteria:**

- Demonstrate that local hashing/canonicalization does not hide the original lookup from the resolver.
- Demonstrate that resolver-visible data is not automatically propagated as stored cloud/party state.

**Tracking:**
- Completed:
- Evidence:
- Paper impact:
- Notes:

---

## 13.2 Compare with no-provider policy

- [ ] Run equivalent recovery under a local/no-provider CuePolicy.

**Goal:** provide concrete evidence for the paper’s distinction between storage privacy and resolver privacy.

**Tracking:**
- Completed:
- Evidence:
- Notes:

---

# 14. P3 — Rewrite the paper around the stronger system

## 14.1 Title

- [ ] Re-evaluate title after implementation is stable.

Potential directions:

- emphasize CuePolicy + end-to-end threshold recovery;
- avoid over-focusing on one location/person policy;
- avoid novelty claims around TPASS itself.

**Tracking:**
- Decision:
- Notes:

---

## 14.2 Abstract

- [ ] Rewrite abstract to include:
  - explicit CuePolicy problem;
  - multiple policy families;
  - clean-device recovery;
  - real/distributed deployment evidence;
  - no-offline-oracle scope;
  - no memorability claim.

**Acceptance criteria:**

- Abstract does not lead with a same-host demo.
- Abstract does not imply rate-limit guarantees not established.

**Tracking:**
- Completed:
- Notes:

---

## 14.3 Introduction

- [ ] Rewrite introduction around the systems gap rather than “location cues”.

Suggested logic:

1. Key loss problem.
2. Password-protected backups can create offline-guessing targets.
3. TPASS can prevent specified below-threshold offline checking.
4. But TPASS expects stable password input; real human-facing recovery information is ambiguous, versioned, resolver-dependent, and subject to drift.
5. LOCUS makes this transformation a protocol boundary and implements a complete recovery lifecycle.

**Acceptance criteria:**

- Acknowledge early that TPASS is an existing primitive.
- State precisely what LOCUS adds.

**Tracking:**
- Completed:
- Notes:

---

## 14.4 Contributions

- [ ] Rewrite contribution list in this order:

1. CuePolicy abstraction + multiple policy instantiations.
2. End-to-end storage-separated recovery architecture with explicit fresh-device bootstrap.
3. Reference implementation with UI, cloud backend(s), native TPASS, and distributed parties.
4. Evaluation of policy conformance, clean-device recovery, state/information-flow boundaries, and deployment cost.
5. Security analysis of offline/online/resolver/lifecycle boundaries.

**Tracking:**
- Completed:
- Notes:

---

## 14.5 Add architecture figure

- [ ] Add a central figure showing enrollment and recovery.

Must visually show:

`Human cues -> CuePolicy -> p_M -> TPASS -> S_R -> K_wrap -> encrypted key`

and storage separation:

- cloud;
- recovery parties;
- optional resolver;
- client-local ephemeral secrets;
- fresh-client bootstrap.

**Acceptance criteria:**

- A general security reviewer can understand the system from the figure + caption.

**Tracking:**
- Completed:
- Figure file:
- Paper page:
- Notes:

---

## 14.6 Add CuePolicy architecture subsection

- [ ] Replace single-policy emphasis with common contract + policy instantiations.
- [ ] Move policy-specific details to examples/tables where possible.

**Tracking:**
- Completed:
- Notes:

---

## 14.7 Add fresh-device bootstrap/admission section

- [ ] Document the RecoveryDescriptor and recovery-discovery model.
- [ ] State user assumptions after device loss.
- [ ] Explain party endpoint authentication.
- [ ] Explain whether recovery is publicly callable or separately admitted.

**Tracking:**
- Completed:
- Notes:

---

## 14.8 Update algorithms

- [ ] Update enrollment algorithm for new descriptor/backend details.
- [ ] Update recovery algorithm to include bootstrap/discovery inputs/steps.
- [ ] Verify all equations and key dependencies remain correct.

**Tracking:**
- Completed:
- Notes:

---

## 14.9 Rebuild evaluation around research questions

- [ ] RQ1 CuePolicy generality/conformance
- [ ] RQ2 clean-device recovery
- [ ] RQ3 storage/information-flow boundary
- [ ] RQ4 realistic distributed cost
- [ ] RQ5 resolver boundary

**Acceptance criteria:**

- Each experiment answers a stated research question.
- Snapshot tests are not oversold as cryptographic proofs.

**Tracking:**
- Completed:
- Notes:

---

## 14.10 Update threat model/security analysis

- [ ] Add recovery descriptor/discovery attacker considerations.
- [ ] Add provider/account assumptions if real cloud login is required.
- [ ] Preserve cloud/below-threshold/offline-oracle claims.
- [ ] Preserve resolver-observer analysis.
- [ ] Keep threshold compromise outside guarantee.
- [ ] Normalize recovery error-channel discussion.

**Tracking:**
- Completed:
- Notes:

---

## 14.11 Update related work and novelty positioning

- [ ] Make the TPASS relationship explicit and non-defensive.
- [ ] Clarify that LOCUS does not claim the primitive or basic password-to-random-secret composition.
- [ ] Explain the systems delta:
  - semantic human input boundary;
  - versioning/canonicalization;
  - fresh-device bootstrap;
  - multi-policy integration;
  - concrete storage/party separation;
  - end-to-end artifact.

**Tracking:**
- Completed:
- Notes:

---

## 14.12 Update limitations

- [ ] No human memorability claim.
- [ ] No entropy claim.
- [ ] Resolver privacy limitations.
- [ ] Cloud-account dependency if applicable.
- [ ] Global rate-control boundary.
- [ ] Threshold compromise.
- [ ] party rollback/lifecycle limitations.
- [ ] prototype/audit limitations.

**Tracking:**
- Completed:
- Notes:

---

## 14.13 Update conclusion

- [ ] Conclude on the complete systems contribution, not future user studies.

Future human studies should be framed as a distinct next research question, not missing validation of the current systems claim.

**Tracking:**
- Completed:
- Notes:

---

# 15. P3/P4 — Artifact and reproducibility

## 15.1 Anonymous artifact

- [ ] Prepare anonymous repository/archive for review.

Include:

- source;
- build instructions;
- policy vectors;
- deployment scripts;
- clean-device recovery workflow;
- experiment harness;
- result-processing scripts;
- figure/table regeneration;
- limitations/security notes.

**Tracking:**
- Completed:
- Artifact location:
- Notes:

---

## 15.2 Clean-host reproduction

- [ ] Reproduce the complete paper-facing workflow from a clean environment.

**Must include:**

- build;
- enrollment;
- client destruction;
- fresh recovery;
- multi-policy tests;
- key evaluation runs;
- paper tables/figures generation.

**Acceptance criteria:**

- No undeclared developer-local state is required.

**Tracking:**
- Completed:
- Environment:
- Evidence:
- Notes:

---

## 15.3 Cryptographic implementation assurance

- [ ] Expand property/regression tests for TPASS transcript encoding and domain separation.
- [ ] Add fuzz/property tests where appropriate.
- [ ] Preserve deterministic cross-language vectors.
- [ ] Document any changes from Yi et al.’s source construction.
- [ ] Review generator derivation and transcript mapping.

**Optional:** independent code review if available.

**Tracking:**
- Completed:
- Evidence:
- Notes:

---

# 16. P4 — Consistency audit before submission

## 16.1 Protocol consistency

- [ ] Every variable in the paper matches implementation semantics.
- [ ] `p_M` is never described as an encryption key.
- [ ] `S_R` is the TPASS-recovered group secret.
- [ ] `K_wrap` is derived from `S_R`.
- [ ] Fresh client recovers the original `sk_U`.
- [ ] New key generation occurs only during initial setup or post-recovery rotation.

---

## 16.2 Storage consistency

- [ ] Cloud table matches actual cloud state.
- [ ] Party-state table matches actual party state.
- [ ] Descriptor table matches implementation.
- [ ] Post-enrollment client state matches erasure claim.
- [ ] Resolver observations match actual resolver flow.

---

## 16.3 Claim consistency

- [ ] No claim of memorability.
- [ ] No claim of measured cue entropy.
- [ ] No claim of global rate-limit security unless established.
- [ ] No claim of resolver privacy when using external resolvers.
- [ ] No claim of threshold security beyond inherited TPASS assumptions.
- [ ] No claim of production-ready cryptography/audit unless true.

---

## 16.4 ASIACCS presentation/compliance

- [ ] Main text within page limit.
- [ ] Open Science appendix updated.
- [ ] Ethical Considerations appendix updated.
- [ ] Anonymous artifact available.
- [ ] Architecture figure readable in two-column format.
- [ ] Track selection consistent with applied cryptography/security systems framing.

---

# 17. Reviewer-facing acceptance gates

The revision should not be considered submission-ready until the following gates are met.

## Gate A — CuePolicy is demonstrably general

- [ ] At least 3 materially different policies implemented.
- [ ] Shared interface.
- [ ] Shared conformance harness.
- [ ] No TPASS changes needed per policy.

## Gate B — Fresh-device recovery is real

- [ ] Original client state destroyed.
- [ ] New clean client recovers the original key.
- [ ] Bootstrap/discovery is explicit and implemented.

## Gate C — Deployment evidence is stronger

- [ ] At least one independent-host/VM recovery profile.
- [ ] At least two threshold configurations if feasible.
- [ ] realistic latency/bytes/failure results.

## Gate D — State boundaries are evidenced

- [ ] cloud state audited;
- [ ] party state audited;
- [ ] client erasure audited;
- [ ] network flows inspected;
- [ ] resolver leakage documented.

## Gate E — Novelty story is explicit

- [ ] Introduction states what TPASS already provides.
- [ ] Contribution list centers CuePolicy + lifecycle/system integration.
- [ ] Related work directly compares with Yi et al., SafetyPin, SVR3, PPKR/WhatsApp.

## Gate F — Paper stands without a human study

- [ ] Current contribution is complete as a security systems result.
- [ ] Future usability/memorability research is clearly separate.

## Gate G — Artifact is reviewable

- [ ] Anonymous artifact available.
- [ ] Clean-host reproduction completed.
- [ ] Paper results trace to artifact outputs.

---

# 18. Recommended implementation order

Unless blocked, follow this order to minimize rework:

1. [ ] Freeze scientific claim and online-attempt-control scope.
2. [ ] Define CuePolicy interface.
3. [ ] Finalize `LocationPersonContact-v1` representation and UI wording.
4. [ ] Implement `StructuredPhrase-v1`.
5. [ ] Implement local/no-provider policy.
6. [ ] Define RecoveryDescriptor and bootstrap model.
7. [ ] Refactor cloud backend interface.
8. [ ] Integrate setup/enrollment UI.
9. [ ] Implement complete post-enrollment erasure.
10. [ ] Implement destroy-client + clean-client workflow.
11. [ ] Implement fresh-client bootstrap and recovery.
12. [ ] Validate original-key recovery.
13. [ ] Move parties to independent hosts/VMs.
14. [ ] Add additional threshold profile(s).
15. [ ] Run shared policy conformance suite.
16. [ ] Run state/network-flow audits.
17. [ ] Run performance/failure evaluation.
18. [ ] Rewrite paper around final system.
19. [ ] Prepare/reproduce anonymous artifact.
20. [ ] Run final consistency and ASIACCS compliance audits.

---

# 19. Decisions still required

Keep this list current.

- [ ] Final name of the primary location-person policy.
- [ ] Whether social-media profile URLs remain as a separate experimental policy.
- [ ] Exact provider-independent location canonicalization rule.
- [ ] Recovery bootstrap/discovery model.
- [ ] RecoveryDescriptor fields and integrity/authentication model.
- [ ] Whether a fresh user must already have cloud-account access.
- [ ] Real cloud provider choice.
- [ ] Recovery-party hosting topology.
- [ ] Final threshold profiles.
- [ ] Whether the partial attempt ledger remains in the main paper, moves to appendix, or is removed from the core implementation story.
- [ ] Final paper title after system implementation stabilizes.

---

# 20. Live risk register

Update severity and mitigation as work proceeds.

| Risk | Severity | Current mitigation | Status |
|---|---:|---|---|
| CuePolicy still looks like serialization | Critical | Multiple policies + shared contract + conformance evaluation | Open |
| Bootstrap requires hidden state | Critical | RecoveryDescriptor + explicit discovery model | Open |
| Same-host evaluation too weak | High | Independent hosts/VMs + WAN measurements | Open |
| Social/provider identifiers drift | High | Provider-independent canonicalization / separate provider-dependent policy | Open |
| Online guessing remains practical for weak cues | High | Scope to online-only boundary; no entropy claim; external admission controls | Open |
| Global attempt state rollback | High | Do not claim global bound; narrow scope or redesign separately | Open |
| Cloud account becomes hidden recovery factor | High | Explicitly document/choose retrieval model | Open |
| UI accidentally contradicts storage-erasure claims | Medium | UI wording audit + state inspector | Open |
| TPASS implementation mapping error | High | regression/property/fuzz tests + vectors + documentation | Open |
| Page limit pressure | Medium | architecture figure + concise policy table + move details to artifact/appendix | Open |
| Artifact not reproducible | High | clean-host reproduction gate | Open |

---

# 21. Final submission readiness checklist

- [ ] All acceptance gates A–G passed.
- [ ] All P0 tasks completed.
- [ ] Required P1 tasks completed.
- [ ] Core P2 experiments completed and paper-integrated.
- [ ] P3 rewrite completed.
- [ ] P4 audits completed.
- [ ] No implementation/paper contradictions found.
- [ ] Anonymous artifact tested.
- [ ] Final reviewer-style internal review performed.
- [ ] Final estimated rejection risks documented below.

## Final internal reviewer assessment

**Date:** TBD  
**Recommendation:** TBD  
**Confidence:** TBD  
**Remaining major weaknesses:** TBD  
**Submission decision:** TBD
