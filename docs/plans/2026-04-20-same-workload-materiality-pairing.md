# Same-Workload Materiality Pairing Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Close the profiler-only artifact gap by wiring same-workload benchmark pairing into the host-merge profile summaries, while keeping `materiality_status=unknown` whenever the pairing is incomplete or mismatched.

**Architecture:** Reuse the existing profile aggregate TSV flow and add explicit pairing metadata instead of new runtime telemetry. The profile binary should be able to stamp each aggregate row with `workload_id` and `benchmark_source`; the Python summarizers should compute workload-level materiality only when benchmark metrics are present and correctly paired, and otherwise return `ready_but_materiality_unknown`. Add one small runner so the existing 5-case profile can be regenerated against a single workload benchmark log without hand-editing commands.

**Tech Stack:** C++ profile binary, Python TSV/JSON summarizers, shell regression checks.

### Task 1: Write the RED checks for pairing/materiality guards

**Files:**
- Modify: `scripts/check_summarize_sim_initial_host_merge_min_maintenance_profile.sh`
- Modify: `scripts/check_summarize_sim_initial_host_merge_candidate_index_lifecycle.sh`

**Step 1: Add pairing metadata to synthetic rows**

Extend the synthetic TSV writers with:
- `workload_id`
- `benchmark_source`

Use repeated `workload_id + benchmark_source` rows to model same-workload duplicate benchmark rows.

**Step 2: Add min-profile pairing cases**

Cover:
- complete same-workload pairing -> `decision_status=ready`
- duplicate same-workload benchmark rows -> `materiality_pairing_status=duplicate_grouped`
- missing benchmark metadata -> `ready_but_materiality_unknown`
- mismatched `workload_id/benchmark_source` -> `ready_but_materiality_unknown`
- zero/negative benchmark values -> `not_ready`

**Step 3: Add lifecycle pairing cases**

Cover:
- material candidate-index + complete pairing -> `ready`
- material candidate-index + duplicate_grouped -> `ready`
- missing pairing -> `ready_but_materiality_unknown`
- mismatched pairing -> `ready_but_materiality_unknown`
- residual unexplained still dominates -> `inspect_candidate_index_timer_scope`
- candidate-index not material -> `no_host_merge_runtime_work`

**Step 4: Run both checks to verify RED**

Run:
- `bash scripts/check_summarize_sim_initial_host_merge_min_maintenance_profile.sh`
- `bash scripts/check_summarize_sim_initial_host_merge_candidate_index_lifecycle.sh`

Expected: FAIL until the summarizers and profile aggregate rows understand pairing metadata.

### Task 2: Thread same-workload pairing metadata into aggregate TSV

**Files:**
- Modify: `tests/sim_initial_host_merge_context_apply_profile.cpp`

**Step 1: Add optional pairing arguments**

Support:
- `--workload-id ID`
- `--benchmark-stderr PATH` (already present)

**Step 2: Emit pairing metadata into aggregate TSV**

Add columns:
- `workload_id`
- `benchmark_source`

Rules:
- blank when no benchmark stderr is supplied
- use the exact provided `--workload-id`
- use the benchmark stderr path string as `benchmark_source`

### Task 3: Update the summarizers to enforce pairing

**Files:**
- Modify: `scripts/summarize_sim_initial_host_merge_min_maintenance_profile.py`
- Modify: `scripts/summarize_sim_initial_host_merge_candidate_index_lifecycle.py`

**Step 1: Validate benchmark values**

Treat zero/negative workload benchmark metrics as `not_ready`.

**Step 2: Compute explicit pairing status**

Emit:
- `materiality_pairing_status = complete | missing | mismatched | duplicate_grouped`

Definitions:
- `missing`: benchmark metrics or pairing metadata absent
- `mismatched`: same `workload_id` maps to conflicting benchmark sources or conflicting metrics
- `duplicate_grouped`: multiple case rows share the same `workload_id + benchmark_source` and the summarizer grouped them once
- `complete`: single-use pairing with all metrics present

**Step 3: Materiality stays unknown unless pairing is valid**

Only compute:
- `initial_cpu_merge_share_of_sim_seconds`
- `candidate_index_share_of_sim_seconds`
- `candidate_index_share_of_total_seconds`

when pairing status is `complete` or `duplicate_grouped`.

**Step 4: Emit timer-scope residual shares**

Lifecycle summary should also emit:
- `aux_other_share_of_sim_seconds`
- `candidate_index_unexplained_share_of_sim_seconds`

using existing split timings only, without adding new runtime telemetry.

### Task 4: Add a small same-workload runner

**Files:**
- Create: `scripts/run_sim_initial_host_merge_same_workload_materiality.sh`

**Step 1: Accept one workload benchmark stderr and one corpus root**

Inputs:
- corpus dir
- case list
- workload id
- benchmark stderr path
- output dir

**Step 2: Rebuild the 5-case aggregate rows**

Run `tests/sim_initial_host_merge_context_apply_profile` once per case with:
- same profile binary
- same corpus/workload identity
- same `--benchmark-stderr`
- same `--workload-id`

### Task 5: Verify and refresh the real artifact

**Files:**
- Review: `.tmp/min_maintenance_profile_2026-04-19_21-47-30/cases/*.aggregate.tsv`
- Review: `.tmp/sim_initial_host_merge_real_census_cuda_2026-04-16_16-47-25/coverage_weighted_16_real/full_run.stderr.log`

**Step 1: Run verification**

Run:
- `bash scripts/check_summarize_sim_initial_host_merge_min_maintenance_profile.sh`
- `bash scripts/check_summarize_sim_initial_host_merge_candidate_index_lifecycle.sh`
- `python3 -m py_compile scripts/summarize_sim_initial_host_merge_min_maintenance_profile.py scripts/summarize_sim_initial_host_merge_candidate_index_lifecycle.py`
- `make tests/sim_initial_host_merge_context_apply_profile`

**Step 2: Re-run the summaries**

Expected:
- with the current empty benchmark log, real status remains `ready_but_materiality_unknown`
- next action remains analysis-only:
  - `profile_candidate_index_lifecycle` for min profile
  - `inspect_candidate_index_timer_scope` for lifecycle
