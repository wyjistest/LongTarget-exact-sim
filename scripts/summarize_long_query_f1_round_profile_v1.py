#!/usr/bin/env python3
"""Validate and summarize owner-only F1 per-round telemetry."""

from __future__ import annotations

import argparse
import csv
import json
import os
import tempfile
from pathlib import Path
from typing import Callable, Dict, List, Sequence, TypeVar


SCHEMA_VERSION = "long_query_f1_round_profile_summary_v1"
COUNT_COLUMNS = (
    "round_active_groups",
    "round_forward_attempts",
    "round_reverse_requests",
)
TIME_COLUMNS = (
    "round_forward_total_seconds",
    "round_forward_gpu_seconds",
    "round_forward_h2d_seconds",
    "round_forward_d2h_seconds",
    "round_reverse_total_seconds",
    "round_reverse_gpu_seconds",
    "round_reverse_h2d_seconds",
    "round_reverse_d2h_seconds",
    "round_host_descriptor_seconds",
    "round_host_forward_apply_seconds",
    "round_host_reverse_compact_seconds",
    "round_host_reverse_apply_seconds",
    "round_host_retire_seconds",
)
REQUIRED_COLUMNS = {
    "task_index",
    "ok",
    "cpu_continuation_failures",
    "gpu_kernel_seconds",
    "round_profile_active",
    "round_profile_owner",
    "error",
    *COUNT_COLUMNS,
    *TIME_COLUMNS,
}

T = TypeVar("T", int, float)


def parse_vector(text: str, converter: Callable[[str], T]) -> List[T]:
    if not text:
        return []
    return [converter(value) for value in text.split(",")]


def add_vector(target: List[T], values: Sequence[T], zero: T) -> None:
    if len(target) < len(values):
        target.extend([zero] * (len(values) - len(target)))
    for index, value in enumerate(values):
        target[index] += value


def summarize(report_path: Path) -> Dict[str, object]:
    with report_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        missing = REQUIRED_COLUMNS.difference(reader.fieldnames or [])
        if missing:
            raise ValueError("missing required columns: " + ",".join(sorted(missing)))
        rows = list(reader)
    if not rows:
        raise ValueError("round profile report is empty")

    count_totals: Dict[str, List[int]] = {name: [] for name in COUNT_COLUMNS}
    time_totals: Dict[str, List[float]] = {name: [] for name in TIME_COLUMNS}
    owner_task_indexes: List[int] = []
    failures: List[str] = []
    aggregate_gpu_seconds = 0.0

    for row_number, row in enumerate(rows, start=2):
        count_vectors = {
            name: parse_vector(row[name], int) for name in COUNT_COLUMNS
        }
        count_lengths = {len(values) for values in count_vectors.values()}
        if len(count_lengths) != 1:
            failures.append(f"row_{row_number}_count_vectors_not_rectangular")
        for name, values in count_vectors.items():
            add_vector(count_totals[name], values, 0)

        active = row["round_profile_active"] == "1"
        owner = row["round_profile_owner"] == "1"
        if not active:
            failures.append(f"row_{row_number}_profile_not_active")
        time_vectors = {
            name: parse_vector(row[name], float) for name in TIME_COLUMNS
        }
        if owner:
            owner_task_indexes.append(int(row["task_index"]))
            expected_length = len(count_vectors[COUNT_COLUMNS[0]])
            if any(len(values) != expected_length for values in time_vectors.values()):
                failures.append(f"row_{row_number}_owner_vector_length_mismatch")
            for name, values in time_vectors.items():
                add_vector(time_totals[name], values, 0.0)
        elif any(time_vectors.values()):
            failures.append(f"row_{row_number}_non_owner_has_profile_values")

        if row["ok"] != "1":
            failures.append(f"row_{row_number}_not_ok")
        if int(row["cpu_continuation_failures"]) != 0:
            failures.append(f"row_{row_number}_continuation_failure")
        if row["error"] not in ("", "none"):
            failures.append(f"row_{row_number}_error_{row['error']}")
        aggregate_gpu_seconds += float(row["gpu_kernel_seconds"])

    if not owner_task_indexes:
        failures.append("no_round_profile_owner")

    profile_gpu_seconds = sum(time_totals["round_forward_gpu_seconds"]) + sum(
        time_totals["round_reverse_gpu_seconds"]
    )
    gpu_tolerance = max(1e-6, abs(aggregate_gpu_seconds) * 1e-6)
    gpu_difference = abs(profile_gpu_seconds - aggregate_gpu_seconds)
    if gpu_difference > gpu_tolerance:
        failures.append("round_gpu_sum_differs_from_aggregate")

    round_count = max((len(values) for values in count_totals.values()), default=0)
    rounds = []
    for round_index in range(round_count):
        def count(name: str) -> int:
            values = count_totals[name]
            return values[round_index] if round_index < len(values) else 0

        def seconds(name: str) -> float:
            values = time_totals[name]
            return values[round_index] if round_index < len(values) else 0.0

        forward_gpu = seconds("round_forward_gpu_seconds")
        reverse_gpu = seconds("round_reverse_gpu_seconds")
        round_gpu = forward_gpu + reverse_gpu
        rounds.append(
            {
                "round": round_index,
                "active_groups": count("round_active_groups"),
                "forward_attempts": count("round_forward_attempts"),
                "reverse_requests": count("round_reverse_requests"),
                "forward_total_seconds": seconds("round_forward_total_seconds"),
                "forward_gpu_seconds": forward_gpu,
                "forward_h2d_seconds": seconds("round_forward_h2d_seconds"),
                "forward_d2h_seconds": seconds("round_forward_d2h_seconds"),
                "reverse_total_seconds": seconds("round_reverse_total_seconds"),
                "reverse_gpu_seconds": reverse_gpu,
                "reverse_h2d_seconds": seconds("round_reverse_h2d_seconds"),
                "reverse_d2h_seconds": seconds("round_reverse_d2h_seconds"),
                "host_descriptor_seconds": seconds("round_host_descriptor_seconds"),
                "host_forward_apply_seconds": seconds(
                    "round_host_forward_apply_seconds"
                ),
                "host_reverse_compact_seconds": seconds(
                    "round_host_reverse_compact_seconds"
                ),
                "host_reverse_apply_seconds": seconds(
                    "round_host_reverse_apply_seconds"
                ),
                "host_retire_seconds": seconds("round_host_retire_seconds"),
                "gpu_seconds": round_gpu,
                "gpu_fraction": (
                    round_gpu / profile_gpu_seconds if profile_gpu_seconds else 0.0
                ),
            }
        )

    profiled_host_seconds = sum(
        sum(time_totals[name])
        for name in (
            "round_host_descriptor_seconds",
            "round_host_forward_apply_seconds",
            "round_host_reverse_compact_seconds",
            "round_host_reverse_apply_seconds",
            "round_host_retire_seconds",
        )
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "report": str(report_path),
        "rows": len(rows),
        "owner_count": len(owner_task_indexes),
        "owner_task_indexes": owner_task_indexes,
        "rounds": rounds,
        "aggregate_gpu_seconds": aggregate_gpu_seconds,
        "profile_gpu_seconds": profile_gpu_seconds,
        "gpu_sum_absolute_difference": gpu_difference,
        "gpu_sum_tolerance": gpu_tolerance,
        "profiled_host_seconds": profiled_host_seconds,
        "profiled_host_to_gpu_ratio": (
            profiled_host_seconds / profile_gpu_seconds
            if profile_gpu_seconds
            else 0.0
        ),
        "failures": failures,
        "decision": "round_profile_pass" if not failures else "round_profile_no_go",
    }


def write_json(path: Path, payload: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=path.name + ".tmp.", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    except BaseException:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = summarize(args.report)
    if args.output is not None:
        write_json(args.output, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["decision"] == "round_profile_pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
