#!/usr/bin/env python3
"""Independently audit frozen paper arithmetic without importing the analyzer."""

from __future__ import annotations

import argparse
import csv
import math
import os
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]


def median(values: Iterable[float]) -> float:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("median requires at least one value")
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2.0


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def recomputed_pair_speedups(rows: Iterable[dict[str, str]]) -> list[float]:
    values: list[float] = []
    for row in rows:
        baseline = float(row["baseline_wall_seconds"])
        candidate = float(row["candidate_wall_seconds"])
        reported = float(row["paired_speedup"])
        if baseline <= 0 or candidate <= 0:
            raise ValueError(f"non-positive pair timing: {row['pair_id_text']}")
        actual = baseline / candidate
        if not math.isclose(actual, reported, rel_tol=1e-12, abs_tol=1e-12):
            raise ValueError(f"paired speedup drift: {row['pair_id_text']}")
        values.append(actual)
    return values


def storage_ratio(row: dict[str, str]) -> float:
    legacy = float(row["legacy_text_bytes"])
    archive = float(row["archive_bytes"])
    if min(legacy, archive) <= 0:
        raise ValueError("storage byte counts must be positive")
    return legacy / archive


def stage_speedup(row: dict[str, str]) -> float:
    baseline = float(row["baseline_exact_stage_seconds"])
    candidate = float(row["candidate_exact_stage_seconds"])
    if min(baseline, candidate) <= 0:
        raise ValueError("exact-stage timings must be positive")
    return baseline / candidate


def audit_row(metric: str, workload: str, actual: float, frozen: float, source: str) -> dict[str, str]:
    difference = abs(actual - frozen)
    if not math.isclose(actual, frozen, rel_tol=5e-7, abs_tol=5e-7):
        raise ValueError(f"frozen arithmetic drift: {metric} {workload}: {actual} != {frozen}")
    return {
        "metric_id": metric,
        "workload_id": workload,
        "recomputed_value": f"{actual:.12f}",
        "frozen_value": f"{frozen:.12f}",
        "absolute_difference": f"{difference:.12g}",
        "status": "match",
        "source": source,
    }


def build_audit(source: Path, tables: Path) -> list[dict[str, str]]:
    pairs = read_tsv(source / "paired_speedups.tsv")
    summaries = {row["workload_id"]: row for row in read_tsv(source / "paired_speedup_summary.tsv")}
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in pairs:
        if row["excluded"] == "0":
            grouped[row["workload_id"]].append(row)
    if set(grouped) != set(summaries):
        raise ValueError("paired workload set differs from frozen summary")

    output: list[dict[str, str]] = []
    for workload in sorted(grouped):
        rows = grouped[workload]
        speedups = recomputed_pair_speedups(rows)
        actual = median(speedups)
        frozen = float(summaries[workload]["median_paired_speedup"])
        output.append(audit_row("median_paired_speedup", workload, actual, frozen, "paired_speedups.tsv"))
        reductions = [
            (float(row["baseline_wall_seconds"]) - float(row["candidate_wall_seconds"]))
            / float(row["baseline_wall_seconds"])
            for row in rows
        ]
        reduction = median(reductions)
        output.append({
            "metric_id": "median_wall_reduction_fraction",
            "workload_id": workload,
            "recomputed_value": f"{reduction:.12f}",
            "frozen_value": "derived_independently",
            "absolute_difference": "NA",
            "status": "derived",
            "source": "paired_speedups.tsv",
        })

    ablation = {row["workload_id"]: row for row in read_tsv(source / "ablation.tsv")}
    archive_rows = [row for row in read_tsv(source / "archive_first.tsv") if row["row_type"] == "archive_restore"]
    ratios = [storage_ratio(row) for row in archive_rows]
    for row, actual in zip(archive_rows, ratios):
        if not math.isclose(actual, float(row["storage_reduction_ratio"]), rel_tol=1e-12, abs_tol=1e-12):
            raise ValueError(f"archive row ratio drift: {row['pair_id_text']}")
    storage_median = median(ratios)
    output.append(audit_row(
        "median_storage_reduction_ratio", "c5_archive_h19_2mb", storage_median,
        float(ablation["c5_archive_h19_2mb"]["median_storage_reduction_ratio"]),
        "archive_first.tsv",
    ))

    phase4_pairs = read_tsv(source / "ablation_resource_pairs_pre_freeze.tsv")
    for workload in ("c6_exact_h19_2mb", "c6_exact_kcnq_segment_chr22"):
        rows = [row for row in phase4_pairs if row["workload_id"] == workload]
        values = [stage_speedup(row) for row in rows]
        for row, actual in zip(rows, values):
            if not math.isclose(actual, float(row["exact_stage_speedup"]), rel_tol=1e-12, abs_tol=1e-12):
                raise ValueError(f"exact-stage row ratio drift: {row['pair_id_text']}")
        stage_median = median(values)
        output.append(audit_row(
            "median_exact_stage_speedup", workload, stage_median,
            float(ablation[workload]["median_exact_stage_speedup"]),
            "ablation_resource_pairs_pre_freeze.tsv",
        ))
        output.append({
            "metric_id": "median_exact_stage_reduction_fraction",
            "workload_id": workload,
            "recomputed_value": f"{median([1.0 - 1.0 / value for value in values]):.12f}",
            "frozen_value": "derived_independently",
            "absolute_difference": "NA",
            "status": "derived",
            "source": "ablation_resource_pairs_pre_freeze.tsv",
        })

    table4 = {(row["workload_id"], row["metric"]): row for row in read_tsv(tables / "table4_ablation_resources.tsv")}
    checks = (
        ("c5_archive_h19_2mb", "storage_reduction_ratio", storage_median),
        ("c6_exact_h19_2mb", "exact_stage_speedup", float(ablation["c6_exact_h19_2mb"]["median_exact_stage_speedup"])),
        ("c6_exact_kcnq_segment_chr22", "exact_stage_speedup", float(ablation["c6_exact_kcnq_segment_chr22"]["median_exact_stage_speedup"])),
    )
    for workload, metric, actual in checks:
        frozen = float(table4[(workload, metric)]["value"])
        output.append(audit_row(f"table4_{metric}", workload, actual, frozen, "table4_ablation_resources.tsv"))
    return output


def write_tsv(path: Path, rows: list[dict[str, str]]) -> None:
    fields = [
        "metric_id", "workload_id", "recomputed_value", "frozen_value",
        "absolute_difference", "status", "source",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", newline="", encoding="utf-8", dir=path.parent, delete=False) as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
        temporary = Path(handle.name)
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=Path, default=ROOT / "paper/source_data")
    parser.add_argument("--table-dir", type=Path, default=ROOT / "paper/tables")
    parser.add_argument("--output", type=Path, default=ROOT / "paper/independent_arithmetic_audit.tsv")
    args = parser.parse_args()
    rows = build_audit(args.source_dir, args.table_dir)
    write_tsv(args.output, rows)
    print(f"independent_arithmetic_rows={len(rows)}")
    print("independent_arithmetic_audit=pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
