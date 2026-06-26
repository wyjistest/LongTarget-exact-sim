#!/usr/bin/env python3
"""Summarize the remaining optimization opportunity in GASAL2 full-plain runs."""

from __future__ import annotations

import argparse
import math
from pathlib import Path


def _read_kv(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
    return values


def _metric_from_stderr(path: Path, key: str, default: str = "0") -> str:
    if not path.exists():
        return default
    prefix = key + "="
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith(prefix):
            return line[len(prefix) :].strip()
    return default


def _float(metrics: dict[str, str], key: str, default: float = 0.0) -> float:
    raw = metrics.get(key)
    if raw is None or raw == "":
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _int(metrics: dict[str, str], key: str, default: int = 0) -> int:
    return int(_float(metrics, key, float(default)))


def _ratio(numerator: float, denominator: float) -> float:
    if denominator == 0.0:
        return float("nan")
    return numerator / denominator


def _fmt(value: float) -> str:
    if math.isfinite(value):
        return f"{value:.6f}"
    return "nan"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Read a GASAL2 CPU-vs-GASAL2 full-plain result and emit the "
            "remaining optimization bottleneck decision."
        )
    )
    parser.add_argument("--work", required=True, type=Path)
    parser.add_argument("--summary", required=True, type=Path)
    parser.add_argument("--min-speedup", type=float, default=20.0)
    parser.add_argument("--min-traceback-requests", type=int, default=1_000_000)
    args = parser.parse_args()

    metrics = _read_kv(args.summary)
    top5_metrics = _read_kv(args.work / "top5_compare.txt")
    cpu_case = _read_kv(args.work / "cpu" / "case_metrics.txt")
    gasal2_case = _read_kv(args.work / "gasal2" / "case_metrics.txt")
    stderr = args.work / "gasal2" / "stderr.log"

    for key, value in cpu_case.items():
        metrics.setdefault(f"cpu_{key}", value)
    for key, value in gasal2_case.items():
        metrics.setdefault(f"gasal2_{key}", value)
    for key in (
        "top5_score_equal",
        "top5_stability_equal",
        "top5_nt_score_equal",
        "missing_rows",
        "extra_rows",
    ):
        if key in top5_metrics:
            metrics.setdefault(key, top5_metrics[key])
    stderr_defaults = {
        "gasal2_active": "benchmark.fasim_top5_gasal2_gpu_scoreinfo_active",
        "gasal2_requests": "benchmark.fasim_gasal2_requests",
        "gasal2_traceback_requests": "benchmark.fasim_gasal2_traceback_requests",
        "gasal2_fallbacks": "benchmark.fasim_gasal2_fallbacks",
        "gasal2_length_guard_fallbacks": "benchmark.fasim_gasal2_length_guard_fallbacks",
        "gasal2_total_seconds": "benchmark.fasim_gasal2_total_seconds",
        "gasal2_extend_wall_seconds": (
            "benchmark.fasim_top5_gasal2_phase_gasal2_extend_wall_seconds"
        ),
        "gasal2_convert_wall_seconds": (
            "benchmark.fasim_top5_gasal2_phase_gasal2_convert_wall_seconds"
        ),
        "exact_column_wall_seconds": (
            "benchmark.fasim_top5_gasal2_phase_exact_column_wall_seconds"
        ),
        "output_write_seconds": (
            "benchmark.fasim_top5_gasal2_phase_output_write_seconds"
        ),
        "flush_total_seconds": "benchmark.fasim_top5_gasal2_phase_flush_total_seconds",
    }
    for metric_key, stderr_key in stderr_defaults.items():
        if metric_key not in metrics or metrics[metric_key] in {"", "0"}:
            metrics[metric_key] = _metric_from_stderr(stderr, stderr_key, metrics.get(metric_key, "0"))

    cpu_wall = _float(metrics, "cpu_wall_seconds")
    if cpu_wall == 0.0:
        cpu_wall = _float(metrics, "cpu_wall_seconds", _float(cpu_case, "wall_seconds"))
    gasal2_wall = _float(metrics, "gasal2_wall_seconds")
    if gasal2_wall == 0.0:
        gasal2_wall = _float(metrics, "gasal2_wall_seconds", _float(gasal2_case, "wall_seconds"))
    speedup = _float(metrics, "run_wall_speedup", _ratio(cpu_wall, gasal2_wall))
    gasal2_requests = _int(metrics, "gasal2_requests")
    traceback_requests = _int(metrics, "gasal2_traceback_requests")
    gasal2_lines = _int(metrics, "gasal2_lines")
    gasal2_total = _float(metrics, "gasal2_total_seconds")
    extend_wall = _float(metrics, "gasal2_extend_wall_seconds")
    convert_wall = _float(metrics, "gasal2_convert_wall_seconds")
    exact_column_wall = _float(metrics, "exact_column_wall_seconds")
    output_write = _float(metrics, "output_write_seconds")
    flush_total = _float(metrics, "flush_total_seconds")

    required_top5_clean = all(
        metrics.get(key) == "true"
        for key in ("top5_score_equal", "top5_stability_equal", "top5_nt_score_equal")
    )
    active_clean = (
        metrics.get("gasal2_active") == "1"
        and _int(metrics, "gasal2_fallbacks") == 0
        and _int(metrics, "gasal2_length_guard_fallbacks") == 0
    )
    strong_speed_signal = speedup >= args.min_speedup
    traceback_material = traceback_requests >= args.min_traceback_requests

    if required_top5_clean and active_clean and strong_speed_signal and traceback_material:
        decision = "traceback_reduction_is_primary_remaining_optimization"
        next_action = "prototype_or_characterize_top5_limited_traceback"
    elif required_top5_clean and active_clean and strong_speed_signal:
        decision = "batch_stream_or_cpu_overhead_tuning_only"
        next_action = "sweep_batch_stream_settings"
    else:
        decision = "do_not_optimize_until_contract_or_speed_gate_is_clean"
        next_action = "fix_contract_or_measurement_first"

    non_output_wall = max(gasal2_wall - output_write, 0.0)
    non_gasal2_wall = max(gasal2_wall - gasal2_total, 0.0)

    output = {
        "decision": decision,
        "next_action": next_action,
        "cpu_wall_seconds": _fmt(cpu_wall),
        "gasal2_wall_seconds": _fmt(gasal2_wall),
        "run_wall_speedup": _fmt(speedup),
        "top5_score_equal": metrics.get("top5_score_equal", "false"),
        "top5_stability_equal": metrics.get("top5_stability_equal", "false"),
        "top5_nt_score_equal": metrics.get("top5_nt_score_equal", "false"),
        "gasal2_active": metrics.get("gasal2_active", "0"),
        "gasal2_requests": str(gasal2_requests),
        "gasal2_traceback_requests": str(traceback_requests),
        "gasal2_fallbacks": str(_int(metrics, "gasal2_fallbacks")),
        "gasal2_length_guard_fallbacks": str(_int(metrics, "gasal2_length_guard_fallbacks")),
        "traceback_requests_per_gasal2_request": _fmt(
            _ratio(float(traceback_requests), float(gasal2_requests))
        ),
        "traceback_requests_per_output_row": _fmt(
            _ratio(float(traceback_requests), float(gasal2_lines))
        ),
        "gasal2_total_seconds": _fmt(gasal2_total),
        "gasal2_extend_wall_seconds": _fmt(extend_wall),
        "gasal2_convert_wall_seconds": _fmt(convert_wall),
        "exact_column_wall_seconds": _fmt(exact_column_wall),
        "output_write_seconds": _fmt(output_write),
        "flush_total_seconds": _fmt(flush_total),
        "gasal2_kernel_fraction_of_wall": _fmt(_ratio(gasal2_total, gasal2_wall)),
        "convert_fraction_of_wall": _fmt(_ratio(convert_wall, gasal2_wall)),
        "output_write_fraction_of_wall": _fmt(_ratio(output_write, gasal2_wall)),
        "non_gasal2_wall_seconds": _fmt(non_gasal2_wall),
        "non_output_wall_seconds": _fmt(non_output_wall),
        "optimization_boundary": (
            "output_write_is_not_material"
            if output_write > 0.0 and _ratio(output_write, gasal2_wall) < 0.05
            else "output_or_convert_still_material"
        ),
        "full_rows_equal": str(
            _int(metrics, "cpu_only_rows", _int(metrics, "missing_rows")) == 0
            and _int(metrics, "gasal2_only_rows", _int(metrics, "extra_rows")) == 0
        ).lower(),
    }
    for key, value in output.items():
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
