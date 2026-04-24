# Top-Level Optimization Budget Reset

## Status

Phase 1 leaf-level candidate-index profiling is complete and stopped. Phase 2 candidate-index structural profiling is also stopped because it did not produce a stable structural signal. Candidate-index remains material, but it is no longer the active optimization frontier under the current profiling framework.

## Goal

Reset optimization selection to a top-level budget. The next target should be chosen by share of end-to-end time and Amdahl upper bound, not by candidate-index local curiosity.

## Artifact Contract

`scripts/summarize_longtarget_top_level_perf_budget.py` consumes either:

1. An explicit budget JSON with `total_seconds` and `components`.
2. A `scripts/project_whole_genome_runtime.py --json` report with `projected_*_seconds` fields.

It emits:

1. `top_level_perf_budget.json`
2. `top_level_perf_budget_decision.json`
3. `top_level_perf_budget.md`

Each component row includes:

1. `component`
2. `seconds`
3. `share_of_total`
4. `max_speedup_if_removed`
5. `status`
6. `recommended_action`

## Candidate-Index Policy

When the branch roll-up decision says candidate-index profiling has stopped, the top-level budget must mark candidate-index as contextual evidence only:

```json
{
  "component": "candidate_index",
  "status": "known_material_but_no_actionable_leaf",
  "candidate_index_policy": "do_not_continue_leaf_split",
  "recommended_action": "stop_candidate_index_work",
  "eligible_for_selection": false
}
```

This prevents the budget reset from reopening candidate-index leaf split or structural roll-up work.

## Allowed Next Actions

The top-level decision is intentionally narrow:

1. `profile_calc_score_path`
2. `profile_device_resident_sim_pipeline`
3. `profile_d2h_handoff_path`
4. `profile_safe_store_or_locate_path`
5. `stop_candidate_index_work`

No `split_candidate_index_leaf_*` action is valid in this phase.

## Stop Rule

If candidate-index is the only material component and the candidate-index branch is stopped, the budget may recommend `stop_candidate_index_work`. Otherwise it should select the largest eligible non-candidate component that crosses the material share threshold.

Runtime prototypes remain disabled until a top-level budget target is selected and then profiled under that target's own evidence gate.
