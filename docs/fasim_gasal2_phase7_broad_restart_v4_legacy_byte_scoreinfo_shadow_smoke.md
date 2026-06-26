# Fasim GASAL2 Phase 7 v4 Legacy-Byte ScoreInfo Shadow Smoke

This checkpoint is the first runtime smoke after the Phase 7 v4
scoreInfo-native design. It is a host-contract checkpoint, not a GPU gate pass
and not a broad completion claim.

## Scope

```text
phase7_broad_restart_v4_legacy_byte_scoreinfo_shadow_smoke =
  host_contract_clean_needs_gpu
phase7_broad_restart_v4_legacy_byte_scoreinfo_shadow_status =
  host_reconstruction_clean_gpu_rows_zero
required_runtime_env =
  FASIM_GASAL2_PHASE7_V4_LEGACY_BYTE_SCOREINFO_SHADOW
runtime_default = off
runtime_authority = CPU aligner.Align()
gpu_endpoint_cigar_traceback_output_authority = 0
phase7_broad_restart_v4_gate_v4_1_pass = 0
broad_gate_pass = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

No GPU endpoint, CIGAR, traceback, output, or digest authority is introduced.
CPU `aligner.Align()` remains the score/endpoint/traceback/CIGAR/output/digest
authority.

## Runtime Evidence

Command:

```bash
make check-fasim-gasal2-phase7-v4-legacy-byte-scoreinfo-shadow-runtime-smoke
```

Observed result:

```text
phase7_v4_legacy_byte_scoreinfo_shadow_runtime_smoke =
  host_contract_clean_needs_gpu
phase7_v4_legacy_byte_scoreinfo_shadow_active = 1
phase7_v4_legacy_byte_scoreinfo_shadow_scoreinfo_rows_equal = 1
phase7_v4_legacy_byte_scoreinfo_shadow_scoreinfo_order_equal = 1
phase7_v4_legacy_byte_scoreinfo_shadow_scoreinfo_attempt_windows_equal = 1
phase7_v4_legacy_byte_scoreinfo_shadow_host_contract_pass = 1
phase7_v4_legacy_byte_scoreinfo_shadow_gpu_scoreinfo_rows = 0
phase7_v4_legacy_byte_scoreinfo_shadow_gate_v4_1_pass = 0
phase7_broad_restart_v4_broad_gate_pass = 0
```

The runtime smoke checks:

```text
default_off = 1
requested = 1 when env is set
active = 1 when env is set
tasks > 0
cpu_scoreinfo_rows > 0
host_scoreinfo_rows > 0
scoreinfo_rows_equal = 1
scoreinfo_order_equal = 1
scoreinfo_attempt_windows_equal = 1
scoreinfo_mismatches = 0
scoreinfo_false_negatives = 0
scoreinfo_extra_required_attempts = 0
gpu_scoreinfo_rows = 0
gpu_endpoint_cigar_traceback_output_authority = 0
gate_v4_1_pass = 0
source = host_column_score_reconstruction
```

## Interpretation

This smoke proves only the host-side reconstruction contract:

```text
CPU legacy scoreInfo source:
  aligner.preAlign()

host reconstruction source:
  aligner.preAlignColumnScores()
  legacy threshold filter
  legacy window-of-5 peak clustering
  legacy first-max tie behavior
```

It does not prove a GPU scoreInfo source:

```text
gpu_scoreinfo_rows = 0
phase7_broad_restart_v4_gate_v4_1_pass = 0
```

The next valid Path B runtime gate remains:

```text
phase7_broad_restart_v4_next_gate =
  gpu_legacy_byte_scoreinfo_shadow_first1
```

Do not add a `broad_replacement` workload-matrix row from this smoke. Do not
use GPU/GASAL2 endpoint, CIGAR, traceback, output, or digest authority.
