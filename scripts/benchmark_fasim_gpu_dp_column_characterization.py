#!/usr/bin/env python3
from __future__ import annotations

import argparse
import dataclasses
import os
from pathlib import Path
import shutil
import statistics
import subprocess
import sys
from typing import Dict, Iterable, List, Optional


ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from benchmark_fasim_profile import (  # noqa: E402
    canonical_lite_records,
    digest_records,
    metric_float,
    parse_benchmark_metrics,
    validate_profile,
)


STAGE_KEYS = [
    "fasim_total_seconds",
    "fasim_window_generation_seconds",
    "fasim_transfer_string_seconds",
    "fasim_dp_scoring_seconds",
    "fasim_column_max_seconds",
    "fasim_local_max_seconds",
    "fasim_nonoverlap_seconds",
    "fasim_output_seconds",
]

GPU_KEYS = [
    "fasim_gpu_dp_column_active",
    "fasim_gpu_dp_column_calls",
    "fasim_gpu_dp_column_windows",
    "fasim_gpu_dp_column_cells",
    "fasim_gpu_dp_column_h2d_bytes",
    "fasim_gpu_dp_column_d2h_bytes",
    "fasim_gpu_dp_column_kernel_seconds",
    "fasim_gpu_dp_column_total_seconds",
    "fasim_gpu_dp_column_validate_seconds",
    "fasim_gpu_dp_column_score_mismatches",
    "fasim_gpu_dp_column_column_max_mismatches",
    "fasim_gpu_dp_column_fallbacks",
]

REPORT_KEYS = STAGE_KEYS + GPU_KEYS


@dataclasses.dataclass(frozen=True)
class ModeSpec:
    label: str
    bin_kind: str
    env: Dict[str, str]


@dataclasses.dataclass(frozen=True)
class WorkloadSpec:
    label: str
    description: str
    dna_entries: int = 0
    dna_repeat: int = 1
    dna_path: Optional[Path] = None
    rna_path: Optional[Path] = None


@dataclasses.dataclass(frozen=True)
class RunResult:
    metrics: Dict[str, str]
    digest: str
    records: int


def read_fasta_sequence(path: Path) -> str:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    sequence = "".join(line.strip() for line in lines if line and not line.startswith(">"))
    if not sequence:
        raise RuntimeError(f"empty fasta sequence: {path}")
    return sequence


def write_tiled_fasta(path: Path, *, sequence: str, entries: int, repeat: int) -> None:
    if entries <= 0:
        raise RuntimeError("entries must be > 0")
    if repeat <= 0:
        raise RuntimeError("repeat must be > 0")
    tiled = sequence * repeat
    with path.open("w", encoding="utf-8") as handle:
        for index in range(entries):
            start = index * len(tiled) + 1
            end = start + len(tiled) - 1
            handle.write(f">hg19|chr11|{start}-{end}\n")
            handle.write(tiled)
            handle.write("\n")


def copy_input(src: Path, dst: Path) -> None:
    if not src.exists():
        raise RuntimeError(f"missing input: {src}")
    if src.suffix == ".gz":
        raise RuntimeError(f"compressed FASTA is not supported: {src}")
    shutil.copyfile(src, dst)


def prepare_inputs(workload: WorkloadSpec, work_dir: Path) -> tuple[str, str]:
    inputs_dir = work_dir / "inputs"
    inputs_dir.mkdir(parents=True, exist_ok=True)
    if workload.dna_path is not None and workload.rna_path is not None:
        dna_name = workload.dna_path.name
        rna_name = workload.rna_path.name
        copy_input(workload.dna_path, inputs_dir / dna_name)
        copy_input(workload.rna_path, inputs_dir / rna_name)
        return dna_name, rna_name

    dna_name = f"{workload.label}.fa"
    if workload.label == "tiny" and workload.dna_entries == 1 and workload.dna_repeat == 1:
        dna_name = "testDNA.fa"
        shutil.copyfile(ROOT / "testDNA.fa", inputs_dir / dna_name)
    else:
        dna_sequence = read_fasta_sequence(ROOT / "testDNA.fa")
        write_tiled_fasta(
            inputs_dir / dna_name,
            sequence=dna_sequence,
            entries=workload.dna_entries,
            repeat=workload.dna_repeat,
        )
    shutil.copyfile(ROOT / "H19.fa", inputs_dir / "H19.fa")
    return dna_name, "H19.fa"


def run_once(
    *,
    workload: WorkloadSpec,
    mode: ModeSpec,
    bin_path: Path,
    work_dir: Path,
    require_profile: bool,
) -> RunResult:
    if work_dir.exists():
        shutil.rmtree(work_dir)
    output_dir = work_dir / "out"
    output_dir.mkdir(parents=True, exist_ok=True)
    dna_name, rna_name = prepare_inputs(workload, work_dir)

    env = os.environ.copy()
    env["FASIM_VERBOSE"] = "0"
    env["FASIM_OUTPUT_MODE"] = "lite"
    env["FASIM_PROFILE"] = "1"
    env["FASIM_EXTEND_THREADS"] = "1"
    env.update(mode.env)

    proc = subprocess.run(
        [
            str(bin_path),
            "-f1",
            dna_name,
            "-f2",
            rna_name,
            "-r",
            "1",
            "-O",
            str(output_dir),
        ],
        cwd=str(work_dir / "inputs"),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    (work_dir / "stdout.log").write_text(proc.stdout, encoding="utf-8")
    (work_dir / "stderr.log").write_text(proc.stderr, encoding="utf-8")
    if proc.returncode != 0:
        raise RuntimeError(
            f"{workload.label}/{mode.label} failed with exit {proc.returncode}; "
            f"see {work_dir / 'stderr.log'}"
        )
    metrics = parse_benchmark_metrics(proc.stderr)
    if require_profile:
        validate_profile(metrics)
    records = canonical_lite_records(output_dir)
    return RunResult(metrics=metrics, digest=digest_records(records), records=len(records))


def median_metric(runs: List[RunResult], key: str) -> float:
    return statistics.median(metric_float(run.metrics, key) for run in runs)


def median_count(runs: List[RunResult], key: str) -> int:
    return int(round(median_metric(runs, key)))


def speedup(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator > 0 else 0.0


def fmt_seconds(value: float) -> str:
    return f"{value:.6f}"


def fmt_speedup(value: float) -> str:
    return f"{value:.2f}x" if value > 0 else "n/a"


def fmt_int(value: int) -> str:
    return f"{value:,}"


def stable_digest(runs: List[RunResult]) -> str:
    digests = {run.digest for run in runs}
    if len(digests) != 1:
        raise RuntimeError(f"digest changed across runs: {sorted(digests)}")
    return runs[0].digest


def stable_records(runs: List[RunResult]) -> int:
    records = {run.records for run in runs}
    if len(records) != 1:
        raise RuntimeError(f"record count changed across runs: {sorted(records)}")
    return runs[0].records


def append_table(lines: List[str], headers: List[str], rows: Iterable[List[str]]) -> None:
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join("---" for _ in headers) + " |")
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")


def render_report(
    *,
    results: Dict[str, Dict[str, List[RunResult]]],
    workloads: List[WorkloadSpec],
    modes: List[ModeSpec],
    repeat: int,
    output_path: Path,
) -> str:
    lines: List[str] = []
    lines.append("# Fasim GPU DP+column Characterization")
    lines.append("")
    lines.append("Base branch:")
    lines.append("")
    lines.append("```text")
    lines.append("fasim-gpu-dp-column-prototype")
    lines.append("```")
    lines.append("")
    lines.append(
        "This stacked PR characterizes the default-off `FASIM_GPU_DP_COLUMN=1` "
        "prototype with repeated median A/B runs. It does not add optimization "
        "code, change output authority, or change scoring/threshold/non-overlap behavior."
    )
    lines.append("")
    lines.append(f"Each workload/mode uses {repeat} runs. Tables report medians.")
    lines.append("")
    lines.append("## Modes")
    lines.append("")
    append_table(
        lines,
        ["Mode", "Binary", "Environment"],
        [
            [mode.label, mode.bin_kind, "`" + " ".join(f"{k}={v}" for k, v in mode.env.items()) + "`"]
            for mode in modes
        ],
    )
    lines.append("")
    lines.append("## Median Summary")
    lines.append("")
    rows: List[List[str]] = []
    for workload in workloads:
        legacy_total = median_metric(results[workload.label]["legacy"], "fasim_total_seconds")
        table_total = median_metric(results[workload.label]["table"], "fasim_total_seconds")
        for mode in modes:
            runs = results[workload.label][mode.label]
            total = median_metric(runs, "fasim_total_seconds")
            rows.append(
                [
                    workload.label,
                    mode.label,
                    fmt_seconds(total),
                    fmt_speedup(speedup(legacy_total, total)),
                    fmt_speedup(speedup(table_total, total)),
                    fmt_seconds(median_metric(runs, "fasim_window_generation_seconds")),
                    fmt_seconds(median_metric(runs, "fasim_transfer_string_seconds")),
                    fmt_seconds(median_metric(runs, "fasim_dp_scoring_seconds")),
                    fmt_seconds(median_metric(runs, "fasim_column_max_seconds")),
                    fmt_seconds(median_metric(runs, "fasim_output_seconds")),
                ]
            )
    append_table(
        lines,
        [
            "Workload",
            "Mode",
            "Total seconds",
            "vs legacy",
            "vs table",
            "Window gen",
            "transferString",
            "DP",
            "Column",
            "Output",
        ],
        rows,
    )
    lines.append("")
    lines.append("## GPU Cost Summary")
    lines.append("")
    rows = []
    for workload in workloads:
        for mode_label in ("gpu", "gpu_validate"):
            runs = results[workload.label][mode_label]
            rows.append(
                [
                    workload.label,
                    mode_label,
                    str(median_count(runs, "fasim_gpu_dp_column_active")),
                    str(median_count(runs, "fasim_gpu_dp_column_calls")),
                    fmt_int(median_count(runs, "fasim_gpu_dp_column_windows")),
                    fmt_int(median_count(runs, "fasim_gpu_dp_column_cells")),
                    fmt_int(median_count(runs, "fasim_gpu_dp_column_h2d_bytes")),
                    fmt_int(median_count(runs, "fasim_gpu_dp_column_d2h_bytes")),
                    fmt_seconds(median_metric(runs, "fasim_gpu_dp_column_kernel_seconds")),
                    fmt_seconds(median_metric(runs, "fasim_gpu_dp_column_total_seconds")),
                    fmt_seconds(median_metric(runs, "fasim_gpu_dp_column_validate_seconds")),
                    str(median_count(runs, "fasim_gpu_dp_column_score_mismatches")),
                    str(median_count(runs, "fasim_gpu_dp_column_column_max_mismatches")),
                    str(median_count(runs, "fasim_gpu_dp_column_fallbacks")),
                ]
            )
    append_table(
        lines,
        [
            "Workload",
            "Mode",
            "Active",
            "Calls",
            "Windows",
            "Cells",
            "H2D bytes",
            "D2H bytes",
            "Kernel seconds",
            "GPU total seconds",
            "Validate seconds",
            "Score mismatches",
            "Column mismatches",
            "Fallbacks",
        ],
        rows,
    )
    lines.append("")
    lines.append("## Digest Stability")
    lines.append("")
    rows = []
    for workload in workloads:
        reference_digest = ""
        for mode in modes:
            runs = results[workload.label][mode.label]
            digest = stable_digest(runs)
            records = stable_records(runs)
            if not reference_digest:
                reference_digest = digest
            rows.append(
                [
                    workload.label,
                    mode.label,
                    "`" + digest + "`",
                    str(records),
                    "yes" if digest == reference_digest else "no",
                ]
            )
    append_table(lines, ["Workload", "Mode", "Digest", "Records", "Matches legacy"], rows)
    lines.append("")
    lines.append("## Cost Breakdown Gap")
    lines.append("")
    lines.append(
        "The current prototype reports H2D/D2H byte counts plus GPU kernel and GPU "
        "batch wall seconds. It does not yet expose separate CUDA init seconds, "
        "H2D seconds, D2H seconds, or CPU extension seconds. Those are the next "
        "diagnostic targets if the GPU path remains a performance candidate."
    )
    lines.append("")
    any_mismatch = any(
        median_count(results[w.label][m], key) != 0
        for w in workloads
        for m in ("gpu", "gpu_validate")
        for key in (
            "fasim_gpu_dp_column_score_mismatches",
            "fasim_gpu_dp_column_column_max_mismatches",
            "fasim_gpu_dp_column_fallbacks",
        )
    )
    if any_mismatch:
        lines.append("## Validation Finding")
        lines.append("")
        lines.append(
            "`FASIM_GPU_DP_COLUMN_VALIDATE=1` found GPU-vs-CPU DP/column "
            "mismatches or fallbacks on at least one workload."
        )
        lines.append("")
        rows = []
        for workload in workloads:
            runs = results[workload.label]["gpu_validate"]
            rows.append(
                [
                    workload.label,
                    str(median_count(runs, "fasim_gpu_dp_column_score_mismatches")),
                    str(median_count(runs, "fasim_gpu_dp_column_column_max_mismatches")),
                    str(median_count(runs, "fasim_gpu_dp_column_fallbacks")),
                ]
            )
        append_table(
            lines,
            ["Workload", "Score mismatches", "Column mismatches", "Fallbacks"],
            rows,
        )
        lines.append("")
        lines.append(
            "Final digests remain stable because the prototype falls back to the "
            "CPU/Fasim authority, but this is not clean enough for any recommended "
            "opt-in claim."
        )
        lines.append("")
    lines.append("## Decision")
    lines.append("")
    if any_mismatch:
        decision = (
            "Correctness is not clean under validation. Stop performance work and "
            "debug GPU-vs-CPU DP/column mismatches before any opt-in recommendation."
        )
    else:
        gpu_wins = []
        for workload in workloads:
            table_total = median_metric(results[workload.label]["table"], "fasim_total_seconds")
            gpu_total = median_metric(results[workload.label]["gpu"], "fasim_total_seconds")
            if gpu_total < table_total:
                gpu_wins.append(workload.label)
        if gpu_wins:
            decision = (
                "`FASIM_GPU_DP_COLUMN=1` is a size/workload-sensitive performance "
                f"candidate on: {', '.join(gpu_wins)}. Next step is to split CUDA "
                "init, transfer, kernel, and CPU extension costs before recommending it."
            )
        else:
            decision = (
                "`FASIM_GPU_DP_COLUMN=1` did not beat table-only medians in this "
                "characterization. Keep it as a correctness prototype and focus next "
                "on overhead breakdown or alternate filters before recommending it."
            )
    lines.append(decision)
    lines.append("")
    lines.append("Forbidden-scope check:")
    lines.append("")
    lines.append("```text")
    lines.append("default enablement: no")
    lines.append("scoring/threshold/non-overlap/output change: no")
    lines.append("new filter/full CUDA rewrite: no")
    lines.append("digest relaxation: no")
    lines.append("```")
    lines.append("")

    report = "\n".join(lines)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report + "\n", encoding="utf-8")
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--x86-bin", default=str(ROOT / "fasim_longtarget_x86"))
    parser.add_argument("--cuda-bin", default=str(ROOT / "fasim_longtarget_cuda"))
    parser.add_argument("--repeat", type=int, default=5)
    parser.add_argument("--work-dir", default=str(ROOT / ".tmp" / "fasim_gpu_dp_column_characterization"))
    parser.add_argument("--output", default=str(ROOT / "docs" / "fasim_gpu_dp_column_characterization.md"))
    parser.add_argument("--human-17kb-dna")
    parser.add_argument("--human-17kb-rna")
    parser.add_argument("--human-508kb-dna")
    parser.add_argument("--human-508kb-rna")
    parser.add_argument("--require-human", action="store_true")
    parser.add_argument("--require-profile", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        repeat = args.repeat if args.repeat > 0 else 1
        x86_bin = Path(args.x86_bin).resolve()
        cuda_bin = Path(args.cuda_bin).resolve()
        if not x86_bin.exists():
            raise RuntimeError(f"missing x86 binary: {x86_bin}")
        if not cuda_bin.exists():
            raise RuntimeError(f"missing CUDA binary: {cuda_bin}")

        workloads = [
            WorkloadSpec("tiny", "current testDNA/H19 smoke fixture", dna_entries=1),
            WorkloadSpec("medium_synthetic", "8-entry deterministic testDNA/H19 scale-up", dna_entries=8),
            WorkloadSpec("window_heavy_synthetic", "32-entry deterministic testDNA/H19 scale-up", dna_entries=32),
        ]
        human_pairs = [
            ("human_lnc_atlas_17kb_target", args.human_17kb_dna, args.human_17kb_rna),
            ("human_lnc_atlas_508kb_target", args.human_508kb_dna, args.human_508kb_rna),
        ]
        for label, dna, rna in human_pairs:
            if dna and rna:
                workloads.append(
                    WorkloadSpec(
                        label=label,
                        description="local humanLncAtlas FASTA copied from earlier profiling worktree",
                        dna_path=Path(dna).resolve(),
                        rna_path=Path(rna).resolve(),
                    )
                )
            elif args.require_human:
                raise RuntimeError(f"missing required human workload paths for {label}")

        modes = [
            ModeSpec("legacy", "x86", {}),
            ModeSpec("table", "x86", {"FASIM_TRANSFERSTRING_TABLE": "1"}),
            ModeSpec(
                "gpu",
                "cuda",
                {"FASIM_TRANSFERSTRING_TABLE": "1", "FASIM_GPU_DP_COLUMN": "1"},
            ),
            ModeSpec(
                "gpu_validate",
                "cuda",
                {
                    "FASIM_TRANSFERSTRING_TABLE": "1",
                    "FASIM_GPU_DP_COLUMN": "1",
                    "FASIM_GPU_DP_COLUMN_VALIDATE": "1",
                },
            ),
        ]

        work_dir_base = Path(args.work_dir)
        results: Dict[str, Dict[str, List[RunResult]]] = {}
        for workload in workloads:
            results[workload.label] = {}
            reference_digest = ""
            for mode in modes:
                bin_path = cuda_bin if mode.bin_kind == "cuda" else x86_bin
                runs: List[RunResult] = []
                for run_index in range(repeat):
                    run = run_once(
                        workload=workload,
                        mode=mode,
                        bin_path=bin_path,
                        work_dir=work_dir_base / workload.label / mode.label / f"run{run_index + 1}",
                        require_profile=args.require_profile,
                    )
                    runs.append(run)
                digest = stable_digest(runs)
                if not reference_digest:
                    reference_digest = digest
                elif digest != reference_digest:
                    raise RuntimeError(
                        f"{workload.label}/{mode.label} digest mismatch: "
                        f"expected {reference_digest}, got {digest}"
                    )
                results[workload.label][mode.label] = runs

        report = render_report(
            results=results,
            workloads=workloads,
            modes=modes,
            repeat=repeat,
            output_path=Path(args.output),
        )
        print(report)
        return 0
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
