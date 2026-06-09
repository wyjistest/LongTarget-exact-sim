#!/usr/bin/env python3
"""Validate the recorded chr21+chr22 GASAL2 preAlign max-tasks probe."""

from __future__ import annotations

import csv
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WORK = (
    ROOT / ".tmp" / "characterize_fasim_gasal2_prealign_max_tasks_probe_chr21_chr22_current"
)


def _load_summary(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        raise SystemExit(f"missing summary: {path}")
    rows = list(csv.DictReader(path.open(newline="", encoding="utf-8"), delimiter="\t"))
    if not rows:
        raise SystemExit(f"empty summary: {path}")
    return {row["label"]: row for row in rows}


def _load_decision(path: Path) -> dict[str, str]:
    if not path.exists():
        raise SystemExit(f"missing decision: {path}")
    decision: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            decision[key] = value
    return decision


def _as_int(row: dict[str, str], key: str) -> int:
    return int(float(row[key]))


def _as_float(row: dict[str, str], key: str) -> float:
    return float(row[key])


def _require_clean_payload(row: dict[str, str]) -> None:
    for key in (
        "topk_payload_equal_vs_formal",
        "topk_rows_payload_equal_vs_formal",
        "topk_lite_equal_vs_formal",
    ):
        if row[key] != "true":
            raise SystemExit(f"{row['label']} has non-clean {key}: {row}")


def _require_active_clean(row: dict[str, str]) -> None:
    _require_clean_payload(row)
    if row["scoreinfo_rank_observe_enabled_shards"] != row["shard_count"]:
        raise SystemExit(f"{row['label']} rank observe not enabled per shard: {row}")
    if _as_int(row, "scoreinfo_rank_observe_rows") <= 0:
        raise SystemExit(f"{row['label']} rank observe rows are empty: {row}")
    if _as_int(row, "scoreinfo_rank_observe_unknown_rows") != 0:
        raise SystemExit(f"{row['label']} has unknown rank rows: {row}")
    if _as_int(row, "scoreinfo_rank_observe_max_rank") <= 0:
        raise SystemExit(f"{row['label']} has no observed rank max: {row}")
    if _as_int(row, "gasal2_requests") <= 0:
        raise SystemExit(f"{row['label']} has no GASAL2 requests: {row}")
    if _as_int(row, "gasal2_traceback_requests") <= 0:
        raise SystemExit(f"{row['label']} has no GASAL2 traceback requests: {row}")
    if _as_int(row, "exact_scoreinfo_gpu_tasks") <= 0:
        raise SystemExit(f"{row['label']} has no exact scoreInfo GPU tasks: {row}")
    if _as_int(row, "exact_scoreinfo_gpu_overflow_batches") != 0:
        raise SystemExit(f"{row['label']} has exact scoreInfo overflow batches: {row}")
    if _as_int(row, "exact_scoreinfo_gpu_fallback_batches") != 0:
        raise SystemExit(f"{row['label']} has exact scoreInfo fallback batches: {row}")


def main() -> int:
    work = Path(os.environ.get("WORK", str(DEFAULT_WORK)))
    rows = _load_summary(work / "summary.tsv")
    decision = _load_decision(work / "decision.txt")

    required_labels = ("formal_default", "max16384", "max32768")
    missing = [label for label in required_labels if label not in rows]
    if missing:
        raise SystemExit(f"missing rows: {', '.join(missing)}")

    formal = rows["formal_default"]
    max16384 = rows["max16384"]
    max32768 = rows["max32768"]

    if formal["result_contract"] != "gasal2_top5_column_pruned_scoreinfo_artifact_v1":
        raise SystemExit(f"formal row has unexpected contract: {formal}")
    if formal["prealign_cuda_max_tasks"] != "8192":
        raise SystemExit(f"pre-promotion formal row is not the expected 8192 preset: {formal}")
    for row, value in ((max16384, "16384"), (max32768, "32768")):
        if row["result_contract"] != "gasal2_top5_scoreinfo_artifact_v1":
            raise SystemExit(f"{row['label']} has unexpected contract: {row}")
        if row["prealign_cuda_max_tasks"] != value:
            raise SystemExit(f"{row['label']} has unexpected max-tasks value: {row}")

    for row in (formal, max16384, max32768):
        _require_active_clean(row)

    formal_batches = _as_int(formal, "exact_scoreinfo_gpu_batches")
    max16384_batches = _as_int(max16384, "exact_scoreinfo_gpu_batches")
    max32768_batches = _as_int(max32768, "exact_scoreinfo_gpu_batches")
    if max16384_batches >= formal_batches:
        raise SystemExit(
            f"max16384 did not reduce exact batches: {max16384_batches} >= {formal_batches}"
        )
    if max32768_batches >= max16384_batches:
        raise SystemExit(
            f"max32768 did not reduce exact batches: {max32768_batches} >= {max16384_batches}"
        )

    formal_wall = _as_float(formal, "wall_seconds")
    max16384_wall = _as_float(max16384, "wall_seconds")
    if max16384_wall >= formal_wall:
        raise SystemExit(
            f"max16384 did not improve wall time: {max16384_wall} >= {formal_wall}"
        )
    if _as_float(max16384, "speedup_vs_formal") <= 1.0:
        raise SystemExit(f"max16384 speedup is not positive vs formal: {max16384}")

    if decision.get("best_top5_clean_label") != "max16384":
        raise SystemExit(f"unexpected best label: {decision}")
    if decision.get("best_top5_clean_prealign_cuda_max_tasks") != "16384":
        raise SystemExit(f"unexpected best max-tasks value: {decision}")
    if int(decision.get("best_top5_clean_exact_scoreinfo_gpu_batches", "0")) != max16384_batches:
        raise SystemExit(f"decision exact batch count does not match summary: {decision}")

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
