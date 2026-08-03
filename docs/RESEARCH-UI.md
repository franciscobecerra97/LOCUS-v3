# Local Research UI

Status: P7.2--P7.4 implemented and locally verified on 2026-08-03 under D022.

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

## Verification and limits

Automated tests cover local assets, forbidden browser APIs and remote URLs,
strict routing/decoding, security headers, full enrollment/bootstrap/recovery,
and safe inspection. Interactive browser checks covered enrollment, recovery,
cross-suite successor creation, inspection, transient field clearing,
desktop layout, and a 390-by-844 responsive layout with no browser warning or
error output.

This is same-process research-client conformance. It is not retained P8/P9
evidence, public admission, real-provider operation, deployment separation,
production hardening, accessibility certification, a human study, or usability
evidence. Browser and operating-system screenshots, process memory, crash
collectors, accessibility technologies, browser extensions, and forensic
erasure remain outside the application's control. No manuscript claim is
changed by P7.
