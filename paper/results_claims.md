# Results Claim Source Sheet

Generated from `paper/claim_evidence.tsv` under data freeze
`paper-data-v1-dccfd49-20260716`. This is structured source material,
not manuscript prose.

## C1

- claim_id: `C1`
- one-sentence result: Under the checked short-query fast top-K contract and hardware scope, GASAL2 reduced wall time with a median paired speedup of 38.32x (bootstrap 95% CI 38.20-38.60x).
- scope: `fast_topk_score_stability_nt`; workloads `c1_h19_chr21_chr22_fast_topk`.
- n: `5`; required repeats `5_valid_pairs`.
- point estimate: `median_paired_speedup=38.320882`.
- interval or range: `bootstrap95=38.200466-38.599922`.
- correctness: `5_of_5_pairs_clean;three_top5_equal;fallbacks=0`.
- figure/table: Figures 1D and 2; Tables 1 and 2.
- source data: `paper/source_data/paired_speedup_summary.tsv` filtered by `workload_id=c1_h19_chr21_chr22_fast_topk`.
- allowed wording: Under the checked short-query fast top-K contract and hardware scope, GASAL2 reduced wall time with a median paired speedup of 38.32x (bootstrap 95% CI 38.20-38.60x).
- forbidden extrapolation: Limited to the checked H19 chr21+chr22 fast top-K contract and recorded hardware.

## C2

- claim_id: `C2`
- one-sentence result: The preregistered non-H19 panel supports generalization beyond H19, with 10 of 13 supported-query workloads contract-clean; three mismatch workloads are reported without exclusion.
- scope: `fast_topk_score_stability_nt`; workloads `generalization_core;generalization_breadth;full_length_guards`.
- n: `13`; required repeats `3_per_core;1_per_breadth`.
- point estimate: `10_of_13_supported_workloads_clean;24_of_31_pairs_clean;clean_workload_median_speedup=17.247141`.
- interval or range: `clean_workload_speedup_range=11.924442-23.044489`.
- correctness: `10_of_13_workloads_clean;3_mismatch_workloads_retained;fallbacks=0;OOM=0`.
- figure/table: Figure 2; Tables 2 and 3.
- source data: `paper/source_data/generalization.tsv` filtered by `row_type=supported_query`.
- allowed wording: The preregistered non-H19 panel supports generalization beyond H19, with 10 of 13 supported-query workloads contract-clean; three mismatch workloads are reported without exclusion.
- forbidden extrapolation: Three repeat-consistent mismatch workloads are retained; eligibility remains workload-contract checked.

## C3

- claim_id: `C3`
- one-sentence result: Correctness was evaluated separately for score-, stability-, and Nt-ranked clustered TFO1-5, with unsupported full-length inputs rejected before GPU execution.
- scope: `fast_topk_score_stability_nt;full_tfosorted_rowset;preflight_guard_only`; workloads `core;generalization;negative_controls`.
- n: `64`; required repeats `all_preregistered_runs`.
- point estimate: `54_of_61_paired_comparisons_clean;3_of_3_full_length_guards_fail_closed`.
- interval or range: `paired_clean_fraction=0.885246;guard_range=3_of_3`.
- correctness: `54_of_61_pairs_clean;7_mismatch_pairs_retained;3_of_3_guards_fail_closed;fallbacks=0;OOM=0`.
- figure/table: Figure 2; Table 3.
- source data: `paper/source_data/correctness.tsv` filtered by `row_type in {paired_contract,preflight_guard}`.
- allowed wording: Correctness was evaluated separately for score-, stability-, and Nt-ranked clustered TFO1-5, with unsupported full-length inputs rejected before GPU execution.
- forbidden extrapolation: Fast top-K equality is not full-row equality; seven mismatch pairs remain visible.

## C4

- claim_id: `C4`
- one-sentence result: At one worker per GPU, bounded two-slot scheduling produced median paired speedups of 1.143x on chr21 and 1.151x on chr22 relative to the synchronous preset.
- scope: `fast_topk_score_stability_nt`; workloads `c4_h19_chr21_two_slot;c4_h19_chr22_two_slot`.
- n: `10`; required repeats `5_valid_pairs_each`.
- point estimate: `chr21_median=1.143132;chr22_median=1.151205`.
- interval or range: `chr21_bootstrap95=1.140845-1.157663;chr22_bootstrap95=1.147547-1.158090`.
- correctness: `10_of_10_pairs_clean;three_top5_equal;fallbacks=0`.
- figure/table: Figure 3; Tables 2 and 4.
- source data: `paper/source_data/paired_speedup_summary.tsv` filtered by `workload_id in {c4_h19_chr21_two_slot,c4_h19_chr22_two_slot}`.
- allowed wording: At one worker per GPU, bounded two-slot scheduling produced median paired speedups of 1.143x on chr21 and 1.151x on chr22 relative to the synchronous preset.
- forbidden extrapolation: Evidence is limited to one worker per GPU; high-density configurations are not recommended.

## C5

- claim_id: `C5`
- one-sentence result: Archive-first output restored byte-identical results while reducing stored bytes 5.72-fold; bounded SQLite merge reduced median peak RSS by 33.62% at additional wall-time cost.
- scope: `archive_restore_only;shifted_grid_bounded_full_rows`; workloads `archive_small;archive_large_synthetic;kcnq1ot1_max8`.
- n: `6`; required repeats `3_merge_repetitions_large`.
- point estimate: `storage_ratio=5.715078;run_plus_restore_ratio_of_median_walls=1.195362;median_merge_rss_reduction=0.336190`.
- interval or range: `storage_ratio_range=5.715078-5.715078;merge_rss_reduction_range=0.332421-0.341258`.
- correctness: `6_of_6_pairs_byte_equal`.
- figure/table: Figure S1; Table 4.
- source data: `paper/source_data/archive_first.tsv` filtered by `row_type in {archive_restore,bounded_exact_merge}`.
- allowed wording: Archive-first output restored byte-identical results while reducing stored bytes 5.72-fold; bounded SQLite merge reduced median peak RSS by 33.62% at additional wall-time cost.
- forbidden extrapolation: SQLite exact merge reduces memory but is slower; storage reduction is not compute acceleration.

## C6

- claim_id: `C6`
- one-sentence result: The exact-column optimization improved the stage by 1.35x on H19 and 1.65x on the KCNQ1OT1 segment, corresponding to 1.08x and 1.12x end-to-end speedups.
- scope: `full_tfosorted_rowset`; workloads `exact_column_kcnq1ot1_segment;exact_column_h19_control`.
- n: `6`; required repeats `3_compatible_pairs`.
- point estimate: `h19_stage=1.348059_e2e=1.082711;kcnq_stage=1.651694_e2e=1.115307`.
- interval or range: `h19_e2e_bootstrap95=1.055717-1.086287_stage_range=1.343799-1.379978;kcnq_e2e_bootstrap95=1.102467-1.125012_stage_range=1.624119-1.658582`.
- correctness: `6_of_6_pairs_full_output_equal;fallbacks=0;overflow=0`.
- figure/table: Figure 3; Table 4.
- source data: `paper/source_data/ablation.tsv` filtered by `workload_id in {c6_exact_h19_2mb,c6_exact_kcnq_segment_chr22}`.
- allowed wording: The exact-column optimization improved the stage by 1.35x on H19 and 1.65x on the KCNQ1OT1 segment, corresponding to 1.08x and 1.12x end-to-end speedups.
- forbidden extrapolation: Component-stage speedup must not be presented as the end-to-end speedup.

## C7

- claim_id: `C7`
- one-sentence result: Strong gains are concentrated in short-query fast top-K; full output is near parity and bounded max8 long-query execution reached 1.087x without meeting the promotion gate.
- scope: `full_tfosorted_rowset;shifted_grid_bounded_full_rows;preflight_guard_only`; workloads `chr22_full;chr1_full;c7_kcnq_max8_chr22;long_query_guards`.
- n: `3`; required repeats `3_valid_max8_pairs`.
- point estimate: `max8_median_paired_speedup=1.087369;chr1_full_descriptive=1.094;chr22_full_descriptive=0.993`.
- interval or range: `max8_bootstrap95=1.085216-1.088411`.
- correctness: `3_of_3_max8_pairs_full_output_and_top5_clean;fallbacks=0;OOM=0`.
- figure/table: Figure 4; Supplementary operating-envelope table.
- source data: `paper/source_data/operating_envelope.tsv` filtered by `workload_id=c7_kcnq_max8_chr22 for repeated estimate;historical rows descriptive only`.
- allowed wording: Strong gains are concentrated in short-query fast top-K; full output is near parity and bounded max8 long-query execution reached 1.087x without meeting the promotion gate.
- forbidden extrapolation: Full transcript and full hg38 were not run; historical full-output rows are descriptive n=1.
