# Anonymous Artifact Manifest

The package is built from an explicit allowlist. It contains:

- the Apache-2.0 software license, CC BY 4.0 documentation/material notice, and
  third-party licensing inventory;
- pinned build metadata, lockfiles, task runner, and continuous-integration
  workflow;
- the reviewer installation, evaluation, and package-boundary guides;
- Python and Rust implementation source, tests, and synthetic vectors;
- isolated same-host deployment configuration and fictional resolver fixtures;
- machine-readable experiment schemas;
- retained aggregate-only attack and performance records;
- the deterministic processed performance summary; and
- manifest-bound generated paper-table inputs.

It does not contain:

- version-control history, remotes, branches, or author identity metadata;
- internal project-management records or private research notes;
- the manuscript, compiled PDF, bibliography, or LaTeX support package;
- superseded experiment records or generated inputs;
- temporary files, caches, virtual environments, compiler outputs, local
  benchmarks, logs, traces, packet captures, or core dumps;
- credentials, certificates, private keys, real user or cue data, snapshots,
  or databases; or
- files containing local user-directory paths or author-identifying repository
  information.

`artifact_manifest.json` records every packaged path, size, and SHA-256 digest,
plus the clean source revision that produced the archive. In an extracted
package, the quality and provenance gates validate source paths and bytes
against this manifest without requiring version-control metadata.

The retained experiment records contain pseudonymous host labels and source
revision identifiers as immutable provenance. They contain no author names,
institutional identifiers, personal repository URLs, or local filesystem
paths.
