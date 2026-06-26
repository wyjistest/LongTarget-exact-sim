# Fasim GASAL2 Phase 7 GPU Exact Work-Unit Compaction First1 Shadow Consumer No-Go

This checkpoint closes the exact work-unit compaction first1 shadow consumer
gate. It is a no-go checkpoint for the current exact input-key compaction
family, not a runtime implementation, not a work-drop implementation, and not
a completion claim.

## Scope

```text
phase7_gpu_exact_work_unit_compaction_first1_shadow_consumer_no_go = recorded
previous_checkpoint = docs/fasim_gasal2_phase7_gpu_exact_work_unit_compaction_first1_shadow_scaffold.md
previous_gate = phase7_gpu_exact_work_unit_compaction_first1_shadow_consumer_or_no_go
runtime_reduction_enabled = 0
runtime_work_drop_enabled = 0
first1_runtime_reduction_gate_pass = 0
first64_runtime_allowed = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

The previous first1 shadow made exact work-unit key telemetry observable while
deliberately remaining fail-closed:

```text
requested = 1
active = 1
scoreinfo_key_descriptors > 0
scoreinfo_unique_keys > 0
scoreinfo_duplicate_units = 0
align_key_descriptors > 0
align_unique_keys > 0
align_duplicate_attempts = 0
key_collisions = 0
cpu_key_validation_mismatches = 0
unsupported_key_descriptors = 0
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

That evidence is correctness-safe because CPU replay still performs all
semantic work, but it contains no duplicate scoreInfo/preAlign unit or Align
attempt that a consumer could safely compact into a runtime reduction.

## Consumer Result

A real consumer would need non-trivial exact duplicate classes and key
decisions that are available before duplicate CPU work is performed. The
current first1 shadow does not provide consumable duplicate work:

```text
accepted_exact_work_unit_compaction_consumer = 0
accepted_exact_work_unit_compaction_reduction = 0
accepted_scoreinfo_prealign_compaction = 0
accepted_align_side_compaction = 0
consumer_can_reduce_scoreinfo_work = 0
consumer_can_reduce_align_work = 0
consumer_can_reduce_cpu_replay_frontier = 0
consumer_available_before_scoreinfo_prealign_skip = 0
consumer_available_before_align_skip = 0
duplicate_work_units_available = 0
scoreinfo_duplicate_work_units_available = 0
align_duplicate_work_units_available = 0
```

The clean first1 shadow only proves that exact-key accounting is inert when no
work is dropped. It does not prove a useful runtime reducer, because the
current keys do not identify repeated semantic work in either CPU path required
by the broad objective.

## Decision

```text
phase7_gpu_exact_work_unit_compaction_first1_shadow_consumer_status = no_go_no_duplicate_work
do_not_implement_reducing_runtime_from_this_shadow = 1
do_not_run_first64_from_this_shadow = 1
do_not_promote_broad_replacement_row_from_this_shadow = 1
path_b_gpu_exact_work_unit_compaction_family_stopped = 1
runtime_reduction_enabled = 0
runtime_work_drop_enabled = 0
scoreinfo_prealign_reduced = 0
align_side_reduced = 0
first1_runtime_reduction_gate_pass = 0
first64_runtime_allowed = 0
next_valid_gate = path_a_scope_acceptance_or_different_gpu_execution_design_after_exact_work_unit_compaction_no_go
current_execution_gate = path_a_scope_acceptance_or_different_gpu_execution_design_after_exact_work_unit_compaction_no_go
current_next_pr = fasim_path_a_scope_acceptance_or_different_gpu_execution_design_after_exact_work_unit_compaction_no_go
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

Path B may continue only with a genuinely different GPU execution design that
can produce a valid pre-drop complete-row-safe proof and reduce both required
CPU paths. It must not relabel zero duplicate counts, fail-closed CPU replay,
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
