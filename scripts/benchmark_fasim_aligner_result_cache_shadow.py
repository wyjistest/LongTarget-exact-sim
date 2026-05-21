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
from check_fasim_gpu_dp_column_hg38_score_mismatch_fix import (  # noqa: E402
    HG38_CHR21_SOFTMASK_COMPACT_REGION_Z,
    decode_fixture,
    write_fasta,
)


RESULT_CACHE_KEYS = [
    "fasim_aligner_result_cache_shadow_enabled",
    "fasim_aligner_result_cache_calls",
    "fasim_aligner_result_cache_unique_keys",
    "fasim_aligner_result_cache_duplicate_calls",
    "fasim_aligner_result_cache_duplicate_fraction",
    "fasim_aligner_result_cache_duplicate_cells",
    "fasim_aligner_result_cache_est_seconds_saved",
    "fasim_aligner_result_cache_memory_bytes_est",
    "fasim_aligner_result_cache_score_mismatches",
    "fasim_aligner_result_cache_endpoint_mismatches",
    "fasim_aligner_result_cache_cigar_mismatches",
    "fasim_aligner_result_cache_digest_mismatches",
    "fasim_aligner_result_cache_first_mismatch_key",
]

RESULT_CACHE_MISMATCH_KEYS = [
    "fasim_aligner_result_cache_score_mismatches",
    "fasim_aligner_result_cache_endpoint_mismatches",
    "fasim_aligner_result_cache_cigar_mismatches",
    "fasim_aligner_result_cache_digest_mismatches",
]


def make_final_stack_env() -> Dict[str, str]:
    return {
        "FASIM_TRANSFERSTRING_TABLE": "1",
        "FASIM_GPU_DP_COLUMN_AUTO": "1",
        "FASIM_GPU_DP_COLUMN_AUTO_MIN_WINDOWS": "1",
        "FASIM_GPU_DP_COLUMN_AUTO_MIN_CELLS": "1",
        "FASIM_SSW_PROFILE_CACHE": "1",
        "FASIM_SSW_AVX2": "1",
        "FASIM_SSW_PROFILE_CONTEXT": "1",
        "FASIM_EXACT_COLUMN_EXTEND_BATCH": "1",
    }


def make_modes() -> List[ModeSpec]:
    final_stack_env = make_final_stack_env()
    return [
        ModeSpec("table_only", "cuda", {"FASIM_TRANSFERSTRING_TABLE": "1"}),
        ModeSpec("final_stack", "cuda", final_stack_env),
        ModeSpec(
            "result_cache_shadow",
            "cuda",
            dict(final_stack_env, FASIM_ALIGNER_RESULT_CACHE_SHADOW="1"),
        ),
    ]


def mode_count(results: Dict[str, List[RunResult]], mode: str, key: str) -> int:
    return median_count(results[mode], key)


def mode_metric(results: Dict[str, List[RunResult]], mode: str, key: str) -> float:
    return median_metric(results[mode], key)


def digest_matches_reference(results: Dict[str, List[RunResult]], mode: str) -> bool:
    return stable_digest(results[mode]) == stable_digest(results["table_only"])


def require_metrics(results: Dict[str, List[RunResult]], keys: Iterable[str]) -> None:
    for mode in ["final_stack", "result_cache_shadow"]:
        for key in keys:
            mode_metric(results, mode, key)


def prepare_workload(args: argparse.Namespace, work_root: Path) -> WorkloadSpec:
    if args.dna:
        rna_path = Path(args.rna) if args.rna else ROOT / "H19.fa"
        return WorkloadSpec(
            args.label,
            "user-provided aligner result-cache shadow workload",
            dna_path=Path(args.dna),
            rna_path=rna_path,
        )

    fixture_dir = work_root / "fixtures"
    fixture_dir.mkdir(parents=True, exist_ok=True)
    dna_path = fixture_dir / "hg38_chr21_softmask_compact_region.fa"
    write_fasta(
        dna_path,
        "hg38|chr21|41825001-41830000",
        decode_fixture(HG38_CHR21_SOFTMASK_COMPACT_REGION_Z),
    )
    return WorkloadSpec(
        "hg38_chr21_softmask_compact_region",
        "small hg38 soft-mask fixture with compact exact-column coverage",
        dna_path=dna_path,
        rna_path=ROOT / "H19.fa",
    )


def validate_results(results: Dict[str, List[RunResult]]) -> None:
    require_metrics(results, RESULT_CACHE_KEYS)
    for mode in ["final_stack", "result_cache_shadow"]:
        if not digest_matches_reference(results, mode):
            raise RuntimeError(f"{mode}: digest changed relative to table_only")
    if mode_count(results, "final_stack", "fasim_aligner_result_cache_shadow_enabled") != 0:
        raise RuntimeError("result-cache shadow unexpectedly enabled in final_stack")
    if mode_count(results, "result_cache_shadow", "fasim_aligner_result_cache_shadow_enabled") != 1:
        raise RuntimeError("result-cache shadow was not enabled")

    calls = mode_count(results, "result_cache_shadow", "fasim_aligner_result_cache_calls")
    unique = mode_count(results, "result_cache_shadow", "fasim_aligner_result_cache_unique_keys")
    duplicates = mode_count(
        results, "result_cache_shadow", "fasim_aligner_result_cache_duplicate_calls"
    )
    if calls <= 0 or unique <= 0:
        raise RuntimeError(f"invalid result-cache shape: calls={calls} unique={unique}")
    if unique + duplicates != calls:
        raise RuntimeError(
            f"result-cache accounting mismatch: unique={unique} "
            f"duplicates={duplicates} calls={calls}"
        )
    duplicate_fraction = mode_metric(
        results, "result_cache_shadow", "fasim_aligner_result_cache_duplicate_fraction"
    )
    if abs(duplicate_fraction - (duplicates / calls)) > 0.000001:
        raise RuntimeError("duplicate fraction mismatch")
    if mode_count(results, "result_cache_shadow", "fasim_aligner_result_cache_memory_bytes_est") <= 0:
        raise RuntimeError("missing result-cache memory estimate")
    for key in RESULT_CACHE_MISMATCH_KEYS:
        if mode_count(results, "result_cache_shadow", key) != 0:
            raise RuntimeError(f"expected {key}=0")
    if mode_count(results, "result_cache_shadow", "fasim_aligner_result_cache_first_mismatch_key") != 0:
        raise RuntimeError("unexpected first mismatch key")


def percent(value: int, total: int) -> str:
    if total <= 0:
        return "0.00%"
    return f"{(100.0 * value / total):.2f}%"


def render_report(
    *,
    workload: WorkloadSpec,
    results: Dict[str, List[RunResult]],
    repeat: int,
    output_path: Path,
) -> str:
    lines: List[str] = []
    lines.append("# Fasim Aligner Result-Cache Shadow")
    lines.append("")
    lines.append(
        "This report characterizes whether repeated identical `aligner.Align` requests "
        "exist inside legacy `fastSIM_extend_from_scoreinfo`. It is shadow-only: every "
        "legacy `aligner.Align` call still executes normally, cached results are never "
        "used for runtime output, and the shadow only compares duplicate request results "
        "against the first observed result for the same exact key."
    )
    lines.append("")
    lines.append(
        "Boundary: no real result cache, no default enablement, no output change, "
        "no scoring/threshold/non-overlap change, and no GPU AUTO, SSW/AVX2/"
        "ProfileContext, SIM-close, or recovery behavior change."
    )
    lines.append("")
    lines.append(
        f"Workload: `{workload.label}`. Each mode uses {repeat} run(s); tables report medians."
    )
    lines.append("")
    lines.append("## Modes")
    lines.append("")
    append_table(
        lines,
        ["Mode", "Environment"],
        [
            [mode.label, "`" + " ".join(f"{k}={v}" for k, v in mode.env.items()) + "`"]
            for mode in make_modes()
        ],
    )
    lines.append("")

    table_total = mode_metric(results, "table_only", "fasim_total_seconds")
    final_total = mode_metric(results, "final_stack", "fasim_total_seconds")
    shadow_total = mode_metric(results, "result_cache_shadow", "fasim_total_seconds")
    lines.append("## Runtime Summary")
    lines.append("")
    append_table(
        lines,
        [
            "Table-only seconds",
            "Final stack seconds",
            "Result-cache shadow seconds",
            "Final stack speedup",
            "Records",
            "Digest",
            "Final digest match",
            "Shadow digest match",
        ],
        [
            [
                fmt_seconds(table_total),
                fmt_seconds(final_total),
                fmt_seconds(shadow_total),
                fmt_speedup(speedup(table_total, final_total)),
                str(stable_records(results["table_only"])),
                "`" + stable_digest(results["table_only"]) + "`",
                "yes" if digest_matches_reference(results, "final_stack") else "no",
                "yes" if digest_matches_reference(results, "result_cache_shadow") else "no",
            ]
        ],
    )
    lines.append("")

    calls = mode_count(results, "result_cache_shadow", "fasim_aligner_result_cache_calls")
    unique = mode_count(results, "result_cache_shadow", "fasim_aligner_result_cache_unique_keys")
    duplicates = mode_count(
        results, "result_cache_shadow", "fasim_aligner_result_cache_duplicate_calls"
    )
    lines.append("## Request Shape")
    lines.append("")
    append_table(
        lines,
        [
            "Calls",
            "Unique keys",
            "Duplicate calls",
            "Duplicate fraction",
            "Duplicate cells",
            "Memory estimate bytes",
        ],
        [
            [
                fmt_int(calls),
                fmt_int(unique),
                fmt_int(duplicates),
                percent(duplicates, calls),
                fmt_int(
                    mode_count(
                        results,
                        "result_cache_shadow",
                        "fasim_aligner_result_cache_duplicate_cells",
                    )
                ),
                fmt_int(
                    mode_count(
                        results,
                        "result_cache_shadow",
                        "fasim_aligner_result_cache_memory_bytes_est",
                    )
                ),
            ]
        ],
    )
    lines.append("")

    lines.append("## Key Class")
    lines.append("")
    append_table(
        lines,
        ["Key class", "Calls", "Unique", "Duplicates", "Est saved seconds", "Mismatch count"],
        [
            [
                "query_hash + target_hash + filter/mask/scoring/AVX2 mode",
                fmt_int(calls),
                fmt_int(unique),
                fmt_int(duplicates),
                fmt_seconds(
                    mode_metric(
                        results,
                        "result_cache_shadow",
                        "fasim_aligner_result_cache_est_seconds_saved",
                    )
                ),
                str(
                    sum(
                        mode_count(results, "result_cache_shadow", key)
                        for key in RESULT_CACHE_MISMATCH_KEYS
                    )
                ),
            ]
        ],
    )
    lines.append("")

    lines.append("## Correctness")
    lines.append("")
    append_table(
        lines,
        ["Field", "Mismatches", "Notes"],
        [
            [
                "score",
                str(
                    mode_count(
                        results,
                        "result_cache_shadow",
                        "fasim_aligner_result_cache_score_mismatches",
                    )
                ),
                "Duplicate request score matches first-seen result.",
            ],
            [
                "endpoint",
                str(
                    mode_count(
                        results,
                        "result_cache_shadow",
                        "fasim_aligner_result_cache_endpoint_mismatches",
                    )
                ),
                "Compares ref/read begin and end fields.",
            ],
            [
                "CIGAR",
                str(
                    mode_count(
                        results,
                        "result_cache_shadow",
                        "fasim_aligner_result_cache_cigar_mismatches",
                    )
                ),
                "Compares CIGAR string.",
            ],
            [
                "digest",
                str(
                    mode_count(
                        results,
                        "result_cache_shadow",
                        "fasim_aligner_result_cache_digest_mismatches",
                    )
                ),
                "Runtime digest is unchanged because shadow output is not used.",
            ],
        ],
    )
    lines.append("")

    lines.append("## Timing Estimate")
    lines.append("")
    append_table(
        lines,
        ["Align CPU seconds", "Estimated seconds saved", "Shadow total seconds"],
        [
            [
                fmt_seconds(mode_metric(results, "result_cache_shadow", "fasim_aligner_align_seconds")),
                fmt_seconds(
                    mode_metric(
                        results,
                        "result_cache_shadow",
                        "fasim_aligner_result_cache_est_seconds_saved",
                    )
                ),
                fmt_seconds(shadow_total),
            ]
        ],
    )
    lines.append("")

    lines.append("## Decision")
    lines.append("")
    duplicate_fraction = duplicates / calls if calls > 0 else 0.0
    est_saved = mode_metric(
        results, "result_cache_shadow", "fasim_aligner_result_cache_est_seconds_saved"
    )
    memory_bytes = mode_count(
        results, "result_cache_shadow", "fasim_aligner_result_cache_memory_bytes_est"
    )
    if duplicates == 0 or duplicate_fraction < 0.01:
        lines.append(
            "Duplicate aligner requests are rare on this workload. A real result-cache "
            "path is not supported by this characterization unless larger workloads show "
            "a materially different duplicate rate."
        )
    elif est_saved < 1.0 or duplicate_fraction < 0.10:
        lines.append(
            "Duplicate requests are present, but the hit rate and estimated saved CPU time "
            "are modest. Keep the result-cache idea as shadow-only unless larger workloads "
            "show a larger absolute saving with acceptable memory overhead."
        )
    elif est_saved < 5.0 or memory_bytes > 100_000_000:
        lines.append(
            "Duplicate requests are present with a measurable estimated saving, but this "
            "is not yet a strong real-path signal because the projected saving is modest "
            "relative to total runtime and the key set has non-trivial memory cost. Do not "
            "build a real result-cache opt-in without a bounded/LRU design and another "
            "characterization."
        )
    else:
        lines.append(
            "Duplicate requests are present with non-trivial estimated saved CPU time. "
            "A future real cache would still need to be default-off and include validate/"
            "fallback before using cached results."
        )
    lines.append("")
    lines.append("## Boundaries")
    lines.append("")
    lines.append("```text")
    lines.append("real result cache added: no")
    lines.append("skips aligner.Align in runtime path: no")
    lines.append("uses cached result for runtime output: no")
    lines.append("default enabled: no")
    lines.append("scoring/threshold/non-overlap/output changed: no")
    lines.append("GPU AUTO / SSW / AVX2 / ProfileContext changed: no")
    lines.append("SIM-close / recovery changed: no")
    lines.append("```")
    lines.append("")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cuda-bin", required=True)
    parser.add_argument("--dna", default="")
    parser.add_argument("--rna", default="")
    parser.add_argument("--label", default="hg38_chr21_H19")
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument(
        "--work-dir",
        default=str(ROOT / ".tmp" / "fasim_aligner_result_cache_shadow_report"),
    )
    parser.add_argument(
        "--output",
        default=str(ROOT / "docs" / "fasim_aligner_result_cache_shadow.md"),
    )
    parser.add_argument("--require-profile", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    cuda_bin = Path(args.cuda_bin)
    if not cuda_bin.is_absolute():
        cuda_bin = (ROOT / cuda_bin).resolve()
    if not cuda_bin.exists():
        raise RuntimeError(f"missing CUDA Fasim binary: {cuda_bin}")
    if args.repeat <= 0:
        raise RuntimeError("--repeat must be > 0")

    work_root = Path(args.work_dir)
    if not work_root.is_absolute():
        work_root = (ROOT / work_root).resolve()
    workload = prepare_workload(args, work_root)
    modes = make_modes()
    results: Dict[str, List[RunResult]] = {mode.label: [] for mode in modes}
    for mode in modes:
        for run_index in range(args.repeat):
            results[mode.label].append(
                run_once(
                    workload=workload,
                    mode=mode,
                    bin_path=cuda_bin,
                    work_dir=work_root / workload.label / mode.label / f"run_{run_index + 1}",
                    require_profile=args.require_profile,
                )
            )

    if args.check:
        validate_results(results)

    render_report(
        workload=workload,
        results=results,
        repeat=args.repeat,
        output_path=Path(args.output).resolve(),
    )
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
