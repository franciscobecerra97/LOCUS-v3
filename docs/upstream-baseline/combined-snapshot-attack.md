# Combined Cloud Plus One-Party Snapshot Attack Boundary

Status: implemented, development-verified, and retained as corrected
aggregate-only Cycle 1 v2 evidence from clean cutover commit `12ca815` and
pseudonymous host `cycle1-v2-host-a`. The v1 record is historical evidence for
the superseded metadata profile. Independent clean-host reproduction remains.

## Defensive Question

P6.4 asks whether the exact union of the already-frozen P6.2 cloud snapshot and
P6.3 one-party persistent snapshot gives an offline attacker a local predicate
that distinguishes correct from incorrect cue-derived password candidates. It
tests the combined cloud-plus-`t-1` claim for the deployed two-of-three TPASS
profile. It does not infer combined security from separate volume layout or from
the two prerequisite experiments passing independently.

The scenario identifier is
`cloud-plus-t-minus-one-party-snapshot-no-offline-predicate-v1`. The compromised
set contains the logical cloud role and exactly one synthetic recovery party, so
`t - 1 = 1` for the frozen threshold `t = 2` profile.

## Authorized Local Model

The ordinary isolated deployment completes one recovery using generated
synthetic cues, credentials, keys, and backup state, then stops `party1`. The
existing trusted P6.2 collector copies the exact stored cloud object into a
`cloud/` sub-snapshot. The existing trusted P6.3 collector copies every regular
persistent file from the stopped `party1` volume into a `party/` sub-snapshot.
Neither collector implements or exercises a compromise mechanism.

A separate trusted finalizer has no network, credentials, client mount, live
party mount, resolver mount, cloud mount, or other-party mount. It receives only
the shared snapshot volume, validates both frozen sub-snapshots, checks their
cross-role epoch/digest/TPASS binding, and writes the top-level manifest. It does
not perform candidate testing.

The offline audit runs as a separate non-root process with no network or
credentials and with only the completed combined volume mounted read-only. Any
candidate-path socket operation or filesystem access outside the already-loaded
validated snapshot fails the scenario. All containers, networks, credentials,
and storage are local, generated for the current run, and disposable.

## Exact Combined Snapshot Contract

`LOCUS-combined-snapshot-input-v1` contains exactly:

- canonical top-level `manifest.json`;
- `cloud/`, containing exactly one valid `LOCUS-cloud-snapshot-input-v1`; and
- `party/`, containing exactly one valid `LOCUS-party-snapshot-input-v1`.

The top-level canonical manifest binds exactly:

- format version;
- frozen combined-profile identifier;
- stopped, post-one-recovery capture-checkpoint identifier;
- P6.2 and P6.3 sub-snapshot versions;
- SHA-256 over each canonical sub-snapshot `manifest.json` byte string;
- compromised-party count `1`; and
- TPASS threshold `2`.

The sub-manifest digests bind the exact canonical subcontracts: P6.2's manifest
binds the cloud object bytes, while P6.3's manifest binds every stopped party
file. The finalizer refuses an existing top-level manifest, an unexpected entry,
a link or non-directory sub-snapshot, a malformed/noncanonical sub-snapshot, or
any mismatch. Publication uses exclusive creation; it does not overwrite or
repair input.

Offline validation independently repeats every P6.2 and P6.3 validation and the
top-level digest checks. It additionally requires these cross-role bindings:

- cloud backup identifier equals the party authorizer backup identifier;
- cloud epoch equals the party authorizer epoch;
- cloud backup digest equals the party authorizer backup digest;
- cloud TPASS public parameters equal the parameters stored with party 1; and
- the public threshold/party count remain exactly two-of-three while the party
  snapshot contains only party 1's native state.

Thus a manifest-consistent union assembled from independently valid but
different synthetic enrollments fails before candidate testing.

## Included And Excluded State

The union intentionally includes the complete P6.2 encrypted cloud object and
public locator/integrity metadata together with the complete P6.3 party-1
persistent snapshot, including its native share, signer/TLS keys, bindings,
attempt state, idempotency state, runtime package, and SQLite companion files
when present. These bytes are inputs only and are never printed.

The union excludes:

- client bundles, raw/canonical cues, cue identifiers, derived TPASS passwords,
  recovered group secrets, wrapping keys, plaintext, and the protected private
  key outside its ciphertext;
- resolver fixtures, queries, results, and observations;
- every other recovery party's files, states, messages, and credentials;
- live cloud, party, coordinator, client, resolver, or identity-provider access;
- host/container runtime memory, logs, packet captures, crash dumps, deleted
  blocks, provider/orchestrator metadata, and multi-epoch history; and
- correctness labels or a precomputed password/cue verifier.

The party sub-snapshot deliberately contains secret-bearing party material. A
passing report therefore means that no such input was emitted and no local
candidate predicate was observed; it does not claim that the combined input is
secret-free.

## Offline Candidate Decision Rule

The audit validates and loads the entire combined snapshot before enabling the
candidate boundary guard. It then evaluates a fixed, bounded set of generated
synthetic candidates. A candidate signal exists only if computation over the
combined in-memory cloud and party state produces a candidate-dependent Boolean
correctness decision, recovered plaintext, matching verifier, or equivalent
repeatable local distinction without further online participation.

Public candidate-dependent preprocessing that returns no correctness decision
is not a signal. Candidate-independent canonical, digest, database, certificate,
and cross-binding failures are snapshot-integrity failures, not cue-correctness
signals, and stop the scenario before candidate testing.

The scenario passes only when:

- both frozen sub-snapshots and the combined manifest validate;
- the cloud/party epoch, backup digest, and TPASS public parameters match;
- exactly one party snapshot is present for threshold two;
- every bounded candidate produces no local correctness signal;
- candidate evaluation attempts no network operation or filesystem access; and
- the registered aggregate report passes recursive public-output validation.

A test-only injected Boolean verifier is the positive candidate-signal control.
Separate test-only probes attempt a socket and an excluded file read. A
manifest-consistent union of the cloud snapshot from one enrollment and the
party snapshot from another is the positive cross-binding control. None of
these controls is serialized into the normal snapshot or generalized into an
arbitrary-target tool.

## Aggregate Evidence

The registered observation contains only fixed labels and nonnegative counts:

- candidate count and candidate-signal count;
- compromised-party count, party-snapshot count, and threshold;
- network-attempt and excluded-path-access counts;
- cloud-snapshot, party-snapshot, and combined-binding validation labels; and
- secret-output-exposure count.

It contains no candidate values or hashes, keys, shares, certificates, database
rows, backup identifiers or digests, ciphertext, absolute paths, exception text,
per-candidate outcomes, sub-manifests, or source permission modes. Temporary
writable SQLite validation copies remain inside the offline process's disposable
temporary filesystem and are removed before exit.

## Verification

On 2026-07-23 the disposable same-host Compose profile completed one synthetic
recovery, stopped party 1, collected the exact cloud and party sub-snapshots,
finalized their networkless manifest-bound union, and ran the separate non-root,
credential-free, read-only, networkless audit. The observed report exactly
matched the expected aggregate result:

- two synthetic candidates and zero candidate signals;
- one compromised party at threshold two;
- both sub-snapshots valid and their combined binding matched;
- zero network attempts and zero excluded-path accesses; and
- zero secret-output exposures.

Output scanning passed. The task runner removed the generated containers,
volumes, and networks, and a separate exact-project-label query found no
remaining resource. That first run used commit `2481321` with development-only
provenance. The archived 2026-07-23 v1 run repeated the exact observation and
cleanup from clean commit `812cb96` and pseudonymous host `cycle1-host-a`.
The authoritative corrected v2 run repeated it again from cutover commit
`12ca815`, pseudonymous host `cycle1-v2-host-a`, and an immutable
aggregate-only v2 raw-output path.

## Interpretation And Limitations

A passing result is bounded implementation evidence that the exact registered
cloud-plus-one-party persistent union exposes no implemented local
candidate-correctness predicate in this scenario. It supports only the scoped
combined snapshot claim under the stated TPASS, AEAD, KDF, canonicalization, and
implementation assumptions. It is not a cryptographic proof and establishes no
cue entropy, memorability, usability, production security, or global online
attempt bound.

The scenario does not cover live compromise, runtime memory, logs or arbitrary
traces, side channels, malicious online protocol behavior, multiple/cumulative
or cross-epoch party compromise, another threshold/profile, independently
administered roles, cloud plus `t` parties, endpoint compromise, or a leaked
group/wrapping secret. The retained result still requires independent clean-host
reproduction.
