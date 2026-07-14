#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import math
import statistics
from pathlib import Path


METRICS = {
    "exact_batches": "benchmark.fasim_top5_gasal2_phase_exact_column_batches",
    "exact_tasks": "benchmark.fasim_top5_gasal2_phase_exact_column_tasks",
    "exact_cells": "benchmark.fasim_top5_gasal2_phase_exact_column_cells",
    "compact_batches": "benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_batches",
    "scoreinfo_tasks": "benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_tasks",
    "scoreinfo_cells": "benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_cells",
    "overflow_batches": "benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_overflow_batches",
    "exact_fallback_batches": "benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_fallback_batches",
    "column_wall_seconds": "benchmark.fasim_top5_gasal2_phase_exact_column_wall_seconds",
    "column_kernel_seconds": "benchmark.fasim_top5_gasal2_phase_exact_column_kernel_seconds",
    "column_h2d_seconds": "benchmark.fasim_top5_gasal2_phase_exact_column_h2d_seconds",
    "column_d2h_seconds": "benchmark.fasim_top5_gasal2_phase_exact_column_d2h_seconds",
    "compact_wall_seconds": "benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_wall_seconds",
    "compact_kernel_seconds": "benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_kernel_seconds",
    "compact_h2d_seconds": "benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_h2d_seconds",
    "compact_d2h_seconds": "benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_d2h_seconds",
    "gasal2_fallbacks": "benchmark.fasim_gasal2_fallbacks",
}

INTEGER_METRICS = {
    "exact_batches",
    "exact_tasks",
    "exact_cells",
    "compact_batches",
    "scoreinfo_tasks",
    "scoreinfo_cells",
    "overflow_batches",
    "exact_fallback_batches",
    "gasal2_fallbacks",
}


class SummaryError(ValueError):
    pass


def number(value: str, name: str, source: Path) -> float:
    try:
        parsed = float(value)
    except ValueError as exc:
        raise SummaryError(f"invalid {name}={value!r} in {source}") from exc
    if not math.isfinite(parsed) or parsed < 0:
        raise SummaryError(f"invalid non-negative {name}={value!r} in {source}")
    return parsed


def integer(value: str, name: str, source: Path) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise SummaryError(f"invalid integer {name}={value!r} in {source}") from exc
    if parsed < 0:
        raise SummaryError(f"invalid non-negative {name}={value!r} in {source}")
    return parsed


def one_value(path: Path, label: str) -> str:
    if not path.is_file():
        raise SummaryError(f"missing {label}: {path}")
    values = path.read_text(encoding="utf-8").split()
    if len(values) != 1:
        raise SummaryError(f"{label} must contain one value: {path}")
    return values[0]


def read_run(path: Path) -> dict[str, float | int | str]:
    stderr_path = path / "stderr.log"
    if not stderr_path.is_file():
        raise SummaryError(f"missing stderr log: {stderr_path}")
    raw: dict[str, str] = {}
    for line in stderr_path.read_text(encoding="utf-8").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            raw[key] = value

    row: dict[str, float | int | str] = {
        "run": path.name,
        "wall_seconds": number(
            one_value(path / "wall_seconds.txt", "wall receipt"),
            "wall_seconds",
            path / "wall_seconds.txt",
        ),
        "output_sha256": one_value(path / "output.sha256", "output digest"),
    }
    for name, full_name in METRICS.items():
        if full_name not in raw:
            raise SummaryError(f"missing required metric {name} ({full_name}) in {stderr_path}")
        row[name] = (
            integer(raw[full_name], name, stderr_path)
            if name in INTEGER_METRICS
            else number(raw[full_name], name, stderr_path)
        )
    row["exact_stage_seconds"] = float(row["column_wall_seconds"]) + float(
        row["compact_wall_seconds"]
    )
    row["exact_kernel_seconds"] = float(row["column_kernel_seconds"]) + float(
        row["compact_kernel_seconds"]
    )
    row["exact_h2d_seconds"] = float(row["column_h2d_seconds"]) + float(
        row["compact_h2d_seconds"]
    )
    row["exact_d2h_seconds"] = float(row["column_d2h_seconds"]) + float(
        row["compact_d2h_seconds"]
    )
    row["exact_launches"] = int(row["exact_batches"]) + int(row["compact_batches"])
    column_tasks = int(row["exact_tasks"])
    scoreinfo_tasks = int(row["scoreinfo_tasks"])
    column_cells = int(row["exact_cells"])
    scoreinfo_cells = int(row["scoreinfo_cells"])
    if column_tasks and scoreinfo_tasks and column_tasks != scoreinfo_tasks:
        raise SummaryError(
            f"column/scoreInfo task mismatch in {path}: {column_tasks} != {scoreinfo_tasks}"
        )
    if column_cells and scoreinfo_cells and column_cells != scoreinfo_cells:
        raise SummaryError(
            f"column/scoreInfo cell mismatch in {path}: {column_cells} != {scoreinfo_cells}"
        )
    row["exact_work_tasks"] = column_tasks or scoreinfo_tasks
    row["exact_work_cells"] = column_cells or scoreinfo_cells
    return row


def read_root(root: Path) -> dict[str, dict[str, float | int | str]]:
    run_dirs = sorted(path for path in root.glob("run_*") if path.is_dir())
    if not run_dirs:
        raise SummaryError(f"no run_* directories under {root}")
    return {path.name: read_run(path) for path in run_dirs}


def percentile_spread(values: list[float]) -> tuple[float, float, float, float]:
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0], ordered[0], ordered[0], ordered[0]
    quartiles = statistics.quantiles(ordered, n=4, method="inclusive")
    return ordered[0], quartiles[0], quartiles[2], ordered[-1]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Summarize paired baseline/candidate exact-column end-to-end runs."
    )
    parser.add_argument("--baseline-root", required=True, type=Path)
    parser.add_argument("--candidate-root", required=True, type=Path)
    parser.add_argument("--details", type=Path)
    parser.add_argument("--summary", type=Path)
    args = parser.parse_args()

    baseline = read_root(args.baseline_root)
    candidate = read_root(args.candidate_root)
    if baseline.keys() != candidate.keys():
        raise SummaryError(
            f"paired run names differ: baseline={sorted(baseline)} candidate={sorted(candidate)}"
        )

    paired: list[dict[str, float | int | str]] = []
    for name in baseline:
        base = baseline[name]
        cand = candidate[name]
        if int(base["exact_work_tasks"]) != int(cand["exact_work_tasks"]):
            raise SummaryError(
                f"exact task mismatch in {name}: {base['exact_work_tasks']} != {cand['exact_work_tasks']}"
            )
        if int(base["exact_work_cells"]) != int(cand["exact_work_cells"]):
            raise SummaryError(
                f"exact cell mismatch in {name}: {base['exact_work_cells']} != {cand['exact_work_cells']}"
            )
        if base["output_sha256"] != cand["output_sha256"]:
            raise SummaryError(f"output digest mismatch in {name}")
        paired.append(
            {
                "run": name,
                "baseline_wall_seconds": base["wall_seconds"],
                "candidate_wall_seconds": cand["wall_seconds"],
                "baseline_exact_stage_seconds": base["exact_stage_seconds"],
                "candidate_exact_stage_seconds": cand["exact_stage_seconds"],
                "baseline_exact_kernel_seconds": base["exact_kernel_seconds"],
                "candidate_exact_kernel_seconds": cand["exact_kernel_seconds"],
                "baseline_exact_h2d_seconds": base["exact_h2d_seconds"],
                "candidate_exact_h2d_seconds": cand["exact_h2d_seconds"],
                "baseline_exact_d2h_seconds": base["exact_d2h_seconds"],
                "candidate_exact_d2h_seconds": cand["exact_d2h_seconds"],
                "baseline_exact_launches": base["exact_launches"],
                "candidate_exact_launches": cand["exact_launches"],
                "exact_tasks": base["exact_work_tasks"],
                "exact_cells": base["exact_work_cells"],
                "output_sha256": base["output_sha256"],
            }
        )

    baseline_wall = [float(row["baseline_wall_seconds"]) for row in paired]
    candidate_wall = [float(row["candidate_wall_seconds"]) for row in paired]
    baseline_stage = [float(row["baseline_exact_stage_seconds"]) for row in paired]
    candidate_stage = [float(row["candidate_exact_stage_seconds"]) for row in paired]
    base_wall_median = statistics.median(baseline_wall)
    candidate_wall_median = statistics.median(candidate_wall)
    base_stage_median = statistics.median(baseline_stage)
    candidate_stage_median = statistics.median(candidate_stage)
    wall_reduction = (
        100.0 * (base_wall_median - candidate_wall_median) / base_wall_median
        if base_wall_median
        else 0.0
    )
    exact_reduction = (
        100.0 * (base_stage_median - candidate_stage_median) / base_stage_median
        if base_stage_median
        else 0.0
    )
    total_fallbacks = sum(
        int(candidate[name]["gasal2_fallbacks"])
        + int(candidate[name]["exact_fallback_batches"])
        for name in candidate
    )
    total_overflow = sum(int(candidate[name]["overflow_batches"]) for name in candidate)

    if wall_reduction >= 10.0:
        promotion = "strong_go"
    elif wall_reduction >= 0.0 and (exact_reduction >= 20.0 or wall_reduction >= 5.0):
        promotion = "go"
    else:
        promotion = "no_go"
    if total_fallbacks or total_overflow:
        promotion = "no_go"

    base_min, base_q1, base_q3, base_max = percentile_spread(baseline_wall)
    cand_min, cand_q1, cand_q3, cand_max = percentile_spread(candidate_wall)
    summary: dict[str, str | int] = {
        "runs": len(paired),
        "baseline_wall_median_seconds": f"{base_wall_median:.6f}",
        "candidate_wall_median_seconds": f"{candidate_wall_median:.6f}",
        "wall_reduction_percent": f"{wall_reduction:.2f}",
        "speedup": f"{base_wall_median / candidate_wall_median:.6f}",
        "baseline_wall_min_seconds": f"{base_min:.6f}",
        "baseline_wall_q1_seconds": f"{base_q1:.6f}",
        "baseline_wall_q3_seconds": f"{base_q3:.6f}",
        "baseline_wall_max_seconds": f"{base_max:.6f}",
        "candidate_wall_min_seconds": f"{cand_min:.6f}",
        "candidate_wall_q1_seconds": f"{cand_q1:.6f}",
        "candidate_wall_q3_seconds": f"{cand_q3:.6f}",
        "candidate_wall_max_seconds": f"{cand_max:.6f}",
        "baseline_exact_stage_median_seconds": f"{base_stage_median:.6f}",
        "candidate_exact_stage_median_seconds": f"{candidate_stage_median:.6f}",
        "exact_stage_reduction_percent": f"{exact_reduction:.2f}",
        "exact_tasks_equal_all": 1,
        "exact_cells_equal_all": 1,
        "full_output_sha_equal_all": 1,
        "fallbacks": total_fallbacks,
        "overflow_batches": total_overflow,
        "promotion_gate": promotion,
    }
    output = "".join(f"{key}={value}\n" for key, value in summary.items())
    print(output, end="")
    if args.summary:
        args.summary.parent.mkdir(parents=True, exist_ok=True)
        args.summary.write_text(output, encoding="utf-8")
    if args.details:
        args.details.parent.mkdir(parents=True, exist_ok=True)
        with args.details.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle, fieldnames=list(paired[0]), delimiter="\t", lineterminator="\n"
            )
            writer.writeheader()
            writer.writerows(paired)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, UnicodeError, SummaryError) as exc:
        raise SystemExit(str(exc)) from exc
