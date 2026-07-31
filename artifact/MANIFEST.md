# Artifact Manifest Policy

The final expanded artifact must use an explicit allowlist and a new manifest
version.

It must exclude:

- Git metadata and developer identity;
- credentials, keys, tokens, certificates, and accounts;
- raw cues or candidate values;
- databases, snapshots, logs, traces, dumps, and caches;
- build outputs and local environments;
- historical paper results presented as current evidence;
- external PDFs with unverified redistribution rights.

Exact-profile baseline evidence may be included when the allowlist and
documentation label it unambiguously. The integrated repository contains the
manuscript, but an anonymous artifact may continue to exclude manuscript source
and PDF. Repository inclusion does not imply artifact inclusion.

Every included file must have a canonical path, size, SHA-256 digest, and
license coverage. The extracted tree must pass the complete gate without Git
metadata or hidden developer state.
