#!/usr/bin/env python3
import argparse
import json
from pathlib import Path


PHASE = "device_side_ordered_candidate_maintenance_shadow_design"

ALLOWED_NEXT_ACTIONS = [
    "implement_opt_in_device_ordered_maintenance_shadow",
    "return_to_ordered_candidate_maintenance_budget",
]

FORBIDDEN_TRANSFORMS = [
    "unordered_key_summary",
    "victim_slot_reorder",
    "lazy_generation_index",
    "floor_update_skip",
]

REQUIRED_VALIDATION_HASHES = [
    "final_candidate_state_hash",
    "candidate_slot_key_hash",
    "candidate_slot_score_hash",
    "candidate_slot_generation_hash",
    "candidate_index_visibility_hash",
    "replacement_sequence_hash",
    "running_min_update_sequence_hash",
    "running_min_slot_update_sequence_hash",
    "floor_change_sequence_hash",
    "safe_store_state_hash",
    "candidate_state_handoff_hash",
    "summary_ordinal_hash",
    "observed_candidate_index_hash",
]

REQUIRED_COUNTER_COMPARISONS = [
    "candidate_count",
    "runningMin",
    "runningMinSlot",
    "full_set_miss_count",
    "existing_candidate_hit_count",
    "candidate_replacement_count",
    "state_update_count",
]

REQUIRED_MISMATCH_FIELDS = [
    "shadow_mismatch_count",
    "first_mismatch_case_id",
    "first_mismatch_summary_ordinal",
    "first_mismatch_kind",
    "first_mismatch_host_value",
    "first_mismatch_shadow_value",
]

REQUIRED_SHADOW_TELEMETRY = [
    "shadow_enabled",
    "shadow_validate_enabled",
    "shadow_case_count",
    "shadow_summary_count",
    "shadow_event_count",
    "shadow_seconds",
    "host_cpu_merge_seconds",
    "shadow_vs_host_speed_ratio",
    "shadow_mismatch_count",
    "shadow_first_mismatch_kind",
    "shadow_first_mismatch_summary_ordinal",
    "shadow_final_candidate_state_hash",
    "host_final_candidate_state_hash",
    "shadow_replacement_sequence_hash",
    "host_replacement_sequence_hash",
    "shadow_running_min_sequence_hash",
    "host_running_min_sequence_hash",
    "shadow_d2h_bytes",
    "shadow_device_state_bytes",
    "shadow_host_state_bytes_avoided_estimate",
]

PROMOTION_GATES = {
    "validation": [
        "shadow_mismatch_count == 0",
        "candidate_state_hash_exact_match",
        "replacement_sequence_hash_exact_match",
        "running_min_sequence_hash_exact_match",
        "running_min_slot_sequence_hash_exact_match",
    ],
    "coverage": [
        "synthetic_smoke_pass",
        "corpus_validation_pass",
        "five_case_representative_pass",
        "heavy_and_sample_pass",
    ],
    "performance_plausibility": [
        "shadow_cost_not_obviously_worse_than_host_merge",
        "avoidable_host_cpu_merge_seconds_remains_material",
    ],
    "safety": [
        "default_path_unchanged",
        "output_bytes_unchanged",
        "telemetry_marks_shadow_only",
    ],
}

SCOPE_PLAN = [
    {
        "scope": "synthetic_corpus_validation",
        "goal": "validate ordering and digest comparison on small known row-run summaries",
    },
    {
        "scope": "real_representative_digest_validation",
        "goal": "compare host and shadow digests on host_cpu_merge-dominant representative cases",
    },
    {
        "scope": "large_workload_shadow_telemetry",
        "goal": "measure shadow-only cost and bytes after validation passes",
    },
]


def parse_args():
    parser = argparse.ArgumentParser(
        description="Emit Phase 3c device ordered-maintenance shadow design artifacts."
    )
    parser.add_argument(
        "--ordered-maintenance-budget-decision",
        required=True,
        help="ordered_candidate_maintenance_budget_decision.json from Phase 3b.",
    )
    parser.add_argument("--output-dir", required=True, help="Output directory.")
    return parser.parse_args()


def read_json(path):
    source = Path(path)
    with source.open("r", encoding="utf-8") as handle:
        return json.load(handle), source


def phase3b_ready(decision):
    return (
        decision.get("decision_status") == "ready"
        and decision.get("phase") == "device_side_ordered_candidate_maintenance_budget"
        and decision.get("telemetry_status") == "closed"
        and decision.get("device_side_ordered_candidate_maintenance_feasibility")
        in {"plausible", "strong"}
        and decision.get("recommended_next_action")
        == "design_device_side_ordered_candidate_maintenance_shadow"
        and decision.get("runtime_prototype_allowed") is False
    )


def base_design(source_path, phase3b_decision):
    return {
        "phase": PHASE,
        "allowed_next_actions": ALLOWED_NEXT_ACTIONS,
        "runtime_prototype_allowed": False,
        "default_path_changes_allowed": False,
        "source_ordered_maintenance_budget_decision": str(source_path),
        "phase3b_telemetry_status": phase3b_decision.get("telemetry_status"),
        "phase3b_feasibility": phase3b_decision.get(
            "device_side_ordered_candidate_maintenance_feasibility"
        ),
        "phase3b_recommended_next_action": phase3b_decision.get(
            "recommended_next_action"
        ),
    }


def active_design(source_path, phase3b_decision):
    design = base_design(source_path, phase3b_decision)
    design.update(
        {
            "decision_status": "ready",
            "shadow_design_status": "ready_for_opt_in_shadow_implementation",
            "recommended_next_action": "implement_opt_in_device_ordered_maintenance_shadow",
            "input_contract": "row_run_summaries_ordered",
            "ordering_contract": "preserve_original_summary_order",
            "shadow_result_contract": "validation_telemetry_only",
            "forbidden_transforms": FORBIDDEN_TRANSFORMS,
            "required_counter_comparisons": REQUIRED_COUNTER_COMPARISONS,
            "required_validation_hashes": REQUIRED_VALIDATION_HASHES,
            "required_mismatch_fields": REQUIRED_MISMATCH_FIELDS,
            "required_shadow_telemetry": REQUIRED_SHADOW_TELEMETRY,
            "opt_in_environment_flags": [
                "LONGTARGET_SIM_DEVICE_ORDERED_MAINTENANCE_SHADOW",
                "LONGTARGET_SIM_DEVICE_ORDERED_MAINTENANCE_SHADOW_VALIDATE",
            ],
            "promotion_gates": PROMOTION_GATES,
            "scope_plan": SCOPE_PLAN,
        }
    )
    return design


def inactive_design(source_path, phase3b_decision):
    design = base_design(source_path, phase3b_decision)
    design.update(
        {
            "decision_status": "inactive",
            "shadow_design_status": "blocked_by_phase3b_decision",
            "recommended_next_action": "return_to_ordered_candidate_maintenance_budget",
            "input_contract": None,
            "ordering_contract": None,
            "shadow_result_contract": None,
            "forbidden_transforms": [],
            "required_counter_comparisons": [],
            "required_validation_hashes": [],
            "required_mismatch_fields": [],
            "required_shadow_telemetry": [],
            "opt_in_environment_flags": [],
            "promotion_gates": {},
            "scope_plan": [],
        }
    )
    return design


def build_design(source_path, phase3b_decision):
    if phase3b_ready(phase3b_decision):
        return active_design(source_path, phase3b_decision)
    return inactive_design(source_path, phase3b_decision)


def render_markdown(design):
    lines = [
        "# Device Ordered Maintenance Shadow Design",
        "",
        f"- phase: `{design['phase']}`",
        f"- decision_status: `{design['decision_status']}`",
        f"- shadow_design_status: `{design['shadow_design_status']}`",
        f"- recommended_next_action: `{design['recommended_next_action']}`",
        f"- runtime_prototype_allowed: `{str(design['runtime_prototype_allowed']).lower()}`",
        "- default_path_changes_allowed: "
        f"`{str(design['default_path_changes_allowed']).lower()}`",
        "",
        "## Contracts",
        "",
        f"- input_contract: `{design['input_contract']}`",
        f"- ordering_contract: `{design['ordering_contract']}`",
        f"- shadow_result_contract: `{design['shadow_result_contract']}`",
        "",
        "## Forbidden Transforms",
        "",
    ]
    for item in design.get("forbidden_transforms", []):
        lines.append(f"- `{item}`")
    lines.extend(["", "## Required Validation Hashes", ""])
    for item in design.get("required_validation_hashes", []):
        lines.append(f"- `{item}`")
    lines.extend(["", "## Promotion Gates", ""])
    for group, entries in design.get("promotion_gates", {}).items():
        joined = ", ".join(f"`{entry}`" for entry in entries)
        lines.append(f"- {group}: {joined}")
    lines.append("")
    return "\n".join(lines)


def write_outputs(output_dir, design):
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "device_ordered_maintenance_shadow_design.json").open(
        "w", encoding="utf-8"
    ) as handle:
        json.dump(design, handle, indent=2, sort_keys=True)
        handle.write("\n")
    (output_dir / "device_ordered_maintenance_shadow_design.md").write_text(
        render_markdown(design), encoding="utf-8"
    )


def main():
    args = parse_args()
    phase3b_decision, source_path = read_json(args.ordered_maintenance_budget_decision)
    design = build_design(source_path, phase3b_decision)
    write_outputs(Path(args.output_dir), design)


if __name__ == "__main__":
    main()
