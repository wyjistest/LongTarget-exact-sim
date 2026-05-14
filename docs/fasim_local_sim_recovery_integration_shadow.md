# Fasim Local SIM Recovery Integration Shadow

Base branch:

```text
fasim-local-sim-recovery-executor-shadow
```

This report is diagnostic-only. It runs the Fasim-visible risk detector and bounded local SIM executor, then builds a side candidate set from Fasim output records plus recovered local SIM records. The side set is evaluated with an exact raw-record de-duplication comparator; it is not written as Fasim output and does not replace final non-overlap authority.

The representative fixtures are deterministic synthetic fixtures. This shadow measures integration feasibility only; it is not a production accuracy claim and it is not a real `FASIM_SIM_RECOVERY=1` mode.

| Setting | Value |
| --- | --- |
| profile_set | representative |
| candidate_set | Fasim raw records union bounded local SIM raw records |
| dedup_comparator | exact canonical lite record identity |
| nonoverlap_conflicts | diagnostic same-family genomic overlap pairs only |
| output_mutations_expected | 0 |

## Workload Summary

| Workload | Fasim records | Recovered candidates | Unique recovered | Duplicate recovered | Integrated records | SIM records | SIM-only | SIM-only recovered | Recall vs SIM | Precision vs SIM | Extra vs SIM | Overlap conflicts | Output mutations |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| tiny | 6 | 20 | 20 | 0 | 26 | 9 | 9 | 9 | 100.00% | 34.62% | 17 | 48 | 0 |
| medium_synthetic | 48 | 160 | 160 | 0 | 208 | 72 | 72 | 72 | 100.00% | 34.62% | 136 | 384 | 0 |
| window_heavy_synthetic | 192 | 640 | 640 | 0 | 832 | 288 | 288 | 288 | 100.00% | 34.62% | 544 | 1536 | 0 |

## Category Summary

| Category | SIM-only | Recovered after side integration | Unrecovered | Recall |
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
| fasim_sim_recovery_integration_shadow_enabled | 1 |
| fasim_sim_recovery_integration_shadow_fasim_records | 246 |
| fasim_sim_recovery_integration_shadow_recovered_candidates | 820 |
| fasim_sim_recovery_integration_shadow_unique_recovered_records | 820 |
| fasim_sim_recovery_integration_shadow_duplicate_recovered_records | 0 |
| fasim_sim_recovery_integration_shadow_integrated_records | 1066 |
| fasim_sim_recovery_integration_shadow_sim_records | 369 |
| fasim_sim_recovery_integration_shadow_sim_only_records | 369 |
| fasim_sim_recovery_integration_shadow_sim_only_recovered | 369 |
| fasim_sim_recovery_integration_shadow_recall_vs_sim | 100.00% |
| fasim_sim_recovery_integration_shadow_precision_vs_sim | 34.62% |
| fasim_sim_recovery_integration_shadow_extra_records_vs_sim | 697 |
| fasim_sim_recovery_integration_shadow_nonoverlap_conflicts | 1968 |
| fasim_sim_recovery_integration_shadow_output_mutations | 0 |

## Decision

The side integration recovers most SIM records, but extra candidates are high. Refine candidate filtering, de-duplication, or documented merge semantics before a real opt-in.

Forbidden-scope check:

```text
Fasim output change: no
Recovered records added to output: no
Real FASIM_SIM_RECOVERY mode: no
Scoring/threshold/non-overlap behavior change: no
GPU/filter behavior change: no
Production accuracy claim: no
```
