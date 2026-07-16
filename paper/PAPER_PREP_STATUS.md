# GASAL2-LongTarget Paper Preparation Status

## Final Decision

```text
paper_preparation_ready_with_declared_limitations
```

The scoped short-query fast top-K paper package is ready for author-led drafting.
This decision does not promote a runtime default or expand the long-query claim.

## Frozen Authority

```text
paper_runtime_epoch = 0
paper_runtime_commit = 0d11aa2d61b7ccda59b462ab8e0750dad17ee18f
data_freeze_id = paper-data-v1-dccfd49-20260716
aggregate_check = make check-fasim-gasal2-paper-prep
```

## Primary Claims

- C1: five clean H19 chr21+chr22 fast top-K pairs; median paired speedup
  38.320882x, bootstrap 95% CI 38.200466-38.599922x.
- C2: 10 of 13 preregistered supported-query workloads are contract-clean;
  three repeat-consistent mismatch workloads remain reported.
- C3: 54 of 61 paired comparisons are clean, seven mismatch pairs remain
  visible, and all three full-length guards fail closed before GPU execution.
- C4: one-worker-per-GPU two-slot medians are 1.143132x on chr21 and
  1.151205x on chr22; all ten pairs are clean.
- C5: archive-first storage reduction is 5.715078-fold with byte-identical
  restore; bounded SQLite merge reduces median peak RSS by 0.336190 at
  additional wall-time cost.
- C6: exact-column stage medians are 1.348059x on H19 and 1.651694x on the
  KCNQ1OT1 segment; end-to-end medians are 1.082711x and 1.115307x.
- C7: bounded max8 median paired speedup is 1.087369x and remains below the
  promotion gate; historical full-output rows are descriptive and near parity.

The generated wording and exact source filters are in
`paper/results_claims.md`; the independent arithmetic receipt is
`paper/independent_arithmetic_audit.tsv`.

## Completion Audit

`paper/completion_audit.tsv` maps all ten phase gates and all 25 final
`goal-final.md` checklist items to authoritative evidence and executable Make
verifiers. All 35 rows are `pass`; the aggregate gate rejects missing evidence,
unknown verifier targets, unchecked final items, or a non-clean audit status.

## Correctness Summary

- Score-, stability-, and Nt-ranked clustered TFO1-TFO5 are separate gates.
- Fast top-K equality is not interpreted as full TFOsorted row-set equality.
- All mismatch, guard, fallback, OOM and exclusion rows remain represented.
- Frozen counts: 167 benchmark runs, 61 paired comparisons, 54 clean pairs,
  seven mismatch pairs and 64 correctness rows.

## Figure And Table Inventory

- Five figure sets, each as SVG, PDF and direct 600 DPI PNG.
- Four table bundles, each as TSV, Markdown and LaTeX.
- One supplementary operating-envelope TSV and complete captions.
- Thirty generated files covered by `paper/figures/render_manifest.tsv`.

## Reproduction Status

- Staged-tree clean-checkout quick reproduction passes without GPU benchmarks.
- Frozen source-data checksums, 21 paired summaries, figures and tables rebuild
  byte-for-byte.
- Thirteen unique inputs have authority, license note, size, SHA-256, workload
  mapping and reconstruction command.
- Phase 2-4 raw artifacts are locally retained under `.paper-artifacts/` and
  covered by 3,725 manifest rows; public archive publication is pending.
- GPU and bounded max8 rerun commands are explicit and separate from quick
  reproduction.

## Declared Limitations

- One primary RTX 4090 generation; no second GPU architecture.
- Checked short-query boundary is `query_len <= 2812`.
- Three generalization workloads retain clustered stability or Nt mismatch.
- No same-workload authority/synchronous/two-slot A/B/C triad is constructed.
- One worker per 24 GB GPU is the supported density; high-density OOM evidence
  remains visible.
- Full 121-segment KCNQ1OT1 and full hg38 were not run.
- The long-query architecture remains a documented no-go under the checked
  promotion contract.
- Public raw-artifact archive and permanent DOI are not yet issued.
- No biological superiority claim is supported by this computational study.

## Remaining Author-Only Tasks

- Approve title, author order, affiliations, ORCIDs, contributions and funding.
- Select the journal and adapt formatting/reporting requirements.
- Review narrative wording against `paper/results_claims.md` and
  `paper/limitations.md`.
- Approve third-party input and artifact redistribution licenses.
- Publish the raw artifact archive, create the permanent DOI and add approved
  citation metadata for this software.

## Release Status

No release, DOI or tag was created automatically. The suggested
`gasal2-longtarget-paper-v0.1` tag remains owner-controlled under
`paper/RELEASE_CHECKLIST.md`.
