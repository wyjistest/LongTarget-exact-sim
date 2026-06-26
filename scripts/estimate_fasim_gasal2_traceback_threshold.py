#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Iterable


TOP5_KEYS = (
    "top5_score_equal",
    "top5_stability_equal",
    "top5_nt_score_equal",
)


def parse_bool(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def parse_int(value: str | None) -> int | None:
    if value is None or value == "":
        return None
    return int(float(value))


def parse_float(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def read_query_fasta_lengths(path: Path | None) -> list[int]:
    if path is None:
        return []
    lengths: list[int] = []
    current = 0
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            if line.startswith(">"):
                if current:
                    lengths.append(current)
                current = 0
            else:
                current += len(line)
    if current:
        lengths.append(current)
    return lengths


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def row_threshold(row: dict[str, str]) -> int:
    value = parse_int(row.get("threshold"))
    if value is None:
        raise ValueError("summary row is missing threshold")
    return value


def row_passes(row: dict[str, str]) -> bool:
    return all(parse_bool(row.get(key)) for key in TOP5_KEYS)


def row_fail_contracts(row: dict[str, str]) -> list[str]:
    return [key.removeprefix("top5_").removesuffix("_equal")
            for key in TOP5_KEYS
            if not parse_bool(row.get(key))]


def infer_baseline_traceback(rows: Iterable[dict[str, str]]) -> int | None:
    inferred: list[int] = []
    for row in rows:
        traceback = parse_int(row.get("traceback_requests"))
        reduction = parse_int(row.get("traceback_reduction"))
        if traceback is not None and reduction is not None:
            inferred.append(traceback + reduction)
    if not inferred:
        return None
    return max(inferred)


def format_value(value: object) -> str:
    if value is None:
        return "NA"
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value)


def emit_metric(metrics: list[tuple[str, object]], key: str, value: object) -> None:
    metrics.append((key, value))


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Estimate a query-specific GASAL2 traceback min-prealign threshold "
            "from a threshold sweep TSV."
        )
    )
    parser.add_argument("--summary", required=True, type=Path)
    parser.add_argument("--query-label", default="unknown")
    parser.add_argument("--query-fasta", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--require-failing-boundary",
        action="store_true",
        help="Exit nonzero unless at least one failing threshold above the recommendation is observed.",
    )
    parser.add_argument(
        "--min-baseline-traceback-requests",
        type=int,
        default=0,
        help="Fail closed when the calibration sample has too little traceback work.",
    )
    args = parser.parse_args()

    rows = sorted(read_rows(args.summary), key=row_threshold)
    if not rows:
        raise SystemExit("summary has no rows")

    passing = [row for row in rows if row_passes(row)]
    failing = [row for row in rows if not row_passes(row)]
    baseline_traceback = infer_baseline_traceback(rows)

    query_lengths = read_query_fasta_lengths(args.query_fasta)
    query_total_bases = sum(query_lengths) if query_lengths else None

    metrics: list[tuple[str, object]] = []
    emit_metric(metrics, "query_label", args.query_label)
    emit_metric(metrics, "summary", str(args.summary))
    emit_metric(metrics, "rows", len(rows))
    emit_metric(metrics, "threshold_min", row_threshold(rows[0]))
    emit_metric(metrics, "threshold_max", row_threshold(rows[-1]))
    emit_metric(metrics, "passing_thresholds", ",".join(str(row_threshold(row)) for row in passing))
    emit_metric(metrics, "failing_thresholds", ",".join(str(row_threshold(row)) for row in failing))
    emit_metric(metrics, "baseline_traceback_requests", baseline_traceback)
    emit_metric(metrics,
                "baseline_traceback_min_required",
                args.min_baseline_traceback_requests)
    emit_metric(metrics, "query_record_count", len(query_lengths) if query_lengths else None)
    emit_metric(metrics, "query_total_bases", query_total_bases)

    if (baseline_traceback is None
            or baseline_traceback < args.min_baseline_traceback_requests):
        emit_metric(metrics, "decision", "insufficient_traceback_signal_expand_sampling")
        emit_metric(metrics, "recommended_threshold", "NA")
        emit_metric(metrics, "first_failing_threshold", "NA")
        emit_metric(metrics, "first_failing_contracts", "NA")
        emit_metric(metrics, "confidence", "insufficient_traceback_signal")
        emit_metric(metrics,
                    "runtime_recommendation",
                    "none_without_same_query_validation")
        text = "".join(f"{key}={format_value(value)}\n" for key, value in metrics)
        if args.output:
            args.output.write_text(text, encoding="utf-8")
        else:
            print(text, end="")
        return 1

    if not passing:
        emit_metric(metrics, "decision", "no_safe_threshold_observed")
        emit_metric(metrics, "recommended_threshold", "NA")
        emit_metric(metrics, "first_failing_threshold", row_threshold(failing[0]) if failing else "NA")
        emit_metric(metrics, "first_failing_contracts",
                    ",".join(row_fail_contracts(failing[0])) if failing else "NA")
        emit_metric(metrics, "confidence", "insufficient_no_passing_threshold")
        text = "".join(f"{key}={format_value(value)}\n" for key, value in metrics)
        if args.output:
            args.output.write_text(text, encoding="utf-8")
        else:
            print(text, end="")
        return 1 if args.require_failing_boundary else 0

    recommended = max(passing, key=row_threshold)
    recommended_threshold = row_threshold(recommended)
    failures_above = [row for row in failing if row_threshold(row) > recommended_threshold]
    first_failure = min(failures_above, key=row_threshold) if failures_above else None
    lower_failures = [row for row in failing if row_threshold(row) < recommended_threshold]

    if first_failure is not None:
        decision = "query_specific_threshold_candidate"
        confidence = "bounded_by_observed_failure"
    else:
        decision = "threshold_lower_bound_only_expand_sweep"
        confidence = "no_failing_boundary_observed"

    emit_metric(metrics, "decision", decision)
    emit_metric(metrics, "recommended_threshold", recommended_threshold)
    emit_metric(metrics, "recommended_threshold_is_query_specific", 1)
    emit_metric(metrics, "recommended_traceback_requests",
                parse_int(recommended.get("traceback_requests")))
    emit_metric(metrics, "recommended_traceback_reduction",
                parse_int(recommended.get("traceback_reduction")))
    emit_metric(metrics, "recommended_traceback_reduction_fraction",
                parse_float(recommended.get("traceback_reduction_fraction")))
    emit_metric(metrics, "recommended_wall_seconds",
                parse_float(recommended.get("wall_seconds")))
    emit_metric(metrics, "recommended_vs_baseline_wall",
                parse_float(recommended.get("vs_baseline_gasal2_wall")))
    if query_total_bases:
        emit_metric(metrics,
                    "recommended_threshold_per_query_base",
                    recommended_threshold / query_total_bases)
    else:
        emit_metric(metrics, "recommended_threshold_per_query_base", None)

    emit_metric(metrics, "first_failing_threshold",
                row_threshold(first_failure) if first_failure else "NA")
    emit_metric(metrics, "first_failing_contracts",
                ",".join(row_fail_contracts(first_failure)) if first_failure else "NA")
    emit_metric(metrics, "safety_margin_to_first_failure",
                row_threshold(first_failure) - recommended_threshold if first_failure else "NA")
    emit_metric(metrics, "non_monotonic_failures_below_recommendation",
                len(lower_failures))
    emit_metric(metrics, "confidence", confidence)
    emit_metric(metrics,
                "runtime_recommendation",
                "none_without_same_query_validation")

    text = "".join(f"{key}={format_value(value)}\n" for key, value in metrics)
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")

    if args.require_failing_boundary and first_failure is None:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
