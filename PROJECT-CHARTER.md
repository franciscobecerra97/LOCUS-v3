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
- multi-host TPASS parties with distinct identities and state;
- a safe, instrumented enrollment and recovery UI;
- reproducible security, failure, information-flow, and performance evidence;
- independent clean-host reproduction and external technical review.

## Scientific thesis

LOCUS combines:

1. local, deterministic processing of structured recovery input;
2. TPASS-mediated recovery of a random group secret;
3. derivation of a symmetric wrapping key from that secret;
4. encrypted private-key storage at a separate cloud role; and
5. threshold state held by recovery parties.

The intended security boundary is that the cloud, fewer than the TPASS
threshold, or their matching persistent snapshots do not gain an offline test
for candidate cues.

## What is inherited

- TPASS construction and security assumptions.
- Password-to-random-secret recovery.
- HKDF and AEAD primitives.
- The current versioned location-person CuePolicy.
- The current native TPASS and backup implementation.

## What LOCUS contributes as a system

- the precise semantic-input-to-protocol boundary;
- versioning and failure behavior for structured CuePolicies;
- storage and role separation;
- explicit bootstrap, admission, lifecycle, and information-flow contracts;
- an integrated reference implementation;
- bounded, reproducible evidence and limitations.

## Non-goals without separate approval and evidence

- inventing a new TPASS construction;
- proving cue memorability, entropy, or usability;
- fuzzy matching or automatic candidate enumeration;
- recovery after threshold compromise;
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
