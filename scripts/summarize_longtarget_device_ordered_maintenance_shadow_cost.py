#!/usr/bin/env python3
import argparse
import csv
import json
from pathlib import Path


PHASE = "device_side_ordered_candidate_maintenance_shadow_cost"

CASE_FIELDS = [
    "workload_id",
    "workload_class",
    "shadow_cost_mode",
    "shadow_enabled",
    "shadow_validate_enabled",
    "shadow_status",
    "total_seconds",
    "sim_seconds",
    "host_cpu_merge_seconds",
    "shadow_seconds",
    "shadow_case_count",
    "shadow_summary_count",
    "shadow_event_count",
    "shadow_mismatch_count",
    "shadow_seconds_per_summary",
    "shadow_seconds_per_event",
    "host_cpu_merge_seconds_per_summary",
    "shadow_vs_host_cpu_merge_ratio",
    "estimated_cpu_merge_seconds_avoidable",
    "estimated_d2h_bytes_avoided",
    "missing_required_field_count",
]

REQUIRED_KEYS = {
    "total_seconds": ("total_seconds",),
    "sim_seconds": ("sim_seconds",),
    "host_cpu_merge_seconds": (
        "sim_ordered_maintenance_shadow_host_cpu_merge_seconds",
        "sim_device_ordered_maintenance_shadow_host_cpu_merge_seconds",
        "sim_initial_scan_cpu_merge_seconds",
    ),
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
    "shadow_seconds": (
        "sim_ordered_maintenance_shadow_seconds",
        "sim_device_ordered_maintenance_shadow_seconds",
    ),
}

OPTIONAL_KEYS = {
    "estimated_cpu_merge_seconds_avoidable": (
        "sim_ordered_maintenance_estimated_cpu_merge_seconds_avoidable",
        "projected_sim_ordered_maintenance_estimated_cpu_merge_seconds_avoidable",
        "sim_initial_scan_cpu_merge_seconds",
    ),
    "estimated_d2h_bytes_avoided": (
        "sim_ordered_maintenance_estimated_d2h_bytes_avoided",
        "projected_sim_ordered_maintenance_estimated_d2h_bytes_avoided",
    ),
}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Summarize Phase 3d.1 ordered-maintenance shadow cost."
    )
    parser.add_argument(
        "--shadow-validation-decision",
        required=True,
        help="device_ordered_maintenance_shadow_validation_decision.json.",
    )
    parser.add_argument(
        "--cost-telemetry",
        action="append",
        required=True,
        help="Benchmark/projection JSON with shadow cost fields. Repeat per workload/mode.",
    )
    parser.add_argument("--output-dir", required=True, help="Output directory.")
    parser.add_argument(
        "--design-ratio-threshold",
        type=float,
        default=2.0,
        help="shadow/host CPU-merge ratio at or below which device shadow design is allowed.",
    )
    parser.add_argument(
        "--breakdown-ratio-threshold",
        type=float,
        default=5.0,
        help="shadow/host CPU-merge ratio at or below which a cost breakdown is still useful.",
    )
    parser.add_argument(
        "--minimum-avoidable-seconds",
        type=float,
        default=1.0,
        help="Minimum avoidable CPU merge seconds for profile_shadow_cost_breakdown.",
    )
    parser.add_argument(
        "--minimum-shadow-summary-count",
        type=int,
        default=1,
        help="Minimum shadow_validate summary coverage required.",
    )
    return parser.parse_args()


def read_json(path):
    source = Path(path)
    with source.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if isinstance(payload, dict) and isinstance(payload.get("benchmark"), dict):
        merged = dict(payload["benchmark"])
        for key, value in payload.items():
            if key != "benchmark":
                merged.setdefault(key, value)
        payload = merged
    return payload, source


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


def infer_cost_mode(payload, shadow_enabled, shadow_validate_enabled):
    explicit = payload.get("shadow_cost_mode") or payload.get("cost_mode") or payload.get("run_mode")
    if explicit:
        return str(explicit)
    if not shadow_enabled:
        return "baseline"
    if shadow_validate_enabled:
        return "shadow_validate"
    return "shadow_no_validate"


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
        case[field] = lookup(payload, aliases, 0)

    case["shadow_enabled"] = to_bool(case["shadow_enabled"])
    case["shadow_validate_enabled"] = to_bool(case["shadow_validate_enabled"])
    case["shadow_cost_mode"] = infer_cost_mode(
        payload,
        case["shadow_enabled"],
        case["shadow_validate_enabled"],
    )
    for field in [
        "shadow_case_count",
        "shadow_summary_count",
        "shadow_event_count",
        "shadow_mismatch_count",
        "estimated_d2h_bytes_avoided",
    ]:
        case[field] = to_int(case[field])
    for field in [
        "total_seconds",
        "sim_seconds",
        "host_cpu_merge_seconds",
        "shadow_seconds",
        "estimated_cpu_merge_seconds_avoidable",
    ]:
        case[field] = to_float(case[field])

    case["shadow_seconds_per_summary"] = (
        case["shadow_seconds"] / case["shadow_summary_count"]
        if case["shadow_summary_count"] > 0
        else 0.0
    )
    case["shadow_seconds_per_event"] = (
        case["shadow_seconds"] / case["shadow_event_count"]
        if case["shadow_event_count"] > 0
        else 0.0
    )
    case["host_cpu_merge_seconds_per_summary"] = (
        case["host_cpu_merge_seconds"] / case["shadow_summary_count"]
        if case["shadow_summary_count"] > 0
        else 0.0
    )
    case["shadow_vs_host_cpu_merge_ratio"] = (
        case["shadow_seconds"] / case["host_cpu_merge_seconds"]
        if case["host_cpu_merge_seconds"] > 0.0
        else 0.0
    )
    case["missing_required_field_count"] = len(missing)
    return case


def sum_field(rows, field):
    return sum(row[field] for row in rows)


def build_summary(cases, validation_decision):
    baseline_cases = [case for case in cases if case["shadow_cost_mode"] == "baseline"]
    no_validate_cases = [
        case for case in cases if case["shadow_cost_mode"] == "shadow_no_validate"
    ]
    validate_cases = [
        case for case in cases if case["shadow_cost_mode"] == "shadow_validate"
    ]
    incomplete_cases = [
        case for case in cases if case["missing_required_field_count"] > 0
    ]
    validate_host_seconds = sum_field(validate_cases, "host_cpu_merge_seconds")
    validate_shadow_seconds = sum_field(validate_cases, "shadow_seconds")
    no_validate_shadow_seconds = sum_field(no_validate_cases, "shadow_seconds")
    aggregate = {
        "workload_count": len({case["workload_id"] for case in cases}),
        "case_count": len(cases),
        "baseline_workload_count": len({case["workload_id"] for case in baseline_cases}),
        "shadow_no_validate_workload_count": len(
            {case["workload_id"] for case in no_validate_cases}
        ),
        "shadow_validate_workload_count": len(
            {case["workload_id"] for case in validate_cases}
        ),
        "incomplete_case_count": len(incomplete_cases),
        "shadow_validate_mismatch_count": sum_field(validate_cases, "shadow_mismatch_count"),
        "shadow_validate_case_count": sum_field(validate_cases, "shadow_case_count"),
        "shadow_validate_summary_count": sum_field(validate_cases, "shadow_summary_count"),
        "shadow_validate_event_count": sum_field(validate_cases, "shadow_event_count"),
        "shadow_validate_seconds": validate_shadow_seconds,
        "shadow_no_validate_seconds": no_validate_shadow_seconds,
        "host_cpu_merge_seconds": validate_host_seconds,
        "estimated_cpu_merge_seconds_avoidable": sum_field(
            validate_cases, "estimated_cpu_merge_seconds_avoidable"
        ),
        "estimated_d2h_bytes_avoided": sum_field(
            validate_cases, "estimated_d2h_bytes_avoided"
        ),
        "shadow_vs_host_cpu_merge_ratio": (
            validate_shadow_seconds / validate_host_seconds
            if validate_host_seconds > 0.0
            else 0.0
        ),
        "shadow_validate_vs_shadow_no_validate_ratio": (
            validate_shadow_seconds / no_validate_shadow_seconds
            if no_validate_shadow_seconds > 0.0
            else 0.0
        ),
    }
    return {
        "phase": PHASE,
        "validation_decision": validation_decision,
        "aggregate": aggregate,
        "cases": cases,
    }


def build_decision(
    summary,
    design_ratio_threshold,
    breakdown_ratio_threshold,
    minimum_avoidable_seconds,
    minimum_shadow_summary_count,
):
    validation = summary["validation_decision"]
    aggregate = summary["aggregate"]
    decision = {
        "phase": PHASE,
        "decision_status": "ready",
        "runtime_prototype_allowed": False,
        "default_path_changes_allowed": False,
        "shadow_validation_status": validation.get("shadow_validation_status", "unknown"),
        "workload_count": aggregate["workload_count"],
        "shadow_validate_workload_count": aggregate["shadow_validate_workload_count"],
        "shadow_validate_summary_count": aggregate["shadow_validate_summary_count"],
        "shadow_validate_mismatch_count": aggregate["shadow_validate_mismatch_count"],
        "shadow_vs_host_cpu_merge_ratio": aggregate["shadow_vs_host_cpu_merge_ratio"],
        "shadow_validate_vs_shadow_no_validate_ratio": aggregate[
            "shadow_validate_vs_shadow_no_validate_ratio"
        ],
        "estimated_cpu_merge_seconds_avoidable": aggregate[
            "estimated_cpu_merge_seconds_avoidable"
        ],
        "estimated_d2h_bytes_avoided": aggregate["estimated_d2h_bytes_avoided"],
    }

    if validation.get("shadow_validation_status") != "passed":
        decision.update(
            {
                "shadow_cost_status": "validation_not_passed",
                "recommended_next_action": "debug_shadow_mismatch",
            }
        )
    elif aggregate["incomplete_case_count"] > 0:
        decision.update(
            {
                "shadow_cost_status": "incomplete",
                "recommended_next_action": "collect_shadow_cost_telemetry",
            }
        )
    elif (
        aggregate["shadow_validate_workload_count"] == 0
        or aggregate["shadow_validate_summary_count"] < minimum_shadow_summary_count
    ):
        decision.update(
            {
                "shadow_cost_status": "insufficient_coverage",
                "recommended_next_action": "expand_shadow_coverage",
            }
        )
    elif aggregate["shadow_validate_mismatch_count"] > 0:
        decision.update(
            {
                "shadow_cost_status": "validation_not_passed",
                "recommended_next_action": "debug_shadow_mismatch",
            }
        )
    elif (
        aggregate["shadow_validate_seconds"] <= 0.0
        or aggregate["host_cpu_merge_seconds"] <= 0.0
    ):
        decision.update(
            {
                "shadow_cost_status": "incomplete",
                "recommended_next_action": "collect_shadow_cost_telemetry",
            }
        )
    elif aggregate["shadow_vs_host_cpu_merge_ratio"] <= design_ratio_threshold:
        decision.update(
            {
                "shadow_cost_status": "ready",
                "recommended_next_action": "design_device_shadow_kernel",
            }
        )
    elif (
        aggregate["shadow_vs_host_cpu_merge_ratio"] <= breakdown_ratio_threshold
        and aggregate["estimated_cpu_merge_seconds_avoidable"]
        >= minimum_avoidable_seconds
    ):
        decision.update(
            {
                "shadow_cost_status": "cost_breakdown_needed",
                "recommended_next_action": "profile_shadow_cost_breakdown",
            }
        )
    else:
        decision.update(
            {
                "shadow_cost_status": "too_expensive",
                "recommended_next_action": "stop_device_ordered_shadow",
            }
        )
    return decision


def render_markdown(summary, decision):
    aggregate = summary["aggregate"]
    lines = [
        "# Device Ordered Maintenance Shadow Cost",
        "",
        f"- phase: `{PHASE}`",
        f"- shadow_cost_status: `{decision['shadow_cost_status']}`",
        f"- recommended_next_action: `{decision['recommended_next_action']}`",
        "- runtime_prototype_allowed: `false`",
        "- default_path_changes_allowed: `false`",
        "",
        "## Aggregate",
        "",
        f"- workloads: `{aggregate['workload_count']}`",
        f"- shadow_validate_workloads: `{aggregate['shadow_validate_workload_count']}`",
        f"- shadow_validate_summaries: `{aggregate['shadow_validate_summary_count']}`",
        f"- shadow_validate_seconds: `{aggregate['shadow_validate_seconds']:.6f}`",
        f"- host_cpu_merge_seconds: `{aggregate['host_cpu_merge_seconds']:.6f}`",
        f"- shadow_vs_host_cpu_merge_ratio: `{aggregate['shadow_vs_host_cpu_merge_ratio']:.6f}`",
        f"- shadow_validate_vs_shadow_no_validate_ratio: `{aggregate['shadow_validate_vs_shadow_no_validate_ratio']:.6f}`",
        "",
        "## Cases",
        "",
    ]
    for case in summary["cases"]:
        lines.append(
            "- "
            f"{case['workload_id']} / {case['shadow_cost_mode']}: "
            f"shadow_seconds=`{case['shadow_seconds']:.6f}`, "
            f"host_cpu_merge_seconds=`{case['host_cpu_merge_seconds']:.6f}`, "
            f"ratio=`{case['shadow_vs_host_cpu_merge_ratio']:.6f}`"
        )
    lines.append("")
    return "\n".join(lines)


def write_outputs(output_dir, cases, summary, decision):
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "device_ordered_maintenance_shadow_cost_cases.tsv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=CASE_FIELDS, delimiter="\t")
        writer.writeheader()
        for case in cases:
            writer.writerow({field: case.get(field, "") for field in CASE_FIELDS})
    with (output_dir / "device_ordered_maintenance_shadow_cost_summary.json").open(
        "w", encoding="utf-8"
    ) as handle:
        json.dump(summary, handle, indent=2, sort_keys=True)
        handle.write("\n")
    with (output_dir / "device_ordered_maintenance_shadow_cost_decision.json").open(
        "w", encoding="utf-8"
    ) as handle:
        json.dump(decision, handle, indent=2, sort_keys=True)
        handle.write("\n")
    (output_dir / "device_ordered_maintenance_shadow_cost.md").write_text(
        render_markdown(summary, decision), encoding="utf-8"
    )


def main():
    args = parse_args()
    validation_decision, _ = read_json(args.shadow_validation_decision)
    cases = []
    for telemetry_path in args.cost_telemetry:
        payload, source_path = read_json(telemetry_path)
        cases.append(normalize_case(payload, source_path))
    summary = build_summary(cases, validation_decision)
    decision = build_decision(
        summary,
        design_ratio_threshold=args.design_ratio_threshold,
        breakdown_ratio_threshold=args.breakdown_ratio_threshold,
        minimum_avoidable_seconds=args.minimum_avoidable_seconds,
        minimum_shadow_summary_count=args.minimum_shadow_summary_count,
    )
    write_outputs(Path(args.output_dir), cases, summary, decision)


if __name__ == "__main__":
    main()
