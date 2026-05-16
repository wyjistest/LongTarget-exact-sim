# Fasim SIM-Close Learned Detector Expanded Hard-Negative Model Shadow

## Expanded Hard-Negative Model Shadow

This report evaluates the dependency-free learned/ranked detector shadow on the #89 expanded hard-negative corpus. It is an offline evaluation only: no runtime model is trained or loaded, and Fasim/SIM-close runtime behavior is unchanged.

| Metric | Value |
| --- | --- |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_enabled | 1 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_rows | 59 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_positive_rows | 26 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_negative_rows | 33 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_workload_count | 7 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_validate_supported_workload_count | 6 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_no_legacy_sim_records_workload_count | 1 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_hard_negative_sources | executor_candidate_non_sim:8,extra_vs_sim_candidate:1,fasim_supported_non_sim:15,near_threshold_rejected_candidate:7,no_legacy_sim_records_proxy:2 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_hard_negative_source_count | 5 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_feature_count | 19 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_features | score,Nt,identity,interval_length,local_rank,family_rank,overlap_degree,distance_to_fasim_boundary,box_size,family_size,family_span,interval_overlap_ratio,dominance_margin,score_margin,Nt_margin,near_threshold_density,peak_count,second_peak_gap,plateau_width |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_evaluation_policy | workload_heldout |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_train_positive | 9 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_train_negative | 11 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_validation_positive | 17 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_validation_negative | 22 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_current_split_degenerate | 0 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_workload_heldout_degenerate | 0 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_family_heldout_degenerate | 0 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_negative_source_heldout_degenerate | 0 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_current_guard_recall | 52.941176 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_current_guard_precision | 90.000000 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_current_guard_false_positives | 1 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_current_guard_false_negatives | 8 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_learned_shadow_recall | 41.176471 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_learned_shadow_precision | 43.750000 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_candidate_eligible_recall | 41.176471 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_candidate_eligible_precision | 43.750000 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_false_positives | 9 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_false_negatives | 10 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_false_positives_by_negative_source | extra_vs_sim_candidate:1,fasim_supported_non_sim:4,near_threshold_rejected_candidate:4 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_false_negatives_by_workload | marmoset_extra_ENSG00000259912_1:6,tiny_validate:4 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_no_legacy_proxy_false_positives | 0 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_selected_threshold | -0.663827 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_loo_workload_evaluated | 6 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_loo_workload_skipped | 1 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_beats_current_guard_on_validation | 0 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_decision | pause_model_path_keep_guard |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_production_model | 0 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_sim_labels_runtime_inputs | 0 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_runtime_behavior_changed | 0 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_model_training_added | 0 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_deep_learning_dependency | 0 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_recommended_default_sim_close | 0 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_current_split_train_positive | 24 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_current_split_train_negative | 31 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_current_split_validation_positive | 2 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_current_split_validation_negative | 2 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_current_split_selected_threshold | -1.482422 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_current_split_current_guard_precision | 100.000000 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_current_split_current_guard_recall | 100.000000 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_current_split_learned_shadow_precision | 50.000000 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_current_split_learned_shadow_recall | 100.000000 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_current_split_candidate_eligible_precision | 50.000000 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_current_split_candidate_eligible_recall | 100.000000 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_current_split_candidate_eligible_false_positives | 2 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_current_split_candidate_eligible_false_negatives | 0 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_workload_heldout_train_positive | 9 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_workload_heldout_train_negative | 11 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_workload_heldout_validation_positive | 17 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_workload_heldout_validation_negative | 22 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_workload_heldout_selected_threshold | -0.663827 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_workload_heldout_current_guard_precision | 90.000000 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_workload_heldout_current_guard_recall | 52.941176 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_workload_heldout_learned_shadow_precision | 43.750000 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_workload_heldout_learned_shadow_recall | 41.176471 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_workload_heldout_candidate_eligible_precision | 43.750000 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_workload_heldout_candidate_eligible_recall | 41.176471 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_workload_heldout_candidate_eligible_false_positives | 9 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_workload_heldout_candidate_eligible_false_negatives | 10 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_family_heldout_train_positive | 12 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_family_heldout_train_negative | 16 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_family_heldout_validation_positive | 14 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_family_heldout_validation_negative | 17 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_family_heldout_selected_threshold | -0.290947 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_family_heldout_current_guard_precision | 100.000000 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_family_heldout_current_guard_recall | 64.285714 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_family_heldout_learned_shadow_precision | 53.846154 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_family_heldout_learned_shadow_recall | 50.000000 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_family_heldout_candidate_eligible_precision | 53.846154 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_family_heldout_candidate_eligible_recall | 50.000000 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_family_heldout_candidate_eligible_false_positives | 6 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_family_heldout_candidate_eligible_false_negatives | 7 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_negative_source_heldout_train_positive | 9 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_negative_source_heldout_train_negative | 18 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_negative_source_heldout_validation_positive | 17 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_negative_source_heldout_validation_negative | 15 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_negative_source_heldout_selected_threshold | 2.371978 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_negative_source_heldout_current_guard_precision | 100.000000 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_negative_source_heldout_current_guard_recall | 52.941176 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_negative_source_heldout_learned_shadow_precision | 30.000000 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_negative_source_heldout_learned_shadow_recall | 35.294118 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_negative_source_heldout_candidate_eligible_precision | 30.000000 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_negative_source_heldout_candidate_eligible_recall | 35.294118 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_negative_source_heldout_candidate_eligible_false_positives | 14 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_negative_source_heldout_candidate_eligible_false_negatives | 11 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_baseline_84_small_dataset_rows | 65 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_baseline_84_small_dataset_current_guard_precision | 100.000000 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_baseline_84_small_dataset_current_guard_recall | 16.666667 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_baseline_84_small_dataset_learned_shadow_precision | 100.000000 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_baseline_84_small_dataset_learned_shadow_recall | 55.555556 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_baseline_87_expanded_corpus_rows | 44 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_baseline_87_expanded_corpus_current_guard_precision | 90.000000 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_baseline_87_expanded_corpus_current_guard_recall | 100.000000 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_baseline_87_expanded_corpus_learned_shadow_precision | 50.000000 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_baseline_87_expanded_corpus_learned_shadow_recall | 77.777778 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_baseline_88_feature_expanded_rows | 44 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_baseline_88_feature_expanded_current_guard_precision | 90.000000 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_baseline_88_feature_expanded_current_guard_recall | 100.000000 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_baseline_88_feature_expanded_learned_shadow_precision | 38.461538 |
| fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_baseline_88_feature_expanded_learned_shadow_recall | 55.555556 |

## Split Evaluation

| Policy | Train + | Train - | Validation + | Validation - | Degenerate | Current guard precision | Current guard recall | Learned precision | Learned recall | Candidate precision | Candidate recall | False + | False - | Threshold |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| current_split | 24 | 31 | 2 | 2 | 0 | 100.000000 | 100.000000 | 50.000000 | 100.000000 | 50.000000 | 100.000000 | 2 | 0 | -1.482422 |
| workload_heldout | 9 | 11 | 17 | 22 | 0 | 90.000000 | 52.941176 | 43.750000 | 41.176471 | 43.750000 | 41.176471 | 9 | 10 | -0.663827 |
| family_heldout | 12 | 16 | 14 | 17 | 0 | 100.000000 | 64.285714 | 53.846154 | 50.000000 | 53.846154 | 50.000000 | 6 | 7 | -0.290947 |
| negative_source_heldout | 9 | 18 | 17 | 15 | 0 | 100.000000 | 52.941176 | 30.000000 | 35.294118 | 30.000000 | 35.294118 | 14 | 11 | 2.371978 |

## Negative-Source Held-Out

| Metric | Value |
| --- | --- |
| train_positive | 9 |
| train_negative | 18 |
| validation_positive | 17 |
| validation_negative | 15 |
| degenerate | 0 |
| candidate_eligible_precision | 30.000000 |
| candidate_eligible_recall | 35.294118 |
| candidate_eligible_false_positives | 14 |
| candidate_eligible_false_negatives | 11 |
| selected_threshold | 2.371978 |

## Error Attribution

| Error bucket | Rows |
| --- | --- |
| false_positives_by_negative_source | extra_vs_sim_candidate:1,fasim_supported_non_sim:4,near_threshold_rejected_candidate:4 |
| false_negatives_by_workload | marmoset_extra_ENSG00000259912_1:6,tiny_validate:4 |
| no_legacy_proxy_false_positives | 0 |

## Leave-One-Workload-Out

Skipped degenerate workloads: `1`.

| Workload | Train + | Train - | Validation + | Validation - | Current guard precision | Current guard recall | Candidate precision | Candidate recall | False + | False - | Threshold |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| marmoset_33639 | 25 | 31 | 1 | 2 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 2 | 1 | -1.623687 |
| marmoset_59006 | 19 | 27 | 7 | 6 | 100.000000 | 57.142857 | 60.000000 | 42.857143 | 2 | 4 | -0.222940 |
| marmoset_extra_ENSG00000224091_1 | 25 | 32 | 1 | 1 | 0.000000 | 0.000000 | 50.000000 | 100.000000 | 1 | 0 | -1.088884 |
| marmoset_extra_ENSG00000234936_1 | 25 | 32 | 1 | 1 | 0.000000 | 0.000000 | 50.000000 | 100.000000 | 1 | 0 | -1.085589 |
| marmoset_extra_ENSG00000259912_1 | 19 | 29 | 7 | 4 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 7 | 1.096207 |
| tiny_validate | 17 | 16 | 9 | 17 | 90.000000 | 100.000000 | 43.750000 | 77.777778 | 9 | 2 | -0.428405 |

## Baseline Comparison

| Source | Rows | Current guard precision | Current guard recall | Learned precision | Learned recall |
| --- | ---: | ---: | ---: | ---: | ---: |
| #84_small_dataset | 65 | 100.000000 | 16.666667 | 100.000000 | 55.555556 |
| #87_expanded_corpus | 44 | 90.000000 | 100.000000 | 50.000000 | 77.777778 |
| #88_feature_expanded | 44 | 90.000000 | 100.000000 | 38.461538 | 55.555556 |
| #90_expanded_hard_negative_primary | 59 | 90.000000 | 52.941176 | 43.750000 | 41.176471 |

## Decision

Decision: `pause_model_path_keep_guard`.

The decision is based on candidate-eligible held-out metrics. If only current-split/resubstitution improves, this is not evidence for runtime promotion. If learned shadow still loses to the hand-written guard, keep the guard and treat #89 as a data foundation.

## Scope

```text
Production model added: no
Runtime model added: no
Deep learning dependency added: no
Fasim runtime changed: no
SIM-close runtime changed: no
Scoring/threshold/non-overlap behavior changed: no
GPU/filter behavior changed: no
SIM labels used as runtime input: no
Recommended/default SIM-close: no
```

No production model is trained or loaded. SIM labels remain offline labels only and must not be used as runtime detector inputs, guard inputs, replacement inputs, or output ordering inputs.
