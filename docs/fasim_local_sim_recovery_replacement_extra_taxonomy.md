# Fasim Local SIM Recovery Replacement Extra Taxonomy

Base branch:

```text
fasim-local-sim-recovery-replacement-shadow
```

This report is diagnostic-only. It analyzes the extra records left by the best non-oracle replacement shape and evaluates non-oracle guards against the side replacement candidate set. It does not add a real `FASIM_SIM_RECOVERY=1` mode and does not mutate Fasim output.

Legacy SIM membership is used only after candidate generation for taxonomy and guard evaluation. It is forbidden as production selection input.

| Setting | Value |
| --- | --- |
| profile_set | representative |
| input_candidates | box-local replacement accepted candidates |
| base_replacement_filter | candidate score >= 89 and Nt >= 50 |
| selected_non_oracle_guard | combined_non_oracle |
| oracle_guard | oracle_sim_match, analysis-only upper bound |
| output_mutations_expected | 0 |

## Workload Feature Summary

| Workload | True SIM records | Extra records | Score min true | Score min extra | Nt min true | Nt min extra | Local rank true p50 | Local rank extra p50 | Dominated true | Dominated extra | Contained true | Contained extra | Boundary true p50 | Boundary extra p50 | Overlap conflicts | Output mutations |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| tiny | 9 | 4 | 89.00 | 91.00 | 50 | 56 | 1.00 | 3.00 | 0 | 1 | 4 | 0 | 0.00 | 0.00 | 11 | 0 |
| medium_synthetic | 72 | 32 | 89.00 | 91.00 | 50 | 56 | 1.00 | 3.00 | 0 | 8 | 32 | 0 | 0.00 | 0.00 | 88 | 0 |
| window_heavy_synthetic | 288 | 128 | 89.00 | 91.00 | 50 | 56 | 1.00 | 3.00 | 0 | 32 | 128 | 0 | 0.00 | 0.00 | 352 | 0 |

## Guard Evaluation

| Workload | Guard | Oracle | Selected candidates | Integrated records | SIM-only recovered | Recall vs SIM | Precision vs SIM | Extra vs SIM | Overlap conflicts | Output mutations |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| tiny | score_nt_threshold | no | 13 | 13 | 9 | 100.00% | 69.23% | 4 | 11 | 0 |
| tiny | local_rank_topk_per_box | no | 10 | 10 | 9 | 100.00% | 90.00% | 1 | 4 | 0 |
| tiny | family_rank_topk | no | 8 | 8 | 7 | 77.78% | 87.50% | 1 | 3 | 0 |
| tiny | dominance_filter | no | 12 | 12 | 9 | 100.00% | 75.00% | 3 | 9 | 0 |
| tiny | containment_boundary_guard | no | 11 | 11 | 8 | 88.89% | 72.73% | 3 | 6 | 0 |
| tiny | combined_non_oracle | no | 10 | 10 | 9 | 100.00% | 90.00% | 1 | 4 | 0 |
| tiny | oracle_sim_match | yes | 9 | 9 | 9 | 100.00% | 100.00% | 0 | 3 | 0 |
| medium_synthetic | score_nt_threshold | no | 104 | 104 | 72 | 100.00% | 69.23% | 32 | 88 | 0 |
| medium_synthetic | local_rank_topk_per_box | no | 80 | 80 | 72 | 100.00% | 90.00% | 8 | 32 | 0 |
| medium_synthetic | family_rank_topk | no | 8 | 8 | 8 | 11.11% | 100.00% | 0 | 0 | 0 |
| medium_synthetic | dominance_filter | no | 96 | 96 | 72 | 100.00% | 75.00% | 24 | 72 | 0 |
| medium_synthetic | containment_boundary_guard | no | 88 | 88 | 64 | 88.89% | 72.73% | 24 | 48 | 0 |
| medium_synthetic | combined_non_oracle | no | 80 | 80 | 72 | 100.00% | 90.00% | 8 | 32 | 0 |
| medium_synthetic | oracle_sim_match | yes | 72 | 72 | 72 | 100.00% | 100.00% | 0 | 24 | 0 |
| window_heavy_synthetic | score_nt_threshold | no | 416 | 416 | 288 | 100.00% | 69.23% | 128 | 352 | 0 |
| window_heavy_synthetic | local_rank_topk_per_box | no | 320 | 320 | 288 | 100.00% | 90.00% | 32 | 128 | 0 |
| window_heavy_synthetic | family_rank_topk | no | 8 | 8 | 8 | 2.78% | 100.00% | 0 | 0 | 0 |
| window_heavy_synthetic | dominance_filter | no | 384 | 384 | 288 | 100.00% | 75.00% | 96 | 288 | 0 |
| window_heavy_synthetic | containment_boundary_guard | no | 352 | 352 | 256 | 88.89% | 72.73% | 96 | 192 | 0 |
| window_heavy_synthetic | combined_non_oracle | no | 320 | 320 | 288 | 100.00% | 90.00% | 32 | 128 | 0 |
| window_heavy_synthetic | oracle_sim_match | yes | 288 | 288 | 288 | 100.00% | 100.00% | 0 | 96 | 0 |

## Guard Summary

| Guard | Oracle | Selected candidates | Integrated records | SIM-only recovered | Recall vs SIM | Precision vs SIM | Extra vs SIM | Overlap conflicts | Output mutations |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| score_nt_threshold | no | 533 | 533 | 369 | 100.00% | 69.23% | 164 | 451 | 0 |
| local_rank_topk_per_box | no | 410 | 410 | 369 | 100.00% | 90.00% | 41 | 164 | 0 |
| family_rank_topk | no | 24 | 24 | 23 | 6.23% | 95.83% | 1 | 3 | 0 |
| dominance_filter | no | 492 | 492 | 369 | 100.00% | 75.00% | 123 | 369 | 0 |
| containment_boundary_guard | no | 451 | 451 | 328 | 88.89% | 72.73% | 123 | 246 | 0 |
| combined_non_oracle | no | 410 | 410 | 369 | 100.00% | 90.00% | 41 | 164 | 0 |
| oracle_sim_match | yes | 369 | 369 | 369 | 100.00% | 100.00% | 0 | 123 | 0 |

## Aggregate

| Metric | Value |
| --- | --- |
| fasim_sim_recovery_extra_taxonomy_enabled | 1 |
| fasim_sim_recovery_extra_taxonomy_true_sim_records | 369 |
| fasim_sim_recovery_extra_taxonomy_extra_records | 164 |
| fasim_sim_recovery_extra_taxonomy_score_min_true | 89.00 |
| fasim_sim_recovery_extra_taxonomy_score_min_extra | 91.00 |
| fasim_sim_recovery_extra_taxonomy_nt_min_true | 50 |
| fasim_sim_recovery_extra_taxonomy_nt_min_extra | 56 |
| fasim_sim_recovery_extra_taxonomy_rank_true_p50 | 1.00 |
| fasim_sim_recovery_extra_taxonomy_rank_extra_p50 | 3.00 |
| fasim_sim_recovery_extra_taxonomy_dominated_true | 0 |
| fasim_sim_recovery_extra_taxonomy_dominated_extra | 41 |
| fasim_sim_recovery_extra_taxonomy_contained_true | 164 |
| fasim_sim_recovery_extra_taxonomy_contained_extra | 0 |
| fasim_sim_recovery_extra_taxonomy_boundary_distance_true_p50 | 0.00 |
| fasim_sim_recovery_extra_taxonomy_boundary_distance_extra_p50 | 0.00 |
| fasim_sim_recovery_extra_taxonomy_overlap_conflicts | 451 |
| fasim_sim_recovery_extra_taxonomy_selected_guard | combined_non_oracle |
| fasim_sim_recovery_extra_taxonomy_selected_guard_recall_vs_sim | 100.00% |
| fasim_sim_recovery_extra_taxonomy_selected_guard_precision_vs_sim | 90.00% |
| fasim_sim_recovery_extra_taxonomy_selected_guard_extra_records_vs_sim | 41 |
| fasim_sim_recovery_extra_taxonomy_selected_guard_overlap_conflicts | 164 |
| fasim_sim_recovery_extra_taxonomy_output_mutations | 0 |

## Decision

A non-oracle guard reaches the strong recall/precision target on these representative synthetic fixtures. The next PR can design a real SIM-close mode, but this remains diagnostic-only.

Forbidden-scope check:

```text
Fasim output change: no
Recovered records added to output: no
Real FASIM_SIM_RECOVERY mode: no
SIM-only labels used as production selection input: no
Scoring/threshold/non-overlap behavior change: no
GPU/filter behavior change: no
Production accuracy claim: no
```
