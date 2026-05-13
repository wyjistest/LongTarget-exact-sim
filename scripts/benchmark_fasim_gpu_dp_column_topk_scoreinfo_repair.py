#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Dict, Iterable, List, Optional, Tuple


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
    median_count,
    median_metric,
    run_once,
    stable_digest,
    stable_records,
)


CapSpec = Tuple[str, Optional[int]]


def parse_caps(value: str) -> List[CapSpec]:
    caps: List[CapSpec] = []
    seen = set()
    for raw_item in value.split(","):
        item = raw_item.strip().lower()
        if not item:
            continue
        if item == "current":
            spec: CapSpec = ("current", None)
        else:
            cap = int(item)
            if cap <= 0:
                raise RuntimeError(f"invalid top-K cap: {raw_item}")
            spec = (str(cap), cap)
        if spec[0] in seen:
            continue
        seen.add(spec[0])
        caps.append(spec)
    if not caps:
        raise RuntimeError("no top-K caps requested")
    return caps


def make_mode(cap_label: str, cap: Optional[int], debug_max_windows: int, debug_window_index: Optional[int]) -> ModeSpec:
    env = {
        "FASIM_TRANSFERSTRING_TABLE": "1",
        "FASIM_GPU_DP_COLUMN": "1",
        "FASIM_GPU_DP_COLUMN_VALIDATE": "1",
        "FASIM_GPU_DP_COLUMN_MISMATCH_DEBUG": "1",
        "FASIM_GPU_DP_COLUMN_DEBUG_MAX_WINDOWS": str(debug_max_windows),
    }
    if cap is not None:
        env["FASIM_GPU_DP_COLUMN_TOPK_CAP"] = str(cap)
    if debug_window_index is not None:
        env["FASIM_GPU_DP_COLUMN_DEBUG_WINDOW_INDEX"] = str(debug_window_index)
    return ModeSpec(f"topk_{cap_label}", "cuda", env)


def validation_clean(runs: List[RunResult]) -> bool:
    return all(
        median_count(runs, key) == 0
        for key in (
            "fasim_gpu_dp_column_score_mismatches",
            "fasim_gpu_dp_column_scoreinfo_mismatches",
            "fasim_gpu_dp_column_column_max_mismatches",
            "fasim_gpu_dp_column_fallbacks",
        )
    )


def mask_labels(mask: int) -> str:
    if mask == 0:
        return "none"
    labels = []
    if mask & 1:
        labels.append("score")
    if mask & 2:
        labels.append("position")
    if mask & 4:
        labels.append("count")
    if mask & 8:
        labels.append("missing-side")
    unknown = mask & ~(1 | 2 | 4 | 8)
    if unknown:
        labels.append(f"unknown-{unknown}")
    return "+".join(labels)


def render_report(
    *,
    results: Dict[str, Dict[str, List[RunResult]]],
    workloads: List[WorkloadSpec],
    cap_specs: List[CapSpec],
    repeat: int,
    output_path: Path,
) -> str:
    lines: List[str] = []
    lines.append("# Fasim GPU DP+column Top-K / ScoreInfo Repair")
    lines.append("")
    lines.append("Base branch:")
    lines.append("")
    lines.append("```text")
    lines.append("fasim-gpu-dp-column-mismatch-taxonomy")
    lines.append("```")
    lines.append("")
    lines.append(
        "This stacked PR debugs the default-off `FASIM_GPU_DP_COLUMN=1` validation "
        "blocker by sweeping bounded top-K capacity and recording first scoreInfo "
        "field differences. It does not change final output authority, scoring, "
        "threshold, non-overlap, or output semantics."
    )
    lines.append("")
    lines.append(f"Each workload/cap uses {repeat} run(s). Tables report medians.")
    lines.append("")
    lines.append("## Debug Environment")
    lines.append("")
    lines.append("```text")
    lines.append("FASIM_TRANSFERSTRING_TABLE=1")
    lines.append("FASIM_GPU_DP_COLUMN=1")
    lines.append("FASIM_GPU_DP_COLUMN_VALIDATE=1")
    lines.append("FASIM_GPU_DP_COLUMN_MISMATCH_DEBUG=1")
    lines.append("FASIM_GPU_DP_COLUMN_TOPK_CAP=<cap>   # omitted for current/default")
    lines.append("```")
    lines.append("")
    lines.append("`fasim_gpu_dp_column_scoreinfo_field_mismatch_mask` uses:")
    lines.append("")
    lines.append("```text")
    lines.append("1 = score field differs")
    lines.append("2 = position field differs")
    lines.append("4 = scoreInfo count differs")
    lines.append("8 = one side is missing at the first differing index")
    lines.append("```")
    lines.append("")

    lines.append("## Cap Sweep")
    lines.append("")
    rows: List[List[str]] = []
    for workload in workloads:
        for cap_label, _cap in cap_specs:
            mode_label = f"topk_{cap_label}"
            runs = results[workload.label][mode_label]
            field_mask = median_count(runs, "fasim_gpu_dp_column_scoreinfo_field_mismatch_mask")
            rows.append(
                [
                    workload.label,
                    cap_label,
                    str(median_count(runs, "fasim_gpu_dp_column_topk_cap")),
                    fmt_seconds(median_metric(runs, "fasim_total_seconds")),
                    fmt_seconds(median_metric(runs, "fasim_gpu_dp_column_total_seconds")),
                    fmt_seconds(median_metric(runs, "fasim_gpu_dp_column_kernel_seconds")),
                    fmt_int(median_count(runs, "fasim_gpu_dp_column_h2d_bytes")),
                    fmt_int(median_count(runs, "fasim_gpu_dp_column_d2h_bytes")),
                    str(median_count(runs, "fasim_gpu_dp_column_score_mismatches")),
                    str(median_count(runs, "fasim_gpu_dp_column_scoreinfo_mismatches")),
                    str(median_count(runs, "fasim_gpu_dp_column_pre_topk_mismatches")),
                    str(median_count(runs, "fasim_gpu_dp_column_post_topk_mismatches")),
                    str(median_count(runs, "fasim_gpu_dp_column_topk_truncated_windows")),
                    str(median_count(runs, "fasim_gpu_dp_column_topk_overflow_windows")),
                    str(median_count(runs, "fasim_gpu_dp_column_fallbacks")),
                    str(median_count(runs, "fasim_gpu_dp_column_first_mismatch_window")),
                    str(median_count(runs, "fasim_gpu_dp_column_first_mismatch_column")),
                    str(median_count(runs, "fasim_gpu_dp_column_cpu_scoreinfo_score")),
                    str(median_count(runs, "fasim_gpu_dp_column_gpu_scoreinfo_score")),
                    str(median_count(runs, "fasim_gpu_dp_column_cpu_scoreinfo_position")),
                    str(median_count(runs, "fasim_gpu_dp_column_gpu_scoreinfo_position")),
                    f"{field_mask} ({mask_labels(field_mask)})",
                ]
            )
    append_table(
        lines,
        [
            "Workload",
            "Cap",
            "Reported cap",
            "Total seconds",
            "GPU total",
            "Kernel",
            "H2D bytes",
            "D2H bytes",
            "Score mismatch",
            "ScoreInfo mismatch",
            "Pre top-K",
            "Post top-K",
            "Truncated",
            "Overflow",
            "Fallbacks",
            "First window",
            "First column",
            "CPU score",
            "GPU score",
            "CPU pos",
            "GPU pos",
            "Field mask",
        ],
        rows,
    )
    lines.append("")

    lines.append("## Digest Stability")
    lines.append("")
    rows = []
    for workload in workloads:
        reference_digest = ""
        for cap_label, _cap in cap_specs:
            mode_label = f"topk_{cap_label}"
            runs = results[workload.label][mode_label]
            digest = stable_digest(runs)
            records = stable_records(runs)
            if not reference_digest:
                reference_digest = digest
            rows.append(
                [
                    workload.label,
                    cap_label,
                    "`" + digest + "`",
                    str(records),
                    "yes" if digest == reference_digest else "no",
                ]
            )
    append_table(lines, ["Workload", "Cap", "Digest", "Records", "Matches first cap"], rows)
    lines.append("")

    lines.append("## Answers")
    lines.append("")
    rows = []
    for workload in workloads:
        clean_caps = []
        current_mismatches = None
        largest_cap_label = ""
        largest_cap_value = -1
        largest_mismatches = None
        for cap_label, cap in cap_specs:
            mode_label = f"topk_{cap_label}"
            runs = results[workload.label][mode_label]
            reported_cap = median_count(runs, "fasim_gpu_dp_column_topk_cap")
            scoreinfo = median_count(runs, "fasim_gpu_dp_column_scoreinfo_mismatches")
            fallbacks = median_count(runs, "fasim_gpu_dp_column_fallbacks")
            if validation_clean(runs):
                clean_caps.append(cap_label)
            if cap is None:
                current_mismatches = f"scoreInfo={scoreinfo}, fallbacks={fallbacks}"
            if reported_cap > largest_cap_value or (reported_cap == largest_cap_value and cap is not None):
                largest_cap_value = reported_cap
                largest_cap_label = cap_label
                largest_mismatches = f"scoreInfo={scoreinfo}, fallbacks={fallbacks}"
        rows.append(
            [
                workload.label,
                ", ".join(clean_caps) if clean_caps else "none",
                clean_caps[0] if clean_caps else "n/a",
                current_mismatches or "not run",
                f"{largest_cap_label} ({largest_cap_value}): {largest_mismatches}",
            ]
        )
    append_table(
        lines,
        [
            "Workload",
            "Zero-mismatch caps",
            "Smallest clean cap",
            "Current/default result",
            "Largest tested cap result",
        ],
        rows,
    )
    lines.append("")

    any_clean = any(
        validation_clean(results[workload.label][f"topk_{cap_label}"])
        for workload in workloads
        for cap_label, _cap in cap_specs
    )
    all_workloads_have_clean = all(
        any(validation_clean(results[workload.label][f"topk_{cap_label}"]) for cap_label, _cap in cap_specs)
        for workload in workloads
    )
    any_post_topk = any(
        median_count(results[workload.label][f"topk_{cap_label}"], "fasim_gpu_dp_column_post_topk_mismatches") != 0
        for workload in workloads
        for cap_label, _cap in cap_specs
    )
    any_pre_topk = any(
        median_count(results[workload.label][f"topk_{cap_label}"], "fasim_gpu_dp_column_pre_topk_mismatches") != 0
        for workload in workloads
        for cap_label, _cap in cap_specs
    )

    lines.append("## Decision")
    lines.append("")
    if all_workloads_have_clean:
        decision = (
            "At least one tested cap validates cleanly for every workload. The next PR "
            "can make the smallest clean cap adaptive/widened validation telemetry, "
            "then repeat performance characterization."
        )
    elif any_clean:
        decision = (
            "Only some workload/cap combinations validate cleanly. Keep GPU DP+column "
            "as a correctness prototype and continue scoreInfo representation repair "
            "before any recommended opt-in."
        )
    elif any_post_topk and not any_pre_topk:
        decision = (
            "No tested cap validates cleanly, while mismatches remain post-top-K with "
            "no pre-top-K score mismatch. The next PR should add selected-window full "
            "scoreInfo/full-column debug or widen the representation beyond the current "
            "bounded cap; do not continue performance work yet."
        )
    elif any_pre_topk:
        decision = (
            "Pre-top-K mismatches appeared. Stop scoreInfo repair and debug raw GPU DP "
            "score equivalence before performance work."
        )
    else:
        decision = (
            "No mismatch was observed in this run set. Re-run with broader debug windows "
            "before considering any opt-in recommendation."
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
    lines.append("")

    report = "\n".join(lines)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report + "\n", encoding="utf-8")
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cuda-bin", default=str(ROOT / "fasim_longtarget_cuda"))
    parser.add_argument("--caps", default="current,8,16,32,64,128,256")
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--debug-max-windows", type=int, default=1)
    parser.add_argument("--debug-window-index", type=int)
    parser.add_argument("--work-dir", default=str(ROOT / ".tmp" / "fasim_gpu_dp_column_topk_scoreinfo_repair"))
    parser.add_argument("--output", default=str(ROOT / "docs" / "fasim_gpu_dp_column_topk_scoreinfo_repair.md"))
    parser.add_argument("--human-17kb-dna")
    parser.add_argument("--human-17kb-rna")
    parser.add_argument("--human-508kb-dna")
    parser.add_argument("--human-508kb-rna")
    parser.add_argument("--require-human", action="store_true")
    parser.add_argument("--require-profile", action="store_true")
    return parser.parse_args()


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


def main() -> int:
    args = parse_args()
    try:
        repeat = args.repeat if args.repeat > 0 else 1
        cap_specs = parse_caps(args.caps)
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

        modes = [
            make_mode(cap_label, cap, args.debug_max_windows, args.debug_window_index)
            for cap_label, cap in cap_specs
        ]
        work_dir_base = Path(args.work_dir)
        results: Dict[str, Dict[str, List[RunResult]]] = {}
        for workload in workloads:
            results[workload.label] = {}
            reference_digest = ""
            for mode in modes:
                runs: List[RunResult] = []
                for run_index in range(repeat):
                    run = run_once(
                        workload=workload,
                        mode=mode,
                        bin_path=cuda_bin,
                        work_dir=work_dir_base / workload.label / mode.label / f"run{run_index + 1}",
                        require_profile=args.require_profile,
                    )
                    runs.append(run)
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
            cap_specs=cap_specs,
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
