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


SHADOW_KEYS = [
    "fasim_exact_column_batch_shadow_enabled",
    "fasim_exact_column_batch_shadow_supported",
    "fasim_exact_column_batch_shadow_disabled_reason",
    "fasim_exact_column_batch_shadow_requests_total",
    "fasim_exact_column_batch_shadow_requests_compared",
    "fasim_exact_column_batch_shadow_cells",
    "fasim_exact_column_batch_shadow_cpu_reference_seconds",
    "fasim_exact_column_batch_shadow_shadow_total_seconds",
    "fasim_exact_column_batch_shadow_kernel_seconds",
    "fasim_exact_column_batch_shadow_h2d_bytes",
    "fasim_exact_column_batch_shadow_d2h_bytes",
    "fasim_exact_column_batch_shadow_score_mismatches",
    "fasim_exact_column_batch_shadow_endpoint_mismatches",
    "fasim_exact_column_batch_shadow_scoreinfo_mismatches",
    "fasim_exact_column_batch_shadow_total_mismatches",
    "fasim_exact_column_batch_shadow_first_mismatch_request",
    "fasim_exact_column_batch_shadow_est_seconds_saved",
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cuda-bin", required=True)
    parser.add_argument(
        "--work-dir",
        default=str(ROOT / ".tmp" / "fasim_exact_column_extend_batch_shadow"),
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
        "small hg38 soft-mask fixture with compact exact-column extend coverage",
        dna_path=dna_path,
        rna_path=ROOT / "H19.fa",
    )

    final_stack_env = {
        "FASIM_TRANSFERSTRING_TABLE": "1",
        "FASIM_GPU_DP_COLUMN_AUTO": "1",
        "FASIM_GPU_DP_COLUMN_AUTO_MIN_WINDOWS": "1",
        "FASIM_GPU_DP_COLUMN_AUTO_MIN_CELLS": "1",
        "FASIM_SSW_PROFILE_CACHE": "1",
        "FASIM_SSW_PROFILE_CONTEXT": "1",
    }
    table = run_once(
        workload=workload,
        mode=ModeSpec("table_only", "cuda", {"FASIM_TRANSFERSTRING_TABLE": "1"}),
        bin_path=cuda_bin,
        work_dir=work_dir / workload.label / "table_only",
        require_profile=True,
    )
    shadow_off = run_once(
        workload=workload,
        mode=ModeSpec("final_stack", "cuda", final_stack_env),
        bin_path=cuda_bin,
        work_dir=work_dir / workload.label / "final_stack",
        require_profile=True,
    )
    shadow_on = run_once(
        workload=workload,
        mode=ModeSpec(
            "final_stack_shadow",
            "cuda",
            dict(final_stack_env, FASIM_EXACT_COLUMN_EXTEND_BATCH_SHADOW="1"),
        ),
        bin_path=cuda_bin,
        work_dir=work_dir / workload.label / "final_stack_shadow",
        require_profile=True,
    )

    require_digest_match(table, shadow_off, "shadow_off")
    require_digest_match(table, shadow_on, "shadow_on")

    require_metrics(shadow_off.metrics, SHADOW_KEYS)
    require_metrics(shadow_on.metrics, SHADOW_KEYS)
    if metric_int(shadow_off.metrics, "fasim_exact_column_batch_shadow_enabled") != 0:
        raise RuntimeError("shadow unexpectedly enabled by default")
    require_zero(
        shadow_off.metrics,
        [
            "fasim_exact_column_batch_shadow_requests_total",
            "fasim_exact_column_batch_shadow_requests_compared",
            "fasim_exact_column_batch_shadow_total_mismatches",
        ],
        "shadow_off",
    )

    if metric_int(shadow_on.metrics, "fasim_exact_column_batch_shadow_enabled") != 1:
        raise RuntimeError("shadow was not enabled")
    if metric_int(shadow_on.metrics, "fasim_exact_column_batch_shadow_supported") != 1:
        raise RuntimeError("shadow did not report supported=1")
    if metric_int(shadow_on.metrics, "fasim_exact_column_batch_shadow_requests_total") <= 0:
        raise RuntimeError("shadow did not observe exact-column extend requests")
    if metric_int(shadow_on.metrics, "fasim_exact_column_batch_shadow_requests_compared") <= 0:
        raise RuntimeError("shadow did not compare exact-column extend requests")
    if metric_int(shadow_on.metrics, "fasim_exact_column_batch_shadow_cells") <= 0:
        raise RuntimeError("shadow did not count exact-column cells")
    require_zero(
        shadow_on.metrics,
        [
            "fasim_exact_column_batch_shadow_score_mismatches",
            "fasim_exact_column_batch_shadow_endpoint_mismatches",
            "fasim_exact_column_batch_shadow_scoreinfo_mismatches",
            "fasim_exact_column_batch_shadow_total_mismatches",
        ],
        "shadow_on",
    )
    if metric_int(shadow_on.metrics, "fasim_gpu_dp_column_exact_extend_windows") <= 0:
        raise RuntimeError("fixture did not exercise exact-column extend windows")

    print("Fasim exact-column extend batch shadow checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
