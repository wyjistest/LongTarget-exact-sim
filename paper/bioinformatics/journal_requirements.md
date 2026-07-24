# Bioinformatics Application Note Requirements Check

```text
checked_at = 2026-07-24
requirements_rechecked = 1
direct_access_status = Cloudflare security challenge
live_content_comparison = blocked
working_article_type = Application Note
```

## Official pages

The current official entry points checked on 2026-07-24 were:

1. **Instructions for Authors**:
   <https://academic.oup.com/bioinformatics/pages/instructions_for_authors>
2. **Scope Guidelines**:
   <https://academic.oup.com/bioinformatics/pages/scope_guidelines>
3. **Submission Online**:
   <https://academic.oup.com/bioinformatics/pages/submission_online>

Both direct HTTP retrieval and a JavaScript-enabled Firefox session were
attempted. The site returned a Cloudflare managed security challenge instead
of the page body. This file therefore separates the conservative working
requirements already frozen in the owner-provided execution specification
from exact live-page details that still require an owner browser check. Gap
`G10_journal_live_verification` records that boundary.

## Working requirements

These constraints are treated as hard upper bounds until the live pages can be
read and compared:

| Topic | Working requirement | Submission consequence |
| --- | --- | --- |
| Article type | Application Note | The manuscript must present usable software and a real application, not only an engineering benchmark. |
| Length | No more than 4 pages; approximately 2,600 words without a main figure, or approximately 2,000 words with one main figure | Phase 7 targets the 2,000-word, one-main-figure form. References and exact exclusions from the word count require live confirmation. |
| Availability and Implementation | Include an explicit Availability and Implementation statement with software and data access | Repository, release payload, source data, checksums and owner-controlled archive/DOI status must be stated without invented public identifiers. |
| Scope: speed improvement | A speed improvement is editorially meaningful only when it materially expands the method's practical application range | The real batch application must meet the preregistered widening gate; a core H19 speedup alone is insufficient. |
| Scope: validation | New software should be evaluated on real biological data and positioned against state-of-the-art methods | Phase 3 supplies real biological inputs and Phase 4 runs Fasim authority plus at least one current external triplex tool. Tool-native outputs remain semantically separate. |
| Main figure | One main figure is budgeted | All numeric panels must be generated from frozen machine-readable source data. |
| figure resolution | Vector PDF/SVG remains authoritative; the current raster deliverables are 600 dpi | Exact official line-art, halftone and combination-art minima remain part of the live-page owner check; no lower-resolution asset will be promoted meanwhile. |
| initial submission | A single internally consistent Application Note manuscript and separately identified supporting files are required by this track | Exact upload formats, anonymization choices and portal fields remain unconfirmed while the Submission Online page is blocked. |
| Supplementary | Supplementary material may hold contract matrices, mismatch details, protocols and extended tables, but cannot repair a missing main-text claim gate | Supplementary files must be cited from the manuscript, frozen with the release payload and checked for machine-readable provenance. |

## Comparison with the execution baseline

No difference identified in the evidence accessible during this run. This is
not a claim that the live text was retrieved: page-body comparison was blocked
by Cloudflare, so exact current wording, figure-resolution categories, initial
submission file rules and Supplementary upload rules must be checked in a
normal owner browser before Phase 7 is finalized.

The implementation remains governed by the stricter interpretation whenever
the working baseline and a later live-page reading differ. Any Difference
identified later must update this file, the gap register and the manuscript
gate before submission readiness can pass.
