# Manuscript Governance

This repository is the integrated continuation of LOCUS. It maintains the
implementation, active technical documentation, manuscript source and rendered
review snapshot, retained versioned evidence, generated manuscript inputs, and
artifact tooling.

Imported material remains bound to its original identifiers and provenance. No
implementation, evidence, or planning change automatically authorizes a
manuscript change. Before every manuscript edit, describe the exact proposed
delta and obtain the owner's explicit approval; the owner may approve or skip
each change.

## Repository-maintained artifacts

This project maintains:

- implementation changes and versioned protocols;
- the authoritative manuscript source, bibliography, and review PDF;
- active threat-model, architecture, and information-flow documentation;
- tests, frozen baseline evidence, and newly versioned aggregate evidence;
- generated paper tables and future figures;
- claim/evidence status; and
- artifact source, release instructions, and sealed historical releases.

## Prohibited assumptions

Implementation progress does not automatically authorize:

- changing a paper title, abstract, thesis, or contribution order;
- promoting an implementation result into a paper claim;
- removing a documented limitation;
- describing a test as a proof;
- describing separate hosts as independent administration;
- describing a UI as usability evidence;
- describing persistent-state deletion as forensic erasure;
- describing local audit records as a global attempt bound.

Every manuscript update must:

1. present the exact proposed text, section, table, figure, or reference delta;
2. identify its implementation/evidence basis and effects on claims and
   limitations;
3. receive an explicit owner decision to approve or skip the change;
4. edit `paper/` only after approval;
5. update the threat model, claim matrix, limitations, related work, generated
   inputs, and artifact instructions as applicable; and
6. rebuild, render, visually inspect, and record the PDF digest/page status.

An owner decision about implementation scope does not implicitly authorize a
narrative change.

D023 therefore authorizes only planning and implementation of the new
integrated reference system and its chronological P8/P9/P10 gates. It does not
authorize a paper statement that the system exists, was evaluated, improves
security or performance, or supports any deployment claim. After the
integrated implementation, mapping review, retained evidence, clean-host
artifact reproduction, and claim-matrix closure are complete, each proposed
system description, result, table, figure, claim, and limitation must still be
presented as an exact manuscript delta for separate owner approval. Any
approved result must identify the evaluated integrated profile; component or
historical evidence may not be relabeled as full-system evidence.
