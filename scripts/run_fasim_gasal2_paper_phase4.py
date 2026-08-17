#!/usr/bin/env python3
"""Collect Phase 4 ablation, archive, exact-column, and resource receipts."""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import run_fasim_gasal2_paper_benchmarks as harness  # noqa: E402
from run_fasim_gasal2_paper_phase3 import (  # noqa: E402
    atomic_json,
    atomic_tsv,
    canonical_digest,
    load_json,
    sha256,
)


RUNTIME_EPOCH = 0
RUNTIME_COMMIT = "0d11aa2d61b7ccda59b462ab8e0750dad17ee18f"
SEED = 20260715
BINARY_SHA256 = "613b24d9190b8b931661fce231ded6662d2b2b3e5772262310e069c15f191cc8"
PAIR_ROOT_NAME = "pairs-v1"
EXPECTED_ROWS = {
    "c5_archive_h19_2mb": ("C5", "archive_pair", "archive_first_exact_restore_v1"),
    "c5_archive_large_synthetic": (
        "C5",
        "archive_pair",
        "archive_merge_large_synthetic_v1",
    ),
    "c6_exact_h19_2mb": ("C6", "exact_column_pair", "exact_column_safe_v1"),
    "c6_exact_kcnq_segment_chr22": (
        "C6",
        "exact_column_pair",
        "exact_column_safe_v1",
    ),
}


def build_phase4_plan(rows: list[dict[str, str]], seed: int) -> dict[str, object]:
    found = {row["workload_id"] for row in rows}
    if found != set(EXPECTED_ROWS) or len(rows) != len(EXPECTED_ROWS):
        raise ValueError("frozen Phase 4 workload set drifted")
    pair_count = 0
    for row in rows:
        expected = EXPECTED_ROWS[row["workload_id"]]
        observed = (row["claim_id"], row["adapter_id"], row["preset_id"])
        if observed != expected or row["required_pairs"] != "3":
            raise ValueError(f"Phase 4 manifest contract drift: {row['workload_id']}")
        pair_count += int(row["required_pairs"])
    pairs: list[dict[str, object]] = []
    warmups: list[dict[str, object]] = []
    for row in sorted(rows, key=lambda item: item["workload_id"]):
        for mode in ("baseline", "candidate"):
            warmups.append(
                {
                    "workload_id": row["workload_id"],
                    "mode": mode,
                    "run_id": harness.run_id(row["workload_id"], 0, mode, True),
                }
            )
        for pair_id in range(1, int(row["required_pairs"]) + 1):
            order, modes = harness.pair_order(seed, row["workload_id"], pair_id)
            pairs.append(
                {
                    "workload_id": row["workload_id"],
                    "pair_id": pair_id,
                    "pair_order": order,
                    "modes": modes,
                }
            )
    return {
        "schema_version": 1,
        "runtime_epoch": RUNTIME_EPOCH,
        "runtime_commit": RUNTIME_COMMIT,
        "workload_count": len(rows),
        "pair_count": pair_count,
        "timed_run_count": pair_count * 2,
        "warmup_count": len(rows) * 2,
        "seed": seed,
        "warmups": warmups,
        "pairs": pairs,
    }


def _benchmark_metrics(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if raw.startswith("benchmark.") and "=" in raw:
            key, value = raw.split("=", 1)
            values[key] = value
    return values


def _metric_int(values: dict[str, str], key: str) -> int:
    try:
        value = int(values[key])
    except (KeyError, ValueError) as exc:
        raise ValueError(f"missing or invalid integer telemetry: {key}") from exc
    if value < 0:
        raise ValueError(f"negative telemetry: {key}")
    return value


def _metric_float(values: dict[str, str], key: str) -> float:
    try:
        value = float(values[key])
    except (KeyError, ValueError) as exc:
        raise ValueError(f"missing or invalid numeric telemetry: {key}") from exc
    if value < 0:
        raise ValueError(f"negative telemetry: {key}")
    return value


def exact_metrics(path: Path) -> dict[str, int | float]:
    values = _benchmark_metrics(path)
    column_tasks = _metric_int(
        values, "benchmark.fasim_top5_gasal2_phase_exact_column_tasks"
    )
    scoreinfo_tasks = _metric_int(
        values, "benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_tasks"
    )
    column_cells = _metric_int(
        values, "benchmark.fasim_top5_gasal2_phase_exact_column_cells"
    )
    scoreinfo_cells = _metric_int(
        values, "benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_cells"
    )
    if column_tasks and scoreinfo_tasks and column_tasks != scoreinfo_tasks:
        raise ValueError("exact-column task telemetry disagrees")
    if column_cells and scoreinfo_cells and column_cells != scoreinfo_cells:
        raise ValueError("exact-column cell telemetry disagrees")
    return {
        "exact_tasks": column_tasks or scoreinfo_tasks,
        "exact_cells": column_cells or scoreinfo_cells,
        "exact_stage_seconds": _metric_float(
            values, "benchmark.fasim_top5_gasal2_phase_exact_column_wall_seconds"
        )
        + _metric_float(
            values, "benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_wall_seconds"
        ),
        "gasal2_requests": _metric_int(values, "benchmark.fasim_gasal2_requests"),
        "traceback_requests": _metric_int(
            values, "benchmark.fasim_gasal2_traceback_requests"
        ),
        "fallbacks": _metric_int(values, "benchmark.fasim_gasal2_fallbacks")
        + _metric_int(
            values,
            "benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_fallback_batches",
        ),
        "overflow_batches": _metric_int(
            values,
            "benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_overflow_batches",
        ),
    }


def evaluate_exact_contract(
    baseline: dict[str, int | float],
    candidate: dict[str, int | float],
    *,
    full_output_byte_equal: bool,
    all_three_top5_equal: bool,
    boundary_ties_equal: bool,
) -> dict[str, int | float | str]:
    exact_work_equal = int(
        baseline["exact_tasks"] == candidate["exact_tasks"]
        and baseline["exact_cells"] == candidate["exact_cells"]
    )
    request_counts_equal = int(
        baseline["gasal2_requests"] == candidate["gasal2_requests"]
        and baseline["traceback_requests"] == candidate["traceback_requests"]
    )
    clean = (
        full_output_byte_equal
        and all_three_top5_equal
        and boundary_ties_equal
        and exact_work_equal == 1
        and request_counts_equal == 1
        and int(candidate["fallbacks"]) == 0
        and int(candidate["overflow_batches"]) == 0
    )
    baseline_stage = float(baseline["exact_stage_seconds"])
    candidate_stage = float(candidate["exact_stage_seconds"])
    return {
        "status": "clean" if clean else "mismatch",
        "decision": "exact_column_contract_clean" if clean else "exact_column_contract_mismatch",
        "exact_work_equal": exact_work_equal,
        "request_counts_equal": request_counts_equal,
        "exact_stage_speedup": baseline_stage / candidate_stage if candidate_stage else 0.0,
    }


def parse_key_values(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if "=" in raw:
            key, value = raw.split("=", 1)
            values[key] = value
    return values


def find_unique(directory: Path, pattern: str) -> Path:
    paths = sorted(directory.glob(pattern))
    if len(paths) != 1:
        raise ValueError(f"expected one {pattern} under {directory}, found {len(paths)}")
    return paths[0]


def run_summary(run_dir: Path) -> dict[str, Any]:
    return load_json(run_dir / "summary.json")


def optional_benchmark_int(summary: dict[str, Any], key: str) -> int:
    metrics = summary.get("benchmark_metrics")
    if not isinstance(metrics, dict):
        return 0
    value = metrics.get(key, "0")
    try:
        return int(float(str(value or "0")))
    except ValueError as exc:
        raise ValueError(f"invalid benchmark counter {key}={value!r}") from exc


def reference_paths(
    row: dict[str, str], manifest: Path, run_dir: Path
) -> tuple[Path, Path]:
    query = run_dir / "inputs/query.fa"
    target_copy = run_dir / "inputs/target.fa"
    target = target_copy if target_copy.is_file() else harness.resolve_path(row["target_path"], manifest)
    if not query.is_file() or not target.is_file():
        raise ValueError(f"missing restore references for {run_dir}")
    return query, target


def restore_archive(
    archive: Path,
    query: Path,
    target: Path,
    output: Path,
    work: Path,
    label: str,
) -> dict[str, int | float | str]:
    restore_log = work / f"{label}-restore.log"
    restore_stderr = work / f"{label}-restore.stderr.log"
    time_path = work / f"{label}-restore.time.txt"
    command = [
        "/usr/bin/time",
        "-v",
        "-o",
        str(time_path),
        sys.executable,
        str(ROOT / "scripts/restore_fasim_tfosorted_column_archive_probe.py"),
        "--archive",
        str(archive),
        "--output",
        str(output),
        "--query-fasta",
        str(query),
        "--target-fasta",
        str(target),
    ]
    started = time.perf_counter()
    with restore_log.open("w", encoding="utf-8") as stdout, restore_stderr.open(
        "w", encoding="utf-8"
    ) as stderr:
        result = subprocess.run(command, cwd=ROOT, stdout=stdout, stderr=stderr, check=False)
    wall = time.perf_counter() - started
    if result.returncode != 0:
        raise ValueError(f"archive restore failed: {restore_stderr}")
    integrity_path = work / f"{label}-integrity.txt"
    integrity = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/check_fasim_tfo_archive_integrity.py"),
            "--archive",
            str(archive),
            "--query-fasta",
            str(query),
            "--target-fasta",
            str(target),
            "--restore-log",
            str(restore_log),
            "--restored-output",
            str(output),
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    integrity_path.write_text(integrity.stdout, encoding="utf-8")
    (work / f"{label}-integrity.stderr.log").write_text(integrity.stderr, encoding="utf-8")
    if integrity.returncode != 0:
        raise ValueError(f"archive integrity failed: {integrity_path}")
    rss = 0
    for raw in time_path.read_text(encoding="utf-8").splitlines():
        if "Maximum resident set size (kbytes):" in raw:
            rss = int(raw.rsplit(":", 1)[1].strip())
            break
    return {
        "wall_seconds": wall,
        "max_rss_kb": rss,
        "output_sha256": sha256(output),
        "output_bytes": output.stat().st_size,
        "archive_sha256": sha256(archive),
        "archive_bytes": archive.stat().st_size,
    }


def compare_tfosorted(
    baseline: Path, candidate: Path, work: Path
) -> dict[str, int | str]:
    details = work / "top5-details.tsv"
    stdout_path = work / "comparator.stdout.log"
    stderr_path = work / "comparator.stderr.log"
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/compare_fasim_segmented_contract.py"),
            "--baseline",
            str(baseline),
            "--candidate",
            str(candidate),
            "--k",
            "5",
            "--details",
            str(details),
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    stdout_path.write_text(result.stdout, encoding="utf-8")
    stderr_path.write_text(result.stderr, encoding="utf-8")
    if result.returncode not in {0, 1} or not details.is_file():
        raise ValueError("TFOsorted comparator failed technically")
    values = dict(
        raw.split("=", 1) for raw in result.stdout.splitlines() if "=" in raw
    )
    required = (
        "full_missing_rows",
        "full_extra_rows",
        "clustered_score_top5_equal",
        "clustered_stability_top5_equal",
        "clustered_nt_top5_equal",
        "all_three_top5_equal",
        "boundary_ties_equal",
    )
    if any(field not in values for field in required):
        raise ValueError("TFOsorted comparator output is incomplete")
    return {field: int(values[field]) for field in required}


def common_pair_metrics(baseline: Path, candidate: Path) -> dict[str, int | float]:
    baseline_summary = run_summary(baseline)
    candidate_summary = run_summary(candidate)
    baseline_wall = float(baseline_summary["wall_seconds"])
    candidate_wall = float(candidate_summary["wall_seconds"])
    return {
        "baseline_wall_seconds": baseline_wall,
        "candidate_wall_seconds": candidate_wall,
        "paired_speedup": baseline_wall / candidate_wall,
        "baseline_max_rss_kb": int(baseline_summary.get("max_rss_kb", 0) or 0),
        "candidate_max_rss_kb": int(candidate_summary.get("max_rss_kb", 0) or 0),
        "baseline_gpu_memory_peak_mib": float(
            baseline_summary.get("gpu_memory_peak_mib", 0) or 0
        ),
        "candidate_gpu_memory_peak_mib": float(
            candidate_summary.get("gpu_memory_peak_mib", 0) or 0
        ),
    }


def compare_real_archive_pair(
    row: dict[str, str], manifest: Path, baseline: Path, candidate: Path, work: Path
) -> dict[str, object]:
    baseline_output = find_unique(baseline / "output", "*-TFOsorted")
    candidate_archive = find_unique(candidate / "output", "*.archive-first.tfoa")
    query, target = reference_paths(row, manifest, candidate)
    restored = work / "candidate-restored-TFOsorted"
    restore = restore_archive(
        candidate_archive, query, target, restored, work, "candidate"
    )
    comparison = compare_tfosorted(baseline_output, restored, work)
    byte_equal = sha256(baseline_output) == sha256(restored)
    candidate_summary = run_summary(candidate)
    fallbacks = sum(
        optional_benchmark_int(candidate_summary, key)
        for key in (
            "benchmark.fasim_gasal2_fallbacks",
            "benchmark.fasim_gasal2_length_guard_fallbacks",
            "benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_fallback_batches",
        )
    )
    clean = (
        byte_equal
        and comparison["full_missing_rows"] == 0
        and comparison["full_extra_rows"] == 0
        and comparison["all_three_top5_equal"] == 1
        and comparison["boundary_ties_equal"] == 1
        and fallbacks == 0
    )
    result: dict[str, object] = {
        **common_pair_metrics(baseline, candidate),
        **comparison,
        "status": "clean" if clean else "mismatch",
        "decision": "archive_restore_contract_clean" if clean else "archive_restore_contract_mismatch",
        "full_output_byte_equal": int(byte_equal),
        "archive_restore_clean": int(clean),
        "legacy_text_bytes": baseline_output.stat().st_size,
        "archive_bytes": candidate_archive.stat().st_size,
        "storage_reduction_ratio": baseline_output.stat().st_size
        / candidate_archive.stat().st_size,
        "restore_wall_seconds": restore["wall_seconds"],
        "restore_max_rss_kb": restore["max_rss_kb"],
        "candidate_run_restore_wall_seconds": float(
            run_summary(candidate)["wall_seconds"]
        )
        + float(restore["wall_seconds"]),
        "fallbacks": fallbacks,
        "overflow_batches": 0,
    }
    if clean:
        restored.unlink()
    return result


def compare_synthetic_archive_pair(
    baseline: Path, candidate: Path, work: Path
) -> dict[str, object]:
    baseline_output = find_unique(baseline / "output", "synthetic-merged-TFOsorted")
    candidate_output = find_unique(candidate / "output", "synthetic-merged-TFOsorted")
    baseline_values = parse_key_values(baseline / "stdout.log")
    candidate_values = parse_key_values(candidate / "stdout.log")
    baseline_rss = int(baseline_values["peak_rss_kb"])
    candidate_rss = int(candidate_values["peak_rss_kb"])
    rss_reduction = baseline_rss - candidate_rss
    rss_fraction = rss_reduction / baseline_rss
    byte_equal = sha256(baseline_output) == sha256(candidate_output)
    clean = (
        byte_equal
        and baseline_values.get("dedup_backend") == "memory"
        and candidate_values.get("dedup_backend") == "sqlite"
        and baseline_values.get("output_rows") == candidate_values.get("output_rows") == "150000"
        and rss_reduction >= 8192
        and rss_fraction >= 0.10
    )
    return {
        **common_pair_metrics(baseline, candidate),
        "status": "clean" if clean else "mismatch",
        "decision": "bounded_memory_merge_clean" if clean else "bounded_memory_merge_mismatch",
        "full_output_byte_equal": int(byte_equal),
        "full_missing_rows": 0 if byte_equal else -1,
        "full_extra_rows": 0 if byte_equal else -1,
        "clustered_score_top5_equal": "NA",
        "clustered_stability_top5_equal": "NA",
        "clustered_nt_top5_equal": "NA",
        "all_three_top5_equal": "NA",
        "boundary_ties_equal": "NA",
        "archive_restore_clean": "NA",
        "memory_merge_wall_seconds": float(baseline_values["merge_wall_seconds"]),
        "sqlite_merge_wall_seconds": float(candidate_values["merge_wall_seconds"]),
        "memory_peak_rss_kb": baseline_rss,
        "sqlite_peak_rss_kb": candidate_rss,
        "peak_rss_reduction_kb": rss_reduction,
        "peak_rss_reduction_fraction": rss_fraction,
        "dedup_db_bytes": int(candidate_values["dedup_db_bytes"]),
        "fallbacks": 0,
        "overflow_batches": 0,
    }


def compare_exact_pair(
    row: dict[str, str], manifest: Path, baseline: Path, candidate: Path, work: Path
) -> dict[str, object]:
    baseline_archive = find_unique(baseline / "output", "*.archive-first.tfoa")
    candidate_archive = find_unique(candidate / "output", "*.archive-first.tfoa")
    baseline_query, baseline_target = reference_paths(row, manifest, baseline)
    candidate_query, candidate_target = reference_paths(row, manifest, candidate)
    baseline_restored = work / "baseline-restored-TFOsorted"
    candidate_restored = work / "candidate-restored-TFOsorted"
    baseline_restore = restore_archive(
        baseline_archive,
        baseline_query,
        baseline_target,
        baseline_restored,
        work,
        "baseline",
    )
    candidate_restore = restore_archive(
        candidate_archive,
        candidate_query,
        candidate_target,
        candidate_restored,
        work,
        "candidate",
    )
    comparison = compare_tfosorted(baseline_restored, candidate_restored, work)
    byte_equal = sha256(baseline_restored) == sha256(candidate_restored)
    baseline_exact = exact_metrics(baseline / "stderr.log")
    candidate_exact = exact_metrics(candidate / "stderr.log")
    evaluation = evaluate_exact_contract(
        baseline_exact,
        candidate_exact,
        full_output_byte_equal=byte_equal,
        all_three_top5_equal=comparison["all_three_top5_equal"] == 1,
        boundary_ties_equal=comparison["boundary_ties_equal"] == 1,
    )
    common = common_pair_metrics(baseline, candidate)
    result: dict[str, object] = {
        **common,
        **comparison,
        **evaluation,
        "full_output_byte_equal": int(byte_equal),
        "archive_restore_clean": int(byte_equal),
        "baseline_exact_stage_seconds": baseline_exact["exact_stage_seconds"],
        "candidate_exact_stage_seconds": candidate_exact["exact_stage_seconds"],
        "baseline_exact_stage_share": float(baseline_exact["exact_stage_seconds"])
        / float(common["baseline_wall_seconds"]),
        "candidate_exact_stage_share": float(candidate_exact["exact_stage_seconds"])
        / float(common["candidate_wall_seconds"]),
        "exact_tasks": baseline_exact["exact_tasks"],
        "exact_cells": baseline_exact["exact_cells"],
        "gasal2_requests": baseline_exact["gasal2_requests"],
        "traceback_requests": baseline_exact["traceback_requests"],
        "fallbacks": candidate_exact["fallbacks"],
        "overflow_batches": candidate_exact["overflow_batches"],
        "baseline_restore_wall_seconds": baseline_restore["wall_seconds"],
        "candidate_restore_wall_seconds": candidate_restore["wall_seconds"],
    }
    if result["status"] == "clean":
        baseline_restored.unlink()
        candidate_restored.unlink()
    return result


def pair_id_text(workload_id: str, pair_id: int) -> str:
    return f"{workload_id}__pair{pair_id:02d}__{RUNTIME_EPOCH}"


def publish_pair(
    row: dict[str, str],
    pair: dict[str, object],
    manifest: Path,
    artifact_root: Path,
    resume: bool,
) -> str:
    workload_id = row["workload_id"]
    pair_id = int(pair["pair_id"])
    baseline = artifact_root / harness.run_id(workload_id, pair_id, "baseline")
    candidate = artifact_root / harness.run_id(workload_id, pair_id, "candidate")
    component_paths = {
        "baseline": baseline / "run-complete.json",
        "candidate": candidate / "run-complete.json",
    }
    for mode, path in component_paths.items():
        if not path.is_file():
            raise ValueError(f"missing {mode} run receipt: {path}")
    config: dict[str, object] = {
        "schema_version": 1,
        "pair_id_text": pair_id_text(workload_id, pair_id),
        "workload_id": workload_id,
        "claim_id": row["claim_id"],
        "pair_id": pair_id,
        "pair_order": pair["pair_order"],
        "runtime_epoch": RUNTIME_EPOCH,
        "runtime_commit": RUNTIME_COMMIT,
        "preset_id": row["preset_id"],
        "output_contract": row["output_contract"],
        "baseline_receipt_sha256": sha256(component_paths["baseline"]),
        "candidate_receipt_sha256": sha256(component_paths["candidate"]),
    }
    config["config_digest_sha256"] = canonical_digest(config)
    destination = artifact_root / PAIR_ROOT_NAME / pair_id_text(workload_id, pair_id)
    complete_path = destination / "pair-complete.json"
    if destination.exists():
        if not complete_path.is_file():
            raise ValueError(f"incomplete pair receipt: {destination}")
        existing = load_json(destination / "pair-config.json")
        complete = load_json(complete_path)
        summary_path = destination / "pair-summary.json"
        if existing.get("config_digest_sha256") != config["config_digest_sha256"]:
            raise ValueError(f"pair config digest mismatch: {destination}")
        if complete.get("summary_sha256") != sha256(summary_path):
            raise ValueError(f"pair summary digest mismatch: {destination}")
        if not resume:
            raise ValueError(f"duplicate pair ID: {destination.name}")
        return "reused"
    temporary = artifact_root / PAIR_ROOT_NAME / f".{destination.name}.partial.{os.getpid()}"
    temporary.mkdir(parents=True)
    atomic_json(temporary / "pair-config.json", config)
    try:
        if workload_id == "c5_archive_h19_2mb":
            comparison = compare_real_archive_pair(
                row, manifest, baseline, candidate, temporary
            )
        elif workload_id == "c5_archive_large_synthetic":
            comparison = compare_synthetic_archive_pair(baseline, candidate, temporary)
        else:
            comparison = compare_exact_pair(row, manifest, baseline, candidate, temporary)
    except BaseException as exc:
        atomic_json(
            temporary / "pair-failure.json",
            {
                "schema_version": 1,
                "status": "technical_failure",
                "reason": "phase4_pair_comparator_failure",
                "exception_type": type(exc).__name__,
                "message": str(exc),
            },
        )
        failed = destination.with_name(f"{destination.name}.failed.{time.time_ns()}")
        os.replace(temporary, failed)
        raise
    summary = {**config, **comparison}
    summary_path = temporary / "pair-summary.json"
    atomic_json(summary_path, summary)
    atomic_json(
        temporary / "pair-complete.json",
        {
            "schema_version": 1,
            "status": "complete",
            "pair_id_text": config["pair_id_text"],
            "config_digest_sha256": config["config_digest_sha256"],
            "summary_sha256": sha256(summary_path),
        },
    )
    os.replace(temporary, destination)
    return "completed"


def invoke_harness(
    manifest: Path,
    binary: Path,
    artifact_root: Path,
    row: dict[str, str],
    mode: str,
    seed: int,
    resume: bool,
    *,
    pair_id: int | None = None,
    warmup: bool = False,
) -> None:
    command = [
        "bash",
        str(ROOT / "scripts/run_fasim_gasal2_paper_benchmarks.sh"),
        "--manifest",
        str(manifest),
        "--binary",
        str(binary),
        "--artifact-root",
        str(artifact_root),
        "--workload-id",
        row["workload_id"],
        "--mode",
        mode,
        "--seed",
        str(seed),
    ]
    if warmup:
        command.append("--warmup")
    elif pair_id is not None:
        command.extend(["--pair-id", str(pair_id)])
    if resume:
        command.append("--resume")
    environment = os.environ.copy()
    if int(row["requires_gpu_count"]) == 1:
        visible = environment.get("CUDA_VISIBLE_DEVICES", "0").split(",")[0].strip()
        environment["CUDA_VISIBLE_DEVICES"] = visible or "0"
    label = f"{row['workload_id']} {'warmup' if warmup else f'pair {pair_id}'} {mode}"
    print(f"phase4_run_start={label}", file=sys.stderr, flush=True)
    result = subprocess.run(
        command,
        cwd=ROOT,
        env=environment,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit(result.stderr.strip() or result.stdout.strip() or "Phase 4 run failed")
    print(f"phase4_run_done={label}", file=sys.stderr, flush=True)


def collect_tables(artifact_root: Path, rows_by_id: dict[str, dict[str, str]]) -> None:
    run_rows: list[dict[str, object]] = []
    for run_dir in sorted(artifact_root.iterdir()):
        if not run_dir.is_dir() or not (run_dir / "run-complete.json").is_file():
            continue
        config = load_json(run_dir / "run-config.json")
        if config.get("workload_id") not in rows_by_id:
            continue
        summary = load_json(run_dir / "summary.json")
        run_rows.append(
            {
                "run_id": config["run_id"],
                "workload_id": config["workload_id"],
                "claim_id": rows_by_id[str(config["workload_id"])]["claim_id"],
                "pair_id": config["pair_id"],
                "mode": config["mode"],
                "warmup": int(bool(config["warmup"])),
                "runtime_epoch": config["runtime_epoch"],
                "config_digest_sha256": config["config_digest_sha256"],
                "wall_seconds": summary["wall_seconds"],
                "max_rss_kb": summary.get("max_rss_kb", 0),
                "gpu_memory_peak_mib": summary.get("gpu_memory_peak_mib", 0),
                "gpu_utilization_peak_percent": summary.get("gpu_utilization_peak_percent", 0),
                "receipt_path": str(run_dir / "run-complete.json"),
            }
        )
    run_fields = list(run_rows[0])
    atomic_tsv(artifact_root / "phase4-runs.tsv", run_fields, run_rows)

    pair_rows: list[dict[str, object]] = []
    for pair_dir in sorted((artifact_root / PAIR_ROOT_NAME).iterdir()):
        if not pair_dir.is_dir() or not (pair_dir / "pair-complete.json").is_file():
            continue
        summary = load_json(pair_dir / "pair-summary.json")
        summary["pair_summary_path"] = str(pair_dir / "pair-summary.json")
        pair_rows.append(summary)
    all_fields: list[str] = []
    for row in pair_rows:
        for field in row:
            if field not in all_fields:
                all_fields.append(field)
    for row in pair_rows:
        for field in all_fields:
            row.setdefault(field, "NA")
    atomic_tsv(artifact_root / "phase4-pairs.tsv", all_fields, pair_rows)

    failure_rows: list[dict[str, object]] = []
    for failure in sorted(artifact_root.rglob("*.failed.*")):
        if not failure.is_dir():
            continue
        payload_path = failure / "pair-failure.json"
        if not payload_path.is_file():
            payload_path = failure / "correctness.json"
        payload = load_json(payload_path) if payload_path.is_file() else {}
        failure_rows.append(
            {
                "artifact_path": str(failure),
                "status": payload.get("status", "technical_failure"),
                "reason": payload.get("reason", "unknown"),
            }
        )
    atomic_tsv(
        artifact_root / "phase4-failures.tsv",
        ["artifact_path", "status", "reason"],
        failure_rows,
    )

    excluded = {
        "phase4-runs.tsv",
        "phase4-pairs.tsv",
        "phase4-failures.tsv",
        "phase4-artifacts.tsv",
    }
    artifact_rows: list[dict[str, object]] = []
    for path in sorted(item for item in artifact_root.rglob("*") if item.is_file()):
        if path.parent == artifact_root and path.name in excluded:
            continue
        artifact_rows.append(
            {
                "artifact_path": path.relative_to(artifact_root).as_posix(),
                "size_bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
        )
    atomic_tsv(
        artifact_root / "phase4-artifacts.tsv",
        ["artifact_path", "size_bytes", "sha256"],
        artifact_rows,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=ROOT / "paper/workload_manifest.tsv")
    parser.add_argument("--binary", type=Path, default=ROOT / ".tmp/fasim_longtarget_gasal2_direct")
    parser.add_argument(
        "--artifact-root",
        type=Path,
        default=ROOT / ".paper-artifacts/runtime-epoch-0-pre-freeze/phase4-ablation-resource",
    )
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    rows = [
        row
        for row in harness.load_manifest(args.manifest)
        if row["workload_id"] in EXPECTED_ROWS
    ]
    plan = build_phase4_plan(rows, args.seed)
    if args.dry_run:
        json.dump(plan, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
        return 0
    if not args.binary.is_file() or sha256(args.binary) != BINARY_SHA256:
        raise SystemExit("Phase 4 binary is missing or differs from the frozen runtime binary")
    args.artifact_root.mkdir(parents=True, exist_ok=True)
    plan_payload = {
        **plan,
        "manifest_sha256": sha256(args.manifest),
        "binary_sha256": sha256(args.binary),
    }
    plan_payload["config_digest_sha256"] = canonical_digest(plan_payload)
    plan_path = args.artifact_root / "phase4-plan.json"
    if plan_path.exists():
        existing_plan = load_json(plan_path)
        if existing_plan.get("config_digest_sha256") != plan_payload["config_digest_sha256"]:
            raise SystemExit("Phase 4 plan digest mismatch")
        if not args.resume:
            raise SystemExit("Phase 4 plan already exists; use --resume")
    else:
        atomic_json(plan_path, plan_payload)
    rows_by_id = {row["workload_id"]: row for row in rows}
    for warmup in plan["warmups"]:
        row = rows_by_id[str(warmup["workload_id"])]
        invoke_harness(
            args.manifest,
            args.binary,
            args.artifact_root,
            row,
            str(warmup["mode"]),
            args.seed,
            args.resume,
            warmup=True,
        )
    for pair in plan["pairs"]:
        row = rows_by_id[str(pair["workload_id"])]
        for mode in pair["modes"]:
            invoke_harness(
                args.manifest,
                args.binary,
                args.artifact_root,
                row,
                str(mode),
                args.seed,
                args.resume,
                pair_id=int(pair["pair_id"]),
            )
        outcome = publish_pair(row, pair, args.manifest, args.artifact_root, args.resume)
        print(
            f"phase4_pair_done={row['workload_id']} pair={pair['pair_id']} outcome={outcome}",
            file=sys.stderr,
            flush=True,
        )
    collect_tables(args.artifact_root, rows_by_id)
    print(f"phase4_workloads={plan['workload_count']}")
    print(f"phase4_pairs={plan['pair_count']}")
    print(f"phase4_artifact_root={args.artifact_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
