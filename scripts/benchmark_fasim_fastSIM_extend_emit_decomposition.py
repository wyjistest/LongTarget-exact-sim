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


FASTSIM_KEYS = [
    "fasim_fastSIM_extend_inclusive_seconds",
    "fasim_fastSIM_extend_exclusive_seconds",
    "fasim_fastSIM_extend_calls",
    "fasim_fastSIM_extend_scoreinfo_records",
    "fasim_fastSIM_extend_records_considered",
    "fasim_fastSIM_extend_records_emitted",
    "fasim_fastSIM_extend_records_rejected",
    "fasim_fastSIM_extend_exact_column_seconds",
    "fasim_fastSIM_extend_scoreinfo_scan_seconds",
    "fasim_fastSIM_extend_candidate_filter_seconds",
    "fasim_fastSIM_extend_record_build_seconds",
    "fasim_fastSIM_extend_alignment_reconstruct_seconds",
    "fasim_fastSIM_extend_cigar_seconds",
    "fasim_fastSIM_extend_vector_push_seconds",
    "fasim_fastSIM_extend_allocation_seconds",
    "fasim_fastSIM_extend_output_stage_seconds",
    "fasim_fastSIM_extend_duplicate_overlap_seconds",
    "fasim_fastSIM_extend_string_format_seconds",
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


def percent(value: float, total: float) -> str:
    if total <= 0.0:
        return "n/a"
    return f"{(100.0 * value / total):.2f}%"


def require_fastSIM_metrics(results: Dict[str, List[RunResult]]) -> None:
    for mode in ["auto", "auto_validate"]:
        for key in FASTSIM_KEYS:
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
    lines.append("# Fasim fastSIM ScoreInfo Emit Decomposition")
    lines.append("")
    lines.append(
        "This telemetry-only report decomposes the CPU-side "
        "`fastSIM_extend_from_scoreinfo` / emit path under "
        "`FASIM_TRANSFERSTRING_TABLE=1 FASIM_GPU_DP_COLUMN_AUTO=1`. It does not "
        "add optimization logic and does not change GPU kernels, AUTO policy, "
        "scoring, thresholding, non-overlap, output semantics, SIM-close, or "
        "recovery behavior."
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
    lines.append("## fastSIM Inclusive / Exclusive")
    lines.append("")
    append_table(
        lines,
        [
            "Mode",
            "GPU emit wrapper seconds",
            "fastSIM inclusive seconds",
            "fastSIM exclusive seconds",
            "external exact-column seconds",
            "calls",
            "scoreInfo records",
            "records considered",
            "records emitted",
            "records rejected",
        ],
        [
            [
                mode,
                fmt_seconds(mode_metric(results, mode, "fasim_gpu_dp_column_emit_seconds")),
                fmt_seconds(mode_metric(results, mode, "fasim_fastSIM_extend_inclusive_seconds")),
                fmt_seconds(mode_metric(results, mode, "fasim_fastSIM_extend_exclusive_seconds")),
                fmt_seconds(mode_metric(results, mode, "fasim_fastSIM_extend_exact_column_seconds")),
                fmt_int(mode_count(results, mode, "fasim_fastSIM_extend_calls")),
                fmt_int(mode_count(results, mode, "fasim_fastSIM_extend_scoreinfo_records")),
                fmt_int(mode_count(results, mode, "fasim_fastSIM_extend_records_considered")),
                fmt_int(mode_count(results, mode, "fasim_fastSIM_extend_records_emitted")),
                fmt_int(mode_count(results, mode, "fasim_fastSIM_extend_records_rejected")),
            ]
            for mode in ["auto", "auto_validate"]
        ],
    )
    lines.append("")
    lines.append("`fastSIM inclusive` measures only `fastSIM_extend_from_scoreinfo`; the P1 exact-column extend happens before that call and is reported as an external comparator, not a nested timer.")
    lines.append("")
    lines.append("## Component Breakdown")
    lines.append("")
    emit_total = mode_metric(results, "auto", "fasim_gpu_dp_column_emit_seconds")
    component_rows = [
        [
            "alignment reconstruction",
            mode_metric(results, "auto", "fasim_fastSIM_extend_alignment_reconstruct_seconds"),
            "exclusive",
            "`aligner.Align` over scoreInfo-derived local windows.",
        ],
        [
            "record build / convertMyTriplex",
            mode_metric(results, "auto", "fasim_fastSIM_extend_record_build_seconds"),
            "exclusive",
            "Triplex construction, CIGAR traversal, identity/stability work.",
        ],
        [
            "duplicate / overlap bookkeeping",
            mode_metric(results, "auto", "fasim_fastSIM_extend_duplicate_overlap_seconds"),
            "exclusive",
            "Sort/unique phases inside `fastSIM_extend_from_scoreinfo`.",
        ],
        [
            "candidate filter",
            mode_metric(results, "auto", "fasim_fastSIM_extend_candidate_filter_seconds"),
            "exclusive",
            "Alignment score/nonzero checks and final threshold checks.",
        ],
        [
            "vector push",
            mode_metric(results, "auto", "fasim_fastSIM_extend_vector_push_seconds"),
            "exclusive",
            "Final `triplex_list.push_back` loop.",
        ],
        [
            "scoreInfo scan",
            mode_metric(results, "auto", "fasim_fastSIM_extend_scoreinfo_scan_seconds"),
            "exclusive",
            "Outer scoreInfo record accounting.",
        ],
        [
            "allocation",
            mode_metric(results, "auto", "fasim_fastSIM_extend_allocation_seconds"),
            "exclusive",
            "Local container construction/reserve-visible allocation envelope.",
        ],
        [
            "output stage",
            mode_metric(results, "auto", "fasim_fastSIM_extend_output_stage_seconds"),
            "exclusive",
            "Final stage before caller-side file formatting/write.",
        ],
        [
            "string formatting",
            mode_metric(results, "auto", "fasim_fastSIM_extend_string_format_seconds"),
            "alias",
            "Currently aliases materialized alignment string work inside record build.",
        ],
        [
            "CIGAR",
            mode_metric(results, "auto", "fasim_fastSIM_extend_cigar_seconds"),
            "alias",
            "Currently aliases CIGAR-derived work inside record build.",
        ],
        [
            "external exact-column extend",
            mode_metric(results, "auto", "fasim_fastSIM_extend_exact_column_seconds"),
            "external",
            "P1 exact-column cost before `fastSIM_extend_from_scoreinfo`.",
        ],
    ]
    append_table(
        lines,
        ["Component", "Seconds", "Percent of emit", "Inclusive or exclusive", "Notes"],
        [
            [name, fmt_seconds(seconds), percent(seconds, emit_total), kind, notes]
            for name, seconds, kind, notes in component_rows
        ],
    )
    lines.append("")
    lines.append("## Answers")
    lines.append("")
    alignment_seconds = mode_metric(results, "auto", "fasim_fastSIM_extend_alignment_reconstruct_seconds")
    build_seconds = mode_metric(results, "auto", "fasim_fastSIM_extend_record_build_seconds")
    duplicate_seconds = mode_metric(results, "auto", "fasim_fastSIM_extend_duplicate_overlap_seconds")
    exact_seconds = mode_metric(results, "auto", "fasim_fastSIM_extend_exact_column_seconds")
    format_seconds = mode_metric(results, "auto", "fasim_fastSIM_extend_string_format_seconds")
    vector_seconds = mode_metric(results, "auto", "fasim_fastSIM_extend_vector_push_seconds")
    lines.append(f"1. Exact-column extend is external to fastSIM and costs {fmt_seconds(exact_seconds)}s.")
    lines.append(f"2. Inside fastSIM, alignment reconstruction costs {fmt_seconds(alignment_seconds)}s and record construction costs {fmt_seconds(build_seconds)}s.")
    lines.append(f"3. Output/string formatting is not separately material at the caller file-write layer in this profile; string formatting aliases record build at {fmt_seconds(format_seconds)}s.")
    lines.append(f"4. Vector push is {fmt_seconds(vector_seconds)}s, not a leading cost.")
    lines.append(f"5. Duplicate/overlap bookkeeping is {fmt_seconds(duplicate_seconds)}s.")
    if exact_seconds >= alignment_seconds and exact_seconds >= build_seconds:
        next_step = "batched exact-column extend shadow remains the largest single adjacent cost."
    elif alignment_seconds >= build_seconds:
        next_step = "alignment reconstruction should be the next target."
    else:
        next_step = "record construction / CIGAR-derived work should be the next target."
    lines.append(f"6. Next PR recommendation: {next_step}")
    lines.append("")
    lines.append("## Boundaries")
    lines.append("")
    lines.append("```text")
    lines.append("optimization logic: no")
    lines.append("GPU kernel or AUTO policy change: no")
    lines.append("scoring/threshold/non-overlap/output semantic change: no")
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
        default=str(ROOT / ".tmp" / "fasim_fastSIM_extend_emit_decomposition"),
    )
    parser.add_argument(
        "--output",
        default=str(ROOT / "docs" / "fasim_fastSIM_extend_emit_decomposition.md"),
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

    require_fastSIM_metrics(results)
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
