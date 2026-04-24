#!/usr/bin/env python3
import argparse
import json
from collections import Counter
from pathlib import Path


ALLOWED_NEXT_ACTIONS = [
    "collect_sim_substage_telemetry",
    "profile_device_resident_state_handoff",
    "profile_device_side_ordered_candidate_maintenance",
    "profile_sim_initial_scan_kernel",
    "profile_locate_traceback_pipeline",
    "stop_sim_pipeline_work",
    "expand_or_stratify_sim_pipeline_budget",
]


def parse_args():
    parser = argparse.ArgumentParser(
        description="Roll up SIM pipeline budget decisions across workloads."
    )
    parser.add_argument(
        "--sim-pipeline-budget-decision",
        action="append",
        required=True,
        help="sim_pipeline_budget_decision.json for one workload. Repeat per workload.",
    )
    parser.add_argument("--output-dir", required=True, help="Output directory.")
    return parser.parse_args()


def read_json(path):
    source = Path(path)
    with source.open("r", encoding="utf-8") as handle:
        return json.load(handle), source


def workload_id_from(decision, source, index):
    raw = decision.get("workload_id")
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    if source.parent.name == "sim_pipeline_budget" and source.parent.parent.name:
        return source.parent.parent.name
    return f"{source.stem or 'workload'}-{index:06d}"


def normalize_workload_decision(decision, source, index):
    return {
        "workload_id": workload_id_from(decision, source, index),
        "decision_status": decision.get("decision_status"),
        "selection_status": decision.get("selection_status"),
        "selected_subcomponent": decision.get("selected_subcomponent"),
        "recommended_next_action": decision.get("recommended_next_action"),
        "runtime_prototype_allowed": decision.get("runtime_prototype_allowed"),
        "source_sim_pipeline_budget_decision": str(source),
    }


def unique_workload_key(workload_id, used):
    if workload_id not in used:
        used.add(workload_id)
        return workload_id
    suffix = 2
    while f"{workload_id}-{suffix}" in used:
        suffix += 1
    key = f"{workload_id}-{suffix}"
    used.add(key)
    return key


def load_workload_decisions(paths):
    workloads = []
    used = set()
    for index, raw_path in enumerate(paths):
        decision, source = read_json(raw_path)
        normalized = normalize_workload_decision(decision, source, index)
        normalized["workload_key"] = unique_workload_key(
            normalized["workload_id"], used
        )
        workloads.append(normalized)
    return workloads


def selected_key(workload):
    return (
        workload.get("selected_subcomponent"),
        workload.get("recommended_next_action"),
    )


def build_rollup(workloads):
    if not workloads:
        raise SystemExit("at least one --sim-pipeline-budget-decision is required")

    status_counts = Counter(row.get("selection_status") or "unknown" for row in workloads)
    any_insufficient = any(
        row.get("selection_status") == "insufficient_sim_substage_telemetry"
        for row in workloads
    )
    all_selected = all(row.get("selection_status") == "selected" for row in workloads)
    all_no_stable = all(
        row.get("selection_status") == "no_stable_subcomponent" for row in workloads
    )
    selected_pairs = {selected_key(row) for row in workloads if row.get("selection_status") == "selected"}

    if any_insufficient:
        selection_status = "insufficient_sim_substage_telemetry"
        selected_subcomponent = None
        recommended_next_action = "collect_sim_substage_telemetry"
    elif all_selected and len(selected_pairs) == 1:
        selection_status = "stable_selected"
        selected_subcomponent, recommended_next_action = next(iter(selected_pairs))
    elif all_no_stable:
        selection_status = "no_stable_subcomponent"
        selected_subcomponent = None
        recommended_next_action = "stop_sim_pipeline_work"
    else:
        selection_status = "workload_dependent_subcomponent"
        selected_subcomponent = None
        recommended_next_action = "expand_or_stratify_sim_pipeline_budget"

    workload_decisions = {
        row["workload_key"]: {
            "workload_id": row["workload_id"],
            "decision_status": row["decision_status"],
            "selection_status": row["selection_status"],
            "selected_subcomponent": row["selected_subcomponent"],
            "recommended_next_action": row["recommended_next_action"],
            "runtime_prototype_allowed": row["runtime_prototype_allowed"],
            "source_sim_pipeline_budget_decision": row[
                "source_sim_pipeline_budget_decision"
            ],
        }
        for row in workloads
    }

    return {
        "decision_status": "ready",
        "phase": "device_resident_sim_pipeline_budget_rollup",
        "selection_status": selection_status,
        "selected_subcomponent": selected_subcomponent,
        "recommended_next_action": recommended_next_action,
        "allowed_next_actions": ALLOWED_NEXT_ACTIONS,
        "runtime_prototype_allowed": False,
        "workload_count": len(workloads),
        "selection_status_counts": dict(sorted(status_counts.items())),
        "workload_decisions": workload_decisions,
    }


def render_markdown(summary):
    lines = [
        "# LongTarget SIM Pipeline Budget Roll-Up",
        "",
        f"- phase: `{summary['phase']}`",
        f"- decision_status: `{summary['decision_status']}`",
        f"- selection_status: `{summary['selection_status']}`",
        f"- selected_subcomponent: `{summary.get('selected_subcomponent') or 'none'}`",
        f"- recommended_next_action: `{summary['recommended_next_action']}`",
        f"- runtime_prototype_allowed: `{str(summary['runtime_prototype_allowed']).lower()}`",
        f"- workload_count: `{summary['workload_count']}`",
        "",
        "| workload | selection_status | selected_subcomponent | recommended_next_action |",
        "| --- | --- | --- | --- |",
    ]
    for workload_id, decision in sorted(summary["workload_decisions"].items()):
        lines.append(
            "| "
            + f"{workload_id} | "
            + f"{decision.get('selection_status') or 'unknown'} | "
            + f"{decision.get('selected_subcomponent') or 'none'} | "
            + f"{decision.get('recommended_next_action') or 'unknown'} |"
        )
    lines.append("")
    return "\n".join(lines)


def write_outputs(output_dir, summary):
    output_dir.mkdir(parents=True, exist_ok=True)
    decision = {
        "decision_status": summary["decision_status"],
        "phase": summary["phase"],
        "selection_status": summary["selection_status"],
        "selected_subcomponent": summary["selected_subcomponent"],
        "recommended_next_action": summary["recommended_next_action"],
        "allowed_next_actions": summary["allowed_next_actions"],
        "runtime_prototype_allowed": summary["runtime_prototype_allowed"],
        "workload_count": summary["workload_count"],
        "workload_decisions": summary["workload_decisions"],
    }
    with (output_dir / "sim_pipeline_budget_rollup.json").open(
        "w", encoding="utf-8"
    ) as handle:
        json.dump(summary, handle, indent=2, sort_keys=True)
        handle.write("\n")
    with (output_dir / "sim_pipeline_budget_rollup_decision.json").open(
        "w", encoding="utf-8"
    ) as handle:
        json.dump(decision, handle, indent=2, sort_keys=True)
        handle.write("\n")
    (output_dir / "sim_pipeline_budget_rollup.md").write_text(
        render_markdown(summary), encoding="utf-8"
    )


def main():
    args = parse_args()
    workloads = load_workload_decisions(args.sim_pipeline_budget_decision)
    summary = build_rollup(workloads)
    write_outputs(Path(args.output_dir), summary)


if __name__ == "__main__":
    main()
