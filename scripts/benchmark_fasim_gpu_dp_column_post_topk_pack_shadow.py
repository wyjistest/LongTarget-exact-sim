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
from benchmark_fasim_gpu_dp_column_full_scoreinfo_debug import add_human_workload  # noqa: E402


def make_mode(label: str, debug_window_index: int, debug_max_records: int, topk_cap: Optional[int]) -> ModeSpec:
    env = {
        "FASIM_TRANSFERSTRING_TABLE": "1",
        "FASIM_GPU_DP_COLUMN": "1",
        "FASIM_GPU_DP_COLUMN_VALIDATE": "1",
        "FASIM_GPU_DP_COLUMN_MISMATCH_DEBUG": "1",
        "FASIM_GPU_DP_COLUMN_FULL_SCOREINFO_DEBUG": "1",
        "FASIM_GPU_DP_COLUMN_POST_TOPK_PACK_SHADOW": "1",
        "FASIM_GPU_DP_COLUMN_DEBUG_MAX_WINDOWS": "1",
        "FASIM_GPU_DP_COLUMN_DEBUG_WINDOW_INDEX": str(debug_window_index),
        "FASIM_GPU_DP_COLUMN_DEBUG_MAX_RECORDS": str(debug_max_records),
    }
    if topk_cap is not None:
        env["FASIM_GPU_DP_COLUMN_TOPK_CAP"] = str(topk_cap)
    return ModeSpec(label, "cuda", env)


def yes_no(value: bool) -> str:
    return "yes" if value else "no"


def render_report(
    *,
    results: Dict[str, List[RunResult]],
    debug_windows: Dict[str, int],
    repeat: int,
    output_path: Path,
) -> str:
    lines: List[str] = []
    lines.append("# Fasim GPU DP+column Post-TopK Pack Shadow")
    lines.append("")
    lines.append("Base branch:")
    lines.append("")
    lines.append("```text")
    lines.append("fasim-gpu-dp-column-full-scoreinfo-debug")
    lines.append("```")
    lines.append("")
    lines.append(
        "This stacked PR adds a default-off post-topK scoreInfo packing shadow for "
        "`FASIM_GPU_DP_COLUMN=1`. It compares CPU authoritative scoreInfo, a "
        "CPU-compatible pack built from GPU pre-topK/full-column records, and the "
        "current GPU post-topK pack. It does not change final output authority or "
        "relax validation."
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
    lines.append("FASIM_GPU_DP_COLUMN_POST_TOPK_PACK_SHADOW=1")
    lines.append("FASIM_GPU_DP_COLUMN_DEBUG_WINDOW_INDEX=<selected mismatching window>")
    lines.append("```")
    lines.append("")

    rows: List[List[str]] = []
    for workload, runs in results.items():
        rows.append(
            [
                workload,
                str(debug_windows[workload]),
                str(median_count(runs, "fasim_gpu_dp_column_score_mismatches")),
                str(median_count(runs, "fasim_gpu_dp_column_scoreinfo_mismatches")),
                str(median_count(runs, "fasim_gpu_dp_column_post_topk_cpu_records")),
                str(median_count(runs, "fasim_gpu_dp_column_post_topk_gpu_pre_records")),
                str(median_count(runs, "fasim_gpu_dp_column_post_topk_gpu_post_records")),
                str(median_count(runs, "fasim_gpu_dp_column_post_topk_cpu_pack_mismatches")),
                str(median_count(runs, "fasim_gpu_dp_column_post_topk_gpu_pack_mismatches")),
                str(median_count(runs, "fasim_gpu_dp_column_post_topk_missing_records")),
                str(median_count(runs, "fasim_gpu_dp_column_post_topk_extra_records")),
                str(median_count(runs, "fasim_gpu_dp_column_post_topk_rank_mismatches")),
                str(median_count(runs, "fasim_gpu_dp_column_post_topk_field_mismatch_mask")),
                str(median_count(runs, "fasim_gpu_dp_column_post_topk_count_mismatches")),
                str(median_count(runs, "fasim_gpu_dp_column_post_topk_position_mismatches")),
                str(median_count(runs, "fasim_gpu_dp_column_post_topk_score_mismatches")),
            ]
        )
    append_table(
        lines,
        [
            "Workload",
            "Window",
            "Raw score mismatches",
            "ScoreInfo mismatches",
            "CPU records",
            "GPU pre records",
            "GPU post records",
            "CPU-pack mismatches",
            "GPU-pack mismatches",
            "Missing",
            "Extra",
            "Rank mismatches",
            "Field mask",
            "Count mismatches",
            "Position mismatches",
            "Score mismatches",
        ],
        rows,
    )
    lines.append("")

    lines.append("Field mask:")
    lines.append("")
    lines.append("```text")
    lines.append("1 = score field/rank differs")
    lines.append("2 = position field/rank differs")
    lines.append("4 = output record count differs")
    lines.append("8 = exact score/position record missing or extra")
    lines.append("```")
    lines.append("")

    rows = []
    for workload, runs in results.items():
        rows.append([workload, "`" + stable_digest(runs) + "`", str(stable_records(runs))])
    append_table(lines, ["Workload", "Digest", "Records"], rows)
    lines.append("")

    lines.append("## Answers")
    lines.append("")
    rows = []
    for workload, runs in results.items():
        cpu_pack_clean = median_count(runs, "fasim_gpu_dp_column_post_topk_cpu_pack_mismatches") == 0
        gpu_pack_clean = median_count(runs, "fasim_gpu_dp_column_post_topk_gpu_pack_mismatches") == 0
        missing = median_count(runs, "fasim_gpu_dp_column_post_topk_missing_records")
        count_mismatch = median_count(runs, "fasim_gpu_dp_column_post_topk_count_mismatches") != 0
        if cpu_pack_clean and not gpu_pack_clean:
            next_fix = "repair current GPU postTopK pack/rank representation"
        elif not cpu_pack_clean:
            next_fix = "repair scoreInfo field mapping before postTopK"
        elif count_mismatch:
            next_fix = "document and repair count/output-record semantics"
        else:
            next_fix = "broaden selected windows before changing behavior"
        rows.append(
            [
                workload,
                yes_no(cpu_pack_clean),
                yes_no(gpu_pack_clean),
                str(missing),
                yes_no(count_mismatch),
                next_fix,
            ]
        )
    append_table(
        lines,
        [
            "Workload",
            "CPU-compatible pack matches CPU",
            "Current GPU pack matches CPU",
            "Missing records",
            "Count mismatch",
            "Next fix",
        ],
        rows,
    )
    lines.append("")

    all_cpu_pack_clean = all(
        median_count(runs, "fasim_gpu_dp_column_post_topk_cpu_pack_mismatches") == 0
        for runs in results.values()
    )
    any_gpu_pack_dirty = any(
        median_count(runs, "fasim_gpu_dp_column_post_topk_gpu_pack_mismatches") != 0
        for runs in results.values()
    )
    lines.append("## Decision")
    lines.append("")
    if all_cpu_pack_clean and any_gpu_pack_dirty:
        decision = (
            "CPU-compatible packing over GPU pre-topK records matches CPU authoritative "
            "scoreInfo, while the current GPU post-topK pack still mismatches. The next "
            "PR should align GPU postTopK packing/ranking with the CPU-compatible path."
        )
    elif not all_cpu_pack_clean:
        decision = (
            "CPU-compatible packing over GPU pre-topK records still mismatches CPU. "
            "Fix scoreInfo field mapping/generation before postTopK packing."
        )
    else:
        decision = (
            "Selected windows did not reproduce a postTopK pack mismatch. Broaden debug "
            "selection before making a representation change."
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
    parser.add_argument("--work-dir", default=str(ROOT / ".tmp" / "fasim_gpu_dp_column_post_topk_pack_shadow"))
    parser.add_argument("--output", default=str(ROOT / "docs" / "fasim_gpu_dp_column_post_topk_pack_shadow.md"))
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
                runs.append(
                    run_once(
                        workload=workload,
                        mode=mode,
                        bin_path=cuda_bin,
                        work_dir=work_dir_base / workload.label / f"run{run_index + 1}",
                        require_profile=args.require_profile,
                    )
                )
            results[workload.label] = runs

        print(
            render_report(
                results=results,
                debug_windows=debug_windows,
                repeat=repeat,
                output_path=Path(args.output),
            )
        )
        return 0
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
