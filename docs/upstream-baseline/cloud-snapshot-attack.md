# LOCUS Cloud-Only Snapshot Boundary

Status: P6.2.1-P6.2.5 implemented, development-verified 2026-07-22, and
retained as corrected aggregate-only Cycle 1 v2 evidence 2026-07-24.
`cloud-snapshot-no-offline-predicate-v1` is bound to the P6.1 registry/schema
and runs through a dedicated Compose collection/offline-execution profile.
The authoritative retained record binds clean cutover commit `12ca815`,
pseudonymous host `cycle1-v2-host-a`, and its immutable v2 raw-output path.
The v1 record remains historical evidence for the superseded metadata profile.

## Problem statement

P6.2 tests the narrow implementation claim that the data held by the cloud
role does not itself become a local cue-correctness predicate. The experiment
must give the attacker exactly the implemented cloud-facing state without
silently adding party state, client state, credentials, or an online recovery
oracle. It must also avoid claiming that a finite program inspection proves the
security of TPASS, AES-GCM, HKDF, or their composition.

The frozen version-1 target is one current, synthetic backup epoch in the
default S3-compatible deployment. Multi-epoch correlation, provider-internal
forensics, access-pattern analysis, and a real cloud-provider compromise are
outside this scenario.

## Claim and threat assumptions

- The attacker has compromised the logical cloud-storage role after one
  canonical backup object has been published.
- The attacker can copy the complete stored object and its non-secret storage
  locator and size, then perform unlimited local computation and generate
  arbitrary candidate recovery inputs.
- The client endpoint, resolver, recovery parties, coordinator, provisioner,
  container engine, and host remain uncompromised.
- The TPASS construction and its Ristretto255 implementation, AES-256-GCM,
  HKDF-SHA-256, SHA-256, canonical encoding, and operating-system randomness
  retain their documented assumptions. P6.2 does not re-prove them.
- All experiment state is generated from the committed synthetic fixture. No
  human cue data or real private key may enter a retained snapshot.

The tested property is narrower than confidentiality against arbitrary
cryptanalysis: given only the frozen snapshot and an attacker-chosen cue
candidate, the implemented snapshot surface exposes no local operation whose
result distinguishes the enrolled candidate from a non-enrolled candidate.

## Normative snapshot input

The version-1 snapshot artifact consists of exactly two files:

1. `object.json`: the byte-for-byte canonical output of
   `prototype.locus.object_store.encode_backup_object` for one
   `LOCUS-cloud-backup-object-v1` envelope. Re-serialized or reconstructed
   client data is not an equivalent input.
2. `manifest.json`: a canonical JSON sidecar with exactly these fields:
   `version = LOCUS-cloud-snapshot-input-v1`,
   `backend = s3-compatible`, the cloud-visible `bucket`, the exact
   `object_key`, `object_bytes`, and `object_sha256` over `object.json`.

The manifest is capture-integrity and public locator metadata, not an extra
secret source. It contains no endpoint or credential that could be used to
turn the offline experiment into a live cloud query. `object_bytes` must equal
the actual file length, `object_sha256` must equal ordinary SHA-256 over the
exact bytes, and the bucket/key must identify the captured object. The object
key follows the implemented `<prefix>/<bid>/<epoch>.json` mapping.

The canonical envelope contains exactly:

- `version`, `bid`, `epoch`, and `backup_digest`; and
- `backup`, whose exact fields are `version`, `bid`, `epoch`, `nonce`,
  `ciphertext`, `tpass_public_params`, `context_policy`, `security_policy`, and
  `digest`.

This means the attacker receives the encrypted private-key backup, its public
nonce and identifiers, complete public TPASS parameters, cue-policy version,
security-policy values, format/algorithm identifiers, canonical sizes, and
both application-visible digests. The public `bid`, `epoch`, and nonce are
enough to derive the cue-password input for an attacker-chosen candidate; the
claimed boundary is that the snapshot still lacks the TPASS secret-dependent
material needed to validate that candidate or derive the AEAD wrapping key.

The `LOCUS-cloud-backup-reference-v1` values are fully derivable from the
envelope and add no independent input. The authorizer configuration is not
part of the cloud snapshot: even where some of its values or public keys are
non-secret, the current cloud role does not store that configuration.

## Explicit exclusions

The version-1 snapshot must not include or permit access to:

- `deployment.json`, the client volume, client memory, or the protected or
  recovered private key;
- any party `service.json`, SQLite database, volume, logs, TPASS secret state,
  response share, signing key, attempt ledger, or lifecycle state;
- the authorizer configuration except for `bid`, `epoch`, and backup-digest
  values already present in `object.json`;
- resolver fixtures, resolver traffic, raw or canonical cues, cue identifiers,
  contact/location records, derived TPASS passwords, or correctness labels;
- group secrets, wrapping keys, AEAD plaintext, protocol randomness, TLS
  private keys, S3 access keys, session tokens, or other credentials;
- coordinator, resolver, party, client, identity-provider, provisioner, or
  cloud-network access during candidate testing; or
- host/container runtime memory, core dumps, deleted blocks, provider control
  planes, server-side replicas, request logs, and access timing. These are
  separate deployment/metadata questions, not evidence supplied by P6.2.

Candidate inputs are attacker-generated parameters, not captured cloud state.
The attack path may receive a candidate value, but never a hidden label saying
whether it is the enrolled value. Test-only positive controls that inject a
synthetic verifier must remain outside normal scenario input and must be
reported only as harness tests.

## Offline-predicate decision rule

For P6.2, a local correctness predicate is an implemented computation that:

1. accepts the frozen snapshot and an attacker-chosen recovery candidate;
2. runs without contacting any live role or consuming additional secret state;
   and
3. returns a candidate-dependent success/failure value, recovered plaintext,
   matching verifier, or other repeatable signal that distinguishes the
   enrolled candidate.

Canonical parsing, envelope/digest validation, format rejection, and object
substitution checks are candidate-independent integrity checks and therefore
are not cue-correctness predicates. Public metadata may help an attacker rank
candidates; ranking is residual leakage, not validation. An authorized online
TPASS attempt can eventually give its client a correctness outcome, but it is
an online oracle and is explicitly outside this snapshot experiment.

The scenario is falsified if the included bytes or the offline code path expose
raw/canonical cues, a password or cue verifier, sufficient party state, a group
or wrapping secret, decryptable plaintext, or any candidate-dependent local
success signal. A network attempt or read of an excluded path is a scenario
boundary violation and must fail the run rather than be interpreted as
evidence for or against the cryptographic claim.

## Collection and execution boundary

1. Provision the ordinary synthetic deployment and publish one current backup
   through the normal S3-compatible adapter.
2. Copy the exact stored response bytes into `object.json`; do not copy or
   transform the client deployment bundle.
3. Produce `manifest.json` only from cloud-visible locator data and values
   derived from the captured bytes, then validate both files against this
   contract and `decode_backup_object`.
4. End the collection phase. Candidate testing runs in a separate process with
   no network and with only the two read-only snapshot files plus executable
   project code and an attacker-supplied candidate source.
5. Emit only aggregate, privacy-safe observations through the P6.1 report
   contract. Neither snapshot bytes nor candidate material belongs in ordinary
   output.

The runner fails closed if its filesystem view contains an excluded
role artifact, if a required input is malformed or noncanonical, or if any
network-capable dependency is invoked. Compose gives the candidate process
`network_mode: none`, no credentials or environment configuration, and one
read-only snapshot volume. The process also replaces ordinary socket and file
entry points during candidate testing with counted fail-closed guards. These
guards are defense in depth for the tested code path, not a sandbox for
arbitrary hostile native code.

## Invariants and failure behavior

1. The captured object is byte-identical to the canonical stored object and is
   at most the implemented 1 MiB bound.
2. The manifest has only the six frozen fields and all derived values match the
   object.
3. The attack process receives no role secret, credential, live service
   endpoint, correctness label, or writable role volume.
4. Candidate testing performs zero resolver, cloud, coordinator, or party
   requests.
5. Malformed, noncanonical, mismatched, oversized, or extra input fails before
   candidate testing and cannot be reported as “no predicate found.”
6. Boundary violations, secret-field findings, or candidate-dependent local
   success produce a failed attack report and a nonzero runner result.
7. A passing report states only that the registered implementation surface did
   not expose a local predicate under this scenario.

## Test and evaluation result

The implemented collector performs an exact idempotent S3 read after the normal
client has published the synthetic backup. It has the S3 credential, cloud
network, a read-only client bundle used only to locate the object, and a fresh
writable snapshot volume. It writes only `object.json` and `manifest.json`.
The separately launched attacker is non-root, has no network or credentials,
and mounts only that volume read-only. Resolved-Compose validation fails if
these identities, mounts, capabilities, networks, commands, or credentials
change.

Focused tests cover the ordinary snapshot; a synthetic verifier positive
control; malformed and noncanonical inputs; object substitution; an extra
excluded role file; attempted filesystem and network access; registry/schema
binding; and report redaction. The positive control produces candidate signals,
and attempted socket/file operations increment boundary counters, so neither
can match the registered passing observation.

The retained Compose run on 2026-07-23 passed with the exact
aggregate observation `candidate_count=2`, `candidate_signals=0`,
`network_attempts=0`, `excluded_path_accesses=0`,
`snapshot_validation=passed`, and `prohibited_material=absent`. Output and
service-log scanning passed, Compose removed all exact-project resources, and
the aggregate-only record contains the frozen trace policy and complete
experiment provenance.

## Interpretation and paper implications

The retained result supports only an implementation statement: the
exact current cloud snapshot surface and registered offline path exposed no
local candidate predicate in this run. It does not prove TPASS password
security, AES/HKDF security, cue entropy or memorability, independent cloud
administration, resistance to a compromised client/host, real-provider
forensics, access-pattern privacy, or the absence of every possible
cryptanalytic attack. Independent clean-host reproduction remains required.
