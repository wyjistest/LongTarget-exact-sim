#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Dict, Iterable, List, Optional


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


VALIDATION_KEYS = (
    "fasim_gpu_dp_column_score_mismatches",
    "fasim_gpu_dp_column_column_max_mismatches",
    "fasim_gpu_dp_column_scoreinfo_mismatches",
    "fasim_gpu_dp_column_compact_scoreinfo_mismatches",
    "fasim_gpu_dp_column_fallbacks",
)


def add_human_workload(
    workloads: List[WorkloadSpec],
    *,
    label: str,
    dna: Optional[str],
    rna: Optional[str],
    require_human: bool,
) -> None:
    if dna and rna:
        workloads.append(
            WorkloadSpec(
                label=label,
                description="local humanLncAtlas FASTA copied from earlier profiling worktree",
                dna_path=Path(dna).resolve(),
                rna_path=Path(rna).resolve(),
            )
        )
    elif require_human:
        raise RuntimeError(f"missing required human workload paths for {label}")


def make_workloads(args: argparse.Namespace) -> List[WorkloadSpec]:
    workloads = [
        WorkloadSpec("tiny", "current testDNA/H19 smoke fixture", dna_entries=1),
        WorkloadSpec("synthetic_entries_2", "2-entry deterministic synthetic sweep", dna_entries=2),
        WorkloadSpec("synthetic_entries_4", "4-entry deterministic synthetic sweep", dna_entries=4),
        WorkloadSpec("medium_synthetic", "8-entry deterministic testDNA/H19 scale-up", dna_entries=8),
        WorkloadSpec("synthetic_entries_16", "16-entry deterministic synthetic sweep", dna_entries=16),
        WorkloadSpec("window_heavy_synthetic", "32-entry deterministic testDNA/H19 scale-up", dna_entries=32),
        WorkloadSpec("synthetic_entries_64", "64-entry deterministic synthetic sweep", dna_entries=64),
        WorkloadSpec("synthetic_entries_128", "128-entry deterministic synthetic sweep", dna_entries=128),
    ]
    add_human_workload(
        workloads,
        label="human_lnc_atlas_17kb_target",
        dna=args.human_17kb_dna,
        rna=args.human_17kb_rna,
        require_human=args.require_human,
    )
    add_human_workload(
        workloads,
        label="human_lnc_atlas_508kb_target",
        dna=args.human_508kb_dna,
        rna=args.human_508kb_rna,
        require_human=args.require_human,
    )
    return workloads


def make_modes() -> List[ModeSpec]:
    return [
        ModeSpec("table_only", "x86", {"FASIM_TRANSFERSTRING_TABLE": "1"}),
        ModeSpec(
            "compact_scoreinfo",
            "cuda",
            {
                "FASIM_TRANSFERSTRING_TABLE": "1",
                "FASIM_GPU_DP_COLUMN": "1",
                "FASIM_GPU_DP_COLUMN_COMPACT_SCOREINFO": "1",
            },
        ),
        ModeSpec(
            "compact_scoreinfo_validate",
            "cuda",
            {
                "FASIM_TRANSFERSTRING_TABLE": "1",
                "FASIM_GPU_DP_COLUMN": "1",
                "FASIM_GPU_DP_COLUMN_COMPACT_SCOREINFO": "1",
                "FASIM_GPU_DP_COLUMN_VALIDATE": "1",
            },
        ),
    ]


def is_validation_clean(runs: List[RunResult]) -> bool:
    return all(median_count(runs, key) == 0 for key in VALIDATION_KEYS)


def compact_wins(results: Dict[str, Dict[str, List[RunResult]]], label: str) -> bool:
    table_total = median_metric(results[label]["table_only"], "fasim_total_seconds")
    compact_total = median_metric(results[label]["compact_scoreinfo"], "fasim_total_seconds")
    return compact_total < table_total


def observed_windows(results: Dict[str, Dict[str, List[RunResult]]], label: str) -> int:
    return median_count(results[label]["compact_scoreinfo"], "fasim_gpu_dp_column_windows")


def observed_cells(results: Dict[str, Dict[str, List[RunResult]]], label: str) -> int:
    return median_count(results[label]["compact_scoreinfo"], "fasim_gpu_dp_column_cells")


def observed_h2d(results: Dict[str, Dict[str, List[RunResult]]], label: str) -> int:
    return median_count(results[label]["compact_scoreinfo"], "fasim_gpu_dp_column_h2d_bytes")


def observed_d2h(results: Dict[str, Dict[str, List[RunResult]]], label: str) -> int:
    return median_count(results[label]["compact_scoreinfo"], "fasim_gpu_dp_column_d2h_bytes")


def synthetic_labels(workloads: Iterable[WorkloadSpec]) -> List[str]:
    return [
        workload.label
        for workload in workloads
        if workload.dna_path is None and workload.rna_path is None
    ]


def threshold_summary(
    *,
    results: Dict[str, Dict[str, List[RunResult]]],
    workloads: List[WorkloadSpec],
) -> tuple[str, str]:
    synthetic = sorted(synthetic_labels(workloads), key=lambda label: observed_cells(results, label))
    wins = [label for label in synthetic if compact_wins(results, label)]
    losses = [label for label in synthetic if not compact_wins(results, label)]
    if wins and losses:
        first_win = min(wins, key=lambda label: observed_cells(results, label))
        last_loss = max(losses, key=lambda label: observed_cells(results, label))
        if observed_cells(results, last_loss) < observed_cells(results, first_win):
            threshold = (
                "The synthetic sweep shows a size crossover between "
                f"{last_loss} ({fmt_int(observed_windows(results, last_loss))} GPU windows, "
                f"{fmt_int(observed_cells(results, last_loss))} DP cells) and "
                f"{first_win} ({fmt_int(observed_windows(results, first_win))} GPU windows, "
                f"{fmt_int(observed_cells(results, first_win))} DP cells)."
            )
            policy = (
                "A future default-off size-gated policy can be designed around observed "
                "GPU windows or DP cells, with DP cells preferred because it directly "
                "captures the scored workload while H2D/D2H bytes mostly scale with windows "
                "in this sweep."
            )
        else:
            threshold = (
                "The synthetic sweep is not monotonic enough to name one clean crossover. "
                "Keep compact GPU as manual opt-in and collect broader repeats before adding AUTO."
            )
            policy = "Do not add `FASIM_GPU_DP_COLUMN_AUTO=1` from this evidence."
    elif wins:
        threshold = "Compact GPU wins across the synthetic sweep; smaller workloads are needed to locate the lower crossover."
        policy = "A default-off size-gated policy may be justified after confirming tiny workload overhead separately."
    else:
        threshold = "Compact GPU does not beat table-only in the synthetic sweep."
        policy = "Keep manual opt-in only."
    return threshold, policy


def render_report(
    *,
    results: Dict[str, Dict[str, List[RunResult]]],
    workloads: List[WorkloadSpec],
    modes: List[ModeSpec],
    repeat: int,
    output_path: Path,
) -> str:
    lines: List[str] = []
    lines.append("# Fasim GPU DP+column Compact Activation Threshold")
    lines.append("")
    lines.append("Base branch:")
    lines.append("")
    lines.append("```text")
    lines.append("fasim-gpu-dp-column-compact-scoreinfo-characterization")
    lines.append("```")
    lines.append("")
    lines.append(
        "This stacked PR characterizes the activation threshold for the default-off "
        "`FASIM_GPU_DP_COLUMN=1 FASIM_GPU_DP_COLUMN_COMPACT_SCOREINFO=1` path. "
        "It adds no GPU/kernel logic and does not change default Fasim output, "
        "scoring, threshold, non-overlap, SIM-close, recovery, or validation behavior."
    )
    lines.append("")
    lines.append(f"Each workload/mode uses {repeat} run(s). Tables report medians.")
    lines.append("")
    lines.append("## Modes")
    lines.append("")
    append_table(
        lines,
        ["Mode", "Binary", "Environment"],
        [
            [
                mode.label,
                mode.bin_kind,
                "`" + " ".join(f"{key}={value}" for key, value in mode.env.items()) + "`",
            ]
            for mode in modes
        ],
    )
    lines.append("")
    lines.append("## Crossover Summary")
    lines.append("")
    rows: List[List[str]] = []
    for workload in workloads:
        label = workload.label
        table_runs = results[label]["table_only"]
        compact_runs = results[label]["compact_scoreinfo"]
        validate_runs = results[label]["compact_scoreinfo_validate"]
        table_total = median_metric(table_runs, "fasim_total_seconds")
        compact_total = median_metric(compact_runs, "fasim_total_seconds")
        rows.append(
            [
                label,
                fmt_int(observed_windows(results, label)),
                fmt_int(observed_cells(results, label)),
                fmt_seconds(table_total),
                fmt_seconds(compact_total),
                fmt_speedup(speedup(table_total, compact_total)),
                fmt_seconds(median_metric(validate_runs, "fasim_total_seconds")),
                "yes" if compact_total < table_total else "no",
                "yes" if is_validation_clean(validate_runs) else "no",
                "yes" if stable_digest(compact_runs) == stable_digest(table_runs) else "no",
            ]
        )
    append_table(
        lines,
        [
            "Workload",
            "GPU windows",
            "DP cells",
            "Table seconds",
            "Compact seconds",
            "Compact speedup",
            "Compact validate seconds",
            "Compact wins",
            "Validation clean",
            "Digest matches",
        ],
        rows,
    )
    lines.append("")
    lines.append("## GPU Cost And Overflow")
    lines.append("")
    rows = []
    for workload in workloads:
        for mode_label in ("compact_scoreinfo", "compact_scoreinfo_validate"):
            runs = results[workload.label][mode_label]
            rows.append(
                [
                    workload.label,
                    mode_label,
                    str(median_count(runs, "fasim_gpu_dp_column_active")),
                    fmt_int(median_count(runs, "fasim_gpu_dp_column_windows")),
                    fmt_int(median_count(runs, "fasim_gpu_dp_column_cells")),
                    fmt_int(median_count(runs, "fasim_gpu_dp_column_h2d_bytes")),
                    fmt_int(median_count(runs, "fasim_gpu_dp_column_d2h_bytes")),
                    fmt_seconds(median_metric(runs, "fasim_gpu_dp_column_kernel_seconds")),
                    fmt_seconds(median_metric(runs, "fasim_gpu_dp_column_total_seconds")),
                    fmt_int(median_count(runs, "fasim_gpu_dp_column_compact_scoreinfo_records")),
                    str(median_count(runs, "fasim_gpu_dp_column_topk_overflow_windows")),
                    str(median_count(runs, "fasim_gpu_dp_column_compact_scoreinfo_fallbacks")),
                    str(median_count(runs, "fasim_gpu_dp_column_exact_scoreinfo_extend_calls")),
                    fmt_int(median_count(runs, "fasim_gpu_dp_column_exact_scoreinfo_extend_d2h_bytes")),
                ]
            )
    append_table(
        lines,
        [
            "Workload",
            "Mode",
            "GPU active",
            "GPU windows",
            "DP cells",
            "H2D bytes",
            "D2H bytes",
            "Kernel seconds",
            "GPU total seconds",
            "Compact records",
            "Overflow windows",
            "Compact fallback windows",
            "Full-column fallback windows",
            "Full-column fallback D2H bytes",
        ],
        rows,
    )
    lines.append("")
    lines.append("## Validation And Digest")
    lines.append("")
    rows = []
    for workload in workloads:
        label = workload.label
        reference_digest = stable_digest(results[label]["table_only"])
        for mode in modes:
            runs = results[label][mode.label]
            rows.append(
                [
                    label,
                    mode.label,
                    "`" + stable_digest(runs) + "`",
                    str(stable_records(runs)),
                    "yes" if stable_digest(runs) == reference_digest else "no",
                    str(median_count(runs, "fasim_gpu_dp_column_score_mismatches")),
                    str(median_count(runs, "fasim_gpu_dp_column_column_max_mismatches")),
                    str(median_count(runs, "fasim_gpu_dp_column_scoreinfo_mismatches")),
                    str(median_count(runs, "fasim_gpu_dp_column_compact_scoreinfo_mismatches")),
                    str(median_count(runs, "fasim_gpu_dp_column_fallbacks")),
                ]
            )
    append_table(
        lines,
        [
            "Workload",
            "Mode",
            "Digest",
            "Records",
            "Matches table-only",
            "Score mismatches",
            "Column mismatches",
            "ScoreInfo mismatches",
            "Compact mismatches",
            "Correctness fallbacks",
        ],
        rows,
    )
    lines.append("")
    lines.append("## Threshold Interpretation")
    lines.append("")
    threshold_text, policy_text = threshold_summary(results=results, workloads=workloads)
    lines.append(threshold_text)
    lines.append("")
    lines.append("Predictor read:")
    lines.append("")
    lines.append("```text")
    lines.append("windows: useful coarse gate")
    lines.append("DP cells: best current threshold predictor")
    lines.append("H2D/D2H bytes: correlated with windows in this sweep")
    lines.append("overflow/full-column fallback: report and monitor; not used as a production selector here")
    lines.append("```")
    lines.append("")
    lines.append(policy_text)
    lines.append("")
    lines.append("## Decision")
    lines.append("")
    validation_ok = all(is_validation_clean(results[workload.label]["compact_scoreinfo_validate"]) for workload in workloads)
    large_real_win = any(
        workload.label == "human_lnc_atlas_508kb_target" and compact_wins(results, workload.label)
        for workload in workloads
    )
    small_real_loss = any(
        workload.label == "human_lnc_atlas_17kb_target" and not compact_wins(results, workload.label)
        for workload in workloads
    )
    synthetic_win_labels = [label for label in synthetic_labels(workloads) if compact_wins(results, label)]
    if not validation_ok:
        decision = (
            "Validation is not clean. Stop threshold work and debug correctness before "
            "any activation policy."
        )
    elif synthetic_win_labels and large_real_win and small_real_loss:
        decision = (
            "Compact GPU is validation-clean and shows a workload-size crossover: "
            f"synthetic wins on {', '.join(synthetic_win_labels)}, 508kb real corpus wins, "
            "and 17kb real corpus still favors table-only. Next PR may design a "
            "default-off size-gated `FASIM_GPU_DP_COLUMN_AUTO=1` policy; do not "
            "recommend/default GPU DP+column yet."
        )
    elif synthetic_win_labels or large_real_win:
        decision = (
            "Compact GPU remains a workload-sensitive candidate, but the threshold "
            "evidence is incomplete or noisy. Keep manual opt-in and collect broader "
            "corpus repeats before AUTO."
        )
    else:
        decision = (
            "Compact GPU is not a clear performance win in this threshold run. Keep "
            "manual opt-in only."
        )
    lines.append(decision)
    lines.append("")
    lines.append("Future policy questions:")
    lines.append("")
    lines.append("```text")
    lines.append("FASIM_GPU_DP_COLUMN_AUTO=1: design-only candidate, not implemented here")
    lines.append("FASIM_GPU_DP_COLUMN_MIN_CELLS=<n>: candidate gate")
    lines.append("FASIM_GPU_DP_COLUMN_MIN_WINDOWS=<n>: secondary candidate gate")
    lines.append("manual opt-in only: remains current behavior")
    lines.append("```")
    lines.append("")
    lines.append("Forbidden-scope check:")
    lines.append("")
    lines.append("```text")
    lines.append("default GPU DP+column: no")
    lines.append("new CUDA/kernel logic: no")
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
    parser.add_argument("--x86-bin", default=str(ROOT / "fasim_longtarget_x86"))
    parser.add_argument("--cuda-bin", default=str(ROOT / "fasim_longtarget_cuda"))
    parser.add_argument("--repeat", type=int, default=3)
    parser.add_argument("--work-dir", default=str(ROOT / ".tmp" / "fasim_gpu_dp_column_compact_threshold"))
    parser.add_argument("--output", default=str(ROOT / "docs" / "fasim_gpu_dp_column_compact_threshold.md"))
    parser.add_argument("--human-17kb-dna")
    parser.add_argument("--human-17kb-rna")
    parser.add_argument("--human-508kb-dna")
    parser.add_argument("--human-508kb-rna")
    parser.add_argument("--require-human", action="store_true")
    parser.add_argument("--require-profile", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        repeat = args.repeat if args.repeat > 0 else 1
        x86_bin = Path(args.x86_bin).resolve()
        cuda_bin = Path(args.cuda_bin).resolve()
        if not x86_bin.exists():
            raise RuntimeError(f"missing x86 binary: {x86_bin}")
        if not cuda_bin.exists():
            raise RuntimeError(f"missing CUDA binary: {cuda_bin}")

        workloads = make_workloads(args)
        modes = make_modes()
        work_dir_base = Path(args.work_dir)
        results: Dict[str, Dict[str, List[RunResult]]] = {}
        for workload in workloads:
            results[workload.label] = {}
            reference_digest = ""
            for mode in modes:
                bin_path = cuda_bin if mode.bin_kind == "cuda" else x86_bin
                runs: List[RunResult] = []
                for run_index in range(repeat):
                    runs.append(
                        run_once(
                            workload=workload,
                            mode=mode,
                            bin_path=bin_path,
                            work_dir=work_dir_base / workload.label / mode.label / f"run{run_index + 1}",
                            require_profile=args.require_profile,
                        )
                    )
                digest = stable_digest(runs)
                if not reference_digest:
                    reference_digest = digest
                elif digest != reference_digest:
                    raise RuntimeError(
                        f"{workload.label}/{mode.label} digest mismatch: "
                        f"expected {reference_digest}, got {digest}"
                    )
                results[workload.label][mode.label] = runs

        report = render_report(
            results=results,
            workloads=workloads,
            modes=modes,
            repeat=repeat,
            output_path=Path(args.output),
        )
        print(report)
        return 0
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
