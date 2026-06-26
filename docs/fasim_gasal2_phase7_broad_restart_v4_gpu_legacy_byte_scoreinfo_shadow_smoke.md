# Fasim GASAL2 Phase 7 v4 GPU Legacy-Byte ScoreInfo Shadow Smoke

This checkpoint is the first true GPU source smoke for the Phase 7 v4
scoreInfo-native path. It proves only NEAT1 first1 scoreInfo shadow equality;
it is not a broad replacement gate and does not give GPU endpoint, CIGAR,
traceback, output, or digest authority.

## Scope

```text
phase7_broad_restart_v4_gpu_legacy_byte_scoreinfo_shadow_smoke =
  gpu_contract_clean_first1
phase7_broad_restart_v4_gpu_legacy_byte_scoreinfo_shadow_status =
  first1_gpu_rows_equal_not_broad
required_runtime_env =
  FASIM_GASAL2_PHASE7_V4_GPU_LEGACY_BYTE_SCOREINFO_SHADOW
runtime_default = off
runtime_authority = CPU aligner.Align()
gpu_endpoint_cigar_traceback_output_authority = 0
phase7_broad_restart_v4_gate_v4_1_pass = 1
phase7_broad_restart_v4_gate_v4_2_pass = 0
phase7_broad_restart_v4_gate_v4_3_pass = 0
broad_gate_pass = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

No production output path changes. GPU scoreInfo rows are compared in shadow
only; CPU `aligner.Align()` remains the score/endpoint/traceback/CIGAR/output
and digest authority.

## Runtime Evidence

Command:

```bash
make check-fasim-gasal2-phase7-v4-gpu-legacy-byte-scoreinfo-shadow-runtime-smoke
```

Observed result:

```text
phase7_v4_gpu_legacy_byte_scoreinfo_shadow_runtime_smoke =
  gpu_contract_clean
phase7_v4_gpu_legacy_byte_scoreinfo_shadow_active = 1
phase7_v4_gpu_legacy_byte_scoreinfo_shadow_scoreinfo_rows_equal = 1
phase7_v4_gpu_legacy_byte_scoreinfo_shadow_scoreinfo_order_equal = 1
phase7_v4_gpu_legacy_byte_scoreinfo_shadow_scoreinfo_attempt_windows_equal = 1
phase7_v4_gpu_legacy_byte_scoreinfo_shadow_host_contract_pass = 1
phase7_v4_gpu_legacy_byte_scoreinfo_shadow_gpu_scoreinfo_rows_gt_zero = 1
phase7_v4_gpu_legacy_byte_scoreinfo_shadow_gate_v4_1_pass = 1
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
phase7_v4_legacy_byte_scoreinfo_shadow_gpu_endpoint_cigar_traceback_output_authority = 0
phase7_v4_legacy_byte_scoreinfo_shadow_gate_v4_1_pass = 1
source = gpu_legacy_byte_scoreinfo
```

The runtime smoke checks:

```text
default_off = 1
requested = 1 when env is set
active = 1 when env is set
tasks > 0
cpu_scoreinfo_rows > 0
host_scoreinfo_rows > 0
gpu_scoreinfo_rows > 0
scoreinfo_rows_equal = 1
scoreinfo_order_equal = 1
scoreinfo_attempt_windows_equal = 1
scoreinfo_mismatches = 0
scoreinfo_false_negatives = 0
scoreinfo_extra_required_attempts = 0
gpu_endpoint_cigar_traceback_output_authority = 0
gate_v4_1_pass = 1
source = gpu_legacy_byte_scoreinfo
```

## Interpretation

This passes v4.1 only:

```text
Gate v4.1:
  GPU legacy-byte scoreInfo shadow equality on NEAT1 first1

Still missing:
  CPU-authority replay using GPU scoreInfo as the candidate source
  Align-side attempt reduction
  NEAT1 first64 broad gate
  full row-set/digest broad replacement matrix row
```

The next valid Path B runtime gate is:

```text
phase7_broad_restart_v4_runtime_next_gate =
  gpu_legacy_byte_scoreinfo_source_first1_cpu_authority_replay
```

Do not add a `broad_replacement` workload-matrix row from this smoke. Do not
use GPU/GASAL2 endpoint, CIGAR, traceback, output, or digest authority.
