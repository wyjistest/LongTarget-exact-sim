#!/usr/bin/env python3
import argparse
import csv
import json
from pathlib import Path


PHASE = "device_side_ordered_candidate_maintenance_shadow_validation"

CASE_FIELDS = [
    "workload_id",
    "workload_class",
    "shadow_enabled",
    "shadow_validate_enabled",
    "shadow_backend",
    "shadow_status",
    "shadow_case_count",
    "shadow_summary_count",
    "shadow_event_count",
    "shadow_mismatch_count",
    "shadow_first_mismatch_case_id",
    "shadow_first_mismatch_summary_ordinal",
    "shadow_first_mismatch_kind",
    "shadow_seconds",
    "host_cpu_merge_seconds",
    "shadow_vs_host_cpu_merge_ratio",
    "host_final_candidate_state_hash",
    "shadow_final_candidate_state_hash",
    "host_replacement_sequence_hash",
    "shadow_replacement_sequence_hash",
    "host_running_min_sequence_hash",
    "shadow_running_min_sequence_hash",
    "host_candidate_index_visibility_hash",
    "shadow_candidate_index_visibility_hash",
    "host_safe_store_state_hash",
    "shadow_safe_store_state_hash",
    "host_observed_candidate_index_hash",
    "shadow_observed_candidate_index_hash",
    "missing_required_field_count",
]

REQUIRED_KEYS = {
    "shadow_enabled": (
        "sim_ordered_maintenance_shadow_enabled",
        "sim_device_ordered_maintenance_shadow_enabled",
    ),
    "shadow_validate_enabled": (
        "sim_ordered_maintenance_shadow_validate_enabled",
        "sim_device_ordered_maintenance_shadow_validate_enabled",
    ),
    "shadow_status": (
        "sim_ordered_maintenance_shadow_status",
        "sim_device_ordered_maintenance_shadow_status",
    ),
    "shadow_case_count": (
        "sim_ordered_maintenance_shadow_case_count",
        "sim_device_ordered_maintenance_shadow_case_count",
    ),
    "shadow_summary_count": (
        "sim_ordered_maintenance_shadow_summary_count",
        "sim_device_ordered_maintenance_shadow_summary_count",
    ),
    "shadow_event_count": (
        "sim_ordered_maintenance_shadow_event_count",
        "sim_device_ordered_maintenance_shadow_event_count",
    ),
    "shadow_mismatch_count": (
        "sim_ordered_maintenance_shadow_mismatch_count",
        "sim_device_ordered_maintenance_shadow_mismatch_count",
    ),
    "host_final_candidate_state_hash": (
        "sim_ordered_maintenance_host_final_candidate_state_hash",
        "sim_device_ordered_maintenance_host_final_candidate_state_hash",
    ),
    "shadow_final_candidate_state_hash": (
        "sim_ordered_maintenance_shadow_final_candidate_state_hash",
        "sim_device_ordered_maintenance_shadow_final_candidate_state_hash",
    ),
    "host_replacement_sequence_hash": (
        "sim_ordered_maintenance_host_replacement_sequence_hash",
        "sim_device_ordered_maintenance_host_replacement_sequence_hash",
    ),
    "shadow_replacement_sequence_hash": (
        "sim_ordered_maintenance_shadow_replacement_sequence_hash",
        "sim_device_ordered_maintenance_shadow_replacement_sequence_hash",
    ),
    "host_running_min_sequence_hash": (
        "sim_ordered_maintenance_host_running_min_sequence_hash",
        "sim_device_ordered_maintenance_host_running_min_update_sequence_hash",
    ),
    "shadow_running_min_sequence_hash": (
        "sim_ordered_maintenance_shadow_running_min_sequence_hash",
        "sim_device_ordered_maintenance_shadow_running_min_update_sequence_hash",
    ),
    "host_candidate_index_visibility_hash": (
        "sim_ordered_maintenance_host_candidate_index_visibility_hash",
        "sim_device_ordered_maintenance_host_candidate_index_visibility_hash",
    ),
    "shadow_candidate_index_visibility_hash": (
        "sim_ordered_maintenance_shadow_candidate_index_visibility_hash",
        "sim_device_ordered_maintenance_shadow_candidate_index_visibility_hash",
    ),
    "host_safe_store_state_hash": (
        "sim_ordered_maintenance_host_safe_store_state_hash",
        "sim_device_ordered_maintenance_host_safe_store_state_hash",
    ),
    "shadow_safe_store_state_hash": (
        "sim_ordered_maintenance_shadow_safe_store_state_hash",
        "sim_device_ordered_maintenance_shadow_safe_store_state_hash",
    ),
}

OPTIONAL_KEYS = {
    "shadow_backend": (
        "sim_ordered_maintenance_shadow_backend",
        "sim_device_ordered_maintenance_shadow_backend",
    ),
    "shadow_first_mismatch_case_id": (
        "sim_ordered_maintenance_shadow_first_mismatch_case_id",
        "sim_device_ordered_maintenance_shadow_first_mismatch_case_id",
    ),
    "shadow_first_mismatch_summary_ordinal": (
        "sim_ordered_maintenance_shadow_first_mismatch_summary_ordinal",
        "sim_device_ordered_maintenance_shadow_first_mismatch_summary_ordinal",
    ),
    "shadow_first_mismatch_kind": (
        "sim_ordered_maintenance_shadow_first_mismatch_kind",
        "sim_device_ordered_maintenance_shadow_first_mismatch_kind",
    ),
    "shadow_seconds": (
        "sim_ordered_maintenance_shadow_seconds",
        "sim_device_ordered_maintenance_shadow_seconds",
    ),
    "host_cpu_merge_seconds": (
        "sim_ordered_maintenance_shadow_host_cpu_merge_seconds",
        "sim_device_ordered_maintenance_shadow_host_cpu_merge_seconds",
        "sim_initial_scan_cpu_merge_seconds",
    ),
    "host_observed_candidate_index_hash": (
        "sim_ordered_maintenance_host_observed_candidate_index_hash",
        "sim_device_ordered_maintenance_host_observed_candidate_index_hash",
    ),
    "shadow_observed_candidate_index_hash": (
        "sim_ordered_maintenance_shadow_observed_candidate_index_hash",
        "sim_device_ordered_maintenance_shadow_observed_candidate_index_hash",
    ),
}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Summarize Phase 3d.1 ordered-maintenance shadow validation."
    )
    parser.add_argument(
        "--shadow-telemetry",
        action="append",
        required=True,
        help="Telemetry/projection JSON with sim_ordered_maintenance_shadow_* fields.",
    )
    parser.add_argument("--output-dir", required=True, help="Output directory.")
    parser.add_argument(
        "--minimum-case-count",
        type=int,
        default=1,
        help="Minimum shadow case count required for passed coverage.",
    )
    parser.add_argument(
        "--minimum-summary-count",
        type=int,
        default=1,
        help="Minimum shadow summary count required for passed coverage.",
    )
    return parser.parse_args()


def read_json(path):
    source = Path(path)
    with source.open("r", encoding="utf-8") as handle:
        return json.load(handle), source


def lookup(payload, aliases, default=None):
    for key in aliases:
        if key in payload:
            return payload[key]
        projected_key = f"projected_{key}"
        if projected_key in payload:
            return payload[projected_key]
    return default


def to_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() not in {"", "0", "false", "no", "off"}
    return False


def to_int(value, default=0):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def to_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def normalize_case(payload, source_path):
    case = {
        "workload_id": payload.get("workload_id", source_path.stem),
        "workload_class": payload.get("workload_class", "unknown"),
    }
    missing = []
    for field, aliases in REQUIRED_KEYS.items():
        value = lookup(payload, aliases)
        if value is None:
            missing.append(field)
            value = ""
        case[field] = value
    for field, aliases in OPTIONAL_KEYS.items():
        if field == "shadow_backend":
            default = "cpu"
        else:
            default = "none" if "kind" in field or "case_id" in field else 0
        case[field] = lookup(payload, aliases, default)

    case["shadow_enabled"] = to_bool(case["shadow_enabled"])
    case["shadow_validate_enabled"] = to_bool(case["shadow_validate_enabled"])
    case["shadow_backend"] = str(case["shadow_backend"]).strip().lower() or "cpu"
    if case["shadow_backend"] not in {"cpu", "device"}:
        case["shadow_backend"] = "unknown"
    case["shadow_status"] = str(case["shadow_status"]).strip().lower()
    for field in [
        "shadow_case_count",
        "shadow_summary_count",
        "shadow_event_count",
        "shadow_mismatch_count",
        "shadow_first_mismatch_summary_ordinal",
    ]:
        case[field] = to_int(case[field])
    for field in [
        "shadow_seconds",
        "host_cpu_merge_seconds",
    ]:
        case[field] = to_float(case[field])
    for field in [
        "host_final_candidate_state_hash",
        "shadow_final_candidate_state_hash",
        "host_replacement_sequence_hash",
        "shadow_replacement_sequence_hash",
        "host_running_min_sequence_hash",
        "shadow_running_min_sequence_hash",
        "host_candidate_index_visibility_hash",
        "shadow_candidate_index_visibility_hash",
        "host_safe_store_state_hash",
        "shadow_safe_store_state_hash",
        "host_observed_candidate_index_hash",
        "shadow_observed_candidate_index_hash",
    ]:
        case[field] = to_int(case[field])
    case["shadow_vs_host_cpu_merge_ratio"] = (
        case["shadow_seconds"] / case["host_cpu_merge_seconds"]
        if case["host_cpu_merge_seconds"] > 0.0
        else 0.0
    )
    case["missing_required_field_count"] = len(missing)
    return case


def digest_pairs_match(case):
    pairs = [
        ("host_final_candidate_state_hash", "shadow_final_candidate_state_hash"),
        ("host_replacement_sequence_hash", "shadow_replacement_sequence_hash"),
        ("host_running_min_sequence_hash", "shadow_running_min_sequence_hash"),
        (
            "host_candidate_index_visibility_hash",
            "shadow_candidate_index_visibility_hash",
        ),
        ("host_safe_store_state_hash", "shadow_safe_store_state_hash"),
    ]
    return all(case[left] == case[right] and case[left] != 0 for left, right in pairs)


def build_summary(cases):
    enabled_cases = [case for case in cases if case["shadow_enabled"]]
    mismatch_cases = [case for case in cases if case["shadow_mismatch_count"] > 0]
    incomplete_cases = [case for case in cases if case["missing_required_field_count"] > 0]
    unsupported_cases = [
        case for case in enabled_cases if case["shadow_status"] == "not_supported"
    ]
    digest_match_cases = [case for case in enabled_cases if digest_pairs_match(case)]
    digest_mismatch_cases = [
        case
        for case in enabled_cases
        if case["missing_required_field_count"] == 0 and not digest_pairs_match(case)
        and case["shadow_status"] != "not_supported"
    ]
    return {
        "phase": PHASE,
        "workload_count": len(cases),
        "enabled_workload_count": len(enabled_cases),
        "incomplete_workload_count": len(incomplete_cases),
        "unsupported_workload_count": len(unsupported_cases),
        "device_unsupported_workload_count": sum(
            1 for case in unsupported_cases if case["shadow_backend"] == "device"
        ),
        "mismatch_workload_count": len(mismatch_cases),
        "digest_match_workload_count": len(digest_match_cases),
        "digest_mismatch_workload_count": len(digest_mismatch_cases),
        "total_shadow_case_count": sum(case["shadow_case_count"] for case in cases),
        "total_shadow_summary_count": sum(case["shadow_summary_count"] for case in cases),
        "total_shadow_event_count": sum(case["shadow_event_count"] for case in cases),
        "total_shadow_mismatch_count": sum(
            case["shadow_mismatch_count"] for case in cases
        ),
        "total_shadow_seconds": sum(case["shadow_seconds"] for case in cases),
        "total_host_cpu_merge_seconds": sum(
            case["host_cpu_merge_seconds"] for case in cases
        ),
        "cases": cases,
    }


def build_decision(summary, minimum_case_count, minimum_summary_count):
    decision = {
        "phase": PHASE,
        "decision_status": "ready",
        "runtime_prototype_allowed": False,
        "default_path_changes_allowed": False,
        "workload_count": summary["workload_count"],
        "enabled_workload_count": summary["enabled_workload_count"],
        "total_shadow_case_count": summary["total_shadow_case_count"],
        "total_shadow_summary_count": summary["total_shadow_summary_count"],
        "total_shadow_mismatch_count": summary["total_shadow_mismatch_count"],
        "digest_mismatch_workload_count": summary["digest_mismatch_workload_count"],
    }
    if summary["enabled_workload_count"] == 0:
        decision.update(
            {
                "shadow_validation_status": "disabled",
                "recommended_next_action": "enable_shadow_validation",
            }
        )
    elif summary["incomplete_workload_count"] > 0:
        decision.update(
            {
                "shadow_validation_status": "incomplete",
                "recommended_next_action": "collect_shadow_validation_telemetry",
            }
        )
    elif summary["unsupported_workload_count"] > 0:
        decision.update(
            {
                "shadow_validation_status": "incomplete",
                "recommended_next_action": (
                    "expand_device_shadow_coverage"
                    if summary["device_unsupported_workload_count"] > 0
                    else "collect_shadow_validation_telemetry"
                ),
            }
        )
    elif (
        summary["total_shadow_mismatch_count"] > 0
        or summary["digest_mismatch_workload_count"] > 0
    ):
        decision.update(
            {
                "shadow_validation_status": "mismatch",
                "recommended_next_action": "debug_shadow_mismatch",
            }
        )
    elif (
        summary["total_shadow_case_count"] < minimum_case_count
        or summary["total_shadow_summary_count"] < minimum_summary_count
    ):
        decision.update(
            {
                "shadow_validation_status": "insufficient_coverage",
                "recommended_next_action": "expand_shadow_coverage",
            }
        )
    else:
        decision.update(
            {
                "shadow_validation_status": "passed",
                "recommended_next_action": "profile_shadow_cost",
            }
        )
    return decision


def render_markdown(summary, decision):
    lines = [
        "# Device Ordered Maintenance Shadow Validation",
        "",
        f"- phase: `{PHASE}`",
        f"- shadow_validation_status: `{decision['shadow_validation_status']}`",
        f"- recommended_next_action: `{decision['recommended_next_action']}`",
        "- runtime_prototype_allowed: `false`",
        "- default_path_changes_allowed: `false`",
        "",
        "## Coverage",
        "",
        f"- workloads: `{summary['workload_count']}`",
        f"- enabled_workloads: `{summary['enabled_workload_count']}`",
        f"- shadow_cases: `{summary['total_shadow_case_count']}`",
        f"- shadow_summaries: `{summary['total_shadow_summary_count']}`",
        f"- mismatches: `{summary['total_shadow_mismatch_count']}`",
        "",
        "## Cases",
        "",
    ]
    for case in summary["cases"]:
        lines.append(
            "- "
            f"{case['workload_id']}: backend=`{case['shadow_backend']}`, "
            f"status=`{case['shadow_status']}`, "
            f"mismatches=`{case['shadow_mismatch_count']}`"
        )
    lines.append("")
    return "\n".join(lines)


def write_outputs(output_dir, cases, summary, decision):
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "device_ordered_maintenance_shadow_validation_cases.tsv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=CASE_FIELDS, delimiter="\t")
        writer.writeheader()
        for case in cases:
            writer.writerow({field: case.get(field, "") for field in CASE_FIELDS})
    with (output_dir / "device_ordered_maintenance_shadow_validation_summary.json").open(
        "w", encoding="utf-8"
    ) as handle:
        json.dump(summary, handle, indent=2, sort_keys=True)
        handle.write("\n")
    with (output_dir / "device_ordered_maintenance_shadow_validation_decision.json").open(
        "w", encoding="utf-8"
    ) as handle:
        json.dump(decision, handle, indent=2, sort_keys=True)
        handle.write("\n")
    (output_dir / "device_ordered_maintenance_shadow_validation.md").write_text(
        render_markdown(summary, decision), encoding="utf-8"
    )


def main():
    args = parse_args()
    cases = []
    for telemetry_path in args.shadow_telemetry:
        payload, source_path = read_json(telemetry_path)
        cases.append(normalize_case(payload, source_path))
    summary = build_summary(cases)
    decision = build_decision(
        summary,
        minimum_case_count=args.minimum_case_count,
        minimum_summary_count=args.minimum_summary_count,
    )
    write_outputs(Path(args.output_dir), cases, summary, decision)


if __name__ == "__main__":
    main()
