# Yi/aPPSS Selection, Comparison, and Successor Contract

Status: Exact P1.2 aPPSS recovery contract approved by D017 and independent
selectable-suite direction approved by D018. D018 supersedes D016's sole-aPPSS
cutover. No aPPSS implementation, selector release, paired evidence, or
manuscript change is complete.

## Source and scope

This analysis uses the complete local 58-page extended paper
*Password-Protected Threshold Signatures* (ASIACRYPT 2024) by Stefan
Dziembowski, Stanislaw Jarecki, Pawel Kedzior, Hugo Krawczyk, Chan Nam Ngo, and
Jiayu Xu. The ignored local PDF has SHA-256
`89654e3df97b0369a6a18bb5184e40fccb784f5f492b5f74a7cfdb2c7c211cf6`.
It is a research input, not a tracked repository or artifact member.

Only Section 3's Augmented Password-Protected Secret Sharing (aPPSS)
construction is relevant to the LOCUS recovery-secret layer. The paper's
augmented password-protected threshold-signature (aptSIG), threshold BLS, and
PFS signature extensions are not part of the planned LOCUS profile.

The primary source anchors are:

- abstract and introduction, pages 1--6, for the augmented compromise goal;
- Section 3.1 and Figure 3, pages 13--16, for the ideal functionality;
- Section 3.2, Figure 4, and Theorem 2, pages 16--18, for the protocol;
- the robustness discussion on page 30;
- Appendix C, pages 36--38, for the adaptive OPRF/2HashDH presentation;
- Appendix D, pages 39--43, for the aPPSS proof; and
- Appendix E, pages 43--45, for the explicit aPPSS-versus-PPSS corruption
  differences.

## How the construction works

Let the paper's public parameters be security parameter `lambda`, corruption
bound `t`, party count `n`, field `F = GF(2^lambda)`, a random-oracle hash `H`
with a `2*lambda`-bit output, and one independently keyed OPRF instance per
server.

### Initialization

For a password `pw`:

1. The user evaluates server `i`'s OPRF on `pw` and obtains
   `rho_i = F_i(pw)` for every server.
2. The user samples a random field element `s` and makes a degree-`t` Shamir
   sharing `(s_1, ..., s_n)`. The paper therefore reconstructs with `t+1`
   distinct shares.
3. Each share is masked as `e_i = s_i XOR rho_i`, and
   `e = (e_1, ..., e_n)`.
4. The user computes `[C || sk] = H(pw, e, s)`. `C` is the recovery check and
   `sk` is the high-entropy aPPSS output.
5. Every server stores the same public record `omega = (e,C)` together with its
   own index, session binding, and independent OPRF secret state. The user
   retains the password and public recovery handle, not `s`, `sk`, or the OPRF
   keys.

The masked-share vector and `C` can be treated as public only within the stated
model. They are not an offline password verifier without enough matching OPRF
secret states or online server evaluations.

### Recovery

For a candidate `pw'` and exactly one reconstruction set:

1. The client evaluates the OPRF on `pw'` with `t+1` servers.
2. It requires distinct, in-range server indices and the identical bound
   `omega` from every selected server.
3. It unmasks the selected shares with the returned OPRF outputs, interpolates
   `s'`, and recomputes `[C' || sk'] = H(pw', e, s')`.
4. It returns `sk'` only if `C' = C`; otherwise it returns failure.

The ideal functionality uses per-server tickets to express one online password
test per server participation. Corrupted servers can generate their own
tickets. A guess becomes fully offline when the adversary controls enough
servers to supply the complete reconstruction set.

## Threshold notation

The two projects use different meanings for `t`:

| Meaning | Paper notation | LOCUS notation |
| --- | --- | --- |
| Maximum server corruption covered by the aPPSS no-leakage result | `t` | `k-1` |
| Reconstruction threshold | `t+1` | `k` |
| Party count | `n` | `n` |

Therefore the planned LOCUS 2-of-3 aPPSS profile maps to the paper's
`t=1,n=3`, not `t=2,n=3`; the paired 3-of-5 profile maps to `t=2,n=5`.
Specifications, schemas, UI, evidence, and any later approved manuscript text
must use `k` for the LOCUS reconstruction threshold and state the mapping.

## Security result and validated comparison

Theorem 2 states that Figure 4 realizes the augmented ideal functionality in
the `(F_OPRF,F_AUTH)` hybrid when `H` is modeled as a random oracle. Appendix E
states the central augmentation explicitly: the prior PPSS functionality
automatically disclosed `sk` after `t+1` corruptions, whereas aPPSS requires the
adversary to perform an offline dictionary attack.

The corresponding LOCUS comparison is:

| Persistent adversary view for one bound epoch | Frozen Yi profile | Planned aPPSS profile |
| --- | --- | --- |
| Cloud/public state only | No local cue predicate under the composition assumptions | No local cue predicate under the composition assumptions |
| Fewer than reconstruction threshold `k` party states | No local cue predicate under the Yi assumptions | No local cue predicate under the approved aPPSS assumptions; an honest server is still required for each online test |
| `k` or more party/server states | Directly interpolate the shared password scalar, secret exponent, and digest; compute the high-entropy group secret without guessing | Evaluate candidates offline with the compromised OPRF keys and `omega`; wrong candidates fail `C`, and the correct candidate yields the high-entropy output |

The Yi result follows the current LOCUS implementation: `PartyState` stores one
Shamir share each of the password scalar, secret exponent, and secret digest,
all at the recovery threshold. It is not merely an inference from an experiment.

The approved precise statement is:

> For a static persistent-state compromise of fewer than reconstruction
> threshold `k`, neither the frozen Yi TPASS profile nor the proposed aPPSS
> profile provides a local offline cue-verification predicate under its stated
> assumptions. Compromise of `k` or more aPPSS servers instead exposes an
> offline dictionary-test capability: the recovery secret is obtained only
> when the adversary supplies the correct cue-derived password, whereas `k` Yi
> party states allow immediate interpolation of the shared password scalar and
> high-entropy recovery secret.

This statement requires all of the following qualifications:

- threshold aPPSS compromise is not secure against offline guessing; attempts
  are local and unrate-limited;
- residual protection then depends on the adversary's conditional distribution
  for the structured input and derived password, not on nominal password length;
- a correct guess recovers the high-entropy secret; aPPSS delays disclosure but
  does not prevent it;
- below-threshold attackers may still make online guesses through honest-server
  interactions, subject only to separately implemented admission/attempt
  controls;
- descriptor, backup, cloud, party, transcript, log, crash, and UI state must
  not introduce another verifier;
- the theorem is a random-oracle/ideal-OPRF/authenticated-initialization result,
  while the exact concrete OPRF assumptions must be reviewed separately;
- the comparison covers the declared static/adaptive corruption and persistent
  state boundary, not side channels, live client compromise, or proactive/mobile
  compromise; and
- the base Figure 4 flow may abort when a selected malicious server misbehaves.
  The paper sketches verifiable-OPRF/retry robustness but does not make that
  sketch part of the base aPPSS theorem.

## Common LOCUS composition and independent suites

Both selectable suites preserve the existing outer key-protection design. The
aPPSS branch is:

```text
structured input M
  -> CuePolicy_v(M) = Z_M or failure
  -> aPPSS-suite-domain password input p_M
  -> aPPSS.Initialize / aPPSS.Recover
  -> sk_appss, defined by LOCUS as S_R
  -> HKDF-SHA-256 wrapping key K_wrap
  -> AES-256-GCM protection of the private key
```

There is no extra independently sampled or threshold-shared unmasked recovery
secret between aPPSS and HKDF. Embedding Yi-style sharing of `S_R` inside an
aPPSS epoch would make `k` party states reveal `S_R` directly and would destroy
the augmented failure mode; this does not prevent separate Yi epochs from
remaining selectable.

Yi remains an independent first-class branch using its frozen password domain,
setup/recovery algebra, public parameters, party state, messages, and native
`S_R` encoding. The two branches meet only at the suite-neutral `S_R -> HKDF ->
AES` boundary. Protected-key generation/import, key-identity verification,
HKDF-SHA-256, AES-256-GCM, storage, bootstrap, admission, lifecycle, and common
client APIs keep the same meaning. No aPPSS object is represented as Yi state or
vice versa.

The aPPSS proof does not prove the entire LOCUS composition. LOCUS must review
the suite-to-HKDF mapping, authenticated backup metadata, descriptor binding,
role-state separation, error normalization, and lifecycle composition.

## Compatibility, selection, and successor switching

- `LOCUS-TPASS-YI-ZK-RISTRETTO255-v1`, its wire objects, vector, backup-v4,
  Compose-v2, and retained v2 evidence remain immutable.
- aPPSS receives new password domains, state and message formats, backup and
  descriptor bindings, service/API schemas, deployment profiles, and evidence
  paths.
- One epoch binds one recovery suite. Mixed Yi/aPPSS threshold sets and
  automatic downgrade are invalid.
- New enrollment explicitly selects either the frozen Yi adapter or the new
  aPPSS adapter before suite setup. Recovery obtains the suite only from the
  authenticated epoch descriptor and never tries another suite.
- Successor switching means: recover through the exact predecessor suite,
  explicitly retain it or choose the other suite, freshly enroll the selected
  successor, make every party/storage/descriptor binding durably ready, verify
  the same protected-key identity, activate it, and only then retire the
  predecessor. Yi-to-Yi, aPPSS-to-aPPSS, Yi-to-aPPSS, and aPPSS-to-Yi are
  distinct tested transitions.
- Party state is never translated in place. A client or service never interprets
  a Yi scalar share as an OPRF key or an aPPSS message as a Yi wire object.

## Approved D017 profile

`docs/APPSS-PROFILE.md` is the exact P1.2 contract. D017 selects:

1. Section 3/Figure 4 aPPSS only, excluding aptSIG;
2. the paper's 2HashDH shape with RFC 9497 OPRF-mode
   `ristretto255-SHA512`, independent per-server/per-epoch keys, canonical
   32-byte Ristretto encodings, and identity rejection;
3. `lambda=128` and degree-`k-1` Shamir sharing over polynomial-basis
   `GF(2^128)` modulo `x^128+x^7+x^2+x+1`, encoded in exactly 16 big-endian
   bytes;
4. a suite/epoch-derived 32-byte password input, 16-byte OPRF masks, and
   domain-separated SHA-256 for Figure 4's 16-byte `C` plus 16-byte `S_R`;
5. canonical public `omega=(e,C)` digest-bound across party, backup, and
   descriptor state;
6. authenticated initialization and request/response bindings covering suite,
   backup, epoch, policy, membership, threshold, configuration, party,
   operation, authorization, and fresh online session;
7. strict canonical decoding, generic recovery rejection, and base Figure 4
   abort-only malicious-server behavior, without the optional VOPRF extension;
8. a first evaluated `k=2,n=3` profile; and
9. a first implementation/evidence claim limited to static persistent-state
   compromise, while separately recording the theorem's hybrid/random-oracle
   basis and the concrete OPRF assumptions.

Final suite/wire identifiers, schemas, bounds, and canonical vectors remain a
P5A.1 gate and must be assigned together. They may not change the approved
primitives, state split, threshold mapping, or claim boundary.

D018 retains that exact first-profile order and adds a matched `k=3,n=5`
aPPSS profile after configuration generalization. Yi is exercised under both
the 2-of-3 and 3-of-5 conditions as an independent adapter. Within each pair,
the suites share the same CuePolicy, synthetic protected key, authorization
topology/quorum, storage, admission, network/failure schedule, host class, and
measurement definitions. All three 2-of-3 subsets and all ten 3-of-5 subsets
must pass for each applicable suite/profile.

## Implementation impact

P5A must introduce an explicit suite registry/selector, keep the Yi adapter
first-class, and add a separate native aPPSS core/binding. The affected surfaces
include backup and descriptor schemas, party service messages, durable attempt
bindings, SQLite state, enrollment and recovery state machines, lifecycle
packages, deployment constants, snapshot parsers, redaction, build locks,
performance phases, evidence schemas, documentation, and artifact allowlists.

The current evaluated networkless provisioner centrally creates all Yi party
states. It may support generated unit fixtures, but it cannot establish the
aPPSS authenticated-distributed-initialization assumption. The evaluated aPPSS
profile requires P3's authenticated enrollment transport so every server
creates and retains its own OPRF key and the client distributes the identical
bound `omega` to authenticated recipients.

## Evidence and claim boundary

New evidence must separately cover correctness, cloud-only, every evaluated
below-`k` coalition, matching cloud-plus-below-`k` state, exact-`k` and
all-server compromise, cross-suite rejection, crash-safe same-suite and
cross-suite successors, and performance. Paired 2-of-3 and 3-of-5 comparisons
use exact common-condition manifests while retaining separate suite/topology
result paths. The Yi/aPPSS threshold comparison uses fixed synthetic state and
fixed candidates and emits aggregate categories only.

P5A.3 now implements the independent adapter, no-fallback registry, common
backup-v5 encryption composition, transient client protocol, per-holder SQLite
state, and a pinned mutual-TLS subprocess recovery test. The central native
setup function remains fixture-only. P5A.4 must still perform initialization
through the authenticated enrollment boundary, and P5A.5 must still integrate
new enrollment and successor switching before release.

Tests and snapshots do not prove the aPPSS theorem, cue entropy, human
memorability, production security, side-channel resistance, proactive security,
or a rollback-resistant global attempt bound. The result is inherited from the
paper and limited to the reviewed concrete profile and LOCUS composition.

## Manuscript boundary

M-APPPSS-001 in `DECISIONS.md` reflects the superseded sole-active-aPPSS
direction and is stale under D018. No file under `paper/` may change until the
owner receives and separately approves a replacement exact change set after the
implementation, review, and evidence gates close.
