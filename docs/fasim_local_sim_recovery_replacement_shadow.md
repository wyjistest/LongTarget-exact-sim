# Fasim Local SIM Recovery Replacement Shadow

Base branch:

```text
fasim-local-sim-recovery-filter-shadow
```

This report is diagnostic-only. It evaluates side replacement and merge strategies for Fasim records plus bounded local SIM recovery candidates. It does not add a real `FASIM_SIM_RECOVERY=1` mode, does not mutate Fasim output, and does not replace final non-overlap authority.

The `oracle_box_replacement` strategy uses legacy SIM membership after candidate generation and is included only as an upper-bound analysis. It is forbidden as production selection input.

| Setting | Value |
| --- | --- |
| profile_set | representative |
| input_candidates | bounded local SIM executor raw records |
| replacement_candidate_filter | candidate score >= 89 and Nt >= 50 |
| box_local_replacement | suppress Fasim records inside detector boxes |
| family_replacement | suppress Fasim records in recovered candidate families |
| output_mutations_expected | 0 |

## Workload Strategy Summary

| Workload | Strategy | Oracle | Integrated records | Fasim suppressed | Recovered accepted | Recall vs SIM | Precision vs SIM | Extra vs SIM | Overlap conflicts | Output mutations |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| tiny | raw_union | no | 26 | 0 | 20 | 100.00% | 34.62% | 17 | 48 | 0 |
| tiny | filtered_union | no | 19 | 0 | 13 | 100.00% | 47.37% | 10 | 24 | 0 |
| tiny | box_local_replacement | no | 13 | 6 | 13 | 100.00% | 69.23% | 4 | 11 | 0 |
| tiny | family_replacement | no | 13 | 6 | 13 | 100.00% | 69.23% | 4 | 11 | 0 |
| tiny | conservative_replacement | no | 13 | 6 | 13 | 100.00% | 69.23% | 4 | 11 | 0 |
| tiny | oracle_box_replacement | yes | 9 | 6 | 9 | 100.00% | 100.00% | 0 | 3 | 0 |
| medium_synthetic | raw_union | no | 208 | 0 | 160 | 100.00% | 34.62% | 136 | 384 | 0 |
| medium_synthetic | filtered_union | no | 152 | 0 | 104 | 100.00% | 47.37% | 80 | 192 | 0 |
| medium_synthetic | box_local_replacement | no | 104 | 48 | 104 | 100.00% | 69.23% | 32 | 88 | 0 |
| medium_synthetic | family_replacement | no | 104 | 48 | 104 | 100.00% | 69.23% | 32 | 88 | 0 |
| medium_synthetic | conservative_replacement | no | 104 | 48 | 104 | 100.00% | 69.23% | 32 | 88 | 0 |
| medium_synthetic | oracle_box_replacement | yes | 72 | 48 | 72 | 100.00% | 100.00% | 0 | 24 | 0 |
| window_heavy_synthetic | raw_union | no | 832 | 0 | 640 | 100.00% | 34.62% | 544 | 1536 | 0 |
| window_heavy_synthetic | filtered_union | no | 608 | 0 | 416 | 100.00% | 47.37% | 320 | 768 | 0 |
| window_heavy_synthetic | box_local_replacement | no | 416 | 192 | 416 | 100.00% | 69.23% | 128 | 352 | 0 |
| window_heavy_synthetic | family_replacement | no | 416 | 192 | 416 | 100.00% | 69.23% | 128 | 352 | 0 |
| window_heavy_synthetic | conservative_replacement | no | 416 | 192 | 416 | 100.00% | 69.23% | 128 | 352 | 0 |
| window_heavy_synthetic | oracle_box_replacement | yes | 288 | 192 | 288 | 100.00% | 100.00% | 0 | 96 | 0 |

## Strategy Summary

| Strategy | Oracle | Integrated records | Fasim suppressed | Recovered accepted | Recall vs SIM | Precision vs SIM | Extra vs SIM | Overlap conflicts | Output mutations |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| raw_union | no | 1066 | 0 | 820 | 100.00% | 34.62% | 697 | 1968 | 0 |
| filtered_union | no | 779 | 0 | 533 | 100.00% | 47.37% | 410 | 984 | 0 |
| box_local_replacement | no | 533 | 246 | 533 | 100.00% | 69.23% | 164 | 451 | 0 |
| family_replacement | no | 533 | 246 | 533 | 100.00% | 69.23% | 164 | 451 | 0 |
| conservative_replacement | no | 533 | 246 | 533 | 100.00% | 69.23% | 164 | 451 | 0 |
| oracle_box_replacement | yes | 369 | 246 | 369 | 100.00% | 100.00% | 0 | 123 | 0 |

## Aggregate

| Metric | Value |
| --- | --- |
| fasim_sim_recovery_replacement_shadow_enabled | 1 |
| fasim_sim_recovery_replacement_shadow_strategy | box_local_replacement |
| fasim_sim_recovery_replacement_shadow_fasim_records | 246 |
| fasim_sim_recovery_replacement_shadow_recovered_candidates | 820 |
| fasim_sim_recovery_replacement_shadow_fasim_records_suppressed | 246 |
| fasim_sim_recovery_replacement_shadow_recovered_records_accepted | 533 |
| fasim_sim_recovery_replacement_shadow_integrated_records | 533 |
| fasim_sim_recovery_replacement_shadow_sim_records | 369 |
| fasim_sim_recovery_replacement_shadow_sim_only_recovered | 369 |
| fasim_sim_recovery_replacement_shadow_recall_vs_sim | 100.00% |
| fasim_sim_recovery_replacement_shadow_precision_vs_sim | 69.23% |
| fasim_sim_recovery_replacement_shadow_extra_records_vs_sim | 164 |
| fasim_sim_recovery_replacement_shadow_overlap_conflicts | 451 |
| fasim_sim_recovery_replacement_shadow_output_mutations | 0 |

## Decision

Replacement semantics improve the raw-union shape but precision is still below the strong threshold. Refine replacement guards, candidate ranking, or box/family selection before a real mode.

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
