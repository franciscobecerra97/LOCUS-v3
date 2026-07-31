# Manuscript-Specific Instructions

Root `AGENTS.md` remains authoritative. These rules add protection for
`paper/`.

- `main.tex` is the authoritative manuscript source.
- `main.pdf` is the intentional rendered review snapshot.
- Do not edit manuscript narrative, claims, contribution ordering, limitations,
  tables, figures, or references until the owner has reviewed the exact
  proposed delta and explicitly approved it.
- Approval of implementation or evidence work does not imply approval of paper
  wording.
- Never hand-edit manifest-bound generated rows. Regenerate them from the exact
  validated evidence profile.
- Do not promote a new result until the claim/evidence matrix identifies its
  profile, assumptions, evidence, and limitations.
- Verify every newly cited source before adding it. Do not promote unverified
  material from `related_work.tex`.
- After an approved edit, rebuild the PDF, render and visually inspect every
  page, check page limits and anonymity, and record the resulting digest and
  build status.
- Keep LaTeX byproducts untracked. Track `main.pdf` only as the deliberate
  review snapshot.
