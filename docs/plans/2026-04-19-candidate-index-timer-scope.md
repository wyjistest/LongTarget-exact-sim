# Candidate Index Timer Scope Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Close the host-merge materiality gate with workload-level benchmark metrics and refine the candidate-index lifecycle summary so `aux_other / timer_scope` becomes an explicit analysis result instead of an opaque bucket.

**Architecture:** Keep the work profiler-only and exact-safe. Reuse the existing split telemetry already emitted by `tests/sim_initial_host_merge_context_apply_profile.cpp`, add optional workload benchmark metrics (`sim_initial_scan_cpu_merge_seconds`, `sim_seconds`, `total_seconds`) to the aggregate TSV, and update the Python summarizers so materiality is derived from workload-level CPU-merge share instead of from isolated `context_apply` timing. On the lifecycle side, compute closure gaps across the existing lookup/miss/reuse/aux tiers and treat large residuals as a timer-scope blocker.

**Tech Stack:** C++ profile binary, Python TSV/JSON summarizers, shell regression checks.

### Task 1: Write the RED checks

**Files:**
- Modify: `scripts/check_summarize_sim_initial_host_merge_min_maintenance_profile.sh`
- Modify: `scripts/check_summarize_sim_initial_host_merge_candidate_index_lifecycle.sh`

**Step 1: Update min-maintenance check**

Use workload-level benchmark fields:
- `sim_initial_scan_cpu_merge_seconds_mean_seconds`
- `sim_initial_scan_seconds_mean_seconds`
- `sim_seconds_mean_seconds`
- `total_seconds_mean_seconds`

Expected:
- known materiality only when `sim_initial_scan_cpu_merge_seconds` and `sim_seconds` are present
- `candidate_index_not_material -> no_host_merge_runtime_work`
- `missing benchmark cpu merge -> ready_but_materiality_unknown`

**Step 2: Update lifecycle check**

Cover:
- `probe_dominant_material -> profile_start_index_probe_path`
- `reuse_writeback_dominant -> profile_lookup_miss_reuse_writeback`
- `erase_dominant_material -> prototype_eager_index_erase_handle_shadow`
- `residual_unexplained -> inspect_candidate_index_timer_scope`
- `candidate_index_not_material -> no_host_merge_runtime_work`
- `materiality_unknown -> ready_but_materiality_unknown`

**Step 3: Run both checks to verify RED**

Run:
- `bash scripts/check_summarize_sim_initial_host_merge_min_maintenance_profile.sh`
- `bash scripts/check_summarize_sim_initial_host_merge_candidate_index_lifecycle.sh`

Expected: FAIL until the summarizers and aggregate TSV gain the new fields/rules.

### Task 2: Thread workload benchmark metrics into aggregate TSV

**Files:**
- Modify: `tests/sim_initial_host_merge_context_apply_profile.cpp`

**Step 1: Add optional benchmark input**

Support an optional benchmark stderr path, parse:
- `benchmark.sim_initial_scan_seconds`
- `benchmark.sim_initial_scan_cpu_merge_seconds`
- `benchmark.sim_initial_scan_cpu_merge_subtotal_seconds`
- `benchmark.sim_seconds`
- `benchmark.total_seconds`

**Step 2: Emit the benchmark values into aggregate TSV**

Add columns:
- `sim_initial_scan_seconds_mean_seconds`
- `sim_initial_scan_cpu_merge_seconds_mean_seconds`
- `sim_initial_scan_cpu_merge_subtotal_seconds_mean_seconds`
- `sim_seconds_mean_seconds`
- `total_seconds_mean_seconds`

Leave fields blank when no benchmark stderr is supplied.

### Task 3: Update the min-maintenance summarizer

**Files:**
- Modify: `scripts/summarize_sim_initial_host_merge_min_maintenance_profile.py`

**Step 1: Resolve workload materiality from benchmark fields**

Compute:
- `initial_cpu_merge_share_of_sim_seconds = sim_initial_scan_cpu_merge_seconds / sim_seconds`
- `candidate_index_share_of_sim_seconds = candidate_index_share_of_initial_cpu_merge * initial_cpu_merge_share_of_sim_seconds`
- `candidate_index_share_of_total_seconds = candidate_index_share_of_initial_cpu_merge * sim_initial_scan_cpu_merge_seconds / total_seconds`

**Step 2: Keep `ready_but_materiality_unknown` honest**

If workload benchmark fields are missing, keep the decision `ready_but_materiality_unknown`.

### Task 4: Update the lifecycle summarizer

**Files:**
- Modify: `scripts/summarize_sim_initial_host_merge_candidate_index_lifecycle.py`

**Step 1: Consume the existing aux-other subfields**

Use:
- `context_apply_lookup_miss_reuse_writeback_aux_other_heap_update_accounting_mean_seconds`
- `context_apply_lookup_miss_reuse_writeback_aux_other_start_index_rebuild_accounting_mean_seconds`
- `context_apply_lookup_miss_reuse_writeback_aux_other_trace_finalize_mean_seconds`
- `context_apply_lookup_miss_reuse_writeback_aux_other_residual_mean_seconds`

**Step 2: Compute timer-scope closure gaps**

Compute:
- `candidate_index_scope_gap`
- `lookup_partition_gap`
- `lookup_miss_partition_gap`
- `reuse_writeback_partition_gap`
- `aux_bookkeeping_partition_gap`
- `aux_other_partition_gap`

**Step 3: Emit lifecycle-only next actions**

Allowed results:
- `inspect_candidate_index_timer_scope`
- `profile_start_index_probe_path`
- `profile_lookup_miss_reuse_writeback`
- `prototype_eager_index_erase_handle_shadow`
- `no_host_merge_runtime_work`

### Task 5: Verify and refresh the real artifact

**Files:**
- Review: `.tmp/min_maintenance_profile_2026-04-19_21-47-30/cases/*.aggregate.tsv`

**Step 1: Run checks and py_compile**

Run:
- `bash scripts/check_summarize_sim_initial_host_merge_min_maintenance_profile.sh`
- `bash scripts/check_summarize_sim_initial_host_merge_candidate_index_lifecycle.sh`
- `bash scripts/check_profile_sim_initial_host_merge_min_maintenance.sh`
- `python3 -m py_compile scripts/summarize_sim_initial_host_merge_min_maintenance_profile.py scripts/summarize_sim_initial_host_merge_candidate_index_lifecycle.py`

**Step 2: Re-run the 5-case lifecycle summary**

Expected:
- if no workload benchmark log is available, keep `ready_but_materiality_unknown`
- real next action should stay analysis-only, most likely `inspect_candidate_index_timer_scope`
