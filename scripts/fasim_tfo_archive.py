#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator


MAGIC = b"FATFOC1\0"
MAGIC_NAME = "FATFOC1"
VERSION = 2
PAYLOAD_COUNT = 13
MAX_DECLARED_BLOCK_ROWS = 1_000_000
MAX_BLOCK_BYTES = 256 * 1024 * 1024
COMP = bytes.maketrans(b"ACGTNacgtn", b"TGCANtgcan")
CODE_TO_DIRECTION = {0: "R", 1: "L"}
CODE_TO_STRAND = {0: "ParaPlus", 1: "ParaMinus", 2: "AntiPlus", 3: "AntiMinus"}
TFOSORTED_COLUMNS = (
    "QueryStart",
    "QueryEnd",
    "StartInSeq",
    "EndInSeq",
    "Direction",
    "Chr",
    "StartInGenome",
    "EndInGenome",
    "MeanStability",
    "MeanIdentity(%)",
    "Strand",
    "Rule",
    "Score",
    "Nt(bp)",
    "Class",
    "MidPoint",
    "Center",
    "TFO sequence",
    "TTS sequence",
)
TFOSORTED_HEADER = ("\t".join(TFOSORTED_COLUMNS) + "\n").encode("ascii")


class ArchiveFormatError(ValueError):
    pass


@dataclass(frozen=True)
class FastaReference:
    path: Path
    header: str
    sequence: bytes
    species: str
    chromosome: str
    start_genome: int


@dataclass
class ArchiveDecodeStats:
    rows: int = 0
    blocks: int = 0
    dictionary_payloads: int = 0
    declared_block_rows: int = 0


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_dna_header_fields(header: str) -> tuple[str, str, int]:
    species = ""
    chromosome = ""
    start_genome = 1
    if not header.startswith(">"):
        return species, chromosome, start_genome

    p1 = header.find("|", 1)
    if p1 < 0:
        return header[1:], chromosome, start_genome
    p2 = header.find("|", p1 + 1)
    if p2 < 0:
        return header[1:p1], header[p1 + 1 :], start_genome

    species = header[1:p1]
    chromosome = header[p1 + 1 : p2]
    coordinate = header[p2 + 1 :]
    dash = coordinate.find("-")
    if dash >= 0:
        coordinate = coordinate[:dash]
    try:
        start_genome = int(coordinate)
    except ValueError:
        start_genome = 0
    return species, chromosome, start_genome


def read_single_fasta(path: Path, role: str) -> FastaReference:
    records: list[tuple[str, bytearray]] = []
    current_header: str | None = None
    current_sequence = bytearray()
    with path.open("rb") as handle:
        for raw in handle:
            line = raw.rstrip(b"\r\n")
            if not line:
                continue
            if line.startswith(b">"):
                if current_header is not None:
                    records.append((current_header, current_sequence))
                try:
                    current_header = line.decode("utf-8")
                except UnicodeDecodeError as exc:
                    raise ArchiveFormatError(f"non-UTF-8 {role} FASTA header in {path}") from exc
                current_sequence = bytearray()
                continue
            if current_header is None:
                raise ArchiveFormatError(f"{role} FASTA sequence before header: {path}")
            current_sequence.extend(line.upper())
    if current_header is not None:
        records.append((current_header, current_sequence))
    if len(records) != 1:
        raise ArchiveFormatError(
            f"archive restore requires exactly one {role} FASTA record in {path}; found {len(records)}"
        )
    header, sequence = records[0]
    if not sequence:
        raise ArchiveFormatError(f"empty {role} FASTA sequence: {path}")
    species, chromosome, start_genome = parse_dna_header_fields(header)
    return FastaReference(
        path=path,
        header=header,
        sequence=bytes(sequence),
        species=species,
        chromosome=chromosome,
        start_genome=start_genome,
    )


def complement(sequence: bytes) -> bytes:
    return sequence.translate(COMP).upper()


def reverse_complement(sequence: bytes) -> bytes:
    return complement(sequence)[::-1]


def target_slice(target: bytes, start: int, end: int, strand_code: int) -> bytes:
    if start > end:
        raise ArchiveFormatError(f"target coordinate range is reversed: {start}-{end}")
    if strand_code in (0, 3):
        if start < 1 or end > len(target):
            raise ArchiveFormatError(
                f"target coordinate range {start}-{end} exceeds 1..{len(target)}"
            )
        raw = target[start - 1 : end]
        return raw if strand_code == 0 else complement(raw)
    if strand_code in (1, 2):
        if start < 0 or end >= len(target):
            raise ArchiveFormatError(
                f"target coordinate range {start}-{end} exceeds 0..{len(target) - 1}"
            )
        raw = target[start : end + 1]
        return reverse_complement(raw) if strand_code == 1 else raw[::-1].upper()
    raise ArchiveFormatError(f"unknown strand code: {strand_code}")


def get_varint(data: bytes, pos: int) -> tuple[int, int]:
    value = 0
    shift = 0
    while True:
        if pos >= len(data):
            raise ArchiveFormatError("truncated varint")
        byte = data[pos]
        pos += 1
        value |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return value, pos
        shift += 7
        if shift >= 70:
            raise ArchiveFormatError("varint exceeds 64-bit range")


def unzigzag(value: int) -> int:
    if value & 1:
        return -((value + 1) >> 1)
    return value >> 1


def decode_delta_varints(payload: bytes, count: int) -> list[int]:
    values: list[int] = []
    previous = 0
    pos = 0
    for _ in range(count):
        encoded, pos = get_varint(payload, pos)
        previous += unzigzag(encoded)
        values.append(previous)
    if pos != len(payload):
        raise ArchiveFormatError("extra delta payload")
    return values


def decode_varints(payload: bytes, count: int) -> list[int]:
    values: list[int] = []
    pos = 0
    for _ in range(count):
        value, pos = get_varint(payload, pos)
        values.append(value)
    if pos != len(payload):
        raise ArchiveFormatError("extra varint payload")
    return values


def decode_bytes(payload: bytes, count: int) -> list[bytes]:
    values: list[bytes] = []
    pos = 0
    for _ in range(count):
        size, pos = get_varint(payload, pos)
        value = payload[pos : pos + size]
        if len(value) != size:
            raise ArchiveFormatError("truncated bytes payload")
        values.append(value)
        pos += size
    if pos != len(payload):
        raise ArchiveFormatError("extra bytes payload")
    return values


def decode_dictionary(payload: bytes, count: int) -> list[bytes]:
    pos = 0
    dictionary_count, pos = get_varint(payload, pos)
    dictionary: list[bytes] = []
    for _ in range(dictionary_count):
        size, pos = get_varint(payload, pos)
        value = payload[pos : pos + size]
        if len(value) != size:
            raise ArchiveFormatError("truncated dictionary value")
        dictionary.append(value)
        pos += size
    values: list[bytes] = []
    for _ in range(count):
        index, pos = get_varint(payload, pos)
        if index >= len(dictionary):
            raise ArchiveFormatError("dictionary index out of range")
        values.append(dictionary[index])
    if pos != len(payload):
        raise ArchiveFormatError("extra dictionary payload")
    return values


def apply_mask(ungapped: bytes, aligned_len: int, mask: bytes) -> bytes:
    required_mask_bytes = (aligned_len + 7) // 8
    if len(mask) != required_mask_bytes:
        raise ArchiveFormatError(
            f"gap mask has {len(mask)} bytes; expected {required_mask_bytes}"
        )
    output = bytearray()
    pos = 0
    for index in range(aligned_len):
        if (mask[index // 8] >> (index % 8)) & 1:
            output.append(45)
        else:
            if pos >= len(ungapped):
                raise ArchiveFormatError("gap mask consumed beyond ungapped sequence")
            output.append(ungapped[pos])
            pos += 1
    if pos != len(ungapped):
        raise ArchiveFormatError(f"gap mask consumed {pos} bases; expected {len(ungapped)}")
    return bytes(output)


def parse_block(block: bytes, declared_block_rows: int) -> tuple[int, dict[str, list[object]]]:
    if len(block) < 8:
        raise ArchiveFormatError("truncated block header")
    row_count, payload_count = struct.unpack("<II", block[:8])
    if row_count > declared_block_rows:
        raise ArchiveFormatError(
            f"archive block row count {row_count} exceeds declared block rows {declared_block_rows}"
        )
    if payload_count != PAYLOAD_COUNT:
        raise ArchiveFormatError(
            f"unsupported archive column payload count: {payload_count}; expected {PAYLOAD_COUNT}"
        )
    pos = 8
    sizes: list[int] = []
    for _ in range(payload_count):
        if pos + 4 > len(block):
            raise ArchiveFormatError("truncated payload size")
        (size,) = struct.unpack("<I", block[pos : pos + 4])
        sizes.append(size)
        pos += 4
    payloads: list[bytes] = []
    for size in sizes:
        payload = block[pos : pos + size]
        if len(payload) != size:
            raise ArchiveFormatError("truncated payload")
        payloads.append(payload)
        pos += size
    if pos != len(block):
        raise ArchiveFormatError("extra block payload")
    values: dict[str, list[object]] = {
        "q_start": decode_delta_varints(payloads[0], row_count),
        "seq_start": decode_delta_varints(payloads[1], row_count),
        "score": decode_delta_varints(payloads[2], row_count),
        "align_len": decode_delta_varints(payloads[3], row_count),
        "q_len": decode_varints(payloads[4], row_count),
        "target_len": decode_varints(payloads[5], row_count),
        "rule": decode_varints(payloads[6], row_count),
        "nt": decode_varints(payloads[7], row_count),
        "flags": list(payloads[8]),
        "stability": decode_dictionary(payloads[9], row_count),
        "identity": decode_dictionary(payloads[10], row_count),
        "tfo_masks": decode_bytes(payloads[11], row_count),
        "tts_masks": decode_bytes(payloads[12], row_count),
    }
    if len(values["flags"]) != row_count:
        raise ArchiveFormatError("bad flags payload")
    return row_count, values


def _ascii(value: bytes, field: str) -> str:
    try:
        return value.decode("ascii")
    except UnicodeDecodeError as exc:
        raise ArchiveFormatError(f"non-ASCII archive {field}") from exc


def iter_archive_first_rows(
    path: Path,
    query: FastaReference,
    target: FastaReference,
    stats: ArchiveDecodeStats | None = None,
) -> Iterator[dict[str, str]]:
    decode_stats = stats if stats is not None else ArchiveDecodeStats()
    with path.open("rb") as archive:
        if archive.read(len(MAGIC)) != MAGIC:
            raise ArchiveFormatError(f"bad archive magic in {path}")
        raw = archive.read(8)
        if len(raw) != 8:
            raise ArchiveFormatError(f"truncated archive header in {path}")
        version, block_rows = struct.unpack("<II", raw)
        if version != VERSION:
            raise ArchiveFormatError(
                f"unsupported archive version in {path}: {version}; expected {VERSION}"
            )
        if block_rows == 0:
            raise ArchiveFormatError(f"archive declares zero block rows: {path}")
        if block_rows > MAX_DECLARED_BLOCK_ROWS:
            raise ArchiveFormatError(
                f"archive declares unsupported block rows {block_rows}; maximum is {MAX_DECLARED_BLOCK_ROWS}"
            )
        decode_stats.declared_block_rows = block_rows
        while True:
            raw = archive.read(4)
            if len(raw) != 4:
                raise ArchiveFormatError(f"truncated archive block size in {path}")
            (block_size,) = struct.unpack("<I", raw)
            if block_size == 0:
                if archive.read(1):
                    raise ArchiveFormatError(f"trailing bytes after archive terminator in {path}")
                break
            if block_size > MAX_BLOCK_BYTES:
                raise ArchiveFormatError(
                    f"archive block size {block_size} exceeds bounded limit {MAX_BLOCK_BYTES} in {path}"
                )
            block = archive.read(block_size)
            if len(block) != block_size:
                raise ArchiveFormatError(f"truncated archive block in {path}")
            row_count, values = parse_block(block, block_rows)
            decode_stats.blocks += 1
            decode_stats.dictionary_payloads += 2
            for index in range(row_count):
                query_start = int(values["q_start"][index])
                sequence_start = int(values["seq_start"][index])
                score = int(values["score"][index])
                aligned_len = int(values["align_len"][index])
                query_len = int(values["q_len"][index])
                target_len = int(values["target_len"][index])
                if query_start < 1 or query_len < 1 or target_len < 1 or aligned_len < 1:
                    raise ArchiveFormatError(
                        f"invalid non-positive archive coordinates at row {decode_stats.rows + 1}"
                    )
                query_end = query_start + query_len - 1
                sequence_end = sequence_start + target_len - 1
                if query_end > len(query.sequence):
                    raise ArchiveFormatError(
                        f"archive query range {query_start}-{query_end} exceeds 1..{len(query.sequence)}"
                    )
                flags = int(values["flags"][index])
                if flags & ~0x7:
                    raise ArchiveFormatError(f"unsupported archive flags: {flags}")
                direction_code = flags & 0x1
                strand_code = (flags >> 1) & 0x3
                query_slice = query.sequence[query_start - 1 : query_end]
                target_ungapped = target_slice(
                    target.sequence,
                    sequence_start,
                    sequence_end,
                    strand_code,
                )
                tfo = apply_mask(
                    query_slice,
                    aligned_len,
                    bytes(values["tfo_masks"][index]),
                )
                tts = apply_mask(
                    target_ungapped,
                    aligned_len,
                    bytes(values["tts_masks"][index]),
                )
                midpoint = (query_start + query_end) // 2
                genome_start = sequence_start + target.start_genome - 1
                genome_end = sequence_end + target.start_genome - 1
                row = {
                    "QueryStart": str(query_start),
                    "QueryEnd": str(query_end),
                    "StartInSeq": str(sequence_start),
                    "EndInSeq": str(sequence_end),
                    "Direction": CODE_TO_DIRECTION[direction_code],
                    "Chr": target.chromosome,
                    "StartInGenome": str(genome_start),
                    "EndInGenome": str(genome_end),
                    "MeanStability": _ascii(bytes(values["stability"][index]), "stability"),
                    "MeanIdentity(%)": _ascii(bytes(values["identity"][index]), "identity"),
                    "Strand": CODE_TO_STRAND[strand_code],
                    "Rule": str(int(values["rule"][index])),
                    "Score": str(score),
                    "Nt(bp)": str(int(values["nt"][index])),
                    "Class": "0",
                    "MidPoint": str(midpoint),
                    "Center": str(midpoint),
                    "TFO sequence": _ascii(tfo, "TFO sequence"),
                    "TTS sequence": _ascii(tts, "TTS sequence"),
                }
                decode_stats.rows += 1
                yield row
