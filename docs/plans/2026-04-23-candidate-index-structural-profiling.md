# Candidate-Index Structural Profiling Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Transition candidate-index investigation from leaf-level sampled profiling to structural profiling, so the next phase can explain why candidate-index remains material without assuming a single dominant leaf.

**Architecture:** Reuse the existing low-overhead sampled lifecycle and branch-rollup artifacts as Phase 2 inputs, but stop asking leaf-local dominance questions. First build a branch-agnostic operation roll-up, then add common memory/layout profiling that looks for shared write/read behavior across branches, and only then add coarse hardware observation if the first two workstreams still leave the structural signal ambiguous. Keep the top-level next action authoritative at the roll-up/phase level, and keep `runtime_prototype_allowed = false` throughout Phase 2.

**Tech Stack:** C++, Python 3, Bash, existing sampled profiler harness, TSV/JSON/Markdown summarizers, Linux hardware-counter tooling (`perf` or equivalent).

### Task 1: Freeze the Phase 2 contract and authoritative rules

**Files:**
- Modify: `docs/plans/2026-04-23-candidate-index-leaf-profiling-stop-summary.md`
- Modify: `README.md`
- Create: `scripts/summarize_sim_initial_host_merge_candidate_index_structural_phase.py`
- Create: `scripts/check_summarize_sim_initial_host_merge_candidate_index_structural_phase.sh`

1. Write a failing fixture for a new phase-level decision artifact that records:
   - `phase = structural_profiling`
   - `phase_status = active | stopped`
   - `current_focus = operation_rollup | common_memory_behavior | hardware_observation | null`
   - `runtime_prototype_allowed = false`
2. Run the new check and verify it fails because the structural-phase summarizer does not exist yet.
3. Implement the minimal structural-phase summarizer so it consumes the top-level roll-up decision and emits `candidate_index_structural_phase_decision.json`.
4. Re-run the new check until it passes.
5. Commit only the phase-contract scaffolding.

### Task 2: Add branch-agnostic operation roll-up

**Files:**
- Create: `scripts/summarize_sim_initial_host_merge_candidate_index_operation_rollup.py`
- Create: `scripts/check_summarize_sim_initial_host_merge_candidate_index_operation_rollup.sh`
- Modify: `scripts/summarize_sim_initial_host_merge_candidate_index_lifecycle.py`
- Modify: `scripts/summarize_sim_initial_host_merge_profile_branch_rollup.py`

1. Write failing fixtures that aggregate existing analyzed branches into the shared operation classes:
   - `scan`
   - `compare`
   - `branch_or_guard`
   - `store`
   - `clear`
   - `overwrite`
   - `state_update`
   - `trace_or_profile_bookkeeping`
   - `trace_replay_required_state`
   - `benchmark_counter`
2. Run the new check script and confirm the failure is “missing operation roll-up output”, not fixture drift.
3. Implement the roll-up so it emits:
   - `candidate_index_operation_rollup.tsv`
   - `candidate_index_operation_rollup.json`
   - `candidate_index_operation_rollup_decision.json`
   - `candidate_index_operation_rollup.md`
4. Gate the decision so:
   - shared `store + state_update` pressure recommends `profile_candidate_index_common_memory_behavior`
   - shared `compare + branch_or_guard` pressure recommends `profile_candidate_index_common_control_flow_behavior`
   - no stable operation class recommends `stop_candidate_index_structural_profiling`
5. Re-run the operation-rollup check and the existing lifecycle/branch-rollup checks until they all pass.
6. Commit the operation roll-up in isolation.

### Task 3: Export and summarize common memory/layout behavior

**Files:**
- Modify: `sim.h`
- Modify: `tests/sim_initial_host_merge_context_apply_profile.cpp`
- Create: `scripts/summarize_sim_initial_host_merge_candidate_index_common_memory_behavior.py`
- Create: `scripts/check_summarize_sim_initial_host_merge_candidate_index_common_memory_behavior.sh`

1. Write failing fixture coverage for these structural fields:
   - `candidate_index_bytes_read`
   - `candidate_index_bytes_written`
   - `candidate_index_unique_entry_count`
   - `candidate_index_unique_slot_count`
   - `candidate_index_unique_cacheline_count`
   - `candidate_index_same_cacheline_rewrite_count`
   - `candidate_index_insert_bytes`
   - `candidate_index_clear_bytes`
   - `candidate_index_overwrite_bytes`
   - `candidate_index_state_update_bytes`
   - `candidate_index_bookkeeping_bytes`
2. Run the new check and confirm failure is due to missing export/plumbing.
3. Add minimal low-overhead counters to the existing candidate-index hot path, biased toward byte/entry/cacheline accounting rather than new leaf timers.
4. Summarize the new data into:
   - `candidate_index_common_memory_behavior_cases.tsv`
   - `candidate_index_common_memory_behavior_summary.json`
   - `candidate_index_common_memory_behavior_decision.json`
   - `candidate_index_common_memory_behavior_summary.md`
5. Derive at least these decision metrics:
   - `candidate_index_write_amplification_share`
   - `candidate_index_same_cacheline_rewrite_share`
   - `candidate_index_hot_cold_mixed_touch_share`
   - `candidate_index_bytes_per_event`
   - `candidate_index_bytes_per_unique_entry`
6. Re-run the new common-memory check plus the existing CPU/profile checks.
7. Commit the memory/layout work separately from other workstreams.

### Task 4: Add coarse hardware observation only after Workstreams A and B are real

**Files:**
- Create: `scripts/run_sim_initial_host_merge_candidate_index_hardware_observation.sh`
- Create: `scripts/summarize_sim_initial_host_merge_candidate_index_hardware_observation.py`
- Create: `scripts/check_summarize_sim_initial_host_merge_candidate_index_hardware_observation.sh`
- Modify: `README.md`

1. Write a fixture that expects a 5-case median-based hardware observation summary, not a new leaf-level timer split.
2. Run the new hardware check and confirm failure is due to missing observation artifacts.
3. Implement a conservative harness that runs the authoritative low-overhead baseline 3 times per case and records medians for:
   - `cycles`
   - `instructions`
   - `branches`
   - `branch-misses`
   - `cache-references`
   - `cache-misses`
   - `L1-dcache-load-misses`
   - `LLC-load-misses`
   - `dTLB-load-misses`
4. Summarize the results into:
   - `candidate_index_hardware_observation.tsv`
   - `candidate_index_hardware_observation_summary.json`
   - `candidate_index_hardware_observation_decision.json`
   - `candidate_index_hardware_observation_summary.md`
5. Keep the decision coarse:
   - memory/cache dominant -> common memory/layout hypothesis
   - branch-miss dominant -> common branch/comparator hypothesis
   - no clear signal -> structural stop
6. Commit the hardware-observation harness separately from operation and memory changes.

### Task 5: Integrate the top-level stop rule

**Files:**
- Modify: `scripts/summarize_sim_initial_host_merge_profile_branch_rollup.py`
- Modify: `scripts/summarize_sim_initial_host_merge_candidate_index_structural_phase.py`
- Modify: `docs/plans/2026-04-23-candidate-index-leaf-profiling-stop-summary.md`

1. Add a failing fixture where operation roll-up, common memory behavior, and hardware observation all report “no stable structural signal”.
2. Verify the expected top-level result is:
   - `recommended_next_action = stop_candidate_index_structural_profiling`
   - `phase_status = stopped`
   - `runtime_prototype_allowed = false`
3. Implement the minimal stop-rule wiring so the structural phase can stop without reviving any leaf frontier.
4. Re-run the branch-rollup, structural-phase, and relevant new checks until they pass together.
5. Commit the stop-rule integration separately.

### Task 6: Full verification and artifact refresh

**Files:**
- Modify as needed based on verification failures.

1. Run the targeted summarizer checks:
   - `bash scripts/check_summarize_sim_initial_host_merge_candidate_index_operation_rollup.sh`
   - `bash scripts/check_summarize_sim_initial_host_merge_candidate_index_common_memory_behavior.sh`
   - `bash scripts/check_summarize_sim_initial_host_merge_candidate_index_structural_phase.sh`
2. If hardware observation is implemented in the same batch, also run:
   - `bash scripts/check_summarize_sim_initial_host_merge_candidate_index_hardware_observation.sh`
3. Re-run the existing candidate-index checks:
   - `bash scripts/check_summarize_sim_initial_host_merge_candidate_index_lifecycle.sh`
   - `bash scripts/check_summarize_sim_initial_host_merge_state_update_bookkeeping_classification.sh`
   - `bash scripts/check_summarize_sim_initial_host_merge_profile_branch_rollup.sh`
4. If new counters were added, run the matching CPU profile binary/test build before claiming success.
5. Refresh only the authoritative Phase 2 artifacts needed by the current task batch; do not start runtime prototypes.

### Risks And Notes

- Phase 2 must not reintroduce leaf-level dominance hunting under a different name; branch-local outputs stay contextual, not authoritative.
- `runtime_prototype_allowed` remains `false` until a stable structural signal exists across cases and workstreams.
- Workstream order matters: operation roll-up first, common memory/layout second, hardware observation last.
- If operation roll-up, common memory/layout, and hardware observation all fail to produce a stable signal, stop structural profiling rather than inventing a new profiler tree.
