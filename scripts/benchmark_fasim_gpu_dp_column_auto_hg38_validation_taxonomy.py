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


SELECTED_PATHS = {
    0: "table",
    1: "compact_gpu",
    2: "manual_gpu",
}

FIRST_FAILURE_REASONS = {
    0: "none",
    1: "score_mismatch",
    2: "scoreinfo_mismatch",
    3: "exact_scoreinfo_failure",
    4: "unknown_validation_failure",
}


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


def selected_path(results: Dict[str, List[RunResult]], mode: str) -> str:
    code = mode_count(results, mode, "fasim_gpu_dp_column_auto_selected_path")
    return SELECTED_PATHS.get(code, f"unknown_{code}")


def percent(numerator: int, denominator: int) -> str:
    if denominator <= 0:
        return "n/a"
    return f"{(100.0 * numerator / denominator):.2f}%"


def digest_matches_reference(results: Dict[str, List[RunResult]], mode: str) -> bool:
    return stable_digest(results[mode]) == stable_digest(results["table_only"])


def taxonomy_rows(results: Dict[str, List[RunResult]]) -> List[List[str]]:
    mode = "auto_validate"
    total = mode_count(results, mode, "fasim_gpu_dp_column_validate_windows_total")
    digest_affected = "no" if digest_matches_reference(results, mode) else "yes"
    failed = mode_count(results, mode, "fasim_gpu_dp_column_validate_windows_failed")
    batch_windows = mode_count(results, mode, "fasim_gpu_dp_column_validate_batch_fallback_windows")
    batch_failed = mode_count(results, mode, "fasim_gpu_dp_column_validate_batch_fallback_failed_windows")
    conservative_batch = max(0, batch_windows - batch_failed)

    rows = [
        [
            "score mismatch",
            fmt_int(mode_count(results, mode, "fasim_gpu_dp_column_validate_score_mismatch_windows")),
            percent(mode_count(results, mode, "fasim_gpu_dp_column_validate_score_mismatch_windows"), total),
            digest_affected,
            "CPU max score differed from GPU peak score in validation.",
        ],
        [
            "scoreInfo mismatch",
            fmt_int(mode_count(results, mode, "fasim_gpu_dp_column_validate_scoreinfo_mismatch_windows")),
            percent(mode_count(results, mode, "fasim_gpu_dp_column_validate_scoreinfo_mismatch_windows"), total),
            digest_affected,
            "CPU scoreInfo vector differed from GPU-derived scoreInfo.",
        ],
        [
            "compact scoreInfo mismatch",
            fmt_int(mode_count(results, mode, "fasim_gpu_dp_column_validate_compact_scoreinfo_mismatch_windows")),
            percent(
                mode_count(results, mode, "fasim_gpu_dp_column_validate_compact_scoreinfo_mismatch_windows"),
                total,
            ),
            digest_affected,
            "Subset of scoreInfo mismatches while compact scoreInfo was active.",
        ],
        [
            "validation failed windows",
            fmt_int(failed),
            percent(failed, total),
            digest_affected,
            "Actual windows whose validate task returned false.",
        ],
        [
            "validation batch fallback",
            fmt_int(batch_windows),
            percent(batch_windows, total),
            digest_affected,
            "Whole batches rerun on CPU because at least one window in the batch failed validation.",
        ],
        [
            "batch-amplified fallback",
            fmt_int(conservative_batch),
            percent(conservative_batch, total),
            digest_affected,
            "Windows rerun on CPU only because they shared a failed validation batch.",
        ],
        [
            "TopK overflow in validation",
            fmt_int(mode_count(results, mode, "fasim_gpu_dp_column_validate_topk_overflow_windows")),
            percent(mode_count(results, mode, "fasim_gpu_dp_column_validate_topk_overflow_windows"), total),
            digest_affected,
            "Compact TopK overflow forced exact-column scoreInfo reconstruction during validation.",
        ],
        [
            "emit-time compact TopK exact extend",
            fmt_int(mode_count(results, mode, "fasim_gpu_dp_column_exact_scoreinfo_extend_calls")),
            percent(mode_count(results, mode, "fasim_gpu_dp_column_exact_scoreinfo_extend_calls"), total),
            digest_affected,
            "Successful compact overflow exact-column extends while emitting GPU results.",
        ],
        [
            "exact scoreInfo validation failure",
            fmt_int(mode_count(results, mode, "fasim_gpu_dp_column_validate_exact_scoreinfo_failure_windows")),
            percent(mode_count(results, mode, "fasim_gpu_dp_column_validate_exact_scoreinfo_failure_windows"), total),
            digest_affected,
            "Exact-column scoreInfo debug/reconstruction failed during validation.",
        ],
        [
            "CUDA batch failure fallback",
            fmt_int(mode_count(results, mode, "fasim_gpu_dp_column_cuda_failure_fallback_windows")),
            percent(mode_count(results, mode, "fasim_gpu_dp_column_cuda_failure_fallback_windows"), total),
            digest_affected,
            "CUDA topK column maxima batch failed before validation.",
        ],
        [
            "emit-time exact scoreInfo failure fallback",
            fmt_int(mode_count(results, mode, "fasim_gpu_dp_column_exact_scoreinfo_failure_fallback_windows")),
            percent(mode_count(results, mode, "fasim_gpu_dp_column_exact_scoreinfo_failure_fallback_windows"), total),
            digest_affected,
            "Exact scoreInfo reconstruction failed while emitting GPU results.",
        ],
    ]
    return rows


def render_report(
    *,
    workload: WorkloadSpec,
    modes: List[ModeSpec],
    results: Dict[str, List[RunResult]],
    repeat: int,
    output_path: Path,
) -> str:
    lines: List[str] = []
    lines.append("# Fasim GPU DP+column AUTO hg38 Validation Taxonomy")
    lines.append("")
    lines.append("Base branch:")
    lines.append("")
    lines.append("```text")
    lines.append("fasim-gpu-dp-column-auto-large-workload-characterization")
    lines.append("```")
    lines.append("")
    lines.append(
        "This report classifies `FASIM_GPU_DP_COLUMN_AUTO=1` validation fallbacks "
        "on a large real hg38 workload. It adds telemetry only: no GPU logic, "
        "default behavior, scoring, threshold, non-overlap, output, SIM-close, "
        "recovery, or validation semantics change."
    )
    lines.append("")
    lines.append(f"Workload: `{workload.label}`. Each mode uses {repeat} run(s); tables report medians.")
    lines.append("")
    lines.append("## Modes")
    lines.append("")
    append_table(
        lines,
        ["Mode", "Environment"],
        [["table_only", "`FASIM_TRANSFERSTRING_TABLE=1`"]]
        + [
            [mode.label, "`" + " ".join(f"{key}={value}" for key, value in mode.env.items()) + "`"]
            for mode in modes
            if mode.label != "table_only"
        ],
    )
    lines.append("")
    lines.append("## Performance And Digest")
    lines.append("")
    table_total = mode_metric(results, "table_only", "fasim_total_seconds")
    auto_total = mode_metric(results, "auto", "fasim_total_seconds")
    validate_total = mode_metric(results, "auto_validate", "fasim_total_seconds")
    append_table(
        lines,
        [
            "Workload",
            "Observed windows",
            "Observed cells",
            "Selected path",
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
                workload.label,
                fmt_int(mode_count(results, "auto", "fasim_gpu_dp_column_auto_observed_windows")),
                fmt_int(mode_count(results, "auto", "fasim_gpu_dp_column_auto_observed_cells")),
                selected_path(results, "auto"),
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
    lines.append("## Validation Counters")
    lines.append("")
    append_table(
        lines,
        [
            "Validate windows",
            "Failed windows",
            "Score mismatches",
            "ScoreInfo mismatches",
            "Compact mismatches",
            "Correctness fallbacks",
            "Compact fallback windows",
            "Emit exact extends",
            "Batch fallback batches",
            "Batch fallback windows",
            "Batch failed windows",
            "First failed window",
            "First failure reason",
        ],
        [
            [
                fmt_int(mode_count(results, "auto_validate", "fasim_gpu_dp_column_validate_windows_total")),
                fmt_int(mode_count(results, "auto_validate", "fasim_gpu_dp_column_validate_windows_failed")),
                fmt_int(mode_count(results, "auto_validate", "fasim_gpu_dp_column_validate_score_mismatch_windows")),
                fmt_int(mode_count(results, "auto_validate", "fasim_gpu_dp_column_validate_scoreinfo_mismatch_windows")),
                fmt_int(
                    mode_count(
                        results,
                        "auto_validate",
                        "fasim_gpu_dp_column_validate_compact_scoreinfo_mismatch_windows",
                    )
                ),
                fmt_int(mode_count(results, "auto_validate", "fasim_gpu_dp_column_fallbacks")),
                fmt_int(mode_count(results, "auto_validate", "fasim_gpu_dp_column_compact_scoreinfo_fallbacks")),
                fmt_int(mode_count(results, "auto_validate", "fasim_gpu_dp_column_exact_scoreinfo_extend_calls")),
                fmt_int(mode_count(results, "auto_validate", "fasim_gpu_dp_column_validate_batch_fallback_batches")),
                fmt_int(mode_count(results, "auto_validate", "fasim_gpu_dp_column_validate_batch_fallback_windows")),
                fmt_int(
                    mode_count(results, "auto_validate", "fasim_gpu_dp_column_validate_batch_fallback_failed_windows")
                ),
                str(mode_count(results, "auto_validate", "fasim_gpu_dp_column_validate_first_failed_window")),
                FIRST_FAILURE_REASONS.get(
                    mode_count(results, "auto_validate", "fasim_gpu_dp_column_validate_first_failure_reason"),
                    "unknown",
                ),
            ]
        ],
    )
    lines.append("")
    lines.append("## Fallback Taxonomy")
    lines.append("")
    append_table(
        lines,
        ["Reason", "Windows", "Percent of validated windows", "Digest affected", "Notes"],
        taxonomy_rows(results),
    )
    lines.append("")
    lines.append("## Finding")
    lines.append("")
    total = mode_count(results, "auto_validate", "fasim_gpu_dp_column_validate_windows_total")
    failed = mode_count(results, "auto_validate", "fasim_gpu_dp_column_validate_windows_failed")
    batch_windows = mode_count(results, "auto_validate", "fasim_gpu_dp_column_validate_batch_fallback_windows")
    batch_failed = mode_count(results, "auto_validate", "fasim_gpu_dp_column_validate_batch_fallback_failed_windows")
    conservative_batch = max(0, batch_windows - batch_failed)
    score_mismatches = mode_count(results, "auto_validate", "fasim_gpu_dp_column_validate_score_mismatch_windows")
    correctness_fallbacks = mode_count(results, "auto_validate", "fasim_gpu_dp_column_fallbacks")
    compact_fallbacks = mode_count(results, "auto_validate", "fasim_gpu_dp_column_compact_scoreinfo_fallbacks")
    emit_exact_extends = mode_count(results, "auto_validate", "fasim_gpu_dp_column_exact_scoreinfo_extend_calls")
    validate_exact_extends = mode_count(
        results, "auto_validate", "fasim_gpu_dp_column_validate_exact_scoreinfo_extend_windows"
    )
    lines.append(
        f"`fasim_gpu_dp_column_fallbacks={fmt_int(correctness_fallbacks)}` is batch-granularity "
        f"accounting, not a count of mismatching windows. The run validated {fmt_int(total)} windows; "
        f"{fmt_int(failed)} windows failed validation, including {fmt_int(score_mismatches)} score "
        f"mismatch windows. Those failed windows caused {fmt_int(batch_windows)} windows to be rerun "
        f"on CPU because validation fallback is applied to whole batches, leaving "
        f"{fmt_int(conservative_batch)} batch-amplified fallback windows."
    )
    lines.append("")
    lines.append(
        f"`fasim_gpu_dp_column_compact_scoreinfo_fallbacks={fmt_int(compact_fallbacks)}` splits into "
        f"{fmt_int(batch_windows)} validation batch fallback windows plus {fmt_int(emit_exact_extends)} "
        "successful emit-time compact TopK exact-column extends. Validation also reconstructed "
        f"exact scoreInfo for {fmt_int(validate_exact_extends)} TopK-overflow windows, tracked separately "
        "by the new validation telemetry."
    )
    lines.append("")
    lines.append("Digest match remains useful but is not treated as strict validation clean.")
    lines.append("")
    lines.append("## Decision")
    lines.append("")
    if failed == 0 and digest_matches_reference(results, "auto_validate"):
        decision = (
            "Validation taxonomy is clean for this workload. AUTO remains default-off; "
            "a later PR may decide whether this supports a large-workload opt-in recommendation."
        )
    elif digest_matches_reference(results, "auto_validate"):
        decision = (
            "AUTO has a strong large-workload speed signal and final digest match, but strict "
            "validation is not clean. Keep GPU AUTO default-off and do not recommend/default it "
            "until the score mismatch windows are debugged or the validation contract is refined."
        )
    else:
        decision = (
            "AUTO validation affects final digest on this workload. Stop performance claims and "
            "debug correctness before any recommendation."
        )
    lines.append(decision)
    lines.append("")
    lines.append("Forbidden-scope check:")
    lines.append("")
    lines.append("```text")
    lines.append("new GPU/kernel optimization logic: no")
    lines.append("default GPU DP+column: no")
    lines.append("validation relaxation or hidden mismatches: no")
    lines.append("scoring/threshold/non-overlap/output change: no")
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
        default=str(ROOT / ".tmp" / "fasim_gpu_dp_column_auto_hg38_validation_taxonomy"),
    )
    parser.add_argument(
        "--output",
        default=str(ROOT / "docs" / "fasim_gpu_dp_column_auto_hg38_validation_taxonomy.md"),
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
        "hg38 whole-chromosome real workload",
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

    if args.check:
        if not digest_matches_reference(results, "auto"):
            raise RuntimeError("auto digest does not match table_only")
        if not digest_matches_reference(results, "auto_validate"):
            raise RuntimeError("auto_validate digest does not match table_only")
        if mode_count(results, "auto_validate", "fasim_gpu_dp_column_validate_windows_total") <= 0:
            raise RuntimeError("auto_validate did not report validation windows")

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
