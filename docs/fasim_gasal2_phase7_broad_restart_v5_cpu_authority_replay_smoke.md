# Fasim GASAL2 Phase 7 v5 CPU-Authority Replay Smoke

This checkpoint records the strict first1 Gate v5.2 runtime result for the
true pre-scoreInfo descriptor-source path.

It is a runtime pass checkpoint, not a completion claim.

## Result

```text
phase7_broad_restart_v5_cpu_authority_replay_smoke =
  gate_v5_2_pass_first1

strict_gate_target =
  check-fasim-gasal2-phase7-v5-cpu-authority-replay-runtime-smoke
```

Observed telemetry from the passing first1 runtime smoke:

```text
phase7_v5_cpu_authority_replay_requested = 1
phase7_v5_cpu_authority_replay_active = 1
phase7_v5_cpu_authority_replay_source_is_pre_scoreinfo = 1
phase7_v5_cpu_authority_replay_scoreinfo_prealign_reduced = 1
phase7_v5_cpu_authority_replay_gpu_descriptor_scoreinfos = 718
phase7_v5_cpu_authority_replay_gpu_descriptor_attempts = 2872
phase7_v5_cpu_authority_replay_reference_align_attempts = 2872
phase7_v5_cpu_authority_replay_candidate_align_attempts = 2008
phase7_v5_cpu_authority_replay_descriptor_false_negatives = 0
phase7_v5_cpu_authority_replay_missing_required_attempts = 0
phase7_v5_cpu_authority_replay_cpu_align_authority = 1
phase7_v5_cpu_authority_replay_gpu_endpoint_cigar_traceback_output_authority = 0
phase7_v5_cpu_authority_replay_full_rows_equal = 1
phase7_v5_cpu_authority_replay_digest_match = 1
phase7_v5_cpu_authority_replay_missing_rows = 0
phase7_v5_cpu_authority_replay_extra_rows = 0
phase7_v5_cpu_authority_replay_triplex_mismatches = 0
phase7_v5_cpu_authority_replay_gate_v5_2_pass = 1
candidate_align_attempts < reference_align_attempts
```

The strict Gate v5.2 checker now passes:

```bash
make check-fasim-gasal2-phase7-v5-cpu-authority-replay-runtime-smoke
```

## Root Cause Fixed

The first CPU-authority replay attempt produced real `.lite` output drift even
though internal telemetry reported `full_rows_equal = 1` and `digest_match = 1`.
The drift came from v5 descriptor emission using an integer denominator
approximation for the five legacy attempt windows:

```text
14 / 23 / 32 / 41 / 50
```

That approximation is not byte-for-byte equivalent to the legacy `float Iden`
loop in `fastSIM_extend_from_scoreinfo()`. Some score values produce a one-base
cutlength difference, which can move replay coordinates and change final rows.

The runtime source now uses the same helper for GPU descriptor emission and CPU
coverage reference:

```text
root_cause_fix = legacy_float_identity_cutlength_descriptor_generation
```

This keeps the descriptor attempts aligned with the legacy CPU-authority
attempt windows.

## What This Proves

```text
v5.1 CUDA-emitted compact attempt descriptors can feed CPU-authority replay
CPU aligner.Align() remains the Align authority
full first1 rows and digest match the CPU baseline
candidate Align attempts are reduced from 2872 to 2008
scoreInfo/preAlign source work is reduced/replaced for this gate
descriptor_false_negatives = 0
missing_required_attempts = 0
GPU endpoint/CIGAR/traceback/output authority remains forbidden
```

## What This Does Not Prove

```text
not broad completion
not first64 performance
not full workload speedup
not workload-matrix broad_replacement promotion
not GPU endpoint/CIGAR/traceback/output authority
```

CPU `aligner.Align()` remains the endpoint, CIGAR, traceback, output, and
digest authority.

## Next Required Gate

```text
next_required_gate = phase7_gate_v5_3_first64_broad_gate
```

The next Path B artifact must run the same architecture on a first64-equivalent
broad gate and prove:

```text
full_rows_equal = true
digest_match = true
missing_rows = 0
extra_rows = 0
triplex_mismatches = 0
candidate_wall_seconds < baseline_wall_seconds
candidate_vs_baseline > 1.0
scoreInfo/preAlign work reduced or replaced
Align-side work reduced or replaced
fallback_accounting_clean = true
```

## Decision

```text
broad_objective_status = open
phase7_broad_restart_v5_gate_v5_1_pass = 1
phase7_broad_restart_v5_gate_v5_2_pass = 1
phase7_broad_restart_v5_gate_v5_3_pass = 0
must_not_call_update_goal_complete = 1
```
