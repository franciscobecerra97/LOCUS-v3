# ACNS_AGENT.md

## Purpose

This file defines the **ACNS 2027 publication strategy for LOCUS** and records the research, security, evaluation, and narrative changes that should be made after the existing LOCUS implementation PLAN is completed.

This file is **not a replacement for the existing project `AGENT.md` or `PLAN.md`**.

The current project already has an agent guide and an implementation plan that produced the present LOCUS system and manuscript. Those remain authoritative for completing the current implementation work.

`ACNS_AGENT.md` has a different role:

- preserve the ACNS 2027 research strategy while implementation work is still ongoing;
- prevent remaining implementation decisions from contradicting the intended ACNS security story;
- define what must change in the paper once the current PLAN is complete;
- provide the basis for a later `ACNS_PLAN.md`;
- help any AI agent continue the ACNS revision consistently without silently changing LOCUS's scope or claims.

The target venue is:

**25th International Conference on Applied Cryptography and Network Security (ACNS 2027)**

The intended submission is the first ACNS 2027 cycle unless the project owner explicitly changes this decision.

---

# 1. Relationship to Existing Project Instructions

LOCUS already contains:

1. an existing `AGENT.md`;
2. an existing `PLAN.md`;
3. a working implementation;
4. a manuscript generated from that implementation and evidence;
5. ongoing PLAN tasks that are not yet complete.

The following precedence must be respected.

## 1.1 While the current PLAN is unfinished

The existing:

- `AGENT.md`
- `PLAN.md`
- approved claim/evidence matrix
- implementation invariants
- frozen cryptographic suite mappings

remain authoritative for implementation work.

`ACNS_AGENT.md` must **not** be interpreted as permission to bypass, reorder, or replace unfinished PLAN tasks.

Do not rewrite the system merely to make the paper easier to publish.

Do not weaken existing security invariants.

Do not silently change cryptographic mappings.

Do not modify accepted evidence boundaries without explicit project-owner approval.

## 1.2 Role of ACNS_AGENT during the unfinished PLAN

While the implementation PLAN is still active, this document is a **forward-looking research constraint**.

If a remaining implementation decision has multiple valid solutions, prefer the option that:

- preserves the principal below-threshold security claim;
- keeps suite behavior explicit;
- does not introduce fallback or downgrade behavior;
- keeps authorization and reconstruction thresholds distinct;
- minimizes persistent secret-derived state;
- keeps cloud state separated from threshold-holder state;
- improves reproducibility and reviewer-verifiable evidence;
- does not introduce a new unexamined offline cue-testing predicate.

However, the current PLAN must still be completed according to its own gates.

## 1.3 After the current PLAN is complete

Once the current PLAN is fully completed and validated:

1. record the final implementation commit;
2. freeze the final claim/evidence state;
3. record final performance results;
4. record independent cryptographic review results;
5. record clean-host artifact reproduction results;
6. create `ACNS_PLAN.md`.

`ACNS_PLAN.md` will then contain the concrete tasks required to transform the completed LOCUS project and manuscript into the ACNS 2027 submission.

---

# 2. Core ACNS Strategy

The ACNS version of LOCUS should **not** be presented primarily as:

> a software framework combining several existing components.

It should also **not** be presented primarily as:

> a human-memorable cue system.

The central ACNS research story should instead be:

> A secure threshold/password-protected recovery primitive is not sufficient by itself to guarantee a secure end-to-end private-key recovery system. The surrounding storage, discovery, metadata, lifecycle, configuration, recovery-package, error-handling, and clean-client mechanisms can accidentally recreate an offline verification predicate. LOCUS defines the system-level conditions required to preserve below-threshold offline-guessing resistance and demonstrates a complete recovery architecture that maintains those conditions across the full recovery workflow.

The ACNS paper should therefore follow this intellectual progression:

**security problem → security definition → system construction → composition argument → implementation → evidence**

rather than:

**software interfaces → implementation → tests**

---

# 3. Principal Scientific Claim

The current manuscript already contains a narrow and defensible central claim:

> Cloud-only, fewer-than-reconstruction-threshold party, and matching cloud-plus-below-threshold persistent states do not expose a local offline predicate for testing a candidate recovery input. Candidate evaluation requires online participation from sufficient authenticated threshold parties, under the selected suite's assumptions.

This claim should remain central.

However, for ACNS it must become a **formal research property**, not only an informal implementation statement.

The ACNS version should define a property such as:

`Below-Threshold Offline-Guessing Resistance`

or an equivalent formal name approved by the project owner.

A future `ACNS_PLAN.md` should include work to define:

- adversary capabilities;
- persistent views;
- public configuration available to the adversary;
- candidate recovery inputs;
- allowed and disallowed oracle interactions;
- success condition;
- suite assumptions;
- system assumptions;
- exact boundary between offline and online testing.

The formalization should make clear that the protected view includes, where applicable:

- encrypted backup state;
- public descriptor state;
- public current-pointer state;
- public suite configuration;
- public masked-share material;
- fewer than `k` matching holder states;
- the combination of cloud state and fewer than `k` matching holder states.

The formal property must not claim more than the implementation or inherited suites support.

---

# 4. Add a LOCUS Composition Security Result

This is the highest-priority scientific improvement for ACNS.

The current paper explicitly states that its persistent-state table is not a new cryptographic proof. That is honest, but it leaves the main novelty vulnerable to the reviewer objection:

> What scientific result does LOCUS establish beyond correctly integrating existing TPASS/PPSS mechanisms?

The ACNS version should attempt to provide a system-level composition result.

A target theorem may have the following shape:

> Under the assumptions of the selected threshold recovery suite, the authenticated configuration mechanisms, correct domain separation, HKDF, AEAD security, and the defined trust model, the cloud-plus-below-threshold persistent view of LOCUS does not provide an efficient local predicate for validating a candidate recovery input without online participation from the required uncompromised recovery infrastructure.

The exact theorem statement must be developed carefully.

Do not invent a theorem simply to satisfy reviewers.

The theorem must be:

- consistent with the inherited Yi and aPPSS assumptions;
- consistent with the actual implementation;
- explicit about what is inherited versus newly argued;
- explicit about active-client compromise;
- explicit about threshold compromise;
- explicit about online interactions;
- explicit about rollback limitations;
- explicit about suite-specific consequences.

A reduction, hybrid argument, or rigorous composition argument may be sufficient if mathematically justified.

LOCUS does **not** need to introduce a new cryptographic primitive.

The new scientific result should be the **system-level composition property**.

---

# 5. Rewrite the Contribution Narrative

The current contribution list is too easily interpreted as software engineering:

- CuePolicy;
- suite-neutral adapter;
- managed reference implementation;
- evidence methodology.

These remain useful, but they should not define the intellectual hierarchy of the ACNS paper.

The ACNS contribution structure should be approximately:

## Contribution 1 — Security problem and model

Identify the risk that surrounding recovery-system mechanisms can reintroduce candidate-validation information even when the underlying threshold/password-protected primitive resists below-threshold offline guessing.

Define the relevant persistent-state adversary views.

## Contribution 2 — Secure recovery composition

Design a complete storage-separated private-key recovery architecture that preserves the target below-threshold offline-guessing property across:

- structured recovery input;
- suite binding;
- authenticated discovery;
- recovery descriptors;
- public configuration;
- encrypted backup storage;
- clean-device recovery;
- lifecycle transitions;
- authorization;
- threshold reconstruction.

## Contribution 3 — Multiple concrete cryptographic instantiations

Instantiate the architecture using:

- Yi TPASS;
- aPPSS.

Clearly characterize their different compromise semantics.

Do not describe the suites as interchangeable at recovery time.

Do not claim new proofs for the inherited primitives.

## Contribution 4 — End-to-end implementation and evaluation

Demonstrate the complete system and validate:

- persistent-state boundaries;
- allowed and forbidden flows;
- malformed/replayed/stale state handling;
- threshold subsets;
- lifecycle transitions;
- failure behavior;
- performance;
- artifact reproducibility.

---

# 6. Explicitly Answer: Why Is TPASS/PPSS Alone Not Enough?

This question must be answered early in the ACNS manuscript, preferably in the Introduction.

The paper should make the following distinction explicit:

> Cryptographic primitive security is not identical to complete recovery-system security.

The system surrounding a secure primitive may introduce new verification channels through:

- encrypted backup construction;
- metadata;
- public commitments;
- recovery packages;
- cue-derived helper data;
- policy versioning;
- canonicalization;
- resolver behavior;
- suite negotiation;
- fallback;
- stale state;
- rollback;
- cross-epoch state;
- mixed holder membership;
- configuration substitution;
- error messages;
- logs;
- crash artifacts;
- lifecycle transitions.

LOCUS should be positioned as an architecture designed specifically to prevent those mechanisms from silently destroying the intended below-threshold security boundary.

This argument is essential to establish novelty.

---

# 7. Strengthen the Online-Guessing Analysis

LOCUS currently does not claim a global or lifetime rollback-resistant attempt bound.

That limitation must remain explicit.

Do not falsely claim that LOCUS solves global rate limiting.

The ACNS paper must instead explain what security is gained by eliminating an offline predicate.

The paper should explicitly distinguish:

## Offline snapshot attacker

An attacker who has copied permitted persistent state should not be able to evaluate arbitrary candidates locally.

This attacker should not receive a local candidate-testing oracle from:

- cloud state;
- below-threshold holder state;
- cloud plus below-threshold holder state.

## Online attacker

Candidate evaluation requires live interaction with the recovery infrastructure under the selected suite and system authorization assumptions.

The paper should characterize exactly what an online attacker needs to obtain or compromise before candidate evaluation becomes possible.

The ACNS paper should explain why converting a snapshot attack into an interactive attack is meaningful even though LOCUS does not claim a global lifetime attempt limit.

Possible evidence may include:

- number of online protocol interactions per candidate;
- online recovery latency;
- service participation required;
- authorization prerequisites;
- observable infrastructure involvement.

Any such measurement must be presented as interaction cost or system behavior, **not** as cryptographic rate limiting unless the system actually guarantees it.

---

# 8. Preserve Suite-Specific Compromise Semantics

The ACNS paper must preserve the distinction between Yi and aPPSS.

For Yi:

- below-threshold state inherits the TPASS protection assumptions;
- threshold persistent-state compromise directly exposes the high-entropy recovery output.

For aPPSS:

- below-threshold state does not provide the candidate predicate under the inherited assumptions;
- threshold holder keys plus public masked-share/commitment state enable unbounded local candidate testing;
- the correct candidate yields the recovery output.

Never flatten these into a generic statement such as:

> threshold compromise breaks LOCUS.

The paper should show that LOCUS deliberately exposes the different semantics rather than hiding them behind a generic adapter.

This is a strength of the design.

---

# 9. Preserve Authorization vs. Reconstruction Separation

The current design separates:

- cryptographic reconstruction threshold `k-of-n`;
- authorization quorum.

This distinction must remain explicit.

The ACNS paper should explain that:

- authorization determines whether an operation is allowed to proceed;
- reconstruction determines whether sufficient cryptographic material exists to recover the suite output;
- authorization is not a substitute for cryptographic threshold security;
- local authorization records do not create a globally monotonic attempt history.

This separation should remain part of the architecture and threat model.

---

# 10. Preserve One-Suite-Per-Epoch and No-Fallback Design

Each recovery epoch must remain bound to exactly one selected suite.

The ACNS paper should emphasize:

- no recovery-time suite negotiation;
- no fallback between Yi and aPPSS;
- no trial of alternate suites;
- no cross-suite share mixing;
- no in-place translation of suite state;
- suite or policy changes create a new successor epoch.

This is not merely implementation hygiene.

It is part of preventing downgrade, cross-context, and unintended candidate-validation behavior.

---

# 11. Reposition CuePolicy

CuePolicy should remain in the paper, but it should no longer appear to be the primary novelty.

Its research role is:

> a strict security boundary that converts structured recovery input into deterministic client-local bytes without persisting candidate verifiers or generating fuzzy alternatives.

The ACNS paper should emphasize security-relevant behavior:

- deterministic encoding;
- explicit versioning;
- rejection of ambiguity;
- rejection of duplicate semantic values where required;
- no candidate lists;
- no persisted cue hash;
- no recovery hint;
- no implicit fallback.

The paper should **not** claim that the supported policies prove memorability or entropy.

Policies such as:

- location/person;
- coordinates;
- phone numbers;
- email addresses

should be treated as concrete examples demonstrating the interface, not as independent research contributions.

---

# 12. Human Study Policy

Do **not** add a human study merely for ACNS.

The current project does not establish:

- cue memorability;
- cue entropy;
- delayed reproducibility;
- accessibility;
- human recovery success;
- real-user error rates.

These must remain limitations.

Do not imply that structured inputs are secure because they are memorable.

Do not claim usability results without evidence.

The ACNS paper should focus on:

- system security;
- cryptographic composition;
- implementation;
- adversary views;
- recovery architecture.

---

# 13. Multi-Host Evaluation

The current reproducible deployment uses one Docker engine under one administrative domain.

This is useful for:

- reproducibility;
- deterministic evidence;
- artifact review;
- controlled failure testing.

However, it does not establish:

- host compromise independence;
- administrative independence;
- network-failure independence;
- geographic independence.

A future `ACNS_PLAN.md` should evaluate whether a small multi-host experiment is feasible after the existing PLAN is complete.

Preferred optional experiment:

- Client on one host;
- multiple threshold parties on separate VMs/hosts;
- storage on a separate host or VM;
- same cryptographic and protocol configuration.

Possible measurements:

- enrollment latency;
- successful recovery latency;
- wrong-input handling;
- one-holder failure;
- 2-of-3 recovery;
- 3-of-5 recovery;
- clean-client recovery;
- network overhead.

This experiment is desirable but lower priority than the formal composition security work.

If time is limited:

**formal security result > multi-host experiment**

The single-host deployment may remain the primary reproducible artifact.

---

# 14. Evaluation Narrative Changes

The current LOCUS project has extensive evidence infrastructure, including:

- persistent-state scenarios;
- flow scenarios;
- malformed-input tests;
- concurrency tests;
- lifecycle tests;
- threshold subset coverage;
- performance observations;
- artifact closure.

This is a strength.

However, the ACNS manuscript must avoid reading like a QA report.

The main paper should emphasize:

1. what security question is being tested;
2. what adversary view is represented;
3. what observation would violate the claim;
4. what the experiment shows;
5. what the experiment does **not** prove.

Detailed internal scenario identifiers and evidence-generation mechanics should be minimized in the main narrative unless necessary for scientific interpretation.

Where allowed by the venue, detailed reproduction information can move to:

- appendix;
- artifact documentation;
- supplementary material.

Do not remove claim-critical evidence.

---

# 15. Comparative Related Work

The ACNS paper should include a concise comparison against relevant recovery families.

At minimum, carefully compare LOCUS with:

- Shamir secret sharing;
- PPSS;
- TPASS;
- Memento;
- SafetyPin;
- SVR3;
- social/decentralized recovery systems;
- password-protected key retrieval systems.

The comparison should focus on dimensions relevant to LOCUS, such as:

- human-derived recovery input;
- threshold recovery;
- offline-guessing resistance;
- clean-device recovery;
- TEE/HSM requirement;
- storage separation;
- authenticated system configuration;
- suite binding;
- lifecycle handling;
- explicit reconstruction/authorization separation;
- system-level implementation/evaluation.

Every table entry must be verified against the cited work before publication.

Do not overstate LOCUS relative to SafetyPin, SVR3, or the underlying PPSS/TPASS literature.

The comparison should make clear that LOCUS is solving a different problem:

> preserving the intended threshold/password-protected security boundary across a complete software recovery architecture.

---

# 16. Threat-Model Presentation

The final ACNS manuscript should present the compromise boundary in a highly visible form.

A useful structure is a matrix containing views such as:

- cloud only;
- fewer than `k` Yi holders;
- fewer than `k` aPPSS holders;
- cloud + fewer than `k` holders;
- threshold Yi holders;
- threshold aPPSS holders;
- active Client;
- trusted host/controller;
- resolver/metadata observer.

For each view, specify:

- local offline cue-testing predicate?
- direct recovery-output exposure?
- private-key recovery?
- live honest-party interaction required?
- inside or outside the principal LOCUS claim?

This matrix should align exactly with the formal security model.

---

# 17. Proposed ACNS Paper Structure

The final ACNS manuscript should approximately follow:

## 1. Introduction

Include:

- private-key recovery problem;
- why ordinary encrypted backups are vulnerable to low-entropy recovery inputs;
- why primitive security is insufficient for complete recovery systems;
- motivating composition failure;
- central research question;
- concise contribution list.

## 2. System Model and Threat Model

Define:

- entities;
- persistent views;
- trusted infrastructure;
- corruption thresholds;
- online vs. offline attackers;
- suite-specific compromise effects.

## 3. Security Definitions

New or substantially expanded section.

Define:

- below-threshold offline-guessing resistance;
- exact persistent-state views;
- candidate-validation experiment;
- assumptions and exclusions.

## 4. LOCUS Architecture

Explain:

- storage separation;
- CuePolicy;
- descriptors;
- discovery;
- authentication;
- authorization/reconstruction separation;
- suite binding;
- clean-client model.

## 5. Protocol Construction

Describe:

- common framing;
- Yi instantiation;
- aPPSS instantiation;
- enrollment;
- recovery;
- successor epochs.

## 6. Security Analysis

Include:

- formal composition argument/theorem;
- suite-specific reasoning;
- metadata analysis;
- rollback analysis;
- online-guessing boundary;
- failure channels;
- active-client and controller boundary.

## 7. Implementation

Describe only implementation details necessary to understand or reproduce the research claims.

## 8. Evaluation

Organize around research questions rather than internal project gates.

Include:

- state-security evidence;
- flow evidence;
- failure/adversarial tests;
- performance;
- optional multi-host results;
- artifact reproduction.

## 9. Related Work

Include a verified comparative table.

## 10. Limitations

Keep the current conservative style.

## 11. Conclusion

Return directly to the system-level security property.

---

# 18. Abstract Narrative

The abstract should no longer read primarily as a component inventory.

It should begin with the security problem.

A target narrative structure is:

1. Low-entropy recovery input creates offline-guessing risk.
2. Threshold password-protected primitives can mitigate this below a corruption threshold.
3. A complete recovery system may accidentally reintroduce a candidate predicate through surrounding storage/configuration/lifecycle mechanisms.
4. LOCUS defines and implements a storage-separated recovery composition intended to preserve the below-threshold property across a clean-device recovery workflow.
5. The architecture is instantiated with Yi TPASS and aPPSS.
6. Security analysis and evaluation demonstrate the stated persistent-state boundary under explicit assumptions.
7. Clearly state limitations.

The abstract should not imply:

- new threshold cryptography;
- human memorability;
- global attempt control;
- production readiness;
- independent administration unless actually evaluated.

---

# 19. Introduction Narrative

The Introduction should establish the following logical chain early:

### Problem A

Private keys must be recoverable after device loss.

### Problem B

Human-derived recovery material is often low entropy.

### Problem C

Ordinary encrypted backups can become offline-guessing targets.

### Existing cryptographic response

TPASS/PPSS-style schemes can protect candidate testing below a corruption threshold.

### Missing systems question

What happens when that primitive is embedded inside:

- cloud storage;
- authenticated discovery;
- recovery packages;
- configuration metadata;
- multiple epochs;
- threshold parties;
- clean replacement devices;
- lifecycle operations?

### LOCUS question

Can the complete system preserve the desired below-threshold no-offline-predicate property?

### LOCUS answer

LOCUS constructs and evaluates an end-to-end architecture intended to preserve this boundary.

This progression should appear before detailed component descriptions.

---

# 20. Language and Claim Discipline

The ACNS paper must preserve the current manuscript's strong claim discipline.

Prefer:

- "under the selected suite assumptions";
- "for the evaluated persistent-state views";
- "does not expose a local offline predicate";
- "requires live protocol participation";
- "the implementation evidence supports";
- "the system does not claim".

Avoid:

- "LOCUS prevents password guessing";
- "LOCUS makes weak cues secure";
- "LOCUS guarantees rate limiting";
- "LOCUS is secure against threshold compromise";
- "LOCUS provides independent distributed trust" when all parties run under one operator;
- "LOCUS proves usability";
- "LOCUS is production ready".

---

# 21. What Must Not Be Changed Without Explicit Approval

Do not silently change:

- Yi suite equations or wire formats;
- aPPSS mapping;
- OPRF mode;
- threshold notation;
- domain-separation rules;
- descriptor bindings;
- authorization quorum;
- reconstruction profiles;
- storage-separation invariants;
- clean-client trust assumptions;
- inherited cryptographic assumptions;
- stated threshold-compromise consequences.

Any claim-impacting change requires:

1. explicit project-owner approval;
2. implementation update;
3. test/evidence update;
4. threat-model update;
5. manuscript update;
6. claim/evidence matrix update.

---

# 22. What Should Not Be Added Solely for ACNS

Do not waste time on:

- a rushed human-subject study;
- a new cryptographic primitive;
- cosmetic UI redesign unrelated to claims;
- artificial benchmark volume;
- unsupported claims of scalability;
- unsupported production deployment claims;
- unsupported global rollback resistance;
- unsupported TEE/HSM comparisons;
- arbitrary new cue families that do not strengthen the security story.

---

# 23. ACNS Revision Priority

After the current PLAN is complete, the future `ACNS_PLAN.md` should prioritize tasks approximately as follows.

## P0 — Critical

1. Freeze final implementation/evidence state.
2. Define formal below-threshold offline-guessing property.
3. Develop the LOCUS composition security argument/theorem.
4. Rewrite novelty and contribution statements.
5. Rewrite Abstract and Introduction around the security problem.
6. Clarify why TPASS/PPSS alone are insufficient for the complete system.

## P1 — Very High

7. Strengthen online-guessing analysis.
8. Build a precise threat-model matrix.
9. Create a verified related-work comparison table.
10. Reorganize evaluation around research questions.
11. Reduce project-QA language in the main narrative.
12. Ensure suite-specific compromise consequences are consistently stated.

## P2 — Valuable

13. Add multi-host evaluation if feasible.
14. Improve distributed-failure evaluation.
15. Improve performance interpretation.
16. Improve artifact presentation for external reviewers.

## Explicit non-goals

- human study;
- new cryptographic primitive;
- production-scale deployment;
- global rollback-resistant rate limiting unless separately redesigned and proven.

---

# 24. Transition Gate From PLAN to ACNS_PLAN

Do not create or execute the final ACNS revision plan until the current implementation PLAN has reached a stable completion point.

Before `ACNS_PLAN.md` begins, verify:

- all current PLAN phases are complete or explicitly closed;
- working tree is clean;
- final source commit is recorded;
- all required tests pass;
- final performance corpus is available;
- independent cryptographic mapping review is completed if required by the project;
- clean-host artifact reproduction is completed if required;
- final limitations are known;
- claim/evidence matrix is synchronized.

If any of these remain incomplete, `ACNS_PLAN.md` may document them as dependencies but must not invent their results.

---

# 25. Agent Workflow for Future AI Assistants

Every agent working on the ACNS version must begin by reading, in order:

1. existing project `AGENT.md`;
2. existing `PLAN.md`;
3. this `ACNS_AGENT.md`;
4. the latest authoritative LOCUS manuscript;
5. the final claim/evidence matrix;
6. `ACNS_PLAN.md` once it exists.

The agent must then determine whether the project is:

- still completing the original PLAN; or
- in the ACNS revision phase.

If the original PLAN is unfinished:

> Continue the original PLAN. Use `ACNS_AGENT.md` only as a constraint and future-publication guide.

If the original PLAN is complete:

> Follow `ACNS_PLAN.md`.

Never merge the two plans implicitly.

---

# 26. Definition of Success

The ACNS revision succeeds when a reviewer can clearly answer all of the following:

1. **What security problem does LOCUS solve?**
2. **Why do existing TPASS/PPSS primitives not solve the complete systems problem by themselves?**
3. **What exact adversary view does LOCUS protect against?**
4. **What is the formal security property?**
5. **Why should the complete LOCUS composition preserve that property?**
6. **What changes at threshold compromise for Yi and aPPSS?**
7. **What is the difference between offline and online guessing in LOCUS?**
8. **What does the implementation evidence actually establish?**
9. **What remains outside the claim?**
10. **Why is LOCUS a research contribution rather than only an integration project?**

If these questions cannot be answered clearly from the main paper, the ACNS revision is not complete.

---

# 27. Final Strategic Principle

The ACNS version should not try to make LOCUS appear broader than it is.

Its strongest research position is narrow and defensible:

> LOCUS studies how to preserve the below-threshold offline-guessing resistance of password-protected threshold recovery when that primitive is embedded inside a complete private-key recovery workflow with structured human-derived input, authenticated configuration, storage separation, authorization, lifecycle transitions, and clean replacement clients.

The paper should build a rigorous argument around that property and evaluate the exact boundaries under which it holds.

That is the core ACNS strategy.
