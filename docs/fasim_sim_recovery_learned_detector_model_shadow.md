# Fasim SIM-Close Learned Detector Model Shadow

## Offline Model Shadow

This report trains a dependency-free ranking/threshold shadow over the offline positive + hard-negative dataset. It is evaluated on the exported train/validation split and does not add a runtime model.

Input negative dataset: `/data/wenyujianData/LongTarget-exact-sim/.worktrees/fasim-sim-recovery-learned-detector-model-shadow/.tmp/fasim_sim_recovery_learned_detector_model_shadow/negative_dataset.tsv`
Input source learned dataset: `/data/wenyujianData/LongTarget-exact-sim/.worktrees/fasim-sim-recovery-learned-detector-model-shadow/.tmp/fasim_sim_recovery_learned_detector_model_shadow/learned_detector_dataset.tsv`

| Metric | Value |
| --- | --- |
| fasim_sim_recovery_learned_detector_model_shadow_enabled | 1 |
| fasim_sim_recovery_learned_detector_model_shadow_rows | 65 |
| fasim_sim_recovery_learned_detector_model_shadow_positive_rows | 40 |
| fasim_sim_recovery_learned_detector_model_shadow_negative_rows | 25 |
| fasim_sim_recovery_learned_detector_model_shadow_learnable_two_class | 1 |
| fasim_sim_recovery_learned_detector_model_shadow_evaluation_mode | heldout_split |
| fasim_sim_recovery_learned_detector_model_shadow_model | standardized_mean_difference_threshold |
| fasim_sim_recovery_learned_detector_model_shadow_heavy_ml_dependency | 0 |
| fasim_sim_recovery_learned_detector_model_shadow_features | score,Nt,identity,interval_length,local_rank,family_rank,overlap_degree,distance_to_fasim_boundary,box_size |
| fasim_sim_recovery_learned_detector_model_shadow_train_positive | 22 |
| fasim_sim_recovery_learned_detector_model_shadow_train_negative | 13 |
| fasim_sim_recovery_learned_detector_model_shadow_validation_positive | 18 |
| fasim_sim_recovery_learned_detector_model_shadow_validation_negative | 12 |
| fasim_sim_recovery_learned_detector_model_shadow_selected_threshold | -0.496593 |
| fasim_sim_recovery_learned_detector_model_shadow_train_selected | 22 |
| fasim_sim_recovery_learned_detector_model_shadow_train_precision | 100.000000 |
| fasim_sim_recovery_learned_detector_model_shadow_train_recall | 100.000000 |
| fasim_sim_recovery_learned_detector_model_shadow_train_false_positives | 0 |
| fasim_sim_recovery_learned_detector_model_shadow_train_false_negatives | 0 |
| fasim_sim_recovery_learned_detector_model_shadow_validation_selected | 15 |
| fasim_sim_recovery_learned_detector_model_shadow_validation_precision | 100.000000 |
| fasim_sim_recovery_learned_detector_model_shadow_validation_recall | 83.333333 |
| fasim_sim_recovery_learned_detector_model_shadow_validation_false_positives | 0 |
| fasim_sim_recovery_learned_detector_model_shadow_validation_false_negatives | 3 |
| fasim_sim_recovery_learned_detector_model_shadow_validation_candidate_eligible_selected | 10 |
| fasim_sim_recovery_learned_detector_model_shadow_validation_candidate_eligible_true_positive | 10 |
| fasim_sim_recovery_learned_detector_model_shadow_validation_candidate_eligible_false_positive | 0 |
| fasim_sim_recovery_learned_detector_model_shadow_validation_candidate_eligible_false_negative_vs_all_positives | 8 |
| fasim_sim_recovery_learned_detector_model_shadow_validation_candidate_eligible_precision | 100.000000 |
| fasim_sim_recovery_learned_detector_model_shadow_validation_candidate_eligible_recall_vs_all_positives | 55.555556 |
| fasim_sim_recovery_learned_detector_model_shadow_validation_target_rows | 8 |
| fasim_sim_recovery_learned_detector_model_shadow_validation_target_rows_selected | 5 |
| fasim_sim_recovery_learned_detector_model_shadow_current_guard_train_precision | 100.000000 |
| fasim_sim_recovery_learned_detector_model_shadow_current_guard_train_recall | 50.000000 |
| fasim_sim_recovery_learned_detector_model_shadow_current_guard_train_false_positives | 0 |
| fasim_sim_recovery_learned_detector_model_shadow_current_guard_train_false_negatives | 11 |
| fasim_sim_recovery_learned_detector_model_shadow_current_guard_validation_precision | 100.000000 |
| fasim_sim_recovery_learned_detector_model_shadow_current_guard_validation_recall | 16.666667 |
| fasim_sim_recovery_learned_detector_model_shadow_current_guard_validation_false_positives | 0 |
| fasim_sim_recovery_learned_detector_model_shadow_current_guard_validation_false_negatives | 15 |
| fasim_sim_recovery_learned_detector_model_shadow_beats_current_guard_on_validation | 1 |
| fasim_sim_recovery_learned_detector_model_shadow_hard_negative_sources | fasim_supported_non_sim:25 |
| fasim_sim_recovery_learned_detector_model_shadow_production_model | 0 |
| fasim_sim_recovery_learned_detector_model_shadow_sim_labels_runtime_inputs | 0 |
| fasim_sim_recovery_learned_detector_model_shadow_runtime_behavior_changed | 0 |

## Feature List

| Feature | Weight |
| --- | ---: |
| score | 0.072342 |
| Nt | -0.322370 |
| identity | -0.017423 |
| interval_length | -0.178363 |
| local_rank | 1.837024 |
| family_rank | -0.185339 |
| overlap_degree | 1.222942 |
| distance_to_fasim_boundary | 0.385303 |
| box_size | -0.404594 |

## Split Counts

| Split | Positive | Negative |
| --- | ---: | ---: |
| train | 22 | 13 |
| validation | 18 | 12 |

## Held-out Validation

| Method | Precision | Recall | False positives | False negatives |
| --- | ---: | ---: | ---: | ---: |
| current_guard | 100.000000 | 16.666667 | 0 | 15 |
| learned_shadow_all_rows | 100.000000 | 83.333333 | 0 | 3 |
| learned_shadow_candidate_eligible | 100.000000 | 55.555556 | 0 | 8 |

## Target Row Audit

| Metric | Value |
| --- | ---: |
| validation target rows | 8 |
| validation target rows selected | 5 |

## Interpretation

`evaluation_mode=heldout_split` means the selected threshold is fitted only on rows marked `split=train` and scored on rows marked `split=validation`.

This is still a small offline feasibility check. It must not be read as held-out production accuracy, especially when hard negatives come from a narrow source mix.

`learned_shadow_all_rows` includes `sim_record_target_positive` rows, which are offline oracle target rows used to study not-box-covered positives. `beats_current_guard_on_validation` is therefore computed from `learned_shadow_candidate_eligible`, not from the all-row target view.

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
