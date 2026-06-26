# Fasim GASAL2 Phase 7 Native CUDA Fasim DP Engine First1 Shadow Consumer No-Go

This checkpoint closes the native CUDA/Fasim DP engine first1 shadow consumer
gate. It is a no-go checkpoint for the current native-DP scaffold family, not
a runtime implementation, not a work-drop implementation, and not a completion
claim.

## Scope

```text
phase7_native_cuda_fasim_dp_engine_first1_shadow_consumer_no_go = recorded
previous_checkpoint = docs/fasim_gasal2_phase7_native_cuda_fasim_dp_engine_first1_shadow_scaffold.md
previous_gate = phase7_native_cuda_fasim_dp_engine_first1_shadow_consumer_or_no_go
runtime_reduction_enabled = 0
runtime_work_drop_enabled = 0
first1_runtime_reduction_gate_pass = 0
first64_runtime_allowed = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

The previous first1 shadow made the native-DP proof surface observable, but it
deliberately remained fail-closed:

```text
native_scoreinfo_tiles > 0
forward_endpoint_witnesses = 0
reverse_start_witnesses = 0
traceback_cigar_witnesses = 0
certificates = 0
missing_required_attempts = native_scoreinfo_tiles
cpu_align_fallbacks = native_scoreinfo_tiles
fallback_to_full_cpu_replay = 1
runtime_reduction_enabled = 0
runtime_work_drop_enabled = 0
scoreinfo_prealign_reduced = 0
align_side_reduced = 0
fallback_accounting_clean = 0
gate_first1_shadow_pass = 0
gate_first1_pass = 0
```

The candidate output bytes remain unchanged because the shadow fully replays
CPU work. That is correctness-safe, but it is not a reducing runtime path.

## Consumer Result

A real consumer would need a pre-drop native-DP certificate covering the
complete row contract before any scoreInfo/preAlign group or Align-side
attempt is skipped. The current native-DP shadow does not produce or consume
that certificate:

```text
accepted_native_cuda_fasim_dp_engine_consumer = 0
accepted_native_dp_certificate = 0
accepted_pre_drop_certificate = 0
consumer_can_drop_scoreinfo_work = 0
consumer_can_drop_align_work = 0
consumer_can_reduce_cpu_replay_frontier = 0
```

The current evidence only proves that first1 request/accounting can be
observed while falling back to full CPU replay. It does not prove that any
scoreInfo tile, forward endpoint witness, reverse-start witness, traceback
CIGAR witness, or full row identity certificate is valid before CPU work.

## Decision

```text
phase7_native_cuda_fasim_dp_engine_first1_shadow_consumer_status = no_go_no_native_dp_certificates
do_not_implement_reducing_runtime_from_this_shadow = 1
do_not_run_first64_from_this_shadow = 1
do_not_promote_broad_replacement_row_from_this_shadow = 1
path_b_native_cuda_fasim_dp_engine_family_stopped = 1
runtime_reduction_enabled = 0
runtime_work_drop_enabled = 0
scoreinfo_prealign_reduced = 0
align_side_reduced = 0
first1_runtime_reduction_gate_pass = 0
first64_runtime_allowed = 0
next_valid_gate = path_a_scope_acceptance_or_different_gpu_execution_design_after_native_cuda_fasim_dp_engine_no_go
current_next_pr = fasim_path_a_scope_acceptance_or_different_gpu_execution_design_after_native_cuda_fasim_dp_engine_no_go
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

Path B may continue only with a genuinely different GPU execution design that
produces a valid pre-drop complete-row-safe certificate before dropping work.
It must not relabel this fail-closed accounting scaffold, final CPU output
membership, or top5-only evidence as a broad replacement proof.

## Authority Model

```text
CPU aligner.Align() authority = 1
GPU score authority = 0
GPU endpoint authority = 0
GPU CIGAR authority = 0
GPU traceback authority = 0
GPU output authority = 0
GPU digest authority = 0
default behavior unchanged = 1
```
