#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Dict, List


ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from benchmark_fasim_gpu_dp_column_characterization import (  # noqa: E402
    ModeSpec,
    RunResult,
    WorkloadSpec,
    append_table,
    fmt_int,
    fmt_seconds,
    fmt_speedup,
    median_count,
    median_metric,
    run_once,
    speedup,
    stable_digest,
    stable_records,
)


BATCH_KEYS = [
    "fasim_align_batch_shadow_enabled",
    "fasim_align_batch_shadow_supported",
    "fasim_align_batch_shadow_disabled_reason",
    "fasim_align_batch_shadow_requests_total",
    "fasim_align_batch_shadow_requests_compared",
    "fasim_align_batch_shadow_requests_unsupported",
    "fasim_align_batch_shadow_query_bases",
    "fasim_align_batch_shadow_target_bases",
    "fasim_align_batch_shadow_cells",
    "fasim_align_batch_shadow_h2d_bytes",
    "fasim_align_batch_shadow_d2h_bytes",
    "fasim_align_batch_shadow_kernel_seconds",
    "fasim_align_batch_shadow_total_seconds",
    "fasim_align_batch_shadow_cpu_reference_seconds",
    "fasim_align_batch_shadow_score_mismatches",
    "fasim_align_batch_shadow_coordinate_mismatches",
    "fasim_align_batch_shadow_cigar_mismatches",
    "fasim_align_batch_shadow_alignment_string_mismatches",
    "fasim_align_batch_shadow_total_mismatches",
    "fasim_align_batch_shadow_fallbacks",
    "fasim_align_batch_shadow_has_score_contract",
    "fasim_align_batch_shadow_has_coordinate_contract",
    "fasim_align_batch_shadow_has_cigar_contract",
    "fasim_align_batch_shadow_has_alignment_string_contract",
]


def make_modes(max_requests: int, stride: int) -> List[ModeSpec]:
    shadow_env = {
        "FASIM_TRANSFERSTRING_TABLE": "1",
        "FASIM_GPU_DP_COLUMN_AUTO": "1",
        "FASIM_GPU_DP_COLUMN_AUTO_MIN_WINDOWS": "1",
        "FASIM_GPU_DP_COLUMN_AUTO_MIN_CELLS": "1",
        "FASIM_ALIGNER_ALIGN_BATCH_SHADOW": "1",
        "FASIM_ALIGNER_ALIGN_BATCH_SHADOW_MAX_REQUESTS": str(max_requests),
        "FASIM_ALIGNER_ALIGN_BATCH_SHADOW_REQUEST_STRIDE": str(stride),
    }
    validate_env = dict(shadow_env)
    validate_env["FASIM_GPU_DP_COLUMN_VALIDATE"] = "1"
    return [
        ModeSpec("table_only", "cuda", {"FASIM_TRANSFERSTRING_TABLE": "1"}),
        ModeSpec(
            "auto",
            "cuda",
            {
                "FASIM_TRANSFERSTRING_TABLE": "1",
                "FASIM_GPU_DP_COLUMN_AUTO": "1",
            },
        ),
        ModeSpec("batch_shadow", "cuda", shadow_env),
        ModeSpec("batch_shadow_validate", "cuda", validate_env),
    ]


def mode_count(results: Dict[str, List[RunResult]], mode: str, key: str) -> int:
    return median_count(results[mode], key)


def mode_metric(results: Dict[str, List[RunResult]], mode: str, key: str) -> float:
    return median_metric(results[mode], key)


def digest_matches_reference(results: Dict[str, List[RunResult]], mode: str) -> bool:
    return stable_digest(results[mode]) == stable_digest(results["table_only"])


def require_batch_metrics(results: Dict[str, List[RunResult]]) -> None:
    for mode in ["batch_shadow", "batch_shadow_validate"]:
        for key in BATCH_KEYS:
            mode_metric(results, mode, key)


def render_report(
    *,
    workload: WorkloadSpec,
    results: Dict[str, List[RunResult]],
    repeat: int,
    max_requests: int,
    stride: int,
    output_path: Path,
) -> str:
    lines: List[str] = []
    lines.append("# Fasim aligner.Align Batch Shadow")
    lines.append("")
    lines.append(
        "This report characterizes a default-off `aligner.Align` batch shadow. "
        "The real CPU `aligner.Align` path remains authoritative; the shadow only "
        "collects bounded requests and reports score/coordinate contract coverage. "
        "It does not feed shadow results into output and does not change scoring, "
        "thresholds, non-overlap, CIGAR/alignment output, GPU DP column AUTO policy, "
        "SIM-close, or recovery behavior."
    )
    lines.append("")
    lines.append(
        "Current implementation note: the shadow uses the existing CUDA DP+column "
        "top-1 backend to batch score and reference-end checks. CPU `aligner.Align` "
        "still provides the real output and the CIGAR/alignment-string contract is "
        "not implemented."
    )
    lines.append("")
    lines.append(
        f"Workload: `{workload.label}`. Each mode uses {repeat} run(s); tables report medians. "
        f"Shadow cap: `{max_requests}` requests, stride `{stride}`."
    )
    lines.append("")

    table_total = mode_metric(results, "table_only", "fasim_total_seconds")
    auto_total = mode_metric(results, "auto", "fasim_total_seconds")
    shadow_total = mode_metric(results, "batch_shadow", "fasim_total_seconds")
    validate_total = mode_metric(results, "batch_shadow_validate", "fasim_total_seconds")

    lines.append("## Performance")
    lines.append("")
    append_table(
        lines,
        [
            "Observed windows",
            "Observed cells",
            "Table seconds",
            "AUTO seconds",
            "AUTO speedup",
            "Batch shadow seconds",
            "Batch shadow speedup",
            "Batch shadow validate seconds",
            "Digest",
            "Records",
            "Shadow digest match",
            "Validate digest match",
        ],
        [
            [
                fmt_int(mode_count(results, "batch_shadow", "fasim_gpu_dp_column_auto_observed_windows")),
                fmt_int(mode_count(results, "batch_shadow", "fasim_gpu_dp_column_auto_observed_cells")),
                fmt_seconds(table_total),
                fmt_seconds(auto_total),
                fmt_speedup(speedup(table_total, auto_total)),
                fmt_seconds(shadow_total),
                fmt_speedup(speedup(table_total, shadow_total)),
                fmt_seconds(validate_total),
                "`" + stable_digest(results["table_only"]) + "`",
                str(stable_records(results["table_only"])),
                "yes" if digest_matches_reference(results, "batch_shadow") else "no",
                "yes" if digest_matches_reference(results, "batch_shadow_validate") else "no",
            ]
        ],
    )
    lines.append("")

    lines.append("## Request Shape")
    lines.append("")
    append_table(
        lines,
        [
            "Mode",
            "Requests total",
            "Compared",
            "Unsupported/skipped",
            "Query bases",
            "Target bases",
            "Cells",
            "H2D bytes",
            "D2H bytes",
        ],
        [
            [
                mode,
                fmt_int(mode_count(results, mode, "fasim_align_batch_shadow_requests_total")),
                fmt_int(mode_count(results, mode, "fasim_align_batch_shadow_requests_compared")),
                fmt_int(mode_count(results, mode, "fasim_align_batch_shadow_requests_unsupported")),
                fmt_int(mode_count(results, mode, "fasim_align_batch_shadow_query_bases")),
                fmt_int(mode_count(results, mode, "fasim_align_batch_shadow_target_bases")),
                fmt_int(mode_count(results, mode, "fasim_align_batch_shadow_cells")),
                fmt_int(mode_count(results, mode, "fasim_align_batch_shadow_h2d_bytes")),
                fmt_int(mode_count(results, mode, "fasim_align_batch_shadow_d2h_bytes")),
            ]
            for mode in ["batch_shadow", "batch_shadow_validate"]
        ],
    )
    lines.append("")

    lines.append("## Contract Coverage")
    lines.append("")
    append_table(
        lines,
        [
            "Mode",
            "Enabled",
            "Supported",
            "Disabled reason",
            "Score",
            "Coordinates",
            "CIGAR",
            "Alignment string",
        ],
        [
            [
                mode,
                fmt_int(mode_count(results, mode, "fasim_align_batch_shadow_enabled")),
                fmt_int(mode_count(results, mode, "fasim_align_batch_shadow_supported")),
                fmt_int(mode_count(results, mode, "fasim_align_batch_shadow_disabled_reason")),
                fmt_int(mode_count(results, mode, "fasim_align_batch_shadow_has_score_contract")),
                fmt_int(mode_count(results, mode, "fasim_align_batch_shadow_has_coordinate_contract")),
                fmt_int(mode_count(results, mode, "fasim_align_batch_shadow_has_cigar_contract")),
                fmt_int(mode_count(results, mode, "fasim_align_batch_shadow_has_alignment_string_contract")),
            ]
            for mode in ["batch_shadow", "batch_shadow_validate"]
        ],
    )
    lines.append("")

    lines.append("## Mismatches")
    lines.append("")
    append_table(
        lines,
        [
            "Mode",
            "Score mismatches",
            "Coordinate mismatches",
            "CIGAR mismatches",
            "Alignment string mismatches",
            "Total mismatches",
            "Fallbacks",
        ],
        [
            [
                mode,
                fmt_int(mode_count(results, mode, "fasim_align_batch_shadow_score_mismatches")),
                fmt_int(mode_count(results, mode, "fasim_align_batch_shadow_coordinate_mismatches")),
                fmt_int(mode_count(results, mode, "fasim_align_batch_shadow_cigar_mismatches")),
                fmt_int(mode_count(results, mode, "fasim_align_batch_shadow_alignment_string_mismatches")),
                fmt_int(mode_count(results, mode, "fasim_align_batch_shadow_total_mismatches")),
                fmt_int(mode_count(results, mode, "fasim_align_batch_shadow_fallbacks")),
            ]
            for mode in ["batch_shadow", "batch_shadow_validate"]
        ],
    )
    lines.append("")

    lines.append("## Timing")
    lines.append("")
    append_table(
        lines,
        [
            "Mode",
            "CPU reference seconds",
            "Shadow total seconds",
            "Kernel seconds",
            "Transfer seconds",
        ],
        [
            [
                mode,
                fmt_seconds(mode_metric(results, mode, "fasim_align_batch_shadow_cpu_reference_seconds")),
                fmt_seconds(mode_metric(results, mode, "fasim_align_batch_shadow_total_seconds")),
                fmt_seconds(mode_metric(results, mode, "fasim_align_batch_shadow_kernel_seconds")),
                fmt_seconds(
                    mode_metric(results, mode, "fasim_align_batch_shadow_total_seconds") -
                    mode_metric(results, mode, "fasim_align_batch_shadow_kernel_seconds")
                ),
            ]
            for mode in ["batch_shadow", "batch_shadow_validate"]
        ],
    )
    lines.append("")

    lines.append("## Decision")
    lines.append("")
    if mode_count(results, "batch_shadow", "fasim_align_batch_shadow_total_mismatches") != 0:
        lines.append(
            "The CUDA score/ref-end shadow mismatched CPU `aligner.Align`; debug the "
            "score or coordinate mapping before adding any broader contract."
        )
    elif mode_count(results, "batch_shadow", "fasim_align_batch_shadow_has_cigar_contract") == 0:
        lines.append(
            "Stage 1 CUDA score/ref-end shadow is clean for the sampled requests. Next "
            "work should add query-coordinate and CIGAR/alignment-string reconstruction "
            "shadow before any real path."
        )
    else:
        lines.append(
            "Full output contract is covered. If timing is materially faster than CPU reference, the next PR can "
            "consider a default-off real opt-in guarded by validation/fallback."
        )
    lines.append("")
    lines.append("## Boundaries")
    lines.append("")
    lines.append("```text")
    lines.append("use shadow result for output: no")
    lines.append("skip CPU aligner.Align in real path: no")
    lines.append("CIGAR/alignment output semantic change: no")
    lines.append("scoring/threshold/non-overlap change: no")
    lines.append("GPU DP column AUTO policy change: no")
    lines.append("validation relaxation: no")
    lines.append("SIM-close/recovery change: no")
    lines.append("```")

    report = "\n".join(lines)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report + "\n", encoding="utf-8")
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cuda-bin", required=True)
    parser.add_argument("--dna", required=True)
    parser.add_argument("--rna", required=True)
    parser.add_argument("--label", default="hg38_chr21_H19")
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--max-requests", type=int, default=10000)
    parser.add_argument("--request-stride", type=int, default=1)
    parser.add_argument(
        "--work-dir",
        default=str(ROOT / ".tmp" / "fasim_aligner_align_batch_shadow"),
    )
    parser.add_argument(
        "--output",
        default=str(ROOT / "docs" / "fasim_aligner_align_batch_shadow.md"),
    )
    parser.add_argument("--require-profile", action="store_true")
    parser.add_argument("--check", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.repeat <= 0:
        raise RuntimeError("--repeat must be positive")
    if args.max_requests <= 0:
        raise RuntimeError("--max-requests must be positive")
    if args.request_stride <= 0:
        raise RuntimeError("--request-stride must be positive")

    cuda_bin = Path(args.cuda_bin)
    if not cuda_bin.is_absolute():
        cuda_bin = (ROOT / cuda_bin).resolve()
    if not cuda_bin.exists():
        raise RuntimeError(f"missing CUDA Fasim binary: {cuda_bin}")

    workload = WorkloadSpec(
        args.label,
        "large real workload",
        dna_path=Path(args.dna).resolve(),
        rna_path=Path(args.rna).resolve(),
    )
    modes = make_modes(args.max_requests, args.request_stride)
    results: Dict[str, List[RunResult]] = {}
    work_dir = Path(args.work_dir)
    for mode in modes:
        runs: List[RunResult] = []
        for index in range(args.repeat):
            runs.append(
                run_once(
                    workload=workload,
                    mode=mode,
                    bin_path=cuda_bin,
                    work_dir=work_dir / workload.label / mode.label / f"run_{index + 1}",
                    require_profile=args.require_profile,
                )
            )
        results[mode.label] = runs

    require_batch_metrics(results)
    report = render_report(
        workload=workload,
        results=results,
        repeat=args.repeat,
        max_requests=args.max_requests,
        stride=args.request_stride,
        output_path=Path(args.output),
    )

    if args.check:
        for mode in ["auto", "batch_shadow", "batch_shadow_validate"]:
            if not digest_matches_reference(results, mode):
                raise RuntimeError(f"{mode}: digest mismatch vs table_only")
        if mode_count(results, "batch_shadow", "fasim_align_batch_shadow_enabled") != 1:
            raise RuntimeError("batch shadow was not enabled")
        if mode_count(results, "batch_shadow", "fasim_align_batch_shadow_requests_compared") <= 0:
            raise RuntimeError("batch shadow compared no requests")
        if mode_count(results, "batch_shadow", "fasim_align_batch_shadow_total_mismatches") != 0:
            raise RuntimeError("batch shadow reported mismatches")

    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
