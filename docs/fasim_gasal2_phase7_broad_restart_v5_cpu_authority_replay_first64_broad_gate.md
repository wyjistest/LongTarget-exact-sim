# Fasim GASAL2 Phase 7 v5 CPU-Authority Replay First64 Broad Gate

This checkpoint records the NEAT1 first64 broad-gate run for the Phase 7 v5
CPU-authority descriptor replay path. It is a no-go checkpoint for the current
v5 architecture: final `.lite` output stays digest/row clean, but wall time is
slower than the CPU baseline and the descriptor coverage/fallback accounting
gate is not clean.

## Scope

```text
phase7_broad_restart_v5_cpu_authority_replay_first64_broad_gate =
  correctness_clean_performance_no_go
phase7_broad_restart_v5_cpu_authority_replay_first64_status =
  first64_correctness_clean_performance_no_go
required_runtime_env =
  FASIM_GASAL2_PHASE7_V5_CPU_AUTHORITY_REPLAY
runtime_default = off
runtime_authority = CPU aligner.Align()
gpu_endpoint_cigar_traceback_output_authority = 0
phase7_broad_restart_v5_gate_v5_1_pass = 1
phase7_broad_restart_v5_gate_v5_2_pass = 1
phase7_broad_restart_v5_gate_v5_3_pass = 0
broad_gate_pass = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

CPU `aligner.Align()` remains the endpoint, CIGAR, traceback, output, and
digest authority. GASAL2/CUDA only supplies candidate attempt descriptors.

## Runtime Evidence

Command:

```bash
make characterize-fasim-gasal2-phase7-v5-cpu-authority-replay-first64
make check-fasim-gasal2-phase7-v5-cpu-authority-replay-first64-result
```

Report:

```text
workload = neat1_first64
record_limit = 64
attempted = 1
digest_match = 1
full_rows_equal = 1
missing_rows = 0
extra_rows = 0
triplex_mismatches = 0
candidate_align_attempts = 115561
reference_align_attempts = 211976
align_attempt_reduction = 96415
candidate_wall_seconds = 124.399845
baseline_wall_seconds = 87.827405
candidate_vs_baseline = 0.706009
requested = 1
active = 1
source_is_pre_scoreinfo = 1
scoreinfo_prealign_reduced = 1
gpu_descriptor_scoreinfos = 52994
gpu_descriptor_attempts = 211976
descriptor_false_negatives = 0
missing_required_attempts = 624
cpu_align_authority = 1
gpu_endpoint_cigar_traceback_output_authority = 0
fallback_accounting_clean = 0
broad_gate_pass = 0
decision = phase7_v5_cpu_authority_replay_first64_broad_gate_no_go
decision_reasons =
  telemetry_row_diff,fallback_accounting_not_clean,candidate_vs_baseline_not_above_1
```

The final output files match, but internal v5 telemetry reports:

```text
benchmark.fasim_gasal2_phase7_v5_cpu_authority_replay_full_rows_equal = 1
benchmark.fasim_gasal2_phase7_v5_cpu_authority_replay_digest_match = 1
benchmark.fasim_gasal2_phase7_v5_cpu_authority_replay_missing_rows = 624
benchmark.fasim_gasal2_phase7_v5_cpu_authority_replay_missing_required_attempts = 624
```

This means the broad gate cannot claim clean fallback/coverage accounting even
though the final `.lite` output happens to remain equal for this run.

## Gate Decision

```text
correctness_gate:
  final digest_match = 1
  final full_rows_equal = 1
  triplex_mismatches = 0

align_side_gate:
  candidate_align_attempts = 115561
  reference_align_attempts = 211976
  align_attempt_reduction = 96415

scoreinfo_prealign_gate:
  source_is_pre_scoreinfo = 1
  scoreinfo_prealign_reduced = 1

fallback_accounting_gate:
  descriptor_false_negatives = 0
  missing_required_attempts = 624
  fallback_accounting_clean = 0

performance_gate:
  baseline_wall_seconds = 87.827405
  candidate_wall_seconds = 124.399845
  candidate_vs_baseline = 0.706009
  performance_gate_pass = 0

broad_gate_pass = 0
```

The v5 path reduces CPU Align attempts and bypasses CPU scoreInfo/preAlign as
the source, but it does not beat the CPU authority baseline and its coverage
accounting is not clean. The current v5 CPU-authority descriptor replay path
therefore cannot be promoted to broad completion or a real replacement path.

## Next Gate

```text
phase7_broad_restart_v5_runtime_next_gate =
  different_gpu_execution_design_or_path_a_scope_decision
```

Do not add a `broad_replacement` workload-matrix row from this first64 result.
Do not use GPU/GASAL2 endpoint, CIGAR, traceback, output, or digest authority.

This is a no-go checkpoint for the current v5 CPU-authority descriptor replay
implementation.
