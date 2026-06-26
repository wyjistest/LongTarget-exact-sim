# Fasim GASAL2 Phase 7 v5 CUDA Descriptor Emission Design

This was the design checkpoint after the strict true pre-scoreInfo
descriptor-source runtime smoke originally failed closed.

Current status: the v5.1 true pre-scoreInfo descriptor-source runtime smoke now
passes on first1. This document remains the design authority for the compact
descriptor API, but it is no longer the next runtime gate.

It is design-only. It does not add a CUDA runtime path and cannot complete the
broad objective by itself.

## Scope

```text
phase7_broad_restart_v5_cuda_descriptor_emission_design = defined
phase7_broad_restart_v5_cuda_descriptor_emission_status = design_only
phase7_broad_restart_v5_cuda_descriptor_emission_may_claim_completion = 0
previous_checkpoint = no_go_needs_cuda_descriptor_emission_kernel
current_runtime_checkpoint = gate_v5_1_pass_first1
next_required_gate = phase7_gate_v5_2_cpu_authority_replay_first1
required_runtime_env = FASIM_GASAL2_PHASE7_V5_TRUE_PRE_SCOREINFO_DESCRIPTOR_SOURCE
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

Historical predecessor:

```text
docs/fasim_gasal2_phase7_broad_restart_v5_true_pre_scoreinfo_descriptor_source_runtime_smoke.md

phase7_broad_restart_v5_true_pre_scoreinfo_descriptor_source_runtime_smoke =
  no_go_needs_cuda_descriptor_emission_kernel
next_required_artifact = cuda_descriptor_emission_kernel_or_api_design
```

Current runtime checkpoint:

```text
docs/fasim_gasal2_phase7_broad_restart_v5_true_pre_scoreinfo_descriptor_source_runtime_smoke.md

phase7_broad_restart_v5_true_pre_scoreinfo_descriptor_source_runtime_smoke =
  gate_v5_1_pass_first1
next_required_gate = phase7_gate_v5_2_cpu_authority_replay_first1
```

## Problem

The existing v4 GPU legacy-byte path computes scoreInfo-compatible peaks on
GPU, but its interface is still scoreInfo-row oriented:

```text
GPU legacy-byte scoreInfo computation
  -> host-visible PreAlignCudaPeak rows
  -> host/CPU attempt descriptor construction
  -> CPU aligner.Align() replay
```

That path is not enough for v5 because v5 requires the GPU execution design to
consume the legacy scoreInfo-compatible stream before it becomes the promoted
host interface.

The required v5 shape is:

```text
GPU legacy-byte scoreInfo-compatible computation
  -> fused GPU scoreInfo consumer state machine
  -> compact candidate attempt descriptors
  -> CPU aligner.Align() authority replay
```

## Proposed CUDA API

```text
new_cuda_api = prealign_cuda_emit_legacy_byte_attempt_descriptors
```

Input boundary:

```text
input_contract = encoded_targets_plus_min_scores_plus_task_metadata
```

Required inputs:

```text
PreAlignCudaQueryHandle legacy_byte_query
encoded target windows
task_count
target_length
min_score per task
max_descriptors_per_task
query_length
nt_min_length
scoring config key
```

The API may reuse the v4 legacy-byte scoreInfo kernel internals, but the
promoted output must not be full scoreInfo rows.

Output boundary:

```text
output_contract = compact_attempt_descriptors_not_scoreinfo_rows
host-visible full legacy scoreInfo row stream = forbidden
```

Descriptor fields:

```text
task_index
scoreinfo_position
scoreinfo_score
scoreinfo_order
attempt_order
target_start
cutlength
target_end_required_for_fallback
nt_min_length
scoring_config_key
overflow_flag
```

The descriptor may include diagnostic fields, but it must not include endpoint,
CIGAR, traceback, final output row, digest, or accept/reject authority.

```text
GPU endpoint/CIGAR/traceback/output authority = 0
CPU aligner.Align() authority replay = 1
```

## GPU Consumer State Machine

For each legacy-byte scoreInfo-compatible peak, GPU code must emit the same
candidate attempt windows that the CPU host loop currently constructs:

```text
for identity in 0.6, 0.7, 0.8, 0.9, 1.0:
  cutlength = int(score + 24) / (9 * identity - 4) + 1
  cutlength = min(cutlength, scoreinfo_position + 1)
  target_start = scoreinfo_position - cutlength + 1
  emit descriptor if target_start >= 0 and cutlength > 0
```

The descriptor order must preserve the legacy ordering needed by
CPU-authority replay:

```text
task order
scoreInfo order
attempt order within scoreInfo
```

If a task exceeds `max_descriptors_per_task`, the API must set an overflow flag
and fail closed for broad promotion. It must not silently drop descriptors.

## Validation Plan

Validation compares after descriptor emission. CPU legacy scoreInfo rows may be
used only as diagnostic authority after GPU descriptor generation, not as the
descriptor source.

Required first1 validation:

```text
validation compares after descriptor emission
descriptor_false_negatives = 0
missing_required_attempts = 0
candidate_attempts_below_all_column_replay_scale = 1
source_is_pre_scoreinfo = 1
scoreinfo_prealign_reduced = 1
gpu_descriptor_attempts > 0
gpu_endpoint_cigar_traceback_output_authority = 0
gate_v5_1_pass = 1
```

CPU-authority replay remains the next gate:

```text
full_rows_equal = true
digest_match = true
missing_rows = 0
extra_rows = 0
triplex_mismatches = 0
candidate_align_attempts < reference_align_attempts
```

## Runtime Integration Boundary

Allowed next implementation:

```text
add descriptor struct in cuda/prealign_cuda.h
add stub API that fails closed by default
add CUDA implementation behind FASIM_GASAL2_PHASE7_V5_TRUE_PRE_SCOREINFO_DESCRIPTOR_SOURCE
wire runtime only before CPU scoreInfo/preAlign generation
copy compact descriptors to host for CPU aligner.Align() replay
record strict Gate v5.1 telemetry
```

Forbidden implementation:

```text
use CPU preAlign as descriptor source
promote PreAlignCudaPeak rows as v5 interface
convert v4 host-visible source replay into v5 by telemetry relabeling
grant GPU endpoint/CIGAR/traceback/output authority
add broad_replacement row may be added from design
```

## Stop Conditions

Stop this design path if:

```text
descriptor false negatives appear
required attempts are missing
descriptor overflow is needed for the target workload
candidate attempts reach all-column replay scale
CPU-authority replay changes rows or digest
first64 wall time does not beat CPU authority baseline
scoreInfo/preAlign work is not actually reduced
```

## Next Gate

```text
next_gate = runtime_smoke_true_pre_scoreinfo_descriptor_source_first1
current_next_gate = phase7_gate_v5_2_cpu_authority_replay_first1
```

The original next runtime prototype for
`prealign_cuda_emit_legacy_byte_attempt_descriptors` has passed Gate v5.1 on
first1. The current next PR should replay those v5 descriptors through CPU
`aligner.Align()` authority and prove full rows/digest equality before any
first64 broad characterization.
