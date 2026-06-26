#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path
from typing import Iterable


def read_fasta(path: Path) -> list[tuple[str, str]]:
    records: list[tuple[str, str]] = []
    header: str | None = None
    seq: list[str] = []
    with path.open(encoding="utf-8", errors="replace") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith(">"):
                if header is not None:
                    records.append((header, "".join(seq)))
                header = line[1:]
                seq = []
            elif header is not None:
                seq.append(line)
    if header is not None:
        records.append((header, "".join(seq)))
    return records


def write_fasta(records: list[tuple[str, str]], path: Path) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for header, sequence in records:
            handle.write(f">{header}\n")
            for i in range(0, len(sequence), 80):
                handle.write(sequence[i:i + 80] + "\n")


def allocate_windows(lengths: list[int], total_windows: int) -> list[int]:
    if total_windows <= 0:
        return [0 for _ in lengths]
    nonzero = [(idx, length) for idx, length in enumerate(lengths) if length > 0]
    if not nonzero:
        return [0 for _ in lengths]

    total_len = sum(length for _, length in nonzero)
    allocations = [0 for _ in lengths]
    raw: list[tuple[float, int]] = []
    assigned = 0
    for idx, length in nonzero:
        share = total_windows * length / total_len
        whole = int(math.floor(share))
        allocations[idx] = whole
        assigned += whole
        raw.append((share - whole, idx))

    for _, idx in sorted(raw, reverse=True):
        if assigned >= total_windows:
            break
        allocations[idx] += 1
        assigned += 1

    return allocations


SampleRow = tuple[int, str, int, int, int, str]


def make_prefix_records(
    records: list[tuple[str, str]],
    max_bases: int,
    sample_id_start: int = 0,
    sample_kind: str = "prefix",
) -> tuple[list[tuple[str, str]], list[SampleRow]]:
    sampled: list[tuple[str, str]] = []
    manifest: list[SampleRow] = []
    remaining = max_bases
    sample_id = sample_id_start
    for header, sequence in records:
        if max_bases > 0 and remaining <= 0:
            break
        take = len(sequence) if max_bases <= 0 else min(len(sequence), remaining)
        if take <= 0:
            continue
        sample_header = (
            f"{header}|sample_window={sample_id}|sample_kind={sample_kind}|"
            f"source_start=0|source_end={take}"
        )
        sampled.append((sample_header, sequence[:take]))
        manifest.append((sample_id, header, 0, take, take, sample_kind))
        sample_id += 1
        if max_bases > 0:
            remaining -= take
    return sampled, manifest


def make_window_records(
    records: list[tuple[str, str]],
    max_bases: int,
    windows: int,
    sample_id_start: int = 0,
    sample_kind: str = "uniform",
) -> tuple[list[tuple[str, str]], list[SampleRow]]:
    if max_bases <= 0 or windows <= 0:
        return [], []
    lengths = [len(sequence) for _, sequence in records]
    allocations = allocate_windows(lengths, windows)
    window_bases = max(1, math.ceil(max_bases / windows))
    sampled: list[tuple[str, str]] = []
    manifest: list[SampleRow] = []
    sample_id = sample_id_start
    total_sampled = 0

    for (header, sequence), count in zip(records, allocations):
        if count <= 0 or not sequence:
            continue
        size = min(window_bases, len(sequence))
        max_start = max(len(sequence) - size, 0)
        starts: list[int] = []
        if count == 1:
            starts = [0]
        else:
            for i in range(count):
                starts.append(round(i * max_start / (count - 1)))

        seen: set[int] = set()
        for start in starts:
            if start in seen:
                continue
            seen.add(start)
            if total_sampled >= max_bases:
                break
            remaining = max_bases - total_sampled
            take = min(size, remaining, len(sequence) - start)
            if take <= 0:
                continue
            end = start + take
            sample_header = (
                f"{header}|sample_window={sample_id}|sample_kind={sample_kind}|"
                f"source_start={start}|source_end={end}"
            )
            sampled.append((sample_header, sequence[start:end]))
            manifest.append((sample_id, header, start, end, take, sample_kind))
            sample_id += 1
            total_sampled += take

    return sampled, manifest


def parse_int(value: str | None) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except ValueError:
        return None


def filtered_tsv_rows(path: Path) -> Iterable[dict[str, str]]:
    with path.open(newline="", encoding="utf-8", errors="replace") as handle:
        lines = [line for line in handle if line.strip() and not line.startswith("#")]
    if not lines:
        return []
    return csv.DictReader(lines, delimiter="\t")


def record_key_map(records: list[tuple[str, str]]) -> dict[str, int]:
    mapping: dict[str, int] = {}
    for idx, (header, _) in enumerate(records):
        for key in {header, header.split()[0] if header.split() else header}:
            if key:
                mapping.setdefault(key, idx)
    return mapping


def row_value(row: dict[str, str], names: tuple[str, ...]) -> str:
    for name in names:
        if name in row:
            return row.get(name, "")
    return ""


def row_record_index(
    row: dict[str, str],
    records: list[tuple[str, str]],
    mapping: dict[str, int],
) -> int | None:
    chrom = row_value(row, ("Chr", "chr", "source_record", "record", "contig"))
    if chrom:
        return mapping.get(chrom)
    if len(records) == 1:
        return 0
    return None


def anchor_center(row: dict[str, str]) -> int | None:
    start = parse_int(row_value(row, ("StartInGenome", "start", "source_start")))
    end = parse_int(row_value(row, ("EndInGenome", "end", "source_end")))
    if start is None and end is None:
        return None
    if start is None:
        return end
    if end is None:
        return start
    return (start + end) // 2


def make_anchor_records(
    records: list[tuple[str, str]],
    anchor_tsv: Path | None,
    anchor_window_bases: int,
    max_windows: int,
    max_bases: int,
    sample_id_start: int = 0,
) -> tuple[list[tuple[str, str]], list[SampleRow]]:
    if anchor_tsv is None or anchor_window_bases <= 0 or max_bases <= 0:
        return [], []
    mapping = record_key_map(records)
    sampled: list[tuple[str, str]] = []
    manifest: list[SampleRow] = []
    seen: set[tuple[int, int, int]] = set()
    sample_id = sample_id_start
    total_sampled = 0

    for row in filtered_tsv_rows(anchor_tsv):
        if max_windows > 0 and len(manifest) >= max_windows:
            break
        if total_sampled >= max_bases:
            break
        record_idx = row_record_index(row, records, mapping)
        center = anchor_center(row)
        if record_idx is None or center is None:
            continue
        header, sequence = records[record_idx]
        if not sequence:
            continue
        size = min(anchor_window_bases, len(sequence), max_bases - total_sampled)
        if size <= 0:
            continue
        start = max(0, min(center - size // 2, len(sequence) - size))
        end = start + size
        key = (record_idx, start, end)
        if key in seen:
            continue
        seen.add(key)
        sample_header = (
            f"{header}|sample_window={sample_id}|sample_kind=anchor|"
            f"source_start={start}|source_end={end}"
        )
        sampled.append((sample_header, sequence[start:end]))
        manifest.append((sample_id, header, start, end, end - start, "anchor"))
        sample_id += 1
        total_sampled += end - start

    return sampled, manifest


def write_manifest(
    manifest: list[SampleRow],
    path: Path | None,
) -> None:
    if path is None:
        return
    with path.open("w", encoding="utf-8") as handle:
        handle.write("sample_id\tsource_record\tsource_start\tsource_end\tbases\tsample_kind\n")
        for row in manifest:
            handle.write("\t".join(str(value) for value in row) + "\n")


def write_metrics(
    input_records: int,
    selected_records: int,
    manifest: list[SampleRow],
    path: Path | None,
) -> None:
    if path is None:
        return
    sampled_bases = sum(row[4] for row in manifest)
    anchor_windows = sum(1 for row in manifest if row[5] == "anchor")
    uniform_windows = sum(1 for row in manifest if row[5] == "uniform")
    prefix_windows = sum(1 for row in manifest if row[5] == "prefix")
    text = "".join([
        f"input_records={input_records}\n",
        f"selected_records={selected_records}\n",
        f"sample_windows={len(manifest)}\n",
        f"anchor_windows={anchor_windows}\n",
        f"uniform_windows={uniform_windows}\n",
        f"prefix_windows={prefix_windows}\n",
        f"sampled_bases={sampled_bases}\n",
    ])
    path.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sample FASTA records by evenly spaced windows for calibration preflights."
    )
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--max-records", type=int, default=1)
    parser.add_argument(
        "--max-bases",
        type=int,
        default=0,
        help="Total sampled-base budget. A value <=0 writes selected records in full.",
    )
    parser.add_argument(
        "--windows",
        type=int,
        default=1,
        help="Number of evenly spaced windows when --max-bases is positive.",
    )
    parser.add_argument(
        "--anchor-tsv",
        type=Path,
        help=(
            "Optional TSV with StartInGenome/EndInGenome coordinates, such as "
            "topk_rows.tsv. Anchor windows are sampled before uniform windows."
        ),
    )
    parser.add_argument(
        "--anchor-window-bases",
        type=int,
        default=0,
        help="Bases per anchor-centered window. A value <=0 disables anchors.",
    )
    parser.add_argument(
        "--anchor-max-windows",
        type=int,
        default=0,
        help="Maximum anchor windows to use. A value <=0 means no explicit cap.",
    )
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--metrics", type=Path)
    args = parser.parse_args()

    records = read_fasta(args.input)
    if not records:
        raise SystemExit(f"no FASTA records found in {args.input}")

    selected = records[:args.max_records] if args.max_records > 0 else records
    if not selected:
        raise SystemExit(f"no FASTA records selected from {args.input}")

    if args.max_bases > 0 and args.windows > 1:
        anchor_sampled, anchor_manifest = make_anchor_records(
            selected,
            args.anchor_tsv,
            args.anchor_window_bases,
            args.anchor_max_windows,
            args.max_bases,
            sample_id_start=0,
        )
        anchor_bases = sum(row[4] for row in anchor_manifest)
        remaining_bases = max(args.max_bases - anchor_bases, 0)
        uniform_sampled, uniform_manifest = make_window_records(
            selected,
            remaining_bases,
            args.windows,
            sample_id_start=len(anchor_manifest),
            sample_kind="uniform",
        )
        sampled = anchor_sampled + uniform_sampled
        manifest = anchor_manifest + uniform_manifest
    else:
        sampled, manifest = make_prefix_records(selected, args.max_bases)

    if not sampled:
        raise SystemExit(f"no bases selected from {args.input}")

    write_fasta(sampled, args.output)
    write_manifest(manifest, args.manifest)
    write_metrics(len(records), len(selected), manifest, args.metrics)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
