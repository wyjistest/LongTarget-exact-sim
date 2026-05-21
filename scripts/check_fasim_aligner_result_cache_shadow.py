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


RESULT_CACHE_KEYS = [
    "fasim_aligner_result_cache_shadow_enabled",
    "fasim_aligner_result_cache_calls",
    "fasim_aligner_result_cache_unique_keys",
    "fasim_aligner_result_cache_duplicate_calls",
    "fasim_aligner_result_cache_duplicate_fraction",
    "fasim_aligner_result_cache_duplicate_cells",
    "fasim_aligner_result_cache_est_seconds_saved",
    "fasim_aligner_result_cache_memory_bytes_est",
    "fasim_aligner_result_cache_score_mismatches",
    "fasim_aligner_result_cache_endpoint_mismatches",
    "fasim_aligner_result_cache_cigar_mismatches",
    "fasim_aligner_result_cache_digest_mismatches",
    "fasim_aligner_result_cache_first_mismatch_key",
]

RESULT_CACHE_MISMATCH_KEYS = [
    "fasim_aligner_result_cache_score_mismatches",
    "fasim_aligner_result_cache_endpoint_mismatches",
    "fasim_aligner_result_cache_cigar_mismatches",
    "fasim_aligner_result_cache_digest_mismatches",
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


def require_digest_match(expected: RunResult, observed: RunResult, label: str) -> None:
    if expected.digest != observed.digest:
        raise RuntimeError(f"{label}: digest mismatch: {expected.digest} vs {observed.digest}")
    if expected.records != observed.records:
        raise RuntimeError(f"{label}: record mismatch: {expected.records} vs {observed.records}")


def make_final_stack_env() -> Dict[str, str]:
    return {
        "FASIM_TRANSFERSTRING_TABLE": "1",
        "FASIM_GPU_DP_COLUMN_AUTO": "1",
        "FASIM_GPU_DP_COLUMN_AUTO_MIN_WINDOWS": "1",
        "FASIM_GPU_DP_COLUMN_AUTO_MIN_CELLS": "1",
        "FASIM_SSW_PROFILE_CACHE": "1",
        "FASIM_SSW_AVX2": "1",
        "FASIM_SSW_PROFILE_CONTEXT": "1",
        "FASIM_EXACT_COLUMN_EXTEND_BATCH": "1",
    }


def run_workload(cuda_bin: Path, work_dir: Path, workload: WorkloadSpec) -> None:
    final_stack_env = make_final_stack_env()
    table = run_once(
        workload=workload,
        mode=ModeSpec("table_only", "cuda", {"FASIM_TRANSFERSTRING_TABLE": "1"}),
        bin_path=cuda_bin,
        work_dir=work_dir / workload.label / "table_only",
        require_profile=True,
    )
    default = run_once(
        workload=workload,
        mode=ModeSpec("final_stack", "cuda", final_stack_env),
        bin_path=cuda_bin,
        work_dir=work_dir / workload.label / "final_stack",
        require_profile=True,
    )
    shadow = run_once(
        workload=workload,
        mode=ModeSpec(
            "result_cache_shadow",
            "cuda",
            dict(final_stack_env, FASIM_ALIGNER_RESULT_CACHE_SHADOW="1"),
        ),
        bin_path=cuda_bin,
        work_dir=work_dir / workload.label / "result_cache_shadow",
        require_profile=True,
    )

    require_digest_match(table, default, f"{workload.label}/final_stack")
    require_digest_match(table, shadow, f"{workload.label}/result_cache_shadow")
    require_metrics(default.metrics, RESULT_CACHE_KEYS)
    require_metrics(shadow.metrics, RESULT_CACHE_KEYS)

    if metric_int(default.metrics, "fasim_aligner_result_cache_shadow_enabled") != 0:
        raise RuntimeError(f"{workload.label}: result-cache shadow unexpectedly enabled")
    if metric_int(shadow.metrics, "fasim_aligner_result_cache_shadow_enabled") != 1:
        raise RuntimeError(f"{workload.label}: result-cache shadow was not enabled")

    calls = metric_int(shadow.metrics, "fasim_aligner_result_cache_calls")
    unique = metric_int(shadow.metrics, "fasim_aligner_result_cache_unique_keys")
    duplicates = metric_int(shadow.metrics, "fasim_aligner_result_cache_duplicate_calls")
    if calls <= 0:
        raise RuntimeError(f"{workload.label}: no aligner calls observed")
    if unique <= 0:
        raise RuntimeError(f"{workload.label}: no result-cache keys observed")
    if unique + duplicates != calls:
        raise RuntimeError(
            f"{workload.label}: cache accounting mismatch: "
            f"unique={unique} duplicates={duplicates} calls={calls}"
        )
    fraction = metric_float(shadow.metrics, "fasim_aligner_result_cache_duplicate_fraction")
    expected_fraction = duplicates / calls
    if abs(fraction - expected_fraction) > 0.000001:
        raise RuntimeError(
            f"{workload.label}: duplicate fraction mismatch: "
            f"{fraction} vs {expected_fraction}"
        )
    if metric_int(shadow.metrics, "fasim_aligner_result_cache_duplicate_cells") < 0:
        raise RuntimeError(f"{workload.label}: negative duplicate cell count")
    if metric_float(shadow.metrics, "fasim_aligner_result_cache_est_seconds_saved") < 0.0:
        raise RuntimeError(f"{workload.label}: negative estimated savings")
    if metric_int(shadow.metrics, "fasim_aligner_result_cache_memory_bytes_est") <= 0:
        raise RuntimeError(f"{workload.label}: missing memory estimate")

    for key in RESULT_CACHE_MISMATCH_KEYS:
        if metric_int(shadow.metrics, key) != 0:
            raise RuntimeError(f"{workload.label}: expected {key}=0, got {shadow.metrics[key]}")
    if metric_int(shadow.metrics, "fasim_aligner_result_cache_first_mismatch_key") != 0:
        raise RuntimeError(f"{workload.label}: unexpected first mismatch key")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cuda-bin", required=True)
    parser.add_argument(
        "--work-dir",
        default=str(ROOT / ".tmp" / "fasim_aligner_result_cache_shadow"),
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

    run_workload(
        cuda_bin,
        work_dir,
        WorkloadSpec(
            "tiny",
            "tiny sample fixture with emitted fastSIM records",
            dna_path=ROOT / "testDNA.fa",
            rna_path=ROOT / "H19.fa",
        ),
    )
    print("Fasim aligner result-cache shadow checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
