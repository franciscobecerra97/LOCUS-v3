# LOCUS Output-Safety Contract

Status: P1.11 enforced output and retained-profile contract, 2026-07-23;
D023 integrated-system obligations added 2026-08-04. P7.5 implementation and
pre-evidence output gate are complete; retained P8/P9 evidence remains pending.

## Problem statement

Normal terminals, logs, status results, traces, benchmark files, attack-result
files, and paper artifacts must not expose raw cues or selected resolver records,
derived cue identifiers, TPASS passwords or states/shares, wrapping keys, private
keys, recovered secrets, party-local cryptographic randomness, or credentials.
The control must fail closed before serialization rather than relying only on a
later text scan.

## Enforced normal-output path

`prototype/locus/redaction.py` recursively validates JSON-bound output. It
rejects prohibited field names at any depth, private-key markers, non-finite
numbers, non-JSON values, and pathologically deep or large values. The deployment
CLI and benchmark runner validate their complete result before emitting it.
Experiment configurations pass through the same check. Deployment smoke testing
also scans combined service logs and client output for field markers, private-key
blocks, and per-run secret/cue canaries; findings report category labels only.

Operator diagnostics may expose an exception class, but never an exception
message. This avoids copying attacker-controlled or secret-bearing values from an
exception into ordinary output.

This is an application-layer guard, not proof that Python runtimes, operating
systems, container engines, crash collectors, debuggers, or third-party libraries
cannot retain memory. Core dumps and external tracing must remain disabled in
paper-facing deployments and need separate deployment verification.

## Retained Compose profile evidence

`docs/retained-profile-evidence.md` freezes the only normal retained trace for
Compose attack, benchmark, and performance profiles. It contains the
registry-bound aggregate result, exact experiment provenance, and a fixed
machine-readable trace policy.
It never contains arbitrary service logs, snapshot bytes, database files,
packet captures, exception text, candidate values, per-candidate outcomes, or
credentials.

The main and focused S3 Compose definitions set the container core-file soft and
hard limits to zero. The main resolved-graph validator requires this for every
service, and live default-deployment inspection checks it for recovery parties,
the resolver, and S3. Successful profile logs are scanned with dynamic canaries
and then discarded during exact-project cleanup rather than copied into retained
evidence. The exclusive evidence writer synchronizes, rereads, and revalidates
the canonical file.

## Unsafe synthetic-only inspection design

No unsafe inspection mode is currently implemented or enabled. If a later
debugging task demonstrates a concrete need, `synthetic-inspection-v1` must meet
all of these conditions:

1. require both a dedicated command-line flag and the exact acknowledgement
   environment variable documented by that implementation;
2. accept only the committed synthetic fixture and refuse arbitrary cue input;
3. require the `inspection` profile and `development` evidence class;
4. refuse benchmark, attack-result, paper, CI, and deployment-smoke profiles;
5. refuse network service startup and retained output;
6. place a prominent unsafe marker on every emitted record; and
7. remain excluded from all normal task-runner commands.

A single environment variable, a generic debug flag, or operator diagnostics
must never activate this mode. Until its isolation tests exist, the safest
implementation is its current absence.

## P7 local research UI

The D022 loopback UI has no unsafe inspection mode. Normal API results pass the
recursive public-output validator, while the transient CuePolicy preview is
marked as active-client-only and returned under no-store headers. The browser
source uses no remote URL, telemetry, cookie, service worker, local/session
storage, IndexedDB, clipboard API, console output, HTML injection helper, or
dynamic code evaluation. The Python HTTP adapter suppresses request logging
and exception text.

The researcher inspector is safe aggregation, not secret-state debugging. It
shows only role placement, versions/public identifiers, safe digests, message
categories, and byte/item counts already permitted by the client API. Copy/cut
and printing are disabled, but the application cannot prevent browser/OS
screenshots, accessibility or extension access, memory inspection, crash
collection, or forensic recovery. No UI output is retained as P8/P9 evidence.

## D023 integrated-system output boundary

P7.5 applies this contract to the complete browser-to-service path, not only
to the current same-process UI and frozen Compose runner. The host browser may
reach only the loopback UI/client gateway, and the browser receives no Docker,
provider, operator, or party credential. Every admission, discovery, storage,
resolver, and party adapter must normalize failures before they reach public
API output; provider and service exception text must never cross the boundary.

The completed integrated validation gate:

- disable core dumps and unreviewed observability for every runtime container;
- suppress request bodies, credentials, cues, candidate values, and
  secret-dependent outcomes in service and proxy logs;
- scan public API output and all collected service output with generated
  per-run cue, key, credential, and secret canaries;
- audit role environments, mounts, persistent state, networks, and resolved and
  live container graphs without retaining secret-bearing bytes;
- keep browser preview data transient, no-store, non-logged, and excluded from
  evidence;
- retain only schema-validated aggregate observations after discarding raw
  logs and exact-project cleanup; and
- use positive controls that prove the scans and state audits detect planted
  fictional prohibited material.

The current UI command and frozen deployment commands remain component
controls and do not satisfy this gate. P7.5 command names and manifest identity
are assigned; P8.3 must assign the privacy-safe trace schema and retained paths
before collection. Optional multi-host or live AWS profiles need
separate output-safety validation and cannot silently reuse the local result.

## Evidence and remaining limits

Focused tests cover safe metrics/status values, every prohibited category named
by P1.11.1, nested fields, private-key markers, dynamic secret/cue canaries,
fixed trace-policy enforcement, metadata/result cross-binding, canonical
serialization, exclusive publication, and reread validation. The frozen
Compose deployment smoke test covers that profile's composed output path and
live container core-file limit; it is not the D023 full-system result.
Privileged-host memory, host crash collectors, container-engine internals,
deleted blocks, and future external observability remain explicitly outside
this evidence boundary and require separate review if later introduced.
