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


BATCH_KEYS = [
    "fasim_exact_column_batch_requested",
    "fasim_exact_column_batch_active",
    "fasim_exact_column_batch_supported",
    "fasim_exact_column_batch_disabled_reason",
    "fasim_exact_column_batch_validate_enabled",
    "fasim_exact_column_batch_requests",
    "fasim_exact_column_batch_cells",
    "fasim_exact_column_batch_max_cells_per_request",
    "fasim_exact_column_batch_pack_seconds",
    "fasim_exact_column_batch_h2d_seconds",
    "fasim_exact_column_batch_kernel_seconds",
    "fasim_exact_column_batch_d2h_seconds",
    "fasim_exact_column_batch_unpack_seconds",
    "fasim_exact_column_batch_apply_seconds",
    "fasim_exact_column_batch_total_seconds",
    "fasim_exact_column_batch_cpu_fallback_seconds",
    "fasim_exact_column_batch_validate_seconds",
    "fasim_exact_column_batch_score_mismatches",
    "fasim_exact_column_batch_endpoint_mismatches",
    "fasim_exact_column_batch_scoreinfo_mismatches",
    "fasim_exact_column_batch_digest_mismatches",
    "fasim_exact_column_batch_fallbacks",
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


def require_batch_clean(metrics: Dict[str, str], label: str) -> None:
    if metric_int(metrics, "fasim_exact_column_batch_requested") != 1:
        raise RuntimeError(f"{label}: batch was not requested")
    if metric_int(metrics, "fasim_exact_column_batch_active") != 1:
        raise RuntimeError(f"{label}: batch was not active")
    if metric_int(metrics, "fasim_exact_column_batch_supported") != 1:
        raise RuntimeError(f"{label}: batch did not report supported=1")
    if metric_int(metrics, "fasim_exact_column_batch_requests") <= 0:
        raise RuntimeError(f"{label}: batch did not observe exact-column requests")
    if metric_int(metrics, "fasim_exact_column_batch_cells") <= 0:
        raise RuntimeError(f"{label}: batch did not count exact-column cells")
    if metric_int(metrics, "fasim_exact_column_batch_max_cells_per_request") <= 0:
        raise RuntimeError(f"{label}: batch did not count max cells per request")
    if metric_float(metrics, "fasim_exact_column_batch_total_seconds") <= 0.0:
        raise RuntimeError(f"{label}: batch did not report positive total seconds")
    if metric_float(metrics, "fasim_exact_column_batch_kernel_seconds") <= 0.0:
        raise RuntimeError(f"{label}: batch did not report positive kernel seconds")
    require_zero(
        metrics,
        [
            "fasim_exact_column_batch_score_mismatches",
            "fasim_exact_column_batch_endpoint_mismatches",
            "fasim_exact_column_batch_scoreinfo_mismatches",
            "fasim_exact_column_batch_digest_mismatches",
            "fasim_exact_column_batch_fallbacks",
        ],
        label,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cuda-bin", required=True)
    parser.add_argument(
        "--work-dir",
        default=str(ROOT / ".tmp" / "fasim_exact_column_extend_batch"),
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
    default = run_once(
        workload=workload,
        mode=ModeSpec("final_stack", "cuda", final_stack_env),
        bin_path=cuda_bin,
        work_dir=work_dir / workload.label / "final_stack",
        require_profile=True,
    )
    batch = run_once(
        workload=workload,
        mode=ModeSpec(
            "final_stack_batch",
            "cuda",
            dict(final_stack_env, FASIM_EXACT_COLUMN_EXTEND_BATCH="1"),
        ),
        bin_path=cuda_bin,
        work_dir=work_dir / workload.label / "final_stack_batch",
        require_profile=True,
    )
    validate = run_once(
        workload=workload,
        mode=ModeSpec(
            "final_stack_batch_validate",
            "cuda",
            dict(
                final_stack_env,
                FASIM_EXACT_COLUMN_EXTEND_BATCH="1",
                FASIM_EXACT_COLUMN_EXTEND_BATCH_VALIDATE="1",
            ),
        ),
        bin_path=cuda_bin,
        work_dir=work_dir / workload.label / "final_stack_batch_validate",
        require_profile=True,
    )

    for label, observed in [
        ("default", default),
        ("batch", batch),
        ("validate", validate),
    ]:
        require_digest_match(table, observed, label)
        require_metrics(observed.metrics, BATCH_KEYS)

    if metric_int(default.metrics, "fasim_exact_column_batch_requested") != 0:
        raise RuntimeError("batch unexpectedly requested by default")
    if metric_int(default.metrics, "fasim_exact_column_batch_active") != 0:
        raise RuntimeError("batch unexpectedly active by default")
    require_zero(
        default.metrics,
        [
            "fasim_exact_column_batch_requests",
            "fasim_exact_column_batch_cells",
            "fasim_exact_column_batch_max_cells_per_request",
            "fasim_exact_column_batch_total_seconds",
            "fasim_exact_column_batch_fallbacks",
        ],
        "default",
    )

    require_batch_clean(batch.metrics, "batch")
    if metric_int(batch.metrics, "fasim_exact_column_batch_validate_enabled") != 0:
        raise RuntimeError("validate unexpectedly enabled in batch mode")
    require_batch_clean(validate.metrics, "validate")
    if metric_int(validate.metrics, "fasim_exact_column_batch_validate_enabled") != 1:
        raise RuntimeError("validate was not enabled")
    if metric_float(validate.metrics, "fasim_exact_column_batch_validate_seconds") <= 0.0:
        raise RuntimeError("validate did not report positive validation seconds")

    print("Fasim exact-column extend batch opt-in checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
