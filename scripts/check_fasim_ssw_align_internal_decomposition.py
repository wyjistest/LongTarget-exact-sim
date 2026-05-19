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
    "fasim_aligner_setup_seconds",
    "fasim_aligner_strlen_seconds",
    "fasim_aligner_query_alloc_seconds",
    "fasim_aligner_query_translate_seconds",
    "fasim_aligner_ref_translate_seconds",
    "fasim_aligner_profile_cache_lookup_seconds",
    "fasim_aligner_profile_cache_hit_seconds",
    "fasim_aligner_profile_cache_miss_seconds",
    "fasim_ssw_align_seconds",
    "fasim_ssw_forward_score_end_seconds",
    "fasim_ssw_reverse_start_seconds",
    "fasim_ssw_banded_sw_seconds",
    "fasim_ssw_cigar_seconds",
    "fasim_ssw_endpoint_bookkeeping_seconds",
    "fasim_ssw_byte_path_seconds",
    "fasim_ssw_word_path_seconds",
    "fasim_ssw_fallback_calls",
    "fasim_ssw_forward_calls",
    "fasim_ssw_reverse_calls",
    "fasim_ssw_banded_sw_calls",
    "fasim_aligner_align_calls",
    "fasim_fastSIM_extend_records_emitted",
    "fasim_fastSIM_extend_records_rejected",
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


def require_decomposition(run: RunResult) -> None:
    require_metrics(run.metrics, REQUIRED_KEYS)
    if metric_int(run.metrics, "fasim_gpu_dp_column_auto_active") != 1:
        raise RuntimeError("AUTO was not active")
    if metric_int(run.metrics, "fasim_aligner_align_cpu_internals_enabled") != 1:
        raise RuntimeError("CPU aligner internals telemetry was not enabled")
    if metric_int(run.metrics, "fasim_ssw_profile_cache_active") != 1:
        raise RuntimeError("SSW profile cache was not active")
    if metric_int(run.metrics, "fasim_aligner_align_calls") <= 0:
        raise RuntimeError("aligner.Align calls were not recorded")
    if metric_float(run.metrics, "fasim_aligner_setup_seconds") <= 0.0:
        raise RuntimeError("aligner setup timer was not exercised")
    if metric_float(run.metrics, "fasim_aligner_ref_translate_seconds") <= 0.0:
        raise RuntimeError("reference translate timer was not exercised")
    if metric_float(run.metrics, "fasim_aligner_profile_cache_lookup_seconds") <= 0.0:
        raise RuntimeError("profile cache lookup timer was not exercised")
    if metric_float(run.metrics, "fasim_aligner_profile_cache_hit_seconds") <= 0.0:
        raise RuntimeError("profile cache hit timer was not exercised")
    if metric_float(run.metrics, "fasim_aligner_profile_cache_miss_seconds") <= 0.0:
        raise RuntimeError("profile cache miss timer was not exercised")
    if metric_float(run.metrics, "fasim_ssw_align_seconds") <= 0.0:
        raise RuntimeError("ssw_align timer was not exercised")
    if metric_float(run.metrics, "fasim_ssw_forward_score_end_seconds") <= 0.0:
        raise RuntimeError("forward score/end timer was not exercised")
    if metric_float(run.metrics, "fasim_ssw_reverse_start_seconds") <= 0.0:
        raise RuntimeError("reverse-start timer was not exercised")
    if metric_float(run.metrics, "fasim_ssw_banded_sw_seconds") <= 0.0:
        raise RuntimeError("banded_sw timer was not exercised")
    if metric_float(run.metrics, "fasim_ssw_cigar_seconds") <= 0.0:
        raise RuntimeError("CIGAR timer was not exercised")
    if metric_float(run.metrics, "fasim_ssw_endpoint_bookkeeping_seconds") <= 0.0:
        raise RuntimeError("endpoint bookkeeping timer was not exercised")
    if metric_float(run.metrics, "fasim_ssw_byte_path_seconds") <= 0.0:
        raise RuntimeError("byte-path timer was not exercised")
    if metric_int(run.metrics, "fasim_ssw_forward_calls") <= 0:
        raise RuntimeError("forward calls were not recorded")
    if metric_int(run.metrics, "fasim_ssw_reverse_calls") <= 0:
        raise RuntimeError("reverse calls were not recorded")
    if metric_int(run.metrics, "fasim_ssw_banded_sw_calls") <= 0:
        raise RuntimeError("banded_sw calls were not recorded")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cuda-bin", required=True)
    parser.add_argument(
        "--work-dir",
        default=str(ROOT / ".tmp" / "fasim_ssw_align_internal_decomposition"),
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
        "small hg38 soft-mask fixture with ssw_align decomposition coverage",
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
    decomposition = run_once(
        workload=workload,
        mode=ModeSpec(
            "auto_cache_ssw_align_internal_decomposition",
            "cuda",
            {
                "FASIM_TRANSFERSTRING_TABLE": "1",
                "FASIM_GPU_DP_COLUMN_AUTO": "1",
                "FASIM_GPU_DP_COLUMN_AUTO_MIN_WINDOWS": "1",
                "FASIM_GPU_DP_COLUMN_AUTO_MIN_CELLS": "1",
                "FASIM_ALIGNER_ALIGN_INTERNALS": "1",
                "FASIM_SSW_PROFILE_CACHE": "1",
            },
        ),
        bin_path=cuda_bin,
        work_dir=work_dir / workload.label / "auto_cache_ssw_align_internal_decomposition",
        require_profile=True,
    )

    require_digest_match(table, decomposition, "auto_cache_ssw_align_internal_decomposition")
    require_decomposition(decomposition)

    print("Fasim ssw_align internal decomposition checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
