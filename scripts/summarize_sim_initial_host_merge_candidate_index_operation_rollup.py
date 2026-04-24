#!/usr/bin/env python3
import argparse
import csv
import json
from pathlib import Path


class OperationRollupInputError(Exception):
    pass


MEMORY_DOMINANCE_THRESHOLD = 0.40
CONTROL_DOMINANCE_THRESHOLD = 0.40
DOMINANCE_MARGIN_THRESHOLD = 0.05


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile-mode-ab-summary", required=True)
    parser.add_argument("--candidate-index-lifecycle-summary", required=True)
    parser.add_argument("--terminal-telemetry-classification-decision")
    parser.add_argument("--state-update-bookkeeping-classification-decision")
    parser.add_argument("--output-dir", required=True)
    return parser.parse_args()


def read_json(path_text):
    path = Path(path_text)
    if not path.is_file():
        raise OperationRollupInputError(f"missing JSON input: {path}")
    return json.loads(path.read_text(encoding="utf-8")), path


def optional_str(mapping, key, default="unknown"):
    if not isinstance(mapping, dict):
        return default
    value = mapping.get(key)
    if value is None or str(value).strip() == "":
        return default
    return str(value)


def require_float(mapping, key):
    if key not in mapping:
        raise OperationRollupInputError(f"missing float field: {key}")
    return float(mapping[key])


def share_of_total(share_of_candidate_index, candidate_index_share_of_total_seconds):
    return float(share_of_candidate_index) * float(candidate_index_share_of_total_seconds)


def add_row(rows, family, share_candidate, candidate_share_total, *, non_runtime=False):
    share_candidate = max(0.0, float(share_candidate))
    rows.append(
        {
            "operation_family": family,
            "share_of_candidate_index": share_candidate,
            "share_of_total_seconds": share_of_total(
                share_candidate, candidate_share_total
            ),
            "case_weighted_share": share_candidate,
            "event_weighted_share": "",
            "stability_status": "stable" if share_candidate > 0.0 else "unknown",
            "non_runtime": non_runtime,
        }
    )


def build_summary(
    ab_summary,
    lifecycle_summary,
    terminal_telemetry_classification,
    _state_update_bookkeeping_classification,
    source_paths,
):
    candidate = lifecycle_summary.get("candidate_index")
    if not isinstance(candidate, dict):
        raise OperationRollupInputError("missing candidate_index object")

    profile_mode_overhead_status = optional_str(
        ab_summary, "profile_mode_overhead_status", "unknown"
    )
    candidate_share_total = require_float(candidate, "share_of_total_seconds")

    rows = []

    start_index_write_share = require_float(
        candidate, "terminal_path_start_index_write_share_of_candidate_index"
    )
    start_index_probe_share = start_index_write_share * float(
        candidate.get("terminal_path_start_index_write_probe_or_locate_share", 0.0)
    )
    start_index_store_parent_share = start_index_write_share * float(
        candidate.get("terminal_path_start_index_write_entry_store_share", 0.0)
    )

    full_probe_share = require_float(
        candidate, "lookup_miss_candidate_set_full_probe_share_of_candidate_index"
    )
    full_probe_scan_share = full_probe_share * float(
        candidate.get("lookup_miss_candidate_set_full_probe_scan_share", 0.0)
    )
    full_probe_compare_share = full_probe_share * float(
        candidate.get("lookup_miss_candidate_set_full_probe_compare_share", 0.0)
    )
    full_probe_branch_share = full_probe_share * float(
        candidate.get("lookup_miss_candidate_set_full_probe_branch_or_guard_share", 0.0)
    )
    full_probe_bookkeeping_share = full_probe_share * float(
        candidate.get("lookup_miss_candidate_set_full_probe_bookkeeping_share", 0.0)
    )

    state_update_share = require_float(
        candidate, "terminal_path_state_update_share_of_candidate_index"
    )
    production_state_update_share = float(
        candidate.get("production_state_update_share_of_candidate_index", 0.0)
    )
    trace_profile_bookkeeping_residual_share = max(
        0.0,
        state_update_share
        * float(
            candidate.get(
                "terminal_path_state_update_trace_or_profile_bookkeeping_share", 0.0
            )
        )
        - production_state_update_share,
    )

    add_row(
        rows,
        "candidate_slot_overwrite",
        candidate.get("terminal_path_candidate_slot_write_share_of_candidate_index", 0.0),
        candidate_share_total,
    )
    add_row(rows, "scan", start_index_probe_share + full_probe_scan_share, candidate_share_total)
    add_row(rows, "compare", full_probe_compare_share, candidate_share_total)
    add_row(rows, "branch_or_guard", full_probe_branch_share, candidate_share_total)
    add_row(rows, "bookkeeping", full_probe_bookkeeping_share, candidate_share_total)
    add_row(
        rows,
        "store_insert",
        start_index_store_parent_share
        * float(candidate.get("terminal_path_start_index_store_insert_share", 0.0)),
        candidate_share_total,
    )
    add_row(
        rows,
        "store_clear",
        start_index_store_parent_share
        * float(candidate.get("terminal_path_start_index_store_clear_share", 0.0)),
        candidate_share_total,
    )
    add_row(
        rows,
        "store_overwrite",
        start_index_store_parent_share
        * float(candidate.get("terminal_path_start_index_store_overwrite_share", 0.0)),
        candidate_share_total,
    )
    add_row(
        rows,
        "state_update",
        state_update_share
        * (
            float(candidate.get("terminal_path_state_update_heap_build_share", 0.0))
            + float(candidate.get("terminal_path_state_update_heap_update_share", 0.0))
            + float(candidate.get("terminal_path_state_update_start_index_rebuild_share", 0.0))
        ),
        candidate_share_total,
    )
    add_row(
        rows,
        "trace_or_profile_bookkeeping",
        trace_profile_bookkeeping_residual_share,
        candidate_share_total,
    )
    add_row(
        rows,
        "benchmark_counter",
        production_state_update_share
        * float(candidate.get("production_state_update_benchmark_counter_share", 0.0)),
        candidate_share_total,
    )
    add_row(
        rows,
        "trace_replay_required_state",
        production_state_update_share
        * float(
            candidate.get("production_state_update_trace_replay_required_state_share", 0.0)
        ),
        candidate_share_total,
    )

    telemetry_kind = optional_str(
        terminal_telemetry_classification, "telemetry_branch_kind", "unknown"
    )
    add_row(
        rows,
        "non_runtime_overhead",
        candidate.get("terminal_path_telemetry_overhead_share_of_candidate_index", 0.0),
        candidate_share_total,
        non_runtime=(telemetry_kind == "profiler_only_overhead"),
    )

    rows.sort(key=lambda row: (-row["share_of_candidate_index"], row["operation_family"]))

    family_totals = {row["operation_family"]: row["share_of_candidate_index"] for row in rows}
    memory_pressure_share = (
        family_totals.get("candidate_slot_overwrite", 0.0)
        + family_totals.get("store_insert", 0.0)
        + family_totals.get("store_clear", 0.0)
        + family_totals.get("store_overwrite", 0.0)
        + family_totals.get("state_update", 0.0)
        + family_totals.get("benchmark_counter", 0.0)
        + family_totals.get("trace_replay_required_state", 0.0)
    )
    control_pressure_share = (
        family_totals.get("scan", 0.0)
        + family_totals.get("compare", 0.0)
        + family_totals.get("branch_or_guard", 0.0)
    )

    if (
        memory_pressure_share >= MEMORY_DOMINANCE_THRESHOLD
        and memory_pressure_share - control_pressure_share >= DOMINANCE_MARGIN_THRESHOLD
    ):
        recommended_next_action = "profile_candidate_index_common_memory_behavior"
        optional_next_action = None
        dominant_operation_group = "memory"
        dominance_status = "stable"
    elif (
        control_pressure_share >= CONTROL_DOMINANCE_THRESHOLD
        and control_pressure_share - memory_pressure_share >= DOMINANCE_MARGIN_THRESHOLD
    ):
        recommended_next_action = "stop_candidate_index_structural_profiling"
        optional_next_action = "profile_candidate_index_common_control_flow_behavior"
        dominant_operation_group = "control_flow"
        dominance_status = "stable"
    else:
        recommended_next_action = "stop_candidate_index_structural_profiling"
        optional_next_action = None
        dominant_operation_group = "none"
        dominance_status = "near_tie"

    summary = {
        "decision_status": "ready",
        "candidate_index_materiality_status": optional_str(
            lifecycle_summary, "candidate_index_materiality_status", "material"
        ),
        "profile_mode_overhead_status": profile_mode_overhead_status,
        "recommended_next_action": recommended_next_action,
        "optional_next_action": optional_next_action,
        "runtime_prototype_allowed": False,
        "dominant_operation_group": dominant_operation_group,
        "dominance_status": dominance_status,
        "memory_pressure_share_of_candidate_index": memory_pressure_share,
        "control_flow_pressure_share_of_candidate_index": control_pressure_share,
        "source_profile_mode_ab_summary": str(source_paths["ab"]),
        "source_candidate_index_lifecycle_summary": str(source_paths["lifecycle"]),
        "rows": rows,
    }
    if source_paths["terminal_telemetry"] is not None:
        summary["source_terminal_telemetry_classification_decision"] = str(
            source_paths["terminal_telemetry"]
        )
    return summary


def render_markdown(summary):
    lines = [
        "# Candidate-Index Operation Rollup",
        "",
        f"- recommended_next_action: `{summary['recommended_next_action']}`",
        f"- optional_next_action: `{summary.get('optional_next_action') or 'none'}`",
        f"- dominant_operation_group: `{summary['dominant_operation_group']}`",
        f"- dominance_status: `{summary['dominance_status']}`",
        f"- memory_pressure_share_of_candidate_index: `{summary['memory_pressure_share_of_candidate_index']:.6f}`",
        f"- control_flow_pressure_share_of_candidate_index: `{summary['control_flow_pressure_share_of_candidate_index']:.6f}`",
        "",
        "| operation_family | share_of_candidate_index | share_of_total_seconds | stability_status | non_runtime |",
        "| --- | ---: | ---: | --- | --- |",
    ]
    for row in summary["rows"]:
        lines.append(
            f"| {row['operation_family']} | {row['share_of_candidate_index']:.6f} | "
            f"{row['share_of_total_seconds']:.6f} | {row['stability_status']} | "
            f"{str(row['non_runtime']).lower()} |"
        )
    return "\n".join(lines)


def main():
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    ab_summary, ab_path = read_json(args.profile_mode_ab_summary)
    lifecycle_summary, lifecycle_path = read_json(args.candidate_index_lifecycle_summary)
    terminal_telemetry_classification, terminal_telemetry_path = (
        read_json(args.terminal_telemetry_classification_decision)
        if args.terminal_telemetry_classification_decision
        else ({}, None)
    )
    state_update_bookkeeping_classification, state_update_bookkeeping_path = (
        read_json(args.state_update_bookkeeping_classification_decision)
        if args.state_update_bookkeeping_classification_decision
        else ({}, None)
    )

    summary = build_summary(
        ab_summary,
        lifecycle_summary,
        terminal_telemetry_classification,
        state_update_bookkeeping_classification,
        {
            "ab": ab_path,
            "lifecycle": lifecycle_path,
            "terminal_telemetry": terminal_telemetry_path,
            "state_update": state_update_bookkeeping_path,
        },
    )
    decision = {
        "decision_status": "ready",
        "recommended_next_action": summary["recommended_next_action"],
        "optional_next_action": summary["optional_next_action"],
        "runtime_prototype_allowed": False,
        "dominant_operation_group": summary["dominant_operation_group"],
        "dominance_status": summary["dominance_status"],
    }

    with (output_dir / "candidate_index_operation_rollup.json").open(
        "w", encoding="utf-8"
    ) as handle:
        json.dump(summary, handle, indent=2, sort_keys=True)
        handle.write("\n")
    with (output_dir / "candidate_index_operation_rollup_decision.json").open(
        "w", encoding="utf-8"
    ) as handle:
        json.dump(decision, handle, indent=2, sort_keys=True)
        handle.write("\n")
    with (output_dir / "candidate_index_operation_rollup.tsv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        fieldnames = [
            "operation_family",
            "share_of_candidate_index",
            "share_of_total_seconds",
            "case_weighted_share",
            "event_weighted_share",
            "stability_status",
            "non_runtime",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(summary["rows"])
    (output_dir / "candidate_index_operation_rollup.md").write_text(
        render_markdown(summary), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
