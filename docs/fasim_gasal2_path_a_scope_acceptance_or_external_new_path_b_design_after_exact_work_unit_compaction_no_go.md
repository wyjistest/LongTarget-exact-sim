# Fasim GASAL2 Path A Scope Acceptance Or External New Path B Design After Exact Work-Unit Compaction No-Go

This checkpoint records the state after the roadmap reached the user-choice
gate following the exact work-unit compaction no-go. It is docs-only. It does
not accept the scoped Path A product, does not define a new Path B GPU design,
does not add runtime behavior, and does not complete the active broad goal.

## Scope

```text
path_a_scope_acceptance_or_external_new_path_b_design_after_exact_work_unit_compaction_no_go = recorded
previous_checkpoint = docs/fasim_gasal2_new_gpu_execution_design_family_spec_or_path_a_acceptance_after_exact_work_unit_compaction_no_go.md
previous_gate = path_a_scope_acceptance_or_external_new_path_b_design_after_exact_work_unit_compaction_no_go
path_a_user_acceptance_recorded = 0
path_a_scoped_completion_may_close_goal = 0
path_b_external_design_input_received = 0
path_b_new_design_family_after_exact_work_unit_compaction_no_go = undefined
path_b_no_viable_new_design_family_after_exact_work_unit_compaction_no_go = 1
path_b_external_design_input_required_after_exact_work_unit_compaction_no_go = 1
runtime_reduction_enabled = 0
runtime_work_drop_enabled = 0
first1_runtime_reduction_gate_pass = 0
first64_runtime_allowed = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

## Decision State

The prior checkpoint evaluated the available design space and did not find a
safe new Path B family:

```text
new_gpu_execution_design_family_spec_or_path_a_acceptance_after_exact_work_unit_compaction_no_go = recorded
path_b_no_viable_new_design_family_after_exact_work_unit_compaction_no_go = 1
path_b_external_design_input_required_after_exact_work_unit_compaction_no_go = 1
path_b_docs_spec_allowed_without_new_design_input = 0
path_b_runtime_pr_allowed = 0
```

No user acceptance of the scoped Path A product is recorded in this checkpoint:

```text
path_a_user_acceptance_recorded = 0
path_a_scoped_completion_may_close_goal = 0
path_a_acceptance_document = docs/fasim_gasal2_path_a_scoped_completion_acceptance.md
```

No external Path B design input is recorded either:

```text
path_b_external_design_input_received = 0
path_b_external_design_document = none
path_b_external_design_reviewed = 0
path_b_external_design_accepted_for_spec = 0
```

Therefore this checkpoint cannot advance to a runtime PR, first1 shadow, or
completion packet.

## Allowed Future Inputs

The active goal can move again only through one of these inputs:

```text
allowed_input_a = explicit_user_path_a_scope_acceptance
allowed_input_b = external_new_path_b_gpu_design_source
```

Path A input must explicitly accept the scoped deliverable and its non-claims:

```text
path_a_scope_must_remain_narrow = 1
path_a_must_not_claim_broad_aligner_replacement = 1
path_a_must_not_claim_long_query_broad_replacement = 1
path_a_must_not_grant_gpu_endpoint_cigar_traceback_output_digest_authority = 1
```

Path B input must provide a genuinely new pre-drop proof source that is not any
stopped family:

```text
not_post_v5_3_descriptor_stream = 1
not_scoreinfo_certificate_engine = 1
not_gpu_owned_scoreinfo_consumer = 1
not_gasal2_full_align_verifier = 1
not_native_cuda_fasim_dp_engine = 1
not_gpu_upper_bound_reject_certificate = 1
not_gpu_exact_work_unit_compaction = 1
requires_scoreinfo_prealign_reduction_plan = 1
requires_align_side_reduction_plan = 1
requires_full_row_digest_equality_plan = 1
requires_fallback_accounting_plan = 1
```

## Current Cursor

Until one of those inputs arrives, the roadmap stays at an input-required
state:

```text
next_valid_gate = user_scope_acceptance_or_external_path_b_design_input_required_after_exact_work_unit_compaction_no_go
current_execution_gate = user_scope_acceptance_or_external_path_b_design_input_required_after_exact_work_unit_compaction_no_go
current_next_pr = none_until_user_scope_acceptance_or_external_path_b_design_input
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

This is not a completion state. It is an explicit stop-before-guessing
checkpoint for the current evidence.

## Forbidden

```text
no real opt-in
no default behavior change
no runtime work drop
no first64 before first1 passes
no promotion of stopped Path B families
no invented Path B design family
no implicit Path A acceptance
no GPU score authority
no GPU endpoint authority
no GPU CIGAR authority
no GPU traceback authority
no GPU output authority
no GPU digest authority
no completion claim from this checkpoint
```

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
