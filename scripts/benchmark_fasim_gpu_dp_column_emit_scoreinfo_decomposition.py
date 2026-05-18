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


DECOMPOSITION_KEYS = [
    "fasim_gpu_dp_column_emit_seconds",
    "fasim_gpu_dp_column_scoreinfo_reconstruct_seconds",
    "fasim_gpu_dp_column_exact_column_extend_seconds",
    "fasim_gpu_dp_column_threshold_fallback_seconds",
    "fasim_gpu_dp_column_topk_postprocess_seconds",
    "fasim_gpu_dp_column_compact_unpack_seconds",
    "fasim_gpu_dp_column_cpu_emit_records",
    "fasim_gpu_dp_column_exact_extend_windows",
    "fasim_gpu_dp_column_overflow_windows",
    "fasim_gpu_dp_column_threshold_fallback_windows",
    "fasim_gpu_dp_column_scoreinfo_reconstruct_records",
]


def make_modes() -> List[ModeSpec]:
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
        ModeSpec(
            "auto_validate",
            "cuda",
            {
                "FASIM_TRANSFERSTRING_TABLE": "1",
                "FASIM_GPU_DP_COLUMN_AUTO": "1",
                "FASIM_GPU_DP_COLUMN_VALIDATE": "1",
            },
        ),
    ]


def mode_count(results: Dict[str, List[RunResult]], mode: str, key: str) -> int:
    return median_count(results[mode], key)


def mode_metric(results: Dict[str, List[RunResult]], mode: str, key: str) -> float:
    return median_metric(results[mode], key)


def digest_matches_reference(results: Dict[str, List[RunResult]], mode: str) -> bool:
    return stable_digest(results[mode]) == stable_digest(results["table_only"])


def require_decomposition_metrics(results: Dict[str, List[RunResult]]) -> None:
    for mode in ["auto", "auto_validate"]:
        for key in DECOMPOSITION_KEYS:
            mode_metric(results, mode, key)


def render_report(
    *,
    workload: WorkloadSpec,
    modes: List[ModeSpec],
    results: Dict[str, List[RunResult]],
    repeat: int,
    output_path: Path,
) -> str:
    lines: List[str] = []
    lines.append("# Fasim GPU DP+column Emit / ScoreInfo Decomposition")
    lines.append("")
    lines.append(
        "This characterization decomposes the default-off "
        "`FASIM_GPU_DP_COLUMN_AUTO=1` path after GPU DP+column scoring. It adds "
        "telemetry only: no GPU optimization logic, no scoring/threshold change, "
        "no output/non-overlap change, and no SIM-close/recovery behavior change."
    )
    lines.append("")
    lines.append(f"Workload: `{workload.label}`. Each mode uses {repeat} run(s); tables report medians.")
    lines.append("")
    lines.append("## Modes")
    lines.append("")
    append_table(
        lines,
        ["Mode", "Environment"],
        [
            [mode.label, "`" + " ".join(f"{key}={value}" for key, value in mode.env.items()) + "`"]
            for mode in modes
        ],
    )
    lines.append("")
    lines.append("## Performance")
    lines.append("")
    table_total = mode_metric(results, "table_only", "fasim_total_seconds")
    auto_total = mode_metric(results, "auto", "fasim_total_seconds")
    validate_total = mode_metric(results, "auto_validate", "fasim_total_seconds")
    append_table(
        lines,
        [
            "Observed windows",
            "Observed cells",
            "Table seconds",
            "AUTO seconds",
            "AUTO speedup",
            "AUTO+validate seconds",
            "Digest",
            "Records",
            "AUTO digest match",
            "AUTO+validate digest match",
        ],
        [
            [
                fmt_int(mode_count(results, "auto", "fasim_gpu_dp_column_auto_observed_windows")),
                fmt_int(mode_count(results, "auto", "fasim_gpu_dp_column_auto_observed_cells")),
                fmt_seconds(table_total),
                fmt_seconds(auto_total),
                fmt_speedup(speedup(table_total, auto_total)),
                fmt_seconds(validate_total),
                "`" + stable_digest(results["table_only"]) + "`",
                str(stable_records(results["table_only"])),
                "yes" if digest_matches_reference(results, "auto") else "no",
                "yes" if digest_matches_reference(results, "auto_validate") else "no",
            ]
        ],
    )
    lines.append("")
    lines.append("## AUTO Post-GPU Decomposition")
    lines.append("")
    append_table(
        lines,
        [
            "Mode",
            "GPU total seconds",
            "GPU kernel seconds",
            "H2D bytes",
            "D2H bytes",
            "compact unpack seconds",
            "topK postprocess seconds",
            "scoreInfo reconstruct seconds",
            "exact-column extend seconds",
            "threshold fallback seconds",
            "emit seconds",
        ],
        [
            [
                mode,
                fmt_seconds(mode_metric(results, mode, "fasim_gpu_dp_column_total_seconds")),
                fmt_seconds(mode_metric(results, mode, "fasim_gpu_dp_column_kernel_seconds")),
                fmt_int(mode_count(results, mode, "fasim_gpu_dp_column_h2d_bytes")),
                fmt_int(mode_count(results, mode, "fasim_gpu_dp_column_d2h_bytes")),
                fmt_seconds(mode_metric(results, mode, "fasim_gpu_dp_column_compact_unpack_seconds")),
                fmt_seconds(mode_metric(results, mode, "fasim_gpu_dp_column_topk_postprocess_seconds")),
                fmt_seconds(mode_metric(results, mode, "fasim_gpu_dp_column_scoreinfo_reconstruct_seconds")),
                fmt_seconds(mode_metric(results, mode, "fasim_gpu_dp_column_exact_column_extend_seconds")),
                fmt_seconds(mode_metric(results, mode, "fasim_gpu_dp_column_threshold_fallback_seconds")),
                fmt_seconds(mode_metric(results, mode, "fasim_gpu_dp_column_emit_seconds")),
            ]
            for mode in ["auto", "auto_validate"]
        ],
    )
    lines.append("")
    lines.append("## Counts")
    lines.append("")
    append_table(
        lines,
        [
            "Mode",
            "scoreInfo reconstruct records",
            "CPU emit records",
            "overflow windows",
            "exact extend windows",
            "threshold fallback windows",
            "validation failed windows",
            "score mismatches",
            "scoreInfo mismatches",
        ],
        [
            [
                mode,
                fmt_int(mode_count(results, mode, "fasim_gpu_dp_column_scoreinfo_reconstruct_records")),
                fmt_int(mode_count(results, mode, "fasim_gpu_dp_column_cpu_emit_records")),
                fmt_int(mode_count(results, mode, "fasim_gpu_dp_column_overflow_windows")),
                fmt_int(mode_count(results, mode, "fasim_gpu_dp_column_exact_extend_windows")),
                fmt_int(mode_count(results, mode, "fasim_gpu_dp_column_threshold_fallback_windows")),
                fmt_int(mode_count(results, mode, "fasim_gpu_dp_column_validate_windows_failed")),
                fmt_int(mode_count(results, mode, "fasim_gpu_dp_column_validate_score_mismatch_windows")),
                fmt_int(mode_count(results, mode, "fasim_gpu_dp_column_validate_scoreinfo_mismatch_windows")),
            ]
            for mode in ["auto", "auto_validate"]
        ],
    )
    lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    exact_seconds = mode_metric(results, "auto", "fasim_gpu_dp_column_exact_column_extend_seconds")
    reconstruct_seconds = mode_metric(results, "auto", "fasim_gpu_dp_column_scoreinfo_reconstruct_seconds")
    d2h_bytes = mode_count(results, "auto", "fasim_gpu_dp_column_d2h_bytes")
    emit_seconds = mode_metric(results, "auto", "fasim_gpu_dp_column_emit_seconds")
    threshold_seconds = mode_metric(results, "auto", "fasim_gpu_dp_column_threshold_fallback_seconds")
    lines.append(
        f"In the AUTO run, exact-column extend is {fmt_seconds(exact_seconds)}s, "
        f"scoreInfo reconstruction is {fmt_seconds(reconstruct_seconds)}s, "
        f"threshold fallback is {fmt_seconds(threshold_seconds)}s, emit is "
        f"{fmt_seconds(emit_seconds)}s, and compact result D2H is {fmt_int(d2h_bytes)} bytes."
    )
    lines.append("")
    if exact_seconds > reconstruct_seconds and exact_seconds > emit_seconds:
        decision = (
            "Exact-column extend is the largest measured post-GPU substage; the next "
            "research PR should be a batched GPU exact-column extend shadow."
        )
    elif reconstruct_seconds > exact_seconds and reconstruct_seconds > emit_seconds:
        decision = (
            "ScoreInfo reconstruction is the largest measured post-GPU substage; the "
            "next research PR should reduce CPU reconstruction or change compact "
            "scoreInfo representation."
        )
    elif emit_seconds > exact_seconds and emit_seconds > reconstruct_seconds:
        decision = (
            "Emit/extension is the largest measured post-GPU substage; further speed "
            "work should focus on the `fastSIM_extend_from_scoreinfo` and output path."
        )
    else:
        decision = (
            "No single measured post-GPU substage clearly dominates; keep AUTO as a "
            "large-workload opt-in candidate and avoid micro-optimizations until a "
            "larger bottleneck is identified."
        )
    lines.append(decision)
    lines.append("")
    lines.append("## Boundaries")
    lines.append("")
    lines.append("```text")
    lines.append("new GPU optimization logic: no")
    lines.append("GPU default/recommendation change: no")
    lines.append("scoring/threshold/non-overlap/output change: no")
    lines.append("SIM-close/recovery change: no")
    lines.append("validation relaxation: no")
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
    parser.add_argument(
        "--work-dir",
        default=str(ROOT / ".tmp" / "fasim_gpu_dp_column_emit_scoreinfo_decomposition"),
    )
    parser.add_argument(
        "--output",
        default=str(ROOT / "docs" / "fasim_gpu_dp_column_emit_scoreinfo_decomposition.md"),
    )
    parser.add_argument("--require-profile", action="store_true")
    parser.add_argument("--check", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.repeat <= 0:
        raise RuntimeError("--repeat must be positive")

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
    modes = make_modes()
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

    require_decomposition_metrics(results)
    if args.check:
        if not digest_matches_reference(results, "auto"):
            raise RuntimeError("auto digest does not match table_only")
        if not digest_matches_reference(results, "auto_validate"):
            raise RuntimeError("auto_validate digest does not match table_only")
        if mode_count(results, "auto", "fasim_gpu_dp_column_auto_active") != 1:
            raise RuntimeError("AUTO did not activate GPU DP+column")

    render_report(
        workload=workload,
        modes=modes,
        results=results,
        repeat=args.repeat,
        output_path=Path(args.output),
    )
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
