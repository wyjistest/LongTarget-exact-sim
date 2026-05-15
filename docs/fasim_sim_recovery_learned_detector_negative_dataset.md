# Fasim SIM-Close Learned Detector Negative Dataset

## Negative / Contrastive Dataset

This report builds an offline trainable contrastive table from the learned-detector TSV. It adds positives plus hard negatives for future SIM-close detector research.

Input dataset: `/data/wenyujianData/LongTarget-exact-sim/.worktrees/fasim-sim-recovery-learned-detector-negative-dataset/.tmp/fasim_sim_recovery_learned_detector_negative_dataset/learned_detector_dataset.tsv`
Output TSV: `/data/wenyujianData/LongTarget-exact-sim/.worktrees/fasim-sim-recovery-learned-detector-negative-dataset/.tmp/fasim_sim_recovery_learned_detector_negative_dataset/negative_dataset.tsv`

| Metric | Value |
| --- | --- |
| fasim_sim_recovery_learned_detector_negative_dataset_enabled | 1 |
| fasim_sim_recovery_learned_detector_negative_dataset_source_rows | 118 |
| fasim_sim_recovery_learned_detector_negative_dataset_rows | 65 |
| fasim_sim_recovery_learned_detector_negative_dataset_positive_rows | 40 |
| fasim_sim_recovery_learned_detector_negative_dataset_negative_rows | 25 |
| fasim_sim_recovery_learned_detector_negative_dataset_learnable_two_class | 1 |
| fasim_sim_recovery_learned_detector_negative_dataset_class_balance | 0.625000 |
| fasim_sim_recovery_learned_detector_negative_dataset_train_positive | 22 |
| fasim_sim_recovery_learned_detector_negative_dataset_train_negative | 13 |
| fasim_sim_recovery_learned_detector_negative_dataset_validation_positive | 18 |
| fasim_sim_recovery_learned_detector_negative_dataset_validation_negative | 12 |
| fasim_sim_recovery_learned_detector_negative_dataset_hard_negative_sources | fasim_supported_non_sim:25 |
| fasim_sim_recovery_learned_detector_negative_dataset_baseline_guard_recall_vs_sim | 35.000000 |
| fasim_sim_recovery_learned_detector_negative_dataset_baseline_guard_precision | 100.000000 |
| fasim_sim_recovery_learned_detector_negative_dataset_production_model | 0 |
| fasim_sim_recovery_learned_detector_negative_dataset_sim_labels_runtime_inputs | 0 |
| fasim_sim_recovery_learned_detector_negative_dataset_runtime_behavior_changed | 0 |

## Hard Negative Sources

| Source | Rows |
| --- | ---: |
| fasim_supported_non_sim | 25 |

## Split Counts

| Split | Positive | Negative |
| --- | ---: | ---: |
| train | 22 | 13 |
| validation | 18 | 12 |

## Interpretation

Positive rows include executor candidates that match legacy SIM and SIM-record target positives not already represented by executor candidates. The latter keep not-box-covered positives visible for future detector work.

Hard negatives include executor candidates or accepted candidates that do not match SIM, Fasim-supported records that are not SIM records, and no-legacy-SIM proxy negatives only when such rows are present.

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
