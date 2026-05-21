#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Dict, Iterable, List, Optional


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
from benchmark_fasim_ssw_profile_context import PROFILE_CONTEXT_KEYS  # noqa: E402


ALIGNER_KEYS = [
    "fasim_aligner_align_calls",
    "fasim_aligner_align_seconds",
]


def make_modes(*, force_auto_small: bool) -> List[ModeSpec]:
    auto_env = {
        "FASIM_TRANSFERSTRING_TABLE": "1",
        "FASIM_GPU_DP_COLUMN_AUTO": "1",
        "FASIM_ALIGNER_ALIGN_INTERNALS": "1",
    }
    if force_auto_small:
        auto_env["FASIM_GPU_DP_COLUMN_AUTO_MIN_WINDOWS"] = "1"
        auto_env["FASIM_GPU_DP_COLUMN_AUTO_MIN_CELLS"] = "1"
    return [
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


def parse_entries(value: str) -> List[int]:
    entries: List[int] = []
    for token in value.split(","):
        token = token.strip()
        if not token:
            continue
        try:
            entry = int(token)
        except ValueError as exc:
            raise RuntimeError(f"invalid synthetic entry count: {token!r}") from exc
        if entry <= 0:
            raise RuntimeError(f"synthetic entry count must be positive: {entry}")
        if entry not in entries:
            entries.append(entry)
    if not entries:
        raise RuntimeError("at least one synthetic entry count is required")
    return entries


def synthetic_label(entries: int) -> str:
    if entries == 1:
        return "tiny"
    if entries == 8:
        return "medium_synthetic"
    if entries == 32:
        return "window_heavy_synthetic"
    return f"synthetic_entries_{entries}"


def make_synthetic_workload(entries: int) -> WorkloadSpec:
    description = (
        "current testDNA/H19 smoke fixture"
        if entries == 1
        else f"{entries}-entry deterministic testDNA/H19 scale-up"
    )
    return WorkloadSpec(synthetic_label(entries), description, dna_entries=entries)


def add_optional_workload(
    workloads: List[WorkloadSpec],
    *,
    label: str,
    description: str,
    dna: Optional[str],
    rna: Optional[str],
    require: bool,
) -> None:
    if dna and rna:
        workloads.append(
            WorkloadSpec(
                label=label,
                description=description,
                dna_path=Path(dna).resolve(),
                rna_path=Path(rna).resolve(),
            )
        )
    elif require:
        raise RuntimeError(f"missing required workload paths for {label}")


def make_workloads(args: argparse.Namespace) -> List[WorkloadSpec]:
    workloads = [make_synthetic_workload(entry) for entry in parse_entries(args.synthetic_entries)]
    add_optional_workload(
        workloads,
        label="human_lnc_atlas_17kb_target",
        description="local humanLncAtlas 17kb target FASTA",
        dna=args.human_17kb_dna,
        rna=args.human_17kb_rna,
        require=args.require_real,
    )
    add_optional_workload(
        workloads,
        label="human_lnc_atlas_508kb_target",
        description="local humanLncAtlas 508kb target FASTA",
        dna=args.human_508kb_dna,
        rna=args.human_508kb_rna,
        require=args.require_real,
    )
    add_optional_workload(
        workloads,
        label=args.hg38_label,
        description="hg38 chr21 + H19 workload",
        dna=args.hg38_dna,
        rna=args.hg38_rna,
        require=args.require_hg38,
    )
    return workloads


def mode_metric(results: Dict[str, List[RunResult]], mode: str, key: str) -> float:
    return median_metric(results[mode], key)


def mode_count(results: Dict[str, List[RunResult]], mode: str, key: str) -> int:
    return median_count(results[mode], key)


def digest_matches_reference(results: Dict[str, List[RunResult]], mode: str) -> bool:
    return stable_digest(results[mode]) == stable_digest(results["auto_cache"])


def records_match_reference(results: Dict[str, List[RunResult]], mode: str) -> bool:
    return stable_records(results[mode]) == stable_records(results["auto_cache"])


def percent(numerator: float, denominator: float) -> str:
    if denominator <= 0.0:
        return "n/a"
    return f"{100.0 * numerator / denominator:.2f}%"


def context_delta_seconds(results: Dict[str, List[RunResult]]) -> float:
    return mode_metric(results, "auto_cache", "fasim_total_seconds") - mode_metric(
        results, "auto_cache_context", "fasim_total_seconds"
    )


def context_hit_rate(results: Dict[str, List[RunResult]], mode: str = "auto_cache_context") -> str:
    return percent(
        float(mode_count(results, mode, "fasim_ssw_profile_context_hits")),
        float(mode_count(results, mode, "fasim_ssw_profile_context_calls")),
    )


def context_clean(results: Dict[str, List[RunResult]], mode: str) -> bool:
    return all(
        mode_count(results, mode, key) == 0
        for key in [
            "fasim_ssw_profile_context_score_mismatches",
            "fasim_ssw_profile_context_endpoint_mismatches",
            "fasim_ssw_profile_context_cigar_mismatches",
            "fasim_ssw_profile_context_digest_mismatches",
            "fasim_ssw_profile_context_fallbacks",
        ]
    )


def align_calls(results: Dict[str, List[RunResult]], mode: str = "auto_cache_context") -> int:
    return mode_count(results, mode, "fasim_aligner_align_calls")


def context_calls(results: Dict[str, List[RunResult]], mode: str = "auto_cache_context") -> int:
    return mode_count(results, mode, "fasim_ssw_profile_context_calls")


def require_context_metrics(all_results: Dict[str, Dict[str, List[RunResult]]]) -> None:
    for workload_results in all_results.values():
        for mode in ["auto_cache", "auto_cache_context", "auto_cache_context_validate"]:
            for key in ALIGNER_KEYS:
                mode_metric(workload_results, mode, key)
        for mode in ["auto_cache_context", "auto_cache_context_validate"]:
            for key in PROFILE_CONTEXT_KEYS:
                mode_metric(workload_results, mode, key)


def check_results(all_results: Dict[str, Dict[str, List[RunResult]]]) -> None:
    require_context_metrics(all_results)
    active_workloads = 0
    for workload, results in all_results.items():
        for mode in ["auto_cache_context", "auto_cache_context_validate"]:
            if not digest_matches_reference(results, mode):
                raise RuntimeError(f"{workload}/{mode}: digest does not match AUTO+cache")
            if not records_match_reference(results, mode):
                raise RuntimeError(f"{workload}/{mode}: record count does not match AUTO+cache")
            if align_calls(results, mode) <= 0:
                continue
            active_workloads += 1
            if mode_count(results, mode, "fasim_ssw_profile_cache_active") != 1:
                raise RuntimeError(f"{workload}/{mode}: SSW profile cache did not activate")
            if mode_count(results, mode, "fasim_ssw_profile_context_requested") != 1:
                raise RuntimeError(f"{workload}/{mode}: SSW ProfileContext was not requested")
            if mode_count(results, mode, "fasim_ssw_profile_context_active") != 1:
                raise RuntimeError(f"{workload}/{mode}: SSW ProfileContext did not activate")
            expected_validate = 1 if mode == "auto_cache_context_validate" else 0
            if mode_count(results, mode, "fasim_ssw_profile_context_validate_enabled") != expected_validate:
                raise RuntimeError(f"{workload}/{mode}: validate telemetry did not match mode")
            if mode_count(results, mode, "fasim_ssw_profile_context_calls") <= 0:
                raise RuntimeError(f"{workload}/{mode}: SSW ProfileContext saw no calls")
            if mode_count(results, mode, "fasim_ssw_profile_context_hits") <= 0:
                raise RuntimeError(f"{workload}/{mode}: SSW ProfileContext saw no hits")
            if mode_count(results, mode, "fasim_ssw_profile_context_misses") <= 0:
                raise RuntimeError(f"{workload}/{mode}: SSW ProfileContext saw no misses")
            if mode_count(results, mode, "fasim_ssw_profile_context_unique_keys") <= 0:
                raise RuntimeError(f"{workload}/{mode}: SSW ProfileContext saw no unique keys")
            if mode == "auto_cache_context_validate" and (
                mode_metric(results, mode, "fasim_ssw_profile_context_validate_seconds") <= 0.0
            ):
                raise RuntimeError(f"{workload}/{mode}: validation time was not recorded")
            if not context_clean(results, mode):
                raise RuntimeError(f"{workload}/{mode}: ProfileContext metrics are not clean")
    if active_workloads <= 0:
        raise RuntimeError("no characterized workload exercised SSW ProfileContext calls")


def render_report(
    *,
    workloads: Iterable[WorkloadSpec],
    all_results: Dict[str, Dict[str, List[RunResult]]],
    repeat: int,
    output_path: Path,
) -> str:
    workload_list = list(workloads)
    lines: List[str] = []
    lines.append("# Fasim SSW ProfileContext Characterization")
    lines.append("")
    lines.append(
        "This report repeatedly characterizes the default-off real SSW "
        "`ProfileContext` opt-in from `FASIM_SSW_PROFILE_CONTEXT=1`. It adds no "
        "optimization logic and does not change defaults. `ProfileContext` is only "
        "active with `FASIM_SSW_PROFILE_CACHE=1`; validation mode reruns the legacy "
        "per-call lookup/translation path and falls back on score, endpoint, CIGAR, "
        "or digest mismatch."
    )
    lines.append("")
    lines.append("Measured modes:")
    lines.append("")
    lines.append("```bash")
    lines.append("# AUTO + cache")
    lines.append("FASIM_TRANSFERSTRING_TABLE=1")
    lines.append("FASIM_GPU_DP_COLUMN_AUTO=1")
    lines.append("FASIM_SSW_PROFILE_CACHE=1")
    lines.append("")
    lines.append("# AUTO + cache + ProfileContext")
    lines.append("FASIM_SSW_PROFILE_CONTEXT=1")
    lines.append("")
    lines.append("# AUTO + cache + ProfileContext validate")
    lines.append("FASIM_SSW_PROFILE_CONTEXT_VALIDATE=1")
    lines.append("```")
    lines.append("")
    lines.append(f"Each workload uses {repeat} run(s); tables report medians.")
    lines.append("")

    append_table(
        lines,
        [
            "Workload",
            "Records",
            "AUTO+cache s",
            "AUTO+cache+context s",
            "Delta s",
            "Context/AUTO+cache",
            "Validate s",
            "Digest clean",
            "Output digest",
            "Context exercised",
        ],
        [
            [
                workload.label,
                fmt_int(stable_records(all_results[workload.label]["auto_cache"])),
                fmt_seconds(mode_metric(all_results[workload.label], "auto_cache", "fasim_total_seconds")),
                fmt_seconds(
                    mode_metric(all_results[workload.label], "auto_cache_context", "fasim_total_seconds")
                ),
                fmt_seconds(context_delta_seconds(all_results[workload.label])),
                fmt_speedup(
                    speedup(
                        mode_metric(all_results[workload.label], "auto_cache", "fasim_total_seconds"),
                        mode_metric(
                            all_results[workload.label],
                            "auto_cache_context",
                            "fasim_total_seconds",
                        ),
                    )
                ),
                fmt_seconds(
                    mode_metric(
                        all_results[workload.label],
                        "auto_cache_context_validate",
                        "fasim_total_seconds",
                    )
                ),
                "yes"
                if all(
                    digest_matches_reference(all_results[workload.label], mode)
                    for mode in ["auto_cache_context", "auto_cache_context_validate"]
                )
                else "no",
                stable_digest(all_results[workload.label]["auto_cache"]),
                "yes" if context_calls(all_results[workload.label]) > 0 else "no",
            ]
            for workload in workload_list
        ],
    )
    lines.append("")

    append_table(
        lines,
        [
            "Workload",
            "Aligner s",
            "Align calls",
            "Context calls",
            "Hits",
            "Misses",
            "Hit rate",
            "Unique keys",
            "Query saved s",
            "Lookup saved s",
            "Validate overhead s",
        ],
        [
            [
                workload.label,
                fmt_seconds(
                    mode_metric(
                        all_results[workload.label],
                        "auto_cache_context",
                        "fasim_aligner_align_seconds",
                    )
                ),
                fmt_int(align_calls(all_results[workload.label])),
                fmt_int(
                    context_calls(all_results[workload.label])
                ),
                fmt_int(
                    mode_count(
                        all_results[workload.label],
                        "auto_cache_context",
                        "fasim_ssw_profile_context_hits",
                    )
                ),
                fmt_int(
                    mode_count(
                        all_results[workload.label],
                        "auto_cache_context",
                        "fasim_ssw_profile_context_misses",
                    )
                ),
                context_hit_rate(all_results[workload.label]),
                fmt_int(
                    mode_count(
                        all_results[workload.label],
                        "auto_cache_context",
                        "fasim_ssw_profile_context_unique_keys",
                    )
                ),
                fmt_seconds(
                    mode_metric(
                        all_results[workload.label],
                        "auto_cache_context",
                        "fasim_ssw_profile_context_query_translate_saved_seconds",
                    )
                ),
                fmt_seconds(
                    mode_metric(
                        all_results[workload.label],
                        "auto_cache_context",
                        "fasim_ssw_profile_context_lookup_saved_seconds",
                    )
                ),
                fmt_seconds(
                    mode_metric(
                        all_results[workload.label],
                        "auto_cache_context_validate",
                        "fasim_ssw_profile_context_validate_seconds",
                    )
                ),
            ]
            for workload in workload_list
        ],
    )
    lines.append("")

    append_table(
        lines,
        [
            "Workload",
            "Score mismatches",
            "Endpoint mismatches",
            "CIGAR mismatches",
            "Digest mismatches",
            "Fallbacks",
        ],
        [
            [
                workload.label,
                fmt_int(
                    mode_count(
                        all_results[workload.label],
                        "auto_cache_context_validate",
                        "fasim_ssw_profile_context_score_mismatches",
                    )
                ),
                fmt_int(
                    mode_count(
                        all_results[workload.label],
                        "auto_cache_context_validate",
                        "fasim_ssw_profile_context_endpoint_mismatches",
                    )
                ),
                fmt_int(
                    mode_count(
                        all_results[workload.label],
                        "auto_cache_context_validate",
                        "fasim_ssw_profile_context_cigar_mismatches",
                    )
                ),
                fmt_int(
                    mode_count(
                        all_results[workload.label],
                        "auto_cache_context_validate",
                        "fasim_ssw_profile_context_digest_mismatches",
                    )
                ),
                fmt_int(
                    mode_count(
                        all_results[workload.label],
                        "auto_cache_context_validate",
                        "fasim_ssw_profile_context_fallbacks",
                    )
                ),
            ]
            for workload in workload_list
        ],
    )
    lines.append("")

    clean = all(
        digest_matches_reference(all_results[workload.label], "auto_cache_context")
        and digest_matches_reference(all_results[workload.label], "auto_cache_context_validate")
        and records_match_reference(all_results[workload.label], "auto_cache_context")
        and records_match_reference(all_results[workload.label], "auto_cache_context_validate")
        and context_clean(all_results[workload.label], "auto_cache_context")
        and context_clean(all_results[workload.label], "auto_cache_context_validate")
        for workload in workload_list
    )
    active_workloads = [
        workload for workload in workload_list if context_calls(all_results[workload.label]) > 0
    ]
    inactive_workloads = [
        workload.label for workload in workload_list if context_calls(all_results[workload.label]) <= 0
    ]
    wins = [workload.label for workload in active_workloads if context_delta_seconds(all_results[workload.label]) > 0.0]
    losses = [
        workload.label for workload in active_workloads if context_delta_seconds(all_results[workload.label]) <= 0.0
    ]
    material_wins = [
        workload.label
        for workload in active_workloads
        if context_delta_seconds(all_results[workload.label]) >= 1.0
    ]
    lines.append("## Decision")
    lines.append("")
    if not clean:
        lines.append("Stop: at least one workload had digest, record, mismatch, or fallback telemetry.")
    elif not active_workloads:
        lines.append(
            "`FASIM_SSW_PROFILE_CONTEXT=1` was exact-clean, but no characterized "
            "workload exercised ProfileContext calls. Do not draw a performance conclusion."
        )
    elif losses:
        lines.append(
            "`FASIM_SSW_PROFILE_CONTEXT=1` is exact-clean, but median runtime was not "
            f"faster on {', '.join(losses)}. Keep it optional and do not promote it "
            "to the core recommended speed stack from this report."
        )
    elif material_wins:
        lines.append(
            "`FASIM_SSW_PROFILE_CONTEXT=1` is exact-clean and shows median wins on "
            f"{', '.join(wins)}. Treat it as an optional low-risk opt-in; keep the "
            "core recommended stack limited to transferString table + GPU AUTO + SSW profile cache "
            "unless broader workloads show larger wins."
        )
    else:
        lines.append(
            "`FASIM_SSW_PROFILE_CONTEXT=1` is exact-clean with only sub-1s median wins "
            "in this characterization. Keep it as an optional low-risk opt-in, not a "
            "strong recommended mode."
        )
    if inactive_workloads:
        lines.append("")
        lines.append(
            "Workloads without ProfileContext calls were excluded from the performance "
            f"decision: {', '.join(inactive_workloads)}."
        )
    lines.append("")

    lines.append("## Boundaries")
    lines.append("")
    lines.append("```text")
    lines.append("new optimization logic: no")
    lines.append("default enabled: no")
    lines.append("requires FASIM_SSW_PROFILE_CACHE=1: yes")
    lines.append("output semantic change: no")
    lines.append("scoring/threshold/non-overlap change: no")
    lines.append("GPU AUTO policy change: no")
    lines.append("SIM-close/recovery change: no")
    lines.append("Accelign real path change: no")
    lines.append("validation relaxation: no")
    lines.append("```")

    report = "\n".join(lines)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report + "\n", encoding="utf-8")
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cuda-bin", default=str(ROOT / "fasim_longtarget_cuda"))
    parser.add_argument("--synthetic-entries", default="1,8,32")
    parser.add_argument("--human-17kb-dna")
    parser.add_argument("--human-17kb-rna")
    parser.add_argument("--human-508kb-dna")
    parser.add_argument("--human-508kb-rna")
    parser.add_argument("--hg38-dna")
    parser.add_argument("--hg38-rna")
    parser.add_argument("--hg38-label", default="hg38_chr21_H19")
    parser.add_argument("--require-real", action="store_true")
    parser.add_argument("--require-hg38", action="store_true")
    parser.add_argument("--repeat", type=int, default=3)
    parser.add_argument("--force-auto-small", action="store_true")
    parser.add_argument(
        "--work-dir",
        default=str(ROOT / ".tmp" / "fasim_ssw_profile_context_characterization"),
    )
    parser.add_argument(
        "--output",
        default=str(ROOT / "docs" / "fasim_ssw_profile_context_characterization.md"),
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

    workloads = make_workloads(args)
    modes = make_modes(force_auto_small=args.force_auto_small)
    work_dir = Path(args.work_dir)
    if not work_dir.is_absolute():
        work_dir = (ROOT / work_dir).resolve()

    all_results: Dict[str, Dict[str, List[RunResult]]] = {}
    for workload in workloads:
        workload_results: Dict[str, List[RunResult]] = {}
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
            workload_results[mode.label] = runs
        all_results[workload.label] = workload_results

    if args.check:
        check_results(all_results)
    else:
        require_context_metrics(all_results)

    report = render_report(
        workloads=workloads,
        all_results=all_results,
        repeat=args.repeat,
        output_path=Path(args.output).resolve(),
    )
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
