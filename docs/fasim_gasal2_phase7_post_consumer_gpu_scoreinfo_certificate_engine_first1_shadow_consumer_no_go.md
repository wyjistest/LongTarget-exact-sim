# Fasim GASAL2 Phase 7 Post-Consumer GPU ScoreInfo Certificate Engine First1 Shadow Consumer No-Go

This checkpoint closes the post-consumer GPU scoreInfo certificate-engine
first1 shadow consumer gate. It is a no-go checkpoint for the current shadow,
not a runtime implementation, not a work-drop implementation, and not a
completion claim.

## Scope

```text
phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_consumer_no_go = recorded
previous_checkpoint = docs/fasim_gasal2_phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_scaffold.md
previous_gate = phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_consumer_or_no_go
runtime_reduction_enabled = 0
runtime_work_drop_enabled = 0
first1_runtime_reduction_gate_pass = 0
first64_runtime_allowed = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

The previous first1 shadow made the post-consumer certificate-engine telemetry
observable, but it deliberately remained fail-closed:

```text
scoreinfo_cert_engine_first1_shadow_active = 1
real_fasim_runtime_certificate_source = 1
certificate_valid_before_work_drop = 0
certificate_valid_before_d2h = 0
gpu_skipped_scoreinfo_groups = 0
gpu_skipped_attempts = 0
cpu_replay_attempts = baseline_cpu_attempts
fallback_to_full_cpu_replay = 1
scoreInfo_prealign_reduced = 0
align_side_reduced = 0
fallback_accounting_clean = 0
gate_first1_shadow_pass = 0
gate_first1_pass = 0
```

The candidate output bytes remain unchanged because the shadow fully replays
CPU work. That is correctness-safe, but it is not a reducing runtime path.

## Consumer Result

A real consumer would need a pre-drop, output-inert certificate before any
scoreInfo/preAlign or Align-side work is skipped. The current shadow does not
produce that certificate:

```text
accepted_scoreinfo_certificate_engine_consumer = 0
accepted_pre_drop_output_inert_certificate = 0
consumer_can_drop_scoreinfo_work = 0
consumer_can_drop_align_work = 0
```

The current evidence only proves that the source can be observed while falling
back to full CPU replay. It does not prove that any skipped scoreInfo group or
attempt is output-inert for the complete row set.

## Decision

```text
phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_consumer_status = no_go_no_valid_pre_drop_certificate
do_not_implement_reducing_runtime_from_this_shadow = 1
do_not_run_first64_from_this_shadow = 1
do_not_promote_broad_replacement_row_from_this_shadow = 1
path_b_scoreinfo_certificate_engine_family_stopped = 1
runtime_reduction_enabled = 0
runtime_work_drop_enabled = 0
first1_runtime_reduction_gate_pass = 0
first64_runtime_allowed = 0
next_valid_gate = path_a_scope_acceptance_or_different_gpu_execution_design_after_scoreinfo_cert_engine_no_go
current_next_pr = fasim_path_a_scope_acceptance_or_different_gpu_execution_design_after_scoreinfo_cert_engine_no_go
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

Path B may continue only with a genuinely different GPU execution design that
produces a valid pre-drop complete-row-safe certificate before dropping work.
It must not relabel this fail-closed shadow, final CPU output membership, or
top5-only evidence as a broad replacement proof.

## Authority Model

```text
CPU aligner.Align() authority = 1
GPU endpoint authority = 0
GPU CIGAR authority = 0
GPU traceback authority = 0
GPU output authority = 0
GPU digest authority = 0
default behavior unchanged = 1
```
