# Candidate Index Lifecycle Summary Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Turn the existing host-merge candidate-index split telemetry into a cost-based lifecycle decision artifact, while also making the min-maintenance summarizer explicit about missing total-sim materiality.

**Architecture:** Keep everything profiler-only and exact-safe. Reuse the split timing fields already emitted by `tests/sim_initial_host_merge_context_apply_profile.cpp`, then add a dedicated Python summarizer that classifies the dominant candidate-index lifecycle blocker (`probe`, `erase`, `start_index_rebuild`, or unresolved residual/timer scope). Separately, tighten the min-maintenance summarizer so missing `sim_seconds` does not silently pretend the materiality gate is known.

**Tech Stack:** Shell RED/GREEN checks, Python TSV/JSON summarizers, existing C++ profile binary output.

### Task 1: Tighten the min-maintenance summarizer status

**Files:**
- Modify: `scripts/check_summarize_sim_initial_host_merge_min_maintenance_profile.sh`
- Modify: `scripts/summarize_sim_initial_host_merge_min_maintenance_profile.py`

**Step 1: Write the failing check**

Add a synthetic case where `candidate_index` dominates CPU merge but no total-sim field is present.

Expected:
- `decision_status=ready_but_materiality_unknown`
- `materiality_status=unknown`
- `recommended_next_action=profile_candidate_index_lifecycle`

**Step 2: Run the check to verify RED**

Run: `bash scripts/check_summarize_sim_initial_host_merge_min_maintenance_profile.sh`
Expected: FAIL because the current summarizer still reports `ready`.

### Task 2: Add the failing candidate-index lifecycle check

**Files:**
- Create: `scripts/check_summarize_sim_initial_host_merge_candidate_index_lifecycle.sh`
- Create: `scripts/summarize_sim_initial_host_merge_candidate_index_lifecycle.py`

**Step 1: Write synthetic aggregate TSV fixtures**

Cover:
- `probe_dominant_material`
- `erase_dominant_material`
- `start_index_rebuild_dominant`
- `aux_other_dominant`
- `immaterial_host_merge`
- `missing_fields`

**Step 2: Run the new shell check to verify RED**

Run: `bash scripts/check_summarize_sim_initial_host_merge_candidate_index_lifecycle.sh`
Expected: FAIL because the summarizer script does not exist yet.

### Task 3: Implement the lifecycle summarizer

**Files:**
- Create: `scripts/summarize_sim_initial_host_merge_candidate_index_lifecycle.py`

**Step 1: Parse the existing aggregate TSV fields**

Require fields for:
- candidate-index total seconds
- lookup total/miss/open-slot/full-probe/eviction/reuse-writeback seconds
- erase/insert seconds
- reuse-writeback aux breakdown seconds

**Step 2: Emit fixed outputs**

Outputs:
- `candidate_index_lifecycle_cases.tsv`
- `candidate_index_lifecycle_summary.json`
- `candidate_index_lifecycle_decision.json`
- `candidate_index_lifecycle_summary.md`

**Step 3: Implement decision rules**

Rules:
1. Missing required fields -> `decision_status=not_ready`
2. Host merge immaterial versus total sim -> `no_host_merge_runtime_work`
3. Erase dominates candidate-index cost -> `prototype_eager_index_erase_handle_shadow`
4. Candidate-set-full probe dominates -> `prototype_lookup_path_optimization_shadow`
5. Start-index rebuild dominates -> `inspect_start_index_rebuild_policy`
6. Residual/aux-other dominates or split closure is suspicious -> `inspect_candidate_index_timer_scope`

**Step 4: Run the shell check to verify GREEN**

Run: `bash scripts/check_summarize_sim_initial_host_merge_candidate_index_lifecycle.sh`
Expected: PASS.

### Task 4: Re-run regression and produce a real heavy artifact

**Files:**
- Review: `.tmp/min_maintenance_profile_2026-04-19_21-47-30/cases/*.aggregate.tsv`

**Step 1: Re-run min-maintenance summary check**

Run: `bash scripts/check_summarize_sim_initial_host_merge_min_maintenance_profile.sh`
Expected: PASS.

**Step 2: Run the lifecycle summarizer on the current 5-case heavy profile**

Run:
- `python3 scripts/summarize_sim_initial_host_merge_candidate_index_lifecycle.py --aggregate-tsv ...`

Expected:
- lifecycle decision artifact generated
- recommendation stays analysis/profiler-only
- no runtime prototype is enabled automatically
