#!/usr/bin/env python3
import argparse
import json
from pathlib import Path


ALLOWED_NEXT_ACTIONS = [
    "profile_calc_score_path",
    "profile_device_resident_sim_pipeline",
    "profile_d2h_handoff_path",
    "profile_safe_store_or_locate_path",
    "stop_candidate_index_work",
]

COMPONENT_ACTIONS = {
    "calc_score": "profile_calc_score_path",
    "sim": "profile_device_resident_sim_pipeline",
    "sim_initial_scan": "profile_device_resident_sim_pipeline",
    "sim_initial_scan_cpu_merge": "profile_device_resident_sim_pipeline",
    "sim_initial_scan_d2h": "profile_d2h_handoff_path",
    "d2h_handoff": "profile_d2h_handoff_path",
    "safe_store": "profile_safe_store_or_locate_path",
    "traceback_locate": "profile_safe_store_or_locate_path",
    "traceback": "profile_safe_store_or_locate_path",
    "locate": "profile_safe_store_or_locate_path",
    "postprocess": "profile_safe_store_or_locate_path",
    "gpu_kernel": "profile_device_resident_sim_pipeline",
    "cpu_fallback": "profile_device_resident_sim_pipeline",
    "candidate_index": "stop_candidate_index_work",
}

PROJECTED_COMPONENT_KEYS = {
    "calc_score": ("projected_calc_score_seconds", "calc_score_seconds"),
    "sim": ("projected_sim_seconds", "sim_seconds"),
    "sim_initial_scan": (
        "projected_sim_initial_scan_seconds",
        "sim_initial_scan_seconds",
    ),
    "sim_initial_scan_d2h": (
        "projected_sim_initial_scan_d2h_seconds",
        "sim_initial_scan_d2h_seconds",
        "projected_d2h_seconds",
        "d2h_seconds",
    ),
    "sim_initial_scan_cpu_merge": (
        "projected_sim_initial_scan_cpu_merge_seconds",
        "sim_initial_scan_cpu_merge_seconds",
    ),
    "candidate_index": ("projected_candidate_index_seconds", "candidate_index_seconds"),
    "safe_store": ("projected_safe_store_seconds", "safe_store_seconds"),
    "traceback_locate": (
        "projected_traceback_locate_seconds",
        "traceback_locate_seconds",
    ),
    "gpu_kernel": ("projected_gpu_kernel_seconds", "gpu_kernel_seconds"),
    "cpu_fallback": ("projected_cpu_fallback_seconds", "cpu_fallback_seconds"),
    "postprocess": ("projected_postprocess_seconds", "postprocess_seconds"),
}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Summarize a top-level LongTarget optimization budget."
    )
    parser.add_argument(
        "--input-budget",
        required=True,
        help="JSON budget or project_whole_genome_runtime report.",
    )
    parser.add_argument(
        "--candidate-index-branch-rollup-decision",
        help="Optional branch_rollup_decision.json that marks candidate-index profiling stopped.",
    )
    parser.add_argument(
        "--material-share-threshold",
        type=float,
        default=0.10,
        help="Share of total seconds required to mark a component material.",
    )
    parser.add_argument("--output-dir", required=True, help="Output directory.")
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


def total_seconds_from(data, components):
    for key in ("total_seconds", "projected_total_seconds", "sample_total_seconds"):
        value = number_or_none(data.get(key))
        if value is not None and value > 0.0:
            return value
    return sum(max(0.0, seconds) for seconds in components.values())


def component_value(raw):
    value = number_or_none(raw)
    if value is not None:
        return value
    if isinstance(raw, dict):
        for key in ("seconds", "projected_seconds", "mean_seconds"):
            value = number_or_none(raw.get(key))
            if value is not None:
                return value
    return None


def components_from_explicit(data):
    raw_components = data.get("components")
    components = {}
    if isinstance(raw_components, dict):
        for name, raw_value in raw_components.items():
            seconds = component_value(raw_value)
            if seconds is not None and seconds > 0.0:
                components[str(name)] = seconds
    elif isinstance(raw_components, list):
        for raw_value in raw_components:
            if not isinstance(raw_value, dict):
                continue
            name = raw_value.get("component") or raw_value.get("name")
            seconds = component_value(raw_value)
            if name and seconds is not None and seconds > 0.0:
                components[str(name)] = seconds
    return components


def first_available_seconds(data, keys):
    for key in keys:
        value = number_or_none(data.get(key))
        if value is not None and value > 0.0:
            return value
    return None


def components_from_projected_report(data):
    components = {}
    for component, keys in PROJECTED_COMPONENT_KEYS.items():
        seconds = first_available_seconds(data, keys)
        if seconds is not None:
            components[component] = seconds
    return components


def candidate_index_is_stopped(branch_rollup_decision):
    if not isinstance(branch_rollup_decision, dict):
        return False
    if branch_rollup_decision.get("runtime_prototype_allowed") is True:
        return False
    stopped_markers = {
        branch_rollup_decision.get("recommended_next_action"),
        branch_rollup_decision.get("leaf_level_candidate_index_profiling_status"),
        branch_rollup_decision.get("current_phase_status"),
        branch_rollup_decision.get("stop_reason"),
    }
    return bool(
        {
            "stop_leaf_level_candidate_index_profiling",
            "stop_candidate_index_structural_profiling",
            "stopped",
            "no_stable_structural_signal",
            "no_single_stable_leaf_found_under_current_profiler",
        }
        & {str(value) for value in stopped_markers if value is not None}
    )


def max_speedup_if_removed(total_seconds, seconds):
    if total_seconds <= 0.0 or seconds < 0.0:
        return None
    remaining = total_seconds - seconds
    if remaining <= 0.0:
        return None
    return total_seconds / remaining


def row_for_component(
    component,
    seconds,
    total_seconds,
    material_share_threshold,
    candidate_index_stopped,
):
    share = seconds / total_seconds if total_seconds > 0.0 else 0.0
    material = share >= material_share_threshold
    recommended_action = COMPONENT_ACTIONS.get(component, "profile_device_resident_sim_pipeline")
    status = "material" if material else "context"
    eligible_for_selection = material
    candidate_index_policy = None

    if component == "candidate_index" and candidate_index_stopped:
        status = "known_material_but_no_actionable_leaf"
        recommended_action = "stop_candidate_index_work"
        eligible_for_selection = False
        candidate_index_policy = "do_not_continue_leaf_split"

    row = {
        "component": component,
        "seconds": seconds,
        "share_of_total": share,
        "max_speedup_if_removed": max_speedup_if_removed(total_seconds, seconds),
        "material": material,
        "status": status,
        "recommended_action": recommended_action,
        "eligible_for_selection": eligible_for_selection,
    }
    if candidate_index_policy is not None:
        row["candidate_index_policy"] = candidate_index_policy
    return row


def build_budget(data, source_path, branch_rollup_decision, branch_rollup_path, threshold):
    components = components_from_explicit(data)
    if not components:
        components = components_from_projected_report(data)
    total_seconds = total_seconds_from(data, components)
    if total_seconds <= 0.0:
        raise SystemExit("top-level total_seconds must be > 0")

    candidate_index_stopped = candidate_index_is_stopped(branch_rollup_decision)
    rows = [
        row_for_component(
            component,
            seconds,
            total_seconds,
            threshold,
            candidate_index_stopped,
        )
        for component, seconds in components.items()
        if seconds > 0.0
    ]
    rows.sort(key=lambda row: (-row["seconds"], row["component"]))

    eligible_rows = [row for row in rows if row["eligible_for_selection"]]
    selected = eligible_rows[0] if eligible_rows else None
    if selected is None and any(row["component"] == "candidate_index" for row in rows):
        recommended_next_action = "stop_candidate_index_work"
        selected_component = "candidate_index"
    elif selected is None:
        recommended_next_action = "profile_device_resident_sim_pipeline"
        selected_component = None
    else:
        recommended_next_action = selected["recommended_action"]
        selected_component = selected["component"]

    summary = {
        "decision_status": "ready",
        "phase": "top_level_optimization_budget_reset",
        "total_seconds": total_seconds,
        "component_count": len(rows),
        "material_share_threshold": threshold,
        "components": rows,
        "selected_component": selected_component,
        "recommended_next_action": recommended_next_action,
        "allowed_next_actions": ALLOWED_NEXT_ACTIONS,
        "candidate_index_work_status": (
            "known_material_but_no_actionable_leaf"
            if candidate_index_stopped
            else "not_classified_by_branch_rollup"
        ),
        "runtime_prototype_allowed": False,
        "source_input_budget": str(source_path),
    }
    if branch_rollup_path is not None:
        summary["source_candidate_index_branch_rollup_decision"] = str(branch_rollup_path)
    return summary


def render_markdown(summary):
    lines = [
        "# LongTarget Top-Level Performance Budget",
        "",
        f"- phase: `{summary['phase']}`",
        f"- total_seconds: `{summary['total_seconds']:.6f}`",
        f"- selected_component: `{summary.get('selected_component') or 'none'}`",
        f"- recommended_next_action: `{summary['recommended_next_action']}`",
        f"- candidate_index_work_status: `{summary['candidate_index_work_status']}`",
        f"- runtime_prototype_allowed: `{str(summary['runtime_prototype_allowed']).lower()}`",
        "",
        "| component | seconds | share_of_total | max_speedup_if_removed | status | recommended_action | eligible |",
        "| --- | ---: | ---: | ---: | --- | --- | --- |",
    ]
    for row in summary["components"]:
        speedup = row.get("max_speedup_if_removed")
        speedup_text = "" if speedup is None else f"{speedup:.6f}"
        lines.append(
            "| "
            + f"{row['component']} | "
            + f"{row['seconds']:.6f} | "
            + f"{row['share_of_total']:.6f} | "
            + f"{speedup_text} | "
            + f"{row['status']} | "
            + f"{row['recommended_action']} | "
            + f"{str(row['eligible_for_selection']).lower()} |"
        )
    lines.append("")
    return "\n".join(lines)


def main():
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    data, source_path = read_json(args.input_budget)
    branch_rollup_decision = {}
    branch_rollup_path = None
    if args.candidate_index_branch_rollup_decision:
        branch_rollup_decision, branch_rollup_path = read_json(
            args.candidate_index_branch_rollup_decision
        )

    summary = build_budget(
        data,
        source_path,
        branch_rollup_decision,
        branch_rollup_path,
        args.material_share_threshold,
    )
    decision = {
        "decision_status": summary["decision_status"],
        "phase": summary["phase"],
        "selected_component": summary["selected_component"],
        "recommended_next_action": summary["recommended_next_action"],
        "allowed_next_actions": summary["allowed_next_actions"],
        "candidate_index_work_status": summary["candidate_index_work_status"],
        "runtime_prototype_allowed": summary["runtime_prototype_allowed"],
        "source_input_budget": summary["source_input_budget"],
    }
    if "source_candidate_index_branch_rollup_decision" in summary:
        decision["source_candidate_index_branch_rollup_decision"] = summary[
            "source_candidate_index_branch_rollup_decision"
        ]

    with (output_dir / "top_level_perf_budget.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2, sort_keys=True)
        handle.write("\n")
    with (output_dir / "top_level_perf_budget_decision.json").open(
        "w", encoding="utf-8"
    ) as handle:
        json.dump(decision, handle, indent=2, sort_keys=True)
        handle.write("\n")
    (output_dir / "top_level_perf_budget.md").write_text(
        render_markdown(summary), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
