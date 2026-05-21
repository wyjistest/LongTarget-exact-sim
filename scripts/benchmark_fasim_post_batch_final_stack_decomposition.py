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

from benchmark_fasim_aligner_align_decomposition import ALIGN_KEYS  # noqa: E402
from benchmark_fasim_fastSIM_extend_emit_decomposition import FASTSIM_KEYS  # noqa: E402
from benchmark_fasim_gpu_dp_column_characterization import (  # noqa: E402
    GPU_KEYS,
    ModeSpec,
    RunResult,
    STAGE_KEYS,
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
from benchmark_fasim_gpu_dp_column_emit_scoreinfo_decomposition import (  # noqa: E402
    DECOMPOSITION_KEYS as GPU_EMIT_KEYS,
)
from benchmark_fasim_ssw_align_internal_decomposition import (  # noqa: E402
    DECOMPOSITION_KEYS as SSW_INTERNAL_KEYS,
    PROFILE_CACHE_KEYS,
)
from benchmark_fasim_ssw_avx2_hybrid_modes import AVX2_KEYS  # noqa: E402
from benchmark_fasim_ssw_profile_context import PROFILE_CONTEXT_KEYS  # noqa: E402


POST_BATCH_STACK_ENV = {
    "FASIM_TRANSFERSTRING_TABLE": "1",
    "FASIM_GPU_DP_COLUMN_AUTO": "1",
    "FASIM_SSW_PROFILE_CACHE": "1",
    "FASIM_EXACT_COLUMN_EXTEND_BATCH": "1",
    "FASIM_SSW_AVX2": "1",
    "FASIM_SSW_PROFILE_CONTEXT": "1",
    "FASIM_ALIGNER_ALIGN_INTERNALS": "1",
}

BATCH_KEYS = [
    "fasim_exact_column_batch_requested",
    "fasim_exact_column_batch_active",
    "fasim_exact_column_batch_supported",
    "fasim_exact_column_batch_disabled_reason",
    "fasim_exact_column_batch_validate_enabled",
    "fasim_exact_column_batch_requests",
    "fasim_exact_column_batch_cells",
    "fasim_exact_column_batch_max_cells_per_request",
    "fasim_exact_column_batch_pack_seconds",
    "fasim_exact_column_batch_h2d_seconds",
    "fasim_exact_column_batch_kernel_seconds",
    "fasim_exact_column_batch_d2h_seconds",
    "fasim_exact_column_batch_unpack_seconds",
    "fasim_exact_column_batch_apply_seconds",
    "fasim_exact_column_batch_total_seconds",
    "fasim_exact_column_batch_cpu_fallback_seconds",
    "fasim_exact_column_batch_validate_seconds",
    "fasim_exact_column_batch_score_mismatches",
    "fasim_exact_column_batch_endpoint_mismatches",
    "fasim_exact_column_batch_scoreinfo_mismatches",
    "fasim_exact_column_batch_digest_mismatches",
    "fasim_exact_column_batch_fallbacks",
]


def mode_metric(results: Dict[str, List[RunResult]], mode: str, key: str) -> float:
    return median_metric(results[mode], key)


def mode_count(results: Dict[str, List[RunResult]], mode: str, key: str) -> int:
    return median_count(results[mode], key)


def percent(numerator: float, denominator: float) -> str:
    if denominator <= 0.0:
        return "n/a"
    return f"{100.0 * numerator / denominator:.2f}%"


def digest_matches_reference(results: Dict[str, List[RunResult]], mode: str) -> bool:
    return stable_digest(results[mode]) == stable_digest(results["table_only"])


def records_match_reference(results: Dict[str, List[RunResult]], mode: str) -> bool:
    return stable_records(results[mode]) == stable_records(results["table_only"])


def make_modes(force_auto: bool) -> List[ModeSpec]:
    final_env = dict(POST_BATCH_STACK_ENV)
    if force_auto:
        final_env["FASIM_GPU_DP_COLUMN_AUTO_MIN_WINDOWS"] = "1"
        final_env["FASIM_GPU_DP_COLUMN_AUTO_MIN_CELLS"] = "1"
    return [
        ModeSpec("table_only", "avx2", {"FASIM_TRANSFERSTRING_TABLE": "1"}),
        ModeSpec("final_stack", "avx2", final_env),
    ]


def require_metrics(results: Dict[str, List[RunResult]]) -> None:
    keys = (
        STAGE_KEYS
        + GPU_KEYS
        + GPU_EMIT_KEYS
        + FASTSIM_KEYS
        + ALIGN_KEYS
        + SSW_INTERNAL_KEYS
        + PROFILE_CACHE_KEYS
        + AVX2_KEYS
        + PROFILE_CONTEXT_KEYS
        + BATCH_KEYS
    )
    for key in keys:
        mode_metric(results, "final_stack", key)


def check_final_stack(results: Dict[str, List[RunResult]]) -> None:
    require_metrics(results)
    if not digest_matches_reference(results, "final_stack"):
        raise RuntimeError("final stack digest does not match table_only")
    if not records_match_reference(results, "final_stack"):
        raise RuntimeError("final stack record count does not match table_only")
    if mode_count(results, "final_stack", "fasim_gpu_dp_column_auto_active") != 1:
        raise RuntimeError("GPU DP column AUTO was not active")
    if mode_count(results, "final_stack", "fasim_gpu_dp_column_active") != 1:
        raise RuntimeError("GPU DP column path was not active")
    if mode_count(results, "final_stack", "fasim_ssw_profile_cache_active") != 1:
        raise RuntimeError("SSW profile cache was not active")
    if mode_count(results, "final_stack", "fasim_ssw_profile_context_active") != 1:
        raise RuntimeError("SSW ProfileContext was not active")
    if mode_count(results, "final_stack", "fasim_ssw_avx2_active") != 1:
        raise RuntimeError("SSW AVX2 was not active")
    if mode_count(results, "final_stack", "fasim_ssw_avx2_mode") != 2:
        raise RuntimeError("SSW AVX2 mode was not forward_only")
    if mode_count(results, "final_stack", "fasim_ssw_avx2_forward_calls") <= 0:
        raise RuntimeError("SSW AVX2 recorded no forward calls")
    if mode_count(results, "final_stack", "fasim_ssw_avx2_reverse_calls") != 0:
        raise RuntimeError("SSW AVX2 unexpectedly recorded reverse calls")
    if mode_count(results, "final_stack", "fasim_exact_column_batch_requested") != 1:
        raise RuntimeError("exact-column batch was not requested")
    if mode_count(results, "final_stack", "fasim_exact_column_batch_active") != 1:
        raise RuntimeError("exact-column batch was not active")
    if mode_count(results, "final_stack", "fasim_exact_column_batch_supported") != 1:
        raise RuntimeError("exact-column batch was not supported")
    if mode_count(results, "final_stack", "fasim_exact_column_batch_requests") <= 0:
        raise RuntimeError("exact-column batch recorded no requests")
    for key in [
        "fasim_gpu_dp_column_fallbacks",
        "fasim_exact_column_batch_fallbacks",
        "fasim_exact_column_batch_score_mismatches",
        "fasim_exact_column_batch_endpoint_mismatches",
        "fasim_exact_column_batch_scoreinfo_mismatches",
        "fasim_exact_column_batch_digest_mismatches",
        "fasim_ssw_profile_cache_fallbacks",
        "fasim_ssw_profile_context_fallbacks",
        "fasim_ssw_avx2_fallback_calls",
        "fasim_ssw_fallback_calls",
        "fasim_ssw_profile_cache_score_mismatches",
        "fasim_ssw_profile_cache_endpoint_mismatches",
        "fasim_ssw_profile_cache_cigar_mismatches",
        "fasim_ssw_profile_cache_digest_mismatches",
        "fasim_ssw_profile_context_score_mismatches",
        "fasim_ssw_profile_context_endpoint_mismatches",
        "fasim_ssw_profile_context_cigar_mismatches",
        "fasim_ssw_profile_context_digest_mismatches",
    ]:
        if mode_count(results, "final_stack", key) != 0:
            raise RuntimeError(f"non-zero {key}")


def row(
    results: Dict[str, List[RunResult]],
    *,
    component: str,
    key: str,
    percent_total_key: str,
    calls: str,
    scope: str,
    notes: str,
) -> List[str]:
    seconds = mode_metric(results, "final_stack", key)
    total = mode_metric(results, "final_stack", percent_total_key)
    return [component, fmt_seconds(seconds), percent(seconds, total), calls, scope, notes]


def fmt_digest_match(results: Dict[str, List[RunResult]], mode: str) -> str:
    return "yes" if digest_matches_reference(results, mode) else "no"


def render_report(
    *,
    workload: WorkloadSpec,
    results: Dict[str, List[RunResult]],
    repeat: int,
    output_path: Path,
) -> str:
    lines: List[str] = []
    lines.append("# Fasim Post-Batch Final Stack Decomposition")
    lines.append("")
    lines.append(
        "This telemetry-only report decomposes the post-batch Fasim speed stack "
        "after `FASIM_EXACT_COLUMN_EXTEND_BATCH=1` removed the previous "
        "exact-column extend bottleneck. It does not add optimization logic or "
        "change output, scoring, threshold, non-overlap, GPU AUTO, SSW, "
        "SIM-close, recovery, or validation behavior."
    )
    lines.append("")
    lines.append("Post-batch stack:")
    lines.append("")
    lines.append("```bash")
    for key, value in POST_BATCH_STACK_ENV.items():
        if key != "FASIM_ALIGNER_ALIGN_INTERNALS":
            lines.append(f"{key}={value}")
    lines.append("```")
    lines.append("")
    lines.append("`FASIM_ALIGNER_ALIGN_INTERNALS=1` is enabled only to collect decomposition telemetry.")
    lines.append("")
    lines.append(f"Workload: `{workload.label}`. Each mode uses {repeat} run(s); tables report medians.")
    lines.append("")

    table_total = mode_metric(results, "table_only", "fasim_total_seconds")
    final_total = mode_metric(results, "final_stack", "fasim_total_seconds")
    records = stable_records(results["final_stack"])
    digest = stable_digest(results["final_stack"])
    lines.append("## Performance")
    lines.append("")
    append_table(
        lines,
        ["Mode", "Total seconds", "Speedup vs table-only", "Records", "Digest", "Digest match"],
        [
            [
                "table_only",
                fmt_seconds(table_total),
                "1.00x",
                fmt_int(stable_records(results["table_only"])),
                "`" + stable_digest(results["table_only"]) + "`",
                "yes",
            ],
            [
                "final_stack",
                fmt_seconds(final_total),
                fmt_speedup(speedup(table_total, final_total)),
                fmt_int(records),
                "`" + digest + "`",
                fmt_digest_match(results, "final_stack"),
            ],
        ],
    )
    lines.append("")

    lines.append("## Activation And Exactness")
    lines.append("")
    append_table(
        lines,
        [
            "Area",
            "Active / mode",
            "Calls / records",
            "Hits",
            "Misses",
            "Fallbacks",
            "Mismatches",
        ],
        [
            [
                "GPU AUTO",
                fmt_int(mode_count(results, "final_stack", "fasim_gpu_dp_column_auto_active")),
                fmt_int(mode_count(results, "final_stack", "fasim_gpu_dp_column_calls")),
                "n/a",
                "n/a",
                fmt_int(mode_count(results, "final_stack", "fasim_gpu_dp_column_fallbacks")),
                (
                    "score="
                    + fmt_int(mode_count(results, "final_stack", "fasim_gpu_dp_column_score_mismatches"))
                    + ", column="
                    + fmt_int(mode_count(results, "final_stack", "fasim_gpu_dp_column_column_max_mismatches"))
                ),
            ],
            [
                "exact-column batch",
                fmt_int(mode_count(results, "final_stack", "fasim_exact_column_batch_active")),
                fmt_int(mode_count(results, "final_stack", "fasim_exact_column_batch_requests")),
                "n/a",
                "n/a",
                fmt_int(mode_count(results, "final_stack", "fasim_exact_column_batch_fallbacks")),
                (
                    "score="
                    + fmt_int(mode_count(results, "final_stack", "fasim_exact_column_batch_score_mismatches"))
                    + ", endpoint="
                    + fmt_int(mode_count(results, "final_stack", "fasim_exact_column_batch_endpoint_mismatches"))
                    + ", scoreInfo="
                    + fmt_int(mode_count(results, "final_stack", "fasim_exact_column_batch_scoreinfo_mismatches"))
                    + ", digest="
                    + fmt_int(mode_count(results, "final_stack", "fasim_exact_column_batch_digest_mismatches"))
                ),
            ],
            [
                "AVX2",
                "mode=" + fmt_int(mode_count(results, "final_stack", "fasim_ssw_avx2_mode")),
                (
                    "forward="
                    + fmt_int(mode_count(results, "final_stack", "fasim_ssw_avx2_forward_calls"))
                    + ", reverse="
                    + fmt_int(mode_count(results, "final_stack", "fasim_ssw_avx2_reverse_calls"))
                ),
                "n/a",
                "n/a",
                fmt_int(mode_count(results, "final_stack", "fasim_ssw_avx2_fallback_calls")),
                "n/a",
            ],
            [
                "SSW profile cache",
                fmt_int(mode_count(results, "final_stack", "fasim_ssw_profile_cache_active")),
                fmt_int(mode_count(results, "final_stack", "fasim_ssw_profile_cache_calls")),
                fmt_int(mode_count(results, "final_stack", "fasim_ssw_profile_cache_hits")),
                fmt_int(mode_count(results, "final_stack", "fasim_ssw_profile_cache_misses")),
                fmt_int(mode_count(results, "final_stack", "fasim_ssw_profile_cache_fallbacks")),
                (
                    "score="
                    + fmt_int(mode_count(results, "final_stack", "fasim_ssw_profile_cache_score_mismatches"))
                    + ", endpoint="
                    + fmt_int(mode_count(results, "final_stack", "fasim_ssw_profile_cache_endpoint_mismatches"))
                    + ", cigar="
                    + fmt_int(mode_count(results, "final_stack", "fasim_ssw_profile_cache_cigar_mismatches"))
                    + ", digest="
                    + fmt_int(mode_count(results, "final_stack", "fasim_ssw_profile_cache_digest_mismatches"))
                ),
            ],
            [
                "ProfileContext",
                fmt_int(mode_count(results, "final_stack", "fasim_ssw_profile_context_active")),
                fmt_int(mode_count(results, "final_stack", "fasim_ssw_profile_context_calls")),
                fmt_int(mode_count(results, "final_stack", "fasim_ssw_profile_context_hits")),
                fmt_int(mode_count(results, "final_stack", "fasim_ssw_profile_context_misses")),
                fmt_int(mode_count(results, "final_stack", "fasim_ssw_profile_context_fallbacks")),
                (
                    "score="
                    + fmt_int(mode_count(results, "final_stack", "fasim_ssw_profile_context_score_mismatches"))
                    + ", endpoint="
                    + fmt_int(mode_count(results, "final_stack", "fasim_ssw_profile_context_endpoint_mismatches"))
                    + ", cigar="
                    + fmt_int(mode_count(results, "final_stack", "fasim_ssw_profile_context_cigar_mismatches"))
                    + ", digest="
                    + fmt_int(mode_count(results, "final_stack", "fasim_ssw_profile_context_digest_mismatches"))
                ),
            ],
        ],
    )
    lines.append("")
    lines.append(
        "Note: with ProfileContext active, the profile cache still backs the "
        "context, but the per-call hot reuse is represented by ProfileContext "
        "hit/miss counters. The remaining SSW profile cache miss is the initial "
        "profile build."
    )
    lines.append("")

    lines.append("## Top-Level Stages")
    lines.append("")
    append_table(
        lines,
        ["Component", "Seconds", "Percent of total", "Calls / bytes", "Scope", "Notes"],
        [
            row(
                results,
                component="window generation",
                key="fasim_window_generation_seconds",
                percent_total_key="fasim_total_seconds",
                calls=fmt_int(mode_count(results, "final_stack", "fasim_num_windows")),
                scope="top-level",
                notes="cutSequence, transferString, source transform, encoded target build",
            ),
            row(
                results,
                component="GPU DP column total",
                key="fasim_gpu_dp_column_total_seconds",
                percent_total_key="fasim_total_seconds",
                calls=fmt_int(mode_count(results, "final_stack", "fasim_gpu_dp_column_calls")),
                scope="inclusive",
                notes="GPU DP+column path wall time including compact transfer and CPU postprocessing envelope",
            ),
            row(
                results,
                component="GPU kernel",
                key="fasim_gpu_dp_column_kernel_seconds",
                percent_total_key="fasim_total_seconds",
                calls=fmt_int(mode_count(results, "final_stack", "fasim_gpu_dp_column_windows")),
                scope="nested",
                notes="device DP+column kernel work inside GPU DP column total",
            ),
            row(
                results,
                component="GPU scoreInfo reconstruct",
                key="fasim_gpu_dp_column_scoreinfo_reconstruct_seconds",
                percent_total_key="fasim_total_seconds",
                calls=fmt_int(mode_count(results, "final_stack", "fasim_gpu_dp_column_scoreinfo_reconstruct_records")),
                scope="post-GPU",
                notes="CPU reconstruction of compact GPU scoreInfo records",
            ),
            row(
                results,
                component="exact-column extend stage",
                key="fasim_gpu_dp_column_exact_column_extend_seconds",
                percent_total_key="fasim_total_seconds",
                calls=fmt_int(mode_count(results, "final_stack", "fasim_gpu_dp_column_exact_extend_windows")),
                scope="post-GPU",
                notes="exact-column extend stage timer; equals the batch backend envelope when batch path is active",
            ),
            row(
                results,
                component="exact-column batch total",
                key="fasim_exact_column_batch_total_seconds",
                percent_total_key="fasim_total_seconds",
                calls=fmt_int(mode_count(results, "final_stack", "fasim_exact_column_batch_requests")),
                scope="post-GPU",
                notes="real batched exact-column extend path, including pack/transfer/kernel/unpack/apply",
            ),
            row(
                results,
                component="exact-column batch kernel",
                key="fasim_exact_column_batch_kernel_seconds",
                percent_total_key="fasim_total_seconds",
                calls=fmt_int(mode_count(results, "final_stack", "fasim_exact_column_batch_cells")),
                scope="nested",
                notes="device exact-column extend kernel inside batch total",
            ),
            row(
                results,
                component="fastSIM emit wrapper",
                key="fasim_gpu_dp_column_emit_seconds",
                percent_total_key="fasim_total_seconds",
                calls=fmt_int(mode_count(results, "final_stack", "fasim_gpu_dp_column_cpu_emit_records")),
                scope="post-GPU",
                notes="CPU emit / extension wrapper for scoreInfo-derived candidates",
            ),
            row(
                results,
                component="non-overlap",
                key="fasim_nonoverlap_seconds",
                percent_total_key="fasim_total_seconds",
                calls="n/a",
                scope="top-level",
                notes="final overlap pruning stage",
            ),
            row(
                results,
                component="caller output",
                key="fasim_output_seconds",
                percent_total_key="fasim_total_seconds",
                calls=fmt_int(records),
                scope="top-level",
                notes="caller-side output formatting/write outside fastSIM record construction",
            ),
        ],
    )
    lines.append("")
    lines.append("H2D bytes: `" + fmt_int(mode_count(results, "final_stack", "fasim_gpu_dp_column_h2d_bytes")) + "`")
    lines.append("D2H bytes: `" + fmt_int(mode_count(results, "final_stack", "fasim_gpu_dp_column_d2h_bytes")) + "`")
    lines.append("")

    lines.append("## Exact-Column Batch Breakdown")
    lines.append("")
    append_table(
        lines,
        ["Component", "Seconds", "Percent of total", "Requests / cells", "Notes"],
        [
            [
                "batch total",
                fmt_seconds(mode_metric(results, "final_stack", "fasim_exact_column_batch_total_seconds")),
                percent(mode_metric(results, "final_stack", "fasim_exact_column_batch_total_seconds"), final_total),
                fmt_int(mode_count(results, "final_stack", "fasim_exact_column_batch_requests")),
                "inclusive pack, transfer, kernel, unpack, and apply time",
            ],
            [
                "pack",
                fmt_seconds(mode_metric(results, "final_stack", "fasim_exact_column_batch_pack_seconds")),
                percent(mode_metric(results, "final_stack", "fasim_exact_column_batch_pack_seconds"), final_total),
                fmt_int(mode_count(results, "final_stack", "fasim_exact_column_batch_requests")),
                "host request packing",
            ],
            [
                "H2D",
                fmt_seconds(mode_metric(results, "final_stack", "fasim_exact_column_batch_h2d_seconds")),
                percent(mode_metric(results, "final_stack", "fasim_exact_column_batch_h2d_seconds"), final_total),
                "n/a",
                "host-to-device transfer",
            ],
            [
                "kernel",
                fmt_seconds(mode_metric(results, "final_stack", "fasim_exact_column_batch_kernel_seconds")),
                percent(mode_metric(results, "final_stack", "fasim_exact_column_batch_kernel_seconds"), final_total),
                fmt_int(mode_count(results, "final_stack", "fasim_exact_column_batch_cells")),
                "device batched exact-column work",
            ],
            [
                "D2H",
                fmt_seconds(mode_metric(results, "final_stack", "fasim_exact_column_batch_d2h_seconds")),
                percent(mode_metric(results, "final_stack", "fasim_exact_column_batch_d2h_seconds"), final_total),
                "n/a",
                "device-to-host transfer",
            ],
            [
                "unpack",
                fmt_seconds(mode_metric(results, "final_stack", "fasim_exact_column_batch_unpack_seconds")),
                percent(mode_metric(results, "final_stack", "fasim_exact_column_batch_unpack_seconds"), final_total),
                fmt_int(mode_count(results, "final_stack", "fasim_exact_column_batch_requests")),
                "host result unpacking",
            ],
            [
                "apply",
                fmt_seconds(mode_metric(results, "final_stack", "fasim_exact_column_batch_apply_seconds")),
                percent(mode_metric(results, "final_stack", "fasim_exact_column_batch_apply_seconds"), final_total),
                fmt_int(mode_count(results, "final_stack", "fasim_exact_column_batch_requests")),
                "feeding batch results into the existing downstream path",
            ],
        ],
    )
    lines.append("")
    lines.append("Batch cells: `" + fmt_int(mode_count(results, "final_stack", "fasim_exact_column_batch_cells")) + "`")
    lines.append(
        "Max cells/request: `"
        + fmt_int(mode_count(results, "final_stack", "fasim_exact_column_batch_max_cells_per_request"))
        + "`"
    )
    lines.append("")

    align_seconds = mode_metric(results, "final_stack", "fasim_aligner_align_seconds")
    ssw_seconds = mode_metric(results, "final_stack", "fasim_ssw_align_seconds")
    align_calls = mode_count(results, "final_stack", "fasim_aligner_align_calls")
    lines.append("## CPU Emit And Align Decomposition")
    lines.append("")
    append_table(
        lines,
        ["Component", "Seconds", "Percent", "Calls", "Scope", "Notes"],
        [
            [
                "fastSIM inclusive",
                fmt_seconds(mode_metric(results, "final_stack", "fasim_fastSIM_extend_inclusive_seconds")),
                percent(mode_metric(results, "final_stack", "fasim_fastSIM_extend_inclusive_seconds"), final_total),
                fmt_int(mode_count(results, "final_stack", "fasim_fastSIM_extend_calls")),
                "wrapper",
                "full `fastSIM_extend_from_scoreinfo` inclusive time, shown as percent of total",
            ],
            [
                "fastSIM alignment reconstruction",
                fmt_seconds(mode_metric(results, "final_stack", "fasim_fastSIM_extend_alignment_reconstruct_seconds")),
                percent(mode_metric(results, "final_stack", "fasim_fastSIM_extend_alignment_reconstruct_seconds"), final_total),
                fmt_int(align_calls),
                "nested",
                "`aligner.Align` over scoreInfo-derived local windows, shown as percent of total",
            ],
            [
                "fastSIM record build",
                fmt_seconds(mode_metric(results, "final_stack", "fasim_fastSIM_extend_record_build_seconds")),
                percent(mode_metric(results, "final_stack", "fasim_fastSIM_extend_record_build_seconds"), final_total),
                fmt_int(mode_count(results, "final_stack", "fasim_fastSIM_extend_records_emitted")),
                "exclusive",
                "record construction, convertMyTriplex, CIGAR traversal, identity/stability work",
            ],
            [
                "aligner.Align",
                fmt_seconds(align_seconds),
                "100.00%",
                fmt_int(align_calls),
                "wrapper",
                "CPU alignment reconstruction authority",
            ],
            [
                "aligner setup",
                fmt_seconds(mode_metric(results, "final_stack", "fasim_aligner_setup_seconds")),
                percent(mode_metric(results, "final_stack", "fasim_aligner_setup_seconds"), align_seconds),
                fmt_int(align_calls),
                "nested",
                "strlen, allocation, translate, cache/context lookup",
            ],
            [
                "ProfileContext saved estimate",
                fmt_seconds(
                    mode_metric(results, "final_stack", "fasim_ssw_profile_context_query_translate_saved_seconds")
                    + mode_metric(results, "final_stack", "fasim_ssw_profile_context_lookup_saved_seconds")
                ),
                "n/a",
                fmt_int(mode_count(results, "final_stack", "fasim_ssw_profile_context_calls")),
                "telemetry estimate",
                "query translate plus lookup seconds avoided by active ProfileContext",
            ],
            [
                "ssw_align",
                fmt_seconds(ssw_seconds),
                percent(ssw_seconds, align_seconds),
                fmt_int(align_calls),
                "nested",
                "forward score/end, reverse-start, endpoint bookkeeping, and CIGAR section",
            ],
            [
                "forward score/end",
                fmt_seconds(mode_metric(results, "final_stack", "fasim_ssw_forward_score_end_seconds")),
                percent(mode_metric(results, "final_stack", "fasim_ssw_forward_score_end_seconds"), align_seconds),
                fmt_int(mode_count(results, "final_stack", "fasim_ssw_forward_calls")),
                "nested",
                "AVX2 forward-only local score and endpoint search",
            ],
            [
                "reverse-start",
                fmt_seconds(mode_metric(results, "final_stack", "fasim_ssw_reverse_start_seconds")),
                percent(mode_metric(results, "final_stack", "fasim_ssw_reverse_start_seconds"), align_seconds),
                fmt_int(mode_count(results, "final_stack", "fasim_ssw_reverse_calls")),
                "nested",
                "SSE2 reverse substring alignment to recover begin coordinates",
            ],
            [
                "CIGAR section",
                fmt_seconds(mode_metric(results, "final_stack", "fasim_ssw_cigar_seconds")),
                percent(mode_metric(results, "final_stack", "fasim_ssw_cigar_seconds"), align_seconds),
                fmt_int(mode_count(results, "final_stack", "fasim_ssw_banded_sw_calls")),
                "nested inclusive",
                "CIGAR preparation plus banded traceback; includes banded_sw",
            ],
            [
                "banded_sw",
                fmt_seconds(mode_metric(results, "final_stack", "fasim_ssw_banded_sw_seconds")),
                percent(mode_metric(results, "final_stack", "fasim_ssw_banded_sw_seconds"), align_seconds),
                fmt_int(mode_count(results, "final_stack", "fasim_ssw_banded_sw_calls")),
                "nested",
                "traceback DP inside CIGAR section",
            ],
        ],
    )
    lines.append("")
    lines.append(
        "Percent basis follows the row note: fastSIM rows use percent of total "
        "runtime, while `aligner.Align` subrows use percent of `aligner.Align`."
    )
    lines.append("")

    lines.append("## Decision")
    lines.append("")
    candidates = [
        ("forward score/end", mode_metric(results, "final_stack", "fasim_ssw_forward_score_end_seconds")),
        ("reverse-start", mode_metric(results, "final_stack", "fasim_ssw_reverse_start_seconds")),
        ("CIGAR / banded_sw", mode_metric(results, "final_stack", "fasim_ssw_cigar_seconds")),
        ("exact-column batch total", mode_metric(results, "final_stack", "fasim_exact_column_batch_total_seconds")),
        ("record construction", mode_metric(results, "final_stack", "fasim_fastSIM_extend_record_build_seconds")),
        ("GPU kernel", mode_metric(results, "final_stack", "fasim_gpu_dp_column_kernel_seconds")),
        ("setup / ProfileContext", mode_metric(results, "final_stack", "fasim_aligner_setup_seconds")),
        ("fastSIM emit wrapper", mode_metric(results, "final_stack", "fasim_gpu_dp_column_emit_seconds")),
    ]
    winner, winner_seconds = max(candidates, key=lambda item: item[1])
    lines.append(
        f"Largest measured candidate component: `{winner}` at {fmt_seconds(winner_seconds)}s "
        f"({percent(winner_seconds, final_total)} of total)."
    )
    if winner == "forward score/end":
        recommendation = "Consider only shadow-first AVX512 forward-only or deeper AVX2 forward optimization."
    elif winner == "reverse-start":
        recommendation = "Design a reverse-start shortcut/cache shadow before any real-path change."
    elif winner == "CIGAR / banded_sw":
        recommendation = "Design a lazy CIGAR/traceback shadow; CIGAR remains part of the output contract."
    elif winner == "exact-column batch total":
        recommendation = "Exact-column batch remains material; inspect pack/transfer/kernel/unpack before changing runtime."
    elif winner == "fastSIM emit wrapper":
        recommendation = "Decompose CPU emit and alignment reconstruction before any real-path change."
    elif winner == "GPU kernel":
        recommendation = "GPU DP column remains material; do not change AUTO policy without a separate validation PR."
    else:
        recommendation = "Treat the current stack as the speed milestone unless a larger workload shows a sharper bottleneck."
    lines.append(recommendation)
    lines.append("")

    lines.append("## Boundaries")
    lines.append("")
    lines.append("```text")
    lines.append("optimization logic added: no")
    lines.append("default batch enablement change: no")
    lines.append("default AVX2/ProfileContext change: no")
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
    parser.add_argument("--dna", required=True)
    parser.add_argument("--rna", required=True)
    parser.add_argument("--label", default="hg38_chr21_H19")
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--force-auto", action="store_true")
    parser.add_argument(
        "--work-dir",
        default=str(ROOT / ".tmp" / "fasim_post_batch_final_stack_decomposition"),
    )
    parser.add_argument(
        "--output",
        default=str(ROOT / "docs" / "fasim_post_batch_final_stack_decomposition.md"),
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
    modes = make_modes(force_auto=args.force_auto)
    work_dir = Path(args.work_dir)
    if not work_dir.is_absolute():
        work_dir = (ROOT / work_dir).resolve()

    results: Dict[str, List[RunResult]] = {}
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

    if args.check:
        check_final_stack(results)
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
