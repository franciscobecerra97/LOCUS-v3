# Mechanism-Level Related Work and Novelty Challenge

Status: primary-source comparison for the ASIACCS 2027 Cycle 1 novelty gate.
Last verified: 2026-07-24. The manuscript's currently cited sources are
recorded in `docs/reference-audit.md`.

## Purpose and scope

This document tests whether LOCUS has a defensible contribution after comparing
mechanisms, assumptions, and evidence—not just problem statements. It covers the
closest work in password-protected secret/key retrieval, encrypted backup,
distributed attempt control, auditable custodial recovery, privacy-preserving
account recovery, social recovery, and fuzzy/biometric reconstruction.

The comparison deliberately separates four properties that are often conflated:

1. preventing a stored snapshot from becoming an offline password oracle;
2. distributing custody or recovery authority;
3. enforcing a finite online-guess budget despite replay, rollback, and failure;
4. authorizing recovery without letting unauthenticated outsiders exhaust that budget.

LOCUS does not inherit properties 2--4 merely by instantiating TPASS.

## Bottom-line novelty finding

The broad claim "distributed, rollback-resistant, rate-limited key recovery from
a human secret" is **not novel**. SafetyPin already combines encrypted backup,
threshold recovery across an HSM fleet, and a distributed append-only log that
enforces a global per-user recovery-attempt limit. SVR3 already combines PPSS,
multiple heterogeneous trust domains, bounded PIN guesses, recovery admission,
fault tolerance, and formally modeled rollback-resistant replication in a
deployed system.

The strongest defensible LOCUS direction is narrower:

> A hardware-independent, storage-separated TPASS recovery architecture with an
> explicit versioned cue-policy boundary, a role-separated same-host prototype,
> snapshot-boundary and native 2-of-3 measurements, and an explicit
> bounded negative result for quorum-only rollback control.

This remains a systems-composition contribution rather than a new threshold
primitive or a completed global attempt-bound mechanism. The paper must not
claim that distributed logs, rollback-resistant attempt counters, PPSS-backed
key recovery, or threshold encrypted backup are themselves new. Independently
administered parties, realistic resolver behavior, real-provider storage,
human-subject cue evidence, and rollback-resistant attempt control remain future
work.

## Closest systems

### SafetyPin (OSDI 2020)

SafetyPin is the closest prior system to LOCUS's global-ledger idea. It encrypts a
backup under an AES key, Shamir-shares that key, and uses a PIN to select a hidden
subset of HSM public keys. Recovery requires threshold decryption shares from the
selected HSMs. Before releasing shares, HSMs require a Merkle inclusion proof that
the recovery is present in a distributed append-only log. The log enforces a
global per-user attempt limit and supports monitoring. HSMs collectively retain
and update the log digest while an untrusted service provider stores the full log.

Mechanism-level overlap with LOCUS:

- encrypted backup plus separately mediated key recovery;
- threshold shares rather than one recovery custodian;
- an untrusted coordinator/storage service plus distributed state holders;
- pre-response proof that an attempt was globally recorded;
- a global per-identifier limit rather than independent per-subset counters;
- append-only state intended to stop a malicious data center from resetting guesses.

Material differences:

- SafetyPin relies on physically protected HSM state, puncturable encryption, and
  a large provider-operated HSM fleet; LOCUS proposes ordinary independently
  operated services plus explicit quorum and surviving-freshness-anchor assumptions.
- SafetyPin's PIN selects the hidden HSM subset through location-hiding encryption;
  LOCUS uses TPASS so any enrolled threshold subset can process the same password
  attempt without learning final success.
- SafetyPin's paper sketches fixed or periodic attempt budgets and leaves HSM
  membership management as an unimplemented log use. LOCUS targets explicit epoch
  retirement, joint reconfiguration, party replacement, and counter migration.
- SafetyPin evaluates hardware scalability and compromise distribution. LOCUS
  must evaluate the different safety/availability costs of independent software
  authorizers; it cannot reuse SafetyPin's HSM assumptions or results.

Primary source: [Dauterman, Corrigan-Gibbs, and Mazières, "SafetyPin: Encrypted Backups with Human-Memorable Secrets," OSDI 2020](https://www.usenix.org/conference/osdi20/presentation/dauterman-safetypin).

### Secure Value Recovery 3 (OSDI 2024)

SVR3 is the closest end-to-end system and the most serious novelty challenge.
It distributes PIN-protected key recovery across heterogeneous enclave clusters in
three cloud providers. It instantiates PPSS so a server does not learn whether a
PIN attempt was correct, deletes key material after bounded use, authenticates
clients before allowing attempts, and replicates guess counts using a modified
Raft protocol designed and TLA+-checked for physical rollback attacks.

SVR3 also analyzes rotating trust-domain subsets. With `n` domains, compromise
threshold `t`, and per-domain usage limit `u`, it gives a bound of
`floor(nu/(t+1))` PIN attempts under its stated assumptions. Thus, "we handle
subset rotation, admission, rollback, and bounded guesses" is not by itself a
LOCUS novelty statement.

Material differences:

- SVR3 relies on attested heterogeneous enclaves and enclave-specific rollback
  granularity; LOCUS's scoped prototype uses ordinary software processes and
  does not provide an equivalent rollback anchor or independent-operator evidence.
- SVR3's bound arises from per-domain use limits and PPSS threshold structure.
  LOCUS's former exact global `B_eff` target is not achieved; P5.13 instead
  records a rollback counterexample for its quorum-only ledger.
- SVR3 uses one application provider and an authentication server. LOCUS separates
  encrypted object storage from TPASS party state and models resolver and
  orchestration roles, but public admission and independent administration are absent.
- SVR3 already provides deployed performance and fault evidence at very large
  scale. LOCUS should not compete on maturity; it should compare assumptions,
  storage composition, cue processing, rollback limitations, and lifecycle scope.

Primary source: [Connell et al., "Secret Key Recovery in a Global-Scale End-to-End Encryption System," OSDI 2024](https://www.usenix.org/conference/osdi24/presentation/connell).

### Password-Protected Key Retrieval and WhatsApp backup

PPKR formalizes password-only retrieval of a high-entropy key and explicitly
includes resistance to offline attacks, one password guess per session, key
authenticity, and an upper limit on incorrect recoveries. The 2024 CCS work studies
several HSM corruption levels and gives constructions ranging from encrypt-to-HSM
to an OPRF-based design. The WhatsApp backup analysis is a concrete predecessor
using OPAQUE and HSM-held password files/counters.

LOCUS differs primarily in applying TPASS to structured-input private-key
recovery while separating the encrypted backup object from party state. Its
partial party ledger is not stronger attempt authority than the cited HSM
systems. It must not imply that password-only key retrieval, a ten-guess deletion
counter, OPRF-based recovery, or resistance to a malicious front-end is new.

Primary sources:

- [Faller et al., "Password-Protected Key Retrieval with(out) HSM Protection," CCS 2024](https://doi.org/10.1145/3658644.3690358).
- [Davies et al., "Security Analysis of the WhatsApp End-to-End Encrypted Backup Protocol," CRYPTO 2023](https://doi.org/10.1007/978-3-031-38551-3_11).

### PPSS, TPASS, and Memento

PPSS and TPASS provide the cryptographic no-offline-oracle building block. The
client supplies a low-entropy password online; below-threshold server compromise
does not by itself yield a local correctness test under each construction's
assumptions. Memento and later PPSS work similarly address reconstruction from a
single password in hostile or password-only environments.

LOCUS inherits this line's password-protected reconstruction property. Its
scoped contribution begins where primitive papers stop: separated backup
storage, deterministic structured-input handling, resolver leakage, concrete
composition, explicit lifecycle/rollback limitations, and evaluated behavior.

Verified primary sources:

- [Bagherzandi et al., "Password-Protected Secret Sharing," CCS 2011](https://doi.org/10.1145/2046707.2046758).
- [Camenisch et al., "Memento," CRYPTO 2014](https://doi.org/10.1007/978-3-662-44381-1_15).
- [Jarecki, Kiayias, Krawczyk, and Xu, "Highly-Efficient and Composable Password-Protected Secret Sharing," EuroS&P 2016](https://doi.org/10.1109/EuroSP.2016.30).
- [Yi et al., "Efficient Threshold Password-Authenticated Secret Sharing Protocols for Cloud Computing," JPDC 2019](https://doi.org/10.1016/j.jpdc.2019.01.013).

### Acsesor and guardian/audit recovery

Acsesor encrypts a secret, distributes recovery responsibility across user-chosen
guardians, and requires recovery requests to appear in a privacy-preserving
transparency ledger before guardians respond. It supports flexible policies such
as delay, second factors, and guardian-enforced rate limiting. Its ledger requires
an additional root of trust such as a bulletin board, trusted hardware, or another
trusted party.

LOCUS differs because its recovery factor is processed through TPASS rather than
guardian attestation or server authentication. It does not claim an exact global
attempt budget. Acsesor already occupies the broad space of separated ciphertext,
distributed recovery parties, request logging, policy enforcement, and auditable
secret release. LOCUS must cite and compare it directly.

Primary source: [Chase et al., "Acsesor: A New Framework for Auditable Custodial Secret Storage and Recovery," IACR ePrint 2022/1729](https://eprint.iacr.org/2022/1729).

### Privacy-preserving account recovery

Little, Qin, and Varia design deployed account recovery for a service that hides
the user list even from the provider. Their partly oblivious PRF supports online
rate limiting without bounding new account creation. This is not threshold key
retrieval, but it is the closest comparison for identity privacy and the tension
between private identifiers, admission, and per-account attempt control.

Primary source: [Little, Qin, and Varia, "Secure Account Recovery for a Privacy-Preserving Web Service," USENIX Security 2024](https://www.usenix.org/conference/usenixsecurity24/presentation/little).

### Social, recovery-code, and custodial approaches

Recovery codes and paper seeds place a high-entropy bearer secret with the user;
loss means lockout and theft can mean immediate compromise. Custodial services
can reset access but concentrate authority. Social/guardian recovery distributes
authorization among people or devices, making guardian selection, collusion,
availability, and relationship drift part of the security model.

LOCUS's recovery parties are not identity witnesses and should not decide whether
the claimant "is" the user. Admission only prevents cheap third-party budget
exhaustion; TPASS evaluates the client-held recovery input. This is a meaningful
mechanism distinction, but not proof that structured cues are memorable or hard
to guess.

### Fuzzy, biometric, and memory-derived reconstruction

Fuzzy commitments/extractors and biometric key generation reconstruct stable key
material from noisy measurements using public helper data. Their central issues
are noise tolerance, entropy loss, cross-matching, biometric privacy, and helper
data. LOCUS instead requires deterministic cue-policy evaluation before TPASS,
including resolution and canonicalization when the selected policy needs them.
It does not tolerate noisy cue values cryptographically and must define ambiguity
and drift as explicit client policy behavior.

Reminisce is a direct memory-based comparison because it uses distinctive pictures
and personal memory for blockchain private-key generation/recovery. LOCUS should
describe location--person pairs only as one structured-input case study and should
not infer human-memory or entropy results from software determinism.

Primary sources:

- [Ballard, Kamara, and Reiter, "The Practical Subtleties of Biometric Key Generation," USENIX Security 2008](https://www.usenix.org/event/sec08/tech/full_papers/ballard/ballard_html/index.html).
- [Seo et al., "Reminisce," Mathematics 2022](https://doi.org/10.3390/math10122047).

## Compact mechanism comparison

| System family | Human factor | Distributed recovery trust | Offline-guessing boundary | Attempt control and rollback | Main distinction from LOCUS |
| --- | --- | --- | --- | --- | --- |
| TPASS/PPSS/Memento | Password | Multiple protocol servers | Core primitive goal below its corruption threshold | Generally outside primitive scope | LOCUS inherits this cryptography |
| PPKR/WhatsApp | Password/PIN | Usually server plus HSM | Strong while required HSM state remains protected; corruption levels are explicit | HSM counter/deletion limit | LOCUS studies storage-separated TPASS recovery without claiming equivalent hardware-backed rate limiting |
| SafetyPin | Short PIN | Threshold subset from a large HSM fleet | Backup ciphertext hides selected HSMs; compromise threshold is hardware-fleet based | Global HSM-maintained append-only log before share release | SafetyPin has a stronger completed attempt-control story; LOCUS differs in cue policy and software TPASS composition |
| SVR3 | PIN | PPSS across heterogeneous enclave/cloud domains | PPSS plus enclave trust | Bounded uses, authenticated admission, modified rollback-resistant Raft protocol, TLA+ model | Closest stronger system; LOCUS does not claim comparable rollback-resistant usage limits or independent operators |
| Acsesor | Server auth plus optional policies/factors | User-chosen guardians | Depends on policy; not intrinsically TPASS | Transparency ledger; optional guardian rate limits and delay | LOCUS makes password evaluation threshold-private but leaves robust admission/budget control to future work |
| Private account recovery | Email/security answers | Primarily one service | Protects identity/account list with oblivious PRF | Online rate limiting | Relevant to private identifiers/admission, not key custody |
| Social recovery | Guardian approval or shares | Human/device guardians | Usually not a password-oracle problem | Approval thresholds, delays, contracts, or policies | LOCUS parties evaluate TPASS rather than attest identity |
| Fuzzy/biometric | Noisy measurement | Often local or helper-data based | Depends on extractor/helper-data assumptions | Usually not a distributed online budget | LOCUS uses deterministic resolution, not fuzzy reconstruction |

## Required paper positioning

The abstract and contribution list should follow these rules:

- Do not claim the first distributed, rate-limited, auditable, or rollback-resistant
  encrypted-backup recovery system.
- Do not present a quorum-certified hash chain alone as novel; SafetyPin already
  couples a distributed append-only log to pre-release authorization, while SVR3
  already couples PPSS usage limits to rollback-resistant consensus.
- State that TPASS/PPSS security is inherited and name the exact construction.
- Frame LOCUS as a hardware-independent storage-separated TPASS architecture and
  same-host research prototype. Do not imply independent operators or an exact
  global budget.
- Treat the cue-policy boundary as a systems contribution, while making clear
  that the three-pair reference policy is one case study rather than a
  memorability, entropy, or authentication breakthrough.
- Compare availability honestly: eliminating HSM assumptions leaves online
  rate limiting, rollback resistance, admission, refusal, and false lockout as
  unresolved deployment problems.

## Evidence needed for the scoped novelty claim

The architecture/prototype paper must show:

1. exact cloud, below-threshold, and combined snapshot boundaries with no local
   cue verifier in the tested implementation;
2. deterministic cue-policy and drift behavior without memorability claims;
3. complete native recovery through separated cloud and party roles;
4. claim-scoped malformed, cloud-binding, resolver, lifecycle, and output-safety
   failures;
5. reproducible end-to-end cost and resilience measurements for the implemented
   core; and
6. a comparison against SafetyPin, SVR3, PPKR, social recovery, and ordinary
   encrypted backups that explicitly concedes LOCUS's weaker attempt-control and
   deployment evidence.

The accepted residual risk is that this may still be judged a careful
integration rather than a new security mechanism. The paper must address that
risk with precision and evidence, not stronger unsupported claims.
