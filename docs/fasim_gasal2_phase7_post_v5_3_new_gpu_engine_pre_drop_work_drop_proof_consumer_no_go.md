# Fasim GASAL2 Phase 7 Post-v5.3 New GPU Engine Pre-Drop Work-Drop Proof Consumer No-Go

This checkpoint closes the current pre-drop work-drop proof consumer gate for
the real-source new GPU engine line. It is a no-go checkpoint, not a runtime
implementation, not a work-drop implementation, and not a completion claim.

## Scope

```text
phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_consumer_no_go = recorded
previous_checkpoint = docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow.md
previous_gate = implement_pre_drop_output_inert_work_drop_proof_consumer_or_no_go
runtime_reduction_enabled = 0
runtime_work_drop_enabled = 0
real_fasim_runtime_work_drop_path = 0
first1_runtime_reduction_gate_pass = 0
first64_runtime_allowed = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

The previous first1 shadow proved that the real Fasim runtime certificate
source is observable while keeping all work-drop behavior disabled:

```text
real_fasim_runtime_certificate_source = 1
source_task_count > 0
source_scoreinfo_count > 0
source_attempt_count > 0
reference_scoreinfo_count > 0
reference_attempt_count > 0
uses_pre_drop_output_inert_proof = 0
gate_first1_proof_pass = 0
gate_first1_pass = 0
```

This checkpoint asks whether a consumer can turn that source into a pre-drop,
complete-row-safe, output-inert work-drop proof.

## Evidence Reviewed

The current source is still the legacy-byte descriptor stream:

```text
current_descriptor_stream = PreAlignCudaAttemptDescriptor
current_descriptor_stream_real_source = 1
current_descriptor_stream_can_replay_cpu_attempts = 1
current_descriptor_stream_can_prove_output_inert_skips = 0
```

It can enumerate selected CPU replay attempts. It does not carry the proof
inputs needed to prove that skipped work is output-inert before the skip point:

```text
skipped_scoreinfo_score_upper_bound = missing
skipped_attempt_score_upper_bound = missing
skipped_attempt_nt_upper_bound = missing
skipped_attempt_identity_upper_bound = missing
skipped_attempt_stability_upper_bound = missing
task_output_capacity = missing
scoreInfo_local_break_state = missing
complete_row_set_output_inert_certificate = missing
```

Prior checkpoints already tested nearby proof families and found the same
boundary:

```text
pre_d2h_output_inert_proof_acceptance_first1 = no_go
new_pre_d2h_proof_family_first1_feasibility_no_go = recorded
stronger_task_frontier_certificate_feasibility_no_go = recorded
task_frontier_certificate_first_attempt_status = no_go
```

Those checkpoints show that final CPU output membership, fixed prefixes, first
scoreInfo groups, aggregate exports, and the current descriptor fields are not
valid runtime proofs for skipped work.

## Consumer Result

```text
accepted_pre_drop_output_inert_proof = 0
uses_pre_drop_output_inert_proof = 0
candidate_uses_final_cpu_output_as_runtime_proof = 0
proof_must_not_use_top5_only_contract = 1
proof_must_cover_complete_row_set = 1
candidate_proof_false_negatives = unproven
candidate_proof_missing_required_attempts = unproven
fallback_to_full_cpu_replay = 1
fallback_accounting_clean = 0
```

A fail-closed consumer can still fall back to full CPU replay, but that does
not reduce scoreInfo/preAlign or Align-side work. A reducing consumer from the
current descriptor stream would need a proof it does not have.

## Decision

```text
phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_consumer_status = no_go_current_descriptor_stream
do_not_implement_reducing_runtime_from_current_descriptor_stream = 1
do_not_run_first64_from_current_descriptor_stream = 1
do_not_promote_broad_replacement_row_from_current_descriptor_stream = 1
path_b_current_family_stopped = 1
runtime_reduction_enabled = 0
runtime_work_drop_enabled = 0
real_fasim_runtime_work_drop_path = 0
scoreInfo_prealign_reduced = 0
align_side_reduced = 0
gate_first1_proof_pass = 0
gate_first1_pass = 0
next_valid_gate = path_a_scope_acceptance_or_different_gpu_execution_design_after_consumer_no_go
current_next_pr = fasim_path_a_scope_acceptance_or_different_gpu_execution_design_after_consumer_no_go
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

Path B may continue only with a genuinely different GPU execution design that
adds a pre-drop complete-row-safe proof source, or with a new scoped decision
from the user. It must not continue by relabelling the current descriptor
stream, the current proof shadow, or final CPU output membership as a runtime
proof.

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
