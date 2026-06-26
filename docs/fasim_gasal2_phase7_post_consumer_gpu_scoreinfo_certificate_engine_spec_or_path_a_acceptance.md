# Fasim GASAL2 Phase 7 Post-Consumer GPU ScoreInfo Certificate Engine Spec Or Path A Acceptance

This checkpoint turns the post-consumer different-GPU-design decision into an
implementation-ready first1 spec. It is docs/spec only. It does not add runtime
behavior, does not authorize runtime work drop, does not authorize first64, and
does not complete the active goal.

## Scope

```text
phase7_post_consumer_gpu_scoreinfo_certificate_engine_spec_or_path_a_acceptance = defined
previous_checkpoint = docs/fasim_gasal2_phase7_post_v5_3_different_gpu_execution_design_after_consumer_no_go.md
previous_gate = phase7_post_consumer_gpu_scoreinfo_certificate_engine_spec_or_path_a_acceptance
path_a_user_acceptance_recorded = 0
path_a_scoped_completion_may_close_goal = 0
path_b_scoreinfo_certificate_engine_spec_defined = 1
runtime_reduction_enabled = 0
runtime_work_drop_enabled = 0
runtime_reduction_pr_allowed = 0
first1_runtime_reduction_gate_pass = 0
first64_runtime_allowed = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

Path A remains available only if the user explicitly accepts scoped completion.
No such acceptance is recorded here. Path B therefore continues through a
Fasim-compatible GPU scoreInfo frontier certificate engine spec.

## Engine Boundary

```text
design_family = fasim_compatible_gpu_scoreinfo_frontier_certificate_engine
not_current_descriptor_stream_continuation = 1
not_gasal2_align_replacement = 1
not_final_cpu_output_membership_proof = 1
not_top5_only_contract = 1
cpu_align_authority_required = 1
```

The engine is allowed to produce only a conservative CPU replay frontier. It is
not allowed to produce endpoint, CIGAR, traceback, output rows, digest, or final
accept/reject authority.

## Required Fasim Semantics

The GPU-side scoreInfo producer must target the Fasim/SSW scoreInfo contract:

```text
requires_fasim_byte_saturation_semantics = 1
requires_scoreinfo_window_of_5_cluster_semantics = 1
requires_scoreinfo_order_equivalence = 1
requires_attempt_order_equivalence = 1
requires_complete_row_set_contract = 1
requires_cpu_authority_replay = 1
```

Generic GASAL2 alignment scores are not sufficient evidence for this gate. The
first implementation may reuse GASAL2 infrastructure only if the emitted
scoreInfo groups, attempt frontier, and certificates follow the Fasim contract.

## Input Layouts

The first1 implementation must define these logical layouts before code can be
accepted:

```text
ScoreInfoCertificateQuery
  query_key
  query_length
  encoded_query_offset
  encoded_query_bytes
  profile_key

ScoreInfoCertificateTargetWindow
  target_key
  target_offset
  target_length
  encoded_target_offset
  encoded_target_bytes

ScoreInfoCertificateTask
  task_id
  task_order
  query_key
  target_key
  target_offset
  target_length
  scoring_config_key
  min_score
  min_nt
  output_slot
  task_output_capacity
```

The layouts must preserve legacy task order. Reordering for GPU batching is
allowed only if the CPU replay frontier is restored to legacy order before any
CPU Align() attempt is selected.

## GPU Frontier Layouts

```text
GpuScoreInfoGroup
  group_id
  task_id
  scoreInfo_group_key
  scoreInfo_group_order
  scoreInfo_group_best_score
  scoreInfo_group_score_upper_bound
  scoreInfo_local_break_state
  first_attempt_id
  attempt_count

GpuAttemptFrontier
  attempt_id
  group_id
  attempt_order
  target_start
  target_end
  query_start
  query_end
  attempt_score_upper_bound
  attempt_nt_upper_bound
  attempt_identity_upper_bound
  attempt_stability_upper_bound
  replay_required
```

The GPU may over-include replay attempts. It may not under-include any attempt
that could change the complete Fasim row set.

## Certificate Contract

The first1 spec accepts only pre-drop, output-inert certificates. A certificate
is valid only before the skipped work is dropped:

```text
certificate_valid_before_work_drop = 1
certificate_valid_before_d2h = 1
certificate_uses_final_cpu_output_membership = 0
certificate_uses_final_digest = 0
certificate_uses_top5_only_membership = 0
certificate_covers_complete_row_set = 1
```

The certificate must include:

```text
SkippedScoreInfoGroupCertificate
  task_id
  group_id
  scoreInfo_group_order
  scoreInfo_group_score_upper_bound
  scoreInfo_local_break_state
  task_current_acceptance_frontier
  task_output_capacity
  output_inert_if_skipped
  fallback_reason

SkippedAttemptCertificate
  task_id
  group_id
  attempt_id
  attempt_order
  attempt_score_upper_bound
  attempt_nt_upper_bound
  attempt_identity_upper_bound
  attempt_stability_upper_bound
  task_current_acceptance_frontier
  task_output_capacity
  output_inert_if_skipped
  fallback_reason
```

If any upper bound, order state, break state, or capacity state is missing, the
engine must fail closed to full CPU replay for the affected task.

## First1 Shadow Runtime Shape

The next runtime checkpoint, if implemented, must be first1-only and
fail-closed:

```text
first1_fail_closed_shadow_scaffold_allowed = 1
runtime_reduction_enabled = 0
runtime_work_drop_enabled = 0
fallback_to_full_cpu_replay = 1
first64_runtime_allowed = 0
```

Suggested environment name for that later checkpoint:

```text
FASIM_GASAL2_PHASE7_POST_CONSUMER_GPU_SCOREINFO_CERT_ENGINE_FIRST1_SHADOW=1
```

The shadow may collect GPU scoreInfo groups, attempt frontiers, and proof
telemetry. It must not use those records to drop CPU work until a later gate
explicitly proves the certificate complete and output-inert.

## Required Telemetry

The first1 shadow must emit these fields:

```text
scoreinfo_cert_engine_requested
scoreinfo_cert_engine_active
scoreinfo_cert_engine_first1_shadow
gpu_scoreinfo_groups
gpu_attempt_frontier_attempts
gpu_selected_replay_attempts
gpu_skipped_scoreinfo_groups
gpu_skipped_attempts
cpu_replay_attempts
baseline_cpu_attempts
scoreInfo_prealign_reduced
align_side_reduced
certificate_valid_before_work_drop
certificate_valid_before_d2h
certificate_false_negatives
missing_required_attempts
fallback_reason_counts
fallback_to_full_cpu_replay
candidate_wall_seconds
baseline_wall_seconds
full_rows_equal
digest_match
missing_rows
extra_rows
triplex_mismatches
```

## First1 Proof Gate

A later reducing-runtime gate may be proposed only after a first1 shadow proves
all of these conditions on the same run:

```text
scoreinfo_cert_engine_active = 1
certificate_valid_before_work_drop = 1
certificate_valid_before_d2h = 1
certificate_false_negatives = 0
missing_required_attempts = 0
full_rows_equal = 1
digest_match = 1
missing_rows = 0
extra_rows = 0
triplex_mismatches = 0
scoreInfo_prealign_reduced = 1
align_side_reduced = 1
fallback_accounting_clean = 1
candidate_wall_seconds < baseline_wall_seconds
CPU aligner.Align() authority = 1
GPU endpoint authority = 0
GPU CIGAR authority = 0
GPU traceback authority = 0
GPU output authority = 0
GPU digest authority = 0
```

Passing this first1 proof gate still would not close the broad objective. It
would only allow a first64 broad-gate proposal.

## Decision

```text
phase7_post_consumer_gpu_scoreinfo_certificate_engine_spec_status = spec_defined
path_b_scoreinfo_certificate_engine_spec_defined = 1
path_b_first1_fail_closed_shadow_scaffold_allowed = 1
path_b_runtime_reduction_pr_allowed = 0
path_b_runtime_work_drop_allowed = 0
path_b_first64_runtime_allowed = 0
next_valid_gate = phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_scaffold
current_next_pr = fasim_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_scaffold
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

This checkpoint defines the next Path B implementation boundary. It does not
prove the design works, does not authorize dropped work, and does not complete
the active goal.
