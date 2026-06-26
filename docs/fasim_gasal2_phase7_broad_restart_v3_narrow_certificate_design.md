# Fasim GASAL2 Phase 7 v3 Narrow Certificate Design

This is the next Phase 7 v3 design checkpoint after the all-column certificate
proved Gate v3.1 mechanics but failed replay preflight by candidate-attempt
explosion.

It is design-only. It is not runtime code, not a broad replacement claim, and
not permission to use GASAL2 endpoint, CIGAR, traceback, output, or digest as
authority.

```text
phase7_broad_restart_v3_narrow_certificate_design = defined
phase7_broad_restart_v3_narrow_certificate_status = design_only
phase7_broad_restart_v3_next_gate = narrow_certificate_runtime_smoke
phase7_broad_restart_v3_gate_v3_1_pass = 0
phase7_broad_restart_v3_gate_v3_2_pass = 0
broad_gate_pass = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

## Why This Exists

The all-column certificate branch showed that CPU scoreInfo calls can be
bypassed in a pre-scoreInfo descriptor source:

```text
cpu_scoreinfo_calls = 0
candidate_certificate_false_negatives = 0
missing_required_attempts = 0
```

But it covered every target end column and every target window:

```text
candidate_attempts = 168,730,848
reference_align_attempts = 2,872
candidate_attempt_ratio = 58,750.30x
```

That cannot satisfy Gate v3.2:

```text
candidate_attempts < reference_align_attempts required for v3.2
candidate_align_attempts < reference_align_attempts required for v3.2
```

Therefore the next v3 branch must keep the scoreInfo-reducing property while
being strictly narrower than all columns/all windows:

```text
must_be_narrower_than_all_column = 1
do_not_use_all_column_or_all_window_certificate = 1
candidate_attempts < 168,730,848
```

## Required Runtime Env

The runtime smoke must be default-off and use a new env name:

```text
required_runtime_env = FASIM_GASAL2_PHASE7_V3_NARROW_CERTIFICATE
```

The env must not be treated as a real opt-in. It may only emit diagnostic
telemetry and must keep CPU `aligner.Align()` output authority.

## Candidate Sources

A valid narrow certificate source may use one of these approaches:

```text
exact scoreInfo-compatible GPU source:
  reproduce Fasim scoreInfo candidate columns, including byte-saturated SSW
  behavior, bias, word upgrade, window-of-5 peak clustering, and legacy ties

scoreInfo-equivalent seed certificate:
  emit a strict superset of legacy scoreInfo columns using a seed/index proof
  that can be checked without running CPU scoreInfo for every task

bounded overgenerate certificate:
  emit more columns than legacy scoreInfo, but far fewer than all target columns
  and far fewer than all target windows
```

These are not valid narrow certificate sources:

```text
all target columns
all target windows
descriptors derived only after CPU scoreInfo/preAlign
selected rows known only after CPU aligner.Align()
GASAL2 endpoint/CIGAR/traceback/output authority
top5-only equality as broad proof
```

## Gate v3.1 Requirements

The narrow runtime smoke may pass Gate v3.1 only if all of these are true on
NEAT1 first1 or an explicitly equivalent broad-path first1 fixture:

```text
gpu_candidate_scoreinfos > 0
gpu_candidate_attempts > 0
cpu_scoreinfo_calls < baseline_cpu_scoreinfo_calls
candidate_certificate_false_negatives = 0
missing_required_attempts = 0
candidate_attempts < 168,730,848
do_not_use_all_column_or_all_window_certificate = 1
CPU aligner.Align() output authority
no GPU endpoint/CIGAR/traceback/output authority
```

Gate v3.1 does not complete the broad objective. It only permits Gate v3.2
first1 replay.

## Gate v3.2 Requirements

The narrow branch may continue to first64 only if CPU-authority replay passes
on first1:

```text
digest_match = 1
full_rows_equal = 1
missing_rows = 0
extra_rows = 0
triplex_mismatches = 0
candidate_align_attempts < reference_align_attempts
candidate_attempts < reference_align_attempts required for v3.2
scoreInfo/preAlign work reduced or replaced
Align-side work reduced or replaced
```

## Gate v3.3 Requirements

Only the broad first64 gate can create a workload-matrix broad claim:

```text
candidate_vs_baseline > 1.0x
candidate_wall_seconds < baseline_wall_seconds
fallback_accounting_clean = 1
full_output_equality = 1
scoreInfo/preAlign work reduced or replaced
Align-side work reduced or replaced
no broad_replacement workload-matrix row before this gate
```

## Non-Goals

```text
no real opt-in
no default policy change
no GPU endpoint authority
no GPU CIGAR authority
no GPU traceback authority
no GPU output authority
no output drift counted as speedup
no broad_replacement workload-matrix row
```

## Decision

```text
phase7_broad_restart_v3_narrow_certificate_design = defined
phase7_broad_restart_v3_narrow_certificate_status = design_only
phase7_broad_restart_v3_next_gate = narrow_certificate_runtime_smoke
phase7_broad_restart_v3_gate_v3_1_pass = 0
phase7_broad_restart_v3_gate_v3_2_pass = 0
must_be_narrower_than_all_column = 1
do_not_use_all_column_or_all_window_certificate = 1
candidate_attempts < 168,730,848
cpu_scoreinfo_calls < baseline_cpu_scoreinfo_calls
candidate_certificate_false_negatives = 0
missing_required_attempts = 0
CPU aligner.Align() output authority
no GPU endpoint/CIGAR/traceback/output authority
required_runtime_env = FASIM_GASAL2_PHASE7_V3_NARROW_CERTIFICATE
no broad_replacement workload-matrix row
broad_gate_pass = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
```
