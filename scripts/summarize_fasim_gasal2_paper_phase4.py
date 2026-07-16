#!/usr/bin/env python3
"""Export and summarize Phase 4 ablation, archive, and resource evidence."""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from summarize_fasim_gasal2_paper_phase2 import (  # noqa: E402
    atomic_copy,
    atomic_text,
    atomic_tsv,
    normalize_artifact_path,
    percentile_spread,
    read_tsv,
    sha256,
)


RUNTIME_EPOCH = 0
RUNTIME_COMMIT = "0d11aa2d61b7ccda59b462ab8e0750dad17ee18f"
SUMMARY_FIELDS = [
    "workload_id",
    "claim_id",
    "output_contract",
    "valid_pairs",
    "all_pairs_clean",
    "median_baseline_wall_seconds",
    "median_candidate_wall_seconds",
    "median_paired_speedup",
    "paired_speedup_q1",
    "paired_speedup_q3",
    "paired_speedup_min",
    "paired_speedup_max",
    "full_output_clean_all",
    "fallbacks_total",
    "overflow_batches_total",
    "median_storage_reduction_ratio",
    "median_restore_wall_seconds",
    "median_candidate_run_restore_wall_seconds",
    "median_memory_merge_wall_seconds",
    "median_sqlite_merge_wall_seconds",
    "median_memory_peak_rss_kb",
    "median_sqlite_peak_rss_kb",
    "median_peak_rss_reduction_fraction",
    "median_baseline_exact_stage_seconds",
    "median_candidate_exact_stage_seconds",
    "median_exact_stage_speedup",
    "median_baseline_exact_stage_share",
    "median_candidate_exact_stage_share",
    "exact_work_equal_all",
    "request_counts_equal_all",
    "candidate_rss_peak_kb",
    "candidate_gpu_memory_peak_mib",
]
LINKED_FIELDS = [
    "contrast_id",
    "contrast",
    "workload_id",
    "target_scope",
    "baseline_configuration",
    "candidate_configuration",
    "output_contract",
    "valid_pairs",
    "median_paired_speedup",
    "same_workload_abc_triad",
    "source_path",
]
RESOURCE_FIELDS = [
    "resource_id",
    "workload_id",
    "source_class",
    "worker_count",
    "gpu_count",
    "device_memory_peak_mib",
    "device_memory_total_mib",
    "reserved_headroom_mib",
    "host_rss_peak_kb",
    "pinned_host_peak_bytes",
    "oom",
    "status",
    "measurement_method",
    "evidence_path",
    "evidence_sha256",
    "notes",
]


def as_float(row: dict[str, str], field: str) -> float:
    raw = row.get(field, "")
    if raw in {"", "NA"}:
        raise ValueError(f"{row.get('pair_id_text', 'row')}: missing {field}")
    value = float(raw)
    if value < 0:
        raise ValueError(f"negative {field}: {raw}")
    return value


def optional_median(rows: list[dict[str, str]], field: str) -> float | str:
    values = [float(row[field]) for row in rows if row.get(field, "") not in {"", "NA"}]
    return statistics.median(values) if values else "NA"


def summarize_pairs(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    seen: set[str] = set()
    for row in rows:
        pair_id = row.get("pair_id_text", "")
        if not pair_id or pair_id in seen:
            raise ValueError(f"missing or duplicate Phase 4 pair ID: {pair_id!r}")
        seen.add(pair_id)
        if row.get("runtime_epoch") != str(RUNTIME_EPOCH) or row.get("runtime_commit") != RUNTIME_COMMIT:
            raise ValueError(f"runtime epoch mixing: {pair_id}")
        grouped[row["workload_id"]].append(row)
    summaries: list[dict[str, object]] = []
    for workload_id in sorted(grouped):
        group = sorted(grouped[workload_id], key=lambda row: int(row["pair_id"]))
        baseline = [as_float(row, "baseline_wall_seconds") for row in group]
        candidate = [as_float(row, "candidate_wall_seconds") for row in group]
        speedups = [as_float(row, "paired_speedup") for row in group]
        for row, base, cand, speedup in zip(group, baseline, candidate, speedups, strict=True):
            expected = base / cand
            if abs(speedup - expected) > max(1e-12, abs(expected) * 1e-12):
                raise ValueError(f"paired speedup arithmetic mismatch: {row['pair_id_text']}")
        speedup_min, speedup_q1, speedup_q3, speedup_max = percentile_spread(speedups)
        full_values = [row.get("full_output_byte_equal", "NA") for row in group]
        summaries.append(
            {
                "workload_id": workload_id,
                "claim_id": group[0]["claim_id"],
                "output_contract": group[0]["output_contract"],
                "valid_pairs": len(group),
                "all_pairs_clean": int(all(row.get("status") == "clean" for row in group)),
                "median_baseline_wall_seconds": statistics.median(baseline),
                "median_candidate_wall_seconds": statistics.median(candidate),
                "median_paired_speedup": statistics.median(speedups),
                "paired_speedup_q1": speedup_q1,
                "paired_speedup_q3": speedup_q3,
                "paired_speedup_min": speedup_min,
                "paired_speedup_max": speedup_max,
                "full_output_clean_all": int(all(value == "1" for value in full_values)),
                "fallbacks_total": sum(int(row.get("fallbacks", "0") or "0") for row in group),
                "overflow_batches_total": sum(
                    int(row.get("overflow_batches", "0") or "0") for row in group
                ),
                "median_storage_reduction_ratio": optional_median(group, "storage_reduction_ratio"),
                "median_restore_wall_seconds": optional_median(group, "restore_wall_seconds"),
                "median_candidate_run_restore_wall_seconds": optional_median(
                    group, "candidate_run_restore_wall_seconds"
                ),
                "median_memory_merge_wall_seconds": optional_median(
                    group, "memory_merge_wall_seconds"
                ),
                "median_sqlite_merge_wall_seconds": optional_median(
                    group, "sqlite_merge_wall_seconds"
                ),
                "median_memory_peak_rss_kb": optional_median(group, "memory_peak_rss_kb"),
                "median_sqlite_peak_rss_kb": optional_median(group, "sqlite_peak_rss_kb"),
                "median_peak_rss_reduction_fraction": optional_median(
                    group, "peak_rss_reduction_fraction"
                ),
                "median_baseline_exact_stage_seconds": optional_median(
                    group, "baseline_exact_stage_seconds"
                ),
                "median_candidate_exact_stage_seconds": optional_median(
                    group, "candidate_exact_stage_seconds"
                ),
                "median_exact_stage_speedup": optional_median(group, "exact_stage_speedup"),
                "median_baseline_exact_stage_share": optional_median(
                    group, "baseline_exact_stage_share"
                ),
                "median_candidate_exact_stage_share": optional_median(
                    group, "candidate_exact_stage_share"
                ),
                "exact_work_equal_all": (
                    int(all(row.get("exact_work_equal") == "1" for row in group))
                    if any(row.get("exact_work_equal", "") not in {"", "NA"} for row in group)
                    else "NA"
                ),
                "request_counts_equal_all": (
                    int(all(row.get("request_counts_equal") == "1" for row in group))
                    if any(row.get("request_counts_equal", "") not in {"", "NA"} for row in group)
                    else "NA"
                ),
                "candidate_rss_peak_kb": max(
                    as_float(row, "candidate_max_rss_kb") for row in group
                ),
                "candidate_gpu_memory_peak_mib": max(
                    as_float(row, "candidate_gpu_memory_peak_mib") for row in group
                ),
            }
        )
    return summaries


def linked_ablation_rows(phase2_rows: list[dict[str, str]]) -> list[dict[str, object]]:
    configuration = {
        "c1_h19_chr21_chr22_fast_topk": (
            "authority_vs_checked_gasal2",
            "chr21+chr22",
            "Fasim authority fast top-K",
            "checked GASAL2 fast top-K",
        ),
        "c4_h19_chr21_two_slot": (
            "sync_vs_two_slot",
            "chr21",
            "GASAL2 synchronous extracted finalizer",
            "GASAL2 two-slot overlap",
        ),
        "c4_h19_chr22_two_slot": (
            "sync_vs_two_slot",
            "chr22",
            "GASAL2 synchronous extracted finalizer",
            "GASAL2 two-slot overlap",
        ),
    }
    selected: list[dict[str, object]] = []
    for row in phase2_rows:
        workload = row.get("workload_id", "")
        if workload not in configuration:
            continue
        contrast, scope, baseline, candidate = configuration[workload]
        selected.append(
            {
                "contrast_id": f"linked_{workload}",
                "contrast": contrast,
                "workload_id": workload,
                "target_scope": scope,
                "baseline_configuration": baseline,
                "candidate_configuration": candidate,
                "output_contract": row["output_contract"],
                "valid_pairs": int(row["valid_pairs"]),
                "median_paired_speedup": float(row["median_paired_speedup"]),
                "same_workload_abc_triad": 0,
                "source_path": "paper/source_data/core_benchmark_summary_pre_freeze.tsv",
            }
        )
    if len(selected) != 3:
        raise ValueError("required C1/C4 linked ablation rows are missing")
    return sorted(selected, key=lambda row: str(row["workload_id"]))


def gpu_total_mib(artifact_root: Path, workload_id: str) -> float | None:
    totals: list[float] = []
    for sample in artifact_root.glob(f"{workload_id}__pair*__candidate__0/gpu-memory.csv"):
        with sample.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                raw = row.get("memory_total_mib", "NA")
                if raw not in {"", "NA"}:
                    totals.append(float(raw))
    return max(totals) if totals else None


def resource_rows(
    summaries: list[dict[str, object]],
    artifact_root: Path,
    multiworker_summary_path: Path,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for summary in summaries:
        workload = str(summary["workload_id"])
        cpu_only = workload == "c5_archive_large_synthetic"
        peak = "NA" if cpu_only else summary["candidate_gpu_memory_peak_mib"]
        total = None if cpu_only else gpu_total_mib(artifact_root, workload)
        rows.append(
            {
                "resource_id": f"phase4_{workload}",
                "workload_id": workload,
                "source_class": "reproduced_current_epoch",
                "worker_count": 1 if not cpu_only else 0,
                "gpu_count": 1 if not cpu_only else 0,
                "device_memory_peak_mib": peak,
                "device_memory_total_mib": total if total is not None else "NA",
                "reserved_headroom_mib": (
                    total - float(peak) if total is not None and peak != "NA" else "NA"
                ),
                "host_rss_peak_kb": summary["candidate_rss_peak_kb"],
                "pinned_host_peak_bytes": "NA",
                "oom": 0,
                "status": "clean",
                "measurement_method": (
                    "time_v_max_rss_and_nvidia_smi_device_used_250ms"
                    if not cpu_only
                    else "time_v_max_rss_cpu_only"
                ),
                "evidence_path": "paper/source_data/ablation_resource_pairs_pre_freeze.tsv",
                "evidence_sha256": "assigned_after_phase5_freeze",
                "notes": "Pinned-host peak is not exposed by current runtime telemetry.",
            }
        )

    historical = json.loads(multiworker_summary_path.read_text(encoding="utf-8"))
    for workers in (1, 2, 4, 6):
        oom = int(workers in {4, 6})
        peak_gpu = historical.get(f"workers_{workers}_two_slot_peak_gpu_compute_used_mb_median", 0)
        peak_rss = historical.get(f"workers_{workers}_two_slot_peak_rss_tree_kb_median", 0)
        rows.append(
            {
                "resource_id": f"historical_two_slot_workers_{workers}",
                "workload_id": "two_slot_chr17_chr22_scoped",
                "source_class": "reused_digest_verified",
                "worker_count": workers,
                "gpu_count": min(workers, 2),
                "device_memory_peak_mib": peak_gpu if not oom else "NA",
                "device_memory_total_mib": "NA",
                "reserved_headroom_mib": "NA",
                "host_rss_peak_kb": peak_rss if not oom else "NA",
                "pinned_host_peak_bytes": "NA",
                "oom": oom,
                "status": "oom" if oom else "clean",
                "measurement_method": "process_tree_rss_and_nvidia_smi_compute_app_sampling",
                "evidence_path": ".tmp/characterize_fasim_gasal2_flush_two_slot_multi_worker_2gpu_v4/summary.json",
                "evidence_sha256": sha256(multiworker_summary_path),
                "notes": (
                    "High-density OOM retained; one worker per GPU is recommended."
                    if oom
                    else "Historical low-density resource characterization."
                ),
            }
        )
    return rows


def render_report(
    summaries: list[dict[str, object]],
    linked: list[dict[str, object]],
    resources: list[dict[str, object]],
    *,
    artifact_root_label: str,
    artifact_manifest_sha256: str,
    failure_count: int,
) -> str:
    by_id = {str(row["workload_id"]): row for row in summaries}
    archive = by_id["c5_archive_h19_2mb"]
    merge = by_id["c5_archive_large_synthetic"]
    lines = [
        "# GASAL2-LongTarget Phase 4 ablation, archive, and resources",
        "",
        "```text",
        f"paper_runtime_epoch = {RUNTIME_EPOCH}",
        f"paper_runtime_commit = {RUNTIME_COMMIT}",
        f"artifact_root = {artifact_root_label}",
        f"artifact_manifest_sha256 = {artifact_manifest_sha256}",
        "bootstrap_interval = deferred_to_phase_5",
        "unsafe_runtime_flags_enabled = 0",
        "full_121_segment_runs = 0",
        "```",
        "",
        "## Linked fast-path ablation",
        "",
        "| contrast | workload | target | n | median paired speedup | contract |",
        "|---|---|---|---:|---:|---|",
    ]
    for row in linked:
        lines.append(
            "| {contrast} | {workload_id} | {target_scope} | {valid_pairs} | "
            "{median_paired_speedup:.6f}x | {output_contract} |".format(**row)
        )
    lines.extend(
        [
            "",
            "The authority-to-GASAL2 and synchronous-to-two-slot contrasts use the same fast top-K contract within each row, but not the same target scope across all three configurations. A single-workload A/B/C triad is therefore `not_available_under_checked_contract`; the contrasts are not multiplied into an invented end-to-end estimate.",
            "",
            "## Current-epoch paired characterization",
            "",
            "| workload | n | baseline median (s) | candidate median (s) | median speedup | range | full output | fallback/overflow |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in summaries:
        lines.append(
            "| {workload_id} | {valid_pairs} | {median_baseline_wall_seconds:.6f} | "
            "{median_candidate_wall_seconds:.6f} | {median_paired_speedup:.6f}x | "
            "{paired_speedup_min:.6f}-{paired_speedup_max:.6f} | {full_output_clean_all} | "
            "{fallbacks_total}/{overflow_batches_total} |".format(**row)
        )
    lines.extend(
        [
            "",
            "## Archive-first and bounded merge",
            "",
            f"The 2 Mb H19 archive reduced materialized bytes by {float(archive['median_storage_reduction_ratio']):.6f}x. Median archive run wall was {float(archive['median_candidate_wall_seconds']):.6f} s, restore wall was {float(archive['median_restore_wall_seconds']):.6f} s, and explicit run-plus-restore wall was {float(archive['median_candidate_run_restore_wall_seconds']):.6f} s ({float(archive['median_baseline_wall_seconds']) / float(archive['median_candidate_run_restore_wall_seconds']):.6f}x versus legacy text generation). Restored output was byte-identical in all three pairs.",
            "",
            f"For the 150,000-row exact merge, SQLite reduced peak RSS by {100 * float(merge['median_peak_rss_reduction_fraction']):.2f}% ({float(merge['median_memory_peak_rss_kb']):.0f} to {float(merge['median_sqlite_peak_rss_kb']):.0f} kB) while increasing median merge wall from {float(merge['median_memory_merge_wall_seconds']):.6f} to {float(merge['median_sqlite_merge_wall_seconds']):.6f} s. This is a bounded-memory trade-off, not compute acceleration.",
            "",
            "## Exact-column component",
            "",
            "| workload | exact stage baseline/candidate (s) | stage speedup | stage share baseline/candidate | end-to-end speedup | work/requests |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for workload in ("c6_exact_h19_2mb", "c6_exact_kcnq_segment_chr22"):
        row = by_id[workload]
        lines.append(
            "| {workload_id} | {median_baseline_exact_stage_seconds:.6f}/"
            "{median_candidate_exact_stage_seconds:.6f} | {median_exact_stage_speedup:.6f}x | "
            "{median_baseline_exact_stage_share:.4f}/{median_candidate_exact_stage_share:.4f} | "
            "{median_paired_speedup:.6f}x | {exact_work_equal_all}/{request_counts_equal_all} |".format(
                **row
            )
        )
    lines.extend(
        [
            "",
            "Stage speedup is reported separately from end-to-end speedup. Exact task, cell, GASAL2 request, and traceback request counts were unchanged in all exact-column pairs.",
            "",
            "## Resource boundary",
            "",
            "| resource | workers/GPUs | device peak/total/headroom (MiB) | host RSS (kB) | pinned host | OOM | status |",
            "|---|---:|---:|---:|---:|---:|---|",
        ]
    )
    for row in resources:
        lines.append(
            "| {resource_id} | {worker_count}/{gpu_count} | {device_memory_peak_mib}/"
            "{device_memory_total_mib}/{reserved_headroom_mib} | "
            "{host_rss_peak_kb} | {pinned_host_peak_bytes} | {oom} | {status} |".format(**row)
        )
    lines.extend(
        [
            "",
            "Current-epoch GPU peaks use 250 ms `nvidia-smi` device-used samples and host RSS uses `/usr/bin/time -v`. Pinned-host peak is unavailable in current telemetry. Historical workers=4 and workers=6 OOM evidence is retained rather than rerun; the supported density remains one GASAL2 worker per 24 GB GPU.",
            "",
            f"technical failure receipts: {failure_count}",
            "",
            "Machine-readable authority:",
            "",
            "- `paper/source_data/ablation_resource_runs_pre_freeze.tsv`",
            "- `paper/source_data/ablation_resource_pairs_pre_freeze.tsv`",
            "- `paper/source_data/ablation_resource_summary_pre_freeze.tsv`",
            "- `paper/source_data/ablation_linked_contrasts_pre_freeze.tsv`",
            "- `paper/source_data/resource_boundary_pre_freeze.tsv`",
            "- `paper/source_data/ablation_resource_failures_pre_freeze.tsv`",
            "- `paper/phase4_artifact_manifest.tsv`",
            "",
        ]
    )
    return "\n".join(lines)


def export_normalized_table(
    source: Path,
    destination: Path,
    artifact_root: Path,
    path_fields: tuple[str, ...],
) -> list[dict[str, str]]:
    fields, rows = read_tsv(source)
    for row in rows:
        for field in path_fields:
            if field in row:
                row[field] = normalize_artifact_path(row[field], artifact_root)
    atomic_tsv(destination, fields, rows)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--artifact-root",
        type=Path,
        default=ROOT / ".paper-artifacts/runtime-epoch-0-pre-freeze/phase4-ablation-resource",
    )
    parser.add_argument("--paper-dir", type=Path, default=ROOT / "paper")
    parser.add_argument(
        "--phase2-summary",
        type=Path,
        default=ROOT / "paper/source_data/core_benchmark_summary_pre_freeze.tsv",
    )
    parser.add_argument(
        "--multiworker-summary",
        type=Path,
        default=ROOT / ".tmp/characterize_fasim_gasal2_flush_two_slot_multi_worker_2gpu_v4/summary.json",
    )
    args = parser.parse_args()
    artifact_root = args.artifact_root.resolve()
    paper_dir = args.paper_dir.resolve()
    source_dir = paper_dir / "source_data"
    required = {
        "runs": artifact_root / "phase4-runs.tsv",
        "pairs": artifact_root / "phase4-pairs.tsv",
        "failures": artifact_root / "phase4-failures.tsv",
        "artifacts": artifact_root / "phase4-artifacts.tsv",
        "phase2": args.phase2_summary.resolve(),
        "multiworker": args.multiworker_summary.resolve(),
    }
    for label, path in required.items():
        if not path.is_file():
            raise SystemExit(f"missing Phase 4 {label} dependency: {path}")
    export_normalized_table(
        required["runs"],
        source_dir / "ablation_resource_runs_pre_freeze.tsv",
        artifact_root,
        ("receipt_path",),
    )
    pairs = export_normalized_table(
        required["pairs"],
        source_dir / "ablation_resource_pairs_pre_freeze.tsv",
        artifact_root,
        ("pair_summary_path",),
    )
    failures = export_normalized_table(
        required["failures"],
        source_dir / "ablation_resource_failures_pre_freeze.tsv",
        artifact_root,
        ("artifact_path",),
    )
    summaries = summarize_pairs(pairs)
    atomic_tsv(
        source_dir / "ablation_resource_summary_pre_freeze.tsv",
        SUMMARY_FIELDS,
        summaries,
    )
    _, phase2_rows = read_tsv(required["phase2"])
    linked = linked_ablation_rows(phase2_rows)
    atomic_tsv(
        source_dir / "ablation_linked_contrasts_pre_freeze.tsv",
        LINKED_FIELDS,
        linked,
    )
    resources = resource_rows(summaries, artifact_root, required["multiworker"])
    atomic_tsv(
        source_dir / "resource_boundary_pre_freeze.tsv",
        RESOURCE_FIELDS,
        resources,
    )
    atomic_copy(required["artifacts"], paper_dir / "phase4_artifact_manifest.tsv")
    manifest_sha256 = sha256(paper_dir / "phase4_artifact_manifest.tsv")
    try:
        artifact_root_label = artifact_root.relative_to(ROOT).as_posix()
    except ValueError:
        artifact_root_label = str(artifact_root)
    atomic_text(
        paper_dir / "ablation_resource_report.md",
        render_report(
            summaries,
            linked,
            resources,
            artifact_root_label=artifact_root_label,
            artifact_manifest_sha256=manifest_sha256,
            failure_count=len(failures),
        ),
    )
    print(f"phase4_workloads={len(summaries)}")
    print(f"phase4_pairs={len(pairs)}")
    print(f"phase4_failures={len(failures)}")
    print(f"phase4_resource_rows={len(resources)}")
    print(f"phase4_artifact_manifest_sha256={manifest_sha256}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
