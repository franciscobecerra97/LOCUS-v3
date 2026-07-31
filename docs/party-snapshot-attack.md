# One-Party Persistent-Snapshot Attack Boundary

Status: implemented, development-verified 2026-07-22, and retained as corrected
aggregate-only Cycle 1 v2 evidence from clean cutover commit `12ca815` and
pseudonymous host `cycle1-v2-host-a`. The v1 record is historical evidence for
the superseded metadata profile. Independent clean-host reproduction remains.

## Defensive Question

P6.3 asks whether the complete persistent state of one recovery party in the
deployed two-of-three TPASS profile gives an offline attacker a local predicate
that distinguishes correct from incorrect cue-derived password candidates.
This is a defensive invariant test of the implemented storage boundary. It is
not a mechanism for compromising a party and it does not model control of a
live service.

The scenario identifier is
`t-minus-one-party-snapshot-no-offline-predicate-v1`. The compromised set is
exactly one synthetic recovery party, so `t - 1 = 1` for the frozen threshold
`t = 2` profile.

## Authorized Local Model

The collector receives a read-only mount of the already provisioned synthetic
`party1` persistent volume. The normal isolated deployment first completes one
synthetic recovery, then stops `party1` before collection so its files do not
change during capture. The collector copies bytes; it does not exploit,
authenticate to, scan, or send adversarial traffic to the party.

The offline audit receives only the resulting snapshot as a read-only mount.
It runs without a network, cloud or party credentials, client state, resolver
state, unrelated host mounts, or access to the other party volumes. Candidate
testing is therefore networkless and credential-free. All containers and
storage used by the development profile are local and disposable.

## Exact Snapshot Contract

`LOCUS-party-snapshot-input-v1` contains exactly:

- canonical `manifest.json`; and
- a `party/` directory containing every regular persistent file visible in the
  stopped `party1` volume.

The required party files are:

- `ca.pem`;
- `peer-key.pem`;
- `peer.pem`;
- `server-key.pem`;
- `server.pem`;
- `service.json`; and
- `party.sqlite3`.

`party.sqlite3-wal` and `party.sqlite3-shm` are permitted only when they exist at
the stopped capture checkpoint; if present, both are included and validated
with the database. No other file, directory below `party/`, symlink, device, or
socket is permitted.

The canonical manifest binds these exact fields:

- format version;
- frozen deployment-profile identifier;
- party identifier `1`;
- TPASS threshold `2` and TPASS party count `3`;
- stopped, post-recovery capture-checkpoint identifier; and
- a path-sorted list containing each file's relative path, byte length, SHA-256
  digest, and source permission mode.

Collection fails closed if required state is absent, the source contains an
unexpected entry, a file changes while it is read, or the destination is not
empty. Offline validation independently rejects noncanonical manifests,
unlisted or missing files, path traversal, links, byte or digest mismatches,
invalid modes, inconsistent profile identifiers, malformed service state,
invalid native TPASS state, or an inconsistent SQLite snapshot.

## Included Secret-Bearing State

The snapshot intentionally includes the selected party's native TPASS secret
state, Ed25519 signer key, TLS private keys, authorization configuration, backup
epoch/digest bindings, durable attempt state, idempotency records, and local
audit state when present. These bytes are inputs to the audit but are never
printed or copied to retained output. The report must not describe this input as
free of prohibited material; the tested property is that the isolated process
does not expose those bytes in its output and does not acquire another role's
state.

The snapshot deliberately excludes:

- cloud backup objects, ciphertext, and cloud credentials;
- client bundles, cue records, resolved descriptors, cue identifiers, candidate
  inputs, derived TPASS passwords, recovered group secrets, wrapping keys, and
  private keys protected by LOCUS;
- resolver files or observations;
- every other recovery party's files;
- live process memory, host/container logs, packet captures, crash dumps, and
  provider or orchestrator metadata; and
- online access to a recovery party, coordinator, resolver, cloud, or other
  candidate-correctness oracle.

## Offline Candidate Decision Rule

The audit validates and inventories the snapshot, then evaluates a fixed,
bounded set of generated synthetic candidates. A candidate signal exists only
if snapshot-local computation produces a candidate-dependent Boolean correctness
decision without contacting any other component. Public, deterministic
candidate-dependent computation that produces no correctness decision is not a
signal.

The scenario passes only when all of the following hold:

- snapshot validation succeeds;
- exactly one party is present for threshold two;
- every bounded candidate produces no local correctness signal;
- candidate evaluation attempts no network operation;
- candidate evaluation accesses no path outside the validated snapshot; and
- emitted evidence is the registered privacy-safe aggregate observation only.

The harness counts network and excluded-path attempts and fails the scenario
when either is nonzero. A test-only injected Boolean verifier is the positive
control: it must produce a signal and make report construction fail. The
positive control is not serialized into the snapshot or shipped as an attack
capability.

## Aggregate Evidence

The registered observation contains only fixed labels and integer counts:

- candidate count and candidate-signal count;
- compromised-party count and threshold;
- network-attempt and excluded-path-access counts;
- snapshot-validation status;
- absence of cloud material from the exact input boundary; and
- secret-output-exposure count.

It contains no candidates, hashes derived from candidates, keys, shares,
certificates, database rows, backup identifiers or digests, file contents,
absolute paths, exception text, or per-candidate outcomes. Temporary writable
copies needed solely to validate SQLite consistency are created inside the
networkless process's disposable temporary filesystem and are removed before
exit.

## Interpretation And Limitations

A passing result is bounded implementation evidence that this one synthetic
party's persistent snapshot exposes no local candidate-correctness predicate in
the registered scenario. It supports only the exact below-threshold storage
claim and the stated TPASS assumptions; it is not a cryptographic proof and does
not establish cue entropy, memorability, usability, or production security.

The scenario does not cover live-party compromise, runtime memory, arbitrary
traces, side channels, malicious online protocol behavior, multiple or
cumulative party compromise, another threshold/profile, multi-epoch
correlation, independently administered parties, or compromise of at least
`t` parties. P6.4 must separately test the exact union of this snapshot and the
P6.2 cloud snapshot; it may not infer combined security from directory layout
alone.
