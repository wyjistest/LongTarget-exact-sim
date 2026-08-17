#!/usr/bin/env python3
"""Deterministically combine or slice FASTA inputs used by paper workloads."""

from __future__ import annotations

import argparse
import os
import tempfile
from pathlib import Path


def atomic_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
        handle.write(payload)
        temporary = Path(handle.name)
    os.replace(temporary, path)


def fasta_sequence(path: Path) -> str:
    sequence: list[str] = []
    headers = 0
    with path.open(encoding="ascii") as handle:
        for raw in handle:
            line = raw.strip()
            if not line:
                continue
            if line.startswith(">"):
                headers += 1
                continue
            sequence.append(line)
    if headers != 1 or not sequence:
        raise ValueError(f"single-record FASTA required: {path}")
    result = "".join(sequence)
    if any(base not in "ACGTNacgtn" for base in result):
        raise ValueError(f"unexpected FASTA alphabet: {path}")
    return result


def combine(inputs: list[Path], output: Path) -> None:
    if len(inputs) < 2:
        raise ValueError("combine requires at least two input FASTA files")
    payload = b"".join(path.read_bytes() for path in inputs)
    atomic_bytes(output, payload)


def slice_fasta(source: Path, output: Path, start: int, end: int, header: str, width: int) -> None:
    sequence = fasta_sequence(source)
    if start < 0 or end <= start or end > len(sequence) or width < 1:
        raise ValueError("invalid zero-based half-open FASTA slice")
    selected = sequence[start:end]
    lines = [f">{header}", *(selected[index:index + width] for index in range(0, len(selected), width))]
    atomic_bytes(output, ("\n".join(lines) + "\n").encode("ascii"))


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    combine_parser = subparsers.add_parser("combine")
    combine_parser.add_argument("--output", type=Path, required=True)
    combine_parser.add_argument("inputs", type=Path, nargs="+")
    slice_parser = subparsers.add_parser("slice")
    slice_parser.add_argument("--input", type=Path, required=True)
    slice_parser.add_argument("--output", type=Path, required=True)
    slice_parser.add_argument("--start", type=int, required=True)
    slice_parser.add_argument("--end", type=int, required=True)
    slice_parser.add_argument("--header", required=True)
    slice_parser.add_argument("--width", type=int, default=80)
    args = parser.parse_args()
    if args.command == "combine":
        combine(args.inputs, args.output)
    else:
        slice_fasta(args.input, args.output, args.start, args.end, args.header, args.width)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
