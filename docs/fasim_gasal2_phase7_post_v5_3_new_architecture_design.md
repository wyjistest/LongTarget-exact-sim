# Fasim GASAL2 Phase 7 Post-v5.3 New Architecture Design

This document defines the next Path B architecture after the v5 CPU-authority
descriptor replay first64 no-go. It is a design checkpoint only. It does not
change runtime behavior and does not complete the active goal.

## Scope

```text
phase7_post_v5_3_new_architecture_design = defined
phase7_post_v5_3_design_family =
  gpu_resident_scoreinfo_consumer_summary_with_cpu_authority_replay
previous_checkpoint =
  docs/fasim_gasal2_phase7_broad_restart_v5_cpu_authority_replay_first64_broad_gate.md
previous_status = stopped_no_go
runtime_default = off
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

## Why v5 Stopped

The v5 CPU-authority descriptor replay first64 gate failed for two independent
reasons:

```text
performance:
  candidate_wall_seconds = 124.399845
  baseline_wall_seconds = 87.827405
  candidate_vs_baseline = 0.706009

coverage/accounting:
  missing_required_attempts = 624
  fallback_accounting_clean = 0
```

The next architecture must therefore change both:

```text
1. host-visible descriptor replay overhead
2. coverage/fallback accounting
```

Repeating v5 with a smaller refactor is not a valid Path B continuation.

## Architecture

The next architecture keeps the legacy Fasim state machine on CPU, but moves
the scoreInfo-local consumer decision closer to the GPU scoreInfo producer.

```text
GPU stage:
  compute legacy-byte-compatible scoreInfo candidates
  consume per-task candidate rows on device
  emit compact per-task consumer summary
  emit only selected CPU-authority replay attempts
  emit diagnostic coverage counters

CPU stage:
  preserve legacy task order
  replay CPU aligner.Align() only for emitted selected attempts
  keep CPU endpoint/CIGAR/traceback/output/digest authority
  compare candidate output against CPU baseline in shadow mode
```

The output from the GPU stage is not a host-visible full scoreInfo row stream
and not a full v5 attempt descriptor replay:

```text
output_contract =
  compact_task_consumer_summary_plus_selected_attempts

forbidden_output_contracts:
  full host-visible scoreInfo rows
  all-window/all-column attempt descriptors
  endpoint/CIGAR/traceback/output/digest authority
```

## Required Difference From v5

```text
differs_from_v5_descriptor_replay = 1
no_full_descriptor_replay = 1
gpu_consumer_reduces_before_host_transfer = 1
selected_attempts_must_be_less_than_v5_candidate_attempts = 1
coverage_accounting_must_be_clean_before_broad_claim = 1
```

The first runtime prototype must report:

```text
gpu_consumer_summary_rows > 0
gpu_selected_attempts > 0
gpu_selected_attempts < v5_candidate_align_attempts
candidate_align_attempts < reference_align_attempts
descriptor_false_negatives = 0
missing_required_attempts = 0
fallback_accounting_clean = 1
cpu_align_authority = 1
gpu_endpoint_cigar_traceback_output_authority = 0
```

## Correctness Contract

The design is shadow/default-off until it passes these gates:

```text
first1_gate:
  digest_match = 1
  full_rows_equal = 1
  missing_rows = 0
  extra_rows = 0
  triplex_mismatches = 0
  descriptor_false_negatives = 0
  missing_required_attempts = 0
  fallback_accounting_clean = 1
  candidate_align_attempts < reference_align_attempts

first64_gate:
  digest_match = 1
  full_rows_equal = 1
  missing_rows = 0
  extra_rows = 0
  triplex_mismatches = 0
  fallback_accounting_clean = 1
  candidate_wall_seconds < baseline_wall_seconds
  candidate_vs_baseline > 1.0
  scoreInfo/preAlign work reduced or replaced
  Align-side work reduced or replaced
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

CPU output remains the only production output. GPU output can only select which
CPU-authority attempts are replayed in shadow mode.

## Telemetry

The runtime prototype must emit itemized telemetry:

```text
requested
active
source_is_pre_scoreinfo
gpu_scoreinfo_tasks
gpu_consumer_summary_rows
gpu_selected_attempts
reference_align_attempts
candidate_align_attempts
v5_candidate_align_attempts
scoreinfo_prealign_reduced
align_side_reduced
descriptor_false_negatives
missing_required_attempts
fallback_accounting_clean
gpu_kernel_seconds
h2d_seconds
d2h_seconds
cpu_replay_seconds
candidate_wall_seconds
baseline_wall_seconds
candidate_vs_baseline
digest_match
full_rows_equal
triplex_mismatches
```

## First Implementation Gate

```text
next_runtime_env =
  FASIM_GASAL2_PHASE7_POST_V5_3_GPU_CONSUMER_SUMMARY=1

next_runtime_gate =
  post_v5_3_gpu_consumer_summary_first1_smoke

deliverables:
  default-off env
  fail-closed CPU-only stub
  telemetry counters
  first1 smoke checker
  roadmap checkpoint
```

The first1 smoke may be performance-neutral, but it must prove the architecture
is different from v5:

```text
gpu_consumer_reduces_before_host_transfer = 1
gpu_selected_attempts < v5_candidate_align_attempts
missing_required_attempts = 0
fallback_accounting_clean = 1
```

## Stop Conditions

Stop this architecture if any of these occur:

```text
gpu_selected_attempts >= v5_candidate_align_attempts
missing_required_attempts > 0
descriptor_false_negatives > 0
fallback_accounting_clean = 0
first1 output rows differ
first64 candidate_wall_seconds >= baseline_wall_seconds
the implementation requires GPU endpoint/CIGAR/traceback/output authority
```

## Decision

```text
phase7_post_v5_3_new_architecture_may_implement = 1
phase7_post_v5_3_new_architecture_may_claim_completion = 0
next_required_gate = post_v5_3_gpu_consumer_summary_first1_smoke
broad_objective_status = open
must_not_call_update_goal_complete = 1
```
