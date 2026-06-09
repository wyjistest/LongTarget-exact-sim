# Fasim GASAL2 Score-Prepass State-Machine Consumer

This is a default-off runtime shadow checkpoint. It records and gates the
remaining broad replacement-consumer direction that still matches the current
evidence.

## Current Evidence

Selected-only replay is no-go because it loses the legacy
`fastSIM_extend_from_scoreinfo()` state machine:

```text
per scoreInfo:
  sweep Iden windows in order
  if sw_score >= scoreInfo.score:
      emit that window and stop sweeping this scoreInfo
  else keep only the best ref_end == cutlength - 1 fallback
  otherwise keep the last nonzero alignment
  emit at most one alignment for this scoreInfo
```

Grouped selected-prefix replay is clean only because it expands selected
scoreInfo groups back to the legacy prefix attempts. That preserves output but
removes the CPU-align reduction.

## Existing Bridge Capability

The GASAL2 bridge already has the required score-only information:

```text
ScoreOnlyResult:
  sw_score
  query_end
  ref_end

FasimGasal2Attempt:
  scoreinfo_index
  start
  cutlength
  prealign_score
  target_end_required_for_fallback
```

The bridge also already has `select_attempts_from_scores()`, which applies the
legacy threshold / best-end / last selector to score-only results and returns at
most one selected attempt per scoreInfo. The current long-query shadow avoids
the unsafe whole-query selector and uses segmented GASAL2 score-prepass hits to
expand each selected scoreInfo back to the required legacy prefix before the
state-machine consumer runs.

## Candidate Shadow

The next useful implementation is:

```text
FASIM_GASAL2_SCORE_PREPASS_STATE_MACHINE_CONSUMER_SHADOW=1
```

Shadow behavior:

```text
1. Build the same attempts as legacy scoreInfo extend.
2. Run segmented GASAL2 score-prepass for those attempts.
3. Expand segmented selected attempts to the required per-scoreInfo legacy
   prefix.
4. Apply the legacy per-scoreInfo state machine over those prefix attempts.
5. CPU-align only the selected/fallback attempt per scoreInfo.
6. Convert/filter/sort normally.
7. Compare task triplex lists against CPU authority.
8. Do not use shadow output for candidate state, output, or digest.
```

The goal is not selected-only replay. The goal is score-prepass state-machine
selection with CPU traceback only on the final selected attempts.

## Required Telemetry

```text
score_prepass_state_machine_shadow_requested
score_prepass_state_machine_shadow_active
score_prepass_state_machine_shadow_tasks
score_prepass_state_machine_shadow_scoreinfos
score_prepass_state_machine_shadow_attempts
score_prepass_state_machine_shadow_selected_attempts
score_prepass_state_machine_shadow_cpu_align_attempts
score_prepass_state_machine_shadow_triplex_mismatches
score_prepass_state_machine_shadow_first_mismatch_source
score_prepass_state_machine_shadow_first_mismatch_kind
score_prepass_state_machine_shadow_score_seconds
score_prepass_state_machine_shadow_select_seconds
score_prepass_state_machine_shadow_cpu_align_seconds
score_prepass_state_machine_shadow_convert_seconds
score_prepass_state_machine_shadow_total_seconds
score_prepass_state_machine_shadow_fallbacks
```

## Hard Gate

Current NEAT1 first1 runtime smoke:

```text
digest clean
tasks = 48
scoreInfo mismatches = 0
length_guard_fallbacks = 0
score_prepass_state_machine_shadow_tasks = 1
score_prepass_state_machine_shadow_attempts = 2,872
score_prepass_state_machine_shadow_selected_attempts = 9,995
score_prepass_state_machine_shadow_cpu_align_attempts = 51
score_prepass_state_machine_shadow_fallbacks = 0
score_prepass_state_machine_shadow_triplex_mismatches = 0
```

`selected_attempts` is raw cross-segment selected hits, not unique traceback
work. The CPU work reduction is measured by `cpu_align_attempts`.

For NEAT1 first64:

```text
digest clean
triplex_mismatches = 0
fallbacks = 0
selected_attempts << attempts
cpu_align_attempts << legacy realpath_extend_align_attempts
GPU score-prepass + state-machine consumer total < CPU fallback wall
MALAT1 scoped positive remains clean
```

## Stop Gate

```text
If score-only state-machine selected attempts do not reproduce CPU triplexes,
  do not promote.

If selected attempts are clean but CPU align attempts are not materially lower,
  do not promote.

If score-prepass total plus CPU traceback is still slower than CPU fallback,
  do not promote.

If endpoint/CIGAR/traceback authority is required for correctness,
  keep CPU authority and do not promote GPU output.
```

## Non-Goals

```text
no GPU endpoint authority
no GPU CIGAR authority
no GPU traceback authority
no output/digest authority
no production opt-in
no selected-only consumer promotion
```

## Gate

```bash
make check-fasim-gasal2-score-prepass-state-machine-consumer
make check-fasim-gasal2-score-prepass-state-machine-consumer-runtime-smoke
make check-fasim-gasal2-score-prepass-state-machine-consumer-segmented-runtime-smoke
```
