# Fasim GASAL2 Phase 7 v4 GPU Legacy-Byte ScoreInfo Source First64 Broad Gate

This checkpoint records the NEAT1 first64 broad-gate run for the v4 GPU
legacy-byte scoreInfo source replay path. It is a no-go checkpoint for the
current v4 source replay implementation: correctness stays clean, but wall
time is slower than the CPU authority baseline.

## Scope

```text
phase7_broad_restart_v4_gpu_legacy_byte_scoreinfo_source_first64_broad_gate =
  correctness_clean_performance_no_go
phase7_broad_restart_v4_gpu_legacy_byte_scoreinfo_source_first64_status =
  first64_correctness_clean_performance_no_go
required_runtime_env =
  FASIM_GASAL2_PHASE7_V4_GPU_LEGACY_BYTE_SCOREINFO_SOURCE_REPLAY
runtime_default = off
runtime_authority = CPU aligner.Align()
gpu_endpoint_cigar_traceback_output_authority = 0
phase7_broad_restart_v4_gate_v4_1_pass = 1
phase7_broad_restart_v4_gate_v4_2_pass = 1
phase7_broad_restart_v4_gate_v4_3_pass = 0
broad_gate_pass = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

The GPU path supplies scoreInfo rows only after CPU/host/GPU scoreInfo equality
is clean. CPU `aligner.Align()` remains the endpoint, CIGAR, traceback, output,
and digest authority.

## Runtime Evidence

Manual NEAT1 first64 run:

```text
baseline_wall_seconds = 86.358386
candidate_wall_seconds = 134.744406
candidate_vs_baseline = 0.640905
digest_match = 1

candidate_gate_v4_2_pass = 1
candidate_gpu_scoreinfo_rows = 52994
candidate_source_replay_scoreinfo_rows = 52994
candidate_realpath_requested = 1
candidate_realpath_fallbacks = 0
candidate_realpath_extend_scoreinfo_groups = 52994
candidate_realpath_extend_align_attempts = 140087
candidate_realpath_extend_seconds = 52.1721
candidate_realpath_extend_align_seconds = 52.0788
reference_align_attempts = 211976
align_attempt_reduction = 71889
```

## Gate Decision

```text
correctness_gate:
  digest_match = 1
  candidate_gate_v4_2_pass = 1
  candidate_gpu_scoreinfo_rows = candidate_source_replay_scoreinfo_rows

align_side_gate:
  candidate_realpath_extend_align_attempts = 140087
  reference_align_attempts = 211976
  align_attempt_reduction = 71889

performance_gate:
  baseline_wall_seconds = 86.358386
  candidate_wall_seconds = 134.744406
  candidate_vs_baseline = 0.640905
  performance_gate_pass = 0
```

The first64 result preserves output digest and reduces CPU Align attempts, but
it does not beat the CPU authority baseline. The current v4 source replay path
therefore cannot be promoted to broad completion or a real replacement path.

## Next Gate

```text
phase7_broad_restart_v4_runtime_next_gate =
  different_gpu_execution_design_or_path_a_scope_decision
```

Do not add a `broad_replacement` workload-matrix row from this first64 result.
Do not use GPU/GASAL2 endpoint, CIGAR, traceback, output, or digest authority.

This is a no-go checkpoint for the current v4 source replay implementation.
