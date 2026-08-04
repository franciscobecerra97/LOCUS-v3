# LOCUS Local Isolated Deployment

Status: P4.10.1-P4.10.3 and the P4.8 one-party fallback gate implemented and
live-verified 2026-07-21. P4.9.3 adds authenticated lifecycle routes and
successor runtime-state reconstruction in five processes. P4.9.4's
`cross-epoch-runtime-mix-v1` Compose profile passed on 2026-07-22 with a
host-controlled party restart, exact report validation, output scanning, and
complete resource cleanup. P6.2's separate cloud-snapshot collection and
networkless attacker profile passed its development gate on 2026-07-22. P6.3's
stopped one-party collection and P6.4's matching combined-snapshot profile
passed their development gates on 2026-07-22/23. The archived v1 collection
retains those results for the superseded metadata profile. The authoritative
corrected v2 collection retained all three aggregate-only reports plus ten P7
blocks against clean cutover commit `12ca815` and pseudonymous host
`cycle1-v2-host-a`. All 33 v2 records passed output scanning and cleanup; no
LOCUS container, volume, or network remained after the collection audit.

D023 does not reinterpret this deployment or its retained results. It approves
a separately versioned P7.5 successor that connects the loopback UI/client
gateway to every required runtime service and becomes the primary P8/P9
system-under-test. P7.5 is not yet implemented; none of the commands in this
document starts that integrated system.

The performance runner builds its reference image under the fixed
`locus-performance-image-v1` Compose identity before a block and reuses the
inspected image ID in all three disposable scenario records. This avoids
project-label-dependent image IDs while preserving fresh scenario projects.

## Problem statement

The authenticated recovery-party subprocess path and S3-compatible backup path
now run as one local artifact. The deployment composes those exact
implementations while making role access, startup, persistence, failure, and
evidence boundaries inspectable.

This deployment is a same-host research artifact. Containers, networks, and
volumes demonstrate explicit software boundaries; they do not establish
independent administration, resistance to a malicious Docker host, or Internet
deployment security.

## Frozen deployment and D023 successor

The implemented graph in this document preserves the exact
`LOCUS-compose-deployment-v2` meaning and its frozen Yi profile. Its smoke,
attack, benchmark, configurable-endpoint, and retained-evidence workflows
remain valid only for their recorded manifests and provenance.

P7.5 will create a new deployment family with these runtime roles:

- an ephemeral UI/client gateway exposed only on host loopback;
- a local synthetic admission/capability service;
- an operator/discovery/signing service;
- an application storage gateway;
- a local S3-compatible object store;
- a resolver service; and
- five authenticated authorizer/holder parties.

The browser will reach only the UI/client gateway. The gateway will call the
other services through authenticated adapters, and the storage gateway alone
will hold provider credentials. A networkless bootstrap may create synthetic
credentials, public configuration, empty role roots, and fixtures, but it may
not inject Yi/aPPSS state, protected-key state, or surviving enrollment-client
state. Client A enrollment and Client B recovery will use separate ephemeral
roots and identities.

That system must exercise Yi and aPPSS at both 2-of-3 and 3-of-5 over five
authorizers with 4-of-5 authorization, all registered CuePolicies, and
same-suite and cross-suite successor flows. It remains a same-host research
profile. Multi-host placement and live AWS S3 are optional and require distinct
versioned profiles and, where applicable, execution authorization. P7.5 work
package 1 will assign the exact manifest, identifiers, validators, and operator
commands together; this frozen deployment document does not preassign them.

## Threat assumptions

- The Docker host, engine, Compose controller, build process, and one-shot
  provisioner are trusted for this local profile.
- Runtime party, resolver, client, and object-store containers are treated as
  distinct roles. A compromised runtime role should not receive another role's
  mounted secrets through the declared Compose graph.
- The client is ephemeral and trusted with its recovery input while an operation
  runs. The synthetic fixture is not human data.
- SeaweedFS mini mode has one generated administrative test credential. This is
  local S3 API conformance, not production cloud IAM evidence.
- No host port is published. Plain HTTP inside the `cloud` network is an explicit
  local-only exception; party protocol traffic continues to require pinned TLS
  1.3 mutual authentication.

## Role-access matrix

| Role | Writable state | Read-only inputs | Networks | Explicitly forbidden |
| --- | --- | --- | --- | --- |
| Provisioner | all five initially empty party volumes and ephemeral client volume | synthetic cue fixture and image code | none | network access and long-running service behavior |
| Client/profile runner | none | read-only client bundle/identity | `cloud`, `resolver`, `recovery` | party volumes/states, authorizer private keys, S3 data volume |
| Resolver | none | synthetic cue fixture | `resolver` | party/client/cloud volumes and credentials |
| S3-compatible store | cloud data volume | generated S3 credential | `cloud` | cue fixture, client identity, party state/volumes |
| Party `i` | only party `i` database in party `i` volume | its own TPASS state if `i <= 3`, authorizer key, server/peer identity, CA and public peer/configuration data | `recovery` | cue fixture, client volume, S3 credential/data, every other party volume/state/key |
| Snapshot collector | fresh snapshot volume | client bundle and exact S3 object | `cloud` | party volumes, resolver network, retained output beyond the canonical object/manifest |
| Offline snapshot attacker | none | read-only two-file snapshot volume | none | client/party/cloud volumes, credentials, resolver data, every network |

The provisioner is an explicit initialization authority, not an independently
secure party. It exits before runtime recovery. Re-running it over a partial or
inconsistent layout fails closed; an already complete layout is verified rather
than overwritten. It drops all Linux capabilities and restores only `CHOWN`,
`FOWNER`, and read-only `DAC_READ_SEARCH`, which are required to initialize,
transfer ownership of, and audit the private named volumes.

## Startup and recovery flow

Run the complete disposable gate from the repository root:

```console
uv run --frozen python tasks.py deployment-smoke
```

To run the same five party containers through the separately versioned public
endpoint setup, use:

```console
uv run --frozen python tasks.py deployment-configurable-smoke
```

The default [party endpoint setup](../deploy/party-endpoints.json) uses the five
local Compose service names. The
[five-host example](../deploy/party-endpoints.five-host.example.json) shows the
five DNS/IP fields that can later be replaced. The overlay only prepares and
binds endpoint configuration; it does not turn one Docker engine into five
hosts or deploy containers remotely.

1. The task runner generates a unique Compose project, image tag, S3 credential,
   bucket prefix, and clean named volumes without printing secrets.
   The multi-stage build pins its base images by multi-platform OCI digest and
   wheels the frozen hashed runtime dependency closure exported from `uv.lock`.
2. The networkless provisioner validates the exactly-three-pair synthetic
   fixture; creates native 2-of-3 TPASS state, a sealed synthetic key backup,
   4-of-5 attempt-authorizer configuration, and an ephemeral CA; and writes only
   each role's allowed files.
3. SeaweedFS, the deterministic resolver, and five parties start on their
   disjoint networks. Health checks use only each role's normal interface.
4. The client queries the resolver, reproduces the canonical recovery input,
   immutably creates and reads the exact S3 backup, reconciles the current ledger
   head, obtains one authorization certificate, completes native recovery through
   parties 1 and 3, and decrypts the backup locally.
5. The task runner inspects the resolved graph and live container state, runs a
   redacted snapshot audit, restarts party 1 over its same volume, and repeats
   recovery through parties 1 and 3 at the next counted slot.
6. The runner then stops party 1 and performs a third recovery through the fixed
   fallback set 2 and 3. It requires the certified consumed count to advance
   exactly from zero to three, scans logs/results for known secrets, and removes
   every container, network, and volume.

The pinned SeaweedFS process directs informational startup logs to its ephemeral
`/tmp` mount because the upstream startup banner includes the configured access
key. Only error-severity output reaches the container log; the smoke scan still
fails if either generated S3 credential appears there.

## Demo, benchmark, and attack profiles

The optional profiles start a fresh copy of the same base graph and invoke
the same packaged protocol implementation through its normal resolver, S3, and
party interfaces:

```console
uv run --frozen python tasks.py deployment-demo
uv run --frozen python tasks.py deployment-benchmark --runs 2
uv run --frozen python tasks.py deployment-attack --scenario resolver-unavailable-v1
uv run --frozen python tasks.py deployment-attack --scenario cloud-snapshot-no-offline-predicate-v1
uv run --frozen python tasks.py deployment-attack --scenario t-minus-one-party-snapshot-no-offline-predicate-v1
uv run --frozen python tasks.py deployment-attack --scenario cross-epoch-runtime-mix-v1
```

- `deployment-demo` performs one complete recovery and accepts only the exact
  redacted result used by the default client path.
- `deployment-benchmark` permits one to four complete recoveries because the
  current synthetic epoch has a four-attempt budget. Each sample includes
  resolver, cloud, attempt-authorization, remote native TPASS, and decryption
  time; it excludes image build, service startup, and provisioning. The runner
  validates the samples and summary, then attaches exact experiment metadata.
- `deployment-attack` accepts only a registered scenario and exact P6.1 report.
  The initial `resolver-unavailable-v1` scenario uses a nonexistent resolver
  path and passes only when no attempt is consumed. See `attack-report.md`.
- `cloud-snapshot-no-offline-predicate-v1` first runs the normal client to
  publish the synthetic backup, uses a one-shot collector to copy only exact S3
  bytes plus public locator/integrity metadata, and then runs two synthetic
  candidates in a separate non-root container with no network, credentials, or
  client/party mounts. Its retained Cycle 1 run matched zero local signals and
  zero boundary attempts; it is bounded implementation evidence, not a
  cryptographic proof or real-provider compromise.
- `t-minus-one-party-snapshot-no-offline-predicate-v1` completes one synthetic
  recovery, stops party 1, and gives a trusted networkless collector read-only
  access to that party's persistent volume and a fresh output volume. A separate
  non-root, credential-free, networkless process receives only the resulting
  snapshot read-only. Its retained Cycle 1 run matched one compromised party at
  threshold two, two candidates, zero local signals, boundary attempts, or
  secret-output exposures, a valid snapshot, and no cloud material. This is a
  bounded below-threshold check, not a compromise mechanism or proof.
- `cross-epoch-runtime-mix-v1` creates an immutable successor, obtains old/new
  lifecycle quorums, rejects a changed runtime package, verifies the 3/2
  no-quorum state, activates the successor, pauses while the host restarts party
  1, then requires retired-epoch refusal and successor recovery. It is a narrow
  lifecycle/mixing boundary, not rollback or global attempt-bound evidence. Its
  same-host development run passed on 2026-07-22.

Benchmark and attack results default to unsaved `development` evidence. Their
metadata deliberately warns about a dirty worktree, unlabeled host, or
unretained output. `--out` uses exclusive file creation and never overwrites a
result. `--evidence-class paper` additionally requires a clean Git state, a
non-default `--host-id`, and an immutable repository-relative path under
`experiments/raw/`; otherwise it fails closed. No development measurement in
this document is a paper-facing performance or security result.

## Invariants

1. No runtime service mounts more than its row in the role-access matrix.
2. No party environment contains S3 credentials and no party configuration
   contains ciphertext, cue records, another party's TPASS state, or another
   party's private identity.
3. The client bundle contains no TPASS party state or authorizer private key.
4. The S3 object digest equals the digest certified in every party configuration
   before an attempt is authorized.
5. Provisioning finishes before parties start; healthy parties use their normal
   pinned-mTLS endpoint and persistent database.
6. Restarting a party never recreates its volume or resets its consumed count.
7. Ordinary output and logs contain no cue records, private keys, TPASS state,
   S3 secret, recovered group secret, wrapping key, or decrypted private key.
8. Deployment checks do not make paper-facing performance or independent-
   administration claims.
9. Demo, benchmark, and networked attack profile services have the same runtime
   identity, mounts, networks, cloud environment, and dependency graph as the
   client.
10. Profile output and all service logs are scanned with generated credentials
    and every synthetic cue value as dynamic canaries before a result is shown.
11. The client selects a quorum-consistent TPASS set before authorization. It
    never switches that set after authorization, even when a selected party
    later fails; the attempt remains consumed.
12. The cloud-snapshot collector is a trusted one-shot collection authority with
    only read-only client input, the cloud network/credential, and a fresh output
    volume. The attacker receives only that volume read-only, runs as non-root,
    has no environment credentials, and uses `network_mode: none`.
13. The party-snapshot collector is a trusted one-shot copier with no network or
    environment credentials, a read-only stopped `party1` volume, and a fresh
    output volume. Its non-root attacker receives only the copied volume
    read-only, has no credentials, and uses `network_mode: none`.

## Failure behavior

- Missing/partial volumes, malformed fixtures, configuration disagreement,
  unavailable services, certificate failures, S3 mismatch, insufficient quorum,
  or decryption failure produce a generic nonzero client/provisioner result.
- One unavailable authorizer is tolerated when the remaining compact 4-of-5
  quorum and a quorum-consistent 2-of-3 TPASS set are reachable. Insufficient
  authorization or TPASS availability fails generically; the runner retains no
  secret output and always attempts full Compose cleanup.
- Compose validation fails before startup if a service gains an unexpected
  network, mount, environment secret, host port, capability, or unpinned image.
- A failed smoke run is evidence of an artifact/deployment defect, not of cue
  correctness or cryptographic insecurity by itself.
- An invalid benchmark summary, rewritten attack scenario, secret-bearing field,
  contradictory attack status, or existing output path is rejected without
  emitting or overwriting evidence.
- An extra snapshot file, malformed/noncanonical manifest or object,
  substitution, prohibited field, candidate signal, or attempted file/network
  access prevents the cloud-snapshot scenario from matching its passing report.
- An unexpected/missing party file, noncanonical or mismatched manifest,
  malformed key/native/database state, checkpoint mismatch, candidate signal,
  secret-output exposure, or attempted file/network access prevents the
  one-party snapshot scenario from matching its passing report.

## Test and evaluation plan

- Unit-test provisioning idempotency, partial-layout refusal, certificate/config
  consistency, and recursive role-state separation.
- Validate the resolved Compose service, image, network, volume, port,
  capability, read-only-root, and environment matrix before startup.
- Inspect live container mounts/networks/environments and redacted logs.
- Complete two end-to-end recoveries separated by a party restart, stop party 1,
  recover through parties 2 and 3, and verify the certified consumed count
  advances exactly to three without reset.
- Record build/start/provision/recovery/restart/cleanup outcomes and software
  versions. Latency from this smoke profile is diagnostic only; P8 defines
  paper-facing distributions and scenarios.
- Live-verify each optional profile, its cleanup, and its recursive canary scan.
  Extend the attack registry one reviewed P6 scenario at a time rather than
  injecting unregistered shell faults.
- For the cross-epoch profile, verify that party 1 becomes healthy after the
  host-controlled restart before the runner resumes, that both immutable S3
  objects remain bound to their epochs, and that cleanup removes the one-off
  attack container and all Compose resources.
- For the cloud snapshot profile, verify the collector and attacker role graph,
  exact two-file snapshot, positive controls, aggregate-only report, and full
  removal of the snapshot volume with all other Compose resources.
- For the party snapshot profile, verify the stopped capture checkpoint, exact
  all-file manifest, one-party/native/database bindings, positive controls,
  aggregate-only report, and full removal of the snapshot volume with every
  other Compose resource.

## Paper implications

A green deployment supports the narrow claim that the current LOCUS components
can be composed reproducibly on one host with explicit role-specific mounts,
networks, credentials, native TPASS recovery, durable party restart, and an
S3-compatible backup. The same gate also shows one-party fallback for this
specific compact profile without weakening its 4-of-5 authorization quorum or
2-of-3 TPASS threshold. It does not support claims of independent operators,
cloud-provider IAM, rollback resistance, production hardening, human cue
usability, Byzantine liveness, or realistic distributed performance.

The profile gates additionally support the narrow artifact claim that demo,
benchmark, and registered attack workflows invoke the same deployed code and
emit versioned redacted results. The two-sample benchmark and
resolver-unavailable bootstrap remain development evidence only. P6.2-P6.4 and
the frozen P7 corpus now have clean, labeled, immutable aggregate-only records;
independent clean-host reproduction remains required.

These historical/component results do not support a claim about the D023
full-system path. After P7.5 closes, central P8 assurance and P9
performance/resilience results must bind the exact integrated manifest and
traverse its UI/client gateway and authenticated services. Unit, native,
same-process UI, P6, and this frozen Compose profile remain supporting controls,
not substitutes. No manuscript wording is authorized by D023 alone.
