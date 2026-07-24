#!/usr/bin/env python3
from __future__ import annotations

import gzip
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, TextIO


ROOT = Path(__file__).resolve().parents[2]
SELECTION_SEED = "gasal2-longtarget-phase3-application-v1-20260724"
ASSEMBLY = "GRCh38"
ANNOTATION_RELEASE = "GENCODE v49"
PRIMARY_CHROMOSOMES = {f"chr{i}" for i in range(1, 23)} | {"chrX"}
TARGET_CHROMOSOMES = ("chr21", "chr22")
MANIFEST_FIELDS = (
    "record_id",
    "record_role",
    "source_release",
    "assembly",
    "original_gene_id",
    "original_gene_name",
    "original_transcript_id",
    "selection_rule",
    "sequence_length",
    "chromosome",
    "strand",
    "tss",
    "region_start",
    "region_end",
    "sequence_sha256",
    "file_sha256",
    "path",
    "license_note",
    "split",
    "status",
)


@dataclass(frozen=True)
class Transcript:
    transcript_id: str
    gene_id: str
    gene_name: str
    gene_type: str
    chromosome: str
    start: int
    end: int
    strand: str
    level: int
    tags: frozenset[str]


def open_text(path: Path) -> TextIO:
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8", errors="strict", newline="")
    return path.open("r", encoding="utf-8", errors="strict", newline="")


def sha256_stream(stream: BinaryIO) -> str:
    digest = hashlib.sha256()
    for block in iter(lambda: stream.read(1024 * 1024), b""):
        digest.update(block)
    return digest.hexdigest()


def sha256_file(path: Path) -> str:
    with path.open("rb") as handle:
        return sha256_stream(handle)


def stable_id(value: str) -> str:
    return value.split(".", 1)[0]


def sequence_sha256(sequence: str) -> str:
    return hashlib.sha256(sequence.encode("ascii")).hexdigest()


def parse_attributes(text: str) -> dict[str, tuple[str, ...]]:
    attributes: dict[str, list[str]] = {}
    position = 0
    while position < len(text):
        while position < len(text) and text[position].isspace():
            position += 1
        if position == len(text):
            break

        key_start = position
        while position < len(text) and not text[position].isspace() and text[position] != ";":
            position += 1
        key = text[key_start:position]
        if not key or position == len(text) or text[position] == ";":
            raise ValueError(f"malformed GTF attributes: {text}")
        while position < len(text) and text[position].isspace():
            position += 1
        if position == len(text):
            raise ValueError(f"malformed GTF attributes: {text}")

        if text[position] == '"':
            value_start = position + 1
            value_end = text.find('"', value_start)
            if value_end < 0:
                raise ValueError(f"malformed GTF attributes: {text}")
            value = text[value_start:value_end]
            position = value_end + 1
            while position < len(text) and text[position].isspace():
                position += 1
            if position < len(text) and text[position] != ";":
                raise ValueError(f"malformed GTF attributes: {text}")
        else:
            value_start = position
            while position < len(text) and text[position] != ";":
                position += 1
            value = text[value_start:position].strip()
            if not value or any(character.isspace() for character in value):
                raise ValueError(f"malformed GTF attributes: {text}")

        attributes.setdefault(key, []).append(value)
        if position < len(text):
            position += 1

    return {key: tuple(values) for key, values in attributes.items()}


def parse_fasta(path: Path) -> list[tuple[str, str]]:
    records: list[tuple[str, str]] = []
    seen_headers: set[str] = set()
    header: str | None = None
    sequence_parts: list[str] = []

    def append_record() -> None:
        if header is None or not sequence_parts:
            raise ValueError(f"empty FASTA record in {path}")
        records.append((header, "".join(sequence_parts).upper()))

    with open_text(path) as handle:
        for raw in handle:
            line = raw.strip()
            if not line:
                continue
            if line.startswith(">"):
                if header is not None:
                    append_record()
                header = line[1:].strip()
                sequence_parts = []
                if not header:
                    raise ValueError(f"empty FASTA record in {path}")
                if header in seen_headers:
                    raise ValueError(f"duplicate FASTA header {header!r} in {path}")
                seen_headers.add(header)
            elif header is None:
                raise ValueError(f"sequence before FASTA header in {path}")
            else:
                sequence_parts.append(line)

    append_record()
    return records


def _required_attribute(
    attributes: dict[str, tuple[str, ...]],
    name: str,
    *,
    path: Path,
    line_number: int,
) -> str:
    values = attributes.get(name, ())
    if len(values) != 1 or not values[0].strip():
        raise ValueError(f"missing required GTF attribute {name} at row {line_number} in {path}")
    return values[0]


def parse_gtf(path: Path) -> dict[str, Transcript]:
    transcripts: dict[str, Transcript] = {}
    with open_text(path) as handle:
        for line_number, raw in enumerate(handle, 1):
            if raw.startswith("#"):
                continue
            fields = raw.rstrip("\r\n").split("\t")
            if len(fields) != 9:
                raise ValueError(
                    f"GTF row {line_number} in {path} must contain exactly 9 columns"
                )
            chromosome, _, feature, start_text, end_text, _, strand, _, attribute_text = fields
            try:
                start = int(start_text)
                end = int(end_text)
            except ValueError as error:
                raise ValueError(
                    f"invalid GTF coordinates at row {line_number} in {path}"
                ) from error
            if start <= 0 or end <= 0 or start > end:
                raise ValueError(f"invalid GTF coordinates at row {line_number} in {path}")
            if feature != "transcript":
                continue
            if strand not in {"+", "-"}:
                raise ValueError(f"invalid transcript strand at row {line_number} in {path}")

            attributes = parse_attributes(attribute_text)
            transcript_id = _required_attribute(
                attributes, "transcript_id", path=path, line_number=line_number
            )
            gene_id = _required_attribute(attributes, "gene_id", path=path, line_number=line_number)
            gene_name = _required_attribute(
                attributes, "gene_name", path=path, line_number=line_number
            )
            gene_type = _required_attribute(
                attributes, "gene_type", path=path, line_number=line_number
            )

            level_values = attributes.get("level", ())
            if not level_values:
                level = 99
            elif len(level_values) != 1 or not level_values[0].isdigit():
                raise ValueError(f"invalid GTF level at row {line_number} in {path}")
            else:
                level = int(level_values[0])

            transcript = Transcript(
                transcript_id=transcript_id,
                gene_id=gene_id,
                gene_name=gene_name,
                gene_type=gene_type,
                chromosome=chromosome,
                start=start,
                end=end,
                strand=strand,
                level=level,
                tags=frozenset(attributes.get("tag", ())),
            )
            existing = transcripts.get(transcript_id)
            if existing is not None and existing != transcript:
                raise ValueError(
                    f"duplicate transcript ID {transcript_id} has differing metadata in {path}"
                )
            transcripts[transcript_id] = transcript
    return transcripts
