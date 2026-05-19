#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Dict, Iterable, List


ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from benchmark_fasim_gpu_dp_column_characterization import (  # noqa: E402
    ModeSpec,
    RunResult,
    WorkloadSpec,
    append_table,
    fmt_seconds,
    run_once,
)
from check_fasim_gpu_dp_column_hg38_score_mismatch_fix import (  # noqa: E402
    HG38_CHR21_SOFTMASK_COMPACT_REGION_Z,
    decode_fixture,
    write_fasta,
)
from check_fasim_parasail_aligner_shadow import (  # noqa: E402
    REQUIRED_KEYS,
    metric_float,
    metric_int,
    require_metrics,
)


def render_report(
    *,
    table: RunResult,
    shadow: RunResult,
    output_path: Path,
) -> str:
    require_metrics(shadow.metrics, REQUIRED_KEYS)

    lines: List[str] = []
    lines.append("# Fasim Parasail Aligner Shadow")
    lines.append("")
    lines.append("This PR adds a default-off Parasail aligner shadow gate.")
    lines.append("It does not replace `aligner.Align` and does not use Parasail output for production output.")
    lines.append("")
    lines.append("## Local Dependency State")
    lines.append("")
    append_table(
        lines,
        ["Metric", "Value"],
        [
            ["shadow enabled", str(metric_int(shadow.metrics, "fasim_aligner_parasail_shadow_enabled"))],
            ["supported", str(metric_int(shadow.metrics, "fasim_aligner_parasail_shadow_supported"))],
            [
                "disabled reason",
                str(metric_int(shadow.metrics, "fasim_aligner_parasail_shadow_disabled_reason")),
            ],
            ["requests total", str(metric_int(shadow.metrics, "fasim_aligner_parasail_shadow_requests_total"))],
            [
                "requests compared",
                str(metric_int(shadow.metrics, "fasim_aligner_parasail_shadow_requests_compared")),
            ],
            ["fallbacks", str(metric_int(shadow.metrics, "fasim_aligner_parasail_shadow_fallbacks"))],
            [
                "uses runtime output",
                str(metric_int(shadow.metrics, "fasim_aligner_parasail_shadow_uses_runtime_output")),
            ],
        ],
    )
    lines.append("")
    lines.append("`disabled_reason=1` means Parasail support was not built into this binary.")
    lines.append("That is the expected default in this local environment because `parasail.h`/`libparasail` are not installed.")
    lines.append("")
    lines.append("## Correctness Guard")
    lines.append("")
    append_table(
        lines,
        ["Check", "Value"],
        [
            ["table digest", table.digest],
            ["shadow digest", shadow.digest],
            ["records", str(table.records)],
            ["score mismatches", str(metric_int(shadow.metrics, "fasim_aligner_parasail_shadow_score_mismatches"))],
            [
                "endpoint mismatches",
                str(metric_int(shadow.metrics, "fasim_aligner_parasail_shadow_endpoint_mismatches")),
            ],
            ["CIGAR mismatches", str(metric_int(shadow.metrics, "fasim_aligner_parasail_shadow_cigar_mismatches"))],
            [
                "digest mismatches",
                str(metric_int(shadow.metrics, "fasim_aligner_parasail_shadow_digest_mismatches")),
            ],
        ],
    )
    lines.append("")
    lines.append("## Timers")
    lines.append("")
    append_table(
        lines,
        ["Timer", "Seconds"],
        [
            [
                "CPU reference",
                fmt_seconds(metric_float(shadow.metrics, "fasim_aligner_parasail_shadow_cpu_reference_seconds")),
            ],
            [
                "Parasail profile",
                fmt_seconds(metric_float(shadow.metrics, "fasim_aligner_parasail_shadow_profile_seconds")),
            ],
            [
                "Parasail align",
                fmt_seconds(metric_float(shadow.metrics, "fasim_aligner_parasail_shadow_align_seconds")),
            ],
            [
                "Parasail CIGAR",
                fmt_seconds(metric_float(shadow.metrics, "fasim_aligner_parasail_shadow_cigar_seconds")),
            ],
            [
                "Parasail total",
                fmt_seconds(metric_float(shadow.metrics, "fasim_aligner_parasail_shadow_total_seconds")),
            ],
        ],
    )
    lines.append("")
    lines.append("## Boundary")
    lines.append("")
    lines.append("- Default build links the Parasail stub, so no new dependency is required.")
    lines.append("- `FASIM_ALIGNER_PARASAIL_SHADOW=1` only records sampled side-path telemetry.")
    lines.append("- Real Parasail comparison requires an explicit `FASIM_PARASAIL_ENABLE=1` build with include/lib flags.")
    lines.append("- Parasail shadow is not a real-path candidate until score, endpoint, CIGAR, and digest are exact-clean.")
    lines.append("- Secondary score is not supported by the current Parasail SSW shadow contract.")
    lines.append("")
    text = "\n".join(lines) + "\n"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text, encoding="utf-8")
    return text


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cuda-bin", required=True)
    parser.add_argument(
        "--work-dir",
        default=str(ROOT / ".tmp" / "fasim_parasail_aligner_shadow_benchmark"),
    )
    parser.add_argument(
        "--output",
        default=str(ROOT / ".tmp" / "fasim_parasail_aligner_shadow.md"),
    )
    parser.add_argument("--require-profile", action="store_true")
    parser.add_argument("--check", action="store_true")
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
        require_profile=args.require_profile,
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
        require_profile=args.require_profile,
    )

    if args.check:
        if table.digest != shadow.digest:
            raise RuntimeError(f"digest mismatch: {table.digest} vs {shadow.digest}")
        if table.records != shadow.records:
            raise RuntimeError(f"record mismatch: {table.records} vs {shadow.records}")
        for key in [
            "fasim_aligner_parasail_shadow_score_mismatches",
            "fasim_aligner_parasail_shadow_endpoint_mismatches",
            "fasim_aligner_parasail_shadow_cigar_mismatches",
            "fasim_aligner_parasail_shadow_digest_mismatches",
        ]:
            if metric_int(shadow.metrics, key) != 0:
                raise RuntimeError(f"non-zero {key}")

    text = render_report(table=table, shadow=shadow, output_path=Path(args.output))
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
