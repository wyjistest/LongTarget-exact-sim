#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path


PREFIX_ELIGIBILITY = "benchmark.fasim_gasal2_pretraceback_pruning_eligibility_"
PREFIX_BENCH = "benchmark."

FIELDS = [
    "workload_name",
    "status",
    "decision",
    "target",
    "query",
    "mode",
    "workers",
    "group_target_records",
    "output_mode",
    "gasal2_runtime_env",
    "tracebacks_requested",
    "eligibility_attempts",
    "retained_final_rows",
    "removed_attempts",
    "pretraceback_span_provable",
    "pretraceback_span_fraction_of_traceback",
    "pretraceback_span_fraction_of_removed",
    "post_traceback_only_attempts",
    "unknown_eligibility_attempts",
    "mapped_removed_attempts",
    "unmapped_removed_attempts",
    "cigar_dependent_duplicate",
    "cigar_dependent_span",
    "same_final_row_different_descriptor",
    "sort_or_dominance_removed",
    "full_output_safe_candidate_attempts",
    "false_prune_shadow",
    "missing_rows_shadow",
    "extra_rows_shadow",
    "baseline_lite_rows",
    "candidate_lite_rows",
    "full_lite_missing_rows",
    "full_lite_extra_rows",
    "baseline_tfosorted_rows",
    "candidate_tfosorted_rows",
    "full_tfosorted_missing_rows",
    "full_tfosorted_extra_rows",
    "top5_score_equal",
    "top5_stability_equal",
    "top5_nt_score_equal",
    "timing_split_available",
    "gasal2_wall_seconds",
    "gasal2_extend_seconds",
    "gasal2_convert_seconds",
    "gasal2_traceback_seconds",
    "exact_column_seconds",
    "output_write_seconds",
    "projected_saved_traceback_requests",
    "projected_saved_traceback_fraction",
    "projected_saved_traceback_seconds",
    "projected_wall_speedup_if_span_pruned",
    "artifact_provenance",
    "notes",
]

ELIGIBILITY_INT_KEYS = [
    "attempts",
    "retained_final_rows",
    "removed_attempts",
    "mapped_removed_attempts",
    "unmapped_removed_attempts",
    "pretraceback_span_provable",
    "cigar_dependent_duplicate",
    "cigar_dependent_span",
    "same_final_row_different_descriptor",
    "sort_or_dominance_removed",
    "false_prune_shadow",
    "missing_rows_shadow",
    "extra_rows_shadow",
]

OPTIONAL_ELIGIBILITY_INT_DEFAULTS = {
    "full_output_safe_candidate_attempts": 0,
    "representative_selection_dependent": 0,
    "reverse_start_dependent_span": 0,
    "exact_request_duplicate": 0,
    "exact_descriptor_duplicate": 0,
    "cross_flush_exact_duplicate": 0,
}

BOOL_FIELDS = {
    "top5_score_equal",
    "top5_stability_equal",
    "top5_nt_score_equal",
    "timing_split_available",
}


def _read_key_values(path: Path | None) -> dict[str, str]:
    if path is None:
        return {}
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def _read_report_values(path: Path | None) -> dict[str, str]:
    if path is None:
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"runner report is not an object: {path}")
    values: dict[str, str] = {}
    bench = payload.get("fasim_benchmark_sums", {})
    if isinstance(bench, dict):
        for key, value in bench.items():
            values["benchmark." + str(key)] = str(value)
            if str(key).startswith("fasim_gasal2_pretraceback_pruning_eligibility_"):
                suffix = str(key).removeprefix(
                    "fasim_gasal2_pretraceback_pruning_eligibility_"
                )
                values["eligibility." + suffix] = str(value)
    if "merged_records" in payload:
        values["report.merged_records"] = str(payload["merged_records"])
    if "merged_raw_records" in payload:
        values["report.merged_raw_records"] = str(payload["merged_raw_records"])
    if "worker_count" in payload:
        values["report.worker_count"] = str(payload["worker_count"])
    if "group_target_records" in payload:
        values["report.group_target_records"] = str(payload["group_target_records"])
    if "merged_output" in payload:
        values["report.merged_output"] = str(payload["merged_output"])
    return values


def _parse_stderr(path: Path | None) -> dict[str, str]:
    if path is None:
        return {}
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key.startswith(PREFIX_ELIGIBILITY):
            values["eligibility." + key[len(PREFIX_ELIGIBILITY) :]] = value
        elif key.startswith(PREFIX_BENCH):
            values["benchmark." + key[len(PREFIX_BENCH) :]] = value
    return values


def _unknown_row(args: argparse.Namespace, status: str, decision: str, notes: str) -> dict[str, str]:
    row = {field: "unknown" for field in FIELDS}
    row.update(
        {
            "workload_name": args.workload_name,
            "status": status,
            "decision": decision,
            "target": args.target,
            "query": args.query,
            "mode": args.mode,
            "workers": args.workers,
            "group_target_records": args.group_target_records,
            "output_mode": args.output_mode,
            "gasal2_runtime_env": args.gasal2_runtime_env,
            "timing_split_available": "false",
            "projected_saved_traceback_seconds": "unknown",
            "projected_wall_speedup_if_span_pruned": "unknown",
            "artifact_provenance": args.artifact_provenance,
            "notes": notes,
        }
    )
    return row


def _as_int(values: dict[str, str], key: str) -> int:
    if key not in values:
        raise ValueError(f"missing required metric: {key}")
    value = values[key]
    try:
        return int(float(value))
    except ValueError as exc:
        raise ValueError(f"invalid integer metric {key}: {value}") from exc


def _optional_metric(values: dict[str, str], key: str, default: int) -> int:
    value = values.get(key)
    if value is None or value == "":
        return default
    try:
        return int(float(value))
    except ValueError as exc:
        raise ValueError(f"invalid integer metric {key}: {value}") from exc


def _as_float_text(values: dict[str, str], keys: list[str]) -> str:
    for key in keys:
        if key not in values:
            continue
        value = values[key]
        try:
            return f"{float(value):.6f}"
        except ValueError:
            continue
    return "unknown"


def _ratio(num: int, den: int) -> str:
    if den <= 0:
        return "unknown"
    return f"{num / den:.6f}"


def _bool_from_summary(values: dict[str, str], key: str) -> str:
    if key not in values:
        return "unknown"
    value = values[key].strip().lower()
    if value in {"true", "1", "yes"}:
        return "true"
    if value in {"false", "0", "no"}:
        return "false"
    return "unknown"


def _first_value(values: dict[str, str], keys: list[str], default: str = "unknown") -> str:
    for key in keys:
        if key in values and values[key] != "":
            return values[key]
    return default


def _combine_notes(*parts: str) -> str:
    cleaned = [part.strip() for part in parts if part and part.strip()]
    if not cleaned:
        return "none"
    return "; ".join(cleaned)


def _derive_decision(row: dict[str, str]) -> str:
    if row["status"] != "complete":
        return "no_decision"
    clean_values = [
        row["false_prune_shadow"] == "0",
        row["missing_rows_shadow"] == "0",
        row["extra_rows_shadow"] == "0",
        row["full_lite_missing_rows"] in {"0", "unknown"},
        row["full_lite_extra_rows"] in {"0", "unknown"},
        row["full_tfosorted_missing_rows"] in {"0", "unknown"},
        row["full_tfosorted_extra_rows"] in {"0", "unknown"},
        row["top5_score_equal"] in {"true", "unknown"},
        row["top5_stability_equal"] in {"true", "unknown"},
        row["top5_nt_score_equal"] in {"true", "unknown"},
        row["unknown_eligibility_attempts"] == "0",
    ]
    if not all(clean_values):
        return "no_go_contract_or_unknown_not_clean"
    fraction = 0.0
    try:
        fraction = float(row["projected_saved_traceback_fraction"])
    except ValueError:
        pass
    if row["timing_split_available"] == "true" and row["projected_saved_traceback_seconds"] != "unknown":
        try:
            if float(row["projected_saved_traceback_seconds"]) >= 1.0:
                return "weak_go_more_characterization_needed"
        except ValueError:
            pass
    if fraction >= 0.05:
        return "weak_go_more_characterization_needed"
    return "no_go_span_bucket_not_material"


def _parse_optional_int(text: str) -> int | None:
    if text == "unknown":
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


def build_row(args: argparse.Namespace) -> dict[str, str]:
    stderr_values = _parse_stderr(args.stderr)
    report_values = _read_report_values(args.runner_report)
    stderr_values.update({key: value for key, value in report_values.items() if key not in stderr_values})
    top5 = _read_key_values(args.top5_summary)
    lite = _read_key_values(args.full_lite_summary)
    tfosorted = _read_key_values(args.tfosorted_summary)

    if args.status != "complete":
        return _unknown_row(args, args.status, "no_decision", args.notes)

    try:
        metrics = {
            key: _as_int(stderr_values, "eligibility." + key)
            for key in ELIGIBILITY_INT_KEYS
        }
        for key, default in OPTIONAL_ELIGIBILITY_INT_DEFAULTS.items():
            metrics[key] = _optional_metric(stderr_values, "eligibility." + key, default)
    except ValueError as exc:
        return _unknown_row(
            args,
            "incomplete",
            "no_decision",
            _combine_notes(args.notes, str(exc)),
        )

    tracebacks = _parse_optional_int(
        _first_value(
            stderr_values,
            [
                "benchmark.fasim_gasal2_traceback_requests",
                "benchmark.fasim_gasal2_traceback_count",
            ],
            "unknown",
        )
    )
    if tracebacks is None:
        tracebacks = metrics["attempts"]

    removed = metrics["removed_attempts"]
    span = metrics["pretraceback_span_provable"]
    post_traceback_only = (
        metrics["same_final_row_different_descriptor"]
        + metrics["cigar_dependent_duplicate"]
        + metrics["representative_selection_dependent"]
        + metrics["sort_or_dominance_removed"]
        + metrics["reverse_start_dependent_span"]
        + metrics["cigar_dependent_span"]
    )

    gasal2_wall = _as_float_text(
        stderr_values,
        [
            "benchmark.total_wall_seconds",
            "benchmark.fasim_top5_gasal2_phase_flush_total_seconds",
            "benchmark.fasim_gasal2_wall_seconds",
        ],
    )
    gasal2_extend = _as_float_text(
        stderr_values,
        [
            "benchmark.fasim_gasal2_extend_wall_seconds",
            "benchmark.fasim_top5_gasal2_phase_gasal2_extend_wall_seconds",
            "benchmark.fasim_top5_gasal2_phase_gasal2_extend_seconds",
        ],
    )
    gasal2_convert = _as_float_text(
        stderr_values,
        [
            "benchmark.fasim_gasal2_convert_wall_seconds",
            "benchmark.fasim_top5_gasal2_phase_gasal2_convert_wall_seconds",
            "benchmark.fasim_top5_gasal2_phase_gasal2_convert_seconds",
        ],
    )
    exact_column = _as_float_text(
        stderr_values,
        [
            "benchmark.fasim_top5_gasal2_phase_exact_column_wall_seconds",
            "benchmark.fasim_top5_gasal2_phase_exact_column_seconds",
        ],
    )
    output_write = _as_float_text(
        stderr_values,
        [
            "benchmark.fasim_top5_gasal2_phase_output_write_seconds",
            "benchmark.fasim_gasal2_output_write_seconds",
        ],
    )
    gasal2_traceback = _as_float_text(
        stderr_values,
        [
            "benchmark.fasim_gasal2_traceback_seconds",
            "benchmark.fasim_top5_gasal2_phase_gasal2_traceback_seconds",
        ],
    )

    timing_split_available = "false"
    projected_saved_seconds = "unknown"
    projected_speedup = "unknown"
    if gasal2_traceback != "unknown":
        timing_split_available = "true"
        projected_saved = float(gasal2_traceback) * (span / tracebacks if tracebacks > 0 else 0.0)
        projected_saved_seconds = f"{projected_saved:.6f}"
        try:
            wall = float(gasal2_wall)
            if wall > projected_saved:
                projected_speedup = f"{wall / (wall - projected_saved):.6f}"
        except ValueError:
            projected_speedup = "unknown"

    row = {field: "unknown" for field in FIELDS}
    row.update(
        {
            "workload_name": args.workload_name,
            "status": "complete",
            "decision": "unknown",
            "target": args.target,
            "query": args.query,
            "mode": args.mode,
            "workers": args.workers,
            "group_target_records": args.group_target_records,
            "output_mode": args.output_mode,
            "gasal2_runtime_env": args.gasal2_runtime_env,
            "tracebacks_requested": str(tracebacks),
            "eligibility_attempts": str(metrics["attempts"]),
            "retained_final_rows": str(metrics["retained_final_rows"]),
            "removed_attempts": str(removed),
            "pretraceback_span_provable": str(span),
            "pretraceback_span_fraction_of_traceback": _ratio(span, tracebacks),
            "pretraceback_span_fraction_of_removed": _ratio(span, removed),
            "post_traceback_only_attempts": str(post_traceback_only),
            "unknown_eligibility_attempts": _first_value(
                stderr_values,
                ["eligibility.unknown"],
                "0",
            ),
            "mapped_removed_attempts": str(metrics["mapped_removed_attempts"]),
            "unmapped_removed_attempts": str(metrics["unmapped_removed_attempts"]),
            "cigar_dependent_duplicate": str(metrics["cigar_dependent_duplicate"]),
            "cigar_dependent_span": str(metrics["cigar_dependent_span"]),
            "same_final_row_different_descriptor": str(metrics["same_final_row_different_descriptor"]),
            "sort_or_dominance_removed": str(metrics["sort_or_dominance_removed"]),
            "full_output_safe_candidate_attempts": str(metrics["full_output_safe_candidate_attempts"]),
            "false_prune_shadow": str(metrics["false_prune_shadow"]),
            "missing_rows_shadow": str(metrics["missing_rows_shadow"]),
            "extra_rows_shadow": str(metrics["extra_rows_shadow"]),
            "baseline_lite_rows": _first_value(lite, ["baseline_rows", "baseline_lite_rows"]),
            "candidate_lite_rows": _first_value(lite, ["candidate_rows", "candidate_lite_rows"]),
            "full_lite_missing_rows": _first_value(lite, ["missing_rows", "full_lite_missing_rows"], "unknown"),
            "full_lite_extra_rows": _first_value(lite, ["extra_rows", "full_lite_extra_rows"], "unknown"),
            "baseline_tfosorted_rows": _first_value(tfosorted, ["baseline_rows", "baseline_tfosorted_rows"], _first_value(lite, ["baseline_rows", "baseline_lite_rows"])),
            "candidate_tfosorted_rows": _first_value(tfosorted, ["candidate_rows", "candidate_tfosorted_rows"], _first_value(lite, ["candidate_rows", "candidate_lite_rows"])),
            "full_tfosorted_missing_rows": _first_value(tfosorted, ["missing_rows", "full_tfosorted_missing_rows"], "unknown"),
            "full_tfosorted_extra_rows": _first_value(tfosorted, ["extra_rows", "full_tfosorted_extra_rows"], "unknown"),
            "top5_score_equal": _bool_from_summary(top5, "top5_score_equal"),
            "top5_stability_equal": _bool_from_summary(top5, "top5_stability_equal"),
            "top5_nt_score_equal": _bool_from_summary(top5, "top5_nt_score_equal"),
            "timing_split_available": timing_split_available,
            "gasal2_wall_seconds": gasal2_wall,
            "gasal2_extend_seconds": gasal2_extend,
            "gasal2_convert_seconds": gasal2_convert,
            "gasal2_traceback_seconds": gasal2_traceback,
            "exact_column_seconds": exact_column,
            "output_write_seconds": output_write,
            "projected_saved_traceback_requests": str(span),
            "projected_saved_traceback_fraction": _ratio(span, tracebacks),
            "projected_saved_traceback_seconds": projected_saved_seconds,
            "projected_wall_speedup_if_span_pruned": projected_speedup,
            "artifact_provenance": args.artifact_provenance,
            "notes": _combine_notes(
                args.notes,
                "traceback timing not split from extend"
                if timing_split_available == "false"
                else "",
            ),
        }
    )
    row["decision"] = _derive_decision(row)
    return row


def write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "unknown") for field in FIELDS})


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Summarize GASAL2 pre-traceback span real-workload characterization."
    )
    parser.add_argument("--workload-name", required=True)
    parser.add_argument("--status", default="complete", choices=["complete", "missing", "incomplete"])
    parser.add_argument("--stderr", type=Path)
    parser.add_argument("--runner-report", type=Path)
    parser.add_argument("--top5-summary", type=Path)
    parser.add_argument("--full-lite-summary", type=Path)
    parser.add_argument("--tfosorted-summary", type=Path)
    parser.add_argument("--target", default="unknown")
    parser.add_argument("--query", default="unknown")
    parser.add_argument("--mode", default="unknown")
    parser.add_argument("--workers", default="unknown")
    parser.add_argument("--group-target-records", default="unknown")
    parser.add_argument("--output-mode", default="unknown")
    parser.add_argument("--gasal2-runtime-env", default="unknown")
    parser.add_argument("--artifact-provenance", default="unknown")
    parser.add_argument("--notes", default="")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    row = build_row(args)
    write_rows(args.output, [row])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
