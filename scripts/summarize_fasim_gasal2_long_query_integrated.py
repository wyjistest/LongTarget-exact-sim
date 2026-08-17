#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import math
import statistics
from collections import defaultdict
from pathlib import Path


CONTRACT_ONES = (
    "full_output_byte_equal",
    "top5_score_equal",
    "top5_stability_equal",
    "top5_nt_score_equal",
    "offline_clustered_top5_equal",
    "archive_restore_clean",
)

INTEGER_FIELDS = (
    "repeat",
    "baseline_gasal2_requests",
    "candidate_gasal2_requests",
    "baseline_traceback_requests",
    "candidate_traceback_requests",
    "exact_work_tasks",
    "exact_work_cells",
    "baseline_archive_bytes",
    "candidate_archive_bytes",
    "baseline_peak_rss_kb",
    "candidate_peak_rss_kb",
    "temporary_text_bytes",
    "fallbacks",
    "oom",
    *CONTRACT_ONES,
)

FLOAT_FIELDS = (
    "baseline_pipeline_wall_seconds",
    "candidate_pipeline_wall_seconds",
    "baseline_exact_stage_seconds",
    "candidate_exact_stage_seconds",
    "baseline_traceback_stage_seconds",
    "candidate_traceback_stage_seconds",
)

DETAIL_FIELDS = (
    "workload",
    "repeats",
    "baseline_wall_median",
    "candidate_wall_median",
    "speedup",
    "wall_reduction_percent",
    "baseline_wall_min",
    "baseline_wall_q1",
    "baseline_wall_q3",
    "baseline_wall_max",
    "candidate_wall_min",
    "candidate_wall_q1",
    "candidate_wall_q3",
    "candidate_wall_max",
    "direction_stable",
    "baseline_exact_stage_median",
    "candidate_exact_stage_median",
    "exact_stage_reduction_percent",
    "baseline_traceback_stage_median",
    "candidate_traceback_stage_median",
    "baseline_archive_bytes_max",
    "candidate_archive_bytes_max",
    "baseline_peak_rss_kb_max",
    "candidate_peak_rss_kb_max",
    "contracts_clean",
)


class SummaryError(ValueError):
    pass


def parse_int(value: str, field: str, source: Path) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise SummaryError(f"invalid integer {field}={value!r} in {source}") from exc
    if parsed < 0:
        raise SummaryError(f"invalid non-negative {field}={parsed} in {source}")
    return parsed


def parse_float(value: str, field: str, source: Path) -> float:
    try:
        parsed = float(value)
    except ValueError as exc:
        raise SummaryError(f"invalid float {field}={value!r} in {source}") from exc
    if not math.isfinite(parsed) or parsed < 0:
        raise SummaryError(f"invalid non-negative {field}={parsed} in {source}")
    return parsed


def read_rows(path: Path) -> list[dict[str, str | int | float]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        missing = sorted(
            {"workload", "decision", *INTEGER_FIELDS, *FLOAT_FIELDS}
            - set(reader.fieldnames or ())
        )
        if missing:
            raise SummaryError(f"missing pair fields in {path}: {missing}")
        raw_rows = list(reader)
    rows: list[dict[str, str | int | float]] = []
    seen: set[tuple[str, int]] = set()
    for raw in raw_rows:
        row: dict[str, str | int | float] = dict(raw)
        for field in INTEGER_FIELDS:
            row[field] = parse_int(raw[field], field, path)
        for field in FLOAT_FIELDS:
            row[field] = parse_float(raw[field], field, path)
        key = (str(row["workload"]), int(row["repeat"]))
        if key in seen:
            raise SummaryError(f"duplicate workload/repeat pair: {key}")
        seen.add(key)
        if raw["decision"] != "paired_integrated_contract_clean":
            raise SummaryError(f"dirty pair contract decision for {key}: {raw['decision']}")
        for field in CONTRACT_ONES:
            if int(row[field]) != 1:
                raise SummaryError(f"dirty pair contract {field}=0 for {key}")
        for field in ("temporary_text_bytes", "fallbacks", "oom"):
            if int(row[field]) != 0:
                raise SummaryError(f"dirty pair contract {field}={row[field]} for {key}")
        rows.append(row)
    if not rows:
        raise SummaryError(f"no pair rows in {path}")
    return rows


def spread(values: list[float]) -> tuple[float, float, float, float]:
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0], ordered[0], ordered[0], ordered[0]
    quartiles = statistics.quantiles(ordered, n=4, method="inclusive")
    return ordered[0], quartiles[0], quartiles[2], ordered[-1]


def reduction(baseline: float, candidate: float) -> float:
    return 100.0 * (baseline - candidate) / baseline if baseline else 0.0


def summarize_workload(
    workload: str, rows: list[dict[str, str | int | float]]
) -> dict[str, str | int]:
    baseline_wall = [float(row["baseline_pipeline_wall_seconds"]) for row in rows]
    candidate_wall = [float(row["candidate_pipeline_wall_seconds"]) for row in rows]
    baseline_exact = [float(row["baseline_exact_stage_seconds"]) for row in rows]
    candidate_exact = [float(row["candidate_exact_stage_seconds"]) for row in rows]
    baseline_traceback = [float(row["baseline_traceback_stage_seconds"]) for row in rows]
    candidate_traceback = [float(row["candidate_traceback_stage_seconds"]) for row in rows]
    base_median = statistics.median(baseline_wall)
    candidate_median = statistics.median(candidate_wall)
    base_exact_median = statistics.median(baseline_exact)
    candidate_exact_median = statistics.median(candidate_exact)
    base_traceback_median = statistics.median(baseline_traceback)
    candidate_traceback_median = statistics.median(candidate_traceback)
    base_spread = spread(baseline_wall)
    candidate_spread = spread(candidate_wall)
    return {
        "workload": workload,
        "repeats": len(rows),
        "baseline_wall_median": f"{base_median:.6f}",
        "candidate_wall_median": f"{candidate_median:.6f}",
        "speedup": f"{base_median / candidate_median if candidate_median else 0.0:.6f}",
        "wall_reduction_percent": f"{reduction(base_median, candidate_median):.6f}",
        "baseline_wall_min": f"{base_spread[0]:.6f}",
        "baseline_wall_q1": f"{base_spread[1]:.6f}",
        "baseline_wall_q3": f"{base_spread[2]:.6f}",
        "baseline_wall_max": f"{base_spread[3]:.6f}",
        "candidate_wall_min": f"{candidate_spread[0]:.6f}",
        "candidate_wall_q1": f"{candidate_spread[1]:.6f}",
        "candidate_wall_q3": f"{candidate_spread[2]:.6f}",
        "candidate_wall_max": f"{candidate_spread[3]:.6f}",
        "direction_stable": int(
            all(candidate < baseline for baseline, candidate in zip(baseline_wall, candidate_wall))
        ),
        "baseline_exact_stage_median": f"{base_exact_median:.6f}",
        "candidate_exact_stage_median": f"{candidate_exact_median:.6f}",
        "exact_stage_reduction_percent": f"{reduction(base_exact_median, candidate_exact_median):.6f}",
        "baseline_traceback_stage_median": f"{base_traceback_median:.6f}",
        "candidate_traceback_stage_median": f"{candidate_traceback_median:.6f}",
        "baseline_archive_bytes_max": max(int(row["baseline_archive_bytes"]) for row in rows),
        "candidate_archive_bytes_max": max(int(row["candidate_archive_bytes"]) for row in rows),
        "baseline_peak_rss_kb_max": max(int(row["baseline_peak_rss_kb"]) for row in rows),
        "candidate_peak_rss_kb_max": max(int(row["candidate_peak_rss_kb"]) for row in rows),
        "contracts_clean": 1,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Summarize paired Phase 7 integrated long-query benchmarks."
    )
    parser.add_argument("--pairs", required=True, type=Path)
    parser.add_argument("--details", required=True, type=Path)
    parser.add_argument("--summary", required=True, type=Path)
    args = parser.parse_args()

    rows = read_rows(args.pairs)
    grouped: dict[str, list[dict[str, str | int | float]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["workload"])].append(row)
    details = [summarize_workload(name, grouped[name]) for name in sorted(grouped)]
    by_name = {str(row["workload"]): row for row in details}

    max8 = by_name.get("max8")
    max8_repeats = int(max8["repeats"]) if max8 else 0
    max8_direction_stable = int(max8["direction_stable"]) if max8 else 0
    max8_reduction = float(max8["wall_reduction_percent"]) if max8 else 0.0
    full_allowed = int(
        max8 is not None
        and max8_repeats >= 2
        and max8_direction_stable == 1
        and max8_reduction >= 10.0
    )

    short = by_name.get("h19_short")
    short_regression = (
        -float(short["wall_reduction_percent"]) if short is not None else float("inf")
    )
    short_gate = int(short is not None and short_regression <= 3.0)

    summary: dict[str, str | int] = {
        "pair_rows": len(rows),
        "workloads": ",".join(sorted(grouped)),
        "all_pair_contracts_clean": 1,
        "max8_repeats": max8_repeats,
        "max8_direction_stable": max8_direction_stable,
        "max8_median_wall_reduction_percent": f"{max8_reduction:.6f}",
        "max8_full_run_allowed": full_allowed,
        "short_query_regression_percent": (
            f"{short_regression:.6f}" if math.isfinite(short_regression) else "unavailable"
        ),
        "short_query_regression_gate": short_gate,
        "decision": (
            "full_run_allowed"
            if full_allowed and short_gate
            else "bounded_only_full_run_not_allowed"
        ),
    }
    for workload, detail in by_name.items():
        prefix = workload.replace("-", "_")
        summary[f"{prefix}_repeats"] = detail["repeats"]
        summary[f"{prefix}_baseline_wall_median"] = detail["baseline_wall_median"]
        summary[f"{prefix}_candidate_wall_median"] = detail["candidate_wall_median"]
        summary[f"{prefix}_speedup"] = detail["speedup"]
        summary[f"{prefix}_wall_reduction_percent"] = detail["wall_reduction_percent"]

    args.details.parent.mkdir(parents=True, exist_ok=True)
    with args.details.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=DETAIL_FIELDS, delimiter="\t", lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(details)
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    output = "".join(f"{key}={value}\n" for key, value in summary.items())
    args.summary.write_text(output, encoding="utf-8")
    print(output, end="")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, UnicodeError, SummaryError) as exc:
        raise SystemExit(str(exc)) from exc
