#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
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
    box_cells,
    build_sim_recovery_real_mode,
    candidate_local_ranks,
    classify_sim_only_record,
    combined_non_oracle_candidate_raw,
    count_same_family_genomic_overlaps,
    dominated_by_higher_score,
    expand_interval,
    index_by_family,
    merge_recovery_boxes,
    overlaps,
    parse_genomic_header,
    parse_lite_records,
    pct,
    record_in_any_box,
    records_by_box,
    records_overlap_in_both_axes,
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
    sim_close_artifacts: "RecoveryRunArtifacts"
    validate_mode: Optional[object]
    validate_wall_seconds: float
    validate_artifacts: Optional["RecoveryRunArtifacts"]
    validation_coverage: "ValidationCoverage"
    miss_taxonomy: Optional["MissTaxonomy"]
    recall_repair_results: Tuple["RecallRepairResult", ...]
    score_landscape_results: Tuple["ScoreLandscapeDetectorResult", ...]


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


@dataclasses.dataclass(frozen=True)
class MissTaxonomy:
    enabled: bool
    sim_records: int
    shared_records: int
    missed_records: int
    not_box_covered: int
    box_covered_but_executor_missing: int
    guard_rejected: int
    replacement_suppressed: int
    canonicalization_mismatches: int
    metric_ambiguity_records: int


@dataclasses.dataclass(frozen=True)
class RecallRepairResult:
    workload_label: str
    strategy: str
    enabled: bool
    boxes: int
    cells: int
    full_search_cells: int
    sim_records: int
    shared_records: int
    missed_records: int
    not_box_covered: int
    guard_rejected: int
    recovered_from_box_expansion: int
    recovered_from_guard_relaxation: int
    extra_vs_sim: int
    overlap_conflicts: int
    output_mutations: int
    oracle: bool = False

    @property
    def cell_fraction(self) -> float:
        return (self.cells / self.full_search_cells * 100.0) if self.full_search_cells else 0.0

    @property
    def recall_vs_sim(self) -> float:
        return pct(self.shared_records, self.sim_records) if self.sim_records else 0.0

    @property
    def precision_vs_sim(self) -> float:
        output_records = self.shared_records + self.extra_vs_sim
        return pct(self.shared_records, output_records) if output_records else 0.0


@dataclasses.dataclass(frozen=True)
class ScoreLandscapeDetectorResult:
    workload_label: str
    strategy: str
    enabled: bool
    boxes: int
    cells: int
    full_search_cells: int
    sim_records: int
    shared_records: int
    missed_records: int
    not_box_covered: int
    guard_rejected: int
    extra_vs_sim: int
    overlap_conflicts: int
    output_mutations: int

    @property
    def cell_fraction(self) -> float:
        return (self.cells / self.full_search_cells * 100.0) if self.full_search_cells else 0.0

    @property
    def recall_vs_sim(self) -> float:
        return pct(self.shared_records, self.sim_records) if self.sim_records else 0.0

    @property
    def precision_vs_sim(self) -> float:
        output_records = self.shared_records + self.extra_vs_sim
        return pct(self.shared_records, output_records) if output_records else 0.0


@dataclasses.dataclass(frozen=True)
class RecoveryRunArtifacts:
    boxes: Tuple[RecoveryBox, ...]
    candidate_raw: frozenset[str]
    accepted_candidate_raw: frozenset[str]
    suppressed_fasim_raw: frozenset[str]
    sim_records: Tuple[TriplexRecord, ...]
    sim_only: Tuple[GapRecord, ...]


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


def _boxes_by_family(boxes: Sequence[RecoveryBox]) -> Dict[Tuple[str, str, str], List[RecoveryBox]]:
    boxes_by_family: Dict[Tuple[str, str, str], List[RecoveryBox]] = {}
    for box in boxes:
        boxes_by_family.setdefault(box.family, []).append(box)
    return boxes_by_family


def _has_canonicalization_mismatch(
    record: TriplexRecord,
    sim_close_records: Sequence[TriplexRecord],
) -> bool:
    return any(
        other.raw != record.raw
        and records_overlap_in_both_axes(record, other)
        and other.nt == record.nt
        and abs(other.score - record.score) <= 0.001
        for other in sim_close_records
    )


def classify_missed_sim_records(
    *,
    sim_records: Sequence[TriplexRecord],
    sim_close_records: Sequence[TriplexRecord],
    boxes: Sequence[RecoveryBox],
    candidate_raw: Set[str],
    accepted_candidate_raw: Set[str],
) -> MissTaxonomy:
    sim_raw = {record.raw for record in sim_records}
    sim_close_raw = {record.raw for record in sim_close_records}
    missed = [record for record in sim_records if record.raw not in sim_close_raw]
    buckets = missed_sim_record_buckets(
        missed_records=missed,
        sim_close_records=sim_close_records,
        boxes=boxes,
        candidate_raw=candidate_raw,
        accepted_candidate_raw=accepted_candidate_raw,
    )

    return MissTaxonomy(
        enabled=True,
        sim_records=len(sim_raw),
        shared_records=len(sim_raw & sim_close_raw),
        missed_records=len(missed),
        not_box_covered=len(buckets["not_box_covered"]),
        box_covered_but_executor_missing=len(buckets["box_covered_but_executor_missing"]),
        guard_rejected=len(buckets["guard_rejected"]),
        replacement_suppressed=len(buckets["replacement_suppressed"]),
        canonicalization_mismatches=len(buckets["canonicalization_mismatches"]),
        metric_ambiguity_records=len(buckets["metric_ambiguity_records"]),
    )


def missed_sim_record_buckets(
    *,
    missed_records: Sequence[TriplexRecord],
    sim_close_records: Sequence[TriplexRecord],
    boxes: Sequence[RecoveryBox],
    candidate_raw: Set[str],
    accepted_candidate_raw: Set[str],
) -> Dict[str, Set[str]]:
    buckets: Dict[str, Set[str]] = {
        "not_box_covered": set(),
        "box_covered_but_executor_missing": set(),
        "guard_rejected": set(),
        "replacement_suppressed": set(),
        "canonicalization_mismatches": set(),
        "metric_ambiguity_records": set(),
    }
    boxes_by_family = _boxes_by_family(boxes)
    sim_close_raw = {record.raw for record in sim_close_records}
    for record in missed_records:
        if _has_canonicalization_mismatch(record, sim_close_records):
            buckets["canonicalization_mismatches"].add(record.raw)
        elif not record_in_any_box(record, boxes_by_family):
            buckets["not_box_covered"].add(record.raw)
        elif record.raw not in candidate_raw:
            buckets["box_covered_but_executor_missing"].add(record.raw)
        elif record.raw not in accepted_candidate_raw:
            buckets["guard_rejected"].add(record.raw)
        elif record.raw not in sim_close_raw:
            buckets["replacement_suppressed"].add(record.raw)
        else:
            buckets["metric_ambiguity_records"].add(record.raw)
    return buckets


def build_miss_taxonomy(
    *,
    enabled: bool,
    validate: bool,
    sim_records: Sequence[TriplexRecord],
    fasim: ModeRun,
    executor_shadow: ExecutorShadow,
    mode: object,
) -> Optional[MissTaxonomy]:
    if not enabled or not validate:
        return None
    candidate_raw = set(executor_shadow.candidate_records_raw)
    candidate_records = parse_lite_records(sorted(candidate_raw))
    accepted_candidate_raw = combined_non_oracle_candidate_raw(
        candidate_records=candidate_records,
        fasim_records=fasim.records,
        boxes=executor_shadow.boxes,
    )
    sim_close_records = parse_lite_records(getattr(mode, "output_raw_records", ()))
    return classify_missed_sim_records(
        sim_records=sim_records,
        sim_close_records=sim_close_records,
        boxes=executor_shadow.boxes,
        candidate_raw=candidate_raw,
        accepted_candidate_raw=accepted_candidate_raw,
    )


def accepted_candidate_raw_for_guard(
    *,
    guard: str,
    candidate_records: Sequence[TriplexRecord],
    fasim_records: Sequence[TriplexRecord],
    boxes: Sequence[RecoveryBox],
    sim_raw: Set[str],
) -> Set[str]:
    if guard == "combined_non_oracle":
        return combined_non_oracle_candidate_raw(
            candidate_records=candidate_records,
            fasim_records=fasim_records,
            boxes=boxes,
        )

    candidate_in_boxes, _ = records_by_box(candidate_records, boxes)
    in_box_records = [record for record in candidate_records if record.raw in candidate_in_boxes]
    if guard == "score_nt_threshold":
        return {record.raw for record in in_box_records if record.score >= 89.0 and record.nt >= 50}
    if guard == "oracle_sim_match":
        return {record.raw for record in in_box_records if record.raw in sim_raw}

    if guard == "local_rank_top3":
        min_score = 89.0
        min_nt = 50
    elif guard == "relaxed_score_nt_rank3":
        min_score = 85.0
        min_nt = 45
    else:
        raise RuntimeError(f"unknown recall repair guard: {guard}")

    threshold_records = [
        record for record in in_box_records if record.score >= min_score and record.nt >= min_nt
    ]
    local_ranks = candidate_local_ranks(threshold_records, boxes)
    dominance_references = list(fasim_records) + list(threshold_records)
    return {
        record.raw
        for record in threshold_records
        if local_ranks.get(record.raw, 0)
        and local_ranks[record.raw] <= 3
        and not dominated_by_higher_score(record, dominance_references)
    }


def evaluate_recall_repair_strategy(
    *,
    strategy: str,
    boxes: Sequence[RecoveryBox],
    full_search_cells: int,
    fasim_records: Sequence[TriplexRecord],
    sim_records: Sequence[TriplexRecord],
    baseline_shared_raw: Set[str],
    baseline_not_box_covered_raw: Set[str],
    baseline_guard_rejected_raw: Set[str],
    candidate_raw: Set[str],
    accepted_candidate_raw: Set[str],
    suppressed_fasim_raw: Set[str],
    output_mutations: int,
    oracle: bool = False,
) -> RecallRepairResult:
    fasim_raw = {record.raw for record in fasim_records}
    sim_raw = {record.raw for record in sim_records}
    integrated_raw = (fasim_raw - suppressed_fasim_raw) | accepted_candidate_raw
    integrated_records = parse_lite_records(sorted(integrated_raw))
    shared_raw = integrated_raw & sim_raw
    missed_records = [record for record in sim_records if record.raw not in integrated_raw]
    taxonomy = classify_missed_sim_records(
        sim_records=sim_records,
        sim_close_records=integrated_records,
        boxes=boxes,
        candidate_raw=candidate_raw,
        accepted_candidate_raw=accepted_candidate_raw,
    )
    newly_shared = shared_raw - baseline_shared_raw
    return RecallRepairResult(
        workload_label="",
        strategy=strategy,
        enabled=True,
        boxes=len(boxes),
        cells=sum(box_cells(box) for box in boxes),
        full_search_cells=full_search_cells,
        sim_records=len(sim_raw),
        shared_records=len(shared_raw),
        missed_records=len(missed_records),
        not_box_covered=taxonomy.not_box_covered,
        guard_rejected=taxonomy.guard_rejected,
        recovered_from_box_expansion=len(newly_shared & baseline_not_box_covered_raw),
        recovered_from_guard_relaxation=len(newly_shared & baseline_guard_rejected_raw),
        extra_vs_sim=len(integrated_raw - sim_raw),
        overlap_conflicts=count_same_family_genomic_overlaps(integrated_records),
        output_mutations=output_mutations,
        oracle=oracle,
    )


def build_recall_repair_shadow(
    *,
    enabled: bool,
    validate: bool,
    label: str,
    bin_path: Path,
    sim_records: Sequence[TriplexRecord],
    fasim: ModeRun,
    base_executor: ExecutorShadow,
    mode: object,
    dna_entries: Sequence[SequenceEntry],
    query_sequence: str,
    full_cells: int,
    work_dir: Path,
    merge_gap_bp: int,
) -> Tuple[RecallRepairResult, ...]:
    if not enabled or not validate:
        return ()

    sim_raw = {record.raw for record in sim_records}
    base_candidate_raw = set(base_executor.candidate_records_raw)
    base_candidate_records = parse_lite_records(sorted(base_candidate_raw))
    base_accepted = combined_non_oracle_candidate_raw(
        candidate_records=base_candidate_records,
        fasim_records=fasim.records,
        boxes=base_executor.boxes,
    )
    base_fasim_in_boxes, _ = records_by_box(fasim.records, base_executor.boxes)
    base_integrated_records = parse_lite_records(getattr(mode, "output_raw_records", ()))
    base_integrated_raw = {record.raw for record in base_integrated_records}
    baseline_shared_raw = base_integrated_raw & sim_raw
    base_missed = [record for record in sim_records if record.raw not in base_integrated_raw]
    base_buckets = missed_sim_record_buckets(
        missed_records=base_missed,
        sim_close_records=base_integrated_records,
        boxes=base_executor.boxes,
        candidate_raw=base_candidate_raw,
        accepted_candidate_raw=base_accepted,
    )

    executor_by_box_variant: Dict[str, ExecutorShadow] = {"current": base_executor}
    for variant, margin in (("margin128", 128), ("margin256", 256)):
        boxes = build_fasim_visible_boxes(
            fasim_records=fasim.records,
            merge_gap_bp=merge_gap_bp,
            margin_bp=margin,
        )
        executor_by_box_variant[variant] = build_external_executor_shadow(
            label=label,
            bin_path=bin_path,
            boxes=boxes,
            dna_entries=dna_entries,
            query_sequence=query_sequence,
            sim_only=(),
            full_cells=full_cells,
            work_dir=work_dir / variant,
        )

    strategy_specs = (
        ("baseline_current", "current", "combined_non_oracle", False),
        ("box_margin_128_current_guard", "margin128", "combined_non_oracle", False),
        ("box_margin_256_current_guard", "margin256", "combined_non_oracle", False),
        ("guard_local_rank_top3", "current", "local_rank_top3", False),
        ("guard_score_nt_threshold", "current", "score_nt_threshold", False),
        ("guard_relaxed_score_nt_rank3", "current", "relaxed_score_nt_rank3", False),
        ("box_margin_128_guard_local_rank_top3", "margin128", "local_rank_top3", False),
        ("box_margin_128_guard_relaxed_score_nt_rank3", "margin128", "relaxed_score_nt_rank3", False),
        ("oracle_upper_bound", "margin256", "oracle_sim_match", True),
    )
    results: List[RecallRepairResult] = []
    for strategy, box_variant, guard, oracle in strategy_specs:
        executor = executor_by_box_variant[box_variant]
        candidate_raw = set(executor.candidate_records_raw)
        candidate_records = parse_lite_records(sorted(candidate_raw))
        fallbacks = executor.executor_failures + executor.unsupported_boxes
        accepted_raw = (
            set()
            if fallbacks
            else accepted_candidate_raw_for_guard(
                guard=guard,
                candidate_records=candidate_records,
                fasim_records=fasim.records,
                boxes=executor.boxes,
                sim_raw=sim_raw,
            )
        )
        suppressed_fasim_raw = set() if fallbacks else records_by_box(fasim.records, executor.boxes)[0]
        result = evaluate_recall_repair_strategy(
            strategy=strategy,
            boxes=executor.boxes,
            full_search_cells=executor.full_search_cells,
            fasim_records=fasim.records,
            sim_records=sim_records,
            baseline_shared_raw=baseline_shared_raw,
            baseline_not_box_covered_raw=base_buckets["not_box_covered"],
            baseline_guard_rejected_raw=base_buckets["guard_rejected"],
            candidate_raw=candidate_raw,
            accepted_candidate_raw=accepted_raw,
            suppressed_fasim_raw=suppressed_fasim_raw,
            output_mutations=0,
            oracle=oracle,
        )
        results.append(dataclasses.replace(result, workload_label=label))
    return tuple(results)


def record_box(
    record: TriplexRecord,
    *,
    margin_bp: int,
    category: str,
) -> RecoveryBox:
    return RecoveryBox(
        family=record.family,
        genome_interval=expand_interval(record.genome_interval, margin_bp),
        query_interval=expand_interval(record.query_interval, margin_bp),
        categories=frozenset([category]),
    )


def overlap_density_boxes(
    *,
    fasim_records: Sequence[TriplexRecord],
    margin_bp: int,
) -> List[RecoveryBox]:
    grouped: Dict[Tuple[str, str, str], List[TriplexRecord]] = defaultdict(list)
    for record in fasim_records:
        grouped[record.family].append(record)

    boxes: List[RecoveryBox] = []
    for family, records in grouped.items():
        ordered = sorted(records, key=lambda record: (record.genome_interval[0], record.genome_interval[1], record.raw))
        cluster: List[TriplexRecord] = []
        cluster_genome: Optional[List[int]] = None
        cluster_query: Optional[List[int]] = None
        for record in ordered:
            genome = record.genome_interval
            query = record.query_interval
            if cluster_genome is None or cluster_query is None:
                cluster = [record]
                cluster_genome = [genome[0], genome[1]]
                cluster_query = [query[0], query[1]]
                continue
            if genome[0] <= cluster_genome[1] + margin_bp or any(
                overlaps(genome, existing.genome_interval) for existing in cluster
            ):
                cluster.append(record)
                cluster_genome[0] = min(cluster_genome[0], genome[0])
                cluster_genome[1] = max(cluster_genome[1], genome[1])
                cluster_query[0] = min(cluster_query[0], query[0])
                cluster_query[1] = max(cluster_query[1], query[1])
                continue
            if len(cluster) >= 2:
                boxes.append(
                    RecoveryBox(
                        family=family,
                        genome_interval=expand_interval(tuple(cluster_genome), margin_bp),
                        query_interval=expand_interval(tuple(cluster_query), margin_bp),
                        categories=frozenset(["overlap_density"]),
                    )
                )
            cluster = [record]
            cluster_genome = [genome[0], genome[1]]
            cluster_query = [query[0], query[1]]
        if cluster_genome is not None and cluster_query is not None and len(cluster) >= 2:
            boxes.append(
                RecoveryBox(
                    family=family,
                    genome_interval=expand_interval(tuple(cluster_genome), margin_bp),
                    query_interval=expand_interval(tuple(cluster_query), margin_bp),
                    categories=frozenset(["overlap_density"]),
                )
            )
    return boxes


def build_score_landscape_boxes(
    *,
    fasim_records: Sequence[TriplexRecord],
    strategy: str,
    merge_gap_bp: int,
    margin_bp: int,
) -> List[RecoveryBox]:
    if strategy == "baseline_current":
        return build_fasim_visible_boxes(
            fasim_records=fasim_records,
            merge_gap_bp=merge_gap_bp,
            margin_bp=margin_bp,
        )

    if not fasim_records:
        return []

    scores = [record.score for record in fasim_records]
    min_score = min(scores)
    near_threshold = [record for record in fasim_records if record.score <= min_score + 5.0]
    long_hits = [record for record in fasim_records if record.nt >= 80]

    raw_boxes: List[RecoveryBox] = []
    if strategy == "score_peak_box_expansion":
        raw_boxes = [
            record_box(record, margin_bp=96, category="score_peak_box_expansion")
            for record in fasim_records
        ]
    elif strategy == "near_threshold_peak_detector":
        raw_boxes = [
            record_box(record, margin_bp=192, category="near_threshold_peak")
            for record in near_threshold
        ]
    elif strategy == "long_hit_internal_peak_detector":
        raw_boxes = [
            record_box(record, margin_bp=192, category="long_hit_internal_peak")
            for record in long_hits
        ]
    elif strategy == "overlap_density_detector":
        raw_boxes = overlap_density_boxes(fasim_records=fasim_records, margin_bp=192)
    elif strategy == "combined_score_landscape_detector":
        raw_boxes = [
            record_box(record, margin_bp=margin_bp, category="fasim_output_record")
            for record in fasim_records
        ]
        raw_boxes.extend(
            record_box(record, margin_bp=96, category="score_peak_box_expansion")
            for record in fasim_records
        )
        raw_boxes.extend(
            record_box(record, margin_bp=192, category="near_threshold_peak")
            for record in near_threshold
        )
        raw_boxes.extend(
            record_box(record, margin_bp=192, category="long_hit_internal_peak")
            for record in long_hits
        )
        raw_boxes.extend(overlap_density_boxes(fasim_records=fasim_records, margin_bp=192))
    else:
        raise RuntimeError(f"unknown score-landscape detector strategy: {strategy}")

    return merge_recovery_boxes(raw_boxes, merge_gap_bp=merge_gap_bp)


def evaluate_score_landscape_strategy(
    *,
    label: str,
    strategy: str,
    boxes: Sequence[RecoveryBox],
    full_search_cells: int,
    fasim_records: Sequence[TriplexRecord],
    sim_records: Sequence[TriplexRecord],
    candidate_raw: Set[str],
    accepted_candidate_raw: Set[str],
    suppressed_fasim_raw: Set[str],
    output_mutations: int,
) -> ScoreLandscapeDetectorResult:
    fasim_raw = {record.raw for record in fasim_records}
    sim_raw = {record.raw for record in sim_records}
    integrated_raw = (fasim_raw - suppressed_fasim_raw) | accepted_candidate_raw
    integrated_records = parse_lite_records(sorted(integrated_raw))
    taxonomy = classify_missed_sim_records(
        sim_records=sim_records,
        sim_close_records=integrated_records,
        boxes=boxes,
        candidate_raw=candidate_raw,
        accepted_candidate_raw=accepted_candidate_raw,
    )
    return ScoreLandscapeDetectorResult(
        workload_label=label,
        strategy=strategy,
        enabled=True,
        boxes=len(boxes),
        cells=sum(box_cells(box) for box in boxes),
        full_search_cells=full_search_cells,
        sim_records=len(sim_raw),
        shared_records=len(integrated_raw & sim_raw),
        missed_records=taxonomy.missed_records,
        not_box_covered=taxonomy.not_box_covered,
        guard_rejected=taxonomy.guard_rejected,
        extra_vs_sim=len(integrated_raw - sim_raw),
        overlap_conflicts=count_same_family_genomic_overlaps(integrated_records),
        output_mutations=output_mutations,
    )


def build_score_landscape_detector_shadow(
    *,
    enabled: bool,
    validate: bool,
    label: str,
    bin_path: Path,
    sim_records: Sequence[TriplexRecord],
    fasim: ModeRun,
    base_executor: ExecutorShadow,
    dna_entries: Sequence[SequenceEntry],
    query_sequence: str,
    full_cells: int,
    work_dir: Path,
    merge_gap_bp: int,
    margin_bp: int,
) -> Tuple[ScoreLandscapeDetectorResult, ...]:
    if not enabled or not validate:
        return ()

    sim_raw = {record.raw for record in sim_records}
    box_strategies = (
        "baseline_current",
        "score_peak_box_expansion",
        "near_threshold_peak_detector",
        "long_hit_internal_peak_detector",
        "overlap_density_detector",
        "combined_score_landscape_detector",
    )
    executor_by_strategy: Dict[str, ExecutorShadow] = {"baseline_current": base_executor}
    for strategy in box_strategies:
        if strategy == "baseline_current":
            continue
        boxes = build_score_landscape_boxes(
            fasim_records=fasim.records,
            strategy=strategy,
            merge_gap_bp=merge_gap_bp,
            margin_bp=margin_bp,
        )
        executor_by_strategy[strategy] = build_external_executor_shadow(
            label=label,
            bin_path=bin_path,
            boxes=boxes,
            dna_entries=dna_entries,
            query_sequence=query_sequence,
            sim_only=(),
            full_cells=full_cells,
            work_dir=work_dir / strategy,
        )

    strategy_specs = (
        ("baseline_current", "baseline_current", "combined_non_oracle"),
        ("score_peak_box_expansion", "score_peak_box_expansion", "combined_non_oracle"),
        ("near_threshold_peak_detector", "near_threshold_peak_detector", "combined_non_oracle"),
        ("long_hit_internal_peak_detector", "long_hit_internal_peak_detector", "combined_non_oracle"),
        ("overlap_density_detector", "overlap_density_detector", "combined_non_oracle"),
        ("combined_score_landscape_detector", "combined_score_landscape_detector", "score_nt_threshold"),
        ("combined_detector_current_guard", "combined_score_landscape_detector", "combined_non_oracle"),
        ("combined_detector_relaxed_guard", "combined_score_landscape_detector", "relaxed_score_nt_rank3"),
    )

    results: List[ScoreLandscapeDetectorResult] = []
    for strategy, box_strategy, guard in strategy_specs:
        executor = executor_by_strategy[box_strategy]
        candidate_raw = set(executor.candidate_records_raw)
        candidate_records = parse_lite_records(sorted(candidate_raw))
        fallbacks = executor.executor_failures + executor.unsupported_boxes
        accepted_raw = (
            set()
            if fallbacks
            else accepted_candidate_raw_for_guard(
                guard=guard,
                candidate_records=candidate_records,
                fasim_records=fasim.records,
                boxes=executor.boxes,
                sim_raw=sim_raw,
            )
        )
        suppressed_fasim_raw = set() if fallbacks else records_by_box(fasim.records, executor.boxes)[0]
        results.append(
            evaluate_score_landscape_strategy(
                label=label,
                strategy=strategy,
                boxes=executor.boxes,
                full_search_cells=executor.full_search_cells,
                fasim_records=fasim.records,
                sim_records=sim_records,
                candidate_raw=candidate_raw,
                accepted_candidate_raw=accepted_raw,
                suppressed_fasim_raw=suppressed_fasim_raw,
                output_mutations=0,
            )
        )
    return tuple(results)


def build_sim_close_mode(
    *,
    bin_path: Path,
    spec: CaseSpec,
    fasim: ModeRun,
    validate: bool,
    miss_taxonomy_enabled: bool,
    recall_repair_enabled: bool,
    score_landscape_detector_enabled: bool,
    work_dir: Path,
    merge_gap_bp: int,
    margin_bp: int,
    near_tie_delta: float,
    threshold_score_band: float,
    long_hit_nt: int,
) -> Tuple[
    object,
    float,
    RecoveryRunArtifacts,
    ValidationCoverage,
    Optional[MissTaxonomy],
    Tuple[RecallRepairResult, ...],
    Tuple[ScoreLandscapeDetectorResult, ...],
]:
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
    candidate_records = parse_lite_records(sorted(executor.candidate_records_raw))
    accepted_candidate_raw = combined_non_oracle_candidate_raw(
        candidate_records=candidate_records,
        fasim_records=fasim.records,
        boxes=executor.boxes,
    )
    fallbacks = executor.executor_failures + executor.unsupported_boxes
    fasim_in_boxes, _ = records_by_box(fasim.records, executor.boxes)
    artifacts = RecoveryRunArtifacts(
        boxes=tuple(executor.boxes),
        candidate_raw=executor.candidate_records_raw,
        accepted_candidate_raw=frozenset() if fallbacks else frozenset(accepted_candidate_raw),
        suppressed_fasim_raw=frozenset() if fallbacks else frozenset(fasim_in_boxes),
        sim_records=tuple(sim.records),
        sim_only=tuple(sim_only),
    )
    write_lite_output(work_dir / "sim_close.lite", mode.output_raw_records)
    coverage = build_validation_coverage(
        requested=validate,
        sim_records=sim.records,
        sim_only=sim_only,
        mode=mode,
    )
    miss_taxonomy = build_miss_taxonomy(
        enabled=miss_taxonomy_enabled,
        validate=validate,
        sim_records=sim.records,
        fasim=fasim,
        executor_shadow=executor,
        mode=mode,
    )
    recall_repair_results = build_recall_repair_shadow(
        enabled=recall_repair_enabled,
        validate=validate,
        label=spec.label,
        bin_path=bin_path,
        sim_records=sim.records,
        fasim=fasim,
        base_executor=executor,
        mode=mode,
        dna_entries=dna_entries,
        query_sequence=query_sequence,
        full_cells=full_cells,
        work_dir=work_dir / "recall_repair",
        merge_gap_bp=merge_gap_bp,
    )
    score_landscape_results = build_score_landscape_detector_shadow(
        enabled=score_landscape_detector_enabled,
        validate=validate,
        label=spec.label,
        bin_path=bin_path,
        sim_records=sim.records,
        fasim=fasim,
        base_executor=executor,
        dna_entries=dna_entries,
        query_sequence=query_sequence,
        full_cells=full_cells,
        work_dir=work_dir / "score_landscape_detector",
        merge_gap_bp=merge_gap_bp,
        margin_bp=margin_bp,
    )
    return (
        mode,
        time.perf_counter() - start,
        artifacts,
        coverage,
        miss_taxonomy,
        recall_repair_results,
        score_landscape_results,
    )




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
    miss_taxonomy_report: bool,
    recall_repair_shadow: bool,
    score_landscape_detector_shadow: bool,
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
        sim_close, sim_close_wall, sim_close_artifacts, sim_close_coverage, _, _, _ = build_sim_close_mode(
            bin_path=bin_path,
            spec=spec,
            fasim=fast,
            validate=False,
            miss_taxonomy_enabled=False,
            recall_repair_enabled=False,
            score_landscape_detector_enabled=False,
            work_dir=run_dir / "sim_close",
            merge_gap_bp=merge_gap_bp,
            margin_bp=margin_bp,
            near_tie_delta=near_tie_delta,
            threshold_score_band=threshold_score_band,
            long_hit_nt=long_hit_nt,
        )
        validate_mode: Optional[object] = None
        validate_wall = 0.0
        validate_artifacts: Optional[RecoveryRunArtifacts] = None
        validation_coverage = sim_close_coverage
        miss_taxonomy: Optional[MissTaxonomy] = None
        recall_repair_results: Tuple[RecallRepairResult, ...] = ()
        score_landscape_results: Tuple[ScoreLandscapeDetectorResult, ...] = ()
        if spec.validate:
            (
                validate_mode,
                validate_wall,
                validate_artifacts,
                validation_coverage,
                miss_taxonomy,
                recall_repair_results,
                score_landscape_results,
            ) = build_sim_close_mode(
                bin_path=bin_path,
                spec=spec,
                fasim=fast,
                validate=True,
                miss_taxonomy_enabled=miss_taxonomy_report,
                recall_repair_enabled=recall_repair_shadow,
                score_landscape_detector_enabled=score_landscape_detector_shadow,
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
                sim_close_artifacts=sim_close_artifacts,
                validate_mode=validate_mode,
                validate_wall_seconds=validate_wall,
                validate_artifacts=validate_artifacts,
                validation_coverage=validation_coverage,
                miss_taxonomy=miss_taxonomy,
                recall_repair_results=recall_repair_results,
                score_landscape_results=score_landscape_results,
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


def total_miss_taxonomy_per_repeat(summaries: Sequence[CaseSummary], repeat: int, attr: str) -> List[float]:
    totals: List[float] = []
    for run_index in range(repeat):
        total = 0.0
        for summary in summaries:
            taxonomy = summary.runs[run_index].miss_taxonomy
            if taxonomy is not None:
                total += float(getattr(taxonomy, attr))
        totals.append(total)
    return totals


def recall_repair_results(summaries: Sequence[CaseSummary]) -> List[RecallRepairResult]:
    return [result for summary in summaries for run in summary.runs for result in run.recall_repair_results]


def score_landscape_results(summaries: Sequence[CaseSummary]) -> List[ScoreLandscapeDetectorResult]:
    return [result for summary in summaries for run in summary.runs for result in run.score_landscape_results]


def best_recall_repair_result(results: Sequence[RecallRepairResult]) -> Optional[RecallRepairResult]:
    non_oracle = [result for result in results if not result.oracle]
    if not non_oracle:
        return None
    return max(
        non_oracle,
        key=lambda result: (
            result.recall_vs_sim,
            result.precision_vs_sim,
            -result.extra_vs_sim,
            -result.cells,
            result.strategy,
        ),
    )


def best_score_landscape_result(
    results: Sequence[ScoreLandscapeDetectorResult],
) -> Optional[ScoreLandscapeDetectorResult]:
    if not results:
        return None
    return max(
        results,
        key=lambda result: (
            result.recall_vs_sim,
            result.precision_vs_sim,
            -result.extra_vs_sim,
            -result.cells,
            result.strategy,
        ),
    )


def validation_matrix(
    summaries: Sequence[CaseSummary],
) -> Tuple[List[List[str]], Dict[str, str]]:
    rows: List[List[str]] = []
    supported_cases = 0
    unsupported_cases = 0
    high_recall_high_precision_cases = 0
    precision_clean_recall_low_cases = 0
    sim_records = 0
    shared_records = 0
    missed_records = 0
    extra_records = 0

    for summary in summaries:
        run = summary.runs[0]
        selected = selected_mode(run)
        coverage = run.validation_coverage
        taxonomy = run.miss_taxonomy
        supported = coverage.supported
        if supported:
            supported_cases += 1
        else:
            unsupported_cases += 1

        recall = mode_value(selected, "recall_vs_sim") if supported else 0.0
        precision = mode_value(selected, "precision_vs_sim") if supported else 0.0
        if supported and recall >= 90.0 and precision >= 90.0:
            high_recall_high_precision_cases += 1
        if supported and precision >= 95.0 and recall < 80.0:
            precision_clean_recall_low_cases += 1

        case_missed = taxonomy.missed_records if taxonomy is not None else max(
            coverage.sim_records - coverage.shared_records, 0
        )
        sim_records += coverage.sim_records
        shared_records += coverage.shared_records
        missed_records += case_missed
        extra_records += coverage.sim_close_extra_records if supported else 0

        rows.append(
            [
                summary.spec.label,
                "yes" if summary.spec.validate else "no",
                "yes" if supported else "no",
                coverage.unsupported_reason,
                run.fast.digest,
                mode_text(run.sim_close, "output_digest"),
                str(coverage.sim_records),
                str(coverage.sim_close_records),
                str(coverage.shared_records),
                str(case_missed),
                fmt_metric(recall) if supported else "NA",
                fmt_metric(precision) if supported else "NA",
                str(coverage.sim_close_extra_records) if supported else "NA",
                str(taxonomy.not_box_covered) if taxonomy is not None else "NA",
                str(taxonomy.guard_rejected) if taxonomy is not None else "NA",
                str(taxonomy.box_covered_but_executor_missing) if taxonomy is not None else "NA",
                str(taxonomy.replacement_suppressed) if taxonomy is not None else "NA",
                str(int(mode_value(selected, "boxes"))),
                str(int(mode_value(selected, "cells"))),
                fmt_metric(mode_cell_fraction(selected)),
                f"{metric_float(run.fast.metrics, 'fasim_total_seconds'):.6f}",
                f"{run.sim_close_wall_seconds:.6f}",
                f"{run.validate_wall_seconds:.6f}" if run.validate_mode is not None else "NA",
            ]
        )

    telemetry = {
        "enabled": "1",
        "cases": str(len(summaries)),
        "validate_supported_cases": str(supported_cases),
        "unsupported_cases": str(unsupported_cases),
        "high_recall_high_precision_cases": str(high_recall_high_precision_cases),
        "precision_clean_recall_low_cases": str(precision_clean_recall_low_cases),
        "sim_records": str(sim_records),
        "shared_records": str(shared_records),
        "missed_records": str(missed_records),
        "extra_records": str(extra_records),
    }
    return rows, telemetry


LEARNED_DETECTOR_DATASET_FIELDS = [
    "workload_label",
    "run_index",
    "candidate_id",
    "source",
    "validate_supported",
    "validate_unsupported_reason",
    "chr",
    "genome_start",
    "genome_end",
    "query_start",
    "query_end",
    "genome_len",
    "query_len",
    "score",
    "tri_score",
    "nt",
    "identity",
    "mean_stability",
    "rule",
    "strand",
    "direction",
    "same_family_overlap_count",
    "nearest_fasim_score_delta",
    "local_rank",
    "box_covered",
    "box_count_covering",
    "box_categories",
    "cell_cost",
    "label_available",
    "label_in_sim",
    "label_sim_only",
    "label_shared_sim_close",
    "label_guard_should_accept",
    "label_miss_stage",
]


def selected_artifacts(run: CaseRun) -> RecoveryRunArtifacts:
    return run.validate_artifacts if run.validate_artifacts is not None else run.sim_close_artifacts


def record_length(interval: Tuple[int, int]) -> int:
    return interval[1] - interval[0] + 1


def covering_recovery_boxes(
    record: TriplexRecord,
    boxes: Sequence[RecoveryBox],
) -> List[RecoveryBox]:
    genome = record.genome_interval
    query = record.query_interval
    return [
        box
        for box in boxes
        if box.family == record.family
        and box.genome_interval[0] <= genome[0]
        and genome[1] <= box.genome_interval[1]
        and box.query_interval[0] <= query[0]
        and query[1] <= box.query_interval[1]
    ]


def same_family_overlap_count(
    record: TriplexRecord,
    fasim_records: Sequence[TriplexRecord],
) -> int:
    return sum(
        1
        for other in fasim_records
        if other.raw != record.raw
        and other.family == record.family
        and overlaps(record.genome_interval, other.genome_interval)
    )


def nearest_fasim_score_delta(
    record: TriplexRecord,
    fasim_records: Sequence[TriplexRecord],
) -> str:
    same_family = [other for other in fasim_records if other.family == record.family]
    if not same_family:
        return "NA"
    return fmt_metric(min(abs(record.score - other.score) for other in same_family))


def learned_detector_label_stage(
    *,
    raw: str,
    validate_supported: bool,
    sim_raw: Set[str],
    sim_close_raw: Set[str],
    miss_stage_by_raw: Dict[str, str],
) -> str:
    if not validate_supported:
        return "unlabeled"
    if raw in miss_stage_by_raw:
        return miss_stage_by_raw[raw]
    if raw in sim_raw and raw in sim_close_raw:
        return "shared"
    if raw not in sim_raw and raw in sim_close_raw:
        return "extra"
    return "negative"


def append_learned_detector_source_rows(
    *,
    rows: List[Dict[str, str]],
    source: str,
    records: Sequence[TriplexRecord],
    summary: CaseSummary,
    run: CaseRun,
    artifacts: RecoveryRunArtifacts,
    local_ranks: Dict[str, int],
    sim_raw: Set[str],
    sim_only_raw: Set[str],
    sim_close_raw: Set[str],
    miss_stage_by_raw: Dict[str, str],
) -> None:
    coverage = run.validation_coverage
    validate_supported = coverage.supported
    label_available = "1" if validate_supported else "0"
    for record in sorted(
        records,
        key=lambda item: (
            item.chr_name,
            item.genome_interval[0],
            item.genome_interval[1],
            item.query_interval[0],
            item.query_interval[1],
            item.raw,
        ),
    ):
        covering_boxes = covering_recovery_boxes(record, artifacts.boxes)
        categories = sorted({category for box in covering_boxes for category in box.categories})
        raw = record.raw
        stage = learned_detector_label_stage(
            raw=raw,
            validate_supported=validate_supported,
            sim_raw=sim_raw,
            sim_close_raw=sim_close_raw,
            miss_stage_by_raw=miss_stage_by_raw,
        )
        rows.append(
            {
                "workload_label": summary.spec.label,
                "run_index": str(run.index),
                "candidate_id": f"{summary.spec.label}_run{run.index}_{len(rows) + 1:06d}",
                "source": source,
                "validate_supported": "1" if validate_supported else "0",
                "validate_unsupported_reason": coverage.unsupported_reason,
                "chr": record.chr_name,
                "genome_start": str(record.genome_interval[0]),
                "genome_end": str(record.genome_interval[1]),
                "query_start": str(record.query_interval[0]),
                "query_end": str(record.query_interval[1]),
                "genome_len": str(record_length(record.genome_interval)),
                "query_len": str(record_length(record.query_interval)),
                "score": fmt_metric(record.score),
                "tri_score": fmt_metric(record.score),
                "nt": str(record.nt),
                "identity": fmt_metric(record.identity),
                "mean_stability": fmt_metric(record.stability),
                "rule": record.rule,
                "strand": record.strand,
                "direction": record.direction,
                "same_family_overlap_count": str(same_family_overlap_count(record, run.fast.records)),
                "nearest_fasim_score_delta": nearest_fasim_score_delta(record, run.fast.records),
                "local_rank": str(local_ranks.get(raw, 0)),
                "box_covered": "1" if covering_boxes else "0",
                "box_count_covering": str(len(covering_boxes)),
                "box_categories": ";".join(categories) if categories else "NA",
                "cell_cost": str(sum(box_cells(box) for box in covering_boxes)),
                "label_available": label_available,
                "label_in_sim": "1" if validate_supported and raw in sim_raw else ("0" if validate_supported else "NA"),
                "label_sim_only": "1" if validate_supported and raw in sim_only_raw else ("0" if validate_supported else "NA"),
                "label_shared_sim_close": (
                    "1" if validate_supported and raw in sim_raw and raw in sim_close_raw else (
                        "0" if validate_supported else "NA"
                    )
                ),
                "label_guard_should_accept": (
                    "1" if validate_supported and raw in sim_raw and raw in artifacts.candidate_raw else (
                        "0" if validate_supported else "NA"
                    )
                ),
                "label_miss_stage": stage,
            }
        )


def learned_detector_dataset_rows(summaries: Sequence[CaseSummary]) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    for summary in summaries:
        for run in summary.runs:
            artifacts = selected_artifacts(run)
            selected = selected_mode(run)
            sim_records = list(artifacts.sim_records)
            sim_raw = {record.raw for record in sim_records}
            sim_only_raw = {gap.record.raw for gap in artifacts.sim_only}
            sim_close_raw = set(getattr(selected, "output_raw_records", ()))
            candidate_records = parse_lite_records(sorted(artifacts.candidate_raw))
            accepted_records = parse_lite_records(sorted(artifacts.accepted_candidate_raw))
            local_ranks = candidate_local_ranks(candidate_records, artifacts.boxes)
            miss_stage_by_raw: Dict[str, str] = {}
            if run.validation_coverage.supported:
                sim_close_records = parse_lite_records(sorted(sim_close_raw))
                missed = [record for record in sim_records if record.raw not in sim_close_raw]
                buckets = missed_sim_record_buckets(
                    missed_records=missed,
                    sim_close_records=sim_close_records,
                    boxes=artifacts.boxes,
                    candidate_raw=set(artifacts.candidate_raw),
                    accepted_candidate_raw=set(artifacts.accepted_candidate_raw),
                )
                for stage, raw_values in buckets.items():
                    for raw in raw_values:
                        miss_stage_by_raw[raw] = stage

            sources = (
                ("fasim_record", run.fast.records),
                ("sim_record", sim_records),
                ("executor_candidate", candidate_records),
                ("accepted_candidate", accepted_records),
            )
            for source, records in sources:
                append_learned_detector_source_rows(
                    rows=rows,
                    source=source,
                    records=records,
                    summary=summary,
                    run=run,
                    artifacts=artifacts,
                    local_ranks=local_ranks,
                    sim_raw=sim_raw,
                    sim_only_raw=sim_only_raw,
                    sim_close_raw=sim_close_raw,
                    miss_stage_by_raw=miss_stage_by_raw,
                )
    return rows


def write_learned_detector_dataset(
    *,
    summaries: Sequence[CaseSummary],
    output_path: Path,
) -> Dict[str, str]:
    rows = learned_detector_dataset_rows(summaries)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=LEARNED_DETECTOR_DATASET_FIELDS, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)

    sources = Counter(row["source"] for row in rows)
    label_stages = Counter(row["label_miss_stage"] for row in rows)
    output_mutations = max(
        (
            int(mode_value(selected_mode(run), "output_mutations_fast_mode"))
            for summary in summaries
            for run in summary.runs
        ),
        default=0,
    )
    return {
        "enabled": "1",
        "rows": str(len(rows)),
        "path": str(output_path),
        "sim_label_columns": "1",
        "output_mutations": str(output_mutations),
        "validate_supported_rows": str(sum(1 for row in rows if row["validate_supported"] == "1")),
        "source_fasim_records": str(sources.get("fasim_record", 0)),
        "source_sim_records": str(sources.get("sim_record", 0)),
        "source_executor_candidates": str(sources.get("executor_candidate", 0)),
        "source_accepted_candidates": str(sources.get("accepted_candidate", 0)),
        "label_shared": str(label_stages.get("shared", 0)),
        "label_extra": str(label_stages.get("extra", 0)),
        "label_unlabeled": str(label_stages.get("unlabeled", 0)),
    }


def empty_learned_detector_dataset_telemetry() -> Dict[str, str]:
    return {
        "enabled": "0",
        "rows": "0",
        "path": "NA",
        "sim_label_columns": "0",
        "output_mutations": "0",
        "validate_supported_rows": "0",
        "source_fasim_records": "0",
        "source_sim_records": "0",
        "source_executor_candidates": "0",
        "source_accepted_candidates": "0",
        "label_shared": "0",
        "label_extra": "0",
        "label_unlabeled": "0",
    }


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
    miss_taxonomy_report: bool,
    recall_repair_shadow: bool,
    validation_matrix_report: bool,
    score_landscape_detector_shadow: bool,
    learned_detector_dataset_report: bool,
    learned_detector_dataset_telemetry: Dict[str, str],
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
            ["miss_taxonomy_report", "yes" if miss_taxonomy_report else "no"],
            ["recall_repair_shadow", "yes" if recall_repair_shadow else "no"],
            ["validation_matrix_report", "yes" if validation_matrix_report else "no"],
            ["score_landscape_detector_shadow", "yes" if score_landscape_detector_shadow else "no"],
            ["learned_detector_dataset_report", "yes" if learned_detector_dataset_report else "no"],
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

    if miss_taxonomy_report:
        miss_rows: List[List[str]] = []
        for summary in summaries:
            for run in summary.runs:
                taxonomy = run.miss_taxonomy
                if taxonomy is None:
                    miss_rows.append(
                        [
                            summary.spec.label,
                            str(run.index),
                            "0",
                            "0",
                            "0",
                            "0",
                            "0",
                            "0",
                            "0",
                            "0",
                            "0",
                            "0",
                            "not_validated",
                        ]
                    )
                    continue
                miss_rows.append(
                    [
                        summary.spec.label,
                        str(run.index),
                        "1" if taxonomy.enabled else "0",
                        str(taxonomy.sim_records),
                        str(taxonomy.shared_records),
                        str(taxonomy.missed_records),
                        str(taxonomy.not_box_covered),
                        str(taxonomy.box_covered_but_executor_missing),
                        str(taxonomy.guard_rejected),
                        str(taxonomy.replacement_suppressed),
                        str(taxonomy.canonicalization_mismatches),
                        str(taxonomy.metric_ambiguity_records),
                        run.validation_coverage.unsupported_reason,
                    ]
                )

        lines.append("## Miss Taxonomy")
        lines.append("")
        append_table(
            lines,
            [
                "Case",
                "Run",
                "Enabled",
                "SIM records",
                "Shared records",
                "Missed records",
                "Not box covered",
                "Box covered executor missing",
                "Guard rejected",
                "Replacement suppressed",
                "Canonicalization mismatches",
                "Metric ambiguity records",
                "validate_unsupported_reason",
            ],
            miss_rows,
        )
        lines.append("")
        lines.append("Metric consistency note:")
        lines.append("")
        lines.append(
            "`SIM-only records` in the coverage tables are legacy SIM records "
            "not matched by the default Fasim fast-mode output. `Missed "
            "records` in this taxonomy are legacy SIM records not matched by "
            "the SIM-close side output. These are different comparisons, so "
            "`shared_records + sim_only_records` is not expected to equal "
            "`sim_records`."
        )
        lines.append("")
        lines.append(
            "SIM labels are used only after SIM-close selection to assign "
            "diagnostic miss buckets. They do not influence risk boxes, local "
            "SIM execution, guard selection, replacement, or output ordering."
        )
        lines.append("")

    matrix_telemetry = {"enabled": "0"}
    if validation_matrix_report:
        matrix_rows, matrix_telemetry = validation_matrix(summaries)
        lines.append("## Validation Matrix")
        lines.append("")
        append_table(
            lines,
            [
                "Case",
                "Validated",
                "Validate supported",
                "validate_unsupported_reason",
                "Fast digest",
                "SIM-close digest",
                "SIM records",
                "SIM-close records",
                "Shared records",
                "Missed records",
                "Recall vs SIM",
                "Precision vs SIM",
                "Extra vs SIM",
                "Not box covered",
                "Guard rejected",
                "Executor missing",
                "Replacement suppressed",
                "Boxes",
                "Cells",
                "Cell fraction",
                "Fast seconds",
                "SIM-close wall seconds",
                "Validate wall seconds",
            ],
            matrix_rows,
        )
        lines.append("")
        lines.append(
            "This matrix is diagnostic-only. It expands the case-level "
            "validation view for the current `FASIM_SIM_RECOVERY=1` "
            "experimental side output, but it adds no recovery logic and does "
            "not change production selection."
        )
        lines.append("")
        lines.append(
            "`precision-clean / recall-low` means precision is at least 95% "
            "while recall is below 80% on a validate-supported case. That "
            "pattern is evidence for more detector work, not a recommendation "
            "to default SIM-close mode."
        )
        lines.append("")

    landscape_results = score_landscape_results(summaries)
    if score_landscape_detector_shadow:
        lines.append("## Score-Landscape Detector Shadow")
        lines.append("")
        landscape_rows: List[List[str]] = []
        for result in landscape_results:
            landscape_rows.append(
                [
                    result.workload_label,
                    result.strategy,
                    str(result.boxes),
                    str(result.cells),
                    fmt_metric(result.cell_fraction),
                    str(result.shared_records),
                    str(result.missed_records),
                    str(result.not_box_covered),
                    str(result.guard_rejected),
                    fmt_metric(result.recall_vs_sim),
                    fmt_metric(result.precision_vs_sim),
                    str(result.extra_vs_sim),
                    str(result.overlap_conflicts),
                    str(result.output_mutations),
                ]
            )
        append_table(
            lines,
            [
                "Case",
                "Strategy",
                "Boxes",
                "Cells",
                "Cell fraction",
                "Shared",
                "Missed",
                "Not box covered",
                "Guard rejected",
                "Recall",
                "Precision",
                "Extra",
                "Conflicts",
                "Output mutations",
            ],
            landscape_rows,
        )
        lines.append("")
        lines.append(
            "This score-landscape/local-max detector shadow is diagnostic-only. "
            "It uses non-oracle Fasim-visible local-max proxies from final "
            "records, score/Nt bands, long-hit records, and overlap-density "
            "clusters. It does not add recovery logic or change production "
            "selection."
        )
        lines.append("")
        lines.append(
            "Current Fasim profile output does not expose column-max coordinates "
            "as a stable production input, so this shadow evaluates deployable "
            "score-landscape proxies before any C++ or output-path change."
        )
        lines.append("")

    if learned_detector_dataset_report:
        lines.append("## Learned Detector Dataset")
        lines.append("")
        append_table(
            lines,
            ["Metric", "Value"],
            [
                [f"fasim_sim_recovery_learned_detector_dataset_{key}", value]
                for key, value in learned_detector_dataset_telemetry.items()
            ],
        )
        lines.append("")
        lines.append(
            "This export is a diagnostic training/evaluation dataset for a "
            "learned SIM-gap risk detector. It records Fasim-visible candidate "
            "features plus post-hoc SIM labels; it does not train a model, "
            "load a model, or change SIM-close production selection."
        )
        lines.append("")
        lines.append(
            "SIM labels are post-hoc training labels only. They must not be "
            "used as runtime detector inputs, recovery-box inputs, guard "
            "inputs, replacement inputs, or output ordering inputs."
        )
        lines.append("")
        lines.append("Do not train or ship a production learned detector from this report.")
        lines.append("")

    repair_results = recall_repair_results(summaries)
    if recall_repair_shadow:
        repair_rows: List[List[str]] = []
        for result in repair_results:
            repair_rows.append(
                [
                    result.workload_label,
                    result.strategy + ("_oracle" if result.oracle else ""),
                    str(result.boxes),
                    str(result.cells),
                    fmt_metric(result.cell_fraction),
                    str(result.shared_records),
                    str(result.missed_records),
                    str(result.not_box_covered),
                    str(result.guard_rejected),
                    str(result.recovered_from_box_expansion),
                    str(result.recovered_from_guard_relaxation),
                    fmt_metric(result.recall_vs_sim),
                    fmt_metric(result.precision_vs_sim),
                    str(result.extra_vs_sim),
                    str(result.overlap_conflicts),
                    str(result.output_mutations),
                ]
            )

        lines.append("## Recall Repair Shadow")
        lines.append("")
        append_table(
            lines,
            [
                "Case",
                "Strategy",
                "Boxes",
                "Cells",
                "Cell fraction",
                "Shared",
                "Missed",
                "Not box covered",
                "Guard rejected",
                "Recovered from box expansion",
                "Recovered from guard relaxation",
                "Recall",
                "Precision",
                "Extra",
                "Conflicts",
                "Output mutations",
            ],
            repair_rows,
        )
        lines.append("")
        lines.append(
            "Recall repair strategies are shadow-only. Non-oracle strategies "
            "vary Fasim-visible box margins and candidate guards. The oracle "
            "upper bound is analysis-only and must not be used for production "
            "selection."
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
    miss_taxonomy_enabled = int(miss_taxonomy_report)
    miss_taxonomy_sim_records = median_float(total_miss_taxonomy_per_repeat(summaries, repeat, "sim_records"))
    miss_taxonomy_shared_records = median_float(total_miss_taxonomy_per_repeat(summaries, repeat, "shared_records"))
    missed_records = median_float(total_miss_taxonomy_per_repeat(summaries, repeat, "missed_records"))
    not_box_covered = median_float(total_miss_taxonomy_per_repeat(summaries, repeat, "not_box_covered"))
    box_covered_executor_missing = median_float(
        total_miss_taxonomy_per_repeat(summaries, repeat, "box_covered_but_executor_missing")
    )
    guard_rejected = median_float(total_miss_taxonomy_per_repeat(summaries, repeat, "guard_rejected"))
    replacement_suppressed = median_float(
        total_miss_taxonomy_per_repeat(summaries, repeat, "replacement_suppressed")
    )
    canonicalization_mismatches = median_float(
        total_miss_taxonomy_per_repeat(summaries, repeat, "canonicalization_mismatches")
    )
    metric_ambiguity_records = median_float(
        total_miss_taxonomy_per_repeat(summaries, repeat, "metric_ambiguity_records")
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

    miss_telemetry = {
        "fasim_sim_recovery_real_corpus_miss_taxonomy_enabled": str(miss_taxonomy_enabled),
        "fasim_sim_recovery_real_corpus_sim_records": fmt_metric(miss_taxonomy_sim_records),
        "fasim_sim_recovery_real_corpus_shared_records": fmt_metric(miss_taxonomy_shared_records),
        "fasim_sim_recovery_real_corpus_missed_records": fmt_metric(missed_records),
        "fasim_sim_recovery_real_corpus_not_box_covered": fmt_metric(not_box_covered),
        "fasim_sim_recovery_real_corpus_box_covered_executor_missing": fmt_metric(
            box_covered_executor_missing
        ),
        "fasim_sim_recovery_real_corpus_guard_rejected": fmt_metric(guard_rejected),
        "fasim_sim_recovery_real_corpus_replacement_suppressed": fmt_metric(
            replacement_suppressed
        ),
        "fasim_sim_recovery_real_corpus_canonicalization_mismatches": fmt_metric(
            canonicalization_mismatches
        ),
        "fasim_sim_recovery_real_corpus_metric_ambiguity_records": fmt_metric(
            metric_ambiguity_records
        ),
    }
    best_repair = best_recall_repair_result(repair_results)
    repair_telemetry = {
        "enabled": "1" if recall_repair_shadow else "0",
        "strategy": best_repair.strategy if best_repair is not None else "NA",
        "boxes": str(best_repair.boxes) if best_repair is not None else "0",
        "cells": str(best_repair.cells) if best_repair is not None else "0",
        "cell_fraction": fmt_metric(best_repair.cell_fraction) if best_repair is not None else fmt_metric(0.0),
        "sim_records": str(best_repair.sim_records) if best_repair is not None else "0",
        "shared_records": str(best_repair.shared_records) if best_repair is not None else "0",
        "missed_records": str(best_repair.missed_records) if best_repair is not None else "0",
        "not_box_covered": str(best_repair.not_box_covered) if best_repair is not None else "0",
        "guard_rejected": str(best_repair.guard_rejected) if best_repair is not None else "0",
        "recovered_from_box_expansion": (
            str(best_repair.recovered_from_box_expansion) if best_repair is not None else "0"
        ),
        "recovered_from_guard_relaxation": (
            str(best_repair.recovered_from_guard_relaxation) if best_repair is not None else "0"
        ),
        "recall_vs_sim": fmt_metric(best_repair.recall_vs_sim) if best_repair is not None else fmt_metric(0.0),
        "precision_vs_sim": (
            fmt_metric(best_repair.precision_vs_sim) if best_repair is not None else fmt_metric(0.0)
        ),
        "extra_vs_sim": str(best_repair.extra_vs_sim) if best_repair is not None else "0",
        "overlap_conflicts": str(best_repair.overlap_conflicts) if best_repair is not None else "0",
        "output_mutations": str(best_repair.output_mutations) if best_repair is not None else "0",
    }
    best_landscape = best_score_landscape_result(landscape_results)
    landscape_telemetry = {
        "enabled": "1" if score_landscape_detector_shadow else "0",
        "strategy": best_landscape.strategy if best_landscape is not None else "NA",
        "boxes": str(best_landscape.boxes) if best_landscape is not None else "0",
        "cells": str(best_landscape.cells) if best_landscape is not None else "0",
        "cell_fraction": (
            fmt_metric(best_landscape.cell_fraction) if best_landscape is not None else fmt_metric(0.0)
        ),
        "sim_records": str(best_landscape.sim_records) if best_landscape is not None else "0",
        "shared_records": str(best_landscape.shared_records) if best_landscape is not None else "0",
        "missed_records": str(best_landscape.missed_records) if best_landscape is not None else "0",
        "not_box_covered": str(best_landscape.not_box_covered) if best_landscape is not None else "0",
        "guard_rejected": str(best_landscape.guard_rejected) if best_landscape is not None else "0",
        "recall_vs_sim": (
            fmt_metric(best_landscape.recall_vs_sim) if best_landscape is not None else fmt_metric(0.0)
        ),
        "precision_vs_sim": (
            fmt_metric(best_landscape.precision_vs_sim) if best_landscape is not None else fmt_metric(0.0)
        ),
        "extra_vs_sim": str(best_landscape.extra_vs_sim) if best_landscape is not None else "0",
        "overlap_conflicts": str(best_landscape.overlap_conflicts) if best_landscape is not None else "0",
        "output_mutations": str(best_landscape.output_mutations) if best_landscape is not None else "0",
    }

    lines.append("## Aggregate")
    lines.append("")
    append_table(
        lines,
        ["Metric", "Value"],
        [[f"fasim_sim_recovery_real_corpus_{key}", value] for key, value in telemetry.items()],
    )
    lines.append("")

    if miss_taxonomy_report:
        lines.append("## Miss Taxonomy Aggregate")
        lines.append("")
        append_table(
            lines,
            ["Metric", "Value"],
            [[key, value] for key, value in miss_telemetry.items()],
        )
        lines.append("")

    if validation_matrix_report:
        lines.append("## Validation Matrix Aggregate")
        lines.append("")
        append_table(
            lines,
            ["Metric", "Value"],
            [[f"fasim_sim_recovery_validation_matrix_{key}", value] for key, value in matrix_telemetry.items()],
        )
        lines.append("")

    if score_landscape_detector_shadow:
        lines.append("## Score-Landscape Detector Best Aggregate")
        lines.append("")
        append_table(
            lines,
            ["Metric", "Value"],
            [
                [f"fasim_sim_recovery_score_landscape_detector_{key}", value]
                for key, value in landscape_telemetry.items()
            ],
        )
        lines.append("")

    if learned_detector_dataset_report:
        lines.append("## Learned Detector Dataset Aggregate")
        lines.append("")
        append_table(
            lines,
            ["Metric", "Value"],
            [
                [f"fasim_sim_recovery_learned_detector_dataset_{key}", value]
                for key, value in learned_detector_dataset_telemetry.items()
            ],
        )
        lines.append("")

    if recall_repair_shadow:
        lines.append("## Recall Repair Best Non-Oracle Aggregate")
        lines.append("")
        append_table(
            lines,
            ["Metric", "Value"],
            [[f"fasim_sim_recovery_recall_repair_{key}", value] for key, value in repair_telemetry.items()],
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
    if validation_matrix_report:
        precision_clean_low = int(matrix_telemetry.get("precision_clean_recall_low_cases", "0"))
        supported_cases = int(matrix_telemetry.get("validate_supported_cases", "0"))
        if precision_clean_low:
            lines.append(
                f"The validation matrix found {precision_clean_low} of "
                f"{supported_cases} validate-supported cases in the "
                "precision-clean / recall-low bucket. Treat that as evidence "
                "that broader real-corpus validation or a new detector input "
                "is needed before any real-mode expansion."
            )
            lines.append("")
            lines.append(
                "If this pattern holds across a broader matrix, the next "
                "algorithmic PR should investigate a score-landscape or "
                "local-max risk detector rather than continuing small "
                "box/guard threshold tweaks."
            )
        else:
            lines.append(
                "The validation matrix did not find a precision-clean / "
                "recall-low case in this supplied set. Broader real-corpus "
                "coverage is still required before recommending SIM-close."
            )
        lines.append("")
    if miss_taxonomy_report and missed_records:
        lines.append(
            "The miss taxonomy attributes the current SIM-close recall gap to "
            f"{int(not_box_covered)} records outside the Fasim-visible recovery "
            f"boxes and {int(guard_rejected)} records rejected by the current "
            "`combined_non_oracle` guard. Executor-missing, replacement-"
            "suppressed, canonicalization-mismatch, and metric-ambiguity "
            f"counts are {int(box_covered_executor_missing)}, "
            f"{int(replacement_suppressed)}, {int(canonicalization_mismatches)}, "
            f"and {int(metric_ambiguity_records)}, respectively."
        )
        lines.append("")
        lines.append(
            "The next algorithmic work should therefore be split between "
            "real-corpus risk detector or box expansion for the uncovered "
            "records, and real-corpus guard refinement for covered executor "
            "candidates. This PR does not make those changes."
        )
        lines.append("")
    if score_landscape_detector_shadow and best_landscape is not None:
        lines.append(
            "The best non-oracle score-landscape/local-max detector shadow "
            f"strategy is `{best_landscape.strategy}` with recall "
            f"{best_landscape.recall_vs_sim:.2f}%, precision "
            f"{best_landscape.precision_vs_sim:.2f}%, extra records "
            f"{best_landscape.extra_vs_sim}, and cell fraction "
            f"{best_landscape.cell_fraction:.6f}%. This is diagnostic evidence "
            "only; it does not change SIM-close real output."
        )
        lines.append("")
        if missed_records == 0:
            lines.append(
                "The supplied validate-supported cases have no SIM-close "
                "missed records, so this score-landscape sweep is a smoke "
                "check rather than evidence that the detector clears the "
                "real-corpus recall-repair threshold."
            )
        elif (
            best_landscape.recall_vs_sim >= 70.0
            and best_landscape.precision_vs_sim >= 90.0
            and best_landscape.cell_fraction < 1.0
        ):
            lines.append(
                "This detector shadow clears the strong real-corpus tradeoff "
                "threshold for a follow-up detector/guard design update. It "
                "still does not justify defaulting or recommending SIM-close."
            )
        elif best_landscape.recall_vs_sim > recall_median:
            lines.append(
                "The detector shadow improves recall but does not clear the "
                "strong tradeoff threshold. Continue detector analysis before "
                "any real-mode update."
            )
        else:
            lines.append(
                "The detector shadow does not materially improve recall. Keep "
                "SIM-close experimental/research-only and avoid broadening "
                "real-mode behavior from this evidence."
            )
        lines.append("")
    if recall_repair_shadow and best_repair is not None:
        lines.append(
            "The best non-oracle recall-repair shadow strategy is "
            f"`{best_repair.strategy}` with recall {best_repair.recall_vs_sim:.2f}%, "
            f"precision {best_repair.precision_vs_sim:.2f}%, extra records "
            f"{best_repair.extra_vs_sim}, and cell fraction {best_repair.cell_fraction:.6f}%. "
            "This is diagnostic evidence only; it does not change SIM-close "
            "real output."
        )
        lines.append("")
        if (
            best_repair.recall_vs_sim > recall_median
            and best_repair.recall_vs_sim >= 70.0
            and best_repair.precision_vs_sim >= 85.0
        ):
            lines.append(
                "The repair shadow shows a stronger recall/precision tradeoff "
                "than the current conservative real-corpus checkpoint. The "
                "next PR should turn the winning detector or guard change into "
                "a separate shadow/design step, not default SIM-close mode."
            )
        elif best_repair.recall_vs_sim > recall_median:
            lines.append(
                "The repair shadow improves recall but does not yet clear the "
                "strong tradeoff threshold. Keep SIM-close experimental and "
                "continue detector/guard analysis before any real-mode update."
            )
        else:
            lines.append(
                "The repair shadow does not materially improve recall. Keep "
                "SIM-close experimental and avoid broadening real-mode behavior."
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
            taxonomy = run.miss_taxonomy
            if taxonomy is not None:
                print(f"{prefix}.miss_taxonomy_enabled={1 if taxonomy.enabled else 0}")
                print(f"{prefix}.miss_taxonomy_sim_records={taxonomy.sim_records}")
                print(f"{prefix}.miss_taxonomy_shared_records={taxonomy.shared_records}")
                print(f"{prefix}.missed_records={taxonomy.missed_records}")
                print(f"{prefix}.not_box_covered={taxonomy.not_box_covered}")
                print(f"{prefix}.box_covered_executor_missing={taxonomy.box_covered_but_executor_missing}")
                print(f"{prefix}.guard_rejected={taxonomy.guard_rejected}")
                print(f"{prefix}.replacement_suppressed={taxonomy.replacement_suppressed}")
                print(f"{prefix}.canonicalization_mismatches={taxonomy.canonicalization_mismatches}")
                print(f"{prefix}.metric_ambiguity_records={taxonomy.metric_ambiguity_records}")
            for result in run.recall_repair_results:
                repair_prefix = (
                    f"benchmark.fasim_sim_recovery_recall_repair."
                    f"{summary.spec.label}.{result.strategy}"
                )
                print(f"{repair_prefix}.enabled={1 if result.enabled else 0}")
                print(f"{repair_prefix}.oracle={1 if result.oracle else 0}")
                print(f"{repair_prefix}.boxes={result.boxes}")
                print(f"{repair_prefix}.cells={result.cells}")
                print(f"{repair_prefix}.cell_fraction={result.cell_fraction:.6f}")
                print(f"{repair_prefix}.sim_records={result.sim_records}")
                print(f"{repair_prefix}.shared_records={result.shared_records}")
                print(f"{repair_prefix}.missed_records={result.missed_records}")
                print(f"{repair_prefix}.not_box_covered={result.not_box_covered}")
                print(f"{repair_prefix}.guard_rejected={result.guard_rejected}")
                print(f"{repair_prefix}.recovered_from_box_expansion={result.recovered_from_box_expansion}")
                print(f"{repair_prefix}.recovered_from_guard_relaxation={result.recovered_from_guard_relaxation}")
                print(f"{repair_prefix}.recall_vs_sim={result.recall_vs_sim:.6f}")
                print(f"{repair_prefix}.precision_vs_sim={result.precision_vs_sim:.6f}")
                print(f"{repair_prefix}.extra_vs_sim={result.extra_vs_sim}")
                print(f"{repair_prefix}.overlap_conflicts={result.overlap_conflicts}")
                print(f"{repair_prefix}.output_mutations={result.output_mutations}")
            for result in run.score_landscape_results:
                landscape_prefix = (
                    f"benchmark.fasim_sim_recovery_score_landscape_detector."
                    f"{summary.spec.label}.{result.strategy}"
                )
                print(f"{landscape_prefix}.enabled={1 if result.enabled else 0}")
                print(f"{landscape_prefix}.boxes={result.boxes}")
                print(f"{landscape_prefix}.cells={result.cells}")
                print(f"{landscape_prefix}.cell_fraction={result.cell_fraction:.6f}")
                print(f"{landscape_prefix}.sim_records={result.sim_records}")
                print(f"{landscape_prefix}.shared_records={result.shared_records}")
                print(f"{landscape_prefix}.missed_records={result.missed_records}")
                print(f"{landscape_prefix}.not_box_covered={result.not_box_covered}")
                print(f"{landscape_prefix}.guard_rejected={result.guard_rejected}")
                print(f"{landscape_prefix}.recall_vs_sim={result.recall_vs_sim:.6f}")
                print(f"{landscape_prefix}.precision_vs_sim={result.precision_vs_sim:.6f}")
                print(f"{landscape_prefix}.extra_vs_sim={result.extra_vs_sim}")
                print(f"{landscape_prefix}.overlap_conflicts={result.overlap_conflicts}")
                print(f"{landscape_prefix}.output_mutations={result.output_mutations}")

    for key, value in telemetry.items():
        print(f"benchmark.fasim_sim_recovery_real_corpus.total.{key}={value}")
    if miss_taxonomy_report:
        for key, value in miss_telemetry.items():
            print(f"benchmark.{key}={value}")
    if validation_matrix_report:
        for key, value in matrix_telemetry.items():
            print(f"benchmark.fasim_sim_recovery_validation_matrix.{key}={value}")
    if score_landscape_detector_shadow:
        for key, value in landscape_telemetry.items():
            print(f"benchmark.fasim_sim_recovery_score_landscape_detector.total.{key}={value}")
    if learned_detector_dataset_report:
        for key, value in learned_detector_dataset_telemetry.items():
            print(f"benchmark.fasim_sim_recovery_learned_detector_dataset.total.{key}={value}")
    if recall_repair_shadow:
        for key, value in repair_telemetry.items():
            print(f"benchmark.fasim_sim_recovery_recall_repair.total.{key}={value}")

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
    parser.add_argument("--miss-taxonomy-report", action="store_true")
    parser.add_argument("--recall-repair-shadow", action="store_true")
    parser.add_argument("--validation-matrix-report", action="store_true")
    parser.add_argument("--score-landscape-detector-shadow", action="store_true")
    parser.add_argument("--learned-detector-dataset", default="")
    parser.add_argument("--learned-detector-dataset-report", action="store_true")
    args = parser.parse_args()

    try:
        bin_path = Path(args.bin)
        if not bin_path.is_absolute():
            bin_path = (ROOT / bin_path).resolve()
        if not bin_path.exists():
            raise RuntimeError(f"missing Fasim binary: {bin_path}")

        recall_repair_shadow = (
            args.recall_repair_shadow
            or os.environ.get("FASIM_SIM_RECOVERY_RECALL_REPAIR_SHADOW", "0") == "1"
        )
        validation_matrix_report = (
            args.validation_matrix_report
            or os.environ.get("FASIM_SIM_RECOVERY_VALIDATION_MATRIX", "0") == "1"
        )
        score_landscape_detector_shadow = (
            args.score_landscape_detector_shadow
            or os.environ.get("FASIM_SIM_RECOVERY_SCORE_LANDSCAPE_DETECTOR_SHADOW", "0") == "1"
        )
        learned_detector_dataset_report = (
            args.learned_detector_dataset_report
            or os.environ.get("FASIM_SIM_RECOVERY_LEARNED_DETECTOR_DATASET", "0") == "1"
            or bool(args.learned_detector_dataset)
        )
        validate_labels = parse_validate_labels([*args.validate_case, *args.validate_cases])
        if (recall_repair_shadow or score_landscape_detector_shadow) and not validate_labels and args.case:
            validate_labels = {ensure_label(raw[0]) for raw in args.case}
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
                miss_taxonomy_report=(
                    args.miss_taxonomy_report
                    or recall_repair_shadow
                    or validation_matrix_report
                    or score_landscape_detector_shadow
                ),
                recall_repair_shadow=recall_repair_shadow,
                score_landscape_detector_shadow=score_landscape_detector_shadow,
            )
            for case in cases
        ]
        learned_detector_dataset_telemetry = empty_learned_detector_dataset_telemetry()
        if learned_detector_dataset_report:
            dataset_path = (
                Path(args.learned_detector_dataset).resolve()
                if args.learned_detector_dataset
                else work_dir / "learned_detector_dataset.tsv"
            )
            learned_detector_dataset_telemetry = write_learned_detector_dataset(
                summaries=summaries,
                output_path=dataset_path,
            )
        report, _ = render_report(
            summaries=summaries,
            repeat=repeat,
            output_path=Path(args.output),
            title=args.report_title,
            base_branch=args.base_branch,
            coverage_report=(
                args.validation_coverage_report
                or recall_repair_shadow
                or validation_matrix_report
                or score_landscape_detector_shadow
            ),
            miss_taxonomy_report=(
                args.miss_taxonomy_report
                or recall_repair_shadow
                or validation_matrix_report
                or score_landscape_detector_shadow
            ),
            recall_repair_shadow=recall_repair_shadow,
            validation_matrix_report=validation_matrix_report,
            score_landscape_detector_shadow=score_landscape_detector_shadow,
            learned_detector_dataset_report=learned_detector_dataset_report,
            learned_detector_dataset_telemetry=learned_detector_dataset_telemetry,
        )
        print(report)
        return 0
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
