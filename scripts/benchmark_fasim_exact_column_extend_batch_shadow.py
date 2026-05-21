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


FINAL_STACK_ENV = {
    "FASIM_TRANSFERSTRING_TABLE": "1",
    "FASIM_GPU_DP_COLUMN_AUTO": "1",
    "FASIM_SSW_PROFILE_CACHE": "1",
    "FASIM_SSW_AVX2": "1",
    "FASIM_SSW_PROFILE_CONTEXT": "1",
}

SHADOW_KEYS = [
    "fasim_exact_column_batch_shadow_enabled",
    "fasim_exact_column_batch_shadow_supported",
    "fasim_exact_column_batch_shadow_disabled_reason",
    "fasim_exact_column_batch_shadow_requests_total",
    "fasim_exact_column_batch_shadow_requests_compared",
    "fasim_exact_column_batch_shadow_cells",
    "fasim_exact_column_batch_shadow_max_cells_per_request",
    "fasim_exact_column_batch_shadow_cpu_reference_seconds",
    "fasim_exact_column_batch_shadow_shadow_total_seconds",
    "fasim_exact_column_batch_shadow_kernel_seconds",
    "fasim_exact_column_batch_shadow_h2d_seconds",
    "fasim_exact_column_batch_shadow_d2h_seconds",
    "fasim_exact_column_batch_shadow_pack_seconds",
    "fasim_exact_column_batch_shadow_unpack_seconds",
    "fasim_exact_column_batch_shadow_h2d_bytes",
    "fasim_exact_column_batch_shadow_d2h_bytes",
    "fasim_exact_column_batch_shadow_score_mismatches",
    "fasim_exact_column_batch_shadow_endpoint_mismatches",
    "fasim_exact_column_batch_shadow_scoreinfo_mismatches",
    "fasim_exact_column_batch_shadow_total_mismatches",
    "fasim_exact_column_batch_shadow_first_mismatch_request",
    "fasim_exact_column_batch_shadow_est_seconds_saved",
    "fasim_exact_column_batch_shadow_net_saved_seconds",
]

EXACT_COLUMN_KEYS = [
    "fasim_total_seconds",
    "fasim_gpu_dp_column_auto_active",
    "fasim_gpu_dp_column_active",
    "fasim_gpu_dp_column_exact_column_extend_seconds",
    "fasim_gpu_dp_column_exact_extend_windows",
    "fasim_gpu_dp_column_fallbacks",
]


def make_modes(force_auto: bool) -> List[ModeSpec]:
    final_env = dict(FINAL_STACK_ENV)
    if force_auto:
        final_env["FASIM_GPU_DP_COLUMN_AUTO_MIN_WINDOWS"] = "1"
        final_env["FASIM_GPU_DP_COLUMN_AUTO_MIN_CELLS"] = "1"
    return [
        ModeSpec("final_stack", "avx2", final_env),
        ModeSpec(
            "final_stack_shadow",
            "avx2",
            dict(final_env, FASIM_EXACT_COLUMN_EXTEND_BATCH_SHADOW="1"),
        ),
    ]


def mode_metric(results: Dict[str, List[RunResult]], mode: str, key: str) -> float:
    return median_metric(results[mode], key)


def mode_count(results: Dict[str, List[RunResult]], mode: str, key: str) -> int:
    return median_count(results[mode], key)


def percent(numerator: float, denominator: float) -> str:
    if denominator <= 0.0:
        return "n/a"
    return f"{100.0 * numerator / denominator:.2f}%"


def require_metrics(results: Dict[str, List[RunResult]]) -> None:
    for mode in ["final_stack", "final_stack_shadow"]:
        for key in EXACT_COLUMN_KEYS + SHADOW_KEYS:
            mode_metric(results, mode, key)


def require_zero(results: Dict[str, List[RunResult]], mode: str, keys: Iterable[str]) -> None:
    for key in keys:
        if mode_count(results, mode, key) != 0:
            raise RuntimeError(f"{mode}: expected {key}=0")


def check_shadow(results: Dict[str, List[RunResult]]) -> None:
    require_metrics(results)
    reference_digest = stable_digest(results["final_stack"])
    reference_records = stable_records(results["final_stack"])
    if stable_digest(results["final_stack_shadow"]) != reference_digest:
        raise RuntimeError("shadow changed output digest")
    if stable_records(results["final_stack_shadow"]) != reference_records:
        raise RuntimeError("shadow changed output record count")
    if mode_count(results, "final_stack", "fasim_exact_column_batch_shadow_enabled") != 0:
        raise RuntimeError("shadow enabled by default")
    if mode_count(results, "final_stack_shadow", "fasim_exact_column_batch_shadow_enabled") != 1:
        raise RuntimeError("shadow was not enabled")
    if mode_count(results, "final_stack_shadow", "fasim_exact_column_batch_shadow_supported") != 1:
        raise RuntimeError("shadow did not report supported=1")
    if mode_count(results, "final_stack_shadow", "fasim_exact_column_batch_shadow_requests_compared") <= 0:
        raise RuntimeError("shadow compared no requests")
    require_zero(
        results,
        "final_stack_shadow",
        [
            "fasim_exact_column_batch_shadow_score_mismatches",
            "fasim_exact_column_batch_shadow_endpoint_mismatches",
            "fasim_exact_column_batch_shadow_scoreinfo_mismatches",
            "fasim_exact_column_batch_shadow_total_mismatches",
        ],
    )
    if mode_count(results, "final_stack_shadow", "fasim_gpu_dp_column_fallbacks") != 0:
        raise RuntimeError("GPU DP column fallbacks appeared")


def render_report(
    *,
    workload: WorkloadSpec,
    results: Dict[str, List[RunResult]],
    repeat: int,
    output_path: Path,
) -> str:
    final_total = mode_metric(results, "final_stack", "fasim_total_seconds")
    shadow_total = mode_metric(results, "final_stack_shadow", "fasim_total_seconds")
    shadow_cpu = mode_metric(
        results, "final_stack_shadow", "fasim_exact_column_batch_shadow_cpu_reference_seconds"
    )
    shadow_total_seconds = mode_metric(
        results, "final_stack_shadow", "fasim_exact_column_batch_shadow_shadow_total_seconds"
    )

    lines: List[str] = []
    lines.append("# Fasim Exact-Column Extend Batch Shadow")
    lines.append("")
    lines.append(
        "This PR adds a default-off diagnostic shadow for the exact-column "
        "extend step identified by the final speed stack decomposition. CPU "
        "exact-column extend remains authoritative; shadow output is never fed "
        "into fastSIM emit or final output."
    )
    lines.append("")
    lines.append("Final stack under test:")
    lines.append("")
    lines.append("```bash")
    for key, value in FINAL_STACK_ENV.items():
        lines.append(f"{key}={value}")
    lines.append("# shadow mode adds:")
    lines.append("FASIM_EXACT_COLUMN_EXTEND_BATCH_SHADOW=1")
    lines.append("```")
    lines.append("")
    lines.append(f"Workload: `{workload.label}`. Each mode uses {repeat} run(s); tables report medians.")
    lines.append("")
    lines.append("## Performance")
    lines.append("")
    append_table(
        lines,
        ["Mode", "Total seconds", "Records", "Digest", "Shadow enabled"],
        [
            [
                "final_stack",
                fmt_seconds(final_total),
                fmt_int(stable_records(results["final_stack"])),
                "`" + stable_digest(results["final_stack"]) + "`",
                fmt_int(mode_count(results, "final_stack", "fasim_exact_column_batch_shadow_enabled")),
            ],
            [
                "final_stack_shadow",
                fmt_seconds(shadow_total),
                fmt_int(stable_records(results["final_stack_shadow"])),
                "`" + stable_digest(results["final_stack_shadow"]) + "`",
                fmt_int(mode_count(results, "final_stack_shadow", "fasim_exact_column_batch_shadow_enabled")),
            ],
        ],
    )
    lines.append("")
    lines.append("## Request Shape")
    lines.append("")
    requests = mode_count(results, "final_stack_shadow", "fasim_exact_column_batch_shadow_requests_total")
    cells = mode_count(results, "final_stack_shadow", "fasim_exact_column_batch_shadow_cells")
    avg_cells = int(round(cells / requests)) if requests > 0 else 0
    append_table(
        lines,
        ["Requests", "Compared", "Cells", "Avg cells/request", "H2D bytes", "D2H bytes"],
        [
            [
                fmt_int(requests),
                fmt_int(mode_count(results, "final_stack_shadow", "fasim_exact_column_batch_shadow_requests_compared")),
                fmt_int(cells),
                fmt_int(avg_cells),
                fmt_int(mode_count(results, "final_stack_shadow", "fasim_exact_column_batch_shadow_h2d_bytes")),
                fmt_int(mode_count(results, "final_stack_shadow", "fasim_exact_column_batch_shadow_d2h_bytes")),
            ]
        ],
    )
    lines.append("")
    lines.append("## Correctness")
    lines.append("")
    append_table(
        lines,
        ["Field", "Mismatches", "First mismatch", "Notes"],
        [
            [
                "score",
                fmt_int(mode_count(results, "final_stack_shadow", "fasim_exact_column_batch_shadow_score_mismatches")),
                fmt_int(mode_count(results, "final_stack_shadow", "fasim_exact_column_batch_shadow_first_mismatch_request")),
                "max column score contract",
            ],
            [
                "endpoint",
                fmt_int(mode_count(results, "final_stack_shadow", "fasim_exact_column_batch_shadow_endpoint_mismatches")),
                fmt_int(mode_count(results, "final_stack_shadow", "fasim_exact_column_batch_shadow_first_mismatch_request")),
                "max-score column endpoint",
            ],
            [
                "scoreInfo",
                fmt_int(mode_count(results, "final_stack_shadow", "fasim_exact_column_batch_shadow_scoreinfo_mismatches")),
                fmt_int(mode_count(results, "final_stack_shadow", "fasim_exact_column_batch_shadow_first_mismatch_request")),
                "score/position records consumed by fastSIM emit",
            ],
            [
                "total",
                fmt_int(mode_count(results, "final_stack_shadow", "fasim_exact_column_batch_shadow_total_mismatches")),
                fmt_int(mode_count(results, "final_stack_shadow", "fasim_exact_column_batch_shadow_first_mismatch_request")),
                "shadow remains diagnostic only",
            ],
        ],
    )
    lines.append("")
    lines.append("## Timing")
    lines.append("")
    append_table(
        lines,
        ["CPU reference", "Shadow total", "Kernel", "Transfer", "Estimated saved"],
        [
            [
                fmt_seconds(shadow_cpu),
                fmt_seconds(shadow_total_seconds),
                fmt_seconds(mode_metric(results, "final_stack_shadow", "fasim_exact_column_batch_shadow_kernel_seconds")),
                (
                    "h2d="
                    + fmt_int(mode_count(results, "final_stack_shadow", "fasim_exact_column_batch_shadow_h2d_bytes"))
                    + ", d2h="
                    + fmt_int(mode_count(results, "final_stack_shadow", "fasim_exact_column_batch_shadow_d2h_bytes"))
                ),
                fmt_seconds(
                    mode_metric(results, "final_stack_shadow", "fasim_exact_column_batch_shadow_est_seconds_saved")
                ),
            ]
        ],
    )
    lines.append("")
    lines.append(
        "The current shadow is a CPU-side diagnostic contract check. "
        "`kernel_seconds=0` means this PR does not add a new CUDA kernel; a later "
        "real batched GPU opt-in would need to replace the diagnostic shadow "
        "with a packed request/output implementation and validate the same fields."
    )
    lines.append(
        "`estimated saved` is an upper-bound diagnostic for the exact-column "
        "contract only. It is not a measured wall-clock speedup from this PR."
    )
    lines.append("")
    lines.append("## Boundaries")
    lines.append("")
    lines.append("```text")
    lines.append("real output changed: no")
    lines.append("shadow output used by emit: no")
    lines.append("default enablement: no")
    lines.append("scoring/threshold/non-overlap change: no")
    lines.append("GPU AUTO policy change: no")
    lines.append("SSW/AVX2/ProfileContext change: no")
    lines.append("SIM-close/recovery change: no")
    lines.append("validation relaxation: no")
    lines.append("```")
    lines.append("")
    if mode_count(results, "final_stack_shadow", "fasim_exact_column_batch_shadow_total_mismatches") == 0:
        lines.append(
            "Decision: contract shadow is clean. A real batched GPU exact-column "
            "extend remains a separate opt-in PR and should keep CPU validation/fallback."
        )
    else:
        lines.append("Decision: mismatches appeared; debug the exact-column contract before performance work.")

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
        default=str(ROOT / ".tmp" / "fasim_exact_column_extend_batch_shadow_benchmark"),
    )
    parser.add_argument(
        "--output",
        default=str(ROOT / "docs" / "fasim_exact_column_extend_batch_shadow.md"),
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
        check_shadow(results)
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
