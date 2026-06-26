# Fasim GASAL2 Phase 7 Gate C GPU Candidate Generator Design

This is a docs-only design checkpoint for Phase 7 Gate C. It is not runtime
code, not a default policy, not a broad completion claim, and not permission to
use GASAL2 endpoint/CIGAR/traceback/output as authority.

```text
phase7_gate_c_gpu_candidate_generator_design = defined
```

## Context

Gate A and Gate B established a CPU-authority reduction target:

```text
Gate A first1 is correctness-clean:
  digest_match = 1
  full_rows_equal = 1
  candidate_align_attempts = 2,008
  reference_align_attempts = 2,872

Gate B first64 is correctness-clean:
  digest_match = 1
  full_rows_equal = 1
  candidate_align_attempts = 140,087
  reference_align_attempts = 211,976
  align_attempt_reduction = 71,889
  wall time = near parity across reruns
```

The remaining blocker is not all-attempt early-stop correctness. The blocker is
that scoreInfo/preAlign work is still CPU work, and first64 wall time is near
parity rather than a material broad win.

```text
broad_gate_pass = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

## Goal

Gate C should test whether a GASAL2 or GPU-assisted candidate generator can
replace or materially reduce CPU scoreInfo/preAlign work while preserving the
all-attempt early-stop frontier.

The design principle is:

```text
candidate coverage before candidate reduction
```

The GPU side may propose candidate descriptors. CPU `aligner.Align()` remains
the row/output/digest authority.

## Authority

Allowed:

```text
coverage-preserving GPU candidate generator
GPU may generate candidate descriptors
CPU aligner.Align() remains authority
CPU replay decides selected rows
CPU converted rows remain row/output/digest authority
Gate A/Gate B all-attempt early-stop output is the comparison target
```

Forbidden:

```text
GASAL2 output authority = 0
no GPU endpoint authority
no GPU CIGAR or traceback authority
no real opt-in
no default policy change
no workload matrix broad_replacement row until Gate C first64 passes
no broad completion from first1-only evidence
```

## Proposed Architecture

Gate C should be implemented as a default-off shadow path.

### C0: Oracle Frontier Export

Use the existing all-attempt early-stop runtime as the oracle. Export the
scoreInfo/attempt frontier needed to reproduce Gate A and Gate B:

```text
task_id
scoreinfo_index
scoreinfo_position
scoreinfo_score
attempt_rank
attempt_start
attempt_cutlength
selected_by_cpu_replay
emitted_before
emitted_after
```

This export is diagnostic only. It must not change output.

### C1: GPU Candidate Descriptor Generator

Generate candidate descriptors using GASAL2 or another GPU-assisted score path:

```text
task_id
scoreinfo_index or generated_scoreinfo_key
candidate_position
candidate_score
attempt_start
attempt_cutlength
source = gpu_candidate_generator
```

The first version should prefer a conservative superset over an aggressive
reducer. The gate is coverage-preserving behavior, not minimum descriptor
count.

### C2: Coverage Comparison

Compare GPU descriptors against the all-attempt early-stop frontier before any
candidate is used for CPU replay.

Required counters:

```text
oracle_scoreinfos
oracle_attempts
gate_b_candidate_align_attempts
gpu_candidate_scoreinfos
gpu_candidate_attempts
covered_selected_scoreinfos
false_negative_scoreinfos = 0
missing_required_attempts = 0
extra_candidate_attempts
candidate_align_attempts <= Gate B candidate_align_attempts
```

If selected scoreInfos are missed, stop. A faster run with missing selected
scoreInfos is not useful.

### C3: CPU-Authority Replay

Only after C2 passes, replay GPU candidate descriptors through CPU
`aligner.Align()` and the existing all-attempt early-stop emission logic.

Gate C first1 correctness requirements:

```text
NEAT1 first1 coverage gate
digest_match = 1 or full_rows_equal = 1
missing_rows = 0
extra_rows = 0
triplex_mismatches = 0
false_negative_scoreinfos = 0
candidate_align_attempts <= Gate B candidate_align_attempts
scoreInfo/preAlign work reduced or replaced
```

### C4: First64 Broad Gate

Only after first1 passes, run NEAT1 first64.

Gate C first64 broad requirements:

```text
NEAT1 first64 broad gate
digest_match = 1 or full_rows_equal = 1
missing_rows = 0
extra_rows = 0
triplex_mismatches = 0
false_negative_scoreinfos = 0
candidate_align_attempts <= Gate B candidate_align_attempts
candidate_wall_seconds < baseline_wall_seconds
candidate_vs_baseline > 1.0
scoreInfo/preAlign work reduced or replaced
Align-side work reduced or replaced
fallbacks = 0 for the claimed GPU candidate path
```

Only if this gate passes may the workload matrix add a
`contract=broad_replacement` row.

```text
workload matrix broad_replacement row is forbidden until Gate C first64 passes
```

## Telemetry

Gate C telemetry should be itemized enough to decide whether GPU work helped
or only moved cost around:

```text
phase7_gate_c_requested
phase7_gate_c_active
phase7_gate_c_tasks
phase7_gate_c_oracle_scoreinfos
phase7_gate_c_oracle_attempts
phase7_gate_c_gpu_candidate_scoreinfos
phase7_gate_c_gpu_candidate_attempts
phase7_gate_c_false_negative_scoreinfos
phase7_gate_c_missing_required_attempts
phase7_gate_c_extra_candidate_attempts
phase7_gate_c_candidate_align_attempts
phase7_gate_c_gate_b_candidate_align_attempts
phase7_gate_c_scoreinfo_cpu_seconds
phase7_gate_c_gpu_candidate_seconds
phase7_gate_c_cpu_replay_seconds
phase7_gate_c_total_seconds
phase7_gate_c_digest_match
phase7_gate_c_full_rows_equal
```

## Stop Conditions

Stop Gate C if:

```text
false_negative_scoreinfos > 0
missing_rows > 0
extra_rows > 0
triplex_mismatches > 0
candidate_align_attempts > Gate B candidate_align_attempts
scoreInfo/preAlign work is not reduced or replaced
first64 wall time is not better than baseline
GPU output is required as authority for the path to work
```

## Decision

```text
If Gate C first1 fails:
  stop GPU candidate generator work and keep Gate A/B as diagnostic only.

If Gate C first1 passes but first64 fails:
  keep the path as first1 evidence only; do not promote to broad replacement.

If Gate C first64 passes:
  update docs/fasim_gasal2_workload_matrix.tsv with a broad_replacement row,
  rerun Phase 6 and Phase 8, and only then consider Path B completion.

Until then:
  broad_gate_pass = 0
  broad_objective_status = open
  must_not_call_update_goal_complete = 1
```

## Stop Checkpoint

```text
Document:
  docs/fasim_gasal2_phase7_gate_c_stop_checkpoint.md

phase7_gate_c_stop_checkpoint = current_source_no_go
current_gate_c_source_status = stopped_no_gpu_candidate_descriptors
gate_c_first64_allowed = 0
restart_requires_new_gpu_candidate_descriptor_source = 1

Restart requires:
  gpu_candidate_scoreinfos > 0
  gpu_candidate_attempts > 0
  scoreinfo_reduced = 1
  candidate_align_attempts <= 2,008
  output contract clean
  CPU aligner.Align() remains authority

Until then:
  broad_gate_pass = 0
  broad_objective_status = open
  must_not_call_update_goal_complete = 1
```

## Implementation Plan

```text
phase7_gate_c_gpu_candidate_generator_implementation_plan = defined

Document:
  docs/superpowers/plans/2026-06-13-fasim-gasal2-phase7-gate-c-gpu-candidate-generator.md

Scope:
  default-off shadow path
  FASIM_GASAL2_PHASE7_GATE_C_GPU_CANDIDATES=1
  Gate C env and telemetry
  oracle frontier reuse
  GPU candidate descriptor shadow
  coverage comparison gate
  CPU-authority replay gate
  NEAT1 first1 coverage gate
  NEAT1 first64 broad gate

Still forbidden:
  no real opt-in
  no GPU endpoint authority
  no GPU CIGAR or traceback authority
  workload matrix broad_replacement row is forbidden until Gate C first64 passes

Current status:
  design and implementation plan are defined
  runtime env/smoke evidence is clean for the oracle-metric scaffold
  first1 and first64 Gate C coverage evidence are not yet present
  broad_gate_pass = 0
  broad_objective_status = open
  must_not_call_update_goal_complete = 1
```

## Runtime Scaffold Checkpoint

```text
phase7_gate_c_runtime_smoke = pass

Command:
  make check-fasim-gasal2-phase7-gate-c-runtime-smoke

Smoke evidence:
  default_off_requested = 0
  default_off_active = 0
  candidate_requested = 1
  candidate_active = 0
  candidate_tasks = 48
  candidate_oracle_scoreinfos = 48
  candidate_oracle_attempts = 192
  candidate_gpu_candidate_scoreinfos = 0
  candidate_gpu_candidate_attempts = 0
  candidate_false_negative_scoreinfos = 0
  candidate_missing_required_attempts = 0
  candidate_extra_candidate_attempts = 0

Interpretation:
  Gate C env and telemetry are wired.
  This is an oracle-metric scaffold smoke, not GPU candidate generation.
  The next implementation gate is Task 3: GPU Candidate Descriptor Shadow.
  No first1/first64 coverage proof has passed yet.
  broad_gate_pass = 0
  broad_objective_status = open
  must_not_call_update_goal_complete = 1
```

## First1 Descriptor Shadow Checkpoint

```text
phase7_gate_c_first1 = no_go_no_gpu_candidate_descriptors

Command:
  make characterize-fasim-gasal2-phase7-gate-c-first1
  make check-fasim-gasal2-phase7-gate-c-first1-result

Result:
  digest_match = 1
  full_rows_equal = 1
  candidate_align_attempts = 2,008
  gate_b_candidate_align_attempts = 2,008
  scoreinfo_reduced = 0
  oracle_scoreinfos = 718
  oracle_attempts = 2,872
  gpu_candidate_scoreinfos = 0
  gpu_candidate_attempts = 0
  decision = phase7_gate_c_first1_no_go
  decision_reasons = no_gpu_candidate_descriptors,scoreinfo_not_reduced

Interpretation:
  The CPU-authority replay side remains clean.
  The current Gate C prototype has no GPU candidate descriptor source for
  NEAT1 first1.
  It does not reduce or replace scoreInfo/preAlign work.
  It must not continue to first64 broad characterization.
  broad_gate_pass = 0
  broad_objective_status = open
  must_not_call_update_goal_complete = 1
```
