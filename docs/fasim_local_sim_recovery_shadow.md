# Fasim Local SIM Recovery Shadow

Base branch:

```text
fasim-sim-gap-taxonomy
```

This report is diagnostic-only. It builds local recovery boxes from Fasim-supported SIM gaps and checks which legacy SIM-only records would fall inside those boxes. It does not add recovered records to Fasim output and does not change scoring, threshold, non-overlap, filter, or GPU behavior.

The shadow uses the full legacy `-F` SIM output as an oracle to estimate local recovery coverage. It is not a production local-SIM implementation and should not be treated as a production accuracy claim.

Because this is an oracle feasibility shadow, the boxes are selected from known SIM-only taxonomy records and their overlapping Fasim records. A deployable path still needs an independent risk detector and a bounded local SIM executor.

| Setting | Value |
| --- | --- |
| profile_set | representative |
| box_source | overlapping Fasim records |
| margin_bp | 32 |
| merge_gap_bp | 32 |
| output_mutations_expected | 0 |

## Workload Summary

| Workload | SIM-only | Recovered | Unrecovered | Recovery recall | Boxes | Windows | Cells | Full-search cells | Cell fraction | Shadow seconds | Candidate SIM records | Output mutations |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| tiny | 9 | 9 | 0 | 100.00% | 6 | 4 | 95812 | 12277192 | 0.78% | 0.000358 | 9 | 0 |
| medium_synthetic | 72 | 72 | 0 | 100.00% | 48 | 4 | 766496 | 98217536 | 0.78% | 0.001017 | 72 | 0 |
| window_heavy_synthetic | 288 | 288 | 0 | 100.00% | 192 | 4 | 3065984 | 392870144 | 0.78% | 0.016409 | 288 | 0 |

## Category Summary

| Category | SIM-only | Recovered | Recall | Boxes | Cells | Seconds |
| --- | --- | --- | --- | --- | --- | --- |
| long_hit_internal_peak | 41 | 41 | 100.00% | 41 | 1010568 | 0.017784 |
| nested_alignment | 123 | 123 | 100.00% | 123 | 1741967 | 0.017784 |
| nonoverlap_conflict | 0 | 0 | 0.00% | 0 | 0 | 0.017784 |
| overlap_chain | 205 | 205 | 100.00% | 164 | 2791485 | 0.017784 |
| tie_near_tie | 0 | 0 | 0.00% | 0 | 0 | 0.017784 |
| threshold_near | 0 | 0 | 0.00% | 0 | 0 | 0.017784 |
| unknown | 0 | 0 | 0.00% | 0 | 0 | 0.017784 |

Box and cell counts in the category table are non-exclusive because a merged box can cover multiple gap categories.

## Aggregate

| Metric | Value |
| --- | --- |
| fasim_sim_recovery_shadow_enabled | 1 |
| fasim_sim_recovery_shadow_boxes | 246 |
| fasim_sim_recovery_shadow_windows | 12 |
| fasim_sim_recovery_shadow_cells | 3928292 |
| fasim_sim_recovery_shadow_full_search_cells | 503364872 |
| fasim_sim_recovery_shadow_cell_fraction | 0.78% |
| fasim_sim_recovery_shadow_seconds | 0.017784 |
| fasim_sim_recovery_shadow_sim_only_records | 369 |
| fasim_sim_recovery_shadow_recovered_records | 369 |
| fasim_sim_recovery_shadow_unrecovered_records | 0 |
| fasim_sim_recovery_shadow_recovery_recall | 100.00% |
| fasim_sim_recovery_shadow_candidate_records | 369 |
| fasim_sim_recovery_shadow_output_mutations | 0 |

## Decision

Local recovery boxes cover most SIM-only records on these synthetic fixtures. A real local SIM recovery shadow that executes bounded SIM inside boxes is a plausible next PR.

Forbidden-scope check:

```text
Fasim output change: no
Recovered records added to output: no
Scoring/threshold/non-overlap behavior change: no
GPU/filter behavior change: no
Production accuracy claim: no
```

