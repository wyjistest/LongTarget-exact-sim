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


INDEPENDENCE_KEYS = [
    "fasim_fastSIM_precompute_independence_enabled",
    "fasim_fastSIM_precompute_legacy_requests",
    "fasim_fastSIM_precompute_derived_requests",
    "fasim_fastSIM_precompute_request_count_mismatches",
    "fasim_fastSIM_precompute_request_order_mismatches",
    "fasim_fastSIM_precompute_request_field_mismatches",
    "fasim_fastSIM_precompute_state_dependent_requests",
    "fasim_fastSIM_precompute_full_replay_enabled",
    "fasim_fastSIM_precompute_replay_requests",
    "fasim_fastSIM_precompute_cpu_compute_seconds",
    "fasim_fastSIM_precompute_replay_seconds",
    "fasim_fastSIM_precompute_est_parallel_seconds_2t",
    "fasim_fastSIM_precompute_est_parallel_seconds_4t",
    "fasim_fastSIM_precompute_est_parallel_seconds_8t",
    "fasim_fastSIM_precompute_est_parallel_seconds_16t",
    "fasim_fastSIM_precompute_memory_bytes",
]

REQUEST_COMPARISON_KEYS = [
    "fasim_fastSIM_precompute_request_count_mismatches",
    "fasim_fastSIM_precompute_request_order_mismatches",
    "fasim_fastSIM_precompute_request_field_mismatches",
    "fasim_fastSIM_precompute_state_dependent_requests",
]

REPLAY_MISMATCH_KEYS = [
    "fasim_fastSIM_precompute_candidate_state_mismatches",
    "fasim_fastSIM_precompute_emitted_record_mismatches",
    "fasim_fastSIM_precompute_cigar_mismatches",
    "fasim_fastSIM_precompute_digest_mismatches",
    "fasim_fastSIM_precompute_fallbacks",
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
    independence = run_once(
        workload=workload,
        mode=ModeSpec(
            "precompute_independence",
            "cuda",
            dict(
                final_stack_env,
                FASIM_FASTSIM_ALIGN_PRECOMPUTE_SHADOW="1",
                FASIM_FASTSIM_ALIGN_PRECOMPUTE_INDEPENDENCE="1",
            ),
        ),
        bin_path=cuda_bin,
        work_dir=work_dir / workload.label / "precompute_independence",
        require_profile=True,
    )

    require_digest_match(table, default, f"{workload.label}/final_stack")
    require_digest_match(table, independence, f"{workload.label}/precompute_independence")
    require_metrics(default.metrics, INDEPENDENCE_KEYS)
    require_metrics(independence.metrics, INDEPENDENCE_KEYS)

    if metric_int(default.metrics, "fasim_fastSIM_precompute_independence_enabled") != 0:
        raise RuntimeError(f"{workload.label}: independence shadow unexpectedly enabled")
    if metric_int(independence.metrics, "fasim_fastSIM_precompute_independence_enabled") != 1:
        raise RuntimeError(f"{workload.label}: independence shadow was not enabled")
    if metric_int(independence.metrics, "fasim_fastSIM_precompute_full_replay_enabled") != 1:
        raise RuntimeError(f"{workload.label}: full replay was not enabled")

    legacy = metric_int(independence.metrics, "fasim_fastSIM_precompute_legacy_requests")
    derived = metric_int(independence.metrics, "fasim_fastSIM_precompute_derived_requests")
    replay = metric_int(independence.metrics, "fasim_fastSIM_precompute_replay_requests")
    if legacy <= 0:
        raise RuntimeError(f"{workload.label}: no legacy requests observed")
    if derived < legacy:
        raise RuntimeError(
            f"{workload.label}: derived requests should cover legacy requests: "
            f"legacy={legacy} derived={derived}"
        )
    if legacy != replay:
        raise RuntimeError(
            f"{workload.label}: request counts differ: legacy={legacy} derived={derived} replay={replay}"
        )
    for key in REQUEST_COMPARISON_KEYS:
        if metric_int(independence.metrics, key) < 0:
            raise RuntimeError(f"{workload.label}: expected non-negative {key}")
    for key in REPLAY_MISMATCH_KEYS:
        if metric_int(independence.metrics, key) != 0:
            raise RuntimeError(f"{workload.label}: expected {key}=0, got {independence.metrics[key]}")
    if metric_float(independence.metrics, "fasim_fastSIM_precompute_cpu_compute_seconds") <= 0.0:
        raise RuntimeError(f"{workload.label}: missing compute timing")
    if metric_float(independence.metrics, "fasim_fastSIM_precompute_replay_seconds") <= 0.0:
        raise RuntimeError(f"{workload.label}: missing replay timing")
    if metric_int(independence.metrics, "fasim_fastSIM_precompute_memory_bytes") <= 0:
        raise RuntimeError(f"{workload.label}: missing memory footprint")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cuda-bin", required=True)
    parser.add_argument(
        "--work-dir",
        default=str(ROOT / ".tmp" / "fasim_fastSIM_align_precompute_independence"),
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
    print("Fasim fastSIM align precompute independence checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
