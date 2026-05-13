#!/usr/bin/env python3
from __future__ import annotations

import argparse
import dataclasses
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
    print_window_generation_detail_table,
    read_expected_digest,
    validate_profile,
)


@dataclasses.dataclass(frozen=True)
class FixtureSpec:
    label: str
    dna_entries: int
    dna_repeat: int
    description: str


@dataclasses.dataclass(frozen=True)
class FixtureRun:
    spec: FixtureSpec
    metrics: Dict[str, str]
    digest: str
    records: int


REPRESENTATIVE_FIXTURES = [
    FixtureSpec(
        label="tiny",
        dna_entries=1,
        dna_repeat=1,
        description="current testDNA/H19 smoke fixture",
    ),
    FixtureSpec(
        label="medium_synthetic",
        dna_entries=8,
        dna_repeat=1,
        description="deterministic multi-record scale-up from testDNA/H19",
    ),
    FixtureSpec(
        label="window_heavy_synthetic",
        dna_entries=32,
        dna_repeat=1,
        description="deterministic window-heavy scale-up from testDNA/H19",
    ),
]

SMOKE_FIXTURES = [
    FixtureSpec(
        label="tiny",
        dna_entries=1,
        dna_repeat=1,
        description="current testDNA/H19 smoke fixture",
    ),
]


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


def format_seconds(value: float) -> str:
    return f"{value:.6f}"


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


def expected_digest_for(expected_dir: Optional[Path], label: str) -> Optional[str]:
    if expected_dir is None:
        return None
    path = expected_dir / f"{label}.digest"
    if not path.exists():
        raise RuntimeError(f"missing expected digest for {label}: {path}")
    return read_expected_digest(path)


def run_fixture_once(
    *,
    root: Path,
    bin_path: Path,
    spec: FixtureSpec,
    work_dir: Path,
    require_profile: bool,
) -> FixtureRun:
    if work_dir.exists():
        shutil.rmtree(work_dir)
    inputs_dir = work_dir / "inputs"
    output_dir = work_dir / "out"
    inputs_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    dna_filename = f"{spec.label}.fa"
    if spec.label == "tiny" and spec.dna_entries == 1 and spec.dna_repeat == 1:
        dna_filename = "testDNA.fa"
        shutil.copyfile(root / "testDNA.fa", inputs_dir / dna_filename)
    else:
        dna_sequence = read_fasta_sequence(root / "testDNA.fa")
        write_tiled_fasta(
            inputs_dir / dna_filename,
            sequence=dna_sequence,
            entries=spec.dna_entries,
            repeat=spec.dna_repeat,
        )
    shutil.copyfile(root / "H19.fa", inputs_dir / "H19.fa")

    env = os.environ.copy()
    env["FASIM_VERBOSE"] = "0"
    env["FASIM_OUTPUT_MODE"] = "lite"
    env["FASIM_PROFILE"] = "1"
    env["FASIM_EXTEND_THREADS"] = "1"

    proc = subprocess.run(
        [
            str(bin_path),
            "-f1",
            dna_filename,
            "-f2",
            "H19.fa",
            "-r",
            "1",
            "-O",
            str(output_dir),
        ],
        cwd=str(inputs_dir),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    (work_dir / "stdout.log").write_text(proc.stdout, encoding="utf-8")
    (work_dir / "stderr.log").write_text(proc.stderr, encoding="utf-8")
    if proc.returncode != 0:
        raise RuntimeError(f"{spec.label} failed with exit {proc.returncode}; see {work_dir / 'stderr.log'}")

    metrics = parse_benchmark_metrics(proc.stderr)
    if require_profile:
        validate_profile(metrics)
    records = canonical_lite_records(output_dir)
    digest = digest_records(records)
    return FixtureRun(spec=spec, metrics=metrics, digest=digest, records=len(records))


def run_fixture(
    *,
    root: Path,
    bin_path: Path,
    spec: FixtureSpec,
    work_dir_base: Path,
    repeat: int,
    require_profile: bool,
    expected_digest: Optional[str],
) -> FixtureRun:
    last_run: Optional[FixtureRun] = None
    first_digest = ""
    for index in range(repeat):
        work_dir = work_dir_base / spec.label / f"run{index + 1}"
        run = run_fixture_once(
            root=root,
            bin_path=bin_path,
            spec=spec,
            work_dir=work_dir,
            require_profile=require_profile,
        )
        if expected_digest is not None and run.digest != expected_digest:
            raise RuntimeError(
                f"{spec.label} digest mismatch: expected {expected_digest}, got {run.digest}"
            )
        if index == 0:
            first_digest = run.digest
        elif run.digest != first_digest:
            raise RuntimeError(
                f"{spec.label} digest changed across repeats: {first_digest} vs {run.digest}"
            )
        last_run = run
    if last_run is None:
        raise RuntimeError(f"{spec.label} did not run")
    return last_run


def print_stage_table(run: FixtureRun) -> None:
    metrics = run.metrics
    total = metric_float(metrics, "fasim_total_seconds")
    stages = [
        ("I/O", "fasim_io_seconds"),
        ("window generation", "fasim_window_generation_seconds"),
        ("DP scoring", "fasim_dp_scoring_seconds"),
        ("column max", "fasim_column_max_seconds"),
        ("local max", "fasim_local_max_seconds"),
        ("non-overlap", "fasim_nonoverlap_seconds"),
        ("validation", "fasim_validation_seconds"),
        ("output", "fasim_output_seconds"),
    ]
    print("| Stage | Seconds | Percent |")
    print("| --- | ---: | ---: |")
    for label, key in stages:
        seconds = metric_float(metrics, key)
        print(f"| {label} | {format_seconds(seconds)} | {percent(seconds, total):.2f}% |")


def print_amdahl_table(run: FixtureRun) -> None:
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
        fraction = metric_fraction(run.metrics, keys)
        values = [amdahl_speedup(fraction, speedup) for speedup in (5, 10, 20, 50)]
        print(
            f"| {label} ({fraction * 100.0:.2f}%) | "
            f"{values[0]:.3f}x | {values[1]:.3f}x | {values[2]:.3f}x | {values[3]:.3f}x |"
        )


def print_report(runs: List[FixtureRun]) -> None:
    print("# Fasim Representative Profile")
    print("")
    print("| Fixture | Entries | DNA repeat | Total seconds | Windows | DP cells | Candidates | Final hits | Digest |")
    print("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |")
    for run in runs:
        metrics = run.metrics
        print(
            f"| {run.spec.label} | {run.spec.dna_entries} | {run.spec.dna_repeat} | "
            f"{format_seconds(metric_float(metrics, 'fasim_total_seconds'))} | "
            f"{metrics.get('fasim_num_windows', '0')} | "
            f"{metrics.get('fasim_num_dp_cells', '0')} | "
            f"{metrics.get('fasim_num_candidates', '0')} | "
            f"{metrics.get('fasim_num_final_hits', '0')} | "
            f"{run.digest} |"
        )
    print("")
    for run in runs:
        print(f"## {run.spec.label}")
        print("")
        print(run.spec.description)
        print("")
        print_stage_table(run)
        print("")
        print_window_generation_detail_table(run.metrics)
        print("")
        print("Amdahl estimates:")
        print("")
        print_amdahl_table(run)
        print("")
        metrics = run.metrics
        total = metric_float(metrics, "fasim_total_seconds")
        dp = metric_float(metrics, "fasim_dp_scoring_seconds")
        column = metric_float(metrics, "fasim_column_max_seconds")
        local = metric_float(metrics, "fasim_local_max_seconds")
        print(f"benchmark.fasim_representative.{run.spec.label}.total_seconds={total}")
        print(f"benchmark.fasim_representative.{run.spec.label}.dp_scoring_percent={percent(dp, total):.6f}")
        print(f"benchmark.fasim_representative.{run.spec.label}.dp_column_percent={percent(dp + column, total):.6f}")
        print(f"benchmark.fasim_representative.{run.spec.label}.dp_column_local_percent={percent(dp + column + local, total):.6f}")
        print(f"benchmark.fasim_representative.{run.spec.label}.output_digest={run.digest}")
        print(f"benchmark.fasim_representative.{run.spec.label}.canonical_output_records={run.records}")
        for key, value in sorted(metrics.items()):
            print(f"benchmark.fasim_representative.{run.spec.label}.{key}={value}")
        print("")
    print(f"benchmark.fasim_representative.fixture_count={len(runs)}")


def fixtures_for(profile_set: str) -> List[FixtureSpec]:
    if profile_set == "representative":
        return REPRESENTATIVE_FIXTURES
    if profile_set == "smoke":
        return SMOKE_FIXTURES
    raise RuntimeError(f"unknown profile set: {profile_set}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bin", required=True)
    parser.add_argument("--profile-set", choices=("representative", "smoke"), default="representative")
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--require-profile", action="store_true")
    parser.add_argument("--expected-digest-dir")
    parser.add_argument("--work-dir", default=str(ROOT / ".tmp" / "fasim_representative_profile"))
    args = parser.parse_args()

    try:
        repeat = args.repeat if args.repeat > 0 else 1
        bin_path = Path(args.bin)
        if not bin_path.is_absolute():
            bin_path = (ROOT / bin_path).resolve()
        if not bin_path.exists():
            raise RuntimeError(f"missing Fasim binary: {bin_path}")
        expected_dir = Path(args.expected_digest_dir) if args.expected_digest_dir else None
        work_dir_base = Path(args.work_dir)
        runs: List[FixtureRun] = []
        for spec in fixtures_for(args.profile_set):
            run = run_fixture(
                root=ROOT,
                bin_path=bin_path,
                spec=spec,
                work_dir_base=work_dir_base,
                repeat=repeat,
                require_profile=args.require_profile,
                expected_digest=expected_digest_for(expected_dir, spec.label),
            )
            runs.append(run)
        print_report(runs)
        return 0
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
