# Fasim GASAL2 Phase 7 GPU-Owned ScoreInfo Consumer Design Spec Or Path A Acceptance

This checkpoint turns the post scoreInfo-certificate-engine no-go into a
different Path B design. It is docs/spec only. It does not add runtime
behavior, does not authorize work drop, does not authorize first64, and does
not complete the active goal.

## Scope

```text
phase7_gpu_owned_scoreinfo_consumer_design_spec_or_path_a_acceptance = defined
previous_checkpoint = docs/fasim_gasal2_path_a_scope_acceptance_or_different_gpu_execution_design_after_scoreinfo_cert_engine_no_go.md
previous_gate = phase7_gpu_owned_scoreinfo_consumer_design_spec_or_path_a_acceptance
path_a_user_acceptance_recorded = 0
path_a_scoped_completion_may_close_goal = 0
path_b_gpu_owned_scoreinfo_consumer_spec_defined = 1
runtime_reduction_enabled = 0
runtime_work_drop_enabled = 0
runtime_reduction_pr_allowed = 0
first1_runtime_reduction_gate_pass = 0
first64_runtime_allowed = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

Path A remains available only if the user explicitly accepts the scoped
completion packet. No such acceptance is recorded here. Path B therefore
continues only through the GPU-owned scoreInfo consumer design below.

## Design Boundary

```text
design_family = gpu_owned_fasim_scoreinfo_consumer_with_pre_drop_frontier_certificate
not_current_scoreinfo_certificate_engine_continuation = 1
not_post_consumer_shadow_continuation = 1
not_current_descriptor_stream_continuation = 1
not_gasal2_align_replacement = 1
not_final_cpu_output_membership_proof = 1
not_top5_only_contract = 1
cpu_align_authority_required = 1
```

The key change from the stopped family is the proof boundary. The GPU must
produce and consume enough Fasim-compatible scoreInfo local state to decide the
CPU replay frontier before CPU replay selection. A certificate computed after
full CPU replay, final output materialization, top5 selection, or digest
comparison is not valid for this design.

## Required Semantics

The design targets Fasim/SSW scoreInfo behavior, not generic GASAL2 score
behavior:

```text
requires_fasim_byte_saturation_semantics = 1
requires_unsigned_saturating_byte_score_path = 1
requires_word_upgrade_equivalence = 1
requires_scoreinfo_window_of_5_cluster_semantics = 1
requires_scoreinfo_order_equivalence = 1
requires_attempt_order_equivalence = 1
requires_complete_row_set_contract = 1
requires_cpu_authority_replay = 1
```

GPU work may over-include CPU replay. It may not under-include any scoreInfo
group or attempt that can affect the complete Fasim row set.

## GPU-Owned State Layout

```text
gpu_owned_scoreinfo_state_layout = defined

GpuOwnedScoreInfoState
  task_id
  query_key
  target_window_key
  scoring_config_key
  min_score
  min_nt
  scoreinfo_column_index
  byte_saturation_bias
  byte_saturation_max
  word_upgrade_required
  current_column_best_score
  current_column_best_query_end
  current_column_best_target_end
  window5_cluster_key
  window5_cluster_rank
  window5_cluster_best_score
  window5_cluster_best_query_end
  window5_cluster_best_target_end
  scoreinfo_group_order
  scoreinfo_local_break_state
  task_output_capacity
  task_current_acceptance_frontier
```

This state must be owned at the decision point. A host reconstruction after
all scoreInfo rows or after CPU Align() replay is not enough.

## GPU-Owned Attempt Frontier Layout

```text
gpu_owned_attempt_frontier_layout = defined

GpuOwnedAttemptFrontier
  task_id
  group_id
  attempt_id
  scoreinfo_group_order
  attempt_order
  target_start
  target_end
  query_start
  query_end
  legacy_attempt_order
  score_upper_bound
  nt_upper_bound
  identity_upper_bound
  stability_upper_bound
  replay_required
  replay_reason
```

The frontier is restored to legacy order before the CPU chooses any replay
attempt. Batching and GPU-local order are allowed only if the exported replay
frontier is legacy-order equivalent.

## Pre-Drop Certificate Field Math

```text
pre_drop_certificate_field_math = defined
certificate_produced_before_work_drop = 1
certificate_consumed_before_cpu_replay_selection = 1
certificate_valid_before_d2h = 1
certificate_uses_final_cpu_output_membership = 0
certificate_uses_final_digest = 0
certificate_uses_top5_only_membership = 0
certificate_covers_complete_row_set = 1
```

The first implementation spec must define these inequalities for every skipped
group or attempt:

```text
skipped_score_upper_bound >= legacy_possible_score
skipped_nt_upper_bound >= legacy_possible_nt
skipped_identity_upper_bound >= legacy_possible_identity
skipped_stability_upper_bound >= legacy_possible_stability
skipped_order_after_required_frontier = 1
skipped_capacity_cannot_change_output = 1
skipped_local_break_state_preserved = 1
```

A skip is permitted only when the certificate proves this condition before the
skip:

```text
output_inert_if_skipped =
  skipped_order_after_required_frontier
  and skipped_capacity_cannot_change_output
  and skipped_local_break_state_preserved
  and upper_bounds_cannot_cross_acceptance_frontier
```

If any term is missing, unknown, or computed from final CPU output membership,
the task must fail closed to full CPU replay.

## Consumer Decision Point

```text
consumer_decision_point_before_cpu_replay_selection = defined

consumer_input:
  GpuOwnedScoreInfoState
  GpuOwnedAttemptFrontier
  pre_drop_certificate_field_math

consumer_output:
  reduced_cpu_replay_frontier
  skipped_scoreinfo_group_certificates
  skipped_attempt_certificates
  fallback_reason_counts
```

The consumer may only remove CPU work before the CPU replay scheduler selects
aligner.Align() attempts. It must not use endpoint, CIGAR, traceback, output
rows, digest rows, or final top5/TFO membership as authority.

## Fallback Accounting Schema

```text
fallback_accounting_schema = defined

fallback_reason:
  unsupported_query_shape
  unsupported_target_shape
  unsupported_scoring_config
  missing_scoreinfo_state
  missing_attempt_frontier
  missing_upper_bound
  order_ambiguity
  capacity_ambiguity
  local_break_state_ambiguity
  cuda_error
  certificate_math_failed
```

Fallback is correctness-safe only if it expands work to full CPU replay for the
affected task:

```text
fallback_to_full_cpu_replay = 1
fallback_expands_work = 1
fallback_drops_work = 0
fallback_rows_authoritative = 0
fallback_accounting_clean_required = 1
```

## First1 Shadow Inputs

```text
first1_shadow_inputs = defined

required_first1_input:
  workload = NEAT1 first1 or equivalent broad-path first1 fixture
  baseline = CPU authority run
  gpu_owned_scoreinfo_consumer_requested = 1
  runtime_reduction_enabled = 0
  runtime_work_drop_enabled = 0
  first64_runtime_allowed = 0
```

The first1 shadow may collect state, frontier, and certificate telemetry. It
must not skip scoreInfo work or CPU Align() work until a later consumer gate
accepts the pre-drop proof.

## First1 Shadow Expected Telemetry

```text
first1_shadow_expected_telemetry = defined

gpu_owned_scoreinfo_consumer_requested
gpu_owned_scoreinfo_consumer_active
gpu_owned_scoreinfo_states
gpu_owned_attempt_frontier_attempts
gpu_owned_replay_frontier_attempts
gpu_owned_skipped_scoreinfo_groups
gpu_owned_skipped_attempts
cpu_replay_attempts
baseline_cpu_attempts
scoreInfo_prealign_reduced
align_side_reduced
runtime_reduction_enabled
runtime_work_drop_enabled
certificate_produced_before_work_drop
certificate_consumed_before_cpu_replay_selection
certificate_false_negatives
missing_required_attempts
fallback_reason_counts
fallback_accounting_clean
candidate_wall_seconds
baseline_wall_seconds
full_rows_equal
digest_match
missing_rows
extra_rows
triplex_mismatches
```

The expected first1 shadow status is fail-closed until a later gate proves the
certificate is consumable:

```text
gpu_owned_scoreinfo_consumer_active = 1
runtime_reduction_enabled = 0
runtime_work_drop_enabled = 0
scoreInfo_prealign_reduced = 0
align_side_reduced = 0
```

## Later Runtime Gate

A later reducing-runtime PR may be proposed only after a first1 shadow and
consumer gate prove all of these on the same input:

```text
certificate_produced_before_work_drop = 1
certificate_consumed_before_cpu_replay_selection = 1
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

Passing first1 permits only a first64 proposal. It does not complete the broad
objective.

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

## Current Decision

```text
phase7_gpu_owned_scoreinfo_consumer_design_spec_status = spec_defined
path_b_gpu_owned_first1_fail_closed_shadow_allowed = 1
path_b_runtime_reduction_pr_allowed = 0
path_b_runtime_work_drop_allowed = 0
path_b_first64_runtime_allowed = 0
next_valid_gate = phase7_gpu_owned_scoreinfo_consumer_first1_shadow_scaffold
current_next_pr = fasim_gpu_owned_scoreinfo_consumer_first1_shadow_scaffold
```

The next Path B checkpoint may be a first1 fail-closed shadow scaffold for this
GPU-owned consumer. It must keep runtime reduction, work drop, first64, and GPU
output authority disabled.

## Non-Completion

```text
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

This checkpoint defines the next design family enough for a first1 shadow
scaffold to be reviewed. It does not prove the design is implementable, fast,
or complete.
