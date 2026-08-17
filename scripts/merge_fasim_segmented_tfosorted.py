#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import os
import re
import resource
import sqlite3
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from fasim_tfo_archive import (
    ArchiveDecodeStats,
    ArchiveFormatError,
    FastaReference,
    TFOSORTED_COLUMNS,
    iter_archive_first_rows as iter_archive_rows,
    read_single_fasta,
    sha256_file,
)


INT_OFFSET_COLUMNS = ("QueryStart", "QueryEnd", "MidPoint", "Center")
TYPED_MANIFEST_COLUMNS = {
    "segment_id",
    "global_start",
    "global_end",
    "artifact_kind",
    "artifact_path",
}
ARCHIVE_REFERENCE_COLUMNS = {
    "query_fasta",
    "query_fasta_sha256",
    "target_fasta",
    "target_fasta_sha256",
}
LEGACY_MANIFEST_COLUMNS = {"segment_id", "global_start", "global_end", "tfosorted"}
SUPPORTED_ARTIFACT_KINDS = {"tfosorted", "archive_first_tfoa"}
SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")


class MergeError(ValueError):
    pass


@dataclass(frozen=True)
class SegmentArtifact:
    segment_id: str
    global_start: int
    global_end: int
    artifact_kind: str
    artifact_path: Path
    query_fasta: Path | None = None
    query_fasta_sha256: str | None = None
    target_fasta: Path | None = None
    target_fasta_sha256: str | None = None

    @property
    def query_length(self) -> int:
        return self.global_end - self.global_start


class ReferenceCache:
    def __init__(self) -> None:
        self._digests: dict[Path, str] = {}
        self._references: dict[tuple[Path, str], FastaReference] = {}

    def verified_reference(self, path: Path, expected_digest: str, role: str) -> FastaReference:
        if not SHA256_RE.fullmatch(expected_digest):
            raise MergeError(f"invalid {role} reference digest for {path}: {expected_digest}")
        resolved = path.resolve()
        actual_digest = self._digests.get(resolved)
        if actual_digest is None:
            actual_digest = sha256_file(resolved)
            self._digests[resolved] = actual_digest
        if actual_digest != expected_digest.lower():
            raise MergeError(
                f"{role} reference digest mismatch for {path}: expected {expected_digest.lower()}, got {actual_digest}"
            )
        key = (resolved, role)
        reference = self._references.get(key)
        if reference is None:
            reference = read_single_fasta(resolved, role)
            self._references[key] = reference
        return reference


class MemoryDedup:
    backend = "memory"

    def __init__(self) -> None:
        self._seen: set[bytes] = set()

    def add(self, key: bytes) -> bool:
        if key in self._seen:
            return False
        self._seen.add(key)
        return True

    def finish(self) -> int | None:
        return None

    def abort(self) -> None:
        return None


class SQLiteDedup:
    backend = "sqlite"

    def __init__(self, path: Path, commit_rows: int) -> None:
        if path.exists() or any(_sqlite_sidecars(path)):
            raise MergeError(f"dedup database already exists; refusing stale state: {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.commit_rows = commit_rows
        self.pending = 0
        self.connection = sqlite3.connect(str(path))
        self.connection.execute("PRAGMA temp_store=FILE")
        self.connection.execute("PRAGMA cache_size=-8192")
        self.connection.execute("PRAGMA journal_mode=DELETE")
        self.connection.execute("CREATE TABLE seen (row BLOB PRIMARY KEY) WITHOUT ROWID")

    def add(self, key: bytes) -> bool:
        before = self.connection.total_changes
        self.connection.execute("INSERT OR IGNORE INTO seen(row) VALUES (?)", (key,))
        inserted = self.connection.total_changes != before
        self.pending += 1
        if self.pending >= self.commit_rows:
            self.connection.commit()
            self.pending = 0
        return inserted

    def finish(self) -> int:
        self.connection.commit()
        self.connection.close()
        return _sqlite_bytes(self.path)

    def abort(self) -> None:
        try:
            self.connection.rollback()
        finally:
            self.connection.close()


def _sqlite_sidecars(path: Path) -> list[Path]:
    candidates = [Path(f"{path}-journal"), Path(f"{path}-wal"), Path(f"{path}-shm")]
    return [candidate for candidate in candidates if candidate.exists()]


def _sqlite_bytes(path: Path) -> int:
    paths = [path, *_sqlite_sidecars(path)]
    return sum(candidate.stat().st_size for candidate in paths if candidate.exists())


def _remove_sqlite(path: Path) -> None:
    for candidate in [path, *_sqlite_sidecars(path)]:
        try:
            candidate.unlink()
        except FileNotFoundError:
            pass


def _resolve_path(raw_path: str, manifest_path: Path) -> Path:
    if not raw_path:
        raise MergeError("empty artifact/reference path in segment manifest")
    path = Path(raw_path)
    if path.is_absolute() or path.exists():
        return path
    return manifest_path.parent / path


def _parse_nonnegative_int(value: str, field: str, segment_id: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise MergeError(f"segment {segment_id} has non-integer {field}: {value!r}") from exc
    if parsed < 0:
        raise MergeError(f"segment {segment_id} has negative {field}: {parsed}")
    return parsed


def read_manifest(path: Path) -> list[SegmentArtifact]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        columns = reader.fieldnames or []
        if len(columns) != len(set(columns)):
            raise MergeError(f"segment manifest has duplicate columns: {path}")
        typed = TYPED_MANIFEST_COLUMNS <= set(columns)
        legacy = LEGACY_MANIFEST_COLUMNS <= set(columns)
        if not typed and not legacy:
            typed_missing = sorted(TYPED_MANIFEST_COLUMNS - set(columns))
            legacy_missing = sorted(LEGACY_MANIFEST_COLUMNS - set(columns))
            raise MergeError(
                "segment manifest is neither typed nor legacy; "
                f"typed missing={','.join(typed_missing)} legacy missing={','.join(legacy_missing)}"
            )
        rows = list(reader)
    if not rows:
        raise MergeError(f"empty segment manifest: {path}")

    artifacts: list[SegmentArtifact] = []
    seen_ids: set[str] = set()
    for row_number, row in enumerate(rows, start=2):
        if None in row or any(value is None for value in row.values()):
            raise MergeError(f"malformed segment manifest row {row_number}: {path}")
        segment_id = row.get("segment_id", "")
        if not segment_id:
            raise MergeError(f"empty segment_id at manifest row {row_number}: {path}")
        if segment_id in seen_ids:
            raise MergeError(f"duplicate segment_id in manifest: {segment_id}")
        seen_ids.add(segment_id)
        global_start = _parse_nonnegative_int(row.get("global_start", ""), "global_start", segment_id)
        global_end = _parse_nonnegative_int(row.get("global_end", ""), "global_end", segment_id)
        if global_end <= global_start:
            raise MergeError(
                f"segment {segment_id} has invalid global range {global_start}-{global_end}"
            )

        if typed:
            artifact_kind = row.get("artifact_kind", "")
            artifact_path = _resolve_path(row.get("artifact_path", ""), path)
        else:
            artifact_kind = "tfosorted"
            artifact_path = _resolve_path(row.get("tfosorted", ""), path)
        if artifact_kind not in SUPPORTED_ARTIFACT_KINDS:
            raise MergeError(
                f"segment {segment_id} has unsupported artifact_kind: {artifact_kind!r}"
            )
        if not artifact_path.is_file():
            raise MergeError(f"segment artifact does not exist: {artifact_path}")

        kwargs: dict[str, Path | str | int | None] = {}
        if artifact_kind == "archive_first_tfoa":
            missing = sorted(ARCHIVE_REFERENCE_COLUMNS - set(columns))
            if missing:
                raise MergeError(
                    f"archive segment manifest missing reference columns: {','.join(missing)}"
                )
            for field in ARCHIVE_REFERENCE_COLUMNS:
                if not row.get(field, ""):
                    raise MergeError(f"segment {segment_id} has empty archive reference field: {field}")
            kwargs = {
                "query_fasta": _resolve_path(row["query_fasta"], path),
                "query_fasta_sha256": row["query_fasta_sha256"].lower(),
                "target_fasta": _resolve_path(row["target_fasta"], path),
                "target_fasta_sha256": row["target_fasta_sha256"].lower(),
            }
        artifacts.append(
            SegmentArtifact(
                segment_id=segment_id,
                global_start=global_start,
                global_end=global_end,
                artifact_kind=artifact_kind,
                artifact_path=artifact_path,
                **kwargs,
            )
        )
    return artifacts


def iter_text_tfosorted_rows(path: Path) -> Iterator[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        current_header = reader.fieldnames or []
        if current_header != list(TFOSORTED_COLUMNS):
            raise MergeError(f"unsupported TFOsorted column set in {path}: {current_header}")
        for row_number, row in enumerate(reader, start=2):
            if None in row or any(value is None for value in row.values()):
                raise MergeError(f"malformed TFOsorted row {row_number} in {path}")
            yield dict(row)


def iter_archive_first_rows(
    segment: SegmentArtifact,
    references: ReferenceCache,
    stats: ArchiveDecodeStats,
) -> Iterator[dict[str, str]]:
    if (
        segment.query_fasta is None
        or segment.query_fasta_sha256 is None
        or segment.target_fasta is None
        or segment.target_fasta_sha256 is None
    ):
        raise MergeError(f"segment {segment.segment_id} is missing archive references")
    query = references.verified_reference(
        segment.query_fasta,
        segment.query_fasta_sha256,
        "query",
    )
    target = references.verified_reference(
        segment.target_fasta,
        segment.target_fasta_sha256,
        "target",
    )
    if len(query.sequence) != segment.query_length:
        raise MergeError(
            f"segment {segment.segment_id} query FASTA length {len(query.sequence)} "
            f"does not match global range length {segment.query_length}"
        )
    yield from iter_archive_rows(segment.artifact_path, query, target, stats)


def _coordinate(row: dict[str, str], column: str, source: Path) -> int:
    value = row.get(column, "")
    if value == "":
        raise MergeError(f"missing coordinate {column} in {source}")
    try:
        return int(value)
    except ValueError as exc:
        raise MergeError(f"non-integer coordinate {column}={value!r} in {source}") from exc


def restore_global_query_coordinates(
    row: dict[str, str],
    segment: SegmentArtifact,
) -> dict[str, str]:
    local_values = {
        column: _coordinate(row, column, segment.artifact_path)
        for column in INT_OFFSET_COLUMNS
    }
    query_start = local_values["QueryStart"]
    query_end = local_values["QueryEnd"]
    if query_start < 1 or query_end < query_start or query_end > segment.query_length:
        raise MergeError(
            f"query coordinate range {query_start}-{query_end} in {segment.artifact_path} "
            f"exceeds segment range 1..{segment.query_length}"
        )
    for column in ("MidPoint", "Center"):
        if local_values[column] < query_start or local_values[column] > query_end:
            raise MergeError(
                f"coordinate {column}={local_values[column]} is outside query range "
                f"{query_start}-{query_end} in {segment.artifact_path}"
            )
    restored = dict(row)
    for column, value in local_values.items():
        restored[column] = str(value + segment.global_start)
    return restored


def canonical_row(row: dict[str, str]) -> bytes:
    values: list[str] = []
    for column in TFOSORTED_COLUMNS:
        value = row[column]
        if "\t" in value or "\r" in value or "\n" in value:
            raise MergeError(f"TFOsorted field contains a control delimiter: {column}")
        values.append(value)
    return ("\t".join(values) + "\n").encode("utf-8")


def _peak_rss_kb() -> int:
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if os.uname().sysname == "Darwin":
        return int(peak // 1024)
    return int(peak)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Restore global query coordinates and merge segmented Fasim TFOsorted outputs."
    )
    parser.add_argument("--segments", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--query-min", type=int)
    parser.add_argument("--query-max", type=int)
    parser.add_argument("--dedup-backend", choices=("memory", "sqlite"), default="memory")
    parser.add_argument("--dedup-db", type=Path)
    parser.add_argument("--keep-dedup-db", action="store_true")
    parser.add_argument("--sqlite-commit-rows", type=int, default=10000)
    args = parser.parse_args()

    if args.query_min is not None and args.query_max is not None and args.query_min > args.query_max:
        parser.error("--query-min must be <= --query-max")
    if args.sqlite_commit_rows <= 0:
        parser.error("--sqlite-commit-rows must be positive")
    if args.dedup_backend == "memory" and (args.dedup_db or args.keep_dedup_db):
        parser.error("--dedup-db/--keep-dedup-db require --dedup-backend sqlite")

    merge_start = time.perf_counter()
    restore_wall_seconds = 0.0
    dedup_wall_seconds = 0.0
    write_wall_seconds = 0.0
    input_rows = 0
    output_row_count = 0
    duplicate_rows = 0
    filtered_rows = 0
    archive_input_bytes = 0
    text_input_bytes = 0
    kind_counts: Counter[str] = Counter()
    references = ReferenceCache()
    archive_stats = ArchiveDecodeStats()
    dedup_db_path: Path | None = None
    dedup_db_bytes: int | None = None
    dedup_db_retained = 0
    dedup: MemoryDedup | SQLiteDedup | None = None
    partial_output = args.output.with_name(f"{args.output.name}.partial")

    try:
        segments = read_manifest(args.segments)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        try:
            partial_output.unlink()
        except FileNotFoundError:
            pass
        if args.dedup_backend == "sqlite":
            dedup_db_path = args.dedup_db or args.output.with_name(
                f".{args.output.name}.dedup.sqlite"
            )
            dedup = SQLiteDedup(dedup_db_path, args.sqlite_commit_rows)
        else:
            dedup = MemoryDedup()

        with partial_output.open("wb") as output:
            write_start = time.perf_counter()
            output.write(("\t".join(TFOSORTED_COLUMNS) + "\n").encode("ascii"))
            write_wall_seconds += time.perf_counter() - write_start
            for segment in segments:
                kind_counts[segment.artifact_kind] += 1
                artifact_bytes = segment.artifact_path.stat().st_size
                if segment.artifact_kind == "archive_first_tfoa":
                    archive_input_bytes += artifact_bytes
                    iterator = iter_archive_first_rows(segment, references, archive_stats)
                else:
                    text_input_bytes += artifact_bytes
                    iterator = iter_text_tfosorted_rows(segment.artifact_path)
                iterator = iter(iterator)
                while True:
                    restore_start = time.perf_counter()
                    try:
                        row = next(iterator)
                    except StopIteration:
                        restore_wall_seconds += time.perf_counter() - restore_start
                        break
                    restore_wall_seconds += time.perf_counter() - restore_start
                    input_rows += 1

                    restore_start = time.perf_counter()
                    restored = restore_global_query_coordinates(row, segment)
                    restore_wall_seconds += time.perf_counter() - restore_start
                    query_start = int(restored["QueryStart"])
                    query_end = int(restored["QueryEnd"])
                    if args.query_min is not None and query_start < args.query_min:
                        filtered_rows += 1
                        continue
                    if args.query_max is not None and query_end > args.query_max:
                        filtered_rows += 1
                        continue

                    encoded = canonical_row(restored)
                    dedup_start = time.perf_counter()
                    first_seen = dedup.add(encoded)
                    dedup_wall_seconds += time.perf_counter() - dedup_start
                    if not first_seen:
                        duplicate_rows += 1
                        continue
                    write_start = time.perf_counter()
                    output.write(encoded)
                    write_wall_seconds += time.perf_counter() - write_start
                    output_row_count += 1
            write_start = time.perf_counter()
            output.flush()
            write_wall_seconds += time.perf_counter() - write_start

        dedup_start = time.perf_counter()
        dedup_db_bytes = dedup.finish()
        dedup_wall_seconds += time.perf_counter() - dedup_start
        dedup = None
        write_start = time.perf_counter()
        os.replace(partial_output, args.output)
        write_wall_seconds += time.perf_counter() - write_start
        if dedup_db_path is not None:
            if args.keep_dedup_db:
                dedup_db_retained = 1
            else:
                _remove_sqlite(dedup_db_path)
    except (
        ArchiveFormatError,
        MergeError,
        OSError,
        UnicodeError,
        csv.Error,
        sqlite3.Error,
    ) as exc:
        if dedup is not None:
            dedup.abort()
        raise SystemExit(str(exc)) from exc

    merge_wall_seconds = time.perf_counter() - merge_start
    kind_summary = ",".join(
        f"{kind}:{kind_counts[kind]}" for kind in sorted(kind_counts)
    )
    print(f"segments={len(segments)}")
    print(f"artifact_kind_counts={kind_summary}")
    print(f"archive_input_bytes={archive_input_bytes}")
    print(f"text_input_bytes={text_input_bytes}")
    print(f"input_rows={input_rows}")
    print(f"output_rows={output_row_count}")
    print(f"duplicate_rows={duplicate_rows}")
    print(f"filtered_rows={filtered_rows}")
    print(f"dedup_backend={args.dedup_backend}")
    print(
        "dedup_db_bytes="
        + (str(dedup_db_bytes) if dedup_db_bytes is not None else "unavailable")
    )
    print(
        "dedup_db="
        + (str(dedup_db_path) if dedup_db_path is not None else "unavailable")
    )
    print(f"dedup_db_retained={dedup_db_retained}")
    print(f"merge_wall_seconds={merge_wall_seconds:.6f}")
    print(f"restore_wall_seconds={restore_wall_seconds:.6f}")
    print(f"dedup_wall_seconds={dedup_wall_seconds:.6f}")
    print(f"write_wall_seconds={write_wall_seconds:.6f}")
    print(f"peak_rss_kb={_peak_rss_kb()}")
    print(f"archive_blocks={archive_stats.blocks}")
    print(f"archive_rows={archive_stats.rows}")
    print(f"output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
