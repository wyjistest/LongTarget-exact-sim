# Fasim Local SIM Recovery Executor Shadow

Base branch:

```text
fasim-sim-recovery-risk-detector
```

This report runs a bounded local SIM executor inside boxes selected by the Fasim-visible risk detector. Box selection uses Fasim output records only. The executor result is diagnostic-only and is compared against SIM-only records after execution.

The shadow does not add recovered records to Fasim output and does not change scoring, threshold, non-overlap, output, GPU, or filter behavior. The representative fixtures remain deterministic synthetic fixtures, not a production accuracy benchmark.

| Setting | Value |
| --- | --- |
| profile_set | representative |
| box_source | Fasim-visible risk detector boxes |
| executor | per-box legacy -F SIM on cropped DNA/RNA |
| output_mutations_expected | 0 |

## Workload Summary

| Workload | Boxes | Cells | Full-search cells | Cell fraction | Executor seconds | SIM-only | Recovered | Unrecovered | Recall | Candidate records | Executor failures | Unsupported boxes | Output mutations |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| tiny | 6 | 95812 | 12277192 | 0.78% | 0.169633 | 9 | 9 | 0 | 100.00% | 20 | 0 | 0 | 0 |
| medium_synthetic | 48 | 766496 | 98217536 | 0.78% | 1.562290 | 72 | 72 | 0 | 100.00% | 160 | 0 | 0 | 0 |
| window_heavy_synthetic | 192 | 3065984 | 392870144 | 0.78% | 6.263588 | 288 | 288 | 0 | 100.00% | 640 | 0 | 0 | 0 |

## Category Summary

| Category | SIM-only | Recovered | Unrecovered | Recall |
| --- | --- | --- | --- | --- |
| long_hit_internal_peak | 41 | 41 | 0 | 100.00% |
| nested_alignment | 123 | 123 | 0 | 100.00% |
| nonoverlap_conflict | 0 | 0 | 0 | 0.00% |
| overlap_chain | 205 | 205 | 0 | 100.00% |
| tie_near_tie | 0 | 0 | 0 | 0.00% |
| threshold_near | 0 | 0 | 0 | 0.00% |
| unknown | 0 | 0 | 0 | 0.00% |

## Aggregate

| Metric | Value |
| --- | --- |
| fasim_sim_recovery_executor_shadow_enabled | 1 |
| fasim_sim_recovery_executor_shadow_boxes | 246 |
| fasim_sim_recovery_executor_shadow_cells | 3928292 |
| fasim_sim_recovery_executor_shadow_full_search_cells | 503364872 |
| fasim_sim_recovery_executor_shadow_cell_fraction | 0.78% |
| fasim_sim_recovery_executor_shadow_seconds | 7.995510 |
| fasim_sim_recovery_executor_shadow_sim_only_records | 369 |
| fasim_sim_recovery_executor_shadow_recovered_records | 369 |
| fasim_sim_recovery_executor_shadow_unrecovered_records | 0 |
| fasim_sim_recovery_executor_shadow_recall | 100.00% |
| fasim_sim_recovery_executor_shadow_candidate_records | 820 |
| fasim_sim_recovery_executor_shadow_output_mutations | 0 |
| fasim_sim_recovery_executor_shadow_executor_failures | 0 |
| fasim_sim_recovery_executor_shadow_unsupported_boxes | 0 |

## Decision

The bounded executor recovers most SIM-only records within a small cell fraction. A real local SIM recovery opt-in with validation is a plausible next PR.

Forbidden-scope check:

```text
Fasim output change: no
Recovered records added to output: no
Scoring/threshold/non-overlap behavior change: no
GPU/filter behavior change: no
Production accuracy claim: no
SIM-only coordinates used for selection: no
```
