# Phase 3d: Device-Side Ordered Candidate Maintenance Shadow Validation

## Status

Phase 3c has passed the design gate and may recommend:

```text
recommended_next_action = implement_opt_in_device_ordered_maintenance_shadow
runtime_prototype_allowed = false
default_path_changes_allowed = false
```

Phase 3d starts with validation contracts only. The first implementation step is a deterministic host digest and a default-disabled shadow telemetry schema. It does not implement a GPU kernel, does not replace host ordered maintenance, and does not connect any shadow result to output.

Phase 3d.1 adds an independent CPU shadow replay that is still validation-only. It copies the pre-merge host context only when the explicit shadow flag is enabled, replays the ordered row-run summaries into a shadow context, finalizes a shadow digest, and compares it against the authoritative host digest. The default path does not run the shadow replay.

## Opt-In Contract

Only explicit shadow flags may activate host digest recording for this lane:

```bash
LONGTARGET_SIM_DEVICE_ORDERED_MAINTENANCE_SHADOW=1
LONGTARGET_SIM_DEVICE_ORDERED_MAINTENANCE_SHADOW_VALIDATE=1
```

Do not introduce or use `LONGTARGET_SIM_DEVICE_ORDERED_MAINTENANCE=1`; that name reads like a runtime replacement rather than a shadow-only validation mode.

## Host Digest Contract

The authoritative host path remains the comparison target. The host digest records:

```text
candidate_count
running_min
running_min_slot
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

The digest is deterministic and compact. It is intended for host-vs-shadow validation and mismatch localization, not for performance attribution.

## Shadow Schema

Benchmark output exposes the disabled/default schema even when shadow is not enabled:

```text
benchmark.sim_device_ordered_maintenance_shadow_enabled
benchmark.sim_device_ordered_maintenance_shadow_validate_enabled
benchmark.sim_device_ordered_maintenance_shadow_status
benchmark.sim_device_ordered_maintenance_shadow_case_count
benchmark.sim_device_ordered_maintenance_shadow_summary_count
benchmark.sim_device_ordered_maintenance_shadow_event_count
benchmark.sim_device_ordered_maintenance_shadow_mismatch_count
benchmark.sim_device_ordered_maintenance_shadow_seconds
benchmark.sim_device_ordered_maintenance_shadow_host_cpu_merge_seconds
```

Host and shadow digest hash fields are also exposed. In the default disabled path, shadow fields are zero and `shadow_status=disabled`.

## Validation Summarizer

`scripts/summarize_longtarget_device_ordered_maintenance_shadow_validation.py` consumes one or more projection or benchmark telemetry JSON files containing the shadow fields and emits:

```text
device_ordered_maintenance_shadow_validation_cases.tsv
device_ordered_maintenance_shadow_validation_summary.json
device_ordered_maintenance_shadow_validation_decision.json
device_ordered_maintenance_shadow_validation.md
```

The decision gate is:

```text
disabled -> enable_shadow_validation
incomplete -> collect_shadow_validation_telemetry
mismatch -> debug_shadow_mismatch
insufficient_coverage -> expand_shadow_coverage
passed -> profile_shadow_cost
```

Every decision keeps:

```text
runtime_prototype_allowed = false
default_path_changes_allowed = false
```

## Validation Boundary

The next shadow implementation may only compare validation telemetry. It must preserve:

```text
input_contract = row_run_summaries_ordered
ordering_contract = preserve_original_summary_order
default_path_changes_allowed = false
```

Any future shadow mismatch must lead to `debug_shadow_mismatch` or an exactness audit. It must not promote a device/runtime path.
