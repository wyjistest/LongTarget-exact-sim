# Production State Update Bookkeeping Profile Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extend the sampled candidate-index profiling pipeline so `profile_production_state_update_bookkeeping_path` can decompose `terminal_path_state_update_bookkeeping = production_state_bookkeeping` into source-stable production subpaths without enabling runtime prototypes.

**Architecture:** Reuse the existing `AuxOther*` / `AuxOtherResidual*` timing structure as the first stable production split instead of inventing speculative semantic timers. Export a new production-bookkeeping parent/child closure from the replay/profile binary, let lifecycle summarization derive dominance and actionability, then surface the concrete child decision through branch roll-up while keeping `runtime_prototype_allowed = false`.

**Tech Stack:** C++, Python 3, Bash, TSV/JSON summarizers, existing profiling regression scripts.

### Task 1: Lock regression expectations first

**Files:**
- Modify: `scripts/check_summarize_sim_initial_host_merge_candidate_index_lifecycle.sh`
- Modify: `scripts/check_summarize_sim_initial_host_merge_profile_branch_rollup.sh`

1. Add failing fixture coverage for production state-update bookkeeping fields and decisions.
2. Cover at least these actions: `profile_trace_replay_required_state_update_path`, `reduce_or_cold_path_benchmark_state_update_counters`, `mark_production_state_update_as_distributed_overhead`.
3. Run the targeted check script and confirm failure is due to missing production bookkeeping plumbing rather than fixture mistakes.

### Task 2: Export production bookkeeping split from the profile binary

**Files:**
- Modify: `sim.h`
- Modify: `tests/sim_initial_host_merge_context_apply_profile.cpp`

1. Add a production-bookkeeping parent scope derived from `AuxOtherSeconds`.
2. Export child seconds/counts for source-stable buckets already visible in code:
   - benchmark/accounting counters
   - trace/replay-required trace record/finalize
   - residual production bookkeeping
3. Add event-level sampled closure counters for the production-bookkeeping branch.
4. Keep the existing state-update bookkeeping mode semantics unchanged.

### Task 3: Teach lifecycle summarization the new branch

**Files:**
- Modify: `scripts/summarize_sim_initial_host_merge_candidate_index_lifecycle.py`

1. Parse the new TSV fields and derive production-bookkeeping closure, shares, dominant child, and unexplained share.
2. Gate branch-local decisions only when the parent classification is `production_state_bookkeeping`.
3. Emit a concrete next action while preserving `runtime_prototype_allowed = false`.

### Task 4: Propagate the new decision through roll-up

**Files:**
- Modify: `scripts/summarize_sim_initial_host_merge_profile_branch_rollup.py`

1. Recognize the new production state-update child actions as branch-local state-update decisions.
2. Surface the concrete action as the authoritative next step when `terminal_path_state_update` remains the frontier.

### Task 5: Verify

**Files:**
- Modify as needed based on failures from earlier tasks.

1. Run:
   - `bash scripts/check_summarize_sim_initial_host_merge_candidate_index_lifecycle.sh`
   - `bash scripts/check_summarize_sim_initial_host_merge_profile_branch_rollup.sh`
2. If those pass, run the broader state-update related checks if required by failures.
3. Do not run a fresh real 5-case campaign in this change unless the code path is fully ready and the user explicitly wants the artifact refresh in this turn.

### Risks And Notes

- The current `trace_or_profile_bookkeeping` bucket is broader than its name; the first refinement must follow source-stable code boundaries, not wishful semantics.
- `no_state_update_bookkeeping` explain-share remains a classification input only; it must not be reused as proof that a child bucket is removable.
- Any new branch-local action here is profiler-only guidance. No runtime prototype should be enabled.
