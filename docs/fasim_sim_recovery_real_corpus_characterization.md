# Fasim SIM-Close Recovery Real-Corpus Characterization

Base branch:

```text
fasim-sim-recovery-real-mode-characterization
```

This report characterizes the default-off `FASIM_SIM_RECOVERY=1` SIM-close harness on external FASTA cases. It adds no new recovery logic and does not change scoring, threshold, non-overlap, GPU, filter, or default fast-mode behavior.

`SIM-close wall seconds` measures the side recovery/merge path after the fast Fasim output is available. The end-to-end SIM-close harness cost is reported separately as fast seconds plus SIM-close wall seconds.

| Setting | Value |
| --- | --- |
| cases | 2 |
| repeat | 2 |
| fast_mode | default Fasim on the same FASTA |
| sim_close_mode | FASIM_SIM_RECOVERY=1 side-output harness |
| validate_mode | post-hoc legacy SIM only for validate cases |

## Case Summary

| Case | Validated | Fast digest | SIM-close digest | Validate digest | Fast records | SIM-close records | Boxes | Cells | Cell fraction | Recovered candidates | Accepted | Suppressed | Recall vs SIM | Precision vs SIM | Extra vs SIM | Overlap conflicts | Fallbacks |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| human_lnc_atlas_17kb_target | yes | sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 | sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 | sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 | 0 | 0 | 0 | 0 | 0.000000 | 0 | 0 | 0 | NA | NA | NA | 0 | 0 |
| human_lnc_atlas_508kb_target | no | sha256:25469e60179a524dd712d7ef69ee0c8e379a17f8472be3c2843cd14eda04d221 | sha256:20c37af91408ed5604de79a33ceb0ec470f954f39ab9103f31d07499f22810c9 | NA | 34 | 14 | 34 | 501250 | 0.064813 | 30 | 14 | 34 | NA | NA | NA | 0 | 0 |

## Run Summary

| Case | Run | Fast seconds | Fast digest | SIM-close digest | Validate digest | Output records | Boxes | Cells | Executor seconds | SIM-close wall seconds | Validate wall seconds |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| human_lnc_atlas_17kb_target | 1 | 0.043039 | sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 | sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 | sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 | 0 | 0 | 0 | 0.000110 | 0.000688 | 2.659064 |
| human_lnc_atlas_17kb_target | 2 | 0.042506 | sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 | sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 | sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 | 0 | 0 | 0 | 0.000053 | 0.000266 | 2.631964 |
| human_lnc_atlas_508kb_target | 1 | 1.196000 | sha256:25469e60179a524dd712d7ef69ee0c8e379a17f8472be3c2843cd14eda04d221 | sha256:20c37af91408ed5604de79a33ceb0ec470f954f39ab9103f31d07499f22810c9 | NA | 14 | 34 | 501250 | 1.050282 | 1.054317 | NA |
| human_lnc_atlas_508kb_target | 2 | 1.244500 | sha256:25469e60179a524dd712d7ef69ee0c8e379a17f8472be3c2843cd14eda04d221 | sha256:20c37af91408ed5604de79a33ceb0ec470f954f39ab9103f31d07499f22810c9 | NA | 14 | 34 | 501250 | 1.141088 | 1.145444 | NA |

## Aggregate

| Metric | Value |
| --- | --- |
| fasim_sim_recovery_real_corpus_cases | 2 |
| fasim_sim_recovery_real_corpus_repeat | 2 |
| fasim_sim_recovery_real_corpus_validated_cases | 1 |
| fasim_sim_recovery_real_corpus_validate_supported_cases | 0 |
| fasim_sim_recovery_real_corpus_fast_digest_stable | 1 |
| fasim_sim_recovery_real_corpus_sim_close_digest_stable | 1 |
| fasim_sim_recovery_real_corpus_validate_selection_stable | 1 |
| fasim_sim_recovery_real_corpus_fast_mode_output_mutations | 0 |
| fasim_sim_recovery_real_corpus_fast_total_seconds_median | 1.263022 |
| fasim_sim_recovery_real_corpus_sim_close_wall_seconds_median | 1.100357 |
| fasim_sim_recovery_real_corpus_sim_close_end_to_end_seconds_median | 2.363380 |
| fasim_sim_recovery_real_corpus_validate_wall_seconds_median | 2.645514 |
| fasim_sim_recovery_real_corpus_validate_end_to_end_seconds_median | 3.908536 |
| fasim_sim_recovery_real_corpus_boxes_median | 34.000000 |
| fasim_sim_recovery_real_corpus_cells_median | 501250.000000 |
| fasim_sim_recovery_real_corpus_full_search_cells_median | 800442981.000000 |
| fasim_sim_recovery_real_corpus_cell_fraction_median | 0.062622 |
| fasim_sim_recovery_real_corpus_executor_seconds_median | 1.095766 |
| fasim_sim_recovery_real_corpus_fasim_records_median | 34.000000 |
| fasim_sim_recovery_real_corpus_recovered_candidates_median | 30.000000 |
| fasim_sim_recovery_real_corpus_recovered_accepted_median | 14.000000 |
| fasim_sim_recovery_real_corpus_fasim_suppressed_median | 34.000000 |
| fasim_sim_recovery_real_corpus_sim_close_output_records_median | 14.000000 |
| fasim_sim_recovery_real_corpus_recall_vs_sim_median | 0.000000 |
| fasim_sim_recovery_real_corpus_precision_vs_sim_median | 0.000000 |
| fasim_sim_recovery_real_corpus_extra_vs_sim_median | 0.000000 |
| fasim_sim_recovery_real_corpus_overlap_conflicts_median | 0.000000 |
| fasim_sim_recovery_real_corpus_fallbacks_median | 0.000000 |
| fasim_sim_recovery_real_corpus_sim_labels_production_inputs | 0 |
| fasim_sim_recovery_real_corpus_recommendation | experimental_opt_in |

## Decision

Keep `FASIM_SIM_RECOVERY=1` as an experimental opt-in. This characterization checks output stability and recovery footprint on the supplied FASTA cases; production recommendation still requires broader real-corpus evidence.

Full legacy SIM validation was requested for at least one case, but no validate-supported SIM records were produced, so recall/precision/extra metrics are not interpreted here.

Treat this as stability and footprint evidence only when validation is unavailable; SIM-close output may intentionally differ from the fast-mode Fasim digest.

Do not recommend or default SIM-close mode from this PR.

## Scope

```text
Default Fasim output changed: no
SIM labels used as production input: no
Validation affects production selection: no
Scoring/threshold/non-overlap behavior change: no
GPU/filter behavior change: no
Recommended/default mode: no
Production accuracy claim: no
```
