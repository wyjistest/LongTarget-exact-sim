# Fasim GASAL2 Phase 7 GPU Upper-Bound Reject Certificate First1 Shadow Consumer No-Go

This checkpoint closes the upper-bound reject certificate first1 shadow
consumer gate. It is a no-go checkpoint for the current upper-bound reject
certificate family, not a runtime implementation, not a work-drop
implementation, and not a completion claim.

## Scope

```text
phase7_gpu_upper_bound_reject_certificate_first1_shadow_consumer_no_go = recorded
previous_checkpoint = docs/fasim_gasal2_phase7_gpu_upper_bound_reject_certificate_first1_shadow_scaffold.md
previous_gate = phase7_gpu_upper_bound_reject_certificate_first1_shadow_consumer_or_no_go
runtime_reduction_enabled = 0
runtime_work_drop_enabled = 0
first1_runtime_reduction_gate_pass = 0
first64_runtime_allowed = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

The previous first1 shadow made the upper-bound descriptor/certificate stream
observable while deliberately remaining fail-closed:

```text
upper_bound_descriptors > 0
upper_bound_certificates > 0
reject_candidates_shadow = 0
would_reject_scoreinfo_groups = 0
would_reject_align_attempts = 0
certificate_false_negatives = 0
baseline_rows_in_rejected_groups = 0
baseline_rows_in_rejected_attempts = 0
unsupported_descriptors = 0
fallback_to_full_cpu_replay = 1
runtime_reduction_enabled = 0
runtime_work_drop_enabled = 0
scoreinfo_prealign_reduced = 0
align_side_reduced = 0
full_rows_equal = 1
digest_match = 1
gate_first1_shadow_pass = 1
gate_first1_pass = 0
```

That is correctness-safe because CPU replay still performs all semantic work,
but the evidence contains no rejected scoreInfo/preAlign group or Align-side
attempt that a consumer could safely drop.

## Consumer Result

A real consumer would need a pre-drop reject decision that is available before
CPU scoreInfo/preAlign or CPU Align work is skipped. The current shadow does
not provide consumable rejected work:

```text
accepted_gpu_upper_bound_reject_certificate_consumer = 0
accepted_upper_bound_reject_certificate = 0
accepted_pre_drop_reject_certificate = 0
consumer_can_drop_scoreinfo_work = 0
consumer_can_drop_align_work = 0
consumer_can_reduce_cpu_replay_frontier = 0
consumer_available_before_scoreinfo_prealign_skip = 0
consumer_available_before_align_skip = 0
rejected_work_units_available = 0
reject_certificate_coverage = 0
```

The clean first1 shadow only proves that the accounting path is inert when no
work is dropped. It does not prove a useful runtime reducer, because the
current certificates do not identify any safe reject that can reduce either of
the broad objective's required CPU paths.

## Decision

```text
phase7_gpu_upper_bound_reject_certificate_first1_shadow_consumer_status = no_go_no_rejected_work
do_not_implement_reducing_runtime_from_this_shadow = 1
do_not_run_first64_from_this_shadow = 1
do_not_promote_broad_replacement_row_from_this_shadow = 1
path_b_gpu_upper_bound_reject_certificate_family_stopped = 1
runtime_reduction_enabled = 0
runtime_work_drop_enabled = 0
scoreinfo_prealign_reduced = 0
align_side_reduced = 0
first1_runtime_reduction_gate_pass = 0
first64_runtime_allowed = 0
next_valid_gate = path_a_scope_acceptance_or_different_gpu_execution_design_after_gpu_upper_bound_reject_certificate_no_go
current_next_pr = fasim_path_a_scope_acceptance_or_different_gpu_execution_design_after_gpu_upper_bound_reject_certificate_no_go
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

Path B may continue only with a genuinely different GPU execution design that
can produce a valid pre-drop complete-row-safe proof and reduce both required
CPU paths. It must not relabel this fail-closed shadow, zero-reject accounting,
final CPU output membership, or top5-only evidence as a broad replacement
proof.

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
