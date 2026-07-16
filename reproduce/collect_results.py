#!/usr/bin/env python3
"""Collect Phase 2-4 receipts into the frozen paper source-data schema."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import tempfile
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_COMMIT = "0d11aa2d61b7ccda59b462ab8e0750dad17ee18f"
RUNTIME_EPOCH = 0
DEFAULT_FREEZE_ID = "paper-data-v1-dccfd49-20260716"
PHASES = {
    "phase2": {
        "root": ROOT / ".paper-artifacts/runtime-epoch-0-pre-freeze/phase2-core",
        "runs": "core_benchmark_runs_pre_freeze.tsv",
        "pairs": "core_benchmark_pairs_pre_freeze.tsv",
        "failures": "core_benchmark_failures_pre_freeze.tsv",
        "manifest": ROOT / "paper/phase2_artifact_manifest.tsv",
    },
    "phase3": {
        "root": ROOT / ".paper-artifacts/runtime-epoch-0-pre-freeze/phase3-generalization",
        "runs": "generalization_runs_pre_freeze.tsv",
        "pairs": "generalization_pairs_pre_freeze.tsv",
        "failures": "generalization_failures_pre_freeze.tsv",
        "manifest": ROOT / "paper/phase3_artifact_manifest.tsv",
    },
    "phase4": {
        "root": ROOT / ".paper-artifacts/runtime-epoch-0-pre-freeze/phase4-ablation-resource",
        "runs": "ablation_resource_runs_pre_freeze.tsv",
        "pairs": "ablation_resource_pairs_pre_freeze.tsv",
        "failures": "ablation_resource_failures_pre_freeze.tsv",
        "manifest": ROOT / "paper/phase4_artifact_manifest.tsv",
    },
}
PAIR_FIELDS = [
    "data_freeze_id",
    "runtime_epoch",
    "runtime_commit",
    "machine_id",
    "workload_id",
    "claim_id",
    "role",
    "query_id",
    "query_length_nt",
    "target_id",
    "pair_id",
    "pair_id_text",
    "pair_order",
    "preset_id",
    "output_contract",
    "baseline_wall_seconds",
    "candidate_wall_seconds",
    "paired_speedup",
    "status",
    "decision",
    "excluded",
    "exclusion_reason",
    "artifact_path",
    "artifact_sha256",
    "source_phase",
]
RUN_FIELDS = [
    "data_freeze_id",
    "runtime_epoch",
    "runtime_commit",
    "machine_id",
    "workload_id",
    "claim_id",
    "pair_id",
    "run_id",
    "mode",
    "role",
    "output_contract",
    "wall_seconds",
    "exact_stage_seconds",
    "cpu_finalizer_seconds",
    "host_scheduling_overlap_seconds",
    "peak_gpu_memory_bytes",
    "peak_rss_kb",
    "gasal2_requests",
    "traceback_requests",
    "fallbacks",
    "length_guard_fallbacks",
    "runtime_batch_fallbacks",
    "overflow_fallbacks",
    "top5_score_equal",
    "top5_stability_equal",
    "top5_nt_equal",
    "boundary_ties_equal",
    "full_output_byte_equal",
    "missing_rows",
    "extra_rows",
    "status",
    "excluded",
    "exclusion_reason",
    "config_digest_sha256",
    "artifact_path",
    "artifact_sha256",
    "source_phase",
]
CORRECTNESS_FIELDS = [
    "data_freeze_id",
    "workload_id",
    "claim_id",
    "pair_id_text",
    "row_type",
    "top5_score_equal",
    "top5_stability_equal",
    "top5_nt_equal",
    "boundary_ties_equal",
    "full_output_byte_equal",
    "missing_rows",
    "extra_rows",
    "fallbacks",
    "overflow_fallbacks",
    "oom",
    "supported",
    "guard_reason",
    "gpu_fast_path_executed",
    "status",
    "artifact_path",
    "artifact_sha256",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_tsv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            raise ValueError(f"missing TSV header: {path}")
        return reader.fieldnames, list(reader)


def write_tsv(path: Path, fields: list[str], rows: Iterable[dict[str, object]]) -> None:
    normalized = []
    for source in rows:
        normalized.append(
            {
                field: "NA" if source.get(field, "NA") in {None, ""} else source.get(field)
                for field in fields
            }
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", newline="", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(normalized)
        temporary = Path(handle.name)
    os.replace(temporary, path)


def load_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON object required: {path}")
    return payload


def machine_id(environment: dict[str, object]) -> str:
    lscpu = environment.get("lscpu")
    nvidia = environment.get("nvidia_smi")
    lscpu_text = str(lscpu.get("stdout", "")) if isinstance(lscpu, dict) else ""
    nvidia_text = str(nvidia.get("stdout", "")) if isinstance(nvidia, dict) else ""
    cpu_match = re.search(r"^Model name:\s*(.+)$", lscpu_text, re.MULTILINE)
    driver_match = re.search(r"^Driver Version\s*:\s*(.+)$", nvidia_text, re.MULTILINE)
    products = sorted(
        re.findall(r"^\s*Product Name\s*:\s*(.+)$", nvidia_text, re.MULTILINE)
    )
    stable = {
        "platform": environment.get("platform", "NA"),
        "cpu_model": cpu_match.group(1).strip() if cpu_match else "NA",
        "driver": driver_match.group(1).strip() if driver_match else "NA",
        "gpu_products": products,
    }
    encoded = json.dumps(stable, sort_keys=True, separators=(",", ":")).encode()
    return "machine-" + hashlib.sha256(encoded).hexdigest()[:12]


def manifest_rows(path: Path) -> dict[str, dict[str, str]]:
    _, rows = read_tsv(path)
    result = {row["workload_id"]: row for row in rows}
    if len(result) != len(rows):
        raise ValueError("duplicate workload manifest ID")
    return result


def normalize_pair(
    row: dict[str, str],
    manifest: dict[str, dict[str, str]],
    *,
    data_freeze_id: str,
    machine: str,
    artifact_sha256: str,
    artifact_path: str | None = None,
    source_phase: str = "test",
) -> dict[str, object]:
    workload = row["workload_id"]
    if workload not in manifest:
        raise ValueError(f"pair workload absent from manifest: {workload}")
    frozen = manifest[workload]
    observed_preset = row.get("preset_id") or frozen["preset_id"]
    if observed_preset != frozen["preset_id"]:
        raise ValueError(f"preset drift in {row['pair_id_text']}")
    frozen_contract = frozen.get("output_contract")
    if frozen_contract and row["output_contract"] != frozen_contract:
        raise ValueError(f"output contract drift in {row['pair_id_text']}")
    if row["runtime_epoch"] != str(RUNTIME_EPOCH) or row["runtime_commit"] != RUNTIME_COMMIT:
        raise ValueError(f"runtime epoch mixing in {row['pair_id_text']}")
    return {
        "data_freeze_id": data_freeze_id,
        "runtime_epoch": row["runtime_epoch"],
        "runtime_commit": row["runtime_commit"],
        "machine_id": machine,
        "workload_id": workload,
        "claim_id": row["claim_id"],
        "role": row.get("role") or frozen["role"],
        "query_id": row.get("query_id") or frozen["query_id"],
        "query_length_nt": row.get("query_length_nt") or frozen["query_length_nt"],
        "target_id": row.get("target_id") or frozen["target_id"],
        "pair_id": row["pair_id"],
        "pair_id_text": row["pair_id_text"],
        "pair_order": row["pair_order"],
        "preset_id": observed_preset,
        "output_contract": row["output_contract"],
        "baseline_wall_seconds": row["baseline_wall_seconds"],
        "candidate_wall_seconds": row["candidate_wall_seconds"],
        "paired_speedup": row["paired_speedup"],
        "status": row["status"],
        "decision": row["decision"],
        "excluded": 0,
        "exclusion_reason": "NA",
        "artifact_path": artifact_path or row["pair_summary_path"],
        "artifact_sha256": artifact_sha256,
        "source_phase": source_phase,
    }


def pick(row: dict[str, str], *fields: str, default: str = "NA") -> str:
    for field in fields:
        value = row.get(field, "")
        if value not in {"", "NA"}:
            return value
    return default


def pair_correctness(row: dict[str, str]) -> dict[str, str]:
    return {
        "top5_score_equal": pick(row, "top5_score_equal", "clustered_score_top5_equal"),
        "top5_stability_equal": pick(
            row, "top5_stability_equal", "clustered_stability_top5_equal"
        ),
        "top5_nt_equal": pick(row, "top5_nt_score_equal", "clustered_nt_top5_equal"),
        "boundary_ties_equal": pick(row, "boundary_ties_equal"),
        "full_output_byte_equal": pick(row, "full_output_byte_equal"),
        "missing_rows": pick(row, "missing_rows", "full_missing_rows"),
        "extra_rows": pick(row, "extra_rows", "full_extra_rows"),
        "fallbacks": pick(row, "fallbacks", default="0"),
        "overflow_fallbacks": pick(
            row, "candidate_overflow_batches", "overflow_fallbacks", "overflow_batches", default="0"
        ),
        "oom": pick(row, "oom", default="0"),
    }


def metric(metrics: dict[str, object], key: str, default: str = "NA") -> str:
    value = metrics.get(key, default)
    return str(value) if value not in {None, ""} else default


def stage_sum(metrics: dict[str, object]) -> float | str:
    keys = (
        "benchmark.fasim_top5_gasal2_phase_exact_column_wall_seconds",
        "benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_wall_seconds",
    )
    found = [float(metrics[key]) for key in keys if key in metrics]
    return sum(found) if found else "NA"


def artifact_run_dir(root: Path, receipt_relative: str) -> Path:
    receipt = Path(receipt_relative)
    if receipt.is_absolute():
        raise ValueError(f"machine-specific receipt path in final source input: {receipt}")
    return (root / receipt).parent


def run_machine(root: Path, receipt_relative: str) -> str:
    run_dir = artifact_run_dir(root, receipt_relative)
    return machine_id(load_json(run_dir / "environment.json"))


def collect_pairs(
    source_dir: Path,
    workload_manifest: dict[str, dict[str, str]],
    data_freeze_id: str,
) -> tuple[list[dict[str, object]], dict[tuple[str, str], dict[str, str]]]:
    output: list[dict[str, object]] = []
    correctness: dict[tuple[str, str], dict[str, str]] = {}
    seen: set[str] = set()
    for phase, config in PHASES.items():
        root = Path(config["root"])
        _, rows = read_tsv(source_dir / str(config["pairs"]))
        for row in rows:
            pair_id = row["pair_id_text"]
            if pair_id in seen:
                raise ValueError(f"duplicate pair across phases: {pair_id}")
            seen.add(pair_id)
            summary_relative = row["pair_summary_path"]
            summary_path = root / summary_relative
            if not summary_path.is_file():
                raise ValueError(f"missing pair summary artifact: {summary_path}")
            baseline_receipt = root / f"{row['workload_id']}__pair{int(row['pair_id']):02d}__baseline__0/run-complete.json"
            machine = machine_id(load_json(baseline_receipt.with_name("environment.json"))) if baseline_receipt.with_name("environment.json").is_file() else run_machine(
                root,
                f"{row['workload_id']}__pair{int(row['pair_id']):02d}__baseline__0/run-complete.json",
            )
            output.append(
                normalize_pair(
                    row,
                    workload_manifest,
                    data_freeze_id=data_freeze_id,
                    machine=machine,
                    artifact_sha256=sha256(summary_path),
                    artifact_path=f"{phase}:{summary_relative}",
                    source_phase=phase,
                )
            )
            correctness[(row["workload_id"], row["pair_id"])] = {
                **pair_correctness(row),
                "status": row["status"],
                "claim_id": row["claim_id"],
                "pair_id_text": pair_id,
                "artifact_path": f"{phase}:{summary_relative}",
                "artifact_sha256": sha256(summary_path),
            }
    return output, correctness


def collect_runs(
    source_dir: Path,
    workload_manifest: dict[str, dict[str, str]],
    pair_status: dict[tuple[str, str], dict[str, str]],
    data_freeze_id: str,
) -> list[dict[str, object]]:
    output: list[dict[str, object]] = []
    seen: set[str] = set()
    for phase, config in PHASES.items():
        root = Path(config["root"])
        _, rows = read_tsv(source_dir / str(config["runs"]))
        for row in rows:
            run_id = row["run_id"]
            if run_id in seen:
                raise ValueError(f"duplicate run ID across phases: {run_id}")
            seen.add(run_id)
            frozen = workload_manifest[row["workload_id"]]
            run_dir = artifact_run_dir(root, row["receipt_path"])
            receipt = run_dir / "run-complete.json"
            summary = load_json(run_dir / "summary.json")
            metrics = summary.get("benchmark_metrics", {})
            if not isinstance(metrics, dict):
                metrics = {}
            warmup = row.get("warmup") == "1"
            mode = row["mode"]
            guard = mode == "preflight"
            pair = pair_status.get((row["workload_id"], row["pair_id"]), {})
            correctness = pair if not warmup and not guard else {}
            if warmup:
                status, excluded, reason = "warmup", 1, "protocol_warmup"
            elif guard:
                status, excluded, reason = "guarded", 1, "preflight_guard_not_performance"
            else:
                status, excluded, reason = str(pair.get("status", "failed")), 0, "NA"
            gpu_mib = row.get("gpu_memory_peak_mib", "NA")
            gpu_bytes: int | str = "NA"
            if gpu_mib not in {"", "NA"}:
                gpu_bytes = int(round(float(gpu_mib) * 1024 * 1024))
            runtime_fallbacks = metric(metrics, "benchmark.fasim_gasal2_fallbacks", "0")
            length_fallbacks = metric(
                metrics, "benchmark.fasim_gasal2_length_guard_fallbacks", "0"
            )
            batch_fallbacks = metric(
                metrics,
                "benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_fallback_batches",
                "0",
            )
            overflow = metric(
                metrics,
                "benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_overflow_batches",
                "0",
            )
            output.append(
                {
                    "data_freeze_id": data_freeze_id,
                    "runtime_epoch": row["runtime_epoch"],
                    "runtime_commit": RUNTIME_COMMIT,
                    "machine_id": machine_id(load_json(run_dir / "environment.json")),
                    "workload_id": row["workload_id"],
                    "claim_id": row.get("claim_id") or frozen["claim_id"],
                    "pair_id": row["pair_id"],
                    "run_id": run_id,
                    "mode": mode,
                    "role": row.get("role") or frozen["role"],
                    "output_contract": frozen["output_contract"],
                    "wall_seconds": row["wall_seconds"],
                    "exact_stage_seconds": stage_sum(metrics),
                    "cpu_finalizer_seconds": metric(
                        metrics,
                        "benchmark.fasim_gasal2_flush_two_slot_overlap_cpu_finalizer_seconds",
                    ),
                    "host_scheduling_overlap_seconds": metric(
                        metrics,
                        "benchmark.fasim_gasal2_flush_two_slot_overlap_host_scheduling_overlap_seconds",
                    ),
                    "peak_gpu_memory_bytes": gpu_bytes,
                    "peak_rss_kb": row["max_rss_kb"],
                    "gasal2_requests": metric(metrics, "benchmark.fasim_gasal2_requests", "0"),
                    "traceback_requests": metric(
                        metrics, "benchmark.fasim_gasal2_traceback_requests", "0"
                    ),
                    "fallbacks": runtime_fallbacks,
                    "length_guard_fallbacks": length_fallbacks,
                    "runtime_batch_fallbacks": batch_fallbacks,
                    "overflow_fallbacks": overflow,
                    "top5_score_equal": correctness.get("top5_score_equal", "NA"),
                    "top5_stability_equal": correctness.get("top5_stability_equal", "NA"),
                    "top5_nt_equal": correctness.get("top5_nt_equal", "NA"),
                    "boundary_ties_equal": correctness.get("boundary_ties_equal", "NA"),
                    "full_output_byte_equal": correctness.get("full_output_byte_equal", "NA"),
                    "missing_rows": correctness.get("missing_rows", "NA"),
                    "extra_rows": correctness.get("extra_rows", "NA"),
                    "status": status,
                    "excluded": excluded,
                    "exclusion_reason": reason,
                    "config_digest_sha256": row["config_digest_sha256"],
                    "artifact_path": f"{phase}:{row['receipt_path']}",
                    "artifact_sha256": sha256(receipt),
                    "source_phase": phase,
                }
            )
    return output


def collect_correctness(
    pair_status: dict[tuple[str, str], dict[str, str]],
    source_dir: Path,
    data_freeze_id: str,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for (workload, _), pair in sorted(pair_status.items()):
        rows.append(
            {
                "data_freeze_id": data_freeze_id,
                "workload_id": workload,
                "claim_id": pair["claim_id"],
                "pair_id_text": pair["pair_id_text"],
                "row_type": "paired_contract",
                **{field: pair.get(field, "NA") for field in (
                    "top5_score_equal", "top5_stability_equal", "top5_nt_equal",
                    "boundary_ties_equal", "full_output_byte_equal", "missing_rows",
                    "extra_rows", "fallbacks", "overflow_fallbacks", "oom",
                )},
                "supported": "NA",
                "guard_reason": "NA",
                "gpu_fast_path_executed": "NA",
                "status": pair["status"],
                "artifact_path": pair["artifact_path"],
                "artifact_sha256": pair["artifact_sha256"],
            }
        )
    _, guards = read_tsv(source_dir / "generalization_guards_pre_freeze.tsv")
    guard_root = Path(PHASES["phase3"]["root"])
    for guard in guards:
        receipt = guard_root / guard["receipt_path"]
        rows.append(
            {
                "data_freeze_id": data_freeze_id,
                "workload_id": guard["workload_id"],
                "claim_id": "C3",
                "pair_id_text": guard["run_id"],
                "row_type": "preflight_guard",
                "top5_score_equal": "NA",
                "top5_stability_equal": "NA",
                "top5_nt_equal": "NA",
                "boundary_ties_equal": "NA",
                "full_output_byte_equal": "NA",
                "missing_rows": "NA",
                "extra_rows": "NA",
                "fallbacks": 0,
                "overflow_fallbacks": 0,
                "oom": 0,
                "supported": guard["supported"],
                "guard_reason": guard["reason"],
                "gpu_fast_path_executed": guard["gpu_fast_path_executed"],
                "status": guard["status"],
                "artifact_path": f"phase3:{guard['receipt_path']}",
                "artifact_sha256": sha256(receipt),
            }
        )
    return rows


def copy_with_freeze(
    source: Path, destination: Path, data_freeze_id: str, fields: list[str] | None = None
) -> list[dict[str, object]]:
    source_fields, source_rows = read_tsv(source)
    output_fields = fields or ["data_freeze_id", *source_fields]
    output = [{"data_freeze_id": data_freeze_id, **row} for row in source_rows]
    write_tsv(destination, output_fields, output)
    return output


def collect_generalization(source_dir: Path, data_freeze_id: str) -> list[dict[str, object]]:
    _, workloads = read_tsv(source_dir / "generalization_workloads_pre_freeze.tsv")
    _, guards = read_tsv(source_dir / "generalization_guards_pre_freeze.tsv")
    fields = [
        "data_freeze_id", "row_type", "workload_id", "query_id", "query_length_nt",
        "fragment_position", "target_id", "target_region", "role", "valid_pairs",
        "median_paired_speedup", "clustered_score_all_equal",
        "clustered_stability_all_equal", "clustered_nt_all_equal",
        "boundary_ties_all_equal", "fallbacks_total", "oom_total", "supported",
        "guard_reason", "gpu_fast_path_executed", "status",
    ]
    output: list[dict[str, object]] = []
    for row in workloads:
        output.append({"data_freeze_id": data_freeze_id, "row_type": "supported_query", **row})
    for row in guards:
        output.append(
            {
                "data_freeze_id": data_freeze_id,
                "row_type": "full_length_guard",
                **row,
                "role": "negative_control",
                "valid_pairs": 0,
                "median_paired_speedup": "NA",
                "clustered_score_all_equal": "NA",
                "clustered_stability_all_equal": "NA",
                "clustered_nt_all_equal": "NA",
                "boundary_ties_all_equal": "NA",
                "fallbacks_total": 0,
                "oom_total": 0,
                "guard_reason": row["reason"],
            }
        )
    write_tsv(source_dir / "generalization.tsv", fields, output)
    return output


def collect_ablation(source_dir: Path, data_freeze_id: str) -> list[dict[str, object]]:
    _, paired = read_tsv(source_dir / "ablation_resource_summary_pre_freeze.tsv")
    _, linked = read_tsv(source_dir / "ablation_linked_contrasts_pre_freeze.tsv")
    fields = [
        "data_freeze_id", "row_type", "workload_id", "claim_id", "contrast",
        "target_scope", "baseline_configuration", "candidate_configuration",
        "output_contract", "n", "median_baseline_wall_seconds",
        "median_candidate_wall_seconds", "median_paired_speedup",
        "median_exact_stage_speedup", "median_storage_reduction_ratio",
        "median_peak_rss_reduction_fraction", "all_pairs_clean",
        "same_workload_abc_triad", "source_path",
    ]
    output: list[dict[str, object]] = []
    for row in paired:
        output.append(
            {
                "data_freeze_id": data_freeze_id,
                "row_type": "phase4_paired",
                **row,
                "n": row["valid_pairs"],
                "contrast": "NA",
                "target_scope": "NA",
                "baseline_configuration": "NA",
                "candidate_configuration": "NA",
                "same_workload_abc_triad": "NA",
                "source_path": "paper/source_data/ablation_resource_pairs_pre_freeze.tsv",
            }
        )
    for row in linked:
        output.append(
            {
                "data_freeze_id": data_freeze_id,
                "row_type": "linked_contrast",
                **row,
                "claim_id": "C1" if row["contrast"] == "authority_vs_checked_gasal2" else "C4",
                "n": row["valid_pairs"],
                "median_baseline_wall_seconds": "NA",
                "median_candidate_wall_seconds": "NA",
                "median_exact_stage_speedup": "NA",
                "median_storage_reduction_ratio": "NA",
                "median_peak_rss_reduction_fraction": "NA",
                "all_pairs_clean": 1,
            }
        )
    write_tsv(source_dir / "ablation.tsv", fields, output)
    return output


def collect_resources(source_dir: Path, data_freeze_id: str, paired_digest: str) -> None:
    fields, rows = read_tsv(source_dir / "resource_boundary_pre_freeze.tsv")
    for row in rows:
        if row["evidence_sha256"] == "assigned_after_phase5_freeze":
            row["evidence_sha256"] = paired_digest
    write_tsv(
        source_dir / "resources.tsv",
        ["data_freeze_id", *fields],
        [{"data_freeze_id": data_freeze_id, **row} for row in rows],
    )


def collect_archive(source_dir: Path, pairs: list[dict[str, str]], data_freeze_id: str) -> None:
    fields = [
        "data_freeze_id", "workload_id", "pair_id_text", "row_type",
        "baseline_wall_seconds", "candidate_wall_seconds", "paired_speedup",
        "legacy_text_bytes", "archive_bytes", "storage_reduction_ratio",
        "restore_wall_seconds", "candidate_run_restore_wall_seconds",
        "memory_merge_wall_seconds", "sqlite_merge_wall_seconds",
        "memory_peak_rss_kb", "sqlite_peak_rss_kb",
        "peak_rss_reduction_fraction", "full_output_byte_equal", "status",
        "artifact_path", "artifact_sha256",
    ]
    output = []
    for row in pairs:
        if row["claim_id"] != "C5":
            continue
        output.append(
            {
                "data_freeze_id": data_freeze_id,
                **row,
                "row_type": (
                    "archive_restore" if row["workload_id"] == "c5_archive_h19_2mb" else "bounded_exact_merge"
                ),
            }
        )
    write_tsv(source_dir / "archive_first.tsv", fields, output)


def collect_operating(source_dir: Path, data_freeze_id: str) -> None:
    fields = [
        "data_freeze_id", "workload_id", "contract", "scope", "status",
        "row_equal", "top5_equal", "speedup", "fallbacks", "n",
        "source_class", "evidence_path", "evidence_sha256", "notes",
    ]
    _, historical = read_tsv(source_dir / "core_operating_envelope_pre_freeze.tsv")
    _, core = read_tsv(source_dir / "core_benchmark_summary_pre_freeze.tsv")
    output: list[dict[str, object]] = [
        {"data_freeze_id": data_freeze_id, **row} for row in historical
    ]
    max8 = next(row for row in core if row["workload_id"] == "c7_kcnq_max8_chr22")
    output.append(
        {
            "data_freeze_id": data_freeze_id,
            "workload_id": max8["workload_id"],
            "contract": max8["output_contract"],
            "scope": "bounded_max8_dual_grid_chr22",
            "status": "clean_but_below_promotion_gate",
            "row_equal": max8["full_output_contract_clean"],
            "top5_equal": max8["top5_contract_clean"],
            "speedup": max8["median_paired_speedup"],
            "fallbacks": max8["fallbacks_total"],
            "n": max8["valid_pairs"],
            "source_class": "reproduced_current_epoch",
            "evidence_path": "paper/source_data/core_benchmark_pairs_pre_freeze.tsv",
            "evidence_sha256": sha256(source_dir / "core_benchmark_pairs_pre_freeze.tsv"),
            "notes": "Full 121-segment candidate and full hg38 were not run.",
        }
    )
    write_tsv(source_dir / "operating_envelope.tsv", fields, output)


def collect_exclusions(
    source_dir: Path,
    runs: list[dict[str, object]],
    data_freeze_id: str,
) -> None:
    fields = [
        "data_freeze_id", "record_id", "record_type", "workload_id", "status",
        "excluded_from", "exclusion_reason", "rerun_or_replacement", "evidence_path",
        "artifact_sha256", "source_phase",
    ]
    output: list[dict[str, object]] = []
    for row in runs:
        if row["excluded"] != 1:
            continue
        output.append(
            {
                "data_freeze_id": data_freeze_id,
                "record_id": row["run_id"],
                "record_type": "run",
                "workload_id": row["workload_id"],
                "status": row["status"],
                "excluded_from": "paired_performance_statistics",
                "exclusion_reason": row["exclusion_reason"],
                "rerun_or_replacement": "not_applicable",
                "evidence_path": row["artifact_path"],
                "artifact_sha256": row["artifact_sha256"],
                "source_phase": row["source_phase"],
            }
        )
    for phase, config in PHASES.items():
        failure_file = source_dir / str(config["failures"])
        _, failures = read_tsv(failure_file)
        manifest_digest = sha256(Path(config["manifest"]))
        for row in failures:
            output.append(
                {
                    "data_freeze_id": data_freeze_id,
                    "record_id": row.get("run_id", row["artifact_path"]),
                    "record_type": "derived_pair_or_failure",
                    "workload_id": row.get("run_id", "NA").split("__pair", 1)[0],
                    "status": row["status"],
                    "excluded_from": "authoritative_pair_table",
                    "exclusion_reason": row["reason"],
                    "rerun_or_replacement": (
                        "authoritative_later_comparator_receipt"
                        if row["reason"] == "superseded_derived_pair"
                        else "technical_failure_retained"
                    ),
                    "evidence_path": f"{phase}:{row['artifact_path']}",
                    "artifact_sha256": manifest_digest,
                    "source_phase": phase,
                }
            )
    write_tsv(source_dir / "exclusions.tsv", fields, output)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=Path, default=ROOT / "paper/source_data")
    parser.add_argument("--manifest", type=Path, default=ROOT / "paper/workload_manifest.tsv")
    parser.add_argument("--data-freeze-id", default=DEFAULT_FREEZE_ID)
    args = parser.parse_args()
    source_dir = args.source_dir.resolve()
    workload_manifest = manifest_rows(args.manifest)
    pairs, pair_status = collect_pairs(source_dir, workload_manifest, args.data_freeze_id)
    runs = collect_runs(source_dir, workload_manifest, pair_status, args.data_freeze_id)
    correctness = collect_correctness(pair_status, source_dir, args.data_freeze_id)
    write_tsv(source_dir / "paired_speedups.tsv", PAIR_FIELDS, pairs)
    write_tsv(source_dir / "benchmark_runs.tsv", RUN_FIELDS, runs)
    write_tsv(source_dir / "correctness.tsv", CORRECTNESS_FIELDS, correctness)
    collect_generalization(source_dir, args.data_freeze_id)
    collect_ablation(source_dir, args.data_freeze_id)
    collect_resources(source_dir, args.data_freeze_id, sha256(source_dir / "paired_speedups.tsv"))
    _, raw_phase4_pairs = read_tsv(source_dir / "ablation_resource_pairs_pre_freeze.tsv")
    phase4_root = Path(PHASES["phase4"]["root"])
    archive_rows = []
    for row in raw_phase4_pairs:
        pair_path = phase4_root / row["pair_summary_path"]
        archive_rows.append(
            {
                **row,
                "artifact_path": f"phase4:{row['pair_summary_path']}",
                "artifact_sha256": sha256(pair_path),
            }
        )
    collect_archive(source_dir, archive_rows, args.data_freeze_id)
    collect_operating(source_dir, args.data_freeze_id)
    collect_exclusions(source_dir, runs, args.data_freeze_id)
    print(f"data_freeze_id={args.data_freeze_id}")
    print(f"benchmark_runs={len(runs)}")
    print(f"paired_speedups={len(pairs)}")
    print(f"correctness_rows={len(correctness)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
