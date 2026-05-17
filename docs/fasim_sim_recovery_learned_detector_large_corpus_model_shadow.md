# Fasim SIM-Close Learned Detector Large Corpus Model Shadow

## Large Corpus Model Shadow

This report evaluates the dependency-free learned/ranked detector shadow on the #91 large corpus. It is an offline evaluation only: no runtime model is trained or loaded, and Fasim/SIM-close runtime behavior is unchanged.

| Metric | Value |
| --- | --- |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_enabled | 1 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_rows | 140 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_positive_rows | 73 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_negative_rows | 67 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_workload_count | 21 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_validate_supported_workload_count | 19 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_no_legacy_sim_records_workload_count | 2 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_hard_negative_sources | executor_candidate_non_sim:9,extra_vs_sim_candidate:2,fasim_supported_non_sim:46,near_threshold_rejected_candidate:7,no_legacy_sim_records_proxy:3 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_hard_negative_source_count | 5 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_feature_count | 19 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_features | score,Nt,identity,interval_length,local_rank,family_rank,overlap_degree,distance_to_fasim_boundary,box_size,family_size,family_span,interval_overlap_ratio,dominance_margin,score_margin,Nt_margin,near_threshold_density,peak_count,second_peak_gap,plateau_width |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_evaluation_policy | workload_heldout |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_train_positive | 48 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_train_negative | 37 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_validation_positive | 25 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_validation_negative | 30 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_current_split_degenerate | 0 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_workload_heldout_degenerate | 0 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_family_heldout_degenerate | 0 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_negative_source_heldout_degenerate | 0 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_current_guard_recall | 44.000000 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_current_guard_precision | 91.666667 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_current_guard_false_positives | 1 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_current_guard_false_negatives | 14 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_learned_shadow_recall | 60.000000 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_learned_shadow_precision | 57.692308 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_candidate_eligible_recall | 60.000000 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_candidate_eligible_precision | 57.692308 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_false_positives | 11 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_false_negatives | 10 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_false_positives_by_negative_source | executor_candidate_non_sim:1,extra_vs_sim_candidate:1,fasim_supported_non_sim:5,near_threshold_rejected_candidate:4 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_false_negatives_by_workload | marmoset_extra_ENSG00000244558_1:3,marmoset_extra_ENSG00000259912_1:6,tiny_validate:1 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_no_legacy_proxy_false_positives | 0 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_selected_threshold | -1.344861 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_loo_workload_evaluated | 18 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_loo_workload_skipped | 3 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_beats_current_guard_on_validation | 0 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_decision | pause_model_path_keep_guard |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_production_model | 0 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_sim_labels_runtime_inputs | 0 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_runtime_behavior_changed | 0 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_model_training_added | 0 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_deep_learning_dependency | 0 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_recommended_default_sim_close | 0 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_current_split_train_positive | 56 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_current_split_train_negative | 52 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_current_split_validation_positive | 17 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_current_split_validation_negative | 15 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_current_split_selected_threshold | -0.266848 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_current_split_current_guard_precision | 100.000000 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_current_split_current_guard_recall | 35.294118 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_current_split_learned_shadow_precision | 76.470588 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_current_split_learned_shadow_recall | 76.470588 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_current_split_candidate_eligible_precision | 76.470588 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_current_split_candidate_eligible_recall | 76.470588 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_current_split_candidate_eligible_false_positives | 4 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_current_split_candidate_eligible_false_negatives | 4 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_workload_heldout_train_positive | 48 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_workload_heldout_train_negative | 37 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_workload_heldout_validation_positive | 25 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_workload_heldout_validation_negative | 30 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_workload_heldout_selected_threshold | -1.344861 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_workload_heldout_current_guard_precision | 91.666667 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_workload_heldout_current_guard_recall | 44.000000 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_workload_heldout_learned_shadow_precision | 57.692308 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_workload_heldout_learned_shadow_recall | 60.000000 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_workload_heldout_candidate_eligible_precision | 57.692308 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_workload_heldout_candidate_eligible_recall | 60.000000 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_workload_heldout_candidate_eligible_false_positives | 11 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_workload_heldout_candidate_eligible_false_negatives | 10 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_family_heldout_train_positive | 43 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_family_heldout_train_negative | 42 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_family_heldout_validation_positive | 30 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_family_heldout_validation_negative | 25 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_family_heldout_selected_threshold | -1.230405 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_family_heldout_current_guard_precision | 94.736842 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_family_heldout_current_guard_recall | 60.000000 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_family_heldout_learned_shadow_precision | 61.538462 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_family_heldout_learned_shadow_recall | 80.000000 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_family_heldout_candidate_eligible_precision | 58.333333 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_family_heldout_candidate_eligible_recall | 70.000000 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_family_heldout_candidate_eligible_false_positives | 15 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_family_heldout_candidate_eligible_false_negatives | 9 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_negative_source_heldout_train_positive | 48 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_negative_source_heldout_train_negative | 51 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_negative_source_heldout_validation_positive | 25 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_negative_source_heldout_validation_negative | 16 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_negative_source_heldout_selected_threshold | -0.430485 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_negative_source_heldout_current_guard_precision | 100.000000 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_negative_source_heldout_current_guard_recall | 44.000000 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_negative_source_heldout_learned_shadow_precision | 42.857143 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_negative_source_heldout_learned_shadow_recall | 48.000000 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_negative_source_heldout_candidate_eligible_precision | 42.857143 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_negative_source_heldout_candidate_eligible_recall | 48.000000 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_negative_source_heldout_candidate_eligible_false_positives | 16 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_negative_source_heldout_candidate_eligible_false_negatives | 13 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_baseline_84_small_dataset_rows | 65 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_baseline_84_small_dataset_current_guard_precision | 100.000000 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_baseline_84_small_dataset_current_guard_recall | 16.666667 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_baseline_84_small_dataset_learned_shadow_precision | 100.000000 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_baseline_84_small_dataset_learned_shadow_recall | 55.555556 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_baseline_87_expanded_corpus_rows | 44 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_baseline_87_expanded_corpus_current_guard_precision | 90.000000 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_baseline_87_expanded_corpus_current_guard_recall | 100.000000 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_baseline_87_expanded_corpus_learned_shadow_precision | 50.000000 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_baseline_87_expanded_corpus_learned_shadow_recall | 77.777778 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_baseline_88_feature_expanded_rows | 44 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_baseline_88_feature_expanded_current_guard_precision | 90.000000 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_baseline_88_feature_expanded_current_guard_recall | 100.000000 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_baseline_88_feature_expanded_learned_shadow_precision | 38.461538 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_baseline_88_feature_expanded_learned_shadow_recall | 55.555556 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_source_rows | 254 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_baseline_90_rows | 59 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_baseline_90_positive_rows | 26 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_baseline_90_negative_rows | 33 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_baseline_90_workload_count | 7 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_baseline_90_hard_negative_source_count | 5 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_baseline_90_current_guard_precision | 90.000000 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_baseline_90_current_guard_recall | 52.941176 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_baseline_90_learned_shadow_precision | 43.750000 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_baseline_90_learned_shadow_recall | 41.176471 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_baseline_90_candidate_eligible_precision | 43.750000 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_baseline_90_candidate_eligible_recall | 41.176471 |
| fasim_sim_recovery_learned_detector_large_corpus_model_shadow_baseline_90_decision | pause_model_path_keep_guard |

## Split Evaluation

| Policy | Train + | Train - | Validation + | Validation - | Degenerate | Current guard precision | Current guard recall | Learned precision | Learned recall | Candidate precision | Candidate recall | False + | False - | Threshold |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| current_split | 56 | 52 | 17 | 15 | 0 | 100.000000 | 35.294118 | 76.470588 | 76.470588 | 76.470588 | 76.470588 | 4 | 4 | -0.266848 |
| workload_heldout | 48 | 37 | 25 | 30 | 0 | 91.666667 | 44.000000 | 57.692308 | 60.000000 | 57.692308 | 60.000000 | 11 | 10 | -1.344861 |
| family_heldout | 43 | 42 | 30 | 25 | 0 | 94.736842 | 60.000000 | 61.538462 | 80.000000 | 58.333333 | 70.000000 | 15 | 9 | -1.230405 |
| negative_source_heldout | 48 | 51 | 25 | 16 | 0 | 100.000000 | 44.000000 | 42.857143 | 48.000000 | 42.857143 | 48.000000 | 16 | 13 | -0.430485 |

## Negative-Source Held-Out

| Metric | Value |
| --- | --- |
| train_positive | 48 |
| train_negative | 51 |
| validation_positive | 25 |
| validation_negative | 16 |
| degenerate | 0 |
| current_guard_precision | 100.000000 |
| current_guard_recall | 44.000000 |
| candidate_eligible_precision | 42.857143 |
| candidate_eligible_recall | 48.000000 |
| candidate_eligible_false_positives | 16 |
| candidate_eligible_false_negatives | 13 |
| selected_threshold | -0.430485 |

## Error Attribution

| Error bucket | Rows |
| --- | --- |
| false_positives_by_negative_source | executor_candidate_non_sim:1,extra_vs_sim_candidate:1,fasim_supported_non_sim:5,near_threshold_rejected_candidate:4 |
| false_negatives_by_workload | marmoset_extra_ENSG00000244558_1:3,marmoset_extra_ENSG00000259912_1:6,tiny_validate:1 |
| no_legacy_proxy_false_positives | 0 |

## Leave-One-Workload-Out

Skipped degenerate workloads: `3`.

| Workload | Train + | Train - | Validation + | Validation - | Current guard precision | Current guard recall | Candidate precision | Candidate recall | False + | False - | Threshold |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| marmoset_33639 | 72 | 65 | 1 | 2 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 1 | -0.533994 |
| marmoset_59006 | 66 | 61 | 7 | 6 | 100.000000 | 57.142857 | 45.454545 | 71.428571 | 6 | 2 | -1.240580 |
| marmoset_extra_ENSG00000224091_1 | 72 | 66 | 1 | 1 | 0.000000 | 0.000000 | 100.000000 | 100.000000 | 0 | 0 | -1.246646 |
| marmoset_extra_ENSG00000234936_1 | 72 | 66 | 1 | 1 | 0.000000 | 0.000000 | 50.000000 | 100.000000 | 1 | 0 | -1.241527 |
| marmoset_extra_ENSG00000235058_1 | 72 | 66 | 1 | 1 | 0.000000 | 0.000000 | 100.000000 | 100.000000 | 0 | 0 | -1.251369 |
| marmoset_extra_ENSG00000237797_1 | 57 | 59 | 16 | 8 | 100.000000 | 50.000000 | 90.000000 | 56.250000 | 1 | 7 | -0.119304 |
| marmoset_extra_ENSG00000244558_1 | 69 | 63 | 4 | 4 | 0.000000 | 0.000000 | 100.000000 | 25.000000 | 0 | 3 | -0.381934 |
| marmoset_extra_ENSG00000254789_1 | 70 | 64 | 3 | 3 | 0.000000 | 0.000000 | 60.000000 | 100.000000 | 2 | 0 | -1.153441 |
| marmoset_extra_ENSG00000255542_1 | 72 | 65 | 1 | 2 | 100.000000 | 100.000000 | 33.333333 | 100.000000 | 2 | 0 | -1.194279 |
| marmoset_extra_ENSG00000257180_1 | 70 | 65 | 3 | 2 | 100.000000 | 33.333333 | 33.333333 | 33.333333 | 2 | 2 | -1.292282 |
| marmoset_extra_ENSG00000259377_1 | 72 | 66 | 1 | 1 | 100.000000 | 100.000000 | 50.000000 | 100.000000 | 1 | 0 | -1.244993 |
| marmoset_extra_ENSG00000259912_1 | 66 | 63 | 7 | 4 | 0.000000 | 0.000000 | 100.000000 | 28.571429 | 0 | 5 | -0.677158 |
| marmoset_extra_ENSG00000260017_1 | 66 | 63 | 7 | 4 | 80.000000 | 57.142857 | 57.142857 | 57.142857 | 3 | 3 | -0.395513 |
| marmoset_extra_ENSG00000260509_2 | 71 | 65 | 2 | 2 | 0.000000 | 0.000000 | 100.000000 | 100.000000 | 0 | 0 | -0.410949 |
| marmoset_extra_ENSG00000263146_2 | 69 | 65 | 4 | 2 | 100.000000 | 50.000000 | 75.000000 | 75.000000 | 1 | 1 | -1.253540 |
| marmoset_extra_ENSG00000269473_1 | 72 | 66 | 1 | 1 | 0.000000 | 0.000000 | 50.000000 | 100.000000 | 1 | 0 | -1.246143 |
| marmoset_extra_ENSG00000273492_1 | 70 | 64 | 3 | 3 | 100.000000 | 66.666667 | 50.000000 | 100.000000 | 3 | 0 | -1.222229 |
| tiny_validate | 64 | 50 | 9 | 17 | 90.000000 | 100.000000 | 40.909091 | 100.000000 | 13 | 0 | -1.300254 |

## Baseline Comparison

| Source | Rows | Current guard precision | Current guard recall | Learned precision | Learned recall | Decision |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| #84_small_dataset | 65 | 100.000000 | 16.666667 | 100.000000 | 55.555556 | historical |
| #87_expanded_corpus | 44 | 90.000000 | 100.000000 | 50.000000 | 77.777778 | historical |
| #88_feature_expanded | 44 | 90.000000 | 100.000000 | 38.461538 | 55.555556 | historical |
| #90_expanded_hard_negative_primary | 59 | 90.000000 | 52.941176 | 43.750000 | 41.176471 | pause_model_path_keep_guard |
| #91_large_corpus_primary | 140 | 91.666667 | 44.000000 | 57.692308 | 60.000000 | pause_model_path_keep_guard |

## Decision

Decision: `pause_model_path_keep_guard`.

The decision is based on candidate-eligible held-out metrics. If only current-split/resubstitution improves, this is not evidence for runtime promotion. If learned shadow still loses to the hand-written guard, keep the guard and collect better signal before revisiting runtime work.

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
