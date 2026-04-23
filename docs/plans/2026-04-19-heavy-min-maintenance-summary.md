# Heavy Min Maintenance Summary Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Export the new host-merge min/index profiler telemetry into profile TSV artifacts and summarize 5-case heavy evidence into a cost-based decision artifact without changing runtime behavior.

**Architecture:** Keep the profiler runtime exact-safe and analysis-only. Extend `sim_initial_host_merge_context_apply_profile` so its single-run and aggregate TSVs include the new full-set-miss, refresh-min, and candidate-index lifecycle telemetry. Add a Python summarizer that reads one or more aggregate TSVs, computes case-level and campaign-level cost shares, and emits a decision artifact that chooses between `prototype_stable_min_maintenance`, `profile_candidate_index_lifecycle`, `prototype_eager_index_erase_handle`, `return_to_initial_run_summary_kernel`, and `no_host_merge_runtime_work`.

**Tech Stack:** C++ profile binary, Python TSV/JSON summarizer, shell regression checks.

### Task 1: Add the failing decision check for min-maintenance profile summaries

**Files:**
- Create: `scripts/check_summarize_sim_initial_host_merge_min_maintenance_profile.sh`
- Create: `docs/plans/2026-04-19-heavy-min-maintenance-summary.md`

**Step 1: Write synthetic aggregate TSV fixtures inside the shell check**

Cover:
- `refresh_min_dominant`
- `candidate_index_dominant`
- `erase_dominant`
- `both_low`
- `cpu_merge_not_material`
- `missing_fields`

**Step 2: Run the new shell check to verify RED**

Run: `bash scripts/check_summarize_sim_initial_host_merge_min_maintenance_profile.sh`
Expected: FAIL because the summarizer script does not exist yet.

### Task 2: Export new profiler telemetry from the context-apply profile binary

**Files:**
- Modify: `tests/sim_initial_host_merge_context_apply_profile.cpp`
- Review: `sim.h`
- Review: `Makefile`

**Step 1: Add new per-case TSV columns**

Emit replay fields for:
- `context_apply_full_set_miss_seconds`
- `context_apply_refresh_min_seconds`
- `context_apply_candidate_index_seconds`
- `context_apply_candidate_index_erase_seconds`
- `context_apply_candidate_index_insert_seconds`
- `context_apply_full_set_miss_count`
- `context_apply_floor_changed_count`
- `context_apply_floor_changed_share`
- `context_apply_running_min_slot_changed_count`
- `context_apply_running_min_slot_changed_share`
- `context_apply_victim_was_running_min_count`
- `context_apply_victim_was_running_min_share`
- `context_apply_refresh_min_calls`
- `context_apply_refresh_min_slots_scanned`
- `context_apply_refresh_min_slots_scanned_per_call`
- `context_apply_candidate_index_lookup_count`
- `context_apply_candidate_index_hit_count`
- `context_apply_candidate_index_miss_count`
- `context_apply_candidate_index_erase_count`
- `context_apply_candidate_index_insert_count`

**Step 2: Add aggregate TSV mean/p50/p95 columns**

Emit aggregate timing summaries for:
- `context_apply_full_set_miss`
- `context_apply_refresh_min`
- `context_apply_candidate_index`
- `context_apply_candidate_index_erase`
- `context_apply_candidate_index_insert`

Keep aggregate counts/shares aligned with the replay result.

**Step 3: Compile the profile binary**

Run: `make tests/sim_initial_host_merge_context_apply_profile`
Expected: PASS.

### Task 3: Implement the cost-based profile summarizer

**Files:**
- Create: `scripts/summarize_sim_initial_host_merge_min_maintenance_profile.py`
- Modify: `scripts/check_summarize_sim_initial_host_merge_min_maintenance_profile.sh`

**Step 1: Load one or more aggregate TSV inputs**

Support:
- repeated `--aggregate-tsv`
- optional repeated `--case-id`
- optional thresholds:
  - `--prototype-share-threshold`
  - `--erase-dominant-share-threshold`
  - `--host-merge-materiality-threshold`

**Step 2: Emit case TSV and summary JSON**

Outputs:
- `min_maintenance_profile_cases.tsv`
- `min_maintenance_profile_summary.json`
- `min_maintenance_profile_decision.json`
- `min_maintenance_profile_summary.md`

**Step 3: Implement decision rules**

Rules:
1. If required fields are missing: `decision_status=not_ready`
2. If host merge is not material versus total sim time: `no_host_merge_runtime_work`
3. If both refresh-min and candidate-index shares are high: `prototype_stable_min_maintenance`
4. If refresh-min share is high: `prototype_stable_min_maintenance`
5. If candidate-index share is high and erase share is high: `prototype_eager_index_erase_handle`
6. If candidate-index share is high: `profile_candidate_index_lifecycle`
7. Otherwise: `return_to_initial_run_summary_kernel`

**Step 4: Run the shell check to verify GREEN**

Run: `bash scripts/check_summarize_sim_initial_host_merge_min_maintenance_profile.sh`
Expected: PASS.

### Task 4: Verify end-to-end profile export and summarizer integration

**Files:**
- Modify: `scripts/check_profile_sim_initial_host_merge_min_maintenance.sh` (only if needed)
- Review: `.tmp/context_apply_profile_all.tsv`
- Review: `.tmp/sim_initial_host_merge_real_census_cuda_2026-04-16_16-47-25/corpus*`

**Step 1: Re-run existing profiler regression**

Run: `bash scripts/check_profile_sim_initial_host_merge_min_maintenance.sh`
Expected: PASS.

**Step 2: Build the profile binary explicitly**

Run: `make tests/sim_initial_host_merge_context_apply_profile`
Expected: PASS.

**Step 3: If a 5-case heavy corpus is available, generate a real profile artifact**

Run:
- `tests/sim_initial_host_merge_context_apply_profile ... --aggregate-tsv ...`
- `python3 scripts/summarize_sim_initial_host_merge_min_maintenance_profile.py ...`

Expected:
- decision artifact generated
- no runtime prototype enabled automatically
- next action chosen only from profiled cost shares
