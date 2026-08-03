# P5A.7 Internal Recovery-Suite Mapping Assessment

Status: `Provisionally accepted with required qualifications`; independent
human cryptographic validation remains pending under D020.

Assessment date: 2026-08-03

Cryptographic implementation reviewed: `f92b302`

Assessor: OpenAI Codex, acting at the owner's request as an internal technical
assessor

Independence: Not independent. Codex contributed to the implementation and its
documentation. This record must never be represented as an independent audit
or independent cryptographic review.

Conflicts: Prior implementation and documentation contribution to the reviewed
repository.

## Disposition

| Boundary | Provisional internal disposition | Human status |
| --- | --- | --- |
| Frozen Yi TPASS mapping | Accepted with required qualifications | Pending |
| D017 aPPSS mapping | Accepted with required qualifications | Pending |
| LOCUS outer composition | Accepted with required qualifications | Pending |
| Overall | Accepted with required qualifications for implementation chronology only | Pending |

No claim-blocking or correction-required implementation defect was found in
the scoped mapping. P6 work may start under D020. This assessment does not
satisfy D019's independence requirement and cannot support manuscript wording,
a statement that either suite was independently reviewed, a production release
claim, or promotion of P5A.6 development regression into paper evidence.

## Sources and scope

The assessment compared the implementation with:

- Xun Yi et al., *Efficient Threshold Password-Authenticated Secret Sharing
  Protocols for Cloud Computing* (2019), Section 3.2, Figure 3, correctness in
  Section 3.3, and Section 4.2/Theorems 3--4. The author-hosted primary preprint
  used for this assessment is
  <https://www.dcs.warwick.ac.uk/~fenghao/files/JPDC.pdf>.
- Xun Yi et al., *Practical Threshold Password-Authenticated Secret Sharing
  Protocol* (ESORICS 2015), as the predecessor identified by the 2019 paper.
  The exact implemented one-phase zero-knowledge construction is reviewed
  against the 2019 Figure 3 presentation.
- *Password-Protected Threshold Signatures* (2024), Section 3, Figure 3 ideal
  functionality, Figure 4 construction, Theorem 2, Appendix C's 2HashDH
  construction/proof, and the discussion distinguishing aPPSS from PPSS. The
  owner-supplied file
  `extra/2024 - augmented Password-Protected Secret Sharing (aPPSS).pdf` is an
  ignored research input and is not redistributed.
- RFC 9497's base OPRF mode and ristretto255-SHA512 ciphersuite as the concrete
  OPRF profile selected by D017.

The reviewed implementation/specification boundary includes:

- `tpass-core/src/lib.rs`, `tpass-core/src/wire.rs`, the native Yi vector,
  `tpass-python/src/lib.rs`, `prototype/locus/tpass.py`, and
  `prototype/locus/yi_compat.py`;
- `appss-core/src/lib.rs`, the native aPPSS vector,
  `tpass-python/src/lib.rs`, `prototype/locus/appss.py`,
  `appss_client.py`, `appss_formats.py`, `appss_party.py`, and
  `appss_party_http.py`;
- `prototype/locus/recovery_suite_registry.py`,
  `selectable_suite_lifecycle.py`, `suite_backup.py`, and
  `suite_compromise_regression.py`;
- `PROTOCOL-INVARIANTS.md`, `docs/crypto-design.md`,
  `docs/APPSS-PROFILE.md`, `docs/APPSS-WIRE-FORMAT.md`,
  `docs/backup-cryptography.md`, `docs/SYSTEM-INTERFACES.md`,
  `docs/INFORMATION-FLOW.md`, and the associated conformance, selection,
  lifecycle, transport, backup, and compromise-regression tests.

This is a construction/claim mapping assessment. It is not a complete code
audit, new security proof, side-channel analysis, constant-time certification,
formal UC composition proof, production threat assessment, human-cue entropy
study, or review of every LOCUS service.

## Method

For each suite, the assessment traced:

1. enrollment inputs, sampled secrets, sharing degree, and durable state;
2. the online request, holder response, client reconstruction, and final check;
3. the exact public and persistent state available below and at threshold;
4. every concrete group, field, OPRF, hash, framing, and domain adaptation;
5. the suite output entering HKDF/AES and every stored public binding; and
6. selector, descriptor, lifecycle, and error behavior for cross-suite paths.

The fixed vectors and tests were used as implementation consistency checks,
not as substitutes for the source security arguments. The completed provisional
classifications are recorded in `docs/RECOVERY-SUITE-DEVIATIONS.md`.

## Frozen Yi TPASS findings

### Equation mapping

The implemented construction follows the 2019 paper's Figure 3 protocol in
additive notation:

- enrollment shares the password scalar, secret exponent, and
  `H(recovery_id, group_secret)` using independent degree-`k-1` polynomials;
- the client request is `A = r*G1 - pw*G2`, corresponding to
  `g1^r * g2^{-pw}`;
- holder `i` forms `B_i = r_i*G1 + a_i*f1(i)*G2`, samples `c_i,d_i`, and emits
  the additive form of the paper's one-equation proof;
- every selected holder checks
  `delta_i*G1 = h_i*C_i + H_i*D_i` before responding;
- holder response shares are the additive forms of the paper's `E_i,F_i`
  equations; and
- the client removes its blinding, inverts the aggregate challenge, and accepts
  only when the recovered digest element equals
  `H(recovery_id, S)*G2`.

The threshold mapping is exact for Yi: LOCUS `k` equals the paper's `t`, and
each polynomial has degree `k-1`. Canonical selected-set handling changes only
transcript representation and prevents duplicate or ambiguous membership.

### Below-threshold and threshold-compromise result

One serialized state in the 2-of-3 profile contains one point on each of three
independent degree-one polynomials. It does not determine the password scalar,
secret exponent, or digest scalar and supplies no local relation that validates
one candidate under the paper's DDH/proof assumptions. The public parameters
and encrypted backup add no such relation.

Any two matching Yi states interpolate all three constants. In particular, the
secret exponent is reconstructed directly and therefore the high-entropy group
secret is derived without a password search. This validates the Yi side of the
stated comparison for static, matching persistent-state compromise.

### Required Yi qualifications

- Ristretto255 is an algebraically suitable prime-order group substitution, but
  the source theorem is not a proof of this exact transcript implementation.
  DDH/discrete-log hardness in the selected group remains an assumption.
- `G2` is deterministically derived by domain-separated hash-to-Ristretto. This
  does not literally implement the paper's multiparty one-honest-server
  generator ceremony. Acceptance therefore relies on the explicit assumption
  that no party knows the discrete-log relation between the independently
  derived generators. LOCUS must not describe this as the source standard-model
  setup without that qualification.
- The framed SHA-512 transcript hashes are domain-separated concrete choices.
  Their proof-of-knowledge and collision-resistance properties are inherited
  assumptions; the implemented verification equation and tests do not prove
  knowledge extraction or zero knowledge.
- The assessment covers the persistent-state/no-local-predicate statement, not
  every active-adversary or concurrent-session property in the source model.

## D017 aPPSS findings

### Figure 4 mapping

The source uses a degree-`t` Shamir polynomial and reconstructs with `t+1`
servers. LOCUS uses degree `k-1` and reconstructs with exactly `k`, so the
translation `k=t+1` is consistent. The first 2-of-3 profile therefore
corresponds to the paper's `t=1,n=3` case.

For holder `i`, the client obtains a base-OPRF result under an independent
holder/epoch key and derives a 16-byte mask `rho_i`. Enrollment samples a
degree-`k-1` polynomial over the specified `GF(2^128)`, publishes
`e_i = s_i XOR rho_i`, and computes a 32-byte hash split into 16-byte `C` and
16-byte `S_R`. Recovery repeats the selected OPRF evaluations, unmasks exactly
`k` shares, interpolates `s`, recomputes `(C,S_R)`, compares `C` in constant
time, and returns `S_R` only on equality. No separately sampled or independently
shared recovery secret exists.

The field representation, XOR addition, reduction polynomial, polynomial
evaluation, and interpolation-at-zero implement the specified
polynomial-basis `GF(2^128)` rules. Public-state decoding enforces ordered,
complete masked shares and an exact digest. Holder identities, OPRF instances,
password inputs, public state, and recovery are bound to one suite and epoch.

### Persistent-state result

Each installed holder stores only its own OPRF key, holder/context binding,
public `omega`, and bounded request/idempotency metadata. It does not store an
OPRF output, unmasked share, Shamir secret, `p_M`, `S_R`, or wrapping key.

With fewer than `k` matching keys, an attacker can evaluate candidate OPRFs and
unmask fewer than `k` Shamir shares, but cannot reconstruct `s` or recompute
the public commitment. Public `omega` and the encrypted backup do not add the
missing share or an independent cue verifier. Under the declared OPRF and
random-oracle assumptions, this supports the scoped no-local-predicate claim.

With `k` matching keys plus public `omega`, an attacker can evaluate each
candidate, reconstruct a candidate `s`, and compare the recomputed `C` with the
public commitment. This is an unrate-limited offline dictionary test. A correct
candidate also yields `S_R`; the compromised state does not directly reveal
`S_R` before a correct guess. This validates the aPPSS side of the stated
threshold-compromise distinction.

### Required aPPSS qualifications

- Theorem 2 is stated in the random-oracle `(F_OPRF,F_AUTH)` hybrid. LOCUS's
  RFC 9497 base OPRF and authenticated transport are concrete realizations, not
  a formal proof that the exact implementation UC-realizes the theorem.
- The RFC OPRF output is domain-separated and compressed to 128 mask bits with
  SHA-256. The Figure 4 hash is concretized by a framed SHA-256 call whose
  output is split into `C` and `S_R`. These are D017 concrete-profile choices
  accepted only under their explicit pseudorandomness/random-oracle
  assumptions.
- The added suite/epoch/holder/context domains preserve equality between setup
  and recovery while preventing cross-context reuse. They are sound defensive
  binding choices, but are not analyzed verbatim in the paper.
- Initialization uses authenticated, recipient-bound channels and holder-local
  OPRF key generation. This is consistent with the required authenticated
  initialization boundary, but is not a formal realization proof.
- The implementation uses abort-only base OPRF behavior. It does not implement
  or claim the optional verifiable-OPRF robustness extension, attribution of a
  malicious holder, or guaranteed completion with malicious selected holders.
- The assessed claim is static, read-only, matching persistent-state
  compromise for one epoch. It does not establish adaptive/proactive security,
  erasure, side-channel resistance, or broader hybrid-model guarantees.

## LOCUS composition findings

### Client-local cue processing

CuePolicy output remains client-local. New aPPSS epochs derive `p_M` from the
authenticated aPPSS context and canonical CuePolicy bytes. Yi uses its frozen
context-password input followed by the native recovery-ID-bound hash-to-scalar
step. Neither path persists the canonical cue bytes or password input.

### Persistent verifier inventory

The reviewed backup, descriptor, bundle, holder, lifecycle, admission, and
audit schemas contain public identifiers, context/configuration digests,
encrypted backup bytes, public suite state, and request/idempotency metadata.
They prohibit or omit raw cues, `Z_M`, `p_M`, OPRF outputs, unmasked shares,
suite outputs, wrapping keys, plaintext protected keys, and a cue-derived
verifier. Blinded/evaluated OPRF transcript retention at one aPPSS holder does
not reveal the client's blind or create the missing below-threshold
reconstruction relation.

### Suite dispatch and lifecycle

One selector chooses exactly one registered suite for new setup. Recovery
ignores enrollment-time preference and dispatches only from the authenticated
descriptor suite identifier. Unknown identifiers, suite/profile mismatch,
cross-suite state, cross-epoch state, duplicate holders, and mixed public state
fail closed. No probe, automatic retry, downgrade, or fallback path exists.
Same-suite and cross-suite successor creation performs wholly fresh native
setup after client-side predecessor recovery; it does not convert shares or
retain dual-suite state for one epoch.

### Outer cryptography

Yi's 32-byte encoded group point and aPPSS's 16-byte output are treated as
opaque, suite-bound input keying material. HKDF-SHA-256 derives the wrapping key
using the backup/epoch/nonce binding, and AES-256-GCM authenticates the exact
suite-bearing backup associated data. The backup does not contain an
independently sampled symmetric key or a candidate-test value. Variable native
suite-output lengths do not create cross-suite equivalence because the
authenticated suite identifier, public format, context, backup AAD, and
descriptor all remain exact.

### Required composition qualifications

- The no-local-predicate statement is conditional on the underlying suite
  assumptions and the exact static persistent views. It is not an entropy or
  memorability claim.
- AES-GCM is a verifier for a candidate *recovery secret*, but below threshold
  neither suite gives the attacker a way to derive that secret from a cue
  candidate. At aPPSS threshold, the public `C` already provides the intended
  offline test; the ciphertext does not preserve below-threshold security.
- Transport authentication, admission, local audit controls, bounded decoding,
  and generic errors are defense-in-depth system mechanisms. They do not prove
  either construction or create a rollback-resistant global attempt bound.
- The existing retained v2 and Yi-only Compose evidence cannot be relabeled as
  aPPSS or selectable-suite evidence. Paired deployment and retained evidence
  remain P6/P8/P9 work.

## Findings register

| Finding | Class | Resolution |
| --- | --- | --- |
| INT-001: The review packet named nonexistent `suite_epoch_factory.py` and `suite_successor.py` files. | Documentation | Corrected to `selectable_suite_lifecycle.py`; no code or claim impact. |
| INT-002: Yi `G2` generation differs from the paper's ceremony. | Documentation / claim qualification | Accepted only with the explicit unknown-discrete-log/hash-derived-generator assumption above; already represented as YI-002. |
| INT-003: The aPPSS theorem uses ideal OPRF/authenticated-channel and random-oracle hybrids, while D017 is concrete. | Documentation / claim qualification | Accepted only as a scoped concrete-profile mapping, not a direct implementation proof of Theorem 2; represented by APPSS-003, APPSS-006, APPSS-008, and APPSS-010. |
| INT-004: Current below-threshold and compromise tests are bounded development regressions. | Out of scope for cryptographic proof | Keep the test/proof distinction and collect new suite-separated evidence only after P8/P9 freeze it. |

There are no open `claim-blocking` or `correction-required` findings in this
internal assessment.

## Mandatory human validation

A qualified human reviewer who is independent of the implementation must later:

1. disclose identity/qualifications, independence, and conflicts;
2. verify the exact Yi group/generator/transcript/proof mapping and decide
   whether every YI provisional classification is acceptable;
3. verify the exact aPPSS threshold, RFC OPRF, field, mask, hash split,
   authenticated initialization, and corruption-view mapping;
4. inspect the complete persistent-state inventory and no-fallback composition;
5. confirm, change, or reject every provisional deviations-register status;
6. classify any new issue and require correction/re-review or claim removal for
   every rejected claim-critical mapping;
7. bind the finding to the exact final implementation commit and record an
   attributable integrity digest/signature; and
8. issue separate Yi, aPPSS, composition, and overall dispositions.

Until those steps are complete, project language must say “provisionally
assessed internally” and never “independently reviewed,” “audited,” or
“cryptographically verified.”

## Integrity and chronology

The reviewed cryptographic implementation is commit `f92b302`. Later P5A.7
changes may activate the already implemented selector and update documentation
and tests, but any semantic change to `tpass-core`, `appss-core`, suite password
derivation, state formats, recovery equations, or the HKDF/AES boundary voids
this provisional disposition and requires a new assessment. The final P5A.7
release-readiness record stores the SHA-256 digest of this file and the exact
post-activation verification commit.
