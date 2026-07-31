# Artifact Manifest Policy

The active baseline package uses the explicit v2 allowlist implemented in
`prototype/locus/artifact_package.py`, package-specific documentation under
`artifact/package-v2/`, and `LOCUS-anonymous-artifact-v2` manifests validated by
`docs/schemas/artifact-manifest-v2.schema.json`.

It must exclude:

- Git metadata and developer identity;
- credentials, keys, tokens, certificates, and accounts;
- raw cues or candidate values;
- databases, snapshots, logs, traces, dumps, and caches;
- build outputs and local environments;
- historical paper results presented as current evidence;
- external PDFs with unverified redistribution rights.

The v2 allowlist includes only the exact-profile frozen v2 aggregate evidence
and generated performance inputs. It deliberately excludes the manuscript,
review PDF, bibliography, superseded results, external papers, and
repository-facing planning documents. Repository inclusion does not imply
package inclusion.

Every included file must have a canonical path, size, SHA-256 digest, and
license coverage. The extracted tree must pass the complete gate without Git
metadata or hidden developer state.
