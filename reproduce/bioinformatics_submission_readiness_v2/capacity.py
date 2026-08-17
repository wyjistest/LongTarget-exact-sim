#!/usr/bin/env python3
"""Deterministic makespan and paired hierarchical capacity estimators."""

from __future__ import annotations

import argparse
import json
import math
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence


SECONDS_PER_DAY = 86400.0


class CapacityError(ValueError):
    pass


@dataclass(frozen=True)
class WorkloadTimings:
    workload_id: str
    authority_seconds: tuple[float, ...]
    gpu_seconds: tuple[float, ...]

    def validate(self) -> None:
        if not self.workload_id:
            raise CapacityError("workload_id must be nonempty")
        if not self.authority_seconds or len(self.authority_seconds) != len(self.gpu_seconds):
            raise CapacityError(f"{self.workload_id} must have paired nonempty repeats")
        for value in (*self.authority_seconds, *self.gpu_seconds):
            if not math.isfinite(value) or value <= 0:
                raise CapacityError(f"{self.workload_id} contains an invalid duration")


def scheduled_makespan(durations: Sequence[float], workers: int) -> float:
    if workers <= 0:
        raise CapacityError("worker count must be positive")
    if not durations:
        raise CapacityError("scheduler requires at least one task")
    available = [0.0] * workers
    for duration in durations:
        if not math.isfinite(duration) or duration <= 0:
            raise CapacityError("scheduler duration must be finite and positive")
        worker = min(range(workers), key=lambda index: (available[index], index))
        available[worker] += duration
    return max(available)


def capacity_summary(
    authority_durations: Sequence[float],
    gpu_durations: Sequence[float],
    *,
    authority_workers: int,
    gpu_workers: int,
) -> dict[str, float]:
    if len(authority_durations) != len(gpu_durations) or not authority_durations:
        raise CapacityError("capacity arms must contain the same positive workload count")
    authority_makespan = scheduled_makespan(authority_durations, authority_workers)
    gpu_makespan = scheduled_makespan(gpu_durations, gpu_workers)
    units = float(len(authority_durations))
    authority_capacity = SECONDS_PER_DAY * units / authority_makespan
    gpu_capacity = SECONDS_PER_DAY * units / gpu_makespan
    return {
        "validated_work_units": units,
        "authority_makespan_seconds": authority_makespan,
        "gpu_makespan_seconds": gpu_makespan,
        "authority_capacity_24h": authority_capacity,
        "gpu_capacity_24h": gpu_capacity,
        "capacity_ratio": gpu_capacity / authority_capacity,
    }


def workload_mean_durations(rows: Sequence[WorkloadTimings]) -> tuple[list[float], list[float]]:
    authority = []
    gpu = []
    for row in rows:
        row.validate()
        authority.append(math.fsum(row.authority_seconds) / len(row.authority_seconds))
        gpu.append(math.fsum(row.gpu_seconds) / len(row.gpu_seconds))
    return authority, gpu


def inverted_cdf(values: Sequence[float], probability: float) -> float:
    if not values or not 0 <= probability <= 1:
        raise CapacityError("invalid empirical quantile request")
    ordered = sorted(values)
    index = max(0, math.ceil(probability * len(ordered)) - 1)
    return ordered[index]


def paired_hierarchical_bootstrap(
    rows: Sequence[WorkloadTimings],
    *,
    authority_workers: int,
    gpu_workers: int,
    replicates: int,
    seed: int,
) -> dict[str, Any]:
    if not rows or replicates <= 0:
        raise CapacityError("bootstrap requires workloads and positive replicates")
    for row in rows:
        row.validate()
    rng = random.Random(seed)
    ratios: list[float] = []
    workload_count = len(rows)
    for _ in range(replicates):
        authority_tasks: list[float] = []
        gpu_tasks: list[float] = []
        for _outer in range(workload_count):
            row = rows[rng.randrange(workload_count)]
            sampled_pairs = [rng.randrange(len(row.authority_seconds)) for _ in row.authority_seconds]
            authority_tasks.append(
                math.fsum(row.authority_seconds[index] for index in sampled_pairs)
                / len(sampled_pairs)
            )
            gpu_tasks.append(
                math.fsum(row.gpu_seconds[index] for index in sampled_pairs)
                / len(sampled_pairs)
            )
        ratios.append(
            capacity_summary(
                authority_tasks,
                gpu_tasks,
                authority_workers=authority_workers,
                gpu_workers=gpu_workers,
            )["capacity_ratio"]
        )
    authority, gpu = workload_mean_durations(rows)
    point = capacity_summary(
        authority,
        gpu,
        authority_workers=authority_workers,
        gpu_workers=gpu_workers,
    )
    return {
        "schema_version": 1,
        "estimand": "validated_24_hour_capacity_ratio",
        "point_estimate": point,
        "bootstrap": {
            "seed": seed,
            "replicates": replicates,
            "outer_resampling_unit": "paired_workload",
            "inner_resampling_unit": "paired_timing_repeat_within_workload",
            "within_workload_task_duration": "arithmetic_mean_of_inner_resampled_repeats",
            "scheduler_replayed_per_replicate": True,
            "quantile_method": "inverted_cdf",
            "one_sided_95_lcb": inverted_cdf(ratios, 0.05),
        },
    }


def timings_from_mapping(value: Mapping[str, Any]) -> list[WorkloadTimings]:
    raw = value.get("workloads")
    if not isinstance(raw, list):
        raise CapacityError("input must contain a workloads array")
    rows = []
    for item in raw:
        if not isinstance(item, dict):
            raise CapacityError("workload timing must be an object")
        rows.append(
            WorkloadTimings(
                workload_id=str(item.get("workload_id", "")),
                authority_seconds=tuple(float(v) for v in item.get("authority_seconds", [])),
                gpu_seconds=tuple(float(v) for v in item.get("gpu_seconds", [])),
            )
        )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--authority-workers", required=True, type=int)
    parser.add_argument("--gpu-workers", required=True, type=int)
    parser.add_argument("--replicates", required=True, type=int)
    parser.add_argument("--seed", required=True, type=int)
    args = parser.parse_args()
    try:
        value = json.loads(args.input.read_text(encoding="utf-8"))
        result = paired_hierarchical_bootstrap(
            timings_from_mapping(value),
            authority_workers=args.authority_workers,
            gpu_workers=args.gpu_workers,
            replicates=args.replicates,
            seed=args.seed,
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, CapacityError, TypeError) as error:
        print(f"capacity estimation failed: {error}")
        return 1
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
