# Fasim SIM-Close Score-Landscape Detector Shadow

Base branch:

```text
fasim-sim-recovery-real-corpus-validation-matrix
```

This report characterizes the default-off `FASIM_SIM_RECOVERY=1` SIM-close harness on external FASTA cases. It adds no new recovery logic and does not change scoring, threshold, non-overlap, GPU, filter, or default fast-mode behavior.

`SIM-close wall seconds` measures the side recovery/merge path after the fast Fasim output is available. The end-to-end SIM-close harness cost is reported separately as fast seconds plus SIM-close wall seconds.

| Setting | Value |
| --- | --- |
| cases | 2 |
| repeat | 1 |
| fast_mode | default Fasim on the same FASTA |
| sim_close_mode | FASIM_SIM_RECOVERY=1 side-output harness |
| validate_mode | post-hoc legacy SIM only for validate cases |
| coverage_report | yes |
| miss_taxonomy_report | yes |
| recall_repair_shadow | no |
| validation_matrix_report | no |
| score_landscape_detector_shadow | yes |

## Case Summary

| Case | Validated | Validate supported | Validate supported records | validate_unsupported_reason | Fast digest | SIM-close digest | Validate digest | Fast records | SIM records | SIM-close records | Shared records | SIM-only records | SIM-close extra records | Boxes | Cells | Cell fraction | Recovered candidates | Accepted | Suppressed | Recall vs SIM | Precision vs SIM | Extra vs SIM | Overlap conflicts | Fallbacks |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| human_lnc_atlas_17kb_target | yes | no | 0 | no_legacy_sim_records | sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 | sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 | sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 | 0 | 0 | 0 | 0 | 0 | NA | 0 | 0 | 0.000000 | 0 | 0 | 0 | NA | NA | NA | 0 | 0 |
| human_lnc_atlas_508kb_target | yes | yes | 40 | supported | sha256:25469e60179a524dd712d7ef69ee0c8e379a17f8472be3c2843cd14eda04d221 | sha256:20c37af91408ed5604de79a33ceb0ec470f954f39ab9103f31d07499f22810c9 | sha256:20c37af91408ed5604de79a33ceb0ec470f954f39ab9103f31d07499f22810c9 | 34 | 40 | 14 | 14 | 31 | 0 | 34 | 501250 | 0.064813 | 30 | 14 | 34 | 35.000000 | 100.000000 | 0 | 0 | 0 |

## Run Summary

| Case | Run | Fast seconds | Fast digest | SIM-close digest | Validate digest | Validate supported | Validate supported records | validate_unsupported_reason | SIM records | Output records | Shared records | SIM-only records | SIM-close extra records | Boxes | Cells | Executor seconds | SIM-close wall seconds | Validate wall seconds |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| human_lnc_atlas_17kb_target | 1 | 0.060906 | sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 | sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 | sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 | 0 | 0 | no_legacy_sim_records | 0 | 0 | 0 | 0 | NA | 0 | 0 | 0.000122 | 0.000658 | 2.592778 |
| human_lnc_atlas_508kb_target | 1 | 1.190070 | sha256:25469e60179a524dd712d7ef69ee0c8e379a17f8472be3c2843cd14eda04d221 | sha256:20c37af91408ed5604de79a33ceb0ec470f954f39ab9103f31d07499f22810c9 | sha256:20c37af91408ed5604de79a33ceb0ec470f954f39ab9103f31d07499f22810c9 | 1 | 40 | supported | 40 | 14 | 14 | 31 | 0 | 34 | 501250 | 0.969281 | 1.026303 | 77.421545 |

## Miss Taxonomy

| Case | Run | Enabled | SIM records | Shared records | Missed records | Not box covered | Box covered executor missing | Guard rejected | Replacement suppressed | Canonicalization mismatches | Metric ambiguity records | validate_unsupported_reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| human_lnc_atlas_17kb_target | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | no_legacy_sim_records |
| human_lnc_atlas_508kb_target | 1 | 1 | 40 | 14 | 26 | 10 | 0 | 16 | 0 | 0 | 0 | supported |

Metric consistency note:

`SIM-only records` in the coverage tables are legacy SIM records not matched by the default Fasim fast-mode output. `Missed records` in this taxonomy are legacy SIM records not matched by the SIM-close side output. These are different comparisons, so `shared_records + sim_only_records` is not expected to equal `sim_records`.

SIM labels are used only after SIM-close selection to assign diagnostic miss buckets. They do not influence risk boxes, local SIM execution, guard selection, replacement, or output ordering.

## Score-Landscape Detector Shadow

| Case | Strategy | Boxes | Cells | Cell fraction | Shared | Missed | Not box covered | Guard rejected | Recall | Precision | Extra | Conflicts | Output mutations |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| human_lnc_atlas_17kb_target | baseline_current | 0 | 0 | 0.000000 | 0 | 0 | 0 | 0 | 0.000000 | 0.000000 | 0 | 0 | 0 |
| human_lnc_atlas_17kb_target | score_peak_box_expansion | 0 | 0 | 0.000000 | 0 | 0 | 0 | 0 | 0.000000 | 0.000000 | 0 | 0 | 0 |
| human_lnc_atlas_17kb_target | near_threshold_peak_detector | 0 | 0 | 0.000000 | 0 | 0 | 0 | 0 | 0.000000 | 0.000000 | 0 | 0 | 0 |
| human_lnc_atlas_17kb_target | long_hit_internal_peak_detector | 0 | 0 | 0.000000 | 0 | 0 | 0 | 0 | 0.000000 | 0.000000 | 0 | 0 | 0 |
| human_lnc_atlas_17kb_target | overlap_density_detector | 0 | 0 | 0.000000 | 0 | 0 | 0 | 0 | 0.000000 | 0.000000 | 0 | 0 | 0 |
| human_lnc_atlas_17kb_target | combined_score_landscape_detector | 0 | 0 | 0.000000 | 0 | 0 | 0 | 0 | 0.000000 | 0.000000 | 0 | 0 | 0 |
| human_lnc_atlas_17kb_target | combined_detector_current_guard | 0 | 0 | 0.000000 | 0 | 0 | 0 | 0 | 0.000000 | 0.000000 | 0 | 0 | 0 |
| human_lnc_atlas_17kb_target | combined_detector_relaxed_guard | 0 | 0 | 0.000000 | 0 | 0 | 0 | 0 | 0.000000 | 0.000000 | 0 | 0 | 0 |
| human_lnc_atlas_508kb_target | baseline_current | 34 | 501250 | 0.064813 | 14 | 26 | 10 | 16 | 35.000000 | 100.000000 | 0 | 0 | 0 |
| human_lnc_atlas_508kb_target | score_peak_box_expansion | 34 | 2113538 | 0.273286 | 14 | 26 | 10 | 16 | 35.000000 | 100.000000 | 0 | 0 | 0 |
| human_lnc_atlas_508kb_target | near_threshold_peak_detector | 3 | 580935 | 0.075116 | 8 | 32 | 18 | 2 | 20.000000 | 25.806452 | 23 | 0 | 0 |
| human_lnc_atlas_508kb_target | long_hit_internal_peak_detector | 0 | 0 | 0.000000 | 9 | 31 | 19 | 0 | 22.500000 | 26.470588 | 25 | 0 | 0 |
| human_lnc_atlas_508kb_target | overlap_density_detector | 0 | 0 | 0.000000 | 9 | 31 | 19 | 0 | 22.500000 | 26.470588 | 25 | 0 | 0 |
| human_lnc_atlas_508kb_target | combined_score_landscape_detector | 34 | 2509826 | 0.324527 | 14 | 26 | 10 | 16 | 35.000000 | 100.000000 | 0 | 0 | 0 |
| human_lnc_atlas_508kb_target | combined_detector_current_guard | 34 | 2509826 | 0.324527 | 14 | 26 | 10 | 16 | 35.000000 | 100.000000 | 0 | 0 | 0 |
| human_lnc_atlas_508kb_target | combined_detector_relaxed_guard | 34 | 2509826 | 0.324527 | 18 | 22 | 10 | 12 | 45.000000 | 100.000000 | 0 | 0 | 0 |

This score-landscape/local-max detector shadow is diagnostic-only. It uses non-oracle Fasim-visible local-max proxies from final records, score/Nt bands, long-hit records, and overlap-density clusters. It does not add recovery logic or change production selection.

Current Fasim profile output does not expose column-max coordinates as a stable production input, so this shadow evaluates deployable score-landscape proxies before any C++ or output-path change.

## Aggregate

| Metric | Value |
| --- | --- |
| fasim_sim_recovery_real_corpus_cases | 2 |
| fasim_sim_recovery_real_corpus_repeat | 1 |
| fasim_sim_recovery_real_corpus_validated_cases | 2 |
| fasim_sim_recovery_real_corpus_validate_supported_cases | 1 |
| fasim_sim_recovery_real_corpus_fast_digest_stable | 1 |
| fasim_sim_recovery_real_corpus_sim_close_digest_stable | 1 |
| fasim_sim_recovery_real_corpus_validate_selection_stable | 1 |
| fasim_sim_recovery_real_corpus_fast_mode_output_mutations | 0 |
| fasim_sim_recovery_real_corpus_fast_total_seconds_median | 1.250976 |
| fasim_sim_recovery_real_corpus_sim_close_wall_seconds_median | 1.026961 |
| fasim_sim_recovery_real_corpus_sim_close_end_to_end_seconds_median | 2.277936 |
| fasim_sim_recovery_real_corpus_validate_wall_seconds_median | 80.014323 |
| fasim_sim_recovery_real_corpus_validate_end_to_end_seconds_median | 81.265298 |
| fasim_sim_recovery_real_corpus_boxes_median | 34.000000 |
| fasim_sim_recovery_real_corpus_cells_median | 501250.000000 |
| fasim_sim_recovery_real_corpus_full_search_cells_median | 800442981.000000 |
| fasim_sim_recovery_real_corpus_cell_fraction_median | 0.062622 |
| fasim_sim_recovery_real_corpus_executor_seconds_median | 0.969403 |
| fasim_sim_recovery_real_corpus_fasim_records_median | 34.000000 |
| fasim_sim_recovery_real_corpus_recovered_candidates_median | 30.000000 |
| fasim_sim_recovery_real_corpus_recovered_accepted_median | 14.000000 |
| fasim_sim_recovery_real_corpus_fasim_suppressed_median | 34.000000 |
| fasim_sim_recovery_real_corpus_sim_close_output_records_median | 14.000000 |
| fasim_sim_recovery_real_corpus_validate_supported_records_median | 40.000000 |
| fasim_sim_recovery_real_corpus_sim_records_median | 40.000000 |
| fasim_sim_recovery_real_corpus_sim_close_records_median | 14.000000 |
| fasim_sim_recovery_real_corpus_shared_records_median | 14.000000 |
| fasim_sim_recovery_real_corpus_sim_only_records_median | 31.000000 |
| fasim_sim_recovery_real_corpus_sim_close_extra_records_median | 0.000000 |
| fasim_sim_recovery_real_corpus_recall_vs_sim_median | 35.000000 |
| fasim_sim_recovery_real_corpus_precision_vs_sim_median | 100.000000 |
| fasim_sim_recovery_real_corpus_extra_vs_sim_median | 0.000000 |
| fasim_sim_recovery_real_corpus_overlap_conflicts_median | 0.000000 |
| fasim_sim_recovery_real_corpus_fallbacks_median | 0.000000 |
| fasim_sim_recovery_real_corpus_sim_labels_production_inputs | 0 |
| fasim_sim_recovery_real_corpus_recommendation | experimental_opt_in |

## Miss Taxonomy Aggregate

| Metric | Value |
| --- | --- |
| fasim_sim_recovery_real_corpus_miss_taxonomy_enabled | 1 |
| fasim_sim_recovery_real_corpus_sim_records | 40.000000 |
| fasim_sim_recovery_real_corpus_shared_records | 14.000000 |
| fasim_sim_recovery_real_corpus_missed_records | 26.000000 |
| fasim_sim_recovery_real_corpus_not_box_covered | 10.000000 |
| fasim_sim_recovery_real_corpus_box_covered_executor_missing | 0.000000 |
| fasim_sim_recovery_real_corpus_guard_rejected | 16.000000 |
| fasim_sim_recovery_real_corpus_replacement_suppressed | 0.000000 |
| fasim_sim_recovery_real_corpus_canonicalization_mismatches | 0.000000 |
| fasim_sim_recovery_real_corpus_metric_ambiguity_records | 0.000000 |

## Score-Landscape Detector Best Aggregate

| Metric | Value |
| --- | --- |
| fasim_sim_recovery_score_landscape_detector_enabled | 1 |
| fasim_sim_recovery_score_landscape_detector_strategy | combined_detector_relaxed_guard |
| fasim_sim_recovery_score_landscape_detector_boxes | 34 |
| fasim_sim_recovery_score_landscape_detector_cells | 2509826 |
| fasim_sim_recovery_score_landscape_detector_cell_fraction | 0.324527 |
| fasim_sim_recovery_score_landscape_detector_sim_records | 40 |
| fasim_sim_recovery_score_landscape_detector_shared_records | 18 |
| fasim_sim_recovery_score_landscape_detector_missed_records | 22 |
| fasim_sim_recovery_score_landscape_detector_not_box_covered | 10 |
| fasim_sim_recovery_score_landscape_detector_guard_rejected | 12 |
| fasim_sim_recovery_score_landscape_detector_recall_vs_sim | 45.000000 |
| fasim_sim_recovery_score_landscape_detector_precision_vs_sim | 100.000000 |
| fasim_sim_recovery_score_landscape_detector_extra_vs_sim | 0 |
| fasim_sim_recovery_score_landscape_detector_overlap_conflicts | 0 |
| fasim_sim_recovery_score_landscape_detector_output_mutations | 0 |

## Decision

Keep `FASIM_SIM_RECOVERY=1` as an experimental opt-in. This characterization checks validation coverage, output stability, and recovery footprint on the supplied FASTA cases; production recommendation still requires broader real-corpus evidence.

At least one supplied case produced validate-supported legacy SIM records. Interpret recall/precision only for those supported cases; unsupported cases remain footprint/stability evidence.

The current supported-case recall is below the synthetic representative signal. This does not justify recommending SIM-close mode; it points to further real-corpus guard/replacement refinement before any high-accuracy claim.

The miss taxonomy attributes the current SIM-close recall gap to 10 records outside the Fasim-visible recovery boxes and 16 records rejected by the current `combined_non_oracle` guard. Executor-missing, replacement-suppressed, canonicalization-mismatch, and metric-ambiguity counts are 0, 0, 0, and 0, respectively.

The next algorithmic work should therefore be split between real-corpus risk detector or box expansion for the uncovered records, and real-corpus guard refinement for covered executor candidates. This PR does not make those changes.

The best non-oracle score-landscape/local-max detector shadow strategy is `combined_detector_relaxed_guard` with recall 45.00%, precision 100.00%, extra records 0, and cell fraction 0.324527%. This is diagnostic evidence only; it does not change SIM-close real output.

The detector shadow improves recall but does not clear the strong tradeoff threshold. Continue detector analysis before any real-mode update.

Treat this as stability and footprint evidence only when validation is unavailable; SIM-close output may intentionally differ from the fast-mode Fasim digest.

Do not recommend or default SIM-close mode from this PR.

## Scope

```text
Default Fasim output changed: no
SIM labels used as production input: no
Validation affects production selection: no
Scoring/threshold/non-overlap behavior change: no
GPU/filter behavior change: no
Recommended/default mode: no
Production accuracy claim: no
```
