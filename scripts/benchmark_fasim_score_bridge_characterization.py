#!/usr/bin/env python3
import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


ROOT = _repo_root()


RAW_FIELDS = [
    "workload",
    "workers",
    "max_requests",
    "wall_seconds",
    "runner_total_seconds",
    "single_seconds",
    "digest_match",
    "records",
    "prealign_cuda_total_seconds",
    "prealign_cuda_fallbacks",
    "extend_seconds",
    "extend_align_seconds",
    "align_forward_score_end_seconds",
    "bridge_shadow_enabled",
    "bridge_requests",
    "bridge_cells",
    "bridge_groups",
    "bridge_descriptor_count",
    "bridge_descriptor_bytes",
    "bridge_query_buffer_bytes",
    "bridge_target_buffer_bytes",
    "bridge_cpu_reference_seconds",
    "bridge_pack_seconds",
    "bridge_h2d_seconds",
    "bridge_kernel_seconds",
    "bridge_d2h_seconds",
    "bridge_unpack_seconds",
    "bridge_total_seconds",
    "bridge_processed_requests",
    "bridge_processed_fraction",
    "bridge_total_vs_observed_cpu_reference",
    "bridge_processed_cpu_reference_est_seconds",
    "bridge_total_vs_processed_cpu_reference_est",
    "bridge_descriptor_bytes_per_request",
    "bridge_target_bytes_per_request",
    "bridge_query_bytes_per_group",
    "bridge_score_mismatches",
    "bridge_endpoint_mismatches",
    "bridge_unsupported_requests",
    "report_path",
]


SUMMARY_FIELDS = RAW_FIELDS


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


def _max_worker_wall(report: dict[str, object]) -> float:
    per_worker = report.get("per_worker")
    if not isinstance(per_worker, list) or not per_worker:
        raise RuntimeError("report has no per_worker timing")
    return max(
        _num(worker.get("wall_seconds"))
        for worker in per_worker
        if isinstance(worker, dict)
    )


def row_from_report(
    *,
    report_path: Path,
    workload: str,
    workers: int,
    max_requests: int,
    runner_total_seconds: float,
) -> dict[str, object]:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    telemetry = report.get("sharded_telemetry", {})
    if not isinstance(telemetry, dict):
        telemetry = {}
    single_run = report.get("single_run")
    single_seconds = (
        _num(single_run.get("wall_seconds"))
        if isinstance(single_run, dict)
        else 0.0
    )
    cpu_reference = _num(telemetry.get("fasim_score_bridge_cpu_reference_seconds"))
    bridge_total = _num(telemetry.get("fasim_score_bridge_total_seconds"))
    bridge_requests = _int(telemetry.get("fasim_score_bridge_requests"))
    unsupported = _int(telemetry.get("fasim_score_bridge_unsupported_requests"))
    processed_requests = max(0, bridge_requests - unsupported)
    processed_fraction = _safe_ratio(float(processed_requests), float(bridge_requests))
    processed_cpu_reference_est = cpu_reference * processed_fraction
    descriptor_bytes = _int(telemetry.get("fasim_score_bridge_descriptor_bytes"))
    descriptor_count = _int(telemetry.get("fasim_score_bridge_descriptor_count"))
    target_bytes = _int(telemetry.get("fasim_score_bridge_target_buffer_bytes"))
    query_bytes = _int(telemetry.get("fasim_score_bridge_query_buffer_bytes"))
    groups = _int(telemetry.get("fasim_score_bridge_groups"))

    return {
        "workload": workload,
        "workers": workers,
        "max_requests": max_requests,
        "wall_seconds": _max_worker_wall(report),
        "runner_total_seconds": runner_total_seconds,
        "single_seconds": single_seconds,
        "digest_match": int(bool(report.get("single_vs_sharded_digest_match"))),
        "records": _int(report.get("merged_records")),
        "prealign_cuda_total_seconds": _num(
            telemetry.get("fasim_prealign_cuda_total_seconds")
        ),
        "prealign_cuda_fallbacks": _int(
            telemetry.get("fasim_prealign_cuda_fallbacks")
        ),
        "extend_seconds": _num(telemetry.get("fasim_extend_seconds")),
        "extend_align_seconds": _num(telemetry.get("fasim_extend_align_seconds")),
        "align_forward_score_end_seconds": _num(
            telemetry.get("fasim_align_forward_score_end_seconds")
        ),
        "bridge_shadow_enabled": _int(
            telemetry.get("fasim_score_bridge_shadow_enabled")
        ),
        "bridge_requests": bridge_requests,
        "bridge_cells": _int(telemetry.get("fasim_score_bridge_cells")),
        "bridge_groups": groups,
        "bridge_descriptor_count": descriptor_count,
        "bridge_descriptor_bytes": descriptor_bytes,
        "bridge_query_buffer_bytes": query_bytes,
        "bridge_target_buffer_bytes": target_bytes,
        "bridge_cpu_reference_seconds": cpu_reference,
        "bridge_pack_seconds": _num(telemetry.get("fasim_score_bridge_pack_seconds")),
        "bridge_h2d_seconds": _num(telemetry.get("fasim_score_bridge_h2d_seconds")),
        "bridge_kernel_seconds": _num(
            telemetry.get("fasim_score_bridge_kernel_seconds")
        ),
        "bridge_d2h_seconds": _num(telemetry.get("fasim_score_bridge_d2h_seconds")),
        "bridge_unpack_seconds": _num(
            telemetry.get("fasim_score_bridge_unpack_seconds")
        ),
        "bridge_total_seconds": bridge_total,
        "bridge_processed_requests": processed_requests,
        "bridge_processed_fraction": processed_fraction,
        "bridge_total_vs_observed_cpu_reference": _safe_ratio(
            bridge_total,
            cpu_reference,
        ),
        "bridge_processed_cpu_reference_est_seconds": processed_cpu_reference_est,
        "bridge_total_vs_processed_cpu_reference_est": _safe_ratio(
            bridge_total,
            processed_cpu_reference_est,
        ),
        "bridge_descriptor_bytes_per_request": _safe_ratio(
            float(descriptor_bytes),
            float(descriptor_count),
        ),
        "bridge_target_bytes_per_request": _safe_ratio(
            float(target_bytes),
            float(processed_requests),
        ),
        "bridge_query_bytes_per_group": _safe_ratio(float(query_bytes), float(groups)),
        "bridge_score_mismatches": _int(
            telemetry.get("fasim_score_bridge_score_mismatches")
        ),
        "bridge_endpoint_mismatches": _int(
            telemetry.get("fasim_score_bridge_endpoint_mismatches")
        ),
        "bridge_unsupported_requests": unsupported,
        "report_path": str(report_path),
    }


def _write_tsv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, delimiter="\t", extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _run_one(
    *,
    workload: dict[str, object],
    workers: int,
    max_requests: int,
    args: argparse.Namespace,
    work_dir: Path,
) -> dict[str, object]:
    run_dir = (
        work_dir
        / "runs"
        / _sanitize_name(workload["name"])
        / f"workers_{workers}"
        / f"max_{max_requests}"
    )
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
        "--workers",
        str(workers),
        "--gpu-ids",
        args.gpu_ids,
        "--cpu-pool",
        args.cpu_pool,
        "--cpu-cores-per-worker",
        str(args.cpu_cores_per_worker),
        "--auto-cpu-core-ranges",
        "--manifest",
        str(run_dir / "run_manifest.json"),
        "--env",
        "FASIM_ENABLE_PREALIGN_CUDA=1",
        "--env",
        f"FASIM_EXTEND_THREADS={args.extend_threads}",
        "--env",
        "FASIM_ALIGN_PROFILE_CACHE=1",
        "--env",
        "FASIM_ALIGN_SCORE_BRIDGE_GPU_SHADOW=1",
        "--env",
        f"FASIM_ALIGN_SCORE_BRIDGE_GPU_SHADOW_MAX_REQUESTS={max_requests}",
    ]

    env = os.environ.copy()
    env.pop("FASIM_CUDA_DEVICES", None)
    stdout_path = run_dir / "runner.stdout.log"
    stderr_path = run_dir / "runner.stderr.log"
    stdout_path.parent.mkdir(parents=True, exist_ok=True)

    start = time.perf_counter()
    proc = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
        check=False,
    )
    runner_total_seconds = time.perf_counter() - start
    stdout_path.write_text(proc.stdout, encoding="utf-8")
    stderr_path.write_text(proc.stderr, encoding="utf-8")
    if proc.returncode != 0:
        raise RuntimeError(
            f"{workload['name']} workers={workers} max_requests={max_requests} "
            f"failed with exit {proc.returncode}; see {stderr_path}"
        )

    report_path = run_dir / "report.json"
    if not report_path.exists():
        raise RuntimeError(f"missing report: {report_path}")
    return row_from_report(
        report_path=report_path,
        workload=str(workload["name"]),
        workers=workers,
        max_requests=max_requests,
        runner_total_seconds=runner_total_seconds,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Characterize current-base score-only GPU bridge shadow.",
    )
    parser.add_argument("--fasim-bin", required=True, type=Path)
    parser.add_argument("--work-dir", required=True, type=Path)
    parser.add_argument(
        "--workload",
        action="append",
        required=True,
        metavar="NAME:TARGET_FASTA:RNA_FASTA:RULE",
        help="workload to characterize; repeatable",
    )
    parser.add_argument("--workers", default="4,6")
    parser.add_argument("--max-requests", default="1000,10000,50000,100000")
    parser.add_argument("--gpu-ids", default="0,1")
    parser.add_argument("--cpu-pool", default="0-19")
    parser.add_argument("--cpu-cores-per-worker", type=int, default=3)
    parser.add_argument("--extend-threads", type=int, default=6)
    parser.add_argument("--output-mode", choices=("lite", "tfosorted"), default="lite")
    parser.add_argument(
        "--force",
        action="store_true",
        help="remove --work-dir before running",
    )
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    args.fasim_bin = args.fasim_bin.resolve()
    work_dir = args.work_dir.resolve()
    if not args.fasim_bin.exists():
        raise RuntimeError(f"missing Fasim binary: {args.fasim_bin}")

    workloads = [_parse_workload(spec) for spec in args.workload]
    workers = _parse_csv_ints(args.workers, flag="--workers")
    max_requests_values = _parse_csv_ints(args.max_requests, flag="--max-requests")
    if work_dir.exists():
        if not args.force:
            raise RuntimeError(f"--work-dir exists, pass --force to replace: {work_dir}")
        shutil.rmtree(work_dir)
    work_dir.mkdir(parents=True)

    rows: list[dict[str, object]] = []
    for workload in workloads:
        for worker_count in workers:
            for max_requests in max_requests_values:
                row = _run_one(
                    workload=workload,
                    workers=worker_count,
                    max_requests=max_requests,
                    args=args,
                    work_dir=work_dir,
                )
                rows.append(row)
                _write_tsv(work_dir / "raw.tsv", rows, RAW_FIELDS)

    _write_tsv(work_dir / "summary.tsv", rows, SUMMARY_FIELDS)
    (work_dir / "summary.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "mode": "fasim_score_bridge_characterization",
                "active_env": {
                    "FASIM_ENABLE_PREALIGN_CUDA": "1",
                    "FASIM_EXTEND_THREADS": str(args.extend_threads),
                    "FASIM_ALIGN_PROFILE_CACHE": "1",
                    "FASIM_ALIGN_SCORE_BRIDGE_GPU_SHADOW": "1",
                },
                "workers": workers,
                "max_requests": max_requests_values,
                "workloads": workloads,
                "rows": rows,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"summary_path": str(work_dir / "summary.tsv")}, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
