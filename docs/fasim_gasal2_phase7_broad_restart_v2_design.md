# Fasim GASAL2 Phase 7 Broad Restart v2 Design

This is a Phase 7 broad-replacement restart design after the current Phase 7
next reducer failed the broad gate.

It is not runtime code, not a completion claim, and not permission to use
GASAL2 output as authority.

## Stop Evidence

The current Phase 7 next reducer is stopped as a broad path:

```text
short-query bounded smoke:
  digest clean
  false_negative_scoreinfos = 0
  triplex_mismatches = 0
  candidate_align_attempts = 48
  reference_align_attempts = 192
  bounded go, not broad completion

NEAT1 first1 broad gate:
  NEAT1 first1 correctness no-go
  digest_match = 0
  full_rows_equal = 0
  baseline_only_rows = 8
  candidate_only_rows = 5
  top5 score/stability/nt-score equality = false
  candidate_align_attempts = 1266
  reference_align_attempts = 2696
```

Interpretation:

```text
The reducer can reduce CPU align attempts, but it does not preserve the
task-local and scoreInfo-local output contract. Reducing attempts before
proving the exact frontier is the wrong order.
```

## v2 Architecture

The v2 restart reverses that order:

```text
frontier log first
exact replay proof before reduction
reducer only after replay proof passes
```

Definitions:

```text
frontier log:
  a CPU-authority trace of every task-local scoreInfo, attempt, Align result,
  selected/rejected state transition, emitted triplex, sort/unique frontier,
  and top-N boundary needed to replay legacy output.

replay proof:
  deterministic reconstruction from the frontier log that reproduces the
  legacy output contract without using GASAL2 result authority.

reducer:
  a later candidate that may drop or avoid work only after the replay proof
  proves the exact state it is allowed to preserve.
```

Required invariants:

```text
task-local frontier identity
scoreInfo-local single-emission state
legacy attempt order
legacy best/last fallback behavior
legacy sort/unique/top-N boundary
CPU aligner.Align() remains authority
GASAL2 output authority = 0
```

The candidate reducer may only consume a proven frontier log. It must not
invent a separate state machine.

## Authority

Allowed:

```text
CPU aligner.Align() remains authority
CPU converted rows remain output authority
GASAL2 may propose scores or descriptors only after replay proof is clean
```

Forbidden:

```text
no GPU endpoint authority
no GPU CIGAR or traceback authority
no output or digest authority from GASAL2
no top5-only proof as broad proof
no current selected-only reducer
no current prefix coverage reducer
no current segmented traceback as broad path
```

## Required Gates

Gate 1:

```text
NEAT1 first1 replay proof
missing_rows = 0
extra_rows = 0
triplex_mismatches = 0
false_negative_scoreinfos = 0
digest_match = 1 or full_rows_equal = 1
candidate_align_attempts = reference_align_attempts
```

This gate proves the frontier log and replay are exact. It is not an
optimization gate.

Gate 2:

```text
NEAT1 first64 replay proof
same correctness requirements as Gate 1
```

Gate 3:

```text
NEAT1 first1 reducer shadow
full row-set equality or digest clean
false_negative_scoreinfos = 0
triplex_mismatches = 0
candidate_align_attempts < reference_align_attempts
scoreInfo/preAlign work reduced
Align-side attempts reduced or replaced
```

Gate 4:

```text
NEAT1 first64 broad gate
full row-set equality or digest clean
false_negative_scoreinfos = 0
triplex_mismatches = 0
candidate_align_attempts < reference_align_attempts
candidate_wall_seconds < baseline_wall_seconds
candidate_vs_baseline > 1.0x
scoreInfo/preAlign work reduced
Align-side attempts reduced or replaced
```

Only Gate 4 can create a broad-replacement matrix row.

## Current Scaffold Evidence

2026-06-12:

```text
phase7_broad_restart_v2_frontier_log_scaffold_gate = runtime_smoke_clean

Command:
  make check-fasim-gasal2-phase7-frontier-log-env
  make check-fasim-gasal2-phase7-frontier-log-runtime-smoke

Runtime:
  FASIM_GASAL2_PHASE7_FRONTIER_LOG=1
  frontier log path is non-empty
  frontier log digest is non-empty
  frontier log TSV schema is present
  frontier log has at least one data row

Authority:
  CPU aligner.Align() remains authority
  GASAL2 output authority = 0
  no GPU endpoint authority
  no GPU CIGAR or traceback authority
  no output or digest authority from GASAL2

Current status:
  diagnostic scaffold only
  no CPU Align attempt reduction yet
  no broad completion claim
  broad_objective_status = open
  must_not_call_update_goal_complete = 1

next gate = NEAT1 first1 exact replay proof
```

## Current Replay Evidence

2026-06-12:

```text
phase7_broad_restart_v2_frontier_replay_gate = exact_no_reduction

Command:
  make characterize-fasim-gasal2-phase7-frontier-replay
  make check-fasim-gasal2-phase7-frontier-replay-result

neat1_first1:
  digest_match = 1
  full_rows_equal = 1
  missing_rows = 0
  extra_rows = 0
  triplex_mismatches = 0
  false_negative_scoreinfos = 0
  frontier_log_rows = 2,872
  frontier_selected_rows = 718
  frontier_positive_align_rows = 2,872
  candidate_align_attempts = reference_align_attempts = 2,872

neat1_first64:
  digest_match = 1
  full_rows_equal = 1
  missing_rows = 0
  extra_rows = 0
  triplex_mismatches = 0
  false_negative_scoreinfos = 0
  frontier_log_rows = 211,976
  frontier_selected_rows = 52,994
  frontier_positive_align_rows = 211,976
  candidate_align_attempts = reference_align_attempts = 211,976

Authority:
  CPU aligner.Align() remains authority
  GASAL2 output authority = 0
  no GPU endpoint authority
  no GPU CIGAR or traceback authority
  no output or digest authority from GASAL2

Current status:
  replay proof is exact for NEAT1 first1 and first64
  reducer-ready frontier evidence is present
  no measured CPU Align attempt reduction yet
  not broad completion
  broad_objective_status = open
  must_not_call_update_goal_complete = 1

next gate = reducer shadow after replay proof
```

## Current Reducer Evidence

2026-06-12:

```text
phase7_broad_restart_v2_frontier_reducer =
  oracle_reduction_projected_not_broad

Command:
  make check-fasim-gasal2-roadmap-phase7-broad-restart-v2-frontier-reducer

neat1_first1:
  digest_match = 1
  full_rows_equal = 1
  missing_rows = 0
  extra_rows = 0
  triplex_mismatches = 0
  false_negative_scoreinfos = 0
  candidate_align_attempts = 718
  reference_align_attempts = 2,872
  align_attempt_reduction = 2,154
  wall_time_basis = oracle_projected
  broad_gate_pass = 0

neat1_first64:
  digest_match = 1
  full_rows_equal = 1
  missing_rows = 0
  extra_rows = 0
  triplex_mismatches = 0
  false_negative_scoreinfos = 0
  candidate_align_attempts = 52,994
  reference_align_attempts = 211,976
  align_attempt_reduction = 158,982
  wall_time_basis = oracle_projected
  broad_gate_pass = 0

Interpretation:
  selected frontier rows define a useful upper bound after exact replay proof
  selected frontier rows are known only after CPU Align in the current log
  a future predictor or measured runtime reducer is still required
  no broad-replacement matrix row may be added yet

Authority:
  CPU aligner.Align() remains authority
  GASAL2 output authority = 0
  no GPU endpoint authority
  no GPU CIGAR or traceback authority
  no output or digest authority from GASAL2

Current status:
  exact projected Align-attempt reduction exists
  measured runtime reducer does not exist yet
  broad_objective_status = open
  must_not_call_update_goal_complete = 1

next gate = measured runtime reducer or predictor
```

## Current Predictor Evidence

2026-06-13:

```text
phase7_broad_restart_v2_frontier_predictor =
  no_go_current_features

Command:
  make check-fasim-gasal2-roadmap-phase7-broad-restart-v2-frontier-predictor

Feature scope tested:
  pre_align_frontier_fields:
    scoreinfo_position
    scoreinfo_score
    attempt_index / rank within scoreInfo
    attempt_start
    attempt_cutlength

Predictors tested:
  keep_all
  keep_first_1/2/3
  keep_last_1/2/3
  start_asc_top_1/2/3
  start_desc_top_1/2/3
  cutlength_asc_top_1/2/3
  cutlength_desc_top_1/2/3
  oracle_selected, marked oracle_post_align

neat1_first64:
  reference_attempts = 211,976
  selected_rows = 52,994
  selected_rank_set = 0,1,2,3
  group_size_set = 4

  oracle_selected:
    false_negative_selected_rows = 0
    align_attempt_reduction = 158,982
    feature_scope = oracle_post_align
    predictor_gate_pass = 0

  keep_all:
    false_negative_selected_rows = 0
    align_attempt_reduction = 0

  reducing pre-align predictors:
    all have false_negative_selected_rows > 0

Decision:
  phase7_frontier_predictor_no_go_current_features

Interpretation:
  the current frontier fields do not contain a safe pre-Align selected-row
  predictor
  the 75% reduction remains an oracle upper bound, not a runtime path
  a future reducer needs a new signal, such as a cheap score/trace surrogate,
  or a different measured runtime design

Current status:
  no measured runtime reducer exists
  broad_objective_status = open
  must_not_call_update_goal_complete = 1

next gate = new pre-Align signal or measured runtime reducer design
```

## Current Score-Signal Evidence

2026-06-13:

```text
phase7_broad_restart_v2_frontier_score_signal = no_go

Command:
  make check-fasim-gasal2-roadmap-phase7-broad-restart-v2-frontier-score-signal

Feature scope tested:
  post_align_score_or_endpoint:
    align_sw_score
    align_ref_begin
    align_ref_end
    align_query_begin
    align_query_end

Signals tested:
  align_sw_score_desc_top_1/2/3
  align_sw_score_asc_top_1/2/3
  align_sw_score_ge_best_zero_fn
  endpoint asc/desc top_1/2/3 variants
  oracle_selected, marked oracle_post_align_selected

neat1_first64:
  reference_attempts = 211,976
  selected_rows = 52,994
  selected_score_rank_counts = 0:33615,1:2469,2:2240,3:14670

  oracle_selected:
    false_negative_selected_rows = 0
    align_attempt_reduction = 158,982
    signal_gate_pass = 0

  align_sw_score_desc_top_3:
    false_negative_selected_rows = 14,670
    align_attempt_reduction = 52,994
    signal_gate_pass = 0

  align_sw_score_ge_best_zero_fn:
    false_negative_selected_rows = 0
    align_attempt_reduction = 0
    signal_gate_pass = 0

Decision:
  phase7_frontier_score_signal_no_go

Interpretation:
  even post-Align score/end fields do not contain a safe reducing signal
  a cheap score-only surrogate is unlikely to identify selected frontier rows
  without reproducing more of the legacy state
  the oracle reduction remains useful only as an upper bound

Current status:
  no measured runtime reducer exists
  broad_objective_status = open
  must_not_call_update_goal_complete = 1

next gate = new non-score signal or measured runtime reducer design
```

## Current Early-Stop Evidence

2026-06-13:

```text
phase7_broad_restart_v2_frontier_early_stop =
  candidate_not_measured

Command:
  make check-fasim-gasal2-roadmap-phase7-broad-restart-v2-frontier-early-stop

Candidate:
  scoreInfo-local early stop after the first selected attempt
  CPU aligner.Align() remains authority for attempts up to the selected row
  attempts after selected are skipped only within the same scoreInfo group

neat1_first1:
  groups = 718
  reference_attempts = 2,872
  candidate_align_attempts = 1,512
  align_attempt_reduction = 1,360
  reduction_fraction = 0.473538
  selected_rows = 718
  multi_selected_groups = 0
  no_selected_groups = 0
  skipped_after_selected_rows = 1,360
  unsafe_skipped_rows = 0

neat1_first64:
  groups = 52,994
  reference_attempts = 211,976
  candidate_align_attempts = 103,953
  align_attempt_reduction = 108,023
  reduction_fraction = 0.509600
  selected_rows = 52,994
  selected_rank_counts = 0:33615,1:2469,2:2240,3:14670
  multi_selected_groups = 0
  no_selected_groups = 0
  skipped_after_selected_rows = 108,023
  unsafe_skipped_rows = 0
  false_negative_selected_rows = 0

Interpretation:
  unlike predictor and score-signal gates, this is a plausible runtime reducer
  because it uses a state observed after CPU-authority Align and selection
  it is still only a frontier-log characterization
  no measured runtime reducer exists yet

Current status:
  runtime_candidate = 1
  measured_runtime = 0
  broad_gate_pass = 0
  broad_objective_status = open
  must_not_call_update_goal_complete = 1

next gate = measured runtime early-stop reducer
```

## Current Early-Stop Runtime Smoke Evidence

2026-06-13:

```text
phase7_broad_restart_v2_frontier_early_stop_runtime =
  runtime_smoke_clean_needs_neat1_first1

Command:
  make check-fasim-gasal2-phase7-frontier-early-stop-runtime-smoke

Runtime:
  FASIM_GASAL2_PHASE7_FRONTIER_EARLY_STOP=1
  default_off = 1
  requested = 1
  active = 1
  scoreinfos = positive
  reference_align_attempts = 192
  candidate_align_attempts = 48
  skipped_attempts = 144
  output digest unchanged

Interpretation:
  measured runtime telemetry now exists for scoreInfo-local early stop
  CPU aligner.Align() remains authority for attempted rows
  skipped_attempts means avoided CPU Align calls relative to all built attempts
  the small fixture proves runtime smoke only, not broad replacement

Current status:
  runtime_smoke = pass
  NEAT1 first1 measured correctness = not_run
  NEAT1 first64 broad gate = not_run
  broad_gate_pass = 0
  broad_objective_status = open
  must_not_call_update_goal_complete = 1

next gate = measured runtime NEAT1 first1 correctness gate
```

## Current Early-Stop Runtime First1 Evidence

2026-06-13:

```text
phase7_broad_restart_v2_frontier_early_stop_runtime_first1 =
  correctness_no_go

Command:
  make characterize-fasim-gasal2-phase7-frontier-early-stop-runtime
  make check-fasim-gasal2-phase7-frontier-early-stop-runtime-result

neat1_first1:
  digest_match = 0
  full_rows_equal = 0
  missing_rows = 7
  extra_rows = 5
  triplex_mismatches = 12
  candidate_align_attempts = 1,309
  reference_align_attempts = 2,872
  align_attempt_reduction = 1,563
  candidate_vs_baseline ~= 0.97
  decision = phase7_frontier_early_stop_runtime_first1_no_go
  decision_reasons = output_rows_differ,missing_rows,extra_rows

Interpretation:
  measured runtime early-stop reduces CPU Align attempts
  but it does not preserve the first broad correctness gate
  output drift cannot be counted as speedup
  NEAT1 first64 broad gate must not run for this candidate

Current status:
  runtime_first1_correctness = no_go
  broad_gate_pass = 0
  broad_objective_status = open
  must_not_call_update_goal_complete = 1

next gate = new reducer or architecture; do not continue this early-stop
  candidate to NEAT1 first64
```

## Stop Conditions

Stop v2 if:

```text
frontier replay cannot reproduce NEAT1 first1 exactly
frontier replay cannot reproduce NEAT1 first64 exactly
the reducer changes task-local frontier identity
the reducer changes scoreInfo-local single-emission state
candidate_align_attempts are not reduced after replay proof
candidate wall time does not beat baseline at NEAT1 first64
```

## Decision

```text
If replay proof fails:
  stop broad GASAL2 replacement work until the legacy state machine is fully
  specified.

If replay proof passes but reducer cannot reduce Align attempts:
  keep the frontier log as diagnostic infrastructure only.

If NEAT1 first64 reducer gate passes:
  next PR may add a broad_replacement workload-matrix row, still default-off.
```

## Next Reducer Design After Early-Stop No-Go

2026-06-13:

```text
phase7_next_reducer_after_early_stop_no_go_design = defined

Document:
  docs/fasim_gasal2_phase7_next_reducer_after_early_stop_no_go_design.md

Design:
  coverage-first all-attempt CPU replay
  candidate coverage before candidate reduction
  do not continue the measured early-stop candidate to NEAT1 first64

Next gate:
  Gate A: all-attempt early-stop runtime first1

Authority:
  CPU aligner.Align() remains authority
  GASAL2 output authority = 0
  no GPU endpoint authority
  no GPU CIGAR or traceback authority

Current status:
  broad_objective_status = open
  must_not_call_update_goal_complete = 1
```

## Current All-Attempt Early-Stop Runtime First1 Evidence

2026-06-13:

```text
phase7_all_attempt_early_stop_runtime_first1 =
  correctness_go_needs_first64

Command:
  make characterize-fasim-gasal2-phase7-all-attempt-early-stop-runtime
  make check-fasim-gasal2-phase7-all-attempt-early-stop-runtime-result

Runtime:
  FASIM_GASAL2_PHASE7_ALL_ATTEMPT_EARLY_STOP=1

neat1_first1:
  digest_match = 1
  full_rows_equal = 1
  missing_rows = 0
  extra_rows = 0
  triplex_mismatches = 0
  false_negative_scoreinfos = 0
  candidate_align_attempts = 2,008
  reference_align_attempts = 2,872
  align_attempt_reduction = 864
  candidate_vs_baseline = near_parity_across_reruns
  decision = phase7_all_attempt_early_stop_runtime_first1_go
  decision_reasons = none

Interpretation:
  all-attempt mode keeps candidate coverage before candidate reduction
  CPU aligner.Align() remains authority
  NEAT1 first1 correctness and Align-side attempt reduction pass
  first1 wall time is near parity across reruns and is not a broad performance gate
  this is not broad completion because scoreInfo/preAlign work is not reduced

Current status:
  first1_correctness = go
  first1_wall_time = near_parity_not_broad_evidence
  first64_broad_gate = not_run
  broad_gate_pass = 0
  broad_objective_status = open
  must_not_call_update_goal_complete = 1

next gate = all-attempt early-stop runtime first64, then coverage-preserving
  GPU candidate generator if first64 remains clean and useful
```

## Current All-Attempt Early-Stop Runtime First64 Evidence

2026-06-13:

```text
phase7_all_attempt_early_stop_runtime_first64 =
  correctness_go_near_parity_not_broad

Command:
  make characterize-fasim-gasal2-phase7-all-attempt-early-stop-runtime-first64
  make check-fasim-gasal2-phase7-all-attempt-early-stop-runtime-first64-result

Runtime:
  FASIM_GASAL2_PHASE7_ALL_ATTEMPT_EARLY_STOP=1

neat1_first64:
  digest_match = 1
  full_rows_equal = 1
  missing_rows = 0
  extra_rows = 0
  triplex_mismatches = 0
  false_negative_scoreinfos = 0
  candidate_align_attempts = 140,087
  reference_align_attempts = 211,976
  align_attempt_reduction = 71,889
  candidate_vs_baseline = near_parity_across_reruns
  decision = phase7_all_attempt_early_stop_runtime_first64_go
  decision_reasons = none

Interpretation:
  all-attempt mode preserves the first64 output contract
  CPU aligner.Align() remains authority
  Align-side work is reduced by 71,889 attempts
  scoreInfo/preAlign work is still CPU work
  wall time is near parity across reruns, not a material broad performance win
  this is a coverage-preserving reducer milestone, not broad completion

Current status:
  first64_correctness = go
  first64_align_side_reduction = go
  first64_wall_time = near_parity_not_material
  broad_gate_pass = 0
  broad_objective_status = open
  must_not_call_update_goal_complete = 1

next gate = coverage-preserving GPU candidate generator
```

## Gate C GPU Candidate Generator Design

2026-06-13:

```text
phase7_gate_c_gpu_candidate_generator_design = defined

Document:
  docs/fasim_gasal2_phase7_gate_c_gpu_candidate_generator_design.md

Purpose:
  reduce or replace CPU scoreInfo/preAlign work while preserving the
  all-attempt early-stop frontier

Required first gate:
  NEAT1 first1 coverage gate
  false_negative_scoreinfos = 0
  missing_rows = 0
  extra_rows = 0
  triplex_mismatches = 0
  candidate_align_attempts <= Gate B candidate_align_attempts
  scoreInfo/preAlign work reduced or replaced

Required broad gate:
  NEAT1 first64 broad gate
  full claimed output contract clean
  candidate_wall_seconds < baseline_wall_seconds
  candidate_vs_baseline > 1.0
  scoreInfo/preAlign work reduced or replaced
  Align-side work reduced or replaced

Authority:
  CPU aligner.Align() remains authority
  GASAL2 output authority = 0
  no GPU endpoint authority
  no GPU CIGAR or traceback authority
  no real opt-in

Current status:
  broad_gate_pass = 0
  broad_objective_status = open
  must_not_call_update_goal_complete = 1
```
