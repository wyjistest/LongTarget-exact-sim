# Fasim SIM-Close Learned Detector Real-Corpus Hard Negatives

## Real-Corpus Expansion

This report expands the offline learned-detector data line with bounded optional marmoset real-corpus cases when local FASTA pairs are available. It collects hard-negative evidence only; it does not train a model or change runtime behavior.

Input negative dataset: `/data/wenyujianData/LongTarget-exact-sim/.worktrees/fasim-sim-recovery-learned-detector-real-corpus-hard-negatives/.tmp/fasim_sim_recovery_learned_detector_real_corpus_hard_negatives_check/negative_dataset.tsv`
Input source learned dataset: `/data/wenyujianData/LongTarget-exact-sim/.worktrees/fasim-sim-recovery-learned-detector-real-corpus-hard-negatives/.tmp/fasim_sim_recovery_learned_detector_real_corpus_hard_negatives_check/learned_detector_dataset.tsv`
Negative dataset report: `/data/wenyujianData/LongTarget-exact-sim/.worktrees/fasim-sim-recovery-learned-detector-real-corpus-hard-negatives/.tmp/fasim_sim_recovery_learned_detector_real_corpus_hard_negatives_check/negative_dataset_report.md`

| Metric | Value |
| --- | --- |
| fasim_sim_recovery_learned_detector_real_corpus_hard_negatives_enabled | 1 |
| fasim_sim_recovery_learned_detector_real_corpus_hard_negatives_rows | 59 |
| fasim_sim_recovery_learned_detector_real_corpus_hard_negatives_positive_rows | 26 |
| fasim_sim_recovery_learned_detector_real_corpus_hard_negatives_negative_rows | 33 |
| fasim_sim_recovery_learned_detector_real_corpus_hard_negatives_learnable_two_class | 1 |
| fasim_sim_recovery_learned_detector_real_corpus_hard_negatives_source_rows | 103 |
| fasim_sim_recovery_learned_detector_real_corpus_hard_negatives_workload_count | 7 |
| fasim_sim_recovery_learned_detector_real_corpus_hard_negatives_family_count | 4 |
| fasim_sim_recovery_learned_detector_real_corpus_hard_negatives_validate_supported_workload_count | 6 |
| fasim_sim_recovery_learned_detector_real_corpus_hard_negatives_no_legacy_sim_records_workload_count | 1 |
| fasim_sim_recovery_learned_detector_real_corpus_hard_negatives_unique_workloads | 7 |
| fasim_sim_recovery_learned_detector_real_corpus_hard_negatives_unique_families | 4 |
| fasim_sim_recovery_learned_detector_real_corpus_hard_negatives_hard_negative_sources | executor_candidate_non_sim:8,extra_vs_sim_candidate:1,fasim_supported_non_sim:15,near_threshold_rejected_candidate:7,no_legacy_sim_records_proxy:2 |
| fasim_sim_recovery_learned_detector_real_corpus_hard_negatives_hard_negative_source_count | 5 |
| fasim_sim_recovery_learned_detector_real_corpus_hard_negatives_available_requested_negative_sources | executor_candidate_non_sim:16,extra_vs_sim_candidate:2,fasim_supported_non_sim:15,near_threshold_rejected_candidate:8,no_legacy_sim_records_proxy:2 |
| fasim_sim_recovery_learned_detector_real_corpus_hard_negatives_missing_requested_negative_sources | none |
| fasim_sim_recovery_learned_detector_real_corpus_hard_negatives_candidate_eligible_positive_rows | 24 |
| fasim_sim_recovery_learned_detector_real_corpus_hard_negatives_candidate_eligible_negative_rows | 33 |
| fasim_sim_recovery_learned_detector_real_corpus_hard_negatives_heldout_workload_available | 1 |
| fasim_sim_recovery_learned_detector_real_corpus_hard_negatives_heldout_family_available | 1 |
| fasim_sim_recovery_learned_detector_real_corpus_hard_negatives_modeling_gate | ready_for_offline_shadow |
| fasim_sim_recovery_learned_detector_real_corpus_hard_negatives_production_model | 0 |
| fasim_sim_recovery_learned_detector_real_corpus_hard_negatives_sim_labels_runtime_inputs | 0 |
| fasim_sim_recovery_learned_detector_real_corpus_hard_negatives_runtime_behavior_changed | 0 |
| fasim_sim_recovery_learned_detector_real_corpus_hard_negatives_requested_negative_source_executor_candidate_non_sim | 8 |
| fasim_sim_recovery_learned_detector_real_corpus_hard_negatives_available_negative_source_executor_candidate_non_sim | 16 |
| fasim_sim_recovery_learned_detector_real_corpus_hard_negatives_requested_negative_source_extra_vs_sim_candidate | 1 |
| fasim_sim_recovery_learned_detector_real_corpus_hard_negatives_available_negative_source_extra_vs_sim_candidate | 2 |
| fasim_sim_recovery_learned_detector_real_corpus_hard_negatives_requested_negative_source_fasim_supported_non_sim | 15 |
| fasim_sim_recovery_learned_detector_real_corpus_hard_negatives_available_negative_source_fasim_supported_non_sim | 15 |
| fasim_sim_recovery_learned_detector_real_corpus_hard_negatives_requested_negative_source_near_threshold_rejected_candidate | 7 |
| fasim_sim_recovery_learned_detector_real_corpus_hard_negatives_available_negative_source_near_threshold_rejected_candidate | 8 |
| fasim_sim_recovery_learned_detector_real_corpus_hard_negatives_requested_negative_source_no_legacy_sim_records_proxy | 2 |
| fasim_sim_recovery_learned_detector_real_corpus_hard_negatives_available_negative_source_no_legacy_sim_records_proxy | 2 |
| fasim_sim_recovery_learned_detector_real_corpus_hard_negatives_current_split_train_positive | 24 |
| fasim_sim_recovery_learned_detector_real_corpus_hard_negatives_current_split_train_negative | 31 |
| fasim_sim_recovery_learned_detector_real_corpus_hard_negatives_current_split_validation_positive | 2 |
| fasim_sim_recovery_learned_detector_real_corpus_hard_negatives_current_split_validation_negative | 2 |
| fasim_sim_recovery_learned_detector_real_corpus_hard_negatives_current_split_degenerate | 0 |
| fasim_sim_recovery_learned_detector_real_corpus_hard_negatives_family_heldout_train_positive | 12 |
| fasim_sim_recovery_learned_detector_real_corpus_hard_negatives_family_heldout_train_negative | 16 |
| fasim_sim_recovery_learned_detector_real_corpus_hard_negatives_family_heldout_validation_positive | 14 |
| fasim_sim_recovery_learned_detector_real_corpus_hard_negatives_family_heldout_validation_negative | 17 |
| fasim_sim_recovery_learned_detector_real_corpus_hard_negatives_family_heldout_degenerate | 0 |
| fasim_sim_recovery_learned_detector_real_corpus_hard_negatives_workload_heldout_train_positive | 9 |
| fasim_sim_recovery_learned_detector_real_corpus_hard_negatives_workload_heldout_train_negative | 11 |
| fasim_sim_recovery_learned_detector_real_corpus_hard_negatives_workload_heldout_validation_positive | 17 |
| fasim_sim_recovery_learned_detector_real_corpus_hard_negatives_workload_heldout_validation_negative | 22 |
| fasim_sim_recovery_learned_detector_real_corpus_hard_negatives_workload_heldout_degenerate | 0 |
| fasim_sim_recovery_learned_detector_real_corpus_hard_negatives_discovered_marmoset_pair_count | 417 |
| fasim_sim_recovery_learned_detector_real_corpus_hard_negatives_excluded_existing_marmoset_pair_count | 3 |
| fasim_sim_recovery_learned_detector_real_corpus_hard_negatives_eligible_extra_marmoset_pair_count | 396 |
| fasim_sim_recovery_learned_detector_real_corpus_hard_negatives_extra_marmoset_limit | 9 |
| fasim_sim_recovery_learned_detector_real_corpus_hard_negatives_extra_marmoset_min_rna_bytes | 700 |
| fasim_sim_recovery_learned_detector_real_corpus_hard_negatives_selected_extra_case_count | 9 |
| fasim_sim_recovery_learned_detector_real_corpus_hard_negatives_selected_extra_cases | marmoset_extra_ENSG00000234936_1,marmoset_extra_ENSG00000271314_1,marmoset_extra_ENSG00000267714_1,marmoset_extra_ENSG00000272192_1,marmoset_extra_ENSG00000258789_1,marmoset_extra_ENSG00000259054_1,marmoset_extra_ENSG00000259912_1,marmoset_extra_ENSG00000201680_1,marmoset_extra_ENSG00000224091_1 |
| fasim_sim_recovery_learned_detector_real_corpus_hard_negatives_real_corpus_data_line | 1 |
| fasim_sim_recovery_learned_detector_real_corpus_hard_negatives_runtime_model_path | paused |
| fasim_sim_recovery_learned_detector_real_corpus_hard_negatives_model_training_added | 0 |
| fasim_sim_recovery_learned_detector_real_corpus_hard_negatives_deep_learning_dependency | 0 |
| fasim_sim_recovery_learned_detector_real_corpus_hard_negatives_recommended_default_sim_close | 0 |
| fasim_sim_recovery_learned_detector_real_corpus_hard_negatives_selected_extra_source_rows | 27 |
| fasim_sim_recovery_learned_detector_real_corpus_hard_negatives_selected_extra_negative_rows | 6 |
| fasim_sim_recovery_learned_detector_real_corpus_hard_negatives_selected_extra_positive_rows | 9 |

## Selected Extra Marmoset Cases

| Label | Gene | DNA bytes | RNA bytes | DNA | RNA |
| --- | --- | ---: | ---: | --- | --- |
| marmoset_extra_ENSG00000234936_1 | ENSG00000234936.1 | 5052 | 708 | `/data/wenyujianData/humanLncAtlas/wenyujian/inputForShenzhen-marmoset/ENSG00000234936.1_marmoset-targetDNA/ENSG00000229664.1_marmoset-4544288-4549288.fa` | `/data/wenyujianData/humanLncAtlas/wenyujian/inputForShenzhen-marmoset/ENSG00000234936.1_marmoset/marmoset_chr14_ENSG00000234936.1_AC010883.5.fa` |
| marmoset_extra_ENSG00000271314_1 | ENSG00000271314.1 | 5054 | 728 | `/data/wenyujianData/humanLncAtlas/wenyujian/inputForShenzhen-marmoset/ENSG00000271314.1_marmoset-targetDNA/ENSG00000237857.2_marmoset-78613317-78618317.fa` | `/data/wenyujianData/humanLncAtlas/wenyujian/inputForShenzhen-marmoset/ENSG00000271314.1_marmoset/marmoset_chr1_ENSG00000271314.1_RP11-435O5.6.fa` |
| marmoset_extra_ENSG00000267714_1 | ENSG00000267714.1 | 5050 | 741 | `/data/wenyujianData/humanLncAtlas/wenyujian/inputForShenzhen-marmoset/ENSG00000267714.1_marmoset-targetDNA/ENSG00000224078.8_marmoset-878084-883084.fa` | `/data/wenyujianData/humanLncAtlas/wenyujian/inputForShenzhen-marmoset/ENSG00000267714.1_marmoset/marmoset_chr22_ENSG00000267714.1_CTD-2540B15.6.fa` |
| marmoset_extra_ENSG00000272192_1 | ENSG00000272192.1 | 5055 | 757 | `/data/wenyujianData/humanLncAtlas/wenyujian/inputForShenzhen-marmoset/ENSG00000272192.1_marmoset-targetDNA/ENSG00000272192.1_marmoset-18171195-18176195.fa` | `/data/wenyujianData/humanLncAtlas/wenyujian/inputForShenzhen-marmoset/ENSG00000272192.1_marmoset/marmoset_chr16_ENSG00000272192.1_CTD-2532N20.1.fa` |
| marmoset_extra_ENSG00000258789_1 | ENSG00000258789.1 | 5053 | 774 | `/data/wenyujianData/humanLncAtlas/wenyujian/inputForShenzhen-marmoset/ENSG00000258789.1_marmoset-targetDNA/ENSG00000228126.1_marmoset-4490400-4495400.fa` | `/data/wenyujianData/humanLncAtlas/wenyujian/inputForShenzhen-marmoset/ENSG00000258789.1_marmoset/marmoset_chr10_ENSG00000258789.1_RP11-507K2.3.fa` |
| marmoset_extra_ENSG00000259054_1 | ENSG00000259054.1 | 5052 | 803 | `/data/wenyujianData/humanLncAtlas/wenyujian/inputForShenzhen-marmoset/ENSG00000259054.1_marmoset-targetDNA/ENSG00000272908.1_marmoset-6146721-6151721.fa` | `/data/wenyujianData/humanLncAtlas/wenyujian/inputForShenzhen-marmoset/ENSG00000259054.1_marmoset/marmoset_chr10_ENSG00000259054.1_AE000662.93.fa` |
| marmoset_extra_ENSG00000259912_1 | ENSG00000259912.1 | 5053 | 805 | `/data/wenyujianData/humanLncAtlas/wenyujian/inputForShenzhen-marmoset/ENSG00000259912.1_marmoset-targetDNA/ENSG00000259912.1_marmoset-2161282-2166282.fa` | `/data/wenyujianData/humanLncAtlas/wenyujian/inputForShenzhen-marmoset/ENSG00000259912.1_marmoset/marmoset_chr20_ENSG00000259912.1_CTC-527H23.2.fa` |
| marmoset_extra_ENSG00000201680_1 | ENSG00000201680.1 | 5054 | 875 | `/data/wenyujianData/humanLncAtlas/wenyujian/inputForShenzhen-marmoset/ENSG00000201680.1_marmoset-targetDNA/ENSG00000201680.1_marmoset-32015574-32020574.fa` | `/data/wenyujianData/humanLncAtlas/wenyujian/inputForShenzhen-marmoset/ENSG00000201680.1_marmoset/marmoset_chr4_ENSG00000201680.1_Y_RNA.fa` |
| marmoset_extra_ENSG00000224091_1 | ENSG00000224091.1 | 5053 | 879 | `/data/wenyujianData/humanLncAtlas/wenyujian/inputForShenzhen-marmoset/ENSG00000224091.1_marmoset-targetDNA/ENSG00000267030.1_marmoset-4157905-4162905.fa` | `/data/wenyujianData/humanLncAtlas/wenyujian/inputForShenzhen-marmoset/ENSG00000224091.1_marmoset/marmoset_chr11_ENSG00000224091.1_AC104389.16.fa` |

## Hard Negative Source Audit

| Source | Dataset rows | Source rows available |
| --- | ---: | ---: |
| executor_candidate_non_sim | 8 | 16 |
| extra_vs_sim_candidate | 1 | 2 |
| fasim_supported_non_sim | 15 | 15 |
| near_threshold_rejected_candidate | 7 | 8 |
| no_legacy_sim_records_proxy | 2 | 2 |

No unavailable hard-negative rows are fabricated.

## Source Row Mix

| Source row kind | Rows |
| --- | ---: |
| accepted_candidate | 14 |
| executor_candidate | 41 |
| fasim_record | 22 |
| sim_record | 26 |

## Corpus Gate

| Gate | Value |
| --- | --- |
| workload_count | 7 |
| family_count | 4 |
| validate_supported_workload_count | 6 |
| no_legacy_sim_records_workload_count | 1 |
| hard_negative_source_count | 5 |
| heldout_workload_available | 1 |
| heldout_family_available | 1 |
| modeling_gate | ready_for_offline_shadow |

This PR deliberately stays on the data-expansion path after the #88 negative model result. Any future model shadow should be a separate offline evaluation PR and must re-check held-out behavior.

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
