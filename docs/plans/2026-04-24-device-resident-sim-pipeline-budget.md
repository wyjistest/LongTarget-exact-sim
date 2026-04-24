# Device-Resident SIM Pipeline Budget

## Status

Phase 3 top-level optimization budget selected `sim` in the current smoke artifact, but that only selects a direction. It does not authorize a GPU/runtime implementation. Phase 3a therefore starts with a SIM pipeline budget.

## Goal

Break `sim_seconds` into coarse, implementation-relevant subcomponents before choosing a runtime prototype direction:

1. `state_handoff`
2. `host_cpu_merge`
3. `gpu_compute`
4. `locate_traceback`

The budget should answer whether SIM time is dominated by D2H/state handoff, host ordered candidate maintenance, GPU kernel work, or locate/traceback continuation.

## Artifact Contract

`scripts/summarize_longtarget_sim_pipeline_budget.py` consumes:

1. `top_level_perf_budget_decision.json`
2. A SIM telemetry/projection JSON with aggregate fields or `cases[]`

It emits:

1. `sim_pipeline_budget.json`
2. `sim_pipeline_budget_decision.json`
3. `sim_pipeline_budget_cases.tsv`
4. `sim_pipeline_budget.md`

`scripts/refresh_longtarget_sim_pipeline_budget.sh` wraps this post-processing step and writes the same files under `sim_pipeline_budget/` in the requested output root. The wrapper consumes existing artifacts only; it does not run a workload and does not enable a runtime prototype.

If the top-level decision did not select `sim -> profile_device_resident_sim_pipeline`, the summarizer returns `decision_status=inactive` and `recommended_next_action=return_to_top_level_budget`.

## Decision Gate

The only active next actions are:

1. `collect_sim_substage_telemetry`
2. `profile_device_resident_state_handoff`
3. `profile_device_side_ordered_candidate_maintenance`
4. `profile_sim_initial_scan_kernel`
5. `profile_locate_traceback_pipeline`
6. `stop_sim_pipeline_work`

`runtime_prototype_allowed` remains `false`. A selected subcomponent means “profile this subpath next,” not “implement the optimization.”

## Field Mapping

`state_handoff` aggregates D2H/state rebuild/handoff fields such as:

```text
sim_initial_scan_d2h_seconds
candidate_state_handoff_seconds
host_rebuild_seconds
sim_initial_candidate_state_rebuild_seconds
sim_safe_store_handoff_seconds
```

For existing benchmark logs, `scripts/project_whole_genome_runtime.py` normalizes the current runtime field names into those Phase 3a names: `sim_initial_run_summaries_total -> sim_initial_summary_count`, `sim_initial_store_bytes_d2h -> sim_initial_candidate_state_bytes_d2h`, `sim_initial_store_rebuild_seconds -> sim_initial_host_rebuild_seconds`, and `sim_initial_store_upload_seconds -> sim_initial_state_handoff_seconds`.

`host_cpu_merge` uses `sim_initial_scan_cpu_merge_seconds`. `gpu_compute` uses `sim_initial_scan_gpu_seconds` or `gpu_kernel_seconds`. `locate_traceback` aggregates locate, traceback, and output materialization seconds.

Missing fields are reported as `insufficient_sim_substage_telemetry` with `recommended_next_action=collect_sim_substage_telemetry`, not as evidence that the SIM pipeline lacks a stable subcomponent. If substage fields are present but no subcomponent clears the dominance threshold, the decision is `stop_sim_pipeline_work`.
