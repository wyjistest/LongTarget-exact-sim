# Fasim GASAL2 Path A Scope Acceptance Or Different GPU Execution Design After ScoreInfo Cert Engine No-Go

This checkpoint records the fork after the post-consumer GPU scoreInfo
certificate-engine first1 shadow consumer stopped. It is docs-only. It does
not add runtime behavior, does not authorize work drop, and does not complete
the active goal.

## Scope

```text
path_a_scope_acceptance_or_different_gpu_execution_design_after_scoreinfo_cert_engine_no_go = recorded
previous_checkpoint = docs/fasim_gasal2_phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_consumer_no_go.md
previous_gate = path_a_scope_acceptance_or_different_gpu_execution_design_after_scoreinfo_cert_engine_no_go
path_a_user_acceptance_recorded = 0
path_a_scoped_completion_may_close_goal = 0
path_b_scoreinfo_certificate_engine_family_stopped = 1
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

The previous checkpoint established that the scoreInfo certificate-engine
shadow was observable but not consumable as a reducing runtime:

```text
scoreinfo_cert_engine_first1_shadow_active = 1
certificate_valid_before_work_drop = 0
certificate_valid_before_d2h = 0
accepted_scoreinfo_certificate_engine_consumer = 0
accepted_pre_drop_output_inert_certificate = 0
consumer_can_drop_scoreinfo_work = 0
consumer_can_drop_align_work = 0
gpu_skipped_scoreinfo_groups = 0
gpu_skipped_attempts = 0
cpu_replay_attempts = baseline_cpu_attempts
scoreInfo_prealign_reduced = 0
align_side_reduced = 0
fallback_accounting_clean = 0
gate_first1_pass = 0
```

This is correctness-safe because it falls back to full CPU replay, but it is
not a path to runtime reduction.

## Stopped Family

The current Path B family is stopped:

```text
stopped_family = post_consumer_gpu_scoreinfo_certificate_engine_shadow
path_b_scoreinfo_certificate_engine_family_stopped = 1
do_not_continue_fail_closed_shadow_as_runtime = 1
do_not_relabel_shadow_telemetry_as_pre_drop_certificate = 1
do_not_run_first64_from_failed_first1_consumer = 1
do_not_promote_broad_replacement_row_from_this_family = 1
```

Continuing this family would preserve the same missing proof:

```text
missing_valid_pre_drop_certificate = 1
missing_output_inert_skip_proof = 1
missing_scoreinfo_work_drop = 1
missing_align_side_work_drop = 1
```

## Required Different Path B Design

If Path B continues, the next artifact must be a genuinely different GPU
execution design:

```text
path_b_different_gpu_execution_design_required = 1
path_b_different_gpu_execution_design_defined = 1
design_family = gpu_owned_fasim_scoreinfo_consumer_with_pre_drop_frontier_certificate
not_current_scoreinfo_certificate_engine_continuation = 1
not_post_consumer_shadow_continuation = 1
not_current_descriptor_stream_continuation = 1
not_gasal2_align_replacement = 1
not_final_cpu_output_membership_proof = 1
not_top5_only_contract = 1
runtime_pr_allowed = 0
```

The next design must move the proof boundary earlier than the stopped shadow:

```text
certificate_produced_before_work_drop = 1
certificate_consumed_before_cpu_replay_selection = 1
gpu_owns_scoreinfo_local_consumer_state = 1
gpu_owns_attempt_frontier_state = 1
gpu_outputs_reduced_cpu_replay_frontier = 1
fallback_to_full_cpu_replay_on_uncertainty = 1
```

The design must prove skipped work is output-inert for the complete Fasim row
set before dropping the work. A host-side label after full CPU replay, final
CPU output membership, final digest membership, or top5-only membership is not
an acceptable proof.

## Required Semantics

The next Path B spec must target Fasim/SSW scoreInfo semantics:

```text
requires_fasim_byte_saturation_semantics = 1
requires_scoreinfo_window_of_5_cluster_semantics = 1
requires_scoreinfo_order_equivalence = 1
requires_attempt_order_equivalence = 1
requires_complete_row_set_contract = 1
requires_cpu_authority_replay = 1
```

The GPU is still not allowed to become final output authority:

```text
forbidden_gpu_outputs:
  endpoint authority
  CIGAR authority
  traceback authority
  final output authority
  digest authority
```

## Next Spec Gate

The next Path B checkpoint must be a spec-or-Path-A decision, not runtime
code:

```text
next_valid_gate = phase7_gpu_owned_scoreinfo_consumer_design_spec_or_path_a_acceptance
current_next_pr = fasim_gpu_owned_scoreinfo_consumer_design_spec_or_path_a_acceptance
runtime_reduction_enabled = 0
runtime_work_drop_enabled = 0
first64_runtime_allowed = 0
```

That spec must define:

```text
gpu_owned_scoreinfo_state_layout
gpu_owned_attempt_frontier_layout
pre_drop_certificate_field_math
consumer_decision_point_before_cpu_replay_selection
fallback_accounting_schema
first1_shadow_inputs
first1_shadow_expected_telemetry
```

A later runtime checkpoint may run only after the spec exists, and it must be
first1-only and fail-closed until these are proven:

```text
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

## Decision

```text
path_a_user_acceptance_recorded = 0
path_a_scoped_completion_may_close_goal = 0
path_b_different_gpu_execution_design_after_scoreinfo_cert_engine_no_go_status = design_defined
path_b_new_design_family = gpu_owned_fasim_scoreinfo_consumer_with_pre_drop_frontier_certificate
path_b_runtime_pr_allowed = 0
path_b_docs_spec_allowed = 1
path_b_scoreinfo_certificate_engine_family_stopped = 1
current_execution_gate = phase7_gpu_owned_scoreinfo_consumer_design_spec_or_path_a_acceptance
current_next_pr = fasim_gpu_owned_scoreinfo_consumer_design_spec_or_path_a_acceptance
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

This checkpoint advances the roadmap by stopping the failed scoreInfo
certificate-engine family and defining what "different" means for the next
Path B design. It does not prove that the new design is implementable, fast, or
complete.

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
