# State Update Bookkeeping Classification Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add `terminal_path_state_update` bookkeeping classification so sampled state-update dominance can be resolved as profiler-only, mixed, unknown, or production bookkeeping without enabling runtime prototypes.

**Architecture:** Extend the existing sampled profiling pipeline with a narrowly gated `lexical_first_half_sampled_no_state_update_bookkeeping` mode, propagate bookkeeping mode metadata through lifecycle summaries, classify with a with/without summarizer modeled after terminal telemetry classification, then let branch roll-up consume the classification artifact as the authoritative next action.

**Tech Stack:** C++, Python 3, Bash, TSV/JSON summarizers, existing test/check scripts.

### Task 1: Lock regression coverage before implementation

**Files:**
- Modify: `scripts/check_run_sim_initial_host_merge_same_workload_materiality_profile.sh`
- Modify: `scripts/check_summarize_sim_initial_host_merge_candidate_index_lifecycle.sh`
- Modify: `scripts/check_summarize_sim_initial_host_merge_profile_branch_rollup.sh`
- Create: `scripts/check_summarize_sim_initial_host_merge_state_update_bookkeeping_classification.sh`

1. Add regression expectations for the new profile mode and bookkeeping-mode metadata.
2. Add a dedicated classification check script with ready and not-ready fixtures.
3. Extend branch roll-up regression so `terminal_path_state_update` can consume a bookkeeping classification decision.
4. Run the new/updated checks and confirm they fail for the expected missing-plumbing reasons.

### Task 2: Finish profiling pipeline plumbing

**Files:**
- Modify: `scripts/run_sim_initial_host_merge_same_workload_materiality_profile.sh`
- Modify: `scripts/summarize_sim_initial_host_merge_candidate_index_lifecycle.py`

1. Teach the run script about `lexical_first_half_sampled_no_state_update_bookkeeping`.
2. Propagate `state_update_bookkeeping_mode_requested/effective` into case rows, aggregate, summary, and decision context.
3. Preserve `runtime_prototype_allowed = false`.

### Task 3: Add state-update bookkeeping classification summarizer

**Files:**
- Create: `scripts/summarize_sim_initial_host_merge_state_update_bookkeeping_classification.py`

1. Reuse terminal-telemetry classification structure.
2. Compare with/without bookkeeping summaries plus case-level behavior consistency.
3. Emit summary, decision, TSV, and markdown artifacts with explain-share metrics and recommended action.

### Task 4: Wire top-level roll-up to classification

**Files:**
- Modify: `scripts/summarize_sim_initial_host_merge_profile_branch_rollup.py`

1. Accept `--state-update-bookkeeping-classification-decision`.
2. When the selected frontier is `terminal_path_state_update` and its local action is bookkeeping classification, surface the classification decision as the authoritative next action.
3. Export the new authoritative source path.

### Task 5: Verify end to end

**Files:**
- Modify as needed based on failures from prior tasks.

1. Build `tests/sim_initial_host_merge_context_apply_profile`.
2. Run:
   - `bash scripts/check_run_sim_initial_host_merge_same_workload_materiality_profile.sh`
   - `bash scripts/check_summarize_sim_initial_host_merge_candidate_index_lifecycle.sh`
   - `bash scripts/check_summarize_sim_initial_host_merge_state_update_bookkeeping_classification.sh`
   - `bash scripts/check_summarize_sim_initial_host_merge_profile_branch_rollup.sh`
3. If those pass, optionally run the real 5-case with/without bookkeeping campaign to refresh authoritative artifacts.

### Risks And Notes

- The `no_state_update_bookkeeping` mode must only disable trace/profile bookkeeping, never production state or replay-critical semantics.
- Behavior mismatch between with/without summaries must stop classification and report semantic drift.
- `candidate_index_lifecycle_decision.json` is not the authoritative top-level action when roll-up has newer context; roll-up must record authoritative sources explicitly.
