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

FALLBACK_REASONS = [
    "unsupported_rule",
    "unsupported_sequence_alphabet",
    "too_few_tasks",
    "too_many_tasks",
    "target_too_short",
    "query_too_long_or_unsupported",
    "cuda_allocation_or_launch",
    "empty_candidate_set",
    "unknown",
]

RAW_FIELDS = [
    "workload",
    "target_record_count",
    "target_bases",
    "group_label",
    "group_target_records",
    "grouped_shard_count",
    "worker_count",
    "topk_candidate",
    "max_tasks_candidate",
    "wall_seconds",
    "runner_total_seconds",
    "digest_match",
    "digest_match_vs_baseline",
    "merged_digest",
    "baseline_digest",
    "merged_records",
    "duplicate_removed",
    "prealign_cuda_requested",
    "prealign_cuda_active",
    "prealign_cuda_fallbacks",
    "fallback_reason_total",
    "fallback_reason_top",
    "fallback_reason_top_count",
    "prealign_cuda_tasks",
    "prealign_cuda_batches",
    "effective_topk",
    "effective_max_tasks",
    "suppress_bp",
    "dynamic_smem_required",
    "dynamic_smem_limit",
    "shared_mem_default_limit",
    "shared_mem_optin_limit",
    "device_shared_mem_limit",
    "block_dim",
    "resource_fit_supported",
    "smem_optin_possible",
    "smem_optin_requested",
    "smem_optin_active",
    "smem_optin_fallback_reason",
    "prealign_cuda_total_seconds",
    "prealign_cuda_kernel_seconds",
    "profile_cache_hit_rate",
    "report_path",
] + [f"fallback_{reason}" for reason in FALLBACK_REASONS]


def _parse_csv(spec: str | None, *, flag: str) -> list[str]:
    if spec is None or not spec.strip():
        return []
    values = [item.strip() for item in spec.split(",")]
    if any(not value for value in values):
        raise RuntimeError(f"{flag} must not include empty entries")
    return values


def parse_ordered_csv_ints(spec: str, *, flag: str) -> list[int]:
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
    deduped: list[int] = []
    seen: set[int] = set()
    for value in values:
        if value in seen:
            continue
        deduped.append(value)
        seen.add(value)
    return deduped


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
    deduped: list[int | None] = []
    seen: set[int | None] = set()
    for value in values:
        if value in seen:
            continue
        deduped.append(value)
        seen.add(value)
    if None in deduped and deduped[0] is not None:
        deduped = [None] + [value for value in deduped if value is not None]
    return deduped


def _parse_csv_ints(spec: str, *, flag: str) -> list[int]:
    return sorted(parse_ordered_csv_ints(spec, flag=flag))


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


def _records_bases(records: list[runner.FastaRecord]) -> int:
    return sum(len(record.sequence) for record in records)


def _worker_wall(report: dict[str, object]) -> float:
    per_worker = report.get("per_worker")
    if not isinstance(per_worker, list):
        return 0.0
    return max(
        (_num(worker.get("wall_seconds")) for worker in per_worker if isinstance(worker, dict)),
        default=0.0,
    )


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


def _reason_counts(telemetry: dict[str, object]) -> dict[str, int]:
    return {
        reason: _int(telemetry.get(f"fasim_prealign_cuda_fallback_{reason}"))
        for reason in FALLBACK_REASONS
    }


def _top_reason(counts: dict[str, int]) -> tuple[str, int]:
    top_reason = "none"
    top_count = 0
    for reason in FALLBACK_REASONS:
        count = counts.get(reason, 0)
        if count > top_count:
            top_reason = reason
            top_count = count
    return top_reason, top_count


def row_from_runner_report(
    *,
    report_path: Path,
    workload_name: str,
    target_bases: int,
    group_target_records: int | None,
    worker_count: int,
    topk_candidate: int,
    max_tasks_candidate: int,
    runner_total_seconds: float,
    baseline_digest: str | None,
) -> dict[str, object]:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    telemetry = _aggregate_telemetry(report)
    counts = _reason_counts(telemetry)
    reason_total = sum(counts.values())
    top_reason, top_count = _top_reason(counts)
    profile_calls = _int(telemetry.get("fasim_align_profile_cache_calls"))
    profile_hits = _int(telemetry.get("fasim_align_profile_cache_hits"))
    merged_digest = report.get("merged_digest")
    digest_match_vs_baseline = (
        baseline_digest is not None and merged_digest == baseline_digest
    )

    row = {
        "workload": workload_name,
        "target_record_count": _int(report.get("target_record_count")),
        "target_bases": target_bases,
        "group_label": group_label(group_target_records),
        "group_target_records": group_target_records,
        "grouped_shard_count": _int(report.get("grouped_shard_count")),
        "worker_count": worker_count,
        "topk_candidate": topk_candidate,
        "max_tasks_candidate": max_tasks_candidate,
        "wall_seconds": _worker_wall(report),
        "runner_total_seconds": runner_total_seconds,
        "digest_match": int(bool(report.get("single_vs_sharded_digest_match"))),
        "digest_match_vs_baseline": int(digest_match_vs_baseline),
        "merged_digest": merged_digest,
        "baseline_digest": baseline_digest,
        "merged_records": _int(report.get("merged_records")),
        "duplicate_removed": _int(report.get("duplicate_records_removed")),
        "prealign_cuda_requested": _int(telemetry.get("fasim_prealign_cuda_requested")),
        "prealign_cuda_active": _int(telemetry.get("fasim_prealign_cuda_active")),
        "prealign_cuda_fallbacks": _int(telemetry.get("fasim_prealign_cuda_fallbacks")),
        "fallback_reason_total": reason_total,
        "fallback_reason_top": top_reason,
        "fallback_reason_top_count": top_count,
        "prealign_cuda_tasks": _int(telemetry.get("fasim_prealign_cuda_tasks")),
        "prealign_cuda_batches": _int(telemetry.get("fasim_prealign_cuda_batches")),
        "effective_topk": _int(telemetry.get("fasim_prealign_cuda_topk")),
        "effective_max_tasks": _int(telemetry.get("fasim_prealign_cuda_max_tasks")),
        "suppress_bp": _int(telemetry.get("fasim_prealign_cuda_peak_suppress_bp")),
        "dynamic_smem_required": _int(
            telemetry.get("fasim_prealign_cuda_dynamic_smem_required")
        ),
        "dynamic_smem_limit": _int(
            telemetry.get("fasim_prealign_cuda_dynamic_smem_limit")
        ),
        "shared_mem_default_limit": _int(
            telemetry.get("fasim_prealign_cuda_shared_mem_default_limit")
        ),
        "shared_mem_optin_limit": _int(
            telemetry.get("fasim_prealign_cuda_shared_mem_optin_limit")
        ),
        "device_shared_mem_limit": _int(
            telemetry.get("fasim_prealign_cuda_device_shared_mem_limit")
        ),
        "block_dim": _int(telemetry.get("fasim_prealign_cuda_block_dim")),
        "resource_fit_supported": _int(
            telemetry.get("fasim_prealign_cuda_resource_fit_supported")
        ),
        "smem_optin_possible": _int(
            telemetry.get("fasim_prealign_cuda_smem_optin_possible")
        ),
        "smem_optin_requested": _int(
            telemetry.get("fasim_prealign_cuda_smem_optin_requested")
        ),
        "smem_optin_active": _int(
            telemetry.get("fasim_prealign_cuda_smem_optin_active")
        ),
        "smem_optin_fallback_reason": telemetry.get(
            "fasim_prealign_cuda_smem_optin_fallback_reason",
            "none",
        ),
        "prealign_cuda_total_seconds": _num(
            telemetry.get("fasim_prealign_cuda_total_seconds")
        ),
        "prealign_cuda_kernel_seconds": _num(
            telemetry.get("fasim_prealign_cuda_kernel_seconds")
        ),
        "profile_cache_hit_rate": _safe_ratio(float(profile_hits), float(profile_calls)),
        "report_path": str(report_path),
    }
    for reason in FALLBACK_REASONS:
        row[f"fallback_{reason}"] = counts[reason]
    return row


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
    topk_candidate: int,
    max_tasks_candidate: int,
    run_dir: Path,
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
    run_env_overrides = list(env_overrides)
    run_env_overrides.extend(
        [
            f"FASIM_PREALIGN_CUDA_TOPK={topk_candidate}",
            f"FASIM_PREALIGN_CUDA_MAX_TASKS={max_tasks_candidate}",
        ]
    )
    for item in run_env_overrides:
        cmd.extend(["--env", item])
    for item in args.fasim_arg:
        cmd.extend(["--fasim-arg", item])

    label = (
        f"{group_label(group_target_records)}_workers_{worker_count}"
        f"_topk_{topk_candidate}_max_tasks_{max_tasks_candidate}"
    )
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
    topk_values: list[int],
    max_tasks_values: list[int],
    gpu_ids: list[str],
    explicit_cpu_core_ranges: list[str],
    env_overrides: list[str],
    work_dir: Path,
) -> dict[str, object]:
    workload_name = str(workload["name"])
    workload_dir = work_dir / _sanitize_name(workload_name)
    records = runner._read_fasta(Path(str(workload["target"])))
    target_bases = _records_bases(records)
    rows: list[dict[str, object]] = []
    run_reports: list[dict[str, object]] = []

    baseline_digest_by_shape: dict[tuple[int | None, int], str | None] = {}
    baseline_topk = topk_values[0]
    baseline_max_tasks = max_tasks_values[0]

    for group_value in group_values:
        for worker_count in worker_counts:
            for topk_candidate in topk_values:
                for max_tasks_candidate in max_tasks_values:
                    shape_key = (group_value, worker_count)
                    run_dir = (
                        workload_dir
                        / f"group_{group_label(group_value)}"
                        / f"workers_{worker_count}"
                        / f"topk_{topk_candidate}_max_tasks_{max_tasks_candidate}"
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
                        topk_candidate=topk_candidate,
                        max_tasks_candidate=max_tasks_candidate,
                        run_dir=run_dir,
                    )
                    if (
                        topk_candidate == baseline_topk
                        and max_tasks_candidate == baseline_max_tasks
                    ):
                        baseline_digest_by_shape[shape_key] = report.get("merged_digest")
                    baseline_digest = baseline_digest_by_shape.get(shape_key)
                    row = row_from_runner_report(
                        report_path=report_path,
                        workload_name=workload_name,
                        target_bases=target_bases,
                        group_target_records=group_value,
                        worker_count=worker_count,
                        topk_candidate=topk_candidate,
                        max_tasks_candidate=max_tasks_candidate,
                        runner_total_seconds=runner_total_seconds,
                        baseline_digest=baseline_digest,
                    )
                    rows.append(row)
                    run_reports.append(
                        {
                            "group_target_records": group_value,
                            "worker_count": worker_count,
                            "topk_candidate": topk_candidate,
                            "max_tasks_candidate": max_tasks_candidate,
                            "report_path": str(report_path),
                            "report": report,
                        }
                    )

    return {
        "name": workload_name,
        "target": workload["target"],
        "rna": workload["rna"],
        "rule": workload["rule"],
        "target_record_count": len(records),
        "target_bases": target_bases,
        "runs": run_reports,
        "rows": rows,
        "all_digest_match": all(bool(row["digest_match"]) for row in rows),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Characterize preAlign CUDA resource-fit launch telemetry."
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
    parser.add_argument("--topk-values", default="64,32,16")
    parser.add_argument("--max-tasks-values", default="4096")
    parser.add_argument("--gpu-ids", default=None)
    parser.add_argument("--cpu-core-ranges", default=None)
    parser.add_argument("--cpu-pool", default=None)
    parser.add_argument("--cpu-cores-per-worker", type=int, default=None)
    parser.add_argument("--auto-cpu-core-ranges", action="store_true")
    parser.add_argument("--extend-threads", type=int, default=6)
    parser.add_argument("--env", action="append", default=[], metavar="KEY=VALUE")
    parser.add_argument("--fasim-arg", action="append", default=[])
    args = parser.parse_args()

    args.fasim_bin = args.fasim_bin.resolve()
    if not args.fasim_bin.exists():
        raise RuntimeError(f"missing Fasim binary: {args.fasim_bin}")
    workloads = [_parse_workload(spec) for spec in args.workload]
    group_values = parse_group_values(args.group_target_records)
    worker_counts = _parse_csv_ints(args.workers, flag="--workers")
    topk_values = parse_ordered_csv_ints(args.topk_values, flag="--topk-values")
    max_tasks_values = parse_ordered_csv_ints(
        args.max_tasks_values, flag="--max-tasks-values"
    )
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
            topk_values=topk_values,
            max_tasks_values=max_tasks_values,
            gpu_ids=gpu_ids,
            explicit_cpu_core_ranges=explicit_cpu_core_ranges,
            env_overrides=env_overrides,
            work_dir=work_dir,
        )
        workload_reports.append(report)
        rows.extend(report["rows"])

    output = {
        "schema_version": 1,
        "mode": "fasim_prealign_cuda_resource_fit",
        "output_mode": args.output_mode,
        "fallback_reasons": FALLBACK_REASONS,
        "group_target_records": [group_label(value) for value in group_values],
        "worker_counts": worker_counts,
        "topk_values": topk_values,
        "max_tasks_values": max_tasks_values,
        "gpu_ids": gpu_ids,
        "cpu_core_ranges": explicit_cpu_core_ranges,
        "cpu_pool": args.cpu_pool,
        "cpu_cores_per_worker": args.cpu_cores_per_worker,
        "auto_cpu_core_ranges": bool(args.auto_cpu_core_ranges),
        "env_overrides": env_overrides,
        "workloads": workload_reports,
        "rows": rows,
        "summary": {
            "workloads": len(workload_reports),
            "rows": len(rows),
            "all_digest_match": all(bool(row["digest_match"]) for row in rows),
            "fallback_reason_total": sum(int(row["fallback_reason_total"]) for row in rows),
        },
    }
    _write_json(work_dir / "report.json", output)
    _write_tsv(work_dir / "raw.tsv", rows, RAW_FIELDS)
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
