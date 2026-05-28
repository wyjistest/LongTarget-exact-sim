#!/usr/bin/env python3
import argparse
import csv
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

import fasim_sharded_runner as runner


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


ROOT = _repo_root()


RAW_FIELDS = [
    "workload",
    "target_record_count",
    "target_bases",
    "group_label",
    "group_target_records",
    "grouped_shard_count",
    "worker_count",
    "wall_seconds",
    "runner_total_seconds",
    "speedup_vs_default_grouping",
    "digest_match",
    "merged_records",
    "duplicate_removed",
    "prealign_cuda_fallbacks",
    "prealign_cuda_fallback_delta_vs_default",
    "prealign_cuda_tasks",
    "prealign_cuda_batches",
    "profile_cache_active",
    "profile_cache_calls",
    "profile_cache_hits",
    "profile_cache_misses",
    "profile_cache_hit_rate",
    "extend_seconds",
    "output_seconds",
    "imbalance_ratio",
    "per_worker_seconds",
    "per_worker_shards",
    "per_shard_records",
    "per_shard_seconds",
    "manifest_resume_status",
    "report_path",
]


def _parse_csv(spec: str | None, *, flag: str) -> list[str]:
    if spec is None or not spec.strip():
        return []
    values = [item.strip() for item in spec.split(",")]
    if any(not value for value in values):
        raise RuntimeError(f"{flag} must not include empty entries")
    return values


def _parse_csv_ints(spec: str, *, flag: str) -> list[int]:
    values: list[int] = []
    for raw in spec.split(","):
        item = raw.strip()
        if not item:
            continue
        try:
            value = int(item)
        except ValueError as exc:
            raise RuntimeError(f"invalid {flag} entry: {item}") from exc
        if value < 1:
            raise RuntimeError(f"{flag} entries must be >= 1: {item}")
        values.append(value)
    if not values:
        raise RuntimeError(f"{flag} must not be empty")
    return sorted(set(values))


def parse_group_values(spec: str) -> list[int | None]:
    values: list[int | None] = []
    for raw in spec.split(","):
        item = raw.strip()
        if not item:
            continue
        if item.lower() in {"none", "null", "default", "baseline"}:
            values.append(None)
            continue
        try:
            value = int(item)
        except ValueError as exc:
            raise RuntimeError(f"invalid --group-target-records entry: {item}") from exc
        if value < 1:
            raise RuntimeError("--group-target-records entries must be >= 1")
        values.append(value)
    if not values:
        raise RuntimeError("--group-target-records must not be empty")
    if None not in values:
        raise RuntimeError("--group-target-records must include none/default baseline")
    deduped: list[int | None] = []
    seen: set[int | None] = set()
    for value in values:
        if value in seen:
            continue
        deduped.append(value)
        seen.add(value)
    if deduped[0] is not None:
        deduped = [None] + [value for value in deduped if value is not None]
    return deduped


def group_label(group_target_records: int | None) -> str:
    return "default" if group_target_records is None else str(group_target_records)


def _parse_workload(spec: str) -> dict[str, object]:
    parts = spec.split(":", 3)
    if len(parts) != 4:
        raise RuntimeError(
            "--workload must be NAME:TARGET_FASTA:RNA_FASTA:RULE, got: " + spec
        )
    name, target, rna, rule = parts
    if not name.strip():
        raise RuntimeError("--workload name must not be empty")
    target_path = Path(target).resolve()
    rna_path = Path(rna).resolve()
    if not target_path.exists():
        raise RuntimeError(f"missing target FASTA: {target_path}")
    if not rna_path.exists():
        raise RuntimeError(f"missing RNA FASTA: {rna_path}")
    return {
        "name": name.strip(),
        "target": str(target_path),
        "rna": str(rna_path),
        "rule": rule,
    }


def _sanitize_name(name: object) -> str:
    text = str(name)
    cleaned = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in text)
    cleaned = cleaned.strip("._-")
    return cleaned or "item"


def _num(value: object, default: float = 0.0) -> float:
    if value is None:
        return default
    if isinstance(value, bool):
        return float(int(value))
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value))
    except ValueError:
        return default


def _int(value: object, default: int = 0) -> int:
    return int(_num(value, float(default)))


def _safe_ratio(part: float, whole: float) -> float:
    return part / whole if whole else 0.0


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _write_tsv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, delimiter="\t", extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _format_seconds_list(values: list[object]) -> str:
    return ",".join(f"{_num(value):.6f}" for value in values)


def _format_int_list(values: list[object]) -> str:
    return ",".join(str(_int(value)) for value in values)


def _records_bases(records: list[runner.FastaRecord]) -> int:
    return sum(len(record.sequence) for record in records)


def _worker_wall(report: dict[str, object]) -> float:
    per_worker = report.get("per_worker")
    if not isinstance(per_worker, list):
        return 0.0
    return max((_num(worker.get("wall_seconds")) for worker in per_worker if isinstance(worker, dict)), default=0.0)


def _worker_sum(report: dict[str, object]) -> float:
    per_worker = report.get("per_worker")
    if not isinstance(per_worker, list):
        return 0.0
    return sum(_num(worker.get("wall_seconds")) for worker in per_worker if isinstance(worker, dict))


def _imbalance_ratio(per_worker_seconds: list[object]) -> float:
    active = [_num(value) for value in per_worker_seconds if _num(value) > 0.0]
    if not active:
        return 0.0
    return max(active) / (sum(active) / len(active))


def _aggregate_telemetry(report: dict[str, object]) -> dict[str, object]:
    telemetry = report.get("sharded_telemetry")
    if isinstance(telemetry, dict):
        return telemetry
    per_worker = report.get("per_worker")
    if not isinstance(per_worker, list):
        return {}
    return runner._sum_fasim_telemetry(
        [
            worker.get("telemetry")
            for worker in per_worker
            if isinstance(worker, dict) and isinstance(worker.get("telemetry"), dict)
        ]
    )


def row_from_runner_report(
    *,
    report_path: Path,
    workload_name: str,
    target_bases: int,
    group_target_records: int | None,
    worker_count: int,
    baseline_by_worker: dict[int, dict[str, object]],
    runner_total_seconds: float,
    resume_status: str,
) -> dict[str, object]:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    telemetry = _aggregate_telemetry(report)
    per_worker = report.get("per_worker")
    per_worker_seconds = (
        [worker.get("wall_seconds") for worker in per_worker if isinstance(worker, dict)]
        if isinstance(per_worker, list)
        else []
    )
    per_worker_shards = (
        [len(worker.get("shard_ids", [])) for worker in per_worker if isinstance(worker, dict)]
        if isinstance(per_worker, list)
        else []
    )
    per_shard = report.get("per_shard")
    per_shard_records = (
        [shard.get("records") for shard in per_shard if isinstance(shard, dict)]
        if isinstance(per_shard, list)
        else []
    )
    per_shard_seconds = (
        [
            shard.get("run", {}).get("wall_seconds")
            for shard in per_shard
            if isinstance(shard, dict)
        ]
        if isinstance(per_shard, list)
        else []
    )
    wall_seconds = _worker_wall(report)
    fallback_value = _int(telemetry.get("fasim_prealign_cuda_fallbacks"))
    baseline = baseline_by_worker.get(worker_count, {})
    baseline_wall = _num(baseline.get("wall_seconds"))
    baseline_fallbacks = _int(baseline.get("fallbacks"))
    profile_calls = _int(telemetry.get("fasim_align_profile_cache_calls"))
    profile_hits = _int(telemetry.get("fasim_align_profile_cache_hits"))

    return {
        "workload": workload_name,
        "target_record_count": _int(report.get("target_record_count")),
        "target_bases": target_bases,
        "group_label": group_label(group_target_records),
        "group_target_records": group_target_records,
        "grouped_shard_count": _int(report.get("grouped_shard_count")),
        "worker_count": worker_count,
        "wall_seconds": wall_seconds,
        "runner_total_seconds": runner_total_seconds,
        "speedup_vs_default_grouping": _safe_ratio(baseline_wall, wall_seconds),
        "digest_match": int(bool(report.get("single_vs_sharded_digest_match"))),
        "merged_records": _int(report.get("merged_records")),
        "duplicate_removed": _int(report.get("duplicate_records_removed")),
        "prealign_cuda_fallbacks": fallback_value,
        "prealign_cuda_fallback_delta_vs_default": fallback_value - baseline_fallbacks,
        "prealign_cuda_tasks": _int(telemetry.get("fasim_prealign_cuda_tasks")),
        "prealign_cuda_batches": _int(telemetry.get("fasim_prealign_cuda_batches")),
        "profile_cache_active": _int(telemetry.get("fasim_align_profile_cache_active")),
        "profile_cache_calls": profile_calls,
        "profile_cache_hits": profile_hits,
        "profile_cache_misses": _int(telemetry.get("fasim_align_profile_cache_misses")),
        "profile_cache_hit_rate": _safe_ratio(float(profile_hits), float(profile_calls)),
        "extend_seconds": _num(telemetry.get("fasim_extend_seconds")),
        "output_seconds": _num(telemetry.get("fasim_output_seconds")),
        "imbalance_ratio": _imbalance_ratio(per_worker_seconds),
        "per_worker_seconds": per_worker_seconds,
        "per_worker_shards": per_worker_shards,
        "per_shard_records": per_shard_records,
        "per_shard_seconds": per_shard_seconds,
        "manifest_resume_status": resume_status,
        "report_path": str(report_path),
    }


def _tsv_row(row: dict[str, object]) -> dict[str, object]:
    converted = dict(row)
    converted["per_worker_seconds"] = _format_seconds_list(
        list(converted.get("per_worker_seconds", []))
    )
    converted["per_worker_shards"] = _format_int_list(
        list(converted.get("per_worker_shards", []))
    )
    converted["per_shard_records"] = _format_int_list(
        list(converted.get("per_shard_records", []))
    )
    converted["per_shard_seconds"] = _format_seconds_list(
        list(converted.get("per_shard_seconds", []))
    )
    return converted


def _default_env(args: argparse.Namespace) -> list[str]:
    env = [
        "FASIM_ENABLE_PREALIGN_CUDA=1",
        f"FASIM_EXTEND_THREADS={args.extend_threads}",
        "FASIM_ALIGN_PROFILE_CACHE=1",
        "FASIM_VERBOSE=0",
    ]
    env.extend(args.env)
    return env


def _run_runner(
    *,
    workload: dict[str, object],
    args: argparse.Namespace,
    group_target_records: int | None,
    worker_count: int,
    gpu_ids: list[str],
    explicit_cpu_core_ranges: list[str],
    env_overrides: list[str],
    run_dir: Path,
    resume: bool,
) -> tuple[dict[str, object], float, Path]:
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "fasim_sharded_runner.py"),
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
        "--validate-single",
        "--manifest",
        str(run_dir / "run_manifest.json"),
        "--workers",
        str(worker_count),
    ]
    if resume:
        cmd.append("--resume")
    if group_target_records is not None:
        cmd.extend(["--group-target-records", str(group_target_records)])
    if gpu_ids:
        cmd.extend(["--gpu-ids", ",".join(gpu_ids)])
    if explicit_cpu_core_ranges:
        if len(explicit_cpu_core_ranges) < worker_count:
            raise RuntimeError(
                "--cpu-core-ranges must include at least as many ranges as the largest worker count"
            )
        cmd.extend(["--cpu-core-ranges", ",".join(explicit_cpu_core_ranges[:worker_count])])
    if args.auto_cpu_core_ranges:
        cmd.append("--auto-cpu-core-ranges")
        if args.cpu_pool:
            cmd.extend(["--cpu-pool", args.cpu_pool])
        if args.cpu_cores_per_worker is not None:
            cmd.extend(["--cpu-cores-per-worker", str(args.cpu_cores_per_worker)])
    for item in env_overrides:
        cmd.extend(["--env", item])
    for item in args.fasim_arg:
        cmd.extend(["--fasim-arg", item])

    label = f"{group_label(group_target_records)}_workers_{worker_count}"
    if resume:
        label += "_resume"
    stdout_path = run_dir.parent / "logs" / f"{label}.stdout.log"
    stderr_path = run_dir.parent / "logs" / f"{label}.stderr.log"
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
            f"{label} failed with exit {proc.returncode}; see {stderr_path}"
        )
    report_path = run_dir / "report.json"
    if not report_path.exists():
        raise RuntimeError(f"missing runner report: {report_path}")
    return json.loads(report_path.read_text(encoding="utf-8")), t1 - t0, report_path


def _characterize_workload(
    *,
    workload: dict[str, object],
    args: argparse.Namespace,
    group_values: list[int | None],
    worker_counts: list[int],
    gpu_ids: list[str],
    explicit_cpu_core_ranges: list[str],
    env_overrides: list[str],
    work_dir: Path,
) -> dict[str, object]:
    workload_name = str(workload["name"])
    workload_dir = work_dir / _sanitize_name(workload_name)
    records = runner._read_fasta(Path(str(workload["target"])))
    target_record_count = len(records)
    target_bases = _records_bases(records)
    rows: list[dict[str, object]] = []
    run_reports: list[dict[str, object]] = []
    baseline_by_worker: dict[int, dict[str, object]] = {}

    for group_value in group_values:
        for worker_count in worker_counts:
            run_dir = (
                workload_dir
                / f"group_{group_label(group_value)}"
                / f"workers_{worker_count}"
            )
            if run_dir.exists():
                shutil.rmtree(run_dir)
            report, runner_total_seconds, report_path = _run_runner(
                workload=workload,
                args=args,
                group_target_records=group_value,
                worker_count=worker_count,
                gpu_ids=gpu_ids,
                explicit_cpu_core_ranges=explicit_cpu_core_ranges,
                env_overrides=env_overrides,
                run_dir=run_dir,
                resume=False,
            )
            performance_report_path = report_path
            resume_status = "fresh_manifest"
            if args.resume_smoke and group_value is not None and worker_count == min(worker_counts):
                performance_report_path = run_dir / "report.fresh.json"
                _write_json(performance_report_path, report)
                resume_report, _, _ = _run_runner(
                    workload=workload,
                    args=args,
                    group_target_records=group_value,
                    worker_count=worker_count,
                    gpu_ids=gpu_ids,
                    explicit_cpu_core_ranges=explicit_cpu_core_ranges,
                    env_overrides=env_overrides,
                    run_dir=run_dir,
                    resume=True,
                )
                resumed = resume_report.get("resumed_shards")
                expected = resume_report.get("shard_ids")
                resume_status = (
                    "same_config_resume_reused"
                    if isinstance(resumed, list) and resumed == expected
                    else "same_config_resume_not_reused"
                )

            telemetry = _aggregate_telemetry(report)
            if group_value is None:
                baseline_by_worker[worker_count] = {
                    "wall_seconds": _worker_wall(report),
                    "fallbacks": _int(telemetry.get("fasim_prealign_cuda_fallbacks")),
                }
            row = row_from_runner_report(
                report_path=performance_report_path,
                workload_name=workload_name,
                target_bases=target_bases,
                group_target_records=group_value,
                worker_count=worker_count,
                baseline_by_worker=baseline_by_worker,
                runner_total_seconds=runner_total_seconds,
                resume_status=resume_status,
            )
            rows.append(row)
            run_reports.append(
                {
                    "group_target_records": group_value,
                    "worker_count": worker_count,
                    "resume_status": resume_status,
                    "report_path": str(performance_report_path),
                    "report": report,
                }
            )

    return {
        "name": workload_name,
        "target": workload["target"],
        "rna": workload["rna"],
        "rule": workload["rule"],
        "target_record_count": target_record_count,
        "target_bases": target_bases,
        "runs": run_reports,
        "rows": rows,
        "all_digest_match": all(bool(row["digest_match"]) for row in rows),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Characterize the real --group-target-records Fasim sharded-runner "
            "option on tiny-region workloads."
        )
    )
    parser.add_argument(
        "--workload",
        action="append",
        required=True,
        metavar="NAME:TARGET_FASTA:RNA_FASTA:RULE",
    )
    parser.add_argument("--fasim-bin", required=True, type=Path)
    parser.add_argument("--work-dir", required=True, type=Path)
    parser.add_argument("--output-mode", choices=("lite", "tfosorted"), default="lite")
    parser.add_argument("--group-target-records", default="none,8,16,32")
    parser.add_argument("--workers", default="1,2,4")
    parser.add_argument("--gpu-ids", default=None)
    parser.add_argument("--cpu-core-ranges", default=None)
    parser.add_argument("--cpu-pool", default=None)
    parser.add_argument("--cpu-cores-per-worker", type=int, default=None)
    parser.add_argument("--auto-cpu-core-ranges", action="store_true")
    parser.add_argument("--extend-threads", type=int, default=6)
    parser.add_argument("--resume-smoke", action="store_true")
    parser.add_argument("--env", action="append", default=[], metavar="KEY=VALUE")
    parser.add_argument("--fasim-arg", action="append", default=[])
    args = parser.parse_args()

    args.fasim_bin = args.fasim_bin.resolve()
    if not args.fasim_bin.exists():
        raise RuntimeError(f"missing Fasim binary: {args.fasim_bin}")
    workloads = [_parse_workload(spec) for spec in args.workload]
    group_values = parse_group_values(args.group_target_records)
    worker_counts = _parse_csv_ints(args.workers, flag="--workers")
    gpu_ids = _parse_csv(args.gpu_ids, flag="--gpu-ids")
    explicit_cpu_core_ranges = _parse_csv(args.cpu_core_ranges, flag="--cpu-core-ranges")
    if explicit_cpu_core_ranges and len(explicit_cpu_core_ranges) < max(worker_counts):
        raise RuntimeError(
            "--cpu-core-ranges must include at least as many ranges as the largest worker count"
        )
    if args.auto_cpu_core_ranges and not args.cpu_pool:
        raise RuntimeError("--auto-cpu-core-ranges requires --cpu-pool")
    if args.auto_cpu_core_ranges and args.cpu_cores_per_worker is None:
        raise RuntimeError("--auto-cpu-core-ranges requires --cpu-cores-per-worker")

    env_overrides = _default_env(args)
    work_dir = args.work_dir.resolve()
    if work_dir.exists():
        shutil.rmtree(work_dir)
    work_dir.mkdir(parents=True)

    workload_reports = []
    rows: list[dict[str, object]] = []
    for workload in workloads:
        report = _characterize_workload(
            workload=workload,
            args=args,
            group_values=group_values,
            worker_counts=worker_counts,
            gpu_ids=gpu_ids,
            explicit_cpu_core_ranges=explicit_cpu_core_ranges,
            env_overrides=env_overrides,
            work_dir=work_dir,
        )
        workload_reports.append(report)
        rows.extend(report["rows"])

    output = {
        "schema_version": 1,
        "mode": "fasim_group_target_records_option_characterization",
        "output_mode": args.output_mode,
        "group_target_records": [group_label(value) for value in group_values],
        "worker_counts": worker_counts,
        "gpu_ids": gpu_ids,
        "cpu_core_ranges": explicit_cpu_core_ranges,
        "cpu_pool": args.cpu_pool,
        "cpu_cores_per_worker": args.cpu_cores_per_worker,
        "auto_cpu_core_ranges": bool(args.auto_cpu_core_ranges),
        "env_overrides": env_overrides,
        "resume_smoke": bool(args.resume_smoke),
        "workloads": workload_reports,
        "rows": rows,
        "summary": {
            "workloads": len(workload_reports),
            "rows": len(rows),
            "all_digest_match": all(bool(row["digest_match"]) for row in rows),
        },
    }
    _write_json(work_dir / "report.json", output)
    _write_tsv(work_dir / "raw.tsv", [_tsv_row(row) for row in rows], RAW_FIELDS)
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
