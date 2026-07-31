# LOCUS Resolver Behavior And Drift Contract

Status: P3.7 deterministic simulation contract, version 1, 2026-07-21.

## Problem statement

A fresh recovery client may see renamed directory entries, reindexed map records,
changed coordinates or contact channels, missing records, ambiguous results, or a
new provider profile. LOCUS must define which changes preserve the same canonical
input, which produce one counted recovery mismatch, and which stop locally before
attempt authorization. It must not probe alternate interpretations automatically.

## Threat assumptions

The resolver may be stale, unavailable, observing, or malicious. It can cause
denial of service, canonical drift, or improved attacker guess ranking; the
baseline does not claim resolver privacy or integrity. The client endpoint is
trusted while it displays and selects results. Cloud storage and recovery parties
never receive the directory response, record identifiers, labels, coordinates,
or selected contacts.

## Versioned simulation interface

`LOCUS-deterministic-directory-v1` maps one exact `resolved` response containing
three selected location-person pairs to the P3.1 canonicalizer. Provider record
identifiers and NFC display labels are validated but discarded. Only decimal
coordinates and the selected email/E.164 channel enter canonicalization. Unknown
fields, malformed record identifiers/text, the wrong profile, a non-resolved
status, and any P3.1 policy violation produce the single local error `resolver
selection unavailable`.

The corpus `prototype/test-vectors/resolver-drift-v1.json` defines these outcomes:

| Scenario | Outcome | Attempt use |
| --- | --- | --- |
| Display/location/person rename only | same canonical input | normal recovery may continue |
| Map reindex/movement within the same `e4` cell | same canonical input | normal recovery may continue |
| Map movement across an `e4` boundary | canonical drift | one generic counted recovery failure if submitted |
| Selected contact changes | canonical drift | one generic counted recovery failure if submitted |
| Provider-profile version changes | local rejection; migrate by new epoch | no attempt requested |
| Ambiguous or missing result | local rejection | no attempt requested |

The stable/drift comparison exists only in the synthetic test harness, where the
enrollment fixture is known. A real fresh client must not store a baseline cue
digest or verifier to perform that comparison: it obtains one explicitly selected
input and learns success only through the budgeted TPASS recovery outcome.

## Invariants and failure behavior

1. Display labels and provider record identifiers never enter canonical bytes.
2. Resolver-profile changes never silently reinterpret an existing epoch.
3. Ambiguity, missing data, malformed responses, and unsupported profiles stop
   before authorization with one generic local category.
4. A syntactically valid but changed canonical input is not tested locally and
   consumes at most one authorized attempt if submitted.
5. The client never enumerates candidates or retries variants under one attempt.
6. Raw directory data remains client-local and is excluded from ordinary output.

The current deployment CLI emits only a generic failed record by default; its
optional operator diagnostic exposes an exception class, not a message. The full
public enrollment/recovery interface remains P3.4/P3.8 work and must preserve the
same pre-attempt versus counted-failure boundary without revealing which pair
changed.

## Test and evaluation plan

The versioned corpus currently verifies renamed entries, within/across-grid map
changes, changed contacts, provider-version change, ambiguity, and missing data.
All local-rejection cases have identical text. Remaining evaluation should run
the corpus on clean supported platforms, trace that local rejection makes zero
party requests, verify that canonical drift makes exactly one budgeted request,
inspect resolver/client traffic and logs, and compare the deterministic fixture
with any future self-hosted or external profile.

## Paper implications

The evidence supports deterministic software handling and explicit safe-failure
semantics only. It does not show that people remember the cues, that real provider
records remain stable, that the resolver is private, or that a renamed record is
necessarily the same real-world entity. Any paper claim must preserve those
limits.
