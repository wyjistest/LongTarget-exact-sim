# Fasim GASAL2 Phase 7 v5 True Pre-ScoreInfo Descriptor Source Design

This document narrows the next Phase 7 v5 step after the post-scoreInfo
descriptor scaffold no-go. It is design-only. It does not add a runtime path
and cannot complete the broad objective by itself.

## Scope

```text
phase7_broad_restart_v5_true_pre_scoreinfo_descriptor_source_design = defined
phase7_broad_restart_v5_true_pre_scoreinfo_descriptor_source_status = design_only
phase7_broad_restart_v5_true_pre_scoreinfo_descriptor_source_may_claim_completion = 0
phase7_broad_restart_v5_gate_v5_1_pass = 0
phase7_broad_restart_v5_true_pre_scoreinfo_descriptor_source_next_gate = runtime_smoke_true_pre_scoreinfo_descriptor_source_first1
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

The previous v5 runtime scaffold is useful only as a descriptor-accounting
checkpoint. It records candidate attempt descriptors after CPU preAlign has
already produced scoreInfo rows, so it cannot pass Gate v5.1.

## Required Architecture

The next source must be a true pre-scoreInfo descriptor source:

```text
GPU legacy byte scoreInfo-compatible computation
  -> fused GPU scoreInfo consumer state machine
  -> compact candidate attempt descriptors
  -> CPU aligner.Align() authority replay
```

Hard requirements:

```text
Do not use CPU aligner.preAlign() or any CPU legacy scoreInfo producer as the descriptor source.
Do not materialize the full legacy scoreInfo row stream as a host-visible promoted interface.
Do not use host-visible scoreInfo rows as the promoted v5 interface.
Do not emit endpoint, CIGAR, traceback, output row, digest, or accept/reject authority from GPU.
CPU aligner.Align() remains endpoint, CIGAR, traceback, output, and digest authority.
```

Diagnostic validation may compare against CPU scoreInfo after descriptor
emission, but the descriptor source may not depend on those CPU rows to decide
which descriptors to emit.

## Descriptor Contract

Each descriptor must carry enough information for the CPU authority path to
attempt the same semantic candidate the legacy path would attempt:

```text
query_id
target_record_id
target_offset
target_length
legacy_scoreinfo_group_id
legacy_attempt_window_begin
legacy_attempt_window_end
legacy_score
legacy_scoreinfo_order
legacy_attempt_order
scoring_config_key
```

The descriptor may add diagnostic columns, but it must not become final output
authority.

## Gate v5.1 Runtime Requirements

The next runtime smoke must use NEAT1 first1 and must prove:

```text
source_is_pre_scoreinfo = 1
scoreinfo_prealign_reduced = 1
gpu_descriptor_attempts > 0
descriptor_false_negatives = 0
missing_required_attempts = 0
gpu_endpoint_cigar_traceback_output_authority = 0
candidate attempts stay below all-column replay scale
phase7_broad_restart_v5_gate_v5_1_pass = 1
```

The current post-scoreInfo scaffold has:

```text
scoreinfo_prealign_reduced = 0
phase7_broad_restart_v5_gate_v5_1_pass = 0
```

That scaffold must not be promoted by changing telemetry values without
actually moving descriptor emission before CPU scoreInfo/preAlign work.

## Implementation Boundary

Allowed next work:

```text
add a CUDA/bridge API that emits compact candidate attempt descriptors
consume legacy byte scoreInfo-compatible state inside GPU execution
copy only compact descriptors needed by CPU aligner.Align() replay
run CPU validation after descriptor emission in diagnostic mode
record source_is_pre_scoreinfo and scoreinfo_prealign_reduced telemetry
```

Forbidden next work:

```text
continue v4 host-visible scoreInfo source replay as broad path
rename post-scoreInfo descriptor mirror as pre-scoreInfo source
use GPU endpoint/CIGAR/traceback/output/digest authority
add broad_replacement workload-matrix rows before Gate v5.3
claim goal completion from this design checkpoint
```

## Stop Conditions

Stop this v5 branch if any of these occur:

```text
descriptor_false_negatives > 0
missing_required_attempts > 0
full rows or digest differ in CPU-authority replay
scoreInfo/preAlign work is not reduced or replaced
candidate attempts grow to all-column replay scale
candidate wall time is not below CPU authority baseline on first64
fallback accounting is not clean for a claimed GPU path
```

If this happens, the broad objective remains open unless Path A scoped
completion is explicitly accepted.

## Next Gate

```text
phase7_broad_restart_v5_true_pre_scoreinfo_descriptor_source_next_gate = runtime_smoke_true_pre_scoreinfo_descriptor_source_first1
```

The next implementation must be default-off and fail closed until the runtime
telemetry proves a true pre-scoreInfo descriptor source. This design checkpoint
does not make the active goal complete.
