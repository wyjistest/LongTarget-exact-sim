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


AVX2_KEYS = [
    "fasim_ssw_avx2_requested",
    "fasim_ssw_avx2_compiled",
    "fasim_ssw_avx2_active",
    "fasim_ssw_avx2_mode",
    "fasim_ssw_avx2_calls",
    "fasim_ssw_avx2_forward_calls",
    "fasim_ssw_avx2_reverse_calls",
    "fasim_ssw_avx2_byte_calls",
    "fasim_ssw_avx2_word_calls",
    "fasim_ssw_avx2_fallback_calls",
]

SSW_DECOMPOSITION_KEYS = [
    "fasim_ssw_forward_score_end_seconds",
    "fasim_ssw_reverse_start_seconds",
    "fasim_ssw_cigar_seconds",
    "fasim_ssw_banded_sw_seconds",
    "fasim_ssw_endpoint_bookkeeping_seconds",
    "fasim_ssw_byte_path_seconds",
    "fasim_ssw_word_path_seconds",
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


def mode_metric(results: Dict[str, List[RunResult]], mode: str, key: str) -> float:
    return median_metric(results[mode], key)


def mode_count(results: Dict[str, List[RunResult]], mode: str, key: str) -> int:
    return median_count(results[mode], key)


def digest_matches_reference(results: Dict[str, List[RunResult]], mode: str) -> bool:
    return stable_digest(results[mode]) == stable_digest(results["sse2_auto_cache"])


def percent(numerator: float, denominator: float) -> str:
    if denominator <= 0.0:
        return "n/a"
    return f"{100.0 * numerator / denominator:.2f}%"


def make_modes() -> List[ModeSpec]:
    base_env = {
        "FASIM_TRANSFERSTRING_TABLE": "1",
        "FASIM_GPU_DP_COLUMN_AUTO": "1",
        "FASIM_GPU_DP_COLUMN_AUTO_MIN_WINDOWS": "1",
        "FASIM_GPU_DP_COLUMN_AUTO_MIN_CELLS": "1",
        "FASIM_ALIGNER_ALIGN_INTERNALS": "1",
        "FASIM_SSW_PROFILE_CACHE": "1",
    }
    return [
        ModeSpec("sse2_auto_cache", "sse2", base_env),
        ModeSpec("avx2_compiled_auto_cache", "avx2", base_env),
        ModeSpec("avx2_default_auto_cache", "avx2", dict(base_env, FASIM_SSW_AVX2="1")),
        ModeSpec(
            "avx2_all_auto_cache",
            "avx2",
            dict(base_env, FASIM_SSW_AVX2="1", FASIM_SSW_AVX2_MODE="all"),
        ),
        ModeSpec(
            "avx2_forward_only_auto_cache",
            "avx2",
            dict(base_env, FASIM_SSW_AVX2="1", FASIM_SSW_AVX2_MODE="forward_only"),
        ),
        ModeSpec(
            "avx2_reverse_only_auto_cache",
            "avx2",
            dict(base_env, FASIM_SSW_AVX2="1", FASIM_SSW_AVX2_MODE="reverse_only"),
        ),
        ModeSpec(
            "avx2_off_auto_cache",
            "avx2",
            dict(base_env, FASIM_SSW_AVX2="1", FASIM_SSW_AVX2_MODE="off"),
        ),
    ]


def bin_for_mode(mode: ModeSpec, *, sse2_bin: Path, avx2_bin: Path) -> Path:
    if mode.bin_kind == "sse2":
        return sse2_bin
    if mode.bin_kind == "avx2":
        return avx2_bin
    raise RuntimeError(f"unknown binary kind: {mode.bin_kind}")


def require_avx2_metrics(all_results: Dict[str, Dict[str, List[RunResult]]]) -> None:
    modes = characterized_modes()
    for workload_results in all_results.values():
        for mode in modes:
            for key in AVX2_KEYS:
                mode_metric(workload_results, mode, key)
            for key in SSW_DECOMPOSITION_KEYS:
                mode_metric(workload_results, mode, key)


def check_requested_mode(
    *,
    workload: str,
    results: Dict[str, List[RunResult]],
    mode: str,
    expect_active: bool,
) -> None:
    if mode_count(results, mode, "fasim_ssw_avx2_requested") != 1:
        raise RuntimeError(f"{workload}/{mode}: AVX2 not requested")
    if mode_count(results, mode, "fasim_ssw_avx2_compiled") != 1:
        raise RuntimeError(f"{workload}/{mode}: AVX2 not compiled")
    if mode_count(results, mode, "fasim_ssw_avx2_fallback_calls") != 0:
        raise RuntimeError(f"{workload}/{mode}: AVX2 fell back")

    active = mode_count(results, mode, "fasim_ssw_avx2_active")
    calls = mode_count(results, mode, "fasim_ssw_avx2_calls")
    if expect_active:
        if active != 1:
            raise RuntimeError(f"{workload}/{mode}: AVX2 not active")
        if calls <= 0:
            raise RuntimeError(f"{workload}/{mode}: AVX2 saw no calls")
    else:
        if active != 0:
            raise RuntimeError(f"{workload}/{mode}: AVX2 unexpectedly active")
        if calls != 0:
            raise RuntimeError(f"{workload}/{mode}: AVX2 unexpectedly saw calls")
    if mode == "avx2_default_auto_cache" and mode_count(results, mode, "fasim_ssw_avx2_mode") != 2:
        raise RuntimeError(f"{workload}/{mode}: AVX2 default mode was not forward_only")
    if mode == "avx2_all_auto_cache" and mode_count(results, mode, "fasim_ssw_avx2_mode") != 1:
        raise RuntimeError(f"{workload}/{mode}: AVX2 mode was not all")
    if mode == "avx2_forward_only_auto_cache" and mode_count(results, mode, "fasim_ssw_avx2_mode") != 2:
        raise RuntimeError(f"{workload}/{mode}: AVX2 mode was not forward_only")
    if mode == "avx2_reverse_only_auto_cache" and mode_count(results, mode, "fasim_ssw_avx2_mode") != 3:
        raise RuntimeError(f"{workload}/{mode}: AVX2 mode was not reverse_only")
    if mode == "avx2_off_auto_cache" and mode_count(results, mode, "fasim_ssw_avx2_mode") != 4:
        raise RuntimeError(f"{workload}/{mode}: AVX2 mode was not off")


def check_results(all_results: Dict[str, Dict[str, List[RunResult]]]) -> None:
    require_avx2_metrics(all_results)
    active_workloads = 0
    for workload, results in all_results.items():
        for mode in characterized_modes()[1:]:
            if not digest_matches_reference(results, mode):
                raise RuntimeError(f"{workload}/{mode}: digest does not match sse2_auto_cache")
            if stable_records(results[mode]) != stable_records(results["sse2_auto_cache"]):
                raise RuntimeError(f"{workload}/{mode}: record count does not match sse2_auto_cache")

        if mode_count(results, "sse2_auto_cache", "fasim_ssw_avx2_compiled") != 0:
            raise RuntimeError(f"{workload}/sse2_auto_cache: AVX2 unexpectedly compiled")
        if mode_count(results, "sse2_auto_cache", "fasim_ssw_avx2_mode") != 0:
            raise RuntimeError(f"{workload}/sse2_auto_cache: AVX2 mode unexpectedly active")
        if mode_count(results, "avx2_compiled_auto_cache", "fasim_ssw_avx2_compiled") != 1:
            raise RuntimeError(f"{workload}/avx2_compiled_auto_cache: AVX2 not compiled")
        if mode_count(results, "avx2_compiled_auto_cache", "fasim_ssw_avx2_requested") != 0:
            raise RuntimeError(f"{workload}/avx2_compiled_auto_cache: AVX2 unexpectedly requested")
        if mode_count(results, "avx2_compiled_auto_cache", "fasim_ssw_avx2_active") != 0:
            raise RuntimeError(f"{workload}/avx2_compiled_auto_cache: AVX2 unexpectedly active")
        if mode_count(results, "avx2_compiled_auto_cache", "fasim_ssw_avx2_mode") != 0:
            raise RuntimeError(f"{workload}/avx2_compiled_auto_cache: AVX2 mode unexpectedly active")

        if mode_count(results, "avx2_all_auto_cache", "fasim_aligner_align_cpu_calls") <= 0:
            continue
        active_workloads += 1
        check_requested_mode(
            workload=workload,
            results=results,
            mode="avx2_default_auto_cache",
            expect_active=True,
        )
        check_requested_mode(
            workload=workload,
            results=results,
            mode="avx2_all_auto_cache",
            expect_active=True,
        )
        check_requested_mode(
            workload=workload,
            results=results,
            mode="avx2_forward_only_auto_cache",
            expect_active=True,
        )
        check_requested_mode(
            workload=workload,
            results=results,
            mode="avx2_reverse_only_auto_cache",
            expect_active=True,
        )
        check_requested_mode(
            workload=workload,
            results=results,
            mode="avx2_off_auto_cache",
            expect_active=False,
        )
    if active_workloads <= 0:
        raise RuntimeError("no characterized workload exercised AVX2 SSW calls")


def display_mode(mode: str) -> str:
    return {
        "sse2_auto_cache": "SSE2 baseline",
        "avx2_compiled_auto_cache": "AVX2 compiled/off",
        "avx2_default_auto_cache": "AVX2 default forward_only",
        "avx2_all_auto_cache": "AVX2 explicit all",
        "avx2_forward_only_auto_cache": "AVX2 forward_only",
        "avx2_reverse_only_auto_cache": "AVX2 reverse_only",
        "avx2_off_auto_cache": "AVX2 mode=off",
    }[mode]


def characterized_modes() -> List[str]:
    return [
        "sse2_auto_cache",
        "avx2_compiled_auto_cache",
        "avx2_default_auto_cache",
        "avx2_all_auto_cache",
        "avx2_forward_only_auto_cache",
        "avx2_reverse_only_auto_cache",
        "avx2_off_auto_cache",
    ]


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
    lines.append("# Fasim SSW AVX2 Hybrid Modes")
    lines.append("")
    lines.append(
        "This report compares default SSE2, full AVX2, and hybrid AVX2 SSW "
        "modes. When `FASIM_SSW_AVX2=1` is requested without an explicit mode, "
        "the default AVX2 submode is `forward_only`: AVX2 is used for the forward "
        "score/end pass while reverse-start and CIGAR stay on the legacy SSE2 path."
    )
    lines.append("")
    lines.append(f"Each workload uses {repeat} run(s); tables report medians.")
    lines.append("")

    for workload in workload_list:
        results = all_results[workload.label]
        baseline_total = mode_metric(results, "sse2_auto_cache", "fasim_total_seconds")
        baseline_ssw = mode_metric(results, "sse2_auto_cache", "fasim_aligner_align_cpu_ssw_align_seconds")
        baseline_forward = mode_metric(results, "sse2_auto_cache", "fasim_ssw_forward_score_end_seconds")
        baseline_reverse = mode_metric(results, "sse2_auto_cache", "fasim_ssw_reverse_start_seconds")
        baseline_byte = mode_metric(results, "sse2_auto_cache", "fasim_ssw_byte_path_seconds")
        lines.append(f"## {workload.label}")
        lines.append("")
        lines.append(f"Records: `{fmt_int(stable_records(results['sse2_auto_cache']))}`")
        lines.append("")
        append_table(
            lines,
            [
                "Mode",
                "Total s",
                "Total vs SSE2",
                "SSW align s",
                "SSW vs SSE2",
                "Forward s",
                "Forward vs SSE2",
                "Reverse s",
                "Reverse vs SSE2",
                "CIGAR s",
                "Digest clean",
            ],
            [
                [
                    display_mode(mode),
                    fmt_seconds(mode_metric(results, mode, "fasim_total_seconds")),
                    fmt_speedup(speedup(baseline_total, mode_metric(results, mode, "fasim_total_seconds"))),
                    fmt_seconds(mode_metric(results, mode, "fasim_aligner_align_cpu_ssw_align_seconds")),
                    fmt_speedup(speedup(baseline_ssw, mode_metric(results, mode, "fasim_aligner_align_cpu_ssw_align_seconds"))),
                    fmt_seconds(mode_metric(results, mode, "fasim_ssw_forward_score_end_seconds")),
                    fmt_speedup(speedup(baseline_forward, mode_metric(results, mode, "fasim_ssw_forward_score_end_seconds"))),
                    fmt_seconds(mode_metric(results, mode, "fasim_ssw_reverse_start_seconds")),
                    fmt_speedup(speedup(baseline_reverse, mode_metric(results, mode, "fasim_ssw_reverse_start_seconds"))),
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
                "AVX2 requested",
                "AVX2 compiled",
                "AVX2 mode",
                "AVX2 active",
                "AVX2 calls",
                "Forward calls",
                "Reverse calls",
                "Byte calls",
                "Word calls",
                "Fallbacks",
                "Byte path s",
                "Byte vs SSE2",
                "Banded_sw s",
            ],
            [
                [
                    display_mode(mode),
                    fmt_int(mode_count(results, mode, "fasim_ssw_avx2_requested")),
                    fmt_int(mode_count(results, mode, "fasim_ssw_avx2_compiled")),
                    fmt_int(mode_count(results, mode, "fasim_ssw_avx2_mode")),
                    fmt_int(mode_count(results, mode, "fasim_ssw_avx2_active")),
                    fmt_int(mode_count(results, mode, "fasim_ssw_avx2_calls")),
                    fmt_int(mode_count(results, mode, "fasim_ssw_avx2_forward_calls")),
                    fmt_int(mode_count(results, mode, "fasim_ssw_avx2_reverse_calls")),
                    fmt_int(mode_count(results, mode, "fasim_ssw_avx2_byte_calls")),
                    fmt_int(mode_count(results, mode, "fasim_ssw_avx2_word_calls")),
                    fmt_int(mode_count(results, mode, "fasim_ssw_avx2_fallback_calls")),
                    fmt_seconds(mode_metric(results, mode, "fasim_ssw_byte_path_seconds")),
                    fmt_speedup(speedup(baseline_byte, mode_metric(results, mode, "fasim_ssw_byte_path_seconds"))),
                    fmt_seconds(mode_metric(results, mode, "fasim_ssw_banded_sw_seconds")),
                ]
                for mode in modes
            ],
        )
        lines.append("")

    clean = all(
        digest_matches_reference(all_results[workload.label], mode)
        and mode_count(all_results[workload.label], mode, "fasim_ssw_avx2_fallback_calls") == 0
        for workload in workload_list
        for mode in modes
    )
    lines.append("## Decision")
    lines.append("")
    if not clean:
        lines.append("Stop: a hybrid mode changed output digest or fell back.")
    else:
        if "hg38_chr21_H19" in all_results:
            hg38 = all_results["hg38_chr21_H19"]
            sse2_total = mode_metric(hg38, "sse2_auto_cache", "fasim_total_seconds")
            default_total = mode_metric(hg38, "avx2_default_auto_cache", "fasim_total_seconds")
            all_total = mode_metric(hg38, "avx2_all_auto_cache", "fasim_total_seconds")
            forward_total = mode_metric(hg38, "avx2_forward_only_auto_cache", "fasim_total_seconds")
            reverse_total = mode_metric(hg38, "avx2_reverse_only_auto_cache", "fasim_total_seconds")
            lines.append(
                "All characterized AVX2 modes are digest-clean with zero fallbacks. "
                "`FASIM_SSW_AVX2=1` now defaults to `forward_only`; explicit "
                f"`forward_only` is {fmt_seconds(forward_total)} and the unset default is "
                f"{fmt_seconds(default_total)} on hg38, versus {fmt_seconds(all_total)} "
                f"for explicit full AVX2 and {fmt_seconds(sse2_total)} for SSE2. "
                f"`reverse_only` regresses to {fmt_seconds(reverse_total)}, so reverse-start remains SSE2-preferred."
            )
        else:
            lines.append(
                "All characterized AVX2 modes are digest-clean with zero fallbacks. "
                "Use the hg38 medians to decide whether `forward_only` should become the preferred optional AVX2 mode."
            )
    lines.append("")
    lines.append("## Boundaries")
    lines.append("")
    lines.append("```text")
    lines.append("default enabled: no")
    lines.append("FASIM_SSW_AVX2=1 default submode: forward_only")
    lines.append("output semantic change: no")
    lines.append("scoring/threshold/non-overlap change: no")
    lines.append("GPU AUTO policy change: no")
    lines.append("SSW profile cache default change: no")
    lines.append("AVX512 added: no")
    lines.append("validation relaxation: no")
    lines.append("```")

    report = "\n".join(lines)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report + "\n", encoding="utf-8")
    return report

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sse2-bin", required=True)
    parser.add_argument("--avx2-bin", required=True)
    parser.add_argument("--synthetic-entries", default="1,32")
    parser.add_argument("--hg38-dna")
    parser.add_argument("--hg38-rna")
    parser.add_argument("--hg38-label", default="hg38_chr21_H19")
    parser.add_argument("--require-hg38", action="store_true")
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument(
        "--work-dir",
        default=str(ROOT / ".tmp" / "fasim_ssw_avx2_hybrid_modes"),
    )
    parser.add_argument(
        "--output",
        default=str(ROOT / "docs" / "fasim_ssw_avx2_hybrid_modes.md"),
    )
    parser.add_argument("--require-profile", action="store_true")
    parser.add_argument("--check", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.repeat <= 0:
        raise RuntimeError("--repeat must be positive")

    sse2_bin = Path(args.sse2_bin)
    avx2_bin = Path(args.avx2_bin)
    if not sse2_bin.is_absolute():
        sse2_bin = (ROOT / sse2_bin).resolve()
    if not avx2_bin.is_absolute():
        avx2_bin = (ROOT / avx2_bin).resolve()
    if not sse2_bin.exists():
        raise RuntimeError(f"missing SSE2 Fasim binary: {sse2_bin}")
    if not avx2_bin.exists():
        raise RuntimeError(f"missing AVX2 Fasim binary: {avx2_bin}")

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
                        bin_path=bin_for_mode(mode, sse2_bin=sse2_bin, avx2_bin=avx2_bin),
                        work_dir=work_dir / workload.label / mode.label / f"run_{index + 1}",
                        require_profile=args.require_profile,
                    )
                )
            workload_results[mode.label] = runs
        all_results[workload.label] = workload_results

    if args.check:
        check_results(all_results)
    else:
        require_avx2_metrics(all_results)

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
