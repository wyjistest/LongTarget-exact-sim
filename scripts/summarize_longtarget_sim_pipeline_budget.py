#!/usr/bin/env python3
import argparse
import csv
import json
from pathlib import Path


ALLOWED_NEXT_ACTIONS = [
    "collect_sim_substage_telemetry",
    "profile_device_resident_state_handoff",
    "profile_device_side_ordered_candidate_maintenance",
    "profile_sim_initial_scan_kernel",
    "profile_locate_traceback_pipeline",
    "stop_sim_pipeline_work",
]

SUBCOMPONENTS = {
    "state_handoff": {
        "keys": (
            "sim_initial_scan_d2h_seconds",
            "candidate_state_handoff_seconds",
            "host_rebuild_seconds",
            "sim_initial_candidate_state_rebuild_seconds",
            "sim_safe_store_handoff_seconds",
        ),
        "projected_keys": (
            "projected_sim_initial_scan_d2h_seconds",
            "projected_candidate_state_handoff_seconds",
            "projected_host_rebuild_seconds",
            "projected_sim_initial_candidate_state_rebuild_seconds",
            "projected_sim_safe_store_handoff_seconds",
        ),
        "recommended_action": "profile_device_resident_state_handoff",
    },
    "host_cpu_merge": {
        "keys": ("sim_initial_scan_cpu_merge_seconds",),
        "projected_keys": ("projected_sim_initial_scan_cpu_merge_seconds",),
        "recommended_action": "profile_device_side_ordered_candidate_maintenance",
    },
    "gpu_compute": {
        "keys": ("sim_initial_scan_gpu_seconds", "gpu_kernel_seconds"),
        "projected_keys": (
            "projected_sim_initial_scan_gpu_seconds",
            "projected_gpu_kernel_seconds",
        ),
        "recommended_action": "profile_sim_initial_scan_kernel",
    },
    "locate_traceback": {
        "keys": (
            "sim_locate_seconds",
            "sim_traceback_seconds",
            "sim_output_materialization_seconds",
        ),
        "projected_keys": (
            "projected_sim_locate_seconds",
            "projected_sim_traceback_seconds",
            "projected_sim_output_materialization_seconds",
        ),
        "recommended_action": "profile_locate_traceback_pipeline",
    },
}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Summarize a device-resident SIM pipeline budget."
    )
    parser.add_argument(
        "--top-level-budget-decision",
        required=True,
        help="top_level_perf_budget_decision.json that selected SIM.",
    )
    parser.add_argument(
        "--input-budget",
        required=True,
        help="JSON report with SIM pipeline seconds or projected seconds.",
    )
    parser.add_argument(
        "--dominance-share-threshold",
        type=float,
        default=0.40,
        help="Share of SIM seconds required to select a subcomponent.",
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


def first_number(data, keys):
    for key in keys:
        value = number_or_none(data.get(key))
        if value is not None:
            return value
    return None


def sum_keys(data, keys):
    total = 0.0
    seen = False
    for key in keys:
        value = number_or_none(data.get(key))
        if value is not None and value > 0.0:
            total += value
            seen = True
    return total if seen else None


def top_level_selects_sim(top_level_decision):
    if not isinstance(top_level_decision, dict):
        return False
    if top_level_decision.get("runtime_prototype_allowed") is True:
        return False
    return (
        top_level_decision.get("selected_component") == "sim"
        and top_level_decision.get("recommended_next_action")
        == "profile_device_resident_sim_pipeline"
    )


def total_seconds_from(data):
    return first_number(data, ("total_seconds", "projected_total_seconds"))


def sim_seconds_from(data):
    return first_number(data, ("sim_seconds", "projected_sim_seconds"))


def case_rows_from(data):
    raw_cases = data.get("cases")
    if isinstance(raw_cases, list):
        rows = []
        for index, raw_case in enumerate(raw_cases):
            if isinstance(raw_case, dict):
                case = dict(raw_case)
                case.setdefault("case_id", f"case-{index:06d}")
                rows.append(case)
        if rows:
            return rows
    case = dict(data)
    case.setdefault("case_id", "aggregate")
    return [case]


def subcomponent_seconds_from(data, spec):
    regular = sum_keys(data, spec["keys"])
    projected = sum_keys(data, spec["projected_keys"])
    if projected is not None:
        return projected
    return regular


def max_speedup_if_removed(base_seconds, seconds):
    if base_seconds is None or base_seconds <= 0.0:
        return None
    remaining = base_seconds - seconds
    if remaining <= 0.0:
        return None
    return base_seconds / remaining


def build_case_tsv_rows(cases, sim_seconds):
    rows = []
    for raw_case in cases:
        case_id = str(raw_case.get("case_id", "aggregate"))
        case_sim_seconds = sim_seconds_from(raw_case) or sim_seconds
        for subcomponent, spec in SUBCOMPONENTS.items():
            seconds = subcomponent_seconds_from(raw_case, spec)
            if seconds is None:
                continue
            rows.append(
                {
                    "case_id": case_id,
                    "subcomponent": subcomponent,
                    "seconds": seconds,
                    "share_of_sim_seconds": (
                        seconds / case_sim_seconds
                        if case_sim_seconds and case_sim_seconds > 0.0
                        else 0.0
                    ),
                }
            )
    return rows


def sum_subcomponent_from_cases(cases, spec):
    total = 0.0
    seen = False
    for raw_case in cases:
        seconds = subcomponent_seconds_from(raw_case, spec)
        if seconds is not None:
            total += seconds
            seen = True
    return total if seen else None


def inactive_summary(top_level_path, input_path):
    return {
        "decision_status": "inactive",
        "phase": "device_resident_sim_pipeline_budget",
        "selection_status": "inactive",
        "selected_subcomponent": None,
        "recommended_next_action": "return_to_top_level_budget",
        "allowed_next_actions": ALLOWED_NEXT_ACTIONS,
        "runtime_prototype_allowed": False,
        "source_top_level_budget_decision": str(top_level_path),
        "source_input_budget": str(input_path),
        "subcomponents": [],
        "cases_tsv": None,
    }


def build_summary(top_level_decision, top_level_path, data, input_path, threshold):
    if not top_level_selects_sim(top_level_decision):
        return inactive_summary(top_level_path, input_path)

    sim_seconds = sim_seconds_from(data)
    if sim_seconds is None or sim_seconds <= 0.0:
        raise SystemExit("sim_seconds/projected_sim_seconds must be > 0")
    total_seconds = total_seconds_from(data) or sim_seconds
    cases = case_rows_from(data)

    subcomponents = []
    for name, spec in SUBCOMPONENTS.items():
        seconds = subcomponent_seconds_from(data, spec)
        if seconds is None:
            seconds = sum_subcomponent_from_cases(cases, spec)
        if seconds is None:
            seconds = 0.0
            evidence_status = "missing"
        else:
            evidence_status = "provided"
        share_of_sim = seconds / sim_seconds if sim_seconds > 0.0 else 0.0
        share_of_total = seconds / total_seconds if total_seconds > 0.0 else 0.0
        subcomponents.append(
            {
                "subcomponent": name,
                "seconds": seconds,
                "share_of_sim_seconds": share_of_sim,
                "share_of_total_seconds": share_of_total,
                "max_sim_speedup_if_removed": max_speedup_if_removed(
                    sim_seconds, seconds
                ),
                "max_total_speedup_if_removed": max_speedup_if_removed(
                    total_seconds, seconds
                ),
                "evidence_status": evidence_status,
                "recommended_action": spec["recommended_action"],
            }
        )
    subcomponents.sort(key=lambda row: (-row["seconds"], row["subcomponent"]))

    provided = [row for row in subcomponents if row["evidence_status"] == "provided"]
    selected = provided[0] if provided and provided[0]["share_of_sim_seconds"] >= threshold else None
    if not provided:
        selected_subcomponent = None
        recommended_next_action = "collect_sim_substage_telemetry"
        selection_status = "insufficient_sim_substage_telemetry"
    elif selected is None:
        selected_subcomponent = None
        recommended_next_action = "stop_sim_pipeline_work"
        selection_status = "no_stable_subcomponent"
    else:
        selected_subcomponent = selected["subcomponent"]
        recommended_next_action = selected["recommended_action"]
        selection_status = "selected"

    case_rows = build_case_tsv_rows(cases, sim_seconds)
    return {
        "decision_status": "ready",
        "phase": "device_resident_sim_pipeline_budget",
        "selection_status": selection_status,
        "total_seconds": total_seconds,
        "sim_seconds": sim_seconds,
        "dominance_share_threshold": threshold,
        "provided_subcomponent_count": len(provided),
        "selected_subcomponent": selected_subcomponent,
        "recommended_next_action": recommended_next_action,
        "allowed_next_actions": ALLOWED_NEXT_ACTIONS,
        "runtime_prototype_allowed": False,
        "source_top_level_budget_decision": str(top_level_path),
        "source_input_budget": str(input_path),
        "subcomponents": subcomponents,
        "case_rows": case_rows,
    }


def render_markdown(summary):
    lines = [
        "# LongTarget SIM Pipeline Budget",
        "",
        f"- phase: `{summary['phase']}`",
        f"- decision_status: `{summary['decision_status']}`",
        f"- selection_status: `{summary.get('selection_status') or 'unknown'}`",
        f"- selected_subcomponent: `{summary.get('selected_subcomponent') or 'none'}`",
        f"- recommended_next_action: `{summary['recommended_next_action']}`",
        f"- runtime_prototype_allowed: `{str(summary['runtime_prototype_allowed']).lower()}`",
        "",
        "| subcomponent | seconds | share_of_sim_seconds | share_of_total_seconds | evidence_status | recommended_action |",
        "| --- | ---: | ---: | ---: | --- | --- |",
    ]
    for row in summary.get("subcomponents", []):
        lines.append(
            "| "
            + f"{row['subcomponent']} | "
            + f"{row['seconds']:.6f} | "
            + f"{row['share_of_sim_seconds']:.6f} | "
            + f"{row['share_of_total_seconds']:.6f} | "
            + f"{row['evidence_status']} | "
            + f"{row['recommended_action']} |"
        )
    lines.append("")
    return "\n".join(lines)


def write_cases_tsv(path, case_rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=(
                "case_id",
                "subcomponent",
                "seconds",
                "share_of_sim_seconds",
            ),
            delimiter="\t",
        )
        writer.writeheader()
        for row in case_rows:
            writer.writerow(row)


def main():
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    top_level_decision, top_level_path = read_json(args.top_level_budget_decision)
    data, input_path = read_json(args.input_budget)
    summary = build_summary(
        top_level_decision,
        top_level_path,
        data,
        input_path,
        args.dominance_share_threshold,
    )

    cases_path = output_dir / "sim_pipeline_budget_cases.tsv"
    case_rows = summary.pop("case_rows", [])
    write_cases_tsv(cases_path, case_rows)
    summary["cases_tsv"] = str(cases_path)

    decision = {
        "decision_status": summary["decision_status"],
        "phase": summary["phase"],
        "selection_status": summary["selection_status"],
        "selected_subcomponent": summary["selected_subcomponent"],
        "recommended_next_action": summary["recommended_next_action"],
        "allowed_next_actions": summary["allowed_next_actions"],
        "runtime_prototype_allowed": summary["runtime_prototype_allowed"],
        "source_top_level_budget_decision": summary[
            "source_top_level_budget_decision"
        ],
        "source_input_budget": summary["source_input_budget"],
    }

    with (output_dir / "sim_pipeline_budget.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2, sort_keys=True)
        handle.write("\n")
    with (output_dir / "sim_pipeline_budget_decision.json").open(
        "w", encoding="utf-8"
    ) as handle:
        json.dump(decision, handle, indent=2, sort_keys=True)
        handle.write("\n")
    (output_dir / "sim_pipeline_budget.md").write_text(
        render_markdown(summary), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
