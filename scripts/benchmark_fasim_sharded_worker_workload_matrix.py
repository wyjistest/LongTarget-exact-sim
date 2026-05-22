#!/usr/bin/env python3
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


ROOT = _repo_root()


def _parse_int_csv(spec: str, *, flag: str) -> list[int]:
    values: list[int] = []
    for raw in spec.split(","):
        item = raw.strip()
        if not item:
            continue
        try:
            value = int(item)
        except ValueError as e:
            raise RuntimeError(f"invalid {flag} entry: {item}") from e
        if value < 1:
            raise RuntimeError(f"{flag} entries must be >= 1: {item}")
        values.append(value)
    if not values:
        raise RuntimeError(f"{flag} must not be empty")
    return sorted(set(values))


def _parse_csv(spec: str | None, *, flag: str) -> list[str]:
    if spec is None or not spec.strip():
        return []
    values = [item.strip() for item in spec.split(",")]
    if any(not value for value in values):
        raise RuntimeError(f"{flag} must not include empty entries")
    return values


def _parse_workload(spec: str) -> dict[str, object]:
    parts = spec.split(":", 3)
    if len(parts) != 4:
        raise RuntimeError(
            "--workload must be NAME:TARGET_FASTA:RNA_FASTA:RULE, got: " + spec
        )
    name, target, rna, rule = parts
    if not name:
        raise RuntimeError("--workload name must not be empty")
    target_path = Path(target).resolve()
    rna_path = Path(rna).resolve()
    if not target_path.exists():
        raise RuntimeError(f"missing workload target FASTA: {target_path}")
    if not rna_path.exists():
        raise RuntimeError(f"missing workload RNA FASTA: {rna_path}")
    return {
        "name": name,
        "target": str(target_path),
        "rna": str(rna_path),
        "rule": rule,
    }


def _sanitize_name(name: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in name)
    cleaned = cleaned.strip("._-")
    return cleaned or "workload"


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _run_scaling_for_workload(
    *,
    workload: dict[str, object],
    args: argparse.Namespace,
    worker_counts: list[int],
    gpu_ids: list[str],
    cpu_core_ranges: list[str],
    work_dir: Path,
) -> tuple[dict[str, object], Path]:
    name = str(workload["name"])
    run_dir = work_dir / _sanitize_name(name)
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "benchmark_fasim_sharded_worker_scaling.py"),
        "--fasim-bin",
        str(args.fasim_bin),
        "--target",
        str(workload["target"]),
        "--rna",
        str(workload["rna"]),
        "--rule",
        str(workload["rule"]),
        "--work-dir",
        str(run_dir),
        "--output-mode",
        args.output_mode,
        "--workers",
        ",".join(str(value) for value in worker_counts),
    ]

    if gpu_ids:
        cmd.extend(["--gpu-ids", ",".join(gpu_ids)])
    if cpu_core_ranges:
        cmd.extend(["--cpu-core-ranges", ",".join(cpu_core_ranges)])
    for item in args.env:
        cmd.extend(["--env", item])
    for item in args.fasim_arg:
        cmd.extend(["--fasim-arg", item])

    stdout_path = work_dir / "logs" / f"{_sanitize_name(name)}.stdout.log"
    stderr_path = work_dir / "logs" / f"{_sanitize_name(name)}.stderr.log"
    stdout_path.parent.mkdir(parents=True, exist_ok=True)

    proc = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    stdout_path.write_text(proc.stdout, encoding="utf-8")
    stderr_path.write_text(proc.stderr, encoding="utf-8")
    if proc.returncode != 0:
        raise RuntimeError(
            f"workload {name} failed with exit {proc.returncode}; see {stderr_path}"
        )

    report_path = run_dir / "report.json"
    if not report_path.exists():
        raise RuntimeError(f"missing workload report: {report_path}")
    return json.loads(report_path.read_text(encoding="utf-8")), report_path


def _summarize_workload(
    *,
    workload: dict[str, object],
    report: dict[str, object],
    report_path: Path,
) -> dict[str, object]:
    runs = report.get("runs")
    if not isinstance(runs, list) or not runs:
        raise RuntimeError(f"workload {workload['name']} has no runs")

    baseline = report.get("baseline")
    if not isinstance(baseline, dict):
        raise RuntimeError(f"workload {workload['name']} has no baseline")

    all_digest_match = bool(report.get("summary", {}).get("all_digest_match"))
    first_run = runs[0]
    shard_count = first_run.get("shard_count") if isinstance(first_run, dict) else None
    best = min(runs, key=lambda run: float(run["wall_seconds"]))

    normalized_runs = []
    for run in runs:
        normalized_runs.append(
            {
                "worker_count": run.get("worker_count"),
                "shard_count": run.get("shard_count"),
                "gpu_ids": run.get("gpu_ids"),
                "workers_per_gpu": run.get("workers_per_gpu"),
                "workers_derived_from_gpu_ids": run.get(
                    "workers_derived_from_gpu_ids"
                ),
                "gpu_sharing_mode": run.get("gpu_sharing_mode"),
                "cpu_core_ranges": run.get("cpu_core_ranges"),
                "per_worker_seconds": [
                    worker.get("wall_seconds") for worker in run.get("per_worker", [])
                ],
                "per_worker_estimated_cells": [
                    worker.get("estimated_cells") for worker in run.get("per_worker", [])
                ],
                "per_worker_records": [
                    worker.get("records") for worker in run.get("per_worker", [])
                ],
                "per_shard_seconds": [
                    shard.get("run", {}).get("wall_seconds")
                    for shard in run.get("per_shard", [])
                ],
                "per_shard_records": [
                    shard.get("records") for shard in run.get("per_shard", [])
                ],
                "per_shard_digest": [
                    shard.get("digest") for shard in run.get("per_shard", [])
                ],
                "merged_records": run.get("merged_records"),
                "merged_digest": run.get("merged_digest"),
                "single_digest": run.get("single_digest"),
                "single_vs_sharded_digest_match": run.get(
                    "single_vs_sharded_digest_match"
                ),
                "duplicate_records_removed": run.get("duplicate_records_removed"),
                "wall_seconds": run.get("wall_seconds"),
                "runner_total_seconds": run.get("runner_total_seconds"),
                "speedup_vs_single_worker": run.get("speedup_vs_1_worker"),
                "speedup_vs_single_whole_run": run.get("speedup_vs_single"),
                "fallbacks": run.get("fallbacks"),
                "mismatches": run.get("mismatches"),
                "report_path": run.get("report_path"),
            }
        )

    return {
        "name": workload["name"],
        "target": workload["target"],
        "rna": workload["rna"],
        "rule": workload["rule"],
        "report_path": str(report_path),
        "shard_count": shard_count,
        "all_digest_match": all_digest_match,
        "baseline": baseline,
        "runs": normalized_runs,
        "best_worker_count": best.get("worker_count"),
        "best_wall_seconds": best.get("wall_seconds"),
        "best_speedup_vs_single_worker": best.get("speedup_vs_1_worker"),
        "best_speedup_vs_single_whole_run": best.get("speedup_vs_single"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run a sharded worker scaling matrix across multi-contig Fasim workloads.",
    )
    parser.add_argument(
        "--workload",
        action="append",
        required=True,
        metavar="NAME:TARGET_FASTA:RNA_FASTA:RULE",
        help="workload to characterize; repeatable",
    )
    parser.add_argument("--fasim-bin", required=True, type=Path)
    parser.add_argument("--work-dir", required=True, type=Path)
    parser.add_argument(
        "--output-mode",
        choices=("lite", "tfosorted"),
        default="lite",
    )
    parser.add_argument(
        "--workers",
        default="1,2,4",
        help="comma-separated worker counts to characterize",
    )
    parser.add_argument("--gpu-ids", default=None)
    parser.add_argument("--cpu-core-ranges", default=None)
    parser.add_argument(
        "--env",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="environment override passed to every Fasim worker",
    )
    parser.add_argument(
        "--fasim-arg",
        action="append",
        default=[],
        help="extra single argument appended to each Fasim invocation",
    )

    args = parser.parse_args()
    args.fasim_bin = args.fasim_bin.resolve()
    work_dir = args.work_dir.resolve()

    if not args.fasim_bin.exists():
        raise RuntimeError(f"missing Fasim binary: {args.fasim_bin}")

    workloads = [_parse_workload(spec) for spec in args.workload]
    worker_counts = _parse_int_csv(args.workers, flag="--workers")
    if 1 not in worker_counts:
        raise RuntimeError("--workers must include 1")
    gpu_ids = _parse_csv(args.gpu_ids, flag="--gpu-ids")
    cpu_core_ranges = _parse_csv(args.cpu_core_ranges, flag="--cpu-core-ranges")

    if work_dir.exists():
        shutil.rmtree(work_dir)
    (work_dir / "logs").mkdir(parents=True)

    workload_reports = []
    for workload in workloads:
        report, report_path = _run_scaling_for_workload(
            workload=workload,
            args=args,
            worker_counts=worker_counts,
            gpu_ids=gpu_ids,
            cpu_core_ranges=cpu_core_ranges,
            work_dir=work_dir,
        )
        workload_reports.append(
            _summarize_workload(
                workload=workload,
                report=report,
                report_path=report_path,
            )
        )

    all_digest_match = all(
        bool(workload["all_digest_match"]) for workload in workload_reports
    )
    output = {
        "schema_version": 1,
        "mode": "fasim_sharded_worker_workload_matrix",
        "output_mode": args.output_mode,
        "worker_counts": worker_counts,
        "gpu_ids": gpu_ids,
        "cpu_core_ranges": cpu_core_ranges,
        "env_overrides": args.env,
        "workloads": workload_reports,
        "summary": {
            "workloads": len(workload_reports),
            "all_digest_match": all_digest_match,
        },
    }
    report_path = work_dir / "report.json"
    _write_json(report_path, output)
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
