#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import struct
from pathlib import Path


MAGIC = b"FATFOC1\0"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _fasta_bases(path: Path) -> int:
    bases = 0
    with path.open("rb") as handle:
        for line in handle:
            if line.startswith(b">"):
                continue
            bases += len(line.strip())
    return bases


def _restore_metrics(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text().splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key] = value
    return values


def _archive_header(path: Path) -> dict[str, str]:
    with path.open("rb") as handle:
        magic = handle.read(len(MAGIC))
        if magic != MAGIC:
            raise SystemExit("archive magic mismatch")
        raw_header = handle.read(8)
        if len(raw_header) != 8:
            raise SystemExit("truncated archive header")
        version, block_rows = struct.unpack("<II", raw_header)
        terminator_present = "0"
        while True:
            raw_size = handle.read(4)
            if len(raw_size) != 4:
                break
            (block_size,) = struct.unpack("<I", raw_size)
            if block_size == 0:
                terminator_present = "1"
                break
            skipped = handle.seek(block_size, 1)
            if skipped is None:
                continue
        return {
            "archive_magic": "FATFOC1",
            "archive_version": str(version),
            "archive_block_rows": str(block_rows),
            "archive_terminator_present": terminator_present,
        }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate and summarize a Fasim TFO column archive artifact."
    )
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--query-fasta", required=True, type=Path)
    parser.add_argument("--target-fasta", required=True, type=Path)
    parser.add_argument("--restore-log", required=True, type=Path)
    parser.add_argument("--restored-output", required=True, type=Path)
    args = parser.parse_args()

    restore = _restore_metrics(args.restore_log)
    output = _archive_header(args.archive)
    output.update(
        {
            "archive_sha256": _sha256(args.archive),
            "query_fasta_sha256": _sha256(args.query_fasta),
            "target_fasta_sha256": _sha256(args.target_fasta),
            "restored_sha256": _sha256(args.restored_output),
            "query_bases": str(_fasta_bases(args.query_fasta)),
            "target_bases": str(_fasta_bases(args.target_fasta)),
            "archive_bytes": str(args.archive.stat().st_size),
            "restored_bytes": str(args.restored_output.stat().st_size),
            "restore_rows": restore.get("rows", ""),
            "restore_dictionary_payloads": restore.get("dictionary_payloads", ""),
            "restore_reported_bytes": restore.get("restored_bytes", ""),
        }
    )
    for key, value in output.items():
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
