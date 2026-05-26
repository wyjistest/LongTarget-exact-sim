#!/usr/bin/env python3
import argparse
import csv
import json
import shutil
import statistics
import subprocess
import sys
import time
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


ROOT = _repo_root()


MODES: dict[str, dict[str, str]] = {
    "baseline": {},
    "cache": {
        "FASIM_ALIGN_PROFILE_CACHE": "1",
    },
    "cache_validate": {
        "FASIM_ALIGN_PROFILE_CACHE": "1",
        "FASIM_ALIGN_PROFILE_CACHE_VALIDATE": "1",
    },
}


RAW_FIELDS = [
    "workload",
    "repeat",
    "workers",
    "mode",
    "wall_seconds",
    "runner_total_seconds",
    "single_seconds",
    "digest_match",
    "records",
    "profile_cache_active",
    "profile_cache_validate",
    "profile_cache_calls",
    "profile_cache_hits",
    "profile_cache_misses",
    "profile_cache_unique_keys",
    "profile_cache_hit_rate",
    "profile_cache_saved_seconds",
    "profile_cache_validate_seconds",
    "profile_cache_score_mismatches",
    "profile_cache_endpoint_mismatches",
    "profile_cache_cigar_mismatches",
    "profile_cache_digest_mismatches",
    "profile_cache_fallbacks",
    "prealign_cuda_fallbacks",
    "prealign_cuda_total_seconds",
    "extend_seconds",
    "align_profile_seconds",
    "align_ssw_total_seconds",
    "report_path",
]


SUMMARY_FIELDS = [
    "workload",
    "workers",
    "mode",
    "runs",
    "digest_clean_runs",
    "median_wall_seconds",
    "min_wall_seconds",
    "max_wall_seconds",
    "wall_delta_vs_baseline",
    "median_runner_total_seconds",
    "median_single_seconds",
    "records",
    "median_profile_cache_hit_rate",
    "median_profile_cache_hits",
    "median_profile_cache_misses",
    "median_profile_cache_unique_keys",
    "median_profile_cache_saved_seconds",
    "median_profile_cache_validate_seconds",
    "score_mismatches",
    "endpoint_mismatches",
    "cigar_mismatches",
    "digest_mismatches",
    "cache_fallbacks",
    "prealign_cuda_fallbacks",
]


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


def _median(values: list[float]) -> float:
    return float(statistics.median(values)) if values else 0.0


def _common_or_list(values: list[object]) -> object:
    if not values:
        return None
    first = values[0]
    if all(value == first for value in values):
        return first
    return sorted({str(value) for value in values})


def _max_worker_wall(report: dict[str, object]) -> float:
    per_worker = report.get("per_worker")
    if not isinstance(per_worker, list) or not per_worker:
        raise RuntimeError("report has no per_worker timing")
    return max(_num(worker.get("wall_seconds")) for worker in per_worker if isinstance(worker, dict))


def _run_one(
    *,
    workload: dict[str, object],
    workers: int,
    repeat: int,
    mode: str,
    mode_env: dict[str, str],
    args: argparse.Namespace,
    work_dir: Path,
) -> dict[str, object]:
    run_dir = (
        work_dir
        / "runs"
        / _sanitize_name(workload["name"])
        / f"workers_{workers}"
        / mode
        / f"repeat_{repeat}"
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
    ]

    worker_env = {
        "FASIM_ENABLE_PREALIGN_CUDA": "1",
        "FASIM_EXTEND_THREADS": str(args.extend_threads),
        **mode_env,
    }
    for key, value in worker_env.items():
        cmd.extend(["--env", f"{key}={value}"])

    env = os_environ_without_cuda_devices()
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
            f"{workload['name']} workers={workers} mode={mode} repeat={repeat} "
            f"failed with exit {proc.returncode}; see {stderr_path}"
        )

    report_path = run_dir / "report.json"
    if not report_path.exists():
        raise RuntimeError(f"missing report: {report_path}")
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
    calls = _int(telemetry.get("fasim_align_profile_cache_calls"))
    hits = _int(telemetry.get("fasim_align_profile_cache_hits"))
    hit_rate = float(hits) / float(calls) if calls else 0.0

    return {
        "workload": workload["name"],
        "repeat": repeat,
        "workers": workers,
        "mode": mode,
        "wall_seconds": _max_worker_wall(report),
        "runner_total_seconds": runner_total_seconds,
        "single_seconds": single_seconds,
        "digest_match": int(bool(report.get("single_vs_sharded_digest_match"))),
        "records": _int(report.get("merged_records")),
        "profile_cache_active": _int(telemetry.get("fasim_align_profile_cache_active")),
        "profile_cache_validate": _int(telemetry.get("fasim_align_profile_cache_validate")),
        "profile_cache_calls": calls,
        "profile_cache_hits": hits,
        "profile_cache_misses": _int(telemetry.get("fasim_align_profile_cache_misses")),
        "profile_cache_unique_keys": _int(telemetry.get("fasim_align_profile_cache_unique_keys")),
        "profile_cache_hit_rate": hit_rate,
        "profile_cache_saved_seconds": _num(telemetry.get("fasim_align_profile_cache_saved_seconds")),
        "profile_cache_validate_seconds": _num(telemetry.get("fasim_align_profile_cache_validate_seconds")),
        "profile_cache_score_mismatches": _int(telemetry.get("fasim_align_profile_cache_score_mismatches")),
        "profile_cache_endpoint_mismatches": _int(telemetry.get("fasim_align_profile_cache_endpoint_mismatches")),
        "profile_cache_cigar_mismatches": _int(telemetry.get("fasim_align_profile_cache_cigar_mismatches")),
        "profile_cache_digest_mismatches": _int(telemetry.get("fasim_align_profile_cache_digest_mismatches")),
        "profile_cache_fallbacks": _int(telemetry.get("fasim_align_profile_cache_fallbacks")),
        "prealign_cuda_fallbacks": _int(telemetry.get("fasim_prealign_cuda_fallbacks")),
        "prealign_cuda_total_seconds": _num(telemetry.get("fasim_prealign_cuda_total_seconds")),
        "extend_seconds": _num(telemetry.get("fasim_extend_seconds")),
        "align_profile_seconds": _num(telemetry.get("fasim_align_profile_seconds")),
        "align_ssw_total_seconds": _num(telemetry.get("fasim_align_ssw_total_seconds")),
        "report_path": str(report_path),
    }


def os_environ_without_cuda_devices() -> dict[str, str]:
    import os

    env = os.environ.copy()
    env.pop("FASIM_CUDA_DEVICES", None)
    return env


def _write_tsv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, delimiter="\t", extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _summarize(raw_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[tuple[object, object, object], list[dict[str, object]]] = {}
    for row in raw_rows:
        key = (row["workload"], row["workers"], row["mode"])
        grouped.setdefault(key, []).append(row)

    baseline_medians: dict[tuple[object, object], float] = {}
    for (workload, workers, mode), rows in grouped.items():
        if mode == "baseline":
            baseline_medians[(workload, workers)] = _median(
                [_num(row["wall_seconds"]) for row in rows]
            )

    summary_rows: list[dict[str, object]] = []
    for key in sorted(grouped, key=lambda item: (str(item[0]), int(item[1]), str(item[2]))):
        workload, workers, mode = key
        rows = grouped[key]
        wall_values = [_num(row["wall_seconds"]) for row in rows]
        median_wall = _median(wall_values)
        baseline_wall = baseline_medians.get((workload, workers), median_wall)
        mismatch_fields = [
            "profile_cache_score_mismatches",
            "profile_cache_endpoint_mismatches",
            "profile_cache_cigar_mismatches",
            "profile_cache_digest_mismatches",
            "profile_cache_fallbacks",
            "prealign_cuda_fallbacks",
        ]
        mismatch_sums = {
            field: sum(_int(row[field]) for row in rows)
            for field in mismatch_fields
        }
        summary_rows.append(
            {
                "workload": workload,
                "workers": workers,
                "mode": mode,
                "runs": len(rows),
                "digest_clean_runs": sum(_int(row["digest_match"]) for row in rows),
                "median_wall_seconds": median_wall,
                "min_wall_seconds": min(wall_values) if wall_values else 0.0,
                "max_wall_seconds": max(wall_values) if wall_values else 0.0,
                "wall_delta_vs_baseline": (
                    (median_wall / baseline_wall) - 1.0 if baseline_wall else 0.0
                ),
                "median_runner_total_seconds": _median(
                    [_num(row["runner_total_seconds"]) for row in rows]
                ),
                "median_single_seconds": _median(
                    [_num(row["single_seconds"]) for row in rows]
                ),
                "records": _common_or_list([row["records"] for row in rows]),
                "median_profile_cache_hit_rate": _median(
                    [_num(row["profile_cache_hit_rate"]) for row in rows]
                ),
                "median_profile_cache_hits": _median(
                    [_num(row["profile_cache_hits"]) for row in rows]
                ),
                "median_profile_cache_misses": _median(
                    [_num(row["profile_cache_misses"]) for row in rows]
                ),
                "median_profile_cache_unique_keys": _median(
                    [_num(row["profile_cache_unique_keys"]) for row in rows]
                ),
                "median_profile_cache_saved_seconds": _median(
                    [_num(row["profile_cache_saved_seconds"]) for row in rows]
                ),
                "median_profile_cache_validate_seconds": _median(
                    [_num(row["profile_cache_validate_seconds"]) for row in rows]
                ),
                "score_mismatches": mismatch_sums["profile_cache_score_mismatches"],
                "endpoint_mismatches": mismatch_sums["profile_cache_endpoint_mismatches"],
                "cigar_mismatches": mismatch_sums["profile_cache_cigar_mismatches"],
                "digest_mismatches": mismatch_sums["profile_cache_digest_mismatches"],
                "cache_fallbacks": mismatch_sums["profile_cache_fallbacks"],
                "prealign_cuda_fallbacks": mismatch_sums["prealign_cuda_fallbacks"],
            }
        )
    return summary_rows


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Repeat current-base align profile cache A/B sharded runs.",
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
    parser.add_argument("--repeats", type=int, default=3)
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
    if args.repeats < 1:
        raise RuntimeError("--repeats must be >= 1")

    workloads = [_parse_workload(spec) for spec in args.workload]
    workers = _parse_csv_ints(args.workers, flag="--workers")
    if work_dir.exists():
        if not args.force:
            raise RuntimeError(f"--work-dir exists, pass --force to replace: {work_dir}")
        shutil.rmtree(work_dir)
    work_dir.mkdir(parents=True)

    raw_rows: list[dict[str, object]] = []
    for repeat in range(1, args.repeats + 1):
        for workload in workloads:
            for worker_count in workers:
                for mode, mode_env in MODES.items():
                    row = _run_one(
                        workload=workload,
                        workers=worker_count,
                        repeat=repeat,
                        mode=mode,
                        mode_env=mode_env,
                        args=args,
                        work_dir=work_dir,
                    )
                    raw_rows.append(row)
                    _write_tsv(work_dir / "raw.tsv", raw_rows, RAW_FIELDS)

    summary_rows = _summarize(raw_rows)
    _write_tsv(work_dir / "summary.tsv", summary_rows, SUMMARY_FIELDS)
    (work_dir / "summary.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "mode": "fasim_align_profile_cache_characterization",
                "repeats": args.repeats,
                "workers": workers,
                "workloads": workloads,
                "raw_rows": raw_rows,
                "summary_rows": summary_rows,
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
