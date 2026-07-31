# LOCUS reference cue policy

Status: P3.1 frozen design contract with the P3.2 deterministic fixture and P3.6
pinned canonicalization corpus implemented, 2026-07-21. This is an implementation
specification, not evidence that the cues are memorable, unpredictable, or
usable by people.

## Problem statement

LOCUS needs one deterministic way for a fresh client to turn structured recovery
input into the TPASS password input without placing a cue identifier or verifier
in the cloud or at a recovery party. The reference case uses exactly three
location-person relationships. Resolver display data is only a selection aid;
the cryptographic input is a narrow, versioned canonical descriptor.

The policy must prefer explicit failure over silent reinterpretation. It does not
perform fuzzy matching, guess aliases, try several candidate encodings, or issue
multiple TPASS attempts behind one user action.

## Threat assumptions and non-claims

- The enrollment and recovery client is trusted while processing cues. Endpoint
  compromise reveals them and is outside the recovery confidentiality claim.
- A local fixture resolver is deterministic but synthetic. An external resolver
  can observe queries, selected candidates, locale, and timing and can manipulate
  results.
- Personal information may be public, socially known, correlated, or low entropy.
  Three pairs are a reference interface choice, not an entropy claim.
- Exact canonicalization prevents accidental representation ambiguity; it does
  not make the underlying input secret or stable over a person's lifetime.
- A fresh client may use the same account-backed map/contact sources, but it has
  no secret enrollment-client file and receives no stored cue hints from LOCUS.

## Policy identifier and public metadata

The policy identifier embedded in the canonical recovery input is
`LOCUS-location-person-set-v1`. The intended public policy metadata is:

```json
{
  "version": "LOCUS-location-person-set-v1",
  "pair_count": 3,
  "location_precision": 4,
  "person_channel_types": ["email", "phone"],
  "resolver_profile": "LOCUS-deterministic-fixture-v1"
}
```

The external-resolver deployment replaces `resolver_profile` with a public,
versioned profile identifier. That identifier describes behavior and supported
record types; it is not a user-specific source or record identifier.

The current deployed profile authenticates the exact one-field metadata object
`{"version":"LOCUS-location-person-set-v1"}`. The archived Cycle 1 v1 corpus
used the legacy envelope label `LOCUS-local-context-v1`; it remains immutable
historical evidence and must not be relabeled, merged with v2 evidence, or used
as evidence for the corrected profile.

The backup, cloud, parties, attempt ledger, audit records, and ordinary logs must
not contain location coordinates, place names, contact names, contact values,
provider record identifiers, pair hashes, the ordered/set cue tuple, candidate
lists, resolver queries/results, or a cue-derived password verifier. In
particular, publishing a hash of any individual descriptor would create a cheap
dictionary predicate and is forbidden.

## Input shape

One recovery input contains exactly three pairs. Each pair contains:

1. one canonical location identity; and
2. one canonical person contact channel selected by the user for that location.

The association is significant: swapping people between two locations changes
the input. The order in which the three pairs are entered is not significant.

An input is rejected before TPASS if it has fewer or more than three pairs, an
unsupported field or channel type, a malformed value, two identical locations,
two identical person channels, or two identical complete pairs. Rejecting reuse
avoids accidental loss of the intended three-pair structure. This is a policy
choice, not a claim that distinct pairs are statistically independent.

## Canonical location identity

Resolver results may contain provider identifiers, names, addresses, categories,
and localized labels for display. None of those enter the password input. The
canonical identity is the selected WGS 84 point quantized to four decimal degrees:

```json
{"latitude_e4": 495987, "longitude_e4": 61344}
```

Rules:

- The resolver supplies latitude and longitude as decimal strings, never binary
  floating-point values.
- Latitude is in `[-90, 90]` and longitude is in `[-180, 180]`.
- Parse the strings as exact base-10 decimals, multiply by `10000`, and round to
  the nearest integer using round-half-to-even.
- Reject NaN, infinity, exponent notation, signed zero variants, leading/trailing
  whitespace, more than 8 fractional digits, and coordinates outside the range.
- Canonical zero is integer `0`. The poles and antimeridian are not wrapped or
  aliased; `-180` and `180` are distinct canonical longitudes.
- Four decimal places are roughly an 11 m latitude grid. This deliberately
  coalesces very nearby points and reduces precision leakage inside the client,
  but the canonical coordinates themselves must still never leave it.

The client displays the quantized point before enrollment and recovery so the
user can reject an unexpected resolver result. Provider record IDs and labels
may change without changing the cue if they still resolve to the same quantized
point. Moving across a quantization boundary changes the cue and safely fails.

## Canonical person identity

Names and relationship labels are display-only because case, spelling, locale,
and naming changes are too unstable for the cryptographic descriptor. The user
selects exactly one contact channel from the chosen person record. The descriptor
is one of:

```json
{"type": "email", "value": "friend@example.org"}
{"type": "phone", "value": "+352621123456"}
```

Email rules:

- Input must be valid UTF-8, normalized to Unicode NFC, with no surrounding
  Unicode whitespace or control characters.
- The reference policy accepts ASCII addr-spec values only. It rejects comments,
  display names, quoted local parts, domain literals, consecutive dots, and an
  absent local or domain part.
- Lowercase both local and domain parts using ASCII lowercase. This intentionally
  follows common account-directory behavior even though SMTP local-part case can
  theoretically be significant; deployments with case-sensitive addresses must
  reject them rather than silently use this policy.
- The domain must be an ASCII A-label supplied by the resolver profile. Unicode
  domains are converted by the resolver profile before policy validation; the
  conversion version is part of that profile, not guessed by the client.

Phone rules:

- The resolver must supply an E.164 number beginning with `+`, followed by 8 to
  15 ASCII digits; the first digit after `+` must be 1--9.
- Spaces, punctuation, extensions, service codes, local dialing forms, and
  locale-dependent inference are rejected. The UI may use locale to help the user
  choose a country code, but locale never enters canonicalization.

Adding, removing, or changing the selected contact channel changes the cue.
Changing the display name, relationship label, or unselected channels does not.

## Pair encoding and order independence

For each validated pair, encode this exact object with the repository's canonical
JSON rules (UTF-8, sorted keys, no insignificant whitespace):

```json
{
  "location": {"latitude_e4": 495987, "longitude_e4": 61344},
  "person": {"type": "phone", "value": "+352621123456"},
  "version": "LOCUS-location-person-pair-v1"
}
```

Compute `pair_key = H("LOCUS/cue-pair/v1" || encoded_pair)`. Sort the three full
encoded pair objects by the unsigned lexicographic order of their 32-byte
`pair_key`; if keys collide for different encodings, sort those encodings
lexicographically as a deterministic tie-breaker. Hash collisions are not used as
an equality test: duplicate checks compare full canonical location, person, and
pair encodings.

The password-input preimage is the canonical encoding of:

```json
{
  "pairs": ["<sorted full pair object 1>", "<...2>", "<...3>"],
  "version": "LOCUS-location-person-set-v1"
}
```

The schematic strings above stand for embedded objects, not JSON strings. The
client passes this byte encoding and the public recovery identifier to the
native domain-separated TPASS password mapping. The recovery identifier binds
the backup identifier in the retained epoch-1 profile. The recovery nonce does
not enter the TPASS password mapping; it is the wrapping-key HKDF salt.
Intermediate descriptors, pair keys, preimage bytes, and derived scalars are
client-local ephemeral values.

The exact synthetic reference bytes are pinned in
`prototype/test-vectors/cue-policy-v1.json`. The corpus binds the default resolver
fixture to one 511-byte canonical encoding and its SHA-256 digest, verifies
multiple input orders, and requires locale-dependent decimal/phone forms and
non-ASCII coordinate, email, or plus-sign variants to fail before an online
attempt. These are software interoperability vectors, not human-data evidence.

## Unicode and locale rules

- All accepted text first undergoes strict UTF-8 decoding and Unicode NFC using a
  pinned runtime/database version recorded in artifact provenance.
- Canonical cryptographic fields use only integers or the constrained ASCII
  person-channel forms above. General Unicode place/person labels are display-only.
- Locale may affect search ranking, display, and phone-country UI assistance. It
  must not alter an already canonical coordinate or E.164/email value.
- The client records the runtime, Unicode database, and resolver-profile versions
  in experiment output, not in user-specific persistent cue state.

## Ambiguity, drift, and migration

The resolver may show several candidates, but the client never auto-selects one.
The user explicitly selects a point and a contact channel and confirms their
canonical summaries. If a recovery query is ambiguous, missing, malformed, or
resolves across a coordinate boundary, the client stops before attempt
authorization. It does not probe alternatives through TPASS.

Once an attempt has been authorized, any resulting mismatch is one generic,
counted recovery failure. Parties cannot tell which pair or component differed.

There is no in-place policy reinterpretation. A policy-version change, coordinate
precision change, contact-normalization change, or resolver-profile change needs
a new backup epoch. Migration requires either the unlocked original key or a
successful recovery under the old policy, followed by fresh enrollment and
certified retirement of the old epoch. If neither is available, LOCUS fails
closed; an operator must not rewrite metadata to make old party state accept a new
policy.

## Invariants

1. Exactly three distinct location-person pairs enter derivation.
2. Pair order at input does not affect derivation; pair association does.
3. Equivalent permitted representations have one canonical byte encoding.
4. No user-specific cue descriptor or cue-checking digest crosses the client
   boundary or enters persistent operational state.
5. One confirmed canonical set produces one TPASS password attempt; the client
   never searches variants under one authorization certificate.
6. Policy changes create a new epoch and cannot reinterpret enrolled state.
7. All cue-related failures exposed by recovery are generic at the online oracle
   boundary.

## Failure behavior

Malformed input, unsupported versions, duplicates, unresolved ambiguity, and
missing channels fail locally before an attempt is requested. Resolver and local
validation errors may be actionable in a pre-attempt UI, but logs must contain
only coarse error categories and synthetic fixture identifiers.

After attempt authorization, wrong canonical input, TPASS proof/digest failure,
and backup decryption failure all return the same external recovery rejection.
Availability errors may be reported separately only when doing so cannot reveal
cue correctness; timing and message-size behavior must be measured.

## Test plan

- Fixed vectors for coordinate rounding, negative zero, boundaries, email and
  E.164 acceptance/rejection, Unicode NFC, and canonical JSON bytes.
- Permute all six orders of one three-pair set and require identical output.
- Change every association, coordinate cell, channel type, and channel value and
  require a different preimage.
- Reject pair counts other than three, every duplicate class, unknown fields,
  unsupported profiles/versions, floats, and locale-dependent phone forms.
- Exercise provider-label and record-ID drift that preserves canonical values,
  and coordinate/contact drift that safely fails.
- Recursively inspect backup objects, party databases, audit logs, traces, crash
  state, and status output for prohibited cue material.
- Verify that no alternative-candidate loop can reuse one attempt certificate.
- Run cross-platform vectors with pinned Python/Unicode versions.

## Evaluation plan

The artifact will report deterministic fixture success, drift outcomes, resolver
latency, bytes and metadata visible at each role, and network traces showing that
cue records remain client-local. Synthetic personas may measure candidate-space
behavior only as an attack-model exercise; they are not human-subject evidence.
No usability, memorability, entropy, or long-term stability result may be inferred
from software tests.

## Paper implications and implementation boundary

The paper may describe this as a conservative three-pair structured-input case
study and a versioned client-local data-flow boundary. It must not call the policy
memorable, high entropy, fuzzy, provider-private, or empirically usable.

The retained Compose deployment and deterministic resolver fixture use this
exact three-pair canonicalizer, and the pinned canonical/drift corpora exercise
it. The generic `prototype/locus/core.py` scaffold still accepts any nonempty
cue count, includes provider record fields and labels in hashing, and preserves
input order; its demo uses two pairs. Those generic behaviors are development
scaffolding, do not define the paper-facing protocol, and must not support
CLM-02, CLM-20, or performance claims.

The corrected profile is `LOCUS-reference-backup-v4` within
`LOCUS-compose-deployment-v2`. Strict validation rejects the archived v3/legacy
combination and every mixed label/version before authorization. New retained
results must use v2 evidence paths; the old corpus remains readable only through
the explicitly versioned historical evidence validators.
