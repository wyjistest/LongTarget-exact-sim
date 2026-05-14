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
class SequenceEntry:
    chr_name: str
    start: int
    end: int
    sequence: str


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
class ExecutorShadow:
    workload_label: str
    boxes: List[RecoveryBox]
    seconds: float
    full_search_cells: int
    sim_only_records: int
    recovered_records: int
    unrecovered_records: int
    candidate_records: int
    output_mutations: int
    executor_failures: int
    unsupported_boxes: int
    recovered_by_category: Counter
    sim_only_by_category: Counter
    candidate_records_raw: frozenset[str]

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
class IntegrationShadow:
    workload_label: str
    fasim_records: int
    recovered_candidates: int
    unique_recovered_records: int
    duplicate_recovered_records: int
    integrated_records: int
    sim_records: int
    sim_only_records: int
    sim_only_recovered: int
    shared_records_vs_sim: int
    extra_records_vs_sim: int
    nonoverlap_conflicts: int
    output_mutations: int
    recovered_by_category: Counter
    sim_only_by_category: Counter

    @property
    def recall_vs_sim(self) -> float:
        return pct(self.shared_records_vs_sim, self.sim_records)

    @property
    def precision_vs_sim(self) -> float:
        return pct(self.shared_records_vs_sim, self.integrated_records)


@dataclasses.dataclass(frozen=True)
class FilterStrategyResult:
    workload_label: str
    strategy: str
    recovered_candidates: int
    filtered_candidates: int
    integrated_records: int
    sim_only_recovered: int
    shared_records_vs_sim: int
    sim_records: int
    extra_records_vs_sim: int
    overlap_conflicts_before: int
    overlap_conflicts_after: int
    output_mutations: int
    oracle: bool

    @property
    def recall_vs_sim(self) -> float:
        return pct(self.shared_records_vs_sim, self.sim_records)

    @property
    def precision_vs_sim(self) -> float:
        return pct(self.shared_records_vs_sim, self.integrated_records)


@dataclasses.dataclass(frozen=True)
class FilterShadow:
    workload_label: str
    recovered_candidates: int
    fasim_duplicates: int
    near_duplicates: int
    sim_only_matches: int
    extra_vs_sim: int
    overlap_conflicts_before: int
    nested_candidates: int
    internal_peak_candidates: int
    unknown_candidates: int
    output_mutations: int
    strategies: Tuple[FilterStrategyResult, ...]


@dataclasses.dataclass(frozen=True)
class ReplacementStrategyResult:
    workload_label: str
    strategy: str
    fasim_records: int
    recovered_candidates: int
    fasim_records_suppressed: int
    recovered_records_accepted: int
    integrated_records: int
    sim_records: int
    sim_only_recovered: int
    shared_records_vs_sim: int
    extra_records_vs_sim: int
    overlap_conflicts: int
    output_mutations: int
    oracle: bool

    @property
    def recall_vs_sim(self) -> float:
        return pct(self.shared_records_vs_sim, self.sim_records)

    @property
    def precision_vs_sim(self) -> float:
        return pct(self.shared_records_vs_sim, self.integrated_records)


@dataclasses.dataclass(frozen=True)
class ReplacementShadow:
    workload_label: str
    fasim_records: int
    recovered_candidates: int
    output_mutations: int
    strategies: Tuple[ReplacementStrategyResult, ...]


@dataclasses.dataclass(frozen=True)
class ExtraCandidateFeature:
    raw: str
    true_sim_record: bool
    score: float
    nt: int
    genome_length: int
    query_length: int
    local_rank: int
    family_rank: int
    dominated_by_higher_score: bool
    contained_in_fasim: bool
    overlaps_fasim: bool
    boundary_distance: int
    conflict_degree: int
    box_cells: int
    nested_candidate: bool
    internal_peak_candidate: bool


@dataclasses.dataclass(frozen=True)
class ExtraGuardResult:
    workload_label: str
    guard: str
    selected_candidates: int
    integrated_records: int
    sim_records: int
    sim_only_recovered: int
    shared_records_vs_sim: int
    extra_records_vs_sim: int
    overlap_conflicts: int
    output_mutations: int
    oracle: bool

    @property
    def recall_vs_sim(self) -> float:
        return pct(self.shared_records_vs_sim, self.sim_records)

    @property
    def precision_vs_sim(self) -> float:
        return pct(self.shared_records_vs_sim, self.integrated_records)


@dataclasses.dataclass(frozen=True)
class ReplacementExtraTaxonomy:
    workload_label: str
    true_sim_records: int
    extra_records: int
    score_min_true: float
    score_min_extra: float
    nt_min_true: int
    nt_min_extra: int
    rank_true_p50: float
    rank_extra_p50: float
    dominated_true: int
    dominated_extra: int
    contained_true: int
    contained_extra: int
    boundary_distance_true_p50: float
    boundary_distance_extra_p50: float
    overlap_conflicts: int
    output_mutations: int
    guards: Tuple[ExtraGuardResult, ...]


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
    executor_shadow: Optional[ExecutorShadow] = None
    integration_shadow: Optional[IntegrationShadow] = None
    filter_shadow: Optional[FilterShadow] = None
    replacement_shadow: Optional[ReplacementShadow] = None
    replacement_extra_taxonomy: Optional[ReplacementExtraTaxonomy] = None


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


def read_fasta_entries(path: Path) -> List[Tuple[str, str]]:
    entries: List[Tuple[str, str]] = []
    header: Optional[str] = None
    chunks: List[str] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith(">"):
            if header is not None:
                entries.append((header, "".join(chunks)))
            header = line[1:]
            chunks = []
            continue
        chunks.append(line)
    if header is not None:
        entries.append((header, "".join(chunks)))
    if not entries:
        raise RuntimeError(f"empty FASTA: {path}")
    return entries


def parse_genomic_header(header: str) -> Tuple[str, int, int]:
    parts = header.split("|")
    if len(parts) < 3:
        raise RuntimeError(f"unsupported genomic FASTA header: {header}")
    start_text, sep, end_text = parts[2].partition("-")
    if not sep:
        raise RuntimeError(f"unsupported genomic FASTA interval: {header}")
    return (parts[1], int(start_text), int(end_text))


def fixture_dna_entries(spec: FixtureSpec) -> List[SequenceEntry]:
    if spec.label == "tiny" and spec.dna_entries == 1 and spec.dna_repeat == 1:
        entries = read_fasta_entries(ROOT / "testDNA.fa")
        sequence_entries: List[SequenceEntry] = []
        for header, sequence in entries:
            chr_name, start, end = parse_genomic_header(header)
            sequence_entries.append(SequenceEntry(chr_name=chr_name, start=start, end=end, sequence=sequence))
        return sequence_entries

    base_sequence = read_fasta_sequence(ROOT / "testDNA.fa")
    tiled = base_sequence * spec.dna_repeat
    entries: List[SequenceEntry] = []
    for index in range(spec.dna_entries):
        start = index * len(tiled) + 1
        end = start + len(tiled) - 1
        entries.append(SequenceEntry(chr_name="chr11", start=start, end=end, sequence=tiled))
    return entries


def write_fasta(path: Path, header: str, sequence: str) -> None:
    with path.open("w", encoding="utf-8") as handle:
        handle.write(f">{header}\n")
        for index in range(0, len(sequence), 80):
            handle.write(sequence[index : index + 80])
            handle.write("\n")


def canonical_lite_records_or_empty(output_dir: Path) -> List[str]:
    records: List[str] = []
    paths = sorted(output_dir.glob("*-TFOsorted.lite"))
    if not paths:
        return records
    for path in paths:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            for line_no, line in enumerate(handle):
                line = line.rstrip("\n").rstrip("\r")
                if not line:
                    continue
                if line_no == 0 and line.startswith("Chr\tStartInGenome\t"):
                    continue
                records.append(line)
    records.sort()
    return records


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


def record_in_box(record: TriplexRecord, box: RecoveryBox) -> bool:
    return (
        record.family == box.family
        and contains(box.genome_interval, record.genome_interval)
        and contains(box.query_interval, record.query_interval)
    )


def containing_dna_entry(box: RecoveryBox, entries: Sequence[SequenceEntry]) -> Optional[Tuple[SequenceEntry, Tuple[int, int]]]:
    overlapping = [
        entry
        for entry in entries
        if entry.chr_name == box.family[0]
        and overlaps((entry.start, entry.end), box.genome_interval)
    ]
    if len(overlapping) != 1:
        return None
    entry = overlapping[0]
    clipped = (max(box.genome_interval[0], entry.start), min(box.genome_interval[1], entry.end))
    if clipped[0] > clipped[1]:
        return None
    return (entry, clipped)


def translate_local_record(
    record: TriplexRecord,
    *,
    dna_entry_start: int,
    dna_interval_start: int,
    query_interval_start: int,
) -> TriplexRecord:
    fields = record.raw.split("\t")
    dna_offset = dna_interval_start - dna_entry_start
    query_offset = query_interval_start - 1
    fields[5] = str(parse_int(fields[5], "QueryStart", record.raw) + query_offset)
    fields[6] = str(parse_int(fields[6], "QueryEnd", record.raw) + query_offset)
    fields[7] = str(parse_int(fields[7], "StartInSeq", record.raw) + dna_offset)
    fields[8] = str(parse_int(fields[8], "EndInSeq", record.raw) + dna_offset)
    return parse_lite_record("\t".join(fields))


def run_executor_box(
    *,
    bin_path: Path,
    box: RecoveryBox,
    box_index: int,
    work_dir: Path,
    dna_entries: Sequence[SequenceEntry],
    query_sequence: str,
) -> Tuple[List[TriplexRecord], bool, bool]:
    dna_match = containing_dna_entry(box, dna_entries)
    if dna_match is None:
        return ([], True, False)
    dna_entry, dna_interval = dna_match
    query_interval = (
        max(1, box.query_interval[0]),
        min(len(query_sequence), box.query_interval[1]),
    )
    if query_interval[0] > query_interval[1]:
        return ([], True, False)

    box_dir = work_dir / f"box_{box_index:04d}"
    if box_dir.exists():
        shutil.rmtree(box_dir)
    inputs_dir = box_dir / "inputs"
    output_dir = box_dir / "out"
    inputs_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    dna_start = dna_interval[0] - dna_entry.start
    dna_end = dna_interval[1] - dna_entry.start + 1
    query_start = query_interval[0] - 1
    query_end = query_interval[1]
    write_fasta(
        inputs_dir / "boxDNA.fa",
        f"hg19|{dna_entry.chr_name}|{dna_interval[0]}-{dna_interval[1]}",
        dna_entry.sequence[dna_start:dna_end],
    )
    write_fasta(inputs_dir / "boxRNA.fa", "H19", query_sequence[query_start:query_end])

    env = os.environ.copy()
    env["FASIM_VERBOSE"] = "0"
    env["FASIM_OUTPUT_MODE"] = "lite"
    env["FASIM_EXTEND_THREADS"] = "1"
    proc = subprocess.run(
        [
            str(bin_path),
            "-f1",
            "boxDNA.fa",
            "-f2",
            "boxRNA.fa",
            "-r",
            "1",
            "-O",
            str(output_dir),
            "-F",
        ],
        cwd=str(inputs_dir),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    (box_dir / "stdout.log").write_text(proc.stdout, encoding="utf-8")
    (box_dir / "stderr.log").write_text(proc.stderr, encoding="utf-8")
    if proc.returncode != 0:
        return ([], False, True)

    translated: List[TriplexRecord] = []
    for record in parse_lite_records(canonical_lite_records_or_empty(output_dir)):
        translated_record = translate_local_record(
            record,
            dna_entry_start=dna_entry.start,
            dna_interval_start=dna_interval[0],
            query_interval_start=query_interval[0],
        )
        if record_in_box(translated_record, box):
            translated.append(translated_record)
    return (translated, False, False)


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


def build_bounded_local_sim_executor_shadow(
    *,
    spec: FixtureSpec,
    bin_path: Path,
    boxes: Sequence[RecoveryBox],
    sim_only: Sequence[GapRecord],
    work_dir: Path,
) -> ExecutorShadow:
    start = time.perf_counter()
    if work_dir.exists():
        shutil.rmtree(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    dna_entries = fixture_dna_entries(spec)
    query_sequence = read_fasta_sequence(ROOT / "H19.fa")
    recovered_raw: Set[str] = set()
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

    recovered_by_category: Counter = Counter()
    sim_only_by_category: Counter = Counter(gap.primary for gap in sim_only)
    for gap in sim_only:
        if gap.record.raw in candidate_raw:
            recovered_raw.add(gap.record.raw)
            recovered_by_category.update([gap.primary])

    seconds = time.perf_counter() - start
    return ExecutorShadow(
        workload_label=spec.label,
        boxes=list(boxes),
        seconds=seconds,
        full_search_cells=fixture_full_search_cells(spec),
        sim_only_records=len(sim_only),
        recovered_records=len(recovered_raw),
        unrecovered_records=len(sim_only) - len(recovered_raw),
        candidate_records=len(candidate_raw),
        output_mutations=0,
        executor_failures=executor_failures,
        unsupported_boxes=unsupported_boxes,
        recovered_by_category=recovered_by_category,
        sim_only_by_category=sim_only_by_category,
        candidate_records_raw=frozenset(candidate_raw),
    )


def count_same_family_genomic_overlaps(records: Sequence[TriplexRecord]) -> int:
    by_family: Dict[Tuple[str, str, str], List[TriplexRecord]] = defaultdict(list)
    for record in records:
        by_family[record.family].append(record)

    conflicts = 0
    for family_records in by_family.values():
        ordered = sorted(family_records, key=lambda record: (record.genome_interval[0], record.genome_interval[1], record.raw))
        active: List[TriplexRecord] = []
        for record in ordered:
            active = [candidate for candidate in active if candidate.genome_interval[1] >= record.genome_interval[0]]
            for candidate in active:
                if overlaps(candidate.genome_interval, record.genome_interval):
                    conflicts += 1
            active.append(record)
    return conflicts


def records_overlap_in_both_axes(left: TriplexRecord, right: TriplexRecord) -> bool:
    return (
        left.family == right.family
        and overlaps(left.genome_interval, right.genome_interval)
        and overlaps(left.query_interval, right.query_interval)
    )


def is_near_duplicate_candidate(record: TriplexRecord, fasim_records: Sequence[TriplexRecord]) -> bool:
    return any(records_overlap_in_both_axes(record, fasim_record) for fasim_record in fasim_records)


def is_nested_candidate(record: TriplexRecord, fasim_records: Sequence[TriplexRecord]) -> bool:
    return any(
        record.family == fasim_record.family
        and contains(fasim_record.genome_interval, record.genome_interval)
        and contains(fasim_record.query_interval, record.query_interval)
        for fasim_record in fasim_records
    )


def is_internal_peak_candidate(record: TriplexRecord, fasim_records: Sequence[TriplexRecord]) -> bool:
    return any(
        record.family == fasim_record.family
        and contains(fasim_record.genome_interval, record.genome_interval)
        and contains(fasim_record.query_interval, record.query_interval)
        and fasim_record.nt > record.nt
        for fasim_record in fasim_records
    )


def is_interval_dominated(record: TriplexRecord, references: Sequence[TriplexRecord]) -> bool:
    return any(
        reference.raw != record.raw
        and reference.family == record.family
        and contains(reference.genome_interval, record.genome_interval)
        and contains(reference.query_interval, record.query_interval)
        and reference.score >= record.score
        for reference in references
    )


def evaluate_filter_strategy(
    *,
    workload_label: str,
    strategy: str,
    selected_candidate_raw: Set[str],
    candidate_raw: Set[str],
    fasim_raw: Set[str],
    sim_raw: Set[str],
    sim_only_raw: Set[str],
    overlap_conflicts_before: int,
    oracle: bool,
) -> FilterStrategyResult:
    integrated_raw = fasim_raw | selected_candidate_raw
    integrated_records = parse_lite_records(sorted(integrated_raw))
    shared_records_vs_sim = integrated_raw & sim_raw
    return FilterStrategyResult(
        workload_label=workload_label,
        strategy=strategy,
        recovered_candidates=len(candidate_raw),
        filtered_candidates=len(selected_candidate_raw),
        integrated_records=len(integrated_raw),
        sim_only_recovered=len(sim_only_raw & integrated_raw),
        shared_records_vs_sim=len(shared_records_vs_sim),
        sim_records=len(sim_raw),
        extra_records_vs_sim=len(integrated_raw - sim_raw),
        overlap_conflicts_before=overlap_conflicts_before,
        overlap_conflicts_after=count_same_family_genomic_overlaps(integrated_records),
        output_mutations=0,
        oracle=oracle,
    )


def evaluate_replacement_strategy(
    *,
    workload_label: str,
    strategy: str,
    fasim_raw: Set[str],
    candidate_raw: Set[str],
    suppressed_fasim_raw: Set[str],
    accepted_candidate_raw: Set[str],
    sim_raw: Set[str],
    sim_only_raw: Set[str],
    oracle: bool = False,
) -> ReplacementStrategyResult:
    integrated_raw = (fasim_raw - suppressed_fasim_raw) | accepted_candidate_raw
    integrated_records = parse_lite_records(sorted(integrated_raw))
    shared_records_vs_sim = integrated_raw & sim_raw
    return ReplacementStrategyResult(
        workload_label=workload_label,
        strategy=strategy,
        fasim_records=len(fasim_raw),
        recovered_candidates=len(candidate_raw),
        fasim_records_suppressed=len(suppressed_fasim_raw),
        recovered_records_accepted=len(accepted_candidate_raw),
        integrated_records=len(integrated_raw),
        sim_records=len(sim_raw),
        sim_only_recovered=len(sim_only_raw & integrated_raw),
        shared_records_vs_sim=len(shared_records_vs_sim),
        extra_records_vs_sim=len(integrated_raw - sim_raw),
        overlap_conflicts=count_same_family_genomic_overlaps(integrated_records),
        output_mutations=0,
        oracle=oracle,
    )


def records_by_box(
    records: Sequence[TriplexRecord],
    boxes: Sequence[RecoveryBox],
) -> Tuple[Set[str], Dict[int, Set[str]]]:
    contained: Set[str] = set()
    per_box: Dict[int, Set[str]] = {}
    for index, box in enumerate(boxes):
        raw_in_box = {record.raw for record in records if record_in_box(record, box)}
        per_box[index] = raw_in_box
        contained.update(raw_in_box)
    return contained, per_box


def candidate_order_key(record: TriplexRecord) -> Tuple[float, int, int, int, str]:
    return (-record.score, -record.nt, record.genome_interval[0], record.query_interval[0], record.raw)


def median_value(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return float(ordered[middle])
    return float(ordered[middle - 1] + ordered[middle]) / 2.0


def min_float(values: Sequence[float]) -> float:
    return min(values) if values else 0.0


def min_int(values: Sequence[int]) -> int:
    return min(values) if values else 0


def candidate_local_ranks(
    records: Sequence[TriplexRecord],
    boxes: Sequence[RecoveryBox],
) -> Dict[str, int]:
    ranks: Dict[str, int] = {record.raw: 0 for record in records}
    for box in boxes:
        in_box = [record for record in records if record_in_box(record, box)]
        for rank, record in enumerate(sorted(in_box, key=candidate_order_key), start=1):
            previous = ranks.get(record.raw, 0)
            if previous == 0 or rank < previous:
                ranks[record.raw] = rank
    return ranks


def candidate_family_ranks(records: Sequence[TriplexRecord]) -> Dict[str, int]:
    by_family: Dict[Tuple[str, str, str], List[TriplexRecord]] = defaultdict(list)
    for record in records:
        by_family[record.family].append(record)
    ranks: Dict[str, int] = {}
    for family_records in by_family.values():
        for rank, record in enumerate(sorted(family_records, key=candidate_order_key), start=1):
            ranks[record.raw] = rank
    return ranks


def candidate_box_cells(
    record: TriplexRecord,
    boxes: Sequence[RecoveryBox],
) -> int:
    cells = [box_cells(box) for box in boxes if record_in_box(record, box)]
    return min_int(cells)


def candidate_boundary_distance(
    record: TriplexRecord,
    fasim_records: Sequence[TriplexRecord],
) -> int:
    distances: List[int] = []
    for fasim_record in fasim_records:
        if not records_overlap_in_both_axes(record, fasim_record):
            continue
        distances.extend(
            [
                abs(record.genome_interval[0] - fasim_record.genome_interval[0]),
                abs(record.genome_interval[1] - fasim_record.genome_interval[1]),
                abs(record.query_interval[0] - fasim_record.query_interval[0]),
                abs(record.query_interval[1] - fasim_record.query_interval[1]),
            ]
        )
    return min_int(distances)


def candidate_conflict_degrees(records: Sequence[TriplexRecord]) -> Dict[str, int]:
    degrees: Dict[str, int] = {record.raw: 0 for record in records}
    by_family: Dict[Tuple[str, str, str], List[TriplexRecord]] = defaultdict(list)
    for record in records:
        by_family[record.family].append(record)
    for family_records in by_family.values():
        ordered = sorted(family_records, key=lambda record: (record.genome_interval[0], record.genome_interval[1], record.raw))
        for left_index, left in enumerate(ordered):
            for right in ordered[left_index + 1 :]:
                if right.genome_interval[0] > left.genome_interval[1]:
                    break
                if overlaps(left.genome_interval, right.genome_interval):
                    degrees[left.raw] += 1
                    degrees[right.raw] += 1
    return degrees


def dominated_by_higher_score(
    record: TriplexRecord,
    references: Sequence[TriplexRecord],
) -> bool:
    return any(
        reference.raw != record.raw
        and reference.family == record.family
        and reference.score > record.score
        and contains(reference.genome_interval, record.genome_interval)
        and contains(reference.query_interval, record.query_interval)
        for reference in references
    )


def build_extra_candidate_features(
    *,
    candidate_records: Sequence[TriplexRecord],
    sim_raw: Set[str],
    fasim_records: Sequence[TriplexRecord],
    boxes: Sequence[RecoveryBox],
) -> List[ExtraCandidateFeature]:
    local_ranks = candidate_local_ranks(candidate_records, boxes)
    family_ranks = candidate_family_ranks(candidate_records)
    conflict_degrees = candidate_conflict_degrees(candidate_records)
    dominance_references = list(fasim_records) + list(candidate_records)
    features: List[ExtraCandidateFeature] = []
    for record in candidate_records:
        features.append(
            ExtraCandidateFeature(
                raw=record.raw,
                true_sim_record=record.raw in sim_raw,
                score=record.score,
                nt=record.nt,
                genome_length=interval_length(record.genome_interval),
                query_length=interval_length(record.query_interval),
                local_rank=local_ranks.get(record.raw, 0),
                family_rank=family_ranks.get(record.raw, 0),
                dominated_by_higher_score=dominated_by_higher_score(record, dominance_references),
                contained_in_fasim=is_nested_candidate(record, fasim_records),
                overlaps_fasim=is_near_duplicate_candidate(record, fasim_records),
                boundary_distance=candidate_boundary_distance(record, fasim_records),
                conflict_degree=conflict_degrees.get(record.raw, 0),
                box_cells=candidate_box_cells(record, boxes),
                nested_candidate=is_nested_candidate(record, fasim_records),
                internal_peak_candidate=is_internal_peak_candidate(record, fasim_records),
            )
        )
    return features


def evaluate_extra_guard(
    *,
    workload_label: str,
    guard: str,
    selected_candidate_raw: Set[str],
    fasim_raw: Set[str],
    suppressed_fasim_raw: Set[str],
    sim_raw: Set[str],
    sim_only_raw: Set[str],
    oracle: bool = False,
) -> ExtraGuardResult:
    integrated_raw = (fasim_raw - suppressed_fasim_raw) | selected_candidate_raw
    integrated_records = parse_lite_records(sorted(integrated_raw))
    shared_records_vs_sim = integrated_raw & sim_raw
    return ExtraGuardResult(
        workload_label=workload_label,
        guard=guard,
        selected_candidates=len(selected_candidate_raw),
        integrated_records=len(integrated_raw),
        sim_records=len(sim_raw),
        sim_only_recovered=len(sim_only_raw & integrated_raw),
        shared_records_vs_sim=len(shared_records_vs_sim),
        extra_records_vs_sim=len(integrated_raw - sim_raw),
        overlap_conflicts=count_same_family_genomic_overlaps(integrated_records),
        output_mutations=0,
        oracle=oracle,
    )


def build_local_sim_recovery_replacement_extra_taxonomy(
    *,
    workload_label: str,
    sim_records: Sequence[TriplexRecord],
    fasim_records: Sequence[TriplexRecord],
    sim_only: Sequence[GapRecord],
    executor_shadow: ExecutorShadow,
) -> ReplacementExtraTaxonomy:
    fasim_raw = {record.raw for record in fasim_records}
    sim_raw = {record.raw for record in sim_records}
    sim_only_raw = {gap.record.raw for gap in sim_only}
    candidate_raw = set(executor_shadow.candidate_records_raw)
    candidate_records = parse_lite_records(sorted(candidate_raw))
    candidate_by_raw = {record.raw: record for record in candidate_records}
    boxes = executor_shadow.boxes
    fasim_in_boxes, _ = records_by_box(fasim_records, boxes)
    candidate_in_boxes, _ = records_by_box(candidate_records, boxes)

    accepted_raw = {
        raw
        for raw, record in candidate_by_raw.items()
        if raw in candidate_in_boxes and record.score >= 89.0 and record.nt >= 50
    }
    accepted_records = [candidate_by_raw[raw] for raw in sorted(accepted_raw)]
    features = build_extra_candidate_features(
        candidate_records=accepted_records,
        sim_raw=sim_raw,
        fasim_records=fasim_records,
        boxes=boxes,
    )
    true_features = [feature for feature in features if feature.true_sim_record]
    extra_features = [feature for feature in features if not feature.true_sim_record]

    score_nt_threshold = set(accepted_raw)
    local_rank_topk = {feature.raw for feature in features if feature.local_rank and feature.local_rank <= 2}
    family_rank_topk = {feature.raw for feature in features if feature.family_rank and feature.family_rank <= 2}
    dominance_filter = {feature.raw for feature in features if not feature.dominated_by_higher_score}
    containment_boundary_guard = {
        feature.raw
        for feature in features
        if feature.contained_in_fasim or feature.boundary_distance <= 4
    }
    combined_non_oracle = {
        feature.raw
        for feature in features
        if feature.local_rank
        and feature.local_rank <= 2
        and not feature.dominated_by_higher_score
    }
    oracle_sim_match = accepted_raw & sim_raw

    guard_specs = (
        ("score_nt_threshold", score_nt_threshold, False),
        ("local_rank_topk_per_box", local_rank_topk, False),
        ("family_rank_topk", family_rank_topk, False),
        ("dominance_filter", dominance_filter, False),
        ("containment_boundary_guard", containment_boundary_guard, False),
        ("combined_non_oracle", combined_non_oracle, False),
        ("oracle_sim_match", oracle_sim_match, True),
    )
    guards = tuple(
        evaluate_extra_guard(
            workload_label=workload_label,
            guard=guard,
            selected_candidate_raw=selected_raw,
            fasim_raw=fasim_raw,
            suppressed_fasim_raw=fasim_in_boxes,
            sim_raw=sim_raw,
            sim_only_raw=sim_only_raw,
            oracle=oracle,
        )
        for guard, selected_raw, oracle in guard_specs
    )

    return ReplacementExtraTaxonomy(
        workload_label=workload_label,
        true_sim_records=len(true_features),
        extra_records=len(extra_features),
        score_min_true=min_float([feature.score for feature in true_features]),
        score_min_extra=min_float([feature.score for feature in extra_features]),
        nt_min_true=min_int([feature.nt for feature in true_features]),
        nt_min_extra=min_int([feature.nt for feature in extra_features]),
        rank_true_p50=median_value([float(feature.local_rank) for feature in true_features]),
        rank_extra_p50=median_value([float(feature.local_rank) for feature in extra_features]),
        dominated_true=sum(1 for feature in true_features if feature.dominated_by_higher_score),
        dominated_extra=sum(1 for feature in extra_features if feature.dominated_by_higher_score),
        contained_true=sum(1 for feature in true_features if feature.contained_in_fasim),
        contained_extra=sum(1 for feature in extra_features if feature.contained_in_fasim),
        boundary_distance_true_p50=median_value([float(feature.boundary_distance) for feature in true_features]),
        boundary_distance_extra_p50=median_value([float(feature.boundary_distance) for feature in extra_features]),
        overlap_conflicts=count_same_family_genomic_overlaps(accepted_records),
        output_mutations=0,
        guards=guards,
    )


def build_local_sim_recovery_replacement_shadow(
    *,
    workload_label: str,
    sim_records: Sequence[TriplexRecord],
    fasim_records: Sequence[TriplexRecord],
    sim_only: Sequence[GapRecord],
    executor_shadow: ExecutorShadow,
) -> ReplacementShadow:
    fasim_raw = {record.raw for record in fasim_records}
    sim_raw = {record.raw for record in sim_records}
    sim_only_raw = {gap.record.raw for gap in sim_only}
    candidate_raw = set(executor_shadow.candidate_records_raw)
    candidate_records = parse_lite_records(sorted(candidate_raw))
    candidate_by_raw = {record.raw: record for record in candidate_records}
    fasim_by_raw = {record.raw: record for record in fasim_records}
    boxes = executor_shadow.boxes

    filtered_candidate_raw = {
        raw
        for raw, record in candidate_by_raw.items()
        if record.score >= 89.0 and record.nt >= 50
    }

    fasim_in_boxes, fasim_raw_by_box = records_by_box(fasim_records, boxes)
    candidate_in_boxes, candidate_raw_by_box = records_by_box(candidate_records, boxes)
    filtered_candidate_in_boxes = filtered_candidate_raw & candidate_in_boxes

    candidate_families = {record.family for record in candidate_records if record.raw in filtered_candidate_raw}
    family_suppressed_fasim = {
        record.raw
        for record in fasim_records
        if record.family in candidate_families
    }
    family_accepted_candidates = {
        raw
        for raw, record in candidate_by_raw.items()
        if raw in filtered_candidate_raw and record.family in candidate_families
    }

    conservative_suppressed: Set[str] = set()
    conservative_accepted: Set[str] = set()
    for index, box in enumerate(boxes):
        fasim_box_raw = fasim_raw_by_box.get(index, set())
        candidate_box_raw = candidate_raw_by_box.get(index, set()) & filtered_candidate_raw
        if not fasim_box_raw or not candidate_box_raw:
            continue
        fasim_score_max = max(fasim_by_raw[raw].score for raw in fasim_box_raw)
        candidate_score_max = max(candidate_by_raw[raw].score for raw in candidate_box_raw)
        if len(candidate_box_raw) >= len(fasim_box_raw) and candidate_score_max >= fasim_score_max:
            conservative_suppressed.update(fasim_box_raw)
            conservative_accepted.update(candidate_box_raw)

    strategies = (
        evaluate_replacement_strategy(
            workload_label=workload_label,
            strategy="raw_union",
            fasim_raw=fasim_raw,
            candidate_raw=candidate_raw,
            suppressed_fasim_raw=set(),
            accepted_candidate_raw=set(candidate_raw),
            sim_raw=sim_raw,
            sim_only_raw=sim_only_raw,
        ),
        evaluate_replacement_strategy(
            workload_label=workload_label,
            strategy="filtered_union",
            fasim_raw=fasim_raw,
            candidate_raw=candidate_raw,
            suppressed_fasim_raw=set(),
            accepted_candidate_raw=set(filtered_candidate_raw),
            sim_raw=sim_raw,
            sim_only_raw=sim_only_raw,
        ),
        evaluate_replacement_strategy(
            workload_label=workload_label,
            strategy="box_local_replacement",
            fasim_raw=fasim_raw,
            candidate_raw=candidate_raw,
            suppressed_fasim_raw=fasim_in_boxes,
            accepted_candidate_raw=filtered_candidate_in_boxes,
            sim_raw=sim_raw,
            sim_only_raw=sim_only_raw,
        ),
        evaluate_replacement_strategy(
            workload_label=workload_label,
            strategy="family_replacement",
            fasim_raw=fasim_raw,
            candidate_raw=candidate_raw,
            suppressed_fasim_raw=family_suppressed_fasim,
            accepted_candidate_raw=family_accepted_candidates,
            sim_raw=sim_raw,
            sim_only_raw=sim_only_raw,
        ),
        evaluate_replacement_strategy(
            workload_label=workload_label,
            strategy="conservative_replacement",
            fasim_raw=fasim_raw,
            candidate_raw=candidate_raw,
            suppressed_fasim_raw=conservative_suppressed,
            accepted_candidate_raw=conservative_accepted,
            sim_raw=sim_raw,
            sim_only_raw=sim_only_raw,
        ),
        evaluate_replacement_strategy(
            workload_label=workload_label,
            strategy="oracle_box_replacement",
            fasim_raw=fasim_raw,
            candidate_raw=candidate_raw,
            suppressed_fasim_raw=fasim_in_boxes,
            accepted_candidate_raw=candidate_raw & sim_raw,
            sim_raw=sim_raw,
            sim_only_raw=sim_only_raw,
            oracle=True,
        ),
    )

    return ReplacementShadow(
        workload_label=workload_label,
        fasim_records=len(fasim_raw),
        recovered_candidates=len(candidate_raw),
        output_mutations=0,
        strategies=strategies,
    )


def build_local_sim_recovery_filter_shadow(
    *,
    workload_label: str,
    sim_records: Sequence[TriplexRecord],
    fasim_records: Sequence[TriplexRecord],
    sim_only: Sequence[GapRecord],
    executor_shadow: ExecutorShadow,
) -> FilterShadow:
    fasim_raw = {record.raw for record in fasim_records}
    sim_raw = {record.raw for record in sim_records}
    sim_only_raw = {gap.record.raw for gap in sim_only}
    candidate_raw = set(executor_shadow.candidate_records_raw)
    candidate_records = parse_lite_records(sorted(candidate_raw))
    fasim_records_by_raw = {record.raw: record for record in fasim_records}
    candidate_by_raw = {record.raw: record for record in candidate_records}
    reference_records = list(fasim_records) + candidate_records
    overlap_conflicts_before = count_same_family_genomic_overlaps(parse_lite_records(sorted(fasim_raw | candidate_raw)))

    fasim_duplicates = len(candidate_raw & fasim_raw)
    sim_only_matches = len(candidate_raw & sim_only_raw)
    extra_vs_sim = len(candidate_raw - sim_raw)
    near_duplicates = sum(
        1
        for record in candidate_records
        if record.raw not in fasim_raw and is_near_duplicate_candidate(record, fasim_records)
    )
    nested_candidates = sum(1 for record in candidate_records if is_nested_candidate(record, fasim_records))
    internal_peak_candidates = sum(1 for record in candidate_records if is_internal_peak_candidate(record, fasim_records))
    classified_raw: Set[str] = set()
    classified_raw.update(candidate_raw & fasim_raw)
    classified_raw.update(candidate_raw & sim_only_raw)
    classified_raw.update(raw for raw, record in candidate_by_raw.items() if is_near_duplicate_candidate(record, fasim_records))
    classified_raw.update(candidate_raw - sim_raw)
    unknown_candidates = len(candidate_raw - classified_raw)

    exact_dedup_only = set(candidate_raw)
    score_interval_dominance = {
        raw
        for raw, record in candidate_by_raw.items()
        if not is_interval_dominated(record, reference_records)
    }
    same_family_overlap_suppression = {
        raw
        for raw, record in candidate_by_raw.items()
        if not any(records_overlap_in_both_axes(record, fasim_record) for fasim_record in fasim_records_by_raw.values())
    }
    oracle_sim_match = candidate_raw & sim_raw
    non_oracle_score_nt = {
        raw
        for raw, record in candidate_by_raw.items()
        if record.score >= 89.0 and record.nt >= 50
    }

    strategies = (
        evaluate_filter_strategy(
            workload_label=workload_label,
            strategy="exact_dedup_only",
            selected_candidate_raw=exact_dedup_only,
            candidate_raw=candidate_raw,
            fasim_raw=fasim_raw,
            sim_raw=sim_raw,
            sim_only_raw=sim_only_raw,
            overlap_conflicts_before=overlap_conflicts_before,
            oracle=False,
        ),
        evaluate_filter_strategy(
            workload_label=workload_label,
            strategy="score_interval_dominance",
            selected_candidate_raw=score_interval_dominance,
            candidate_raw=candidate_raw,
            fasim_raw=fasim_raw,
            sim_raw=sim_raw,
            sim_only_raw=sim_only_raw,
            overlap_conflicts_before=overlap_conflicts_before,
            oracle=False,
        ),
        evaluate_filter_strategy(
            workload_label=workload_label,
            strategy="same_family_overlap_suppression",
            selected_candidate_raw=same_family_overlap_suppression,
            candidate_raw=candidate_raw,
            fasim_raw=fasim_raw,
            sim_raw=sim_raw,
            sim_only_raw=sim_only_raw,
            overlap_conflicts_before=overlap_conflicts_before,
            oracle=False,
        ),
        evaluate_filter_strategy(
            workload_label=workload_label,
            strategy="oracle_sim_match",
            selected_candidate_raw=oracle_sim_match,
            candidate_raw=candidate_raw,
            fasim_raw=fasim_raw,
            sim_raw=sim_raw,
            sim_only_raw=sim_only_raw,
            overlap_conflicts_before=overlap_conflicts_before,
            oracle=True,
        ),
        evaluate_filter_strategy(
            workload_label=workload_label,
            strategy="non_oracle_score_nt",
            selected_candidate_raw=non_oracle_score_nt,
            candidate_raw=candidate_raw,
            fasim_raw=fasim_raw,
            sim_raw=sim_raw,
            sim_only_raw=sim_only_raw,
            overlap_conflicts_before=overlap_conflicts_before,
            oracle=False,
        ),
    )

    return FilterShadow(
        workload_label=workload_label,
        recovered_candidates=len(candidate_raw),
        fasim_duplicates=fasim_duplicates,
        near_duplicates=near_duplicates,
        sim_only_matches=sim_only_matches,
        extra_vs_sim=extra_vs_sim,
        overlap_conflicts_before=overlap_conflicts_before,
        nested_candidates=nested_candidates,
        internal_peak_candidates=internal_peak_candidates,
        unknown_candidates=unknown_candidates,
        output_mutations=0,
        strategies=strategies,
    )


def build_local_sim_recovery_integration_shadow(
    *,
    workload_label: str,
    sim_records: Sequence[TriplexRecord],
    fasim_records: Sequence[TriplexRecord],
    sim_only: Sequence[GapRecord],
    executor_shadow: ExecutorShadow,
) -> IntegrationShadow:
    fasim_raw = {record.raw for record in fasim_records}
    sim_raw = {record.raw for record in sim_records}
    candidate_raw = set(executor_shadow.candidate_records_raw)
    integrated_raw = fasim_raw | candidate_raw
    sim_only_raw = {gap.record.raw for gap in sim_only}
    shared_vs_sim = integrated_raw & sim_raw

    recovered_by_category: Counter = Counter()
    sim_only_by_category: Counter = Counter(gap.primary for gap in sim_only)
    for gap in sim_only:
        if gap.record.raw in integrated_raw:
            recovered_by_category.update([gap.primary])

    integrated_records = parse_lite_records(sorted(integrated_raw))
    return IntegrationShadow(
        workload_label=workload_label,
        fasim_records=len(fasim_raw),
        recovered_candidates=len(candidate_raw),
        unique_recovered_records=len(candidate_raw - fasim_raw),
        duplicate_recovered_records=len(candidate_raw & fasim_raw),
        integrated_records=len(integrated_raw),
        sim_records=len(sim_raw),
        sim_only_records=len(sim_only_raw),
        sim_only_recovered=len(sim_only_raw & integrated_raw),
        shared_records_vs_sim=len(shared_vs_sim),
        extra_records_vs_sim=len(integrated_raw - sim_raw),
        nonoverlap_conflicts=count_same_family_genomic_overlaps(integrated_records),
        output_mutations=0,
        recovered_by_category=recovered_by_category,
        sim_only_by_category=sim_only_by_category,
    )


def analyze_gap(
    *,
    bin_path: Path,
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
    executor_shadow_enabled: bool,
    integration_shadow_enabled: bool,
    filter_shadow_enabled: bool,
    replacement_shadow_enabled: bool,
    replacement_extra_taxonomy_enabled: bool,
    executor_shadow_work_dir: Path,
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

    detector = (
        build_fasim_visible_risk_detector(
            spec=spec,
            sim_records=sim.records,
            fasim_records=fasim.records,
            sim_only=sim_only,
            merge_gap_bp=merge_gap_bp,
            margin_bp=risk_detector_margin_bp,
        )
        if (
            risk_detector_enabled
            or executor_shadow_enabled
            or integration_shadow_enabled
            or filter_shadow_enabled
            or replacement_shadow_enabled
            or replacement_extra_taxonomy_enabled
        )
        else None
    )

    executor_shadow = (
        build_bounded_local_sim_executor_shadow(
            spec=spec,
            bin_path=bin_path,
            boxes=detector.boxes if detector is not None else [],
            sim_only=sim_only,
            work_dir=executor_shadow_work_dir,
        )
        if (
            executor_shadow_enabled
            or integration_shadow_enabled
            or filter_shadow_enabled
            or replacement_shadow_enabled
            or replacement_extra_taxonomy_enabled
        )
        else None
    )

    integration_shadow = (
        build_local_sim_recovery_integration_shadow(
            workload_label=spec.label,
            sim_records=sim.records,
            fasim_records=fasim.records,
            sim_only=sim_only,
            executor_shadow=executor_shadow,
        )
        if integration_shadow_enabled and executor_shadow is not None
        else None
    )

    filter_shadow = (
        build_local_sim_recovery_filter_shadow(
            workload_label=spec.label,
            sim_records=sim.records,
            fasim_records=fasim.records,
            sim_only=sim_only,
            executor_shadow=executor_shadow,
        )
        if filter_shadow_enabled and executor_shadow is not None
        else None
    )

    replacement_shadow = (
        build_local_sim_recovery_replacement_shadow(
            workload_label=spec.label,
            sim_records=sim.records,
            fasim_records=fasim.records,
            sim_only=sim_only,
            executor_shadow=executor_shadow,
        )
        if replacement_shadow_enabled and executor_shadow is not None
        else None
    )

    replacement_extra_taxonomy = (
        build_local_sim_recovery_replacement_extra_taxonomy(
            workload_label=spec.label,
            sim_records=sim.records,
            fasim_records=fasim.records,
            sim_only=sim_only,
            executor_shadow=executor_shadow,
        )
        if replacement_extra_taxonomy_enabled and executor_shadow is not None
        else None
    )

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
        risk_detector=(detector if risk_detector_enabled else None),
        executor_shadow=(executor_shadow if executor_shadow_enabled else None),
        integration_shadow=integration_shadow,
        filter_shadow=filter_shadow,
        replacement_shadow=replacement_shadow,
        replacement_extra_taxonomy=replacement_extra_taxonomy,
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


def render_executor_shadow_report(
    *,
    gaps: Sequence[WorkloadGap],
    output_path: Path,
    profile_set: str,
) -> str:
    shadows = [gap.executor_shadow for gap in gaps if gap.executor_shadow is not None]
    if len(shadows) != len(gaps):
        raise RuntimeError("executor shadow report requested without executor shadow data")

    lines: List[str] = []
    lines.append("# Fasim Local SIM Recovery Executor Shadow")
    lines.append("")
    lines.append("Base branch:")
    lines.append("")
    lines.append("```text")
    lines.append("fasim-sim-recovery-risk-detector")
    lines.append("```")
    lines.append("")
    lines.append(
        "This report runs a bounded local SIM executor inside boxes selected by "
        "the Fasim-visible risk detector. Box selection uses Fasim output "
        "records only. The executor result is diagnostic-only and is compared "
        "against SIM-only records after execution."
    )
    lines.append("")
    lines.append(
        "The shadow does not add recovered records to Fasim output and does not "
        "change scoring, threshold, non-overlap, output, GPU, or filter behavior. "
        "The representative fixtures remain deterministic synthetic fixtures, "
        "not a production accuracy benchmark."
    )
    lines.append("")
    append_table(
        lines,
        ["Setting", "Value"],
        [
            ["profile_set", profile_set],
            ["box_source", "Fasim-visible risk detector boxes"],
            ["executor", "per-box legacy -F SIM on cropped DNA/RNA"],
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
    total_recovered = 0
    total_unrecovered = 0
    total_candidates = 0
    total_output_mutations = 0
    total_executor_failures = 0
    total_unsupported_boxes = 0
    aggregate_sim_only_by_category: Counter = Counter()
    aggregate_recovered_by_category: Counter = Counter()

    for shadow in shadows:
        total_boxes += len(shadow.boxes)
        total_cells += shadow.cells
        total_full_search_cells += shadow.full_search_cells
        total_seconds += shadow.seconds
        total_sim_only += shadow.sim_only_records
        total_recovered += shadow.recovered_records
        total_unrecovered += shadow.unrecovered_records
        total_candidates += shadow.candidate_records
        total_output_mutations += shadow.output_mutations
        total_executor_failures += shadow.executor_failures
        total_unsupported_boxes += shadow.unsupported_boxes
        aggregate_sim_only_by_category.update(shadow.sim_only_by_category)
        aggregate_recovered_by_category.update(shadow.recovered_by_category)
        rows.append(
            [
                shadow.workload_label,
                str(len(shadow.boxes)),
                str(shadow.cells),
                str(shadow.full_search_cells),
                fmt_pct(shadow.cell_fraction),
                f"{shadow.seconds:.6f}",
                str(shadow.sim_only_records),
                str(shadow.recovered_records),
                str(shadow.unrecovered_records),
                fmt_pct(shadow.recall),
                str(shadow.candidate_records),
                str(shadow.executor_failures),
                str(shadow.unsupported_boxes),
                str(shadow.output_mutations),
            ]
        )

    lines.append("## Workload Summary")
    lines.append("")
    append_table(
        lines,
        [
            "Workload",
            "Boxes",
            "Cells",
            "Full-search cells",
            "Cell fraction",
            "Executor seconds",
            "SIM-only",
            "Recovered",
            "Unrecovered",
            "Recall",
            "Candidate records",
            "Executor failures",
            "Unsupported boxes",
            "Output mutations",
        ],
        rows,
    )
    lines.append("")

    lines.append("## Category Summary")
    lines.append("")
    append_table(
        lines,
        ["Category", "SIM-only", "Recovered", "Unrecovered", "Recall"],
        [
            [
                category,
                str(aggregate_sim_only_by_category.get(category, 0)),
                str(aggregate_recovered_by_category.get(category, 0)),
                str(
                    aggregate_sim_only_by_category.get(category, 0)
                    - aggregate_recovered_by_category.get(category, 0)
                ),
                fmt_pct(
                    pct(
                        aggregate_recovered_by_category.get(category, 0),
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
            ["fasim_sim_recovery_executor_shadow_enabled", "1"],
            ["fasim_sim_recovery_executor_shadow_boxes", str(total_boxes)],
            ["fasim_sim_recovery_executor_shadow_cells", str(total_cells)],
            ["fasim_sim_recovery_executor_shadow_full_search_cells", str(total_full_search_cells)],
            ["fasim_sim_recovery_executor_shadow_cell_fraction", fmt_pct(pct(total_cells, total_full_search_cells))],
            ["fasim_sim_recovery_executor_shadow_seconds", f"{total_seconds:.6f}"],
            ["fasim_sim_recovery_executor_shadow_sim_only_records", str(total_sim_only)],
            ["fasim_sim_recovery_executor_shadow_recovered_records", str(total_recovered)],
            ["fasim_sim_recovery_executor_shadow_unrecovered_records", str(total_unrecovered)],
            ["fasim_sim_recovery_executor_shadow_recall", fmt_pct(pct(total_recovered, total_sim_only))],
            ["fasim_sim_recovery_executor_shadow_candidate_records", str(total_candidates)],
            ["fasim_sim_recovery_executor_shadow_output_mutations", str(total_output_mutations)],
            ["fasim_sim_recovery_executor_shadow_executor_failures", str(total_executor_failures)],
            ["fasim_sim_recovery_executor_shadow_unsupported_boxes", str(total_unsupported_boxes)],
        ],
    )
    lines.append("")

    lines.append("## Decision")
    lines.append("")
    recall = pct(total_recovered, total_sim_only)
    cell_fraction = pct(total_cells, total_full_search_cells)
    if total_output_mutations != 0:
        decision = "Stop: executor shadow observed output mutations, which violates diagnostic-only scope."
    elif total_executor_failures or total_unsupported_boxes:
        decision = "Executor shadow has failures or unsupported boxes; repair executor plumbing before real recovery."
    elif recall >= 90.0 and cell_fraction <= 5.0:
        decision = (
            "The bounded executor recovers most SIM-only records within a small "
            "cell fraction. A real local SIM recovery opt-in with validation is a "
            "plausible next PR."
        )
    elif recall >= 60.0 and cell_fraction <= 5.0:
        decision = "The executor has useful recall but needs stronger local recovery before a real opt-in."
    elif cell_fraction > 5.0:
        decision = "Executor boxes are too broad; tune risk detector boxes before real recovery."
    else:
        decision = "Executor recall is too low; improve bounded local SIM recovery before real recovery."
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
    lines.append("SIM-only coordinates used for selection: no")
    lines.append("```")
    lines.append("")

    for shadow in shadows:
        prefix = f"benchmark.fasim_sim_recovery_executor_shadow.{shadow.workload_label}"
        print(f"{prefix}.enabled=1")
        print(f"{prefix}.boxes={len(shadow.boxes)}")
        print(f"{prefix}.cells={shadow.cells}")
        print(f"{prefix}.full_search_cells={shadow.full_search_cells}")
        print(f"{prefix}.cell_fraction={shadow.cell_fraction:.6f}")
        print(f"{prefix}.seconds={shadow.seconds:.6f}")
        print(f"{prefix}.sim_only_records={shadow.sim_only_records}")
        print(f"{prefix}.recovered_records={shadow.recovered_records}")
        print(f"{prefix}.unrecovered_records={shadow.unrecovered_records}")
        print(f"{prefix}.recall={shadow.recall:.6f}")
        print(f"{prefix}.candidate_records={shadow.candidate_records}")
        print(f"{prefix}.output_mutations={shadow.output_mutations}")
        print(f"{prefix}.executor_failures={shadow.executor_failures}")
        print(f"{prefix}.unsupported_boxes={shadow.unsupported_boxes}")
        for category in GAP_CATEGORIES:
            print(f"{prefix}.{category}_recovered={shadow.recovered_by_category.get(category, 0)}")

    print("benchmark.fasim_sim_recovery_executor_shadow.total.enabled=1")
    print(f"benchmark.fasim_sim_recovery_executor_shadow.total.boxes={total_boxes}")
    print(f"benchmark.fasim_sim_recovery_executor_shadow.total.cells={total_cells}")
    print(f"benchmark.fasim_sim_recovery_executor_shadow.total.full_search_cells={total_full_search_cells}")
    print(f"benchmark.fasim_sim_recovery_executor_shadow.total.cell_fraction={pct(total_cells, total_full_search_cells):.6f}")
    print(f"benchmark.fasim_sim_recovery_executor_shadow.total.seconds={total_seconds:.6f}")
    print(f"benchmark.fasim_sim_recovery_executor_shadow.total.sim_only_records={total_sim_only}")
    print(f"benchmark.fasim_sim_recovery_executor_shadow.total.recovered_records={total_recovered}")
    print(f"benchmark.fasim_sim_recovery_executor_shadow.total.unrecovered_records={total_unrecovered}")
    print(f"benchmark.fasim_sim_recovery_executor_shadow.total.recall={pct(total_recovered, total_sim_only):.6f}")
    print(f"benchmark.fasim_sim_recovery_executor_shadow.total.candidate_records={total_candidates}")
    print(f"benchmark.fasim_sim_recovery_executor_shadow.total.output_mutations={total_output_mutations}")
    print(f"benchmark.fasim_sim_recovery_executor_shadow.total.executor_failures={total_executor_failures}")
    print(f"benchmark.fasim_sim_recovery_executor_shadow.total.unsupported_boxes={total_unsupported_boxes}")
    for category in GAP_CATEGORIES:
        print(
            f"benchmark.fasim_sim_recovery_executor_shadow.total.{category}_recovered="
            f"{aggregate_recovered_by_category.get(category, 0)}"
        )
    print(
        "benchmark.fasim_sim_recovery_executor_shadow.total.internal_peak_recovered="
        f"{aggregate_recovered_by_category.get('long_hit_internal_peak', 0)}"
    )

    report = "\n".join(lines)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report + "\n", encoding="utf-8")
    return report


def render_integration_shadow_report(
    *,
    gaps: Sequence[WorkloadGap],
    output_path: Path,
    profile_set: str,
) -> str:
    shadows = [gap.integration_shadow for gap in gaps if gap.integration_shadow is not None]
    if len(shadows) != len(gaps):
        raise RuntimeError("integration shadow report requested without integration shadow data")

    lines: List[str] = []
    lines.append("# Fasim Local SIM Recovery Integration Shadow")
    lines.append("")
    lines.append("Base branch:")
    lines.append("")
    lines.append("```text")
    lines.append("fasim-local-sim-recovery-executor-shadow")
    lines.append("```")
    lines.append("")
    lines.append(
        "This report is diagnostic-only. It runs the Fasim-visible risk detector "
        "and bounded local SIM executor, then builds a side candidate set from "
        "Fasim output records plus recovered local SIM records. The side set is "
        "evaluated with an exact raw-record de-duplication comparator; it is not "
        "written as Fasim output and does not replace final non-overlap authority."
    )
    lines.append("")
    lines.append(
        "The representative fixtures are deterministic synthetic fixtures. This "
        "shadow measures integration feasibility only; it is not a production "
        "accuracy claim and it is not a real `FASIM_SIM_RECOVERY=1` mode."
    )
    lines.append("")
    append_table(
        lines,
        ["Setting", "Value"],
        [
            ["profile_set", profile_set],
            ["candidate_set", "Fasim raw records union bounded local SIM raw records"],
            ["dedup_comparator", "exact canonical lite record identity"],
            ["nonoverlap_conflicts", "diagnostic same-family genomic overlap pairs only"],
            ["output_mutations_expected", "0"],
        ],
    )
    lines.append("")

    rows: List[List[str]] = []
    total_fasim = 0
    total_candidates = 0
    total_unique_recovered = 0
    total_duplicate_recovered = 0
    total_integrated = 0
    total_sim = 0
    total_sim_only = 0
    total_sim_only_recovered = 0
    total_shared_vs_sim = 0
    total_extra_vs_sim = 0
    total_nonoverlap_conflicts = 0
    total_output_mutations = 0
    aggregate_sim_only_by_category: Counter = Counter()
    aggregate_recovered_by_category: Counter = Counter()

    for shadow in shadows:
        total_fasim += shadow.fasim_records
        total_candidates += shadow.recovered_candidates
        total_unique_recovered += shadow.unique_recovered_records
        total_duplicate_recovered += shadow.duplicate_recovered_records
        total_integrated += shadow.integrated_records
        total_sim += shadow.sim_records
        total_sim_only += shadow.sim_only_records
        total_sim_only_recovered += shadow.sim_only_recovered
        total_shared_vs_sim += shadow.shared_records_vs_sim
        total_extra_vs_sim += shadow.extra_records_vs_sim
        total_nonoverlap_conflicts += shadow.nonoverlap_conflicts
        total_output_mutations += shadow.output_mutations
        aggregate_sim_only_by_category.update(shadow.sim_only_by_category)
        aggregate_recovered_by_category.update(shadow.recovered_by_category)
        rows.append(
            [
                shadow.workload_label,
                str(shadow.fasim_records),
                str(shadow.recovered_candidates),
                str(shadow.unique_recovered_records),
                str(shadow.duplicate_recovered_records),
                str(shadow.integrated_records),
                str(shadow.sim_records),
                str(shadow.sim_only_records),
                str(shadow.sim_only_recovered),
                fmt_pct(shadow.recall_vs_sim),
                fmt_pct(shadow.precision_vs_sim),
                str(shadow.extra_records_vs_sim),
                str(shadow.nonoverlap_conflicts),
                str(shadow.output_mutations),
            ]
        )

    lines.append("## Workload Summary")
    lines.append("")
    append_table(
        lines,
        [
            "Workload",
            "Fasim records",
            "Recovered candidates",
            "Unique recovered",
            "Duplicate recovered",
            "Integrated records",
            "SIM records",
            "SIM-only",
            "SIM-only recovered",
            "Recall vs SIM",
            "Precision vs SIM",
            "Extra vs SIM",
            "Overlap conflicts",
            "Output mutations",
        ],
        rows,
    )
    lines.append("")

    lines.append("## Category Summary")
    lines.append("")
    append_table(
        lines,
        ["Category", "SIM-only", "Recovered after side integration", "Unrecovered", "Recall"],
        [
            [
                category,
                str(aggregate_sim_only_by_category.get(category, 0)),
                str(aggregate_recovered_by_category.get(category, 0)),
                str(
                    aggregate_sim_only_by_category.get(category, 0)
                    - aggregate_recovered_by_category.get(category, 0)
                ),
                fmt_pct(
                    pct(
                        aggregate_recovered_by_category.get(category, 0),
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
            ["fasim_sim_recovery_integration_shadow_enabled", "1"],
            ["fasim_sim_recovery_integration_shadow_fasim_records", str(total_fasim)],
            ["fasim_sim_recovery_integration_shadow_recovered_candidates", str(total_candidates)],
            ["fasim_sim_recovery_integration_shadow_unique_recovered_records", str(total_unique_recovered)],
            ["fasim_sim_recovery_integration_shadow_duplicate_recovered_records", str(total_duplicate_recovered)],
            ["fasim_sim_recovery_integration_shadow_integrated_records", str(total_integrated)],
            ["fasim_sim_recovery_integration_shadow_sim_records", str(total_sim)],
            ["fasim_sim_recovery_integration_shadow_sim_only_records", str(total_sim_only)],
            ["fasim_sim_recovery_integration_shadow_sim_only_recovered", str(total_sim_only_recovered)],
            ["fasim_sim_recovery_integration_shadow_recall_vs_sim", fmt_pct(pct(total_shared_vs_sim, total_sim))],
            ["fasim_sim_recovery_integration_shadow_precision_vs_sim", fmt_pct(pct(total_shared_vs_sim, total_integrated))],
            ["fasim_sim_recovery_integration_shadow_extra_records_vs_sim", str(total_extra_vs_sim)],
            ["fasim_sim_recovery_integration_shadow_nonoverlap_conflicts", str(total_nonoverlap_conflicts)],
            ["fasim_sim_recovery_integration_shadow_output_mutations", str(total_output_mutations)],
        ],
    )
    lines.append("")

    lines.append("## Decision")
    lines.append("")
    recall = pct(total_shared_vs_sim, total_sim)
    precision = pct(total_shared_vs_sim, total_integrated)
    if total_output_mutations != 0:
        decision = "Stop: integration shadow observed output mutations, which violates diagnostic-only scope."
    elif recall >= 90.0 and precision >= 50.0:
        decision = (
            "The side integration recovers most SIM records with a bounded extra "
            "candidate set. A real `FASIM_SIM_RECOVERY=1` SIM-close opt-in design "
            "is a plausible next PR."
        )
    elif recall >= 90.0:
        decision = (
            "The side integration recovers most SIM records, but extra candidates "
            "are high. Refine candidate filtering, de-duplication, or documented "
            "merge semantics before a real opt-in."
        )
    else:
        decision = (
            "Recovery candidates do not survive side integration with enough SIM "
            "recall. Improve executor output or integration semantics before a "
            "real opt-in."
        )
    lines.append(decision)
    lines.append("")
    lines.append("Forbidden-scope check:")
    lines.append("")
    lines.append("```text")
    lines.append("Fasim output change: no")
    lines.append("Recovered records added to output: no")
    lines.append("Real FASIM_SIM_RECOVERY mode: no")
    lines.append("Scoring/threshold/non-overlap behavior change: no")
    lines.append("GPU/filter behavior change: no")
    lines.append("Production accuracy claim: no")
    lines.append("```")
    lines.append("")

    for shadow in shadows:
        prefix = f"benchmark.fasim_sim_recovery_integration_shadow.{shadow.workload_label}"
        print(f"{prefix}.enabled=1")
        print(f"{prefix}.fasim_records={shadow.fasim_records}")
        print(f"{prefix}.recovered_candidates={shadow.recovered_candidates}")
        print(f"{prefix}.unique_recovered_records={shadow.unique_recovered_records}")
        print(f"{prefix}.duplicate_recovered_records={shadow.duplicate_recovered_records}")
        print(f"{prefix}.integrated_records={shadow.integrated_records}")
        print(f"{prefix}.sim_records={shadow.sim_records}")
        print(f"{prefix}.sim_only_records={shadow.sim_only_records}")
        print(f"{prefix}.sim_only_recovered={shadow.sim_only_recovered}")
        print(f"{prefix}.recall_vs_sim={shadow.recall_vs_sim:.6f}")
        print(f"{prefix}.precision_vs_sim={shadow.precision_vs_sim:.6f}")
        print(f"{prefix}.extra_records_vs_sim={shadow.extra_records_vs_sim}")
        print(f"{prefix}.nonoverlap_conflicts={shadow.nonoverlap_conflicts}")
        print(f"{prefix}.output_mutations={shadow.output_mutations}")

    print("benchmark.fasim_sim_recovery_integration_shadow.total.enabled=1")
    print(f"benchmark.fasim_sim_recovery_integration_shadow.total.fasim_records={total_fasim}")
    print(f"benchmark.fasim_sim_recovery_integration_shadow.total.recovered_candidates={total_candidates}")
    print(f"benchmark.fasim_sim_recovery_integration_shadow.total.unique_recovered_records={total_unique_recovered}")
    print(f"benchmark.fasim_sim_recovery_integration_shadow.total.duplicate_recovered_records={total_duplicate_recovered}")
    print(f"benchmark.fasim_sim_recovery_integration_shadow.total.integrated_records={total_integrated}")
    print(f"benchmark.fasim_sim_recovery_integration_shadow.total.sim_records={total_sim}")
    print(f"benchmark.fasim_sim_recovery_integration_shadow.total.sim_only_records={total_sim_only}")
    print(f"benchmark.fasim_sim_recovery_integration_shadow.total.sim_only_recovered={total_sim_only_recovered}")
    print(f"benchmark.fasim_sim_recovery_integration_shadow.total.recall_vs_sim={pct(total_shared_vs_sim, total_sim):.6f}")
    print(
        "benchmark.fasim_sim_recovery_integration_shadow.total.precision_vs_sim="
        f"{pct(total_shared_vs_sim, total_integrated):.6f}"
    )
    print(f"benchmark.fasim_sim_recovery_integration_shadow.total.extra_records_vs_sim={total_extra_vs_sim}")
    print(f"benchmark.fasim_sim_recovery_integration_shadow.total.nonoverlap_conflicts={total_nonoverlap_conflicts}")
    print(f"benchmark.fasim_sim_recovery_integration_shadow.total.output_mutations={total_output_mutations}")

    report = "\n".join(lines)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report + "\n", encoding="utf-8")
    return report


def render_filter_shadow_report(
    *,
    gaps: Sequence[WorkloadGap],
    output_path: Path,
    profile_set: str,
) -> str:
    shadows = [gap.filter_shadow for gap in gaps if gap.filter_shadow is not None]
    if len(shadows) != len(gaps):
        raise RuntimeError("filter shadow report requested without filter shadow data")

    lines: List[str] = []
    lines.append("# Fasim Local SIM Recovery Filter Shadow")
    lines.append("")
    lines.append("Base branch:")
    lines.append("")
    lines.append("```text")
    lines.append("fasim-local-sim-recovery-integration-shadow")
    lines.append("```")
    lines.append("")
    lines.append(
        "This report is diagnostic-only. It classifies bounded local SIM "
        "recovery candidates and evaluates side filtering strategies against "
        "the Fasim output plus recovered-candidate set. It does not add a real "
        "`FASIM_SIM_RECOVERY=1` mode and does not mutate Fasim output."
    )
    lines.append("")
    lines.append(
        "The `oracle_sim_match` strategy uses legacy SIM membership after "
        "candidate generation and is included only as an upper-bound analysis. "
        "It is forbidden as production selection input."
    )
    lines.append("")
    append_table(
        lines,
        ["Setting", "Value"],
        [
            ["profile_set", profile_set],
            ["input_candidates", "bounded local SIM executor raw records"],
            ["candidate_set", "Fasim raw records union filtered local SIM raw records"],
            ["non_oracle_heuristic", "candidate score >= 89 and Nt >= 50"],
            ["output_mutations_expected", "0"],
        ],
    )
    lines.append("")

    total_recovered_candidates = 0
    total_fasim_duplicates = 0
    total_near_duplicates = 0
    total_sim_only_matches = 0
    total_extra_vs_sim = 0
    total_overlap_conflicts_before = 0
    total_nested_candidates = 0
    total_internal_peak_candidates = 0
    total_unknown_candidates = 0
    total_output_mutations = 0
    class_rows: List[List[str]] = []
    strategy_totals: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    strategy_oracle: Dict[str, bool] = {}

    for shadow in shadows:
        total_recovered_candidates += shadow.recovered_candidates
        total_fasim_duplicates += shadow.fasim_duplicates
        total_near_duplicates += shadow.near_duplicates
        total_sim_only_matches += shadow.sim_only_matches
        total_extra_vs_sim += shadow.extra_vs_sim
        total_overlap_conflicts_before += shadow.overlap_conflicts_before
        total_nested_candidates += shadow.nested_candidates
        total_internal_peak_candidates += shadow.internal_peak_candidates
        total_unknown_candidates += shadow.unknown_candidates
        total_output_mutations += shadow.output_mutations
        class_rows.append(
            [
                shadow.workload_label,
                str(shadow.recovered_candidates),
                str(shadow.fasim_duplicates),
                str(shadow.near_duplicates),
                str(shadow.sim_only_matches),
                str(shadow.extra_vs_sim),
                str(shadow.nested_candidates),
                str(shadow.internal_peak_candidates),
                str(shadow.overlap_conflicts_before),
                str(shadow.output_mutations),
            ]
        )
        for result in shadow.strategies:
            totals = strategy_totals[result.strategy]
            strategy_oracle[result.strategy] = result.oracle
            totals["recovered_candidates"] += result.recovered_candidates
            totals["filtered_candidates"] += result.filtered_candidates
            totals["integrated_records"] += result.integrated_records
            totals["sim_only_recovered"] += result.sim_only_recovered
            totals["shared_records_vs_sim"] += result.shared_records_vs_sim
            totals["sim_records"] += result.sim_records
            totals["extra_records_vs_sim"] += result.extra_records_vs_sim
            totals["overlap_conflicts_before"] += result.overlap_conflicts_before
            totals["overlap_conflicts_after"] += result.overlap_conflicts_after
            totals["output_mutations"] += result.output_mutations

    lines.append("## Candidate Class Summary")
    lines.append("")
    append_table(
        lines,
        [
            "Workload",
            "Recovered candidates",
            "Fasim duplicates",
            "Near duplicates",
            "SIM-only matches",
            "Extra vs SIM",
            "Nested candidates",
            "Internal peak candidates",
            "Overlap conflicts before",
            "Output mutations",
        ],
        class_rows,
    )
    lines.append("")
    lines.append(
        "Candidate classes are diagnostic and not mutually exclusive. `Near "
        "duplicate` means same-family overlap in both genomic and RNA axes with "
        "a Fasim output record."
    )
    lines.append("")

    strategy_rows: List[List[str]] = []
    strategy_order = [
        "exact_dedup_only",
        "score_interval_dominance",
        "same_family_overlap_suppression",
        "oracle_sim_match",
        "non_oracle_score_nt",
    ]
    for strategy in strategy_order:
        totals = strategy_totals[strategy]
        strategy_rows.append(
            [
                strategy,
                "yes" if strategy_oracle.get(strategy, False) else "no",
                str(totals.get("recovered_candidates", 0)),
                str(totals.get("filtered_candidates", 0)),
                str(totals.get("integrated_records", 0)),
                str(totals.get("sim_only_recovered", 0)),
                fmt_pct(pct(totals.get("shared_records_vs_sim", 0), totals.get("sim_records", 0))),
                fmt_pct(pct(totals.get("shared_records_vs_sim", 0), totals.get("integrated_records", 0))),
                str(totals.get("extra_records_vs_sim", 0)),
                str(totals.get("overlap_conflicts_after", 0)),
                str(totals.get("output_mutations", 0)),
            ]
        )

    lines.append("## Strategy Summary")
    lines.append("")
    append_table(
        lines,
        [
            "Strategy",
            "Oracle",
            "Recovered candidates",
            "Filtered candidates",
            "Integrated records",
            "SIM-only recovered",
            "Recall vs SIM",
            "Precision vs SIM",
            "Extra vs SIM",
            "Overlap conflicts",
            "Output mutations",
        ],
        strategy_rows,
    )
    lines.append("")

    selected_strategy = "non_oracle_score_nt"
    selected = strategy_totals[selected_strategy]
    lines.append("## Aggregate")
    lines.append("")
    append_table(
        lines,
        ["Metric", "Value"],
        [
            ["fasim_sim_recovery_filter_shadow_enabled", "1"],
            ["fasim_sim_recovery_filter_shadow_recovered_candidates", str(total_recovered_candidates)],
            ["fasim_sim_recovery_filter_shadow_fasim_duplicates", str(total_fasim_duplicates)],
            ["fasim_sim_recovery_filter_shadow_near_duplicates", str(total_near_duplicates)],
            ["fasim_sim_recovery_filter_shadow_sim_only_matches", str(total_sim_only_matches)],
            ["fasim_sim_recovery_filter_shadow_extra_vs_sim", str(total_extra_vs_sim)],
            ["fasim_sim_recovery_filter_shadow_overlap_conflicts_before", str(total_overlap_conflicts_before)],
            ["fasim_sim_recovery_filter_shadow_overlap_conflicts_after", str(selected.get("overlap_conflicts_after", 0))],
            ["fasim_sim_recovery_filter_shadow_filtered_candidates", str(selected.get("filtered_candidates", 0))],
            ["fasim_sim_recovery_filter_shadow_integrated_records", str(selected.get("integrated_records", 0))],
            ["fasim_sim_recovery_filter_shadow_recall_vs_sim", fmt_pct(pct(selected.get("shared_records_vs_sim", 0), selected.get("sim_records", 0)))],
            ["fasim_sim_recovery_filter_shadow_precision_vs_sim", fmt_pct(pct(selected.get("shared_records_vs_sim", 0), selected.get("integrated_records", 0)))],
            ["fasim_sim_recovery_filter_shadow_extra_records_vs_sim", str(selected.get("extra_records_vs_sim", 0))],
            ["fasim_sim_recovery_filter_shadow_nested_candidates", str(total_nested_candidates)],
            ["fasim_sim_recovery_filter_shadow_internal_peak_candidates", str(total_internal_peak_candidates)],
            ["fasim_sim_recovery_filter_shadow_unknown_candidates", str(total_unknown_candidates)],
            ["fasim_sim_recovery_filter_shadow_output_mutations", str(total_output_mutations + selected.get("output_mutations", 0))],
        ],
    )
    lines.append("")

    lines.append("## Decision")
    lines.append("")
    non_oracle = selected
    oracle = strategy_totals["oracle_sim_match"]
    non_oracle_recall = pct(non_oracle.get("shared_records_vs_sim", 0), non_oracle.get("sim_records", 0))
    non_oracle_precision = pct(non_oracle.get("shared_records_vs_sim", 0), non_oracle.get("integrated_records", 0))
    oracle_recall = pct(oracle.get("shared_records_vs_sim", 0), oracle.get("sim_records", 0))
    if total_output_mutations or non_oracle.get("output_mutations", 0):
        decision = "Stop: filter shadow observed output mutations, which violates diagnostic-only scope."
    elif non_oracle_recall >= 90.0 and non_oracle_precision >= 70.0:
        decision = (
            "A non-oracle filter preserves high SIM recall while substantially "
            "improving precision. A real SIM-close mode design is plausible next."
        )
    elif oracle_recall >= 90.0 and non_oracle_recall < 90.0:
        decision = (
            "Only the oracle upper bound preserves high recall. Do not proceed to "
            "real recovery; improve non-oracle features, ranking, or merge "
            "semantics first."
        )
    elif non_oracle_precision < 70.0:
        decision = (
            "The non-oracle filter reduces some candidates but precision remains "
            "low. Refine recovery boxes, candidate ranking, or de-dup semantics."
        )
    else:
        decision = "Filtering remains inconclusive; keep this as diagnostic-only."
    lines.append(decision)
    lines.append("")
    lines.append("Forbidden-scope check:")
    lines.append("")
    lines.append("```text")
    lines.append("Fasim output change: no")
    lines.append("Recovered records added to output: no")
    lines.append("Real FASIM_SIM_RECOVERY mode: no")
    lines.append("SIM-only labels used as production selection input: no")
    lines.append("Scoring/threshold/non-overlap behavior change: no")
    lines.append("GPU/filter behavior change: no")
    lines.append("Production accuracy claim: no")
    lines.append("```")

    for shadow in shadows:
        prefix = f"benchmark.fasim_sim_recovery_filter_shadow.{shadow.workload_label}"
        print(f"{prefix}.enabled=1")
        print(f"{prefix}.recovered_candidates={shadow.recovered_candidates}")
        print(f"{prefix}.fasim_duplicates={shadow.fasim_duplicates}")
        print(f"{prefix}.near_duplicates={shadow.near_duplicates}")
        print(f"{prefix}.sim_only_matches={shadow.sim_only_matches}")
        print(f"{prefix}.extra_vs_sim={shadow.extra_vs_sim}")
        print(f"{prefix}.overlap_conflicts_before={shadow.overlap_conflicts_before}")
        print(f"{prefix}.nested_candidates={shadow.nested_candidates}")
        print(f"{prefix}.internal_peak_candidates={shadow.internal_peak_candidates}")
        print(f"{prefix}.unknown_candidates={shadow.unknown_candidates}")
        print(f"{prefix}.output_mutations={shadow.output_mutations}")

    print("benchmark.fasim_sim_recovery_filter_shadow.total.enabled=1")
    print(f"benchmark.fasim_sim_recovery_filter_shadow.total.recovered_candidates={total_recovered_candidates}")
    print(f"benchmark.fasim_sim_recovery_filter_shadow.total.fasim_duplicates={total_fasim_duplicates}")
    print(f"benchmark.fasim_sim_recovery_filter_shadow.total.near_duplicates={total_near_duplicates}")
    print(f"benchmark.fasim_sim_recovery_filter_shadow.total.sim_only_matches={total_sim_only_matches}")
    print(f"benchmark.fasim_sim_recovery_filter_shadow.total.extra_vs_sim={total_extra_vs_sim}")
    print(f"benchmark.fasim_sim_recovery_filter_shadow.total.overlap_conflicts_before={total_overlap_conflicts_before}")
    print(f"benchmark.fasim_sim_recovery_filter_shadow.total.overlap_conflicts_after={selected.get('overlap_conflicts_after', 0)}")
    print(f"benchmark.fasim_sim_recovery_filter_shadow.total.filtered_candidates={selected.get('filtered_candidates', 0)}")
    print(f"benchmark.fasim_sim_recovery_filter_shadow.total.integrated_records={selected.get('integrated_records', 0)}")
    print(
        "benchmark.fasim_sim_recovery_filter_shadow.total.recall_vs_sim="
        f"{pct(selected.get('shared_records_vs_sim', 0), selected.get('sim_records', 0)):.6f}"
    )
    print(
        "benchmark.fasim_sim_recovery_filter_shadow.total.precision_vs_sim="
        f"{pct(selected.get('shared_records_vs_sim', 0), selected.get('integrated_records', 0)):.6f}"
    )
    print(f"benchmark.fasim_sim_recovery_filter_shadow.total.extra_records_vs_sim={selected.get('extra_records_vs_sim', 0)}")
    print(f"benchmark.fasim_sim_recovery_filter_shadow.total.output_mutations={total_output_mutations + selected.get('output_mutations', 0)}")
    for strategy in strategy_order:
        totals = strategy_totals[strategy]
        prefix = f"benchmark.fasim_sim_recovery_filter_shadow.strategy.{strategy}"
        print(f"{prefix}.oracle={1 if strategy_oracle.get(strategy, False) else 0}")
        print(f"{prefix}.recovered_candidates={totals.get('recovered_candidates', 0)}")
        print(f"{prefix}.filtered_candidates={totals.get('filtered_candidates', 0)}")
        print(f"{prefix}.integrated_records={totals.get('integrated_records', 0)}")
        print(f"{prefix}.sim_only_recovered={totals.get('sim_only_recovered', 0)}")
        print(f"{prefix}.recall_vs_sim={pct(totals.get('shared_records_vs_sim', 0), totals.get('sim_records', 0)):.6f}")
        print(
            f"{prefix}.precision_vs_sim="
            f"{pct(totals.get('shared_records_vs_sim', 0), totals.get('integrated_records', 0)):.6f}"
        )
        print(f"{prefix}.extra_records_vs_sim={totals.get('extra_records_vs_sim', 0)}")
        print(f"{prefix}.overlap_conflicts={totals.get('overlap_conflicts_after', 0)}")
        print(f"{prefix}.output_mutations={totals.get('output_mutations', 0)}")

    report = "\n".join(lines)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report + "\n", encoding="utf-8")
    return report


def render_replacement_shadow_report(
    *,
    gaps: Sequence[WorkloadGap],
    output_path: Path,
    profile_set: str,
) -> str:
    shadows = [gap.replacement_shadow for gap in gaps if gap.replacement_shadow is not None]
    if len(shadows) != len(gaps):
        raise RuntimeError("replacement shadow report requested without replacement shadow data")

    lines: List[str] = []
    lines.append("# Fasim Local SIM Recovery Replacement Shadow")
    lines.append("")
    lines.append("Base branch:")
    lines.append("")
    lines.append("```text")
    lines.append("fasim-local-sim-recovery-filter-shadow")
    lines.append("```")
    lines.append("")
    lines.append(
        "This report is diagnostic-only. It evaluates side replacement and merge "
        "strategies for Fasim records plus bounded local SIM recovery candidates. "
        "It does not add a real `FASIM_SIM_RECOVERY=1` mode, does not mutate "
        "Fasim output, and does not replace final non-overlap authority."
    )
    lines.append("")
    lines.append(
        "The `oracle_box_replacement` strategy uses legacy SIM membership after "
        "candidate generation and is included only as an upper-bound analysis. "
        "It is forbidden as production selection input."
    )
    lines.append("")
    append_table(
        lines,
        ["Setting", "Value"],
        [
            ["profile_set", profile_set],
            ["input_candidates", "bounded local SIM executor raw records"],
            ["replacement_candidate_filter", "candidate score >= 89 and Nt >= 50"],
            ["box_local_replacement", "suppress Fasim records inside detector boxes"],
            ["family_replacement", "suppress Fasim records in recovered candidate families"],
            ["output_mutations_expected", "0"],
        ],
    )
    lines.append("")

    strategy_order = [
        "raw_union",
        "filtered_union",
        "box_local_replacement",
        "family_replacement",
        "conservative_replacement",
        "oracle_box_replacement",
    ]
    strategy_totals: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    strategy_oracle: Dict[str, bool] = {}
    workload_rows: List[List[str]] = []

    for shadow in shadows:
        for result in shadow.strategies:
            totals = strategy_totals[result.strategy]
            strategy_oracle[result.strategy] = result.oracle
            totals["fasim_records"] += result.fasim_records
            totals["recovered_candidates"] += result.recovered_candidates
            totals["fasim_records_suppressed"] += result.fasim_records_suppressed
            totals["recovered_records_accepted"] += result.recovered_records_accepted
            totals["integrated_records"] += result.integrated_records
            totals["sim_records"] += result.sim_records
            totals["sim_only_recovered"] += result.sim_only_recovered
            totals["shared_records_vs_sim"] += result.shared_records_vs_sim
            totals["extra_records_vs_sim"] += result.extra_records_vs_sim
            totals["overlap_conflicts"] += result.overlap_conflicts
            totals["output_mutations"] += result.output_mutations
            workload_rows.append(
                [
                    result.workload_label,
                    result.strategy,
                    "yes" if result.oracle else "no",
                    str(result.integrated_records),
                    str(result.fasim_records_suppressed),
                    str(result.recovered_records_accepted),
                    fmt_pct(result.recall_vs_sim),
                    fmt_pct(result.precision_vs_sim),
                    str(result.extra_records_vs_sim),
                    str(result.overlap_conflicts),
                    str(result.output_mutations),
                ]
            )

    lines.append("## Workload Strategy Summary")
    lines.append("")
    append_table(
        lines,
        [
            "Workload",
            "Strategy",
            "Oracle",
            "Integrated records",
            "Fasim suppressed",
            "Recovered accepted",
            "Recall vs SIM",
            "Precision vs SIM",
            "Extra vs SIM",
            "Overlap conflicts",
            "Output mutations",
        ],
        workload_rows,
    )
    lines.append("")

    strategy_rows: List[List[str]] = []
    for strategy in strategy_order:
        totals = strategy_totals[strategy]
        strategy_rows.append(
            [
                strategy,
                "yes" if strategy_oracle.get(strategy, False) else "no",
                str(totals.get("integrated_records", 0)),
                str(totals.get("fasim_records_suppressed", 0)),
                str(totals.get("recovered_records_accepted", 0)),
                fmt_pct(pct(totals.get("shared_records_vs_sim", 0), totals.get("sim_records", 0))),
                fmt_pct(pct(totals.get("shared_records_vs_sim", 0), totals.get("integrated_records", 0))),
                str(totals.get("extra_records_vs_sim", 0)),
                str(totals.get("overlap_conflicts", 0)),
                str(totals.get("output_mutations", 0)),
            ]
        )

    lines.append("## Strategy Summary")
    lines.append("")
    append_table(
        lines,
        [
            "Strategy",
            "Oracle",
            "Integrated records",
            "Fasim suppressed",
            "Recovered accepted",
            "Recall vs SIM",
            "Precision vs SIM",
            "Extra vs SIM",
            "Overlap conflicts",
            "Output mutations",
        ],
        strategy_rows,
    )
    lines.append("")

    non_oracle_replacement_order = [
        "box_local_replacement",
        "family_replacement",
        "conservative_replacement",
    ]
    selected_strategy = max(
        non_oracle_replacement_order,
        key=lambda strategy: (
            pct(strategy_totals[strategy].get("shared_records_vs_sim", 0), strategy_totals[strategy].get("sim_records", 0)),
            pct(strategy_totals[strategy].get("shared_records_vs_sim", 0), strategy_totals[strategy].get("integrated_records", 0)),
            -strategy_totals[strategy].get("extra_records_vs_sim", 0),
        ),
    )
    selected = strategy_totals[selected_strategy]
    oracle = strategy_totals["oracle_box_replacement"]
    total_fasim = strategy_totals["raw_union"].get("fasim_records", 0)
    total_candidates = strategy_totals["raw_union"].get("recovered_candidates", 0)
    selected_recall = pct(selected.get("shared_records_vs_sim", 0), selected.get("sim_records", 0))
    selected_precision = pct(selected.get("shared_records_vs_sim", 0), selected.get("integrated_records", 0))
    oracle_precision = pct(oracle.get("shared_records_vs_sim", 0), oracle.get("integrated_records", 0))
    total_output_mutations = selected.get("output_mutations", 0)

    lines.append("## Aggregate")
    lines.append("")
    append_table(
        lines,
        ["Metric", "Value"],
        [
            ["fasim_sim_recovery_replacement_shadow_enabled", "1"],
            ["fasim_sim_recovery_replacement_shadow_strategy", selected_strategy],
            ["fasim_sim_recovery_replacement_shadow_fasim_records", str(total_fasim)],
            ["fasim_sim_recovery_replacement_shadow_recovered_candidates", str(total_candidates)],
            ["fasim_sim_recovery_replacement_shadow_fasim_records_suppressed", str(selected.get("fasim_records_suppressed", 0))],
            ["fasim_sim_recovery_replacement_shadow_recovered_records_accepted", str(selected.get("recovered_records_accepted", 0))],
            ["fasim_sim_recovery_replacement_shadow_integrated_records", str(selected.get("integrated_records", 0))],
            ["fasim_sim_recovery_replacement_shadow_sim_records", str(selected.get("sim_records", 0))],
            ["fasim_sim_recovery_replacement_shadow_sim_only_recovered", str(selected.get("sim_only_recovered", 0))],
            ["fasim_sim_recovery_replacement_shadow_recall_vs_sim", fmt_pct(selected_recall)],
            ["fasim_sim_recovery_replacement_shadow_precision_vs_sim", fmt_pct(selected_precision)],
            ["fasim_sim_recovery_replacement_shadow_extra_records_vs_sim", str(selected.get("extra_records_vs_sim", 0))],
            ["fasim_sim_recovery_replacement_shadow_overlap_conflicts", str(selected.get("overlap_conflicts", 0))],
            ["fasim_sim_recovery_replacement_shadow_output_mutations", str(total_output_mutations)],
        ],
    )
    lines.append("")

    lines.append("## Decision")
    lines.append("")
    if total_output_mutations:
        decision = "Stop: replacement shadow observed output mutations, which violates diagnostic-only scope."
    elif selected_recall >= 90.0 and selected_precision >= 70.0:
        decision = (
            "A non-oracle replacement strategy keeps high SIM recall and greatly "
            "reduces extras/conflicts. A real SIM-close mode design is plausible next."
        )
    elif selected_recall >= 90.0 and selected_precision >= 50.0:
        decision = (
            "Replacement semantics improve the raw-union shape but precision is "
            "still below the strong threshold. Refine replacement guards, "
            "candidate ranking, or box/family selection before a real mode."
        )
    elif oracle_precision >= 90.0:
        decision = (
            "The oracle replacement upper bound is strong, but non-oracle "
            "replacement still loses too much precision or recall. Improve "
            "non-oracle guards before a real mode."
        )
    else:
        decision = (
            "Replacement does not yet provide a clean SIM-close side output. Keep "
            "this diagnostic-only and revisit the canonical output model."
        )
    lines.append(decision)
    lines.append("")
    lines.append("Forbidden-scope check:")
    lines.append("")
    lines.append("```text")
    lines.append("Fasim output change: no")
    lines.append("Recovered records added to output: no")
    lines.append("Real FASIM_SIM_RECOVERY mode: no")
    lines.append("SIM-only labels used as production selection input: no")
    lines.append("Scoring/threshold/non-overlap behavior change: no")
    lines.append("GPU/filter behavior change: no")
    lines.append("Production accuracy claim: no")
    lines.append("```")

    for shadow in shadows:
        prefix = f"benchmark.fasim_sim_recovery_replacement_shadow.{shadow.workload_label}"
        print(f"{prefix}.enabled=1")
        print(f"{prefix}.fasim_records={shadow.fasim_records}")
        print(f"{prefix}.recovered_candidates={shadow.recovered_candidates}")
        print(f"{prefix}.output_mutations={shadow.output_mutations}")
        for result in shadow.strategies:
            strategy_prefix = f"{prefix}.strategy.{result.strategy}"
            print(f"{strategy_prefix}.oracle={1 if result.oracle else 0}")
            print(f"{strategy_prefix}.fasim_records_suppressed={result.fasim_records_suppressed}")
            print(f"{strategy_prefix}.recovered_records_accepted={result.recovered_records_accepted}")
            print(f"{strategy_prefix}.integrated_records={result.integrated_records}")
            print(f"{strategy_prefix}.sim_only_recovered={result.sim_only_recovered}")
            print(f"{strategy_prefix}.recall_vs_sim={result.recall_vs_sim:.6f}")
            print(f"{strategy_prefix}.precision_vs_sim={result.precision_vs_sim:.6f}")
            print(f"{strategy_prefix}.extra_records_vs_sim={result.extra_records_vs_sim}")
            print(f"{strategy_prefix}.overlap_conflicts={result.overlap_conflicts}")
            print(f"{strategy_prefix}.output_mutations={result.output_mutations}")

    print("benchmark.fasim_sim_recovery_replacement_shadow.total.enabled=1")
    print(f"benchmark.fasim_sim_recovery_replacement_shadow.total.strategy={selected_strategy}")
    print(f"benchmark.fasim_sim_recovery_replacement_shadow.total.fasim_records={total_fasim}")
    print(f"benchmark.fasim_sim_recovery_replacement_shadow.total.recovered_candidates={total_candidates}")
    print(
        "benchmark.fasim_sim_recovery_replacement_shadow.total.fasim_records_suppressed="
        f"{selected.get('fasim_records_suppressed', 0)}"
    )
    print(
        "benchmark.fasim_sim_recovery_replacement_shadow.total.recovered_records_accepted="
        f"{selected.get('recovered_records_accepted', 0)}"
    )
    print(f"benchmark.fasim_sim_recovery_replacement_shadow.total.integrated_records={selected.get('integrated_records', 0)}")
    print(f"benchmark.fasim_sim_recovery_replacement_shadow.total.sim_records={selected.get('sim_records', 0)}")
    print(f"benchmark.fasim_sim_recovery_replacement_shadow.total.sim_only_recovered={selected.get('sim_only_recovered', 0)}")
    print(f"benchmark.fasim_sim_recovery_replacement_shadow.total.recall_vs_sim={selected_recall:.6f}")
    print(f"benchmark.fasim_sim_recovery_replacement_shadow.total.precision_vs_sim={selected_precision:.6f}")
    print(f"benchmark.fasim_sim_recovery_replacement_shadow.total.extra_records_vs_sim={selected.get('extra_records_vs_sim', 0)}")
    print(f"benchmark.fasim_sim_recovery_replacement_shadow.total.overlap_conflicts={selected.get('overlap_conflicts', 0)}")
    print(f"benchmark.fasim_sim_recovery_replacement_shadow.total.output_mutations={total_output_mutations}")
    for strategy in strategy_order:
        totals = strategy_totals[strategy]
        prefix = f"benchmark.fasim_sim_recovery_replacement_shadow.strategy.{strategy}"
        print(f"{prefix}.oracle={1 if strategy_oracle.get(strategy, False) else 0}")
        print(f"{prefix}.fasim_records_suppressed={totals.get('fasim_records_suppressed', 0)}")
        print(f"{prefix}.recovered_records_accepted={totals.get('recovered_records_accepted', 0)}")
        print(f"{prefix}.integrated_records={totals.get('integrated_records', 0)}")
        print(f"{prefix}.sim_only_recovered={totals.get('sim_only_recovered', 0)}")
        print(
            f"{prefix}.recall_vs_sim="
            f"{pct(totals.get('shared_records_vs_sim', 0), totals.get('sim_records', 0)):.6f}"
        )
        print(
            f"{prefix}.precision_vs_sim="
            f"{pct(totals.get('shared_records_vs_sim', 0), totals.get('integrated_records', 0)):.6f}"
        )
        print(f"{prefix}.extra_records_vs_sim={totals.get('extra_records_vs_sim', 0)}")
        print(f"{prefix}.overlap_conflicts={totals.get('overlap_conflicts', 0)}")
        print(f"{prefix}.output_mutations={totals.get('output_mutations', 0)}")

    report = "\n".join(lines)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report + "\n", encoding="utf-8")
    return report


def fmt_float(value: float) -> str:
    return f"{value:.2f}"


def render_replacement_extra_taxonomy_report(
    *,
    gaps: Sequence[WorkloadGap],
    output_path: Path,
    profile_set: str,
) -> str:
    taxonomies = [gap.replacement_extra_taxonomy for gap in gaps if gap.replacement_extra_taxonomy is not None]
    if len(taxonomies) != len(gaps):
        raise RuntimeError("replacement extra taxonomy report requested without replacement extra taxonomy data")

    lines: List[str] = []
    lines.append("# Fasim Local SIM Recovery Replacement Extra Taxonomy")
    lines.append("")
    lines.append("Base branch:")
    lines.append("")
    lines.append("```text")
    lines.append("fasim-local-sim-recovery-replacement-shadow")
    lines.append("```")
    lines.append("")
    lines.append(
        "This report is diagnostic-only. It analyzes the extra records left by "
        "the best non-oracle replacement shape and evaluates non-oracle guards "
        "against the side replacement candidate set. It does not add a real "
        "`FASIM_SIM_RECOVERY=1` mode and does not mutate Fasim output."
    )
    lines.append("")
    lines.append(
        "Legacy SIM membership is used only after candidate generation for "
        "taxonomy and guard evaluation. It is forbidden as production selection "
        "input."
    )
    lines.append("")
    append_table(
        lines,
        ["Setting", "Value"],
        [
            ["profile_set", profile_set],
            ["input_candidates", "box-local replacement accepted candidates"],
            ["base_replacement_filter", "candidate score >= 89 and Nt >= 50"],
            ["selected_non_oracle_guard", "combined_non_oracle"],
            ["oracle_guard", "oracle_sim_match, analysis-only upper bound"],
            ["output_mutations_expected", "0"],
        ],
    )
    lines.append("")

    feature_rows: List[List[str]] = []
    guard_rows: List[List[str]] = []
    total_true = 0
    total_extra = 0
    total_dominated_true = 0
    total_dominated_extra = 0
    total_contained_true = 0
    total_contained_extra = 0
    total_output_mutations = 0
    total_overlap_conflicts = 0
    true_score_mins: List[float] = []
    extra_score_mins: List[float] = []
    true_nt_mins: List[int] = []
    extra_nt_mins: List[int] = []
    true_rank_p50s: List[float] = []
    extra_rank_p50s: List[float] = []
    true_boundary_p50s: List[float] = []
    extra_boundary_p50s: List[float] = []
    guard_order = [
        "score_nt_threshold",
        "local_rank_topk_per_box",
        "family_rank_topk",
        "dominance_filter",
        "containment_boundary_guard",
        "combined_non_oracle",
        "oracle_sim_match",
    ]
    guard_totals: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    guard_oracle: Dict[str, bool] = {}

    for taxonomy in taxonomies:
        total_true += taxonomy.true_sim_records
        total_extra += taxonomy.extra_records
        total_dominated_true += taxonomy.dominated_true
        total_dominated_extra += taxonomy.dominated_extra
        total_contained_true += taxonomy.contained_true
        total_contained_extra += taxonomy.contained_extra
        total_output_mutations += taxonomy.output_mutations
        total_overlap_conflicts += taxonomy.overlap_conflicts
        if taxonomy.true_sim_records:
            true_score_mins.append(taxonomy.score_min_true)
            true_nt_mins.append(taxonomy.nt_min_true)
            true_rank_p50s.append(taxonomy.rank_true_p50)
            true_boundary_p50s.append(taxonomy.boundary_distance_true_p50)
        if taxonomy.extra_records:
            extra_score_mins.append(taxonomy.score_min_extra)
            extra_nt_mins.append(taxonomy.nt_min_extra)
            extra_rank_p50s.append(taxonomy.rank_extra_p50)
            extra_boundary_p50s.append(taxonomy.boundary_distance_extra_p50)
        feature_rows.append(
            [
                taxonomy.workload_label,
                str(taxonomy.true_sim_records),
                str(taxonomy.extra_records),
                fmt_float(taxonomy.score_min_true),
                fmt_float(taxonomy.score_min_extra),
                str(taxonomy.nt_min_true),
                str(taxonomy.nt_min_extra),
                fmt_float(taxonomy.rank_true_p50),
                fmt_float(taxonomy.rank_extra_p50),
                str(taxonomy.dominated_true),
                str(taxonomy.dominated_extra),
                str(taxonomy.contained_true),
                str(taxonomy.contained_extra),
                fmt_float(taxonomy.boundary_distance_true_p50),
                fmt_float(taxonomy.boundary_distance_extra_p50),
                str(taxonomy.overlap_conflicts),
                str(taxonomy.output_mutations),
            ]
        )
        for guard in taxonomy.guards:
            totals = guard_totals[guard.guard]
            guard_oracle[guard.guard] = guard.oracle
            totals["selected_candidates"] += guard.selected_candidates
            totals["integrated_records"] += guard.integrated_records
            totals["sim_records"] += guard.sim_records
            totals["sim_only_recovered"] += guard.sim_only_recovered
            totals["shared_records_vs_sim"] += guard.shared_records_vs_sim
            totals["extra_records_vs_sim"] += guard.extra_records_vs_sim
            totals["overlap_conflicts"] += guard.overlap_conflicts
            totals["output_mutations"] += guard.output_mutations
            guard_rows.append(
                [
                    guard.workload_label,
                    guard.guard,
                    "yes" if guard.oracle else "no",
                    str(guard.selected_candidates),
                    str(guard.integrated_records),
                    str(guard.sim_only_recovered),
                    fmt_pct(guard.recall_vs_sim),
                    fmt_pct(guard.precision_vs_sim),
                    str(guard.extra_records_vs_sim),
                    str(guard.overlap_conflicts),
                    str(guard.output_mutations),
                ]
            )

    lines.append("## Workload Feature Summary")
    lines.append("")
    append_table(
        lines,
        [
            "Workload",
            "True SIM records",
            "Extra records",
            "Score min true",
            "Score min extra",
            "Nt min true",
            "Nt min extra",
            "Local rank true p50",
            "Local rank extra p50",
            "Dominated true",
            "Dominated extra",
            "Contained true",
            "Contained extra",
            "Boundary true p50",
            "Boundary extra p50",
            "Overlap conflicts",
            "Output mutations",
        ],
        feature_rows,
    )
    lines.append("")

    lines.append("## Guard Evaluation")
    lines.append("")
    append_table(
        lines,
        [
            "Workload",
            "Guard",
            "Oracle",
            "Selected candidates",
            "Integrated records",
            "SIM-only recovered",
            "Recall vs SIM",
            "Precision vs SIM",
            "Extra vs SIM",
            "Overlap conflicts",
            "Output mutations",
        ],
        guard_rows,
    )
    lines.append("")

    guard_summary_rows: List[List[str]] = []
    for guard in guard_order:
        totals = guard_totals[guard]
        guard_summary_rows.append(
            [
                guard,
                "yes" if guard_oracle.get(guard, False) else "no",
                str(totals.get("selected_candidates", 0)),
                str(totals.get("integrated_records", 0)),
                str(totals.get("sim_only_recovered", 0)),
                fmt_pct(pct(totals.get("shared_records_vs_sim", 0), totals.get("sim_records", 0))),
                fmt_pct(pct(totals.get("shared_records_vs_sim", 0), totals.get("integrated_records", 0))),
                str(totals.get("extra_records_vs_sim", 0)),
                str(totals.get("overlap_conflicts", 0)),
                str(totals.get("output_mutations", 0)),
            ]
        )

    lines.append("## Guard Summary")
    lines.append("")
    append_table(
        lines,
        [
            "Guard",
            "Oracle",
            "Selected candidates",
            "Integrated records",
            "SIM-only recovered",
            "Recall vs SIM",
            "Precision vs SIM",
            "Extra vs SIM",
            "Overlap conflicts",
            "Output mutations",
        ],
        guard_summary_rows,
    )
    lines.append("")

    selected_guard = "combined_non_oracle"
    selected = guard_totals[selected_guard]
    oracle = guard_totals["oracle_sim_match"]
    selected_recall = pct(selected.get("shared_records_vs_sim", 0), selected.get("sim_records", 0))
    selected_precision = pct(selected.get("shared_records_vs_sim", 0), selected.get("integrated_records", 0))
    oracle_precision = pct(oracle.get("shared_records_vs_sim", 0), oracle.get("integrated_records", 0))
    aggregate_score_min_true = min_float(true_score_mins)
    aggregate_score_min_extra = min_float(extra_score_mins)
    aggregate_nt_min_true = min_int(true_nt_mins)
    aggregate_nt_min_extra = min_int(extra_nt_mins)
    aggregate_rank_true_p50 = median_value(true_rank_p50s)
    aggregate_rank_extra_p50 = median_value(extra_rank_p50s)
    aggregate_boundary_true_p50 = median_value(true_boundary_p50s)
    aggregate_boundary_extra_p50 = median_value(extra_boundary_p50s)

    lines.append("## Aggregate")
    lines.append("")
    append_table(
        lines,
        ["Metric", "Value"],
        [
            ["fasim_sim_recovery_extra_taxonomy_enabled", "1"],
            ["fasim_sim_recovery_extra_taxonomy_true_sim_records", str(total_true)],
            ["fasim_sim_recovery_extra_taxonomy_extra_records", str(total_extra)],
            ["fasim_sim_recovery_extra_taxonomy_score_min_true", fmt_float(aggregate_score_min_true)],
            ["fasim_sim_recovery_extra_taxonomy_score_min_extra", fmt_float(aggregate_score_min_extra)],
            ["fasim_sim_recovery_extra_taxonomy_nt_min_true", str(aggregate_nt_min_true)],
            ["fasim_sim_recovery_extra_taxonomy_nt_min_extra", str(aggregate_nt_min_extra)],
            ["fasim_sim_recovery_extra_taxonomy_rank_true_p50", fmt_float(aggregate_rank_true_p50)],
            ["fasim_sim_recovery_extra_taxonomy_rank_extra_p50", fmt_float(aggregate_rank_extra_p50)],
            ["fasim_sim_recovery_extra_taxonomy_dominated_true", str(total_dominated_true)],
            ["fasim_sim_recovery_extra_taxonomy_dominated_extra", str(total_dominated_extra)],
            ["fasim_sim_recovery_extra_taxonomy_contained_true", str(total_contained_true)],
            ["fasim_sim_recovery_extra_taxonomy_contained_extra", str(total_contained_extra)],
            ["fasim_sim_recovery_extra_taxonomy_boundary_distance_true_p50", fmt_float(aggregate_boundary_true_p50)],
            ["fasim_sim_recovery_extra_taxonomy_boundary_distance_extra_p50", fmt_float(aggregate_boundary_extra_p50)],
            ["fasim_sim_recovery_extra_taxonomy_overlap_conflicts", str(total_overlap_conflicts)],
            ["fasim_sim_recovery_extra_taxonomy_selected_guard", selected_guard],
            ["fasim_sim_recovery_extra_taxonomy_selected_guard_recall_vs_sim", fmt_pct(selected_recall)],
            ["fasim_sim_recovery_extra_taxonomy_selected_guard_precision_vs_sim", fmt_pct(selected_precision)],
            ["fasim_sim_recovery_extra_taxonomy_selected_guard_extra_records_vs_sim", str(selected.get("extra_records_vs_sim", 0))],
            ["fasim_sim_recovery_extra_taxonomy_selected_guard_overlap_conflicts", str(selected.get("overlap_conflicts", 0))],
            ["fasim_sim_recovery_extra_taxonomy_output_mutations", str(total_output_mutations + selected.get("output_mutations", 0))],
        ],
    )
    lines.append("")

    lines.append("## Decision")
    lines.append("")
    if total_output_mutations or selected.get("output_mutations", 0):
        decision = "Stop: extra taxonomy observed output mutations, which violates diagnostic-only scope."
    elif selected_recall >= 90.0 and selected_precision >= 80.0:
        decision = (
            "A non-oracle guard reaches the strong recall/precision target on "
            "these representative synthetic fixtures. The next PR can design a "
            "real SIM-close mode, but this remains diagnostic-only."
        )
    elif selected_recall >= 90.0 and selected_precision >= 70.0:
        decision = (
            "The selected non-oracle guard keeps high recall but precision remains "
            "in the 70-80% band. Refine ranking or merge semantics before a real mode."
        )
    elif oracle_precision >= 90.0:
        decision = (
            "The oracle upper bound is strong, but non-oracle guards do not yet "
            "separate extras cleanly. Do not proceed to real recovery."
        )
    else:
        decision = (
            "Extras are not cleanly separated by the current feature set. "
            "SIM-close mode may need a different output model."
        )
    lines.append(decision)
    lines.append("")
    lines.append("Forbidden-scope check:")
    lines.append("")
    lines.append("```text")
    lines.append("Fasim output change: no")
    lines.append("Recovered records added to output: no")
    lines.append("Real FASIM_SIM_RECOVERY mode: no")
    lines.append("SIM-only labels used as production selection input: no")
    lines.append("Scoring/threshold/non-overlap behavior change: no")
    lines.append("GPU/filter behavior change: no")
    lines.append("Production accuracy claim: no")
    lines.append("```")

    for taxonomy in taxonomies:
        prefix = f"benchmark.fasim_sim_recovery_extra_taxonomy.{taxonomy.workload_label}"
        print(f"{prefix}.enabled=1")
        print(f"{prefix}.true_sim_records={taxonomy.true_sim_records}")
        print(f"{prefix}.extra_records={taxonomy.extra_records}")
        print(f"{prefix}.score_min_true={taxonomy.score_min_true:.6f}")
        print(f"{prefix}.score_min_extra={taxonomy.score_min_extra:.6f}")
        print(f"{prefix}.nt_min_true={taxonomy.nt_min_true}")
        print(f"{prefix}.nt_min_extra={taxonomy.nt_min_extra}")
        print(f"{prefix}.rank_true_p50={taxonomy.rank_true_p50:.6f}")
        print(f"{prefix}.rank_extra_p50={taxonomy.rank_extra_p50:.6f}")
        print(f"{prefix}.dominated_true={taxonomy.dominated_true}")
        print(f"{prefix}.dominated_extra={taxonomy.dominated_extra}")
        print(f"{prefix}.contained_true={taxonomy.contained_true}")
        print(f"{prefix}.contained_extra={taxonomy.contained_extra}")
        print(f"{prefix}.boundary_distance_true_p50={taxonomy.boundary_distance_true_p50:.6f}")
        print(f"{prefix}.boundary_distance_extra_p50={taxonomy.boundary_distance_extra_p50:.6f}")
        print(f"{prefix}.overlap_conflicts={taxonomy.overlap_conflicts}")
        print(f"{prefix}.output_mutations={taxonomy.output_mutations}")
        for guard in taxonomy.guards:
            guard_prefix = f"{prefix}.guard.{guard.guard}"
            print(f"{guard_prefix}.oracle={1 if guard.oracle else 0}")
            print(f"{guard_prefix}.selected_candidates={guard.selected_candidates}")
            print(f"{guard_prefix}.integrated_records={guard.integrated_records}")
            print(f"{guard_prefix}.sim_only_recovered={guard.sim_only_recovered}")
            print(f"{guard_prefix}.recall_vs_sim={guard.recall_vs_sim:.6f}")
            print(f"{guard_prefix}.precision_vs_sim={guard.precision_vs_sim:.6f}")
            print(f"{guard_prefix}.extra_records_vs_sim={guard.extra_records_vs_sim}")
            print(f"{guard_prefix}.overlap_conflicts={guard.overlap_conflicts}")
            print(f"{guard_prefix}.output_mutations={guard.output_mutations}")

    print("benchmark.fasim_sim_recovery_extra_taxonomy.total.enabled=1")
    print(f"benchmark.fasim_sim_recovery_extra_taxonomy.total.true_sim_records={total_true}")
    print(f"benchmark.fasim_sim_recovery_extra_taxonomy.total.extra_records={total_extra}")
    print(f"benchmark.fasim_sim_recovery_extra_taxonomy.total.score_min_true={aggregate_score_min_true:.6f}")
    print(f"benchmark.fasim_sim_recovery_extra_taxonomy.total.score_min_extra={aggregate_score_min_extra:.6f}")
    print(f"benchmark.fasim_sim_recovery_extra_taxonomy.total.nt_min_true={aggregate_nt_min_true}")
    print(f"benchmark.fasim_sim_recovery_extra_taxonomy.total.nt_min_extra={aggregate_nt_min_extra}")
    print(f"benchmark.fasim_sim_recovery_extra_taxonomy.total.rank_true_p50={aggregate_rank_true_p50:.6f}")
    print(f"benchmark.fasim_sim_recovery_extra_taxonomy.total.rank_extra_p50={aggregate_rank_extra_p50:.6f}")
    print(f"benchmark.fasim_sim_recovery_extra_taxonomy.total.dominated_true={total_dominated_true}")
    print(f"benchmark.fasim_sim_recovery_extra_taxonomy.total.dominated_extra={total_dominated_extra}")
    print(f"benchmark.fasim_sim_recovery_extra_taxonomy.total.contained_true={total_contained_true}")
    print(f"benchmark.fasim_sim_recovery_extra_taxonomy.total.contained_extra={total_contained_extra}")
    print(f"benchmark.fasim_sim_recovery_extra_taxonomy.total.boundary_distance_true_p50={aggregate_boundary_true_p50:.6f}")
    print(f"benchmark.fasim_sim_recovery_extra_taxonomy.total.boundary_distance_extra_p50={aggregate_boundary_extra_p50:.6f}")
    print(f"benchmark.fasim_sim_recovery_extra_taxonomy.total.overlap_conflicts={total_overlap_conflicts}")
    print(f"benchmark.fasim_sim_recovery_extra_taxonomy.total.output_mutations={total_output_mutations + selected.get('output_mutations', 0)}")
    for guard in guard_order:
        totals = guard_totals[guard]
        prefix = f"benchmark.fasim_sim_recovery_extra_taxonomy.guard.{guard}"
        print(f"{prefix}.oracle={1 if guard_oracle.get(guard, False) else 0}")
        print(f"{prefix}.selected_candidates={totals.get('selected_candidates', 0)}")
        print(f"{prefix}.integrated_records={totals.get('integrated_records', 0)}")
        print(f"{prefix}.sim_only_recovered={totals.get('sim_only_recovered', 0)}")
        print(f"{prefix}.recall_vs_sim={pct(totals.get('shared_records_vs_sim', 0), totals.get('sim_records', 0)):.6f}")
        print(
            f"{prefix}.precision_vs_sim="
            f"{pct(totals.get('shared_records_vs_sim', 0), totals.get('integrated_records', 0)):.6f}"
        )
        print(f"{prefix}.extra_records_vs_sim={totals.get('extra_records_vs_sim', 0)}")
        print(f"{prefix}.overlap_conflicts={totals.get('overlap_conflicts', 0)}")
        print(f"{prefix}.output_mutations={totals.get('output_mutations', 0)}")

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
    parser.add_argument("--executor-shadow", action="store_true")
    parser.add_argument("--executor-shadow-output", default=str(ROOT / "docs" / "fasim_local_sim_recovery_executor_shadow.md"))
    parser.add_argument("--integration-shadow", action="store_true")
    parser.add_argument("--integration-shadow-output", default=str(ROOT / "docs" / "fasim_local_sim_recovery_integration_shadow.md"))
    parser.add_argument("--filter-shadow", action="store_true")
    parser.add_argument("--filter-shadow-output", default=str(ROOT / "docs" / "fasim_local_sim_recovery_filter_shadow.md"))
    parser.add_argument("--replacement-shadow", action="store_true")
    parser.add_argument("--replacement-shadow-output", default=str(ROOT / "docs" / "fasim_local_sim_recovery_replacement_shadow.md"))
    parser.add_argument("--replacement-extra-taxonomy", action="store_true")
    parser.add_argument(
        "--replacement-extra-taxonomy-output",
        default=str(ROOT / "docs" / "fasim_local_sim_recovery_replacement_extra_taxonomy.md"),
    )
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
        executor_shadow_enabled = args.executor_shadow or os.environ.get("FASIM_SIM_RECOVERY_EXECUTOR_SHADOW") == "1"
        integration_shadow_enabled = args.integration_shadow or os.environ.get("FASIM_SIM_RECOVERY_INTEGRATION_SHADOW") == "1"
        filter_shadow_enabled = args.filter_shadow or os.environ.get("FASIM_SIM_RECOVERY_FILTER_SHADOW") == "1"
        replacement_shadow_enabled = args.replacement_shadow or os.environ.get("FASIM_SIM_RECOVERY_REPLACEMENT_SHADOW") == "1"
        replacement_extra_taxonomy_enabled = (
            args.replacement_extra_taxonomy
            or os.environ.get("FASIM_SIM_RECOVERY_REPLACEMENT_EXTRA_TAXONOMY") == "1"
        )
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
                    bin_path=bin_path,
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
                    executor_shadow_enabled=executor_shadow_enabled,
                    integration_shadow_enabled=integration_shadow_enabled,
                    filter_shadow_enabled=filter_shadow_enabled,
                    replacement_shadow_enabled=replacement_shadow_enabled,
                    replacement_extra_taxonomy_enabled=replacement_extra_taxonomy_enabled,
                    executor_shadow_work_dir=work_dir_base / spec.label / "executor_shadow",
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
        if executor_shadow_enabled:
            print(
                render_executor_shadow_report(
                    gaps=gaps,
                    output_path=Path(args.executor_shadow_output),
                    profile_set=args.profile_set,
                )
            )
        if integration_shadow_enabled:
            print(
                render_integration_shadow_report(
                    gaps=gaps,
                    output_path=Path(args.integration_shadow_output),
                    profile_set=args.profile_set,
                )
            )
        if filter_shadow_enabled:
            print(
                render_filter_shadow_report(
                    gaps=gaps,
                    output_path=Path(args.filter_shadow_output),
                    profile_set=args.profile_set,
                )
            )
        if replacement_shadow_enabled:
            print(
                render_replacement_shadow_report(
                    gaps=gaps,
                    output_path=Path(args.replacement_shadow_output),
                    profile_set=args.profile_set,
                )
            )
        if replacement_extra_taxonomy_enabled:
            print(
                render_replacement_extra_taxonomy_report(
                    gaps=gaps,
                    output_path=Path(args.replacement_extra_taxonomy_output),
                    profile_set=args.profile_set,
                )
            )
        return 0
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
