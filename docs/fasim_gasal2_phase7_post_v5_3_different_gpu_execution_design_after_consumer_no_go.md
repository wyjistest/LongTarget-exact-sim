# Fasim GASAL2 Phase 7 Post-v5.3 Different GPU Execution Design After Consumer No-Go

This checkpoint records the Path B design decision after the real-source
pre-drop work-drop proof consumer stopped on the current descriptor stream. It
is docs-only. It does not add runtime behavior, does not authorize work drop,
and does not complete the active goal.

## Scope

```text
phase7_post_v5_3_different_gpu_execution_design_after_consumer_no_go = defined
previous_checkpoint = docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_consumer_no_go.md
previous_gate = path_a_scope_acceptance_or_different_gpu_execution_design_after_consumer_no_go
runtime_default = off
runtime_reduction_enabled = 0
runtime_work_drop_enabled = 0
first1_runtime_reduction_gate_pass = 0
first64_runtime_allowed = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

Path A scoped completion is still allowed only if the user explicitly accepts
the narrowed scoped deliverable. No such acceptance is recorded here. This
document therefore records the Path B design shape that would be required if
the broad objective continues.

## Starting Evidence

The previous consumer checkpoint established:

```text
current_descriptor_stream = PreAlignCudaAttemptDescriptor
current_descriptor_stream_real_source = 1
current_descriptor_stream_can_replay_cpu_attempts = 1
current_descriptor_stream_can_prove_output_inert_skips = 0
accepted_pre_drop_output_inert_proof = 0
path_b_current_family_stopped = 1
```

The stopped descriptor stream lacks the proof inputs required to skip work
before the skip point:

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

Therefore the next Path B design must not be a continuation of the
`PreAlignCudaAttemptDescriptor` replay/export family.

## Required Design Change

```text
design_family = fasim_compatible_gpu_scoreinfo_frontier_certificate_engine
not_current_descriptor_stream_continuation = 1
not_gasal2_align_replacement = 1
not_final_cpu_output_membership_proof = 1
not_top5_only_contract = 1
runtime_pr_allowed = 0
```

The key design change is that the GPU must keep enough scoreInfo/attempt state
resident to prove skipped work output-inert before exporting a reduced replay
frontier. Host-side pruning after exporting the full descriptor stream is not a
different design and remains stopped.

## Required GPU-Side Semantics

The new design must target Fasim/SSW scoreInfo semantics, not generic GASAL2
alignment semantics:

```text
requires_fasim_byte_saturation_semantics = 1
requires_scoreinfo_window_of_5_cluster_semantics = 1
requires_scoreinfo_order_equivalence = 1
requires_attempt_order_equivalence = 1
requires_complete_row_set_contract = 1
requires_cpu_authority_replay = 1
```

GPU output may select CPU replay attempts only when skipped work has a
conservative certificate:

```text
required_gpu_outputs:
  selected_replay_attempts
  skipped_scoreinfo_group_certificate
  skipped_attempt_certificate
  fallback_reason_counters
  proof_telemetry

forbidden_gpu_outputs:
  endpoint authority
  CIGAR authority
  traceback authority
  final output authority
  digest authority
```

## Required Certificate Inputs

The implementation-ready spec must define these fields before any runtime
prototype:

```text
scoreInfo_group_key
scoreInfo_group_order
scoreInfo_group_best_score
scoreInfo_group_score_upper_bound
scoreInfo_local_break_state
attempt_order
attempt_score_upper_bound
attempt_nt_upper_bound
attempt_identity_upper_bound
attempt_stability_upper_bound
task_output_capacity
task_current_acceptance_frontier
scoring_config_key
query_key
target_key
target_offset
target_length
```

The certificate must prove skipped work is output-inert for the complete row
set. It must not depend on final CPU output membership, final digest, top5-only
membership, or post-replay labels.

## Execution Shape

```text
CPU setup:
  preserve Fasim task order
  prepare encoded query and target descriptors
  provide scoring config and per-task thresholds

GPU engine:
  generate Fasim-compatible scoreInfo groups
  apply scoreInfo-local attempt ordering
  keep candidate frontier state resident
  compute conservative skipped-work upper bounds
  emit selected replay attempts only when the certificate is complete
  fail closed to full CPU replay when any proof input is missing

CPU replay:
  run CPU aligner.Align() for selected attempts
  keep CPU output, endpoint, CIGAR, traceback, and digest authority
  compare full rows and digest against CPU baseline in shadow mode
```

## First1 Spec Gate

The next Path B checkpoint must be a spec-or-Path-A decision, not runtime code:

```text
first1_spec_gate_required = 1
runtime_reduction_enabled = 0
runtime_work_drop_enabled = 0
first64_runtime_allowed = 0
```

The spec must define:

```text
encoded query layout
encoded target layout
GPU scoreInfo group layout
GPU attempt frontier layout
certificate field math
fallback behavior
telemetry schema
first1 checker inputs and expected outputs
```

The first runtime checkpoint after that spec, if any, must remain first1-only
and fail-closed until it proves:

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
cpu_align_authority = 1
gpu_endpoint_cigar_traceback_output_authority = 0
```

## Decision

```text
phase7_post_v5_3_different_gpu_execution_design_after_consumer_no_go_status = design_defined
path_b_new_design_family = fasim_compatible_gpu_scoreinfo_frontier_certificate_engine
path_b_runtime_pr_allowed = 0
path_b_docs_spec_allowed = 1
path_b_current_descriptor_family_stopped = 1
path_a_user_acceptance_still_allowed = 1
next_valid_gate = phase7_post_consumer_gpu_scoreinfo_certificate_engine_spec_or_path_a_acceptance
current_next_pr = fasim_post_consumer_gpu_scoreinfo_certificate_engine_spec_or_path_a_acceptance
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

This checkpoint advances Path B by defining what "different GPU execution"
means after the consumer no-go. It does not prove that the design is
implementable, fast, or complete. Those claims require the next spec gate and
later first1/full-row validation.

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
