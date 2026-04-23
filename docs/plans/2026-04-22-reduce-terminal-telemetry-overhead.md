# Reduce Terminal Telemetry Overhead Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make low-overhead sampled profiling keep terminal telemetry overhead accounting cold/off by default while preserving an explicit opt-in path for classification/debug reruns.

**Architecture:** Add a narrow terminal-telemetry-overhead override that only affects profiler accounting inside the existing terminal telemetry gate. Keep runtime behavior and core candidate-index/state-update counters unchanged. Expose the requested/effective mode through the profile binary and wrapper so artifacts stay auditable.

**Tech Stack:** C++, bash, existing profile binary/test harness, JSON/TSV artifact pipeline

### Task 1: Lock expected behavior with failing regression

**Files:**
- Modify: `scripts/check_run_sim_initial_host_merge_same_workload_materiality_profile.sh`
- Test: `scripts/check_run_sim_initial_host_merge_same_workload_materiality_profile.sh`

**Step 1: Write the failing test**

Add assertions that:
- default `lexical_first_half_sampled` produces `terminal_telemetry_overhead_mode_effective=off`
- default sampled lifecycle summary reports `terminal_path_telemetry_overhead_seconds == 0.0`
- explicit `--terminal-telemetry-overhead on` preserves sampled span fields and yields `terminal_telemetry_overhead_mode_effective=on`

**Step 2: Run test to verify it fails**

Run: `bash scripts/check_run_sim_initial_host_merge_same_workload_materiality_profile.sh`
Expected: FAIL because the binary/wrapper do not yet expose the new telemetry-overhead mode or default-off behavior.

### Task 2: Add binary-level terminal telemetry overhead override

**Files:**
- Modify: `sim.h`
- Modify: `tests/sim_initial_host_merge_context_apply_profile.cpp`
- Test: `scripts/check_run_sim_initial_host_merge_same_workload_materiality_profile.sh`

**Step 1: Add minimal override plumbing**

Implement a requested/effective terminal telemetry overhead mode with:
- default `auto`
- sampled mode defaulting effective behavior to `off`
- explicit `on` available for classification/debug
- `lexical_first_half_sampled_no_terminal_telemetry` still forcing `off`

**Step 2: Surface metadata**

Write `terminal_telemetry_overhead_mode_requested` and `terminal_telemetry_overhead_mode_effective` into per-case and aggregate TSV output.

**Step 3: Run targeted regression**

Run: `bash scripts/check_run_sim_initial_host_merge_same_workload_materiality_profile.sh`
Expected: PASS

### Task 3: Wire the wrapper CLI

**Files:**
- Modify: `scripts/run_sim_initial_host_merge_same_workload_materiality_profile.sh`
- Test: `scripts/check_run_sim_initial_host_merge_same_workload_materiality_profile.sh`

**Step 1: Add wrapper flag**

Expose `--terminal-telemetry-overhead auto|on|off` and forward it to the profile binary when present.

**Step 2: Re-run regression**

Run: `bash scripts/check_run_sim_initial_host_merge_same_workload_materiality_profile.sh`
Expected: PASS with both default-off sampled and explicit-on sampled cases.

### Task 4: Guard downstream behavior

**Files:**
- Modify: `scripts/check_summarize_sim_initial_host_merge_terminal_telemetry_classification.sh` (only if needed)
- Modify: `scripts/check_summarize_sim_initial_host_merge_profile_branch_rollup.sh` (only if needed)
- Test: `bash scripts/check_summarize_sim_initial_host_merge_terminal_telemetry_classification.sh`
- Test: `bash scripts/check_summarize_sim_initial_host_merge_profile_branch_rollup.sh`

**Step 1: Confirm existing summarizers remain compatible**

Only patch downstream checks if the new telemetry-mode metadata requires it. Do not change classification logic unless a compatibility break is real.

**Step 2: Run downstream checks**

Run:
- `bash scripts/check_summarize_sim_initial_host_merge_terminal_telemetry_classification.sh`
- `bash scripts/check_summarize_sim_initial_host_merge_profile_branch_rollup.sh`

Expected: PASS

### Task 5: Final verification

**Files:**
- Reference: `docs/plans/2026-04-22-reduce-terminal-telemetry-overhead.md`

**Step 1: Run the verification set**

Run:
- `bash scripts/check_run_sim_initial_host_merge_same_workload_materiality_profile.sh`
- `bash scripts/check_summarize_sim_initial_host_merge_terminal_telemetry_classification.sh`
- `bash scripts/check_summarize_sim_initial_host_merge_profile_branch_rollup.sh`

**Step 2: Summarize risks**

Call out that the change is profiler-only and that real 5-case reruns are still needed before updating higher-level artifacts again.

### Risks and Notes

- Do not change candidate replacement, start-index writes, or running-state behavior.
- Do not remove the explicit classification path that proves `terminal_path_telemetry_overhead = profiler_only_overhead`.
- Keep the override narrow: it should only affect terminal telemetry overhead accounting, not the broader sampled span timing tree.
