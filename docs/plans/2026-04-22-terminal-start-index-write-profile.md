# Terminal Start Index Write Profiling Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add profiler-only sampled split and operation census for `terminal_path_start_index_write` so the next frontier can distinguish locate/probe cost from entry-store cost without enabling runtime prototypes.

**Architecture:** Extend the existing `ensureSimCandidateIndexForRun(...)` fine-grained lookup trace with a new start-index-write parent interval, a minimal two-child split (`left`/`right`), and non-semantic operation counters. Surface those fields through replay/export, then teach the lifecycle summarizer and regression checks to consume the new data and emit the next profiling action.

**Tech Stack:** C++11 profiler instrumentation in `sim.h`, TSV export in `tests/sim_initial_host_merge_context_apply_profile.cpp`, Python lifecycle summarizer, shell regression checks.

### Task 1: Lock the summary contract with a failing regression

**Files:**
- Modify: `scripts/check_summarize_sim_initial_host_merge_candidate_index_lifecycle.sh`
- Test: `scripts/check_summarize_sim_initial_host_merge_candidate_index_lifecycle.sh`

**Step 1: Write the failing regression**

Add synthetic TSV coverage for:
- `terminal_path_start_index_write_parent_seconds`
- `terminal_path_start_index_write_left_seconds`
- `terminal_path_start_index_write_right_seconds`
- sampled closure fields
- operation census fields
- decision routing for probe-dominant vs store-dominant cases

**Step 2: Run the regression to verify it fails**

Run: `bash scripts/check_summarize_sim_initial_host_merge_candidate_index_lifecycle.sh`
Expected: FAIL because the summarizer does not yet expose the new start-index-write fields.

### Task 2: Add profiler trace and export wiring

**Files:**
- Modify: `sim.h`
- Modify: `tests/sim_initial_host_merge_context_apply_profile.cpp`
- Test: `scripts/check_run_sim_initial_host_merge_same_workload_materiality_profile.sh`

**Step 1: Write the failing export regression**

Extend the profile-mode check to require the new aggregate TSV columns and lifecycle summary fields for start-index-write split/census.

**Step 2: Run the regression to verify it fails**

Run: `bash scripts/check_run_sim_initial_host_merge_same_workload_materiality_profile.sh`
Expected: FAIL because the profile binary does not yet export the new fields.

**Step 3: Write the minimal implementation**

Add:
- start-index-write parent/left/right nanoseconds
- sampled coverage counters
- operation census counters (`insert`, `update_existing`, `clear`, `overwrite`, `idempotent`, `value_changed`, `probe_count`, `probe_steps_total`)

Propagate them through:
- `SimCandidateIndexLookupTrace`
- `SimInitialContextApplyTelemetry`
- `SimInitialHostMergeReplayResult`
- aggregate TSV header/body in the profile test binary

### Task 3: Teach the lifecycle summarizer the new split

**Files:**
- Modify: `scripts/summarize_sim_initial_host_merge_candidate_index_lifecycle.py`
- Test: `scripts/check_summarize_sim_initial_host_merge_candidate_index_lifecycle.sh`

**Step 1: Implement derived metrics**

Add start-index-write:
- parent/left/right/child_known/unexplained
- sampled closure status
- share metrics
- operation census shares
- dominant child label

**Step 2: Implement the next-action gate**

Route to:
- `profile_start_index_probe_or_locate_path`
- `profile_start_index_store_path`
- `profile_start_index_bookkeeping_path`
- `prototype_start_index_idempotent_write_skip_shadow`
- `inspect_start_index_write_timer_scope`

Keep `runtime_prototype_allowed = false`.

**Step 3: Run the summarizer regression**

Run: `bash scripts/check_summarize_sim_initial_host_merge_candidate_index_lifecycle.sh`
Expected: PASS.

### Task 4: Verify end-to-end profile export

**Files:**
- Test: `scripts/check_run_sim_initial_host_merge_same_workload_materiality_profile.sh`

**Step 1: Run the profile export regression**

Run: `bash scripts/check_run_sim_initial_host_merge_same_workload_materiality_profile.sh`
Expected: PASS.

**Step 2: Record remaining gap**

Do not rerun the real 5-case campaign in this task. The next manual step is a fresh low-overhead sampled rerun with terminal telemetry effectively off.

### Task 5: Final verification and handoff

**Files:**
- Reference: `sim.h`
- Reference: `tests/sim_initial_host_merge_context_apply_profile.cpp`
- Reference: `scripts/summarize_sim_initial_host_merge_candidate_index_lifecycle.py`
- Reference: `scripts/check_summarize_sim_initial_host_merge_candidate_index_lifecycle.sh`
- Reference: `scripts/check_run_sim_initial_host_merge_same_workload_materiality_profile.sh`

**Step 1: Re-run both checks**

Run:
- `bash scripts/check_summarize_sim_initial_host_merge_candidate_index_lifecycle.sh`
- `bash scripts/check_run_sim_initial_host_merge_same_workload_materiality_profile.sh`

Expected: both PASS.

**Step 2: Handoff**

Summarize the new authoritative profiler-only capability and explicitly note that the real 5-case artifact is still stale until rerun.

## Risks and Notes

- The new split must stay profiler-only and must not change candidate replacement or replay behavior.
- `terminal_path_start_index_write` currently maps to the reuse-writeback key-rebind/write section, not the earlier erase path.
- Sampled closure counters must reuse the existing low-overhead sampled semantics; avoid introducing always-on fine timers.

## References

- `sim.h:9080`
- `sim.h:9490`
- `tests/sim_initial_host_merge_context_apply_profile.cpp:1617`
- `scripts/summarize_sim_initial_host_merge_candidate_index_lifecycle.py:426`
- `scripts/check_summarize_sim_initial_host_merge_candidate_index_lifecycle.sh:1`
