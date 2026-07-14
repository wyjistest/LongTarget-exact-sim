#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOP5_COMPARE = ROOT / "scripts" / "compare_fasim_lite_topk.py"
CLUSTER_COMPARE = ROOT / "scripts" / "compare_fasim_lite_offline_cluster_topk.py"

FIELDS = (
    "workload",
    "repeat",
    "baseline_root",
    "candidate_root",
    "baseline_config_digest",
    "candidate_config_digest",
    "grid_count",
    "segment_count",
    "baseline_pipeline_wall_seconds",
    "candidate_pipeline_wall_seconds",
    "baseline_segment_wall_seconds",
    "candidate_segment_wall_seconds",
    "speedup",
    "wall_reduction_percent",
    "baseline_gasal2_requests",
    "candidate_gasal2_requests",
    "baseline_traceback_requests",
    "candidate_traceback_requests",
    "exact_work_tasks",
    "exact_work_cells",
    "exact_work_equal",
    "baseline_exact_stage_seconds",
    "candidate_exact_stage_seconds",
    "baseline_traceback_stage_seconds",
    "candidate_traceback_stage_seconds",
    "baseline_archive_bytes",
    "candidate_archive_bytes",
    "baseline_output_rows",
    "candidate_output_rows",
    "baseline_duplicate_rows",
    "candidate_duplicate_rows",
    "baseline_peak_rss_kb",
    "candidate_peak_rss_kb",
    "full_output_byte_equal",
    "missing_rows",
    "extra_rows",
    "top5_score_equal",
    "top5_stability_equal",
    "top5_nt_score_equal",
    "offline_clustered_top5_equal",
    "archive_restore_clean",
    "temporary_text_bytes",
    "fallbacks",
    "oom",
    "decision",
)


class CompareError(ValueError):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_config(root: Path) -> dict[str, object]:
    path = root / "run-config.json"
    if not path.is_file():
        raise CompareError(f"missing run config: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    recorded = str(payload.get("config_digest_sha256", ""))
    canonical_payload = dict(payload)
    canonical_payload.pop("config_digest_sha256", None)
    canonical = json.dumps(canonical_payload, sort_keys=True, separators=(",", ":"))
    actual = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    if recorded != actual:
        raise CompareError(f"run config digest mismatch in {path}")
    return payload


def load_summary(root: Path, config: dict[str, object]) -> dict[str, str]:
    path = root / "summary.txt"
    if not path.is_file():
        raise CompareError(f"missing run summary: {path}")
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            values[key] = value
    if values.get("config_digest_sha256") != config["config_digest_sha256"]:
        raise CompareError(f"summary/config digest mismatch in {path}")
    return values


def integer(values: dict[str, str], key: str, source: Path) -> int:
    if key not in values:
        raise CompareError(f"missing {key} in {source}")
    try:
        value = int(values[key])
    except ValueError as exc:
        raise CompareError(f"invalid integer {key}={values[key]!r} in {source}") from exc
    if value < 0:
        raise CompareError(f"invalid non-negative {key}={value} in {source}")
    return value


def floating(values: dict[str, str], key: str, source: Path) -> float:
    if key not in values:
        raise CompareError(f"missing {key} in {source}")
    try:
        value = float(values[key])
    except ValueError as exc:
        raise CompareError(f"invalid float {key}={values[key]!r} in {source}") from exc
    if not math.isfinite(value) or value < 0:
        raise CompareError(f"invalid non-negative {key}={value} in {source}")
    return value


def key_values(text: str) -> dict[str, str]:
    return dict(line.split("=", 1) for line in text.splitlines() if "=" in line)


def run_contract(command: list[str], label: str) -> dict[str, str]:
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        raise CompareError(
            f"{label} contract failed ({result.returncode}): {result.stderr or result.stdout}"
        )
    return key_values(result.stdout)


def grid_outputs(root: Path) -> dict[str, Path]:
    outputs = {
        path.parent.name: path
        for path in root.glob("grids/shift_*/merged-common-TFOsorted")
        if path.is_file()
    }
    if not outputs:
        raise CompareError(f"no merged grid outputs under {root}")
    return outputs


def require_equal_config(
    baseline: dict[str, object], candidate: dict[str, object]
) -> None:
    if baseline.get("exact_column_variant") != "legacy_authority_scoreinfo":
        raise CompareError("baseline config has unexpected exact-column variant")
    if candidate.get("exact_column_variant") != "gpu_pruned_scoreinfo_v1":
        raise CompareError("candidate config has unexpected exact-column variant")
    for name, payload in (("baseline", baseline), ("candidate", candidate)):
        if payload.get("archive_first") is not True:
            raise CompareError(f"{name} config did not enable archive-first")
        if payload.get("persistent_context") is not False:
            raise CompareError(f"{name} config unexpectedly enabled persistent context")
        if payload.get("traceback_certificate_mode") != "disabled":
            raise CompareError(f"{name} config unexpectedly enabled traceback certificate")
        if payload.get("worker_count") != 1:
            raise CompareError(f"{name} config must use one worker")
    baseline_comparable = dict(baseline)
    candidate_comparable = dict(candidate)
    for payload in (baseline_comparable, candidate_comparable):
        payload.pop("config_digest_sha256", None)
        payload.pop("exact_column_variant", None)
    if baseline_comparable != candidate_comparable:
        differing = sorted(
            key
            for key in baseline_comparable.keys() | candidate_comparable.keys()
            if baseline_comparable.get(key) != candidate_comparable.get(key)
        )
        raise CompareError(f"non-variant run config drift: {differing}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare one paired integrated GASAL2 segmented-query run."
    )
    parser.add_argument("--workload", required=True)
    parser.add_argument("--repeat", required=True, type=int)
    parser.add_argument("--baseline-root", required=True, type=Path)
    parser.add_argument("--candidate-root", required=True, type=Path)
    parser.add_argument("--work-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    baseline_config = load_config(args.baseline_root)
    candidate_config = load_config(args.candidate_root)
    require_equal_config(baseline_config, candidate_config)
    baseline_summary = load_summary(args.baseline_root, baseline_config)
    candidate_summary = load_summary(args.candidate_root, candidate_config)
    baseline_source = args.baseline_root / "summary.txt"
    candidate_source = args.candidate_root / "summary.txt"

    baseline_outputs = grid_outputs(args.baseline_root)
    candidate_outputs = grid_outputs(args.candidate_root)
    if baseline_outputs.keys() != candidate_outputs.keys():
        raise CompareError(
            "baseline/candidate grid output mismatch: "
            f"{sorted(baseline_outputs)} != {sorted(candidate_outputs)}"
        )

    args.work_dir.mkdir(parents=True, exist_ok=True)
    for shift in sorted(baseline_outputs):
        baseline_output = baseline_outputs[shift]
        candidate_output = candidate_outputs[shift]
        if sha256(baseline_output) != sha256(candidate_output):
            raise CompareError(f"full output byte mismatch for {shift}")
        top5 = run_contract(
            [
                "python3",
                str(TOP5_COMPARE),
                "--baseline",
                str(baseline_output),
                "--candidate",
                str(candidate_output),
                "--k",
                "5",
            ],
            f"{shift} top5",
        )
        for key in (
            "top5_score_equal",
            "top5_stability_equal",
            "top5_nt_score_equal",
        ):
            if top5.get(key) != "true":
                raise CompareError(f"{shift} {key} is not true")
        if top5.get("missing_rows") != "0" or top5.get("extra_rows") != "0":
            raise CompareError(f"{shift} canonical row-set differs despite byte gate")
        cluster = run_contract(
            [
                "python3",
                str(CLUSTER_COMPARE),
                "--baseline",
                str(baseline_output),
                "--candidate",
                str(candidate_output),
                "--k",
                "5",
                "--details",
                str(args.work_dir / f"{shift}-offline-cluster.tsv"),
            ],
            f"{shift} offline cluster",
        )
        if cluster.get("top5_offline_cluster_equal") != "true":
            raise CompareError(f"{shift} offline clustered top5 differs")
        if cluster.get("top5_offline_cluster_overlap") != "5":
            raise CompareError(f"{shift} offline clustered top5 overlap is not 5")
        (args.work_dir / f"{shift}-top5.txt").write_text(
            "".join(f"{key}={value}\n" for key, value in top5.items()),
            encoding="utf-8",
        )
        (args.work_dir / f"{shift}-offline-cluster.txt").write_text(
            "".join(f"{key}={value}\n" for key, value in cluster.items()),
            encoding="utf-8",
        )

    for name, values, source in (
        ("baseline", baseline_summary, baseline_source),
        ("candidate", candidate_summary, candidate_source),
    ):
        expected_enabled = 0 if name == "baseline" else 1
        if integer(values, "exact_scoreinfo_gpu_pruned_output_enabled", source) != expected_enabled:
            raise CompareError(f"{name} exact-scoreInfo variant did not activate as configured")
        for key in (
            "exact_scoreinfo_gpu_column_pruned_output_enabled",
            "exact_scoreinfo_gpu_overflow_batches",
            "exact_scoreinfo_gpu_fallback_batches",
            "gasal2_fallbacks",
            "length_guard_fallbacks",
            "per_segment_full_text_emitted",
            "text_input_bytes",
        ):
            if integer(values, key, source) != 0:
                raise CompareError(f"{name} expected {key}=0")
        if integer(values, "bounded_memory_backend_active", source) != 1:
            raise CompareError(f"{name} bounded merge backend is inactive")
        if values.get("top5_offline_cluster_equal") != "true":
            raise CompareError(f"{name} shifted-grid clustered top5 is not stable")
        if values.get("top5_offline_cluster_overlap") != "5":
            raise CompareError(f"{name} shifted-grid clustered top5 overlap is not 5")

    baseline_tasks = integer(baseline_summary, "exact_work_tasks", baseline_source)
    candidate_tasks = integer(candidate_summary, "exact_work_tasks", candidate_source)
    baseline_cells = integer(baseline_summary, "exact_work_cells", baseline_source)
    candidate_cells = integer(candidate_summary, "exact_work_cells", candidate_source)
    if baseline_tasks != candidate_tasks or baseline_cells != candidate_cells:
        raise CompareError(
            "exact work differs: "
            f"tasks {baseline_tasks}!={candidate_tasks}, cells {baseline_cells}!={candidate_cells}"
        )

    baseline_wall = floating(
        baseline_summary, "pipeline_wall_seconds", baseline_source
    )
    candidate_wall = floating(
        candidate_summary, "pipeline_wall_seconds", candidate_source
    )
    speedup = baseline_wall / candidate_wall if candidate_wall else 0.0
    reduction = (
        100.0 * (baseline_wall - candidate_wall) / baseline_wall
        if baseline_wall
        else 0.0
    )
    segment_count = sum(
        integer(baseline_summary, f"grid_shift_{shift}_segment_count", baseline_source)
        for shift in baseline_config["grid_shifts"]
    )
    candidate_segment_count = sum(
        integer(candidate_summary, f"grid_shift_{shift}_segment_count", candidate_source)
        for shift in candidate_config["grid_shifts"]
    )
    if segment_count != candidate_segment_count:
        raise CompareError("baseline/candidate segment count differs")

    row: dict[str, str | int] = {
        "workload": args.workload,
        "repeat": args.repeat,
        "baseline_root": str(args.baseline_root),
        "candidate_root": str(args.candidate_root),
        "baseline_config_digest": baseline_config["config_digest_sha256"],
        "candidate_config_digest": candidate_config["config_digest_sha256"],
        "grid_count": len(baseline_outputs),
        "segment_count": segment_count,
        "baseline_pipeline_wall_seconds": f"{baseline_wall:.6f}",
        "candidate_pipeline_wall_seconds": f"{candidate_wall:.6f}",
        "baseline_segment_wall_seconds": f"{floating(baseline_summary, 'segment_run_wall_seconds', baseline_source):.6f}",
        "candidate_segment_wall_seconds": f"{floating(candidate_summary, 'segment_run_wall_seconds', candidate_source):.6f}",
        "speedup": f"{speedup:.6f}",
        "wall_reduction_percent": f"{reduction:.6f}",
        "baseline_gasal2_requests": integer(baseline_summary, "gasal2_requests", baseline_source),
        "candidate_gasal2_requests": integer(candidate_summary, "gasal2_requests", candidate_source),
        "baseline_traceback_requests": integer(baseline_summary, "gasal2_traceback_requests", baseline_source),
        "candidate_traceback_requests": integer(candidate_summary, "gasal2_traceback_requests", candidate_source),
        "exact_work_tasks": baseline_tasks,
        "exact_work_cells": baseline_cells,
        "exact_work_equal": 1,
        "baseline_exact_stage_seconds": f"{floating(baseline_summary, 'exact_stage_seconds', baseline_source):.6f}",
        "candidate_exact_stage_seconds": f"{floating(candidate_summary, 'exact_stage_seconds', candidate_source):.6f}",
        "baseline_traceback_stage_seconds": f"{floating(baseline_summary, 'traceback_host_observed_stage_seconds', baseline_source):.6f}",
        "candidate_traceback_stage_seconds": f"{floating(candidate_summary, 'traceback_host_observed_stage_seconds', candidate_source):.6f}",
        "baseline_archive_bytes": integer(baseline_summary, "archive_input_bytes", baseline_source),
        "candidate_archive_bytes": integer(candidate_summary, "archive_input_bytes", candidate_source),
        "baseline_output_rows": integer(baseline_summary, "output_rows", baseline_source),
        "candidate_output_rows": integer(candidate_summary, "output_rows", candidate_source),
        "baseline_duplicate_rows": integer(baseline_summary, "duplicate_rows", baseline_source),
        "candidate_duplicate_rows": integer(candidate_summary, "duplicate_rows", candidate_source),
        "baseline_peak_rss_kb": integer(baseline_summary, "peak_rss_kb", baseline_source),
        "candidate_peak_rss_kb": integer(candidate_summary, "peak_rss_kb", candidate_source),
        "full_output_byte_equal": 1,
        "missing_rows": 0,
        "extra_rows": 0,
        "top5_score_equal": 1,
        "top5_stability_equal": 1,
        "top5_nt_score_equal": 1,
        "offline_clustered_top5_equal": 1,
        "archive_restore_clean": 1,
        "temporary_text_bytes": 0,
        "fallbacks": 0,
        "oom": 0,
        "decision": "paired_integrated_contract_clean",
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=FIELDS, delimiter="\t", lineterminator="\n"
        )
        writer.writeheader()
        writer.writerow(row)
    print("".join(f"{field}={row[field]}\n" for field in FIELDS), end="")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, UnicodeError, json.JSONDecodeError, CompareError) as exc:
        raise SystemExit(str(exc)) from exc
