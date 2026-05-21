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
    median_count,
    median_metric,
    run_once,
    stable_digest,
    stable_records,
)


ENDPOINT_ENVELOPE_KEYS = [
    "fasim_accelign_endpoint_envelope_shadow_enabled",
    "fasim_accelign_endpoint_envelope_shadow_requests",
    "fasim_accelign_endpoint_envelope_shadow_requests_compared",
    "fasim_accelign_endpoint_envelope_shadow_requests_unsupported",
    "fasim_accelign_endpoint_envelope_shadow_flank",
    "fasim_accelign_endpoint_envelope_shadow_score_mismatches",
    "fasim_accelign_endpoint_envelope_shadow_endpoint_mismatches",
    "fasim_accelign_endpoint_envelope_shadow_cigar_mismatches",
    "fasim_accelign_endpoint_envelope_shadow_alignment_string_mismatches",
    "fasim_accelign_endpoint_envelope_shadow_total_mismatches",
    "fasim_accelign_endpoint_envelope_shadow_contains_cpu_endpoint",
    "fasim_accelign_endpoint_envelope_shadow_misses_cpu_endpoint",
    "fasim_accelign_endpoint_envelope_shadow_contains_cpu_interval",
    "fasim_accelign_endpoint_envelope_shadow_misses_cpu_interval",
    "fasim_accelign_endpoint_envelope_shadow_accelign_seconds",
    "fasim_accelign_endpoint_envelope_shadow_cpu_full_seconds",
    "fasim_accelign_endpoint_envelope_shadow_cpu_envelope_seconds",
    "fasim_accelign_endpoint_envelope_shadow_net_est_seconds_saved",
    "fasim_accelign_endpoint_envelope_shadow_projected_full_saved",
    "fasim_accelign_endpoint_envelope_shadow_has_score_contract",
    "fasim_accelign_endpoint_envelope_shadow_has_endpoint_contract",
    "fasim_accelign_endpoint_envelope_shadow_has_cigar_contract",
    "fasim_accelign_endpoint_envelope_shadow_has_alignment_string_contract",
    "fasim_accelign_endpoint_envelope_shadow_uses_runtime_output",
]


def parse_int_list(value: str, *, allow_full: bool = False) -> List[int]:
    parsed: List[int] = []
    for item in value.split(","):
        item = item.strip()
        if not item:
            continue
        if allow_full and item.lower() == "full":
            parsed.append(0)
            continue
        number = int(item)
        if number < 0 or (number == 0 and not allow_full):
            raise RuntimeError(f"invalid list value: {item}")
        parsed.append(number)
    if not parsed:
        raise RuntimeError("empty integer list")
    return parsed


def sample_label(size: int) -> str:
    return "full" if size == 0 else str(size)


def sample_cap(size: int) -> str:
    return "2147483647" if size == 0 else str(size)


def mode_count(results: Dict[str, List[RunResult]], mode: str, key: str) -> int:
    return median_count(results[mode], key)


def mode_metric(results: Dict[str, List[RunResult]], mode: str, key: str) -> float:
    return median_metric(results[mode], key)


def require_endpoint_envelope_metrics(results: Dict[str, List[RunResult]], modes: List[str]) -> None:
    for mode in modes:
        for key in ENDPOINT_ENVELOPE_KEYS:
            mode_metric(results, mode, key)


def render_report(
    *,
    workload: WorkloadSpec,
    results: Dict[str, List[RunResult]],
    modes: List[str],
    repeat: int,
    output_path: Path,
) -> str:
    lines: List[str] = []
    lines.append("# Fasim Accelign Endpoint Envelope Shadow")
    lines.append("")
    lines.append(
        "This report characterizes a default-off research shadow for using "
        "Accelign endpoint output as an envelope hint, followed by CPU legacy "
        "traceback inside that envelope. CPU `aligner.Align` remains the runtime "
        "authority; the shadow never feeds Fasim output."
    )
    lines.append("")
    lines.append(
        "The shadow tests whether `Accelign ref_end +/- flank` covers the CPU "
        "legacy alignment interval and whether CPU traceback inside that smaller "
        "target window can reconstruct score, endpoints, and CIGAR."
    )
    lines.append("")
    lines.append(f"Workload: `{workload.label}`. Each mode uses {repeat} run(s); tables report medians.")
    lines.append("")

    baseline_rows = [
        [
            fmt_seconds(mode_metric(results, "table_only", "fasim_total_seconds")),
            fmt_seconds(mode_metric(results, "auto", "fasim_total_seconds")),
            "`" + stable_digest(results["table_only"]) + "`",
            str(stable_records(results["table_only"])),
            "yes" if stable_digest(results["auto"]) == stable_digest(results["table_only"]) else "no",
        ]
    ]
    lines.append("## Baseline")
    lines.append("")
    append_table(
        lines,
        ["Table seconds", "AUTO seconds", "Digest", "Records", "AUTO digest match"],
        baseline_rows,
    )
    lines.append("")

    rows: List[List[str]] = []
    for mode in modes:
        rows.append(
            [
                mode,
                fmt_int(mode_count(results, mode, "fasim_accelign_endpoint_envelope_shadow_flank")),
                fmt_int(mode_count(results, mode, "fasim_accelign_endpoint_envelope_shadow_requests")),
                fmt_int(mode_count(results, mode, "fasim_accelign_endpoint_envelope_shadow_requests_compared")),
                fmt_int(mode_count(results, mode, "fasim_accelign_endpoint_envelope_shadow_requests_unsupported")),
                fmt_int(mode_count(results, mode, "fasim_accelign_endpoint_envelope_shadow_contains_cpu_endpoint")),
                fmt_int(mode_count(results, mode, "fasim_accelign_endpoint_envelope_shadow_misses_cpu_endpoint")),
                fmt_int(mode_count(results, mode, "fasim_accelign_endpoint_envelope_shadow_contains_cpu_interval")),
                fmt_int(mode_count(results, mode, "fasim_accelign_endpoint_envelope_shadow_misses_cpu_interval")),
            ]
        )
    lines.append("## Envelope Coverage")
    lines.append("")
    append_table(
        lines,
        [
            "Mode",
            "Flank",
            "Requests",
            "Compared",
            "Unsupported",
            "Contains CPU endpoint",
            "Misses CPU endpoint",
            "Contains CPU interval",
            "Misses CPU interval",
        ],
        rows,
    )
    lines.append("")

    contract_rows: List[List[str]] = []
    for mode in modes:
        contract_rows.append(
            [
                mode,
                fmt_int(mode_count(results, mode, "fasim_accelign_endpoint_envelope_shadow_score_mismatches")),
                fmt_int(mode_count(results, mode, "fasim_accelign_endpoint_envelope_shadow_endpoint_mismatches")),
                fmt_int(mode_count(results, mode, "fasim_accelign_endpoint_envelope_shadow_cigar_mismatches")),
                fmt_int(mode_count(results, mode, "fasim_accelign_endpoint_envelope_shadow_total_mismatches")),
                str(mode_count(results, mode, "fasim_accelign_endpoint_envelope_shadow_uses_runtime_output")),
            ]
        )
    lines.append("## Contract")
    lines.append("")
    append_table(
        lines,
        ["Mode", "Score mismatches", "Endpoint mismatches", "CIGAR mismatches", "Total mismatches", "Uses output"],
        contract_rows,
    )
    lines.append("")

    timing_rows: List[List[str]] = []
    for mode in modes:
        timing_rows.append(
            [
                mode,
                fmt_seconds(mode_metric(results, mode, "fasim_accelign_endpoint_envelope_shadow_accelign_seconds")),
                fmt_seconds(mode_metric(results, mode, "fasim_accelign_endpoint_envelope_shadow_cpu_full_seconds")),
                fmt_seconds(mode_metric(results, mode, "fasim_accelign_endpoint_envelope_shadow_cpu_envelope_seconds")),
                fmt_seconds(mode_metric(results, mode, "fasim_accelign_endpoint_envelope_shadow_net_est_seconds_saved")),
                fmt_seconds(mode_metric(results, mode, "fasim_accelign_endpoint_envelope_shadow_projected_full_saved")),
            ]
        )
    lines.append("## Timing")
    lines.append("")
    append_table(
        lines,
        ["Mode", "Accelign seconds", "CPU full seconds", "CPU envelope seconds", "Net saved", "Projected full saved"],
        timing_rows,
    )
    lines.append("")

    largest_mode = modes[-1]
    misses_interval = mode_count(
        results, largest_mode, "fasim_accelign_endpoint_envelope_shadow_misses_cpu_interval"
    )
    total_mismatches = mode_count(
        results, largest_mode, "fasim_accelign_endpoint_envelope_shadow_total_mismatches"
    )
    net_saved = mode_metric(
        results, largest_mode, "fasim_accelign_endpoint_envelope_shadow_net_est_seconds_saved"
    )
    lines.append("## Decision")
    lines.append("")
    if misses_interval != 0:
        lines.append(
            "The Accelign-derived envelope missed at least one CPU legacy alignment "
            "interval. Do not use this as a real path with the current flank/policy."
        )
    elif total_mismatches != 0:
        lines.append(
            "The envelope covered CPU intervals, but CPU traceback inside the envelope "
            "did not reconstruct the full legacy contract. Debug interval construction "
            "or stop this path."
        )
    elif net_saved <= 0.0:
        lines.append(
            "The envelope contract is clean in this sample, but estimated net savings "
            "are not positive. Keep this as research shadow only."
        )
    else:
        lines.append(
            "The envelope covered CPU intervals, reconstructed the sampled contract, "
            "and showed positive net savings. Next work can expand samples and add "
            "candidate/output-level digest gates."
        )
    lines.append("")
    lines.append("## Boundaries")
    lines.append("")
    lines.append("```text")
    lines.append("use Accelign result for output: no")
    lines.append("skip CPU aligner.Align: no")
    lines.append("Accelign endpoint authority: no")
    lines.append("CPU legacy traceback remains authority: yes")
    lines.append("scoring/threshold/non-overlap change: no")
    lines.append("GPU DP column AUTO policy change: no")
    lines.append("validation relaxation: no")
    lines.append("SIM-close/recovery change: no")
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
    parser.add_argument("--sample-sizes", default="1000")
    parser.add_argument("--flanks", default="32,64,128")
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument(
        "--work-dir",
        default=str(ROOT / ".tmp" / "fasim_accelign_endpoint_envelope_shadow"),
    )
    parser.add_argument(
        "--output",
        default=str(ROOT / "docs" / "fasim_accelign_endpoint_envelope_shadow.md"),
    )
    parser.add_argument("--require-profile", action="store_true")
    parser.add_argument("--check", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.repeat <= 0:
        raise RuntimeError("--repeat must be positive")
    sample_sizes = parse_int_list(args.sample_sizes, allow_full=True)
    flanks = parse_int_list(args.flanks)

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
    envelope_modes: List[str] = []
    for size in sample_sizes:
        for flank in flanks:
            label = f"envelope_{sample_label(size)}_flank_{flank}"
            envelope_modes.append(label)
            modes.append(
                ModeSpec(
                    label,
                    "cuda",
                    {
                        "FASIM_TRANSFERSTRING_TABLE": "1",
                        "FASIM_GPU_DP_COLUMN_AUTO": "1",
                        "FASIM_GPU_DP_COLUMN_AUTO_MIN_WINDOWS": "1",
                        "FASIM_GPU_DP_COLUMN_AUTO_MIN_CELLS": "1",
                        "FASIM_ALIGNER_ACCELIGN_ENDPOINT_ENVELOPE_SHADOW": "1",
                        "FASIM_ALIGNER_ACCELIGN_ENDPOINT_ENVELOPE_SHADOW_MAX_REQUESTS": sample_cap(size),
                        "FASIM_ALIGNER_ACCELIGN_ENDPOINT_ENVELOPE_SHADOW_REQUEST_STRIDE": "1",
                        "FASIM_ALIGNER_ACCELIGN_ENDPOINT_ENVELOPE_SHADOW_FLANK": str(flank),
                    },
                )
            )

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

    require_endpoint_envelope_metrics(results, envelope_modes)
    for mode in envelope_modes:
        if stable_digest(results[mode]) != stable_digest(results["table_only"]):
            raise RuntimeError(f"{mode}: digest mismatch")
        if stable_records(results[mode]) != stable_records(results["table_only"]):
            raise RuntimeError(f"{mode}: record count mismatch")

    report = render_report(
        workload=workload,
        results=results,
        modes=envelope_modes,
        repeat=args.repeat,
        output_path=Path(args.output),
    )
    if args.check:
        for mode in envelope_modes:
            if mode_count(results, mode, "fasim_accelign_endpoint_envelope_shadow_enabled") != 1:
                raise RuntimeError(f"{mode}: endpoint-envelope shadow was not enabled")
            if mode_count(results, mode, "fasim_accelign_endpoint_envelope_shadow_requests_compared") <= 0:
                raise RuntimeError(f"{mode}: no endpoint-envelope requests compared")
            if mode_count(results, mode, "fasim_accelign_endpoint_envelope_shadow_uses_runtime_output") != 0:
                raise RuntimeError(f"{mode}: endpoint-envelope shadow used runtime output")
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
