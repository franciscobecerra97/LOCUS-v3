# AWS S3 Application Storage Profile

Status: P6.2 implementation complete locally; live AWS validation requires a
separate execution authorization and disposable synthetic research account.

## Boundary

`LOCUS-storage-provider-aws-s3-v1` is a supplemental application-operated AWS
S3 profile. It is not the default reviewer path, a personal user bucket, an
authentication provider, a descriptor trust root, or evidence of independent
cloud administration. Deterministic filesystem and local S3-compatible paths
remain sufficient to reproduce the implementation.

The client authenticates to the LOCUS application boundary using the existing
D004 capability and proof key. It never receives an AWS access key, secret key,
session token, IAM policy, or pre-signed bearer URL. The application gateway
holds an explicitly supplied, prefix-scoped provider credential and executes
one exact admitted operation.

## Implemented operations

`LOCUS-application-storage-gateway-v1` supports:

- immutable encrypted-backup create and exact read, plus exact lifecycle
  deletion;
- immutable descriptor create and exact digest-bound read;
- immutable recovery-bundle create and exact digest/length-bound read; and
- current-pointer exact read and compare-and-swap using
  `LOCUS-storage-pointer-cas-v1`.

The gateway first requires the P3.4 verifier to validate issuer, subject,
backup, epoch, operation, audience, client proof key, nonce, lifetime, request
digest, and derived pseudonymous prefix. The provider backend then independently
checks the exact logical object key and content binding before invoking S3.
Neither layer has a listing operation.

## AWS construction and IAM shape

The AWS provider accepts only explicit application-side configuration:

- bucket and region;
- exact application/subject/backup prefix;
- access key and secret key;
- optional short-lived session token; and
- bounded network timeout.

It supplies no custom endpoint, uses TLS certificate verification, and disables
ambient credential discovery by passing every credential field directly to the
pinned SDK client. Credential values are excluded from provider
representations, request digests, results, errors, and documentation.

`aws_prefix_policy()` produces one TLS-conditioned resource statement for the
exact `arn:aws:s3:::bucket/prefix/*` namespace. It contains only
`s3:GetObject`, `s3:PutObject`, and `s3:DeleteObject`; it grants no bucket or
object listing. An operator may reduce those actions further for a read-only or
publication-only gateway role.

S3 ETags remain opaque concurrency tokens. S3 access control, Versioning, and
Object Lock do not authenticate LOCUS descriptors, establish current-state
freshness, or prove rollback resistance.

## Reproducible validation

Default tests use generated synthetic capabilities, client proof keys, backup
objects, descriptors, bundles, pointers, and a deterministic fake S3 service.
They cover every implemented role, exact retry/read, stale CAS, subject/prefix
isolation, capability replay binding, no-list behavior, provider outage
mapping, TLS properties, session-token forwarding, and credential-safe object
representations.

`prototype/tests/test_aws_s3_live.py` is deliberately skipped unless all of the
following are set by an explicitly authorized operator:

- `LOCUS_RUN_AWS_S3_TEST=1`;
- `LOCUS_AWS_S3_TEST_BUCKET`;
- `LOCUS_AWS_S3_TEST_ACCESS_KEY`;
- `LOCUS_AWS_S3_TEST_SECRET_KEY`;
- optional `LOCUS_AWS_S3_TEST_SESSION_TOKEN`;
- `LOCUS_AWS_S3_TEST_REGION`; and
- `LOCUS_AWS_S3_TEST_PREFIX`.

That gate performs only read-only TLS/bucket connectivity. A later real-provider
functional run requires a separately approved disposable prefix, exact cleanup
or lifecycle policy, synthetic material only, privacy-safe aggregate output,
and a new versioned result path. Normal CI, reviewers, and recovery clients
must never require these variables.

## Limitations

The current result does not establish AWS conditional-write behavior, IAM or
account configuration correctness, provider availability, provider-side log or
metadata privacy, regional behavior, independent administration, production
security, or performance. The application operator and AWS may observe the
pseudonymous namespace, exact object keys, sizes, timing, region, and access
patterns. Gateway or issuer compromise can authorize or deny provider
operations but does not make unauthenticated provider bytes valid LOCUS
configuration.
