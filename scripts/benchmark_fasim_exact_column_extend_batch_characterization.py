#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Dict, Iterable, List


ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from benchmark_fasim_exact_column_extend_batch import BATCH_KEYS  # noqa: E402
from benchmark_fasim_exact_column_extend_batch_shadow import FINAL_STACK_ENV  # noqa: E402
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


REPORT_KEYS = [
    "fasim_total_seconds",
    "fasim_gpu_dp_column_auto_active",
    "fasim_gpu_dp_column_active",
    "fasim_gpu_dp_column_exact_column_extend_seconds",
    "fasim_gpu_dp_column_fallbacks",
] + BATCH_KEYS


def make_modes(force_auto: bool) -> List[ModeSpec]:
    final_env = dict(FINAL_STACK_ENV)
    if force_auto:
        final_env["FASIM_GPU_DP_COLUMN_AUTO_MIN_WINDOWS"] = "1"
        final_env["FASIM_GPU_DP_COLUMN_AUTO_MIN_CELLS"] = "1"
    return [
        ModeSpec("table_only", "avx2", {"FASIM_TRANSFERSTRING_TABLE": "1"}),
        ModeSpec("final_stack", "avx2", final_env),
        ModeSpec(
            "final_stack_batch",
            "avx2",
            dict(final_env, FASIM_EXACT_COLUMN_EXTEND_BATCH="1"),
        ),
        ModeSpec(
            "final_stack_batch_validate",
            "avx2",
            dict(
                final_env,
                FASIM_EXACT_COLUMN_EXTEND_BATCH="1",
                FASIM_EXACT_COLUMN_EXTEND_BATCH_VALIDATE="1",
            ),
        ),
    ]


def characterized_modes() -> List[str]:
    return [
        "table_only",
        "final_stack",
        "final_stack_batch",
        "final_stack_batch_validate",
    ]


def mode_metric(results: Dict[str, List[RunResult]], mode: str, key: str) -> float:
    return median_metric(results[mode], key)


def mode_count(results: Dict[str, List[RunResult]], mode: str, key: str) -> int:
    return median_count(results[mode], key)


def require_metrics(results: Dict[str, List[RunResult]]) -> None:
    for runs in results.values():
        for key in REPORT_KEYS:
            median_metric(runs, key)


def require_zero(results: Dict[str, List[RunResult]], mode: str, keys: Iterable[str]) -> None:
    for key in keys:
        if mode_count(results, mode, key) != 0:
            raise RuntimeError(f"{mode}: expected {key}=0")


def digest_matches_reference(results: Dict[str, List[RunResult]], mode: str) -> bool:
    return stable_digest(results[mode]) == stable_digest(results["table_only"])


def records_match_reference(results: Dict[str, List[RunResult]], mode: str) -> bool:
    return stable_records(results[mode]) == stable_records(results["table_only"])


def check_characterization(results: Dict[str, List[RunResult]]) -> None:
    require_metrics(results)
    for mode in characterized_modes()[1:]:
        if not digest_matches_reference(results, mode):
            raise RuntimeError(f"{mode}: digest mismatch vs table_only")
        if not records_match_reference(results, mode):
            raise RuntimeError(f"{mode}: record count mismatch vs table_only")

    for mode in ["table_only", "final_stack"]:
        if mode_count(results, mode, "fasim_exact_column_batch_requested") != 0:
            raise RuntimeError(f"{mode}: batch unexpectedly requested")
        if mode_count(results, mode, "fasim_exact_column_batch_active") != 0:
            raise RuntimeError(f"{mode}: batch unexpectedly active")

    for mode in ["final_stack_batch", "final_stack_batch_validate"]:
        if mode_count(results, mode, "fasim_exact_column_batch_requested") != 1:
            raise RuntimeError(f"{mode}: batch was not requested")
        if mode_count(results, mode, "fasim_exact_column_batch_active") != 1:
            raise RuntimeError(f"{mode}: batch was not active")
        if mode_count(results, mode, "fasim_exact_column_batch_supported") != 1:
            raise RuntimeError(f"{mode}: batch did not report supported=1")
        if mode_count(results, mode, "fasim_exact_column_batch_requests") <= 0:
            raise RuntimeError(f"{mode}: no batch requests")
        if mode_count(results, mode, "fasim_exact_column_batch_cells") <= 0:
            raise RuntimeError(f"{mode}: no batch cells")
        require_zero(
            results,
            mode,
            [
                "fasim_exact_column_batch_score_mismatches",
                "fasim_exact_column_batch_endpoint_mismatches",
                "fasim_exact_column_batch_scoreinfo_mismatches",
                "fasim_exact_column_batch_digest_mismatches",
                "fasim_exact_column_batch_fallbacks",
                "fasim_gpu_dp_column_fallbacks",
            ],
        )

    for mode in ["final_stack", "final_stack_batch", "final_stack_batch_validate"]:
        if mode_count(results, mode, "fasim_gpu_dp_column_auto_active") != 1:
            raise RuntimeError(f"{mode}: GPU DP column AUTO was not active")
        if mode_count(results, mode, "fasim_gpu_dp_column_active") != 1:
            raise RuntimeError(f"{mode}: GPU DP column path was not active")

    if mode_count(results, "final_stack_batch", "fasim_exact_column_batch_validate_enabled") != 0:
        raise RuntimeError("validate unexpectedly enabled in batch mode")
    if mode_count(results, "final_stack_batch_validate", "fasim_exact_column_batch_validate_enabled") != 1:
        raise RuntimeError("validate was not enabled")
    if mode_metric(results, "final_stack_batch_validate", "fasim_exact_column_batch_validate_seconds") <= 0.0:
        raise RuntimeError("validate mode reported no validation time")


def digest_clean(results: Dict[str, List[RunResult]], mode: str) -> str:
    return "yes" if digest_matches_reference(results, mode) else "no"


def mode_display(mode: str) -> str:
    return {
        "table_only": "table-only",
        "final_stack": "final stack",
        "final_stack_batch": "final stack + exact-column batch",
        "final_stack_batch_validate": "final stack + exact-column batch + validate",
    }[mode]


def render_report(
    *,
    workload: WorkloadSpec,
    results: Dict[str, List[RunResult]],
    repeat: int,
    output_path: Path,
) -> str:
    table_total = mode_metric(results, "table_only", "fasim_total_seconds")
    final_total = mode_metric(results, "final_stack", "fasim_total_seconds")
    batch_total = mode_metric(results, "final_stack_batch", "fasim_total_seconds")
    validate_total = mode_metric(results, "final_stack_batch_validate", "fasim_total_seconds")

    lines: List[str] = []
    lines.append("# Fasim Exact-Column Extend Batch Characterization")
    lines.append("")
    lines.append(
        "This docs/script-only report characterizes the default-off real "
        "`FASIM_EXACT_COLUMN_EXTEND_BATCH=1` opt-in with repeated median runs. "
        "It does not add optimization logic, default the batch path, or change "
        "output, scoring, threshold, non-overlap, GPU AUTO, SSW/AVX2/ProfileContext, "
        "SIM-close, recovery, or validation behavior."
    )
    lines.append("")
    lines.append("## Modes")
    lines.append("")
    append_table(
        lines,
        ["Mode", "Environment"],
        [
            ["table-only", "`FASIM_TRANSFERSTRING_TABLE=1`"],
            [
                "final stack",
                "`"
                + " ".join(f"{key}={value}" for key, value in FINAL_STACK_ENV.items())
                + "`",
            ],
            [
                "final stack + exact-column batch",
                "`"
                + " ".join(f"{key}={value}" for key, value in FINAL_STACK_ENV.items())
                + " FASIM_EXACT_COLUMN_EXTEND_BATCH=1`",
            ],
            [
                "final stack + exact-column batch + validate",
                "`"
                + " ".join(f"{key}={value}" for key, value in FINAL_STACK_ENV.items())
                + " FASIM_EXACT_COLUMN_EXTEND_BATCH=1"
                + " FASIM_EXACT_COLUMN_EXTEND_BATCH_VALIDATE=1`",
            ],
        ],
    )
    lines.append("")
    lines.append(
        f"Workload: `{workload.label}`. Each mode uses {repeat} run(s); tables report medians."
    )
    lines.append("")
    lines.append("## Median Summary")
    lines.append("")
    append_table(
        lines,
        [
            "Mode",
            "Total seconds",
            "Speedup vs table-only",
            "Speedup vs final stack",
            "Records",
            "Digest",
            "Digest clean",
            "Batch active",
            "Validate",
        ],
        [
            [
                mode_display("table_only"),
                fmt_seconds(table_total),
                "1.00x",
                "n/a",
                fmt_int(stable_records(results["table_only"])),
                "`" + stable_digest(results["table_only"]) + "`",
                "yes",
                fmt_int(mode_count(results, "table_only", "fasim_exact_column_batch_active")),
                fmt_int(mode_count(results, "table_only", "fasim_exact_column_batch_validate_enabled")),
            ],
            [
                mode_display("final_stack"),
                fmt_seconds(final_total),
                fmt_speedup(speedup(table_total, final_total)),
                "1.00x",
                fmt_int(stable_records(results["final_stack"])),
                "`" + stable_digest(results["final_stack"]) + "`",
                digest_clean(results, "final_stack"),
                fmt_int(mode_count(results, "final_stack", "fasim_exact_column_batch_active")),
                fmt_int(mode_count(results, "final_stack", "fasim_exact_column_batch_validate_enabled")),
            ],
            [
                mode_display("final_stack_batch"),
                fmt_seconds(batch_total),
                fmt_speedup(speedup(table_total, batch_total)),
                fmt_speedup(speedup(final_total, batch_total)),
                fmt_int(stable_records(results["final_stack_batch"])),
                "`" + stable_digest(results["final_stack_batch"]) + "`",
                digest_clean(results, "final_stack_batch"),
                fmt_int(mode_count(results, "final_stack_batch", "fasim_exact_column_batch_active")),
                fmt_int(mode_count(results, "final_stack_batch", "fasim_exact_column_batch_validate_enabled")),
            ],
            [
                mode_display("final_stack_batch_validate"),
                fmt_seconds(validate_total),
                fmt_speedup(speedup(table_total, validate_total)),
                fmt_speedup(speedup(final_total, validate_total)),
                fmt_int(stable_records(results["final_stack_batch_validate"])),
                "`" + stable_digest(results["final_stack_batch_validate"]) + "`",
                digest_clean(results, "final_stack_batch_validate"),
                fmt_int(mode_count(results, "final_stack_batch_validate", "fasim_exact_column_batch_active")),
                fmt_int(mode_count(results, "final_stack_batch_validate", "fasim_exact_column_batch_validate_enabled")),
            ],
        ],
    )
    lines.append("")
    lines.append("`FASIM_EXACT_COLUMN_EXTEND_BATCH_VALIDATE=1` is a correctness gate, not the recommended performance mode.")
    lines.append("")
    lines.append("## Batch Telemetry")
    lines.append("")
    append_table(
        lines,
        [
            "Mode",
            "Requests",
            "Cells",
            "Max cells/request",
            "Batch total",
            "Pack",
            "H2D",
            "Kernel",
            "D2H",
            "Unpack",
            "Apply",
            "CPU fallback",
            "Validate",
        ],
        [
            [
                mode_display(mode),
                fmt_int(mode_count(results, mode, "fasim_exact_column_batch_requests")),
                fmt_int(mode_count(results, mode, "fasim_exact_column_batch_cells")),
                fmt_int(mode_count(results, mode, "fasim_exact_column_batch_max_cells_per_request")),
                fmt_seconds(mode_metric(results, mode, "fasim_exact_column_batch_total_seconds")),
                fmt_seconds(mode_metric(results, mode, "fasim_exact_column_batch_pack_seconds")),
                fmt_seconds(mode_metric(results, mode, "fasim_exact_column_batch_h2d_seconds")),
                fmt_seconds(mode_metric(results, mode, "fasim_exact_column_batch_kernel_seconds")),
                fmt_seconds(mode_metric(results, mode, "fasim_exact_column_batch_d2h_seconds")),
                fmt_seconds(mode_metric(results, mode, "fasim_exact_column_batch_unpack_seconds")),
                fmt_seconds(mode_metric(results, mode, "fasim_exact_column_batch_apply_seconds")),
                fmt_seconds(mode_metric(results, mode, "fasim_exact_column_batch_cpu_fallback_seconds")),
                fmt_seconds(mode_metric(results, mode, "fasim_exact_column_batch_validate_seconds")),
            ]
            for mode in characterized_modes()
        ],
    )
    lines.append("")
    lines.append("## Correctness")
    lines.append("")
    append_table(
        lines,
        ["Mode", "Score", "Endpoint", "ScoreInfo", "Digest", "Batch fallbacks", "GPU fallbacks"],
        [
            [
                mode_display(mode),
                fmt_int(mode_count(results, mode, "fasim_exact_column_batch_score_mismatches")),
                fmt_int(mode_count(results, mode, "fasim_exact_column_batch_endpoint_mismatches")),
                fmt_int(mode_count(results, mode, "fasim_exact_column_batch_scoreinfo_mismatches")),
                fmt_int(mode_count(results, mode, "fasim_exact_column_batch_digest_mismatches")),
                fmt_int(mode_count(results, mode, "fasim_exact_column_batch_fallbacks")),
                fmt_int(mode_count(results, mode, "fasim_gpu_dp_column_fallbacks")),
            ]
            for mode in characterized_modes()
        ],
    )
    lines.append("")
    lines.append("## Decision")
    lines.append("")
    if batch_total > 0.0 and stable_digest(results["final_stack_batch"]) == stable_digest(results["table_only"]):
        lines.append(
            "`FASIM_EXACT_COLUMN_EXTEND_BATCH=1` remains a strong large-workload "
            "opt-in candidate if these medians stay clean and stable. This PR "
            "does not default it."
        )
    else:
        lines.append(
            "The batch path is not promoted by this report. Any mismatch, fallback, "
            "or unstable median should stop defaulting or real-path expansion."
        )
    lines.append("")
    lines.append("## Boundaries")
    lines.append("")
    lines.append("```text")
    lines.append("optimization logic added: no")
    lines.append("default batch enablement: no")
    lines.append("CPU fallback authority: yes")
    lines.append("scoring/threshold/non-overlap change: no")
    lines.append("GPU AUTO policy change: no")
    lines.append("SSW/AVX2/ProfileContext change: no")
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
    parser.add_argument("--dna", required=True)
    parser.add_argument("--rna", required=True)
    parser.add_argument("--label", default="hg38_chr21_H19")
    parser.add_argument("--repeat", type=int, default=3)
    parser.add_argument("--force-auto", action="store_true")
    parser.add_argument(
        "--work-dir",
        default=str(ROOT / ".tmp" / "fasim_exact_column_extend_batch_characterization"),
    )
    parser.add_argument(
        "--output",
        default=str(ROOT / "docs" / "fasim_exact_column_extend_batch_characterization.md"),
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
    work_dir = Path(args.work_dir)
    if not work_dir.is_absolute():
        work_dir = (ROOT / work_dir).resolve()

    results: Dict[str, List[RunResult]] = {}
    for mode in make_modes(force_auto=args.force_auto):
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
        check_characterization(results)
    else:
        require_metrics(results)

    report = render_report(
        workload=workload,
        results=results,
        repeat=args.repeat,
        output_path=Path(args.output).resolve(),
    )
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
