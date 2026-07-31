# CuePolicy Registry Target Design

Status: owner-approved target-design direction under D005. No new policy
identifier is assigned until the schemas, canonical vectors, compatibility
rules, and implementation plan are approved and registered. This document does
not alter `LOCUS-location-person-set-v1` or the current manuscript.

## Goal

Demonstrate that LOCUS accepts multiple immutable structured-input policies
through one client-side contract while preserving the existing TPASS and
protected-key path. The registry establishes interface generality only. It does
not establish cue entropy, memorability, usability, or resistance to online
guessing.

## Common contract

Every policy declares:

- immutable identifier and schema version;
- exact accepted input shape and cardinality;
- resolver profile and the data visible to that resolver;
- bounded validation and canonicalization;
- Unicode, locale, case, whitespace, punctuation, and length rules;
- ordering, duplicate, ambiguity, missing-input, and drift behavior;
- deterministic canonical output bytes or one generic local failure;
- policy-specific domain separation; and
- canonical positive and negative vectors.

Policies do not emit hints, fuzzy alternatives, multi-candidate retries,
password-derived authenticators, or a persisted offline verifier.

## Frozen composite policy

`LOCUS-location-person-set-v1` remains byte-for-byte immutable. It continues to
accept exactly three distinct location-person pairs, use the frozen pair and
set encodings, and serve as the resolver-backed reference policy. Extracting
shared atom helpers must not change its canonical bytes, errors, TPASS password
input, backup behavior, or retained vectors.

## Approved atomic policy families

The names below are design labels, not final protocol identifiers.

### Quantized-coordinate set

- Input: exactly three distinct objects containing only `latitude` and
  `longitude` decimal strings.
- Validation: the frozen coordinate grammar and bounds from the existing v1
  policy.
- Canonical atom: signed integer latitude/longitude values at `10^-4` degrees
  using decimal half-even rounding.
- Ordering: policy-specific deterministic ordering over canonical atom bytes.
- Resolver: `NoResolver` for the approved direct-coordinate profile.
- Rejection: duplicate canonical coordinates, locale-specific numbers,
  non-ASCII numeric forms, out-of-range values, negative zero, unknown fields,
  and unsupported versions.

### Canonical-phone set

- Input: exactly three distinct phone-number strings.
- Validation and canonical atom: strict E.164 `+` followed by 8--15 digits,
  with a nonzero first digit after `+`, matching the existing v1 atom grammar.
- Ordering: policy-specific deterministic ordering over canonical atom bytes.
- Resolver: `NoResolver`.
- Rejection: national/local forms, inferred country codes, whitespace,
  punctuation, extensions, Unicode lookalikes, duplicate canonical values,
  unknown fields, and unsupported versions.

### Canonical-email set

- Input: exactly three distinct email-address strings.
- Validation and canonical atom: the constrained ASCII local-part/domain
  grammar used by the existing v1 atom, with NFC input, at least two valid
  domain labels, and lowercase canonical output.
- Ordering: policy-specific deterministic ordering over canonical atom bytes.
- Resolver: `NoResolver`.
- Rejection: display names, comments, Unicode or non-ASCII forms, malformed or
  single-label domains, duplicate canonical values, unknown fields, and
  unsupported versions.

## Encoding and domain separation

Shared atom canonicalizers may be reused internally, but the atomic policies
must not reuse the composite policy's top-level encoding or policy domain. Each
canonical output contains its own final registered policy identifier and an
exact list field for its atom type. Policy selection is authenticated by the
`RecoveryDescriptor` and is included in the TPASS password-input domain.

An input valid under one policy must not be interpreted under another. The
conformance corpus includes cross-policy inputs, identifiers, descriptors, and
recovery attempts that must fail before secret-dependent recovery.

## Resolver profiles

The registry initially exposes two resolver behaviors:

- the frozen deterministic resolver fixture used by the composite policy; and
- `NoResolver`, which performs no network lookup and returns direct validated
  input to the selected atomic policy.

An external location resolver is a later optional adapter. It requires a new
provider/version profile, bounded query and result behavior, declared
ambiguity/drift outcomes, privacy-safe observations, and separate execution
approval. It may not enumerate alternatives through TPASS.

## Public metadata and limitations

The descriptor exposes the selected policy identifier and therefore the input
category. Email addresses, phone numbers, and quantized locations may have
small or socially predictable candidate spaces. The project claims only that
the declared cloud and below-threshold persistent-state views do not obtain a
local offline predicate under the LOCUS/TPASS assumptions. Authorized online
clients can still submit guesses subject to the separately declared admission
and deployment controls.

## Required evidence

- Frozen v1 vectors and TPASS/backup behavior remain byte-identical.
- Every new policy has canonical positive and negative vectors.
- All input orders produce one canonical set encoding.
- Duplicate canonical atoms and malformed/unsupported input fail locally.
- Cross-policy, cross-version, and descriptor-policy mixing fail closed.
- The corpus passes on clean Linux and Windows.
- One independent vector consumer reproduces the registered bytes.
- Persisted-state and output scans find no raw atoms, canonical output,
  password input, hints, or verifier outside the active client.

