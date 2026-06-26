# Fasim GASAL2 Phase 7 Post-v5.3 New GPU Engine Real-Source First1 Shadow Scaffold

This checkpoint makes the current Phase 7.1 gate observable. It is a
fail-closed scaffold, not a runtime reduction, not a first1 pass, and not a
completion claim.

## Scope

```text
phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_scaffold = fail_closed_no_real_source
previous_checkpoint = docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_first1_spec_or_path_a_acceptance.md
previous_gate = phase7_new_gpu_engine_real_source_first1_shadow_or_path_a_acceptance
required_runtime_env = FASIM_GASAL2_PHASE7_POST_V5_3_NEW_GPU_ENGINE_REAL_SOURCE_FIRST1_SHADOW
telemetry_prefix = benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_
runtime_reduction_enabled = 0
runtime_work_drop_enabled = 0
first1_runtime_reduction_gate_pass = 0
first64_runtime_allowed = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

The scaffold is default-off. When requested, it records that the real-source
first1 path has no real Fasim runtime certificate source and no real work-drop
path yet, then falls closed to CPU authority.

## Runtime Telemetry Contract

Expected fail-closed telemetry when the env is set:

```text
requested = 1
active = 0
real_fasim_runtime_certificate_source = 0
real_fasim_runtime_work_drop_path = 0
runtime_certificate_is_synthetic = 0
gpu_tasks = 0
gpu_candidate_groups = 0
gpu_replay_attempts = 0
gpu_selected_attempts = 0
gpu_skipped_groups = 0
gpu_skipped_attempts = 0
cpu_replay_attempts = 0
baseline_cpu_attempts = 0
missing_certificate = 1
fallback_to_full_cpu_replay = 1
scoreinfo_prealign_reduced = 0
align_side_reduced = 0
fallback_accounting_clean = 0
certificate_false_negatives = 0
missing_required_attempts = 0
cpu_align_authority = 1
gpu_endpoint_cigar_traceback_output_authority = 0
full_rows_equal = 0
digest_match = 0
missing_rows = 0
extra_rows = 0
triplex_mismatches = 0
candidate_wall_seconds = 0
baseline_wall_seconds = 0
gate_first1_pass = 0
```

The zero equality fields are not mismatch evidence. They mean the scaffold did
not run a candidate replay and therefore cannot claim a first1 pass.

## Why This Exists

The previous synthetic certificate producer showed that an API can emit
certificate-shaped telemetry, but it did not provide:

```text
nonzero real_fasim_runtime_certificate_source
nonzero real_fasim_runtime_work_drop_path
runtime_certificate_is_synthetic = 0
```

This scaffold prevents that synthetic producer from being relabelled as a real
runtime proof. The only valid next Path B step is to implement a real runtime
certificate source or explicitly accept Path A scoped completion.

## Decision

```text
real_source_first1_shadow_gate_pass = 0
runtime_reduction_enabled = 0
runtime_work_drop_enabled = 0
next_valid_gate = implement_real_source_certificate_source_or_path_a_acceptance
current_next_pr = fasim_new_gpu_engine_real_source_certificate_source_or_path_a_acceptance
```

Do not run first64 from this scaffold. Do not add a broad-replacement workload
matrix row from this scaffold.

## Authority Model

```text
CPU aligner.Align() authority = 1
GPU endpoint authority = 0
GPU CIGAR authority = 0
GPU traceback authority = 0
GPU output authority = 0
GPU digest authority = 0
```

## Non-Completion

```text
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

This checkpoint advances the active goal by making the current real-source
first1 gate executable and fail-closed. It does not prove Path B and does not
close the active goal.
