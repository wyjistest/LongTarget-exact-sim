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
    median_count,
    run_once,
    stable_digest,
    stable_records,
)


def make_mode(label: str, debug_window_index: int, debug_max_records: int, topk_cap: Optional[int]) -> ModeSpec:
    env = {
        "FASIM_TRANSFERSTRING_TABLE": "1",
        "FASIM_GPU_DP_COLUMN": "1",
        "FASIM_GPU_DP_COLUMN_VALIDATE": "1",
        "FASIM_GPU_DP_COLUMN_MISMATCH_DEBUG": "1",
        "FASIM_GPU_DP_COLUMN_FULL_SCOREINFO_DEBUG": "1",
        "FASIM_GPU_DP_COLUMN_DEBUG_MAX_WINDOWS": "1",
        "FASIM_GPU_DP_COLUMN_DEBUG_WINDOW_INDEX": str(debug_window_index),
        "FASIM_GPU_DP_COLUMN_DEBUG_MAX_RECORDS": str(debug_max_records),
    }
    if topk_cap is not None:
        env["FASIM_GPU_DP_COLUMN_TOPK_CAP"] = str(topk_cap)
    return ModeSpec(label, "cuda", env)


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


def yn(value: bool) -> str:
    return "yes" if value else "no"


def render_report(
    *,
    results: Dict[str, List[RunResult]],
    debug_windows: Dict[str, int],
    repeat: int,
    output_path: Path,
) -> str:
    lines: List[str] = []
    lines.append("# Fasim GPU DP+column Full ScoreInfo Debug")
    lines.append("")
    lines.append("Base branch:")
    lines.append("")
    lines.append("```text")
    lines.append("fasim-gpu-dp-column-topk-scoreinfo-repair")
    lines.append("```")
    lines.append("")
    lines.append(
        "This stacked PR adds selected-window full scoreInfo diagnostics for the "
        "default-off `FASIM_GPU_DP_COLUMN=1` validation blocker. It does not "
        "change scoring, threshold, non-overlap, output semantics, validation "
        "rules, or GPU default behavior."
    )
    lines.append("")
    lines.append(f"Each selected workload/window uses {repeat} run(s). Tables report medians.")
    lines.append("")
    lines.append("## Debug Environment")
    lines.append("")
    lines.append("```text")
    lines.append("FASIM_TRANSFERSTRING_TABLE=1")
    lines.append("FASIM_GPU_DP_COLUMN=1")
    lines.append("FASIM_GPU_DP_COLUMN_VALIDATE=1")
    lines.append("FASIM_GPU_DP_COLUMN_MISMATCH_DEBUG=1")
    lines.append("FASIM_GPU_DP_COLUMN_FULL_SCOREINFO_DEBUG=1")
    lines.append("FASIM_GPU_DP_COLUMN_DEBUG_WINDOW_INDEX=<selected mismatching window>")
    lines.append("FASIM_GPU_DP_COLUMN_DEBUG_MAX_RECORDS=<bounded print sample>")
    lines.append("```")
    lines.append("")

    rows: List[List[str]] = []
    for workload, runs in results.items():
        rows.append(
            [
                workload,
                str(debug_windows[workload]),
                str(median_count(runs, "fasim_gpu_dp_column_full_debug_window_index")),
                str(median_count(runs, "fasim_gpu_dp_column_score_mismatches")),
                str(median_count(runs, "fasim_gpu_dp_column_scoreinfo_mismatches")),
                str(median_count(runs, "fasim_gpu_dp_column_pre_topk_mismatches")),
                str(median_count(runs, "fasim_gpu_dp_column_post_topk_mismatches")),
                str(median_count(runs, "fasim_gpu_dp_column_fallbacks")),
                str(median_count(runs, "fasim_gpu_dp_column_full_debug_column_mismatches")),
                str(median_count(runs, "fasim_gpu_dp_column_full_debug_column_score_delta_max")),
                str(median_count(runs, "fasim_gpu_dp_column_full_debug_cpu_records")),
                str(median_count(runs, "fasim_gpu_dp_column_full_debug_gpu_pre_topk_records")),
                str(median_count(runs, "fasim_gpu_dp_column_full_debug_gpu_post_topk_records")),
                str(median_count(runs, "fasim_gpu_dp_column_full_debug_cpu_record_missing_pre_topk")),
                str(median_count(runs, "fasim_gpu_dp_column_full_debug_cpu_record_missing_post_topk")),
                str(median_count(runs, "fasim_gpu_dp_column_full_debug_first_mismatch_rank")),
                str(median_count(runs, "fasim_gpu_dp_column_full_debug_first_mismatch_score_delta")),
                str(median_count(runs, "fasim_gpu_dp_column_full_debug_first_mismatch_position_delta")),
                str(median_count(runs, "fasim_gpu_dp_column_full_debug_first_mismatch_count_delta")),
                str(median_count(runs, "fasim_gpu_dp_column_full_debug_scoreinfo_set_mismatches")),
                str(median_count(runs, "fasim_gpu_dp_column_full_debug_scoreinfo_field_mismatches")),
            ]
        )
    append_table(
        lines,
        [
            "Workload",
            "Requested window",
            "Debug window",
            "Raw score mismatches",
            "ScoreInfo mismatches",
            "Pre top-K",
            "Post top-K",
            "Fallbacks",
            "Full column mismatches",
            "Column delta max",
            "CPU records",
            "GPU pre-topK records",
            "GPU post-topK records",
            "CPU rec missing pre",
            "CPU rec missing post",
            "First rank",
            "Score delta",
            "Position delta",
            "Count delta",
            "Set mismatches",
            "Field mismatches",
        ],
        rows,
    )
    lines.append("")
    lines.append("Telemetry notes:")
    lines.append("")
    lines.append("- `Full column mismatches` compares CPU full column max scores against GPU full column max scores before top-K.")
    lines.append("- `Set mismatches` is the exact score/position symmetric difference between CPU scoreInfo and GPU pre-topK scoreInfo.")
    lines.append("- `Count delta` is `GPU post-topK scoreInfo count - CPU scoreInfo count`; `scoreInfo` itself stores only score and position.")
    lines.append("- `CPU rec missing pre/post` checks whether the first mismatching CPU score/position record exists in GPU pre-topK or post-topK records.")
    lines.append("")

    rows = []
    for workload, runs in results.items():
        rows.append(
            [
                workload,
                "`" + stable_digest(runs) + "`",
                str(stable_records(runs)),
            ]
        )
    append_table(lines, ["Workload", "Digest", "Records"], rows)
    lines.append("")

    lines.append("## Answers")
    lines.append("")
    rows = []
    for workload, runs in results.items():
        column_clean = median_count(runs, "fasim_gpu_dp_column_full_debug_column_mismatches") == 0
        missing_pre = median_count(runs, "fasim_gpu_dp_column_full_debug_cpu_record_missing_pre_topk") != 0
        missing_post = median_count(runs, "fasim_gpu_dp_column_full_debug_cpu_record_missing_post_topk") != 0
        field_mismatch = median_count(runs, "fasim_gpu_dp_column_full_debug_scoreinfo_field_mismatches") != 0
        set_mismatch = median_count(runs, "fasim_gpu_dp_column_full_debug_scoreinfo_set_mismatches") != 0
        if not column_clean:
            next_fix = "debug raw GPU column generation"
        elif not missing_pre and missing_post:
            next_fix = "repair top-K ranking/packing or include required records"
        elif not missing_post and field_mismatch:
            next_fix = "repair scoreInfo field mapping"
        elif set_mismatch:
            next_fix = "compare scoreInfo generation semantics before top-K"
        else:
            next_fix = "broaden selected-window debug before changing validation"
        rows.append(
            [
                workload,
                yn(column_clean),
                yn(not missing_pre),
                yn(missing_post),
                yn(field_mismatch),
                next_fix,
            ]
        )
    append_table(
        lines,
        [
            "Workload",
            "Full column identical",
            "CPU record present pre-topK",
            "Lost/changed post-topK",
            "Field delta observed",
            "Next fix",
        ],
        rows,
    )
    lines.append("")

    lines.append("## Decision")
    lines.append("")
    any_column_mismatch = any(
        median_count(runs, "fasim_gpu_dp_column_full_debug_column_mismatches") != 0
        for runs in results.values()
    )
    any_missing_pre = any(
        median_count(runs, "fasim_gpu_dp_column_full_debug_cpu_record_missing_pre_topk") != 0
        for runs in results.values()
    )
    any_missing_post = any(
        median_count(runs, "fasim_gpu_dp_column_full_debug_cpu_record_missing_post_topk") != 0
        for runs in results.values()
    )
    if any_column_mismatch:
        decision = (
            "Selected-window full debug found full column max differences, so the next "
            "PR must debug raw GPU column generation before scoreInfo/top-K work."
        )
    elif any_missing_pre:
        decision = (
            "The first mismatching CPU scoreInfo record is absent before GPU top-K, "
            "so the next PR should repair GPU scoreInfo generation rather than top-K "
            "capacity alone."
        )
    elif any_missing_post:
        decision = (
            "The first mismatching CPU scoreInfo record is present before top-K but "
            "absent after bounded top-K/packing. The next PR should repair top-K "
            "ranking/representation or compact all required records."
        )
    else:
        decision = (
            "The selected records are present after top-K; remaining differences look "
            "field-level. The next PR should repair scoreInfo field mapping."
        )
    lines.append(decision)
    lines.append("")
    lines.append("Forbidden-scope check:")
    lines.append("")
    lines.append("```text")
    lines.append("default GPU enablement: no")
    lines.append("validation relaxation: no")
    lines.append("scoring/threshold/non-overlap/output change: no")
    lines.append("new filter/full CUDA rewrite: no")
    lines.append("speedup claim: no")
    lines.append("```")

    report = "\n".join(lines)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report + "\n", encoding="utf-8")
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cuda-bin", default=str(ROOT / "fasim_longtarget_cuda"))
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--debug-max-records", type=int, default=8)
    parser.add_argument("--topk-cap", type=int)
    parser.add_argument("--work-dir", default=str(ROOT / ".tmp" / "fasim_gpu_dp_column_full_scoreinfo_debug"))
    parser.add_argument("--output", default=str(ROOT / "docs" / "fasim_gpu_dp_column_full_scoreinfo_debug.md"))
    parser.add_argument("--human-17kb-dna")
    parser.add_argument("--human-17kb-rna")
    parser.add_argument("--human-17kb-debug-window-index", type=int, default=3)
    parser.add_argument("--human-508kb-dna")
    parser.add_argument("--human-508kb-rna")
    parser.add_argument("--human-508kb-debug-window-index", type=int, default=5)
    parser.add_argument("--require-human", action="store_true")
    parser.add_argument("--require-profile", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        repeat = args.repeat if args.repeat > 0 else 1
        cuda_bin = Path(args.cuda_bin).resolve()
        if not cuda_bin.exists():
            raise RuntimeError(f"missing CUDA binary: {cuda_bin}")

        workloads: List[WorkloadSpec] = []
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
        if not workloads:
            raise RuntimeError("provide at least one human workload path pair")

        debug_windows = {
            "human_lnc_atlas_17kb_target": args.human_17kb_debug_window_index,
            "human_lnc_atlas_508kb_target": args.human_508kb_debug_window_index,
        }
        work_dir_base = Path(args.work_dir)
        results: Dict[str, List[RunResult]] = {}
        for workload in workloads:
            mode = make_mode(
                workload.label,
                debug_windows[workload.label],
                args.debug_max_records,
                args.topk_cap,
            )
            runs: List[RunResult] = []
            for run_index in range(repeat):
                run = run_once(
                    workload=workload,
                    mode=mode,
                    bin_path=cuda_bin,
                    work_dir=work_dir_base / workload.label / f"run{run_index + 1}",
                    require_profile=args.require_profile,
                )
                runs.append(run)
            results[workload.label] = runs

        report = render_report(
            results=results,
            debug_windows=debug_windows,
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
