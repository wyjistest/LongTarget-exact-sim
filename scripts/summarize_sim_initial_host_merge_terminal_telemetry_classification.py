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
]


class ClassificationInputError(Exception):
    pass


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--with-terminal-telemetry-summary", required=True)
    parser.add_argument("--without-terminal-telemetry-summary", required=True)
    parser.add_argument("--forced-off-terminal-telemetry-summary")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--current-branch", default="terminal_path_telemetry_overhead")
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


def optional_float(mapping, key, default=None):
    value = mapping.get(key, None)
    if value is None or str(value).strip() == "":
        return default
    return float(value)


def optional_str(mapping, key, default="unknown"):
    value = mapping.get(key, None)
    if value is None or str(value).strip() == "":
        return default
    return str(value)


def extract_mode_metadata(summary):
    candidate = require_mapping(summary, "candidate_index")
    return {
        "profile_mode": optional_str(
            candidate, "profile_mode", optional_str(summary, "profile_mode", "unknown")
        ),
        "requested": optional_str(
            candidate,
            "terminal_telemetry_overhead_mode_requested",
            optional_str(
                summary, "terminal_telemetry_overhead_mode_requested", "unknown"
            ),
        ),
        "effective": optional_str(
            candidate,
            "terminal_telemetry_overhead_mode_effective",
            optional_str(
                summary, "terminal_telemetry_overhead_mode_effective", "unknown"
            ),
        ),
    }


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
    if with_mode["requested"] != "on":
        return "mismatch"
    if with_mode["effective"] != "on":
        return "mismatch"
    if without_mode["effective"] != "off":
        return "mismatch"
    return "matched"


def classify_branch(
    *,
    candidate_index_delta,
    terminal_parent_delta,
    telemetry_overhead_with,
    telemetry_overhead_without,
    candidate_index_without,
    material_threshold_share,
):
    telemetry_delta_explains_share = optional_ratio(
        candidate_index_delta, telemetry_overhead_with
    )
    terminal_delta_explains_share = optional_ratio(
        terminal_parent_delta, telemetry_overhead_with
    )
    residual_share_of_candidate = optional_ratio(
        telemetry_overhead_without, candidate_index_without
    )

    if telemetry_delta_explains_share is not None and telemetry_delta_explains_share >= 0.80:
        return (
            "profiler_only_overhead",
            "reduce_or_cold_path_profiler_telemetry",
            telemetry_delta_explains_share,
            terminal_delta_explains_share,
            residual_share_of_candidate,
        )

    if (
        terminal_delta_explains_share is not None
        and terminal_delta_explains_share >= 0.80
        and (telemetry_delta_explains_share is None or telemetry_delta_explains_share < 0.30)
    ):
        return (
            "benchmark_telemetry_overhead",
            "reduce_or_cold_path_profiler_telemetry",
            telemetry_delta_explains_share,
            terminal_delta_explains_share,
            residual_share_of_candidate,
        )

    if (
        residual_share_of_candidate is not None
        and residual_share_of_candidate >= material_threshold_share
    ):
        return (
            "production_hot_path_bookkeeping",
            "profile_production_bookkeeping_path",
            telemetry_delta_explains_share,
            terminal_delta_explains_share,
            residual_share_of_candidate,
        )

    if (
        telemetry_delta_explains_share is not None
        and 0.30 <= telemetry_delta_explains_share < 0.80
    ):
        return (
            "mixed",
            "split_terminal_telemetry_overhead_source",
            telemetry_delta_explains_share,
            terminal_delta_explains_share,
            residual_share_of_candidate,
        )

    return (
        "unknown",
        "inspect_terminal_telemetry_timer_scope",
        telemetry_delta_explains_share,
        terminal_delta_explains_share,
        residual_share_of_candidate,
    )


def build_summary(
    *,
    with_summary,
    without_summary,
    forced_off_summary,
    with_path,
    without_path,
    forced_off_path,
    current_branch,
    material_threshold_share,
):
    with_candidate = require_mapping(with_summary, "candidate_index")
    without_candidate = require_mapping(without_summary, "candidate_index")

    candidate_index_with = require_float(with_candidate, "seconds")
    candidate_index_without = require_float(without_candidate, "seconds")
    terminal_parent_with = require_float(with_candidate, "terminal_path_parent_seconds")
    terminal_parent_without = require_float(without_candidate, "terminal_path_parent_seconds")
    telemetry_overhead_with = require_float(
        with_candidate, "terminal_path_telemetry_overhead_seconds"
    )
    telemetry_overhead_without = require_float(
        without_candidate, "terminal_path_telemetry_overhead_seconds"
    )

    candidate_index_delta = nonnegative_delta(
        candidate_index_with, candidate_index_without
    )
    terminal_parent_delta = nonnegative_delta(
        terminal_parent_with, terminal_parent_without
    )

    (
        telemetry_branch_kind,
        recommended_next_action,
        telemetry_delta_explains_share,
        terminal_delta_explains_share,
        residual_share_of_candidate,
    ) = classify_branch(
        candidate_index_delta=candidate_index_delta,
        terminal_parent_delta=terminal_parent_delta,
        telemetry_overhead_with=telemetry_overhead_with,
        telemetry_overhead_without=telemetry_overhead_without,
        candidate_index_without=candidate_index_without,
        material_threshold_share=material_threshold_share,
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
    terminal_telemetry_mode_status = classify_mode_status(with_mode, without_mode)

    forced_off_mode = None
    off_equivalence_status = "not_checked"
    off_equivalence_case_comparison = {
        "case_set_consistency_status": "not_checked",
        "behavior_consistency_status": "not_checked",
    }
    off_equivalence_candidate_index_delta = None
    off_equivalence_terminal_parent_delta = None
    if forced_off_summary is not None:
        forced_off_mode = extract_mode_metadata(forced_off_summary)
        forced_off_candidate = require_mapping(forced_off_summary, "candidate_index")
        off_equivalence_candidate_index_delta = abs(
            candidate_index_without - require_float(forced_off_candidate, "seconds")
        )
        off_equivalence_terminal_parent_delta = abs(
            terminal_parent_without
            - require_float(forced_off_candidate, "terminal_path_parent_seconds")
        )
        off_equivalence_case_comparison = compare_cases(
            without_summary, forced_off_summary
        )
        off_equivalence_status = (
            "matched"
            if (
                forced_off_mode["effective"] == "off"
                and off_equivalence_case_comparison["case_set_consistency_status"]
                == "matched"
                and off_equivalence_case_comparison["behavior_consistency_status"]
                == "matched"
            )
            else "mismatch"
        )

    decision_status = "ready"
    if case_comparison["case_set_consistency_status"] == "mismatch":
        decision_status = "not_ready"
        telemetry_branch_kind = "unknown"
        recommended_next_action = "inspect_terminal_telemetry_case_set_mismatch"
    elif case_comparison["behavior_consistency_status"] == "mismatch":
        decision_status = "not_ready"
        telemetry_branch_kind = "unknown"
        recommended_next_action = "inspect_no_terminal_telemetry_semantic_drift"
    elif terminal_telemetry_mode_status == "mismatch":
        decision_status = "not_ready"
        telemetry_branch_kind = "unknown"
        recommended_next_action = "rerun_with_explicit_terminal_telemetry_modes"
    elif off_equivalence_status == "mismatch":
        decision_status = "not_ready"
        telemetry_branch_kind = "unknown"
        recommended_next_action = "inspect_terminal_telemetry_off_equivalence_drift"

    summary = {
        "decision_status": decision_status,
        "runtime_prototype_allowed": False,
        "current_branch": current_branch,
        "candidate_index_materiality_status": candidate_index_materiality_status,
        "profile_mode_overhead_status": profile_mode_overhead_status,
        "trusted_span_timing": trusted_span_timing,
        "trusted_span_source": trusted_span_source,
        "with_terminal_telemetry_summary": str(with_path),
        "without_terminal_telemetry_summary": str(without_path),
        "forced_off_terminal_telemetry_summary": (
            str(forced_off_path) if forced_off_path is not None else None
        ),
        "with_terminal_telemetry_profile_mode": with_mode["profile_mode"],
        "with_terminal_telemetry_mode_requested": with_mode["requested"],
        "with_terminal_telemetry_mode_effective": with_mode["effective"],
        "without_terminal_telemetry_profile_mode": without_mode["profile_mode"],
        "without_terminal_telemetry_mode_requested": without_mode["requested"],
        "without_terminal_telemetry_mode_effective": without_mode["effective"],
        "forced_off_terminal_telemetry_profile_mode": (
            forced_off_mode["profile_mode"] if forced_off_mode else None
        ),
        "forced_off_terminal_telemetry_mode_requested": (
            forced_off_mode["requested"] if forced_off_mode else None
        ),
        "forced_off_terminal_telemetry_mode_effective": (
            forced_off_mode["effective"] if forced_off_mode else None
        ),
        "terminal_telemetry_mode_status": terminal_telemetry_mode_status,
        "candidate_index_seconds_with_terminal_telemetry": candidate_index_with,
        "candidate_index_seconds_without_terminal_telemetry": candidate_index_without,
        "candidate_index_seconds_delta_without_terminal_telemetry": candidate_index_delta,
        "terminal_parent_seconds_with_terminal_telemetry": terminal_parent_with,
        "terminal_parent_seconds_without_terminal_telemetry": terminal_parent_without,
        "terminal_parent_seconds_delta_without_terminal_telemetry": terminal_parent_delta,
        "terminal_path_telemetry_overhead_seconds_with": telemetry_overhead_with,
        "terminal_path_telemetry_overhead_seconds_without": telemetry_overhead_without,
        "telemetry_delta_explains_share": telemetry_delta_explains_share,
        "terminal_delta_explains_share": terminal_delta_explains_share,
        "terminal_path_telemetry_overhead_residual_share_of_candidate_index": residual_share_of_candidate,
        "case_set_consistency_status": case_comparison["case_set_consistency_status"],
        "behavior_consistency_status": case_comparison["behavior_consistency_status"],
        "with_case_ids": case_comparison["with_case_ids"],
        "without_case_ids": case_comparison["without_case_ids"],
        "semantic_drift_field_mismatches": case_comparison["semantic_drift_field_mismatches"],
        "workload_id": case_comparison.get("workload_id"),
        "off_equivalence_status": off_equivalence_status,
        "off_equivalence_case_set_consistency_status": off_equivalence_case_comparison[
            "case_set_consistency_status"
        ],
        "off_equivalence_behavior_consistency_status": (
            off_equivalence_case_comparison["behavior_consistency_status"]
        ),
        "off_equivalence_candidate_index_delta": off_equivalence_candidate_index_delta,
        "off_equivalence_terminal_parent_delta": off_equivalence_terminal_parent_delta,
        "telemetry_branch_kind": telemetry_branch_kind,
        "recommended_next_action": recommended_next_action,
        "material_threshold_share_of_candidate_index": material_threshold_share,
    }
    return summary


def render_markdown(summary):
    lines = [
        "# SIM Initial Host Merge Terminal Telemetry Classification",
        "",
        f"- current_branch: `{summary['current_branch']}`",
        f"- telemetry_branch_kind: `{summary['telemetry_branch_kind']}`",
        f"- recommended_next_action: `{summary['recommended_next_action']}`",
        f"- runtime_prototype_allowed: `{str(summary['runtime_prototype_allowed']).lower()}`",
        f"- case_set_consistency_status: `{summary['case_set_consistency_status']}`",
        f"- behavior_consistency_status: `{summary['behavior_consistency_status']}`",
        f"- terminal_telemetry_mode_status: `{summary['terminal_telemetry_mode_status']}`",
        f"- off_equivalence_status: `{summary['off_equivalence_status']}`",
        "",
        "| metric | value |",
        "| --- | ---: |",
        f"| with_terminal_telemetry_mode_requested | {summary['with_terminal_telemetry_mode_requested']} |",
        f"| with_terminal_telemetry_mode_effective | {summary['with_terminal_telemetry_mode_effective']} |",
        f"| without_terminal_telemetry_mode_requested | {summary['without_terminal_telemetry_mode_requested']} |",
        f"| without_terminal_telemetry_mode_effective | {summary['without_terminal_telemetry_mode_effective']} |",
        f"| forced_off_terminal_telemetry_mode_requested | {summary['forced_off_terminal_telemetry_mode_requested'] or 'n/a'} |",
        f"| forced_off_terminal_telemetry_mode_effective | {summary['forced_off_terminal_telemetry_mode_effective'] or 'n/a'} |",
        f"| candidate_index_seconds_with_terminal_telemetry | {format_metric(summary['candidate_index_seconds_with_terminal_telemetry'])} |",
        f"| candidate_index_seconds_without_terminal_telemetry | {format_metric(summary['candidate_index_seconds_without_terminal_telemetry'])} |",
        f"| candidate_index_seconds_delta_without_terminal_telemetry | {format_metric(summary['candidate_index_seconds_delta_without_terminal_telemetry'])} |",
        f"| terminal_parent_seconds_with_terminal_telemetry | {format_metric(summary['terminal_parent_seconds_with_terminal_telemetry'])} |",
        f"| terminal_parent_seconds_without_terminal_telemetry | {format_metric(summary['terminal_parent_seconds_without_terminal_telemetry'])} |",
        f"| terminal_parent_seconds_delta_without_terminal_telemetry | {format_metric(summary['terminal_parent_seconds_delta_without_terminal_telemetry'])} |",
        f"| terminal_path_telemetry_overhead_seconds_with | {format_metric(summary['terminal_path_telemetry_overhead_seconds_with'])} |",
        f"| terminal_path_telemetry_overhead_seconds_without | {format_metric(summary['terminal_path_telemetry_overhead_seconds_without'])} |",
        f"| telemetry_delta_explains_share | {format_metric(summary['telemetry_delta_explains_share'])} |",
        f"| terminal_delta_explains_share | {format_metric(summary['terminal_delta_explains_share'])} |",
        f"| residual_share_of_candidate_index | {format_metric(summary['terminal_path_telemetry_overhead_residual_share_of_candidate_index'])} |",
        f"| off_equivalence_candidate_index_delta | {format_metric(summary['off_equivalence_candidate_index_delta'])} |",
        f"| off_equivalence_terminal_parent_delta | {format_metric(summary['off_equivalence_terminal_parent_delta'])} |",
        "",
    ]
    return "\n".join(lines)


def write_cases_tsv(path, summary):
    fieldnames = [
        "current_branch",
        "telemetry_branch_kind",
        "recommended_next_action",
        "terminal_telemetry_mode_status",
        "off_equivalence_status",
        "with_terminal_telemetry_mode_requested",
        "with_terminal_telemetry_mode_effective",
        "without_terminal_telemetry_mode_requested",
        "without_terminal_telemetry_mode_effective",
        "forced_off_terminal_telemetry_mode_requested",
        "forced_off_terminal_telemetry_mode_effective",
        "candidate_index_seconds_with_terminal_telemetry",
        "candidate_index_seconds_without_terminal_telemetry",
        "candidate_index_seconds_delta_without_terminal_telemetry",
        "terminal_parent_seconds_with_terminal_telemetry",
        "terminal_parent_seconds_without_terminal_telemetry",
        "terminal_parent_seconds_delta_without_terminal_telemetry",
        "terminal_path_telemetry_overhead_seconds_with",
        "terminal_path_telemetry_overhead_seconds_without",
        "telemetry_delta_explains_share",
        "terminal_delta_explains_share",
        "terminal_path_telemetry_overhead_residual_share_of_candidate_index",
        "off_equivalence_candidate_index_delta",
        "off_equivalence_terminal_parent_delta",
        "case_set_consistency_status",
        "behavior_consistency_status",
        "off_equivalence_case_set_consistency_status",
        "off_equivalence_behavior_consistency_status",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerow({field: summary.get(field, "") for field in fieldnames})


def main():
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    with_summary, with_path = read_json(args.with_terminal_telemetry_summary)
    without_summary, without_path = read_json(args.without_terminal_telemetry_summary)
    forced_off_summary, forced_off_path = (
        read_json(args.forced_off_terminal_telemetry_summary)
        if args.forced_off_terminal_telemetry_summary
        else (None, None)
    )

    summary = build_summary(
        with_summary=with_summary,
        without_summary=without_summary,
        forced_off_summary=forced_off_summary,
        with_path=with_path,
        without_path=without_path,
        forced_off_path=forced_off_path,
        current_branch=args.current_branch,
        material_threshold_share=args.material_threshold_share_of_candidate_index,
    )
    decision = {
        "decision_status": summary["decision_status"],
        "runtime_prototype_allowed": summary["runtime_prototype_allowed"],
        "current_branch": summary["current_branch"],
        "telemetry_branch_kind": summary["telemetry_branch_kind"],
        "recommended_next_action": summary["recommended_next_action"],
        "terminal_telemetry_mode_status": summary["terminal_telemetry_mode_status"],
        "off_equivalence_status": summary["off_equivalence_status"],
        "candidate_index_seconds_delta_without_terminal_telemetry": summary[
            "candidate_index_seconds_delta_without_terminal_telemetry"
        ],
        "terminal_parent_seconds_delta_without_terminal_telemetry": summary[
            "terminal_parent_seconds_delta_without_terminal_telemetry"
        ],
        "telemetry_delta_explains_share": summary["telemetry_delta_explains_share"],
        "terminal_delta_explains_share": summary["terminal_delta_explains_share"],
    }

    with (output_dir / "terminal_telemetry_classification_summary.json").open(
        "w", encoding="utf-8"
    ) as handle:
        json.dump(summary, handle, indent=2, sort_keys=True)
        handle.write("\n")
    with (output_dir / "terminal_telemetry_classification_decision.json").open(
        "w", encoding="utf-8"
    ) as handle:
        json.dump(decision, handle, indent=2, sort_keys=True)
        handle.write("\n")
    write_cases_tsv(
        output_dir / "terminal_telemetry_classification_cases.tsv", summary
    )
    (output_dir / "terminal_telemetry_classification_summary.md").write_text(
        render_markdown(summary) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
