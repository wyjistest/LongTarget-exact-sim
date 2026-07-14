#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path


METRICS = {
    "score_fill_seconds": "benchmark.fasim_gasal2_score_fill_seconds",
    "score_submit_seconds": "benchmark.fasim_gasal2_score_submit_seconds",
    "score_wait_seconds": "benchmark.fasim_gasal2_score_wait_seconds",
    "score_poll_wait_seconds": "benchmark.fasim_gasal2_score_poll_wait_seconds",
    "score_result_copy_seconds": "benchmark.fasim_gasal2_score_result_copy_seconds",
    "traceback_fill_seconds": "benchmark.fasim_gasal2_traceback_fill_seconds",
    "traceback_submit_seconds": "benchmark.fasim_gasal2_traceback_submit_seconds",
    "traceback_wait_seconds": "benchmark.fasim_gasal2_traceback_wait_seconds",
    "traceback_poll_wait_seconds": "benchmark.fasim_gasal2_traceback_poll_wait_seconds",
    "traceback_result_copy_seconds": "benchmark.fasim_gasal2_traceback_result_copy_seconds",
    "traceback_cigar_vector_seconds": "benchmark.fasim_gasal2_traceback_cigar_vector_seconds",
    "traceback_cigar_string_seconds": "benchmark.fasim_gasal2_traceback_cigar_string_seconds",
    "traceback_convert_seconds": "benchmark.fasim_gasal2_cpu_traceback_convert_seconds",
    "convert_filter_seconds": "benchmark.fasim_top5_gasal2_phase_gasal2_convert_filter_seconds",
    "convert_sort_seconds": "benchmark.fasim_top5_gasal2_phase_gasal2_convert_sort_seconds",
    "traceback_requests": "benchmark.fasim_gasal2_traceback_requests",
    "traceback_batches": "benchmark.fasim_gasal2_traceback_batches",
    "fallbacks": "benchmark.fasim_gasal2_fallbacks",
    "length_guard_fallbacks": "benchmark.fasim_gasal2_length_guard_fallbacks",
}

INTEGER_METRICS = {
    "traceback_requests",
    "traceback_batches",
    "fallbacks",
    "length_guard_fallbacks",
}


class AnalysisError(ValueError):
    pass


def parse_log(path: Path) -> dict[str, float | int]:
    raw: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8", errors="strict").splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        raw[key] = value

    parsed: dict[str, float | int] = {}
    for short_name, full_name in METRICS.items():
        if full_name not in raw:
            raise AnalysisError(
                f"missing required metric {short_name} ({full_name}) in {path}"
            )
        value = raw[full_name]
        try:
            number = int(value) if short_name in INTEGER_METRICS else float(value)
        except ValueError as exc:
            raise AnalysisError(f"invalid {short_name}={value!r} in {path}") from exc
        if number < 0 or (isinstance(number, float) and not math.isfinite(number)):
            raise AnalysisError(f"invalid non-negative {short_name}={value!r} in {path}")
        parsed[short_name] = number
    validate_wait_closure(parsed, path)
    return parsed


def validate_wait_closure(metrics: dict[str, float | int], path: Path) -> None:
    for prefix in ("score", "traceback"):
        wait = float(metrics[f"{prefix}_wait_seconds"])
        components = float(metrics[f"{prefix}_poll_wait_seconds"]) + float(
            metrics[f"{prefix}_result_copy_seconds"]
        )
        tolerance = max(1e-5, wait * 1e-5)
        if abs(wait - components) > tolerance:
            raise AnalysisError(
                f"{prefix} wait timing does not close in {path}: "
                f"wait={wait:.9f}, poll+copy={components:.9f}"
            )


def read_wall(path: Path) -> float:
    if not path.is_file():
        raise AnalysisError(f"missing wall receipt: {path}")
    values = path.read_text(encoding="utf-8", errors="strict").split()
    if len(values) != 1:
        raise AnalysisError(f"wall receipt must contain one value: {path}")
    try:
        wall = float(values[0])
    except ValueError as exc:
        raise AnalysisError(f"invalid wall receipt: {path}") from exc
    if not math.isfinite(wall) or wall < 0:
        raise AnalysisError(f"invalid non-negative wall receipt: {path}")
    return wall


def discover_logs(root: Path) -> list[Path]:
    return sorted(
        path
        for path in root.rglob("stderr.log")
        if path.parent.name.startswith("run_")
    )


def grid_shift(log: Path) -> str:
    for parent in log.parents:
        if parent.name.startswith("shift_"):
            return parent.name.removeprefix("shift_")
    return "unavailable"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Aggregate traceback-stage timing across segmented GASAL2 runs."
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
        row: dict[str, float | int | str] = {
            "grid_shift": grid_shift(log),
            "run": log.parent.name,
            "wall_seconds": read_wall(log.parent / "wall_seconds.txt"),
        }
        row.update(parse_log(log))
        rows.append(row)

    def total(name: str) -> float:
        return sum(float(row[name]) for row in rows)

    def total_int(name: str) -> int:
        return sum(int(row[name]) for row in rows)

    score_prepass = (
        total("score_fill_seconds")
        + total("score_submit_seconds")
        + total("score_wait_seconds")
    )
    traceback_host_stage = (
        total("traceback_fill_seconds")
        + total("traceback_submit_seconds")
        + total("traceback_wait_seconds")
        + total("traceback_convert_seconds")
    )
    cigar_materialize = total("traceback_cigar_vector_seconds") + total(
        "traceback_cigar_string_seconds"
    )
    filter_sort = total("convert_filter_seconds") + total("convert_sort_seconds")
    end_to_end = total("wall_seconds")
    shifts = sorted(
        {str(row["grid_shift"]) for row in rows},
        key=lambda value: (
            value == "unavailable",
            int(value) if value.lstrip("-").isdigit() else value,
        ),
    )

    summary: dict[str, str | int] = {
        "runs": len(rows),
        "grid_shifts": ",".join(shifts),
        "end_to_end_seconds": f"{end_to_end:.6f}",
        "traceback_requests": total_int("traceback_requests"),
        "traceback_batches": total_int("traceback_batches"),
        "traceback_score_prepass_seconds": f"{score_prepass:.6f}",
        "traceback_score_prepass_scope": "score_fill_submit_wait",
        "traceback_pack_seconds": f"{total('traceback_fill_seconds'):.6f}",
        "traceback_submit_seconds": f"{total('traceback_submit_seconds'):.6f}",
        "traceback_host_wait_seconds": f"{total('traceback_wait_seconds'):.6f}",
        "traceback_host_poll_wait_seconds": f"{total('traceback_poll_wait_seconds'):.6f}",
        "traceback_result_copy_seconds": f"{total('traceback_result_copy_seconds'):.6f}",
        "traceback_cigar_materialize_seconds": f"{cigar_materialize:.6f}",
        "traceback_convert_seconds": f"{total('traceback_convert_seconds'):.6f}",
        "traceback_filter_dedup_cluster_seconds": f"{filter_sort:.6f}",
        "filter_dedup_cluster_scope": "per_run_filter_sort_only",
        "traceback_host_observed_stage_seconds": f"{traceback_host_stage:.6f}",
        "traceback_host_observed_percent": (
            f"{100.0 * traceback_host_stage / end_to_end:.2f}" if end_to_end else "0.00"
        ),
        "traceback_h2d_seconds": "unavailable",
        "traceback_kernel_seconds": "unavailable",
        "traceback_d2h_seconds": "unavailable",
        "device_timing_supported": 0,
        "timing_closure": "clean",
        "fallbacks": total_int("fallbacks"),
        "length_guard_fallbacks": total_int("length_guard_fallbacks"),
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
    except (OSError, UnicodeError, AnalysisError) as exc:
        raise SystemExit(str(exc)) from exc
