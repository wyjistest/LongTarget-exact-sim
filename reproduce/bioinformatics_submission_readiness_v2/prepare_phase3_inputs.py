#!/usr/bin/env python3
"""Create the fresh input-only Phase 3 panel without running prediction code."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import os
import re
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator


ROOT = Path(__file__).resolve().parents[2]
PAPER = ROOT / "paper/bioinformatics_submission_readiness_v2"
ARTIFACT_ROOT = ROOT / ".paper-artifacts/bioinformatics-submission-readiness-v2/phase3"
V2_ARTIFACT_ROOT = ARTIFACT_ROOT.parent
INPUT_ROOT = ARTIFACT_ROOT / "frozen-inputs"
MANIFEST = PAPER / "phase_3_input_manifest.tsv"
EXCLUSION_RECEIPT = PAPER / "phase_3_exclusion_digest_receipt.json"
SOURCE_RECEIPT = ROOT / "paper/biological_topk_successor/experimental_source_receipt.json"
SOURCE_ROOT = ROOT / ".paper-artifacts/biological-topk-successor/experimental-phase5/source"
QUERY_SOURCE = SOURCE_ROOT / "gencode.v49.lncRNA_transcripts.fa.gz"
SELECTION_SEED = "bioinformatics_submission_readiness_v2_phase3_inputs_20260731"
WORKLOAD_COUNT = 10
TARGET_LENGTH = 20_000_001
QUERY_MIN_LENGTH = 450
QUERY_MAX_LENGTH = 750
CHROMOSOMES = tuple(f"chr{index}" for index in range(1, WORKLOAD_COUNT + 1))
MANIFEST_FIELDS = (
    "workload_id",
    "selection_seed",
    "query_ordinal_namespace",
    "query_source_ordinal",
    "query_header",
    "query_path",
    "query_sequence_length",
    "query_sequence_sha256",
    "query_gc_fraction",
    "query_extraction_recipe_id",
    "target_ordinal_namespace",
    "target_source_ordinal",
    "target_header",
    "target_path",
    "target_sequence_length",
    "target_sequence_sha256",
    "target_gc_fraction",
    "target_extraction_recipe_id",
    "assembly",
    "target_coordinate_namespace",
    "chromosome",
    "target_region_start0",
    "target_region_end0",
    "query_source_path",
    "query_source_sha256",
    "target_source_path",
    "target_source_sha256",
    "fresh_against_exclusion_snapshot",
)


class InputFreezeError(RuntimeError):
    pass


@dataclass(frozen=True)
class FastaRecord:
    ordinal: int
    header: str
    sequence: str


def require(condition: bool, message: str) -> None:
    if not condition:
        raise InputFreezeError(message)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sequence_sha256(sequence: str) -> str:
    return sha256_bytes(sequence.encode("ascii"))


def read_single_fasta_sequence(path: Path) -> str:
    lines = path.read_text(encoding="ascii").splitlines()
    require(sum(line.startswith(">") for line in lines) == 1, f"not single-record FASTA: {path}")
    sequence = "".join(line.strip() for line in lines if line and not line.startswith(">" )).upper()
    require(bool(sequence), f"empty FASTA: {path}")
    return sequence


def iter_gzip_fasta(path: Path) -> Iterator[FastaRecord]:
    ordinal = 0
    header: str | None = None
    sequence: list[str] = []
    with gzip.open(path, "rt", encoding="ascii") as handle:
        for raw in handle:
            line = raw.strip()
            if not line:
                continue
            if line.startswith(">"):
                if header is not None:
                    yield FastaRecord(ordinal, header, "".join(sequence).upper())
                ordinal += 1
                header = line[1:]
                sequence = []
            else:
                require(header is not None, f"sequence precedes header in {path}")
                sequence.append(line)
    if header is not None:
        yield FastaRecord(ordinal, header, "".join(sequence).upper())


def read_gzip_chromosome(path: Path, chromosome: str) -> str:
    records = list(iter_gzip_fasta(path))
    require(len(records) == 1, f"expected one chromosome record in {path}")
    observed = records[0].header.split()[0]
    require(observed == chromosome, f"chromosome identity drift: {observed} != {chromosome}")
    return records[0].sequence


def acgt_runs(sequence: str, minimum_length: int) -> Iterator[tuple[int, int]]:
    start: int | None = None
    for index, base in enumerate(sequence):
        if base in "ACGT":
            if start is None:
                start = index
        elif start is not None:
            if index - start >= minimum_length:
                yield start, index
            start = None
    if start is not None and len(sequence) - start >= minimum_length:
        yield start, len(sequence)


def candidate_window_starts(sequence: str, length: int) -> list[int]:
    starts: set[int] = set()
    for run_start, run_end in acgt_runs(sequence, length):
        first_grid = ((run_start + 999_999) // 1_000_000) * 1_000_000
        starts.add(run_start)
        starts.add(run_end - length)
        starts.update(range(first_grid, run_end - length + 1, 1_000_000))
    return sorted(starts)


def walk_json_hashes(value: object) -> Iterator[str]:
    if isinstance(value, dict):
        for key, item in value.items():
            if key in {"query_sequence_sha256", "target_sequence_sha256"} and isinstance(item, str):
                if re.fullmatch(r"[0-9a-f]{64}", item):
                    yield item
            yield from walk_json_hashes(item)
    elif isinstance(value, list):
        for item in value:
            yield from walk_json_hashes(item)


def collect_excluded_digests() -> tuple[set[str], dict[str, int]]:
    digests: set[str] = set()
    counts = {"tracked_structured_records": 0, "artifact_fasta_files": 0, "tracked_fasta_files": 0}
    for path in (ROOT / "paper").rglob("*"):
        if not path.is_file():
            continue
        if PAPER in path.parents and path.name.startswith(
            ("phase_3_", "phase_4_", "phase_5_", "phase_6_", "phase_7_")
        ):
            continue
        if path.suffix == ".json":
            try:
                value = json.loads(path.read_text(encoding="utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue
            values = list(walk_json_hashes(value))
            counts["tracked_structured_records"] += len(values)
            digests.update(values)
        elif path.suffix == ".tsv":
            try:
                with path.open(newline="", encoding="utf-8") as handle:
                    rows = csv.DictReader(handle, delimiter="\t")
                    for row in rows:
                        for field in ("query_sequence_sha256", "target_sequence_sha256"):
                            value = row.get(field)
                            if value and re.fullmatch(r"[0-9a-f]{64}", value):
                                digests.add(value)
                                counts["tracked_structured_records"] += 1
            except (UnicodeDecodeError, csv.Error):
                continue
    artifact_root = ROOT / ".paper-artifacts"
    for path in artifact_root.rglob("*.fa"):
        if V2_ARTIFACT_ROOT in path.parents:
            relative = path.relative_to(V2_ARTIFACT_ROOT)
            if relative.parts and relative.parts[0] not in {"phase1", "phase2"}:
                continue
        if path.name not in {"query.fa", "target.fa"} and "frozen-inputs" not in path.parts:
            continue
        try:
            digests.add(sequence_sha256(read_single_fasta_sequence(path)))
            counts["artifact_fasta_files"] += 1
        except (OSError, UnicodeDecodeError, InputFreezeError):
            continue
    for path in (ROOT / "reproduce").rglob("*.fa"):
        try:
            digests.add(sequence_sha256(read_single_fasta_sequence(path)))
            counts["tracked_fasta_files"] += 1
        except (OSError, UnicodeDecodeError, InputFreezeError):
            continue
    return digests, counts


def source_receipt_map() -> dict[str, dict[str, object]]:
    receipt = json.loads(SOURCE_RECEIPT.read_text(encoding="utf-8"))
    return {item["path"]: item for item in receipt["files"]}


def source_record(path: Path, records: dict[str, dict[str, object]]) -> dict[str, object]:
    relative = str(path.relative_to(ROOT))
    require(relative in records, f"source is absent from frozen predecessor receipt: {relative}")
    record = records[relative]
    require(path.stat().st_size == record["size_bytes"], f"source size drift: {relative}")
    require(sha256_file(path) == record["sha256"], f"source digest drift: {relative}")
    return record


def choose_queries(excluded: set[str]) -> list[FastaRecord]:
    candidates: list[tuple[str, FastaRecord]] = []
    seen: set[str] = set()
    for record in iter_gzip_fasta(QUERY_SOURCE):
        if not QUERY_MIN_LENGTH <= len(record.sequence) <= QUERY_MAX_LENGTH:
            continue
        if set(record.sequence) > set("ACGT"):
            continue
        digest = sequence_sha256(record.sequence)
        if digest in excluded or digest in seen:
            continue
        seen.add(digest)
        rank = sha256_bytes(f"{SELECTION_SEED}\tquery\t{record.ordinal}\t{digest}".encode("ascii"))
        candidates.append((rank, record))
    candidates.sort(key=lambda item: item[0])
    require(len(candidates) >= WORKLOAD_COUNT, "insufficient fresh query candidates")
    return [record for _, record in candidates[:WORKLOAD_COUNT]]


def choose_target(chromosome: str, sequence: str, excluded: set[str]) -> tuple[int, str]:
    candidates = candidate_window_starts(sequence, TARGET_LENGTH)
    require(bool(candidates), f"no ACGT-only target window for {chromosome}")
    ranked = sorted(
        candidates,
        key=lambda start: sha256_bytes(
            f"{SELECTION_SEED}\ttarget\t{chromosome}\t{start}\t{TARGET_LENGTH}".encode("ascii")
        ),
    )
    for start in ranked:
        target = sequence[start : start + TARGET_LENGTH]
        digest = sequence_sha256(target)
        if digest not in excluded:
            return start, target
    raise InputFreezeError(f"all target candidates were previously used for {chromosome}")


def gc_fraction(sequence: str) -> str:
    return format((sequence.count("G") + sequence.count("C")) / len(sequence), ".12f")


def write_fasta(path: Path, header: str, sequence: str) -> None:
    with path.open("w", encoding="ascii", newline="\n") as handle:
        handle.write(f">{header}\n")
        for start in range(0, len(sequence), 80):
            handle.write(sequence[start : start + 80] + "\n")


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def freeze() -> dict[str, object]:
    for path in (ARTIFACT_ROOT, MANIFEST, EXCLUSION_RECEIPT):
        require(not path.exists(), f"Phase 3 input destination already exists: {path}")
    excluded, exclusion_counts = collect_excluded_digests()
    excluded_snapshot_sha256 = sha256_bytes(("\n".join(sorted(excluded)) + "\n").encode("ascii"))
    source_records = source_receipt_map()
    query_source_record = source_record(QUERY_SOURCE, source_records)
    queries = choose_queries(excluded)
    temporary = Path(tempfile.mkdtemp(prefix=".phase3-inputs.partial.", dir=ARTIFACT_ROOT.parent))
    rows: list[dict[str, str]] = []
    source_bindings: list[dict[str, object]] = [dict(query_source_record)]
    try:
        frozen_inputs = temporary / "frozen-inputs"
        frozen_inputs.mkdir(parents=True)
        used = set(excluded)
        for index, (chromosome, query) in enumerate(zip(CHROMOSOMES, queries, strict=True), 1):
            target_source = SOURCE_ROOT / "grch38-primary" / f"{chromosome}.fa.gz"
            target_source_record = source_record(target_source, source_records)
            source_bindings.append(dict(target_source_record))
            chromosome_sequence = read_gzip_chromosome(target_source, chromosome)
            target_start0, target = choose_target(chromosome, chromosome_sequence, used)
            workload_id = f"v2p4_w{index:03d}"
            destination = frozen_inputs / workload_id
            destination.mkdir()
            query_path = destination / "query.fa"
            target_path = destination / "target.fa"
            target_end0 = target_start0 + len(target)
            target_header = f"GRCh38|{chromosome}|{target_start0}-{target_end0}|v2_phase3_20mb_acgt_window"
            write_fasta(query_path, query.header, query.sequence)
            write_fasta(target_path, target_header, target)
            query_digest = sequence_sha256(query.sequence)
            target_digest = sequence_sha256(target)
            require(query_digest not in used and target_digest not in used, "selected input digest is not fresh")
            require(query_digest != target_digest, "query and target digest collision")
            used.update((query_digest, target_digest))
            rows.append(
                {
                    "workload_id": workload_id,
                    "selection_seed": SELECTION_SEED,
                    "query_ordinal_namespace": "gencode_v49_lncRNA_transcript_v2_phase3_v1",
                    "query_source_ordinal": str(query.ordinal),
                    "query_header": query.header,
                    "query_path": str((INPUT_ROOT / workload_id / "query.fa").relative_to(ROOT)),
                    "query_sequence_length": str(len(query.sequence)),
                    "query_sequence_sha256": query_digest,
                    "query_gc_fraction": gc_fraction(query.sequence),
                    "query_extraction_recipe_id": "gencode_v49_full_transcript_acgt_450_750_v1",
                    "target_ordinal_namespace": "grch38_v2_phase3_20mb_windows_v1",
                    "target_source_ordinal": chromosome,
                    "target_header": target_header,
                    "target_path": str((INPUT_ROOT / workload_id / "target.fa").relative_to(ROOT)),
                    "target_sequence_length": str(len(target)),
                    "target_sequence_sha256": target_digest,
                    "target_gc_fraction": gc_fraction(target),
                    "target_extraction_recipe_id": "deterministic_acgt_window_20000001_v1",
                    "assembly": "GRCh38",
                    "target_coordinate_namespace": "GRCh38_0_based_half_open",
                    "chromosome": chromosome,
                    "target_region_start0": str(target_start0),
                    "target_region_end0": str(target_end0),
                    "query_source_path": str(QUERY_SOURCE.relative_to(ROOT)),
                    "query_source_sha256": str(query_source_record["sha256"]),
                    "target_source_path": str(target_source.relative_to(ROOT)),
                    "target_source_sha256": str(target_source_record["sha256"]),
                    "fresh_against_exclusion_snapshot": "1",
                }
            )
        require(len(rows) == WORKLOAD_COUNT, "formal workload count drift")
        os.replace(temporary, ARTIFACT_ROOT)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    with MANIFEST.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=MANIFEST_FIELDS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    exclusion_receipt = {
        "schema_version": 1,
        "phase": 3,
        "selection_seed": SELECTION_SEED,
        "exclusion_scope": "all discoverable historical and development query/target FASTA inputs plus structured sequence digests; the Phase 3 output root is excluded",
        "excluded_digest_count": len(excluded),
        "excluded_digest_set_sha256": excluded_snapshot_sha256,
        "source_counts": exclusion_counts,
        "selected_query_digests_fresh": True,
        "selected_target_digests_fresh": True,
        "performance_or_prediction_outputs_inspected_for_selection": False,
    }
    write_json(EXCLUSION_RECEIPT, exclusion_receipt)
    generation_receipt = {
        "schema_version": 1,
        "phase": 3,
        "input_only": True,
        "prediction_executed": False,
        "selection_seed": SELECTION_SEED,
        "workload_count": len(rows),
        "query_length_range": [QUERY_MIN_LENGTH, QUERY_MAX_LENGTH],
        "target_length": TARGET_LENGTH,
        "chromosomes": list(CHROMOSOMES),
        "manifest_path": str(MANIFEST.relative_to(ROOT)),
        "manifest_sha256": sha256_file(MANIFEST),
        "exclusion_receipt_path": str(EXCLUSION_RECEIPT.relative_to(ROOT)),
        "exclusion_receipt_sha256": sha256_file(EXCLUSION_RECEIPT),
        "source_bindings": source_bindings,
    }
    write_json(ARTIFACT_ROOT / "input-generation-receipt.json", generation_receipt)
    return generation_receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze", action="store_true", required=True)
    parser.parse_args()
    try:
        receipt = freeze()
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, InputFreezeError) as error:
        print(f"Phase 3 input freeze failed: {error}")
        return 1
    print(json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
