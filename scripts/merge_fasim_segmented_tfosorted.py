#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from pathlib import Path


INT_OFFSET_COLUMNS = ("QueryStart", "QueryEnd", "MidPoint", "Center")
TFOSORTED_COLUMNS = [
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
]


def read_manifest(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    if not rows:
        raise SystemExit(f"empty segment manifest: {path}")
    required = {"segment_id", "global_start", "global_end", "tfosorted"}
    missing = sorted(required - set(rows[0]))
    if missing:
        raise SystemExit(f"segment manifest missing columns: {','.join(missing)}")
    return rows


def restore_row(row: dict[str, str], offset: int) -> dict[str, str]:
    restored = dict(row)
    for column in INT_OFFSET_COLUMNS:
        value = restored.get(column, "")
        if value == "":
            continue
        restored[column] = str(int(value) + offset)
    return restored


def row_key(row: dict[str, str], columns: list[str]) -> str:
    return "\t".join(row.get(column, "") for column in columns)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Restore global query coordinates and merge segmented Fasim TFOsorted outputs."
    )
    parser.add_argument("--segments", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--query-min", type=int)
    parser.add_argument("--query-max", type=int)
    args = parser.parse_args()

    segments = read_manifest(args.segments)
    output_rows: list[dict[str, str]] = []
    seen: set[str] = set()
    header: list[str] | None = None
    input_rows = 0
    duplicate_rows = 0
    filtered_rows = 0

    for segment in segments:
        tfosorted = Path(segment["tfosorted"])
        if not tfosorted.is_absolute():
            tfosorted = args.segments.parent / tfosorted
        offset = int(segment["global_start"])
        with tfosorted.open(newline="", encoding="utf-8", errors="replace") as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            current_header = reader.fieldnames or []
            if current_header != TFOSORTED_COLUMNS:
                raise SystemExit(
                    f"unsupported TFOsorted schema in {tfosorted}: {current_header}"
                )
            if header is None:
                header = current_header
            elif header != current_header:
                raise SystemExit(f"inconsistent TFOsorted header in {tfosorted}")
            for row in reader:
                input_rows += 1
                restored = restore_row(row, offset)
                query_start = int(restored["QueryStart"])
                query_end = int(restored["QueryEnd"])
                if args.query_min is not None and query_start < args.query_min:
                    filtered_rows += 1
                    continue
                if args.query_max is not None and query_end > args.query_max:
                    filtered_rows += 1
                    continue
                key = row_key(restored, current_header)
                if key in seen:
                    duplicate_rows += 1
                    continue
                seen.add(key)
                output_rows.append(restored)

    if header is None:
        header = TFOSORTED_COLUMNS
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=header, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(output_rows)

    print(f"segments={len(segments)}")
    print(f"input_rows={input_rows}")
    print(f"output_rows={len(output_rows)}")
    print(f"duplicate_rows={duplicate_rows}")
    print(f"filtered_rows={filtered_rows}")
    print(f"output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
