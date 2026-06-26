# Fasim GASAL2 Path A Scope Acceptance Or Different GPU Execution Design After Exact Work-Unit Compaction No-Go

This checkpoint records the fork after the GPU exact work-unit compaction
first1 shadow consumer stopped. It is docs-only. It does not add runtime
behavior, does not authorize work drop, and does not complete the active broad
goal.

## Scope

```text
path_a_scope_acceptance_or_different_gpu_execution_design_after_exact_work_unit_compaction_no_go = recorded
previous_checkpoint = docs/fasim_gasal2_phase7_gpu_exact_work_unit_compaction_first1_shadow_consumer_no_go.md
previous_gate = path_a_scope_acceptance_or_different_gpu_execution_design_after_exact_work_unit_compaction_no_go
path_a_user_acceptance_recorded = 0
path_a_scoped_completion_may_close_goal = 0
path_b_gpu_exact_work_unit_compaction_family_stopped = 1
path_b_different_gpu_execution_design_required = 1
path_b_different_gpu_execution_design_defined = 0
runtime_default = off
runtime_reduction_enabled = 0
runtime_work_drop_enabled = 0
first1_runtime_reduction_gate_pass = 0
first64_runtime_allowed = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

Path A remains available only if the user explicitly accepts the scoped
completion packet in `docs/fasim_gasal2_path_a_scoped_completion_acceptance.md`.
No such acceptance is recorded here. Therefore the active broad objective
stays open.

## Starting Evidence

The previous checkpoint established that the exact work-unit compaction shadow
was observable but not consumable as a reducing runtime:

```text
scoreinfo_key_descriptors > 0
scoreinfo_unique_keys > 0
scoreinfo_duplicate_units = 0
align_key_descriptors > 0
align_unique_keys > 0
align_duplicate_attempts = 0
key_collisions = 0
cpu_key_validation_mismatches = 0
unsupported_key_descriptors = 0
accepted_exact_work_unit_compaction_consumer = 0
accepted_exact_work_unit_compaction_reduction = 0
accepted_scoreinfo_prealign_compaction = 0
accepted_align_side_compaction = 0
duplicate_work_units_available = 0
fallback_to_full_cpu_replay = 1
runtime_reduction_enabled = 0
runtime_work_drop_enabled = 0
scoreinfo_prealign_reduced = 0
align_side_reduced = 0
gate_first1_shadow_pass = 1
gate_first1_pass = 0
```

This is correctness-safe because it falls back to full CPU replay, but it does
not prove that any scoreInfo/preAlign unit or Align-side attempt can be
compacted before CPU authority runs.

## Stopped Families

The current exact work-unit compaction family is stopped:

```text
stopped_family = gpu_exact_work_unit_compaction_replay
path_b_gpu_exact_work_unit_compaction_family_stopped = 1
do_not_continue_exact_work_unit_compaction_shadow_as_runtime = 1
do_not_relabel_zero_duplicate_accounting_as_work_drop = 1
do_not_run_first64_from_failed_exact_work_unit_consumer = 1
do_not_promote_broad_replacement_row_from_this_family = 1
```

The earlier Path B families are also stopped and must not be recycled under a
new name:

```text
stopped_prior_families:
  post_v5_3_descriptor_stream
  scoreinfo_certificate_engine
  gpu_owned_scoreinfo_consumer
  gasal2_full_align_result_with_cpu_verifier_certificate
  native_cuda_fasim_dp_certificate_engine
  gpu_upper_bound_reject_certificate_engine
  gpu_exact_work_unit_compaction_replay
```

Continuing any of these families would preserve the same missing proof:

```text
missing_valid_pre_drop_certificate = 1
missing_complete_row_safe_work_drop = 1
missing_scoreinfo_work_drop = 1
missing_align_side_work_drop = 1
missing_first1_runtime_reduction_gate = 1
missing_first64_broad_gate = 1
```

## Required Next Path B Shape

If Path B continues, the next artifact must be a genuinely different GPU
execution design family. This checkpoint does not define that family:

```text
path_b_different_gpu_execution_design_after_exact_work_unit_compaction_no_go_status = required_not_defined
path_b_new_design_family_after_exact_work_unit_compaction_no_go = undefined
path_b_new_design_family_spec_required = 1
path_b_runtime_pr_allowed = 0
path_b_docs_spec_allowed = 1
```

The next design must be different from every stopped family:

```text
not_gpu_exact_work_unit_compaction_continuation = 1
not_gpu_upper_bound_reject_certificate_continuation = 1
not_native_cuda_fasim_dp_engine_continuation = 1
not_gasal2_full_align_verifier_continuation = 1
not_gasal2_align_replacement = 1
not_gpu_owned_scoreinfo_consumer_continuation = 1
not_scoreinfo_certificate_engine_continuation = 1
not_post_v5_3_descriptor_stream_continuation = 1
not_final_cpu_output_membership_proof = 1
not_top5_only_contract = 1
```

It must start as a spec-or-Path-A decision, not runtime code. It must explain,
before implementation, what new proof source exists before CPU work and why it
can reduce both sides required by the broad objective:

```text
requires_pre_drop_complete_row_safe_certificate_source = 1
requires_scoreinfo_prealign_reduction_plan = 1
requires_align_side_reduction_plan = 1
requires_fallback_accounting_schema = 1
requires_first1_shadow_inputs = 1
requires_first1_shadow_expected_telemetry = 1
requires_first64_broad_gate_plan = 1
```

## Forbidden

```text
no real opt-in
no default behavior change
no runtime work drop
no first64 before first1 passes
no promotion of the stopped exact work-unit compaction family
no promotion of stopped earlier Path B families
no GPU score authority
no GPU endpoint authority
no GPU CIGAR authority
no GPU traceback authority
no GPU output authority
no GPU digest authority
no completion claim from this checkpoint
```

## Next Gate

The next gate is either explicit Path A scoped acceptance or a docs-only spec
for a new Path B GPU execution family:

```text
next_valid_gate = new_gpu_execution_design_family_spec_or_path_a_acceptance_after_exact_work_unit_compaction_no_go
current_execution_gate = new_gpu_execution_design_family_spec_or_path_a_acceptance_after_exact_work_unit_compaction_no_go
current_next_pr = fasim_new_gpu_execution_design_family_spec_or_path_a_acceptance_after_exact_work_unit_compaction_no_go
runtime_reduction_enabled = 0
runtime_work_drop_enabled = 0
first64_runtime_allowed = 0
```

That next spec may not claim completion. It can only define a new proof family
and the first1 fail-closed gate needed to test it. If no genuinely different
design is available, the broad objective remains open and unproven.

## Decision

```text
path_a_user_acceptance_recorded = 0
path_a_scoped_completion_may_close_goal = 0
path_b_different_gpu_execution_design_after_exact_work_unit_compaction_no_go_status = required_not_defined
path_b_new_design_family_after_exact_work_unit_compaction_no_go = undefined
path_b_runtime_pr_allowed = 0
path_b_docs_spec_allowed = 1
path_b_gpu_exact_work_unit_compaction_family_stopped = 1
current_execution_gate = new_gpu_execution_design_family_spec_or_path_a_acceptance_after_exact_work_unit_compaction_no_go
current_next_pr = fasim_new_gpu_execution_design_family_spec_or_path_a_acceptance_after_exact_work_unit_compaction_no_go
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

This checkpoint advances the roadmap by recording that the GPU exact work-unit
compaction family did not produce consumable duplicate work. It does not prove
a new design, runtime speedup, or broad replacement.

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
