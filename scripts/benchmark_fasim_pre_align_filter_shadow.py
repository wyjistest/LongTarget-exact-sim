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


PRE_ALIGN_KEYS = [
    "fasim_pre_align_filter_shadow_enabled",
    "fasim_pre_align_filter_candidates",
    "fasim_pre_align_filter_actual_emitted",
    "fasim_pre_align_filter_actual_rejected",
    "fasim_pre_align_filter_predicted_reject",
    "fasim_pre_align_filter_true_reject",
    "fasim_pre_align_filter_false_reject",
    "fasim_pre_align_filter_false_keep",
    "fasim_pre_align_filter_precision",
    "fasim_pre_align_filter_recall",
    "fasim_pre_align_filter_est_align_calls_saved",
    "fasim_pre_align_filter_est_align_cells_saved",
    "fasim_pre_align_filter_est_seconds_saved",
    "fasim_pre_align_filter_output_digest_affected",
    "fasim_pre_align_filter_actual_emitted_align_calls",
    "fasim_pre_align_filter_actual_rejected_align_calls",
    "fasim_pre_align_filter_actual_emitted_align_cells",
    "fasim_pre_align_filter_actual_rejected_align_cells",
    "fasim_pre_align_reject_reason_score",
    "fasim_pre_align_reject_reason_Nt",
    "fasim_pre_align_reject_reason_length",
    "fasim_pre_align_reject_reason_coordinates",
    "fasim_pre_align_reject_reason_overlap",
    "fasim_pre_align_reject_reason_cigar",
    "fasim_pre_align_reject_reason_unknown",
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
                "FASIM_PRE_ALIGN_FILTER_SHADOW": "1",
            },
        ),
        ModeSpec(
            "auto_validate",
            "cuda",
            {
                "FASIM_TRANSFERSTRING_TABLE": "1",
                "FASIM_GPU_DP_COLUMN_AUTO": "1",
                "FASIM_GPU_DP_COLUMN_VALIDATE": "1",
                "FASIM_PRE_ALIGN_FILTER_SHADOW": "1",
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


def require_pre_align_metrics(results: Dict[str, List[RunResult]]) -> None:
    for mode in ["auto", "auto_validate"]:
        for key in PRE_ALIGN_KEYS:
            mode_metric(results, mode, key)


def render_report(
    *,
    workload: WorkloadSpec,
    results: Dict[str, List[RunResult]],
    repeat: int,
    output_path: Path,
) -> str:
    lines: List[str] = []
    lines.append("# Fasim Pre-Align Filter Shadow")
    lines.append("")
    lines.append(
        "This diagnostic report evaluates a pre-align reject estimator before "
        "`aligner.Align` while leaving the real output path unchanged. The shadow "
        "does not skip Align, does not change output, scoring, thresholds, "
        "non-overlap, GPU kernels, AUTO policy, SIM-close, or recovery behavior."
    )
    lines.append("")
    lines.append(f"Workload: `{workload.label}`. Each mode uses {repeat} run(s); tables report medians.")
    lines.append("")

    table_total = mode_metric(results, "table_only", "fasim_total_seconds")
    auto_total = mode_metric(results, "auto", "fasim_total_seconds")
    validate_total = mode_metric(results, "auto_validate", "fasim_total_seconds")
    lines.append("## Performance")
    lines.append("")
    append_table(
        lines,
        [
            "Observed windows",
            "Observed cells",
            "Table seconds",
            "AUTO+shadow seconds",
            "AUTO speedup",
            "AUTO+validate+shadow seconds",
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

    lines.append("## Shadow Outcome")
    lines.append("")
    append_table(
        lines,
        [
            "Mode",
            "Candidates",
            "Actual emitted",
            "Actual rejected",
            "Predicted reject",
            "True reject",
            "False reject",
            "False keep",
            "Precision",
            "Recall",
            "Digest affected",
        ],
        [
            [
                mode,
                fmt_int(mode_count(results, mode, "fasim_pre_align_filter_candidates")),
                fmt_int(mode_count(results, mode, "fasim_pre_align_filter_actual_emitted")),
                fmt_int(mode_count(results, mode, "fasim_pre_align_filter_actual_rejected")),
                fmt_int(mode_count(results, mode, "fasim_pre_align_filter_predicted_reject")),
                fmt_int(mode_count(results, mode, "fasim_pre_align_filter_true_reject")),
                fmt_int(mode_count(results, mode, "fasim_pre_align_filter_false_reject")),
                fmt_int(mode_count(results, mode, "fasim_pre_align_filter_false_keep")),
                percent(
                    mode_count(results, mode, "fasim_pre_align_filter_true_reject"),
                    mode_count(results, mode, "fasim_pre_align_filter_predicted_reject"),
                ),
                percent(
                    mode_count(results, mode, "fasim_pre_align_filter_true_reject"),
                    mode_count(results, mode, "fasim_pre_align_filter_actual_rejected"),
                ),
                fmt_int(mode_count(results, mode, "fasim_pre_align_filter_output_digest_affected")),
            ]
            for mode in ["auto", "auto_validate"]
        ],
    )
    lines.append("")

    lines.append("## Estimated Savings")
    lines.append("")
    append_table(
        lines,
        [
            "Mode",
            "Align seconds",
            "Align calls",
            "Align cells",
            "Rejected align calls",
            "Rejected align cells",
            "Est calls saved",
            "Est cells saved",
            "Est seconds saved",
        ],
        [
            [
                mode,
                fmt_seconds(mode_metric(results, mode, "fasim_aligner_align_seconds")),
                fmt_int(mode_count(results, mode, "fasim_aligner_align_calls")),
                fmt_int(mode_count(results, mode, "fasim_aligner_align_total_cells")),
                fmt_int(mode_count(results, mode, "fasim_pre_align_filter_actual_rejected_align_calls")),
                fmt_int(mode_count(results, mode, "fasim_pre_align_filter_actual_rejected_align_cells")),
                fmt_int(mode_count(results, mode, "fasim_pre_align_filter_est_align_calls_saved")),
                fmt_int(mode_count(results, mode, "fasim_pre_align_filter_est_align_cells_saved")),
                fmt_seconds(mode_metric(results, mode, "fasim_pre_align_filter_est_seconds_saved")),
            ]
            for mode in ["auto", "auto_validate"]
        ],
    )
    lines.append("")

    lines.append("## Rejection Reason Taxonomy")
    lines.append("")
    append_table(
        lines,
        [
            "Mode",
            "Score/identity/stability",
            "Nt",
            "Length",
            "Coordinates",
            "Overlap/rank",
            "CIGAR",
            "Unknown",
        ],
        [
            [
                mode,
                fmt_int(mode_count(results, mode, "fasim_pre_align_reject_reason_score")),
                fmt_int(mode_count(results, mode, "fasim_pre_align_reject_reason_Nt")),
                fmt_int(mode_count(results, mode, "fasim_pre_align_reject_reason_length")),
                fmt_int(mode_count(results, mode, "fasim_pre_align_reject_reason_coordinates")),
                fmt_int(mode_count(results, mode, "fasim_pre_align_reject_reason_overlap")),
                fmt_int(mode_count(results, mode, "fasim_pre_align_reject_reason_cigar")),
                fmt_int(mode_count(results, mode, "fasim_pre_align_reject_reason_unknown")),
            ]
            for mode in ["auto", "auto_validate"]
        ],
    )
    lines.append("")

    lines.append("## Strategy Summary")
    lines.append("")
    predicted = mode_count(results, "auto", "fasim_pre_align_filter_predicted_reject")
    true_reject = mode_count(results, "auto", "fasim_pre_align_filter_true_reject")
    false_reject = mode_count(results, "auto", "fasim_pre_align_filter_false_reject")
    false_keep = mode_count(results, "auto", "fasim_pre_align_filter_false_keep")
    actual_rejected = mode_count(results, "auto", "fasim_pre_align_filter_actual_rejected")
    rejected_align_seconds = mode_metric(results, "auto", "fasim_aligner_align_seconds") * (
        mode_count(results, "auto", "fasim_pre_align_filter_actual_rejected_align_cells") /
        max(1, mode_count(results, "auto", "fasim_aligner_align_total_cells"))
    )
    append_table(
        lines,
        [
            "Strategy",
            "Predicted reject",
            "True reject",
            "False reject",
            "False keep",
            "Est calls saved",
            "Est cells saved",
            "Est seconds saved",
            "Notes",
        ],
        [
            [
                "combined conservative guard",
                fmt_int(predicted),
                fmt_int(true_reject),
                fmt_int(false_reject),
                fmt_int(false_keep),
                fmt_int(mode_count(results, "auto", "fasim_pre_align_filter_est_align_calls_saved")),
                fmt_int(mode_count(results, "auto", "fasim_pre_align_filter_est_align_cells_saved")),
                fmt_seconds(mode_metric(results, "auto", "fasim_pre_align_filter_est_seconds_saved")),
                "score/position/max-cutlength metadata only; real path unchanged",
            ],
            [
                "oracle upper bound",
                fmt_int(actual_rejected),
                fmt_int(actual_rejected),
                "0",
                "0",
                fmt_int(mode_count(results, "auto", "fasim_pre_align_filter_actual_rejected_align_calls")),
                fmt_int(mode_count(results, "auto", "fasim_pre_align_filter_actual_rejected_align_cells")),
                fmt_seconds(rejected_align_seconds),
                "analysis only; uses post-align outcome",
            ],
        ],
    )
    lines.append("")

    lines.append("## Decision")
    lines.append("")
    if false_reject == 0 and mode_metric(results, "auto", "fasim_pre_align_filter_est_seconds_saved") >= 3.0:
        lines.append(
            "The shadow found a zero-false-reject pre-align filter with material estimated savings. "
            "A later PR can consider a real opt-in guarded by validation/fallback."
        )
    elif false_reject == 0 and predicted > 0:
        lines.append(
            "The shadow found a zero-false-reject filter, but estimated savings are small. "
            "Keep this as telemetry unless larger workloads show more value."
        )
    elif predicted == 0:
        lines.append(
            "The conservative pre-align guard did not reject any candidates. "
            "Do not implement a real filter from this strategy; evaluate richer features or batching."
        )
    else:
        lines.append(
            "The pre-align guard has false rejects. Do not implement it in the real path; "
            "move to richer shadow features, scoreInfo-to-output shadow, or batched alignment reconstruction."
        )
    lines.append("")
    lines.append("## Boundaries")
    lines.append("")
    lines.append("```text")
    lines.append("skip Align in real path: no")
    lines.append("output semantic change: no")
    lines.append("scoring/threshold/non-overlap change: no")
    lines.append("GPU kernel or AUTO policy change: no")
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
    parser.add_argument(
        "--work-dir",
        default=str(ROOT / ".tmp" / "fasim_pre_align_filter_shadow_benchmark"),
    )
    parser.add_argument(
        "--output",
        default=str(ROOT / "docs" / "fasim_pre_align_filter_shadow.md"),
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

    require_pre_align_metrics(results)
    if args.check:
        if not digest_matches_reference(results, "auto"):
            raise RuntimeError("auto digest does not match table_only")
        if not digest_matches_reference(results, "auto_validate"):
            raise RuntimeError("auto_validate digest does not match table_only")
        if mode_count(results, "auto", "fasim_gpu_dp_column_auto_active") != 1:
            raise RuntimeError("AUTO did not activate GPU DP+column")
        if mode_count(results, "auto", "fasim_pre_align_filter_output_digest_affected") != 0:
            raise RuntimeError("pre-align shadow affected output digest")

    render_report(
        workload=workload,
        results=results,
        repeat=args.repeat,
        output_path=Path(args.output),
    )
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
