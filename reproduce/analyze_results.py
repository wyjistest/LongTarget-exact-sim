#!/usr/bin/env python3
"""Compute reproducible paired paper statistics from frozen source data."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
import statistics
import tempfile
import os
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SEED = 20260715
DEFAULT_RESAMPLES = 10000
SUMMARY_FIELDS = [
    "data_freeze_id",
    "runtime_epoch",
    "runtime_commit",
    "machine_id",
    "workload_id",
    "claim_id",
    "preset_id",
    "output_contract",
    "n",
    "median_baseline_wall_seconds",
    "baseline_wall_q1_seconds",
    "baseline_wall_q3_seconds",
    "baseline_wall_min_seconds",
    "baseline_wall_max_seconds",
    "median_candidate_wall_seconds",
    "candidate_wall_q1_seconds",
    "candidate_wall_q3_seconds",
    "candidate_wall_min_seconds",
    "candidate_wall_max_seconds",
    "median_paired_speedup",
    "paired_speedup_q1",
    "paired_speedup_q3",
    "paired_speedup_min",
    "paired_speedup_max",
    "paired_speedup_bootstrap_ci_low",
    "paired_speedup_bootstrap_ci_high",
    "contract_clean_pairs",
    "contract_clean_fraction",
    "analysis_seed",
    "bootstrap_resamples",
]


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            raise ValueError(f"missing TSV header: {path}")
        return list(reader)


def atomic_tsv(path: Path, fields: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", newline="", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
        temporary = Path(handle.name)
    os.replace(temporary, path)


def atomic_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
        temporary = Path(handle.name)
    os.replace(temporary, path)


def percentile(values: list[float], probability: float) -> float:
    if not values:
        raise ValueError("cannot compute percentile of empty values")
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = probability * (len(ordered) - 1)
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def bootstrap_median_ci(
    values: list[float], *, seed: int, resamples: int
) -> tuple[float | str, float | str]:
    if len(values) < 3:
        return "NA", "NA"
    if resamples < 1:
        raise ValueError("bootstrap resamples must be positive")
    generator = random.Random(seed)
    medians = [
        statistics.median(generator.choices(values, k=len(values)))
        for _ in range(resamples)
    ]
    return percentile(medians, 0.025), percentile(medians, 0.975)


def spread(values: list[float]) -> tuple[float, float, float, float]:
    if len(values) == 1:
        return values[0], values[0], values[0], values[0]
    quartiles = statistics.quantiles(sorted(values), n=4, method="inclusive")
    return min(values), quartiles[0], quartiles[2], max(values)


def number(row: dict[str, str], field: str) -> float:
    raw = row.get(field, "")
    try:
        value = float(raw)
    except ValueError as exc:
        raise ValueError(f"{row.get('pair_id_text', 'pair')}: invalid {field}={raw!r}") from exc
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{row.get('pair_id_text', 'pair')}: non-positive {field}={raw!r}")
    return value


def summarize_pairs(
    rows: list[dict[str, str]], *, seed: int, resamples: int
) -> list[dict[str, object]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    seen_pairs: set[str] = set()
    for row in rows:
        pair_id = row.get("pair_id_text", "")
        if not pair_id or pair_id in seen_pairs:
            raise ValueError(f"duplicate pair: {pair_id!r}")
        seen_pairs.add(pair_id)
        if row.get("excluded") not in {"0", "1"}:
            raise ValueError(f"invalid exclusion flag: {pair_id}")
        if row["excluded"] == "0":
            grouped[row["workload_id"]].append(row)

    summaries: list[dict[str, object]] = []
    compatibility = (
        "data_freeze_id",
        "runtime_epoch",
        "runtime_commit",
        "machine_id",
        "claim_id",
        "preset_id",
        "output_contract",
    )
    for workload_id in sorted(grouped):
        group = sorted(grouped[workload_id], key=lambda row: int(row["pair_id"]))
        for field in compatibility:
            if len({row[field] for row in group}) != 1:
                raise ValueError(f"{workload_id}: pair compatibility mismatch in {field}")
        baseline = [number(row, "baseline_wall_seconds") for row in group]
        candidate = [number(row, "candidate_wall_seconds") for row in group]
        speedups = [number(row, "paired_speedup") for row in group]
        for row, base, cand, observed in zip(group, baseline, candidate, speedups, strict=True):
            expected = base / cand
            if not math.isclose(observed, expected, rel_tol=1e-12, abs_tol=1e-12):
                raise ValueError(f"speedup arithmetic mismatch: {row['pair_id_text']}")
        base_min, base_q1, base_q3, base_max = spread(baseline)
        cand_min, cand_q1, cand_q3, cand_max = spread(candidate)
        speed_min, speed_q1, speed_q3, speed_max = spread(speedups)
        workload_seed = seed ^ int(
            hashlib.sha256(workload_id.encode()).hexdigest()[:8], 16
        )
        ci_low, ci_high = bootstrap_median_ci(
            speedups, seed=workload_seed, resamples=resamples
        )
        clean = sum(row["status"] == "clean" for row in group)
        summaries.append(
            {
                **{field: group[0][field] for field in compatibility},
                "workload_id": workload_id,
                "n": len(group),
                "median_baseline_wall_seconds": statistics.median(baseline),
                "baseline_wall_q1_seconds": base_q1,
                "baseline_wall_q3_seconds": base_q3,
                "baseline_wall_min_seconds": base_min,
                "baseline_wall_max_seconds": base_max,
                "median_candidate_wall_seconds": statistics.median(candidate),
                "candidate_wall_q1_seconds": cand_q1,
                "candidate_wall_q3_seconds": cand_q3,
                "candidate_wall_min_seconds": cand_min,
                "candidate_wall_max_seconds": cand_max,
                "median_paired_speedup": statistics.median(speedups),
                "paired_speedup_q1": speed_q1,
                "paired_speedup_q3": speed_q3,
                "paired_speedup_min": speed_min,
                "paired_speedup_max": speed_max,
                "paired_speedup_bootstrap_ci_low": ci_low,
                "paired_speedup_bootstrap_ci_high": ci_high,
                "contract_clean_pairs": clean,
                "contract_clean_fraction": clean / len(group),
                "analysis_seed": seed,
                "bootstrap_resamples": resamples if len(group) >= 3 else 0,
            }
        )
    return summaries


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--pairs",
        type=Path,
        default=ROOT / "paper/source_data/paired_speedups.tsv",
    )
    parser.add_argument(
        "--summary-tsv",
        type=Path,
        default=ROOT / "paper/source_data/paired_speedup_summary.tsv",
    )
    parser.add_argument(
        "--summary-json",
        type=Path,
        default=ROOT / "paper/source_data/paired_speedup_summary.json",
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--resamples", type=int, default=DEFAULT_RESAMPLES)
    args = parser.parse_args()
    rows = read_tsv(args.pairs)
    summaries = summarize_pairs(rows, seed=args.seed, resamples=args.resamples)
    atomic_tsv(args.summary_tsv, SUMMARY_FIELDS, summaries)
    atomic_json(
        args.summary_json,
        {
            "schema_version": 1,
            "analysis_seed": args.seed,
            "bootstrap_resamples": args.resamples,
            "workloads": summaries,
        },
    )
    print(f"analyzed_pairs={sum(int(row['n']) for row in summaries)}")
    print(f"analyzed_workloads={len(summaries)}")
    print(f"bootstrap_seed={args.seed}")
    print(f"bootstrap_resamples={args.resamples}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
