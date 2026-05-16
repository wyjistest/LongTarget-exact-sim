# Fasim SIM-Close Learned Detector Feature Expansion

## Feature Expansion Shadow

This report reruns the dependency-free learned/ranked detector shadow with richer offline feature columns derived from Fasim-visible source rows. It does not train or load a runtime model and does not change Fasim or SIM-close runtime behavior.

| Metric | Value |
| --- | --- |
| fasim_sim_recovery_learned_detector_feature_expansion_enabled | 1 |
| fasim_sim_recovery_learned_detector_feature_expansion_rows | 44 |
| fasim_sim_recovery_learned_detector_feature_expansion_positive_rows | 17 |
| fasim_sim_recovery_learned_detector_feature_expansion_negative_rows | 27 |
| fasim_sim_recovery_learned_detector_feature_expansion_hard_negative_sources | executor_candidate_non_sim:8,extra_vs_sim_candidate:1,fasim_supported_non_sim:9,near_threshold_rejected_candidate:7,no_legacy_sim_records_proxy:2 |
| fasim_sim_recovery_learned_detector_feature_expansion_hard_negative_source_count | 5 |
| fasim_sim_recovery_learned_detector_feature_expansion_expanded_corpus_available | 1 |
| fasim_sim_recovery_learned_detector_feature_expansion_evaluation_policy | workload_heldout |
| fasim_sim_recovery_learned_detector_feature_expansion_train_positive | 8 |
| fasim_sim_recovery_learned_detector_feature_expansion_train_negative | 10 |
| fasim_sim_recovery_learned_detector_feature_expansion_validation_positive | 9 |
| fasim_sim_recovery_learned_detector_feature_expansion_validation_negative | 17 |
| fasim_sim_recovery_learned_detector_feature_expansion_current_split_degenerate | 0 |
| fasim_sim_recovery_learned_detector_feature_expansion_workload_heldout_degenerate | 0 |
| fasim_sim_recovery_learned_detector_feature_expansion_family_heldout_degenerate | 0 |
| fasim_sim_recovery_learned_detector_feature_expansion_current_guard_recall | 100.000000 |
| fasim_sim_recovery_learned_detector_feature_expansion_current_guard_precision | 90.000000 |
| fasim_sim_recovery_learned_detector_feature_expansion_current_guard_false_positives | 1 |
| fasim_sim_recovery_learned_detector_feature_expansion_current_guard_false_negatives | 0 |
| fasim_sim_recovery_learned_detector_feature_expansion_learned_shadow_recall | 55.555556 |
| fasim_sim_recovery_learned_detector_feature_expansion_learned_shadow_precision | 38.461538 |
| fasim_sim_recovery_learned_detector_feature_expansion_false_positives | 8 |
| fasim_sim_recovery_learned_detector_feature_expansion_false_negatives | 4 |
| fasim_sim_recovery_learned_detector_feature_expansion_selected_threshold | -0.608670 |
| fasim_sim_recovery_learned_detector_feature_expansion_candidate_eligible_recall | 55.555556 |
| fasim_sim_recovery_learned_detector_feature_expansion_candidate_eligible_precision | 38.461538 |
| fasim_sim_recovery_learned_detector_feature_expansion_candidate_eligible_false_positives | 8 |
| fasim_sim_recovery_learned_detector_feature_expansion_candidate_eligible_false_negatives | 4 |
| fasim_sim_recovery_learned_detector_feature_expansion_beats_current_guard_on_validation | 0 |
| fasim_sim_recovery_learned_detector_feature_expansion_decision | pause_model_path_keep_guard |
| fasim_sim_recovery_learned_detector_feature_expansion_production_model | 0 |
| fasim_sim_recovery_learned_detector_feature_expansion_sim_labels_runtime_inputs | 0 |
| fasim_sim_recovery_learned_detector_feature_expansion_runtime_behavior_changed | 0 |
| fasim_sim_recovery_learned_detector_feature_expansion_current_split_train_positive | 15 |
| fasim_sim_recovery_learned_detector_feature_expansion_current_split_train_negative | 25 |
| fasim_sim_recovery_learned_detector_feature_expansion_current_split_validation_positive | 2 |
| fasim_sim_recovery_learned_detector_feature_expansion_current_split_validation_negative | 2 |
| fasim_sim_recovery_learned_detector_feature_expansion_current_split_selected_threshold | 1.415287 |
| fasim_sim_recovery_learned_detector_feature_expansion_current_split_current_guard_precision | 100.000000 |
| fasim_sim_recovery_learned_detector_feature_expansion_current_split_current_guard_recall | 100.000000 |
| fasim_sim_recovery_learned_detector_feature_expansion_current_split_learned_shadow_precision | 66.666667 |
| fasim_sim_recovery_learned_detector_feature_expansion_current_split_learned_shadow_recall | 100.000000 |
| fasim_sim_recovery_learned_detector_feature_expansion_current_split_candidate_eligible_precision | 66.666667 |
| fasim_sim_recovery_learned_detector_feature_expansion_current_split_candidate_eligible_recall | 100.000000 |
| fasim_sim_recovery_learned_detector_feature_expansion_current_split_false_positives | 1 |
| fasim_sim_recovery_learned_detector_feature_expansion_current_split_false_negatives | 0 |
| fasim_sim_recovery_learned_detector_feature_expansion_workload_heldout_train_positive | 8 |
| fasim_sim_recovery_learned_detector_feature_expansion_workload_heldout_train_negative | 10 |
| fasim_sim_recovery_learned_detector_feature_expansion_workload_heldout_validation_positive | 9 |
| fasim_sim_recovery_learned_detector_feature_expansion_workload_heldout_validation_negative | 17 |
| fasim_sim_recovery_learned_detector_feature_expansion_workload_heldout_selected_threshold | -0.608670 |
| fasim_sim_recovery_learned_detector_feature_expansion_workload_heldout_current_guard_precision | 90.000000 |
| fasim_sim_recovery_learned_detector_feature_expansion_workload_heldout_current_guard_recall | 100.000000 |
| fasim_sim_recovery_learned_detector_feature_expansion_workload_heldout_learned_shadow_precision | 38.461538 |
| fasim_sim_recovery_learned_detector_feature_expansion_workload_heldout_learned_shadow_recall | 55.555556 |
| fasim_sim_recovery_learned_detector_feature_expansion_workload_heldout_candidate_eligible_precision | 38.461538 |
| fasim_sim_recovery_learned_detector_feature_expansion_workload_heldout_candidate_eligible_recall | 55.555556 |
| fasim_sim_recovery_learned_detector_feature_expansion_workload_heldout_false_positives | 8 |
| fasim_sim_recovery_learned_detector_feature_expansion_workload_heldout_false_negatives | 4 |
| fasim_sim_recovery_learned_detector_feature_expansion_family_heldout_train_positive | 8 |
| fasim_sim_recovery_learned_detector_feature_expansion_family_heldout_train_negative | 12 |
| fasim_sim_recovery_learned_detector_feature_expansion_family_heldout_validation_positive | 9 |
| fasim_sim_recovery_learned_detector_feature_expansion_family_heldout_validation_negative | 15 |
| fasim_sim_recovery_learned_detector_feature_expansion_family_heldout_selected_threshold | -0.433741 |
| fasim_sim_recovery_learned_detector_feature_expansion_family_heldout_current_guard_precision | 100.000000 |
| fasim_sim_recovery_learned_detector_feature_expansion_family_heldout_current_guard_recall | 100.000000 |
| fasim_sim_recovery_learned_detector_feature_expansion_family_heldout_learned_shadow_precision | 66.666667 |
| fasim_sim_recovery_learned_detector_feature_expansion_family_heldout_learned_shadow_recall | 22.222222 |
| fasim_sim_recovery_learned_detector_feature_expansion_family_heldout_candidate_eligible_precision | 66.666667 |
| fasim_sim_recovery_learned_detector_feature_expansion_family_heldout_candidate_eligible_recall | 22.222222 |
| fasim_sim_recovery_learned_detector_feature_expansion_family_heldout_false_positives | 1 |
| fasim_sim_recovery_learned_detector_feature_expansion_family_heldout_false_negatives | 7 |
| fasim_sim_recovery_learned_detector_feature_expansion_expanded_feature_count | 19 |
| fasim_sim_recovery_learned_detector_feature_expansion_expanded_features | score,Nt,identity,interval_length,local_rank,family_rank,overlap_degree,distance_to_fasim_boundary,box_size,family_size,family_span,interval_overlap_ratio,dominance_margin,score_margin,Nt_margin,near_threshold_density,peak_count,second_peak_gap,plateau_width |
| fasim_sim_recovery_learned_detector_feature_expansion_new_feature_count | 10 |
| fasim_sim_recovery_learned_detector_feature_expansion_new_features | family_size,family_span,interval_overlap_ratio,dominance_margin,score_margin,Nt_margin,near_threshold_density,peak_count,second_peak_gap,plateau_width |
| fasim_sim_recovery_learned_detector_feature_expansion_baseline_expanded_shadow_recall | 77.777778 |
| fasim_sim_recovery_learned_detector_feature_expansion_baseline_expanded_shadow_precision | 50.000000 |
| fasim_sim_recovery_learned_detector_feature_expansion_baseline_current_guard_recall | 100.000000 |
| fasim_sim_recovery_learned_detector_feature_expansion_baseline_current_guard_precision | 90.000000 |

## Expanded Feature List

| Feature | Source |
| --- | --- |
| score | existing_baseline |
| Nt | existing_baseline |
| identity | existing_baseline |
| interval_length | existing_baseline |
| local_rank | existing_baseline |
| family_rank | existing_baseline |
| overlap_degree | existing_baseline |
| distance_to_fasim_boundary | existing_baseline |
| box_size | existing_baseline |
| family_size | expanded_fasim_visible |
| family_span | expanded_fasim_visible |
| interval_overlap_ratio | expanded_fasim_visible |
| dominance_margin | expanded_fasim_visible |
| score_margin | expanded_fasim_visible |
| Nt_margin | expanded_fasim_visible |
| near_threshold_density | expanded_fasim_visible |
| peak_count | expanded_fasim_visible |
| second_peak_gap | expanded_fasim_visible |
| plateau_width | expanded_fasim_visible |

## Split Evaluation

| Policy | Train + | Train - | Validation + | Validation - | Degenerate | Current guard precision | Current guard recall | Learned precision | Learned recall | Candidate precision | Candidate recall | Threshold |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| current_split | 15 | 25 | 2 | 2 | 0 | 100.000000 | 100.000000 | 66.666667 | 100.000000 | 66.666667 | 100.000000 | 1.415287 |
| workload_heldout | 8 | 10 | 9 | 17 | 0 | 90.000000 | 100.000000 | 38.461538 | 55.555556 | 38.461538 | 55.555556 | -0.608670 |
| family_heldout | 8 | 12 | 9 | 15 | 0 | 100.000000 | 100.000000 | 66.666667 | 22.222222 | 66.666667 | 22.222222 | -0.433741 |

## Baseline Comparison

| Source | Current guard precision | Current guard recall | Learned precision | Learned recall | Rows |
| --- | ---: | ---: | ---: | ---: | ---: |
| #87_expanded_shadow | 90.000000 | 100.000000 | 50.000000 | 77.777778 | 44 |
| feature_expansion_primary | 90.000000 | 100.000000 | 38.461538 | 55.555556 | 44 |

## Decision

Decision: `pause_model_path_keep_guard`.

The decision remains based on candidate-eligible held-out metrics, not oracle-only target rows. If the expanded feature shadow still cannot beat the current hand-written guard, the learned-detector model path should pause while the current guard remains the stronger detector.

## Scope

```text
Production model added: no
Fasim runtime changed: no
SIM-close runtime changed: no
Scoring/threshold/non-overlap behavior changed: no
GPU/filter behavior changed: no
SIM labels used as runtime input: no
Recommended/default SIM-close: no
```

No production model is trained or loaded. SIM labels remain offline labels only and must not be used as runtime detector inputs, guard inputs, replacement inputs, or output ordering inputs.
