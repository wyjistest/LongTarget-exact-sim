# Owner Metadata Needed

Codex must not infer, approve or publish any item in this file. Values remain
owner-controlled until explicitly supplied and reviewed.

| Field | Current value | Required owner action |
| --- | --- | --- |
| Author order | `[OWNER REQUIRED]` | Supply and approve the complete ordered author list. |
| Affiliations | `[OWNER REQUIRED]` | Map each author to approved institutional affiliations. |
| ORCIDs | `[OWNER REQUIRED]` | Supply verified ORCIDs or explicitly decline where the journal permits. |
| Funding | `[OWNER REQUIRED]` | Supply funder names and grant identifiers exactly as awarded. |
| CRediT roles | `[OWNER REQUIRED]` | Approve contributor roles for every author. |
| Corresponding author | `[OWNER REQUIRED]` | Identify the corresponding author and approved contact details. |
| Third-party redistribution | `[OWNER REQUIRED]` | Approve licenses and redistribution terms for software, references, annotations, inputs and external-tool artifacts. |
| Final software version | `[OWNER REQUIRED]` | Choose the public release version after the release-candidate audit. |
| Public DOI | `[OWNER REQUIRED AFTER DEPOSIT]` | Create the archive and provide the DOI only after it resolves to the checksum-verified payload. |
| Signed release tag | `[OWNER REQUIRED AFTER ARCHIVE]` | Create and push the signed tag only after license and archive approval. |
| Submission-system answers | `[OWNER REQUIRED]` | Complete article type, declarations, conflicts, data availability, reviewer and portal questions. |

## Additional approvals

- Approve the title, abstract, cover letter and all claim language.
- Verify the live Bioinformatics official pages in a normal browser and resolve
  `G10_journal_live_verification`.
- Approve public repository visibility and the exact archive payload.
- Confirm whether a genuinely different GPU architecture is available for the
  optional Phase 6 study.

Templates and validators may be generated before these values exist, but no
placeholder may be presented as submission-ready metadata.
