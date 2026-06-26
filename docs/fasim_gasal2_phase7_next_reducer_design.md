# Fasim GASAL2 Phase 7 Next Reducer Design

This is the next Phase 7 design gate after the current CPU-authority candidate
coverage reducer stopped.

It is not runtime code, not a completion claim, and not a permission to use
GASAL2 output as authority.

## Current Stop Evidence

The current candidate reducer has two bounded smoke variants:

```text
prefix coverage:
  false_negative_scoreinfos = 0
  candidate_align_attempts = 51
  reference_align_attempts = 51
  align_reduction = 0

selected-only coverage:
  false_negative_scoreinfos = 0
  candidate_attempts = 2352
  candidate_align_attempts = 51
  reference_align_attempts = 51
  align_reduction = 0
```

Decision:

```text
current_reducer_no_go:
  no_cpu_align_attempt_reduction
```

## Required Direction

The next broad-path reducer must be materially different from the current
prefix/selected-only candidate coverage reducer.

Required shape:

```text
task-local frontier reducer
scoreInfo-local state preservation
legacy single-emission semantics
CPU aligner.Align() remains authority
GASAL2 proposes attempts only
no GPU endpoint authority
no GPU CIGAR or traceback
no output or digest authority from GASAL2
```

The reducer must shrink CPU work before calling CPU `aligner.Align()`:

```text
candidate_align_attempts < reference_align_attempts
false_negative_scoreinfos = 0
triplex_mismatches = 0
missing_triplexes = 0
extra_triplexes = 0
digest_match = 1 or full_rows_equal = 1
candidate_wall_seconds < baseline_wall_seconds
candidate_vs_baseline > 1.0x
```

For the bounded short-query scaffold, wall time is an observed field only. The
synthetic input is too small for stable timing, so that scaffold gate only
proves wiring, exactness, and align-attempt reduction. The hard wall-time gate
remains the NEAT1 first64 broad gate below.

## Forbidden Restarts

Do not restart Phase 7 with:

```text
prefix coverage reducer
selected-only coverage reducer
current broad replacement-consumer replay
current score-prepass state-machine trust
segmented GASAL2 traceback
GASAL2 endpoint as terminal authority
GASAL2 score as accept/reject authority without CPU validation
GASAL2 CIGAR or traceback
MALAT1 scoped two-contract runtime as broad replacement
top5 artifact as full-output replacement
```

## Required Telemetry

Future reducer prototypes must report:

```text
phase7_next_reducer_requested
phase7_next_reducer_active
phase7_next_reducer_tasks
phase7_next_reducer_scoreinfos
phase7_next_reducer_reference_attempts
phase7_next_reducer_candidate_attempts
phase7_next_reducer_candidate_align_attempts
phase7_next_reducer_reference_align_attempts
phase7_next_reducer_false_negative_scoreinfos
phase7_next_reducer_triplex_mismatches
phase7_next_reducer_missing_triplexes
phase7_next_reducer_extra_triplexes
phase7_next_reducer_digest_match
phase7_next_reducer_full_rows_equal
phase7_next_reducer_baseline_wall_seconds
phase7_next_reducer_candidate_wall_seconds
phase7_next_reducer_candidate_vs_baseline
phase7_next_reducer_first_false_negative_task
phase7_next_reducer_first_false_negative_scoreinfo
phase7_next_reducer_first_mismatch
```

## Workload Gate

NEAT1 first64 remains the broad gate.

Initial bounded smoke may use NEAT1 first1 with `REPLAY_PROBE_MAX_TASKS=1`, but
that smoke can only prove a scaffold. It cannot satisfy broad completion.

Current broad-gate status:

```text
short-query bounded smoke:
  digest clean
  false_negative_scoreinfos = 0
  triplex_mismatches = 0
  candidate_align_attempts = 48
  reference_align_attempts = 192
  bounded go, not broad completion

NEAT1 first1 segmented broad-gate probe:
  candidate_align_attempts = 1266
  reference_align_attempts = 2696
  align attempts reduced
  false_negative_scoreinfos = 0
  triplex_mismatches = 0
  digest_match = 0
  full_rows_equal = 0
  baseline_only_rows = 8
  candidate_only_rows = 5
  top5 score/stability/nt-score equality = false
  decision = correctness no-go

NEAT1 first64:
  skipped after first1 correctness no-go
```

Interpretation:

```text
The current segmented next-reducer shape can reduce CPU Align attempts, but it
does not preserve the NEAT1 output contract even on first1. It is stopped as a
broad replacement path unless a different reducer preserves task-local and
scoreInfo-local semantics before reducing CPU Align attempts.
```

Hard go requires:

```text
NEAT1 first64
full row-set equality or digest clean
false_negative_scoreinfos = 0
triplex_mismatches = 0
candidate_align_attempts < reference_align_attempts
candidate_wall_seconds < baseline_wall_seconds
candidate_vs_baseline > 1.0x
```

## Decision

```text
If candidate_align_attempts are not reduced:
  stop this reducer.

If false_negative_scoreinfos is nonzero:
  stop this reducer.

If triplex output or digest changes:
  stop this reducer.

If only kernel time improves but CPU Align work remains unchanged:
  stop this reducer.

If NEAT1 first64 passes correctness and runtime gates:
  next PR may characterize larger workloads, still default-off.
```
