#!/usr/bin/env python3
import argparse
import csv
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

SUBCOMPONENT_COLUMNS = {
    "state_handoff": "state_handoff",
    "host_cpu_merge": "host_cpu_merge_or_rebuild",
    "gpu_compute": "gpu_compute",
    "locate_traceback": "locate_traceback_safe_store",
}

CASE_TSV_FIELDS = [
    "workload_id",
    "workload_class",
    "selection_status",
    "selected_subcomponent",
    "recommended_next_action",
    "sim_seconds",
    "total_seconds",
    "state_handoff_share_of_sim",
    "host_cpu_merge_or_rebuild_share_of_sim",
    "gpu_compute_share_of_sim",
    "locate_traceback_safe_store_share_of_sim",
    "state_handoff_share_of_total",
    "host_cpu_merge_or_rebuild_share_of_total",
    "gpu_compute_share_of_total",
    "locate_traceback_safe_store_share_of_total",
    "missing_required_field_count",
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


def sibling_summary_path(decision_source):
    return decision_source.with_name("sim_pipeline_budget.json")


def read_optional_summary(decision_source):
    source = sibling_summary_path(decision_source)
    if not source.exists():
        return None, source
    with source.open("r", encoding="utf-8") as handle:
        return json.load(handle), source


def number_or_none(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def workload_id_from(decision, source, index):
    raw = decision.get("workload_id")
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    if source.parent.name == "sim_pipeline_budget" and source.parent.parent.name:
        return source.parent.parent.name
    return f"{source.stem or 'workload'}-{index:06d}"


def subcomponent_share_map(summary):
    shares = {}
    if not isinstance(summary, dict):
        return shares
    for row in summary.get("subcomponents", []):
        if not isinstance(row, dict):
            continue
        subcomponent = row.get("subcomponent")
        if subcomponent not in SUBCOMPONENT_COLUMNS:
            continue
        shares[subcomponent] = {
            "share_of_sim": number_or_none(row.get("share_of_sim_seconds")),
            "share_of_total": number_or_none(row.get("share_of_total_seconds")),
            "evidence_status": row.get("evidence_status"),
        }
    return shares


def missing_required_field_count(shares):
    missing = 0
    for subcomponent in SUBCOMPONENT_COLUMNS:
        row = shares.get(subcomponent)
        if not row or row.get("evidence_status") != "provided":
            missing += 1
    return missing


def normalize_workload_decision(decision, source, index):
    summary, summary_source = read_optional_summary(source)
    shares = subcomponent_share_map(summary)
    workload_class = "unknown"
    total_seconds = None
    sim_seconds = None
    if isinstance(summary, dict):
        workload_class = str(summary.get("workload_class") or workload_class)
        total_seconds = number_or_none(summary.get("total_seconds"))
        sim_seconds = number_or_none(summary.get("sim_seconds"))
    if isinstance(decision.get("workload_class"), str) and decision["workload_class"].strip():
        workload_class = decision["workload_class"].strip()
    return {
        "workload_id": workload_id_from(decision, source, index),
        "workload_class": workload_class,
        "decision_status": decision.get("decision_status"),
        "selection_status": decision.get("selection_status"),
        "selected_subcomponent": decision.get("selected_subcomponent"),
        "recommended_next_action": decision.get("recommended_next_action"),
        "runtime_prototype_allowed": decision.get("runtime_prototype_allowed"),
        "total_seconds": total_seconds,
        "sim_seconds": sim_seconds,
        "subcomponent_shares": shares,
        "missing_required_field_count": missing_required_field_count(shares),
        "source_sim_pipeline_budget_decision": str(source),
        "source_sim_pipeline_budget": str(summary_source) if summary else None,
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


def format_number(value):
    if value is None:
        return ""
    return f"{value:.6f}"


def build_case_rows(workloads):
    rows = []
    for workload in workloads:
        row = {
            "workload_id": workload["workload_id"],
            "workload_class": workload["workload_class"],
            "selection_status": workload.get("selection_status") or "unknown",
            "selected_subcomponent": workload.get("selected_subcomponent") or "",
            "recommended_next_action": workload.get("recommended_next_action") or "",
            "sim_seconds": format_number(workload.get("sim_seconds")),
            "total_seconds": format_number(workload.get("total_seconds")),
            "missing_required_field_count": str(
                workload.get("missing_required_field_count", 0)
            ),
        }
        for subcomponent, prefix in SUBCOMPONENT_COLUMNS.items():
            share = workload["subcomponent_shares"].get(subcomponent, {})
            row[f"{prefix}_share_of_sim"] = format_number(
                share.get("share_of_sim")
            )
            row[f"{prefix}_share_of_total"] = format_number(
                share.get("share_of_total")
            )
        rows.append(row)
    return rows


def sim_seconds_weighted_selected(workloads):
    total_sim_seconds = sum(
        row["sim_seconds"] for row in workloads if row.get("sim_seconds") is not None
    )
    weighted = Counter()
    for row in workloads:
        selected_subcomponent = row.get("selected_subcomponent")
        sim_seconds = row.get("sim_seconds")
        if row.get("selection_status") != "selected":
            continue
        if not selected_subcomponent or sim_seconds is None:
            continue
        weighted[selected_subcomponent] += sim_seconds
    if not weighted or total_sim_seconds <= 0.0:
        return None, None
    selected_subcomponent, selected_seconds = weighted.most_common(1)[0]
    return selected_subcomponent, selected_seconds / total_sim_seconds


def stable_subcomponents_by_workload_class(workloads):
    groups = {}
    for row in workloads:
        groups.setdefault(row["workload_class"], []).append(row)
    stable = {}
    for workload_class, group in groups.items():
        if workload_class == "unknown" or len(group) < 2:
            continue
        selected_pairs = {
            selected_key(row) for row in group if row.get("selection_status") == "selected"
        }
        if len(selected_pairs) != 1 or len(selected_pairs) != len(group):
            continue
        selected_subcomponent, recommended_next_action = next(iter(selected_pairs))
        stable[workload_class] = {
            "selected_subcomponent": selected_subcomponent,
            "recommended_next_action": recommended_next_action,
            "workload_count": len(group),
        }
    return stable


def minimum_next_workloads(workloads, selection_status):
    if selection_status != "workload_dependent_subcomponent":
        return []
    next_workloads = []
    seen = set()
    for row in workloads:
        if row.get("selection_status") != "selected":
            continue
        selected_subcomponent = row.get("selected_subcomponent")
        if not selected_subcomponent or selected_subcomponent in seen:
            continue
        seen.add(selected_subcomponent)
        next_workloads.append(f"one_more_{selected_subcomponent}_like_workload")
    if any(row.get("selection_status") == "no_stable_subcomponent" for row in workloads):
        next_workloads.append("one_more_no_stable_like_workload")
    if not next_workloads:
        next_workloads.append("one_more_ready_workload")
    return next_workloads


def stratification_status_from(selection_status):
    if selection_status == "workload_dependent_subcomponent":
        return "needed"
    if selection_status == "insufficient_sim_substage_telemetry":
        return "blocked_by_missing_telemetry"
    return "not_needed"


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
    selected_pairs = {
        selected_key(row) for row in workloads if row.get("selection_status") == "selected"
    }

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

    stratification_status = stratification_status_from(selection_status)
    weighted_subcomponent, weighted_share = sim_seconds_weighted_selected(workloads)
    stable_by_class = stable_subcomponents_by_workload_class(workloads)
    minimum_workloads = minimum_next_workloads(workloads, selection_status)

    workload_decisions = {
        row["workload_key"]: {
            "workload_id": row["workload_id"],
            "workload_class": row["workload_class"],
            "decision_status": row["decision_status"],
            "selection_status": row["selection_status"],
            "selected_subcomponent": row["selected_subcomponent"],
            "recommended_next_action": row["recommended_next_action"],
            "runtime_prototype_allowed": row["runtime_prototype_allowed"],
            "sim_seconds": row["sim_seconds"],
            "total_seconds": row["total_seconds"],
            "missing_required_field_count": row["missing_required_field_count"],
            "source_sim_pipeline_budget_decision": row[
                "source_sim_pipeline_budget_decision"
            ],
            "source_sim_pipeline_budget": row["source_sim_pipeline_budget"],
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
        "stratification_status": stratification_status,
        "stable_subcomponents_by_workload_class": stable_by_class,
        "minimum_next_workloads": minimum_workloads,
        "sim_seconds_weighted_selected_subcomponent": weighted_subcomponent,
        "selected_subcomponent_share_of_sim_seconds": weighted_share,
        "workload_count": len(workloads),
        "selection_status_counts": dict(sorted(status_counts.items())),
        "workload_decisions": workload_decisions,
        "case_rows": build_case_rows(workloads),
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
        f"- stratification_status: `{summary['stratification_status']}`",
        f"- runtime_prototype_allowed: `{str(summary['runtime_prototype_allowed']).lower()}`",
        f"- workload_count: `{summary['workload_count']}`",
        "",
        "| workload | workload_class | selection_status | selected_subcomponent | recommended_next_action |",
        "| --- | --- | --- | --- | --- |",
    ]
    for workload_id, decision in sorted(summary["workload_decisions"].items()):
        lines.append(
            "| "
            + f"{workload_id} | "
            + f"{decision.get('workload_class') or 'unknown'} | "
            + f"{decision.get('selection_status') or 'unknown'} | "
            + f"{decision.get('selected_subcomponent') or 'none'} | "
            + f"{decision.get('recommended_next_action') or 'unknown'} |"
        )
    lines.append("")
    return "\n".join(lines)


def write_outputs(output_dir, summary):
    output_dir.mkdir(parents=True, exist_ok=True)
    cases_path = output_dir / "sim_pipeline_budget_rollup_cases.tsv"
    with cases_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CASE_TSV_FIELDS, delimiter="\t")
        writer.writeheader()
        writer.writerows(summary["case_rows"])
    summary["cases_tsv"] = str(cases_path)

    decision = {
        "decision_status": summary["decision_status"],
        "phase": summary["phase"],
        "selection_status": summary["selection_status"],
        "selected_subcomponent": summary["selected_subcomponent"],
        "recommended_next_action": summary["recommended_next_action"],
        "allowed_next_actions": summary["allowed_next_actions"],
        "runtime_prototype_allowed": summary["runtime_prototype_allowed"],
        "stratification_status": summary["stratification_status"],
        "stable_subcomponents_by_workload_class": summary[
            "stable_subcomponents_by_workload_class"
        ],
        "minimum_next_workloads": summary["minimum_next_workloads"],
        "sim_seconds_weighted_selected_subcomponent": summary[
            "sim_seconds_weighted_selected_subcomponent"
        ],
        "selected_subcomponent_share_of_sim_seconds": summary[
            "selected_subcomponent_share_of_sim_seconds"
        ],
        "workload_count": summary["workload_count"],
        "workload_decisions": summary["workload_decisions"],
        "cases_tsv": summary["cases_tsv"],
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
