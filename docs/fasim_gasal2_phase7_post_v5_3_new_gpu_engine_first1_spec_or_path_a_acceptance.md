# Fasim GASAL2 Phase 7 Post-v5.3 New GPU Engine First1 Spec Or Path A Acceptance

This checkpoint specifies the first runnable Path B shadow gate for a new
Fasim-compatible GPU scoreInfo/attempt engine. It is still docs/spec only. It
does not add runtime behavior, does not authorize first1 runtime work, and does
not complete the active goal.

## Scope

```text
phase7_post_v5_3_new_gpu_engine_first1_spec_or_path_a_acceptance = defined
previous_checkpoint = docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_spec_or_path_a_acceptance.md
previous_gate = phase7_new_gpu_engine_first1_spec_or_path_a_acceptance
runtime_reduction_enabled = 0
runtime_pr_allowed = 0
first1_runtime_allowed = 0
first64_runtime_allowed = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

Current acceptance state:

```text
path_a_user_acceptance_recorded = 0
path_a_scoped_completion_may_close_goal = 0
path_b_first1_spec_defined = 1
path_b_first1_runtime_allowed = 0
```

Path A remains available only through explicit user scoped acceptance. Without
that acceptance, the next Path B artifact must be a shadow runtime that follows
this first1 spec exactly.

## First1 Data Layout Contract

The first1 shadow runtime must use explicit GPU input and output records. The
field names below are the contract; implementation may choose C++ structs or a
plain packed buffer, but the semantics must remain visible in telemetry and
checker output.

Input task record:

```text
GpuScoreInfoTask
  query_id
  query_offset
  query_length
  target_id
  target_offset
  target_length
  scoring_config_key
  min_score
  output_slot
  task_order
```

Candidate group record:

```text
GpuCandidateGroup
  scoreinfo_group_id
  score
  target_end
  query_end
  candidate_order_key
  attempt_start_index
  attempt_count
```

CPU replay attempt record:

```text
GpuReplayAttempt
  attempt_id
  group_id
  target_start
  target_end
  query_start
  query_end
  legacy_attempt_order
```

The ordering fields must be sufficient to replay selected attempts through CPU
`aligner.Align()` in legacy order. GPU records are not final output rows.

## Certificate Contract

Every skipped scoreInfo group and skipped replay attempt must have a
conservative certificate that is valid before D2H and before CPU output is
known:

```text
skipped_scoreinfo_upper_bound_score
skipped_attempt_upper_bound_score
skipped_attempt_upper_bound_nt
skipped_attempt_upper_bound_identity
skipped_attempt_upper_bound_stability
task_output_capacity_exhausted
scoreinfo_local_break_state
certificate_valid_before_d2h = 1
final_cpu_output_membership_required_for_certificate = 0
```

The certificate must prove that skipped work cannot change the full restored
row set, not just top5 membership. A certificate derived from final CPU output
membership is an offline explanation only and cannot be used as runtime proof.

## Fail-Closed Rules

Any uncertainty must expand CPU replay, not skip work:

```text
fallback_on_missing_bound = 1
fallback_on_capacity_exhaustion = 1
fallback_on_order_ambiguity = 1
fallback_on_unsupported_shape = 1
fallback_to_full_cpu_replay = 1
```

Fail-closed fallback is not a correctness failure. It is a performance limiter
that must be counted and reported.

## First1 Telemetry

The first1 shadow must report enough counters to prove both correctness and
work reduction:

```text
gpu_tasks
gpu_candidate_groups
gpu_selected_attempts
gpu_skipped_groups
gpu_skipped_attempts
cpu_replay_attempts
baseline_cpu_attempts
scoreInfo_prealign_reduction_ratio
align_side_reduction_ratio
fallback_reason_counts
certificate_false_negatives
missing_required_attempts
```

`scoreInfo_prealign_reduction_ratio` and `align_side_reduction_ratio` must be
computed against the CPU-authority baseline for the same first1 input.

## First1 Acceptance Gate

The first1 shadow can advance only when all gates pass:

```text
digest_match = 1
full_rows_equal = 1
missing_rows = 0
extra_rows = 0
triplex_mismatches = 0
scoreInfo_prealign_reduced = 1
align_side_reduced = 1
fallback_accounting_clean = 1
certificate_false_negatives = 0
missing_required_attempts = 0
```

Authority remains unchanged:

```text
CPU aligner.Align() authority = 1
GPU endpoint authority = 0
GPU CIGAR authority = 0
GPU traceback authority = 0
GPU output authority = 0
GPU digest authority = 0
```

Passing this first1 gate permits only a follow-up first64 broad-gate proposal.
It does not complete the broad objective.

## Current Decision

```text
next_valid_gate = phase7_new_gpu_engine_first1_shadow_or_path_a_acceptance
current_next_pr = fasim_new_gpu_engine_first1_shadow_or_path_a_acceptance
```

If Path A is not accepted, the next Path B PR may be a first1 shadow runtime
proposal only if it implements this data layout, certificate, fail-closed, and
telemetry contract.

## Non-Completion

```text
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

This checkpoint defines the first1 implementation spec. It does not approve a
real output path and does not close the goal.
