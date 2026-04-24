#!/usr/bin/env python3
import argparse
import csv
import json
from pathlib import Path


PHASE = "device_side_ordered_candidate_maintenance_budget"

ALLOWED_NEXT_ACTIONS = [
    "collect_ordered_candidate_maintenance_telemetry",
    "design_device_side_ordered_candidate_maintenance_shadow",
    "profile_device_resident_state_handoff_with_ordered_maintenance",
    "stop_host_cpu_merge_work",
    "stop_or_rethink_device_side_ordered_maintenance",
    "stop_or_rethink_device_side_ordered_candidate_maintenance",
    "collect_more_ordered_maintenance_shape",
    "refine_ordered_maintenance_shape_telemetry",
    "return_to_sim_pipeline_budget_rollup",
]

ORDERED_SHAPE_CONFIDENCE_ORDER = [
    "fallback_conservative",
    "coarse",
    "event_level",
    "validated",
]

REQUIRED_SHAPE_KEYS = {
    "candidate_event_count": (
        "projected_sim_ordered_maintenance_candidate_event_count",
        "sim_ordered_maintenance_candidate_event_count",
    ),
    "ordered_segment_count": (
        "projected_sim_ordered_maintenance_ordered_segment_count",
        "sim_ordered_maintenance_ordered_segment_count",
    ),
    "parallel_segment_count": (
        "projected_sim_ordered_maintenance_parallel_segment_count",
        "sim_ordered_maintenance_parallel_segment_count",
    ),
    "mean_segment_length": (
        "projected_sim_ordered_maintenance_mean_segment_length",
        "sim_ordered_maintenance_mean_segment_length",
    ),
    "p90_segment_length": (
        "projected_sim_ordered_maintenance_p90_segment_length",
        "sim_ordered_maintenance_p90_segment_length",
    ),
    "serial_dependency_share": (
        "projected_sim_ordered_maintenance_serial_dependency_share",
        "sim_ordered_maintenance_serial_dependency_share",
    ),
    "parallelizable_event_share": (
        "projected_sim_ordered_maintenance_parallelizable_event_share",
        "sim_ordered_maintenance_parallelizable_event_share",
    ),
    "estimated_d2h_bytes_avoided": (
        "projected_sim_ordered_maintenance_estimated_d2h_bytes_avoided",
        "sim_ordered_maintenance_estimated_d2h_bytes_avoided",
    ),
    "estimated_host_rebuild_seconds_avoided": (
        "projected_sim_ordered_maintenance_estimated_host_rebuild_seconds_avoided",
        "sim_ordered_maintenance_estimated_host_rebuild_seconds_avoided",
    ),
    "estimated_cpu_merge_seconds_avoidable": (
        "projected_sim_ordered_maintenance_estimated_cpu_merge_seconds_avoidable",
        "sim_ordered_maintenance_estimated_cpu_merge_seconds_avoidable",
    ),
    "state_machine_count": (
        "projected_sim_ordered_maintenance_state_machine_count",
        "sim_ordered_maintenance_state_machine_count",
    ),
    "state_machine_nonempty_count": (
        "projected_sim_ordered_maintenance_state_machine_nonempty_count",
        "sim_ordered_maintenance_state_machine_nonempty_count",
    ),
    "state_machine_event_count_total": (
        "projected_sim_ordered_maintenance_state_machine_event_count_total",
        "sim_ordered_maintenance_state_machine_event_count_total",
    ),
    "state_machine_event_count_p50": (
        "projected_sim_ordered_maintenance_state_machine_event_count_p50",
        "sim_ordered_maintenance_state_machine_event_count_p50",
    ),
    "state_machine_event_count_p90": (
        "projected_sim_ordered_maintenance_state_machine_event_count_p90",
        "sim_ordered_maintenance_state_machine_event_count_p90",
    ),
    "state_machine_event_count_p99": (
        "projected_sim_ordered_maintenance_state_machine_event_count_p99",
        "sim_ordered_maintenance_state_machine_event_count_p99",
    ),
    "state_machine_event_count_max": (
        "projected_sim_ordered_maintenance_state_machine_event_count_max",
        "sim_ordered_maintenance_state_machine_event_count_max",
    ),
    "state_machine_work_imbalance_ratio": (
        "projected_sim_ordered_maintenance_state_machine_work_imbalance_ratio",
        "sim_ordered_maintenance_state_machine_work_imbalance_ratio",
    ),
    "state_machine_ideal_parallelism": (
        "projected_sim_ordered_maintenance_state_machine_ideal_parallelism",
        "sim_ordered_maintenance_state_machine_ideal_parallelism",
    ),
}

REQUIRED_SOURCE_KEYS = {
    "ordered_segment_source": (
        "sim_ordered_maintenance_ordered_segment_source",
    ),
    "serial_dependency_source": (
        "sim_ordered_maintenance_serial_dependency_source",
    ),
    "parallelizable_event_source": (
        "sim_ordered_maintenance_parallelizable_event_source",
    ),
    "ordered_shape_confidence": (
        "sim_ordered_maintenance_ordered_shape_confidence",
    ),
}

OPTIONAL_SHAPE_KEYS = {
    "summary_count": (
        "projected_sim_initial_summary_count",
        "projected_sim_initial_run_summaries_total",
        "sim_initial_summary_count",
        "sim_initial_run_summaries_total",
    ),
    "candidate_state_bytes_d2h": (
        "projected_sim_initial_candidate_state_bytes_d2h",
        "projected_sim_initial_store_bytes_d2h",
        "sim_initial_candidate_state_bytes_d2h",
        "sim_initial_store_bytes_d2h",
    ),
}

CASE_FIELDS = [
    "workload_id",
    "workload_class",
    "host_cpu_merge_seconds",
    "host_cpu_merge_share_of_sim",
    "host_cpu_merge_share_of_total",
    "candidate_event_count",
    "summary_count",
    "ordered_segment_count",
    "parallel_segment_count",
    "ordered_segment_source",
    "serial_dependency_source",
    "parallelizable_event_source",
    "ordered_shape_confidence",
    "mean_segment_length",
    "p90_segment_length",
    "serial_dependency_share",
    "parallelizable_event_share",
    "estimated_d2h_bytes_avoided",
    "estimated_host_rebuild_seconds_avoided",
    "estimated_cpu_merge_seconds_avoidable",
    "state_machine_count",
    "state_machine_nonempty_count",
    "state_machine_event_count_total",
    "state_machine_event_count_p50",
    "state_machine_event_count_p90",
    "state_machine_event_count_p99",
    "state_machine_event_count_max",
    "state_machine_work_imbalance_ratio",
    "state_machine_ideal_parallelism",
    "candidate_state_bytes_d2h",
    "missing_required_field_count",
]


def parse_args():
    parser = argparse.ArgumentParser(
        description="Summarize Phase 3b ordered candidate maintenance feasibility."
    )
    parser.add_argument(
        "--sim-pipeline-budget-rollup-decision",
        required=True,
        help="sim_pipeline_budget_rollup_decision.json from Phase 3a.",
    )
    parser.add_argument("--output-dir", required=True, help="Output directory.")
    parser.add_argument(
        "--host-merge-share-threshold",
        type=float,
        default=0.30,
        help="Minimum host_cpu_merge share of SIM seconds to keep Phase 3b active.",
    )
    parser.add_argument(
        "--parallelizable-threshold",
        type=float,
        default=0.50,
        help="Minimum parallelizable event share for shadow-design feasibility.",
    )
    parser.add_argument(
        "--serial-dependency-stop-threshold",
        type=float,
        default=0.90,
        help="Serial dependency share that blocks device-side ordered maintenance.",
    )
    parser.add_argument(
        "--parallelizable-stop-threshold",
        type=float,
        default=0.10,
        help="Maximum parallelizable event share when declaring an event-level serial blocker.",
    )
    return parser.parse_args()


def read_json(path):
    source = Path(path)
    with source.open("r", encoding="utf-8") as handle:
        return json.load(handle), source


def number_or_none(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def first_number(data, keys):
    if not isinstance(data, dict):
        return None
    for key in keys:
        value = number_or_none(data.get(key))
        if value is not None:
            return value
    return None


def first_string(data, keys):
    if not isinstance(data, dict):
        return None
    for key in keys:
        value = data.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def format_number(value):
    if value is None:
        return ""
    return f"{value:.6f}"


def source_input_budget_from(sim_budget):
    if not isinstance(sim_budget, dict):
        return None
    value = sim_budget.get("source_input_budget")
    if isinstance(value, str) and value:
        return value
    return None


def host_cpu_merge_row(sim_budget):
    for row in sim_budget.get("subcomponents", []):
        if isinstance(row, dict) and row.get("subcomponent") == "host_cpu_merge":
            return row
    return {}


def load_optional_projection(sim_budget):
    source = source_input_budget_from(sim_budget)
    if not source:
        return {}, None
    path = Path(source)
    if not path.exists():
        return {}, str(path)
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle), str(path)


def shape_values_from(projection):
    values = {}
    missing = []
    for name, keys in REQUIRED_SHAPE_KEYS.items():
        value = first_number(projection, keys)
        values[name] = value
        if value is None:
            missing.append(name)
    for name, keys in REQUIRED_SOURCE_KEYS.items():
        value = first_string(projection, keys)
        values[name] = value
        if value is None:
            missing.append(name)
    for name, keys in OPTIONAL_SHAPE_KEYS.items():
        values[name] = first_number(projection, keys)
    values["missing_required_field_count"] = len(missing)
    values["missing_required_fields"] = missing
    return values


def workload_rows_from_rollup(rollup):
    rows = []
    decisions = rollup.get("workload_decisions")
    if not isinstance(decisions, dict):
        return rows
    for key, decision in decisions.items():
        if not isinstance(decision, dict):
            continue
        source = decision.get("source_sim_pipeline_budget")
        if not source:
            continue
        sim_budget_path = Path(source)
        if not sim_budget_path.exists():
            continue
        sim_budget, _ = read_json(sim_budget_path)
        projection, projection_source = load_optional_projection(sim_budget)
        host_row = host_cpu_merge_row(sim_budget)
        shape = shape_values_from(projection)
        rows.append(
            {
                "workload_key": key,
                "workload_id": decision.get("workload_id") or key,
                "workload_class": decision.get("workload_class") or "unknown",
                "host_cpu_merge_seconds": number_or_none(host_row.get("seconds")),
                "host_cpu_merge_share_of_sim": number_or_none(
                    host_row.get("share_of_sim_seconds")
                ),
                "host_cpu_merge_share_of_total": number_or_none(
                    host_row.get("share_of_total_seconds")
                ),
                "shape": shape,
                "source_sim_pipeline_budget": str(sim_budget_path),
                "source_input_budget": projection_source,
            }
        )
    return rows


def weighted_average(rows, key, weight_key):
    total_weight = 0.0
    total_value = 0.0
    for row in rows:
        value = row["shape"].get(key)
        weight = row["shape"].get(weight_key)
        if value is None or weight is None or weight <= 0.0:
            continue
        total_weight += weight
        total_value += value * weight
    if total_weight <= 0.0:
        return None
    return total_value / total_weight


def sum_shape(rows, key):
    total = 0.0
    seen = False
    for row in rows:
        value = row["shape"].get(key)
        if value is not None:
            total += value
            seen = True
    return total if seen else None


def min_value(rows, key):
    values = [row["shape"].get(key) for row in rows if row["shape"].get(key) is not None]
    return min(values) if values else None


def unique_strings(rows, key):
    values = {
        row["shape"].get(key)
        for row in rows
        if isinstance(row["shape"].get(key), str) and row["shape"].get(key)
    }
    return sorted(values)


def aggregate_shape_confidence(rows):
    values = unique_strings(rows, "ordered_shape_confidence")
    if not values:
        return None
    ranks = {
        value: index
        for index, value in enumerate(ORDERED_SHAPE_CONFIDENCE_ORDER)
    }
    known = [value for value in values if value in ranks]
    if not known:
        return values[0]
    return min(known, key=lambda value: ranks[value])


def aggregate_rows(rows):
    host_seconds = sum(
        row["host_cpu_merge_seconds"] or 0.0 for row in rows
    )
    state_machine_event_count_total = sum_shape(rows, "state_machine_event_count_total")
    state_machine_event_count_max = max(
        (
            row["shape"].get("state_machine_event_count_max")
            for row in rows
            if row["shape"].get("state_machine_event_count_max") is not None
        ),
        default=None,
    )
    state_machine_count = sum_shape(rows, "state_machine_count")
    state_machine_ideal_parallelism = None
    if (
        state_machine_event_count_total is not None
        and state_machine_event_count_max is not None
        and state_machine_event_count_max > 0.0
    ):
        state_machine_ideal_parallelism = (
            state_machine_event_count_total / state_machine_event_count_max
        )
    state_machine_work_imbalance_ratio = None
    if (
        state_machine_count is not None
        and state_machine_count > 0.0
        and state_machine_event_count_total is not None
        and state_machine_event_count_total > 0.0
        and state_machine_event_count_max is not None
    ):
        state_machine_work_imbalance_ratio = (
            state_machine_event_count_max /
            (state_machine_event_count_total / state_machine_count)
        )
    aggregate = {
        "host_cpu_merge_seconds": host_seconds,
        "host_cpu_merge_share_of_sim_min": min(
            (
                row["host_cpu_merge_share_of_sim"]
                for row in rows
                if row["host_cpu_merge_share_of_sim"] is not None
            ),
            default=None,
        ),
        "candidate_event_count": sum_shape(rows, "candidate_event_count"),
        "summary_count": sum_shape(rows, "summary_count"),
        "ordered_segment_count": sum_shape(rows, "ordered_segment_count"),
        "parallel_segment_count": sum_shape(rows, "parallel_segment_count"),
        "ordered_segment_sources": unique_strings(rows, "ordered_segment_source"),
        "serial_dependency_sources": unique_strings(rows, "serial_dependency_source"),
        "parallelizable_event_sources": unique_strings(rows, "parallelizable_event_source"),
        "ordered_shape_confidence": aggregate_shape_confidence(rows),
        "mean_segment_length": weighted_average(rows, "mean_segment_length", "candidate_event_count"),
        "p90_segment_length": max(
            (
                row["shape"].get("p90_segment_length")
                for row in rows
                if row["shape"].get("p90_segment_length") is not None
            ),
            default=None,
        ),
        "serial_dependency_share": weighted_average(
            rows, "serial_dependency_share", "candidate_event_count"
        ),
        "parallelizable_event_share": weighted_average(
            rows, "parallelizable_event_share", "candidate_event_count"
        ),
        "estimated_d2h_bytes_avoided": sum_shape(rows, "estimated_d2h_bytes_avoided"),
        "estimated_host_rebuild_seconds_avoided": sum_shape(
            rows, "estimated_host_rebuild_seconds_avoided"
        ),
        "estimated_cpu_merge_seconds_avoidable": sum_shape(
            rows, "estimated_cpu_merge_seconds_avoidable"
        ),
        "state_machine_count": state_machine_count,
        "state_machine_nonempty_count": sum_shape(rows, "state_machine_nonempty_count"),
        "state_machine_event_count_total": state_machine_event_count_total,
        "state_machine_event_count_p50": weighted_average(
            rows, "state_machine_event_count_p50", "state_machine_count"
        ),
        "state_machine_event_count_p90": max(
            (
                row["shape"].get("state_machine_event_count_p90")
                for row in rows
                if row["shape"].get("state_machine_event_count_p90") is not None
            ),
            default=None,
        ),
        "state_machine_event_count_p99": max(
            (
                row["shape"].get("state_machine_event_count_p99")
                for row in rows
                if row["shape"].get("state_machine_event_count_p99") is not None
            ),
            default=None,
        ),
        "state_machine_event_count_max": state_machine_event_count_max,
        "state_machine_work_imbalance_ratio": state_machine_work_imbalance_ratio,
        "state_machine_ideal_parallelism": state_machine_ideal_parallelism,
        "candidate_state_bytes_d2h": sum_shape(rows, "candidate_state_bytes_d2h"),
        "missing_required_field_count": sum(
            row["shape"]["missing_required_field_count"] for row in rows
        ),
        "min_parallel_segment_count": min_value(rows, "parallel_segment_count"),
    }
    return aggregate


def inactive_summary(rollup_path, rollup):
    return {
        "decision_status": "inactive",
        "phase": PHASE,
        "telemetry_status": "inactive",
        "device_side_ordered_candidate_maintenance_feasibility": "inactive",
        "recommended_next_action": "return_to_sim_pipeline_budget_rollup",
        "allowed_next_actions": ALLOWED_NEXT_ACTIONS,
        "runtime_prototype_allowed": False,
        "source_sim_pipeline_budget_rollup_decision": str(rollup_path),
        "sim_pipeline_selection_status": rollup.get("selection_status"),
        "sim_pipeline_selected_subcomponent": rollup.get("selected_subcomponent"),
        "workloads": [],
        "aggregate": {},
    }


def active_phase(rollup):
    return (
        rollup.get("runtime_prototype_allowed") is False
        and rollup.get("selection_status") in {"stable_selected", "workload_weighted_selected"}
        and rollup.get("selected_subcomponent") == "host_cpu_merge"
        and rollup.get("recommended_next_action")
        == "profile_device_side_ordered_candidate_maintenance"
    )


def decide(rows, aggregate, args):
    if not rows:
        return (
            "insufficient_telemetry",
            "insufficient_telemetry",
            "collect_ordered_candidate_maintenance_telemetry",
        )
    if aggregate["missing_required_field_count"] > 0:
        return (
            "insufficient_telemetry",
            "insufficient_telemetry",
            "collect_ordered_candidate_maintenance_telemetry",
        )
    if (
        aggregate["host_cpu_merge_share_of_sim_min"] is not None
        and aggregate["host_cpu_merge_share_of_sim_min"]
        < args.host_merge_share_threshold
    ):
        return ("closed", "weak", "stop_host_cpu_merge_work")
    shape_confidence = aggregate.get("ordered_shape_confidence")
    if shape_confidence in {"fallback_conservative", "coarse"}:
        return (
            "closed",
            "weak",
            "refine_ordered_maintenance_shape_telemetry",
        )
    serial_share = aggregate.get("serial_dependency_share")
    parallel_share = aggregate.get("parallelizable_event_share")
    if (
        shape_confidence in {"event_level", "validated"}
        and serial_share is not None
        and serial_share >= args.serial_dependency_stop_threshold
        and parallel_share is not None
        and parallel_share <= args.parallelizable_stop_threshold
    ):
        return (
            "closed",
            "blocked_by_order_dependency",
            "stop_or_rethink_device_side_ordered_candidate_maintenance",
        )
    avoidable = aggregate.get("estimated_cpu_merge_seconds_avoidable")
    if (
        parallel_share is not None
        and parallel_share >= args.parallelizable_threshold
        and avoidable is not None
        and avoidable > 0.0
    ):
        feasibility = "strong" if parallel_share >= 0.70 else "plausible"
        return (
            "closed",
            feasibility,
            "design_device_side_ordered_candidate_maintenance_shadow",
        )
    if aggregate.get("estimated_d2h_bytes_avoided"):
        return (
            "closed",
            "plausible",
            "profile_device_resident_state_handoff_with_ordered_maintenance",
        )
    return ("closed", "weak", "collect_more_ordered_maintenance_shape")


def build_summary(rollup, rollup_path, args):
    if not active_phase(rollup):
        return inactive_summary(rollup_path, rollup)
    rows = workload_rows_from_rollup(rollup)
    aggregate = aggregate_rows(rows)
    telemetry_status, feasibility, recommended_next_action = decide(rows, aggregate, args)
    return {
        "decision_status": "ready",
        "phase": PHASE,
        "telemetry_status": telemetry_status,
        "device_side_ordered_candidate_maintenance_feasibility": feasibility,
        "recommended_next_action": recommended_next_action,
        "allowed_next_actions": ALLOWED_NEXT_ACTIONS,
        "runtime_prototype_allowed": False,
        "source_sim_pipeline_budget_rollup_decision": str(rollup_path),
        "sim_pipeline_selection_status": rollup.get("selection_status"),
        "sim_pipeline_selected_subcomponent": rollup.get("selected_subcomponent"),
        "missing_required_field_count": aggregate["missing_required_field_count"],
        "workload_count": len(rows),
        "workloads": rows,
        "aggregate": aggregate,
    }


def case_row_for(row):
    shape = row["shape"]
    values = {
        "workload_id": row["workload_id"],
        "workload_class": row["workload_class"],
        "host_cpu_merge_seconds": format_number(row["host_cpu_merge_seconds"]),
        "host_cpu_merge_share_of_sim": format_number(
            row["host_cpu_merge_share_of_sim"]
        ),
        "host_cpu_merge_share_of_total": format_number(
            row["host_cpu_merge_share_of_total"]
        ),
        "missing_required_field_count": str(shape["missing_required_field_count"]),
    }
    for key in CASE_FIELDS:
        if key in values:
            continue
        value = shape.get(key)
        if isinstance(value, str):
            values[key] = value
        else:
            values[key] = format_number(value)
    return values


def write_cases_tsv(path, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CASE_FIELDS, delimiter="\t")
        writer.writeheader()
        for row in rows:
            writer.writerow(case_row_for(row))


def render_markdown(summary):
    lines = [
        "# LongTarget Ordered Candidate Maintenance Budget",
        "",
        f"- phase: `{summary['phase']}`",
        f"- decision_status: `{summary['decision_status']}`",
        f"- telemetry_status: `{summary['telemetry_status']}`",
        "- device_side_ordered_candidate_maintenance_feasibility: "
        f"`{summary['device_side_ordered_candidate_maintenance_feasibility']}`",
        f"- recommended_next_action: `{summary['recommended_next_action']}`",
        f"- runtime_prototype_allowed: `{str(summary['runtime_prototype_allowed']).lower()}`",
        "",
        "| workload | host_cpu_merge_share_of_sim | missing_required_field_count |",
        "| --- | ---: | ---: |",
    ]
    for row in summary.get("workloads", []):
        lines.append(
            "| "
            + f"{row['workload_id']} | "
            + f"{format_number(row['host_cpu_merge_share_of_sim'])} | "
            + f"{row['shape']['missing_required_field_count']} |"
        )
    lines.append("")
    return "\n".join(lines)


def decision_from(summary):
    return {
        "decision_status": summary["decision_status"],
        "phase": summary["phase"],
        "telemetry_status": summary["telemetry_status"],
        "device_side_ordered_candidate_maintenance_feasibility": summary[
            "device_side_ordered_candidate_maintenance_feasibility"
        ],
        "recommended_next_action": summary["recommended_next_action"],
        "allowed_next_actions": summary["allowed_next_actions"],
        "runtime_prototype_allowed": summary["runtime_prototype_allowed"],
        "source_sim_pipeline_budget_rollup_decision": summary[
            "source_sim_pipeline_budget_rollup_decision"
        ],
        "sim_pipeline_selection_status": summary["sim_pipeline_selection_status"],
        "sim_pipeline_selected_subcomponent": summary[
            "sim_pipeline_selected_subcomponent"
        ],
        "missing_required_field_count": summary.get("missing_required_field_count", 0),
        "workload_count": summary.get("workload_count", 0),
        "aggregate": summary.get("aggregate", {}),
        "cases_tsv": summary.get("cases_tsv"),
    }


def write_outputs(output_dir, summary):
    output_dir.mkdir(parents=True, exist_ok=True)
    cases_path = output_dir / "ordered_candidate_maintenance_budget_cases.tsv"
    write_cases_tsv(cases_path, summary.get("workloads", []))
    summary["cases_tsv"] = str(cases_path)

    with (output_dir / "ordered_candidate_maintenance_budget_summary.json").open(
        "w", encoding="utf-8"
    ) as handle:
        json.dump(summary, handle, indent=2, sort_keys=True)
        handle.write("\n")
    with (output_dir / "ordered_candidate_maintenance_budget_decision.json").open(
        "w", encoding="utf-8"
    ) as handle:
        json.dump(decision_from(summary), handle, indent=2, sort_keys=True)
        handle.write("\n")
    (output_dir / "ordered_candidate_maintenance_budget.md").write_text(
        render_markdown(summary), encoding="utf-8"
    )


def main():
    args = parse_args()
    rollup, rollup_path = read_json(args.sim_pipeline_budget_rollup_decision)
    summary = build_summary(rollup, rollup_path, args)
    write_outputs(Path(args.output_dir), summary)


if __name__ == "__main__":
    main()
