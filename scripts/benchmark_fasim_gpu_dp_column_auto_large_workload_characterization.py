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

AUTO_MIN_CELLS_KEY = "fasim_gpu_dp_column_auto_min_cells"
AUTO_MIN_WINDOWS_KEY = "fasim_gpu_dp_column_auto_min_windows"
AUTO_OBSERVED_CELLS_KEY = "fasim_gpu_dp_column_auto_observed_cells"
AUTO_OBSERVED_WINDOWS_KEY = "fasim_gpu_dp_column_auto_observed_windows"

DISABLED_REASONS = {
    0: "none",
    1: "below_threshold",
    2: "cuda_unavailable",
    3: "manual_gpu_requested",
    4: "non_fastsim",
}

SELECTED_PATHS = {
    0: "table",
    1: "compact_gpu",
    2: "manual_gpu",
}


def parse_entries(value: str) -> List[int]:
    entries: List[int] = []
    for token in value.split(","):
        token = token.strip()
        if not token:
            continue
        try:
            entry = int(token)
        except ValueError as exc:
            raise RuntimeError(f"invalid synthetic entry count: {token!r}") from exc
        if entry <= 0:
            raise RuntimeError(f"synthetic entry count must be positive: {entry}")
        if entry not in entries:
            entries.append(entry)
    if not entries:
        raise RuntimeError("at least one synthetic entry count is required")
    return entries


def synthetic_label(entries: int) -> str:
    if entries == 1:
        return "tiny"
    if entries == 8:
        return "medium_synthetic"
    if entries == 32:
        return "window_heavy_synthetic"
    return f"synthetic_entries_{entries}"


def make_synthetic_workload(entries: int) -> WorkloadSpec:
    if entries == 1:
        description = "current testDNA/H19 smoke fixture"
    else:
        description = f"{entries}-entry deterministic testDNA/H19 scale-up"
    return WorkloadSpec(synthetic_label(entries), description, dna_entries=entries)


def add_optional_workload(
    workloads: List[WorkloadSpec],
    *,
    label: str,
    description: str,
    dna: Optional[str],
    rna: Optional[str],
    require: bool,
) -> None:
    if dna and rna:
        workloads.append(
            WorkloadSpec(
                label=label,
                description=description,
                dna_path=Path(dna).resolve(),
                rna_path=Path(rna).resolve(),
            )
        )
    elif require:
        raise RuntimeError(f"missing required workload paths for {label}")


def make_workloads(args: argparse.Namespace) -> List[WorkloadSpec]:
    workloads = [make_synthetic_workload(entries) for entries in parse_entries(args.synthetic_entries)]
    add_optional_workload(
        workloads,
        label="human_lnc_atlas_17kb_target",
        description="local humanLncAtlas 17kb target FASTA",
        dna=args.human_17kb_dna,
        rna=args.human_17kb_rna,
        require=args.require_human,
    )
    add_optional_workload(
        workloads,
        label="human_lnc_atlas_508kb_target",
        description="local humanLncAtlas 508kb target FASTA",
        dna=args.human_508kb_dna,
        rna=args.human_508kb_rna,
        require=args.require_human,
    )
    add_optional_workload(
        workloads,
        label=args.large_real_label,
        description="optional larger real-corpus FASTA",
        dna=args.large_real_dna,
        rna=args.large_real_rna,
        require=args.require_large_real,
    )
    add_optional_workload(
        workloads,
        label=args.whole_genome_label,
        description="optional whole-genome-style FASTA sample",
        dna=args.whole_genome_dna,
        rna=args.whole_genome_rna,
        require=args.require_whole_genome,
    )
    return workloads


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


def mode_count(results: Dict[str, Dict[str, List[RunResult]]], label: str, mode: str, key: str) -> int:
    return median_count(results[label][mode], key)


def mode_metric(results: Dict[str, Dict[str, List[RunResult]]], label: str, mode: str, key: str) -> float:
    return median_metric(results[label][mode], key)


def selected_path(results: Dict[str, Dict[str, List[RunResult]]], label: str, mode: str) -> str:
    code = mode_count(results, label, mode, "fasim_gpu_dp_column_auto_selected_path")
    return SELECTED_PATHS.get(code, f"unknown_{code}")


def disabled_reason(results: Dict[str, Dict[str, List[RunResult]]], label: str, mode: str) -> str:
    code = mode_count(results, label, mode, "fasim_gpu_dp_column_auto_disabled_reason")
    return DISABLED_REASONS.get(code, f"unknown_{code}")


def auto_cells(results: Dict[str, Dict[str, List[RunResult]]], label: str) -> int:
    return mode_count(results, label, "auto", AUTO_OBSERVED_CELLS_KEY)


def auto_windows(results: Dict[str, Dict[str, List[RunResult]]], label: str) -> int:
    return mode_count(results, label, "auto", AUTO_OBSERVED_WINDOWS_KEY)


def auto_min_cells(results: Dict[str, Dict[str, List[RunResult]]], label: str) -> int:
    return mode_count(results, label, "auto", AUTO_MIN_CELLS_KEY)


def auto_min_windows(results: Dict[str, Dict[str, List[RunResult]]], label: str) -> int:
    return mode_count(results, label, "auto", AUTO_MIN_WINDOWS_KEY)


def threshold_matched(results: Dict[str, Dict[str, List[RunResult]]], label: str) -> bool:
    return auto_cells(results, label) >= auto_min_cells(results, label) and auto_windows(
        results, label
    ) >= auto_min_windows(results, label)


def validation_clean(runs: List[RunResult]) -> bool:
    return all(median_count(runs, key) == 0 for key in VALIDATION_KEYS)


def digest_matches_reference(results: Dict[str, Dict[str, List[RunResult]]], label: str, mode: str) -> bool:
    return stable_digest(results[label][mode]) == stable_digest(results[label]["table_only"])


def workload_kind(workload: WorkloadSpec) -> str:
    return "synthetic" if workload.dna_path is None and workload.rna_path is None else "real"


def auto_speedup_text(results: Dict[str, Dict[str, List[RunResult]]], label: str) -> str:
    if selected_path(results, label, "auto") != "compact_gpu":
        return "n/a"
    table_total = mode_metric(results, label, "table_only", "fasim_total_seconds")
    auto_total = mode_metric(results, label, "auto", "fasim_total_seconds")
    return fmt_speedup(speedup(table_total, auto_total))


def workload_notes(workloads: Iterable[WorkloadSpec]) -> List[List[str]]:
    rows: List[List[str]] = []
    for workload in workloads:
        rows.append([workload.label, workload_kind(workload), workload.description])
    return rows


def require_count(results: Dict[str, Dict[str, List[RunResult]]], label: str, mode: str, key: str, expected: int) -> None:
    observed = mode_count(results, label, mode, key)
    if observed != expected:
        raise RuntimeError(f"{label}/{mode}/{key}: expected {expected}, got {observed}")


def run_check_assertions(
    *,
    results: Dict[str, Dict[str, List[RunResult]]],
    workloads: List[WorkloadSpec],
) -> None:
    below_labels: List[str] = []
    above_labels: List[str] = []
    for workload in workloads:
        label = workload.label
        for mode in ("auto", "auto_validate"):
            require_count(results, label, mode, "fasim_gpu_dp_column_auto_requested", 1)
            if not digest_matches_reference(results, label, mode):
                raise RuntimeError(f"{label}/{mode}: digest does not match table_only")
        if not validation_clean(results[label]["auto_validate"]):
            raise RuntimeError(f"{label}/auto_validate: validation counters are not clean")

        if threshold_matched(results, label):
            above_labels.append(label)
            for mode in ("auto", "auto_validate"):
                require_count(results, label, mode, "fasim_gpu_dp_column_auto_active", 1)
                require_count(results, label, mode, "fasim_gpu_dp_column_auto_threshold_matched", 1)
                require_count(results, label, mode, "fasim_gpu_dp_column_auto_selected_path", 1)
                require_count(results, label, mode, "fasim_gpu_dp_column_auto_disabled_reason", 0)
        else:
            below_labels.append(label)
            for mode in ("auto", "auto_validate"):
                require_count(results, label, mode, "fasim_gpu_dp_column_auto_active", 0)
                require_count(results, label, mode, "fasim_gpu_dp_column_auto_threshold_matched", 0)
                require_count(results, label, mode, "fasim_gpu_dp_column_auto_selected_path", 0)
                require_count(results, label, mode, "fasim_gpu_dp_column_auto_disabled_reason", 1)

    if not below_labels:
        raise RuntimeError("check mode requires at least one below-threshold workload")
    if not above_labels:
        raise RuntimeError("check mode requires at least one threshold-matching workload")


def append_mode_table(
    lines: List[str],
    *,
    modes: List[ModeSpec],
) -> None:
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


def render_report(
    *,
    results: Dict[str, Dict[str, List[RunResult]]],
    workloads: List[WorkloadSpec],
    modes: List[ModeSpec],
    repeat: int,
    output_path: Path,
) -> str:
    lines: List[str] = []
    lines.append("# Fasim GPU DP+column AUTO Large Workload Characterization")
    lines.append("")
    lines.append("Base branch:")
    lines.append("")
    lines.append("```text")
    lines.append("fasim-gpu-dp-column-auto-policy")
    lines.append("```")
    lines.append("")
    lines.append(
        "This stacked PR characterizes the default-off `FASIM_GPU_DP_COLUMN_AUTO=1` "
        "policy on larger synthetic and optional real-corpus workloads. It adds no "
        "GPU logic and does not change default Fasim output, scoring, thresholds, "
        "non-overlap behavior, SIM-close, recovery, or validation behavior."
    )
    lines.append("")
    lines.append(f"Each workload/mode uses {repeat} run(s). Tables report medians.")
    lines.append("")
    lines.append("## Modes")
    lines.append("")
    append_mode_table(lines, modes=modes)
    lines.append("")
    lines.append("## Workloads")
    lines.append("")
    append_table(lines, ["Workload", "Kind", "Description"], workload_notes(workloads))
    lines.append("")
    lines.append("## AUTO Summary")
    lines.append("")
    rows: List[List[str]] = []
    for workload in workloads:
        label = workload.label
        table_total = mode_metric(results, label, "table_only", "fasim_total_seconds")
        auto_total = mode_metric(results, label, "auto", "fasim_total_seconds")
        validate_total = mode_metric(results, label, "auto_validate", "fasim_total_seconds")
        rows.append(
            [
                label,
                fmt_int(auto_windows(results, label)),
                fmt_int(auto_cells(results, label)),
                fmt_seconds(table_total),
                fmt_seconds(auto_total),
                auto_speedup_text(results, label),
                fmt_seconds(validate_total),
                str(mode_count(results, label, "auto", "fasim_gpu_dp_column_auto_requested")),
                str(mode_count(results, label, "auto", "fasim_gpu_dp_column_auto_active")),
                selected_path(results, label, "auto"),
                disabled_reason(results, label, "auto"),
                "yes" if validation_clean(results[label]["auto_validate"]) else "no",
                "yes" if digest_matches_reference(results, label, "auto") else "no",
            ]
        )
    append_table(
        lines,
        [
            "Workload",
            "AUTO windows",
            "AUTO DP cells",
            "Table seconds",
            "AUTO seconds",
            "AUTO speedup",
            "AUTO+validate seconds",
            "Requested",
            "Active",
            "Selected path",
            "Disabled reason",
            "Validation clean",
            "Digest matches",
        ],
        rows,
    )
    lines.append("")
    lines.append("## Stage And GPU Cost")
    lines.append("")
    rows = []
    for workload in workloads:
        label = workload.label
        for mode_label in ("auto", "auto_validate"):
            rows.append(
                [
                    label,
                    mode_label,
                    fmt_seconds(mode_metric(results, label, mode_label, "fasim_total_seconds")),
                    fmt_seconds(mode_metric(results, label, mode_label, "fasim_window_generation_seconds")),
                    fmt_seconds(mode_metric(results, label, mode_label, "fasim_dp_scoring_seconds")),
                    fmt_seconds(mode_metric(results, label, mode_label, "fasim_column_max_seconds")),
                    str(mode_count(results, label, mode_label, "fasim_gpu_dp_column_active")),
                    fmt_int(mode_count(results, label, mode_label, "fasim_gpu_dp_column_windows")),
                    fmt_int(mode_count(results, label, mode_label, "fasim_gpu_dp_column_cells")),
                    fmt_seconds(mode_metric(results, label, mode_label, "fasim_gpu_dp_column_kernel_seconds")),
                    fmt_seconds(mode_metric(results, label, mode_label, "fasim_gpu_dp_column_total_seconds")),
                    fmt_int(mode_count(results, label, mode_label, "fasim_gpu_dp_column_h2d_bytes")),
                    fmt_int(mode_count(results, label, mode_label, "fasim_gpu_dp_column_d2h_bytes")),
                    str(mode_count(results, label, mode_label, "fasim_gpu_dp_column_compact_scoreinfo_fallbacks")),
                    str(mode_count(results, label, mode_label, "fasim_gpu_dp_column_exact_scoreinfo_extend_calls")),
                ]
            )
    append_table(
        lines,
        [
            "Workload",
            "Mode",
            "Total seconds",
            "Window gen",
            "DP seconds",
            "Column seconds",
            "GPU active",
            "GPU windows",
            "GPU cells",
            "Kernel seconds",
            "GPU total seconds",
            "H2D bytes",
            "D2H bytes",
            "Compact fallback windows",
            "Full-column fallback windows",
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
            rows.append(
                [
                    label,
                    mode.label,
                    "`" + stable_digest(results[label][mode.label]) + "`",
                    str(stable_records(results[label][mode.label])),
                    "yes" if stable_digest(results[label][mode.label]) == reference_digest else "no",
                    str(mode_count(results, label, mode.label, "fasim_gpu_dp_column_score_mismatches")),
                    str(mode_count(results, label, mode.label, "fasim_gpu_dp_column_column_max_mismatches")),
                    str(mode_count(results, label, mode.label, "fasim_gpu_dp_column_scoreinfo_mismatches")),
                    str(mode_count(results, label, mode.label, "fasim_gpu_dp_column_compact_scoreinfo_mismatches")),
                    str(mode_count(results, label, mode.label, "fasim_gpu_dp_column_fallbacks")),
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
    lines.append("## Decision")
    lines.append("")
    validation_ok = all(validation_clean(results[workload.label]["auto_validate"]) for workload in workloads)
    digest_ok = all(
        digest_matches_reference(results, workload.label, mode.label)
        for workload in workloads
        for mode in modes
    )
    threshold_labels = [workload.label for workload in workloads if threshold_matched(results, workload.label)]
    active_labels = [
        workload.label
        for workload in workloads
        if mode_count(results, workload.label, "auto", "fasim_gpu_dp_column_auto_active") == 1
    ]
    speedup_labels = [
        workload.label
        for workload in workloads
        if threshold_matched(results, workload.label)
        and mode_metric(results, workload.label, "auto", "fasim_total_seconds")
        < mode_metric(results, workload.label, "table_only", "fasim_total_seconds")
    ]
    real_labels = [workload.label for workload in workloads if workload_kind(workload) == "real"]
    if not validation_ok or not digest_ok:
        decision = (
            "AUTO validation or digest checks are not clean. Stop performance claims "
            "and debug correctness before changing any recommendation."
        )
    elif threshold_labels and set(threshold_labels) == set(active_labels) and speedup_labels:
        decision = (
            "`FASIM_GPU_DP_COLUMN_AUTO=1` correctly keeps below-threshold workloads on "
            "the table path and selects compact GPU for threshold-matching workloads. "
            f"It beats table-only medians on: {', '.join(speedup_labels)}. Keep AUTO "
            "as a large-workload opt-in candidate; do not default GPU from this PR."
        )
    elif threshold_labels:
        decision = (
            "AUTO selection is digest-clean but speedup is not stable across the "
            "threshold-matching workloads in this run. Keep AUTO opt-in and collect "
            "broader large real-corpus medians before any stronger recommendation."
        )
    else:
        decision = (
            "This run did not include any threshold-matching workload. Add larger "
            "synthetic, real-corpus, or whole-genome-style inputs before evaluating AUTO."
        )
    if not real_labels:
        decision += (
            " No optional real-corpus workload was available in this run, so the result "
            "does not support a whole-genome or real-corpus order-of-magnitude claim."
        )
    lines.append(decision)
    lines.append("")
    lines.append("Forbidden-scope check:")
    lines.append("")
    lines.append("```text")
    lines.append("new GPU/kernel logic: no")
    lines.append("default GPU DP+column: no")
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
    parser.add_argument("--cuda-bin", default=str(ROOT / "fasim_longtarget_cuda"))
    parser.add_argument("--repeat", type=int, default=3)
    parser.add_argument("--synthetic-entries", default="1,32,64,128")
    parser.add_argument(
        "--work-dir",
        default=str(ROOT / ".tmp" / "fasim_gpu_dp_column_auto_large_workload_characterization"),
    )
    parser.add_argument(
        "--output",
        default=str(ROOT / "docs" / "fasim_gpu_dp_column_auto_large_workload_characterization.md"),
    )
    parser.add_argument("--human-17kb-dna")
    parser.add_argument("--human-17kb-rna")
    parser.add_argument("--human-508kb-dna")
    parser.add_argument("--human-508kb-rna")
    parser.add_argument("--large-real-dna")
    parser.add_argument("--large-real-rna")
    parser.add_argument("--large-real-label", default="large_real_corpus_target")
    parser.add_argument("--whole-genome-dna")
    parser.add_argument("--whole-genome-rna")
    parser.add_argument("--whole-genome-label", default="whole_genome_style_sample")
    parser.add_argument("--require-human", action="store_true")
    parser.add_argument("--require-large-real", action="store_true")
    parser.add_argument("--require-whole-genome", action="store_true")
    parser.add_argument("--require-profile", action="store_true")
    parser.add_argument("--check", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        repeat = args.repeat if args.repeat > 0 else 1
        cuda_bin = Path(args.cuda_bin).resolve()
        if not cuda_bin.exists():
            raise RuntimeError(f"missing CUDA Fasim binary: {cuda_bin}")

        workloads = make_workloads(args)
        modes = make_modes()
        work_dir_base = Path(args.work_dir)
        results: Dict[str, Dict[str, List[RunResult]]] = {}
        for workload in workloads:
            results[workload.label] = {}
            reference_digest = ""
            for mode in modes:
                runs: List[RunResult] = []
                for run_index in range(repeat):
                    runs.append(
                        run_once(
                            workload=workload,
                            mode=mode,
                            bin_path=cuda_bin,
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

        if args.check:
            run_check_assertions(results=results, workloads=workloads)

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
