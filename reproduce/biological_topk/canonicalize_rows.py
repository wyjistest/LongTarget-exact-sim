#!/usr/bin/env python3
"""Fail-closed TFOsorted parsing and canonical row construction.

The comparator reads input identity receipts before it reads either prediction
file.  This module deliberately keeps receipt parsing, external-file
validation, and output canonicalization as separate operations so callers can
enforce that ordering.
"""

from __future__ import annotations

import csv
import functools
import hashlib
import json
import re
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping, Sequence

try:  # Direct execution and package import are both supported.
    from . import contract
except ImportError:  # pragma: no cover - exercised by script entry points
    import contract  # type: ignore[no-redef]


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
PAIR_IDENTITY_FIELDS = (
    "schema_version",
    "query_ordinal_namespace",
    "query_source_ordinal",
    "query_sequence_sha256",
    "query_extracted_interval",
    "target_ordinal_namespace",
    "target_source_ordinal",
    "target_sequence_sha256",
    "target_extracted_interval",
    "assembly",
    "target_coordinate_namespace",
    "query_extraction_recipe_id",
    "target_extraction_recipe_id",
    "parameter_bundle_sha256",
    "input_pair_digest",
)
RECEIPT_FIELDS = (
    "schema_version",
    "receipt_kind",
    "workload_id",
    "arm",
    "evidence_role",
    "technical_success",
    "output_valid",
    "output_sha256",
    "query_fasta",
    "query_fasta_interval",
    "target_fasta",
    "target_fasta_interval",
    "target_region_start0",
    "chromosome_or_target_id",
    "input_identity",
)
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
NONNEGATIVE_INTEGER_PATTERN = re.compile(r"(?:0|[1-9][0-9]*)\Z", re.ASCII)
POSITIVE_INTEGER_PATTERN = re.compile(r"[1-9][0-9]*\Z", re.ASCII)


class CanonicalizationError(contract.ContractError):
    """Raised when a receipt, FASTA, or TFOsorted row is not canonical."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _require_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise CanonicalizationError(f"{label} must be a JSON object")
    return value


def _require_exact_fields(value: Mapping[str, Any], fields: Sequence[str], label: str) -> None:
    missing = sorted(set(fields) - set(value))
    unknown = sorted(set(value) - set(fields))
    if missing or unknown:
        raise CanonicalizationError(
            f"{label} field mismatch: missing={missing}, unknown={unknown}"
        )


def _parse_slice(value: Any, label: str) -> tuple[int, int]:
    if (
        not isinstance(value, list)
        or len(value) != 2
        or any(not isinstance(item, int) or isinstance(item, bool) for item in value)
    ):
        raise CanonicalizationError(f"{label} must be a two-integer JSON array")
    start, end = value
    if not 0 <= start < end:
        raise CanonicalizationError(f"{label} must be a nonempty 0-based half-open interval")
    return start, end


def _parse_sha256(value: Any, label: str) -> str:
    if not isinstance(value, str) or SHA256_PATTERN.fullmatch(value) is None:
        raise CanonicalizationError(f"{label} must be a lowercase SHA-256 digest")
    return value


def _resolve_path(raw: Any, base: Path, label: str) -> Path:
    if not isinstance(raw, str) or not raw:
        raise CanonicalizationError(f"{label} must be a nonempty path")
    path = Path(raw)
    return path if path.is_absolute() else (base / path).resolve()


@dataclass(frozen=True, slots=True)
class InputReceipt:
    source_path: Path | None
    workload_id: str
    arm: str
    evidence_role: str
    technical_success: bool
    output_valid: bool
    output_sha256: str
    query_fasta: Path
    query_fasta_interval: tuple[int, int]
    target_fasta: Path
    target_fasta_interval: tuple[int, int]
    target_region_start0: int
    chromosome_or_target_id: str
    input_identity: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class ValidatedReceipt:
    receipt: InputReceipt
    query_sequence: str
    target_sequence: str


@dataclass(frozen=True, slots=True)
class CanonicalRow:
    source_index: int
    raw_row_key: tuple[str, ...]
    raw_query_start: int
    raw_query_end: int
    direction: str
    chromosome_or_target_id: str
    strand: str
    rule: int
    score: Decimal
    score_decimal_string: str
    score_integer: int
    nt: int
    mean_stability: Decimal
    mean_stability_decimal: str
    mean_identity: Decimal
    mean_identity_decimal: str
    coordinates: contract.CanonicalCoordinates
    legacy_midpoint: int
    raw_tfo_sha256: str
    raw_tts_sha256: str
    ungapped_tfo_sha256: str
    ungapped_tts_sha256: str
    strict_row_digest_diagnostic: str
    technical_valid: bool = True


def _validate_identity(identity: Mapping[str, Any]) -> None:
    _require_exact_fields(identity, PAIR_IDENTITY_FIELDS, "input_identity")
    if identity["schema_version"] != 1:
        raise CanonicalizationError("input identity schema_version must be 1")
    for field in (
        "query_ordinal_namespace",
        "target_ordinal_namespace",
        "assembly",
        "target_coordinate_namespace",
        "query_extraction_recipe_id",
        "target_extraction_recipe_id",
    ):
        if not isinstance(identity[field], str) or not identity[field]:
            raise CanonicalizationError(f"input identity {field} must be nonempty text")
    for field in ("query_source_ordinal", "target_source_ordinal"):
        value = identity[field]
        if not isinstance(value, (str, int)) or isinstance(value, bool) or str(value) == "":
            raise CanonicalizationError(f"input identity {field} must be a string or integer")
    for field in (
        "query_sequence_sha256",
        "target_sequence_sha256",
        "parameter_bundle_sha256",
        "input_pair_digest",
    ):
        _parse_sha256(identity[field], f"input identity {field}")
    for field in ("query_extracted_interval", "target_extracted_interval"):
        interval = identity[field]
        if (
            not isinstance(interval, dict)
            or set(interval) != {"start0", "end0"}
            or not isinstance(interval["start0"], int)
            or isinstance(interval["start0"], bool)
            or not isinstance(interval["end0"], int)
            or isinstance(interval["end0"], bool)
            or not 0 <= interval["start0"] < interval["end0"]
        ):
            raise CanonicalizationError(
                f"input identity {field} must contain a nonempty start0/end0 interval"
            )
    observed = contract.input_pair_digest(identity)
    if observed != identity["input_pair_digest"]:
        raise CanonicalizationError("input_pair_digest does not reproduce from its identity")


def receipt_from_mapping(
    value: Mapping[str, Any],
    *,
    source_path: Path | None = None,
    base_directory: Path | None = None,
) -> InputReceipt:
    _require_exact_fields(value, RECEIPT_FIELDS, "input receipt")
    if value["schema_version"] != 1:
        raise CanonicalizationError("input receipt schema_version must be 1")
    if value["receipt_kind"] != "biological_topk_input_receipt_v1":
        raise CanonicalizationError("unsupported input receipt kind")
    for field in ("workload_id", "arm", "evidence_role", "chromosome_or_target_id"):
        if not isinstance(value[field], str) or not value[field]:
            raise CanonicalizationError(f"receipt {field} must be nonempty text")
    if value["arm"] not in {"A", "G"}:
        raise CanonicalizationError("receipt arm must be A or G")
    for field in ("technical_success", "output_valid"):
        if not isinstance(value[field], bool):
            raise CanonicalizationError(f"receipt {field} must be boolean")
    output_sha256 = _parse_sha256(value["output_sha256"], "receipt output_sha256")
    target_region_start0 = value["target_region_start0"]
    if (
        not isinstance(target_region_start0, int)
        or isinstance(target_region_start0, bool)
        or target_region_start0 < 0
    ):
        raise CanonicalizationError("target_region_start0 must be a nonnegative integer")
    identity = _require_mapping(value["input_identity"], "input_identity")
    _validate_identity(identity)
    base = base_directory or (source_path.parent if source_path is not None else Path.cwd())
    return InputReceipt(
        source_path=source_path,
        workload_id=value["workload_id"],
        arm=value["arm"],
        evidence_role=value["evidence_role"],
        technical_success=value["technical_success"],
        output_valid=value["output_valid"],
        output_sha256=output_sha256,
        query_fasta=_resolve_path(value["query_fasta"], base, "query_fasta"),
        query_fasta_interval=_parse_slice(value["query_fasta_interval"], "query_fasta_interval"),
        target_fasta=_resolve_path(value["target_fasta"], base, "target_fasta"),
        target_fasta_interval=_parse_slice(value["target_fasta_interval"], "target_fasta_interval"),
        target_region_start0=target_region_start0,
        chromosome_or_target_id=value["chromosome_or_target_id"],
        input_identity=dict(identity),
    )


def load_receipt(path: Path) -> InputReceipt:
    if not path.is_file() or path.is_symlink():
        raise CanonicalizationError(f"missing or unsafe input receipt: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise CanonicalizationError(f"invalid input receipt JSON {path}: {error}") from error
    return receipt_from_mapping(_require_mapping(value, "input receipt"), source_path=path.resolve())


@functools.lru_cache(maxsize=256)
def _read_single_fasta(path: Path, role: str) -> str:
    if not path.is_file() or path.is_symlink():
        raise CanonicalizationError(f"missing or unsafe {role} FASTA: {path}")
    records: list[str] = []
    current: list[str] | None = None
    try:
        lines = path.read_text(encoding="ascii").splitlines()
    except UnicodeDecodeError as error:
        raise CanonicalizationError(f"non-ASCII {role} FASTA: {path}") from error
    for line_number, line in enumerate(lines, 1):
        if not line:
            continue
        if line.startswith(">"):
            if current is not None:
                records.append("".join(current))
            current = []
            continue
        if current is None:
            raise CanonicalizationError(f"{role} FASTA sequence precedes header at line {line_number}")
        if line != line.strip(" \t\r\n") or any(character in " \t" for character in line):
            raise CanonicalizationError(f"whitespace inside {role} FASTA sequence at line {line_number}")
        current.append(line)
    if current is not None:
        records.append("".join(current))
    if len(records) != 1:
        raise CanonicalizationError(f"{role} FASTA must contain exactly one record")
    sequence = contract.normalize_ungapped(records[0])
    if not sequence:
        raise CanonicalizationError(f"empty {role} FASTA sequence")
    return sequence


def validate_receipt_files(receipt: InputReceipt, output_path: Path) -> ValidatedReceipt:
    if not receipt.technical_success or not receipt.output_valid:
        raise CanonicalizationError(
            f"{receipt.arm} receipt reports technical_success/output_valid false"
        )
    if not output_path.is_file() or output_path.is_symlink():
        raise CanonicalizationError(f"missing or unsafe TFOsorted output: {output_path}")
    if sha256_file(output_path) != receipt.output_sha256:
        raise CanonicalizationError(f"{receipt.arm} output checksum mismatch")
    query_source = _read_single_fasta(receipt.query_fasta, "query")
    target_source = _read_single_fasta(receipt.target_fasta, "target")
    query_start, query_end = receipt.query_fasta_interval
    target_start, target_end = receipt.target_fasta_interval
    if query_end > len(query_source) or target_end > len(target_source):
        raise CanonicalizationError(f"{receipt.arm} FASTA extraction interval is out of bounds")
    query = query_source[query_start:query_end]
    target = target_source[target_start:target_end]
    if contract.sequence_sha256(query) != receipt.input_identity["query_sequence_sha256"]:
        raise CanonicalizationError(f"{receipt.arm} query sequence digest mismatch")
    if contract.sequence_sha256(target) != receipt.input_identity["target_sequence_sha256"]:
        raise CanonicalizationError(f"{receipt.arm} target sequence digest mismatch")
    return ValidatedReceipt(receipt=receipt, query_sequence=query, target_sequence=target)


def _parse_integer(raw: str, label: str, *, positive: bool = False) -> int:
    pattern = POSITIVE_INTEGER_PATTERN if positive else NONNEGATIVE_INTEGER_PATTERN
    if pattern.fullmatch(raw) is None:
        qualifier = "positive" if positive else "nonnegative"
        raise CanonicalizationError(f"{label} must be a canonical {qualifier} integer")
    return int(raw)


def _canonical_row(
    row: Mapping[str, str],
    source_index: int,
    validated: ValidatedReceipt,
) -> CanonicalRow:
    receipt = validated.receipt
    query_start = _parse_integer(row["QueryStart"], "QueryStart", positive=True)
    query_end = _parse_integer(row["QueryEnd"], "QueryEnd", positive=True)
    target_start = _parse_integer(row["StartInSeq"], "StartInSeq")
    target_end = _parse_integer(row["EndInSeq"], "EndInSeq")
    genome_start = _parse_integer(row["StartInGenome"], "StartInGenome")
    genome_end = _parse_integer(row["EndInGenome"], "EndInGenome")
    rule = _parse_integer(row["Rule"], "Rule")
    nt = _parse_integer(row["Nt(bp)"], "Nt(bp)")
    _parse_integer(row["Class"], "Class")
    _parse_integer(row["MidPoint"], "MidPoint")
    _parse_integer(row["Center"], "Center")
    score = contract.parse_decimal(row["Score"])
    if score != score.to_integral_value():
        raise CanonicalizationError("Score is nonintegral under integral_exact")
    stability = contract.parse_decimal(row["MeanStability"])
    identity = contract.parse_decimal(row["MeanIdentity(%)"])
    if not 0 <= identity <= 100:
        raise CanonicalizationError("MeanIdentity(%) is outside [0,100]")
    if row["Direction"] not in contract.CURRENT_REACHABLE_DIRECTIONS:
        raise CanonicalizationError(f"unsupported Direction: {row['Direction']!r}")
    if row["Strand"] not in contract.SUPPORTED_STRANDS:
        raise CanonicalizationError(f"unsupported Strand: {row['Strand']!r}")
    coordinates = contract.canonicalize_coordinates(
        raw_query_start=query_start,
        raw_query_end=query_end,
        raw_target_start=target_start,
        raw_target_end=target_end,
        strand=row["Strand"],
        direction=row["Direction"],
        target_length=len(validated.target_sequence),
        target_region_start0=receipt.target_region_start0,
    )
    if coordinates.query_end0 > len(validated.query_sequence):
        raise CanonicalizationError("normalized query interval is outside the query FASTA")
    ungapped_tfo = contract.normalize_ungapped(row["TFO sequence"])
    ungapped_tts = contract.normalize_ungapped(row["TTS sequence"])
    if not ungapped_tfo or not ungapped_tts:
        raise CanonicalizationError("TFO/TTS sequence becomes empty after normalization")
    expected_tts = contract.reconstruct_tts(
        validated.target_sequence,
        coordinates,
        row["Strand"],
    )
    if ungapped_tts != expected_tts:
        raise CanonicalizationError(
            f"TTS reconstruction mismatch at source row {source_index + 2}"
        )
    chromosome = row["Chr"] or receipt.chromosome_or_target_id
    raw_key = tuple(row[column] for column in TFOSORTED_COLUMNS)
    return CanonicalRow(
        source_index=source_index,
        raw_row_key=raw_key,
        raw_query_start=query_start,
        raw_query_end=query_end,
        direction=row["Direction"],
        chromosome_or_target_id=chromosome,
        strand=row["Strand"],
        rule=rule,
        score=score,
        score_decimal_string=contract.canonical_decimal(score),
        score_integer=int(score),
        nt=nt,
        mean_stability=stability,
        mean_stability_decimal=contract.canonical_decimal(stability),
        mean_identity=identity,
        mean_identity_decimal=contract.canonical_decimal(identity),
        coordinates=coordinates,
        legacy_midpoint=contract.legacy_query_midpoint(query_start, query_end),
        raw_tfo_sha256=hashlib.sha256(row["TFO sequence"].encode("utf-8")).hexdigest(),
        raw_tts_sha256=hashlib.sha256(row["TTS sequence"].encode("utf-8")).hexdigest(),
        ungapped_tfo_sha256=contract.sequence_sha256(ungapped_tfo),
        ungapped_tts_sha256=contract.sequence_sha256(ungapped_tts),
        strict_row_digest_diagnostic=contract.canonical_json_sha256(list(raw_key)),
    )


def canonicalize_output(path: Path, validated: ValidatedReceipt) -> tuple[CanonicalRow, ...]:
    try:
        handle = path.open(newline="", encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise CanonicalizationError(f"cannot read TFOsorted output {path}: {error}") from error
    with handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if tuple(reader.fieldnames or ()) != TFOSORTED_COLUMNS:
            raise CanonicalizationError(
                f"unsupported TFOsorted columns: {reader.fieldnames or []}"
            )
        rows: list[CanonicalRow] = []
        for source_index, row in enumerate(reader):
            if None in row or any(value is None for value in row.values()):
                raise CanonicalizationError(f"malformed TFOsorted row {source_index + 2}")
            canonical = _canonical_row(row, source_index, validated)
            rows.append(canonical)
    rows.sort(key=lambda row: row.raw_row_key)
    unique: list[CanonicalRow] = []
    previous: tuple[str, ...] | None = None
    for row in rows:
        if row.raw_row_key != previous:
            unique.append(row)
            previous = row.raw_row_key
    return tuple(unique)


def input_identity_mismatches(
    authority: InputReceipt,
    candidate: InputReceipt,
) -> tuple[str, ...]:
    mismatches = list(
        contract.input_identity_mismatches(
            authority.input_identity,
            candidate.input_identity,
        )
    )
    if authority.workload_id != candidate.workload_id:
        mismatches.append("workload_id")
    return tuple(mismatches)


__all__ = [name for name in globals() if not name.startswith("_")]
