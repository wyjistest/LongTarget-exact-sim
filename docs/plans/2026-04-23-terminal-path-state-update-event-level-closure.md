# Terminal Path State Update Event-Level Closure Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Prevent placeholder `terminal_path_state_update` coverage from driving lifecycle decisions, then implement real event-level sampled closure from `sim.h` through TSV export and summarization.

**Architecture:** Add a summarizer-side guard that marks placeholder coverage as non-authoritative and forces `instrument_terminal_path_state_update_event_level_closure`. Then instrument the reuse-writeback aux hot path with a parent sampled flag and child mask so state-update sampled counters, child seconds, and child counts are recorded in `sim.h` and exported through replay/profile TSVs into lifecycle summaries.

**Tech Stack:** C++, Python, shell regression scripts, sampled profiler telemetry in `sim.h`

### Task 1: Guard placeholder coverage in lifecycle summarizer

**Files:**
- Modify: `scripts/check_summarize_sim_initial_host_merge_candidate_index_lifecycle.sh`
- Modify: `scripts/summarize_sim_initial_host_merge_candidate_index_lifecycle.py`

**Step 1: Write the failing test**

Extend the lifecycle shell regression with a `state_update_placeholder_coverage` case that expects:
- `terminal_path_state_update_coverage_source = placeholder`
- `terminal_path_state_update_timer_scope_status = missing_event_level_coverage`
- `recommended_next_action = instrument_terminal_path_state_update_event_level_closure`

**Step 2: Run test to verify it fails**

Run: `bash scripts/check_summarize_sim_initial_host_merge_candidate_index_lifecycle.sh`
Expected: FAIL because the new fields and guarded action do not exist yet.

**Step 3: Write minimal implementation**

Add summarizer fields for `terminal_path_state_update_coverage_source` and `terminal_path_state_update_timer_scope_status`, and force the guard before any branch-local child decision when coverage source is not `event_level_sampled`.

**Step 4: Run test to verify it passes**

Run: `bash scripts/check_summarize_sim_initial_host_merge_candidate_index_lifecycle.sh`
Expected: PASS

### Task 2: Require real state-update sampled closure in exported profile artifacts

**Files:**
- Modify: `scripts/check_run_sim_initial_host_merge_same_workload_materiality_profile.sh`
- Modify: `sim.h`
- Modify: `tests/sim_initial_host_merge_context_apply_profile.cpp`

**Step 1: Write the failing test**

Strengthen the profile run check so state-update sampled closure fields must be real, not placeholders:
- sampled event count present and greater than zero
- coverage source exported as `event_level_sampled`
- covered sampled count not greater than sampled count

**Step 2: Run test to verify it fails**

Run: `bash scripts/check_run_sim_initial_host_merge_same_workload_materiality_profile.sh`
Expected: FAIL because current state-update sampled closure fields are zero placeholders.

**Step 3: Write minimal implementation**

Instrument `sim.h` with:
- parent sampled flag for `terminal_path_state_update`
- child mask bits for `heap_build`, `heap_update`, `start_index_rebuild`, `trace_or_profile_bookkeeping`
- sampled / covered / unclassified / multi-child counters
- sampled child counts

Thread those counters through replay export and `tests/sim_initial_host_merge_context_apply_profile.cpp`, and emit `terminal_path_state_update_coverage_source = event_level_sampled` when real sampled counters are present.

**Step 4: Run test to verify it passes**

Run: `bash scripts/check_run_sim_initial_host_merge_same_workload_materiality_profile.sh`
Expected: PASS

### Task 3: Verify lifecycle + roll-up remain green

**Files:**
- Modify if needed: `scripts/summarize_sim_initial_host_merge_candidate_index_lifecycle.py`
- Modify if needed: `scripts/summarize_sim_initial_host_merge_profile_branch_rollup.py`

**Step 1: Run targeted regressions**

Run:
- `bash scripts/check_summarize_sim_initial_host_merge_candidate_index_lifecycle.sh`
- `bash scripts/check_summarize_sim_initial_host_merge_profile_branch_rollup.sh`

Expected: PASS

**Step 2: Refactor only if needed**

Keep naming and field wiring consistent, but avoid changing runtime behavior or broadening state-update semantics beyond the four planned children.

**Step 3: Final verification**

Run all three checks together:
- `bash scripts/check_summarize_sim_initial_host_merge_candidate_index_lifecycle.sh`
- `bash scripts/check_summarize_sim_initial_host_merge_profile_branch_rollup.sh`
- `bash scripts/check_run_sim_initial_host_merge_same_workload_materiality_profile.sh`

Expected: PASS

### Task 4: Record outcome

**Files:**
- Modify: `docs/plans/2026-04-23-terminal-path-state-update-event-level-closure.md`

**Step 1: Append verification notes**

Record which commands were run and whether `terminal_path_state_update` is now exporting real event-level sampled closure.

**Step 2: Commit**

Suggested:

```bash
git add docs/plans/2026-04-23-terminal-path-state-update-event-level-closure.md \
  scripts/check_summarize_sim_initial_host_merge_candidate_index_lifecycle.sh \
  scripts/check_run_sim_initial_host_merge_same_workload_materiality_profile.sh \
  scripts/summarize_sim_initial_host_merge_candidate_index_lifecycle.py \
  sim.h \
  tests/sim_initial_host_merge_context_apply_profile.cpp
git commit -m "feat: add state-update event-level sampled closure"
```
