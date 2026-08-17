# Biological Top-K Successor Validation Status

```text
epoch_id = biological_topk_successor_v2
predecessor_commit = 7fae3de6b13780d7cc0776038489cf2f22072339
predecessor_decision = blocked_fixed_budget
fixed_total_artifact_storage_bytes = 68719476736
active_phase = null
phase_0_status = pass
phase_1_status = pass
phase_2_status = pass
phase_3_status = pass
phase_4_status = pass
phase_5_status = pass
phase_6_status = no_go
phase_7_status = not_authorized_previous_no_go
phase_8_status = not_authorized_previous_no_go
phase_9_status = not_authorized_previous_no_go
contract_status = biological_utility_no_go
gpu_screen_status = experimental
bioinformatics_route = closed_biological_utility_gap
```

The owner authorized a separate 64 GiB successor epoch after the predecessor
stopped under its fixed 8 GiB quota. The predecessor commit, tracked evidence,
two runtime artifact roots, missing attempts, and `blocked_fixed_budget`
decision remain immutable. No predecessor scientific comparison occurred.

Successor Phase 0 froze the new protocol, exact authorization, predecessor
boundary, state schema, and checker without creating prediction output. Phase 1
reused the exact scientific contract and statistical thresholds, added all 178
predecessor Phase 4 workloads to the exclusion boundary, and froze a corrected
resource model using terminal receipt timing and directory byte counts only.

## Phase 1 Evidence

```text
scientific_contract_changed = false
comparator_changed = false
N_panel = 178
n_binary_required = 124
fresh_eligible_query_rows = 26903
fresh_unique_query_digests = 26882
fresh_unique_target_digests_short = 606
fresh_unique_target_digests_medium = 559
fresh_unique_target_digests_large = 480
predecessor_phase4_exclusion_rows_added = 178
resource_observations = 165
projected_total_artifact_point_with_reservation = 21641092710
projected_total_artifact_upper_95_with_reservation = 21994055006
total_max_observed_stress_with_reservation = 52172798966
fixed_total_artifact_storage_bytes = 68719476736
storage_margin_bytes = 16546677770
projected_gpu_hours_upper_95 = 5.8282239559473235
projected_scheduled_wall_upper_95_seconds = 29630.848795678117
all_information_gates_pass = true
all_resource_gates_pass = true
fresh_pair_selected = false
new_prediction_run = false
```

## Phase 2 Evidence

```text
historical_comparisons_rerun = 184
ranking_results = 552
detail_rows = 2391
strict_row_diagnostic_mismatches_preserved = 14
technical_failures = 0
input_identity_mismatches = 0
scientific_contract_changed = false
comparator_changed = false
regression_artifacts_byte_identical_to_predecessor = true
fresh_pair_selected = false
new_prediction_run = false
```

## Phase 3 Evidence

```text
selection_kind = input_only_static_source_metadata
primary_workloads = 178
technical_repeat_instances = 6
validation_instances = 184
planned_attempts = 368
predecessor_query_overlap = 0
predecessor_target_overlap = 0
predecessor_pair_overlap = 0
pair_order_AG = 92
pair_order_GA = 92
fixed_total_artifact_storage_bytes = 68719476736
manifest_specific_storage_gate = pass
manifest_specific_gpu_hours_gate = pass
manifest_specific_scheduled_wall_gate = pass
raw_telemetry_policy = validate_then_deterministic_lossless_gzip_before_next_attempt
new_prediction_run = false
```

## Phase 4 Evidence

```text
decision = pass
planned_attempts = 368
terminal_attempts = 368
successful_attempts = 368
technical_failures = 0
comparison_started_by_runner = false
offline_comparisons = 184
binary_gate_denominator = 177
n_binary_required = 124
informative_reference_nonempty_workloads = 177
total_reference_candidate_sites = 856
score_complete_set_successes = 174/177
score_complete_set_lcb = 0.9567791704809228870584073383547318964204588678636645639634031355891670467556213
stability_complete_set_successes = 177/177
nt_complete_set_successes = 175/177
all_top1_retention_successes = 177/177
all_six_endpoint_gates_pass = true
input_identity_mismatches = 0
ambiguous_matches = 0
unexpected_fallbacks = 0
telemetry_archives = 184
raw_telemetry_files = 0
actual_gpu_hours = 6.4305268712717547
actual_scheduled_elapsed_wall_seconds = 32617.130879
actual_total_artifact_storage_bytes_with_tracked_reservation = 19889990755
artifact_storage_margin_bytes = 48829485981
fixed_budget_gate_pass = true
infrastructure_repair_epochs_used = 0
```

The frozen successor holdout passed every fixed-sequence concordance endpoint,
the independent information and identity gates, the zero-technical-failure
gate, and the fixed 64 GiB resource gate. Phase 5 independent experimental
benchmark preregistration is therefore authorized. Product status remains
`experimental`, and rank order remains diagnostic-only.

## Phase 5 Evidence

```text
decision = pass
distinct_lncRNA_outer_units = 5
primary_datasets = 5
assay_type_classes = ChIRP
cross_assay_generality_claim = not_supported
regions_per_dataset = 1000
positives_per_dataset = 100
negatives_per_positive = 9
total_regions = 5000
maximum_gc_absolute_difference = 0.049792531120
LINC01116_4x_feasible_windows = 3324
LINC01116_8x_feasible_windows = 830
LINC01116_eligible_GRCh38_windows = 806
attempts_A_G_X = 5/5/5
bootstrap_replicates = 10000
bootstrap_seed = 20260816
external_predictor = Triplexator_v1.3.3
evaluation_prediction_started = false
phase_6_authorized = true
```

Phase 5 froze five independent evaluation lncRNAs, deterministic public-data
labels and matched negatives, exact region scoring, the E1-E4 paired
hierarchical bootstrap, and independent A/G/X attempts. Only ChIRP satisfied
the input availability definition, so no cross-assay generality claim is
supported. Product status remains `experimental`; no evaluation prediction has
run, and Phase 6 may start only after the Phase 5 commit passes its read-only
post-commit check.

Phase 6 ran at parent commit `dc2271b` under the 15 frozen A/G/X attempts,
96 GPU-hours, 96 CPU wall-hours, one infrastructure repair epoch, and the
unchanged 64 GiB total artifact quota. Prediction backends received only their
query, target, and executable inside the isolated sandbox. Labels remained
sealed until all 15 attempt receipts were terminal.

## Phase 6 Evidence

```text
decision = no_go
planned_attempts = 15
terminal_attempts = 15
successful_primary_attempts = 10/10
primary_technical_failures = 0
external_technical_failures = 5/5
scientific_retries_or_replacements = 0
E1_LCB_GPU_minus_CPU_AUCPR = -0.00016433297083244259
E1_pass = true
E2_LCB_GPU_minus_CPU_recall_at_P = 0
E2_pass = true
E3_LCB_GPU_AUCPR_minus_prevalence = 0.0083898682678954888
E3_pass = true
E4_LCB_log_GPU_top_P_enrichment = -0.024581674369296539
E4_pass = false
biological_utility_pass = false
gpu_backend_hours = 0.28682696827055554
cpu_and_external_backend_wall_hours = 0.4085622015505555
scheduled_epoch_elapsed_wall_seconds = 3004.548254
actual_total_artifact_storage_bytes_with_tracked_reservation = 21880213804
artifact_storage_margin_bytes = 46839262932
fixed_budget_gates = pass
```

All ten primary A/G attempts completed successfully and the non-inferiority
endpoints E1-E2 plus absolute AUCPR endpoint E3 passed. E4 failed its frozen
strict-positive one-sided lower-bound requirement, so the intersection-union
gate is a scientific no-go even though its point estimate was positive. All
five external Triplexator attempts were retained as terminal failures after
the frozen absolute output path prevented creation of Triplexator temporary
summary files; they were non-comparable and unused in primary inference. No
retry or replacement occurred. Phase 7-9 are not authorized, product status
remains `experimental`, and the bioinformatics route is closed for this
biological-utility gap.
