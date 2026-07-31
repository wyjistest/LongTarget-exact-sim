#!/usr/bin/env python3
"""Freeze the successor Phase 5 independent experimental benchmark."""

from __future__ import annotations

import argparse
import bisect
import csv
import gzip
import hashlib
import io
import json
import math
import subprocess
import sys
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[2]
PAPER = ROOT / "paper/biological_topk_successor"
ARTIFACT_ROOT = ROOT / ".paper-artifacts/biological-topk-successor/experimental-phase5"
SOURCE = ARTIFACT_ROOT / "source"
TOOLS = ARTIFACT_ROOT / "tools"
INPUT_ROOT = ARTIFACT_ROOT / "frozen-inputs"
LABEL_SITE = TOOLS / "label-venv/lib/python3.11/site-packages"
if LABEL_SITE.is_dir():
    sys.path.insert(0, str(LABEL_SITE))

import numpy as np  # noqa: E402
import pyBigWig  # type: ignore[import-not-found]  # noqa: E402
from pyliftover import LiftOver  # type: ignore[import-not-found]  # noqa: E402


PHASE4_COMMIT = "59f2445b1deb980d5e4c2f25cda916206158d81a"
WINDOW_LENGTH = 4097
SEPARATOR_LENGTH = 4097
POSITIVE_COUNT = 100
NEGATIVES_PER_POSITIVE = 9
REGIONS_PER_DATASET = 1000
GC_TOLERANCE = 0.05
LINC_SIGNAL_THRESHOLD = 8.0
LINC_FEASIBILITY_COUNTS = {"4": 3324, "8": 830}
POSITIVE_SELECTION_SEED = "biological_topk_successor_phase5_positive_v1_20260730"
NEGATIVE_SELECTION_SEED = "biological_topk_successor_phase5_negative_v1_20260730"
REGION_ID_SEED = "biological_topk_successor_phase5_region_id_v1"
SIMULATION_SEED = 20260815
BOOTSTRAP_SEED = 20260816
SIMULATION_REPLICATES = 10_000
BOOTSTRAP_REPLICATES = 10_000
SELECTION_TIMESTAMP = "2026-07-30"

GENCODE = SOURCE / "gencode.v49.lncRNA_transcripts.fa.gz"
SRA_FASTA = SOURCE / "NR_045587.1.fa"
BLACKLIST = SOURCE / "hg38-blacklist.v2.bed.gz"
HG18_CHAIN = SOURCE / "hg18ToHg38.over.chain.gz"
HG19_CHAIN = SOURCE / "hg19ToHg38.over.chain.gz"
GENOME_ROOT = SOURCE / "grch38-primary"
AUTHORITY_BINARY = ROOT / ".paper-artifacts/bioinformatics-canonical-hybrid-v2/runtime-epoch1/fasim_longtarget_x86"
CANDIDATE_BINARY = ROOT / ".paper-artifacts/bioinformatics-canonical-hybrid-v2/runtime-epoch1/fasim_longtarget_gasal2"
EXTERNAL_BINARY = TOOLS / "triplexator-v1.3.3/triplexator"
EXTERNAL_LICENSE = TOOLS / "triplexator-v1.3.3/LICENCE.txt"
RUNTIME_RECEIPT = ROOT / "paper/bioinformatics/canonical_hybrid_v2_runtime.json"
RUNNER = ROOT / "reproduce/biological_topk_successor/run_phase6.py"
ANALYZER = ROOT / "reproduce/biological_topk_successor/analyze_phase6.py"

DEVELOPMENT_REGISTRY = PAPER / "experimental_development_registry.tsv"
EVALUATION_INVENTORY = PAPER / "experimental_evaluation_inventory.tsv"
SOURCE_RECEIPT = PAPER / "experimental_source_receipt.json"
TOOL_RECEIPT = PAPER / "experimental_tool_receipt.json"
POWER_SIMULATION = PAPER / "experimental_power_simulation.json"
INFORMATION_DECISION = PAPER / "experimental_information_decision.json"
BENCHMARK_SPEC = PAPER / "experimental_benchmark_spec.md"
BENCHMARK_PLAN = PAPER / "experimental_benchmark_plan.json"
BENCHMARK_MANIFEST = PAPER / "experimental_benchmark_manifest.tsv"
ATTEMPT_PLAN = PAPER / "experimental_attempt_plan.tsv"
MANIFEST_CHECKSUM = PAPER / "experimental_manifest.sha256"
RUNTIME_INPUT_RECEIPT = PAPER / "experimental_runtime_input_receipt.json"

PRIMARY_CHROMOSOMES = tuple([f"chr{index}" for index in range(1, 23)] + ["chrX", "chrY"])
EXPECTED_QUERY_DIGESTS = {
    "bte_linc01116_gse227804": "23c48f8f8bef148c82bc320cc18570a589c0e6a4e0fb1b44377142857b846256",
    "bte_hotair_gse31332": "e1629df5c735a8db3a9b46d21feb31d4f35ff7146adc1be0c69cd1146b1de78d",
    "bte_pcgem1_gse47804": "5aae51c88337d8e1b8a3dc2996346345096763279ca6d39202ab41c130bf152b",
    "bte_sra_gse58641": "7d3274f4c9fa0340e7c6dfbfb9dfc57a5fbb89ad2274cc0f0358b3aa717710b5",
    "bte_hottip_gse114981": "e12c29b7091e0eadcb0f9b24598f1d002da54e445ff5bfa71120ff67c8a8ec33",
}


class FreezeError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise FreezeError(message)


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    require(path.is_file() and not path.is_symlink(), f"missing or unsafe file: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False) + "\n").encode("ascii")


def canonical_digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")
    ).hexdigest()


def tsv_bytes(fields: Sequence[str], rows: Iterable[Mapping[str, Any]]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fields, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({field: row[field] for field in fields})
    return output.getvalue().encode("utf-8")


def fasta_bytes(identifier: str, sequence: str) -> bytes:
    lines = [f">{identifier}"]
    lines.extend(sequence[index : index + 80] for index in range(0, len(sequence), 80))
    return ("\n".join(lines) + "\n").encode("ascii")


def multi_fasta_bytes(records: Sequence[tuple[str, str]]) -> bytes:
    return b"".join(fasta_bytes(identifier, sequence) for identifier, sequence in records)


def fasta_records(path: Path) -> Iterable[tuple[str, str]]:
    require(path.is_file() and not path.is_symlink(), f"missing or unsafe FASTA: {path}")
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="ascii") as handle:
        header: str | None = None
        chunks: list[str] = []
        for raw in handle:
            line = raw.rstrip("\r\n")
            if line.startswith(">"):
                if header is not None:
                    yield header, "".join(chunks).upper().replace("U", "T")
                header = line[1:]
                chunks = []
            elif line:
                require(header is not None and line == line.strip(), f"malformed FASTA: {path}")
                chunks.append(line)
        if header is not None:
            yield header, "".join(chunks).upper().replace("U", "T")


def read_chromosome(chromosome: str) -> str:
    path = GENOME_ROOT / f"{chromosome}.fa.gz"
    records = list(fasta_records(path))
    require(len(records) == 1 and records[0][0].split()[0] == chromosome, f"chromosome FASTA drift: {path}")
    sequence = records[0][1]
    require(not (set(sequence) - set("ACGTN")), f"chromosome alphabet drift: {chromosome}")
    return sequence


def gc_fraction(sequence: str) -> float:
    require(sequence and "N" not in sequence, "GC requested for invalid sequence")
    return (sequence.count("G") + sequence.count("C")) / len(sequence)


def sequence_digest(sequence: str) -> str:
    return hashlib.sha256(sequence.encode("ascii")).hexdigest()


@dataclass(frozen=True)
class Dataset:
    dataset_id: str
    outer_lncRNA_id: str
    lncRNA: str
    accession: str
    sample_accession: str
    publication: str
    publication_id: str
    source_build: str
    query_transcript: str
    query_source: str
    query_construction: str
    query_rationale: str
    peak_path: str | None
    peak_url: str | None
    positive_rule: str


DATASETS = (
    Dataset(
        "bte_linc01116_gse227804",
        "lncrna_linc01116",
        "LINC01116/HOXDeRNA",
        "GSE227804",
        "GSM7108396,GSM7108397,GSM7108406,GSM7108411",
        "HOXDeRNA activates a cancerous transcription program and super-enhancers via genome-wide binding",
        "PMID:39383879",
        "hg19",
        "ENST00000295549.9",
        "gencode_v49",
        "complete_frozen_annotation_isoform",
        "GENCODE LINC01116-201 is a complete in-envelope transcript fixed before prediction for the assay gene HOXDeRNA",
        None,
        None,
        "fixed 4097-bp hg19 bins; both library-size-normalized ChIRP replicates >=8x each normalized Input and LacZ control; strongest 100 eligible bins",
    ),
    Dataset(
        "bte_hotair_gse31332",
        "lncrna_hotair",
        "HOTAIR",
        "GSE31332",
        "GSE31332_hotair_oe",
        "Genomic maps of long noncoding RNA occupancy reveal principles of RNA-chromatin interactions",
        "PMID:21963238",
        "hg18",
        "ENST00000424518.6",
        "gencode_v49",
        "complete_frozen_annotation_isoform",
        "GENCODE HOTAIR-201 is the complete in-envelope 2.4-kb transcript corresponding to the approximately 2.2-kb assayed RNA",
        "GSE31332_hotair_oe_peaks.bed.gz",
        "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE31nnn/GSE31332/suppl/GSE31332_hotair_oe_peaks.bed.gz",
        "author HOTAIR ChIRP peaks; deterministic input-only hash ranking after hg18 center liftOver",
    ),
    Dataset(
        "bte_pcgem1_gse47804",
        "lncrna_pcgem1",
        "PCGEM1",
        "GSE47804",
        "GSM1159894",
        "lncRNA-dependent mechanisms of androgen-receptor-regulated gene activation programs",
        "PMID:23945587",
        "hg18",
        "ENST00000606314.2",
        "gencode_v49",
        "complete_frozen_annotation_isoform",
        "longest complete GENCODE PCGEM1 transcript within the operating envelope; publication used full-length probes",
        "GSM1159894_PCGEM1_plusDHT_hs17l4_4.HOMERpeaks.txt.gz",
        "https://ftp.ncbi.nlm.nih.gov/geo/samples/GSM1159nnn/GSM1159894/suppl/GSM1159894_PCGEM1_plusDHT_hs17l4_4.HOMERpeaks.txt.gz",
        "author plus-DHT PCGEM1 ChIRP HOMER peaks; deterministic input-only hash ranking after hg18 center liftOver",
    ),
    Dataset(
        "bte_sra_gse58641",
        "lncrna_sra",
        "SRA",
        "GSE58641",
        "GSM1415922",
        "Association of the Long Non-coding RNA Steroid Receptor RNA Activator (SRA) with TrxG and PRC2 Complexes",
        "PMID:26496121",
        "hg19",
        "NR_045587.1",
        "ncbi_refseq",
        "complete_assay_linked_refseq_isoform",
        "publication states that ChIRP probes cover positions 124-1473 of NR_045587.1; the complete 1473-nt RefSeq query is in envelope",
        "GSM1415922_NTERA2_SRA.bed.gz",
        "https://ftp.ncbi.nlm.nih.gov/geo/samples/GSM1415nnn/GSM1415922/suppl/GSM1415922_NTERA2_SRA.bed.gz",
        "author SRA ChIRP peaks after triplicate intersection and LacZ subtraction; deterministic input-only hash ranking after hg19 center liftOver",
    ),
    Dataset(
        "bte_hottip_gse114981",
        "lncrna_hottip",
        "HOTTIP",
        "GSE114981",
        "GSM3161929",
        "HOTTIP lncRNA Promotes Hematopoietic Stem Cell Self-Renewal Leading to AML-like Disease in Mice",
        "PMID:31786140",
        "hg19",
        "ENST00000472494.2",
        "gencode_v49",
        "complete_frozen_annotation_isoform",
        "longest complete GENCODE HOTTIP transcript within the operating envelope after excluding the 3343-nt out-of-envelope isoform",
        "GSM3161929_WT-CHIRP-seq_peaks.bed.gz",
        "https://ftp.ncbi.nlm.nih.gov/geo/samples/GSM3161nnn/GSM3161929/suppl/GSM3161929_WT-CHIRP-seq_peaks.bed.gz",
        "author wild-type HOTTIP ChIRP MACS peaks; deterministic input-only hash ranking after hg19 center liftOver",
    ),
)
DATASET_BY_ID = {dataset.dataset_id: dataset for dataset in DATASETS}


@dataclass(frozen=True)
class Candidate:
    dataset_id: str
    source_row: int
    source_chromosome: str
    source_start0: int
    source_end0: int
    source_build: str
    target_chromosome: str
    target_start0: int
    target_end0: int
    lift_strand: str
    lift_score: int
    signal_strength: float | None
    selection_key: str
    gc: float | None = None
    digest: str | None = None


class IntervalIndex:
    def __init__(self, intervals: Iterable[tuple[int, int]]) -> None:
        merged: list[list[int]] = []
        for start, end in sorted(intervals):
            if not merged or start > merged[-1][1]:
                merged.append([start, end])
            else:
                merged[-1][1] = max(merged[-1][1], end)
        self.intervals = tuple((start, end) for start, end in merged)
        self.starts = tuple(start for start, _ in self.intervals)

    def overlaps(self, start: int, end: int) -> bool:
        index = bisect.bisect_left(self.starts, end) - 1
        return index >= 0 and self.intervals[index][1] > start


def blacklist_indexes() -> dict[str, IntervalIndex]:
    rows: dict[str, list[tuple[int, int]]] = {chromosome: [] for chromosome in PRIMARY_CHROMOSOMES}
    with gzip.open(BLACKLIST, "rt", encoding="ascii") as handle:
        for raw in handle:
            fields = raw.rstrip("\n").split("\t")
            require(len(fields) >= 3, "blacklist row malformed")
            if fields[0] in rows:
                rows[fields[0]].append((int(fields[1]), int(fields[2])))
    return {chromosome: IntervalIndex(intervals) for chromosome, intervals in rows.items()}


def query_sequences() -> dict[str, str]:
    transcript_to_dataset = {
        dataset.query_transcript: dataset.dataset_id
        for dataset in DATASETS
        if dataset.query_source == "gencode_v49"
    }
    sequences: dict[str, str] = {}
    for header, sequence in fasta_records(GENCODE):
        transcript = header.split("|", 1)[0]
        if transcript in transcript_to_dataset:
            dataset_id = transcript_to_dataset[transcript]
            require(dataset_id not in sequences, f"duplicate selected query transcript: {transcript}")
            sequences[dataset_id] = sequence
    sra_records = list(fasta_records(SRA_FASTA))
    require(len(sra_records) == 1 and sra_records[0][0].startswith("NR_045587.1 "), "SRA RefSeq identity drift")
    sequences["bte_sra_gse58641"] = sra_records[0][1]
    require(set(sequences) == set(DATASET_BY_ID), "selected query sequence missing")
    for dataset_id, sequence in sequences.items():
        require(500 <= len(sequence) <= 2812, f"query outside operating envelope: {dataset_id}")
        require(not (set(sequence) - set("ACGT")), f"query alphabet drift: {dataset_id}")
        require(sequence_digest(sequence) == EXPECTED_QUERY_DIGESTS[dataset_id], f"query digest drift: {dataset_id}")
    return sequences


def peak_rows(path: Path) -> list[tuple[str, int, int]]:
    rows: list[tuple[str, int, int]] = []
    with gzip.open(path, "rt", encoding="ascii") as handle:
        for raw in handle:
            if not raw.strip() or raw.startswith(("#", "track", "browser")):
                continue
            fields = raw.rstrip("\n").split("\t")
            require(len(fields) >= 3, f"malformed peak row: {path}")
            try:
                start, end = int(fields[1]), int(fields[2])
            except ValueError:
                continue
            require(start >= 0 and end > start, f"invalid peak interval: {path}")
            rows.append((fields[0], start, end))
    return rows


def unique_lift(lo: LiftOver, chromosome: str, coordinate: int) -> tuple[str, int, str, int] | None:
    converted = [
        (str(row[0]), int(row[1]), str(row[2]), int(row[3]))
        for row in lo.convert_coordinate(chromosome, coordinate)
        if str(row[0]) in PRIMARY_CHROMOSOMES
    ]
    identities = {(row[0], row[1], row[2]) for row in converted}
    if len(identities) != 1:
        return None
    return max(converted, key=lambda row: row[3])


def candidate_from_source(
    dataset: Dataset,
    source_row: int,
    chromosome: str,
    start: int,
    end: int,
    lo: LiftOver,
    signal_strength: float | None = None,
) -> Candidate | None:
    if chromosome not in PRIMARY_CHROMOSOMES:
        return None
    center = start + (end - start - 1) // 2
    lifted = unique_lift(lo, chromosome, center)
    if lifted is None:
        return None
    target_chromosome, target_center, strand, score = lifted
    target_start = target_center - WINDOW_LENGTH // 2
    target_end = target_start + WINDOW_LENGTH
    key = hashlib.sha256(
        f"{POSITIVE_SELECTION_SEED}|{dataset.dataset_id}|{source_row}|{chromosome}|{start}|{end}".encode("ascii")
    ).hexdigest()
    return Candidate(
        dataset.dataset_id,
        source_row,
        chromosome,
        start,
        end,
        dataset.source_build,
        target_chromosome,
        target_start,
        target_end,
        strand,
        score,
        signal_strength,
        key,
    )


def integrated_fixed_bins(
    intervals: Iterable[tuple[int, int, float]],
    chromosome_length: int,
) -> np.ndarray:
    require(chromosome_length > 0, "LINC BigWig chromosome length is invalid")
    bin_count = math.ceil(chromosome_length / WINDOW_LENGTH)
    values = np.zeros(bin_count, dtype=np.float64)
    for start, end, value in intervals:
        require(0 <= start < end <= chromosome_length, "LINC BigWig interval is out of bounds")
        if not value:
            continue
        first_bin = start // WINDOW_LENGTH
        last_bin = (end - 1) // WINDOW_LENGTH
        if first_bin == last_bin:
            values[first_bin] += (end - start) * value
            continue
        values[first_bin] += (WINDOW_LENGTH - (start % WINDOW_LENGTH)) * value
        if last_bin > first_bin + 1:
            values[first_bin + 1 : last_bin] += WINDOW_LENGTH * value
        values[last_bin] += (end - last_bin * WINDOW_LENGTH) * value
    values /= WINDOW_LENGTH
    return values


def linc_signal_candidates(lo: LiftOver) -> tuple[list[Candidate], dict[str, Any]]:
    names = (
        "GSM7108396_ChIRP_GBM4_rep1.bigwig",
        "GSM7108397_ChIRP_GBM4_rep2.bigwig",
        "GSM7108406_ChiRP_GBM4_Input.bigwig",
        "GSM7108411_ChiRP_GBM4_LacZ.bigwig",
    )
    handles = [pyBigWig.open(str(SOURCE / name)) for name in names]
    try:
        chromosome_maps = [handle.chroms() for handle in handles]
        for chromosome in PRIMARY_CHROMOSOMES:
            require(all(chromosome in chromosomes for chromosomes in chromosome_maps), f"LINC BigWig missing {chromosome}")
            chromosome_length = int(chromosome_maps[0][chromosome])
            require(
                all(int(chromosomes[chromosome]) == chromosome_length for chromosomes in chromosome_maps),
                f"LINC BigWig chromosome length drift: {chromosome}",
            )
        library_totals = []
        for handle in handles:
            total = 0.0
            for chromosome in PRIMARY_CHROMOSOMES:
                for start, end, value in handle.intervals(chromosome) or ():
                    if value:
                        total += (end - start) * value
            library_totals.append(total)
        library_totals_array = np.array(library_totals, dtype=np.float64)
        require(np.all(library_totals_array > 0), "LINC BigWig primary-chromosome signal total is zero")
        candidates: list[Candidate] = []
        counts = {4: 0, 8: 0}
        source_row = 0
        for chromosome in PRIMARY_CHROMOSOMES:
            chromosome_length = int(chromosome_maps[0][chromosome])
            normalized = []
            for handle, total in zip(handles, library_totals, strict=True):
                values = integrated_fixed_bins(handle.intervals(chromosome) or (), chromosome_length)
                values *= 1_000_000.0 / total
                normalized.append(values)
            replicate = np.minimum(normalized[0], normalized[1])
            control = np.maximum(normalized[2], normalized[3])
            eligible_by_threshold = {
                threshold: (replicate > 0) & (replicate >= threshold * control)
                for threshold in counts
            }
            for threshold in counts:
                counts[threshold] += int(np.count_nonzero(eligible_by_threshold[threshold]))
            strength = np.log1p(replicate) - np.log1p(control)
            for bin_index in np.flatnonzero(eligible_by_threshold[int(LINC_SIGNAL_THRESHOLD)]):
                source_row += 1
                start = int(bin_index) * WINDOW_LENGTH
                candidate = candidate_from_source(
                    DATASET_BY_ID["bte_linc01116_gse227804"],
                    source_row,
                    chromosome,
                    start,
                    start + WINDOW_LENGTH,
                    lo,
                    float(strength[bin_index]),
                )
                if candidate is not None:
                    candidates.append(candidate)
        require({str(key): value for key, value in counts.items()} == LINC_FEASIBILITY_COUNTS, f"LINC feasibility count drift: {counts}")
        return candidates, {
            "track_paths": [f"source/{name}" for name in names],
            "primary_chromosome_signal_totals": [format(value, ".17g") for value in library_totals],
            "feasibility_chromosomes": list(PRIMARY_CHROMOSOMES),
            "feasibility_chromosome_count": len(PRIMARY_CHROMOSOMES),
            "fixed_window_length": WINDOW_LENGTH,
            "fixed_window_origin": 0,
            "fixed_window_count_definition": "ceil(primary_chromosome_length/4097)",
            "interval_integration": "sum(overlap_bp*BigWig_value)/4097 including final partial window",
            "track_normalization": "integrated_window_mean*1000000/primary_chromosome_signal_total",
            "eligibility_definition": "replicate=min(normalized_rep1,normalized_rep2); control=max(normalized_input,normalized_lacz); replicate>0 and replicate>=threshold*control",
            "selection_strength": "log1p(replicate)-log1p(control)",
            "threshold_candidate_counts": {str(key): value for key, value in counts.items()},
        }
    finally:
        for handle in handles:
            handle.close()


def raw_candidates() -> tuple[dict[str, list[Candidate]], dict[str, Any]]:
    liftovers = {"hg18": LiftOver(str(HG18_CHAIN)), "hg19": LiftOver(str(HG19_CHAIN))}
    by_dataset: dict[str, list[Candidate]] = {dataset.dataset_id: [] for dataset in DATASETS}
    source_counts: dict[str, Any] = {}
    for dataset in DATASETS:
        if dataset.peak_path is None:
            continue
        rows = peak_rows(SOURCE / dataset.peak_path)
        canonical_rows = sum(chromosome in PRIMARY_CHROMOSOMES for chromosome, _, _ in rows)
        for source_row, (chromosome, start, end) in enumerate(rows, 1):
            candidate = candidate_from_source(dataset, source_row, chromosome, start, end, liftovers[dataset.source_build])
            if candidate is not None:
                by_dataset[dataset.dataset_id].append(candidate)
        source_counts[dataset.dataset_id] = {
            "source_peak_rows": len(rows),
            "primary_chromosome_peak_rows": canonical_rows,
            "unique_center_liftover_rows": len(by_dataset[dataset.dataset_id]),
        }
    linc, signal_receipt = linc_signal_candidates(liftovers["hg19"])
    by_dataset["bte_linc01116_gse227804"] = linc
    source_counts["bte_linc01116_gse227804"] = {
        "source_signal_windows_at_8x": LINC_FEASIBILITY_COUNTS["8"],
        "unique_center_liftover_rows": len(linc),
        "signal_rule": signal_receipt,
    }
    return by_dataset, source_counts


def eligible_candidates(
    candidates: Mapping[str, Sequence[Candidate]],
    blacklist: Mapping[str, IntervalIndex],
) -> tuple[dict[str, list[Candidate]], dict[str, int]]:
    by_chromosome: dict[str, list[Candidate]] = {chromosome: [] for chromosome in PRIMARY_CHROMOSOMES}
    for rows in candidates.values():
        for row in rows:
            by_chromosome[row.target_chromosome].append(row)
    eligible: dict[str, list[Candidate]] = {dataset.dataset_id: [] for dataset in DATASETS}
    chromosome_lengths: dict[str, int] = {}
    for chromosome in PRIMARY_CHROMOSOMES:
        sequence = read_chromosome(chromosome)
        chromosome_lengths[chromosome] = len(sequence)
        for candidate in by_chromosome[chromosome]:
            if candidate.target_start0 < 0 or candidate.target_end0 > len(sequence):
                continue
            if blacklist[chromosome].overlaps(candidate.target_start0, candidate.target_end0):
                continue
            region = sequence[candidate.target_start0 : candidate.target_end0]
            if len(region) != WINDOW_LENGTH or "N" in region:
                continue
            eligible[candidate.dataset_id].append(
                replace(candidate, gc=gc_fraction(region), digest=sequence_digest(region))
            )
    return eligible, chromosome_lengths


def interval_overlaps(intervals: Sequence[tuple[int, int]], start: int, end: int) -> bool:
    return any(existing_start < end and start < existing_end for existing_start, existing_end in intervals)


def select_positives(eligible: Mapping[str, Sequence[Candidate]]) -> dict[str, list[Candidate]]:
    selected: dict[str, list[Candidate]] = {}
    for dataset in DATASETS:
        rows = list(eligible[dataset.dataset_id])
        if dataset.dataset_id == "bte_linc01116_gse227804":
            rows.sort(key=lambda row: (-(row.signal_strength or 0.0), row.selection_key))
        else:
            rows.sort(key=lambda row: row.selection_key)
        accepted: list[Candidate] = []
        occupied: dict[str, list[tuple[int, int]]] = {}
        for row in rows:
            intervals = occupied.setdefault(row.target_chromosome, [])
            if interval_overlaps(intervals, row.target_start0, row.target_end0):
                continue
            intervals.append((row.target_start0, row.target_end0))
            accepted.append(row)
            if len(accepted) == POSITIVE_COUNT:
                break
        require(len(accepted) == POSITIVE_COUNT, f"insufficient nonoverlapping positives: {dataset.dataset_id}")
        selected[dataset.dataset_id] = accepted
    return selected


MANIFEST_FIELDS = (
    "dataset_id",
    "outer_lncRNA_id",
    "region_id",
    "fasta_order",
    "label",
    "label_source",
    "source_build",
    "source_chromosome",
    "source_start0",
    "source_end0",
    "target_build",
    "target_chromosome",
    "target_start0",
    "target_end0",
    "target_length",
    "target_concat_start0",
    "target_concat_end0",
    "gc_fraction",
    "block_id",
    "positive_selection_rank",
    "negative_match_index",
    "matched_positive_region_id",
    "gc_absolute_difference",
    "region_sequence_sha256",
    "query_sequence_sha256",
    "query_fasta_path",
    "target_fasta_path",
)


def region_id(dataset_id: str, chromosome: str, start: int, end: int, digest: str) -> str:
    value = hashlib.sha256(f"{REGION_ID_SEED}|{dataset_id}|GRCh38|{chromosome}|{start}|{end}|{digest}".encode("ascii")).hexdigest()
    return f"bt5_{value[:24]}"


def build_regions(
    eligible: Mapping[str, Sequence[Candidate]],
    positives: Mapping[str, Sequence[Candidate]],
    chromosome_lengths: Mapping[str, int],
    blacklist: Mapping[str, IntervalIndex],
    queries: Mapping[str, str],
) -> tuple[list[dict[str, Any]], dict[str, list[tuple[str, str]]]]:
    forbidden = {
        (dataset.dataset_id, chromosome): IntervalIndex(
            (row.target_start0, row.target_end0)
            for row in eligible[dataset.dataset_id]
            if row.target_chromosome == chromosome
        )
        for dataset in DATASETS
        for chromosome in PRIMARY_CHROMOSOMES
    }
    positive_rank = {
        (dataset_id, row.target_chromosome, row.target_start0, row.target_end0): rank
        for dataset_id, rows in positives.items()
        for rank, row in enumerate(rows, 1)
    }
    by_chromosome: dict[str, list[tuple[str, Candidate]]] = {chromosome: [] for chromosome in PRIMARY_CHROMOSOMES}
    for dataset_id, rows in positives.items():
        for row in rows:
            by_chromosome[row.target_chromosome].append((dataset_id, row))

    records: list[dict[str, Any]] = []
    sequences: dict[str, str] = {}
    occupied: dict[tuple[str, str], list[tuple[int, int]]] = {}
    for dataset_id, rows in positives.items():
        for row in rows:
            occupied.setdefault((dataset_id, row.target_chromosome), []).append((row.target_start0, row.target_end0))

    for chromosome in PRIMARY_CHROMOSOMES:
        sequence = read_chromosome(chromosome)
        require(len(sequence) == chromosome_lengths[chromosome], f"chromosome length changed during freeze: {chromosome}")
        for dataset_id, positive in sorted(
            by_chromosome[chromosome],
            key=lambda item: positive_rank[(item[0], item[1].target_chromosome, item[1].target_start0, item[1].target_end0)],
        ):
            dataset = DATASET_BY_ID[dataset_id]
            rank = positive_rank[(dataset_id, chromosome, positive.target_start0, positive.target_end0)]
            positive_sequence = sequence[positive.target_start0 : positive.target_end0]
            digest = sequence_digest(positive_sequence)
            require(digest == positive.digest, "positive sequence changed during region construction")
            positive_id = region_id(dataset_id, chromosome, positive.target_start0, positive.target_end0, digest)
            require(positive_id not in sequences, "duplicate region ID")
            sequences[positive_id] = positive_sequence
            query_path = (INPUT_ROOT / dataset_id / "query.fa").relative_to(ROOT).as_posix()
            target_path = (INPUT_ROOT / dataset_id / "target.fa").relative_to(ROOT).as_posix()
            records.append(
                {
                    "dataset_id": dataset_id,
                    "outer_lncRNA_id": dataset.outer_lncRNA_id,
                    "region_id": positive_id,
                    "fasta_order": 0,
                    "label": 1,
                    "label_source": "frozen_input_only_positive_rule",
                    "source_build": positive.source_build,
                    "source_chromosome": positive.source_chromosome,
                    "source_start0": positive.source_start0,
                    "source_end0": positive.source_end0,
                    "target_build": "GRCh38",
                    "target_chromosome": chromosome,
                    "target_start0": positive.target_start0,
                    "target_end0": positive.target_end0,
                    "target_length": WINDOW_LENGTH,
                    "target_concat_start0": 0,
                    "target_concat_end0": 0,
                    "gc_fraction": format(positive.gc or 0.0, ".12f"),
                    "block_id": chromosome,
                    "positive_selection_rank": rank,
                    "negative_match_index": 0,
                    "matched_positive_region_id": "NA",
                    "gc_absolute_difference": "0.000000000000",
                    "region_sequence_sha256": digest,
                    "query_sequence_sha256": sequence_digest(queries[dataset_id]),
                    "query_fasta_path": query_path,
                    "target_fasta_path": target_path,
                }
            )

            for match_index in range(1, NEGATIVES_PER_POSITIVE + 1):
                accepted: tuple[int, int, str, float, str] | None = None
                for counter in range(1, 1_000_001):
                    token = hashlib.sha256(
                        f"{NEGATIVE_SELECTION_SEED}|{dataset_id}|{positive.selection_key}|{match_index}|{counter}".encode("ascii")
                    ).digest()
                    start = int.from_bytes(token[:8], "big") % (len(sequence) - WINDOW_LENGTH + 1)
                    end = start + WINDOW_LENGTH
                    if blacklist[chromosome].overlaps(start, end):
                        continue
                    if forbidden[(dataset_id, chromosome)].overlaps(start, end):
                        continue
                    if interval_overlaps(occupied[(dataset_id, chromosome)], start, end):
                        continue
                    candidate_sequence = sequence[start:end]
                    if "N" in candidate_sequence:
                        continue
                    candidate_gc = gc_fraction(candidate_sequence)
                    difference = abs(candidate_gc - float(positive.gc or 0.0))
                    if difference > GC_TOLERANCE:
                        continue
                    candidate_digest = sequence_digest(candidate_sequence)
                    candidate_id = region_id(dataset_id, chromosome, start, end, candidate_digest)
                    if candidate_id in sequences:
                        continue
                    accepted = (start, end, candidate_id, difference, candidate_digest)
                    sequences[candidate_id] = candidate_sequence
                    occupied[(dataset_id, chromosome)].append((start, end))
                    break
                require(accepted is not None, f"negative matching exhausted: {dataset_id} positive {rank} match {match_index}")
                start, end, candidate_id, difference, candidate_digest = accepted
                records.append(
                    {
                        "dataset_id": dataset_id,
                        "outer_lncRNA_id": dataset.outer_lncRNA_id,
                        "region_id": candidate_id,
                        "fasta_order": 0,
                        "label": 0,
                        "label_source": "same_chromosome_gc_matched_negative",
                        "source_build": "NA",
                        "source_chromosome": "NA",
                        "source_start0": "NA",
                        "source_end0": "NA",
                        "target_build": "GRCh38",
                        "target_chromosome": chromosome,
                        "target_start0": start,
                        "target_end0": end,
                        "target_length": WINDOW_LENGTH,
                        "target_concat_start0": 0,
                        "target_concat_end0": 0,
                        "gc_fraction": format(gc_fraction(sequences[candidate_id]), ".12f"),
                        "block_id": chromosome,
                        "positive_selection_rank": rank,
                        "negative_match_index": match_index,
                        "matched_positive_region_id": positive_id,
                        "gc_absolute_difference": format(difference, ".12f"),
                        "region_sequence_sha256": candidate_digest,
                        "query_sequence_sha256": sequence_digest(queries[dataset_id]),
                        "query_fasta_path": query_path,
                        "target_fasta_path": target_path,
                    }
                )

    ordered_records: list[dict[str, Any]] = []
    target_records: dict[str, list[tuple[str, str]]] = {}
    for dataset in DATASETS:
        dataset_rows = sorted((row for row in records if row["dataset_id"] == dataset.dataset_id), key=lambda row: row["region_id"])
        require(len(dataset_rows) == REGIONS_PER_DATASET, f"dataset region count drift: {dataset.dataset_id}")
        require(sum(int(row["label"]) for row in dataset_rows) == POSITIVE_COUNT, f"dataset positive count drift: {dataset.dataset_id}")
        for order, row in enumerate(dataset_rows, 1):
            row["fasta_order"] = order
            concat_start = (order - 1) * (WINDOW_LENGTH + SEPARATOR_LENGTH)
            row["target_concat_start0"] = concat_start
            row["target_concat_end0"] = concat_start + WINDOW_LENGTH
        ordered_records.extend(dataset_rows)
        target_records[dataset.dataset_id] = [(row["region_id"], sequences[row["region_id"]]) for row in dataset_rows]
    require(len(ordered_records) == len(sequences) == len(DATASETS) * REGIONS_PER_DATASET, "global region count drift")
    require(len({row["region_id"] for row in ordered_records}) == len(ordered_records), "global region ID collision")
    return ordered_records, target_records


def source_urls() -> dict[str, str]:
    urls = {
        "source/gencode.v49.lncRNA_transcripts.fa.gz": "https://ftp.ebi.ac.uk/pub/databases/gencode/Gencode_human/release_49/gencode.v49.lncRNA_transcripts.fa.gz",
        "source/NR_045587.1.fa": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=nuccore&id=NR_045587.1&rettype=fasta&retmode=text",
        "source/hg18ToHg38.over.chain.gz": "https://hgdownload.soe.ucsc.edu/goldenPath/hg18/liftOver/hg18ToHg38.over.chain.gz",
        "source/hg19ToHg38.over.chain.gz": "https://hgdownload.soe.ucsc.edu/goldenPath/hg19/liftOver/hg19ToHg38.over.chain.gz",
        "source/hg38-blacklist.v2.bed.gz": "https://raw.githubusercontent.com/Boyle-Lab/Blacklist/master/lists/hg38-blacklist.v2.bed.gz",
        "source/GSE31332_hotair_oe_peaks.bed.gz": DATASET_BY_ID["bte_hotair_gse31332"].peak_url or "",
        "source/GSM1159894_PCGEM1_plusDHT_hs17l4_4.HOMERpeaks.txt.gz": DATASET_BY_ID["bte_pcgem1_gse47804"].peak_url or "",
        "source/GSM1415922_NTERA2_SRA.bed.gz": DATASET_BY_ID["bte_sra_gse58641"].peak_url or "",
        "source/GSM3161929_WT-CHIRP-seq_peaks.bed.gz": DATASET_BY_ID["bte_hottip_gse114981"].peak_url or "",
    }
    for filename in (
        "GSM7108396_ChIRP_GBM4_rep1.bigwig",
        "GSM7108397_ChIRP_GBM4_rep2.bigwig",
        "GSM7108406_ChiRP_GBM4_Input.bigwig",
        "GSM7108411_ChiRP_GBM4_LacZ.bigwig",
    ):
        accession = filename.split("_", 1)[0]
        urls[f"source/{filename}"] = f"https://ftp.ncbi.nlm.nih.gov/geo/samples/GSM7108nnn/{accession}/suppl/{filename}"
    for chromosome in PRIMARY_CHROMOSOMES:
        urls[f"source/grch38-primary/{chromosome}.fa.gz"] = f"https://hgdownload.soe.ucsc.edu/goldenPath/hg38/chromosomes/{chromosome}.fa.gz"
    return urls


def source_receipt(source_counts: Mapping[str, Any]) -> dict[str, Any]:
    urls = source_urls()
    files = []
    for relative, url in sorted(urls.items()):
        path = ARTIFACT_ROOT / relative
        files.append({"path": path.relative_to(ROOT).as_posix(), "url": url, "size_bytes": path.stat().st_size, "sha256": sha256_file(path)})
    return {
        "schema_version": 1,
        "phase": 5,
        "status": "complete",
        "selection_timestamp": SELECTION_TIMESTAMP,
        "assembly_target": "GRCh38",
        "coordinate_policy": "source_interval_center_unique_chain_mapping_then_centered_4097bp_GRCh38_window",
        "source_counts": source_counts,
        "files": files,
        "public_data_access": "NCBI_GEO_GENCODE_UCSC_and_ENCODE_blacklist_public_downloads",
        "dataset_specific_license_asserted": False,
        "legal_access_gate_pass": True,
    }


DEVELOPMENT_FIELDS = (
    "outer_lncRNA_id",
    "lncRNA",
    "query_sequence_sha256",
    "development_source",
    "registry_scope",
    "development_or_evaluation",
    "primary_evaluation_allowed",
    "reason",
)


def development_rows() -> list[dict[str, Any]]:
    digests = {
        "MEG3": "c67150e68d7b4e97de72704aebcac52d2bd3342a200715484e99fff2f015e15d",
        "MALAT1": "056b43eb32bea3b841261eb771fea92f193f43a51f4d5ed6f03bb69fb30da5f1",
        "NEAT1": "0cd673f10dba5ebfd5263eb274fdd25ad71e31d63eea4f4fdc3c458d7b8753df",
        "H19": "7d94fb9515b0fa63dbe8fb62e01bb50616760ce80eeef29ec9c3893af8040f4e",
        "KCNQ1OT1": "f8883e1855017b7a28576770a8c8476a8eb1adbfcbef08d55c6dc74c49a86cc4",
    }
    return [
        {
            "outer_lncRNA_id": f"development_{name.lower()}",
            "lncRNA": name,
            "query_sequence_sha256": digest,
            "development_source": "paper/biological_topk/fresh_input_exclusion_registry.tsv",
            "registry_scope": "all historical accessions assays segments and digests for this lncRNA",
            "development_or_evaluation": "development",
            "primary_evaluation_allowed": 0,
            "reason": "historical development paper generalization or parameter evidence",
        }
        for name, digest in digests.items()
    ]


EVALUATION_FIELDS = (
    "dataset_id",
    "outer_lncRNA_id",
    "lncRNA",
    "assay",
    "assay_type_class",
    "assay_type_available",
    "availability_reason",
    "accession",
    "publication",
    "genome_build",
    "query_construction_type",
    "full_transcript_or_domain_coordinates",
    "query_length",
    "sequence_sha256",
    "positive_definition",
    "negative_definition",
    "license",
    "development_or_evaluation",
    "failure_reason",
)


def evaluation_rows(queries: Mapping[str, str]) -> list[dict[str, Any]]:
    rows = []
    for dataset in DATASETS:
        rows.append(
            {
                "dataset_id": dataset.dataset_id,
                "outer_lncRNA_id": dataset.outer_lncRNA_id,
                "lncRNA": dataset.lncRNA,
                "assay": "ChIRP-seq",
                "assay_type_class": "ChIRP",
                "assay_type_available": 1,
                "availability_reason": "public genomic-DNA occupancy data, reconstructable input-only labels, and independently fixed in-envelope query",
                "accession": f"{dataset.accession};{dataset.sample_accession}",
                "publication": f"{dataset.publication};{dataset.publication_id}",
                "genome_build": dataset.source_build,
                "query_construction_type": dataset.query_construction,
                "full_transcript_or_domain_coordinates": f"{dataset.query_transcript}:0-{len(queries[dataset.dataset_id])}",
                "query_length": len(queries[dataset.dataset_id]),
                "sequence_sha256": sequence_digest(queries[dataset.dataset_id]),
                "positive_definition": dataset.positive_rule,
                "negative_definition": "9 nonoverlapping same-chromosome GRCh38 windows per positive; no source-positive, blacklist, or N overlap; absolute GC difference <=0.05",
                "license": "public GEO data; no dataset-specific redistribution license asserted",
                "development_or_evaluation": "primary_evaluation",
                "failure_reason": "NA",
            }
        )
    exclusions = (
        ("excluded_terc_gse31332", "TERC", "ChIRP", "query approximately 451 nt, below the 500-nt operating minimum"),
        ("excluded_prncr1_gse47804", "PRNCR1", "ChIRP", "complete query exceeds 2812 nt and arbitrary truncation is forbidden"),
        ("excluded_rain", "RAIN", "ChIRP", "eight public isoforms and no unambiguous assay-linked query isoform"),
        ("excluded_slncr_gse302468", "SLNCR", "RNA-seq perturbation", "not genomic DNA occupancy or binding labels"),
        ("excluded_hlmr1_gse335367", "HLMR1", "ChIRP-RNA", "RNA interactome assay rather than genomic DNA occupancy"),
        ("excluded_hmrhl", "Hmrhl", "RNA-seq", "only public RNA-seq perturbation data identified"),
        ("excluded_xist", "XIST", "targeted occupancy", "no qualifying public targeted dataset with an in-envelope independent query identified"),
        ("excluded_firre", "FIRRE", "targeted occupancy", "no qualifying public targeted dataset with reconstructable labels identified"),
    )
    for dataset_id, name, assay, reason in exclusions:
        rows.append(
            {
                "dataset_id": dataset_id,
                "outer_lncRNA_id": f"excluded_{name.lower()}",
                "lncRNA": name,
                "assay": assay,
                "assay_type_class": "not_available",
                "assay_type_available": 0,
                "availability_reason": "failed frozen input/data availability definition",
                "accession": "NA",
                "publication": "NA",
                "genome_build": "NA",
                "query_construction_type": "NA",
                "full_transcript_or_domain_coordinates": "NA",
                "query_length": "NA",
                "sequence_sha256": "NA",
                "positive_definition": "NA",
                "negative_definition": "NA",
                "license": "NA",
                "development_or_evaluation": "excluded_inventory_candidate",
                "failure_reason": reason,
            }
        )
    return rows


def power_simulation() -> dict[str, Any]:
    means = np.array([0.0, 0.0, 0.10, math.log(2.0)], dtype=np.float64)
    standard_deviations = np.array([0.010, 0.020, 0.030, 0.20], dtype=np.float64)
    rng = np.random.default_rng(SIMULATION_SEED)
    panels = rng.normal(means, standard_deviations, size=(SIMULATION_REPLICATES, len(DATASETS), 4))
    bootstrap_rng = np.random.default_rng(BOOTSTRAP_SEED)
    bootstrap_indices = bootstrap_rng.integers(0, len(DATASETS), size=(BOOTSTRAP_REPLICATES, len(DATASETS)))
    thresholds = np.array([-0.02, -0.05, 0.0, 0.0], dtype=np.float64)
    strict = np.array([False, False, True, True])
    endpoint_pass = np.zeros((SIMULATION_REPLICATES, 4), dtype=bool)
    finite = np.zeros(SIMULATION_REPLICATES, dtype=bool)
    for start in range(0, SIMULATION_REPLICATES, 100):
        batch = panels[start : start + 100]
        bootstrap_means = batch[:, bootstrap_indices, :].mean(axis=2)
        lower = np.quantile(bootstrap_means, 0.05, axis=1, method="inverted_cdf")
        finite[start : start + len(batch)] = np.isfinite(lower).all(axis=1)
        endpoint_pass[start : start + len(batch)] = (lower >= thresholds) & ((~strict) | (lower > thresholds))
    marginal = endpoint_pass.sum(axis=0)
    joint = int(endpoint_pass.all(axis=1).sum())
    return {
        "schema_version": 1,
        "phase": 5,
        "status": "complete",
        "simulation_role": "design_identifiability_and_power_only_not_biological_evidence",
        "simulation_seed": SIMULATION_SEED,
        "simulation_replicates": SIMULATION_REPLICATES,
        "distinct_lncRNA_outer_units": len(DATASETS),
        "datasets_per_lncRNA": 1,
        "regions_per_dataset": REGIONS_PER_DATASET,
        "positives_per_dataset": POSITIVE_COUNT,
        "prevalence": "0.1",
        "planning_ranges": {
            "plausible_prevalence": ["0.01", "0.10"],
            "expected_aucpr": ["0.05", "0.40"],
            "within_dataset_block_size": [25, 50, 100],
            "within_dataset_correlation": ["0.05", "0.10", "0.20"],
            "within_lncRNA_cross_assay_correlation": ["0.25", "0.50", "0.75"],
        },
        "simulation_model": {
            "endpoint_order": ["E1", "E2", "E3", "E4"],
            "lncRNA_level_true_means": [format(value, ".17g") for value in means],
            "between_lncRNA_standard_deviations": [format(value, ".17g") for value in standard_deviations],
            "distribution": "independent_normal_planning_scenario",
            "interpretation": "pre-specified plausible passing scenario used only to test finite one-sided interval identification with five outer units",
        },
        "analysis": {
            "bootstrap_seed": BOOTSTRAP_SEED,
            "bootstrap_replicates": BOOTSTRAP_REPLICATES,
            "outer_resampling_unit": "distinct_lncRNA",
            "nested_dataset_level": "one_primary_dataset_per_lncRNA_no_resampling_needed",
            "nested_block": "chromosome",
            "shared_resample_indices_for_all_endpoints": True,
            "zero_precision_resample_rule": "negative_infinity_E4_no_pseudocount_or_replacement",
            "one_sided_lcb_quantile": "0.05",
            "quantile_method": "inverted_cdf",
            "thresholds": {"E1": ">=-0.02", "E2": ">=-0.05", "E3": ">0", "E4": ">0"},
        },
        "results": {
            "finite_lcb_panels": int(finite.sum()),
            "finite_lcb_fraction": format(float(finite.mean()), ".17g"),
            "marginal_gate_pass_counts": {endpoint: int(marginal[index]) for index, endpoint in enumerate(("E1", "E2", "E3", "E4"))},
            "joint_gate_pass_count": joint,
            "joint_gate_pass_probability": format(joint / SIMULATION_REPLICATES, ".17g"),
            "one_sided_interval_identifiable": bool(finite.all()),
        },
    }


def tool_receipt() -> dict[str, Any]:
    version = subprocess.run(
        (str(EXTERNAL_BINARY), "--version"),
        cwd=ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=30,
    )
    expected_version = "Version 1.3.2 (30/03/2012) SeqAn Revision: 1225"
    require(
        version.returncode == 1 and version.stdout.strip() == expected_version,
        "Triplexator version probe drift",
    )
    return {
        "schema_version": 1,
        "phase": 5,
        "status": "pass",
        "authority": {
            "path": AUTHORITY_BINARY.relative_to(ROOT).as_posix(),
            "sha256": sha256_file(AUTHORITY_BINARY),
            "runtime_receipt_path": RUNTIME_RECEIPT.relative_to(ROOT).as_posix(),
            "runtime_receipt_sha256": sha256_file(RUNTIME_RECEIPT),
        },
        "candidate": {
            "path": CANDIDATE_BINARY.relative_to(ROOT).as_posix(),
            "sha256": sha256_file(CANDIDATE_BINARY),
            "runtime_receipt_path": RUNTIME_RECEIPT.relative_to(ROOT).as_posix(),
            "runtime_receipt_sha256": sha256_file(RUNTIME_RECEIPT),
        },
        "external": {
            "name": "Triplexator",
            "upstream_repository": "https://github.com/Gurado/Triplexator.git",
            "upstream_tag": "v1.3.3",
            "upstream_commit": "4505bba7b3dc8cf4922d71446c755e91c448673c",
            "reported_version": version.stdout.strip(),
            "version_probe_exit_code": version.returncode,
            "path": EXTERNAL_BINARY.relative_to(ROOT).as_posix(),
            "sha256": sha256_file(EXTERNAL_BINARY),
            "license_path": EXTERNAL_LICENSE.relative_to(ROOT).as_posix(),
            "license_sha256": sha256_file(EXTERNAL_LICENSE),
            "license": "CC BY-NC-ND 3.0 Australia",
            "use_boundary": "local noncommercial research evaluation only; do not redistribute source or binary without owner/legal review",
            "build": "GNU++98 permissive compatibility build; private compatibility patch changes obsolete SeqAn abstract return types from value to reference only",
            "upstream_smoke_tests": "14/14 pass",
            "primary_metric_comparability": False,
            "failure_policy": "retain terminal failure; no replacement or outcome-informed retry",
        },
        "external_predictor_available": True,
    }


ATTEMPT_FIELDS = (
    "attempt_id",
    "execution_index",
    "dataset_id",
    "outer_lncRNA_id",
    "arm",
    "backend",
    "primary_comparator_arm",
    "query_fasta_path",
    "query_fasta_sha256",
    "query_sequence_sha256",
    "target_fasta_path",
    "target_fasta_sha256",
    "region_count",
    "labels_visible_to_backend",
    "binary_path",
    "binary_sha256",
    "parameter_bundle_sha256",
    "argument_template",
    "runner_path",
    "runner_sha256",
    "analyzer_path",
    "analyzer_sha256",
    "gpu_physical_index",
    "cpu_affinity",
    "timeout_seconds",
    "retry_policy",
    "comparison_policy",
    "artifact_root",
    "status",
)


def attempt_rows(runtime_files: Mapping[Path, bytes], queries: Mapping[str, str]) -> list[dict[str, Any]]:
    require(RUNNER.is_file() and ANALYZER.is_file(), "Phase 6 runner/analyzer must exist before the attempt freeze")
    binaries = {"A": AUTHORITY_BINARY, "G": CANDIDATE_BINARY, "X": EXTERNAL_BINARY}
    backends = {"A": "archived_cpu_authority", "G": "archived_gasal2_candidate", "X": "triplexator_v1.3.3_external"}
    arguments = {
        "A": "{binary} -f1 {target_fasta} -f2 {query_fasta} -r 0 -O {output_directory}",
        "G": "{binary} -f1 {target_fasta} -f2 {query_fasta} -r 0 -O {output_directory}",
        "X": "{binary} -ss {query_fasta} -ds {target_fasta} -l 16 -L 30 -e 5 -of 2 -rm 0 -o {output_file}",
    }
    rows: list[dict[str, Any]] = []
    execution_index = 0
    for dataset_index, dataset in enumerate(DATASETS):
        query_path = INPUT_ROOT / dataset.dataset_id / "query.fa"
        target_path = INPUT_ROOT / dataset.dataset_id / "target.fa"
        for arm in ("A", "G", "X"):
            execution_index += 1
            binary = binaries[arm]
            parameter_bundle = {
                "arm": arm,
                "argument_template": arguments[arm],
                "region_score": "maximum exact Score among rows with Nt(bp)>50; no-valid-row=-1" if arm in {"A", "G"} else "external_summary_diagnostic_only",
                "environment": "frozen_by_phase6_runner",
            }
            attempt_id = f"bt6_{dataset_index + 1:02d}_{arm.lower()}"
            rows.append(
                {
                    "attempt_id": attempt_id,
                    "execution_index": execution_index,
                    "dataset_id": dataset.dataset_id,
                    "outer_lncRNA_id": dataset.outer_lncRNA_id,
                    "arm": arm,
                    "backend": backends[arm],
                    "primary_comparator_arm": int(arm in {"A", "G"}),
                    "query_fasta_path": query_path.relative_to(ROOT).as_posix(),
                    "query_fasta_sha256": sha256_bytes(runtime_files[query_path]),
                    "query_sequence_sha256": sequence_digest(queries[dataset.dataset_id]),
                    "target_fasta_path": target_path.relative_to(ROOT).as_posix(),
                    "target_fasta_sha256": sha256_bytes(runtime_files[target_path]),
                    "region_count": REGIONS_PER_DATASET,
                    "labels_visible_to_backend": 0,
                    "binary_path": binary.relative_to(ROOT).as_posix(),
                    "binary_sha256": sha256_file(binary),
                    "parameter_bundle_sha256": canonical_digest(parameter_bundle),
                    "argument_template": arguments[arm],
                    "runner_path": RUNNER.relative_to(ROOT).as_posix(),
                    "runner_sha256": sha256_file(RUNNER),
                    "analyzer_path": ANALYZER.relative_to(ROOT).as_posix(),
                    "analyzer_sha256": sha256_file(ANALYZER),
                    "gpu_physical_index": dataset_index % 2 if arm == "G" else "NA",
                    "cpu_affinity": "0-9" if arm in {"A", "X"} else "10-19",
                    "timeout_seconds": 43200,
                    "retry_policy": "none",
                    "comparison_policy": "offline_after_all_15_attempts_terminal",
                    "artifact_root": f".paper-artifacts/biological-topk-successor/experimental-phase6/{attempt_id}",
                    "status": "preregistered_not_run",
                }
            )
    require(len(rows) == 15, "experimental attempt count drift")
    return rows


def benchmark_spec() -> bytes:
    return b"""# Independent Experimental Benchmark Specification

This Phase 5 freeze contains five distinct primary lncRNA outer units and one
ChIRP dataset per unit. All source labels, query identities, target regions,
negative matches, tool bindings, endpoint definitions, and resampling rules
were fixed before any evaluation prediction.

Each dataset has exactly 100 positive and 900 negative 4097-bp GRCh38 windows.
Author peaks are selected by deterministic input-only hash ranking after unique
center liftOver. LINC01116 positives are the strongest 100 eligible fixed bins
under the frozen two-replicate versus Input/LacZ normalized 8x rule. Negatives
are on the same chromosome as their matched positive, differ in GC fraction by
at most 0.05, do not overlap any eligible source-positive window or blacklist,
contain no N, and do not overlap another selected region in that dataset.

Region IDs are label-blind and FASTA order is ascending region ID. Because the
frozen Fasim interface reads only the first target FASTA record, each dataset's
target is one record containing the ordered regions separated by 4097 Ns. The
manifest freezes every region's concatenated offset. The analyzer rejects any
row not wholly contained in one region. Prediction backends receive only query
and target FASTA files; they do not receive the experimental manifest. Labels
are read only by the offline analyzer after all 15 A/G/X attempts are terminal.

For A and G, the primary region score is the maximum exact integer Score among
valid emitted rows with Nt(bp)>50. A region with no valid row receives -1. The
emission source filters at scoreMin=0, so -1 is strictly below the legal emitted
minimum. Ties are ordered by the fixed region ID. X is an external diagnostic
and is not substituted for either primary arm.

Per dataset, the primary metrics are AUCPR, recall@P_d, precision@P_d,
prevalence, and natural-log top-P enrichment, where P_d=100. Dataset values are
aggregated equally within lncRNA and then equally across the five distinct
lncRNAs. Here each lncRNA has one primary dataset.

All four endpoints use the same 10,000 paired hierarchical bootstrap indices,
seed 20260816, and an inverted-CDF one-sided 5th percentile lower bound. The
outer unit is lncRNA and the nested block is chromosome. A and G remain paired
at every level. A bootstrap resample with zero top-P precision receives
negative-infinity E4, so it cannot improve the lower bound; no pseudocount,
resample deletion, or replacement is allowed. E1 requires LCB(G-A
AUCPR)>=-0.02, E2 requires LCB(G-A
recall@P)>=-0.05, E3 requires LCB(G AUCPR-prevalence)>0, and E4 requires
LCB(log(G precision@P/prevalence))>0. All four must pass. Any primary dataset
with zero precision forces E4 and the global gate to fail without a pseudocount
or bootstrap replacement.

Only ChIRP met the frozen input/data availability definition. Therefore
cross_assay_generality_claim=not_supported.
"""


def benchmark_plan(
    manifest_payload: bytes,
    attempt_payload: bytes,
    power: Mapping[str, Any],
    source: Mapping[str, Any],
    tools: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "phase": 5,
        "epoch_id": "biological_topk_successor_v2",
        "source_commit": PHASE4_COMMIT,
        "status": "preregistered",
        "dataset_count": len(DATASETS),
        "distinct_lncRNA_outer_units": len(DATASETS),
        "assay_type_classes_available": ["ChIRP"],
        "primary_assay_type_classes": ["ChIRP"],
        "cross_assay_generality_claim": "not_supported",
        "regions_per_dataset": REGIONS_PER_DATASET,
        "positives_per_dataset": POSITIVE_COUNT,
        "negatives_per_positive": NEGATIVES_PER_POSITIVE,
        "target_region_length": WINDOW_LENGTH,
        "target_separator_length": SEPARATOR_LENGTH,
        "target_serialization": "single FASTA record; ascending label-blind region_id; 4097-N separators; manifest-frozen offsets",
        "target_build": "GRCh38",
        "negative_matching": {
            "same_chromosome": True,
            "absolute_gc_difference_max": "0.05",
            "exclude_source_positive_windows": True,
            "exclude_blacklist": True,
            "exclude_N": True,
            "selected_region_nonoverlap": True,
            "seed": NEGATIVE_SELECTION_SEED,
        },
        "label_blinding": {
            "region_id": "bt5_<24 lowercase hexadecimal characters>",
            "fasta_header": "t_<24 lowercase hexadecimal characters>",
            "fasta_order": "ascending_region_id with manifest-frozen concatenated offsets",
            "labels_visible_to_prediction_backend": False,
            "labels_read_stage": "offline_only_after_all_attempts_terminal",
        },
        "region_score": {
            "valid_row_rule": "existing contract validity and Nt(bp)>50",
            "primary": "maximum exact integer Score",
            "no_valid_row_sentinel": -1,
            "legal_emitted_score_minimum": 0,
            "sentinel_below_legal_minimum": True,
            "tie_policy": "ascending fixed region_id without labels",
            "identical_function_for_A_and_G": True,
        },
        "primary_k": {"name": "recall_at_P_d", "P_d": POSITIVE_COUNT},
        "endpoints": {
            "E1": {"contrast": "macro_lncRNA_G_minus_A_AUCPR", "lcb": ">=-0.02"},
            "E2": {"contrast": "macro_lncRNA_G_minus_A_recall_at_P", "lcb": ">=-0.05"},
            "E3": {"contrast": "macro_lncRNA_G_AUCPR_minus_prevalence", "lcb": ">0"},
            "E4": {"contrast": "macro_lncRNA_log_G_precision_at_P_over_prevalence", "lcb": ">0"},
        },
        "intersection_union_gate": "E1_AND_E2_AND_E3_AND_E4",
        "zero_precision_rule": "automatic_E4_and_global_failure_no_pseudocount",
        "bootstrap": power["analysis"],
        "bootstrap_zero_precision_resample_rule": "negative_infinity_E4_no_pseudocount_or_replacement",
        "execution": {
            "attempt_count": 15,
            "arms": ["A", "G", "X"],
            "independent_execution": True,
            "comparison_barrier": "all_15_attempts_terminal",
            "max_gpu_hours": 96,
            "max_cpu_wall_hours": 96,
            "max_total_artifact_storage_bytes": 64 * 1024**3,
            "tracked_evidence_reservation_bytes": 256 * 1024**2,
            "fixed_quota_includes_predecessor_evidence": True,
            "max_infrastructure_repair_epochs": 1,
            "scientific_retry_or_replacement": False,
        },
        "bindings": {
            "experimental_benchmark_manifest_sha256": sha256_bytes(manifest_payload),
            "experimental_attempt_plan_sha256": sha256_bytes(attempt_payload),
            "experimental_power_simulation_sha256": canonical_digest(power),
            "experimental_source_receipt_sha256": canonical_digest(source),
            "experimental_tool_receipt_sha256": canonical_digest(tools),
        },
        "evaluation_prediction_started": False,
        "scientific_output_created": False,
        "phase_6_authorized": True,
    }


def build() -> tuple[dict[Path, bytes], dict[Path, bytes]]:
    queries = query_sequences()
    blacklist = blacklist_indexes()
    raw, source_counts = raw_candidates()
    eligible, chromosome_lengths = eligible_candidates(raw, blacklist)
    positives = select_positives(eligible)
    for dataset in DATASETS:
        source_counts[dataset.dataset_id]["eligible_GRCh38_windows"] = len(eligible[dataset.dataset_id])
        source_counts[dataset.dataset_id]["selected_primary_positive_windows"] = len(positives[dataset.dataset_id])
    manifest_rows, target_records = build_regions(eligible, positives, chromosome_lengths, blacklist, queries)

    runtime: dict[Path, bytes] = {}
    for dataset in DATASETS:
        query = queries[dataset.dataset_id]
        runtime[INPUT_ROOT / dataset.dataset_id / "query.fa"] = fasta_bytes(f"q_{sequence_digest(query)[:24]}", query)
        concatenated = ("N" * SEPARATOR_LENGTH).join(sequence for _, sequence in target_records[dataset.dataset_id])
        require(len(concatenated) == REGIONS_PER_DATASET * WINDOW_LENGTH + (REGIONS_PER_DATASET - 1) * SEPARATOR_LENGTH, "concatenated target length drift")
        runtime[INPUT_ROOT / dataset.dataset_id / "target.fa"] = fasta_bytes(f"t_{sequence_digest(concatenated)[:24]}", concatenated)

    manifest_payload = tsv_bytes(MANIFEST_FIELDS, manifest_rows)
    source_value = source_receipt(source_counts)
    tool_value = tool_receipt()
    power_value = power_simulation()
    attempts = attempt_rows(runtime, queries)
    attempt_payload = tsv_bytes(ATTEMPT_FIELDS, attempts)
    plan_value = benchmark_plan(manifest_payload, attempt_payload, power_value, source_value, tool_value)
    information_value = {
        "schema_version": 1,
        "phase": 5,
        "decision": "pass",
        "distinct_lncRNA_outer_units": len(DATASETS),
        "minimum_distinct_lncRNAs": 5,
        "minimum_outer_unit_gate_pass": True,
        "primary_dataset_count": len(DATASETS),
        "all_primary_lncRNAs_have_dataset": True,
        "available_assay_type_classes": ["ChIRP"],
        "multiple_assay_types_input_eligible": False,
        "cross_assay_generality_claim": "not_supported",
        "one_sided_interval_identifiable": power_value["results"]["one_sided_interval_identifiable"],
        "finite_lcb_simulation_fraction": power_value["results"]["finite_lcb_fraction"],
        "power_simulation_sha256": canonical_digest(power_value),
        "external_predictor_available": tool_value["external_predictor_available"],
        "labels_and_negatives_deterministic": True,
        "evaluation_prediction_started": False,
        "phase_6_authorized": True,
        "blocked_reason": None,
    }
    runtime_receipt_value = {
        "schema_version": 1,
        "phase": 5,
        "status": "complete",
        "files": [
            {
                "path": path.relative_to(ROOT).as_posix(),
                "size_bytes": len(payload),
                "sha256": sha256_bytes(payload),
                "contains_labels": False,
            }
            for path, payload in sorted(runtime.items(), key=lambda item: item[0].as_posix())
        ],
        "dataset_count": len(DATASETS),
        "query_fasta_count": len(DATASETS),
        "target_fasta_count": len(DATASETS),
        "target_fasta_records_per_dataset": 1,
        "target_separator_length": SEPARATOR_LENGTH,
        "target_region_count": len(manifest_rows),
        "fasta_headers_label_blind": True,
        "evaluation_prediction_started": False,
    }
    tracked = {
        DEVELOPMENT_REGISTRY: tsv_bytes(DEVELOPMENT_FIELDS, development_rows()),
        EVALUATION_INVENTORY: tsv_bytes(EVALUATION_FIELDS, evaluation_rows(queries)),
        SOURCE_RECEIPT: canonical_json_bytes(source_value),
        TOOL_RECEIPT: canonical_json_bytes(tool_value),
        POWER_SIMULATION: canonical_json_bytes(power_value),
        INFORMATION_DECISION: canonical_json_bytes(information_value),
        BENCHMARK_SPEC: benchmark_spec(),
        BENCHMARK_PLAN: canonical_json_bytes(plan_value),
        BENCHMARK_MANIFEST: manifest_payload,
        ATTEMPT_PLAN: attempt_payload,
        MANIFEST_CHECKSUM: f"{sha256_bytes(manifest_payload)}  {BENCHMARK_MANIFEST.name}\n".encode("ascii"),
        RUNTIME_INPUT_RECEIPT: canonical_json_bytes(runtime_receipt_value),
    }
    return tracked, runtime


def write_payloads(payloads: Mapping[Path, bytes]) -> None:
    for path, payload in payloads.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.tmp")
        temporary.write_bytes(payload)
        temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        tracked, runtime = build()
        payloads = {**tracked, **runtime}
        if args.write:
            write_payloads(payloads)
            print(f"wrote {len(tracked)} tracked and {len(runtime)} runtime Phase 5 artifacts")
            return 0
        stale = [
            path.relative_to(ROOT).as_posix()
            for path, payload in payloads.items()
            if not path.is_file() or path.is_symlink() or path.read_bytes() != payload
        ]
        require(not stale, f"Phase 5 artifacts do not reproduce: {stale}")
        print("successor Phase 5 benchmark artifacts reproduce byte-for-byte")
        return 0
    except (FreezeError, OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"successor Phase 5 freeze failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
