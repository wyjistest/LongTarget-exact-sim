# Fasim SIM-Close Recovery Real Mode Characterization

Base branch:

```text
fasim-sim-recovery-real-mode-skeleton
```

This report characterizes the default-off `FASIM_SIM_RECOVERY=1` skeleton. It adds no new recovery logic and does not change scoring, threshold, non-overlap, GPU, filter, or default fast-mode behavior.

| Setting | Value |
| --- | --- |
| profile_set | representative |
| repeat | 3 |
| fast_mode | default Fasim exactness profile |
| sim_close_mode | FASIM_SIM_RECOVERY=1 |
| validate_mode | FASIM_SIM_RECOVERY=1 FASIM_SIM_RECOVERY_VALIDATE=1 |
| expected_fast_digest | sha256:fbcd7908110386e90c452008c872a8b32f775656042e8723a258f463f5ebeff6 |

## Run Summary

| Run | Fast seconds | Fast digest | SIM-close digest | Validate digest | Output records | Recall vs SIM | Precision vs SIM | Extra vs SIM | Overlap conflicts | Fallbacks | SIM-close wall seconds | Validate wall seconds |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.055319 | sha256:fbcd7908110386e90c452008c872a8b32f775656042e8723a258f463f5ebeff6 | sha256:8e6bd08f6093931e27fc6e51a15f00239d1a14de32973f1068c29ddb9b60c1f1 | sha256:8e6bd08f6093931e27fc6e51a15f00239d1a14de32973f1068c29ddb9b60c1f1 | 410 | 100.000000 | 90.000000 | 41 | 164 | 0 | 83.194004 | 83.361679 |
| 2 | 0.036704 | sha256:fbcd7908110386e90c452008c872a8b32f775656042e8723a258f463f5ebeff6 | sha256:8e6bd08f6093931e27fc6e51a15f00239d1a14de32973f1068c29ddb9b60c1f1 | sha256:8e6bd08f6093931e27fc6e51a15f00239d1a14de32973f1068c29ddb9b60c1f1 | 410 | 100.000000 | 90.000000 | 41 | 164 | 0 | 83.369277 | 83.593124 |
| 3 | 0.042253 | sha256:fbcd7908110386e90c452008c872a8b32f775656042e8723a258f463f5ebeff6 | sha256:8e6bd08f6093931e27fc6e51a15f00239d1a14de32973f1068c29ddb9b60c1f1 | sha256:8e6bd08f6093931e27fc6e51a15f00239d1a14de32973f1068c29ddb9b60c1f1 | 410 | 100.000000 | 90.000000 | 41 | 164 | 0 | 83.679030 | 83.498175 |

## Recovery Footprint

| Run | Boxes | Cells | Full search cells | Cell fraction | Executor seconds | Fasim records | Recovered candidates | Recovered accepted | Fasim suppressed |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 246 | 3928292 | 503364872 | 0.780406 | 7.862276 | 246 | 820 | 410 | 246 |
| 2 | 246 | 3928292 | 503364872 | 0.780406 | 7.997899 | 246 | 820 | 410 | 246 |
| 3 | 246 | 3928292 | 503364872 | 0.780406 | 8.382003 | 246 | 820 | 410 | 246 |

## Aggregate

| Metric | Value |
| --- | --- |
| fasim_sim_recovery_characterization_repeat | 3 |
| fasim_sim_recovery_characterization_fast_digest_stable | 1 |
| fasim_sim_recovery_characterization_fast_expected_digest_match | 1 |
| fasim_sim_recovery_characterization_sim_close_digest_stable | 1 |
| fasim_sim_recovery_characterization_validate_selection_stable | 1 |
| fasim_sim_recovery_characterization_fast_digest | sha256:fbcd7908110386e90c452008c872a8b32f775656042e8723a258f463f5ebeff6 |
| fasim_sim_recovery_characterization_sim_close_digest | sha256:8e6bd08f6093931e27fc6e51a15f00239d1a14de32973f1068c29ddb9b60c1f1 |
| fasim_sim_recovery_characterization_fast_total_seconds_median | 0.042253 |
| fasim_sim_recovery_characterization_sim_close_wall_seconds_median | 83.369277 |
| fasim_sim_recovery_characterization_validate_wall_seconds_median | 83.498175 |
| fasim_sim_recovery_characterization_boxes_median | 246.000000 |
| fasim_sim_recovery_characterization_cells_median | 3928292.000000 |
| fasim_sim_recovery_characterization_full_search_cells_median | 503364872.000000 |
| fasim_sim_recovery_characterization_cell_fraction_median | 0.780406 |
| fasim_sim_recovery_characterization_executor_seconds_median | 7.997899 |
| fasim_sim_recovery_characterization_fasim_records_median | 246.000000 |
| fasim_sim_recovery_characterization_recovered_candidates_median | 820.000000 |
| fasim_sim_recovery_characterization_recovered_accepted_median | 410.000000 |
| fasim_sim_recovery_characterization_fasim_suppressed_median | 246.000000 |
| fasim_sim_recovery_characterization_output_records_median | 410.000000 |
| fasim_sim_recovery_characterization_recall_vs_sim_median | 100.000000 |
| fasim_sim_recovery_characterization_precision_vs_sim_median | 90.000000 |
| fasim_sim_recovery_characterization_extra_vs_sim_median | 41.000000 |
| fasim_sim_recovery_characterization_overlap_conflicts_median | 164.000000 |
| fasim_sim_recovery_characterization_fallbacks_median | 0.000000 |
| fasim_sim_recovery_characterization_fast_mode_output_mutations | 0 |
| fasim_sim_recovery_characterization_recommendation | experimental_opt_in |

## Decision

Keep `FASIM_SIM_RECOVERY=1` as an experimental opt-in. The repeated synthetic characterization shows stable fast and SIM-close digests, post-hoc validation does not alter selection, recall remains high, precision remains acceptable, and fast-mode output mutations remain zero.

Do not recommend or default SIM-close mode until production-corpus evidence exists.

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
