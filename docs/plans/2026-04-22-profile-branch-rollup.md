# Profile Branch Rollup Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a lightweight branch roll-up summary that backtracks from a stopped profiling subtree and selects the next material branch without rerunning the profiler.

**Architecture:** Read the refreshed profile-mode A/B summary together with the sampled candidate-index lifecycle summary. Derive a small frontier table of stopped subtree rows plus known material lifecycle branches, then emit a decision artifact that either selects the next branch or reports that no stable material branch remains.

**Tech Stack:** Python, JSON/TSV/Markdown artifact generation, Bash regression

### Task 1: Lock roll-up behavior with a failing regression

**Files:**
- Create: `scripts/check_summarize_sim_initial_host_merge_profile_branch_rollup.sh`
- Test: `scripts/check_summarize_sim_initial_host_merge_profile_branch_rollup.sh`

**Step 1: Write the failing test**

Create a temp fixture with:
- a stopped `gap_before_a00_span_0_alt_right` subtree
- candidate lifecycle branch shares where `terminal_path_telemetry_overhead` is the largest eligible next branch

Assert:
- `current_exhausted_subtree = gap_before_a00_span_0_alt_right`
- `next_candidate_branch = terminal_path_telemetry_overhead`
- `recommended_next_action = profile_next_stable_material_branch`

**Step 2: Run test to verify it fails**

Run: `bash scripts/check_summarize_sim_initial_host_merge_profile_branch_rollup.sh`
Expected: FAIL because the roll-up script does not exist yet.

### Task 2: Implement the minimal roll-up summarizer

**Files:**
- Create: `scripts/summarize_sim_initial_host_merge_profile_branch_rollup.py`
- Test: `scripts/check_summarize_sim_initial_host_merge_profile_branch_rollup.sh`

**Step 1: Load summary inputs**

Read:
- profile-mode A/B summary JSON
- sampled candidate-index lifecycle summary JSON

**Step 2: Build rows**

Emit a small non-overlapping frontier that includes:
- stopped subtree `gap_before_a00_span_0_alt_right`
- sibling `gap_before_a00_span_0_alt_left`
- explicit lifecycle branches:
  - `terminal_path_candidate_slot_write`
  - `terminal_path_start_index_write`
  - `terminal_path_state_update`
  - `terminal_path_telemetry_overhead`
  - `lookup_miss_candidate_set_full_probe`

**Step 3: Select next branch**

Mark a row eligible only if:
- `share_of_total_seconds >= 0.03`
- closure is closed
- overhead is ok
- subtree is not exhausted

Pick the eligible row with the largest `share_of_total_seconds`.

### Task 3: Refresh artifacts and annotate authoritative stop summary

**Files:**
- Modify: `.tmp/profile_mode_ab_2026-04-22_09-53-10_alt_right_repart_shared_workload_rerun/ab_summary_stop_rule_refresh/profile_mode_ab_summary.md`
- Create: `.tmp/profile_mode_ab_2026-04-22_09-53-10_alt_right_repart_shared_workload_rerun/branch_rollup_stop_rule_refresh/*`

**Step 1: Regenerate branch roll-up**

Run the roll-up summarizer on the refreshed stop artifact and sampled lifecycle summary.

**Step 2: Mark authoritative summary**

Prepend the refreshed stop summary markdown with:
- `Authoritative artifact: ab_summary_stop_rule_refresh`
- `Supersedes: ab_summary`

### Task 4: Verify

**Files:**
- Test: `scripts/check_summarize_sim_initial_host_merge_profile_branch_rollup.sh`

**Step 1: Run the new regression**

Run: `bash scripts/check_summarize_sim_initial_host_merge_profile_branch_rollup.sh`
Expected: PASS
