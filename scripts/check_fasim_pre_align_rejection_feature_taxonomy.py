#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Dict, Iterable


ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from benchmark_fasim_gpu_dp_column_characterization import (  # noqa: E402
    ModeSpec,
    RunResult,
    WorkloadSpec,
    run_once,
)


REQUIRED_KEYS = [
    "fasim_pre_align_feature_sweep_enabled",
    "fasim_pre_align_feature_sweep_rules_tested",
    "fasim_pre_align_feature_sweep_best_zero_false_reject_rule",
    "fasim_pre_align_feature_sweep_best_predicted_reject",
    "fasim_pre_align_feature_sweep_best_true_reject",
    "fasim_pre_align_feature_sweep_best_false_reject",
    "fasim_pre_align_feature_sweep_best_false_keep",
    "fasim_pre_align_feature_sweep_best_est_calls_saved",
    "fasim_pre_align_feature_sweep_best_est_cells_saved",
    "fasim_pre_align_feature_sweep_best_est_seconds_saved",
    "fasim_pre_align_feature_emitted_score_mean",
    "fasim_pre_align_feature_rejected_score_mean",
    "fasim_pre_align_feature_emitted_rank_mean",
    "fasim_pre_align_feature_rejected_rank_mean",
    "fasim_pre_align_feature_emitted_target_len_mean",
    "fasim_pre_align_feature_rejected_target_len_mean",
    "fasim_pre_align_feature_emitted_align_calls_mean",
    "fasim_pre_align_feature_rejected_align_calls_mean",
]


def metric_float(metrics: Dict[str, str], key: str) -> float:
    try:
        return float(metrics[key])
    except KeyError as exc:
        raise RuntimeError(f"missing metric {key}") from exc
    except ValueError as exc:
        raise RuntimeError(f"non-numeric metric {key}={metrics[key]!r}") from exc


def metric_int(metrics: Dict[str, str], key: str) -> int:
    return int(round(metric_float(metrics, key)))


def require_metrics(metrics: Dict[str, str], keys: Iterable[str]) -> None:
    for key in keys:
        metric_float(metrics, key)


def require_digest_match(table: RunResult, observed: RunResult, label: str) -> None:
    if table.digest != observed.digest:
        raise RuntimeError(f"{label}: digest mismatch: {table.digest} vs {observed.digest}")
    if table.records != observed.records:
        raise RuntimeError(f"{label}: record mismatch: {table.records} vs {observed.records}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cuda-bin", required=True)
    parser.add_argument(
        "--work-dir",
        default=str(ROOT / ".tmp" / "fasim_pre_align_rejection_feature_taxonomy"),
    )
    args = parser.parse_args()

    cuda_bin = Path(args.cuda_bin)
    if not cuda_bin.is_absolute():
        cuda_bin = (ROOT / cuda_bin).resolve()
    if not cuda_bin.exists():
        raise RuntimeError(f"missing CUDA Fasim binary: {cuda_bin}")

    work_dir = Path(args.work_dir)
    workload = WorkloadSpec(
        "testDNA_H19_feature_sweep",
        "small smoke fixture with emitted and rejected fastSIM candidates",
        dna_path=ROOT / "testDNA.fa",
        rna_path=ROOT / "H19.fa",
    )

    table = run_once(
        workload=workload,
        mode=ModeSpec("table_only", "cuda", {"FASIM_TRANSFERSTRING_TABLE": "1"}),
        bin_path=cuda_bin,
        work_dir=work_dir / workload.label / "table_only",
        require_profile=True,
    )
    auto = run_once(
        workload=workload,
        mode=ModeSpec(
            "auto",
            "cuda",
            {
                "FASIM_TRANSFERSTRING_TABLE": "1",
                "FASIM_GPU_DP_COLUMN_AUTO": "1",
                "FASIM_GPU_DP_COLUMN_AUTO_MIN_WINDOWS": "1",
                "FASIM_GPU_DP_COLUMN_AUTO_MIN_CELLS": "1",
                "FASIM_PRE_ALIGN_FILTER_SHADOW": "1",
                "FASIM_PRE_ALIGN_FEATURE_SWEEP": "1",
            },
        ),
        bin_path=cuda_bin,
        work_dir=work_dir / workload.label / "auto",
        require_profile=True,
    )
    require_digest_match(table, auto, "auto")
    require_metrics(auto.metrics, REQUIRED_KEYS)

    if metric_int(auto.metrics, "fasim_pre_align_feature_sweep_enabled") != 1:
        raise RuntimeError("pre-align feature sweep was not enabled")
    if metric_int(auto.metrics, "fasim_pre_align_feature_sweep_rules_tested") <= 0:
        raise RuntimeError("pre-align feature sweep did not test any rules")
    if metric_int(auto.metrics, "fasim_pre_align_filter_output_digest_affected") != 0:
        raise RuntimeError("pre-align feature sweep must not affect output digest")

    print("Fasim pre-align rejection feature taxonomy checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
