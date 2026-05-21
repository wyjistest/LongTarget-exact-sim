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
    fmt_speedup,
    median_count,
    median_metric,
    run_once,
    speedup,
    stable_digest,
    stable_records,
)


DECOMPOSITION_KEYS = [
    "fasim_aligner_setup_seconds",
    "fasim_aligner_strlen_seconds",
    "fasim_aligner_query_alloc_seconds",
    "fasim_aligner_query_translate_seconds",
    "fasim_aligner_ref_translate_seconds",
    "fasim_aligner_profile_cache_lookup_seconds",
    "fasim_aligner_profile_cache_hit_seconds",
    "fasim_aligner_profile_cache_miss_seconds",
    "fasim_ssw_align_seconds",
    "fasim_ssw_forward_score_end_seconds",
    "fasim_ssw_reverse_start_seconds",
    "fasim_ssw_banded_sw_seconds",
    "fasim_ssw_cigar_seconds",
    "fasim_ssw_endpoint_bookkeeping_seconds",
    "fasim_ssw_byte_path_seconds",
    "fasim_ssw_word_path_seconds",
    "fasim_ssw_fallback_calls",
    "fasim_ssw_forward_calls",
    "fasim_ssw_reverse_calls",
    "fasim_ssw_banded_sw_calls",
]

PROFILE_CACHE_KEYS = [
    "fasim_ssw_profile_cache_active",
    "fasim_ssw_profile_cache_calls",
    "fasim_ssw_profile_cache_hits",
    "fasim_ssw_profile_cache_misses",
    "fasim_ssw_profile_cache_unique_keys",
    "fasim_ssw_profile_cache_score_mismatches",
    "fasim_ssw_profile_cache_endpoint_mismatches",
    "fasim_ssw_profile_cache_cigar_mismatches",
    "fasim_ssw_profile_cache_digest_mismatches",
    "fasim_ssw_profile_cache_fallbacks",
]


def mode_metric(results: Dict[str, List[RunResult]], mode: str, key: str) -> float:
    return median_metric(results[mode], key)


def mode_count(results: Dict[str, List[RunResult]], mode: str, key: str) -> int:
    return median_count(results[mode], key)


def digest_matches_reference(results: Dict[str, List[RunResult]], mode: str) -> bool:
    return stable_digest(results[mode]) == stable_digest(results["table_only"])


def percent(numerator: float, denominator: float) -> str:
    if denominator <= 0.0:
        return "n/a"
    return f"{100.0 * numerator / denominator:.2f}%"


def require_metrics(results: Dict[str, List[RunResult]], keys: Iterable[str]) -> None:
    for key in keys:
        mode_metric(results, "auto_cache_decomposition", key)


def render_report(
    *,
    workload: WorkloadSpec,
    results: Dict[str, List[RunResult]],
    repeat: int,
    output_path: Path,
) -> str:
    lines: List[str] = []
    lines.append("# Fasim SSW Align Internal Decomposition")
    lines.append("")
    lines.append(
        "This telemetry-only report decomposes the remaining `aligner.Align` setup "
        "and `ssw_align` internals after the current speed stack. It does not add "
        "an optimization, change output, scoring, thresholds, non-overlap behavior, "
        "GPU AUTO policy, SIM-close, recovery, or validation behavior."
    )
    lines.append("")
    lines.append("Measured opt-in stack:")
    lines.append("")
    lines.append("```bash")
    lines.append("FASIM_TRANSFERSTRING_TABLE=1")
    lines.append("FASIM_GPU_DP_COLUMN_AUTO=1")
    lines.append("FASIM_SSW_PROFILE_CACHE=1")
    lines.append("FASIM_ALIGNER_ALIGN_INTERNALS=1")
    lines.append("```")
    lines.append("")
    lines.append(f"Workload: `{workload.label}`. Each mode uses {repeat} run(s); tables report medians.")
    lines.append("")

    table_total = mode_metric(results, "table_only", "fasim_total_seconds")
    auto_total = mode_metric(results, "auto_cache_decomposition", "fasim_total_seconds")
    append_table(
        lines,
        ["Mode", "Seconds", "Speedup vs table", "Digest match", "Records"],
        [
            [
                "table_only",
                fmt_seconds(table_total),
                "1.00x",
                "yes",
                str(stable_records(results["table_only"])),
            ],
            [
                "AUTO + cache + decomposition",
                fmt_seconds(auto_total),
                fmt_speedup(speedup(table_total, auto_total)),
                "yes" if digest_matches_reference(results, "auto_cache_decomposition") else "no",
                str(stable_records(results["auto_cache_decomposition"])),
            ],
        ],
    )
    lines.append("")

    align_seconds = mode_metric(results, "auto_cache_decomposition", "fasim_aligner_align_seconds")
    align_calls = mode_count(results, "auto_cache_decomposition", "fasim_aligner_align_calls")
    ssw_seconds = mode_metric(results, "auto_cache_decomposition", "fasim_ssw_align_seconds")
    lines.append("## Required Component Table")
    lines.append("")
    append_table(
        lines,
        ["Component", "Seconds", "Calls", "Percent of aligner", "Notes"],
        [
            [
                "aligner setup",
                fmt_seconds(mode_metric(results, "auto_cache_decomposition", "fasim_aligner_setup_seconds")),
                fmt_int(align_calls),
                percent(mode_metric(results, "auto_cache_decomposition", "fasim_aligner_setup_seconds"), align_seconds),
                "strlen, allocation, query/ref translate, and profile cache lookup/build",
            ],
            [
                "strlen(query)",
                fmt_seconds(mode_metric(results, "auto_cache_decomposition", "fasim_aligner_strlen_seconds")),
                fmt_int(align_calls),
                percent(mode_metric(results, "auto_cache_decomposition", "fasim_aligner_strlen_seconds"), align_seconds),
                "query length discovery",
            ],
            [
                "query allocation",
                fmt_seconds(mode_metric(results, "auto_cache_decomposition", "fasim_aligner_query_alloc_seconds")),
                fmt_int(align_calls),
                percent(mode_metric(results, "auto_cache_decomposition", "fasim_aligner_query_alloc_seconds"), align_seconds),
                "translated query buffer allocation",
            ],
            [
                "query translate",
                fmt_seconds(mode_metric(results, "auto_cache_decomposition", "fasim_aligner_query_translate_seconds")),
                fmt_int(align_calls),
                percent(mode_metric(results, "auto_cache_decomposition", "fasim_aligner_query_translate_seconds"), align_seconds),
                "ASCII bases to SSW alphabet",
            ],
            [
                "ref translate",
                fmt_seconds(mode_metric(results, "auto_cache_decomposition", "fasim_aligner_ref_translate_seconds")),
                fmt_int(align_calls),
                percent(mode_metric(results, "auto_cache_decomposition", "fasim_aligner_ref_translate_seconds"), align_seconds),
                "short target translation",
            ],
            [
                "profile cache lookup",
                fmt_seconds(mode_metric(results, "auto_cache_decomposition", "fasim_aligner_profile_cache_lookup_seconds")),
                fmt_int(mode_count(results, "auto_cache_decomposition", "fasim_ssw_profile_cache_calls")),
                percent(mode_metric(results, "auto_cache_decomposition", "fasim_aligner_profile_cache_lookup_seconds"), align_seconds),
                "exact query/scoring key map lookup, including miss build path",
            ],
            [
                "profile cache hit",
                fmt_seconds(mode_metric(results, "auto_cache_decomposition", "fasim_aligner_profile_cache_hit_seconds")),
                fmt_int(mode_count(results, "auto_cache_decomposition", "fasim_ssw_profile_cache_hits")),
                percent(mode_metric(results, "auto_cache_decomposition", "fasim_aligner_profile_cache_hit_seconds"), align_seconds),
                "hit-only lookup time",
            ],
            [
                "profile cache miss",
                fmt_seconds(mode_metric(results, "auto_cache_decomposition", "fasim_aligner_profile_cache_miss_seconds")),
                fmt_int(mode_count(results, "auto_cache_decomposition", "fasim_ssw_profile_cache_misses")),
                percent(mode_metric(results, "auto_cache_decomposition", "fasim_aligner_profile_cache_miss_seconds"), align_seconds),
                "miss lookup plus profile build insertion",
            ],
            [
                "ssw_align",
                fmt_seconds(ssw_seconds),
                fmt_int(align_calls),
                percent(ssw_seconds, align_seconds),
                "SSW forward, reverse-start, endpoint bookkeeping, and CIGAR section",
            ],
            [
                "forward score/end",
                fmt_seconds(mode_metric(results, "auto_cache_decomposition", "fasim_ssw_forward_score_end_seconds")),
                fmt_int(mode_count(results, "auto_cache_decomposition", "fasim_ssw_forward_calls")),
                percent(mode_metric(results, "auto_cache_decomposition", "fasim_ssw_forward_score_end_seconds"), align_seconds),
                "initial local score and endpoint search",
            ],
            [
                "reverse-start",
                fmt_seconds(mode_metric(results, "auto_cache_decomposition", "fasim_ssw_reverse_start_seconds")),
                fmt_int(mode_count(results, "auto_cache_decomposition", "fasim_ssw_reverse_calls")),
                percent(mode_metric(results, "auto_cache_decomposition", "fasim_ssw_reverse_start_seconds"), align_seconds),
                "reverse substring alignment to recover begin coordinates",
            ],
            [
                "CIGAR section",
                fmt_seconds(mode_metric(results, "auto_cache_decomposition", "fasim_ssw_cigar_seconds")),
                fmt_int(mode_count(results, "auto_cache_decomposition", "fasim_ssw_banded_sw_calls")),
                percent(mode_metric(results, "auto_cache_decomposition", "fasim_ssw_cigar_seconds"), align_seconds),
                "CIGAR preparation plus banded traceback; includes banded_sw below",
            ],
            [
                "banded_sw",
                fmt_seconds(mode_metric(results, "auto_cache_decomposition", "fasim_ssw_banded_sw_seconds")),
                fmt_int(mode_count(results, "auto_cache_decomposition", "fasim_ssw_banded_sw_calls")),
                percent(mode_metric(results, "auto_cache_decomposition", "fasim_ssw_banded_sw_seconds"), align_seconds),
                "nested core traceback DP inside CIGAR section",
            ],
            [
                "endpoint bookkeeping",
                fmt_seconds(mode_metric(results, "auto_cache_decomposition", "fasim_ssw_endpoint_bookkeeping_seconds")),
                fmt_int(align_calls),
                percent(mode_metric(results, "auto_cache_decomposition", "fasim_ssw_endpoint_bookkeeping_seconds"), align_seconds),
                "copy forward/reverse best cells into returned endpoint fields",
            ],
        ],
    )
    lines.append("")

    lines.append("## SIMD Path Mix")
    lines.append("")
    append_table(
        lines,
        ["Path", "Seconds", "Calls", "Percent of ssw_align", "Notes"],
        [
            [
                "byte path",
                fmt_seconds(mode_metric(results, "auto_cache_decomposition", "fasim_ssw_byte_path_seconds")),
                "n/a",
                percent(mode_metric(results, "auto_cache_decomposition", "fasim_ssw_byte_path_seconds"), ssw_seconds),
                "SSE2 byte kernel calls, forward plus reverse when byte path is valid",
            ],
            [
                "word path",
                fmt_seconds(mode_metric(results, "auto_cache_decomposition", "fasim_ssw_word_path_seconds")),
                "n/a",
                percent(mode_metric(results, "auto_cache_decomposition", "fasim_ssw_word_path_seconds"), ssw_seconds),
                "SSE2 word kernel calls, including saturation fallback",
            ],
            [
                "word fallback",
                "n/a",
                fmt_int(mode_count(results, "auto_cache_decomposition", "fasim_ssw_fallback_calls")),
                "n/a",
                "byte score saturated at 255 and retried with word profile",
            ],
        ],
    )
    lines.append("")

    lines.append("## Call Shape And Correctness")
    lines.append("")
    append_table(
        lines,
        [
            "Align calls",
            "Emitted records",
            "Rejected records",
            "Cache hits",
            "Cache misses",
            "Unique keys",
            "Score mismatches",
            "Endpoint mismatches",
            "CIGAR mismatches",
            "Digest mismatches",
            "Fallbacks",
        ],
        [
            [
                fmt_int(align_calls),
                fmt_int(mode_count(results, "auto_cache_decomposition", "fasim_fastSIM_extend_records_emitted")),
                fmt_int(mode_count(results, "auto_cache_decomposition", "fasim_fastSIM_extend_records_rejected")),
                fmt_int(mode_count(results, "auto_cache_decomposition", "fasim_ssw_profile_cache_hits")),
                fmt_int(mode_count(results, "auto_cache_decomposition", "fasim_ssw_profile_cache_misses")),
                fmt_int(mode_count(results, "auto_cache_decomposition", "fasim_ssw_profile_cache_unique_keys")),
                fmt_int(mode_count(results, "auto_cache_decomposition", "fasim_ssw_profile_cache_score_mismatches")),
                fmt_int(mode_count(results, "auto_cache_decomposition", "fasim_ssw_profile_cache_endpoint_mismatches")),
                fmt_int(mode_count(results, "auto_cache_decomposition", "fasim_ssw_profile_cache_cigar_mismatches")),
                fmt_int(mode_count(results, "auto_cache_decomposition", "fasim_ssw_profile_cache_digest_mismatches")),
                fmt_int(mode_count(results, "auto_cache_decomposition", "fasim_ssw_profile_cache_fallbacks")),
            ]
        ],
    )
    lines.append("")

    forward = mode_metric(results, "auto_cache_decomposition", "fasim_ssw_forward_score_end_seconds")
    reverse = mode_metric(results, "auto_cache_decomposition", "fasim_ssw_reverse_start_seconds")
    cigar = mode_metric(results, "auto_cache_decomposition", "fasim_ssw_cigar_seconds")
    setup = mode_metric(results, "auto_cache_decomposition", "fasim_aligner_setup_seconds")
    lines.append("## Decision Guide")
    lines.append("")
    if setup >= align_seconds * 0.10:
        lines.append(
            "Setup remains material. A future `TranslatedQuery/ProfileContext` cache shadow is worth evaluating before "
            "touching traceback semantics."
        )
    elif forward >= ssw_seconds * 0.50:
        lines.append(
            "Forward score/end dominates `ssw_align`. Continue SIMD/Parasail exploration only as exact-clean shadow or "
            "default-off opt-in."
        )
    elif reverse >= ssw_seconds * 0.30:
        lines.append(
            "Reverse-start is material. Future work should focus on reverse-start cache or shortcut shadows."
        )
    elif cigar >= ssw_seconds * 0.30:
        lines.append(
            "CIGAR/traceback is material. Future work should focus on CIGAR reconstruction and traceback cost."
        )
    else:
        lines.append(
            "Costs are distributed. Avoid narrow micro-optimizations unless a larger workload shows a dominant stage."
        )
    lines.append("")

    lines.append("## Boundaries")
    lines.append("")
    lines.append("```text")
    lines.append("real optimization added: no")
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
        default=str(ROOT / ".tmp" / "fasim_ssw_align_internal_decomposition"),
    )
    parser.add_argument(
        "--output",
        default=str(ROOT / "docs" / "fasim_ssw_align_internal_decomposition.md"),
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
    decomposition_env = {
        "FASIM_TRANSFERSTRING_TABLE": "1",
        "FASIM_GPU_DP_COLUMN_AUTO": "1",
        "FASIM_SSW_PROFILE_CACHE": "1",
        "FASIM_ALIGNER_ALIGN_INTERNALS": "1",
    }
    if args.force_auto:
        decomposition_env["FASIM_GPU_DP_COLUMN_AUTO_MIN_WINDOWS"] = "1"
        decomposition_env["FASIM_GPU_DP_COLUMN_AUTO_MIN_CELLS"] = "1"

    modes = [
        ModeSpec("table_only", "cuda", {"FASIM_TRANSFERSTRING_TABLE": "1"}),
        ModeSpec(
            "auto_cache_decomposition",
            "cuda",
            decomposition_env,
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

    require_metrics(results, DECOMPOSITION_KEYS + PROFILE_CACHE_KEYS)
    report = render_report(
        workload=workload,
        results=results,
        repeat=args.repeat,
        output_path=Path(args.output).resolve(),
    )

    if args.check:
        if not digest_matches_reference(results, "auto_cache_decomposition"):
            raise RuntimeError("AUTO+cache decomposition digest does not match table_only")
        if mode_count(results, "auto_cache_decomposition", "fasim_ssw_profile_cache_active") != 1:
            raise RuntimeError("SSW profile cache was not active")
        if mode_count(results, "auto_cache_decomposition", "fasim_aligner_align_calls") <= 0:
            raise RuntimeError("aligner.Align calls were not recorded")
        if mode_count(results, "auto_cache_decomposition", "fasim_ssw_forward_calls") <= 0:
            raise RuntimeError("forward calls were not recorded")
        if mode_count(results, "auto_cache_decomposition", "fasim_ssw_reverse_calls") <= 0:
            raise RuntimeError("reverse calls were not recorded")
        if mode_count(results, "auto_cache_decomposition", "fasim_ssw_banded_sw_calls") <= 0:
            raise RuntimeError("banded_sw calls were not recorded")
        for key in [
            "fasim_ssw_profile_cache_score_mismatches",
            "fasim_ssw_profile_cache_endpoint_mismatches",
            "fasim_ssw_profile_cache_cigar_mismatches",
            "fasim_ssw_profile_cache_digest_mismatches",
            "fasim_ssw_profile_cache_fallbacks",
        ]:
            if mode_count(results, "auto_cache_decomposition", key) != 0:
                raise RuntimeError(f"non-zero {key}")

    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
