#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from statistics import median


PREDICTORS = [
    ("gasal2_requests", "benchmark.fasim_gasal2_requests"),
    ("traceback_requests", "benchmark.fasim_gasal2_traceback_requests"),
    ("gasal2_total_seconds", "benchmark.fasim_gasal2_total_seconds"),
    ("convert_seconds", "benchmark.fasim_gasal2_cpu_traceback_convert_seconds"),
    ("gasal2_rows", None),
    ("archive_bytes", None),
    ("gzip_bytes", None),
]


def _float(value: object, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _pearson(xs: list[float], ys: list[float]) -> float:
    if len(xs) != len(ys) or len(xs) < 2:
        return 0.0
    x_mean = sum(xs) / len(xs)
    y_mean = sum(ys) / len(ys)
    x_dev = [x - x_mean for x in xs]
    y_dev = [y - y_mean for y in ys]
    num = sum(a * b for a, b in zip(x_dev, y_dev))
    den_x = math.sqrt(sum(a * a for a in x_dev))
    den_y = math.sqrt(sum(b * b for b in y_dev))
    if den_x == 0.0 or den_y == 0.0:
        return 0.0
    return num / (den_x * den_y)


def _load_overlap(path: Path) -> dict[str, dict[str, float]]:
    rows: dict[str, dict[str, float]] = {}
    with path.open("rt", newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            chrom = row["chrom"]
            if chrom.startswith("TOTAL"):
                continue
            rows[chrom] = {
                "fasim_wall_seconds": _float(row.get("fasim_wall_seconds")),
                "speedup": _float(row.get("speedup")),
                "gasal2_rows": _float(row.get("gasal2_rows")),
                "fasim_rows": _float(row.get("fasim_rows")),
                "common_rows": _float(row.get("common_rows")),
                "overlap_vs_fasim": _float(row.get("overlap_vs_fasim")),
                "jaccard": _float(row.get("jaccard")),
            }
    return rows


def _metric(metrics: dict[str, str], key: str) -> float:
    return _float(metrics.get(key))


def _decision(max_to_median: float, top_1_fraction: float, top_3_fraction: float) -> str:
    if max_to_median >= 2.0 or top_1_fraction >= 0.20 or top_3_fraction >= 0.45:
        return "material_tail_latency"
    return "tail_latency_not_material"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Summarize GASAL2-LongTarget shard tail latency and predictor correlations."
    )
    parser.add_argument("--gasal2-summary", required=True, type=Path)
    parser.add_argument("--overlap-tsv", required=True, type=Path)
    parser.add_argument("--output-tsv", required=True, type=Path)
    parser.add_argument("--output-summary", required=True, type=Path)
    args = parser.parse_args()

    gasal2 = json.loads(args.gasal2_summary.read_text())
    overlap = _load_overlap(args.overlap_tsv)
    rows: list[dict[str, float | str]] = []
    for shard in gasal2.get("shards", []):
        chrom = shard.get("chrom")
        if not chrom:
            continue
        metrics = shard.get("metrics") or {}
        overlap_row = overlap.get(str(chrom), {})
        row: dict[str, float | str] = {
            "chrom": str(chrom),
            "gasal2_wall_seconds": _float(shard.get("wall_seconds")),
            "archive_bytes": _float(shard.get("archive_bytes")),
            "gzip_bytes": _float(shard.get("archive_gzip_bytes")),
            "gasal2_requests": _metric(metrics, "benchmark.fasim_gasal2_requests"),
            "traceback_requests": _metric(metrics, "benchmark.fasim_gasal2_traceback_requests"),
            "gasal2_total_seconds": _metric(metrics, "benchmark.fasim_gasal2_total_seconds"),
            "score_wait_seconds": _metric(metrics, "benchmark.fasim_gasal2_score_wait_seconds"),
            "traceback_wait_seconds": _metric(metrics, "benchmark.fasim_gasal2_traceback_wait_seconds"),
            "convert_seconds": _metric(metrics, "benchmark.fasim_gasal2_cpu_traceback_convert_seconds"),
            "gasal2_rows": overlap_row.get("gasal2_rows", 0.0),
            "fasim_rows": overlap_row.get("fasim_rows", 0.0),
            "common_rows": overlap_row.get("common_rows", 0.0),
            "overlap_vs_fasim": overlap_row.get("overlap_vs_fasim", 0.0),
            "jaccard": overlap_row.get("jaccard", 0.0),
            "fasim_wall_seconds": overlap_row.get("fasim_wall_seconds", 0.0),
            "speedup": overlap_row.get("speedup", 0.0),
        }
        rows.append(row)

    if not rows:
        raise SystemExit("no shard rows found")

    total_wall = sum(_float(row["gasal2_wall_seconds"]) for row in rows)
    for row in rows:
        row["wall_fraction"] = (
            _float(row["gasal2_wall_seconds"]) / total_wall if total_wall > 0.0 else 0.0
        )
        row["requests_per_second"] = (
            _float(row["gasal2_requests"]) / _float(row["gasal2_wall_seconds"])
            if _float(row["gasal2_wall_seconds"]) > 0.0
            else 0.0
        )
        row["tracebacks_per_second"] = (
            _float(row["traceback_requests"]) / _float(row["gasal2_wall_seconds"])
            if _float(row["gasal2_wall_seconds"]) > 0.0
            else 0.0
        )

    walls = [_float(row["gasal2_wall_seconds"]) for row in rows]
    med_wall = median(walls)
    max_wall = max(walls)
    max_to_median = max_wall / med_wall if med_wall > 0.0 else 0.0
    sorted_by_wall = sorted(rows, key=lambda row: _float(row["gasal2_wall_seconds"]), reverse=True)
    top_1_fraction = _float(sorted_by_wall[0]["wall_fraction"])
    top_3_fraction = sum(_float(row["wall_fraction"]) for row in sorted_by_wall[:3])
    top_5_fraction = sum(_float(row["wall_fraction"]) for row in sorted_by_wall[:5])

    correlations: dict[str, float] = {}
    for name, metric_key in PREDICTORS:
        values = []
        for row in rows:
            if metric_key is None:
                values.append(_float(row.get(name)))
            else:
                values.append(_float(row.get(name)))
        correlations[name] = _pearson(walls, values)
    best_predictor = max(correlations, key=lambda key: abs(correlations[key]))

    args.output_tsv.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "chrom",
        "gasal2_wall_seconds",
        "wall_fraction",
        "gasal2_requests",
        "traceback_requests",
        "gasal2_rows",
        "speedup",
        "requests_per_second",
        "tracebacks_per_second",
        "convert_seconds",
        "archive_bytes",
        "gzip_bytes",
        "overlap_vs_fasim",
        "jaccard",
    ]
    with args.output_tsv.open("wt", newline="") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=fieldnames)
        writer.writeheader()
        for row in sorted_by_wall:
            writer.writerow(
                {
                    key: (
                        f"{_float(row[key]):.6f}"
                        if key != "chrom"
                        else row[key]
                    )
                    for key in fieldnames
                }
            )

    summary_lines = [
        f"shards={len(rows)}",
        f"gasal2_outer_wall_seconds={_float(gasal2.get('outer_wall_seconds')):.6f}",
        f"sum_shard_wall_seconds={total_wall:.6f}",
        f"median_shard_wall_seconds={med_wall:.6f}",
        f"max_shard_wall_seconds={max_wall:.6f}",
        f"max_shard={sorted_by_wall[0]['chrom']}",
        f"max_to_median_wall_ratio={max_to_median:.6f}",
        f"top_1_shards_wall_fraction={top_1_fraction:.6f}",
        f"top_3_shards_wall_fraction={top_3_fraction:.6f}",
        f"top_5_shards_wall_fraction={top_5_fraction:.6f}",
        f"tail_latency_decision={_decision(max_to_median, top_1_fraction, top_3_fraction)}",
        f"best_wall_predictor={best_predictor}",
    ]
    for key in sorted(correlations):
        summary_lines.append(f"wall_corr_{key}={correlations[key]:.6f}")
    summary_lines.extend(
        [
            f"total_gasal2_requests={sum(_float(row['gasal2_requests']) for row in rows):.0f}",
            f"total_traceback_requests={sum(_float(row['traceback_requests']) for row in rows):.0f}",
            f"total_gasal2_rows={sum(_float(row['gasal2_rows']) for row in rows):.0f}",
            f"total_archive_bytes={sum(_float(row['archive_bytes']) for row in rows):.0f}",
            f"total_gzip_bytes={sum(_float(row['gzip_bytes']) for row in rows):.0f}",
        ]
    )
    args.output_summary.parent.mkdir(parents=True, exist_ok=True)
    args.output_summary.write_text("\n".join(summary_lines) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
