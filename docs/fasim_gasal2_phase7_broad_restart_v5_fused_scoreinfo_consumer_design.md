# Fasim GASAL2 Phase 7 v5 Fused ScoreInfo Consumer Design

This document defines the next Path B candidate after the v4 GPU legacy-byte
scoreInfo source replay first64 no-go checkpoint. It is design-only. It does
not add a runtime path and cannot complete the broad objective by itself.

## Scope

```text
phase7_broad_restart_v5_fused_scoreinfo_consumer_design = defined
phase7_broad_restart_v5_status = design_only
phase7_broad_restart_v5_design_family = fused_gpu_scoreinfo_to_candidate_attempt_descriptors
phase7_broad_restart_v5_differs_from_v4_source_replay = 1
phase7_broad_restart_v5_may_claim_completion = 0
phase7_broad_restart_v5_gate_v5_1_pass = 0
phase7_broad_restart_v5_gate_v5_2_pass = 0
phase7_broad_restart_v5_gate_v5_3_pass = 0
phase7_broad_restart_v5_next_gate = fused_scoreinfo_consumer_descriptor_contract_first1
broad_gate_pass = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

The current v4 source replay must not continue as the broad path. The v4
checkpoint was correctness-clean on NEAT1 first64, but slower than the CPU
authority baseline because it still paid for a full GPU scoreInfo row source,
host-visible scoreInfo replay, and CPU-authority realpath work.

## Design Difference From v4

v4 shape:

```text
GPU legacy byte scoreInfo rows
  -> host-visible scoreInfo row stream
  -> CPU all-attempt early-stop replay
  -> CPU aligner.Align() authority
```

v5 shape:

```text
GPU legacy byte scoreInfo computation
  -> GPU consumer state machine
  -> compact candidate attempt descriptors
  -> CPU aligner.Align() authority
```

Required differences:

```text
Do not materialize the full legacy scoreInfo row stream as a host-visible intermediate.
Compute legacy byte scoreInfo and consume the row stream in the same GPU execution design.
Emit compact candidate attempt descriptors, not endpoint, CIGAR, traceback, output, or digest authority.
CPU aligner.Align() remains the only endpoint, CIGAR, traceback, output, and digest authority.
```

The v5 design is not a new GPU aligner. It is a fused scoreInfo-to-attempt
descriptor producer. CPU `aligner.Align()` still validates and emits every
semantic output.

## Candidate Descriptor Contract

Each emitted descriptor must be sufficient for the CPU authority path to
attempt exactly the same semantic candidate as the legacy path would attempt:

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

The descriptor is not allowed to contain final endpoint, CIGAR, traceback,
output row, digest contribution, or accept/reject authority.

## Required Gates

Gate v5.1: descriptor contract first1

```text
workload = NEAT1 first1
GPU descriptor source active
full row-set/digest equality = required
descriptor false negatives = 0
descriptor extra required attempts = 0
scoreInfo/preAlign work reduced or replaced = required
CPU aligner.Align() authority = required
phase7_broad_restart_v5_gate_v5_1_pass = 1
```

Gate v5.2: CPU-authority replay first1

```text
workload = NEAT1 first1
full row-set/digest equality = required
candidate_align_attempts < reference_align_attempts = required
candidate_wall_seconds < baseline_wall_seconds = preferred before first64
fallbacks = 0 for the claimed GPU path = required
phase7_broad_restart_v5_gate_v5_2_pass = 1
```

Gate v5.3: broad first64 gate

```text
workload = NEAT1 first64 or stronger
full row-set/digest equality = required
candidate_wall_seconds < baseline_wall_seconds = required
scoreInfo/preAlign work reduced or replaced = required
Align-side work reduced or replaced = required
fallbacks = 0 for the claimed GPU path = required
phase7_broad_restart_v5_gate_v5_3_pass = 1
```

No `broad_replacement` workload-matrix row may be added before Gate v5.3
passes.

## Stop Conditions

Stop this design if any of these happen:

```text
descriptor false negatives > 0
missing output rows > 0
extra output rows > 0
digest mismatch
GPU descriptor source falls back on the claimed workload
scoreInfo/preAlign work is not reduced or replaced
candidate wall time is not below the CPU authority baseline on the first64 gate
```

If v5 stops, the active goal remains open unless Path A scoped completion is
explicitly accepted.

## Non-Goals

```text
no real opt-in
no default behavior change
no endpoint authority from GPU
no CIGAR authority from GPU
no traceback authority from GPU
no output or digest authority from GPU
no broad_replacement workload-matrix row before Gate v5.3 passes
```

## Next Gate

```text
phase7_broad_restart_v5_next_gate = fused_scoreinfo_consumer_descriptor_contract_first1
```

The next implementation must be default-off and must prove the descriptor
contract on NEAT1 first1 before any first64 broad run. This design checkpoint
only selects the next Path B shape; it does not make the active goal complete.
