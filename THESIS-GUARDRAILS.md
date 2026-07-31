# Thesis Guardrails

## Core thesis

LOCUS provides a versioned client-side boundary from structured semantic input
to TPASS password input and composes it with separated encrypted backup storage
and threshold-party state. Under its declared assumptions, the cloud and fewer
than the TPASS threshold do not gain a local offline cue-testing predicate.

## Work that strengthens the thesis

The following work can improve implementation completeness and evidence without
changing the thesis:

- a common CuePolicy interface and registry;
- multiple immutable CuePolicy implementations;
- independent canonical-vector consumers;
- authenticated RecoveryDescriptor and discovery;
- true clean-client recovery;
- authenticated enrollment transport;
- explicit public-client admission;
- exact original-key identity verification;
- provider-neutral storage and additional adapters;
- multi-host deployment;
- deployed threshold variants;
- integrated successor lifecycle;
- bounded general party replacement;
- a UI over the stable protocol API;
- state and information-flow audits;
- concurrency, crash, property, and fuzz testing;
- performance and resilience evaluation;
- clean-host artifact reproduction;
- independent cryptographic and systems review.

These changes strengthen the existing system claim only after matching evidence
passes.

## Work that requires an explicit thesis or architecture decision

- changing the protected-key derivation path;
- replacing TPASS with another recovery primitive;
- making a global attempt bound a primary security claim;
- adding a monotonic authority or consensus service to the mandatory core;
- making identity recovery or public admission a scientific contribution;
- treating private resolver infrastructure as a new privacy contribution;
- making real-cloud integration a security result rather than an adapter;
- claiming independent administration;
- claiming general party replacement, proactive resharing, or Byzantine
  lifecycle;
- claiming threshold-compromise security;
- changing title, abstract, thesis, contribution hierarchy, claims, or
  limitations in the current manuscript.

Even a narrative change that preserves the thesis requires an exact proposed
delta and explicit owner approval before `paper/` is edited.

## Claims that require separate human or production evidence

Do not infer any of these from protocol tests or a UI:

- memorability;
- entropy of human-selected cues;
- comparative recall;
- usability;
- accessibility for a target population;
- reduction in user error;
- production security;
- side-channel resistance;
- secure forensic erasure;
- Internet-scale scalability;
- independent cryptographic audit.

## Interpretation rules

- Multiple CuePolicies show interface generality, not human suitability.
- A clean replacement VM shows state isolation, not forensic erasure.
- Separate VMs show host separation, not independent administration.
- Signed local attempt records show local auditability, not a global bound.
- A real provider shows adapter compatibility, not provider independence or
  production readiness.
- Bounded adversarial tests show the exact observed behavior, not proof.
- Tests of a cryptographic implementation show conformance and regression
  resistance, not a new security theorem.
