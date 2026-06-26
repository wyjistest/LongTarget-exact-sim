# Fasim GASAL2 New GPU Execution Design Family Spec Or Path A Acceptance After Exact Work-Unit Compaction No-Go

This checkpoint evaluates the required next gate after the exact work-unit
compaction family stopped. It does not accept Path A, does not define a new
Path B runtime design, does not add runtime behavior, and does not complete
the active broad goal.

## Scope

```text
new_gpu_execution_design_family_spec_or_path_a_acceptance_after_exact_work_unit_compaction_no_go = recorded
previous_checkpoint = docs/fasim_gasal2_path_a_scope_acceptance_or_different_gpu_execution_design_after_exact_work_unit_compaction_no_go.md
previous_gate = new_gpu_execution_design_family_spec_or_path_a_acceptance_after_exact_work_unit_compaction_no_go
path_a_user_acceptance_recorded = 0
path_a_scoped_completion_may_close_goal = 0
path_b_new_design_family_after_exact_work_unit_compaction_no_go = undefined
path_b_no_viable_new_design_family_after_exact_work_unit_compaction_no_go = 1
path_b_external_design_input_required_after_exact_work_unit_compaction_no_go = 1
path_b_runtime_pr_allowed = 0
path_b_docs_spec_allowed_without_new_design_input = 0
runtime_reduction_enabled = 0
runtime_work_drop_enabled = 0
first1_runtime_reduction_gate_pass = 0
first64_runtime_allowed = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

Path A remains available only if the user explicitly accepts the scoped
completion packet in `docs/fasim_gasal2_path_a_scoped_completion_acceptance.md`.
No such acceptance is recorded here.

## Starting Evidence

The previous checkpoints stopped every current Path B design family:

```text
post_v5_3_descriptor_stream = stopped
scoreinfo_certificate_engine = stopped
gpu_owned_scoreinfo_consumer = stopped
gasal2_full_align_result_with_cpu_verifier_certificate = stopped
native_cuda_fasim_dp_certificate_engine = stopped
gpu_upper_bound_reject_certificate_engine = stopped
gpu_exact_work_unit_compaction_replay = stopped
```

The exact work-unit compaction family stopped because it produced no duplicate
work that could be consumed into a runtime reducer:

```text
scoreinfo_duplicate_units = 0
align_duplicate_attempts = 0
accepted_exact_work_unit_compaction_consumer = 0
accepted_exact_work_unit_compaction_reduction = 0
path_b_gpu_exact_work_unit_compaction_family_stopped = 1
```

The broad objective still requires all of these before completion:

```text
full_rows_equal = 1
digest_match = 1
missing_rows = 0
extra_rows = 0
triplex_mismatches = 0
candidate_wall_seconds < baseline_wall_seconds
candidate_vs_baseline > 1.0
scoreInfo/preAlign work reduced or replaced = 1
Align-side work reduced or replaced = 1
fallback_accounting_clean = 1
```

## Candidate Designs Reviewed

### Design A: GPU persistent full Fasim state-machine replica

This would move scoreInfo/preAlign, candidate-frontier state, Align-side
attempt generation, and output-state replay into a persistent GPU pipeline.

Decision:

```text
requires_gpu_fastSIM_state_machine = 1
requires_gpu_output_state_equivalence = 1
requires_gpu_endpoint_cigar_traceback_equivalence = 1
requires_complete_row_set_authority_change = 1
current_code_can_implement_safely_now = 0
```

This is not a valid next spec under the current authority contract because GPU
endpoint, CIGAR, traceback, output, and digest authority remain forbidden.

### Design B: GPU dominance/upper-bound frontier certificate

This would try to skip future work when already-observed candidates dominate
the remaining frontier.

Decision:

```text
requires_upper_bound_reject_or_frontier_continuation = 1
requires_final_or_post_replay_frontier_knowledge = 1
requires_complete_row_safe_pre_drop_proof = missing
current_code_can_implement_safely_now = 0
```

This is not a genuinely different family from the stopped upper-bound reject,
frontier, and descriptor-stream proof lines unless a new independent pre-drop
proof source is supplied.

### Design C: GPU full-align library replacement with CPU verifier

This would use another GPU alignment engine to propose full Align results,
then rely on CPU verification before output authority changes.

Decision:

```text
requires_gasal2_or_full_align_verifier_continuation = 1
requires_endpoint_cigar_traceback_equivalence = 1
requires_candidate_output_digest_equivalence = 1
current_code_can_implement_safely_now = 0
```

This is not a valid next spec because the GASAL2 full-align verifier family,
native CUDA/Fasim DP family, and direct aligner replacement direction have
already stopped without a complete-row-safe reducing proof.

## Decision

No Path A acceptance is recorded, and no genuinely different Path B design
family is defined in this checkpoint:

```text
path_a_user_acceptance_recorded = 0
path_a_scoped_completion_may_close_goal = 0
path_b_new_design_family_after_exact_work_unit_compaction_no_go = undefined
path_b_no_viable_new_design_family_after_exact_work_unit_compaction_no_go = 1
path_b_external_design_input_required_after_exact_work_unit_compaction_no_go = 1
path_b_runtime_pr_allowed = 0
path_b_docs_spec_allowed_without_new_design_input = 0
```

The next valid action is therefore a user-visible choice, not another runtime
PR:

```text
next_valid_gate = path_a_scope_acceptance_or_external_new_path_b_design_after_exact_work_unit_compaction_no_go
current_execution_gate = path_a_scope_acceptance_or_external_new_path_b_design_after_exact_work_unit_compaction_no_go
current_next_pr = fasim_path_a_scope_acceptance_or_external_new_path_b_design_after_exact_work_unit_compaction_no_go
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

If Path A is accepted, the acceptance packet must explicitly limit the claim to
the scoped deliverables and must not claim broad aligner replacement. If Path B
continues, the user or a separate design review must supply a genuinely new
pre-drop proof source that is not one of the stopped families.

## Forbidden

```text
no real opt-in
no default behavior change
no runtime work drop
no first64 before first1 passes
no promotion of stopped Path B families
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
