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
from check_fasim_gpu_dp_column_hg38_score_mismatch_fix import (  # noqa: E402
    HG38_CHR21_SOFTMASK_COMPACT_REGION_Z,
    decode_fixture,
    write_fasta,
)


REQUIRED_KEYS = [
    "fasim_ssw_avx2_requested",
    "fasim_ssw_avx2_compiled",
    "fasim_ssw_avx2_active",
    "fasim_ssw_avx2_calls",
    "fasim_ssw_avx2_byte_calls",
    "fasim_ssw_avx2_word_calls",
    "fasim_ssw_avx2_fallback_calls",
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


def require_avx2_active(run: RunResult) -> None:
    require_metrics(run.metrics, REQUIRED_KEYS)
    if metric_int(run.metrics, "fasim_ssw_avx2_requested") != 1:
        raise RuntimeError("SSW AVX2 path was not requested")
    if metric_int(run.metrics, "fasim_ssw_avx2_compiled") != 1:
        raise RuntimeError("SSW AVX2 path is not compiled into this binary")
    if metric_int(run.metrics, "fasim_ssw_avx2_active") != 1:
        raise RuntimeError("SSW AVX2 path was not active")
    if metric_int(run.metrics, "fasim_ssw_avx2_calls") <= 0:
        raise RuntimeError("SSW AVX2 path did not observe calls")
    if metric_int(run.metrics, "fasim_ssw_avx2_byte_calls") <= 0:
        raise RuntimeError("SSW AVX2 byte path did not observe calls")
    if metric_int(run.metrics, "fasim_ssw_avx2_fallback_calls") != 0:
        raise RuntimeError("SSW AVX2 path unexpectedly fell back")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cuda-bin", required=True)
    parser.add_argument(
        "--work-dir",
        default=str(ROOT / ".tmp" / "fasim_ssw_avx2_check"),
    )
    args = parser.parse_args()

    cuda_bin = Path(args.cuda_bin)
    if not cuda_bin.is_absolute():
        cuda_bin = (ROOT / cuda_bin).resolve()
    if not cuda_bin.exists():
        raise RuntimeError(f"missing CUDA Fasim binary: {cuda_bin}")

    work_dir = Path(args.work_dir)
    if not work_dir.is_absolute():
        work_dir = (ROOT / work_dir).resolve()
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
        "small hg38 soft-mask fixture with SSW AVX2 coverage",
        dna_path=dna_path,
        rna_path=ROOT / "H19.fa",
    )

    common_env = {
        "FASIM_TRANSFERSTRING_TABLE": "1",
        "FASIM_GPU_DP_COLUMN_AUTO": "1",
        "FASIM_GPU_DP_COLUMN_AUTO_MIN_WINDOWS": "1",
        "FASIM_GPU_DP_COLUMN_AUTO_MIN_CELLS": "1",
        "FASIM_ALIGNER_ALIGN_INTERNALS": "1",
        "FASIM_SSW_PROFILE_CACHE": "1",
    }
    table = run_once(
        workload=workload,
        mode=ModeSpec("table_only", "cuda", {"FASIM_TRANSFERSTRING_TABLE": "1"}),
        bin_path=cuda_bin,
        work_dir=work_dir / workload.label / "table_only",
        require_profile=True,
    )
    avx2 = run_once(
        workload=workload,
        mode=ModeSpec(
            "ssw_avx2",
            "cuda",
            dict(common_env, FASIM_SSW_AVX2="1"),
        ),
        bin_path=cuda_bin,
        work_dir=work_dir / workload.label / "ssw_avx2",
        require_profile=True,
    )

    require_digest_match(table, avx2, "ssw_avx2")
    require_avx2_active(avx2)

    print("Fasim SSW AVX2 checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
