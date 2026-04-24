#!/usr/bin/env python3
import argparse
import csv
import json
from pathlib import Path


class CommonMemoryInputError(Exception):
    pass


MEMORY_COVERAGE_THRESHOLD = 0.60
SAME_CACHELINE_REWRITE_SIGNAL_THRESHOLD = 0.70


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-index-lifecycle-summary", required=True)
    parser.add_argument("--candidate-index-operation-rollup-decision")
    parser.add_argument("--output-dir", required=True)
    return parser.parse_args()


def read_json(path_text):
    path = Path(path_text)
    if not path.is_file():
        raise CommonMemoryInputError(f"missing JSON input: {path}")
    return json.loads(path.read_text(encoding="utf-8")), path


def optional_str(mapping, key, default="unknown"):
    if not isinstance(mapping, dict):
        return default
    value = mapping.get(key)
    if value is None or str(value).strip() == "":
        return default
    return str(value)


def build_summary(lifecycle_summary, lifecycle_path, operation_rollup_decision, operation_path):
    candidate = lifecycle_summary.get("candidate_index")
    if not isinstance(candidate, dict):
        raise CommonMemoryInputError("missing candidate_index object")

    candidate_slot_write_share = float(
        candidate.get("terminal_path_candidate_slot_write_share_of_candidate_index", 0.0)
    )
    start_index_write_share = float(
        candidate.get("terminal_path_start_index_write_share_of_candidate_index", 0.0)
    )
    covered_share_of_candidate_index = candidate_slot_write_share + start_index_write_share

    known_bytes_written = int(candidate.get("terminal_path_candidate_bytes_written", 0)) + int(
        candidate.get("terminal_path_start_index_bytes_written", 0)
    )
    unique_entry_count = int(candidate.get("terminal_path_start_index_store_unique_entry_count", 0))
    same_entry_rewrite_count = int(
        candidate.get("terminal_path_start_index_store_same_entry_rewrite_count", 0)
    )
    same_cacheline_rewrite_count = int(
        candidate.get("terminal_path_start_index_store_same_cacheline_rewrite_count", 0)
    )
    start_index_write_count = int(candidate.get("terminal_path_start_index_write_count", 0))

    bytes_per_event = (
        float(known_bytes_written) / float(start_index_write_count)
        if start_index_write_count > 0
        else 0.0
    )
    bytes_per_unique_entry = (
        float(known_bytes_written) / float(unique_entry_count)
        if unique_entry_count > 0
        else 0.0
    )
    same_cacheline_rewrite_share = (
        float(same_cacheline_rewrite_count) / float(same_entry_rewrite_count)
        if same_entry_rewrite_count > 0
        else 0.0
    )
    same_entry_rewrite_share = (
        float(same_entry_rewrite_count)
        / float(max(unique_entry_count, same_entry_rewrite_count))
        if max(unique_entry_count, same_entry_rewrite_count) > 0
        else 0.0
    )

    missing_major_components = []
    if float(candidate.get("terminal_path_state_update_share_of_candidate_index", 0.0)) > 0.0:
        missing_major_components.append("state_update_bytes")
    if float(candidate.get("production_state_update_share_of_candidate_index", 0.0)) > 0.0:
        missing_major_components.append("production_state_update_bytes")

    coverage_status = (
        "sufficient"
        if covered_share_of_candidate_index >= MEMORY_COVERAGE_THRESHOLD
        else "partial"
    )

    operation_rollup_action = optional_str(
        operation_rollup_decision, "recommended_next_action", "unknown"
    )
    operation_rollup_optional_next_action = optional_str(
        operation_rollup_decision, "optional_next_action", ""
    )
    if operation_rollup_action != "profile_candidate_index_common_memory_behavior":
        selection_status = "inactive"
        recommended_next_action = "stop_candidate_index_structural_profiling"
        optional_next_action = (
            operation_rollup_optional_next_action
            if operation_rollup_optional_next_action
            else None
        )
    elif covered_share_of_candidate_index < MEMORY_COVERAGE_THRESHOLD:
        selection_status = "active"
        recommended_next_action = "instrument_candidate_index_state_update_memory_counters"
        optional_next_action = None
    elif same_cacheline_rewrite_share >= SAME_CACHELINE_REWRITE_SIGNAL_THRESHOLD:
        selection_status = "active"
        recommended_next_action = "profile_candidate_index_common_store_layout"
        optional_next_action = None
    else:
        selection_status = "active"
        recommended_next_action = "stop_candidate_index_structural_profiling"
        optional_next_action = None

    rows = [
        {
            "metric": "known_bytes_written",
            "value": known_bytes_written,
        },
        {
            "metric": "covered_share_of_candidate_index",
            "value": f"{covered_share_of_candidate_index:.6f}",
        },
        {
            "metric": "same_cacheline_rewrite_share",
            "value": f"{same_cacheline_rewrite_share:.6f}",
        },
    ]

    return {
        "decision_status": "ready",
        "selection_status": selection_status,
        "memory_coverage_scope": "terminal_write_paths_only",
        "coverage_status": coverage_status,
        "covered_share_of_candidate_index": covered_share_of_candidate_index,
        "known_bytes_written": known_bytes_written,
        "same_cacheline_rewrite_share": same_cacheline_rewrite_share,
        "same_entry_rewrite_share": same_entry_rewrite_share,
        "bytes_per_event": bytes_per_event,
        "bytes_per_unique_entry": bytes_per_unique_entry,
        "missing_major_components": missing_major_components,
        "recommended_next_action": recommended_next_action,
        "optional_next_action": optional_next_action,
        "runtime_prototype_allowed": False,
        "source_candidate_index_lifecycle_summary": str(lifecycle_path),
        "source_candidate_index_operation_rollup_decision": (
            str(operation_path) if operation_path is not None else None
        ),
        "rows": rows,
    }


def render_markdown(summary):
    lines = [
        "# Candidate-Index Common Memory Behavior",
        "",
        f"- selection_status: `{summary['selection_status']}`",
        f"- memory_coverage_scope: `{summary['memory_coverage_scope']}`",
        f"- coverage_status: `{summary['coverage_status']}`",
        f"- covered_share_of_candidate_index: `{summary['covered_share_of_candidate_index']:.6f}`",
        f"- same_cacheline_rewrite_share: `{summary['same_cacheline_rewrite_share']:.6f}`",
        f"- bytes_per_event: `{summary['bytes_per_event']:.6f}`",
        f"- bytes_per_unique_entry: `{summary['bytes_per_unique_entry']:.6f}`",
        f"- recommended_next_action: `{summary['recommended_next_action']}`",
        f"- optional_next_action: `{summary.get('optional_next_action') or 'none'}`",
        "",
    ]
    return "\n".join(lines)


def main():
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    lifecycle_summary, lifecycle_path = read_json(args.candidate_index_lifecycle_summary)
    operation_rollup_decision, operation_path = (
        read_json(args.candidate_index_operation_rollup_decision)
        if args.candidate_index_operation_rollup_decision
        else ({}, None)
    )

    summary = build_summary(
        lifecycle_summary, lifecycle_path, operation_rollup_decision, operation_path
    )
    decision = {
        "decision_status": "ready",
        "selection_status": summary["selection_status"],
        "recommended_next_action": summary["recommended_next_action"],
        "optional_next_action": summary["optional_next_action"],
        "runtime_prototype_allowed": False,
    }

    with (output_dir / "candidate_index_common_memory_behavior_summary.json").open(
        "w", encoding="utf-8"
    ) as handle:
        json.dump(summary, handle, indent=2, sort_keys=True)
        handle.write("\n")
    with (output_dir / "candidate_index_common_memory_behavior_decision.json").open(
        "w", encoding="utf-8"
    ) as handle:
        json.dump(decision, handle, indent=2, sort_keys=True)
        handle.write("\n")
    with (output_dir / "candidate_index_common_memory_behavior_cases.tsv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        fieldnames = ["metric", "value"]
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(summary["rows"])
    (output_dir / "candidate_index_common_memory_behavior_summary.md").write_text(
        render_markdown(summary), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
