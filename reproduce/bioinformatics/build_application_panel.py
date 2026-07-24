#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import fcntl
import gzip
import hashlib
import io
import json
import os
import stat
import sys
import threading
import zlib
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import BinaryIO, Callable, TextIO


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
DEVELOPMENT_EXCLUSION_FIELDS = ("exclusion_type", "value", "reason")
DEVELOPMENT_EXCLUSION_TYPES = ("gene_id", "gene_name", "sequence_sha256")
HOLDOUT_MANIFEST_FIELDS = (
    "workload_id",
    "query_id",
    "gene_id",
    "gene_name",
    "transcript_id",
    "query_length_nt",
    "length_stratum",
    "query_sequence_sha256",
    "query_file_sha256",
    "query_path",
    "target_id",
    "target_gene_id",
    "target_gene_name",
    "target_chromosome",
    "target_strand",
    "target_tss",
    "target_region_start",
    "target_region_end",
    "target_length_bp",
    "target_sequence_sha256",
    "target_file_sha256",
    "target_path",
    "assembly",
    "annotation_release",
    "selection_seed",
    "requested_contract",
    "run_modes",
    "repeat_count",
    "status",
)
HOLDOUT_QUERY_FIELDS = (
    "gene_id",
    "gene_name",
    "transcript_id",
    "query_length_nt",
    "length_stratum",
    "query_sequence_sha256",
    "query_file_sha256",
    "query_path",
)
QUERY_COUNT = 50
MIN_TARGET_COUNT = 300
MIN_QUERY_LENGTH = 500
MAX_QUERY_LENGTH = 2812
CANONICAL_BASES = frozenset("ACGT")
GENCODE_V49_IDENTITY_FIELDS = (
    "transcript ID",
    "gene ID",
    "Havana gene ID",
    "Havana transcript ID",
    "transcript name",
    "gene name",
)
COMMON = {
    "source_release": "GENCODE v49",
    "assembly": "GRCh38",
    "split": "application",
    "status": "preregistered_not_run",
}
QUERY_LICENSE = (
    "GENCODE project data are open access; selected derived FASTA retained with "
    "source attribution; final redistribution approval remains owner-controlled"
)
TARGET_LICENSE = (
    "UCSC data-use conditions and Genome Reference Consortium attribution apply; "
    "selected promoter FASTA retained; final redistribution approval remains owner-controlled"
)
SUMMARY_FIELDS = (
    "freeze_id",
    "manifest_sha256",
    "query_count",
    "target_count",
    "pair_count",
    "query_total_bp",
    "target_total_bp",
    "chr21_target_count",
    "chr22_target_count",
    "min_query_length",
    "max_query_length",
    "annotation_target_candidate_count",
    "excluded_target_count",
)
QUERY_SELECTION_RULE = (
    "GENCODE v49 lncRNA transcript on chr1-chr22 or chrX; canonical ACGT; 500-2812 nt; "
    "exclude development and Phase 2 holdout gene/sequence identities; one transcript per "
    "stable gene by level, basic tag, descending length, and transcript ID; first 50 by "
    "seeded SHA-256"
)
TARGET_SELECTION_RULE = (
    "GENCODE v49 protein-coding transcript on chr21 or chr22; one transcript per stable "
    "gene by MANE Select, Ensembl canonical, APPRIS principal, basic tag, level, descending "
    "length, and transcript ID; forward-genomic strand-aware TSS window -2000/+500; "
    "canonical ACGT"
)
FREEZE_ID_PREFIX = "bioinformatics-phase3-application-v1-"
APPLICATION_SOURCE_FIELDS = (
    "source_id",
    "role",
    "provider",
    "release",
    "assembly",
    "url",
    "upstream_md5",
    "compressed_size_bytes",
    "compressed_sha256",
    "decompressed_size_bytes",
    "decompressed_sha256",
    "local_source_path",
    "license_or_terms",
    "redistribution_note",
    "download_command",
    "status",
)
SOURCE_SPEC_FIELDS = APPLICATION_SOURCE_FIELDS[:-1]
_PUBLICATION_LOCK = threading.RLock()
_ROLLBACK_DESCRIPTOR_RESERVE_COUNT = 8


@dataclass(frozen=True)
class SourceSpec:
    source_id: str
    role: str
    provider: str
    release: str
    assembly: str
    url: str
    upstream_md5: str
    compressed_size_bytes: int
    compressed_sha256: str
    decompressed_size_bytes: int
    decompressed_sha256: str
    local_source_path: str
    license_or_terms: str
    redistribution_note: str
    download_command: str


SOURCE_SPECS = (
    SourceSpec(
        source_id="gencode_v49_lncrna",
        role="lncRNA transcript sequences",
        provider="GENCODE",
        release="v49",
        assembly="GRCh38.p14",
        url=(
            "https://ftp.ebi.ac.uk/pub/databases/gencode/Gencode_human/release_49/"
            "gencode.v49.lncRNA_transcripts.fa.gz"
        ),
        upstream_md5="6d52ea2c72933c864e46a560fe0b5d4c",
        compressed_size_bytes=37870043,
        compressed_sha256=(
            "1f04e509309fa74b694ef3cc1e52c1c8173bb0e679f8a22785fa43ecadd28ef4"
        ),
        decompressed_size_bytes=223740848,
        decompressed_sha256=(
            "4c632018e0198d76fe76471baa5511a1c07af86bf7bab6ce6747edb8d5add5ae"
        ),
        local_source_path=(
            ".tmp/bioinformatics_application_sources/"
            "gencode.v49.lncRNA_transcripts.fa.gz"
        ),
        license_or_terms="GENCODE project data are open access",
        redistribution_note=(
            "Selected small transcript FASTAs are retained with source attribution; "
            "final redistribution approval remains owner-controlled"
        ),
        download_command=(
            "curl -fL --retry 3 --output "
            ".tmp/bioinformatics_application_sources/"
            "gencode.v49.lncRNA_transcripts.fa.gz.partial.$$ "
            "https://ftp.ebi.ac.uk/pub/databases/gencode/Gencode_human/release_49/"
            "gencode.v49.lncRNA_transcripts.fa.gz"
        ),
    ),
    SourceSpec(
        source_id="gencode_v49_gtf",
        role="gene and transcript annotation",
        provider="GENCODE",
        release="v49",
        assembly="GRCh38.p14",
        url=(
            "https://ftp.ebi.ac.uk/pub/databases/gencode/Gencode_human/release_49/"
            "gencode.v49.annotation.gtf.gz"
        ),
        upstream_md5="0ef4a024ea2d35b1b88c12447b0b70b9",
        compressed_size_bytes=93374019,
        compressed_sha256=(
            "d6e6fe0515c95b2a8cd36a853c1989cee9115c736c60237c56ae92b9daaaf7c4"
        ),
        decompressed_size_bytes=3323462848,
        decompressed_sha256=(
            "ff32fd55c6799b3b94fe10aa17b2b5d4da952fa1de12fe44afadf32e949ec914"
        ),
        local_source_path=(
            ".tmp/bioinformatics_application_sources/gencode.v49.annotation.gtf.gz"
        ),
        license_or_terms="GENCODE project data are open access",
        redistribution_note=(
            "Annotation is downloaded for reconstruction and is not redistributed "
            "in this repository"
        ),
        download_command=(
            "curl -fL --retry 3 --output "
            ".tmp/bioinformatics_application_sources/"
            "gencode.v49.annotation.gtf.gz.partial.$$ "
            "https://ftp.ebi.ac.uk/pub/databases/gencode/Gencode_human/release_49/"
            "gencode.v49.annotation.gtf.gz"
        ),
    ),
    SourceSpec(
        source_id="ucsc_hg38_chr21",
        role="forward genomic reference sequence",
        provider="UCSC Genome Browser / Genome Reference Consortium",
        release="hg38 2014-01-23",
        assembly="GRCh38",
        url=(
            "https://hgdownload.soe.ucsc.edu/goldenPath/hg38/chromosomes/chr21.fa.gz"
        ),
        upstream_md5="184df2bd9b812b6e6b6da16c6021369e",
        compressed_size_bytes=12709705,
        compressed_sha256=(
            "c979ca1e5065c2521a50773473e0d0cc018fd6f3e9bb3aa90493fe7b45d57d1b"
        ),
        decompressed_size_bytes=47644190,
        decompressed_sha256=(
            "35c71b68436d1a278ecb6a1e875af3ba4020738a028a7feac769a6d62790ae1f"
        ),
        local_source_path=".tmp/bioinformatics_application_sources/chr21.fa.gz",
        license_or_terms=(
            "UCSC data-use conditions and Genome Reference Consortium attribution apply"
        ),
        redistribution_note=(
            "Only selected promoter sequences are retained; final redistribution "
            "approval remains owner-controlled"
        ),
        download_command=(
            "curl -fL --retry 3 --output "
            ".tmp/bioinformatics_application_sources/chr21.fa.gz.partial.$$ "
            "https://hgdownload.soe.ucsc.edu/goldenPath/hg38/chromosomes/chr21.fa.gz"
        ),
    ),
    SourceSpec(
        source_id="ucsc_hg38_chr22",
        role="forward genomic reference sequence",
        provider="UCSC Genome Browser / Genome Reference Consortium",
        release="hg38 2014-01-23",
        assembly="GRCh38",
        url=(
            "https://hgdownload.soe.ucsc.edu/goldenPath/hg38/chromosomes/chr22.fa.gz"
        ),
        upstream_md5="41b47ce1cc21b558409c19b892e1c0d1",
        compressed_size_bytes=12255678,
        compressed_sha256=(
            "05f9d97d6fbfd08a44ca45b50837ca2ae9c471f35ba79dffec04d2cb5eaaf695"
        ),
        decompressed_size_bytes=51834845,
        decompressed_sha256=(
            "ce3ee1ca39356238f7aee438a40a88b4f1b9d80b316b263e16fb12402212d10f"
        ),
        local_source_path=".tmp/bioinformatics_application_sources/chr22.fa.gz",
        license_or_terms=(
            "UCSC data-use conditions and Genome Reference Consortium attribution apply"
        ),
        redistribution_note=(
            "Only selected promoter sequences are retained; final redistribution "
            "approval remains owner-controlled"
        ),
        download_command=(
            "curl -fL --retry 3 --output "
            ".tmp/bioinformatics_application_sources/chr22.fa.gz.partial.$$ "
            "https://hgdownload.soe.ucsc.edu/goldenPath/hg38/chromosomes/chr22.fa.gz"
        ),
    ),
)
_BIOLOGICAL_SOURCE_BINDINGS = (
    ("gencode_v49_lncrna", "lncrna_fasta", "lncRNA transcript sequences"),
    ("gencode_v49_gtf", "annotation_gtf", "gene and transcript annotation"),
    (
        "ucsc_hg38_chr21",
        "chr21_fasta",
        "forward genomic reference sequence",
    ),
    (
        "ucsc_hg38_chr22",
        "chr22_fasta",
        "forward genomic reference sequence",
    ),
)


@dataclass(frozen=True)
class _VerifiedSourceSpecs:
    specs: tuple[SourceSpec, ...]


@dataclass(frozen=True)
class SourceInputs:
    lncrna_fasta: Path
    annotation_gtf: Path
    chr21_fasta: Path
    chr22_fasta: Path
    development_exclusions: Path
    holdout_manifest: Path
    source_specs: tuple[SourceSpec, ...]


@dataclass(frozen=True)
class FreezePaths:
    repository_root: Path
    selection_receipt: Path
    application_inputs: Path
    manifest: Path
    manifest_checksum: Path
    source_ledger: Path
    input_summary: Path


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


@dataclass
class _SourceSnapshot:
    path: Path
    descriptor: int | None
    identity: tuple[int, int, int, int, int]
    component_chain: tuple[tuple[int, int], ...]
    md5: str
    sha256: str
    size_bytes: int

    def __str__(self) -> str:
        return str(self.path)

    def verify_descriptor(self) -> int:
        if self.descriptor is None:
            raise ValueError(f"source descriptor is closed: {self.path}")
        metadata = os.fstat(self.descriptor)
        if _file_identity(metadata) != self.identity:
            raise ValueError(f"source changed during reconstruction: {self.path}")
        return self.descriptor

    def close(self) -> None:
        if self.descriptor is not None:
            descriptor = self.descriptor
            metadata = os.fstat(descriptor)
            if (metadata.st_dev, metadata.st_ino) != self.identity[:2]:
                raise ValueError(f"source descriptor identity changed: {self.path}")
            self.descriptor = None
            os.close(descriptor)


@contextmanager
def open_text(path: Path | _SourceSnapshot) -> Iterator[TextIO]:
    if isinstance(path, _SourceSnapshot):
        descriptor = path.verify_descriptor()
        _verify_source_snapshot_path(path)
        os.lseek(descriptor, 0, os.SEEK_SET)
        duplicate = os.dup(descriptor)
        binary = os.fdopen(duplicate, "rb", closefd=True)
        compressed: gzip.GzipFile | None = None
        text: TextIO | None = None
        try:
            raw: BinaryIO = binary
            if path.path.suffix == ".gz":
                compressed = gzip.GzipFile(fileobj=binary, mode="rb")
                raw = compressed
            text = io.TextIOWrapper(
                raw,
                encoding="utf-8",
                errors="strict",
                newline="",
            )
            yield text
        finally:
            if text is not None:
                text.close()
            elif compressed is not None:
                compressed.close()
            if not binary.closed:
                binary.close()
            path.verify_descriptor()
            _verify_source_snapshot_path(path)
        return
    if path.suffix == ".gz":
        with gzip.open(
            path,
            "rt",
            encoding="utf-8",
            errors="strict",
            newline="",
        ) as handle:
            yield handle
        return
    with path.open("r", encoding="utf-8", errors="strict", newline="") as handle:
        yield handle


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


def _iter_fasta_records(
    path: Path | _SourceSnapshot,
) -> Iterator[tuple[str, str]]:
    seen_headers: set[str] = set()
    header: str | None = None
    sequence_parts: list[str] = []

    def record() -> tuple[str, str]:
        if header is None or not sequence_parts:
            raise ValueError(f"empty FASTA record in {path}")
        return header, "".join(sequence_parts).upper()

    with open_text(path) as handle:
        for raw in handle:
            line = raw.rstrip("\r\n")
            if not line.strip():
                continue
            if line.startswith(">"):
                if header is not None:
                    yield record()
                header = line[1:]
                sequence_parts = []
                if not header.strip():
                    raise ValueError(f"empty FASTA record in {path}")
                if header in seen_headers:
                    raise ValueError(f"duplicate FASTA header {header!r} in {path}")
                seen_headers.add(header)
            elif header is None:
                raise ValueError(f"sequence before FASTA header in {path}")
            else:
                sequence_parts.append(line.strip())

    yield record()


def parse_fasta(path: Path) -> list[tuple[str, str]]:
    return list(_iter_fasta_records(path))


def read_chromosome_fasta(path: Path, requested_chromosome: str) -> str:
    if requested_chromosome not in TARGET_CHROMOSOMES:
        raise ValueError(f"unsupported requested target chromosome {requested_chromosome!r}")
    records = parse_fasta(path)
    if len(records) != 1:
        raise ValueError(f"chromosome source must contain exactly one FASTA record: {path}")
    header, sequence = records[0]
    if header != requested_chromosome:
        raise ValueError(
            f"chromosome FASTA record must be named exactly {requested_chromosome!r}: {path}"
        )
    return sequence


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
            elif len(level_values) != 1 or level_values[0] not in {"1", "2", "3"}:
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


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and all(character in "0123456789abcdef" for character in value)


def read_development_exclusions(path: Path) -> dict[str, set[str]]:
    exclusions = {exclusion_type: set() for exclusion_type in DEVELOPMENT_EXCLUSION_TYPES}
    with open_text(path) as handle:
        reader = csv.reader(handle, delimiter="\t")
        try:
            header = next(reader)
        except StopIteration as error:
            raise ValueError(
                "development exclusions must have exclusion_type, value and reason columns"
            ) from error
        if tuple(header) != DEVELOPMENT_EXCLUSION_FIELDS:
            raise ValueError(
                "development exclusions must have exclusion_type, value and reason columns"
            )
        for line_number, row in enumerate(reader, 2):
            if len(row) != len(DEVELOPMENT_EXCLUSION_FIELDS):
                raise ValueError(f"malformed development exclusion row {line_number} in {path}")
            exclusion_type, value, reason = row
            if exclusion_type not in exclusions:
                raise ValueError(
                    f"unsupported development exclusion type {exclusion_type!r} "
                    f"at row {line_number} in {path}"
                )
            if (
                not value
                or value != value.strip()
                or not reason
                or reason != reason.strip()
            ):
                raise ValueError(f"malformed development exclusion row {line_number} in {path}")
            if exclusion_type == "sequence_sha256" and not _is_sha256(value):
                raise ValueError(f"malformed development exclusion row {line_number} in {path}")
            normalized_value = stable_id(value) if exclusion_type == "gene_id" else value
            if not normalized_value:
                raise ValueError(f"malformed development exclusion row {line_number} in {path}")
            exclusions[exclusion_type].add(normalized_value)
    return exclusions


def read_holdout_exclusions(path: Path) -> tuple[set[str], set[str]]:
    gene_ids: set[str] = set()
    sequence_digests: set[str] = set()
    queries: dict[str, tuple[str, ...]] = {}
    gene_owners: dict[str, str] = {}
    digest_owners: dict[str, str] = {}
    with open_text(path) as handle:
        reader = csv.reader(handle, delimiter="\t")
        try:
            header = next(reader)
        except StopIteration as error:
            raise ValueError("holdout manifest has the wrong columns") from error
        if tuple(header) != HOLDOUT_MANIFEST_FIELDS:
            raise ValueError("holdout manifest has the wrong columns")
        row_count = 0
        for line_number, values in enumerate(reader, 2):
            row_count += 1
            if len(values) != len(HOLDOUT_MANIFEST_FIELDS) or any(not value for value in values):
                raise ValueError(f"malformed holdout manifest row {line_number} in {path}")
            for field, value in zip(HOLDOUT_MANIFEST_FIELDS, values, strict=True):
                if value != value.strip():
                    raise ValueError(
                        f"whitespace-padded holdout manifest field {field!r} "
                        f"at row {line_number} in {path}"
                    )
            row = dict(zip(HOLDOUT_MANIFEST_FIELDS, values, strict=True))
            gene_id = stable_id(row["gene_id"])
            query_id = row["query_id"]
            sequence_digest = row["query_sequence_sha256"]
            if not gene_id or not _is_sha256(sequence_digest):
                raise ValueError(f"malformed holdout manifest row {line_number} in {path}")
            if not _is_sha256(row["query_file_sha256"]):
                raise ValueError(
                    f"malformed query_file_sha256 at holdout manifest row "
                    f"{line_number} in {path}"
                )
            identity = tuple(row[field] for field in HOLDOUT_QUERY_FIELDS)
            existing = queries.get(query_id)
            if existing is not None and existing != identity:
                raise ValueError(f"conflicting holdout query {query_id!r} in {path}")
            gene_owner = gene_owners.get(gene_id)
            if gene_owner is not None and gene_owner != query_id:
                raise ValueError(
                    f"stable gene ID {gene_id!r} belongs to multiple holdout queries in {path}"
                )
            digest_owner = digest_owners.get(sequence_digest)
            if digest_owner is not None and digest_owner != query_id:
                raise ValueError(
                    f"query sequence digest {sequence_digest!r} belongs to multiple "
                    f"holdout queries in {path}"
                )
            queries[query_id] = identity
            gene_owners[gene_id] = query_id
            digest_owners[sequence_digest] = query_id
            gene_ids.add(gene_id)
            sequence_digests.add(sequence_digest)
    if row_count == 0:
        raise ValueError(f"holdout manifest has no rows: {path}")
    return gene_ids, sequence_digests


def target_representative_key(tx: Transcript) -> tuple[object, ...]:
    tags = tx.tags
    return (
        0 if "MANE_Select" in tags else 1,
        0 if "Ensembl_canonical" in tags else 1,
        0 if "appris_principal_1" in tags else 1,
        0 if any(tag.startswith("appris_principal") for tag in tags) else 1,
        0 if "basic" in tags else 1,
        tx.level,
        -(tx.end - tx.start + 1),
        tx.transcript_id,
    )


def choose_target_representative(transcripts: Iterable[Transcript]) -> Transcript:
    try:
        iterator = iter(transcripts)
        representative = next(iterator)
    except StopIteration as error:
        raise ValueError("no target candidates for stable gene") from error
    representative_key = target_representative_key(representative)
    for transcript in iterator:
        key = target_representative_key(transcript)
        if key < representative_key:
            representative = transcript
            representative_key = key
    return representative


def promoter_bounds(tx: Transcript, chromosome_length: int) -> tuple[int, int, int]:
    tss = tx.start if tx.strand == "+" else tx.end
    start = max(1, tss - (2000 if tx.strand == "+" else 500))
    end = min(chromosome_length, tss + (500 if tx.strand == "+" else 2000))
    return tss, start, end


def materialize_promoter(
    tx: Transcript,
    chromosome_sequence: str,
) -> dict[str, object]:
    tss, start, end = promoter_bounds(tx, len(chromosome_sequence))
    if 1 <= tss <= len(chromosome_sequence):
        sequence = chromosome_sequence[start - 1 : end]
    else:
        start = 0
        end = 0
        sequence = ""
    return {
        "transcript_id": tx.transcript_id,
        "gene_id": tx.gene_id,
        "gene_name": tx.gene_name,
        "chromosome": tx.chromosome,
        "strand": tx.strand,
        "tss": tss,
        "region_start": start,
        "region_end": end,
        "sequence_length": len(sequence),
        "sequence": sequence,
    }


def _validated_target_candidates(
    transcripts: dict[str, Transcript],
) -> dict[str, list[Transcript]]:
    if not isinstance(transcripts, dict):
        raise ValueError("transcripts must be a mapping keyed by full transcript ID")

    candidates_by_gene: dict[str, list[Transcript]] = {}
    stable_transcript_ids: set[str] = set()
    gene_identities: dict[str, tuple[str, str, str, str, str]] = {}
    for mapping_key, tx in transcripts.items():
        if not isinstance(tx, Transcript):
            raise ValueError(f"transcript mapping value for {mapping_key!r} is not a Transcript")
        if mapping_key != tx.transcript_id:
            raise ValueError(
                f"transcript mapping key {mapping_key!r} does not match {tx.transcript_id!r}"
            )
        identity_values = (
            tx.transcript_id,
            tx.gene_id,
            tx.gene_name,
            tx.gene_type,
            tx.chromosome,
        )
        if any(
            not isinstance(value, str) or not value or value != value.strip()
            for value in identity_values
        ):
            raise ValueError(f"malformed transcript identity for {mapping_key!r}")
        if type(tx.strand) is not str or tx.strand not in {"+", "-"}:
            raise ValueError("target transcript strand must be '+' or '-'")
        if type(tx.level) is not int or tx.level not in {1, 2, 3, 99}:
            raise ValueError("target transcript level must be one of 1, 2, 3, 99")
        if (
            type(tx.start) is not int
            or type(tx.end) is not int
            or tx.start <= 0
            or tx.end < tx.start
            or not isinstance(tx.tags, frozenset)
            or any(
                not isinstance(tag, str) or not tag or tag != tag.strip()
                for tag in tx.tags
            )
        ):
            raise ValueError(f"malformed transcript metadata for {mapping_key!r}")

        stable_transcript_id = stable_id(tx.transcript_id)
        stable_gene_id = stable_id(tx.gene_id)
        if not stable_transcript_id or not stable_gene_id:
            raise ValueError(f"blank stable identifier for {mapping_key!r}")
        if stable_transcript_id in stable_transcript_ids:
            raise ValueError(f"duplicate stable transcript ID {stable_transcript_id!r}")
        stable_transcript_ids.add(stable_transcript_id)

        gene_identity = (
            tx.gene_id,
            tx.gene_name,
            tx.gene_type,
            tx.chromosome,
            tx.strand,
        )
        existing_identity = gene_identities.get(stable_gene_id)
        if existing_identity is not None and existing_identity != gene_identity:
            raise ValueError(
                f"stable gene ID {stable_gene_id!r} has conflicting identity"
            )
        gene_identities[stable_gene_id] = gene_identity

        if tx.gene_type == "protein_coding" and tx.chromosome in TARGET_CHROMOSOMES:
            candidates_by_gene.setdefault(stable_gene_id, []).append(tx)
    return candidates_by_gene


def _select_targets_streaming(
    *,
    transcripts: dict[str, Transcript],
    chromosome_sequence: Callable[[str], str],
) -> tuple[list[dict[str, object]], dict[str, int]]:
    candidates_by_gene = _validated_target_candidates(transcripts)
    representatives = [
        choose_target_representative(candidates)
        for candidates in candidates_by_gene.values()
    ]
    counts = {
        "annotation_target_candidate_count": len(representatives),
        "retained_target_count": 0,
        "excluded_target_count": 0,
        "excluded_empty_promoter_count": 0,
        "excluded_noncanonical_promoter_count": 0,
        "chr21_annotation_target_candidate_count": 0,
        "chr22_annotation_target_candidate_count": 0,
        "chr21_retained_target_count": 0,
        "chr22_retained_target_count": 0,
        "chr21_excluded_target_count": 0,
        "chr22_excluded_target_count": 0,
    }
    retained: list[dict[str, object]] = []
    for chromosome in TARGET_CHROMOSOMES:
        chromosome_content = chromosome_sequence(chromosome)
        if not isinstance(chromosome_content, str) or not chromosome_content:
            raise ValueError(f"{chromosome} chromosome sequence must be a non-empty string")
        for tx in representatives:
            if tx.chromosome != chromosome:
                continue
            counts[f"{chromosome}_annotation_target_candidate_count"] += 1
            target = materialize_promoter(tx, chromosome_content)
            sequence = str(target["sequence"])
            if not sequence:
                counts["excluded_empty_promoter_count"] += 1
                counts[f"{chromosome}_excluded_target_count"] += 1
                continue
            if set(sequence) - CANONICAL_BASES:
                counts["excluded_noncanonical_promoter_count"] += 1
                counts[f"{chromosome}_excluded_target_count"] += 1
                continue
            target["sequence_sha256"] = sequence_sha256(sequence)
            retained.append(target)
            counts[f"{chromosome}_retained_target_count"] += 1

    counts["retained_target_count"] = len(retained)
    counts["excluded_target_count"] = (
        counts["excluded_empty_promoter_count"]
        + counts["excluded_noncanonical_promoter_count"]
    )
    if len(retained) < MIN_TARGET_COUNT:
        raise ValueError(
            f"only {len(retained)} retained targets; {MIN_TARGET_COUNT} required"
        )
    for chromosome in TARGET_CHROMOSOMES:
        if counts[f"{chromosome}_retained_target_count"] == 0:
            raise ValueError(f"no retained target on {chromosome}")

    retained.sort(
        key=lambda row: (
            int(str(row["chromosome"])[3:]),
            int(row["tss"]),
            stable_id(str(row["gene_id"])),
            str(row["transcript_id"]),
        )
    )
    stable_target_gene_ids = {stable_id(str(row["gene_id"])) for row in retained}
    if len(stable_target_gene_ids) != len(retained):
        raise ValueError("retained targets must contain unique stable genes")
    for index, target in enumerate(retained, 1):
        target["target_id"] = f"at{index:04d}"
    return retained, counts


def select_targets(
    *,
    transcripts: dict[str, Transcript],
    chromosome_sequences: dict[str, str],
) -> tuple[list[dict[str, object]], dict[str, int]]:
    if not isinstance(chromosome_sequences, dict) or set(chromosome_sequences) != set(
        TARGET_CHROMOSOMES
    ):
        raise ValueError("chromosome sequences must contain exactly chr21 and chr22")
    return _select_targets_streaming(
        transcripts=transcripts,
        chromosome_sequence=lambda chromosome: chromosome_sequences[chromosome],
    )


def query_representative_key(row: dict[str, object]) -> tuple[object, ...]:
    basic = row["basic"]
    if type(basic) is not bool:
        raise ValueError("query representative basic must be bool")
    return (
        int(row["level"]),
        0 if basic else 1,
        -int(row["sequence_length"]),
        str(row["transcript_id"]),
    )


def choose_query_representative(rows: Iterable[dict[str, object]]) -> dict[str, object]:
    try:
        iterator = iter(rows)
        representative = next(iterator)
    except StopIteration as error:
        raise ValueError("no query candidates for stable gene") from error
    representative_key = query_representative_key(representative)
    for row in iterator:
        row_key = query_representative_key(row)
        if row_key < representative_key:
            representative = row
            representative_key = row_key
    return representative


def query_selection_hash(row: dict[str, object]) -> str:
    payload = "|".join(
        (
            SELECTION_SEED,
            stable_id(str(row["gene_id"])),
            stable_id(str(row["transcript_id"])),
            str(row["sequence_sha256"]),
        )
    )
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def _select_queries_streaming(
    *,
    fasta_records: Iterable[tuple[str, str]],
    transcripts: dict[str, Transcript],
    development_exclusions: dict[str, set[str]],
    holdout_gene_ids: set[str],
    holdout_sequence_sha256: set[str],
) -> tuple[list[dict[str, object]], dict[str, int], dict[str, str]]:
    if set(development_exclusions) != set(DEVELOPMENT_EXCLUSION_TYPES):
        raise ValueError("development exclusions must contain the three supported types")

    counts = {
        "input_query_record_count": 0,
        "validated_query_candidate_count": 0,
        "eligible_query_transcript_count": 0,
        "representative_query_count": 0,
        "selected_query_count": 0,
        "excluded_missing_gtf_metadata_count": 0,
        "excluded_non_lncRNA_count": 0,
        "excluded_non_primary_chromosome_count": 0,
        "excluded_noncanonical_sequence_count": 0,
        "excluded_query_length_count": 0,
        "excluded_development_gene_id_count": 0,
        "excluded_development_gene_name_count": 0,
        "excluded_development_sequence_sha256_count": 0,
        "excluded_holdout_gene_id_count": 0,
        "excluded_holdout_sequence_sha256_count": 0,
    }
    representatives_by_gene: dict[str, dict[str, object]] = {}
    representative_sequences: dict[str, str] = {}
    biological_transcript_ids: set[str] = set()
    stable_transcript_ids: set[str] = set()

    for header, sequence in fasta_records:
        counts["input_query_record_count"] += 1
        parts = header.split("|")
        if len(parts) != 8 or parts[7] != "":
            raise ValueError(f"unsupported GENCODE v49 FASTA header: {header}")
        for field, value in zip(GENCODE_V49_IDENTITY_FIELDS, parts[:6], strict=True):
            if not value or value != value.strip():
                raise ValueError(
                    f"invalid GENCODE v49 FASTA identity field {field}: {header}"
                )
        transcript_id, gene_id = parts[0], parts[1]
        if transcript_id in biological_transcript_ids:
            raise ValueError(f"duplicate biological transcript ID {transcript_id!r}")
        biological_transcript_ids.add(transcript_id)
        stable_transcript_id = stable_id(transcript_id)
        if not stable_transcript_id:
            raise ValueError(f"blank stable transcript ID in GENCODE FASTA header: {header}")
        if stable_transcript_id in stable_transcript_ids:
            raise ValueError(f"duplicate stable transcript ID {stable_transcript_id!r}")
        stable_transcript_ids.add(stable_transcript_id)

        declared_length_text = parts[6]
        if not declared_length_text.isdigit():
            raise ValueError(f"GENCODE FASTA declared length is not numeric: {header}")
        declared_length = int(declared_length_text)
        if declared_length != len(sequence):
            raise ValueError(
                f"GENCODE FASTA declared length {declared_length} does not match "
                f"sequence length {len(sequence)} for {transcript_id}"
            )

        metadata = transcripts.get(transcript_id)
        if metadata is None:
            counts["excluded_missing_gtf_metadata_count"] += 1
            continue
        if metadata.transcript_id != transcript_id:
            raise ValueError(f"GTF metadata transcript mismatch for {transcript_id}")
        if metadata.gene_id != gene_id:
            raise ValueError(f"GENCODE FASTA/GTF gene mismatch for {transcript_id}")
        if metadata.gene_name != parts[5]:
            raise ValueError(f"GENCODE FASTA/GTF gene name mismatch for {transcript_id}")

        if metadata.gene_type != "lncRNA":
            counts["excluded_non_lncRNA_count"] += 1
            continue
        if metadata.chromosome not in PRIMARY_CHROMOSOMES:
            counts["excluded_non_primary_chromosome_count"] += 1
            continue
        if set(sequence) - CANONICAL_BASES:
            counts["excluded_noncanonical_sequence_count"] += 1
            continue
        if not MIN_QUERY_LENGTH <= len(sequence) <= MAX_QUERY_LENGTH:
            counts["excluded_query_length_count"] += 1
            continue

        stable_gene_id = stable_id(gene_id)
        if not stable_gene_id or not stable_transcript_id:
            raise ValueError(f"blank stable identifier in GENCODE FASTA header: {header}")
        digest = sequence_sha256(sequence)
        counts["validated_query_candidate_count"] += 1
        if stable_gene_id in development_exclusions["gene_id"]:
            counts["excluded_development_gene_id_count"] += 1
            continue
        if metadata.gene_name in development_exclusions["gene_name"]:
            counts["excluded_development_gene_name_count"] += 1
            continue
        if digest in development_exclusions["sequence_sha256"]:
            counts["excluded_development_sequence_sha256_count"] += 1
            continue
        if stable_gene_id in holdout_gene_ids:
            counts["excluded_holdout_gene_id_count"] += 1
            continue
        if digest in holdout_sequence_sha256:
            counts["excluded_holdout_sequence_sha256_count"] += 1
            continue

        candidate: dict[str, object] = {
            "transcript_id": transcript_id,
            "gene_id": gene_id,
            "gene_name": metadata.gene_name,
            "chromosome": metadata.chromosome,
            "level": metadata.level,
            "basic": "basic" in metadata.tags,
            "sequence_length": len(sequence),
            "sequence_sha256": digest,
        }
        representative = representatives_by_gene.get(stable_gene_id)
        if (
            representative is None
            or query_representative_key(candidate)
            < query_representative_key(representative)
        ):
            representatives_by_gene[stable_gene_id] = candidate
            representative_sequences[stable_gene_id] = sequence
        counts["eligible_query_transcript_count"] += 1

    representatives = list(representatives_by_gene.values())
    counts["representative_query_count"] = len(representatives)
    if len(representatives) < QUERY_COUNT:
        raise ValueError(
            f"only {len(representatives)} eligible stable genes; {QUERY_COUNT} required"
        )

    ordered = [
        {**row, "selection_hash": query_selection_hash(row)} for row in representatives
    ]
    ordered.sort(
        key=lambda row: (
            str(row["selection_hash"]),
            stable_id(str(row["gene_id"])),
            str(row["transcript_id"]),
        )
    )
    selected = ordered[:QUERY_COUNT]
    selected_gene_ids = {stable_id(str(row["gene_id"])) for row in selected}
    if len(selected_gene_ids) != QUERY_COUNT:
        raise ValueError(f"selected queries must contain {QUERY_COUNT} unique stable genes")
    selected_sequence_digests = {str(row["sequence_sha256"]) for row in selected}
    if len(selected_sequence_digests) != QUERY_COUNT:
        raise ValueError("selected query sequence digests must be unique")
    for index, row in enumerate(selected, 1):
        row["query_id"] = f"aq{index:03d}"
    counts["selected_query_count"] = len(selected)
    selected_sequences = {
        str(row["transcript_id"]): representative_sequences[
            stable_id(str(row["gene_id"]))
        ]
        for row in selected
    }
    return selected, counts, selected_sequences


def select_queries(
    *,
    fasta_records: Iterable[tuple[str, str]],
    transcripts: dict[str, Transcript],
    development_exclusions: dict[str, set[str]],
    holdout_gene_ids: set[str],
    holdout_sequence_sha256: set[str],
) -> tuple[list[dict[str, object]], dict[str, int]]:
    selected, counts, _sequences = _select_queries_streaming(
        fasta_records=fasta_records,
        transcripts=transcripts,
        development_exclusions=development_exclusions,
        holdout_gene_ids=holdout_gene_ids,
        holdout_sequence_sha256=holdout_sequence_sha256,
    )
    return selected, counts


@dataclass(frozen=True)
class _FreezeModel:
    application_files: dict[str, bytes]
    selection_receipt_bytes: bytes
    manifest_bytes: bytes
    manifest_checksum_bytes: bytes
    source_ledger_bytes: bytes
    input_summary_bytes: bytes
    result: dict[str, object]


def _canonical_json_bytes(payload: dict[str, object]) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("ascii")


def _tsv_bytes(
    fieldnames: tuple[str, ...],
    rows: Iterable[dict[str, object]],
) -> bytes:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(
        buffer,
        fieldnames=fieldnames,
        delimiter="\t",
        lineterminator="\n",
        extrasaction="raise",
    )
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")


def _source_spec_rows(
    source_specs: tuple[SourceSpec, ...],
) -> list[dict[str, object]]:
    return [
        {
            field_name: getattr(source, field_name)
            for field_name in SOURCE_SPEC_FIELDS
        }
        for source in source_specs
    ]


def _verified_application_source_rows(
    verified_sources: _VerifiedSourceSpecs,
) -> list[dict[str, object]]:
    if not isinstance(verified_sources, _VerifiedSourceSpecs):
        raise ValueError("application source ledger requires verified source specs")
    return [
        {**row, "status": "verified"}
        for row in _source_spec_rows(verified_sources.specs)
    ]


def _fasta_bytes(header: str, sequence: str) -> bytes:
    if not header or any(character in header for character in "\r\n\t"):
        raise ValueError("FASTA header contains an invalid control character")
    if not sequence or set(sequence) - CANONICAL_BASES:
        raise ValueError("published FASTA sequence must be non-empty canonical ACGT")
    lines = [f">{header}"]
    lines.extend(sequence[index : index + 80] for index in range(0, len(sequence), 80))
    return ("\n".join(lines) + "\n").encode("ascii")


def _path_exists_no_follow(path: Path) -> bool:
    return os.path.lexists(path)


def _file_identity(metadata: os.stat_result) -> tuple[int, int, int, int, int]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    )


def _open_file_and_chain_by_no_follow_walk(
    path: Path,
    flags: int,
) -> tuple[int, tuple[tuple[int, int], ...]]:
    if not path.is_absolute() or ".." in path.parts or len(path.parts) < 2:
        raise ValueError(f"file path must be absolute without '..': {path}")
    directory_flags = (
        os.O_RDONLY
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    directory = os.open(path.anchor, directory_flags)
    root_metadata = os.fstat(directory)
    chain = [(root_metadata.st_dev, root_metadata.st_ino)]
    try:
        for component in path.parts[1:-1]:
            child = os.open(component, directory_flags, dir_fd=directory)
            os.close(directory)
            directory = child
            metadata = os.fstat(directory)
            chain.append((metadata.st_dev, metadata.st_ino))
        descriptor = os.open(
            path.parts[-1],
            flags | getattr(os, "O_NOFOLLOW", 0),
            dir_fd=directory,
        )
        metadata = os.fstat(descriptor)
        chain.append((metadata.st_dev, metadata.st_ino))
        return descriptor, tuple(chain)
    finally:
        os.close(directory)


def _read_regular_file_no_follow(path: Path) -> bytes:
    try:
        try:
            descriptor, _ = _open_file_and_chain_by_no_follow_walk(
                path,
                os.O_RDONLY | getattr(os, "O_NOATIME", 0),
            )
        except PermissionError:
            descriptor, _ = _open_file_and_chain_by_no_follow_walk(path, os.O_RDONLY)
    except OSError as error:
        raise ValueError(
            f"cannot open regular file without following links: {path}"
        ) from error
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise ValueError(f"expected regular file: {path}")
        chunks: list[bytes] = []
        while block := os.read(descriptor, 1024 * 1024):
            chunks.append(block)
        content = b"".join(chunks)
        after = os.fstat(descriptor)
        if _file_identity(after) != _file_identity(before) or len(content) != before.st_size:
            raise ValueError(f"regular file changed while it was read: {path}")
        return content
    finally:
        os.close(descriptor)


def _path_identity_chain_without_opening_file(
    path: Path,
) -> tuple[tuple[tuple[int, int], ...], tuple[int, int, int, int, int]]:
    if not path.is_absolute() or ".." in path.parts or len(path.parts) < 2:
        raise ValueError(f"source path must be absolute without '..': {path}")
    directory_flags = (
        os.O_RDONLY
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    directory = os.open(path.anchor, directory_flags)
    metadata = os.fstat(directory)
    chain = [(metadata.st_dev, metadata.st_ino)]
    try:
        for component in path.parts[1:-1]:
            child = os.open(component, directory_flags, dir_fd=directory)
            os.close(directory)
            directory = child
            metadata = os.fstat(directory)
            chain.append((metadata.st_dev, metadata.st_ino))
        metadata = os.stat(path.parts[-1], dir_fd=directory, follow_symlinks=False)
        if not stat.S_ISREG(metadata.st_mode):
            raise ValueError(f"source is not a regular file: {path}")
        chain.append((metadata.st_dev, metadata.st_ino))
        return tuple(chain), _file_identity(metadata)
    finally:
        os.close(directory)


def _lexical_absolute(path: Path, label: str) -> Path:
    if not isinstance(path, Path):
        raise ValueError(f"{label} must be a pathlib.Path")
    if not path.is_absolute():
        raise ValueError(f"{label} must be absolute: {path}")
    if ".." in path.parts:
        raise ValueError(f"{label} must not contain '..': {path}")
    return Path(os.path.abspath(path))


def _validate_no_symlink_components(path: Path, label: str) -> None:
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        try:
            metadata = os.lstat(current)
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(metadata.st_mode):
            raise ValueError(f"{label} contains a symbolic link component: {current}")
        if current != path and not stat.S_ISDIR(metadata.st_mode):
            raise ValueError(f"{label} parent component is not a directory: {current}")


def _relative_output_path(repository_root: Path, path: Path, label: str) -> str:
    root = _lexical_absolute(repository_root, "repository root")
    output = _lexical_absolute(path, label)
    try:
        relative = output.relative_to(root)
    except ValueError as error:
        raise ValueError(f"{label} is outside repository root: {path}") from error
    if not relative.parts or ".." in relative.parts:
        raise ValueError(f"{label} is not a repository-relative destination: {path}")
    return relative.as_posix()


def _validate_freeze_paths(outputs: FreezePaths) -> None:
    if not isinstance(outputs, FreezePaths):
        raise ValueError("outputs must be a FreezePaths instance")
    root = _lexical_absolute(outputs.repository_root, "repository root")
    _validate_no_symlink_components(root, "repository root")
    try:
        root_metadata = os.lstat(root)
    except FileNotFoundError as error:
        raise ValueError(f"repository root does not exist: {root}") from error
    if not stat.S_ISDIR(root_metadata.st_mode):
        raise ValueError(f"repository root is not a directory: {root}")

    destinations = {
        "selection receipt": outputs.selection_receipt,
        "application input tree": outputs.application_inputs,
        "manifest": outputs.manifest,
        "manifest checksum": outputs.manifest_checksum,
        "source ledger": outputs.source_ledger,
        "input summary": outputs.input_summary,
    }
    normalized: dict[str, Path] = {}
    for label, path in destinations.items():
        _relative_output_path(root, path, label)
        normalized[label] = _lexical_absolute(path, label)
        _validate_no_symlink_components(normalized[label], label)

    items = tuple(normalized.items())
    for index, (left_label, left) in enumerate(items):
        for right_label, right in items[index + 1 :]:
            if left == right or left in right.parents or right in left.parents:
                raise ValueError(
                    f"output path collision between {left_label} and {right_label}"
                )

    existing_inodes: dict[tuple[int, int], str] = {}
    for label, path in items:
        if not _path_exists_no_follow(path):
            continue
        metadata = os.lstat(path)
        identity = (metadata.st_dev, metadata.st_ino)
        owner = existing_inodes.get(identity)
        if owner is not None:
            raise ValueError(f"output path alias between {owner} and {label}")
        existing_inodes[identity] = label

    canonical_paths = {
        "selection receipt": root / "paper/bioinformatics/application_selection.json",
        "application input tree": root / "reproduce/bioinformatics/application_inputs",
        "manifest": root / "paper/bioinformatics/application_manifest.tsv",
        "manifest checksum": root / "paper/bioinformatics/application_manifest.sha256",
        "source ledger": root / "paper/bioinformatics/application_sources.tsv",
        "input summary": root / "paper/bioinformatics/application_input_summary.tsv",
    }
    for label, canonical in canonical_paths.items():
        if normalized[label] != canonical:
            raise ValueError(f"{label} must use canonical output path: {canonical}")


def _validate_source_specs(
    source_specs: tuple[SourceSpec, ...],
) -> tuple[SourceSpec, ...]:
    if not isinstance(source_specs, tuple) or len(source_specs) != len(
        _BIOLOGICAL_SOURCE_BINDINGS
    ):
        raise ValueError("source inputs require exactly four biological source specs")
    if any(not isinstance(source, SourceSpec) for source in source_specs):
        raise ValueError("biological source specs must be SourceSpec instances")
    expected_ids = tuple(binding[0] for binding in _BIOLOGICAL_SOURCE_BINDINGS)
    actual_ids = tuple(source.source_id for source in source_specs)
    if actual_ids != expected_ids:
        raise ValueError("biological source specs have wrong source IDs and order")
    for source, (_source_id, _snapshot_name, expected_role) in zip(
        source_specs,
        _BIOLOGICAL_SOURCE_BINDINGS,
        strict=True,
    ):
        if source.role != expected_role:
            raise ValueError(f"biological source role mismatch: {source.source_id}")
        if (
            not isinstance(source.compressed_size_bytes, int)
            or isinstance(source.compressed_size_bytes, bool)
            or source.compressed_size_bytes <= 0
            or not isinstance(source.decompressed_size_bytes, int)
            or isinstance(source.decompressed_size_bytes, bool)
            or source.decompressed_size_bytes <= 0
        ):
            raise ValueError(f"biological source size is invalid: {source.source_id}")
        if (
            not isinstance(source.upstream_md5, str)
            or len(source.upstream_md5) != 32
            or set(source.upstream_md5) - set("0123456789abcdef")
        ):
            raise ValueError(f"biological source MD5 is invalid: {source.source_id}")
        if not _is_sha256(source.compressed_sha256) or not _is_sha256(
            source.decompressed_sha256
        ):
            raise ValueError(f"biological source SHA-256 is invalid: {source.source_id}")
        for field_name in (
            "provider",
            "release",
            "assembly",
            "url",
            "local_source_path",
            "license_or_terms",
            "redistribution_note",
            "download_command",
        ):
            value = getattr(source, field_name)
            if (
                not isinstance(value, str)
                or not value
                or any(character in value for character in "\r\n\t")
            ):
                raise ValueError(
                    f"biological source metadata is invalid: {source.source_id} {field_name}"
                )
        if not source.url.startswith("https://"):
            raise ValueError(f"biological source URL is invalid: {source.source_id}")
    return source_specs


def _validate_source_inputs(inputs: SourceInputs) -> None:
    if not isinstance(inputs, SourceInputs):
        raise ValueError("inputs must be a SourceInputs instance")
    _validate_source_specs(inputs.source_specs)
    paths = {
        "lncRNA FASTA": inputs.lncrna_fasta,
        "annotation GTF": inputs.annotation_gtf,
        "chr21 FASTA": inputs.chr21_fasta,
        "chr22 FASTA": inputs.chr22_fasta,
        "development exclusions": inputs.development_exclusions,
        "Phase 2 holdout manifest": inputs.holdout_manifest,
    }
    for label, path in paths.items():
        normalized = _lexical_absolute(path, label)
        _validate_no_symlink_components(normalized, label)
        try:
            metadata = os.lstat(normalized)
        except FileNotFoundError as error:
            raise ValueError(f"missing {label}: {path}") from error
        if not stat.S_ISREG(metadata.st_mode):
            raise ValueError(f"{label} is not a regular file: {path}")


def _snapshot_source(path: Path) -> _SourceSnapshot:
    try:
        try:
            descriptor, retained_chain = _open_file_and_chain_by_no_follow_walk(
                path,
                os.O_RDONLY | getattr(os, "O_NOATIME", 0),
            )
        except PermissionError:
            descriptor, retained_chain = _open_file_and_chain_by_no_follow_walk(
                path,
                os.O_RDONLY,
            )
    except OSError as error:
        raise ValueError(f"cannot snapshot source without following links: {path}") from error
    retained = False
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise ValueError(f"source is not a regular file: {path}")
        before_identity = _file_identity(before)
        os.lseek(descriptor, 0, os.SEEK_SET)
        md5_digest = hashlib.md5()
        sha256_digest = hashlib.sha256()
        size_bytes = 0
        while block := os.read(descriptor, 1024 * 1024):
            md5_digest.update(block)
            sha256_digest.update(block)
            size_bytes += len(block)
        after = os.fstat(descriptor)
        if _file_identity(after) != before_identity or size_bytes != before.st_size:
            raise ValueError(f"source changed while it was snapshotted: {path}")
        current_chain, current_identity = _path_identity_chain_without_opening_file(path)
        if retained_chain[:-1] != current_chain[:-1]:
            raise ValueError(
                f"source parent changed while it was read without following links: {path}"
            )
        if current_identity != before_identity:
            raise ValueError(f"source changed while it was snapshotted: {path}")
        snapshot = _SourceSnapshot(
            path=path,
            descriptor=descriptor,
            identity=before_identity,
            component_chain=retained_chain,
            md5=md5_digest.hexdigest(),
            sha256=sha256_digest.hexdigest(),
            size_bytes=size_bytes,
        )
        retained = True
        return snapshot
    finally:
        if not retained:
            os.close(descriptor)


def _snapshot_sources(inputs: SourceInputs) -> dict[str, _SourceSnapshot]:
    snapshots: dict[str, _SourceSnapshot] = {}
    paths = (
        ("annotation_gtf", inputs.annotation_gtf),
        ("chr21_fasta", inputs.chr21_fasta),
        ("chr22_fasta", inputs.chr22_fasta),
        ("development_exclusions", inputs.development_exclusions),
        ("lncrna_fasta", inputs.lncrna_fasta),
        ("phase2_holdout_manifest", inputs.holdout_manifest),
    )
    try:
        for name, path in paths:
            snapshots[name] = _snapshot_source(path)
        return snapshots
    except BaseException:
        _close_source_snapshots(snapshots)
        raise


def _verify_source_snapshot_path(snapshot: _SourceSnapshot) -> None:
    try:
        current_chain, current_identity = _path_identity_chain_without_opening_file(
            snapshot.path
        )
    except (OSError, ValueError) as error:
        raise ValueError(f"source changed during reconstruction: {snapshot.path}") from error
    if current_chain[:-1] != snapshot.component_chain[:-1]:
        raise ValueError(f"source parent changed during reconstruction: {snapshot.path}")
    if current_identity != snapshot.identity:
        raise ValueError(f"source changed during reconstruction: {snapshot.path}")


def _verify_source_snapshots(snapshots: dict[str, _SourceSnapshot]) -> None:
    for snapshot in snapshots.values():
        snapshot.verify_descriptor()
        _verify_source_snapshot_path(snapshot)


def _close_source_snapshots(snapshots: dict[str, _SourceSnapshot]) -> None:
    errors: list[BaseException] = []
    for snapshot in snapshots.values():
        try:
            snapshot.close()
        except BaseException as error:
            errors.append(error)
    if errors and any(snapshot.descriptor is not None for snapshot in snapshots.values()):
        raise RuntimeError("; ".join(str(error) for error in errors))


def _decompressed_source_identity(
    snapshot: _SourceSnapshot,
) -> tuple[int, str]:
    descriptor = snapshot.verify_descriptor()
    _verify_source_snapshot_path(snapshot)
    if snapshot.path.suffix != ".gz":
        snapshot.verify_descriptor()
        _verify_source_snapshot_path(snapshot)
        return snapshot.size_bytes, snapshot.sha256

    os.lseek(descriptor, 0, os.SEEK_SET)
    duplicate = os.dup(descriptor)
    try:
        binary = os.fdopen(duplicate, "rb", closefd=True)
    except BaseException:
        os.close(duplicate)
        raise
    digest = hashlib.sha256()
    size_bytes = 0
    try:
        try:
            with binary:
                with gzip.GzipFile(fileobj=binary, mode="rb") as compressed:
                    while block := compressed.read(1024 * 1024):
                        digest.update(block)
                        size_bytes += len(block)
        except (EOFError, OSError, zlib.error) as error:
            raise ValueError(
                f"cannot decompress biological source: {snapshot.path}"
            ) from error
    finally:
        snapshot.verify_descriptor()
        _verify_source_snapshot_path(snapshot)
    return size_bytes, digest.hexdigest()


def _bind_verified_biological_sources(
    snapshots: dict[str, _SourceSnapshot],
    source_specs: tuple[SourceSpec, ...],
) -> _VerifiedSourceSpecs:
    validated_specs = _validate_source_specs(source_specs)
    _verify_source_snapshots(snapshots)
    for source, (_source_id, snapshot_name, _expected_role) in zip(
        validated_specs,
        _BIOLOGICAL_SOURCE_BINDINGS,
        strict=True,
    ):
        try:
            snapshot = snapshots[snapshot_name]
        except KeyError as error:
            raise ValueError(
                f"biological source snapshot is missing: {source.source_id}"
            ) from error
        if (
            snapshot.size_bytes != source.compressed_size_bytes
            or snapshot.md5 != source.upstream_md5
            or snapshot.sha256 != source.compressed_sha256
        ):
            raise ValueError(
                "biological source identity mismatch for "
                f"{source.source_id}: expected size={source.compressed_size_bytes} "
                f"md5={source.upstream_md5} sha256={source.compressed_sha256}; "
                f"actual size={snapshot.size_bytes} md5={snapshot.md5} "
                f"sha256={snapshot.sha256}"
            )
        decompressed_size, decompressed_sha256 = _decompressed_source_identity(
            snapshot
        )
        if (
            decompressed_size != source.decompressed_size_bytes
            or decompressed_sha256 != source.decompressed_sha256
        ):
            raise ValueError(
                "decompressed biological source identity mismatch for "
                f"{source.source_id}: expected size={source.decompressed_size_bytes} "
                f"sha256={source.decompressed_sha256}; actual size={decompressed_size} "
                f"sha256={decompressed_sha256}"
            )
    return _VerifiedSourceSpecs(validated_specs)


def _source_identities(
    snapshots: dict[str, _SourceSnapshot],
) -> dict[str, dict[str, object]]:
    identities: dict[str, dict[str, object]] = {}
    for name, snapshot in snapshots.items():
        identities[name] = {
            "sha256": snapshot.sha256,
            "size_bytes": snapshot.size_bytes,
        }
    return identities


def _manifest_rows_and_files(
    *,
    queries: list[dict[str, object]],
    targets: list[dict[str, object]],
    query_sequences: dict[str, str],
    outputs: FreezePaths,
) -> tuple[list[dict[str, object]], dict[str, bytes]]:
    rows: list[dict[str, object]] = []
    files: dict[str, bytes] = {}
    repository_root = _lexical_absolute(outputs.repository_root, "repository root")

    for query in queries:
        record_id = str(query["query_id"])
        transcript_id = str(query["transcript_id"])
        gene_id = str(query["gene_id"])
        gene_name = str(query["gene_name"])
        try:
            sequence = query_sequences[transcript_id]
        except KeyError as error:
            raise ValueError(f"selected query sequence is unavailable: {transcript_id}") from error
        if sequence_sha256(sequence) != str(query["sequence_sha256"]):
            raise ValueError(f"selected query sequence drifted: {transcript_id}")
        relative_file = f"queries/{record_id}.fa"
        content = _fasta_bytes(
            "|".join(
                (
                    record_id,
                    transcript_id,
                    gene_id,
                    gene_name,
                    ANNOTATION_RELEASE,
                    ASSEMBLY,
                    "application_query",
                )
            ),
            sequence,
        )
        destination = outputs.application_inputs / relative_file
        rows.append(
            {
                "record_id": record_id,
                "record_role": "query",
                **COMMON,
                "original_gene_id": gene_id,
                "original_gene_name": gene_name,
                "original_transcript_id": transcript_id,
                "selection_rule": QUERY_SELECTION_RULE,
                "sequence_length": len(sequence),
                "chromosome": "NA",
                "strand": "NA",
                "tss": "NA",
                "region_start": "NA",
                "region_end": "NA",
                "sequence_sha256": sequence_sha256(sequence),
                "file_sha256": hashlib.sha256(content).hexdigest(),
                "path": _relative_output_path(
                    repository_root,
                    destination,
                    f"query FASTA {record_id}",
                ),
                "license_note": QUERY_LICENSE,
            }
        )
        files[relative_file] = content

    for target in targets:
        record_id = str(target["target_id"])
        transcript_id = str(target["transcript_id"])
        gene_id = str(target["gene_id"])
        gene_name = str(target["gene_name"])
        chromosome = str(target["chromosome"])
        start = int(target["region_start"])
        end = int(target["region_end"])
        sequence = str(target["sequence"])
        if sequence_sha256(sequence) != str(target["sequence_sha256"]):
            raise ValueError(f"selected target sequence drifted: {transcript_id}")
        relative_file = f"targets/{record_id}.fa"
        content = _fasta_bytes(
            "|".join(
                (
                    record_id,
                    transcript_id,
                    gene_id,
                    gene_name,
                    ASSEMBLY,
                    f"{chromosome}:{start}-{end}",
                    "promoter_forward_genomic",
                )
            ),
            sequence,
        )
        destination = outputs.application_inputs / relative_file
        rows.append(
            {
                "record_id": record_id,
                "record_role": "target",
                **COMMON,
                "original_gene_id": gene_id,
                "original_gene_name": gene_name,
                "original_transcript_id": transcript_id,
                "selection_rule": TARGET_SELECTION_RULE,
                "sequence_length": len(sequence),
                "chromosome": chromosome,
                "strand": str(target["strand"]),
                "tss": int(target["tss"]),
                "region_start": start,
                "region_end": end,
                "sequence_sha256": sequence_sha256(sequence),
                "file_sha256": hashlib.sha256(content).hexdigest(),
                "path": _relative_output_path(
                    repository_root,
                    destination,
                    f"target FASTA {record_id}",
                ),
                "license_note": TARGET_LICENSE,
            }
        )
        files[relative_file] = content
    return rows, files


def _selected_query_identity(row: dict[str, object]) -> dict[str, object]:
    return {
        "query_id": row["query_id"],
        "original_gene_id": row["gene_id"],
        "original_gene_name": row["gene_name"],
        "original_transcript_id": row["transcript_id"],
        "selection_hash": row["selection_hash"],
        "sequence_length": row["sequence_length"],
        "sequence_sha256": row["sequence_sha256"],
    }


def _selected_target_identity(row: dict[str, object]) -> dict[str, object]:
    return {
        "target_id": row["target_id"],
        "original_gene_id": row["gene_id"],
        "original_gene_name": row["gene_name"],
        "original_transcript_id": row["transcript_id"],
        "chromosome": row["chromosome"],
        "strand": row["strand"],
        "tss": row["tss"],
        "region_start": row["region_start"],
        "region_end": row["region_end"],
        "sequence_length": row["sequence_length"],
        "sequence_sha256": row["sequence_sha256"],
    }


def _derive_record_summary(
    rows: list[dict[str, object]] | list[dict[str, str]],
    target_counts: dict[str, int],
) -> dict[str, object]:
    queries = [row for row in rows if row["record_role"] == "query"]
    targets = [row for row in rows if row["record_role"] == "target"]
    if len(queries) != QUERY_COUNT:
        raise ValueError(f"materialized query count must be exactly {QUERY_COUNT}")
    if len(targets) < MIN_TARGET_COUNT:
        raise ValueError(f"materialized target count must be at least {MIN_TARGET_COUNT}")
    if len({str(row["record_id"]) for row in rows}) != len(rows):
        raise ValueError("materialized record IDs must be unique")
    if len({str(row["path"]) for row in rows}) != len(rows):
        raise ValueError("materialized record paths must be unique")
    if len({stable_id(str(row["original_gene_id"])) for row in queries}) != len(queries):
        raise ValueError("materialized query genes must be unique")
    if len({str(row["sequence_sha256"]) for row in queries}) != len(queries):
        raise ValueError("materialized query sequence digests must be unique")
    if len({stable_id(str(row["original_gene_id"])) for row in targets}) != len(targets):
        raise ValueError("materialized target genes must be unique")

    chromosome_counts = {
        chromosome: sum(row["chromosome"] == chromosome for row in targets)
        for chromosome in TARGET_CHROMOSOMES
    }
    if any(count == 0 for count in chromosome_counts.values()):
        raise ValueError("materialized targets must include chr21 and chr22")

    query_lengths = [int(row["sequence_length"]) for row in queries]
    result: dict[str, object] = {
        "query_count": len(queries),
        "target_count": len(targets),
        "pair_count": len(queries) * len(targets),
        "query_total_bp": sum(query_lengths),
        "target_total_bp": sum(int(row["sequence_length"]) for row in targets),
        "chr21_target_count": chromosome_counts["chr21"],
        "chr22_target_count": chromosome_counts["chr22"],
        "min_query_length": min(query_lengths),
        "max_query_length": max(query_lengths),
        "annotation_target_candidate_count": target_counts[
            "annotation_target_candidate_count"
        ],
        "excluded_target_count": target_counts["excluded_target_count"],
    }
    if int(result["pair_count"]) < QUERY_COUNT * MIN_TARGET_COUNT:
        raise ValueError("materialized pair count must be at least 15000")
    if (
        int(result["annotation_target_candidate_count"])
        != int(result["target_count"]) + int(result["excluded_target_count"])
    ):
        raise ValueError("target candidate and exclusion totals are inconsistent")
    return result


def _validate_materialized_records(
    rows: list[dict[str, object]],
    files: dict[str, bytes],
    target_counts: dict[str, int],
) -> dict[str, object]:
    expected_relative_files = {
        "/".join(str(row["path"]).split("/")[-2:]) for row in rows
    }
    if set(files) != expected_relative_files:
        raise ValueError("materialized FASTA tree does not match manifest records")
    return _derive_record_summary(rows, target_counts)


def _prepare_freeze_from_snapshots(
    snapshots: dict[str, _SourceSnapshot],
    outputs: FreezePaths,
    verified_sources: _VerifiedSourceSpecs,
) -> _FreezeModel:
    transcripts = parse_gtf(snapshots["annotation_gtf"])
    development_exclusions = read_development_exclusions(
        snapshots["development_exclusions"]
    )
    holdout_gene_ids, holdout_sequence_digests = read_holdout_exclusions(
        snapshots["phase2_holdout_manifest"]
    )
    queries, query_counts, query_sequences = _select_queries_streaming(
        fasta_records=_iter_fasta_records(snapshots["lncrna_fasta"]),
        transcripts=transcripts,
        development_exclusions=development_exclusions,
        holdout_gene_ids=holdout_gene_ids,
        holdout_sequence_sha256=holdout_sequence_digests,
    )
    targets, target_counts = _select_targets_streaming(
        transcripts=transcripts,
        chromosome_sequence=lambda chromosome: read_chromosome_fasta(
            snapshots[f"{chromosome}_fasta"],
            chromosome,
        ),
    )
    rows, application_files = _manifest_rows_and_files(
        queries=queries,
        targets=targets,
        query_sequences=query_sequences,
        outputs=outputs,
    )
    derived = _validate_materialized_records(rows, application_files, target_counts)
    manifest_bytes = _tsv_bytes(MANIFEST_FIELDS, rows)
    manifest_sha256 = hashlib.sha256(manifest_bytes).hexdigest()
    freeze_id = FREEZE_ID_PREFIX + manifest_sha256[:8]
    result = {
        "freeze_id": freeze_id,
        "manifest_sha256": manifest_sha256,
        **derived,
    }
    summary_bytes = _tsv_bytes(SUMMARY_FIELDS, [result])
    checksum_bytes = f"{manifest_sha256}  {outputs.manifest.name}\n".encode("ascii")
    source_ledger_bytes = _tsv_bytes(
        APPLICATION_SOURCE_FIELDS,
        _verified_application_source_rows(verified_sources),
    )
    _verify_source_snapshots(snapshots)
    receipt = {
        "annotation_release": ANNOTATION_RELEASE,
        "assembly": ASSEMBLY,
        "final_freeze_id": freeze_id,
        "manifest_sha256": manifest_sha256,
        "proposed_freeze_id": freeze_id,
        "query_counts": query_counts,
        "query_selection_rule": QUERY_SELECTION_RULE,
        "schema_version": 1,
        "selected_queries": [_selected_query_identity(row) for row in queries],
        "selected_targets": [_selected_target_identity(row) for row in targets],
        "selection_seed": SELECTION_SEED,
        "source_identities": _source_identities(snapshots),
        "target_counts": target_counts,
        "target_selection_rule": TARGET_SELECTION_RULE,
    }
    return _FreezeModel(
        application_files=application_files,
        selection_receipt_bytes=_canonical_json_bytes(receipt),
        manifest_bytes=manifest_bytes,
        manifest_checksum_bytes=checksum_bytes,
        source_ledger_bytes=source_ledger_bytes,
        input_summary_bytes=summary_bytes,
        result=result,
    )


def _prepare_freeze(inputs: SourceInputs, outputs: FreezePaths) -> _FreezeModel:
    _validate_source_inputs(inputs)
    _validate_freeze_paths(outputs)
    snapshots = _snapshot_sources(inputs)
    try:
        verified_sources = _bind_verified_biological_sources(
            snapshots,
            inputs.source_specs,
        )
        return _prepare_freeze_from_snapshots(
            snapshots,
            outputs,
            verified_sources,
        )
    finally:
        _close_source_snapshots(snapshots)


def _output_directory_flags() -> int:
    return (
        os.O_RDONLY
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NOATIME", 0)
    )


def _register_existing_output_inode(
    metadata: os.stat_result,
    label: str,
    seen_inodes: dict[tuple[int, int], str],
) -> None:
    if metadata.st_nlink != 1:
        raise ValueError(f"multiply-linked output is not immutable: {label}")
    identity = (metadata.st_dev, metadata.st_ino)
    owner = seen_inodes.get(identity)
    if owner is not None:
        raise ValueError(f"output inode alias between {owner} and {label}")
    seen_inodes[identity] = label


def _read_output_file_at(
    parent_descriptor: int,
    name: str,
    label: str,
    seen_inodes: dict[tuple[int, int], str],
) -> bytes:
    try:
        descriptor = os.open(
            name,
            os.O_RDONLY
            | getattr(os, "O_NOFOLLOW", 0)
            | getattr(os, "O_NOATIME", 0),
            dir_fd=parent_descriptor,
        )
    except OSError as error:
        raise ValueError(
            f"cannot read existing output without following links or changing atime: {label}"
        ) from error
    try:
        return _read_output_descriptor(descriptor, label, seen_inodes)
    finally:
        os.close(descriptor)


def _read_output_descriptor(
    descriptor: int,
    label: str,
    seen_inodes: dict[tuple[int, int], str],
) -> bytes:
    before = os.fstat(descriptor)
    if not stat.S_ISREG(before.st_mode):
        raise ValueError(f"existing output is not a regular file: {label}")
    _register_existing_output_inode(before, label, seen_inodes)
    os.lseek(descriptor, 0, os.SEEK_SET)
    chunks: list[bytes] = []
    while block := os.read(descriptor, 1024 * 1024):
        chunks.append(block)
    content = b"".join(chunks)
    after = os.fstat(descriptor)
    if _file_identity(after) != _file_identity(before) or len(content) != before.st_size:
        raise ValueError(f"existing output changed while it was read: {label}")
    return content


def _open_output_directory(path: Path, label: str) -> int:
    try:
        descriptor, _ = _open_file_and_chain_by_no_follow_walk(
            path,
            _output_directory_flags(),
        )
    except OSError as error:
        raise ValueError(
            f"cannot traverse existing output without following links or changing atime: {label}"
        ) from error
    metadata = os.fstat(descriptor)
    if not stat.S_ISDIR(metadata.st_mode):
        os.close(descriptor)
        raise ValueError(f"artifact tree is not a regular directory: {path}")
    return descriptor


def _actual_tree_bytes_from_descriptor(
    root_descriptor: int,
    label: str,
    seen_inodes: dict[tuple[int, int], str] | None = None,
) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    directories: set[str] = set()
    inode_registry = seen_inodes if seen_inodes is not None else {}

    def visit(directory_descriptor: int, relative: Path) -> None:
        os.lseek(directory_descriptor, 0, os.SEEK_SET)
        with os.scandir(directory_descriptor) as iterator:
            entries = sorted(iterator, key=lambda entry: entry.name)
        for entry in entries:
            entry_relative = relative / entry.name
            entry_metadata = entry.stat(follow_symlinks=False)
            if stat.S_ISLNK(entry_metadata.st_mode):
                raise ValueError(f"artifact tree contains a symbolic link: {entry_relative}")
            if stat.S_ISDIR(entry_metadata.st_mode):
                directories.add(entry_relative.as_posix())
                try:
                    child = os.open(
                        entry.name,
                        _output_directory_flags(),
                        dir_fd=directory_descriptor,
                    )
                except OSError as error:
                    raise ValueError(
                        f"cannot traverse output directory without changing atime: {entry_relative}"
                    ) from error
                try:
                    child_metadata = os.fstat(child)
                    if (child_metadata.st_dev, child_metadata.st_ino) != (
                        entry_metadata.st_dev,
                        entry_metadata.st_ino,
                    ):
                        raise ValueError(f"output directory changed during traversal: {entry_relative}")
                    visit(child, entry_relative)
                finally:
                    os.close(child)
            elif stat.S_ISREG(entry_metadata.st_mode):
                files[entry_relative.as_posix()] = _read_output_file_at(
                    directory_descriptor,
                    entry.name,
                    entry_relative.as_posix(),
                    inode_registry,
                )
            else:
                raise ValueError(f"artifact tree contains a non-regular entry: {entry_relative}")

    visit(root_descriptor, Path())
    if directories != {"queries", "targets"}:
        raise ValueError(f"existing application input tree drift: {label}")
    return files


def _verify_retained_tree_entries(
    root_descriptor: int,
    captured: dict[tuple[str, ...], _CapturedTreeEntry],
) -> None:
    if any(captured_entry.state != "mutated" for captured_entry in captured.values()):
        raise ValueError("retained tree capture state changed")
    try:
        _verify_captured_tree_namespace(root_descriptor, captured)
    except ValueError as error:
        raise ValueError(f"retained tree entry validation failed: {error}") from error


def _retained_tree_name_metadata(
    root_descriptor: int,
    relative: tuple[str, ...],
) -> os.stat_result:
    parent = _open_relative_directory(root_descriptor, relative[:-1])
    try:
        return os.stat(relative[-1], dir_fd=parent, follow_symlinks=False)
    except FileNotFoundError as error:
        raise ValueError(f"retained tree entry moved: {'/'.join(relative)}") from error
    finally:
        os.close(parent)


def _tree_namespace_from_descriptor(
    root_descriptor: int,
) -> dict[tuple[str, ...], tuple[int, tuple[int, int]]]:
    namespace: dict[tuple[str, ...], tuple[int, tuple[int, int]]] = {}

    def visit(directory_descriptor: int, prefix: tuple[str, ...]) -> None:
        os.lseek(directory_descriptor, 0, os.SEEK_SET)
        with os.scandir(directory_descriptor) as iterator:
            entries = sorted(iterator, key=lambda entry: entry.name)
        for entry in entries:
            metadata = entry.stat(follow_symlinks=False)
            relative = (*prefix, entry.name)
            if not stat.S_ISDIR(metadata.st_mode) and not stat.S_ISREG(metadata.st_mode):
                raise ValueError(f"retained tree contains a non-regular entry: {'/'.join(relative)}")
            identity = (metadata.st_dev, metadata.st_ino)
            namespace[relative] = (metadata.st_mode, identity)
            if stat.S_ISDIR(metadata.st_mode):
                child = _open_directory_at(directory_descriptor, entry.name)
                try:
                    if _descriptor_identity(child) != identity:
                        raise ValueError(
                            f"retained tree directory changed: {'/'.join(relative)}"
                        )
                    visit(child, relative)
                finally:
                    os.close(child)

    visit(root_descriptor, ())
    return namespace


def _actual_retained_tree_bytes(
    root_descriptor: int,
    captured: dict[tuple[str, ...], _CapturedTreeEntry],
    seen_inodes: dict[tuple[int, int], str],
) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    directories: set[str] = set()
    for relative, captured_entry in sorted(captured.items()):
        if captured_entry.state != "mutated":
            raise ValueError(f"retained tree entry is unavailable: {'/'.join(relative)}")
        before_name = _retained_tree_name_metadata(root_descriptor, relative)
        _verify_captured_entry(before_name, captured_entry, "/".join(relative))
        if stat.S_ISDIR(captured_entry.mode):
            directories.add("/".join(relative))
        else:
            parent = _open_relative_directory(root_descriptor, relative[:-1])
            descriptor = _open_captured_tree_entry(
                parent,
                relative[-1],
                captured_entry,
                "/".join(relative),
            )
            try:
                content = _read_output_descriptor(
                    descriptor,
                    "/".join(relative),
                    seen_inodes,
                )
                if hashlib.sha256(content).hexdigest() != captured_entry.content_sha256:
                    raise ValueError(
                        f"retained tree entry content changed: {'/'.join(relative)}"
                    )
                files["/".join(relative)] = content
            finally:
                os.close(descriptor)
                os.close(parent)
        after_name = _retained_tree_name_metadata(root_descriptor, relative)
        _verify_captured_entry(after_name, captured_entry, "/".join(relative))

    namespace = _tree_namespace_from_descriptor(root_descriptor)
    if set(namespace) != set(captured):
        raise ValueError("retained application tree namespace changed")
    for relative, (current_mode, current_identity) in namespace.items():
        captured_entry = captured[relative]
        if current_identity != captured_entry.identity:
            raise ValueError(f"retained tree entry was replaced: {'/'.join(relative)}")
        if stat.S_IFMT(current_mode) != stat.S_IFMT(captured_entry.mode):
            raise ValueError(f"retained tree entry type changed: {'/'.join(relative)}")
    if directories != {"queries", "targets"}:
        raise ValueError("retained application tree directories changed")
    return files


def _open_relative_parent_if_exists(
    repository_descriptor: int,
    components: tuple[str, ...],
) -> int | None:
    current = os.dup(repository_descriptor)
    try:
        for component in components:
            try:
                metadata = os.stat(component, dir_fd=current, follow_symlinks=False)
            except FileNotFoundError:
                os.close(current)
                return None
            if not stat.S_ISDIR(metadata.st_mode):
                raise ValueError(f"output parent component is not a directory: {component}")
            child = _open_directory_at(current, component)
            if _descriptor_identity(child) != (metadata.st_dev, metadata.st_ino):
                os.close(child)
                raise ValueError(f"output parent changed during traversal: {component}")
            os.close(current)
            current = child
        return current
    except BaseException:
        os.close(current)
        raise


def _read_existing_output_file(
    repository_descriptor: int,
    components: tuple[str, ...],
    label: str,
    seen_inodes: dict[tuple[int, int], str],
    *,
    allow_missing: bool = False,
    retained_entry: _CreatedEntry | None = None,
) -> bytes | None:
    if retained_entry is not None:
        if retained_entry.parent_descriptor is None:
            raise ValueError(f"retained output parent is closed: {label}")
        if retained_entry.object_descriptor is None or retained_entry.object_identity is None:
            raise ValueError(f"retained output object is unavailable: {label}")
        _verify_retained_parent(
            repository_descriptor,
            components[:-1],
            retained_entry.parent_descriptor,
        )
        current = os.stat(
            retained_entry.name,
            dir_fd=retained_entry.parent_descriptor,
            follow_symlinks=False,
        )
        if (current.st_dev, current.st_ino) != retained_entry.object_identity:
            raise ValueError(f"retained output name changed: {label}")
        if _descriptor_identity(retained_entry.object_descriptor) != retained_entry.object_identity:
            raise ValueError(f"retained output descriptor changed: {label}")
        return _read_output_descriptor(
            retained_entry.object_descriptor,
            label,
            seen_inodes,
        )

    parent_descriptor = _open_relative_parent_if_exists(
        repository_descriptor,
        components[:-1],
    )
    if parent_descriptor is None:
        if allow_missing:
            return None
        raise ValueError(f"existing output parent is missing: {label}")
    try:
        try:
            os.stat(components[-1], dir_fd=parent_descriptor, follow_symlinks=False)
        except FileNotFoundError:
            if allow_missing:
                return None
            raise ValueError(f"existing output is missing: {label}")
        return _read_output_file_at(
            parent_descriptor,
            components[-1],
            label,
            seen_inodes,
        )
    finally:
        os.close(parent_descriptor)


def _preflight_existing(
    repository_descriptor: int,
    outputs: FreezePaths,
    model: _FreezeModel,
    journal: _PublicationJournal | None = None,
) -> list[tuple[str, Path, bytes | dict[str, bytes]]]:
    expected = [
        (
            "application input tree",
            outputs.application_inputs,
            ("reproduce", "bioinformatics", "application_inputs"),
            model.application_files,
        ),
        (
            "selection receipt",
            outputs.selection_receipt,
            ("paper", "bioinformatics", "application_selection.json"),
            model.selection_receipt_bytes,
        ),
        (
            "manifest",
            outputs.manifest,
            ("paper", "bioinformatics", "application_manifest.tsv"),
            model.manifest_bytes,
        ),
        (
            "manifest checksum",
            outputs.manifest_checksum,
            ("paper", "bioinformatics", "application_manifest.sha256"),
            model.manifest_checksum_bytes,
        ),
        (
            "source ledger",
            outputs.source_ledger,
            ("paper", "bioinformatics", "application_sources.tsv"),
            model.source_ledger_bytes,
        ),
        (
            "input summary",
            outputs.input_summary,
            ("paper", "bioinformatics", "application_input_summary.tsv"),
            model.input_summary_bytes,
        ),
    ]
    missing: list[tuple[str, Path, bytes | dict[str, bytes]]] = []
    seen_inodes: dict[tuple[int, int], str] = {}
    for label, destination, components, expected_content in expected:
        retained_entry = None
        if journal is not None:
            retained_entry = next(
                (
                    entry
                    for entry in journal.created
                    if entry.display_path == destination and entry.state == "mutated"
                ),
                None,
            )
        if isinstance(expected_content, dict):
            try:
                if retained_entry is not None:
                    if (
                        retained_entry.parent_descriptor is None
                        or retained_entry.object_descriptor is None
                        or retained_entry.object_identity is None
                    ):
                        raise ValueError("retained application tree is unavailable")
                    _verify_retained_parent(
                        repository_descriptor,
                        components[:-1],
                        retained_entry.parent_descriptor,
                    )
                    current = os.stat(
                        retained_entry.name,
                        dir_fd=retained_entry.parent_descriptor,
                        follow_symlinks=False,
                    )
                    if (current.st_dev, current.st_ino) != retained_entry.object_identity:
                        raise ValueError("retained application tree name changed")
                    if (
                        _descriptor_identity(retained_entry.object_descriptor)
                        != retained_entry.object_identity
                    ):
                        raise ValueError("retained application tree descriptor changed")
                    _verify_retained_tree_entries(
                        retained_entry.object_descriptor,
                        retained_entry.captured_tree,
                    )
                    actual = _actual_retained_tree_bytes(
                        retained_entry.object_descriptor,
                        retained_entry.captured_tree,
                        seen_inodes,
                    )
                else:
                    parent = _open_relative_parent_if_exists(
                        repository_descriptor,
                        components[:-1],
                    )
                    if parent is None:
                        missing.append((label, destination, expected_content))
                        continue
                    try:
                        try:
                            root = _open_directory_at(parent, components[-1])
                        except ValueError as error:
                            try:
                                os.stat(
                                    components[-1],
                                    dir_fd=parent,
                                    follow_symlinks=False,
                                )
                            except FileNotFoundError:
                                missing.append((label, destination, expected_content))
                                continue
                            raise error
                        try:
                            actual = _actual_tree_bytes_from_descriptor(
                                root,
                                label,
                                seen_inodes,
                            )
                        finally:
                            os.close(root)
                    finally:
                        os.close(parent)
            except ValueError as error:
                if "multiply-linked output" in str(error) or "output inode alias" in str(error):
                    raise
                raise ValueError(f"existing {label} drift: {destination}") from error
        else:
            try:
                actual = _read_existing_output_file(
                    repository_descriptor,
                    components,
                    label,
                    seen_inodes,
                    allow_missing=True,
                    retained_entry=retained_entry,
                )
            except ValueError as error:
                if "multiply-linked output" in str(error) or "output inode alias" in str(error):
                    raise
                raise ValueError(f"existing {label} drift: {destination}") from error
            if actual is None:
                missing.append((label, destination, expected_content))
                continue
        if actual != expected_content:
            raise ValueError(f"existing {label} drift: {destination}")
    return missing


def _validate_staged_relative(relative: tuple[str, ...]) -> None:
    if not relative or any(
        not component
        or component in {".", ".."}
        or Path(component).name != component
        for component in relative
    ):
        raise ValueError(f"invalid staged relative path: {'/'.join(relative)}")


def _create_staged_directory(parent_descriptor: int, name: str) -> int:
    _validate_staged_relative((name,))
    os.mkdir(name, mode=0o700, dir_fd=parent_descriptor)
    descriptor: int | None = None
    try:
        descriptor = _open_directory_at(parent_descriptor, name)
        metadata = os.fstat(descriptor)
        if stat.S_IMODE(metadata.st_mode) != 0o700:
            raise ValueError(f"staged directory is not mode 0700: {name}")
        return descriptor
    except BaseException:
        if descriptor is not None:
            retained = descriptor
            descriptor = None
            os.close(retained)
        raise


def _write_staged_file(
    stage: _StagingDirectory,
    relative: tuple[str, ...],
    content: bytes,
) -> None:
    _validate_staged_relative(relative)
    parent = _open_relative_directory(stage.root_descriptor, relative[:-1])
    descriptor: int | None = None
    try:
        descriptor = os.open(
            relative[-1],
            os.O_WRONLY
            | os.O_CREAT
            | os.O_EXCL
            | getattr(os, "O_NOFOLLOW", 0),
            0o600,
            dir_fd=parent,
        )
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or stat.S_IMODE(before.st_mode) != 0o600
            or before.st_nlink != 1
        ):
            raise ValueError(f"staged file is not a private regular file: {'/'.join(relative)}")
        view = memoryview(content)
        written = 0
        while written < len(view):
            written += os.write(descriptor, view[written:])
        _fsync_descriptor(descriptor)
        after = os.fstat(descriptor)
        if (
            (after.st_dev, after.st_ino) != (before.st_dev, before.st_ino)
            or after.st_size != len(content)
            or after.st_nlink != 1
        ):
            raise ValueError(f"staged file changed while written: {'/'.join(relative)}")
    finally:
        if descriptor is not None:
            retained = descriptor
            descriptor = None
            os.close(retained)
        os.close(parent)


def _read_staged_file(
    stage: _StagingDirectory,
    relative: tuple[str, ...],
    label: str,
    seen_inodes: dict[tuple[int, int], str],
) -> bytes:
    _validate_staged_relative(relative)
    parent = _open_relative_directory(stage.root_descriptor, relative[:-1])
    try:
        return _read_output_file_at(
            parent,
            relative[-1],
            label,
            seen_inodes,
        )
    finally:
        os.close(parent)


def _fsync_staged_directory(
    stage: _StagingDirectory,
    relative: tuple[str, ...],
) -> None:
    descriptor = _open_relative_directory(stage.root_descriptor, relative)
    try:
        _fsync_descriptor(descriptor)
    finally:
        os.close(descriptor)


def _stage_freeze(
    stage: _StagingDirectory,
    model: _FreezeModel,
) -> dict[str, tuple[str, ...]]:
    application_descriptor = _create_staged_directory(
        stage.root_descriptor,
        "application_inputs",
    )
    try:
        for name in ("queries", "targets"):
            child = _create_staged_directory(application_descriptor, name)
            os.close(child)
    finally:
        os.close(application_descriptor)

    for relative_text, content in sorted(model.application_files.items()):
        relative = tuple(Path(relative_text).parts)
        if len(relative) != 2 or relative[0] not in {"queries", "targets"}:
            raise ValueError(f"invalid application staging path: {relative_text}")
        _write_staged_file(stage, ("application_inputs", *relative), content)

    staged = {
        "application input tree": ("application_inputs",),
        "selection receipt": ("application_selection.json",),
        "manifest": ("application_manifest.tsv",),
        "manifest checksum": ("application_manifest.sha256",),
        "source ledger": ("application_sources.tsv",),
        "input summary": ("application_input_summary.tsv",),
    }
    _write_staged_file(
        stage,
        staged["selection receipt"],
        model.selection_receipt_bytes,
    )
    _write_staged_file(stage, staged["manifest"], model.manifest_bytes)
    _write_staged_file(
        stage,
        staged["manifest checksum"],
        model.manifest_checksum_bytes,
    )
    _write_staged_file(
        stage,
        staged["source ledger"],
        model.source_ledger_bytes,
    )
    _write_staged_file(stage, staged["input summary"], model.input_summary_bytes)
    for relative in (
        ("application_inputs", "queries"),
        ("application_inputs", "targets"),
        ("application_inputs",),
        (),
    ):
        _fsync_staged_directory(stage, relative)
    return staged


def _parse_staged_tsv(
    content: bytes,
    fieldnames: tuple[str, ...],
    label: str,
) -> list[dict[str, str]]:
    try:
        text = content.decode("utf-8", errors="strict")
    except UnicodeError as error:
        raise ValueError(f"staged {label} is not UTF-8") from error
    reader = csv.DictReader(io.StringIO(text, newline=""), delimiter="\t")
    if tuple(reader.fieldnames or ()) != fieldnames:
        raise ValueError(f"staged {label} has the wrong fields")
    rows = list(reader)
    if any(None in row or set(row) != set(fieldnames) for row in rows):
        raise ValueError(f"staged {label} has malformed rows")
    return rows


def _parse_published_fasta_bytes(content: bytes, label: str) -> tuple[str, str]:
    try:
        text = content.decode("ascii", errors="strict")
    except UnicodeError as error:
        raise ValueError(f"staged FASTA {label} is not ASCII") from error
    if not text.endswith("\n") or "\r" in text:
        raise ValueError(f"staged FASTA {label} has noncanonical line endings")
    lines = text.splitlines()
    if len(lines) < 2 or not lines[0].startswith(">") or not lines[0][1:]:
        raise ValueError(f"staged FASTA {label} has no complete record")
    if any(line.startswith(">") for line in lines[1:]):
        raise ValueError(f"staged FASTA {label} contains more than one record")
    sequence_lines = lines[1:]
    if any(not line or len(line) > 80 for line in sequence_lines):
        raise ValueError(f"staged FASTA {label} has noncanonical wrapping")
    if any(len(line) != 80 for line in sequence_lines[:-1]):
        raise ValueError(f"staged FASTA {label} has noncanonical wrapping")
    sequence = "".join(sequence_lines)
    if not sequence or set(sequence) - CANONICAL_BASES:
        raise ValueError(f"staged FASTA {label} is not canonical ACGT")
    return lines[0][1:], sequence


def _validate_complete_stage(
    stage: _StagingDirectory,
    staged: dict[str, tuple[str, ...]],
    model: _FreezeModel,
    outputs: FreezePaths,
) -> None:
    try:
        if _descriptor_identity(stage.root_descriptor) != stage.root.identity:
            raise ValueError("retained staging root identity changed")
        expected_directories = {
            ("application_inputs",),
            ("application_inputs", "queries"),
            ("application_inputs", "targets"),
        }
        expected_stage_files = {
            ("application_inputs", *Path(relative).parts)
            for relative in model.application_files
        } | {
            relative
            for label, relative in staged.items()
            if label != "application input tree"
        }
        namespace = _tree_namespace_from_descriptor(stage.root_descriptor)
        if set(namespace) != expected_directories | expected_stage_files:
            raise ValueError("staged freeze namespace is incomplete or contains extra entries")
        if any(
            not stat.S_ISDIR(namespace[relative][0])
            for relative in expected_directories
        ) or any(
            not stat.S_ISREG(namespace[relative][0])
            for relative in expected_stage_files
        ):
            raise ValueError("staged freeze namespace contains an invalid entry type")

        seen_inodes: dict[tuple[int, int], str] = {}
        application_descriptor = _open_relative_directory(
            stage.root_descriptor,
            staged["application input tree"],
        )
        try:
            application_files = _actual_tree_bytes_from_descriptor(
                application_descriptor,
                "staged application input tree",
                seen_inodes,
            )
        finally:
            os.close(application_descriptor)
        manifest_bytes = _read_staged_file(
            stage,
            staged["manifest"],
            "staged manifest",
            seen_inodes,
        )
        rows = _parse_staged_tsv(manifest_bytes, MANIFEST_FIELDS, "manifest")
        if len(rows) != QUERY_COUNT + int(model.result["target_count"]):
            raise ValueError("staged manifest record count is inconsistent")

        repository_prefix = Path("reproduce/bioinformatics/application_inputs")
        expected_files: set[str] = set()
        query_rows: list[dict[str, str]] = []
        target_rows: list[dict[str, str]] = []
        for row in rows:
            role = row["record_role"]
            if role not in {"query", "target"}:
                raise ValueError("staged manifest contains an invalid record role")
            record_path = Path(row["path"])
            if record_path.is_absolute() or ".." in record_path.parts:
                raise ValueError("staged manifest contains an unsafe record path")
            try:
                relative_file = record_path.relative_to(repository_prefix).as_posix()
            except ValueError as error:
                raise ValueError("staged manifest path is outside application inputs") from error
            if relative_file in expected_files:
                raise ValueError("staged manifest contains duplicate record paths")
            expected_files.add(relative_file)
            try:
                fasta_bytes = application_files[relative_file]
            except KeyError as error:
                raise ValueError(f"staged FASTA is missing: {relative_file}") from error
            header, sequence = _parse_published_fasta_bytes(fasta_bytes, relative_file)
            if header.split("|", 1)[0] != row["record_id"]:
                raise ValueError("staged FASTA record ID does not match manifest")
            if int(row["sequence_length"]) != len(sequence):
                raise ValueError("staged FASTA sequence length does not match manifest")
            if row["sequence_sha256"] != sequence_sha256(sequence):
                raise ValueError("staged FASTA sequence digest does not match manifest")
            if row["file_sha256"] != hashlib.sha256(fasta_bytes).hexdigest():
                raise ValueError("staged FASTA file digest does not match manifest")
            if any(row[key] != value for key, value in COMMON.items()):
                raise ValueError("staged manifest common metadata drifted")
            if role == "query":
                if any(
                    row[field] != "NA"
                    for field in ("chromosome", "strand", "tss", "region_start", "region_end")
                ):
                    raise ValueError("staged query coordinates must be NA")
                if (
                    row["selection_rule"] != QUERY_SELECTION_RULE
                    or row["license_note"] != QUERY_LICENSE
                ):
                    raise ValueError("staged query provenance metadata drifted")
                query_rows.append(row)
            else:
                if row["chromosome"] not in TARGET_CHROMOSOMES or row["strand"] not in {"+", "-"}:
                    raise ValueError("staged target coordinates are invalid")
                start = int(row["region_start"])
                end = int(row["region_end"])
                int(row["tss"])
                if start <= 0 or end < start or end - start + 1 != len(sequence):
                    raise ValueError("staged target region does not match FASTA sequence")
                if (
                    row["selection_rule"] != TARGET_SELECTION_RULE
                    or row["license_note"] != TARGET_LICENSE
                ):
                    raise ValueError("staged target provenance metadata drifted")
                target_rows.append(row)

        if set(application_files) != expected_files:
            raise ValueError("staged FASTA tree has extra files")
        manifest_sha256 = hashlib.sha256(manifest_bytes).hexdigest()
        freeze_id = FREEZE_ID_PREFIX + manifest_sha256[:8]
        record_summary = _derive_record_summary(
            rows,
            {
                "annotation_target_candidate_count": int(
                    model.result["annotation_target_candidate_count"]
                ),
                "excluded_target_count": int(model.result["excluded_target_count"]),
            },
        )
        derived_summary = {
            "freeze_id": freeze_id,
            "manifest_sha256": manifest_sha256,
            **record_summary,
        }
        summary_bytes = _read_staged_file(
            stage,
            staged["input summary"],
            "staged input summary",
            seen_inodes,
        )
        summary_rows = _parse_staged_tsv(summary_bytes, SUMMARY_FIELDS, "input summary")
        if len(summary_rows) != 1:
            raise ValueError("staged input summary must contain exactly one row")
        if summary_rows[0] != {key: str(value) for key, value in derived_summary.items()}:
            raise ValueError("staged input summary is not derived from manifest and FASTA")

        checksum = _read_staged_file(
            stage,
            staged["manifest checksum"],
            "staged manifest checksum",
            seen_inodes,
        )
        expected_checksum = f"{manifest_sha256}  {outputs.manifest.name}\n".encode("ascii")
        if checksum != expected_checksum:
            raise ValueError("staged manifest checksum is inconsistent")
        source_ledger = _read_staged_file(
            stage,
            staged["source ledger"],
            "staged source ledger",
            seen_inodes,
        )
        source_rows = _parse_staged_tsv(
            source_ledger,
            APPLICATION_SOURCE_FIELDS,
            "source ledger",
        )
        expected_source_ids = [binding[0] for binding in _BIOLOGICAL_SOURCE_BINDINGS]
        if (
            [row["source_id"] for row in source_rows] != expected_source_ids
            or any(row["status"] != "verified" for row in source_rows)
        ):
            raise ValueError("staged source ledger is not a verified four-source ledger")
        receipt_bytes = _read_staged_file(
            stage,
            staged["selection receipt"],
            "staged selection receipt",
            seen_inodes,
        )
        receipt = json.loads(receipt_bytes)
        if receipt_bytes != _canonical_json_bytes(receipt):
            raise ValueError("staged selection receipt is not canonical JSON")
        if (
            receipt.get("manifest_sha256") != manifest_sha256
            or receipt.get("proposed_freeze_id") != freeze_id
            or receipt.get("final_freeze_id") != freeze_id
            or len(receipt.get("selected_queries", ())) != len(query_rows)
            or len(receipt.get("selected_targets", ())) != len(target_rows)
        ):
            raise ValueError("staged selection receipt is inconsistent")

        if manifest_bytes != model.manifest_bytes:
            raise ValueError("staged manifest differs from reconstructed source selection")
        if receipt_bytes != model.selection_receipt_bytes:
            raise ValueError("staged selection receipt differs from reconstructed source selection")
        if checksum != model.manifest_checksum_bytes:
            raise ValueError("staged checksum differs from reconstructed source selection")
        if source_ledger != model.source_ledger_bytes:
            raise ValueError("staged source ledger differs from reconstructed source ledger")
        if summary_bytes != model.input_summary_bytes:
            raise ValueError("staged summary differs from reconstructed source selection")
        if application_files != model.application_files:
            raise ValueError("staged FASTA files differ from reconstructed source selection")
    except (KeyError, OSError, TypeError, UnicodeError, ValueError, json.JSONDecodeError) as error:
        raise ValueError(f"staged freeze validation failed: {error}") from error


def _descriptor_identity(descriptor: int) -> tuple[int, int]:
    metadata = os.fstat(descriptor)
    return metadata.st_dev, metadata.st_ino


def _remove_owned_cache_entry(
    cache_descriptor: int,
    entry_name: str,
    expected_identity: tuple[int, int],
) -> bool:
    if not isinstance(cache_descriptor, int) or isinstance(cache_descriptor, bool):
        raise ValueError("cache descriptor must be an integer")
    if (
        not isinstance(entry_name, str)
        or not entry_name
        or entry_name in {".", ".."}
        or "/" in entry_name
        or "\x00" in entry_name
    ):
        raise ValueError("cache entry name must be one path component")
    if (
        not isinstance(expected_identity, tuple)
        or len(expected_identity) != 2
        or any(
            not isinstance(value, int) or isinstance(value, bool) or value < 0
            for value in expected_identity
        )
    ):
        raise ValueError("cache entry identity must be a device/inode pair")
    if not stat.S_ISDIR(os.fstat(cache_descriptor).st_mode):
        raise ValueError("cache descriptor is not a directory")
    try:
        metadata = os.stat(
            entry_name,
            dir_fd=cache_descriptor,
            follow_symlinks=False,
        )
    except FileNotFoundError:
        return False
    if (
        not stat.S_ISREG(metadata.st_mode)
        or (metadata.st_dev, metadata.st_ino) != expected_identity
    ):
        return False
    os.unlink(entry_name, dir_fd=cache_descriptor)
    return True


def _fsync_descriptor(descriptor: int) -> None:
    os.fsync(descriptor)


def _open_directory_at(parent_descriptor: int, name: str) -> int:
    try:
        descriptor = os.open(name, _output_directory_flags(), dir_fd=parent_descriptor)
    except OSError as error:
        raise ValueError(f"cannot open output directory safely: {name}") from error
    if not stat.S_ISDIR(os.fstat(descriptor).st_mode):
        os.close(descriptor)
        raise ValueError(f"output component is not a directory: {name}")
    return descriptor


def _open_relative_directory(
    root_descriptor: int,
    components: tuple[str, ...],
) -> int:
    current = os.dup(root_descriptor)
    try:
        for component in components:
            child = _open_directory_at(current, component)
            os.close(current)
            current = child
        return current
    except BaseException:
        os.close(current)
        raise


@dataclass
class _CapturedTreeEntry:
    mode: int
    identity: tuple[int, int]
    fingerprint: tuple[int, ...]
    content_sha256: str | None
    state: str = "mutated"


def _tree_entry_fingerprint(metadata: os.stat_result) -> tuple[int, ...]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_uid,
        metadata.st_gid,
        metadata.st_nlink,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    )


def _descriptor_content_sha256(descriptor: int, label: str) -> str:
    before = os.fstat(descriptor)
    before_fingerprint = _tree_entry_fingerprint(before)
    if not stat.S_ISREG(before.st_mode):
        raise ValueError(f"created tree entry is not a regular file: {label}")
    os.lseek(descriptor, 0, os.SEEK_SET)
    digest = hashlib.sha256()
    while block := os.read(descriptor, 1024 * 1024):
        digest.update(block)
    after = os.fstat(descriptor)
    if _tree_entry_fingerprint(after) != before_fingerprint:
        raise ValueError(f"created tree entry changed while read: {label}")
    return digest.hexdigest()


def _verify_captured_entry(
    metadata: os.stat_result,
    captured: _CapturedTreeEntry,
    label: str,
    *,
    allow_owned_directory_changes: bool = False,
) -> None:
    identity = metadata.st_dev, metadata.st_ino
    if identity != captured.identity:
        raise ValueError(f"created tree entry was replaced: {label}")
    if stat.S_IFMT(metadata.st_mode) != stat.S_IFMT(captured.mode):
        raise ValueError(f"created tree entry type changed: {label}")
    if not (
        allow_owned_directory_changes
        and captured.state == "verified"
        and stat.S_ISDIR(captured.mode)
    ) and _tree_entry_fingerprint(metadata) != captured.fingerprint:
        raise ValueError(f"created tree entry metadata changed: {label}")


def _open_captured_tree_entry(
    parent_descriptor: int,
    name: str,
    captured: _CapturedTreeEntry,
    label: str,
    *,
    allow_owned_directory_changes: bool = False,
) -> int:
    descriptor = _open_staged_object(
        parent_descriptor,
        name,
        stat.S_ISDIR(captured.mode),
    )
    try:
        _verify_captured_entry(
            os.fstat(descriptor),
            captured,
            label,
            allow_owned_directory_changes=allow_owned_directory_changes,
        )
        if captured.content_sha256 is not None:
            if _descriptor_content_sha256(descriptor, label) != captured.content_sha256:
                raise ValueError(f"created tree entry content changed: {label}")
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _capture_tree_identities(
    root_descriptor: int,
) -> dict[tuple[str, ...], _CapturedTreeEntry]:
    captured: dict[tuple[str, ...], _CapturedTreeEntry] = {}

    def visit(directory_descriptor: int, prefix: tuple[str, ...]) -> None:
        os.lseek(directory_descriptor, 0, os.SEEK_SET)
        with os.scandir(directory_descriptor) as iterator:
            entries = sorted(iterator, key=lambda entry: entry.name)
        for entry in entries:
            metadata = entry.stat(follow_symlinks=False)
            relative = (*prefix, entry.name)
            if stat.S_ISDIR(metadata.st_mode):
                child = _open_directory_at(directory_descriptor, entry.name)
                try:
                    child_metadata = os.fstat(child)
                    if _tree_entry_fingerprint(child_metadata) != _tree_entry_fingerprint(
                        metadata
                    ):
                        raise ValueError(
                            f"created tree changed during capture: {'/'.join(relative)}"
                        )
                    captured[relative] = _CapturedTreeEntry(
                        mode=metadata.st_mode,
                        identity=(metadata.st_dev, metadata.st_ino),
                        fingerprint=_tree_entry_fingerprint(metadata),
                        content_sha256=None,
                    )
                    visit(child, relative)
                    if _tree_entry_fingerprint(os.fstat(child)) != captured[relative].fingerprint:
                        raise ValueError(
                            f"created tree changed during capture: {'/'.join(relative)}"
                        )
                finally:
                    os.close(child)
            elif stat.S_ISREG(metadata.st_mode):
                child = _open_staged_object(directory_descriptor, entry.name, False)
                try:
                    child_metadata = os.fstat(child)
                    if _tree_entry_fingerprint(child_metadata) != _tree_entry_fingerprint(
                        metadata
                    ):
                        raise ValueError(
                            f"created tree changed during capture: {'/'.join(relative)}"
                        )
                    captured[relative] = _CapturedTreeEntry(
                        mode=metadata.st_mode,
                        identity=(metadata.st_dev, metadata.st_ino),
                        fingerprint=_tree_entry_fingerprint(metadata),
                        content_sha256=_descriptor_content_sha256(
                            child,
                            "/".join(relative),
                        ),
                    )
                finally:
                    os.close(child)
            else:
                raise ValueError(f"created tree contains a non-regular entry: {'/'.join(relative)}")

    visit(root_descriptor, ())
    return captured


def _verify_captured_tree_namespace(
    root_descriptor: int,
    captured: dict[tuple[str, ...], _CapturedTreeEntry],
) -> None:
    seen: set[tuple[str, ...]] = set()

    def visit(directory_descriptor: int, prefix: tuple[str, ...]) -> None:
        os.lseek(directory_descriptor, 0, os.SEEK_SET)
        with os.scandir(directory_descriptor) as iterator:
            entries = sorted(iterator, key=lambda entry: entry.name)
        for entry in entries:
            relative = (*prefix, entry.name)
            captured_entry = captured.get(relative)
            if captured_entry is None or captured_entry.state == "resolved":
                raise ValueError(f"created tree contains an extra entry: {'/'.join(relative)}")
            descriptor = _open_captured_tree_entry(
                directory_descriptor,
                entry.name,
                captured_entry,
                "/".join(relative),
                allow_owned_directory_changes=True,
            )
            try:
                seen.add(relative)
                if stat.S_ISDIR(captured_entry.mode):
                    visit(descriptor, relative)
            finally:
                os.close(descriptor)

    visit(root_descriptor, ())
    expected = {
        relative
        for relative, captured_entry in captured.items()
        if captured_entry.state != "resolved"
    }
    if seen != expected:
        missing = min(expected - seen, default=("unknown",))
        raise ValueError(f"created tree entry is missing or moved: {'/'.join(missing)}")


def _names_for_inode(
    parent_descriptor: int,
    identity: tuple[int, int],
) -> list[str]:
    os.lseek(parent_descriptor, 0, os.SEEK_SET)
    with os.scandir(parent_descriptor) as iterator:
        entries = tuple(iterator)
    names: list[str] = []
    for candidate in entries:
        try:
            metadata = candidate.stat(follow_symlinks=False)
        except FileNotFoundError:
            continue
        if (metadata.st_dev, metadata.st_ino) == identity:
            names.append(candidate.name)
    return sorted(names)


def _remove_captured_tree_entries(
    root_descriptor: int,
    captured: dict[tuple[str, ...], _CapturedTreeEntry],
) -> None:
    _verify_captured_tree_namespace(root_descriptor, captured)
    for captured_entry in captured.values():
        if captured_entry.state == "mutated":
            captured_entry.state = "verified"

    def remove(directory_descriptor: int, prefix: tuple[str, ...]) -> None:
        os.lseek(directory_descriptor, 0, os.SEEK_SET)
        with os.scandir(directory_descriptor) as iterator:
            entries = sorted(iterator, key=lambda entry: entry.name)
        for entry in entries:
            relative = (*prefix, entry.name)
            captured_entry = captured.get(relative)
            if captured_entry is None or captured_entry.state == "resolved":
                raise OSError(f"created tree contains an unrelated entry: {'/'.join(relative)}")
            descriptor = _open_captured_tree_entry(
                directory_descriptor,
                entry.name,
                captured_entry,
                "/".join(relative),
                allow_owned_directory_changes=True,
            )
            try:
                if stat.S_ISDIR(captured_entry.mode):
                    remove(descriptor, relative)
                    os.rmdir(entry.name, dir_fd=directory_descriptor)
                else:
                    os.unlink(entry.name, dir_fd=directory_descriptor)
                if os.fstat(descriptor).st_nlink != 0:
                    raise OSError(
                        f"created tree entry moved outside tree: {'/'.join(relative)}"
                    )
                captured_entry.state = "resolved"
            finally:
                os.close(descriptor)

    remove(root_descriptor, ())


@dataclass(eq=False)
class _CreatedEntry:
    display_path: Path
    parent_descriptor: int | None
    parent_identity: tuple[int, int]
    name: str
    object_identity: tuple[int, int] | None
    is_directory: bool
    recursive: bool
    object_descriptor: int | None
    captured_tree: dict[tuple[str, ...], _CapturedTreeEntry]
    source_link_count: int | None
    state: str = "pending"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Path):
            return self.display_path == other
        return self is other

    def close(self) -> None:
        errors: list[BaseException] = []
        if self.parent_descriptor is not None:
            descriptor = self.parent_descriptor
            if _descriptor_identity(descriptor) != self.parent_identity:
                errors.append(
                    ValueError(
                        f"published parent identity changed before closure: {self.display_path}"
                    )
                )
            else:
                self.parent_descriptor = None
                try:
                    os.close(descriptor)
                except BaseException as error:
                    errors.append(error)
        if self.object_descriptor is not None:
            descriptor = self.object_descriptor
            if (
                self.object_identity is not None
                and _descriptor_identity(descriptor) != self.object_identity
            ):
                errors.append(
                    ValueError(
                        f"published object identity changed before closure: {self.display_path}"
                    )
                )
            else:
                self.object_descriptor = None
                try:
                    os.close(descriptor)
                except BaseException as error:
                    errors.append(error)
        if errors:
            raise RuntimeError("; ".join(str(error) for error in errors))

    @property
    def resolved(self) -> bool:
        return self.state == "resolved"

    @resolved.setter
    def resolved(self, value: bool) -> None:
        self.state = "resolved" if value else "mutated"


@dataclass
class _TimestampRecord:
    descriptor: int | None
    identity: tuple[int, int]
    access_time_ns: int
    modification_time_ns: int

    def close(self) -> None:
        if self.descriptor is not None:
            descriptor = self.descriptor
            if _descriptor_identity(descriptor) != self.identity:
                raise ValueError("timestamp descriptor identity changed before closure")
            self.descriptor = None
            os.close(descriptor)


@dataclass
class _OwnedDescriptor:
    descriptor: int | None
    identity: tuple[int, int]

    def close(self) -> None:
        if self.descriptor is not None:
            descriptor = self.descriptor
            if _descriptor_identity(descriptor) != self.identity:
                raise ValueError("owned descriptor identity changed before closure")
            self.descriptor = None
            os.close(descriptor)

    def close_reliably(self, label: str) -> None:
        last_error: BaseException | None = None
        for _attempt in range(3):
            try:
                self.close()
            except BaseException as error:
                last_error = error
            if self.descriptor is None:
                return
        raise RuntimeError(
            f"{label} descriptor closure failed after retries: {last_error}"
        ) from last_error


def _remove_created_path(entry: _CreatedEntry) -> None:
    if entry.resolved:
        return
    if entry.parent_descriptor is None:
        raise ValueError(f"published parent descriptor is closed: {entry.display_path.parent}")
    if _descriptor_identity(entry.parent_descriptor) != entry.parent_identity:
        raise ValueError(f"published parent identity changed: {entry.display_path.parent}")
    if entry.object_identity is None:
        try:
            os.stat(entry.name, dir_fd=entry.parent_descriptor, follow_symlinks=False)
        except FileNotFoundError:
            entry.state = "resolved"
            return
        raise OSError(f"pending publication cannot be identified safely: {entry.display_path}")
    if entry.recursive and entry.object_descriptor is not None:
        if _descriptor_identity(entry.object_descriptor) != entry.object_identity:
            raise ValueError(f"published tree identity changed: {entry.display_path}")
        _remove_captured_tree_entries(entry.object_descriptor, entry.captured_tree)
    matching_names = _names_for_inode(entry.parent_descriptor, entry.object_identity)
    if len(matching_names) > 1:
        raise OSError(f"published entry is multiply linked in its parent: {entry.display_path}")
    if not matching_names:
        if entry.state == "pending":
            if entry.object_descriptor is None:
                entry.state = "resolved"
                return
            current_links = os.fstat(entry.object_descriptor).st_nlink
            if entry.source_link_count is not None and current_links == entry.source_link_count:
                entry.state = "resolved"
                return
        if entry.object_descriptor is not None and os.fstat(entry.object_descriptor).st_nlink == 0:
            entry.state = "resolved"
            return
        raise OSError(f"published entry moved outside retained parent: {entry.display_path}")
    actual_name = matching_names[0]
    if entry.is_directory:
        os.rmdir(actual_name, dir_fd=entry.parent_descriptor)
    else:
        os.unlink(actual_name, dir_fd=entry.parent_descriptor)
    if _names_for_inode(entry.parent_descriptor, entry.object_identity):
        raise OSError(f"published entry still exists after rollback: {entry.display_path}")
    if entry.source_link_count is not None and entry.object_descriptor is not None:
        if os.fstat(entry.object_descriptor).st_nlink != entry.source_link_count:
            raise OSError(f"published link count did not roll back: {entry.display_path}")
    entry.state = "resolved"


def _open_staged_object(
    parent_descriptor: int,
    name: str,
    is_directory: bool,
) -> int:
    if is_directory:
        return _open_directory_at(parent_descriptor, name)
    try:
        try:
            descriptor = os.open(
                name,
                os.O_RDONLY
                | getattr(os, "O_NOFOLLOW", 0)
                | getattr(os, "O_NOATIME", 0),
                dir_fd=parent_descriptor,
            )
        except PermissionError:
            descriptor = os.open(
                name,
                os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0),
                dir_fd=parent_descriptor,
            )
    except OSError as error:
        raise ValueError(f"cannot retain staged publication object safely: {name}") from error
    if not stat.S_ISREG(os.fstat(descriptor).st_mode):
        os.close(descriptor)
        raise ValueError(f"staged publication object is not a regular file: {name}")
    return descriptor


def _remove_staging_tree_contents(
    directory_descriptor: int,
    prefix: tuple[str, ...] = (),
) -> None:
    os.lseek(directory_descriptor, 0, os.SEEK_SET)
    with os.scandir(directory_descriptor) as iterator:
        entries = sorted(iterator, key=lambda entry: entry.name)
    for entry in entries:
        relative = (*prefix, entry.name)
        metadata = entry.stat(follow_symlinks=False)
        if stat.S_ISDIR(metadata.st_mode):
            child = _open_directory_at(directory_descriptor, entry.name)
            try:
                if _descriptor_identity(child) != (metadata.st_dev, metadata.st_ino):
                    raise ValueError(
                        f"staging directory changed during cleanup: {'/'.join(relative)}"
                    )
                _remove_staging_tree_contents(child, relative)
                os.rmdir(entry.name, dir_fd=directory_descriptor)
                if os.fstat(child).st_nlink != 0:
                    raise OSError(
                        f"staging directory moved during cleanup: {'/'.join(relative)}"
                    )
            finally:
                os.close(child)
        elif stat.S_ISREG(metadata.st_mode):
            child = _open_staged_object(directory_descriptor, entry.name, False)
            try:
                retained = os.fstat(child)
                if (retained.st_dev, retained.st_ino) != (
                    metadata.st_dev,
                    metadata.st_ino,
                ):
                    raise ValueError(
                        f"staging file changed during cleanup: {'/'.join(relative)}"
                    )
                os.unlink(entry.name, dir_fd=directory_descriptor)
                if os.fstat(child).st_nlink != retained.st_nlink - 1:
                    raise OSError(
                        f"staging file moved during cleanup: {'/'.join(relative)}"
                    )
            finally:
                os.close(child)
        else:
            raise ValueError(
                f"staging tree contains an unrelated entry: {'/'.join(relative)}"
            )


@dataclass
class _StagingDirectory:
    display_path: Path
    name: str
    parent: _OwnedDescriptor
    root: _OwnedDescriptor
    cleaned: bool = False

    @classmethod
    def create(cls, parent_path: Path, prefix: str) -> _StagingDirectory:
        if not prefix or Path(prefix).name != prefix or prefix in {".", ".."}:
            raise ValueError(f"invalid staging directory prefix: {prefix!r}")
        parent_descriptor = _open_output_directory(parent_path, "staging parent")
        parent = _OwnedDescriptor(
            descriptor=parent_descriptor,
            identity=_descriptor_identity(parent_descriptor),
        )
        name: str | None = None
        created_identity: tuple[int, int] | None = None
        root_descriptor: int | None = None
        root: _OwnedDescriptor | None = None
        stage: _StagingDirectory | None = None
        try:
            for _attempt in range(128):
                candidate = f"{prefix}{os.urandom(8).hex()}"
                try:
                    os.mkdir(candidate, mode=0o700, dir_fd=parent_descriptor)
                except FileExistsError:
                    continue
                name = candidate
                break
            if name is None:
                raise FileExistsError("cannot allocate a unique staging directory name")

            created = os.stat(name, dir_fd=parent_descriptor, follow_symlinks=False)
            created_identity = (created.st_dev, created.st_ino)
            if not stat.S_ISDIR(created.st_mode) or stat.S_IMODE(created.st_mode) != 0o700:
                raise ValueError("created staging entry is not a 0700 directory")
            root_descriptor = _open_directory_at(parent_descriptor, name)
            root_identity = _descriptor_identity(root_descriptor)
            root = _OwnedDescriptor(
                descriptor=root_descriptor,
                identity=root_identity,
            )
            root_descriptor = None
            if root_identity != created_identity:
                root.close_reliably("unbound staging root")
                root = None
                raise ValueError("created staging directory changed before it was retained")
            stage = cls(
                display_path=parent_path / name,
                name=name,
                parent=parent,
                root=root,
            )
            root = None
            return stage
        except BaseException as primary_error:
            recovery_errors: list[BaseException] = []
            if stage is not None:
                try:
                    stage.cleanup_reliably()
                except BaseException as error:
                    recovery_errors.append(error)
            else:
                if root is not None:
                    try:
                        root.close_reliably("staging root")
                    except BaseException as error:
                        recovery_errors.append(error)
                elif root_descriptor is not None:
                    descriptor = root_descriptor
                    root_descriptor = None
                    try:
                        os.close(descriptor)
                    except BaseException as error:
                        recovery_errors.append(error)
                if created_identity is None and name is not None:
                    try:
                        recoverable = os.stat(
                            name,
                            dir_fd=parent_descriptor,
                            follow_symlinks=False,
                        )
                        if (
                            not stat.S_ISDIR(recoverable.st_mode)
                            or stat.S_IMODE(recoverable.st_mode) != 0o700
                        ):
                            raise ValueError(
                                "unbound staging entry is not the created 0700 directory"
                            )
                        created_identity = (
                            recoverable.st_dev,
                            recoverable.st_ino,
                        )
                    except BaseException as error:
                        recovery_errors.append(error)
                if created_identity is not None:
                    try:
                        matching_names = _names_for_inode(
                            parent_descriptor,
                            created_identity,
                        )
                        if len(matching_names) != 1:
                            raise OSError(
                                "created staging inode cannot be resolved in retained parent"
                            )
                        os.rmdir(matching_names[0], dir_fd=parent_descriptor)
                        if _names_for_inode(parent_descriptor, created_identity):
                            raise OSError("created staging inode remains after cleanup")
                    except BaseException as error:
                        recovery_errors.append(error)
                try:
                    parent.close_reliably("staging parent")
                except BaseException as error:
                    recovery_errors.append(error)
            if recovery_errors:
                details = "; ".join(str(error) for error in recovery_errors)
                raise RuntimeError(
                    f"staging creation recovery failed: {details}"
                ) from primary_error
            raise

    @property
    def root_descriptor(self) -> int:
        if self.root.descriptor is None:
            raise ValueError("staging root descriptor is closed")
        return self.root.descriptor

    def _cleanup_once(self) -> None:
        if self.cleaned:
            return
        if self.parent.descriptor is None or self.root.descriptor is None:
            raise ValueError("staging ownership was released before cleanup")
        if _descriptor_identity(self.parent.descriptor) != self.parent.identity:
            raise ValueError("staging parent descriptor identity changed")
        if _descriptor_identity(self.root.descriptor) != self.root.identity:
            raise ValueError("staging root descriptor identity changed")
        matching_names = _names_for_inode(self.parent.descriptor, self.root.identity)
        if not matching_names:
            if os.fstat(self.root.descriptor).st_nlink == 0:
                self.cleaned = True
                return
            raise OSError("retained staging directory moved outside its retained parent")
        if len(matching_names) != 1:
            raise OSError("retained staging directory has multiple parent bindings")
        actual_name = matching_names[0]
        _remove_staging_tree_contents(self.root.descriptor)
        os.rmdir(actual_name, dir_fd=self.parent.descriptor)
        if _names_for_inode(self.parent.descriptor, self.root.identity):
            raise OSError("retained staging directory remains after cleanup")
        if os.fstat(self.root.descriptor).st_nlink != 0:
            raise OSError("retained staging directory moved during cleanup")
        self.cleaned = True

    def close(self) -> None:
        errors: list[BaseException] = []
        for label, owner in (("staging root", self.root), ("staging parent", self.parent)):
            try:
                owner.close_reliably(label)
            except BaseException as error:
                errors.append(error)
        if errors:
            raise RuntimeError("; ".join(str(error) for error in errors))

    def cleanup_reliably(self) -> None:
        last_error: BaseException | None = None
        for _attempt in range(3):
            try:
                self._cleanup_once()
            except BaseException as error:
                last_error = error
            else:
                self.close()
                return
        try:
            self.close()
        except BaseException as close_error:
            last_error = RuntimeError(f"{last_error}; {close_error}")
        raise RuntimeError(
            f"staging cleanup failed after retries: {last_error}"
        ) from last_error


def _bind_pending_entry(entry: _CreatedEntry) -> None:
    if entry.state != "pending":
        raise ValueError(f"publication entry is not pending: {entry.display_path}")
    if entry.parent_descriptor is None:
        raise ValueError(f"pending publication parent is closed: {entry.display_path.parent}")
    metadata = os.stat(
        entry.name,
        dir_fd=entry.parent_descriptor,
        follow_symlinks=False,
    )
    identity = (metadata.st_dev, metadata.st_ino)
    if entry.object_identity is not None and identity != entry.object_identity:
        raise ValueError(f"published object identity changed: {entry.display_path}")
    if stat.S_ISDIR(metadata.st_mode) != entry.is_directory:
        raise ValueError(f"published object type changed: {entry.display_path}")
    entry.object_identity = identity
    entry.state = "mutated"
    if entry.object_descriptor is None and entry.is_directory:
        entry.object_descriptor = _open_directory_at(
            entry.parent_descriptor,
            entry.name,
        )
    if entry.object_descriptor is not None:
        if _descriptor_identity(entry.object_descriptor) != identity:
            raise ValueError(f"retained published object changed: {entry.display_path}")


@dataclass
class _PublicationJournal:
    created: list[_CreatedEntry]
    timestamps: dict[tuple[int, int], _TimestampRecord]
    owned_descriptors: list[_OwnedDescriptor] = field(default_factory=list)
    rollback_reserve: list[_OwnedDescriptor] = field(default_factory=list)
    armed: bool = True

    def adopt_descriptor(self, descriptor: int) -> None:
        self.owned_descriptors.append(
            _OwnedDescriptor(
                descriptor=descriptor,
                identity=_descriptor_identity(descriptor),
            )
        )

    def reserve_rollback_capacity(self, descriptor: int) -> None:
        if self.rollback_reserve:
            raise ValueError("rollback descriptor capacity was already reserved")
        for _index in range(_ROLLBACK_DESCRIPTOR_RESERVE_COUNT):
            retained = os.dup(descriptor)
            self.rollback_reserve.append(
                _OwnedDescriptor(
                    descriptor=retained,
                    identity=_descriptor_identity(retained),
                )
            )

    def _release_rollback_capacity(self) -> None:
        errors: list[BaseException] = []
        for record in self.rollback_reserve:
            try:
                record.close()
            except BaseException as error:
                errors.append(error)
        if errors and any(record.descriptor is not None for record in self.rollback_reserve):
            raise RuntimeError("; ".join(str(error) for error in errors))

    def record_timestamp(self, descriptor: int) -> None:
        metadata = os.fstat(descriptor)
        identity = (metadata.st_dev, metadata.st_ino)
        if identity not in self.timestamps:
            self.timestamps[identity] = _TimestampRecord(
                descriptor=os.dup(descriptor),
                identity=identity,
                access_time_ns=metadata.st_atime_ns,
                modification_time_ns=metadata.st_mtime_ns,
            )

    def record_pending(
        self,
        *,
        parent_descriptor: int,
        name: str,
        display_path: Path,
        recursive: bool,
        is_directory: bool,
        source_parent_descriptor: int | None = None,
        source_name: str | None = None,
    ) -> _CreatedEntry:
        retained_parent = os.dup(parent_descriptor)
        object_descriptor: int | None = None
        try:
            object_identity: tuple[int, int] | None = None
            captured_tree: dict[tuple[str, ...], _CapturedTreeEntry] = {}
            source_link_count: int | None = None
            if source_parent_descriptor is not None:
                if source_name is None:
                    raise ValueError("staged publication source name is required")
                object_descriptor = _open_staged_object(
                    source_parent_descriptor,
                    source_name,
                    is_directory,
                )
                metadata = os.fstat(object_descriptor)
                object_identity = (metadata.st_dev, metadata.st_ino)
                source_link_count = metadata.st_nlink
                if recursive:
                    captured_tree = _capture_tree_identities(object_descriptor)
            entry = _CreatedEntry(
                display_path=display_path,
                parent_descriptor=retained_parent,
                parent_identity=_descriptor_identity(parent_descriptor),
                name=name,
                object_identity=object_identity,
                is_directory=is_directory,
                recursive=recursive,
                object_descriptor=object_descriptor,
                captured_tree=captured_tree,
                source_link_count=source_link_count,
            )
            self.created.append(entry)
            return entry
        except BaseException:
            os.close(retained_parent)
            if object_descriptor is not None:
                os.close(object_descriptor)
            raise

    def record_created(
        self,
        *,
        parent_descriptor: int,
        name: str,
        display_path: Path,
        recursive: bool,
    ) -> None:
        parent_identity = _descriptor_identity(parent_descriptor)
        for entry in reversed(self.created):
            if entry.display_path != display_path or entry.name != name:
                continue
            if entry.parent_identity != parent_identity or entry.recursive != recursive:
                raise ValueError(f"pending publication registration drift: {display_path}")
            if entry.state != "mutated" or entry.object_identity is None:
                raise ValueError(f"publication mutation was not bound: {display_path}")
            return
        raise ValueError(f"publication mutation had no pending intent: {display_path}")

    def _close(self) -> None:
        errors: list[BaseException] = []
        for entry in self.created:
            try:
                entry.close()
            except BaseException as error:
                errors.append(error)
        for record in self.timestamps.values():
            try:
                record.close()
            except BaseException as error:
                errors.append(error)
        for record in self.owned_descriptors:
            try:
                record.close()
            except BaseException as error:
                errors.append(error)
        for record in self.rollback_reserve:
            try:
                record.close()
            except BaseException as error:
                errors.append(error)
        if errors:
            raise RuntimeError("; ".join(str(error) for error in errors))

    def _all_descriptors_closed(self) -> bool:
        return all(
            entry.parent_descriptor is None
            and entry.object_descriptor is None
            for entry in self.created
        ) and all(
            record.descriptor is None for record in self.timestamps.values()
        ) and all(
            record.descriptor is None for record in self.owned_descriptors
        ) and all(record.descriptor is None for record in self.rollback_reserve)

    def _close_reliably(self) -> None:
        last_error: BaseException | None = None
        for _attempt in range(3):
            try:
                self._close()
            except BaseException as error:
                last_error = error
            if self._all_descriptors_closed():
                return
        raise RuntimeError(f"journal descriptor closure failed after retries: {last_error}") from last_error

    def commit(self) -> None:
        if self.armed:
            self._close_reliably()
            self.armed = False

    def release_after_recovery_failure(self) -> None:
        if self.armed:
            self._close_reliably()

    def rollback(self) -> None:
        if not self.armed:
            return
        self._release_rollback_capacity()
        last_errors: list[BaseException] = []
        for _attempt in range(3):
            last_errors = []
            for entry in reversed(self.created):
                if entry.resolved:
                    continue
                try:
                    _remove_created_path(entry)
                except BaseException as error:
                    last_errors.append(error)
            if all(entry.resolved for entry in self.created):
                for record in self.timestamps.values():
                    if record.descriptor is None:
                        last_errors.append(ValueError("timestamp target descriptor is closed"))
                        continue
                    if _descriptor_identity(record.descriptor) != record.identity:
                        last_errors.append(ValueError("timestamp target identity changed"))
                        continue
                    os.utime(
                        record.descriptor,
                        ns=(record.access_time_ns, record.modification_time_ns),
                    )
                    restored = os.fstat(record.descriptor)
                    if (
                        restored.st_atime_ns != record.access_time_ns
                        or restored.st_mtime_ns != record.modification_time_ns
                    ):
                        last_errors.append(OSError("timestamp restoration did not persist"))
                if not last_errors:
                    self._close_reliably()
                    self.armed = False
                    return
        message = "; ".join(str(error) for error in last_errors) or "rollback incomplete"
        raise RuntimeError(f"publication rollback failed after retries: {message}")


def _open_or_create_output_directory(
    repository_descriptor: int,
    repository_root: Path,
    components: tuple[str, ...],
    journal: _PublicationJournal,
) -> int:
    current = os.dup(repository_descriptor)
    display = repository_root
    try:
        for component in components:
            display /= component
            try:
                child = _open_directory_at(current, component)
            except ValueError as original_error:
                try:
                    os.stat(component, dir_fd=current, follow_symlinks=False)
                except FileNotFoundError:
                    journal.record_timestamp(current)
                    pending = journal.record_pending(
                        parent_descriptor=current,
                        name=component,
                        display_path=display,
                        recursive=False,
                        is_directory=True,
                    )
                    os.mkdir(component, dir_fd=current)
                    _bind_pending_entry(pending)
                    journal.record_created(
                        parent_descriptor=current,
                        name=component,
                        display_path=display,
                        recursive=False,
                    )
                    if pending.object_descriptor is None:
                        raise ValueError(f"created output directory was not retained: {display}")
                    child = os.dup(pending.object_descriptor)
                    _fsync_descriptor(current)
                else:
                    raise original_error
            os.close(current)
            current = child
        return current
    except BaseException:
        os.close(current)
        raise


def _verify_retained_parent(
    repository_descriptor: int,
    components: tuple[str, ...],
    retained_descriptor: int,
) -> None:
    current = _open_relative_directory(repository_descriptor, components)
    try:
        if _descriptor_identity(current) != _descriptor_identity(retained_descriptor):
            raise ValueError(f"output parent identity changed: {'/'.join(components)}")
    finally:
        os.close(current)


def _verify_repository_path_binding(
    repository_root: Path,
    retained_descriptor: int,
) -> None:
    try:
        current, component_chain = _open_file_and_chain_by_no_follow_walk(
            repository_root,
            _output_directory_flags(),
        )
    except (OSError, ValueError) as error:
        raise ValueError(f"repository root identity changed: {repository_root}") from error
    owner = _OwnedDescriptor(
        descriptor=current,
        identity=component_chain[-1],
    )
    try:
        if component_chain[-1] != _descriptor_identity(retained_descriptor):
            raise ValueError(f"repository root identity changed: {repository_root}")
    finally:
        owner.close_reliably("repository path verification")


@contextmanager
def _publication_guard(repository_root: Path) -> Iterator[int]:
    with _PUBLICATION_LOCK:
        try:
            descriptor, component_chain = _open_file_and_chain_by_no_follow_walk(
                repository_root,
                _output_directory_flags(),
            )
        except OSError as error:
            raise ValueError(f"cannot lock repository root safely: {repository_root}") from error
        owned_descriptor = _OwnedDescriptor(
            descriptor=descriptor,
            identity=component_chain[-1],
        )
        try:
            if not stat.S_ISDIR(os.fstat(descriptor).st_mode):
                raise ValueError(f"repository root is not a directory: {repository_root}")
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            try:
                yield descriptor
            finally:
                fcntl.flock(descriptor, fcntl.LOCK_UN)
        finally:
            owned_descriptor.close_reliably("repository guard")


def _publish_staged(
    *,
    stage: _StagingDirectory,
    staged: dict[str, tuple[str, ...]],
    missing: list[tuple[str, Path, bytes | dict[str, bytes]]],
    outputs: FreezePaths,
    repository_descriptor: int,
    journal: _PublicationJournal,
    after_publish: Callable[[int, Path], None] | None,
) -> tuple[int | None, int | None]:
    stage_descriptor = stage.root_descriptor
    journal.reserve_rollback_capacity(stage_descriptor)
    application_parent: int | None = None
    metadata_parent: int | None = None
    step = 0
    for label, destination, _ in missing:
        source_relative = staged[label]
        if len(source_relative) != 1:
            raise ValueError(f"staged publication source is not a root entry: {label}")
        source_name = source_relative[0]
        if label == "application input tree":
            if application_parent is None:
                application_parent = _open_or_create_output_directory(
                    repository_descriptor,
                    outputs.repository_root,
                    ("reproduce", "bioinformatics"),
                    journal,
                )
                journal.adopt_descriptor(application_parent)
            parent = application_parent
        else:
            if metadata_parent is None:
                metadata_parent = _open_or_create_output_directory(
                    repository_descriptor,
                    outputs.repository_root,
                    ("paper", "bioinformatics"),
                    journal,
                )
                journal.adopt_descriptor(metadata_parent)
            parent = metadata_parent
        try:
            os.stat(destination.name, dir_fd=parent, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            raise ValueError(f"concurrent destination appeared during publication: {destination}")
        journal.record_timestamp(parent)
        pending = journal.record_pending(
            parent_descriptor=parent,
            name=destination.name,
            display_path=destination,
            recursive=label == "application input tree",
            is_directory=label == "application input tree",
            source_parent_descriptor=stage_descriptor,
            source_name=source_name,
        )
        if label == "application input tree":
            os.rename(
                source_name,
                destination.name,
                src_dir_fd=stage_descriptor,
                dst_dir_fd=parent,
            )
        else:
            os.link(
                source_name,
                destination.name,
                src_dir_fd=stage_descriptor,
                dst_dir_fd=parent,
                follow_symlinks=False,
            )
        _bind_pending_entry(pending)
        journal.record_created(
            parent_descriptor=parent,
            name=destination.name,
            display_path=destination,
            recursive=label == "application input tree",
        )
        _fsync_descriptor(parent)
        step += 1
        if after_publish is not None:
            after_publish(step, destination)
    return application_parent, metadata_parent


def _cleanup_stage_reliably(stage: _StagingDirectory) -> None:
    stage.cleanup_reliably()


def _rollback_after_failure(
    primary_error: BaseException,
    journal: _PublicationJournal,
    stage: _StagingDirectory,
) -> None:
    rollback_error: BaseException | None = None
    try:
        journal.rollback()
    except BaseException as error:
        rollback_error = error
        try:
            journal.release_after_recovery_failure()
        except BaseException as close_error:
            rollback_error = RuntimeError(f"{error}; {close_error}")
    cleanup_error: BaseException | None = None
    try:
        _cleanup_stage_reliably(stage)
    except BaseException as error:
        cleanup_error = error
    if rollback_error is not None or cleanup_error is not None:
        details = "; ".join(
            str(error) for error in (rollback_error, cleanup_error) if error is not None
        )
        raise RuntimeError(f"transaction recovery failed: {details}") from primary_error


def _publish_prepared_freeze(
    model: _FreezeModel,
    outputs: FreezePaths,
    after_publish: Callable[[int, Path], None] | None,
) -> dict[str, object]:
    with _publication_guard(outputs.repository_root) as repository_descriptor:
        _validate_freeze_paths(outputs)
        missing = _preflight_existing(repository_descriptor, outputs, model)
        if not missing:
            _verify_repository_path_binding(
                outputs.repository_root,
                repository_descriptor,
            )
            return dict(model.result)
        stage = _StagingDirectory.create(
            outputs.repository_root.parent,
            f".{outputs.repository_root.name}.application-freeze-stage.",
        )
        journal = _PublicationJournal(created=[], timestamps={})
        application_parent: int | None = None
        metadata_parent: int | None = None
        try:
            staged = _stage_freeze(stage, model)
            _validate_complete_stage(stage, staged, model, outputs)
            application_parent, metadata_parent = _publish_staged(
                stage=stage,
                staged=staged,
                missing=missing,
                outputs=outputs,
                repository_descriptor=repository_descriptor,
                journal=journal,
                after_publish=after_publish,
            )
            _cleanup_stage_reliably(stage)
            if application_parent is not None:
                _verify_retained_parent(
                    repository_descriptor,
                    ("reproduce", "bioinformatics"),
                    application_parent,
                )
            if metadata_parent is not None:
                _verify_retained_parent(
                    repository_descriptor,
                    ("paper", "bioinformatics"),
                    metadata_parent,
                )
            if _preflight_existing(repository_descriptor, outputs, model, journal):
                raise ValueError("published freeze is incomplete after stage cleanup")
            _verify_repository_path_binding(
                outputs.repository_root,
                repository_descriptor,
            )
        except BaseException as primary_error:
            _rollback_after_failure(primary_error, journal, stage)
            raise
        journal.commit()
    return dict(model.result)


def build_freeze(
    inputs: SourceInputs,
    outputs: FreezePaths,
    after_publish: Callable[[int, Path], None] | None = None,
) -> dict[str, object]:
    model = _prepare_freeze(inputs, outputs)
    return _publish_prepared_freeze(model, outputs, after_publish)


def verify_freeze(
    inputs: SourceInputs,
    outputs: FreezePaths,
    selection: Path,
) -> dict[str, object]:
    model = _prepare_freeze(inputs, outputs)
    with _publication_guard(outputs.repository_root) as repository_descriptor:
        _validate_freeze_paths(outputs)
        _compare_selection_receipt(model.selection_receipt_bytes, selection)
        missing = _preflight_existing(repository_descriptor, outputs, model)
        if missing:
            labels = ", ".join(label for label, _path, _content in missing)
            raise ValueError(f"existing freeze is incomplete: {labels}")
        _compare_selection_receipt(model.selection_receipt_bytes, selection)
        _verify_repository_path_binding(
            outputs.repository_root,
            repository_descriptor,
        )
    return dict(model.result)


def select_freeze(
    inputs: SourceInputs,
    outputs: FreezePaths,
) -> dict[str, object]:
    model = _prepare_freeze(inputs, outputs)
    with _publication_guard(outputs.repository_root) as repository_descriptor:
        _validate_freeze_paths(outputs)
        destination = outputs.selection_receipt
        try:
            existing = _read_existing_output_file(
                repository_descriptor,
                ("paper", "bioinformatics", "application_selection.json"),
                "selection receipt",
                {},
                allow_missing=True,
            )
        except ValueError as error:
            raise ValueError(f"existing selection receipt drift: {destination}") from error
        if existing is not None:
            if existing != model.selection_receipt_bytes:
                raise ValueError(f"existing selection receipt drift: {destination}")
            _verify_repository_path_binding(
                outputs.repository_root,
                repository_descriptor,
            )
            return dict(model.result)

        stage = _StagingDirectory.create(
            outputs.repository_root.parent,
            f".{outputs.repository_root.name}.application-select-stage.",
        )
        journal = _PublicationJournal(created=[], timestamps={})
        metadata_parent: int | None = None
        try:
            staged_receipt = ("application_selection.json",)
            _write_staged_file(stage, staged_receipt, model.selection_receipt_bytes)
            _fsync_staged_directory(stage, ())
            if (
                _read_staged_file(
                    stage,
                    staged_receipt,
                    "staged selection receipt",
                    {},
                )
                != model.selection_receipt_bytes
            ):
                raise ValueError("staged selection receipt failed validation")
            _application_parent, metadata_parent = _publish_staged(
                stage=stage,
                staged={"selection receipt": staged_receipt},
                missing=[
                    (
                        "selection receipt",
                        destination,
                        model.selection_receipt_bytes,
                    )
                ],
                outputs=outputs,
                repository_descriptor=repository_descriptor,
                journal=journal,
                after_publish=None,
            )
            _cleanup_stage_reliably(stage)
            if metadata_parent is None:
                raise ValueError("selection publication did not retain metadata parent")
            _verify_retained_parent(
                repository_descriptor,
                ("paper", "bioinformatics"),
                metadata_parent,
            )
            if (
                _read_existing_output_file(
                    repository_descriptor,
                    ("paper", "bioinformatics", "application_selection.json"),
                    "selection receipt",
                    {},
                    retained_entry=next(
                        entry
                        for entry in journal.created
                        if entry.display_path == destination and entry.state == "mutated"
                    ),
                )
                != model.selection_receipt_bytes
            ):
                raise ValueError("published selection receipt drifted after stage cleanup")
            _verify_repository_path_binding(
                outputs.repository_root,
                repository_descriptor,
            )
        except BaseException as primary_error:
            _rollback_after_failure(primary_error, journal, stage)
            raise
        journal.commit()
    return dict(model.result)


def _compare_selection_receipt(
    expected: bytes,
    selection: Path,
) -> None:
    selection_path = _lexical_absolute(selection, "selection receipt input")
    _validate_no_symlink_components(selection_path, "selection receipt input")
    try:
        actual = _read_regular_file_no_follow(selection_path)
    except ValueError as error:
        raise ValueError(f"selection receipt drift: {selection}") from error
    if actual != expected:
        raise ValueError(f"selection receipt drift: {selection}")


def _add_common_cli_arguments(command: argparse.ArgumentParser) -> None:
    command.add_argument("--repository-root", type=Path, required=True)
    command.add_argument("--lncrna-fasta", type=Path, required=True)
    command.add_argument("--annotation-gtf", type=Path, required=True)
    command.add_argument("--chr21-fasta", type=Path, required=True)
    command.add_argument("--chr22-fasta", type=Path, required=True)
    command.add_argument("--development-exclusions", type=Path, required=True)
    command.add_argument("--holdout-manifest", type=Path, required=True)
    command.add_argument("--selection-receipt", type=Path, required=True)
    command.add_argument("--application-inputs", type=Path, required=True)
    command.add_argument("--manifest", type=Path, required=True)
    command.add_argument("--manifest-checksum", type=Path, required=True)
    command.add_argument("--source-ledger", type=Path, required=True)
    command.add_argument("--input-summary", type=Path, required=True)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description="Select and materialize the preregistered Phase 3 application panel."
    )
    subparsers = result.add_subparsers(dest="command", required=True)
    cleanup_cache_entry = subparsers.add_parser(
        "cleanup-cache-entry",
        help="Remove one retained-cache entry only when its inode still matches.",
    )
    cleanup_cache_entry.add_argument("--cache-directory-fd", type=int, required=True)
    cleanup_cache_entry.add_argument("--entry-name", required=True)
    cleanup_cache_entry.add_argument("--expected-device", type=int, required=True)
    cleanup_cache_entry.add_argument("--expected-inode", type=int, required=True)
    subparsers.add_parser(
        "sources",
        help="Emit the canonical pinned upstream source specifications.",
    )
    select = subparsers.add_parser(
        "select",
        help="Reconstruct selection and publish its canonical receipt.",
    )
    _add_common_cli_arguments(select)
    verify = subparsers.add_parser(
        "verify",
        help="Verify the complete immutable input freeze without publishing.",
    )
    _add_common_cli_arguments(verify)
    verify.add_argument(
        "--selection",
        type=Path,
        required=True,
        help="Receipt whose exact reconstructed bytes must match.",
    )
    materialize = subparsers.add_parser(
        "materialize",
        help="Reconstruct selection and publish the immutable input freeze.",
    )
    _add_common_cli_arguments(materialize)
    materialize.add_argument(
        "--selection",
        type=Path,
        help="Optional receipt whose exact reconstructed bytes must match.",
    )
    return result


def _paths_from_arguments(args: argparse.Namespace) -> tuple[SourceInputs, FreezePaths]:
    return (
        SourceInputs(
            lncrna_fasta=args.lncrna_fasta,
            annotation_gtf=args.annotation_gtf,
            chr21_fasta=args.chr21_fasta,
            chr22_fasta=args.chr22_fasta,
            development_exclusions=args.development_exclusions,
            holdout_manifest=args.holdout_manifest,
            source_specs=SOURCE_SPECS,
        ),
        FreezePaths(
            repository_root=args.repository_root,
            selection_receipt=args.selection_receipt,
            application_inputs=args.application_inputs,
            manifest=args.manifest,
            manifest_checksum=args.manifest_checksum,
            source_ledger=args.source_ledger,
            input_summary=args.input_summary,
        ),
    )


def main(argv: Iterable[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.command == "cleanup-cache-entry":
        try:
            _remove_owned_cache_entry(
                args.cache_directory_fd,
                args.entry_name,
                (args.expected_device, args.expected_inode),
            )
        except (OSError, ValueError) as error:
            print(f"cache cleanup failed: {error}", file=sys.stderr)
            return 2
        return 0
    if args.command == "sources":
        sys.stdout.write(
            _tsv_bytes(
                SOURCE_SPEC_FIELDS,
                _source_spec_rows(SOURCE_SPECS),
            ).decode("utf-8")
        )
        return 0
    inputs, outputs = _paths_from_arguments(args)
    try:
        if args.command == "select":
            result = select_freeze(inputs, outputs)
        elif args.command == "verify":
            result = verify_freeze(inputs, outputs, args.selection)
        else:
            model = _prepare_freeze(inputs, outputs)
            if args.selection is not None:
                _compare_selection_receipt(model.selection_receipt_bytes, args.selection)
            result = _publish_prepared_freeze(model, outputs, None)
    except (OSError, UnicodeError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"application freeze build failed: {error}", file=sys.stderr)
        return 2
    print(f"selected_queries={result['query_count']}")
    print(f"selected_targets={result['target_count']}")
    print(f"freeze_id={result['freeze_id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
