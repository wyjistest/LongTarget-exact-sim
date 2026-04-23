# Terminal Telemetry Overhead Classification Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Classify `terminal_path_telemetry_overhead` as profiler-only, benchmark-only, production bookkeeping, mixed, or unknown without changing runtime behavior.

**Architecture:** Extend the existing low-overhead profile campaign with narrow "no terminal telemetry" modes, then add a dedicated classification summarizer that compares with/without telemetry artifacts and emits a decision artifact. Keep the change profiler-only: candidate replacement, start-index writes, running-state updates, and replay correctness remain unchanged.

**Tech Stack:** C++, Bash, Python JSON/TSV/Markdown artifact generation

### Task 1: Lock classification behavior with a failing regression

**Files:**
- Modify: `scripts/check_summarize_sim_initial_host_merge_profile_mode_ab.sh`
- Create: `scripts/check_summarize_sim_initial_host_merge_terminal_telemetry_classification.sh`
- Test: `scripts/check_summarize_sim_initial_host_merge_terminal_telemetry_classification.sh`

**Step 1: Write the failing test**

Create a fixture with:
- sampled-with-telemetry artifact
- sampled-without-terminal-telemetry artifact
- optional count-only-without-terminal-telemetry artifact

Assert at minimum:
- `current_branch = terminal_path_telemetry_overhead`
- `runtime_prototype_allowed = false`
- `telemetry_branch_kind = profiler_only_overhead`
- `recommended_next_action = reduce_or_cold_path_profiler_telemetry`

**Step 2: Run test to verify it fails**

Run: `bash scripts/check_summarize_sim_initial_host_merge_terminal_telemetry_classification.sh`
Expected: FAIL because the classification summarizer does not exist yet.

### Task 2: Add no-terminal-telemetry profile modes

**Files:**
- Modify: `sim.h`
- Modify: `tests/sim_initial_host_merge_context_apply_profile.cpp`
- Modify: `scripts/run_sim_initial_host_merge_same_workload_materiality_profile.sh`

**Step 1: Extend mode enums and CLI parsing**

Add:
- `lexical_first_half_sampled_no_terminal_telemetry`
- optionally `lexical_first_half_count_only_no_terminal_telemetry`

**Step 2: Gate terminal telemetry narrowly**

Disable only terminal telemetry bookkeeping/timers/counters/export updates needed for classification.

Do not change:
- candidate replacement
- `SimCandidateStartIndex` writes
- running state
- replay correctness

**Step 3: Verify mode wiring**

Run the relevant wrapper/help/regression command and confirm the new mode names are accepted.

### Task 3: Implement classification summarizer

**Files:**
- Create: `scripts/summarize_sim_initial_host_merge_terminal_telemetry_classification.py`
- Modify: `scripts/check_summarize_sim_initial_host_merge_terminal_telemetry_classification.sh`

**Step 1: Load with/without telemetry artifacts**

Read sampled-with and sampled-without lifecycle summaries.

**Step 2: Compute deltas and classification**

Emit:
- `candidate_index_seconds_with_terminal_telemetry`
- `candidate_index_seconds_without_terminal_telemetry`
- `candidate_index_seconds_delta_without_terminal_telemetry`
- `terminal_parent_seconds_with_terminal_telemetry`
- `terminal_parent_seconds_without_terminal_telemetry`
- `terminal_parent_seconds_delta_without_terminal_telemetry`
- `terminal_path_telemetry_overhead_seconds_with`
- `terminal_path_telemetry_overhead_seconds_without`
- `telemetry_delta_explains_share`
- `terminal_delta_explains_share`
- `telemetry_branch_kind`
- `recommended_next_action`

**Step 3: Write decision artifacts**

Output:
- `terminal_telemetry_overhead_classification_cases.tsv`
- `terminal_telemetry_overhead_classification_summary.json`
- `terminal_telemetry_overhead_classification_decision.json`
- `terminal_telemetry_overhead_classification_summary.md`

### Task 4: Verify end-to-end

**Files:**
- Test: `scripts/check_summarize_sim_initial_host_merge_terminal_telemetry_classification.sh`
- Test: `scripts/check_run_sim_initial_host_merge_same_workload_materiality_profile.sh`

**Step 1: Run classification regression**

Run: `bash scripts/check_summarize_sim_initial_host_merge_terminal_telemetry_classification.sh`
Expected: PASS

**Step 2: Run mode wrapper regression**

Run: `bash scripts/check_run_sim_initial_host_merge_same_workload_materiality_profile.sh`
Expected: PASS with the new no-terminal-telemetry mode accepted.
