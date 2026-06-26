#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from statistics import median
from typing import Iterable


SUMMARY_FLUSH_FIELDS = [
    "flush_id",
    "shard_name",
    "flush_wall_seconds",
    "requests",
    "traceback_requests",
    "rows",
    "pack_seconds",
    "gpu_path_seconds",
    "exact_column_seconds",
    "traceback_seconds",
    "d2h_seconds",
    "convert_seconds",
    "archive_write_seconds",
    "sort_dedup_seconds",
    "gasal2_score_poll_wait_seconds",
    "gasal2_score_result_copy_seconds",
    "gasal2_traceback_poll_wait_seconds",
    "gasal2_traceback_result_copy_seconds",
    "gasal2_traceback_cigar_vector_seconds",
    "gasal2_traceback_cigar_string_seconds",
    "gasal2_synchronous_wait_seconds",
    "synchronous_flush_path",
    "queue_supported",
    "gpu_producer_blocked_seconds",
    "cpu_consumer_idle_seconds",
    "waiting_for_free_buffer_seconds",
    "archive_queue_depth_max",
    "decision_hint",
]


def _float(value: object, default: float = 0.0) -> float:
    if value is None:
        return default
    text = str(value).strip()
    if not text or text.upper() == "NA":
        return default
    try:
        return float(text)
    except ValueError:
        return default


def _int(value: object, default: int = 0) -> int:
    if value is None:
        return default
    text = str(value).strip()
    if not text or text.upper() == "NA":
        return default
    try:
        return int(float(text))
    except ValueError:
        return default


def _bool(value: object) -> bool:
    text = str(value).strip().lower()
    return text in {"1", "true", "yes", "y", "on"}


def _seconds_between(row: dict[str, str], start_key: str, end_key: str) -> float:
    start = _float(row.get(start_key), math.nan)
    end = _float(row.get(end_key), math.nan)
    if not math.isfinite(start) or not math.isfinite(end) or end < start:
        return 0.0
    return (end - start) / 1_000_000_000.0


def _span(row: dict[str, str], pairs: Iterable[tuple[str, str]]) -> float:
    starts: list[float] = []
    ends: list[float] = []
    for start_key, end_key in pairs:
        start = _float(row.get(start_key), math.nan)
        end = _float(row.get(end_key), math.nan)
        if math.isfinite(start) and math.isfinite(end) and end >= start and end > 0:
            starts.append(start)
            ends.append(end)
    if not starts or not ends:
        return 0.0
    return (max(ends) - min(starts)) / 1_000_000_000.0


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = int(math.ceil((percentile / 100.0) * len(ordered))) - 1
    index = max(0, min(index, len(ordered) - 1))
    return ordered[index]


def _pearson(xs: list[float], ys: list[float]) -> float:
    if len(xs) != len(ys) or len(xs) < 2:
        return 0.0
    x_mean = sum(xs) / len(xs)
    y_mean = sum(ys) / len(ys)
    x_dev = [x - x_mean for x in xs]
    y_dev = [y - y_mean for y in ys]
    num = sum(a * b for a, b in zip(x_dev, y_dev))
    den_x = math.sqrt(sum(a * a for a in x_dev))
    den_y = math.sqrt(sum(b * b for b in y_dev))
    if den_x == 0.0 or den_y == 0.0:
        return 0.0
    return num / (den_x * den_y)


def _finish_time_for_workers(durations: list[float], workers: int) -> float:
    if workers <= 1:
        return sum(durations)
    loads = [0.0] * workers
    for duration in durations:
        index = min(range(workers), key=lambda i: loads[i])
        loads[index] += max(0.0, duration)
    return max(loads) if loads else 0.0


def _pipeline_makespan(flushes: list[dict[str, float | str]], buffer_count: int) -> float:
    # Approximate an in-order bounded-buffer pipeline with three stages:
    # pack, GPU path, and CPU finalization. This is a simulation estimate, not
    # measured runtime.
    if not flushes:
        return 0.0
    pack_available = 0.0
    gpu_available = 0.0
    cpu_available = 0.0
    queue_limit = max(1, buffer_count - 1)
    gpu_finishes: list[float] = []
    cpu_finish = 0.0
    for row in flushes:
        if len(gpu_finishes) > queue_limit:
            pack_available = max(pack_available, gpu_finishes[-queue_limit - 1])
        pack_finish = pack_available + _float(row["pack_seconds"])
        pack_available = pack_finish
        gpu_start = max(pack_finish, gpu_available)
        gpu_finish = gpu_start + _float(row["gpu_path_seconds"])
        gpu_available = gpu_finish
        gpu_finishes.append(gpu_finish)
        cpu_stage = (
            _float(row["convert_seconds"]) +
            _float(row["archive_write_seconds"]) +
            _float(row["sort_dedup_seconds"])
        )
        cpu_start = max(gpu_finish, cpu_available)
        cpu_finish = cpu_start + cpu_stage
        cpu_available = cpu_finish
    return cpu_finish


def _decision(rows: list[dict[str, float | str]]) -> str:
    if not rows:
        return "telemetry_incomplete"
    availability_keys = [
        "gpu_producer_blocked_available",
        "cpu_consumer_idle_available",
        "waiting_for_free_buffer_available",
        "archive_queue_depth_available",
    ]
    unavailable = 0
    total_availability = 0
    for row in rows:
        source = row.get("_source")
        if not isinstance(source, dict):
            continue
        for key in availability_keys:
            total_availability += 1
            if not _bool(source.get(key)):
                unavailable += 1
    if total_availability == 0 or unavailable > 0:
        return "telemetry_incomplete"
    total_gpu = sum(_float(row["gpu_path_seconds"]) for row in rows)
    total_convert = sum(_float(row["convert_seconds"]) for row in rows)
    total_archive = sum(_float(row["archive_write_seconds"]) for row in rows)
    total_pack = sum(_float(row["pack_seconds"]) for row in rows)
    total_wall = sum(_float(row["flush_wall_seconds"]) for row in rows)
    if total_wall <= 0.0:
        return "telemetry_incomplete"
    if total_archive > total_gpu and total_archive > total_convert:
        return "archive_backpressure_candidate"
    if total_pack > total_gpu and total_pack > total_convert:
        return "pack_starvation_candidate"
    if total_gpu >= total_convert + total_archive:
        return "gpu_critical_path"
    simulated = _pipeline_makespan(rows, 3)
    current = sum(_float(row["flush_wall_seconds"]) for row in rows)
    speedup = current / simulated if simulated > 0.0 else 1.0
    if speedup < 1.05:
        return "pipeline_refactor_no_go"
    return "pipeline_overlap_candidate"


def _parse_rows(path: Path) -> list[dict[str, float | str | dict[str, str]]]:
    rows: list[dict[str, float | str | dict[str, str]]] = []
    with path.open("rt", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for source in reader:
            flush_wall = _seconds_between(source, "pack_start_ns", "flush_complete_ns")
            pack = _seconds_between(source, "pack_start_ns", "pack_end_ns")
            exact = _seconds_between(source, "exact_column_start_ns", "exact_column_end_ns")
            traceback = _span(
                source,
                [
                    ("traceback_pack_start_ns", "traceback_pack_end_ns"),
                    ("traceback_submit_start_ns", "traceback_submit_end_ns"),
                    ("traceback_wait_start_ns", "traceback_wait_end_ns"),
                ],
            )
            d2h = _seconds_between(source, "d2h_start_ns", "d2h_end_ns")
            gpu_path = _span(
                source,
                [
                    ("h2d_start_ns", "h2d_end_ns"),
                    ("gasal2_score_submit_start_ns", "gasal2_score_submit_end_ns"),
                    ("gasal2_score_wait_start_ns", "gasal2_score_wait_end_ns"),
                    ("exact_column_start_ns", "exact_column_end_ns"),
                    ("traceback_pack_start_ns", "traceback_pack_end_ns"),
                    ("traceback_submit_start_ns", "traceback_submit_end_ns"),
                    ("traceback_wait_start_ns", "traceback_wait_end_ns"),
                    ("d2h_start_ns", "d2h_end_ns"),
                ],
            )
            row: dict[str, float | str | dict[str, str]] = {
                "flush_id": str(source.get("flush_id", "")),
                "shard_name": str(source.get("shard_name", "")),
                "worker_id": str(source.get("worker_id", "")),
                "gpu_id": str(source.get("gpu_id", "")),
                "flush_sequence": _int(source.get("flush_sequence")),
                "flush_wall_seconds": flush_wall,
                "requests": _int(source.get("gasal2_requests")),
                "traceback_requests": _int(source.get("traceback_requests")),
                "rows": _int(source.get("final_rows_after_sort_dedup") or source.get("emitted_rows")),
                "pack_seconds": pack,
                "gpu_path_seconds": gpu_path,
                "exact_column_seconds": exact,
                "traceback_seconds": traceback,
                "d2h_seconds": d2h,
                "convert_seconds": _seconds_between(source, "convert_start_ns", "convert_end_ns"),
                "archive_write_seconds": _seconds_between(source, "archive_write_start_ns", "archive_write_end_ns"),
                "sort_dedup_seconds": _seconds_between(source, "sort_dedup_start_ns", "sort_dedup_end_ns"),
                "gasal2_score_poll_wait_seconds": _float(source.get("gasal2_score_poll_wait_seconds")),
                "gasal2_score_result_copy_seconds": _float(source.get("gasal2_score_result_copy_seconds")),
                "gasal2_traceback_poll_wait_seconds": _float(source.get("gasal2_traceback_poll_wait_seconds")),
                "gasal2_traceback_result_copy_seconds": _float(source.get("gasal2_traceback_result_copy_seconds")),
                "gasal2_traceback_cigar_vector_seconds": _float(source.get("gasal2_traceback_cigar_vector_seconds")),
                "gasal2_traceback_cigar_string_seconds": _float(source.get("gasal2_traceback_cigar_string_seconds")),
                "gasal2_synchronous_wait_seconds": _float(source.get("gasal2_synchronous_wait_seconds")),
                "synchronous_flush_path": 1 if _bool(source.get("synchronous_flush_path")) else 0,
                "queue_supported": 1 if _bool(source.get("queue_supported")) else 0,
                "gpu_producer_blocked_seconds": _float(source.get("gpu_producer_blocked_seconds")),
                "cpu_consumer_idle_seconds": _float(source.get("cpu_consumer_idle_seconds")),
                "waiting_for_free_buffer_seconds": _float(source.get("waiting_for_free_buffer_seconds")),
                "archive_queue_depth_max": max(
                    _float(source.get("archive_queue_depth_at_start")),
                    _float(source.get("archive_queue_depth_at_end")),
                ),
                "archive_bytes": _int(source.get("archive_bytes")),
                "archive_blocks": _int(source.get("archive_blocks")),
                "decision_hint": str(source.get("decision_hint", "")),
                "_source": source,
            }
            rows.append(row)
    return rows


def _format_summary_value(value: float | int | str) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, int):
        return str(value)
    return f"{value:.6f}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Summarize GASAL2-LongTarget flush-level pipeline telemetry."
    )
    parser.add_argument("--flush-tsv", required=True, type=Path)
    parser.add_argument("--chrome-trace", type=Path)
    parser.add_argument("--output-summary", required=True, type=Path)
    parser.add_argument("--output-tsv", required=True, type=Path)
    args = parser.parse_args()

    rows = _parse_rows(args.flush_tsv)
    if not rows:
        raise SystemExit("no flush rows found")

    walls = [_float(row["flush_wall_seconds"]) for row in rows]
    total_wall = sum(walls)
    med_wall = median(walls)
    max_wall = max(walls)
    sorted_walls = sorted(walls, reverse=True)
    top_n = max(1, int(math.ceil(len(sorted_walls) * 0.01)))
    top_1pct_fraction = sum(sorted_walls[:top_n]) / total_wall if total_wall > 0.0 else 0.0

    current_makespan = total_wall
    two_buffer = _pipeline_makespan(rows, 2)
    three_buffer = _pipeline_makespan(rows, 3)
    convert_durations = [_float(row["convert_seconds"]) for row in rows]
    convert_1 = _finish_time_for_workers(convert_durations, 1)
    convert_2 = _finish_time_for_workers(convert_durations, 2)
    convert_4 = _finish_time_for_workers(convert_durations, 4)

    trace_events = 0
    if args.chrome_trace is not None and args.chrome_trace.exists():
        try:
            trace = json.loads(args.chrome_trace.read_text())
            trace_events = len(trace.get("traceEvents", []))
        except json.JSONDecodeError:
            trace_events = 0

    summary: list[tuple[str, float | int | str]] = [
        ("flushes", len(rows)),
        ("total_flush_wall_seconds", total_wall),
        ("p50_flush_wall_seconds", _percentile(walls, 50)),
        ("p90_flush_wall_seconds", _percentile(walls, 90)),
        ("p99_flush_wall_seconds", _percentile(walls, 99)),
        ("max_flush_wall_seconds", max_wall),
        ("max_to_median_flush_wall_ratio", max_wall / med_wall if med_wall > 0.0 else 0.0),
        ("top_1pct_flush_wall_fraction", top_1pct_fraction),
        ("total_requests", sum(_int(row["requests"]) for row in rows)),
        ("total_traceback_requests", sum(_int(row["traceback_requests"]) for row in rows)),
        ("total_rows", sum(_int(row["rows"]) for row in rows)),
        ("total_pack_seconds", sum(_float(row["pack_seconds"]) for row in rows)),
        ("total_gpu_path_seconds", sum(_float(row["gpu_path_seconds"]) for row in rows)),
        ("total_exact_column_seconds", sum(_float(row["exact_column_seconds"]) for row in rows)),
        ("total_traceback_seconds", sum(_float(row["traceback_seconds"]) for row in rows)),
        ("total_d2h_seconds", sum(_float(row["d2h_seconds"]) for row in rows)),
        ("total_convert_seconds", sum(_float(row["convert_seconds"]) for row in rows)),
        ("total_archive_write_seconds", sum(_float(row["archive_write_seconds"]) for row in rows)),
        ("total_sort_dedup_seconds", sum(_float(row["sort_dedup_seconds"]) for row in rows)),
        ("total_gasal2_score_poll_wait_seconds", sum(_float(row["gasal2_score_poll_wait_seconds"]) for row in rows)),
        ("total_gasal2_score_result_copy_seconds", sum(_float(row["gasal2_score_result_copy_seconds"]) for row in rows)),
        ("total_gasal2_traceback_poll_wait_seconds", sum(_float(row["gasal2_traceback_poll_wait_seconds"]) for row in rows)),
        ("total_gasal2_traceback_result_copy_seconds", sum(_float(row["gasal2_traceback_result_copy_seconds"]) for row in rows)),
        ("total_gasal2_traceback_cigar_vector_seconds", sum(_float(row["gasal2_traceback_cigar_vector_seconds"]) for row in rows)),
        ("total_gasal2_traceback_cigar_string_seconds", sum(_float(row["gasal2_traceback_cigar_string_seconds"]) for row in rows)),
        ("total_gasal2_synchronous_wait_seconds", sum(_float(row["gasal2_synchronous_wait_seconds"]) for row in rows)),
        ("total_gasal2_result_copy_seconds", sum(_float(row["gasal2_score_result_copy_seconds"]) + _float(row["gasal2_traceback_result_copy_seconds"]) for row in rows)),
        ("queue_supported", 1 if any(_int(row["queue_supported"]) != 0 for row in rows) else 0),
        ("synchronous_flush_path", 1 if any(_int(row["synchronous_flush_path"]) != 0 for row in rows) else 0),
        ("total_gpu_producer_blocked_seconds", sum(_float(row["gpu_producer_blocked_seconds"]) for row in rows)),
        ("total_cpu_consumer_idle_seconds", sum(_float(row["cpu_consumer_idle_seconds"]) for row in rows)),
        ("total_waiting_for_free_buffer_seconds", sum(_float(row["waiting_for_free_buffer_seconds"]) for row in rows)),
        ("wall_corr_requests", _pearson(walls, [_float(row["requests"]) for row in rows])),
        ("wall_corr_tracebacks", _pearson(walls, [_float(row["traceback_requests"]) for row in rows])),
        ("wall_corr_rows", _pearson(walls, [_float(row["rows"]) for row in rows])),
        ("wall_corr_convert_seconds", _pearson(walls, [_float(row["convert_seconds"]) for row in rows])),
        ("wall_corr_archive_write_seconds", _pearson(walls, [_float(row["archive_write_seconds"]) for row in rows])),
        ("current_makespan_seconds", current_makespan),
        ("ideal_two_buffer_makespan_seconds", two_buffer),
        ("ideal_three_buffer_makespan_seconds", three_buffer),
        ("convert_workers_1_makespan_seconds", convert_1),
        ("convert_workers_2_makespan_seconds", convert_2),
        ("convert_workers_4_makespan_seconds", convert_4),
        ("simulated_two_buffer_speedup", current_makespan / two_buffer if two_buffer > 0.0 else 0.0),
        ("simulated_three_buffer_speedup", current_makespan / three_buffer if three_buffer > 0.0 else 0.0),
        ("simulated_convert_workers_2_speedup", convert_1 / convert_2 if convert_2 > 0.0 else 0.0),
        ("simulated_convert_workers_4_speedup", convert_1 / convert_4 if convert_4 > 0.0 else 0.0),
    ]

    total_gpu = sum(_float(row["gpu_path_seconds"]) for row in rows)
    total_convert = sum(_float(row["convert_seconds"]) for row in rows)
    total_archive = sum(_float(row["archive_write_seconds"]) for row in rows)
    total_pack = sum(_float(row["pack_seconds"]) for row in rows)
    summary.extend(
        [
            ("archive_writer_is_bottleneck", 1 if total_archive > total_gpu and total_archive > total_convert else 0),
            ("convert_is_bottleneck", 1 if total_convert > total_gpu and total_convert > total_archive else 0),
            ("gpu_is_bottleneck", 1 if total_gpu >= total_convert and total_gpu >= total_archive else 0),
            ("pack_is_bottleneck", 1 if total_pack > total_gpu and total_pack > total_convert else 0),
            ("chrome_trace_events", trace_events),
            (
                "simulation_assumption",
                "in_order_three_stage_pack_gpu_cpu_model_using_measured_durations_not_measured_runtime",
            ),
            ("decision", _decision(rows)),
        ]
    )

    args.output_tsv.parent.mkdir(parents=True, exist_ok=True)
    with args.output_tsv.open("wt", newline="") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=SUMMARY_FLUSH_FIELDS)
        writer.writeheader()
        for row in rows:
            out: dict[str, str] = {}
            for key in SUMMARY_FLUSH_FIELDS:
                value = row.get(key, "")
                if isinstance(value, float):
                    out[key] = f"{value:.6f}"
                elif isinstance(value, int):
                    out[key] = str(value)
                else:
                    out[key] = str(value)
            writer.writerow(out)

    args.output_summary.parent.mkdir(parents=True, exist_ok=True)
    args.output_summary.write_text(
        "\n".join(f"{key}={_format_summary_value(value)}" for key, value in summary) + "\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
