# Branch Rollup Terminal Telemetry Classification Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Update the branch roll-up summarizer so it consumes the real terminal telemetry classification decision and advances the next action from `classify_terminal_path_telemetry_overhead` to `reduce_or_cold_path_profiler_telemetry`.

**Architecture:** Keep the roll-up frontier logic intact, but add an optional classification-decision input for `terminal_path_telemetry_overhead`. When present, this input overrides the branch's kind/actionability/recommended action and updates the top-level decision accordingly. Then refresh the real `.tmp/.../branch_rollup_stop_rule_refresh` artifact.

**Tech Stack:** Python, Bash regression, JSON/TSV/Markdown artifact generation

### Task 1: Lock the new roll-up behavior with a failing regression

**Files:**
- Modify: `scripts/check_summarize_sim_initial_host_merge_profile_branch_rollup.sh`
- Test: `scripts/check_summarize_sim_initial_host_merge_profile_branch_rollup.sh`

**Step 1: Extend the fixture**

Add a terminal telemetry classification decision fixture that says:
- `decision_status = ready`
- `current_branch = terminal_path_telemetry_overhead`
- `telemetry_branch_kind = profiler_only_overhead`
- `recommended_next_action = reduce_or_cold_path_profiler_telemetry`

**Step 2: Change expected roll-up outputs**

Assert:
- `next_candidate_branch = terminal_path_telemetry_overhead`
- `recommended_next_action = reduce_or_cold_path_profiler_telemetry`
- row `terminal_path_telemetry_overhead` has:
  - `branch_kind = profiler_only_overhead`
  - `branch_actionability = reduce_profiler_overhead_first`

**Step 3: Run test to verify it fails**

Run: `bash scripts/check_summarize_sim_initial_host_merge_profile_branch_rollup.sh`
Expected: FAIL before implementation.

### Task 2: Implement classification-aware roll-up

**Files:**
- Modify: `scripts/summarize_sim_initial_host_merge_profile_branch_rollup.py`

**Step 1: Add optional input**

Support:
- `--terminal-telemetry-classification-decision`

**Step 2: Override terminal telemetry row**

If the classification decision exists and is `ready` for `terminal_path_telemetry_overhead`, override:
- `branch_kind`
- `branch_actionability`
- row-level `recommended_action`

**Step 3: Update top-level decision**

If the classified top branch is `profiler_only_overhead`, emit:
- `recommended_next_action = reduce_or_cold_path_profiler_telemetry`
- `runtime_prototype_allowed = false`

### Task 3: Refresh the real artifact

**Files:**
- Refresh: `.tmp/profile_mode_ab_2026-04-22_09-53-10_alt_right_repart_shared_workload_rerun/branch_rollup_stop_rule_refresh/*`

**Step 1: Re-run roll-up summarizer**

Use:
- refreshed stop-rule A/B summary
- sampled lifecycle summary
- real terminal telemetry classification decision

**Step 2: Verify real decision**

Confirm:
- `current_exhausted_subtree = gap_before_a00_span_0_alt_right`
- `next_candidate_branch = terminal_path_telemetry_overhead`
- `recommended_next_action = reduce_or_cold_path_profiler_telemetry`

### Task 4: Verify

**Files:**
- Test: `scripts/check_summarize_sim_initial_host_merge_profile_branch_rollup.sh`

**Step 1: Run regression**

Run: `bash scripts/check_summarize_sim_initial_host_merge_profile_branch_rollup.sh`
Expected: PASS
