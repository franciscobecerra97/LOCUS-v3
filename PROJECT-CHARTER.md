# Project Charter

## Objective

Develop LOCUS from a compact same-host research prototype into a complete,
realistically deployable reference recovery system while preserving the
existing storage-separation and no-offline-oracle thesis.

This repository jointly advances the reference system, its evidence, and the
owner-approved manuscript. The imported manuscript remains the authoritative
baseline until the owner approves an exact narrative delta; implementation
progress alone does not change it.

The target system should eventually provide:

- explicit clean-client bootstrap and recovery discovery;
- an authenticated, versioned RecoveryDescriptor;
- authenticated enrollment and recovery transport;
- public-client admission through a separately modeled authorization layer;
- exact original-key recovery and post-recovery successor enrollment;
- multiple immutable CuePolicy implementations behind one contract;
- provider-neutral backup and descriptor storage;
- multi-host recovery parties with distinct identities and suite-bound state;
- a safe, instrumented enrollment and recovery UI;
- reproducible security, failure, information-flow, and performance evidence;
- independent clean-host reproduction and external technical review.

## Scientific thesis

The active imported baseline combines:

1. local, deterministic processing of structured recovery input;
2. TPASS-mediated recovery of a random group secret;
3. derivation of a symmetric wrapping key from that secret;
4. encrypted private-key storage at a separate cloud role; and
5. threshold state held by recovery parties.

The intended security boundary is that the cloud, fewer than the TPASS
threshold, or their matching persistent snapshots do not gain an offline test
for candidate cues.

D018 supersedes D016's sole-aPPSS cutover without changing that below-threshold
system thesis. D020 activates the P5A application/component interface after a
provisional internal mapping assessment: frozen Yi TPASS and D017 aPPSS are
independent first-class suites selected explicitly for each enrollment or fresh
successor epoch. Both solve the same password-protected recovery-secret problem
and feed the same HKDF/AES protected-key path, but retain distinct state,
messages, assumptions, and threshold-compromise behavior. Enough aPPSS server
state enables offline guessing but does not directly reveal `S_R` before a
correct password guess; matching Yi threshold state directly exposes its
high-entropy recovery secret. No low-entropy-cue, rate-limit, or continued
threshold-security claim follows.

D017 and `docs/APPSS-PROFILE.md` freeze the initial successor recovery contract:
Figure 4 aPPSS with a concrete ristretto255/SHA-512 2HashDH OPRF,
`GF(2^128)`, a SHA-256-derived 16-byte commitment and 16-byte `S_R`, first
2-of-3 evaluation, and abort-only robustness. D018 additionally requires paired
Yi/aPPSS 2-of-3 and later 3-of-5 profiles under matching system conditions.
The 2-of-3 application/component path is implemented and provisionally accepted
with explicit qualifications under D020. P6.3 adds matched same-host process
deployment profiles for 2-of-3 and 3-of-5; this is not independent human
validation, retained evidence, host independence, or manuscript wording.
D021 authorizes those paired deployments at 2-of-3 and 3-of-5 over five
authorizers with a separate 4-of-5 authorization quorum. P6.4 may claim only
the exact host-separation tier actually demonstrated; administrative
independence still requires genuine independent operators.

## What is inherited

- TPASS construction and security assumptions.
- Password-to-random-secret recovery.
- HKDF and AEAD primitives.
- The current versioned location-person CuePolicy.
- The current native TPASS and backup implementation.

The aPPSS paper, future profile, implementation, and evidence are not inherited
baseline facts and must receive new identifiers and provenance.

## What LOCUS contributes as a system

- the precise semantic-input-to-protocol boundary;
- versioning and failure behavior for structured CuePolicies;
- storage and role separation;
- explicit bootstrap, admission, lifecycle, and information-flow contracts;
- an integrated reference implementation;
- bounded, reproducible evidence and limitations.

## Non-goals without separate approval and evidence

- claiming either Yi TPASS or aPPSS as a new LOCUS construction;
- proving cue memorability, entropy, or usability;
- fuzzy matching or automatic candidate enumeration;
- preventing offline guessing or guaranteeing recovery-secret confidentiality
  after aPPSS reconstruction-threshold compromise;
- hiding resolver use from the resolver;
- global rollback-resistant attempt limiting;
- Byzantine availability;
- forensic secure erasure;
- production security or side-channel resistance;
- independent administration based only on separate local hosts;
- real-user or production-account experimentation.

## Success condition

The project succeeds when an unfamiliar reviewer can take an isolated clean
client, use only the declared bootstrap inputs and fictional recovery cues,
authenticate the current configuration, contact the required online parties,
recover the exact original synthetic private key, verify its public identity,
and reproduce the bounded security and performance evidence without hidden
developer state. The manuscript, claim/evidence matrix, technical
documentation, generated inputs, artifact, and rendered PDF must describe that
exact evaluated system consistently.
