# Fasim GASAL2 Phase 7 Post-v5.3 Stronger Task-Frontier Certificate Design

This document defines the next Path B design after the first task-frontier
certificate producer ran but failed the external output gate. It is a
docs-only design checkpoint, not a completion claim.

## Scope

```text
phase7_post_v5_3_stronger_task_frontier_certificate_design = defined
phase7_post_v5_3_stronger_task_frontier_certificate_status = design_only
phase7_post_v5_3_stronger_task_frontier_certificate_may_implement = 1
phase7_post_v5_3_stronger_task_frontier_certificate_may_claim_completion = 0
previous_checkpoint =
  docs/fasim_gasal2_phase7_post_v5_3_task_frontier_certificate_first_attempt_no_go.md
previous_status = first_scoreinfo_group_per_task_certificate_no_go
runtime_default = off
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

## Why The First Task-Frontier Probe Stopped

The first task-frontier producer proved the mechanics but not the contract:

```text
task_frontier_certificate_rows = 48
gpu_selected_attempts = 192
v5_candidate_align_attempts = 2872
candidate_align_attempts = 138
reference_align_attempts = 2872
external_digest_match = 0
external_full_rows_equal = 0
missing_rows = 17
extra_rows = 0
phase7_post_v5_3_task_frontier_certificate_first1_gate_pass = 0
```

Therefore the next design cannot be:

```text
first_scoreinfo_group_per_task = 1
scoreinfo_group_selection_without_output_bound = 1
task_frontier_certificate_rows_without_skipped_group_proof = 1
```

## Required Stronger Certificate

The next certificate must prove that skipped scoreInfo groups cannot contribute
to the final task output before descriptors cross D2H.

Required certificate fields:

```text
task_id
task_descriptor_count
scoreinfo_count
selected_scoreinfo_count
selected_attempt_count
selected_attempt_ranges
task_output_capacity = N
task_frontier_min_kept_rank_bound
task_frontier_min_kept_score_bound
task_frontier_min_kept_nt_bound
task_frontier_min_kept_identity_bound
task_frontier_min_kept_stability_bound
skipped_scoreinfo_count
skipped_scoreinfo_score_upper_bound
skipped_attempt_score_upper_bound
skipped_attempt_nt_upper_bound
skipped_attempt_identity_upper_bound
skipped_attempt_stability_upper_bound
skipped_attempt_safe_reason
fallback_to_full_replay
```

The proof must be conservative:

```text
fallback_to_full_replay = 1 if any skipped group could affect output
fallback_to_full_replay = 0 only when every skipped group is output-inert
```

## Runtime Shape

```text
source:
  legacy-byte CUDA scoreInfo / attempt descriptor stream

gpu stage:
  compute task-local certificate bounds
  select only certificate-covered attempts
  fail closed to full v5 descriptor replay when proof is not available

cpu stage:
  replay CPU aligner.Align() only for selected attempts
  preserve legacy task order
  write normal Fasim output
  compare full rows and digest externally against CPU baseline
```

This remains different from stopped designs:

```text
differs_from_v5_descriptor_replay = 1
differs_from_fixed_prefix_summary = 1
differs_from_first_scoreinfo_group_probe = 1
uses_task_frontier_certificate = 1
uses_prefix_boundary_only = 0
arbitrary_sparse_subset = 0
first_descriptor_per_scoreinfo = 0
fixed_prefix_per_scoreinfo = 0
gpu_consumer_reduces_before_host_transfer = 1
```

## Authority Model

```text
CPU aligner.Align() authority = 1
GPU score authority = diagnostic only
GPU endpoint authority = 0
GPU CIGAR authority = 0
GPU traceback authority = 0
GPU output authority = 0
GPU digest authority = 0
external_output_comparison_authority = 1
```

## Next Runtime Gate

Use a new env so the no-go first attempt cannot be confused with a stronger
certificate:

```text
next_runtime_env =
  FASIM_GASAL2_PHASE7_POST_V5_3_STRONGER_TASK_FRONTIER_CERTIFICATE=1

next_required_gate =
  stronger_task_frontier_certificate_first1_smoke
```

The first1 gate may pass only if:

```text
requested = 1
active = 1
source_is_pre_scoreinfo = 1
source_is_legacy_byte_cuda = 1
gasal2_score_only_long_query_dependency = 0
uses_task_frontier_certificate = 1
uses_prefix_boundary_only = 0
arbitrary_sparse_subset = 0
first_descriptor_per_scoreinfo = 0
fixed_prefix_per_scoreinfo = 0
gpu_consumer_reduces_before_host_transfer = 1
task_frontier_certificate_rows > 0
fallback_to_full_replay = 0
gpu_selected_attempts > 0
gpu_selected_attempts < v5_candidate_align_attempts
candidate_align_attempts < reference_align_attempts
descriptor_false_negatives = 0
missing_required_attempts = 0
fallback_accounting_clean = 1
external_digest_match = 1
external_full_rows_equal = 1
missing_rows = 0
extra_rows = 0
triplex_mismatches = 0
cpu_align_authority = 1
gpu_endpoint_cigar_traceback_output_authority = 0
gate_first1_pass = 1
```

Do not run first64 until this first1 gate passes:

```text
do_not_run_first64_until_stronger_task_frontier_first1_pass = 1
```

## Stop Conditions

Stop this design if any of these occur:

```text
fallback_to_full_replay = 1 for all first1 tasks
gpu_selected_attempts >= v5_candidate_align_attempts
candidate_align_attempts >= reference_align_attempts
external_digest_match = 0
external_full_rows_equal = 0
missing_rows > 0
extra_rows > 0
the proof depends on final CPU output after replay
the implementation requires GPU endpoint/CIGAR/traceback/output authority
```

## Decision

```text
phase7_post_v5_3_stronger_task_frontier_certificate_design = defined
phase7_post_v5_3_stronger_task_frontier_certificate_status = design_only
phase7_post_v5_3_stronger_task_frontier_certificate_may_implement = 1
phase7_post_v5_3_stronger_task_frontier_certificate_may_claim_completion = 0
next_required_gate = stronger_task_frontier_certificate_first1_smoke
broad_objective_status = open
must_not_call_update_goal_complete = 1
```
