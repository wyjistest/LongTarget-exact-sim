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


INTERNAL_KEYS = [
    "fasim_aligner_align_cpu_internals_enabled",
    "fasim_aligner_align_cpu_strlen_seconds",
    "fasim_aligner_align_cpu_query_alloc_seconds",
    "fasim_aligner_align_cpu_query_translate_seconds",
    "fasim_aligner_align_cpu_ref_alloc_seconds",
    "fasim_aligner_align_cpu_ref_translate_seconds",
    "fasim_aligner_align_cpu_profile_build_seconds",
    "fasim_aligner_align_cpu_ssw_align_seconds",
    "fasim_aligner_align_cpu_convert_seconds",
    "fasim_aligner_align_cpu_destroy_seconds",
    "fasim_aligner_align_cpu_calls",
    "fasim_aligner_align_cpu_null_results",
]

PROFILE_REUSE_KEYS = [
    "fasim_ssw_profile_reuse_shadow_enabled",
    "fasim_ssw_profile_build_calls",
    "fasim_ssw_profile_unique_keys",
    "fasim_ssw_profile_reused_possible_calls",
    "fasim_ssw_profile_build_seconds",
    "fasim_ssw_profile_est_reuse_saved_seconds",
    "fasim_ssw_profile_key_query_length",
    "fasim_ssw_profile_key_scoring_hash",
    "fasim_ssw_profile_key_orientation",
    "fasim_ssw_profile_shadow_compared",
    "fasim_ssw_profile_shadow_score_mismatches",
    "fasim_ssw_profile_shadow_endpoint_mismatches",
    "fasim_ssw_profile_shadow_cigar_mismatches",
    "fasim_ssw_profile_shadow_output_digest_mismatches",
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
    return f"{100.0 * numerator / denominator:.2f}%"


def require_internal_metrics(results: Dict[str, List[RunResult]]) -> None:
    for key in INTERNAL_KEYS:
        mode_metric(results, "auto_cpu_internals", key)
    if "auto_profile_reuse_shadow" in results:
        for key in INTERNAL_KEYS + PROFILE_REUSE_KEYS:
            mode_metric(results, "auto_profile_reuse_shadow", key)


def render_report(
    *,
    workload: WorkloadSpec,
    results: Dict[str, List[RunResult]],
    repeat: int,
    output_path: Path,
) -> str:
    lines: List[str] = []
    lines.append("# Fasim aligner.Align CPU Internals")
    lines.append("")
    lines.append(
        "This telemetry-only report decomposes the CPU `aligner.Align` wrapper "
        "used by `fastSIM_extend_from_scoreinfo`. It is enabled only by "
        "`FASIM_ALIGNER_ALIGN_INTERNALS=1`; it does not change output, scoring, "
        "thresholds, non-overlap, GPU kernels, AUTO policy, SIM-close, recovery, "
        "or validation behavior."
    )
    lines.append("")
    lines.append(f"Workload: `{workload.label}`. Each mode uses {repeat} run(s); tables report medians.")
    lines.append("")

    table_total = mode_metric(results, "table_only", "fasim_total_seconds")
    auto_total = mode_metric(results, "auto_cpu_internals", "fasim_total_seconds")
    lines.append("## Baseline")
    lines.append("")
    append_table(
        lines,
        [
            "Observed windows",
            "Observed cells",
            "Table seconds",
            "AUTO+internals seconds",
            "AUTO speedup",
            "Digest",
            "Records",
            "Digest match",
        ],
        [
            [
                fmt_int(mode_count(results, "auto_cpu_internals", "fasim_gpu_dp_column_auto_observed_windows")),
                fmt_int(mode_count(results, "auto_cpu_internals", "fasim_gpu_dp_column_auto_observed_cells")),
                fmt_seconds(table_total),
                fmt_seconds(auto_total),
                fmt_speedup(speedup(table_total, auto_total)),
                "`" + stable_digest(results["table_only"]) + "`",
                str(stable_records(results["table_only"])),
                "yes" if digest_matches_reference(results, "auto_cpu_internals") else "no",
            ]
        ],
    )
    lines.append("")

    align_seconds = mode_metric(results, "auto_cpu_internals", "fasim_aligner_align_seconds")
    align_calls = mode_count(results, "auto_cpu_internals", "fasim_aligner_align_calls")
    cpu_calls = mode_count(results, "auto_cpu_internals", "fasim_aligner_align_cpu_calls")
    lines.append("## Wrapper Internals")
    lines.append("")
    components = [
        ("strlen(query)", "fasim_aligner_align_cpu_strlen_seconds", "query length discovery"),
        ("query allocation", "fasim_aligner_align_cpu_query_alloc_seconds", "per-call translated query buffer"),
        ("query translate", "fasim_aligner_align_cpu_query_translate_seconds", "ASCII to SSW alphabet"),
        ("ref allocation", "fasim_aligner_align_cpu_ref_alloc_seconds", "per-call translated target buffer"),
        ("ref translate", "fasim_aligner_align_cpu_ref_translate_seconds", "short target translation"),
        ("profile build", "fasim_aligner_align_cpu_profile_build_seconds", "ssw_init query profile"),
        ("ssw_align", "fasim_aligner_align_cpu_ssw_align_seconds", "SSW DP plus begin/CIGAR work"),
        ("convert alignment", "fasim_aligner_align_cpu_convert_seconds", "s_align to C++ Alignment"),
        ("destroy/free", "fasim_aligner_align_cpu_destroy_seconds", "per-call cleanup"),
    ]
    append_table(
        lines,
        ["Component", "Seconds", "Percent of Align", "Notes"],
        [
            [
                name,
                fmt_seconds(mode_metric(results, "auto_cpu_internals", key)),
                percent(mode_metric(results, "auto_cpu_internals", key), align_seconds),
                notes,
            ]
            for name, key, notes in components
        ],
    )
    lines.append("")

    summed = sum(mode_metric(results, "auto_cpu_internals", key) for _, key, _ in components)
    residual = align_seconds - summed
    lines.append("## Call Shape")
    lines.append("")
    append_table(
        lines,
        [
            "Align calls",
            "CPU internals calls",
            "Total cells",
            "Avg query len",
            "Avg target len",
            "Max target len",
            "Null results",
            "Measured internals",
            "Residual vs outer Align",
        ],
        [
            [
                fmt_int(align_calls),
                fmt_int(cpu_calls),
                fmt_int(mode_count(results, "auto_cpu_internals", "fasim_aligner_align_total_cells")),
                f"{mode_metric(results, 'auto_cpu_internals', 'fasim_aligner_align_avg_query_len'):.2f}",
                f"{mode_metric(results, 'auto_cpu_internals', 'fasim_aligner_align_avg_target_len'):.2f}",
                fmt_int(mode_count(results, "auto_cpu_internals", "fasim_aligner_align_max_target_len")),
                fmt_int(mode_count(results, "auto_cpu_internals", "fasim_aligner_align_cpu_null_results")),
                fmt_seconds(summed),
                fmt_seconds(residual),
            ]
        ],
    )
    lines.append("")

    ssw_seconds = mode_metric(results, "auto_cpu_internals", "fasim_aligner_align_cpu_ssw_align_seconds")
    profile_seconds = mode_metric(results, "auto_cpu_internals", "fasim_aligner_align_cpu_profile_build_seconds")
    ref_translate_seconds = mode_metric(results, "auto_cpu_internals", "fasim_aligner_align_cpu_ref_translate_seconds")
    destroy_seconds = mode_metric(results, "auto_cpu_internals", "fasim_aligner_align_cpu_destroy_seconds")
    if "auto_profile_reuse_shadow" in results:
        lines.append("## SSW Profile Reuse Shadow")
        lines.append("")
        shadow_calls = mode_count(results, "auto_profile_reuse_shadow", "fasim_ssw_profile_build_calls")
        shadow_reusable = mode_count(results, "auto_profile_reuse_shadow", "fasim_ssw_profile_reused_possible_calls")
        shadow_unique = mode_count(results, "auto_profile_reuse_shadow", "fasim_ssw_profile_unique_keys")
        append_table(
            lines,
            [
                "Build calls",
                "Unique keys",
                "Reusable calls",
                "Reuse opportunity",
                "Build seconds",
                "Est saved seconds",
                "Compared",
                "Score mismatches",
                "Endpoint mismatches",
                "CIGAR mismatches",
                "Digest mismatches",
            ],
            [
                [
                    fmt_int(shadow_calls),
                    fmt_int(shadow_unique),
                    fmt_int(shadow_reusable),
                    percent(float(shadow_reusable), float(shadow_calls)),
                    fmt_seconds(mode_metric(results, "auto_profile_reuse_shadow", "fasim_ssw_profile_build_seconds")),
                    fmt_seconds(mode_metric(results, "auto_profile_reuse_shadow", "fasim_ssw_profile_est_reuse_saved_seconds")),
                    fmt_int(mode_count(results, "auto_profile_reuse_shadow", "fasim_ssw_profile_shadow_compared")),
                    fmt_int(mode_count(results, "auto_profile_reuse_shadow", "fasim_ssw_profile_shadow_score_mismatches")),
                    fmt_int(mode_count(results, "auto_profile_reuse_shadow", "fasim_ssw_profile_shadow_endpoint_mismatches")),
                    fmt_int(mode_count(results, "auto_profile_reuse_shadow", "fasim_ssw_profile_shadow_cigar_mismatches")),
                    fmt_int(mode_count(results, "auto_profile_reuse_shadow", "fasim_ssw_profile_shadow_output_digest_mismatches")),
                ]
            ],
        )
        lines.append("")
        append_table(
            lines,
            ["Last query length", "Scoring hash", "Orientation key", "Digest match"],
            [
                [
                    fmt_int(mode_count(results, "auto_profile_reuse_shadow", "fasim_ssw_profile_key_query_length")),
                    fmt_int(mode_count(results, "auto_profile_reuse_shadow", "fasim_ssw_profile_key_scoring_hash")),
                    fmt_int(mode_count(results, "auto_profile_reuse_shadow", "fasim_ssw_profile_key_orientation")),
                    "yes" if digest_matches_reference(results, "auto_profile_reuse_shadow") else "no",
                ]
            ],
        )
        lines.append("")

    lines.append("## Decision")
    lines.append("")
    if ssw_seconds >= align_seconds * 0.60:
        lines.append(
            "`ssw_align` dominates the CPU wrapper. Setup/allocation reuse alone is unlikely to recover most of "
            "the remaining `aligner.Align` cost; a CPU SIMD/batched short-align path would be the next real "
            "optimization candidate."
        )
    elif profile_seconds >= align_seconds * 0.20:
        lines.append(
            "Query profile build is a material cost. The next PR should evaluate query-profile reuse or a batched "
            "CPU wrapper before changing alignment semantics."
        )
    elif ref_translate_seconds + destroy_seconds >= align_seconds * 0.20:
        lines.append(
            "Per-call buffer translation/cleanup is material. The next PR should evaluate buffer reuse and target "
            "translation staging."
        )
    else:
        lines.append(
            "Costs are distributed across wrapper stages. Avoid a narrow optimization until a lower-level profile "
            "identifies a single dominant stage."
        )
    lines.append("")
    lines.append("## Boundaries")
    lines.append("")
    lines.append("```text")
    lines.append("optimize aligner.Align: no")
    lines.append("bypass Align in real output: no")
    lines.append("CIGAR/alignment output semantic change: no")
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
    parser.add_argument("--force-auto", action="store_true")
    parser.add_argument(
        "--work-dir",
        default=str(ROOT / ".tmp" / "fasim_aligner_align_cpu_internals"),
    )
    parser.add_argument(
        "--output",
        default=str(ROOT / "docs" / "fasim_aligner_align_cpu_internals.md"),
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
    auto_env = {
        "FASIM_TRANSFERSTRING_TABLE": "1",
        "FASIM_GPU_DP_COLUMN_AUTO": "1",
        "FASIM_ALIGNER_ALIGN_INTERNALS": "1",
    }
    shadow_env = dict(auto_env)
    shadow_env["FASIM_SSW_PROFILE_REUSE_SHADOW"] = "1"
    if args.force_auto:
        auto_env["FASIM_GPU_DP_COLUMN_AUTO_MIN_WINDOWS"] = "1"
        auto_env["FASIM_GPU_DP_COLUMN_AUTO_MIN_CELLS"] = "1"
        shadow_env["FASIM_GPU_DP_COLUMN_AUTO_MIN_WINDOWS"] = "1"
        shadow_env["FASIM_GPU_DP_COLUMN_AUTO_MIN_CELLS"] = "1"

    modes = [
        ModeSpec("table_only", "cuda", {"FASIM_TRANSFERSTRING_TABLE": "1"}),
        ModeSpec(
            "auto_cpu_internals",
            "cuda",
            auto_env,
        ),
        ModeSpec(
            "auto_profile_reuse_shadow",
            "cuda",
            shadow_env,
        ),
    ]
    results: Dict[str, List[RunResult]] = {}
    work_dir = Path(args.work_dir)
    if not work_dir.is_absolute():
        work_dir = (ROOT / work_dir).resolve()
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

    require_internal_metrics(results)
    report = render_report(
        workload=workload,
        results=results,
        repeat=args.repeat,
        output_path=Path(args.output).resolve(),
    )

    if args.check:
        if not digest_matches_reference(results, "auto_cpu_internals"):
            raise RuntimeError("auto_cpu_internals digest does not match table_only")
        if not digest_matches_reference(results, "auto_profile_reuse_shadow"):
            raise RuntimeError("auto_profile_reuse_shadow digest does not match table_only")
        if mode_count(results, "auto_cpu_internals", "fasim_gpu_dp_column_auto_active") != 1:
            raise RuntimeError("AUTO did not activate GPU DP+column")
        if mode_count(results, "auto_profile_reuse_shadow", "fasim_gpu_dp_column_auto_active") != 1:
            raise RuntimeError("AUTO did not activate GPU DP+column in profile reuse shadow")
        if mode_count(results, "auto_cpu_internals", "fasim_aligner_align_cpu_internals_enabled") != 1:
            raise RuntimeError("CPU aligner internals telemetry was not enabled")
        if mode_count(results, "auto_profile_reuse_shadow", "fasim_ssw_profile_reuse_shadow_enabled") != 1:
            raise RuntimeError("SSW profile reuse shadow telemetry was not enabled")
        if mode_count(results, "auto_cpu_internals", "fasim_aligner_align_cpu_calls") != mode_count(
            results, "auto_cpu_internals", "fasim_aligner_align_calls"
        ):
            raise RuntimeError("CPU internals call count does not match aligner.Align calls")
        if mode_count(results, "auto_profile_reuse_shadow", "fasim_ssw_profile_shadow_score_mismatches") != 0:
            raise RuntimeError("SSW profile reuse shadow score mismatched")
        if mode_count(results, "auto_profile_reuse_shadow", "fasim_ssw_profile_shadow_endpoint_mismatches") != 0:
            raise RuntimeError("SSW profile reuse shadow endpoint mismatched")
        if mode_count(results, "auto_profile_reuse_shadow", "fasim_ssw_profile_shadow_cigar_mismatches") != 0:
            raise RuntimeError("SSW profile reuse shadow CIGAR mismatched")
        if mode_count(results, "auto_profile_reuse_shadow", "fasim_ssw_profile_shadow_output_digest_mismatches") != 0:
            raise RuntimeError("SSW profile reuse shadow output digest mismatched")

    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
