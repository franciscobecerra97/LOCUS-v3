# LOCUS Backup Cryptography

Status: implemented local cryptographic format for P2.5 and filesystem plus
S3-compatible object-storage adapters for P4.5/P4.6. P5A.3--P5A.5 additionally
implement the suite-neutral backup-v5 application component for Yi and aPPSS.
D020 activates the exact selector/component interface after provisional
internal mapping acceptance. This is research-grade composition and local
conformance evidence, not an audit, paired selectable-suite deployment,
independent cloud deployment, real-provider result, or production-readiness
claim.

## Problem Statement

LOCUS must encrypt the protected private key under a wrapping key derived only
after successful TPASS recovery. The ciphertext must also authenticate the
public metadata that selects the backup, cue policy, security policy, TPASS
configuration, and cryptographic format. A cloud or transport adversary must not
be able to modify those fields without detection.

## Primitive And Dependency

- AEAD: AES-256-GCM through `cryptography==49.0.0`.
- Wrapping-key derivation: HKDF-SHA-256 through the same library.
- AES key length: exactly 32 bytes.
- GCM nonce: 12 fresh random bytes generated for every encryption.
- GCM tag: the library's full 16-byte tag, appended to the ciphertext.
- Current paper-facing and released Yi backup format:
  `LOCUS-reference-backup-v4`.
- Inactive selectable-suite component format:
  `LOCUS-reference-backup-v5`.
- Archived Cycle 1 format: `LOCUS-reference-backup-v3`; immutable historical
  evidence only.

The wrapping key is derived from the recovered encoded TPASS group secret. The
16-byte recovery nonce is the HKDF salt. The canonical HKDF info is:

```text
Encode({"purpose": "LOCUS-wrap", "bid": backup_id, "epoch": positive_epoch})
```

The recovery nonce is distinct from the fresh 12-byte AES-GCM nonce.

Backup v5 keeps this same HKDF-SHA-256/AES-256-GCM composition. It replaces the
TPASS-only public-state member with an exact suite identifier, registered
suite-state format, canonical public-state bytes, suite context digest, and
typed holder membership. The client supplies the high-entropy recovery secret
returned by the exact selected suite to the common sealing/opening path. For Yi
that value is the frozen encoded group secret; for aPPSS it is the correctly
unmasked `S_R`. Recovery authenticates these public bindings before dispatch and
never tries another suite after failure.

## Sealed-Ciphertext Format

The `ciphertext` member of a backup is an object with exactly four fields:

```json
{
  "version": "LOCUS-AES-256-GCM-v1",
  "algorithm": "AES-256-GCM",
  "nonce": "24 lowercase hexadecimal characters",
  "ciphertext": "lowercase hexadecimal ciphertext with the 16-byte tag appended"
}
```

Unknown, missing, or extra fields are rejected. Hex encodings must be lowercase,
even-length, and canonical. The decoded nonce must be exactly 12 bytes and the
decoded ciphertext must contain at least the 16-byte tag.

## Associated Data

For backup v4, the AEAD authenticates the deterministic encoding of these
fields:

- associated-data format version;
- backup format version;
- backup identifier, which currently identifies the local backup epoch;
- explicit positive backup epoch;
- recovery nonce used for cue-password and wrapping-key derivation;
- complete TPASS public parameters;
- context-policy metadata;
- security-policy metadata;
- sealed-ciphertext version and algorithm.

Backup v5 authenticates the corresponding suite-neutral fields: the backup and
ciphertext format identifiers, backup identifier and epoch, recovery nonce,
CuePolicy identifier, exact suite identifier/state format/public-state bytes,
suite context digest, typed holder membership, and security-policy metadata.

The ciphertext and its AES-GCM nonce are not recursively placed in associated
data; AES-GCM already authenticates both through its ciphertext/tag operation.
The party-stored backup digest separately binds the complete cloud object,
including the sealed-ciphertext object.

## Cloud Object And Reference Format

`prototype/locus/object_store.py` defines the current smallest storage boundary.
The cloud object is canonical JSON with exactly these members:

- `version = LOCUS-cloud-backup-object-v1`;
- `bid` and positive `epoch`;
- `backup_digest`; and
- the complete encrypted public backup object.

An exact party/client reference uses
`LOCUS-cloud-backup-reference-v1` and contains only `bid`, `epoch`, and
`backup_digest`. The digest covers the complete backup except its self-digest,
including the epoch, ciphertext, and all public policy and TPASS metadata. The
signed authorizer configuration uses `LOCUS-attempt-config-v2` and incorporates
that backup digest; each party database schema v5 stores the same digest in its
durable epoch row. The P4.9 transition additionally signs both predecessor and
successor backup/configuration digests, their consecutive epoch numbers, and the
predecessor's final head/count/budget. Both immutable objects remain stored under
different epoch keys after retirement; deletion is not used as replay defense.

The filesystem adapter limits an encoded cloud object to 1 MiB. It writes and
fsyncs a same-directory temporary file, then atomically publishes the final
immutable `(bid, epoch)` name through a non-overwriting hard link. An exact
retry returns the existing reference only when the bytes match; different bytes
at the same key are a conflict. Reads reject symlinks, non-regular files,
duplicate/noncanonical JSON, unknown fields, envelope/reference mismatch, and
digest mismatch. Not-found, unavailable, corrupt, conflict, and oversized
outcomes are distinct at the storage interface. The recovery wrapper maps them
to one coarse client failure before entering a counted TPASS attempt.

`prototype/locus/s3_object_store.py` preserves the same application contract
over S3. It uses `boto3==1.43.51`, explicit credentials instead of ambient
credential discovery, SigV4, path-style addressing for local compatibility,
bounded connection/read timeouts, and bounded SDK retries. HTTPS is required by
default; plaintext HTTP requires an explicit local-test opt-in. The object key is
`<prefix>/<bid>/<epoch>.json`.

Creation sends `If-None-Match: *` and a SHA-256 transport checksum. A
precondition failure is accepted as an exact idempotent retry only after a
bounded GET returns byte-for-byte identical canonical content; different content
is an immutable-key conflict. Conditional-write conflicts are retried at most
three times. Reads enforce both the advertised and streamed 1 MiB bounds, close
the response body, and apply the same canonical envelope/reference/digest
validation as the filesystem adapter. ETags, server metadata, and transport
checksums are not application integrity authorities.

`deploy/compose.s3.yaml` pins SeaweedFS 4.29 by multi-platform OCI digest. The
`s3-smoke` task generates ephemeral credentials and a unique object prefix,
validates the resolved single-service Compose boundary, publishes S3 only on a
random loopback port, runs the shared contract, and removes its container,
dedicated network, and named volume. The upstream mini mode uses one
administrative test credential rather than a least-privilege production policy.
The focused `s3-smoke` slice contains only the storage service. Separately, the
default `deploy/compose.yaml` path integrates the same S3 adapter with the
resolver, client, and five authenticated party services and has passed
enrollment, recovery, restart/catch-up, alternate-subset recovery, output
scanning, and cleanup. Both paths remain same-host synthetic evidence, not a
real-provider or independently administered cloud deployment.

## Threat Assumptions And Invariants

- Each enrollment derives a new wrapping key from a fresh TPASS group secret and
  fresh recovery nonce. The recovery nonce is not part of the native TPASS
  password mapping.
- The wrapping-key derivation, AEAD associated data, cloud reference, party
  record, signed authorizer configuration, and durable party epoch all bind the
  same explicit epoch and/or exact backup digest.
- Every call to encryption generates a fresh 96-bit AES-GCM nonce.
- A `(key, nonce)` pair must never be reused.
- The client validates the exact ciphertext format before starting a counted
  TPASS attempt.
- A valid-format ciphertext, nonce, key, or associated-data modification causes
  one generic authentication failure at decryption.
- The client does not report the final AEAD result to recovery parties.
- No private key, wrapping key, group secret, or raw cue is stored in the cloud
  object or party record.

Random 96-bit nonces give a negligible collision probability at the experiment
scale, but a future high-volume deployment should define an explicit per-key
usage limit and operational nonce-collision response.

## Failure Behavior

Missing, unavailable, malformed, stale, substituted, or corrupt cloud objects
fail before attempt consumption when the client begins from the current honest
party-pinned reference. Malformed or unsupported ciphertext formats likewise
fail before attempt consumption.
Authentication failures occur only after TPASS recovery and are mapped to
`CryptoError` locally. The future service/CLI boundary must normalize detailed
TPASS and AEAD failures to one external recovery rejection while retaining only
privacy-safe local diagnostics.

## Test Evidence

The local tests cover:

- successful AES-256-GCM round trips;
- distinct random nonces across encryptions;
- exact key, nonce, and tag/ciphertext lengths;
- ciphertext and nonce tampering;
- wrong associated data;
- cross-backup ciphertext substitution;
- authenticated security-policy substitution;
- missing, extra, malformed, non-canonical, and unsupported format values;
- malformed-format rejection before attempt consumption;
- separated filesystem create/read/delete and exact-retry behavior;
- the same enrollment/recovery, exact retry, immutable conflict, deletion, and
  pre-attempt failure contract through fake and live S3-compatible backends;
- explicit S3 configuration rejection for unsafe bucket names and accidental
  plaintext endpoints, bounded reads, conditional-conflict retry, transport
  outage mapping, stale-reference substitution, and canonical/digest checks;
- immutable-key conflict, noncanonical/oversized object, stale-epoch
  substitution, corruption, mismatched reference, deletion, and unavailable
  backend behavior;
- party/cloud snapshot inspection excluding the other role's secret state;
- five authenticated party processes reconstructing the native TPASS secret
  and decrypting a private key fetched through the separated store; and
- the RFC 5869 HKDF-SHA-256 test case 1 output.

These tests demonstrate implementation behavior. They do not replace analysis
of the underlying primitives, an independently deployed or real-provider cloud
snapshot experiment, key erasure analysis, independent review, or a
cryptographic audit. The filesystem adapter assumes same-filesystem hard-link
support and does not claim hostile-local-filesystem TOCTOU resistance. Local
SeaweedFS conformance is not evidence that every S3-compatible provider has the
same conditional-write or error behavior.

## Evaluation And Paper Implications

Local and distributed experiments must record `cryptography`, OpenSSL, Python,
OS, and architecture versions. Measurements should separate HKDF, AES-GCM, TPASS,
serialization, storage, and network time. Existing manuscript AEAD statements
may describe AES-256-GCM as implemented locally, but must continue to qualify the
overall artifact as local, unaudited, and not production-ready.
