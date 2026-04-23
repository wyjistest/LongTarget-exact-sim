# Lookup Miss Full-Probe Profile Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add profiler-only branch-local profiling for `lookup_miss_candidate_set_full_probe` so lifecycle and roll-up can choose the next non-runtime profiling action from real 5-case evidence.

**Architecture:** Extend the existing sampled telemetry/export path in `sim.h` and `tests/sim_initial_host_merge_context_apply_profile.cpp` with full-probe closure and census fields, then teach `scripts/summarize_sim_initial_host_merge_candidate_index_lifecycle.py` to aggregate and classify the new branch-local evidence, and finally let `scripts/summarize_sim_initial_host_merge_profile_branch_rollup.py` surface that decision. Follow strict TDD: regression first, verify failing, then minimum code to pass.

**Tech Stack:** C++, Python 3, Bash regression scripts, TSV/JSON artifact summarizers

### Task 1: Add failing lifecycle regression for full-probe decision gate

**Files:**
- Modify: `scripts/check_summarize_sim_initial_host_merge_candidate_index_lifecycle.sh`
- Test: `scripts/check_summarize_sim_initial_host_merge_candidate_index_lifecycle.sh`

**Step 1: Write the failing test**

Add synthetic profile rows with explicit full-probe sampled closure/census fields that exercise:
- `profile_candidate_set_full_scan_path`
- `profile_candidate_set_probe_compare_path`
- `profile_lookup_miss_probe_branch_path`
- `prototype_redundant_full_probe_skip_shadow`
- `inspect_lookup_miss_candidate_set_full_probe_timer_scope`
- `no_single_stable_leaf_found_under_current_profiler`

**Step 2: Run test to verify it fails**

Run: `bash scripts/check_summarize_sim_initial_host_merge_candidate_index_lifecycle.sh`
Expected: FAIL because lifecycle summary does not yet emit the new full-probe fields or decision mapping.

**Step 3: Write minimal implementation**

Teach the lifecycle summarizer to parse synthetic full-probe inputs and emit branch-local closure / shares / decision.

**Step 4: Run test to verify it passes**

Run: `bash scripts/check_summarize_sim_initial_host_merge_candidate_index_lifecycle.sh`
Expected: PASS

### Task 2: Add failing roll-up regression for full-probe branch-local decision

**Files:**
- Modify: `scripts/check_summarize_sim_initial_host_merge_profile_branch_rollup.sh`
- Test: `scripts/check_summarize_sim_initial_host_merge_profile_branch_rollup.sh`

**Step 1: Write the failing test**

Add lifecycle summary fixtures where:
- `next_candidate_branch = lookup_miss_candidate_set_full_probe`
- `next_candidate_branch_decision = profile_candidate_set_full_scan_path`

Assert roll-up surfaces:
- `recommended_next_action = profile_candidate_set_full_scan_path`
- `runtime_prototype_allowed = false`

**Step 2: Run test to verify it fails**

Run: `bash scripts/check_summarize_sim_initial_host_merge_profile_branch_rollup.sh`
Expected: FAIL because roll-up only knows the generic `profile_lookup_miss_candidate_set_full_probe` action.

**Step 3: Write minimal implementation**

Teach roll-up to consume the new full-probe branch-local decision.

**Step 4: Run test to verify it passes**

Run: `bash scripts/check_summarize_sim_initial_host_merge_profile_branch_rollup.sh`
Expected: PASS

### Task 3: Extend profile export with full-probe sampled closure and census

**Files:**
- Modify: `sim.h`
- Modify: `tests/sim_initial_host_merge_context_apply_profile.cpp`
- Test: `scripts/check_run_sim_initial_host_merge_same_workload_materiality_profile.sh`

**Step 1: Write the failing test**

Add export assertions for new TSV headers / aggregates:
- parent / scan / compare / branch_or_guard / bookkeeping seconds
- sampled coverage counts
- probe count / slots scanned / full scan / early exit / found existing / confirmed absent / redundant reprobe

**Step 2: Run test to verify it fails**

Run: `bash scripts/check_run_sim_initial_host_merge_same_workload_materiality_profile.sh`
Expected: FAIL because the export does not yet contain the new full-probe columns.

**Step 3: Write minimal implementation**

Extend `SimCandidateIndexLookupTrace`, `SimInitialContextApplyTelemetry`, replay summaries, and TSV writers to export the new full-probe fields.

**Step 4: Run test to verify it passes**

Run: `bash scripts/check_run_sim_initial_host_merge_same_workload_materiality_profile.sh`
Expected: PASS

### Task 4: Aggregate full-probe metrics in lifecycle summary

**Files:**
- Modify: `scripts/summarize_sim_initial_host_merge_candidate_index_lifecycle.py`
- Test: `scripts/check_summarize_sim_initial_host_merge_candidate_index_lifecycle.sh`

**Step 1: Write minimal implementation**

Add:
- case-level parsing
- aggregate summation
- derived coverage / unexplained shares
- slots-scanned percentile or histogram handling
- decision gate for full-probe branch-local actions

**Step 2: Run targeted test**

Run: `bash scripts/check_summarize_sim_initial_host_merge_candidate_index_lifecycle.sh`
Expected: PASS

### Task 5: Surface full-probe branch-local decision in roll-up

**Files:**
- Modify: `scripts/summarize_sim_initial_host_merge_profile_branch_rollup.py`
- Test: `scripts/check_summarize_sim_initial_host_merge_profile_branch_rollup.sh`

**Step 1: Write minimal implementation**

Allow roll-up to prefer lifecycle-provided full-probe decisions over the generic `profile_lookup_miss_candidate_set_full_probe` placeholder.

**Step 2: Run targeted test**

Run: `bash scripts/check_summarize_sim_initial_host_merge_profile_branch_rollup.sh`
Expected: PASS

### Task 6: Verify end-to-end regressions

**Files:**
- Test: `scripts/check_run_sim_initial_host_merge_same_workload_materiality_profile.sh`
- Test: `scripts/check_summarize_sim_initial_host_merge_candidate_index_lifecycle.sh`
- Test: `scripts/check_summarize_sim_initial_host_merge_profile_branch_rollup.sh`

**Step 1: Run all regression commands**

```bash
bash scripts/check_run_sim_initial_host_merge_same_workload_materiality_profile.sh
bash scripts/check_summarize_sim_initial_host_merge_candidate_index_lifecycle.sh
bash scripts/check_summarize_sim_initial_host_merge_profile_branch_rollup.sh
```

**Step 2: Record residual risks**

If export passes but real 5-case artifacts are stale, explicitly note that fresh rerun is still required before any performance conclusion.

### Task 7: Real artifact follow-up (not part of this code patch)

**Files:**
- Reference: `.tmp/profile_start_index_store_2026-04-22_5case_low_overhead/...`

**Step 1: After code lands, rerun the low-overhead 5-case campaign**

Use `lexical_first_half_sampled` with terminal telemetry effective `off`.

**Step 2: Refresh summaries**

Recompute:
- `candidate_index_lifecycle_summary.json`
- `candidate_index_lifecycle_decision.json`
- `branch_rollup_decision.json`

**Step 3: Confirm next authoritative action**

Expected next action should come from the new full-probe branch-local decision, not from a generic placeholder.

### Risks And Notes

- Full-probe percentiles may be awkward to preserve from sampled traces; histogram fallback is acceptable if it keeps TDD simple.
- Runtime behavior must remain unchanged; all new logic is profiler/export/summarizer only.
- `runtime_prototype_allowed` must remain `false` in lifecycle and roll-up outputs.
