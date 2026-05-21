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
    "fasim_aligner_align_seconds",
    "fasim_aligner_align_calls",
    "fasim_aligner_align_total_cells",
    "fasim_aligner_align_total_query_bases",
    "fasim_aligner_align_total_target_bases",
    "fasim_aligner_align_avg_query_len",
    "fasim_aligner_align_avg_target_len",
    "fasim_aligner_align_max_query_len",
    "fasim_aligner_align_max_target_len",
    "fasim_aligner_align_records_considered",
    "fasim_aligner_align_records_emitted",
    "fasim_aligner_align_records_rejected_after_align",
    "fasim_aligner_align_scoreinfo_exact_score_matches",
    "fasim_aligner_align_scoreinfo_position_matches",
    "fasim_aligner_align_required_for_cigar",
    "fasim_aligner_align_required_for_score",
    "fasim_aligner_align_required_for_coordinates",
    "fasim_aligner_align_bypass_shadow_enabled",
    "fasim_aligner_align_bypass_shadow_bypassable_records",
    "fasim_aligner_align_bypass_shadow_non_bypassable_records",
    "fasim_aligner_align_bypass_shadow_est_seconds_saved",
    "fasim_aligner_align_bypass_shadow_score_mismatches",
    "fasim_aligner_align_bypass_shadow_coordinate_mismatches",
    "fasim_aligner_align_bypass_shadow_cigar_missing_records",
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
        default=str(ROOT / ".tmp" / "fasim_aligner_align_decomposition"),
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
        "small hg38 soft-mask fixture with compact exact-extend coverage",
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
    auto = run_once(
        workload=workload,
        mode=ModeSpec(
            "auto",
            "cuda",
            {
                "FASIM_TRANSFERSTRING_TABLE": "1",
                "FASIM_GPU_DP_COLUMN_AUTO": "1",
                "FASIM_GPU_DP_COLUMN_AUTO_MIN_WINDOWS": "1",
                "FASIM_GPU_DP_COLUMN_AUTO_MIN_CELLS": "1",
            },
        ),
        bin_path=cuda_bin,
        work_dir=work_dir / workload.label / "auto",
        require_profile=True,
    )
    require_digest_match(table, auto, "auto")
    require_metrics(auto.metrics, REQUIRED_KEYS)

    if metric_int(auto.metrics, "fasim_gpu_dp_column_auto_active") != 1:
        raise RuntimeError("AUTO was not active")
    if metric_float(auto.metrics, "fasim_aligner_align_seconds") <= 0.0:
        raise RuntimeError("aligner.Align timer was not exercised")
    if metric_int(auto.metrics, "fasim_aligner_align_calls") <= 0:
        raise RuntimeError("aligner.Align call count was not recorded")
    if metric_int(auto.metrics, "fasim_aligner_align_total_cells") <= 0:
        raise RuntimeError("aligner.Align cells were not recorded")
    if metric_int(auto.metrics, "fasim_aligner_align_records_considered") <= 0:
        raise RuntimeError("aligner.Align records considered were not recorded")

    print("Fasim aligner.Align decomposition checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
