# Terminal Path State Update Profile Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add profiler/export/summarizer/roll-up support for `terminal_path_state_update` so the branch can be profiled and classified without enabling runtime prototypes.

**Architecture:** Reuse the existing low-overhead sampled profiling pattern already used by `lookup_miss_candidate_set_full_probe` and `terminal_path_start_index_write`. The new branch-local state-update path will use the real reuse-writeback aux boundaries already present in telemetry: heap build, heap update, start-index rebuild, and aux bookkeeping.

**Tech Stack:** C++, Python, Bash regression scripts, existing sampled telemetry pipeline.

### Task 1: Lock the branch semantics in tests

**Files:**
- Modify: `scripts/check_summarize_sim_initial_host_merge_candidate_index_lifecycle.sh`
- Modify: `scripts/check_summarize_sim_initial_host_merge_profile_branch_rollup.sh`

**Step 1: Write the failing lifecycle regression**

Add synthetic lifecycle fixtures that inject `terminal_path_state_update` sampled fields and assert these decisions:
- `classify_terminal_path_state_update_bookkeeping`
- `profile_heap_update_path`
- `profile_heap_build_path`
- `profile_start_index_rebuild_path`
- `inspect_terminal_path_state_update_timer_scope`
- `mark_terminal_path_state_update_as_distributed_overhead`

**Step 2: Run the lifecycle regression to verify it fails**

Run: `bash scripts/check_summarize_sim_initial_host_merge_candidate_index_lifecycle.sh`

Expected: failure because the lifecycle summarizer does not yet consume state-update branch-local fields.

**Step 3: Write the failing roll-up regression**

Add roll-up fixtures covering:
- `next_candidate_branch=terminal_path_state_update` with no branch-local decision yet -> `profile_terminal_path_state_update`
- `next_candidate_branch=terminal_path_state_update` with lifecycle decision ready -> roll-up should surface that decision

**Step 4: Run the roll-up regression to verify it fails**

Run: `bash scripts/check_summarize_sim_initial_host_merge_profile_branch_rollup.sh`

Expected: failure because roll-up still treats state-update as a generic unmapped branch-local decision.

### Task 2: Export state-update sampled fields

**Files:**
- Modify: `sim.h`
- Modify: `tests/sim_initial_host_merge_context_apply_profile.cpp`
- Modify: `scripts/check_run_sim_initial_host_merge_same_workload_materiality_profile.sh`

**Step 1: Add sampled state-update telemetry fields**

Add/export fields for:
- parent / child-known / unexplained seconds
- heap build / heap update / start-index rebuild / trace-or-profile bookkeeping seconds
- sampled event coverage counts
- operation census counts tied to existing aux telemetry totals

**Step 2: Run the export check**

Run: `bash scripts/check_run_sim_initial_host_merge_same_workload_materiality_profile.sh`

Expected: pass with the new state-update columns present.

### Task 3: Teach the lifecycle summarizer the new branch

**Files:**
- Modify: `scripts/summarize_sim_initial_host_merge_candidate_index_lifecycle.py`

**Step 1: Parse the new state-update inputs**

Read optional sampled state-update seconds/count fields from TSV rows and expose them in per-case candidate metrics plus aggregate summary JSON.

**Step 2: Add the branch-local gate**

Implement the decision order:
1. closure / unexplained failure -> inspect timer scope
2. bookkeeping-dominant -> classify bookkeeping
3. heap-update dominant -> profile heap update
4. heap-build dominant -> profile heap build
5. start-index-rebuild dominant -> profile start-index rebuild
6. else -> mark distributed overhead

**Step 3: Re-run the lifecycle regression**

Run: `bash scripts/check_summarize_sim_initial_host_merge_candidate_index_lifecycle.sh`

Expected: pass.

### Task 4: Surface the branch-local decision in roll-up

**Files:**
- Modify: `scripts/summarize_sim_initial_host_merge_profile_branch_rollup.py`

**Step 1: Consume lifecycle state-update decisions**

If `terminal_path_state_update` is the selected frontier and lifecycle already has a branch-local action, surface it as:
- `next_candidate_branch_decision`
- `recommended_next_action`

If not, keep the generic top-level action:
- `profile_terminal_path_state_update`

**Step 2: Re-run the roll-up regression**

Run: `bash scripts/check_summarize_sim_initial_host_merge_profile_branch_rollup.sh`

Expected: pass.

### Task 5: Final verification

**Files:**
- Modify: none

**Step 1: Run the full relevant check set**

Run:
- `bash scripts/check_summarize_sim_initial_host_merge_candidate_index_lifecycle.sh`
- `bash scripts/check_summarize_sim_initial_host_merge_profile_branch_rollup.sh`
- `bash scripts/check_run_sim_initial_host_merge_same_workload_materiality_profile.sh`

**Step 2: Review outputs for invariants**

Confirm:
- `runtime_prototype_allowed = false`
- state-update branch only changes profiler/export/summarizer path
- no previously stopped frontier is reopened

### Risks and Notes

- `terminal_path_state_update` is semantically narrow: it is not generic state-field writes.
- Existing worktree is dirty; do not revert unrelated user edits.
- This task ends at “path ready”, not at “real 5-case evidence refreshed”.

### References

- `tests/sim_initial_host_merge_context_apply_profile.cpp`
- `sim.h`
- `scripts/summarize_sim_initial_host_merge_candidate_index_lifecycle.py`
- `scripts/summarize_sim_initial_host_merge_profile_branch_rollup.py`
