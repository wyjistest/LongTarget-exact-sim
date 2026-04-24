# Phase 3c: Device-Side Ordered Candidate Maintenance Shadow

## Status

Phase 3a has stably selected `host_cpu_merge` as the SIM pipeline subcomponent. Phase 3b has closed ordered-maintenance telemetry and currently reports `device_side_ordered_candidate_maintenance_feasibility=plausible` with `recommended_next_action=design_device_side_ordered_candidate_maintenance_shadow`.

This phase is a shadow/validation design only. It does not authorize a runtime replacement, GPU implementation connected to output, or any default-path behavior change.

## Entry Gate

Phase 3c is active only when the Phase 3b decision has:

```text
decision_status = ready
phase = device_side_ordered_candidate_maintenance_budget
telemetry_status = closed
device_side_ordered_candidate_maintenance_feasibility = plausible | strong
recommended_next_action = design_device_side_ordered_candidate_maintenance_shadow
runtime_prototype_allowed = false
```

Otherwise the shadow design summarizer remains inactive and returns `recommended_next_action=return_to_ordered_candidate_maintenance_budget`.

## Contracts

The shadow lane must preserve the exact host ordered-maintenance semantics:

```text
input_contract = row_run_summaries_ordered
ordering_contract = preserve_original_summary_order
shadow_result_contract = validation_telemetry_only
runtime_prototype_allowed = false
default_path_changes_allowed = false
```

The default host path remains authoritative. A future shadow implementation may compute additional candidate state and telemetry, but the shadow result must not participate in output, candidate visibility, handoff, or timing interpretation for the default path.

## Forbidden Transforms

Phase 3c explicitly forbids:

```text
unordered_key_summary
victim_slot_reorder
lazy_generation_index
floor_update_skip
```

These transforms can change floor/running-min visibility or replacement order. They are not valid shortcuts for an exact-safe shadow.

## Required Validation

The first shadow implementation should compare counters and digests instead of dumping full candidate state. Required counter comparisons:

```text
candidate_count
runningMin
runningMinSlot
full_set_miss_count
existing_candidate_hit_count
candidate_replacement_count
state_update_count
```

Required validation hashes:

```text
final_candidate_state_hash
candidate_slot_key_hash
candidate_slot_score_hash
candidate_slot_generation_hash
candidate_index_visibility_hash
replacement_sequence_hash
running_min_update_sequence_hash
running_min_slot_update_sequence_hash
floor_change_sequence_hash
safe_store_state_hash
candidate_state_handoff_hash
summary_ordinal_hash
observed_candidate_index_hash
```

Mismatch reporting must at least include:

```text
shadow_mismatch_count
first_mismatch_case_id
first_mismatch_summary_ordinal
first_mismatch_kind
first_mismatch_host_value
first_mismatch_shadow_value
```

## Opt-In Flags

A future implementation should use explicit shadow-only names:

```bash
LONGTARGET_SIM_DEVICE_ORDERED_MAINTENANCE_SHADOW=1
LONGTARGET_SIM_DEVICE_ORDERED_MAINTENANCE_SHADOW_VALIDATE=1
```

Do not use a shorter runtime-like flag such as `LONGTARGET_SIM_DEVICE_ORDERED_MAINTENANCE=1`; that name is too easy to misread as a default-path replacement.

## Required Shadow Telemetry

The design artifact requires a future implementation to expose:

```text
shadow_enabled
shadow_validate_enabled
shadow_case_count
shadow_summary_count
shadow_event_count
shadow_seconds
host_cpu_merge_seconds
shadow_vs_host_speed_ratio
shadow_mismatch_count
shadow_first_mismatch_kind
shadow_first_mismatch_summary_ordinal
shadow_final_candidate_state_hash
host_final_candidate_state_hash
shadow_replacement_sequence_hash
host_replacement_sequence_hash
shadow_running_min_sequence_hash
host_running_min_sequence_hash
shadow_d2h_bytes
shadow_device_state_bytes
shadow_host_state_bytes_avoided_estimate
```

Validation fields are higher priority than performance fields. Performance telemetry only becomes meaningful after exact digest validation passes.

## Promotion Gate

The shadow lane can only advance beyond design after all of these remain true:

```text
validation:
  shadow_mismatch_count == 0
  candidate_state_hash_exact_match
  replacement_sequence_hash_exact_match
  running_min_sequence_hash_exact_match
  running_min_slot_sequence_hash_exact_match

coverage:
  synthetic_smoke_pass
  corpus_validation_pass
  five_case_representative_pass
  heavy_and_sample_pass

performance_plausibility:
  shadow_cost_not_obviously_worse_than_host_merge
  avoidable_host_cpu_merge_seconds_remains_material

safety:
  default_path_unchanged
  output_bytes_unchanged
  telemetry_marks_shadow_only
```

If validation fails, the next action is exactness audit or shape telemetry refinement, not runtime replacement.

## Artifact

`scripts/summarize_longtarget_device_ordered_maintenance_shadow_design.py` consumes the Phase 3b `ordered_candidate_maintenance_budget_decision.json` and emits:

```text
device_ordered_maintenance_shadow_design.json
device_ordered_maintenance_shadow_design.md
```

When active, the design artifact reports:

```text
shadow_design_status = ready_for_opt_in_shadow_implementation
recommended_next_action = implement_opt_in_device_ordered_maintenance_shadow
runtime_prototype_allowed = false
default_path_changes_allowed = false
```
