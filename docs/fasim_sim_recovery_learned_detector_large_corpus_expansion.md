# Fasim SIM-Close Learned Detector Large Corpus Expansion

## Large Corpus Expansion

This report generates a larger offline learned-detector real-corpus dataset by raising the bounded optional marmoset expansion limit. It is data generation only: no runtime model is trained or loaded, and Fasim/SIM-close runtime behavior is unchanged.

| Metric | Value |
| --- | --- |
| fasim_sim_recovery_learned_detector_large_corpus_expansion_enabled | 1 |
| fasim_sim_recovery_learned_detector_large_corpus_expansion_extra_marmoset_limit | 36 |
| fasim_sim_recovery_learned_detector_large_corpus_expansion_extra_marmoset_min_rna_bytes | 700 |
| fasim_sim_recovery_learned_detector_large_corpus_expansion_rows | 140 |
| fasim_sim_recovery_learned_detector_large_corpus_expansion_positive_rows | 73 |
| fasim_sim_recovery_learned_detector_large_corpus_expansion_negative_rows | 67 |
| fasim_sim_recovery_learned_detector_large_corpus_expansion_source_rows | 254 |
| fasim_sim_recovery_learned_detector_large_corpus_expansion_workload_count | 21 |
| fasim_sim_recovery_learned_detector_large_corpus_expansion_family_count | 4 |
| fasim_sim_recovery_learned_detector_large_corpus_expansion_validate_supported_workload_count | 19 |
| fasim_sim_recovery_learned_detector_large_corpus_expansion_no_legacy_sim_records_workload_count | 2 |
| fasim_sim_recovery_learned_detector_large_corpus_expansion_hard_negative_sources | executor_candidate_non_sim:9,extra_vs_sim_candidate:2,fasim_supported_non_sim:46,near_threshold_rejected_candidate:7,no_legacy_sim_records_proxy:3 |
| fasim_sim_recovery_learned_detector_large_corpus_expansion_hard_negative_source_count | 5 |
| fasim_sim_recovery_learned_detector_large_corpus_expansion_candidate_eligible_positive_rows | 66 |
| fasim_sim_recovery_learned_detector_large_corpus_expansion_candidate_eligible_negative_rows | 67 |
| fasim_sim_recovery_learned_detector_large_corpus_expansion_discovered_marmoset_pair_count | 417 |
| fasim_sim_recovery_learned_detector_large_corpus_expansion_eligible_extra_marmoset_pair_count | 396 |
| fasim_sim_recovery_learned_detector_large_corpus_expansion_selected_extra_case_count | 36 |
| fasim_sim_recovery_learned_detector_large_corpus_expansion_selected_extra_source_rows | 178 |
| fasim_sim_recovery_learned_detector_large_corpus_expansion_selected_extra_positive_rows | 56 |
| fasim_sim_recovery_learned_detector_large_corpus_expansion_selected_extra_negative_rows | 40 |
| fasim_sim_recovery_learned_detector_large_corpus_expansion_heldout_workload_available | 1 |
| fasim_sim_recovery_learned_detector_large_corpus_expansion_heldout_family_available | 1 |
| fasim_sim_recovery_learned_detector_large_corpus_expansion_workload_heldout_degenerate | 0 |
| fasim_sim_recovery_learned_detector_large_corpus_expansion_family_heldout_degenerate | 0 |
| fasim_sim_recovery_learned_detector_large_corpus_expansion_modeling_gate | ready_for_offline_shadow |
| fasim_sim_recovery_learned_detector_large_corpus_expansion_baseline_expanded_hard_negative_rows | 59 |
| fasim_sim_recovery_learned_detector_large_corpus_expansion_baseline_expanded_hard_negative_positive_rows | 26 |
| fasim_sim_recovery_learned_detector_large_corpus_expansion_baseline_expanded_hard_negative_negative_rows | 33 |
| fasim_sim_recovery_learned_detector_large_corpus_expansion_baseline_expanded_hard_negative_workload_count | 7 |
| fasim_sim_recovery_learned_detector_large_corpus_expansion_baseline_expanded_hard_negative_source_count | 5 |
| fasim_sim_recovery_learned_detector_large_corpus_expansion_growth_vs_expanded_hard_negative_rows | 81 |
| fasim_sim_recovery_learned_detector_large_corpus_expansion_growth_vs_expanded_hard_negative_positive_rows | 47 |
| fasim_sim_recovery_learned_detector_large_corpus_expansion_growth_vs_expanded_hard_negative_negative_rows | 34 |
| fasim_sim_recovery_learned_detector_large_corpus_expansion_growth_vs_expanded_hard_negative_workloads | 14 |
| fasim_sim_recovery_learned_detector_large_corpus_expansion_production_model | 0 |
| fasim_sim_recovery_learned_detector_large_corpus_expansion_sim_labels_runtime_inputs | 0 |
| fasim_sim_recovery_learned_detector_large_corpus_expansion_runtime_behavior_changed | 0 |
| fasim_sim_recovery_learned_detector_large_corpus_expansion_model_training_added | 0 |
| fasim_sim_recovery_learned_detector_large_corpus_expansion_deep_learning_dependency | 0 |
| fasim_sim_recovery_learned_detector_large_corpus_expansion_recommended_default_sim_close | 0 |

## Corpus Growth

| Metric | #90 baseline | Large corpus | Growth |
| --- | --- | --- | --- |
| rows | 59 | 140 | 81 |
| positive_rows | 26 | 73 | 47 |
| negative_rows | 33 | 67 | 34 |
| workload_count | 7 | 21 | 14 |

## Hard Negative Source Audit

| Source | Rows |
| --- | --- |
| executor_candidate_non_sim | 9 |
| extra_vs_sim_candidate | 2 |
| fasim_supported_non_sim | 46 |
| near_threshold_rejected_candidate | 7 |
| no_legacy_sim_records_proxy | 3 |

## Selected Extra Marmoset Cases

| Label | Gene | DNA bytes | RNA bytes |
| --- | --- | --- | --- |
| marmoset_extra_ENSG00000234936_1 | ENSG00000234936.1 | 5052 | 708 |
| marmoset_extra_ENSG00000271314_1 | ENSG00000271314.1 | 5054 | 728 |
| marmoset_extra_ENSG00000267714_1 | ENSG00000267714.1 | 5050 | 741 |
| marmoset_extra_ENSG00000272192_1 | ENSG00000272192.1 | 5055 | 757 |
| marmoset_extra_ENSG00000258789_1 | ENSG00000258789.1 | 5053 | 774 |
| marmoset_extra_ENSG00000259054_1 | ENSG00000259054.1 | 5052 | 803 |
| marmoset_extra_ENSG00000259912_1 | ENSG00000259912.1 | 5053 | 805 |
| marmoset_extra_ENSG00000201680_1 | ENSG00000201680.1 | 5054 | 875 |
| marmoset_extra_ENSG00000224091_1 | ENSG00000224091.1 | 5053 | 879 |
| marmoset_extra_ENSG00000257180_1 | ENSG00000257180.1 | 5053 | 935 |
| marmoset_extra_ENSG00000237797_1 | ENSG00000237797.1 | 5051 | 949 |
| marmoset_extra_ENSG00000267898_1 | ENSG00000267898.1 | 5053 | 949 |
| marmoset_extra_ENSG00000254789_1 | ENSG00000254789.1 | 5051 | 989 |
| marmoset_extra_ENSG00000273176_1 | ENSG00000273176.1 | 5053 | 1011 |
| marmoset_extra_ENSG00000271937_1 | ENSG00000271937.1 | 5055 | 1061 |
| marmoset_extra_ENSG00000235058_1 | ENSG00000235058.1 | 5055 | 1130 |
| marmoset_extra_ENSG00000224943_1 | ENSG00000224943.1 | 5055 | 1141 |
| marmoset_extra_ENSG00000235020_2 | ENSG00000235020.2 | 5054 | 1145 |
| marmoset_extra_ENSG00000174680_5 | ENSG00000174680.5 | 5050 | 1344 |
| marmoset_extra_ENSG00000269473_1 | ENSG00000269473.1 | 5053 | 1342 |
| marmoset_extra_ENSG00000258343_1 | ENSG00000258343.1 | 5054 | 1347 |
| marmoset_extra_ENSG00000260509_2 | ENSG00000260509.2 | 5053 | 1359 |
| marmoset_extra_ENSG00000273492_1 | ENSG00000273492.1 | 5051 | 1397 |
| marmoset_extra_ENSG00000180458_2 | ENSG00000180458.2 | 5054 | 1415 |
| marmoset_extra_ENSG00000224081_3 | ENSG00000224081.3 | 5053 | 1435 |
| marmoset_extra_ENSG00000259377_1 | ENSG00000259377.1 | 5050 | 1458 |
| marmoset_extra_ENSG00000267045_1 | ENSG00000267045.1 | 5052 | 1478 |
| marmoset_extra_ENSG00000258001_1 | ENSG00000258001.1 | 5053 | 1508 |
| marmoset_extra_ENSG00000223534_1 | ENSG00000223534.1 | 5053 | 1512 |
| marmoset_extra_ENSG00000223469_1 | ENSG00000223469.1 | 5054 | 1548 |
| marmoset_extra_ENSG00000255542_1 | ENSG00000255542.1 | 5051 | 1587 |
| marmoset_extra_ENSG00000263146_2 | ENSG00000263146.2 | 5054 | 1600 |
| marmoset_extra_ENSG00000255020_1 | ENSG00000255020.1 | 5050 | 1650 |
| marmoset_extra_ENSG00000240291_1 | ENSG00000240291.1 | 5053 | 1730 |
| marmoset_extra_ENSG00000244558_1 | ENSG00000244558.1 | 5050 | 1749 |
| marmoset_extra_ENSG00000260017_1 | ENSG00000260017.1 | 5053 | 1748 |

## Decision

This PR expands the offline corpus only. A future learned-detector model shadow, if pursued, must be a separate PR and must re-check held-out behavior against the current hand-written guard.

## Scope

```text
Production model added: no
Runtime behavior changed: no
Fasim runtime changed: no
SIM-close runtime changed: no
Scoring/threshold/non-overlap behavior changed: no
GPU/filter behavior changed: no
SIM labels used as runtime input: no
Recommended/default SIM-close: no
Deep learning dependency added: no
```

No production model is trained or loaded. SIM labels remain offline labels only. They must not be used as runtime detector inputs, guard inputs, replacement inputs, or output ordering inputs.
