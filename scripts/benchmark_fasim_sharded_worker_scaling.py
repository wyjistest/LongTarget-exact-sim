#!/usr/bin/env python3
import argparse
import json
import re
import shutil
import subprocess
import sys
import time
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


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _run_sharded_mode(
    *,
    worker_count: int,
    args: argparse.Namespace,
    work_dir: Path,
    gpu_ids: list[str],
    cpu_core_ranges: list[str],
) -> tuple[dict[str, object], float, Path]:
    run_dir = work_dir / f"workers_{worker_count}"
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "fasim_sharded_runner.py"),
        "--fasim-bin",
        str(args.fasim_bin),
        "--target",
        str(args.target),
        "--rna",
        str(args.rna),
        "--rule",
        str(args.rule),
        "--work-dir",
        str(run_dir),
        "--output-mode",
        args.output_mode,
        "--validate-single",
        "--workers",
        str(worker_count),
    ]

    if gpu_ids:
        cmd.extend(["--gpu-ids", ",".join(gpu_ids)])
    if cpu_core_ranges:
        if len(cpu_core_ranges) < worker_count:
            raise RuntimeError(
                "--cpu-core-ranges must include at least as many ranges as the largest worker count"
            )
        cmd.extend(["--cpu-core-ranges", ",".join(cpu_core_ranges[:worker_count])])
    for item in args.env:
        cmd.extend(["--env", item])
    for item in args.fasim_arg:
        cmd.extend(["--fasim-arg", item])

    stdout_path = work_dir / "logs" / f"workers_{worker_count}.stdout.log"
    stderr_path = work_dir / "logs" / f"workers_{worker_count}.stderr.log"
    stdout_path.parent.mkdir(parents=True, exist_ok=True)

    t0 = time.perf_counter()
    proc = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    t1 = time.perf_counter()

    stdout_path.write_text(proc.stdout, encoding="utf-8")
    stderr_path.write_text(proc.stderr, encoding="utf-8")
    if proc.returncode != 0:
        raise RuntimeError(
            f"workers={worker_count} sharded run failed with exit {proc.returncode}; see {stderr_path}"
        )

    report_path = run_dir / "report.json"
    if not report_path.exists():
        raise RuntimeError(f"missing sharded report: {report_path}")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    return report, t1 - t0, report_path


def _max_worker_seconds(report: dict[str, object]) -> float:
    per_worker = report.get("per_worker")
    if not isinstance(per_worker, list) or not per_worker:
        raise RuntimeError("sharded report has no per_worker timing")
    return max(float(worker.get("wall_seconds", 0.0)) for worker in per_worker)


def _sum_worker_seconds(report: dict[str, object]) -> float:
    per_worker = report.get("per_worker")
    if not isinstance(per_worker, list):
        return 0.0
    return sum(float(worker.get("wall_seconds", 0.0)) for worker in per_worker)


def _scan_counter_terms(report: dict[str, object], terms: tuple[str, ...]) -> int | None:
    log_paths: list[Path] = []
    for shard in report.get("per_shard", []):
        if not isinstance(shard, dict):
            continue
        run = shard.get("run")
        if not isinstance(run, dict):
            continue
        for key in ("stdout_path", "stderr_path"):
            value = run.get(key)
            if isinstance(value, str):
                log_paths.append(Path(value))

    total = 0
    found = False
    pattern = re.compile(r"=\s*(-?\d+)")
    for path in log_paths:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for line in text.splitlines():
            lower = line.lower()
            if any(term in lower for term in terms):
                match = pattern.search(line)
                if match:
                    total += int(match.group(1))
                    found = True
    return total if found else None


def _summarize_run(
    *,
    worker_count: int,
    report: dict[str, object],
    report_path: Path,
    runner_total_seconds: float,
    single_seconds: float,
    one_worker_seconds: float,
    baseline_digest: str,
) -> dict[str, object]:
    wall_seconds = _max_worker_seconds(report)
    merged_digest = str(report.get("merged_digest"))
    return {
        "worker_count": worker_count,
        "runner_total_seconds": runner_total_seconds,
        "wall_seconds": wall_seconds,
        "worker_seconds_sum": _sum_worker_seconds(report),
        "speedup_vs_single": single_seconds / wall_seconds if wall_seconds else None,
        "speedup_vs_1_worker": one_worker_seconds / wall_seconds if wall_seconds else None,
        "report_path": str(report_path),
        "shard_count": report.get("shard_count"),
        "worker_count_reported": report.get("worker_count"),
        "gpu_ids": report.get("gpu_ids"),
        "workers_per_gpu": report.get("workers_per_gpu"),
        "workers_derived_from_gpu_ids": report.get("workers_derived_from_gpu_ids"),
        "gpu_sharing_mode": report.get("gpu_sharing_mode"),
        "cpu_core_ranges": report.get("cpu_core_ranges"),
        "per_worker": report.get("per_worker"),
        "per_shard": report.get("per_shard"),
        "merged_records": report.get("merged_records"),
        "merged_digest": merged_digest,
        "single_records": report.get("single_records"),
        "single_digest": report.get("single_digest"),
        "single_vs_sharded_digest_match": report.get("single_vs_sharded_digest_match"),
        "duplicate_records_removed": report.get("duplicate_records_removed"),
        "digest_matches_baseline": merged_digest == baseline_digest,
        "fallbacks": _scan_counter_terms(report, ("fallback",)),
        "mismatches": _scan_counter_terms(report, ("mismatch",)),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Characterize contig sharded Fasim scaling across worker counts.",
    )
    parser.add_argument("--fasim-bin", required=True, type=Path)
    parser.add_argument("--target", required=True, type=Path)
    parser.add_argument("--rna", required=True, type=Path)
    parser.add_argument("--rule", default="0")
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
    parser.add_argument(
        "--gpu-ids",
        default=None,
        help="optional comma-separated GPU ids passed to the sharded runner",
    )
    parser.add_argument(
        "--cpu-core-ranges",
        default=None,
        help="optional comma-separated CPU ranges; sliced per worker count",
    )
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
    args.target = args.target.resolve()
    args.rna = args.rna.resolve()
    work_dir = args.work_dir.resolve()

    if not args.fasim_bin.exists():
        raise RuntimeError(f"missing Fasim binary: {args.fasim_bin}")
    if not args.target.exists():
        raise RuntimeError(f"missing target FASTA: {args.target}")
    if not args.rna.exists():
        raise RuntimeError(f"missing RNA FASTA: {args.rna}")

    worker_counts = _parse_int_csv(args.workers, flag="--workers")
    if 1 not in worker_counts:
        raise RuntimeError("--workers must include 1 so speedup_vs_1_worker is defined")
    gpu_ids = _parse_csv(args.gpu_ids, flag="--gpu-ids")
    cpu_core_ranges = _parse_csv(args.cpu_core_ranges, flag="--cpu-core-ranges")

    if work_dir.exists():
        shutil.rmtree(work_dir)
    (work_dir / "logs").mkdir(parents=True)

    raw_reports: dict[int, dict[str, object]] = {}
    report_paths: dict[int, Path] = {}
    runner_totals: dict[int, float] = {}
    for worker_count in worker_counts:
        report, runner_total_seconds, report_path = _run_sharded_mode(
            worker_count=worker_count,
            args=args,
            work_dir=work_dir,
            gpu_ids=gpu_ids,
            cpu_core_ranges=cpu_core_ranges,
        )
        raw_reports[worker_count] = report
        report_paths[worker_count] = report_path
        runner_totals[worker_count] = runner_total_seconds

    baseline = raw_reports[1]
    baseline_digest = str(baseline.get("merged_digest"))
    single_run = baseline.get("single_run")
    if not isinstance(single_run, dict):
        raise RuntimeError("1-worker baseline report missing single_run")
    single_seconds = float(single_run.get("wall_seconds", 0.0))
    if single_seconds <= 0:
        raise RuntimeError("1-worker baseline single_run wall_seconds is not positive")
    one_worker_seconds = _max_worker_seconds(baseline)

    runs = [
        _summarize_run(
            worker_count=worker_count,
            report=raw_reports[worker_count],
            report_path=report_paths[worker_count],
            runner_total_seconds=runner_totals[worker_count],
            single_seconds=single_seconds,
            one_worker_seconds=one_worker_seconds,
            baseline_digest=baseline_digest,
        )
        for worker_count in worker_counts
    ]

    best = min(runs, key=lambda run: float(run["wall_seconds"]))
    all_digest_match = all(
        run["single_vs_sharded_digest_match"] is True
        and run["digest_matches_baseline"] is True
        for run in runs
    )

    report = {
        "schema_version": 1,
        "mode": "fasim_sharded_worker_scaling",
        "target": str(args.target),
        "rna": str(args.rna),
        "rule": str(args.rule),
        "output_mode": args.output_mode,
        "env_overrides": args.env,
        "worker_counts": worker_counts,
        "gpu_ids": gpu_ids,
        "cpu_core_ranges": cpu_core_ranges,
        "baseline": {
            "worker_count": 1,
            "report_path": str(report_paths[1]),
            "single_seconds": single_seconds,
            "sharded_wall_seconds": one_worker_seconds,
            "merged_records": baseline.get("merged_records"),
            "merged_digest": baseline_digest,
            "single_digest": baseline.get("single_digest"),
            "single_vs_sharded_digest_match": baseline.get(
                "single_vs_sharded_digest_match"
            ),
        },
        "runs": runs,
        "summary": {
            "all_digest_match": all_digest_match,
            "best_worker_count": best["worker_count"],
            "best_wall_seconds": best["wall_seconds"],
            "best_speedup_vs_single": best["speedup_vs_single"],
            "best_speedup_vs_1_worker": best["speedup_vs_1_worker"],
        },
    }

    report_path = work_dir / "report.json"
    _write_json(report_path, report)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
