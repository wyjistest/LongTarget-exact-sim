#!/usr/bin/env python3
"""Run one deterministic synthetic exact-merge benchmark for paper receipts."""

from __future__ import annotations

import argparse
import csv
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from fasim_tfo_archive import TFOSORTED_COLUMNS  # noqa: E402


def write_input(path: Path, row_count: int) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(TFOSORTED_COLUMNS)
        for index in range(row_count):
            query_start = index + 1
            target_start = index * 5 + 1
            writer.writerow(
                [
                    query_start,
                    query_start + 3,
                    target_start,
                    target_start + 3,
                    "R",
                    "chrSynthetic",
                    target_start,
                    target_start + 3,
                    "1.5",
                    "75",
                    "ParaPlus",
                    0,
                    index,
                    4,
                    0,
                    query_start + 1,
                    query_start + 1,
                    "ACGT",
                    "TGCA",
                ]
            )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", choices=("memory", "sqlite"), required=True)
    parser.add_argument("--rows", type=int, default=150000)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.rows <= 0:
        parser.error("--rows must be positive")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    source = args.output.with_name(f"{args.output.stem}.input.tsv")
    manifest = args.output.with_name(f"{args.output.stem}.segments.tsv")
    write_input(source, args.rows)
    with manifest.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(
            ["segment_id", "global_start", "global_end", "artifact_kind", "artifact_path"]
        )
        writer.writerow([0, 0, args.rows + 10, "tfosorted", source])
    command = [
        sys.executable,
        str(ROOT / "scripts/merge_fasim_segmented_tfosorted.py"),
        "--segments",
        str(manifest),
        "--output",
        str(args.output),
        "--dedup-backend",
        args.backend,
    ]
    if args.backend == "sqlite":
        command.extend(
            ["--dedup-db", str(args.output.with_name(f"{args.output.stem}.dedup.sqlite"))]
        )
    result = subprocess.run(
        command,
        cwd=ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        raise SystemExit(result.stderr.strip() or "exact merge failed")
    print(f"backend={args.backend}")
    print(f"input_rows={args.rows}")
    print(result.stdout, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
