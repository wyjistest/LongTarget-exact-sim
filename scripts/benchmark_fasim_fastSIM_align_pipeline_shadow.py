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


PIPELINE_KEYS = [
    "fasim_fastSIM_pipeline_shadow_enabled",
    "fasim_fastSIM_pipeline_legacy_requests",
    "fasim_fastSIM_pipeline_segments",
    "fasim_fastSIM_pipeline_barriers",
    "fasim_fastSIM_pipeline_segment_p50",
    "fasim_fastSIM_pipeline_segment_p90",
    "fasim_fastSIM_pipeline_segment_p99",
    "fasim_fastSIM_pipeline_segment_max",
    "fasim_fastSIM_pipeline_segment_len1",
    "fasim_fastSIM_pipeline_segment_len2",
    "fasim_fastSIM_pipeline_segment_len3",
    "fasim_fastSIM_pipeline_segment_len4",
    "fasim_fastSIM_pipeline_segment_len5plus",
    "fasim_fastSIM_pipeline_requests_batchable_2",
    "fasim_fastSIM_pipeline_requests_batchable_4",
    "fasim_fastSIM_pipeline_requests_batchable_8",
    "fasim_fastSIM_pipeline_requests_batchable_16",
    "fasim_fastSIM_pipeline_est_parallel_seconds_2t",
    "fasim_fastSIM_pipeline_est_parallel_seconds_4t",
    "fasim_fastSIM_pipeline_est_parallel_seconds_8t",
    "fasim_fastSIM_pipeline_candidate_state_mismatches",
    "fasim_fastSIM_pipeline_emitted_record_mismatches",
    "fasim_fastSIM_pipeline_cigar_mismatches",
    "fasim_fastSIM_pipeline_digest_mismatches",
    "fasim_fastSIM_precompute_candidate_state_mismatches",
    "fasim_fastSIM_precompute_emitted_record_mismatches",
    "fasim_fastSIM_precompute_cigar_mismatches",
    "fasim_fastSIM_precompute_digest_mismatches",
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
            "pipeline_shadow",
            "cuda",
            dict(final_stack_env, FASIM_FASTSIM_ALIGN_PIPELINE_SHADOW="1"),
        ),
    ]


def mode_count(results: Dict[str, List[RunResult]], mode: str, key: str) -> int:
    return median_count(results[mode], key)


def mode_metric(results: Dict[str, List[RunResult]], mode: str, key: str) -> float:
    return median_metric(results[mode], key)


def digest_matches_reference(results: Dict[str, List[RunResult]], mode: str) -> bool:
    return stable_digest(results[mode]) == stable_digest(results["table_only"])


def require_metrics(results: Dict[str, List[RunResult]], keys: Iterable[str]) -> None:
    for mode in ["final_stack", "pipeline_shadow"]:
        for key in keys:
            mode_metric(results, mode, key)


def prepare_workload(args: argparse.Namespace, work_root: Path) -> WorkloadSpec:
    if args.dna:
        rna_path = Path(args.rna) if args.rna else ROOT / "H19.fa"
        return WorkloadSpec(
            args.label,
            "user-provided fastSIM align pipeline shadow workload",
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
    require_metrics(results, PIPELINE_KEYS)
    for mode in ["final_stack", "pipeline_shadow"]:
        if not digest_matches_reference(results, mode):
            raise RuntimeError(f"{mode}: digest changed relative to table_only")
    if mode_count(results, "final_stack", "fasim_fastSIM_pipeline_shadow_enabled") != 0:
        raise RuntimeError("pipeline shadow unexpectedly enabled in final_stack")
    if mode_count(results, "pipeline_shadow", "fasim_fastSIM_pipeline_shadow_enabled") != 1:
        raise RuntimeError("pipeline shadow was not enabled")
    legacy = mode_count(results, "pipeline_shadow", "fasim_fastSIM_pipeline_legacy_requests")
    segments = mode_count(results, "pipeline_shadow", "fasim_fastSIM_pipeline_segments")
    if legacy <= 0 or segments <= 0:
        raise RuntimeError(f"invalid pipeline shape: legacy={legacy} segments={segments}")
    segment_max = mode_count(results, "pipeline_shadow", "fasim_fastSIM_pipeline_segment_max")
    if segment_max <= 0:
        raise RuntimeError("missing max segment size")
    histogram_segments = sum(
        mode_count(results, "pipeline_shadow", key)
        for key in [
            "fasim_fastSIM_pipeline_segment_len1",
            "fasim_fastSIM_pipeline_segment_len2",
            "fasim_fastSIM_pipeline_segment_len3",
            "fasim_fastSIM_pipeline_segment_len4",
            "fasim_fastSIM_pipeline_segment_len5plus",
        ]
    )
    if histogram_segments != segments:
        raise RuntimeError(
            f"segment histogram mismatch: histogram={histogram_segments} segments={segments}"
        )
    if (
        mode_count(results, "pipeline_shadow", "fasim_fastSIM_pipeline_requests_batchable_2") > 0
        and segment_max < 2
    ):
        raise RuntimeError("batchable_2 reported with segment max < 2")
    for key in [
        "fasim_fastSIM_pipeline_candidate_state_mismatches",
        "fasim_fastSIM_pipeline_emitted_record_mismatches",
        "fasim_fastSIM_pipeline_cigar_mismatches",
        "fasim_fastSIM_pipeline_digest_mismatches",
        "fasim_fastSIM_precompute_candidate_state_mismatches",
        "fasim_fastSIM_precompute_emitted_record_mismatches",
        "fasim_fastSIM_precompute_cigar_mismatches",
        "fasim_fastSIM_precompute_digest_mismatches",
    ]:
        if mode_count(results, "pipeline_shadow", key) != 0:
            raise RuntimeError(f"expected {key}=0")


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
    lines.append("# Fasim fastSIM Align Pipeline Shadow")
    lines.append("")
    lines.append(
        "This report characterizes whether the legacy `aligner.Align` stream inside "
        "`fastSIM_extend_from_scoreinfo` contains post-hoc segments large enough "
        "for a future bounded buffered or pipelined precompute. It is shadow-only: "
        "serial fastSIM emit remains authority and shadow output is never used for runtime output. "
        "Segment length is measured from the observed legacy stream; it is not a real-path "
        "contract because early-break decisions are only known after prior Align results."
    )
    lines.append("")
    lines.append(
        "Boundary: no real precompute, no default enablement, no output change, "
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
    pipeline_total = mode_metric(results, "pipeline_shadow", "fasim_total_seconds")
    lines.append("## Runtime Summary")
    lines.append("")
    append_table(
        lines,
        [
            "Table-only seconds",
            "Final stack seconds",
            "Pipeline shadow seconds",
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
                fmt_seconds(pipeline_total),
                fmt_speedup(speedup(table_total, final_total)),
                str(stable_records(results["table_only"])),
                "`" + stable_digest(results["table_only"]) + "`",
                "yes" if digest_matches_reference(results, "final_stack") else "no",
                "yes" if digest_matches_reference(results, "pipeline_shadow") else "no",
            ]
        ],
    )
    lines.append("")

    lines.append("## Segment Shape")
    lines.append("")
    legacy = mode_count(results, "pipeline_shadow", "fasim_fastSIM_pipeline_legacy_requests")
    segments = mode_count(results, "pipeline_shadow", "fasim_fastSIM_pipeline_segments")
    append_table(
        lines,
        [
            "Legacy requests",
            "Segments",
            "Barriers",
            "p50",
            "p90",
            "p99",
            "max",
            "Avg requests/segment",
        ],
        [
            [
                fmt_int(legacy),
                fmt_int(segments),
                fmt_int(mode_count(results, "pipeline_shadow", "fasim_fastSIM_pipeline_barriers")),
                fmt_int(mode_count(results, "pipeline_shadow", "fasim_fastSIM_pipeline_segment_p50")),
                fmt_int(mode_count(results, "pipeline_shadow", "fasim_fastSIM_pipeline_segment_p90")),
                fmt_int(mode_count(results, "pipeline_shadow", "fasim_fastSIM_pipeline_segment_p99")),
                fmt_int(mode_count(results, "pipeline_shadow", "fasim_fastSIM_pipeline_segment_max")),
                f"{legacy / segments:.2f}" if segments > 0 else "0.00",
            ]
        ],
    )
    lines.append("")

    lines.append("## Bounded Lookahead")
    lines.append("")
    append_table(
        lines,
        ["Segment length", "Segments"],
        [
            ["1", fmt_int(mode_count(results, "pipeline_shadow", "fasim_fastSIM_pipeline_segment_len1"))],
            ["2", fmt_int(mode_count(results, "pipeline_shadow", "fasim_fastSIM_pipeline_segment_len2"))],
            ["3", fmt_int(mode_count(results, "pipeline_shadow", "fasim_fastSIM_pipeline_segment_len3"))],
            ["4", fmt_int(mode_count(results, "pipeline_shadow", "fasim_fastSIM_pipeline_segment_len4"))],
            ["5+", fmt_int(mode_count(results, "pipeline_shadow", "fasim_fastSIM_pipeline_segment_len5plus"))],
        ],
    )
    lines.append("")
    batchable_2 = mode_count(results, "pipeline_shadow", "fasim_fastSIM_pipeline_requests_batchable_2")
    batchable_4 = mode_count(results, "pipeline_shadow", "fasim_fastSIM_pipeline_requests_batchable_4")
    batchable_8 = mode_count(results, "pipeline_shadow", "fasim_fastSIM_pipeline_requests_batchable_8")
    batchable_16 = mode_count(results, "pipeline_shadow", "fasim_fastSIM_pipeline_requests_batchable_16")
    append_table(
        lines,
        ["Lookahead", "Requests in segments", "Share of legacy requests"],
        [
            ["2", fmt_int(batchable_2), percent(batchable_2, legacy)],
            ["4", fmt_int(batchable_4), percent(batchable_4, legacy)],
            ["8", fmt_int(batchable_8), percent(batchable_8, legacy)],
            ["16", fmt_int(batchable_16), percent(batchable_16, legacy)],
        ],
    )
    lines.append("")

    lines.append("## Replay Correctness")
    lines.append("")
    append_table(
        lines,
        ["Field", "Mismatches", "Notes"],
        [
            [
                "candidate state",
                str(mode_count(results, "pipeline_shadow", "fasim_fastSIM_precompute_candidate_state_mismatches")),
                "Reuses legacy ordered replay comparison.",
            ],
            [
                "emitted record",
                str(mode_count(results, "pipeline_shadow", "fasim_fastSIM_precompute_emitted_record_mismatches")),
                "Compares reconstructed candidate records before final output filtering.",
            ],
            [
                "CIGAR",
                str(mode_count(results, "pipeline_shadow", "fasim_fastSIM_precompute_cigar_mismatches")),
                "Compares side rerun CIGAR against legacy `aligner.Align` CIGAR.",
            ],
            [
                "digest",
                str(mode_count(results, "pipeline_shadow", "fasim_fastSIM_precompute_digest_mismatches")),
                "Runtime digest is unchanged because shadow output is not used.",
            ],
        ],
    )
    lines.append("")

    lines.append("## Timing Estimate")
    lines.append("")
    append_table(
        lines,
        [
            "Legacy emit",
            "Align CPU seconds",
            "Est 2-thread",
            "Est 4-thread",
            "Est 8-thread",
        ],
        [
            [
                fmt_seconds(mode_metric(results, "pipeline_shadow", "fasim_fastSIM_extend_inclusive_seconds")),
                fmt_seconds(mode_metric(results, "pipeline_shadow", "fasim_aligner_align_seconds")),
                fmt_seconds(mode_metric(results, "pipeline_shadow", "fasim_fastSIM_pipeline_est_parallel_seconds_2t")),
                fmt_seconds(mode_metric(results, "pipeline_shadow", "fasim_fastSIM_pipeline_est_parallel_seconds_4t")),
                fmt_seconds(mode_metric(results, "pipeline_shadow", "fasim_fastSIM_pipeline_est_parallel_seconds_8t")),
            ]
        ],
    )
    lines.append("")

    lines.append("## Decision")
    lines.append("")
    p90 = mode_count(results, "pipeline_shadow", "fasim_fastSIM_pipeline_segment_p90")
    if p90 >= 4 and batchable_8 > 0:
        lines.append(
            "The legacy stream contains non-trivial post-hoc segments. This supports only "
            "further state-aware pipeline research; it is not enough for a real opt-in because "
            "the segment width is learned from legacy Align outcomes."
        )
    elif p90 >= 4:
        lines.append(
            "The legacy stream has short post-hoc length-4 groups, but no large lookahead-8/16 "
            "opportunity on this workload. A naive lookahead-4 path would still need to avoid "
            "#121-style overcompute, because many candidates break after the first Align call. "
            "Do not build a real pipeline opt-in from this result."
        )
    else:
        lines.append(
            "The legacy stream is dominated by short state-barrier groups. Full upfront "
            "precompute is already no-go from #121, and a bounded pipeline is unlikely to "
            "produce large savings unless a narrower state dependency is found."
        )
    lines.append("")
    lines.append("## Boundaries")
    lines.append("")
    lines.append("```text")
    lines.append("real precompute added: no")
    lines.append("uses shadow output for runtime output: no")
    lines.append("replaces fastSIM emit: no")
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
        default=str(ROOT / ".tmp" / "fasim_fastSIM_align_pipeline_shadow_report"),
    )
    parser.add_argument(
        "--output",
        default=str(ROOT / "docs" / "fasim_fastSIM_align_pipeline_shadow.md"),
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
