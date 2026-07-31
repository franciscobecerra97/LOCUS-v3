# LOCUS In-Process Educational Walkthrough

Status: optional synthetic-only teaching interface, 2026-07-28.

## Purpose

The walkthrough makes the paper-facing cue mapping and native TPASS recovery
sequence observable without creating a deployment or exposing protocol
secrets. It is an educational interface, not a new experiment, retained
evidence source, production enrollment service, or usability study.

Run it from the repository root:

```console
uv run --frozen python tasks.py walkthrough
```

The walkthrough accepts only numbered selections from a built-in fictional
catalog. It never asks for free-form names, locations, contacts, credentials,
private keys, or other personal data. A fresh 32-byte test key and all
cryptographic material exist only in process memory and are not written to
disk.

## Walkthrough stages

1. **Selection:** choose exactly three distinct fictional location-person pair
   aliases. The underlying synthetic records are not printed.
2. **Canonicalization:** apply the exact
   `LOCUS-location-person-set-v1` three-pair policy used by the retained
   deployment.
3. **Enrollment:** run the native Ristretto255 2-of-3 TPASS setup, encrypt a
   generated test key using the deployed v4 backup format, and retain one
   logical holder record per TPASS holder.
4. **Client reset:** discard the plaintext test key. The walkthrough retains
   only its one-way verification digest so that a later successful result can
   be checked without keeping the original key.
5. **Recovery:** choose three fictional pair aliases and any two of the three
   TPASS holders. The attempt is counted before native commitment generation.
   Correct selections restore and authenticate the generated test key; other
   selections return only `generic-rejection`.
6. **Retry:** optionally retry until success, cancellation, or exhaustion of
   the three-attempt educational budget.

Normal output contains only fictional display aliases, counts, versions, byte
sizes, selected holder numbers, and generic outcomes. It does not contain the
underlying synthetic records, canonical recovery bytes, TPASS input, blinders,
holder records, commitments, response shares, group secret, wrapping key,
ciphertext, or generated test key.

## Evidence and security boundary

The walkthrough uses the exact cue canonicalizer, deployed v4 backup format,
HKDF/AES-256-GCM composition, and native Ristretto255 TPASS phases. All roles
are nevertheless logical objects inside one process:

- there is no resolver or cloud network service;
- there are no HTTPS party processes or mutually authenticated identities;
- the attempt counter is in-memory and is not the signed durable ledger;
- no filesystem/S3 separation or independent administration is demonstrated;
- no state survives process exit;
- Python/runtime memory zeroization is not demonstrated; and
- output success is not evidence about human cue memorability or usability.

Use `tasks.py deployment-demo` or `tasks.py deployment-smoke` for the isolated
same-host service topology. Use only the registered experiment commands and
immutable v2 corpus for paper evidence.
