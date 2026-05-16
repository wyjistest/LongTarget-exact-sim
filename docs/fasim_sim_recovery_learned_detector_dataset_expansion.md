# Fasim SIM-Close Learned Detector Dataset Expansion

## Offline Dataset Expansion Audit

This report audits the positive + hard-negative learned-detector dataset, the available hard-negative sources in the source TSV, and split discipline for future offline detector research. It does not add a runtime model or change Fasim output.

Input negative dataset: `/data/wenyujianData/LongTarget-exact-sim/.worktrees/fasim-sim-recovery-learned-detector-dataset-expansion/.tmp/fasim_sim_recovery_learned_detector_dataset_expansion/negative_dataset.tsv`
Input source learned dataset: `/data/wenyujianData/LongTarget-exact-sim/.worktrees/fasim-sim-recovery-learned-detector-dataset-expansion/.tmp/fasim_sim_recovery_learned_detector_dataset_expansion/learned_detector_dataset.tsv`

| Metric | Value |
| --- | --- |
| fasim_sim_recovery_learned_detector_dataset_expansion_enabled | 1 |
| fasim_sim_recovery_learned_detector_dataset_expansion_rows | 65 |
| fasim_sim_recovery_learned_detector_dataset_expansion_positive_rows | 40 |
| fasim_sim_recovery_learned_detector_dataset_expansion_negative_rows | 25 |
| fasim_sim_recovery_learned_detector_dataset_expansion_learnable_two_class | 1 |
| fasim_sim_recovery_learned_detector_dataset_expansion_source_rows | 118 |
| fasim_sim_recovery_learned_detector_dataset_expansion_workload_count | 1 |
| fasim_sim_recovery_learned_detector_dataset_expansion_family_count | 4 |
| fasim_sim_recovery_learned_detector_dataset_expansion_unique_workloads | 1 |
| fasim_sim_recovery_learned_detector_dataset_expansion_unique_families | 4 |
| fasim_sim_recovery_learned_detector_dataset_expansion_hard_negative_sources | fasim_supported_non_sim:25 |
| fasim_sim_recovery_learned_detector_dataset_expansion_hard_negative_source_count | 1 |
| fasim_sim_recovery_learned_detector_dataset_expansion_available_requested_negative_sources | fasim_supported_non_sim:25 |
| fasim_sim_recovery_learned_detector_dataset_expansion_missing_requested_negative_sources | executor_candidate_non_sim,extra_vs_sim_candidate,near_threshold_rejected_candidate,no_legacy_sim_records_proxy |
| fasim_sim_recovery_learned_detector_dataset_expansion_candidate_eligible_positive_rows | 30 |
| fasim_sim_recovery_learned_detector_dataset_expansion_candidate_eligible_negative_rows | 25 |
| fasim_sim_recovery_learned_detector_dataset_expansion_heldout_workload_available | 0 |
| fasim_sim_recovery_learned_detector_dataset_expansion_heldout_family_available | 1 |
| fasim_sim_recovery_learned_detector_dataset_expansion_modeling_gate | collect_more_workloads |
| fasim_sim_recovery_learned_detector_dataset_expansion_production_model | 0 |
| fasim_sim_recovery_learned_detector_dataset_expansion_sim_labels_runtime_inputs | 0 |
| fasim_sim_recovery_learned_detector_dataset_expansion_runtime_behavior_changed | 0 |
| fasim_sim_recovery_learned_detector_dataset_expansion_requested_negative_source_executor_candidate_non_sim | 0 |
| fasim_sim_recovery_learned_detector_dataset_expansion_available_negative_source_executor_candidate_non_sim | 0 |
| fasim_sim_recovery_learned_detector_dataset_expansion_requested_negative_source_extra_vs_sim_candidate | 0 |
| fasim_sim_recovery_learned_detector_dataset_expansion_available_negative_source_extra_vs_sim_candidate | 0 |
| fasim_sim_recovery_learned_detector_dataset_expansion_requested_negative_source_fasim_supported_non_sim | 25 |
| fasim_sim_recovery_learned_detector_dataset_expansion_available_negative_source_fasim_supported_non_sim | 25 |
| fasim_sim_recovery_learned_detector_dataset_expansion_requested_negative_source_near_threshold_rejected_candidate | 0 |
| fasim_sim_recovery_learned_detector_dataset_expansion_available_negative_source_near_threshold_rejected_candidate | 0 |
| fasim_sim_recovery_learned_detector_dataset_expansion_requested_negative_source_no_legacy_sim_records_proxy | 0 |
| fasim_sim_recovery_learned_detector_dataset_expansion_available_negative_source_no_legacy_sim_records_proxy | 0 |
| fasim_sim_recovery_learned_detector_dataset_expansion_current_split_train_positive | 22 |
| fasim_sim_recovery_learned_detector_dataset_expansion_current_split_train_negative | 13 |
| fasim_sim_recovery_learned_detector_dataset_expansion_current_split_validation_positive | 18 |
| fasim_sim_recovery_learned_detector_dataset_expansion_current_split_validation_negative | 12 |
| fasim_sim_recovery_learned_detector_dataset_expansion_current_split_degenerate | 0 |
| fasim_sim_recovery_learned_detector_dataset_expansion_family_heldout_train_positive | 24 |
| fasim_sim_recovery_learned_detector_dataset_expansion_family_heldout_train_negative | 18 |
| fasim_sim_recovery_learned_detector_dataset_expansion_family_heldout_validation_positive | 16 |
| fasim_sim_recovery_learned_detector_dataset_expansion_family_heldout_validation_negative | 7 |
| fasim_sim_recovery_learned_detector_dataset_expansion_family_heldout_degenerate | 0 |
| fasim_sim_recovery_learned_detector_dataset_expansion_workload_heldout_train_positive | 0 |
| fasim_sim_recovery_learned_detector_dataset_expansion_workload_heldout_train_negative | 0 |
| fasim_sim_recovery_learned_detector_dataset_expansion_workload_heldout_validation_positive | 40 |
| fasim_sim_recovery_learned_detector_dataset_expansion_workload_heldout_validation_negative | 25 |
| fasim_sim_recovery_learned_detector_dataset_expansion_workload_heldout_degenerate | 1 |
| fasim_sim_recovery_learned_detector_dataset_expansion_model_evaluation_mode | heldout_split |
| fasim_sim_recovery_learned_detector_dataset_expansion_model_heavy_ml_dependency | 0 |
| fasim_sim_recovery_learned_detector_dataset_expansion_selected_threshold | -0.496593 |
| fasim_sim_recovery_learned_detector_dataset_expansion_all_row_validation_precision | 100.000000 |
| fasim_sim_recovery_learned_detector_dataset_expansion_all_row_validation_recall | 83.333333 |
| fasim_sim_recovery_learned_detector_dataset_expansion_all_row_validation_false_positives | 0 |
| fasim_sim_recovery_learned_detector_dataset_expansion_all_row_validation_false_negatives | 3 |
| fasim_sim_recovery_learned_detector_dataset_expansion_candidate_eligible_selected | 10 |
| fasim_sim_recovery_learned_detector_dataset_expansion_candidate_eligible_true_positive | 10 |
| fasim_sim_recovery_learned_detector_dataset_expansion_candidate_eligible_false_positive | 0 |
| fasim_sim_recovery_learned_detector_dataset_expansion_candidate_eligible_false_negative_vs_all_positives | 8 |
| fasim_sim_recovery_learned_detector_dataset_expansion_candidate_eligible_precision | 100.000000 |
| fasim_sim_recovery_learned_detector_dataset_expansion_candidate_eligible_recall_vs_all_positives | 55.555556 |
| fasim_sim_recovery_learned_detector_dataset_expansion_current_guard_validation_precision | 100.000000 |
| fasim_sim_recovery_learned_detector_dataset_expansion_current_guard_validation_recall | 16.666667 |
| fasim_sim_recovery_learned_detector_dataset_expansion_current_guard_validation_false_positives | 0 |
| fasim_sim_recovery_learned_detector_dataset_expansion_current_guard_validation_false_negatives | 15 |
| fasim_sim_recovery_learned_detector_dataset_expansion_beats_current_guard_on_validation | 1 |

## Hard Negative Source Audit

| Source | Dataset rows | Source rows available |
| --- | ---: | ---: |
| executor_candidate_non_sim | 0 | 0 |
| extra_vs_sim_candidate | 0 | 0 |
| fasim_supported_non_sim | 25 | 25 |
| near_threshold_rejected_candidate | 0 | 0 |
| no_legacy_sim_records_proxy | 0 | 0 |

No unavailable hard-negative rows are fabricated.

## Source Row Mix

| Source row kind | Rows |
| --- | ---: |
| accepted_candidate | 14 |
| executor_candidate | 30 |
| fasim_record | 34 |
| sim_record | 40 |

## Split Discipline Audit

| Split policy | Train positive | Train negative | Validation positive | Validation negative | Degenerate |
| --- | ---: | ---: | ---: | ---: | ---: |
| current_split | 22 | 13 | 18 | 12 | 0 |
| family_heldout | 24 | 18 | 16 | 7 | 0 |
| workload_heldout | 0 | 0 | 40 | 25 | 1 |

Workload-heldout evaluation can be degenerate when only one workload has candidate rows. In that case the report records the limitation instead of treating the split as held-out evidence.

## Corpus Expansion Gate

| Gate | Value |
| --- | --- |
| workload_count | 1 |
| family_count | 4 |
| hard_negative_source_count | 1 |
| heldout_workload_available | 0 |
| heldout_family_available | 1 |
| modeling_gate | collect_more_workloads |

`modeling_gate=ready_for_offline_shadow` requires non-degenerate workload and family held-out evidence plus at least three hard-negative sources. Otherwise the next step remains corpus expansion, not runtime model promotion.

## Current Split Shadow Metrics

| Method | Precision | Recall | False positives | False negatives |
| --- | ---: | ---: | ---: | ---: |
| current_guard | 100.000000 | 16.666667 | 0 | 15 |
| learned_shadow_all_rows | 100.000000 | 83.333333 | 0 | 3 |
| learned_shadow_candidate_eligible | 100.000000 | 55.555556 | 0 | 8 |

## Interpretation

This is a dataset expansion and split-discipline checkpoint, not a model promotion checkpoint. When requested hard-negative sources are absent from the source TSV, the correct result is an explicit zero count.

This PR audits the current dataset and shows it is still too small and too narrow for production learned-detector claims.

No production model is trained or loaded. SIM labels remain offline labels only. They must not be used as runtime detector inputs, guard inputs, replacement inputs, or output ordering inputs.

## Scope

```text
Production model added: no
Fasim runtime changed: no
SIM-close runtime changed: no
Scoring/threshold/non-overlap behavior changed: no
GPU/filter behavior changed: no
SIM labels used as runtime input: no
Recommended/default mode: no
```
