# LOCUS Manuscript Reference Audit

Status: cited-source metadata audit completed 2026-07-28 for the current
`paper/main.tex`. This file does not approve uncited entries remaining in
`paper/references.bib`.

## Method

- Extract every citation key used by `paper/main.tex`.
- Require one matching BibTeX entry for each key.
- Verify DOI records against Crossref metadata and standards against the RFC
  Editor.
- Verify the closest-system metadata and mechanism-level comparison against
  primary publisher/project pages and papers.
- Correct author, title, year, venue, page, DOI, or URL mismatches in
  `paper/references.bib`.
- Treat an uncited BibTeX entry as outside this completed audit. Uncited entries
  should be removed or separately verified before an anonymous source release.

## Audited Cited Set

| Key | Authoritative identifier or source | Result |
| --- | --- | --- |
| `AlAmeen2015Cues` | USENIX SOUPS 2015 paper page and local paper | Metadata and one-week study scope matched |
| `AlAmeen2017GeoPass` | DOI `10.1093/iwc/iww033` and local paper | Metadata, 66-day field-study, and interference-study scope matched |
| `AVSS2002` | DOI `10.1145/586110.586124` | Metadata matched |
| `Bagherzandi2011PPSS` | DOI `10.1145/2046707.2046758` | Metadata matched |
| `Biddle2012Graphical` | DOI `10.1145/2333112.2333114` | Metadata matched |
| `Bonneau2015Secrets` | DOI `10.1145/2736277.2741691` | Metadata matched |
| `Camenisch2014Memento` | DOI `10.1007/978-3-662-44381-1_15` | Metadata matched |
| `CRSA2021` | DOI `10.1109/TIFS.2021.3104142` | Corrected author `Deqing Zou` |
| `DAppRecovery2019` | DOI `10.1109/Blockchain.2019.00028` | Metadata matched |
| `Feldman1987` | DOI `10.1109/SFCS.1987.4` | Metadata matched |
| `FuzzyCommitment1999` | DOI `10.1145/319709.319714` | Metadata matched |
| `FuzzyExtractors2004` | DOI `10.1145/1030083.1030096` | Metadata matched |
| `HKDF2010` | RFC 5869; DOI `10.17487/RFC5869` | Metadata matched |
| `Hang2015LocationFallback` | USENIX SOUPS 2015 paper page | Metadata and six-month fallback-study scope matched |
| `Jarecki2014PPSS` | DOI `10.1007/978-3-662-45608-8_13` | Metadata matched |
| `PPKR2024` | DOI `10.1145/3658644.3690358`; ETH published-version record | Metadata and mechanism scope matched |
| `PPSS2016` | DOI `10.1109/EuroSP.2016.30` | Metadata matched |
| `PVSS1999` | DOI `10.1007/3-540-48405-1_10` | Metadata matched |
| `RFC5116AEAD` | RFC 5116; DOI `10.17487/RFC5116` | Metadata and AEAD/nonce scope matched |
| `SafetyPin2020` | USENIX OSDI 2020 paper page and paper | Added verified entry; mechanism comparison checked |
| `Shamir1979` | DOI `10.1145/359168.359176` | Metadata matched |
| `SocialWallet2023` | DOI `10.1145/3564746.3587016` | Metadata matched |
| `SVR3_2024` | USENIX OSDI 2024 paper page and paper | Added verified entry; mechanism comparison checked |
| `WhatsAppBackup2023` | DOI `10.1007/978-3-031-38551-3_11` | Metadata matched |
| `Yan2004Password` | DOI `10.1109/MSP.2004.81` | Metadata matched |
| `Yi2015TPASS` | DOI `10.1007/978-3-319-24174-6_18` | Metadata matched |
| `Yi2019TPASS` | DOI `10.1016/j.jpdc.2019.01.013`; Warwick accepted manuscript and local article | Corrected author `Xuechao Yang`; construction scope matched |
| `Zhou2025MapPasswords` | DOI `10.1109/TDSC.2025.3549028` and local paper | Metadata, tolerant-distance, and two-week study scope matched |

## Closest-System Claim Check

- SafetyPin is an encrypted mobile-backup system using a short PIN and a
  distributed HSM fleet with hardware-backed brute-force defenses. LOCUS must
  not claim to be the first distributed or attempt-controlled
  offline-guessing-resistant backup system.
- SVR3 distributes recovery across heterogeneous enclaves and cloud providers
  and includes explicit rollback-protection and fault-tolerance mechanisms with
  deployed-scale evidence. LOCUS must not imply comparable rollback, scale, or
  independent-administration evidence.
- PPKR and the WhatsApp backup analysis cover password-bootstrapped high-entropy
  key retrieval under explicit server/HSM assumptions. LOCUS's narrower delta
  is its native TPASS composition, versioned cue-policy boundary, role
  separation, and bounded snapshot evidence.
- Yi et al. supply the TPASS construction. LOCUS implements and maps their
  zero-knowledge variant; TPASS itself is inherited, not a LOCUS contribution.

## Remaining Bibliography Hygiene

`paper/references.bib` still contains entries not cited by `paper/main.tex`.
BibTeX excludes them from the compiled bibliography, but the anonymous source
artifact should not ship unverified surplus references. Before M5 packaging,
either verify each remaining entry under the same procedure or remove it from
the anonymous bibliography without changing the audited cited set.
