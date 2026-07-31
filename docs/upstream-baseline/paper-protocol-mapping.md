# LOCUS Paper-Facing Protocol Mapping

Status: authoritative mapping for the retained Cycle 1 deployment and
manuscript, frozen from clean evidence commit
`812cb96cc5fba9d4332ae349eb6d664bac0f17b1` and audited against current commit
`2d42a61b064089e99402605b7ac70c5fc41163bf` on 2026-07-24.

This document specifies what the evaluated LOCUS artifact actually executes. It
is the source of truth when manuscript notation, older design prose, the generic
local scaffold, and the retained deployment differ. It is not a new security
proof or a long-term compatibility promise.

## Scope

The paper-facing path is the default isolated deployment in
`prototype/locus/deployment.py`, using:

- exactly three location-person cue pairs;
- the native Rust/Ristretto255 TPASS backend;
- a 2-of-3 TPASS configuration hosted by parties 1--3;
- five authenticated authorizer/party processes, of which parties 4--5 do not
  hold TPASS secret state;
- one canonical S3-compatible encrypted cloud object;
- a four-attempt signed-ledger configuration whose global rollback-resistant
  bound is explicitly not claimed; and
- one same-host synthetic deployment and retained evidence corpus.

The variable-cue `enroll`/`recover` functions and simulator/toy backends in
`prototype/locus/core.py` and `prototype/locus/tpass.py` are development and
regression scaffolding. They are not the evaluated cue-to-TPASS construction and
must not define the paper algorithm or support performance claims.

## Canonical Encoding

`Encode` is the UTF-8 output of canonical JSON with recursively sorted object
keys, no insignificant whitespace, ASCII escapes for non-ASCII code points, and
NFC-normalized strings. The frozen cue policy accepts only constrained ASCII
cryptographic fields after validation, so display labels and provider record
identifiers never enter this encoding.

Variable-length fields in native TPASS transcript hashes use an unsigned
64-bit big-endian length followed by the field bytes. Let `LP(x)` denote that
encoding.

## Cue Input

The client accepts exactly three distinct location-person pairs. Each pair is:

```text
pair_j = {
  "location": {
    "latitude_e4": round_half_even(10000 * latitude),
    "longitude_e4": round_half_even(10000 * longitude)
  },
  "person": {
    "type": "email" or "phone",
    "value": canonical ASCII email or E.164 number
  },
  "version": "LOCUS-location-person-pair-v1"
}
```

Locations, people, and full pairs must each be pairwise distinct. Pairs are
ordered by:

```text
(
  SHA256("LOCUS/cue-pair/v1" || 0x00 || LP32(Encode(pair_j))),
  Encode(pair_j)
)
```

where `LP32` is the helper's unsigned 32-bit big-endian length prefix. The
second component is a deterministic collision tie-breaker, not an equality
test.

The complete canonical recovery input is:

```text
Z = Encode({
  "pairs": [ordered pair_1, ordered pair_2, ordered pair_3],
  "version": "LOCUS-location-person-set-v1"
})
```

The pinned reference fixture produces exactly 511 bytes. `Z`, individual
descriptors, and pair-ordering hashes remain client-local and are not persisted.

## Recovery Identifier And TPASS Password

For the retained epoch-1 profile:

```text
bid = 16 fresh random bytes, represented as 32 lowercase hexadecimal characters
ID  = ASCII("LOCUS-compose-recovery-v1:") || bid_bytes
```

The native TPASS protocol domain is:

```text
D_TPASS = ASCII("LOCUS-TPASS-YI-ZK-RISTRETTO255-v1")
```

The password scalar is:

```text
p = ReduceScalar(
      SHA512(
        LP(D_TPASS) ||
        LP(ASCII("password")) ||
        LP(ID) ||
        LP(Z)
      )
    )
```

The 16-byte recovery nonce stored in the backup is not an input to `p`. The
backup identifier is bound through `ID`. The retained initial profile has epoch
1. The separate synthetic lifecycle scenario uses
`ASCII("LOCUS-compose-recovery-v2:") || bid_bytes` for its epoch-2 successor;
this is a scenario-specific identifier, not a general epoch-encoding rule.

## Native TPASS Secret And Digest

Enrollment samples a nonzero scalar `s` and computes the 32-byte encoded group
secret:

```text
S = EncodeRistretto(s * G2)
```

The digest scalar shared by TPASS is:

```text
theta = ReduceScalar(
          SHA512(
            LP(D_TPASS) ||
            LP(ASCII("secret-digest")) ||
            LP(ID) ||
            LP(S)
          )
        )
```

The Yi et al. password, secret-exponent, and digest polynomials and recovery
equations are mapped to additive Ristretto notation as specified in
`docs/crypto-design.md`. Successful client finalization returns `S` only after
the recovered digest relation validates.

## Wrapping-Key Derivation

Enrollment samples a fresh 16-byte recovery nonce `nu_R`. The evaluated path has
no intermediate `K_R`. It derives the 32-byte AES wrapping key directly:

```text
K_wrap = HKDF-SHA-256(
  IKM  = S,
  salt = nu_R,
  info = Encode({
    "bid": bid_hex,
    "epoch": positive_epoch,
    "purpose": "LOCUS-wrap"
  }),
  L = 32
)
```

The AES-GCM encryption nonce is a separate fresh 12-byte value.

## Authenticated Backup

Before encryption, the public backup metadata contains:

```text
version             = "LOCUS-reference-backup-v4"
bid                 = bid_hex
epoch               = positive integer
nonce               = lowercase hex(nu_R)
tpass_public_params = native backend, wire encoding, parameters, threshold, parties
context_policy      = version metadata
security_policy     = version, max_attempts, cooldown_seconds
```

AES-256-GCM authenticates `Encode` of exactly:

```text
{
  "version": "LOCUS-backup-associated-data-v1",
  "backup_version": backup.version,
  "bid": backup.bid,
  "epoch": backup.epoch,
  "recovery_nonce": backup.nonce,
  "tpass_public_params": backup.tpass_public_params,
  "context_policy": backup.context_policy,
  "security_policy": backup.security_policy,
  "sealed_version": "LOCUS-AES-256-GCM-v1",
  "sealed_algorithm": "AES-256-GCM"
}
```

The sealed member contains exactly its format version, algorithm, 12-byte nonce,
and ciphertext with the 16-byte GCM tag appended.

After encryption:

```text
backup_digest =
  SHA256(
    "LOCUS-backup-digest-v1" || 0x00 ||
    LP32(Encode(backup_without_digest))
  )
```

The cloud stores one canonical `LOCUS-cloud-backup-object-v1` envelope containing
`bid`, `epoch`, `backup_digest`, and the complete
`LOCUS-reference-backup-v4` backup. Party configuration and the client reference
pin the same `(bid, epoch, backup_digest)`.

## Recovery Order

The evaluated recovery path:

1. Reads and validates the exact party-pinned cloud object before consuming an
   attempt.
2. Resolves and canonicalizes exactly three pairs into `Z`.
3. Constructs the blinded native TPASS request for `(ID, Z)`.
4. Selects one fixed healthy TPASS subset from quorum-consistent summaries.
5. Durably installs one signed authorization before the first
   secret-state-dependent commitment.
6. Runs commitment and response phases with the fixed subset.
7. Aggregates responses and accepts `S` only after the native digest check.
8. Derives `K_wrap`, authenticates the full backup metadata, and decrypts the
   private key locally.
9. Does not report the final TPASS or AEAD result to recovery parties.

The signed ledger provides exact retry, durable local state, authenticated
same-host boundaries, and the measured attempt transition. It does not establish
a rollback-resistant global attempt bound.

## Version Boundary And Retained Evidence

The current paper-facing profile is the single valid combination:

```text
backup.version                 = "LOCUS-reference-backup-v4"
context_policy.version         = "LOCUS-location-person-set-v1"
deployment.artifact            = "LOCUS-compose-deployment-v2"
performance experiment_id      = "compose-performance-v2"
processed/generated path root  = "performance-v2"
```

Provisioning, layout audit, the client, the fetched cloud object, and lifecycle
entry points validate this combination before authorization or
secret-state-dependent work. A v4 backup with the old label, a v3 backup with
the new label, and the archived v3/old-label combination are all rejected by
the active deployment.

The immutable Cycle 1 v1 corpus remains an accurate record of its old
`LOCUS-reference-backup-v3` plus `LOCUS-local-context-v1` profile. It is not
rewritten or reinterpreted. The evidence tooling retains explicit v1 readers,
while all corrected collections, processed summaries, manifests, and generated
paper inputs use v2 artifacts and paths. The generic variable-cue scaffold is
separately named `LOCUS-development-backup-v1` and
`LOCUS-development-context-v1`; it cannot be mistaken for the deployed
protocol.

## Claim Boundary

This mapping supports only the evaluated composition and bounded implementation
observations. It does not establish cue memorability or entropy, independent
administration, resolver privacy, concurrent or geographic scalability, a
complete public admission design, a global attempt bound, party-state rollback
resistance, or an independent cryptographic audit.
