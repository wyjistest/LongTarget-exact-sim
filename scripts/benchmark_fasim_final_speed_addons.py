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
from benchmark_fasim_ssw_avx2_hybrid_modes import AVX2_KEYS, SSW_DECOMPOSITION_KEYS  # noqa: E402
from benchmark_fasim_ssw_profile_context import PROFILE_CONTEXT_KEYS  # noqa: E402


CORE_KEYS = [
    "fasim_total_seconds",
    "fasim_aligner_align_seconds",
    "fasim_aligner_align_cpu_ssw_align_seconds",
    "fasim_output_digest_available",
    "fasim_canonical_output_records",
]


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
    description = (
        "current testDNA/H19 smoke fixture"
        if entries == 1
        else f"{entries}-entry deterministic testDNA/H19 scale-up"
    )
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
    workloads = [make_synthetic_workload(entry) for entry in parse_entries(args.synthetic_entries)]
    add_optional_workload(
        workloads,
        label=args.hg38_label,
        description="hg38 chr21 + H19 workload",
        dna=args.hg38_dna,
        rna=args.hg38_rna,
        require=args.require_hg38,
    )
    return workloads


def make_modes() -> List[ModeSpec]:
    core_env = {
        "FASIM_TRANSFERSTRING_TABLE": "1",
        "FASIM_GPU_DP_COLUMN_AUTO": "1",
        "FASIM_GPU_DP_COLUMN_AUTO_MIN_WINDOWS": "1",
        "FASIM_GPU_DP_COLUMN_AUTO_MIN_CELLS": "1",
        "FASIM_ALIGNER_ALIGN_INTERNALS": "1",
        "FASIM_SSW_PROFILE_CACHE": "1",
    }
    return [
        ModeSpec("core", "avx2", core_env),
        ModeSpec("core_avx2", "avx2", dict(core_env, FASIM_SSW_AVX2="1")),
        ModeSpec(
            "core_profile_context",
            "avx2",
            dict(core_env, FASIM_SSW_PROFILE_CONTEXT="1"),
        ),
        ModeSpec(
            "core_avx2_profile_context",
            "avx2",
            dict(core_env, FASIM_SSW_AVX2="1", FASIM_SSW_PROFILE_CONTEXT="1"),
        ),
    ]


def mode_metric(results: Dict[str, List[RunResult]], mode: str, key: str) -> float:
    return median_metric(results[mode], key)


def mode_count(results: Dict[str, List[RunResult]], mode: str, key: str) -> int:
    return median_count(results[mode], key)


def digest_matches_reference(results: Dict[str, List[RunResult]], mode: str) -> bool:
    return stable_digest(results[mode]) == stable_digest(results["core"])


def records_match_reference(results: Dict[str, List[RunResult]], mode: str) -> bool:
    return stable_records(results[mode]) == stable_records(results["core"])


def percent(numerator: float, denominator: float) -> str:
    if denominator <= 0.0:
        return "n/a"
    return f"{100.0 * numerator / denominator:.2f}%"


def delta_seconds(results: Dict[str, List[RunResult]], mode: str) -> float:
    return mode_metric(results, "core", "fasim_total_seconds") - mode_metric(
        results, mode, "fasim_total_seconds"
    )


def display_mode(mode: str) -> str:
    return {
        "core": "core",
        "core_avx2": "core + AVX2",
        "core_profile_context": "core + ProfileContext",
        "core_avx2_profile_context": "core + AVX2 + ProfileContext",
    }[mode]


def characterized_modes() -> List[str]:
    return [
        "core",
        "core_avx2",
        "core_profile_context",
        "core_avx2_profile_context",
    ]


def require_metrics(all_results: Dict[str, Dict[str, List[RunResult]]]) -> None:
    for workload_results in all_results.values():
        for mode in characterized_modes():
            for key in CORE_KEYS + AVX2_KEYS + SSW_DECOMPOSITION_KEYS + PROFILE_CONTEXT_KEYS:
                mode_metric(workload_results, mode, key)


def check_profile_context_clean(
    *,
    workload: str,
    results: Dict[str, List[RunResult]],
    mode: str,
) -> None:
    if mode_count(results, mode, "fasim_ssw_profile_context_requested") != 1:
        raise RuntimeError(f"{workload}/{mode}: ProfileContext not requested")
    if mode_count(results, mode, "fasim_ssw_profile_context_active") != 1:
        raise RuntimeError(f"{workload}/{mode}: ProfileContext not active")
    if mode_count(results, mode, "fasim_ssw_profile_context_fallbacks") != 0:
        raise RuntimeError(f"{workload}/{mode}: ProfileContext fell back")
    for key in [
        "fasim_ssw_profile_context_score_mismatches",
        "fasim_ssw_profile_context_endpoint_mismatches",
        "fasim_ssw_profile_context_cigar_mismatches",
        "fasim_ssw_profile_context_digest_mismatches",
    ]:
        if mode_count(results, mode, key) != 0:
            raise RuntimeError(f"{workload}/{mode}: {key} != 0")


def check_avx2_clean(
    *,
    workload: str,
    results: Dict[str, List[RunResult]],
    mode: str,
) -> None:
    if mode_count(results, mode, "fasim_ssw_avx2_requested") != 1:
        raise RuntimeError(f"{workload}/{mode}: AVX2 not requested")
    if mode_count(results, mode, "fasim_ssw_avx2_compiled") != 1:
        raise RuntimeError(f"{workload}/{mode}: AVX2 not compiled")
    if mode_count(results, mode, "fasim_ssw_avx2_mode") != 2:
        raise RuntimeError(f"{workload}/{mode}: AVX2 mode was not forward_only")
    if mode_count(results, mode, "fasim_ssw_avx2_active") != 1:
        raise RuntimeError(f"{workload}/{mode}: AVX2 not active")
    if mode_count(results, mode, "fasim_ssw_avx2_forward_calls") <= 0:
        raise RuntimeError(f"{workload}/{mode}: AVX2 saw no forward calls")
    if mode_count(results, mode, "fasim_ssw_avx2_reverse_calls") != 0:
        raise RuntimeError(f"{workload}/{mode}: AVX2 unexpectedly used reverse calls")
    if mode_count(results, mode, "fasim_ssw_avx2_fallback_calls") != 0:
        raise RuntimeError(f"{workload}/{mode}: AVX2 fell back")


def check_results(all_results: Dict[str, Dict[str, List[RunResult]]]) -> None:
    require_metrics(all_results)
    active_workloads = 0
    for workload, results in all_results.items():
        for mode in characterized_modes()[1:]:
            if not digest_matches_reference(results, mode):
                raise RuntimeError(f"{workload}/{mode}: digest does not match core")
            if not records_match_reference(results, mode):
                raise RuntimeError(f"{workload}/{mode}: record count does not match core")

        if mode_count(results, "core", "fasim_aligner_align_calls") <= 0:
            continue
        active_workloads += 1
        for mode in ["core", "core_profile_context"]:
            if mode_count(results, mode, "fasim_ssw_avx2_requested") != 0:
                raise RuntimeError(f"{workload}/{mode}: AVX2 unexpectedly requested")
            if mode_count(results, mode, "fasim_ssw_avx2_active") != 0:
                raise RuntimeError(f"{workload}/{mode}: AVX2 unexpectedly active")
        for mode in ["core_avx2", "core_avx2_profile_context"]:
            check_avx2_clean(workload=workload, results=results, mode=mode)
        for mode in ["core_profile_context", "core_avx2_profile_context"]:
            check_profile_context_clean(workload=workload, results=results, mode=mode)
    if active_workloads <= 0:
        raise RuntimeError("no workload exercised aligner.Align calls")


def hit_rate(results: Dict[str, List[RunResult]], mode: str) -> str:
    return percent(
        float(mode_count(results, mode, "fasim_ssw_profile_context_hits")),
        float(mode_count(results, mode, "fasim_ssw_profile_context_calls")),
    )


def digest_clean(results: Dict[str, List[RunResult]], mode: str) -> str:
    return "yes" if digest_matches_reference(results, mode) else "no"


def render_report(
    *,
    workloads: Iterable[WorkloadSpec],
    all_results: Dict[str, Dict[str, List[RunResult]]],
    repeat: int,
    output_path: Path,
) -> str:
    workload_list = list(workloads)
    modes = characterized_modes()
    lines: List[str] = []
    lines.append("# Fasim Final Speed Add-ons Characterization")
    lines.append("")
    lines.append(
        "This report compares the core large-workload opt-in stack with optional "
        "AVX2 and SSW ProfileContext add-ons. It does not add optimization logic "
        "or default any optional path."
    )
    lines.append("")
    lines.append("Core stack:")
    lines.append("")
    lines.append("```bash")
    lines.append("FASIM_TRANSFERSTRING_TABLE=1")
    lines.append("FASIM_GPU_DP_COLUMN_AUTO=1")
    lines.append("FASIM_SSW_PROFILE_CACHE=1")
    lines.append("```")
    lines.append("")
    lines.append(f"Each workload uses {repeat} run(s); tables report medians.")
    lines.append("")

    for workload in workload_list:
        results = all_results[workload.label]
        core_total = mode_metric(results, "core", "fasim_total_seconds")
        core_ssw = mode_metric(results, "core", "fasim_aligner_align_cpu_ssw_align_seconds")
        core_forward = mode_metric(results, "core", "fasim_ssw_forward_score_end_seconds")
        core_reverse = mode_metric(results, "core", "fasim_ssw_reverse_start_seconds")
        lines.append(f"## {workload.label}")
        lines.append("")
        lines.append(f"Records: `{fmt_int(stable_records(results['core']))}`")
        lines.append(f"Digest: `{stable_digest(results['core'])}`")
        lines.append("")
        append_table(
            lines,
            [
                "Mode",
                "Total s",
                "Delta vs core s",
                "Speedup vs core",
                "SSW align s",
                "SSW speedup",
                "Forward s",
                "Forward speedup",
                "Reverse s",
                "Reverse speedup",
                "CIGAR s",
                "Digest clean",
            ],
            [
                [
                    display_mode(mode),
                    fmt_seconds(mode_metric(results, mode, "fasim_total_seconds")),
                    fmt_seconds(delta_seconds(results, mode)),
                    fmt_speedup(speedup(core_total, mode_metric(results, mode, "fasim_total_seconds"))),
                    fmt_seconds(mode_metric(results, mode, "fasim_aligner_align_cpu_ssw_align_seconds")),
                    fmt_speedup(speedup(core_ssw, mode_metric(results, mode, "fasim_aligner_align_cpu_ssw_align_seconds"))),
                    fmt_seconds(mode_metric(results, mode, "fasim_ssw_forward_score_end_seconds")),
                    fmt_speedup(speedup(core_forward, mode_metric(results, mode, "fasim_ssw_forward_score_end_seconds"))),
                    fmt_seconds(mode_metric(results, mode, "fasim_ssw_reverse_start_seconds")),
                    fmt_speedup(speedup(core_reverse, mode_metric(results, mode, "fasim_ssw_reverse_start_seconds"))),
                    fmt_seconds(mode_metric(results, mode, "fasim_ssw_cigar_seconds")),
                    digest_clean(results, mode),
                ]
                for mode in modes
            ],
        )
        lines.append("")
        append_table(
            lines,
            [
                "Mode",
                "AVX2 mode",
                "AVX2 calls",
                "AVX2 forward",
                "AVX2 reverse",
                "AVX2 fallbacks",
                "ProfileContext active",
                "ProfileContext hits",
                "ProfileContext misses",
                "ProfileContext hit rate",
                "ProfileContext fallbacks",
            ],
            [
                [
                    display_mode(mode),
                    fmt_int(mode_count(results, mode, "fasim_ssw_avx2_mode")),
                    fmt_int(mode_count(results, mode, "fasim_ssw_avx2_calls")),
                    fmt_int(mode_count(results, mode, "fasim_ssw_avx2_forward_calls")),
                    fmt_int(mode_count(results, mode, "fasim_ssw_avx2_reverse_calls")),
                    fmt_int(mode_count(results, mode, "fasim_ssw_avx2_fallback_calls")),
                    fmt_int(mode_count(results, mode, "fasim_ssw_profile_context_active")),
                    fmt_int(mode_count(results, mode, "fasim_ssw_profile_context_hits")),
                    fmt_int(mode_count(results, mode, "fasim_ssw_profile_context_misses")),
                    hit_rate(results, mode),
                    fmt_int(mode_count(results, mode, "fasim_ssw_profile_context_fallbacks")),
                ]
                for mode in modes
            ],
        )
        lines.append("")

    clean = all(
        digest_matches_reference(all_results[workload.label], mode)
        and records_match_reference(all_results[workload.label], mode)
        for workload in workload_list
        for mode in modes[1:]
    )
    lines.append("## Decision")
    lines.append("")
    if not clean:
        lines.append("Stop: at least one optional add-on changed digest or record count.")
    elif "hg38_chr21_H19" in all_results:
        hg38 = all_results["hg38_chr21_H19"]
        core = mode_metric(hg38, "core", "fasim_total_seconds")
        avx2 = mode_metric(hg38, "core_avx2", "fasim_total_seconds")
        context = mode_metric(hg38, "core_profile_context", "fasim_total_seconds")
        both = mode_metric(hg38, "core_avx2_profile_context", "fasim_total_seconds")
        lines.append(
            "All optional add-on modes are digest-clean relative to core. "
            f"hg38 medians: core {fmt_seconds(core)}, core+AVX2 {fmt_seconds(avx2)}, "
            f"core+ProfileContext {fmt_seconds(context)}, core+AVX2+ProfileContext {fmt_seconds(both)}."
        )
    else:
        lines.append("All optional add-on modes are digest-clean relative to core.")
    lines.append("")
    lines.append("## Boundaries")
    lines.append("")
    lines.append("```text")
    lines.append("new optimization logic: no")
    lines.append("default AVX2: no")
    lines.append("default ProfileContext: no")
    lines.append("output semantic change: no")
    lines.append("scoring/threshold/non-overlap change: no")
    lines.append("GPU AUTO policy change: no")
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
    parser.add_argument("--synthetic-entries", default="1,32")
    parser.add_argument("--hg38-dna")
    parser.add_argument("--hg38-rna")
    parser.add_argument("--hg38-label", default="hg38_chr21_H19")
    parser.add_argument("--require-hg38", action="store_true")
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument(
        "--work-dir",
        default=str(ROOT / ".tmp" / "fasim_final_speed_addons"),
    )
    parser.add_argument(
        "--output",
        default=str(ROOT / "docs" / "fasim_final_speed_addons_characterization.md"),
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
        raise RuntimeError(f"missing Fasim binary: {cuda_bin}")

    workloads = make_workloads(args)
    modes = make_modes()
    work_dir = Path(args.work_dir)
    if not work_dir.is_absolute():
        work_dir = (ROOT / work_dir).resolve()

    all_results: Dict[str, Dict[str, List[RunResult]]] = {}
    for workload in workloads:
        workload_results: Dict[str, List[RunResult]] = {}
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
            workload_results[mode.label] = runs
        all_results[workload.label] = workload_results

    if args.check:
        check_results(all_results)
    else:
        require_metrics(all_results)

    report = render_report(
        workloads=workloads,
        all_results=all_results,
        repeat=args.repeat,
        output_path=Path(args.output).resolve(),
    )
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
