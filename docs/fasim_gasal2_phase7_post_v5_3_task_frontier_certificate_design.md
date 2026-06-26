# Fasim GASAL2 Phase 7 Post-v5.3 Task-Frontier Certificate Design

This document selects the next Path B design after the fixed-prefix
post-v5.3 consumer-summary probe failed. It is a design checkpoint only. It
does not change runtime behavior and does not complete the active goal.

## Scope

```text
phase7_post_v5_3_task_frontier_certificate_design = defined
phase7_post_v5_3_task_frontier_certificate_status = design_only
phase7_post_v5_3_task_frontier_certificate_may_implement = 1
phase7_post_v5_3_task_frontier_certificate_may_claim_completion = 0
previous_checkpoint =
  docs/fasim_gasal2_phase7_post_v5_3_stronger_consumer_summary_prefix_no_go.md
previous_status = fixed_prefix_consumer_summary_no_go
runtime_default = off
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

## Why The Prefix Path Stopped

The stronger prefix runtime probe proved that a fixed per-scoreInfo prefix is
not enough:

```text
prefix_1_2_3_reduce_gpu_selected_attempts_but_change_output = 1
prefix_4_5_preserve_output_but_do_not_reduce_gpu_selected_attempts = 1
phase7_post_v5_3_stronger_consumer_summary_first1_gate_pass = 0
```

Therefore the next design cannot be:

```text
first_descriptor_per_scoreinfo = 1
fixed_prefix_per_scoreinfo = 1
arbitrary_sparse_subset = 1
```

## Design Family

```text
phase7_post_v5_3_design_family =
  gpu_task_frontier_certificate_with_cpu_authority_replay
```

The key change is the proof boundary. The GPU must reason about the
task-local frontier that controls final output, not only about the local order
inside one scoreInfo group.

```text
source:
  legacy-byte CUDA scoreInfo / attempt descriptor stream

gpu stage:
  group attempt descriptors by legacy task
  evaluate scoreInfo-local and task-local competition state
  emit a compact task-frontier certificate
  emit only CPU-authority replay attempts covered by the certificate
  fail closed to full replay when the certificate cannot prove safety

cpu stage:
  preserve legacy task order
  replay CPU aligner.Align() for emitted attempts
  compare restored rows/digest against CPU authority
```

This is a different execution design from v5 and the fixed-prefix probe:

```text
differs_from_v5_descriptor_replay = 1
differs_from_fixed_prefix_summary = 1
uses_task_frontier_certificate = 1
uses_prefix_boundary_only = 0
gpu_consumer_reduces_before_host_transfer = 1
```

## Certificate Contract

The GPU task-frontier certificate must prove that skipped attempts cannot
affect the CPU-authority output for the same task.

Required certificate fields:

```text
task_id
task_descriptor_count
scoreinfo_count
selected_attempt_count
selected_attempt_range_or_bitmap
task_frontier_key
task_frontier_score_bound
task_frontier_nt_bound
task_frontier_stability_bound
skipped_attempt_count
skipped_attempt_safe_reason
fallback_to_full_replay
```

The first implementation may be conservative, but the first1 gate cannot pass
unless it proves real reduction:

```text
selected_attempt_count > 0
selected_attempt_count < v5_candidate_align_attempts
candidate_align_attempts < reference_align_attempts
fallback_to_full_replay = 0 for the claimed first1 pass
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
```

The GPU may only select replay attempts in a shadow/default-off path. It must
not emit endpoint, CIGAR, traceback, output, digest, or candidate state as
authority.

## First Runtime Gate

The first runtime PR should use a new explicit env so it cannot be confused
with the stopped first-descriptor or fixed-prefix implementations:

```text
next_runtime_env =
  FASIM_GASAL2_PHASE7_POST_V5_3_TASK_FRONTIER_CERTIFICATE=1

next_required_gate =
  post_v5_3_task_frontier_certificate_first1_smoke
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
gpu_selected_attempts > 0
gpu_selected_attempts < v5_candidate_align_attempts
candidate_align_attempts < reference_align_attempts
descriptor_false_negatives = 0
missing_required_attempts = 0
fallback_accounting_clean = 1
digest_match = 1
full_rows_equal = 1
missing_rows = 0
extra_rows = 0
triplex_mismatches = 0
cpu_align_authority = 1
gpu_endpoint_cigar_traceback_output_authority = 0
gate_first1_pass = 1
```

Do not run first64 until the first1 gate passes:

```text
do_not_run_first64_until_first1_gate_pass = 1
```

## First64 Broad Gate

Only after first1 passes, run a first64-equivalent broad characterization.
That gate may pass only if:

```text
digest_match = 1
full_rows_equal = 1
missing_rows = 0
extra_rows = 0
triplex_mismatches = 0
scoreInfo/preAlign work reduced or replaced
Align-side work reduced or replaced
fallback_accounting_clean = 1
candidate_wall_seconds < baseline_wall_seconds
candidate_vs_baseline > 1.0
cpu_align_authority = 1
gpu_endpoint_cigar_traceback_output_authority = 0
```

Only after this broad gate may Phase 6 add:

```text
contract = broad_replacement
```

## Stop Conditions

Stop this design if any of these occur:

```text
uses_task_frontier_certificate = 0
uses_prefix_boundary_only = 1
first_descriptor_per_scoreinfo = 1
fixed_prefix_per_scoreinfo = 1
arbitrary_sparse_subset = 1
task_frontier_certificate_rows = 0
gpu_selected_attempts >= v5_candidate_align_attempts
candidate_align_attempts >= reference_align_attempts
descriptor_false_negatives > 0
missing_required_attempts > 0
fallback_accounting_clean = 0
first1 output rows differ
first1 digest differs
first64 candidate_wall_seconds >= baseline_wall_seconds
the implementation requires GPU endpoint/CIGAR/traceback/output authority
```

## Decision

```text
phase7_post_v5_3_task_frontier_certificate_design = defined
phase7_post_v5_3_task_frontier_certificate_status = design_only
phase7_post_v5_3_task_frontier_certificate_may_implement = 1
phase7_post_v5_3_task_frontier_certificate_may_claim_completion = 0
next_required_gate = post_v5_3_task_frontier_certificate_first1_smoke
broad_objective_status = open
must_not_call_update_goal_complete = 1
```
