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
    "fasim_aligner_accelign_shadow_enabled",
    "fasim_aligner_accelign_shadow_supported",
    "fasim_aligner_accelign_shadow_disabled_reason",
    "fasim_aligner_accelign_shadow_requests_total",
    "fasim_aligner_accelign_shadow_requests_compared",
    "fasim_aligner_accelign_shadow_requests_unsupported",
    "fasim_aligner_accelign_shadow_query_bases",
    "fasim_aligner_accelign_shadow_target_bases",
    "fasim_aligner_accelign_shadow_cells",
    "fasim_aligner_accelign_shadow_h2d_bytes",
    "fasim_aligner_accelign_shadow_d2h_bytes",
    "fasim_aligner_accelign_shadow_kernel_seconds",
    "fasim_aligner_accelign_shadow_total_seconds",
    "fasim_aligner_accelign_shadow_cpu_reference_seconds",
    "fasim_aligner_accelign_shadow_score_mismatches",
    "fasim_aligner_accelign_shadow_endpoint_mismatches",
    "fasim_aligner_accelign_shadow_total_mismatches",
    "fasim_aligner_accelign_shadow_fallbacks",
    "fasim_aligner_accelign_shadow_has_score_contract",
    "fasim_aligner_accelign_shadow_has_endpoint_contract",
    "fasim_aligner_accelign_shadow_has_cigar_contract",
    "fasim_aligner_accelign_shadow_has_alignment_string_contract",
    "fasim_aligner_accelign_shadow_uses_runtime_output",
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cuda-bin", required=True)
    parser.add_argument(
        "--work-dir",
        default=str(ROOT / ".tmp" / "fasim_aligner_accelign_shadow"),
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
        "small hg38 soft-mask fixture with Accelign shadow coverage",
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
    shadow = run_once(
        workload=workload,
        mode=ModeSpec(
            "accelign_shadow",
            "cuda",
            {
                "FASIM_TRANSFERSTRING_TABLE": "1",
                "FASIM_GPU_DP_COLUMN_AUTO": "1",
                "FASIM_GPU_DP_COLUMN_AUTO_MIN_WINDOWS": "1",
                "FASIM_GPU_DP_COLUMN_AUTO_MIN_CELLS": "1",
                "FASIM_ALIGNER_ACCELIGN_SHADOW": "1",
                "FASIM_ALIGNER_ACCELIGN_SHADOW_MAX_REQUESTS": "256",
            },
        ),
        bin_path=cuda_bin,
        work_dir=work_dir / workload.label / "accelign_shadow",
        require_profile=True,
    )
    require_digest_match(table, shadow, "accelign_shadow")
    require_metrics(shadow.metrics, REQUIRED_KEYS)

    if metric_int(shadow.metrics, "fasim_aligner_accelign_shadow_enabled") != 1:
        raise RuntimeError("Accelign shadow was not enabled")
    if metric_int(shadow.metrics, "fasim_aligner_accelign_shadow_supported") != 1:
        raise RuntimeError("Accelign shadow backend was not supported")
    if metric_int(shadow.metrics, "fasim_aligner_accelign_shadow_uses_runtime_output") != 0:
        raise RuntimeError("Accelign shadow must not feed runtime output")
    if metric_int(shadow.metrics, "fasim_aligner_accelign_shadow_requests_total") <= 0:
        raise RuntimeError("Accelign shadow did not observe any requests")
    if metric_int(shadow.metrics, "fasim_aligner_accelign_shadow_requests_compared") <= 0:
        raise RuntimeError("Accelign shadow did not compare any requests")
    if metric_int(shadow.metrics, "fasim_aligner_accelign_shadow_h2d_bytes") <= 0:
        raise RuntimeError("Accelign shadow did not transfer request bytes to GPU")
    if metric_int(shadow.metrics, "fasim_aligner_accelign_shadow_d2h_bytes") <= 0:
        raise RuntimeError("Accelign shadow did not transfer result bytes from GPU")
    if metric_float(shadow.metrics, "fasim_aligner_accelign_shadow_kernel_seconds") <= 0.0:
        raise RuntimeError("Accelign shadow did not report GPU kernel time")
    if metric_int(shadow.metrics, "fasim_aligner_accelign_shadow_has_score_contract") != 1:
        raise RuntimeError("Accelign shadow must report score contract coverage")
    if metric_int(shadow.metrics, "fasim_aligner_accelign_shadow_score_mismatches") != 0:
        raise RuntimeError("Accelign shadow score contract mismatched")
    if metric_int(shadow.metrics, "fasim_aligner_accelign_shadow_has_cigar_contract") != 0:
        raise RuntimeError("Accelign shadow must not claim CIGAR coverage")
    if metric_int(shadow.metrics, "fasim_aligner_accelign_shadow_has_alignment_string_contract") != 0:
        raise RuntimeError("Accelign shadow must not claim alignment-string coverage")

    print("Fasim Accelign aligner shadow checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
