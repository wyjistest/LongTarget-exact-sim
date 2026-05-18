#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
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
from check_fasim_gpu_dp_column_hg38_score_mismatch_fix import (  # noqa: E402
    HG38_CHR21_SOFTMASK_COMPACT_REGION_Z,
    decode_fixture,
    write_fasta,
)


REQUIRED_THRESHOLD_KEYS = [
    "fasim_gpu_dp_column_threshold_gpu_windows",
    "fasim_gpu_dp_column_threshold_cpu_windows",
    "fasim_gpu_dp_column_threshold_cpu_seconds",
    "fasim_gpu_dp_column_threshold_shadow_enabled",
    "fasim_gpu_dp_column_threshold_shadow_compared_windows",
    "fasim_gpu_dp_column_threshold_shadow_mismatches",
    "fasim_gpu_dp_column_threshold_shadow_delta_max",
]


def metric_int(metrics: Dict[str, str], key: str) -> int:
    try:
        return int(round(float(metrics[key])))
    except KeyError as exc:
        raise RuntimeError(f"missing metric {key}") from exc
    except ValueError as exc:
        raise RuntimeError(f"non-numeric metric {key}={metrics[key]!r}") from exc


def require_metrics(metrics: Dict[str, str], keys: Iterable[str]) -> None:
    for key in keys:
        metric_int(metrics, key)


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
        default=str(ROOT / ".tmp" / "fasim_gpu_auto_threshold_topk_telemetry"),
    )
    args = parser.parse_args()

    cuda_bin = Path(args.cuda_bin)
    if not cuda_bin.is_absolute():
        cuda_bin = (ROOT / cuda_bin).resolve()
    if not cuda_bin.exists():
        raise RuntimeError(f"missing CUDA Fasim binary: {cuda_bin}")

    work_dir = Path(args.work_dir)
    fixture_dir = work_dir / "fixtures"
    fixture_dir.mkdir(parents=True, exist_ok=True)
    dna_path = fixture_dir / "hg38_chr21_softmask_compact_region.fa"
    write_fasta(
        dna_path,
        "hg38|chr21|41825001-41830000",
        decode_fixture(HG38_CHR21_SOFTMASK_COMPACT_REGION_Z),
    )
    workload = WorkloadSpec(
        "hg38_chr21_softmask_compact_region",
        "small hg38 soft-mask fixture with true N threshold and compact overflow coverage",
        dna_path=dna_path,
        rna_path=ROOT / "H19.fa",
    )

    table = run_once(
        workload=workload,
        mode=ModeSpec("table_only", "cuda", {"FASIM_TRANSFERSTRING_TABLE": "1"}),
        bin_path=cuda_bin,
        work_dir=work_dir / workload.label / "table_only",
        require_profile=True,
    )
    auto_validate = run_once(
        workload=workload,
        mode=ModeSpec(
            "auto_validate_shadow",
            "cuda",
            {
                "FASIM_TRANSFERSTRING_TABLE": "1",
                "FASIM_GPU_DP_COLUMN_AUTO": "1",
                "FASIM_GPU_DP_COLUMN_AUTO_MIN_WINDOWS": "1",
                "FASIM_GPU_DP_COLUMN_AUTO_MIN_CELLS": "1",
                "FASIM_GPU_DP_COLUMN_VALIDATE": "1",
                "FASIM_GPU_DP_COLUMN_THRESHOLD_SHADOW": "1",
                "FASIM_GPU_DP_COLUMN_TOPK_CAP": "4",
            },
        ),
        bin_path=cuda_bin,
        work_dir=work_dir / workload.label / "auto_validate_shadow",
        require_profile=True,
    )

    require_digest_match(table, auto_validate, "auto_validate_shadow")
    require_metrics(auto_validate.metrics, REQUIRED_THRESHOLD_KEYS)
    if metric_int(auto_validate.metrics, "fasim_gpu_dp_column_threshold_shadow_enabled") != 1:
        raise RuntimeError("threshold shadow mode did not report enabled")
    if metric_int(auto_validate.metrics, "fasim_gpu_dp_column_threshold_cpu_windows") <= 0:
        raise RuntimeError("fixture did not exercise CPU threshold windows")
    if metric_int(auto_validate.metrics, "fasim_gpu_dp_column_threshold_shadow_compared_windows") <= 0:
        raise RuntimeError("threshold shadow did not compare any windows")
    if metric_int(auto_validate.metrics, "fasim_gpu_dp_column_validate_windows_failed") != 0:
        raise RuntimeError("validation failed in telemetry check")

    sweep_report = work_dir / "topk_sweep_report.md"
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "benchmark_fasim_gpu_dp_column_auto_hg38_validation_taxonomy.py"),
            "--cuda-bin",
            str(cuda_bin),
            "--dna",
            str(dna_path),
            "--rna",
            str(ROOT / "H19.fa"),
            "--label",
            "hg38_chr21_softmask_compact_region",
            "--repeat",
            "1",
            "--work-dir",
            str(work_dir / "topk_sweep"),
            "--output",
            str(sweep_report),
            "--require-profile",
            "--check",
            "--auto-min-windows",
            "1",
            "--auto-min-cells",
            "1",
            "--topk-sweep",
            "4,8",
        ],
        cwd=ROOT,
        check=True,
    )
    report_text = sweep_report.read_text(encoding="utf-8")
    for expected in [
        "## Threshold Source",
        "## TopK Sweep",
        "| TopK | AUTO+validate seconds | Exact extends | Compact fallback windows | Digest match | Validation failed windows |",
        "| 4 |",
        "| 8 |",
    ]:
        if expected not in report_text:
            raise RuntimeError(f"missing TopK sweep report text: {expected}")

    print("Fasim GPU AUTO threshold/topK telemetry checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
