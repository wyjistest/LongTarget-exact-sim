# Profile Mode AB Stop Rule Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a stop-rule to the low-overhead profile-mode A/B summarizer so consecutive near-tie repartitions stop further subtree splitting.

**Architecture:** Keep the existing profiling/export pipeline unchanged. Extend the summarizer's decision logic and regression fixtures so the decision surface records repartition attempt counts, detects repeated near-tie repartitions, and emits a stop action without changing the current runtime gate.

**Tech Stack:** Bash regression fixtures, Python summarizer, JSON/TSV artifacts

### Task 1: Lock expected stop-rule behavior with regression fixtures

**Files:**
- Modify: `scripts/check_summarize_sim_initial_host_merge_profile_mode_ab.sh`
- Test: `scripts/check_summarize_sim_initial_host_merge_profile_mode_ab.sh`

**Step 1: Write the failing test**

Add a fixture for repeated `alt_right` repartition near-tie results and assert the decision becomes `mark_gap_before_a00_span_0_alt_right_as_distributed_overhead`.

**Step 2: Run test to verify it fails**

Run: `bash scripts/check_summarize_sim_initial_host_merge_profile_mode_ab.sh`
Expected: FAIL because the summarizer still returns `repartition_gap_before_a00_span_0_alt_right_boundary`.

### Task 2: Implement minimal summarizer support

**Files:**
- Modify: `scripts/summarize_sim_initial_host_merge_profile_mode_ab.py`
- Test: `scripts/check_summarize_sim_initial_host_merge_profile_mode_ab.sh`

**Step 1: Add attempt counters and stop-rule**

Track repartition attempts / consecutive near-tie count for the `alt_right` subtree and emit a stop action after two consecutive near-tie repartitions.

**Step 2: Export new fields**

Write the new counters and subtree status into summary, case rows, and decision JSON without changing `runtime_prototype_allowed`.

### Task 3: Verify regressions

**Files:**
- Test: `scripts/check_summarize_sim_initial_host_merge_profile_mode_ab.sh`
- Test: `scripts/check_run_sim_initial_host_merge_same_workload_materiality_profile.sh`

**Step 1: Run summarizer regression**

Run: `bash scripts/check_summarize_sim_initial_host_merge_profile_mode_ab.sh`
Expected: PASS

**Step 2: Run same-workload regression**

Run: `bash scripts/check_run_sim_initial_host_merge_same_workload_materiality_profile.sh`
Expected: PASS
