# Minimal V3 Score-Band 75-79 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a minimal runtime `minimal_v3` lane that extends non-empty selective fallback with only the `score_band_75_79` candidate class.

**Architecture:** Keep the existing `minimal_v2_selective_fallback` path intact. Add one config/env knob and a post-hoc non-empty rescue path that only runs when the current singleton-missing-margin selector finds nothing. Expose the behavior through a new benchmark run label and keep documentation/reporting aligned.

**Tech Stack:** C++11 runtime in `exact_sim.h`, existing C++ threshold tests, Python benchmark tooling, shell integration check, markdown docs.

### Task 1: Lock the runtime behavior with failing tests

**Files:**
- Modify: `tests/test_exact_sim_two_stage_threshold.cpp`
- Test: `tests/test_exact_sim_two_stage_threshold.cpp`

**Step 1: Write the failing test**

The new tests are already in place:
- rescue a non-empty rejected `75-79` score-band candidate when the new config knob is enabled
- keep `<75` rejected and preserve the `no_singleton_missing_margin` rejection accounting

**Step 2: Run test to verify it fails**

Run: `make check-exact-sim-two-stage-threshold`
Expected: compile failure because `ExactSimTwoStageSelectiveFallbackConfig` does not yet expose `nonEmptyEnableScoreBand7579`.

### Task 2: Implement the minimal runtime support

**Files:**
- Modify: `exact_sim.h`
- Test: `tests/test_exact_sim_two_stage_threshold.cpp`

**Step 1: Write minimal implementation**

- Add `nonEmptyEnableScoreBand7579` to `ExactSimTwoStageSelectiveFallbackConfig`
- Parse `LONGTARGET_TWO_STAGE_SELECTIVE_FALLBACK_NON_EMPTY_SCORE_BAND_75_79`
- In `exact_sim_apply_two_stage_selective_fallback_in_place()`, preserve the current singleton path
- If the singleton path selects nothing, and the new knob is enabled, scan non-empty rejected windows for the best uncovered `75-79` candidate
- Rescue at most one such window per task

**Step 2: Run test to verify it passes**

Run: `make check-exact-sim-two-stage-threshold`
Expected: PASS

### Task 3: Add the benchmark lane

**Files:**
- Modify: `scripts/benchmark_two_stage_threshold_modes.py`
- Modify: `scripts/check_two_stage_threshold_modes.sh`

**Step 1: Write the failing integration expectation**

- Extend the shell check to request and validate `deferred_exact_minimal_v3_scoreband_75_79`

**Step 2: Run check to verify it fails**

Run: `make check-two-stage-threshold-modes`
Expected: failure until the new run label is added to the benchmark tool.

**Step 3: Write minimal implementation**

- Add the new run label to `RUN_LABELS`
- Configure it to use deferred exact + `minimal_v2` reject mode + selective fallback + `max_kept_windows=2` + `score_band_75_79`

**Step 4: Run check to verify it passes**

Run: `make check-two-stage-threshold-modes`
Expected: PASS

### Task 4: Document the lane and verify the repo state

**Files:**
- Modify: `README.md`
- Modify: `EXACT_SIM_PROGRESS.md`

**Step 1: Update docs minimally**

- Describe the new runtime lane and env knob
- Record that the first runtime expansion target is `score_band_75_79`

**Step 2: Run final verification**

Run:
- `make check-exact-sim-two-stage-threshold`
- `make check-two-stage-threshold-modes`
- `git diff --check`

**Step 3: Commit**

```bash
git add exact_sim.h tests/test_exact_sim_two_stage_threshold.cpp \
  scripts/benchmark_two_stage_threshold_modes.py scripts/check_two_stage_threshold_modes.sh \
  README.md EXACT_SIM_PROGRESS.md docs/plans/2026-04-14-minimal-v3-scoreband-75-79.md
git commit -m "Add minimal_v3 score-band 75-79 runtime lane"
```
