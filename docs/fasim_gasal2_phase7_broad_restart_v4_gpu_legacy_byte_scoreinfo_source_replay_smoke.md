# Fasim GASAL2 Phase 7 v4 GPU Legacy-Byte ScoreInfo Source Replay Smoke

This checkpoint advances the Phase 7 v4 scoreInfo-native path from shadow row
comparison to first1 CPU-authority replay. It is still default-off and does not
give GPU endpoint, CIGAR, traceback, output, or digest authority.

## Scope

```text
phase7_broad_restart_v4_gpu_legacy_byte_scoreinfo_source_replay_smoke =
  cpu_authority_replay_clean_first1
phase7_broad_restart_v4_gpu_legacy_byte_scoreinfo_source_replay_status =
  first1_replay_clean_needs_first64_broad_gate
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

No production output path changes. The diagnostic run uses GPU legacy-byte
scoreInfo rows as the source only after CPU/host/GPU scoreInfo rows match, then
replays through CPU `aligner.Align()`. CPU output remains the authority for the
digest comparison.

## Runtime Evidence

Command:

```bash
make check-fasim-gasal2-phase7-v4-gpu-legacy-byte-scoreinfo-source-replay-runtime-smoke
```

Observed result:

```text
phase7_v4_gpu_legacy_byte_scoreinfo_source_replay_runtime_smoke =
  cpu_authority_replay_first1
phase7_v4_gpu_legacy_byte_scoreinfo_source_replay_active = 1
phase7_v4_gpu_legacy_byte_scoreinfo_source_replay_digest_match = 1
phase7_v4_gpu_legacy_byte_scoreinfo_source_replay_scoreinfo_rows_equal = 1
phase7_v4_gpu_legacy_byte_scoreinfo_source_replay_scoreinfo_order_equal = 1
phase7_v4_gpu_legacy_byte_scoreinfo_source_replay_scoreinfo_attempt_windows_equal = 1
phase7_v4_gpu_legacy_byte_scoreinfo_source_replay_gpu_scoreinfo_rows_gt_zero = 1
phase7_v4_gpu_legacy_byte_scoreinfo_source_replay_align_attempts = 2008
phase7_v4_gpu_legacy_byte_scoreinfo_source_replay_reference_align_attempts = 2872
phase7_v4_gpu_legacy_byte_scoreinfo_source_replay_align_attempt_reduction = 864
phase7_v4_gpu_legacy_byte_scoreinfo_source_replay_gate_v4_2_pass = 1
phase7_broad_restart_v4_broad_gate_pass = 0
```

Underlying runtime metrics:

```text
phase7_v4_legacy_byte_scoreinfo_shadow_tasks = 48
phase7_v4_legacy_byte_scoreinfo_shadow_cpu_scoreinfo_rows = 718
phase7_v4_legacy_byte_scoreinfo_shadow_host_scoreinfo_rows = 718
phase7_v4_legacy_byte_scoreinfo_shadow_gpu_scoreinfo_rows = 718
phase7_v4_legacy_byte_scoreinfo_shadow_scoreinfo_rows_equal = 1
phase7_v4_legacy_byte_scoreinfo_shadow_scoreinfo_order_equal = 1
phase7_v4_legacy_byte_scoreinfo_shadow_scoreinfo_attempt_windows_equal = 1
phase7_v4_legacy_byte_scoreinfo_shadow_scoreinfo_mismatches = 0
phase7_v4_legacy_byte_scoreinfo_shadow_scoreinfo_false_negatives = 0
phase7_v4_legacy_byte_scoreinfo_shadow_scoreinfo_extra_required_attempts = 0
phase7_v4_legacy_byte_scoreinfo_shadow_host_contract_pass = 1
phase7_v4_legacy_byte_scoreinfo_shadow_source_replay_requested = 1
phase7_v4_legacy_byte_scoreinfo_shadow_source_replay_active = 1
phase7_v4_legacy_byte_scoreinfo_shadow_source_replay_streaming_ready = 1
phase7_v4_legacy_byte_scoreinfo_shadow_source_replay_scoreinfo_rows = 718
phase7_v4_legacy_byte_scoreinfo_shadow_source_replay_cpu_authority = 1
phase7_v4_legacy_byte_scoreinfo_shadow_source_replay_gpu_endpoint_cigar_traceback_output_authority = 0
phase7_v4_legacy_byte_scoreinfo_shadow_gate_v4_1_pass = 1
phase7_v4_legacy_byte_scoreinfo_shadow_gate_v4_2_pass = 1
source = gpu_legacy_byte_scoreinfo_source_replay
```

Replay metrics:

```text
realpath_requested = 1
realpath_fallbacks = 0
realpath_extend_scoreinfo_groups = 718
realpath_extend_align_attempts = 2008
reference_align_attempts = 2872
align_attempt_reduction = 864
```

## Interpretation

This passes v4.2 only:

```text
Gate v4.1:
  GPU legacy-byte scoreInfo shadow equality on NEAT1 first1

Gate v4.2:
  GPU legacy-byte scoreInfo source replay through CPU aligner.Align() on NEAT1
  first1, with digest clean and Align-side attempt reduction

Still missing:
  NEAT1 first64 or equivalent broad gate
  candidate wall-time win on the broad gate
  full row-set/digest broad replacement matrix row
```

The next valid Path B runtime gate is:

```text
phase7_broad_restart_v4_runtime_next_gate =
  gpu_legacy_byte_scoreinfo_source_first64_broad_gate
```

Do not add a `broad_replacement` workload-matrix row from this smoke. Do not
use GPU/GASAL2 endpoint, CIGAR, traceback, output, or digest authority.
