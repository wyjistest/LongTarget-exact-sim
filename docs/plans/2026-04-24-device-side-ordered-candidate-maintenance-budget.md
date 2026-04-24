# Device-Side Ordered Candidate Maintenance Budget

## Status

Phase 3a can select `host_cpu_merge` as the stable SIM subcomponent. That does not reopen candidate-index leaf profiling and does not authorize a GPU/runtime implementation. Phase 3b is a profiler-only feasibility lane for device-side ordered candidate maintenance.

## Goal

Determine whether the host ordered candidate maintenance stage has enough ordered-but-segmentable work to justify an exact-safe shadow design. This phase treats the host CPU merge as a stage-level cost, not as a candidate-index leaf tree.

## Artifact Contract

`scripts/summarize_longtarget_sim_ordered_candidate_maintenance_budget.py` consumes `sim_pipeline_budget_rollup_decision.json` from Phase 3a. The roll-up must stably select:

```text
selected_subcomponent = host_cpu_merge
recommended_next_action = profile_device_side_ordered_candidate_maintenance
runtime_prototype_allowed = false
```

It emits:

1. `ordered_candidate_maintenance_budget_summary.json`
2. `ordered_candidate_maintenance_budget_decision.json`
3. `ordered_candidate_maintenance_budget_cases.tsv`
4. `ordered_candidate_maintenance_budget.md`

## Required Shape Fields

The first version expects these telemetry fields in each workload projection JSON:

```text
sim_ordered_maintenance_candidate_event_count
sim_ordered_maintenance_ordered_segment_count
sim_ordered_maintenance_parallel_segment_count
sim_ordered_maintenance_mean_segment_length
sim_ordered_maintenance_p90_segment_length
sim_ordered_maintenance_serial_dependency_share
sim_ordered_maintenance_parallelizable_event_share
sim_ordered_maintenance_estimated_d2h_bytes_avoided
sim_ordered_maintenance_estimated_host_rebuild_seconds_avoided
sim_ordered_maintenance_estimated_cpu_merge_seconds_avoidable
```

`projected_` prefixes are also accepted. Missing required fields keep the phase at `collect_ordered_candidate_maintenance_telemetry`.

## Decision Gate

```text
if required ordered-maintenance fields missing:
    recommended_next_action = collect_ordered_candidate_maintenance_telemetry

elif host_cpu_merge_share_of_sim < 0.30:
    recommended_next_action = stop_host_cpu_merge_work

elif serial_dependency_share is high and parallel_segment_count is low:
    recommended_next_action = stop_or_rethink_device_side_ordered_maintenance

elif parallelizable_event_share >= 0.50
     and estimated_cpu_merge_seconds_avoidable is material:
    recommended_next_action = design_device_side_ordered_candidate_maintenance_shadow

elif d2h_or_state_handoff bytes also material:
    recommended_next_action = profile_device_resident_state_handoff_with_ordered_maintenance

else:
    recommended_next_action = collect_more_ordered_maintenance_shape
```

`runtime_prototype_allowed` remains `false` for every outcome. A shadow design, if later reached, must preserve row-run summary order, candidate visibility, floor/running-min updates, and final output bytes.

## Non-Goals

Do not restart candidate-index leaf profiling, start-index splits, state-update bookkeeping splits, unordered key coalescing, victim-slot reorder, or a runtime GPU implementation from this phase.
