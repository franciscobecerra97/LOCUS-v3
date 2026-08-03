# Yi/aPPSS Compromise-Boundary Regression

Status: P5A.6 aggregate-only development regression for the first paired
`k=2,n=3` profile. It is not retained P9 evidence, a cryptographic proof, an
entropy or memorability result, or a released selectable-suite deployment.

## Defensive invariant and protected asset

The protected asset is the high-entropy recovery output used by the unchanged
LOCUS HKDF/AES backup composition. For an exact matching epoch, the regression
keeps these statements separate:

1. fewer than `k` Yi or aPPSS serialized holder records do not expose a tested
   local cue predicate through the bounded implementation interface;
2. `k` Yi records directly interpolate the shared input scalar, protected
   exponent, and digest share, making the recovery output derivable without a
   dictionary search; and
3. `k` aPPSS records plus public `omega` permit offline tests of fixed inputs,
   while the recovery output appears only for the fixed correct input.

The first statement remains inherited from the respective constructions under
their declared assumptions. The regression tests only exact serialized-state
and API behavior; it does not prove either theorem.

## Exact fixed synthetic profile

The only callable evaluator accepts no arguments. It generates one ephemeral
pair from fixed source labels:

- the canonical CuePolicy output is SHA-256 of
  `LOCUS/P5A.6/fixed-synthetic-CuePolicy-output/v1`;
- the protected key is SHA-256 of
  `LOCUS/P5A.6/fixed-synthetic-protected-key/v1`;
- the incorrect fixed suite input is SHA-256 of
  `LOCUS/P5A.6/fixed-incorrect-suite-input/v1`;
- backup ID `a6` repeated 16 times, epoch 1, and nonce `b6` repeated 16 times;
- frozen `LOCUS-location-person-set-v1` and `LOCUS-no-resolver-v1`;
- recovery threshold 2-of-3 and authorization quorum 4-of-5;
- local synthetic admission and backup v5; and
- independent suite password domains derived from the same canonical input.

The report commits these shared public conditions through one deterministic
manifest digest. It never serializes the input bytes, suite password inputs,
protected key, holder records, OPRF keys, shares, or recovery outputs.

## Views and boundary

For each suite the evaluator creates a canonical backup-v5 cloud view and three
serialized holder records, then treats the resulting byte strings as immutable.
It checks cloud-only, all four below-threshold coalitions (empty plus each single
holder), and the matching cloud-plus-coalition views. Unit execution forbids
socket creation. A direct-verifier marker absent from the real view is injected
only into a transient positive-control copy and must be detected.

For threshold compromise, all three 2-of-3 subsets and the all-server view are
covered. The Yi comparator independently parses the frozen canonical party
wire after native validation, interpolates its three shared scalars, checks the
input/digest relations, and verifies ordinary recovery. It records only that
the recovery output is directly derivable from the reconstructed exponent. The
aPPSS comparator uses the compromised serialized OPRF keys and public state
locally against exactly two transient fixed inputs; it retains only the
aggregate facts that the incorrect input releases no output and the correct one
does. There is no configurable guessing interface.

## Strict output and path

The report identifier and schema are
`LOCUS-recovery-suite-compromise-regression-v1` and
`docs/schemas/recovery-suite-compromise-regression-v1.schema.json`. The report
exists only in memory during tests. No raw result is written or retained; P9
must assign separate suite/topology result paths before collection. The strict
validator rejects altered common conditions, scenario order/count, threshold
observations, hygiene flags, extra members, and unsafe public output.

## Interpretation limit

The result validates a fixed synthetic, static, networkless implementation
boundary. It does not establish Theorem 2, the Yi proof, cue entropy, human
memory, adaptive/proactive security, side-channel resistance, independent
administration, production compromise behavior, performance, or a 3-of-5
profile. In particular, threshold aPPSS compromise is unrate-limited offline
guessing; it is not continued threshold protection for low-entropy inputs.
