#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path


METRICS = {
    "column_pruned_enabled": (
        "benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_column_pruned_output_enabled"
    ),
    "exact_batches": "benchmark.fasim_top5_gasal2_phase_exact_column_batches",
    "exact_tasks": "benchmark.fasim_top5_gasal2_phase_exact_column_tasks",
    "exact_cells": "benchmark.fasim_top5_gasal2_phase_exact_column_cells",
    "compact_batches": "benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_batches",
    "column_wall_seconds": "benchmark.fasim_top5_gasal2_phase_exact_column_wall_seconds",
    "column_kernel_seconds": "benchmark.fasim_top5_gasal2_phase_exact_column_kernel_seconds",
    "column_h2d_seconds": "benchmark.fasim_top5_gasal2_phase_exact_column_h2d_seconds",
    "column_d2h_seconds": "benchmark.fasim_top5_gasal2_phase_exact_column_d2h_seconds",
    "compact_wall_seconds": "benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_wall_seconds",
    "compact_kernel_seconds": "benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_kernel_seconds",
    "compact_h2d_seconds": "benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_h2d_seconds",
    "compact_d2h_seconds": "benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_d2h_seconds",
    "fallbacks": "benchmark.fasim_gasal2_fallbacks",
}

INTEGER_METRICS = {
    "column_pruned_enabled",
    "exact_batches",
    "exact_tasks",
    "exact_cells",
    "compact_batches",
    "fallbacks",
}


class ProfileError(ValueError):
    pass


def parse_log(path: Path) -> dict[str, str]:
    raw: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8", errors="strict").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            raw[key] = value
    result: dict[str, str] = {}
    for short_name, full_name in METRICS.items():
        if full_name not in raw:
            raise ProfileError(
                f"missing required metric {short_name} ({full_name}) in {path}"
            )
        result[short_name] = raw[full_name]
    return result


def number(value: str, name: str, source: Path) -> float:
    try:
        parsed = float(value)
    except ValueError as exc:
        raise ProfileError(f"invalid {name}={value!r} in {source}") from exc
    if not math.isfinite(parsed) or parsed < 0:
        raise ProfileError(f"invalid non-negative {name}={value!r} in {source}")
    return parsed


def integer(value: str, name: str, source: Path) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ProfileError(f"invalid integer {name}={value!r} in {source}") from exc
    if parsed < 0:
        raise ProfileError(f"invalid non-negative {name}={value!r} in {source}")
    return parsed


def read_wall(path: Path) -> float:
    if not path.is_file():
        raise ProfileError(f"missing wall receipt: {path}")
    values = path.read_text(encoding="utf-8").split()
    if len(values) != 1:
        raise ProfileError(f"wall receipt must contain one value: {path}")
    return number(values[0], "wall_seconds", path)


def grid_shift(log: Path) -> str:
    for parent in log.parents:
        if parent.name.startswith("shift_"):
            return parent.name.removeprefix("shift_")
    return "unavailable"


def discover_logs(root: Path) -> list[Path]:
    return sorted(
        path
        for path in root.rglob("stderr.log")
        if path.parent.name.startswith("run_")
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Aggregate exact-column cost across segmented long-query runs."
    )
    parser.add_argument("--run-root", required=True, type=Path)
    parser.add_argument("--details", type=Path)
    parser.add_argument("--summary", type=Path)
    args = parser.parse_args()

    logs = discover_logs(args.run_root)
    if not logs:
        parser.error(f"no run_*/stderr.log files under {args.run_root}")

    rows: list[dict[str, float | int | str]] = []
    for log in logs:
        parsed = parse_log(log)
        row: dict[str, float | int | str] = {
            "grid_shift": grid_shift(log),
            "run": log.parent.name,
            "wall_seconds": read_wall(log.parent / "wall_seconds.txt"),
        }
        for name, value in parsed.items():
            row[name] = integer(value, name, log) if name in INTEGER_METRICS else number(
                value, name, log
            )
        rows.append(row)

    def total(name: str) -> float:
        return sum(float(row[name]) for row in rows)

    def total_int(name: str) -> int:
        return sum(int(row[name]) for row in rows)

    end_to_end = total("wall_seconds")
    exact_stage = total("column_wall_seconds") + total("compact_wall_seconds")
    exact_kernel = total("column_kernel_seconds") + total("compact_kernel_seconds")
    exact_h2d = total("column_h2d_seconds") + total("compact_h2d_seconds")
    exact_d2h = total("column_d2h_seconds") + total("compact_d2h_seconds")
    exact_tasks = total_int("exact_tasks")
    exact_cells = total_int("exact_cells")
    exact_batches = total_int("exact_batches")
    compact_batches = total_int("compact_batches")
    exact_stage_percent = 100.0 * exact_stage / end_to_end if end_to_end else 0.0
    kernel_percent = 100.0 * exact_kernel / exact_stage if exact_stage else 0.0
    variants = {int(row["column_pruned_enabled"]) for row in rows}
    if variants == {0}:
        variant = "column_maxima_cpu_scoreinfo"
    elif variants == {1}:
        variant = "column_scoreinfo_pruned_fused"
    else:
        variant = "mixed"
    shifts = sorted(
        {str(row["grid_shift"]) for row in rows},
        key=lambda value: (value == "unavailable", int(value) if value.lstrip("-").isdigit() else value),
    )

    summary: dict[str, str | int] = {
        "runs": len(rows),
        "grid_shifts": ",".join(shifts),
        "end_to_end_seconds": f"{end_to_end:.6f}",
        "exact_stage_seconds": f"{exact_stage:.6f}",
        "exact_stage_percent": f"{exact_stage_percent:.2f}",
        "exact_kernel_seconds": f"{exact_kernel:.6f}",
        "exact_kernel_percent_of_stage": f"{kernel_percent:.2f}",
        "exact_h2d_seconds": f"{exact_h2d:.6f}",
        "exact_d2h_seconds": f"{exact_d2h:.6f}",
        "exact_batches": exact_batches,
        "exact_compact_batches": compact_batches,
        "exact_launches": exact_batches + compact_batches,
        "exact_tasks_before": exact_tasks,
        "exact_tasks_after": exact_tasks,
        "exact_tasks_dropped_identical": 0,
        "exact_cells_before": exact_cells,
        "exact_cells_after": exact_cells,
        "fallbacks": total_int("fallbacks"),
        "kernel_variant": variant,
        "entry_gate": "material" if exact_stage_percent >= 10.0 else "no_go_low_ceiling",
    }

    output = "".join(f"{key}={value}\n" for key, value in summary.items())
    print(output, end="")
    if args.summary:
        args.summary.parent.mkdir(parents=True, exist_ok=True)
        args.summary.write_text(output, encoding="utf-8")
    if args.details:
        args.details.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = ["grid_shift", "run", "wall_seconds", *METRICS]
        with args.details.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle, fieldnames=fieldnames, delimiter="\t", lineterminator="\n"
            )
            writer.writeheader()
            writer.writerows(rows)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, UnicodeError, ProfileError) as exc:
        raise SystemExit(str(exc)) from exc
