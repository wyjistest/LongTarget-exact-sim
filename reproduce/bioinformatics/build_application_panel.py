#!/usr/bin/env python3
from __future__ import annotations

import csv
import gzip
import hashlib
from collections.abc import Iterable
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
            line = raw.rstrip("\r\n")
            if not line.strip():
                continue
            if line.startswith(">"):
                if header is not None:
                    append_record()
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

    append_record()
    return records


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
    with path.open("r", encoding="utf-8", errors="strict", newline="") as handle:
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
    with path.open("r", encoding="utf-8", errors="strict", newline="") as handle:
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


def select_targets(
    *,
    transcripts: dict[str, Transcript],
    chromosome_sequences: dict[str, str],
) -> tuple[list[dict[str, object]], dict[str, int]]:
    if not isinstance(chromosome_sequences, dict) or set(chromosome_sequences) != set(
        TARGET_CHROMOSOMES
    ):
        raise ValueError("chromosome sequences must contain exactly chr21 and chr22")
    for chromosome in TARGET_CHROMOSOMES:
        sequence = chromosome_sequences[chromosome]
        if not isinstance(sequence, str) or not sequence:
            raise ValueError(f"{chromosome} chromosome sequence must be a non-empty string")

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
    for tx in representatives:
        chromosome = tx.chromosome
        counts[f"{chromosome}_annotation_target_candidate_count"] += 1
        target = materialize_promoter(tx, chromosome_sequences[chromosome])
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


def select_queries(
    *,
    fasta_records: Iterable[tuple[str, str]],
    transcripts: dict[str, Transcript],
    development_exclusions: dict[str, set[str]],
    holdout_gene_ids: set[str],
    holdout_sequence_sha256: set[str],
) -> tuple[list[dict[str, object]], dict[str, int]]:
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
    candidates_by_gene: dict[str, list[dict[str, object]]] = {}
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
        candidates_by_gene.setdefault(stable_gene_id, []).append(candidate)
        counts["eligible_query_transcript_count"] += 1

    representatives = [
        choose_query_representative(rows) for rows in candidates_by_gene.values()
    ]
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
    return selected, counts
