#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from fasim_tfo_archive import (
    ArchiveDecodeStats,
    ArchiveFormatError,
    TFOSORTED_COLUMNS,
    iter_archive_first_rows,
    read_single_fasta,
)


def restore_archive(
    source: Path,
    destination: Path,
    query_fasta: Path,
    target_fasta: Path,
) -> ArchiveDecodeStats:
    query = read_single_fasta(query_fasta, "query")
    target = read_single_fasta(target_fasta, "target")
    stats = ArchiveDecodeStats()
    with destination.open("w", encoding="utf-8", newline="") as output:
        output.write("\t".join(TFOSORTED_COLUMNS) + "\n")
        for row in iter_archive_first_rows(source, query, target, stats):
            output.write("\t".join(row[column] for column in TFOSORTED_COLUMNS) + "\n")
    return stats


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--query-fasta", required=True, type=Path)
    parser.add_argument("--target-fasta", required=True, type=Path)
    args = parser.parse_args()
    try:
        stats = restore_archive(
            args.archive,
            args.output,
            args.query_fasta,
            args.target_fasta,
        )
    except (ArchiveFormatError, OSError) as exc:
        raise SystemExit(str(exc)) from exc
    print(f"rows={stats.rows}")
    print(f"dictionary_payloads={stats.dictionary_payloads}")
    print(f"restored_bytes={args.output.stat().st_size}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
