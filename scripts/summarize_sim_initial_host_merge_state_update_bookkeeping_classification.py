#!/usr/bin/env python3
import argparse
import csv
import json
from pathlib import Path

CORE_BEHAVIOR_COUNT_FIELDS = [
    "full_set_miss_count",
    "candidate_index_lookup_count",
    "candidate_index_insert_count",
    "candidate_index_erase_count",
    "terminal_path_event_count",
    "terminal_path_candidate_slot_write_count",
    "terminal_path_start_index_write_count",
    "terminal_path_state_update_count",
    "terminal_path_state_update_event_count",
    "terminal_path_state_update_heap_build_count",
    "terminal_path_state_update_heap_update_count",
    "terminal_path_state_update_start_index_rebuild_count",
]


class ClassificationInputError(Exception):
    pass


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--with-state-update-bookkeeping-summary", required=True)
    parser.add_argument("--without-state-update-bookkeeping-summary", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--current-branch", default="terminal_path_state_update")
    parser.add_argument(
        "--material-threshold-share-of-candidate-index",
        type=float,
        default=0.03,
    )
    return parser.parse_args()


def read_json(path_text):
    path = Path(path_text)
    if not path.is_file():
        raise ClassificationInputError(f"missing JSON input: {path}")
    return json.loads(path.read_text(encoding="utf-8")), path


def require_mapping(mapping, key):
    value = mapping.get(key)
    if not isinstance(value, dict):
        raise ClassificationInputError(f"missing object field: {key}")
    return value


def require_float(mapping, key):
    value = mapping.get(key, None)
    if value is None:
        raise ClassificationInputError(f"missing float field: {key}")
    return float(value)


def optional_str(mapping, key, default="unknown"):
    value = mapping.get(key, None)
    if value is None or str(value).strip() == "":
        return default
    return str(value)


def optional_cases(summary):
    cases = summary.get("cases", None)
    if not isinstance(cases, list):
        return None
    indexed = {}
    for case in cases:
        if not isinstance(case, dict):
            continue
        case_id = optional_str(case, "case_id", "")
        if case_id:
            indexed[case_id] = case
    return indexed or None


def to_intish(value):
    return int(round(float(value)))


def compare_cases(with_summary, without_summary):
    with_cases = optional_cases(with_summary)
    without_cases = optional_cases(without_summary)
    if with_cases is None or without_cases is None:
        return {
            "case_set_consistency_status": "not_checked",
            "behavior_consistency_status": "not_checked",
            "with_case_ids": [],
            "without_case_ids": [],
            "semantic_drift_field_mismatches": [],
        }

    with_case_ids = sorted(with_cases.keys())
    without_case_ids = sorted(without_cases.keys())
    if with_case_ids != without_case_ids:
        return {
            "case_set_consistency_status": "mismatch",
            "behavior_consistency_status": "not_checked",
            "with_case_ids": with_case_ids,
            "without_case_ids": without_case_ids,
            "semantic_drift_field_mismatches": [],
        }

    with_workload_ids = sorted(
        {optional_str(case, "workload_id", "") for case in with_cases.values()}
    )
    without_workload_ids = sorted(
        {optional_str(case, "workload_id", "") for case in without_cases.values()}
    )
    if with_workload_ids != without_workload_ids or len(with_workload_ids) != 1:
        return {
            "case_set_consistency_status": "mismatch",
            "behavior_consistency_status": "not_checked",
            "with_case_ids": with_case_ids,
            "without_case_ids": without_case_ids,
            "semantic_drift_field_mismatches": [],
        }

    mismatches = []
    for case_id in with_case_ids:
        with_case = with_cases[case_id]
        without_case = without_cases[case_id]
        for field in CORE_BEHAVIOR_COUNT_FIELDS:
            with_value = with_case.get(field, None)
            without_value = without_case.get(field, None)
            if with_value is None or without_value is None:
                continue
            if to_intish(with_value) != to_intish(without_value):
                mismatches.append(
                    {
                        "case_id": case_id,
                        "field": field,
                        "with_value": to_intish(with_value),
                        "without_value": to_intish(without_value),
                    }
                )

    return {
        "case_set_consistency_status": "matched",
        "behavior_consistency_status": "matched" if not mismatches else "mismatch",
        "with_case_ids": with_case_ids,
        "without_case_ids": without_case_ids,
        "semantic_drift_field_mismatches": mismatches,
        "workload_id": with_workload_ids[0],
    }


def extract_mode_metadata(summary):
    candidate = require_mapping(summary, "candidate_index")
    return {
        "profile_mode": optional_str(
            candidate, "profile_mode", optional_str(summary, "profile_mode", "unknown")
        ),
        "requested": optional_str(
            candidate,
            "state_update_bookkeeping_mode_requested",
            optional_str(summary, "state_update_bookkeeping_mode_requested", "unknown"),
        ),
        "effective": optional_str(
            candidate,
            "state_update_bookkeeping_mode_effective",
            optional_str(summary, "state_update_bookkeeping_mode_effective", "unknown"),
        ),
    }


def nonnegative_delta(with_value, without_value):
    return (with_value - without_value) if with_value > without_value else 0.0


def optional_ratio(numerator, denominator):
    if denominator is None or denominator <= 0.0:
        return None
    return numerator / denominator


def format_metric(value):
    if value is None:
        return "n/a"
    return f"{value:.6f}"


def classify_mode_status(with_mode, without_mode):
    if with_mode["effective"] != "on":
        return "mismatch"
    if without_mode["requested"] != "off":
        return "mismatch"
    if without_mode["effective"] != "off":
        return "mismatch"
    return "matched"


def classify_branch(
    *,
    candidate_index_delta,
    terminal_parent_delta,
    state_update_parent_delta,
    bookkeeping_with,
    bookkeeping_without,
):
    candidate_index_delta_explains_share = optional_ratio(
        candidate_index_delta, bookkeeping_with
    )
    terminal_parent_delta_explains_share = optional_ratio(
        terminal_parent_delta, bookkeeping_with
    )
    state_update_parent_delta_explains_share = optional_ratio(
        state_update_parent_delta, bookkeeping_with
    )

    if (
        candidate_index_delta_explains_share is not None
        and candidate_index_delta_explains_share >= 0.80
    ) or (
        state_update_parent_delta_explains_share is not None
        and state_update_parent_delta_explains_share >= 0.80
    ):
        return (
            "profiler_only_overhead",
            "reduce_or_cold_path_state_update_bookkeeping",
            candidate_index_delta_explains_share,
            terminal_parent_delta_explains_share,
            state_update_parent_delta_explains_share,
        )

    if (
        bookkeeping_without <= 1e-12
        and (candidate_index_delta_explains_share or 0.0) < 0.30
        and (state_update_parent_delta_explains_share or 0.0) < 0.30
    ):
        return (
            "timer_scope_artifact_or_unknown",
            "inspect_state_update_bookkeeping_timer_scope",
            candidate_index_delta_explains_share,
            terminal_parent_delta_explains_share,
            state_update_parent_delta_explains_share,
        )

    if (
        candidate_index_delta_explains_share is not None
        and 0.30 <= candidate_index_delta_explains_share < 0.80
    ) or (
        state_update_parent_delta_explains_share is not None
        and 0.30 <= state_update_parent_delta_explains_share < 0.80
    ):
        return (
            "mixed",
            "split_state_update_bookkeeping_source",
            candidate_index_delta_explains_share,
            terminal_parent_delta_explains_share,
            state_update_parent_delta_explains_share,
        )

    return (
        "production_state_bookkeeping",
        "profile_production_state_update_bookkeeping_path",
        candidate_index_delta_explains_share,
        terminal_parent_delta_explains_share,
        state_update_parent_delta_explains_share,
    )


def build_summary(
    *,
    with_summary,
    without_summary,
    with_path,
    without_path,
    current_branch,
    material_threshold_share,
):
    with_candidate = require_mapping(with_summary, "candidate_index")
    without_candidate = require_mapping(without_summary, "candidate_index")

    candidate_index_with = require_float(with_candidate, "seconds")
    candidate_index_without = require_float(without_candidate, "seconds")
    terminal_parent_with = require_float(with_candidate, "terminal_path_parent_seconds")
    terminal_parent_without = require_float(
        without_candidate, "terminal_path_parent_seconds"
    )
    state_update_parent_with = require_float(
        with_candidate, "terminal_path_state_update_parent_seconds"
    )
    state_update_parent_without = require_float(
        without_candidate, "terminal_path_state_update_parent_seconds"
    )
    bookkeeping_with = require_float(
        with_candidate, "terminal_path_state_update_trace_or_profile_bookkeeping_seconds"
    )
    bookkeeping_without = require_float(
        without_candidate,
        "terminal_path_state_update_trace_or_profile_bookkeeping_seconds",
    )

    candidate_index_delta = nonnegative_delta(
        candidate_index_with, candidate_index_without
    )
    terminal_parent_delta = nonnegative_delta(
        terminal_parent_with, terminal_parent_without
    )
    state_update_parent_delta = nonnegative_delta(
        state_update_parent_with, state_update_parent_without
    )

    (
        state_update_bookkeeping_kind,
        recommended_next_action,
        candidate_index_delta_explains_share,
        terminal_parent_delta_explains_share,
        state_update_parent_delta_explains_share,
    ) = classify_branch(
        candidate_index_delta=candidate_index_delta,
        terminal_parent_delta=terminal_parent_delta,
        state_update_parent_delta=state_update_parent_delta,
        bookkeeping_with=bookkeeping_with,
        bookkeeping_without=bookkeeping_without,
    )

    profile_mode_overhead_status = optional_str(
        with_summary, "profile_mode_overhead_status", "unknown"
    )
    trusted_span_timing = (
        bool(with_summary.get("trusted_span_timing", False))
        if "trusted_span_timing" in with_summary
        else None
    )
    trusted_span_source = optional_str(with_summary, "trusted_span_source", "unknown")
    candidate_index_materiality_status = optional_str(
        with_summary, "candidate_index_materiality_status", "unknown"
    )
    case_comparison = compare_cases(with_summary, without_summary)
    with_mode = extract_mode_metadata(with_summary)
    without_mode = extract_mode_metadata(without_summary)
    mode_status = classify_mode_status(with_mode, without_mode)

    decision_status = "ready"
    if case_comparison["case_set_consistency_status"] == "mismatch":
        decision_status = "not_ready"
        state_update_bookkeeping_kind = "unknown"
        recommended_next_action = "inspect_state_update_bookkeeping_case_set_mismatch"
    elif case_comparison["behavior_consistency_status"] == "mismatch":
        decision_status = "not_ready"
        state_update_bookkeeping_kind = "unknown"
        recommended_next_action = "inspect_no_state_update_bookkeeping_semantic_drift"
    elif mode_status == "mismatch":
        decision_status = "not_ready"
        state_update_bookkeeping_kind = "unknown"
        recommended_next_action = "rerun_with_explicit_state_update_bookkeeping_modes"

    return {
        "decision_status": decision_status,
        "decision_context_status": "ready_but_requires_branch_rollup_context",
        "authoritative_next_action_source": "branch_rollup_decision",
        "runtime_prototype_allowed": False,
        "current_branch": current_branch,
        "candidate_index_materiality_status": candidate_index_materiality_status,
        "profile_mode_overhead_status": profile_mode_overhead_status,
        "trusted_span_timing": trusted_span_timing,
        "trusted_span_source": trusted_span_source,
        "with_state_update_bookkeeping_summary": str(with_path),
        "without_state_update_bookkeeping_summary": str(without_path),
        "with_state_update_bookkeeping_profile_mode": with_mode["profile_mode"],
        "with_state_update_bookkeeping_mode_requested": with_mode["requested"],
        "with_state_update_bookkeeping_mode_effective": with_mode["effective"],
        "without_state_update_bookkeeping_profile_mode": without_mode["profile_mode"],
        "without_state_update_bookkeeping_mode_requested": without_mode["requested"],
        "without_state_update_bookkeeping_mode_effective": without_mode["effective"],
        "state_update_bookkeeping_mode_status": mode_status,
        "candidate_index_seconds_with_state_update_bookkeeping": candidate_index_with,
        "candidate_index_seconds_without_state_update_bookkeeping": candidate_index_without,
        "candidate_index_seconds_delta_without_state_update_bookkeeping": candidate_index_delta,
        "terminal_parent_seconds_with_state_update_bookkeeping": terminal_parent_with,
        "terminal_parent_seconds_without_state_update_bookkeeping": terminal_parent_without,
        "terminal_parent_seconds_delta_without_state_update_bookkeeping": terminal_parent_delta,
        "state_update_parent_seconds_with_state_update_bookkeeping": state_update_parent_with,
        "state_update_parent_seconds_without_state_update_bookkeeping": state_update_parent_without,
        "state_update_parent_seconds_delta_without_bookkeeping": state_update_parent_delta,
        "state_update_bookkeeping_seconds_with": bookkeeping_with,
        "state_update_bookkeeping_seconds_without": bookkeeping_without,
        "candidate_index_delta_explains_share": candidate_index_delta_explains_share,
        "terminal_parent_delta_explains_share": terminal_parent_delta_explains_share,
        "state_update_parent_delta_explains_share": state_update_parent_delta_explains_share,
        "case_set_consistency_status": case_comparison["case_set_consistency_status"],
        "behavior_consistency_status": case_comparison["behavior_consistency_status"],
        "with_case_ids": case_comparison["with_case_ids"],
        "without_case_ids": case_comparison["without_case_ids"],
        "semantic_drift_field_mismatches": case_comparison["semantic_drift_field_mismatches"],
        "workload_id": case_comparison.get("workload_id"),
        "state_update_bookkeeping_kind": state_update_bookkeeping_kind,
        "recommended_next_action": recommended_next_action,
        "material_threshold_share_of_candidate_index": material_threshold_share,
    }


def render_markdown(summary):
    lines = [
        "# SIM Initial Host Merge State Update Bookkeeping Classification",
        "",
        f"- decision_context_status: `{summary['decision_context_status']}`",
        f"- authoritative_next_action_source: `{summary['authoritative_next_action_source']}`",
        f"- current_branch: `{summary['current_branch']}`",
        f"- state_update_bookkeeping_kind: `{summary['state_update_bookkeeping_kind']}`",
        f"- recommended_next_action: `{summary['recommended_next_action']}`",
        f"- runtime_prototype_allowed: `{str(summary['runtime_prototype_allowed']).lower()}`",
        f"- case_set_consistency_status: `{summary['case_set_consistency_status']}`",
        f"- behavior_consistency_status: `{summary['behavior_consistency_status']}`",
        f"- state_update_bookkeeping_mode_status: `{summary['state_update_bookkeeping_mode_status']}`",
        "",
        "| metric | value |",
        "| --- | ---: |",
        f"| with_state_update_bookkeeping_mode_requested | {summary['with_state_update_bookkeeping_mode_requested']} |",
        f"| with_state_update_bookkeeping_mode_effective | {summary['with_state_update_bookkeeping_mode_effective']} |",
        f"| without_state_update_bookkeeping_mode_requested | {summary['without_state_update_bookkeeping_mode_requested']} |",
        f"| without_state_update_bookkeeping_mode_effective | {summary['without_state_update_bookkeeping_mode_effective']} |",
        f"| candidate_index_seconds_with_state_update_bookkeeping | {format_metric(summary['candidate_index_seconds_with_state_update_bookkeeping'])} |",
        f"| candidate_index_seconds_without_state_update_bookkeeping | {format_metric(summary['candidate_index_seconds_without_state_update_bookkeeping'])} |",
        f"| candidate_index_seconds_delta_without_state_update_bookkeeping | {format_metric(summary['candidate_index_seconds_delta_without_state_update_bookkeeping'])} |",
        f"| terminal_parent_seconds_delta_without_state_update_bookkeeping | {format_metric(summary['terminal_parent_seconds_delta_without_state_update_bookkeeping'])} |",
        f"| state_update_parent_seconds_delta_without_bookkeeping | {format_metric(summary['state_update_parent_seconds_delta_without_bookkeeping'])} |",
        f"| state_update_bookkeeping_seconds_with | {format_metric(summary['state_update_bookkeeping_seconds_with'])} |",
        f"| state_update_bookkeeping_seconds_without | {format_metric(summary['state_update_bookkeeping_seconds_without'])} |",
        f"| candidate_index_delta_explains_share | {format_metric(summary['candidate_index_delta_explains_share'])} |",
        f"| terminal_parent_delta_explains_share | {format_metric(summary['terminal_parent_delta_explains_share'])} |",
        f"| state_update_parent_delta_explains_share | {format_metric(summary['state_update_parent_delta_explains_share'])} |",
        "",
    ]
    return "\n".join(lines)


def write_cases_tsv(path, summary):
    fieldnames = [
        "current_branch",
        "state_update_bookkeeping_kind",
        "recommended_next_action",
        "state_update_bookkeeping_mode_status",
        "with_state_update_bookkeeping_mode_requested",
        "with_state_update_bookkeeping_mode_effective",
        "without_state_update_bookkeeping_mode_requested",
        "without_state_update_bookkeeping_mode_effective",
        "candidate_index_seconds_with_state_update_bookkeeping",
        "candidate_index_seconds_without_state_update_bookkeeping",
        "candidate_index_seconds_delta_without_state_update_bookkeeping",
        "terminal_parent_seconds_with_state_update_bookkeeping",
        "terminal_parent_seconds_without_state_update_bookkeeping",
        "terminal_parent_seconds_delta_without_state_update_bookkeeping",
        "state_update_parent_seconds_with_state_update_bookkeeping",
        "state_update_parent_seconds_without_state_update_bookkeeping",
        "state_update_parent_seconds_delta_without_bookkeeping",
        "state_update_bookkeeping_seconds_with",
        "state_update_bookkeeping_seconds_without",
        "candidate_index_delta_explains_share",
        "terminal_parent_delta_explains_share",
        "state_update_parent_delta_explains_share",
        "case_set_consistency_status",
        "behavior_consistency_status",
        "workload_id",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerow({field: summary.get(field) for field in fieldnames})


def main():
    args = parse_args()

    with_summary, with_path = read_json(args.with_state_update_bookkeeping_summary)
    without_summary, without_path = read_json(
        args.without_state_update_bookkeeping_summary
    )

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    summary = build_summary(
        with_summary=with_summary,
        without_summary=without_summary,
        with_path=with_path,
        without_path=without_path,
        current_branch=args.current_branch,
        material_threshold_share=args.material_threshold_share_of_candidate_index,
    )
    decision = {
        "decision_status": summary["decision_status"],
        "decision_context_status": summary["decision_context_status"],
        "authoritative_next_action_source": summary[
            "authoritative_next_action_source"
        ],
        "current_branch": summary["current_branch"],
        "state_update_bookkeeping_kind": summary["state_update_bookkeeping_kind"],
        "recommended_next_action": summary["recommended_next_action"],
        "runtime_prototype_allowed": summary["runtime_prototype_allowed"],
        "candidate_index_materiality_status": summary[
            "candidate_index_materiality_status"
        ],
        "profile_mode_overhead_status": summary["profile_mode_overhead_status"],
        "trusted_span_timing": summary["trusted_span_timing"],
        "trusted_span_source": summary["trusted_span_source"],
    }

    summary_path = output_dir / "state_update_bookkeeping_classification_summary.json"
    decision_path = output_dir / "state_update_bookkeeping_classification_decision.json"
    tsv_path = output_dir / "state_update_bookkeeping_classification.tsv"
    markdown_path = output_dir / "state_update_bookkeeping_classification.md"

    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    decision_path.write_text(
        json.dumps(decision, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    write_cases_tsv(tsv_path, summary)
    markdown_path.write_text(render_markdown(summary) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
