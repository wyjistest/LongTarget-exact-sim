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
    "fasim_aligner_parasail_shadow_enabled",
    "fasim_aligner_parasail_shadow_supported",
    "fasim_aligner_parasail_shadow_disabled_reason",
    "fasim_aligner_parasail_shadow_requests_total",
    "fasim_aligner_parasail_shadow_requests_compared",
    "fasim_aligner_parasail_shadow_requests_unsupported",
    "fasim_aligner_parasail_shadow_query_bases",
    "fasim_aligner_parasail_shadow_target_bases",
    "fasim_aligner_parasail_shadow_cells",
    "fasim_aligner_parasail_shadow_cpu_reference_seconds",
    "fasim_aligner_parasail_shadow_profile_seconds",
    "fasim_aligner_parasail_shadow_align_seconds",
    "fasim_aligner_parasail_shadow_cigar_seconds",
    "fasim_aligner_parasail_shadow_total_seconds",
    "fasim_aligner_parasail_shadow_score_mismatches",
    "fasim_aligner_parasail_shadow_endpoint_mismatches",
    "fasim_aligner_parasail_shadow_cigar_mismatches",
    "fasim_aligner_parasail_shadow_cigar_normalized_mismatches",
    "fasim_aligner_parasail_shadow_digest_mismatches",
    "fasim_aligner_parasail_shadow_total_mismatches",
    "fasim_aligner_parasail_shadow_fallbacks",
    "fasim_aligner_parasail_shadow_secondary_score_supported",
    "fasim_aligner_parasail_shadow_has_score_contract",
    "fasim_aligner_parasail_shadow_has_endpoint_contract",
    "fasim_aligner_parasail_shadow_has_cigar_contract",
    "fasim_aligner_parasail_shadow_has_alignment_string_contract",
    "fasim_aligner_parasail_shadow_uses_runtime_output",
]

PARASAIL_NOT_BUILT_DISABLED_REASON = 1


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
        default=str(ROOT / ".tmp" / "fasim_parasail_aligner_shadow"),
    )
    parser.add_argument(
        "--expect-supported",
        action="store_true",
        help="Require a real Parasail-enabled binary instead of the default stub gate.",
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
        "small hg38 soft-mask fixture with Parasail shadow gate coverage",
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
            "parasail_shadow",
            "cuda",
            {
                "FASIM_TRANSFERSTRING_TABLE": "1",
                "FASIM_GPU_DP_COLUMN_AUTO": "1",
                "FASIM_GPU_DP_COLUMN_AUTO_MIN_WINDOWS": "1",
                "FASIM_GPU_DP_COLUMN_AUTO_MIN_CELLS": "1",
                "FASIM_ALIGNER_ALIGN_INTERNALS": "1",
                "FASIM_ALIGNER_PARASAIL_SHADOW": "1",
                "FASIM_ALIGNER_PARASAIL_SHADOW_MAX_REQUESTS": "128",
            },
        ),
        bin_path=cuda_bin,
        work_dir=work_dir / workload.label / "parasail_shadow",
        require_profile=True,
    )

    require_digest_match(table, shadow, "parasail_shadow")
    require_metrics(shadow.metrics, REQUIRED_KEYS)

    if metric_int(shadow.metrics, "fasim_aligner_parasail_shadow_enabled") != 1:
        raise RuntimeError("Parasail shadow was not enabled")
    supported = metric_int(shadow.metrics, "fasim_aligner_parasail_shadow_supported")
    disabled_reason = metric_int(
        shadow.metrics, "fasim_aligner_parasail_shadow_disabled_reason"
    )
    fallbacks = metric_int(shadow.metrics, "fasim_aligner_parasail_shadow_fallbacks")
    if args.expect_supported:
        if supported != 1:
            raise RuntimeError("real Parasail build did not report supported=1")
        if disabled_reason != 0:
            raise RuntimeError("real Parasail build reported a disabled reason")
        if fallbacks != 0:
            raise RuntimeError("real Parasail build reported fallback requests")
    else:
        if supported != 0:
            raise RuntimeError("default build must report Parasail unsupported")
        if disabled_reason != PARASAIL_NOT_BUILT_DISABLED_REASON:
            raise RuntimeError("Parasail shadow did not report not-built disabled reason")
        if fallbacks <= 0:
            raise RuntimeError("Parasail shadow did not report fallback requests")
    if metric_int(shadow.metrics, "fasim_aligner_parasail_shadow_uses_runtime_output") != 0:
        raise RuntimeError("Parasail shadow must not feed runtime output")
    if metric_int(shadow.metrics, "fasim_aligner_parasail_shadow_requests_total") <= 0:
        raise RuntimeError("Parasail shadow did not observe any aligner requests")
    if metric_int(shadow.metrics, "fasim_aligner_parasail_shadow_requests_compared") <= 0:
        raise RuntimeError("Parasail shadow did not sample any aligner requests")
    for key in [
        "fasim_aligner_parasail_shadow_score_mismatches",
        "fasim_aligner_parasail_shadow_endpoint_mismatches",
        "fasim_aligner_parasail_shadow_cigar_mismatches",
        "fasim_aligner_parasail_shadow_digest_mismatches",
        "fasim_aligner_parasail_shadow_total_mismatches",
    ]:
        if metric_int(shadow.metrics, key) != 0:
            raise RuntimeError(f"Parasail shadow reported non-zero {key}")
    if metric_int(shadow.metrics, "fasim_aligner_parasail_shadow_has_score_contract") != 1:
        raise RuntimeError("Parasail shadow should declare score comparison intent")
    if metric_int(shadow.metrics, "fasim_aligner_parasail_shadow_has_endpoint_contract") != 1:
        raise RuntimeError("Parasail shadow should declare endpoint comparison intent")
    if metric_int(shadow.metrics, "fasim_aligner_parasail_shadow_has_cigar_contract") != 1:
        raise RuntimeError("Parasail shadow should declare CIGAR comparison intent")
    if (
        metric_int(shadow.metrics, "fasim_aligner_parasail_shadow_secondary_score_supported")
        != 0
    ):
        raise RuntimeError("Parasail SSW shadow must not claim secondary score support yet")

    print("Fasim Parasail aligner shadow gate checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
