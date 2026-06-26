# Fasim GASAL2 Phase 7 Post-v5.3 Long-Query-Safe Consumer Summary Design

This document defines the next valid Path B design after the host-assisted
consumer feasibility no-go. It is a design checkpoint only. It does not change
runtime behavior and does not complete the active goal.

## Scope

```text
phase7_post_v5_3_long_query_safe_consumer_summary_design = defined
phase7_post_v5_3_long_query_safe_design_family =
  legacy_byte_cuda_scoreinfo_consumer_summary_without_gasal2_score_only
previous_checkpoint =
  docs/fasim_gasal2_phase7_post_v5_3_host_assisted_consumer_feasibility_no_go.md
previous_status = host_assisted_no_go_long_query_length_guard
runtime_default = off
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

## Why The Host-Assisted Path Stopped

The host-assisted feasibility probe failed before it could test the strict
GPU-side consumer summary requirement:

```text
workload = NEAT1 first1
query_len = 22767
gasal2_max_query_len = 2812
host_selected_attempts = 0
prefix_descriptor_attempts = 0
candidate_align_attempts = 0
digest_match = 0
full_rows_equal = 0
gate_first1_pass = 0
```

Therefore the next broad design must not depend on GASAL2 score-only selection
for NEAT1-like long queries:

```text
gasal2_score_only_long_query_dependency = 0
host_assisted_gasal2_score_only_selector_may_continue = 0
```

## Design Goal

Use the existing legacy-byte-compatible CUDA scoreInfo/attempt descriptor
producer as the long-query-safe source, then add a GPU-side consumer summary
stage that decides per scoreInfo how much CPU-authority replay is needed.

```text
source:
  legacy-byte CUDA scoreInfo / attempt descriptor stream

consumer:
  CUDA scoreInfo-local summary stage

host output:
  compact task summary
  selected prefix boundary per scoreInfo
  selected CPU replay attempt descriptors only

authority:
  CPU aligner.Align()
```

This is not a GASAL2 replacement for `aligner.Align()` and not a GPU
endpoint/CIGAR/traceback path.

## Data Flow

```text
CPU prepares one task batch
  -> CUDA legacy-byte scoreInfo/attempt descriptor producer
  -> CUDA consumer summary kernel
       per task
       per scoreInfo
       inspect attempt descriptor order
       emit selected replay boundary or no-output reason
  -> host receives compact summary and selected prefix descriptors
  -> CPU ordered replay with fastSIM_extend_from_attempt_descriptors()
  -> CPU writes canonical output
  -> compare candidate full rows/digest against CPU baseline
```

The GPU-side summary must happen before host transfer:

```text
gpu_consumer_reduces_before_host_transfer = 1
full_host_visible_descriptor_replay = 0
```

## Consumer Summary Contract

The consumer summary is allowed to reduce host transfer and CPU replay only
when it can preserve CPU replay semantics:

```text
for each scoreInfo group:
  preserve descriptor order
  preserve scoreInfo score
  preserve targetStart/cutlength
  preserve targetEndRequiredForFallback
  emit a prefix boundary, not an arbitrary sparse subset
```

The CPU replay still runs the authoritative local alignments:

```text
CPU aligner.Align() authority = 1
GPU endpoint authority = 0
GPU CIGAR authority = 0
GPU traceback authority = 0
GPU output authority = 0
GPU digest authority = 0
```

## Required Runtime Env

The first runtime PR should reuse the strict post-v5.3 env:

```text
next_runtime_env =
  FASIM_GASAL2_PHASE7_POST_V5_3_GPU_CONSUMER_SUMMARY=1

next_runtime_gate =
  post_v5_3_gpu_consumer_summary_first1_smoke
```

It must not use the failed host-assisted env as the implementation path:

```text
FASIM_GASAL2_PHASE7_POST_V5_3_HOST_ASSISTED_CONSUMER_FEASIBILITY:
  diagnostic no-go evidence only
```

## Required Telemetry

The first runtime PR must emit:

```text
requested
active
source_is_pre_scoreinfo
source_is_legacy_byte_cuda
gasal2_score_only_long_query_dependency
gpu_scoreinfo_tasks
gpu_consumer_summary_rows
gpu_consumer_reduces_before_host_transfer
gpu_selected_scoreinfos
gpu_selected_attempts
gpu_prefix_descriptor_attempts
reference_align_attempts
candidate_align_attempts
v5_candidate_align_attempts
scoreinfo_prealign_reduced
align_side_reduced
descriptor_false_negatives
missing_required_attempts
fallback_accounting_clean
cpu_replay_seconds
gpu_summary_kernel_seconds
h2d_seconds
d2h_seconds
candidate_wall_seconds
baseline_wall_seconds
candidate_vs_baseline
digest_match
full_rows_equal
missing_rows
extra_rows
triplex_mismatches
cpu_align_authority
gpu_endpoint_cigar_traceback_output_authority
gate_first1_pass
```

## First1 Gate

The first runtime smoke may not advance unless all of these are true:

```text
requested = 1
active = 1
source_is_pre_scoreinfo = 1
source_is_legacy_byte_cuda = 1
gasal2_score_only_long_query_dependency = 0
gpu_consumer_summary_rows > 0
gpu_consumer_reduces_before_host_transfer = 1
gpu_selected_attempts > 0
gpu_selected_attempts < v5_candidate_align_attempts
gpu_prefix_descriptor_attempts < v5_candidate_align_attempts
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

The first1 gate is not broad completion:

```text
phase7_post_v5_3_long_query_safe_consumer_summary_may_claim_completion = 0
```

## First64 Broad Gate

Run this only after first1 passes:

```text
digest_match = 1
full_rows_equal = 1
missing_rows = 0
extra_rows = 0
triplex_mismatches = 0
candidate_wall_seconds < baseline_wall_seconds
candidate_vs_baseline > 1.0
scoreinfo_prealign_reduced = 1
align_side_reduced = 1
fallback_accounting_clean = 1
gasal2_score_only_long_query_dependency = 0
cpu_align_authority = 1
gpu_endpoint_cigar_traceback_output_authority = 0
```

Only after this gate may a workload matrix row use:

```text
contract = broad_replacement
```

## Stop Conditions

Stop this design if any of these occur:

```text
the implementation uses GASAL2 score-only selection for NEAT1-like long queries
gpu_consumer_reduces_before_host_transfer = 0
gpu_selected_attempts >= v5_candidate_align_attempts
gpu_prefix_descriptor_attempts >= v5_candidate_align_attempts
candidate_align_attempts >= reference_align_attempts
descriptor_false_negatives > 0
missing_required_attempts > 0
fallback_accounting_clean = 0
first1 output rows differ
first64 candidate_wall_seconds >= baseline_wall_seconds
the implementation requires GPU endpoint/CIGAR/traceback/output authority
```

## Decision

```text
phase7_post_v5_3_long_query_safe_consumer_summary_may_implement = 1
phase7_post_v5_3_long_query_safe_consumer_summary_may_claim_completion = 0
next_required_gate = post_v5_3_gpu_consumer_summary_first1_smoke
broad_objective_status = open
must_not_call_update_goal_complete = 1
```
