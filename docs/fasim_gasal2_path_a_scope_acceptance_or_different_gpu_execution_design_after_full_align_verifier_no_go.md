# Fasim GASAL2 Path A Scope Acceptance Or Different GPU Execution Design After Full-Align Verifier No-Go

This checkpoint records the fork after the GASAL2 full-align verifier first1
shadow consumer stopped. It is docs-only. It does not add runtime behavior,
does not authorize work drop, and does not complete the active broad goal.

## Scope

```text
path_a_scope_acceptance_or_different_gpu_execution_design_after_full_align_verifier_no_go = recorded
previous_checkpoint = docs/fasim_gasal2_phase7_gasal2_full_align_verifier_first1_shadow_consumer_no_go.md
previous_gate = path_a_scope_acceptance_or_different_gpu_execution_design_after_full_align_verifier_no_go
path_a_user_acceptance_recorded = 0
path_a_scoped_completion_may_close_goal = 0
path_b_full_align_verifier_family_stopped = 1
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

The previous checkpoint established that the full-align verifier shadow was
observable but not consumable as a reducing runtime:

```text
phase7_full_align_verifier_first1_shadow_active = 1
descriptors > 0
proposals = 0
proposal_failures = descriptors
accepted_full_align_verifier_consumer = 0
accepted_full_align_verifier_certificate = 0
accepted_gasal2_full_align_proposals = 0
consumer_can_drop_align_work = 0
consumer_can_drop_scoreinfo_work = 0
cpu_align_fallbacks = descriptors
fallback_to_full_cpu_replay = 1
gate_first1_shadow_pass = 0
```

This is correctness-safe because it falls back to full CPU replay, but it is
not a path to runtime reduction and it does not produce any GASAL2 full-align
proposal that a verifier can consume.

## Stopped Family

The current Path B family is stopped:

```text
stopped_family = gasal2_full_align_result_with_cpu_verifier_certificate
path_b_full_align_verifier_family_stopped = 1
do_not_continue_descriptor_only_shadow_as_runtime = 1
do_not_relabel_missing_proposals_as_verified = 1
do_not_run_first64_from_failed_first1_consumer = 1
do_not_promote_broad_replacement_row_from_this_family = 1
```

Continuing this family would preserve the same missing proof:

```text
missing_gasal2_full_align_proposals = 1
missing_verified_full_align_certificate = 1
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
design_family = native_cuda_fasim_dp_certificate_engine
not_gasal2_full_align_verifier_continuation = 1
not_gasal2_align_replacement = 1
not_gpu_owned_scoreinfo_consumer_continuation = 1
not_scoreinfo_certificate_engine_continuation = 1
not_post_v5_3_descriptor_stream_continuation = 1
not_final_cpu_output_membership_proof = 1
not_top5_only_contract = 1
runtime_pr_allowed = 0
```

The next design must move away from GASAL2 proposal semantics and target
Fasim/SSW compatibility directly:

```text
native_cuda_fasim_byte_scoreinfo = 1
native_cuda_fasim_forward_reverse_trace_witness = 1
native_cuda_fasim_cigar_witness = 1
certificate_produced_before_work_drop = 1
certificate_consumed_before_cpu_align_skip = 1
fallback_to_full_cpu_replay_on_uncertainty = 1
```

This is not permission to make GPU output authoritative. The GPU can only
produce proof data. CPU `aligner.Align()` remains the verifier and fallback
authority until a later gate proves complete row-set equivalence and runtime
reduction.

## Required Semantics

The next Path B spec must target the complete Fasim row contract:

```text
requires_fasim_byte_saturation_semantics = 1
requires_scoreinfo_window_of_5_cluster_semantics = 1
requires_scoreinfo_order_equivalence = 1
requires_attempt_order_equivalence = 1
requires_local_max_tie_policy_equivalence = 1
requires_reverse_start_equivalence = 1
requires_traceback_cigar_equivalence = 1
requires_complete_row_set_contract = 1
requires_cpu_authority_replay = 1
```

The GPU is still not allowed to become final output authority:

```text
forbidden_gpu_outputs:
  score authority
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
next_valid_gate = phase7_native_cuda_fasim_dp_engine_design_spec_or_path_a_acceptance
current_next_pr = fasim_native_cuda_fasim_dp_engine_design_spec_or_path_a_acceptance
runtime_reduction_enabled = 0
runtime_work_drop_enabled = 0
first64_runtime_allowed = 0
```

That spec must define:

```text
native_scoreinfo_byte_dp_layout
native_forward_score_endpoint_layout
native_reverse_start_layout
native_traceback_cigar_witness_layout
pre_drop_certificate_field_math
consumer_decision_point_before_cpu_align_skip
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
path_b_different_gpu_execution_design_after_full_align_verifier_no_go_status = design_defined
path_b_new_design_family_after_full_align_verifier_no_go = native_cuda_fasim_dp_certificate_engine
path_b_runtime_pr_allowed = 0
path_b_docs_spec_allowed = 1
path_b_full_align_verifier_family_stopped = 1
current_execution_gate = phase7_native_cuda_fasim_dp_engine_design_spec_or_path_a_acceptance
current_next_pr = fasim_native_cuda_fasim_dp_engine_design_spec_or_path_a_acceptance
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

This checkpoint advances the roadmap by stopping the failed GASAL2 full-align
verifier family and defining what "different" means for the next Path B
design. It does not prove that the new design is implementable, fast, or
complete.

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
