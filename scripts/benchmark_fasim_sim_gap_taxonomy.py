#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import dataclasses
import os
from pathlib import Path
import shutil
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
    parse_benchmark_metrics,
    validate_profile,
)
from benchmark_fasim_representative_profile import (  # noqa: E402
    FixtureSpec,
    REPRESENTATIVE_FIXTURES,
    SMOKE_FIXTURES,
    read_fasta_sequence,
    write_tiled_fasta,
)


SMALL_MEDIUM_FIXTURES = REPRESENTATIVE_FIXTURES[:2]
GAP_CATEGORIES = [
    "long_hit_internal_peak",
    "nested_alignment",
    "nonoverlap_conflict",
    "overlap_chain",
    "tie_near_tie",
    "threshold_near",
    "unknown",
]


@dataclasses.dataclass(frozen=True)
class TriplexRecord:
    raw: str
    chr_name: str
    genome_start: int
    genome_end: int
    strand: str
    rule: str
    query_start: int
    query_end: int
    start_in_seq: int
    end_in_seq: int
    direction: str
    score: float
    nt: int
    identity: float
    stability: float

    @property
    def family(self) -> Tuple[str, str, str]:
        return (self.chr_name, self.strand, self.rule)

    @property
    def genome_interval(self) -> Tuple[int, int]:
        return normalized_interval(self.genome_start, self.genome_end)

    @property
    def query_interval(self) -> Tuple[int, int]:
        return normalized_interval(self.query_start, self.query_end)


@dataclasses.dataclass(frozen=True)
class ModeRun:
    label: str
    digest: str
    records: List[TriplexRecord]
    metrics: Dict[str, str]


@dataclasses.dataclass(frozen=True)
class GapRecord:
    record: TriplexRecord
    primary: str
    flags: Set[str]
    overlapping_fasim_records: int
    nearest_score_delta: Optional[float]


@dataclasses.dataclass(frozen=True)
class RecoveryEstimate:
    recovery_windows: int
    recovery_boxes: int
    recovery_cells: int


@dataclasses.dataclass(frozen=True)
class RecoveryBox:
    family: Tuple[str, str, str]
    genome_interval: Tuple[int, int]
    query_interval: Tuple[int, int]
    categories: frozenset[str]


@dataclasses.dataclass(frozen=True)
class RecoveryShadow:
    workload_label: str
    boxes: List[RecoveryBox]
    seconds: float
    full_search_cells: int
    sim_only_records: int
    recovered_records: int
    unrecovered_records: int
    candidate_records: int
    output_mutations: int
    recovered_by_category: Counter
    sim_only_by_category: Counter

    @property
    def windows(self) -> int:
        return len({box.family for box in self.boxes})

    @property
    def cells(self) -> int:
        return sum(box_cells(box) for box in self.boxes)

    @property
    def cell_fraction(self) -> float:
        return (float(self.cells) / float(self.full_search_cells) * 100.0) if self.full_search_cells else 0.0

    @property
    def recall(self) -> float:
        return pct(self.recovered_records, self.sim_only_records)


@dataclasses.dataclass(frozen=True)
class RiskDetectorResult:
    workload_label: str
    mode: str
    boxes: List[RecoveryBox]
    seconds: float
    full_search_cells: int
    sim_only_records: int
    supported_sim_only_records: int
    unsupported_sim_only_records: int
    candidate_records: int
    false_positive_boxes: int
    output_mutations: int
    supported_by_category: Counter
    sim_only_by_category: Counter

    @property
    def cells(self) -> int:
        return sum(box_cells(box) for box in self.boxes)

    @property
    def cell_fraction(self) -> float:
        return (float(self.cells) / float(self.full_search_cells) * 100.0) if self.full_search_cells else 0.0

    @property
    def recall(self) -> float:
        return pct(self.supported_sim_only_records, self.sim_only_records)


@dataclasses.dataclass(frozen=True)
class WorkloadGap:
    spec: FixtureSpec
    sim: ModeRun
    fasim: ModeRun
    shared_records: int
    sim_region_supported_records: int
    sim_only: List[GapRecord]
    fasim_only: List[TriplexRecord]
    category_counts: Counter
    flag_counts: Counter
    recovery: RecoveryEstimate
    recovery_shadow: Optional[RecoveryShadow] = None
    risk_detector: Optional[RiskDetectorResult] = None


def normalized_interval(a: int, b: int) -> Tuple[int, int]:
    return (a, b) if a <= b else (b, a)


def interval_length(interval: Tuple[int, int]) -> int:
    return max(0, interval[1] - interval[0] + 1)


def expand_interval(interval: Tuple[int, int], margin: int) -> Tuple[int, int]:
    return (max(1, interval[0] - margin), interval[1] + margin)


def overlaps(a: Tuple[int, int], b: Tuple[int, int]) -> bool:
    return max(a[0], b[0]) <= min(a[1], b[1])


def contains(outer: Tuple[int, int], inner: Tuple[int, int]) -> bool:
    return outer[0] <= inner[0] and inner[1] <= outer[1]


def box_cells(box: RecoveryBox) -> int:
    return interval_length(box.genome_interval) * interval_length(box.query_interval)


def parse_int(value: str, field: str, raw: str) -> int:
    try:
        return int(float(value))
    except ValueError as exc:
        raise RuntimeError(f"invalid integer {field}={value!r} in record: {raw}") from exc


def parse_float(value: str, field: str, raw: str) -> float:
    try:
        return float(value)
    except ValueError as exc:
        raise RuntimeError(f"invalid float {field}={value!r} in record: {raw}") from exc


def parse_lite_record(raw: str) -> TriplexRecord:
    fields = raw.split("\t")
    if len(fields) != 14:
        raise RuntimeError(f"expected 14 lite fields, got {len(fields)}: {raw}")
    return TriplexRecord(
        raw=raw,
        chr_name=fields[0],
        genome_start=parse_int(fields[1], "StartInGenome", raw),
        genome_end=parse_int(fields[2], "EndInGenome", raw),
        strand=fields[3],
        rule=fields[4],
        query_start=parse_int(fields[5], "QueryStart", raw),
        query_end=parse_int(fields[6], "QueryEnd", raw),
        start_in_seq=parse_int(fields[7], "StartInSeq", raw),
        end_in_seq=parse_int(fields[8], "EndInSeq", raw),
        direction=fields[9],
        score=parse_float(fields[10], "Score", raw),
        nt=parse_int(fields[11], "Nt(bp)", raw),
        identity=parse_float(fields[12], "MeanIdentity(%)", raw),
        stability=parse_float(fields[13], "MeanStability", raw),
    )


def parse_lite_records(raw_records: Iterable[str]) -> List[TriplexRecord]:
    return [parse_lite_record(raw) for raw in raw_records]


def prepare_inputs(spec: FixtureSpec, work_dir: Path) -> Tuple[str, str]:
    inputs_dir = work_dir / "inputs"
    inputs_dir.mkdir(parents=True, exist_ok=True)
    dna_filename = f"{spec.label}.fa"
    if spec.label == "tiny" and spec.dna_entries == 1 and spec.dna_repeat == 1:
        dna_filename = "testDNA.fa"
        shutil.copyfile(ROOT / "testDNA.fa", inputs_dir / dna_filename)
    else:
        dna_sequence = read_fasta_sequence(ROOT / "testDNA.fa")
        write_tiled_fasta(
            inputs_dir / dna_filename,
            sequence=dna_sequence,
            entries=spec.dna_entries,
            repeat=spec.dna_repeat,
        )
    shutil.copyfile(ROOT / "H19.fa", inputs_dir / "H19.fa")
    return dna_filename, "H19.fa"


def fixture_full_search_cells(spec: FixtureSpec) -> int:
    dna_sequence = read_fasta_sequence(ROOT / "testDNA.fa")
    rna_sequence = read_fasta_sequence(ROOT / "H19.fa")
    return len(dna_sequence) * spec.dna_repeat * spec.dna_entries * len(rna_sequence)


def run_mode(
    *,
    bin_path: Path,
    spec: FixtureSpec,
    mode: str,
    work_dir: Path,
    require_profile: bool,
) -> ModeRun:
    if work_dir.exists():
        shutil.rmtree(work_dir)
    output_dir = work_dir / "out"
    output_dir.mkdir(parents=True, exist_ok=True)
    dna_filename, rna_filename = prepare_inputs(spec, work_dir)

    env = os.environ.copy()
    env["FASIM_VERBOSE"] = "0"
    env["FASIM_OUTPUT_MODE"] = "lite"
    env["FASIM_PROFILE"] = "1"
    env["FASIM_EXTEND_THREADS"] = "1"

    cmd = [
        str(bin_path),
        "-f1",
        dna_filename,
        "-f2",
        rna_filename,
        "-r",
        "1",
        "-O",
        str(output_dir),
    ]
    if mode == "sim":
        cmd.append("-F")
    elif mode != "fasim":
        raise RuntimeError(f"unknown mode: {mode}")

    proc = subprocess.run(
        cmd,
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
        raise RuntimeError(f"{spec.label}/{mode} failed with exit {proc.returncode}; see {work_dir / 'stderr.log'}")

    metrics = parse_benchmark_metrics(proc.stderr)
    if require_profile:
        validate_profile(metrics)
    raw_records = canonical_lite_records(output_dir)
    return ModeRun(
        label=mode,
        digest=digest_records(raw_records),
        records=parse_lite_records(raw_records),
        metrics=metrics,
    )


def index_by_family(records: Sequence[TriplexRecord]) -> Dict[Tuple[str, str, str], List[TriplexRecord]]:
    indexed: Dict[Tuple[str, str, str], List[TriplexRecord]] = defaultdict(list)
    for record in records:
        indexed[record.family].append(record)
    return indexed


def is_region_supported(record: TriplexRecord, candidates_by_family: Dict[Tuple[str, str, str], List[TriplexRecord]]) -> bool:
    genome_interval = record.genome_interval
    return any(
        overlaps(genome_interval, candidate.genome_interval)
        for candidate in candidates_by_family.get(record.family, [])
    )


def nearest_score_delta(record: TriplexRecord, candidates: Sequence[TriplexRecord]) -> Optional[float]:
    if not candidates:
        return None
    return min(abs(record.score - candidate.score) for candidate in candidates)


def classify_sim_only_record(
    record: TriplexRecord,
    fasim_by_family: Dict[Tuple[str, str, str], List[TriplexRecord]],
    *,
    near_tie_delta: float,
    threshold_score_band: float,
    long_hit_nt: int,
    workload_min_score: float,
) -> GapRecord:
    same_family = fasim_by_family.get(record.family, [])
    genome_interval = record.genome_interval
    query_interval = record.query_interval
    overlapping = [
        candidate
        for candidate in same_family
        if overlaps(genome_interval, candidate.genome_interval)
    ]
    containing = [
        candidate
        for candidate in overlapping
        if contains(candidate.genome_interval, genome_interval)
        and contains(candidate.query_interval, query_interval)
    ]

    flags: Set[str] = set()
    if containing:
        flags.add("nested_alignment")
    if any(candidate.nt >= long_hit_nt and candidate.nt > record.nt for candidate in containing):
        flags.add("long_hit_internal_peak")
    if len(overlapping) >= 2:
        flags.add("nonoverlap_conflict")
    elif len(overlapping) == 1:
        flags.add("overlap_chain")
    score_delta = nearest_score_delta(record, overlapping or same_family)
    if score_delta is not None and score_delta <= near_tie_delta:
        flags.add("tie_near_tie")
    if record.score <= workload_min_score + threshold_score_band:
        flags.add("threshold_near")

    for primary in (
        "long_hit_internal_peak",
        "nested_alignment",
        "nonoverlap_conflict",
        "overlap_chain",
        "tie_near_tie",
        "threshold_near",
    ):
        if primary in flags:
            return GapRecord(record, primary, flags, len(overlapping), score_delta)
    return GapRecord(record, "unknown", flags, len(overlapping), score_delta)


def estimate_recovery(sim_only: Sequence[GapRecord], *, merge_gap_bp: int) -> RecoveryEstimate:
    grouped: Dict[Tuple[str, str, str], List[TriplexRecord]] = defaultdict(list)
    for gap in sim_only:
        grouped[gap.record.family].append(gap.record)

    recovery_boxes = 0
    recovery_cells = 0
    for records in grouped.values():
        ordered = sorted(records, key=lambda item: (item.genome_interval[0], item.genome_interval[1]))
        current_genome: Optional[List[int]] = None
        current_query: Optional[List[int]] = None
        for record in ordered:
            genome = record.genome_interval
            query = record.query_interval
            if current_genome is None or current_query is None:
                current_genome = [genome[0], genome[1]]
                current_query = [query[0], query[1]]
                continue
            if genome[0] <= current_genome[1] + merge_gap_bp:
                current_genome[1] = max(current_genome[1], genome[1])
                current_query[0] = min(current_query[0], query[0])
                current_query[1] = max(current_query[1], query[1])
                continue
            recovery_boxes += 1
            recovery_cells += interval_length(tuple(current_genome)) * interval_length(tuple(current_query))
            current_genome = [genome[0], genome[1]]
            current_query = [query[0], query[1]]
        if current_genome is not None and current_query is not None:
            recovery_boxes += 1
            recovery_cells += interval_length(tuple(current_genome)) * interval_length(tuple(current_query))

    return RecoveryEstimate(
        recovery_windows=len(grouped),
        recovery_boxes=recovery_boxes,
        recovery_cells=recovery_cells,
    )


def merge_recovery_boxes(boxes: Sequence[RecoveryBox], *, merge_gap_bp: int) -> List[RecoveryBox]:
    grouped: Dict[Tuple[str, str, str], List[RecoveryBox]] = defaultdict(list)
    for box in boxes:
        grouped[box.family].append(box)

    merged: List[RecoveryBox] = []
    for family, family_boxes in grouped.items():
        ordered = sorted(family_boxes, key=lambda item: (item.genome_interval[0], item.genome_interval[1]))
        current_genome: Optional[List[int]] = None
        current_query: Optional[List[int]] = None
        current_categories: Set[str] = set()
        for box in ordered:
            genome = box.genome_interval
            query = box.query_interval
            if current_genome is None or current_query is None:
                current_genome = [genome[0], genome[1]]
                current_query = [query[0], query[1]]
                current_categories = set(box.categories)
                continue
            if genome[0] <= current_genome[1] + merge_gap_bp:
                current_genome[1] = max(current_genome[1], genome[1])
                current_query[0] = min(current_query[0], query[0])
                current_query[1] = max(current_query[1], query[1])
                current_categories.update(box.categories)
                continue
            merged.append(
                RecoveryBox(
                    family=family,
                    genome_interval=tuple(current_genome),
                    query_interval=tuple(current_query),
                    categories=frozenset(current_categories),
                )
            )
            current_genome = [genome[0], genome[1]]
            current_query = [query[0], query[1]]
            current_categories = set(box.categories)
        if current_genome is not None and current_query is not None:
            merged.append(
                RecoveryBox(
                    family=family,
                    genome_interval=tuple(current_genome),
                    query_interval=tuple(current_query),
                    categories=frozenset(current_categories),
                )
            )
    return merged


def record_in_any_box(record: TriplexRecord, boxes_by_family: Dict[Tuple[str, str, str], List[RecoveryBox]]) -> bool:
    genome = record.genome_interval
    query = record.query_interval
    return any(
        contains(box.genome_interval, genome) and contains(box.query_interval, query)
        for box in boxes_by_family.get(record.family, [])
    )


def build_local_recovery_shadow(
    *,
    spec: FixtureSpec,
    sim_records: Sequence[TriplexRecord],
    fasim_records: Sequence[TriplexRecord],
    sim_only: Sequence[GapRecord],
    merge_gap_bp: int,
    margin_bp: int,
) -> RecoveryShadow:
    start = time.perf_counter()
    fasim_by_family = index_by_family(fasim_records)
    raw_boxes: List[RecoveryBox] = []
    seen: Set[Tuple[Tuple[str, str, str], Tuple[int, int], Tuple[int, int], str]] = set()

    for gap in sim_only:
        record = gap.record
        for candidate in fasim_by_family.get(record.family, []):
            if not overlaps(record.genome_interval, candidate.genome_interval):
                continue
            genome = expand_interval(candidate.genome_interval, margin_bp)
            query = expand_interval(candidate.query_interval, margin_bp)
            key = (record.family, genome, query, gap.primary)
            if key in seen:
                continue
            seen.add(key)
            raw_boxes.append(
                RecoveryBox(
                    family=record.family,
                    genome_interval=genome,
                    query_interval=query,
                    categories=frozenset([gap.primary]),
                )
            )

    boxes = merge_recovery_boxes(raw_boxes, merge_gap_bp=merge_gap_bp)
    boxes_by_family: Dict[Tuple[str, str, str], List[RecoveryBox]] = defaultdict(list)
    for box in boxes:
        boxes_by_family[box.family].append(box)

    recovered_by_category: Counter = Counter()
    sim_only_by_category: Counter = Counter(gap.primary for gap in sim_only)
    recovered_records = 0
    for gap in sim_only:
        if record_in_any_box(gap.record, boxes_by_family):
            recovered_records += 1
            recovered_by_category.update([gap.primary])

    candidate_records = sum(1 for record in sim_records if record_in_any_box(record, boxes_by_family))
    seconds = time.perf_counter() - start
    return RecoveryShadow(
        workload_label=spec.label,
        boxes=boxes,
        seconds=seconds,
        full_search_cells=fixture_full_search_cells(spec),
        sim_only_records=len(sim_only),
        recovered_records=recovered_records,
        unrecovered_records=len(sim_only) - recovered_records,
        candidate_records=candidate_records,
        output_mutations=0,
        recovered_by_category=recovered_by_category,
        sim_only_by_category=sim_only_by_category,
    )


def build_fasim_visible_risk_detector(
    *,
    spec: FixtureSpec,
    sim_records: Sequence[TriplexRecord],
    fasim_records: Sequence[TriplexRecord],
    sim_only: Sequence[GapRecord],
    merge_gap_bp: int,
    margin_bp: int,
) -> RiskDetectorResult:
    start = time.perf_counter()
    raw_boxes = [
        RecoveryBox(
            family=record.family,
            genome_interval=expand_interval(record.genome_interval, margin_bp),
            query_interval=expand_interval(record.query_interval, margin_bp),
            categories=frozenset(["fasim_output_record"]),
        )
        for record in fasim_records
    ]
    boxes = merge_recovery_boxes(raw_boxes, merge_gap_bp=merge_gap_bp)
    boxes_by_family: Dict[Tuple[str, str, str], List[RecoveryBox]] = defaultdict(list)
    for box in boxes:
        boxes_by_family[box.family].append(box)

    supported_by_category: Counter = Counter()
    sim_only_by_category: Counter = Counter(gap.primary for gap in sim_only)
    supported_records = 0
    for gap in sim_only:
        if record_in_any_box(gap.record, boxes_by_family):
            supported_records += 1
            supported_by_category.update([gap.primary])

    candidate_records = sum(1 for record in sim_records if record_in_any_box(record, boxes_by_family))
    false_positive_boxes = 0
    for box in boxes:
        if not any(
            contains(box.genome_interval, gap.record.genome_interval)
            and contains(box.query_interval, gap.record.query_interval)
            for gap in sim_only
            if gap.record.family == box.family
        ):
            false_positive_boxes += 1

    seconds = time.perf_counter() - start
    return RiskDetectorResult(
        workload_label=spec.label,
        mode="all_fasim_records_baseline",
        boxes=boxes,
        seconds=seconds,
        full_search_cells=fixture_full_search_cells(spec),
        sim_only_records=len(sim_only),
        supported_sim_only_records=supported_records,
        unsupported_sim_only_records=len(sim_only) - supported_records,
        candidate_records=candidate_records,
        false_positive_boxes=false_positive_boxes,
        output_mutations=0,
        supported_by_category=supported_by_category,
        sim_only_by_category=sim_only_by_category,
    )


def analyze_gap(
    *,
    spec: FixtureSpec,
    sim: ModeRun,
    fasim: ModeRun,
    near_tie_delta: float,
    threshold_score_band: float,
    long_hit_nt: int,
    merge_gap_bp: int,
    recovery_shadow_enabled: bool,
    recovery_shadow_margin_bp: int,
    risk_detector_enabled: bool,
    risk_detector_margin_bp: int,
) -> WorkloadGap:
    sim_raw = {record.raw for record in sim.records}
    fasim_raw = {record.raw for record in fasim.records}
    shared = sim_raw & fasim_raw
    sim_only_records = [record for record in sim.records if record.raw not in fasim_raw]
    fasim_only_records = [record for record in fasim.records if record.raw not in sim_raw]

    all_scores = [record.score for record in sim.records + fasim.records]
    workload_min_score = min(all_scores) if all_scores else 0.0
    fasim_by_family = index_by_family(fasim.records)
    sim_region_supported_records = sum(1 for record in sim.records if is_region_supported(record, fasim_by_family))
    sim_only = [
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
    category_counts = Counter(gap.primary for gap in sim_only)
    flag_counts: Counter = Counter()
    for gap in sim_only:
        flag_counts.update(gap.flags)

    return WorkloadGap(
        spec=spec,
        sim=sim,
        fasim=fasim,
        shared_records=len(shared),
        sim_region_supported_records=sim_region_supported_records,
        sim_only=sim_only,
        fasim_only=fasim_only_records,
        category_counts=category_counts,
        flag_counts=flag_counts,
        recovery=estimate_recovery(sim_only, merge_gap_bp=merge_gap_bp),
        recovery_shadow=(
            build_local_recovery_shadow(
                spec=spec,
                sim_records=sim.records,
                fasim_records=fasim.records,
                sim_only=sim_only,
                merge_gap_bp=merge_gap_bp,
                margin_bp=recovery_shadow_margin_bp,
            )
            if recovery_shadow_enabled
            else None
        ),
        risk_detector=(
            build_fasim_visible_risk_detector(
                spec=spec,
                sim_records=sim.records,
                fasim_records=fasim.records,
                sim_only=sim_only,
                merge_gap_bp=merge_gap_bp,
                margin_bp=risk_detector_margin_bp,
            )
            if risk_detector_enabled
            else None
        ),
    )


def pct(numerator: int, denominator: int) -> float:
    return (float(numerator) / float(denominator) * 100.0) if denominator else 0.0


def fmt_pct(value: float) -> str:
    return f"{value:.2f}%"


def append_table(lines: List[str], headers: List[str], rows: Iterable[List[str]]) -> None:
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join("---" for _ in headers) + " |")
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")


def render_report(
    *,
    gaps: Sequence[WorkloadGap],
    output_path: Path,
    profile_set: str,
    near_tie_delta: float,
    threshold_score_band: float,
    long_hit_nt: int,
    merge_gap_bp: int,
) -> str:
    lines: List[str] = []
    lines.append("# Fasim SIM-Gap Taxonomy")
    lines.append("")
    lines.append("Base branch:")
    lines.append("")
    lines.append("```text")
    lines.append("fasim-gpu-dp-column-post-topk-align")
    lines.append("```")
    lines.append("")
    lines.append(
        "This report compares Fasim fast output against the same binary's legacy "
        "`-F` SIM path on deterministic fixtures. It is taxonomy-only: no Fasim "
        "output change, no recovery, no filter, and no GPU code."
    )
    lines.append("")
    lines.append("## Settings")
    lines.append("")
    append_table(
        lines,
        ["Setting", "Value"],
        [
            ["profile_set", profile_set],
            ["near_tie_delta", f"{near_tie_delta:g}"],
            ["threshold_score_band", f"{threshold_score_band:g}"],
            ["long_hit_nt", str(long_hit_nt)],
            ["merge_gap_bp", str(merge_gap_bp)],
        ],
    )
    lines.append("")

    rows: List[List[str]] = []
    total_sim = 0
    total_fasim = 0
    total_shared = 0
    total_region_supported = 0
    total_sim_only = 0
    total_fasim_only = 0
    total_recovery_boxes = 0
    total_recovery_cells = 0
    total_recovery_windows = 0
    aggregate_categories: Counter = Counter()
    aggregate_flags: Counter = Counter()
    for gap in gaps:
        sim_count = len(gap.sim.records)
        fasim_count = len(gap.fasim.records)
        sim_only_count = len(gap.sim_only)
        fasim_only_count = len(gap.fasim_only)
        total_sim += sim_count
        total_fasim += fasim_count
        total_shared += gap.shared_records
        total_region_supported += gap.sim_region_supported_records
        total_sim_only += sim_only_count
        total_fasim_only += fasim_only_count
        total_recovery_windows += gap.recovery.recovery_windows
        total_recovery_boxes += gap.recovery.recovery_boxes
        total_recovery_cells += gap.recovery.recovery_cells
        aggregate_categories.update(gap.category_counts)
        aggregate_flags.update(gap.flag_counts)
        rows.append(
            [
                gap.spec.label,
                str(sim_count),
                str(fasim_count),
                str(gap.shared_records),
                str(gap.sim_region_supported_records),
                str(sim_only_count),
                str(fasim_only_count),
                fmt_pct(pct(gap.shared_records, sim_count)),
                fmt_pct(pct(gap.sim_region_supported_records, sim_count)),
                fmt_pct(pct(sim_only_count, sim_count)),
                gap.sim.digest,
                gap.fasim.digest,
            ]
        )
    append_table(
        lines,
        [
            "Workload",
            "SIM records",
            "Fasim records",
            "Shared exact",
            "SIM region-supported",
            "SIM-only",
            "Fasim-only",
            "Exact recall vs SIM",
            "Region support vs SIM",
            "SIM-only %",
            "SIM digest",
            "Fasim digest",
        ],
        rows,
    )
    lines.append("")
    lines.append(
        "`Shared exact` is strict canonical lite-record identity. "
        "`SIM region-supported` is looser: a SIM record is counted when Fasim has "
        "a same-family genomic overlap. Region support is a locality signal for "
        "possible recovery boxes, not an output-equivalence claim."
    )
    lines.append("")

    lines.append("## Limitations")
    lines.append("")
    lines.append(
        "The representative fixtures are deterministic scale-ups of the small "
        "repository fixtures. They are useful for taxonomy plumbing and local "
        "pattern checks, but they are not a production corpus. Treat the decision "
        "below as a direction for the next diagnostic PR, not as proof that SIM "
        "recovery will improve production accuracy."
    )
    lines.append("")

    lines.append("## Aggregate SIM-Only Taxonomy")
    lines.append("")
    categories = GAP_CATEGORIES
    append_table(
        lines,
        ["Category", "SIM-only records", "Percent of SIM-only"],
        [
            [
                category,
                str(aggregate_categories.get(category, 0)),
                fmt_pct(pct(aggregate_categories.get(category, 0), total_sim_only)),
            ]
            for category in categories
        ],
    )
    lines.append("")

    lines.append("Flag counts are non-exclusive; a SIM-only record can have multiple flags.")
    lines.append("")
    append_table(
        lines,
        ["Flag", "Records", "Percent of SIM-only"],
        [
            [flag, str(aggregate_flags.get(flag, 0)), fmt_pct(pct(aggregate_flags.get(flag, 0), total_sim_only))]
            for flag in categories[:-1]
        ],
    )
    lines.append("")

    lines.append("## Per-Workload Taxonomy")
    lines.append("")
    for gap in gaps:
        lines.append(f"### {gap.spec.label}")
        lines.append("")
        append_table(
            lines,
            ["Category", "SIM-only records", "Percent of workload SIM-only"],
            [
                [
                    category,
                    str(gap.category_counts.get(category, 0)),
                    fmt_pct(pct(gap.category_counts.get(category, 0), len(gap.sim_only))),
                ]
                for category in categories
            ],
        )
        lines.append("")
        append_table(
            lines,
            ["Recovery estimate", "Value"],
            [
                ["recovery_windows", str(gap.recovery.recovery_windows)],
                ["recovery_boxes", str(gap.recovery.recovery_boxes)],
                ["recovery_cells", str(gap.recovery.recovery_cells)],
            ],
        )
        lines.append("")

    lines.append("## Aggregate Recovery Cost Estimate")
    lines.append("")
    append_table(
        lines,
        ["Metric", "Value"],
        [
            ["sim_records", str(total_sim)],
            ["fasim_records", str(total_fasim)],
            ["shared_records", str(total_shared)],
            ["sim_region_supported_records", str(total_region_supported)],
            ["sim_only_records", str(total_sim_only)],
            ["fasim_only_records", str(total_fasim_only)],
            ["fasim_recall_vs_sim", fmt_pct(pct(total_shared, total_sim))],
            ["region_support_vs_sim", fmt_pct(pct(total_region_supported, total_sim))],
            ["recovery_windows", str(total_recovery_windows)],
            ["recovery_boxes", str(total_recovery_boxes)],
            ["recovery_cells", str(total_recovery_cells)],
        ],
    )
    lines.append("")

    lines.append("## Decision")
    lines.append("")
    if total_sim_only == 0:
        decision = (
            "No SIM-only records were observed on this fixture set. Broaden the "
            "fixtures before designing SIM recovery."
        )
    else:
        local_like = (
            aggregate_categories.get("long_hit_internal_peak", 0)
            + aggregate_categories.get("nested_alignment", 0)
            + aggregate_categories.get("overlap_chain", 0)
            + aggregate_categories.get("nonoverlap_conflict", 0)
        )
        local_pct = pct(local_like, total_sim_only)
        if local_pct >= 80.0:
            decision = (
                "SIM-only records concentrate in local/nested/overlap patterns. "
                "A local SIM recovery shadow is a plausible next PR."
            )
        elif local_pct >= 50.0:
            decision = (
                "SIM-only records are partially local/nested/overlap-like. A recovery "
                "shadow is plausible, but thresholds and box costs need broader data."
            )
        else:
            decision = (
                "SIM-only records are not concentrated in local/nested/overlap patterns. "
                "SIM-close recovery may be expensive or require broader taxonomy."
            )
    lines.append(decision)
    lines.append("")
    lines.append("Forbidden-scope check:")
    lines.append("")
    lines.append("```text")
    lines.append("Fasim output change: no")
    lines.append("SIM recovery implementation: no")
    lines.append("GPU code: no")
    lines.append("filter/threshold/non-overlap behavior change: no")
    lines.append("```")
    lines.append("")

    for gap in gaps:
        print(f"benchmark.fasim_sim_gap.{gap.spec.label}.sim_records={len(gap.sim.records)}")
        print(f"benchmark.fasim_sim_gap.{gap.spec.label}.fasim_records={len(gap.fasim.records)}")
        print(f"benchmark.fasim_sim_gap.{gap.spec.label}.shared_records={gap.shared_records}")
        print(
            f"benchmark.fasim_sim_gap.{gap.spec.label}.sim_region_supported_records="
            f"{gap.sim_region_supported_records}"
        )
        print(f"benchmark.fasim_sim_gap.{gap.spec.label}.sim_only_records={len(gap.sim_only)}")
        print(f"benchmark.fasim_sim_gap.{gap.spec.label}.fasim_only_records={len(gap.fasim_only)}")
        print(f"benchmark.fasim_sim_gap.{gap.spec.label}.fasim_recall_vs_sim={pct(gap.shared_records, len(gap.sim.records)):.6f}")
        print(
            f"benchmark.fasim_sim_gap.{gap.spec.label}.region_support_vs_sim="
            f"{pct(gap.sim_region_supported_records, len(gap.sim.records)):.6f}"
        )
        print(f"benchmark.fasim_sim_gap.{gap.spec.label}.recovery_windows={gap.recovery.recovery_windows}")
        print(f"benchmark.fasim_sim_gap.{gap.spec.label}.recovery_boxes={gap.recovery.recovery_boxes}")
        print(f"benchmark.fasim_sim_gap.{gap.spec.label}.recovery_cells={gap.recovery.recovery_cells}")
        for category in categories:
            print(
                f"benchmark.fasim_sim_gap.{gap.spec.label}.category_{category}="
                f"{gap.category_counts.get(category, 0)}"
            )
    print(f"benchmark.fasim_sim_gap.total.sim_records={total_sim}")
    print(f"benchmark.fasim_sim_gap.total.fasim_records={total_fasim}")
    print(f"benchmark.fasim_sim_gap.total.shared_records={total_shared}")
    print(f"benchmark.fasim_sim_gap.total.sim_region_supported_records={total_region_supported}")
    print(f"benchmark.fasim_sim_gap.total.sim_only_records={total_sim_only}")
    print(f"benchmark.fasim_sim_gap.total.fasim_only_records={total_fasim_only}")
    print(f"benchmark.fasim_sim_gap.total.fasim_recall_vs_sim={pct(total_shared, total_sim):.6f}")
    print(f"benchmark.fasim_sim_gap.total.region_support_vs_sim={pct(total_region_supported, total_sim):.6f}")
    print(f"benchmark.fasim_sim_gap.total.recovery_windows={total_recovery_windows}")
    print(f"benchmark.fasim_sim_gap.total.recovery_boxes={total_recovery_boxes}")
    print(f"benchmark.fasim_sim_gap.total.recovery_cells={total_recovery_cells}")
    for category in categories:
        print(f"benchmark.fasim_sim_gap.total.category_{category}={aggregate_categories.get(category, 0)}")

    report = "\n".join(lines)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report + "\n", encoding="utf-8")
    return report


def render_recovery_shadow_report(
    *,
    gaps: Sequence[WorkloadGap],
    output_path: Path,
    profile_set: str,
    margin_bp: int,
    merge_gap_bp: int,
) -> str:
    shadows = [gap.recovery_shadow for gap in gaps if gap.recovery_shadow is not None]
    if len(shadows) != len(gaps):
        raise RuntimeError("recovery shadow report requested without recovery shadow data")

    lines: List[str] = []
    lines.append("# Fasim Local SIM Recovery Shadow")
    lines.append("")
    lines.append("Base branch:")
    lines.append("")
    lines.append("```text")
    lines.append("fasim-sim-gap-taxonomy")
    lines.append("```")
    lines.append("")
    lines.append(
        "This report is diagnostic-only. It builds local recovery boxes from "
        "Fasim-supported SIM gaps and checks which legacy SIM-only records would "
        "fall inside those boxes. It does not add recovered records to Fasim "
        "output and does not change scoring, threshold, non-overlap, filter, or "
        "GPU behavior."
    )
    lines.append("")
    lines.append(
        "The shadow uses the full legacy `-F` SIM output as an oracle to estimate "
        "local recovery coverage. It is not a production local-SIM implementation "
        "and should not be treated as a production accuracy claim."
    )
    lines.append("")
    lines.append(
        "Because this is an oracle feasibility shadow, the boxes are selected from "
        "known SIM-only taxonomy records and their overlapping Fasim records. A "
        "deployable path still needs an independent risk detector and a bounded "
        "local SIM executor."
    )
    lines.append("")
    append_table(
        lines,
        ["Setting", "Value"],
        [
            ["profile_set", profile_set],
            ["box_source", "overlapping Fasim records"],
            ["margin_bp", str(margin_bp)],
            ["merge_gap_bp", str(merge_gap_bp)],
            ["output_mutations_expected", "0"],
        ],
    )
    lines.append("")

    rows: List[List[str]] = []
    total_boxes = 0
    total_windows = 0
    total_cells = 0
    total_full_search_cells = 0
    total_seconds = 0.0
    total_sim_only = 0
    total_recovered = 0
    total_unrecovered = 0
    total_candidates = 0
    total_output_mutations = 0
    aggregate_sim_only_by_category: Counter = Counter()
    aggregate_recovered_by_category: Counter = Counter()
    aggregate_category_boxes: Counter = Counter()
    aggregate_category_cells: Counter = Counter()

    for gap in gaps:
        shadow = gap.recovery_shadow
        if shadow is None:
            continue
        total_boxes += len(shadow.boxes)
        total_windows += shadow.windows
        total_cells += shadow.cells
        total_full_search_cells += shadow.full_search_cells
        total_seconds += shadow.seconds
        total_sim_only += shadow.sim_only_records
        total_recovered += shadow.recovered_records
        total_unrecovered += shadow.unrecovered_records
        total_candidates += shadow.candidate_records
        total_output_mutations += shadow.output_mutations
        aggregate_sim_only_by_category.update(shadow.sim_only_by_category)
        aggregate_recovered_by_category.update(shadow.recovered_by_category)
        for box in shadow.boxes:
            for category in box.categories:
                aggregate_category_boxes.update([category])
                aggregate_category_cells[category] += box_cells(box)
        rows.append(
            [
                shadow.workload_label,
                str(shadow.sim_only_records),
                str(shadow.recovered_records),
                str(shadow.unrecovered_records),
                fmt_pct(shadow.recall),
                str(len(shadow.boxes)),
                str(shadow.windows),
                str(shadow.cells),
                str(shadow.full_search_cells),
                fmt_pct(shadow.cell_fraction),
                f"{shadow.seconds:.6f}",
                str(shadow.candidate_records),
                str(shadow.output_mutations),
            ]
        )

    lines.append("## Workload Summary")
    lines.append("")
    append_table(
        lines,
        [
            "Workload",
            "SIM-only",
            "Recovered",
            "Unrecovered",
            "Recovery recall",
            "Boxes",
            "Windows",
            "Cells",
            "Full-search cells",
            "Cell fraction",
            "Shadow seconds",
            "Candidate SIM records",
            "Output mutations",
        ],
        rows,
    )
    lines.append("")

    lines.append("## Category Summary")
    lines.append("")
    append_table(
        lines,
        ["Category", "SIM-only", "Recovered", "Recall", "Boxes", "Cells", "Seconds"],
        [
            [
                category,
                str(aggregate_sim_only_by_category.get(category, 0)),
                str(aggregate_recovered_by_category.get(category, 0)),
                fmt_pct(
                    pct(
                        aggregate_recovered_by_category.get(category, 0),
                        aggregate_sim_only_by_category.get(category, 0),
                    )
                ),
                str(aggregate_category_boxes.get(category, 0)),
                str(aggregate_category_cells.get(category, 0)),
                f"{total_seconds:.6f}",
            ]
            for category in GAP_CATEGORIES
        ],
    )
    lines.append("")
    lines.append(
        "Box and cell counts in the category table are non-exclusive because a "
        "merged box can cover multiple gap categories."
    )
    lines.append("")

    lines.append("## Aggregate")
    lines.append("")
    append_table(
        lines,
        ["Metric", "Value"],
        [
            ["fasim_sim_recovery_shadow_enabled", "1"],
            ["fasim_sim_recovery_shadow_boxes", str(total_boxes)],
            ["fasim_sim_recovery_shadow_windows", str(total_windows)],
            ["fasim_sim_recovery_shadow_cells", str(total_cells)],
            ["fasim_sim_recovery_shadow_full_search_cells", str(total_full_search_cells)],
            ["fasim_sim_recovery_shadow_cell_fraction", fmt_pct(pct(total_cells, total_full_search_cells))],
            ["fasim_sim_recovery_shadow_seconds", f"{total_seconds:.6f}"],
            ["fasim_sim_recovery_shadow_sim_only_records", str(total_sim_only)],
            ["fasim_sim_recovery_shadow_recovered_records", str(total_recovered)],
            ["fasim_sim_recovery_shadow_unrecovered_records", str(total_unrecovered)],
            ["fasim_sim_recovery_shadow_recovery_recall", fmt_pct(pct(total_recovered, total_sim_only))],
            ["fasim_sim_recovery_shadow_candidate_records", str(total_candidates)],
            ["fasim_sim_recovery_shadow_output_mutations", str(total_output_mutations)],
        ],
    )
    lines.append("")

    lines.append("## Decision")
    lines.append("")
    recall = pct(total_recovered, total_sim_only)
    if total_output_mutations != 0:
        decision = "Stop: the shadow observed output mutations, which violates diagnostic-only scope."
    elif recall >= 80.0:
        decision = (
            "Local recovery boxes cover most SIM-only records on these synthetic "
            "fixtures. A real local SIM recovery shadow that executes bounded SIM "
            "inside boxes is a plausible next PR."
        )
    elif recall >= 50.0:
        decision = (
            "Local recovery boxes cover part of the SIM-only set. Improve box "
            "selection before designing a real opt-in recovery path."
        )
    else:
        decision = (
            "Local recovery boxes do not cover enough SIM-only records. SIM-close "
            "mode is likely too expensive or needs a different risk detector."
        )
    lines.append(decision)
    lines.append("")
    lines.append("Forbidden-scope check:")
    lines.append("")
    lines.append("```text")
    lines.append("Fasim output change: no")
    lines.append("Recovered records added to output: no")
    lines.append("Scoring/threshold/non-overlap behavior change: no")
    lines.append("GPU/filter behavior change: no")
    lines.append("Production accuracy claim: no")
    lines.append("```")
    lines.append("")

    for shadow in shadows:
        print(f"benchmark.fasim_sim_recovery_shadow.{shadow.workload_label}.enabled=1")
        print(f"benchmark.fasim_sim_recovery_shadow.{shadow.workload_label}.boxes={len(shadow.boxes)}")
        print(f"benchmark.fasim_sim_recovery_shadow.{shadow.workload_label}.windows={shadow.windows}")
        print(f"benchmark.fasim_sim_recovery_shadow.{shadow.workload_label}.cells={shadow.cells}")
        print(f"benchmark.fasim_sim_recovery_shadow.{shadow.workload_label}.full_search_cells={shadow.full_search_cells}")
        print(f"benchmark.fasim_sim_recovery_shadow.{shadow.workload_label}.cell_fraction={shadow.cell_fraction:.6f}")
        print(f"benchmark.fasim_sim_recovery_shadow.{shadow.workload_label}.seconds={shadow.seconds:.6f}")
        print(f"benchmark.fasim_sim_recovery_shadow.{shadow.workload_label}.sim_only_records={shadow.sim_only_records}")
        print(f"benchmark.fasim_sim_recovery_shadow.{shadow.workload_label}.recovered_records={shadow.recovered_records}")
        print(f"benchmark.fasim_sim_recovery_shadow.{shadow.workload_label}.unrecovered_records={shadow.unrecovered_records}")
        print(f"benchmark.fasim_sim_recovery_shadow.{shadow.workload_label}.recovery_recall={shadow.recall:.6f}")
        print(f"benchmark.fasim_sim_recovery_shadow.{shadow.workload_label}.candidate_records={shadow.candidate_records}")
        print(f"benchmark.fasim_sim_recovery_shadow.{shadow.workload_label}.output_mutations={shadow.output_mutations}")
        for category in GAP_CATEGORIES:
            print(
                f"benchmark.fasim_sim_recovery_shadow.{shadow.workload_label}.{category}_recovered="
                f"{shadow.recovered_by_category.get(category, 0)}"
            )

    print("benchmark.fasim_sim_recovery_shadow.total.enabled=1")
    print(f"benchmark.fasim_sim_recovery_shadow.total.boxes={total_boxes}")
    print(f"benchmark.fasim_sim_recovery_shadow.total.windows={total_windows}")
    print(f"benchmark.fasim_sim_recovery_shadow.total.cells={total_cells}")
    print(f"benchmark.fasim_sim_recovery_shadow.total.full_search_cells={total_full_search_cells}")
    print(f"benchmark.fasim_sim_recovery_shadow.total.cell_fraction={pct(total_cells, total_full_search_cells):.6f}")
    print(f"benchmark.fasim_sim_recovery_shadow.total.seconds={total_seconds:.6f}")
    print(f"benchmark.fasim_sim_recovery_shadow.total.sim_only_records={total_sim_only}")
    print(f"benchmark.fasim_sim_recovery_shadow.total.recovered_records={total_recovered}")
    print(f"benchmark.fasim_sim_recovery_shadow.total.unrecovered_records={total_unrecovered}")
    print(f"benchmark.fasim_sim_recovery_shadow.total.recovery_recall={pct(total_recovered, total_sim_only):.6f}")
    print(f"benchmark.fasim_sim_recovery_shadow.total.candidate_records={total_candidates}")
    print(f"benchmark.fasim_sim_recovery_shadow.total.output_mutations={total_output_mutations}")
    for category in GAP_CATEGORIES:
        print(
            f"benchmark.fasim_sim_recovery_shadow.total.{category}_recovered="
            f"{aggregate_recovered_by_category.get(category, 0)}"
        )

    report = "\n".join(lines)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report + "\n", encoding="utf-8")
    return report


def render_risk_detector_report(
    *,
    gaps: Sequence[WorkloadGap],
    output_path: Path,
    profile_set: str,
    margin_bp: int,
    merge_gap_bp: int,
) -> str:
    detectors = [gap.risk_detector for gap in gaps if gap.risk_detector is not None]
    if len(detectors) != len(gaps):
        raise RuntimeError("risk detector report requested without risk detector data")

    lines: List[str] = []
    lines.append("# Fasim SIM-Recovery Risk Detector")
    lines.append("")
    lines.append("Base branch:")
    lines.append("")
    lines.append("```text")
    lines.append("fasim-local-sim-recovery-shadow")
    lines.append("```")
    lines.append("")
    lines.append(
        "This report evaluates an independent Fasim-visible risk detector. Box "
        "selection uses only Fasim output record family/orientation and "
        "coordinates. This conservative baseline selects every Fasim output "
        "record as a local risk region; it does not use SIM-only record "
        "coordinates, taxonomy labels, legacy SIM output, or oracle boxes for "
        "selection."
    )
    lines.append("")
    lines.append(
        "Legacy `-F` SIM output is used only after detector selection to measure "
        "coverage of SIM-only records. The detector is diagnostic-only: it does "
        "not change Fasim output and does not run bounded local SIM recovery."
    )
    lines.append("")
    append_table(
        lines,
        ["Setting", "Value"],
        [
            ["profile_set", profile_set],
            ["detector_mode", "all_fasim_records_baseline"],
            ["box_source", "Fasim output records only"],
            ["margin_bp", str(margin_bp)],
            ["merge_gap_bp", str(merge_gap_bp)],
            ["output_mutations_expected", "0"],
        ],
    )
    lines.append("")

    rows: List[List[str]] = []
    total_boxes = 0
    total_cells = 0
    total_full_search_cells = 0
    total_seconds = 0.0
    total_sim_only = 0
    total_supported = 0
    total_unsupported = 0
    total_candidates = 0
    total_false_positive_boxes = 0
    total_output_mutations = 0
    aggregate_sim_only_by_category: Counter = Counter()
    aggregate_supported_by_category: Counter = Counter()

    for detector in detectors:
        total_boxes += len(detector.boxes)
        total_cells += detector.cells
        total_full_search_cells += detector.full_search_cells
        total_seconds += detector.seconds
        total_sim_only += detector.sim_only_records
        total_supported += detector.supported_sim_only_records
        total_unsupported += detector.unsupported_sim_only_records
        total_candidates += detector.candidate_records
        total_false_positive_boxes += detector.false_positive_boxes
        total_output_mutations += detector.output_mutations
        aggregate_sim_only_by_category.update(detector.sim_only_by_category)
        aggregate_supported_by_category.update(detector.supported_by_category)
        rows.append(
            [
                detector.workload_label,
                detector.mode,
                str(len(detector.boxes)),
                str(detector.cells),
                str(detector.full_search_cells),
                fmt_pct(detector.cell_fraction),
                str(detector.sim_only_records),
                str(detector.supported_sim_only_records),
                str(detector.unsupported_sim_only_records),
                fmt_pct(detector.recall),
                str(detector.false_positive_boxes),
                str(detector.output_mutations),
            ]
        )

    lines.append("## Workload Summary")
    lines.append("")
    append_table(
        lines,
        [
            "Workload",
            "Mode",
            "Boxes",
            "Cells",
            "Full-search cells",
            "Cell fraction",
            "SIM-only",
            "Covered",
            "Uncovered",
            "Recall",
            "False-positive boxes",
            "Output mutations",
        ],
        rows,
    )
    lines.append("")

    lines.append("## Category Summary")
    lines.append("")
    append_table(
        lines,
        ["Category", "SIM-only", "Covered", "Recall"],
        [
            [
                category,
                str(aggregate_sim_only_by_category.get(category, 0)),
                str(aggregate_supported_by_category.get(category, 0)),
                fmt_pct(
                    pct(
                        aggregate_supported_by_category.get(category, 0),
                        aggregate_sim_only_by_category.get(category, 0),
                    )
                ),
            ]
            for category in GAP_CATEGORIES
        ],
    )
    lines.append("")

    lines.append("## Aggregate")
    lines.append("")
    append_table(
        lines,
        ["Metric", "Value"],
        [
            ["fasim_sim_recovery_risk_detector_enabled", "1"],
            ["fasim_sim_recovery_risk_detector_boxes", str(total_boxes)],
            ["fasim_sim_recovery_risk_detector_cells", str(total_cells)],
            ["fasim_sim_recovery_risk_detector_full_search_cells", str(total_full_search_cells)],
            ["fasim_sim_recovery_risk_detector_cell_fraction", fmt_pct(pct(total_cells, total_full_search_cells))],
            ["fasim_sim_recovery_risk_detector_seconds", f"{total_seconds:.6f}"],
            ["fasim_sim_recovery_risk_detector_sim_only_records", str(total_sim_only)],
            ["fasim_sim_recovery_risk_detector_supported_sim_only_records", str(total_supported)],
            ["fasim_sim_recovery_risk_detector_unsupported_sim_only_records", str(total_unsupported)],
            ["fasim_sim_recovery_risk_detector_recall", fmt_pct(pct(total_supported, total_sim_only))],
            ["fasim_sim_recovery_risk_detector_candidate_records", str(total_candidates)],
            ["fasim_sim_recovery_risk_detector_false_positive_boxes", str(total_false_positive_boxes)],
            ["fasim_sim_recovery_risk_detector_output_mutations", str(total_output_mutations)],
        ],
    )
    lines.append("")

    lines.append("## Decision")
    lines.append("")
    recall = pct(total_supported, total_sim_only)
    cell_fraction = pct(total_cells, total_full_search_cells)
    if total_output_mutations != 0:
        decision = "Stop: detector evaluation observed output mutations, which violates diagnostic-only scope."
    elif recall >= 90.0 and cell_fraction <= 5.0:
        decision = (
            "The Fasim-visible detector covers most SIM-only records while keeping "
            "cell fraction small. A bounded local SIM executor shadow is a plausible "
            "next PR."
        )
    elif recall >= 60.0 and cell_fraction <= 5.0:
        decision = (
            "The detector has useful coverage but needs stronger risk features or "
            "box expansion before bounded local SIM execution."
        )
    elif cell_fraction > 5.0:
        decision = "Detector boxes are too broad; tune risk features before executor work."
    else:
        decision = "Detector recall is too low; improve risk features before executor work."
    lines.append(decision)
    lines.append("")
    lines.append("Forbidden-scope check:")
    lines.append("")
    lines.append("```text")
    lines.append("SIM-only coordinates used for selection: no")
    lines.append("Legacy SIM output used for selection: no")
    lines.append("Oracle boxes used for selection: no")
    lines.append("Fasim output change: no")
    lines.append("Recovered records added to output: no")
    lines.append("Scoring/threshold/non-overlap behavior change: no")
    lines.append("GPU/filter behavior change: no")
    lines.append("Production accuracy claim: no")
    lines.append("```")
    lines.append("")

    for detector in detectors:
        prefix = f"benchmark.fasim_sim_recovery_risk_detector.{detector.workload_label}"
        print(f"{prefix}.enabled=1")
        print(f"{prefix}.mode={detector.mode}")
        print(f"{prefix}.boxes={len(detector.boxes)}")
        print(f"{prefix}.cells={detector.cells}")
        print(f"{prefix}.full_search_cells={detector.full_search_cells}")
        print(f"{prefix}.cell_fraction={detector.cell_fraction:.6f}")
        print(f"{prefix}.seconds={detector.seconds:.6f}")
        print(f"{prefix}.sim_only_records={detector.sim_only_records}")
        print(f"{prefix}.supported_sim_only_records={detector.supported_sim_only_records}")
        print(f"{prefix}.unsupported_sim_only_records={detector.unsupported_sim_only_records}")
        print(f"{prefix}.recall={detector.recall:.6f}")
        print(f"{prefix}.candidate_records={detector.candidate_records}")
        print(f"{prefix}.false_positive_boxes={detector.false_positive_boxes}")
        print(f"{prefix}.output_mutations={detector.output_mutations}")
        for category in GAP_CATEGORIES:
            category_recall = pct(
                detector.supported_by_category.get(category, 0),
                detector.sim_only_by_category.get(category, 0),
            )
            print(f"{prefix}.{category}_covered={detector.supported_by_category.get(category, 0)}")
            print(f"{prefix}.{category}_recall={category_recall:.6f}")

    print("benchmark.fasim_sim_recovery_risk_detector.total.enabled=1")
    print("benchmark.fasim_sim_recovery_risk_detector.total.mode=all_fasim_records_baseline")
    print(f"benchmark.fasim_sim_recovery_risk_detector.total.boxes={total_boxes}")
    print(f"benchmark.fasim_sim_recovery_risk_detector.total.cells={total_cells}")
    print(f"benchmark.fasim_sim_recovery_risk_detector.total.full_search_cells={total_full_search_cells}")
    print(f"benchmark.fasim_sim_recovery_risk_detector.total.cell_fraction={pct(total_cells, total_full_search_cells):.6f}")
    print(f"benchmark.fasim_sim_recovery_risk_detector.total.seconds={total_seconds:.6f}")
    print(f"benchmark.fasim_sim_recovery_risk_detector.total.sim_only_records={total_sim_only}")
    print(f"benchmark.fasim_sim_recovery_risk_detector.total.supported_sim_only_records={total_supported}")
    print(f"benchmark.fasim_sim_recovery_risk_detector.total.unsupported_sim_only_records={total_unsupported}")
    print(f"benchmark.fasim_sim_recovery_risk_detector.total.recall={pct(total_supported, total_sim_only):.6f}")
    print(f"benchmark.fasim_sim_recovery_risk_detector.total.candidate_records={total_candidates}")
    print(f"benchmark.fasim_sim_recovery_risk_detector.total.false_positive_boxes={total_false_positive_boxes}")
    print(f"benchmark.fasim_sim_recovery_risk_detector.total.output_mutations={total_output_mutations}")
    for category in GAP_CATEGORIES:
        category_recall = pct(
            aggregate_supported_by_category.get(category, 0),
            aggregate_sim_only_by_category.get(category, 0),
        )
        print(f"benchmark.fasim_sim_recovery_risk_detector.total.{category}_covered={aggregate_supported_by_category.get(category, 0)}")
        print(f"benchmark.fasim_sim_recovery_risk_detector.total.{category}_recall={category_recall:.6f}")

    print(
        "benchmark.fasim_sim_recovery_risk_detector.total.internal_peak_recall="
        f"{pct(aggregate_supported_by_category.get('long_hit_internal_peak', 0), aggregate_sim_only_by_category.get('long_hit_internal_peak', 0)):.6f}"
    )

    report = "\n".join(lines)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report + "\n", encoding="utf-8")
    return report


def fixtures_for(profile_set: str) -> List[FixtureSpec]:
    if profile_set == "smoke":
        return SMOKE_FIXTURES
    if profile_set == "small_medium":
        return SMALL_MEDIUM_FIXTURES
    if profile_set == "representative":
        return REPRESENTATIVE_FIXTURES
    raise RuntimeError(f"unknown profile set: {profile_set}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bin", default=str(ROOT / "fasim_longtarget_x86"))
    parser.add_argument("--profile-set", choices=("smoke", "small_medium", "representative"), default="small_medium")
    parser.add_argument("--work-dir", default=str(ROOT / ".tmp" / "fasim_sim_gap_taxonomy"))
    parser.add_argument("--output", default=str(ROOT / "docs" / "fasim_sim_gap_taxonomy.md"))
    parser.add_argument("--require-profile", action="store_true")
    parser.add_argument("--require-sim-gap-taxonomy", action="store_true")
    parser.add_argument("--recovery-shadow", action="store_true")
    parser.add_argument("--recovery-shadow-output", default=str(ROOT / "docs" / "fasim_local_sim_recovery_shadow.md"))
    parser.add_argument("--recovery-shadow-margin-bp", type=int, default=32)
    parser.add_argument("--risk-detector", action="store_true")
    parser.add_argument("--risk-detector-output", default=str(ROOT / "docs" / "fasim_sim_recovery_risk_detector.md"))
    parser.add_argument("--risk-detector-margin-bp", type=int, default=32)
    parser.add_argument("--near-tie-delta", type=float, default=1.0)
    parser.add_argument("--threshold-score-band", type=float, default=5.0)
    parser.add_argument("--long-hit-nt", type=int, default=80)
    parser.add_argument("--merge-gap-bp", type=int, default=32)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        bin_path = Path(args.bin)
        if not bin_path.is_absolute():
            bin_path = (ROOT / bin_path).resolve()
        if not bin_path.exists():
            raise RuntimeError(f"missing Fasim binary: {bin_path}")

        recovery_shadow_enabled = args.recovery_shadow or os.environ.get("FASIM_SIM_RECOVERY_SHADOW") == "1"
        risk_detector_enabled = args.risk_detector or os.environ.get("FASIM_SIM_RECOVERY_RISK_DETECTOR") == "1"
        work_dir_base = Path(args.work_dir)
        gaps: List[WorkloadGap] = []
        for spec in fixtures_for(args.profile_set):
            sim = run_mode(
                bin_path=bin_path,
                spec=spec,
                mode="sim",
                work_dir=work_dir_base / spec.label / "sim",
                require_profile=args.require_profile,
            )
            fasim = run_mode(
                bin_path=bin_path,
                spec=spec,
                mode="fasim",
                work_dir=work_dir_base / spec.label / "fasim",
                require_profile=args.require_profile,
            )
            gaps.append(
                analyze_gap(
                    spec=spec,
                    sim=sim,
                    fasim=fasim,
                    near_tie_delta=args.near_tie_delta,
                    threshold_score_band=args.threshold_score_band,
                    long_hit_nt=args.long_hit_nt,
                    merge_gap_bp=args.merge_gap_bp,
                    recovery_shadow_enabled=recovery_shadow_enabled,
                    recovery_shadow_margin_bp=args.recovery_shadow_margin_bp,
                    risk_detector_enabled=risk_detector_enabled,
                    risk_detector_margin_bp=args.risk_detector_margin_bp,
                )
            )

        if args.require_sim_gap_taxonomy:
            missing = [
                gap.spec.label
                for gap in gaps
                if len(gap.sim.records) == 0 and len(gap.fasim.records) == 0
            ]
            if missing:
                raise RuntimeError("empty SIM/Fasim comparisons: " + ", ".join(missing))

        print(
            render_report(
                gaps=gaps,
                output_path=Path(args.output),
                profile_set=args.profile_set,
                near_tie_delta=args.near_tie_delta,
                threshold_score_band=args.threshold_score_band,
                long_hit_nt=args.long_hit_nt,
                merge_gap_bp=args.merge_gap_bp,
            )
        )
        if recovery_shadow_enabled:
            print(
                render_recovery_shadow_report(
                    gaps=gaps,
                    output_path=Path(args.recovery_shadow_output),
                    profile_set=args.profile_set,
                    margin_bp=args.recovery_shadow_margin_bp,
                    merge_gap_bp=args.merge_gap_bp,
                )
            )
        if risk_detector_enabled:
            print(
                render_risk_detector_report(
                    gaps=gaps,
                    output_path=Path(args.risk_detector_output),
                    profile_set=args.profile_set,
                    margin_bp=args.risk_detector_margin_bp,
                    merge_gap_bp=args.merge_gap_bp,
                )
            )
        return 0
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
