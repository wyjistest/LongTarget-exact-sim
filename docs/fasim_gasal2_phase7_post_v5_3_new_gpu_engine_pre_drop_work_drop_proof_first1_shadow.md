# Fasim GASAL2 Phase 7 Post-v5.3 New GPU Engine Pre-Drop Work-Drop Proof First1 Shadow

This checkpoint implements the first1 shadow for the pre-drop work-drop proof
gate. It is fail-closed: it observes the real runtime certificate source and
prints telemetry, but it does not enable runtime reduction, does not drop work,
does not use GPU endpoint/CIGAR/traceback/output/digest as authority, and does
not close the broad objective.

## Scope

```text
phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow = fail_closed_shadow
previous_checkpoint = docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_design.md
previous_gate = implement_pre_drop_output_inert_work_drop_proof_first1_shadow
required_runtime_env = FASIM_GASAL2_PHASE7_POST_V5_3_NEW_GPU_ENGINE_PRE_DROP_WORK_DROP_PROOF_FIRST1_SHADOW
telemetry_prefix = benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_
```

The shadow reuses the real pre-drop Fasim runtime certificate source from the
previous checkpoint. It does not yet prove a skip is output-inert.

## Runtime Contract

When the runtime env is set on first1, the checkpoint must report:

```text
requested = 1
active = 1
real_fasim_runtime_certificate_source = 1
uses_pre_drop_output_inert_proof = 0
runtime_reduction_enabled = 0
runtime_work_drop_enabled = 0
real_fasim_runtime_work_drop_path = 0
candidate_uses_final_cpu_output_as_runtime_proof = 0
proof_must_not_use_top5_only_contract = 1
proof_must_cover_complete_row_set = 1
fallback_to_full_cpu_replay = 1
candidate_proof_false_negatives = 0
candidate_proof_missing_required_attempts = 0
scoreInfo_prealign_reduced = 0
align_side_reduced = 0
fallback_accounting_clean = 0
full_rows_equal = 0
digest_match = 0
gate_first1_proof_pass = 0
gate_first1_pass = 0
```

The source/reference counts must be non-zero when the real source is observed:

```text
source_task_count > 0
source_scoreinfo_count > 0
source_attempt_count > 0
reference_scoreinfo_count > 0
reference_attempt_count > 0
```

The candidate output bytes must remain identical to the baseline because this
checkpoint does not consume the proof to drop work.

## Authority Model

```text
CPU aligner.Align() authority = 1
GPU endpoint authority = 0
GPU CIGAR authority = 0
GPU traceback authority = 0
GPU output authority = 0
GPU digest authority = 0
```

## Non-Claims

This checkpoint does not claim:

```text
accepted pre-drop output-inert proof
enabled runtime reduction
enabled runtime work drop
real Fasim runtime work-drop path
clean fallback accounting
first1 proof pass
first1 broad gate pass
broad objective completion
```

## Decision

```text
phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_status = fail_closed_shadow
real_fasim_runtime_certificate_source = 1
uses_pre_drop_output_inert_proof = 0
runtime_reduction_enabled = 0
runtime_work_drop_enabled = 0
gate_first1_proof_pass = 0
gate_first1_pass = 0
next_valid_gate = implement_pre_drop_output_inert_work_drop_proof_consumer_or_no_go
current_next_pr = fasim_new_gpu_engine_pre_drop_work_drop_proof_consumer_or_no_go
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

The next gate must either implement a real pre-drop output-inert proof consumer
or stop this design family as no-go. It must not proceed to first64 until a
first1 proof pass exists.
