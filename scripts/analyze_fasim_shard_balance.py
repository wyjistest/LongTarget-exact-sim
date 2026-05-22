#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

import fasim_sharded_runner as runner


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


def _shards_from_fasta(target: Path) -> list[runner.Shard]:
    records = runner._read_fasta(target)
    if not records:
        raise ValueError(f"no FASTA records found in {target}")

    shards: list[runner.Shard] = []
    for idx, record in enumerate(records):
        target_name, start, end = runner._parse_target_header(record)
        shard_id = f"shard_{idx:04d}_{runner._sanitize_for_path(target_name)}"
        shards.append(
            runner.Shard(
                shard_id=shard_id,
                target_name=target_name,
                target_start=start,
                target_end=end,
                shard_fasta_path=target,
                estimated_length=len(record.sequence),
                estimated_windows=None,
                estimated_cells=None,
            )
        )
    return shards


def _shard_work(shard: runner.Shard) -> int:
    return int(shard.estimated_cells or shard.estimated_length)


def _effective_workers_per_gpu(
    *, worker_count: int, gpu_ids: list[str]
) -> float | None:
    if not gpu_ids:
        return None
    return worker_count / len(gpu_ids)


def _integer_workers_per_gpu(
    *, worker_count: int, gpu_ids: list[str]
) -> int | None:
    if not gpu_ids:
        return None
    if worker_count % len(gpu_ids) != 0:
        return None
    return worker_count // len(gpu_ids)


def _resolve_cpu_ranges_for_count(
    *,
    args: argparse.Namespace,
    explicit_cpu_core_ranges: list[str],
    worker_count: int,
) -> list[str]:
    if explicit_cpu_core_ranges and args.auto_cpu_core_ranges:
        raise ValueError("--cpu-core-ranges and --auto-cpu-core-ranges cannot be used together")
    if explicit_cpu_core_ranges:
        if len(explicit_cpu_core_ranges) < worker_count:
            raise ValueError("--cpu-core-ranges must include at least one range per worker")
        return explicit_cpu_core_ranges[:worker_count]
    return runner._resolve_cpu_core_ranges(
        explicit_cpu_core_ranges=[],
        auto_cpu_core_ranges=bool(args.auto_cpu_core_ranges),
        cpu_pool=args.cpu_pool,
        cpu_cores_per_worker=args.cpu_cores_per_worker,
        worker_count=worker_count,
    )


def _assignment_report(
    *,
    shards: list[runner.Shard],
    worker_count: int,
    gpu_ids: list[str],
    cpu_core_ranges: list[str],
) -> dict[str, object]:
    assignments = runner._assign_shards_to_workers(
        shards,
        worker_count=worker_count,
        gpu_ids=gpu_ids,
        cpu_core_ranges=cpu_core_ranges,
    )
    total_work = sum(_shard_work(shard) for shard in shards)
    per_worker_work = {
        assignment.worker_id: sum(_shard_work(shard) for shard in assignment.shards)
        for assignment in assignments
    }
    predicted_makespan = max(per_worker_work.values()) if per_worker_work else 0
    ideal_work = total_work / worker_count if worker_count else 0.0
    largest_shard = max(shards, key=lambda shard: (_shard_work(shard), shard.shard_id))
    straggler_worker = min(
        per_worker_work,
        key=lambda worker_id: (-per_worker_work[worker_id], worker_id),
    )
    shard_to_worker = {
        shard.shard_id: assignment.worker_id
        for assignment in assignments
        for shard in assignment.shards
    }

    per_worker: list[dict[str, object]] = []
    for assignment in assignments:
        worker_work = per_worker_work[assignment.worker_id]
        per_worker.append(
            {
                "worker_id": assignment.worker_id,
                "gpu_id": assignment.gpu_id,
                "cpu_core_range": assignment.cpu_core_range,
                "shard_ids": [shard.shard_id for shard in assignment.shards],
                "target_names": [shard.target_name for shard in assignment.shards],
                "shard_count": len(assignment.shards),
                "estimated_length": sum(shard.estimated_length for shard in assignment.shards),
                "estimated_cells": runner._sum_estimated_cells(assignment.shards),
                "estimated_work": worker_work,
                "work_fraction": worker_work / total_work if total_work else 0.0,
            }
        )

    per_shard = [
        {
            "shard_id": shard.shard_id,
            "target_name": shard.target_name,
            "target_start": shard.target_start,
            "target_end": shard.target_end,
            "estimated_length": shard.estimated_length,
            "estimated_windows": shard.estimated_windows,
            "estimated_cells": shard.estimated_cells,
            "estimated_work": _shard_work(shard),
            "assigned_worker": shard_to_worker[shard.shard_id],
        }
        for shard in shards
    ]
    straggler_assignment = assignments[straggler_worker]
    straggler_shard_ids = {shard.shard_id for shard in straggler_assignment.shards}
    straggler_shards = [
        item for item in per_shard if item["shard_id"] in straggler_shard_ids
    ]

    return {
        "worker_count": worker_count,
        "gpu_ids": gpu_ids,
        "workers_per_gpu": _integer_workers_per_gpu(
            worker_count=worker_count,
            gpu_ids=gpu_ids,
        ),
        "effective_workers_per_gpu": _effective_workers_per_gpu(
            worker_count=worker_count,
            gpu_ids=gpu_ids,
        ),
        "gpu_sharing_mode": runner._gpu_sharing_mode(
            worker_count=worker_count,
            gpu_ids=gpu_ids,
        ),
        "cpu_core_ranges": cpu_core_ranges,
        "taskset_enabled": bool(cpu_core_ranges),
        "total_estimated_work": total_work,
        "ideal_worker_work": ideal_work,
        "predicted_makespan_work": predicted_makespan,
        "predicted_makespan_cells": None,
        "predicted_makespan_length": predicted_makespan,
        "load_imbalance_ratio": predicted_makespan / ideal_work if ideal_work else 0.0,
        "idle_fraction_estimate": (
            1.0 - (total_work / (worker_count * predicted_makespan))
            if worker_count and predicted_makespan
            else 0.0
        ),
        "largest_shard_id": largest_shard.shard_id,
        "largest_shard_name": largest_shard.target_name,
        "largest_shard_work": _shard_work(largest_shard),
        "largest_shard_cells": largest_shard.estimated_cells,
        "largest_shard_length": largest_shard.estimated_length,
        "largest_shard_fraction": _shard_work(largest_shard) / total_work if total_work else 0.0,
        "empty_worker_count": sum(1 for assignment in assignments if not assignment.shards),
        "straggler_worker": straggler_worker,
        "straggler_shards": straggler_shards,
        "per_worker": per_worker,
        "per_shard": per_shard,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Plan-only Fasim contig-shard balance analysis. This does not run "
            "Fasim; it applies the sharded runner largest-first worker assignment "
            "to FASTA contigs and reports load-balance/straggler estimates."
        )
    )
    parser.add_argument("--target", type=Path, required=True, help="Target FASTA to analyze.")
    parser.add_argument(
        "--workload-name",
        default=None,
        help="Label used in the JSON report. Defaults to target FASTA stem.",
    )
    parser.add_argument(
        "--workers",
        default="1,2,4,6,8",
        help="Comma-separated worker counts to analyze.",
    )
    parser.add_argument(
        "--gpu-ids",
        default=None,
        help="Comma-separated CUDA_VISIBLE_DEVICES values assigned to workers.",
    )
    parser.add_argument(
        "--cpu-core-ranges",
        default=None,
        help="Comma-separated taskset CPU ranges. Prefixes are used for smaller worker counts.",
    )
    parser.add_argument(
        "--cpu-pool",
        default=None,
        help="CPU core pool used with --auto-cpu-core-ranges, e.g. 0-23.",
    )
    parser.add_argument(
        "--cpu-cores-per-worker",
        type=int,
        default=None,
        help="Number of CPU cores assigned to each worker in auto CPU binding mode.",
    )
    parser.add_argument(
        "--auto-cpu-core-ranges",
        action="store_true",
        help="Derive one taskset CPU range per analyzed worker.",
    )
    parser.add_argument("--output", type=Path, default=None, help="Write JSON report to this path.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    target = args.target.resolve()
    if not target.exists():
        raise RuntimeError(f"missing target FASTA: {target}")

    worker_counts = _parse_int_csv(args.workers, flag="--workers")
    gpu_ids = runner._parse_csv_list(args.gpu_ids, name="--gpu-ids")
    explicit_cpu_core_ranges = runner._parse_csv_list(
        args.cpu_core_ranges,
        name="--cpu-core-ranges",
    )
    shards = _shards_from_fasta(target)
    shard_plan = [
        {
            "shard_id": shard.shard_id,
            "target_name": shard.target_name,
            "target_start": shard.target_start,
            "target_end": shard.target_end,
            "estimated_length": shard.estimated_length,
            "estimated_windows": shard.estimated_windows,
            "estimated_cells": shard.estimated_cells,
            "estimated_work": _shard_work(shard),
        }
        for shard in shards
    ]
    runs = []
    for worker_count in worker_counts:
        cpu_core_ranges = _resolve_cpu_ranges_for_count(
            args=args,
            explicit_cpu_core_ranges=explicit_cpu_core_ranges,
            worker_count=worker_count,
        )
        runs.append(
            _assignment_report(
                shards=shards,
                worker_count=worker_count,
                gpu_ids=gpu_ids,
                cpu_core_ranges=cpu_core_ranges,
            )
        )

    estimated_cells_available = not any(shard.estimated_cells is None for shard in shards)
    report = {
        "schema_version": 1,
        "mode": "shard_balance_plan",
        "fasim_execution": False,
        "assignment_policy": "largest-first estimated_cells_or_length",
        "cost_metric": "estimated_cells" if estimated_cells_available else "estimated_length",
        "estimated_cells_available": estimated_cells_available,
        "estimated_windows_available": not any(shard.estimated_windows is None for shard in shards),
        "workload_name": args.workload_name or target.stem,
        "target_fasta": str(target),
        "target_fasta_digest": runner._sha256_file(target),
        "contig_count": len(shards),
        "shard_count": len(shards),
        "worker_counts": worker_counts,
        "gpu_ids": gpu_ids,
        "cpu_pool": args.cpu_pool,
        "cpu_cores_per_worker": args.cpu_cores_per_worker,
        "auto_cpu_core_ranges": bool(args.auto_cpu_core_ranges),
        "shard_plan_digest": runner._json_digest(shard_plan),
        "shard_plan": shard_plan,
        "runs": runs,
        "notes": [
            "Plan-only analysis; no Fasim subprocesses are executed.",
            "Current contig shards use estimated_length because estimated_cells is unavailable.",
            "This report does not validate digest equality or runtime scaling.",
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
