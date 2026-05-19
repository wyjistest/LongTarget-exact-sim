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


SCALING_KEYS = [
    "fasim_aligner_accelign_shadow_enabled",
    "fasim_aligner_accelign_shadow_supported",
    "fasim_aligner_accelign_shadow_disabled_reason",
    "fasim_aligner_accelign_shadow_requests_total",
    "fasim_aligner_accelign_shadow_requests_compared",
    "fasim_aligner_accelign_shadow_requests_unsupported",
    "fasim_aligner_accelign_shadow_query_bases",
    "fasim_aligner_accelign_shadow_target_bases",
    "fasim_aligner_accelign_shadow_cells",
    "fasim_aligner_accelign_shadow_h2d_bytes",
    "fasim_aligner_accelign_shadow_d2h_bytes",
    "fasim_aligner_accelign_shadow_kernel_seconds",
    "fasim_aligner_accelign_shadow_total_seconds",
    "fasim_aligner_accelign_shadow_cpu_reference_seconds",
    "fasim_aligner_accelign_shadow_score_mismatches",
    "fasim_aligner_accelign_shadow_endpoint_mismatches",
    "fasim_aligner_accelign_shadow_endpoint_same_score_mismatches",
    "fasim_aligner_accelign_shadow_ref_end_mismatches",
    "fasim_aligner_accelign_shadow_query_end_mismatches",
    "fasim_aligner_accelign_shadow_both_end_mismatches",
    "fasim_aligner_accelign_shadow_off_by_one_mismatches",
    "fasim_aligner_accelign_shadow_ref_end_gpu_before_cpu",
    "fasim_aligner_accelign_shadow_ref_end_gpu_after_cpu",
    "fasim_aligner_accelign_shadow_query_end_gpu_before_cpu",
    "fasim_aligner_accelign_shadow_query_end_gpu_after_cpu",
    "fasim_aligner_accelign_shadow_ref_end_delta_abs_max",
    "fasim_aligner_accelign_shadow_query_end_delta_abs_max",
    "fasim_aligner_accelign_shadow_first_mismatch_request",
    "fasim_aligner_accelign_shadow_first_mismatch_cpu_score",
    "fasim_aligner_accelign_shadow_first_mismatch_gpu_score",
    "fasim_aligner_accelign_shadow_first_mismatch_cpu_ref_end",
    "fasim_aligner_accelign_shadow_first_mismatch_gpu_ref_end",
    "fasim_aligner_accelign_shadow_first_mismatch_cpu_query_end",
    "fasim_aligner_accelign_shadow_first_mismatch_gpu_query_end",
    "fasim_aligner_accelign_shadow_total_mismatches",
    "fasim_aligner_accelign_shadow_fallbacks",
    "fasim_aligner_accelign_shadow_has_score_contract",
    "fasim_aligner_accelign_shadow_has_endpoint_contract",
    "fasim_aligner_accelign_shadow_has_cigar_contract",
    "fasim_aligner_accelign_shadow_has_alignment_string_contract",
    "fasim_aligner_accelign_shadow_uses_runtime_output",
]

SCORE_ONLY_KEYS = [
    "fasim_accelign_score_only_shadow_enabled",
    "fasim_accelign_score_only_mode",
    "fasim_accelign_score_only_requests",
    "fasim_accelign_score_only_requests_compared",
    "fasim_accelign_score_only_requests_unsupported",
    "fasim_accelign_score_only_score_mismatches",
    "fasim_accelign_score_only_cpu_seconds",
    "fasim_accelign_score_only_kernel_seconds",
    "fasim_accelign_score_only_total_seconds",
    "fasim_accelign_score_only_h2d_bytes",
    "fasim_accelign_score_only_d2h_bytes",
    "fasim_accelign_score_only_query_reuse_active",
    "fasim_accelign_score_only_query_staging_bytes",
    "fasim_accelign_score_only_target_staging_bytes",
    "fasim_accelign_score_only_has_endpoint_contract",
    "fasim_accelign_score_only_uses_runtime_output",
]

SCORE_PRECHECK_KEYS = [
    "fasim_accelign_score_precheck_shadow_enabled",
    "fasim_accelign_score_precheck_requests",
    "fasim_accelign_score_precheck_requests_compared",
    "fasim_accelign_score_precheck_requests_unsupported",
    "fasim_accelign_score_precheck_score_mismatches",
    "fasim_accelign_score_precheck_predicted_reject",
    "fasim_accelign_score_precheck_true_reject",
    "fasim_accelign_score_precheck_false_reject",
    "fasim_accelign_score_precheck_false_keep",
    "fasim_accelign_score_precheck_est_cpu_align_calls_saved",
    "fasim_accelign_score_precheck_est_cpu_align_seconds_saved",
    "fasim_accelign_score_precheck_cpu_seconds",
    "fasim_accelign_score_precheck_kernel_seconds",
    "fasim_accelign_score_precheck_accelign_seconds",
    "fasim_accelign_score_precheck_net_est_seconds_saved",
    "fasim_accelign_score_precheck_h2d_bytes",
    "fasim_accelign_score_precheck_d2h_bytes",
    "fasim_accelign_score_precheck_query_staging_bytes",
    "fasim_accelign_score_precheck_target_staging_bytes",
    "fasim_accelign_score_precheck_query_reuse_active",
    "fasim_accelign_score_precheck_has_endpoint_contract",
    "fasim_accelign_score_precheck_uses_runtime_output",
]


def parse_sample_sizes(value: str) -> List[int]:
    sizes: List[int] = []
    for item in value.split(","):
        item = item.strip()
        if not item:
            continue
        if item.lower() == "full":
            sizes.append(0)
            continue
        parsed = int(item)
        if parsed <= 0:
            raise RuntimeError(f"invalid sample size: {item}")
        sizes.append(parsed)
    if not sizes:
        raise RuntimeError("no sample sizes requested")
    return sizes


def sample_label(size: int) -> str:
    return "full" if size == 0 else str(size)


def sample_cap(size: int) -> str:
    return "2147483647" if size == 0 else str(size)


def mode_count(results: Dict[str, List[RunResult]], mode: str, key: str) -> int:
    return median_count(results[mode], key)


def mode_metric(results: Dict[str, List[RunResult]], mode: str, key: str) -> float:
    return median_metric(results[mode], key)


def digest_matches_reference(results: Dict[str, List[RunResult]], mode: str) -> bool:
    return stable_digest(results[mode]) == stable_digest(results["table_only"])


def require_scaling_metrics(results: Dict[str, List[RunResult]], modes: List[str]) -> None:
    for mode in modes:
        for key in SCALING_KEYS:
            mode_metric(results, mode, key)


def require_score_only_metrics(results: Dict[str, List[RunResult]], modes: List[str]) -> None:
    for mode in modes:
        for key in SCORE_ONLY_KEYS:
            mode_metric(results, mode, key)


def require_score_precheck_metrics(results: Dict[str, List[RunResult]], modes: List[str]) -> None:
    for mode in modes:
        for key in SCORE_PRECHECK_KEYS:
            mode_metric(results, mode, key)


def throughput(numerator: float, seconds: float) -> float:
    return numerator / seconds if seconds > 0.0 else 0.0


def render_report(
    *,
    workload: WorkloadSpec,
    results: Dict[str, List[RunResult]],
    sample_sizes: List[int],
    repeat: int,
    output_path: Path,
) -> str:
    shadow_modes = [f"accelign_{sample_label(size)}" for size in sample_sizes]
    lines: List[str] = []
    lines.append("# Fasim Accelign Aligner Shadow Scaling")
    lines.append("")
    lines.append(
        "This report characterizes scaling for the default-off Accelign float "
        "`aligner.Align` shadow. CPU `aligner.Align` remains the runtime "
        "authority; Accelign results are never used for output. This does not "
        "add CIGAR/alignment-string reconstruction and does not change scoring, "
        "thresholds, non-overlap, GPU DP column AUTO policy, SIM-close, or "
        "recovery behavior."
    )
    lines.append("")
    lines.append(
        "Accelign shadow timing is extra diagnostic work after CPU "
        "`aligner.Align`; compare sampled CPU reference seconds against "
        "Accelign kernel/total seconds, not Fasim wall-clock as a real-path "
        "speedup."
    )
    lines.append("")
    lines.append(f"Workload: `{workload.label}`. Each mode uses {repeat} run(s); tables report medians.")
    lines.append("")

    table_total = mode_metric(results, "table_only", "fasim_total_seconds")
    auto_total = mode_metric(results, "auto", "fasim_total_seconds")
    lines.append("## Baseline")
    lines.append("")
    append_table(
        lines,
        [
            "Observed windows",
            "Observed cells",
            "Table seconds",
            "AUTO seconds",
            "AUTO speedup",
            "Digest",
            "Records",
            "AUTO digest match",
        ],
        [
            [
                fmt_int(mode_count(results, "auto", "fasim_gpu_dp_column_auto_observed_windows")),
                fmt_int(mode_count(results, "auto", "fasim_gpu_dp_column_auto_observed_cells")),
                fmt_seconds(table_total),
                fmt_seconds(auto_total),
                fmt_speedup(speedup(table_total, auto_total)),
                "`" + stable_digest(results["table_only"]) + "`",
                str(stable_records(results["table_only"])),
                "yes" if digest_matches_reference(results, "auto") else "no",
            ]
        ],
    )
    lines.append("")

    rows: List[List[str]] = []
    for size in sample_sizes:
        mode = f"accelign_{sample_label(size)}"
        compared = mode_count(results, mode, "fasim_aligner_accelign_shadow_requests_compared")
        cpu_seconds = mode_metric(results, mode, "fasim_aligner_accelign_shadow_cpu_reference_seconds")
        kernel_seconds = mode_metric(results, mode, "fasim_aligner_accelign_shadow_kernel_seconds")
        total_seconds = mode_metric(results, mode, "fasim_aligner_accelign_shadow_total_seconds")
        overhead_seconds = total_seconds - kernel_seconds
        rows.append(
            [
                sample_label(size),
                fmt_int(mode_count(results, mode, "fasim_aligner_accelign_shadow_requests_total")),
                fmt_int(compared),
                fmt_int(mode_count(results, mode, "fasim_aligner_accelign_shadow_requests_unsupported")),
                fmt_seconds(cpu_seconds),
                fmt_seconds(kernel_seconds),
                fmt_seconds(overhead_seconds),
                fmt_seconds(total_seconds),
                fmt_speedup(speedup(cpu_seconds, kernel_seconds)),
                fmt_speedup(speedup(cpu_seconds, total_seconds)),
                fmt_int(mode_count(results, mode, "fasim_aligner_accelign_shadow_score_mismatches")),
                fmt_int(mode_count(results, mode, "fasim_aligner_accelign_shadow_endpoint_mismatches")),
                fmt_int(mode_count(results, mode, "fasim_aligner_accelign_shadow_total_mismatches")),
            ]
        )

    lines.append("## Scaling")
    lines.append("")
    append_table(
        lines,
        [
            "Sample cap",
            "Requests total",
            "Compared",
            "Skipped",
            "CPU reference seconds",
            "Accelign kernel seconds",
            "Staging/overhead seconds",
            "Accelign shadow total seconds",
            "Kernel vs CPU speedup",
            "Total vs CPU speedup",
            "Score mismatches",
            "Endpoint mismatches",
            "Total mismatches",
        ],
        rows,
    )
    lines.append("")

    throughput_rows: List[List[str]] = []
    for size in sample_sizes:
        mode = f"accelign_{sample_label(size)}"
        compared = mode_count(results, mode, "fasim_aligner_accelign_shadow_requests_compared")
        cells = mode_count(results, mode, "fasim_aligner_accelign_shadow_cells")
        cpu_seconds = mode_metric(results, mode, "fasim_aligner_accelign_shadow_cpu_reference_seconds")
        kernel_seconds = mode_metric(results, mode, "fasim_aligner_accelign_shadow_kernel_seconds")
        total_seconds = mode_metric(results, mode, "fasim_aligner_accelign_shadow_total_seconds")
        throughput_rows.append(
            [
                sample_label(size),
                fmt_int(compared),
                fmt_int(cells),
                f"{throughput(compared, cpu_seconds):.2f}",
                f"{throughput(compared, kernel_seconds):.2f}",
                f"{throughput(compared, total_seconds):.2f}",
                f"{throughput(cells, cpu_seconds):.2f}",
                f"{throughput(cells, kernel_seconds):.2f}",
                f"{throughput(cells, total_seconds):.2f}",
            ]
        )
    lines.append("## Throughput")
    lines.append("")
    append_table(
        lines,
        [
            "Sample cap",
            "Compared",
            "Cells",
            "CPU requests/sec",
            "Accelign kernel requests/sec",
            "Accelign total requests/sec",
            "CPU cells/sec",
            "Accelign kernel cells/sec",
            "Accelign total cells/sec",
        ],
        throughput_rows,
    )
    lines.append("")

    taxonomy_rows: List[List[str]] = []
    for size in sample_sizes:
        mode = f"accelign_{sample_label(size)}"
        taxonomy_rows.append(
            [
                sample_label(size),
                fmt_int(mode_count(results, mode, "fasim_aligner_accelign_shadow_endpoint_mismatches")),
                fmt_int(mode_count(results, mode, "fasim_aligner_accelign_shadow_endpoint_same_score_mismatches")),
                fmt_int(mode_count(results, mode, "fasim_aligner_accelign_shadow_ref_end_mismatches")),
                fmt_int(mode_count(results, mode, "fasim_aligner_accelign_shadow_query_end_mismatches")),
                fmt_int(mode_count(results, mode, "fasim_aligner_accelign_shadow_both_end_mismatches")),
                fmt_int(mode_count(results, mode, "fasim_aligner_accelign_shadow_off_by_one_mismatches")),
            ]
        )
    lines.append("## Endpoint Taxonomy")
    lines.append("")
    append_table(
        lines,
        [
            "Sample cap",
            "Endpoint mismatches",
            "Same-score endpoint mismatches",
            "Ref-end mismatches",
            "Query-end mismatches",
            "Both-end mismatches",
            "Off-by-one mismatches",
        ],
        taxonomy_rows,
    )
    lines.append("")

    direction_rows: List[List[str]] = []
    for size in sample_sizes:
        mode = f"accelign_{sample_label(size)}"
        direction_rows.append(
            [
                sample_label(size),
                fmt_int(mode_count(results, mode, "fasim_aligner_accelign_shadow_ref_end_gpu_before_cpu")),
                fmt_int(mode_count(results, mode, "fasim_aligner_accelign_shadow_ref_end_gpu_after_cpu")),
                fmt_int(mode_count(results, mode, "fasim_aligner_accelign_shadow_query_end_gpu_before_cpu")),
                fmt_int(mode_count(results, mode, "fasim_aligner_accelign_shadow_query_end_gpu_after_cpu")),
                fmt_int(mode_count(results, mode, "fasim_aligner_accelign_shadow_ref_end_delta_abs_max")),
                fmt_int(mode_count(results, mode, "fasim_aligner_accelign_shadow_query_end_delta_abs_max")),
            ]
        )
    lines.append("## Endpoint Direction")
    lines.append("")
    append_table(
        lines,
        [
            "Sample cap",
            "Ref-end GPU before CPU",
            "Ref-end GPU after CPU",
            "Query-end GPU before CPU",
            "Query-end GPU after CPU",
            "Max abs ref-end delta",
            "Max abs query-end delta",
        ],
        direction_rows,
    )
    lines.append("")

    first_rows: List[List[str]] = []
    for size in sample_sizes:
        mode = f"accelign_{sample_label(size)}"
        first_rows.append(
            [
                sample_label(size),
                fmt_int(mode_count(results, mode, "fasim_aligner_accelign_shadow_first_mismatch_request")),
                fmt_int(mode_count(results, mode, "fasim_aligner_accelign_shadow_first_mismatch_cpu_score")),
                fmt_int(mode_count(results, mode, "fasim_aligner_accelign_shadow_first_mismatch_gpu_score")),
                fmt_int(mode_count(results, mode, "fasim_aligner_accelign_shadow_first_mismatch_cpu_ref_end")),
                fmt_int(mode_count(results, mode, "fasim_aligner_accelign_shadow_first_mismatch_gpu_ref_end")),
                fmt_int(mode_count(results, mode, "fasim_aligner_accelign_shadow_first_mismatch_cpu_query_end")),
                fmt_int(mode_count(results, mode, "fasim_aligner_accelign_shadow_first_mismatch_gpu_query_end")),
            ]
        )
    lines.append("## First Mismatch")
    lines.append("")
    append_table(
        lines,
        [
            "Sample cap",
            "Request",
            "CPU score",
            "Accelign score",
            "CPU ref_end",
            "Accelign ref_end",
            "CPU query_end",
            "Accelign query_end",
        ],
        first_rows,
    )
    lines.append("")

    contract_rows: List[List[str]] = []
    for size in sample_sizes:
        mode = f"accelign_{sample_label(size)}"
        contract_rows.append(
            [
                sample_label(size),
                str(mode_count(results, mode, "fasim_aligner_accelign_shadow_has_score_contract")),
                str(mode_count(results, mode, "fasim_aligner_accelign_shadow_has_endpoint_contract")),
                str(mode_count(results, mode, "fasim_aligner_accelign_shadow_has_cigar_contract")),
                str(mode_count(results, mode, "fasim_aligner_accelign_shadow_has_alignment_string_contract")),
                str(mode_count(results, mode, "fasim_aligner_accelign_shadow_uses_runtime_output")),
            ]
        )
    lines.append("## Contract Coverage")
    lines.append("")
    append_table(
        lines,
        [
            "Sample cap",
            "Score",
            "Endpoint",
            "CIGAR",
            "Alignment string",
            "Uses runtime output",
        ],
        contract_rows,
    )
    lines.append("")

    largest_mode = shadow_modes[-1]
    largest_score_mismatches = mode_count(
        results, largest_mode, "fasim_aligner_accelign_shadow_score_mismatches"
    )
    largest_endpoint_mismatches = mode_count(
        results, largest_mode, "fasim_aligner_accelign_shadow_endpoint_mismatches"
    )
    largest_cpu = mode_metric(
        results, largest_mode, "fasim_aligner_accelign_shadow_cpu_reference_seconds"
    )
    largest_kernel = mode_metric(
        results, largest_mode, "fasim_aligner_accelign_shadow_kernel_seconds"
    )
    largest_total = mode_metric(
        results, largest_mode, "fasim_aligner_accelign_shadow_total_seconds"
    )
    lines.append("## Decision")
    lines.append("")
    if largest_score_mismatches != 0:
        lines.append(
            "Accelign score mismatched CPU `aligner.Align`; debug scoring before "
            "any performance work."
        )
    elif largest_endpoint_mismatches != 0:
        lines.append(
            "Accelign score is clean at the largest sampled size, but endpoint "
            "mismatches remain. Do not use Accelign as an endpoint authority or "
            "runtime replacement."
        )
    elif largest_total < largest_cpu:
        lines.append(
            "Accelign shadow total beats the sampled CPU reference and score/"
            "endpoint contracts are clean at the largest sampled size. Next work "
            "can investigate CIGAR/alignment-string coverage and real-path "
            "validation."
        )
    elif largest_kernel < largest_cpu:
        lines.append(
            "Accelign kernel beats the sampled CPU reference, but total shadow "
            "time does not. Next work should target request staging/layout before "
            "any real-path integration."
        )
    else:
        lines.append(
            "Accelign remains slower than the sampled CPU reference at the "
            "largest sampled size. Do not expand this path toward real output."
        )
    lines.append("")
    lines.append("```text")
    lines.append(f"largest_cpu_reference_seconds = {fmt_seconds(largest_cpu)}")
    lines.append(f"largest_accelign_kernel_seconds = {fmt_seconds(largest_kernel)}")
    lines.append(f"largest_accelign_total_seconds = {fmt_seconds(largest_total)}")
    lines.append("```")
    lines.append("")
    lines.append("## Boundaries")
    lines.append("")
    lines.append("```text")
    lines.append("use Accelign result for output: no")
    lines.append("skip CPU aligner.Align: no")
    lines.append("CIGAR/alignment-string reconstruction: no")
    lines.append("scoring/threshold/non-overlap change: no")
    lines.append("GPU DP column AUTO policy change: no")
    lines.append("validation relaxation: no")
    lines.append("SIM-close/recovery change: no")
    lines.append("```")

    report = "\n".join(lines)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report + "\n", encoding="utf-8")
    return report


def render_score_only_report(
    *,
    workload: WorkloadSpec,
    results: Dict[str, List[RunResult]],
    sample_sizes: List[int],
    repeat: int,
    output_path: Path,
) -> str:
    score_modes = [f"accelign_score_only_{sample_label(size)}" for size in sample_sizes]
    lines: List[str] = []
    lines.append("# Fasim Accelign Score-Only Query-Reuse Shadow")
    lines.append("")
    lines.append(
        "This report characterizes a default-off Accelign score-only shadow. "
        "CPU `aligner.Align` remains the runtime authority; Accelign scores are "
        "not used for output, thresholding, non-overlap, CIGAR/alignment output, "
        "SIM-close, or recovery."
    )
    lines.append("")
    lines.append(
        "Endpoint comparison is intentionally unsupported here because the "
        "endpoint taxonomy showed same-score endpoint selection differences. "
        "This mode measures score contract, timing, and duplicate query staging "
        "costs before any one-to-many/PSSM reuse work."
    )
    lines.append("")
    lines.append(f"Workload: `{workload.label}`. Each mode uses {repeat} run(s); tables report medians.")
    lines.append("")

    rows: List[List[str]] = []
    for size in sample_sizes:
        mode = f"accelign_score_only_{sample_label(size)}"
        requests = mode_count(results, mode, "fasim_accelign_score_only_requests")
        compared = mode_count(results, mode, "fasim_accelign_score_only_requests_compared")
        cpu_seconds = mode_metric(results, mode, "fasim_accelign_score_only_cpu_seconds")
        kernel_seconds = mode_metric(results, mode, "fasim_accelign_score_only_kernel_seconds")
        total_seconds = mode_metric(results, mode, "fasim_accelign_score_only_total_seconds")
        overhead_seconds = total_seconds - kernel_seconds
        rows.append(
            [
                sample_label(size),
                fmt_int(requests),
                fmt_int(compared),
                fmt_int(mode_count(results, mode, "fasim_accelign_score_only_requests_unsupported")),
                fmt_seconds(cpu_seconds),
                fmt_seconds(kernel_seconds),
                fmt_seconds(overhead_seconds),
                fmt_seconds(total_seconds),
                fmt_speedup(speedup(cpu_seconds, kernel_seconds)),
                fmt_speedup(speedup(cpu_seconds, total_seconds)),
                fmt_int(mode_count(results, mode, "fasim_accelign_score_only_score_mismatches")),
                str(mode_count(results, mode, "fasim_accelign_score_only_has_endpoint_contract")),
                str(mode_count(results, mode, "fasim_accelign_score_only_uses_runtime_output")),
            ]
        )
    lines.append("## Score-Only Timing")
    lines.append("")
    append_table(
        lines,
        [
            "Sample cap",
            "Requests",
            "Compared",
            "Unsupported",
            "CPU reference seconds",
            "Accelign kernel seconds",
            "Staging/overhead seconds",
            "Accelign total seconds",
            "Kernel vs CPU speedup",
            "Total vs CPU speedup",
            "Score mismatches",
            "Endpoint contract",
            "Uses runtime output",
        ],
        rows,
    )
    lines.append("")

    staging_rows: List[List[str]] = []
    for size in sample_sizes:
        mode = f"accelign_score_only_{sample_label(size)}"
        h2d = mode_count(results, mode, "fasim_accelign_score_only_h2d_bytes")
        d2h = mode_count(results, mode, "fasim_accelign_score_only_d2h_bytes")
        query_bytes = mode_count(results, mode, "fasim_accelign_score_only_query_staging_bytes")
        target_bytes = mode_count(results, mode, "fasim_accelign_score_only_target_staging_bytes")
        staging_rows.append(
            [
                sample_label(size),
                fmt_int(h2d),
                fmt_int(d2h),
                fmt_int(query_bytes),
                fmt_int(target_bytes),
                f"{(query_bytes / h2d * 100.0) if h2d else 0.0:.2f}%",
                f"{(target_bytes / h2d * 100.0) if h2d else 0.0:.2f}%",
                str(mode_count(results, mode, "fasim_accelign_score_only_query_reuse_active")),
            ]
        )
    lines.append("## Staging")
    lines.append("")
    append_table(
        lines,
        [
            "Sample cap",
            "H2D bytes",
            "D2H bytes",
            "Query staging bytes",
            "Target staging bytes",
            "Query share of H2D",
            "Target share of H2D",
            "Query reuse active",
        ],
        staging_rows,
    )
    lines.append("")

    largest_mode = score_modes[-1]
    largest_score_mismatches = mode_count(
        results, largest_mode, "fasim_accelign_score_only_score_mismatches"
    )
    largest_cpu = mode_metric(results, largest_mode, "fasim_accelign_score_only_cpu_seconds")
    largest_kernel = mode_metric(results, largest_mode, "fasim_accelign_score_only_kernel_seconds")
    largest_total = mode_metric(results, largest_mode, "fasim_accelign_score_only_total_seconds")
    largest_query_reuse = mode_count(
        results, largest_mode, "fasim_accelign_score_only_query_reuse_active"
    )

    lines.append("## Decision")
    lines.append("")
    if largest_score_mismatches != 0:
        lines.append("Accelign score-only mismatched CPU `aligner.Align`; stop this path.")
    elif largest_total < largest_cpu and largest_query_reuse != 0:
        lines.append(
            "Score-only is clean and query reuse is active with total shadow "
            "time below the sampled CPU reference. Next work can design a "
            "score-only precheck/CPU traceback bridge."
        )
    elif largest_total < largest_cpu:
        lines.append(
            "Score-only is clean and faster than sampled CPU reference, but "
            "query reuse is not active. Next work should evaluate one-to-many "
            "or PSSM query reuse before any real-path design."
        )
    elif largest_kernel < largest_cpu:
        lines.append(
            "Score-only kernel is faster than sampled CPU reference, but total "
            "time is not. Request staging/layout dominates the next decision."
        )
    else:
        lines.append("Score-only is clean but not faster; stop Accelign score-only work.")
    lines.append("")
    lines.append("```text")
    lines.append(f"largest_cpu_reference_seconds = {fmt_seconds(largest_cpu)}")
    lines.append(f"largest_accelign_score_only_kernel_seconds = {fmt_seconds(largest_kernel)}")
    lines.append(f"largest_accelign_score_only_total_seconds = {fmt_seconds(largest_total)}")
    lines.append(f"query_reuse_active = {largest_query_reuse}")
    lines.append("```")
    lines.append("")
    lines.append("## Boundaries")
    lines.append("")
    lines.append("```text")
    lines.append("use Accelign result for output: no")
    lines.append("use Accelign endpoints: no")
    lines.append("skip CPU aligner.Align: no")
    lines.append("CIGAR/alignment-string reconstruction: no")
    lines.append("scoring/threshold/non-overlap change: no")
    lines.append("GPU DP column AUTO policy change: no")
    lines.append("validation relaxation: no")
    lines.append("mandatory Accelign dependency: no")
    lines.append("```")

    report = "\n".join(lines)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report + "\n", encoding="utf-8")
    return report


def render_score_precheck_report(
    *,
    workload: WorkloadSpec,
    results: Dict[str, List[RunResult]],
    sample_sizes: List[int],
    repeat: int,
    output_path: Path,
) -> str:
    precheck_modes = [f"accelign_score_precheck_{sample_label(size)}" for size in sample_sizes]
    lines: List[str] = []
    lines.append("# Fasim Accelign Score-Only Precheck Shadow")
    lines.append("")
    lines.append(
        "This report characterizes a default-off Accelign score-only precheck "
        "shadow. CPU `aligner.Align` remains the runtime authority and still "
        "runs for every request; Accelign scores are used only after the fact "
        "to simulate a per-align-call score gate."
    )
    lines.append("")
    lines.append(
        "The simulated reject is call-scoped: `Accelign score < scoreInfo.score` "
        "means that individual CPU Align call could not satisfy the immediate "
        "`alignment.sw_score >= scoreInfo.score` break condition. This is not "
        "a candidate/output-level skip proof because later cut lengths, CIGAR, "
        "traceback, NT checks, and final non-overlap still remain CPU-owned."
    )
    lines.append("")
    lines.append(f"Workload: `{workload.label}`. Each mode uses {repeat} run(s); tables report medians.")
    lines.append("")

    rows: List[List[str]] = []
    for size in sample_sizes:
        mode = f"accelign_score_precheck_{sample_label(size)}"
        requests = mode_count(results, mode, "fasim_accelign_score_precheck_requests")
        compared = mode_count(results, mode, "fasim_accelign_score_precheck_requests_compared")
        cpu_seconds = mode_metric(results, mode, "fasim_accelign_score_precheck_cpu_seconds")
        kernel_seconds = mode_metric(results, mode, "fasim_accelign_score_precheck_kernel_seconds")
        accelign_seconds = mode_metric(results, mode, "fasim_accelign_score_precheck_accelign_seconds")
        saved_seconds = mode_metric(results, mode, "fasim_accelign_score_precheck_est_cpu_align_seconds_saved")
        net_seconds = mode_metric(results, mode, "fasim_accelign_score_precheck_net_est_seconds_saved")
        rows.append(
            [
                sample_label(size),
                fmt_int(requests),
                fmt_int(compared),
                fmt_int(mode_count(results, mode, "fasim_accelign_score_precheck_requests_unsupported")),
                fmt_seconds(cpu_seconds),
                fmt_seconds(kernel_seconds),
                fmt_seconds(accelign_seconds),
                fmt_int(mode_count(results, mode, "fasim_accelign_score_precheck_predicted_reject")),
                fmt_int(mode_count(results, mode, "fasim_accelign_score_precheck_true_reject")),
                fmt_int(mode_count(results, mode, "fasim_accelign_score_precheck_false_reject")),
                fmt_int(mode_count(results, mode, "fasim_accelign_score_precheck_false_keep")),
                fmt_int(mode_count(results, mode, "fasim_accelign_score_precheck_est_cpu_align_calls_saved")),
                fmt_seconds(saved_seconds),
                fmt_seconds(net_seconds),
                fmt_speedup(speedup(cpu_seconds, accelign_seconds)),
            ]
        )
    lines.append("## Score-Gate Simulation")
    lines.append("")
    append_table(
        lines,
        [
            "Sample cap",
            "Requests",
            "Compared",
            "Unsupported",
            "CPU reference seconds",
            "Accelign kernel seconds",
            "Accelign total seconds",
            "Predicted reject calls",
            "True reject calls",
            "False reject calls",
            "False keep calls",
            "Estimated CPU calls saved",
            "Estimated CPU seconds saved",
            "Net estimated seconds saved",
            "Accelign vs CPU speedup",
        ],
        rows,
    )
    lines.append("")

    contract_rows: List[List[str]] = []
    for size in sample_sizes:
        mode = f"accelign_score_precheck_{sample_label(size)}"
        contract_rows.append(
            [
                sample_label(size),
                fmt_int(mode_count(results, mode, "fasim_accelign_score_precheck_score_mismatches")),
                str(mode_count(results, mode, "fasim_accelign_score_precheck_has_endpoint_contract")),
                str(mode_count(results, mode, "fasim_accelign_score_precheck_uses_runtime_output")),
                str(mode_count(results, mode, "fasim_accelign_score_precheck_query_reuse_active")),
            ]
        )
    lines.append("## Contract")
    lines.append("")
    append_table(
        lines,
        [
            "Sample cap",
            "Score mismatches",
            "Endpoint contract",
            "Uses runtime output",
            "Query reuse active",
        ],
        contract_rows,
    )
    lines.append("")

    staging_rows: List[List[str]] = []
    for size in sample_sizes:
        mode = f"accelign_score_precheck_{sample_label(size)}"
        h2d = mode_count(results, mode, "fasim_accelign_score_precheck_h2d_bytes")
        d2h = mode_count(results, mode, "fasim_accelign_score_precheck_d2h_bytes")
        query_bytes = mode_count(results, mode, "fasim_accelign_score_precheck_query_staging_bytes")
        target_bytes = mode_count(results, mode, "fasim_accelign_score_precheck_target_staging_bytes")
        staging_rows.append(
            [
                sample_label(size),
                fmt_int(h2d),
                fmt_int(d2h),
                fmt_int(query_bytes),
                fmt_int(target_bytes),
                f"{(query_bytes / h2d * 100.0) if h2d else 0.0:.2f}%",
                f"{(target_bytes / h2d * 100.0) if h2d else 0.0:.2f}%",
            ]
        )
    lines.append("## Staging")
    lines.append("")
    append_table(
        lines,
        [
            "Sample cap",
            "H2D bytes",
            "D2H bytes",
            "Query staging bytes",
            "Target staging bytes",
            "Query share of H2D",
            "Target share of H2D",
        ],
        staging_rows,
    )
    lines.append("")

    largest_mode = precheck_modes[-1]
    largest_score_mismatches = mode_count(
        results, largest_mode, "fasim_accelign_score_precheck_score_mismatches"
    )
    largest_false_reject = mode_count(
        results, largest_mode, "fasim_accelign_score_precheck_false_reject"
    )
    largest_net = mode_metric(
        results, largest_mode, "fasim_accelign_score_precheck_net_est_seconds_saved"
    )
    largest_predicted = mode_count(
        results, largest_mode, "fasim_accelign_score_precheck_predicted_reject"
    )

    lines.append("## Decision")
    lines.append("")
    if largest_score_mismatches != 0:
        lines.append("Accelign score mismatched CPU `aligner.Align`; stop score-precheck work.")
    elif largest_false_reject != 0:
        lines.append(
            "The score-gate simulation produced false rejects. Do not use this "
            "as a rejection precheck; at most investigate score ranking."
        )
    elif largest_net > 0.0 and largest_predicted > 0:
        lines.append(
            "The score-gate simulation is score-clean with zero false rejects "
            "and positive net estimated savings at the largest sample. Next "
            "work can design a default-off real precheck with validation/"
            "fallback, but only for the same call-scoped score gate unless a "
            "separate candidate/output proof is added."
        )
    elif largest_predicted > 0:
        lines.append(
            "The score-gate simulation is score-clean with zero false rejects, "
            "but Accelign overhead exceeds estimated saved CPU Align time. Keep "
            "this as shadow only."
        )
    else:
        lines.append(
            "The score-gate simulation is score-clean but predicts no useful "
            "rejects. Do not build a real precheck from this rule."
        )
    lines.append("")
    lines.append("```text")
    lines.append(f"largest_predicted_reject_calls = {fmt_int(largest_predicted)}")
    lines.append(f"largest_false_reject_calls = {fmt_int(largest_false_reject)}")
    lines.append(f"largest_net_est_seconds_saved = {fmt_seconds(largest_net)}")
    lines.append("```")
    lines.append("")
    lines.append("## Boundaries")
    lines.append("")
    lines.append("```text")
    lines.append("use Accelign result for output: no")
    lines.append("use Accelign endpoints: no")
    lines.append("skip CPU aligner.Align in this PR: no")
    lines.append("claim candidate/output-level filtering: no")
    lines.append("CIGAR/alignment-string reconstruction: no")
    lines.append("scoring/threshold/non-overlap change: no")
    lines.append("GPU DP column AUTO policy change: no")
    lines.append("validation relaxation: no")
    lines.append("mandatory Accelign dependency: no")
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
    parser.add_argument("--sample-sizes", default="1000,10000,50000")
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument(
        "--work-dir",
        default=str(ROOT / ".tmp" / "fasim_aligner_accelign_shadow_scaling"),
    )
    parser.add_argument(
        "--output",
        default=str(ROOT / "docs" / "fasim_aligner_accelign_shadow_scaling.md"),
    )
    parser.add_argument(
        "--score-only-output",
        default=str(ROOT / "docs" / "fasim_accelign_score_only_query_reuse_shadow.md"),
    )
    parser.add_argument(
        "--score-precheck-output",
        default=str(ROOT / "docs" / "fasim_accelign_score_precheck_shadow.md"),
    )
    parser.add_argument("--require-profile", action="store_true")
    parser.add_argument("--check", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.repeat <= 0:
        raise RuntimeError("--repeat must be positive")
    sample_sizes = parse_sample_sizes(args.sample_sizes)

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
    modes = [
        ModeSpec("table_only", "cuda", {"FASIM_TRANSFERSTRING_TABLE": "1"}),
        ModeSpec(
            "auto",
            "cuda",
            {
                "FASIM_TRANSFERSTRING_TABLE": "1",
                "FASIM_GPU_DP_COLUMN_AUTO": "1",
            },
        ),
    ]
    for size in sample_sizes:
        modes.append(
            ModeSpec(
                f"accelign_{sample_label(size)}",
                "cuda",
                {
                    "FASIM_TRANSFERSTRING_TABLE": "1",
                    "FASIM_GPU_DP_COLUMN_AUTO": "1",
                    "FASIM_GPU_DP_COLUMN_AUTO_MIN_WINDOWS": "1",
                    "FASIM_GPU_DP_COLUMN_AUTO_MIN_CELLS": "1",
                    "FASIM_ALIGNER_ACCELIGN_SHADOW": "1",
                    "FASIM_ALIGNER_ACCELIGN_SHADOW_MAX_REQUESTS": sample_cap(size),
                    "FASIM_ALIGNER_ACCELIGN_SHADOW_REQUEST_STRIDE": "1",
                },
            )
        )
        modes.append(
            ModeSpec(
                f"accelign_score_only_{sample_label(size)}",
                "cuda",
                {
                    "FASIM_TRANSFERSTRING_TABLE": "1",
                    "FASIM_GPU_DP_COLUMN_AUTO": "1",
                    "FASIM_GPU_DP_COLUMN_AUTO_MIN_WINDOWS": "1",
                    "FASIM_GPU_DP_COLUMN_AUTO_MIN_CELLS": "1",
                    "FASIM_ALIGNER_ACCELIGN_SCORE_ONLY_SHADOW": "1",
                    "FASIM_ALIGNER_ACCELIGN_SCORE_ONLY_SHADOW_MAX_REQUESTS": sample_cap(size),
                    "FASIM_ALIGNER_ACCELIGN_SCORE_ONLY_SHADOW_REQUEST_STRIDE": "1",
                },
            )
        )
        modes.append(
            ModeSpec(
                f"accelign_score_precheck_{sample_label(size)}",
                "cuda",
                {
                    "FASIM_TRANSFERSTRING_TABLE": "1",
                    "FASIM_GPU_DP_COLUMN_AUTO": "1",
                    "FASIM_GPU_DP_COLUMN_AUTO_MIN_WINDOWS": "1",
                    "FASIM_GPU_DP_COLUMN_AUTO_MIN_CELLS": "1",
                    "FASIM_ALIGNER_ACCELIGN_SCORE_PRECHECK_SHADOW": "1",
                    "FASIM_ALIGNER_ACCELIGN_SCORE_PRECHECK_SHADOW_MAX_REQUESTS": sample_cap(size),
                    "FASIM_ALIGNER_ACCELIGN_SCORE_PRECHECK_SHADOW_REQUEST_STRIDE": "1",
                },
            )
        )

    results: Dict[str, List[RunResult]] = {}
    work_dir = Path(args.work_dir)
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

    shadow_modes = [f"accelign_{sample_label(size)}" for size in sample_sizes]
    score_only_modes = [f"accelign_score_only_{sample_label(size)}" for size in sample_sizes]
    score_precheck_modes = [f"accelign_score_precheck_{sample_label(size)}" for size in sample_sizes]
    require_scaling_metrics(results, shadow_modes)
    require_score_only_metrics(results, score_only_modes)
    require_score_precheck_metrics(results, score_precheck_modes)
    report = render_report(
        workload=workload,
        results=results,
        sample_sizes=sample_sizes,
        repeat=args.repeat,
        output_path=Path(args.output),
    )
    render_score_only_report(
        workload=workload,
        results=results,
        sample_sizes=sample_sizes,
        repeat=args.repeat,
        output_path=Path(args.score_only_output),
    )
    render_score_precheck_report(
        workload=workload,
        results=results,
        sample_sizes=sample_sizes,
        repeat=args.repeat,
        output_path=Path(args.score_precheck_output),
    )

    if args.check:
        for mode in ["auto"] + shadow_modes + score_only_modes + score_precheck_modes:
            if not digest_matches_reference(results, mode):
                raise RuntimeError(f"{mode}: digest mismatch vs table_only")
        for mode in shadow_modes:
            if mode_count(results, mode, "fasim_aligner_accelign_shadow_enabled") != 1:
                raise RuntimeError(f"{mode}: Accelign shadow not enabled")
            if mode_count(results, mode, "fasim_aligner_accelign_shadow_supported") != 1:
                raise RuntimeError(f"{mode}: Accelign shadow not supported")
            if mode_count(results, mode, "fasim_aligner_accelign_shadow_uses_runtime_output") != 0:
                raise RuntimeError(f"{mode}: Accelign shadow must not feed output")
            if mode_count(results, mode, "fasim_aligner_accelign_shadow_requests_compared") <= 0:
                raise RuntimeError(f"{mode}: no compared requests")
            if mode_count(results, mode, "fasim_aligner_accelign_shadow_score_mismatches") != 0:
                raise RuntimeError(f"{mode}: Accelign score contract mismatched")
            if mode_count(results, mode, "fasim_aligner_accelign_shadow_has_cigar_contract") != 0:
                raise RuntimeError(f"{mode}: Accelign shadow must not claim CIGAR coverage")
            if mode_count(results, mode, "fasim_aligner_accelign_shadow_has_alignment_string_contract") != 0:
                raise RuntimeError(f"{mode}: Accelign shadow must not claim alignment-string coverage")
        for mode in score_only_modes:
            if mode_count(results, mode, "fasim_accelign_score_only_shadow_enabled") != 1:
                raise RuntimeError(f"{mode}: Accelign score-only shadow not enabled")
            if mode_count(results, mode, "fasim_accelign_score_only_uses_runtime_output") != 0:
                raise RuntimeError(f"{mode}: Accelign score-only shadow must not feed output")
            if mode_count(results, mode, "fasim_accelign_score_only_requests") <= 0:
                raise RuntimeError(f"{mode}: no score-only requests")
            if mode_count(results, mode, "fasim_accelign_score_only_requests_compared") <= 0:
                raise RuntimeError(f"{mode}: no compared score-only requests")
            if mode_count(results, mode, "fasim_accelign_score_only_score_mismatches") != 0:
                raise RuntimeError(f"{mode}: Accelign score-only contract mismatched")
            if mode_count(results, mode, "fasim_accelign_score_only_has_endpoint_contract") != 0:
                raise RuntimeError(f"{mode}: Accelign score-only must not claim endpoint coverage")
        for mode in score_precheck_modes:
            if mode_count(results, mode, "fasim_accelign_score_precheck_shadow_enabled") != 1:
                raise RuntimeError(f"{mode}: Accelign score precheck shadow not enabled")
            if mode_count(results, mode, "fasim_accelign_score_precheck_uses_runtime_output") != 0:
                raise RuntimeError(f"{mode}: Accelign score precheck must not feed output")
            if mode_count(results, mode, "fasim_accelign_score_precheck_requests") <= 0:
                raise RuntimeError(f"{mode}: no score precheck requests")
            if mode_count(results, mode, "fasim_accelign_score_precheck_requests_compared") <= 0:
                raise RuntimeError(f"{mode}: no compared score precheck requests")
            if mode_count(results, mode, "fasim_accelign_score_precheck_score_mismatches") != 0:
                raise RuntimeError(f"{mode}: Accelign score precheck contract mismatched")
            if mode_count(results, mode, "fasim_accelign_score_precheck_has_endpoint_contract") != 0:
                raise RuntimeError(f"{mode}: Accelign score precheck must not claim endpoint coverage")
            if mode_count(results, mode, "fasim_accelign_score_precheck_false_reject") != 0:
                raise RuntimeError(f"{mode}: Accelign score precheck false-rejected a CPU score-pass call")
            saved_seconds = mode_metric(
                results, mode, "fasim_accelign_score_precheck_est_cpu_align_seconds_saved"
            )
            accelign_seconds = mode_metric(
                results, mode, "fasim_accelign_score_precheck_accelign_seconds"
            )
            net_seconds = mode_metric(
                results, mode, "fasim_accelign_score_precheck_net_est_seconds_saved"
            )
            if abs(net_seconds - (saved_seconds - accelign_seconds)) > 0.000001:
                raise RuntimeError(f"{mode}: net estimate does not equal saved CPU seconds minus Accelign seconds")

    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
