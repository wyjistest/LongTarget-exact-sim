#!/usr/bin/env python3
import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any


def _parse_int_csv(value: str, *, flag: str) -> list[int]:
    values: list[int] = []
    for item in value.split(","):
        text = item.strip()
        if not text:
            continue
        try:
            parsed = int(text)
        except ValueError as exc:
            raise ValueError(f"{flag} must be a comma-separated integer list") from exc
        if parsed < 1:
            raise ValueError(f"{flag} values must be >= 1")
        values.append(parsed)
    if not values:
        raise ValueError(f"{flag} must include at least one value")
    return values


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def _parse_run_spec(spec: str) -> tuple[str, Path]:
    if "=" in spec:
        label, path_text = spec.split("=", 1)
        label = label.strip()
        path_text = path_text.strip()
        if not label:
            raise ValueError("--run label must not be empty")
    else:
        path_text = spec.strip()
        label = Path(path_text).parent.name or Path(path_text).stem
    if not path_text:
        raise ValueError("--run path must not be empty")
    return label, Path(path_text)


def _shard_seconds(shard: dict[str, Any]) -> float:
    if shard.get("wall_seconds") is not None:
        return float(shard["wall_seconds"])
    run = shard.get("run")
    if isinstance(run, dict) and run.get("wall_seconds") is not None:
        return float(run["wall_seconds"])
    raise ValueError(f"shard {shard.get('shard_id', '<unknown>')} missing wall_seconds")


def _worker_seconds(worker: dict[str, Any], shard_seconds_by_id: dict[str, float]) -> float:
    if worker.get("wall_seconds") is not None:
        return float(worker["wall_seconds"])
    shard_ids = worker.get("shard_ids") or []
    return sum(shard_seconds_by_id[str(shard_id)] for shard_id in shard_ids)


def _shard_work(shard: dict[str, Any]) -> int | None:
    value = shard.get("estimated_cells")
    if value is None:
        value = shard.get("estimated_length")
    if value is None:
        return None
    return int(value)


def _pearson(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) != len(ys) or len(xs) < 2:
        return None
    x_mean = sum(xs) / len(xs)
    y_mean = sum(ys) / len(ys)
    numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys))
    x_var = sum((x - x_mean) ** 2 for x in xs)
    y_var = sum((y - y_mean) ** 2 for y in ys)
    if x_var <= 0.0 or y_var <= 0.0:
        return None
    return numerator / math.sqrt(x_var * y_var)


def _gpu_sharing_mode(worker_count: int, gpu_ids: list[str]) -> str:
    if not gpu_ids:
        return "none"
    if worker_count <= len(gpu_ids):
        return "exclusive"
    return "shared"


def _workers_per_gpu(worker_count: int, gpu_ids: list[str]) -> int | None:
    if not gpu_ids or worker_count % len(gpu_ids) != 0:
        return None
    return worker_count // len(gpu_ids)


def _greedy_assign_by_seconds(
    shards: list[dict[str, Any]],
    *,
    worker_count: int,
) -> dict[str, Any]:
    workers = [
        {
            "worker_id": worker_id,
            "shard_ids": [],
            "target_names": [],
            "predicted_seconds": 0.0,
        }
        for worker_id in range(worker_count)
    ]
    ordered = sorted(
        shards,
        key=lambda shard: (
            -float(shard["seconds"]),
            str(shard["shard_id"]),
        ),
    )
    for shard in ordered:
        worker = min(
            workers,
            key=lambda item: (
                float(item["predicted_seconds"]),
                int(item["worker_id"]),
            ),
        )
        worker["shard_ids"].append(shard["shard_id"])
        worker["target_names"].append(shard["target_name"])
        worker["predicted_seconds"] = float(worker["predicted_seconds"]) + float(shard["seconds"])

    total_seconds = sum(float(shard["seconds"]) for shard in shards)
    makespan = max(float(worker["predicted_seconds"]) for worker in workers) if workers else 0.0
    ideal = total_seconds / worker_count if worker_count else 0.0
    straggler_worker = max(
        workers,
        key=lambda worker: (
            float(worker["predicted_seconds"]),
            -int(worker["worker_id"]),
        ),
    )
    return {
        "worker_count": worker_count,
        "predicted_makespan_seconds": makespan,
        "ideal_makespan_seconds": ideal,
        "scheduler_efficiency": ideal / makespan if makespan else None,
        "idle_fraction_estimate": 1.0 - (ideal / makespan) if makespan else None,
        "empty_worker_count": sum(1 for worker in workers if not worker["shard_ids"]),
        "straggler_worker": straggler_worker["worker_id"],
        "per_worker": workers,
    }


def _analyze_run(
    *,
    label: str,
    path: Path,
    data: dict[str, Any],
    simulate_workers: list[int],
) -> dict[str, Any]:
    per_shard_raw = data.get("per_shard")
    per_worker_raw = data.get("per_worker")
    if not isinstance(per_shard_raw, list) or not isinstance(per_worker_raw, list):
        raise ValueError(f"{path} must contain per_shard and per_worker lists")

    shards: list[dict[str, Any]] = []
    for raw in per_shard_raw:
        if not isinstance(raw, dict):
            raise ValueError(f"{path} per_shard entries must be objects")
        seconds = _shard_seconds(raw)
        work = _shard_work(raw)
        records = int(raw.get("records") or 0)
        time_per_work = seconds / work if work else None
        shards.append(
            {
                "shard_id": raw.get("shard_id"),
                "target_name": raw.get("target_name"),
                "target_start": raw.get("target_start"),
                "target_end": raw.get("target_end"),
                "worker_id": raw.get("worker_id"),
                "gpu_id": raw.get("gpu_id"),
                "cpu_core_range": raw.get("cpu_core_range"),
                "estimated_length": raw.get("estimated_length"),
                "estimated_cells": raw.get("estimated_cells"),
                "estimated_work": work,
                "seconds": seconds,
                "records": records,
                "raw_records": raw.get("raw_records"),
                "digest": raw.get("digest") or raw.get("output_digest"),
                "status": raw.get("status"),
                "time_per_estimated_work": time_per_work,
                "records_per_second": records / seconds if seconds else None,
            }
        )

    shard_seconds_by_id = {str(shard["shard_id"]): float(shard["seconds"]) for shard in shards}
    shard_by_id = {str(shard["shard_id"]): shard for shard in shards}

    per_worker: list[dict[str, Any]] = []
    for raw in per_worker_raw:
        if not isinstance(raw, dict):
            raise ValueError(f"{path} per_worker entries must be objects")
        worker_id = int(raw["worker_id"])
        shard_ids = [str(shard_id) for shard_id in raw.get("shard_ids") or []]
        actual_seconds = _worker_seconds(raw, shard_seconds_by_id)
        assigned_shards = [shard_by_id[shard_id] for shard_id in shard_ids if shard_id in shard_by_id]
        per_worker.append(
            {
                "worker_id": worker_id,
                "gpu_id": raw.get("gpu_id"),
                "cpu_core_range": raw.get("cpu_core_range"),
                "shard_ids": shard_ids,
                "target_names": [shard["target_name"] for shard in assigned_shards],
                "shard_count": len(shard_ids),
                "estimated_length": raw.get("estimated_length"),
                "estimated_cells": raw.get("estimated_cells"),
                "actual_seconds": actual_seconds,
                "sum_shard_seconds": sum(float(shard["seconds"]) for shard in assigned_shards),
                "records": raw.get("records"),
                "raw_records": raw.get("raw_records"),
            }
        )

    worker_count = int(data.get("worker_count") or len(per_worker))
    total_shard_seconds = sum(float(shard["seconds"]) for shard in shards)
    actual_makespan = max(float(worker["actual_seconds"]) for worker in per_worker) if per_worker else 0.0
    ideal_makespan = total_shard_seconds / worker_count if worker_count else 0.0
    straggler = max(
        per_worker,
        key=lambda worker: (
            float(worker["actual_seconds"]),
            -int(worker["worker_id"]),
        ),
    )
    straggler_shards = [
        shard_by_id[shard_id]
        for shard_id in straggler["shard_ids"]
        if shard_id in shard_by_id
    ]

    work_pairs = [
        (float(shard["estimated_work"]), float(shard["seconds"]))
        for shard in shards
        if shard["estimated_work"] is not None
    ]
    record_pairs = [
        (float(shard["records"]), float(shard["seconds"]))
        for shard in shards
        if shard["records"] is not None
    ]
    simulation = [
        _greedy_assign_by_seconds(shards, worker_count=count)
        for count in simulate_workers
    ]
    best_sim = min(
        simulation,
        key=lambda item: (
            float(item["predicted_makespan_seconds"]),
            int(item["worker_count"]),
        ),
    )

    return {
        "run_label": label,
        "report_path": str(path),
        "run_status": data.get("run_status"),
        "worker_count": worker_count,
        "gpu_ids": data.get("gpu_ids") or [],
        "workers_per_gpu": data.get("workers_per_gpu")
        if data.get("workers_per_gpu") is not None
        else _workers_per_gpu(worker_count, data.get("gpu_ids") or []),
        "gpu_sharing_mode": data.get("gpu_sharing_mode")
        or _gpu_sharing_mode(worker_count, data.get("gpu_ids") or []),
        "cpu_core_ranges": data.get("cpu_core_ranges") or [],
        "merged_digest": data.get("merged_digest"),
        "merged_records": data.get("merged_records"),
        "duplicate_records_removed": data.get("duplicate_records_removed")
        if data.get("duplicate_records_removed") is not None
        else data.get("duplicate_removed"),
        "failed_shards": data.get("failed_shards") or [],
        "resumed_shards": data.get("resumed_shards") or [],
        "shard_count": len(shards),
        "actual_makespan_seconds": actual_makespan,
        "total_shard_seconds": total_shard_seconds,
        "ideal_makespan_seconds": ideal_makespan,
        "scheduler_efficiency": ideal_makespan / actual_makespan if actual_makespan else None,
        "idle_fraction_estimate": 1.0 - (ideal_makespan / actual_makespan)
        if actual_makespan
        else None,
        "straggler_worker": straggler["worker_id"],
        "straggler_shards": straggler_shards,
        "empty_worker_count": sum(1 for worker in per_worker if not worker["shard_ids"]),
        "time_correlation": {
            "estimated_length_vs_seconds": _pearson(
                [x for x, _ in work_pairs],
                [y for _, y in work_pairs],
            ),
            "records_vs_seconds": _pearson(
                [x for x, _ in record_pairs],
                [y for _, y in record_pairs],
            ),
        },
        "predicted_best_worker_count_by_observed_times": best_sim["worker_count"],
        "observed_time_greedy_simulation": simulation,
        "per_worker": per_worker,
        "per_shard": shards,
    }


def _digest_map(run: dict[str, Any]) -> dict[str, str | None]:
    return {
        str(shard["shard_id"]): shard.get("digest")
        for shard in run["per_shard"]
    }


def _cross_run_summary(runs: list[dict[str, Any]]) -> dict[str, Any]:
    merged_digests = {run.get("merged_digest") for run in runs if run.get("merged_digest")}
    first_digest_map = _digest_map(runs[0]) if runs else {}
    digest_mismatches: list[dict[str, Any]] = []
    for run in runs[1:]:
        current = _digest_map(run)
        all_shard_ids = sorted(set(first_digest_map) | set(current))
        for shard_id in all_shard_ids:
            if first_digest_map.get(shard_id) != current.get(shard_id):
                digest_mismatches.append(
                    {
                        "run_label": run["run_label"],
                        "shard_id": shard_id,
                        "baseline_digest": first_digest_map.get(shard_id),
                        "digest": current.get(shard_id),
                    }
                )

    best = min(
        runs,
        key=lambda run: (
            float(run["actual_makespan_seconds"]),
            int(run["worker_count"]),
        ),
    )
    return {
        "merged_digest_consistent": len(merged_digests) <= 1,
        "merged_digests": sorted(merged_digests),
        "per_shard_digest_consistent": not digest_mismatches,
        "per_shard_digest_mismatches": digest_mismatches,
        "best_observed_run_label": best["run_label"],
        "best_observed_worker_count": best["worker_count"],
        "best_observed_seconds": best["actual_makespan_seconds"],
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Analyze completed Fasim sharded runner reports for actual "
            "per-shard/per-worker stragglers. This does not run Fasim."
        )
    )
    parser.add_argument(
        "--workload-name",
        required=True,
        help="Workload label for the output report.",
    )
    parser.add_argument(
        "--run",
        action="append",
        required=True,
        help="Run report path, optionally as label=path. May be repeated.",
    )
    parser.add_argument(
        "--simulate-workers",
        default="1,2,3,4,5,6,8",
        help="Comma-separated worker counts for observed-time greedy simulation.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Write JSON report to this path.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    simulate_workers = _parse_int_csv(args.simulate_workers, flag="--simulate-workers")
    run_specs = [_parse_run_spec(spec) for spec in args.run]

    runs: list[dict[str, Any]] = []
    for label, path in run_specs:
        resolved = path.resolve()
        if not resolved.exists():
            raise RuntimeError(f"missing run report: {resolved}")
        runs.append(
            _analyze_run(
                label=label,
                path=resolved,
                data=_load_json(resolved),
                simulate_workers=simulate_workers,
            )
        )

    report = {
        "schema_version": 1,
        "mode": "sharded_run_straggler_analysis",
        "fasim_execution": False,
        "workload_name": args.workload_name,
        "run_labels": [run["run_label"] for run in runs],
        "simulate_workers": simulate_workers,
        "cross_run": _cross_run_summary(runs),
        "runs": runs,
        "notes": [
            "This analysis reads completed sharded runner reports; it does not run Fasim.",
            "Observed-time simulation reassigns completed contig shard durations and does not model GPU or CPU contention.",
            "This report does not validate single whole-target digest equality or runtime scaling on other hardware.",
        ],
    }

    encoded = json.dumps(report, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
