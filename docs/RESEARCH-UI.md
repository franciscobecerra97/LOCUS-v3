# Local Research UI

Status: P7.2--P7.4 implemented and locally verified on 2026-08-03 under D022.
D023 preserves this UI, and P7.5 now connects it to the deployed service plane
under a separate integrated deployment/configuration identity.

D025/P7.7 assigns the implemented `LOCUS-managed-client-ui-v1` over
`LOCUS-client-api-v2` plus the distinct `LOCUS-local-manager-ui-v1`. Those
profiles do not reinterpret this v1 UI. The Manager UI contains only
sanitized lifecycle controls; the managed Client UI contains enrollment and
recovery. `management` and `client-lifecycle` are disjoint, and a managed
Client cannot reach the Manager UI/API. Transient synthetic-key reveal and the
client recovery-package upload/download are permitted only under the assigned
profiles and their P7.7-tested output-safety boundary.

The managed Manager and Client documents are published over separate
`manager-edge` and `browser-edge` networks. Manager stop/start, restart, and
kill/start controls for a Client retain its public ID but clear its volatile UI/
API state and rotate proof identity; the Manager UI must warn that these are
destructive resets. Destroy removes the Client and ID.

The managed Client locks enrollment fields until the backend reports a loaded
transient key; package recovery remains available to a clean Client without a
preexisting key. The Manager disables mutating lifecycle controls once complete
shutdown begins while keeping read-only refresh available. These are thin-UI
interaction guards within the assigned API semantics, not new recovery,
lifecycle, usability, or evidence claims.

## Purpose and boundary

`LOCUS-local-research-ui-v1` is a thin, synthetic-only interface over the
frozen `LOCUS-client-api-v1` boundary. It provides enrollment, clean-client
bootstrap and recovery, explicit successor preparation, and a safe research
inspector. The browser contains no CuePolicy canonicalizer, recovery-suite
implementation, descriptor verifier, admission implementation, storage
adapter, or lifecycle coordinator.

The interface is standards-based semantic HTML, local CSS, and local
JavaScript served by the pinned Python runtime. It has no third-party web
runtime, remote asset, telemetry endpoint, service worker, cookie, or browser
storage. The server accepts loopback hosts only and disables request logging.

## Start the interface

From the repository root, install the frozen environment and run:

```console
uv sync --frozen
uv run --frozen python tasks.py ui
```

The command prints the loopback URL, which is normally
`http://127.0.0.1:8765/`. A different loopback port may be selected with
`--port`. Do not enter real cues, private keys, account data, or credentials.

This command starts the completed same-process component interface only. It
does not start the D023 admission, operator/discovery, storage gateway,
S3-compatible store, resolver, or five-party deployment. The separate
integrated workflow uses `integrated-config`, `integrated-start`,
`integrated-stop`, and `integrated-smoke` after validating the P7.5 manifest and
service graph.

## Implemented workflows

Enrollment requires an explicit Yi TPASS or aPPSS suite, a preconfigured
2-of-3 or 3-of-5 holder profile, and one registered CuePolicy. Synthetic key
generation/import, transient normalized preview, public-key fingerprint,
public recovery-receipt export, redacted role placement, and input disposal are
visible. Preview values remain active-client data and are cleared after
enrollment.

Recovery starts only from an exported public receipt. Bootstrap authenticates
the current descriptor/bundle state before the UI renders the enrolled suite,
policy, epoch, threshold, and authorization quorum. Recovery has no suite
selector or fallback. Successful recovery reports only the verified public-key
fingerprint and public status. Successor preparation separately requires an
explicit suite, holder profile, and protected-key rotation choice.

The inspector accepts a public receipt and displays only role placement,
registered public identifiers, safe digests, message categories, and aggregate
byte/item counts. It uses the same recursive safe-inspection result as the
client API and never receives secret-bearing state.

## Local HTTP boundary

The fixed routes are:

- `GET /`, `GET /assets/styles.css`, and `GET /assets/app.js`;
- `GET /api/v1/catalog`;
- `POST /api/v1/preview-policy`;
- `POST /api/v1/enroll`, `/bootstrap`, `/recover`, `/successor`, and `/inspect`.

POST requests require exact JSON content type, bounded bodies, and unique
object keys. Queries, fragments, unknown routes, oversized bodies, malformed
JSON, and non-finite values fail closed. Public operations pass the repository
output-safety validator; transient policy preview is separately labelled by an
HTTP response header and is never logged.

Every response disables caching and framing and applies a self-only content
security policy, no-referrer policy, restrictive permissions policy, and MIME
sniffing protection. HTML additionally requests clearing of browser cache,
cookies, and storage. Copy/cut and printing are disabled in the interface, and
page teardown clears in-memory form values.

## P7.5 integrated realization

P7.5 packages the same semantic UI and `LOCUS-client-api-v1` route meanings in
an ephemeral UI/client-gateway container exposed only on host loopback. The
browser must not contact recovery parties, the provider, or Docker directly.
The gateway replaces the current same-process record-store bindings with
authenticated adapters to:

- the local synthetic admission/capability service;
- operator-signed discovery and public recovery metadata;
- the application storage gateway and, behind it, the local S3-compatible
  store;
- the resolver service only when the selected policy requires it; and
- five authorizer/holder party processes.

The UI itself gains no CuePolicy, suite, descriptor, storage, admission, or
lifecycle logic. It must cover Yi and aPPSS at 2-of-3 and 3-of-5, all four
CuePolicies, isolated enrollment and clean-client recovery, and explicit
same- or cross-suite successor creation through those deployed services. The
reproducible profile remains local and synthetic; optional multi-host or AWS
profiles require separate identities and execution approval.

## Verification and limits

Automated tests cover local assets, forbidden browser APIs and remote URLs,
strict routing/decoding, security headers, full enrollment/bootstrap/recovery,
and safe inspection. Interactive browser checks covered enrollment, recovery,
cross-suite successor creation, inspection, transient field clearing,
desktop layout, and a 390-by-844 responsive layout with no browser warning or
error output.

The completed P7 checks are same-process research-client conformance. They are
not retained P8/P9 evidence and cannot substitute for the completed P7.5
full-system gate. The P7.5 gate is also ordinary implementation verification,
not retained evidence. Public admission, real-provider operation,
independent administration, production hardening, accessibility certification,
a human study, and usability remain outside this profile. Browser and
operating-system screenshots, process memory, crash collectors, accessibility
technologies, browser extensions, and forensic erasure remain outside the
application's control. No manuscript claim is changed by P7 or D023.
