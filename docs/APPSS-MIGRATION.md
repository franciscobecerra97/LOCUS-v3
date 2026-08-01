# aPPSS Successor Analysis and Migration Contract

Status: Owner-approved migration direction under D016 and exact P1.2 recovery
contract under D017. No aPPSS implementation, evidence, active-profile cutover,
or manuscript change is complete.

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
`t=1,n=3`, not `t=2,n=3`. Specifications, schemas, UI, evidence, and manuscript
text must use `k` for the LOCUS reconstruction threshold and state the mapping.

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

## LOCUS composition

The successor preserves the existing outer key-protection design:

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
secret between aPPSS and HKDF. Keeping the current Yi sharing of `S_R` alongside
aPPSS would make `k` party states reveal `S_R` directly and would destroy the
augmented failure mode.

The aPPSS proof does not prove the entire LOCUS composition. LOCUS must review
the suite-to-HKDF mapping, authenticated backup metadata, descriptor binding,
role-state separation, error normalization, and lifecycle composition.

## Compatibility and migration

- `LOCUS-TPASS-YI-ZK-RISTRETTO255-v1`, its wire objects, vector, backup-v4,
  Compose-v2, and retained v2 evidence remain immutable.
- aPPSS receives new password domains, state and message formats, backup and
  descriptor bindings, service/API schemas, deployment profiles, and evidence
  paths.
- One epoch binds one recovery suite. Mixed Yi/aPPSS threshold sets and
  automatic downgrade are invalid.
- Existing Yi epochs remain recoverable through the legacy adapter.
- Migration means: recover through Yi, freshly enroll a new aPPSS epoch, make
  every party/storage/descriptor binding durably ready, verify successor
  recovery, activate it, and only then retire the Yi predecessor.
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

## Implementation impact

P5A must introduce a suite-neutral recovery interface and a separate native
aPPSS core/binding while preserving the Yi adapter. The affected surfaces
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
all-server compromise, cross-suite rejection, crash-safe migration, and
performance. The Yi/aPPSS threshold comparison uses fixed synthetic state and
fixed candidates and emits aggregate categories only.

Tests and snapshots do not prove the aPPSS theorem, cue entropy, human
memorability, production security, side-channel resistance, proactive security,
or a rollback-resistant global attempt bound. The result is inherited from the
paper and limited to the reviewed concrete profile and LOCUS composition.

## Manuscript boundary

M-APPPSS-001 in `DECISIONS.md` records the proposed future paper sections and
claim. It remains pending. No file under `paper/` may change until the owner
separately approves that exact change set after the implementation, review, and
evidence gates close.
