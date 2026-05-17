# Fasim SIM-Close Learned Detector Precision Sweep

## Precision-Constrained Threshold Sweep

This report sweeps thresholds for the dependency-free learned/ranked detector shadow on the #92 large-corpus workload-heldout split. The thresholds are validation-label characterizations only; they are not runtime thresholds and are not production detector inputs.

| Metric | Value |
| --- | --- |
| fasim_sim_recovery_learned_detector_precision_sweep_enabled | 1 |
| fasim_sim_recovery_learned_detector_precision_sweep_rows | 140 |
| fasim_sim_recovery_learned_detector_precision_sweep_positive_rows | 73 |
| fasim_sim_recovery_learned_detector_precision_sweep_negative_rows | 67 |
| fasim_sim_recovery_learned_detector_precision_sweep_source_rows | 254 |
| fasim_sim_recovery_learned_detector_precision_sweep_workload_count | 21 |
| fasim_sim_recovery_learned_detector_precision_sweep_validate_supported_workload_count | 19 |
| fasim_sim_recovery_learned_detector_precision_sweep_hard_negative_sources | executor_candidate_non_sim:9,extra_vs_sim_candidate:2,fasim_supported_non_sim:46,near_threshold_rejected_candidate:7,no_legacy_sim_records_proxy:3 |
| fasim_sim_recovery_learned_detector_precision_sweep_hard_negative_source_count | 5 |
| fasim_sim_recovery_learned_detector_precision_sweep_evaluation_policy | workload_heldout |
| fasim_sim_recovery_learned_detector_precision_sweep_train_positive | 48 |
| fasim_sim_recovery_learned_detector_precision_sweep_train_negative | 37 |
| fasim_sim_recovery_learned_detector_precision_sweep_validation_positive | 25 |
| fasim_sim_recovery_learned_detector_precision_sweep_validation_negative | 30 |
| fasim_sim_recovery_learned_detector_precision_sweep_workload_heldout_degenerate | 0 |
| fasim_sim_recovery_learned_detector_precision_sweep_sweep_threshold_count | 57 |
| fasim_sim_recovery_learned_detector_precision_sweep_selected_threshold | -1.344861 |
| fasim_sim_recovery_learned_detector_precision_sweep_current_guard_recall | 44.000000 |
| fasim_sim_recovery_learned_detector_precision_sweep_current_guard_precision | 91.666667 |
| fasim_sim_recovery_learned_detector_precision_sweep_current_guard_false_positives | 1 |
| fasim_sim_recovery_learned_detector_precision_sweep_current_guard_false_negatives | 14 |
| fasim_sim_recovery_learned_detector_precision_sweep_learned_shadow_recall | 60.000000 |
| fasim_sim_recovery_learned_detector_precision_sweep_learned_shadow_precision | 57.692308 |
| fasim_sim_recovery_learned_detector_precision_sweep_learned_shadow_false_positives | 11 |
| fasim_sim_recovery_learned_detector_precision_sweep_learned_shadow_false_negatives | 10 |
| fasim_sim_recovery_learned_detector_precision_sweep_false_positives_by_negative_source | none |
| fasim_sim_recovery_learned_detector_precision_sweep_false_negatives_by_workload | marmoset_extra_ENSG00000234936_1:1,marmoset_extra_ENSG00000244558_1:4,marmoset_extra_ENSG00000259912_1:7,marmoset_extra_ENSG00000269473_1:1,marmoset_extra_ENSG00000273492_1:3,tiny_validate:9 |
| fasim_sim_recovery_learned_detector_precision_sweep_decision | pause_model_path_keep_guard |
| fasim_sim_recovery_learned_detector_precision_sweep_production_model | 0 |
| fasim_sim_recovery_learned_detector_precision_sweep_sim_labels_runtime_inputs | 0 |
| fasim_sim_recovery_learned_detector_precision_sweep_runtime_behavior_changed | 0 |
| fasim_sim_recovery_learned_detector_precision_sweep_model_training_added | 0 |
| fasim_sim_recovery_learned_detector_precision_sweep_deep_learning_dependency | 0 |
| fasim_sim_recovery_learned_detector_precision_sweep_recommended_default_sim_close | 0 |
| fasim_sim_recovery_learned_detector_precision_sweep_max_recall_at_precision_90 | 0.000000 |
| fasim_sim_recovery_learned_detector_precision_sweep_precision_at_precision_90 | 0.000000 |
| fasim_sim_recovery_learned_detector_precision_sweep_threshold_at_precision_90 | none |
| fasim_sim_recovery_learned_detector_precision_sweep_false_positives_at_precision_90 | 0 |
| fasim_sim_recovery_learned_detector_precision_sweep_false_negatives_at_precision_90 | 25 |
| fasim_sim_recovery_learned_detector_precision_sweep_max_recall_at_precision_95 | 0.000000 |
| fasim_sim_recovery_learned_detector_precision_sweep_precision_at_precision_95 | 0.000000 |
| fasim_sim_recovery_learned_detector_precision_sweep_threshold_at_precision_95 | none |
| fasim_sim_recovery_learned_detector_precision_sweep_false_positives_at_precision_95 | 0 |
| fasim_sim_recovery_learned_detector_precision_sweep_false_negatives_at_precision_95 | 25 |
| fasim_sim_recovery_learned_detector_precision_sweep_max_recall_at_precision_99 | 0.000000 |
| fasim_sim_recovery_learned_detector_precision_sweep_precision_at_precision_99 | 0.000000 |
| fasim_sim_recovery_learned_detector_precision_sweep_threshold_at_precision_99 | none |
| fasim_sim_recovery_learned_detector_precision_sweep_false_positives_at_precision_99 | 0 |
| fasim_sim_recovery_learned_detector_precision_sweep_false_negatives_at_precision_99 | 25 |
| fasim_sim_recovery_learned_detector_precision_sweep_current_guard_only_selected | 12 |
| fasim_sim_recovery_learned_detector_precision_sweep_current_guard_only_true_positive | 11 |
| fasim_sim_recovery_learned_detector_precision_sweep_current_guard_only_false_positive | 1 |
| fasim_sim_recovery_learned_detector_precision_sweep_current_guard_only_false_negative | 14 |
| fasim_sim_recovery_learned_detector_precision_sweep_current_guard_only_precision | 91.666667 |
| fasim_sim_recovery_learned_detector_precision_sweep_current_guard_only_recall | 44.000000 |
| fasim_sim_recovery_learned_detector_precision_sweep_learned_precision_90_only_selected | 0 |
| fasim_sim_recovery_learned_detector_precision_sweep_learned_precision_90_only_true_positive | 0 |
| fasim_sim_recovery_learned_detector_precision_sweep_learned_precision_90_only_false_positive | 0 |
| fasim_sim_recovery_learned_detector_precision_sweep_learned_precision_90_only_false_negative | 25 |
| fasim_sim_recovery_learned_detector_precision_sweep_learned_precision_90_only_precision | 0.000000 |
| fasim_sim_recovery_learned_detector_precision_sweep_learned_precision_90_only_recall | 0.000000 |
| fasim_sim_recovery_learned_detector_precision_sweep_hybrid_or_precision_90_selected | 12 |
| fasim_sim_recovery_learned_detector_precision_sweep_hybrid_or_precision_90_true_positive | 11 |
| fasim_sim_recovery_learned_detector_precision_sweep_hybrid_or_precision_90_false_positive | 1 |
| fasim_sim_recovery_learned_detector_precision_sweep_hybrid_or_precision_90_false_negative | 14 |
| fasim_sim_recovery_learned_detector_precision_sweep_hybrid_or_precision_90_precision | 91.666667 |
| fasim_sim_recovery_learned_detector_precision_sweep_hybrid_or_precision_90_recall | 44.000000 |
| fasim_sim_recovery_learned_detector_precision_sweep_hybrid_and_precision_90_selected | 0 |
| fasim_sim_recovery_learned_detector_precision_sweep_hybrid_and_precision_90_true_positive | 0 |
| fasim_sim_recovery_learned_detector_precision_sweep_hybrid_and_precision_90_false_positive | 0 |
| fasim_sim_recovery_learned_detector_precision_sweep_hybrid_and_precision_90_false_negative | 25 |
| fasim_sim_recovery_learned_detector_precision_sweep_hybrid_and_precision_90_precision | 0.000000 |
| fasim_sim_recovery_learned_detector_precision_sweep_hybrid_and_precision_90_recall | 0.000000 |

## Precision Targets

| Precision target | Threshold | Precision | Max recall | False + | False - |
| ---: | ---: | ---: | ---: | ---: | ---: |
| >= 90% | none | 0.000000 | 0.000000 | 0 | 25 |
| >= 95% | none | 0.000000 | 0.000000 | 0 | 25 |
| >= 99% | none | 0.000000 | 0.000000 | 0 | 25 |

## Precision/Recall Curve

| Threshold | Selected | Precision | Recall | False + | False - |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 3.747075 | 0 | 0.000000 | 0.000000 | 0 | 25 |
| 2.747075 | 1 | 0.000000 | 0.000000 | 1 | 25 |
| 2.504021 | 2 | 50.000000 | 4.000000 | 1 | 24 |
| 2.495647 | 3 | 33.333333 | 4.000000 | 2 | 24 |
| 2.391892 | 4 | 50.000000 | 8.000000 | 2 | 23 |
| 2.250182 | 5 | 60.000000 | 12.000000 | 2 | 22 |
| 2.138629 | 6 | 50.000000 | 12.000000 | 3 | 22 |
| 2.134110 | 7 | 57.142857 | 16.000000 | 3 | 21 |
| 1.012855 | 8 | 50.000000 | 16.000000 | 4 | 21 |
| 0.883262 | 9 | 44.444444 | 16.000000 | 5 | 21 |
| 0.803258 | 10 | 40.000000 | 16.000000 | 6 | 21 |
| 0.793473 | 11 | 36.363636 | 16.000000 | 7 | 21 |
| 0.735951 | 12 | 33.333333 | 16.000000 | 8 | 21 |
| 0.702194 | 13 | 38.461538 | 20.000000 | 8 | 20 |
| 0.637707 | 14 | 42.857143 | 24.000000 | 8 | 19 |
| 0.515448 | 15 | 46.666667 | 28.000000 | 8 | 18 |
| 0.018809 | 16 | 50.000000 | 32.000000 | 8 | 17 |
| -0.096250 | 17 | 52.941176 | 36.000000 | 8 | 16 |
| -0.191908 | 18 | 55.555556 | 40.000000 | 8 | 15 |
| -0.354982 | 19 | 57.894737 | 44.000000 | 8 | 14 |
| -0.667912 | 20 | 55.000000 | 44.000000 | 9 | 14 |
| -0.745369 | 21 | 57.142857 | 48.000000 | 9 | 13 |
| -0.790937 | 22 | 54.545455 | 48.000000 | 10 | 13 |
| -0.852064 | 23 | 52.173913 | 48.000000 | 11 | 13 |
| -0.899338 | 24 | 54.166667 | 52.000000 | 11 | 12 |
| -1.068181 | 25 | 56.000000 | 56.000000 | 11 | 11 |
| -1.230583 | 26 | 57.692308 | 60.000000 | 11 | 10 |
| -1.351296 | 27 | 55.555556 | 60.000000 | 12 | 10 |
| -1.385224 | 28 | 53.571429 | 60.000000 | 13 | 10 |
| -1.448420 | 29 | 55.172414 | 64.000000 | 13 | 9 |
| -1.450873 | 30 | 56.666667 | 68.000000 | 13 | 8 |
| -1.460499 | 31 | 54.838710 | 68.000000 | 14 | 8 |
| -1.474826 | 32 | 56.250000 | 72.000000 | 14 | 7 |
| -1.562014 | 33 | 54.545455 | 72.000000 | 15 | 7 |
| -1.579662 | 34 | 55.882353 | 76.000000 | 15 | 6 |
| -1.641721 | 35 | 57.142857 | 80.000000 | 15 | 5 |
| -1.647950 | 36 | 55.555556 | 80.000000 | 16 | 5 |
| -1.711025 | 37 | 54.054054 | 80.000000 | 17 | 5 |
| -1.762393 | 38 | 52.631579 | 80.000000 | 18 | 5 |
| -1.777183 | 39 | 53.846154 | 84.000000 | 18 | 4 |
| -1.928449 | 40 | 55.000000 | 88.000000 | 18 | 3 |
| -2.118500 | 41 | 53.658537 | 88.000000 | 19 | 3 |
| -2.140014 | 42 | 52.380952 | 88.000000 | 20 | 3 |
| -2.140737 | 43 | 53.488372 | 92.000000 | 20 | 2 |
| -2.301370 | 44 | 52.272727 | 92.000000 | 21 | 2 |
| -2.415105 | 45 | 51.111111 | 92.000000 | 22 | 2 |
| -2.816545 | 46 | 50.000000 | 92.000000 | 23 | 2 |
| -2.853256 | 47 | 48.936170 | 92.000000 | 24 | 2 |
| -2.935705 | 48 | 47.916667 | 92.000000 | 25 | 2 |
| -3.139098 | 49 | 46.938776 | 92.000000 | 26 | 2 |
| -3.225205 | 50 | 46.000000 | 92.000000 | 27 | 2 |
| -3.307958 | 51 | 47.058824 | 96.000000 | 27 | 1 |
| -3.554238 | 52 | 46.153846 | 96.000000 | 28 | 1 |
| -3.867236 | 53 | 47.169811 | 100.000000 | 28 | 0 |
| -4.709991 | 54 | 46.296296 | 100.000000 | 29 | 0 |
| -5.223279 | 55 | 45.454545 | 100.000000 | 30 | 0 |
| -6.223279 | 55 | 45.454545 | 100.000000 | 30 | 0 |

## Hybrid Policies

`learned_precision_90_only` uses the best offline learned threshold with precision >= 90%. Hybrid policies are offline comparisons against the current hand-written guard and do not change runtime behavior.

| Policy | Selected | Precision | Recall | False + | False - |
| --- | ---: | ---: | ---: | ---: | ---: |
| current_guard_only | 12 | 91.666667 | 44.000000 | 1 | 14 |
| learned_precision_90_only | 0 | 0.000000 | 0.000000 | 0 | 25 |
| hybrid_or_precision_90 | 12 | 91.666667 | 44.000000 | 1 | 14 |
| hybrid_and_precision_90 | 0 | 0.000000 | 0.000000 | 0 | 25 |

## Error Attribution

| Error bucket | Rows |
| --- | --- |
| false_positives_by_negative_source | none |
| false_negatives_by_workload | marmoset_extra_ENSG00000234936_1:1,marmoset_extra_ENSG00000244558_1:4,marmoset_extra_ENSG00000259912_1:7,marmoset_extra_ENSG00000269473_1:1,marmoset_extra_ENSG00000273492_1:3,tiny_validate:9 |

## Decision

Decision: `pause_model_path_keep_guard`.

If learned or hybrid policy beats the current guard at precision >= 90%, the learned-detector research line remains worth offline follow-up. If recall falls below the current guard once precision is constrained, keep the hand-written guard and collect better signal.

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
