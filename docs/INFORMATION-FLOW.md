# Information-Flow Contract

This table is the starting contract. Update it before implementing new roles or
retained observations.

Legend:

- `E` — allowed only ephemerally.
- `P` — allowed to persist.
- `F` — forbidden.
- `O` — role may observe as an explicit policy consequence.

| Material | Enrollment client | Backup store | Descriptor store | Resolver | TPASS holder | Authorizer-only | Recovery client |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Raw structured cues | E | F | F | O when used | F | F | E |
| Resolver queries/results | E | F | F | O when used | F | F | E |
| Selected provider IDs | E or F by policy | F | F | O | F | F | E or F |
| Canonical policy output `Z_M` | E | F | F | F | F | F | E |
| TPASS password input `p_M` | E | F | F | F | F | F | E |
| TPASS public parameters | P | P | P | F | P | P if required | P |
| One party's TPASS state | Transient during provisioning | F | F | F | P: own only | F | F |
| Complete TPASS setup states | E only | F | F | F | F | F | F |
| Recovered group secret `S_R` | E | F | F | F | F | F | E |
| Wrapping key `K_wrap` | E | F | F | F | F | F | E |
| Plaintext protected key | E/input | F | F | F | F | F | E/output |
| Encrypted backup | P or transient | P | Locator/digest only | F | Reference/digest only | Reference/digest if required | P or transient |
| Immutable recovery-bundle ZIP | E or P during publication | P in bundle-capable provider | P only when the same provider implements the bundle interface | F | Locator/digest only | Locator/digest if required | E or P during retrieval |
| Bundle manifest | E or P | P with bundle | P with descriptor/bundle | F | Safe digest only if required | Safe digest only if required | E or P |
| Backup identifier/epoch/digest | P | P | P | F | P | P | P |
| Policy identifier/public rules | P | P | P | Policy-dependent | P | P | P |
| Endpoint identities/membership | P | Public as required | P | F | P | P | P |
| Admission credential/token | E | F | F | F | F except validation input | F except validation input | E |
| Short-lived proof-key-bound storage capability | E | F behind gateway | F behind gateway | F | F | F unless separately acting as issuer | E |
| Local audit state | F after request | F | F | F | P: own | P: own | F |
| Descriptor signature/current pointer | P | F unless co-hosted adapter | P | F | P as required | P as required | P |

## Additional rules

- A provider may implement backup and descriptor interfaces in one external
  service, but the logical data contracts remain distinct.
- Under D014, a bundle-capable provider may physically colocate the canonical
  encrypted backup, signed descriptor, and manifest in one immutable bounded
  ZIP. The authenticated mutable current pointer remains outside the ZIP, and
  physical colocation does not permit either logical store to retain prohibited
  material.
- ZIP filenames and manifests contain only registered public names, versions,
  sizes, and digests. They contain no user label, cue, selected record,
  candidate hint, credential, or secret-bearing value.
- Under D015, an application-operated S3 namespace is scoped by the admitted
  subject and backup identifier. AWS S3 is the optional external profile. The
  application operator and provider may observe namespace, object-key, timing,
  size, and access metadata; S3 access control is not the descriptor trust
  root.
- Clients receive no AWS access key and need no personal AWS account. The
  application storage gateway validates short-lived proof-key-bound
  authorization for the exact allowed prefix and operation. Normal recovery
  has no bucket-list permission.
- Public metadata must be reviewed for linkability and enumeration even when it
  is not secret.
- A role may not derive permission to persist a value merely because it observed
  it transiently.
- Logs, telemetry, screenshots, traces, dumps, exception messages, and UI state
  are storage channels and follow the same table.
- Positive controls must prove that audits detect deliberately inserted
  fictional forbidden material.
- Network-flow evidence records categories and byte counts, not payloads.

## Application storage gateway view

The D015 application storage gateway is a stateless protocol adapter within the
cloud-side compromise view. It may transiently observe the proof-key-bound
storage capability, pseudonymous subject scope, backup identifier, epoch,
exact object key, operation, encrypted backup, signed descriptor, current
pointer, manifest, and bundle bytes required for that operation. It may hold a
narrow server-side provider credential for the application namespace.

It must not receive raw or canonical cues, TPASS password input, party state,
recovered group secret, wrapping key, or plaintext private-key material. It
exposes no bucket listing to the client, emits no provider exception text, and
persists no request body, capability, or client proof material in logs or audit
records. Its compromise does not turn provider bytes into authenticated LOCUS
configuration and is included in future cloud-plus-descriptor/bundle snapshot
evidence.

## Clean-client boundary

Client B may receive only the inputs approved in D001--D003 and the eventual
D004 admission decision, such as:

- installed application and pinned trust root;
- admission/identity authentication capability and a short-lived scoped
  storage capability;
- optional recovery receipt or handle;
- authenticated current pointer and immutable recovery bundle;
- user-entered fictional cues;
- fresh session/proof key.

It must not inherit:

- Client A volume or environment;
- coordinator private key from enrollment;
- long-lived or account-wide storage-provider credentials;
- deployment configuration not obtainable through the approved bootstrap;
- raw cues or canonical output;
- protected private key;
- TPASS group secret or wrapping key;
- party secret state.
