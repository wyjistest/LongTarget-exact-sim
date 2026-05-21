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


PROFILE_CONTEXT_KEYS = [
    "fasim_ssw_profile_context_shadow_enabled",
    "fasim_ssw_profile_context_unique_keys",
    "fasim_ssw_profile_context_calls",
    "fasim_ssw_profile_context_reusable_calls",
    "fasim_ssw_profile_context_query_translate_saved_seconds_est",
    "fasim_ssw_profile_context_lookup_saved_seconds_est",
    "fasim_ssw_profile_context_build_seconds",
    "fasim_ssw_profile_context_shadow_compared",
    "fasim_ssw_profile_context_score_mismatches",
    "fasim_ssw_profile_context_endpoint_mismatches",
    "fasim_ssw_profile_context_cigar_mismatches",
    "fasim_ssw_profile_context_digest_mismatches",
    "fasim_aligner_query_translate_seconds",
    "fasim_aligner_profile_cache_lookup_seconds",
    "fasim_aligner_setup_seconds",
    "fasim_aligner_align_seconds",
    "fasim_ssw_profile_cache_active",
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
        mode_metric(results, "auto_cache_profile_context_shadow", key)


def render_report(
    *,
    workload: WorkloadSpec,
    results: Dict[str, List[RunResult]],
    repeat: int,
    output_path: Path,
) -> str:
    lines: List[str] = []
    lines.append("# Fasim SSW ProfileContext Shadow")
    lines.append("")
    lines.append(
        "This default-off shadow estimates the cost that could be removed by hoisting "
        "translated-query and SSW profile-cache lookup work into a reusable "
        "`ProfileContext`. Runtime output remains controlled by the existing CPU "
        "`aligner.Align` path; this report adds no real optimization."
    )
    lines.append("")
    lines.append("Measured opt-in stack:")
    lines.append("")
    lines.append("```bash")
    lines.append("FASIM_TRANSFERSTRING_TABLE=1")
    lines.append("FASIM_GPU_DP_COLUMN_AUTO=1")
    lines.append("FASIM_SSW_PROFILE_CACHE=1")
    lines.append("FASIM_ALIGNER_ALIGN_INTERNALS=1")
    lines.append("FASIM_SSW_PROFILE_CONTEXT_SHADOW=1")
    lines.append("```")
    lines.append("")
    lines.append(f"Workload: `{workload.label}`. Each mode uses {repeat} run(s); tables report medians.")
    lines.append("")

    table_total = mode_metric(results, "table_only", "fasim_total_seconds")
    shadow_total = mode_metric(
        results, "auto_cache_profile_context_shadow", "fasim_total_seconds"
    )
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
                "AUTO + cache + ProfileContext shadow",
                fmt_seconds(shadow_total),
                fmt_speedup(speedup(table_total, shadow_total)),
                "yes" if digest_matches_reference(results, "auto_cache_profile_context_shadow") else "no",
                str(stable_records(results["auto_cache_profile_context_shadow"])),
            ],
        ],
    )
    lines.append("")

    mode = "auto_cache_profile_context_shadow"
    align_seconds = mode_metric(results, mode, "fasim_aligner_align_seconds")
    query_saved = mode_metric(
        results, mode, "fasim_ssw_profile_context_query_translate_saved_seconds_est"
    )
    lookup_saved = mode_metric(
        results, mode, "fasim_ssw_profile_context_lookup_saved_seconds_est"
    )
    total_saved = query_saved + lookup_saved
    append_table(
        lines,
        [
            "Calls",
            "Reusable calls",
            "Unique keys",
            "Query translate saved est.",
            "Lookup saved est.",
            "Total saved est.",
            "Percent of aligner",
            "Compared",
        ],
        [
            [
                fmt_int(mode_count(results, mode, "fasim_ssw_profile_context_calls")),
                fmt_int(mode_count(results, mode, "fasim_ssw_profile_context_reusable_calls")),
                fmt_int(mode_count(results, mode, "fasim_ssw_profile_context_unique_keys")),
                fmt_seconds(query_saved),
                fmt_seconds(lookup_saved),
                fmt_seconds(total_saved),
                percent(total_saved, align_seconds),
                fmt_int(mode_count(results, mode, "fasim_ssw_profile_context_shadow_compared")),
            ]
        ],
    )
    lines.append("")

    append_table(
        lines,
        [
            "Aligner setup",
            "Query translate measured",
            "Profile lookup measured",
            "Profile cache hits",
            "Profile cache misses",
            "Profile cache unique keys",
        ],
        [
            [
                fmt_seconds(mode_metric(results, mode, "fasim_aligner_setup_seconds")),
                fmt_seconds(mode_metric(results, mode, "fasim_aligner_query_translate_seconds")),
                fmt_seconds(mode_metric(results, mode, "fasim_aligner_profile_cache_lookup_seconds")),
                fmt_int(mode_count(results, mode, "fasim_ssw_profile_cache_hits")),
                fmt_int(mode_count(results, mode, "fasim_ssw_profile_cache_misses")),
                fmt_int(mode_count(results, mode, "fasim_ssw_profile_cache_unique_keys")),
            ]
        ],
    )
    lines.append("")

    append_table(
        lines,
        ["Score mismatches", "Endpoint mismatches", "CIGAR mismatches", "Digest mismatches", "Cache fallbacks"],
        [
            [
                fmt_int(mode_count(results, mode, "fasim_ssw_profile_context_score_mismatches")),
                fmt_int(mode_count(results, mode, "fasim_ssw_profile_context_endpoint_mismatches")),
                fmt_int(mode_count(results, mode, "fasim_ssw_profile_context_cigar_mismatches")),
                fmt_int(mode_count(results, mode, "fasim_ssw_profile_context_digest_mismatches")),
                fmt_int(mode_count(results, mode, "fasim_ssw_profile_cache_fallbacks")),
            ]
        ],
    )
    lines.append("")

    lines.append("## Decision")
    lines.append("")
    if not digest_matches_reference(results, mode):
        lines.append("Stop: ProfileContext shadow changed the output digest.")
    elif total_saved >= 3.0:
        lines.append(
            "The estimated setup saving is material. A future default-off real "
            "`FASIM_SSW_PROFILE_CONTEXT=1` path with validation/fallback is worth evaluating."
        )
    else:
        lines.append(
            "The shadow is clean, but estimated setup savings are small. Keep this "
            "as research evidence unless broader workloads show a larger opportunity."
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
        default=str(ROOT / ".tmp" / "fasim_ssw_profile_context_shadow"),
    )
    parser.add_argument(
        "--output",
        default=str(ROOT / "docs" / "fasim_ssw_profile_context_shadow.md"),
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
    shadow_env = {
        "FASIM_TRANSFERSTRING_TABLE": "1",
        "FASIM_GPU_DP_COLUMN_AUTO": "1",
        "FASIM_SSW_PROFILE_CACHE": "1",
        "FASIM_ALIGNER_ALIGN_INTERNALS": "1",
        "FASIM_SSW_PROFILE_CONTEXT_SHADOW": "1",
    }
    if args.force_auto:
        shadow_env["FASIM_GPU_DP_COLUMN_AUTO_MIN_WINDOWS"] = "1"
        shadow_env["FASIM_GPU_DP_COLUMN_AUTO_MIN_CELLS"] = "1"

    modes = [
        ModeSpec("table_only", "cuda", {"FASIM_TRANSFERSTRING_TABLE": "1"}),
        ModeSpec("auto_cache_profile_context_shadow", "cuda", shadow_env),
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

    require_metrics(results, PROFILE_CONTEXT_KEYS)
    report = render_report(
        workload=workload,
        results=results,
        repeat=args.repeat,
        output_path=Path(args.output).resolve(),
    )

    if args.check:
        mode = "auto_cache_profile_context_shadow"
        if not digest_matches_reference(results, mode):
            raise RuntimeError("AUTO+cache ProfileContext shadow digest does not match table_only")
        if mode_count(results, mode, "fasim_ssw_profile_context_shadow_enabled") != 1:
            raise RuntimeError("ProfileContext shadow was not enabled")
        if mode_count(results, mode, "fasim_ssw_profile_context_reusable_calls") <= 0:
            raise RuntimeError("ProfileContext shadow did not record reusable calls")
        for key in [
            "fasim_ssw_profile_context_score_mismatches",
            "fasim_ssw_profile_context_endpoint_mismatches",
            "fasim_ssw_profile_context_cigar_mismatches",
            "fasim_ssw_profile_context_digest_mismatches",
            "fasim_ssw_profile_cache_score_mismatches",
            "fasim_ssw_profile_cache_endpoint_mismatches",
            "fasim_ssw_profile_cache_cigar_mismatches",
            "fasim_ssw_profile_cache_digest_mismatches",
            "fasim_ssw_profile_cache_fallbacks",
        ]:
            if mode_count(results, mode, key) != 0:
                raise RuntimeError(f"non-zero {key}")

    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
