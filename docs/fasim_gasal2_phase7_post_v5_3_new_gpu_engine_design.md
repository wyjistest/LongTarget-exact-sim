# Fasim GASAL2 Phase 7 Post-v5.3 New GPU Engine Design

This checkpoint defines what a genuinely different Path B GPU engine would
need to be after the current descriptor/proof-family line stopped. It is a
docs/spec checkpoint only. It does not add runtime behavior and does not
complete the active goal.

## Scope

```text
phase7_post_v5_3_new_gpu_engine_design = defined
previous_checkpoint = docs/fasim_gasal2_phase7_post_v5_3_different_gpu_execution_design_or_scope_acceptance.md
previous_status = path_b_runtime_pr_allowed_0
runtime_default = off
runtime_reduction_enabled = 0
first64_runtime_allowed = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

The previous checkpoint narrowed the valid work to either explicit Path A
scoped acceptance or a new Path B engine design. This document records the Path
B design contract. It does not authorize an implementation PR yet.

## Design Family

```text
design_family = fasim_compatible_gpu_scoreinfo_attempt_engine
not_gasal2_align_replacement = 1
not_current_descriptor_stream_continuation = 1
```

The design is not a direct GASAL2 `aligner.Align()` replacement and not another
variant of the current `PreAlignCudaAttemptDescriptor` replay stream. It is a
new GPU scoreInfo/attempt engine whose output remains subject to CPU authority
replay.

## Required Semantics

The new engine must target the semantics that earlier GASAL2 and descriptor
paths failed to preserve broadly:

```text
requires_fasim_byte_saturation_semantics = 1
requires_scoreinfo_window_of_5_cluster_semantics = 1
requires_candidate_attempt_order_equivalence = 1
requires_pre_d2h_output_inert_certificate = 1
requires_cpu_authority_replay = 1
requires_scoreinfo_prealign_reduction = 1
requires_align_side_reduction = 1
requires_full_row_digest_equality = 1
```

The required GPU-side output is not final Fasim output. It is a conservative
candidate/attempt stream plus proof metadata:

```text
gpu_output_contract:
  scoreInfo-compatible candidate groups
  selected CPU replay attempts
  conservative skipped-work certificate
  fallback reason counters

forbidden_gpu_output_contract:
  endpoint authority
  CIGAR authority
  traceback authority
  final output authority
  digest authority
```

## Architecture Sketch

```text
CPU stage:
  preserve Fasim task order
  prepare encoded query/target descriptors
  provide scoring config and thresholds

GPU engine:
  reproduce Fasim-compatible scoreInfo candidate semantics
  apply scoreInfo-local attempt ordering
  compute conservative upper bounds for skipped groups/attempts
  emit only proven-safe selected CPU replay attempts
  fail closed to full replay when proof inputs are missing

CPU replay:
  run CPU aligner.Align() for selected attempts
  reconstruct canonical output through existing Fasim code
  compare full rows/digest against CPU baseline in shadow mode
```

This architecture must reduce work before D2H. Host-only pruning after a full
descriptor export does not satisfy this design.

## First1 Spec Gate

Before any runtime prototype, a narrower implementation spec must define the
first1 gate:

```text
first1_spec_gate_required = 1
required_inputs:
  encoded query layout
  encoded target layout
  scoring config key
  scoreInfo-compatible scoring mode
  candidate ordering rule
  skipped scoreInfo upper bound
  skipped attempt score upper bound
  skipped attempt nt upper bound
  skipped attempt identity upper bound
  skipped attempt stability upper bound
  task output capacity
  scoreInfo-local break-state

required_outputs:
  selected replay attempts
  skipped-work certificate
  fail-closed fallback counters
  proof telemetry
```

The first1 gate must require:

```text
digest_match = 1
full_rows_equal = 1
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

## First64 Broad Gate

The first64 broad gate may run only after first1 passes:

```text
first64_broad_gate_required = 1
```

The first64 gate must require:

```text
digest_match = 1
full_rows_equal = 1
missing_rows = 0
extra_rows = 0
triplex_mismatches = 0
candidate_wall_seconds < baseline_wall_seconds
candidate_vs_baseline > 1.0
scoreInfo_prealign_reduced = 1
align_side_reduced = 1
fallback_accounting_clean = 1
```

Passing first1 without first64 remains a checkpoint, not broad completion.

## Authority Model

```text
CPU aligner.Align() authority = 1
GPU endpoint authority = 0
GPU CIGAR authority = 0
GPU traceback authority = 0
GPU output authority = 0
GPU digest authority = 0
```

GPU output may select or skip replay work only when the certificate proves the
skipped work output-inert before reduction. CPU output remains the only
semantic authority.

## Current Decision

The design is not implementable from the current runtime pieces without a new
spec and new kernel family:

```text
current_runtime_implementation_available = 0
runtime_pr_allowed = 0
docs_spec_checkpoint_only = 1
next_valid_gate = phase7_new_gpu_engine_spec_or_path_a_acceptance
```

If Path B continues, the next checkpoint must be an implementation-ready spec
for this engine family. It must define the exact data layout, certificate math,
fallback behavior, telemetry, and first1 checker before any runtime code is
added.

If the user accepts Path A, the next checkpoint is the scoped close packet
instead.

## Non-Completion

```text
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

This checkpoint advances the roadmap by replacing the stopped descriptor-line
runtime idea with a stricter engine-level design contract. It does not close
Path A or Path B.
