# Fasim GASAL2 Phase 7 Post-v5.3 Stronger Consumer Summary Design

This document defines the next valid Path B design after the first
post-v5.3 GPU consumer-summary runtime attempt failed. It is a design
checkpoint only. It does not change runtime behavior and does not complete the
active goal.

## Scope

```text
phase7_post_v5_3_stronger_consumer_summary_design = defined
phase7_post_v5_3_stronger_consumer_summary_status = design_only
phase7_post_v5_3_stronger_consumer_summary_may_implement = 1
phase7_post_v5_3_stronger_consumer_summary_may_claim_completion = 0
previous_checkpoint =
  docs/fasim_gasal2_phase7_post_v5_3_gpu_consumer_summary_first_attempt_no_go.md
previous_status = first_descriptor_per_scoreinfo_no_go
runtime_default = off
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

## Why The First Attempt Stopped

The first post-v5.3 consumer-summary runtime probe did reduce work before host
transfer, but it changed the final lite output:

```text
implementation_shape = first_descriptor_per_scoreinfo_gpu_summary
gpu_consumer_reduces_before_host_transfer = 1
gpu_selected_attempts = 718
reference_align_attempts = 2872
candidate_align_attempts = 718
baseline_lite_rows = 19
candidate_lite_rows = 25
external_digest_match = 0
external_full_rows_equal = 0
gate_first1_pass = 0
```

That proves the next reducer cannot select an arbitrary single descriptor per
scoreInfo group.

```text
first_descriptor_per_scoreinfo_preserves_output = 0
first_descriptor_per_scoreinfo_may_continue = 0
required_next_design_property = prefix_boundary_or_equivalent_replay_proof
```

## Required Architecture Change

The next design must preserve the CPU replay boundary semantics while still
reducing device-to-host data and CPU align attempts.

```text
source:
  legacy-byte CUDA scoreInfo / attempt descriptor stream

consumer:
  GPU scoreInfo-local boundary analyzer

required_output:
  compact per-scoreInfo replay certificate
  selected prefix boundary, or an equivalent replay-proof boundary
  selected CPU-authority replay attempts only

forbidden_output:
  arbitrary sparse descriptor subset
  first descriptor per scoreInfo
  GPU endpoint / CIGAR / traceback / output / digest authority
```

The design must remain long-query safe:

```text
gasal2_score_only_long_query_dependency = 0
source_is_legacy_byte_cuda = 1
source_is_pre_scoreinfo = 1
```

## Replay Certificate

For each scoreInfo group, the GPU consumer must emit enough information for
the CPU replay path to prove that skipped descriptors cannot affect final
output.

The certificate must include:

```text
scoreinfo_id
descriptor_count
selected_prefix_count
selected_prefix_end_index
scoreinfo_score
target_start
cutlength
target_end_required_for_fallback
ordered_replay_boundary
skipped_suffix_safe_reason
```

The first implementation may use a conservative boundary:

```text
conservative_boundary_allowed = 1
prefix_boundary_may_equal_full_group = 1
```

But it cannot pass the first1 gate unless it reduces below the v5 replay scale:

```text
selected_prefix_attempts < v5_candidate_align_attempts
candidate_align_attempts < reference_align_attempts
```

## Correctness Gate

The next runtime gate is still first1 and still shadow/default-off:

```text
next_runtime_env =
  FASIM_GASAL2_PHASE7_POST_V5_3_GPU_CONSUMER_SUMMARY=1

next_required_gate =
  post_v5_3_stronger_consumer_summary_first1_smoke
```

The gate may pass only if all of these are true:

```text
requested = 1
active = 1
source_is_pre_scoreinfo = 1
source_is_legacy_byte_cuda = 1
gasal2_score_only_long_query_dependency = 0
gpu_consumer_reduces_before_host_transfer = 1
uses_prefix_boundary_or_equivalent_replay_proof = 1
arbitrary_sparse_subset = 0
first_descriptor_per_scoreinfo = 0
gpu_consumer_summary_rows > 0
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
external_output_comparison_authority = 1
cpu_align_authority = 1
gpu_endpoint_cigar_traceback_output_authority = 0
gate_first1_pass = 1
```

Do not run first64 unless this first1 gate passes.

```text
do_not_run_first64_until_first1_gate_pass = 1
```

## Telemetry

The runtime prototype must emit:

```text
requested
active
source_is_pre_scoreinfo
source_is_legacy_byte_cuda
gasal2_score_only_long_query_dependency
uses_prefix_boundary_or_equivalent_replay_proof
arbitrary_sparse_subset
first_descriptor_per_scoreinfo
gpu_consumer_summary_rows
gpu_selected_scoreinfos
gpu_selected_attempts
selected_prefix_attempts
full_group_fallback_scoreinfos
full_group_fallback_attempts
skipped_suffix_attempts
reference_align_attempts
candidate_align_attempts
v5_candidate_align_attempts
descriptor_false_negatives
missing_required_attempts
fallback_accounting_clean
digest_match
full_rows_equal
missing_rows
extra_rows
triplex_mismatches
candidate_wall_seconds
baseline_wall_seconds
candidate_vs_baseline
cpu_align_authority
gpu_endpoint_cigar_traceback_output_authority
```

## First64 Broad Gate

Run first64 only after the first1 output and digest are externally clean:

```text
first1_gate_pass = 1
external_digest_match = 1
external_full_rows_equal = 1
```

The first64 gate may add a broad-replacement workload row only if it proves:

```text
digest_match = 1
full_rows_equal = 1
missing_rows = 0
extra_rows = 0
triplex_mismatches = 0
scoreinfo_prealign_reduced = 1
align_side_reduced = 1
fallback_accounting_clean = 1
candidate_wall_seconds < baseline_wall_seconds
candidate_vs_baseline > 1.0
cpu_align_authority = 1
gpu_endpoint_cigar_traceback_output_authority = 0
```

## Stop Conditions

Stop this architecture if any of these occur:

```text
the implementation selects an arbitrary sparse subset
first_descriptor_per_scoreinfo = 1
uses_prefix_boundary_or_equivalent_replay_proof = 0
first1 output rows differ
first1 digest differs
descriptor_false_negatives > 0
missing_required_attempts > 0
fallback_accounting_clean = 0
gpu_selected_attempts >= v5_candidate_align_attempts
candidate_align_attempts >= reference_align_attempts
first64 candidate_wall_seconds >= baseline_wall_seconds
the implementation requires GPU endpoint/CIGAR/traceback/output authority
```

## Decision

```text
phase7_post_v5_3_stronger_consumer_summary_design = defined
phase7_post_v5_3_stronger_consumer_summary_status = design_only
phase7_post_v5_3_stronger_consumer_summary_may_implement = 1
phase7_post_v5_3_stronger_consumer_summary_may_claim_completion = 0
next_required_gate = post_v5_3_stronger_consumer_summary_first1_smoke
broad_objective_status = open
must_not_call_update_goal_complete = 1
```
