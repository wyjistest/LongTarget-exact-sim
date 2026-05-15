#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Dict


ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from benchmark_fasim_gpu_dp_column_characterization import (  # noqa: E402
    ModeSpec,
    RunResult,
    WorkloadSpec,
    median_count,
    run_once,
)


VALIDATION_KEYS = (
    "fasim_gpu_dp_column_score_mismatches",
    "fasim_gpu_dp_column_column_max_mismatches",
    "fasim_gpu_dp_column_scoreinfo_mismatches",
    "fasim_gpu_dp_column_compact_scoreinfo_mismatches",
    "fasim_gpu_dp_column_fallbacks",
)


def require_count(metrics: Dict[str, str], key: str, expected: int) -> None:
    try:
        observed = int(round(float(metrics[key])))
    except KeyError as exc:
        raise RuntimeError(f"missing metric {key}") from exc
    except ValueError as exc:
        raise RuntimeError(f"non-numeric metric {key}={metrics[key]!r}") from exc
    if observed != expected:
        raise RuntimeError(f"{key}: expected {expected}, got {observed}")


def require_digest_match(table: RunResult, auto: RunResult, label: str) -> None:
    if table.digest != auto.digest:
        raise RuntimeError(
            f"{label}: digest mismatch between table-only and auto: "
            f"{table.digest} vs {auto.digest}"
        )
    if table.records != auto.records:
        raise RuntimeError(
            f"{label}: record count mismatch between table-only and auto: "
            f"{table.records} vs {auto.records}"
        )


def run_mode(
    *,
    workload: WorkloadSpec,
    mode: ModeSpec,
    cuda_bin: Path,
    work_dir: Path,
) -> RunResult:
    return run_once(
        workload=workload,
        mode=mode,
        bin_path=cuda_bin,
        work_dir=work_dir / workload.label / mode.label,
        require_profile=True,
    )


def check_below_threshold(cuda_bin: Path, work_dir: Path) -> None:
    workload = WorkloadSpec("tiny", "current testDNA/H19 smoke fixture", dna_entries=1)
    table = run_mode(
        workload=workload,
        mode=ModeSpec("table_only", "cuda", {"FASIM_TRANSFERSTRING_TABLE": "1"}),
        cuda_bin=cuda_bin,
        work_dir=work_dir,
    )
    auto = run_mode(
        workload=workload,
        mode=ModeSpec(
            "auto",
            "cuda",
            {
                "FASIM_TRANSFERSTRING_TABLE": "1",
                "FASIM_GPU_DP_COLUMN_AUTO": "1",
            },
        ),
        cuda_bin=cuda_bin,
        work_dir=work_dir,
    )
    require_digest_match(table, auto, workload.label)

    metrics = auto.metrics
    require_count(metrics, "fasim_gpu_dp_column_auto_requested", 1)
    require_count(metrics, "fasim_gpu_dp_column_auto_active", 0)
    require_count(metrics, "fasim_gpu_dp_column_auto_min_cells", 1_500_000_000)
    require_count(metrics, "fasim_gpu_dp_column_auto_min_windows", 128)
    require_count(metrics, "fasim_gpu_dp_column_auto_observed_cells", 49_108_768)
    require_count(metrics, "fasim_gpu_dp_column_auto_observed_windows", 4)
    require_count(metrics, "fasim_gpu_dp_column_auto_threshold_matched", 0)
    require_count(metrics, "fasim_gpu_dp_column_auto_disabled_reason", 1)
    require_count(metrics, "fasim_gpu_dp_column_auto_selected_path", 0)
    require_count(metrics, "fasim_gpu_dp_column_active", 0)
    require_count(metrics, "fasim_gpu_dp_column_compact_scoreinfo_active", 0)


def check_above_threshold(cuda_bin: Path, work_dir: Path) -> None:
    workload = WorkloadSpec(
        "window_heavy_synthetic",
        "32-entry deterministic testDNA/H19 scale-up",
        dna_entries=32,
    )
    table = run_mode(
        workload=workload,
        mode=ModeSpec("table_only", "cuda", {"FASIM_TRANSFERSTRING_TABLE": "1"}),
        cuda_bin=cuda_bin,
        work_dir=work_dir,
    )
    auto = run_mode(
        workload=workload,
        mode=ModeSpec(
            "auto_validate",
            "cuda",
            {
                "FASIM_TRANSFERSTRING_TABLE": "1",
                "FASIM_GPU_DP_COLUMN_AUTO": "1",
                "FASIM_GPU_DP_COLUMN_VALIDATE": "1",
            },
        ),
        cuda_bin=cuda_bin,
        work_dir=work_dir,
    )
    require_digest_match(table, auto, workload.label)

    metrics = auto.metrics
    require_count(metrics, "fasim_gpu_dp_column_auto_requested", 1)
    require_count(metrics, "fasim_gpu_dp_column_auto_active", 1)
    require_count(metrics, "fasim_gpu_dp_column_auto_min_cells", 1_500_000_000)
    require_count(metrics, "fasim_gpu_dp_column_auto_min_windows", 128)
    require_count(metrics, "fasim_gpu_dp_column_auto_observed_cells", 1_571_480_576)
    require_count(metrics, "fasim_gpu_dp_column_auto_observed_windows", 128)
    require_count(metrics, "fasim_gpu_dp_column_auto_threshold_matched", 1)
    require_count(metrics, "fasim_gpu_dp_column_auto_disabled_reason", 0)
    require_count(metrics, "fasim_gpu_dp_column_auto_selected_path", 1)
    require_count(metrics, "fasim_gpu_dp_column_active", 1)
    require_count(metrics, "fasim_gpu_dp_column_compact_scoreinfo_active", 1)
    for key in VALIDATION_KEYS:
        require_count(metrics, key, 0)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cuda-bin", required=True)
    parser.add_argument(
        "--work-dir",
        default=str(ROOT / ".tmp" / "fasim_gpu_dp_column_auto_policy"),
    )
    args = parser.parse_args()

    cuda_bin = Path(args.cuda_bin)
    if not cuda_bin.is_absolute():
        cuda_bin = (ROOT / cuda_bin).resolve()
    if not cuda_bin.exists():
        raise RuntimeError(f"missing CUDA Fasim binary: {cuda_bin}")

    work_dir = Path(args.work_dir)
    check_below_threshold(cuda_bin, work_dir)
    check_above_threshold(cuda_bin, work_dir)
    print("Fasim GPU DP+column auto policy checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
