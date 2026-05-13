#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
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
    print_transfer_string_detail_table,
    print_window_generation_detail_table,
    read_expected_digest,
    validate_profile,
)


STAGE_KEYS = [
    ("I/O", "fasim_io_seconds"),
    ("window generation", "fasim_window_generation_seconds"),
    ("DP scoring", "fasim_dp_scoring_seconds"),
    ("column max", "fasim_column_max_seconds"),
    ("local max", "fasim_local_max_seconds"),
    ("non-overlap", "fasim_nonoverlap_seconds"),
    ("validation", "fasim_validation_seconds"),
    ("output", "fasim_output_seconds"),
]


def percent(part: float, total: float) -> float:
    return (part / total * 100.0) if total > 0 else 0.0


def amdahl_speedup(fraction: float, speedup: int) -> float:
    if fraction <= 0:
        return 1.0
    return 1.0 / ((1.0 - fraction) + (fraction / float(speedup)))


def metric_fraction(metrics: Dict[str, str], keys: Iterable[str]) -> float:
    total = metric_float(metrics, "fasim_total_seconds")
    accelerated = sum(metric_float(metrics, key) for key in keys)
    return accelerated / total if total > 0 else 0.0


def copy_input(src: Path, dst: Path) -> None:
    if not src.exists():
        raise RuntimeError(f"missing input: {src}")
    if src.suffix == ".gz":
        raise RuntimeError(f"compressed FASTA is not supported by this runner: {src}")
    shutil.copyfile(src, dst)


def run_once(
    *,
    bin_path: Path,
    dna_path: Path,
    rna_path: Path,
    label: str,
    work_dir: Path,
    rule: int,
    strand: Optional[int],
    require_profile: bool,
) -> tuple[Dict[str, str], str, int]:
    if work_dir.exists():
        shutil.rmtree(work_dir)
    input_dir = work_dir / "inputs"
    output_dir = work_dir / "out"
    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    dna_name = dna_path.name
    rna_name = rna_path.name
    copy_input(dna_path, input_dir / dna_name)
    copy_input(rna_path, input_dir / rna_name)

    env = os.environ.copy()
    env["FASIM_VERBOSE"] = "0"
    env["FASIM_OUTPUT_MODE"] = "lite"
    env["FASIM_PROFILE"] = "1"
    env["FASIM_EXTEND_THREADS"] = "1"

    cmd = [
        str(bin_path),
        "-f1",
        dna_name,
        "-f2",
        rna_name,
        "-r",
        str(rule),
        "-O",
        str(output_dir),
    ]
    if strand is not None:
        cmd.extend(["-t", str(strand)])

    proc = subprocess.run(
        cmd,
        cwd=str(input_dir),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    (work_dir / "stdout.log").write_text(proc.stdout, encoding="utf-8")
    (work_dir / "stderr.log").write_text(proc.stderr, encoding="utf-8")
    (work_dir / "command.txt").write_text(" ".join(cmd) + "\n", encoding="utf-8")
    if proc.returncode != 0:
        raise RuntimeError(f"{label} failed with exit {proc.returncode}; see {work_dir / 'stderr.log'}")

    metrics = parse_benchmark_metrics(proc.stderr)
    if require_profile:
        validate_profile(metrics)
    records = canonical_lite_records(output_dir)
    digest = digest_records(records)
    return metrics, digest, len(records)


def print_stage_table(metrics: Dict[str, str]) -> None:
    total = metric_float(metrics, "fasim_total_seconds")
    print("| Stage | Seconds | Percent |")
    print("| --- | ---: | ---: |")
    for label, key in STAGE_KEYS:
        seconds = metric_float(metrics, key)
        print(f"| {label} | {seconds:.6f} | {percent(seconds, total):.2f}% |")


def print_amdahl_table(metrics: Dict[str, str]) -> None:
    fractions = [
        ("DP only", ["fasim_dp_scoring_seconds"]),
        ("DP + column", ["fasim_dp_scoring_seconds", "fasim_column_max_seconds"]),
        (
            "DP + column + local",
            [
                "fasim_dp_scoring_seconds",
                "fasim_column_max_seconds",
                "fasim_local_max_seconds",
            ],
        ),
    ]
    print("| Accelerated fraction | 5x | 10x | 20x | 50x |")
    print("| --- | ---: | ---: | ---: | ---: |")
    for label, keys in fractions:
        fraction = metric_fraction(metrics, keys)
        values = [amdahl_speedup(fraction, speedup) for speedup in (5, 10, 20, 50)]
        print(
            f"| {label} ({fraction * 100.0:.2f}%) | "
            f"{values[0]:.3f}x | {values[1]:.3f}x | {values[2]:.3f}x | {values[3]:.3f}x |"
        )


def print_report(
    *,
    label: str,
    dna_path: Path,
    rna_path: Path,
    metrics: Dict[str, str],
    digest: str,
    record_count: int,
) -> None:
    total = metric_float(metrics, "fasim_total_seconds")
    dp = metric_float(metrics, "fasim_dp_scoring_seconds")
    column = metric_float(metrics, "fasim_column_max_seconds")
    local = metric_float(metrics, "fasim_local_max_seconds")
    print("# Fasim Real-Corpus Profile")
    print("")
    print(f"label: {label}")
    print(f"dna: {dna_path}")
    print(f"rna: {rna_path}")
    print(f"canonical output digest: {digest}")
    print(f"canonical output records: {record_count}")
    print("")
    print("| Metric | Value |")
    print("| --- | ---: |")
    for key in [
        "fasim_total_seconds",
        "fasim_num_queries",
        "fasim_num_windows",
        "fasim_num_dp_cells",
        "fasim_num_candidates",
        "fasim_num_validated_candidates",
        "fasim_num_final_hits",
    ]:
        print(f"| {key} | {metrics.get(key, '0')} |")
    print("")
    print_stage_table(metrics)
    print("")
    print_window_generation_detail_table(metrics)
    print("")
    print_transfer_string_detail_table(metrics)
    print("")
    print(f"DP/scoring percentage: {percent(dp, total):.2f}%")
    print(f"DP+column percentage: {percent(dp + column, total):.2f}%")
    print(f"DP+column+local percentage: {percent(dp + column + local, total):.2f}%")
    print("")
    print_amdahl_table(metrics)
    print("")
    print(f"benchmark.fasim_real_corpus.{label}.output_digest={digest}")
    print(f"benchmark.fasim_real_corpus.{label}.canonical_output_records={record_count}")
    print(f"benchmark.fasim_real_corpus.{label}.dp_scoring_percent={percent(dp, total):.6f}")
    print(f"benchmark.fasim_real_corpus.{label}.dp_column_percent={percent(dp + column, total):.6f}")
    print(f"benchmark.fasim_real_corpus.{label}.dp_column_local_percent={percent(dp + column + local, total):.6f}")
    for key, value in sorted(metrics.items()):
        print(f"benchmark.fasim_real_corpus.{label}.{key}={value}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bin", required=True)
    parser.add_argument("--dna", required=True)
    parser.add_argument("--rna", required=True)
    parser.add_argument("--label", default="real_corpus")
    parser.add_argument("--rule", type=int, default=1)
    parser.add_argument("--strand", type=int)
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--require-profile", action="store_true")
    parser.add_argument("--expected-digest-file")
    parser.add_argument("--work-dir", default=str(ROOT / ".tmp" / "fasim_real_corpus_profile"))
    args = parser.parse_args()

    try:
        bin_path = Path(args.bin)
        if not bin_path.is_absolute():
            bin_path = (ROOT / bin_path).resolve()
        if not bin_path.exists():
            raise RuntimeError(f"missing Fasim binary: {bin_path}")
        dna_path = Path(args.dna).resolve()
        rna_path = Path(args.rna).resolve()
        expected_digest = read_expected_digest(Path(args.expected_digest_file)) if args.expected_digest_file else None
        repeat = args.repeat if args.repeat > 0 else 1
        work_dir_base = Path(args.work_dir)

        first_digest = ""
        last_metrics: Dict[str, str] = {}
        last_digest = ""
        last_record_count = 0
        for index in range(repeat):
            metrics, digest, record_count = run_once(
                bin_path=bin_path,
                dna_path=dna_path,
                rna_path=rna_path,
                label=args.label,
                work_dir=work_dir_base / f"run{index + 1}",
                rule=args.rule,
                strand=args.strand,
                require_profile=args.require_profile,
            )
            if expected_digest is not None and digest != expected_digest:
                raise RuntimeError(f"digest mismatch: expected {expected_digest}, got {digest}")
            if index == 0:
                first_digest = digest
            elif digest != first_digest:
                raise RuntimeError(f"digest changed across repeats: {first_digest} vs {digest}")
            last_metrics = metrics
            last_digest = digest
            last_record_count = record_count

        print_report(
            label=args.label,
            dna_path=dna_path,
            rna_path=rna_path,
            metrics=last_metrics,
            digest=last_digest,
            record_count=last_record_count,
        )
        return 0
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
