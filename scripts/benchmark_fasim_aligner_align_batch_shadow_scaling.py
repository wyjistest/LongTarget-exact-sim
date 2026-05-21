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


SCALING_KEYS = [
    "fasim_align_batch_shadow_enabled",
    "fasim_align_batch_shadow_supported",
    "fasim_align_batch_shadow_requests_total",
    "fasim_align_batch_shadow_requests_compared",
    "fasim_align_batch_shadow_requests_unsupported",
    "fasim_align_batch_shadow_cells",
    "fasim_align_batch_shadow_h2d_bytes",
    "fasim_align_batch_shadow_d2h_bytes",
    "fasim_align_batch_shadow_kernel_seconds",
    "fasim_align_batch_shadow_total_seconds",
    "fasim_align_batch_shadow_cpu_reference_seconds",
    "fasim_align_batch_shadow_score_mismatches",
    "fasim_align_batch_shadow_coordinate_mismatches",
    "fasim_align_batch_shadow_total_mismatches",
]


def parse_sample_sizes(value: str) -> List[int]:
    sizes: List[int] = []
    for item in value.split(","):
        item = item.strip()
        if not item:
            continue
        if item.lower() == "full":
            sizes.append(0)
            continue
        parsed = int(item)
        if parsed <= 0:
            raise RuntimeError(f"invalid sample size: {item}")
        sizes.append(parsed)
    if not sizes:
        raise RuntimeError("no sample sizes requested")
    return sizes


def sample_label(size: int) -> str:
    return "full" if size == 0 else str(size)


def sample_cap(size: int) -> str:
    return "2147483647" if size == 0 else str(size)


def mode_count(results: Dict[str, List[RunResult]], mode: str, key: str) -> int:
    return median_count(results[mode], key)


def mode_metric(results: Dict[str, List[RunResult]], mode: str, key: str) -> float:
    return median_metric(results[mode], key)


def digest_matches_reference(results: Dict[str, List[RunResult]], mode: str) -> bool:
    return stable_digest(results[mode]) == stable_digest(results["table_only"])


def require_scaling_metrics(results: Dict[str, List[RunResult]], modes: List[str]) -> None:
    for mode in modes:
        for key in SCALING_KEYS:
            mode_metric(results, mode, key)


def throughput(numerator: float, seconds: float) -> float:
    return numerator / seconds if seconds > 0.0 else 0.0


def render_report(
    *,
    workload: WorkloadSpec,
    results: Dict[str, List[RunResult]],
    sample_sizes: List[int],
    repeat: int,
    output_path: Path,
) -> str:
    shadow_modes = [f"shadow_{sample_label(size)}" for size in sample_sizes]
    lines: List[str] = []
    lines.append("# Fasim aligner.Align Batch Shadow Scaling")
    lines.append("")
    lines.append(
        "This report characterizes scaling for the default-off batched/GPU "
        "`aligner.Align` score/ref-end shadow. CPU `aligner.Align` remains the "
        "real output authority; shadow results are never used for output. This "
        "does not add CIGAR/alignment-string reconstruction and does not change "
        "scoring, thresholds, non-overlap, GPU DP column AUTO policy, SIM-close, "
        "or recovery behavior."
    )
    lines.append("")
    lines.append(f"Workload: `{workload.label}`. Each mode uses {repeat} run(s); tables report medians.")
    lines.append("")

    table_total = mode_metric(results, "table_only", "fasim_total_seconds")
    auto_total = mode_metric(results, "auto", "fasim_total_seconds")
    lines.append("## Baseline")
    lines.append("")
    append_table(
        lines,
        [
            "Observed windows",
            "Observed cells",
            "Table seconds",
            "AUTO seconds",
            "AUTO speedup",
            "Digest",
            "Records",
            "AUTO digest match",
        ],
        [
            [
                fmt_int(mode_count(results, "auto", "fasim_gpu_dp_column_auto_observed_windows")),
                fmt_int(mode_count(results, "auto", "fasim_gpu_dp_column_auto_observed_cells")),
                fmt_seconds(table_total),
                fmt_seconds(auto_total),
                fmt_speedup(speedup(table_total, auto_total)),
                "`" + stable_digest(results["table_only"]) + "`",
                str(stable_records(results["table_only"])),
                "yes" if digest_matches_reference(results, "auto") else "no",
            ]
        ],
    )
    lines.append("")

    rows: List[List[str]] = []
    for size in sample_sizes:
        mode = f"shadow_{sample_label(size)}"
        compared = mode_count(results, mode, "fasim_align_batch_shadow_requests_compared")
        cells = mode_count(results, mode, "fasim_align_batch_shadow_cells")
        cpu_seconds = mode_metric(results, mode, "fasim_align_batch_shadow_cpu_reference_seconds")
        kernel_seconds = mode_metric(results, mode, "fasim_align_batch_shadow_kernel_seconds")
        total_seconds = mode_metric(results, mode, "fasim_align_batch_shadow_total_seconds")
        transfer_seconds = total_seconds - kernel_seconds
        rows.append(
            [
                sample_label(size),
                fmt_int(mode_count(results, mode, "fasim_align_batch_shadow_requests_total")),
                fmt_int(compared),
                fmt_int(mode_count(results, mode, "fasim_align_batch_shadow_requests_unsupported")),
                fmt_seconds(cpu_seconds),
                fmt_seconds(kernel_seconds),
                fmt_seconds(transfer_seconds),
                fmt_seconds(total_seconds),
                fmt_speedup(speedup(cpu_seconds, total_seconds)),
                fmt_int(mode_count(results, mode, "fasim_align_batch_shadow_score_mismatches")),
                fmt_int(mode_count(results, mode, "fasim_align_batch_shadow_coordinate_mismatches")),
                fmt_int(mode_count(results, mode, "fasim_align_batch_shadow_total_mismatches")),
            ]
        )

    lines.append("## Scaling")
    lines.append("")
    append_table(
        lines,
        [
            "Sample cap",
            "Requests total",
            "Compared",
            "Skipped",
            "CPU reference seconds",
            "GPU kernel seconds",
            "Transfer seconds",
            "GPU shadow total seconds",
            "GPU vs CPU shadow speedup",
            "Score mismatches",
            "Ref-end mismatches",
            "Total mismatches",
        ],
        rows,
    )
    lines.append("")

    throughput_rows: List[List[str]] = []
    for size in sample_sizes:
        mode = f"shadow_{sample_label(size)}"
        compared = mode_count(results, mode, "fasim_align_batch_shadow_requests_compared")
        cells = mode_count(results, mode, "fasim_align_batch_shadow_cells")
        cpu_seconds = mode_metric(results, mode, "fasim_align_batch_shadow_cpu_reference_seconds")
        total_seconds = mode_metric(results, mode, "fasim_align_batch_shadow_total_seconds")
        throughput_rows.append(
            [
                sample_label(size),
                fmt_int(compared),
                fmt_int(cells),
                f"{throughput(compared, cpu_seconds):.2f}",
                f"{throughput(compared, total_seconds):.2f}",
                f"{throughput(cells, cpu_seconds):.2f}",
                f"{throughput(cells, total_seconds):.2f}",
            ]
        )
    lines.append("## Throughput")
    lines.append("")
    append_table(
        lines,
        [
            "Sample cap",
            "Compared",
            "Cells",
            "CPU requests/sec",
            "GPU shadow requests/sec",
            "CPU cells/sec",
            "GPU shadow cells/sec",
        ],
        throughput_rows,
    )
    lines.append("")

    full_or_largest_mode = shadow_modes[-1]
    full_total = mode_metric(results, full_or_largest_mode, "fasim_align_batch_shadow_total_seconds")
    full_cpu = mode_metric(results, full_or_largest_mode, "fasim_align_batch_shadow_cpu_reference_seconds")
    full_mismatches = mode_count(results, full_or_largest_mode, "fasim_align_batch_shadow_total_mismatches")
    lines.append("## Decision")
    lines.append("")
    if full_mismatches != 0:
        lines.append(
            "The score/ref-end shadow mismatched CPU `aligner.Align`; debug correctness before any performance work."
        )
    elif full_total < full_cpu:
        lines.append(
            "The score/ref-end GPU shadow beats CPU reference at the largest sampled size. "
            "Next work can expand the output contract to query coordinates and CIGAR/alignment strings."
        )
    else:
        lines.append(
            "The score/ref-end GPU shadow remains slower than CPU reference at the largest sampled size. "
            "Do not add CIGAR/alignment-string reconstruction or real path from this result."
        )
    lines.append("")
    lines.append("## Boundaries")
    lines.append("")
    lines.append("```text")
    lines.append("use shadow result for output: no")
    lines.append("skip CPU aligner.Align: no")
    lines.append("CIGAR/alignment-string reconstruction: no")
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
    parser.add_argument("--sample-sizes", default="1000,10000,50000")
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument(
        "--work-dir",
        default=str(ROOT / ".tmp" / "fasim_aligner_align_batch_shadow_scaling"),
    )
    parser.add_argument(
        "--output",
        default=str(ROOT / "docs" / "fasim_aligner_align_batch_shadow_scaling.md"),
    )
    parser.add_argument("--require-profile", action="store_true")
    parser.add_argument("--check", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.repeat <= 0:
        raise RuntimeError("--repeat must be positive")
    sample_sizes = parse_sample_sizes(args.sample_sizes)

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
    modes = [
        ModeSpec("table_only", "cuda", {"FASIM_TRANSFERSTRING_TABLE": "1"}),
        ModeSpec(
            "auto",
            "cuda",
            {
                "FASIM_TRANSFERSTRING_TABLE": "1",
                "FASIM_GPU_DP_COLUMN_AUTO": "1",
            },
        ),
    ]
    for size in sample_sizes:
        modes.append(
            ModeSpec(
                f"shadow_{sample_label(size)}",
                "cuda",
                {
                    "FASIM_TRANSFERSTRING_TABLE": "1",
                    "FASIM_GPU_DP_COLUMN_AUTO": "1",
                    "FASIM_GPU_DP_COLUMN_AUTO_MIN_WINDOWS": "1",
                    "FASIM_GPU_DP_COLUMN_AUTO_MIN_CELLS": "1",
                    "FASIM_ALIGNER_ALIGN_BATCH_SHADOW": "1",
                    "FASIM_ALIGNER_ALIGN_BATCH_SHADOW_MAX_REQUESTS": sample_cap(size),
                    "FASIM_ALIGNER_ALIGN_BATCH_SHADOW_REQUEST_STRIDE": "1",
                },
            )
        )

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

    shadow_modes = [f"shadow_{sample_label(size)}" for size in sample_sizes]
    require_scaling_metrics(results, shadow_modes)
    report = render_report(
        workload=workload,
        results=results,
        sample_sizes=sample_sizes,
        repeat=args.repeat,
        output_path=Path(args.output),
    )

    if args.check:
        for mode in ["auto"] + shadow_modes:
            if not digest_matches_reference(results, mode):
                raise RuntimeError(f"{mode}: digest mismatch vs table_only")
        for mode in shadow_modes:
            if mode_count(results, mode, "fasim_align_batch_shadow_enabled") != 1:
                raise RuntimeError(f"{mode}: batch shadow not enabled")
            if mode_count(results, mode, "fasim_align_batch_shadow_total_mismatches") != 0:
                raise RuntimeError(f"{mode}: batch shadow mismatched")
            if mode_count(results, mode, "fasim_align_batch_shadow_requests_compared") <= 0:
                raise RuntimeError(f"{mode}: no compared requests")

    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
