# Paper Artifact Release Checklist

Suggested tag: `gasal2-longtarget-paper-v0.1`.

Do not create or push the tag as part of paper preparation. A project owner must
complete and approve every item below first.

- [ ] Confirm author order, affiliations, funding, and contribution statements.
- [ ] Confirm repository and third-party input licenses with the institution.
- [ ] Confirm all 13 external/tracked inputs against `reproduce/input_manifest.tsv`.
- [ ] Attach `paper/source_data/`, tables, figures, captions, and manifests.
- [ ] Archive Phase 2-4 raw artifacts outside Git and publish their manifest mapping.
- [ ] Create citation metadata (`CITATION.cff`) only after author approval.
- [ ] Run `make check-fasim-gasal2-paper-prep` from the release candidate commit.
- [ ] Create a GitHub release and permanent archive; record the DOI after issuance.
- [ ] Verify the archived DOI payload checksum against the release candidate.
- [ ] Create the signed tag only after the permanent archive and license review pass.

Suggested owner-run commands after approval:

```bash
git tag -s gasal2-longtarget-paper-v0.1 <approved-commit>
git push origin gasal2-longtarget-paper-v0.1
```
