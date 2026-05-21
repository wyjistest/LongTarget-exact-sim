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
    "fasim_ssw_profile_context_requested",
    "fasim_ssw_profile_context_active",
    "fasim_ssw_profile_context_disabled_reason",
    "fasim_ssw_profile_context_validate_enabled",
    "fasim_ssw_profile_context_calls",
    "fasim_ssw_profile_context_hits",
    "fasim_ssw_profile_context_misses",
    "fasim_ssw_profile_context_unique_keys",
    "fasim_ssw_profile_context_query_translate_saved_seconds",
    "fasim_ssw_profile_context_lookup_saved_seconds",
    "fasim_ssw_profile_context_validate_seconds",
    "fasim_ssw_profile_context_score_mismatches",
    "fasim_ssw_profile_context_endpoint_mismatches",
    "fasim_ssw_profile_context_cigar_mismatches",
    "fasim_ssw_profile_context_digest_mismatches",
    "fasim_ssw_profile_context_fallbacks",
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
    for mode in ["auto_cache_context", "auto_cache_context_validate"]:
        for key in keys:
            mode_metric(results, mode, key)


def render_report(
    *,
    workload: WorkloadSpec,
    results: Dict[str, List[RunResult]],
    repeat: int,
    output_path: Path,
) -> str:
    lines: List[str] = []
    lines.append("# Fasim SSW ProfileContext Opt-In")
    lines.append("")
    lines.append(
        "This report characterizes the default-off real SSW `ProfileContext` fast path. "
        "`FASIM_SSW_PROFILE_CONTEXT=1` is active only when `FASIM_SSW_PROFILE_CACHE=1` "
        "is active. It reuses the translated query and hot cached profile context by "
        "exact query/scoring key. Validation mode reruns the legacy per-call "
        "translation/cache-lookup path and falls back on any score, endpoint, CIGAR, "
        "or digest mismatch."
    )
    lines.append("")
    lines.append("Measured opt-in stack:")
    lines.append("")
    lines.append("```bash")
    lines.append("FASIM_TRANSFERSTRING_TABLE=1")
    lines.append("FASIM_GPU_DP_COLUMN_AUTO=1")
    lines.append("FASIM_SSW_PROFILE_CACHE=1")
    lines.append("FASIM_SSW_PROFILE_CONTEXT=1")
    lines.append("```")
    lines.append("")
    lines.append(f"Workload: `{workload.label}`. Each mode uses {repeat} run(s); tables report medians.")
    lines.append("")

    table_total = mode_metric(results, "table_only", "fasim_total_seconds")
    auto_cache_total = mode_metric(results, "auto_cache", "fasim_total_seconds")
    context_total = mode_metric(results, "auto_cache_context", "fasim_total_seconds")
    validate_total = mode_metric(results, "auto_cache_context_validate", "fasim_total_seconds")
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
                "AUTO + cache",
                fmt_seconds(auto_cache_total),
                fmt_speedup(speedup(table_total, auto_cache_total)),
                "yes" if digest_matches_reference(results, "auto_cache") else "no",
                str(stable_records(results["auto_cache"])),
            ],
            [
                "AUTO + cache + ProfileContext",
                fmt_seconds(context_total),
                fmt_speedup(speedup(table_total, context_total)),
                "yes" if digest_matches_reference(results, "auto_cache_context") else "no",
                str(stable_records(results["auto_cache_context"])),
            ],
            [
                "AUTO + cache + ProfileContext validate",
                fmt_seconds(validate_total),
                fmt_speedup(speedup(table_total, validate_total)),
                "yes" if digest_matches_reference(results, "auto_cache_context_validate") else "no",
                str(stable_records(results["auto_cache_context_validate"])),
            ],
        ],
    )
    lines.append("")

    append_table(
        lines,
        [
            "Mode",
            "Calls",
            "Hits",
            "Misses",
            "Hit rate",
            "Unique keys",
            "Query saved",
            "Lookup saved",
            "Validate seconds",
            "Fallbacks",
        ],
        [
            [
                mode,
                fmt_int(mode_count(results, mode, "fasim_ssw_profile_context_calls")),
                fmt_int(mode_count(results, mode, "fasim_ssw_profile_context_hits")),
                fmt_int(mode_count(results, mode, "fasim_ssw_profile_context_misses")),
                percent(
                    float(mode_count(results, mode, "fasim_ssw_profile_context_hits")),
                    float(mode_count(results, mode, "fasim_ssw_profile_context_calls")),
                ),
                fmt_int(mode_count(results, mode, "fasim_ssw_profile_context_unique_keys")),
                fmt_seconds(mode_metric(results, mode, "fasim_ssw_profile_context_query_translate_saved_seconds")),
                fmt_seconds(mode_metric(results, mode, "fasim_ssw_profile_context_lookup_saved_seconds")),
                fmt_seconds(mode_metric(results, mode, "fasim_ssw_profile_context_validate_seconds")),
                fmt_int(mode_count(results, mode, "fasim_ssw_profile_context_fallbacks")),
            ]
            for mode in ["auto_cache_context", "auto_cache_context_validate"]
        ],
    )
    lines.append("")

    append_table(
        lines,
        [
            "Mode",
            "Score mismatches",
            "Endpoint mismatches",
            "CIGAR mismatches",
            "Digest mismatches",
            "Cache fallbacks",
        ],
        [
            [
                mode,
                fmt_int(mode_count(results, mode, "fasim_ssw_profile_context_score_mismatches")),
                fmt_int(mode_count(results, mode, "fasim_ssw_profile_context_endpoint_mismatches")),
                fmt_int(mode_count(results, mode, "fasim_ssw_profile_context_cigar_mismatches")),
                fmt_int(mode_count(results, mode, "fasim_ssw_profile_context_digest_mismatches")),
                fmt_int(mode_count(results, mode, "fasim_ssw_profile_cache_fallbacks")),
            ]
            for mode in ["auto_cache_context", "auto_cache_context_validate"]
        ],
    )
    lines.append("")

    append_table(
        lines,
        ["AUTO+cache seconds", "Context seconds", "Delta seconds", "Context hit rate", "Digest clean"],
        [
            [
                fmt_seconds(auto_cache_total),
                fmt_seconds(context_total),
                fmt_seconds(auto_cache_total - context_total),
                percent(
                    float(mode_count(results, "auto_cache_context", "fasim_ssw_profile_context_hits")),
                    float(mode_count(results, "auto_cache_context", "fasim_ssw_profile_context_calls")),
                ),
                "yes" if digest_matches_reference(results, "auto_cache_context") else "no",
            ]
        ],
    )
    lines.append("")

    lines.append("## Decision")
    lines.append("")
    if not digest_matches_reference(results, "auto_cache_context"):
        lines.append("Stop: ProfileContext changed the output digest.")
    elif any(mode_count(results, "auto_cache_context_validate", key) != 0 for key in [
        "fasim_ssw_profile_context_score_mismatches",
        "fasim_ssw_profile_context_endpoint_mismatches",
        "fasim_ssw_profile_context_cigar_mismatches",
        "fasim_ssw_profile_context_digest_mismatches",
        "fasim_ssw_profile_context_fallbacks",
    ]):
        lines.append("Stop: ProfileContext validation found mismatches or fallbacks.")
    elif context_total < auto_cache_total:
        lines.append("ProfileContext is exact-clean and faster in this run.")
    else:
        lines.append("ProfileContext is exact-clean, but this run did not show a runtime win.")
    lines.append("")

    lines.append("## Boundaries")
    lines.append("")
    lines.append("```text")
    lines.append("default enabled: no")
    lines.append("requires FASIM_SSW_PROFILE_CACHE=1: yes")
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
        default=str(ROOT / ".tmp" / "fasim_ssw_profile_context"),
    )
    parser.add_argument(
        "--output",
        default=str(ROOT / "docs" / "fasim_ssw_profile_context.md"),
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
    if args.force_auto:
        auto_env["FASIM_GPU_DP_COLUMN_AUTO_MIN_WINDOWS"] = "1"
        auto_env["FASIM_GPU_DP_COLUMN_AUTO_MIN_CELLS"] = "1"
    modes = [
        ModeSpec("table_only", "cuda", {"FASIM_TRANSFERSTRING_TABLE": "1"}),
        ModeSpec("auto_cache", "cuda", dict(auto_env, FASIM_SSW_PROFILE_CACHE="1")),
        ModeSpec(
            "auto_cache_context",
            "cuda",
            dict(
                auto_env,
                FASIM_SSW_PROFILE_CACHE="1",
                FASIM_SSW_PROFILE_CONTEXT="1",
            ),
        ),
        ModeSpec(
            "auto_cache_context_validate",
            "cuda",
            dict(
                auto_env,
                FASIM_SSW_PROFILE_CACHE="1",
                FASIM_SSW_PROFILE_CONTEXT="1",
                FASIM_SSW_PROFILE_CONTEXT_VALIDATE="1",
            ),
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

    require_metrics(results, PROFILE_CONTEXT_KEYS)
    report = render_report(
        workload=workload,
        results=results,
        repeat=args.repeat,
        output_path=Path(args.output).resolve(),
    )

    if args.check:
        for mode in ["auto_cache", "auto_cache_context", "auto_cache_context_validate"]:
            if not digest_matches_reference(results, mode):
                raise RuntimeError(f"{mode} digest does not match table_only")
        for mode in ["auto_cache_context", "auto_cache_context_validate"]:
            if mode_count(results, mode, "fasim_ssw_profile_context_active") != 1:
                raise RuntimeError(f"{mode} did not activate SSW ProfileContext")
            if mode_count(results, mode, "fasim_ssw_profile_context_hits") <= 0:
                raise RuntimeError(f"{mode} did not record SSW ProfileContext hits")
            if mode_count(results, mode, "fasim_ssw_profile_context_misses") <= 0:
                raise RuntimeError(f"{mode} did not record SSW ProfileContext misses")
            for key in [
                "fasim_ssw_profile_context_score_mismatches",
                "fasim_ssw_profile_context_endpoint_mismatches",
                "fasim_ssw_profile_context_cigar_mismatches",
                "fasim_ssw_profile_context_digest_mismatches",
                "fasim_ssw_profile_context_fallbacks",
                "fasim_ssw_profile_cache_score_mismatches",
                "fasim_ssw_profile_cache_endpoint_mismatches",
                "fasim_ssw_profile_cache_cigar_mismatches",
                "fasim_ssw_profile_cache_digest_mismatches",
                "fasim_ssw_profile_cache_fallbacks",
            ]:
                if mode_count(results, mode, key) != 0:
                    raise RuntimeError(f"{mode} reported non-zero {key}")

    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
