# LOCUS Attack-Report Contract

Status: P6.1 implemented for the version-1 report contract. The registry contains
the live-verified resolver bootstrap, P6.9
`cross-epoch-runtime-mix-v1`, P6.2
`cloud-snapshot-no-offline-predicate-v1`, P6.3
`t-minus-one-party-snapshot-no-offline-predicate-v1`, and P6.4
`cloud-plus-t-minus-one-party-snapshot-no-offline-predicate-v1`. The P6.2-P6.4
profiles isolate exact persistent snapshots from separate non-root,
credential-free, read-only, networkless candidate processes and retain only
schema-validated aggregate observations. Their authoritative corrected Cycle 1
records bind clean cutover commit `12ca815`, pseudonymous host
`cycle1-v2-host-a`, and immutable paths under
`experiments/raw/attacks-v2/`. The matching v1 records remain immutable
historical evidence for the superseded metadata profile. Independent
clean-host reproduction remains M5 work.

## Problem statement

Attack experiments need one machine-readable result shape so that a runner
cannot silently change a scenario, omit a failed observation, or print
secret-bearing diagnostics. Each report binds a registered scenario to its
prerequisites, procedure, parameters, expected result, observed result, status,
and deliberately narrow interpretation.

The report is the redacted observation, not a proof and not a substitute for
raw experimental evidence. Host, dependency, Git, time, and retention provenance
is attached by the task runner using `LOCUS-experiment-metadata-v1`.

## Threat assumptions

- The host and Compose controller are trusted to invoke the declared image and
  retain the emitted report without alteration.
- Scenarios use synthetic state. Online scenarios inject failures through a
  normal local interface; assumed storage compromise is represented only by a
  pre-generated read-only snapshot. P6.3's trusted collector alone reads the
  stopped synthetic party volume, and its offline process receives no live
  service or other-role mount.
- A scenario pass supports only its registered interpretation. It cannot be
  generalized to a different attacker or security property.
- Normal output must not contain cues, derived passwords, party state, TPASS
  shares, cloud credentials, private/wrapping keys, recovered secrets, or
  cryptographic randomness.

## Versioned report and registry

`prototype/locus/attack_runner.py` owns the immutable in-code registry and the
fail-closed validator. `docs/schemas/attack-report-v1.schema.json` is the
portable scenario-bound schema. Version 1 registers:

`resolver-unavailable-v1`:

1. Read the privacy-safe consumed-attempt count through the normal party status
   interfaces.
2. Request recovery using a nonexistent resolver path.
3. Read the consumed-attempt count again.
4. Pass only when the failure is categorized as resolver unavailable and the
   attempt delta is zero.

This bootstrap scenario verifies an early failure boundary. It does not test an
offline cue oracle, subset rotation, replay, rollback, cross-epoch mixing,
malformed parties, selective refusal, or lockout abuse.

`cloud-snapshot-no-offline-predicate-v1`:

1. Publish one ordinary synthetic backup, then copy the exact stored S3 bytes
   and a canonical public locator/integrity manifest into a fresh volume.
2. Start a separate non-root process with `network_mode: none`, no credentials,
   and only the two-file snapshot mounted read-only.
3. Validate the object, manifest, size, digest, locator, and public TPASS shape;
   reject extra role files, prohibited fields, and substitutions.
4. Exercise two fixed synthetic attacker candidates while counted file/socket
   guards are active, then emit only aggregate observations.

The retained Cycle 1 run passed with two candidates and zero candidate
signals, network attempts, excluded-path accesses, or prohibited-material
findings. Positive-control tests introduce a synthetic verifier and attempted
file/network access and require a failed observation. The result tests the
registered implementation surface; it is not a cryptographic proof or a real
cloud-provider compromise.

`t-minus-one-party-snapshot-no-offline-predicate-v1`:

1. Complete one ordinary synthetic recovery, stop `party1`, then copy every
   regular persistent file in that volume into a fresh snapshot with a canonical
   byte/digest/size/mode manifest.
2. Start a separate non-root process with `network_mode: none`, no credentials,
   and only the one-party snapshot mounted read-only.
3. Validate the exact file set, authorizer and TLS keys, party-1 native state and
   2-of-3 public parameters, and the post-one-recovery SQLite checkpoint through
   a disposable temporary copy.
4. Exercise two fixed synthetic attacker candidates under counted file/socket
   guards and emit only aggregate observations.

The retained Cycle 1 run passed with two candidates, one compromised party
at threshold two, zero candidate signals, network attempts, excluded-path
accesses, or secret-output exposures, a valid snapshot, and no cloud material in
the exact input. Positive controls inject a test-only Boolean verifier and
attempted file/network access and require failed observations. The snapshot
intentionally contains party secret state, but none is emitted. This is bounded
below-threshold implementation evidence, not a live-party compromise mechanism,
cryptographic proof, or multi-party/cumulative-compromise result.

`cross-epoch-runtime-mix-v1`:

1. Publish a direct immutable successor and obtain matching old approvals and
   package-bound new readiness statements.
2. After the correct package is prepared, retry one preparation with synthetic
   predecessor-context party state and require a changed-package conflict.
3. Install activation at three parties and require the resulting 3/2 split to
   form neither old nor new quorum.
4. Complete activation, pause at a filesystem checkpoint, let the host restart
   activated party 1, and resume only after that party is healthy.
5. Require old-epoch vote refusal, all-old retired/all-new active status, and
   successful successor recovery.

This scenario tests one same-membership transition, post-preparation package
substitution, and deterministic mixed-activation boundary on one host. It does
not validate the first package delivered by an authorized coordinator, restore
arbitrary party snapshots, implement party replacement, prove rollback
resistance, or establish the global attempt bound. Its same-host development
Compose run passed on 2026-07-22 with exact report validation, output scanning,
and complete cleanup.

## Invariants

1. The report contains exactly the schema fields and one known version/scenario.
2. Registry-owned prerequisites, procedure, expected result, and interpretation
   are copied exactly; a result cannot rewrite them.
3. `status=passed` if and only if the observed result equals the expected result.
4. Unexpected success and unexpected errors remain structured failed reports
   when the runner can still observe the postcondition.
5. Recursive output validation rejects prohibited field names, key material,
   non-finite values, and non-JSON data before host output or retention.
6. The Compose attack service uses the same image, provisioned state, client
   volume, networks, credentials, and HTTP/S3 interfaces as the demo and
   benchmark runners.

## Failure behavior

Unknown scenarios, modified registry text, extra fields, invalid parameters,
noncanonical observations, or contradictory status values fail validation.
Failure before a trustworthy observation produces a nonzero runner result and
no report. A valid but security-relevant mismatch produces `status=failed` and
a nonzero container exit. The task runner always attempts Compose cleanup and
refuses paper evidence when provenance is dirty, unlabeled, or unretained.

## Test plan

- Accept one exact passing registry-bound report.
- Reject changed procedures, extra/secret-bearing fields, invalid parameters,
  unknown scenarios, and summary/status mismatches.
- Run every registered scenario against the isolated deployment and confirm the
  exact scenario-specific observations, restart checkpoint, output scan, and
  cleanup behavior.
- Scan profile output and service logs using generated credentials and all
  synthetic cue values as canaries.
- Re-run the default deployment smoke path to ensure profiles do not broaden its
  role graph or alter normal recovery.

## Evaluation plan

Each additional P6.4-P6.13 scenario will receive a distinct versioned registry entry,
parameters, fixtures, repeat policy, and narrow expected result. Raw traces must
use immutable `experiments/raw/` paths after a trace format and privacy filter
are frozen. Processed summaries must be generated separately and linked to the
raw report identifiers. The initial resolver and lifecycle runs remain
development-only. P6.2-P6.4 now have retained aggregate-only Cycle 1 records;
other future scenarios require their own frozen collection contract.

## Paper implications

P6.1 supports the reproducibility claim that attack observations have a strict,
redacted, scenario-bound format. The bootstrap result supports a narrow statement
that resolver failure precedes attempt authorization in that deployed path. The
cross-epoch result supports only its exact same-host lifecycle/mixing and restart
observations. The retained P6.2 result supports only that the exact registered
cloud snapshot and inspected path exposed no implemented local candidate
predicate in that run. The retained P6.3 result says the same only for the
complete stopped persistent snapshot of one synthetic party in the frozen
2-of-3 profile. Retained P6.4 directly tests only their exact matching combined
union. None of these results supports a global attempt-bound,
party-state rollback, arbitrary-replay, or malicious-party property. The latter properties are scoped
non-claims; only retained architecture claims receive paper-facing P6 evidence.
