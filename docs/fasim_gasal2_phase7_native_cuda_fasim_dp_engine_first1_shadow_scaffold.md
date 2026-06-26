# Fasim GASAL2 Phase 7 Native CUDA Fasim DP Engine First1 Shadow Scaffold

This checkpoint turns the native CUDA/Fasim DP engine design into a
fail-closed first1 telemetry scaffold. It is not a runtime reduction path and
does not complete the active broad goal.

## Scope

```text
phase7_native_cuda_fasim_dp_engine_first1_shadow_scaffold = fail_closed_shadow
previous_checkpoint = docs/fasim_gasal2_phase7_native_cuda_fasim_dp_engine_design_spec_or_path_a_acceptance.md
previous_gate = phase7_native_cuda_fasim_dp_engine_first1_fail_closed_shadow_scaffold
required_runtime_env = FASIM_GASAL2_PHASE7_NATIVE_CUDA_FASIM_DP_ENGINE_FIRST1_SHADOW
telemetry_prefix = benchmark.fasim_gasal2_phase7_native_cuda_fasim_dp_engine_
runtime_default = off
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

The scaffold records the first1 native-DP proof surface without producing a
usable certificate. It therefore fails closed to full CPU replay and keeps CPU
`aligner.Align()` as the only semantic authority.

## Observed Fail-Closed Contract

```text
requested = 1
active = 1
native_scoreinfo_tiles > 0
forward_endpoint_witnesses = 0
reverse_start_witnesses = 0
traceback_cigar_witnesses = 0
certificates = 0
certificate_false_negatives = 0
missing_required_attempts = native_scoreinfo_tiles
scoreinfo_byte_mismatches = 0
endpoint_mismatches = 0
reverse_start_mismatches = 0
cigar_mismatches = 0
full_row_mismatches = 0
digest_mismatches = 0
full_rows_equal = 0
digest_match = 0
cpu_align_fallbacks = native_scoreinfo_tiles
runtime_reduction_enabled = 0
runtime_work_drop_enabled = 0
scoreinfo_prealign_reduced = 0
align_side_reduced = 0
fallback_accounting_clean = 0
fallback_to_full_cpu_replay = 1
gate_first1_shadow_pass = 0
gate_first1_pass = 0
```

The output bytes must match the baseline run because this checkpoint does not
consume GPU results. The missing required attempts are accounted as CPU
fallbacks, not skipped work.

## Authority

```text
CPU aligner.Align() authority = 1
GPU score authority = 0
GPU endpoint authority = 0
GPU CIGAR authority = 0
GPU traceback authority = 0
GPU output authority = 0
GPU digest authority = 0
gpu_score_authority = 0
gpu_endpoint_authority = 0
gpu_cigar_traceback_output_authority = 0
gpu_output_digest_authority = 0
```

No endpoint, CIGAR, traceback, output, digest, candidate-state, or final
score authority moves to GPU in this checkpoint.

## Decision

```text
path_b_native_cuda_fasim_dp_engine_first1_shadow_scaffold = 1
phase7_native_cuda_fasim_dp_engine_first1_shadow_scaffold_status = fail_closed_no_runtime_reduction
phase7_native_cuda_fasim_dp_engine_runtime_reduction_enabled = 0
phase7_native_cuda_fasim_dp_engine_runtime_work_drop_enabled = 0
phase7_native_cuda_fasim_dp_engine_gate_first1_shadow_pass = 0
path_b_runtime_reduction_pr_allowed = 0
path_b_runtime_work_drop_allowed = 0
first1_runtime_reduction_gate_pass = 0
first64_runtime_allowed = 0
next_valid_gate = phase7_native_cuda_fasim_dp_engine_first1_shadow_consumer_or_no_go
current_execution_gate = phase7_native_cuda_fasim_dp_engine_first1_shadow_consumer_or_no_go
current_next_pr = fasim_native_cuda_fasim_dp_engine_first1_shadow_consumer_or_no_go
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

The next gate must decide whether this native-DP family can produce and
consume a real first1 certificate before CPU Align work. If it cannot, this
family must stop or fork to a genuinely different design. It is still
forbidden to run first64 or claim broad completion before first1 proves an
output-equivalent runtime reduction.

## Forbidden

```text
no real opt-in
no runtime reduction
no runtime work drop
no first64 runtime
no GPU score authority
no GPU endpoint authority
no GPU CIGAR authority
no GPU traceback authority
no GPU output authority
no GPU digest authority
no top5-only completion claim
no archive-only completion claim
no output-drift speedup claim
```
