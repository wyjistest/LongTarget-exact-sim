# GASAL2-LongTarget Phase 2 core paired benchmarks

This report is generated from the Phase 2 machine-readable receipt tables; no timing value is copied from historical prose.

```text
paper_runtime_epoch = 0
paper_runtime_commit = 0d11aa2d61b7ccda59b462ab8e0750dad17ee18f
artifact_root = .paper-artifacts/runtime-epoch-0-pre-freeze/phase2-core
artifact_manifest_sha256 = d6d4bd7b6ffa98f4ae510694816b4d4c906274f92a9121b6dab7adacdec05ce4
bootstrap_interval = deferred_to_phase_5
```

## Paired results

| workload | contract | n | baseline median (s) | candidate median (s) | median speedup | speedup IQR | speedup range | correctness | fallback/OOM |
|---|---|---:|---:|---:|---:|---:|---:|---|---:|
| c1_h19_chr21_chr22_fast_topk | fast_topk_score_stability_nt | 5 | 2377.197162 | 61.841816 | 38.320882x | 38.317023-38.555819 | 38.200466-38.599922 | top5=1 | 0/0 |
| c4_h19_chr21_two_slot | fast_topk_score_stability_nt | 5 | 63.000340 | 55.083558 | 1.143132x | 1.142957-1.144917 | 1.140845-1.157663 | top5=1 | 0/0 |
| c4_h19_chr22_two_slot | fast_topk_score_stability_nt | 5 | 62.340776 | 54.170906 | 1.151205x | 1.147962-1.156241 | 1.147547-1.158090 | top5=1 | 0/0 |
| c7_kcnq_max8_chr22 | shifted_grid_bounded_full_rows | 3 | 1021.717526 | 938.724094 | 1.087369x | 1.086293-1.087890 | 1.085216-1.088411 | top5=1; byte=1 | 0/0 |

The `fast_topk_score_stability_nt` rows require equality of score-, stability-, and Nt-ranked clustered TFO1-5. Diagnostic row-set drift is not promoted to a full-output requirement. The bounded max8 row additionally requires byte-identical materialized output and zero missing/extra rows.

## Failure inventory

retained failure/mismatch artifacts: 11

failure reasons: pair_comparator_failure=1; superseded_derived_pair=10

Technical comparator failures and superseded mismatch receipts remain in `core_benchmark_failures_pre_freeze.tsv`. A parser or relocated-path repair creates a new derived comparator receipt; it never edits the failed receipt or raw run artifact.

## Descriptive operating envelope

| workload | contract | n | status | speedup | fallback | source class |
|---|---|---:|---|---:|---:|---|
| chr1_full | equivalence_first_full_output | 1 | pass | 1.094x | 0 | committed_historical_artifact |
| chr22_full | equivalence_first_full_output | 1 | pass | 0.993x | 0 | committed_historical_artifact |
| h19_short_integrated | segmented_archive_first_exact_scoreinfo_v1 | 1 | pass | 1.074793x | 0 | committed_historical_artifact |
| malat1_first8 | long_query_boundary | 1 | fail | 0.702x | 3091 | committed_historical_artifact |
| neat1_first64 | long_query_boundary | 1 | fallback | 1.009x | 0 | committed_historical_artifact |

These are one-run historical descriptive rows from the digest-verified tracked workload matrix. They receive no Phase 2 bootstrap claim and are not pooled with current-epoch pairs.

## Scope

The C1 result supersedes the historical single-pair 40.119136x starting value for paper reporting. Historical and Phase 2 samples are not pooled. C4 is limited to one worker per GPU. C7 is the preregistered bounded max8 dual-grid workload; full 121-segment KCNQ1OT1 and full hg38 were not run.

Machine-readable authority:

- `paper/source_data/core_benchmark_runs_pre_freeze.tsv`
- `paper/source_data/core_benchmark_pairs_pre_freeze.tsv`
- `paper/source_data/core_benchmark_failures_pre_freeze.tsv`
- `paper/source_data/core_benchmark_summary_pre_freeze.tsv`
- `paper/source_data/core_operating_envelope_pre_freeze.tsv`
- `paper/phase2_artifact_manifest.tsv`
