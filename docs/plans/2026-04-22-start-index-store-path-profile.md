# Start Index Store Path Profiling Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Elevate `terminal_path_start_index_write`'s branch-local decision into branch roll-up and add profiler-only sampled store-path telemetry so the next frontier can distinguish insert, clear, overwrite, and write-amplification behavior without enabling runtime prototypes.

**Architecture:** Reuse the existing low-overhead sampled start-index-write split as the parent scope. Add a second profiler-only store-path split under the existing store child, export the new timers and census fields through the replay/profile TSV, then teach the lifecycle summarizer and roll-up summarizer to consume the new branch-local decision. Keep `runtime_prototype_allowed = false` throughout.

**Tech Stack:** C++11 profiler instrumentation in `sim.h`, TSV export in `tests/sim_initial_host_merge_context_apply_profile.cpp`, Python summarizers, shell regression checks.

### Task 1: Lock roll-up elevation with a failing regression

**Files:**
- Modify: `scripts/check_summarize_sim_initial_host_merge_profile_branch_rollup.sh`
- Modify: `scripts/summarize_sim_initial_host_merge_profile_branch_rollup.py`
- Test: `scripts/check_summarize_sim_initial_host_merge_profile_branch_rollup.sh`

**Step 1: Write the failing regression**

Make the synthetic lifecycle summary expose:
- `terminal_path_start_index_write_share_of_candidate_index`
- `terminal_path_start_index_write_sampled_count_closure_status = closed`
- `terminal_path_start_index_write_probe_or_locate_share = 0.0`
- `terminal_path_start_index_write_entry_store_share = 1.0`
- `recommended_next_action = profile_start_index_store_path`

Assert the roll-up decision becomes:
- `next_candidate_branch = terminal_path_start_index_write`
- `next_candidate_branch_decision = profile_start_index_store_path`
- `recommended_next_action = profile_start_index_store_path`

**Step 2: Run test to verify it fails**

Run: `bash scripts/check_summarize_sim_initial_host_merge_profile_branch_rollup.sh`
Expected: FAIL because the roll-up still returns `profile_next_stable_material_branch`.

### Task 2: Lock store-path lifecycle summary with failing regressions

**Files:**
- Modify: `scripts/check_summarize_sim_initial_host_merge_candidate_index_lifecycle.sh`
- Modify: `scripts/summarize_sim_initial_host_merge_candidate_index_lifecycle.py`
- Test: `scripts/check_summarize_sim_initial_host_merge_candidate_index_lifecycle.sh`

**Step 1: Write the failing regression**

Extend the synthetic TSV injection with store-path fields for:
- `terminal_path_start_index_store_parent_seconds`
- `terminal_path_start_index_store_insert_seconds`
- `terminal_path_start_index_store_clear_seconds`
- `terminal_path_start_index_store_overwrite_seconds`
- sampled closure counters
- store census counts/bytes/pairing counters

Assert lifecycle summary emits:
- store-path closure and share fields
- store dominant child / dominance status
- `recommended_next_action` routing for insert-dominant, clear-dominant, overwrite-dominant, and clear-overwrite-amplification cases

**Step 2: Run test to verify it fails**

Run: `bash scripts/check_summarize_sim_initial_host_merge_candidate_index_lifecycle.sh`
Expected: FAIL because the summarizer does not yet expose store-path telemetry.

### Task 3: Add profiler/export wiring for store-path telemetry

**Files:**
- Modify: `sim.h`
- Modify: `tests/sim_initial_host_merge_context_apply_profile.cpp`
- Modify: `scripts/check_run_sim_initial_host_merge_same_workload_materiality_profile.sh`
- Test: `scripts/check_run_sim_initial_host_merge_same_workload_materiality_profile.sh`

**Step 1: Write the failing export regression**

Require the aggregate TSV/profile summary to export:
- store-path seconds and sampled counters
- store census counts and byte counters
- same-entry / same-cacheline / paired-operation counters

**Step 2: Run test to verify it fails**

Run: `bash scripts/check_run_sim_initial_host_merge_same_workload_materiality_profile.sh`
Expected: FAIL because the profile binary does not export the new store-path fields.

**Step 3: Write minimal implementation**

Instrument the existing start-index-write store child with:
- insert / clear / overwrite sampled timers
- shared sampled parent coverage accounting
- store census counters for counts, bytes, unique targets, and paired-write heuristics

Propagate fields through:
- lookup trace
- context telemetry
- replay summary
- aggregate TSV header/body

### Task 4: Implement summarizer logic and roll-up elevation

**Files:**
- Modify: `scripts/summarize_sim_initial_host_merge_candidate_index_lifecycle.py`
- Modify: `scripts/summarize_sim_initial_host_merge_profile_branch_rollup.py`
- Test: `scripts/check_summarize_sim_initial_host_merge_candidate_index_lifecycle.sh`
- Test: `scripts/check_summarize_sim_initial_host_merge_profile_branch_rollup.sh`

**Step 1: Add derived store-path metrics**

Emit:
- parent / child-known / unexplained / coverage shares
- insert / clear / overwrite shares
- same-entry / same-cacheline / clear-then-overwrite pairing shares
- branch-local `recommended_next_action`

**Step 2: Elevate lifecycle decision into roll-up**

If the frontier branch is `terminal_path_start_index_write` and lifecycle decision is ready, carry:
- `next_candidate_branch_decision`
- `recommended_next_action = profile_start_index_store_path`

Keep generic fallback behavior for other branches.

**Step 3: Run targeted regressions**

Run:
- `bash scripts/check_summarize_sim_initial_host_merge_candidate_index_lifecycle.sh`
- `bash scripts/check_summarize_sim_initial_host_merge_profile_branch_rollup.sh`

Expected: PASS.

### Task 5: Verify end-to-end profile export

**Files:**
- Test: `scripts/check_run_sim_initial_host_merge_same_workload_materiality_profile.sh`

**Step 1: Run export verification**

Run: `bash scripts/check_run_sim_initial_host_merge_same_workload_materiality_profile.sh`
Expected: PASS.

**Step 2: Record remaining gap**

Do not run the real 5-case campaign in this task. The next manual step remains a fresh low-overhead sampled rerun for the store-path frontier.

## Risks and Notes

- All new instrumentation must stay profiler-only and must not affect candidate replacement, replay semantics, or runtime eligibility.
- Roll-up should only elevate lifecycle decisions when the lifecycle artifact is ready and matches the selected branch.
- Store-path pairing counters must be conservative; if exact same-entry/cacheline detection is not cheap enough, prefer a simpler exact counter set over speculative heuristics.

## References

- `scripts/summarize_sim_initial_host_merge_profile_branch_rollup.py`
- `scripts/summarize_sim_initial_host_merge_candidate_index_lifecycle.py`
- `scripts/check_summarize_sim_initial_host_merge_profile_branch_rollup.sh`
- `scripts/check_summarize_sim_initial_host_merge_candidate_index_lifecycle.sh`
- `sim.h`
- `tests/sim_initial_host_merge_context_apply_profile.cpp`
