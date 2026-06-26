# Fasim GASAL2 Phase 7 v4 ScoreInfo-Native GPU Design

This checkpoint defines the next valid Path B design after the Phase 7 v3
seed/index path stopped. It is design-only. It adds no runtime code, makes no
performance claim, and does not close the active goal.

The design is materially different from the stopped v3 paths:

```text
not GASAL2 standard SW score output
not seed/index min-cover replay
not all-column replay
not bounded-probe certificate
not existing exact-column GPU scoreInfo source
```

## Scope

```text
phase7_broad_restart_v4_scoreinfo_native_design = defined
phase7_broad_restart_v4_status = design_only
phase7_broad_restart_v4_next_gate = legacy_byte_scoreinfo_shadow_first1
phase7_broad_restart_v4_may_claim_completion = 0
broad_gate_pass = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

No GPU endpoint, CIGAR, traceback, output, or digest authority is introduced.
CPU `aligner.Align()` remains the score/endpoint/traceback/CIGAR/output/digest
authority until a later broad gate explicitly proves otherwise.

## Predecessor Boundary

The immediate predecessor is:

```text
docs/fasim_gasal2_phase7_broad_restart_v3_seed_path_stop.md
phase7_broad_restart_v3_seed_path_stop = current_seed_index_path_stopped
phase7_broad_restart_v3_seed_path_status =
  stopped_no_output_clean_non_oracle_reducer
phase7_broad_restart_v3_may_continue_to_first64 = 0
phase7_broad_restart_v3_next_gate =
  different_scoreinfo_compatible_gpu_execution_design_or_path_a_scope_decision
```

The v4 design chooses the Path B branch of that gate:

```text
selected_next_path = different_scoreinfo_compatible_gpu_execution_design
```

Path A scoped completion remains available only if the user explicitly accepts
the narrowed product contract.

## Design Thesis

The broad path has two separate blockers:

```text
1. scoreInfo/preAlign work must move off the CPU authority path.
2. Align-side CPU attempts must still be reduced without changing output.
```

Existing evidence already proves the second half in a diagnostic form:

```text
all-attempt early-stop first1:
  full_rows_equal = 1
  digest_match = 1
  candidate_align_attempts = 2,008
  reference_align_attempts = 2,872

all-attempt early-stop first64:
  full_rows_equal = 1
  digest_match = 1
  candidate_align_attempts = 140,087
  reference_align_attempts = 211,976
  candidate_vs_baseline = near_parity_across_reruns
```

That path is not broad completion because scoreInfo/preAlign work remains CPU
work. The v4 design therefore targets only the missing half: produce the same
legacy scoreInfo stream on GPU, then feed the already-proven all-attempt
early-stop CPU-authority replay.

## Required Legacy ScoreInfo Contract

The GPU path must reproduce Fasim scoreInfo semantics, not GASAL2 generic SW
semantics:

```text
legacy_ssw_byte_saturation = required
legacy_bias_behavior = required
legacy_word_upgrade_on_saturation = required
legacy_window_of_5_peak_clustering = required
legacy_scoreInfo_order = required
legacy_attempt_window_order = required
legacy_tie_policy = required
legacy_alphabet_translation = required
legacy_gap_config = required
```

The candidate rows emitted by v4 must be comparable to CPU scoreInfo rows before
any CPU `aligner.Align()` replay:

```text
scoreinfo_rows_equal = true
scoreinfo_order_equal = true
scoreinfo_attempt_windows_equal = true
scoreinfo_mismatches = 0
scoreinfo_false_negatives = 0
scoreinfo_extra_required_attempts = 0
```

## Architecture

### 1. GPU Legacy ScoreInfo Generator

Input:

```text
query/profile key
translated query
target descriptor offset
target descriptor length
scoring config key
task id
scoreInfo output slot
```

Execution:

```text
implement Fasim/SSW-compatible byte-lane scoreInfo DP
rerun word-lane equivalent only for byte saturation cases
keep query/profile resident where possible
stage target windows contiguously
emit legacy scoreInfo rows in deterministic task/order sequence
```

Output:

```text
scoreInfo row id
task id
score
query end/start fields needed by legacy attempt construction
target end/start fields needed by legacy attempt construction
attempt window descriptors
diagnostic checksum
```

### 2. CPU-Authority All-Attempt Early-Stop Replay

The replay path remains CPU-authority:

```text
CPU aligner.Align() evaluates candidate attempts
all-attempt early-stop keeps the existing scoreInfo-local stop rule
CPU converted rows remain output/digest authority
GPU scoreInfo rows are not endpoint/CIGAR/output authority
```

This is the only reason v4 can plausibly satisfy both broad blockers:

```text
scoreInfo/preAlign reduced by GPU legacy scoreInfo generation
Align-side attempts reduced by all-attempt early-stop replay
```

## Gate Sequence

### Gate v4.1: Shadow First1

Goal:

```text
Prove GPU-generated scoreInfo rows match CPU legacy scoreInfo rows on NEAT1
first1 without using GPU rows for output.
```

Required telemetry:

```text
phase7_v4_legacy_byte_scoreinfo_shadow_active = 1
cpu_scoreinfo_rows > 0
gpu_scoreinfo_rows > 0
scoreinfo_rows_equal = 1
scoreinfo_order_equal = 1
scoreinfo_attempt_windows_equal = 1
scoreinfo_mismatches = 0
scoreinfo_false_negatives = 0
scoreinfo_extra_required_attempts = 0
gpu_endpoint_cigar_traceback_output_authority = 0
```

Stop if:

```text
scoreInfo rows differ
attempt windows differ
byte saturation or word-upgrade cases diverge
tie/order behavior diverges
```

### Gate v4.2: Source First1

Goal:

```text
Use GPU-generated legacy scoreInfo rows as the descriptor source, then replay
with CPU aligner.Align() and all-attempt early-stop.
```

Required telemetry:

```text
cpu_scoreinfo_calls < baseline_cpu_scoreinfo_calls
real_pre_scoreinfo_reducer_proven = 1
full_rows_equal = true
digest_match = true
missing_rows = 0
extra_rows = 0
triplex_mismatches = 0
candidate_align_attempts < reference_align_attempts
fallback_accounting_clean = true
```

Stop if:

```text
CPU scoreInfo work is not reduced
output differs
Align-side attempts are not reduced
fallbacks hide GPU scoreInfo generation
```

### Gate v4.3: First64 Broad Gate

Goal:

```text
Run the same v4 source on NEAT1 first64 or equivalent broad workload.
```

Required telemetry:

```text
full_rows_equal = true
digest_match = true
candidate_wall_seconds < baseline_wall_seconds
candidate_vs_baseline > 1.0
scoreInfo/preAlign work reduced or replaced
Align-side work reduced or replaced
fallback_accounting_clean = true
```

Only after this gate may the workload matrix add:

```text
contract = broad_replacement
```

## Forbidden Shortcuts

```text
no broad_replacement workload-matrix row
no top5-only evidence
no output drift as speedup
no GASAL2 endpoint/CIGAR/traceback/output authority
no seed min-cover replay continuation
no current exact-column GPU scoreInfo source continuation
no first64 run before first1 shadow and source gates pass
```

## Decision

```text
phase7_broad_restart_v4_scoreinfo_native_design = defined
phase7_broad_restart_v4_status = design_only
phase7_broad_restart_v4_gate_v4_1_pass = 0
phase7_broad_restart_v4_gate_v4_2_pass = 0
phase7_broad_restart_v4_gate_v4_3_pass = 0
broad_gate_pass = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

This checkpoint only defines the next implementation contract. The active goal
remains open until either Path A scoped completion is explicitly accepted or a
future v4 implementation passes the first64 broad gate and updates the workload
matrix with a passing `broad_replacement` row.
