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


PRECOMPUTE_KEYS = [
    "fasim_fastSIM_precompute_shadow_enabled",
    "fasim_fastSIM_precompute_requests",
    "fasim_fastSIM_precompute_requests_independent",
    "fasim_fastSIM_precompute_requests_state_dependent",
    "fasim_fastSIM_precompute_cpu_reference_seconds",
    "fasim_fastSIM_precompute_side_compute_seconds",
    "fasim_fastSIM_precompute_side_replay_seconds",
    "fasim_fastSIM_precompute_est_parallel_seconds_2t",
    "fasim_fastSIM_precompute_est_parallel_seconds_4t",
    "fasim_fastSIM_precompute_est_parallel_seconds_8t",
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


def require_zero(metrics: Dict[str, str], keys: Iterable[str], label: str) -> None:
    for key in keys:
        if metric_int(metrics, key) != 0:
            raise RuntimeError(f"{label}: expected {key}=0, got {metrics[key]}")


def require_shadow_clean(table: RunResult, default: RunResult, shadow: RunResult, label: str) -> None:
    require_digest_match(table, default, f"{label}/final_stack")
    require_digest_match(table, shadow, f"{label}/precompute_shadow")
    require_metrics(default.metrics, PRECOMPUTE_KEYS)
    require_metrics(shadow.metrics, PRECOMPUTE_KEYS)

    if metric_int(default.metrics, "fasim_fastSIM_precompute_shadow_enabled") != 0:
        raise RuntimeError(f"{label}: fastSIM precompute shadow unexpectedly enabled by default")
    require_zero(
        default.metrics,
        [
            "fasim_fastSIM_precompute_requests",
            "fasim_fastSIM_precompute_requests_independent",
            "fasim_fastSIM_precompute_requests_state_dependent",
            "fasim_fastSIM_precompute_candidate_state_mismatches",
            "fasim_fastSIM_precompute_emitted_record_mismatches",
            "fasim_fastSIM_precompute_cigar_mismatches",
            "fasim_fastSIM_precompute_digest_mismatches",
            "fasim_fastSIM_precompute_fallbacks",
        ],
        f"{label}/default",
    )

    if metric_int(shadow.metrics, "fasim_fastSIM_precompute_shadow_enabled") != 1:
        raise RuntimeError(f"{label}: fastSIM precompute shadow was not enabled")
    requests = metric_int(shadow.metrics, "fasim_fastSIM_precompute_requests")
    if requests <= 0:
        raise RuntimeError(f"{label}: fastSIM precompute shadow did not observe any requests")
    independent = metric_int(
        shadow.metrics, "fasim_fastSIM_precompute_requests_independent"
    )
    state_dependent = metric_int(
        shadow.metrics, "fasim_fastSIM_precompute_requests_state_dependent"
    )
    if independent + state_dependent != requests:
        raise RuntimeError(
            f"{label}: fastSIM precompute request independence counters do not sum to requests"
        )
    if metric_float(shadow.metrics, "fasim_fastSIM_precompute_cpu_reference_seconds") <= 0.0:
        raise RuntimeError(f"{label}: fastSIM precompute shadow did not report CPU reference time")
    if metric_float(shadow.metrics, "fasim_fastSIM_precompute_side_compute_seconds") <= 0.0:
        raise RuntimeError(f"{label}: fastSIM precompute shadow did not report side compute time")
    if metric_float(shadow.metrics, "fasim_fastSIM_precompute_side_replay_seconds") <= 0.0:
        raise RuntimeError(f"{label}: fastSIM precompute shadow did not report side replay time")
    require_zero(
        shadow.metrics,
        [
            "fasim_fastSIM_precompute_candidate_state_mismatches",
            "fasim_fastSIM_precompute_emitted_record_mismatches",
            "fasim_fastSIM_precompute_cigar_mismatches",
            "fasim_fastSIM_precompute_digest_mismatches",
            "fasim_fastSIM_precompute_fallbacks",
        ],
        f"{label}/precompute_shadow",
    )


def run_workload(cuda_bin: Path, work_dir: Path, workload: WorkloadSpec) -> RunResult:
    final_stack_env = {
        "FASIM_TRANSFERSTRING_TABLE": "1",
        "FASIM_GPU_DP_COLUMN_AUTO": "1",
        "FASIM_GPU_DP_COLUMN_AUTO_MIN_WINDOWS": "1",
        "FASIM_GPU_DP_COLUMN_AUTO_MIN_CELLS": "1",
        "FASIM_SSW_PROFILE_CACHE": "1",
        "FASIM_SSW_AVX2": "1",
        "FASIM_SSW_PROFILE_CONTEXT": "1",
        "FASIM_EXACT_COLUMN_EXTEND_BATCH": "1",
    }
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
            "precompute_shadow",
            "cuda",
            dict(
                final_stack_env,
                FASIM_FASTSIM_ALIGN_PRECOMPUTE_SHADOW="1",
                FASIM_FASTSIM_ALIGN_PRECOMPUTE_SHADOW_MAX_REQUESTS="256",
            ),
        ),
        bin_path=cuda_bin,
        work_dir=work_dir / workload.label / "precompute_shadow",
        require_profile=True,
    )
    require_shadow_clean(table, default, shadow, workload.label)
    return shadow


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cuda-bin", required=True)
    parser.add_argument(
        "--work-dir",
        default=str(ROOT / ".tmp" / "fasim_fastSIM_align_precompute_shadow"),
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
    compact = WorkloadSpec(
        "hg38_chr21_softmask_compact_region",
        "small hg38 soft-mask fixture with compact exact-column coverage",
        dna_path=dna_path,
        rna_path=ROOT / "H19.fa",
    )
    tiny = WorkloadSpec(
        "tiny",
        "tiny sample fixture with emitted fastSIM records",
        dna_path=ROOT / "testDNA.fa",
        rna_path=ROOT / "H19.fa",
    )

    run_workload(cuda_bin, work_dir, compact)
    tiny_shadow = run_workload(cuda_bin, work_dir, tiny)
    if metric_int(tiny_shadow.metrics, "fasim_fastSIM_extend_records_emitted") <= 0:
        raise RuntimeError("tiny: expected emitted fastSIM records for emitted-record shadow coverage")

    print("Fasim fastSIM align precompute shadow checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
