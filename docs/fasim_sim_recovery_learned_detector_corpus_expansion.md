# Fasim SIM-Close Learned Detector Corpus Expansion

## Corpus Gate Report

This report records the current offline learned-detector corpus gate. It does not add a runtime model, change Fasim output, or recommend/default SIM-close.

When the local marmoset real-corpus inputs are available, the check script appends three additional offline workloads:

- `marmoset_59006`: validate-supported real-corpus case
- `marmoset_33639`: validate-supported real-corpus case
- `marmoset_29743_no_legacy`: no-legacy-SIM proxy negative case

The local corpus root defaults to `/data/wenyujianData/humanLncAtlas/wenyujian/inputForShenzhen-marmoset` and can be overridden with `FASIM_SIM_RECOVERY_LEARNED_DETECTOR_MARMOSET_ROOT`.

| Metric | Value |
| --- | --- |
| workload_count | 4 |
| family_count | 4 |
| validate_supported_workload_count | 3 |
| no_legacy_sim_records_workload_count | 1 |
| rows | 44 |
| positive_rows | 17 |
| negative_rows | 27 |
| hard_negative_sources | executor_candidate_non_sim:8,extra_vs_sim_candidate:1,fasim_supported_non_sim:9,near_threshold_rejected_candidate:7,no_legacy_sim_records_proxy:2 |
| hard_negative_source_count | 5 |
| workload_heldout_degenerate | 0 |
| family_heldout_degenerate | 0 |
| heldout_workload_available | 1 |
| heldout_family_available | 1 |
| modeling_gate | ready_for_offline_shadow |

## Decision

The next learned-detector step can be an offline model-shadow PR with held-out evaluation when the marmoset corpus inputs are present. This is not a runtime promotion signal.

If the marmoset corpus inputs are not present, the check falls back to the tracked tiny fixture and the gate remains `collect_more_workloads`. SIM labels may remain offline training/evaluation labels only; they must not be used as runtime detector inputs, guard inputs, replacement inputs, or output ordering inputs.

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
