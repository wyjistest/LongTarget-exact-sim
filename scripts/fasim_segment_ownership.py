#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, Sequence

from fasim_tfo_archive import ArchiveDecodeStats, TFOSORTED_COLUMNS
from merge_fasim_segmented_tfosorted import (
    ReferenceCache,
    SegmentArtifact,
    canonical_row,
    iter_archive_first_rows,
    iter_text_tfosorted_rows,
    read_manifest,
    restore_global_query_coordinates,
)


DESCRIPTOR_COLUMNS = (
    "segment_id",
    "grid_shift",
    "segment_start",
    "segment_end",
    "core_start",
    "core_end",
    "left_halo",
    "right_halo",
    "query_length",
    "is_first_segment",
    "is_last_segment",
)


class OwnershipError(ValueError):
    pass


@dataclass(frozen=True)
class SegmentInterval:
    segment_id: str
    start: int
    end: int


@dataclass(frozen=True)
class SegmentDescriptor:
    segment_id: str
    grid_shift: int
    segment_start: int
    segment_end: int
    core_start: int
    core_end: int
    left_halo: int
    right_halo: int
    query_length: int
    is_first_segment: bool
    is_last_segment: bool


@dataclass(frozen=True)
class OwnerDecision:
    owner: SegmentDescriptor | None
    eligible_count: int
    core_overlap: int


def segment_starts(
    query_length: int,
    segment_length: int,
    segment_overlap: int,
    grid_shift: int,
) -> list[int]:
    if query_length <= 0:
        raise OwnershipError("query_length must be positive")
    if segment_length <= 0:
        raise OwnershipError("segment_length must be positive")
    if segment_overlap < 0 or segment_overlap >= segment_length:
        raise OwnershipError("segment_overlap must be >= 0 and smaller than segment_length")
    if grid_shift < 0:
        raise OwnershipError("grid_shift must be non-negative")
    if query_length <= segment_length:
        return [0]

    stride = segment_length - segment_overlap
    max_start = query_length - segment_length
    starts = {0, max_start}
    start = grid_shift % stride
    while start <= max_start:
        starts.add(start)
        start += stride
    return sorted(starts)


def derive_descriptors(
    intervals: Sequence[SegmentInterval],
    grid_shift: int,
    query_length: int,
) -> list[SegmentDescriptor]:
    if query_length <= 0:
        raise OwnershipError("query_length must be positive")
    if grid_shift < 0:
        raise OwnershipError("grid_shift must be non-negative")
    if not intervals:
        raise OwnershipError("at least one segment interval is required")

    ordered = sorted(intervals, key=lambda interval: (interval.start, interval.end, interval.segment_id))
    if len({interval.segment_id for interval in ordered}) != len(ordered):
        raise OwnershipError("segment IDs must be unique")
    for interval in ordered:
        if interval.start < 0 or interval.end <= interval.start or interval.end > query_length:
            raise OwnershipError(
                f"invalid segment interval {interval.segment_id}: {interval.start}-{interval.end}"
            )

    boundaries: list[int] = []
    for left, right in zip(ordered, ordered[1:]):
        boundary = (left.end + right.start) // 2
        if boundary < right.start or boundary > left.end:
            raise OwnershipError(
                f"segments {left.segment_id} and {right.segment_id} do not overlap"
            )
        boundaries.append(boundary)

    descriptors: list[SegmentDescriptor] = []
    for index, interval in enumerate(ordered):
        core_start = interval.start if index == 0 else boundaries[index - 1]
        core_end = interval.end if index == len(ordered) - 1 else boundaries[index]
        if core_start < interval.start or core_end > interval.end or core_end <= core_start:
            raise OwnershipError(
                f"core {core_start}-{core_end} is not contained by segment {interval.segment_id} "
                f"({interval.start}-{interval.end})"
            )
        descriptors.append(
            SegmentDescriptor(
                segment_id=interval.segment_id,
                grid_shift=grid_shift,
                segment_start=interval.start,
                segment_end=interval.end,
                core_start=core_start,
                core_end=core_end,
                left_halo=core_start - interval.start,
                right_halo=interval.end - core_end,
                query_length=query_length,
                is_first_segment=interval.start == 0,
                is_last_segment=interval.end == query_length,
            )
        )
    return descriptors


def _segment_id_key(segment_id: str) -> tuple[int, int | str]:
    try:
        return (0, int(segment_id))
    except ValueError:
        return (1, segment_id)


def choose_owner(
    query_start: int,
    query_end: int,
    descriptors: Sequence[SegmentDescriptor],
) -> OwnerDecision:
    if query_start < 1 or query_end < query_start:
        raise OwnershipError(f"invalid 1-based query span: {query_start}-{query_end}")
    span_start = query_start - 1
    span_end = query_end
    eligible = [
        descriptor
        for descriptor in descriptors
        if descriptor.segment_start <= span_start and span_end <= descriptor.segment_end
    ]
    if not eligible:
        return OwnerDecision(owner=None, eligible_count=0, core_overlap=0)

    def rank(descriptor: SegmentDescriptor) -> tuple[object, ...]:
        overlap = max(
            0,
            min(span_end, descriptor.core_end) - max(span_start, descriptor.core_start),
        )
        center_distance = abs(
            (span_start + span_end) - (descriptor.core_start + descriptor.core_end)
        )
        return (
            -overlap,
            center_distance,
            descriptor.segment_start,
            _segment_id_key(descriptor.segment_id),
        )

    owner = min(eligible, key=rank)
    core_overlap = max(
        0,
        min(span_end, owner.core_end) - max(span_start, owner.core_start),
    )
    return OwnerDecision(
        owner=owner,
        eligible_count=len(eligible),
        core_overlap=core_overlap,
    )


def write_descriptor_manifest(path: Path, descriptors: Sequence[SegmentDescriptor]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=list(DESCRIPTOR_COLUMNS),
            delimiter="\t",
            lineterminator="\n",
        )
        writer.writeheader()
        for descriptor in descriptors:
            writer.writerow(
                {
                    "segment_id": descriptor.segment_id,
                    "grid_shift": descriptor.grid_shift,
                    "segment_start": descriptor.segment_start,
                    "segment_end": descriptor.segment_end,
                    "core_start": descriptor.core_start,
                    "core_end": descriptor.core_end,
                    "left_halo": descriptor.left_halo,
                    "right_halo": descriptor.right_halo,
                    "query_length": descriptor.query_length,
                    "is_first_segment": int(descriptor.is_first_segment),
                    "is_last_segment": int(descriptor.is_last_segment),
                }
            )


def _integer(row: dict[str, str], column: str, source: Path) -> int:
    value = row.get(column, "")
    try:
        return int(value)
    except ValueError as exc:
        raise OwnershipError(f"invalid {column}={value!r} in {source}") from exc


def read_descriptor_manifest(path: Path) -> list[SegmentDescriptor]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames != list(DESCRIPTOR_COLUMNS):
            raise OwnershipError(
                f"unsupported descriptor columns in {path}: {reader.fieldnames or []}"
            )
        rows = list(reader)
    descriptors: list[SegmentDescriptor] = []
    for row in rows:
        if None in row or any(value is None for value in row.values()):
            raise OwnershipError(f"malformed descriptor row in {path}")
        descriptors.append(
            SegmentDescriptor(
                segment_id=row["segment_id"],
                grid_shift=_integer(row, "grid_shift", path),
                segment_start=_integer(row, "segment_start", path),
                segment_end=_integer(row, "segment_end", path),
                core_start=_integer(row, "core_start", path),
                core_end=_integer(row, "core_end", path),
                left_halo=_integer(row, "left_halo", path),
                right_halo=_integer(row, "right_halo", path),
                query_length=_integer(row, "query_length", path),
                is_first_segment=row["is_first_segment"] == "1",
                is_last_segment=row["is_last_segment"] == "1",
            )
        )
    if not descriptors:
        raise OwnershipError(f"empty descriptor manifest: {path}")
    if len({descriptor.segment_id for descriptor in descriptors}) != len(descriptors):
        raise OwnershipError(f"duplicate segment ID in descriptor manifest: {path}")
    return descriptors


def _iter_segment_rows(
    segment: SegmentArtifact,
    references: ReferenceCache,
    archive_stats: ArchiveDecodeStats,
) -> Iterator[dict[str, str]]:
    if segment.artifact_kind == "archive_first_tfoa":
        yield from iter_archive_first_rows(segment, references, archive_stats)
    else:
        yield from iter_text_tfosorted_rows(segment.artifact_path)


def _row_digest(encoded: bytes) -> bytes:
    return hashlib.sha256(encoded).digest()


def _sqlite_paths(path: Path) -> Iterable[Path]:
    yield path
    yield Path(f"{path}-journal")
    yield Path(f"{path}-wal")
    yield Path(f"{path}-shm")


def _database_bytes(path: Path) -> int:
    return sum(candidate.stat().st_size for candidate in _sqlite_paths(path) if candidate.exists())


def _write_summary(path: Path, metrics: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(f"{path.name}.partial")
    with partial.open("w", encoding="utf-8") as handle:
        for key, value in metrics.items():
            handle.write(f"{key}={value}\n")
    os.replace(partial, path)


def _read_authority_rows(path: Path) -> Iterator[bytes]:
    for row in iter_text_tfosorted_rows(path):
        yield canonical_row(row)


def run_shadow(
    segments_path: Path,
    descriptors_path: Path,
    authority_path: Path | None,
    output_path: Path,
    database_path: Path,
    summary_path: Path,
    commit_rows: int,
) -> dict[str, object]:
    if commit_rows <= 0:
        raise OwnershipError("commit_rows must be positive")
    stale = [path for path in _sqlite_paths(database_path) if path.exists()]
    if stale:
        raise OwnershipError(f"shadow database already exists; refusing stale state: {stale[0]}")

    segments = read_manifest(segments_path)
    descriptors = read_descriptor_manifest(descriptors_path)
    descriptor_by_id = {descriptor.segment_id: descriptor for descriptor in descriptors}
    if set(descriptor_by_id) != {segment.segment_id for segment in segments}:
        raise OwnershipError("segment and descriptor manifests contain different segment IDs")
    for segment in segments:
        descriptor = descriptor_by_id[segment.segment_id]
        if (segment.global_start, segment.global_end) != (
            descriptor.segment_start,
            descriptor.segment_end,
        ):
            raise OwnershipError(f"segment geometry mismatch for {segment.segment_id}")

    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(database_path))
    connection.execute("PRAGMA temp_store=FILE")
    connection.execute("PRAGMA cache_size=-8192")
    connection.execute("PRAGMA journal_mode=DELETE")
    connection.execute(
        """
        CREATE TABLE rows (
            digest BLOB PRIMARY KEY,
            row BLOB NOT NULL,
            query_start INTEGER NOT NULL,
            query_end INTEGER NOT NULL,
            owner_segment_id TEXT,
            eligible_count INTEGER NOT NULL,
            first_seen INTEGER NOT NULL,
            owner_observed INTEGER NOT NULL DEFAULT 0
        ) WITHOUT ROWID
        """
    )
    connection.execute(
        "CREATE TABLE authority (digest BLOB PRIMARY KEY, row BLOB NOT NULL, position INTEGER NOT NULL) WITHOUT ROWID"
    )

    rows_total = 0
    rows_non_owner_duplicate = 0
    pending = 0
    references = ReferenceCache()
    archive_stats = ArchiveDecodeStats()
    try:
        for segment in segments:
            for local_row in _iter_segment_rows(segment, references, archive_stats):
                rows_total += 1
                restored = restore_global_query_coordinates(local_row, segment)
                encoded = canonical_row(restored)
                digest = _row_digest(encoded)
                query_start = int(restored["QueryStart"])
                query_end = int(restored["QueryEnd"])
                decision = choose_owner(query_start, query_end, descriptors)
                owner_id = decision.owner.segment_id if decision.owner is not None else None
                owner_observed = int(owner_id == segment.segment_id)
                if not owner_observed:
                    rows_non_owner_duplicate += 1
                connection.execute(
                    """
                    INSERT OR IGNORE INTO rows(
                        digest, row, query_start, query_end, owner_segment_id,
                        eligible_count, first_seen, owner_observed
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        digest,
                        encoded,
                        query_start,
                        query_end,
                        owner_id,
                        decision.eligible_count,
                        rows_total,
                        owner_observed,
                    ),
                )
                stored = connection.execute(
                    "SELECT row, owner_segment_id FROM rows WHERE digest = ?", (digest,)
                ).fetchone()
                if stored is None or bytes(stored[0]) != encoded:
                    raise OwnershipError("SHA-256 collision in ownership shadow row store")
                if stored[1] != owner_id:
                    raise OwnershipError("owner decision changed for an identical final row")
                if owner_observed:
                    connection.execute(
                        "UPDATE rows SET owner_observed = 1 WHERE digest = ?", (digest,)
                    )
                pending += 1
                if pending >= commit_rows:
                    connection.commit()
                    pending = 0

        if authority_path is not None:
            for position, encoded in enumerate(_read_authority_rows(authority_path), start=1):
                digest = _row_digest(encoded)
                connection.execute(
                    "INSERT OR IGNORE INTO authority(digest, row, position) VALUES (?, ?, ?)",
                    (digest, encoded, position),
                )
                stored = connection.execute(
                    "SELECT row FROM authority WHERE digest = ?", (digest,)
                ).fetchone()
                if stored is None or bytes(stored[0]) != encoded:
                    raise OwnershipError("SHA-256 collision in authority row store")
        connection.commit()

        rows_unique = connection.execute("SELECT count(*) FROM rows").fetchone()[0]
        rows_owned = connection.execute(
            "SELECT count(*) FROM rows WHERE owner_segment_id IS NOT NULL AND owner_observed = 1"
        ).fetchone()[0]
        rows_no_owner = connection.execute(
            "SELECT count(*) FROM rows WHERE owner_segment_id IS NULL"
        ).fetchone()[0]
        rows_multi_owner = connection.execute(
            "SELECT count(*) FROM rows WHERE eligible_count > 1"
        ).fetchone()[0]
        owner_mismatch = connection.execute(
            "SELECT count(*) FROM rows WHERE owner_segment_id IS NOT NULL AND owner_observed = 0"
        ).fetchone()[0]
        if authority_path is None:
            authority_missing = "unavailable"
            authority_extra = "unavailable"
        else:
            authority_missing = connection.execute(
                """
                SELECT count(*) FROM authority a
                WHERE NOT EXISTS (
                    SELECT 1 FROM rows r
                    WHERE r.digest = a.digest AND r.owner_segment_id IS NOT NULL AND r.owner_observed = 1
                )
                """
            ).fetchone()[0]
            authority_extra = connection.execute(
                """
                SELECT count(*) FROM rows r
                WHERE r.owner_segment_id IS NOT NULL AND r.owner_observed = 1
                  AND NOT EXISTS (SELECT 1 FROM authority a WHERE a.digest = r.digest)
                """
            ).fetchone()[0]

        output_path.parent.mkdir(parents=True, exist_ok=True)
        partial_output = output_path.with_name(f"{output_path.name}.partial")
        with partial_output.open("wb") as output:
            output.write(("\t".join(TFOSORTED_COLUMNS) + "\n").encode("ascii"))
            if authority_path is not None:
                cursor = connection.execute(
                    """
                    SELECT a.row FROM authority a
                    JOIN rows r ON r.digest = a.digest
                    WHERE r.owner_segment_id IS NOT NULL AND r.owner_observed = 1
                    ORDER BY a.position
                    """
                )
                for (encoded,) in cursor:
                    output.write(bytes(encoded))
                cursor = connection.execute(
                    """
                    SELECT r.row FROM rows r
                    WHERE r.owner_segment_id IS NOT NULL AND r.owner_observed = 1
                      AND NOT EXISTS (SELECT 1 FROM authority a WHERE a.digest = r.digest)
                    ORDER BY r.first_seen
                    """
                )
            else:
                cursor = connection.execute(
                    """
                    SELECT row FROM rows
                    WHERE owner_segment_id IS NOT NULL AND owner_observed = 1
                    ORDER BY first_seen
                    """
                )
            for (encoded,) in cursor:
                output.write(bytes(encoded))
            output.flush()
        os.replace(partial_output, output_path)

        potential_removed = rows_total - rows_owned
        metrics: dict[str, object] = {
            "shadow_mode": 1,
            "rows_total": rows_total,
            "rows_unique": rows_unique,
            "rows_owned": rows_owned,
            "rows_non_owner_duplicate": rows_non_owner_duplicate,
            "rows_no_owner": rows_no_owner,
            "rows_multi_owner_before_tiebreak": rows_multi_owner,
            "rows_owner_mismatch_vs_authority": owner_mismatch,
            "authority_missing_rows": authority_missing,
            "authority_extra_rows": authority_extra,
            "owner_is_unique": int(rows_no_owner == 0),
            "potential_row_observations_removed": potential_removed,
            "potential_row_reduction_percent": (
                f"{100.0 * potential_removed / rows_total:.2f}" if rows_total else "0.00"
            ),
            "potential_exact_tasks_removed": "unavailable",
            "potential_tracebacks_removed": "unavailable",
            "runtime_work_dropped": 0,
            "archive_rows": archive_stats.rows,
            "database_bytes": 0,
            "database": database_path,
            "output": output_path,
        }
        connection.commit()
        metrics["database_bytes"] = _database_bytes(database_path)
        _write_summary(summary_path, metrics)
        return metrics
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _derive_command(args: argparse.Namespace) -> int:
    intervals = [
        SegmentInterval(segment.segment_id, segment.global_start, segment.global_end)
        for segment in read_manifest(args.segments)
    ]
    descriptors = derive_descriptors(intervals, args.grid_shift, args.query_length)
    write_descriptor_manifest(args.output, descriptors)
    return 0


def _shadow_command(args: argparse.Namespace) -> int:
    metrics = run_shadow(
        args.segments,
        args.descriptors,
        args.authority,
        args.output,
        args.db,
        args.summary,
        args.sqlite_commit_rows,
    )
    for key, value in metrics.items():
        print(f"{key}={value}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Derive deterministic segment ownership and measure it in a no-drop shadow."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    derive = subparsers.add_parser("derive", help="derive core/halo descriptors from a segment manifest")
    derive.add_argument("--segments", required=True, type=Path)
    derive.add_argument("--grid-shift", required=True, type=int)
    derive.add_argument("--query-length", required=True, type=int)
    derive.add_argument("--output", required=True, type=Path)
    derive.set_defaults(function=_derive_command)

    shadow = subparsers.add_parser("shadow", help="measure final-row ownership without dropping runtime work")
    shadow.add_argument("--segments", required=True, type=Path)
    shadow.add_argument("--descriptors", required=True, type=Path)
    shadow.add_argument("--authority", type=Path)
    shadow.add_argument("--output", required=True, type=Path)
    shadow.add_argument("--db", required=True, type=Path)
    shadow.add_argument("--summary", required=True, type=Path)
    shadow.add_argument("--sqlite-commit-rows", type=int, default=10000)
    shadow.set_defaults(function=_shadow_command)

    args = parser.parse_args()
    try:
        return args.function(args)
    except (OwnershipError, OSError, csv.Error, sqlite3.Error, ValueError) as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    raise SystemExit(main())
