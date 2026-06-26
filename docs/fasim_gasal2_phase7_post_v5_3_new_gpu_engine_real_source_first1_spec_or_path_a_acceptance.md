# Fasim GASAL2 Phase 7 Post-v5.3 New GPU Engine Real-Source First1 Spec Or Path A Acceptance

This checkpoint specifies the next runnable Path B first1 shadow gate after the
synthetic certificate-producer line failed to reduce runtime work. It is
docs/spec only. It does not add runtime behavior, does not authorize first64,
and does not complete the active goal.

## Scope

```text
phase7_post_v5_3_new_gpu_engine_real_source_first1_spec_or_path_a_acceptance = defined
previous_checkpoint = docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_design_after_first1_no_go.md
previous_gate = phase7_new_gpu_engine_real_source_first1_spec_or_path_a_acceptance
runtime_reduction_enabled = 0
runtime_pr_allowed = 0
first1_runtime_allowed = 0
first64_runtime_allowed = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

Path A remains available only through explicit user scoped acceptance:

```text
path_a_user_acceptance_recorded = 0
path_a_scoped_completion_may_close_goal = 0
```

Path B may continue only through a real-source first1 shadow implementation
that follows this spec:

```text
path_b_real_source_first1_spec_defined = 1
path_b_first1_shadow_runtime_allowed = 0
path_b_first64_runtime_allowed = 0
```

## Runtime Hook Contract

The first1 shadow must be wired at a real Fasim runtime point, not a synthetic
test producer:

```text
real_runtime_hook_location = scoreInfo/preAlign task construction before CPU replay attempts are selected
certificate_producer_location = GPU scoreInfo/attempt engine before D2H
certificate_consumer_location = CPU replay scheduler before dropping replay work
work_drop_decision_point = before CPU aligner.Align() attempts are skipped
fallback_to_full_cpu_replay_point = before output rows are materialized
```

The hook must satisfy:

```text
real_fasim_runtime_certificate_source_required = 1
real_fasim_runtime_work_drop_path_required = 1
runtime_certificate_is_synthetic_allowed = 0
host_only_after_full_descriptor_export_allowed = 0
final_cpu_output_membership_required_for_certificate = 0
```

## Data Layout Contract

The implementation may use structs or packed buffers, but it must expose these
fields in telemetry and checker output.

Input task record:

```text
RealSourceGpuScoreInfoTask
  task_id
  query_id
  query_offset
  query_length
  target_id
  target_offset
  target_length
  scoring_config_key
  min_score
  min_nt
  task_order
  output_slot
```

Candidate group record:

```text
RealSourceGpuCandidateGroup
  group_id
  task_id
  scoreinfo_score
  target_end
  query_end
  candidate_order_key
  first_attempt_id
  attempt_count
```

Replay attempt record:

```text
RealSourceGpuReplayAttempt
  attempt_id
  group_id
  target_start
  target_end
  query_start
  query_end
  legacy_attempt_order
  replay_required
```

Skipped-work certificate record:

```text
RealSourceGpuSkippedWorkCertificate
  skipped_group_id
  skipped_attempt_id
  skipped_scoreinfo_upper_bound_score
  skipped_attempt_upper_bound_score
  skipped_attempt_upper_bound_nt
  skipped_attempt_upper_bound_identity
  skipped_attempt_upper_bound_stability
  scoreinfo_local_break_state
  task_output_capacity
  certificate_valid_before_d2h
  certificate_reason
```

## Fail-Closed Semantics

The first1 shadow must expand CPU work rather than skip when the proof is
uncertain:

```text
fallback_on_missing_certificate = 1
fallback_on_order_ambiguity = 1
fallback_on_capacity_exhaustion = 1
fallback_on_unsupported_query_or_target_shape = 1
fallback_on_cuda_error = 1
fallback_to_full_cpu_replay = 1
```

Fallback is correctness-safe but must be counted. A fallback-heavy first1 does
not pass the broad Path B gate unless it still reduces both work classes and
beats the CPU baseline.

## Required Telemetry

The first1 shadow must emit these counters:

```text
real_source_first1_requested
real_source_first1_active
real_fasim_runtime_certificate_source
real_fasim_runtime_work_drop_path
runtime_certificate_is_synthetic
gpu_tasks
gpu_candidate_groups
gpu_replay_attempts
gpu_selected_attempts
gpu_skipped_groups
gpu_skipped_attempts
cpu_replay_attempts
baseline_cpu_attempts
scoreInfo_prealign_reduced
align_side_reduced
fallback_reason_counts
certificate_false_negatives
missing_required_attempts
candidate_wall_seconds
baseline_wall_seconds
full_rows_equal
digest_match
missing_rows
extra_rows
triplex_mismatches
```

## First1 Acceptance Gate

The first1 shadow can advance only when all gates pass on the same first1
input:

```text
real_fasim_runtime_certificate_source = 1
real_fasim_runtime_work_drop_path = 1
runtime_certificate_is_synthetic = 0
full_rows_equal = 1
digest_match = 1
missing_rows = 0
extra_rows = 0
triplex_mismatches = 0
scoreInfo_prealign_reduced = 1
align_side_reduced = 1
fallback_accounting_clean = 1
certificate_false_negatives = 0
missing_required_attempts = 0
candidate_wall_seconds < baseline_wall_seconds
```

Passing this gate permits only a first64 broad-gate proposal. It does not
complete the broad objective.

## Authority Model

```text
CPU aligner.Align() authority = 1
GPU endpoint authority = 0
GPU CIGAR authority = 0
GPU traceback authority = 0
GPU output authority = 0
GPU digest authority = 0
```

GPU records may only select or skip CPU replay work through a conservative
certificate. CPU replay and existing Fasim output code remain semantic
authority.

## Current Decision

```text
next_valid_gate = phase7_new_gpu_engine_real_source_first1_shadow_or_path_a_acceptance
current_next_pr = fasim_new_gpu_engine_real_source_first1_shadow_or_path_a_acceptance
```

If Path A is not explicitly accepted, the next Path B PR may be a first1
shadow runtime only if it implements this real-source hook, certificate,
fail-closed, and telemetry contract.

## Non-Completion

```text
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

This checkpoint defines the first1 real-source implementation spec. It does not
approve a real output path and does not close the goal.
