# Candidate-Index Leaf Profiling Stop Summary

## Status

Leaf-level candidate-index profiling is complete and stopped.

Top-level authoritative state is defined by `branch_rollup_decision.json`, not by any branch-local lifecycle/classification artifact:

```text
recommended_next_action = stop_leaf_level_candidate_index_profiling
leaf_level_candidate_index_profiling_status = stopped
active_frontier = null
stop_reason = no_single_stable_leaf_found_under_current_profiler
runtime_prototype_allowed = false
```

## Meaning

This stop result does not mean the candidate-index path is immaterial. The current interpretation is:

```text
candidate-index remains material,
but the current low-overhead sampled leaf profiler did not find
a single stable actionable runtime leaf.
```

The sampled frontier sequence now closes as:

- `gap_before_a00_span_0_alt_right` -> distributed overhead / no stable leaf
- `terminal_path_telemetry_overhead` -> profiler-only overhead / mitigated
- `terminal_path_start_index_write` -> distributed store overhead / exhausted
- `lookup_miss_candidate_set_full_probe` -> no single stable leaf
- `terminal_path_state_update` -> distributed production-state-update overhead / exhausted

## Phase Boundary

The profiling boundary is now:

```text
Phase 1: leaf-level candidate-index profiling
status: complete / stopped

Phase 2: structural profiling
goal: explain why candidate-index is material without assuming
      a single dominant leaf
```

If work continues, it should proceed as structural profiling rather than deeper leaf splitting. Natural next directions are:

- common memory/layout profiling
- branch-agnostic operation census roll-up
- coarser hardware or memory-behavior observation

The concrete Phase 2 execution handoff is captured in:

- `docs/plans/2026-04-23-candidate-index-structural-profiling.md`

That plan keeps the top-level authority at roll-up / phase level, keeps `runtime_prototype_allowed = false`, and adds an explicit structural stop rule so this line does not fall back into deeper leaf splitting.

## Artifact Reading Rule

Branch-local summaries remain useful, but they are not authoritative for the top-level next action:

- `candidate_index_lifecycle_decision.json` requires branch-rollup context
- `state_update_bookkeeping_classification_decision.json` requires branch-rollup context
- `branch_rollup_decision.json` is authoritative for stop/continue status

## CI

This branch now includes a minimal GitHub Actions workflow at `.github/workflows/ci.yml` that mirrors the local CPU verification path for this profiling work:

- build the main CPU target
- build the host-merge/profile helper binaries
- run targeted candidate-index runtime tests
- run the lifecycle/classification/roll-up regression checks
