#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path


def union_intervals(intervals: list[tuple[int, int]]) -> list[tuple[int, int]]:
    merged: list[list[int]] = []
    for start, end in sorted((start, end) for start, end in intervals if end > start):
        if not merged or start > merged[-1][1]:
            merged.append([start, end])
        elif end > merged[-1][1]:
            merged[-1][1] = end
    return [(start, end) for start, end in merged]


def seconds(intervals: list[tuple[int, int]]) -> float:
    return sum(end - start for start, end in union_intervals(intervals)) / 1e9


def overlap_seconds(a_intervals: list[tuple[int, int]],
                    b_intervals: list[tuple[int, int]]) -> float:
    a = union_intervals(a_intervals)
    b = union_intervals(b_intervals)
    i = 0
    j = 0
    total = 0
    while i < len(a) and j < len(b):
        start = max(a[i][0], b[j][0])
        end = min(a[i][1], b[j][1])
        if end > start:
            total += end - start
        if a[i][1] < b[j][1]:
            i += 1
        else:
            j += 1
    return total / 1e9


def nvtx_intervals(con: sqlite3.Connection, name: str) -> list[tuple[int, int]]:
    query = """
        select n.start, n.end
        from NVTX_EVENTS n
        left join StringIds s on n.textId = s.id
        where n.end is not null
          and coalesce(n.text, s.value) = ?
        order by n.start
    """
    return [(int(start), int(end)) for start, end in con.execute(query, (name,))]


def table_intervals(con: sqlite3.Connection, table: str) -> list[tuple[int, int]]:
    try:
        return [(int(start), int(end))
                for start, end in con.execute(f"select start, end from {table}")]
    except sqlite3.OperationalError:
        return []


def emit_metric(metrics: list[tuple[str, str]], key: str, value: int | float | str) -> None:
    if isinstance(value, float):
        metrics.append((key, f"{value:.6f}"))
    else:
        metrics.append((key, str(value)))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Summarize GASAL2 NVTX/CUDA interval overlap from an Nsight SQLite export.")
    parser.add_argument("sqlite", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    con = sqlite3.connect(str(args.sqlite))
    kernel = table_intervals(con, "CUPTI_ACTIVITY_KIND_KERNEL")
    memcpy = table_intervals(con, "CUPTI_ACTIVITY_KIND_MEMCPY")
    gpu_activity = union_intervals(kernel + memcpy)

    ranges = {
        "flush": nvtx_intervals(con, "fasim.gasal2.flush"),
        "score_traceback": nvtx_intervals(con, "fasim.gasal2.score_traceback"),
        "pack": nvtx_intervals(con, "fasim.gasal2.pack"),
        "convert": nvtx_intervals(con, "fasim.gasal2.convert"),
        "two_slot_submit_result": nvtx_intervals(
            con, "fasim.gasal2.two_slot.submit_result"),
        "two_slot_cpu_finalizer": nvtx_intervals(
            con, "fasim.gasal2.two_slot.cpu_finalizer"),
        "two_slot_ordered_commit": nvtx_intervals(
            con, "fasim.gasal2.two_slot.ordered_commit"),
        "two_slot_slot_lifetime": nvtx_intervals(
            con, "fasim.gasal2.two_slot.slot_lifetime"),
        "two_slot_drain": nvtx_intervals(con, "fasim.gasal2.two_slot.drain"),
    }

    metrics: list[tuple[str, str]] = []
    emit_metric(metrics, "kernel_instances", len(kernel))
    emit_metric(metrics, "memcpy_instances", len(memcpy))
    emit_metric(metrics, "kernel_union_seconds", seconds(kernel))
    emit_metric(metrics, "memcpy_union_seconds", seconds(memcpy))
    emit_metric(metrics, "gpu_activity_union_seconds", seconds(gpu_activity))

    for label, intervals in ranges.items():
        range_seconds = seconds(intervals)
        gpu_overlap = overlap_seconds(intervals, gpu_activity)
        emit_metric(metrics, f"{label}_instances", len(intervals))
        emit_metric(metrics, f"{label}_seconds", range_seconds)
        emit_metric(metrics, f"{label}_gpu_activity_overlap_seconds", gpu_overlap)
        emit_metric(metrics, f"{label}_kernel_overlap_seconds",
                    overlap_seconds(intervals, kernel))
        emit_metric(metrics, f"{label}_memcpy_overlap_seconds",
                    overlap_seconds(intervals, memcpy))
        emit_metric(metrics, f"{label}_gpu_activity_overlap_fraction",
                    gpu_overlap / range_seconds if range_seconds > 0.0 else 0.0)

    text = "\n".join(f"{key}={value}" for key, value in metrics) + "\n"
    if args.output:
        args.output.write_text(text)
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
