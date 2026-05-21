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


INDEPENDENCE_KEYS = [
    "fasim_fastSIM_precompute_independence_enabled",
    "fasim_fastSIM_precompute_legacy_requests",
    "fasim_fastSIM_precompute_derived_requests",
    "fasim_fastSIM_precompute_request_count_mismatches",
    "fasim_fastSIM_precompute_request_order_mismatches",
    "fasim_fastSIM_precompute_request_field_mismatches",
    "fasim_fastSIM_precompute_state_dependent_requests",
    "fasim_fastSIM_precompute_full_replay_enabled",
    "fasim_fastSIM_precompute_replay_requests",
    "fasim_fastSIM_precompute_candidate_state_mismatches",
    "fasim_fastSIM_precompute_emitted_record_mismatches",
    "fasim_fastSIM_precompute_cigar_mismatches",
    "fasim_fastSIM_precompute_digest_mismatches",
    "fasim_fastSIM_precompute_fallbacks",
    "fasim_fastSIM_precompute_cpu_compute_seconds",
    "fasim_fastSIM_precompute_replay_seconds",
    "fasim_fastSIM_precompute_est_parallel_seconds_2t",
    "fasim_fastSIM_precompute_est_parallel_seconds_4t",
    "fasim_fastSIM_precompute_est_parallel_seconds_8t",
    "fasim_fastSIM_precompute_est_parallel_seconds_16t",
    "fasim_fastSIM_precompute_memory_bytes",
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
            "precompute_independence",
            "cuda",
            dict(final_stack_env, FASIM_FASTSIM_ALIGN_PRECOMPUTE_INDEPENDENCE="1"),
        ),
    ]


def mode_count(results: Dict[str, List[RunResult]], mode: str, key: str) -> int:
    return median_count(results[mode], key)


def mode_metric(results: Dict[str, List[RunResult]], mode: str, key: str) -> float:
    return median_metric(results[mode], key)


def digest_matches_reference(results: Dict[str, List[RunResult]], mode: str) -> bool:
    return stable_digest(results[mode]) == stable_digest(results["table_only"])


def require_metrics(results: Dict[str, List[RunResult]], keys: Iterable[str]) -> None:
    for mode in ["final_stack", "precompute_independence"]:
        for key in keys:
            mode_metric(results, mode, key)


def prepare_workload(args: argparse.Namespace, work_root: Path) -> WorkloadSpec:
    if args.dna:
        rna_path = Path(args.rna) if args.rna else ROOT / "H19.fa"
        return WorkloadSpec(
            args.label,
            "user-provided fastSIM precompute independence workload",
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
    require_metrics(results, INDEPENDENCE_KEYS)
    for mode in ["final_stack", "precompute_independence"]:
        if not digest_matches_reference(results, mode):
            raise RuntimeError(f"{mode}: digest changed relative to table_only")
    if mode_count(results, "final_stack", "fasim_fastSIM_precompute_independence_enabled") != 0:
        raise RuntimeError("independence shadow unexpectedly enabled in final_stack")
    if mode_count(results, "precompute_independence", "fasim_fastSIM_precompute_independence_enabled") != 1:
        raise RuntimeError("independence shadow was not enabled")
    if mode_count(results, "precompute_independence", "fasim_fastSIM_precompute_full_replay_enabled") != 1:
        raise RuntimeError("full replay was not enabled")
    legacy = mode_count(results, "precompute_independence", "fasim_fastSIM_precompute_legacy_requests")
    replay = mode_count(results, "precompute_independence", "fasim_fastSIM_precompute_replay_requests")
    derived = mode_count(results, "precompute_independence", "fasim_fastSIM_precompute_derived_requests")
    if legacy <= 0 or replay != legacy or derived < legacy:
        raise RuntimeError(
            f"invalid request counts: legacy={legacy} replay={replay} derived={derived}"
        )
    for key in [
        "fasim_fastSIM_precompute_candidate_state_mismatches",
        "fasim_fastSIM_precompute_emitted_record_mismatches",
        "fasim_fastSIM_precompute_cigar_mismatches",
        "fasim_fastSIM_precompute_digest_mismatches",
        "fasim_fastSIM_precompute_fallbacks",
    ]:
        if mode_count(results, "precompute_independence", key) != 0:
            raise RuntimeError(f"expected {key}=0")


def render_report(
    *,
    workload: WorkloadSpec,
    results: Dict[str, List[RunResult]],
    repeat: int,
    output_path: Path,
) -> str:
    lines: List[str] = []
    lines.append("# Fasim fastSIM Align Precompute Independence")
    lines.append("")
    lines.append(
        "This report characterizes whether `aligner.Align` requests inside "
        "`fastSIM_extend_from_scoreinfo` can be generated from scoreInfo before "
        "the serial emit loop observes any Align result. It is shadow-only: the "
        "serial fastSIM emit path remains authority and shadow output is never "
        "used for runtime output."
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
    independence_total = mode_metric(results, "precompute_independence", "fasim_total_seconds")
    lines.append("## Runtime Summary")
    lines.append("")
    append_table(
        lines,
        [
            "Table-only seconds",
            "Final stack seconds",
            "Independence shadow seconds",
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
                fmt_seconds(independence_total),
                fmt_speedup(speedup(table_total, final_total)),
                str(stable_records(results["table_only"])),
                "`" + stable_digest(results["table_only"]) + "`",
                "yes" if digest_matches_reference(results, "final_stack") else "no",
                "yes" if digest_matches_reference(results, "precompute_independence") else "no",
            ]
        ],
    )
    lines.append("")

    lines.append("## Request Generation")
    lines.append("")
    legacy = mode_count(results, "precompute_independence", "fasim_fastSIM_precompute_legacy_requests")
    derived = mode_count(results, "precompute_independence", "fasim_fastSIM_precompute_derived_requests")
    state_dependent = mode_count(
        results, "precompute_independence", "fasim_fastSIM_precompute_state_dependent_requests"
    )
    append_table(
        lines,
        [
            "Legacy requests",
            "ScoreInfo-derived requests",
            "Count delta",
            "Order mismatches",
            "Field mismatches",
            "State-dependent / extra requests",
        ],
        [
            [
                fmt_int(legacy),
                fmt_int(derived),
                fmt_int(mode_count(results, "precompute_independence", "fasim_fastSIM_precompute_request_count_mismatches")),
                fmt_int(mode_count(results, "precompute_independence", "fasim_fastSIM_precompute_request_order_mismatches")),
                fmt_int(mode_count(results, "precompute_independence", "fasim_fastSIM_precompute_request_field_mismatches")),
                fmt_int(state_dependent),
            ]
        ],
    )
    lines.append("")
    lines.append(
        "A non-zero state-dependent count means the scoreInfo-derived upfront "
        "sequence would perform Align calls that legacy serial emit skips after "
        "observing earlier Align results."
    )
    lines.append("")

    lines.append("## Full Replay Correctness")
    lines.append("")
    append_table(
        lines,
        ["Field", "Mismatches", "Notes"],
        [
            [
                "candidate state",
                str(mode_count(results, "precompute_independence", "fasim_fastSIM_precompute_candidate_state_mismatches")),
                "Compares ordered replay against legacy candidate state.",
            ],
            [
                "emitted record",
                str(mode_count(results, "precompute_independence", "fasim_fastSIM_precompute_emitted_record_mismatches")),
                "Compares reconstructed candidate records before final output filtering.",
            ],
            [
                "CIGAR",
                str(mode_count(results, "precompute_independence", "fasim_fastSIM_precompute_cigar_mismatches")),
                "Compares side rerun CIGAR against legacy `aligner.Align` CIGAR.",
            ],
            [
                "digest",
                str(mode_count(results, "precompute_independence", "fasim_fastSIM_precompute_digest_mismatches")),
                "Runtime digest is unchanged because shadow output is not used.",
            ],
            [
                "fallbacks",
                str(mode_count(results, "precompute_independence", "fasim_fastSIM_precompute_fallbacks")),
                "No real-path fallback exists in this PR.",
            ],
        ],
    )
    lines.append("")

    lines.append("## Timing And Memory")
    lines.append("")
    append_table(
        lines,
        [
            "Legacy emit",
            "Side compute",
            "Side replay",
            "Est 2-thread",
            "Est 4-thread",
            "Est 8-thread",
            "Est 16-thread",
            "Memory bytes",
        ],
        [
            [
                fmt_seconds(mode_metric(results, "precompute_independence", "fasim_fastSIM_extend_inclusive_seconds")),
                fmt_seconds(mode_metric(results, "precompute_independence", "fasim_fastSIM_precompute_cpu_compute_seconds")),
                fmt_seconds(mode_metric(results, "precompute_independence", "fasim_fastSIM_precompute_replay_seconds")),
                fmt_seconds(mode_metric(results, "precompute_independence", "fasim_fastSIM_precompute_est_parallel_seconds_2t")),
                fmt_seconds(mode_metric(results, "precompute_independence", "fasim_fastSIM_precompute_est_parallel_seconds_4t")),
                fmt_seconds(mode_metric(results, "precompute_independence", "fasim_fastSIM_precompute_est_parallel_seconds_8t")),
                fmt_seconds(mode_metric(results, "precompute_independence", "fasim_fastSIM_precompute_est_parallel_seconds_16t")),
                fmt_int(mode_count(results, "precompute_independence", "fasim_fastSIM_precompute_memory_bytes")),
            ]
        ],
    )
    lines.append("")

    lines.append("## Decision")
    lines.append("")
    replay_clean = (
        mode_count(results, "precompute_independence", "fasim_fastSIM_precompute_candidate_state_mismatches") == 0
        and mode_count(results, "precompute_independence", "fasim_fastSIM_precompute_emitted_record_mismatches") == 0
        and mode_count(results, "precompute_independence", "fasim_fastSIM_precompute_cigar_mismatches") == 0
        and digest_matches_reference(results, "precompute_independence")
    )
    if state_dependent == 0 and replay_clean:
        lines.append(
            "The scoreInfo-derived request sequence matches legacy and full replay is clean for this workload. "
            "This supports, but does not yet prove, a future real precompute opt-in."
        )
    elif replay_clean:
        lines.append(
            "Full replay is clean for the legacy request sequence, but scoreInfo-derived upfront request "
            "generation differs from legacy. Do not build a real upfront precompute path from this result; "
            "consider a smaller buffered or pipeline design only after decomposing the state dependency."
        )
    else:
        lines.append(
            "Full replay is not clean. Do not parallelize fastSIM align reconstruction until the mismatch "
            "contract is understood."
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
        default=str(ROOT / ".tmp" / "fasim_fastSIM_align_precompute_independence_report"),
    )
    parser.add_argument(
        "--output",
        default=str(ROOT / "docs" / "fasim_fastSIM_align_precompute_independence.md"),
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
