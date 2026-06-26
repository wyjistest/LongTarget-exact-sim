#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import struct
from dataclasses import dataclass
from pathlib import Path


KEY_COLUMNS = [
    "Chr",
    "StartInGenome",
    "EndInGenome",
    "Strand",
    "Rule",
    "QueryStart",
    "QueryEnd",
    "StartInSeq",
    "EndInSeq",
    "Direction",
    "Score",
    "Nt(bp)",
    "MeanIdentity(%)",
    "MeanStability",
]


@dataclass
class TriplexRow:
    row: dict[str, str]
    index: int
    stari: int
    endi: int
    starj: int
    endj: int
    reverse: int
    strand: int
    rule: int
    score: float
    nt: int
    identity: float
    tri_score: float
    middle: int = 0
    motif: int = 0
    center: int = 0
    neartriplex: int = 0


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def _as_int(row: dict[str, str], key: str) -> int:
    return int(row[key])


def _as_float(row: dict[str, str], key: str) -> float:
    return float(row[key])


def _strand_flags(label: str) -> tuple[int, int]:
    if label == "ParaPlus":
        return 0, 1
    if label == "ParaMinus":
        return 1, 1
    if label == "AntiMinus":
        return 1, -1
    if label == "AntiPlus":
        return 0, -1
    raise ValueError(f"unsupported Strand label: {label!r}")


def _load_triplex_rows(path: Path) -> list[TriplexRow]:
    rows = []
    for index, row in enumerate(_read_rows(path)):
        reverse, strand = _strand_flags(row["Strand"])
        rows.append(
            TriplexRow(
                row=row,
                index=index,
                stari=_as_int(row, "QueryStart"),
                endi=_as_int(row, "QueryEnd"),
                starj=_as_int(row, "StartInSeq"),
                endj=_as_int(row, "EndInSeq"),
                reverse=reverse,
                strand=strand,
                rule=_as_int(row, "Rule"),
                score=_as_float(row, "Score"),
                nt=_as_int(row, "Nt(bp)"),
                identity=_as_float(row, "MeanIdentity(%)"),
                tri_score=_as_float(row, "MeanStability"),
            )
        )
    return rows


def _float_bits(value: float) -> int:
    return struct.unpack("<I", struct.pack("<f", value))[0]


def _cluster_triplex(rows: list[TriplexRow], dd: int, length: int) -> None:
    axis_map: dict[int, list[int]] = {}
    rows_by_middle: dict[int, list[TriplexRow]] = {}
    max_neartriplexnum = 0
    max_pos = 0
    found = False

    for row in rows:
        if row.nt > length:
            middle = int((row.stari + row.endi) / 2)
            row.middle = middle
            row.motif = 0
            rows_by_middle.setdefault(middle, []).append(row)
            axis_map.setdefault(middle, [0, 0])[0] += 1

            for i in range(-dd, dd + 1):
                pos = middle + i
                axis = axis_map.setdefault(pos, [0, 0])
                if i > 0:
                    axis[1] += dd - i
                elif i < 0:
                    axis[1] += dd + i
                if axis_map.setdefault(middle, [0, 0])[0] > 0:
                    if axis[1] > max_neartriplexnum:
                        max_neartriplexnum = axis[1]
                        max_pos = pos
                        found = True
            row.neartriplex = axis_map.setdefault(middle, [0, 0])[1]

    theclass = 1
    while found:
        for i in range(max_pos - dd, max_pos + dd + 1):
            for row in rows_by_middle.get(i, []):
                if row.motif == 0:
                    row.motif = theclass
                    row.center = max_pos
            axis_map.pop(i, None)

        max_neartriplexnum = 0
        max_pos = 0
        found = False
        for pos in sorted(axis_map):
            axis = axis_map[pos]
            if axis[1] >= max_neartriplexnum and axis[0] > 0:
                max_neartriplexnum = axis[1]
                max_pos = pos
                found = True
        theclass += 1


def _comp_key(row: TriplexRow) -> tuple[object, ...]:
    return (
        row.motif,
        row.stari,
        row.endi,
        row.starj,
        row.endj,
        row.reverse,
        row.strand,
        row.rule,
        row.nt,
        row.middle,
        row.center,
        row.neartriplex,
        _float_bits(row.score),
        _float_bits(row.identity),
        _float_bits(row.tri_score),
        "",
        "",
        row.index,
    )


def _row_key(row: dict[str, str]) -> str:
    return "\t".join(row.get(column, "") for column in KEY_COLUMNS)


def clustered_topk(path: Path, k: int, dd: int, length: int) -> list[TriplexRow]:
    rows = _load_triplex_rows(path)
    _cluster_triplex(rows, dd=dd, length=length)
    clustered = [row for row in rows if row.motif != 0]
    return sorted(clustered, key=_comp_key)[:k]


def digest(keys: list[str]) -> str:
    return hashlib.sha256(("\n".join(keys) + "\n").encode()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare offline cluster-derived top-k rows from Fasim lite outputs."
    )
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--cluster-distance", type=int, default=15)
    parser.add_argument("--cluster-length", type=int, default=50)
    parser.add_argument("--details", type=Path)
    args = parser.parse_args()

    baseline_top = clustered_topk(
        args.baseline, args.k, args.cluster_distance, args.cluster_length
    )
    candidate_top = clustered_topk(
        args.candidate, args.k, args.cluster_distance, args.cluster_length
    )
    baseline_keys = [_row_key(row.row) for row in baseline_top]
    candidate_keys = [_row_key(row.row) for row in candidate_top]
    equal = baseline_keys == candidate_keys

    print(f"baseline={args.baseline}")
    print(f"candidate={args.candidate}")
    print(f"top{args.k}_offline_cluster_equal={str(equal).lower()}")
    print(f"top{args.k}_offline_cluster_overlap={len(set(baseline_keys) & set(candidate_keys))}")
    print(f"top{args.k}_offline_cluster_baseline_digest={digest(baseline_keys)}")
    print(f"top{args.k}_offline_cluster_candidate_digest={digest(candidate_keys)}")

    if args.details:
        args.details.parent.mkdir(parents=True, exist_ok=True)
        with args.details.open("w", newline="") as handle:
            writer = csv.writer(handle, delimiter="\t")
            writer.writerow(
                [
                    "side",
                    "rank",
                    "Class",
                    "MidPoint",
                    "Center",
                    *KEY_COLUMNS,
                ]
            )
            for side, rows in (("baseline", baseline_top), ("candidate", candidate_top)):
                for rank, row in enumerate(rows, 1):
                    writer.writerow(
                        [
                            side,
                            rank,
                            row.motif,
                            row.middle,
                            row.center,
                            *[row.row.get(column, "") for column in KEY_COLUMNS],
                        ]
                    )

    return 0 if equal else 1


if __name__ == "__main__":
    raise SystemExit(main())
