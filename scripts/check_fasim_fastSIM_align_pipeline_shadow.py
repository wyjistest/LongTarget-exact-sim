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


PIPELINE_KEYS = [
    "fasim_fastSIM_pipeline_shadow_enabled",
    "fasim_fastSIM_pipeline_legacy_requests",
    "fasim_fastSIM_pipeline_segments",
    "fasim_fastSIM_pipeline_barriers",
    "fasim_fastSIM_pipeline_segment_p50",
    "fasim_fastSIM_pipeline_segment_p90",
    "fasim_fastSIM_pipeline_segment_p99",
    "fasim_fastSIM_pipeline_segment_max",
    "fasim_fastSIM_pipeline_segment_len1",
    "fasim_fastSIM_pipeline_segment_len2",
    "fasim_fastSIM_pipeline_segment_len3",
    "fasim_fastSIM_pipeline_segment_len4",
    "fasim_fastSIM_pipeline_segment_len5plus",
    "fasim_fastSIM_pipeline_requests_batchable_2",
    "fasim_fastSIM_pipeline_requests_batchable_4",
    "fasim_fastSIM_pipeline_requests_batchable_8",
    "fasim_fastSIM_pipeline_requests_batchable_16",
    "fasim_fastSIM_pipeline_est_parallel_seconds_2t",
    "fasim_fastSIM_pipeline_est_parallel_seconds_4t",
    "fasim_fastSIM_pipeline_est_parallel_seconds_8t",
    "fasim_fastSIM_pipeline_candidate_state_mismatches",
    "fasim_fastSIM_pipeline_emitted_record_mismatches",
    "fasim_fastSIM_pipeline_cigar_mismatches",
    "fasim_fastSIM_pipeline_digest_mismatches",
]

PIPELINE_MISMATCH_KEYS = [
    "fasim_fastSIM_pipeline_candidate_state_mismatches",
    "fasim_fastSIM_pipeline_emitted_record_mismatches",
    "fasim_fastSIM_pipeline_cigar_mismatches",
    "fasim_fastSIM_pipeline_digest_mismatches",
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
    pipeline = run_once(
        workload=workload,
        mode=ModeSpec(
            "pipeline_shadow",
            "cuda",
            dict(final_stack_env, FASIM_FASTSIM_ALIGN_PIPELINE_SHADOW="1"),
        ),
        bin_path=cuda_bin,
        work_dir=work_dir / workload.label / "pipeline_shadow",
        require_profile=True,
    )

    require_digest_match(table, default, f"{workload.label}/final_stack")
    require_digest_match(table, pipeline, f"{workload.label}/pipeline_shadow")
    require_metrics(default.metrics, PIPELINE_KEYS)
    require_metrics(pipeline.metrics, PIPELINE_KEYS)

    if metric_int(default.metrics, "fasim_fastSIM_pipeline_shadow_enabled") != 0:
        raise RuntimeError(f"{workload.label}: pipeline shadow unexpectedly enabled")
    if metric_int(pipeline.metrics, "fasim_fastSIM_pipeline_shadow_enabled") != 1:
        raise RuntimeError(f"{workload.label}: pipeline shadow was not enabled")

    legacy = metric_int(pipeline.metrics, "fasim_fastSIM_pipeline_legacy_requests")
    segments = metric_int(pipeline.metrics, "fasim_fastSIM_pipeline_segments")
    barriers = metric_int(pipeline.metrics, "fasim_fastSIM_pipeline_barriers")
    if legacy <= 0:
        raise RuntimeError(f"{workload.label}: no legacy requests observed")
    if segments <= 0:
        raise RuntimeError(f"{workload.label}: no pipeline segments observed")
    if barriers + segments < segments:
        raise RuntimeError(f"{workload.label}: invalid barrier count")
    segment_max = metric_int(pipeline.metrics, "fasim_fastSIM_pipeline_segment_max")
    if segment_max <= 0:
        raise RuntimeError(f"{workload.label}: missing max segment size")
    histogram_segments = sum(
        metric_int(pipeline.metrics, key)
        for key in [
            "fasim_fastSIM_pipeline_segment_len1",
            "fasim_fastSIM_pipeline_segment_len2",
            "fasim_fastSIM_pipeline_segment_len3",
            "fasim_fastSIM_pipeline_segment_len4",
            "fasim_fastSIM_pipeline_segment_len5plus",
        ]
    )
    if histogram_segments != segments:
        raise RuntimeError(
            f"{workload.label}: segment histogram mismatch: "
            f"histogram={histogram_segments} segments={segments}"
        )
    if metric_int(pipeline.metrics, "fasim_fastSIM_pipeline_requests_batchable_2") > legacy:
        raise RuntimeError(f"{workload.label}: batchable_2 exceeds legacy request count")
    if (
        metric_int(pipeline.metrics, "fasim_fastSIM_pipeline_requests_batchable_2") > 0
        and segment_max < 2
    ):
        raise RuntimeError(f"{workload.label}: batchable_2 reported with segment max < 2")
    if metric_float(pipeline.metrics, "fasim_fastSIM_pipeline_est_parallel_seconds_2t") <= 0.0:
        raise RuntimeError(f"{workload.label}: missing 2-thread estimate")

    for key in PIPELINE_MISMATCH_KEYS:
        if metric_int(pipeline.metrics, key) != 0:
            raise RuntimeError(f"{workload.label}: expected {key}=0, got {pipeline.metrics[key]}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cuda-bin", required=True)
    parser.add_argument(
        "--work-dir",
        default=str(ROOT / ".tmp" / "fasim_fastSIM_align_pipeline_shadow"),
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
    print("Fasim fastSIM align pipeline shadow checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
