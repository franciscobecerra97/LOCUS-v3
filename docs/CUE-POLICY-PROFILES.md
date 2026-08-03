# CuePolicy Profiles

Status: P5.2 design frozen and P5.3 atomic policies implemented on 2026-08-03
under D005. The three new policy identifiers are assigned with canonical
vectors and the exact registry. `LOCUS-no-resolver-v1` remains protected but
unimplemented until P5.4. No new policy is accepted by an enrollment or
recovery suite until that client flow explicitly selects its exact identifier.

## Common contract

The frozen `LOCUS-location-person-set-v1` policy remains byte-for-byte
unchanged. Each new policy is atomic: it accepts exactly one category of direct
structured input, requires exactly three distinct canonical members, and emits
one canonical byte string or fails. It never emits hints, alternatives, partial
results, or a verifier.

All three policies use these rules:

- the input is a JSON-like Python value with the exact shape stated below;
- unknown fields, booleans in numeric positions, non-ASCII category values,
  unbounded values, and implicit local-format conversion fail;
- canonical duplicates fail after normalization or coordinate quantization;
- members are ordered by the tuple
  `(hash_bytes(member_order_domain, encode(member)), encode(member))`;
- the output is the existing canonical `encode` of the exact top-level mapping;
- the top-level version value and member-order domain are policy-specific;
- raw input, canonical members, output bytes, and candidate-derived values are
  transient client state and are never resolver, cloud, descriptor, or party
  state; and
- the public policy identifier reveals the selected input category.

Canonical output bytes are not directly interchangeable recovery-suite
password inputs. A recovery suite must apply its separately versioned password
input domain while binding the exact suite identifier, policy identifier, and
canonical bytes. The frozen Yi/composite-policy input is not reinterpreted.

## Quantized coordinate set

Reserved identifier: `LOCUS-quantized-coordinate-set-v1`

Reserved member-order domain:
`LOCUS/quantized-coordinate-set/member-order/v1`

Accepted input is a list of exactly three mappings. Each mapping contains
exactly `latitude` and `longitude`, both decimal strings. The lexical grammar is
`-?(0|[1-9][0-9]*)(\.[0-9]{1,8})?`; leading `+`, exponent notation,
whitespace, leading zeroes, and negative zero are invalid. Latitude must be in
`[-90,90]` and longitude in `[-180,180]` before quantization.

Each value is multiplied by 10,000 and rounded to an integer using decimal
round-half-even. A canonical member is exactly:

```text
{"latitude_e4": integer, "longitude_e4": integer}
```

The canonical output is:

```text
{
  "coordinates": [three canonically ordered members],
  "version": "LOCUS-quantized-coordinate-set-v1"
}
```

Two inputs that quantize to the same latitude/longitude pair are duplicates and
fail. No geocoder, place name, datum conversion, fuzzy radius, or nearby-point
enumeration is part of this policy. WGS84 is the declared interpretation of the
input; the implementation does not measure device accuracy or human recall.

## Canonical phone set

Reserved identifier: `LOCUS-canonical-phone-set-v1`

Reserved member-order domain: `LOCUS/canonical-phone-set/member-order/v1`

Accepted input is a list of exactly three ASCII strings. Each string must match
`\+[1-9][0-9]{1,14}`: a leading plus followed by 2--15 digits, with a nonzero
first digit. This is the policy's bounded E.164 lexical form. It performs no
country inference, dialing-prefix conversion, spacing or punctuation removal,
extension handling, number-plan lookup, ownership check, or reachability check.

The canonical member is the input string unchanged. The canonical output is:

```text
{
  "phones": [three canonically ordered strings],
  "version": "LOCUS-canonical-phone-set-v1"
}
```

Byte-identical canonical numbers are duplicates and fail.

## Canonical email set

Reserved identifier: `LOCUS-canonical-email-set-v1`

Reserved member-order domain: `LOCUS/canonical-email-set/member-order/v1`

Accepted input is a list of exactly three ASCII strings, each at most 254
characters. It must contain one `@`. The local part is 1--64 characters and is
one or more dot-separated atoms drawn from this ASCII set:

```text
A-Z a-z 0-9 ! # $ % & ' * + / = ? ^ _ ` { | } ~ -
```

Empty atoms and leading, trailing, or repeated dots fail. The domain is at most
253 characters, contains
at least two labels, and every 1--63 character label starts and ends with an
ASCII alphanumeric character and otherwise contains only ASCII alphanumeric
characters or `-`.

The complete address is normalized to lowercase, matching the frozen composite
policy's constrained contact rule. No Unicode/IDNA conversion, comments,
quoted strings, address display names, provider aliasing, deliverability check,
or local-part equivalence inference is performed. This is a deliberately
constrained LOCUS identifier grammar, not a claim to accept every RFC-valid
mailbox.

The canonical output is:

```text
{
  "emails": [three canonically ordered lowercase strings],
  "version": "LOCUS-canonical-email-set-v1"
}
```

Addresses equal after lowercasing are duplicates and fail.

## Direct-input resolver profile

Reserved identifier: `LOCUS-no-resolver-v1`

The three atomic policies declare `NoResolver`. P5.4 implements this adapter; it
performs no lookup and has no external observer. It invokes exactly the selected
policy once on the supplied structured input and returns that policy's
identifier and canonical bytes. A policy mismatch, malformed input, or
ambiguous/multi-candidate value fails; it never retries a recovery suite with
variants.

The frozen composite policy continues to use
`LOCUS-deterministic-directory-v1` in the reproducible reference path. A real
location provider remains separately execution-gated and is not part of P5.

## Stable local error contract

Errors occur inside the active client before suite invocation. P5.3 assigns
typed internal error codes for wrong shape/cardinality, invalid member, and
canonical duplicate while retaining category-specific local messages. Remote
roles receive no partial canonical value or failure detail. Error normalization
at admitted recovery boundaries remains unchanged.

## Claim boundary

These policies demonstrate that the LOCUS interfaces are not tied to one
composite location-person representation. They do not establish entropy,
memorability, usability, ownership, geographic accuracy, address validity, or
resistance to dictionary guessing. Policy/category disclosure and input
guessability remain explicit limitations.

## Implementation and vectors

The implementations live in `prototype/locus/cue_policy.py` and the exact
registry in `prototype/locus/cue_policy_registry.py`. The shared corpus is
`prototype/test-vectors/cue-policy-conformance-v1.json`. It includes one legacy
vector-source binding and pinned vectors/errors for each new policy. A separate
consumer checks canonical JSON, hex, and digests without importing LOCUS code.
