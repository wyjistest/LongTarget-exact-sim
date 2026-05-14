#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import dataclasses
from pathlib import Path
import os
import re
import shutil
import statistics
import subprocess
import sys
import time
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple


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
from benchmark_fasim_sim_gap_taxonomy import (  # noqa: E402
    ExecutorShadow,
    GapRecord,
    LITE_HEADER,
    ModeRun,
    RecoveryBox,
    SequenceEntry,
    TriplexRecord,
    build_sim_recovery_real_mode,
    classify_sim_only_record,
    expand_interval,
    index_by_family,
    merge_recovery_boxes,
    parse_genomic_header,
    parse_lite_records,
    read_fasta_entries,
    run_executor_box,
)


LABEL_RE = re.compile(r"^[A-Za-z0-9_]+$")


@dataclasses.dataclass(frozen=True)
class CaseSpec:
    label: str
    dna_path: Path
    rna_path: Path
    validate: bool


@dataclasses.dataclass(frozen=True)
class CaseRun:
    index: int
    fast: ModeRun
    fast_wall_seconds: float
    sim_close: object
    sim_close_wall_seconds: float
    validate_mode: Optional[object]
    validate_wall_seconds: float
    validation_coverage: "ValidationCoverage"


@dataclasses.dataclass(frozen=True)
class CaseSummary:
    spec: CaseSpec
    runs: List[CaseRun]


@dataclasses.dataclass(frozen=True)
class ValidationCoverage:
    requested: bool
    supported: bool
    unsupported_reason: str
    supported_records: int
    sim_records: int
    sim_close_records: int
    shared_records: int
    sim_only_records: int
    sim_close_extra_records: int


def ensure_label(label: str) -> str:
    if not LABEL_RE.match(label):
        raise RuntimeError(f"case label must match {LABEL_RE.pattern}: {label}")
    return label


def copy_input(src: Path, dst: Path) -> None:
    if not src.exists():
        raise RuntimeError(f"missing input: {src}")
    if src.suffix == ".gz":
        raise RuntimeError(f"compressed FASTA is not supported by this runner: {src}")
    shutil.copyfile(src, dst)


def sequence_entries_from_fasta(path: Path) -> List[SequenceEntry]:
    entries: List[SequenceEntry] = []
    for header, sequence in read_fasta_entries(path):
        chr_name, start, end = parse_genomic_header(header)
        expected_length = end - start + 1
        if expected_length != len(sequence):
            raise RuntimeError(
                f"FASTA interval length mismatch for {path}: "
                f"{header} spans {expected_length}, sequence has {len(sequence)}"
            )
        entries.append(SequenceEntry(chr_name=chr_name, start=start, end=end, sequence=sequence))
    return entries


def query_sequence_from_fasta(path: Path) -> str:
    entries = read_fasta_entries(path)
    if len(entries) != 1:
        raise RuntimeError(f"SIM-close local recovery currently expects one RNA entry: {path}")
    return entries[0][1]


def full_search_cells(dna_entries: Sequence[SequenceEntry], query_sequence: str) -> int:
    return sum(len(entry.sequence) for entry in dna_entries) * len(query_sequence)


def clean_env() -> Dict[str, str]:
    env = os.environ.copy()
    env["FASIM_VERBOSE"] = "0"
    env["FASIM_OUTPUT_MODE"] = "lite"
    env["FASIM_PROFILE"] = "1"
    env["FASIM_EXTEND_THREADS"] = "1"
    env.pop("FASIM_SIM_RECOVERY", None)
    env.pop("FASIM_SIM_RECOVERY_VALIDATE", None)
    return env


def run_fasim_mode(
    *,
    bin_path: Path,
    spec: CaseSpec,
    mode: str,
    work_dir: Path,
    require_profile: bool,
) -> Tuple[ModeRun, float]:
    if work_dir.exists():
        shutil.rmtree(work_dir)
    input_dir = work_dir / "inputs"
    output_dir = work_dir / "out"
    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    dna_name = spec.dna_path.name
    rna_name = spec.rna_path.name
    copy_input(spec.dna_path, input_dir / dna_name)
    copy_input(spec.rna_path, input_dir / rna_name)

    cmd = [
        str(bin_path),
        "-f1",
        dna_name,
        "-f2",
        rna_name,
        "-r",
        "1",
        "-O",
        str(output_dir),
    ]
    if mode == "sim":
        cmd.append("-F")
    elif mode != "fasim":
        raise RuntimeError(f"unknown mode: {mode}")

    start = time.perf_counter()
    proc = subprocess.run(
        cmd,
        cwd=str(input_dir),
        env=clean_env(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    wall_seconds = time.perf_counter() - start
    (work_dir / "stdout.log").write_text(proc.stdout, encoding="utf-8")
    (work_dir / "stderr.log").write_text(proc.stderr, encoding="utf-8")
    (work_dir / "command.txt").write_text(" ".join(cmd) + "\n", encoding="utf-8")
    if proc.returncode != 0:
        raise RuntimeError(f"{spec.label}/{mode} failed with exit {proc.returncode}; see {work_dir / 'stderr.log'}")

    metrics = parse_benchmark_metrics(proc.stderr)
    if require_profile:
        validate_profile(metrics)
    raw_records = canonical_lite_records(output_dir)
    return (
        ModeRun(
            label=mode,
            digest=digest_records(raw_records),
            records=parse_lite_records(raw_records),
            metrics=metrics,
        ),
        wall_seconds,
    )


def sim_only_gaps(
    *,
    sim: ModeRun,
    fasim: ModeRun,
    near_tie_delta: float,
    threshold_score_band: float,
    long_hit_nt: int,
) -> List[GapRecord]:
    fasim_raw = {record.raw for record in fasim.records}
    sim_only_records = [record for record in sim.records if record.raw not in fasim_raw]
    all_scores = [record.score for record in sim.records + fasim.records]
    workload_min_score = min(all_scores) if all_scores else 0.0
    fasim_by_family = index_by_family(fasim.records)
    return [
        classify_sim_only_record(
            record,
            fasim_by_family,
            near_tie_delta=near_tie_delta,
            threshold_score_band=threshold_score_band,
            long_hit_nt=long_hit_nt,
            workload_min_score=workload_min_score,
        )
        for record in sim_only_records
    ]


def build_fasim_visible_boxes(
    *,
    fasim_records: Sequence[TriplexRecord],
    merge_gap_bp: int,
    margin_bp: int,
) -> List[RecoveryBox]:
    raw_boxes = [
        RecoveryBox(
            family=record.family,
            genome_interval=expand_interval(record.genome_interval, margin_bp),
            query_interval=expand_interval(record.query_interval, margin_bp),
            categories=frozenset(["fasim_output_record"]),
        )
        for record in fasim_records
    ]
    return merge_recovery_boxes(raw_boxes, merge_gap_bp=merge_gap_bp)


def build_external_executor_shadow(
    *,
    label: str,
    bin_path: Path,
    boxes: Sequence[RecoveryBox],
    dna_entries: Sequence[SequenceEntry],
    query_sequence: str,
    sim_only: Sequence[GapRecord],
    full_cells: int,
    work_dir: Path,
) -> ExecutorShadow:
    start = time.perf_counter()
    if work_dir.exists():
        shutil.rmtree(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    candidate_raw: Set[str] = set()
    executor_failures = 0
    unsupported_boxes = 0
    for index, box in enumerate(boxes, start=1):
        records, unsupported, failed = run_executor_box(
            bin_path=bin_path,
            box=box,
            box_index=index,
            work_dir=work_dir,
            dna_entries=dna_entries,
            query_sequence=query_sequence,
        )
        if unsupported:
            unsupported_boxes += 1
            continue
        if failed:
            executor_failures += 1
            continue
        for record in records:
            candidate_raw.add(record.raw)

    recovered_raw: Set[str] = set()
    for gap in sim_only:
        if gap.record.raw in candidate_raw:
            recovered_raw.add(gap.record.raw)

    seconds = time.perf_counter() - start
    return ExecutorShadow(
        workload_label=label,
        boxes=list(boxes),
        seconds=seconds,
        full_search_cells=full_cells,
        sim_only_records=len(sim_only),
        recovered_records=len(recovered_raw),
        unrecovered_records=len(sim_only) - len(recovered_raw),
        candidate_records=len(candidate_raw),
        output_mutations=0,
        executor_failures=executor_failures,
        unsupported_boxes=unsupported_boxes,
        recovered_by_category=Counter(),
        sim_only_by_category=Counter(),
        candidate_records_raw=frozenset(candidate_raw),
    )


def write_lite_output(path: Path, raw_records: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        handle.write(LITE_HEADER)
        handle.write("\n")
        for raw in raw_records:
            handle.write(raw)
            handle.write("\n")


def build_validation_coverage(
    *,
    requested: bool,
    sim_records: Sequence[TriplexRecord],
    sim_only: Sequence[GapRecord],
    mode: object,
) -> ValidationCoverage:
    sim_raw = {record.raw for record in sim_records}
    sim_only_raw = {gap.record.raw for gap in sim_only}
    sim_close_raw = set(getattr(mode, "output_raw_records", ()))
    supported = requested and bool(sim_raw)
    if not requested:
        unsupported_reason = "not_requested"
    elif supported:
        unsupported_reason = "supported"
    else:
        unsupported_reason = "no_legacy_sim_records"
    return ValidationCoverage(
        requested=requested,
        supported=supported,
        unsupported_reason=unsupported_reason,
        supported_records=len(sim_raw) if supported else 0,
        sim_records=len(sim_raw) if requested else 0,
        sim_close_records=len(sim_close_raw),
        shared_records=len(sim_close_raw & sim_raw) if supported else 0,
        sim_only_records=len(sim_only_raw) if supported else 0,
        sim_close_extra_records=len(sim_close_raw - sim_raw) if supported else 0,
    )


def build_sim_close_mode(
    *,
    bin_path: Path,
    spec: CaseSpec,
    fasim: ModeRun,
    validate: bool,
    work_dir: Path,
    merge_gap_bp: int,
    margin_bp: int,
    near_tie_delta: float,
    threshold_score_band: float,
    long_hit_nt: int,
) -> Tuple[object, float, ValidationCoverage]:
    start = time.perf_counter()
    dna_entries = sequence_entries_from_fasta(spec.dna_path)
    query_sequence = query_sequence_from_fasta(spec.rna_path)
    full_cells = full_search_cells(dna_entries, query_sequence)
    boxes = build_fasim_visible_boxes(
        fasim_records=fasim.records,
        merge_gap_bp=merge_gap_bp,
        margin_bp=margin_bp,
    )

    sim = ModeRun(label="sim", digest="", records=[], metrics={})
    sim_only: List[GapRecord] = []
    if validate:
        sim, _ = run_fasim_mode(
            bin_path=bin_path,
            spec=spec,
            mode="sim",
            work_dir=work_dir / "sim",
            require_profile=False,
        )
        sim_only = sim_only_gaps(
            sim=sim,
            fasim=fasim,
            near_tie_delta=near_tie_delta,
            threshold_score_band=threshold_score_band,
            long_hit_nt=long_hit_nt,
        )

    executor = build_external_executor_shadow(
        label=spec.label,
        bin_path=bin_path,
        boxes=boxes,
        dna_entries=dna_entries,
        query_sequence=query_sequence,
        sim_only=sim_only,
        full_cells=full_cells,
        work_dir=work_dir / "executor",
    )
    mode = build_sim_recovery_real_mode(
        workload_label=spec.label,
        sim_records=sim.records,
        fasim=fasim,
        sim_only=sim_only,
        executor_shadow=executor,
        validate_enabled=validate,
    )
    write_lite_output(work_dir / "sim_close.lite", mode.output_raw_records)
    coverage = build_validation_coverage(
        requested=validate,
        sim_records=sim.records,
        sim_only=sim_only,
        mode=mode,
    )
    return mode, time.perf_counter() - start, coverage


def median_float(values: Iterable[float]) -> float:
    values_list = list(values)
    return float(statistics.median(values_list)) if values_list else 0.0


def stable(values: Iterable[str]) -> bool:
    values_list = list(values)
    return bool(values_list) and all(value == values_list[0] for value in values_list)


def mode_value(mode: object, attr: str, default: float = 0.0) -> float:
    value = getattr(mode, attr, default)
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def mode_text(mode: object, attr: str, default: str = "") -> str:
    value = getattr(mode, attr, default)
    return str(value)


def mode_cell_fraction(mode: object) -> float:
    full_cells = mode_value(mode, "full_search_cells")
    return (mode_value(mode, "cells") / full_cells * 100.0) if full_cells else 0.0


def append_table(lines: List[str], headers: List[str], rows: Iterable[List[str]]) -> None:
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join("---" for _ in headers) + " |")
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")


def fmt_bool(value: bool) -> str:
    return "1" if value else "0"


def fmt_metric(value: float) -> str:
    return f"{value:.6f}"


def run_case(
    *,
    bin_path: Path,
    spec: CaseSpec,
    repeat: int,
    work_dir: Path,
    require_profile: bool,
    merge_gap_bp: int,
    margin_bp: int,
    near_tie_delta: float,
    threshold_score_band: float,
    long_hit_nt: int,
) -> CaseSummary:
    runs: List[CaseRun] = []
    for index in range(1, repeat + 1):
        run_dir = work_dir / spec.label / f"run{index}"
        fast, fast_wall = run_fasim_mode(
            bin_path=bin_path,
            spec=spec,
            mode="fasim",
            work_dir=run_dir / "fast",
            require_profile=require_profile,
        )
        sim_close, sim_close_wall, sim_close_coverage = build_sim_close_mode(
            bin_path=bin_path,
            spec=spec,
            fasim=fast,
            validate=False,
            work_dir=run_dir / "sim_close",
            merge_gap_bp=merge_gap_bp,
            margin_bp=margin_bp,
            near_tie_delta=near_tie_delta,
            threshold_score_band=threshold_score_band,
            long_hit_nt=long_hit_nt,
        )
        validate_mode: Optional[object] = None
        validate_wall = 0.0
        validation_coverage = sim_close_coverage
        if spec.validate:
            validate_mode, validate_wall, validation_coverage = build_sim_close_mode(
                bin_path=bin_path,
                spec=spec,
                fasim=fast,
                validate=True,
                work_dir=run_dir / "sim_close_validate",
                merge_gap_bp=merge_gap_bp,
                margin_bp=margin_bp,
                near_tie_delta=near_tie_delta,
                threshold_score_band=threshold_score_band,
                long_hit_nt=long_hit_nt,
            )
        runs.append(
            CaseRun(
                index=index,
                fast=fast,
                fast_wall_seconds=fast_wall,
                sim_close=sim_close,
                sim_close_wall_seconds=sim_close_wall,
                validate_mode=validate_mode,
                validate_wall_seconds=validate_wall,
                validation_coverage=validation_coverage,
            )
        )
    return CaseSummary(spec=spec, runs=runs)


def selected_mode(run: CaseRun) -> object:
    return run.validate_mode if run.validate_mode is not None else run.sim_close


def case_fast_stable(summary: CaseSummary) -> bool:
    return stable(run.fast.digest for run in summary.runs)


def case_sim_close_stable(summary: CaseSummary) -> bool:
    return stable(mode_text(run.sim_close, "output_digest") for run in summary.runs)


def case_validate_selection_stable(summary: CaseSummary) -> bool:
    if not summary.spec.validate:
        return True
    return all(
        run.validate_mode is not None
        and mode_text(run.validate_mode, "output_digest") == mode_text(run.sim_close, "output_digest")
        for run in summary.runs
    )


def all_modes(summaries: Sequence[CaseSummary]) -> List[object]:
    return [selected_mode(run) for summary in summaries for run in summary.runs]


def validated_modes(summaries: Sequence[CaseSummary]) -> List[object]:
    return [
        run.validate_mode
        for summary in summaries
        for run in summary.runs
        if run.validate_mode is not None and bool(getattr(run.validate_mode, "validate_supported", False))
    ]


def total_per_repeat(summaries: Sequence[CaseSummary], repeat: int, attr: str) -> List[float]:
    totals: List[float] = []
    for run_index in range(repeat):
        total = 0.0
        for summary in summaries:
            total += mode_value(selected_mode(summary.runs[run_index]), attr)
        totals.append(total)
    return totals


def total_coverage_per_repeat(summaries: Sequence[CaseSummary], repeat: int, attr: str) -> List[float]:
    totals: List[float] = []
    for run_index in range(repeat):
        total = 0.0
        for summary in summaries:
            total += float(getattr(summary.runs[run_index].validation_coverage, attr))
        totals.append(total)
    return totals


def total_fast_seconds_per_repeat(summaries: Sequence[CaseSummary], repeat: int) -> List[float]:
    return [
        sum(metric_float(summary.runs[run_index].fast.metrics, "fasim_total_seconds") for summary in summaries)
        for run_index in range(repeat)
    ]


def total_sim_close_wall_seconds_per_repeat(summaries: Sequence[CaseSummary], repeat: int) -> List[float]:
    return [
        sum(summary.runs[run_index].sim_close_wall_seconds for summary in summaries)
        for run_index in range(repeat)
    ]


def total_validate_wall_seconds_per_repeat(summaries: Sequence[CaseSummary], repeat: int) -> List[float]:
    return [
        sum(summary.runs[run_index].validate_wall_seconds for summary in summaries)
        for run_index in range(repeat)
    ]


def per_repeat_sum(left: Sequence[float], right: Sequence[float]) -> List[float]:
    return [a + b for a, b in zip(left, right)]


def render_report(
    *,
    summaries: Sequence[CaseSummary],
    repeat: int,
    output_path: Path,
    title: str,
    base_branch: str,
    coverage_report: bool,
) -> Tuple[str, Dict[str, str]]:
    fast_digest_stable = all(case_fast_stable(summary) for summary in summaries)
    sim_close_digest_stable = all(case_sim_close_stable(summary) for summary in summaries)
    validate_selection_stable = all(case_validate_selection_stable(summary) for summary in summaries)
    fast_mode_output_mutations = int(max(total_per_repeat(summaries, repeat, "output_mutations_fast_mode") or [0.0]))

    modes = all_modes(summaries)
    validation_modes = validated_modes(summaries)
    recall_source = validation_modes
    precision_source = validation_modes
    recommendation = (
        "experimental_opt_in"
        if fast_digest_stable
        and sim_close_digest_stable
        and validate_selection_stable
        and fast_mode_output_mutations == 0
        else "needs_followup"
    )

    lines: List[str] = []
    lines.append(f"# {title}")
    lines.append("")
    lines.append("Base branch:")
    lines.append("")
    lines.append("```text")
    lines.append(base_branch)
    lines.append("```")
    lines.append("")
    lines.append(
        "This report characterizes the default-off `FASIM_SIM_RECOVERY=1` "
        "SIM-close harness on external FASTA cases. It adds no new recovery "
        "logic and does not change scoring, threshold, non-overlap, GPU, "
        "filter, or default fast-mode behavior."
    )
    lines.append("")
    lines.append(
        "`SIM-close wall seconds` measures the side recovery/merge path after "
        "the fast Fasim output is available. The end-to-end SIM-close harness "
        "cost is reported separately as fast seconds plus SIM-close wall seconds."
    )
    lines.append("")
    append_table(
        lines,
        ["Setting", "Value"],
        [
            ["cases", str(len(summaries))],
            ["repeat", str(repeat)],
            ["fast_mode", "default Fasim on the same FASTA"],
            ["sim_close_mode", "FASIM_SIM_RECOVERY=1 side-output harness"],
            ["validate_mode", "post-hoc legacy SIM only for validate cases"],
            ["coverage_report", "yes" if coverage_report else "no"],
        ],
    )
    lines.append("")

    case_rows: List[List[str]] = []
    for summary in summaries:
        first_run = summary.runs[0]
        selected = selected_mode(first_run)
        validation = first_run.validate_mode
        coverage = first_run.validation_coverage
        validate_supported = bool(getattr(selected, "validate_supported", False))
        case_rows.append(
            [
                summary.spec.label,
                "yes" if summary.spec.validate else "no",
                "yes" if coverage.supported else "no",
                str(coverage.supported_records),
                coverage.unsupported_reason,
                first_run.fast.digest,
                mode_text(first_run.sim_close, "output_digest"),
                mode_text(validation, "output_digest", "NA") if validation is not None else "NA",
                str(len(first_run.fast.records)),
                str(coverage.sim_records),
                str(int(mode_value(selected, "output_records"))),
                str(coverage.shared_records),
                str(coverage.sim_only_records),
                str(coverage.sim_close_extra_records) if coverage.supported else "NA",
                str(int(mode_value(selected, "boxes"))),
                str(int(mode_value(selected, "cells"))),
                fmt_metric(mode_cell_fraction(selected)),
                str(int(mode_value(selected, "recovered_candidates"))),
                str(int(mode_value(selected, "recovered_accepted"))),
                str(int(mode_value(selected, "fasim_suppressed"))),
                fmt_metric(mode_value(selected, "recall_vs_sim")) if validate_supported else "NA",
                fmt_metric(mode_value(selected, "precision_vs_sim")) if validate_supported else "NA",
                str(int(mode_value(selected, "extra_vs_sim"))) if validate_supported else "NA",
                str(int(mode_value(selected, "overlap_conflicts"))),
                str(int(mode_value(selected, "fallbacks"))),
            ]
        )

    lines.append("## Case Summary")
    lines.append("")
    append_table(
        lines,
        [
            "Case",
            "Validated",
            "Validate supported",
            "Validate supported records",
            "validate_unsupported_reason",
            "Fast digest",
            "SIM-close digest",
            "Validate digest",
            "Fast records",
            "SIM records",
            "SIM-close records",
            "Shared records",
            "SIM-only records",
            "SIM-close extra records",
            "Boxes",
            "Cells",
            "Cell fraction",
            "Recovered candidates",
            "Accepted",
            "Suppressed",
            "Recall vs SIM",
            "Precision vs SIM",
            "Extra vs SIM",
            "Overlap conflicts",
            "Fallbacks",
        ],
        case_rows,
    )
    lines.append("")

    run_rows: List[List[str]] = []
    for summary in summaries:
        for run in summary.runs:
            selected = selected_mode(run)
            validate_digest = mode_text(run.validate_mode, "output_digest", "NA") if run.validate_mode else "NA"
            coverage = run.validation_coverage
            run_rows.append(
                [
                    summary.spec.label,
                    str(run.index),
                    f"{metric_float(run.fast.metrics, 'fasim_total_seconds'):.6f}",
                    run.fast.digest,
                    mode_text(run.sim_close, "output_digest"),
                    validate_digest,
                    "1" if coverage.supported else "0",
                    str(coverage.supported_records),
                    coverage.unsupported_reason,
                    str(coverage.sim_records),
                    str(int(mode_value(selected, "output_records"))),
                    str(coverage.shared_records),
                    str(coverage.sim_only_records),
                    str(coverage.sim_close_extra_records) if coverage.supported else "NA",
                    str(int(mode_value(selected, "boxes"))),
                    str(int(mode_value(selected, "cells"))),
                    fmt_metric(mode_value(selected, "executor_seconds")),
                    f"{run.sim_close_wall_seconds:.6f}",
                    f"{run.validate_wall_seconds:.6f}" if run.validate_mode else "NA",
                ]
            )

    lines.append("## Run Summary")
    lines.append("")
    append_table(
        lines,
        [
            "Case",
            "Run",
            "Fast seconds",
            "Fast digest",
            "SIM-close digest",
            "Validate digest",
            "Validate supported",
            "Validate supported records",
            "validate_unsupported_reason",
            "SIM records",
            "Output records",
            "Shared records",
            "SIM-only records",
            "SIM-close extra records",
            "Boxes",
            "Cells",
            "Executor seconds",
            "SIM-close wall seconds",
            "Validate wall seconds",
        ],
        run_rows,
    )
    lines.append("")

    boxes_median = median_float(total_per_repeat(summaries, repeat, "boxes"))
    cells_median = median_float(total_per_repeat(summaries, repeat, "cells"))
    full_cells_median = median_float(total_per_repeat(summaries, repeat, "full_search_cells"))
    cell_fraction_median = (cells_median / full_cells_median * 100.0) if full_cells_median else 0.0
    fast_total_seconds_median = median_float(total_fast_seconds_per_repeat(summaries, repeat))
    sim_close_wall_seconds = total_sim_close_wall_seconds_per_repeat(summaries, repeat)
    validate_wall_seconds = total_validate_wall_seconds_per_repeat(summaries, repeat)
    fast_total_seconds = total_fast_seconds_per_repeat(summaries, repeat)
    sim_close_wall_seconds_median = median_float(sim_close_wall_seconds)
    validate_wall_seconds_median = median_float(validate_wall_seconds)
    sim_close_end_to_end_seconds_median = median_float(per_repeat_sum(fast_total_seconds, sim_close_wall_seconds))
    validate_end_to_end_seconds_median = median_float(per_repeat_sum(fast_total_seconds, validate_wall_seconds))
    executor_seconds_median = median_float(total_per_repeat(summaries, repeat, "executor_seconds"))
    fasim_records_median = median_float(total_per_repeat(summaries, repeat, "fasim_records"))
    recovered_candidates_median = median_float(total_per_repeat(summaries, repeat, "recovered_candidates"))
    recovered_accepted_median = median_float(total_per_repeat(summaries, repeat, "recovered_accepted"))
    fasim_suppressed_median = median_float(total_per_repeat(summaries, repeat, "fasim_suppressed"))
    output_records_median = median_float(total_per_repeat(summaries, repeat, "output_records"))
    fallbacks_median = median_float(total_per_repeat(summaries, repeat, "fallbacks"))
    overlap_conflicts_median = median_float(total_per_repeat(summaries, repeat, "overlap_conflicts"))
    recall_median = median_float(mode_value(mode, "recall_vs_sim") for mode in recall_source)
    precision_median = median_float(mode_value(mode, "precision_vs_sim") for mode in precision_source)
    extra_median = median_float(mode_value(mode, "extra_vs_sim") for mode in validation_modes)
    validate_supported_records_median = median_float(total_coverage_per_repeat(summaries, repeat, "supported_records"))
    sim_records_median = median_float(total_coverage_per_repeat(summaries, repeat, "sim_records"))
    sim_close_records_coverage_median = median_float(total_coverage_per_repeat(summaries, repeat, "sim_close_records"))
    shared_records_median = median_float(total_coverage_per_repeat(summaries, repeat, "shared_records"))
    sim_only_records_median = median_float(total_coverage_per_repeat(summaries, repeat, "sim_only_records"))
    sim_close_extra_records_median = median_float(
        total_coverage_per_repeat(summaries, repeat, "sim_close_extra_records")
    )

    telemetry = {
        "cases": str(len(summaries)),
        "repeat": str(repeat),
        "validated_cases": str(sum(1 for summary in summaries if summary.spec.validate)),
        "validate_supported_cases": str(
            sum(
                1
                for summary in summaries
                if any(
                    run.validate_mode is not None
                    and bool(getattr(run.validate_mode, "validate_supported", False))
                    for run in summary.runs
                )
            )
        ),
        "fast_digest_stable": fmt_bool(fast_digest_stable),
        "sim_close_digest_stable": fmt_bool(sim_close_digest_stable),
        "validate_selection_stable": fmt_bool(validate_selection_stable),
        "fast_mode_output_mutations": str(fast_mode_output_mutations),
        "fast_total_seconds_median": fmt_metric(fast_total_seconds_median),
        "sim_close_wall_seconds_median": fmt_metric(sim_close_wall_seconds_median),
        "sim_close_end_to_end_seconds_median": fmt_metric(sim_close_end_to_end_seconds_median),
        "validate_wall_seconds_median": fmt_metric(validate_wall_seconds_median),
        "validate_end_to_end_seconds_median": fmt_metric(validate_end_to_end_seconds_median),
        "boxes_median": fmt_metric(boxes_median),
        "cells_median": fmt_metric(cells_median),
        "full_search_cells_median": fmt_metric(full_cells_median),
        "cell_fraction_median": fmt_metric(cell_fraction_median),
        "executor_seconds_median": fmt_metric(executor_seconds_median),
        "fasim_records_median": fmt_metric(fasim_records_median),
        "recovered_candidates_median": fmt_metric(recovered_candidates_median),
        "recovered_accepted_median": fmt_metric(recovered_accepted_median),
        "fasim_suppressed_median": fmt_metric(fasim_suppressed_median),
        "sim_close_output_records_median": fmt_metric(output_records_median),
        "validate_supported_records_median": fmt_metric(validate_supported_records_median),
        "sim_records_median": fmt_metric(sim_records_median),
        "sim_close_records_median": fmt_metric(sim_close_records_coverage_median),
        "shared_records_median": fmt_metric(shared_records_median),
        "sim_only_records_median": fmt_metric(sim_only_records_median),
        "sim_close_extra_records_median": fmt_metric(sim_close_extra_records_median),
        "recall_vs_sim_median": fmt_metric(recall_median),
        "precision_vs_sim_median": fmt_metric(precision_median),
        "extra_vs_sim_median": fmt_metric(extra_median),
        "overlap_conflicts_median": fmt_metric(overlap_conflicts_median),
        "fallbacks_median": fmt_metric(fallbacks_median),
        "sim_labels_production_inputs": "0",
        "recommendation": recommendation,
    }

    lines.append("## Aggregate")
    lines.append("")
    append_table(
        lines,
        ["Metric", "Value"],
        [[f"fasim_sim_recovery_real_corpus_{key}", value] for key, value in telemetry.items()],
    )
    lines.append("")

    lines.append("## Decision")
    lines.append("")
    lines.append(
        "Keep `FASIM_SIM_RECOVERY=1` as an experimental opt-in. This "
        "characterization checks validation coverage, output stability, and "
        "recovery footprint on the supplied FASTA cases; production "
        "recommendation still requires broader real-corpus evidence."
    )
    lines.append("")
    if coverage_report and validation_modes:
        lines.append(
            "At least one supplied case produced validate-supported legacy SIM "
            "records. Interpret recall/precision only for those supported "
            "cases; unsupported cases remain footprint/stability evidence."
        )
        lines.append("")
        if recall_median < 80.0:
            lines.append(
                "The current supported-case recall is below the synthetic "
                "representative signal. This does not justify recommending "
                "SIM-close mode; it points to further real-corpus "
                "guard/replacement refinement before any high-accuracy claim."
            )
            lines.append("")
    requested_validation = any(summary.spec.validate for summary in summaries)
    if requested_validation and not validation_modes:
        lines.append(
            "Full legacy SIM validation was requested for at least one case, "
            "but no validate-supported SIM records were produced, so "
            "recall/precision/extra metrics are not interpreted here."
        )
        lines.append("")
    elif not validation_modes:
        lines.append(
            "No full legacy SIM validation was run for the supplied cases, so "
            "recall/precision/extra metrics are not interpreted here."
        )
        lines.append("")
    lines.append(
        "Treat this as stability and footprint evidence only when validation "
        "is unavailable; SIM-close output may intentionally differ from the "
        "fast-mode Fasim digest."
    )
    lines.append("")
    lines.append("Do not recommend or default SIM-close mode from this PR.")
    lines.append("")

    lines.append("## Scope")
    lines.append("")
    lines.append("```text")
    lines.append("Default Fasim output changed: no")
    lines.append("SIM labels used as production input: no")
    lines.append("Validation affects production selection: no")
    lines.append("Scoring/threshold/non-overlap behavior change: no")
    lines.append("GPU/filter behavior change: no")
    lines.append("Recommended/default mode: no")
    lines.append("Production accuracy claim: no")
    lines.append("```")

    for summary in summaries:
        for run in summary.runs:
            selected = selected_mode(run)
            prefix = f"benchmark.fasim_sim_recovery_real_corpus.{summary.spec.label}.run{run.index}"
            print(f"{prefix}.fast_digest={run.fast.digest}")
            print(f"{prefix}.sim_close_digest={mode_text(run.sim_close, 'output_digest')}")
            if run.validate_mode is not None:
                print(f"{prefix}.validate_digest={mode_text(run.validate_mode, 'output_digest')}")
            coverage = run.validation_coverage
            print(f"{prefix}.validate_supported={1 if coverage.supported else 0}")
            print(f"{prefix}.validate_supported_records={coverage.supported_records}")
            print(f"{prefix}.validate_unsupported_reason={coverage.unsupported_reason}")
            print(f"{prefix}.sim_records={coverage.sim_records}")
            print(f"{prefix}.sim_close_records={coverage.sim_close_records}")
            print(f"{prefix}.shared_records={coverage.shared_records}")
            print(f"{prefix}.sim_only_records={coverage.sim_only_records}")
            print(f"{prefix}.sim_close_extra_records={coverage.sim_close_extra_records}")
            print(f"{prefix}.output_records={int(mode_value(selected, 'output_records'))}")
            print(f"{prefix}.boxes={int(mode_value(selected, 'boxes'))}")
            print(f"{prefix}.cells={int(mode_value(selected, 'cells'))}")
            print(f"{prefix}.recovered_candidates={int(mode_value(selected, 'recovered_candidates'))}")
            print(f"{prefix}.recovered_accepted={int(mode_value(selected, 'recovered_accepted'))}")
            print(f"{prefix}.fasim_suppressed={int(mode_value(selected, 'fasim_suppressed'))}")
            print(f"{prefix}.fallbacks={int(mode_value(selected, 'fallbacks'))}")
            print(f"{prefix}.output_mutations_fast_mode={int(mode_value(selected, 'output_mutations_fast_mode'))}")

    for key, value in telemetry.items():
        print(f"benchmark.fasim_sim_recovery_real_corpus.total.{key}={value}")

    report = "\n".join(lines)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report + "\n", encoding="utf-8")
    return report, telemetry


def parse_cases(raw_cases: Optional[Sequence[Sequence[str]]], validate_labels: Set[str]) -> List[CaseSpec]:
    cases: List[CaseSpec] = []
    for raw in raw_cases or []:
        label, dna, rna = raw
        label = ensure_label(label)
        cases.append(
            CaseSpec(
                label=label,
                dna_path=Path(dna).resolve(),
                rna_path=Path(rna).resolve(),
                validate=label in validate_labels,
            )
        )
    if not cases:
        raise RuntimeError("at least one --case LABEL DNA RNA is required")
    return cases


def parse_validate_labels(values: Sequence[str]) -> Set[str]:
    labels: Set[str] = set()
    for value in values:
        for label in value.split(","):
            label = label.strip()
            if label:
                labels.add(ensure_label(label))
    return labels


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bin", default=str(ROOT / "fasim_longtarget_x86"))
    parser.add_argument("--case", nargs=3, action="append", metavar=("LABEL", "DNA", "RNA"))
    parser.add_argument("--validate-case", action="append", default=[])
    parser.add_argument("--validate-cases", action="append", default=[])
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--require-profile", action="store_true")
    parser.add_argument("--merge-gap-bp", type=int, default=32)
    parser.add_argument("--risk-margin-bp", type=int, default=32)
    parser.add_argument("--near-tie-delta", type=float, default=1.0)
    parser.add_argument("--threshold-score-band", type=float, default=5.0)
    parser.add_argument("--long-hit-nt", type=int, default=80)
    parser.add_argument("--work-dir", default=str(ROOT / ".tmp" / "fasim_sim_recovery_real_corpus_characterization"))
    parser.add_argument("--output", default=str(ROOT / "docs" / "fasim_sim_recovery_real_corpus_characterization.md"))
    parser.add_argument("--report-title", default="Fasim SIM-Close Recovery Real-Corpus Characterization")
    parser.add_argument("--base-branch", default="fasim-sim-recovery-real-mode-characterization")
    parser.add_argument("--validation-coverage-report", action="store_true")
    args = parser.parse_args()

    try:
        bin_path = Path(args.bin)
        if not bin_path.is_absolute():
            bin_path = (ROOT / bin_path).resolve()
        if not bin_path.exists():
            raise RuntimeError(f"missing Fasim binary: {bin_path}")

        validate_labels = parse_validate_labels([*args.validate_case, *args.validate_cases])
        cases = parse_cases(args.case, validate_labels)
        repeat = args.repeat if args.repeat > 0 else 1
        work_dir = Path(args.work_dir).resolve()
        if work_dir.exists():
            shutil.rmtree(work_dir)
        work_dir.mkdir(parents=True, exist_ok=True)

        summaries = [
            run_case(
                bin_path=bin_path,
                spec=case,
                repeat=repeat,
                work_dir=work_dir,
                require_profile=args.require_profile,
                merge_gap_bp=args.merge_gap_bp,
                margin_bp=args.risk_margin_bp,
                near_tie_delta=args.near_tie_delta,
                threshold_score_band=args.threshold_score_band,
                long_hit_nt=args.long_hit_nt,
            )
            for case in cases
        ]
        report, _ = render_report(
            summaries=summaries,
            repeat=repeat,
            output_path=Path(args.output),
            title=args.report_title,
            base_branch=args.base_branch,
            coverage_report=args.validation_coverage_report,
        )
        print(report)
        return 0
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
