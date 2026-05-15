# Fasim SIM-Close Learned Detector Model Shadow

## Learned Detector Model Shadow

This is a diagnostic-only offline model shadow over the learned-detector dataset TSV. It trains or scores candidate rows outside the Fasim runtime path and does not change recovery boxes, guards, replacement, output ordering, or default behavior.

Dataset: `/data/wenyujianData/LongTarget-exact-sim/.worktrees/fasim-sim-recovery-score-landscape-detector-shadow/.tmp/fasim_sim_recovery_learned_detector_model/learned_detector_dataset.tsv`

| Metric | Value |
| --- | --- |
| fasim_sim_recovery_learned_detector_model_enabled | 1 |
| fasim_sim_recovery_learned_detector_model_dataset_rows | 118 |
| fasim_sim_recovery_learned_detector_model_sim_record_rows | 40 |
| fasim_sim_recovery_learned_detector_model_candidate_rows | 30 |
| fasim_sim_recovery_learned_detector_model_accepted_rows | 14 |
| fasim_sim_recovery_learned_detector_model_positive_rows | 30 |
| fasim_sim_recovery_learned_detector_model_negative_rows | 0 |
| fasim_sim_recovery_learned_detector_model_learnable_two_class | 0 |
| fasim_sim_recovery_learned_detector_model_model | heuristic_score_nt_identity |
| fasim_sim_recovery_learned_detector_model_sklearn_used | 0 |
| fasim_sim_recovery_learned_detector_model_evaluation_mode | resubstitution_smoke |
| fasim_sim_recovery_learned_detector_model_top_n | 14 |
| fasim_sim_recovery_learned_detector_model_current_accepted_recall | 46.666667 |
| fasim_sim_recovery_learned_detector_model_current_accepted_precision | 100.000000 |
| fasim_sim_recovery_learned_detector_model_current_accepted_recall_vs_sim | 35.000000 |
| fasim_sim_recovery_learned_detector_model_model_selected_rows | 14 |
| fasim_sim_recovery_learned_detector_model_model_selected_positive_rows | 14 |
| fasim_sim_recovery_learned_detector_model_model_topn_recall | 46.666667 |
| fasim_sim_recovery_learned_detector_model_model_topn_precision | 100.000000 |
| fasim_sim_recovery_learned_detector_model_model_topn_recall_vs_sim | 35.000000 |
| fasim_sim_recovery_learned_detector_model_candidate_oracle_selected_rows | 30 |
| fasim_sim_recovery_learned_detector_model_candidate_oracle_positive_rows | 30 |
| fasim_sim_recovery_learned_detector_model_candidate_oracle_recall_vs_sim | 75.000000 |
| fasim_sim_recovery_learned_detector_model_candidate_oracle_precision | 100.000000 |
| fasim_sim_recovery_learned_detector_model_model_auc | 0.000000 |
| fasim_sim_recovery_learned_detector_model_positive_score_median | 210.406150 |
| fasim_sim_recovery_learned_detector_model_negative_score_median | 0.000000 |
| fasim_sim_recovery_learned_detector_model_guard_policy_shadow_enabled | 1 |
| fasim_sim_recovery_learned_detector_model_guard_policy_shadow_policies | 8 |
| fasim_sim_recovery_learned_detector_model_guard_policy_shadow_best_non_oracle_policy | relaxed_score_nt_rank3 |
| fasim_sim_recovery_learned_detector_model_guard_policy_shadow_best_non_oracle_recall_vs_sim | 45.000000 |
| fasim_sim_recovery_learned_detector_model_guard_policy_shadow_best_non_oracle_precision | 100.000000 |
| fasim_sim_recovery_learned_detector_model_guard_policy_shadow_current_guard_recall_vs_sim | 35.000000 |
| fasim_sim_recovery_learned_detector_model_guard_policy_shadow_current_guard_precision | 100.000000 |
| fasim_sim_recovery_learned_detector_model_guard_policy_shadow_accept_all_executor_recall_vs_sim | 75.000000 |
| fasim_sim_recovery_learned_detector_model_guard_policy_shadow_accept_all_executor_precision | 100.000000 |
| fasim_sim_recovery_learned_detector_model_guard_policy_shadow_relaxed_score_nt_rank3_recall_vs_sim | 45.000000 |
| fasim_sim_recovery_learned_detector_model_guard_policy_shadow_relaxed_score_nt_rank3_precision | 100.000000 |
| fasim_sim_recovery_learned_detector_model_production_model | 0 |

## Guard Policy Shadow

These rows replay simple non-oracle guard policies over exported executor candidates. They are TSV-only diagnostics; they do not change the runtime `combined_non_oracle` guard or SIM-close output.

| Policy | Selected | Positive | Negative | Recall within candidates | Recall vs SIM | Precision |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| current_guard | 14 | 14 | 0 | 46.666667 | 35.000000 | 100.000000 |
| score_nt_threshold | 14 | 14 | 0 | 46.666667 | 35.000000 | 100.000000 |
| score_nt_rank5 | 14 | 14 | 0 | 46.666667 | 35.000000 | 100.000000 |
| local_rank_top3 | 14 | 14 | 0 | 46.666667 | 35.000000 | 100.000000 |
| relaxed_score_nt_rank3 | 18 | 18 | 0 | 60.000000 | 45.000000 | 100.000000 |
| relaxed_score_nt_rank5 | 18 | 18 | 0 | 60.000000 | 45.000000 | 100.000000 |
| relaxed_score_nt_rank10 | 18 | 18 | 0 | 60.000000 | 45.000000 | 100.000000 |
| accept_all_executor | 30 | 30 | 0 | 100.000000 | 75.000000 | 100.000000 |

## Guard Policy By Workload

This table keeps workload-specific behavior visible so a policy that is clean on one real case but dirty on a fixture is not hidden by aggregate telemetry.

| Workload | Policy | Selected | Positive | Negative | Recall within candidates | Recall vs SIM | Precision |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| human_lnc_atlas_508kb_target | current_guard | 14 | 14 | 0 | 46.666667 | 35.000000 | 100.000000 |
| human_lnc_atlas_508kb_target | score_nt_threshold | 14 | 14 | 0 | 46.666667 | 35.000000 | 100.000000 |
| human_lnc_atlas_508kb_target | score_nt_rank5 | 14 | 14 | 0 | 46.666667 | 35.000000 | 100.000000 |
| human_lnc_atlas_508kb_target | local_rank_top3 | 14 | 14 | 0 | 46.666667 | 35.000000 | 100.000000 |
| human_lnc_atlas_508kb_target | relaxed_score_nt_rank3 | 18 | 18 | 0 | 60.000000 | 45.000000 | 100.000000 |
| human_lnc_atlas_508kb_target | relaxed_score_nt_rank5 | 18 | 18 | 0 | 60.000000 | 45.000000 | 100.000000 |
| human_lnc_atlas_508kb_target | relaxed_score_nt_rank10 | 18 | 18 | 0 | 60.000000 | 45.000000 | 100.000000 |
| human_lnc_atlas_508kb_target | accept_all_executor | 30 | 30 | 0 | 100.000000 | 75.000000 | 100.000000 |

## Interpretation

`current_accepted_recall` and `model_topn_recall` are measured within the executor-candidate rows. The `*_recall_vs_sim` metrics are the production-relevant view against all validate-supported SIM records.

`candidate_oracle_*` means accepting every exported executor candidate using post-hoc SIM labels as an upper-bound diagnostic. It is not a runtime policy and must not be used for production selection.

This dataset has only one candidate label class, so no two-class learned ranker can be validated from it. The result should be read as guard/detector diagnostic evidence, not model-quality evidence.

`evaluation_mode=resubstitution_smoke` means the model is evaluated on the same rows it was fit on. This is only a separability smoke check, not held-out real-corpus evidence.

## Decision

This report is a guard/detector shadow only. The best non-oracle guard policy is `relaxed_score_nt_rank3` with 45.000000 recall vs SIM and 100.000000 precision. The current guard remains the runtime behavior.

`accept_all_executor` is an oracle-style upper-bound diagnostic over already exported executor candidates. It does not solve records that were never covered by recovery boxes, and it must not be used as a production policy.

Do not default or recommend SIM-close mode from this report. Broader real-corpus coverage and a detector for not-box-covered records are still required before any high-accuracy claim.

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

Do not use this model for production selection.

