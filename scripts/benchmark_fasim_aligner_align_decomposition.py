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


ALIGN_KEYS = [
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


def percent(numerator: float, denominator: float) -> str:
    if denominator <= 0.0:
        return "n/a"
    return f"{(100.0 * numerator / denominator):.2f}%"


def fmt_bases(value: float) -> str:
    return f"{value:.2f}"


def require_align_metrics(results: Dict[str, List[RunResult]]) -> None:
    for mode in ["auto", "auto_validate"]:
        for key in ALIGN_KEYS:
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
    lines.append("# Fasim aligner.Align Decomposition")
    lines.append("")
    lines.append(
        "This telemetry-only report characterizes `aligner.Align` calls inside "
        "`fastSIM_extend_from_scoreinfo` under "
        "`FASIM_TRANSFERSTRING_TABLE=1 FASIM_GPU_DP_COLUMN_AUTO=1`. It does not "
        "bypass Align and does not change output, scoring, thresholds, non-overlap, "
        "GPU kernels, AUTO policy, SIM-close, or recovery behavior."
    )
    lines.append("")
    lines.append(f"Workload: `{workload.label}`. Each mode uses {repeat} run(s); tables report medians.")
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
    lines.append("## Align Call Distribution")
    lines.append("")
    append_table(
        lines,
        [
            "Mode",
            "Calls",
            "Total seconds",
            "Total cells",
            "Avg query len",
            "Avg target len",
            "Max query len",
            "Max target len",
            "Seconds / call",
        ],
        [
            [
                mode,
                fmt_int(mode_count(results, mode, "fasim_aligner_align_calls")),
                fmt_seconds(mode_metric(results, mode, "fasim_aligner_align_seconds")),
                fmt_int(mode_count(results, mode, "fasim_aligner_align_total_cells")),
                fmt_bases(mode_metric(results, mode, "fasim_aligner_align_avg_query_len")),
                fmt_bases(mode_metric(results, mode, "fasim_aligner_align_avg_target_len")),
                fmt_int(mode_count(results, mode, "fasim_aligner_align_max_query_len")),
                fmt_int(mode_count(results, mode, "fasim_aligner_align_max_target_len")),
                fmt_seconds(
                    mode_metric(results, mode, "fasim_aligner_align_seconds") /
                    max(1, mode_count(results, mode, "fasim_aligner_align_calls"))
                ),
            ]
            for mode in ["auto", "auto_validate"]
        ],
    )
    lines.append("")
    lines.append("## Align Outcome")
    lines.append("")
    considered = mode_count(results, "auto", "fasim_aligner_align_records_considered")
    emitted = mode_count(results, "auto", "fasim_aligner_align_records_emitted")
    rejected = mode_count(results, "auto", "fasim_aligner_align_records_rejected_after_align")
    append_table(
        lines,
        [
            "Mode",
            "Records considered",
            "Emitted",
            "Rejected after Align",
            "Rejected fraction",
            "ScoreInfo score matches",
            "ScoreInfo position matches",
            "Required for CIGAR",
            "Required for score",
            "Required for coordinates",
        ],
        [
            [
                mode,
                fmt_int(mode_count(results, mode, "fasim_aligner_align_records_considered")),
                fmt_int(mode_count(results, mode, "fasim_aligner_align_records_emitted")),
                fmt_int(mode_count(results, mode, "fasim_aligner_align_records_rejected_after_align")),
                percent(
                    mode_count(results, mode, "fasim_aligner_align_records_rejected_after_align"),
                    max(1, mode_count(results, mode, "fasim_aligner_align_records_considered")),
                ),
                fmt_int(mode_count(results, mode, "fasim_aligner_align_scoreinfo_exact_score_matches")),
                fmt_int(mode_count(results, mode, "fasim_aligner_align_scoreinfo_position_matches")),
                fmt_int(mode_count(results, mode, "fasim_aligner_align_required_for_cigar")),
                fmt_int(mode_count(results, mode, "fasim_aligner_align_required_for_score")),
                fmt_int(mode_count(results, mode, "fasim_aligner_align_required_for_coordinates")),
            ]
            for mode in ["auto", "auto_validate"]
        ],
    )
    lines.append("")
    lines.append("## Bypass Feasibility")
    lines.append("")
    append_table(
        lines,
        [
            "Mode",
            "Shadow enabled",
            "Bypassable",
            "Non-bypassable",
            "Estimated saved seconds",
            "Score mismatches",
            "Coordinate mismatches",
            "CIGAR missing records",
            "Blockers",
        ],
        [
            [
                mode,
                fmt_int(mode_count(results, mode, "fasim_aligner_align_bypass_shadow_enabled")),
                fmt_int(mode_count(results, mode, "fasim_aligner_align_bypass_shadow_bypassable_records")),
                fmt_int(mode_count(results, mode, "fasim_aligner_align_bypass_shadow_non_bypassable_records")),
                fmt_seconds(mode_metric(results, mode, "fasim_aligner_align_bypass_shadow_est_seconds_saved")),
                fmt_int(mode_count(results, mode, "fasim_aligner_align_bypass_shadow_score_mismatches")),
                fmt_int(mode_count(results, mode, "fasim_aligner_align_bypass_shadow_coordinate_mismatches")),
                fmt_int(mode_count(results, mode, "fasim_aligner_align_bypass_shadow_cigar_missing_records")),
                "No bypass estimator is active in this telemetry PR.",
            ]
            for mode in ["auto", "auto_validate"]
        ],
    )
    lines.append("")
    lines.append("## Decision")
    lines.append("")
    align_seconds = mode_metric(results, "auto", "fasim_aligner_align_seconds")
    align_calls = mode_count(results, "auto", "fasim_aligner_align_calls")
    max_target = mode_count(results, "auto", "fasim_aligner_align_max_target_len")
    avg_target = mode_metric(results, "auto", "fasim_aligner_align_avg_target_len")
    rejection_fraction = 100.0 * rejected / max(1, considered)
    lines.append(
        f"`aligner.Align` accounts for {fmt_seconds(align_seconds)}s across "
        f"{fmt_int(align_calls)} calls. Average target length is "
        f"{fmt_bases(avg_target)} bases and max target length is {fmt_int(max_target)} bases."
    )
    lines.append("")
    if rejection_fraction >= 50.0:
        lines.append(
            f"{percent(rejected, max(1, considered))} of considered records are rejected after Align. "
            "The next PR should investigate pre-align filtering or a scoreInfo-to-output shadow."
        )
    elif max_target > avg_target * 10.0:
        lines.append(
            "Align calls are dominated by unusually large targets. The next PR should profile individual large calls or batch them."
        )
    else:
        lines.append(
            "Align calls are numerous and moderately sized. The next PR should investigate batched alignment reconstruction or a safe pre-align filter."
        )
    lines.append("")
    lines.append("## Boundaries")
    lines.append("")
    lines.append("```text")
    lines.append("bypass Align in real output: no")
    lines.append("CIGAR/alignment output semantic change: no")
    lines.append("scoring/threshold/non-overlap change: no")
    lines.append("GPU kernel or AUTO policy change: no")
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
        default=str(ROOT / ".tmp" / "fasim_aligner_align_decomposition"),
    )
    parser.add_argument(
        "--output",
        default=str(ROOT / "docs" / "fasim_aligner_align_decomposition.md"),
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

    require_align_metrics(results)
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
