# Fasim SIM-Recovery Risk Detector

Base branch:

```text
fasim-local-sim-recovery-shadow
```

This report evaluates an independent Fasim-visible risk detector. Box selection uses only Fasim output record family/orientation and coordinates. This conservative baseline selects every Fasim output record as a local risk region; it does not use SIM-only record coordinates, taxonomy labels, legacy SIM output, or oracle boxes for selection.

Legacy `-F` SIM output is used only after detector selection to measure coverage of SIM-only records. The detector is diagnostic-only: it does not change Fasim output and does not run bounded local SIM recovery.

| Setting | Value |
| --- | --- |
| profile_set | representative |
| detector_mode | all_fasim_records_baseline |
| box_source | Fasim output records only |
| margin_bp | 32 |
| merge_gap_bp | 32 |
| output_mutations_expected | 0 |

## Workload Summary

| Workload | Mode | Boxes | Cells | Full-search cells | Cell fraction | SIM-only | Covered | Uncovered | Recall | False-positive boxes | Output mutations |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| tiny | all_fasim_records_baseline | 6 | 95812 | 12277192 | 0.78% | 9 | 9 | 0 | 100.00% | 0 | 0 |
| medium_synthetic | all_fasim_records_baseline | 48 | 766496 | 98217536 | 0.78% | 72 | 72 | 0 | 100.00% | 0 | 0 |
| window_heavy_synthetic | all_fasim_records_baseline | 192 | 3065984 | 392870144 | 0.78% | 288 | 288 | 0 | 100.00% | 0 | 0 |

## Category Summary

| Category | SIM-only | Covered | Recall |
| --- | --- | --- | --- |
| long_hit_internal_peak | 41 | 41 | 100.00% |
| nested_alignment | 123 | 123 | 100.00% |
| nonoverlap_conflict | 0 | 0 | 0.00% |
| overlap_chain | 205 | 205 | 100.00% |
| tie_near_tie | 0 | 0 | 0.00% |
| threshold_near | 0 | 0 | 0.00% |
| unknown | 0 | 0 | 0.00% |

## Aggregate

| Metric | Value |
| --- | --- |
| fasim_sim_recovery_risk_detector_enabled | 1 |
| fasim_sim_recovery_risk_detector_boxes | 246 |
| fasim_sim_recovery_risk_detector_cells | 3928292 |
| fasim_sim_recovery_risk_detector_full_search_cells | 503364872 |
| fasim_sim_recovery_risk_detector_cell_fraction | 0.78% |
| fasim_sim_recovery_risk_detector_seconds | 0.008193 |
| fasim_sim_recovery_risk_detector_sim_only_records | 369 |
| fasim_sim_recovery_risk_detector_supported_sim_only_records | 369 |
| fasim_sim_recovery_risk_detector_unsupported_sim_only_records | 0 |
| fasim_sim_recovery_risk_detector_recall | 100.00% |
| fasim_sim_recovery_risk_detector_candidate_records | 369 |
| fasim_sim_recovery_risk_detector_false_positive_boxes | 0 |
| fasim_sim_recovery_risk_detector_output_mutations | 0 |

## Decision

The Fasim-visible detector covers most SIM-only records while keeping cell fraction small. A bounded local SIM executor shadow is a plausible next PR.

Forbidden-scope check:

```text
SIM-only coordinates used for selection: no
Legacy SIM output used for selection: no
Oracle boxes used for selection: no
Fasim output change: no
Recovered records added to output: no
Scoring/threshold/non-overlap behavior change: no
GPU/filter behavior change: no
Production accuracy claim: no
```
