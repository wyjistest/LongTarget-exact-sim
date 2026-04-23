# Floor Min Maintenance Profiler Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Tighten mixed-hazard analyzer metrics and add exact-safe host-merge min-maintenance profiler telemetry without changing runtime behavior.

**Architecture:** Keep the mixed-hazard path analysis-only and rename ambiguous metrics so the report does not over-claim lookup-level semantics. Add benchmark-only counters/timers around host-side full-set-miss replacement, running-min refresh, and candidate-index lifecycle so the next step can choose between stable min maintenance and eager erase-handle work from evidence instead of locality intuition.

**Tech Stack:** Python analyzer/check scripts, existing C++ host-merge benchmark telemetry, shell regression checks.

### Task 1: Inspect existing profiler hooks and benchmark outputs

**Files:**
- Modify: `docs/plans/2026-04-19-floor-min-maintenance-profiler.md`
- Review: `sim.h`
- Review: `Makefile`
- Review: `tests/test_sim_initial_host_merge_steady_state_trace.cpp`

**Step 1: Identify the current host-merge running-min refresh path**

Run: `rg -n "refreshSimRunningMin|runningMin|full_set_miss|benchmark" sim.h tests Makefile`
Expected: find the concrete function/path that updates `runningMin` and existing benchmark emission points.

**Step 2: Record the exact files/functions to touch**

Run: `rg -n "sim_initial_host_merge|host_merge|cpu_merge" sim.h tests`
Expected: narrow the change set to specific telemetry structs/functions and one or more tests/checks.

### Task 2: Add failing RED checks for analyzer metric naming and profiler telemetry

**Files:**
- Create: `scripts/check_profile_sim_initial_host_merge_min_maintenance.sh`
- Modify: `scripts/check_analyze_sim_initial_host_merge_mixed_hazard_modes.sh`
- Test: `tests/test_sim_initial_host_merge_steady_state_trace.cpp`

**Step 1: Extend the mixed-hazard check to require signed/abs delta fields and renamed floor-change-relative victim metrics**

Run: `bash scripts/check_analyze_sim_initial_host_merge_mixed_hazard_modes.sh`
Expected: FAIL because the analyzer does not yet emit the new field names/metrics.

**Step 2: Add a profiler-focused regression that expects min-maintenance counters to close**

Run: `bash scripts/check_profile_sim_initial_host_merge_min_maintenance.sh`
Expected: FAIL because the telemetry does not exist yet.

### Task 3: Implement analyzer naming cleanup and delta expansion

**Files:**
- Modify: `scripts/analyze_sim_initial_host_merge_mixed_hazard_modes.py`
- Modify: `scripts/check_analyze_sim_initial_host_merge_mixed_hazard_modes.sh`

**Step 1: Emit both signed and absolute running-min delta summary metrics**

Run: `bash scripts/check_analyze_sim_initial_host_merge_mixed_hazard_modes.sh`
Expected: still FAIL until the renamed victim-floor ordering fields also exist.

**Step 2: Rename the victim reappearance ordering metrics to make the FULL_SET_MISS scope explicit**

Run: `bash scripts/check_analyze_sim_initial_host_merge_mixed_hazard_modes.sh`
Expected: PASS.

### Task 4: Add benchmark-only min-maintenance telemetry

**Files:**
- Modify: `sim.h`
- Modify: `Makefile`
- Modify: `tests/test_sim_initial_host_merge_steady_state_trace.cpp`
- Modify or create: `scripts/check_profile_sim_initial_host_merge_min_maintenance.sh`

**Step 1: Add counters/timers for full-set-miss count, floor-changed count, refresh-min calls/time/slots scanned, victim-was-running-min, running-min-slot changes, and candidate-index lookup/erase/insert timing**

Run: `bash scripts/check_profile_sim_initial_host_merge_min_maintenance.sh`
Expected: FAIL until the benchmark/check output closes correctly.

**Step 2: Wire benchmark emission without changing host-merge decisions**

Run: `bash scripts/check_profile_sim_initial_host_merge_min_maintenance.sh`
Expected: PASS.

### Task 5: Verify end-to-end and record heavy-campaign profiler readiness

**Files:**
- Modify: `scripts/check_profile_sim_initial_host_merge_min_maintenance.sh`
- Review: `.tmp/steady_state_hazard_campaign_2026-04-19_15-39-18/campaign/mixed_hazard_modes/*`

**Step 1: Run fresh verification**

Run:
- `bash scripts/check_analyze_sim_initial_host_merge_mixed_hazard_modes.sh`
- `bash scripts/check_profile_sim_initial_host_merge_min_maintenance.sh`

Expected: both pass with pristine output.

**Step 2: Summarize the profiler gate**

Run: inspect generated telemetry and report whether the next action remains `profile_floor_min_maintenance`.
Expected: no runtime prototype enabled; only profiler readiness is claimed.
