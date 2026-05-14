# Fasim Local SIM Recovery Filter Shadow

Base branch:

```text
fasim-local-sim-recovery-integration-shadow
```

This report is diagnostic-only. It classifies bounded local SIM recovery candidates and evaluates side filtering strategies against the Fasim output plus recovered-candidate set. It does not add a real `FASIM_SIM_RECOVERY=1` mode and does not mutate Fasim output.

The `oracle_sim_match` strategy uses legacy SIM membership after candidate generation and is included only as an upper-bound analysis. It is forbidden as production selection input.

| Setting | Value |
| --- | --- |
| profile_set | representative |
| input_candidates | bounded local SIM executor raw records |
| candidate_set | Fasim raw records union filtered local SIM raw records |
| non_oracle_heuristic | candidate score >= 89 and Nt >= 50 |
| output_mutations_expected | 0 |

## Candidate Class Summary

| Workload | Recovered candidates | Fasim duplicates | Near duplicates | SIM-only matches | Extra vs SIM | Nested candidates | Internal peak candidates | Overlap conflicts before | Output mutations |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| tiny | 20 | 0 | 20 | 9 | 11 | 4 | 4 | 48 | 0 |
| medium_synthetic | 160 | 0 | 160 | 72 | 88 | 32 | 32 | 384 | 0 |
| window_heavy_synthetic | 640 | 0 | 640 | 288 | 352 | 128 | 128 | 1536 | 0 |

Candidate classes are diagnostic and not mutually exclusive. `Near duplicate` means same-family overlap in both genomic and RNA axes with a Fasim output record.

## Strategy Summary

| Strategy | Oracle | Recovered candidates | Filtered candidates | Integrated records | SIM-only recovered | Recall vs SIM | Precision vs SIM | Extra vs SIM | Overlap conflicts | Output mutations |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| exact_dedup_only | no | 820 | 820 | 1066 | 369 | 100.00% | 34.62% | 697 | 1968 | 0 |
| score_interval_dominance | no | 820 | 615 | 861 | 205 | 55.56% | 23.81% | 656 | 1394 | 0 |
| same_family_overlap_suppression | no | 820 | 0 | 246 | 0 | 0.00% | 0.00% | 246 | 0 | 0 |
| oracle_sim_match | yes | 820 | 369 | 615 | 369 | 100.00% | 60.00% | 246 | 492 | 0 |
| non_oracle_score_nt | no | 820 | 533 | 779 | 369 | 100.00% | 47.37% | 410 | 984 | 0 |

## Aggregate

| Metric | Value |
| --- | --- |
| fasim_sim_recovery_filter_shadow_enabled | 1 |
| fasim_sim_recovery_filter_shadow_recovered_candidates | 820 |
| fasim_sim_recovery_filter_shadow_fasim_duplicates | 0 |
| fasim_sim_recovery_filter_shadow_near_duplicates | 820 |
| fasim_sim_recovery_filter_shadow_sim_only_matches | 369 |
| fasim_sim_recovery_filter_shadow_extra_vs_sim | 451 |
| fasim_sim_recovery_filter_shadow_overlap_conflicts_before | 1968 |
| fasim_sim_recovery_filter_shadow_overlap_conflicts_after | 984 |
| fasim_sim_recovery_filter_shadow_filtered_candidates | 533 |
| fasim_sim_recovery_filter_shadow_integrated_records | 779 |
| fasim_sim_recovery_filter_shadow_recall_vs_sim | 100.00% |
| fasim_sim_recovery_filter_shadow_precision_vs_sim | 47.37% |
| fasim_sim_recovery_filter_shadow_extra_records_vs_sim | 410 |
| fasim_sim_recovery_filter_shadow_nested_candidates | 164 |
| fasim_sim_recovery_filter_shadow_internal_peak_candidates | 164 |
| fasim_sim_recovery_filter_shadow_unknown_candidates | 0 |
| fasim_sim_recovery_filter_shadow_output_mutations | 0 |

## Decision

The non-oracle filter reduces some candidates but precision remains low. Refine recovery boxes, candidate ranking, or de-dup semantics.

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
