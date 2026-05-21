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
from benchmark_fasim_profile import metric_float  # noqa: E402
from check_fasim_gpu_dp_column_hg38_score_mismatch_fix import (  # noqa: E402
    HG38_CHR21_SOFTMASK_COMPACT_REGION_Z,
    decode_fixture,
    write_fasta,
)


PRECOMPUTE_KEYS = [
    "fasim_fastSIM_precompute_shadow_enabled",
    "fasim_fastSIM_precompute_requests",
    "fasim_fastSIM_precompute_requests_independent",
    "fasim_fastSIM_precompute_requests_state_dependent",
    "fasim_fastSIM_precompute_cpu_reference_seconds",
    "fasim_fastSIM_precompute_side_compute_seconds",
    "fasim_fastSIM_precompute_side_replay_seconds",
    "fasim_fastSIM_precompute_est_parallel_seconds_2t",
    "fasim_fastSIM_precompute_est_parallel_seconds_4t",
    "fasim_fastSIM_precompute_est_parallel_seconds_8t",
    "fasim_fastSIM_precompute_candidate_state_mismatches",
    "fasim_fastSIM_precompute_emitted_record_mismatches",
    "fasim_fastSIM_precompute_cigar_mismatches",
    "fasim_fastSIM_precompute_digest_mismatches",
    "fasim_fastSIM_precompute_fallbacks",
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


def make_modes(max_requests: int, stride: int) -> List[ModeSpec]:
    final_stack_env = make_final_stack_env()
    shadow_env = dict(
        final_stack_env,
        FASIM_FASTSIM_ALIGN_PRECOMPUTE_SHADOW="1",
        FASIM_FASTSIM_ALIGN_PRECOMPUTE_SHADOW_MAX_REQUESTS=str(max_requests),
        FASIM_FASTSIM_ALIGN_PRECOMPUTE_SHADOW_REQUEST_STRIDE=str(stride),
    )
    return [
        ModeSpec("table_only", "cuda", {"FASIM_TRANSFERSTRING_TABLE": "1"}),
        ModeSpec("final_stack", "cuda", final_stack_env),
        ModeSpec("precompute_shadow", "cuda", shadow_env),
    ]


def mode_count(results: Dict[str, List[RunResult]], mode: str, key: str) -> int:
    return median_count(results[mode], key)


def mode_metric(results: Dict[str, List[RunResult]], mode: str, key: str) -> float:
    return median_metric(results[mode], key)


def digest_matches_reference(results: Dict[str, List[RunResult]], mode: str) -> bool:
    return stable_digest(results[mode]) == stable_digest(results["table_only"])


def require_metrics(results: Dict[str, List[RunResult]], keys: Iterable[str]) -> None:
    for mode in ["final_stack", "precompute_shadow"]:
        for key in keys:
            mode_metric(results, mode, key)


def render_report(
    *,
    workload: WorkloadSpec,
    results: Dict[str, List[RunResult]],
    repeat: int,
    max_requests: int,
    stride: int,
    output_path: Path,
) -> str:
    lines: List[str] = []
    lines.append("# Fasim fastSIM Align Precompute Shadow")
    lines.append("")
    lines.append(
        "This report characterizes a default-off `fastSIM_extend_from_scoreinfo` "
        "aligner precompute shadow. The serial fastSIM emit path remains the "
        "runtime authority; the shadow collects bounded `aligner.Align` requests, "
        "reruns them in a side path, replays candidate decisions in legacy order, "
        "and compares diagnostic state. It does not feed shadow output into final "
        "Fasim output."
    )
    lines.append("")
    lines.append(
        "Boundary: no default enablement, no output change, no scoring/threshold/"
        "non-overlap change, and no GPU AUTO, SSW/AVX2/ProfileContext, SIM-close, "
        "or recovery behavior change."
    )
    lines.append("")
    lines.append(
        f"Workload: `{workload.label}`. Each mode uses {repeat} run(s); tables "
        f"report medians. Shadow cap: `{max_requests}` requests, stride `{stride}`."
    )
    lines.append("")
    lines.append("## Modes")
    lines.append("")
    append_table(
        lines,
        ["Mode", "Environment"],
        [
            [mode.label, "`" + " ".join(f"{k}={v}" for k, v in mode.env.items()) + "`"]
            for mode in make_modes(max_requests, stride)
        ],
    )
    lines.append("")

    table_total = mode_metric(results, "table_only", "fasim_total_seconds")
    final_total = mode_metric(results, "final_stack", "fasim_total_seconds")
    shadow_total = mode_metric(results, "precompute_shadow", "fasim_total_seconds")

    lines.append("## Runtime Summary")
    lines.append("")
    append_table(
        lines,
        [
            "Table-only seconds",
            "Final stack seconds",
            "Precompute shadow seconds",
            "Final stack speedup",
            "Shadow speedup",
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
                fmt_speedup(speedup(table_total, shadow_total)),
                str(stable_records(results["table_only"])),
                "`" + stable_digest(results["table_only"]) + "`",
                "yes" if digest_matches_reference(results, "final_stack") else "no",
                "yes" if digest_matches_reference(results, "precompute_shadow") else "no",
            ]
        ],
    )
    lines.append("")

    lines.append("## Request Independence")
    lines.append("")
    requests = mode_count(results, "precompute_shadow", "fasim_fastSIM_precompute_requests")
    independent = mode_count(
        results, "precompute_shadow", "fasim_fastSIM_precompute_requests_independent"
    )
    state_dependent = mode_count(
        results, "precompute_shadow", "fasim_fastSIM_precompute_requests_state_dependent"
    )
    append_table(
        lines,
        ["Requests", "Independent", "State-dependent / unsampled", "Notes"],
        [
            [
                fmt_int(requests),
                fmt_int(independent),
                fmt_int(state_dependent),
                "Independent means every align call for that candidate was sampled and replayed.",
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
                "candidate state",
                str(mode_count(results, "precompute_shadow", "fasim_fastSIM_precompute_candidate_state_mismatches")),
                "n/a",
                "Compares replayed myflag, score, endpoints, cutlength, and selected call for sampled candidates.",
            ],
            [
                "emitted record",
                str(mode_count(results, "precompute_shadow", "fasim_fastSIM_precompute_emitted_record_mismatches")),
                "n/a",
                "Compares candidate triplex records reconstructed by side replay before global final output filtering.",
            ],
            [
                "CIGAR",
                str(mode_count(results, "precompute_shadow", "fasim_fastSIM_precompute_cigar_mismatches")),
                "n/a",
                "Compares side rerun CIGAR against legacy aligner.Align CIGAR for sampled requests.",
            ],
            [
                "digest",
                str(mode_count(results, "precompute_shadow", "fasim_fastSIM_precompute_digest_mismatches")),
                "n/a",
                "Runtime digest is unchanged because shadow output is not used for final output.",
            ],
            [
                "fallbacks",
                str(mode_count(results, "precompute_shadow", "fasim_fastSIM_precompute_fallbacks")),
                "n/a",
                "No real-path fallback exists in this PR; CPU serial emit remains authority.",
            ],
        ],
    )
    lines.append("")

    lines.append("## Timing")
    lines.append("")
    append_table(
        lines,
        [
            "Legacy emit",
            "CPU reference sample",
            "Side compute",
            "Side replay",
            "Estimated 2-thread",
            "Estimated 4-thread",
            "Estimated 8-thread",
        ],
        [
            [
                fmt_seconds(mode_metric(results, "precompute_shadow", "fasim_fastSIM_extend_inclusive_seconds")),
                fmt_seconds(mode_metric(results, "precompute_shadow", "fasim_fastSIM_precompute_cpu_reference_seconds")),
                fmt_seconds(mode_metric(results, "precompute_shadow", "fasim_fastSIM_precompute_side_compute_seconds")),
                fmt_seconds(mode_metric(results, "precompute_shadow", "fasim_fastSIM_precompute_side_replay_seconds")),
                fmt_seconds(mode_metric(results, "precompute_shadow", "fasim_fastSIM_precompute_est_parallel_seconds_2t")),
                fmt_seconds(mode_metric(results, "precompute_shadow", "fasim_fastSIM_precompute_est_parallel_seconds_4t")),
                fmt_seconds(mode_metric(results, "precompute_shadow", "fasim_fastSIM_precompute_est_parallel_seconds_8t")),
            ]
        ],
    )
    lines.append("")

    lines.append("## Decision")
    lines.append("")
    if (
        mode_count(results, "precompute_shadow", "fasim_fastSIM_precompute_candidate_state_mismatches") == 0
        and mode_count(results, "precompute_shadow", "fasim_fastSIM_precompute_emitted_record_mismatches") == 0
        and mode_count(results, "precompute_shadow", "fasim_fastSIM_precompute_cigar_mismatches") == 0
        and digest_matches_reference(results, "precompute_shadow")
    ):
        lines.append(
            "The sampled shadow is clean. This is evidence that aligner requests "
            "can be collected and replayed diagnostically for the sampled workload; "
            "it is not a real runtime precompute path yet."
        )
    else:
        lines.append(
            "The sampled shadow is not clean. Do not build a real precompute path "
            "until the mismatch contract is understood."
        )
    lines.append("")
    lines.append("Next PR, if pursued, should broaden sampled workload coverage before any real opt-in.")
    lines.append("")
    lines.append("## Boundaries")
    lines.append("")
    lines.append("```text")
    lines.append("uses shadow output for runtime output: no")
    lines.append("replaces fastSIM emit: no")
    lines.append("default enabled: no")
    lines.append("scoring/threshold/non-overlap/output changed: no")
    lines.append("GPU AUTO / SSW / SIM-close / recovery changed: no")
    lines.append("```")
    lines.append("")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return "\n".join(lines)


def prepare_workload(args: argparse.Namespace, work_root: Path) -> WorkloadSpec:
    if args.dna:
        rna_path = Path(args.rna) if args.rna else ROOT / "H19.fa"
        return WorkloadSpec(
            args.label,
            "user-provided final stack precompute shadow workload",
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
    require_metrics(results, PRECOMPUTE_KEYS)
    for mode in ["final_stack", "precompute_shadow"]:
        if not digest_matches_reference(results, mode):
            raise RuntimeError(f"{mode}: digest changed relative to table_only")
    if mode_count(results, "final_stack", "fasim_fastSIM_precompute_shadow_enabled") != 0:
        raise RuntimeError("precompute shadow unexpectedly enabled in final_stack mode")
    if mode_count(results, "precompute_shadow", "fasim_fastSIM_precompute_shadow_enabled") != 1:
        raise RuntimeError("precompute shadow was not enabled")
    requests = mode_count(results, "precompute_shadow", "fasim_fastSIM_precompute_requests")
    independent = mode_count(
        results, "precompute_shadow", "fasim_fastSIM_precompute_requests_independent"
    )
    state_dependent = mode_count(
        results, "precompute_shadow", "fasim_fastSIM_precompute_requests_state_dependent"
    )
    if requests <= 0:
        raise RuntimeError("precompute shadow observed no requests")
    if independent + state_dependent != requests:
        raise RuntimeError("precompute shadow independence counters do not sum to requests")
    for key in [
        "fasim_fastSIM_precompute_candidate_state_mismatches",
        "fasim_fastSIM_precompute_emitted_record_mismatches",
        "fasim_fastSIM_precompute_cigar_mismatches",
        "fasim_fastSIM_precompute_digest_mismatches",
        "fasim_fastSIM_precompute_fallbacks",
    ]:
        if mode_count(results, "precompute_shadow", key) != 0:
            raise RuntimeError(f"precompute shadow expected {key}=0")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cuda-bin", required=True)
    parser.add_argument("--dna", default="")
    parser.add_argument("--rna", default="")
    parser.add_argument("--label", default="hg38_chr21_H19")
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--max-requests", type=int, default=10000)
    parser.add_argument("--request-stride", type=int, default=1)
    parser.add_argument(
        "--work-dir",
        default=str(ROOT / ".tmp" / "fasim_fastSIM_align_precompute_shadow_report"),
    )
    parser.add_argument(
        "--output",
        default=str(ROOT / "docs" / "fasim_fastSIM_align_precompute_shadow.md"),
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
    modes = make_modes(args.max_requests, args.request_stride)
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
        max_requests=args.max_requests,
        stride=args.request_stride,
        output_path=Path(args.output).resolve(),
    )
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
