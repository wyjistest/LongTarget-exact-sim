#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Dict, List, Optional


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


SUMMARY_KEYS = [
    "fasim_total_seconds",
    "fasim_window_generation_seconds",
    "fasim_transfer_string_seconds",
    "fasim_dp_scoring_seconds",
    "fasim_column_max_seconds",
    "fasim_output_seconds",
]

GPU_KEYS = [
    "fasim_gpu_dp_column_active",
    "fasim_gpu_dp_column_windows",
    "fasim_gpu_dp_column_cells",
    "fasim_gpu_dp_column_h2d_bytes",
    "fasim_gpu_dp_column_d2h_bytes",
    "fasim_gpu_dp_column_kernel_seconds",
    "fasim_gpu_dp_column_total_seconds",
    "fasim_gpu_dp_column_score_mismatches",
    "fasim_gpu_dp_column_column_max_mismatches",
    "fasim_gpu_dp_column_scoreinfo_mismatches",
    "fasim_gpu_dp_column_fallbacks",
    "fasim_gpu_dp_column_topk_overflow_windows",
    "fasim_gpu_dp_column_compact_scoreinfo_active",
    "fasim_gpu_dp_column_compact_scoreinfo_records",
    "fasim_gpu_dp_column_compact_scoreinfo_fallbacks",
    "fasim_gpu_dp_column_exact_scoreinfo_extend_calls",
    "fasim_gpu_dp_column_exact_scoreinfo_extend_d2h_bytes",
]


def compact_fallback_windows(runs: List[RunResult]) -> int:
    return median_count(runs, "fasim_gpu_dp_column_compact_scoreinfo_fallbacks")


def full_column_extend_windows(runs: List[RunResult]) -> int:
    return median_count(runs, "fasim_gpu_dp_column_exact_scoreinfo_extend_calls")


def validation_clean(runs: List[RunResult]) -> bool:
    return all(
        median_count(runs, key) == 0
        for key in (
            "fasim_gpu_dp_column_score_mismatches",
            "fasim_gpu_dp_column_column_max_mismatches",
            "fasim_gpu_dp_column_scoreinfo_mismatches",
            "fasim_gpu_dp_column_fallbacks",
            "fasim_gpu_dp_column_compact_scoreinfo_mismatches",
        )
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
        WorkloadSpec("medium_synthetic", "8-entry deterministic testDNA/H19 scale-up", dna_entries=8),
        WorkloadSpec("window_heavy_synthetic", "32-entry deterministic testDNA/H19 scale-up", dna_entries=32),
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
            "full_column_exact_validate",
            "cuda",
            {
                "FASIM_TRANSFERSTRING_TABLE": "1",
                "FASIM_GPU_DP_COLUMN": "1",
                "FASIM_GPU_DP_COLUMN_VALIDATE": "1",
            },
        ),
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


def render_report(
    *,
    results: Dict[str, Dict[str, List[RunResult]]],
    workloads: List[WorkloadSpec],
    modes: List[ModeSpec],
    repeat: int,
    output_path: Path,
) -> str:
    lines: List[str] = []
    lines.append("# Fasim GPU DP+column Compact ScoreInfo Characterization")
    lines.append("")
    lines.append("Base branch:")
    lines.append("")
    lines.append("```text")
    lines.append("fasim-gpu-dp-column-compact-scoreinfo-packing")
    lines.append("```")
    lines.append("")
    lines.append(
        "This stacked PR characterizes the default-off "
        "`FASIM_GPU_DP_COLUMN_COMPACT_SCOREINFO=1` path across repeated runs. "
        "It adds no GPU logic and does not change default Fasim output, scoring, "
        "threshold, non-overlap, SIM-close, or recovery behavior."
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
    lines.append("## Median Wall-Clock Summary")
    lines.append("")
    rows: List[List[str]] = []
    for workload in workloads:
        table_total = median_metric(results[workload.label]["table_only"], "fasim_total_seconds")
        full_total = median_metric(results[workload.label]["full_column_exact_validate"], "fasim_total_seconds")
        for mode in modes:
            runs = results[workload.label][mode.label]
            total = median_metric(runs, "fasim_total_seconds")
            rows.append(
                [
                    workload.label,
                    mode.label,
                    fmt_seconds(total),
                    fmt_speedup(speedup(table_total, total)),
                    fmt_speedup(speedup(full_total, total)),
                    fmt_seconds(median_metric(runs, "fasim_window_generation_seconds")),
                    fmt_seconds(median_metric(runs, "fasim_transfer_string_seconds")),
                    fmt_seconds(median_metric(runs, "fasim_dp_scoring_seconds")),
                    fmt_seconds(median_metric(runs, "fasim_column_max_seconds")),
                    fmt_seconds(median_metric(runs, "fasim_output_seconds")),
                ]
            )
    append_table(
        lines,
        [
            "Workload",
            "Mode",
            "Total seconds",
            "vs table-only",
            "vs full-column exact",
            "Window gen",
            "transferString",
            "DP",
            "Column",
            "Output",
        ],
        rows,
    )
    lines.append("")
    lines.append("## GPU / Compact ScoreInfo Summary")
    lines.append("")
    rows = []
    for workload in workloads:
        for mode in modes:
            runs = results[workload.label][mode.label]
            rows.append(
                [
                    workload.label,
                    mode.label,
                    str(median_count(runs, "fasim_gpu_dp_column_active")),
                    fmt_int(median_count(runs, "fasim_gpu_dp_column_windows")),
                    fmt_int(median_count(runs, "fasim_gpu_dp_column_cells")),
                    fmt_int(median_count(runs, "fasim_gpu_dp_column_h2d_bytes")),
                    fmt_int(median_count(runs, "fasim_gpu_dp_column_d2h_bytes")),
                    fmt_seconds(median_metric(runs, "fasim_gpu_dp_column_kernel_seconds")),
                    fmt_seconds(median_metric(runs, "fasim_gpu_dp_column_total_seconds")),
                    str(median_count(runs, "fasim_gpu_dp_column_compact_scoreinfo_active")),
                    fmt_int(median_count(runs, "fasim_gpu_dp_column_compact_scoreinfo_records")),
                    fmt_int(median_count(runs, "fasim_gpu_dp_column_compact_scoreinfo_d2h_bytes")),
                    str(compact_fallback_windows(runs)),
                    str(full_column_extend_windows(runs)),
                    fmt_int(median_count(runs, "fasim_gpu_dp_column_exact_scoreinfo_extend_d2h_bytes")),
                ]
            )
    append_table(
        lines,
        [
            "Workload",
            "Mode",
            "GPU active",
            "Windows",
            "Cells",
            "H2D bytes",
            "D2H bytes",
            "Kernel seconds",
            "GPU total seconds",
            "Compact active",
            "Compact records",
            "Compact D2H bytes",
            "Compact overflow/fallback windows",
            "Full-column extend windows",
            "Full-column extend D2H bytes",
        ],
        rows,
    )
    lines.append("")
    lines.append("## Validation Summary")
    lines.append("")
    rows = []
    for workload in workloads:
        for mode_label in ("full_column_exact_validate", "compact_scoreinfo_validate"):
            runs = results[workload.label][mode_label]
            rows.append(
                [
                    workload.label,
                    mode_label,
                    str(median_count(runs, "fasim_gpu_dp_column_score_mismatches")),
                    str(median_count(runs, "fasim_gpu_dp_column_column_max_mismatches")),
                    str(median_count(runs, "fasim_gpu_dp_column_scoreinfo_mismatches")),
                    str(median_count(runs, "fasim_gpu_dp_column_compact_scoreinfo_mismatches")),
                    str(median_count(runs, "fasim_gpu_dp_column_fallbacks")),
                    "yes" if validation_clean(runs) else "no",
                ]
            )
    append_table(
        lines,
        [
            "Workload",
            "Mode",
            "Score mismatches",
            "Column mismatches",
            "ScoreInfo mismatches",
            "Compact mismatches",
            "Correctness fallbacks",
            "Clean",
        ],
        rows,
    )
    lines.append("")
    lines.append("## Digest Stability")
    lines.append("")
    rows = []
    for workload in workloads:
        reference_digest = ""
        for mode in modes:
            runs = results[workload.label][mode.label]
            digest = stable_digest(runs)
            records = stable_records(runs)
            if not reference_digest:
                reference_digest = digest
            rows.append(
                [
                    workload.label,
                    mode.label,
                    "`" + digest + "`",
                    str(records),
                    "yes" if digest == reference_digest else "no",
                ]
            )
    append_table(lines, ["Workload", "Mode", "Digest", "Records", "Matches table-only"], rows)
    lines.append("")
    lines.append("## Decision")
    lines.append("")
    validation_ok = all(
        validation_clean(results[workload.label][mode_label])
        for workload in workloads
        for mode_label in ("full_column_exact_validate", "compact_scoreinfo_validate")
    )
    compact_wins = [
        workload.label
        for workload in workloads
        if median_metric(results[workload.label]["compact_scoreinfo"], "fasim_total_seconds")
        < median_metric(results[workload.label]["table_only"], "fasim_total_seconds")
    ]
    compact_beats_full = [
        workload.label
        for workload in workloads
        if median_metric(results[workload.label]["compact_scoreinfo_validate"], "fasim_total_seconds")
        < median_metric(results[workload.label]["full_column_exact_validate"], "fasim_total_seconds")
    ]
    missing_table_wins = [
        workload.label
        for workload in workloads
        if workload.label != "tiny" and workload.label not in compact_wins
    ]
    if not validation_ok:
        decision = (
            "Validation is not clean. Stop performance characterization and debug "
            "GPU DP+column score/column/scoreInfo correctness before any recommendation."
        )
    elif compact_wins and compact_beats_full and not missing_table_wins:
        decision = (
            "`FASIM_GPU_DP_COLUMN_COMPACT_SCOREINFO=1` is validation-clean and wins "
            f"against table-only on {', '.join(compact_wins)} while improving over "
            f"full-column exact on {', '.join(compact_beats_full)}. Treat it as a "
            "possible recommended opt-in candidate after broader corpus confirmation."
        )
    elif compact_wins and compact_beats_full:
        decision = (
            "Compact scoreInfo is validation-clean and improves over full-column exact "
            f"on {', '.join(compact_beats_full)}. It beats table-only only on "
            f"{', '.join(compact_wins)}, while table-only still wins on "
            f"{', '.join(missing_table_wins)}. Keep it default-off and treat it as "
            "a workload-sensitive performance candidate, not a recommended opt-in yet."
        )
    elif compact_beats_full:
        decision = (
            "Compact scoreInfo is validation-clean and improves over full-column exact "
            f"on {', '.join(compact_beats_full)}, but it does not beat table-only "
            "medians in this run set. Keep it default-off and characterize larger workloads."
        )
    else:
        decision = (
            "Compact scoreInfo is validation-clean but does not improve enough in this "
            "run set. Keep it as a correctness/packing option, not a performance recommendation."
        )
    lines.append(decision)
    lines.append("")
    lines.append("Forbidden-scope check:")
    lines.append("")
    lines.append("```text")
    lines.append("default GPU enablement: no")
    lines.append("compact recommendation/default: no")
    lines.append("scoring/threshold/non-overlap/output change: no")
    lines.append("SIM-close/recovery change: no")
    lines.append("validation relaxation: no")
    lines.append("```")
    lines.append("")

    report = "\n".join(lines)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report + "\n", encoding="utf-8")
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--x86-bin", default=str(ROOT / "fasim_longtarget_x86"))
    parser.add_argument("--cuda-bin", default=str(ROOT / "fasim_longtarget_cuda"))
    parser.add_argument("--repeat", type=int, default=3)
    parser.add_argument("--work-dir", default=str(ROOT / ".tmp" / "fasim_gpu_dp_column_compact_scoreinfo_characterization"))
    parser.add_argument("--output", default=str(ROOT / "docs" / "fasim_gpu_dp_column_compact_scoreinfo_characterization.md"))
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
